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
    hasResidenceDistinction: bool
    hasEventDateDistinction: bool
    missingCasesCount: int
    naCasesCount: int
    missingCapacityCount: int
    naCapacityCount: int
    priorityCount: int
    mobileRoute: list[MobileRouteStop]
    forecast: Forecast
    source: Source


class SuggestedMapping(BaseModel):
    zone: str
    residenceZone: str = ""
    period: str
    eventDate: str = ""
    violence: str
    service: str
    cases: str
    capacity: str
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


class MappingBody(BaseModel):
    zone: str = Field(min_length=1, max_length=200)
    residenceZone: str = Field(default="", max_length=200)
    period: str = Field(min_length=1, max_length=200)
    eventDate: str = Field(default="", max_length=200)
    violence: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=200)
    cases: str = Field(min_length=1, max_length=200)
    capacity: str = Field(min_length=1, max_length=200)
    person: str = Field(default="", max_length=200)
    periodStatus: str = Field(default="", max_length=200)


class ApplyBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
    mapping: MappingBody


class SheetBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
