/**
 * Beihang University brand palette + signal-class semantics.
 * Single source of truth for all dashboard colours.
 */
export const BEIHANG = {
  primary: "#003360", // deep blue
  secondary: "#344E7F", // medium blue
  accent: "#BCB245", // mustard
  ink: "#1F2A37", // near-black text
  slate: "#5B6B7F", // muted text
  mist: "#EEF2F7", // page background
  card: "#FFFFFF",
  line: "#D8E0EA", // hairline borders
} as const;

export const SIGNAL = {
  CLEAN: "#2E7D32", // green
  WARNING: "#E1A100", // amber
  DEGRADED: "#C0392B", // red
} as const;

export type SignalClass = keyof typeof SIGNAL;

/** Map P(DEGRADED) -> class using dashboard thresholds. */
export function classify(pDeg: number): SignalClass {
  if (pDeg < 0.3) return "CLEAN";
  if (pDeg < 0.7) return "WARNING";
  return "DEGRADED";
}

/** Continuous green→amber→red colour for a probability in [0,1]. */
export function riskColor(pDeg: number): string {
  const c = classify(pDeg);
  return SIGNAL[c];
}
