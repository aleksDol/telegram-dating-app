import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import type { User } from '../types'
import { isApiConfigured, api } from '../api/client'
import { useTelegram } from '../hooks/useTelegram'

/** ID демо-пользователя для режима просмотра без регистрации */
export const DEMO_USER_ID = 0

type AppState = {
  user: User | null
  loading: boolean
  error: string | null
  isDemo: boolean
  /** Показывать демо-события на страницах событий (для зарегистрированных, когда с API пусто) */
  useDemoEvents: boolean
  setUser: (u: User | null) => void
  setUseDemoEvents: (v: boolean) => void
  fetchUser: () => Promise<void>
  logout: () => void
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const { userId } = useTelegram()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [useDemoEvents, setUseDemoEvents] = useState(false)

  const fetchUser = useCallback(async () => {
    if (!isApiConfigured()) {
      setLoading(false)
      setUser(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { user: u } = await api.getUser()
      setUser(u ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    setUser(null)
  }, [])

  return (
    <AppContext.Provider
      value={{
        user,
        loading,
        error,
        isDemo: user?.user_id === DEMO_USER_ID,
        useDemoEvents,
        setUser,
        setUseDemoEvents,
        fetchUser,
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
