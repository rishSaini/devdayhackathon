import hmac
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import Settings
from .registry import REGISTRY
from .schemas import ALIASES, ApprovalRequest, ChoiceRequest, Profile, TapRequest
from .service import Conflict, Service
from .tools.twilio_tools import TwilioMessaging, valid_signature


def create_app(settings: Settings | None = None, service: Service | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if bool(settings.ripple_user_token) != bool(settings.ripple_caregiver_token):
            raise ValueError(
                "Configure both resident and caregiver access tokens, or neither for local demo mode."
            )
        if settings.ripple_user_token and hmac.compare_digest(
            settings.ripple_user_token.get_secret_value().encode(),
            settings.ripple_caregiver_token.get_secret_value().encode(),
        ):
            raise ValueError("Resident and caregiver tokens must differ.")
        if settings.ripple_live_twilio and not settings.ripple_user_token:
            raise ValueError("Configure API access tokens before enabling live messaging.")
        messaging = (
            TwilioMessaging(settings) if settings.ripple_live_twilio and service is None else None
        )
        app.state.service = service or Service(settings, messaging=messaging)
        try:
            await app.state.service.start()
            yield
        finally:
            await app.state.service.close()

    app = FastAPI(title="Ripple backend", lifespan=lifespan)

    @app.middleware("http")
    async def access(request: Request, call_next):
        if (
            not settings.ripple_user_token
            or request.method == "OPTIONS"
            or request.url.path
            in {
                "/healthz",
                "/twilio/sms",
                "/twilio/status",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/docs/oauth2-redirect",
            }
        ):
            return await call_next(request)
        supplied = request.headers.get("Authorization", "")
        role = None
        for name, token in (
            ("user", settings.ripple_user_token),
            ("caregiver", settings.ripple_caregiver_token),
        ):
            if token and hmac.compare_digest(
                supplied.encode(), ("Bearer " + token.get_secret_value()).encode()
            ):
                role = name
        if role is None:
            return JSONResponse(status_code=401, content={"message": "API access token required."})
        caregiver_write = request.url.path.endswith(
            ("/approval", "/acknowledge")
        ) or request.url.path.startswith("/demo/approve/")
        if request.method != "GET" and role != ("caregiver" if caregiver_write else "user"):
            return JSONResponse(
                status_code=403, content={"message": "This role cannot perform this operation."}
            )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ripple_cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Authorization"],
    )

    default_openapi = app.openapi

    def secured_openapi():
        schema = default_openapi()
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "RippleAccessToken"
        ] = {
            "type": "http",
            "scheme": "bearer",
            "description": "Resident token for requests and preferences; caregiver token for approvals and acknowledgement. Local demo mode permits omission.",
        }
        for path, operations in schema["paths"].items():
            if path not in {"/healthz", "/twilio/sms", "/twilio/status"}:
                for operation in operations.values():
                    operation["security"] = [{"RippleAccessToken": []}]
        return schema

    app.openapi = secured_openapi

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

    @app.get("/actions")
    async def list_actions(
        request: Request,
        session_id: str | None = None,
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        actions = sorted(
            request.app.state.service.store.actions.values(),
            key=lambda action: action.created_at,
            reverse=True,
        )
        actions = [
            action
            for action in actions
            if (session_id is None or action.request.session_id == session_id)
            and (status is None or action.response.status == status)
        ]
        return {
            "total": len(actions),
            "actions": [a.response.model_dump() for a in actions[offset : offset + limit]],
        }

    @app.get("/catalog")
    async def catalog():
        return {
            "actions": [asdict(spec) for spec in REGISTRY.values()],
            "aliases": ALIASES,
            "devices": "mock",
            "checkout": "mock",
        }

    @app.get("/profile")
    async def profile(request: Request):
        return request.app.state.service.profile().model_dump()

    @app.put("/profile")
    async def put_profile(payload: Profile, request: Request):
        return request.app.state.service.save_profile(payload)

    @app.get("/devices")
    async def devices(request: Request):
        return {"source": "mock", "state": request.app.state.service.devices.read()}

    @app.get("/medical-records")
    async def medical_records(request: Request):
        return {
            "source": "mock",
            "records": request.app.state.service.store.resource("medical_records", []),
        }

    @app.post("/actions/{action_id}/choice", status_code=202)
    async def choose(action_id: str, payload: ChoiceRequest, request: Request):
        return request.app.state.service.choose(
            action_id, payload.clarification_id, payload.choice_id
        )

    @app.post("/actions/{action_id}/approval")
    async def approve(action_id: str, payload: ApprovalRequest, request: Request):
        return request.app.state.service.approve(action_id, payload.approved, payload.fingerprint)

    @app.post("/actions/{action_id}/undo")
    async def undo(action_id: str, request: Request):
        return request.app.state.service.undo(action_id)

    @app.post("/actions/{action_id}/acknowledge")
    async def acknowledge(action_id: str, request: Request):
        return request.app.state.service.acknowledge(action_id)

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

    async def signed_form(request: Request, path: str):
        # Do not accept query parameters or trust proxy headers for the signed URL.
        if request.url.query:
            raise HTTPException(400, "Webhook query parameters are not supported.")
        if (
            request.headers.get("content-type", "").split(";")[0]
            != "application/x-www-form-urlencoded"
        ):
            raise HTTPException(415, "Expected URL-encoded Twilio form.")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > 16384:
                raise HTTPException(413, "Webhook payload is too large.")
            raw.extend(chunk)
        try:
            values = parse_qs(raw.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
        except (ValueError, UnicodeError):
            raise HTTPException(400, "Invalid form.") from None
        if any(len(value) != 1 for value in values.values()):
            raise HTTPException(400, "Repeated form fields are not supported.")
        form = {key: value[0] for key, value in values.items()}
        if not valid_signature(settings, form, request.headers.get("X-Twilio-Signature", ""), path):
            raise HTTPException(403, "Invalid Twilio signature.")
        return form

    @app.post("/twilio/status")
    async def delivery_status(request: Request):
        form = await signed_form(request, "/twilio/status")
        provider_id = form.get("MessageSid") or form.get("CallSid")
        status = form.get("MessageStatus") or form.get("CallStatus")
        if not provider_id or not status:
            raise HTTPException(400, "Provider ID and status are required.")
        request.app.state.service.provider_status(provider_id, status)
        return Response(content="<Response/>", media_type="application/xml")

    @app.post("/twilio/sms")
    async def sms(request: Request):
        form = await signed_form(request, "/twilio/sms")
        if not settings.caregiver_phone or form.get("From") != settings.caregiver_phone:
            raise HTTPException(403, "Sender is not the designated co-signer.")
        words = form.get("Body", "").strip().split()
        if not words or words[0].upper() not in {"YES", "NO"} or len(words) > 2:
            raise HTTPException(400, "Reply YES or NO followed by the action ID.")
        engine = request.app.state.service
        message_id = form.get("MessageSid", "")
        if not message_id:
            raise HTTPException(400, "Twilio MessageSid is required.")
        if engine.store.webhook_seen(message_id):
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
        approved = words[0].upper() == "YES"
        action = engine.store.get(action_id)
        previous_response = action.response.model_copy(deep=True)
        previously_approved = action.approved
        try:
            with engine.store.transaction():
                engine.approve(action_id, approved, enqueue=False)
                engine.store.remember_webhook(message_id)
        except Exception:
            action.response = previous_response
            action.approved = previously_approved
            raise
        if approved:
            engine.spawn(engine.finalize(action), action)
        engine.processed_webhooks.add(message_id)
        return Response(content="<Response/>", media_type="application/xml")

    @app.get("/healthz")
    async def health(request: Request):
        return {
            "status": "ok",
            "prototype": True,
            "storage": "sqlite_single_worker",
            "access": "resident_and_caregiver_tokens"
            if settings.ripple_user_token
            else "local_demo_no_auth",
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
