import { ArrowUpRight, Layers, TrendingUp } from "lucide-react"
import type {
  ClassificationColor,
  DynamicBreakdown,
  DynamicMetric,
  Forecast,
  Summary,
  Trend,
} from "../../../../packages/shared/types"
import { fmt, gap, humanizeColumnLabel } from "../lib/format"

const TIER_ORDER: Array<{ color: ClassificationColor; title: string; hint: string }> = [
  { color: "priority", title: "Atención prioritaria", hint: "Demanda supera capacidad (brecha ≥ 130%)" },
  { color: "watch", title: "Posible subregistro", hint: "Bajo volumen relativo de registros" },
  { color: "elevated", title: "Optimizar capacidad", hint: "Ampliación de turnos y cobertura" },
  { color: "stable", title: "Cobertura estable", hint: "Oferta institucional suficiente" },
]

export function GeneralComparisonCard({
  summaries,
  hasCapacityData,
  selected,
  onSelect,
  onShowAll,
  maxRows = 10,
}: {
  summaries: Summary[]
  hasCapacityData: boolean
  selected: string
  onSelect: (name: string) => void
  onShowAll: () => void
  maxRows?: number
}) {
  const rows = summaries.slice(0, maxRows)
  const maxScale = Math.max(
    ...rows.flatMap((item) => (hasCapacityData ? [item.cases, item.capacity] : [item.cases])),
    1,
  )
  const topZone = summaries[0]
  const headline = !topZone
    ? "Sin registros en la selección actual"
    : hasCapacityData && topZone.ratio >= 1.3
      ? `${topZone.name} encabeza la brecha (${gap(topZone.ratio)})`
      : hasCapacityData && topZone.capacity > 0
        ? `La capacidad supera la demanda en ${topZone.name}`
        : `${topZone.name} concentra ${fmt(topZone.cases)} casos`

  return (
    <section className="panel chart-panel">
      <div className="panel-heading compact">
        <div>
          <h2>{headline}</h2>
          <p>{hasCapacityData ? "Casos vs. atenciones por municipio" : "Casos registrados por municipio"}</p>
        </div>
        <span className="axis-tag">0 – {fmt(Math.ceil(maxScale))}</span>
      </div>
      <div className="bar-chart">
        {rows.map((row) => {
          const demandWidth = row.cases === 0 ? 0 : Math.max(2, (row.cases / maxScale) * 100)
          const capWidth = row.capacity === 0 ? 0 : Math.max(2, (row.capacity / maxScale) * 100)
          return (
            <button
              type="button"
              className={`bar-row ${row.name === selected ? "bar-active" : ""}`}
              key={row.name}
              onClick={() => onSelect(row.name)}
              title={
                hasCapacityData
                  ? `${row.name}: ${fmt(row.cases)} casos · ${fmt(row.capacity)} atenciones`
                  : `${row.name}: ${fmt(row.cases)} casos`
              }
            >
              <span className="bar-name">{row.name}</span>
              <span className={`bar-track${hasCapacityData ? "" : " single"}`}>
                <i className="bar-demand" style={{ width: `${demandWidth}%` }} />
                {hasCapacityData && <i className="bar-capacity" style={{ width: `${capWidth}%` }} />}
              </span>
              <span className="bar-number">
                {hasCapacityData ? `${fmt(row.cases)} / ${fmt(row.capacity)}` : fmt(row.cases)}
              </span>
            </button>
          )
        })}
      </div>
      <div className="chart-legend">
        <span>
          <i className="legend-square demand" /> Casos
        </span>
        {hasCapacityData && (
          <span>
            <i className="legend-square capacity" /> Atenciones
          </span>
        )}
        <button type="button" onClick={onShowAll}>
          Ver todos <ArrowUpRight size={13} />
        </button>
      </div>
    </section>
  )
}

export function Charts({
  summaries,
  trends,
  forecast,
  dynamicBreakdowns,
  dynamicMetrics,
  hasCapacityData,
  selected,
  latestPeriod,
  missingTotal,
  naTotal,
  undatedCases = 0,
  onSelect,
  onShowAll,
  onFilterBy,
}: {
  summaries: Summary[]
  trends: Trend[]
  forecast?: Forecast
  dynamicBreakdowns: DynamicBreakdown[]
  dynamicMetrics: DynamicMetric[]
  hasCapacityData: boolean
  selected: string
  latestPeriod: string
  missingTotal: number
  naTotal: number
  undatedCases?: number
  onSelect: (name: string) => void
  onShowAll: () => void
  onFilterBy?: (field: "violence" | "service" | "period", value: string) => void
}) {
  const forecastPoints = forecast?.available ? forecast.points : []
  const trendValues = [
    ...trends.flatMap((item) => (hasCapacityData ? [item.cases, item.capacity] : [item.cases])),
    ...forecastPoints.flatMap((item) => (hasCapacityData ? [item.cases, item.capacity] : [item.cases])),
  ]
  const maxTrend = Math.max(...trendValues, 1)
  const midTrend = Math.round(maxTrend / 2)

  const rangeLabel =
    forecastPoints.length >= 2
      ? `${forecastPoints[0].period}–${forecastPoints[forecastPoints.length - 1].period}`
      : ""
  const trendHeadline = forecast?.available
    ? `Trayectoria proyectada a 5 años${rangeLabel ? ` (${rangeLabel})` : ""}`
    : "Evolución de registros por periodo"
  const trendSubtitle = forecast?.excludedIncompletePeriods.length
    ? `Tendencia histórica y proyección lineal simple (excluye ${forecast.excludedIncompletePeriods.join(", ")})`
    : "Tendencia histórica y proyección lineal simple"

  const tierStats = TIER_ORDER.map((tier) => {
    const items = summaries.filter((row) => row.classification.color === tier.color)
    return {
      ...tier,
      count: items.length,
      cases: items.reduce((acc, row) => acc + row.cases, 0),
      capacity: items.reduce((acc, row) => acc + row.capacity, 0),
    }
  })
  const maxTierCount = Math.max(...tierStats.map((tier) => tier.count), 1)

  return (
    <div className="charts-grid">
      <GeneralComparisonCard
        summaries={summaries}
        hasCapacityData={hasCapacityData}
        selected={selected}
        onSelect={onSelect}
        onShowAll={onShowAll}
        maxRows={10}
      />

      <section className="panel trend-panel">
        <div className="panel-heading compact">
          <div>
            <h2>{trendHeadline}</h2>
            <p>{trendSubtitle}</p>
          </div>
          <span className="trend-badge">{latestPeriod}</span>
        </div>
        <div className="trend-chart-wrap tall">
          <div className="trend-y-axis" aria-hidden="true">
            <span>{fmt(Math.ceil(maxTrend))}</span>
            <span>{fmt(midTrend)}</span>
            <span>0</span>
          </div>
          <div className="trend-chart">
            {trends.map((point) => {
              const dHeight = point.cases === 0 ? 0 : Math.max(3, (point.cases / maxTrend) * 100)
              const cHeight = point.capacity === 0 ? 0 : Math.max(3, (point.capacity / maxTrend) * 100)
              return (
                <div className={`trend-column ${point.complete ? "" : "incomplete-period"}`} key={point.period}>
                  <span className="trend-val">{fmt(point.cases)}</span>
                  <div className="trend-bars">
                    <i className="trend-demand" style={{ height: `${dHeight}%` }} title={`${point.period}: ${fmt(point.cases)} casos`} />
                    {hasCapacityData && (
                      <i className="trend-capacity" style={{ height: `${cHeight}%` }} title={`${point.period}: ${fmt(point.capacity)} atenciones`} />
                    )}
                  </div>
                  <span>{point.period}</span>
                </div>
              )
            })}
            {forecastPoints.map((point) => {
              const dHeight = point.cases === 0 ? 0 : Math.max(3, (point.cases / maxTrend) * 100)
              const cHeight = point.capacity === 0 ? 0 : Math.max(3, (point.capacity / maxTrend) * 100)
              return (
                <div className="trend-column projected" key={`proj-${point.period}`}>
                  <span className="trend-val">{fmt(point.cases)}</span>
                  <div className="trend-bars">
                    <i
                      className="trend-demand projected-bar"
                      style={{ height: `${dHeight}%` }}
                      title={`Proyección ${point.period}: ${fmt(point.cases)} casos`}
                    />
                    {hasCapacityData && (
                      <i
                        className="trend-capacity projected-bar"
                        style={{ height: `${cHeight}%` }}
                        title={`Proyección ${point.period}: ${fmt(point.capacity)} atenciones`}
                      />
                    )}
                  </div>
                  <span>{point.period}*</span>
                </div>
              )
            })}
          </div>
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-square demand" /> Casos
          </span>
          {hasCapacityData && (
            <span>
              <i className="legend-square capacity" /> Atenciones
            </span>
          )}
          {forecastPoints.length > 0 && (
            <span>
              <i className="legend-square projected" /> *Proyección 5 años
            </span>
          )}
          <span className="trend-note">
            Eje desde 0{undatedCases > 0 ? ` · +${fmt(undatedCases)} sin fecha` : ""}
          </span>
        </div>
        <p className="chart-footnote">
          Estimación lineal de tendencia a partir del histórico disponible; no representa predicción definitiva ni tasa poblacional.
        </p>
      </section>

      {dynamicBreakdowns.map((breakdown, bdIdx) => {
        const displayLabel = humanizeColumnLabel(breakdown.label)
        const top = breakdown.items[0]
        const maxCatCases = Math.max(...breakdown.items.map((item) => item.cases), 1)
        const barColorClass =
          breakdown.kind === "temporal"
            ? "dyn-temporal"
            : breakdown.kind === "status"
              ? "dyn-status"
              : breakdown.kind === "numeric"
                ? "dyn-numeric"
                : bdIdx % 2 === 0
                  ? "dyn-cat-a"
                  : "dyn-cat-b"
        const canFilter =
          breakdown.filterField === "violence" ||
          breakdown.filterField === "service" ||
          breakdown.filterField === "period"
        return (
          <section className="panel chart-panel dynamic-chart-panel" key={breakdown.key}>
            <div className="panel-heading compact">
              <div>
                <h2>
                  {top
                    ? breakdown.kind === "numeric"
                      ? `Distribución de ${displayLabel}: predomina ${top.name} (${top.sharePct}%)`
                      : `${top.name} concentra el ${top.sharePct}% en ${displayLabel}`
                    : `Sin registros en ${displayLabel}`}
                </h2>
                <p>
                  {breakdown.kind === "numeric"
                    ? `${displayLabel} · ${breakdown.totalCategories} rangos`
                    : `${displayLabel} · ${breakdown.totalCategories} categorías`}
                </p>
              </div>
              <span className="axis-tag">
                <Layers size={11} /> {breakdown.items.length}
              </span>
            </div>
            <div className="bar-chart">
              {breakdown.items.map((item) => {
                const width = item.cases === 0 ? 0 : Math.max(3, (item.cases / maxCatCases) * 100)
                return (
                  <button
                    type="button"
                    className="bar-row"
                    key={item.name}
                    onClick={() => {
                      if (canFilter && onFilterBy && breakdown.filterField) {
                        onFilterBy(breakdown.filterField as "violence" | "service" | "period", item.name)
                      }
                    }}
                    title={`${item.name}: ${fmt(item.cases)} casos (${item.sharePct}%) · ${fmt(item.records)} registros`}
                  >
                    <span className="bar-name">{item.name}</span>
                    <span className="bar-track single">
                      <i className={barColorClass} style={{ width: `${width}%` }} />
                    </span>
                    <span className="bar-number">
                      {fmt(item.cases)} ({item.sharePct}%)
                    </span>
                  </button>
                )
              })}
            </div>
          </section>
        )
      })}

      {dynamicMetrics.length > 0 && (
        <section className="panel tier-panel">
          <div className="panel-heading compact">
            <div>
              <h2>Indicadores numéricos del archivo</h2>
              <p>Los promedios conservan el 0 y excluyen N/A o valores faltantes</p>
            </div>
            <span className="axis-tag">{dynamicMetrics.length} métricas</span>
          </div>
          <div className="dynamic-metrics-grid">
            {dynamicMetrics.map((metric) => (
              <div className="dynamic-metric-card" key={metric.key}>
                <span>{humanizeColumnLabel(metric.label)}</span>
                <strong>{metric.avg !== null ? `Prom. ${fmt(metric.avg)}` : "Sin datos válidos"}</strong>
                <small>
                  Suma: {fmt(metric.sum)} · Rango: {metric.min !== null ? fmt(metric.min) : "—"} a{" "}
                  {metric.max !== null ? fmt(metric.max) : "—"}
                </small>
                <small>
                  Ceros: {metric.zeroCount} · N/A: {metric.naCount} · Faltantes: {metric.missingCount}
                </small>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="panel tier-panel">
        <div className="panel-heading compact">
          <div>
            <h2>
              {!hasCapacityData
                ? `${summaries.length} municipios con registros activos`
                : tierStats[0].count > 0
                  ? `${tierStats[0].count} municipios en atención prioritaria`
                  : "Sin municipios en saturación crítica"}
            </h2>
            <p>
              {hasCapacityData
                ? "Distribución por clasificación operativa y volumen acumulado"
                : "Resumen de cobertura territorial y calidad del corte"}
            </p>
          </div>
          <span className="axis-tag">{summaries.length} municipios</span>
        </div>
        {hasCapacityData && (
          <div className="tier-bars">
            {tierStats.map((tier) => {
              const width = tier.count === 0 ? 0 : Math.max(4, (tier.count / maxTierCount) * 100)
              return (
                <div className="tier-row" key={tier.color}>
                  <div className="tier-meta">
                    <span className={`status-pill ${tier.color}`}>
                      <i /> {tier.title}
                    </span>
                    <small>{tier.hint}</small>
                  </div>
                  <div className="tier-track">
                    <span className={`tier-fill ${tier.color}`} style={{ width: `${width}%` }} />
                  </div>
                  <div className="tier-numbers">
                    <b>{tier.count} mun.</b>
                    <small>
                      {fmt(tier.cases)} c. / {fmt(tier.capacity)} at.
                    </small>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <div className="tier-quality-strip">
          <span>
            <TrendingUp size={13} /> Variación anual estimada:{" "}
            <b>
              {forecast?.available
                ? forecast.annualDeltaCases > 0
                  ? `Al alza (${fmt(forecast.annualDeltaCases)} casos/año)`
                  : forecast.annualDeltaCases < 0
                    ? `A la baja (${fmt(Math.abs(forecast.annualDeltaCases))} casos/año)`
                    : "Estable (0 casos/año)"
                : "Histórico insuficiente"}
            </b>
          </span>
          <span>
            Datos N/A excluidos: <b>{fmt(naTotal)}</b> · Faltantes: <b>{fmt(missingTotal)}</b>
          </span>
        </div>
      </section>
    </div>
  )
}
