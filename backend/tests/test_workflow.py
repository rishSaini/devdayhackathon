import asyncio

import pytest
from conftest import tap

from app.decisions import Classification
from app.integrations import MockMessaging
from app.schemas import ToolResult
from app.service import Conflict, Service


async def wait_for(action, status, timeout=1):
    async with asyncio.timeout(timeout):
        while action.response.status != status:
            await asyncio.sleep(0.002)


class CountingMessaging(MockMessaging):
    def __init__(self):
        self.sms = 0
        self.calls = 0
        self.locations = 0

    async def send_sms(self, to, body):
        self.sms += 1
        return await super().send_sms(to, body)

    async def voice_call(self, to, message):
        self.calls += 1
        return await super().voice_call(to, message)

    async def location_sms(self, to, location, *, fallback=False):
        self.locations += 1
        return await super().location_sms(to, location, fallback=fallback)


async def test_cancel_prevents_sms_and_normal_execution_waits(settings):
    messaging = CountingMessaging()
    service = Service(settings, messaging)
    try:
        response = service.tap(tap("text_home"))
        assert response["status"] == "pending_cancel" and messaging.sms == 0
        service.cancel(response["action_id"])
        await asyncio.sleep(0.04)
        assert messaging.sms == 0
        result = service.tap(tap("text_home", session="another"))
        action = service.store.get(result["action_id"])
        await wait_for(action, "done")
        assert messaging.sms == 1
        assert action.response.source == "mock"
        assert "nothing was sent" in action.response.message
    finally:
        await service.close()


@pytest.mark.parametrize("outcome", ["approve", "decline", "cancel", "expire"])
async def test_lunch_gates(settings, outcome):
    service = Service(settings)
    try:
        action = service.store.get(service.tap(tap())["action_id"])
        await wait_for(action, "awaiting_approval")
        assert not any("checkout" in r.detail for r in action.response.tool_results)
        if outcome == "approve":
            service.approve(action.response.action_id, True)
            with pytest.raises(Conflict):
                service.approve(action.response.action_id, True)
            await wait_for(action, "done")
            assert sum("Simulated checkout" in r.detail for r in action.response.tool_results) == 1
            assert "$12.40" in action.response.message
        elif outcome == "decline":
            service.approve(action.response.action_id, False)
            assert action.response.status == "declined"
        elif outcome == "cancel":
            service.cancel(action.response.action_id)
            with pytest.raises(Conflict):
                service.approve(action.response.action_id, True)
        else:
            await wait_for(action, "expired")
            with pytest.raises(Conflict):
                service.approve(action.response.action_id, True)
        if outcome != "approve":
            assert not any("checkout" in r.detail for r in action.response.tool_results)
    finally:
        await service.close()


async def test_model_escalation_never_bypasses_purchase_approval(settings):
    service = Service(settings)

    async def escalate(spec):
        return Classification(3, "live", 0.5)

    service.classifier.classify = escalate
    try:
        action = service.store.get(service.tap(tap())["action_id"])
        await wait_for(action, "awaiting_approval")
        assert action.response.tier == 3
        assert not action.approved
        assert not any("checkout" in r.detail for r in action.response.tool_results)
    finally:
        await service.close()


async def test_emergency_does_not_wait_for_classifier_and_is_deduplicated(settings):
    messaging = CountingMessaging()
    service = Service(settings, messaging)
    blocker = asyncio.Event()

    async def slow(spec):
        await blocker.wait()
        return Classification(1, "live", 1)

    service.classifier.classify = slow
    try:
        response = service.tap(tap("emergency", timestamp=1000))
        assert service.tap(tap("emergency", timestamp=1100)) == {"status": "debounced"}
        action = service.store.get(response["action_id"])
        await wait_for(action, "done")
        assert messaging.calls == messaging.locations == 1
        assert action.response.tier == 3
        assert "fixed demo location" in action.response.message
        with pytest.raises(Conflict):
            service.cancel(action.response.action_id)
        blocker.set()
        await asyncio.sleep(0.01)
        assert action.response.tier == 3
        assert any("emergency log" in result.detail for result in action.response.tool_results)
    finally:
        await service.close()


async def test_voice_failure_does_not_block_location_sms(settings):
    messaging = CountingMessaging()

    async def broken(to, message):
        raise RuntimeError("secret exception")

    messaging.voice_call = broken
    service = Service(settings, messaging)
    try:
        action = service.store.get(service.tap(tap("emergency"))["action_id"])
        await wait_for(action, "failed")
        assert messaging.locations == 1
        assert "secret exception" not in action.response.model_dump_json()
        assert any(result.ok for result in action.response.tool_results)
    finally:
        await service.close()


async def test_approval_send_failure_does_not_leave_pending(settings):
    messaging = MockMessaging()

    async def broken(*args):
        return ToolResult(ok=False, source="mock", detail="Approval send failed.")

    messaging.send_approval = broken
    service = Service(settings, messaging)
    try:
        action = service.store.get(service.tap(tap())["action_id"])
        await wait_for(action, "failed")
        with pytest.raises(Conflict):
            service.approve(action.response.action_id, True)
    finally:
        await service.close()
