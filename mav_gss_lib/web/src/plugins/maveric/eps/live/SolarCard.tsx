import { memo } from 'react'
import { classifySolarPanel, formatCurrent, fmt, type SolarPanelState } from '../derive'
import type { EpsFieldMap, EpsFieldName } from '../types'

interface Props {
  fields: EpsFieldMap
}

function pick(fields: EpsFieldMap, k: EpsFieldName): number {
  const v = fields[k]
  return typeof v === 'number' ? v : NaN
}

function badgeForState(s: SolarPanelState): string {
  if (s === 'gen')  return 'GEN'
  if (s === 'dead') return 'DEAD'
  return 'IDLE'
}

function SolarRow({ index, V, I, P, state }: {
  index: 1 | 2 | 3; V: number; I: number; P: number; state: SolarPanelState;
}) {
  return (
    <div className={`solar-row ${state}`} data-component="SolarRow" data-panel={index}>
      <span className="s-name">VSIN{index}</span>
      <span className="s-badge">{badgeForState(state)}</span>
      <span className="s-v" data-hk={`VSIN${index}`}>{Number.isFinite(V) ? `${V.toFixed(2)} V` : '— V'}</span>
      <span className="s-i" data-hk={`ISIN${index}`}>{formatCurrent(I)}</span>
      <span className="s-p" data-hk={`PSIN${index}`}>{fmt(P, 2)} W</span>
    </div>
  )
}

function SolarCardInner({ fields }: Props) {
  const states: SolarPanelState[] = ([1, 2, 3] as const).map((n) =>
    classifySolarPanel(fields, n),
  )
  const genCount  = states.filter((s) => s === 'gen').length
  const deadCount = states.filter((s) => s === 'dead').length
  const dotCls = deadCount > 0 ? 'dot danger'
    : genCount  > 0 ? 'dot success'
    : 'dot neutral'
  const dotLbl = deadCount > 0 ? `FAULT ${genCount} / 3`
    : `${genCount} / 3`

  return (
    <div className="card" data-component="SolarCard">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Solar</span>
          <span className="card-sub">VSIN1 · VSIN2 · VSIN3</span>
        </div>
        <div className={dotCls}>
          <span className="sh"></span><span className="lbl">{dotLbl}</span>
        </div>
      </div>
      <div className="solar-body">
        {([1, 2, 3] as const).map((n) => (
          <SolarRow
            key={n}
            index={n}
            V={pick(fields, `VSIN${n}` as EpsFieldName)}
            I={pick(fields, `ISIN${n}` as EpsFieldName)}
            P={pick(fields, `PSIN${n}` as EpsFieldName)}
            state={states[n - 1]}
          />
        ))}
      </div>
    </div>
  )
}

export const SolarCard = memo(SolarCardInner)
