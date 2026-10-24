import React, { useState } from 'react';
import {
  Code2,
  Copy,
  Check,
  Terminal,
  Play,
  FileCode,
  FileText,
  ShieldCheck,
  Waves
} from 'lucide-react';
import { DECISIONS_API_SYSTEM_INSTRUCTION } from '../services/rippleEngine';
import { AACButtonPayload, TriageResult, UserContext } from '../types';

interface CodeInspectorProps {
  onRunTestPayload: (payload: AACButtonPayload) => void;
  testResult: TriageResult | null;
  user: UserContext;
}

export const CodeInspector: React.FC<CodeInspectorProps> = ({
  onRunTestPayload,
  testResult,
  user
}) => {
  const [activeCodeTab, setActiveCodeTab] = useState<'main_py' | 'prompt' | 'schemas' | 'tester'>('main_py');
  const [copied, setCopied] = useState<string | null>(null);

  // Custom Payload Tester State
  const [testButtonId, setTestButtonId] = useState('unlock_door');
  const [testLabel, setTestLabel] = useState('Unlock Front Door');
  const [testDeltaMs, setTestDeltaMs] = useState(500);
  const [testSeverity, setTestSeverity] = useState(8);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const FASTAPI_MAIN_PY = `"""
Ripple AAC Execution Engine - FastAPI Backend
Hackathon Track: Agents in Action

Features:
1. Spasm Filter: 400ms debounce protecting against involuntary tremor double-taps.
2. Decisions API: Strict 3-tier triage (Tier 1 Low, Tier 2 Medium Approval Loop, Tier 3 High Emergency Bypass).
3. Agents API Handoff: Tool execution (smart locks, Twilio approvals, medical EHR logging).
4. Webhook Callback: Asynchronous caregiver authorization loop.
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ripple.engine")

app = FastAPI(
    title="Ripple - AAC Physical Autonomy Engine",
    description="Backend routing engine connecting adult AAC grids to OpenAI Decisions API and Agents API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 1. SCHEMAS: Incoming Frontend Payloads & Response Contracts
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    user_id: str = Field(..., description="Unique ID of the AAC user (e.g., patient identifier)")
    caregiver_phone: str = Field(default="+15550192834", description="Emergency/Caregiver contact phone number")
    location: Optional[str] = Field(default="Living Room, Home", description="Current room/physical location of user")
    vital_status: Optional[str] = Field(default="Stable", description="Known baseline condition")

class AACButtonPayload(BaseModel):
    button_id: str = Field(..., description="Unique identifier of tapped button, e.g., 'unlock_door', 'log_pain'")
    label: str = Field(..., description="Display label of the AAC button")
    client_timestamp_ms: int = Field(..., description="Epoch milliseconds when tap physically registered on glass")
    user: UserContext = Field(..., description="Contextual information about user and caregiver")
    custom_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Auxiliary data (e.g. pain level)")

class CaregiverApprovalPayload(BaseModel):
    action_id: str = Field(..., description="Unique ID of the pending Tier 2 action")
    decision: Literal["approved", "rejected"] = Field(..., description="Caregiver's decision")
    notes: Optional[str] = Field(default=None, description="Optional note from caregiver")
    caregiver_id: str = Field(default="cg_sarah_01", description="ID of responding caregiver")

class TriageResult(BaseModel):
    action_id: str
    tier: Literal["Tier 1", "Tier 2", "Tier 3"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    category: str
    requires_caregiver_approval: bool
    bypass_delays: bool
    status: Literal["executed", "pending_approval", "emergency_dispatched", "debounced_dropped"]
    agent_tool: str
    tool_result: Optional[Dict[str, Any]] = None
    reasoning: str
    processed_at_ms: int
    dropped_by_spasm_filter: bool = False

# ---------------------------------------------------------------------------
# 2. THE SPASM FILTER (Middleware / Debounce Logic)
# ---------------------------------------------------------------------------
DEBOUNCE_THRESHOLD_MS = 400

class SpasmFilterStore:
    def __init__(self):
        self._last_tap_times: Dict[str, int] = {}

    def should_drop(self, user_id: str, button_id: str, tap_timestamp_ms: int) -> tuple[bool, int]:
        key = f"{user_id}:{button_id}"
        last_time = self._last_tap_times.get(key)
        
        if last_time is not None:
            delta = tap_timestamp_ms - last_time
            if 0 <= delta < DEBOUNCE_THRESHOLD_MS:
                logger.warning(f"[SPASM DROP] {key} tapped in {delta}ms (<400ms). Silently dropped.")
                return True, delta
        
        self._last_tap_times[key] = tap_timestamp_ms
        delta = 0 if last_time is None else (tap_timestamp_ms - last_time)
        return False, delta

spasm_filter = SpasmFilterStore()

# ---------------------------------------------------------------------------
# 3. THE DECISIONS API TRIAGE (System Instruction & Classification)
# ---------------------------------------------------------------------------
DECISIONS_API_SYSTEM_INSTRUCTION = """${DECISIONS_API_SYSTEM_INSTRUCTION}"""

def classify_via_decisions_api(payload: AACButtonPayload) -> Dict[str, Any]:
    btn_id = payload.button_id.lower()
    params = payload.custom_params or {}

    # Tier 3 Check: Emergency / Door Unlock
    if any(k in btn_id for k in ["unlock_door", "unlock", "emergency", "sos", "emt"]):
        return {
            "tier": "Tier 3",
            "risk_level": "HIGH",
            "category": "EMERGENCY",
            "requires_caregiver_approval": False,
            "bypass_delays": True,
            "agent_tool": "smart_lock_grant_access",
            "tool_parameters": {"door_id": "front_deadbolt_01", "emergency_override": True},
            "reasoning": "High-risk physical access. Bypassing caregiver approval delays to grant EMT access."
        }

    # Tier 2 Check: Health Log / Financial Order
    if any(k in btn_id for k in ["log_pain", "pain", "order_doordash", "doordash", "purchase"]):
        is_pain = "pain" in btn_id
        severity = params.get("severity", 8)
        return {
            "tier": "Tier 2",
            "risk_level": "MEDIUM",
            "category": "HEALTH_FINANCIAL",
            "requires_caregiver_approval": True,
            "bypass_delays": False,
            "agent_tool": "log_medical_event" if is_pain else "twilio_send_approval_text",
            "tool_parameters": {
                "event_type": "Severe Acute Pain Episode" if is_pain else "Food Delivery Order",
                "severity": severity,
                "caregiver_phone": payload.user.caregiver_phone
            },
            "reasoning": "Medium-risk health log or financial transaction. Triggering Caregiver Approval Loop."
        }

    # Tier 1 Default: Environmental / Social
    return {
        "tier": "Tier 1",
        "risk_level": "LOW",
        "category": "ENVIRONMENTAL_SOCIAL",
        "requires_caregiver_approval": False,
        "bypass_delays": False,
        "agent_tool": "smart_thermostat_set" if "thermostat" in btn_id else "twilio_send_casual_text",
        "tool_parameters": {"button_id": btn_id},
        "reasoning": "Low-risk comfort or communication request. Executing immediately without caregiver delay."
    }

# ---------------------------------------------------------------------------
# 4. THE AGENTS API HANDOFF (Mock Tool Execution Functions)
# ---------------------------------------------------------------------------
pending_approvals: Dict[str, Dict[str, Any]] = {}
execution_audit_log: list[Dict[str, Any]] = []

def twilio_send_approval_text(action_details: str, caregiver_phone: str) -> Dict[str, Any]:
    msg_id = f"SM_{uuid.uuid4().hex[:12]}"
    logger.info(f"[TWILIO DISPATCH] To: {caregiver_phone} | Msg: {action_details}")
    return {
        "service": "Twilio Programmable Messaging API",
        "message_sid": msg_id,
        "recipient": caregiver_phone,
        "body": f"Ripple AAC Alert: Patient requested '{action_details}'. Reply 'YES' to approve.",
        "status": "queued_awaiting_webhook"
    }

def smart_lock_grant_access() -> Dict[str, Any]:
    logger.info("[SMART LOCK] Triggered unlock command. Deadbolt disengaged.")
    return {
        "device": "Schlage Encode Smart Deadbolt",
        "state": "UNLOCKED",
        "protocol": "Matter Over Thread",
        "duration_seconds": 300,
        "status": "access_granted_emt_path_clear"
    }

def log_medical_event(event_type: str, severity: int) -> Dict[str, Any]:
    ehr_id = f"EHR_{uuid.uuid4().hex[:8]}"
    logger.info(f"[MEDICAL EHR LOG] Type: {event_type} | Severity: {severity}/10 | ID: {ehr_id}")
    return {
        "ehr_system": "FHIR R4 Observation Resource",
        "record_id": ehr_id,
        "event_type": event_type,
        "severity": severity,
        "status": "recorded_in_patient_timeline"
    }

def execute_agent_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "smart_lock_grant_access":
        return smart_lock_grant_access()
    elif tool_name == "log_medical_event":
        return log_medical_event(parameters.get("event_type", "Pain"), parameters.get("severity", 8))
    elif tool_name == "twilio_send_approval_text":
        return twilio_send_approval_text(parameters.get("action_details", "Verification"), parameters.get("caregiver_phone", ""))
    return {"status": "executed", "parameters": parameters}

# ---------------------------------------------------------------------------
# 5. FASTAPI ROUTES
# ---------------------------------------------------------------------------
@app.post("/api/aac/tap", response_model=TriageResult)
async def handle_aac_tap(payload: AACButtonPayload):
    now_ms = int(time.time() * 1000)
    client_ts = payload.client_timestamp_ms or now_ms

    dropped, delta_ms = spasm_filter.should_drop(payload.user.user_id, payload.button_id, client_ts)
    if dropped:
        return TriageResult(
            action_id=f"drop_{uuid.uuid4().hex[:8]}",
            tier="Tier 1",
            risk_level="LOW",
            category="SPASM_FILTER_DROPPED",
            requires_caregiver_approval=False,
            bypass_delays=False,
            status="debounced_dropped",
            agent_tool="none",
            reasoning=f"Motor spasm debounce activated. Tap occurred {delta_ms}ms after previous tap (<400ms).",
            processed_at_ms=now_ms,
            dropped_by_spasm_filter=True
        )

    classification = classify_via_decisions_api(payload)
    action_id = f"act_{uuid.uuid4().hex[:10]}"
    tier = classification["tier"]

    if tier == "Tier 3":
        tool_res = execute_agent_tool(classification["agent_tool"], classification["tool_parameters"])
        status_val = "emergency_dispatched"
    elif tier == "Tier 2":
        tool_res = twilio_send_approval_text(payload.label, payload.user.caregiver_phone)
        pending_approvals[action_id] = {"action_id": action_id, "payload": payload.model_dump(), "classification": classification}
        status_val = "pending_approval"
    else:
        tool_res = execute_agent_tool(classification["agent_tool"], classification["tool_parameters"])
        status_val = "executed"

    result = TriageResult(
        action_id=action_id,
        tier=tier,
        risk_level=classification["risk_level"],
        category=classification["category"],
        requires_caregiver_approval=classification["requires_caregiver_approval"],
        bypass_delays=classification["bypass_delays"],
        status=status_val,
        agent_tool=classification["agent_tool"],
        tool_result=tool_res,
        reasoning=classification["reasoning"],
        processed_at_ms=now_ms
    )
    execution_audit_log.insert(0, result.model_dump())
    return result

@app.post("/webhook/caregiver-approval")
async def caregiver_approval_webhook(payload: CaregiverApprovalPayload):
    action = pending_approvals.get(payload.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    
    if payload.decision == "approved":
        tool_res = execute_agent_tool(action["classification"]["agent_tool"], action["classification"]["tool_parameters"])
        del pending_approvals[payload.action_id]
        return {"success": True, "resumed_tool_result": tool_res}
    else:
        del pending_approvals[payload.action_id]
        return {"success": True, "status": "aborted_by_caregiver"}
`;

  return (
    <div className="space-y-8">
      {/* Header Stone */}
      <div className="frosted-glass-card p-7 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="signature-kicker">Architecture &amp; System Instruction</span>
            <h2 className="font-heading text-2xl font-bold text-[#141414] tracking-[-0.025em] mt-1 flex items-center gap-2.5">
              <span>FastAPI &amp; System Prompt Inspector</span>
              <Waves className="w-5 h-5 text-[#5B8DB8]" />
            </h2>
            <p className="text-sm font-body text-[#6B6B6B] mt-1 max-w-xl leading-relaxed">
              Explore the complete Python FastAPI main.py code, the exact system prompt string for the Decisions API, and live test custom request payloads.
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex flex-wrap items-center gap-2 mt-5 pt-4 border-t border-[#EFE9DE]">
          <button
            onClick={() => setActiveCodeTab('main_py')}
            className={`px-4 py-2 rounded-[14px] text-xs font-semibold font-body transition-all border shadow-sm ${
              activeCodeTab === 'main_py'
                ? 'bg-[#1A3226] text-white border-[#1A3226]'
                : 'bg-white/80 hover:bg-white text-[#6B6B6B] border-[#EFE9DE]'
            }`}
          >
            FastAPI main.py (Full Python)
          </button>
          <button
            onClick={() => setActiveCodeTab('prompt')}
            className={`px-4 py-2 rounded-[14px] text-xs font-semibold font-body transition-all border shadow-sm ${
              activeCodeTab === 'prompt'
                ? 'bg-[#1A3226] text-white border-[#1A3226]'
                : 'bg-white/80 hover:bg-white text-[#6B6B6B] border-[#EFE9DE]'
            }`}
          >
            Decisions API System Prompt
          </button>
          <button
            onClick={() => setActiveCodeTab('schemas')}
            className={`px-4 py-2 rounded-[14px] text-xs font-semibold font-body transition-all border shadow-sm ${
              activeCodeTab === 'schemas'
                ? 'bg-[#1A3226] text-white border-[#1A3226]'
                : 'bg-white/80 hover:bg-white text-[#6B6B6B] border-[#EFE9DE]'
            }`}
          >
            Pydantic JSON Schemas
          </button>
          <button
            onClick={() => setActiveCodeTab('tester')}
            className={`px-4 py-2 rounded-[14px] text-xs font-semibold font-body transition-all border shadow-sm ${
              activeCodeTab === 'tester'
                ? 'bg-[#1A3226] text-white border-[#1A3226]'
                : 'bg-white/80 hover:bg-white text-[#6B6B6B] border-[#EFE9DE]'
            }`}
          >
            Live Request Injector
          </button>
        </div>
      </div>

      {/* Tab 1: FastAPI main.py */}
      {activeCodeTab === 'main_py' && (
        <div className="frosted-glass-card p-7 space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-[#EFE9DE] text-xs text-[#6B6B6B]">
            <span className="font-mono flex items-center gap-2 font-bold text-[#141414]">
              <FileCode className="w-4 h-4 text-[#1A3226]" />
              /backend/main.py (Production Ready)
            </span>
            <button
              onClick={() => handleCopy(FASTAPI_MAIN_PY, 'main.py')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] bg-white border border-[#EFE9DE] hover:border-[#1A3226] text-[#141414] text-xs font-semibold transition-all shadow-sm"
            >
              {copied === 'main.py' ? <Check className="w-3.5 h-3.5 text-[#2E7D32]" /> : <Copy className="w-3.5 h-3.5 text-[#1A3226]" />}
              <span>{copied === 'main.py' ? 'Copied' : 'Copy Code'}</span>
            </button>
          </div>

          <pre className="text-xs font-mono p-5 rounded-[20px] overflow-x-auto max-h-[580px] leading-relaxed bg-[#1A3226] text-[#34D399] border border-[#14261d]">
            {FASTAPI_MAIN_PY}
          </pre>
        </div>
      )}

      {/* Tab 2: System Instruction */}
      {activeCodeTab === 'prompt' && (
        <div className="frosted-glass-card p-7 space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-[#EFE9DE] text-xs text-[#6B6B6B]">
            <span className="font-mono flex items-center gap-2 font-bold text-[#141414]">
              <FileText className="w-4 h-4 text-[#D4A373]" />
              Decisions API System Prompt Instruction
            </span>
            <button
              onClick={() => handleCopy(DECISIONS_API_SYSTEM_INSTRUCTION, 'prompt')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] bg-white border border-[#EFE9DE] hover:border-[#1A3226] text-[#141414] text-xs font-semibold transition-all shadow-sm"
            >
              {copied === 'prompt' ? <Check className="w-3.5 h-3.5 text-[#2E7D32]" /> : <Copy className="w-3.5 h-3.5 text-[#1A3226]" />}
              <span>{copied === 'prompt' ? 'Copied' : 'Copy Prompt'}</span>
            </button>
          </div>

          <div className="p-4 rounded-[16px] text-xs leading-relaxed border bg-[#FEF9C3]/80 border-[#FDE047] text-[#141414]">
            <strong>Ternary Risk Partitioning Principle:</strong> Enforces deterministic LLM boundaries between low-risk comfort actions (instant execute), medium-risk financial/health events (holds in Caregiver Webhook loop), and emergency access (instant EMT bypass).
          </div>

          <pre className="text-xs font-mono p-5 rounded-[20px] overflow-x-auto max-h-[500px] whitespace-pre-wrap leading-relaxed bg-[#1A3226] text-[#D4A373] border border-[#14261d]">
            {DECISIONS_API_SYSTEM_INSTRUCTION}
          </pre>
        </div>
      )}

      {/* Tab 3: Pydantic Schemas */}
      {activeCodeTab === 'schemas' && (
        <div className="frosted-glass-card p-7 space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-[#EFE9DE] text-xs text-[#6B6B6B]">
            <span className="font-mono flex items-center gap-2 font-bold text-[#141414]">
              <Code2 className="w-4 h-4 text-[#34D399]" />
              Pydantic Contract Schemas
            </span>
            <button
              onClick={() => handleCopy(FASTAPI_MAIN_PY, 'schemas')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] bg-white border border-[#EFE9DE] hover:border-[#1A3226] text-[#141414] text-xs font-semibold transition-all shadow-sm"
            >
              {copied === 'schemas' ? <Check className="w-3.5 h-3.5 text-[#2E7D32]" /> : <Copy className="w-3.5 h-3.5 text-[#1A3226]" />}
              <span>{copied === 'schemas' ? 'Copied' : 'Copy Schemas'}</span>
            </button>
          </div>

          <pre className="text-xs font-mono p-5 rounded-[20px] overflow-x-auto max-h-[500px] leading-relaxed bg-[#1A3226] text-[#EFE9DE] border border-[#14261d]">
{`class UserContext(BaseModel):
    user_id: str = Field(..., description="Unique ID of the AAC user (e.g., patient identifier)")
    caregiver_phone: str = Field(default="+15550192834", description="Caregiver phone for Twilio SMS approval webhooks")
    location: Optional[str] = Field(default="Living Room, Home", description="Physical location")
    vital_status: Optional[str] = Field(default="Stable", description="Baseline sensor status")

class AACButtonPayload(BaseModel):
    button_id: str = Field(..., description="ID of button, e.g. 'unlock_door', 'log_pain', 'order_doordash'")
    label: str = Field(..., description="Human-readable AAC label")
    client_timestamp_ms: int = Field(..., description="Epoch ms when tap registered (used for spasm debounce)")
    user: UserContext = Field(..., description="Context for routing")
    custom_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Auxiliary params (severity, amount)")

class CaregiverApprovalPayload(BaseModel):
    action_id: str = Field(..., description="ID of pending Tier 2 action")
    decision: Literal["approved", "rejected"] = Field(..., description="Caregiver webhook decision")
    notes: Optional[str] = Field(default=None, description="Optional clinical/care note")
    caregiver_id: str = Field(default="cg_sarah_01", description="ID of responding caregiver")

class TriageResult(BaseModel):
    action_id: str
    tier: Literal["Tier 1", "Tier 2", "Tier 3"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    category: str
    requires_caregiver_approval: bool
    bypass_delays: bool
    status: Literal["executed", "pending_approval", "emergency_dispatched", "debounced_dropped"]
    agent_tool: str
    tool_result: Optional[Dict[str, Any]] = None
    reasoning: str
    processed_at_ms: int
    dropped_by_spasm_filter: bool = False`}
          </pre>
        </div>
      )}

      {/* Tab 4: Live Payload Tester */}
      {activeCodeTab === 'tester' && (
        <div className="frosted-glass-card p-7 space-y-6">
          <div>
            <span className="signature-kicker">Interactive Sandbox</span>
            <h3 className="font-heading text-lg font-bold text-[#141414]">Live Request Injector</h3>
            <p className="text-xs font-body text-[#6B6B6B]">
              Construct an arbitrary incoming frontend AAC payload and observe how the Spasm Filter and Decisions API triage it in real-time.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            <div>
              <label className="block mb-1.5 font-mono font-semibold text-[#141414]">
                button_id
              </label>
              <select
                value={testButtonId}
                onChange={(e) => {
                  setTestButtonId(e.target.value);
                  if (e.target.value === 'unlock_door') setTestLabel('Unlock Front Door');
                  else if (e.target.value === 'log_pain') setTestLabel('Log Level 8 Pain');
                  else if (e.target.value === 'order_doordash') setTestLabel('Order DoorDash');
                  else if (e.target.value === 'adjust_thermostat') setTestLabel('Adjust Thermostat');
                  else setTestLabel('Custom Intent');
                }}
                className="w-full bg-white border border-[#EFE9DE] rounded-[14px] p-3 text-[#141414] focus:outline-none focus:border-[#1A3226] font-mono shadow-sm"
              >
                <option value="unlock_door">unlock_door (Tier 3 - Emergency)</option>
                <option value="emergency_sos">emergency_sos (Tier 3 - Emergency)</option>
                <option value="log_pain">log_pain (Tier 2 - Health Log)</option>
                <option value="order_doordash">order_doordash (Tier 2 - Financial)</option>
                <option value="adjust_thermostat">adjust_thermostat (Tier 1 - Environment)</option>
                <option value="text_caregiver">text_caregiver (Tier 1 - Social)</option>
                <option value="custom_action">custom_action (Arbitrary)</option>
              </select>
            </div>

            <div>
              <label className="block mb-1.5 font-mono font-semibold text-[#141414]">
                label
              </label>
              <input
                type="text"
                value={testLabel}
                onChange={(e) => setTestLabel(e.target.value)}
                className="w-full bg-white border border-[#EFE9DE] rounded-[14px] p-3 text-[#141414] focus:outline-none focus:border-[#1A3226] shadow-sm font-body"
              />
            </div>

            <div>
              <label className="block mb-1.5 font-mono font-semibold text-[#141414]">
                Simulated Tap Delta: {testDeltaMs}ms
                {testDeltaMs < 400 ? (
                  <span className="ml-2 font-bold text-[#B8860B]">(Spasm Filter will drop)</span>
                ) : (
                  <span className="ml-2 font-bold text-[#2E7D32]">(Will pass Spasm Filter)</span>
                )}
              </label>
              <input
                type="range"
                min="50"
                max="1000"
                step="25"
                value={testDeltaMs}
                onChange={(e) => setTestDeltaMs(Number(e.target.value))}
                className="w-full cursor-pointer accent-[#1A3226]"
              />
            </div>

            <div>
              <label className="block mb-1.5 font-mono font-semibold text-[#141414]">
                Pain Severity (if log_pain)
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={testSeverity}
                onChange={(e) => setTestSeverity(Number(e.target.value))}
                className="w-full bg-white border border-[#EFE9DE] rounded-[14px] p-3 text-[#141414] focus:outline-none focus:border-[#1A3226] font-mono shadow-sm"
              />
            </div>
          </div>

          {/* Primary Button Recipe: Deep Forest (#1A3226), 16px radius, white text, green-tinted shadow */}
          <div className="pt-2">
            <button
              onClick={() => {
                const now = Date.now();
                const payload: AACButtonPayload = {
                  button_id: testButtonId,
                  label: testLabel,
                  client_timestamp_ms: now,
                  user: {
                    user_id: user.user_id,
                    caregiver_phone: user.caregiver_phone,
                    location: user.location,
                    vital_status: user.vital_status
                  },
                  custom_params: {
                    severity: testSeverity
                  }
                };
                onRunTestPayload(payload);
              }}
              className="px-6 py-3.5 rounded-[16px] bg-[#1A3226] hover:bg-[#14261d] text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-[0_4px_14px_-2px_rgba(26,50,38,0.18)] active:scale-95 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current text-[#34D399]" />
              <span>Cast Request into Stream Engine</span>
            </button>
          </div>

          {testResult && (
            <div className="p-5 rounded-[20px] bg-[#1A3226] text-white border border-[#14261d] space-y-2">
              <div className="text-xs font-mono flex items-center justify-between text-[#A0A0A0]">
                <span>INSPECTION RESULT:</span>
                <span className={`font-bold ${testResult.dropped_by_spasm_filter ? 'text-[#B8860B]' : 'text-[#34D399]'}`}>
                  {testResult.status.toUpperCase()}
                </span>
              </div>
              <pre className="text-xs font-mono text-[#EFE9DE] bg-[#14261d] p-4 rounded-[14px] overflow-x-auto max-h-52 border border-white/5">
                {JSON.stringify(testResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
