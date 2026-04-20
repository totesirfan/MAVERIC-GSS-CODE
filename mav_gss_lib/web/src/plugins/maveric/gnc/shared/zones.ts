export interface TempBand {
  lo: number
  hi: number
}

// Safe operating ranges per GNC Registers WIP CSV (Apr 17 2026).
// Hard caution/danger thresholds not yet specified — anything outside
// the safe band renders as caution.
export const TEMP_BANDS = {
  ADCS_TMP: { lo: -25, hi:  70 },  // reg 0/148
  FSS_TMP1: { lo: -20, hi:  85 },  // reg 0/153, source for NVG_TMP
} as const

export type ZoneTone = 'nominal' | 'caution' | 'danger'

export function zoneTone(
  celsius: number | null | undefined,
  band: TempBand,
): ZoneTone | null {
  if (celsius == null) return null
  if (celsius >= band.lo && celsius <= band.hi) return 'nominal'
  return 'caution'
}

// Temp gauges share a common −40..+90 °C display scale; the safe-band
// edges are positioned as a percentage of that scale.
export const TEMP_DISPLAY_MIN = -40
export const TEMP_DISPLAY_MAX = 90
export const TEMP_DISPLAY_RANGE = TEMP_DISPLAY_MAX - TEMP_DISPLAY_MIN

export function tempPercent(celsius: number): number {
  const raw = ((celsius - TEMP_DISPLAY_MIN) / TEMP_DISPLAY_RANGE) * 100
  return Math.max(0, Math.min(100, raw))
}
