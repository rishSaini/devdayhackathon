"""Exercise the real OpenAI SDK parser against an offline HTTP transport."""

import asyncio
import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.decisions import Classifier
from app.registry import REGISTRY


def choice(name="risk_tier", value="tier_1"):
    return {
        "type": "choice",
        "name": name,
        "choice": value,
        "confidence": 0.94,
        "probabilities": [{"value": value, "probability": 1.0}],
    }


@pytest.mark.parametrize(
    "answers,expected_reason",
    [
        ([choice()], None),
        ([choice("unrelated"), choice()], None),
        ([], "invalid_response"),
        ([choice("unrelated")], "invalid_response"),
        ([choice(), choice()], "invalid_response"),
        ([choice(value="tier_4")], "invalid_response"),
        ([{"type": "refusal", "name": "risk_tier", "refusal": "private text"}], "refused"),
    ],
)
async def test_real_sdk_response_parsing(settings, answers, expected_reason):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        assert request.url.path == "/v1/decisions"
        return httpx.Response(
            200,
            json={
                "answers": answers,
                "model": "gpt-6-luna",
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        )

    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    async with AsyncOpenAI(
        api_key="offline-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as client:
        result = await Classifier(settings, client).classify(REGISTRY["order_lunch"])
    assert result.tier == 2  # A model cannot remove the purchase approval floor.
    assert result.fallback_reason == expected_reason
    assert result.source == ("fallback" if expected_reason else "live")
    assert result.model_tier == (None if expected_reason else 1)
    assert len(requests) == (2 if expected_reason == "invalid_response" else 1)
    assert requests[0]["questions"][0]["name"] == "risk_tier"
    assert "private text" not in repr(result)


async def test_timeout_has_bounded_retry_and_reason(settings):
    calls = []

    async def respond(request):
        calls.append(request)
        await asyncio.sleep(1)
        raise AssertionError("The classifier should time out first.")

    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    async with AsyncOpenAI(
        api_key="offline-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ) as client:
        result = await Classifier(settings, client).classify(REGISTRY["text_home"])
    assert len(calls) == 2
    assert result.source == "fallback" and result.fallback_reason == "timeout"


async def test_missing_key_is_distinct_from_disabled(settings):
    settings.openai_api_key = None
    classifier = Classifier(settings)
    assert (await classifier.classify(REGISTRY["text_home"])).fallback_reason == "disabled"
    settings.ripple_live_models = True
    assert (await classifier.classify(REGISTRY["text_home"])).fallback_reason == "missing_api_key"
