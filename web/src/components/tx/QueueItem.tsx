import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { colors, ptypeColor } from '@/lib/colors'
import type { TxQueueCmd } from '@/lib/types'

interface QueueItemProps {
  item: TxQueueCmd
  index: number
  onToggleGuard: (index: number) => void
  onDelete: (index: number) => void
}

export function QueueItem({ item, index, onToggleGuard, onDelete }: QueueItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `item-${index}` })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const borderColor = item.guard ? colors.warning : colors.success

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="group flex items-center gap-2 px-2 py-1 rounded text-xs border-l-2 mb-0.5"
      {...attributes}
      {...listeners}
    >
      <div style={{ borderColor }} className="border-l-2 -ml-2 self-stretch" />
      <span className="cursor-grab text-xs select-none" style={{ color: colors.dim }} title="Drag to reorder">
        &#x2807;
      </span>
      <span className="w-6 text-right shrink-0" style={{ color: colors.dim }}>
        {item.num}
      </span>
      <span className="w-10 shrink-0" style={{ color: colors.value }}>
        {item.dest}
      </span>
      <span className="w-8 shrink-0" style={{ color: ptypeColor(item.ptype) }}>
        {item.ptype}
      </span>
      <span className="font-bold shrink-0" style={{ color: colors.value }}>
        {item.cmd}
      </span>
      <span className="flex-1 min-w-0 truncate" style={{ color: colors.dim }}>
        {item.args}
      </span>
      {item.guard && (
        <span
          className="px-1 rounded text-[10px] font-medium shrink-0"
          style={{ color: colors.warning, backgroundColor: `${colors.warning}22` }}
        >
          GUARD
        </span>
      )}
      <span className="w-8 text-right shrink-0" style={{ color: colors.dim }}>
        {item.size}B
      </span>

      {/* Hover actions */}
      <div className="hidden group-hover:flex items-center gap-1 shrink-0">
        <button
          onClick={(e) => { e.stopPropagation(); onToggleGuard(index) }}
          className="px-1 rounded text-[10px]"
          style={{ color: item.guard ? colors.dim : colors.warning }}
          title={item.guard ? 'Remove guard' : 'Add guard'}
        >
          {item.guard ? '\u2613' : '\u26A0'}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(index) }}
          className="px-1 rounded text-[10px]"
          style={{ color: colors.error }}
          title="Delete"
        >
          \u2715
        </button>
      </div>
    </div>
  )
}
