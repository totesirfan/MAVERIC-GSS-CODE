import { useState, useCallback, useMemo } from 'react'
import { useDebouncedValue } from './useDebouncedValue'
import { useColumnDefs } from '@/state/session'
import type { ColumnDef } from '@/lib/types'

type LogEntry = Record<string, unknown>
const PAGE_SIZE = 200

const NUM_COL: ColumnDef = { id: 'num', label: '#', align: 'right', width: 'w-9' }
const TIME_COL: ColumnDef = { id: 'time', label: 'time', width: 'w-[68px]' }
const SIZE_COL: ColumnDef = { id: 'size', label: 'size', align: 'right', width: 'w-10' }

export function useLogQuery() {
  const [sessions, setSessions] = useState<Record<string, unknown>[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [currentOffset, setCurrentOffset] = useState(0)

  const [cmdFilter, setCmdFilter] = useState('')
  const [fromTime, setFromTime] = useState('')
  const [toTime, setToTime] = useState('')
  const [dateFilter, setDateFilter] = useState('')

  const debouncedCmd = useDebouncedValue(cmdFilter, 300)
  const debouncedFrom = useDebouncedValue(fromTime, 300)
  const debouncedTo = useDebouncedValue(toTime, 300)

  // Columns come from SessionProvider. LogViewer is only ever mounted in the
  // main window (behind the Logs button), so context is always available here.
  // Wrap mission TX columns with platform-owned num/time/size prefix+suffix for
  // the log viewer's display convention.
  const { defs: ctxDefs } = useColumnDefs()
  const rxColumns = ctxDefs?.rx ?? []
  const txColumns = useMemo<ColumnDef[]>(() => {
    const mission = ctxDefs?.tx ?? []
    return [NUM_COL, TIME_COL, ...mission, SIZE_COL]
  }, [ctxDefs])

  const fetchSessions = useCallback(() => {
    fetch('/api/logs')
      .then((r) => r.json())
      .then((data: Record<string, unknown>[]) => setSessions(data))
      .catch(() => {})
  }, [])

  const fetchEntries = useCallback((sessionId: string, append = false, offsetOverride = 0) => {
    setLoading(true)
    const params = new URLSearchParams()
    if (debouncedCmd) params.set('cmd', debouncedCmd)
    if (debouncedFrom) params.set('from', debouncedFrom)
    if (debouncedTo) params.set('to', debouncedTo)
    params.set('offset', String(offsetOverride))
    params.set('limit', String(PAGE_SIZE))
    fetch(`/api/logs/${sessionId}?${params.toString()}`)
      .then((r) => r.json())
      .then((data: { entries: LogEntry[]; has_more: boolean }) => {
        setEntries(prev => append ? [...prev, ...data.entries] : data.entries)
        setHasMore(data.has_more)
        setCurrentOffset(offsetOverride + data.entries.length)
        setLoading(false)
      })
      .catch(() => {
        setEntries([])
        setHasMore(false)
        setCurrentOffset(0)
        setLoading(false)
      })
  }, [debouncedCmd, debouncedFrom, debouncedTo])

  const reset = useCallback(() => {
    setSelected(null)
    setEntries([])
    setCmdFilter('')
    setFromTime('')
    setToTime('')
    setDateFilter('')
    setHasMore(false)
    setCurrentOffset(0)
  }, [])

  return {
    sessions,
    selected,
    setSelected,
    entries,
    loading,
    hasMore,
    currentOffset,
    cmdFilter,
    setCmdFilter,
    fromTime,
    setFromTime,
    toTime,
    setToTime,
    dateFilter,
    setDateFilter,
    debouncedCmd,
    debouncedFrom,
    debouncedTo,
    rxColumns,
    txColumns,
    fetchSessions,
    fetchEntries,
    reset,
  }
}
