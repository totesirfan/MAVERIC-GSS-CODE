import { useMemo, useState } from 'react'
import {
  DndContext, closestCenter,
  PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { Trash2, Send, StopCircle, ChevronDown } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { QueueItem } from '@/components/tx/QueueItem'
import { colors } from '@/lib/colors'
import { buildTxRow } from '@/lib/columns'
import type {
  TxQueueItem, TxQueueCmd, ColumnDef, SendProgress,
} from '@/lib/types'

const ROW_HEIGHT_PX = 30
const MAX_VISIBLE_ROWS = 4

interface QueuePanelProps {
  /** Header label, e.g. "Imaging Queue" or "Files Queue". */
  title: string
  /** Regex matched against each pending command's `cmd_id`. Only matching
   *  rows are shown; clearing only removes matching rows from the queue. */
  kindRegex: RegExp
  /** Stable id prefix for this panel's QueueItem keys/sortable ids. Avoids
   *  React key collisions when two QueuePanels render simultaneously. */
  idPrefix: string
  pendingQueue: TxQueueItem[]
  txColumns: ColumnDef[]
  sendProgress: SendProgress | null
  sendAll: () => void
  abortSend: () => void
  removeQueueItem: (index: number) => void
}

interface FilteredRow {
  /** Index in the unfiltered pendingQueue — required for removeQueueItem */
  absoluteIndex: number
  item: TxQueueCmd
  cmdId: string
}

/**
 * Mission-page queue — filtered, read-only view of the main TX pending
 * queue showing only commands whose cmd_id matches `kindRegex`. Matches
 * the main dashboard TxQueue layout (column header, QueueItem rows,
 * footer bar) so the visual is identical; cosmetic-only drag + context
 * menu handlers.
 */
export function QueuePanel({
  title,
  kindRegex,
  idPrefix,
  pendingQueue,
  txColumns,
  sendProgress,
  sendAll,
  abortSend,
  removeQueueItem,
}: QueuePanelProps) {
  const filteredRows = useMemo<FilteredRow[]>(() => {
    const rows: FilteredRow[] = []
    pendingQueue.forEach((item, idx) => {
      if (item.type !== 'mission_cmd') return
      const payload = item.payload as Record<string, unknown>
      const cmdId = String(payload.cmd_id ?? '')
      if (!kindRegex.test(cmdId)) return
      rows.push({ absoluteIndex: idx, item, cmdId })
    })
    return rows
  }, [pendingQueue, kindRegex])

  const visibleColumns = useMemo(() => {
    return txColumns.filter(column => {
      if (column.id === 'src') return false
      if (!column.hide_if_all?.length) return true
      const suppressSet = new Set(column.hide_if_all)
      return !filteredRows.every(row => {
        const r = buildTxRow(row.item, [column])
        return suppressSet.has(r[column.id]?.value as never)
      })
    })
  }, [txColumns, filteredRows])

  const count = filteredRows.length
  const otherCount = pendingQueue.length - count
  const sending = sendProgress !== null
  const noop = () => {}

  const [collapsedAtCount, setCollapsedAtCount] = useState<number | null>(null)
  const open = count > 0 && collapsedAtCount !== count
  const setOpen = (nextOpen: boolean) => setCollapsedAtCount(nextOpen ? null : count)

  const bodyMaxHeight = Math.min(count, MAX_VISIBLE_ROWS) * ROW_HEIGHT_PX

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 99999 } }),
  )

  const clearMatching = () => {
    const sorted = [...filteredRows].sort((a, b) => b.absoluteIndex - a.absoluteIndex)
    for (const row of sorted) {
      removeQueueItem(row.absoluteIndex)
    }
  }

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="flex flex-col rounded-md border overflow-hidden shadow-panel shrink-0"
      style={{
        borderColor: colors.borderSubtle,
        backgroundColor: colors.bgPanel,
      }}
    >
      <CollapsibleTrigger
        className="flex items-center gap-2 px-3 border-b shrink-0 w-full text-left hover:bg-white/[0.02] transition-colors outline-none"
        style={{
          borderColor: colors.borderSubtle,
          minHeight: 34,
          paddingTop: 6,
          paddingBottom: 6,
        }}
      >
        <ChevronDown
          className="size-3.5 transition-transform duration-200"
          style={{
            color: colors.dim,
            transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
          }}
        />
        <span
          className="font-bold uppercase"
          style={{
            color: colors.value,
            fontSize: 14,
            letterSpacing: '0.02em',
          }}
        >
          {title}
        </span>
        <span className="text-[11px]" style={{ color: colors.dim }}>
          {count} cmd{count !== 1 ? 's' : ''}
          {otherCount > 0 ? ` · +${otherCount} other pending` : ''}
        </span>
        {sending && (
          <Badge
            className="text-[11px] px-1.5 py-0 h-5 animate-pulse-text"
            style={{ backgroundColor: colors.infoFill, color: colors.info }}
          >
            SENDING {sendProgress.sent}/{sendProgress.total}
          </Badge>
        )}
      </CollapsibleTrigger>

      <CollapsibleContent>
        {count > 0 && (
          <div
            className="flex items-center gap-1.5 px-3.5 py-0.5 text-[11px] font-light shrink-0"
            style={{ color: colors.dim }}
          >
            <span className="w-7 text-right">#</span>
            {visibleColumns.length > 0
              ? visibleColumns.map(c => (
                  <span
                    key={c.id}
                    className={`${c.width ?? ''} ${c.flex ? 'flex-1 min-w-0' : 'shrink-0'} ${c.align === 'right' ? 'text-right' : ''}`}
                  >
                    {c.label}
                  </span>
                ))
              : <span className="flex-1">command</span>
            }
          </div>
        )}

        <div
          className="overflow-y-auto overflow-x-hidden px-2 py-1 flex flex-col"
          style={{ maxHeight: count > 0 ? bodyMaxHeight : undefined }}
        >
          {count === 0 ? (
            <div
              className="flex items-center justify-center py-3 text-xs"
              style={{ color: colors.dim }}
            >
              No commands staged
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={noop}>
              <SortableContext
                items={[...filteredRows].reverse().map(r => `${idPrefix}-${r.item.num}`)}
                strategy={verticalListSortingStrategy}
              >
                {[...filteredRows].reverse().map((row, reverseIdx) => {
                  const displayNum = filteredRows.length - reverseIdx
                  const isSending = sending && row.absoluteIndex === 0
                  const status = isSending ? 'sending' : 'pending'
                  return (
                    <QueueItem
                      key={`${idPrefix}-${row.item.num}`}
                      item={{ ...row.item, num: displayNum }}
                      status={status}
                      index={row.absoluteIndex}
                      sortId={`${idPrefix}-${row.item.num}`}
                      expanded={false}
                      isGuarding={false}
                      compact
                      visibleColumns={visibleColumns}
                      onSelect={noop}
                      onToggleGuard={noop}
                      onDelete={removeQueueItem}
                      onDuplicate={noop}
                      onMoveToTop={noop}
                      onMoveToBottom={noop}
                    />
                  )
                })}
              </SortableContext>
            </DndContext>
          )}
        </div>
      </CollapsibleContent>

      <div
        className="flex items-center justify-end gap-1.5 px-3 py-1 border-t shrink-0"
        style={{ borderColor: colors.borderSubtle }}
      >
        {count > 0 && !sending && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearMatching}
            className="h-6 px-2 text-xs gap-1"
            style={{ color: colors.dim }}
          >
            <Trash2 className="size-3" /> Clear
          </Button>
        )}
        {sending ? (
          <Button
            size="sm"
            onClick={abortSend}
            className="h-6 px-2 text-xs gap-1 btn-feedback"
            style={{ color: colors.bgBase, backgroundColor: colors.error }}
          >
            <StopCircle className="size-3" /> Abort
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={sendAll}
            disabled={count === 0}
            className="h-6 px-2 text-xs gap-1 btn-feedback"
            style={{ color: colors.bgBase, backgroundColor: colors.success }}
          >
            <Send className="size-3" /> Send All
          </Button>
        )}
      </div>
    </Collapsible>
  )
}
