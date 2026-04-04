import { useState, useMemo, type RefObject } from 'react'
import { PacketRow } from './PacketRow'
import { PacketDetail } from './PacketDetail'
import { colors } from '@/lib/colors'
import type { RxPacket } from '@/lib/types'

interface PacketListProps {
  packets: RxPacket[]
  showHex: boolean
  showFrame: boolean
  hideUplink: boolean
  autoScrollState: {
    ref: RefObject<HTMLDivElement | null>
    onScroll: () => void
  }
}

export function PacketList({ packets, showHex, showFrame, hideUplink, autoScrollState }: PacketListProps) {
  const [selectedNum, setSelectedNum] = useState<number | null>(null)

  const filtered = useMemo(
    () => hideUplink ? packets.filter((p) => !p.is_echo) : packets,
    [packets, hideUplink],
  )

  const { ref, onScroll } = autoScrollState

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Column headers */}
      <div
        className="flex items-center gap-2 px-2 py-1 text-[10px] uppercase tracking-wider border-b shrink-0"
        style={{ color: colors.dim, borderColor: '#333', backgroundColor: colors.bgPanel }}
      >
        <span className="w-8 text-right">#</span>
        <span className="w-16">Time</span>
        {showFrame && <span className="w-14">Frame</span>}
        <span className="w-8">Type</span>
        <span className="w-20">Cmd</span>
        <span className="flex-1">Args</span>
        <span className="w-16 text-right">Flags</span>
        <span className="w-10 text-right">Size</span>
      </div>

      {/* Scrollable packet list */}
      <div ref={ref} onScroll={onScroll} className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs" style={{ color: colors.dim }}>
            Waiting for packets...
          </div>
        ) : (
          filtered.map((pkt) => (
            <div key={pkt.num}>
              <PacketRow
                packet={pkt}
                selected={selectedNum === pkt.num}
                showFrame={showFrame}
                onClick={() => setSelectedNum(selectedNum === pkt.num ? null : pkt.num)}
              />
              {selectedNum === pkt.num && (
                <PacketDetail packet={pkt} showHex={showHex} />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
