import time
from collections.abc import Callable


class SpasmFilter:
    """Only accepted taps advance the window. Call before any async operation."""

    def __init__(self, window_ms: int = 400, monotonic: Callable[[], float] = time.monotonic):
        self.window_ms = window_ms
        self.monotonic = monotonic
        self.accepted: dict[tuple[str, str], tuple[int, float]] = {}

    def should_drop(self, session_id: str, button_id: str, timestamp: int) -> bool:
        now = self.monotonic()
        key = session_id, button_id
        previous = self.accepted.get(key)
        if previous is not None:
            client_gap = timestamp - previous[0]
            gap = client_gap if client_gap >= 0 else (now - previous[1]) * 1000
            if gap < self.window_ms:
                return True
        self.accepted[key] = timestamp, now
        return False
