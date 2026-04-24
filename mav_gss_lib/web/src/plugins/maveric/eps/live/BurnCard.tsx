import { memo } from 'react'
import { formatCurrent, fmt } from '../derive'

const VBRN_DANGER = 0.1

type BurnState = 'ok' | 'alarm' | 'latched'

function vbrnState(v: number, latched: boolean): BurnState {
  if (Number.isFinite(v) && v > VBRN_DANGER) return 'alarm'
  if (latched) return 'latched'
  return 'ok'
}

interface Props {
  VBRN1: number; IBRN1: number; PBRN1: number
  VBRN2: number; IBRN2: number; PBRN2: number
  latched: Record<string, number>
  onAcknowledge: (field: string) => void
}

function BurnCell({ id, V, I, P, latched, onAck }: {
  id: 'VBRN1' | 'VBRN2'
  V: number; I: number; P: number
  latched: boolean
  onAck: (field: string) => void
}) {
  const state = vbrnState(V, latched)
  const cls = state === 'alarm' ? 'vout-cell alarm'
    : state === 'latched' ? 'vout-cell alarm'
    : 'vout-cell off'
  const badge = state === 'alarm' ? 'ALARM' : state === 'latched' ? 'LATCH' : 'SAFE'
  return (
    <div className={cls} data-component="BurnCell" data-rail={id}>
      <div className="top">
        <span className="name">{id}</span>
        <span className="badge">{badge}</span>
      </div>
      <div className="meta"><span>Deploy {id.slice(-1)}</span></div>
      <div className="big-v">
        <span data-hk={id}>{fmt(V, 3)}</span>
        <span className="u">V</span>
      </div>
      <div className="ip">
        <span data-hk={id.replace('V', 'I')}>{formatCurrent(I)}</span>
        <span data-hk={id.replace('V', 'P')}>{fmt(P, 2)} W</span>
      </div>
      {state === 'latched' && (
        <button
          type="button"
          className="burn-ack"
          onClick={() => onAck(id)}
          aria-label={`Acknowledge ${id} latch`}
        >
          ACK
        </button>
      )}
    </div>
  )
}

function BurnCardInner(p: Props) {
  const s1 = vbrnState(p.VBRN1, 'VBRN1' in p.latched)
  const s2 = vbrnState(p.VBRN2, 'VBRN2' in p.latched)
  const anyAlm   = s1 === 'alarm' || s2 === 'alarm'
  const anyLatch = s1 === 'latched' || s2 === 'latched'
  const dotCls = anyAlm ? 'dot danger' : anyLatch ? 'dot warn' : 'dot success'
  const dotLbl = anyAlm ? 'FAULT'      : anyLatch ? 'LATCH'    : 'SAFE'

  return (
    <div className="card" data-component="BurnCard">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Deploy Burn</span>
        </div>
        <div className={dotCls}>
          <span className="sh"></span><span className="lbl">{dotLbl}</span>
        </div>
      </div>
      <div className="burn-body">
        <BurnCell id="VBRN1" V={p.VBRN1} I={p.IBRN1} P={p.PBRN1}
                  latched={'VBRN1' in p.latched} onAck={p.onAcknowledge} />
        <BurnCell id="VBRN2" V={p.VBRN2} I={p.IBRN2} P={p.PBRN2}
                  latched={'VBRN2' in p.latched} onAck={p.onAcknowledge} />
      </div>
    </div>
  )
}

export const BurnCard = memo(BurnCardInner)
