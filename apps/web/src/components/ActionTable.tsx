import { ArrowDownToLine, MapPin, Search } from "lucide-react"
import { useMemo, useState } from "react"
import type { Summary } from "../../../../packages/shared/types"
import { csvCell, fmt, gap } from "../lib/format"

export function ActionTable({
  summaries,
  selected,
  onSelect,
  className = "",
}: {
  summaries: Summary[]
  selected: string
  onSelect: (name: string) => void
  className?: string
}) {
  const [query, setQuery] = useState("")
  const rows = useMemo(
    () => summaries.filter((row) => row.name.toLocaleLowerCase("es-MX").includes(query.toLocaleLowerCase("es-MX"))),
    [summaries, query],
  )

  function exportCsv() {
    const lines = [
      ["Municipio", "Casos registrados", "Capacidad de servicio", "Brecha", "Clasificación operativa", "Acción sugerida"],
      ...rows.map((row) => [
        row.name,
        row.cases,
        row.capacity,
        gap(row.ratio),
        row.classification.label,
        row.classification.action,
      ]),
    ]
    const csv = lines.map((line) => line.map((cell) => csvCell(cell)).join(",")).join("\n")
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }))
    const link = document.createElement("a")
    link.href = url
    link.download = "focalizacion-smet.csv"
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className={`panel action-panel ${className}`.trim()}>
      <div className="action-heading">
        <div>
          <span className="eyebrow">
            PLANEACIÓN OPERATIVA <span className="eyebrow-slash">/</span> 04
          </span>
          <h2>Focalización de jornadas itinerantes y unidades móviles</h2>
          <p>Priorización sugerida a partir de la relación demanda / capacidad registrada.</p>
        </div>
        <div className="table-tools">
          <label className="search-box">
            <Search size={15} />
            <input
              aria-label="Buscar municipio"
              placeholder="Buscar municipio…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button type="button" className="button secondary export-button" onClick={exportCsv}>
            <ArrowDownToLine size={15} /> Exportar CSV
          </button>
        </div>
      </div>
      <div className="action-table-wrap">
        <table className="action-table">
          <thead>
            <tr>
              <th>MUNICIPIO</th>
              <th>CASOS REGISTRADOS</th>
              <th>CAPACIDAD</th>
              <th>BRECHA ESTIMADA</th>
              <th>CLASIFICACIÓN OPERATIVA</th>
              <th>ACCIÓN SUGERIDA</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 8).map((row) => (
              <tr key={row.name} className={selected === row.name ? "row-selected" : ""} onClick={() => onSelect(row.name)}>
                <td>
                  <span className="municipality-cell">
                    <MapPin size={14} />
                    {row.name}
                  </span>
                </td>
                <td>{fmt(row.cases)}</td>
                <td>{fmt(row.capacity)}</td>
                <td>
                  <span className={row.ratio >= 1.3 ? "text-priority" : ""}>{gap(row.ratio)}</span>
                </td>
                <td>
                  <span className={`status-pill ${row.classification.color}`}>
                    <i /> {row.classification.label}
                  </span>
                </td>
                <td className="suggestion-cell">{row.classification.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>
          Mostrando <b>{Math.min(8, rows.length)}</b> de <b>{rows.length}</b> municipios
        </span>
        <span>
          <span className="footer-dot" /> Clic en una fila para consultar municipio
        </span>
      </div>
    </section>
  )
}
