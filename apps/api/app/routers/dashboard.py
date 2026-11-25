from fastapi import APIRouter, Query

from app.schemas import DashboardResponse
from app.services.analytics import build_dashboard
from app.services.catalog import load_active
from app.services.constants import load_constants

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    period: str = Query(default="", max_length=80),
    year: str = Query(default="", max_length=20),
    month: str = Query(default="", max_length=20),
    day: str = Query(default="", max_length=20),
    municipality: str = Query(default="", max_length=120),
    violence: str = Query(default="", max_length=120),
    service: str = Query(default="", max_length=120),
) -> dict:
    labels = load_constants()["filters"]
    records, source, metadata = load_active()
    available_years = {str(row["period"])[:4] for row in records if str(row["period"])[:4].isdigit()}

    has_granular = any(val.strip() for val in (year, month, day))
    if period:
        resolved_period = period
        resolved_year = year.strip()
    elif has_granular:
        resolved_period = labels["allPeriods"]
        resolved_year = year.strip()
    elif labels["defaultPeriod"] in available_years or labels["defaultPeriod"] in {row["period"] for row in records}:
        resolved_period = labels["allPeriods"]
        resolved_year = labels["defaultPeriod"]
    else:
        resolved_period = labels["allPeriods"]
        resolved_year = "Todos"

    filters = {
        "period": resolved_period,
        "year": resolved_year or "Todos",
        "month": month.strip() or "Todos",
        "day": day.strip() or "Todos",
        "municipality": municipality or labels["allZones"],
        "violence": violence or labels["allViolence"],
        "service": service or labels["allServices"],
    }
    return build_dashboard(records, filters, source, metadata)
