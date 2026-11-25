import { AlertTriangle, ArrowUpRight, BarChart3, Filter, Gauge, HeartHandshake, Map, MapPin, RefreshCw, Table2, Users } from "lucide-react"
import { useState } from "react"
import { ActionTable } from "../components/ActionTable"
import { Charts, GeneralComparisonCard } from "../components/Charts"
import { MapPanel } from "../components/MapPanel"
import { SearchableSelect } from "../components/SearchableSelect"
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
  const hasCapacityData = data?.hasCapacityData ?? true
  const demandExceeds = hasCapacityData && totalCases / Math.max(totalCapacity, 1) > 1
  const missingTotal = (data?.missingCasesCount ?? 0) + (data?.missingCapacityCount ?? 0)
  const naTotal = (data?.naCasesCount ?? 0) + (data?.naCapacityCount ?? 0)
  const dimLabels = data?.dimensionLabels ?? {
    zone: "Municipio (hecho)",
    period: "Periodo de corte",
    violence: "Tipo de violencia",
    service: "Tipo de servicio",
    cases: "Casos registrados",
    capacity: "Atenciones / capacidad",
  }

  const periodOptions = [labels.allPeriods, ...(data?.periods ?? [])]
  const zoneOptions = [labels.allZones, ...(data?.municipalities ?? [])]
  const violenceOptions = [labels.allViolence, ...(data?.violenceTypes ?? [])]
  const serviceOptions = [labels.allServices, ...(data?.serviceTypes ?? [])]

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
        <div className="filter-select">
          <span>{dimLabels.period.toUpperCase()}</span>
          <SearchableSelect
            ariaLabel={dimLabels.period}
            value={filters.period}
            options={periodOptions}
            onChange={(value) => setFilters({ ...filters, period: value })}
          />
        </div>
        <div className="filter-select">
          <span>{dimLabels.zone.toUpperCase()}</span>
          <SearchableSelect
            ariaLabel={dimLabels.zone}
            value={filters.municipality}
            options={zoneOptions}
            onChange={(value) => setFilters({ ...filters, municipality: value })}
          />
        </div>
        <div className="filter-select">
          <span>{dimLabels.violence.toUpperCase()}</span>
          <SearchableSelect
            ariaLabel={dimLabels.violence}
            value={filters.violence}
            options={violenceOptions}
            onChange={(value) => setFilters({ ...filters, violence: value })}
          />
        </div>
        <div className="filter-select">
          <span>{dimLabels.service.toUpperCase()}</span>
          <SearchableSelect
            ariaLabel={dimLabels.service}
            value={filters.service}
            options={serviceOptions}
            onChange={(value) => setFilters({ ...filters, service: value })}
          />
        </div>
        <button
          type="button"
          className="reset-filter"
          onClick={() =>
            setFilters({
              period: (data?.periods ?? []).includes(labels.defaultPeriod) ? labels.defaultPeriod : labels.allPeriods,
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
            <span>{dimLabels.capacity.toUpperCase()}</span>
            <span className="kpi-icon violet">
              <HeartHandshake size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {hasCapacityData ? fmt(totalCapacity) : "N/A"}
            <span className="kpi-unit">{hasCapacityData ? "atenciones" : "sin columna"}</span>
          </div>
          <div className="kpi-foot">
            <span>{naTotal > 0 ? `${naTotal} N/A excluidos` : hasCapacityData ? "Capacidad registrada" : "Métrica no incluida"}</span>
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
            {!hasCapacityData ? "N/A" : totalCapacity > 0 ? `${Math.round((totalCases / totalCapacity) * 100)}%` : totalCases > 0 ? "Sin cap." : "0%"}
            <span className="kpi-unit">{hasCapacityData ? "demanda / capacidad" : "sin cobertura"}</span>
          </div>
          <div className="kpi-foot">
            <span className={demandExceeds ? "text-priority" : "text-stable"}>
              {!hasCapacityData
                ? "Solo conteo de casos"
                : totalCases > totalCapacity
                  ? "Demanda supera capacidad"
                  : "Capacidad sobre demanda"}
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
            {hasCapacityData ? (data?.priorityCount ?? 0) : summaries.length}
            <span className="kpi-unit">{hasCapacityData ? "municipios" : "grupos activos"}</span>
          </div>
          <div className="kpi-foot">
            <span className="kpi-trend orange-trend">
              <AlertTriangle size={12} /> {hasCapacityData ? "Atención prioritaria" : "Cobertura por grupo"}
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
            dynamicBreakdowns={data?.dynamicBreakdowns ?? []}
            dynamicMetrics={data?.dynamicMetrics ?? []}
            hasCapacityData={hasCapacityData}
            selected={selected}
            latestPeriod={data?.periods.at(-1) ?? "—"}
            missingTotal={missingTotal}
            naTotal={naTotal}
            onSelect={setSelected}
            onShowAll={() => setFilters({ ...filters, municipality: labels.allZones })}
            onFilterBy={(field, val) => setFilters({ ...filters, [field]: val })}
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
