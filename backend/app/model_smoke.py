"""Opt-in paid model checks. All action tools and storage remain local mocks."""

import argparse
import asyncio
import json

from .agents import Executor
from .config import Settings
from .decisions import Classifier
from .devices import Devices
from .integrations import MockMessaging
from .planning import Planner
from .registry import REGISTRY
from .schemas import Profile, TapRequest
from .store import ActionStore


async def check(settings: Settings, component: str) -> int:
    if not settings.models_configured:
        print(json.dumps({"status": "not_configured", "required": "live models flag and API key"}))
        return 2
    if component in {"agents", "planner", "all"} and not settings.ripple_agent_model:
        print(json.dumps({"status": "not_configured", "required": "RIPPLE_AGENT_MODEL"}))
        return 2
    passed = True
    if component in {"decisions", "all"}:
        classifier = Classifier(settings)
        try:
            for button, spec in REGISTRY.items():
                result = await classifier.classify(spec)
                ok = result.source == "live"
                passed &= ok
                print(
                    json.dumps(
                        {"component": "decisions", "button": button, "ok": ok, **vars(result)}
                    )
                )
        finally:
            await classifier.close()

    if component == "decisions":
        return 0 if passed else 1

    store = ActionStore()
    devices = Devices(store)
    try:
        for button in REGISTRY:
            params = (
                {"severity": 4}
                if button == "log_pain"
                else {"elevation": 15}
                if button == "reposition_bed"
                else {}
            )
            request = TapRequest(
                button_id=button, timestamp=1, session_id="model-smoke", params=params
            )
            action = store.create(request, REGISTRY[button].policy_floor)
            if button != "emergency":
                # Agent-only checks use deterministic preparation to isolate execution failures.
                planning_settings = (
                    settings
                    if component in {"planner", "all"}
                    else settings.model_copy(update={"ripple_live_models": False})
                )
                planned = await Planner(planning_settings).build(request, Profile(), devices.read())
                if component in {"planner", "all"}:
                    ok = planned.source == "live" and planned.selected is not None
                    passed &= ok
                    print(json.dumps({"component": "planner", "button": button, "ok": ok}))
                if planned.selected:
                    action.response.plan = planned.candidates[planned.selected]
            if component not in {"agents", "all"}:
                continue
            executor = Executor(settings, MockMessaging(), devices)
            phases = (
                ["prepare", "finalize"]
                if button == "order_lunch"
                else ["emergency"]
                if button == "emergency"
                else ["execute"]
            )
            for phase in phases:
                # Approval is synthetic and restricted to this isolated mock-tool check.
                action.approved = phase == "finalize" or (
                    button != "order_lunch" and REGISTRY[button].policy_floor >= 2
                )
                action.response.approval_fingerprint = (
                    action.fingerprint() if action.approved else None
                )
                action.response.status = "executing"
                results = await executor.run(action, phase)
                ok = bool(results) and all(r.ok and r.source != "fallback" for r in results)
                passed &= ok
                print(
                    json.dumps(
                        {
                            "component": "agents_sdk",
                            "button": button,
                            "phase": phase,
                            "ok": ok,
                            "tools": "mock",
                            "fallback": any(r.source == "fallback" for r in results),
                        }
                    )
                )
    finally:
        store.close()
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--component", choices=["decisions", "planner", "agents", "all"], default="all"
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(check(Settings(), args.component)))
