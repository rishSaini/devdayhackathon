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
        "text_caregiver": ActionSpec(
            "text_caregiver",
            "Text Caregiver",
            "Send a user-selected message to the caregiver.",
            1,
            1,
        ),
        "set_temperature": ActionSpec(
            "set_temperature",
            "Set Temperature",
            "Set the simulated room thermostat within allowed bounds.",
            1,
            1,
        ),
        "log_pain": ActionSpec(
            "log_pain",
            "Log Pain",
            "Record the user's own reported pain severity in a simulated record.",
            2,
            2,
            touches_health_record=True,
        ),
        "reposition_bed": ActionSpec(
            "reposition_bed",
            "Adjust Bed Head",
            "Apply an explicitly selected simulated bed preset.",
            2,
            2,
        ),
        "request_drink": ActionSpec(
            "request_drink", "Request Drink", "Ask the caregiver for a drink of water.", 1, 1
        ),
        "unlock_door": ActionSpec(
            "unlock_door",
            "Unlock Front Door",
            "Grant a time-bounded simulated door access window, without emergency dispatch.",
            3,
            3,
            physical_access_change=True,
        ),
    }
)
