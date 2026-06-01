# backend/main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import csv
import io
import os
import hashlib
import tempfile
import logging
import re
from mimetypes import guess_type
from pathlib import Path

from utils.run_checker import run_data_checker
from utils.tagger import run_tagger  # NEW
from metadata import save_record  # ✅ new import
from metadata import list_records, load_record, update_description, update_record_controls, delete_record
from utils.fake_type_checker import fake_type_checker, match_selected_type
from typing import Optional
from gcs import put_object, generate_presigned_url, delete_object

from pydantic import BaseModel
from db import engine
from models import Base
from users import (
    ALLOWED_PLANS,
    ALLOWED_KYB_STATUSES,
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    set_user_restricted,
    update_user_kyb_status,
    update_user_plan,
    verify_user_password,
)
from auth.admin import is_admin
from reviews.settings import get_review_visibility_months, visibility_cutoff
from reviews.store_db import (
    delete_review as delete_review_db,
    get_lifetime_stats,
    get_review_by_user_id,
    get_visible_stats,
    list_reviews_for_admin,
    list_visible_reviews,
    set_review_status,
    upsert_user_review,
)
from reviews.validation import (
    MAX_REVIEW_LEN,
    MIN_REVIEW_LEN,
    validate_review_payload,
)
from audit import write_audit_event



app = FastAPI()

logger = logging.getLogger("uvicorn.error")


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _audit(
    request: Request | None,
    *,
    action: str,
    actor_id: str | None = None,
    resource: str | None = None,
    purpose: str | None = None,
    result: str = "SUCCESS",
    metadata: dict | None = None,
) -> None:
    write_audit_event(
        actor_id=actor_id,
        action=action,
        resource=resource,
        purpose=purpose,
        result=result,
        ip=_client_ip(request),
        metadata=metadata,
    )


@app.on_event("startup")
def _ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def _warm_upload_pipeline() -> None:
    warmup_path = None
    try:
        from pipeline import process_file_pipeline

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as warmup_file:
            warmup_file.write(
                "timestamp,value,source\n"
                "2026-01-01T00:00:00Z,1,startup-warmup\n"
                "2026-01-01T00:01:00Z,2,startup-warmup\n"
            )
            warmup_path = warmup_file.name

        process_file_pipeline(warmup_path, "startup-warmup.csv")
        logger.info("Upload pipeline warmed during startup")
    except Exception:
        logger.exception("Failed to warm upload pipeline during startup")
    finally:
        if warmup_path and os.path.exists(warmup_path):
            os.remove(warmup_path)


def _safe_upload_filename(name: str) -> str:
    # Avoid directory traversal / weird client-supplied paths.
    return os.path.basename(name or "upload")


def _safe_tmp_suffix(filename: str) -> str:
    suffix = Path(filename).suffix
    if not suffix:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9.]", "", suffix)
    if not cleaned.startswith("."):
        return ""
    # Keep temp suffixes short to avoid OS/path issues.
    return cleaned[:16]


def _best_mime_type(*, filename: str, client_content_type: str | None) -> tuple[str, str]:
    """
    Choose a MIME type for storage/metadata.

    We prefer the client-provided content type when it's specific; otherwise guess from filename.
    Returns: (mime, source) where source is one of: client | filename | default
    """
    if client_content_type and client_content_type not in ("application/octet-stream", "binary/octet-stream"):
        return client_content_type, "client"

    guessed, _ = guess_type(filename)
    if guessed:
        return guessed, "filename"

    return (client_content_type or "application/octet-stream"), "default"


def _parse_ask_price(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    try:
        price = round(float(value), 2)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ask price must be a valid number")
    if price < 0:
        raise HTTPException(status_code=400, detail="Ask price must be zero or greater")
    return price


PLAN_RANK = {"free": 0, "basic": 1, "business": 2, "enterprise": 3}
SENSITIVITY_POLICY = {
    "public": {"min_plan": "free", "kyb_required": False},
    "internal": {"min_plan": "basic", "kyb_required": False},
    "confidential": {"min_plan": "basic", "kyb_required": False},
    "sensitive": {"min_plan": "business", "kyb_required": True},
    "special_category": {"min_plan": "enterprise", "kyb_required": True},
}
CATEGORY_SENSITIVITY = {
    "medical": "special_category",
    "finance": "confidential",
    "retail": "internal",
    "text": "internal",
    "images": "internal",
    "geospatial": "confidential",
    "general": "internal",
}


def _public_user_payload(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "plan": user.get("plan", "free"),
        "kyb_status": user.get("kyb_status", "pending"),
        "restricted": bool(user.get("restricted", False)),
    }


def _dataset_owner_id(record: dict) -> str | None:
    extra = record.get("extra", {}) or {}
    return record.get("owner") or extra.get("owner_user_id")


def _normalise_sensitivity(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in SENSITIVITY_POLICY else "internal"


def _build_access_policy(*, category: str, pii_report: dict | None) -> dict:
    sensitivity = CATEGORY_SENSITIVITY.get((category or "").strip().lower(), "internal")
    if pii_report and int(pii_report.get("redacted_cells") or 0) > 0:
        sensitivity = "sensitive" if sensitivity != "special_category" else sensitivity
    rule = SENSITIVITY_POLICY[sensitivity]
    return {
        "sensitivity": sensitivity,
        "min_plan": rule["min_plan"],
        "kyb_required": rule["kyb_required"],
        "permitted_uses": ["analytics", "research", "product_development"],
        "prohibited_uses": ["re_identification", "secondary_sale_without_consent", "individual_profiling"],
    }


def _build_provenance(
    *,
    user_id: str,
    safe_filename: str,
    file_hash: str,
    content_type: str,
    mime_source: str,
    object_key: str,
    pipeline_results: dict,
) -> dict:
    return {
        "source": "seller_upload",
        "uploader_user_id": user_id,
        "original_filename": safe_filename,
        "file_hash": file_hash,
        "storage_provider": "gcs",
        "object_key": object_key,
        "mime": content_type,
        "mime_source": mime_source,
        "pipeline_version": "fast-compliance-pipeline-v1",
        "transformations": [
            "sha256_hash",
            "pii_scan_and_redaction",
            "category_prediction",
            "quality_scoring",
            "metadata_persistence",
        ],
        "stats": pipeline_results.get("stats", {}),
    }


def _build_compliance_evidence(*, category: str, type_result: dict, type_match: dict, pipeline_results: dict, access_policy: dict) -> dict:
    return {
        "pii_report": pipeline_results.get("pii_report", {}),
        "category_verification": {
            "user_selected": category,
            "auto_detected": type_result.get("predicted_type"),
            "confidence": type_result.get("confidence"),
            "match": type_match.get("match"),
        },
        "quality": {
            "score": pipeline_results.get("quality_score"),
            "best_use_case": pipeline_results.get("best_use_case"),
            "details": pipeline_results.get("details", []),
        },
        "access_policy": access_policy,
        "listing_decision": "needs_review"
        if access_policy.get("sensitivity") in {"sensitive", "special_category"}
        else "listable",
    }


def _require_access_to_dataset(
    *,
    record: dict,
    requester_id: str | None,
    requester_username: str | None = None,
    purpose: str = "buyer_download",
) -> dict:
    if record.get("restriction_status") != "active":
        raise HTTPException(status_code=423, detail="Dataset is restricted")

    owner_id = _dataset_owner_id(record)
    if requester_id and requester_id == owner_id:
        user = get_user_by_id(requester_id)
        if not user:
            raise HTTPException(status_code=403, detail="Not authorized")
        return user

    if not requester_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    user = get_user_by_id(requester_id)
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    if user.get("restricted"):
        raise HTTPException(status_code=423, detail="Account is restricted")
    if is_admin(user_id=user["id"], username=requester_username or user.get("username")):
        return user

    policy = record.get("access_policy") or (record.get("extra") or {}).get("access_policy") or {}
    sensitivity = _normalise_sensitivity(policy.get("sensitivity"))
    min_plan = policy.get("min_plan") or SENSITIVITY_POLICY[sensitivity]["min_plan"]
    user_plan = user.get("plan", "free")
    if PLAN_RANK.get(user_plan, 0) < PLAN_RANK.get(min_plan, 0):
        raise HTTPException(status_code=403, detail="Licence tier does not permit this dataset")
    if policy.get("kyb_required", SENSITIVITY_POLICY[sensitivity]["kyb_required"]) and user.get("kyb_status") != "verified":
        raise HTTPException(status_code=403, detail="KYB verification required")

    permitted_uses = set(policy.get("permitted_uses") or [])
    if permitted_uses and purpose not in permitted_uses and purpose not in {"buyer_download", "buyer_preview"}:
        raise HTTPException(status_code=403, detail="Purpose is not permitted for this dataset")
    return user

# Allow frontend connection (adjust later for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://shannova-frontend-604156427652.europe-west1.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Base upload directory (we'll create subfolders per category)
# 🔹 Allowed category bins
ALLOWED_CATEGORIES = [
    "medical",
    "finance",
    "retail",
    "text",
    "images",
    "geospatial",
    "general",
]

class RegisterRequest(BaseModel):
  username: str
  email: str
  password: str
  plan: str = "free"


class LoginRequest(BaseModel):
  username: str
  password: str


class DescriptionUpdate(BaseModel):
  description: str


class PlanUpdate(BaseModel):
  plan: str


class KybStatusUpdate(BaseModel):
  status: str


class RestrictionUpdate(BaseModel):
  restricted: bool = True
  reason: str = "data_subject_restriction"


class ReviewUpsertRequest(BaseModel):
  review_text: str
  rating: int


class ReviewModerationRequest(BaseModel):
  status: str


# backend/main.py

@app.post("/upload")
async def upload_file(
    request: Request = None,
    file: UploadFile = File(...),
    category: str = Form("general"),
    user_id: str | None = Form(None),
    description: str | None = Form(None),
    ask_price_usd: str | None = Form(None),
):
    """
    Receive file, hash it, run quality checker, store metadata, and return results.
    Includes fake category prediction + confidence.
    """

    # 0?????? Validate category
    if category not in ALLOWED_CATEGORIES:
        _audit(
            request,
            action="UPLOAD_DATASET",
            actor_id=user_id,
            purpose="seller_upload",
            result="DENIED",
            metadata={"reason": "invalid_category", "category": category},
        )
        raise HTTPException(status_code=400, detail="Invalid category")
    if not user_id:
        _audit(
            request,
            action="UPLOAD_DATASET",
            purpose="seller_upload",
            result="DENIED",
            metadata={"reason": "missing_user_id", "category": category},
        )
        raise HTTPException(status_code=403, detail="Verified seller account required")
    uploader = get_user_by_id(user_id)
    if not uploader or uploader.get("restricted") or uploader.get("kyb_status") != "verified":
        _audit(
            request,
            action="UPLOAD_DATASET",
            actor_id=user_id,
            purpose="seller_upload",
            result="DENIED",
            metadata={
                "reason": "seller_kyb_required",
                "kyb_status": uploader.get("kyb_status") if uploader else None,
                "restricted": bool(uploader.get("restricted")) if uploader else None,
            },
        )
        raise HTTPException(status_code=403, detail="Verified seller account required")
    parsed_ask_price = _parse_ask_price(ask_price_usd)

    contents = await file.read()
    if not contents:
        _audit(
            request,
            action="UPLOAD_DATASET",
            actor_id=user_id,
            purpose="seller_upload",
            result="DENIED",
            metadata={"reason": "empty_file", "filename": safe_filename if "safe_filename" in locals() else None},
        )
        raise HTTPException(status_code=400, detail="File is empty")

    tmp_path = None
    safe_filename = _safe_upload_filename(file.filename)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=_safe_tmp_suffix(safe_filename)) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name

        # Generate SHA-256 hash early
        file_hash = hashlib.sha256(contents).hexdigest()

        # Run real AI Pipeline (Gamma, Beta, Alpha)
        from pipeline import process_file_pipeline
        pipeline_results = process_file_pipeline(str(tmp_path), safe_filename)
        
        type_result = {
            "predicted_type": pipeline_results["predicted_category"],
            "confidence": pipeline_results["confidence"]
        }

        type_match = match_selected_type(
            user_selected=category,
            predicted=type_result["predicted_type"],
            confidence=type_result["confidence"],
        )

        results = {
            "quality_score": pipeline_results["quality_score"],
            "status": "passed" if pipeline_results["quality_score"] >= 80 else "needs_review",
            "details": pipeline_results["details"],
            "quality_scores": {"overall": pipeline_results["quality_score"]}
        }
        quality_score = results["quality_score"]

        # If Gamma scrubbed PII, update the contents variable so the safe version is uploaded to GCS
        with open(tmp_path, "rb") as f:
            contents = f.read()

        tags = pipeline_results.get("generated_tags", [])
        
        # We append the best use case to the description if they didn't provide one
        if not description:
            description = pipeline_results.get("best_use_case", "")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    file_ext = Path(safe_filename).suffix.lstrip(".").lower() or None
    object_key = f"datasets/{file_hash}/{safe_filename}"
    content_type, mime_source = _best_mime_type(
        filename=safe_filename,
        client_content_type=file.content_type,
    )
    access_policy = _build_access_policy(category=category, pii_report=pipeline_results.get("pii_report", {}))
    provenance = _build_provenance(
        user_id=user_id,
        safe_filename=safe_filename,
        file_hash=file_hash,
        content_type=content_type,
        mime_source=mime_source,
        object_key=object_key,
        pipeline_results=pipeline_results,
    )
    compliance_evidence = _build_compliance_evidence(
        category=category,
        type_result=type_result,
        type_match=type_match,
        pipeline_results=pipeline_results,
        access_policy=access_policy,
    )
    try:
        put_object(
            key=object_key,
            body=contents,
            content_type=content_type,
        )
    except Exception:
        logger.exception("Failed to upload object to GCS: %s", object_key)
        _audit(
            request,
            action="UPLOAD_DATASET",
            actor_id=user_id,
            resource=file_hash,
            purpose="seller_upload",
            result="FAILURE",
            metadata={"stage": "storage", "filename": safe_filename},
        )
        raise HTTPException(status_code=500, detail="Failed to upload dataset to storage")

    # 5?????? Save metadata
    try:
        save_record(
            file_hash=file_hash,
            filename=safe_filename,
            category=category,
            description=description,
            ask_price_usd=parsed_ask_price,
            owner=user_id,
            storage_provider="gcs",
            object_key=object_key,
            bytes=len(contents),
            mime=content_type,
            provenance=provenance,
            compliance_evidence=compliance_evidence,
            access_policy=access_policy,
            restriction_status="active",
            results={
                **results,
                "detected_category": type_result["predicted_type"],
                "category_confidence": type_result["confidence"],
            },
            extra={
                "user_category": category,
                "predicted_category": type_result["predicted_type"],
                "prediction_confidence": type_result["confidence"],
                "category_match": type_match["match"],
                "client_content_type": file.content_type,
                "mime_source": mime_source,

                # ???? NEW: ownership + tagging info
                "owner_user_id": user_id,
                "tag_hash": "pipeline-tags",
                "tags": tags,
                "tagger_raw": {},   # keep full tagger payload for now
                "description": description,
                "ask_price_usd": parsed_ask_price,
                "stats": pipeline_results.get("stats", {}),
                "data_sample": pipeline_results.get("data_sample", []),
                "pii_report": pipeline_results.get("pii_report", {}),
                "provenance": provenance,
                "compliance_evidence": compliance_evidence,
                "access_policy": access_policy,
                "restriction_status": "active",
            },
        )
    except Exception:
        logger.exception("Failed to save metadata for %s", file_hash)
        try:
            delete_object(key=object_key)
        except Exception:
            logger.exception("Failed to clean up GCS object after metadata error: %s", object_key)
        _audit(
            request,
            action="UPLOAD_DATASET",
            actor_id=user_id,
            resource=file_hash,
            purpose="seller_upload",
            result="FAILURE",
            metadata={"stage": "metadata", "filename": safe_filename},
        )
        raise HTTPException(status_code=500, detail="Failed to save dataset metadata")


    _audit(
        request,
        action="UPLOAD_DATASET",
        actor_id=user_id,
        resource=file_hash,
        purpose="seller_upload",
        result="SUCCESS",
        metadata={
            "filename": safe_filename,
            "category": category,
            "predicted_category": type_result["predicted_type"],
            "quality_score": quality_score,
            "bytes": len(contents),
            "pii_report": pipeline_results.get("pii_report", {}),
            "access_policy": access_policy,
        },
    )

    return {
        "filename": safe_filename,
        "hash": file_hash,
        "file_type": file_ext,
        "mime": content_type,
        "mime_source": mime_source,
        "user_category": category,
        "ask_price_usd": parsed_ask_price,
        "predicted_category": type_result["predicted_type"],
        "confidence": type_result["confidence"],
        "category_match": type_match["match"],
        "quality_score": quality_score,
        "status": results.get("status"),
        "details": results.get("details"),

        # NEW
        "user_id": user_id,
        "tags": tags,
        "tag_hash": "pipeline-tags",
        "stats": pipeline_results.get("stats", {}),
        "pii_report": pipeline_results.get("pii_report", {}),
        "access_policy": access_policy,
        "provenance": provenance,
        "compliance_evidence": compliance_evidence,
    }


# this will be replaced when we move to a data base
@app.get("/metadata")
def get_all_metadata(
    request: Request = None,
    limit: int | None = None,
    owner_id: Optional[str] = None,   # 🔹 NEW
):
    """
    List saved metadata records (newest first).
    Optional: ?limit=50
    Optional: ?owner_id=<user_id> to filter by owner.
    """
    records = list_records(limit=limit)

    # 🔹 If an owner_id is specified, filter by extra.owner_user_id
    if owner_id is not None:
        filtered = []
        for rec in records:
            extra = rec.get("extra", {}) or {}
            if extra.get("owner_user_id") == owner_id:
                filtered.append(rec)
        records = filtered

    _audit(
        request,
        action="LIST_DATASETS",
        actor_id=owner_id,
        resource="dataset_records",
        purpose="metadata_browse",
        result="SUCCESS",
        metadata={"count": len(records), "owner_filter": owner_id is not None},
    )
    return {"count": len(records), "items": records}


@app.get("/metadata/{file_hash}")
def get_metadata_by_hash(file_hash: str, request: Request = None):
    """
    Fetch one metadata record by its hash.
    """
    rec = load_record(file_hash)
    if rec is None:
        _audit(
            request,
            action="READ_DATASET_METADATA",
            resource=file_hash,
            purpose="metadata_lookup",
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Record not found")
    _audit(
        request,
        action="READ_DATASET_METADATA",
        resource=file_hash,
        purpose="metadata_lookup",
        result="SUCCESS",
    )
    return rec

@app.get("/datasets/{file_hash}/download")
def download_dataset(
    file_hash: str,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
    requester_username: str | None = Header(default=None, alias="X-Username"),
    purpose: str = Header(default="buyer_download", alias="X-Purpose"),
):
    record = load_record(file_hash)
    if record is None:
        _audit(
            request,
            action="DOWNLOAD_DATASET",
            resource=file_hash,
            purpose=purpose,
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Record not found")
    try:
        requester = _require_access_to_dataset(
            record=record,
            requester_id=requester_id,
            requester_username=requester_username,
            purpose=purpose,
        )
    except HTTPException as exc:
        _audit(
            request,
            action="DOWNLOAD_DATASET",
            actor_id=requester_id,
            resource=file_hash,
            purpose=purpose,
            result="DENIED",
            metadata={"reason": exc.detail},
        )
        raise

    object_key = record.get("object_key")
    if not object_key:
        _audit(
            request,
            action="DOWNLOAD_DATASET",
            resource=file_hash,
            purpose=purpose,
            result="NOT_FOUND",
            metadata={"reason": "missing_object_key"},
        )
        raise HTTPException(status_code=404, detail="File not found")

    expires_in = 600
    filename = record.get("filename") or f"{file_hash}"
    mime = record.get("mime") or "application/octet-stream"
    url = generate_presigned_url(
        key=object_key,
        filename=filename,
        mime=mime,
        expires_in=expires_in,
    )
    if not url:
        logger.error("Failed to generate download URL for %s", object_key)
        _audit(
            request,
            action="DOWNLOAD_DATASET",
            resource=file_hash,
            purpose=purpose,
            result="FAILURE",
            metadata={"stage": "signed_url"},
        )
        raise HTTPException(status_code=500, detail="Failed to generate download link")
    _audit(
        request,
        action="DOWNLOAD_DATASET",
        actor_id=requester["id"],
        resource=file_hash,
        purpose=purpose,
        result="SUCCESS",
        metadata={"expires_in": expires_in, "mime": mime},
    )
    return {"url": url, "expires_in": expires_in}

@app.delete("/datasets/{file_hash}")
def delete_dataset(
    file_hash: str,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not requester_id:
        _audit(
            request,
            action="DELETE_DATASET",
            resource=file_hash,
            purpose="seller_delete",
            result="DENIED",
            metadata={"reason": "missing_requester"},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        record = load_record(file_hash)
    except Exception:
        _audit(
            request,
            action="DELETE_DATASET",
            actor_id=requester_id,
            resource=file_hash,
            purpose="seller_delete",
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Record not found")
    if record is None:
        _audit(
            request,
            action="DELETE_DATASET",
            actor_id=requester_id,
            resource=file_hash,
            purpose="seller_delete",
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Record not found")

    extra = record.get("extra", {}) or {}
    owner_id = extra.get("owner_user_id")
    if not owner_id or requester_id != owner_id:
        _audit(
            request,
            action="DELETE_DATASET",
            actor_id=requester_id,
            resource=file_hash,
            purpose="seller_delete",
            result="DENIED",
            metadata={"owner_id": owner_id},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    object_key = record.get("object_key") or extra.get("object_key")
    if object_key:
        try:
            delete_object(key=object_key)
        except Exception as exc:
            logger.exception("Failed to delete GCS object %s", object_key)
            _audit(
                request,
                action="DELETE_DATASET",
                actor_id=requester_id,
                resource=file_hash,
                purpose="seller_delete",
                result="FAILURE",
                metadata={"stage": "storage"},
            )
            raise HTTPException(status_code=500, detail="Failed to delete dataset file")

    if not delete_record(file_hash):
        _audit(
            request,
            action="DELETE_DATASET",
            actor_id=requester_id,
            resource=file_hash,
            purpose="seller_delete",
            result="NOT_FOUND",
            metadata={"stage": "metadata"},
        )
        raise HTTPException(status_code=404, detail="Record not found")

    _audit(
        request,
        action="DELETE_DATASET",
        actor_id=requester_id,
        resource=file_hash,
        purpose="seller_delete",
        result="SUCCESS",
    )
    return {"ok": True}

@app.patch("/datasets/{file_hash}/description")
def update_description_endpoint(
    file_hash: str,
    payload: DescriptionUpdate,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
    requester_username: str | None = Header(default=None, alias="X-Username"),
):
    desc = payload.description
    if not isinstance(desc, str):
        _audit(request, action="UPDATE_DATASET_DESCRIPTION", resource=file_hash, result="DENIED", metadata={"reason": "invalid_description_type"})
        raise HTTPException(status_code=400, detail="Description must be a string")
    if len(desc) > 1000:
        _audit(request, action="UPDATE_DATASET_DESCRIPTION", resource=file_hash, result="DENIED", metadata={"reason": "description_too_long"})
        raise HTTPException(status_code=400, detail="Description too long")

    record = load_record(file_hash)
    if record is None:
        _audit(request, action="UPDATE_DATASET_DESCRIPTION", resource=file_hash, result="NOT_FOUND")
        raise HTTPException(status_code=404, detail="Record not found")

    resolved_requester_id = requester_id
    if not resolved_requester_id and requester_username:
        user = get_user_by_username(requester_username)
        if not user:
            _audit(request, action="UPDATE_DATASET_DESCRIPTION", resource=file_hash, result="DENIED", metadata={"reason": "unknown_username"})
            raise HTTPException(status_code=403, detail="Not authorized")
        resolved_requester_id = user.get("id")

    if not resolved_requester_id:
        _audit(request, action="UPDATE_DATASET_DESCRIPTION", resource=file_hash, result="DENIED", metadata={"reason": "missing_requester"})
        raise HTTPException(status_code=403, detail="Not authorized")

    extra = record.get("extra", {}) or {}
    owner_id = extra.get("owner_user_id")
    if not owner_id or owner_id != resolved_requester_id:
        _audit(
            request,
            action="UPDATE_DATASET_DESCRIPTION",
            actor_id=resolved_requester_id,
            resource=file_hash,
            purpose="seller_listing_update",
            result="DENIED",
            metadata={"owner_id": owner_id},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    updated = update_description(file_hash, desc)
    if updated is None:
        _audit(request, action="UPDATE_DATASET_DESCRIPTION", actor_id=resolved_requester_id, resource=file_hash, result="NOT_FOUND")
        raise HTTPException(status_code=404, detail="Record not found")
    updated.pop("hash", None)
    _audit(
        request,
        action="UPDATE_DATASET_DESCRIPTION",
        actor_id=resolved_requester_id,
        resource=file_hash,
        purpose="seller_listing_update",
        result="SUCCESS",
    )
    return updated

@app.post("/register")
def register_user(payload: RegisterRequest, request: Request = None):
    try:
        user = create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            plan=payload.plan,
        )
        _audit(
            request,
            action="REGISTER_USER",
            actor_id=user["id"],
            resource=user["id"],
            purpose="account_registration",
            result="SUCCESS",
            metadata={"username": user["username"], "plan": user.get("plan", "free")},
        )
        return {"ok": True, "user": user}
    except ValueError as e:
        _audit(
            request,
            action="REGISTER_USER",
            purpose="account_registration",
            result="DENIED",
            metadata={"username": payload.username, "reason": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login_user(payload: LoginRequest, request: Request = None):
    """
    Simple login: verifies username + password.
    For now, returns ok + user info if correct.
    Later we can add real tokens/sessions.
    """
    user = get_user_by_username(payload.username)
    if not user:
        _audit(
            request,
            action="LOGIN_USER",
            purpose="account_login",
            result="DENIED",
            metadata={"username": payload.username, "reason": "unknown_user"},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_user_password(payload.username, payload.password):
        _audit(
            request,
            action="LOGIN_USER",
            actor_id=user.get("id"),
            resource=user.get("id"),
            purpose="account_login",
            result="DENIED",
            metadata={"username": payload.username, "reason": "bad_password"},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    _audit(
        request,
        action="LOGIN_USER",
        actor_id=user["id"],
        resource=user["id"],
        purpose="account_login",
        result="SUCCESS",
        metadata={"username": user["username"]},
    )
    return {
        "ok": True,
        "user": _public_user_payload(user),
    }


def _require_user(requester_id: str | None) -> dict:
    if not requester_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = get_user_by_id(requester_id)
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user


def _records_owned_by(user_id: str) -> list[dict]:
    return [record for record in list_records() if _dataset_owner_id(record) == user_id]


def _review_payload_for_user(user_id: str) -> dict | None:
    review = get_review_by_user_id(user_id)
    if not review:
        return None
    return {
        "id": review.id,
        "review_text": review.review_text,
        "rating": review.rating,
        "status": review.status,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


def _build_user_export(user_id: str) -> dict:
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user": _public_user_payload(user),
        "datasets": _records_owned_by(user_id),
        "review": _review_payload_for_user(user_id),
    }


def _user_export_as_csv(payload: dict) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "section",
            "id",
            "filename",
            "category",
            "status",
            "restriction_status",
            "plan",
            "kyb_status",
        ],
    )
    writer.writeheader()
    user = payload["user"]
    writer.writerow(
        {
            "section": "user",
            "id": user["id"],
            "plan": user.get("plan"),
            "kyb_status": user.get("kyb_status"),
            "restriction_status": "restricted" if user.get("restricted") else "active",
        }
    )
    for record in payload["datasets"]:
        writer.writerow(
            {
                "section": "dataset",
                "id": record.get("hash"),
                "filename": record.get("filename"),
                "category": record.get("category"),
                "status": record.get("status"),
                "restriction_status": record.get("restriction_status"),
            }
        )
    review = payload.get("review")
    if review:
        writer.writerow(
            {
                "section": "review",
                "id": review.get("id"),
                "status": review.get("status"),
            }
        )
    return output.getvalue()


@app.get("/me")
def get_me(
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user = _require_user(requester_id)
    _audit(
        request,
        action="READ_ACCOUNT",
        actor_id=user["id"],
        resource=user["id"],
        purpose="account_self_service",
        result="SUCCESS",
    )
    return {
        "ok": True,
        "user": _public_user_payload(user),
        "is_admin": is_admin(user_id=user["id"], username=user.get("username")),
        "review_visibility_months": get_review_visibility_months(),
    }


@app.get("/users/{user_id}/export")
def export_user_data(
    user_id: str,
    format: str = "json",
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not requester_id or requester_id != user_id:
        _audit(
            request,
            action="EXPORT_USER_DATA",
            actor_id=requester_id,
            resource=user_id,
            purpose="data_subject_access_request",
            result="DENIED",
            metadata={"reason": "not_owner"},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    payload = _build_user_export(user_id)
    requested_format = (format or "json").strip().lower()
    _audit(
        request,
        action="EXPORT_USER_DATA",
        actor_id=user_id,
        resource=user_id,
        purpose="data_subject_access_request",
        result="SUCCESS",
        metadata={"format": requested_format, "dataset_count": len(payload["datasets"])},
    )
    if requested_format == "json":
        return {"ok": True, "format": "json", "data": payload}
    if requested_format == "csv":
        return PlainTextResponse(
            _user_export_as_csv(payload),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="shannova-user-{user_id}-export.csv"'},
        )
    raise HTTPException(status_code=400, detail="Unsupported export format")


@app.patch("/users/{user_id}/restrict")
def restrict_user_processing(
    user_id: str,
    payload: RestrictionUpdate,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not requester_id or requester_id != user_id:
        _audit(
            request,
            action="RESTRICT_USER_PROCESSING",
            actor_id=requester_id,
            resource=user_id,
            purpose="data_subject_restriction_request",
            result="DENIED",
            metadata={"reason": "not_owner"},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        user = set_user_restricted(user_id, payload.restricted)
    except ValueError as e:
        _audit(
            request,
            action="RESTRICT_USER_PROCESSING",
            actor_id=user_id,
            resource=user_id,
            purpose="data_subject_restriction_request",
            result="NOT_FOUND",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))

    records = _records_owned_by(user_id)
    restriction_status = "restricted" if payload.restricted else "active"
    for record in records:
        update_record_controls(
            record["hash"],
            restriction_status=restriction_status,
            compliance_evidence={
                "restriction_request": {
                    "restricted": payload.restricted,
                    "reason": payload.reason,
                }
            },
            extra={"restriction_status": restriction_status},
        )

    _audit(
        request,
        action="RESTRICT_USER_PROCESSING",
        actor_id=user_id,
        resource=user_id,
        purpose="data_subject_restriction_request",
        result="SUCCESS",
        metadata={"restricted": payload.restricted, "dataset_count": len(records), "reason": payload.reason},
    )
    return {"ok": True, "user": user, "dataset_count": len(records), "restriction_status": restriction_status}


@app.get("/reviews/public")
def get_public_reviews(limit: int = 50, request: Request = None):
    limit = max(1, min(200, int(limit)))
    avg, total = get_visible_stats()
    models = list_visible_reviews(limit=limit)
    items = []
    for m in models:
        user = get_user_by_id(m.user_id)
        items.append(
            {
                "id": m.id,
                "review_text": m.review_text,
                "rating": m.rating,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "reviewer_name": (user.get("username") if user else "Anonymous"),
            }
        )
    _audit(
        request,
        action="LIST_PUBLIC_REVIEWS",
        resource="reviews",
        purpose="public_reviews",
        result="SUCCESS",
        metadata={"count": len(items), "limit": limit},
    )
    return {
        "ok": True,
        "items": items,
        "avg_rating": avg,
        "total_reviews": total,
        "visibility_months": get_review_visibility_months(),
    }


@app.get("/reviews/approved")
def get_public_reviews_legacy(limit: int = 50, request: Request = None):
    # Backward-compatible alias. Public UI should not use "approved" wording.
    return get_public_reviews(limit=limit, request=request)


@app.get("/reviews/me")
def get_my_review(
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user = _require_user(requester_id)
    user_id = user["id"]
    model = get_review_by_user_id(user_id)
    if not model:
        _audit(
            request,
            action="READ_OWN_REVIEW",
            actor_id=user_id,
            resource=f"review:user:{user_id}",
            purpose="account_self_service",
            result="SUCCESS",
            metadata={"found": False},
        )
        return {"ok": True, "review": None, "min_len": MIN_REVIEW_LEN, "max_len": MAX_REVIEW_LEN}
    _audit(
        request,
        action="READ_OWN_REVIEW",
        actor_id=user_id,
        resource=model.id,
        purpose="account_self_service",
        result="SUCCESS",
        metadata={"found": True},
    )
    return {
        "ok": True,
        "review": {
            "id": model.id,
            "review_text": model.review_text,
            "rating": model.rating,
            "status": model.status,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        },
        "min_len": MIN_REVIEW_LEN,
        "max_len": MAX_REVIEW_LEN,
    }


@app.put("/reviews/me")
def upsert_my_review(
    payload: ReviewUpsertRequest,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user = _require_user(requester_id)
    user_id = user["id"]
    try:
        validated = validate_review_payload(payload.review_text, payload.rating)
    except ValueError as e:
        _audit(
            request,
            action="UPSERT_REVIEW",
            actor_id=user_id,
            resource=f"review:user:{user_id}",
            purpose="review_submission",
            result="DENIED",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))

    try:
        model = upsert_user_review(
            user_id=user_id,
            review_text=validated.review_text,
            rating=validated.rating,
        )
    except ValueError as e:
        _audit(
            request,
            action="UPSERT_REVIEW",
            actor_id=user_id,
            resource=f"review:user:{user_id}",
            purpose="review_submission",
            result="DENIED",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=429, detail=str(e))

    _audit(
        request,
        action="UPSERT_REVIEW",
        actor_id=user_id,
        resource=model.id,
        purpose="review_submission",
        result="SUCCESS",
        metadata={"rating": validated.rating, "status": model.status},
    )
    return {
        "ok": True,
        "review": {
            "id": model.id,
            "review_text": model.review_text,
            "rating": model.rating,
            "status": model.status,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        },
    }


@app.get("/admin/reviews")
def admin_list_reviews(
    status: str = "pending",
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
    requester_username: str | None = Header(default=None, alias="X-Username"),
):
    user = _require_user(requester_id)
    if not is_admin(user_id=user["id"], username=user.get("username")):
        _audit(
            request,
            action="ADMIN_LIST_REVIEWS",
            actor_id=user["id"],
            resource="reviews",
            purpose="admin_review_moderation",
            result="DENIED",
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    normalized = (status or "pending").strip().lower()
    try:
        models = list_reviews_for_admin(normalized)
    except ValueError:
        _audit(
            request,
            action="ADMIN_LIST_REVIEWS",
            actor_id=user["id"],
            resource="reviews",
            purpose="admin_review_moderation",
            result="DENIED",
            metadata={"reason": "invalid_status", "status": normalized},
        )
        raise HTTPException(status_code=400, detail="Invalid status")

    cutoff = visibility_cutoff()
    vis_avg, vis_count = get_visible_stats()
    lifetime_avg, lifetime_count = get_lifetime_stats()
    approved_avg, approved_count = get_lifetime_stats(statuses=["approved"])
    items = []
    for m in models:
        u = get_user_by_id(m.user_id)
        archived = bool(m.status == "approved" and m.created_at and m.created_at < cutoff)
        visible = bool(m.status == "approved" and not archived)
        view_status = "archived" if archived else ("visible" if visible else m.status)
        items.append(
            {
                "id": m.id,
                "user_id": m.user_id,
                "review_text": m.review_text,
                "rating": m.rating,
                "status": m.status,
                "view_status": view_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                "reviewer_name": (u.get("username") if u else "Unknown"),
            }
        )
    _audit(
        request,
        action="ADMIN_LIST_REVIEWS",
        actor_id=user["id"],
        resource="reviews",
        purpose="admin_review_moderation",
        result="SUCCESS",
        metadata={"status": normalized, "count": len(items)},
    )
    return {
        "ok": True,
        "items": items,
        "visibility_months": get_review_visibility_months(),
        "stats": {
            "visible_avg_rating": vis_avg,
            "visible_count": vis_count,
            "lifetime_avg_rating": lifetime_avg,
            "lifetime_count": lifetime_count,
            "approved_lifetime_avg_rating": approved_avg,
            "approved_lifetime_count": approved_count,
        },
    }


@app.patch("/admin/reviews/{review_id}")
def admin_moderate_review(
    review_id: str,
    payload: ReviewModerationRequest,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
    requester_username: str | None = Header(default=None, alias="X-Username"),
):
    user = _require_user(requester_id)
    if not is_admin(user_id=user["id"], username=user.get("username")):
        _audit(
            request,
            action="ADMIN_MODERATE_REVIEW",
            actor_id=user["id"],
            resource=review_id,
            purpose="admin_review_moderation",
            result="DENIED",
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    normalized = (payload.status or "").strip().lower()
    if normalized not in ("approved", "rejected", "pending"):
        _audit(
            request,
            action="ADMIN_MODERATE_REVIEW",
            actor_id=user["id"],
            resource=review_id,
            purpose="admin_review_moderation",
            result="DENIED",
            metadata={"reason": "invalid_status", "status": normalized},
        )
        raise HTTPException(status_code=400, detail="Invalid status")

    model = set_review_status(review_id, normalized)
    if not model:
        _audit(
            request,
            action="ADMIN_MODERATE_REVIEW",
            actor_id=user["id"],
            resource=review_id,
            purpose="admin_review_moderation",
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Review not found")
    _audit(
        request,
        action="ADMIN_MODERATE_REVIEW",
        actor_id=user["id"],
        resource=review_id,
        purpose="admin_review_moderation",
        result="SUCCESS",
        metadata={"status": normalized},
    )
    return {"ok": True}


@app.delete("/admin/reviews/{review_id}")
def admin_delete_review(
    review_id: str,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
    requester_username: str | None = Header(default=None, alias="X-Username"),
):
    user = _require_user(requester_id)
    if not is_admin(user_id=user["id"], username=user.get("username")):
        _audit(
            request,
            action="ADMIN_DELETE_REVIEW",
            actor_id=user["id"],
            resource=review_id,
            purpose="admin_review_moderation",
            result="DENIED",
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    deleted = delete_review_db(review_id)
    if not deleted:
        _audit(
            request,
            action="ADMIN_DELETE_REVIEW",
            actor_id=user["id"],
            resource=review_id,
            purpose="admin_review_moderation",
            result="NOT_FOUND",
        )
        raise HTTPException(status_code=404, detail="Review not found")
    _audit(
        request,
        action="ADMIN_DELETE_REVIEW",
        actor_id=user["id"],
        resource=review_id,
        purpose="admin_review_moderation",
        result="SUCCESS",
    )
    return {"ok": True}


@app.patch("/users/{user_id}/plan")
def update_user_plan_endpoint(
    user_id: str,
    payload: PlanUpdate,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not requester_id or requester_id != user_id:
        _audit(
            request,
            action="UPDATE_USER_PLAN",
            actor_id=requester_id,
            resource=user_id,
            purpose="account_self_service",
            result="DENIED",
            metadata={"reason": "not_owner"},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    if payload.plan.strip().lower() not in ALLOWED_PLANS:
        _audit(
            request,
            action="UPDATE_USER_PLAN",
            actor_id=requester_id,
            resource=user_id,
            purpose="account_self_service",
            result="DENIED",
            metadata={"reason": "invalid_plan", "plan": payload.plan},
        )
        raise HTTPException(status_code=400, detail="Invalid plan")

    try:
        user = update_user_plan(user_id, payload.plan)
        _audit(
            request,
            action="UPDATE_USER_PLAN",
            actor_id=requester_id,
            resource=user_id,
            purpose="account_self_service",
            result="SUCCESS",
            metadata={"plan": user.get("plan")},
        )
        return {"ok": True, "user": user}
    except ValueError as e:
        _audit(
            request,
            action="UPDATE_USER_PLAN",
            actor_id=requester_id,
            resource=user_id,
            purpose="account_self_service",
            result="NOT_FOUND",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/admin/users/{user_id}/kyb")
def admin_update_user_kyb_status(
    user_id: str,
    payload: KybStatusUpdate,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    admin_user = _require_user(requester_id)
    if not is_admin(user_id=admin_user["id"], username=admin_user.get("username")):
        _audit(
            request,
            action="ADMIN_UPDATE_KYB",
            actor_id=admin_user["id"],
            resource=user_id,
            purpose="kyb_verification",
            result="DENIED",
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    normalized = (payload.status or "").strip().lower()
    if normalized not in ALLOWED_KYB_STATUSES:
        _audit(
            request,
            action="ADMIN_UPDATE_KYB",
            actor_id=admin_user["id"],
            resource=user_id,
            purpose="kyb_verification",
            result="DENIED",
            metadata={"reason": "invalid_status", "status": normalized},
        )
        raise HTTPException(status_code=400, detail="Invalid KYB status")

    try:
        user = update_user_kyb_status(user_id, normalized)
    except ValueError as e:
        _audit(
            request,
            action="ADMIN_UPDATE_KYB",
            actor_id=admin_user["id"],
            resource=user_id,
            purpose="kyb_verification",
            result="NOT_FOUND",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))

    _audit(
        request,
        action="ADMIN_UPDATE_KYB",
        actor_id=admin_user["id"],
        resource=user_id,
        purpose="kyb_verification",
        result="SUCCESS",
        metadata={"kyb_status": normalized},
    )
    return {"ok": True, "user": user}


@app.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: str,
    request: Request = None,
    requester_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not requester_id or requester_id != user_id:
        _audit(
            request,
            action="DELETE_USER",
            actor_id=requester_id,
            resource=user_id,
            purpose="account_deletion",
            result="DENIED",
            metadata={"reason": "not_owner"},
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fail closed on cleanup errors so account deletion does not orphan data.
    try:
        records = list_records()
    except Exception:
        logger.exception("Failed to list dataset records for user deletion: %s", user_id)
        _audit(
            request,
            action="DELETE_USER",
            actor_id=user_id,
            resource=user_id,
            purpose="account_deletion",
            result="FAILURE",
            metadata={"stage": "list_datasets"},
        )
        raise HTTPException(status_code=503, detail="Failed to load user datasets")

    for rec in records:
        extra = rec.get("extra", {}) or {}
        if extra.get("owner_user_id") != user_id:
            continue
        file_hash = rec.get("hash")
        object_key = rec.get("object_key") or extra.get("object_key")

        if object_key:
            try:
                delete_object(key=object_key)
            except Exception:
                logger.exception("Failed to delete GCS object %s", object_key)
                _audit(
                    request,
                    action="DELETE_USER",
                    actor_id=user_id,
                    resource=user_id,
                    purpose="account_deletion",
                    result="FAILURE",
                    metadata={"stage": "delete_dataset_file", "file_hash": file_hash},
                )
                raise HTTPException(status_code=500, detail="Failed to delete user dataset file")

        if file_hash:
            try:
                deleted = delete_record(file_hash)
            except Exception:
                logger.exception("Failed to delete record %s", file_hash)
                _audit(
                    request,
                    action="DELETE_USER",
                    actor_id=user_id,
                    resource=user_id,
                    purpose="account_deletion",
                    result="FAILURE",
                    metadata={"stage": "delete_dataset_metadata", "file_hash": file_hash},
                )
                raise HTTPException(status_code=500, detail="Failed to delete user dataset metadata")
            if not deleted:
                logger.warning("Dataset record already missing during user deletion: %s", file_hash)

    review = get_review_by_user_id(user_id)
    if review:
        try:
            deleted = delete_review_db(review.id)
        except Exception:
            logger.exception("Failed to delete review %s for user %s", review.id, user_id)
            _audit(
                request,
                action="DELETE_USER",
                actor_id=user_id,
                resource=user_id,
                purpose="account_deletion",
                result="FAILURE",
                metadata={"stage": "delete_review", "review_id": review.id},
            )
            raise HTTPException(status_code=500, detail="Failed to delete user review")
        if not deleted:
            logger.error("Review disappeared during user deletion: %s", review.id)
            _audit(
                request,
                action="DELETE_USER",
                actor_id=user_id,
                resource=user_id,
                purpose="account_deletion",
                result="FAILURE",
                metadata={"stage": "delete_review_missing", "review_id": review.id},
            )
            raise HTTPException(status_code=500, detail="Failed to delete user review")

    try:
        delete_user(user_id)
    except ValueError as e:
        _audit(
            request,
            action="DELETE_USER",
            actor_id=user_id,
            resource=user_id,
            purpose="account_deletion",
            result="NOT_FOUND",
            metadata={"reason": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))

    _audit(
        request,
        action="DELETE_USER",
        actor_id=user_id,
        resource=user_id,
        purpose="account_deletion",
        result="SUCCESS",
    )
    return {"ok": True}
