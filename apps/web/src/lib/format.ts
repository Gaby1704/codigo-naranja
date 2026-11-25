export const fmt = (value: number) => new Intl.NumberFormat("es-MX").format(value)

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
