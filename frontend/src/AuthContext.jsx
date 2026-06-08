import { createContext, useContext, useState, useEffect } from 'react'
import { auth as authApi, getToken, setToken, clearToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (token) {
      authApi.me().then(setUser).catch(() => clearToken()).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email, password) {
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setUser(res.user)
    return res
  }

  async function register(name, username, email, password) {
    const res = await authApi.register({ name, username, email, password })
    setToken(res.access_token)
    setUser(res.user)
    return res
  }

  async function logout() {
    try { await authApi.logout() } catch {}
    clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
