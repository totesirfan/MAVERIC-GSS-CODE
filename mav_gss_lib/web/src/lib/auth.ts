let authToken: string | null = null
let authTokenPromise: Promise<string> | null = null

export async function getAuthToken(): Promise<string> {
  if (authToken) return authToken
  if (!authTokenPromise) {
    authTokenPromise = fetch('/api/status')
      .then((r) => r.json())
      .then((data: { auth_token?: string }) => {
        authToken = String(data.auth_token ?? '')
        return authToken
      })
      .catch(() => '')
  }
  return authTokenPromise
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = await getAuthToken()
  const headers = new Headers(init.headers ?? {})
  if (token) headers.set('X-GSS-Token', token)
  return fetch(input, { ...init, headers })
}
