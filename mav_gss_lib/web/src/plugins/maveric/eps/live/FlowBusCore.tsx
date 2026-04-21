import { memo } from 'react'
import { fmt } from '../derive'
import type { ChargeDir } from '../types'

interface Props {
  V_BUS: number
  I_BUS: number
  V_SYS: number
  I_BAT: number
  chargeDir: ChargeDir
}

const BUS_LINK_DEADBAND_A = 0.05

function formatIBat(v: number): string {
  if (!Number.isFinite(v)) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(3)} A`
}

function batDirectionLabel(dir: ChargeDir): string {
  if (dir === 'charge') return 'CHG'
  if (dir === 'discharge') return 'DIS'
  return 'IDLE'
}

function FlowBusCoreInner({ V_BUS, I_BUS, V_SYS, I_BAT, chargeDir }: Props) {
  const pBusText = Number.isFinite(V_BUS) && Number.isFinite(I_BUS)
    ? `${(V_BUS * I_BUS).toFixed(2)} W`
    : '—'
  const busFlowing =
    Number.isFinite(I_BUS) && Math.abs(I_BUS) > BUS_LINK_DEADBAND_A
  return (
    <div className="flow-bus-rail" data-component="BusRail">
      <div className="bus-line" aria-hidden="true" />
      <div className="bus-core">
        <div className="bus-side" data-role="bus">
          <span className="label">BUS</span>
          <span className="i"><span data-hk="V_BUS">{fmt(V_BUS, 3)}</span> V</span>
          <span className="sep">·</span>
          <span className="i"><span data-hk="I_BUS">{fmt(I_BUS, 3)} A</span></span>
          <span className="sep">·</span>
          <span className="i"><span data-derived="P_BUS">{pBusText}</span></span>
        </div>
        <div className={`bus-link ${busFlowing ? 'active' : 'idle'}`} data-bus-active={busFlowing}>
          <svg viewBox="0 0 40 12" preserveAspectRatio="none">
            <path className={busFlowing ? 'flow' : ''} d="M0,6 L40,6" />
          </svg>
        </div>
        <div
          className="bus-badge"
          role="img"
          aria-label={`System bus ${fmt(V_SYS, 3)} volts`}
        >
          <span className="label">SYS</span>
          <span className="v" data-hk="V_SYS">{fmt(V_SYS, 3)}</span>
          <span className="u">V</span>
        </div>
        <div className={`bat-link ${chargeDir}`} data-bat-direction={chargeDir}>
          <svg viewBox="0 0 40 12" preserveAspectRatio="none">
            <path className={chargeDir === 'idle' ? '' : 'flow'} d="M0,6 L40,6" />
          </svg>
        </div>
        <div className={`bat ${chargeDir}`} data-bat-state={chargeDir}>
          <span className="label">BAT</span>
          <span className="i">I_BAT <span data-hk="I_BAT">{formatIBat(I_BAT)}</span></span>
          <span className={`state ${chargeDir}`} data-state={chargeDir}>{batDirectionLabel(chargeDir)}</span>
        </div>
      </div>
    </div>
  )
}

export const FlowBusCore = memo(FlowBusCoreInner)
