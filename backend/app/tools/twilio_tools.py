"""Explicitly enabled REST adapter. One attempt per send; no automatic retries."""

from xml.sax.saxutils import escape

import httpx
from twilio.request_validator import RequestValidator

from ..config import Settings
from ..integrations import validate_recipient
from ..schemas import Location, ToolResult


class TwilioMessaging:
    mode = "live"

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.ripple_live_twilio or not settings.twilio_auth_token:
            raise ValueError("Live Twilio requires explicit configuration.")
        if not settings.twilio_account_sid.startswith("AC"):
            raise ValueError("Configure a Twilio account SID.")
        validate_recipient(settings.twilio_from_number)
        self.allowed = {
            validate_recipient(settings.home_phone),
            validate_recipient(settings.caregiver_phone),
            validate_recipient(settings.emergency_contact),
        }
        if not settings.public_base_url.startswith("https://"):
            raise ValueError("Configure the public HTTPS webhook base URL.")

    async def _send(self, resource: str, to: str, fields: dict[str, str]) -> ToolResult:
        try:
            validate_recipient(to)
            if to not in self.allowed:
                raise ValueError("Recipient is outside the configured demo allowlist.")
            async with httpx.AsyncClient(timeout=self.settings.ripple_tool_timeout_s) as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.settings.twilio_account_sid}/{resource}.json",
                    auth=(
                        self.settings.twilio_account_sid,
                        self.settings.twilio_auth_token.get_secret_value(),
                    ),
                    data={
                        "To": to,
                        "From": self.settings.twilio_from_number,
                        "StatusCallback": self.settings.public_base_url.rstrip("/")
                        + "/twilio/status",
                        **fields,
                    },
                )
            response.raise_for_status()
            data = response.json()
            if not data.get("sid") or data.get("status") in {"failed", "undelivered", "canceled"}:
                raise ValueError("Twilio did not accept the operation.")
            return ToolResult(
                ok=True,
                source="live",
                detail=f"Twilio accepted {resource.lower()}; delivery is not confirmed.",
                provider_id=data["sid"],
                provider_status=data.get("status"),
            )
        except Exception:
            return ToolResult(
                ok=False,
                source="live",
                detail="Twilio operation failed or its outcome is unknown. Check provider status before retrying.",
            )

    async def send_sms(self, to: str, body: str) -> ToolResult:
        return await self._send("Messages", to, {"Body": body[:160]})

    async def send_approval(self, to: str, action_id: str, details: str) -> ToolResult:
        body = f"Ripple: {self.settings.user_display_name} requests {details}. Reply YES {action_id} or NO {action_id}."
        return await self._send("Messages", to, {"Body": body})

    async def voice_call(self, to: str, message: str) -> ToolResult:
        said = escape(message)
        return await self._send(
            "Calls", to, {"Twiml": f"<Response><Say>{said}</Say><Say>{said}</Say></Response>"}
        )

    async def location_sms(
        self, to: str, location: Location, *, fallback: bool = False
    ) -> ToolResult:
        return await self._send(
            "Messages",
            to,
            {
                "Body": f"Ripple demo emergency alert. {'Fixed demo fallback, not GPS' if fallback else 'Device-reported location'} (accuracy: {location.accuracy_m if location.accuracy_m is not None else 'unknown'} m): https://maps.google.com/?q={location.lat},{location.lng}",
            },
        )


def valid_signature(
    settings: Settings, form: dict[str, str], signature: str, path: str = "/twilio/sms"
) -> bool:
    if not settings.twilio_auth_token or not settings.public_base_url.startswith("https://"):
        return False
    url = settings.public_base_url.rstrip("/") + path
    return RequestValidator(settings.twilio_auth_token.get_secret_value()).validate(
        url, form, signature
    )


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Explicit Twilio smoke check; requires live mode and an allowlisted recipient."
    )
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--sms", nargs=2, metavar=("RECIPIENT", "MESSAGE"))
    commands.add_argument("--call", nargs=2, metavar=("RECIPIENT", "MESSAGE"))
    args = parser.parse_args()
    try:
        adapter = TwilioMessaging(Settings())
    except ValueError:
        print("Twilio smoke check disabled or incomplete configuration. No request was made.")
        raise SystemExit(2) from None
    operation = adapter.send_sms(*args.sms) if args.sms else adapter.voice_call(*args.call)
    result = asyncio.run(operation)
    print(result.model_dump_json())
    raise SystemExit(0 if result.ok else 1)
