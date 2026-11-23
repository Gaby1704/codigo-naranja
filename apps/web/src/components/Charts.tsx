import { ArrowUpRight, CircleHelp } from "lucide-react"
import type { Summary, Trend } from "../../../../packages/shared/types"
import { fmt } from "../lib/format"

export function Charts({
  summaries,
  trends,
  selected,
  latestPeriod,
  onSelect,
  onShowAll,
}: {
  summaries: Summary[]
  trends: Trend[]
  selected: string
  latestPeriod: string
  onSelect: (name: string) => void
  onShowAll: () => void
}) {
  const maxCases = Math.max(...summaries.map((item) => item.cases), 1)
  const maxCapacity = Math.max(...summaries.map((item) => item.capacity), 1)
  const maxTrend = Math.max(...trends.map((item) => Math.max(item.cases, item.capacity)), 1)

  return (
    <aside className="side-column">
      <section className="panel chart-panel">
        <div className="panel-heading compact">
          <div>
            <span className="eyebrow">
              COMPARATIVA <span className="eyebrow-slash">/</span> 02
            </span>
            <h2>Demanda vs. capacidad</h2>
            <p>Por municipio · selección actual</p>
          </div>
          <button type="button" title="Detalle de comparativa" className="icon-button">
            <CircleHelp size={15} />
          </button>
        </div>
        <div className="bar-chart">
          {summaries.slice(0, 7).map((row) => (
            <button
              type="button"
              className={`bar-row ${row.name === selected ? "bar-active" : ""}`}
              key={row.name}
              onClick={() => onSelect(row.name)}
            >
              <span className="bar-name">{row.name}</span>
              <span className="bar-track">
                <i className="bar-demand" style={{ width: `${Math.max(5, (row.cases / maxCases) * 100)}%` }} />
                <i className="bar-capacity" style={{ width: `${Math.max(5, (row.capacity / maxCapacity) * 100)}%` }} />
              </span>
              <span className="bar-number">{fmt(row.cases)}</span>
            </button>
          ))}
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-square demand" /> Casos
          </span>
          <span>
            <i className="legend-square capacity" /> Capacidad
          </span>
          <button type="button" onClick={onShowAll}>
            Ver todos <ArrowUpRight size={13} />
          </button>
        </div>
      </section>
      <section className="panel trend-panel">
        <div className="panel-heading compact">
          <div>
            <span className="eyebrow">
              EVOLUCIÓN <span className="eyebrow-slash">/</span> 03
            </span>
            <h2>Tendencia de registros</h2>
            <p>Casos vs. capacidad por año</p>
          </div>
          <span className="trend-badge">{latestPeriod}</span>
        </div>
        <div className="trend-chart">
          {trends.map((point) => (
            <div className="trend-column" key={point.period}>
              <div className="trend-bars">
                <i className="trend-demand" style={{ height: `${Math.max(4, (point.cases / maxTrend) * 100)}%` }} title={`${fmt(point.cases)} casos`} />
                <i className="trend-capacity" style={{ height: `${Math.max(4, (point.capacity / maxTrend) * 100)}%` }} title={`${fmt(point.capacity)} capacidad`} />
              </div>
              <span>{point.period}</span>
            </div>
          ))}
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-square demand" /> Casos
          </span>
          <span>
            <i className="legend-square capacity" /> Capacidad
          </span>
          <span className="trend-note">Registros por periodo</span>
        </div>
      </section>
    </aside>
  )
}
