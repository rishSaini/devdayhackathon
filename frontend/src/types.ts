export type Tier = 'Tier 1' | 'Tier 2' | 'Tier 3';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type ActionCategory = 'ENVIRONMENTAL_SOCIAL' | 'HEALTH_FINANCIAL' | 'EMERGENCY' | 'SPASM_FILTER_DROPPED';
export type ExecutionStatus = 'executed' | 'pending_approval' | 'emergency_dispatched' | 'debounced_dropped';

export type ThemeId = 'sage' | 'earth' | 'sage-night' | 'earth-night';

export interface ThemeColors {
  id: ThemeId;
  name: string;
  subtitle: string;
  bgBase: string;
  cardBase: string;
  cardBorder: string;
  cardShadow: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  accentLight: string;
  emergency: string;
  emergencyLight: string;
  tier2: string;
  tier2Light: string;
  navBg: string;
  subtleBg: string;
  inputBg: string;
  codeBg: string;
  isDark: boolean;
}

export interface UserContext {
  user_id: string;
  name: string;
  caregiver_name: string;
  caregiver_phone: string;
  location: string;
  vital_status: string;
}

export interface AACButtonConfig {
  id: string;
  label: string;
  category: 'emergency' | 'health' | 'finance' | 'environment' | 'social';
  tierExpected: Tier;
  iconName: string;
  speechPhrase: string;
  description: string;
  customParams?: Record<string, any>;
}

export interface AACButtonPayload {
  button_id: string;
  label: string;
  client_timestamp_ms: number;
  user: {
    user_id: string;
    caregiver_phone: string;
    location: string;
    vital_status: string;
  };
  custom_params?: Record<string, any>;
}

export interface TriageResult {
  action_id: string;
  tier: Tier;
  risk_level: RiskLevel;
  category: ActionCategory;
  requires_caregiver_approval: boolean;
  bypass_delays: boolean;
  status: ExecutionStatus;
  agent_tool: string;
  tool_result?: Record<string, any> | null;
  reasoning: string;
  processed_at_ms: number;
  dropped_by_spasm_filter: boolean;
  delta_ms?: number;
}

export interface PendingApproval {
  action_id: string;
  payload: AACButtonPayload;
  classification: {
    tier: Tier;
    risk_level: RiskLevel;
    category: string;
    reasoning: string;
    agent_tool: string;
    tool_parameters: Record<string, any>;
  };
  created_at: number;
  sms_dispatch: {
    service: string;
    message_sid: string;
    recipient: string;
    body: string;
  };
}

export interface AuditLogEntry {
  id: string;
  timestamp: number;
  action_id: string;
  button_label: string;
  tier: Tier;
  status: ExecutionStatus | 'caregiver_approved_and_executed' | 'caregiver_rejected';
  summary: string;
  details?: Record<string, any>;
}
