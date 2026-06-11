import hashlib
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from models import Base, User
from users import store


class TestPasswordHashing(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.old_session_local = store.SessionLocal
        store.SessionLocal = self.session_factory

    def tearDown(self):
        store.SessionLocal = self.old_session_local
        Base.metadata.drop_all(bind=self.engine)

    def test_hash_uses_versioned_pbkdf2_format(self):
        password_hash = store._hash_password("correct horse battery staple")

        self.assertTrue(password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(store._verify_password("correct horse battery staple", password_hash))
        self.assertFalse(store._verify_password("wrong password", password_hash))

    def test_legacy_sha256_hash_is_upgraded_on_successful_login(self):
        legacy_hash = hashlib.sha256("secret".encode("utf-8")).hexdigest()
        with self.session_factory() as db:
            db.add(User(id="user-1", username="alice", email="alice@example.com", password_hash=legacy_hash))
            db.commit()

        self.assertTrue(store.verify_user_password("alice", "secret"))

        with self.session_factory() as db:
            new_hash = db.execute(select(User.password_hash).where(User.id == "user-1")).scalar_one()
        self.assertTrue(new_hash.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(legacy_hash, new_hash)
        self.assertTrue(store._verify_password("secret", new_hash))

    def test_legacy_sha256_hash_is_not_upgraded_on_failed_login(self):
        legacy_hash = hashlib.sha256("secret".encode("utf-8")).hexdigest()
        with self.session_factory() as db:
            db.add(User(id="user-1", username="alice", email="alice@example.com", password_hash=legacy_hash))
            db.commit()

        self.assertFalse(store.verify_user_password("alice", "wrong"))

        with self.session_factory() as db:
            unchanged_hash = db.execute(select(User.password_hash).where(User.id == "user-1")).scalar_one()
        self.assertEqual(legacy_hash, unchanged_hash)

    def test_user_store_crud_uses_database(self):
        public_user = store.create_user("alice", "ALICE@example.com", "secret", plan="business")
        self.assertNotIn("password_hash", public_user)
        self.assertEqual("business", public_user["plan"])

        loaded = store.get_user_by_username("alice")
        self.assertEqual("alice@example.com", loaded["email"])
        self.assertTrue(store.verify_user_password("alice", "secret"))

        updated = store.update_user_kyb_status(public_user["id"], "verified")
        self.assertEqual("verified", updated["kyb_status"])

        restricted = store.set_user_restricted(public_user["id"], True)
        self.assertTrue(restricted["restricted"])

        store.delete_user(public_user["id"])
        self.assertIsNone(store.get_user_by_id(public_user["id"]))


if __name__ == "__main__":
    unittest.main()
