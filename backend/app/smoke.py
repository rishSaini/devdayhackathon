"""Offline smoke check. This never enables models, SMS, or voice calls."""

import asyncio
import json
import time

from .config import Settings
from .registry import REGISTRY
from .schemas import TapRequest
from .service import Service


async def main():
    settings = Settings(
        _env_file=None,
        ripple_database_path=":memory:",
        ripple_live_models=False,
        ripple_live_twilio=False,
        ripple_cancel_window_s=0.01,
    )
    service = Service(settings)
    try:
        for button in REGISTRY:
            result = service.tap(
                TapRequest(
                    button_id=button,
                    timestamp=int(time.time() * 1000),
                    session_id="offline-smoke",
                    params={"severity": 4}
                    if button == "log_pain"
                    else {"elevation": 15}
                    if button == "reposition_bed"
                    else {},
                )
            )
            action = service.store.get(result["action_id"])
            async with asyncio.timeout(2):
                while action.response.status not in {"done", "failed"}:
                    if action.response.status == "awaiting_approval":
                        service.approve(action.response.action_id, True)
                    await asyncio.sleep(0.002)
            assert action.response.status == "done", action.response.message
            assert action.response.source == "mock"
            print(
                json.dumps(
                    {
                        "button_id": button,
                        "status": action.response.status,
                        "source": action.response.source,
                    }
                )
            )
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
