import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { PublicUser } from "../../../../packages/shared/types"
import { getMe } from "../api"

type AuthState = {
  user: PublicUser | null
  ready: boolean
  setUser: (user: PublicUser | null) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<PublicUser | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let active = true
    getMe()
      .then((response) => {
        if (active) setUser(response.user)
      })
      .catch(() => {
        if (active) setUser(null)
      })
      .finally(() => {
        if (active) setReady(true)
      })
    return () => {
      active = false
    }
  }, [])

  const value = useMemo(() => ({ user, ready, setUser }), [user, ready])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth debe usarse dentro de AuthProvider")
  return value
}
