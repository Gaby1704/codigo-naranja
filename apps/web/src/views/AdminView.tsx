import { ArrowDownToLine, Check, FileSpreadsheet, ShieldCheck, Upload } from "lucide-react"
import { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import type { ColumnMapping, UploadPreview } from "../../../../packages/shared/types"
import { applyDataset, changeSheet, downloadTemplate, uploadDataset } from "../api"
import { allFilters } from "../lib/shared"
import { useBoard } from "../state/board"

const FIELDS: Array<[keyof ColumnMapping, string]> = [
  ["zone", "Zona / municipio"],
  ["period", "Periodo / año / mes"],
  ["violence", "Tipo de violencia"],
  ["service", "Tipo de servicio"],
  ["cases", "Casos registrados"],
  ["capacity", "Servicios / atenciones registradas"],
]

export function AdminView() {
  const navigate = useNavigate()
  const { setFilters } = useBoard()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [notice, setNotice] = useState("")
  const [preview, setPreview] = useState<UploadPreview | null>(null)
  const [mapping, setMapping] = useState<ColumnMapping | null>(null)
  const [busy, setBusy] = useState(false)

  async function loadFile(file?: File) {
    if (!file) return
    const lower = file.name.toLowerCase()
    if (!lower.endsWith(".xlsx") && !lower.endsWith(".xls")) {
      setNotice("Selecciona un archivo Excel .xlsx o .xls.")
      return
    }
    setBusy(true)
    setNotice("")
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
    if (!mapping.person) {
      setNotice("Para garantizar una alerta por persona, asigna la columna de identificador de persona o expediente antes de aplicar el archivo.")
      return
    }
    setBusy(true)
    setNotice("")
    try {
      await applyDataset(preview.uploadId, preview.sheet, mapping)
      setFilters({ ...allFilters })
      navigate("/")
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "No se pudieron aplicar los datos.")
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
          <h2>Administración de registros</h2>
          <p>Importa y prepara archivos para actualizar el tablero territorial.</p>
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
        <h3>Arrastra tu archivo Excel aquí</h3>
        <p>Registro de casos y/o registro de servicios · Formato .xlsx o .xls</p>
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
        <small>El archivo se valida y limpia en el servidor. No queda una copia fuera del dataset activo.</small>
      </div>
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      {preview && mapping && (
        <div className="admin-card">
          <div className="admin-card-title">
            <div>
              <span className="eyebrow">
                CONFIGURACIÓN <span className="eyebrow-slash">/</span> 01
              </span>
              <h3>Revisa y asigna tus columnas</h3>
              <p>
                Libro: <strong>{preview.name}</strong> · {preview.rowCount} filas detectadas
              </p>
            </div>
            <span className="file-badge">
              <FileSpreadsheet size={15} /> XLSX
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
            {FIELDS.map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <select value={mapping[key]} onChange={(event) => setMapping({ ...mapping, [key]: event.target.value })}>
                  {preview.headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <label className="field-label">
              Identificador de persona / expediente (requerido para deduplicar)
              <select value={mapping.person} onChange={(event) => setMapping({ ...mapping, person: event.target.value })}>
                <option value="">Sin columna de identificador</option>
                {preview.headers.map((header) => (
                  <option key={header} value={header}>
                    {header}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="preview-table">
            <table>
              <thead>
                <tr>
                  {preview.headers.slice(0, 6).map((header) => (
                    <th key={header}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview.map((row, index) => (
                  <tr key={index}>
                    {preview.headers.slice(0, 6).map((header) => (
                      <td key={header}>{row[header] ?? ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-actions">
            <span>
              <ShieldCheck size={15} /> Limpieza automática · alerta única por identificador de persona · duplicados consolidados
            </span>
            <button type="button" className="button primary" onClick={() => void apply()} disabled={busy}>
              <Check size={16} /> Aplicar al tablero
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
