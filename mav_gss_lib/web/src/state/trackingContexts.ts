import { createContext } from 'react'
import type { UseTrackingSocket } from '@/components/radio/useTrackingSocket'
import type { DopplerMode } from '@/lib/types'

export type TrackingValue = UseTrackingSocket
export type TrackingStatusValue = { mode: DopplerMode; error: string }

export const TrackingContext = createContext<TrackingValue | null>(null)
export const TrackingStatusContext = createContext<TrackingStatusValue | null>(null)
