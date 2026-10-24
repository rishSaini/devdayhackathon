# Ripple backend

FastAPI implements all ten backend actions with Decisions and the local OpenAI Agents SDK.
The original four-action API remains supported.
The frontend still uses browser-local simulations and needs integration.

## Run locally

Use Python 3.11 or newer. Local validation uses Python 3.13.
Run these commands from `backend/`:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.
Open `/docs` for interactive requests and `/healthz` for integration modes.
Defaults make no external calls.

SQLite stores actions, choices, profiles, approvals, tool journals, webhook IDs, and simulated device state.
Use exactly one worker. A file lock rejects a second worker for the same database.
Pending choices and approvals survive restarts with their original deadlines.
Interrupted execution becomes a visible failure with saved tool results; external effects are never automatically replayed.
The default database is `backend/app/data/ripple.sqlite3`.
An explicit relative `RIPPLE_DATABASE_PATH` resolves from the server's working directory.
Tests and offline smoke checks use isolated memory databases.

## Access roles

This deployment serves one resident and their designated caregiver.
It is not a multi-tenant identity service.
Configure distinct `RIPPLE_USER_TOKEN` and `RIPPLE_CAREGIVER_TOKEN` values before using live Twilio.
Generate each token with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Send the appropriate token as `Authorization: Bearer TOKEN`.
The API key for OpenAI is separate from these access tokens.

- The resident can submit, clarify, cancel, undo, and replace their preference profile.
- The caregiver can approve, decline, and acknowledge assistance requests.
- Both roles can read this resident's actions, profile, devices, and simulated records.
- Health and API schemas are public. Twilio endpoints require valid provider signatures.
- Leaving both API tokens empty enables local demo mode without authentication.

Bind local demo mode to loopback.
SQLite contains message text and user-reported pain notes; keep the database and tokens private.
The database file uses owner-only permissions.

## Actions and parameters

`POST /tap` accepts `button_id`, a fresh millisecond `timestamp`, `session_id`, optional `location`, and optional `params`.
Unknown actions, unrelated parameters, and invalid bounds return HTTP 422 before model execution.
Validation errors do not echo private inputs.

| Canonical ID | Parameters | Behavior |
|---|---|---|
| `text_home` | `message`, up to 160 characters | Send the exact selected text to the configured home contact after cancellation time. |
| `text_caregiver` | `message`, up to 160 characters | Send the exact selected text to the configured caregiver. |
| `dim_lights` | `brightness`, 0–100 | Apply a simulated light setting and read it back. Supports explicit undo. |
| `set_temperature` | `temperature_f`, 60–80 | Apply a simulated room setting and read it back. Supports explicit undo. |
| `order_lunch` | `order_name` | Prepare an available synthetic order within budget; require exact-order approval before simulated checkout. |
| `log_pain` | `severity`, 0–10; optional `notes`, up to 500 characters | Ask for missing severity; require approval before saving a simulated record. |
| `reposition_bed` | `elevation`, 0–45 | Ask for a missing preset; require approval before moving a simulated bed. |
| `request_drink` | None | Send a water request to the caregiver. Acknowledgement is a separate event. |
| `unlock_door` | None | Require approval for a simulated 15-minute access window. It never calls an emergency contact. |
| `emergency` | Optional device location | Start the contact call and location SMS without waiting for planning or classification. |

`GET /catalog` lists actions and explicit aliases from the exported UI:

| UI ID | Canonical ID |
|---|---|
| `order_doordash` | `order_lunch` |
| `emergency_sos` | `emergency` |
| `adjust_thermostat` | `set_temperature` |
| `water_assistance` | `request_drink` |

Responses expose the canonical `button_id`.
These aliases do not establish DoorDash integration or 911 dispatch.
The frontend must adapt its old `client_timestamp_ms` and `custom_params` fields to the documented request schema.

Example request, with a fresh timestamp substituted at each tap:

```json
{
  "button_id": "log_pain",
  "timestamp": 1792800000000,
  "session_id": "tablet-01",
  "params": {"severity": 4, "notes": "My own report."}
}
```

## Workflow endpoints

| Endpoint | Purpose |
|---|---|
| `POST /tap` | Start an action. HTTP 202 includes an action ID; duplicate taps return HTTP 200 with `status: debounced`. |
| `GET /actions/{id}` | Poll workflow status, plan, clarification, approval details, and tool outcomes. |
| `GET /actions` | Restore activity; filter by `session_id` and `status`, with bounded `limit` and `offset`. |
| `POST /actions/{id}/choice` | Submit `clarification_id` and one offered `choice_id`. |
| `POST /actions/{id}/approval` | Caregiver submits `approved` and the current `approval_fingerprint`. |
| `POST /actions/{id}/cancel` | Stop future execution before it starts. Emergency dispatch cannot be canceled. |
| `POST /actions/{id}/undo` | Undo completed light or temperature changes when no newer change exists. |
| `POST /actions/{id}/acknowledge` | Caregiver acknowledges a completed drink request. This does not establish physical assistance. |
| `GET /profile`, `PUT /profile` | Read or replace the resident's preference profile. PUT uses schema defaults for omitted fields. |
| `GET /devices` | Read persisted simulated device state, including derived door access expiry. |
| `GET /medical-records` | Read simulated user-reported pain records. |

Poll every 750 milliseconds.
The statuses are `classifying`, `pending_cancel`, `awaiting_input`, `awaiting_approval`, `executing`, and terminal outcomes.
Terminal outcomes are `done`, `failed`, `canceled`, `declined`, and `expired`.
Planning occurs before classification for non-emergency actions.
Tier 1 preserves the five-second cancellation window from the accepted tap.
User choices and approvals expire independently.
A stale choice, repeated approval, or changed approval fingerprint returns HTTP 409.
A new action is required when an approved plan changes.

`done` means the tools returned success.
For messaging, initial success means provider acceptance, not confirmed delivery.
Read `provider_status` in each tool result for later updates.
A failed callback changes the action to `failed`; successful earlier results remain visible.
Emergency contact outcomes and `emergency_followup_status` are separate.
Review partial and unknown outcomes before starting another request.

## Planning and model execution

Set `RIPPLE_LIVE_MODELS=true`, `OPENAI_API_KEY`, and an account-supported `RIPPLE_AGENT_MODEL`.
`RIPPLE_DECISIONS_MODEL` defaults to `gpt-6-luna`.
Without live configuration, deterministic planning and template execution remain explicitly labeled.

The read-only SDK planner sees validated candidates and simulated device state.
Candidates include the selected message or reported pain notes when those fields apply.
The planner can request clarification but cannot create tools, recipients, orders, or arbitrary execution arguments.
Explicit user choices cannot be replaced by model preferences.
Unavailable or over-budget lunch choices require a new user selection.
No available lunch produces a failure without checkout or approval requests.

Decisions evaluates server-owned action metadata and selected operation names.
It does not receive contact numbers, GPS coordinates, message text, or pain notes.
The model may raise a tier but cannot remove a backend policy floor.
Confidence below the configured threshold increases the tier.
The threshold remains a prototype setting, not measured model accuracy.
Each Decisions attempt has a bounded timeout and at most one retry.

Execution uses separate preparation and approved tool capabilities.
Messages preserve the exact selected text; the execution agent cannot invent the user's wellbeing.
Approval binds to the action ID, plan, order items, and price.
Checkout rechecks current budget and availability.
Bed, pain-record, and standalone access actions also require approval.
Only the explicit emergency action starts emergency contact dispatch.
SDK tracing is disabled, and exceptions are sanitized.

Responses distinguish `planning_source`, `tier_source`, and execution sources in `tool_results`.
`model_tier` preserves the original choice before policy enforcement.
`classification_fallback_reason` identifies disabled mode, missing keys, refusal, malformed responses, timeout, or API failure.

## Twilio integration

Configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, and all three destination numbers.
Configure `PUBLIC_BASE_URL` as the externally reachable HTTPS base URL.
Set both API access tokens before enabling `RIPPLE_LIVE_TWILIO=true`.
Use teammate-owned test numbers in E.164 format.
The adapter blocks emergency-service short numbers and recipients outside the configured allowlist.

Configure incoming SMS at `POST {PUBLIC_BASE_URL}/twilio/sms`.
Outbound calls and messages set `StatusCallback` to `{PUBLIC_BASE_URL}/twilio/status` automatically.
Both endpoints verify signatures against the exact configured public URL.
Query parameters and repeated form fields are rejected.

The designated caregiver replies `YES act_...` or `NO act_...`.
Bare YES/NO works only with one pending approval.
Approval and webhook deduplication commit together.
Replayed webhook IDs cannot approve another action, including after restart.
Status callbacks tolerate retries, callbacks before REST responses, and older status updates.
Provider acceptance and actual delivery remain distinct.
No outbound operation automatically retries an uncertain send.

GPS absence uses the fixed demo coordinates.
The location SMS explicitly labels this fallback; device coordinates retain their reported accuracy when available.

`RIPPLE_DEMO_APPROVAL=true` enables the backup `POST /demo/approve/{id}?decision=YES` route.
It remains disabled by default and requires the caregiver token when API access control is configured.

## Verification

```sh
python -m pytest -q
ruff check app tests
ruff format --check app tests
python -m pip check
python -m app.smoke
```

Offline tests exercise API routes, all ten actions, real SDK HTTP parsing, scoped tools, and structured planning.
They also cover clarification, approval snapshots, callback order, persistence, restart recovery, and API roles.
The offline smoke command executes all ten actions with mock tools and synthetic approval.
These tests do not measure live model quality or phone delivery.

Opt-in live model checks make paid requests but keep messaging, storage, and device tools isolated:

```sh
python -m app.model_smoke --component decisions
python -m app.model_smoke --component planner
python -m app.model_smoke --component agents
```

The default component `all` runs every path.
Exit code 0 means the requested model paths passed; 1 means failure or fallback; 2 means missing configuration.
Successful fallback execution does not count as live model verification.

## Remaining integration work

Live OpenAI access and actual Twilio delivery require configured credentials and rehearsal.
The frontend still needs request adapters, polling, clarification, approval, and status rendering.
Lights, temperature, beds, locks, medical records, and checkout remain simulated.
Real emergency-service dispatch is absent.
Production identity, multi-resident tenancy, encrypted storage, retention policies, and hardware integrations are outside this prototype.

Sources: [Decisions](https://developers.openai.com/api/docs/guides/decisions), [Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart?lang=python), [Twilio message status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status), [Twilio calls](https://www.twilio.com/docs/voice/api/call-resource).
