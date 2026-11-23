import { AlertTriangle, ArrowUpRight, Filter, Gauge, HeartHandshake, MapPin, RefreshCw, Users } from "lucide-react"
import { useState } from "react"
import { ActionTable } from "../components/ActionTable"
import { Charts } from "../components/Charts"
import { MapPanel } from "../components/MapPanel"
import { fmt } from "../lib/format"
import { filters as labels } from "../lib/shared"
import { useBoard } from "../state/board"

export function DashboardView() {
  const { filters, setFilters, data, loading, error } = useBoard()
  const [selected, setSelected] = useState("Apizaco")
  const [mobileView, setMobileView] = useState<"map" | "charts" | "table">("map")
  const [filtersOpen, setFiltersOpen] = useState(false)
  const summaries = data?.summaries ?? []
  const totalCases = data?.totalCases ?? 0
  const totalCapacity = data?.totalCapacity ?? 0
  const demandExceeds = totalCases / Math.max(totalCapacity, 1) > 1

  return (
    <>
      <section className={`filters-row ${filtersOpen ? "filters-open" : ""}`}>
        <span className="filters-label">
          <Filter size={14} /> FILTRAR
        </span>
        <button type="button" className="mobile-filter-toggle" onClick={() => setFiltersOpen((open) => !open)}>
          <Filter size={15} /> Filtros
        </button>
        <label className="filter-select">
          <span>PERIODO</span>
          <select value={filters.period} onChange={(event) => setFilters({ ...filters, period: event.target.value })}>
            <option>{labels.allPeriods}</option>
            {(data?.periods ?? []).map((period) => (
              <option key={period}>{period}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span>ZONA / MUNICIPIO</span>
          <select value={filters.municipality} onChange={(event) => setFilters({ ...filters, municipality: event.target.value })}>
            <option>{labels.allZones}</option>
            {(data?.municipalities ?? []).map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span>TIPO DE VIOLENCIA</span>
          <select value={filters.violence} onChange={(event) => setFilters({ ...filters, violence: event.target.value })}>
            <option>{labels.allViolence}</option>
            {(data?.violenceTypes ?? []).map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span>TIPO DE SERVICIO</span>
          <select value={filters.service} onChange={(event) => setFilters({ ...filters, service: event.target.value })}>
            <option>{labels.allServices}</option>
            {(data?.serviceTypes ?? []).map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="reset-filter"
          onClick={() =>
            setFilters({
              period: labels.defaultPeriod,
              municipality: labels.allZones,
              violence: labels.allViolence,
              service: labels.allServices,
            })
          }
        >
          <RefreshCw size={13} /> Limpiar
        </button>
      </section>
      {error && (
        <div className="notice" role="alert">
          {error}
        </div>
      )}
      {loading && !data && <div className="notice">Cargando tablero…</div>}
      <section className="kpi-grid" aria-label="Indicadores clave">
        <article className="kpi-card">
          <div className="kpi-top">
            <span>CASOS REGISTRADOS</span>
            <span className="kpi-icon burgundy">
              <Users size={17} />
            </span>
          </div>
          <div className="kpi-value">
            {fmt(totalCases)}
            <span className="kpi-unit">casos</span>
          </div>
          <div className="kpi-foot">
            <span className="kpi-trend">
              <ArrowUpRight size={13} /> Registros activos
            </span>
            <span>en selección</span>
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span>SERVICIOS / ATENCIONES REGISTRADAS</span>
            <span className="kpi-icon violet">
              <HeartHandshake size={17} />
            </span>
          </div>
          <div className="kpi-value">
            {fmt(totalCapacity)}
            <span className="kpi-unit">atenciones</span>
          </div>
          <div className="kpi-foot">
            <span>Frecuencia acumulada</span>
            <span>en selección</span>
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span>BRECHA RELATIVA DE ATENCIÓN</span>
            <span className="kpi-icon orange">
              <Gauge size={17} />
            </span>
          </div>
          <div className="kpi-value">
            {totalCapacity ? `${Math.round((totalCases / totalCapacity) * 100)}%` : "—"}
            <span className="kpi-unit">demanda / capacidad</span>
          </div>
          <div className="kpi-foot">
            <span className={demandExceeds ? "text-priority" : "text-stable"}>
              {totalCases > totalCapacity ? "Demanda supera capacidad" : "Capacidad sobre demanda"}
            </span>
            <span>estimado</span>
          </div>
        </article>
        <article className="kpi-card priority-kpi">
          <div className="kpi-top">
            <span>ZONAS PRIORITARIAS</span>
            <span className="kpi-icon priority-icon">
              <MapPin size={17} />
            </span>
          </div>
          <div className="kpi-value">
            {data?.priorityCount ?? 0}
            <span className="kpi-unit">municipios</span>
          </div>
          <div className="kpi-foot">
            <span className="kpi-trend orange-trend">
              <AlertTriangle size={13} /> Atención prioritaria
            </span>
            <span>unidad móvil</span>
          </div>
        </article>
      </section>
      <nav className="mobile-dashboard-tabs" aria-label="Secciones del tablero">
        <button type="button" className={mobileView === "map" ? "active" : ""} onClick={() => setMobileView("map")}>
          Mapa
        </button>
        <button type="button" className={mobileView === "charts" ? "active" : ""} onClick={() => setMobileView("charts")}>
          Gráficas
        </button>
        <button type="button" className={mobileView === "table" ? "active" : ""} onClick={() => setMobileView("table")}>
          Tabla operativa
        </button>
      </nav>
      <div className={`main-grid mobile-view-${mobileView}`}>
        <MapPanel summaries={summaries} selected={selected} onSelect={setSelected} />
        <Charts
          summaries={summaries}
          trends={data?.trends ?? []}
          selected={selected}
          latestPeriod={data?.periods.at(-1) ?? "—"}
          onSelect={setSelected}
          onShowAll={() => setFilters({ ...filters, municipality: labels.allZones })}
        />
      </div>
      <ActionTable className={`mobile-view-${mobileView}`} summaries={summaries} selected={selected} onSelect={setSelected} />
      <footer className="disclaimer">
        <span className="disclaimer-icon">
          <AlertTriangle size={15} />
        </span>
        <p>
          <strong>Nota de rigor analítico.</strong> Cada alerta/caso representa a una persona única según su identificador o expediente. Los resultados reflejan exclusivamente los registros disponibles en la base activa; no representan necesariamente la totalidad de la población ni la incidencia real. Las zonas con pocos registros podrían presentar subregistro.
        </p>
        <span className="footer-brand">
          CÓDIGO NARANJA <i>·</i> BY MUEGAN-ING
        </span>
      </footer>
    </>
  )
}
