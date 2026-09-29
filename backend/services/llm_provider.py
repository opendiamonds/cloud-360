"""LLM provider selection: the OpenRouter gateway, or the local Claude Code CLI.

Every LLM feature in Cloud-360 runs through claude-agent-sdk, which spawns the
`claude` CLI as a subprocess. That subprocess can reach a model two ways:

    openrouter   ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN point the CLI at
    (default)    OpenRouter. This is how the deployed stack runs: a container
                 has no interactive `claude login` to fall back on.

    cli          The CLI authenticates itself with whatever `claude login`
                 stored (macOS Keychain, ~/.claude). Local development only --
                 it needs a logged-in CLI on the same machine, and it spends
                 the developer's own Claude allowance rather than OpenRouter
                 credits.

The two are mutually exclusive at the environment level, and the exclusion is
**not symmetric**. A non-empty ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY takes
precedence over the CLI's own login and disables it; ANTHROPIC_BASE_URL
misroutes the CLI outright. Empty values are harmless -- leftover non-empty
ones are not. So cli mode DELETES those variables instead of blanking them.
Blanking is what the old code did, and it is not enough: `.env` is loaded with
override=True, so any value on disk or in the shell reaches the subprocess.

The ANTHROPIC_DEFAULT_*_MODEL family has to be deleted for the same reason,
and it is easy to miss because it neither authenticates nor routes. Those
variables define what the CLI's *aliases* resolve to: with
ANTHROPIC_DEFAULT_SONNET_MODEL=google/gemini-3.7-flash in the environment,
asking the CLI for `sonnet` gets you that OpenRouter slug sent to Anthropic,
which answers 404. That silently cancels the model normalisation below --
:func:`get_model_name` maps the leftover slug to a bare `sonnet`, and the alias
mapping maps it straight back.

Why an explicit switch rather than "no OpenRouter key means use the CLI": the
deployed stack must fail loudly when its secret is missing. Auto-detection
would turn a missing deploy secret into a confusing CLI auth error instead of
"OPENROUTER_API_KEY is not set".
"""

from __future__ import annotations

import logging
import os

from services.llm_limits import apply_agent_token_limits_to_env

logger = logging.getLogger("cloud360.llm_provider")

OPENROUTER = "openrouter"
CLI = "cli"
_VALID_PROVIDERS = (OPENROUTER, CLI)

OPENROUTER_BASE_URL = "https://openrouter.ai/api"

# Anything that routes or authenticates the CLI subprocess. In cli mode each of
# these must be ABSENT from the environment, not merely empty.
_CLI_AUTH_VARS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
)

# What the CLI's model aliases (sonnet/opus/haiku) resolve to. A gateway slug
# left here re-applies itself after normalisation and every request 404s.
_CLI_ALIAS_MODEL_VARS = (
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)

_CLI_CONFLICTING_VARS = _CLI_AUTH_VARS + _CLI_ALIAS_MODEL_VARS

# OpenRouter addresses models as "<vendor>/<model>"; the CLI uses bare names or
# aliases. A slug from the wrong provider is rejected at request time, which is
# far from where the misconfiguration lives.
_OPENROUTER_DEFAULT_MODEL = "google/gemini-3.7-flash"
_OPENROUTER_DEFAULT_REVIEW_MODEL = "anthropic/claude-3.5-haiku"
_CLI_DEFAULT_MODEL = "sonnet"
_CLI_DEFAULT_REVIEW_MODEL = "haiku"


def get_provider() -> str:
    """Which provider this process uses. Defaults to openrouter.

    An unrecognised value falls back to openrouter with a warning rather than
    raising: a typo in one optional variable should not stop the whole API from
    starting, and the fallback still produces the explicit "key not set" error
    from :func:`auth_error_message` if nothing is configured.
    """
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not raw:
        return OPENROUTER
    if raw not in _VALID_PROVIDERS:
        logger.warning(
            "LLM_PROVIDER=%r 不是有效值（可用：%s），退回 %s",
            raw,
            "、".join(_VALID_PROVIDERS),
            OPENROUTER,
        )
        return OPENROUTER
    return raw


def configure_provider_env() -> None:
    """Prepare the process environment for the selected provider.

    Safe to call repeatedly; both the startup hook and each request call it.
    """
    if get_provider() == CLI:
        _configure_cli_env()
    else:
        _configure_openrouter_env()


def _configure_cli_env() -> None:
    removed = [name for name in _CLI_CONFLICTING_VARS if os.environ.pop(name, None) is not None]
    if removed:
        # Worth a log line: the developer put these somewhere (.env or shell)
        # and would otherwise have no idea they are being ignored.
        logger.info(
            "LLM_PROVIDER=cli：已移除 %s，改用 claude CLI 自帶的登入認證",
            "、".join(removed),
        )
    apply_agent_token_limits_to_env()


def _configure_openrouter_env() -> None:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not openrouter_key:
        return

    os.environ.setdefault("ANTHROPIC_BASE_URL", OPENROUTER_BASE_URL)
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        os.environ["ANTHROPIC_AUTH_TOKEN"] = openrouter_key
    # Must be empty, or the SDK may reach Anthropic directly instead of OpenRouter.
    os.environ["ANTHROPIC_API_KEY"] = ""

    if not os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL"):
        os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = os.environ.get(
            "LLM_MODEL", _OPENROUTER_DEFAULT_MODEL
        )

    apply_agent_token_limits_to_env()


def llm_auth_ready() -> bool:
    """Whether an LLM call can be attempted at all.

    In cli mode the CLI owns its own credentials, so the backend cannot inspect
    them and does not try -- it lets the CLI answer for itself. In openrouter
    mode a credential must be present in the environment, because without one
    the request is guaranteed to fail upstream.
    """
    if get_provider() == CLI:
        return True
    return bool(
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    )


def auth_error_message() -> str:
    """The message shown when :func:`llm_auth_ready` is False."""
    return (
        "尚未設定 OPENROUTER_API_KEY（Agent SDK 經 OpenRouter 需要此金鑰）。"
        "本機開發也可改設 LLM_PROVIDER=cli，改用已登入的 claude CLI。"
    )


def _resolve(candidates: tuple[str, ...], default: str, *, provider: str) -> str:
    for value in candidates:
        value = (value or "").strip()
        if not value:
            continue
        if provider == CLI and "/" in value:
            # An OpenRouter slug left over in .env would make every cli-mode
            # request fail at the CLI with an opaque model error.
            logger.info(
                "LLM_PROVIDER=cli：忽略 gateway 格式的模型名稱 %r，改用 %r",
                value,
                default,
            )
            continue
        return value
    return default


def _sonnet_alias_candidate(provider: str) -> tuple[str, ...]:
    """ANTHROPIC_DEFAULT_SONNET_MODEL as a model source, where that is meaningful.

    Only under openrouter. Under cli the variable does not name the model to
    use -- it redefines what the `sonnet` alias points at -- so reading it as a
    model name would reintroduce the very slug :func:`_configure_cli_env`
    deletes, and would do so even before that function has run.
    """
    if provider == CLI:
        return ()
    return (os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", ""),)


def get_model_name() -> str:
    """Model for the design/lens agents."""
    provider = get_provider()
    default = _CLI_DEFAULT_MODEL if provider == CLI else _OPENROUTER_DEFAULT_MODEL
    return _resolve(
        (os.environ.get("LLM_MODEL", ""),) + _sonnet_alias_candidate(provider),
        default,
        provider=provider,
    )


def get_review_model_name() -> str:
    """Model for A3 review suggestions; prefers a faster model."""
    provider = get_provider()
    default = _CLI_DEFAULT_REVIEW_MODEL if provider == CLI else _OPENROUTER_DEFAULT_REVIEW_MODEL
    return _resolve(
        (
            os.environ.get("REVIEW_LLM_MODEL", ""),
            os.environ.get("LLM_MODEL", ""),
        )
        + _sonnet_alias_candidate(provider),
        default,
        provider=provider,
    )
