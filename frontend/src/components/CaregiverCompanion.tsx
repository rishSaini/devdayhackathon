import React, { useState } from 'react';
import {
  Smartphone,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  MessageSquare,
  Lock,
  Unlock,
  Thermometer,
  FileText,
  Send,
  Waves,
  Heart,
  Quote
} from 'lucide-react';
import { PendingApproval, UserContext } from '../types';
import { colors } from '../theme/colors';
import sarahPortraitImg from '../assets/images/caregiver_sarah_portrait_1792820502388.jpg';

interface CaregiverCompanionProps {
  user: UserContext;
  pendingApprovals: PendingApproval[];
  onApproveAction: (actionId: string, notes: string) => void;
  onRejectAction: (actionId: string, notes: string) => void;
  lockState: { unlocked: boolean; durationRemaining: number; lastUnlockedTime: string | null };
  currentTemp: number;
  ehrLogs: Array<{ id: string; time: string; event: string; severity: number }>;
}

export const CaregiverCompanion: React.FC<CaregiverCompanionProps> = ({
  user,
  pendingApprovals,
  onApproveAction,
  onRejectAction,
  lockState,
  currentTemp,
  ehrLogs
}) => {
  const [caregiverNote, setCaregiverNote] = useState('');

  return (
    <div className="space-y-8">
      {/* Top Banner Hero Card: Personal Caregiver Profile */}
      <div className="bg-white rounded-[24px] border border-[#E6DFD2] p-6 sm:p-8 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.08)]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-5">
            {/* Sarah's Portrait */}
            <div className="relative shrink-0">
              <img
                src={sarahPortraitImg}
                alt="Sarah Sterling, Caregiver & Registered Nurse"
                className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border-2 border-[#1A3226]/20 shadow-md"
                loading="lazy"
                referrerPolicy="no-referrer"
              />
              <span className="absolute bottom-0 right-0 w-4 h-4 bg-[#2E7D32] border-2 border-white rounded-full shadow-xs" title="Online & Connected" />
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="signature-kicker text-[#1A3226]">
                  Verified Caregiver Relay
                </span>
                <span className="bg-[#EDF7ED] text-[#2E7D32] border border-[#C8E6C9] rounded-full px-2.5 py-0.5 text-[11px] font-semibold font-body">
                  Active On Duty
                </span>
              </div>
              <h2 className="font-heading text-2xl font-bold text-[#141414] tracking-[-0.025em]">
                Sarah Sterling · Care Partner
              </h2>
              <p className="text-xs sm:text-sm font-body text-[#6B6B6B]">
                Registered Nurse · Primary Family Caregiver for {user.name} · Phone: <span className="font-mono font-bold text-[#1A3226]">{user.caregiver_phone}</span>
              </p>
            </div>
          </div>

          {/* Garamond Personal Message from Sarah */}
          <div className="lg:max-w-md bg-[#FAF9F6] border border-[#E6DFD2] rounded-[18px] p-4 shadow-2xs">
            <div className="flex items-start gap-2">
              <Quote className="w-4 h-4 text-[#D4A373] shrink-0 mt-0.5 opacity-80" />
              <p className="font-editorial-quote text-[14px] text-[#141414] leading-relaxed">
                "I'm always within a few minutes. Dad, you have total freedom over your room—when you tap an order or medical note, I verify it here instantly."
              </p>
            </div>
            <div className="text-[11px] font-body text-[#A0A0A0] text-right mt-1">
              Sarah · 4 min away
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Simulated Caregiver Smartphone in Clean Ceramic White */}
        <div className="lg:col-span-6 space-y-4">
          <div className="bg-white border border-[#E6DFD2] rounded-[28px] p-6 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.10)] relative overflow-hidden">
            {/* Top Phone Speaker & Header */}
            <div className="flex items-center justify-between pb-4 border-b border-[#EFE9DE] mb-4">
              <div className="flex items-center gap-3">
                <img
                  src={sarahPortraitImg}
                  alt="Sarah"
                  className="w-8 h-8 rounded-full object-cover border border-[#E6DFD2]"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                />
                <div>
                  <span className="font-body text-xs font-bold text-[#141414] block">
                    Sarah's Phone · Twilio SMS Relay
                  </span>
                  <span className="text-[10px] text-[#2E7D32] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2E7D32]" />
                    Online · Automated Webhook Active
                  </span>
                </div>
              </div>
              <div className="text-[11px] font-mono text-[#A0A0A0]">
                5G · 100%
              </div>
            </div>

            {/* Simulated SMS Thread */}
            <div className="space-y-4 min-h-[380px] flex flex-col justify-end">
              {/* Prior mock reassuring text */}
              <div className="p-4 rounded-[18px] rounded-tl-none max-w-[85%] text-xs border border-[#EFE9DE] bg-[#F7F2EA] space-y-1 shadow-sm">
                <span className="signature-kicker text-[#1A3226] block">
                  PEBBLE SYSTEM NOTIFICATION
                </span>
                <p className="text-[#141414] font-medium leading-relaxed">
                  Robert is comfortably seated in living room recliner. Vital sensors nominal (SpO2 97%).
                </p>
                <div className="text-[10px] text-[#A0A0A0] text-right font-mono">08:00 AM</div>
              </div>

              {pendingApprovals.length === 0 ? (
                <div className="border border-dashed border-[#EFE9DE] bg-[#F7F2EA]/40 rounded-[20px] p-8 text-center text-xs text-[#6B6B6B] my-auto space-y-2">
                  <div className="w-10 h-10 rounded-full bg-[#EDF7ED] border border-[#C8E6C9] flex items-center justify-center mx-auto text-[#2E7D32]">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <p className="font-heading text-sm font-bold text-[#141414]">Waters are Quiet</p>
                  <p className="max-w-xs mx-auto text-[#6B6B6B] leading-relaxed">
                    No pending authorizations. When Robert taps a Tier 2 button on the AAC grid, an SMS approval card will ripple here immediately.
                  </p>
                </div>
              ) : (
                pendingApprovals.map((pending) => (
                  <div
                    key={pending.action_id}
                    className="border border-[#FDE047] bg-[#FEF9C3]/80 p-5 rounded-[20px] rounded-tl-none text-xs space-y-3 shadow-md transition-all"
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono">
                      <span className="font-bold text-[#B8860B] flex items-center gap-1.5">
                        <Waves className="w-3.5 h-3.5 animate-pulse" />
                        RIPPLE VERIFICATION REQUIRED
                      </span>
                      <span className="text-[#6B6B6B]">
                        {new Date(pending.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <p className="font-semibold text-sm text-[#141414] leading-relaxed">
                      {pending.sms_dispatch.body}
                    </p>

                    <div className="p-3 rounded-[14px] bg-white/80 border border-[#EFE9DE] text-[11px] font-mono text-[#6B6B6B] space-y-1">
                      <div>Action ID: <span className="font-bold text-[#1A3226]">{pending.action_id}</span></div>
                      <div>Requested Action: <span className="font-semibold text-[#141414]">{pending.payload.label}</span></div>
                      <div>Triage Safety Tier: <span className="font-bold text-[#B8860B]">Tier 2 (Caregiver Loop)</span></div>
                    </div>

                    {/* Primary Button Recipe (Deep Forest, 16px radius) & Secondary (Warm Cream, 12px radius) */}
                    <div className="pt-2 flex items-center gap-3">
                      <button
                        onClick={() => onApproveAction(pending.action_id, caregiverNote || 'Authorized by Sarah via Pebble Link Webhook')}
                        className="flex-1 py-3 px-4 rounded-[16px] bg-[#1A3226] hover:bg-[#14261d] text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-[0_4px_14px_-2px_rgba(26,50,38,0.18)] active:scale-95 cursor-pointer"
                      >
                        <CheckCircle2 className="w-4 h-4 text-[#34D399]" />
                        <span>Authorize Execution</span>
                      </button>
                      <button
                        onClick={() => onRejectAction(pending.action_id, caregiverNote || 'Declined by caregiver')}
                        className="py-3 px-4 rounded-[12px] bg-[#F7F2EA] hover:bg-[#FDECEA] hover:text-[#C62828] text-[#141414] border border-[#E6DFD2] text-xs font-semibold transition-colors cursor-pointer"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Decline</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input note box for caregiver webhook */}
            <div className="mt-5 pt-4 border-t border-[#EFE9DE] flex items-center gap-2">
              <input
                type="text"
                placeholder="Caregiver notes for permanent ledger (e.g., 'Checked vitals, approving lunch')..."
                value={caregiverNote}
                onChange={(e) => setCaregiverNote(e.target.value)}
                className="flex-1 bg-white border border-[#EFE9DE] rounded-[14px] px-4 py-2.5 text-xs text-[#141414] placeholder-[#A0A0A0] focus:outline-none focus:border-[#1A3226] transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Right Column: Physical Autonomy Telemetry */}
        <div className="lg:col-span-6 space-y-5">
          <div className="frosted-glass-card p-7 space-y-5">
            <div>
              <span className="signature-kicker">Actuator Telemetry</span>
              <h3 className="font-heading text-base font-bold text-[#141414]">
                Physical Autonomy Ecosystem
              </h3>
              <p className="text-xs font-body text-[#6B6B6B]">
                Live operational status of connected physical hardware and patient clinical charts.
              </p>
            </div>

            {/* Smart Deadbolt Card */}
            <div className="p-5 rounded-[20px] bg-white/70 border border-white/80 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <div
                  className={`w-11 h-11 rounded-[16px] border flex items-center justify-center transition-all ${
                    lockState.unlocked
                      ? 'bg-[#FDECEA] border-[#FFCDD2] text-[#C62828]'
                      : 'bg-[#EDF7ED] border-[#C8E6C9] text-[#2E7D32]'
                  }`}
                >
                  {lockState.unlocked ? <Unlock className="w-5 h-5" /> : <Lock className="w-5 h-5" />}
                </div>
                <div>
                  <div className="font-heading text-sm font-bold text-[#141414]">
                    Schlage Encode Smart Deadbolt
                  </div>
                  <div className="text-[11px] font-body text-[#6B6B6B]">
                    Front Entrance · Matter Over Thread
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div
                  className={`text-xs font-mono font-bold ${
                    lockState.unlocked ? 'text-[#C62828]' : 'text-[#2E7D32]'
                  }`}
                >
                  {lockState.unlocked ? 'UNLOCKED (EMT PASS)' : 'LOCKED & SECURED'}
                </div>
                {lockState.unlocked && (
                  <div className="text-[10px] font-mono text-[#A0A0A0] mt-0.5">
                    Relocking in {lockState.durationRemaining}s
                  </div>
                )}
              </div>
            </div>

            {/* Smart Thermostat Card */}
            <div className="p-5 rounded-[20px] bg-white/70 border border-white/80 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-[16px] bg-[#EFF6FF] border border-[#BFDBFE] text-[#5B8DB8] flex items-center justify-center">
                  <Thermometer className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-heading text-sm font-bold text-[#141414]">
                    Google Nest Learning Thermostat
                  </div>
                  <div className="text-[11px] font-body text-[#6B6B6B]">
                    Living Room Zone · Eco Mode
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="font-mono text-base font-bold text-[#1A3226]">
                  {currentTemp}°F
                </div>
                <div className="text-[10px] font-semibold text-[#2E7D32]">
                  Optimal temperature
                </div>
              </div>
            </div>

            {/* EHR Medical Event Feed */}
            <div className="p-5 rounded-[20px] bg-white/70 border border-white/80 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-[#141414]">
                  <FileText className="w-4 h-4 text-[#D4A373]" />
                  <span className="font-heading text-sm">FHIR EHR Medical Timeline</span>
                </div>
                <span className="text-[10px] font-mono text-[#A0A0A0]">Live Clinical Feed</span>
              </div>

              {ehrLogs.length === 0 ? (
                <div className="text-xs text-[#A0A0A0] py-4 text-center">
                  No medical episodes recorded today.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-48 overflow-y-auto">
                  {ehrLogs.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-[14px] bg-[#F7F2EA] border border-[#EFE9DE] text-xs flex items-center justify-between"
                    >
                      <div>
                        <div className="font-bold text-[#141414]">{item.event}</div>
                        <div className="text-[10px] text-[#6B6B6B] font-mono mt-0.5">
                          Observation ID: {item.id} · Wong-Baker: {item.severity}/10
                        </div>
                      </div>
                      <span className="text-[11px] font-mono font-bold text-[#B8860B] tabular-nums">
                        {item.time}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
