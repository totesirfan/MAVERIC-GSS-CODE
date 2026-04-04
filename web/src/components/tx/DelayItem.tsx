import { useState } from 'react'
import { colors } from '@/lib/colors'

interface DelayItemProps {
  delayMs: number
  index: number
  onEditDelay: (index: number, ms: number) => void
}

export function DelayItem({ delayMs, index, onEditDelay }: DelayItemProps) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(String(delayMs))

  function handleSubmit() {
    const ms = parseInt(value, 10)
    if (!isNaN(ms) && ms > 0) {
      onEditDelay(index, ms)
    }
    setEditing(false)
  }

  return (
    <div className="flex items-center gap-2 px-2 py-1 my-0.5">
      <div className="flex-1 border-t border-dashed" style={{ borderColor: colors.dim }} />
      {editing ? (
        <input
          autoFocus
          type="number"
          className="w-20 bg-transparent border rounded px-1 py-0.5 text-xs text-center outline-none"
          style={{ borderColor: colors.label, color: colors.value }}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={handleSubmit}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); if (e.key === 'Escape') setEditing(false) }}
        />
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="px-2 py-0.5 rounded text-[10px] font-medium"
          style={{ color: colors.label, backgroundColor: `${colors.label}15` }}
        >
          {delayMs}ms
        </button>
      )}
      <div className="flex-1 border-t border-dashed" style={{ borderColor: colors.dim }} />
    </div>
  )
}
