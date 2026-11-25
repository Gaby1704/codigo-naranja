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
            INSERT INTO datasets (id, name, synthetic, active, audit_json, metadata_json, created_at)
            VALUES (?, NULL, 1, 1, NULL, NULL, ?)
            """,
            (dataset_id, iso(utcnow())),
        )
        conn.executemany(
            """
            INSERT INTO records (
              dataset_id, zone, residence_zone, period, event_date, period_complete,
              violence, service, cases, capacity, cases_status, capacity_status, person_id,
              extra_dims_json, extra_metrics_json, extra_metric_statuses_json
            )
            VALUES (?, ?, '', ?, '', 1, ?, ?, ?, ?, 'value', 'value', '', '{}', '{}', '{}')
            """,
            [
                (dataset_id, row["zone"], row["period"], row["violence"], row["service"], row["cases"], row["capacity"])
                for row in demo_records()
            ],
        )
    logger.info("Dataset de demostración listo.")


def load_active() -> tuple[list[dict], dict, dict | None]:
    with db() as conn:
        dataset = conn.execute(
            "SELECT id, name, synthetic, audit_json, metadata_json FROM datasets WHERE active = 1 AND synthetic = 0 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if dataset is None:
            return [], {"fileName": None, "synthetic": False, "audit": None}, None
        rows = conn.execute(
            """
            SELECT zone, residence_zone, period, event_date, period_complete,
                   violence, service, cases, capacity, cases_status, capacity_status, person_id,
                   extra_dims_json, extra_metrics_json, extra_metric_statuses_json
            FROM records WHERE dataset_id = ?
            """,
            (dataset["id"],),
        ).fetchall()
    audit = json.loads(dataset["audit_json"]) if dataset["audit_json"] else None
    metadata = json.loads(dataset["metadata_json"]) if dataset["metadata_json"] else None
    source = {"fileName": dataset["name"], "synthetic": bool(dataset["synthetic"]), "audit": audit}
    parsed_rows: list[dict] = []
    for row in rows:
        item = dict(row)
        item["extra_dims"] = json.loads(item.pop("extra_dims_json", "{}") or "{}")
        item["extra_metrics"] = json.loads(item.pop("extra_metrics_json", "{}") or "{}")
        item["extra_metric_statuses"] = json.loads(item.pop("extra_metric_statuses_json", "{}") or "{}")
        parsed_rows.append(item)
    return parsed_rows, source, metadata


def replace_active(name: str, records: list[dict], audit: dict, metadata: dict | None = None) -> None:
    dataset_id = uuid.uuid4().hex
    with db() as conn:
        conn.execute("DELETE FROM records")
        conn.execute("DELETE FROM datasets")
        conn.execute(
            """
            INSERT INTO datasets (id, name, synthetic, active, audit_json, metadata_json, created_at)
            VALUES (?, ?, 0, 1, ?, ?, ?)
            """,
            (
                dataset_id,
                name,
                json.dumps(audit, ensure_ascii=False),
                json.dumps(metadata, ensure_ascii=False) if metadata is not None else None,
                iso(utcnow()),
            ),
        )
        conn.executemany(
            """
            INSERT INTO records (
              dataset_id, zone, residence_zone, period, event_date, period_complete,
              violence, service, cases, capacity, cases_status, capacity_status, person_id,
              extra_dims_json, extra_metrics_json, extra_metric_statuses_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    dataset_id,
                    row["zone"],
                    row.get("residence_zone", ""),
                    row["period"],
                    row.get("event_date", ""),
                    row.get("period_complete", 1),
                    row["violence"],
                    row["service"],
                    row["cases"],
                    row["capacity"],
                    row.get("cases_status", "value"),
                    row.get("capacity_status", "value"),
                    row.get("person_id", ""),
                    json.dumps(row.get("extra_dims", {}), ensure_ascii=False),
                    json.dumps(row.get("extra_metrics", {}), ensure_ascii=False),
                    json.dumps(row.get("extra_metric_statuses", {}), ensure_ascii=False),
                )
                for row in records
            ],
        )
