"""Offline smoke check. This never enables models, SMS, or voice calls."""

import asyncio
import json
import time

from .config import Settings
from .schemas import TapRequest
from .service import Service


async def main():
    settings = Settings(
        _env_file=None,
        ripple_live_models=False,
        ripple_live_twilio=False,
        ripple_cancel_window_s=0.01,
    )
    service = Service(settings)
    try:
        for button in ("text_home", "dim_lights", "order_lunch", "emergency"):
            result = service.tap(
                TapRequest(
                    button_id=button,
                    timestamp=int(time.time() * 1000),
                    session_id="offline-smoke",
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
