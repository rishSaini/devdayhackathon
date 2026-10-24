import time
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from test_backend_workflows import approve, submit, wait

from app.integrations import MockMessaging
from app.main import create_app
from app.schemas import Profile, TapRequest, ToolResult
from app.service import Service


def durable(settings, tmp_path):
    settings.ripple_database_path = str(tmp_path / "state.sqlite3")
    settings.ripple_approval_timeout_s = 10
    return settings


def test_pending_approval_and_profile_survive_restart(settings, tmp_path):
    durable(settings, tmp_path)
    with TestClient(create_app(settings)) as client:
        client.put("/profile", json=Profile(brightness=25).model_dump())
        action_id = submit(client, "order_lunch")
        pending = wait(client, action_id, "awaiting_approval")
    with TestClient(create_app(settings)) as client:
        restored = client.get("/actions/" + action_id).json()
        assert restored["approval_fingerprint"] == pending["approval_fingerprint"]
        assert client.get("/profile").json()["brightness"] == 25
        done = approve(client, action_id)
        assert sum("Simulated checkout" in r["detail"] for r in done["tool_results"]) == 1
        assert (
            client.post(
                "/actions/" + action_id + "/approval",
                json={"approved": True, "fingerprint": pending["approval_fingerprint"]},
            ).status_code
            == 409
        )


def test_clarification_survives_restart(settings, tmp_path):
    durable(settings, tmp_path)
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "log_pain")
        original = wait(client, action_id, "awaiting_input")
    with TestClient(create_app(settings)) as client:
        restored = client.get("/actions/" + action_id).json()
        assert restored["clarification"] == original["clarification"]
        response = client.post(
            "/actions/" + action_id + "/choice",
            json={"clarification_id": original["clarification"]["id"], "choice_id": "6"},
        )
        assert response.status_code == 202
        approve(client, action_id)
        assert client.get("/medical-records").json()["records"][0]["severity"] == 6


def test_restart_expires_old_approval(settings, tmp_path):
    durable(settings, tmp_path)
    settings.ripple_approval_timeout_s = 0.03
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "order_lunch")
        wait(client, action_id, "awaiting_approval")
    time.sleep(0.04)
    with TestClient(create_app(settings)) as client:
        action = wait(client, action_id, "expired")
        assert not any("checkout" in result["detail"] for result in action["tool_results"])


async def test_unknown_interrupted_send_is_never_replayed(settings, tmp_path):
    durable(settings, tmp_path)
    original = Service(settings)
    action = original.store.create(
        TapRequest(button_id="text_home", timestamp=1000, session_id="same-device"), 1
    )
    action.response.status = "executing"
    action.effects["execute.send_sms"] = ToolResult(
        ok=False, source="live", detail="Outcome unknown."
    ).model_dump()
    action.checkpoint()
    original.store.close()  # Simulates recovery from the saved executing checkpoint.
    messaging = MockMessaging()
    messaging.send_sms = AsyncMock(wraps=messaging.send_sms)
    recovered = Service(settings, messaging)
    try:
        await recovered.start()
        restored = recovered.store.get(action.response.action_id)
        assert restored.response.status == "failed"
        assert "interrupted" in restored.response.message
        assert restored.response.tool_results[0].detail == "Outcome unknown."
        assert messaging.send_sms.await_count == 0
        assert recovered.tap(
            TapRequest(button_id="text_home", timestamp=1100, session_id="same-device")
        ) == {"status": "debounced"}
    finally:
        await recovered.close()


def test_device_state_and_undo_survive_restart(settings, tmp_path):
    durable(settings, tmp_path)
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "dim_lights", {"brightness": 15})
        wait(client, action_id, "done")
    with TestClient(create_app(settings)) as client:
        assert client.get("/devices").json()["state"]["brightness"] == 15
        assert client.post("/actions/" + action_id + "/undo").status_code == 200
        assert client.get("/devices").json()["state"]["brightness"] == 80
