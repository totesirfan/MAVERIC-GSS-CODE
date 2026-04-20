import styles from './gauge.module.css'
import { tempPercent, zoneTone, type TempBand } from './zones'
import { formatAge, ageMs } from './staleness'

interface RangeTick {
  label: string
  /** Position 0..100. */
  percent: number
  /** Corner anchor (lo = 0%, hi = 100%). */
  edge?: 'lo' | 'hi'
  /** Marks a safe-band edge — label gets weight-600. */
  safeEdge?: boolean
}

interface TempGaugeProps {
  label: string
  /** Register name in tooltip / log context. */
  celsius: number | null | undefined
  commFault?: boolean
  band: TempBand
  /** Positions where the in-bar `.limSafe` ticks sit, in percent of the
   *  display scale (−40..+90 by default). */
  safeLoPercent: number
  safeHiPercent: number
  /** Labelled range under the bar. */
  ticks: RangeTick[]
  receivedAt?: number | null
  nowMs: number
}

export function TempGauge({
  label,
  celsius,
  commFault,
  band,
  safeLoPercent,
  safeHiPercent,
  ticks,
  receivedAt,
  nowMs,
}: TempGaugeProps) {
  const tone = commFault ? 'danger' : zoneTone(celsius ?? null, band)
  const toneClass =
    tone === 'nominal' ? styles.nominal
    : tone === 'caution' ? styles.caution
    : tone === 'danger' ? styles.danger
    : ''

  const valueText = commFault
    ? 'SENSOR FAULT'
    : celsius == null
    ? '—'
    : `${celsius.toFixed(1)} °C`

  const markerLeft =
    !commFault && celsius != null ? `${tempPercent(celsius)}%` : null

  const hasData = receivedAt != null
  const age = ageMs(receivedAt ?? null, nowMs)

  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <div className={styles.gauge}>
        <div className={styles.limSafe} style={{ left: `${safeLoPercent}%` }} />
        <div className={styles.limSafe} style={{ left: `${safeHiPercent}%` }} />
        {markerLeft && <div className={styles.marker} style={{ left: markerLeft }} />}
        <div className={styles.range}>
          {ticks.map((t, i) => (
            <span
              key={i}
              className={`${styles.tick} ${
                t.edge === 'lo' ? styles.tickEdgeLo
                : t.edge === 'hi' ? styles.tickEdgeHi
                : ''
              } ${t.safeEdge ? styles.safeEdge : ''}`}
              style={{ left: `${t.percent}%` }}
            >
              {t.label}
            </span>
          ))}
        </div>
      </div>
      <span className={`${styles.value} ${toneClass}`}>{valueText}</span>
      <span className={styles.age}>{hasData ? formatAge(age) : '—'}</span>
    </div>
  )
}
