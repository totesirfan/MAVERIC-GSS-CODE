import { memo } from 'react'
import { fmt } from '../derive'

type LoadKind = 'vout' | 'rail'

interface PillProps {
  id: string
  label: string
  P: number
  on: boolean
  kind: LoadKind
}

function Pill({ id, label, P, on, kind }: PillProps) {
  const cls = kind === 'rail'
    ? 'flow-pill ld rail'
    : on ? 'flow-pill ld on' : 'flow-pill ld off'
  const glyphCls = kind === 'rail' ? 'sev sq' : 'sev'
  const glyph = kind === 'rail' ? '■' : on ? '●' : '○'
  return (
    <span className={cls} data-load={id}>
      <span className="pill-lead">
        <span className={glyphCls} aria-hidden="true">{glyph}</span>
        <span className="id">{label}</span>
      </span>
      <span className="pill-trail">
        <span className="v" data-hk={id}>{Number.isFinite(P) ? `${fmt(P, 2)} W` : '—'}</span>
      </span>
    </span>
  )
}

interface Props {
  POUT1: number
  POUT2: number
  POUT3: number
  POUT4: number
  POUT5: number
  POUT6: number
  VOUT1: number
  VOUT2: number
  VOUT3: number
  VOUT4: number
  VOUT5: number
  VOUT6: number
  P3V3: number
  P5V0: number
}

function isOn(V: number): boolean {
  return Number.isFinite(V) && V > 0.5
}

function FlowLoadRowInner(p: Props) {
  return (
    <div className="flow-row ld" aria-label="Bus loads">
      <div className="flow-label">Loads</div>
      <Pill id="POUT1" label="VOUT1" P={p.POUT1} on={isOn(p.VOUT1)} kind="vout" />
      <Pill id="POUT2" label="VOUT2" P={p.POUT2} on={isOn(p.VOUT2)} kind="vout" />
      <Pill id="POUT3" label="VOUT3" P={p.POUT3} on={isOn(p.VOUT3)} kind="vout" />
      <Pill id="POUT4" label="VOUT4" P={p.POUT4} on={isOn(p.VOUT4)} kind="vout" />
      <Pill id="POUT5" label="VOUT5" P={p.POUT5} on={isOn(p.VOUT5)} kind="vout" />
      <Pill id="POUT6" label="VOUT6" P={p.POUT6} on={isOn(p.VOUT6)} kind="vout" />
      <Pill id="P3V3"  label="3V3"   P={p.P3V3}  on={true}         kind="rail" />
      <Pill id="P5V0"  label="5V"    P={p.P5V0}  on={true}         kind="rail" />
    </div>
  )
}

export const FlowLoadRow = memo(FlowLoadRowInner)
