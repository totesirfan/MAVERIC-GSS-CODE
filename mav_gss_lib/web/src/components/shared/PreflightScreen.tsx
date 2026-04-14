import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, AlertTriangle, Minus, Loader2 } from 'lucide-react'
import { colors } from '@/lib/colors'
import type {
  PreflightCheck,
  PreflightSummary,
  UpdatePhase,
  UpdateProgress,
  UpdatesCheckMeta,
  UpdateUIState,
} from '@/lib/types'

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
  updates: 'Updates',
}

const PHASE_LABELS: Record<UpdatePhase, string> = {
  git_pull:       'git pull',
  pip_install:    'pip install',
  bootstrap_venv: 'bootstrap venv',
  restart:        'restart',
}

// Ordered phase list for rendering the applying/failed state.
const PHASE_ORDER: UpdatePhase[] = ['git_pull', 'bootstrap_venv', 'pip_install', 'restart']

// USC brand colors (official Cardinal & Gold) — https://identity.usc.edu/color/
const USC_GOLD     = '#FFCC00'

interface Props {
  checks: PreflightCheck[]
  summary: PreflightSummary | null
  connected: boolean
  dismissing: boolean
  onContinue: () => void
  onRerun: () => void
  updateState: UpdateUIState
  updatePhases: Record<UpdatePhase, UpdateProgress>
  onShowConfirm: () => void
  onCancelConfirm: () => void
  onApplyUpdate: () => void
  onReloadPage: () => void
}

export function PreflightScreen({
  checks,
  summary,
  connected,
  dismissing,
  onContinue,
  onRerun,
  updateState,
  updatePhases,
  onShowConfirm,
  onCancelConfirm,
  onApplyUpdate,
  onReloadPage,
}: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, PreflightCheck[]>()
    for (const c of checks) {
      const arr = map.get(c.group) || []
      arr.push(c)
      map.set(c.group, arr)
    }
    return map
  }, [checks])

  // "All passed" requires no failures AND no warnings AND no skips.
  // summary.ready only tracks failures, so we tighten the check for the
  // visible label/button tone — e.g., an offline-skipped update check should
  // not render as "ALL CHECKS PASSED" just because nothing failed.
  const skipped = summary?.skipped ?? 0
  const allPassed =
    summary?.ready === true &&
    summary.warnings === 0 &&
    skipped === 0
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
                  className={groupId === 'updates' ? 'col-span-2' : undefined}
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
                  {groupId === 'updates' && (
                    <UpdatesGroupExtras
                      meta={(groupChecks[0]?.meta as UpdatesCheckMeta | null | undefined) ?? null}
                      updateState={updateState}
                      updatePhases={updatePhases}
                      onShowConfirm={onShowConfirm}
                      onCancelConfirm={onCancelConfirm}
                      onApplyUpdate={onApplyUpdate}
                      onReloadPage={onReloadPage}
                    />
                  )}
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
                : `${summary.failed} FAILED · ${summary.warnings} WARN${skipped > 0 ? ` · ${skipped} SKIP` : ''}`}
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

// =============================================================================
//  Updates group extras — button, confirm panel, phase list, failed/reloading
// =============================================================================

interface UpdatesExtrasProps {
  meta: UpdatesCheckMeta | null
  updateState: UpdateUIState
  updatePhases: Record<UpdatePhase, UpdateProgress>
  onShowConfirm: () => void
  onCancelConfirm: () => void
  onApplyUpdate: () => void
  onReloadPage: () => void
}

function UpdatesGroupExtras({
  meta,
  updateState,
  updatePhases,
  onShowConfirm,
  onCancelConfirm,
  onApplyUpdate,
  onReloadPage,
}: UpdatesExtrasProps) {
  // idle — render button if meta says so
  if (updateState === 'idle') {
    if (!meta || meta.button !== 'apply') return null
    const disabled = meta.button_disabled
    return (
      <div className="mt-2 flex flex-col gap-1">
        <button
          disabled={disabled}
          onClick={disabled ? undefined : onShowConfirm}
          className="w-48 text-[11px] py-1.5 rounded tracking-widest"
          style={{
            color: disabled ? colors.textDisabled : colors.success,
            border: `1px solid ${disabled ? colors.borderStrong : colors.success}66`,
            background: 'transparent',
            fontFamily: 'JetBrains Mono, monospace',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          APPLY UPDATE
        </button>
        {disabled && meta.button_reason && (
          <span className="text-[10px]" style={{ color: colors.textMuted }}>
            {meta.button_reason}
          </span>
        )}
      </div>
    )
  }

  // confirming — header, commit list, planned phases, CONFIRM/CANCEL
  if (updateState === 'confirming' && meta) {
    const header = meta.behind_count > 0
      ? `Apply ${meta.behind_count} commit${meta.behind_count === 1 ? '' : 's'}?`
      : 'Install Python dependencies?'

    // Mutually-exclusive pip bullet branches — match backend phase-skip logic.
    const pipBullet: string | null = (() => {
      if (meta.missing_pip_deps.length > 0) {
        return `pip install -r requirements.txt (${meta.missing_pip_deps.length} new package${meta.missing_pip_deps.length === 1 ? '' : 's'})`
      }
      if (meta.requirements_changed) {
        return 'pip install -r requirements.txt (refresh)'
      }
      if (meta.requirements_out_of_sync) {
        return 'retry pip install -r requirements.txt (last install incomplete)'
      }
      return null
    })()

    return (
      <div className="mt-3 space-y-2">
        <div
          className="text-[11px]"
          style={{ color: colors.textPrimary, fontFamily: 'Inter, sans-serif' }}
        >
          {header}
        </div>
        {meta.behind_count > 0 && meta.commits.length > 0 && (
          <div
            className="max-h-32 overflow-auto text-[11px] space-y-0.5 pr-2"
            style={{
              color: colors.textSecondary,
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {meta.commits.map((c) => (
              <div key={c.sha}>
                <span style={{ color: colors.textMuted }}>{c.sha}</span>
                {'  '}
                {c.subject}
              </div>
            ))}
          </div>
        )}
        <div
          className="text-[11px] space-y-0.5"
          style={{ color: colors.textSecondary, fontFamily: 'JetBrains Mono, monospace' }}
        >
          <div style={{ color: colors.textMuted }}>This will:</div>
          {meta.behind_count > 0 && (
            <div>• git pull origin {meta.branch}</div>
          )}
          {pipBullet && <div>• {pipBullet}</div>}
          <div>• restart MAV_WEB.py</div>
        </div>
        <div className="flex gap-2 pt-1">
          <button
            onClick={onApplyUpdate}
            className="text-[11px] px-4 py-1.5 rounded tracking-widest"
            style={{
              color: colors.bgApp,
              background: colors.success,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            CONFIRM
          </button>
          <button
            onClick={onCancelConfirm}
            className="text-[11px] px-4 py-1.5 rounded tracking-widest"
            style={{
              color: colors.textSecondary,
              border: `1px solid ${colors.borderStrong}`,
              background: 'transparent',
              fontFamily: 'JetBrains Mono, monospace',
              cursor: 'pointer',
            }}
          >
            CANCEL
          </button>
        </div>
      </div>
    )
  }

  // applying / failed / reloading — phase list
  if (updateState === 'applying' || updateState === 'failed' || updateState === 'reloading') {
    return (
      <div className="mt-3 space-y-2">
        <PhaseList updatePhases={updatePhases} />
        {updateState === 'reloading' && (
          <div
            className="flex items-center gap-2 text-[11px]"
            style={{ color: colors.textSecondary, fontFamily: 'JetBrains Mono, monospace' }}
          >
            <Loader2 size={12} className="animate-spin" style={{ color: colors.active }} />
            Restarting...
          </div>
        )}
        {updateState === 'failed' && (
          <button
            onClick={onReloadPage}
            className="text-[11px] px-4 py-1.5 rounded tracking-widest"
            style={{
              color: colors.warning,
              border: `1px solid ${colors.warning}66`,
              background: 'transparent',
              fontFamily: 'JetBrains Mono, monospace',
              cursor: 'pointer',
            }}
          >
            RELOAD
          </button>
        )}
      </div>
    )
  }

  return null
}

function PhaseList({ updatePhases }: { updatePhases: Record<UpdatePhase, UpdateProgress> }) {
  // Only show phases that are running, ok, or fail — pending phases are dim
  // and shown after the first active one fires.
  const hasAnyActive = PHASE_ORDER.some((p) => updatePhases[p].status !== 'pending')
  return (
    <div className="space-y-0.5">
      {PHASE_ORDER.map((phase) => {
        const st = updatePhases[phase]
        if (!hasAnyActive && st.status === 'pending') return null
        const label = PHASE_LABELS[phase]
        let Icon: typeof Loader2 = Minus
        let color: string = colors.neutral
        let spin = false
        if (st.status === 'running') {
          Icon = Loader2
          color = colors.active
          spin = true
        } else if (st.status === 'ok') {
          Icon = Check
          color = colors.success
        } else if (st.status === 'fail') {
          Icon = X
          color = colors.danger
        } else {
          // pending
          Icon = Minus
          color = colors.textDisabled
        }
        return (
          <div key={phase} className="flex items-start gap-2 py-px">
            <Icon
              size={12}
              className={spin ? 'animate-spin' : undefined}
              style={{ color, marginTop: 2, flexShrink: 0 }}
            />
            <div className="min-w-0 flex-1">
              <span
                className="text-[11px]"
                style={{ color, fontFamily: 'JetBrains Mono, monospace' }}
              >
                {label}
              </span>
              {st.detail && (
                <div
                  className="text-[10px] truncate"
                  style={{ color: colors.textMuted, fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {st.detail}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
