import {
  DndContext, closestCenter,
  PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { QueueItem } from './QueueItem'
import { DelayItem } from './DelayItem'
import { colors } from '@/lib/colors'
import type { TxQueueItem, TxQueueSummary, SendProgress } from '@/lib/types'

interface TxQueueProps {
  queue: TxQueueItem[]
  summary: TxQueueSummary
  sendProgress: SendProgress | null
  onToggleGuard: (index: number) => void
  onDelete: (index: number) => void
  onEditDelay: (index: number, ms: number) => void
  onReorder: (oldIndex: number, newIndex: number) => void
  onClear: () => void
  onSend: () => void
}

export function TxQueue({
  queue, summary, sendProgress,
  onToggleGuard, onDelete, onEditDelay, onReorder,
  onClear, onSend,
}: TxQueueProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = queue.findIndex((_, i) => `item-${i}` === active.id)
      const newIndex = queue.findIndex((_, i) => `item-${i}` === over.id)
      if (oldIndex !== -1 && newIndex !== -1) {
        onReorder(oldIndex, newIndex)
      }
    }
  }

  const estStr = summary.est_time_s > 0 ? `~${summary.est_time_s.toFixed(1)}s` : ''

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-2 py-1 text-[10px] border-b shrink-0"
        style={{ color: colors.dim, borderColor: '#333' }}
      >
        <span>{summary.cmds} cmd{summary.cmds !== 1 ? 's' : ''}{summary.guards > 0 ? ` / ${summary.guards} guarded` : ''} {estStr}</span>
        {sendProgress && (
          <span style={{ color: colors.label }}>
            Sending {sendProgress.sent}/{sendProgress.total}: {sendProgress.current}
            {sendProgress.waiting ? ' (waiting)' : ''}
          </span>
        )}
      </div>

      {/* Scrollable queue */}
      <div className="flex-1 overflow-y-auto px-1 py-1">
        {queue.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs" style={{ color: colors.dim }}>
            Queue empty. Type a command below.
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={queue.map((_, i) => `item-${i}`)} strategy={verticalListSortingStrategy}>
              {queue.map((item, i) => {
                if (item.type === 'delay') {
                  return <DelayItem key={`delay-${i}`} delayMs={item.delay_ms} index={i} onEditDelay={onEditDelay} />
                }
                return (
                  <QueueItem
                    key={`cmd-${i}`}
                    item={item}
                    index={i}
                    onToggleGuard={onToggleGuard}
                    onDelete={onDelete}
                  />
                )
              })}
            </SortableContext>
          </DndContext>
        )}
      </div>

      {/* Bottom bar */}
      {queue.length > 0 && (
        <div
          className="flex items-center justify-between px-2 py-1 border-t shrink-0"
          style={{ borderColor: '#333', backgroundColor: colors.bgPanel }}
        >
          <span className="text-xs" style={{ color: colors.dim }}>
            {summary.cmds} item{summary.cmds !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="px-2 py-0.5 rounded text-xs"
              style={{ color: colors.error, border: `1px solid ${colors.error}44` }}
            >
              Clear
            </button>
            <button
              onClick={onSend}
              className="px-2 py-0.5 rounded text-xs font-medium"
              style={{ color: colors.bgBase, backgroundColor: colors.success }}
            >
              Send All
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
