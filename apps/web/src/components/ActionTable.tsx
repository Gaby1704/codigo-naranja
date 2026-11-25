import { ArrowDownToLine, MapPin, Search } from "lucide-react"
import { useMemo, useState } from "react"
import type { Summary } from "../../../../packages/shared/types"
import { csvCell, fmt, fmtMetric, gap } from "../lib/format"
import { municipalitiesMatch } from "../lib/municipalities"

export function ActionTable({
  summaries,
  hasPersonIds,
  hasCapacityData,
  hasResidenceDistinction,
  selected,
  onSelect,
  className = "",
}: {
  summaries: Summary[]
  hasPersonIds: boolean
  hasCapacityData: boolean
  hasResidenceDistinction: boolean
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
    const headers = [
      "Municipio",
      ...(hasResidenceDistinction ? ["Casos por residencia"] : []),
      "Casos registrados",
      ...(hasPersonIds ? ["Personas únicas"] : []),
      "Promedio casos por registro",
      ...(hasCapacityData ? ["Atenciones / capacidad", "Brecha", "Clasificación operativa", "Acción sugerida"] : []),
    ]
    const lines = [
      headers,
      ...rows.map((row) => [
        row.name,
        ...(hasResidenceDistinction ? [row.residenceCases] : []),
        row.casesValidCount > 0 ? row.cases : row.casesNaCount > 0 ? "N/A" : "Sin dato",
        ...(hasPersonIds ? [row.uniquePeople] : []),
        row.avgCasesPerRecord !== null ? row.avgCasesPerRecord : "N/A",
        ...(hasCapacityData
          ? [
              row.capacityValidCount > 0 ? row.capacity : row.capacityNaCount > 0 ? "N/A" : "Sin dato",
              gap(row.ratio),
              row.classification.label,
              row.classification.action,
            ]
          : []),
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
          <h2>Detalle por municipio</h2>
          <p>
            {hasCapacityData
              ? "Relación entre casos registrados y capacidad institucional de atención."
              : "Archivo sin columnas de atenciones o cobertura; se muestran únicamente conteos y promedios registrados."}
          </p>
        </div>
        <div className="table-tools">
          <label className="search-box">
            <Search size={14} />
            <input
              aria-label="Buscar municipio"
              placeholder="Buscar municipio…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button type="button" className="button secondary export-button" onClick={exportCsv}>
            <ArrowDownToLine size={14} /> Exportar CSV
          </button>
        </div>
      </div>

      <div className="action-table-wrap">
        <table className="action-table">
          <thead>
            <tr>
              <th>MUNICIPIO</th>
              <th>CASOS</th>
              {hasPersonIds && <th>PERSONAS ÚNICAS</th>}
              {hasResidenceDistinction && <th>RESIDENCIA</th>}
              {hasCapacityData && <th>ATENCIONES</th>}
              <th>PROM. CASOS</th>
              {hasCapacityData && <th>BRECHA</th>}
              {hasCapacityData && <th>CLASIFICACIÓN</th>}
              {hasCapacityData && <th>ACCIÓN SUGERIDA</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.name}
                className={municipalitiesMatch(selected, row.name) ? "row-selected" : ""}
                onClick={() => onSelect(row.name)}
              >
                <td>
                  <span className="municipality-cell">
                    <MapPin size={13} />
                    {row.name}
                  </span>
                </td>
                <td>{fmtMetric(row.cases, row.casesValidCount, row.casesNaCount, row.casesMissingCount)}</td>
                {hasPersonIds && <td>{fmt(row.uniquePeople)}</td>}
                {hasResidenceDistinction && <td>{fmt(row.residenceCases)}</td>}
                {hasCapacityData && (
                  <td>{fmtMetric(row.capacity, row.capacityValidCount, row.capacityNaCount, row.capacityMissingCount)}</td>
                )}
                <td>{row.avgCasesPerRecord !== null ? fmt(row.avgCasesPerRecord) : "N/A"}</td>
                {hasCapacityData && (
                  <>
                    <td>
                      <span className={row.ratio >= 1.3 ? "text-priority" : ""}>{gap(row.ratio)}</span>
                    </td>
                    <td>
                      <span className={`status-pill ${row.classification.color}`}>
                        <i /> {row.classification.label}
                      </span>
                    </td>
                    <td className="suggestion-cell">{row.classification.action}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>
          Mostrando <b>{rows.length}</b> de <b>{summaries.length}</b> municipios
        </span>
        <span>
          <span className="footer-dot" /> Ceros preservados · N/A excluidos de promedios
        </span>
      </div>
    </section>
  )
}
