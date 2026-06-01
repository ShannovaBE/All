# backend/users/store.py
from pathlib import Path
import json
import hashlib
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


def _hash_password(password: str) -> str:
    # ⚠️ DEV ONLY — replace with a real password hasher later
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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
    user = get_user_by_username(username)
    if not user:
        return False
    return user["password_hash"] == _hash_password(password)
