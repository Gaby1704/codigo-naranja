from fastapi import APIRouter, Query

from app.schemas import DashboardResponse
from app.services.analytics import build_dashboard
from app.services.catalog import load_active
from app.services.constants import load_constants

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    period: str = Query(default="", max_length=80),
    municipality: str = Query(default="", max_length=120),
    violence: str = Query(default="", max_length=120),
    service: str = Query(default="", max_length=120),
) -> dict:
    labels = load_constants()["filters"]
    records, source, metadata = load_active()
    available_periods = {row["period"] for row in records}
    resolved_period = period or (
        labels["defaultPeriod"] if labels["defaultPeriod"] in available_periods else labels["allPeriods"]
    )
    filters = {
        "period": resolved_period,
        "municipality": municipality or labels["allZones"],
        "violence": violence or labels["allViolence"],
        "service": service or labels["allServices"],
    }
    return build_dashboard(records, filters, source, metadata)
