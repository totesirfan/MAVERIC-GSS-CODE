import { memo } from 'react'
import { DROP_ACTIVE, DROP_IDLE, DROP_VIEWBOX } from './svg'

interface Props {
  AC2_active: boolean
  AC1_active: boolean
  VSIN1_active: boolean
  VSIN2_active: boolean
  VSIN3_active: boolean
}

function Drop({ active }: { active: boolean }) {
  return (
    <div className={`flow-drop down ${active ? 'active' : 'idle'}`}>
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

function FlowSourceDropsInner({ AC2_active, AC1_active, VSIN1_active, VSIN2_active, VSIN3_active }: Props) {
  return (
    <div className="flow-row src-drops" aria-hidden="true">
      <div className="flow-drop-spacer" />
      <Drop active={AC2_active} />
      <Drop active={AC1_active} />
      <Drop active={VSIN1_active} />
      <Drop active={VSIN2_active} />
      <Drop active={VSIN3_active} />
    </div>
  )
}

export const FlowSourceDrops = memo(FlowSourceDropsInner)
