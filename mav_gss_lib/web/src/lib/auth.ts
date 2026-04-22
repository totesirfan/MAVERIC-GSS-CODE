let authToken: string | null = null
let authTokenPromise: Promise<string> | null = null

interface AuthTokenOptions {
  forceRefresh?: boolean
}

function loadAuthToken(): Promise<string> {
  const pending = fetch('/api/status', { cache: 'no-store' })
    .then((r) => r.json())
    .then((data: { auth_token?: string }) => {
      authToken = String(data.auth_token ?? '')
      return authToken
    })
    .catch(() => {
      authToken = ''
      return ''
    })
    .finally(() => {
      if (authTokenPromise === pending) authTokenPromise = null
    })
  authTokenPromise = pending
  return pending
}

export async function getAuthToken(options: AuthTokenOptions = {}): Promise<string> {
  if (options.forceRefresh) return loadAuthToken()
  if (authToken !== null) return authToken
  if (authTokenPromise) return authTokenPromise
  return loadAuthToken()
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const firstToken = await getAuthToken()
  const firstHeaders = new Headers(init.headers ?? {})
  if (firstToken) firstHeaders.set('X-GSS-Token', firstToken)

  const firstResponse = await fetch(input, { ...init, headers: firstHeaders })
  if (firstResponse.status !== 403) return firstResponse

  const refreshedToken = await getAuthToken({ forceRefresh: true })
  if (!refreshedToken || refreshedToken === firstToken) return firstResponse

  const retryHeaders = new Headers(init.headers ?? {})
  retryHeaders.set('X-GSS-Token', refreshedToken)
  return fetch(input, { ...init, headers: retryHeaders })
}
