"""Security tests for database bootstrap defaults."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import tests.helpers  # noqa: F401 — path / psycopg2 setup
from database import (
    _allow_insecure_default_personas,
    _allow_insecure_default_users,
    _bootstrap_admin_password,
)


class DatabaseBootstrapSecurityTest(unittest.TestCase):
    def test_local_env_allows_demo_seed(self):
        with patch.dict("os.environ", {"APP_ENV": "local"}, clear=True):
            self.assertTrue(_allow_insecure_default_users())
            self.assertTrue(_allow_insecure_default_personas())
            self.assertEqual(_bootstrap_admin_password(), "admin123")

    def test_test_env_bootstraps_admin_without_demo_personas(self):
        with patch.dict("os.environ", {"APP_ENV": "test"}, clear=True):
            self.assertTrue(_allow_insecure_default_users())
            self.assertFalse(_allow_insecure_default_personas())
            self.assertEqual(_bootstrap_admin_password(), "admin123")

    def test_production_env_blocks_fixed_demo_seed_by_default(self):
        with patch.dict("os.environ", {"APP_ENV": "production"}, clear=True):
            self.assertFalse(_allow_insecure_default_users())
            self.assertFalse(_allow_insecure_default_personas())
            self.assertIsNone(_bootstrap_admin_password())

    def test_production_env_can_use_explicit_bootstrap_password(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "CLOUD360_BOOTSTRAP_ADMIN_PASSWORD": "one-time-secret",
            },
            clear=True,
        ):
            self.assertFalse(_allow_insecure_default_users())
            self.assertEqual(_bootstrap_admin_password(), "one-time-secret")

    def test_non_local_demo_seed_requires_explicit_opt_in(self):
        with patch.dict(
            "os.environ",
            {"APP_ENV": "staging", "ALLOW_INSECURE_DEFAULT_USERS": "true"},
            clear=True,
        ):
            self.assertTrue(_allow_insecure_default_users())

    def test_non_local_persona_seed_requires_explicit_opt_in(self):
        with patch.dict(
            "os.environ",
            {"APP_ENV": "staging", "ALLOW_INSECURE_DEFAULT_PERSONAS": "true"},
            clear=True,
        ):
            self.assertTrue(_allow_insecure_default_personas())


if __name__ == "__main__":
    unittest.main()
