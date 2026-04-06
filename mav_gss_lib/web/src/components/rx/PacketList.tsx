import { useMemo, useRef, useEffect, useCallback } from 'react'
import { PacketRow } from './PacketRow'
import { colors } from '@/lib/colors'
import { col } from '@/lib/columns'
import type { RxPacket } from '@/lib/types'

interface PacketListProps {
  packets: RxPacket[]
  showFrame: boolean
  hideUplink: boolean
  selectedNum: number | null
  onSelect: (num: number) => void
  autoScroll: boolean
  onScrolledUp: () => void
  zmqStatus?: string
  scrollSignal?: number
}

const MAX_DOM_PACKETS = 5000
const hasEcho = (echo: string) => echo && echo !== 'NONE' && echo !== '0' && echo !== ''

export function PacketList({
  packets, showFrame, hideUplink, selectedNum, onSelect,
  autoScroll, onScrolledUp, zmqStatus, scrollSignal,
}: PacketListProps) {
  const isStale = zmqStatus ? ['DOWN', 'OFFLINE'].includes(zmqStatus.toUpperCase()) : false
  const scrollRef = useRef<HTMLDivElement>(null)
  const suppressScroll = useRef(false)

  const filtered = useMemo(
    () => {
      const base = hideUplink ? packets.filter(p => !p.is_echo) : packets
      return base.length > MAX_DOM_PACKETS ? base.slice(-MAX_DOM_PACKETS) : base
    },
    [packets, hideUplink],
  )

  const showEcho = useMemo(
    () => filtered.some(p => hasEcho(p.echo)),
    [filtered],
  )

  // Auto-scroll to bottom when new packets arrive or container resizes
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      suppressScroll.current = true
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      requestAnimationFrame(() => { suppressScroll.current = false })
    }
  }, [filtered.length, autoScroll, scrollSignal])

  // Detect user scrolling up to unlock — ignore programmatic and resize scrolls
  const handleScroll = useCallback(() => {
    if (suppressScroll.current) return
    const el = scrollRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 5
    if (!atBottom) {
      onScrolledUp()
    }
  }, [onScrolledUp])

  return (
    <>
      {isStale && (
        <div className="flex items-center justify-center gap-2 px-3 py-1 text-xs font-semibold shrink-0"
          style={{ backgroundColor: colors.dangerFill, color: colors.danger, borderBottom: `1px solid ${colors.danger}40` }}>
          ⚠ DATA STALE — ZMQ disconnected
        </div>
      )}

      {filtered.length > 0 && (
        <div className="flex items-center text-[11px] font-light px-2 py-0.5 shrink-0" style={{ color: colors.sep }}>
          <span className={`${col.chevron} px-1`} />
          <span className={`${col.num} px-2 text-right`}>#</span>
          <span className={`${col.time} px-2`}>time</span>
          {showFrame && <span className={`${col.frame} px-2`}>frame</span>}
          <span className={`${col.node} px-2`}>src</span>
          {showEcho && <span className={`${col.node} px-2`}>echo</span>}
          <span className={`${col.ptype} px-1`}>type</span>
          <span className="flex-1 px-2">cmd / args</span>
          <span className={`${col.flags} px-2 text-right`}>flags</span>
          <span className={`${col.size} px-2 text-right`}>size</span>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="flex-1 flex items-center justify-center" style={{ color: colors.dim }}>
          <span className="text-xs py-8">Idle — no packets received</span>
        </div>
      ) : (
        <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto overflow-x-hidden">
          {filtered.map(pkt => {
            const isActive = selectedNum === pkt.num
            return (
              <div
                key={pkt.num}
                className={`pkt-row-wrap pkt-flash ${isActive ? 'pkt-border-active' : 'pkt-border-inactive'}`}
              >
                <PacketRow
                  packet={pkt}
                  selected={isActive}
                  showFrame={showFrame}
                  showEcho={showEcho}
                  onClick={() => onSelect(pkt.num)}
                />
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
