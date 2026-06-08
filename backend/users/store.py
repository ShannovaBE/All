# backend/users/store.py
from pathlib import Path
import base64
import binascii
import hmac
import json
import hashlib
import os
from typing import Optional, Dict, Any
import uuid

USERS_DIR = Path("backend/users_store")
USERS_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = USERS_DIR / "users.json"


def _load_all_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all_users(data: Dict[str, Any]) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_PBKDF2_ITERATIONS", "260000"))
PASSWORD_SALT_BYTES = 16


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


ALLOWED_PLANS = ["free", "basic", "business", "enterprise"]
ALLOWED_KYB_STATUSES = ["pending", "verified", "rejected"]


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "plan": user.get("plan", "free"),
        "kyb_status": user.get("kyb_status", "pending"),
        "restricted": bool(user.get("restricted", False)),
    }


def create_user(username: str, email: str, password: str, plan: str = "free") -> Dict[str, Any]:
    users = _load_all_users()

    # Check username is unique
    if any(u["username"] == username for u in users.values()):
        raise ValueError("Username already exists")

    normalized_plan = (plan or "free").strip().lower()
    if normalized_plan not in ALLOWED_PLANS:
        normalized_plan = "free"

    user_id = str(uuid.uuid4())

    user_data = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": _hash_password(password),
        "plan": normalized_plan,
        "kyb_status": "pending",
        "restricted": False,
    }

    users[user_id] = user_data
    _save_all_users(users)

    # Return only safe (public) fields
    return _public_user(user_data)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    users = _load_all_users()
    for user in users.values():
        if user["username"] == username:
            return user
    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    users = _load_all_users()
    return users.get(user_id)


def update_user_plan(user_id: str, plan: str) -> Dict[str, Any]:
    users = _load_all_users()
    user = users.get(user_id)
    if not user:
        raise ValueError("User not found")

    normalized_plan = (plan or "").strip().lower()
    if normalized_plan not in ALLOWED_PLANS:
        raise ValueError("Invalid plan")

    user["plan"] = normalized_plan
    users[user_id] = user
    _save_all_users(users)

    return _public_user(user)


def update_user_kyb_status(user_id: str, status: str) -> Dict[str, Any]:
    users = _load_all_users()
    user = users.get(user_id)
    if not user:
        raise ValueError("User not found")

    normalized = (status or "").strip().lower()
    if normalized not in ALLOWED_KYB_STATUSES:
        raise ValueError("Invalid KYB status")

    user["kyb_status"] = normalized
    users[user_id] = user
    _save_all_users(users)
    return _public_user(user)


def set_user_restricted(user_id: str, restricted: bool) -> Dict[str, Any]:
    users = _load_all_users()
    user = users.get(user_id)
    if not user:
        raise ValueError("User not found")

    user["restricted"] = bool(restricted)
    users[user_id] = user
    _save_all_users(users)
    return _public_user(user)


def delete_user(user_id: str) -> None:
    users = _load_all_users()
    if user_id not in users:
        raise ValueError("User not found")
    users.pop(user_id, None)
    _save_all_users(users)


def verify_user_password(username: str, password: str) -> bool:
    users = _load_all_users()
    user_id = None
    user = None
    for candidate_id, candidate in users.items():
        if candidate["username"] == username:
            user_id = candidate_id
            user = candidate
            break
    if not user or user_id is None:
        return False
    stored_hash = user.get("password_hash", "")
    if not _verify_password(password, stored_hash):
        return False
    if _is_legacy_sha256_hash(stored_hash):
        user["password_hash"] = _hash_password(password)
        users[user_id] = user
        _save_all_users(users)
    return True
