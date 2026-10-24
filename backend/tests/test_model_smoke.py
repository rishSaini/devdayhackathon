from dataclasses import replace

from app import model_smoke
from app.decisions import Classification
from app.schemas import ToolResult


async def test_live_smoke_requires_configuration(settings, capsys):
    assert await model_smoke.check(settings, "all") == 2
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    assert await model_smoke.check(settings, "all") == 2
    assert "offline-test" not in capsys.readouterr().out


async def test_smoke_fails_on_classifier_fallback(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"

    class FakeClassifier:
        async def classify(self, spec):
            result = Classification(spec.static_tier, "live", 0.9)
            return replace(result, source="fallback") if spec.button_id == "emergency" else result

        async def close(self):
            pass

    monkeypatch.setattr(model_smoke, "Classifier", lambda _: FakeClassifier())
    assert await model_smoke.check(settings, "decisions") == 1


async def test_smoke_fails_on_successful_template_execution(settings, monkeypatch):
    settings.ripple_live_models = True
    settings.openai_api_key = "offline-test"
    settings.ripple_agent_model = "offline-model"

    class FakeExecutor:
        async def run(self, action, phase):
            return [ToolResult(ok=True, source="fallback", detail="Template succeeded.")]

    monkeypatch.setattr(model_smoke, "Executor", lambda *_: FakeExecutor())
    assert await model_smoke.check(settings, "agents") == 1
