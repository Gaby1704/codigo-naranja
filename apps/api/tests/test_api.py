from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.config import get_settings
from app.rate_limit import reset as reset_rates
from app.services.uploads import reset as reset_uploads

PASSWORD = "clave-segura-12"
EMAIL = "admin@ejemplo.mx"
HEADERS = {"X-Codigo-Naranja": "1"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "tablero.sqlite"))
    monkeypatch.setenv("ADMIN_EMAIL", EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    reset_rates()
    reset_uploads()
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def _workbook() -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Registros"
    sheet.append(["Municipio", "Periodo", "Tipo_de_violencia", "Tipo_de_servicio", "Casos", "Capacidad", "Identificador"])
    sheet.append(["Apizaco", "2026", "Física", "Orientación jurídica", 10, 5, "EXP-1"])
    sheet.append(["Apizaco", "2024", "Psicológica", "Atención psicológica", 40, 5, "EXP-1"])
    sheet.append(["Tlaxcala", "2026", "Económica", "Trabajo social", 8, 20, "EXP-2"])
    sheet.append(["Chiautempan", "2026", "Física", "Trabajo social", 0, "N/A", "EXP-3"])
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_health_and_public_dashboard(client: TestClient) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert client.get("/api/admin/demo-credentials").status_code == 404
    board = client.get("/api/dashboard", params={"period": "2026"})
    assert board.status_code == 200
    body = board.json()
    assert body["source"]["synthetic"] is True
    assert len(body["summaries"]) == 20
    assert body["totalCases"] > 0
    assert body["forecast"]["available"] is True
    assert len(body["forecast"]["points"]) == 5


def test_login_upload_and_validation(client: TestClient) -> None:
    denied = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert denied.status_code == 403

    wrong = client.post(
        "/api/auth/login",
        headers=HEADERS,
        json={"email": EMAIL, "password": "clave-incorrecta"},
    )
    assert wrong.status_code == 401

    logged = client.post("/api/auth/login", headers=HEADERS, json={"email": EMAIL, "password": PASSWORD})
    assert logged.status_code == 200
    assert logged.json()["user"]["role"] == "admin"
    assert client.get("/api/auth/me").json()["user"]["email"] == EMAIL

    uploaded = client.post(
        "/api/datasets/uploads",
        headers=HEADERS,
        files={"file": ("casos.xlsx", _workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert uploaded.status_code == 200
    preview = uploaded.json()
    assert preview["suggestedMapping"]["person"] == "Identificador"
    applied = client.post(
        f"/api/datasets/uploads/{preview['uploadId']}/apply",
        headers=HEADERS,
        json={"sheet": "Registros", "mapping": preview["suggestedMapping"]},
    )
    assert applied.status_code == 200
    audit = applied.json()["audit"]
    assert audit["valid"] == 4
    assert audit["uniquePeople"] == 3
    assert audit["multiCasePeople"] == 1
    assert audit["zeroValues"] == 1
    assert audit["notApplicable"] == 1

    board = client.get("/api/dashboard", params={"period": "Todos los periodos"}).json()
    by_name = {item["name"]: item for item in board["summaries"]}
    assert by_name["Apizaco"]["cases"] == 50
    assert by_name["Apizaco"]["uniquePeople"] == 1
    assert by_name["Apizaco"]["classification"]["color"] == "priority"
    assert by_name["Tlaxcala"]["classification"]["color"] == "stable"
    assert by_name["Chiautempan"]["casesZeroCount"] == 1
    assert by_name["Chiautempan"]["capacityNaCount"] == 1
    assert board["source"]["synthetic"] is False

    assert client.post("/api/auth/logout", headers=HEADERS).status_code == 204
    assert client.get("/api/auth/me").json()["user"] is None
    blocked = client.post(
        "/api/datasets/uploads",
        headers=HEADERS,
        files={"file": ("casos.xlsx", _workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert blocked.status_code == 401
