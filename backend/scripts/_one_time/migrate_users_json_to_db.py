from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal
from models import User


USERS_FILE = BACKEND_DIR / "users_store" / "users.json"


def main() -> None:
    if not USERS_FILE.exists():
        raise SystemExit(f"No legacy user file found at {USERS_FILE}")

    with USERS_FILE.open("r", encoding="utf-8") as f:
        legacy_users = json.load(f)

    created = 0
    skipped = 0
    with SessionLocal() as db:
        for legacy in legacy_users.values():
            user_id = legacy.get("id")
            if not user_id or db.get(User, user_id):
                skipped += 1
                continue
            db.add(
                User(
                    id=user_id,
                    username=legacy["username"],
                    email=legacy["email"],
                    password_hash=legacy["password_hash"],
                    plan=legacy.get("plan", "free"),
                    kyb_status=legacy.get("kyb_status", "pending"),
                    restricted=bool(legacy.get("restricted", False)),
                )
            )
            created += 1
        db.commit()

    print(f"Migrated {created} users; skipped {skipped}.")


if __name__ == "__main__":
    main()
