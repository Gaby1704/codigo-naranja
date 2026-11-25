import json
import math
import re
import unicodedata
from typing import Any

from app.services.constants import load_constants

_NUMERIC_PATTERN = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
_NA_TOKENS = {"N/A", "NA", "N.A.", "N.A", "NO APLICA", "NO APLICABLE"}
_MISSING_TOKENS = {"", "NULL", "NONE", "NAN", "SIN DATO", "FALTANTE", "N/D", "ND", "-", "--"}
_INCOMPLETE_TOKENS = ("INCOMPLET", "PARCIAL", "EN CURSO", "PROVISIONAL", "ABIERTO", "(P)")


def js_round(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.upper()


def natural_key(value: str) -> tuple:
    parts = re.split(r"(\d+)", value.casefold())
    key: list[tuple[int, int | str]] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part))
    return tuple(key)


def parse_numeric_cell(value: Any) -> tuple[float | None, str]:
    """Classify a numeric cell without conflating 0, N/A, missing, and invalid text."""
    if value is None:
        return None, "missing"
    if isinstance(value, bool):
        return None, "invalid"
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number) or number < 0:
            return None, "invalid"
        return (0.0, "zero") if number == 0.0 else (number, "value")

    raw = str(value).strip()
    folded = normalize(raw)
    if folded in _MISSING_TOKENS:
        return None, "missing"
    if folded in _NA_TOKENS:
        return None, "na"

    compact = raw.replace(" ", "").replace(",", "")
    if _NUMERIC_PATTERN.fullmatch(compact) is None:
        return None, "invalid"
    try:
        number = float(compact)
    except ValueError:
        return None, "invalid"
    if not math.isfinite(number) or number < 0:
        return None, "invalid"
    return (0.0, "zero") if number == 0.0 else (number, "value")


def is_period_incomplete(period: str, status_value: Any = "") -> bool:
    period_norm = normalize(period)
    status_norm = normalize(status_value)
    if any(token in period_norm for token in _INCOMPLETE_TOKENS):
        return True
    if status_norm in {"0", "NO", "FALSE", "INCOMPLETO", "INCOMPLETA", "PARCIAL", "EN CURSO", "PROVISIONAL"}:
        return True
    return any(token in status_norm for token in _INCOMPLETE_TOKENS)


def classify(ratio: float, cases: float) -> dict[str, str]:
    rules = load_constants()["classification"]
    labels = rules["labels"]
    if ratio >= rules["priorityRatio"]:
        return dict(labels["priority"])
    if cases < rules["watchCasesBelow"] and ratio > rules["watchRatioAbove"]:
        return dict(labels["watch"])
    if ratio >= rules["elevatedRatio"]:
        return dict(labels["elevated"])
    return dict(labels["stable"])


def canonical_zone(value: Any) -> str:
    unspecified = load_constants()["filters"]["unspecified"]
    normalized = normalize(value)
    if not normalized:
        return unspecified
    for zone in load_constants()["zones"]:
        if normalize(zone["name"]) == normalized:
            return zone["name"]
    return normalized


def _is_mostly_numeric(header: str, rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    sample = [row.get(header) for row in rows[:80]]
    non_empty = [val for val in sample if normalize(val) not in _MISSING_TOKENS]
    if not non_empty:
        return False
    numeric_ok = 0
    explicit_number = 0
    for val in non_empty:
        _, status = parse_numeric_cell(val)
        if status in {"value", "zero"}:
            explicit_number += 1
            numeric_ok += 1
        elif status == "na":
            numeric_ok += 1
    return explicit_number >= 1 and (numeric_ok / len(non_empty)) >= 0.7


def suggest_mapping(headers: list[str], rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    patterns = load_constants()["columns"]["patterns"]
    normalized = [(header, normalize(header)) for header in headers]
    sample_rows = rows or []

    def guess(field: str, require_numeric: bool = False, exclude: set[str] | None = None) -> str:
        skip = exclude or set()
        for pattern in patterns[field]:
            for header, folded in normalized:
                if header in skip:
                    continue
                if pattern in folded:
                    if require_numeric and sample_rows and not _is_mostly_numeric(header, sample_rows):
                        continue
                    return header
        return ""

    zone = guess("zone")
    residence = guess("residenceZone", exclude={zone})
    period = guess("period", exclude={zone, residence})
    event_date = guess("eventDate", exclude={zone, residence, period})
    violence = guess("violence", exclude={zone, residence, period, event_date})
    service = guess("service", exclude={zone, residence, period, event_date, violence})
    cases = guess("cases", require_numeric=True, exclude={zone, residence, period, event_date, violence, service})
    capacity = guess("capacity", require_numeric=True, exclude={zone, residence, period, event_date, violence, service, cases})
    person = guess("person")
    period_status = guess("periodStatus")

    if sample_rows:
        used = {zone, residence, period, event_date, violence, service, cases, capacity, person, period_status} - {""}
        if not zone:
            for header in headers:
                if header not in used and not _is_mostly_numeric(header, sample_rows):
                    zone = header
                    used.add(header)
                    break
        if not violence:
            for header in headers:
                if header not in used and not _is_mostly_numeric(header, sample_rows):
                    violence = header
                    used.add(header)
                    break
        if not service:
            for header in headers:
                if header not in used and not _is_mostly_numeric(header, sample_rows):
                    service = header
                    used.add(header)
                    break

    return {
        "zone": zone,
        "residenceZone": residence,
        "period": period,
        "eventDate": event_date,
        "violence": violence,
        "service": service,
        "cases": cases,
        "capacity": capacity,
        "person": person,
        "periodStatus": period_status,
    }


def detect_extra_schema(rows: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[str], list[str]]:
    """Detect extra categorical/temporal/status dimensions and numeric metrics from unmapped Excel columns."""
    if not rows:
        return [], []
    headers = list(rows[0].keys())
    mapped_cols = {col for col in mapping.values() if col}
    extra_dims: list[str] = []
    extra_metrics: list[str] = []

    for header in headers:
        if header in mapped_cols:
            continue
        raw_vals = [row.get(header) for row in rows]
        non_empty = [val for val in raw_vals if normalize(val) not in _MISSING_TOKENS]
        if not non_empty:
            continue

        numeric_ok = 0
        explicit_num = 0
        for val in non_empty:
            _, status = parse_numeric_cell(val)
            if status in {"value", "zero"}:
                numeric_ok += 1
                explicit_num += 1
            elif status == "na":
                numeric_ok += 1
        if explicit_num >= 1 and (numeric_ok / len(non_empty)) >= 0.75:
            extra_metrics.append(header)
            continue

        distinct = {normalize(val) for val in non_empty if normalize(val) not in _NA_TOKENS}
        if 1 <= len(distinct) <= 35 and (len(non_empty) <= 12 or len(distinct) / len(non_empty) <= 0.65):
            extra_dims.append(header)

    return extra_dims[:6], extra_metrics[:6]


def validate_processed_dataset(
    rows: list[dict[str, Any]],
    mapping: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Validate pre-processed rows flexibly without requiring fixed column names."""
    unspecified = load_constants()["filters"]["unspecified"]
    text_cols = {
        mapping[key]
        for key in ("zone", "period", "violence", "service")
        if mapping.get(key)
    }
    if mapping.get("cases") and mapping["cases"] in text_cols:
        raise ValueError("El mapeo no es coherente: la columna de casos debe ser numérica o quedar en 1 registro = 1 caso.")
    if mapping.get("capacity") and mapping["capacity"] in text_cols:
        raise ValueError("El mapeo no es coherente: la columna de atenciones/capacidad debe ser numérica o quedar sin asignar.")

    extra_dims, extra_metrics = detect_extra_schema(rows, mapping)
    has_cases_col = bool(mapping.get("cases"))
    has_capacity_col = bool(mapping.get("capacity"))

    processed = len(rows)
    removed = 0
    zero_values = 0
    na_values = 0
    missing_values = 0
    seen_rows: set[str] = set()
    person_counts: dict[str, int] = {}
    has_residence = False
    has_event_date = False

    cleaned: list[dict[str, Any]] = []
    for raw in rows:
        if all(str(value or "").strip() == "" for value in raw.values()):
            removed += 1
            continue

        fingerprint = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
        if fingerprint in seen_rows:
            removed += 1
            continue
        seen_rows.add(fingerprint)

        zone_col = mapping.get("zone") or ""
        period_col = mapping.get("period") or ""
        zone_raw = str(raw.get(zone_col) or "").strip() if zone_col else ""
        period_raw = str(raw.get(period_col) or "").strip() if period_col else ""
        if (zone_col or period_col) and not zone_raw and not period_raw and not extra_dims:
            removed += 1
            continue

        if has_cases_col:
            cases_val, cases_status = parse_numeric_cell(raw.get(mapping["cases"]))
            if cases_status == "invalid":
                removed += 1
                continue
        else:
            cases_val, cases_status = 1.0, "value"

        if has_capacity_col:
            capacity_val, capacity_status = parse_numeric_cell(raw.get(mapping["capacity"]))
            if capacity_status == "invalid":
                removed += 1
                continue
        else:
            capacity_val, capacity_status = None, "na"

        if has_cases_col:
            if cases_status == "zero":
                zero_values += 1
            elif cases_status == "na":
                na_values += 1
            elif cases_status == "missing":
                missing_values += 1

        if has_capacity_col:
            if capacity_status == "zero":
                zero_values += 1
            elif capacity_status == "na":
                na_values += 1
            elif capacity_status == "missing":
                missing_values += 1

        person_col = mapping.get("person") or ""
        person_id = normalize(raw.get(person_col)) if person_col else ""
        if person_id and person_id not in _NA_TOKENS and person_id not in _MISSING_TOKENS:
            person_counts[person_id] = person_counts.get(person_id, 0) + 1
        else:
            person_id = ""

        res_col = mapping.get("residenceZone") or ""
        res_raw = str(raw.get(res_col) or "").strip() if res_col else ""
        residence_zone = ""
        if res_raw and normalize(res_raw) not in (_NA_TOKENS | _MISSING_TOKENS):
            residence_zone = canonical_zone(res_raw)
            has_residence = True

        event_col = mapping.get("eventDate") or ""
        event_raw = str(raw.get(event_col) or "").strip() if event_col else ""
        event_date = ""
        if event_raw and normalize(event_raw) not in (_NA_TOKENS | _MISSING_TOKENS):
            event_date = event_raw
            has_event_date = True

        status_col = mapping.get("periodStatus") or ""
        period_status = raw.get(status_col, "") if status_col else ""

        zone = canonical_zone(zone_raw) if zone_col else unspecified
        period = period_raw or unspecified
        violence_col = mapping.get("violence") or ""
        service_col = mapping.get("service") or ""
        violence = normalize(raw.get(violence_col)) or unspecified if violence_col else unspecified
        service = normalize(raw.get(service_col)) or unspecified if service_col else unspecified
        complete = not is_period_incomplete(period, period_status)

        row_extra_dims: dict[str, str] = {}
        for col in extra_dims:
            val_text = str(raw.get(col) or "").strip()
            norm_val = normalize(val_text)
            if norm_val in _MISSING_TOKENS:
                row_extra_dims[col] = unspecified
            elif norm_val in _NA_TOKENS:
                row_extra_dims[col] = "N/A"
            else:
                row_extra_dims[col] = val_text

        row_extra_metrics: dict[str, float | None] = {}
        row_extra_statuses: dict[str, str] = {}
        for col in extra_metrics:
            val_num, val_status = parse_numeric_cell(raw.get(col))
            if val_status == "invalid":
                val_num, val_status = None, "missing"
            row_extra_metrics[col] = val_num
            row_extra_statuses[col] = val_status

        cleaned.append(
            {
                "zone": zone,
                "residence_zone": residence_zone,
                "period": period,
                "event_date": event_date,
                "period_complete": 1 if complete else 0,
                "violence": violence,
                "service": service,
                "cases": cases_val,
                "capacity": capacity_val,
                "cases_status": cases_status,
                "capacity_status": capacity_status,
                "person_id": person_id,
                "extra_dims": row_extra_dims,
                "extra_metrics": row_extra_metrics,
                "extra_metric_statuses": row_extra_statuses,
            }
        )

    audit = {
        "processed": processed,
        "valid": len(cleaned),
        "removed": removed,
        "uniquePeople": len(person_counts),
        "multiCasePeople": sum(1 for count in person_counts.values() if count > 1),
        "zeroValues": zero_values,
        "notApplicable": na_values,
        "missingValues": missing_values,
        "hasResidenceDistinction": has_residence,
        "hasEventDateDistinction": has_event_date,
    }
    metadata = {
        "hasCapacityData": has_capacity_col,
        "columnLabels": {
            "zone": mapping.get("zone") or "Municipio / zona",
            "period": mapping.get("period") or "Periodo de corte",
            "violence": mapping.get("violence") or "Tipo de violencia",
            "service": mapping.get("service") or "Tipo de servicio",
            "cases": mapping.get("cases") or "Casos registrados",
            "capacity": mapping.get("capacity") or "Servicios / atenciones",
        },
        "extraDimensions": extra_dims,
        "extraMetrics": extra_metrics,
    }
    return cleaned, audit, metadata


def validate_processed_rows(rows: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cleaned, audit, _metadata = validate_processed_dataset(rows, mapping)
    return cleaned, audit


def demo_records() -> list[dict[str, Any]]:
    demo = load_constants()["demo"]
    zones = load_constants()["zones"]
    records: list[dict[str, Any]] = []
    for index, zone in enumerate(zones):
        for offset, year in enumerate(demo["years"]):
            year_key = str(year)
            cases_raw = (demo["casesBase"] + ((index * demo["casesSeedA"] + offset * demo["casesSeedB"]) % demo["casesMod"])) * demo["casesFactors"][year_key]
            capacity_raw = (demo["capacityBase"] + ((index * demo["capacitySeedA"] + offset * demo["capacitySeedB"]) % demo["capacityMod"])) * demo["capacityFactors"][year_key]
            records.append(
                {
                    "zone": zone["name"],
                    "period": year_key,
                    "violence": demo["violence"][(index + offset) % len(demo["violence"])],
                    "service": demo["services"][(index + offset) % len(demo["services"])],
                    "cases": max(demo["casesMin"], js_round(cases_raw)),
                    "capacity": max(demo["capacityMin"], js_round(capacity_raw)),
                }
            )
    return records
