import { createContext, useContext, useEffect, useRef, useState, useCallback, ReactNode } from 'react'

const API_BASE = '/api'
const TOKEN_KEY = 'medical_ai_token'
/** Refresh the access token this many milliseconds before it expires. */
const REFRESH_BEFORE_MS = 60_000

interface User {
  id: number
  email: string
  name: string
  avatar_url: string | null
}

interface AuthContextType {
  token: string | null
  user: User | null
  loading: boolean
  login: () => void
  logout: () => void
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>
}

const AuthContext = createContext<AuthContextType | null>(null)

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  const hash = window.location.hash
  if (hash.startsWith('#token=')) {
    const t = hash.slice(7).trim()
    if (t) {
      localStorage.setItem(TOKEN_KEY, t)
      window.history.replaceState(null, '', window.location.pathname)
      return t
    }
  }
  return localStorage.getItem(TOKEN_KEY)
}

/** Parse the `exp` claim from a JWT without verifying the signature. */
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

/** Returns true when the token expires within the next `bufferMs` milliseconds. */
function isTokenExpiringSoon(token: string, bufferMs = REFRESH_BEFORE_MS): boolean {
  const exp = getTokenExpiry(token)
  return exp === null || Date.now() >= exp - bufferMs
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Tracks an in-flight refresh so concurrent 401s don't trigger multiple refreshes.
  const refreshPromiseRef = useRef<Promise<string | null> | null>(null)

  const storeToken = useCallback((t: string | null) => {
    if (t) {
      localStorage.setItem(TOKEN_KEY, t)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
    setToken(t)
  }, [])

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      clearTimeout(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  /** Call /auth/refresh (cookie-based). Returns the new access token or null on failure. */
  const doRefresh = useCallback(async (): Promise<string | null> => {
    if (refreshPromiseRef.current) return refreshPromiseRef.current

    const promise = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    }).then(async (res) => {
      if (!res.ok) return null
      const data = await res.json()
      return data.access_token as string ?? null
    }).catch(() => null)

    refreshPromiseRef.current = promise
    const newToken = await promise
    refreshPromiseRef.current = null
    return newToken
  }, [])

  /** Schedule a proactive silent refresh before the token expires. */
  const scheduleRefresh = useCallback((currentToken: string) => {
    clearRefreshTimer()
    const exp = getTokenExpiry(currentToken)
    if (!exp) return
    const delay = exp - Date.now() - REFRESH_BEFORE_MS
    if (delay <= 0) return
    refreshTimerRef.current = setTimeout(async () => {
      const newToken = await doRefresh()
      if (newToken) {
        storeToken(newToken)
      } else {
        storeToken(null)
        setUser(null)
      }
    }, delay)
  }, [clearRefreshTimer, doRefresh, storeToken])

  const fetchWithAuth = useCallback(
    async (url: string, options: RequestInit = {}): Promise<Response> => {
      let currentToken = token ?? localStorage.getItem(TOKEN_KEY)

      // Proactively refresh if the token is about to expire
      if (currentToken && isTokenExpiringSoon(currentToken)) {
        const refreshed = await doRefresh()
        if (refreshed) {
          storeToken(refreshed)
          currentToken = refreshed
        }
      }

      const headers = new Headers(options.headers)
      if (currentToken) headers.set('Authorization', `Bearer ${currentToken}`)
      const fullUrl = url.startsWith('http') ? url : `${API_BASE}/${url.replace(/^\//, '')}`

      let res = await fetch(fullUrl, { ...options, headers, credentials: 'include' })

      // On 401 attempt one silent refresh and retry
      if (res.status === 401) {
        const refreshed = await doRefresh()
        if (refreshed) {
          storeToken(refreshed)
          const retryHeaders = new Headers(options.headers)
          retryHeaders.set('Authorization', `Bearer ${refreshed}`)
          res = await fetch(fullUrl, { ...options, headers: retryHeaders, credentials: 'include' })
        } else {
          storeToken(null)
          setUser(null)
        }
      }

      return res
    },
    [token, doRefresh, storeToken]
  )

  const loadUser = useCallback(async () => {
    const t = token ?? localStorage.getItem(TOKEN_KEY)
    if (!t) {
      setLoading(false)
      return
    }
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
        credentials: 'include',
      })
      if (res.ok) {
        setUser(await res.json())
        scheduleRefresh(t)
      } else if (res.status === 401) {
        // Access token expired on startup — try refresh before giving up
        const refreshed = await doRefresh()
        if (refreshed) {
          storeToken(refreshed)
          const retry = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${refreshed}` },
            credentials: 'include',
          })
          if (retry.ok) {
            setUser(await retry.json())
            scheduleRefresh(refreshed)
          } else {
            storeToken(null)
          }
        } else {
          storeToken(null)
        }
      } else {
        storeToken(null)
      }
    } catch {
      storeToken(null)
    } finally {
      setLoading(false)
    }
  }, [token, doRefresh, storeToken, scheduleRefresh])

  useEffect(() => {
    if (token) {
      loadUser()
    } else {
      setLoading(false)
    }
    return clearRefreshTimer
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = () => {
    window.location.href = `${window.location.origin}${API_BASE}/auth/google`
  }

  const logout = useCallback(async () => {
    clearRefreshTimer()
    const t = token ?? localStorage.getItem(TOKEN_KEY)
    if (t) {
      // Best-effort server-side revocation
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          headers: { Authorization: `Bearer ${t}` },
        })
      } catch {
        // ignore network errors on logout
      }
    }
    storeToken(null)
    setUser(null)
  }, [token, clearRefreshTimer, storeToken])

  return (
    <AuthContext.Provider
      value={{
        token: token ?? localStorage.getItem(TOKEN_KEY),
        user,
        loading,
        login,
        logout,
        fetchWithAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
