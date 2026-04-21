import { memo } from 'react'
import { fmt } from '../derive'
import type { AlarmLevel, ChargeDir } from '../types'

function bigTone(alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'big danger'
  if (alarm === 'caution') return 'big warning'
  return 'big'
}

function dotClass(dir: ChargeDir, alarm: AlarmLevel): string {
  if (alarm === 'danger') return 'dot danger'
  if (alarm === 'caution') return 'dot warn'
  if (dir === 'charge') return 'dot success'
  if (dir === 'discharge') return 'dot warn'
  return 'dot neutral'
}

function dotGlyph(dir: ChargeDir): string {
  if (dir === 'charge') return '▲'
  if (dir === 'discharge') return '▼'
  return '◐'
}

function dotLabel(dir: ChargeDir): string {
  if (dir === 'charge') return 'CHG'
  if (dir === 'discharge') return 'DIS'
  return 'IDLE'
}

function chipClass(dir: ChargeDir): string {
  if (dir === 'charge') return 'chip charge'
  if (dir === 'discharge') return 'chip dis'
  return 'chip idle'
}

function formatIBat(v: number): string {
  if (!Number.isFinite(v)) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(3)} A`
}

interface Props {
  V_BAT: number
  I_BAT: number
  prev_V_BAT: number
  chargeDir: ChargeDir
  soc: number | null
  alarm: AlarmLevel
}

function HeroCardBatInner({ V_BAT, I_BAT, prev_V_BAT, chargeDir, soc, alarm }: Props) {
  const hasPrev = Number.isFinite(prev_V_BAT)
  const delta = hasPrev ? V_BAT - prev_V_BAT : NaN
  const deltaClass = !Number.isFinite(delta)
    ? 'd-v flat'
    : Math.abs(delta) < 0.001
      ? 'd-v flat'
      : delta > 0 ? 'd-v up' : 'd-v down'
  const deltaText = Number.isFinite(delta) ? `${delta >= 0 ? '+' : ''}${delta.toFixed(3)} V` : '—'
  const fill = soc ?? 0

  return (
    <div className="card live" data-component="HeroCard" data-kind="bat">
      <div className="card-head live-bg">
        <div className="card-head-left">
          <span className="card-title">Battery</span>
          <span className="card-sub">V_BAT · 2S</span>
        </div>
        <div className={dotClass(chargeDir, alarm)} data-state={chargeDir}>
          <span className="sh">{dotGlyph(chargeDir)}</span>
          <span className="lbl">{dotLabel(chargeDir)}</span>
        </div>
      </div>
      <div className="hero-card-body">
        <div className="hero-reading">
          <span className={bigTone(alarm)} data-hk="V_BAT">{fmt(V_BAT, 3)}</span>
          <span className="unit">V</span>
          <span className="hero-sub" style={{ marginLeft: 'auto' }}>
            I_BAT <span data-hk="I_BAT">{formatIBat(I_BAT)}</span>
            <span className={chipClass(chargeDir)} title="+ = charging, − = discharging">±</span>
            {' · '}
            <span data-state={chargeDir}>{dotLabel(chargeDir)}</span>
          </span>
        </div>
        <div>
          <div
            className="soc-gauge"
            title="Coarse SoC estimate · pack 6.0–8.4 V → 0–100 %; warn 25 %, nom 58 %"
            data-gauge="socFromVbat(V_BAT)"
            role="img"
            aria-label={soc !== null ? `Battery state of charge approximately ${Math.round(soc)} percent, coarse estimate` : 'Battery state of charge unknown'}
          >
            <div className="fill" style={{ width: `${fill}%` }} />
            <div className="lim" style={{ left: '25%' }} />
            <div className="lim" style={{ left: '58%', background: 'var(--state-success)', opacity: 0.85 }} />
          </div>
          <div className="soc-axis">
            <span>0 %</span><span>warn 25</span><span>nom 58</span><span>100 %</span>
          </div>
        </div>
        {hasPrev && (
          <div className="delta-row" data-delta="V_BAT" title="Change since previous packet in this link">
            <span className="d-k">Δ prev pkt</span>
            <span className={deltaClass}>{deltaText}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export const HeroCardBat = memo(HeroCardBatInner)
