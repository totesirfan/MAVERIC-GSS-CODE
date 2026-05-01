/** Formatting helpers for GNC dashboard values. */

export function fmtVec3(v: number[] | null | undefined, decimals = 4): string {
  if (!v || v.length < 3) return '—'
  return `${v[0].toFixed(decimals)}, ${v[1].toFixed(decimals)}, ${v[2].toFixed(decimals)}`
}

export function fmtQuat(v: number[] | null | undefined, decimals = 3): string {
  if (!v || v.length < 4) return '—'
  return v.map(n => n.toFixed(decimals)).join(', ')
}

export function fmtYpr(ypr: [number, number, number] | null, decimals = 2): string {
  if (!ypr) return '—, —, —'
  return ypr.map(n => n.toFixed(decimals)).join(', ')
}

const WEEKDAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** 4-digit ISO year (assumes 20XX). BCD year is 0..99 from the spacecraft. */
export function fmtBcdDate(d: { year: number; month: number; day: number; weekday?: number } | null | undefined): string {
  if (!d) return '—'
  const iso = `${2000 + d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`
  if (typeof d.weekday === 'number') {
    const wd = WEEKDAY_NAMES[d.weekday] ?? ''
    return wd ? `${iso} (${wd})` : iso
  }
  return iso
}

export function fmtBcdTime(t: { hour: number; minute: number; second: number } | null | undefined): string {
  if (!t) return '—'
  return `${String(t.hour).padStart(2, '0')}:${String(t.minute).padStart(2, '0')}:${String(t.second).padStart(2, '0')}`
}

export function fmtTempC(tmp: { celsius: number | null; comm_fault: boolean } | null | undefined): string {
  if (!tmp) return '—'
  if (tmp.comm_fault) return 'SENSOR FAULT'
  if (tmp.celsius === null) return '—'
  return `${tmp.celsius.toFixed(1)} °C`
}
