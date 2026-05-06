import { createContext } from 'react'
import type { RadioStatus, UseRadioSocket } from '@/components/radio/useRadioSocket'

export type RadioValue = UseRadioSocket
export type RadioStatusValue = { status: RadioStatus; connected: boolean }

export const RadioContext = createContext<RadioValue | null>(null)
export const RadioStatusContext = createContext<RadioStatusValue | null>(null)
