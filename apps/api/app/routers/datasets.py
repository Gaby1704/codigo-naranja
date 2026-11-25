import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import get_settings
from app.deps import require_admin, require_csrf
from app.schemas import ApplyBody, SheetBody, UploadPreview
from app.services.accounts import CurrentUser
from app.services.catalog import replace_active
from app.services.excel import WorkbookError, build_template, parse_workbook
from app.services.rules import detect_extra_schema, suggest_mapping, validate_processed_dataset
from app.services.uploads import drop_upload, get_upload, save_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])
_UPLOAD_ID = re.compile(r"^[a-f0-9]{32}$")

_TEMPLATE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _pending(upload_id: str, user_id: str):
    if _UPLOAD_ID.fullmatch(upload_id) is None:
        raise HTTPException(status_code=404, detail="La carga expiró o no existe. Vuelve a seleccionar el archivo.")
    pending = get_upload(upload_id, user_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="La carga expiró o no existe. Vuelve a seleccionar el archivo.")
    return pending


def _filename(upload: UploadFile) -> str:
    raw = Path(upload.filename or "archivo.xlsx").name
    cleaned = "".join(char for char in raw if char.isprintable() and char not in "\\/")
    cleaned = cleaned.strip()[:120]
    return cleaned or "archivo.xlsx"


def _preview(upload_id: str, name: str, sheets: dict[str, list[dict[str, str]]], sheet: str) -> dict:
    rows = sheets[sheet]
    headers = list(rows[0].keys()) if rows else []
    visible = headers[:8]
    suggested = suggest_mapping(headers, rows)
    extra_dims, extra_metrics = detect_extra_schema(rows, suggested)
    return {
        "uploadId": upload_id,
        "name": name,
        "sheet": sheet,
        "sheets": list(sheets),
        "headers": headers,
        "preview": [{header: row.get(header, "") for header in visible} for row in rows[:3]],
        "rowCount": len(rows),
        "suggestedMapping": suggested,
        "detectedDimensions": extra_dims,
        "detectedMetrics": extra_metrics,
    }


@router.get("/template")
def template(user: CurrentUser = Depends(require_admin)) -> Response:
    del user
    return Response(
        content=build_template(),
        media_type=_TEMPLATE,
        headers={"Content-Disposition": 'attachment; filename="plantilla-smet.xlsx"'},
    )


@router.post("/uploads", response_model=UploadPreview)
async def upload_dataset(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    name = _filename(file)
    payload = await file.read(get_settings().upload_limit + 1)
    await file.close()
    if len(payload) > get_settings().upload_limit:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño permitido (8 MB).")
    if not payload:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    try:
        sheets = parse_workbook(payload, name)
    except WorkbookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    upload_id = save_upload(user.id, name, sheets)
    return _preview(upload_id, name, sheets, next(iter(sheets)))


@router.post("/uploads/{upload_id}/sheet", response_model=UploadPreview)
def change_sheet(
    upload_id: str,
    body: SheetBody,
    user: CurrentUser = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    pending = _pending(upload_id, user.id)
    rows = pending.sheets.get(body.sheet)
    if not rows:
        raise HTTPException(status_code=400, detail="La hoja seleccionada no contiene registros.")
    return _preview(upload_id, pending.name, pending.sheets, body.sheet)


@router.post("/uploads/{upload_id}/apply")
def apply_upload(
    upload_id: str,
    body: ApplyBody,
    user: CurrentUser = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    pending = _pending(upload_id, user.id)
    rows = pending.sheets.get(body.sheet)
    if not rows:
        raise HTTPException(status_code=400, detail="La hoja seleccionada no contiene registros.")
    headers = list(rows[0].keys())
    mapping = body.mapping.model_dump()
    if any(column and column not in headers for column in mapping.values()):
        raise HTTPException(status_code=400, detail="La asignación incluye una columna que no existe en la hoja.")
    try:
        cleaned, audit, metadata = validate_processed_dataset(rows, mapping)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not cleaned:
        raise HTTPException(status_code=400, detail="No se encontraron registros válidos coherentes con el esquema esperado.")
    replace_active(pending.name, cleaned, audit, metadata)
    drop_upload(upload_id)
    return {"audit": audit, "fileName": pending.name}
