import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ArrowRight,
  Activity,
  Cpu,
  Terminal,
  Send,
  Waves
} from 'lucide-react';
import { TriageResult, AuditLogEntry } from '../types';

interface PipelineViewerProps {
  lastTriage: TriageResult | null;
  auditLog: AuditLogEntry[];
  onSelectPendingTab: () => void;
}

export const PipelineViewer: React.FC<PipelineViewerProps> = ({
  lastTriage,
  auditLog,
  onSelectPendingTab
}) => {
  return (
    <div className="space-y-8">
      {/* Hero Header Card */}
      <div className="frosted-glass-card p-7 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="signature-kicker">
              Stream Telemetry · Real-time Routing
            </span>
            <h2 className="font-heading text-2xl font-bold text-[#141414] tracking-[-0.025em] mt-1 flex items-center gap-2.5">
              <span>Ripple Execution Stream</span>
              <Waves className="w-5 h-5 text-[#5B8DB8]" />
            </h2>
            <p className="text-sm font-body text-[#6B6B6B] mt-1 max-w-xl leading-relaxed">
              Step-by-step trace showing Spasm Filter debounce evaluation, Decisions API tier triage, and Agents API tool execution.
            </p>
          </div>
          {lastTriage && (
            <div className="text-xs font-mono px-3.5 py-1.5 rounded-full bg-white/80 border border-[#EFE9DE] text-[#6B6B6B] shadow-sm shrink-0">
              Action ID: <span className="font-bold text-[#1A3226]">{lastTriage.action_id}</span>
            </div>
          )}
        </div>
      </div>

      {/* Real-time Trace Pipeline (Hero Card 24px) */}
      {lastTriage ? (
        <div className="frosted-glass-card p-7 sm:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-[#EFE9DE] gap-3">
            <div>
              <span className="signature-kicker text-[#6B6B6B]">
                Triggered at {new Date(lastTriage.processed_at_ms).toLocaleTimeString()}
              </span>
              <h3 className="font-heading text-lg font-bold text-[#141414] mt-0.5">
                Stream Result: {lastTriage.category}
              </h3>
            </div>

            <div>
              {lastTriage.dropped_by_spasm_filter ? (
                <span className="bg-[#FEF9C3] text-[#B8860B] border border-[#FDE047]/60 rounded-full px-3.5 py-1 text-xs font-bold font-mono inline-flex items-center gap-2">
                  <Waves className="w-4 h-4 text-[#B8860B] animate-pulse" />
                  <span>TREMOR ABSORBED ({lastTriage.delta_ms}ms)</span>
                </span>
              ) : (
                <span
                  className={`rounded-full px-3.5 py-1 text-xs font-bold font-mono inline-flex items-center gap-2 ${
                    lastTriage.tier === 'Tier 3'
                      ? 'bg-[#FDECEA] text-[#C62828] border border-[#FFCDD2]'
                      : lastTriage.tier === 'Tier 2'
                      ? 'bg-[#FEF9C3] text-[#B8860B] border border-[#FDE047]'
                      : 'bg-[#EDF7ED] text-[#2E7D32] border border-[#C8E6C9]'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{lastTriage.tier} · {lastTriage.status.toUpperCase()}</span>
                </span>
              )}
            </div>
          </div>

          {/* 3 Step Visual Stream Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Stage 1: Spasm Filter */}
            <div
              className={`p-5 rounded-[20px] border transition-all ${
                lastTriage.dropped_by_spasm_filter
                  ? 'bg-[#FEF9C3]/70 border-[#FDE047] shadow-sm'
                  : 'bg-white/60 border-white/80 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-3 text-[11px] font-mono">
                <span className="text-[#A0A0A0]">STAGE 01</span>
                {lastTriage.dropped_by_spasm_filter ? (
                  <span className="font-bold text-[#B8860B]">ABSORBED &amp; DROPPED</span>
                ) : (
                  <span className="font-bold text-[#2E7D32]">CLEAN TAP PASSED</span>
                )}
              </div>
              <h4 className="font-heading text-base font-bold text-[#141414] flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#1A3226]" />
                Spasm Filter Barrier
              </h4>
              <p className="text-xs font-body text-[#6B6B6B] mt-2 leading-relaxed">
                {lastTriage.dropped_by_spasm_filter
                  ? `Motor jitter arrived in ${lastTriage.delta_ms}ms (< 400ms threshold). Request absorbed peacefully without triggering physical actuation.`
                  : lastTriage.delta_ms && lastTriage.delta_ms > 0
                  ? `Tap delta was ${lastTriage.delta_ms}ms (>= 400ms). Verified intentional adult touch.`
                  : 'Initial session touch verified.'}
              </p>
              <div className="mt-4 pt-3 border-t border-[#EFE9DE] text-[11px] font-mono text-[#A0A0A0] flex justify-between">
                <span>Threshold: 400ms</span>
                <span>User: Robert M.</span>
              </div>
            </div>

            {/* Stage 2: Decisions API Triage */}
            <div
              className={`p-5 rounded-[20px] border transition-all ${
                lastTriage.dropped_by_spasm_filter
                  ? 'opacity-40 bg-white/30 border-[#EFE9DE]'
                  : 'bg-white/60 border-white/80 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-3 text-[11px] font-mono">
                <span className="text-[#A0A0A0]">STAGE 02</span>
                <span
                  className={`font-bold ${
                    lastTriage.tier === 'Tier 3'
                      ? 'text-[#C62828]'
                      : lastTriage.tier === 'Tier 2'
                      ? 'text-[#B8860B]'
                      : 'text-[#2E7D32]'
                  }`}
                >
                  {lastTriage.tier}
                </span>
              </div>
              <h4 className="font-heading text-base font-bold text-[#141414] flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[#D4A373]" />
                Decisions API Triage
              </h4>
              <p className="text-xs font-body text-[#6B6B6B] mt-2 leading-relaxed">
                {lastTriage.reasoning}
              </p>
              <div className="mt-4 pt-3 border-t border-[#EFE9DE] text-[11px] font-mono text-[#A0A0A0] flex justify-between">
                <span>Risk: {lastTriage.risk_level}</span>
                <span>Approval: {lastTriage.requires_caregiver_approval ? 'Required' : 'Bypassed'}</span>
              </div>
            </div>

            {/* Stage 3: Agents API Tool */}
            <div
              className={`p-5 rounded-[20px] border transition-all ${
                lastTriage.dropped_by_spasm_filter
                  ? 'opacity-40 bg-white/30 border-[#EFE9DE]'
                  : 'bg-white/60 border-white/80 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-3 text-[11px] font-mono">
                <span className="text-[#A0A0A0]">STAGE 03</span>
                <span className="font-bold text-[#1A3226]">{lastTriage.agent_tool}</span>
              </div>
              <h4 className="font-heading text-base font-bold text-[#141414] flex items-center gap-2">
                <Send className="w-4 h-4 text-[#34D399]" />
                Agents API Tool
              </h4>
              <p className="text-xs font-body text-[#6B6B6B] mt-2 leading-relaxed">
                {lastTriage.status === 'pending_approval' ? (
                  <span>
                    Action suspended. Twilio SMS dispatched to Sarah's phone. Awaiting webhook authorization.
                  </span>
                ) : lastTriage.status === 'emergency_dispatched' ? (
                  <span className="font-medium text-[#C62828]">
                    Delays bypassed. Physical Schlage deadbolt disengaged immediately for EMT arrival.
                  </span>
                ) : (
                  <span>
                    Direct hardware execution completed. Environmental target state confirmed.
                  </span>
                )}
              </p>
              {lastTriage.status === 'pending_approval' && (
                <div className="mt-4 pt-3 border-t border-[#EFE9DE]">
                  <button
                    onClick={onSelectPendingTab}
                    className="text-xs font-bold text-[#B8860B] hover:text-[#996515] flex items-center gap-1.5 transition-colors"
                  >
                    <span>Authorize on Caregiver Companion</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Raw JSON Stream Output */}
          <div className="p-5 rounded-[20px] bg-[#1A3226] text-white border border-[#14261d]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-[#D4A373] flex items-center gap-2 font-semibold">
                <Terminal className="w-4 h-4 text-[#34D399]" />
                Engine Output Payload (TriageResult)
              </span>
              <span className="text-[11px] font-mono text-[#A0A0A0]">
                processed_at_ms: {lastTriage.processed_at_ms}
              </span>
            </div>
            <pre className="text-xs font-mono text-[#34D399] bg-[#14261d] p-4 rounded-[14px] overflow-x-auto max-h-52 border border-white/5 leading-relaxed">
              {JSON.stringify(lastTriage, null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <div className="frosted-glass-card p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-[#1A3226]/10 border border-[#1A3226]/20 flex items-center justify-center mx-auto text-[#1A3226]">
            <Waves className="w-6 h-6 animate-pulse" />
          </div>
          <h3 className="font-heading text-lg font-bold text-[#141414]">Waters are Still</h3>
          <p className="text-xs font-body text-[#6B6B6B] max-w-md mx-auto leading-relaxed">
            Tap any pebble on the AAC surface to cast an action into the stream and observe the Spasm Filter and Decisions API triage live.
          </p>
        </div>
      )}

      {/* Execution Audit Log Table */}
      <div className="frosted-glass-card p-7 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="signature-kicker">Permanent Ledger</span>
            <h3 className="font-heading text-base font-bold text-[#141414]">Execution Stream Ledger</h3>
            <p className="text-xs font-body text-[#6B6B6B]">Immutable audit record of physical dispatches, approvals, and spasm dampeners</p>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-white/80 border border-[#EFE9DE] text-[#6B6B6B] shadow-sm">
            {auditLog.length} events logged
          </span>
        </div>

        {auditLog.length === 0 ? (
          <div className="text-center py-10 text-xs text-[#A0A0A0]">
            Ledger is empty. Action events will appear here in real-time.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#EFE9DE] text-[#A0A0A0] font-mono">
                  <th className="pb-3 font-medium">TIMESTAMP</th>
                  <th className="pb-3 font-medium">INTENT / BUTTON</th>
                  <th className="pb-3 font-medium">TIER</th>
                  <th className="pb-3 font-medium">STATUS</th>
                  <th className="pb-3 font-medium">SUMMARY</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFE9DE]">
                {auditLog.map((entry) => (
                  <tr key={entry.id} className="hover:bg-white/40 transition-colors">
                    <td className="py-3 font-mono text-[#6B6B6B] tabular-nums">
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 font-semibold text-[#141414]">
                      {entry.button_label}
                    </td>
                    <td className="py-3 font-mono font-bold">
                      <span
                        className={
                          entry.tier === 'Tier 3'
                            ? 'text-[#C62828]'
                            : entry.tier === 'Tier 2'
                            ? 'text-[#B8860B]'
                            : 'text-[#2E7D32]'
                        }
                      >
                        {entry.tier}
                      </span>
                    </td>
                    <td className="py-3 font-mono">
                      <span
                        className={
                          entry.status === 'debounced_dropped'
                            ? 'text-[#B8860B]'
                            : entry.status === 'emergency_dispatched'
                            ? 'text-[#C62828]'
                            : entry.status === 'pending_approval'
                            ? 'text-[#B8860B]'
                            : 'text-[#2E7D32]'
                        }
                      >
                        {entry.status}
                      </span>
                    </td>
                    <td className="py-3 text-[#6B6B6B] max-w-sm truncate">
                      {entry.summary}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
