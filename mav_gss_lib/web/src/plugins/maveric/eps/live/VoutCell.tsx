import { memo } from 'react'
import { fmt } from '../derive'

interface Props {
  index: number
  V: number
  I: number
  P: number
  subsystem: string
}

function railTag(index: number): string {
  return index <= 3 ? '3V3' : '5V'
}

function VoutCellInner({ index, V, I, P, subsystem }: Props) {
  const on = Number.isFinite(V) && V > 0.5
  const state = on ? 'on' : 'off'
  const mA = Number.isFinite(I) ? Math.round(I * 1000) : null
  return (
    <div className={`vout-cell ${state}`} data-component="VoutCell" data-vout={index}>
      <div className="top">
        <span className="name">VOUT{index}</span>
        <span className="badge">{on ? 'ON' : 'OFF'}</span>
      </div>
      <div className="meta">
        <span className="rail-tag">{railTag(index)}</span>
        <span>{subsystem || 'unmapped'}</span>
      </div>
      <div className="big" data-hk={`VOUT${index}`}>{fmt(V, 3)}<span className="u">V</span></div>
      <div className="ip">
        <span data-hk={`IOUT${index}`}>{mA === null ? '—' : `${mA} mA`}</span>
        <span data-hk={`POUT${index}`}>{fmt(P, 2)} W</span>
      </div>
    </div>
  )
}

export const VoutCell = memo(VoutCellInner)
