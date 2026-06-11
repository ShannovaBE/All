from __future__ import annotations

import os
import calendar
from datetime import datetime, timezone


DEFAULT_VISIBILITY_MONTHS = 24


def get_review_visibility_months() -> int:
    raw = os.getenv("REVIEW_VISIBILITY_MONTHS", "").strip()
    if not raw:
        return DEFAULT_VISIBILITY_MONTHS
    try:
        months = int(raw)
    except ValueError:
        return DEFAULT_VISIBILITY_MONTHS
    return max(1, min(120, months))


def subtract_months(dt: datetime, months: int) -> datetime:
    if months <= 0:
        return dt

    year = dt.year
    month = dt.month - months
    while month <= 0:
        month += 12
        year -= 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)


def visibility_cutoff(now: datetime | None = None) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    months = get_review_visibility_months()
    return subtract_months(now, months)
