import { ThemeColors, ThemeId } from '../types';

export const THEMES: Record<ThemeId, ThemeColors> = {
  'sage': {
    id: 'sage',
    name: 'Sage Pebble',
    subtitle: 'Soothing organic greens & emerald autonomy',
    bgBase: '#f4f7f4', // sage-50
    cardBase: '#e5ebe5', // sage-100
    cardBorder: '#ccd9cc', // sage-200
    cardShadow: '0 4px 14px -2px rgba(41, 55, 41, 0.06), inset 0 1px 1px 0 rgba(255, 255, 255, 0.6)',
    textPrimary: '#293729', // sage-900
    textSecondary: '#466146', // sage-600
    textMuted: '#7d9e7d', // sage-400
    accent: '#10b981', // Emerald Green
    accentLight: 'rgba(16, 185, 129, 0.14)',
    emergency: '#ef4444', // Red
    emergencyLight: 'rgba(239, 68, 68, 0.14)',
    tier2: '#5a7a5a', // sage-500
    tier2Light: 'rgba(90, 122, 90, 0.16)',
    navBg: 'rgba(244, 247, 244, 0.94)', // sage-50 blur
    subtleBg: '#ccd9cc', // sage-200
    inputBg: '#ffffff', // Pure White
    codeBg: '#293729', // sage-900
    isDark: false
  },
  'earth': {
    id: 'earth',
    name: 'Earth Pebble',
    subtitle: 'Warm terracotta, natural ceramic & clear blue',
    bgBase: '#fdfaf6', // earth-50
    cardBase: '#f9f1e7', // earth-100
    cardBorder: '#f1e0cc', // earth-200
    cardShadow: '0 4px 14px -2px rgba(102, 64, 46, 0.06), inset 0 1px 1px 0 rgba(255, 255, 255, 0.7)',
    textPrimary: '#66402e', // earth-900
    textSecondary: '#995c3a', // earth-700
    textMuted: '#d4a576', // earth-400
    accent: '#b87445', // earth-600
    accentLight: 'rgba(184, 116, 69, 0.14)',
    emergency: '#ef4444', // Red
    emergencyLight: 'rgba(239, 68, 68, 0.14)',
    tier2: '#c68a54', // earth-500
    tier2Light: 'rgba(198, 138, 84, 0.16)',
    navBg: 'rgba(253, 250, 246, 0.94)', // earth-50 blur
    subtleBg: '#f1e0cc', // earth-200
    inputBg: '#ffffff', // Pure White
    codeBg: '#66402e', // earth-900
    isDark: false
  },
  'sage-night': {
    id: 'sage-night',
    name: 'Sage Night',
    subtitle: 'Deep forest stone & luminous emerald',
    bgBase: '#293729', // sage-900
    cardBase: '#304130', // sage-800
    cardBorder: '#3a4f3a', // sage-700
    cardShadow: '0 8px 24px -4px rgba(0, 0, 0, 0.5), inset 0 1px 1px 0 rgba(255, 255, 255, 0.08)',
    textPrimary: '#ffffff', // Pure White
    textSecondary: '#a8bfa8', // sage-300
    textMuted: '#7d9e7d', // sage-400
    accent: '#10b981', // Emerald Green
    accentLight: 'rgba(16, 185, 129, 0.20)',
    emergency: '#ef4444', // Red
    emergencyLight: 'rgba(239, 68, 68, 0.22)',
    tier2: '#7d9e7d', // sage-400
    tier2Light: 'rgba(125, 158, 125, 0.20)',
    navBg: 'rgba(41, 55, 41, 0.94)', // sage-900 blur
    subtleBg: '#3a4f3a', // sage-700
    inputBg: '#3a4f3a', // sage-700
    codeBg: '#1e261e',
    isDark: true
  },
  'earth-night': {
    id: 'earth-night',
    name: 'Earth Night',
    subtitle: 'Rich dark espresso & sky blue accents',
    bgBase: '#66402e', // earth-900
    cardBase: '#7c4c34', // earth-800
    cardBorder: '#995c3a', // earth-700
    cardShadow: '0 8px 24px -4px rgba(0, 0, 0, 0.5), inset 0 1px 1px 0 rgba(255, 255, 255, 0.08)',
    textPrimary: '#ffffff', // Pure White
    textSecondary: '#e4c6a4', // earth-300
    textMuted: '#d4a576', // earth-400
    accent: '#60a5fa', // Blue
    accentLight: 'rgba(96, 165, 250, 0.20)',
    emergency: '#ef4444', // Red
    emergencyLight: 'rgba(239, 68, 68, 0.22)',
    tier2: '#d4a576', // earth-400
    tier2Light: 'rgba(212, 165, 118, 0.20)',
    navBg: 'rgba(102, 64, 46, 0.94)', // earth-900 blur
    subtleBg: '#995c3a', // earth-700
    inputBg: '#995c3a', // earth-700
    codeBg: '#472c1e',
    isDark: true
  }
};
