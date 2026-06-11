from __future__ import annotations

import os
from typing import Optional


def is_admin(*, user_id: str, username: Optional[str]) -> bool:
    raw_ids = os.getenv("ADMIN_USER_IDS", "").strip()
    raw_names = os.getenv("ADMIN_USERNAMES", "").strip()
    admin_ids = {s.strip() for s in raw_ids.split(",") if s.strip()}
    admin_names = {s.strip().lower() for s in raw_names.split(",") if s.strip()}

    if user_id in admin_ids:
        return True
    if username and username.strip().lower() in admin_names:
        return True
    return False

