import { useState } from 'react'
import { colors } from '@/lib/colors'
import { TxQueue } from './TxQueue'
import { SentHistory } from './SentHistory'
import { CommandInput } from './CommandInput'
import { CommandBuilder } from './CommandBuilder'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import type {
  TxQueueItem, TxQueueSummary, TxHistoryItem,
  SendProgress, GuardConfirm,
} from '@/lib/types'

interface TxPanelProps {
  queue: TxQueueItem[]
  summary: TxQueueSummary
  history: TxHistoryItem[]
  sendProgress: SendProgress | null
  guardConfirm: GuardConfirm | null
  error: string | null
  uplinkMode: string
  queueCommand: (line: string) => void
  queueBuilt: (cmd: string, args: Record<string, string>, dest?: string, echo?: string, ptype?: string) => void
  deleteItem: (index: number) => void
  clearQueue: () => void
  undoLast: () => void
  toggleGuard: (index: number) => void
  reorder: (oldIndex: number, newIndex: number) => void
  addDelay: (ms: number) => void
  editDelay: (index: number, ms: number) => void
  sendAll: () => void
  abortSend: () => void
  approveGuard: () => void
  rejectGuard: () => void
}

export function TxPanel({
  queue, summary, history, sendProgress, guardConfirm, error, uplinkMode,
  queueCommand, queueBuilt, deleteItem, clearQueue, undoLast,
  toggleGuard, reorder, editDelay,
  sendAll, abortSend, approveGuard, rejectGuard,
}: TxPanelProps) {
  const [showBuilder, setShowBuilder] = useState(false)
  const [confirmClear, setConfirmClear] = useState(false)
  const [confirmSend, setConfirmSend] = useState(false)

  // suppress unused for now
  void undoLast; void abortSend

  const modeColor = uplinkMode.toLowerCase().includes('golay') ? colors.frameGolay : colors.frameAx25

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: colors.bgBase }}>
      {/* Panel header */}
      <div
        className="flex items-center justify-between px-2 py-1 border-b shrink-0"
        style={{ borderColor: '#333', backgroundColor: colors.bgPanel }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-wide" style={{ color: colors.label }}>
            TX UPLINK
          </span>
          <span className="text-[10px] font-medium" style={{ color: modeColor }}>
            {uplinkMode || '--'}
          </span>
        </div>
        {sendProgress && (
          <span className="text-[10px]" style={{ color: colors.label }}>
            {sendProgress.sent}/{sendProgress.total}
          </span>
        )}
      </div>

      {/* Queue */}
      <TxQueue
        queue={queue}
        summary={summary}
        sendProgress={sendProgress}
        onToggleGuard={toggleGuard}
        onDelete={deleteItem}
        onEditDelay={editDelay}
        onReorder={reorder}
        onClear={() => setConfirmClear(true)}
        onSend={() => setConfirmSend(true)}
      />

      {/* Sent history */}
      <SentHistory history={history} />

      {/* Command input / builder */}
      {showBuilder ? (
        <CommandBuilder
          onQueue={queueBuilt}
          onClose={() => setShowBuilder(false)}
        />
      ) : (
        <CommandInput
          onSubmit={queueCommand}
          onBuilderToggle={() => setShowBuilder(true)}
          error={error}
        />
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={confirmClear}
        title="Clear Queue"
        detail={`Remove all ${summary.cmds} queued items?`}
        variant="destructive"
        onConfirm={() => { clearQueue(); setConfirmClear(false) }}
        onCancel={() => setConfirmClear(false)}
      />

      <ConfirmDialog
        open={confirmSend}
        title="Send All"
        detail={`Send ${summary.cmds} command${summary.cmds !== 1 ? 's' : ''}${summary.guards > 0 ? ` (${summary.guards} guarded)` : ''}?`}
        variant="caution"
        onConfirm={() => { sendAll(); setConfirmSend(false) }}
        onCancel={() => setConfirmSend(false)}
      />

      <ConfirmDialog
        open={guardConfirm !== null}
        title="Guard Confirmation"
        detail={guardConfirm ? `${guardConfirm.cmd} ${guardConfirm.args} -> ${guardConfirm.dest}` : ''}
        variant="caution"
        onConfirm={approveGuard}
        onCancel={rejectGuard}
      />
    </div>
  )
}
