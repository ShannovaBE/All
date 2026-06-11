from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from metadata import list_retention_due_records, update_record_controls


DEFAULT_RETENTION_DAYS = int(os.getenv("DEFAULT_RETENTION_DAYS", "365"))
RETENTION_DELETE_OBJECTS = os.getenv("RETENTION_DELETE_OBJECTS", "false").strip().lower() == "true"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_retention_policy(*, now: Optional[datetime] = None, days: Optional[int] = None) -> tuple[Dict[str, Any], str]:
    issued_at = now or utc_now()
    retention_days = int(days if days is not None else DEFAULT_RETENTION_DAYS)
    expires_at = issued_at + timedelta(days=retention_days)
    policy = {
        "basis": "standard_marketplace_retention",
        "retention_days": retention_days,
        "issued_at": iso_utc(issued_at),
        "expiry_action": "restrict_metadata_and_disable_download",
        "object_deletion_enabled": RETENTION_DELETE_OBJECTS,
    }
    return policy, iso_utc(expires_at)


def run_retention_sweep(
    *,
    now: Optional[datetime] = None,
    dry_run: bool = True,
    limit: Optional[int] = None,
    delete_objects: Optional[bool] = None,
) -> Dict[str, Any]:
    sweep_time = now or utc_now()
    should_delete_objects = RETENTION_DELETE_OBJECTS if delete_objects is None else bool(delete_objects)
    due_records = list_retention_due_records(now=sweep_time, limit=limit)
    items = []

    for record in due_records:
        file_hash = record.get("hash")
        object_key = record.get("object_key")
        item = {
            "hash": file_hash,
            "filename": record.get("filename"),
            "retention_expires_at": record.get("retention_expires_at"),
            "dry_run": dry_run,
            "action": "would_restrict" if dry_run else "restricted",
            "object_deleted": False,
        }

        if not dry_run and file_hash:
            evidence = {
                "retention": {
                    "action": "retention_expired",
                    "processed_at": iso_utc(sweep_time),
                    "retention_expires_at": record.get("retention_expires_at"),
                    "object_deletion_enabled": should_delete_objects,
                }
            }
            update_record_controls(
                file_hash,
                restriction_status="retention_expired",
                compliance_evidence=evidence,
                extra={
                    "restriction_status": "retention_expired",
                    "retention_last_action_at": iso_utc(sweep_time),
                },
            )
            if should_delete_objects and object_key:
                from gcs import delete_object

                delete_object(key=object_key)
                item["object_deleted"] = True

        items.append(item)

    return {
        "ok": True,
        "dry_run": dry_run,
        "processed_at": iso_utc(sweep_time),
        "due_count": len(items),
        "items": items,
    }
