import json
from dataclasses import dataclass
from decimal import Decimal

from ..config import BACKEND_DIR
from ..schemas import ToolResult


@dataclass(frozen=True)
class SavedOrder:
    name: str
    details: str
    total: Decimal
    eta_minutes: int


def build_saved_order(order_name: str = "usual_lunch") -> SavedOrder:
    data = json.loads((BACKEND_DIR / "fixtures/saved_orders.json").read_text())
    order = data["orders"][order_name]
    if not order["synthetic"] or order["currency"] != "USD":
        raise ValueError("Only synthetic USD orders are supported.")
    total = Decimal(str(order["total_usd"]))
    if total <= 0:
        raise ValueError("Order total must be positive.")
    items = ", ".join(f"{item['quantity']} {item['name']}" for item in order["items"])
    return SavedOrder(order_name, f"{items}; ${total:.2f}", total, order["delivery_eta_minutes"])


async def finalize_order(order: SavedOrder, *, approved: bool) -> ToolResult:
    if not approved:
        return ToolResult(ok=False, source="mock", detail="Checkout blocked: approval is required.")
    return ToolResult(
        ok=True,
        source="mock",
        detail=f"Simulated checkout: ${order.total:.2f}; ETA {order.eta_minutes} minutes. No purchase occurred.",
    )
