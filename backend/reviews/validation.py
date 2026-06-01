from __future__ import annotations

import re
from dataclasses import dataclass


MIN_REVIEW_LEN = 30
MAX_REVIEW_LEN = 1000


@dataclass(frozen=True)
class ReviewPayload:
    review_text: str
    rating: int


_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_review_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.replace("\x00", "")
    cleaned = cleaned.strip()
    cleaned = _TAG_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def validate_review_payload(review_text: str, rating: int) -> ReviewPayload:
    cleaned = sanitize_review_text(review_text)
    if not cleaned:
        raise ValueError("Review cannot be empty")
    if len(cleaned) < MIN_REVIEW_LEN:
        raise ValueError(f"Review must be at least {MIN_REVIEW_LEN} characters")
    if len(cleaned) > MAX_REVIEW_LEN:
        raise ValueError(f"Review must be at most {MAX_REVIEW_LEN} characters")

    if not isinstance(rating, int):
        raise ValueError("Rating must be an integer")
    if rating not in (1, 2, 3, 4, 5):
        raise ValueError("Rating must be between 1 and 5")

    return ReviewPayload(review_text=cleaned, rating=rating)

