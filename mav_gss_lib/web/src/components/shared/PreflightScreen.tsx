import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, AlertTriangle, Minus, Loader2 } from 'lucide-react'
import { colors } from '@/lib/colors'
import type { PreflightCheck, PreflightSummary } from '@/lib/types'

const STATUS_ICON = {
  ok: Check,
  fail: X,
  warn: AlertTriangle,
  skip: Minus,
} as const

const STATUS_COLOR = {
  ok: colors.success,
  fail: colors.danger,
  warn: colors.warning,
  skip: colors.neutral,
} as const

const GROUP_LABELS: Record<string, string> = {
  python_deps: 'Python Dependencies',
  gnuradio: 'GNU Radio / PMT',
  config: 'Config Files',
  web_build: 'Web Build',
  zmq: 'ZMQ Addresses',
}

// USC brand colors (official Cardinal & Gold) — https://identity.usc.edu/color/
const USC_CARDINAL = '#990000'
const USC_GOLD     = '#FFCC00'

interface Props {
  checks: PreflightCheck[]
  summary: PreflightSummary | null
  connected: boolean
  dismissing: boolean
  onContinue: () => void
  onRerun: () => void
}

export function PreflightScreen({ checks, summary, connected, dismissing, onContinue, onRerun }: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, PreflightCheck[]>()
    for (const c of checks) {
      const arr = map.get(c.group) || []
      arr.push(c)
      map.set(c.group, arr)
    }
    return map
  }, [checks])

  const allPassed = summary?.ready === true
  const hasFails = summary ? summary.failed > 0 : false
  const running = !summary && connected && checks.length > 0

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{
        backgroundColor: dismissing ? 'transparent' : 'rgba(8, 8, 8, 0.88)',
        backdropFilter: dismissing ? 'blur(0px)' : 'blur(10px)',
        WebkitBackdropFilter: dismissing ? 'blur(0px)' : 'blur(10px)',
      }}
      animate={dismissing ? { opacity: 0 } : { opacity: 1 }}
      transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Ambient glow behind logo */}
      <div
        className="absolute pointer-events-none"
        style={{
          width: 380, height: 380,
          top: '28%', left: '50%', transform: 'translate(-50%, -50%)',
          background: `radial-gradient(circle, ${colors.active}0A 0%, transparent 70%)`,
          animation: running ? 'preflight-pulse 3s ease-in-out infinite' : undefined,
        }}
      />

      {/* Hero zone */}
      <div className="flex flex-col items-center mb-8 relative z-10">
        <motion.img
          src="/maveric-patch.webp"
          alt="MAVERIC mission patch"
          className="w-56 h-56 mb-6"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 28px ${colors.active}33)` }}
        />

        <motion.div
          className="flex items-baseline gap-4 mb-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <span
            className="text-5xl font-bold tracking-widest"
            style={{ color: colors.textPrimary, fontFamily: 'Inter, sans-serif' }}
          >
            MAVERIC
          </span>
          <span
            className="text-5xl font-bold tracking-widest"
            style={{ color: colors.textPrimary, fontFamily: 'Inter, sans-serif' }}
          >
            GSS
          </span>
        </motion.div>

        <motion.p
          className="text-sm tracking-[0.2em] mb-5"
          style={{ color: colors.textMuted }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
        >
          GROUND STATION SOFTWARE
        </motion.p>

        <motion.div
          className="flex flex-col items-center gap-0.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.35 }}
        >
          <span className="text-xs tracking-wide font-semibold" style={{ color: USC_CARDINAL }}>
            UNIVERSITY OF SOUTHERN CALIFORNIA
          </span>
          <span className="text-xs tracking-wide" style={{ color: USC_GOLD }}>
            SPACE ENGINEERING RESEARCH CENTER
          </span>
        </motion.div>
      </div>

      {/* Check console — sized to fit all checks without scrolling */}
      <motion.div
        className="w-full max-w-xl px-6 relative z-10"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
      >
        {!connected && checks.length === 0 && (
          <div className="flex items-center justify-center gap-2 py-4">
            <Loader2 size={14} className="animate-spin" style={{ color: colors.neutral }} />
            <span className="text-xs" style={{ color: colors.neutral, fontFamily: 'JetBrains Mono, monospace' }}>
              Connecting...
            </span>
          </div>
        )}

        {checks.length > 0 && (
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            <AnimatePresence mode="popLayout">
              {Array.from(groups.entries()).map(([groupId, groupChecks]) => (
                <motion.div
                  key={groupId}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div
                    className="text-[10px] uppercase tracking-[0.18em] mb-1.5"
                    style={{ color: colors.neutral }}
                  >
                    {GROUP_LABELS[groupId] || groupId}
                  </div>
                  <div className="space-y-0.5">
                    {groupChecks.map((check, i) => {
                      const Icon = STATUS_ICON[check.status] || Minus
                      const color = STATUS_COLOR[check.status] || colors.neutral
                      return (
                        <motion.div
                          key={`${groupId}-${i}`}
                          initial={{ opacity: 0, x: -4 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.12, delay: i * 0.02 }}
                          className="flex items-start gap-2 py-px"
                        >
                          <Icon size={12} style={{ color, marginTop: 2, flexShrink: 0 }} />
                          <div className="min-w-0">
                            <span
                              className="text-xs"
                              style={{
                                color: check.status === 'ok' ? colors.textSecondary : color,
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {check.label}
                              {check.detail ? ` — ${check.detail}` : ''}
                            </span>
                            {check.fix && check.status !== 'ok' && (
                              <div className="text-[10px] mt-px" style={{ color: colors.dim }}>
                                {check.fix}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )
                    })}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}

        {running && (
          <div className="flex items-center gap-2 pt-3 justify-center">
            <Loader2 size={12} className="animate-spin" style={{ color: colors.active }} />
            <span className="text-[10px]" style={{ color: colors.textMuted, fontFamily: 'JetBrains Mono, monospace' }}>
              Running checks...
            </span>
          </div>
        )}

        {summary && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="mt-6 pt-4 flex flex-col items-center gap-4"
            style={{ borderTop: `1px solid ${colors.borderSubtle}` }}
          >
            <span
              className="text-xs tracking-wider"
              style={{
                color: allPassed ? colors.success : hasFails ? colors.danger : colors.warning,
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              {allPassed
                ? 'ALL CHECKS PASSED'
                : `${summary.failed} FAILED · ${summary.warnings} WARN`}
            </span>
            <div className="flex flex-col items-center gap-2">
              <button
                onClick={onContinue}
                className="w-40 text-xs py-2 rounded cursor-pointer transition-colors tracking-widest"
                style={{
                  color: allPassed ? colors.bgApp : colors.textPrimary,
                  background: allPassed ? colors.success : 'transparent',
                  border: allPassed ? 'none' : `1px solid ${colors.borderStrong}`,
                  fontWeight: allPassed ? 700 : 500,
                }}
              >
                {allPassed ? 'LAUNCH' : 'CONTINUE ANYWAY'}
              </button>
              {!allPassed && (
                <button
                  onClick={onRerun}
                  className="w-40 text-[10px] py-1.5 rounded cursor-pointer transition-colors tracking-widest"
                  style={{
                    color: colors.textSecondary,
                    border: `1px solid ${colors.borderStrong}`,
                    background: 'transparent',
                  }}
                >
                  RERUN
                </button>
              )}
            </div>
          </motion.div>
        )}
      </motion.div>

      <style>{`
        @keyframes preflight-pulse {
          0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 1; transform: translate(-50%, -50%) scale(1.08); }
        }
      `}</style>
    </motion.div>
  )
}
