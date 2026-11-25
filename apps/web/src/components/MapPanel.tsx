import { geoMercator, geoPath } from "d3-geo"
import type { GeoPermissibleObjects } from "d3-geo"
import { MapPin, RotateCcw, TrendingDown, TrendingUp } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { createPortal } from "react-dom"
import type { DynamicMetric, Summary } from "../../../../packages/shared/types"
import { fmt, fmtMetric, gap, humanizeColumnLabel } from "../lib/format"
import { findFilterValueForGeoName, findSummaryForGeoName, municipalitiesMatch } from "../lib/municipalities"
import { filters as labels } from "../lib/shared"

type GeoFeature = {
  type: "Feature"
  properties: {
    CVEGEO?: string
    CVE_MUN?: string
    NOMGEO?: string
    NOM_MUN?: string
  }
  geometry: GeoPermissibleObjects
}

type GeoCollection = {
  type: "FeatureCollection"
  features: GeoFeature[]
}

const ORANGE_SCALE = ["#fde4cf", "#fbc193", "#f69454", "#de6121", "#a3330c"] as const
const NEUTRAL_ZERO_FILL = "#efebe6"

function choroplethColor(cases: number, maxCases: number): string {
  if (cases <= 0 || maxCases <= 0) return NEUTRAL_ZERO_FILL
  const ratio = Math.min(1, cases / maxCases)
  const index = Math.min(ORANGE_SCALE.length - 1, Math.floor(ratio * (ORANGE_SCALE.length - 0.01)))
  return ORANGE_SCALE[index]
}

export function MapPanel({
  summaries,
  municipalities,
  activeMunicipalityFilter,
  totalCases,
  hasPersonIds,
  hasCapacityData,
  hasResidenceDistinction,
  dynamicMetrics = [],
  onFilterMunicipality,
}: {
  summaries: Summary[]
  municipalities: string[]
  activeMunicipalityFilter: string
  totalCases: number
  hasPersonIds: boolean
  hasCapacityData: boolean
  hasResidenceDistinction: boolean
  dynamicMetrics?: DynamicMetric[]
  onFilterMunicipality: (municipality: string) => void
}) {
  const [collection, setCollection] = useState<GeoCollection | null>(null)
  const [hovered, setHovered] = useState<{
    name: string
    x: number
    y: number
    summary?: Summary
  } | null>(null)

  useEffect(() => {
    let active = true
    fetch("/tlaxcala-municipios.geojson")
      .then((response) => response.json())
      .then((payload: GeoCollection) => {
        if (active) setCollection(payload)
      })
      .catch(() => {
        if (active) setCollection(null)
      })
    return () => {
      active = false
    }
  }, [])

  const { featuresWithPath, maxCases } = useMemo(() => {
    if (!collection) return { featuresWithPath: [], maxCases: 0 }
    const projection = geoMercator().fitExtent(
      [
        [20, 16],
        [780, 394],
      ],
      collection as unknown as GeoPermissibleObjects,
    )
    const pathGen = geoPath(projection)
    const maxVal = Math.max(...summaries.map((item) => item.cases), 0)
    const mapped = collection.features.map((feat, idx) => {
      const name = feat.properties.NOMGEO || feat.properties.NOM_MUN || `Municipio ${idx + 1}`
      const summary = findSummaryForGeoName(name, summaries)
      const cases = summary?.cases ?? 0
      return {
        id: feat.properties.CVEGEO || feat.properties.CVE_MUN || name,
        name,
        d: pathGen(feat as unknown as GeoPermissibleObjects) ?? "",
        summary,
        cases,
        fill: choroplethColor(cases, maxVal),
      }
    })
    return { featuresWithPath: mapped, maxCases: maxVal }
  }, [collection, summaries])

  const activeSummary =
    activeMunicipalityFilter !== labels.allZones
      ? summaries.find((item) => item.name === activeMunicipalityFilter) ??
        findSummaryForGeoName(activeMunicipalityFilter, summaries)
      : summaries[0]

  const isFilteredByMun = activeMunicipalityFilter !== labels.allZones

  return (
    <section className="panel map-panel">
      <div className="panel-heading">
        <div>
          <h2>Cobertura por municipio</h2>
          <p>60 municipios de Tlaxcala · pasa el cursor para explorar o haz clic para filtrar.</p>
        </div>
        {isFilteredByMun && (
          <button
            type="button"
            className="link-inline"
            onClick={() => onFilterMunicipality(labels.allZones)}
            title="Mostrar los 60 municipios"
          >
            <RotateCcw size={12} /> Ver todos
          </button>
        )}
      </div>

      <div className="map-stage choropleth-stage">
        <svg
          className="choropleth-svg"
          viewBox="0 0 800 410"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Mapa coroplético de los 60 municipios de Tlaxcala"
        >
          {featuresWithPath.map((feat) => {
            const isSelected = isFilteredByMun && municipalitiesMatch(feat.name, activeMunicipalityFilter)
            const isHovered = hovered?.name === feat.name
            const isDimmed = isFilteredByMun && !isSelected
            return (
              <path
                key={feat.id}
                d={feat.d}
                fill={feat.fill}
                className={`mun-polygon${isSelected ? " is-selected" : ""}${isHovered ? " is-hovered" : ""}${isDimmed ? " is-dimmed" : ""}`}
                tabIndex={0}
                role="button"
                aria-label={`${feat.name}: ${fmt(feat.cases)} casos`}
                onMouseEnter={(event) => {
                  setHovered({
                    name: feat.name,
                    x: event.clientX,
                    y: event.clientY,
                    summary: feat.summary,
                  })
                }}
                onMouseMove={(event) => {
                  setHovered((prev) =>
                    prev && prev.name === feat.name
                      ? { ...prev, x: event.clientX, y: event.clientY }
                      : prev,
                  )
                }}
                onMouseLeave={() => setHovered((prev) => (prev?.name === feat.name ? null : prev))}
                onFocus={(event) => {
                  const rect = event.currentTarget.getBoundingClientRect()
                  setHovered({
                    name: feat.name,
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2,
                    summary: feat.summary,
                  })
                }}
                onBlur={() => setHovered((prev) => (prev?.name === feat.name ? null : prev))}
                onClick={() => {
                  if (isSelected) {
                    onFilterMunicipality(labels.allZones)
                    return
                  }
                  const targetFilter = findFilterValueForGeoName(feat.name, municipalities)
                  if (targetFilter) {
                    onFilterMunicipality(targetFilter)
                  }
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault()
                    if (isSelected) {
                      onFilterMunicipality(labels.allZones)
                      return
                    }
                    const targetFilter = findFilterValueForGeoName(feat.name, municipalities)
                    if (targetFilter) {
                      onFilterMunicipality(targetFilter)
                    }
                  }
                }}
              />
            )
          })}
        </svg>
      </div>

      {hovered && (
        <MapHoverCard
          zoneName={hovered.name}
          anchorX={hovered.x}
          anchorY={hovered.y}
          summary={hovered.summary}
          totalCases={totalCases}
          hasPersonIds={hasPersonIds}
          hasCapacityData={hasCapacityData}
        />
      )}

      <div className="choropleth-legend">
        <span className="choropleth-zero">
          <i style={{ background: NEUTRAL_ZERO_FILL }} /> 0 registros
        </span>
        <div className="choropleth-ramp">
          <span>Menor</span>
          <div className="ramp-swatches" aria-hidden="true">
            {ORANGE_SCALE.map((hex) => (
              <i key={hex} style={{ background: hex }} />
            ))}
          </div>
          <span>Mayor ({fmt(maxCases)})</span>
        </div>
      </div>

      {activeSummary && (
        <div className="selected-detail">
          <div className="detail-pin">
            <MapPin size={15} />
          </div>
          <div className="detail-location">
            <span>{isFilteredByMun ? "MUNICIPIO FILTRADO" : "MAYOR VOLUMEN"}</span>
            <strong>{activeSummary.name}</strong>
          </div>
          <div className="detail-stat">
            <span>CASOS</span>
            <b>
              {fmtMetric(
                activeSummary.cases,
                activeSummary.casesValidCount,
                activeSummary.casesNaCount,
                activeSummary.casesMissingCount,
              )}
            </b>
          </div>
          {hasPersonIds && (
            <div className="detail-stat">
              <span>PERSONAS</span>
              <b>{fmt(activeSummary.uniquePeople)}</b>
            </div>
          )}
          {hasResidenceDistinction && (
            <div className="detail-stat">
              <span>RESIDENCIA</span>
              <b>{fmt(activeSummary.residenceCases)}</b>
            </div>
          )}
          {hasCapacityData && (
            <>
              <div className="detail-stat">
                <span>ATENCIONES</span>
                <b>
                  {fmtMetric(
                    activeSummary.capacity,
                    activeSummary.capacityValidCount,
                    activeSummary.capacityNaCount,
                    activeSummary.capacityMissingCount,
                  )}
                </b>
              </div>
              <div className="detail-stat">
                <span>BRECHA</span>
                <b className={activeSummary.ratio >= 1.3 ? "text-priority" : ""}>{gap(activeSummary.ratio)}</b>
              </div>
            </>
          )}
          {dynamicMetrics.slice(0, 2).map((metric) => {
            const stat = activeSummary.extraMetrics?.[metric.key]
            if (!stat || stat.avg === null) return null
            return (
              <div className="detail-stat" key={metric.key}>
                <span>PROM. {humanizeColumnLabel(metric.label).toUpperCase()}</span>
                <b>{fmt(stat.avg)}</b>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function MapHoverCard({
  zoneName,
  anchorX,
  anchorY,
  summary,
  totalCases,
  hasPersonIds,
  hasCapacityData,
}: {
  zoneName: string
  anchorX: number
  anchorY: number
  summary?: Summary
  totalCases: number
  hasPersonIds: boolean
  hasCapacityData: boolean
}) {
  const cardWidth = 320
  const estimatedHeight = summary ? 275 : 95
  const vw = window.innerWidth
  const vh = window.innerHeight
  const spaceRight = vw - anchorX
  const left =
    spaceRight >= cardWidth + 24
      ? anchorX + 16
      : Math.max(8, Math.min(anchorX - cardWidth - 16, vw - cardWidth - 8))
  const top = Math.max(8, Math.min(anchorY - 36, vh - estimatedHeight - 8))

  const cases = summary?.cases ?? 0
  const sharePct = totalCases > 0 ? ((cases / totalCases) * 100).toFixed(1) : "0.0"
  const violence = summary?.violenceBreakdown ?? []
  const maxV = Math.max(...violence.map((v) => v.cases), 1)
  const years = summary?.yearlyTrend ?? []
  const maxY = Math.max(...years.map((y) => y.cases), 1)
  const lastYear = years.at(-1)
  const lastDelta = lastYear?.delta ?? null
  const lastDeltaPct = lastYear?.deltaPct ?? null

  return createPortal(
    <div
      className="map-hover-card"
      role="tooltip"
      style={{ top: `${top}px`, left: `${left}px`, width: `${Math.min(cardWidth, vw - 16)}px` }}
    >
      <div className="mhc-head">
        <div>
          <strong>{zoneName}</strong>
          <span>
            {summary
              ? `${fmtMetric(summary.cases, summary.casesValidCount, summary.casesNaCount, summary.casesMissingCount)} casos (${sharePct}% del total)${
                  hasPersonIds ? ` · ${fmt(summary.uniquePeople)} personas únicas` : ""
                }`
              : "0 registros en esta selección"}
          </span>
        </div>
        {hasCapacityData && summary && (
          <span className={`status-pill ${summary.classification.color}`}>{gap(summary.ratio)}</span>
        )}
      </div>

      {summary && (
        <>
          <div className="mhc-section">
            <div className="mhc-title">Tipos de violencia</div>
            {violence.length === 0 ? (
              <p className="mhc-empty">Sin desglose disponible.</p>
            ) : (
              <div className="mhc-bars">
                {violence.slice(0, 5).map((item) => {
                  const pct = item.cases === 0 ? 0 : Math.max(4, (item.cases / maxV) * 100)
                  return (
                    <div className="mhc-bar-row" key={item.name}>
                      <span className="mhc-bar-name" title={item.name}>
                        {item.name}
                      </span>
                      <span className="mhc-bar-track">
                        <i style={{ width: `${pct}%` }} />
                      </span>
                      <span className="mhc-bar-val">{fmt(item.cases)}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="mhc-section">
            <div className="mhc-title-row">
              <span className="mhc-title">Evolución anual</span>
              {lastDelta !== null && (
                <span className={`mhc-delta ${lastDelta > 0 ? "up" : lastDelta < 0 ? "down" : "flat"}`}>
                  {lastDelta > 0 ? <TrendingUp size={11} /> : lastDelta < 0 ? <TrendingDown size={11} /> : null}
                  {lastDelta > 0
                    ? `Subió ${fmt(lastDelta)}`
                    : lastDelta < 0
                      ? `Bajó ${fmt(Math.abs(lastDelta))}`
                      : "Sin cambio"}
                  {lastDeltaPct !== null ? ` (${fmt(Math.abs(lastDeltaPct))}%)` : ""}
                </span>
              )}
            </div>
            {years.length === 0 ? (
              <p className="mhc-empty">Sin serie anual disponible.</p>
            ) : (
              <div className="mhc-years">
                {years.map((yr) => {
                  const h = yr.cases === 0 ? 0 : Math.max(6, (yr.cases / maxY) * 100)
                  const deltaTone = yr.delta === null ? "" : yr.delta > 0 ? "up" : yr.delta < 0 ? "down" : "flat"
                  return (
                    <div className="mhc-year-col" key={yr.year}>
                      <span className="mhc-year-val">{fmt(yr.cases)}</span>
                      <div className="mhc-year-bar-wrap">
                        <i className={`mhc-year-bar ${deltaTone}`} style={{ height: `${h}%` }} />
                      </div>
                      <span className="mhc-year-lbl">{yr.year}</span>
                      <span className={`mhc-year-chg ${deltaTone}`}>
                        {yr.delta === null
                          ? "base"
                          : yr.delta > 0
                            ? `↑ ${fmt(yr.delta)}`
                            : yr.delta < 0
                              ? `↓ ${fmt(Math.abs(yr.delta))}`
                              : "0"}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>,
    document.body,
  )
}
