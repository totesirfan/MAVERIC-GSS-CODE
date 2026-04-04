import { colors, ptypeColor, frameColor } from '@/lib/colors'
import type { RxPacket } from '@/lib/types'

interface PacketRowProps {
  packet: RxPacket
  selected: boolean
  showFrame: boolean
  onClick: () => void
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-GB', { hour12: false })
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '\u2026' : s
}

function argsString(args: RxPacket['args']): string {
  if (Array.isArray(args)) return args.join(' ')
  if (typeof args === 'object' && args !== null) {
    return Object.entries(args).map(([k, v]) => `${k}=${v}`).join(' ')
  }
  return ''
}

export function PacketRow({ packet, selected, showFrame, onClick }: PacketRowProps) {
  const p = packet
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-2 px-2 py-0.5 cursor-pointer hover:bg-white/[0.03] text-xs leading-5"
      style={{
        backgroundColor: selected ? 'rgba(0,191,255,0.06)' : undefined,
        borderLeft: selected ? `2px solid ${colors.label}` : '2px solid transparent',
      }}
    >
      <span className="w-8 text-right shrink-0" style={{ color: colors.dim }}>
        {p.num}
      </span>
      <span className="w-16 shrink-0" style={{ color: colors.dim }}>
        {formatTime(p.time)}
      </span>
      {showFrame && (
        <span className="w-14 shrink-0 font-medium" style={{ color: frameColor(p.frame) }}>
          {p.frame || '--'}
        </span>
      )}
      <span className="w-8 shrink-0 font-medium" style={{ color: ptypeColor(p.ptype) }}>
        {p.ptype}
      </span>
      <span className="w-20 shrink-0 font-bold" style={{ color: colors.value }}>
        {p.cmd || '--'}
      </span>
      <span className="flex-1 min-w-0 truncate" style={{ color: colors.dim }}>
        {truncate(argsString(p.args), 60)}
      </span>
      <span className="flex items-center gap-1 shrink-0">
        {p.crc16_ok === false && (
          <span className="px-1 rounded text-[10px] font-medium" style={{ color: colors.error, backgroundColor: `${colors.error}22` }}>CRC</span>
        )}
        {p.is_echo && (
          <span className="px-1 rounded text-[10px] font-medium" style={{ color: colors.label, backgroundColor: `${colors.label}22` }}>UL</span>
        )}
        {p.is_dup && (
          <span className="px-1 rounded text-[10px] font-medium" style={{ color: colors.warning, backgroundColor: `${colors.warning}22` }}>DUP</span>
        )}
      </span>
      <span className="w-10 text-right shrink-0" style={{ color: colors.dim }}>
        {p.size}B
      </span>
    </div>
  )
}
