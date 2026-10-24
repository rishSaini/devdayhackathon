from fastapi.testclient import TestClient
from test_api import signed_post
from test_backend_workflows import submit, wait
from twilio.request_validator import RequestValidator

from app.integrations import MockMessaging
from app.main import create_app
from app.schemas import ToolResult
from app.service import Service


class ProviderMessaging(MockMessaging):
    mode = "live"

    async def send_sms(self, to, body):
        return ToolResult(
            ok=True,
            source="live",
            detail="Provider accepted; delivery unconfirmed.",
            provider_id="SMdelivery",
            provider_status="queued",
        )


def signed_status(client, settings, status, signature=None):
    form = {"MessageSid": "SMdelivery", "MessageStatus": status}
    signature = signature or RequestValidator(
        settings.twilio_auth_token.get_secret_value()
    ).compute_signature(settings.public_base_url + "/twilio/status", form)
    return client.post("/twilio/status", data=form, headers={"X-Twilio-Signature": signature})


def config(settings):
    settings.twilio_auth_token = "offline-token"
    settings.public_base_url = "https://example.test"
    return settings


def test_signed_delivery_status_and_out_of_order_callbacks(settings):
    config(settings)
    app = create_app(settings, Service(settings, ProviderMessaging()))
    with TestClient(app) as client:
        action_id = submit(client, "text_home")
        action = wait(client, action_id, "done")
        assert action["tool_results"][0]["provider_status"] == "queued"
        assert signed_status(client, settings, "delivered", "invalid").status_code == 403
        assert signed_status(client, settings, "delivered").status_code == 200
        assert signed_status(client, settings, "sent").status_code == 200
        result = client.get("/actions/" + action_id).json()["tool_results"][0]
        assert result["provider_status"] == "delivered"


def test_delivery_failure_is_visible_and_not_retried(settings):
    config(settings)
    app = create_app(settings, Service(settings, ProviderMessaging()))
    with TestClient(app) as client:
        action_id = submit(client, "text_home")
        wait(client, action_id, "done")
        assert signed_status(client, settings, "undelivered").status_code == 200
        action = client.get("/actions/" + action_id).json()
        assert action["status"] == "failed"
        assert not action["tool_results"][0]["ok"]
        assert "delivery failure" in action["error"]


def test_callback_before_rest_result_is_retained(settings):
    config(settings)
    app = create_app(settings, Service(settings, ProviderMessaging()))
    with TestClient(app) as client:
        assert signed_status(client, settings, "delivered").status_code == 200
        action_id = submit(client, "text_home")
        action = wait(client, action_id, "done")
        assert action["tool_results"][0]["provider_status"] == "delivered"


def test_webhook_replay_cannot_approve_a_later_action_after_restart(settings, tmp_path):
    config(settings)
    settings.ripple_database_path = str(tmp_path / "callbacks.sqlite3")
    settings.ripple_approval_timeout_s = 10
    settings.caregiver_phone = "+15555550101"
    form = {"From": settings.caregiver_phone, "Body": "YES", "MessageSid": "SM-old-approval"}
    with TestClient(create_app(settings)) as client:
        first = submit(client, "order_lunch", session="first")
        wait(client, first, "awaiting_approval")
        assert signed_post(client, settings, form).status_code == 200
        wait(client, first, "done")
    with TestClient(create_app(settings)) as client:
        second = submit(client, "order_lunch", session="second")
        wait(client, second, "awaiting_approval")
        assert signed_post(client, settings, form).status_code == 200
        assert client.get("/actions/" + second).json()["status"] == "awaiting_approval"


def test_terminal_status_is_persisted(settings, tmp_path):
    config(settings)
    settings.ripple_database_path = str(tmp_path / "delivery.sqlite3")
    with TestClient(create_app(settings, Service(settings, ProviderMessaging()))) as client:
        action_id = submit(client, "text_home")
        wait(client, action_id, "done")
        signed_status(client, settings, "delivered")
    with TestClient(create_app(settings)) as client:
        assert signed_status(client, settings, "queued").status_code == 200
        assert (
            client.get("/actions/" + action_id).json()["tool_results"][0]["provider_status"]
            == "delivered"
        )


def test_webhook_transaction_failure_does_not_execute_or_lose_pending_state(settings, monkeypatch):
    config(settings)
    settings.caregiver_phone = "+15555550101"
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        action_id = submit(client, "order_lunch")
        wait(client, action_id, "awaiting_approval")
        original = app.state.service.store.remember_webhook

        def fail(_):
            raise RuntimeError("Simulated commit failure")

        monkeypatch.setattr(app.state.service.store, "remember_webhook", fail)
        form = {
            "From": settings.caregiver_phone,
            "Body": f"YES {action_id}",
            "MessageSid": "SM-transaction",
        }
        assert signed_post(client, settings, form).status_code == 500
        action = client.get("/actions/" + action_id).json()
        assert action["status"] == "awaiting_approval"
        assert not any("checkout" in result["detail"] for result in action["tool_results"])
        monkeypatch.setattr(app.state.service.store, "remember_webhook", original)
        assert signed_post(client, settings, form).status_code == 200
        done = wait(client, action_id, "done")
        assert sum("Simulated checkout" in result["detail"] for result in done["tool_results"]) == 1
