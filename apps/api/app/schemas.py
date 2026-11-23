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
    classification: Classification


class Trend(BaseModel):
    period: str
    cases: float
    capacity: float


class Audit(BaseModel):
    processed: int
    valid: int
    removed: int
    imputed: int
    personDuplicates: int


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
    priorityCount: int
    source: Source


class SuggestedMapping(BaseModel):
    zone: str
    period: str
    violence: str
    service: str
    cases: str
    capacity: str
    person: str = ""


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
    period: str = Field(min_length=1, max_length=200)
    violence: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=200)
    cases: str = Field(min_length=1, max_length=200)
    capacity: str = Field(min_length=1, max_length=200)
    person: str = Field(min_length=1, max_length=200)


class ApplyBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
    mapping: MappingBody


class SheetBody(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)
