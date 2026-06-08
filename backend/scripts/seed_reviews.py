from __future__ import annotations

import os
from datetime import datetime, timezone
import uuid

from db import SessionLocal
from models import Review
from users import list_users


def main() -> None:
    if os.getenv("ALLOW_SEED_REVIEWS", "").strip().lower() not in ("1", "true", "yes"):
        raise SystemExit(
            "Refusing to seed. Set ALLOW_SEED_REVIEWS=true to insert sample approved reviews."
        )

    users = list_users()
    if not users:
        raise SystemExit("No users found in the database. Create users first.")

    now = datetime.now(timezone.utc)
    samples = [
        ("Shannova made compliance reviews much easier for our team.", 5),
        ("Clean UI and fast workflow. Would like more filters, but solid.", 4),
        ("Great for finding privacy-safe datasets quickly.", 5),
    ]

    with SessionLocal() as db:
        existing_count = db.query(Review).count()
        if existing_count > 0:
            raise SystemExit("Reviews already exist. Aborting to avoid duplicates.")

        for idx, (user, sample) in enumerate(zip(users, samples, strict=False)):
            text, rating = sample
            db.add(
                Review(
                    id=str(uuid.uuid4()),
                    user_id=user["id"],
                    review_text=text,
                    rating=rating,
                    status="approved",
                    created_at=now,
                    updated_at=now,
                )
            )
            if idx >= 2:
                break

        db.commit()

    print("Seeded sample approved reviews.")


if __name__ == "__main__":
    main()
