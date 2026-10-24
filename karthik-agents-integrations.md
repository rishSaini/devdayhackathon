# Karthik — Agents and external integrations

## Goal
Implement Ripple's model and tool integrations as narrowly scoped modules that plug into the backend core.

## Scope
- Implement Decisions API classification with the README's fixed-choice prompt, pinned timeout/retry settings, confidence round-up, static fallback, and policy-floor enforcement.
- Implement per-tier Agents SDK wrappers and tools from the README. Each tool returns a structured `ok/source/detail` result and catches errors.
- Keep demo smart-home, order, medical-log, and lock tools mocked and clearly labeled. Enforce the 911/112/999 blocklist.

## Ownership boundary
- Twilio SMS, approval messaging/webhook validation, emergency voice, and location SMS are owned by Rishabh. Coordinate interfaces with Rishabh and Ben; do not duplicate those modules.

## Constraints
- Tier 2 finalization is unreachable until a valid approval is received; declining, expiry, or cancellation must not finalize.
- Never let model output choose arbitrary tools, lower the static safety floor, or alter the emergency path.
- Read secrets from environment variables. Do not commit `.env`, phone numbers, or real personal data. Do not log prompt/message/location contents.

## Handoff
- Keep modules aligned with the README repo layout (`decisions.py`, `agents.py`, and `tools/`). Document required env vars and mock/live status. Coordinate route/interface expectations with Ben and Twilio interface expectations with Rishabh.
