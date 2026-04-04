import { colors, ptypeColor, frameColor } from '@/lib/colors'
import type { RxPacket } from '@/lib/types'

interface PacketDetailProps {
  packet: RxPacket
  showHex: boolean
}

function DetailRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="w-16 shrink-0 text-right" style={{ color: colors.dim }}>{label}</span>
      <span style={{ color: color ?? colors.value }}>{value}</span>
    </div>
  )
}

function argsDisplay(args: RxPacket['args']): string {
  if (Array.isArray(args)) return args.join(', ')
  if (typeof args === 'object' && args !== null) {
    return Object.entries(args).map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(', ')
  }
  return '--'
}

function crcDisplay(p: RxPacket): { text: string; color: string } {
  const parts: string[] = []
  if (p.crc16_ok !== null) parts.push(`CRC-16: ${p.crc16_ok ? 'OK' : 'FAIL'}`)
  if (p.crc32_ok !== null) parts.push(`CRC-32: ${p.crc32_ok ? 'OK' : 'FAIL'}`)
  if (parts.length === 0) return { text: '--', color: colors.dim }
  const ok = (p.crc16_ok !== false) && (p.crc32_ok !== false)
  return { text: parts.join(' | '), color: ok ? colors.success : colors.error }
}

export function PacketDetail({ packet: p, showHex }: PacketDetailProps) {
  const crc = crcDisplay(p)

  return (
    <div
      className="px-4 py-2 border-l-2 ml-2 mb-1 space-y-0.5"
      style={{ borderColor: colors.label, backgroundColor: 'rgba(0,191,255,0.03)' }}
    >
      <DetailRow label="Time" value={p.time_utc} />
      <DetailRow label="Frame" value={p.frame || '--'} color={frameColor(p.frame)} />
      <DetailRow label="Src" value={p.src} />
      <DetailRow label="Dest" value={p.dest} />
      <DetailRow label="Echo" value={p.echo} />
      <DetailRow label="Type" value={p.ptype} color={ptypeColor(p.ptype)} />
      <DetailRow label="CRC" value={crc.text} color={crc.color} />
      <DetailRow label="Args" value={argsDisplay(p.args)} />

      {p.warnings.length > 0 && (
        <div className="flex gap-2 text-xs">
          <span className="w-16 shrink-0 text-right" style={{ color: colors.warning }}>Warn</span>
          <span style={{ color: colors.warning }}>{p.warnings.join('; ')}</span>
        </div>
      )}

      {showHex && p.raw_hex && (
        <div className="mt-1">
          <span className="text-xs" style={{ color: colors.dim }}>Hex:</span>
          <pre
            className="text-[10px] mt-0.5 p-1 rounded overflow-x-auto"
            style={{ color: colors.dim, backgroundColor: 'rgba(0,0,0,0.3)' }}
          >
            {p.raw_hex}
          </pre>
        </div>
      )}
    </div>
  )
}
