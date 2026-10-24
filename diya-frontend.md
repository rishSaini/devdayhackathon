# Diya — Ripple frontend (AI Studio)

## Goal
Build Ripple's tablet-style React frontend in AI Studio. Export the frontend source into this repository later so it can be wired to the FastAPI backend.

## Scope
- Create a one-page, adult-oriented AAC interface with a high-contrast 2×2 grid and four large action tiles: Text Home (`text_home`), Dim Lights (`dim_lights`), Order Lunch (`order_lunch`), Emergency (`emergency`).
- Make touch targets large and separated for tremor-friendly use. Use `pointerdown` for activation and prevent accidental repeated taps where practical.
- Show each action's status and risk tier/source when supplied by the API; display the large cancel target and 5-second countdown for Tier 1.
- Include clear offline/error and labeled mock/fallback states. Never show success if the backend reports failure or is unreachable.
- Keep UI and API access separable. Include a small API module with placeholders for `POST /tap`, `GET /actions/{action_id}` polling (750 ms), and `POST /actions/{action_id}/cancel`.

## Contract and constraints
- Follow the frozen API contract and product decisions in the root README. Use `button_id`, `timestamp`, `session_id`, and optional `location` in tap requests.
- No websockets, extra tiles, settings UI, authentication, or new product scope.
- Keep synthetic demo content; do not commit phone numbers, secrets, or real user data.

## Handoff
- Keep the export self-contained with a README noting the AI Studio export steps, run command, and required environment variables (for example, backend base URL).
- When ready, export the files into `frontend/` in this repo. Tell the team which generated files were touched and any dependency/build assumptions. Coordinate before overwriting any existing hand-written integration work.
