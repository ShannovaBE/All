from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional


@dataclass(frozen=True)
class ReviewStat:
    avg_rating: float
    count: int


def _safe_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_visible_review(*, status: str, created_at: Optional[datetime], cutoff: datetime) -> bool:
    if status != "approved":
        return False
    created = _safe_dt(created_at)
    if created is None:
        return False
    return created >= cutoff


def is_archived_review(*, status: str, created_at: Optional[datetime], cutoff: datetime) -> bool:
    if status != "approved":
        return False
    created = _safe_dt(created_at)
    if created is None:
        return False
    return created < cutoff


def compute_stats(
    *,
    visible_ratings: Iterable[int],
    lifetime_ratings: Iterable[int],
) -> tuple[ReviewStat, ReviewStat]:
    visible = list(visible_ratings)
    lifetime = list(lifetime_ratings)

    def _avg(values: list[int]) -> float:
        if not values:
            return 0.0
        return float(sum(values)) / float(len(values))

    return (
        ReviewStat(avg_rating=_avg(visible), count=len(visible)),
        ReviewStat(avg_rating=_avg(lifetime), count=len(lifetime)),
    )

