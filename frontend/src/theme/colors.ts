/**
 * Pebble & Ripple Design System: Colors
 * 
 * Spec:
 * - Main: Paper #FAF9F6, Deep Forest #1A3226, Warm Sand #D4A373
 * - Text: Ink #141414, Body #6B6B6B, Faint #A0A0A0
 * - Warm Creams: #FBFAF7, #F7F2EA, #EFE9DE, #E6DFD2
 * - Ocean & Emerald: #5B8DB8, #3E6E8E, #34D399, #10B981
 * - Status Badges: Pending #B8860B, Accepted #2E7D32, Declined #C62828, Likes #E8612A
 */

export const colors = {
  // Main
  paper: '#FAF9F6',
  deepForest: '#1A3226',
  warmSand: '#D4A373',

  // Text
  ink: '#141414',
  bodyText: '#6B6B6B',
  faintText: '#A0A0A0',

  // Supporting Warm Creams (used instead of harsh gray)
  creams: {
    50: '#FBFAF7',
    100: '#F7F2EA',
    200: '#EFE9DE',
    300: '#E6DFD2'
  },

  // Supporting Ocean & Emerald
  ocean: {
    light: '#5B8DB8',
    dark: '#3E6E8E'
  },
  emerald: {
    main: '#34D399',
    vibrant: '#10B981',
    dark: '#059669'
  },
  likes: '#E8612A',

  // Status Badges
  status: {
    pending: {
      bg: '#FEF9C3',
      text: '#B8860B',
      border: 'rgba(184, 134, 11, 0.25)'
    },
    accepted: {
      bg: '#EDF7ED',
      text: '#2E7D32',
      border: 'rgba(46, 125, 50, 0.25)'
    },
    declined: {
      bg: '#FDECEA',
      text: '#C62828',
      border: 'rgba(198, 40, 40, 0.25)'
    }
  },

  // Autonomy Tiers
  tier: {
    tier1: {
      accent: '#5B8DB8',
      bg: '#F7F2EA',
      border: '#EFE9DE',
      label: 'Immediate Autonomy'
    },
    tier2: {
      accent: '#D4A373',
      bg: '#F7F2EA',
      border: '#EFE9DE',
      label: 'Caregiver Approval'
    },
    tier3: {
      accent: '#C62828',
      bg: '#FDECEA',
      border: '#F8B4B4',
      label: 'Emergency Override'
    }
  }
} as const;

export type Colors = typeof colors;
