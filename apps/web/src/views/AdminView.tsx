import { ArrowDownToLine, ArrowUpRight, Check, FileSpreadsheet, ShieldCheck, Sparkles, Upload } from "lucide-react"
import { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import type { Audit, ColumnMapping, UploadPreview } from "../../../../packages/shared/types"
import { applyDataset, changeSheet, downloadTemplate, uploadDataset } from "../api"
import { allFilters } from "../lib/shared"
import { useBoard } from "../state/board"

const CORE_FIELDS: Array<[keyof ColumnMapping, string, string]> = [
  ["zone", "Dimensión territorial / grupo principal", "Sin columna territorial (agrupación general)"],
  ["period", "Periodo / fecha / corte", "Sin columna de periodo"],
  ["violence", "Categoría principal (ej. tipo de violencia / modalidad)", "Sin columna de categoría"],
  ["service", "Subcategoría o servicio (ej. atención / canalización)", "Sin columna de servicio"],
  ["cases", "Métrica principal de casos / conteo", "1 fila = 1 caso registrado"],
  ["capacity", "Métrica de atenciones / capacidad", "Sin columna de capacidad"],
]

const OPTIONAL_FIELDS: Array<[keyof ColumnMapping, string, string]> = [
  ["person", "Expediente / ID persona única", "Sin columna de expediente"],
  ["residenceZone", "Municipio de residencia / pertenencia", "No incluido"],
  ["eventDate", "Fecha o periodo del hecho", "No incluido"],
  ["periodStatus", "Estado del periodo (completo / parcial)", "Todos los periodos completos"],
]

export function AdminView() {
  const navigate = useNavigate()
  const { setFilters, reload } = useBoard()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [notice, setNotice] = useState("")
  const [preview, setPreview] = useState<UploadPreview | null>(null)
  const [mapping, setMapping] = useState<ColumnMapping | null>(null)
  const [appliedResult, setAppliedResult] = useState<{ fileName: string; audit: Audit } | null>(null)
  const [busy, setBusy] = useState(false)

  async function loadFile(file?: File) {
    if (!file) return
    const lower = file.name.toLowerCase()
    if (!lower.endsWith(".xlsx") && !lower.endsWith(".xls")) {
      setNotice("Selecciona un archivo Excel .xlsx o .xls ya procesado.")
      return
    }
    setBusy(true)
    setNotice("")
    setAppliedResult(null)
    try {
      const next = await uploadDataset(file)
      setPreview(next)
      setMapping(next.suggestedMapping)
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "No fue posible leer el archivo.")
    } finally {
      setBusy(false)
    }
  }

  async function onSheet(name: string) {
    if (!preview) return
    setBusy(true)
    setNotice("")
    try {
      const next = await changeSheet(preview.uploadId, name)
      setPreview(next)
      setMapping(next.suggestedMapping)
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "La hoja seleccionada no contiene registros.")
    } finally {
      setBusy(false)
    }
  }

  async function apply() {
    if (!preview || !mapping) return
    setBusy(true)
    setNotice("")
    try {
      const result = await applyDataset(preview.uploadId, preview.sheet, mapping)
      setAppliedResult(result)
      setPreview(null)
      setFilters({ ...allFilters })
      reload()
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "No se pudieron aplicar los datos.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="admin-layout">
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            CENTRO DE DATOS <span className="eyebrow-slash">/</span> 02
          </span>
          <h2>Carga de archivos procesados</h2>
          <p>
            La depuración pesada se realiza fuera del tablero. Puedes cargar cualquier libro Excel ya procesado sin depender de nombres fijos de columnas: las gráficas, filtros y series se adaptan a las dimensiones y métricas detectadas.
          </p>
        </div>
        <button
          type="button"
          className="button secondary"
          onClick={() => {
            downloadTemplate().catch((reason: unknown) => {
              setNotice(reason instanceof Error ? reason.message : "No se pudo descargar la plantilla.")
            })
          }}
        >
          <ArrowDownToLine size={15} /> Descargar plantilla
        </button>
      </div>
      <div
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          void loadFile(event.dataTransfer.files[0])
        }}
      >
        <span className="upload-symbol">
          <Upload size={23} />
        </span>
        <h3>Arrastra tu archivo Excel ya procesado aquí</h3>
        <p>Detección flexible de columnas categóricas, temporales y métricas · Formato .xlsx o .xls</p>
        <button type="button" className="button primary" onClick={() => inputRef.current?.click()} disabled={busy}>
          <FileSpreadsheet size={16} /> Seleccionar archivo
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          className="sr-only"
          onChange={(event) => void loadFile(event.target.files?.[0])}
        />
        <small>Se conservan los ceros reales, se respetan N/A sin convertirlos a 0 y se contabilizan los datos faltantes.</small>
      </div>
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      {appliedResult && (
        <div className="admin-card audit-result" role="status">
          <div className="admin-card-title">
            <div>
              <span className="eyebrow">
                VALIDACIÓN COMPLETADA <span className="eyebrow-slash">/</span> AUDITORÍA
              </span>
              <h3>Archivo aplicado: {appliedResult.fileName}</h3>
              <p>Base de datos actualizada y gráficas recalculadas según la estructura del archivo.</p>
            </div>
            <button type="button" className="button primary" onClick={() => navigate("/")}>
              Ir al tablero <ArrowUpRight size={15} />
            </button>
          </div>
          <div className="audit-metrics-grid">
            <div>
              <span>REGISTROS VÁLIDOS</span>
              <strong>
                {appliedResult.audit.valid} / {appliedResult.audit.processed}
              </strong>
              <small>{appliedResult.audit.removed} descartados (vacíos, duplicados exactos o incoherentes)</small>
            </div>
            <div>
              <span>EXPEDIENTES / PERSONAS ÚNICAS</span>
              <strong>{appliedResult.audit.uniquePeople}</strong>
              <small>{appliedResult.audit.multiCasePeople} con múltiples casos o seguimientos conservados</small>
            </div>
            <div>
              <span>CEROS CONSERVADOS</span>
              <strong>{appliedResult.audit.zeroValues}</strong>
              <small>Valores numéricos iguales a 0 preservados</small>
            </div>
            <div>
              <span>N/A Y FALTANTES</span>
              <strong>
                {appliedResult.audit.notApplicable} N/A · {appliedResult.audit.missingValues} faltantes
              </strong>
              <small>Excluidos de promedios y nunca convertidos en 0</small>
            </div>
          </div>
        </div>
      )}
      {preview && mapping && (
        <div className="admin-card">
          <div className="admin-card-title">
            <div>
              <span className="eyebrow">
                ESQUEMA FLEXIBLE <span className="eyebrow-slash">/</span> 01
              </span>
              <h3>Verifica la asignación de columnas</h3>
              <p>
                Libro: <strong>{preview.name}</strong> · {preview.rowCount} filas detectadas · {preview.headers.length} columnas
              </p>
            </div>
            <span className="file-badge">
              <FileSpreadsheet size={15} /> {preview.sheet}
            </span>
          </div>
          <label className="field-label">
            Hoja del libro
            <select value={preview.sheet} onChange={(event) => void onSheet(event.target.value)}>
              {preview.sheets.map((sheet) => (
                <option key={sheet}>{sheet}</option>
              ))}
            </select>
          </label>
          <div className="mapping-grid">
            {CORE_FIELDS.map(([key, label, emptyLabel]) => (
              <label className="field-label" key={key}>
                {label}
                <select value={mapping[key]} onChange={(event) => setMapping({ ...mapping, [key]: event.target.value })}>
                  <option value="">{emptyLabel}</option>
                  {preview.headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            {OPTIONAL_FIELDS.map(([key, label, emptyLabel]) => (
              <label className="field-label" key={key}>
                {label}
                <select value={mapping[key]} onChange={(event) => setMapping({ ...mapping, [key]: event.target.value })}>
                  <option value="">{emptyLabel}</option>
                  {preview.headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          {(preview.detectedDimensions.length > 0 || preview.detectedMetrics.length > 0) && (
            <div className="detected-schema-box">
              <Sparkles size={15} />
              <div>
                <strong>Columnas adicionales detectadas para gráficas dinámicas:</strong>
                <p>
                  {preview.detectedDimensions.length > 0 && `Dimensiones: ${preview.detectedDimensions.join(", ")}. `}
                  {preview.detectedMetrics.length > 0 && `Métricas: ${preview.detectedMetrics.join(", ")}.`}
                </p>
              </div>
            </div>
          )}
          <div className="preview-table">
            <table>
              <thead>
                <tr>
                  {preview.headers.slice(0, 8).map((header) => (
                    <th key={header}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview.map((row, index) => (
                  <tr key={index}>
                    {preview.headers.slice(0, 8).map((header) => (
                      <td key={header}>{row[header] ?? ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-actions">
            <span>
              <ShieldCheck size={15} /> Adaptación dinámica a la estructura del libro · Un expediente puede tener múltiples registros sin duplicar persona
            </span>
            <button type="button" className="button primary" onClick={() => void apply()} disabled={busy}>
              <Check size={16} /> Cargar a base de datos
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
