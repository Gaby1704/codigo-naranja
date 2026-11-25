from app.services.analytics import build_dashboard
from app.services.rules import (
    canonical_zone,
    classify,
    demo_records,
    js_round,
    parse_numeric_cell,
    validate_processed_rows,
)


def test_js_round_matches_half_up() -> None:
    assert js_round(15.84) == 16
    assert js_round(21.84) == 22
    assert js_round(60.9) == 61


def test_demo_records_follow_the_original_formula() -> None:
    records = demo_records()
    assert len(records) == 60
    assert records[0] == {
        "zone": "Calpulalpan",
        "period": "2024",
        "violence": "Psicológica",
        "service": "Atención psicológica",
        "cases": 16,
        "capacity": 22,
    }
    nanacamilpa_2025 = next(row for row in records if row["zone"] == "Nanacamilpa" and row["period"] == "2025")
    assert nanacamilpa_2025["cases"] == 61
    assert nanacamilpa_2025["capacity"] == 72


def test_classification_order() -> None:
    assert classify(1.3, 100)["color"] == "priority"
    assert classify(1.29, 10)["color"] == "watch"
    assert classify(0.9, 10)["color"] == "watch"
    assert classify(0.9, 35)["color"] == "elevated"
    assert classify(1.0, 40)["color"] == "elevated"
    assert classify(0.85, 40)["color"] == "stable"
    assert classify(0.8, 10)["color"] == "stable"


def test_numeric_cell_distinguishes_zero_na_missing_and_invalid() -> None:
    assert parse_numeric_cell(0) == (0.0, "zero")
    assert parse_numeric_cell("0") == (0.0, "zero")
    assert parse_numeric_cell("N/A") == (None, "na")
    assert parse_numeric_cell("No aplica") == (None, "na")
    assert parse_numeric_cell("") == (None, "missing")
    assert parse_numeric_cell(None) == (None, "missing")
    assert parse_numeric_cell("Sin dato") == (None, "missing")
    assert parse_numeric_cell(-3) == (None, "invalid")
    assert parse_numeric_cell("texto") == (None, "invalid")


def test_validation_preserves_multicase_expedientes_and_counts_unique_people() -> None:
    rows = [
        {"Municipio": "Apizaco", "Residencia": "Tlaxcala", "Periodo": "2026", "FechaHecho": "2026-01-10", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "10", "Capacidad": "5", "Id": "EXP-1"},
        {"Municipio": "Apizaco", "Residencia": "Tlaxcala", "Periodo": "2026", "FechaHecho": "2026-02-11", "Tipo": "Psicológica", "Servicio": "Psicología", "Casos": "2", "Capacidad": "3", "Id": "EXP-1"},
        {"Municipio": "", "Residencia": "", "Periodo": "", "FechaHecho": "", "Tipo": "", "Servicio": "", "Casos": "", "Capacidad": "", "Id": ""},
        {"Municipio": "Apizaco", "Residencia": "Tlaxcala", "Periodo": "2026", "FechaHecho": "2026-01-10", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "10", "Capacidad": "5", "Id": "EXP-1"},
    ]
    mapping = {
        "zone": "Municipio",
        "residenceZone": "Residencia",
        "period": "Periodo",
        "eventDate": "FechaHecho",
        "violence": "Tipo",
        "service": "Servicio",
        "cases": "Casos",
        "capacity": "Capacidad",
        "person": "Id",
        "periodStatus": "",
    }
    cleaned, audit = validate_processed_rows(rows, mapping)
    assert audit == {
        "processed": 4,
        "valid": 2,
        "removed": 2,
        "uniquePeople": 1,
        "multiCasePeople": 1,
        "zeroValues": 0,
        "notApplicable": 0,
        "missingValues": 0,
        "hasResidenceDistinction": True,
        "hasEventDateDistinction": True,
    }
    assert len(cleaned) == 2
    assert cleaned[0]["residence_zone"] == "Tlaxcala"


def test_validation_handles_zero_na_missing_and_rejects_incoherent() -> None:
    rows = [
        {"Municipio": "foo bar", "Periodo": "2026", "Tipo": "", "Servicio": "", "Casos": "0", "Capacidad": "N/A", "Id": "EXP-9"},
        {"Municipio": "Apizaco", "Periodo": "2026", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "", "Capacidad": "10", "Id": "EXP-10"},
        {"Municipio": "Apizaco", "Periodo": "2026", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "invalido", "Capacidad": "10", "Id": "EXP-11"},
    ]
    mapping = {
        "zone": "Municipio",
        "residenceZone": "",
        "period": "Periodo",
        "eventDate": "",
        "violence": "Tipo",
        "service": "Servicio",
        "cases": "Casos",
        "capacity": "Capacidad",
        "person": "Id",
        "periodStatus": "",
    }
    cleaned, audit = validate_processed_rows(rows, mapping)
    assert len(cleaned) == 2
    assert cleaned[0]["zone"] == "FOO BAR"
    assert cleaned[0]["cases"] == 0.0
    assert cleaned[0]["cases_status"] == "zero"
    assert cleaned[0]["capacity"] is None
    assert cleaned[0]["capacity_status"] == "na"
    assert cleaned[1]["cases"] is None
    assert cleaned[1]["cases_status"] == "missing"
    assert audit["removed"] == 1
    assert audit["zeroValues"] == 1
    assert audit["notApplicable"] == 1
    assert audit["missingValues"] == 1
    assert canonical_zone("  tlaxcala ") == "Tlaxcala"


def test_dashboard_excludes_incomplete_periods_from_five_year_forecast() -> None:
    records = [
        {"zone": "Apizaco", "residence_zone": "", "period": "2024", "event_date": "", "period_complete": 1, "violence": "FISICA", "service": "JURIDICA", "cases": 20.0, "capacity": 15.0, "cases_status": "value", "capacity_status": "value", "person_id": "E1"},
        {"zone": "Apizaco", "residence_zone": "", "period": "2025", "event_date": "", "period_complete": 1, "violence": "FISICA", "service": "JURIDICA", "cases": 30.0, "capacity": 15.0, "cases_status": "value", "capacity_status": "value", "person_id": "E2"},
        {"zone": "Apizaco", "residence_zone": "", "period": "2026 (parcial)", "event_date": "", "period_complete": 0, "violence": "FISICA", "service": "JURIDICA", "cases": 5.0, "capacity": 15.0, "cases_status": "value", "capacity_status": "value", "person_id": "E3"},
    ]
    board = build_dashboard(
        records,
        {"period": "Todos los periodos", "municipality": "Todas las zonas", "violence": "Todos los tipos", "service": "Todos los servicios"},
        {"fileName": "test.xlsx", "synthetic": False, "audit": None},
    )
    forecast = board["forecast"]
    assert forecast["available"] is True
    assert forecast["completePeriodsUsed"] == ["2024", "2025"]
    assert forecast["excludedIncompletePeriods"] == ["2026 (parcial)"]
    assert len(forecast["points"]) == 5
    assert forecast["points"][0]["period"] == "2026"
    assert forecast["direction"] == "al alza"
