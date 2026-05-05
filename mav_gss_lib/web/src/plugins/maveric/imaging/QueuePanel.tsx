import { QueuePanel as SharedQueuePanel } from '../shared/QueuePanel'
import type { TxQueueItem, ColumnDef, SendProgress } from '@/lib/types'

interface ImagingQueuePanelProps {
  pendingQueue: TxQueueItem[]
  txColumns: ColumnDef[]
  sendProgress: SendProgress | null
  sendAll: () => void
  abortSend: () => void
  removeQueueItem: (index: number) => void
}

const IMAGING_KIND_REGEX = /^(img|cam|lcd)_/

export function QueuePanel(props: ImagingQueuePanelProps) {
  return (
    <SharedQueuePanel
      title="Imaging Queue"
      kindRegex={IMAGING_KIND_REGEX}
      idPrefix="img"
      {...props}
    />
  )
}
