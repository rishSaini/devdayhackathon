import time

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.integrations import validate_recipient
from app.main import create_app


def payload(button="order_lunch", session="test"):
    return {"button_id": button, "timestamp": int(time.time() * 1000), "session_id": session}


def pending(client, action_id):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        result = client.get(f"/actions/{action_id}").json()
        if result["status"] == "awaiting_approval":
            return result
        time.sleep(0.002)
    raise AssertionError("Action did not await approval.")


def test_validation_health_and_debounce(settings):
    with TestClient(create_app(settings)) as client:
        result = client.get("/healthz").json()
        assert result["twilio"] == "mock" and result["decisions"] == "fallback"
        invalid = payload("unknown") | {"private": "not-for-echo"}
        response = client.post("/tap", json=invalid)
        assert response.status_code == 422 and "not-for-echo" not in response.text
        request = payload("dim_lights")
        assert client.post("/tap", json=request).status_code == 202
        assert client.post("/tap", json=request).json() == {"status": "debounced"}
        assert client.get("/actions/missing").status_code == 404
        assert client.post("/twilio/sms", data={"Body": "YES"}).status_code == 403


def test_demo_approval_disabled_by_default(settings):
    settings.ripple_demo_approval = False
    with TestClient(create_app(settings)) as client:
        assert client.post("/demo/approve/missing").status_code == 404


def test_demo_approve_and_decline(settings):
    with TestClient(create_app(settings)) as client:
        action_id = client.post("/tap", json=payload()).json()["action_id"]
        pending(client, action_id)
        assert client.post(f"/demo/approve/{action_id}?decision=NO").json()["status"] == "declined"
        assert client.post(f"/demo/approve/{action_id}").status_code == 409


def signed_post(client, settings, form, signature=None):
    form = {"MessageSid": "SM-offline-test", **form}
    signature = signature or RequestValidator(
        settings.twilio_auth_token.get_secret_value()
    ).compute_signature(
        settings.public_base_url + "/twilio/sms",
        form,
    )
    return client.post("/twilio/sms", data=form, headers={"X-Twilio-Signature": signature})


def test_signed_approval_rejects_wrong_sender_and_replay(settings):
    settings.twilio_auth_token = "test-signature-secret"
    settings.public_base_url = "https://example.test"
    settings.caregiver_phone = "+15555550101"
    with TestClient(create_app(settings)) as client:
        action_id = client.post("/tap", json=payload()).json()["action_id"]
        pending(client, action_id)
        form = {"From": settings.caregiver_phone, "Body": f"YES {action_id}"}
        assert signed_post(client, settings, form, "bad-signature").status_code == 403
        assert signed_post(client, settings, form | {"From": "+15555550102"}).status_code == 403
        assert signed_post(client, settings, form).status_code == 200
        assert signed_post(client, settings, form).status_code == 200


def test_replayed_bare_yes_cannot_approve_a_later_action(settings):
    settings.twilio_auth_token = "test-signature-secret"
    settings.public_base_url = "https://example.test"
    settings.caregiver_phone = "+15555550101"
    with TestClient(create_app(settings)) as client:
        first = client.post("/tap", json=payload(session="first")).json()["action_id"]
        pending(client, first)
        form = {"From": settings.caregiver_phone, "Body": "YES", "MessageSid": "SM-first"}
        assert signed_post(client, settings, form).status_code == 200
        second = client.post("/tap", json=payload(session="second")).json()["action_id"]
        pending(client, second)
        assert signed_post(client, settings, form).status_code == 200
        assert client.get(f"/actions/{second}").json()["status"] == "awaiting_approval"


def test_bare_yes_is_ambiguous_when_multiple_pending(settings):
    settings.twilio_auth_token = "test-signature-secret"
    settings.public_base_url = "https://example.test"
    settings.caregiver_phone = "+15555550101"
    with TestClient(create_app(settings)) as client:
        for session in ["first", "second"]:
            action_id = client.post("/tap", json=payload(session=session)).json()["action_id"]
            pending(client, action_id)
        response = signed_post(client, settings, {"From": settings.caregiver_phone, "Body": "YES"})
        assert response.status_code == 409


@pytest.mark.parametrize("number", ["911", "+911", "112", "999", "9-1-1", "", "5551234"])
def test_blocked_or_invalid_numbers(number):
    with pytest.raises(ValueError):
        validate_recipient(number)
