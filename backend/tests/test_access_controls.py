import unittest
from unittest import mock

from fastapi import HTTPException

import main


class TestDatasetAccessControls(unittest.TestCase):
    def test_public_policy_allows_free_without_kyb(self):
        policy = main._build_access_policy(category="retail", pii_report={"redacted_cells": 0})
        self.assertEqual("internal", policy["sensitivity"])
        self.assertEqual("basic", policy["min_plan"])
        self.assertFalse(policy["kyb_required"])

    def test_pii_escalates_policy_to_sensitive(self):
        policy = main._build_access_policy(category="finance", pii_report={"redacted_cells": 2})
        self.assertEqual("sensitive", policy["sensitivity"])
        self.assertEqual("business", policy["min_plan"])
        self.assertTrue(policy["kyb_required"])

    def test_owner_bypasses_buyer_plan_checks(self):
        record = {
            "owner": "user-1",
            "restriction_status": "active",
            "access_policy": {"sensitivity": "sensitive", "min_plan": "business", "kyb_required": True},
        }
        user = {"id": "user-1", "username": "owner", "plan": "free", "kyb_status": "pending"}
        with mock.patch.object(main, "get_user_by_id", return_value=user):
            self.assertEqual(user, main._require_access_to_dataset(record=record, requester_id="user-1"))

    def test_lower_plan_buyer_is_denied(self):
        record = {
            "owner": "seller-1",
            "restriction_status": "active",
            "access_policy": {"sensitivity": "sensitive", "min_plan": "business", "kyb_required": True},
        }
        user = {"id": "buyer-1", "username": "buyer", "plan": "basic", "kyb_status": "verified"}
        with mock.patch.object(main, "get_user_by_id", return_value=user):
            with self.assertRaises(HTTPException) as ctx:
                main._require_access_to_dataset(record=record, requester_id="buyer-1")
        self.assertEqual(403, ctx.exception.status_code)

    def test_sensitive_dataset_requires_kyb(self):
        record = {
            "owner": "seller-1",
            "restriction_status": "active",
            "access_policy": {"sensitivity": "sensitive", "min_plan": "business", "kyb_required": True},
        }
        user = {"id": "buyer-1", "username": "buyer", "plan": "business", "kyb_status": "pending"}
        with mock.patch.object(main, "get_user_by_id", return_value=user):
            with self.assertRaises(HTTPException) as ctx:
                main._require_access_to_dataset(record=record, requester_id="buyer-1")
        self.assertEqual(403, ctx.exception.status_code)

    def test_restricted_dataset_is_locked(self):
        record = {"owner": "seller-1", "restriction_status": "restricted", "access_policy": {}}
        with self.assertRaises(HTTPException) as ctx:
            main._require_access_to_dataset(record=record, requester_id="buyer-1")
        self.assertEqual(423, ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
