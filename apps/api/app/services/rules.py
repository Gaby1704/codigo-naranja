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


def suggest_mapping(headers: list[str]) -> dict[str, str]:
    patterns = load_constants()["columns"]["patterns"]
    normalized = [(header, normalize(header)) for header in headers]

    def guess(field: str, fallback: bool, exclude: set[str] | None = None) -> str:
        skip = exclude or set()
        for pattern in patterns[field]:
            for header, folded in normalized:
                if header in skip:
                    continue
                if pattern in folded:
                    return header
        if fallback and headers:
            for header in headers:
                if header not in skip:
                    return header
            return headers[0]
        return ""

    zone = guess("zone", True)
    residence = guess("residenceZone", False, exclude={zone})
    period = guess("period", True, exclude={zone, residence})
    event_date = guess("eventDate", False, exclude={zone, residence, period})
    violence = guess("violence", True, exclude={zone, residence, period, event_date})
    service = guess("service", True, exclude={zone, residence, period, event_date, violence})
    cases = guess("cases", True, exclude={zone, residence, period, event_date, violence, service})
    capacity = guess("capacity", True, exclude={zone, residence, period, event_date, violence, service, cases})
    person = guess("person", False)
    period_status = guess("periodStatus", False)

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


def validate_processed_rows(rows: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate pre-processed rows for schema and coherence without discarding multi-case expedientes."""
    unspecified = load_constants()["filters"]["unspecified"]
    text_cols = {mapping["zone"], mapping["period"], mapping["violence"], mapping["service"]}
    if mapping["cases"] in text_cols or mapping["capacity"] in text_cols:
        raise ValueError("El mapeo no es coherente: casos y capacidad deben corresponder a columnas numéricas.")

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

        zone_raw = str(raw.get(mapping["zone"]) or "").strip()
        period_raw = str(raw.get(mapping["period"]) or "").strip()
        if not zone_raw and not period_raw:
            removed += 1
            continue

        cases_val, cases_status = parse_numeric_cell(raw.get(mapping["cases"]))
        capacity_val, capacity_status = parse_numeric_cell(raw.get(mapping["capacity"]))
        if cases_status == "invalid" or capacity_status == "invalid":
            removed += 1
            continue

        for status in (cases_status, capacity_status):
            if status == "zero":
                zero_values += 1
            elif status == "na":
                na_values += 1
            elif status == "missing":
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

        zone = canonical_zone(zone_raw)
        period = period_raw or unspecified
        violence = normalize(raw.get(mapping["violence"])) or unspecified
        service = normalize(raw.get(mapping["service"])) or unspecified
        complete = not is_period_incomplete(period, period_status)

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
