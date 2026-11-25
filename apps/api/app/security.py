import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from app.config import get_settings

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_BCRYPT_HASH = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")
_DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt(rounds=12))
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


def valid_bcrypt_hash(value: str) -> bool:
    return bool(value) and _BCRYPT_HASH.fullmatch(value.strip()) is not None


def dummy_verify(password: str) -> None:
    verify_password(password, _DUMMY_HASH.decode("utf-8"))


def token_digest(token: str) -> str:
    secret = get_settings().effective_session_secret.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_session_token(raw_token: str) -> str:
    signature = token_digest(raw_token)
    return f"{raw_token}.{signature}"


def extract_verified_token(cookie_value: str | None) -> str | None:
    if not cookie_value or "." not in cookie_value:
        return None
    raw_token, provided_sig = cookie_value.rsplit(".", 1)
    if not raw_token or not provided_sig:
        return None
    expected_sig = token_digest(raw_token)
    if not hmac.compare_digest(provided_sig, expected_sig):
        return None
    return raw_token


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
