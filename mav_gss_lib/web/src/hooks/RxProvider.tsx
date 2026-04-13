import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { useRxSocket } from '@/hooks/useRxSocket'
import type { RxPacket } from '@/lib/types'

type RxSocketValue = ReturnType<typeof useRxSocket>
type RxStatsValue = RxSocketValue['stats']
type RxStatusValue = Omit<RxSocketValue, 'packets' | 'stats'>

const RxStatusContext = createContext<RxStatusValue | null>(null)
const RxPacketsContext = createContext<RxPacket[] | null>(null)
const RxStatsContext = createContext<RxStatsValue | null>(null)

export function RxProvider({ children }: { children: ReactNode }) {
  const rx = useRxSocket()
  const { packets, stats, ...rest } = rx

  // `packets` and `stats` change on every 50ms flush. Everything else only
  // changes on rare events (status message, column load, replay toggle,
  // session reset). We memoize `rest` against its slow-changing fields so
  // status subscribers don't rerender 20×/sec under RX traffic.
  const statusValue = useMemo<RxStatusValue>(
    () => rest,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      rest.status,
      rest.connected,
      rest.columns,
      rest.replayMode,
      rest.sessionResetGen,
      rest.sessionResetTag,
      rest.clearPackets,
      rest.replacePackets,
      rest.enterReplay,
      rest.exitReplay,
      rest.subscribeCustom,
    ],
  )

  return (
    <RxStatusContext.Provider value={statusValue}>
      <RxStatsContext.Provider value={stats}>
        <RxPacketsContext.Provider value={packets}>
          {children}
        </RxPacketsContext.Provider>
      </RxStatsContext.Provider>
    </RxStatusContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRxStatus(): RxStatusValue {
  const ctx = useContext(RxStatusContext)
  if (!ctx) throw new Error('useRxStatus must be used within RxProvider')
  return ctx
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRxPackets(): RxPacket[] {
  const ctx = useContext(RxPacketsContext)
  if (ctx === null) throw new Error('useRxPackets must be used within RxProvider')
  return ctx
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRxStats(): RxStatsValue {
  const ctx = useContext(RxStatsContext)
  if (!ctx) throw new Error('useRxStats must be used within RxProvider')
  return ctx
}

/**
 * Legacy combined hook — subscribes to status, packets, AND stats, so the
 * consumer rerenders on every packet flush. Prefer the narrower hooks where
 * possible. Retained for `usePluginServices`, which exposes the full shape
 * to plugin pages.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useRx(): RxSocketValue {
  const status = useRxStatus()
  const packets = useRxPackets()
  const stats = useRxStats()
  return { ...status, packets, stats }
}
