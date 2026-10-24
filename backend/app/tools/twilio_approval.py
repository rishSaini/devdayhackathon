"""Tier 2 approval messaging and the signed inbound Twilio SMS webhook."""

from __future__ import annotations

import inspect
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.datastructures import FormData
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from .approvals import PendingApprovalStore, pending_approvals
from .twilio_tools import _blocked, _valid_e164, send_sms


_BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_DIR / ".env", override=False)

DecisionHandler = Callable[[str, str], object | Awaitable[object]]


class _TwilioFormParams:
    """Adapter exposing the getall API expected by Twilio's validator."""

    def __init__(self, form: FormData) -> None:
        self._form = form

    def __iter__(self):
        return iter(self._form)

    def getall(self, key: str) -> list[str]:
        return self._form.getlist(key)


async def twilio_send_approval_text(
    action_id: str,
    action_details: str,
    caregiver_phone: str,
    *,
    store: PendingApprovalStore = pending_approvals,
) -> dict[str, object]:
    """Register a short-lived approval before sending, then remove it on send failure."""
    configured_caregiver = os.getenv("CAREGIVER_PHONE", "").strip()
    if (
        not _valid_e164(caregiver_phone)
        or _blocked(caregiver_phone)
        or not configured_caregiver
        or caregiver_phone.strip() != configured_caregiver
    ):
        return {"ok": False, "source": "fallback", "detail": "Caregiver number must match the configured, non-blocked approval contact."}
    caregiver_phone = caregiver_phone.strip()
    details = " ".join(action_details.split())
    if not action_id or not details:
        return {"ok": False, "source": "fallback", "detail": "Approval action details are missing."}
    try:
        pending = await store.register(action_id, caregiver_phone)
    except Exception:
        return {"ok": False, "source": "fallback", "detail": "Could not register the approval request."}
    text = f"Ripple: Alex wants to {details}. Reply YES {pending.code} or NO {pending.code}. Expires in 10 min."
    result = await send_sms(caregiver_phone, text)
    if not result.get("ok"):
        await store.discard(action_id)
        return result
    return {"ok": True, "source": "live", "detail": "Approval text sent; waiting for the designated caregiver."}


def create_twilio_router(
    *,
    store: PendingApprovalStore = pending_approvals,
    on_decision: DecisionHandler | None = None,
) -> APIRouter:
    if on_decision is None:
        raise ValueError("An action-state callback is required to mount the Twilio approval webhook")
    router = APIRouter()

    @router.post("/twilio/sms")
    async def inbound_sms(request: Request) -> Response:
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if not auth_token or not public_base_url:
            raise HTTPException(status_code=503, detail="Twilio webhook is not configured")

        form = await request.form()
        signature = request.headers.get("X-Twilio-Signature", "")
        # Use the externally configured URL because TLS termination/tunnels can make
        # ASGI's local scheme/host differ from the URL Twilio signed.
        configured = urlsplit(public_base_url)
        if configured.scheme != "https" or not configured.netloc:
            raise HTTPException(status_code=503, detail="Public webhook URL must use HTTPS")
        external_url = f"{public_base_url}{request.url.path}"
        if request.url.query:
            external_url += f"?{request.url.query}"
        validator = RequestValidator(auth_token)
        if not signature or not validator.validate(external_url, _TwilioFormParams(form), signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        sender = str(form.get("From", "")).strip()
        body = str(form.get("Body", "")).strip()
        response = MessagingResponse()
        resolved = await store.resolve(sender, body)
        if resolved is None:
            response.message("Ripple: no matching pending approval. Check the YES/NO code or contact the user.")
        else:
            action_id, decision = resolved
            try:
                result = on_decision(action_id, decision)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                # The approval is consumed to prevent replay; acknowledge it and
                # let the backend audit/reconcile the callback failure.
                response.message("Ripple received your reply, but could not update the action. Please contact the user.")
                return Response(content=str(response), media_type="application/xml")
            response.message("Approval recorded." if decision == "YES" else "No action was approved.")
        return Response(content=str(response), media_type="application/xml")

    return router
