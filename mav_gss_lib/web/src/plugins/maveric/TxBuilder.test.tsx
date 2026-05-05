import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MavericTxBuilder from './TxBuilder'
import { setLastDestNode } from './txBuilderState'

const schema = {
  com_ping: {
    tx_args: [],
    nodes: ['LPPM'],
  },
  eps_get_temp: {
    tx_args: [],
    description: 'Read EPS temperature sensor',
    nodes: ['UPPM'],
  },
  eps_set_mode: {
    tx_args: [],
    description: 'Set EPS subsystem mode',
    nodes: ['UPPM'],
  },
  toggle_hex_display: {
    tx_args: [],
    description: 'Toggle hex display',
    nodes: ['UPPM'],
  },
  ax_keep_alive: {
    tx_args: [],
    description: 'Keep AX100 link alive between passes',
    nodes: ['UPPM'],
  },
}

const identity = {
  mission_name: 'MAVERIC',
  nodes: {
    GS: '0',
    LPPM: '1',
    UPPM: '2',
  },
  ptypes: {},
  node_descriptions: {},
  gs_node: 'GS',
}

function mockBuilderFetch() {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/schema') {
      return Promise.resolve(new Response(JSON.stringify(schema)))
    }
    if (url === '/api/plugins/maveric/identity') {
      return Promise.resolve(new Response(JSON.stringify(identity)))
    }
    return Promise.reject(new Error(`Unexpected fetch: ${url}`))
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  })
  Element.prototype.scrollIntoView = vi.fn()
  setLastDestNode(null)
})

describe('MavericTxBuilder', () => {
  it('queues a no-arg command when Enter is pressed on the focused Queue button', async () => {
    mockBuilderFetch()
    const onQueue = vi.fn()

    render(<MavericTxBuilder onQueue={onQueue} onClose={() => {}} />)

    fireEvent.click(await screen.findByText('com_ping'))

    const queueButton = await screen.findByRole('button', { name: /queue/i })
    await waitFor(() => expect(document.activeElement).toBe(queueButton))

    fireEvent.keyDown(queueButton, { key: 'Enter' })

    expect(onQueue).toHaveBeenCalledTimes(1)
    expect(onQueue).toHaveBeenCalledWith({
      cmd_id: 'com_ping',
      args: {},
      packet: { dest: 'LPPM' },
      guard: false,
    })
  })

  it('restores the last picked destination node after unmount', async () => {
    mockBuilderFetch()

    const first = render(<MavericTxBuilder onQueue={() => {}} onClose={() => {}} />)
    await screen.findByText('com_ping')

    fireEvent.click(screen.getByRole('radio', { name: 'UPPM' }))
    // UPPM-scoped commands become visible only after the dest filter switches.
    await screen.findByText('eps_get_temp')
    expect(screen.queryByText('com_ping')).toBeNull()
    first.unmount()

    render(<MavericTxBuilder onQueue={() => {}} onClose={() => {}} />)
    await screen.findByText('eps_get_temp')
    expect(screen.queryByText('com_ping')).toBeNull()
  })

  it('ranks fuzzy matches with name above description-only hits', async () => {
    mockBuilderFetch()

    render(<MavericTxBuilder onQueue={() => {}} onClose={() => {}} />)
    await screen.findByText('com_ping')

    fireEvent.click(screen.getByRole('radio', { name: 'UPPM' }))
    await waitFor(() => screen.getByText('eps_get_temp'))

    const searchBox = screen.getByPlaceholderText('Search commands...')
    fireEvent.change(searchBox, { target: { value: 'eps' } })

    await waitFor(() => {
      const items = screen.getAllByRole('option').map((el) => el.textContent ?? '')
      // Both eps_* commands rank ahead of the description-only "ax_keep_alive"
      // (its description mentions "passes" — fuzzy hit on "eps" via subsequence
      // is allowed but must lose to real name matches).
      const epsIdx = items.findIndex((t) => t.includes('eps_get_temp'))
      const axIdx = items.findIndex((t) => t.includes('ax_keep_alive'))
      expect(epsIdx).toBeGreaterThanOrEqual(0)
      if (axIdx >= 0) expect(epsIdx).toBeLessThan(axIdx)
    })
  })
})
