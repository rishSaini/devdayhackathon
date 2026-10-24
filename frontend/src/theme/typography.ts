/**
 * Pebble & Ripple Design System: Typography
 * 
 * Spec:
 * - Playfair Display Bold: For the logo only.
 * - Syne Bold: For headings only, with tight letter spacing (e.g., 32px at -0.8px / -0.025em).
 * - Manrope: For everything else. 600 SemiBold primary, then 400 Regular, 700 Bold, 500 Medium.
 * - Signature Detail: Section kicker labels — 10px Manrope Bold, all caps, widely spaced (tracking-[0.15em]), in #A0A0A0.
 * - Monospace: JetBrains Mono for telemetry, timestamps, and API schemas.
 * 
 * Note on quirk resolution:
 * Prior theme drafts mistakenly labeled Syne under serif slots.
 * Here Syne is correctly assigned to display/headings, and Playfair Display to serif logo.
 */

export const typography = {
  fontFamilies: {
    logo: "'Playfair Display', serif",
    heading: "'Syne', system-ui, sans-serif",
    body: "'Manrope', system-ui, -apple-system, sans-serif",
    garamond: "'Cormorant Garamond', 'Garamond', Georgia, serif",
    mono: "'JetBrains Mono', monospace",
    // Compatibility alias:
    serifHeading: "'Syne', system-ui, sans-serif"
  },
  
  weights: {
    regular: 400,
    medium: 500,
    semiBold: 600, // Most used weight
    bold: 700
  },

  letterSpacing: {
    headingTight: '-0.025em', // -0.8px at 32px
    kickerWide: '0.15em',     // 10px Manrope Bold, all caps, widely spaced
    normal: '0em'
  },

  signatureKicker: {
    fontSize: '10px',
    fontFamily: "'Manrope', sans-serif",
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.15em',
    color: '#A0A0A0'
  }
} as const;

export type Typography = typeof typography;
