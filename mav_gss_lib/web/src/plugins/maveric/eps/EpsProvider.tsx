/**
 * EpsProvider — root-mounted state for the EPS HK dashboard.
 *
 * Mission-owned (MAVERIC), mounted at the app root by the platform's
 * MissionProviders wrapper. Subscribes to `/ws/rx` custom messages
 * the moment the app starts and accumulates EPS state continuously,
 * regardless of whether the EPS page is currently rendered.
 *
 * Why root-level and not inside EpsPage:
 *   • /ws/rx connects once at app start, and the adapter's
 *     on_client_connect hook replays the current snapshot at that
 *     moment. If EpsPage mounts later (lazy route), it misses the
 *     replay and opens blank until the next real eps_hk packet.
 *     A root-level provider catches the replay and every live
 *     update, so navigating to EPS is never empty.
 *   • `prev`, the I_BAT ring buffer, `chargeDir` hysteresis, and
 *     `receivedThisLink` accumulate across navigation instead of
 *     resetting on every page mount.
 *   • The provider renders nothing; only React context lives outside
 *     EpsPage, so there is no DOM cost while the page is closed.
 *
 * IMPORTANT — single-consumer rule:
 *   `useEps()` returns ONE context value object. React rerenders
 *   every consumer of that context on any field change. Only
 *   `EpsPage.tsx` should call `useEps()`; it destructures and passes
 *   narrow primitive props down to the 15 memo'd children. Pushing
 *   `useEps()` into child components defeats React.memo and means
 *   every packet rerenders the whole tree. See EpsPage.skeleton.tsx
 *   in docs/eps-port/ for the intended shape.
 *
 * Copy to `mav_gss_lib/web/src/plugins/maveric/eps/EpsProvider.tsx`.
 * Register in `mav_gss_lib/web/src/plugins/maveric/providers.ts`.
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
import { usePluginRxCustomSubscription } from '@/hooks/usePluginServices'
import { useRxStatus } from '@/state/rx'
import { chargeDirection } from './derive'
import type { EpsFields, EpsSnapshot, EpsHkUpdateMsg, ChargeDir } from './types'

interface EpsState {
  current: EpsSnapshot | null
  prev: EpsSnapshot | null
  receivedThisLink: number
  linkGeneration: number
  chargeDir: ChargeDir
  // Field name → received_at_ms of the first fire. Populated on
  // VBRN1/VBRN2 > 0.1 V and on T_DIE ≥ 85 °C (junction limit).
  // Survives across page navigation; cleared per-field by
  // acknowledgeLatch() or wholesale by eps_snapshot_cleared.
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

export function EpsProvider({ children }: PropsWithChildren) {
  // Narrow subscription hook — only subscribes to the custom-message
  // channel. Using `usePluginServices()` here would pull in `useRx()`,
  // which rerenders the provider on every packet flush and defeats
  // the whole point of the provider pattern.
  const subscribeRxCustom = usePluginRxCustomSubscription()
  const { sessionGeneration } = useRxStatus()
  const [state, setState] = useState<EpsState>(INITIAL_STATE)

  // Refs so the subscription callback reads fresh state without
  // resubscribing on every state change (which would drop messages).
  const currentRef = useRef<EpsSnapshot | null>(null)
  const recentIBatsRef = useRef<number[]>([])
  useEffect(() => {
    currentRef.current = state.current
  }, [state.current])

  // Live updates + server-broadcast clear.
  useEffect(() => {
    return subscribeRxCustom((msg) => {
      if (msg.type === 'eps_snapshot_cleared') {
        setState((s) => ({ ...s, current: null, prev: null, latched: {}, chargeDir: 'idle' }))
        recentIBatsRef.current = []
        return
      }
      if (msg.type !== 'eps_hk_update') return
      const update = msg as unknown as EpsHkUpdateMsg
      if (!update.fields || typeof update.received_at_ms !== 'number') return

      // Drop stale and drop replays of what we already have.
      const existing = currentRef.current
      if (existing && update.received_at_ms <= existing.received_at_ms) return

      // Ring buffer, then derive chargeDir off it.
      const iBat = update.fields.I_BAT
      if (typeof iBat === 'number' && Number.isFinite(iBat)) {
        recentIBatsRef.current = [...recentIBatsRef.current, iBat].slice(-3)
      }
      const dir = chargeDirection(
        typeof iBat === 'number' ? iBat : NaN,
        recentIBatsRef.current.slice(0, -1),
      )

      setState((s) => {
        const isReplay = (msg as { replay?: boolean }).replay === true

        // Latch gating: per-field one-shot, acknowledged via UI.
        const newLatched: Record<string, number> = { ...s.latched }
        for (const f of LATCH_BURN_FIELDS) {
          const v = update.fields[f as keyof EpsFields]
          if (typeof v === 'number' && v > LATCH_BURN_THRESHOLD_V && !(f in newLatched)) {
            newLatched[f] = update.received_at_ms
          }
        }
        const td = update.fields.T_DIE
        if (
          typeof td === 'number'
          && td >= LATCH_T_DIE_JUNCTION_C
          && !('T_DIE_junction' in newLatched)
        ) {
          newLatched['T_DIE_junction'] = update.received_at_ms
        }

        const snap: EpsSnapshot = {
          received_at_ms: update.received_at_ms,
          pkt_num: update.pkt_num,
          fields: update.fields,
        }
        return {
          current: snap,
          prev: s.current,
          receivedThisLink: isReplay ? s.receivedThisLink : s.receivedThisLink + 1,
          linkGeneration: s.linkGeneration,
          chargeDir: dir,
          latched: newLatched,
        }
      })
    })
  }, [subscribeRxCustom])

  // Session reset: keep `current` (last-known satellite state is
  // deliberately persistent across operator session breaks), clear
  // `prev` and the ring buffer, reset counter, bump link generation.
  // The latch set is NOT cleared — a deployment fault that fired
  // during the previous session is still a real fault the operator
  // has not acknowledged. They must ack explicitly.
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
    // Fire-and-forget; server broadcasts `eps_snapshot_cleared`
    // which the subscription above handles. Doing it this way
    // avoids the race where a live eps_hk_update arriving during
    // the await would be silently overwritten by an inline reset.
    await fetch('/api/plugins/eps/snapshot', { method: 'DELETE' }).catch(() => {})
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
