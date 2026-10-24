import time
from dataclasses import replace
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import Profile


def submit(client, button, params=None, session=None):
    response = client.post(
        "/tap",
        json={
            "button_id": button,
            "timestamp": int(time.time() * 1000),
            "session_id": session or button,
            "params": params or {},
        },
    )
    assert response.status_code == 202, response.text
    return response.json()["action_id"]


def wait(client, action_id, *statuses):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        response = client.get("/actions/" + action_id)
        assert response.status_code == 200, response.text
        action = response.json()
        if action["status"] in statuses:
            return action
        assert action["status"] not in {"failed", "canceled", "expired"}, action
        time.sleep(0.002)
    raise AssertionError(action)


def approve(client, action_id):
    action = wait(client, action_id, "awaiting_approval")
    response = client.post(
        "/actions/" + action_id + "/approval",
        json={
            "approved": True,
            "fingerprint": action["approval_fingerprint"],
        },
    )
    assert response.status_code == 200, response.text
    return wait(client, action_id, "done")


@pytest.mark.parametrize(
    "button,params,review",
    [
        ("text_home", {"message": "Please call me."}, False),
        ("text_caregiver", {"message": "Please visit."}, False),
        ("dim_lights", {"brightness": 20}, False),
        ("set_temperature", {"temperature_f": 70}, False),
        ("request_drink", {}, False),
        ("order_lunch", {}, True),
        ("log_pain", {"severity": 4, "notes": "My own report."}, True),
        ("reposition_bed", {"elevation": 15}, True),
        ("unlock_door", {}, True),
        ("emergency", {}, False),
    ],
)
def test_every_canonical_action(settings, button, params, review):
    settings.ripple_approval_timeout_s = 10
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, button, params)
        action = approve(client, action_id) if review else wait(client, action_id, "done")
        assert action["button_id"] == button
        assert action["source"] == "mock"
        assert all(r["ok"] for r in action["tool_results"])
        if button == "log_pain":
            records = client.get("/medical-records").json()["records"]
            assert records[0]["severity"] == 4 and records[0]["notes"] == "My own report."
        if button == "unlock_door":
            assert not any(
                r["operation"] in {"emergency_call", "emergency_location"}
                for r in action["tool_results"]
            )


@pytest.mark.parametrize(
    "button,canonical",
    [
        ("order_doordash", "order_lunch"),
        ("emergency_sos", "emergency"),
        ("adjust_thermostat", "set_temperature"),
        ("water_assistance", "request_drink"),
    ],
)
def test_explicit_ui_aliases(settings, button, canonical):
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, button)
        assert client.get("/actions/" + action_id).json()["button_id"] == canonical
        assert client.get("/catalog").json()["aliases"][button] == canonical


@pytest.mark.parametrize(
    "button,params",
    [
        ("set_temperature", {"temperature_f": 90}),
        ("log_pain", {"severity": 11}),
        ("dim_lights", {"brightness": -1}),
        ("reposition_bed", {"elevation": 50}),
        ("emergency", {"message": "private-input"}),
        ("text_home", {"recipient": "+15555550100"}),
        ("text_home", {"severity": 8}),
    ],
)
def test_rejects_invalid_or_unrelated_parameters(settings, button, params):
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/tap",
            json={"button_id": button, "timestamp": 1, "session_id": "test", "params": params},
        )
        assert response.status_code == 422
        assert "private-input" not in response.text
        assert client.get("/actions").json()["total"] == 0


@pytest.mark.parametrize("button,choice", [("log_pain", "3"), ("reposition_bed", "30")])
def test_missing_inputs_wait_and_resume_once(settings, button, choice):
    settings.ripple_approval_timeout_s = 10
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, button)
        action = wait(client, action_id, "awaiting_input")
        assert action["tool_results"] == []
        payload = {"clarification_id": action["clarification"]["id"], "choice_id": choice}
        assert client.post("/actions/" + action_id + "/choice", json=payload).status_code == 202
        assert client.post("/actions/" + action_id + "/choice", json=payload).status_code == 409
        action = approve(client, action_id)
        assert action["plan"]["choice_id"] == choice


def test_adaptive_lunch_respects_availability_and_budget(settings):
    settings.ripple_approval_timeout_s = 10
    with TestClient(create_app(settings)) as client:
        profile = Profile(unavailable_orders=["usual_lunch"], lunch_budget=10).model_dump()
        assert client.put("/profile", json=profile).status_code == 200
        action_id = submit(client, "order_lunch")
        action = wait(client, action_id, "awaiting_input")
        assert [option["id"] for option in action["clarification"]["choices"]] == ["soup_lunch"]
        url = "/actions/" + action_id + "/choice"
        assert (
            client.post(
                url,
                json={
                    "clarification_id": action["clarification"]["id"],
                    "choice_id": "usual_lunch",
                },
            ).status_code
            == 409
        )
        assert (
            client.post(
                url,
                json={"clarification_id": action["clarification"]["id"], "choice_id": "soup_lunch"},
            ).status_code
            == 202
        )
        done = approve(client, action_id)
        assert "$9.50" in done["message"]


def test_no_affordable_lunch_fails_without_effects(settings):
    with TestClient(create_app(settings)) as client:
        client.put("/profile", json=Profile(lunch_budget=1).model_dump())
        action_id = submit(client, "order_lunch")
        action = wait(client, action_id, "failed")
        assert action["tool_results"] == []


def test_approval_binds_to_exact_saved_order(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        action_id = submit(client, "order_lunch")
        original = wait(client, action_id, "awaiting_approval")
        stored = app.state.service.store.get(action_id)
        stored.order = replace(stored.order, total=Decimal("99"))
        assert (
            client.post(
                "/actions/" + action_id + "/approval",
                json={"approved": True, "fingerprint": original["approval_fingerprint"]},
            ).status_code
            == 409
        )
        assert not stored.approved
        assert not any("checkout" in r.detail for r in stored.response.tool_results)


def test_stale_approval_and_decline(settings):
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "log_pain", {"severity": 2})
        action = wait(client, action_id, "awaiting_approval")
        url = "/actions/" + action_id + "/approval"
        assert client.post(url, json={"approved": True, "fingerprint": "stale"}).status_code == 409
        assert (
            client.post(
                url, json={"approved": False, "fingerprint": action["approval_fingerprint"]}
            ).json()["status"]
            == "declined"
        )
        assert client.get("/medical-records").json()["records"] == []


def test_device_readback_undo_and_newer_change_protection(settings):
    with TestClient(create_app(settings)) as client:
        first = submit(client, "dim_lights", {"brightness": 20})
        wait(client, first, "done")
        assert client.get("/devices").json()["state"]["brightness"] == 20
        assert client.post("/actions/" + first + "/undo").json()["undone"]
        assert client.get("/devices").json()["state"]["brightness"] == 80
        assert client.post("/actions/" + first + "/undo").status_code == 409
        second = submit(client, "set_temperature", {"temperature_f": 70})
        wait(client, second, "done")
        third = submit(client, "set_temperature", {"temperature_f": 74}, session="other-device")
        wait(client, third, "done")
        assert client.post("/actions/" + second + "/undo").status_code == 409
        assert client.get("/devices").json()["state"]["temperature_f"] == 74


def test_drink_acknowledgement_is_distinct_and_idempotent(settings):
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "request_drink")
        action = wait(client, action_id, "done")
        assert action["acknowledged_at_ms"] is None
        first = client.post("/actions/" + action_id + "/acknowledge").json()
        assert first["acknowledged_at_ms"] is not None
        assert (
            client.post("/actions/" + action_id + "/acknowledge").json()["acknowledged_at_ms"]
            == first["acknowledged_at_ms"]
        )


def test_clarification_expiry_and_cancellation(settings):
    settings.ripple_input_timeout_s = 0.02
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "log_pain")
        wait(client, action_id, "awaiting_input")
        assert wait(client, action_id, "expired")["tool_results"] == []
        other = submit(client, "reposition_bed")
        wait(client, other, "awaiting_input")
        assert client.post("/actions/" + other + "/cancel").json()["status"] == "canceled"


def test_api_roles(settings):
    settings.ripple_user_token = "resident-token"
    settings.ripple_caregiver_token = "caregiver-token"
    with TestClient(create_app(settings)) as client:
        assert client.get("/profile").status_code == 401
        client.headers["Authorization"] = "Bearer caregiver-token"
        assert client.get("/profile").status_code == 200
        assert client.put("/profile", json=Profile().model_dump()).status_code == 403
        assert client.post("/tap", json={}).status_code == 403
        client.headers["Authorization"] = "Bearer resident-token"
        assert client.put("/profile", json=Profile().model_dump()).status_code == 200
        assert (
            client.post(
                "/actions/missing/approval", json={"approved": True, "fingerprint": "test"}
            ).status_code
            == 403
        )
        response = client.options(
            "/tap",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert response.status_code == 200
        assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_changed_budget_blocks_pending_checkout(settings):
    settings.ripple_approval_timeout_s = 10
    with TestClient(create_app(settings)) as client:
        action_id = submit(client, "order_lunch")
        action = wait(client, action_id, "awaiting_approval")
        assert client.put("/profile", json=Profile(lunch_budget=1).model_dump()).status_code == 200
        response = client.post(
            "/actions/" + action_id + "/approval",
            json={"approved": True, "fingerprint": action["approval_fingerprint"]},
        )
        assert response.status_code == 409
        assert not any(
            "checkout" in result["detail"]
            for result in client.get("/actions/" + action_id).json()["tool_results"]
        )


def test_empty_secrets_are_unconfigured_and_docs_describe_auth(settings):
    settings.ripple_user_token = ""
    settings.ripple_caregiver_token = ""
    settings.openai_api_key = " "
    assert settings.ripple_user_token is None
    assert settings.openai_api_key is None
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()
        assert schema["components"]["securitySchemes"]["RippleAccessToken"]["scheme"] == "bearer"
        assert schema["paths"]["/tap"]["post"]["security"] == [{"RippleAccessToken": []}]
        assert client.get("/healthz").json()["access"] == "local_demo_no_auth"


def test_auth_failure_retains_cors_headers(settings):
    settings.ripple_user_token = "resident-token"
    settings.ripple_caregiver_token = "caregiver-token"
    with TestClient(create_app(settings)) as client:
        response = client.get("/profile", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 401
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_activity_filter_and_pagination(settings):
    with TestClient(create_app(settings)) as client:
        for session in ["first", "second"]:
            action_id = submit(client, "text_home", session=session)
            wait(client, action_id, "done")
        result = client.get("/actions?session_id=second&status=done").json()
        assert result["total"] == 1 and result["actions"][0]["session_id"] == "second"
        assert len(client.get("/actions?limit=1&offset=1").json()["actions"]) == 1
        assert client.get("/actions?limit=101").status_code == 422
