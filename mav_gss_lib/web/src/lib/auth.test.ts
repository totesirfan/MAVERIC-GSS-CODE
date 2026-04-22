import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('auth token helpers', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.restoreAllMocks()
  })

  it('caches the token until a forced refresh is requested', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        json: async () => ({ auth_token: 'token-a' }),
      } as Response)
      .mockResolvedValueOnce({
        json: async () => ({ auth_token: 'token-b' }),
      } as Response)
    vi.stubGlobal('fetch', fetchMock)

    const { getAuthToken } = await import('./auth')

    await expect(getAuthToken()).resolves.toBe('token-a')
    await expect(getAuthToken()).resolves.toBe('token-a')
    await expect(getAuthToken({ forceRefresh: true })).resolves.toBe('token-b')

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/status', { cache: 'no-store' })
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/status', { cache: 'no-store' })
  })

  it('retries authFetch once after a 403 with a refreshed token', async () => {
    const forbidden = { status: 403 } as Response
    const ok = { status: 200 } as Response

    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        json: async () => ({ auth_token: 'stale-token' }),
      } as Response)
      .mockResolvedValueOnce(forbidden)
      .mockResolvedValueOnce({
        json: async () => ({ auth_token: 'fresh-token' }),
      } as Response)
      .mockResolvedValueOnce(ok)
    vi.stubGlobal('fetch', fetchMock)

    const { authFetch } = await import('./auth')

    const response = await authFetch('/api/config', { method: 'PUT' })

    expect(response).toBe(ok)
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/config', {
      method: 'PUT',
      headers: expect.any(Headers),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/config', {
      method: 'PUT',
      headers: expect.any(Headers),
    })

    const firstHeaders = fetchMock.mock.calls[1][1]?.headers as Headers
    const retryHeaders = fetchMock.mock.calls[3][1]?.headers as Headers
    expect(firstHeaders.get('X-GSS-Token')).toBe('stale-token')
    expect(retryHeaders.get('X-GSS-Token')).toBe('fresh-token')
  })
})
