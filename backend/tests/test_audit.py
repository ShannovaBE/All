import unittest
from unittest import mock

from audit import _safe_metadata, write_audit_event


class TestAuditLogging(unittest.TestCase):
    def test_safe_metadata_redacts_secret_like_keys(self):
        safe = _safe_metadata(
            {
                "filename": "dataset.csv",
                "api_key": "should-not-log",
                "password": "should-not-log",
                "nested": {"token": "left-alone-as-nested-context"},
            }
        )

        self.assertEqual("dataset.csv", safe["filename"])
        self.assertEqual("[REDACTED]", safe["api_key"])
        self.assertEqual("[REDACTED]", safe["password"])
        self.assertEqual({"token": "left-alone-as-nested-context"}, safe["nested"])

    def test_write_audit_event_does_not_raise_when_db_fails(self):
        with mock.patch("audit.SessionLocal", side_effect=RuntimeError("db down")):
            write_audit_event(
                action="DOWNLOAD_DATASET",
                actor_id="user-1",
                resource="dataset-1",
                purpose="buyer_download",
                metadata={"secret": "hidden"},
            )


if __name__ == "__main__":
    unittest.main()
