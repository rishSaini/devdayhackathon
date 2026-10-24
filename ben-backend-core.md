# Ben — FastAPI backend core

## Goal
Implement Ripple's contract-first backend skeleton and deterministic safety path described in the root README.

## Scope
- Create the FastAPI app, Pydantic request/response schemas, health endpoint, in-memory action store, and the `/tap`, `/actions/{action_id}`, and `/actions/{action_id}/cancel` routes.
- Implement the frozen four-button registry, 400 ms per-session/per-button spasm filter, and static risk tiers/policy floors.
- Implement the Tier 1 five-second cancellation window and status transitions. Return clear JSON errors and never report success when an action failed.
- Keep external/model calls behind small interfaces so integrations can be connected without weakening the deterministic guards.

## Constraints
- Treat the root README API contract and locked decisions as authoritative. Unknown button IDs must be rejected before any model call. The model cannot override policy floors, debounce, cancellation, or approval gates.
- Use an in-memory store; no database, websockets, auth, or new scope.
- Add only synthetic data. Keep secrets in environment variables and never log message contents or location.

## Handoff
- Provide `backend/app/` implementation, `.env.example`, and `requirements.txt` as appropriate. Document how to start the server and any contract assumptions for frontend integration.
