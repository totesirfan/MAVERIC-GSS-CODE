import { useState, useRef, useCallback, useMemo, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ExternalLink, SlidersHorizontal, Download, X, ClipboardCopy, Binary } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TogglePill } from '@/components/shared/TogglePill'
import { StatusDot } from '@/components/shared/StatusDot'
import { PacketList } from './PacketList'
import { PacketDetail } from './PacketDetail'
import { RxStatusBar } from './RxStatusBar'
import { ReplayPanel } from '@/components/logs/ReplayPanel'
import { colors } from '@/lib/colors'
import { PanelToasts } from '@/components/shared/StatusToast'
import {
  ContextMenuRoot, ContextMenuTrigger, ContextMenuContent,
  ContextMenuItem,
} from '@/components/shared/ContextMenu'
import type { RxPacket, RxStatus } from '@/lib/types'

function f(label: string, value: string): string {
  return `  ${label.padEnd(12)}${value}`
}

function formatPacketText(p: RxPacket): string {
  const lines: string[] = []
  const sep = '\u2500'
  const extras = [p.frame || '', `${p.size}B`, p.is_dup ? '[DUP]' : '', p.is_echo ? '[UL]' : ''].filter(Boolean).join('  ')
  lines.push(`${sep.repeat(4)} #${p.num}  ${p.time_utc || p.time}  ${extras} ${sep.repeat(20)}`)
  if (p.is_echo) lines.push('  \u25B2\u25B2\u25B2 UPLINK ECHO \u25B2\u25B2\u25B2')
  for (const w of p.warnings) lines.push(f('\u26A0 WARNING', w))
  if (p.ax25_header) lines.push(f('AX.25 HDR', p.ax25_header))
  if (p.csp_header) lines.push(f('CSP V1', Object.entries(p.csp_header).map(([k, v]) => `${k}:${v}`).join('  ')))
  if (p.sat_time_utc) lines.push(f('SAT TIME', `${p.sat_time_utc} \u2502 ${p.sat_time_local || ''}`))
  lines.push(f('CMD', `Src:${p.src}  Dest:${p.dest}  Echo:${p.echo || 'NONE'}  Type:${p.ptype}`))
  lines.push(f('CMD ID', p.cmd || '--'))
  for (const a of p.args_named ?? []) lines.push(f(a.name.toUpperCase(), a.value))
  for (let i = 0; i < (p.args_extra ?? []).length; i++) lines.push(f(`ARG +${i}`, (p.args_extra ?? [])[i]))
  if (p.crc16_ok !== null) lines.push(f('CRC-16', p.crc16_ok ? 'OK' : 'FAIL'))
  if (p.crc32_ok !== null) lines.push(f('CRC-32C', p.crc32_ok ? 'OK' : 'FAIL'))
  if (p.raw_hex) {
    const hex = p.raw_hex.match(/.{1,2}/g)?.join(' ') ?? p.raw_hex
    const chunks = hex.match(/.{1,47}/g) ?? [hex]
    chunks.forEach((chunk, i) => lines.push(i === 0 ? f('HEX', chunk) : f('', chunk)))
  }
  return lines.join('\n')
}

interface RxPanelProps {
  packets: RxPacket[]
  status: RxStatus
  replayMode?: boolean
  replaySession?: string | null
  replacePackets?: (pkts: RxPacket[]) => void
  onStopReplay?: () => void
}

const RECEIVE_TIMEOUT_MS = 2000

export function RxPanel({ packets, status, replayMode, replaySession, replacePackets, onStopReplay }: RxPanelProps) {
  const [showHex, setShowHex] = useState(false)
  const [showFrame, setShowFrame] = useState(false)
  const [showWrapper, setShowWrapper] = useState(false)
  const [hideUplink, setHideUplink] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [receiving, setReceiving] = useState(false)
  const [selectedNum, setSelectedNum] = useState<number | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailHeight, setDetailHeight] = useState(200)
  const isDragging = useRef(false)
  const receiveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevLastNum = useRef(-1)
  // Track whether user explicitly pinned a non-latest packet
  const pinned = useRef(false)

  const filtered = useMemo(
    () => hideUplink ? packets.filter(p => !p.is_echo) : packets,
    [packets, hideUplink],
  )
  const lastNum = filtered.length > 0 ? filtered[filtered.length - 1].num : null
  const lastPktNum = packets.length > 0 ? packets[packets.length - 1].num : -1

  // Receiving detection — fire whenever a new packet number appears
  useEffect(() => {
    if (lastPktNum > prevLastNum.current) {
      setReceiving(true)
      if (receiveTimer.current) clearTimeout(receiveTimer.current)
      receiveTimer.current = setTimeout(() => setReceiving(false), RECEIVE_TIMEOUT_MS)
    }
    prevLastNum.current = lastPktNum
  }, [lastPktNum])

  useEffect(() => () => { if (receiveTimer.current) clearTimeout(receiveTimer.current) }, [])

  // Auto-follow latest
  useEffect(() => {
    if (autoScroll && lastNum !== null && !pinned.current) {
      setSelectedNum(lastNum)
    }
  }, [autoScroll, lastNum])

  function handleSelect(num: number) {
    if (selectedNum === num && detailOpen) {
      setDetailOpen(false)
      setSelectedNum(null)
    } else if (selectedNum === num && !detailOpen) {
      setDetailOpen(true)
    } else {
      setSelectedNum(num)
      setDetailOpen(true)
      if (num !== lastNum) {
        pinned.current = true
        setAutoScroll(false)
      } else {
        pinned.current = false
      }
    }
  }

  const handleScrolledUp = useCallback(() => setAutoScroll(false), [])

  const scrollToBottom = useCallback(() => {
    pinned.current = false
    setAutoScroll(true)
  }, [])

  const startDragResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    const startY = e.clientY
    const startH = detailHeight
    function onMove(ev: MouseEvent) {
      setDetailHeight(Math.max(100, Math.min(window.innerHeight * 0.7, startH + (startY - ev.clientY))))
    }
    function onUp() {
      isDragging.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [detailHeight])

  const selectedPacket = selectedNum !== null ? filtered.find(p => p.num === selectedNum) ?? null : null
  const isLive = autoScroll && selectedNum === lastNum

  return (
    <div className="flex flex-col h-full gap-3 relative">
      <div
        className={`flex flex-col flex-1 min-h-0 rounded-lg border overflow-hidden shadow-panel ${receiving ? 'animate-pulse-glow' : ''}`}
        style={{ borderColor: receiving ? `${colors.success}55` : colors.borderSubtle, backgroundColor: colors.bgPanel }}
      >
        <div
          className={`flex items-center justify-between px-3 py-1.5 border-b shrink-0 ${receiving ? 'animate-sweep-green' : ''}`}
          style={{ borderColor: colors.borderSubtle }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold tracking-wide" style={{ color: colors.value }}>RX DOWNLINK</span>
            <StatusDot status={replayMode ? 'REPLAY' : status.zmq} />
            {replayMode ? (
              <span className="text-[11px] font-medium" style={{ color: colors.warning }}>REPLAY</span>
            ) : receiving ? (
              <span className="text-[11px] font-bold animate-pulse-text flex items-center gap-1" style={{ color: colors.success }}>
                <Download className="size-3" />
                Received
              </span>
            ) : (
              <span className="text-[11px] font-light" style={{ color: colors.dim }}>Idle</span>
            )}
          </div>
          <div className="flex items-center gap-1 group/toggles">
            <div className="flex items-center gap-1">
              <div className={`flex items-center gap-1 ${!showHex ? 'hidden group-hover/toggles:flex' : 'flex'}`}>
                <TogglePill label="HEX" active={showHex} onClick={() => setShowHex(v => !v)} />
              </div>
              <div className={`flex items-center gap-1 ${hideUplink ? 'hidden group-hover/toggles:flex' : 'flex'}`}>
                <TogglePill label="UL" active={!hideUplink} onClick={() => setHideUplink(v => !v)} />
              </div>
              <div className={`flex items-center gap-1 ${!showFrame ? 'hidden group-hover/toggles:flex' : 'flex'}`}>
                <TogglePill label="FRAME" active={showFrame} onClick={() => setShowFrame(v => !v)} />
              </div>
              <div className={`flex items-center gap-1 ${!showWrapper ? 'hidden group-hover/toggles:flex' : 'flex'}`}>
                <TogglePill label="WRAP" active={showWrapper} onClick={() => setShowWrapper(v => !v)} />
              </div>
            </div>
            {!showHex && hideUplink && !showFrame && !showWrapper && (
              <SlidersHorizontal className="size-3.5 group-hover/toggles:hidden" style={{ color: colors.dim }} />
            )}
            <Button variant="ghost" size="icon" className="size-6" onClick={() => window.open('/?panel=rx', 'maveric-rx', 'popup=1,width=900,height=800')} title="Pop out RX panel">
              <ExternalLink className="size-3.5" style={{ color: colors.dim }} />
            </Button>
          </div>
        </div>

        {replayMode && replaySession && replacePackets && onStopReplay && (
          <ReplayPanel sessionId={replaySession} replacePackets={replacePackets} onStop={onStopReplay} />
        )}

        <PacketList
          packets={packets}
          showFrame={showFrame}
          hideUplink={hideUplink}
          selectedNum={selectedNum}
          onSelect={handleSelect}
          autoScroll={autoScroll}
          onScrolledUp={handleScrolledUp}
          zmqStatus={replayMode ? 'REPLAY' : status.zmq}
          scrollSignal={detailOpen ? detailHeight : -1}
        />

      </div>

      <RxStatusBar
        status={status}
        packets={packets}
        autoScroll={autoScroll}
        onLiveClick={scrollToBottom}
        replayMode={replayMode}
      />

      {selectedPacket && (
        <div
          className="shrink-0 overflow-hidden"
          style={{
            height: detailOpen ? detailHeight : 0,
            opacity: detailOpen ? 1 : 0,
            transition: isDragging.current ? 'none' : 'height 0.2s ease, opacity 0.15s ease',
          }}
        >
          <ContextMenuRoot>
            <ContextMenuTrigger>
              <div
                className="flex flex-col rounded-lg border overflow-hidden shadow-panel"
                style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, height: detailHeight }}
              >
                <div
                  onMouseDown={startDragResize}
                  className="h-1.5 shrink-0 cursor-ns-resize flex items-center justify-center"
                  style={{ backgroundColor: colors.bgPanelRaised }}
                >
                  <div className="w-8 h-0.5 rounded-full" style={{ backgroundColor: colors.borderStrong }} />
                </div>
                <div className="flex items-center justify-between px-3 py-1 border-b shrink-0" style={{ borderColor: colors.borderSubtle }}>
                  <span className="text-xs font-bold" style={{ color: colors.value }}>
                    #{selectedPacket.num} {selectedPacket.cmd || '???'}
                    {isLive && <span className="ml-2 text-[11px] font-normal" style={{ color: colors.success }}>LIVE</span>}
                  </span>
                  <button onClick={() => setDetailOpen(false)} className="p-0.5 rounded hover:bg-white/5">
                    <X className="size-3" style={{ color: colors.dim }} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={selectedPacket.num}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.1, ease: 'easeOut' }}
                    >
                      <PacketDetail packet={selectedPacket} showHex={showHex} showWrapper={showWrapper} showFrame={showFrame} />
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>
            </ContextMenuTrigger>
            <ContextMenuContent>
              <ContextMenuItem icon={ClipboardCopy} onSelect={() => navigator.clipboard.writeText(formatPacketText(selectedPacket))}>
                Copy Full Details
              </ContextMenuItem>
              <ContextMenuItem icon={ClipboardCopy} onSelect={() => navigator.clipboard.writeText(`${selectedPacket.cmd} ${(selectedPacket.args_named ?? []).map(a => a.value).join(' ')} ${(selectedPacket.args_extra ?? []).join(' ')}`.trim())}>
                Copy Command + Args
              </ContextMenuItem>
              {selectedPacket.raw_hex && (
                <ContextMenuItem icon={Binary} onSelect={() => navigator.clipboard.writeText(selectedPacket.raw_hex)}>
                  Copy Hex
                </ContextMenuItem>
              )}
            </ContextMenuContent>
          </ContextMenuRoot>
        </div>
      )}

      <PanelToasts side="rx" />
    </div>
  )
}
