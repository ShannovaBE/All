import unittest
from datetime import datetime, timezone
from unittest import mock

import retention


class TestRetention(unittest.TestCase):
    def test_build_retention_policy_sets_expiry(self):
        now = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)

        policy, expires_at = retention.build_retention_policy(now=now, days=30)

        self.assertEqual(30, policy["retention_days"])
        self.assertEqual("2026-07-08T12:00:00Z", expires_at)
        self.assertEqual("restrict_metadata_and_disable_download", policy["expiry_action"])

    def test_dry_run_lists_due_records_without_mutation(self):
        due_records = [
            {
                "hash": "dataset-1",
                "filename": "data.csv",
                "retention_expires_at": "2026-06-01T00:00:00Z",
                "object_key": "datasets/dataset-1/data.csv",
            }
        ]

        with mock.patch.object(retention, "list_retention_due_records", return_value=due_records), mock.patch.object(
            retention, "update_record_controls"
        ) as update_controls:
            result = retention.run_retention_sweep(now=datetime(2026, 6, 8, tzinfo=timezone.utc), dry_run=True)

        self.assertEqual(1, result["due_count"])
        self.assertEqual("would_restrict", result["items"][0]["action"])
        update_controls.assert_not_called()

    def test_enforcing_retention_restricts_due_records(self):
        due_records = [
            {
                "hash": "dataset-1",
                "filename": "data.csv",
                "retention_expires_at": "2026-06-01T00:00:00Z",
                "object_key": "datasets/dataset-1/data.csv",
            }
        ]

        with mock.patch.object(retention, "list_retention_due_records", return_value=due_records), mock.patch.object(
            retention, "update_record_controls"
        ) as update_controls:
            result = retention.run_retention_sweep(
                now=datetime(2026, 6, 8, tzinfo=timezone.utc),
                dry_run=False,
                delete_objects=False,
            )

        self.assertEqual(1, result["due_count"])
        self.assertEqual("restricted", result["items"][0]["action"])
        update_controls.assert_called_once()
        _, kwargs = update_controls.call_args
        self.assertEqual("retention_expired", kwargs["restriction_status"])
        self.assertIn("retention", kwargs["compliance_evidence"])


if __name__ == "__main__":
    unittest.main()
