import { useState } from 'react'
import { colors } from '@/lib/colors'
import { TogglePill } from '@/components/shared/TogglePill'
import { PacketList } from './PacketList'
import { RxStatusBar } from './RxStatusBar'
import { useAutoScroll } from '@/hooks/useAutoScroll'
import type { RxPacket, RxStatus } from '@/lib/types'

interface RxPanelProps {
  packets: RxPacket[]
  status: RxStatus
}

export function RxPanel({ packets, status }: RxPanelProps) {
  const [showHex, setShowHex] = useState(false)
  const [showFrame, setShowFrame] = useState(false)
  const [hideUplink, setHideUplink] = useState(false)

  const autoScrollState = useAutoScroll(packets.length)

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: colors.bgBase }}>
      {/* Panel header */}
      <div
        className="flex items-center justify-between px-2 py-1 border-b shrink-0"
        style={{ borderColor: '#333', backgroundColor: colors.bgPanel }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-wide" style={{ color: colors.success }}>
            RX DOWNLINK
          </span>
          {status.pkt_rate > 0 && (
            <span className="text-[10px]" style={{ color: colors.dim }}>
              {status.pkt_rate.toFixed(1)} pkt/s
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <TogglePill label="HEX" active={showHex} onClick={() => setShowHex((v) => !v)} />
          <TogglePill label="UL" active={!hideUplink} onClick={() => setHideUplink((v) => !v)} />
          <TogglePill label="FRAME" active={showFrame} onClick={() => setShowFrame((v) => !v)} />
        </div>
      </div>

      {/* Packet list */}
      <PacketList
        packets={packets}
        showHex={showHex}
        showFrame={showFrame}
        hideUplink={hideUplink}
        autoScrollState={autoScrollState}
      />

      {/* Status bar */}
      <RxStatusBar
        status={status}
        packetCount={packets.length}
        autoScroll={autoScrollState.autoScroll}
        onLiveClick={autoScrollState.scrollToBottom}
      />
    </div>
  )
}
