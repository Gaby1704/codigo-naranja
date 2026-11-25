import { AlertTriangle, BarChart3, Database, Filter, Gauge, HeartHandshake, Map, MapPin, RefreshCw, Table2, Upload, Users } from "lucide-react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ActionTable } from "../components/ActionTable"
import { Charts, GeneralComparisonCard } from "../components/Charts"
import { MapPanel } from "../components/MapPanel"
import { SearchableSelect, type SelectOption } from "../components/SearchableSelect"
import { fmt, humanizeColumnLabel } from "../lib/format"
import { filters as labels } from "../lib/shared"
import { useAuth } from "../state/auth"
import { useBoard } from "../state/board"

const MONTH_NAMES: Record<string, string> = {
  "01": "01 · Enero",
  "02": "02 · Febrero",
  "03": "03 · Marzo",
  "04": "04 · Abril",
  "05": "05 · Mayo",
  "06": "06 · Junio",
  "07": "07 · Julio",
  "08": "08 · Agosto",
  "09": "09 · Septiembre",
  "10": "10 · Octubre",
  "11": "11 · Noviembre",
  "12": "12 · Diciembre",
}

export function DashboardView() {
  const { filters, setFilters, data, loading, error } = useBoard()
  const { user, ready } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<"overview" | "charts" | "table">("overview")
  const [expandComparison, setExpandComparison] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const isAdmin = ready && user?.role === "admin"

  const summaries = data?.summaries ?? []
  const totalCases = data?.totalCases ?? 0
  const totalCapacity = data?.totalCapacity ?? 0
  const totalPeople = data?.totalPeople ?? 0
  const totalRecords = data?.totalRecords ?? 0
  const hasPersonIds = data?.hasPersonIds ?? false
  const hasCapacityData = data?.hasCapacityData ?? true
  const missingTotal = (data?.missingCasesCount ?? 0) + (data?.missingCapacityCount ?? 0)
  const naTotal = (data?.naCasesCount ?? 0) + (data?.naCapacityCount ?? 0)
  const topZone = summaries[0]
  const topSharePct = topZone && totalCases > 0 ? ((topZone.cases / totalCases) * 100).toFixed(1) : "0"
  const avgCasesPerUnit =
    hasPersonIds && totalPeople > 0
      ? (totalCases / totalPeople).toFixed(2)
      : totalRecords > 0
        ? (totalCases / totalRecords).toFixed(2)
        : "0"

  const rawDimLabels = data?.dimensionLabels ?? {
    zone: "Municipio",
    period: "Periodo",
    violence: "Tipo de violencia",
    service: "Servicio",
    cases: "Casos",
    capacity: "Atenciones",
  }
  const dimLabels = {
    zone: humanizeColumnLabel(rawDimLabels.zone),
    period: humanizeColumnLabel(rawDimLabels.period),
    violence: humanizeColumnLabel(rawDimLabels.violence),
    service: humanizeColumnLabel(rawDimLabels.service),
    cases: humanizeColumnLabel(rawDimLabels.cases),
    capacity: humanizeColumnLabel(rawDimLabels.capacity),
  }

  const effectiveYear = filters.year || data?.appliedYear || "Todos"
  const availableYears = data?.years ?? []
  const availableMonths = data?.months ?? []
  const availableDays = data?.days ?? []
  const hasGranularDates = availableMonths.length > 0 || availableDays.length > 0

  const yearOptions: SelectOption[] = ["Todos", ...(availableYears.length > 0 ? availableYears : data?.periods ?? [])]
  const monthOptions: SelectOption[] = [
    "Todos",
    ...availableMonths.map((mo) => ({ value: mo, label: MONTH_NAMES[mo] ?? mo })),
  ]
  const dayOptions: SelectOption[] = ["Todos", ...availableDays]
  const zoneOptions = [labels.allZones, ...(data?.municipalities ?? [])]
  const violenceOptions = [labels.allViolence, ...(data?.violenceTypes ?? [])]
  const serviceOptions = [labels.allServices, ...(data?.serviceTypes ?? [])]

  const defaultYear = availableYears.includes(labels.defaultPeriod) ? labels.defaultPeriod : "Todos"
  const activeFiltersCount =
    (effectiveYear !== defaultYear ? 1 : 0) +
    (filters.month !== "Todos" ? 1 : 0) +
    (filters.day !== "Todos" ? 1 : 0) +
    (filters.municipality !== labels.allZones ? 1 : 0) +
    (filters.violence !== labels.allViolence ? 1 : 0) +
    (filters.service !== labels.allServices ? 1 : 0)

  const selectedMunicipality = filters.municipality !== labels.allZones ? filters.municipality : (topZone?.name ?? "")
  const dynamicMetrics = data?.dynamicMetrics ?? []
  const extraBreakdowns = (data?.dynamicBreakdowns ?? []).filter(
    (item) => item.key.startsWith("extra:") || item.key.startsWith("metric:"),
  )
  const extraDimensions = data?.extraDimensions ?? []
  const tableDimensions = data?.tableDimensions ?? []
  const recordRows = data?.recordRows ?? []
  const primaryAgeBreakdown =
    extraBreakdowns.find((b) => /\bedad\b/i.test(b.label) && !/edad[_ ]?1\b/i.test(b.label)) ??
    extraBreakdowns.find((b) => /\bedad\b/i.test(b.label))
  const topAgeRanges = primaryAgeBreakdown
    ? [...primaryAgeBreakdown.items]
        .filter((item) => !/no especificado/i.test(item.name))
        .sort((a, b) => b.cases - a.cases)
        .slice(0, 3)
    : []

  const primaryAgeMetric =
    dynamicMetrics.find((m) => /\bedad\b/i.test(m.label) && !/edad[_ ]?1\b/i.test(m.label)) ??
    dynamicMetrics.find((m) => /\bedad\b/i.test(m.label)) ??
    dynamicMetrics.find((m) => m.avg !== null)
  const primaryViolenceItem = data?.dynamicBreakdowns?.find((b) => b.key === "violence")?.items[0]
  const hasDataInDb = Boolean(data?.hasData || (data && data.totalRecords > 0) || data?.source.fileName)

  if (loading && !data) {
    return <div className="notice">Cargando tablero…</div>
  }

  if (error && !data) {
    return (
      <div className="notice" role="alert">
        {error}
      </div>
    )
  }

  if (data && !hasDataInDb) {
    return (
      <section className="panel empty-db-panel" role="status">
        <span className="empty-db-icon">
          <Database size={22} />
        </span>
        <h2>Sin información en la base de datos</h2>
        <p>
          No existen registros cargados actualmente en el sistema. Cuando se cargue un archivo Excel válido, aquí se mostrarán los indicadores, el mapa municipal, las gráficas y los listados.
        </p>
        {isAdmin && (
          <button type="button" className="button primary" onClick={() => navigate("/admin")}>
            <Upload size={15} /> Ir a Cargar datos
          </button>
        )}
      </section>
    )
  }

  return (
    <>
      <section className={`filters-row ${filtersOpen ? "filters-open" : ""}`}>
        <span className="filters-label">
          <Filter size={13} /> FILTRAR
        </span>
        <button type="button" className="mobile-filter-toggle" onClick={() => setFiltersOpen((open) => !open)}>
          <Filter size={15} /> Filtros {activeFiltersCount > 0 ? `(${activeFiltersCount})` : ""}
        </button>
        <div className="filter-select filter-date-compact">
          <span>Año</span>
          <SearchableSelect
            ariaLabel={`Año (${dimLabels.period})`}
            value={effectiveYear}
            options={yearOptions}
            onChange={(value) => setFilters({ ...filters, period: labels.allPeriods, year: value })}
          />
        </div>
        {hasGranularDates && (
          <>
            <div className="filter-select filter-date-compact">
              <span>Mes</span>
              <SearchableSelect
                ariaLabel={`Mes (${dimLabels.period})`}
                value={filters.month}
                options={monthOptions}
                onChange={(value) => setFilters({ ...filters, period: labels.allPeriods, month: value })}
              />
            </div>
            <div className="filter-select filter-date-compact">
              <span>Día</span>
              <SearchableSelect
                ariaLabel={`Día (${dimLabels.period})`}
                value={filters.day}
                options={dayOptions}
                onChange={(value) => setFilters({ ...filters, period: labels.allPeriods, day: value })}
              />
            </div>
          </>
        )}
        <div className="filter-select">
          <span>{dimLabels.zone}</span>
          <SearchableSelect
            ariaLabel={dimLabels.zone}
            value={filters.municipality}
            options={zoneOptions}
            onChange={(value) => setFilters({ ...filters, municipality: value })}
          />
        </div>
        <div className="filter-select">
          <span>{dimLabels.violence}</span>
          <SearchableSelect
            ariaLabel={dimLabels.violence}
            value={filters.violence}
            options={violenceOptions}
            onChange={(value) => setFilters({ ...filters, violence: value })}
          />
        </div>
        <div className="filter-select">
          <span>{dimLabels.service}</span>
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
              period: labels.allPeriods,
              year: defaultYear,
              month: "Todos",
              day: "Todos",
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
            <span>Casos registrados</span>
            <span className="kpi-icon burgundy">
              <Users size={15} />
            </span>
          </div>
          <div className="kpi-value">{fmt(totalCases)}</div>
          <div className="kpi-foot">
            <span>{hasPersonIds ? `${fmt(totalPeople)} personas únicas` : `${fmt(totalRecords)} registros`}</span>
          </div>
        </article>

        {hasCapacityData ? (
          <>
            <article className="kpi-card">
              <div className="kpi-top">
                <span>{dimLabels.capacity}</span>
                <span className="kpi-icon violet">
                  <HeartHandshake size={15} />
                </span>
              </div>
              <div className="kpi-value">{fmt(totalCapacity)}</div>
              <div className="kpi-foot">
                <span>Capacidad institucional</span>
              </div>
            </article>
            <article className="kpi-card">
              <div className="kpi-top">
                <span>Brecha relativa</span>
                <span className="kpi-icon orange">
                  <Gauge size={15} />
                </span>
              </div>
              <div className="kpi-value">
                {totalCapacity > 0 ? `${Math.round((totalCases / totalCapacity) * 100)}%` : "—"}
              </div>
              <div className="kpi-foot">
                <span className={totalCases > totalCapacity ? "text-priority" : "text-stable"}>
                  {totalCases > totalCapacity ? "Demanda supera capacidad" : "Capacidad cubre demanda"}
                </span>
              </div>
            </article>
            <article className="kpi-card priority-kpi">
              <div className="kpi-top">
                <span>Zonas prioritarias</span>
                <span className="kpi-icon priority-icon">
                  <MapPin size={15} />
                </span>
              </div>
              <div className="kpi-value">{data?.priorityCount ?? 0}</div>
              <div className="kpi-foot">
                <span className="orange-trend">Municipios en atención prioritaria</span>
              </div>
            </article>
          </>
        ) : (
          <>
            <article className="kpi-card">
              <div className="kpi-top">
                <span>Municipios con incidencia</span>
                <span className="kpi-icon orange">
                  <MapPin size={15} />
                </span>
              </div>
              <div className="kpi-value">{summaries.length}</div>
              <div className="kpi-foot">
                <span>de 60 municipios en Tlaxcala</span>
              </div>
            </article>
            {hasPersonIds ? (
              <article className="kpi-card">
                <div className="kpi-top">
                  <span>Promedio por persona</span>
                  <span className="kpi-icon violet">
                    <Gauge size={15} />
                  </span>
                </div>
                <div className="kpi-value">{avgCasesPerUnit}</div>
                <div className="kpi-foot">
                  <span>casos por persona única</span>
                </div>
              </article>
            ) : primaryAgeMetric && primaryAgeMetric.avg !== null ? (
              <article className="kpi-card">
                <div className="kpi-top">
                  <span>{humanizeColumnLabel(primaryAgeMetric.label)} promedio</span>
                  <span className="kpi-icon violet">
                    <Gauge size={15} />
                  </span>
                </div>
                <div className="kpi-value">{fmt(primaryAgeMetric.avg)}</div>
                <div className="kpi-foot">
                  <span>
                    {primaryAgeMetric.mode !== null && primaryAgeMetric.mode !== undefined
                      ? `Moda: ${fmt(primaryAgeMetric.mode)} · `
                      : ""}
                    {fmt(primaryAgeMetric.validCount)} válidos
                  </span>
                </div>
              </article>
            ) : (
              <article className="kpi-card">
                <div className="kpi-top">
                  <span>Modalidad principal</span>
                  <span className="kpi-icon violet">
                    <Gauge size={15} />
                  </span>
                </div>
                <div className="kpi-value kpi-value-text">
                  {primaryViolenceItem ? primaryViolenceItem.name : "—"}
                </div>
                <div className="kpi-foot">
                  <span>
                    {primaryViolenceItem
                      ? `${fmt(primaryViolenceItem.cases)} registros (${primaryViolenceItem.sharePct}%)`
                      : "Sin desglose"}
                  </span>
                </div>
              </article>
            )}
            <article className="kpi-card">
              <div className="kpi-top">
                <span>Municipio principal</span>
                <span className="kpi-icon priority-icon">
                  <MapPin size={15} />
                </span>
              </div>
              <div className="kpi-value kpi-value-text">{topZone ? topZone.name : "—"}</div>
              <div className="kpi-foot">
                <span>{topZone ? `${fmt(topZone.cases)} casos (${topSharePct}% del total)` : "Sin datos"}</span>
              </div>
            </article>
          </>
        )}
      </section>

      {(dynamicMetrics.length > 0 || extraBreakdowns.length > 0) && (
        <section className="generalities-strip" aria-label="Generalidades de columnas adicionales">
          {dynamicMetrics.map((metric) => (
            <div className="generality-chip" key={`m-${metric.key}`}>
              <span className="gen-label">{humanizeColumnLabel(metric.label)}</span>
              <strong>
                {metric.avg !== null ? `Prom. ${fmt(metric.avg)}` : "Sin dato"}
                {metric.mode !== null && metric.mode !== undefined ? ` · Moda ${fmt(metric.mode)}` : ""}
              </strong>
              <small>
                {metric.modeCount ? `Moda: ${fmt(metric.modeCount)} rep. · ` : ""}
                {metric.min !== null && metric.max !== null ? `${fmt(metric.min)}–${fmt(metric.max)} · ` : ""}
                {fmt(metric.validCount)} válidos
              </small>
            </div>
          ))}
          {topAgeRanges.length > 0 && (
            <div className="generality-chip">
              <span className="gen-label">Rangos de edad principales</span>
              <strong>{topAgeRanges.map((item) => `${item.name} (${item.sharePct}%)`).join(" · ")}</strong>
              <small>{topAgeRanges.map((item) => `${item.name}: ${fmt(item.cases)} casos`).join(" · ")}</small>
            </div>
          )}
          {extraBreakdowns
            .filter(
              (bd) =>
                bd.kind !== "numeric" &&
                bd.items.length > 0 &&
                bd.key !== primaryAgeBreakdown?.key,
            )
            .slice(0, 4)
            .map((bd) => {
              const top = bd.items.find((item) => !/no especificado/i.test(item.name)) ?? bd.items[0]
              return (
                <div className="generality-chip" key={`d-${bd.key}`}>
                  <span className="gen-label">{humanizeColumnLabel(bd.label)}</span>
                  <strong>{top.name}</strong>
                  <small>
                    {top.sharePct}% ({fmt(top.cases)} casos) · {bd.totalCategories} cat.
                  </small>
                </div>
              )
            })}
        </section>
      )}

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
              municipalities={data?.municipalities ?? []}
              activeMunicipalityFilter={filters.municipality}
              totalCases={totalCases}
              hasPersonIds={hasPersonIds}
              hasCapacityData={hasCapacityData}
              hasResidenceDistinction={data?.hasResidenceDistinction ?? false}
              dynamicMetrics={dynamicMetrics}
              onFilterMunicipality={(municipality) => setFilters({ ...filters, municipality })}
            />
            <GeneralComparisonCard
              summaries={summaries}
              hasCapacityData={hasCapacityData}
              selected={selectedMunicipality}
              maxRows={10}
              onSelect={(municipality) =>
                setFilters({
                  ...filters,
                  municipality: filters.municipality === municipality ? labels.allZones : municipality,
                })
              }
              onShowAll={() => {
                setFilters({ ...filters, municipality: labels.allZones })
                setExpandComparison(true)
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
            selected={selectedMunicipality}
            latestPeriod={data?.trends.at(-1)?.period ?? "—"}
            missingTotal={missingTotal}
            naTotal={naTotal}
            undatedCases={data?.undatedCasesCount ?? 0}
            defaultExpandedComparison={expandComparison}
            onSelect={(municipality) => setFilters({ ...filters, municipality })}
            onShowAll={() => setFilters({ ...filters, municipality: labels.allZones })}
            onFilterBy={(field, val) => setFilters({ ...filters, [field]: val })}
          />
        )}

        {activeTab === "table" && (
          <ActionTable
            summaries={summaries}
            dynamicMetrics={dynamicMetrics}
            extraDimensions={extraDimensions}
            tableDimensions={tableDimensions}
            recordRows={recordRows}
            totalRecords={totalRecords}
            hasPersonIds={hasPersonIds}
            hasCapacityData={hasCapacityData}
            hasResidenceDistinction={data?.hasResidenceDistinction ?? false}
            dimensionLabels={dimLabels}
            filters={filters}
            selected={selectedMunicipality}
            onSelect={(municipality) => setFilters({ ...filters, municipality })}
          />
        )}
      </div>

      <footer className="disclaimer">
        <span className="disclaimer-icon">
          <AlertTriangle size={14} />
        </span>
        <p>
          Los resultados reflejan exclusivamente registros institucionales disponibles; un mayor volumen indica cercanía o cobertura, no incidencia poblacional.
        </p>
        <span className="footer-brand">
          CÓDIGO NARANJA <i>·</i> BY MUEGAN-ING
        </span>
      </footer>
    </>
  )
}
