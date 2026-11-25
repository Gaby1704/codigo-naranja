import logging
import secrets
import uuid
from dataclasses import dataclass

from app.config import get_settings
from app.db import db
from app.security import (
    dummy_verify,
    extract_verified_token,
    hash_password,
    iso,
    normalize_email,
    password_problem,
    session_expiry,
    sign_session_token,
    token_digest,
    utcnow,
    valid_bcrypt_hash,
    valid_email,
    verify_password,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    name: str
    email: str
    role: str

    def public(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email, "role": self.role}


def seed_admin() -> None:
    settings = get_settings()
    email = normalize_email(settings.admin_email)
    password = settings.admin_password
    password_hash_env = settings.admin_password_hash.strip()

    if not email and not password and not password_hash_env:
        logger.info("Sin credenciales de administrador configuradas; la carga de datos queda deshabilitada.")
        return
    if not valid_email(email):
        logger.error("ADMIN_EMAIL no tiene un formato válido. No se creó la cuenta administradora.")
        return

    resolved_hash = ""
    if password_hash_env:
        if not valid_bcrypt_hash(password_hash_env):
            logger.error("ADMIN_PASSWORD_HASH no tiene un formato bcrypt válido.")
            return
        resolved_hash = password_hash_env
    else:
        if password_problem(password):
            logger.error("ADMIN_PASSWORD no cumple la política mínima de seguridad. No se creó la cuenta.")
            return
        resolved_hash = hash_password(password)

    with db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, role, created_at)
                VALUES (?, 'Administrador', ?, ?, 'admin', ?)
                """,
                (uuid.uuid4().hex, email, resolved_hash, iso(utcnow())),
            )
        else:
            conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
    logger.info("Cuenta administradora verificada.")


def authenticate(email: str, password: str) -> tuple[str, CurrentUser | None]:
    normalized = normalize_email(email)
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash, role FROM users WHERE email = ?",
            (normalized,),
        ).fetchone()
    if row is None:
        dummy_verify(password)
        return "invalid", None
    if not verify_password(password, row["password_hash"]):
        return "invalid", None
    user = CurrentUser(id=row["id"], name=row["name"], email=row["email"], role=row["role"])
    if user.role != "admin":
        return "forbidden", None
    return "ok", user


def create_session(user_id: str) -> str:
    raw_token = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (uuid.uuid4().hex, user_id, token_digest(raw_token), iso(session_expiry()), iso(utcnow())),
        )
    return sign_session_token(raw_token)


def user_from_token(cookie_value: str | None) -> CurrentUser | None:
    raw_token = extract_verified_token(cookie_value)
    if not raw_token:
        return None
    digest = token_digest(raw_token)
    now = iso(utcnow())
    with db() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.name, users.email, users.role, sessions.id AS session_id, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (digest,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= now:
            conn.execute("DELETE FROM sessions WHERE id = ?", (row["session_id"],))
            return None
    return CurrentUser(id=row["id"], name=row["name"], email=row["email"], role=row["role"])


def delete_session(cookie_value: str | None) -> None:
    raw_token = extract_verified_token(cookie_value)
    if not raw_token:
        return
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest(raw_token),))
