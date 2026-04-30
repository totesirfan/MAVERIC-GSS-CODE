import { colors } from '@/lib/colors'

interface StatusDotProps {
  status: string
  label?: string
}

function dotColor(status: string): string {
  const upper = status.toUpperCase()
  if (upper === 'ONLINE' || upper === 'LIVE' || upper === 'BOUND') return colors.success
  if (upper === 'RETRY' || upper === 'REPLAY') return colors.warning
  if (upper === 'STOPPING') return colors.warning
  if (upper === 'CRASHED' || upper === 'FAULT') return colors.danger
  if (upper === 'STOPPED') return colors.neutral
  if (upper === 'WAITING') return colors.neutral
  return colors.danger
}

/** Shape indicator visible even in monochrome:
 *  ● LIVE/BOUND, ▲ RETRY, ▶ REPLAY, ■ STOPPING, ⚠ CRASHED, ○ STOPPED, … WAITING, ✕ DOWN */
function dotShape(status: string): string {
  const upper = status.toUpperCase()
  if (upper === 'ONLINE' || upper === 'LIVE' || upper === 'BOUND') return '●'  // ●
  if (upper === 'RETRY') return '▲'                                             // ▲
  if (upper === 'REPLAY') return '▶'                                            // ▶
  if (upper === 'STOPPING') return '■'                                          // ■
  if (upper === 'CRASHED' || upper === 'FAULT') return '⚠'                      // ⚠
  if (upper === 'STOPPED') return '○'                                           // ○
  if (upper === 'WAITING') return '…'                                           // …
  return '✕'                                                                    // ✕
}

export function StatusDot({ status, label }: StatusDotProps) {
  const displayLabel = status === 'ONLINE' ? 'LIVE' : status
  const color = dotColor(status)
  const shape = dotShape(status)
  return (
    <span className="inline-flex items-center gap-1.5 color-transition">
      <span className="text-[11px] leading-none" style={{ color }}>{shape}</span>
      <span className="text-[11px] font-medium" style={{ color }}>{label ?? displayLabel}</span>
    </span>
  )
}
