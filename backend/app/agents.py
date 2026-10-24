"""Per-phase Agents SDK tools, with fixed recipients and server-owned parameters.

The project uses the local Agents SDK, not the hosted Agents API.
Tool results, never the model's final prose, determine execution success.
"""

import asyncio
from collections.abc import Awaitable, Callable

from .config import Settings
from .devices import Devices
from .integrations import Messaging
from .schemas import Profile, ToolResult
from .store import TERMINAL, Action
from .tools import delivery, home, medical


class Executor:
    def __init__(self, settings: Settings, messaging: Messaging, devices: Devices | None = None):
        self.settings = settings
        self.messaging = messaging
        self.devices = devices

    async def run(
        self, action: Action, phase: str, ready: Callable[[], None] | None = None
    ) -> list[ToolResult]:
        results: dict[str, ToolResult] = {}

        async def once(name: str, operation: Callable[[], Awaitable[ToolResult]]) -> ToolResult:
            if name not in results:
                effect_key = phase + "." + name
                if effect_key in action.effects:
                    results[name] = ToolResult.model_validate(action.effects[effect_key])
                    return results[name]
                if action.response.status in TERMINAL and not (
                    phase == "emergency" and action.response.status in {"done", "failed"}
                ):
                    return ToolResult(ok=False, source="mock", detail="Action is no longer active.")
                # Insert before the first await, preventing concurrent duplicate tool calls.
                tool_source = (
                    self.messaging.mode
                    if name in {"send_sms", "twilio_send_approval_text", "request_drink"}
                    else "mock"
                )
                results[name] = ToolResult(
                    ok=False,
                    source=tool_source,
                    detail="Tool did not complete; outcome may be unknown.",
                )
                action.effects[effect_key] = results[name].model_dump()
                action.checkpoint()
                try:
                    async with asyncio.timeout(self.settings.ripple_tool_timeout_s):
                        results[name] = await operation()
                except Exception:
                    results[name] = ToolResult(
                        ok=False, source=tool_source, detail="Tool failed; outcome may be unknown."
                    )
                results[name].operation = results[name].operation or name
                action.effects[effect_key] = results[name].model_dump()
                action.checkpoint()
            return results[name]

        async def send_sms(body: str) -> dict:
            """Send one brief casual message to the server-configured home contact."""
            if not body.strip() or len(body) > 160:
                return {"ok": False, "detail": "Use a nonempty message of at most 160 characters."}
            if action.response.plan and body != action.response.plan.parameters.message:
                return {"ok": False, "detail": "Preserve the exact user-selected message."}
            return (
                await once(
                    "send_sms",
                    lambda: self.messaging.send_sms(
                        self.settings.caregiver_phone
                        if action.request.button_id == "text_caregiver"
                        else self.settings.home_phone,
                        body,
                    ),
                )
            ).model_dump()

        async def set_lights() -> dict:
            """Set the simulated room lights to the preset 30 percent."""
            level = action.response.plan.parameters.brightness if action.response.plan else 30
            return (
                await once(
                    "set_lights",
                    lambda: (
                        self.devices.apply(action, "brightness", level)
                        if self.devices
                        else home.set_lights(level)
                    ),
                )
            ).model_dump()

        async def finalize_order() -> dict:
            """Finalize only the exact saved order previously approved by the co-signer."""
            if not action.approved or action.order is None or action.response.status != "executing":
                return {"ok": False, "detail": "Approval required."}
            if (
                action.response.plan
                and action.response.approval_fingerprint != action.fingerprint()
            ):
                return {"ok": False, "detail": "The approved plan changed."}
            if self.devices:
                profile = Profile.model_validate(
                    self.devices.store.resource("profile", Profile().model_dump())
                )
                if (
                    action.order.total > profile.budget_amount
                    or action.order.name in profile.unavailable_orders
                ):
                    return {
                        "ok": False,
                        "detail": "Order no longer meets the current budget or availability limits.",
                    }
            return (
                await once(
                    "finalize_order", lambda: delivery.finalize_order(action.order, approved=True)
                )
            ).model_dump()

        async def build_saved_order() -> dict:
            """Read the server's fixed synthetic lunch order; do this before requesting approval."""

            async def build():
                action.order = delivery.build_saved_order(
                    action.response.plan.parameters.order_name
                    if action.response.plan
                    else "usual_lunch"
                )
                if action.response.plan and action.order.details != action.response.plan.summary:
                    raise ValueError("Saved order changed after planning.")
                return ToolResult(
                    ok=True, source="mock", detail=f"Synthetic saved order: {action.order.details}."
                )

            return (await once("build_saved_order", build)).model_dump()

        async def twilio_send_approval_text() -> dict:
            """Request co-signer approval for the exact saved order. Does not finalize it."""
            if action.order is None:
                return {"ok": False, "detail": "Build the saved order first."}

            async def send():
                if ready is not None:
                    ready()
                return await self.messaging.send_approval(
                    self.settings.caregiver_phone,
                    action.response.action_id,
                    action.order.details,
                )

            return (await once("twilio_send_approval_text", send)).model_dump()

        async def prepare_fallback():
            await build_saved_order()
            await twilio_send_approval_text()

        async def emergency_followup() -> dict:
            """Record a simulated emergency follow-up after deterministic contact dispatch."""
            return (await once("log_medical_event", medical.log_medical_event)).model_dump()

        async def smart_lock_grant_access() -> dict:
            """Grant a simulated 15-minute emergency access window. Never operates a real lock."""
            return (
                await once(
                    "smart_lock_grant_access",
                    lambda: (
                        self.devices.unlock(action)
                        if self.devices
                        else home.smart_lock_grant_access()
                    ),
                )
            ).model_dump()

        async def emergency_fallback():
            await emergency_followup()
            await smart_lock_grant_access()

        async def text_fallback():
            return await send_sms(
                action.response.plan.parameters.message
                if action.response.plan
                else f"Hi, it's {self.settings.user_display_name}. Thinking of you. Call when you can."
            )

        async def set_temperature() -> dict:
            """Apply and verify the exact planned simulated thermostat setting."""
            return (
                await once(
                    "set_temperature",
                    lambda: self.devices.apply(
                        action, "temperature_f", action.response.plan.parameters.temperature_f
                    ),
                )
            ).model_dump()

        async def set_bed() -> dict:
            """Apply the approved simulated bed position; never operates real hardware."""
            if not action.approved:
                return {"ok": False, "detail": "Approval required."}
            return (
                await once(
                    "set_bed",
                    lambda: self.devices.apply(
                        action, "elevation", action.response.plan.parameters.elevation
                    ),
                )
            ).model_dump()

        async def record_pain() -> dict:
            """Save the approved user-reported severity to a simulated record."""
            if not action.approved:
                return {"ok": False, "detail": "Approval required."}
            return (await once("record_pain", lambda: self.devices.log_pain(action))).model_dump()

        async def unlock_door() -> dict:
            """Grant approved simulated access for fifteen minutes without emergency dispatch."""
            if not action.approved:
                return {"ok": False, "detail": "Approval required."}
            return (await once("unlock_door", lambda: self.devices.unlock(action))).model_dump()

        async def request_drink() -> dict:
            """Send one water assistance request to the configured caregiver."""
            return (
                await once(
                    "request_drink",
                    lambda: self.messaging.send_sms(
                        self.settings.caregiver_phone, "Please bring me a drink of water."
                    ),
                )
            ).model_dump()

        if phase == "prepare" and action.request.button_id == "order_lunch":
            operations = [build_saved_order, twilio_send_approval_text]
            prompt = "Call build_saved_order, then twilio_send_approval_text once. Stop after requesting approval."
            fallback = prepare_fallback
            required = {"build_saved_order", "twilio_send_approval_text"}
        elif phase == "finalize" and action.request.button_id == "order_lunch" and action.approved:
            operations = [finalize_order]
            prompt = "Call finalize_order once for the previously approved saved order. Report its result."
            fallback = finalize_order
            required = {"finalize_order"}
        elif phase == "emergency" and action.request.button_id == "emergency":
            operations = [emergency_followup, smart_lock_grant_access]
            prompt = "Call emergency_followup and smart_lock_grant_access once. Contact dispatch was handled separately in code."
            fallback = emergency_fallback
            required = {"log_medical_event", "smart_lock_grant_access"}
        elif phase == "execute" and action.request.button_id in {"text_home", "text_caregiver"}:
            operations = [send_sms]
            prompt = "Draft a casual family check-in under 160 characters, then call send_sms once."
            fallback = text_fallback
            required = {"send_sms"}
            if action.response.plan:
                import json

                prompt = (
                    "Call send_sms once with exactly this user-selected message: "
                    + json.dumps(action.response.plan.parameters.message)
                )
        elif phase == "execute" and action.request.button_id == "dim_lights":
            operations = [set_lights]
            prompt = "Call set_lights once, then report the simulated result."
            fallback = set_lights
            required = {"set_lights"}
        elif (
            phase == "execute"
            and self.devices
            and action.response.plan
            and action.request.button_id
            in {"set_temperature", "reposition_bed", "log_pain", "unlock_door", "request_drink"}
        ):
            operation = {
                "set_temperature": set_temperature,
                "reposition_bed": set_bed,
                "log_pain": record_pain,
                "unlock_door": unlock_door,
                "request_drink": request_drink,
            }[action.request.button_id]
            operations = [operation]
            prompt = f"Call {operation.__name__} once for the validated plan. Report only its tool result."
            fallback = operation
            required = {operation.__name__}
        else:
            return [
                ToolResult(
                    ok=False,
                    source="mock",
                    detail="Operation is outside this action's capabilities.",
                )
            ]

        live = self.settings.models_configured and bool(self.settings.ripple_agent_model)
        if live:
            try:
                from agents import Agent, ModelSettings, RunConfig, Runner, function_tool
                from agents.models.openai_responses import OpenAIResponsesModel
                from openai import AsyncOpenAI

                async with AsyncOpenAI(
                    api_key=self.settings.openai_api_key.get_secret_value(),
                    max_retries=0,
                ) as client:
                    agent = Agent(
                        name=f"Ripple {phase} {action.request.button_id}",
                        instructions="Use only the provided tool to complete the task. Never claim success without a successful tool result.",
                        model=OpenAIResponsesModel(self.settings.ripple_agent_model, client),
                        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
                        tools=[function_tool(operation) for operation in operations],
                    )
                    async with asyncio.timeout(self.settings.ripple_agent_timeout_s):
                        await Runner.run(
                            agent, prompt, max_turns=4, run_config=RunConfig(tracing_disabled=True)
                        )
                if not results:
                    return [
                        ToolResult(
                            ok=False,
                            source="live",
                            detail="Agent did not complete the required tool call.",
                        )
                    ]
            except Exception:
                # Never repeat a tool that may already have sent an external request.
                if not results:
                    await fallback()
                results["agent_fallback"] = ToolResult(
                    ok=True,
                    source="fallback",
                    detail="Agent unavailable; template execution used or prior tool result retained.",
                )
        else:
            await fallback()
            results["agent_fallback"] = ToolResult(
                ok=True,
                source="fallback",
                detail="Offline template execution; no model was called.",
            )
        if not required.issubset(results):
            results["incomplete"] = ToolResult(
                ok=False, source="fallback", detail="Required tool sequence did not complete."
            )
        return list(results.values())
