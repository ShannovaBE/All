# backend/users/store.py
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from db import SessionLocal
from models import User


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_PBKDF2_ITERATIONS", "260000"))
PASSWORD_SALT_BYTES = 16

ALLOWED_PLANS = ["free", "basic", "business", "enterprise"]
ALLOWED_KYB_STATUSES = ["pending", "verified", "rejected"]


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def _hash_password(password: str) -> str:
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_PBKDF2_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def _legacy_sha256_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_legacy_sha256_hash(value: str) -> bool:
    return len(value or "") == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if _is_legacy_sha256_hash(stored_hash):
        return hmac.compare_digest(stored_hash, _legacy_sha256_hash(password))

    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != PASSWORD_HASH_ALGORITHM:
        return False

    try:
        iterations = int(parts[1])
        salt = _b64decode(parts[2])
        expected = _b64decode(parts[3])
    except (ValueError, binascii.Error):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(expected, actual)


def _model_to_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "plan": user.plan or "free",
        "kyb_status": user.kyb_status or "pending",
        "restricted": bool(user.restricted),
    }


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "plan": user.get("plan", "free"),
        "kyb_status": user.get("kyb_status", "pending"),
        "restricted": bool(user.get("restricted", False)),
    }


def list_users() -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        rows = db.execute(select(User).order_by(User.created_at.asc())).scalars().all()
        return [_model_to_user(row) for row in rows]


def create_user(username: str, email: str, password: str, plan: str = "free") -> Dict[str, Any]:
    normalized_username = (username or "").strip()
    normalized_email = (email or "").strip().lower()
    if not normalized_username:
        raise ValueError("Username is required")
    if not normalized_email:
        raise ValueError("Email is required")

    normalized_plan = (plan or "free").strip().lower()
    if normalized_plan not in ALLOWED_PLANS:
        normalized_plan = "free"

    with SessionLocal() as db:
        existing = db.execute(
            select(User).where((User.username == normalized_username) | (User.email == normalized_email))
        ).scalar_one_or_none()
        if existing and existing.username == normalized_username:
            raise ValueError("Username already exists")
        if existing and existing.email == normalized_email:
            raise ValueError("Email already exists")

        user = User(
            id=str(uuid.uuid4()),
            username=normalized_username,
            email=normalized_email,
            password_hash=_hash_password(password),
            plan=normalized_plan,
            kyb_status="pending",
            restricted=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _public_user(_model_to_user(user))


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        return _model_to_user(user) if user else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        return _model_to_user(user) if user else None


def update_user_plan(user_id: str, plan: str) -> Dict[str, Any]:
    normalized_plan = (plan or "").strip().lower()
    if normalized_plan not in ALLOWED_PLANS:
        raise ValueError("Invalid plan")

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        user.plan = normalized_plan
        db.commit()
        db.refresh(user)
        return _public_user(_model_to_user(user))


def update_user_kyb_status(user_id: str, status: str) -> Dict[str, Any]:
    normalized = (status or "").strip().lower()
    if normalized not in ALLOWED_KYB_STATUSES:
        raise ValueError("Invalid KYB status")

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        user.kyb_status = normalized
        db.commit()
        db.refresh(user)
        return _public_user(_model_to_user(user))


def set_user_restricted(user_id: str, restricted: bool) -> Dict[str, Any]:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        user.restricted = bool(restricted)
        db.commit()
        db.refresh(user)
        return _public_user(_model_to_user(user))


def delete_user(user_id: str) -> None:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        db.delete(user)
        db.commit()


def verify_user_password(username: str, password: str) -> bool:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not user:
            return False
        stored_hash = user.password_hash
        if not _verify_password(password, stored_hash):
            return False
        if _is_legacy_sha256_hash(stored_hash):
            user.password_hash = _hash_password(password)
            db.commit()
        return True
