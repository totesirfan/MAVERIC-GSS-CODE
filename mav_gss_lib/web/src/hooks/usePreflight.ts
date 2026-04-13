import { useState, useEffect, useRef, useCallback } from 'react'
import { createSocket } from '@/lib/ws'
import type { PreflightCheck, PreflightSummary } from '@/lib/types'

interface PreflightState {
  checks: PreflightCheck[]
  summary: PreflightSummary | null
  connected: boolean
  rerun: () => void
}

export function usePreflight(): PreflightState {
  const [checks, setChecks] = useState<PreflightCheck[]>([])
  const [summary, setSummary] = useState<PreflightSummary | null>(null)
  const [connected, setConnected] = useState(false)
  const socketRef = useRef<ReturnType<typeof createSocket> | null>(null)

  useEffect(() => {
    const sock = createSocket(
      '/ws/preflight',
      (data: unknown) => {
        const msg = data as Record<string, unknown>
        if (msg.type === 'check') {
          setChecks(prev => [...prev, msg as unknown as PreflightCheck])
        } else if (msg.type === 'summary') {
          setSummary(msg as unknown as PreflightSummary)
        } else if (msg.type === 'reset') {
          setChecks([])
          setSummary(null)
        }
      },
      (isConnected: boolean) => {
        setConnected(isConnected)
        // Reset local state on every (re)connect so the backlog replay
        // the server sends on open does not duplicate prior-run results.
        if (isConnected) {
          setChecks([])
          setSummary(null)
        }
      },
    )
    socketRef.current = sock
    return () => sock.close()
  }, [])

  const rerun = useCallback(() => {
    socketRef.current?.send({ action: 'rerun' })
  }, [])

  return { checks, summary, connected, rerun }
}
