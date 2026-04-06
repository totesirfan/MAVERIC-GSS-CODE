import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { colors } from '@/lib/colors'
import type { Alarm } from '@/hooks/useAlarms'

interface AlarmStripProps {
  alarms: Alarm[]
  onAckAll: () => void
  onAckOne: (id: string) => void
}

const severityColor: Record<string, string> = {
  danger: colors.danger,
  warning: colors.warning,
  advisory: colors.info,
}

export function AlarmStrip({ alarms, onAckAll, onAckOne }: AlarmStripProps) {
  return (
    <AnimatePresence>
      {alarms.length > 0 && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="overflow-hidden shrink-0"
        >
          <div
            className="flex items-center gap-3 px-4 py-1.5 text-xs font-mono animate-pulse-danger"
            style={{
              backgroundColor: colors.dangerFill,
              borderBottom: `1px solid ${colors.danger}40`,
            }}
          >
            <div className="flex items-center gap-1.5 shrink-0">
              <AlertTriangle className="size-3.5" style={{ color: colors.danger }} />
              <span className="font-bold" style={{ color: colors.danger, fontFamily: 'Inter Variable, Inter, sans-serif' }}>
                {alarms.length} {alarms.length === 1 ? 'ALARM' : 'ALARMS'}
              </span>
            </div>

            <div className="w-px h-3.5 shrink-0" style={{ backgroundColor: `${colors.danger}30` }} />

            <div className="flex items-center gap-3 flex-1 min-w-0 overflow-x-auto">
              {alarms.map(a => (
                <button
                  key={a.id}
                  onClick={() => onAckOne(a.id)}
                  className="flex items-center gap-1.5 shrink-0 hover:opacity-70 transition-opacity cursor-pointer"
                  title={`Click to acknowledge: ${a.label}`}
                >
                  <span className="text-[9px]" style={{ color: severityColor[a.severity] }}>●</span>
                  <span className="font-semibold" style={{ color: severityColor[a.severity] }}>{a.label}</span>
                  <span style={{ color: `${severityColor[a.severity]}CC` }}>{a.detail}</span>
                </button>
              ))}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={onAckAll}
              className="shrink-0 h-6 px-2 text-[11px] font-medium"
              style={{ color: colors.textMuted, border: `1px solid ${colors.borderStrong}` }}
            >
              ACK ALL
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
