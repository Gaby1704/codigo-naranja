import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { Dashboard } from "../../../../packages/shared/types"
import { getDashboard } from "../api"
import { filters as labels, type Filters } from "../lib/shared"

type BoardState = {
  filters: Filters
  setFilters: (filters: Filters) => void
  data: Dashboard | null
  loading: boolean
  error: string
  reload: () => void
}

const BoardContext = createContext<BoardState | null>(null)

const initialFilters: Filters = {
  period: "",
  year: "",
  month: "Todos",
  day: "Todos",
  municipality: labels.allZones,
  violence: labels.allViolence,
  service: labels.allServices,
}

export function BoardProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const [data, setData] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError("")
    getDashboard(filters, controller.signal)
      .then((dashboard) => {
        if (!controller.signal.aborted) setData(dashboard)
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setError(reason instanceof Error ? reason.message : "No se pudo cargar el tablero.")
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [filters, version])

  const value = useMemo<BoardState>(
    () => ({
      filters,
      setFilters,
      data,
      loading,
      error,
      reload: () => setVersion((current) => current + 1),
    }),
    [filters, data, loading, error],
  )

  return <BoardContext.Provider value={value}>{children}</BoardContext.Provider>
}

export function useBoard() {
  const value = useContext(BoardContext)
  if (!value) throw new Error("useBoard debe usarse dentro de BoardProvider")
  return value
}
