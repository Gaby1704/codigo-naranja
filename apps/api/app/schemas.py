from typing import Literal

from pydantic import BaseModel, Field


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=72)


class PublicUser(BaseModel):
    name: str
    email: str
    role: Literal["admin", "user"]


class AuthResponse(BaseModel):
    user: PublicUser | None


class Classification(BaseModel):
    label: str
    action: str
    color: Literal["priority", "elevated", "watch", "stable"]


class MunicipalityViolenceItem(BaseModel):
    name: str
    cases: float
    records: int


class MunicipalityYearItem(BaseModel):
    year: str
    cases: float
    delta: float | None
    deltaPct: float | None


class Summary(BaseModel):
    name: str
    cases: float
    capacity: float
    ratio: float
    count: int
    uniquePeople: int
    residenceCases: float
    casesValidCount: int
    casesZeroCount: int
    casesNaCount: int
    casesMissingCount: int
    capacityValidCount: int
    capacityZeroCount: int
    capacityNaCount: int
    capacityMissingCount: int
    avgCasesPerRecord: float | None
    avgCapacityPerRecord: float | None
    violenceBreakdown: list[MunicipalityViolenceItem] = []
    yearlyTrend: list[MunicipalityYearItem] = []
    classification: Classification


class Trend(BaseModel):
    period: str
    cases: float
    capacity: float
    uniquePeople: int
    complete: bool


class MobileRouteStop(BaseModel):
    zone: str
    rank: int
    intervention: str
    reason: str
    cases: float
    capacity: float
    ratio: float
    color: Literal["priority", "elevated", "watch", "stable"]


class ForecastPoint(BaseModel):
    period: str
    cases: float
    capacity: float


class Forecast(BaseModel):
    available: bool
    horizonYears: int
    direction: Literal["al alza", "estable", "a la baja", "insuficiente"]
    annualDeltaCases: float
    annualDeltaCapacity: float
    points: list[ForecastPoint]
    completePeriodsUsed: list[str]
    excludedIncompletePeriods: list[str]
    assumptions: str
    proposals: list[str]


class DimensionLabels(BaseModel):
    zone: str
    period: str
    violence: str
    service: str
    cases: str
    capacity: str


class DynamicBreakdownItem(BaseModel):
    name: str
    cases: float
    records: int
    sharePct: float


class DynamicBreakdown(BaseModel):
    key: str
    label: str
    kind: Literal["category", "status", "temporal"]
    filterField: Literal["violence", "service", "period", "zone"] | None
    totalCategories: int
    items: list[DynamicBreakdownItem]


class DynamicMetric(BaseModel):
    key: str
    label: str
    sum: float
    avg: float | None
    min: float | None
    max: float | None
    validCount: int
    zeroCount: int
    naCount: int
    missingCount: int


class Audit(BaseModel):
    processed: int
    valid: int
    removed: int
    uniquePeople: int
    multiCasePeople: int
    zeroValues: int
    notApplicable: int
    missingValues: int
    hasResidenceDistinction: bool
    hasEventDateDistinction: bool


class Source(BaseModel):
    fileName: str | None
    synthetic: bool
    audit: Audit | None


class DashboardResponse(BaseModel):
    periods: list[str]
    years: list[str] = []
    months: list[str] = []
    days: list[str] = []
    appliedYear: str = ""
    municipalities: list[str]
    violenceTypes: list[str]
    serviceTypes: list[str]
    summaries: list[Summary]
    trends: list[Trend]
    totalCases: float
    totalCapacity: float
    totalPeople: int
    totalRecords: int
    hasPersonIds: bool
    hasCapacityData: bool
    hasResidenceDistinction: bool
    hasEventDateDistinction: bool
    missingCasesCount: int
    naCasesCount: int
    missingCapacityCount: int
    naCapacityCount: int
    priorityCount: int
    dimensionLabels: DimensionLabels
    dynamicBreakdowns: list[DynamicBreakdown]
    dynamicMetrics: list[DynamicMetric]
    mobileRoute: list[MobileRouteStop]
    forecast: Forecast
    source: Source


class SuggestedMapping(BaseModel):
    zone: str = ""
    residenceZone: str = ""
    period: str = ""
    eventDate: str = ""
    violence: str = ""
    service: str = ""
    cases: str = ""
    capacity: str = ""
    person: str = ""
    periodStatus: str = ""


class UploadPreview(BaseModel):
    uploadId: str
    name: str
    sheet: str
    sheets: list[str]
    headers: list[str]
    preview: list[dict[str, str]]
    rowCount: int
    suggestedMapping: SuggestedMapping
    detectedDimensions: list[str] = []
    detectedMetrics: list[str] = []


class MappingBody(BaseModel):
    zone: str = Field(default="", max_length=200)
    residenceZone: str = Field(default="", max_length=200)
    period: str = Field(default="", max_length=200)
    eventDate: str = Field(default="", max_length=200)
    violence: str = Field(default="", max_length=200)
    service: str = Field(default="", max_length=200)
    cases: str = Field(default="", max_length=200)
    capacity: str = Field(default="", max_length=200)
    person: str = Field(default="", max_length=200)
    periodStatus: str = Field(default="", max_length=200)


class ApplyBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
    mapping: MappingBody


class SheetBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
