import { colors } from './colors';
import { typography } from './typography';
import { glass } from './glass';

export * from './colors';
export * from './typography';
export * from './glass';

/**
 * Pebble & Ripple Six Core Design System Sections:
 * 1. Typography
 * 2. Color Palette
 * 3. Glass Effect & Photo Background
 * 4. Shape, Spacing & Shadows
 * 5. Component Recipes
 * 6. Ready-to-use block of CSS variables
 */

export const theme = {
  colors,
  typography,
  glass,

  // Component Recipes
  recipes: {
    // 1. Primary Button: Deep Forest, white text, 16px radius
    primaryButton: 'bg-[#1A3226] hover:bg-[#14261d] text-white font-semibold rounded-[16px] px-5 py-3 shadow-[0_4px_14px_-2px_rgba(26,50,38,0.14)] active:scale-[0.98] transition-all duration-150',

    // 2. Secondary Button: Warm Cream, subtle cream border, Ink text
    secondaryButton: 'bg-[#F7F2EA] hover:bg-[#EFE9DE] border border-[#E6DFD2] text-[#141414] font-semibold rounded-[12px] px-4 py-2.5 transition-all duration-150',

    // 3. White Pill Button on Photos: White 80%, blurred, full pill
    photoPillButton: 'bg-white/80 hover:bg-white/95 backdrop-blur-md text-[#141414] font-semibold rounded-full px-4 py-2 shadow-sm border border-white/60 transition-all active:scale-95',

    // 4. Hero Card: 24px radius, 30% frosted glass, 20px blur, green-tinted shadow
    heroCard: 'bg-white/30 backdrop-blur-[20px] rounded-[24px] border border-white/60 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.12),0_4px_12px_-2px_rgba(26,50,38,0.06)] p-7 sm:p-8',

    // 5. Feature / Action Tile: 24px radius, tactile cream/glass
    actionTile: 'bg-white/35 hover:bg-white/55 backdrop-blur-[20px] rounded-[24px] border border-white/60 shadow-[0_10px_30px_-10px_rgba(26,50,38,0.08)] p-6 transition-all duration-200 active:scale-[0.985]',

    // 6. Signature Section Kicker: 10px Manrope Bold, all caps, widely spaced in #A0A0A0
    kicker: 'text-[10px] font-bold uppercase tracking-[0.15em] text-[#A0A0A0]',

    // 7. Status Badges:
    badges: {
      pending: 'bg-[#FEF9C3] text-[#B8860B] border border-[#FDE047]/50 rounded-full px-3 py-1 text-xs font-semibold',
      accepted: 'bg-[#EDF7ED] text-[#2E7D32] border border-[#C8E6C9] rounded-full px-3 py-1 text-xs font-semibold',
      declined: 'bg-[#FDECEA] text-[#C62828] border border-[#FFCDD2] rounded-full px-3 py-1 text-xs font-semibold'
    }
  }
} as const;

export default theme;
