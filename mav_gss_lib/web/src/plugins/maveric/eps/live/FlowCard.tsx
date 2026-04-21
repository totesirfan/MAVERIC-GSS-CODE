import { memo, useMemo } from 'react'
import { FlowSourceRow } from './FlowSourceRow'
import { FlowSourceDrops } from './FlowSourceDrops'
import { FlowBusCore } from './FlowBusCore'
import { FlowLoadDrops } from './FlowLoadDrops'
import { FlowLoadRow } from './FlowLoadRow'
import { FlowBalance } from './FlowBalance'
import type { ChargeDir, EpsFields, SourceId } from '../types'

interface Props {
  fields: EpsFields | null
  chargeDir: ChargeDir
  efficiency: number | null
  activeSource: SourceId | null
}

function finite(v: number | undefined): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : NaN
}

function FlowCardInner({ fields, chargeDir, efficiency, activeSource }: Props) {
  // Primitives sliced from fields with useMemo — only recompute when fields identity changes.
  const src = useMemo(() => ({
    V_AC1: finite(fields?.V_AC1),
    V_AC2: finite(fields?.V_AC2),
    VSIN1: finite(fields?.VSIN1),
    VSIN2: finite(fields?.VSIN2),
    VSIN3: finite(fields?.VSIN3),
  }), [fields])

  const hub = useMemo(() => ({
    V_BUS: finite(fields?.V_BUS),
    I_BUS: finite(fields?.I_BUS),
    I_BAT: finite(fields?.I_BAT),
  }), [fields])

  const load = useMemo(() => ({
    VOUT1: finite(fields?.VOUT1), POUT1: finite(fields?.POUT1),
    VOUT2: finite(fields?.VOUT2), POUT2: finite(fields?.POUT2),
    VOUT3: finite(fields?.VOUT3), POUT3: finite(fields?.POUT3),
    VOUT4: finite(fields?.VOUT4), POUT4: finite(fields?.POUT4),
    VOUT5: finite(fields?.VOUT5), POUT5: finite(fields?.POUT5),
    VOUT6: finite(fields?.VOUT6), POUT6: finite(fields?.POUT6),
    P3V3:  finite(fields?.P3V3),
    P5V0:  finite(fields?.P5V0),
  }), [fields])

  const pBus = Number.isFinite(hub.V_BUS) && Number.isFinite(hub.I_BUS) ? hub.V_BUS * hub.I_BUS : NaN
  const pIn = useMemo(() => {
    const parts: number[] = []
    const addIfFinite = (v: number) => { if (Number.isFinite(v)) parts.push(v) }
    addIfFinite(finite(fields?.PSIN1))
    addIfFinite(finite(fields?.PSIN2))
    addIfFinite(finite(fields?.PSIN3))
    const vbat = finite(fields?.V_BAT)
    const ibat = finite(fields?.I_BAT)
    if (Number.isFinite(vbat) && Number.isFinite(ibat) && ibat < 0) parts.push(vbat * -ibat)
    if (parts.length === 0) return NaN
    return parts.reduce((a, b) => a + b, 0)
  }, [fields])

  const pOut = pBus
  const effPct = efficiency !== null && Number.isFinite(efficiency)
    ? `${Math.round(efficiency * 100)}`
    : '—'

  return (
    <div className="card flow-card" data-component="FlowCard">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Power Flow</span>
          <span className="card-sub">sources → bus → loads</span>
        </div>
        <span className="card-sub flow-eff">
          <span className="k">P_in</span>
          <span className="v"><span data-derived="P_IN">{Number.isFinite(pIn) ? pIn.toFixed(2) : '—'}</span> W</span>
          <span className="sep">·</span>
          <span className="k">P_out</span>
          <span className="v"><span data-derived="P_OUT">{Number.isFinite(pOut) ? pOut.toFixed(2) : '—'}</span> W</span>
          <span className="sep">·</span>
          <span className="k">η</span>
          <span className={efficiency !== null ? 'v success' : 'v'}>
            <span data-derived="EFFICIENCY">{effPct}</span>%
          </span>
        </span>
      </div>
      <div className="flow-body" title="Power flow">
        <FlowSourceRow
          V_AC2={src.V_AC2} V_AC1={src.V_AC1}
          VSIN1={src.VSIN1} VSIN2={src.VSIN2} VSIN3={src.VSIN3}
          primary={activeSource}
        />
        <FlowSourceDrops
          AC2_active={Number.isFinite(src.V_AC2) && src.V_AC2 > 1.0}
          AC1_active={Number.isFinite(src.V_AC1) && src.V_AC1 > 1.0}
          VSIN1_active={Number.isFinite(src.VSIN1) && src.VSIN1 > 1.0}
          VSIN2_active={Number.isFinite(src.VSIN2) && src.VSIN2 > 1.0}
          VSIN3_active={Number.isFinite(src.VSIN3) && src.VSIN3 > 1.0}
        />
        <FlowBusCore
          V_BUS={hub.V_BUS} I_BUS={hub.I_BUS} I_BAT={hub.I_BAT} chargeDir={chargeDir}
        />
        <FlowLoadDrops
          VOUT1_on={Number.isFinite(load.VOUT1) && load.VOUT1 > 0.5}
          VOUT2_on={Number.isFinite(load.VOUT2) && load.VOUT2 > 0.5}
          VOUT3_on={Number.isFinite(load.VOUT3) && load.VOUT3 > 0.5}
          VOUT4_on={Number.isFinite(load.VOUT4) && load.VOUT4 > 0.5}
          VOUT5_on={Number.isFinite(load.VOUT5) && load.VOUT5 > 0.5}
          VOUT6_on={Number.isFinite(load.VOUT6) && load.VOUT6 > 0.5}
          rail3V3_on={Number.isFinite(load.P3V3) && load.P3V3 > 0.01}
          rail5V0_on={Number.isFinite(load.P5V0) && load.P5V0 > 0.01}
        />
        <FlowLoadRow
          POUT1={load.POUT1} POUT2={load.POUT2} POUT3={load.POUT3}
          POUT4={load.POUT4} POUT5={load.POUT5} POUT6={load.POUT6}
          VOUT1={load.VOUT1} VOUT2={load.VOUT2} VOUT3={load.VOUT3}
          VOUT4={load.VOUT4} VOUT5={load.VOUT5} VOUT6={load.VOUT6}
          P3V3={load.P3V3}   P5V0={load.P5V0}
        />
        <FlowBalance pIn={pIn} pOut={pOut} />
      </div>
    </div>
  )
}

export const FlowCard = memo(FlowCardInner)
