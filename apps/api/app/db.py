import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

SCHEMA = """
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
  person_id TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_records_dataset ON records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_sessions_hash ON sessions(token_hash);
"""

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
}


def _migrate_records_if_needed(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(records)").fetchall()
    if not cols:
        return
    col_map = {row["name"]: row for row in cols}
    missing = _EXPECTED_RECORD_COLUMNS - set(col_map)
    cases_notnull = col_map.get("cases") is not None and col_map["cases"]["notnull"] == 1
    capacity_notnull = col_map.get("capacity") is not None and col_map["capacity"]["notnull"] == 1
    if not missing and not cases_notnull and not capacity_notnull:
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
          person_id TEXT NOT NULL DEFAULT ''
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


def connect() -> sqlite3.Connection:
    settings = get_settings()
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        _migrate_records_if_needed(conn)


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
