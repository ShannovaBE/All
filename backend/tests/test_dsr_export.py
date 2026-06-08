import unittest
from unittest import mock

import main


class TestDataSubjectExport(unittest.TestCase):
    def test_build_user_export_includes_user_datasets_and_review(self):
        user = {
            "id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
            "plan": "business",
            "kyb_status": "verified",
        }
        records = [
            {"hash": "owned", "owner": "user-1", "filename": "a.csv"},
            {"hash": "other", "owner": "user-2", "filename": "b.csv"},
        ]
        review = mock.Mock(
            id="review-1",
            review_text="Useful platform",
            rating=5,
            status="pending",
            created_at=None,
            updated_at=None,
        )

        with mock.patch.object(main, "get_user_by_id", return_value=user), mock.patch.object(
            main, "list_records", return_value=records
        ), mock.patch.object(main, "get_review_by_user_id", return_value=review):
            payload = main._build_user_export("user-1")

        self.assertEqual("user-1", payload["user"]["id"])
        self.assertEqual(1, len(payload["datasets"]))
        self.assertEqual("owned", payload["datasets"][0]["hash"])
        self.assertEqual("review-1", payload["review"]["id"])

    def test_user_export_csv_contains_sections(self):
        csv_text = main._user_export_as_csv(
            {
                "user": {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@example.com",
                    "plan": "business",
                    "kyb_status": "verified",
                    "restricted": False,
                },
                "datasets": [{"hash": "dataset-1", "filename": "data.csv", "category": "finance"}],
                "review": {"id": "review-1", "status": "pending"},
            }
        )

        self.assertIn("section,id", csv_text)
        self.assertIn("user,user-1", csv_text)
        self.assertIn("dataset,dataset-1", csv_text)
        self.assertIn("review,review-1", csv_text)


if __name__ == "__main__":
    unittest.main()
