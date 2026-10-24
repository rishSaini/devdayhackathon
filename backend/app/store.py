"""SQLite checkpoints for a single resident and one server worker."""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

from .schemas import ActionResponse, Plan, TapRequest
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
    created_at: float = field(default_factory=time.time)
    candidates: dict[str, Plan] = field(default_factory=dict)
    effects: dict = field(default_factory=dict)
    previous_device: dict | None = None
    checkpoint: Callable[[], None] = field(default=lambda: None, repr=False)

    def fingerprint(self) -> str:
        data = {
            "plan": self.response.plan.model_dump() if self.response.plan else None,
            "order": asdict(self.order) if self.order else None,
            "button": self.request.button_id,
            "action_id": self.response.action_id,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


class ActionStore:
    def __init__(self, path: str = ":memory:"):
        self.lock_file = None
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
            self.lock_file = os.fdopen(descriptor, "a+b")
            try:
                if os.name == "nt":
                    import msvcrt

                    if not self.lock_file.tell():
                        self.lock_file.write(b"0")
                        self.lock_file.flush()
                    self.lock_file.seek(0)
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.lock_file.close()
                raise RuntimeError(
                    "This database already has a server worker. Use exactly one worker."
                ) from None
        self.db = sqlite3.connect(path, check_same_thread=False)
        if path != ":memory:":
            os.chmod(path, 0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS resources (key TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.execute("CREATE TABLE IF NOT EXISTS webhooks (id TEXT PRIMARY KEY)")
        self.db.commit()
        self.transaction_depth = 0
        self.actions: dict[str, Action] = {}
        for _, raw in self.db.execute("SELECT id, body FROM actions"):
            data = json.loads(raw)
            order = data["order"]
            if order:
                order["total"] = Decimal(order["total"])
            action = Action(
                request=TapRequest.model_validate(data["request"]),
                response=ActionResponse.model_validate(data["response"]),
                created_monotonic=time.monotonic() - max(0, time.time() - data["created_at"]),
                created_at=data["created_at"],
                approved=data["approved"],
                order=SavedOrder(**order) if order else None,
                candidates={
                    key: Plan.model_validate(value)
                    for key, value in data.get("candidates", {}).items()
                },
                effects=data.get("effects", {}),
                previous_device=data.get("previous_device"),
            )
            deadline = action.response.approval_expires_at_ms
            if deadline:
                action.approval_deadline = time.monotonic() + (deadline / 1000 - time.time())
            self.bind(action)

    def bind(self, action: Action):
        self.actions[action.response.action_id] = action
        action.checkpoint = lambda: self.save(action)

    def save(self, action: Action):
        order = asdict(action.order) if action.order else None
        if order:
            order["total"] = str(order["total"])
        body = json.dumps(
            {
                "request": action.request.model_dump(),
                "response": action.response.model_dump(),
                "created_at": action.created_at,
                "approved": action.approved,
                "order": order,
                "candidates": {key: value.model_dump() for key, value in action.candidates.items()},
                "effects": action.effects,
                "previous_device": action.previous_device,
            }
        )
        self.write(
            "INSERT OR REPLACE INTO actions VALUES (?, ?)", (action.response.action_id, body)
        )

    def write(self, sql: str, values: tuple):
        self.db.execute(sql, values)
        if not self.transaction_depth:
            self.db.commit()

    @contextmanager
    def transaction(self):
        if self.transaction_depth:
            raise RuntimeError("Nested workflow transactions are not supported.")
        self.db.execute("BEGIN IMMEDIATE")
        self.transaction_depth += 1
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        finally:
            self.transaction_depth -= 1

    def create(self, request: TapRequest, tier: int) -> Action:
        action = Action(
            request,
            ActionResponse(
                action_id="act_" + uuid.uuid4().hex[:12],
                button_id=request.button_id,
                session_id=request.session_id,
                status="executing" if request.button_id == "emergency" else "classifying",
                tier=tier,
                message="Preparing the selected action.",
            ),
        )
        self.bind(action)
        self.save(action)
        return action

    def get(self, action_id: str) -> Action:
        try:
            return self.actions[action_id]
        except KeyError:
            raise KeyError("Action not found.") from None

    def resource(self, key: str, default):
        row = self.db.execute("SELECT body FROM resources WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put_resource(self, key: str, value):
        self.write("INSERT OR REPLACE INTO resources VALUES (?, ?)", (key, json.dumps(value)))

    def webhook_seen(self, message_id: str) -> bool:
        return (
            self.db.execute("SELECT 1 FROM webhooks WHERE id=?", (message_id,)).fetchone()
            is not None
        )

    def remember_webhook(self, message_id: str):
        self.write("INSERT OR IGNORE INTO webhooks VALUES (?)", (message_id,))

    def close(self):
        self.db.close()
        if self.lock_file:
            self.lock_file.close()
