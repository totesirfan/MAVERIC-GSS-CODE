import { useState, useEffect, useMemo, type ReactNode } from 'react'
import { useSession } from '@/hooks/useSession'
import type { ColumnDef, ColumnDefs, GssConfig, TxColumnDef } from '@/lib/types'
import { SessionContext, type SessionContextValue } from './sessionContexts'

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useSession()
  const [config, setConfig] = useState<GssConfig | null>(null)
  const [columns, setColumns] = useState<ColumnDefs | null>(null)

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((data: GssConfig) => setConfig(data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    Promise.all([
      fetch('/api/tx-columns').then((r) => r.json() as Promise<TxColumnDef[]>),
      fetch('/api/columns').then((r) => r.json() as Promise<ColumnDef[]>),
    ])
      .then(([tx, rx]) => setColumns({ rx, tx }))
      .catch(() => {
        // Keep prior value on transient error rather than stick to null — matches
        // the config path and prevents one flaky boot from blanking column
        // renderers across all main-window consumers for the whole session.
      })
  }, [])

  const value = useMemo<SessionContextValue>(
    () => ({ ...session, config, setConfig, columns }),
    [session, config, columns],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
