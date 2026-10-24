/**
 * Pebble & Ripple Design System: Glass, Shapes & Component Recipes
 * 
 * Spec:
 * - Frosted-glass cards: White at 30% opacity with a 20px blur on web (82% on mobile).
 * - Soft shadows tinted green rather than black (using Deep Forest rgba(26, 50, 38, ...)).
 * - Radii: 24 on big cards, 16 and 12 on buttons, fully rounded pills (9999px).
 * - Faint photo background covered by a heavy cream gradient.
 */

export const glass = {
  // Frosted Glass Presets
  cards: {
    web: {
      background: 'rgba(255, 255, 255, 0.30)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(255, 255, 255, 0.55)',
    },
    mobile: {
      background: 'rgba(255, 255, 255, 0.82)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(255, 255, 255, 0.70)',
    },
    opaqueCream: {
      background: '#F7F2EA',
      border: '1px solid #EFE9DE',
    }
  },

  // Soft shadows tinted green (#1A3226) rather than black
  shadows: {
    card: '0 10px 30px -10px rgba(26, 50, 38, 0.12), 0 4px 12px -2px rgba(26, 50, 38, 0.06)',
    cardHover: '0 16px 36px -12px rgba(26, 50, 38, 0.18), 0 6px 16px -2px rgba(26, 50, 38, 0.08)',
    button: '0 4px 14px -2px rgba(26, 50, 38, 0.14)',
    elevatedPill: '0 6px 20px -4px rgba(26, 50, 38, 0.10)'
  },

  // Radii Specs
  radii: {
    bigCard: '24px',   // 24 on big cards
    buttonLarge: '16px', // 16 on main buttons
    buttonSmall: '12px', // 12 on secondary controls
    pill: '9999px'      // Fully rounded pills
  },

  // Faint photo background covered by heavy cream gradient
  photoBackground: {
    backgroundImage: `
      linear-gradient(180deg, rgba(250, 249, 246, 0.88) 0%, rgba(247, 242, 234, 0.94) 50%, rgba(250, 249, 246, 0.98) 100%),
      radial-gradient(circle at 10% 20%, rgba(212, 163, 115, 0.15) 0%, transparent 40%),
      radial-gradient(circle at 90% 80%, rgba(26, 50, 38, 0.08) 0%, transparent 45%)
    `
  }
} as const;

export type Glass = typeof glass;
