"""LLM provider selection and environment preparation.

Every LLM feature in Cloud-360 reaches its model through **OpenRouter over
HTTP** (`langchain_openai` / `langchain_anthropic` clients configured from the
environment). There is no subprocess in this path.

That was not always true. Until the A3 migration (`ut` commit `b4f0cdc`,
2026-10-01) the LLM features ran through `claude-agent-sdk`, which spawned the
`claude` CLI as a subprocess, and that subprocess could authenticate itself
with whatever `claude login` had stored. `LLM_PROVIDER=cli` existed for exactly
that: it DELETED `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` /
`ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` from the environment so they could
not override the CLI's own login. Deleting rather than blanking mattered,
because `.env` is loaded with `override=True`.

**That mode is retired, because the thing it authenticated no longer exists.**
After the migration nothing spawns a subprocess (`create_subprocess_exec` and
`Popen` have zero occurrences under `backend/`), while `design_agent.py` builds
its client by reading `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` directly.
So cli mode deleted the only credentials the new code path had, and
`llm_auth_ready()` still answered `True` — the health check reported ready and
the feature failed at call time with an empty key. A silent failure, recorded
as RAID R-11 in the 260920-orchestration-brain intent record.

`LLM_PROVIDER=cli` is therefore still RECOGNISED, so that an existing setting
does not pass as a typo, but it resolves to openrouter and logs at ERROR what
happened and why. It does not refuse to start: this module's contract (see
:func:`get_provider`) is that one mis-set optional variable must not stop the
API from booting, and the openrouter path already produces an explicit,
actionable "key not set" error through :func:`auth_error_message` when no
credential is present. Failing at that point names the real problem; refusing
to boot would turn a stale config line into an outage.
"""

import logging
import os

from services.llm_limits import apply_agent_token_limits_to_env

logger = logging.getLogger("cloud360.llm_provider")

OPENROUTER = "openrouter"
_VALID_PROVIDERS = (OPENROUTER,)

# Recognised, but no longer selectable. Kept so an existing `LLM_PROVIDER=cli`
# gets the migration message instead of the generic "not a valid value".
_RETIRED_PROVIDERS = ("cli",)

OPENROUTER_BASE_URL = "https://openrouter.ai/api"

# OpenRouter addresses models as "<vendor>/<model>".
_OPENROUTER_DEFAULT_MODEL = "google/gemini-3.7-flash"
_OPENROUTER_DEFAULT_REVIEW_MODEL = "google/gemini-3.7-flash"
_OPENROUTER_DEFAULT_DESIGN_MODEL = "google/gemini-2.5-flash"


def get_provider() -> str:
    """Which provider this process uses. Always openrouter.

    A retired value logs at ERROR and a typo logs at WARNING; neither raises.
    A mis-set optional variable should not stop the whole API from starting,
    and the openrouter path still produces the explicit "key not set" error
    from :func:`auth_error_message` if nothing is configured.
    """
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not raw:
        return OPENROUTER
    if raw in _RETIRED_PROVIDERS:
        logger.error(
            "LLM_PROVIDER=%r 已退役，改用 %s。"
            "A3 遷移到 LangGraph／OpenRouter 之後已無 claude CLI 子行程可認證，"
            "而該模式會刪除 ANTHROPIC_AUTH_TOKEN／ANTHROPIC_BASE_URL——"
            "留著它會讓金鑰被清空而健康檢查仍回報正常（RAID R-11）。"
            "請改設 OPENROUTER_API_KEY 並移除這一行。",
            raw,
            OPENROUTER,
        )
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
    """Prepare the process environment for OpenRouter.

    Safe to call repeatedly; both the startup hook and each request call it.
    Calling :func:`get_provider` here (rather than ignoring it) is what makes a
    retired or invalid setting visible in the logs at startup.
    """
    get_provider()
    _configure_openrouter_env()


def _configure_openrouter_env() -> None:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not openrouter_key:
        return

    os.environ.setdefault("ANTHROPIC_BASE_URL", OPENROUTER_BASE_URL)
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        os.environ["ANTHROPIC_AUTH_TOKEN"] = openrouter_key
    # Must be empty, or a client may reach Anthropic directly instead of OpenRouter.
    os.environ["ANTHROPIC_API_KEY"] = ""

    if not os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL"):
        os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = os.environ.get(
            "LLM_MODEL", _OPENROUTER_DEFAULT_MODEL
        )

    apply_agent_token_limits_to_env()


def llm_auth_ready() -> bool:
    """Whether an LLM call can be attempted at all.

    A credential must be present in the environment, because without one the
    request is guaranteed to fail upstream. There is no longer a mode that owns
    its own credentials outside this process.
    """
    return bool(
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    )


def auth_error_message() -> str:
    """The message shown when :func:`llm_auth_ready` is False."""
    return (
        "尚未設定 OPENROUTER_API_KEY（LLM 呼叫經 OpenRouter 需要此金鑰）。"
        "請在 backend/.env 設定它。"
    )


def _resolve(candidates: tuple[str, ...], default: str) -> str:
    for value in candidates:
        value = (value or "").strip()
        if not value:
            continue
        return value
    return default


def get_design_model_name() -> str:
    """Model specifically for the A1 design/drawing agent."""
    return _resolve(
        (os.environ.get("DESIGN_LLM_MODEL", ""),),
        _OPENROUTER_DEFAULT_DESIGN_MODEL,
    )


def get_model_name() -> str:
    """Model for general agents (e.g. WA lens engine)."""
    return _resolve(
        (
            os.environ.get("LLM_MODEL", ""),
            os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", ""),
        ),
        _OPENROUTER_DEFAULT_MODEL,
    )


def get_review_model_name() -> str:
    """Model for A3 review suggestions."""
    return _resolve(
        (
            os.environ.get("REVIEW_LLM_MODEL", ""),
            os.environ.get("LLM_MODEL", ""),
            os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", ""),
        ),
        _OPENROUTER_DEFAULT_REVIEW_MODEL,
    )
