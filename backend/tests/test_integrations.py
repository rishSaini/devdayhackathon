import json
from unittest.mock import AsyncMock

import httpx
import pytest
from agents import Runner
from agents.tool_context import ToolContext
from conftest import tap

from app.agents import Executor
from app.integrations import MockMessaging
from app.store import ActionStore
from app.tools.twilio_tools import TwilioMessaging


async def invoke(tool, arguments=None):
    data = json.dumps(arguments or {})
    ctx = ToolContext(
        context=None, tool_name=tool.name, tool_call_id="offline-call", tool_arguments=data
    )
    return await tool.on_invoke_tool(ctx, data)


async def test_sdk_has_scoped_tools_and_does_not_repeat_send_after_model_failure(
    settings, monkeypatch
):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-test-model"
    messaging = MockMessaging()
    messaging.send_sms = AsyncMock(wraps=messaging.send_sms)
    action = ActionStore().create(tap("text_home"), 1)
    action.response.status = "executing"

    async def fake_run(agent, prompt, **kwargs):
        assert kwargs["run_config"].tracing_disabled
        assert [tool.name for tool in agent.tools] == ["send_sms"]
        await invoke(agent.tools[0], {"body": "A checked message."})
        await invoke(agent.tools[0], {"body": "A duplicate attempt."})
        raise RuntimeError("private model error after a send")

    monkeypatch.setattr(Runner, "run", fake_run)
    results = await Executor(settings, messaging).run(action, "execute")
    assert messaging.send_sms.await_count == 1
    assert all(result.ok for result in results)
    assert any(result.source == "fallback" for result in results)
    assert "private model error" not in repr(results)


async def test_sdk_prep_has_no_checkout_and_order_is_server_owned(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-test-model"
    messaging = MockMessaging()
    messaging.send_approval = AsyncMock(wraps=messaging.send_approval)
    action = ActionStore().create(tap(), 2)

    async def fake_run(agent, prompt, **kwargs):
        tools = {tool.name: tool for tool in agent.tools}
        assert set(tools) == {"build_saved_order", "twilio_send_approval_text"}
        blocked = await invoke(tools["twilio_send_approval_text"])
        assert not blocked["ok"]
        await invoke(tools["build_saved_order"])
        await invoke(tools["twilio_send_approval_text"])

    monkeypatch.setattr(Runner, "run", fake_run)
    ready = []
    results = await Executor(settings, messaging).run(action, "prepare", lambda: ready.append(True))
    assert all(result.ok for result in results)
    assert ready == [True]
    assert messaging.send_approval.await_count == 1
    assert "$12.40" in messaging.send_approval.call_args.args[-1]


async def test_sdk_final_prose_does_not_imply_success(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-test-model"
    action = ActionStore().create(tap("dim_lights"), 1)

    async def fake_run(*args, **kwargs):
        return "Done!"  # No actual tool invocation.

    monkeypatch.setattr(Runner, "run", fake_run)
    results = await Executor(settings, MockMessaging()).run(action, "execute")
    assert not results[0].ok


async def test_checkout_tool_is_absent_before_approval(settings):
    action = ActionStore().create(tap(), 2)
    results = await Executor(settings, MockMessaging()).run(action, "finalize")
    assert not results[0].ok


def live_settings(settings):
    settings.ripple_live_twilio = True
    settings.twilio_account_sid = "AC" + "a" * 32
    settings.twilio_auth_token = "offline-token"
    settings.twilio_from_number = "+15555550100"
    settings.home_phone = "+15555550101"
    settings.caregiver_phone = "+15555550102"
    settings.emergency_contact = "+15555550103"
    settings.public_base_url = "https://example.test"
    return settings


async def test_twilio_rest_is_allowlisted_and_acceptance_not_delivery(settings, monkeypatch):
    adapter = TwilioMessaging(live_settings(settings))
    post = AsyncMock(
        return_value=httpx.Response(
            201,
            json={"sid": "SMtest", "status": "queued"},
            request=httpx.Request("POST", "https://example.test"),
        )
    )
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert not (await adapter.send_sms("911", "Blocked")).ok
    assert not (await adapter.send_sms("+15555550999", "Blocked")).ok
    assert post.await_count == 0
    result = await adapter.send_sms(settings.home_phone, "Test")
    assert result.ok and result.source == "live"
    assert "delivery is not confirmed" in result.detail
    assert post.await_count == 1


async def test_twilio_does_not_retry_unknown_send_outcomes(settings, monkeypatch):
    adapter = TwilioMessaging(live_settings(settings))
    post = AsyncMock(side_effect=httpx.ReadTimeout("private request"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    result = await adapter.send_sms(settings.home_phone, "Test")
    assert not result.ok and result.source == "live"
    assert post.await_count == 1
    assert "private request" not in result.detail


@pytest.mark.parametrize(
    "field", ["home_phone", "caregiver_phone", "emergency_contact", "twilio_from_number"]
)
def test_live_startup_rejects_emergency_numbers(settings, field):
    config = live_settings(settings)
    setattr(config, field, "911")
    with pytest.raises(ValueError):
        TwilioMessaging(config)
