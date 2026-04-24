import styles from './gauge.module.css'
import { tempPercent, zoneTone, type TempBand } from './zones'
import { formatAge, ageMs } from '../../shared/staleness'

interface RangeTick {
  label: string
  /** Position 0..100. */
  percent: number
  /** Corner anchor (lo = 0%, hi = 100%). */
  edge?: 'lo' | 'hi'
  /** Marks a safe-band edge — label gets weight-500 and muted color. */
  safeEdge?: boolean
}

interface TempGaugeProps {
  label: string
  /** Register name in tooltip / log context. */
  celsius: number | null | undefined
  commFault?: boolean
  band: TempBand
  /** Positions where the safe-edge `.lim` ticks sit, in percent of the
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
  const fillToneClass =
    tone === 'caution' ? styles.caution
    : tone === 'danger' ? styles.danger
    : ''

  const valueText = commFault
    ? 'SENSOR FAULT'
    : celsius == null
    ? '—'
    : `${celsius.toFixed(1)} °C`

  const fillPercent =
    !commFault && celsius != null ? tempPercent(celsius) : 0
  const showFill = !commFault && celsius != null

  const hasData = receivedAt != null
  const age = ageMs(receivedAt ?? null, nowMs)

  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <div className={styles.barWrap}>
        <div className={styles.bar}>
          {showFill && (
            <div
              className={`${styles.fill} ${fillToneClass}`}
              style={{ width: `${fillPercent}%` }}
            />
          )}
          <div className={styles.lim} style={{ left: `${safeLoPercent}%` }} />
          <div className={styles.lim} style={{ left: `${safeHiPercent}%` }} />
          {showFill && (
            <div className={styles.marker} style={{ left: `${fillPercent}%` }} />
          )}
        </div>
        <div className={styles.axis}>
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
