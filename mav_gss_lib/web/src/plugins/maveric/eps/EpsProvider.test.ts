/** EpsProvider state-machine replay test (v2).
 *
 * Drives v2 {type:"telemetry", domain:"eps", changes:{...}, replay?, cleared?}
 * messages into the platform TelemetryProvider (via a mock
 * `subscribeRxCustom`) and asserts EpsProvider's derived state after
 * each event. Exercises: charge-direction hysteresis, latch fire/ack,
 * session reset, cleared-snapshot flow, replay-not-incrementing-counter,
 * prev/current rotation, stale-drop, and unmount/remount survival.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { createElement, type ReactElement } from 'react'

type RxMessage = Record<string, unknown>
type RxSubscriber = (msg: RxMessage) => void

let mockSubscribers: RxSubscriber[] = []
let mockSessionGeneration = 0

// Mock the platform hooks the providers depend on. TelemetryProvider
// reads /api/telemetry/* — stub that too so the test doesn't hit the
// network.
vi.mock('@/hooks/usePluginServices', () => ({
  usePluginRxCustomSubscription: () => (fn: RxSubscriber) => {
    mockSubscribers.push(fn)
    return () => {
      mockSubscribers = mockSubscribers.filter((s) => s !== fn)
    }
  },
}))

vi.mock('@/state/rx', () => ({
  useRxStatus: () => ({ sessionGeneration: mockSessionGeneration, subscribeCustom: () => () => {} }),
}))

globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => null } as Response) as unknown as typeof fetch

// Dynamic imports AFTER mocks are registered.
async function loadStack() {
  const telemetry = await import('@/state/TelemetryProvider')
  const provider = await import('./EpsProvider')
  return { TelemetryProvider: telemetry.TelemetryProvider, ...provider }
}

function wrapProviders(TelemetryProvider: any, EpsProvider: any, child: ReactElement) {
  return createElement(TelemetryProvider, null, createElement(EpsProvider, null, child))
}

function fireTelemetry(changes: Record<string, { v: unknown; t: number }>, opts: { replay?: boolean; cleared?: boolean } = {}) {
  act(() => {
    for (const sub of [...mockSubscribers]) {
      sub({
        type: 'telemetry',
        domain: 'eps',
        ...(opts.cleared ? { cleared: true } : { changes, ...(opts.replay ? { replay: true } : {}) }),
      } as RxMessage)
    }
  })
}

function fieldsToChanges(fields: Record<string, number>, t: number) {
  const out: Record<string, { v: unknown; t: number }> = {}
  for (const [k, v] of Object.entries(fields)) out[k] = { v, t }
  return out
}

async function makeConsumer(useEps: () => unknown) {
  const captured: { value: any } = { value: null }
  function Consumer(): ReactElement {
    captured.value = useEps()
    return createElement('div', { 'data-testid': 'eps-consumer' }, 'ok')
  }
  return { Consumer, captured }
}


describe('EpsProvider — v2 telemetry envelope', () => {
  beforeEach(() => {
    mockSubscribers = []
    mockSessionGeneration = 0
  })

  it('initial state is empty', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))
    expect(screen.getByTestId('eps-consumer')).toBeTruthy()
    expect(captured.value.current).toBeNull()
    expect(captured.value.prev).toBeNull()
    expect(captured.value.receivedThisLink).toBe(0)
    expect(captured.value.chargeDir).toBe('idle')
    expect(captured.value.latched).toEqual({})
  })

  it('first update populates current and derives chargeDir', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges(
      { I_BUS: 0.4, I_BAT: 0.15, V_BUS: 7.6, V_BAT: 7.5, T_DIE: 22.0, VBRN1: 0.0, VBRN2: 0.0 },
      1000,
    ))

    expect(captured.value.current?.received_at_ms).toBe(1000)
    expect(captured.value.current?.fields.V_BAT).toBe(7.5)
    expect(captured.value.prev).toBeNull()
    // First batch out of empty state is a replay → counter stays 0,
    // prev stays null. chargeDir derived from the live value.
    expect(captured.value.receivedThisLink).toBe(0)
    expect(captured.value.chargeDir).toBe('charge')
  })

  it('second update rotates prev and increments receivedThisLink', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0 }, 1000))
    fireTelemetry(fieldsToChanges({ I_BAT: 0.18, V_BAT: 7.52, T_DIE: 22.3 }, 2000))

    expect(captured.value.current?.received_at_ms).toBe(2000)
    expect(captured.value.prev?.received_at_ms).toBe(1000)
    expect(captured.value.receivedThisLink).toBe(1)
  })

  it('stale update is dropped', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0 }, 2000))
    const before = captured.value
    // Older ts: TelemetryProvider's LWW drops the entries before they hit
    // EpsProvider's effect, so there's nothing to see here at the API
    // surface — received_at_ms stays the same, receivedThisLink unchanged.
    fireTelemetry(fieldsToChanges({ V_BAT: 7.4 }, 1500))
    expect(captured.value.current?.received_at_ms).toBe(before.current?.received_at_ms)
    expect(captured.value.receivedThisLink).toBe(before.receivedThisLink)
  })

  it('VBRN latch fires once and is cleared by acknowledgeLatch', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0, VBRN1: 0.2 }, 1000))
    expect(captured.value.latched.VBRN1).toBe(1000)

    // Re-fire at higher ts — already latched, must not rewrite.
    fireTelemetry(fieldsToChanges({ I_BAT: 0.16, V_BAT: 7.5, T_DIE: 22.0, VBRN1: 0.25 }, 2000))
    expect(captured.value.latched.VBRN1).toBe(1000)

    // Acknowledge — entry removed; re-fire allowed to re-latch.
    act(() => { captured.value.acknowledgeLatch('VBRN1') })
    expect('VBRN1' in captured.value.latched).toBe(false)

    fireTelemetry(fieldsToChanges({ I_BAT: 0.16, V_BAT: 7.5, T_DIE: 22.0, VBRN1: 0.3 }, 3000))
    expect(captured.value.latched.VBRN1).toBe(3000)
  })

  it('T_DIE junction latch fires at the 85 °C threshold', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 80.0 }, 1000))
    expect('T_DIE_junction' in captured.value.latched).toBe(false)

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 85.0 }, 2000))
    expect(captured.value.latched.T_DIE_junction).toBe(2000)
  })

  it('cleared domain resets current/prev/latched/chargeDir', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0, VBRN1: 0.2 }, 1000))
    fireTelemetry(fieldsToChanges({ I_BAT: 0.18, V_BAT: 7.52, T_DIE: 22.3 }, 2000))
    expect(captured.value.current).not.toBeNull()
    expect(Object.keys(captured.value.latched).length).toBe(1)

    fireTelemetry({}, { cleared: true })
    expect(captured.value.current).toBeNull()
    expect(captured.value.prev).toBeNull()
    expect(captured.value.latched).toEqual({})
    expect(captured.value.chargeDir).toBe('idle')
  })

  it('replay-on-connect (empty → populated) is treated as replay, not live', async () => {
    // Production case: a fresh client connects, the adapter's
    // on_client_connect fires router.replay(), TelemetryProvider applies
    // it as one batch into an empty eps slice. EpsProvider should NOT
    // increment receivedThisLink on that first batch — the packet
    // happened before this session.
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    render(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0 }, 1000), { replay: true })
    expect(captured.value.current?.received_at_ms).toBe(1000)
    expect(captured.value.receivedThisLink).toBe(0)
    expect(captured.value.prev).toBeNull()

    // Subsequent live packet increments the counter normally.
    fireTelemetry(fieldsToChanges({ I_BAT: 0.18, V_BAT: 7.52, T_DIE: 22.3 }, 2000))
    expect(captured.value.receivedThisLink).toBe(1)
    expect(captured.value.prev?.received_at_ms).toBe(1000)
  })

  it('session reset clears prev and bumps linkGeneration; current persists', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    const { rerender } = render(
      wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)),
    )

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0 }, 1000))
    fireTelemetry(fieldsToChanges({ I_BAT: 0.18, V_BAT: 7.52, T_DIE: 22.3 }, 2000))
    expect(captured.value.prev).not.toBeNull()

    mockSessionGeneration += 1
    act(() => {
      rerender(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))
    })
    expect(captured.value.current?.received_at_ms).toBe(2000)  // persists
    expect(captured.value.prev).toBeNull()
    expect(captured.value.receivedThisLink).toBe(0)
    expect(captured.value.linkGeneration).toBe(1)
    expect(captured.value.chargeDir).toBe('idle')
  })

  it('provider state survives consumer unmount/remount (root-mount invariant)', async () => {
    const { TelemetryProvider, EpsProvider, useEps } = await loadStack()
    const { Consumer, captured } = await makeConsumer(useEps)
    const { rerender } = render(
      wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)),
    )

    fireTelemetry(fieldsToChanges({ I_BAT: 0.15, V_BAT: 7.5, T_DIE: 22.0 }, 1000))
    fireTelemetry(fieldsToChanges({ I_BAT: 0.18, V_BAT: 7.52, T_DIE: 22.3 }, 2000))
    const before = {
      current_t: captured.value.current?.received_at_ms,
      prev_t:    captured.value.prev?.received_at_ms,
      received:  captured.value.receivedThisLink,
    }

    // Swap the consumer for a placeholder, then remount the real consumer.
    rerender(wrapProviders(TelemetryProvider, EpsProvider, createElement('div')))
    rerender(wrapProviders(TelemetryProvider, EpsProvider, createElement(Consumer)))

    expect(captured.value.current?.received_at_ms).toBe(before.current_t)
    expect(captured.value.prev?.received_at_ms).toBe(before.prev_t)
    expect(captured.value.receivedThisLink).toBe(before.received)
  })
})
