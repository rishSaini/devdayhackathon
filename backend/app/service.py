import asyncio
import time
from collections.abc import Awaitable

from .agents import Executor
from .config import Settings
from .decisions import Classifier
from .integrations import Messaging, MockMessaging
from .registry import REGISTRY
from .schemas import Location, TapRequest, ToolResult
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
        self.classifier = classifier or Classifier(settings)
        self.executor = executor or Executor(settings, self.messaging)
        self.store = ActionStore()
        self.spasm_filter = SpasmFilter(settings.ripple_spasm_window_ms)
        self.tasks: set[asyncio.Task] = set()
        self.processed_webhooks: set[str] = set()

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

        task = asyncio.create_task(guarded())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def tap(self, request: TapRequest) -> dict:
        if self.spasm_filter.should_drop(request.session_id, request.button_id, request.timestamp):
            return {"status": "debounced"}
        spec = REGISTRY[request.button_id]
        action = self.store.create(request, spec.policy_floor)
        if request.button_id == "emergency":
            # Spawn dispatch first, independently of classification and its timeout.
            self.spawn(self.emergency(action), action)
            self.spawn(self.classify(action), action)
        else:
            if spec.static_tier == 1:
                action.response.status = "pending_cancel"
                action.response.cancel_deadline_ms = int(
                    time.time() * 1000 + self.settings.ripple_cancel_window_s * 1000
                )
            self.spawn(self.prepare(action), action)
        return action.response.model_dump()

    async def classify(self, action: Action):
        spec = REGISTRY[action.request.button_id]
        result = await self.classifier.classify(spec)
        action.response.tier = max(spec.policy_floor, result.tier)
        action.response.tier_source = result.source
        action.response.confidence = result.confidence

    async def prepare(self, action: Action):
        await self.classify(action)
        if action.response.status in TERMINAL:
            return
        if action.response.tier >= 2 or action.request.button_id == "order_lunch":
            # Escalation never grants emergency capabilities or bypasses purchase approval.
            action.response.cancel_deadline_ms = None
            if action.request.button_id == "order_lunch":
                results = await self.executor.run(
                    action, "prepare", lambda: self.await_approval(action)
                )
            else:
                self.await_approval(action)
                results = [
                    await self.safe_tool(
                        self.messaging.send_approval(
                            self.settings.caregiver_phone,
                            action.response.action_id,
                            REGISTRY[action.request.button_id].label,
                        )
                    )
                ]
            self.record(action, results)
            if action.response.status in {"classifying", "pending_cancel", "awaiting_approval"}:
                if not all(result.ok for result in results):
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
            return
        remaining = self.settings.ripple_cancel_window_s - (
            time.monotonic() - action.created_monotonic
        )
        await asyncio.sleep(max(0, remaining))
        if action.response.status in TERMINAL:
            return
        action.response.status = "executing"
        self.finish(action, await self.executor.run(action, "execute"))

    def await_approval(self, action: Action):
        if action.response.status in TERMINAL:
            raise Conflict("Action is no longer active.")
        action.response.status = "awaiting_approval"
        action.approval_deadline = time.monotonic() + self.settings.ripple_approval_timeout_s
        self.spawn(self.expire(action), action)

    async def expire(self, action: Action):
        await asyncio.sleep(max(0, action.approval_deadline - time.monotonic()))
        if action.response.status == "awaiting_approval":
            action.response.status = "expired"
            action.response.message = "Approval expired; nothing was finalized."

    def cancel(self, action_id: str) -> dict:
        action = self.store.get(action_id)
        if action.request.button_id == "emergency" or action.response.status not in {
            "pending_cancel",
            "classifying",
            "awaiting_approval",
        }:
            raise Conflict("Action can no longer be canceled.")
        action.response.status = "canceled"
        action.response.message = "Canceled; no further execution will start."
        action.response.cancel_deadline_ms = None
        return action.response.model_dump()

    def approve(self, action_id: str, approved: bool) -> dict:
        action = self.store.get(action_id)
        if action.response.status != "awaiting_approval":
            raise Conflict("Action is not awaiting approval.")
        if action.approval_deadline is None or time.monotonic() >= action.approval_deadline:
            action.response.status = "expired"
            action.response.message = "Approval expired; nothing was finalized."
            raise Conflict("Approval expired.")
        if not approved:
            action.response.status = "declined"
            action.response.message = "Declined; nothing was finalized."
        else:
            # Synchronous claim before any await: duplicate/replayed approvals cannot execute twice.
            action.approved = True
            action.response.status = "executing"
            action.response.message = "Approved; executing the requested action."
            self.spawn(self.finalize(action), action)
        return action.response.model_dump()

    async def finalize(self, action: Action):
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

    async def emergency(self, action: Action):
        location = action.request.location
        fallback_location = location is None
        location = location or Location(
            lat=self.settings.demo_fallback_lat, lng=self.settings.demo_fallback_lng
        )
        results = await asyncio.gather(
            self.safe_tool(
                self.messaging.voice_call(
                    self.settings.emergency_contact,
                    f"This is an automated Ripple demo alert. {self.settings.user_display_name} pressed the emergency button. Location follows by text.",
                )
            ),
            self.safe_tool(self.messaging.location_sms(self.settings.emergency_contact, location)),
        )
        self.finish(action, results)
        if fallback_location:
            action.response.message += " Used the fixed demo location; GPS was unavailable."
        # Follow-up failure does not hide independently recorded dispatch outcomes.
        followup = await self.executor.run(action, "emergency")
        self.record(action, followup)

    def record(self, action: Action, results: list[ToolResult]):
        action.response.tool_results.extend(results)
        # Any simulated operation means this is not an entirely live action.
        all_results = action.response.tool_results
        action.response.source = (
            "mock"
            if any(r.source == "mock" for r in all_results)
            else "fallback"
            if any(r.source == "fallback" for r in all_results)
            else "live"
        )

    def finish(self, action: Action, results: list[ToolResult]):
        self.record(action, results)
        ok = bool(results) and all(result.ok for result in results)
        action.response.status = "done" if ok else "failed"
        action.response.cancel_deadline_ms = None
        action.response.message = " ".join(result.detail for result in results)
        if not ok:
            action.response.error = "Some operations failed or have unknown outcomes. Review individual results before retrying."

    async def close(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*list(self.tasks), return_exceptions=True)
        await self.classifier.close()
