from app.services.analytics import build_dashboard
from app.services.rules import (
    canonical_zone,
    classify,
    demo_records,
    js_round,
    parse_numeric_cell,
    suggest_mapping,
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


def test_dato_completo_is_not_mapped_as_period_status_and_unspecified_excluded_from_trends() -> None:
    headers = ["FOLIO", "MUNICIPIO", "TIPO_DE_VIOLENCIA", "FECHA_DE_REGISTRO", "SERVICIO_RECIBIDO_ATENCION", "DATO_COMPLETO"]
    suggested = suggest_mapping(headers)
    assert suggested["periodStatus"] == ""

    rows = [
        {"MUNICIPIO": "Apizaco", "FECHA_DE_REGISTRO": "2024-06-27", "TIPO_DE_VIOLENCIA": "ECONOMICA", "SERVICIO_RECIBIDO_ATENCION": "NINGUNO", "DATO_COMPLETO": "False"},
        {"MUNICIPIO": "Apizaco", "FECHA_DE_REGISTRO": "2025-05-10", "TIPO_DE_VIOLENCIA": "FISICA", "SERVICIO_RECIBIDO_ATENCION": "JURIDICA", "DATO_COMPLETO": "False"},
        {"MUNICIPIO": "Apizaco", "FECHA_DE_REGISTRO": "", "TIPO_DE_VIOLENCIA": "FISICA", "SERVICIO_RECIBIDO_ATENCION": "JURIDICA", "DATO_COMPLETO": "False"},
    ]
    cleaned, _audit = validate_processed_rows(rows, suggested)
    board = build_dashboard(
        cleaned,
        {"period": "Todos los periodos", "municipality": "Todas las zonas", "violence": "Todos los tipos", "service": "Todos los servicios"},
        {"fileName": "base_limpio.xlsx", "synthetic": False, "audit": None},
    )
    assert [t["period"] for t in board["trends"]] == ["2024", "2025"]
    assert board["forecast"]["available"] is True
    assert board["forecast"]["excludedIncompletePeriods"] == []
    assert board["undatedCasesCount"] == 1.0
    apizaco = board["summaries"][0]
    assert sum(item["cases"] for item in apizaco["violenceBreakdown"]) == apizaco["cases"]
    assert sum(item["cases"] for item in apizaco["yearlyTrend"]) + apizaco["undatedCases"] == apizaco["cases"]


def test_dynamic_columns_like_edad_feed_charts_generalities_and_listings() -> None:
    from app.services.rules import detect_extra_schema, validate_processed_dataset

    rows = [
        {
            "FOLIO": "1",
            "MUNICIPIO": "Apizaco",
            "FECHA_DE_REGISTRO": "2024-02-10",
            "FECHA_DE_REGISTRO_ANIO": "2024",
            "TIPO_DE_VIOLENCIA": "FISICA",
            "SERVICIO_RECIBIDO_ATENCION": "JURIDICA",
            "EDAD": "16",
            "ESCOLARIDAD": "PREPARATORIA",
            "HIJOS": "0",
            "FOLIO_OUTLIER": "False",
            "DATO_COMPLETO": "False",
        },
        {
            "FOLIO": "2",
            "MUNICIPIO": "Apizaco",
            "FECHA_DE_REGISTRO": "2025-03-11",
            "FECHA_DE_REGISTRO_ANIO": "2025",
            "TIPO_DE_VIOLENCIA": "PSICOLOGICA",
            "SERVICIO_RECIBIDO_ATENCION": "PSICOLOGICA",
            "EDAD": "32",
            "ESCOLARIDAD": "PREPARATORIA",
            "HIJOS": "2",
            "FOLIO_OUTLIER": "False",
            "DATO_COMPLETO": "False",
        },
        {
            "FOLIO": "3",
            "MUNICIPIO": "Tlaxcala",
            "FECHA_DE_REGISTRO": "2025-04-12",
            "FECHA_DE_REGISTRO_ANIO": "2025",
            "TIPO_DE_VIOLENCIA": "ECONOMICA",
            "SERVICIO_RECIBIDO_ATENCION": "TRABAJO SOCIAL",
            "EDAD": "48",
            "ESCOLARIDAD": "LICENCIATURA",
            "HIJOS": "1",
            "FOLIO_OUTLIER": "False",
            "DATO_COMPLETO": "False",
        },
    ]
    mapping = suggest_mapping(list(rows[0].keys()), rows)
    extra_dims, extra_metrics = detect_extra_schema(rows, mapping)
    assert "ESCOLARIDAD" in extra_dims
    assert "FOLIO_OUTLIER" not in extra_dims
    assert "DATO_COMPLETO" not in extra_dims
    assert "EDAD" in extra_metrics
    assert "HIJOS" in extra_metrics
    assert "FECHA_DE_REGISTRO_ANIO" not in extra_metrics

    cleaned, audit, meta = validate_processed_dataset(rows, mapping)
    board = build_dashboard(
        cleaned,
        {"period": "Todos los periodos", "municipality": "Todas las zonas", "violence": "Todos los tipos", "service": "Todos los servicios"},
        {"fileName": "dinamico.xlsx", "synthetic": False, "audit": audit},
        meta,
    )
    breakdown_keys = {item["key"]: item for item in board["dynamicBreakdowns"]}
    assert "extra:ESCOLARIDAD" in breakdown_keys
    assert "metric:EDAD" in breakdown_keys
    assert breakdown_keys["metric:EDAD"]["kind"] == "numeric"
    assert "metric:HIJOS" in breakdown_keys

    by_mun = {item["name"]: item for item in board["summaries"]}
    assert by_mun["Apizaco"]["extraMetrics"]["EDAD"]["avg"] == 24.0
    assert by_mun["Apizaco"]["extraDimensions"]["ESCOLARIDAD"] == "PREPARATORIA"
    assert len(board["recordRows"]) == 3
    assert board["recordRows"][0]["extraMetrics"]["EDAD"] == 16.0
    assert board["recordRows"][0]["extraMetrics"]["HIJOS"] == 0.0
    assert board["recordRows"][0]["extraDims"]["ESCOLARIDAD"] == "PREPARATORIA"

    # Legacy metadata with *_OUTLIER or False-only dimensions never graphs False
    legacy_board = build_dashboard(
        cleaned,
        {"period": "Todos los periodos", "municipality": "Todas las zonas", "violence": "Todos los tipos", "service": "Todos los servicios"},
        {"fileName": "legacy.xlsx", "synthetic": False, "audit": audit},
        {"extraDimensions": ["FOLIO_OUTLIER", "EDAD_OUTLIER", "ESCOLARIDAD"], "extraMetrics": ["EDAD"]},
    )
    legacy_keys = {item["key"] for item in legacy_board["dynamicBreakdowns"]}
    assert "extra:FOLIO_OUTLIER" not in legacy_keys
    assert "extra:EDAD_OUTLIER" not in legacy_keys
    for bd in legacy_board["dynamicBreakdowns"]:
        assert all(item["name"].upper() not in {"FALSE", "FALSO"} for item in bd["items"])


def test_euv_column_with_many_values_is_excluded_from_charts_and_kept_in_tables() -> None:
    from app.services.rules import detect_extra_schema, detect_table_only_columns, validate_processed_dataset

    rows = [
        {
            "FOLIO": f"F-{idx}",
            "EUV": f"EUV-{1000 + idx}",
            "MUNICIPIO": "Apizaco" if idx % 2 == 0 else "Tlaxcala",
            "FECHA_DE_REGISTRO": "2025-05-01",
            "TIPO_DE_VIOLENCIA": "PSICOLOGICA",
            "SERVICIO_RECIBIDO_ATENCION": "ATENCION PSICOLOGICA",
            "EDAD": str(20 + (idx % 45)),
        }
        for idx in range(60)
    ]
    mapping = suggest_mapping(list(rows[0].keys()), rows)
    assert mapping["person"] == "FOLIO"
    extra_dims, extra_metrics = detect_extra_schema(rows, mapping)
    table_cols = detect_table_only_columns(rows, mapping)
    assert "EUV" not in extra_dims
    assert "EUV" not in extra_metrics
    assert table_cols == ["EUV"]

    cleaned, audit, meta = validate_processed_dataset(rows, mapping)
    board = build_dashboard(
        cleaned,
        {"period": "Todos los periodos", "municipality": "Todas las zonas", "violence": "Todos los tipos", "service": "Todos los servicios"},
        {"fileName": "euv.xlsx", "synthetic": False, "audit": audit},
        meta,
    )
    assert board["tableDimensions"] == ["EUV"]
    assert all("EUV" not in bd["label"] for bd in board["dynamicBreakdowns"])
    assert all("EUV" not in m["label"] for m in board["dynamicMetrics"])
    by_mun = {item["name"]: item for item in board["summaries"]}
    assert by_mun["Apizaco"]["tableCounts"]["EUV"] == 30
    assert by_mun["Tlaxcala"]["tableCounts"]["EUV"] == 30
    assert board["recordRows"][0]["extraDims"]["EUV"] == "EUV-1000"
