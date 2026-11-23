import { geoMercator, geoPath } from "d3-geo"
import type { GeoPermissibleObjects } from "d3-geo"
import { CircleHelp, MapPin } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import type { Summary } from "../../../../packages/shared/types"
import { fmt, gap } from "../lib/format"
import { zones } from "../lib/shared"

function IconButton({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <button type="button" title={title} className="icon-button">
      {children}
    </button>
  )
}

export function MapPanel({
  summaries,
  selected,
  onSelect,
}: {
  summaries: Summary[]
  selected: string
  onSelect: (name: string) => void
}) {
  const selectedSummary = summaries.find((item) => item.name === selected) ?? summaries[0]
  const colorOf = (name: string) => summaries.find((item) => item.name === name)?.classification.color ?? "stable"

  return (
    <section className="panel map-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            LECTURA TERRITORIAL <span className="eyebrow-slash">/</span> 01
          </span>
          <h2>Prioridad por municipio</h2>
          <p>Relación de casos registrados frente a capacidad de atención</p>
        </div>
        <IconButton title="Información del mapa">
          <CircleHelp size={16} />
        </IconButton>
      </div>
      <div className="map-stage">
        <div className="map-backdrop" />
        <div className="map-grid-lines" />
        <TerritoryOutline />
        <span className="map-caption">
          TLAXCALA <i>·</i> VISTA ESQUEMÁTICA
        </span>
        {zones.map((zone) => {
          const item = summaries.find((row) => row.name === zone.name)
          return (
            <button
              type="button"
              key={zone.name}
              aria-label={`${zone.name}: ${item?.cases ?? 0} casos`}
              title={`${zone.name} · ${fmt(item?.cases ?? 0)} casos · ${gap(item?.ratio ?? 0)} de brecha relativa`}
              className={`map-node ${colorOf(zone.name)} ${selected === zone.name ? "selected" : ""}`}
              style={{ left: `${zone.x}%`, top: `${zone.y}%` }}
              onClick={() => onSelect(zone.name)}
            >
              <span className="node-dot" />
              <span className="node-label">{zone.name}</span>
            </button>
          )
        })}
        <div className="map-north">
          N<br />
          <span>↑</span>
        </div>
        <div className="map-scale">
          <i />
          <i />
          <i />
          <span>Representación esquemática · no a escala</span>
        </div>
      </div>
      <div className="map-legend">
        <span>
          <i className="legend-dot priority" /> Alta demanda · baja cobertura
        </span>
        <span>
          <i className="legend-dot elevated" /> Optimizar capacidad
        </span>
        <span>
          <i className="legend-dot watch" /> Posible subregistro
        </span>
        <span>
          <i className="legend-dot stable" /> Cobertura estable
        </span>
      </div>
      {selectedSummary && (
        <div className="selected-detail">
          <div className="detail-pin">
            <MapPin size={16} />
          </div>
          <div className="detail-location">
            <span>MUNICIPIO SELECCIONADO</span>
            <strong>{selectedSummary.name}</strong>
          </div>
          <div className="detail-stat">
            <span>CASOS</span>
            <b>{fmt(selectedSummary.cases)}</b>
          </div>
          <div className="detail-stat">
            <span>CAPACIDAD</span>
            <b>{fmt(selectedSummary.capacity)}</b>
          </div>
          <div className="detail-stat">
            <span>BRECHA ESTIMADA</span>
            <b className={selectedSummary.ratio >= 1.3 ? "text-priority" : ""}>{gap(selectedSummary.ratio)}</b>
          </div>
          <div className="detail-recommendation">
            <span className={`status-pill ${selectedSummary.classification.color}`}>
              {selectedSummary.classification.label}
            </span>
            <p>{selectedSummary.classification.action}</p>
          </div>
        </div>
      )}
    </section>
  )
}

function TerritoryOutline() {
  const [collection, setCollection] = useState<GeoPermissibleObjects | null>(null)

  useEffect(() => {
    let active = true
    fetch("/tlaxcala.geojson")
      .then((response) => response.json())
      .then((payload: GeoPermissibleObjects) => {
        if (active) setCollection(payload)
      })
      .catch(() => {
        if (active) setCollection(null)
      })
    return () => {
      active = false
    }
  }, [])

  const outline = useMemo(() => {
    if (!collection) return ""
    const projection = geoMercator().center([-98.16, 19.4]).scale(29000).translate([400, 185])
    return geoPath(projection)(collection) ?? ""
  }, [collection])

  return (
    <svg className="territory-map" viewBox="0 0 800 370" role="img" aria-label="Contorno territorial del estado de Tlaxcala">
      <path d={outline} fill="#f5ddd4" stroke="#bb684c" strokeWidth={1.7} />
    </svg>
  )
}
