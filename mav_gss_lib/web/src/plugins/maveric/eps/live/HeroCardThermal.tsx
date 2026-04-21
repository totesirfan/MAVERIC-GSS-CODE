import { memo } from 'react'
import { fmt, clamp } from '../derive'
import type { AlarmLevel } from '../types'

const AXIS_LO = -20
const AXIS_HI = 85
const AXIS_RANGE = AXIS_HI - AXIS_LO
const CRIT_LO = -10
const WARN_LO = 0
const WARN_HI = 60
const CRIT_HI = 85

function bigTone(alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'big danger'
  if (alarm === 'caution') return 'big warning'
  return 'big'
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

function markerPct(T: number): number {
  return (clamp(T, AXIS_LO, AXIS_HI) - AXIS_LO) / AXIS_RANGE * 100
}

function formatEta(s: number | null): string {
  if (s === null || !Number.isFinite(s)) return '—'
  if (s < 0) return 'past'
  if (s < 60) return `${Math.round(s)} s`
  if (s < 3600) return `${Math.round(s / 60)} m`
  return `${(s / 3600).toFixed(1)} h`
}

interface Props {
  T_DIE: number
  TS_ADC: number
  prev_T_DIE: number
  etaSeconds: number | null
  alarm: AlarmLevel
}

function HeroCardThermalInner({ T_DIE, TS_ADC, prev_T_DIE, etaSeconds, alarm }: Props) {
  const hasPrev = Number.isFinite(prev_T_DIE)
  const delta = hasPrev ? T_DIE - prev_T_DIE : NaN
  const deltaClass = !Number.isFinite(delta)
    ? 'd-v flat'
    : Math.abs(delta) < 0.05
      ? 'd-v flat'
      : delta > 0 ? 'd-v up' : 'd-v down'
  const deltaText = Number.isFinite(delta) ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} °C` : '—'
  const showEta = etaSeconds !== null && Number.isFinite(etaSeconds) && alarm === 'caution'

  return (
    <div className="card live" data-component="HeroCard" data-kind="thermal">
      <div className="card-head live-bg">
        <div className="card-head-left">
          <span className="card-title">Thermal</span>
          <span className="card-sub">T_DIE · TS_ADC</span>
        </div>
        <div className={dotClass(alarm)}>
          <span className="sh">●</span><span className="lbl">{dotLabel(alarm)}</span>
        </div>
      </div>
      <div className="hero-card-body">
        <div className="hero-reading">
          <span className={bigTone(alarm)} data-hk="T_DIE">{fmt(T_DIE, 1)}</span>
          <span className="unit">°C</span>
          <span className="hero-sub" style={{ marginLeft: 'auto' }}>
            TS_ADC <span data-hk="TS_ADC">{fmt(TS_ADC, 1)}%</span>
            <span className="chip" title="Battery thermistor polarity: lower % = hotter">INV</span>
          </span>
        </div>
        <div>
          <div
            className="therm-gauge"
            data-gauge="T_DIE"
            role="img"
            aria-label={`T_DIE ${fmt(T_DIE, 1)} °C, safe band 0 to 60 °C`}
          >
            <div className="band-ok" style={{ left: `${markerPct(WARN_LO)}%`, right: `${100 - markerPct(WARN_HI)}%` }} />
            <div className="lim crit" style={{ left: `${markerPct(CRIT_LO)}%` }} />
            <div className="lim warn" style={{ left: `${markerPct(WARN_LO)}%` }} />
            <div className="lim warn" style={{ left: `${markerPct(WARN_HI)}%` }} />
            <div className="lim crit" style={{ left: `${markerPct(CRIT_HI) - 0.5}%` }} />
            {Number.isFinite(T_DIE) && (
              <div className="marker" style={{ left: `${markerPct(T_DIE)}%` }} />
            )}
          </div>
          <div className="therm-axis">
            <span>-20</span><span>0</span><span>60</span><span>85 °C</span>
          </div>
        </div>
        {hasPrev && (
          <div className="delta-row" data-delta="T_DIE" title="Change since previous packet in this link">
            <span className="d-k">Δ prev pkt</span>
            <span className={deltaClass}>{deltaText}</span>
          </div>
        )}
        {showEta && (
          <div className="eta-row" data-eta="T_DIE">
            <span className="e-k">ETA → {WARN_HI} °C</span>
            <span className="e-v">{formatEta(etaSeconds)}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export const HeroCardThermal = memo(HeroCardThermalInner)
