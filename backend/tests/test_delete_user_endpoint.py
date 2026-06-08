import unittest
from types import SimpleNamespace
from unittest import mock

try:
    from fastapi import HTTPException
    import main
except ModuleNotFoundError:  # pragma: no cover - depends on local test env
    HTTPException = None
    main = None


@unittest.skipIf(HTTPException is None or main is None, "fastapi app dependencies not installed")
class TestDeleteUserEndpoint(unittest.TestCase):
    def test_delete_user_aborts_when_dataset_listing_fails(self):
        with mock.patch.object(main, "list_records", side_effect=RuntimeError("db down")), mock.patch.object(
            main, "delete_user"
        ) as delete_user:
            with self.assertRaises(HTTPException) as ctx:
                main.delete_user_endpoint("user-1", requester_id="user-1")

        self.assertEqual(503, ctx.exception.status_code)
        self.assertEqual("Failed to load user datasets", ctx.exception.detail)
        delete_user.assert_not_called()

    def test_delete_user_cleans_up_owned_datasets_and_review(self):
        records = [
            {
                "hash": "owned-hash",
                "object_key": "datasets/owned/file.csv",
                "extra": {"owner_user_id": "user-1"},
            },
            {
                "hash": "other-hash",
                "object_key": "datasets/other/file.csv",
                "extra": {"owner_user_id": "user-2"},
            },
        ]

        with mock.patch.object(main, "list_records", return_value=records), mock.patch.object(
            main, "delete_object"
        ) as delete_object, mock.patch.object(main, "delete_record", return_value=True) as delete_record, mock.patch.object(
            main, "get_review_by_user_id", return_value=SimpleNamespace(id="review-1")
        ), mock.patch.object(main, "delete_review_db", return_value=True) as delete_review_db, mock.patch.object(
            main, "delete_user"
        ) as delete_user:
            result = main.delete_user_endpoint("user-1", requester_id="user-1")

        self.assertEqual({"ok": True}, result)
        delete_object.assert_called_once_with(key="datasets/owned/file.csv")
        delete_record.assert_called_once_with("owned-hash")
        delete_review_db.assert_called_once_with("review-1")
        delete_user.assert_called_once_with("user-1")


if __name__ == "__main__":
    unittest.main()
