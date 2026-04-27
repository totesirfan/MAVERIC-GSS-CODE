import { memo, useEffect, useMemo, useState } from 'react'
import { fmt } from './derive'
import { FIELD_DEFS, GROUP_DEFS, type EpsFieldMap, type GroupId } from './types'
import {
  ageMs, formatAge, staleLevel, STALE_OPACITY, NO_DATA_OPACITY,
} from '../staleness'

interface Props {
  fields: EpsFieldMap
  field_t: EpsFieldMap
}

function FieldsPaneInner({ fields, field_t }: Props) {
  const [filter, setFilter] = useState<GroupId>('all')

  // Tick once a second so the Age column ticks up without a domain-state
  // update. Aligns with FooterMeta / GNC FieldDisplay.
  const [nowMs, setNowMs] = useState<number>(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const hasAny = Object.keys(fields).length > 0

  const rows = useMemo(() => {
    return FIELD_DEFS
      .filter((d) => filter === 'all' || d.group === filter)
      .map((d) => {
        const raw = fields[d.name]
        const value = typeof raw === 'number' ? raw : NaN
        const isZero = Number.isFinite(value) && Math.abs(value) < 0.01
        const valText = fmt(value, d.digits)
        const t = field_t[d.name]
        const age = typeof t === 'number' ? ageMs(t, nowMs) : null
        const hasField = typeof t === 'number'
        const level = hasField ? staleLevel(age) : 'critical'
        const opacity = hasField ? STALE_OPACITY[level] : NO_DATA_OPACITY
        const ageText = hasField ? formatAge(age) : '—'
        return { def: d, isZero, valText, desc: d.subsystem || '',
                 age, ageText, opacity, level }
      })
  }, [fields, field_t, filter, nowMs])

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Housekeeping Fields</span>
          <span className="card-sub">eps domain · 48 · per-field ages</span>
        </div>
        <span className="card-sub" style={{ color: 'var(--text-disabled)' }}>
          {hasAny ? 'live' : 'no data'}
        </span>
      </div>
      <div className="field-toolbar">
        <span id="filter-legend" style={{ color: 'var(--text-disabled)' }}>FILTER</span>
        <div className="filter-group" role="group" aria-labelledby="filter-legend">
          {GROUP_DEFS.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`pill ${filter === g.id ? 'active' : ''}`}
              data-filter={g.id}
              aria-pressed={filter === g.id}
              onClick={() => setFilter(g.id)}
            >
              {g.label}
            </button>
          ))}
        </div>
        <span className="right" aria-live="polite">{rows.length} / 48 fields</span>
      </div>
      <div className="field-table-scroll">
        <table className="field-table">
          <thead>
            <tr>
              <th>Field</th>
              <th className="v">Value</th>
              <th className="u">Unit</th>
              <th>Age</th>
              <th>Group</th>
              <th>Subsystem</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ def, isZero, valText, desc, ageText, opacity, level }) => (
              <tr key={def.name}
                  className={isZero ? 'zero' : undefined}
                  style={{ opacity }}>
                <td className="name" data-hk={def.name}>{def.name}</td>
                <td className="v">{valText}</td>
                <td className="u">{def.unit}</td>
                <td data-stale={level}>{ageText}</td>
                <td>
                  <span className={`group ${def.group}`}>{def.group}</span>
                </td>
                <td>
                  <span className={desc ? 'subsys' : 'subsys tbd'}>{desc || 'unmapped'}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export const FieldsPane = memo(FieldsPaneInner)
