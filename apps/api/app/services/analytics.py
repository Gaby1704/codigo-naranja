from collections import Counter
import re

from app.services.constants import load_constants
from app.services.rules import _is_table_only_col, _is_technical_helper_col, classify, is_period_incomplete, natural_key, normalize

_YEAR_RE = re.compile(r"^\d{4}$")
_ANY_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_YMD_RE = re.compile(r"^((?:19|20)\d{2})[-/](\d{1,2})(?:[-/](\d{1,2}))?(?:\b|T|\s)")
_DMY_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/]((?:19|20)\d{2})(?:\b|\s)")
_TEMPORAL_HINTS = ("MES", "FECHA", "TRIMESTRE", "PERIODO", "ANIO", "ANO", "SEMANA", "DIA")


def _extract_date_parts(period_val: str, event_date_val: str = "") -> tuple[str, str, str]:
    for raw in (period_val, event_date_val):
        text = str(raw or "").strip()
        if not text:
            continue
        m_ymd = _YMD_RE.match(text)
        if m_ymd:
            yr, mo, dy = m_ymd.group(1), m_ymd.group(2).zfill(2), (m_ymd.group(3) or "").zfill(2) if m_ymd.group(3) else ""
            if 1 <= int(mo) <= 12 and (not dy or 1 <= int(dy) <= 31):
                return yr, mo, dy
        m_dmy = _DMY_RE.match(text)
        if m_dmy:
            dy, mo, yr = m_dmy.group(1).zfill(2), m_dmy.group(2).zfill(2), m_dmy.group(3)
            if 1 <= int(mo) <= 12 and 1 <= int(dy) <= 31:
                return yr, mo, dy
        m_yr = _ANY_YEAR_RE.search(text)
        if m_yr:
            return m_yr.group(1), "", ""
    return "", "", ""
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
    if all_trends or summaries:
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


def _fmt_bound(val: float) -> str:
    return str(int(round(val))) if abs(val - round(val)) < 1e-6 else str(round(val, 1))


def _build_numeric_distribution_breakdown(filtered: list[dict], col: str) -> dict | None:
    samples: list[tuple[float, float]] = []
    for row in filtered:
        raw_val = (row.get("extra_metrics") or {}).get(col)
        if raw_val is None:
            continue
        cases_val = float(row["cases"]) if row["cases"] is not None else 0.0
        samples.append((float(raw_val), cases_val))
    if not samples:
        return None
    distinct = sorted({val for val, _ in samples})
    if len(distinct) < 2:
        return None

    ordered_buckets: list[dict] = []
    if len(distinct) <= 8:
        by_val: dict[float, dict] = {}
        for val, cases_val in samples:
            b = by_val.setdefault(val, {"name": _fmt_bound(val), "cases": 0.0, "records": 0})
            b["cases"] += cases_val
            b["records"] += 1
        ordered_buckets = [by_val[val] for val in distinct]
    elif "EDAD" in normalize(col).replace("_", " ").split():
        age_bands = [
            ("0–17 años", lambda v: v < 18),
            ("18–29 años", lambda v: 18 <= v < 30),
            ("30–44 años", lambda v: 30 <= v < 45),
            ("45–59 años", lambda v: 45 <= v < 60),
            ("60+ años", lambda v: v >= 60),
        ]
        for label, pred in age_bands:
            matched = [(v, c) for v, c in samples if pred(v)]
            if matched:
                ordered_buckets.append(
                    {"name": label, "cases": sum(c for _, c in matched), "records": len(matched)}
                )
    else:
        min_v, max_v = distinct[0], distinct[-1]
        bin_count = 5
        step = (max_v - min_v) / bin_count
        if step <= 0:
            return None
        for idx in range(bin_count):
            lo = min_v + idx * step
            hi = max_v if idx == bin_count - 1 else min_v + (idx + 1) * step
            matched = [
                (v, c)
                for v, c in samples
                if (lo <= v <= hi if idx == bin_count - 1 else lo <= v < hi)
            ]
            if matched:
                ordered_buckets.append(
                    {
                        "name": f"{_fmt_bound(lo)} – {_fmt_bound(hi)}",
                        "cases": sum(c for _, c in matched),
                        "records": len(matched),
                    }
                )

    if len(ordered_buckets) < 2:
        return None
    total_cases_sum = sum(item["cases"] for item in ordered_buckets)
    total_records_sum = sum(item["records"] for item in ordered_buckets)
    denom = total_cases_sum if total_cases_sum > 0 else total_records_sum
    return {
        "key": f"metric:{col}",
        "label": col,
        "kind": "numeric",
        "filterField": None,
        "totalCategories": len(ordered_buckets),
        "items": [
            {
                "name": item["name"],
                "cases": round(item["cases"], 2),
                "records": item["records"],
                "sharePct": round(((item["cases"] if total_cases_sum > 0 else item["records"]) / max(denom, 1)) * 100, 1),
            }
            for item in ordered_buckets
        ],
    }


def _build_dynamic_breakdowns(
    filtered: list[dict],
    dim_labels: dict[str, str],
    extra_dimensions: list[str],
    extra_metrics: list[str],
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
        meaningful = [name for name in buckets if name != unspecified and normalize(name) not in {"FALSE", "FALSO"}]
        if not meaningful:
            return None
        ordered = sorted(
            (item for item in buckets.values() if normalize(item["name"]) not in {"FALSE", "FALSO"}),
            key=lambda item: (item["cases"], item["records"]),
            reverse=True,
        )
        if not ordered:
            return None
        denom = total_cases_sum if total_cases_sum > 0 else sum(item["records"] for item in buckets.values())
        items = [
            {
                "name": item["name"],
                "cases": round(item["cases"], 2),
                "records": item["records"],
                "sharePct": round(((item["cases"] if total_cases_sum > 0 else item["records"]) / max(denom, 1)) * 100, 1),
            }
            for item in ordered
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
        if len(breakdowns) >= 25:
            return breakdowns

    norm_dims = {normalize(col).replace(" ", "_") for col in extra_dimensions}
    for col in extra_metrics:
        norm_col = normalize(col).replace(" ", "_")
        if f"{norm_col}_RANGO" in norm_dims:
            continue
        bd = _build_numeric_distribution_breakdown(filtered, col)
        if bd is not None:
            breakdowns.append(bd)
        if len(breakdowns) >= 25:
            break

    return breakdowns


def _compute_mode(values: list[float]) -> tuple[float | None, int]:
    """Return the most frequent numeric value (mode) and its repetition count."""
    if not values:
        return None, 0
    counts = Counter(round(val, 4) for val in values)
    top_val, top_count = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(values) > 1 and top_count == 1:
        return None, 0
    return round(float(top_val), 2), int(top_count)


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
        mode_val, mode_count = _compute_mode(values)
        metrics.append(
            {
                "key": col,
                "label": col,
                "sum": round(sum(values), 2),
                "avg": round(sum(values) / len(values), 2) if values else None,
                "mode": mode_val,
                "modeCount": mode_count,
                "min": round(min(values), 2) if values else None,
                "max": round(max(values), 2) if values else None,
                "validCount": len(values),
                "zeroCount": zero_count,
                "naCount": na_count,
                "missingCount": missing_count,
            }
        )
    return metrics


def _filter_pairs(
    records: list[dict],
    filters: dict[str, str],
    labels: dict[str, str],
) -> tuple[list[tuple[str, str, str]], list[tuple[dict, tuple[str, str, str]]]]:
    row_parts = [_extract_date_parts(row.get("period", ""), row.get("event_date", "")) for row in records]
    filter_year = filters.get("year") or "Todos"
    filter_month = filters.get("month") or "Todos"
    filter_day = filters.get("day") or "Todos"
    if filter_month not in {"Todos", ""} and filter_month.isdigit():
        filter_month = filter_month.zfill(2)
    if filter_day not in {"Todos", ""} and filter_day.isdigit():
        filter_day = filter_day.zfill(2)

    def selected(row: dict, parts: tuple[str, str, str]) -> bool:
        yr, mo, dy = parts
        if filters["period"] != labels["allPeriods"]:
            if row["period"] != filters["period"] and yr != filters["period"]:
                return False
        if filter_year not in {"Todos", ""} and yr != filter_year:
            return False
        if filter_month not in {"Todos", ""} and mo != filter_month:
            return False
        if filter_day not in {"Todos", ""} and dy != filter_day:
            return False
        if filters["municipality"] != labels["allZones"] and row["zone"] != filters["municipality"]:
            return False
        if filters["violence"] != labels["allViolence"] and row["violence"] != filters["violence"]:
            return False
        if filters["service"] != labels["allServices"] and row["service"] != filters["service"]:
            return False
        return True

    return row_parts, [(row, parts) for row, parts in zip(records, row_parts) if selected(row, parts)]


def _serialize_record(row: dict) -> dict:
    return {
        "zone": row["zone"],
        "period": row["period"],
        "violence": row["violence"],
        "service": row["service"],
        "personId": row.get("person_id") or "",
        "cases": row["cases"],
        "casesStatus": row.get("cases_status") or ("value" if row["cases"] is not None else "missing"),
        "capacity": row["capacity"],
        "capacityStatus": row.get("capacity_status") or ("value" if row["capacity"] is not None else "na"),
        "extraDims": dict(row.get("extra_dims") or {}),
        "extraMetrics": dict(row.get("extra_metrics") or {}),
        "extraMetricStatuses": dict(row.get("extra_metric_statuses") or {}),
    }


def _resolve_extra_schema(records: list[dict], meta: dict) -> tuple[list[str], list[str], list[str]]:
    extra_dimensions: list[str] = list(meta.get("extraDimensions") or [])
    extra_metrics: list[str] = list(meta.get("extraMetrics") or [])
    table_dimensions: list[str] = list(meta.get("tableDimensions") or [])
    if not extra_dimensions and records:
        seen_dims: list[str] = []
        for row in records[:50]:
            for key in (row.get("extra_dims") or {}).keys():
                if key not in seen_dims:
                    seen_dims.append(key)
        extra_dimensions = seen_dims
    if not extra_metrics and records:
        seen_metrics: list[str] = []
        for row in records[:50]:
            for key in (row.get("extra_metrics") or {}).keys():
                if key not in seen_metrics:
                    seen_metrics.append(key)
        extra_metrics = seen_metrics
    for col in extra_dimensions:
        if _is_table_only_col(col) and col not in table_dimensions:
            table_dimensions.append(col)
    for col in extra_metrics:
        if _is_table_only_col(col) and col not in table_dimensions:
            table_dimensions.append(col)
    table_dimensions = [col for col in table_dimensions if not _is_technical_helper_col(col, {})]
    extra_dimensions = [
        col for col in extra_dimensions if not _is_technical_helper_col(col, {}) and not _is_table_only_col(col)
    ]
    extra_metrics = [
        col for col in extra_metrics if not _is_technical_helper_col(col, {}) and not _is_table_only_col(col)
    ]
    return extra_dimensions, extra_metrics, table_dimensions


def query_records(
    records: list[dict],
    filters: dict[str, str],
    metadata: dict | None = None,
    q: str = "",
    offset: int = 0,
    limit: int | None = 500,
) -> dict:
    labels = load_constants()["filters"]
    _parts, pairs = _filter_pairs(records, filters, labels)
    filtered = [row for row, _ in pairs]
    needle = normalize(q)
    if needle:
        matched: list[dict] = []
        for row in filtered:
            haystack = [
                row["zone"],
                row["period"],
                row["violence"],
                row["service"],
                row.get("person_id") or "",
                *(str(v) for v in (row.get("extra_dims") or {}).values()),
                *(str(v) for v in (row.get("extra_metrics") or {}).values() if v is not None),
            ]
            if any(needle in normalize(item) for item in haystack):
                matched.append(row)
        filtered = matched

    total = len(filtered)
    sliced = filtered[offset:] if limit is None else filtered[offset : offset + limit]
    meta = metadata or {}
    extra_dims, extra_metrics, table_dims = _resolve_extra_schema(records, meta)
    return {
        "total": total,
        "offset": offset,
        "limit": limit if limit is not None else total,
        "rows": [_serialize_record(row) for row in sliced],
        "extraDimensions": extra_dims,
        "extraMetrics": extra_metrics,
        "tableDimensions": table_dims,
        "hasPersonIds": any(bool(row.get("person_id")) for row in records),
        "hasCapacityData": meta.get("hasCapacityData", True) and any(row["capacity"] is not None for row in records),
    }


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
    extra_dimensions, extra_metrics, table_dimensions = _resolve_extra_schema(records, meta)

    has_person_ids = any(bool(row.get("person_id")) for row in records)
    has_capacity_data = meta.get("hasCapacityData", True) and any(row["capacity"] is not None for row in records)
    has_residence_distinction = any(bool(row.get("residence_zone")) for row in records)
    has_event_date_distinction = any(bool(row.get("event_date")) for row in records)

    filter_year = filters.get("year") or "Todos"
    row_parts, filtered_pairs = _filter_pairs(records, filters, labels)
    years = sorted({yr for yr, _mo, _dy in row_parts if yr}, key=natural_key)
    months = sorted({mo for _yr, mo, _dy in row_parts if mo}, key=natural_key)
    days = sorted({dy for _yr, _mo, dy in row_parts if dy}, key=natural_key)
    filtered = [row for row, _ in filtered_pairs]

    zone_year_cases: dict[str, dict[str, float]] = {}
    for row, parts in zip(records, row_parts):
        if filters["violence"] != labels["allViolence"] and row["violence"] != filters["violence"]:
            continue
        if filters["service"] != labels["allServices"] and row["service"] != filters["service"]:
            continue
        year_key = parts[0] or str(row.get("period") or "").strip() or labels["unspecified"]
        ymap = zone_year_cases.setdefault(row["zone"], {})
        if row["cases"] is not None:
            ymap[year_key] = ymap.get(year_key, 0.0) + float(row["cases"])
        else:
            ymap.setdefault(year_key, ymap.get(year_key, 0.0))

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

    for row, parts in filtered_pairs:
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
                "undated_cases": 0.0,
                "violence": {},
                "extra_metrics_vals": {},
                "extra_dim_counts": {},
                "table_unique_vals": {},
            },
        )
        year_part = parts[0] or (
            str(row.get("period") or "").strip()
            if str(row.get("period") or "").strip() not in {"", labels["unspecified"]}
            else ""
        )
        if not year_part and row["cases"] is not None:
            bucket["undated_cases"] += float(row["cases"])
        for col in extra_metrics:
            val = (row.get("extra_metrics") or {}).get(col)
            if val is not None:
                bucket["extra_metrics_vals"].setdefault(col, []).append(float(val))
        for col in extra_dimensions:
            val_text = str((row.get("extra_dims") or {}).get(col) or "").strip()
            if val_text and val_text != labels["unspecified"] and val_text != "N/A":
                col_counts = bucket["extra_dim_counts"].setdefault(col, {})
                col_counts[val_text] = col_counts.get(val_text, 0) + 1
        for col in table_dimensions:
            val_text = str((row.get("extra_dims") or {}).get(col) or "").strip()
            if val_text and val_text != labels["unspecified"] and val_text != "N/A":
                bucket["table_unique_vals"].setdefault(col, set()).add(val_text)
        bucket["count"] += 1
        vtype = str(row.get("violence") or labels["unspecified"]).strip() or labels["unspecified"]
        vbucket = bucket["violence"].setdefault(vtype, {"name": vtype, "cases": 0.0, "records": 0})
        vbucket["records"] += 1
        if row["cases"] is not None:
            vbucket["cases"] += float(row["cases"])
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
        v_sorted = sorted(
            bucket["violence"].values(),
            key=lambda item: (item["cases"], item["records"]),
            reverse=True,
        )
        if len(v_sorted) > 7:
            head = v_sorted[:6]
            tail = v_sorted[6:]
            v_breakdown = [
                *head,
                {
                    "name": "OTROS",
                    "cases": sum(item["cases"] for item in tail),
                    "records": sum(item["records"] for item in tail),
                },
            ]
        else:
            v_breakdown = v_sorted

        year_map = zone_year_cases.get(bucket["name"], {})
        sorted_years = [yr for yr in sorted(year_map.keys(), key=natural_key) if yr != labels["unspecified"]][-6:]
        yearly_trend: list[dict] = []
        prev_cases: float | None = None
        for yr in sorted_years:
            yr_cases = round(year_map[yr], 2)
            if prev_cases is None:
                delta = None
                delta_pct = None
            else:
                delta = round(yr_cases - prev_cases, 2)
                delta_pct = round((delta / prev_cases) * 100, 1) if prev_cases > 0 else None
            yearly_trend.append({"year": yr, "cases": yr_cases, "delta": delta, "deltaPct": delta_pct})
            prev_cases = yr_cases

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
                "violenceBreakdown": v_breakdown,
                "yearlyTrend": yearly_trend,
                "undatedCases": round(bucket["undated_cases"], 2),
                "extraMetrics": {
                    col: {
                        "avg": round(sum(vals) / len(vals), 2) if vals else None,
                        "mode": mode_val,
                        "modeCount": mode_count,
                        "min": round(min(vals), 2) if vals else None,
                        "max": round(max(vals), 2) if vals else None,
                        "validCount": len(vals),
                    }
                    for col in extra_metrics
                    for vals in [bucket["extra_metrics_vals"].get(col, [])]
                    if vals
                    for mode_val, mode_count in [_compute_mode(vals)]
                },
                "extraDimensions": {
                    col: max(counts.items(), key=lambda kv: kv[1])[0]
                    for col in extra_dimensions
                    for counts in [bucket["extra_dim_counts"].get(col, {})]
                    if counts
                },
                "tableCounts": {
                    col: len(bucket["table_unique_vals"].get(col, set()))
                    for col in table_dimensions
                },
                "classification": classification,
            }
        )
    summaries.sort(key=lambda item: (item["ratio"], item["cases"]), reverse=True)

    use_yearly_buckets = (len(periods) > 6 or any(mo for _yr, mo, _dy in row_parts)) and len(years) >= 2
    trend_buckets: dict[str, list[dict]] = {}
    unspecified_period_cases = 0.0
    for row, parts in zip(records, row_parts):
        if filters["municipality"] != labels["allZones"] and row["zone"] != filters["municipality"]:
            continue
        key = (parts[0] or row["period"]) if use_yearly_buckets else row["period"]
        if not key or key == labels["unspecified"]:
            if row["cases"] is not None:
                unspecified_period_cases += float(row["cases"])
            continue
        trend_buckets.setdefault(key, []).append(row)

    all_trends = []
    for period in sorted(trend_buckets.keys(), key=natural_key):
        subset = trend_buckets[period]
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
    dynamic_breakdowns = _build_dynamic_breakdowns(filtered, dim_labels, extra_dimensions, extra_metrics)
    dynamic_metrics = _build_dynamic_metrics(filtered, extra_metrics)
    record_rows = [_serialize_record(row) for row in filtered[:250]]

    return {
        "periods": periods,
        "years": years,
        "months": months,
        "days": days,
        "appliedYear": filter_year,
        "municipalities": municipalities,
        "violenceTypes": violence_types,
        "serviceTypes": service_types,
        "summaries": summaries,
        "trends": trends,
        "totalCases": sum(float(row["cases"]) for row in filtered if row["cases"] is not None),
        "totalCapacity": sum(float(row["capacity"]) for row in filtered if row["capacity"] is not None),
        "totalPeople": len(all_people),
        "totalRecords": len(filtered),
        "hasData": len(records) > 0,
        "hasPersonIds": has_person_ids,
        "hasCapacityData": has_capacity_data,
        "hasResidenceDistinction": has_residence_distinction,
        "hasEventDateDistinction": has_event_date_distinction,
        "missingCasesCount": missing_cases_count,
        "naCasesCount": na_cases_count,
        "missingCapacityCount": missing_capacity_count,
        "naCapacityCount": na_capacity_count,
        "undatedCasesCount": round(unspecified_period_cases, 2),
        "priorityCount": sum(1 for item in summaries if item["ratio"] >= rules["priorityRatio"]),
        "dimensionLabels": dim_labels,
        "extraDimensions": extra_dimensions,
        "tableDimensions": table_dimensions,
        "dynamicBreakdowns": dynamic_breakdowns,
        "dynamicMetrics": dynamic_metrics,
        "recordRows": record_rows,
        "mobileRoute": mobile_route,
        "forecast": forecast,
        "source": source,
    }
