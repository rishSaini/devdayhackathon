# Karthik — Agents and external integrations

## Goal
Implement Ripple's model and tool integrations as narrowly scoped modules that plug into the backend core.

## Scope
- Implement Decisions API classification with the README's fixed-choice prompt, pinned timeout/retry settings, confidence round-up, static fallback, and policy-floor enforcement.
- Implement per-tier Agents SDK wrappers and tools from the README. Each tool returns a structured `ok/source/detail` result and catches errors.
- Add Twilio SMS, approval SMS, inbound YES/NO webhook handling with signature validation, emergency voice call, and location SMS. Keep the emergency voice/SMS dispatch deterministic and immediate; don't wait for an agent decision.
- Keep demo smart-home, order, medical-log, and lock tools mocked and clearly labeled. Enforce the 911/112/999 blocklist.

## Constraints
- Tier 2 finalization is unreachable until a valid approval is received; declining, expiry, or cancellation must not finalize.
- Never let model output choose arbitrary tools, lower the static safety floor, or alter the emergency path.
- Read secrets from environment variables. Do not commit `.env`, phone numbers, or real personal data. Do not log prompt/message/location contents.

## Handoff
- Keep modules aligned with the README repo layout (`decisions.py`, `agents.py`, and `tools/`). Document required env vars and mock/live status. Coordinate route/interface expectations with Ben before wiring the webhook.
