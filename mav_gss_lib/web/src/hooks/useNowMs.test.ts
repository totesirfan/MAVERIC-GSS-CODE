import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useNowMs } from './useNowMs'

describe('useNowMs', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-24T00:00:00Z'))
  })
  afterEach(() => { vi.useRealTimers() })

  it('returns the current wall time on mount', () => {
    const { result } = renderHook(() => useNowMs())
    expect(result.current).toBe(Date.now())
  })

  it('updates approximately every second', () => {
    const { result } = renderHook(() => useNowMs())
    const start = result.current
    act(() => { vi.advanceTimersByTime(1001) })
    expect(result.current).toBeGreaterThanOrEqual(start + 1000)
  })
})

describe('useNowMs — module-level subscription', () => {
  it('two consumers tick in lock-step from a single interval', async () => {
    vi.useFakeTimers()
    const { renderHook, act } = await import('@testing-library/react')
    const r1 = renderHook(() => useNowMs())
    const r2 = renderHook(() => useNowMs())
    const before1 = r1.result.current
    const before2 = r2.result.current
    expect(before1).toBe(before2)

    // Advance timers + flush React effects inside act so subscriber
    // notifications and state updates land before assertions.
    await act(async () => {
      vi.advanceTimersByTime(1000)
      await Promise.resolve()
    })

    expect(r1.result.current).toBe(r2.result.current)
    expect(r1.result.current).toBeGreaterThan(before1)
    vi.useRealTimers()
  })

  it('a late subscriber matches existing peers without waiting for the next tick', async () => {
    vi.useFakeTimers()
    const { renderHook, act } = await import('@testing-library/react')
    const r1 = renderHook(() => useNowMs())
    // Advance into the middle of a tick window — peer 1 stays on its
    // initial value until the next interval fires.
    await act(async () => {
      vi.advanceTimersByTime(1000)
      await Promise.resolve()
    })
    const peerNow = r1.result.current
    // Move 250 ms further (still inside the next 1 s window — no tick fires).
    await act(async () => {
      vi.advanceTimersByTime(250)
      await Promise.resolve()
    })
    expect(r1.result.current).toBe(peerNow) // no new tick yet

    // Mount a late subscriber. It must initialize to peerNow (NOT a
    // fresh Date.now() that would diverge from peer 1).
    const r2 = renderHook(() => useNowMs())
    await act(async () => { await Promise.resolve() })
    expect(r2.result.current).toBe(peerNow)
    expect(r1.result.current).toBe(r2.result.current)

    vi.useRealTimers()
  })
})
