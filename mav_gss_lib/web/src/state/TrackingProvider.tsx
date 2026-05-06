import { useMemo, type ReactNode } from 'react'
import { useTrackingSocket } from '@/components/radio/useTrackingSocket'
import { TrackingContext, TrackingStatusContext, type TrackingStatusValue } from './trackingContexts'

export function TrackingProvider({ children }: { children: ReactNode }) {
  const tracking = useTrackingSocket()
  // Narrow slot for consumers (e.g. header pill) that only need
  // mode/error — doppler frame updates re-render `tracking` but leave these stable.
  const statusValue = useMemo<TrackingStatusValue>(
    () => ({ mode: tracking.mode, error: tracking.error }),
    [tracking.mode, tracking.error],
  )
  return (
    <TrackingStatusContext.Provider value={statusValue}>
      <TrackingContext.Provider value={tracking}>{children}</TrackingContext.Provider>
    </TrackingStatusContext.Provider>
  )
}
