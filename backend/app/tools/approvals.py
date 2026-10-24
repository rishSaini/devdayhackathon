"""Short-lived in-memory approval tokens for the Tier 2 SMS flow."""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class PendingApproval:
    action_id: str
    caregiver_phone: str
    code: str
    expires_at: float


class PendingApprovalStore:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl = ttl_seconds
        self._items: dict[str, PendingApproval] = {}
        self._lock = asyncio.Lock()

    async def register(self, action_id: str, caregiver_phone: str) -> PendingApproval:
        async with self._lock:
            self._purge_expired()
            existing_codes = {item.code for item in self._items.values() if item.caregiver_phone == caregiver_phone}
            available = [f"{n:02d}" for n in range(100) if f"{n:02d}" not in existing_codes]
            if not available:
                raise RuntimeError("Too many pending approvals for this caregiver")
            code = secrets.choice(available)
            item = PendingApproval(action_id, caregiver_phone, code, time.monotonic() + self._ttl)
            self._items[action_id] = item
            return item

    async def discard(self, action_id: str) -> None:
        async with self._lock:
            self._items.pop(action_id, None)

    async def resolve(self, sender: str, reply: str) -> tuple[str, str] | None:
        """Return (action_id, YES|NO); reject ambiguous, expired, or unauthorized replies."""
        tokens = reply.strip().upper().split()
        if len(tokens) not in (1, 2) or tokens[0] not in {"YES", "NO"}:
            return None
        decision, code = tokens[0], tokens[1] if len(tokens) == 2 else None
        async with self._lock:
            self._purge_expired()
            matches = [
                item for item in self._items.values()
                if item.caregiver_phone == sender and (item.code == code if code else True)
            ]
            if len(matches) != 1:
                return None
            match = matches[0]
            del self._items[match.action_id]
            return match.action_id, decision

    async def pending_for(self, caregiver_phone: str) -> int:
        async with self._lock:
            self._purge_expired()
            return sum(item.caregiver_phone == caregiver_phone for item in self._items.values())

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, item in self._items.items() if item.expires_at <= now]
        for key in expired:
            del self._items[key]


pending_approvals = PendingApprovalStore()
