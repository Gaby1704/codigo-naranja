import { AlertTriangle, ArrowUpRight, BarChart3, Filter, Gauge, HeartHandshake, Map, MapPin, RefreshCw, Table2, Users } from "lucide-react"
import { useState } from "react"
import { ActionTable } from "../components/ActionTable"
import { Charts, GeneralComparisonCard } from "../components/Charts"
import { MapPanel } from "../components/MapPanel"
import { fmt } from "../lib/format"
import { filters as labels } from "../lib/shared"
import { useBoard } from "../state/board"

export function DashboardView() {
  const { filters, setFilters, data, loading, error } = useBoard()
  const [selected, setSelected] = useState("Apizaco")
  const [activeTab, setActiveTab] = useState<"overview" | "charts" | "table">("overview")
  const [filtersOpen, setFiltersOpen] = useState(false)

  const summaries = data?.summaries ?? []
  const totalCases = data?.totalCases ?? 0
  const totalCapacity = data?.totalCapacity ?? 0
  const totalPeople = data?.totalPeople ?? 0
  const totalRecords = data?.totalRecords ?? 0
  const demandExceeds = totalCases / Math.max(totalCapacity, 1) > 1
  const missingTotal = (data?.missingCasesCount ?? 0) + (data?.missingCapacityCount ?? 0)
  const naTotal = (data?.naCasesCount ?? 0) + (data?.naCapacityCount ?? 0)
  const activeFiltersCount =
    (filters.period !== labels.defaultPeriod ? 1 : 0) +
    (filters.municipality !== labels.allZones ? 1 : 0) +
    (filters.violence !== labels.allViolence ? 1 : 0) +
    (filters.service !== labels.allServices ? 1 : 0)

  return (
    <>
      <section className={`filters-row ${filtersOpen ? "filters-open" : ""}`}>
        <span className="filters-label">
          <Filter size={13} /> FILTRAR
        </span>
        <button type="button" className="mobile-filter-toggle" onClick={() => setFiltersOpen((open) => !open)}>
          <Filter size={15} /> Filtros {activeFiltersCount > 0 ? `(${activeFiltersCount})` : ""}
        </button>
        <label className="filter-select">
          <span>PERIODO DE CORTE</span>
          <select value={filters.period} onChange={(event) => setFilters({ ...filters, period: event.target.value })}>
            <option>{labels.allPeriods}</option>
            {(data?.periods ?? []).map((period) => (
              <option key={period}>{period}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span>MUNICIPIO (HECHO)</span>
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
            <span>CASOS vs. EXPEDIENTES</span>
            <span className="kpi-icon burgundy">
              <Users size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {fmt(totalCases)}
            <span className="kpi-unit">casos</span>
          </div>
          <div className="kpi-foot">
            <span className="kpi-trend">
              <ArrowUpRight size={12} /> {data?.hasPersonIds ? `${fmt(totalPeople)} personas únicas` : `${fmt(totalRecords)} registros`}
            </span>
            <span>{data?.hasPersonIds ? `${fmt(totalRecords)} filas` : "agregado"}</span>
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span>SERVICIOS / ATENCIONES</span>
            <span className="kpi-icon violet">
              <HeartHandshake size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {fmt(totalCapacity)}
            <span className="kpi-unit">atenciones</span>
          </div>
          <div className="kpi-foot">
            <span>{naTotal > 0 ? `${naTotal} N/A excluidos` : "Capacidad registrada"}</span>
            <span>{missingTotal > 0 ? `${missingTotal} faltantes` : "en selección"}</span>
          </div>
        </article>
        <article className="kpi-card">
          <div className="kpi-top">
            <span>BRECHA RELATIVA</span>
            <span className="kpi-icon orange">
              <Gauge size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {totalCapacity > 0 ? `${Math.round((totalCases / totalCapacity) * 100)}%` : totalCases > 0 ? "Sin cap." : "0%"}
            <span className="kpi-unit">demanda / capacidad</span>
          </div>
          <div className="kpi-foot">
            <span className={demandExceeds ? "text-priority" : "text-stable"}>
              {totalCases > totalCapacity ? "Demanda supera capacidad" : "Capacidad sobre demanda"}
            </span>
            <span>{data?.hasResidenceDistinction ? "hecho vs. residencia" : "registros"}</span>
          </div>
        </article>
        <article className="kpi-card priority-kpi">
          <div className="kpi-top">
            <span>ZONAS PRIORITARIAS</span>
            <span className="kpi-icon priority-icon">
              <MapPin size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {data?.priorityCount ?? 0}
            <span className="kpi-unit">municipios</span>
          </div>
          <div className="kpi-foot">
            <span className="kpi-trend orange-trend">
              <AlertTriangle size={12} /> Atención prioritaria
            </span>
            <span>en selección</span>
          </div>
        </article>
      </section>

      <nav className="dashboard-tabs" role="tablist" aria-label="Vistas principales del tablero">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "overview"}
          className={activeTab === "overview" ? "active" : ""}
          onClick={() => setActiveTab("overview")}
        >
          <Map size={15} /> Mapa y gráfica general
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "charts"}
          className={activeTab === "charts" ? "active" : ""}
          onClick={() => setActiveTab("charts")}
        >
          <BarChart3 size={15} /> Gráficas
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "table"}
          className={activeTab === "table" ? "active" : ""}
          onClick={() => setActiveTab("table")}
        >
          <Table2 size={15} /> Tabla
        </button>
      </nav>

      <div className="dashboard-workspace">
        {activeTab === "overview" && (
          <div className="overview-grid">
            <MapPanel
              summaries={summaries}
              selected={selected}
              hasPersonIds={data?.hasPersonIds ?? false}
              hasResidenceDistinction={data?.hasResidenceDistinction ?? false}
              onSelect={setSelected}
            />
            <GeneralComparisonCard
              summaries={summaries}
              selected={selected}
              maxRows={10}
              onSelect={setSelected}
              onShowAll={() => {
                setFilters({ ...filters, municipality: labels.allZones })
                setActiveTab("charts")
              }}
            />
          </div>
        )}

        {activeTab === "charts" && (
          <Charts
            summaries={summaries}
            trends={data?.trends ?? []}
            forecast={data?.forecast}
            selected={selected}
            latestPeriod={data?.periods.at(-1) ?? "—"}
            missingTotal={missingTotal}
            naTotal={naTotal}
            onSelect={setSelected}
            onShowAll={() => setFilters({ ...filters, municipality: labels.allZones })}
          />
        )}

        {activeTab === "table" && (
          <ActionTable
            summaries={summaries}
            hasPersonIds={data?.hasPersonIds ?? false}
            hasResidenceDistinction={data?.hasResidenceDistinction ?? false}
            selected={selected}
            onSelect={setSelected}
          />
        )}
      </div>

      <footer className="disclaimer">
        <span className="disclaimer-icon">
          <AlertTriangle size={14} />
        </span>
        <p>
          <strong>Criterio BANAVIM / Tlaxcala:</strong> Un expediente único puede agrupar múltiples casos o seguimientos. Mayor volumen indica acercamiento institucional o cobertura, no mayor incidencia poblacional.
        </p>
        <span className="footer-brand">
          CÓDIGO NARANJA <i>·</i> BY MUEGAN-ING
        </span>
      </footer>
    </>
  )
}
