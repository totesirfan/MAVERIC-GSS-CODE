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
      className="fixed inset-0 z-50 flex items-center justify-center overflow-auto p-6"
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
          top: '50%', left: '28%', transform: 'translate(-50%, -50%)',
          background: `radial-gradient(circle, ${colors.active}0A 0%, transparent 70%)`,
          animation: running ? 'preflight-pulse 3s ease-in-out infinite' : undefined,
        }}
      />

      <div className="flex flex-col md:flex-row items-center md:items-stretch gap-10 md:gap-12 w-full max-w-5xl relative z-10">
      {/* Hero zone */}
      <div className="flex flex-col items-center md:items-start md:justify-center flex-shrink-0">
        <motion.img
          src="/maveric-patch.webp"
          alt="MAVERIC mission patch"
          className="w-40 h-40 mb-5"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 28px ${colors.active}33)` }}
        />

        <motion.div
          className="flex items-baseline gap-3 mb-3"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <span
            className="text-4xl font-bold tracking-widest"
            style={{ color: colors.textPrimary, fontFamily: 'Inter, sans-serif' }}
          >
            MAVERIC
          </span>
          <span
            className="text-4xl font-bold tracking-widest"
            style={{ color: colors.textPrimary, fontFamily: 'Inter, sans-serif' }}
          >
            GSS
          </span>
        </motion.div>

        <motion.p
          className="text-xs tracking-[0.2em] mb-4"
          style={{ color: colors.textMuted }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
        >
          GROUND STATION SOFTWARE
        </motion.p>

        <motion.div
          className="flex flex-col items-start self-start gap-0.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.35 }}
        >
          <img
            src="/usc-primary-logotype-dark.png"
            alt="University of Southern California primary logotype"
            className="h-auto w-[220px] mb-4 select-none"
            style={{ opacity: 0.96 }}
          />
          <span
            className="text-[14px]"
            style={{
              color: colors.textSecondary,
              fontFamily: '"Adobe Caslon Pro", "Libre Caslon Text", Georgia, "Times New Roman", serif',
              lineHeight: 1.2,
            }}
          >
            <span style={{ color: USC_GOLD }}>S</span>pace{' '}
            <span style={{ color: USC_GOLD }}>E</span>ngineering{' '}
            <span style={{ color: USC_GOLD }}>R</span>esearch{' '}
            <span style={{ color: USC_GOLD }}>C</span>enter
          </span>
        </motion.div>
      </div>

      {/* Check console — sized to fit all checks without scrolling */}
      <motion.div
        className="w-full md:flex-1 md:max-w-2xl md:pl-10 md:border-l"
        style={{ borderColor: colors.borderSubtle }}
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
            className="mt-6 flex flex-col items-center gap-4"
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
      </div>

      <style>{`
        @keyframes preflight-pulse {
          0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 1; transform: translate(-50%, -50%) scale(1.08); }
        }
      `}</style>
    </motion.div>
  )
}
