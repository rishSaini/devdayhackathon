"""Persisted simulated devices. No hardware integration is performed."""

import time

from .schemas import ToolResult
from .store import Action, ActionStore


class Devices:
    def __init__(self, store: ActionStore):
        self.store = store

    def read(self):
        state = self.store.resource(
            "devices",
            {
                "brightness": 80,
                "temperature_f": 72,
                "elevation": 0,
                "unlock_until_ms": 0,
                "versions": {
                    "brightness": 0,
                    "temperature_f": 0,
                    "elevation": 0,
                    "unlock_until_ms": 0,
                },
            },
        )
        state["door_unlocked"] = state["unlock_until_ms"] > int(time.time() * 1000)
        return state

    async def apply(self, action: Action, key: str, value: int) -> ToolResult:
        state = self.read()
        # A durable device write is owned by this action, allowing idempotent recovery.
        receipt = self.store.resource("device_receipt:" + action.response.action_id, None)
        if receipt:
            return ToolResult.model_validate(receipt)
        action.previous_device = {
            "key": key,
            "value": state[key],
            "version": state["versions"][key] + 1,
        }
        action.checkpoint()
        state[key] = value
        state["versions"][key] += 1
        self.store.put_resource("devices", state)
        observed = self.read()
        result = ToolResult(
            ok=observed[key] == value,
            source="mock",
            operation=key,
            detail=f"Simulated device: {key} set to {value}; state verified.",
            observed={key: observed[key]},
        )
        self.store.put_resource("device_receipt:" + action.response.action_id, result.model_dump())
        return result

    def undo(self, action: Action) -> ToolResult:
        before = action.previous_device
        if not before or before["key"] not in {"brightness", "temperature_f"}:
            raise ValueError("This action does not support undo.")
        state = self.read()
        key = before["key"]
        if state["versions"][key] != before["version"]:
            raise ValueError(
                "Device changed after this action; undo would overwrite a newer change."
            )
        state[key] = before["value"]
        state["versions"][key] += 1
        self.store.put_resource("devices", state)
        return ToolResult(
            ok=True,
            source="mock",
            detail="Simulated device restored; state verified.",
            observed={key: state[key]},
        )

    async def unlock(self, action: Action) -> ToolResult:
        return await self.apply(action, "unlock_until_ms", int(time.time() * 1000) + 15 * 60 * 1000)

    async def log_pain(self, action: Action) -> ToolResult:
        params = action.response.plan.parameters
        records = self.store.resource("medical_records", [])
        if not any(record["action_id"] == action.response.action_id for record in records):
            records.append(
                {
                    "action_id": action.response.action_id,
                    "severity": params.severity,
                    "notes": params.notes,
                    "source": "mock",
                    "created_at_ms": int(time.time() * 1000),
                }
            )
            self.store.put_resource("medical_records", records)
        return ToolResult(
            ok=True,
            source="mock",
            detail="User-reported pain saved to a simulated record. No clinical record changed.",
            observed={"severity": params.severity},
        )
