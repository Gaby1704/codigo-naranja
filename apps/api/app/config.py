from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"
_DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "codigo_naranja.sqlite"


class Settings(BaseSettings):
    app_env: str = "development"
    database_path: str = str(_DEFAULT_DB)
    admin_email: str = ""
    admin_password: str = ""
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
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
        return self.app_env.lower() == "production"

    @property
    def upload_limit(self) -> int:
        return max(1, min(self.max_upload_bytes, 20 * 1024 * 1024))

    @property
    def row_limit(self) -> int:
        return max(1, min(self.max_rows, 50_000))

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
