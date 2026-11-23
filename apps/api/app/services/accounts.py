import logging
import secrets
import uuid
from dataclasses import dataclass

from app.config import get_settings
from app.db import db
from app.security import (
    dummy_verify,
    hash_password,
    iso,
    normalize_email,
    password_problem,
    session_expiry,
    token_digest,
    utcnow,
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
    if not email and not password:
        logger.info("Sin ADMIN_EMAIL y ADMIN_PASSWORD: no se creó cuenta administradora.")
        return
    if not valid_email(email) or password_problem(password):
        logger.error("ADMIN_EMAIL o ADMIN_PASSWORD no cumplen la política. No se creó la cuenta.")
        return
    with db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, role, created_at)
                VALUES (?, 'Administrador', ?, ?, 'admin', ?)
                """,
                (uuid.uuid4().hex, email, hash_password(password), iso(utcnow())),
            )
        else:
            conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
    logger.info("Cuenta administradora lista.")


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
    token = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (uuid.uuid4().hex, user_id, token_digest(token), iso(session_expiry()), iso(utcnow())),
        )
    return token


def user_from_token(token: str | None) -> CurrentUser | None:
    if not token:
        return None
    digest = token_digest(token)
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


def delete_session(token: str | None) -> None:
    if not token:
        return
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest(token),))
