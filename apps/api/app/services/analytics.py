import re

from app.services.constants import load_constants
from app.services.rules import classify, is_period_incomplete, natural_key, normalize

_YEAR_RE = re.compile(r"^\d{4}$")
_TEMPORAL_HINTS = ("MES", "FECHA", "TRIMESTRE", "PERIODO", "ANIO", "ANO", "SEMANA", "DIA")
_STATUS_HINTS = ("ESTADO", "ESTATUS", "NIVEL", "RIESGO", "ALERTA", "CLASIFIC", "SEM")


def _linear_slope(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return 0.0, values[-1] if values else 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    denom = sum((idx - mean_x) ** 2 for idx in range(n))
    if denom == 0:
        return 0.0, mean_y
    slope = sum((idx - mean_x) * (val - mean_y) for idx, val in enumerate(values)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _build_forecast(all_trends: list[dict], summaries: list[dict]) -> dict:
    complete = [item for item in all_trends if item["complete"]]
    excluded = [item["period"] for item in all_trends if not item["complete"]]

    priority_zones = [item["name"] for item in summaries if item["classification"]["color"] == "priority"][:3]
    watch_zones = [item["name"] for item in summaries if item["classification"]["color"] == "watch"][:3]

    proposals = []
    if priority_zones:
        proposals.append(f"Reforzar la capacidad presencial en {', '.join(priority_zones)}.")
    else:
        proposals.append("Monitorear la capacidad instalada por municipio.")
    if watch_zones:
        proposals.append(f"Fortalecer la detección temprana en {', '.join(watch_zones)} ante posible subregistro.")
    else:
        proposals.append("Mantener la vinculación institucional en zonas periféricas.")
    proposals.append("Estandarizar el seguimiento por expediente único.")

    if len(complete) < 2:
        return {
            "available": False,
            "horizonYears": 5,
            "direction": "insuficiente",
            "annualDeltaCases": 0.0,
            "annualDeltaCapacity": 0.0,
            "points": [],
            "completePeriodsUsed": [item["period"] for item in complete],
            "excludedIncompletePeriods": excluded,
            "assumptions": "Estimación lineal de tendencia a partir del histórico disponible; no representa predicción definitiva ni tasa poblacional.",
            "proposals": proposals,
        }

    cases_series = [float(item["cases"]) for item in complete]
    cap_series = [float(item["capacity"]) for item in complete]
    slope_cases, intercept_cases = _linear_slope(cases_series)
    slope_cap, intercept_cap = _linear_slope(cap_series)

    mean_cases = sum(cases_series) / len(cases_series)
    if mean_cases > 0 and slope_cases > 0.02 * mean_cases:
        direction = "al alza"
    elif mean_cases > 0 and slope_cases < -0.02 * mean_cases:
        direction = "a la baja"
    else:
        direction = "estable"

    last_period = complete[-1]["period"]
    base_year = int(last_period) if _YEAR_RE.fullmatch(last_period) else None
    n = len(complete)
    points = []
    for step in range(1, 6):
        label = str(base_year + step) if base_year is not None else f"+{step} año{'s' if step > 1 else ''}"
        proj_cases = max(0.0, round(intercept_cases + slope_cases * (n - 1 + step), 1))
        proj_cap = max(0.0, round(intercept_cap + slope_cap * (n - 1 + step), 1))
        points.append({"period": label, "cases": proj_cases, "capacity": proj_cap})

    return {
        "available": True,
        "horizonYears": 5,
        "direction": direction,
        "annualDeltaCases": round(slope_cases, 1),
        "annualDeltaCapacity": round(slope_cap, 1),
        "points": points,
        "completePeriodsUsed": [item["period"] for item in complete],
        "excludedIncompletePeriods": excluded,
        "assumptions": "Estimación lineal de tendencia a partir del histórico disponible; no representa predicción definitiva ni tasa poblacional.",
        "proposals": proposals,
    }


def _build_mobile_route(summaries: list[dict]) -> list[dict]:
    return []


def _infer_kind(label: str) -> str:
    folded = normalize(label)
    if any(token in folded for token in _TEMPORAL_HINTS):
        return "temporal"
    if any(token in folded for token in _STATUS_HINTS):
        return "status"
    return "category"


def _build_dynamic_breakdowns(
    filtered: list[dict],
    dim_labels: dict[str, str],
    extra_dimensions: list[str],
) -> list[dict]:
    unspecified = load_constants()["filters"]["unspecified"]
    breakdowns: list[dict] = []

    def make_breakdown(key: str, label: str, filter_field: str | None, extractor) -> dict | None:
        buckets: dict[str, dict] = {}
        total_cases_sum = 0.0
        for row in filtered:
            raw_cat = extractor(row)
            cat = str(raw_cat).strip() if raw_cat else unspecified
            if not cat:
                cat = unspecified
            cases_val = float(row["cases"]) if row["cases"] is not None else 0.0
            bucket = buckets.setdefault(cat, {"name": cat, "cases": 0.0, "records": 0})
            bucket["cases"] += cases_val
            bucket["records"] += 1
            total_cases_sum += cases_val
        if not buckets:
            return None
        meaningful = [name for name in buckets if name != unspecified]
        if not meaningful:
            return None
        ordered = sorted(buckets.values(), key=lambda item: (item["cases"], item["records"]), reverse=True)
        denom = total_cases_sum if total_cases_sum > 0 else sum(item["records"] for item in ordered)
        items = [
            {
                "name": item["name"],
                "cases": round(item["cases"], 2),
                "records": item["records"],
                "sharePct": round(((item["cases"] if total_cases_sum > 0 else item["records"]) / max(denom, 1)) * 100, 1),
            }
            for item in ordered[:8]
        ]
        return {
            "key": key,
            "label": label,
            "kind": _infer_kind(label),
            "filterField": filter_field,
            "totalCategories": len(ordered),
            "items": items,
        }

    for field, key in (("violence", "violence"), ("service", "service")):
        bd = make_breakdown(key, dim_labels[key], field, lambda row, f=field: row.get(f))
        if bd is not None:
            breakdowns.append(bd)

    for col in extra_dimensions:
        bd = make_breakdown(
            f"extra:{col}",
            col,
            None,
            lambda row, c=col: (row.get("extra_dims") or {}).get(c, unspecified),
        )
        if bd is not None:
            breakdowns.append(bd)
        if len(breakdowns) >= 6:
            break

    return breakdowns


def _build_dynamic_metrics(filtered: list[dict], extra_metrics: list[str]) -> list[dict]:
    metrics: list[dict] = []
    for col in extra_metrics:
        values: list[float] = []
        zero_count = 0
        na_count = 0
        missing_count = 0
        for row in filtered:
            val = (row.get("extra_metrics") or {}).get(col)
            status = (row.get("extra_metric_statuses") or {}).get(col, "missing")
            if val is not None:
                fval = float(val)
                values.append(fval)
                if fval == 0.0:
                    zero_count += 1
            elif status == "na":
                na_count += 1
            else:
                missing_count += 1
        if not values and na_count == 0 and missing_count == 0:
            continue
        metrics.append(
            {
                "key": col,
                "label": col,
                "sum": round(sum(values), 2),
                "avg": round(sum(values) / len(values), 2) if values else None,
                "min": round(min(values), 2) if values else None,
                "max": round(max(values), 2) if values else None,
                "validCount": len(values),
                "zeroCount": zero_count,
                "naCount": na_count,
                "missingCount": missing_count,
            }
        )
    return metrics


def build_dashboard(records: list[dict], filters: dict[str, str], source: dict, metadata: dict | None = None) -> dict:
    labels = load_constants()["filters"]
    rules = load_constants()["classification"]
    periods = sorted({row["period"] for row in records}, key=natural_key)
    municipalities = sorted({row["zone"] for row in records}, key=natural_key)
    violence_types = sorted({row["violence"] for row in records}, key=natural_key)
    service_types = sorted({row["service"] for row in records}, key=natural_key)

    meta = metadata or {}
    default_labels = {
        "zone": "Municipio (hecho)",
        "period": "Periodo de corte",
        "violence": "Tipo de violencia",
        "service": "Tipo de servicio",
        "cases": "Casos registrados",
        "capacity": "Atenciones / capacidad",
    }
    dim_labels = {**default_labels, **(meta.get("columnLabels") or {})}
    extra_dimensions: list[str] = list(meta.get("extraDimensions") or [])
    extra_metrics: list[str] = list(meta.get("extraMetrics") or [])

    has_person_ids = any(bool(row.get("person_id")) for row in records)
    has_capacity_data = meta.get("hasCapacityData", True) and any(row["capacity"] is not None for row in records)
    has_residence_distinction = any(bool(row.get("residence_zone")) for row in records)
    has_event_date_distinction = any(bool(row.get("event_date")) for row in records)

    def selected(row: dict) -> bool:
        if filters["period"] != labels["allPeriods"] and row["period"] != filters["period"]:
            return False
        if filters["municipality"] != labels["allZones"] and row["zone"] != filters["municipality"]:
            return False
        if filters["violence"] != labels["allViolence"] and row["violence"] != filters["violence"]:
            return False
        if filters["service"] != labels["allServices"] and row["service"] != filters["service"]:
            return False
        return True

    filtered = [row for row in records if selected(row)]

    residence_cases_by_zone: dict[str, float] = {}
    for row in filtered:
        res_zone = row.get("residence_zone") or ""
        if res_zone and row["cases"] is not None:
            residence_cases_by_zone[res_zone] = residence_cases_by_zone.get(res_zone, 0.0) + float(row["cases"])

    grouped: dict[str, dict] = {}
    all_people: set[str] = set()
    missing_cases_count = 0
    na_cases_count = 0
    missing_capacity_count = 0
    na_capacity_count = 0

    for row in filtered:
        bucket = grouped.setdefault(
            row["zone"],
            {
                "name": row["zone"],
                "cases": 0.0,
                "capacity": 0.0,
                "count": 0,
                "people": set(),
                "cases_valid": 0,
                "cases_zero": 0,
                "cases_na": 0,
                "cases_missing": 0,
                "cap_valid": 0,
                "cap_zero": 0,
                "cap_na": 0,
                "cap_missing": 0,
            },
        )
        bucket["count"] += 1
        pid = row.get("person_id") or ""
        if pid:
            bucket["people"].add(pid)
            all_people.add(pid)

        cases_val = row["cases"]
        cases_status = row.get("cases_status") or ("value" if cases_val is not None else "missing")
        if cases_val is not None:
            bucket["cases"] += float(cases_val)
            bucket["cases_valid"] += 1
            if float(cases_val) == 0.0:
                bucket["cases_zero"] += 1
        elif cases_status == "na":
            bucket["cases_na"] += 1
            na_cases_count += 1
        else:
            bucket["cases_missing"] += 1
            missing_cases_count += 1

        cap_val = row["capacity"]
        cap_status = row.get("capacity_status") or ("value" if cap_val is not None else "missing")
        if cap_val is not None:
            bucket["capacity"] += float(cap_val)
            bucket["cap_valid"] += 1
            if float(cap_val) == 0.0:
                bucket["cap_zero"] += 1
        elif cap_status == "na":
            bucket["cap_na"] += 1
            if has_capacity_data:
                na_capacity_count += 1
        else:
            bucket["cap_missing"] += 1
            if has_capacity_data:
                missing_capacity_count += 1

    summaries = []
    for bucket in grouped.values():
        if not has_capacity_data:
            ratio = 0.0
        elif bucket["capacity"] > 0:
            ratio = bucket["cases"] / bucket["capacity"]
        elif bucket["cases"] > 0:
            ratio = rules["missingCapacityRatio"]
        else:
            ratio = 0.0
        avg_cases = round(bucket["cases"] / bucket["cases_valid"], 2) if bucket["cases_valid"] > 0 else None
        avg_cap = round(bucket["capacity"] / bucket["cap_valid"], 2) if bucket["cap_valid"] > 0 else None
        classification = (
            classify(ratio, bucket["cases"])
            if has_capacity_data
            else {"label": "Sin dato de cobertura", "action": "Consultar registros", "color": "stable"}
        )
        summaries.append(
            {
                "name": bucket["name"],
                "cases": bucket["cases"],
                "capacity": bucket["capacity"],
                "ratio": ratio,
                "count": bucket["count"],
                "uniquePeople": len(bucket["people"]),
                "residenceCases": residence_cases_by_zone.get(bucket["name"], 0.0),
                "casesValidCount": bucket["cases_valid"],
                "casesZeroCount": bucket["cases_zero"],
                "casesNaCount": bucket["cases_na"],
                "casesMissingCount": bucket["cases_missing"],
                "capacityValidCount": bucket["cap_valid"],
                "capacityZeroCount": bucket["cap_zero"],
                "capacityNaCount": bucket["cap_na"],
                "capacityMissingCount": bucket["cap_missing"],
                "avgCasesPerRecord": avg_cases,
                "avgCapacityPerRecord": avg_cap,
                "classification": classification,
            }
        )
    summaries.sort(key=lambda item: (item["ratio"], item["cases"]), reverse=True)

    trend_scope = [
        row
        for row in records
        if filters["municipality"] == labels["allZones"] or row["zone"] == filters["municipality"]
    ]
    all_trends = []
    for period in periods:
        subset = [row for row in trend_scope if row["period"] == period]
        if not subset:
            continue
        is_complete = all(row.get("period_complete", 1) == 1 for row in subset) and not is_period_incomplete(period)
        period_people = {row["person_id"] for row in subset if row.get("person_id")}
        all_trends.append(
            {
                "period": period,
                "cases": sum(float(row["cases"]) for row in subset if row["cases"] is not None),
                "capacity": sum(float(row["capacity"]) for row in subset if row["capacity"] is not None),
                "uniquePeople": len(period_people),
                "complete": is_complete,
            }
        )

    trends = all_trends[-5:]
    forecast = _build_forecast(all_trends, summaries)
    mobile_route = _build_mobile_route(summaries)
    dynamic_breakdowns = _build_dynamic_breakdowns(filtered, dim_labels, extra_dimensions)
    dynamic_metrics = _build_dynamic_metrics(filtered, extra_metrics)

    return {
        "periods": periods,
        "municipalities": municipalities,
        "violenceTypes": violence_types,
        "serviceTypes": service_types,
        "summaries": summaries,
        "trends": trends,
        "totalCases": sum(float(row["cases"]) for row in filtered if row["cases"] is not None),
        "totalCapacity": sum(float(row["capacity"]) for row in filtered if row["capacity"] is not None),
        "totalPeople": len(all_people),
        "totalRecords": len(filtered),
        "hasPersonIds": has_person_ids,
        "hasCapacityData": has_capacity_data,
        "hasResidenceDistinction": has_residence_distinction,
        "hasEventDateDistinction": has_event_date_distinction,
        "missingCasesCount": missing_cases_count,
        "naCasesCount": na_cases_count,
        "missingCapacityCount": missing_capacity_count,
        "naCapacityCount": na_capacity_count,
        "priorityCount": sum(1 for item in summaries if item["ratio"] >= rules["priorityRatio"]),
        "dimensionLabels": dim_labels,
        "dynamicBreakdowns": dynamic_breakdowns,
        "dynamicMetrics": dynamic_metrics,
        "mobileRoute": mobile_route,
        "forecast": forecast,
        "source": source,
    }
