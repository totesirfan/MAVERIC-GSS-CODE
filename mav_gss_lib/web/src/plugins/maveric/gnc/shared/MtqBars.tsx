import type { ReactNode } from 'react'
import styles from './bar-viz.module.css'

export interface AxisTick {
  label: string
  /** Position along the bar, 0..100. */
  percent: number
  /** True for the leftmost/rightmost tick (anchors text to the edge). */
  edge?: 'lo' | 'hi'
}

interface MtqBarProps {
  axis: string
  valueText: string
  unit: string
  /** 0..100 — center-anchored fill drawn between 50% and this position,
   *  plus a 1 px marker line at the value's own position. */
  valuePercent?: number
  /** 0..100 — warn-low threshold line. */
  warnLoPercent?: number
  /** 0..100 — warn-high threshold line. */
  warnHiPercent?: number
  muted?: boolean
}

export function MtqBar({
  axis,
  valueText,
  unit,
  valuePercent,
  warnLoPercent,
  warnHiPercent,
  muted,
}: MtqBarProps) {
  // Center-anchored fill between 50% and the value's position.
  let fillLeft: number | null = null
  let fillWidth = 0
  if (valuePercent != null) {
    if (valuePercent >= 50) {
      fillLeft = 50
      fillWidth = valuePercent - 50
    } else {
      fillLeft = valuePercent
      fillWidth = 50 - valuePercent
    }
  }
  return (
    <div className={styles.axisRow}>
      <span className={styles.axisLabel}>{axis}</span>
      <div className={styles.bar}>
        {warnLoPercent != null && (
          <div className={styles.satLo} style={{ left: `${warnLoPercent}%` }} />
        )}
        {warnHiPercent != null && (
          <div className={styles.satHi} style={{ left: `${warnHiPercent}%` }} />
        )}
        {fillLeft != null && (
          <div
            className={styles.fill}
            style={{ left: `${fillLeft}%`, width: `${fillWidth}%` }}
          />
        )}
        {valuePercent != null && (
          <div className={styles.marker} style={{ left: `${valuePercent}%` }} />
        )}
      </div>
      <span className={`${styles.val} ${muted ? styles.valMuted : ''}`}>
        {valueText}
        <span className={styles.unit}>{unit}</span>
      </span>
    </div>
  )
}

interface MtqScaleProps {
  ticks: AxisTick[]
}

export function MtqScale({ ticks }: MtqScaleProps) {
  return (
    <div className={styles.scaleRow}>
      <span />
      <div className={styles.ticks}>
        {ticks.map((t, i) => (
          <span
            key={i}
            className={`${styles.tick} ${
              t.edge === 'lo' ? styles.tickEdgeLo
              : t.edge === 'hi' ? styles.tickEdgeHi
              : ''
            }`}
            style={{ left: `${t.percent}%` }}
          >
            {t.label}
          </span>
        ))}
      </div>
      <span />
    </div>
  )
}

interface MtqBlockProps {
  title: string
  subtitle: string
  ticks: AxisTick[]
  children: ReactNode
}

export function MtqBlock({ title, subtitle, ticks, children }: MtqBlockProps) {
  return (
    <div className={styles.block}>
      <div className={styles.head}>
        <span className={styles.headTitle}>{title}</span>
        <span className={styles.headSub}>{subtitle}</span>
      </div>
      {children}
      <MtqScale ticks={ticks} />
    </div>
  )
}
