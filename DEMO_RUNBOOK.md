# Ripple demo runbook

This runbook follows the frozen product contract in the root README. The repository currently contains planning docs and fixtures; backend and frontend implementation files have not landed yet. Treat every command below as the intended bring-up sequence once the corresponding implementation exists. Do not describe a feature as live until the phone and UI behavior have been observed during rehearsal.

## Before rehearsal

1. Confirm `backend/` and `frontend/` contain the implementation, and read their local setup instructions if present.
2. Create `backend/.env` from `backend/.env.example`. Use only team-controlled test numbers and synthetic persona data. Never put `.env` in Git.
3. Verify the `EMERGENCY_CONTACT` is a teammate's number, not an emergency-services number. Keep the README blocklist (`911`, `112`, `999`) in force.
4. Check the backend uses the frozen `POST /tap`, `GET /actions/{action_id}`, `POST /actions/{action_id}/cancel`, `POST /twilio/sms`, and `GET /healthz` contract.
5. Confirm each response and UI state visibly distinguishes `live`, `fallback`, and `mock`. Backend unavailable must say that nothing was sent.

## Start the prototype

Use separate terminals from the repository root. These commands match the README; adapt only if the implementation's package scripts differ.

```powershell
# Terminal 1: backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2: public webhook tunnel (needed for inbound Twilio replies)
ngrok http 8000
```

Copy the HTTPS forwarding URL into `PUBLIC_BASE_URL` in `backend/.env`, then configure the Twilio number's inbound Messaging webhook to `POST {PUBLIC_BASE_URL}/twilio/sms`. Restart the backend after environment changes.

```powershell
# Terminal 3: frontend
cd frontend
npm install
npm run dev
```

Open the URL printed by the frontend dev server (the planned default is `http://localhost:5173`). Check `/healthz` before attempting live integrations. Report accurately which integrations are live, fallback, or mock.

## Smoke checks

Start with local health and synthetic behavior. Do not send a real SMS or voice call until the team has confirmed the configured destination numbers and explicitly selected a rehearsal window.

- **Backend health:** open `http://localhost:8000/healthz`; verify reported integration states and fallback labels.
- **Decisions API:** use the implementation's smoke command with `order_lunch`; confirm a fixed choice is returned. A missing entitlement, timeout, or refusal must visibly use static fallback.
- **Twilio SMS and Voice:** after confirming the test recipient and Twilio configuration, run the backend's documented smoke commands. Verify the handset receives the SMS and speaks the call; trial-account prompts and carrier delays may affect the result.
- **Webhook:** send an approval reply from the configured caregiver phone through the public tunnel. Confirm signature validation and matching of YES/NO to the pending action.
- **Frontend/backend:** tap each of the four visible tiles and verify the emitted button ID, timestamp, session ID, and returned action status. Poll every 750 ms per contract.

If implementation modules do not yet expose README's proposed command-line smoke entry points, do not claim that smoke test passed; validate through the available health/API endpoint and record the gap for the owner.

## End-to-end rehearsal checklist

- [ ] **Spasm filter:** rapid repeat of one tile is debounced; it creates no duplicate side effect.
- [ ] **Tier 1:** Text Home and Dim Lights show the five-second cancel window. Cancel stops execution; otherwise action completes. Lights are labeled simulated. Text delivery is called live only after confirmed handset receipt.
- [ ] **Tier 2:** Order Lunch uses the synthetic `usual_lunch` fixture (`$12.40`). Approval request is sent to the configured caregiver. Test YES, NO, timeout/expiry, and user cancel; only YES may start finalization. Checkout remains a clearly labeled mock.
- [ ] **Tier 3:** Emergency has no cancel delay or approval wait. A confirmed teammate test number receives the voice call and location SMS. The path never calls 911/112/999; mock follow-up actions remain labeled.
- [ ] **Fallbacks:** disable or misconfigure one integration in a safe local rehearsal. The UI labels fallback/offline behavior and never fakes success.
- [ ] **Privacy:** use synthetic Alex/order/location data, and confirm logs do not contain prompt text, SMS contents, phone numbers, or location coordinates.

## Demo operator notes

Keep the presenter's phone face-up with ringer on and volume up, and use a second team-controlled phone for caregiver approval. Preflight the tunnel URL and Twilio webhook. If carrier delivery is slow, use the explicitly labeled manual approval backup only if the backend provides it. If backend is unavailable, show the offline state; if the venue blocks the tunnel, use a prerecorded run and label it as recorded.

## Current integration handoff

- **Present:** README contract and demo plan; synthetic order and tier classification fixtures.
- **Awaiting implementation:** FastAPI routes/state machine, Decisions/Agents/Twilio modules, and the AI Studio frontend export.
- **Recheck on integration:** request/response and state transitions, frontend polling/cancel wiring, webhook signature validation, labeled source states, and the full checklist above.
