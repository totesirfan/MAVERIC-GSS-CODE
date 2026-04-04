import { useState, useEffect, useMemo } from 'react'
import { colors } from '@/lib/colors'
import type { CommandSchema, CommandDef } from '@/lib/types'

interface CommandBuilderProps {
  onQueue: (cmd: string, args: Record<string, string>, dest?: string, echo?: string, ptype?: string) => void
  onClose: () => void
}

export function CommandBuilder({ onQueue, onClose }: CommandBuilderProps) {
  const [schema, setSchema] = useState<CommandSchema | null>(null)
  const [search, setSearch] = useState('')
  const [selectedCmd, setSelectedCmd] = useState<string | null>(null)
  const [argValues, setArgValues] = useState<Record<string, string>>({})

  useEffect(() => {
    fetch('/api/schema')
      .then((r) => r.json())
      .then((data: CommandSchema) => setSchema(data))
      .catch(() => {/* offline */})
  }, [])

  const filteredCmds = useMemo(() => {
    if (!schema) return []
    const entries = Object.entries(schema).filter(([, def]) => !def.rx_only)
    if (!search) return entries
    const lower = search.toLowerCase()
    return entries.filter(([name]) => name.toLowerCase().includes(lower))
  }, [schema, search])

  const cmdDef: CommandDef | null = selectedCmd && schema ? schema[selectedCmd] ?? null : null

  function handleSelect(name: string) {
    setSelectedCmd(name)
    setArgValues({})
  }

  function handleQueue() {
    if (!selectedCmd || !cmdDef) return
    onQueue(selectedCmd, argValues, cmdDef.dest, cmdDef.echo, cmdDef.ptype)
    setArgValues({})
  }

  return (
    <div className="border-t" style={{ borderColor: '#333', backgroundColor: colors.bgPanel }}>
      <div className="flex items-center justify-between px-2 py-1">
        <span className="text-xs font-bold" style={{ color: colors.label }}>Command Builder</span>
        <button onClick={onClose} className="text-xs" style={{ color: colors.dim }}>&times;</button>
      </div>

      <div className="px-2 pb-1">
        <input
          type="text"
          className="w-full bg-transparent border rounded px-2 py-1 text-xs outline-none"
          style={{ borderColor: '#333', color: colors.value }}
          placeholder="Search commands..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {!selectedCmd ? (
        <div className="max-h-40 overflow-y-auto px-2 pb-2">
          {!schema ? (
            <div className="text-xs py-2 text-center" style={{ color: colors.dim }}>Loading schema...</div>
          ) : filteredCmds.length === 0 ? (
            <div className="text-xs py-2 text-center" style={{ color: colors.dim }}>No commands found</div>
          ) : (
            filteredCmds.map(([name, def]) => (
              <button
                key={name}
                onClick={() => handleSelect(name)}
                className="block w-full text-left px-2 py-0.5 rounded text-xs hover:bg-white/5"
                style={{ color: colors.value }}
              >
                <span className="font-bold">{name}</span>
                {def.dest && <span style={{ color: colors.dim }}> &rarr; {def.dest}</span>}
                {def.tx_args && def.tx_args.length > 0 && (
                  <span style={{ color: colors.dim }}>
                    {' '}({def.tx_args.map((a) => a.name).join(', ')})
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      ) : (
        <div className="px-2 pb-2 space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setSelectedCmd(null); setArgValues({}) }}
              className="text-xs"
              style={{ color: colors.dim }}
            >
              &larr; Back
            </button>
            <span className="text-xs font-bold" style={{ color: colors.value }}>{selectedCmd}</span>
          </div>

          {cmdDef?.tx_args && cmdDef.tx_args.length > 0 ? (
            cmdDef.tx_args.map((arg) => (
              <div key={arg.name} className="flex items-center gap-2">
                <label className="text-xs w-24 shrink-0 text-right" style={{ color: colors.dim }}>
                  {arg.name}
                  <span className="text-[10px] ml-0.5" style={{ color: colors.dim }}>({arg.type})</span>
                </label>
                <input
                  type="text"
                  className="flex-1 bg-transparent border rounded px-2 py-0.5 text-xs outline-none"
                  style={{ borderColor: '#333', color: colors.value }}
                  value={argValues[arg.name] ?? ''}
                  onChange={(e) => setArgValues((prev) => ({ ...prev, [arg.name]: e.target.value }))}
                  placeholder={arg.type}
                />
              </div>
            ))
          ) : (
            <div className="text-xs" style={{ color: colors.dim }}>No arguments</div>
          )}

          <button
            onClick={handleQueue}
            className="px-3 py-1 rounded text-xs font-medium mt-1"
            style={{ color: colors.bgBase, backgroundColor: colors.success }}
          >
            + Queue
          </button>
        </div>
      )}
    </div>
  )
}
