import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.decisions import ChoiceAnswer, Classifier, apply_policy
from app.registry import REGISTRY, ActionSpec
from app.spasm_filter import SpasmFilter
from app.tools.delivery import build_saved_order, finalize_order


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).resolve().parents[1] / "fixtures/tier_cases.json").read_text())[
        "cases"
    ],
    ids=lambda case: case["id"],
)
async def test_static_fixture_floors(settings, case):
    spec = REGISTRY.get(case["button_id"]) or ActionSpec(
        case["button_id"],
        case["label"],
        case["action_description"],
        int(case["expected_tier"][-1]),
        int(case["expected_tier"][-1]),
    )
    result = await Classifier(settings).classify(spec)
    assert result.tier >= int(case["expected_tier"][-1])
    assert result.source == "fallback"


@pytest.mark.parametrize("button,floor", [("emergency", 3), ("order_lunch", 2)])
def test_model_cannot_lower_floor(button, floor):
    result = apply_policy(
        REGISTRY[button], ChoiceAnswer(type="choice", choice="tier_1", confidence=1), 0.7
    )
    assert result.tier == floor


def test_confidence_rounds_up():
    result = apply_policy(
        REGISTRY["text_home"], ChoiceAnswer(type="choice", choice="tier_2", confidence=0.69), 0.7
    )
    assert result.tier == 3


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        ChoiceAnswer(type="choice", choice="tier_1", confidence=confidence)


async def test_classifier_retries_and_sanitizes(settings):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    client = SimpleNamespace(
        decisions=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("private-payload")))
    )
    classifier = Classifier(settings, client)
    result = await classifier.classify(REGISTRY["order_lunch"])
    assert result.source == "fallback" and result.tier == 2
    assert client.decisions.create.await_count == 2
    assert "private-payload" not in repr(result)


async def test_classifier_uses_choice_schema(settings):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    answer = SimpleNamespace(
        model_dump=lambda: {"type": "choice", "choice": "tier_1", "confidence": 0.94}
    )
    create = AsyncMock(return_value=SimpleNamespace(answers=[answer]))
    result = await Classifier(
        settings, SimpleNamespace(decisions=SimpleNamespace(create=create))
    ).classify(REGISTRY["order_lunch"])
    assert result.tier == 2 and result.source == "live"
    assert create.call_args.kwargs["questions"][0]["type"] == "choice"
    assert "session_id" not in create.call_args.kwargs["input"]


def test_spasm_window_uses_last_accepted_tap_and_independent_keys():
    clock = [0.0]
    filt = SpasmFilter(monotonic=lambda: clock[0])
    assert not filt.should_drop("a", "text_home", 1000)
    assert filt.should_drop("a", "text_home", 1399)
    assert not filt.should_drop("a", "text_home", 1400)
    assert not filt.should_drop("a", "dim_lights", 1401)
    assert not filt.should_drop("b", "text_home", 1401)
    clock[0] = 0.1
    assert filt.should_drop("a", "text_home", 1)
    clock[0] = 0.5
    assert not filt.should_drop("a", "text_home", 1)


async def test_checkout_requires_approval():
    order = build_saved_order()
    assert str(order.total) == "12.4"
    assert not (await finalize_order(order, approved=False)).ok
