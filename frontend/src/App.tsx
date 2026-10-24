/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { TopNav } from './components/TopNav';
import { AACGrid } from './components/AACGrid';
import { PipelineViewer } from './components/PipelineViewer';
import { CaregiverCompanion } from './components/CaregiverCompanion';
import { CodeInspector } from './components/CodeInspector';
import {
  DEFAULT_USER,
  processAACTapLocally,
  clientSpasmFilter,
  vocalizePhrase,
  DEBOUNCE_THRESHOLD_MS
} from './services/rippleEngine';
import {
  playPebbleDropletSound,
  playSpasmAbsorbedSound,
  playEmergencyPulseSound
} from './services/audioHaptics';
import { colors } from './theme/colors';
import {
  AACButtonConfig,
  AACButtonPayload,
  TriageResult,
  PendingApproval,
  AuditLogEntry
} from './types';
import { Waves } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'grid' | 'pipeline' | 'caregiver' | 'inspector'>('grid');
  const [user, setUser] = useState(DEFAULT_USER);
  const [simulateSpasm, setSimulateSpasm] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  // Core Pipeline State
  const [lastTriage, setLastTriage] = useState<TriageResult | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [lastFilterNotice, setLastFilterNotice] = useState<string | null>(null);

  // Physical Autonomy Hardware State
  const [lockState, setLockState] = useState<{
    unlocked: boolean;
    durationRemaining: number;
    lastUnlockedTime: string | null;
  }>({
    unlocked: false,
    durationRemaining: 0,
    lastUnlockedTime: null
  });

  const [currentTemp, setCurrentTemp] = useState<number>(72);
  const [ehrLogs, setEhrLogs] = useState<Array<{ id: string; time: string; event: string; severity: number }>>([
    {
      id: 'EHR-819201',
      time: '07:30 AM',
      event: 'Baseline Neurological Check (Morning)',
      severity: 2
    }
  ]);

  // Lock auto-relock countdown timer
  useEffect(() => {
    let timer: any;
    if (lockState.unlocked && lockState.durationRemaining > 0) {
      timer = setInterval(() => {
        setLockState((prev) => {
          if (prev.durationRemaining <= 1) {
            return { ...prev, unlocked: false, durationRemaining: 0 };
          }
          return { ...prev, durationRemaining: prev.durationRemaining - 1 };
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [lockState.unlocked, lockState.durationRemaining]);

  // Handle AAC Grid Tap with Spasm Filter & Decisions Engine
  const executeTapPayload = (payload: AACButtonPayload, isSpasmClone: boolean = false) => {
    const result = processAACTapLocally(payload);

    if (result.dropped_by_spasm_filter) {
      if (soundEnabled) {
        playSpasmAbsorbedSound();
      }

      setLastFilterNotice(
        `Spasm Filter absorbed involuntary tremor on '${payload.label}' (+${result.delta_ms}ms). Neutralized.`
      );
      setTimeout(() => setLastFilterNotice(null), 5000);

      const dropEntry: AuditLogEntry = {
        id: `audit_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        timestamp: result.processed_at_ms,
        action_id: result.action_id,
        button_label: payload.label,
        tier: 'Tier 1',
        status: 'debounced_dropped',
        summary: `Spasm debounce absorbed tap in ${result.delta_ms}ms (< 400ms threshold). Accidental duplicate neutralized.`
      };
      setAuditLog((prev) => [dropEntry, ...prev]);
      setLastTriage(result);
      return;
    }

    // Play tactile sound on valid tap
    if (soundEnabled) {
      if (result.tier === 'Tier 3') {
        playEmergencyPulseSound();
      } else {
        playPebbleDropletSound(result.tier === 'Tier 2' ? 440 : 560);
      }
    }

    setLastTriage(result);

    // Physical autonomy side effects based on Tier & Agent Tool
    if (result.tier === 'Tier 3') {
      if (result.agent_tool === 'smart_lock_grant_access') {
        setLockState({
          unlocked: true,
          durationRemaining: 300,
          lastUnlockedTime: new Date().toLocaleTimeString()
        });
      }
    } else if (result.tier === 'Tier 2') {
      const newPending: PendingApproval = {
        action_id: result.action_id,
        payload: payload,
        classification: {
          tier: result.tier,
          risk_level: result.risk_level,
          category: result.category,
          reasoning: result.reasoning,
          agent_tool: result.agent_tool,
          tool_parameters: result.tool_result || {}
        },
        created_at: result.processed_at_ms,
        sms_dispatch: {
          service: 'Twilio Programmable Messaging',
          message_sid: result.tool_result?.message_sid || `SM_${Date.now()}`,
          recipient: user.caregiver_phone,
          body: `Ripple AAC Alert: Robert requested '${payload.label}'. Reply YES to approve or review in Caregiver Portal.`
        }
      };
      setPendingApprovals((prev) => [newPending, ...prev]);
    } else {
      if (payload.button_id === 'adjust_thermostat') {
        setCurrentTemp(72);
      }
    }

    const auditEntry: AuditLogEntry = {
      id: `audit_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      timestamp: result.processed_at_ms,
      action_id: result.action_id,
      button_label: payload.label,
      tier: result.tier,
      status: result.status,
      summary: result.reasoning
    };
    setAuditLog((prev) => [auditEntry, ...prev]);
  };

  const handleButtonTap = (btn: AACButtonConfig, isSpasmSimulation: boolean) => {
    setIsProcessing(true);

    if (voiceEnabled) {
      vocalizePhrase(btn.speechPhrase);
    }

    const now = Date.now();
    const primaryPayload: AACButtonPayload = {
      button_id: btn.id,
      label: btn.label,
      client_timestamp_ms: now,
      user: {
        user_id: user.user_id,
        caregiver_phone: user.caregiver_phone,
        location: user.location,
        vital_status: user.vital_status
      },
      custom_params: btn.customParams
    };

    // 1. Primary Tap
    executeTapPayload(primaryPayload, false);

    // 2. If Spasm Simulation is enabled, trigger a tremor double-tap at t = +118ms
    if (isSpasmSimulation) {
      setTimeout(() => {
        const spasmClonePayload: AACButtonPayload = {
          ...primaryPayload,
          client_timestamp_ms: now + 118
        };
        executeTapPayload(spasmClonePayload, true);
        setIsProcessing(false);
      }, 118);
    } else {
      setTimeout(() => setIsProcessing(false), 150);
    }
  };

  // Caregiver Webhook Approval Callbacks
  const handleApproveAction = (actionId: string, notes: string) => {
    const item = pendingApprovals.find((p) => p.action_id === actionId);
    if (!item) return;

    if (soundEnabled) {
      playPebbleDropletSound(620);
    }

    if (item.classification.agent_tool === 'log_medical_event') {
      const severity = item.payload.custom_params?.severity || 8;
      const newEhr = {
        id: `EHR-${Math.floor(100000 + Math.random() * 900000)}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        event: `Acute Pain Rating (Level ${severity}/10) - Caregiver Verified`,
        severity: severity
      };
      setEhrLogs((prev) => [newEhr, ...prev]);
    }

    setPendingApprovals((prev) => prev.filter((p) => p.action_id !== actionId));

    const auditEntry: AuditLogEntry = {
      id: `audit_${Date.now()}_appr`,
      timestamp: Date.now(),
      action_id: actionId,
      button_label: item.payload.label,
      tier: 'Tier 2',
      status: 'caregiver_approved_and_executed',
      summary: `Approved by Sarah via Twilio Webhook callback. Agent tool '${item.classification.agent_tool}' resumed. Notes: ${notes}`
    };
    setAuditLog((prev) => [auditEntry, ...prev]);
  };

  const handleRejectAction = (actionId: string, notes: string) => {
    const item = pendingApprovals.find((p) => p.action_id === actionId);
    if (!item) return;

    if (soundEnabled) {
      playSpasmAbsorbedSound();
    }

    setPendingApprovals((prev) => prev.filter((p) => p.action_id !== actionId));

    const auditEntry: AuditLogEntry = {
      id: `audit_${Date.now()}_rej`,
      timestamp: Date.now(),
      action_id: actionId,
      button_label: item.payload.label,
      tier: 'Tier 2',
      status: 'caregiver_rejected',
      summary: `Declined by Sarah via Webhook. Execution halted safely. Notes: ${notes}`
    };
    setAuditLog((prev) => [auditEntry, ...prev]);
  };

  const handleResetDemo = () => {
    clientSpasmFilter.clear();
    setLastTriage(null);
    setPendingApprovals([]);
    if (soundEnabled) playPebbleDropletSound(480);
    setLastFilterNotice('Debounce stream cleared. Ready for fresh test run.');
    setTimeout(() => setLastFilterNotice(null), 3500);
  };

  return (
    <div className="min-h-screen bg-cream-canvas text-[#141414] font-body pb-16 selection:bg-[#D4A373] selection:text-white">
      {/* Top Bar with Three-Color Logo in Playfair Display Bold */}
      <TopNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingCount={pendingApprovals.length}
        onResetDemo={handleResetDemo}
      />

      {/* Main Viewport */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {activeTab === 'grid' && (
          <AACGrid
            user={user}
            onButtonTap={handleButtonTap}
            simulateSpasm={simulateSpasm}
            setSimulateSpasm={setSimulateSpasm}
            voiceEnabled={voiceEnabled}
            setVoiceEnabled={setVoiceEnabled}
            soundEnabled={soundEnabled}
            setSoundEnabled={setSoundEnabled}
            isProcessing={isProcessing}
            lastFilterNotice={lastFilterNotice}
          />
        )}

        {activeTab === 'pipeline' && (
          <PipelineViewer
            lastTriage={lastTriage}
            auditLog={auditLog}
            onSelectPendingTab={() => setActiveTab('caregiver')}
          />
        )}

        {activeTab === 'caregiver' && (
          <CaregiverCompanion
            user={user}
            pendingApprovals={pendingApprovals}
            onApproveAction={handleApproveAction}
            onRejectAction={handleRejectAction}
            lockState={lockState}
            currentTemp={currentTemp}
            ehrLogs={ehrLogs}
          />
        )}

        {activeTab === 'inspector' && (
          <CodeInspector
            user={user}
            onRunTestPayload={(payload) => {
              executeTapPayload(payload, false);
            }}
            testResult={lastTriage}
          />
        )}
      </main>

      {/* Footer in Warm Cream / Deep Forest */}
      <footer className="border-t border-[#EFE9DE] mt-20 py-8 px-6 text-center text-xs text-[#6B6B6B]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="font-logo font-bold text-[#1A3226]">
              Ripple &amp; Pebble
            </span>
            <span className="text-[#A0A0A0]">·</span>
            <span>Adult Physical AAC Autonomy</span>
            <span className="text-[#A0A0A0]">·</span>
            <span className="font-semibold text-[#1A3226]">
              Deep Forest &amp; Warm Sand
            </span>
          </div>
          <div className="font-mono text-[11px] text-[#A0A0A0] flex items-center gap-2">
            <span>FastAPI</span>
            <span>/</span>
            <span>Decisions API</span>
            <span>/</span>
            <span>Agents API</span>
            <span>/</span>
            <span>Twilio Webhook</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
