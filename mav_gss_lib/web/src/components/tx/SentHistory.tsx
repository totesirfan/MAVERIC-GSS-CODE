import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronRight, History, ClipboardCopy, RotateCcw } from 'lucide-react'
import { colors } from '@/lib/colors'
import { col } from '@/lib/columns'
import { PtypeBadge } from '@/components/shared/PtypeBadge'
import { ContextMenuRoot, ContextMenuTrigger, ContextMenuContent, ContextMenuItem } from '@/components/shared/ContextMenu'
import type { TxHistoryItem, MissionHistoryItem } from '@/lib/types'

type HistoryEntry = TxHistoryItem | MissionHistoryItem

interface SentHistoryProps {
  history: HistoryEntry[]
  onRequeue?: (item: HistoryEntry) => void
}

const springConfig = { type: 'spring' as const, stiffness: 500, damping: 30, mass: 0.8 }

export function SentHistory({ history, onRequeue }: SentHistoryProps) {
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new items arrive
  useEffect(() => {
    if (expanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [history.length, expanded])

  return (
    <div className="shrink-0 rounded-lg border overflow-hidden shadow-panel" style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}>
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-white/[0.03] color-transition"
        style={{ color: colors.dim }}
      >
        {expanded
          ? <ChevronDown className="size-3" style={{ color: colors.label }} />
          : <ChevronRight className="size-3" />
        }
        <History className="size-3" />
        <span>Sent History</span>
        <span className="tabular-nums">({history.length})</span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={springConfig}
            className="overflow-hidden border-t"
            style={{ borderColor: colors.borderSubtle }}
          >
            <div ref={scrollRef} className="max-h-40 overflow-y-auto">
              {history.map((item) => {
                const isMission = 'type' in item && item.type === 'mission_cmd'
                const mItem = item as MissionHistoryItem
                const cItem = item as TxHistoryItem

                return (
                  <ContextMenuRoot key={item.n}>
                    <ContextMenuTrigger>
                      <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono hover:bg-white/[0.03]">
                        <span className={`${col.num} text-right shrink-0 tabular-nums`} style={{ color: colors.dim }}>{item.n}</span>
                        <span className={`${col.time} shrink-0 tabular-nums`} style={{ color: colors.dim }}>{item.ts}</span>
                        {isMission ? (
                          <>
                            <span className="shrink-0 px-2 py-0.5 rounded text-[11px] font-semibold" style={{ color: colors.value, backgroundColor: 'rgba(255,255,255,0.06)' }}>
                              {mItem.display?.title ?? '?'}
                            </span>
                            <span className="flex-1 min-w-0 truncate" style={{ color: colors.dim }}>
                              {mItem.display?.fields?.map(f => `${f.name}=${f.value}`).join(' ')}
                            </span>
                          </>
                        ) : (
                          <>
                            <span className={`${col.node} shrink-0 truncate`} style={{ color: colors.label }}>{cItem.dest}</span>
                            <PtypeBadge ptype={cItem.ptype} />
                            <span className="shrink-0 px-2 py-0.5 rounded text-[11px] font-semibold" style={{ color: colors.value, backgroundColor: 'rgba(255,255,255,0.06)' }}>{cItem.cmd}</span>
                            <span className="flex-1 min-w-0 truncate" style={{ color: colors.dim }}>{cItem.args}</span>
                          </>
                        )}
                        <span className={`${col.size} text-right shrink-0 tabular-nums`} style={{ color: colors.dim }}>{item.size}B</span>
                      </div>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem icon={ClipboardCopy} onSelect={() => {
                        const text = isMission
                          ? `${mItem.display?.title ?? '?'} ${mItem.display?.fields?.map(f => f.value).join(' ') ?? ''}`.trim()
                          : `${cItem.cmd} ${cItem.args}`.trim()
                        navigator.clipboard.writeText(text)
                      }}>
                        Copy Command
                      </ContextMenuItem>
                      {onRequeue && !isMission && (
                        <ContextMenuItem icon={RotateCcw} onSelect={() => onRequeue(item)}>
                          Re-queue
                        </ContextMenuItem>
                      )}
                    </ContextMenuContent>
                  </ContextMenuRoot>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
