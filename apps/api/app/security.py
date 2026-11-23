import hashlib
import re
from datetime import datetime, timedelta, timezone

import bcrypt

from app.config import get_settings

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DUMMY_HASH = bcrypt.hashpw(b"codigo-naranja-dummy-password", bcrypt.gensalt(rounds=12))
MIN_PASSWORD = 12
MAX_PASSWORD_BYTES = 72


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def dummy_verify(password: str) -> None:
    verify_password(password, _DUMMY_HASH.decode("utf-8"))


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    hours = max(1, min(get_settings().session_hours, 24 * 30))
    return utcnow() + timedelta(hours=hours)


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD:
        return "La contraseña debe tener al menos 12 caracteres."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "La contraseña supera el límite de 72 bytes."
    return None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return bool(email) and len(email) <= 254 and _EMAIL.fullmatch(email) is not None
