"""Read-only SDK planning over server-validated candidates; no execution tools."""

import asyncio
import hashlib
import json
from dataclasses import dataclass

from pydantic import BaseModel

from .config import Settings
from .schemas import Parameters, Plan, Profile, TapRequest
from .tools.delivery import build_saved_order


class Proposal(BaseModel):
    choice_id: str | None
    request_choice: bool


@dataclass
class PlanningResult:
    candidates: dict[str, Plan]
    selected: str | None
    source: str
    question: str


def plan(choice: str, summary: str, params: Parameters, steps: list[tuple[str, str]]) -> Plan:
    data = {
        "choice_id": choice,
        "summary": summary,
        "parameters": params.model_dump(),
        "steps": [{"tool": tool, "description": description} for tool, description in steps],
    }
    return Plan(
        **data, fingerprint=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    )


class Planner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def build(self, request: TapRequest, profile: Profile, devices: dict) -> PlanningResult:
        button = request.button_id
        params = request.params.model_copy(deep=True)
        candidates = {}
        needs_input = False
        question = "Choose an option."
        if button == "order_lunch":
            for key in ("usual_lunch", "soup_lunch", "vegetarian_lunch"):
                order = build_saved_order(key)
                if key not in profile.unavailable_orders and order.total <= profile.budget_amount:
                    candidates[key] = plan(
                        key,
                        order.details,
                        Parameters(order_name=key),
                        [
                            ("build_saved_order", "Prepare this exact synthetic order"),
                            ("twilio_send_approval_text", "Request approval for this order"),
                            ("finalize_order", "Finalize only after approval"),
                        ],
                    )
            preferred = params.order_name or profile.preferred_order
            needs_input = preferred not in candidates
            selected = preferred if not needs_input else None
            question = (
                "Your selected lunch is unavailable or exceeds your budget. Choose an alternative."
            )
        elif button == "log_pain":
            needs_input = params.severity is None
            for severity in range(11) if needs_input else [params.severity]:
                key = str(severity)
                candidates[key] = plan(
                    key,
                    f"Record your reported pain: {severity}/10",
                    Parameters(severity=severity, notes=params.notes),
                    [("record_pain", "Save your report after approval")],
                )
            selected = None if needs_input else str(params.severity)
            question = "What pain level do you want to record?"
        elif button == "reposition_bed":
            needs_input = params.elevation is None
            for elevation in (0, 15, 30) if needs_input else [params.elevation]:
                key = str(elevation)
                candidates[key] = plan(
                    key,
                    f"Simulated bed head: {elevation} degrees",
                    Parameters(elevation=elevation),
                    [("set_bed", "Apply and verify the simulated position after approval")],
                )
            selected = None if needs_input else str(params.elevation)
            question = "Choose a simulated bed position."
        else:
            if button in {"text_home", "text_caregiver"}:
                params.message = params.message or (
                    profile.home_message if button == "text_home" else profile.caregiver_message
                )
                summary = "Send your selected message to " + (
                    "home" if button == "text_home" else "your caregiver"
                )
                steps = [("send_sms", "Send only the selected message to the configured contact")]
            elif button == "dim_lights":
                params.brightness = (
                    profile.brightness if params.brightness is None else params.brightness
                )
                summary = f"Set simulated room lights to {params.brightness}%"
                steps = [("set_lights", "Apply the setting and verify device state")]
            elif button == "set_temperature":
                params.temperature_f = params.temperature_f or profile.temperature_f
                summary = f"Set simulated room temperature to {params.temperature_f} F"
                steps = [("set_temperature", "Apply the setting and verify device state")]
            elif button == "request_drink":
                summary = "Ask your caregiver for a drink of water"
                steps = [("request_drink", "Send the request and await separate acknowledgement")]
            elif button == "unlock_door":
                summary = "Grant a simulated 15-minute door access window"
                steps = [("unlock_door", "Apply simulated access only after approval")]
            else:
                raise ValueError("Action has no planning capability.")
            selected = "requested"
            candidates[selected] = plan(selected, summary, params, steps)
        if not candidates:
            raise ValueError("No available option meets your configured limits.")
        source = "fallback"
        if self.settings.models_configured and self.settings.ripple_agent_model:
            try:
                from agents import Agent, ModelSettings, RunConfig, Runner, function_tool
                from agents.models.openai_responses import OpenAIResponsesModel
                from openai import AsyncOpenAI

                context_read = False

                async def read_context() -> dict:
                    """Read allowed candidate plans and current simulated device state. No writes."""
                    nonlocal context_read
                    context_read = True
                    return {
                        "candidates": {
                            key: value.model_dump() for key, value in candidates.items()
                        },
                        "devices": devices,
                        "requires_user_choice": needs_input,
                        "requested_choice": selected,
                    }

                async with AsyncOpenAI(
                    api_key=self.settings.openai_api_key.get_secret_value(), max_retries=0
                ) as client:
                    agent = Agent(
                        name="Ripple read-only planner",
                        output_type=Proposal,
                        instructions="Call read_context. Return only a listed choice. Preserve requested_choice when present. If requires_user_choice is true, request the user's choice. Never invent alternatives or execute actions.",
                        model=OpenAIResponsesModel(self.settings.ripple_agent_model, client),
                        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
                        tools=[function_tool(read_context)],
                    )
                    async with asyncio.timeout(self.settings.ripple_agent_timeout_s):
                        result = await Runner.run(
                            agent,
                            "Plan the selected action using the provided context.",
                            max_turns=4,
                            run_config=RunConfig(tracing_disabled=True),
                        )
                    proposal = Proposal.model_validate(result.final_output)
                    if not context_read:
                        raise ValueError("Planner did not read the available context.")
                    if proposal.request_choice or needs_input:
                        selected = None
                    elif proposal.choice_id != selected or proposal.choice_id not in candidates:
                        raise ValueError("Planner changed explicit user intent.")
                    source = "live"
            except Exception:
                source = "fallback"
        return PlanningResult(candidates, selected, source, question)
