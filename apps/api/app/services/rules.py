import json
import math
import re
import unicodedata
from typing import Any

from app.services.constants import load_constants

_NON_DIGITS = re.compile(r"[^\d.-]")


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


def parse_number(value: Any) -> float:
    text = "" if value is None else str(value)
    cleaned = _NON_DIGITS.sub("", text)
    if cleaned in {"", "-", ".", "-.", "+", "+."}:
        return math.nan
    try:
        number = float(cleaned)
    except ValueError:
        return math.nan
    if not math.isfinite(number):
        return math.nan
    return number


def numeric_field(value: Any) -> tuple[float, bool]:
    raw = "" if value is None else str(value)
    if raw.strip() == "":
        return 0.0, True
    number = parse_number(raw)
    if not math.isfinite(number):
        return 0.0, True
    return max(0.0, number), False


def score(cases_value: Any, capacity_value: Any) -> float:
    cases = parse_number(cases_value)
    capacity = parse_number(capacity_value)
    if not math.isfinite(cases):
        cases = 0.0
    divisor = capacity if math.isfinite(capacity) and capacity > 1 else 1.0
    return cases / divisor


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

    def guess(field: str, fallback: bool) -> str:
        for header, folded in normalized:
            if any(pattern in folded for pattern in patterns[field]):
                return header
        if fallback and headers:
            return headers[0]
        return ""

    return {
        "zone": guess("zone", True),
        "period": guess("period", True),
        "violence": guess("violence", True),
        "service": guess("service", True),
        "cases": guess("cases", True),
        "capacity": guess("capacity", True),
        "person": guess("person", False),
    }


def clean_rows(rows: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    unspecified = load_constants()["filters"]["unspecified"]
    processed = len(rows)
    removed = 0
    imputed = 0
    person_duplicates = 0
    seen_rows: set[str] = set()
    seen_people: set[str] = set()

    def period_of(row: dict[str, Any]) -> str:
        return str(row.get(mapping["period"]) or "")

    ordered = sorted(
        rows,
        key=lambda row: (
            natural_key(period_of(row)),
            score(row.get(mapping["cases"]), row.get(mapping["capacity"])),
        ),
        reverse=True,
    )
    cleaned: list[dict[str, Any]] = []
    for raw in ordered:
        if all(str(value).strip() == "" for value in raw.values()):
            removed += 1
            continue
        fingerprint = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
        if fingerprint in seen_rows:
            removed += 1
            continue
        seen_rows.add(fingerprint)
        person_id = normalize(raw.get(mapping["person"])) if mapping.get("person") else ""
        if person_id and person_id in seen_people:
            removed += 1
            person_duplicates += 1
            continue
        if person_id:
            seen_people.add(person_id)
        cases, cases_imputed = numeric_field(raw.get(mapping["cases"]))
        capacity, capacity_imputed = numeric_field(raw.get(mapping["capacity"]))
        imputed += int(cases_imputed) + int(capacity_imputed)
        zone = canonical_zone(raw.get(mapping["zone"]))
        period = str(raw.get(mapping["period"]) or "").strip() or unspecified
        violence = normalize(raw.get(mapping["violence"])) or unspecified
        service = normalize(raw.get(mapping["service"])) or unspecified
        cleaned.append(
            {
                "zone": zone,
                "period": period,
                "violence": violence,
                "service": service,
                "cases": cases,
                "capacity": capacity,
            }
        )
    audit = {
        "processed": processed,
        "valid": len(cleaned),
        "removed": removed,
        "imputed": imputed,
        "personDuplicates": person_duplicates,
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
