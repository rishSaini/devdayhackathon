# Rishabh — Demo integration and release readiness

## Goal
Own the end-to-end demo path and keep the assembled prototype consistent with the README's contract, safety behavior, and judging story.

## Scope
- Integrate backend and Diya's exported frontend once available; verify request/response fields and action status transitions match the README contract.
- Prepare synthetic fixtures (`saved_orders.json`, `tier_cases.json`) and the demo setup/run notes, including smoke-check steps for Decisions API, Twilio SMS/Voice, and ngrok.
- Review the end-to-end Tier 1 cancel, Tier 2 approval/decline/expiry, and Tier 3 fast path for labeled live/mock/fallback states and understandable UI feedback.
- Keep README setup and demo instructions accurate as implementation lands; capture known demo fallbacks without claiming unavailable integrations are live.

## Constraints
- Don't change the locked product scope or weaken safety rules to make the demo look smoother. No real emergency-services calls; use teammate-owned demo numbers only, configured locally.
- Never commit credentials, phone numbers, medical records, or real location data. Keep demo persona and orders synthetic.
- Coordinate changes to backend/frontend ownership with Ben, Karthik, and Diya rather than duplicating their implementation.

## Handoff
- Leave a short integration checklist with what's wired, what's mocked, environment setup, and any remaining blockers so the demo operator can run it reliably.
