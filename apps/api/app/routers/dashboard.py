import csv
from io import StringIO

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.schemas import DashboardResponse, RecordsPageResponse
from app.services.analytics import build_dashboard, query_records
from app.services.catalog import load_active
from app.services.constants import load_constants

router = APIRouter(tags=["dashboard"])


def _resolve_filters(
    records: list[dict],
    period: str,
    year: str,
    month: str,
    day: str,
    municipality: str,
    violence: str,
    service: str,
) -> dict[str, str]:
    labels = load_constants()["filters"]
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

    return {
        "period": resolved_period,
        "year": resolved_year or "Todos",
        "month": month.strip() or "Todos",
        "day": day.strip() or "Todos",
        "municipality": municipality or labels["allZones"],
        "violence": violence or labels["allViolence"],
        "service": service or labels["allServices"],
    }


def _csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


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
    records, source, metadata = load_active()
    filters = _resolve_filters(records, period, year, month, day, municipality, violence, service)
    return build_dashboard(records, filters, source, metadata)


@router.get("/dashboard/records", response_model=RecordsPageResponse)
def dashboard_records(
    period: str = Query(default="", max_length=80),
    year: str = Query(default="", max_length=20),
    month: str = Query(default="", max_length=20),
    day: str = Query(default="", max_length=20),
    municipality: str = Query(default="", max_length=120),
    violence: str = Query(default="", max_length=120),
    service: str = Query(default="", max_length=120),
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict:
    records, _source, metadata = load_active()
    filters = _resolve_filters(records, period, year, month, day, municipality, violence, service)
    result = query_records(records, filters, metadata, q=q, offset=offset, limit=limit)
    return {
        "total": result["total"],
        "offset": result["offset"],
        "limit": result["limit"],
        "rows": result["rows"],
    }


@router.get("/dashboard/records.csv")
def dashboard_records_csv(
    period: str = Query(default="", max_length=80),
    year: str = Query(default="", max_length=20),
    month: str = Query(default="", max_length=20),
    day: str = Query(default="", max_length=20),
    municipality: str = Query(default="", max_length=120),
    violence: str = Query(default="", max_length=120),
    service: str = Query(default="", max_length=120),
    q: str = Query(default="", max_length=120),
) -> Response:
    records, _source, metadata = load_active()
    filters = _resolve_filters(records, period, year, month, day, municipality, violence, service)
    result = query_records(records, filters, metadata, q=q, offset=0, limit=None)
    extra_dims = result["extraDimensions"]
    extra_metrics = result["extraMetrics"]
    table_dims = result["tableDimensions"]
    has_person = result["hasPersonIds"]
    has_cap = result["hasCapacityData"]

    def fmt_val(val: float | None, status: str) -> str:
        if val is not None:
            return str(int(val)) if float(val).is_integer() else str(val)
        return "N/A" if status == "na" else "Sin dato"

    buf = StringIO()
    writer = csv.writer(buf)
    headers = [
        "Periodo",
        "Municipio",
        "Tipo de violencia",
        "Servicio",
        *(["Expediente"] if has_person else []),
        *table_dims,
        "Casos",
        *(["Atenciones"] if has_cap else []),
        *extra_dims,
        *extra_metrics,
    ]
    writer.writerow([_csv_cell(h) for h in headers])
    for row in result["rows"]:
        line = [
            row["period"],
            row["zone"],
            row["violence"],
            row["service"],
            *([row["personId"] or "Sin dato"] if has_person else []),
            *[row["extraDims"].get(col, "Sin dato") for col in table_dims],
            fmt_val(row["cases"], row["casesStatus"]),
            *([fmt_val(row["capacity"], row["capacityStatus"])] if has_cap else []),
            *[row["extraDims"].get(col, "Sin dato") for col in extra_dims],
            *[fmt_val(row["extraMetrics"].get(col), row["extraMetricStatuses"].get(col, "missing")) for col in extra_metrics],
        ]
        writer.writerow([_csv_cell(cell) for cell in line])

    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="listado-registros-smet.csv"'},
    )
