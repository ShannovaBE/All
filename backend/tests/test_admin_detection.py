import os
import unittest

from auth.admin import is_admin


class TestAdminDetection(unittest.TestCase):
    def setUp(self) -> None:
        self._old_ids = os.environ.get("ADMIN_USER_IDS")
        self._old_names = os.environ.get("ADMIN_USERNAMES")
        return super().setUp()

    def tearDown(self) -> None:
        if self._old_ids is None:
            os.environ.pop("ADMIN_USER_IDS", None)
        else:
            os.environ["ADMIN_USER_IDS"] = self._old_ids

        if self._old_names is None:
            os.environ.pop("ADMIN_USERNAMES", None)
        else:
            os.environ["ADMIN_USERNAMES"] = self._old_names

        return super().tearDown()

    def test_admin_by_id(self):
        os.environ["ADMIN_USER_IDS"] = "u1,u2"
        os.environ["ADMIN_USERNAMES"] = ""
        self.assertTrue(is_admin(user_id="u2", username=None))
        self.assertFalse(is_admin(user_id="u3", username=None))

    def test_admin_by_username_case_insensitive(self):
        os.environ["ADMIN_USER_IDS"] = ""
        os.environ["ADMIN_USERNAMES"] = "Alice, Bob "
        self.assertTrue(is_admin(user_id="x", username="alice"))
        self.assertTrue(is_admin(user_id="x", username="BOB"))
        self.assertFalse(is_admin(user_id="x", username="carol"))


if __name__ == "__main__":
    unittest.main()

