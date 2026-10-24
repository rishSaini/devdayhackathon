import time
import uuid
from dataclasses import dataclass, field

from .schemas import ActionResponse, TapRequest
from .tools.delivery import SavedOrder

TERMINAL = {"done", "failed", "canceled", "declined", "expired"}


@dataclass
class Action:
    request: TapRequest
    response: ActionResponse
    created_monotonic: float = field(default_factory=time.monotonic)
    approval_deadline: float | None = None
    approved: bool = False
    order: SavedOrder | None = None


class ActionStore:
    """Event-loop-local state. Use one server worker; all state resets on restart."""

    def __init__(self):
        self.actions: dict[str, Action] = {}

    def create(self, request: TapRequest, tier: int) -> Action:
        action_id = "act_" + uuid.uuid4().hex[:12]
        action = Action(
            request,
            ActionResponse(
                action_id=action_id,
                status="executing" if request.button_id == "emergency" else "classifying",
                tier=tier,
                message="Preparing action; offline classification until a model result is available.",
            ),
        )
        self.actions[action_id] = action
        return action

    def get(self, action_id: str) -> Action:
        try:
            return self.actions[action_id]
        except KeyError:
            raise KeyError("Action not found.") from None
