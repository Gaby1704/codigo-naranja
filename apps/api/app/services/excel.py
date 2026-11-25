from datetime import date, datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook

from app.config import get_settings

MAX_COLUMNS = 40
MAX_CELL = 500


class WorkbookError(ValueError):
    pass


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.hour == value.minute == value.second == 0 else value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).replace("\x00", "").strip()
    return text[:MAX_CELL]


def _unique_headers(raw_headers: list[str]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(raw_headers, start=1):
        name = header or f"Columna {index}"
        count = seen.get(name, 0) + 1
        seen[name] = count
        headers.append(name if count == 1 else f"{name}_{count}")
    return headers


def _limit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    limit = get_settings().row_limit
    if len(rows) > limit:
        raise WorkbookError(f"La hoja supera el límite de {limit} filas.")
    return rows


def _rows_from_matrix(matrix: list[list[str]]) -> list[dict[str, str]]:
    if not matrix:
        return []
    width = min(len(matrix[0]), MAX_COLUMNS)
    headers = _unique_headers([_cell(cell) for cell in matrix[0][:width]])
    if not any(headers):
        return []
    rows: list[dict[str, str]] = []
    for line in matrix[1:]:
        if len(rows) > get_settings().row_limit:
            raise WorkbookError(f"La hoja supera el límite de {get_settings().row_limit} filas.")
        padded = list(line[:width]) + [""] * (width - len(line[:width]))
        record = {headers[index]: _cell(padded[index]) for index in range(width)}
        if any(value.strip() for value in record.values()):
            rows.append(record)
    return _limit_rows(rows)


def parse_workbook(payload: bytes, filename: str) -> dict[str, list[dict[str, str]]]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        if not payload.startswith(b"PK"):
            raise WorkbookError("El archivo no es un libro .xlsx válido.")
        return _parse_xlsx(payload)
    if lower.endswith(".xls"):
        if not payload.startswith(b"\xd0\xcf\x11\xe0"):
            raise WorkbookError("El archivo no es un libro .xls válido.")
        return _parse_xls(payload)
    raise WorkbookError("Selecciona un archivo Excel .xlsx o .xls.")


def _parse_xlsx(payload: bytes) -> dict[str, list[dict[str, str]]]:
    try:
        workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:
        raise WorkbookError("No fue posible leer el archivo. Verifica que sea un libro Excel válido.") from exc
    sheets: dict[str, list[dict[str, str]]] = {}
    try:
        for sheet in workbook.worksheets:
            matrix: list[list[str]] = []
            for row in sheet.iter_rows(values_only=True):
                if len(matrix) > get_settings().row_limit + 1:
                    raise WorkbookError(f"La hoja supera el límite de {get_settings().row_limit} filas.")
                matrix.append(list(row[:MAX_COLUMNS]))
            parsed = _rows_from_matrix(matrix)
            if parsed:
                sheets[sheet.title] = parsed
    finally:
        workbook.close()
    if not sheets:
        raise WorkbookError("El libro no contiene filas. Selecciona una hoja con registros.")
    return sheets


def _parse_xls(payload: bytes) -> dict[str, list[dict[str, str]]]:
    try:
        import xlrd
    except ImportError as exc:
        raise WorkbookError("La lectura de archivos .xls no está disponible.") from exc
    try:
        book = xlrd.open_workbook(file_contents=payload)
    except Exception as exc:
        raise WorkbookError("No fue posible leer el archivo .xls.") from exc
    sheets: dict[str, list[dict[str, str]]] = {}
    for sheet in book.sheets():
        matrix = []
        limit = get_settings().row_limit + 1
        for row_index in range(min(sheet.nrows, limit + 1)):
            matrix.append([sheet.cell_value(row_index, col) for col in range(min(sheet.ncols, MAX_COLUMNS))])
        if sheet.nrows > limit:
            raise WorkbookError(f"La hoja supera el límite de {get_settings().row_limit} filas.")
        parsed = _rows_from_matrix(matrix)
        if parsed:
            sheets[sheet.name] = parsed
    if not sheets:
        raise WorkbookError("El libro no contiene filas. Selecciona una hoja con registros.")
    return sheets


def build_template() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Registros_Procesados"
    headers = [
        "Municipio_hecho",
        "Municipio_residencia",
        "Periodo_corte",
        "Fecha_hecho",
        "Tipo_de_violencia",
        "Tipo_de_servicio",
        "Casos",
        "Servicios_atenciones",
        "Expediente",
        "Estado_periodo",
    ]
    rows = [
        ["APIZACO", "YAUHQUEMEHCAN", "2026", "2026-02-14", "PSICOLOGICA", "ATENCION PSICOLOGICA", 1, 2, "EXP-0001", "COMPLETO"],
        ["APIZACO", "YAUHQUEMEHCAN", "2026", "2026-02-20", "ECONOMICA", "ORIENTACION JURIDICA", 1, 1, "EXP-0001", "COMPLETO"],
        ["TLAXCALA", "TLAXCALA", "2026", "2026-03-01", "FISICA", "TRABAJO SOCIAL", 0, "N/A", "EXP-0002", "COMPLETO"],
    ]
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
