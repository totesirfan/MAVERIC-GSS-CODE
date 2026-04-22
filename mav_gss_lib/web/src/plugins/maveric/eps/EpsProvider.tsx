/**
 * EpsProvider — root-mounted state for the EPS HK dashboard.
 *
 * Mission-owned (MAVERIC), mounted at the app root by the platform's
 * MissionProviders wrapper. Reads live state from the platform
 * TelemetryProvider via `useTelemetry('eps')` — no direct WS subscription
 * any more. The provider accumulates the derived view model (prev,
 * chargeDir hysteresis, latched warnings, link counters) across
 * navigation so opening the EPS page is never empty.
 *
 * Why root-level and not inside EpsPage:
 *   • The platform TelemetryProvider receives the replay-on-connect
 *     snapshot at app start. A page-local provider would miss the
 *     replay and open blank.
 *   • `prev`, the I_BAT ring buffer, chargeDir hysteresis, and
 *     receivedThisLink accumulate across navigation instead of
 *     resetting on every page mount.
 *   • The provider renders nothing; only React context lives outside
 *     EpsPage, so there is no DOM cost while the page is closed.
 *
 * IMPORTANT — single-consumer rule:
 *   `useEps()` returns ONE context value object. React rerenders every
 *   consumer of that context on any field change. Only `EpsPage.tsx`
 *   should call `useEps()`; it destructures and passes narrow primitive
 *   props down to the 15 memo'd children. Pushing `useEps()` into child
 *   components defeats React.memo and means every packet rerenders the
 *   whole tree.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react'
import { useTelemetry } from '@/state/TelemetryProvider'
import { useRxStatus } from '@/state/rx'
import { chargeDirection } from './derive'
import type { EpsFields, EpsFieldName, EpsSnapshot, ChargeDir } from './types'
import { FIELD_DEFS } from './types'

interface EpsState {
  current: EpsSnapshot | null
  prev: EpsSnapshot | null
  receivedThisLink: number
  linkGeneration: number
  chargeDir: ChargeDir
  // Field name → received_at_ms of the first fire. Populated on
  // VBRN1/VBRN2 > 0.1 V and on T_DIE ≥ 85 °C (junction limit).
  // Survives across page navigation; cleared per-field by
  // acknowledgeLatch() or wholesale by a cleared telemetry domain.
  latched: Record<string, number>
}

interface EpsApi extends EpsState {
  clearSnapshot: () => Promise<void>
  acknowledgeLatch: (field: string) => void
}

const EpsContext = createContext<EpsApi | null>(null)

const INITIAL_STATE: EpsState = {
  current: null,
  prev: null,
  receivedThisLink: 0,
  linkGeneration: 0,
  chargeDir: 'idle',
  latched: {},
}

const LATCH_BURN_FIELDS = ['VBRN1', 'VBRN2'] as const
const LATCH_BURN_THRESHOLD_V = 0.1
const LATCH_T_DIE_JUNCTION_C = 85

const FIELD_NAMES: readonly EpsFieldName[] = FIELD_DEFS.map((d) => d.name)

/** Build an EpsSnapshot view model from a telemetry domain state record.
 *
 *  Returns null when no eps fields are present. received_at_ms is the
 *  max `t` across the 48 entries — because every eps_hk packet emits
 *  all 48 fragments atomically with the same ts_ms, this resolves to
 *  the packet's ingest timestamp.
 */
function buildSnapshot(eps: Record<string, { v?: unknown; t: number }>): EpsSnapshot | null {
  const keys = Object.keys(eps)
  if (keys.length === 0) return null
  let maxT = -Infinity
  const partial: Partial<EpsFields> = {}
  for (const name of FIELD_NAMES) {
    const entry = eps[name]
    if (!entry) continue
    if (entry.t > maxT) maxT = entry.t
    const v = entry.v
    partial[name] = typeof v === 'number' ? v : Number(v)
  }
  // If no field entries were present at all (e.g. only unknown keys
  // populated the domain state), treat as empty.
  if (!Number.isFinite(maxT)) return null
  return {
    received_at_ms: maxT,
    fields: partial as EpsFields,
  }
}

export function EpsProvider({ children }: PropsWithChildren) {
  const eps = useTelemetry('eps')
  const { sessionGeneration } = useRxStatus()
  const [state, setState] = useState<EpsState>(INITIAL_STATE)

  // I_BAT ring buffer for chargeDir hysteresis — kept in a ref so the
  // effect reads fresh values without resubscribing.
  const recentIBatsRef = useRef<number[]>([])

  // Track previously-observed snapshot and whether state was non-empty,
  // both in refs so we can compute transitions without re-running the
  // effect on every unrelated re-render.
  const prevSnapRef = useRef<EpsSnapshot | null>(null)
  const prevNonEmptyRef = useRef<boolean>(false)

  // React to domain-state identity changes (one per ingest batch).
  useEffect(() => {
    const isEmpty = Object.keys(eps).length === 0
    const wasNonEmpty = prevNonEmptyRef.current
    prevNonEmptyRef.current = !isEmpty

    // Transition non-empty → empty: platform cleared the domain.
    // Equivalent to the legacy `eps_snapshot_cleared` hook.
    if (isEmpty) {
      if (wasNonEmpty) {
        prevSnapRef.current = null
        recentIBatsRef.current = []
        setState((s) => ({
          ...s,
          current: null,
          prev: null,
          latched: {},
          chargeDir: 'idle',
        }))
      }
      return
    }

    const snap = buildSnapshot(eps)
    if (!snap) return

    // Drop stale / exact-replay samples — same ts_ms means no new packet.
    const existing = prevSnapRef.current
    if (existing && snap.received_at_ms <= existing.received_at_ms) return

    // Detect replay: first non-empty state after an empty window
    // (either initial mount or a cleared domain). On replay we don't
    // increment receivedThisLink and we don't rotate prev.
    const isReplay = !wasNonEmpty

    // Ring buffer + chargeDir.
    const iBat = snap.fields.I_BAT
    if (typeof iBat === 'number' && Number.isFinite(iBat)) {
      recentIBatsRef.current = [...recentIBatsRef.current, iBat].slice(-3)
    }
    const dir = chargeDirection(
      typeof iBat === 'number' ? iBat : NaN,
      recentIBatsRef.current.slice(0, -1),
    )

    prevSnapRef.current = snap

    setState((s) => {
      // Latch gating: per-field one-shot, acknowledged via UI.
      const newLatched: Record<string, number> = { ...s.latched }
      for (const f of LATCH_BURN_FIELDS) {
        const v = snap.fields[f as keyof EpsFields]
        if (typeof v === 'number' && v > LATCH_BURN_THRESHOLD_V && !(f in newLatched)) {
          newLatched[f] = snap.received_at_ms
        }
      }
      const td = snap.fields.T_DIE
      if (
        typeof td === 'number'
        && td >= LATCH_T_DIE_JUNCTION_C
        && !('T_DIE_junction' in newLatched)
      ) {
        newLatched['T_DIE_junction'] = snap.received_at_ms
      }

      return {
        current: snap,
        prev: isReplay ? s.prev : s.current,
        receivedThisLink: isReplay ? s.receivedThisLink : s.receivedThisLink + 1,
        linkGeneration: s.linkGeneration,
        chargeDir: dir,
        latched: newLatched,
      }
    })
  }, [eps])

  // Session reset: keep `current` (last-known satellite state is
  // deliberately persistent across operator session breaks), clear
  // `prev` and the ring buffer, reset counter, bump link generation.
  // The latch set is NOT cleared — a deployment fault that fired
  // during the previous session is still a real fault the operator
  // has not acknowledged.
  const lastSessionGenRef = useRef(sessionGeneration)
  useEffect(() => {
    if (sessionGeneration === lastSessionGenRef.current) return
    lastSessionGenRef.current = sessionGeneration
    setState((s) => ({
      ...s,
      prev: null,
      receivedThisLink: 0,
      linkGeneration: s.linkGeneration + 1,
      chargeDir: 'idle',
    }))
    recentIBatsRef.current = []
  }, [sessionGeneration])

  const clearSnapshot = useCallback(async () => {
    // Fire-and-forget DELETE against the platform route; server broadcasts
    // `{type:"telemetry", domain:"eps", cleared:true}` which the
    // TelemetryProvider turns into an empty domain state. Our effect
    // above picks the empty transition up and resets local derived state.
    await fetch('/api/telemetry/eps/snapshot', { method: 'DELETE' }).catch(() => {})
  }, [])

  const acknowledgeLatch = useCallback((field: string) => {
    setState((s) => {
      if (!(field in s.latched)) return s
      const next = { ...s.latched }
      delete next[field]
      return { ...s, latched: next }
    })
  }, [])

  const api = useMemo<EpsApi>(
    () => ({ ...state, clearSnapshot, acknowledgeLatch }),
    [state, clearSnapshot, acknowledgeLatch],
  )

  return <EpsContext.Provider value={api}>{children}</EpsContext.Provider>
}

export function useEps(): EpsApi {
  const ctx = useContext(EpsContext)
  if (!ctx) {
    throw new Error(
      'useEps must be used inside <EpsProvider>. '
      + 'Check that plugins/maveric/providers.ts registers EpsProvider.',
    )
  }
  return ctx
}
