import { createContext } from 'react'
import type { SessionState } from '@/hooks/useSession'
import type { ColumnDefs, GssConfig } from '@/lib/types'

export interface SessionContextValue extends SessionState {
  config: GssConfig | null
  setConfig: (c: GssConfig) => void
  columns: ColumnDefs | null
}

export const SessionContext = createContext<SessionContextValue | null>(null)
