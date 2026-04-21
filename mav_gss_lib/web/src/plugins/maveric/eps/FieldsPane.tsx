import { memo, useMemo, useState } from 'react'
import { fmt } from './derive'
import { FIELD_DEFS, GROUP_DEFS, type EpsFields, type GroupId } from './types'

interface Props {
  fields: EpsFields | null
}

function FieldsPaneInner({ fields }: Props) {
  const [filter, setFilter] = useState<GroupId>('all')

  const rows = useMemo(() => {
    return FIELD_DEFS
      .filter((d) => filter === 'all' || d.group === filter)
      .map((d) => {
        const raw = fields ? fields[d.name] : NaN
        const isZero = Number.isFinite(raw) && Math.abs(raw) < 0.01
        const valText = fmt(raw, d.digits)
        const desc = d.subsystem || ''
        return { def: d, raw, isZero, valText, desc }
      })
  }, [fields, filter])

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-head-left">
          <span className="card-title">Housekeeping Fields</span>
          <span className="card-sub">eps_hk · 48 · 96 B int16 LE</span>
        </div>
        <span className="card-sub" style={{ color: 'var(--text-disabled)' }}>
          {fields ? 'live snapshot' : 'no snapshot'}
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
              <th>Group</th>
              <th>Subsystem</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ def, isZero, valText, desc }) => (
              <tr key={def.name} className={isZero ? 'zero' : undefined}>
                <td className="name" data-hk={def.name}>{def.name}</td>
                <td className="v">{valText}</td>
                <td className="u">{def.unit}</td>
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
