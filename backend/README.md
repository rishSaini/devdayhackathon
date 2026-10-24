# Ripple backend

The backend implements the root README's four-button contract.
It uses FastAPI, Decisions classification, the local OpenAI Agents SDK, and an optional Twilio adapter.
The hosted Agents API is not used.

## Run locally

Use Python 3.11 or newer. Local validation used Python 3.13.3.
From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.
Use one worker. State resets when the process restarts.
Open `/docs` for the request schemas and `/healthz` for integration configuration.

Defaults make no external calls. Do not expose this unauthenticated prototype publicly beyond a controlled demo.

## Local checks

```sh
python -m pytest -q
ruff check app tests
python -m app.smoke
```

Tests replace all external calls. No API keys are required.
The smoke command checks all four buttons with mock tools and template execution.

## Contract

```sh
curl -s http://localhost:8000/tap \
  -H 'Content-Type: application/json' \
  -d '{"button_id":"dim_lights","timestamp":1792800000000,"session_id":"demo-tablet-01"}'
```

Use a fresh millisecond timestamp on each physical tap.
Accepted taps return HTTP 202 with an action ID. Duplicates return HTTP 200 with `status: debounced`.
Poll `GET /actions/{action_id}` every 750 ms.
Cancel with `POST /actions/{action_id}/cancel` before execution starts.
Unknown buttons and extra fields return HTTP 422 before classification.
Validation errors do not echo request contents.

The initial status can be `classifying`; Tier 1 starts as `pending_cancel`.
The initial tier uses the policy floor. Polling supplies any later classification result.
Results separately label classification (`tier_source`) and execution (`source`, `tool_results`).
`done` means tools returned success. For Twilio, success means provider acceptance, not handset delivery.
Inspect individual tool results after a partial failure before retrying.

## Model execution

Set `RIPPLE_LIVE_MODELS=true` and `OPENAI_API_KEY` to enable Decisions calls.
Set `RIPPLE_AGENT_MODEL` to a tested, supported model to enable Agents SDK execution.
Without an agent model, the backend uses labeled template execution.
The classifier sends registry metadata only; it sends no phone numbers, location, or user payloads.
One retry follows a failed classification. Each attempt has a two-second timeout.
Refusals, malformed responses, and unavailable APIs use the static tier.
SDK tracing is disabled for each run. Tool calls use fixed recipients and server-owned order details.

The model can raise a tier but cannot remove a purchase approval gate.
Only the registered emergency button can start emergency dispatch.
An escalated comfort action requires approval; escalation cannot grant emergency capabilities.
The Tier 2 preparation agent has no checkout tool.
The finalization agent exists only after approval and cannot change the saved order.
Repeated tool calls within a run do not repeat side effects.
Agent failures after a tool starts never trigger a second send through fallback execution.

## Twilio setup

Keep mock mode until the team confirms a rehearsal window and teammate-owned destinations.
Configure all Twilio fields, three destination numbers, and `PUBLIC_BASE_URL` before enabling `RIPPLE_LIVE_TWILIO=true`.
All numbers must use E.164 format. The prototype blocks 911, 112, and 999.
Destinations are restricted to the configured allowlist.
Restart after configuration changes.

Set the Twilio inbound Messaging webhook to `POST {PUBLIC_BASE_URL}/twilio/sms`.
Use its exact public HTTPS URL without query parameters.
The server validates the Twilio signature and the designated caregiver's sender number.
Approval messages include the full action ID: `YES act_...` or `NO act_...`.
A bare YES/NO works only when exactly one approval is pending.
Expired, canceled, declined, and previously approved actions cannot finalize again.
Repeated webhook message IDs are acknowledged without applying approval to another action.
Outbound requests use one attempt. They do not automatically retry uncertain outcomes.

For local manual approval, set `RIPPLE_DEMO_APPROVAL=true` and restart:

```sh
curl -X POST 'http://localhost:8000/demo/approve/act_REPLACE?decision=YES'
```

Use `decision=NO` to decline. This unauthenticated route is a labeled demo backup, disabled by default.

## Implementation limits and frontend handoff

- Lights, checkout, lock access, and medical logging are simulated.
- Emergency voice and location SMS start independently of the classifier.
- Missing GPS uses the fixed demo location, disclosed in the action message.
- The exported frontend still uses eight buttons and local simulations. It is not wired to these routes.
- Map the UI to `text_home`, `dim_lights`, `order_lunch`, and `emergency` before integration.
- Use `timestamp`, `session_id`, and optional numeric `location` in requests.
- Implement polling, cancellation, and source labels using the backend response.
- Authentication, persistence, actual delivery confirmation, and real emergency-service integration are absent.
- A 400 ms timing filter does not establish whether a tap was intentional or caused by a spasm.

## Documentation checked

- [Decisions](https://developers.openai.com/api/docs/guides/decisions)
- [Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart?lang=python)
- [Twilio request validation](https://www.twilio.com/docs/usage/security)
- [Twilio outbound calls](https://www.twilio.com/docs/voice/api/call-resource)
