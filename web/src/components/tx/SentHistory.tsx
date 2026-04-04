import { useState } from 'react'
import { colors, ptypeColor } from '@/lib/colors'
import type { TxHistoryItem } from '@/lib/types'

interface SentHistoryProps {
  history: TxHistoryItem[]
}

export function SentHistory({ history }: SentHistoryProps) {
  const [expanded, setExpanded] = useState(false)

  if (history.length === 0) return null

  return (
    <div className="border-t shrink-0" style={{ borderColor: '#333' }}>
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-2 py-1 text-xs hover:bg-white/[0.02]"
        style={{ color: colors.dim }}
      >
        <span>Sent History ({history.length})</span>
        <span>{expanded ? '\u25B4' : '\u25BE'}</span>
      </button>

      {expanded && (
        <div className="max-h-32 overflow-y-auto">
          {history.map((item) => (
            <div
              key={item.n}
              className="flex items-center gap-2 px-2 py-0.5 text-xs"
            >
              <span className="w-6 text-right shrink-0" style={{ color: colors.dim }}>{item.n}</span>
              <span className="w-16 shrink-0" style={{ color: colors.dim }}>{item.ts}</span>
              <span className="w-10 shrink-0" style={{ color: colors.value }}>{item.dest}</span>
              <span className="w-8 shrink-0" style={{ color: ptypeColor(item.ptype) }}>{item.ptype}</span>
              <span className="font-bold shrink-0" style={{ color: colors.value }}>{item.cmd}</span>
              <span className="flex-1 min-w-0 truncate" style={{ color: colors.dim }}>{item.args}</span>
              <span className="w-8 text-right shrink-0" style={{ color: colors.dim }}>{item.size}B</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
