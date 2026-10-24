"""Run the actual Agents SDK loop against offline Responses HTTP fixtures."""

import json
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from app.agents import Executor
from app.devices import Devices
from app.integrations import MockMessaging
from app.planning import Planner
from app.schemas import Profile, TapRequest
from app.store import ActionStore
from app.tools.delivery import build_saved_order


@pytest.mark.parametrize(
    "button,phase,operations,fail_after_tools",
    [
        ("text_home", "execute", ["send_sms"], False),
        ("dim_lights", "execute", ["set_lights"], False),
        ("order_lunch", "prepare", ["build_saved_order", "twilio_send_approval_text"], False),
        ("order_lunch", "finalize", ["finalize_order"], False),
        ("emergency", "emergency", ["emergency_followup", "smart_lock_grant_access"], False),
        ("text_home", "execute", ["send_sms", "send_sms"], False),
        ("text_home", "execute", ["send_sms"], True),
        ("text_caregiver", "execute", ["send_sms"], False),
        ("set_temperature", "execute", ["set_temperature"], False),
        ("log_pain", "execute", ["record_pain"], False),
        ("reposition_bed", "execute", ["set_bed"], False),
        ("request_drink", "execute", ["request_drink"], False),
        ("unlock_door", "execute", ["unlock_door"], False),
    ],
)
async def test_sdk_tool_loop_over_http(
    settings, monkeypatch, button, phase, operations, fail_after_tools
):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-model"
    settings.ripple_tool_timeout_s = 1
    messaging = MockMessaging()
    messaging.send_sms = AsyncMock(wraps=messaging.send_sms)
    messaging.send_approval = AsyncMock(wraps=messaging.send_approval)
    store = ActionStore()
    devices = Devices(store)
    action = store.create(TapRequest(button_id=button, timestamp=1, session_id="sdk-http-test"), 2)
    action.response.status = "executing"
    if phase == "finalize":
        action.order = build_saved_order()
        action.approved = True
    if button not in {"text_home", "dim_lights", "order_lunch", "emergency"}:
        action.request.params.message = "Hello from Ripple." if button == "text_caregiver" else None
        action.request.params.severity = 4 if button == "log_pain" else None
        action.request.params.elevation = 15 if button == "reposition_bed" else None
        planned = await Planner(settings.model_copy(update={"ripple_live_models": False})).build(
            action.request, Profile(), devices.read()
        )
        action.response.plan = planned.candidates[planned.selected]
        action.approved = True
        action.response.approval_fingerprint = action.fingerprint()
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.url.path == "/v1/responses"
        assert body["model"] == "offline-model"
        assert body["store"] is False
        assert body["parallel_tool_calls"] is False
        index = len(requests) - 1
        if index < len(operations):
            name = operations[index]
            assert name in {tool["name"] for tool in body["tools"]}
            if phase == "prepare":
                assert "finalize_order" not in {tool["name"] for tool in body["tools"]}
            output = [
                {
                    "type": "function_call",
                    "id": f"fc_{index}",
                    "call_id": f"call_{index}",
                    "name": name,
                    "arguments": json.dumps(
                        {"body": "Hello from Ripple."} if name == "send_sms" else {}
                    ),
                    "status": "completed",
                }
            ]
        else:
            if fail_after_tools:
                return httpx.Response(500, json={"error": {"message": "private provider error"}})
            output = [
                {
                    "type": "message",
                    "id": "msg_final",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "Finished.", "annotations": []}],
                }
            ]
        return httpx.Response(
            200,
            json={
                "id": f"resp_{index}",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "offline-model",
                "output": output,
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            },
        )

    client = openai.AsyncOpenAI(
        api_key="offline-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    )
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: client)
    ready = []
    results = await Executor(settings, messaging, devices).run(
        action, phase, lambda: ready.append(True)
    )
    assert len(requests) == len(operations) + 1
    assert all(result.ok for result in results)
    assert any(r.source == "fallback" for r in results) == fail_after_tools
    assert messaging.send_sms.await_count == int(
        button in {"text_home", "text_caregiver", "request_drink"}
    )
    assert messaging.send_approval.await_count == int(phase == "prepare")
    assert ready == ([True] if phase == "prepare" else [])
    assert "private provider error" not in repr(results)
    for index in range(1, len(requests)):
        assert any(
            item.get("type") == "function_call_output" and item["call_id"] == f"call_{index - 1}"
            for item in requests[index]["input"]
        )
    store.close()
