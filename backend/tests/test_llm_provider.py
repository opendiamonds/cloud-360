"""Tests for LLM provider selection (services.llm_provider).

@purpose Pin the retirement of `LLM_PROVIDER=cli` and the single remaining
         (OpenRouter) credential/model resolution path.
@given   A clean environment with only the MANAGED variables this module reads.
@step    Set LLM_PROVIDER and the credential/model variables; assert what
         get_provider / configure_provider_env / llm_auth_ready resolve to.
@pass    cli resolves to openrouter with an ERROR log and deletes nothing;
         credentials survive; llm_auth_ready reflects whether a key is present.
@story   RAID R-11 (260920-orchestration-brain)

The behaviour under test used to be the cli-vs-openrouter split: cli mode
DELETED every credential variable so the `claude` CLI subprocess could use its
own login. After the A3 migration (`ut` commit `b4f0cdc`) nothing spawns that
subprocess, while `design_agent.py` reads `ANTHROPIC_AUTH_TOKEN` directly — so
cli mode deleted the only credential the live path had, and `llm_auth_ready()`
still returned True. The health check said ready and the call failed with an
empty key. These cases pin that the deletion is gone and that the retired value
is still recognised rather than treated as a typo.
"""

import os
import unittest
from contextlib import contextmanager

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

from services.llm_provider import (
    OPENROUTER,
    auth_error_message,
    configure_provider_env,
    get_design_model_name,
    get_model_name,
    get_provider,
    get_review_model_name,
    llm_auth_ready,
)

MANAGED = (
    "LLM_PROVIDER",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "LLM_MODEL",
    "DESIGN_LLM_MODEL",
    "REVIEW_LLM_MODEL",
)


@contextmanager
def env(**values):
    """Run with exactly `values` set among MANAGED; everything else removed."""
    saved = {k: os.environ.get(k) for k in MANAGED}
    try:
        for k in MANAGED:
            os.environ.pop(k, None)
        for k, v in values.items():
            os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class ProviderSelection(unittest.TestCase):
    def test_defaults_to_openrouter_when_unset(self):
        with env():
            self.assertEqual(get_provider(), OPENROUTER)

    def test_is_case_and_whitespace_insensitive(self):
        with env(LLM_PROVIDER="  OpenRouter  "):
            self.assertEqual(get_provider(), OPENROUTER)

    def test_unknown_value_falls_back_to_openrouter(self):
        with env(LLM_PROVIDER="bedrock"):
            with self.assertLogs("cloud360.llm_provider", level="WARNING") as logs:
                self.assertEqual(get_provider(), OPENROUTER)
            self.assertNotIn("ERROR", logs.output[0].split(":")[0])


class RetiredCliMode(unittest.TestCase):
    """`LLM_PROVIDER=cli` is recognised, resolves to openrouter, and says why."""

    def test_resolves_to_openrouter(self):
        with env(LLM_PROVIDER="cli"):
            self.assertEqual(get_provider(), OPENROUTER)

    def test_logs_at_error_not_as_a_typo(self):
        with env(LLM_PROVIDER="cli"):
            with self.assertLogs("cloud360.llm_provider", level="ERROR") as logs:
                get_provider()
        joined = "\n".join(logs.output)
        self.assertIn("已退役", joined)
        self.assertIn("R-11", joined)
        # The generic typo wording must NOT appear: an existing setting is not a typo.
        self.assertNotIn("不是有效值", joined)

    def test_no_longer_deletes_credentials(self):
        """The defect itself: cli mode used to pop these, leaving an empty key.

        `design_agent.py` builds its client from ANTHROPIC_AUTH_TOKEN /
        ANTHROPIC_BASE_URL, so deleting them is what made the call fail.
        """
        with env(
            LLM_PROVIDER="cli",
            OPENROUTER_API_KEY="sk-or-real",
            ANTHROPIC_AUTH_TOKEN="sk-token",
            ANTHROPIC_BASE_URL="https://openrouter.ai/api",
        ):
            configure_provider_env()
            self.assertEqual(os.environ.get("ANTHROPIC_AUTH_TOKEN"), "sk-token")
            self.assertEqual(os.environ.get("ANTHROPIC_BASE_URL"), "https://openrouter.ai/api")
            self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "sk-or-real")

    def test_auth_ready_no_longer_lies(self):
        """It used to return True unconditionally under cli, with no credential."""
        with env(LLM_PROVIDER="cli"):
            self.assertFalse(llm_auth_ready())
        with env(LLM_PROVIDER="cli", OPENROUTER_API_KEY="sk-or-real"):
            self.assertTrue(llm_auth_ready())

    def test_alias_model_family_survives(self):
        with env(LLM_PROVIDER="cli", ANTHROPIC_DEFAULT_SONNET_MODEL="google/gemini-3.7-flash"):
            configure_provider_env()
            self.assertEqual(
                os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL"), "google/gemini-3.7-flash"
            )


class OpenRouterEnv(unittest.TestCase):
    def test_maps_key_to_auth_token(self):
        with env(OPENROUTER_API_KEY="sk-or-real"):
            configure_provider_env()
            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "sk-or-real")
            self.assertEqual(os.environ["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "")

    def test_touches_nothing_without_a_key(self):
        with env():
            configure_provider_env()
            self.assertIsNone(os.environ.get("ANTHROPIC_BASE_URL"))
            self.assertIsNone(os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    def test_does_not_overwrite_an_explicit_auth_token(self):
        with env(OPENROUTER_API_KEY="sk-or-real", ANTHROPIC_AUTH_TOKEN="sk-explicit"):
            configure_provider_env()
            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "sk-explicit")

    def test_is_idempotent(self):
        with env(OPENROUTER_API_KEY="sk-or-real"):
            configure_provider_env()
            first = dict(os.environ)
            configure_provider_env()
            for k in MANAGED:
                self.assertEqual(os.environ.get(k), first.get(k), k)


class AuthReadiness(unittest.TestCase):
    def test_needs_a_credential(self):
        with env():
            self.assertFalse(llm_auth_ready())

    def test_accepts_either_variable(self):
        with env(OPENROUTER_API_KEY="sk-or-real"):
            self.assertTrue(llm_auth_ready())
        with env(ANTHROPIC_AUTH_TOKEN="sk-token"):
            self.assertTrue(llm_auth_ready())

    def test_whitespace_only_is_not_a_credential(self):
        with env(OPENROUTER_API_KEY="   "):
            self.assertFalse(llm_auth_ready())

    def test_error_message_names_the_one_way_out(self):
        message = auth_error_message()
        self.assertIn("OPENROUTER_API_KEY", message)
        # It must no longer offer cli mode as an alternative.
        self.assertNotIn("LLM_PROVIDER=cli", message)


class ModelNames(unittest.TestCase):
    def test_defaults(self):
        with env():
            self.assertEqual(get_model_name(), "google/gemini-3.7-flash")
            self.assertEqual(get_design_model_name(), "google/gemini-2.5-flash")
            self.assertEqual(get_review_model_name(), "google/gemini-3.7-flash")

    def test_explicit_model_wins(self):
        with env(LLM_MODEL="google/gemini-2.5-pro"):
            self.assertEqual(get_model_name(), "google/gemini-2.5-pro")

    def test_keeps_the_gateway_slug(self):
        """No provider strips vendor/model shapes any more."""
        with env(LLM_MODEL="google/gemini-2.5-flash"):
            self.assertEqual(get_model_name(), "google/gemini-2.5-flash")

    def test_falls_back_to_the_sonnet_alias_variable(self):
        with env(ANTHROPIC_DEFAULT_SONNET_MODEL="google/gemini-2.5-pro"):
            self.assertEqual(get_model_name(), "google/gemini-2.5-pro")

    def test_design_model_has_its_own_override(self):
        with env(LLM_MODEL="google/gemini-2.5-pro", DESIGN_LLM_MODEL="google/gemini-3.7-flash"):
            self.assertEqual(get_design_model_name(), "google/gemini-3.7-flash")
            self.assertEqual(get_model_name(), "google/gemini-2.5-pro")

    def test_review_model_prefers_its_own_override(self):
        with env(LLM_MODEL="google/gemini-2.5-pro", REVIEW_LLM_MODEL="google/gemini-3.7-flash"):
            self.assertEqual(get_review_model_name(), "google/gemini-3.7-flash")

    def test_review_model_falls_back_to_llm_model(self):
        with env(LLM_MODEL="google/gemini-2.5-pro"):
            self.assertEqual(get_review_model_name(), "google/gemini-2.5-pro")


if __name__ == "__main__":
    unittest.main()
