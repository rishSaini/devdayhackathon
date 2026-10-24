"""Rishabh can inject Twilio here without changing the state machine.

Implementations must not retry externally visible sends after ambiguous failures.
They must return ToolResult(ok=False, ...) on failure and enforce fixed recipients.
"""

import re
from typing import Protocol

from .schemas import Location, ToolResult


def validate_recipient(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if digits in {"911", "112", "999"}:
        raise ValueError("Emergency-services numbers are blocked in this prototype.")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
        raise ValueError("Configure a teammate-owned number in E.164 format.")
    return number


class Messaging(Protocol):
    mode: str

    async def send_sms(self, to: str, body: str) -> ToolResult: ...
    async def send_approval(self, to: str, action_id: str, details: str) -> ToolResult: ...
    async def voice_call(self, to: str, message: str) -> ToolResult: ...
    async def location_sms(
        self, to: str, location: Location, *, fallback: bool = False
    ) -> ToolResult: ...


class MockMessaging:
    mode = "mock"

    async def send_sms(self, to: str, body: str) -> ToolResult:
        return ToolResult(ok=True, source="mock", detail="Simulated SMS; nothing was sent.")

    async def send_approval(self, to: str, action_id: str, details: str) -> ToolResult:
        return ToolResult(
            ok=True, source="mock", detail="Simulated approval request; nothing was sent."
        )

    async def voice_call(self, to: str, message: str) -> ToolResult:
        return ToolResult(
            ok=True, source="mock", detail="Simulated voice call; no call was placed."
        )

    async def location_sms(
        self, to: str, location: Location, *, fallback: bool = False
    ) -> ToolResult:
        return ToolResult(
            ok=True, source="mock", detail="Simulated location SMS; no location was shared."
        )
