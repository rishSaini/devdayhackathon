import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import replace

from .agents import Executor
from .config import Settings
from .decisions import Classifier
from .devices import Devices
from .integrations import Messaging, MockMessaging
from .planning import Planner
from .registry import REGISTRY
from .schemas import Choice, Clarification, Location, Profile, TapRequest, ToolResult
from .spasm_filter import SpasmFilter
from .store import TERMINAL, Action, ActionStore


class Conflict(Exception):
    pass


class Service:
    def __init__(
        self, settings: Settings, messaging: Messaging | None = None, classifier=None, executor=None
    ):
        self.settings = settings
        self.messaging = messaging or MockMessaging()
        self.store = ActionStore(settings.ripple_database_path)
        self.devices = Devices(self.store)
        self.classifier = classifier or Classifier(settings)
        self.executor = executor or Executor(settings, self.messaging, self.devices)
        self.planner = Planner(settings)
        self.spasm_filter = SpasmFilter(settings.ripple_spasm_window_ms)
        for action in sorted(self.store.actions.values(), key=lambda a: a.created_at):
            self.spasm_filter.accepted[(action.request.session_id, action.request.button_id)] = (
                action.request.timestamp,
                action.created_monotonic,
            )
        self.tasks: set[asyncio.Task] = set()
        # Compatibility cache; the durable table remains authoritative.
        self.processed_webhooks: set[str] = set()
        self.settings.user_display_name = self.profile().display_name

    def profile(self) -> Profile:
        return Profile.model_validate(
            self.store.resource(
                "profile", Profile(display_name=self.settings.user_display_name).model_dump()
            )
        )

    def save_profile(self, profile: Profile):
        self.store.put_resource("profile", profile.model_dump())
        self.settings.user_display_name = profile.display_name
        return profile.model_dump()

    async def start(self):
        for action in self.store.actions.values():
            status = action.response.status
            if status == "awaiting_approval":
                self.spawn(self.expire(action), action)
            elif status == "awaiting_input":
                self.spawn(self.expire_input(action), action)
            elif status in {"classifying", "pending_cancel"} and not action.effects:
                self.spawn(
                    self.prepare_selected(action) if action.response.plan else self.prepare(action),
                    action,
                )
            elif status not in TERMINAL:
                action.response.status = "failed"
                action.response.error = "Execution was interrupted. Review saved tool results before retrying; no effects were replayed."
                action.response.message = action.response.error
                # Recover journaled results even if the process stopped before finish().
                action.response.tool_results = [
                    ToolResult.model_validate(result) for result in action.effects.values()
                ]
                action.checkpoint()

    def spawn(self, operation: Awaitable, action: Action) -> None:
        async def guarded():
            try:
                await operation
            except asyncio.CancelledError:
                raise
            except Exception:
                if action.response.status not in TERMINAL:
                    action.response.status = "failed"
                    action.response.error = (
                        "Action failed; external outcome may be unknown. Check before retrying."
                    )
                    action.response.message = action.response.error
            finally:
                action.checkpoint()

        task = asyncio.create_task(guarded())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def tap(self, request: TapRequest) -> dict:
        if self.spasm_filter.should_drop(request.session_id, request.button_id, request.timestamp):
            return {"status": "debounced"}
        spec = REGISTRY[request.button_id]
        action = self.store.create(request, spec.policy_floor)
        if request.button_id == "emergency":
            self.spawn(self.emergency(action), action)
            self.spawn(self.classify(action), action)
        else:
            if spec.static_tier == 1:
                action.response.status = "pending_cancel"
                action.response.cancel_deadline_ms = int(
                    time.time() * 1000 + self.settings.ripple_cancel_window_s * 1000
                )
            action.checkpoint()
            self.spawn(self.prepare(action), action)
        return action.response.model_dump()

    async def classify(self, action: Action):
        spec = REGISTRY[action.request.button_id]
        if action.response.plan:
            # Evaluate selected consequences without exporting private message or health text.
            details = ", ".join(step.tool for step in action.response.plan.steps)
            spec = replace(
                spec, action_description=spec.action_description + " Planned operations: " + details
            )
        result = await self.classifier.classify(spec)
        action.response.tier = max(spec.policy_floor, result.tier)
        action.response.tier_source = result.source
        action.response.confidence = result.confidence
        action.response.model_tier = result.model_tier
        action.response.classification_fallback_reason = result.fallback_reason
        action.checkpoint()

    async def prepare(self, action: Action):
        result = await self.planner.build(action.request, self.profile(), self.devices.read())
        if action.response.status in TERMINAL:
            return
        action.candidates = result.candidates
        action.response.planning_source = result.source
        if result.selected is None:
            action.response.status = "awaiting_input"
            action.response.cancel_deadline_ms = None
            action.response.message = result.question
            action.response.clarification = Clarification(
                id="input_" + uuid.uuid4().hex[:12],
                question=result.question,
                choices=[
                    Choice(id=key, label=value.summary) for key, value in result.candidates.items()
                ],
                expires_at_ms=int(time.time() * 1000 + self.settings.ripple_input_timeout_s * 1000),
            )
            action.checkpoint()
            self.spawn(self.expire_input(action), action)
            return
        action.response.plan = action.candidates[result.selected].model_copy(deep=True)
        action.checkpoint()
        await self.prepare_selected(action)

    def choose(self, action_id: str, clarification_id: str, choice_id: str):
        action = self.store.get(action_id)
        clarification = action.response.clarification
        if (
            action.response.status != "awaiting_input"
            or not clarification
            or clarification.id != clarification_id
        ):
            raise Conflict("This clarification is no longer active.")
        if time.time() * 1000 >= clarification.expires_at_ms:
            action.response.status = "expired"
            action.checkpoint()
            raise Conflict("Clarification expired.")
        if choice_id not in action.candidates:
            raise Conflict("Choose one of the offered options.")
        action.response.plan = action.candidates[choice_id].model_copy(deep=True)
        action.response.clarification = None
        action.response.status = "classifying"
        action.checkpoint()
        self.spawn(self.prepare_selected(action), action)
        return action.response.model_dump()

    async def expire_input(self, action: Action):
        clarification = action.response.clarification
        if not clarification:
            return
        await asyncio.sleep(max(0, clarification.expires_at_ms / 1000 - time.time()))
        if (
            action.response.status == "awaiting_input"
            and action.response.clarification
            and action.response.clarification.id == clarification.id
        ):
            action.response.status = "expired"
            action.response.message = "User choice expired; nothing was executed."
            action.checkpoint()

    async def prepare_selected(self, action: Action):
        await self.classify(action)
        if action.response.status in TERMINAL:
            return
        if action.response.tier >= 2:
            action.response.cancel_deadline_ms = None
            if action.request.button_id == "order_lunch":
                results = await self.executor.run(
                    action, "prepare", lambda: self.await_approval(action)
                )
            else:
                self.await_approval(action)
                results = [
                    await self.effect(
                        action,
                        "approval",
                        lambda: self.messaging.send_approval(
                            self.settings.caregiver_phone,
                            action.response.action_id,
                            action.response.plan.summary,
                        ),
                    )
                ]
            self.record(action, results)
            if action.response.status in {"classifying", "pending_cancel", "awaiting_approval"}:
                if not results or not all(result.ok for result in results):
                    action.response.status = "failed"
                    action.response.message = (
                        "Approval request failed or is incomplete; action was not finalized."
                    )
                    action.response.error = action.response.message
                else:
                    action.response.message = "Waiting for co-signer approval." + (
                        " Simulated request; nothing was sent."
                        if self.messaging.mode == "mock"
                        else ""
                    )
            action.checkpoint()
            return
        remaining = self.settings.ripple_cancel_window_s - (
            time.monotonic() - action.created_monotonic
        )
        await asyncio.sleep(max(0, remaining))
        if action.response.status in TERMINAL:
            return
        action.response.status = "executing"
        action.checkpoint()
        self.finish(action, await self.executor.run(action, "execute"))

    def await_approval(self, action: Action):
        if action.response.status in TERMINAL:
            raise Conflict("Action is no longer active.")
        action.response.status = "awaiting_approval"
        action.approval_deadline = time.monotonic() + self.settings.ripple_approval_timeout_s
        action.response.approval_expires_at_ms = int(
            time.time() * 1000 + self.settings.ripple_approval_timeout_s * 1000
        )
        action.response.approval_fingerprint = action.fingerprint()
        action.checkpoint()
        self.spawn(self.expire(action), action)

    async def expire(self, action: Action):
        await asyncio.sleep(max(0, (action.approval_deadline or 0) - time.monotonic()))
        if action.response.status == "awaiting_approval":
            action.response.status = "expired"
            action.response.message = "Approval expired; nothing was finalized."
            action.checkpoint()

    def cancel(self, action_id: str) -> dict:
        action = self.store.get(action_id)
        if action.request.button_id == "emergency" or action.response.status not in {
            "pending_cancel",
            "classifying",
            "awaiting_approval",
            "awaiting_input",
        }:
            raise Conflict("Action can no longer be canceled.")
        action.response.status = "canceled"
        action.response.message = "Canceled; no further execution will start."
        action.response.cancel_deadline_ms = None
        action.checkpoint()
        return action.response.model_dump()

    def approve(
        self,
        action_id: str,
        approved: bool,
        fingerprint: str | None = None,
        *,
        enqueue: bool = True,
    ) -> dict:
        action = self.store.get(action_id)
        if action.response.status != "awaiting_approval":
            raise Conflict("Action is not awaiting approval.")
        if action.approval_deadline is None or time.monotonic() >= action.approval_deadline:
            action.response.status = "expired"
            action.response.message = "Approval expired; nothing was finalized."
            action.checkpoint()
            raise Conflict("Approval expired.")
        if (
            fingerprint is not None and fingerprint != action.response.approval_fingerprint
        ) or action.fingerprint() != action.response.approval_fingerprint:
            raise Conflict("The request changed. A new approval is required.")
        if not approved:
            action.response.status = "declined"
            action.response.message = "Declined; nothing was finalized."
        else:
            if action.order and (
                action.order.total > self.profile().budget_amount
                or action.order.name in self.profile().unavailable_orders
            ):
                raise Conflict("Order no longer meets the current budget or availability limits.")
            action.approved = True
            action.response.status = "executing"
            action.response.message = "Approved; executing the requested action."
            action.checkpoint()
            if enqueue:
                self.spawn(self.finalize(action), action)
        action.checkpoint()
        return action.response.model_dump()

    async def finalize(self, action: Action):
        if action.fingerprint() != action.response.approval_fingerprint:
            raise Conflict("Approved plan changed.")
        phase = "finalize" if action.request.button_id == "order_lunch" else "execute"
        self.finish(action, await self.executor.run(action, phase))

    async def safe_tool(self, operation: Awaitable[ToolResult]) -> ToolResult:
        try:
            async with asyncio.timeout(self.settings.ripple_tool_timeout_s):
                return await operation
        except Exception:
            return ToolResult(
                ok=False,
                source=self.messaging.mode,
                detail="External operation failed or its outcome is unknown.",
            )

    async def effect(
        self, action: Action, name: str, operation: Callable[[], Awaitable[ToolResult]]
    ):
        if name in action.effects:
            return ToolResult.model_validate(action.effects[name])
        pending = ToolResult(
            ok=False,
            source=self.messaging.mode,
            operation=name,
            detail="Operation started; outcome may be unknown.",
        )
        action.effects[name] = pending.model_dump()
        action.checkpoint()
        result = await self.safe_tool(operation())
        result.operation = name
        action.effects[name] = result.model_dump()
        action.checkpoint()
        return result

    async def emergency(self, action: Action):
        action.response.emergency_followup_status = "pending"
        fallback_location = action.request.location is None
        location = action.request.location or Location(
            lat=self.settings.demo_fallback_lat, lng=self.settings.demo_fallback_lng
        )
        results = await asyncio.gather(
            self.effect(
                action,
                "emergency_call",
                lambda: self.messaging.voice_call(
                    self.settings.emergency_contact,
                    f"This is an automated Ripple demo alert. {self.settings.user_display_name} pressed the emergency button. Location follows by text.",
                ),
            ),
            self.effect(
                action,
                "emergency_location",
                lambda: self.messaging.location_sms(
                    self.settings.emergency_contact, location, fallback=fallback_location
                ),
            ),
        )
        self.finish(action, results)
        if fallback_location:
            action.response.message += " Used the fixed demo location; GPS was unavailable."
        action.checkpoint()
        followup = await self.executor.run(action, "emergency")
        self.record(action, followup)
        action.response.emergency_followup_status = (
            "done" if followup and all(result.ok for result in followup) else "failed"
        )
        if action.response.emergency_followup_status == "failed":
            action.response.status = "failed"
            action.response.error = "Emergency follow-up did not complete. Review the separately recorded call and SMS outcomes."
        action.checkpoint()

    def record(self, action: Action, results: list[ToolResult]):
        for result in results:
            if result.provider_id:
                status = self.store.resource("provider:" + result.provider_id, None)
                if status:
                    result.provider_status = status
                    if status in {"failed", "undelivered", "busy", "no-answer", "canceled"}:
                        result.ok = False
                        result.detail = "Provider reported an unsuccessful delivery or call."
                    for effect in action.effects.values():
                        if effect.get("provider_id") == result.provider_id:
                            effect.update(result.model_dump())
        action.response.tool_results.extend(results)
        all_results = action.response.tool_results
        action.response.source = (
            "mock"
            if any(r.source == "mock" for r in all_results)
            else "fallback"
            if any(r.source == "fallback" for r in all_results)
            else "live"
        )
        action.checkpoint()

    def provider_status(self, provider_id: str, status: str):
        progression = (
            ["accepted", "scheduled", "queued", "sending", "sent", "delivered", "read"]
            if provider_id.startswith("SM")
            else ["queued", "initiated", "ringing", "in-progress", "completed"]
        )
        failures = {"failed", "undelivered", "busy", "no-answer", "canceled"}
        if status not in set(progression) | failures:
            raise Conflict("Unsupported provider status.")
        previous = self.store.resource("provider:" + provider_id, None)
        if previous in failures or previous in {"read", "delivered", "completed"}:
            return
        if (
            previous in progression
            and status in progression
            and progression.index(status) < progression.index(previous)
        ):
            return
        self.store.put_resource("provider:" + provider_id, status)
        for action in self.store.actions.values():
            changed = False
            for result in action.response.tool_results:
                if result.provider_id == provider_id:
                    result.provider_status = status
                    if status in failures:
                        result.ok = False
                        result.detail = "Provider reported an unsuccessful delivery or call."
                    changed = True
            for result in action.effects.values():
                if result.get("provider_id") == provider_id:
                    result["provider_status"] = status
                    if status in failures:
                        result["ok"] = False
                    changed = True
            if changed:
                if status in failures and action.response.status not in {
                    "canceled",
                    "declined",
                    "expired",
                }:
                    action.response.status = "failed"
                    action.response.error = "Provider reported a delivery failure. Review individual outcomes before retrying."
                    action.response.message = action.response.error
                action.checkpoint()

    def finish(self, action: Action, results: list[ToolResult]):
        self.record(action, results)
        ok = bool(results) and all(result.ok for result in results)
        action.response.status = "done" if ok else "failed"
        action.response.cancel_deadline_ms = None
        action.response.message = " ".join(result.detail for result in results)
        if not ok:
            action.response.error = "Some operations failed or have unknown outcomes. Review individual results before retrying."
        action.checkpoint()

    def undo(self, action_id: str):
        action = self.store.get(action_id)
        if action.response.status != "done" or action.response.undone:
            raise Conflict("Only a completed, unchanged device action can be undone once.")
        try:
            result = self.devices.undo(action)
        except ValueError as exc:
            raise Conflict(str(exc)) from None
        action.response.undone = True
        self.record(action, [result])
        return action.response.model_dump()

    def acknowledge(self, action_id: str):
        action = self.store.get(action_id)
        if action.request.button_id != "request_drink" or action.response.status != "done":
            raise Conflict("This action is not an active assistance request.")
        if action.response.acknowledged_at_ms is None:
            action.response.acknowledged_at_ms = int(time.time() * 1000)
            action.checkpoint()
        return action.response.model_dump()

    async def close(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*list(self.tasks), return_exceptions=True)
        await self.classifier.close()
        for action in self.store.actions.values():
            action.checkpoint()
        self.store.close()
