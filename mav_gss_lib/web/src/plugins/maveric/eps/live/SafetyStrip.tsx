import { memo } from 'react'
import { fmt } from '../derive'

const VBRN_DANGER = 0.1
const VSIN_ACTIVE = 0.5

interface Props {
  VBRN1: number
  VBRN2: number
  VSIN1: number
  VSIN2: number
  VSIN3: number
  latched: Record<string, number>
  onAcknowledge: (field: string) => void
}

function vbrnState(v: number, latched: boolean): 'ok' | 'alarm' | 'latched' {
  if (Number.isFinite(v) && v > VBRN_DANGER) return 'alarm'
  if (latched) return 'latched'
  return 'ok'
}

function BurnItem({ id, v, latched, onAck }: {
  id: 'VBRN1' | 'VBRN2'
  v: number
  latched: boolean
  onAck: (field: string) => void
}) {
  const state = vbrnState(v, latched)
  const cls = `s-item ${state}`
  const statusWord = state === 'alarm' ? 'ALARM' : state === 'latched' ? 'LATCHED' : 'OK'
  return (
    <span className={cls}>
      <span className="sev" aria-hidden="true" />
      <span className="id">{id}</span>
      <span className="v" data-hk={id}>{fmt(v, 3)} V</span>
      <span className="status-word">{statusWord}</span>
      {state === 'latched' && (
        <button
          type="button"
          className="ack-btn"
          onClick={() => onAck(id)}
          aria-label={`Acknowledge ${id} latch`}
          style={{
            marginLeft: 4, fontSize: 10, padding: '1px 6px',
            background: 'transparent', color: 'var(--state-warning)',
            border: '1px solid var(--state-warning)', borderRadius: 3, cursor: 'pointer',
          }}
        >
          ACK
        </button>
      )}
    </span>
  )
}

function SolarItem({ id, v }: { id: 'VSIN1' | 'VSIN2' | 'VSIN3'; v: number }) {
  return (
    <span className="s-item">
      <span className="sev" aria-hidden="true" />
      <span className="id">{id}</span>
      <span className="v" data-hk={id}>{fmt(v, 2)} V</span>
    </span>
  )
}

function SafetyStripInner({ VBRN1, VBRN2, VSIN1, VSIN2, VSIN3, latched, onAcknowledge }: Props) {
  const brn1_latched = 'VBRN1' in latched
  const brn2_latched = 'VBRN2' in latched
  const anyAlarm =
    (Number.isFinite(VBRN1) && VBRN1 > VBRN_DANGER) ||
    (Number.isFinite(VBRN2) && VBRN2 > VBRN_DANGER) ||
    brn1_latched || brn2_latched
  const deployState = anyAlarm ? 'alarm' : 'ok'
  const deployLabel = anyAlarm ? '● FAULT' : '● SAFE'
  const activeSolar = [VSIN1, VSIN2, VSIN3].filter((v) => Number.isFinite(v) && v >= VSIN_ACTIVE).length
  const solarStateCls = activeSolar > 0 ? 'success' : 'idle'
  const solarLabel = activeSolar > 0 ? `${activeSolar} active` : '0 active'
  return (
    <div
      className={`safety-strip ${anyAlarm ? 'has-alarm' : ''}`}
      data-component="SafetyStrip"
      aria-live="assertive"
      title="Deployment burn lines and solar panel inputs"
    >
      <div className="s-group">
        <span className="s-label">Deploy</span>
        <BurnItem id="VBRN1" v={VBRN1} latched={brn1_latched} onAck={onAcknowledge} />
        <BurnItem id="VBRN2" v={VBRN2} latched={brn2_latched} onAck={onAcknowledge} />
        <span className={`s-state ${deployState}`}>{deployLabel}</span>
      </div>
      <span className="s-divider" aria-hidden="true">|</span>
      <div className="s-group">
        <span className="s-label">Solar</span>
        <SolarItem id="VSIN1" v={VSIN1} />
        <SolarItem id="VSIN2" v={VSIN2} />
        <SolarItem id="VSIN3" v={VSIN3} />
        <span className={`s-state ${solarStateCls}`}>{solarLabel}</span>
      </div>
    </div>
  )
}

export const SafetyStrip = memo(SafetyStripInner)
