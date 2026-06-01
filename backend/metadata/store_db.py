from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from db import SessionLocal
from metadata.config import SCHEMA_VERSION
from metadata.utils import utc_now_iso
from models import DatasetRecord


def _normalize_ask_price(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    try:
        normalized = round(float(value), 2)
    except (TypeError, ValueError):
        return None
    if normalized < 0:
        return None
    return normalized


def _coerce_schema_version(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(float(value))
            except ValueError:
                return 0
    return 0


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _build_record_from_kwargs(
    *,
    file_hash: str,
    filename: str,
    results: Dict[str, Any],
    category: str,
    description: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    owner: Optional[str] = None,
    storage_provider: Optional[str] = None,
    object_key: Optional[str] = None,
    bytes: Optional[int] = None,
    mime: Optional[str] = None,
    ask_price_usd: Optional[float] = None,
    provenance: Optional[Dict[str, Any]] = None,
    compliance_evidence: Optional[Dict[str, Any]] = None,
    access_policy: Optional[Dict[str, Any]] = None,
    restriction_status: str = "active",
) -> Dict[str, Any]:
    ext = filename.split(".")[-1].lower() if "." in filename else None
    normalized_price = _normalize_ask_price(ask_price_usd)
    merged_extra = dict(extra or {})
    if normalized_price is not None:
        merged_extra["ask_price_usd"] = normalized_price

    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": utc_now_iso(),
        "filename": filename,
        "hash": file_hash,
        "category": category,
        "file_type": ext,
        "quality_score": results.get("quality_score"),
        "quality_scores": {"overall": results.get("quality_score")},
        "category_verification": {
            "user_selected": category,
            "auto_detected": results.get("detected_category"),
            "confidence": results.get("category_confidence"),
            "match": None
            if results.get("detected_category") is None
            else (results.get("detected_category") == category),
        },
        "status": results.get("status"),
        "details": results.get("details", []),
        "provenance": provenance or {},
        "compliance_evidence": compliance_evidence or {},
        "access_policy": access_policy or {},
        "restriction_status": restriction_status or "active",
    }

    record["description"] = description or ""
    if normalized_price is not None:
        record["ask_price_usd"] = normalized_price

    if merged_extra:
        record["extra"] = merged_extra
    if owner:
        record["owner"] = owner
    if storage_provider:
        record["storage_provider"] = storage_provider
    if object_key:
        record["object_key"] = object_key
    if bytes is not None:
        record["bytes"] = bytes
    if mime:
        record["mime"] = mime

    return record


def _record_to_model_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    extra = dict(record.get("extra") or {})
    owner = record.get("owner") or extra.get("owner_user_id")
    normalized_price = _normalize_ask_price(record.get("ask_price_usd"))
    if normalized_price is not None:
        extra["ask_price_usd"] = normalized_price

    return {
        "file_hash": record.get("hash") or record.get("file_hash"),
        "schema_version": _coerce_schema_version(record.get("schema_version")),
        "timestamp": _parse_timestamp(record.get("timestamp")),
        "filename": record.get("filename"),
        "category": record.get("category"),
        "file_type": record.get("file_type"),
        "quality_score": record.get("quality_score"),
        "quality_scores": record.get("quality_scores") or {},
        "category_verification": record.get("category_verification") or {},
        "status": record.get("status"),
        "details": record.get("details") or [],
        "description": record.get("description") or "",
        "extra": extra or None,
        "owner": owner,
        "storage_provider": record.get("storage_provider"),
        "object_key": record.get("object_key"),
        "bytes": record.get("bytes"),
        "mime": record.get("mime"),
        "provenance": record.get("provenance") or extra.get("provenance") or {},
        "compliance_evidence": record.get("compliance_evidence") or extra.get("compliance_evidence") or {},
        "access_policy": record.get("access_policy") or extra.get("access_policy") or {},
        "restriction_status": record.get("restriction_status") or extra.get("restriction_status") or "active",
    }


def _model_to_record(model: DatasetRecord) -> Dict[str, Any]:
    description = model.description or ""
    timestamp = model.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    extra = model.extra or {}
    ask_price_usd = _normalize_ask_price(extra.get("ask_price_usd"))

    record = {
        "schema_version": model.schema_version,
        "timestamp": timestamp,
        "filename": model.filename,
        "hash": model.file_hash,
        "category": model.category,
        "file_type": model.file_type,
        "quality_score": model.quality_score,
        "quality_scores": model.quality_scores or {},
        "category_verification": model.category_verification or {},
        "status": model.status,
        "details": model.details or [],
        "description": description,
        "extra": extra,
        "owner": model.owner,
        "storage_provider": model.storage_provider,
        "object_key": model.object_key,
        "bytes": model.bytes,
        "mime": model.mime,
        "provenance": model.provenance or {},
        "compliance_evidence": model.compliance_evidence or {},
        "access_policy": model.access_policy or {},
        "restriction_status": model.restriction_status or "active",
    }
    if ask_price_usd is not None:
        record["ask_price_usd"] = ask_price_usd
    return record


def save_record(record: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    if record is None:
        record = _build_record_from_kwargs(**kwargs)

    data = _record_to_model_fields(record)

    with SessionLocal() as db:
        obj = DatasetRecord(**data)
        merged = db.merge(obj)
        db.commit()
        db.refresh(merged)
        return _model_to_record(merged)


def load_record(file_hash: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        result = db.execute(
            select(DatasetRecord).where(DatasetRecord.file_hash == file_hash)
        ).scalar_one_or_none()
        if result is None:
            return None
        return _model_to_record(result)

def get_record(file_hash: str) -> Optional[Dict[str, Any]]:
    return load_record(file_hash)


def update_description(file_hash: str, description: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        result = db.execute(
            select(DatasetRecord).where(DatasetRecord.file_hash == file_hash)
        ).scalar_one_or_none()
        if result is None:
            return None
        result.description = description or ""
        db.commit()
        db.refresh(result)
        return _model_to_record(result)


def update_record_controls(
    file_hash: str,
    *,
    extra: Optional[Dict[str, Any]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    compliance_evidence: Optional[Dict[str, Any]] = None,
    access_policy: Optional[Dict[str, Any]] = None,
    restriction_status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        result = db.execute(
            select(DatasetRecord).where(DatasetRecord.file_hash == file_hash)
        ).scalar_one_or_none()
        if result is None:
            return None
        if extra is not None:
            current_extra = dict(result.extra or {})
            current_extra.update(extra)
            result.extra = current_extra
        if provenance is not None:
            current_provenance = dict(result.provenance or {})
            current_provenance.update(provenance)
            result.provenance = current_provenance
        if compliance_evidence is not None:
            current_evidence = dict(result.compliance_evidence or {})
            current_evidence.update(compliance_evidence)
            result.compliance_evidence = current_evidence
        if access_policy is not None:
            current_policy = dict(result.access_policy or {})
            current_policy.update(access_policy)
            result.access_policy = current_policy
        if restriction_status is not None:
            result.restriction_status = restriction_status
        db.commit()
        db.refresh(result)
        return _model_to_record(result)

def delete_record(file_hash: str) -> bool:
    with SessionLocal() as db:
        result = db.execute(
            select(DatasetRecord).where(DatasetRecord.file_hash == file_hash)
        ).scalar_one_or_none()
        if result is None:
            return False
        db.delete(result)
        db.commit()
        return True


def list_records(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        stmt = select(DatasetRecord).order_by(DatasetRecord.timestamp.desc())
        if limit:
            stmt = stmt.limit(limit)
        rows = db.execute(stmt).scalars().all()
        return [_model_to_record(row) for row in rows]
