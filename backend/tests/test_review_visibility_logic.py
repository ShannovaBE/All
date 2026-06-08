import unittest
from datetime import datetime, timezone

from reviews.visibility import is_archived_review, is_visible_review


class TestReviewVisibilityLogic(unittest.TestCase):
    def test_visible_boundary(self):
        cutoff = datetime(2024, 3, 9, tzinfo=timezone.utc)
        self.assertTrue(is_visible_review(status="approved", created_at=cutoff, cutoff=cutoff))
        self.assertFalse(
            is_visible_review(
                status="approved",
                created_at=datetime(2024, 3, 8, 23, 59, tzinfo=timezone.utc),
                cutoff=cutoff,
            )
        )

    def test_archived_boundary(self):
        cutoff = datetime(2024, 3, 9, tzinfo=timezone.utc)
        self.assertTrue(
            is_archived_review(
                status="approved",
                created_at=datetime(2024, 3, 8, 23, 59, tzinfo=timezone.utc),
                cutoff=cutoff,
            )
        )
        self.assertFalse(is_archived_review(status="approved", created_at=cutoff, cutoff=cutoff))

    def test_non_approved_never_visible_or_archived(self):
        cutoff = datetime(2024, 3, 9, tzinfo=timezone.utc)
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertFalse(is_visible_review(status="pending", created_at=dt, cutoff=cutoff))
        self.assertFalse(is_archived_review(status="rejected", created_at=dt, cutoff=cutoff))


if __name__ == "__main__":
    unittest.main()

