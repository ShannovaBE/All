import os
import unittest
from datetime import datetime, timezone

from reviews.settings import (
    DEFAULT_VISIBILITY_MONTHS,
    get_review_visibility_months,
    subtract_months,
    visibility_cutoff,
)


class TestReviewVisibilitySettings(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.environ.get("REVIEW_VISIBILITY_MONTHS")
        return super().setUp()

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("REVIEW_VISIBILITY_MONTHS", None)
        else:
            os.environ["REVIEW_VISIBILITY_MONTHS"] = self._old
        return super().tearDown()

    def test_default_visibility_months(self):
        os.environ.pop("REVIEW_VISIBILITY_MONTHS", None)
        self.assertEqual(get_review_visibility_months(), DEFAULT_VISIBILITY_MONTHS)

    def test_visibility_months_clamped(self):
        os.environ["REVIEW_VISIBILITY_MONTHS"] = "0"
        self.assertEqual(get_review_visibility_months(), 1)
        os.environ["REVIEW_VISIBILITY_MONTHS"] = "999"
        self.assertEqual(get_review_visibility_months(), 120)

    def test_subtract_months_calendar_correctness(self):
        # March 31 -> February 28 (or 29) when subtracting one month.
        dt = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
        out = subtract_months(dt, 1)
        self.assertEqual(out.year, 2026)
        self.assertEqual(out.month, 2)
        self.assertIn(out.day, (28, 29))
        self.assertEqual(out.hour, 12)

    def test_visibility_cutoff_uses_env_months(self):
        os.environ["REVIEW_VISIBILITY_MONTHS"] = "24"
        now = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        cutoff = visibility_cutoff(now)
        self.assertEqual(cutoff.year, 2024)
        self.assertEqual(cutoff.month, 3)
        self.assertEqual(cutoff.day, 9)


if __name__ == "__main__":
    unittest.main()

