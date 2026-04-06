import { Send, Reply, CheckCircle, Activity, File, Circle } from 'lucide-react'
import { ptypeTone, toneColor } from '@/lib/colors'

const iconMap: Record<string, React.ElementType> = {
  CMD: Send, REQ: Send,
  RES: Reply,
  ACK: CheckCircle,
  TLM: Activity,
  FILE: File,
}

export function PtypeBadge({ ptype }: { ptype: string | number }) {
  const label = String(ptype)
  const Icon = iconMap[label] ?? Circle
  const tone = ptypeTone(label)
  const fg = toneColor[tone]
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0 rounded-sm border text-[11px] font-medium tracking-wide shrink-0"
      style={{ color: fg, borderColor: `${fg}40`, backgroundColor: `${fg}0A` }}
    >
      <Icon className="size-2.5" />
      {label}
    </span>
  )
}
