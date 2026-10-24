from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ALIASES = {
    "order_doordash": "order_lunch",
    "emergency_sos": "emergency",
    "adjust_thermostat": "set_temperature",
    "water_assistance": "request_drink",
}
Button = Literal[
    "text_home",
    "dim_lights",
    "order_lunch",
    "emergency",
    "text_caregiver",
    "set_temperature",
    "log_pain",
    "reposition_bed",
    "request_drink",
    "unlock_door",
    "order_doordash",
    "emergency_sos",
    "adjust_thermostat",
    "water_assistance",
]

Source = Literal["live", "fallback", "mock"]
ActionStatus = Literal[
    "pending_cancel",
    "classifying",
    "executing",
    "awaiting_approval",
    "done",
    "failed",
    "canceled",
    "declined",
    "expired",
    "awaiting_input",
]


class ButtonId(str, Enum):
    TEXT_HOME = "text_home"
    DIM_LIGHTS = "dim_lights"
    ORDER_LUNCH = "order_lunch"
    EMERGENCY = "emergency"
    TEXT_CAREGIVER = "text_caregiver"
    SET_TEMPERATURE = "set_temperature"
    LOG_PAIN = "log_pain"
    REPOSITION_BED = "reposition_bed"
    REQUEST_DRINK = "request_drink"
    UNLOCK_DOOR = "unlock_door"


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: str | None = Field(default=None, min_length=1, max_length=160)
    brightness: int | None = Field(default=None, ge=0, le=100)
    temperature_f: int | None = Field(default=None, ge=60, le=80)
    elevation: int | None = Field(default=None, ge=0, le=45)
    severity: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=500)
    order_name: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def nonempty_message(self):
        if self.message is not None and not self.message.strip():
            raise ValueError("A message must contain text.")
        return self


class TapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    button_id: Button
    timestamp: int = Field(gt=0)
    session_id: str = Field(min_length=1, max_length=64)
    location: Location | None = None
    params: Parameters = Field(default_factory=Parameters)

    @model_validator(mode="after")
    def validate_parameters(self):
        self.button_id = ALIASES.get(self.button_id, self.button_id)
        allowed = {
            "text_home": {"message"},
            "text_caregiver": {"message"},
            "dim_lights": {"brightness"},
            "set_temperature": {"temperature_f"},
            "reposition_bed": {"elevation"},
            "log_pain": {"severity", "notes"},
            "order_lunch": {"order_name"},
        }.get(self.button_id, set())
        if any(
            value is not None and key not in allowed
            for key, value in self.params.model_dump().items()
        ):
            raise ValueError("Parameters do not match the selected action.")
        return self


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str = Field(default="Alex", min_length=1, max_length=80)
    home_message: str = Field(
        default="Thinking of you. Please call when you can.", min_length=1, max_length=160
    )
    caregiver_message: str = Field(
        default="Please check in with me when you can.", min_length=1, max_length=160
    )
    brightness: int = Field(default=30, ge=0, le=100)
    temperature_f: int = Field(default=72, ge=60, le=80)
    preferred_order: str = Field(default="usual_lunch", min_length=1, max_length=64)
    lunch_budget: float = Field(default=20, gt=0, le=100, allow_inf_nan=False)
    unavailable_orders: list[Literal["usual_lunch", "soup_lunch", "vegetarian_lunch"]] = Field(
        default_factory=list, max_length=3
    )

    @property
    def budget_amount(self) -> Decimal:
        return Decimal(str(self.lunch_budget))


class PlanStep(BaseModel):
    tool: str
    description: str


class Plan(BaseModel):
    choice_id: str
    summary: str
    parameters: Parameters
    steps: list[PlanStep]
    fingerprint: str


class Choice(BaseModel):
    id: str
    label: str


class Clarification(BaseModel):
    id: str
    question: str
    choices: list[Choice]
    expires_at_ms: int


class ChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    clarification_id: str
    choice_id: str


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approved: bool
    fingerprint: str


class ToolResult(BaseModel):
    ok: bool
    source: Source
    detail: str
    provider_id: str | None = None
    provider_status: str | None = None
    operation: str | None = None
    observed: dict = Field(default_factory=dict)


class ActionResponse(BaseModel):
    action_id: str
    status: ActionStatus
    tier: int = Field(ge=1, le=3)
    tier_source: Source = "fallback"
    confidence: float | None = None
    model_tier: int | None = Field(default=None, ge=1, le=3)
    classification_fallback_reason: str | None = None
    cancel_deadline_ms: int | None = None
    source: Source = "mock"
    message: str
    error: str | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    button_id: str | None = None
    session_id: str | None = None
    plan: Plan | None = None
    planning_source: Source = "fallback"
    clarification: Clarification | None = None
    approval_fingerprint: str | None = None
    approval_expires_at_ms: int | None = None
    acknowledged_at_ms: int | None = None
    undone: bool = False
    emergency_followup_status: Literal["pending", "done", "failed"] | None = None
