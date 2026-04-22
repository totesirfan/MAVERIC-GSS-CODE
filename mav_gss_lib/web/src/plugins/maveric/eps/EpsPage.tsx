/**
 * EpsPage — the ONLY consumer of useEps() in the EPS tree.
 *
 * Single-consumer rule: useEps() returns one context value. Context
 * rerenders every consumer on any change. EpsPage destructures what
 * it needs and hands primitive props to the memo'd children so they
 * only rerender when their specific fields change.
 */
import { useMemo, useState } from 'react'
import './styles.css'
import { useEps } from './EpsProvider'
import { alarmState, activeSource, efficiency, socFromVbat, thermalEta } from './derive'
import type { AlarmLevel, EpsFieldName } from './types'

import { HeroCardBus }       from './live/HeroCardBus'
import { HeroCardBat }       from './live/HeroCardBat'
import { HeroCardSys }       from './live/HeroCardSys'
import { HeroCardThermal }   from './live/HeroCardThermal'
import { FlowCard }          from './live/FlowCard'
import { VoutStrip }         from './live/VoutStrip'
import { RailsCard }         from './live/RailsCard'
import { SafetyStrip }       from './live/SafetyStrip'
import { FooterMeta }        from './live/FooterMeta'
import { FieldsPane }        from './FieldsPane'

type Subtab = 'live' | 'fields'

function readSubtabFromUrl(): Subtab {
  const params = new URLSearchParams(window.location.search)
  return params.get('tab') === 'fields' ? 'fields' : 'live'
}

/** Pick a numeric field with NaN fallback — every hero card expects a
 *  number prop and renders "—" internally on NaN. Kept inline here so
 *  consumers stay primitive-prop. */
function pick(fields: Partial<Record<EpsFieldName, number>>, k: EpsFieldName): number {
  const v = fields[k]
  return typeof v === 'number' ? v : NaN
}

export default function EpsPage() {
  const [tab, setTab] = useState<Subtab>(readSubtabFromUrl)

  const {
    fields, field_t, prev_fields, prev_field_t,
    chargeDir, latched, receivedThisLink, acknowledgeLatch,
  } = useEps()

  const hasAny = Object.keys(fields).length > 0

  // Derived state. Every memo recomputes only when its inputs' identity
  // changes, which happens once per rotation batch.
  const alarms = useMemo(() => hasAny ? alarmState(fields) : {}, [fields, hasAny])
  const source = useMemo(() => hasAny ? activeSource(fields) : null, [fields, hasAny])
  const eff    = useMemo(() => hasAny ? efficiency(fields, source) : null, [fields, source, hasAny])
  const soc    = useMemo(() => {
    const v = fields.V_BAT
    return typeof v === 'number' ? socFromVbat(v) : null
  }, [fields])
  const eta    = useMemo(() => {
    const tCur  = field_t.T_DIE
    const tPrev = prev_field_t.T_DIE
    if (tCur === undefined || tPrev === undefined) return null
    const td    = fields.T_DIE
    const tdPrev = prev_fields.T_DIE
    if (typeof td !== 'number' || typeof tdPrev !== 'number') return null
    return thermalEta(td, tdPrev, tCur - tPrev, 60)
  }, [fields.T_DIE, prev_fields.T_DIE, field_t.T_DIE, prev_field_t.T_DIE])

  // Footer uses the newest + oldest per-field age so "is anything live"
  // and "is anything going stale" are both visible.
  const { newestT, oldestT } = useMemo(() => {
    let newest = -Infinity
    let oldest = Infinity
    for (const t of Object.values(field_t)) {
      if (typeof t !== 'number') continue
      if (t > newest) newest = t
      if (t < oldest) oldest = t
    }
    return {
      newestT: Number.isFinite(newest) ? newest : null,
      oldestT: Number.isFinite(oldest) ? oldest : null,
    }
  }, [field_t])

  const onTabChange = (next: Subtab) => {
    setTab(next)
    const url = new URL(window.location.href)
    if (next === 'live') url.searchParams.delete('tab')
    else url.searchParams.set('tab', next)
    window.history.replaceState({}, '', url.toString())
  }

  return (
    <div className="eps-page">
      <nav className="subtabs" role="tablist">
        <button role="tab" aria-selected={tab === 'live'}
                className={`subtab ${tab === 'live' ? 'active' : ''}`}
                onClick={() => onTabChange('live')}>
          Housekeeping
        </button>
        <button role="tab" aria-selected={tab === 'fields'}
                className={`subtab ${tab === 'fields' ? 'active' : ''}`}
                onClick={() => onTabChange('fields')}>
          Fields
        </button>
        <div className="subtab-spacer" />
        <span className="subtab-meta">updates this link: {receivedThisLink}</span>
      </nav>

      <div className="body">
        <section id="pane-live" className={`pane ${tab === 'live' ? 'active' : ''}`}>
          <div className="hero-row">
            <HeroCardBus
              V_BUS={pick(fields, 'V_BUS')}
              I_BUS={pick(fields, 'I_BUS')}
              prev_V_BUS={pick(prev_fields, 'V_BUS')}
              alarm={alarms.V_BUS as AlarmLevel ?? 'unknown'}
            />
            <HeroCardBat
              V_BAT={pick(fields, 'V_BAT')}
              I_BAT={pick(fields, 'I_BAT')}
              prev_V_BAT={pick(prev_fields, 'V_BAT')}
              chargeDir={chargeDir}
              soc={soc}
              alarm={alarms.V_BAT as AlarmLevel ?? 'unknown'}
            />
            <HeroCardSys
              V_SYS={pick(fields, 'V_SYS')}
              prev_V_SYS={pick(prev_fields, 'V_SYS')}
              alarm={alarms.V_SYS as AlarmLevel ?? 'unknown'}
            />
            <HeroCardThermal
              T_DIE={pick(fields, 'T_DIE')}
              TS_ADC={pick(fields, 'TS_ADC')}
              prev_T_DIE={pick(prev_fields, 'T_DIE')}
              etaSeconds={eta}
              alarm={alarms.T_DIE as AlarmLevel ?? 'unknown'}
            />
          </div>

          <div className="vout-rails-row">
            <VoutStrip fields={fields} />
            <RailsCard
              V3V3={pick(fields, 'V3V3')} I3V3={pick(fields, 'I3V3')} P3V3={pick(fields, 'P3V3')}
              V5V0={pick(fields, 'V5V0')} I5V0={pick(fields, 'I5V0')} P5V0={pick(fields, 'P5V0')}
            />
          </div>

          <FlowCard fields={fields} chargeDir={chargeDir} efficiency={eff} activeSource={source} />

          <div className="safety-foot-row">
            <SafetyStrip
              VBRN1={pick(fields, 'VBRN1')} VBRN2={pick(fields, 'VBRN2')}
              VSIN1={pick(fields, 'VSIN1')} VSIN2={pick(fields, 'VSIN2')} VSIN3={pick(fields, 'VSIN3')}
              latched={latched}
              onAcknowledge={acknowledgeLatch}
            />
            <FooterMeta
              pktNum={null}
              newestT={newestT}
              oldestT={oldestT}
            />
          </div>
        </section>

        <section id="pane-fields" className={`pane ${tab === 'fields' ? 'active' : ''}`}>
          <FieldsPane fields={fields} field_t={field_t} />
        </section>
      </div>
    </div>
  )
}
