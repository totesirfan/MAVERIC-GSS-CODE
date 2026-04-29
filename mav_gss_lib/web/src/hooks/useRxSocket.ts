import { useEffect, useRef, useState, useCallback } from 'react'
import { createSocket } from '@/lib/ws'
import type { ParamUpdate, RxPacket, RxStatus } from '@/lib/types'
import {
  createEmptyStats,
  RxPacketBuffer,
  type RxBatchEvent,
  type RxPacketEvent,
  type RxPacketStats,
} from './rxSocketState'

const MAX_PACKETS = 5000
const FLUSH_INTERVAL_MS = 50

export function useRxSocket() {
  const [packets, setPackets] = useState<RxPacket[]>([])
  const [packetParametersById, setPacketParametersById] = useState<Record<string, ParamUpdate[]>>({})
  const [status, setStatus] = useState<RxStatus>({ zmq: 'DOWN', pkt_rate: 0, silence_s: 0 })
  const [connected, setConnected] = useState(false)
  const [stats, setStats] = useState<RxPacketStats>(() => createEmptyStats())
  const socketRef = useRef<ReturnType<typeof createSocket> | null>(null)
  const packetBufferRef = useRef(new RxPacketBuffer(MAX_PACKETS))
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const customListenersRef = useRef<Set<(msg: Record<string, unknown>) => void>>(new Set())
  const [sessionGeneration, setSessionGeneration] = useState(0)
  const [sessionTag, setSessionTag] = useState('')
  const [blackoutUntil, setBlackoutUntil] = useState<number | null>(null)

  const syncVisiblePackets = useCallback(() => {
    if (flushTimerRef.current) {
      clearTimeout(flushTimerRef.current)
      flushTimerRef.current = null
    }
    const snapshot = packetBufferRef.current.snapshot()
    setPackets(snapshot.packets)
    setPacketParametersById(snapshot.parametersById)
    setStats(snapshot.stats)
  }, [])

  const scheduleFlush = useCallback(() => {
    if (flushTimerRef.current) return
    flushTimerRef.current = setTimeout(() => {
      syncVisiblePackets()
    }, FLUSH_INTERVAL_MS)
  }, [syncVisiblePackets])

  useEffect(() => {
    const sock = createSocket(
      '/ws/rx',
      (data) => {
        const msg = data as Record<string, unknown>
        const notifyCustom = (message: Record<string, unknown>) => {
          for (const listener of customListenersRef.current) {
            listener(message)
          }
        }
        if (msg.type === 'rx_packet' && msg.packet) {
          const event = msg as unknown as RxPacketEvent
          packetBufferRef.current.add(event)
          scheduleFlush()
          notifyCustom(msg)
        } else if (msg.type === 'rx_batch') {
          const batch = msg as unknown as RxBatchEvent
          for (const event of batch.events ?? []) {
            packetBufferRef.current.add(event)
            notifyCustom(event as unknown as Record<string, unknown>)
          }
          scheduleFlush()
        } else if (msg.type === 'session_new') {
          packetBufferRef.current.clear()
          setPackets([])
          setPacketParametersById({})
          setStats(createEmptyStats())
          setBlackoutUntil(null)
          setSessionTag((msg as Record<string, unknown>).session_tag as string ?? 'untitled')
          setSessionGeneration((msg as Record<string, unknown>).session_generation as number ?? 0)
        } else if (msg.type === 'session_renamed') {
          setSessionTag((msg as Record<string, unknown>).session_tag as string ?? 'untitled')
        } else if (msg.type === 'status') {
          setStatus({
            zmq: (msg.zmq as string) || 'DOWN',
            pkt_rate: (msg.pkt_rate as number) || 0,
            silence_s: (msg.silence_s as number) || 0,
          })
        } else if (msg.type === 'blackout') {
          const rawMs = (msg as { ms?: unknown }).ms
          const ms = typeof rawMs === 'number' ? rawMs : 0
          if (ms > 0) {
            setBlackoutUntil(performance.now() + ms)
          } else {
            // Explicit clear from the backend (operator disabled the feature
            // while a prior window was still running). Null the deadline so
            // the pill hides immediately instead of finishing the old countdown.
            setBlackoutUntil(null)
          }
        } else {
          notifyCustom(msg)
        }
      },
      setConnected,
    )
    socketRef.current = sock
    return () => {
      if (flushTimerRef.current) clearTimeout(flushTimerRef.current)
      sock.close()
    }
  }, [scheduleFlush])

  const clearPackets = useCallback(() => {
    packetBufferRef.current.clear()
    setPackets([])
    setPacketParametersById({})
    setStats(createEmptyStats())
  }, [])

  const subscribeCustom = useCallback((fn: (msg: Record<string, unknown>) => void) => {
    customListenersRef.current.add(fn)
    return () => { customListenersRef.current.delete(fn) }
  }, [])

  return { packets, packetParametersById, status, connected, stats, clearPackets, sessionGeneration, sessionTag, subscribeCustom, blackoutUntil }
}
