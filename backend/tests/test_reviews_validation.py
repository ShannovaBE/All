import unittest

from reviews.validation import MAX_REVIEW_LEN, MIN_REVIEW_LEN, validate_review_payload


class TestReviewValidation(unittest.TestCase):
    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            validate_review_payload("   ", 5)

    def test_rejects_out_of_range_rating(self):
        with self.assertRaises(ValueError):
            validate_review_payload("x" * MIN_REVIEW_LEN, 0)
        with self.assertRaises(ValueError):
            validate_review_payload("x" * MIN_REVIEW_LEN, 6)

    def test_accepts_valid(self):
        payload = validate_review_payload("Great experience. " * 3, 5)
        self.assertEqual(payload.rating, 5)
        self.assertTrue(len(payload.review_text) >= MIN_REVIEW_LEN)

    def test_limits_length(self):
        with self.assertRaises(ValueError):
            validate_review_payload("a" * (MIN_REVIEW_LEN - 1), 5)
        with self.assertRaises(ValueError):
            validate_review_payload("a" * (MAX_REVIEW_LEN + 1), 5)

    def test_strips_tags(self):
        payload = validate_review_payload("<b>" + ("x" * MIN_REVIEW_LEN) + "</b>", 4)
        self.assertNotIn("<b>", payload.review_text)


if __name__ == "__main__":
    unittest.main()

