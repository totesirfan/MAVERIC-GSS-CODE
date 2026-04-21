import { memo } from 'react'
import { fmt } from '../derive'

const NOM_3V3 = 3.3
const NOM_5V0 = 5.0
const DEV_CAUTION = 0.05

interface Props {
  V3V3: number
  I3V3: number
  P3V3: number
  V5V0: number
  I5V0: number
  P5V0: number
}

function deviationPct(v: number, nom: number): number {
  return ((v - nom) / nom) * 100
}

function railState(v: number, nom: number): 'on' | 'caution' | 'alarm' {
  if (!Number.isFinite(v) || v <= 0) return 'alarm'
  const dev = Math.abs(v - nom) / nom
  if (dev > DEV_CAUTION) return 'caution'
  return 'on'
}

function fmtDevPct(v: number, nom: number): string {
  if (!Number.isFinite(v)) return '—'
  const p = deviationPct(v, nom)
  const sign = p >= 0 ? '+' : ''
  return `${sign}${p.toFixed(1)}% @ ${nom.toFixed(2)} V`
}

function mAText(I: number): string {
  if (!Number.isFinite(I)) return '—'
  return `${Math.round(I * 1000)} mA`
}

function RailsCardInner({ V3V3, I3V3, P3V3, V5V0, I5V0, P5V0 }: Props) {
  const s3 = railState(V3V3, NOM_3V3)
  const s5 = railState(V5V0, NOM_5V0)
  const allOk = s3 === 'on' && s5 === 'on'
  const dotCls = allOk ? 'dot success' : s3 === 'alarm' || s5 === 'alarm' ? 'dot danger' : 'dot warn'
  const dotLbl = allOk ? 'REG' : s3 === 'alarm' || s5 === 'alarm' ? 'ALM' : 'DEV'
  return (
    <div className="card rails-card" data-component="RailsCard">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Hot Rails</span>
          <span className="card-sub">always-on · PPM + MTQ</span>
        </div>
        <div className={dotCls}>
          <span className="sh">●</span><span className="lbl">{dotLbl}</span>
        </div>
      </div>
      <div className="rails-body">
        <div className={`vout-cell ${s3}`} data-component="RailCell" data-rail="3V3">
          <div className="top">
            <span className="name">3V3</span>
            <span className="badge">{s3 === 'alarm' ? 'ALM' : 'REG'}</span>
          </div>
          <div className="meta">
            <span className="rail-tag">dev</span>
            <span className="dev">{fmtDevPct(V3V3, NOM_3V3)}</span>
          </div>
          <div className="big"><span data-hk="V3V3">{fmt(V3V3, 3)}</span><span className="u">V</span></div>
          <div className="ip">
            <span data-hk="I3V3">{mAText(I3V3)}</span>
            <span data-hk="P3V3">{fmt(P3V3, 2)} W</span>
          </div>
        </div>
        <div className={`vout-cell ${s5}`} data-component="RailCell" data-rail="5V">
          <div className="top">
            <span className="name">5V</span>
            <span className="badge">{s5 === 'alarm' ? 'ALM' : 'REG'}</span>
          </div>
          <div className="meta">
            <span className="rail-tag">dev</span>
            <span className="dev">{fmtDevPct(V5V0, NOM_5V0)}</span>
          </div>
          <div className="big"><span data-hk="V5V0">{fmt(V5V0, 3)}</span><span className="u">V</span></div>
          <div className="ip">
            <span data-hk="I5V0">{mAText(I5V0)}</span>
            <span data-hk="P5V0">{fmt(P5V0, 2)} W</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export const RailsCard = memo(RailsCardInner)
