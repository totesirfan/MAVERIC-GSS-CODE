import { memo } from 'react'
import { clamp } from '../derive'

interface Props {
  pIn: number
  pOut: number
}

function FlowBalanceInner({ pIn, pOut }: Props) {
  const pInOk = Number.isFinite(pIn) && pIn > 0
  const pOutOk = Number.isFinite(pOut) && pOut >= 0
  const outPct = pInOk && pOutOk ? clamp((pOut / pIn) * 100, 0, 100) : 0
  const lossPct = pInOk && pOutOk ? clamp(100 - outPct, 0, 100) : 0
  const aria = pInOk && pOutOk
    ? `Delivered ${pOut.toFixed(2)} watts, losses ${Math.max(0, pIn - pOut).toFixed(2)} watts, of ${pIn.toFixed(2)} watts input`
    : 'Power balance unknown'
  return (
    <div className="flow-balance" data-component="FlowBalance">
      <span className="k">balance</span>
      <div className="bar" role="img" aria-label={aria}>
        <div className="fill-out"  style={{ width: `${outPct}%` }} />
        <div className="fill-loss" style={{ left: `${outPct}%`, width: `${lossPct}%` }} />
      </div>
      <span className="legend">
        <span className="lg out">● delivered</span>
        <span className="lg loss">■ losses</span>
      </span>
    </div>
  )
}

export const FlowBalance = memo(FlowBalanceInner)
