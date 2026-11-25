import re

from app.services.constants import load_constants
from app.services.rules import classify, is_period_incomplete, natural_key

_YEAR_RE = re.compile(r"^\d{4}$")


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
        proposals.append(
            f"Desplegar unidad móvil prioritaria y ampliar cobertura presencial en {', '.join(priority_zones)}."
        )
    else:
        proposals.append("Mantener cobertura móvil preventiva y monitorear capacidad instalada por municipio.")

    if watch_zones:
        proposals.append(
            f"Activar jornadas de detección y muestreo territorial en {', '.join(watch_zones)} ante posible subregistro."
        )
    else:
        proposals.append("Reforzar canales de detección temprana y vinculación institucional en zonas periféricas.")

    proposals.append(
        "Estandarizar seguimiento interinstitucional por expediente único para reducir reincidencia y brechas de atención."
    )

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
            "assumptions": (
                "Se requieren al menos 2 periodos de corte completos para proyectar un escenario exploratorio a 5 años. "
                "Las proyecciones nunca equivalen a incidencia poblacional."
            ),
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
        "assumptions": (
            "Escenario exploratorio lineal calculado únicamente sobre periodos completos disponibles "
            "(excluye cortes incompletos). Supone continuidad de la capacidad de registro institucional; "
            "no constituye certeza ni estimación poblacional."
        ),
        "proposals": proposals,
    }


def _build_mobile_route(summaries: list[dict]) -> list[dict]:
    priority = sorted(
        [item for item in summaries if item["classification"]["color"] == "priority"],
        key=lambda item: (item["ratio"], item["cases"]),
        reverse=True,
    )
    watch = sorted(
        [item for item in summaries if item["classification"]["color"] == "watch"],
        key=lambda item: (item["cases"], -item["ratio"]),
    )
    elevated = sorted(
        [item for item in summaries if item["classification"]["color"] == "elevated"],
        key=lambda item: (item["ratio"], item["cases"]),
        reverse=True,
    )

    stops: list[dict] = []
    for item in priority:
        stops.append(
            {
                "zone": item["name"],
                "rank": len(stops) + 1,
                "intervention": "Unidad móvil prioritaria",
                "reason": f"Brecha {round(item['ratio'] * 100)}% ({int(item['cases'])} casos / {int(item['capacity'])} atenciones)",
                "cases": item["cases"],
                "capacity": item["capacity"],
                "ratio": item["ratio"],
                "color": "priority",
            }
        )
    for item in watch:
        stops.append(
            {
                "zone": item["name"],
                "rank": len(stops) + 1,
                "intervention": "Jornada de detección y muestreo",
                "reason": f"Posible subregistro ({int(item['cases'])} casos · baja cobertura relativa)",
                "cases": item["cases"],
                "capacity": item["capacity"],
                "ratio": item["ratio"],
                "color": "watch",
            }
        )
    for item in elevated:
        stops.append(
            {
                "zone": item["name"],
                "rank": len(stops) + 1,
                "intervention": "Jornada itinerante y turnos",
                "reason": f"Demanda cercana al límite ({round(item['ratio'] * 100)}%)",
                "cases": item["cases"],
                "capacity": item["capacity"],
                "ratio": item["ratio"],
                "color": "elevated",
            }
        )
    return stops[:10]


def build_dashboard(records: list[dict], filters: dict[str, str], source: dict) -> dict:
    labels = load_constants()["filters"]
    rules = load_constants()["classification"]
    periods = sorted({row["period"] for row in records}, key=natural_key)
    municipalities = sorted({row["zone"] for row in records}, key=natural_key)
    violence_types = sorted({row["violence"] for row in records}, key=natural_key)
    service_types = sorted({row["service"] for row in records}, key=natural_key)

    has_person_ids = any(bool(row.get("person_id")) for row in records)
    has_residence_distinction = any(
        bool(row.get("residence_zone")) and row.get("residence_zone") != row["zone"] for row in records
    ) or any(bool(row.get("residence_zone")) for row in records)
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
            na_capacity_count += 1
        else:
            bucket["cap_missing"] += 1
            missing_capacity_count += 1

    summaries = []
    for bucket in grouped.values():
        if bucket["capacity"] > 0:
            ratio = bucket["cases"] / bucket["capacity"]
        elif bucket["cases"] > 0:
            ratio = rules["missingCapacityRatio"]
        else:
            ratio = 0.0
        avg_cases = round(bucket["cases"] / bucket["cases_valid"], 2) if bucket["cases_valid"] > 0 else None
        avg_cap = round(bucket["capacity"] / bucket["cap_valid"], 2) if bucket["cap_valid"] > 0 else None
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
                "classification": classify(ratio, bucket["cases"]),
            }
        )
    summaries.sort(key=lambda item: item["ratio"], reverse=True)

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
        "hasResidenceDistinction": has_residence_distinction,
        "hasEventDateDistinction": has_event_date_distinction,
        "missingCasesCount": missing_cases_count,
        "naCasesCount": na_cases_count,
        "missingCapacityCount": missing_capacity_count,
        "naCapacityCount": na_capacity_count,
        "priorityCount": sum(1 for item in summaries if item["ratio"] >= rules["priorityRatio"]),
        "mobileRoute": mobile_route,
        "forecast": forecast,
        "source": source,
    }
