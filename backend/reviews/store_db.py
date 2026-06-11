from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from models import Review
from reviews.settings import visibility_cutoff


RATE_LIMIT_SECONDS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_visible_reviews(limit: int = 50) -> List[Review]:
    cutoff = visibility_cutoff()
    with SessionLocal() as db:
        stmt = (
            select(Review)
            .where(Review.status == "approved")
            .where(Review.created_at >= cutoff)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()


def get_review_by_user_id(user_id: str) -> Optional[Review]:
    with SessionLocal() as db:
        return db.execute(select(Review).where(Review.user_id == user_id)).scalar_one_or_none()


def list_reviews_by_status(status: str) -> List[Review]:
    with SessionLocal() as db:
        stmt = select(Review).where(Review.status == status).order_by(Review.created_at.desc())
        return db.execute(stmt).scalars().all()


def list_archived_reviews(limit: int = 200) -> List[Review]:
    cutoff = visibility_cutoff()
    with SessionLocal() as db:
        stmt = (
            select(Review)
            .where(Review.status == "approved")
            .where(Review.created_at < cutoff)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()


def get_visible_stats() -> Tuple[float, int]:
    cutoff = visibility_cutoff()
    with SessionLocal() as db:
        avg_rating = db.execute(
            select(func.avg(Review.rating))
            .where(Review.status == "approved")
            .where(Review.created_at >= cutoff)
        ).scalar_one()
        count = db.execute(
            select(func.count())
            .select_from(Review)
            .where(Review.status == "approved")
            .where(Review.created_at >= cutoff)
        ).scalar_one()
        return (float(avg_rating) if avg_rating is not None else 0.0, int(count or 0))


def get_lifetime_stats(*, statuses: Optional[List[str]] = None) -> Tuple[float, int]:
    with SessionLocal() as db:
        stmt_avg = select(func.avg(Review.rating))
        stmt_count = select(func.count()).select_from(Review)
        if statuses:
            stmt_avg = stmt_avg.where(Review.status.in_(statuses))
            stmt_count = stmt_count.where(Review.status.in_(statuses))
        avg_rating = db.execute(stmt_avg).scalar_one()
        count = db.execute(stmt_count).scalar_one()
        return (float(avg_rating) if avg_rating is not None else 0.0, int(count or 0))


def list_reviews_for_admin(filter_key: str, limit: int = 200) -> List[Review]:
    normalized = (filter_key or "pending").strip().lower()
    cutoff = visibility_cutoff()

    with SessionLocal() as db:
        stmt = select(Review).order_by(Review.created_at.desc()).limit(limit)

        if normalized == "all":
            return db.execute(stmt).scalars().all()
        if normalized == "pending":
            return db.execute(stmt.where(Review.status == "pending")).scalars().all()
        if normalized == "rejected":
            return db.execute(stmt.where(Review.status == "rejected")).scalars().all()
        if normalized == "visible":
            return (
                db.execute(
                    stmt.where(Review.status == "approved").where(Review.created_at >= cutoff)
                )
                .scalars()
                .all()
            )
        if normalized == "archived":
            return (
                db.execute(
                    stmt.where(Review.status == "approved").where(Review.created_at < cutoff)
                )
                .scalars()
                .all()
            )
        if normalized == "approved":
            return db.execute(stmt.where(Review.status == "approved")).scalars().all()

        raise ValueError("Invalid status")


def upsert_user_review(
    *,
    user_id: str,
    review_text: str,
    rating: int,
) -> Review:
    now = _now()
    with SessionLocal() as db:
        existing = db.execute(select(Review).where(Review.user_id == user_id)).scalar_one_or_none()

        if existing is not None and existing.updated_at is not None:
            if existing.updated_at >= now - timedelta(seconds=RATE_LIMIT_SECONDS):
                raise ValueError("Too many requests. Please wait and try again.")

        if existing is None:
            existing = Review(
                id=str(uuid.uuid4()),
                user_id=user_id,
                review_text=review_text,
                rating=rating,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            db.add(existing)
        else:
            existing.review_text = review_text
            existing.rating = rating
            existing.status = "pending"
            existing.updated_at = now

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("Review already exists for this account. Please refresh and try again.")

        db.refresh(existing)
        return existing


def set_review_status(review_id: str, status: str) -> Optional[Review]:
    with SessionLocal() as db:
        model = db.execute(select(Review).where(Review.id == review_id)).scalar_one_or_none()
        if model is None:
            return None
        model.status = status
        model.updated_at = _now()
        db.commit()
        db.refresh(model)
        return model


def delete_review(review_id: str) -> bool:
    with SessionLocal() as db:
        model = db.execute(select(Review).where(Review.id == review_id)).scalar_one_or_none()
        if model is None:
            return False
        db.delete(model)
        db.commit()
        return True
