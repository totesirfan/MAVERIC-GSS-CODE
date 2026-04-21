/**
 * EpsPage skeleton — the ONLY consumer of useEps() in the EPS tree.
 *
 * Why the single-consumer rule matters:
 *   `useEps()` returns one context value containing current, prev,
 *   chargeDir, latched, receivedThisLink, etc. React context
 *   rerenders EVERY consumer when any field of that value changes.
 *   If all 15 EPS components called useEps() directly, every packet
 *   would rerender the whole page — React.memo on the children would
 *   not help, because context updates bypass memo.
 *
 *   So EpsPage is the only component that calls useEps(). It
 *   destructures the needed slices, pulls pure-primitive props from
 *   `current.fields` / `prev.fields`, and passes them to each memo'd
 *   child. Default React.memo shallow compare then genuinely prevents
 *   a V_BUS change from rerendering the battery card, because
 *   HeroCardBat's props (V_BAT, I_BAT, prev_V_BAT, chargeDir, alarm)
 *   are identical between renders when V_BAT etc. are unchanged.
 *
 * Copy to `mav_gss_lib/web/src/plugins/maveric/eps/EpsPage.tsx` and
 * fill in the remaining component wiring. Do NOT push `useEps()`
 * calls into any of the child components.
 */
import { useMemo, useState } from 'react'
import './styles.css'
import { useEps } from './EpsProvider'
import { alarmState, activeSource, efficiency, socFromVbat, thermalEta } from './derive'
import type { AlarmLevel } from './types'

// Live-pane children (all React.memo'd internally on narrow primitive props).
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

export default function EpsPage() {
  const [tab, setTab] = useState<Subtab>(readSubtabFromUrl)

  // ── Single useEps() call for the whole EPS tree ──
  const { current, prev, chargeDir, latched, receivedThisLink, acknowledgeLatch, clearSnapshot } = useEps()

  // Stable primitive props. All children receive these; none call
  // useEps() themselves. useMemo ensures alarmState/activeSource etc.
  // are only recomputed when `current` changes identity (i.e. a new
  // packet landed), not on every render.
  const fields     = current?.fields ?? null
  const prevFields = prev?.fields ?? null
  const alarms     = useMemo(() => fields ? alarmState(fields) : {},     [fields])
  const source     = useMemo(() => fields ? activeSource(fields) : null, [fields])
  const eff        = useMemo(() => fields ? efficiency(fields, source)  : null, [fields, source])
  const soc        = useMemo(() => fields ? socFromVbat(fields.V_BAT)   : null, [fields])
  const eta        = useMemo(() => {
    if (!fields || !prevFields || !current || !prev) return null
    const dt = current.received_at_ms - prev.received_at_ms
    return thermalEta(fields.T_DIE, prevFields.T_DIE, dt, 60)
  }, [fields, prevFields, current, prev])

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
        <span className="subtab-meta">pkts this link: {receivedThisLink}</span>
      </nav>

      <div className="body">
        <section id="pane-live" className={`pane ${tab === 'live' ? 'active' : ''}`}>
          <div className="hero-row">
            <HeroCardBus
              V_BUS={fields?.V_BUS ?? NaN}
              I_BUS={fields?.I_BUS ?? NaN}
              prev_V_BUS={prevFields?.V_BUS ?? NaN}
              alarm={alarms.V_BUS as AlarmLevel ?? 'unknown'}
            />
            <HeroCardBat
              V_BAT={fields?.V_BAT ?? NaN}
              I_BAT={fields?.I_BAT ?? NaN}
              prev_V_BAT={prevFields?.V_BAT ?? NaN}
              chargeDir={chargeDir}
              soc={soc}
              alarm={alarms.V_BAT as AlarmLevel ?? 'unknown'}
            />
            <HeroCardSys
              V_SYS={fields?.V_SYS ?? NaN}
              prev_V_SYS={prevFields?.V_SYS ?? NaN}
              alarm={alarms.V_SYS as AlarmLevel ?? 'unknown'}
            />
            <HeroCardThermal
              T_DIE={fields?.T_DIE ?? NaN}
              TS_ADC={fields?.TS_ADC ?? NaN}
              prev_T_DIE={prevFields?.T_DIE ?? NaN}
              etaSeconds={eta}
              alarm={alarms.T_DIE as AlarmLevel ?? 'unknown'}
            />
          </div>

          <div className="vout-rails-row">
            {/* VoutStrip + RailsCard each take only the fields they render. */}
            <VoutStrip fields={fields} />
            <RailsCard
              V3V3={fields?.V3V3 ?? NaN} I3V3={fields?.I3V3 ?? NaN} P3V3={fields?.P3V3 ?? NaN}
              V5V0={fields?.V5V0 ?? NaN} I5V0={fields?.I5V0 ?? NaN} P5V0={fields?.P5V0 ?? NaN}
            />
          </div>

          <FlowCard fields={fields} chargeDir={chargeDir} efficiency={eff} activeSource={source} />

          <div className="safety-foot-row">
            <SafetyStrip
              VBRN1={fields?.VBRN1 ?? NaN} VBRN2={fields?.VBRN2 ?? NaN}
              VSIN1={fields?.VSIN1 ?? NaN} VSIN2={fields?.VSIN2 ?? NaN} VSIN3={fields?.VSIN3 ?? NaN}
              latched={latched}
              onAcknowledge={acknowledgeLatch}
            />
            <FooterMeta
              pktNum={current?.pkt_num ?? null}
              receivedAtMs={current?.received_at_ms ?? null}
              onClearSnapshot={clearSnapshot}
            />
          </div>
        </section>

        <section id="pane-fields" className={`pane ${tab === 'fields' ? 'active' : ''}`}>
          <FieldsPane fields={fields} />
        </section>
      </div>
    </div>
  )
}
