import { colors } from '@/lib/colors'
import type { RxStatus } from '@/lib/types'

interface RxStatusBarProps {
  status: RxStatus
  packetCount: number
  autoScroll: boolean
  onLiveClick: () => void
}

export function RxStatusBar({ status, packetCount, autoScroll, onLiveClick }: RxStatusBarProps) {
  const receiving = status.pkt_rate > 0
  const rateText = receiving
    ? `${status.pkt_rate.toFixed(1)} pkt/s`
    : `silent ${status.silence_s}s`

  return (
    <div
      className="flex items-center justify-between px-2 py-1 border-t text-xs"
      style={{ borderColor: '#333', backgroundColor: colors.bgPanel }}
    >
      <div className="flex items-center gap-3">
        <span style={{ color: colors.dim }}>{packetCount} packets</span>
        <span className="inline-flex items-center gap-1">
          <span
            className="inline-block size-1.5 rounded-full"
            style={{
              backgroundColor: receiving ? colors.success : colors.dim,
              boxShadow: receiving ? `0 0 4px ${colors.success}` : undefined,
            }}
          />
          <span style={{ color: receiving ? colors.success : colors.dim }}>{rateText}</span>
        </span>
      </div>

      {!autoScroll && (
        <button
          onClick={onLiveClick}
          className="px-2 py-0.5 rounded text-xs font-medium"
          style={{ color: colors.success, backgroundColor: `${colors.success}22` }}
        >
          LIVE
        </button>
      )}
    </div>
  )
}
