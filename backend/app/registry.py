from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ActionSpec:
    button_id: str
    label: str
    action_description: str
    policy_floor: int
    static_tier: int
    spends_money: bool = False
    touches_health_record: bool = False
    physical_access_change: bool = False


REGISTRY = MappingProxyType(
    {
        "text_home": ActionSpec(
            "text_home", "Text Home", "Send a casual check-in to family.", 1, 1
        ),
        "dim_lights": ActionSpec(
            "dim_lights", "Dim Lights", "Set room lights to 30 percent.", 1, 1
        ),
        "order_lunch": ActionSpec(
            "order_lunch",
            "Order Lunch",
            "Place the synthetic saved lunch order for $12.40.",
            2,
            2,
            spends_money=True,
        ),
        "emergency": ActionSpec(
            "emergency",
            "Emergency",
            "Request immediate help from the designated demo contact.",
            3,
            3,
        ),
    }
)
