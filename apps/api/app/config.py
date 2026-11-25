import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"
_DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "codigo_naranja.sqlite"
_EPHEMERAL_DEV_SECRET = secrets.token_urlsafe(32)
_MIN_SESSION_SECRET = 32


class Settings(BaseSettings):
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # Base de datos: DATABASE_URL tiene prioridad (PostgreSQL en producción o SQLite).
    # DATABASE_DIRECT_URL es opcional para ejecutar DDL/migraciones fuera del pooler (ej. Neon).
    # Si se omite en desarrollo, se usa DATABASE_PATH local.
    database_url: str = ""
    database_direct_url: str = ""
    database_path: str = str(_DEFAULT_DB)
    database_ssl_mode: str = ""

    # Cuenta administradora inicial (sin contraseñas literales en código).
    admin_email: str = ""
    admin_password: str = ""
    admin_password_hash: str = ""

    # Secreto de firma HMAC para sesiones (obligatorio >= 32 caracteres en producción).
    session_secret: str = ""

    # CORS y cookies de sesión.
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool | None = None
    cookie_samesite: Literal["lax", "strict", "none"] | None = None
    cookie_domain: str = ""
    trust_proxy: bool = False

    max_upload_bytes: int = 8 * 1024 * 1024
    max_rows: int = 20_000
    session_hours: int = 24 * 7
    login_attempts: int = 8
    login_window_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def effective_session_secret(self) -> str:
        return self.session_secret.strip() or _EPHEMERAL_DEV_SECRET

    @property
    def effective_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def effective_cookie_samesite(self) -> Literal["lax", "strict", "none"]:
        if self.cookie_samesite is not None:
            return self.cookie_samesite
        return "lax"

    @property
    def effective_cookie_domain(self) -> str | None:
        domain = self.cookie_domain.strip()
        return domain or None

    @property
    def db_backend(self) -> Literal["postgresql", "sqlite"]:
        url = self.database_url.strip().lower()
        if url.startswith(("postgres://", "postgresql://")):
            return "postgresql"
        return "sqlite"

    @property
    def effective_ssl_mode(self) -> str:
        explicit = self.database_ssl_mode.strip()
        if explicit:
            return explicit
        return "require" if self.is_production and self.db_backend == "postgresql" else ""

    @property
    def upload_limit(self) -> int:
        return max(1, min(self.max_upload_bytes, 20 * 1024 * 1024))

    @property
    def row_limit(self) -> int:
        return max(1, min(self.max_rows, 50_000))

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


def validate_runtime_settings(settings: Settings) -> None:
    if settings.effective_cookie_samesite == "none" and not settings.effective_cookie_secure:
        raise RuntimeError(
            "Configuración inválida: COOKIE_SAMESITE=none requiere COOKIE_SECURE=true (HTTPS)."
        )

    if "*" in settings.allowed_origins:
        raise RuntimeError(
            "Configuración inválida: CORS_ORIGINS no debe usar '*' cuando las cookies con credenciales están habilitadas."
        )

    if not settings.is_production:
        return

    missing: list[str] = []
    if len(settings.session_secret.strip()) < _MIN_SESSION_SECRET:
        missing.append(f"SESSION_SECRET (mínimo {_MIN_SESSION_SECRET} caracteres)")
    if not settings.database_url.strip() and not settings.database_path.strip():
        missing.append("DATABASE_URL o DATABASE_PATH")
    if not settings.admin_email.strip():
        missing.append("ADMIN_EMAIL")
    if not settings.admin_password.strip() and not settings.admin_password_hash.strip():
        missing.append("ADMIN_PASSWORD o ADMIN_PASSWORD_HASH")
    if not settings.allowed_origins:
        missing.append("CORS_ORIGINS")

    if missing:
        raise RuntimeError(
            "Faltan variables de entorno obligatorias para producción: " + ", ".join(missing)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
