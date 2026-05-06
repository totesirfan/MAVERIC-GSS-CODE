import { useContext } from 'react'
import {
  TrackingContext,
  TrackingStatusContext,
  type TrackingStatusValue,
  type TrackingValue,
} from './trackingContexts'

export function useTracking(): TrackingValue {
  const ctx = useContext(TrackingContext)
  if (!ctx) throw new Error('useTracking must be used within TrackingProvider')
  return ctx
}

export function useTrackingStatus(): TrackingStatusValue {
  const ctx = useContext(TrackingStatusContext)
  if (!ctx) throw new Error('useTrackingStatus must be used within TrackingProvider')
  return ctx
}
