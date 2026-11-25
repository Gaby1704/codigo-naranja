import { ArrowDownToLine, List, MapPin, Search } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import type { DimensionLabels, DynamicMetric, RecordRow, Summary } from "../../../../packages/shared/types"
import { getDashboardRecords, getRecordsCsvUrl } from "../api"
import { csvCell, fmt, fmtMetric, gap, humanizeColumnLabel } from "../lib/format"
import { municipalitiesMatch } from "../lib/municipalities"
import type { Filters } from "../lib/shared"

function fmtDynamicCell(value: number | null | undefined, status: string | undefined): string {
  if (value !== null && value !== undefined) return fmt(value)
  if (status === "na") return "N/A"
  return "Sin dato"
}

export function ActionTable({
  summaries,
  dynamicMetrics = [],
  extraDimensions = [],
  tableDimensions = [],
  recordRows = [],
  totalRecords = 0,
  hasPersonIds,
  hasCapacityData,
  hasResidenceDistinction,
  dimensionLabels,
  filters,
  selected,
  onSelect,
  className = "",
}: {
  summaries: Summary[]
  dynamicMetrics?: DynamicMetric[]
  extraDimensions?: string[]
  tableDimensions?: string[]
  recordRows?: RecordRow[]
  totalRecords?: number
  hasPersonIds: boolean
  hasCapacityData: boolean
  hasResidenceDistinction: boolean
  dimensionLabels?: DimensionLabels
  filters?: Filters
  selected: string
  onSelect: (name: string) => void
  className?: string
}) {
  const [query, setQuery] = useState("")
  const [viewMode, setViewMode] = useState<"summary" | "records">("summary")
  const [showAllCols, setShowAllCols] = useState(false)
  const [loadedRecords, setLoadedRecords] = useState<RecordRow[]>(recordRows)
  const [remoteTotal, setRemoteTotal] = useState<number>(totalRecords || recordRows.length)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    setLoadedRecords(recordRows)
    setRemoteTotal(totalRecords || recordRows.length)
  }, [recordRows, totalRecords])

  useEffect(() => {
    if (viewMode !== "records" || !filters) return
    const trimmed = query.trim()
    if (!trimmed && loadedRecords.length >= recordRows.length) {
      setRemoteTotal(totalRecords || recordRows.length)
      return
    }
    if (totalRecords <= recordRows.length && !trimmed) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setLoadingMore(true)
      getDashboardRecords(filters, trimmed, 0, 500, controller.signal)
        .then((page) => {
          setLoadedRecords(page.rows)
          setRemoteTotal(page.total)
        })
        .catch(() => {})
        .finally(() => setLoadingMore(false))
    }, 220)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [viewMode, query, filters, totalRecords, recordRows.length])

  async function loadMoreRecords() {
    if (!filters || loadingMore) return
    setLoadingMore(true)
    try {
      const page = await getDashboardRecords(filters, query.trim(), loadedRecords.length, 500)
      setLoadedRecords((prev) => [...prev, ...page.rows])
      setRemoteTotal(page.total)
    } finally {
      setLoadingMore(false)
    }
  }

  const summaryMetrics = useMemo(
    () => (showAllCols ? dynamicMetrics : dynamicMetrics.slice(0, 3)),
    [dynamicMetrics, showAllCols],
  )
  const summaryDims = useMemo(
    () => (showAllCols ? extraDimensions : extraDimensions.slice(0, 3)),
    [extraDimensions, showAllCols],
  )
  const recordMetrics = useMemo(() => dynamicMetrics.map((m) => m.key), [dynamicMetrics])

  const rows = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("es-MX")
    if (!q) return summaries
    return summaries.filter((row) => {
      if (row.name.toLocaleLowerCase("es-MX").includes(q)) return true
      return summaryDims.some((dim) => (row.extraDimensions?.[dim] ?? "").toLocaleLowerCase("es-MX").includes(q))
    })
  }, [summaries, summaryDims, query])

  const filteredRecordRows = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("es-MX")
    if (!q || (filters && totalRecords > recordRows.length)) return loadedRecords
    return loadedRecords.filter((row) => {
      const base = [row.zone, row.period, row.violence, row.service, row.personId]
      if (base.some((val) => val.toLocaleLowerCase("es-MX").includes(q))) return true
      if (Object.values(row.extraDims).some((val) => val.toLocaleLowerCase("es-MX").includes(q))) return true
      return Object.values(row.extraMetrics).some((val) => val !== null && String(val).includes(q))
    })
  }, [loadedRecords, query, filters, totalRecords, recordRows.length])

  function exportCsv() {
    const isRecords = viewMode === "records"
    if (isRecords && filters) {
      const link = document.createElement("a")
      link.href = getRecordsCsvUrl(filters, query.trim())
      link.download = "listado-registros-smet.csv"
      link.click()
      return
    }
    const headers = isRecords
      ? [
          dimensionLabels?.period ?? "Periodo",
          dimensionLabels?.zone ?? "Municipio",
          dimensionLabels?.violence ?? "Tipo de violencia",
          dimensionLabels?.service ?? "Servicio",
          ...(hasPersonIds ? ["Expediente"] : []),
          ...tableDimensions.map((col) => humanizeColumnLabel(col)),
          "Casos",
          ...(hasCapacityData ? ["Atenciones"] : []),
          ...extraDimensions.map((dim) => humanizeColumnLabel(dim)),
          ...recordMetrics.map((col) => humanizeColumnLabel(col)),
        ]
      : [
          "Municipio",
          ...(hasResidenceDistinction ? ["Casos por residencia"] : []),
          "Casos registrados",
          ...(hasPersonIds ? ["Personas únicas"] : []),
          ...tableDimensions.map((col) => `${humanizeColumnLabel(col)} únicos`),
          "Promedio casos por registro",
          ...summaryMetrics.flatMap((m) => [
            `Prom. ${humanizeColumnLabel(m.label)}`,
            `Moda ${humanizeColumnLabel(m.label)}`,
          ]),
          ...summaryDims.map((dim) => `${humanizeColumnLabel(dim)} (frecuente)`),
          ...(hasCapacityData ? ["Atenciones / capacidad", "Brecha", "Clasificación operativa", "Acción sugerida"] : []),
        ]

    const lines = isRecords
      ? [
          headers,
          ...filteredRecordRows.map((row) => [
            row.period,
            row.zone,
            row.violence,
            row.service,
            ...(hasPersonIds ? [row.personId || "Sin dato"] : []),
            ...tableDimensions.map((col) => row.extraDims[col] || "Sin dato"),
            fmtDynamicCell(row.cases, row.casesStatus),
            ...(hasCapacityData ? [fmtDynamicCell(row.capacity, row.capacityStatus)] : []),
            ...extraDimensions.map((dim) => row.extraDims[dim] || "Sin dato"),
            ...recordMetrics.map((col) => fmtDynamicCell(row.extraMetrics[col], row.extraMetricStatuses[col])),
          ]),
        ]
      : [
          headers,
          ...rows.map((row) => [
            row.name,
            ...(hasResidenceDistinction ? [row.residenceCases] : []),
            row.casesValidCount > 0 ? row.cases : row.casesNaCount > 0 ? "N/A" : "Sin dato",
            ...(hasPersonIds ? [row.uniquePeople] : []),
            ...tableDimensions.map((col) => row.tableCounts?.[col] ?? 0),
            row.avgCasesPerRecord !== null ? row.avgCasesPerRecord : "N/A",
            ...summaryMetrics.flatMap((m) => {
              const stat = row.extraMetrics?.[m.key]
              return [
                stat && stat.avg !== null ? stat.avg : "N/A",
                stat && stat.mode !== null && stat.mode !== undefined ? stat.mode : "N/A",
              ]
            }),
            ...summaryDims.map((dim) => row.extraDimensions?.[dim] ?? "Sin dato"),
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
    link.download = isRecords ? "listado-registros-smet.csv" : "focalizacion-smet.csv"
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className={`panel action-panel ${className}`.trim()}>
      <div className="action-heading">
        <div>
          <h2>{viewMode === "summary" ? "Detalle por municipio" : "Listado de registros"}</h2>
          <p>
            {viewMode === "records"
              ? "Registros filtrados con todas las columnas detectadas en el archivo."
              : hasCapacityData
                ? "Relación entre casos registrados, capacidad institucional y métricas detectadas."
                : "Conteos, promedios, modas y columnas detectadas por municipio."}
          </p>
        </div>
        <div className="table-tools">
          <div className="table-mode-switch" role="group" aria-label="Tipo de listado">
            <button
              type="button"
              className={viewMode === "summary" ? "active" : ""}
              onClick={() => setViewMode("summary")}
            >
              <MapPin size={13} /> Por municipio ({rows.length})
            </button>
            <button
              type="button"
              className={viewMode === "records" ? "active" : ""}
              onClick={() => setViewMode("records")}
            >
              <List size={13} /> Registros ({fmt(query.trim() ? remoteTotal : totalRecords || filteredRecordRows.length)})
            </button>
          </div>
          {viewMode === "summary" && (dynamicMetrics.length > 3 || extraDimensions.length > 3) && (
            <button type="button" className="link-inline" onClick={() => setShowAllCols((prev) => !prev)}>
              {showAllCols ? "Menos columnas" : "Ver todas las columnas"}
            </button>
          )}
          <label className="search-box">
            <Search size={14} />
            <input
              aria-label={viewMode === "summary" ? "Buscar municipio o categoría" : "Buscar en el listado"}
              placeholder={viewMode === "summary" ? "Buscar municipio…" : "Buscar en registros…"}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button type="button" className="button secondary export-button" onClick={exportCsv}>
            <ArrowDownToLine size={14} /> Exportar CSV
          </button>
        </div>
      </div>

      {viewMode === "summary" && rows.length === 0 ? (
        <div className="notice" role="status">
          No hay información disponible para mostrar en la tabla con los filtros actuales.
        </div>
      ) : viewMode === "records" && filteredRecordRows.length === 0 ? (
        <div className="notice" role="status">
          {loadingMore
            ? "Buscando registros…"
            : "No existen registros para mostrar con los filtros o búsqueda actuales."}
        </div>
      ) : (
        <div className="action-table-wrap">
          {viewMode === "summary" ? (
          <table className="action-table">
            <thead>
              <tr>
                <th>MUNICIPIO</th>
                <th>CASOS</th>
                {hasPersonIds && <th>PERSONAS ÚNICAS</th>}
                {tableDimensions.map((col) => (
                  <th key={`th-${col}`}>{humanizeColumnLabel(col).toUpperCase()} ÚNICOS</th>
                ))}
                {hasResidenceDistinction && <th>RESIDENCIA</th>}
                {hasCapacityData && <th>ATENCIONES</th>}
                <th>PROM. CASOS</th>
                {summaryMetrics.flatMap((m) => [
                  <th key={`${m.key}-avg`}>PROM. {humanizeColumnLabel(m.label).toUpperCase()}</th>,
                  <th key={`${m.key}-mode`}>MODA {humanizeColumnLabel(m.label).toUpperCase()}</th>,
                ])}
                {summaryDims.map((dim) => (
                  <th key={dim}>{humanizeColumnLabel(dim).toUpperCase()}</th>
                ))}
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
                  {tableDimensions.map((col) => (
                    <td key={`tc-${col}`}>{fmt(row.tableCounts?.[col] ?? 0)}</td>
                  ))}
                  {hasResidenceDistinction && <td>{fmt(row.residenceCases)}</td>}
                  {hasCapacityData && (
                    <td>{fmtMetric(row.capacity, row.capacityValidCount, row.capacityNaCount, row.capacityMissingCount)}</td>
                  )}
                  <td>{row.avgCasesPerRecord !== null ? fmt(row.avgCasesPerRecord) : "N/A"}</td>
                  {summaryMetrics.flatMap((m) => {
                    const stat = row.extraMetrics?.[m.key]
                    return [
                      <td key={`${m.key}-avg`}>{stat && stat.avg !== null ? fmt(stat.avg) : "N/A"}</td>,
                      <td key={`${m.key}-mode`}>
                        {stat && stat.mode !== null && stat.mode !== undefined ? fmt(stat.mode) : "N/A"}
                      </td>,
                    ]
                  })}
                  {summaryDims.map((dim) => (
                    <td key={dim}>{row.extraDimensions?.[dim] ?? "Sin dato"}</td>
                  ))}
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
        ) : (
          <table className="action-table">
            <thead>
              <tr>
                <th>{(dimensionLabels?.period ?? "Periodo").toUpperCase()}</th>
                <th>{(dimensionLabels?.zone ?? "Municipio").toUpperCase()}</th>
                <th>{(dimensionLabels?.violence ?? "Tipo de violencia").toUpperCase()}</th>
                <th>{(dimensionLabels?.service ?? "Servicio").toUpperCase()}</th>
                {hasPersonIds && <th>EXPEDIENTE</th>}
                {tableDimensions.map((col) => (
                  <th key={`rt-${col}`}>{humanizeColumnLabel(col).toUpperCase()}</th>
                ))}
                <th>CASOS</th>
                {hasCapacityData && <th>ATENCIONES</th>}
                {extraDimensions.map((dim) => (
                  <th key={dim}>{humanizeColumnLabel(dim).toUpperCase()}</th>
                ))}
                {recordMetrics.map((col) => (
                  <th key={col}>{humanizeColumnLabel(col).toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRecordRows.map((row, idx) => (
                <tr key={`${row.personId || "r"}-${row.period}-${row.zone}-${idx}`} onClick={() => onSelect(row.zone)}>
                  <td>{row.period}</td>
                  <td>
                    <span className="municipality-cell">
                      <MapPin size={13} />
                      {row.zone}
                    </span>
                  </td>
                  <td>{row.violence}</td>
                  <td>{row.service}</td>
                  {hasPersonIds && <td>{row.personId || "Sin dato"}</td>}
                  {tableDimensions.map((col) => (
                    <td key={`rv-${col}`}>{row.extraDims[col] || "Sin dato"}</td>
                  ))}
                  <td>{fmtDynamicCell(row.cases, row.casesStatus)}</td>
                  {hasCapacityData && <td>{fmtDynamicCell(row.capacity, row.capacityStatus)}</td>}
                  {extraDimensions.map((dim) => (
                    <td key={dim}>{row.extraDims[dim] || "Sin dato"}</td>
                  ))}
                  {recordMetrics.map((col) => (
                    <td key={col}>{fmtDynamicCell(row.extraMetrics[col], row.extraMetricStatuses[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </div>
      )}
      <div className="table-footer">
        <span>
          {viewMode === "summary" ? (
            <>
              Mostrando <b>{rows.length}</b> de <b>{summaries.length}</b> municipios
            </>
          ) : (
            <>
              Mostrando <b>{filteredRecordRows.length}</b> de <b>{fmt(remoteTotal)}</b> registros filtrados
              {filteredRecordRows.length < remoteTotal && (
                <>
                  {" · "}
                  <button
                    type="button"
                    className="link-inline"
                    disabled={loadingMore}
                    onClick={() => void loadMoreRecords()}
                  >
                    {loadingMore ? "Cargando…" : "Cargar 500 más"}
                  </button>
                </>
              )}
            </>
          )}
        </span>
        <span>
          <span className="footer-dot" /> Ceros preservados · N/A excluidos de promedios
        </span>
      </div>
    </section>
  )
}
