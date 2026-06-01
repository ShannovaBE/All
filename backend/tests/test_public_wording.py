import pathlib
import unittest


class TestPublicWording(unittest.TestCase):
    def test_no_approved_reviews_phrase_on_public_reviews_page(self):
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        page = repo_root / "app" / "reviews" / "page.tsx"
        if not page.exists():
            page = repo_root / "frontend" / "app" / "reviews" / "page.tsx"
        content = page.read_text(encoding="utf-8")
        self.assertNotIn("approved reviews", content.lower())


if __name__ == "__main__":
    unittest.main()
