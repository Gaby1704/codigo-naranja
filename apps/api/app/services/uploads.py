import time
import uuid
from dataclasses import dataclass, field

_TTL_SECONDS = 30 * 60
_MAX_PENDING = 30


@dataclass
class PendingUpload:
    user_id: str
    name: str
    sheets: dict[str, list[dict[str, str]]]
    created_at: float = field(default_factory=time.monotonic)


UPLOADS: dict[str, PendingUpload] = {}


def _purge(now: float | None = None) -> None:
    moment = time.monotonic() if now is None else now
    expired = [key for key, item in UPLOADS.items() if moment - item.created_at > _TTL_SECONDS]
    for key in expired:
        UPLOADS.pop(key, None)
    overflow = len(UPLOADS) - _MAX_PENDING
    if overflow > 0:
        oldest = sorted(UPLOADS.items(), key=lambda item: item[1].created_at)[:overflow]
        for key, _item in oldest:
            UPLOADS.pop(key, None)


def save_upload(user_id: str, name: str, sheets: dict[str, list[dict[str, str]]]) -> str:
    _purge()
    upload_id = uuid.uuid4().hex
    UPLOADS[upload_id] = PendingUpload(user_id=user_id, name=name, sheets=sheets)
    _purge()
    return upload_id


def get_upload(upload_id: str, user_id: str) -> PendingUpload | None:
    _purge()
    item = UPLOADS.get(upload_id)
    if item is None or item.user_id != user_id:
        return None
    return item


def drop_upload(upload_id: str) -> None:
    UPLOADS.pop(upload_id, None)


def reset() -> None:
    UPLOADS.clear()
