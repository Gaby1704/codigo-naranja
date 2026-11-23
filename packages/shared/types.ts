export type ClassificationColor = "priority" | "elevated" | "watch" | "stable"

export type Classification = {
  label: string
  action: string
  color: ClassificationColor
}

export type Summary = {
  name: string
  cases: number
  capacity: number
  ratio: number
  count: number
  classification: Classification
}

export type Trend = {
  period: string
  cases: number
  capacity: number
}

export type Audit = {
  processed: number
  valid: number
  removed: number
  imputed: number
  personDuplicates: number
}

export type DashboardSource = {
  fileName: string | null
  synthetic: boolean
  audit: Audit | null
}

export type Dashboard = {
  periods: string[]
  municipalities: string[]
  violenceTypes: string[]
  serviceTypes: string[]
  summaries: Summary[]
  trends: Trend[]
  totalCases: number
  totalCapacity: number
  priorityCount: number
  source: DashboardSource
}

export type PublicUser = {
  name: string
  email: string
  role: "admin" | "user"
}

export type AuthResponse = {
  user: PublicUser | null
}

export type ColumnMapping = {
  zone: string
  period: string
  violence: string
  service: string
  cases: string
  capacity: string
  person: string
}

export type UploadPreview = {
  uploadId: string
  name: string
  sheet: string
  sheets: string[]
  headers: string[]
  preview: Record<string, string>[]
  rowCount: number
  suggestedMapping: ColumnMapping
}

export type ZonePoint = {
  name: string
  x: number
  y: number
}

export type RecordRow = {
  zone: string
  period: string
  violence: string
  service: string
  cases: number
  capacity: number
}
