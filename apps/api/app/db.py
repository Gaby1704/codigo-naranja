import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import get_settings
#comedia
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
  id TEXT PRIMARY KEY,
  name TEXT,
  synthetic INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 0,
  audit_json TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  zone TEXT NOT NULL,
  residence_zone TEXT NOT NULL DEFAULT '',
  period TEXT NOT NULL,
  event_date TEXT NOT NULL DEFAULT '',
  period_complete INTEGER NOT NULL DEFAULT 1,
  violence TEXT NOT NULL,
  service TEXT NOT NULL,
  cases REAL,
  capacity REAL,
  cases_status TEXT NOT NULL DEFAULT 'value',
  capacity_status TEXT NOT NULL DEFAULT 'value',
  person_id TEXT NOT NULL DEFAULT '',
  extra_dims_json TEXT NOT NULL DEFAULT '{}',
  extra_metrics_json TEXT NOT NULL DEFAULT '{}',
  extra_metric_statuses_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_records_dataset ON records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_sessions_hash ON sessions(token_hash);
"""

POSTGRES_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      token_hash TEXT NOT NULL UNIQUE,
      expires_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS datasets (
      id TEXT PRIMARY KEY,
      name TEXT,
      synthetic INTEGER NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 0,
      audit_json TEXT,
      metadata_json TEXT,
      created_at TEXT NOT NULL
    )
    """,
    "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS metadata_json TEXT",
    """
    CREATE TABLE IF NOT EXISTS records (
      id SERIAL PRIMARY KEY,
      dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
      zone TEXT NOT NULL,
      residence_zone TEXT NOT NULL DEFAULT '',
      period TEXT NOT NULL,
      event_date TEXT NOT NULL DEFAULT '',
      period_complete INTEGER NOT NULL DEFAULT 1,
      violence TEXT NOT NULL,
      service TEXT NOT NULL,
      cases DOUBLE PRECISION,
      capacity DOUBLE PRECISION,
      cases_status TEXT NOT NULL DEFAULT 'value',
      capacity_status TEXT NOT NULL DEFAULT 'value',
      person_id TEXT NOT NULL DEFAULT '',
      extra_dims_json TEXT NOT NULL DEFAULT '{}',
      extra_metrics_json TEXT NOT NULL DEFAULT '{}',
      extra_metric_statuses_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS residence_zone TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS event_date TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS period_complete INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS cases_status TEXT NOT NULL DEFAULT 'value'",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS capacity_status TEXT NOT NULL DEFAULT 'value'",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS person_id TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS extra_dims_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS extra_metrics_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE records ADD COLUMN IF NOT EXISTS extra_metric_statuses_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE records ALTER COLUMN cases DROP NOT NULL",
    "ALTER TABLE records ALTER COLUMN capacity DROP NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_records_dataset ON records(dataset_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_hash ON sessions(token_hash)",
]

_EXPECTED_RECORD_COLUMNS = {
    "id",
    "dataset_id",
    "zone",
    "residence_zone",
    "period",
    "event_date",
    "period_complete",
    "violence",
    "service",
    "cases",
    "capacity",
    "cases_status",
    "capacity_status",
    "person_id",
    "extra_dims_json",
    "extra_metrics_json",
    "extra_metric_statuses_json",
}


class _PostgresConnection:
    """Thin adapter so standard '?' queries work identically against PostgreSQL."""

    def __init__(self, raw_conn: Any) -> None:
        self._conn = raw_conn

    @staticmethod
    def _adapt_sql(sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        cur = self._conn.cursor()
        cur.execute(self._adapt_sql(sql), tuple(params))
        return cur

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> Any:
        cur = self._conn.cursor()
        cur.executemany(self._adapt_sql(sql), [tuple(row) for row in seq_of_params])
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _sqlite_path_from_settings() -> Path:
    settings = get_settings()
    url = settings.database_url.strip()
    if url.lower().startswith("sqlite:///"):
        raw = url[len("sqlite:///") :]
        return Path(raw)
    return Path(settings.database_path)


def _normalize_postgres_dsn(raw_url: str, ssl_mode: str = "") -> tuple[str, bool]:
    dsn = raw_url.strip()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://") :]
    parsed = urlparse(dsn)
    is_pooler = "-pooler" in (parsed.hostname or "").lower()
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # PgBouncer / Neon -pooler suele fallar en el handshake si recibe channel_binding=require.
    if is_pooler and "channel_binding" in query_params:
        query_params.pop("channel_binding", None)

    if ssl_mode and "sslmode" not in query_params:
        query_params["sslmode"] = ssl_mode

    cleaned = parsed._replace(query=urlencode(query_params))
    return urlunparse(cleaned), is_pooler


def _connect_postgres(raw_url: str) -> _PostgresConnection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL apunta a PostgreSQL pero falta el paquete 'psycopg'. Instálalo desde requirements.txt."
        ) from exc

    settings = get_settings()
    dsn, is_pooler = _normalize_postgres_dsn(raw_url, settings.effective_ssl_mode)
    # prepare_threshold=None desactiva prepared statements en el servidor (recomendado para PgBouncer / Neon -pooler).
    raw_conn = psycopg.connect(
        dsn,
        row_factory=dict_row,
        connect_timeout=10,
        prepare_threshold=None if is_pooler else 5,
    )
    return _PostgresConnection(raw_conn)


def _migrate_sqlite_datasets(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(datasets)").fetchall()}
    if cols and "metadata_json" not in cols:
        conn.execute("ALTER TABLE datasets ADD COLUMN metadata_json TEXT")


def _migrate_sqlite_records(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(records)").fetchall()
    if not cols:
        return
    col_map = {row["name"]: row for row in cols}
    missing = _EXPECTED_RECORD_COLUMNS - set(col_map)
    cases_notnull = col_map.get("cases") is not None and col_map["cases"]["notnull"] == 1
    capacity_notnull = col_map.get("capacity") is not None and col_map["capacity"]["notnull"] == 1
    if not missing and not cases_notnull and not capacity_notnull:
        return

    if not cases_notnull and not capacity_notnull:
        for col in sorted(missing):
            if col.endswith("_json"):
                conn.execute(f"ALTER TABLE records ADD COLUMN {col} TEXT NOT NULL DEFAULT '{{}}'")
            elif col == "period_complete":
                conn.execute("ALTER TABLE records ADD COLUMN period_complete INTEGER NOT NULL DEFAULT 1")
            elif col in {"cases_status", "capacity_status"}:
                conn.execute(f"ALTER TABLE records ADD COLUMN {col} TEXT NOT NULL DEFAULT 'value'")
            else:
                conn.execute(f"ALTER TABLE records ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        return

    conn.execute("ALTER TABLE records RENAME TO records_old")
    conn.execute(
        """
        CREATE TABLE records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
          zone TEXT NOT NULL,
          residence_zone TEXT NOT NULL DEFAULT '',
          period TEXT NOT NULL,
          event_date TEXT NOT NULL DEFAULT '',
          period_complete INTEGER NOT NULL DEFAULT 1,
          violence TEXT NOT NULL,
          service TEXT NOT NULL,
          cases REAL,
          capacity REAL,
          cases_status TEXT NOT NULL DEFAULT 'value',
          capacity_status TEXT NOT NULL DEFAULT 'value',
          person_id TEXT NOT NULL DEFAULT '',
          extra_dims_json TEXT NOT NULL DEFAULT '{}',
          extra_metrics_json TEXT NOT NULL DEFAULT '{}',
          extra_metric_statuses_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO records (id, dataset_id, zone, period, violence, service, cases, capacity)
        SELECT id, dataset_id, zone, period, violence, service, cases, capacity FROM records_old
        """
    )
    conn.execute("DROP TABLE records_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_dataset ON records(dataset_id)")


def connect() -> Any:
    settings = get_settings()
    if settings.db_backend == "postgresql":
        return _connect_postgres(settings.database_url)

    path = _sqlite_path_from_settings()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    settings = get_settings()
    if settings.db_backend == "postgresql":
        migration_url = settings.database_direct_url.strip() or settings.database_url
        conn = _connect_postgres(migration_url)
        try:
            for stmt in POSTGRES_STATEMENTS:
                conn.execute(stmt)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    with db() as conn:
        conn.executescript(SQLITE_SCHEMA)
        _migrate_sqlite_datasets(conn)
        _migrate_sqlite_records(conn)


@contextmanager
def db() -> Iterator[Any]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
