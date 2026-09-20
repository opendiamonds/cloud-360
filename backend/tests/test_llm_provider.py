"""Tests for LLM provider selection (services.llm_provider).

The behaviour under test is what made the cli path unreachable before: the
guards demanded a non-empty credential, while a non-empty credential is exactly
what disables the CLI's own login. Each case below pins one half of that.
"""

import os
import unittest
from contextlib import contextmanager

import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import

from services.llm_provider import (
    CLI,
    OPENROUTER,
    auth_error_message,
    configure_provider_env,
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

    def test_reads_cli(self):
        with env(LLM_PROVIDER="cli"):
            self.assertEqual(get_provider(), CLI)

    def test_is_case_and_whitespace_insensitive(self):
        with env(LLM_PROVIDER="  CLI  "):
            self.assertEqual(get_provider(), CLI)

    def test_unknown_value_falls_back_to_openrouter(self):
        with env(LLM_PROVIDER="anthropic-direct"):
            with self.assertLogs("cloud360.llm_provider", level="WARNING"):
                self.assertEqual(get_provider(), OPENROUTER)


class CliModeClearsConflictingVars(unittest.TestCase):
    """A non-empty value in any of these disables the CLI's own login."""

    def test_deletes_rather_than_blanks(self):
        with env(
            LLM_PROVIDER="cli",
            ANTHROPIC_BASE_URL="https://openrouter.ai/api",
            ANTHROPIC_AUTH_TOKEN="sk-or-leftover",
            ANTHROPIC_API_KEY="sk-ant-leftover",
        ):
            configure_provider_env()
            # Absent, not empty: an empty string would still be inherited by the
            # subprocess, and an empty ANTHROPIC_BASE_URL is worse than none.
            for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
                self.assertNotIn(name, os.environ, f"{name} should be removed entirely")

    def test_clears_even_when_openrouter_key_is_present(self):
        with env(LLM_PROVIDER="cli", OPENROUTER_API_KEY="sk-or-real"):
            configure_provider_env()
            self.assertNotIn("ANTHROPIC_AUTH_TOKEN", os.environ)

    def test_is_idempotent(self):
        with env(LLM_PROVIDER="cli", ANTHROPIC_API_KEY="x"):
            configure_provider_env()
            configure_provider_env()
            self.assertNotIn("ANTHROPIC_API_KEY", os.environ)

    def test_deletes_the_alias_model_family(self):
        """These name what `sonnet`/`opus`/`haiku` resolve to, not the model.

        Observed 404: with ANTHROPIC_DEFAULT_SONNET_MODEL left at an OpenRouter
        slug, `claude -p ... --model sonnet` reported "There's an issue with the
        selected model (anthropic/claude-sonnet-4.6)". Normalising the model
        name is not enough while the alias maps it back.
        """
        with env(
            LLM_PROVIDER="cli",
            ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-sonnet-4.6",
            ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic/claude-opus-4.1",
            ANTHROPIC_DEFAULT_HAIKU_MODEL="anthropic/claude-3.5-haiku",
        ):
            configure_provider_env()
            for name in (
                "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            ):
                self.assertNotIn(name, os.environ, f"{name} should be removed entirely")

    def test_no_gateway_slug_survives_anywhere(self):
        """The real `backend/.env` shape that produced the 404, end to end."""
        with env(
            LLM_PROVIDER="cli",
            ANTHROPIC_BASE_URL="https://openrouter.ai/api",
            ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-sonnet-4.6",
            LLM_MODEL="anthropic/claude-sonnet-4.6",
        ):
            configure_provider_env()
            leftovers = {
                name: value
                for name, value in os.environ.items()
                if name.startswith("ANTHROPIC_") and "/" in value
            }
            self.assertEqual(leftovers, {}, "a gateway slug reached the CLI subprocess")
            self.assertEqual(get_model_name(), "sonnet")


class OpenRouterModeMapsTheKey(unittest.TestCase):
    def test_maps_key_to_auth_token(self):
        with env(LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-real"):
            configure_provider_env()
            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "sk-or-real")
            self.assertEqual(os.environ["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "")

    def test_touches_nothing_without_a_key(self):
        with env(LLM_PROVIDER="openrouter"):
            configure_provider_env()
            self.assertNotIn("ANTHROPIC_AUTH_TOKEN", os.environ)

    def test_does_not_overwrite_an_explicit_auth_token(self):
        with env(
            LLM_PROVIDER="openrouter",
            OPENROUTER_API_KEY="sk-or-real",
            ANTHROPIC_AUTH_TOKEN="explicit",
        ):
            configure_provider_env()
            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "explicit")


class AuthReadiness(unittest.TestCase):
    def test_cli_is_always_ready(self):
        """The CLI owns its credentials; the backend cannot and must not judge."""
        with env(LLM_PROVIDER="cli"):
            self.assertTrue(llm_auth_ready())

    def test_openrouter_needs_a_credential(self):
        with env(LLM_PROVIDER="openrouter"):
            self.assertFalse(llm_auth_ready())

    def test_openrouter_accepts_either_variable(self):
        with env(LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="k"):
            self.assertTrue(llm_auth_ready())
        with env(LLM_PROVIDER="openrouter", ANTHROPIC_AUTH_TOKEN="t"):
            self.assertTrue(llm_auth_ready())

    def test_whitespace_only_is_not_a_credential(self):
        with env(LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="   "):
            self.assertFalse(llm_auth_ready())

    def test_error_message_names_both_ways_out(self):
        message = auth_error_message()
        self.assertIn("OPENROUTER_API_KEY", message)
        self.assertIn("LLM_PROVIDER=cli", message)


class ModelSelection(unittest.TestCase):
    def test_provider_specific_defaults(self):
        with env(LLM_PROVIDER="openrouter"):
            self.assertEqual(get_model_name(), "google/gemini-3.7-flash")
        with env(LLM_PROVIDER="cli"):
            self.assertEqual(get_model_name(), "sonnet")

    def test_explicit_model_wins(self):
        with env(LLM_PROVIDER="cli", LLM_MODEL="opus"):
            self.assertEqual(get_model_name(), "opus")

    def test_cli_ignores_a_gateway_slug(self):
        """A slug left over from openrouter mode would fail at the CLI."""
        with env(LLM_PROVIDER="cli", LLM_MODEL="anthropic/claude-sonnet-4.6"):
            with self.assertLogs("cloud360.llm_provider", level="INFO"):
                self.assertEqual(get_model_name(), "sonnet")

    def test_openrouter_keeps_the_gateway_slug(self):
        with env(LLM_PROVIDER="openrouter", LLM_MODEL="anthropic/claude-opus-4.1"):
            self.assertEqual(get_model_name(), "anthropic/claude-opus-4.1")

    def test_openrouter_falls_back_to_the_sonnet_alias_variable(self):
        with env(
            LLM_PROVIDER="openrouter",
            ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-opus-4.1",
        ):
            self.assertEqual(get_model_name(), "anthropic/claude-opus-4.1")

    def test_cli_never_reads_the_sonnet_alias_variable(self):
        """Even a bare name there means "what `sonnet` resolves to", not "use this".

        Asserted without calling configure_provider_env() on purpose: the model
        choice must not depend on whether the environment has been cleaned yet.
        """
        with env(LLM_PROVIDER="cli", ANTHROPIC_DEFAULT_SONNET_MODEL="opus"):
            self.assertEqual(get_model_name(), "sonnet")
        with env(LLM_PROVIDER="cli", ANTHROPIC_DEFAULT_SONNET_MODEL="opus"):
            self.assertEqual(get_review_model_name(), "haiku")

    def test_review_model_prefers_its_own_override(self):
        with env(LLM_PROVIDER="cli", LLM_MODEL="opus", REVIEW_LLM_MODEL="haiku"):
            self.assertEqual(get_review_model_name(), "haiku")

    def test_review_model_defaults_per_provider(self):
        with env(LLM_PROVIDER="cli"):
            self.assertEqual(get_review_model_name(), "haiku")
        with env(LLM_PROVIDER="openrouter"):
            self.assertEqual(get_review_model_name(), "anthropic/claude-3.5-haiku")


if __name__ == "__main__":
    unittest.main()
