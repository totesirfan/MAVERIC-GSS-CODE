import { memo } from 'react'
import { DROP_ACTIVE, DROP_IDLE, DROP_VIEWBOX } from './svg'

type DropVariant = 'off' | 'on' | 'rail'

interface Props {
  VOUT1_on: boolean
  VOUT2_on: boolean
  VOUT3_on: boolean
  VOUT4_on: boolean
  VOUT5_on: boolean
  VOUT6_on: boolean
  rail3V3_on: boolean
  rail5V0_on: boolean
}

function Drop({ variant }: { variant: DropVariant }) {
  const cls = `flow-drop up ${variant}`
  const active = variant !== 'off'
  return (
    <div className={cls}>
      <svg viewBox={DROP_VIEWBOX} preserveAspectRatio="none">
        {active
          ? <>
              <path className="flow" d={DROP_ACTIVE.flow} />
              <path className="head" d={DROP_ACTIVE.head} />
            </>
          : <path d={DROP_IDLE.flow} />}
      </svg>
    </div>
  )
}

function vv(on: boolean): DropVariant {
  return on ? 'on' : 'off'
}

function rr(on: boolean): DropVariant {
  return on ? 'rail' : 'off'
}

function FlowLoadDropsInner({
  VOUT1_on, VOUT2_on, VOUT3_on, VOUT4_on, VOUT5_on, VOUT6_on,
  rail3V3_on, rail5V0_on,
}: Props) {
  return (
    <div className="flow-row ld-drops" aria-hidden="true">
      <div className="flow-drop-spacer" />
      <Drop variant={vv(VOUT1_on)} />
      <Drop variant={vv(VOUT2_on)} />
      <Drop variant={vv(VOUT3_on)} />
      <Drop variant={vv(VOUT4_on)} />
      <Drop variant={vv(VOUT5_on)} />
      <Drop variant={vv(VOUT6_on)} />
      <Drop variant={rr(rail3V3_on)} />
      <Drop variant={rr(rail5V0_on)} />
    </div>
  )
}

export const FlowLoadDrops = memo(FlowLoadDropsInner)
