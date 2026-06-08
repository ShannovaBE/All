import unittest

from reviews.visibility import compute_stats


class TestReviewStats(unittest.TestCase):
    def test_visible_vs_lifetime_average(self):
        visible, lifetime = compute_stats(visible_ratings=[5, 4], lifetime_ratings=[5, 4, 1])
        self.assertEqual(visible.count, 2)
        self.assertAlmostEqual(visible.avg_rating, 4.5)
        self.assertEqual(lifetime.count, 3)
        self.assertAlmostEqual(lifetime.avg_rating, (5 + 4 + 1) / 3)

    def test_empty_lists(self):
        visible, lifetime = compute_stats(visible_ratings=[], lifetime_ratings=[])
        self.assertEqual(visible.count, 0)
        self.assertEqual(visible.avg_rating, 0.0)
        self.assertEqual(lifetime.count, 0)
        self.assertEqual(lifetime.avg_rating, 0.0)


if __name__ == "__main__":
    unittest.main()

