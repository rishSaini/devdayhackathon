from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import Settings
from .schemas import TapRequest
from .service import Conflict, Service
from .tools.twilio_tools import TwilioMessaging, valid_signature


def create_app(settings: Settings | None = None, service: Service | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        messaging = (
            TwilioMessaging(settings) if settings.ripple_live_twilio and service is None else None
        )
        app.state.service = service or Service(settings, messaging=messaging)
        try:
            yield
        finally:
            await app.state.service.close()

    app = FastAPI(title="Ripple backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ripple_cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(KeyError)
    async def missing(request: Request, exc: KeyError):
        return JSONResponse(status_code=404, content={"message": "Action not found."})

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict):
        return JSONResponse(status_code=409, content={"message": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        # FastAPI's default validation response echoes input. Keep sensitive payloads out.
        return JSONResponse(
            status_code=422, content={"message": "Invalid request. Check the documented schema."}
        )

    @app.exception_handler(Exception)
    async def failure(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": "Request failed. Check action status before retrying; external outcome may be unknown.",
            },
        )

    @app.post("/tap", status_code=202)
    async def tap(payload: TapRequest, request: Request):
        result = request.app.state.service.tap(payload)
        return JSONResponse(
            status_code=200 if result["status"] == "debounced" else 202, content=result
        )

    @app.get("/actions/{action_id}")
    async def get_action(action_id: str, request: Request):
        return request.app.state.service.store.get(action_id).response.model_dump()

    @app.post("/actions/{action_id}/cancel")
    async def cancel(action_id: str, request: Request):
        return request.app.state.service.cancel(action_id)

    @app.post("/demo/approve/{action_id}")
    async def demo_approve(
        action_id: str, request: Request, decision: Literal["YES", "NO"] = "YES"
    ):
        if not settings.ripple_demo_approval:
            raise HTTPException(404, "Demo approval is disabled.")
        return request.app.state.service.approve(action_id, decision == "YES")

    @app.post("/twilio/sms")
    async def sms(request: Request):
        # Do not accept query parameters or trust proxy headers for the signed URL.
        if request.url.query:
            raise HTTPException(400, "Webhook query parameters are not supported.")
        if (
            request.headers.get("content-type", "").split(";")[0]
            != "application/x-www-form-urlencoded"
        ):
            raise HTTPException(415, "Expected URL-encoded Twilio form.")
        raw = await request.body()
        if len(raw) > 16384:
            raise HTTPException(413, "Webhook payload is too large.")
        try:
            values = parse_qs(raw.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
        except (ValueError, UnicodeError):
            raise HTTPException(400, "Invalid form.") from None
        if any(len(value) != 1 for value in values.values()):
            raise HTTPException(400, "Repeated form fields are not supported.")
        form = {key: value[0] for key, value in values.items()}
        if not valid_signature(settings, form, request.headers.get("X-Twilio-Signature", "")):
            raise HTTPException(403, "Invalid Twilio signature.")
        if not settings.caregiver_phone or form.get("From") != settings.caregiver_phone:
            raise HTTPException(403, "Sender is not the designated co-signer.")
        words = form.get("Body", "").strip().split()
        if not words or words[0].upper() not in {"YES", "NO"} or len(words) > 2:
            raise HTTPException(400, "Reply YES or NO followed by the action ID.")
        engine = request.app.state.service
        message_id = form.get("MessageSid", "")
        if not message_id:
            raise HTTPException(400, "Twilio MessageSid is required.")
        if message_id in engine.processed_webhooks:
            return Response(content="<Response/>", media_type="application/xml")
        if len(words) == 2:
            action_id = words[1]
        else:
            pending = [
                a for a in engine.store.actions.values() if a.response.status == "awaiting_approval"
            ]
            if len(pending) != 1:
                raise HTTPException(409, "Include the action ID to identify the approval.")
            action_id = pending[0].response.action_id
        engine.approve(action_id, words[0].upper() == "YES")
        engine.processed_webhooks.add(message_id)
        return Response(content="<Response/>", media_type="application/xml")

    @app.get("/healthz")
    async def health(request: Request):
        return {
            "status": "ok",
            "prototype": True,
            "storage": "in_memory_single_worker",
            "decisions": "configured_unverified" if settings.models_configured else "fallback",
            "agents": "configured_unverified"
            if settings.models_configured and settings.ripple_agent_model
            else "fallback",
            "twilio": "configured_unverified"
            if request.app.state.service.messaging.mode == "live"
            else "mock",
            "devices": "mock",
            "checkout": "mock",
            "medical_log": "mock",
            "demo_approval": settings.ripple_demo_approval,
        }

    return app


app = create_app()
