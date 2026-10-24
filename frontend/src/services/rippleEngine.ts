import { AACButtonPayload, TriageResult, UserContext } from '../types';

export const DEBOUNCE_THRESHOLD_MS = 400;

export const DECISIONS_API_SYSTEM_INSTRUCTION = `You are the Ripple Decisions Engine, a deterministic safety classifier for an AAC physical
autonomy system serving adults with ALS or stroke recovery.

Your job is to classify incoming AAC button intents into one of THREE strict risk tiers.
You must adhere strictly to these safety boundaries:

TIER 1 (Low Risk - Environmental / Social / Comfort):
- Examples: Adjusting thermostat, turning smart lights on/off, playing relaxing audio,
  sending a casual check-in SMS ("I am resting", "Good morning"), repositioning bed angle,
  requesting a glass of water.
- Action: Execute tool IMMEDIATELY without human confirmation.
- requires_caregiver_approval: false
- bypass_delays: false

TIER 2 (Medium Risk - Health Logging / Financial Transactions / Physical Supplies):
- Examples: Logging severe health episodes (e.g. pain level >= 6, shortness of breath),
  ordering food or groceries via DoorDash/Instacart, scheduling transport, purchasing medical supplies.
- Action: PAUSE execution. Trigger a Caregiver Approval Loop via Twilio SMS webhook.
- requires_caregiver_approval: true
- bypass_delays: false

TIER 3 (High Risk - Immediate Life Safety / Emergency / Physical Access):
- Examples: Unlocking exterior smart door for EMTs / first responders, activating SOS alarm,
  dispatching emergency 911 dispatch notification, critical respiratory distress alert.
- Action: BYPASS ALL QUEUES AND DELAYS. Execute tool IMMEDIATELY and parallel-broadcast emergency alert.
- requires_caregiver_approval: false
- bypass_delays: true

Respond with exact JSON containing:
{
  "tier": "Tier 1" | "Tier 2" | "Tier 3",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "category": "ENVIRONMENTAL_SOCIAL" | "HEALTH_FINANCIAL" | "EMERGENCY",
  "requires_caregiver_approval": boolean,
  "bypass_delays": boolean,
  "agent_tool": string,
  "tool_parameters": object,
  "reasoning": string
}`;

export const DEFAULT_USER: UserContext = {
  user_id: "patient_als_robert_m",
  name: "Robert M. (ALS Phase 3)",
  caregiver_name: "Sarah M. (Spouse & Caregiver)",
  caregiver_phone: "+1 (555) 019-2834",
  location: "Living Room / Motorized Recliner",
  vital_status: "SpO2 97% · Pulse 72 · Stable"
};

// Spasm Filter Memory Store
class SpasmFilterStore {
  private lastTapTimes: Map<string, number> = new Map();

  shouldDrop(userId: string, buttonId: string, tapTimeMs: number): { shouldDrop: boolean; deltaMs: number } {
    const key = `${userId}:${buttonId}`;
    const lastTime = this.lastTapTimes.get(key);

    if (lastTime !== undefined) {
      const delta = tapTimeMs - lastTime;
      if (delta >= 0 && delta < DEBOUNCE_THRESHOLD_MS) {
        return { shouldDrop: true, deltaMs: delta };
      }
    }

    this.lastTapTimes.set(key, tapTimeMs);
    const deltaMs = lastTime !== undefined ? tapTimeMs - lastTime : 0;
    return { shouldDrop: false, deltaMs };
  }

  clear() {
    this.lastTapTimes.clear();
  }
}

export const clientSpasmFilter = new SpasmFilterStore();

// Mock Agent Tools
export function smart_lock_grant_access() {
  return {
    device: "Schlage Encode Smart Deadbolt",
    device_id: "lock_front_01",
    state: "UNLOCKED",
    protocol: "Matter Over Thread / Z-Wave",
    duration_seconds: 300,
    status: "access_granted_emt_path_clear",
    unlocked_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  };
}

export function log_medical_event(eventType: string, severity: number) {
  const ehrId = `EHR-${Math.floor(100000 + Math.random() * 900000)}`;
  return {
    ehr_system: "FHIR R4 Observation Resource",
    record_id: ehrId,
    code: "8310-5 (Pain Severity Rating)",
    event_type: eventType,
    severity: severity,
    scale: "0-10 Wong-Baker FACES / Numeric",
    status: "recorded_in_patient_timeline",
    timestamp: new Date().toLocaleTimeString()
  };
}

export function twilio_send_approval_text(actionDetails: string, caregiverPhone: string) {
  const sid = `SM${Math.random().toString(36).substring(2, 14)}`;
  return {
    service: "Twilio Programmable Messaging API",
    message_sid: sid,
    recipient: caregiverPhone,
    body: `Ripple AAC Alert: Patient requested '${actionDetails}'. Reply 'YES' to approve or review in Caregiver Portal.`,
    status: "queued_awaiting_webhook",
    sent_at: Date.now()
  };
}

export function adjust_smart_thermostat(temp: number) {
  return {
    device: "Google Nest Learning Thermostat",
    target_temp_f: temp,
    mode: "COOL/ECO",
    state: "target_reached"
  };
}

// Full Decisions API Triage Logic (Mirrors Python backend exactly)
export function processAACTapLocally(payload: AACButtonPayload): TriageResult {
  const nowMs = Date.now();
  const tapTs = payload.client_timestamp_ms || nowMs;

  // Step 1: Spasm Filter
  const { shouldDrop, deltaMs } = clientSpasmFilter.shouldDrop(
    payload.user.user_id,
    payload.button_id,
    tapTs
  );

  if (shouldDrop) {
    return {
      action_id: `drop_${Math.random().toString(36).substring(2, 10)}`,
      tier: 'Tier 1',
      risk_level: 'LOW',
      category: 'SPASM_FILTER_DROPPED',
      requires_caregiver_approval: false,
      bypass_delays: false,
      status: 'debounced_dropped',
      agent_tool: 'none',
      tool_result: { delta_ms: deltaMs, threshold_ms: DEBOUNCE_THRESHOLD_MS },
      reasoning: `Motor spasm debounce activated. Tap registered ${deltaMs}ms after previous tap (< 400ms threshold). Silently dropped to prevent accidental double-execution.`,
      processed_at_ms: nowMs,
      dropped_by_spasm_filter: true,
      delta_ms: deltaMs
    };
  }

  const btnId = payload.button_id.toLowerCase();
  const params = payload.custom_params || {};

  // Step 2: Decisions API Classification
  // Tier 3: Emergency / Smart Lock
  if (btnId.includes('unlock_door') || btnId.includes('unlock') || btnId.includes('emergency') || btnId.includes('sos')) {
    const isDoor = btnId.includes('door') || btnId.includes('unlock');
    const toolResult = isDoor ? smart_lock_grant_access() : {
      service: "911 CAD & First Responder Dispatch",
      priority: "CRITICAL_ALPHA",
      protocol: "Rapid EMT Notification",
      lat_long: "37.7749,-122.4194",
      audio_beacon: "ENABLED"
    };

    return {
      action_id: `act_${Math.random().toString(36).substring(2, 10)}`,
      tier: 'Tier 3',
      risk_level: 'HIGH',
      category: 'EMERGENCY',
      requires_caregiver_approval: false,
      bypass_delays: true,
      status: 'emergency_dispatched',
      agent_tool: isDoor ? 'smart_lock_grant_access' : 'emergency_dispatch_sos',
      tool_result: toolResult,
      reasoning: "High-risk physical access or emergency detected. Bypassing all caregiver approval delays to grant immediate entry or trigger EMT assistance.",
      processed_at_ms: nowMs,
      dropped_by_spasm_filter: false,
      delta_ms: deltaMs
    };
  }

  // Tier 2: Health Log / Financial / Supplies
  if (btnId.includes('log_pain') || btnId.includes('pain') || btnId.includes('doordash') || btnId.includes('order')) {
    const isPain = btnId.includes('pain');
    const severity = params.severity ?? 8;
    const actionDetails = isPain
      ? `Patient reported Acute Level ${severity} Pain (requires medication evaluation)`
      : `DoorDash Order ($24.50: Broth, Electrolyte Hydration, Rice)`;

    const smsResult = twilio_send_approval_text(actionDetails, payload.user.caregiver_phone);

    return {
      action_id: `act_${Math.random().toString(36).substring(2, 10)}`,
      tier: 'Tier 2',
      risk_level: 'MEDIUM',
      category: 'HEALTH_FINANCIAL',
      requires_caregiver_approval: true,
      bypass_delays: false,
      status: 'pending_approval',
      agent_tool: isPain ? 'log_medical_event' : 'twilio_send_approval_text',
      tool_result: smsResult,
      reasoning: "Medium-risk health log or financial transaction. Pausing execution and routing to Caregiver Approval Loop via Twilio SMS webhook.",
      processed_at_ms: nowMs,
      dropped_by_spasm_filter: false,
      delta_ms: deltaMs
    };
  }

  // Tier 1: Environmental / Social / Comfort
  let toolResult: any;
  let toolName = 'smart_device_execute';

  if (btnId.includes('thermostat')) {
    toolName = 'adjust_smart_thermostat';
    toolResult = adjust_smart_thermostat(72);
  } else if (btnId.includes('text')) {
    toolName = 'twilio_send_casual_text';
    toolResult = {
      recipient: payload.user.caregiver_phone,
      message: "I am comfortable and resting right now. Love you.",
      status: "delivered_direct"
    };
  } else if (btnId.includes('bed')) {
    toolName = 'smart_bed_adjust_elevation';
    toolResult = {
      device: "Stryker Smart Care Bed",
      head_elevation: "+15 degrees",
      state: "repositioned_comfort"
    };
  } else {
    toolName = 'assistant_chime_announce';
    toolResult = {
      device: "Living Room Chime Speaker",
      audio: "Gentle chime sounded: 'Assistance requested for drink/suction'",
      state: "played"
    };
  }

  return {
    action_id: `act_${Math.random().toString(36).substring(2, 10)}`,
    tier: 'Tier 1',
    risk_level: 'LOW',
    category: 'ENVIRONMENTAL_SOCIAL',
    requires_caregiver_approval: false,
    bypass_delays: false,
    status: 'executed',
    agent_tool: toolName,
    tool_result: toolResult,
    reasoning: "Low-risk environmental or communication intent. Executing immediately without caregiver interruption.",
    processed_at_ms: nowMs,
    dropped_by_spasm_filter: false,
    delta_ms: deltaMs
  };
}

// Web Speech Vocalizer
export function vocalizePhrase(text: string) {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);
  }
}
