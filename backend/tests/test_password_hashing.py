import hashlib
import unittest
from unittest import mock

from users import store


class TestPasswordHashing(unittest.TestCase):
    def test_hash_uses_versioned_pbkdf2_format(self):
        password_hash = store._hash_password("correct horse battery staple")

        self.assertTrue(password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(store._verify_password("correct horse battery staple", password_hash))
        self.assertFalse(store._verify_password("wrong password", password_hash))

    def test_legacy_sha256_hash_is_upgraded_on_successful_login(self):
        legacy_hash = hashlib.sha256("secret".encode("utf-8")).hexdigest()
        users = {
            "user-1": {
                "id": "user-1",
                "username": "alice",
                "email": "alice@example.com",
                "password_hash": legacy_hash,
            }
        }

        with mock.patch.object(store, "_load_all_users", return_value=users), mock.patch.object(
            store, "_save_all_users"
        ) as save_all:
            self.assertTrue(store.verify_user_password("alice", "secret"))

        saved_users = save_all.call_args.args[0]
        new_hash = saved_users["user-1"]["password_hash"]
        self.assertTrue(new_hash.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(legacy_hash, new_hash)
        self.assertTrue(store._verify_password("secret", new_hash))

    def test_legacy_sha256_hash_is_not_upgraded_on_failed_login(self):
        legacy_hash = hashlib.sha256("secret".encode("utf-8")).hexdigest()
        users = {
            "user-1": {
                "id": "user-1",
                "username": "alice",
                "email": "alice@example.com",
                "password_hash": legacy_hash,
            }
        }

        with mock.patch.object(store, "_load_all_users", return_value=users), mock.patch.object(
            store, "_save_all_users"
        ) as save_all:
            self.assertFalse(store.verify_user_password("alice", "wrong"))

        save_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
