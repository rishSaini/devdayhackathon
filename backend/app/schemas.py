from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
]


class ButtonId(str, Enum):
    TEXT_HOME = "text_home"
    DIM_LIGHTS = "dim_lights"
    ORDER_LUNCH = "order_lunch"
    EMERGENCY = "emergency"


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class TapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    button_id: Literal["text_home", "dim_lights", "order_lunch", "emergency"]
    timestamp: int = Field(gt=0)
    session_id: str = Field(min_length=1, max_length=64)
    location: Location | None = None


class ToolResult(BaseModel):
    ok: bool
    source: Source
    detail: str


class ActionResponse(BaseModel):
    action_id: str
    status: ActionStatus
    tier: int = Field(ge=1, le=3)
    tier_source: Source = "fallback"
    confidence: float | None = None
    cancel_deadline_ms: int | None = None
    source: Source = "mock"
    message: str
    error: str | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
