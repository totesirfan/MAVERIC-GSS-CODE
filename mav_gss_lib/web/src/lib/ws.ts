import { getAuthToken } from '@/lib/auth'

export function createSocket(
  path: string,
  onMessage: (data: unknown) => void,
  onStatusChange?: (connected: boolean) => void,
): { send: (msg: unknown) => void; close: () => void } {
  let ws: WebSocket | null = null
  let closed = false
  let retryTimeout: ReturnType<typeof setTimeout> | null = null
  let pendingSends: string[] = []

  function flushPending() {
    if (!ws || ws.readyState !== WebSocket.OPEN || pendingSends.length === 0) return
    for (const payload of pendingSends) {
      ws.send(payload)
    }
    pendingSends = []
  }

  async function connect() {
    if (closed) return
    const token = await getAuthToken({ forceRefresh: true })
    if (closed) return
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = new URL(`${proto}//${location.host}${path}`)
    if (token) url.searchParams.set('token', token)
    ws = new WebSocket(url.toString())
    ws.onopen = () => {
      onStatusChange?.(true)
      flushPending()
    }
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch { /* ignore */ }
    }
    ws.onclose = () => {
      onStatusChange?.(false)
      if (!closed) retryTimeout = setTimeout(connect, 2000)
    }
    ws.onerror = () => ws?.close()
  }
  connect()
  return {
    send(msg: unknown) {
      const payload = JSON.stringify(msg)
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(payload)
        return
      }
      pendingSends.push(payload)
      if (pendingSends.length > 20) {
        pendingSends = pendingSends.slice(-20)
      }
    },
    close() {
      closed = true
      pendingSends = []
      if (retryTimeout) clearTimeout(retryTimeout)
      ws?.close()
    },
  }
}
