import time

import pytest

from app.config import Settings
from app.schemas import TapRequest


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        ripple_database_path=":memory:",
        ripple_user_token=None,
        ripple_caregiver_token=None,
        openai_api_key=None,
        ripple_live_models=False,
        ripple_live_twilio=False,
        ripple_demo_approval=True,
        ripple_cancel_window_s=0.02,
        ripple_approval_timeout_s=0.2,
        ripple_decisions_timeout_s=0.02,
        ripple_tool_timeout_s=0.1,
    )


def tap(button="order_lunch", timestamp=None, session="test-session"):
    return TapRequest(
        button_id=button,
        timestamp=timestamp or int(time.time() * 1000),
        session_id=session,
    )
