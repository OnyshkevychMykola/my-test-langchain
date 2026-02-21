import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'

const API_BASE = '/api'
const TOKEN_KEY = 'medical_ai_token'

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchWithAuth = useCallback(
    async (url: string, options: RequestInit = {}) => {
      const t = token ?? localStorage.getItem(TOKEN_KEY)
      const headers = new Headers(options.headers)
      if (t) headers.set('Authorization', `Bearer ${t}`)
      const path = url.replace(/^\//, '')
return fetch(url.startsWith('http') ? url : `${API_BASE}/${path}`, { ...options, headers })
    },
    [token]
  )

  const loadUser = useCallback(async () => {
    const t = token ?? localStorage.getItem(TOKEN_KEY)
    if (!t) {
      setLoading(false)
      return
    }
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${t}` } })
      if (res.ok) setUser(await res.json())
      else setToken(null)
    } catch {
      setToken(null)
    } finally {
      setLoading(false)
    }
  }, [token])


  useEffect(() => {
    if (token) loadUser()
    else setLoading(false)
  }, [token, loadUser])

  const login = () => {
    window.location.href = `${window.location.origin}${API_BASE}/auth/google`
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token: token ?? localStorage.getItem(TOKEN_KEY), user, loading, login, logout, fetchWithAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
