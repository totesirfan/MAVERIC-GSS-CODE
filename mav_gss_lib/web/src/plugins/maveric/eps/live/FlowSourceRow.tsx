import { memo } from 'react'
import { fmt } from '../derive'
import type { SourceId } from '../types'

interface PillProps {
  id: SourceId
  label: string
  V: number
  active: boolean
  primary: boolean
  threshold?: number
}

function Pill({ id, label, V, active, primary, threshold = 1.0 }: PillProps) {
  const cls = active
    ? primary
      ? 'flow-pill src active primary'
      : 'flow-pill src active'
    : 'flow-pill src idle'
  const glyph = active ? '●' : '○'
  const digits = id.startsWith('VSIN') ? 2 : 3
  const valueText = Number.isFinite(V) ? `${fmt(V, digits)} V` : '—'
  return (
    <span className={cls} data-source={id} aria-label={`${label} ${valueText}${active ? ' active' : ''}`}>
      <span className="pill-lead">
        <span className="sev" aria-hidden="true">{glyph}</span>
        <span className="id">{label}</span>
      </span>
      <span className="pill-trail">
        <span className="v" data-hk={id}>{valueText}</span>
        {active && <span className="state">{primary ? 'ACTIVE' : 'AUX'}</span>}
      </span>
      {/* threshold hinted in aria-label via active state */}
      <span hidden>{threshold}</span>
    </span>
  )
}

interface Props {
  V_AC2: number
  V_AC1: number
  VSIN1: number
  VSIN2: number
  VSIN3: number
  primary: SourceId | null
}

function isActive(V: number, threshold = 1.0): boolean {
  return Number.isFinite(V) && V > threshold
}

function FlowSourceRowInner({ V_AC2, V_AC1, VSIN1, VSIN2, VSIN3, primary }: Props) {
  return (
    <div className="flow-row src" aria-label="Power sources">
      <div className="flow-label">Sources</div>
      <Pill id="V_AC2" label="AC2" V={V_AC2} active={isActive(V_AC2)} primary={primary === 'V_AC2'} />
      <Pill id="V_AC1" label="AC1" V={V_AC1} active={isActive(V_AC1)} primary={primary === 'V_AC1'} />
      <Pill id="VSIN1" label="VSIN1" V={VSIN1} active={isActive(VSIN1)} primary={primary === 'VSIN1'} />
      <Pill id="VSIN2" label="VSIN2" V={VSIN2} active={isActive(VSIN2)} primary={primary === 'VSIN2'} />
      <Pill id="VSIN3" label="VSIN3" V={VSIN3} active={isActive(VSIN3)} primary={primary === 'VSIN3'} />
    </div>
  )
}

export const FlowSourceRow = memo(FlowSourceRowInner)
