import React, { useState } from 'react';
import {
  Unlock,
  ShieldAlert,
  HeartPulse,
  Utensils,
  Thermometer,
  Bed,
  MessageSquare,
  Waves,
  Zap,
  Volume2,
  VolumeX,
  Activity,
  Droplets,
  Heart,
  Quote
} from 'lucide-react';
import { AACButtonConfig, UserContext } from '../types';

// Editorial photography assets for physical AAC autonomy
import heroSanctuaryImg from '../assets/images/hero_patient_sanctuary_1792820501480.jpg';
import frontDoorImg from '../assets/images/sunlit_front_entrance_1792820503981.jpg';
import warmSoupImg from '../assets/images/warm_nourishing_soup_1792820502980.jpg';
import careBedImg from '../assets/images/cozy_reading_bedroom_1792820504596.jpg';

interface AACGridProps {
  user: UserContext;
  onButtonTap: (button: AACButtonConfig, isSpasmSimulation: boolean) => void;
  simulateSpasm: boolean;
  setSimulateSpasm: (val: boolean) => void;
  voiceEnabled: boolean;
  setVoiceEnabled: (val: boolean) => void;
  soundEnabled: boolean;
  setSoundEnabled: (val: boolean) => void;
  isProcessing: boolean;
  lastFilterNotice: string | null;
}

// Emergency Actions: Separated into their own dedicated top section with crisp visual cues
export const EMERGENCY_BUTTONS: (AACButtonConfig & { photoUrl?: string })[] = [
  {
    id: 'unlock_door',
    label: 'Unlock Front Door',
    category: 'emergency',
    tierExpected: 'Tier 3',
    iconName: 'Unlock',
    speechPhrase: 'Unlocking the front door for emergency assistance.',
    description: 'Unlocks the front entrance immediately so EMTs or family can enter without delay.',
    customParams: { door_id: 'front_entrance', duration: 300 },
    photoUrl: frontDoorImg
  },
  {
    id: 'emergency_sos',
    label: 'Emergency SOS',
    category: 'emergency',
    tierExpected: 'Tier 3',
    iconName: 'ShieldAlert',
    speechPhrase: 'Emergency alert activated. Calling emergency first responders.',
    description: 'Alerts 911 dispatch and your emergency contacts immediately with priority override.'
  }
];

// Daily Autonomy Actions: Crisp white cards, single-line titles, fixed height
export const DAILY_BUTTONS: (AACButtonConfig & { photoUrl?: string })[] = [
  {
    id: 'log_pain',
    label: 'Log Acute Pain',
    category: 'health',
    tierExpected: 'Tier 2',
    iconName: 'HeartPulse',
    speechPhrase: 'Logging severe pain level eight to medical chart.',
    description: 'Sends Sarah an alert to evaluate pain medication and notes it in your health record.',
    customParams: { severity: 8, pain_type: 'acute_neuralgic' }
  },
  {
    id: 'order_doordash',
    label: 'Order Lunch',
    category: 'finance',
    tierExpected: 'Tier 2',
    iconName: 'Utensils',
    speechPhrase: 'Requesting food order for warm bone broth and hydration.',
    description: 'Orders warm soup and hydration broth from DoorDash, subject to caregiver confirmation.',
    customParams: { amount: 24.50, items: ['Warm bone broth', 'Hydration electrolyte tea'] },
    photoUrl: warmSoupImg
  },
  {
    id: 'adjust_thermostat',
    label: 'Set Temperature',
    category: 'environment',
    tierExpected: 'Tier 1',
    iconName: 'Thermometer',
    speechPhrase: 'Setting room temperature to seventy-two degrees.',
    description: 'Adjusts the Google Nest thermostat to 72°F for immediate comfort.',
    customParams: { target_temp: 72 }
  },
  {
    id: 'reposition_bed',
    label: 'Adjust Bed Head',
    category: 'environment',
    tierExpected: 'Tier 1',
    iconName: 'Bed',
    speechPhrase: 'Adjusting motorized care bed head elevation by fifteen degrees.',
    description: 'Raises the motorized care bed fifteen degrees for easier pulmonary breathing.',
    customParams: { elevation: 15 },
    photoUrl: careBedImg
  },
  {
    id: 'text_caregiver',
    label: 'Text Sarah',
    category: 'social',
    tierExpected: 'Tier 1',
    iconName: 'MessageSquare',
    speechPhrase: 'Sending text to Sarah: I am resting comfortably and doing well.',
    description: 'Sends Sarah a quick message saying you are resting comfortably and doing well.'
  },
  {
    id: 'water_assistance',
    label: 'Request Drink',
    category: 'social',
    tierExpected: 'Tier 1',
    iconName: 'Waves',
    speechPhrase: 'Requesting oral suction or a cool drink of water.',
    description: 'Sounds a gentle bedside chime in the living room for a drink of water or suction.'
  }
];

export const AACGrid: React.FC<AACGridProps> = ({
  user,
  onButtonTap,
  simulateSpasm,
  setSimulateSpasm,
  voiceEnabled,
  setVoiceEnabled,
  soundEnabled,
  setSoundEnabled,
  isProcessing,
  lastFilterNotice
}) => {
  const [activeRippleId, setActiveRippleId] = useState<string | null>(null);

  const handleTap = (btn: AACButtonConfig) => {
    setActiveRippleId(btn.id);
    setTimeout(() => setActiveRippleId(null), 850);
    onButtonTap(btn, simulateSpasm);
  };

  const renderIcon = (name: string, isEmergency: boolean) => {
    const iconClass = "w-6 h-6 transition-transform duration-200 group-hover:scale-105";
    if (isEmergency) {
      return name === 'Unlock'
        ? <Unlock className={`${iconClass} text-[#C62828]`} />
        : <ShieldAlert className={`${iconClass} text-[#C62828]`} />;
    }

    // Anchor Color: Deep Forest (#1A3226) does the work for all daily actions
    switch (name) {
      case 'HeartPulse': return <HeartPulse className={`${iconClass} text-[#1A3226]`} />;
      case 'Utensils': return <Utensils className={`${iconClass} text-[#1A3226]`} />;
      case 'Thermometer': return <Thermometer className={`${iconClass} text-[#1A3226]`} />;
      case 'Bed': return <Bed className={`${iconClass} text-[#1A3226]`} />;
      case 'MessageSquare': return <MessageSquare className={`${iconClass} text-[#1A3226]`} />;
      case 'Waves': return <Waves className={`${iconClass} text-[#1A3226]`} />;
      default: return <Zap className={`${iconClass} text-[#1A3226]`} />;
    }
  };

  return (
    <div className="space-y-8">
      {/* 1. Header Hero Card: Personal sanctuary portrait with Garamond quote & controls */}
      <div className="bg-white rounded-[24px] border border-[#E6DFD2] overflow-hidden shadow-[0_10px_30px_-10px_rgba(26,50,38,0.08)]">
        {/* Sanctuary Visual Banner & Patient Status */}
        <div className="relative min-h-[160px] sm:min-h-[190px] overflow-hidden flex flex-col justify-between p-6 sm:p-8">
          {/* Background Sanctuary Photography with heavy warm cream gradient */}
          <img
            src={heroSanctuaryImg}
            alt="Robert's peaceful living room sanctuary with soft window light"
            className="absolute inset-0 w-full h-full object-cover object-center filter brightness-[0.92] contrast-[0.98]"
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={(e) => {
              (e.currentTarget as HTMLElement).style.display = 'none';
            }}
          />
          {/* Heavy cream/paper gradient over the photo as specified in the Pebble theme */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#FAF9F6] via-[#FAF9F6]/92 to-[#FAF9F6]/60 backdrop-blur-[1px]" />

          {/* Top Status Line: Manrope 600 with clean spacing */}
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span className="signature-kicker tracking-[0.15em] text-[#1A3226]">
              Assistive Autonomy Surface · Active Session
            </span>

            <div className="flex items-center gap-2 text-[13px] font-semibold text-[#141414] bg-white/80 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-[#E6DFD2] shadow-sm w-fit">
              <span className="font-bold text-[#1A3226]">{user.name}</span>
              <span aria-hidden="true" className="text-[#A0A0A0]">·</span>
              <span className="text-[#6B6B6B]">{user.location}</span>
              <span aria-hidden="true" className="text-[#A0A0A0]">·</span>
              <span className="font-bold text-[#2E7D32] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E7D32] animate-pulse" />
                {user.vital_status}
              </span>
            </div>
          </div>

          {/* Center Personal Autonomy Quote in Garamond */}
          <div className="relative z-10 my-3 max-w-2xl">
            <div className="flex items-start gap-2.5">
              <Quote className="w-5 h-5 text-[#D4A373] shrink-0 mt-1 opacity-70" />
              <p className="font-editorial-quote text-lg sm:text-xl text-[#141414] leading-snug">
                "Autonomy is having my door open for family, warm soup when I need strength, and peace in my own home."
              </p>
            </div>
            <p className="text-[12px] font-body text-[#6B6B6B] mt-1 pl-7 font-medium">
              Robert Sterling · Living with ALS · Voice &amp; Physical Command
            </p>
          </div>

          {/* Bottom Interactive Controls (White Pill Buttons with Green-tinted Hover) */}
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#E6DFD2]/70">
            <div className="space-y-0.5">
              <h1 className="font-heading text-xl sm:text-2xl font-bold text-[#141414] tracking-[-0.025em]">
                Autonomous Assistive Grid
              </h1>
              <p className="text-[13px] font-body text-[#6B6B6B]">
                Touch-first 24px targets with real-time 400ms tremor spasm filter.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <button
                onClick={() => setSimulateSpasm(!simulateSpasm)}
                className={`flex items-center gap-2.5 px-4 py-2 rounded-full text-[13px] font-semibold font-body transition-all duration-150 border shadow-sm ${
                  simulateSpasm
                    ? 'bg-[#FEF9C3] text-[#B8860B] border-[#FDE047]'
                    : 'bg-white hover:bg-[#F7F2EA] text-[#141414] border-[#E6DFD2]'
                }`}
                title="When enabled, every tap fires a second jitter strike within 118ms to test the 400ms Spasm Filter"
              >
                <Activity className="w-4 h-4 text-[#B8860B]" />
                <span>Simulate Spasm (120ms)</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-black/5 font-bold font-body">
                  {simulateSpasm ? 'ACTIVE' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`p-2.5 rounded-full border transition-all duration-150 shadow-sm ${
                  voiceEnabled
                    ? 'bg-[#EDF7ED] text-[#2E7D32] border-[#C8E6C9]'
                    : 'bg-white hover:bg-[#F7F2EA] text-[#6B6B6B] border-[#E6DFD2]'
                }`}
                title="Toggle speech synthesis vocalization"
              >
                {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              </button>

              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={`p-2.5 rounded-full border transition-all duration-150 shadow-sm ${
                  soundEnabled
                    ? 'bg-[#EFF6FF] text-[#5B8DB8] border-[#BFDBFE]'
                    : 'bg-white hover:bg-[#F7F2EA] text-[#6B6B6B] border-[#E6DFD2]'
                }`}
                title="Toggle tactile water droplet sound"
              >
                <Droplets className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Live Spasm Filter Absorbed Notice */}
        {lastFilterNotice && (
          <div className="px-6 sm:px-8 py-3.5 bg-[#FEF9C3]/70 border-t border-[#FDE047] flex items-center gap-3 text-[13px]">
            <div className="w-7 h-7 rounded-full bg-[#FEF9C3] border border-[#FDE047] flex items-center justify-center shrink-0">
              <Waves className="w-4 h-4 text-[#B8860B] animate-pulse" />
            </div>
            <div className="space-y-0.5">
              <span className="signature-kicker text-[#B8860B]">
                Spasm Filter Activated
              </span>
              <div className="text-[#141414] font-semibold font-body">
                {lastFilterNotice}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Dedicated Emergency Actions (Top Section with Crisp Red Outline) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <span className="signature-kicker text-[#C62828]">
            Emergency Assistance · High Priority Tier 3
          </span>
          <span className="text-[12px] font-semibold text-[#C62828] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#C62828] animate-ping" />
            Instant EMT &amp; Responder Override
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {EMERGENCY_BUTTONS.map((btn) => {
            const isRippling = activeRippleId === btn.id;

            return (
              <button
                key={btn.id}
                onClick={() => handleTap(btn)}
                disabled={isProcessing}
                className="group relative overflow-hidden text-left p-6 rounded-[24px] bg-white border-2 border-[#ef4444] shadow-[0_10px_30px_-10px_rgba(239,68,68,0.18)] hover:shadow-[0_14px_36px_-10px_rgba(239,68,68,0.25)] transition-all duration-200 flex flex-col justify-between min-h-[180px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#ef4444] active:scale-[0.985] cursor-pointer"
              >
                {/* Concentric Water Ripple on Tap */}
                {isRippling && (
                  <div className="absolute inset-0 m-auto w-12 h-12 rounded-full pointer-events-none animate-ripple bg-[#ef4444]/25 border border-[#ef4444]" />
                )}

                {/* Top Row: Visual Chamber & Single Red Pill Badge */}
                <div className="flex items-start justify-between w-full relative z-10">
                  <div className="flex items-center gap-3">
                    {/* Icon or Photo thumbnail */}
                    {btn.photoUrl ? (
                      <div className="relative w-14 h-14 rounded-[16px] overflow-hidden border border-[#FFCDD2] shadow-sm">
                        <img
                          src={btn.photoUrl}
                          alt={btn.label}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                          referrerPolicy="no-referrer"
                        />
                        <div className="absolute inset-0 bg-[#C62828]/25 flex items-center justify-center">
                          <Unlock className="w-6 h-6 text-white drop-shadow-md" />
                        </div>
                      </div>
                    ) : (
                      <div className="w-14 h-14 rounded-[16px] bg-[#FDECEA] border border-[#FFCDD2] flex items-center justify-center">
                        {renderIcon(btn.iconName, true)}
                      </div>
                    )}

                    <div>
                      <span className="signature-kicker text-[#C62828] block">
                        Emergency Bypass
                      </span>
                      <span className="text-[12px] font-semibold text-[#141414]">
                        Zero-Delay Execution
                      </span>
                    </div>
                  </div>

                  {/* One small pill badge only (Manrope 600) */}
                  <span className="bg-[#FDECEA] text-[#C62828] border border-[#FFCDD2] rounded-full px-3 py-1 text-[12px] font-semibold font-body">
                    Emergency
                  </span>
                </div>

                {/* Title and Patient Description */}
                <div className="mt-4 relative z-10 space-y-1">
                  <h3 className="font-heading text-lg font-bold text-[#141414] tracking-[-0.025em]">
                    {btn.label}
                  </h3>
                  <p className="text-[13px] font-body text-[#6B6B6B] leading-relaxed">
                    {btn.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Daily Autonomy Actions: Crisp White Cards, Deep Forest Anchor, Single-Line Titles */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between px-1">
          <span className="signature-kicker">
            Daily Autonomy Actions
          </span>
          <span className="text-[13px] font-semibold text-[#6B6B6B]">
            6 Tactile Direct &amp; Caregiver Actions
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {DAILY_BUTTONS.map((btn) => {
            const isTier2 = btn.tierExpected === 'Tier 2';
            const isRippling = activeRippleId === btn.id;

            return (
              <button
                key={btn.id}
                onClick={() => handleTap(btn)}
                disabled={isProcessing}
                className="group relative overflow-hidden text-left p-6 rounded-[24px] bg-white border border-[#E6DFD2] shadow-[0_10px_30px_-10px_rgba(26,50,38,0.08)] hover:shadow-[0_16px_36px_-12px_rgba(26,50,38,0.14)] hover:border-[#D4A373]/60 transition-all duration-200 flex flex-col justify-between min-h-[200px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1A3226] active:scale-[0.985] cursor-pointer"
              >
                {/* Concentric Water Ripple on Tap */}
                {isRippling && (
                  <div
                    className={`absolute inset-0 m-auto w-12 h-12 rounded-full pointer-events-none animate-ripple ${
                      isTier2
                        ? 'bg-[#D4A373]/30 border border-[#D4A373]'
                        : 'bg-[#1A3226]/20 border border-[#1A3226]'
                    }`}
                  />
                )}

                {/* Top Row: Icon / Photo Chamber with Deep Forest (#1A3226) & One Small Pill Badge */}
                <div className="flex items-start justify-between w-full relative z-10">
                  {btn.photoUrl ? (
                    <div className="relative w-12 h-12 rounded-[16px] overflow-hidden border border-[#E6DFD2] shadow-xs group-hover:scale-105 transition-transform duration-200">
                      <img
                        src={btn.photoUrl}
                        alt={btn.label}
                        className="w-full h-full object-cover filter brightness-[0.95]"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute inset-0 bg-[#1A3226]/20 flex items-center justify-center">
                        {btn.iconName === 'Utensils' && <Utensils className="w-5 h-5 text-white drop-shadow-sm" />}
                        {btn.iconName === 'Bed' && <Bed className="w-5 h-5 text-white drop-shadow-sm" />}
                      </div>
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-[16px] bg-[#F7F2EA] border border-[#E6DFD2] flex items-center justify-center transition-transform group-hover:scale-105">
                      {renderIcon(btn.iconName, false)}
                    </div>
                  )}

                  {/* One small pill badge only (Color has a job: Manrope 600) */}
                  {isTier2 ? (
                    <span className="bg-[#FEF9C3] text-[#B8860B] border border-[#FDE047]/60 rounded-full px-3 py-1 text-[12px] font-semibold font-body">
                      Caregiver Approval
                    </span>
                  ) : (
                    <span className="bg-[#EDF7ED] text-[#2E7D32] border border-[#C8E6C9] rounded-full px-3 py-1 text-[12px] font-semibold font-body">
                      Direct Action
                    </span>
                  )}
                </div>

                {/* Bottom Row: Fixed Single-Line Title and Description aligned at exact same vertical height */}
                <div className="mt-5 relative z-10 space-y-1">
                  <h3 className="font-heading text-lg font-bold text-[#141414] tracking-[-0.025em] group-hover:text-[#1A3226] transition-colors truncate">
                    {btn.label}
                  </h3>
                  <p className="text-[13px] font-body text-[#6B6B6B] line-clamp-2 leading-relaxed min-h-[38px]">
                    {btn.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. Three Human-Centered Principles with Editorial Garamond Touches */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-3">
        <div className="bg-white rounded-[24px] border border-[#E6DFD2] p-6 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.06)] space-y-2">
          <span className="signature-kicker">Tremor Protection</span>
          <h4 className="font-heading text-base font-bold text-[#141414]">
            400ms Spasm Filter
          </h4>
          <p className="text-[13px] font-body text-[#6B6B6B] leading-relaxed">
            Involuntary muscle contractions are absorbed peacefully. Rapid double-taps within 400 milliseconds are filtered out before reaching any smart hardware.
          </p>
        </div>

        <div className="bg-white rounded-[24px] border border-[#E6DFD2] p-6 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.06)] space-y-2">
          <span className="signature-kicker">Safety Review</span>
          <h4 className="font-heading text-base font-bold text-[#141414]">
            Caregiver Verification
          </h4>
          <p className="text-[13px] font-body text-[#6B6B6B] leading-relaxed">
            High-stakes orders and medical logs hold in a verification loop until Sarah approves via SMS, protecting you from accidental charges or unverified notes.
          </p>
        </div>

        <div className="bg-white rounded-[24px] border border-[#E6DFD2] p-6 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.06)] space-y-2">
          <span className="signature-kicker">Emergency Override</span>
          <h4 className="font-heading text-base font-bold text-[#141414]">
            Instant First Responder Entry
          </h4>
          <p className="text-[13px] font-body text-[#6B6B6B] leading-relaxed">
            In an emergency, unlocking the front entrance deadbolt bypasses all delays so paramedics and family have an unblocked pathway inside.
          </p>
        </div>
      </div>
    </div>
  );
};
