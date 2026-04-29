import { createContext } from 'react'
import type { useRxSocket } from '@/hooks/useRxSocket'
import type { ParamUpdate, RxPacket } from '@/lib/types'

export type RxSocketValue = ReturnType<typeof useRxSocket>
export type RxStatsValue = RxSocketValue['stats']
export type RxStatusValue = Omit<RxSocketValue, 'packets' | 'stats' | 'packetParametersById'>
export type RxPacketParametersValue = Record<string, ParamUpdate[]>

export interface RxDisplayToggles {
  showHex: boolean
  showFrame: boolean
  showWrapper: boolean
  hideUplink: boolean
  toggleHex: () => void
  toggleFrame: () => void
  toggleWrapper: () => void
  toggleUplink: () => void
}

export const RxDisplayTogglesContext = createContext<RxDisplayToggles | null>(null)
export const RxStatusContext = createContext<RxStatusValue | null>(null)
export const RxPacketsContext = createContext<RxPacket[] | null>(null)
export const RxPacketParametersContext = createContext<RxPacketParametersValue | null>(null)
export const RxStatsContext = createContext<RxStatsValue | null>(null)
