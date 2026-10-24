import json
from types import SimpleNamespace

import httpx
import openai
import pytest
from agents import Runner

from app.devices import Devices
from app.planning import Planner, Proposal
from app.schemas import Profile, TapRequest
from app.store import ActionStore


def request(button="text_home", **params):
    return TapRequest(button_id=button, timestamp=1, session_id="planning", params=params)


@pytest.mark.parametrize(
    "selection,asks,source",
    [("requested", False, "live"), ("invented", False, "fallback"), ("requested", True, "live")],
)
async def test_planning_is_read_only_and_preserves_intent(
    settings, monkeypatch, selection, asks, source
):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-model"

    async def fake_run(agent, prompt, **kwargs):
        assert kwargs["run_config"].tracing_disabled
        assert [tool.name for tool in agent.tools] == ["read_context"]
        from agents.tool_context import ToolContext

        ctx = ToolContext(
            context=None, tool_name="read_context", tool_call_id="read", tool_arguments="{}"
        )
        context = await agent.tools[0].on_invoke_tool(ctx, "{}")
        assert context["candidates"]["requested"]["parameters"]["message"] == "My exact message."
        return SimpleNamespace(final_output=Proposal(choice_id=selection, request_choice=asks))

    monkeypatch.setattr(Runner, "run", fake_run)
    result = await Planner(settings).build(request(message="My exact message."), Profile(), {})
    assert result.source == source
    assert result.selected == (None if asks else "requested")
    assert result.candidates["requested"].parameters.message == "My exact message."


async def test_full_sdk_structured_planning_over_http(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-model"
    requests = []

    def respond(req):
        body = json.loads(req.content)
        requests.append(body)
        assert req.url.path == "/v1/responses"
        assert [tool["name"] for tool in body["tools"]] == ["read_context"]
        if len(requests) == 1:
            output = [
                {
                    "type": "function_call",
                    "id": "fc_read",
                    "call_id": "call_read",
                    "name": "read_context",
                    "arguments": "{}",
                    "status": "completed",
                }
            ]
        else:
            output = [
                {
                    "type": "message",
                    "id": "msg_plan",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"choice_id": "requested", "request_choice": False}),
                            "annotations": [],
                        }
                    ],
                }
            ]
        return httpx.Response(
            200,
            json={
                "id": f"resp_{len(requests)}",
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
    result = await Planner(settings).build(
        request("dim_lights", brightness=25), Profile(), {"brightness": 80}
    )
    assert len(requests) == 2
    assert result.source == "live"
    assert result.candidates[result.selected].parameters.brightness == 25
    assert requests[0]["text"]["format"]["type"] == "json_schema"


async def test_model_cannot_remove_required_user_choice(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-model"

    async def fake_run(agent, *args, **kwargs):
        return SimpleNamespace(final_output=Proposal(choice_id="8", request_choice=False))

    monkeypatch.setattr(Runner, "run", fake_run)
    result = await Planner(settings).build(request("log_pain"), Profile(), {})
    assert result.selected is None
    assert result.source == "fallback"  # Model skipped the required context read.


def test_persistent_database_rejects_second_worker(tmp_path):
    path = str(tmp_path / "single.sqlite3")
    first = ActionStore(path)
    try:
        with pytest.raises(RuntimeError, match="one worker"):
            ActionStore(path)
    finally:
        first.close()
    second = ActionStore(path)
    second.close()


def test_device_lock_expires_without_running_timer():
    store = ActionStore()
    try:
        devices = Devices(store)
        state = devices.read()
        state["unlock_until_ms"] = 1
        store.put_resource("devices", state)
        assert not devices.read()["door_unlocked"]
    finally:
        store.close()
