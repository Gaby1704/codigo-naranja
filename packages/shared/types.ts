export type ClassificationColor = "priority" | "elevated" | "watch" | "stable"

export type Classification = {
  label: string
  action: string
  color: ClassificationColor
}

export type MunicipalityViolenceItem = {
  name: string
  cases: number
  records: number
}

export type MunicipalityYearItem = {
  year: string
  cases: number
  delta: number | null
  deltaPct: number | null
}

export type SummaryExtraMetric = {
  avg: number | null
  mode?: number | null
  modeCount?: number
  min: number | null
  max: number | null
  validCount: number
}

export type Summary = {
  name: string
  cases: number
  capacity: number
  ratio: number
  count: number
  uniquePeople: number
  residenceCases: number
  casesValidCount: number
  casesZeroCount: number
  casesNaCount: number
  casesMissingCount: number
  capacityValidCount: number
  capacityZeroCount: number
  capacityNaCount: number
  capacityMissingCount: number
  avgCasesPerRecord: number | null
  avgCapacityPerRecord: number | null
  violenceBreakdown: MunicipalityViolenceItem[]
  yearlyTrend: MunicipalityYearItem[]
  undatedCases?: number
  extraMetrics?: Record<string, SummaryExtraMetric>
  extraDimensions?: Record<string, string>
  tableCounts?: Record<string, number>
  classification: Classification
}

export type Trend = {
  period: string
  cases: number
  capacity: number
  uniquePeople: number
  complete: boolean
}

export type MobileRouteStop = {
  zone: string
  rank: number
  intervention: string
  reason: string
  cases: number
  capacity: number
  ratio: number
  color: ClassificationColor
}

export type ForecastPoint = {
  period: string
  cases: number
  capacity: number
}

export type Forecast = {
  available: boolean
  horizonYears: number
  direction: "al alza" | "estable" | "a la baja" | "insuficiente"
  annualDeltaCases: number
  annualDeltaCapacity: number
  points: ForecastPoint[]
  completePeriodsUsed: string[]
  excludedIncompletePeriods: string[]
  assumptions: string
  proposals: string[]
}

export type DimensionLabels = {
  zone: string
  period: string
  violence: string
  service: string
  cases: string
  capacity: string
}

export type DynamicBreakdownItem = {
  name: string
  cases: number
  records: number
  sharePct: number
}

export type DynamicBreakdown = {
  key: string
  label: string
  kind: "category" | "status" | "temporal" | "numeric"
  filterField: "violence" | "service" | "period" | "zone" | null
  totalCategories: number
  items: DynamicBreakdownItem[]
}

export type DynamicMetric = {
  key: string
  label: string
  sum: number
  avg: number | null
  mode?: number | null
  modeCount?: number
  min: number | null
  max: number | null
  validCount: number
  zeroCount: number
  naCount: number
  missingCount: number
}

export type Audit = {
  processed: number
  valid: number
  removed: number
  uniquePeople: number
  multiCasePeople: number
  zeroValues: number
  notApplicable: number
  missingValues: number
  hasResidenceDistinction: boolean
  hasEventDateDistinction: boolean
}

export type DashboardSource = {
  fileName: string | null
  synthetic: boolean
  audit: Audit | null
}

export type RecordRow = {
  zone: string
  period: string
  violence: string
  service: string
  personId: string
  cases: number | null
  casesStatus: string
  capacity: number | null
  capacityStatus: string
  extraDims: Record<string, string>
  extraMetrics: Record<string, number | null>
  extraMetricStatuses: Record<string, string>
}

export type RecordsPage = {
  total: number
  offset: number
  limit: number
  rows: RecordRow[]
}

export type Dashboard = {
  periods: string[]
  years: string[]
  months: string[]
  days: string[]
  appliedYear: string
  municipalities: string[]
  violenceTypes: string[]
  serviceTypes: string[]
  summaries: Summary[]
  trends: Trend[]
  totalCases: number
  totalCapacity: number
  totalPeople: number
  totalRecords: number
  hasData?: boolean
  hasPersonIds: boolean
  hasCapacityData: boolean
  hasResidenceDistinction: boolean
  hasEventDateDistinction: boolean
  missingCasesCount: number
  naCasesCount: number
  missingCapacityCount: number
  naCapacityCount: number
  undatedCasesCount?: number
  priorityCount: number
  dimensionLabels: DimensionLabels
  extraDimensions: string[]
  tableDimensions?: string[]
  dynamicBreakdowns: DynamicBreakdown[]
  dynamicMetrics: DynamicMetric[]
  recordRows: RecordRow[]
  mobileRoute: MobileRouteStop[]
  forecast: Forecast
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
  residenceZone: string
  period: string
  eventDate: string
  violence: string
  service: string
  cases: string
  capacity: string
  person: string
  periodStatus: string
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
  detectedDimensions: string[]
  detectedMetrics: string[]
}

export type ZonePoint = {
  name: string
  x: number
  y: number
  labelPos?: "left" | "right" | "top" | "bottom"
}
