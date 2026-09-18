"""LLM token / context limits (OpenRouter credits & Agent SDK)."""

from __future__ import annotations

import os

_DEFAULT_MAX_OUTPUT_TOKENS = 12_000
_MIN_OUTPUT_TOKENS = 512
_MAX_OUTPUT_TOKENS = 24_000
_DEFAULT_XML_CONTEXT_CHARS = 32_000


def get_llm_max_output_tokens() -> int:
    """Max completion tokens per Agent SDK request (maps to CLAUDE_CODE_MAX_OUTPUT_TOKENS)."""
    raw = (
        os.environ.get("LLM_MAX_OUTPUT_TOKENS", "").strip()
        or os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "").strip()
        or str(_DEFAULT_MAX_OUTPUT_TOKENS)
    )
    try:
        value = int(raw)
    except ValueError:
        value = _DEFAULT_MAX_OUTPUT_TOKENS
    return max(_MIN_OUTPUT_TOKENS, min(value, _MAX_OUTPUT_TOKENS))


def get_xml_context_max_chars() -> int:
    raw = os.environ.get("LLM_XML_CONTEXT_MAX_CHARS", str(_DEFAULT_XML_CONTEXT_CHARS)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = _DEFAULT_XML_CONTEXT_CHARS
    return max(2_000, min(value, 200_000))


def truncate_text_for_llm(
    text: str,
    *,
    max_chars: int | None = None,
    label: str = "內容",
) -> str:
    limit = max_chars if max_chars is not None else get_xml_context_max_chars()
    if len(text) <= limit:
        return text
    return (
        text[:limit]
        + f"\n\n<!-- {label}已截斷：原長 {len(text)} 字元，僅保留前 {limit} 字元以降低 token 用量 -->"
    )


def apply_agent_token_limits_to_env() -> None:
    """Write token limits into process env for Claude Code CLI subprocesses."""
    os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(get_llm_max_output_tokens())
    # OpenRouter 等第三方 provider：關閉 extended thinking 以節省 token
    if not os.environ.get("MAX_THINKING_TOKENS", "").strip():
        os.environ["MAX_THINKING_TOKENS"] = "0"


def agent_sdk_env() -> dict[str, str]:
    """Per-request env overrides for ClaudeAgentOptions."""
    return {
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(get_llm_max_output_tokens()),
        "MAX_THINKING_TOKENS": os.environ.get("MAX_THINKING_TOKENS", "0"),
    }
