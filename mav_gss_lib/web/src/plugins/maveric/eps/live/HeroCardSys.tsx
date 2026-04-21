import { memo } from 'react'
import { fmt, clamp } from '../derive'
import type { AlarmLevel } from '../types'

const AXIS_LO = 6.0
const AXIS_HI = 9.5
const AXIS_RANGE = AXIS_HI - AXIS_LO

function bigTone(alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'big danger'
  if (alarm === 'caution') return 'big warning'
  if (alarm === 'ok') return 'big success'
  return 'big muted'
}

function dotClass(alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'dot danger'
  if (alarm === 'caution') return 'dot warn'
  if (alarm === 'ok') return 'dot success'
  return 'dot neutral'
}

function dotLabel(alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'ALM'
  if (alarm === 'caution') return 'CAU'
  if (alarm === 'ok') return 'NOM'
  return '—'
}

function pct(v: number): number {
  return (clamp(v, AXIS_LO, AXIS_HI) - AXIS_LO) / AXIS_RANGE * 100
}

interface Props {
  V_SYS: number
  prev_V_SYS: number
  alarm: AlarmLevel
}

function HeroCardSysInner({ V_SYS, prev_V_SYS, alarm }: Props) {
  const hasPrev = Number.isFinite(prev_V_SYS)
  const delta = hasPrev ? V_SYS - prev_V_SYS : NaN
  const deltaClass = !Number.isFinite(delta)
    ? 'd-v flat'
    : Math.abs(delta) < 0.001
      ? 'd-v flat'
      : delta > 0 ? 'd-v up' : 'd-v down'
  const deltaText = Number.isFinite(delta) ? `${delta >= 0 ? '+' : ''}${delta.toFixed(3)} V` : '—'
  const fill = Number.isFinite(V_SYS) ? pct(V_SYS) : 0

  return (
    <div className="card live" data-component="HeroCard" data-kind="sys">
      <div className="card-head live-bg">
        <div className="card-head-left">
          <span className="card-title">System</span>
          <span className="card-sub">V_SYS</span>
        </div>
        <div className={dotClass(alarm)}>
          <span className="sh">●</span><span className="lbl">{dotLabel(alarm)}</span>
        </div>
      </div>
      <div className="hero-card-body">
        <div className="hero-reading">
          <span className={bigTone(alarm)} data-hk="V_SYS">{fmt(V_SYS, 3)}</span>
          <span className="unit">V</span>
        </div>
        <div title="V_SYS position in bus operating range (6.0–9.5 V)">
          <div
            className="soc-gauge"
            data-gauge="V_SYS"
            role="img"
            aria-label={`V_SYS ${fmt(V_SYS, 3)} V`}
          >
            <div className="fill" style={{ width: `${fill}%` }} />
          </div>
          <div className="soc-axis">
            <span>6.0</span><span>9.5 V</span>
          </div>
        </div>
        {hasPrev && (
          <div className="delta-row" data-delta="V_SYS" title="Change since previous packet in this link">
            <span className="d-k">Δ prev pkt</span>
            <span className={deltaClass}>{deltaText}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export const HeroCardSys = memo(HeroCardSysInner)
