import { Activity, CalendarDays, ChevronDown, CircleHelp, LockKeyhole, LogIn, LogOut, ShieldCheck, SlidersHorizontal, X } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom"
import { login, logout } from "../api"
import { useAuth } from "../state/auth"
import { useBoard } from "../state/board"

export function Shell() {
  const { user, ready, setUser } = useAuth()
  const { filters, data } = useBoard()
  const navigate = useNavigate()
  const [qualityOpen, setQualityOpen] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)
  const closeLogin = useCallback(() => setLoginOpen(false), [])
  const audit = data?.source.audit
  const isAdmin = user?.role === "admin"

  async function signOut() {
    await logout()
    setUser(null)
    navigate("/")
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="Código Naranja by muegan-ing">
          <span className="brand-mark">
            <ShieldCheck size={22} />
          </span>
          <span className="brand-copy">
            <b>
              CÓDIGO <i>/</i> NARANJA
            </b>
            <small>BY MUEGAN-ING · TLAXCALA</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="edition">
            <span className="edition-dot" />
            DATATHON 2026
          </span>
          <button type="button" className="quality-link" onClick={() => setQualityOpen((open) => !open)}>
            <CircleHelp size={15} /> Calidad de datos
          </button>
          <div className="auth-controls">
            {user ? (
              <>
                <span className="user-name" title={user.email}>
                  {user.name || user.email}
                </span>
                <button type="button" className="auth-button secondary" onClick={() => void signOut()}>
                  <LogOut size={14} /> Cerrar sesión
                </button>
              </>
            ) : (
              <button type="button" className="auth-button primary" onClick={() => setLoginOpen(true)} disabled={!ready}>
                <LogIn size={14} /> Iniciar sesión
              </button>
            )}
          </div>
        </div>
      </header>
      <section className="page-intro" id="inicio">
        <div>
          <div className="eyebrow">
            <span className="orange-line" /> INTELIGENCIA TERRITORIAL <span className="eyebrow-slash">/</span> 01 — 2026
          </div>
          <h1>
            Mapa de Saturación <span>&amp; Cobertura</span>
          </h1>
          <p>Demanda de atención y capacidad de servicios para una respuesta más cercana a las mujeres de Tlaxcala.</p>
        </div>
      </section>
      {qualityOpen && (
        <div className="quality-panel">
          <ShieldCheck size={18} />
          <div>
            <b>Calidad y cobertura de los datos</b>
            <p>
              {audit
                ? `${audit.valid} registros válidos de ${audit.processed}; ${audit.removed} filas vacías o duplicadas removidas, ${audit.personDuplicates} alertas duplicadas por persona bloqueadas/consolidadas y ${audit.imputed} valores numéricos imputados con 0. Cada alerta consolidada corresponde al registro más reciente o de mayor prioridad.${data?.source.fileName ? ` Archivo: ${data.source.fileName}.` : ""}`
                : "El tablero refleja únicamente los registros cargados en la fuente activa. Los datos de demostración son sintéticos y no representan cifras oficiales."}
            </p>
          </div>
          <button type="button" aria-label="Cerrar" onClick={() => setQualityOpen(false)}>
            <X size={16} />
          </button>
        </div>
      )}
      <nav className="view-tabs" aria-label="Vistas del tablero">
        <NavLink to="/" end className={({ isActive }) => `tab-link${isActive ? " active" : ""}`}>
          <Activity size={16} /> Tablero territorial
        </NavLink>
        {isAdmin && (
          <NavLink to="/admin" className={({ isActive }) => `tab-link${isActive ? " active" : ""}`}>
            <SlidersHorizontal size={16} /> Administración <span className="tab-suffix">/ Carga de datos</span>
          </NavLink>
        )}
        <span className="tabs-spacer" />
        <span className="period-chip">
          <CalendarDays size={14} />
          {filters.period === "Todos los periodos" ? "Todos los periodos" : `Periodo ${filters.period}`}
          <ChevronDown size={14} />
        </span>
      </nav>
      <Outlet />
      {loginOpen && <LoginDialog onClose={closeLogin} />}
    </main>
  )
}

function LoginDialog({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setBusy(true)
    try {
      const result = await login(email.trim(), password)
      setUser(result.user)
      setPassword("")
      onClose()
      if (result.user?.role === "admin") navigate("/admin")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No fue posible conectar con el servicio de acceso.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="login-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section className="login-dialog" role="dialog" aria-modal="true" aria-labelledby="login-title" aria-describedby="login-description">
        <button type="button" className="login-close" aria-label="Cerrar inicio de sesión" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="login-icon">
          <LockKeyhole size={20} />
        </span>
        <span className="eyebrow">ACCESO RESTRINGIDO</span>
        <h2 id="login-title">Administración</h2>
        <p id="login-description">Inicia sesión con la cuenta administradora para cargar datos del tablero.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>
            Usuario / correo del administrador
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="nombre@ejemplo.mx"
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={12}
              placeholder="Ingresa tu contraseña"
            />
          </label>
          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}
          <button className="button primary login-submit" type="submit" disabled={busy}>
            {busy ? "Verificando…" : "Iniciar sesión"}
          </button>
        </form>
        <small>El acceso administrativo está limitado a la cuenta creada con las variables ADMIN_EMAIL y ADMIN_PASSWORD.</small>
      </section>
    </div>
  )
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth()
  if (!ready) return null
  if (user?.role !== "admin") return <Navigate to="/" replace />
  return children
}
