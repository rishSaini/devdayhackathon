"""Twilio SMS and voice helpers used by Ripple's deterministic action paths."""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client


_BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_DIR / ".env", override=False)

BLOCKED_NUMBERS = frozenset({"911", "112", "999"})
SMS_LIMIT = 160
REQUEST_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class TwilioSettings:
    account_sid: str
    auth_token: str
    from_number: str

    @classmethod
    def from_env(cls) -> "TwilioSettings":
        fields = {
            "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
            "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
            "TWILIO_FROM_NUMBER": os.getenv("TWILIO_FROM_NUMBER", "").strip(),
        }
        missing = [name for name, value in fields.items() if not value]
        if missing:
            raise RuntimeError("Twilio is not configured")
        return cls(fields["TWILIO_ACCOUNT_SID"], fields["TWILIO_AUTH_TOKEN"], fields["TWILIO_FROM_NUMBER"])


def _blocked(to: str) -> bool:
    digits = re.sub(r"\D", "", to)
    return digits in BLOCKED_NUMBERS or (digits.startswith("1") and digits[1:] in BLOCKED_NUMBERS)


def _valid_e164(to: str) -> bool:
    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", to.strip()))


def _client() -> tuple[Client, TwilioSettings]:
    settings = TwilioSettings.from_env()
    http_client = TwilioHttpClient(timeout=REQUEST_TIMEOUT_SECONDS)
    return Client(settings.account_sid, settings.auth_token, http_client=http_client), settings


def _configured_recipient(to: str) -> bool:
    allowed = {
        os.getenv("HOME_PHONE", "").strip(),
        os.getenv("CAREGIVER_PHONE", "").strip(),
        os.getenv("EMERGENCY_CONTACT", "").strip(),
    }
    allowed.discard("")
    return to.strip() in allowed


def _result(ok: bool, detail: str, source: str = "live") -> dict[str, object]:
    return {"ok": ok, "source": source if ok else "fallback", "detail": detail}


async def send_sms(to: str, body: str) -> dict[str, object]:
    """Send a short SMS. Never include message content or phone numbers in results/logs."""
    if not _valid_e164(to) or _blocked(to) or not _configured_recipient(to):
        return _result(False, "Recipient is invalid, unconfigured, or blocked by Ripple policy.")
    body = body.strip()
    if not body or len(body) > SMS_LIMIT:
        return _result(False, f"SMS body must contain 1–{SMS_LIMIT} characters.")
    try:
        client, settings = _client()
        await asyncio.to_thread(client.messages.create, to=to.strip(), from_=settings.from_number.strip(), body=body)
        return _result(True, "SMS sent.")
    except Exception:
        return _result(False, "Twilio SMS could not be sent.")


async def twilio_voice_call(to: str, message: str) -> dict[str, object]:
    """Start an immediate Twilio voice call with the alert spoken twice."""
    emergency_contact = os.getenv("EMERGENCY_CONTACT", "").strip()
    if not _valid_e164(to) or _blocked(to) or not emergency_contact or to.strip() != emergency_contact:
        return _result(False, "Voice recipient must be the configured, non-blocked emergency contact.")
    text = " ".join(message.split())
    if not text or len(text) > 1000:
        return _result(False, "Voice alert must contain 1–1000 characters.")
    try:
        client, settings = _client()
        spoken = escape(text)
        twiml = f"<Response><Say>{spoken}</Say><Pause length=\"1\"/><Say>{spoken}</Say></Response>"
        await asyncio.to_thread(client.calls.create, to=to.strip(), from_=settings.from_number.strip(), twiml=twiml)
        return _result(True, "Emergency voice call started.")
    except Exception:
        return _result(False, "Twilio voice call could not be started.")


async def send_sms_with_location(to: str, lat: float, lng: float) -> dict[str, object]:
    """Send a map link after validating coordinates."""
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return _result(False, "Location coordinates are invalid.")
    emergency_contact = os.getenv("EMERGENCY_CONTACT", "").strip()
    if not emergency_contact or to.strip() != emergency_contact:
        return _result(False, "Location can only be sent to the configured emergency contact.")
    coordinates = quote(f"{lat:.6f},{lng:.6f}")
    map_url = f"https://maps.google.com/?q={coordinates}"
    display_name = os.getenv("USER_DISPLAY_NAME", "The Ripple user").strip() or "The Ripple user"
    return await send_sms(to, f"Ripple emergency alert: {display_name} may need help. Location: {map_url}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send an explicit Twilio smoke test.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sms", nargs=2, metavar=("TO", "MESSAGE"))
    mode.add_argument("--call", nargs=2, metavar=("TO", "MESSAGE"))
    args = parser.parse_args()
    result = asyncio.run(send_sms(*args.sms) if args.sms else twilio_voice_call(*args.call))
    print(f"{result['source']}: {result['detail']}")
    raise SystemExit(0 if result["ok"] else 1)
