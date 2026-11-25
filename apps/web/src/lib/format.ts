export const fmt = (value: number) => new Intl.NumberFormat("es-MX").format(value)

export const cleanLabel = (value: string) => value.replaceAll("_", " ").replace(/\s+/g, " ").trim()

const HUMAN_LABEL_MAP: Array<[RegExp, string]> = [
  [/^(FECHA[ _]?(DE[ _]?)?REGISTRO|PERIODO([ _]?DE)?([ _]?CORTE)?)$/i, "Periodo"],
  [/^MUNICIPIO([ _]?(DEL[ _]?)?HECHO)?$/i, "Municipio"],
  [/^(TIPO[ _]?(DE[ _]?)?VIOLENCIA|MODALIDAD)$/i, "Tipo de violencia"],
  [/^(SERVICIO([ _]?RECIBIDO)?([ _]?ATENCION)?|TIPO[ _]?(DE[ _]?)?SERVICIO)$/i, "Servicio"],
  [/^(ATENCIONES|CAPACIDAD|SERVICIOS[ _]?ATENCIONES)$/i, "Atenciones"],
  [/^CASOS([ _]?REGISTRADOS)?$/i, "Casos"],
]

export function humanizeColumnLabel(value: string): string {
  const cleaned = cleanLabel(value)
  for (const [pattern, friendly] of HUMAN_LABEL_MAP) {
    if (pattern.test(cleaned)) return friendly
  }
  if (!cleaned) return ""
  const lower = cleaned.toLocaleLowerCase("es-MX")
  return lower.charAt(0).toLocaleUpperCase("es-MX") + lower.slice(1)
}

export function fmtMetric(value: number, validCount: number, naCount: number, missingCount: number): string {
  if (validCount > 0) return fmt(value)
  if (naCount > 0) return "N/A"
  if (missingCount > 0) return "Sin dato"
  return "0"
}

export const gap = (ratio: number) => `${Math.round(ratio * 100)}%`

export function csvCell(value: string | number) {
  const text = String(value)
  const guarded = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text
  return `"${guarded.replaceAll('"', '""')}"`
}
