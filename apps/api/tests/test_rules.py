from app.services.rules import canonical_zone, classify, clean_rows, demo_records, js_round


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


def test_cleaning_keeps_one_alert_per_person() -> None:
    rows = [
        {"Municipio": "Apizaco", "Periodo": "2026", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "10", "Capacidad": "5", "Id": "EXP-1"},
        {"Municipio": "Apizaco", "Periodo": "2024", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "40", "Capacidad": "5", "Id": "EXP-1"},
        {"Municipio": "", "Periodo": "", "Tipo": "", "Servicio": "", "Casos": "", "Capacidad": "", "Id": ""},
        {"Municipio": "Apizaco", "Periodo": "2026", "Tipo": "Física", "Servicio": "Jurídica", "Casos": "10", "Capacidad": "5", "Id": "EXP-1"},
    ]
    mapping = {
        "zone": "Municipio",
        "period": "Periodo",
        "violence": "Tipo",
        "service": "Servicio",
        "cases": "Casos",
        "capacity": "Capacidad",
        "person": "Id",
    }
    cleaned, audit = clean_rows(rows, mapping)
    assert audit == {"processed": 4, "valid": 1, "removed": 3, "imputed": 0, "personDuplicates": 1}
    assert cleaned[0]["zone"] == "Apizaco"
    assert cleaned[0]["period"] == "2026"
    assert cleaned[0]["violence"] == "FISICA"
    assert cleaned[0]["cases"] == 10


def test_cleaning_imputes_blank_numbers_and_unknown_zones() -> None:
    rows = [{"Municipio": "foo bar", "Periodo": "", "Tipo": "", "Servicio": "", "Casos": "", "Capacidad": "no", "Id": "EXP-9"}]
    mapping = {
        "zone": "Municipio",
        "period": "Periodo",
        "violence": "Tipo",
        "service": "Servicio",
        "cases": "Casos",
        "capacity": "Capacidad",
        "person": "Id",
    }
    cleaned, audit = clean_rows(rows, mapping)
    assert cleaned[0]["zone"] == "FOO BAR"
    assert cleaned[0]["period"] == "NO ESPECIFICADO"
    assert cleaned[0]["cases"] == 0
    assert cleaned[0]["capacity"] == 0
    assert audit["imputed"] == 2
    assert canonical_zone("  tlaxcala ") == "Tlaxcala"
