"""Unit tests for auth: password hashing, JWT create/decode/expiry."""

from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

import jwt
from hypothesis import given, settings, strategies as st
from starlette.testclient import TestClient

from database import get_db
from main import app
from services import auth
from services.auth import (
    ALGORITHM,
    INSECURE_DEV_SECRET,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)
from tests.helpers import close_session, make_session, make_user


class TestPasswordHashing(unittest.TestCase):
    def test_hash_and_verify_round_trip(self):
        hashed = get_password_hash("admin123")
        self.assertNotEqual(hashed, "admin123")
        self.assertTrue(verify_password("admin123", hashed))
        self.assertFalse(verify_password("wrong", hashed))

    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=33, max_codepoint=126)))
    @settings(max_examples=20, deadline=None)
    def test_verify_accepts_own_hash(self, password: str):
        # bcrypt truncates >72 bytes; keep ASCII printable within that bound
        hashed = get_password_hash(password)
        self.assertTrue(verify_password(password, hashed))


class TestAccessToken(unittest.TestCase):
    def test_create_and_decode(self):
        token = create_access_token({"sub": "alex"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        self.assertEqual(payload["sub"], "alex")
        self.assertIn("exp", payload)

    def test_expired_token_rejected(self):
        token = create_access_token(
            {"sub": "alex"}, expires_delta=timedelta(seconds=-1)
        )
        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "alex"})
        bad = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
        with self.assertRaises(jwt.PyJWTError):
            jwt.decode(bad, SECRET_KEY, algorithms=[ALGORITHM])


class TestSecretConfiguration(unittest.TestCase):
    def test_local_env_allows_dev_secret(self):
        with patch.dict(auth.os.environ, {"APP_ENV": "local"}, clear=True):
            self.assertEqual(auth._resolve_secret_key(), INSECURE_DEV_SECRET)

    def test_non_local_env_requires_jwt_secret(self):
        with patch.dict(auth.os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaises(RuntimeError):
                auth._resolve_secret_key()

    def test_non_local_env_uses_configured_secret(self):
        with patch.dict(
            auth.os.environ,
            {"APP_ENV": "production", "JWT_SECRET": "configured-secret"},
            clear=True,
        ):
            self.assertEqual(auth._resolve_secret_key(), "configured-secret")


class TestLoginActivity(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.user = make_user(
            self.db,
            username="admin",
            role="Platform_Admin",
            password_hash=get_password_hash("admin123"),
        )
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    def test_successful_login_records_last_activity(self):
        self.assertIsNone(self.user.last_activity_at)

        res = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )

        self.assertEqual(res.status_code, 200)
        self.db.refresh(self.user)
        self.assertIsNotNone(self.user.last_activity_at)


class TestGetCurrentUser(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.user = make_user(
            self.db,
            username="alex",
            role="Project_Architect",
            password_hash=get_password_hash("secret"),
        )
        self.inactive = make_user(
            self.db,
            username="ghost",
            role="Developer",
            password_hash=get_password_hash("secret"),
            is_active=False,
        )

    def tearDown(self):
        close_session(self.db)

    def _creds(self, token: str) -> MagicMock:
        c = MagicMock()
        c.credentials = token
        return c

    def test_valid_token_returns_user(self):
        token = create_access_token({"sub": "alex"})
        result = auth.get_current_user(self._creds(token), self.db)
        self.assertEqual(result.username, "alex")

    def test_missing_sub_raises_401(self):
        token = create_access_token({"role": "x"})  # no sub
        # create_access_token always adds exp; decode will succeed but sub is None
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(self._creds(token), self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_unknown_user_raises_401(self):
        from fastapi import HTTPException

        token = create_access_token({"sub": "nobody"})
        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(self._creds(token), self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_inactive_user_raises_403(self):
        from fastapi import HTTPException

        token = create_access_token({"sub": "ghost"})
        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(self._creds(token), self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_invalid_token_raises_401(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(self._creds("not.a.jwt"), self.db)
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
