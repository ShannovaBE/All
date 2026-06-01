from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from db import SessionLocal
from models import AuditEvent


logger = logging.getLogger("uvicorn.error")


def _safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    blocked = {"password", "token", "secret", "key", "authorization", "cookie"}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(term in lowered for term in blocked):
            safe[key] = "[REDACTED]"
        else:
            safe[key] = value
    return safe


def write_audit_event(
    *,
    action: str,
    actor_id: str | None = None,
    resource: str | None = None,
    purpose: str | None = None,
    result: str = "SUCCESS",
    ip: str | None = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    payload = {
        "actor_id": actor_id,
        "action": action,
        "resource": resource,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ip": ip,
        "purpose": purpose,
        "result": result,
        "metadata": _safe_metadata(metadata),
    }
    logger.info("audit_event=%s", json.dumps(payload, sort_keys=True, default=str))

    try:
        with SessionLocal() as db:
            db.add(
                AuditEvent(
                    id=str(uuid.uuid4()),
                    actor_id=actor_id,
                    action=action,
                    resource=resource,
                    purpose=purpose,
                    result=result,
                    ip=ip,
                    metadata_json=payload["metadata"],
                )
            )
            db.commit()
    except Exception:
        logger.exception("Failed to persist audit event: %s", action)
