export const fmt = (value: number) => new Intl.NumberFormat("es-MX").format(value)

export const gap = (ratio: number) => `${Math.round(ratio * 100)}%`

export function csvCell(value: string | number) {
  const text = String(value)
  const guarded = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text
  return `"${guarded.replaceAll('"', '""')}"`
}
