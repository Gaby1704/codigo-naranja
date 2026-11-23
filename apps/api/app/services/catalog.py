import json
import logging
import uuid

from app.db import db
from app.security import iso, utcnow
from app.services.rules import demo_records

logger = logging.getLogger(__name__)


def ensure_demo() -> None:
    with db() as conn:
        active = conn.execute("SELECT id FROM datasets WHERE active = 1 LIMIT 1").fetchone()
        if active is not None:
            return
        dataset_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO datasets (id, name, synthetic, active, audit_json, created_at)
            VALUES (?, NULL, 1, 1, NULL, ?)
            """,
            (dataset_id, iso(utcnow())),
        )
        conn.executemany(
            """
            INSERT INTO records (dataset_id, zone, period, violence, service, cases, capacity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (dataset_id, row["zone"], row["period"], row["violence"], row["service"], row["cases"], row["capacity"])
                for row in demo_records()
            ],
        )
    logger.info("Dataset de demostración listo.")


def load_active() -> tuple[list[dict], dict]:
    with db() as conn:
        dataset = conn.execute(
            "SELECT id, name, synthetic, audit_json FROM datasets WHERE active = 1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if dataset is None:
            return [], {"fileName": None, "synthetic": True, "audit": None}
        rows = conn.execute(
            """
            SELECT zone, period, violence, service, cases, capacity
            FROM records WHERE dataset_id = ?
            """,
            (dataset["id"],),
        ).fetchall()
    audit = json.loads(dataset["audit_json"]) if dataset["audit_json"] else None
    source = {"fileName": dataset["name"], "synthetic": bool(dataset["synthetic"]), "audit": audit}
    return [dict(row) for row in rows], source


def replace_active(name: str, records: list[dict], audit: dict) -> None:
    dataset_id = uuid.uuid4().hex
    with db() as conn:
        conn.execute("DELETE FROM records")
        conn.execute("DELETE FROM datasets")
        conn.execute(
            """
            INSERT INTO datasets (id, name, synthetic, active, audit_json, created_at)
            VALUES (?, ?, 0, 1, ?, ?)
            """,
            (dataset_id, name, json.dumps(audit, ensure_ascii=False), iso(utcnow())),
        )
        conn.executemany(
            """
            INSERT INTO records (dataset_id, zone, period, violence, service, cases, capacity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (dataset_id, row["zone"], row["period"], row["violence"], row["service"], row["cases"], row["capacity"])
                for row in records
            ],
        )
