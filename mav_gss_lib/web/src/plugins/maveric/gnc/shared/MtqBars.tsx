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
  kind:
    | { type: 'saturation'; loPercent: number; hiPercent: number }
    | { type: 'fill'; leftPercent: number; widthPercent: number }
    | { type: 'none' }
  muted?: boolean
}

export function MtqBar({ axis, valueText, unit, kind, muted }: MtqBarProps) {
  return (
    <div className={styles.axisRow}>
      <span className={styles.axisLabel}>{axis}</span>
      <div className={styles.bar}>
        {kind.type === 'saturation' && (
          <>
            <div className={styles.satLo} style={{ left: `${kind.loPercent}%` }} />
            <div className={styles.satHi} style={{ left: `${kind.hiPercent}%` }} />
          </>
        )}
        {kind.type === 'fill' && (
          <div
            className={styles.fill}
            style={{ left: `${kind.leftPercent}%`, width: `${kind.widthPercent}%` }}
          />
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
