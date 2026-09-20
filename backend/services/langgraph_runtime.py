"""LangGraph runtime helpers for OpenRouter (OpenAI-compatible) execution.

Parallel to ``llm_provider`` / ``claude-agent-sdk`` — this module does not
modify CLI / Anthropic env semantics. Cost-advice graph nodes and prompts
belong to U7; this unit only builds the client and runs a caller-supplied
compiled graph.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "google/gemini-3.7-flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"


class RuntimeAuthError(Exception):
    """Missing or empty OpenRouter credentials (domain error, not HTTP)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "missing_openrouter_api_key",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class InvokeOutcome:
    """Successful ``invoke_graph`` result; callers read terminal state via ``.state``."""

    state: Any


@dataclass(frozen=True)
class StreamEvent:
    """One streaming event from ``stream_graph`` / ``astream_graph``."""

    kind: str
    data: Any


@dataclass(frozen=True)
class OpenRouterSettings:
    """Connection settings for the OpenAI-compatible OpenRouter path."""

    api_key_env_name: str = OPENROUTER_API_KEY_ENV
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    default_model: str = DEFAULT_OPENROUTER_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


def _require_openrouter_api_key() -> str:
    value = os.environ.get(OPENROUTER_API_KEY_ENV, "").strip()
    if not value:
        raise RuntimeAuthError(
            f"{OPENROUTER_API_KEY_ENV} is not set",
            code="missing_openrouter_api_key",
        )
    return value


def openrouter_chat_model(
    *,
    model: str | None = None,
    timeout_seconds: float | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
):
    """Build a ``ChatOpenAI`` client pointed at OpenRouter.

    Raises ``RuntimeAuthError`` when ``OPENROUTER_API_KEY`` is missing/empty.
    Does not mutate ``llm_provider`` environment semantics.
    """
    api_key = _require_openrouter_api_key()
    from langchain_openai import ChatOpenAI

    resolved_timeout = (
        DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else float(timeout_seconds)
    )
    resolved_model = model or DEFAULT_OPENROUTER_MODEL
    return ChatOpenAI(
        model=resolved_model,
        api_key=api_key,
        base_url=DEFAULT_OPENROUTER_BASE_URL,
        timeout=resolved_timeout,
        temperature=temperature,
        max_retries=0,
        **kwargs,
    )


def invoke_graph(
    graph: Any,
    state: Any,
    *,
    config: Mapping[str, Any] | None = None,
) -> InvokeOutcome:
    """Synchronously run a caller-compiled graph to completion."""
    if not hasattr(graph, "invoke"):
        raise TypeError("graph must expose an invoke(...) method")
    result = graph.invoke(state, config=dict(config) if config else None)
    return InvokeOutcome(state=result)


def stream_graph(
    graph: Any,
    state: Any,
    *,
    config: Mapping[str, Any] | None = None,
    stream_mode: str | None = None,
) -> Iterator[StreamEvent]:
    """Synchronously stream graph events (smoke / scripts)."""
    if not hasattr(graph, "stream"):
        raise TypeError("graph must expose a stream(...) method")
    kwargs: dict[str, Any] = {}
    if config is not None:
        kwargs["config"] = dict(config)
    if stream_mode is not None:
        kwargs["stream_mode"] = stream_mode
    for chunk in graph.stream(state, **kwargs):
        yield StreamEvent(kind="updates", data=chunk)


async def astream_graph(
    graph: Any,
    state: Any,
    *,
    config: Mapping[str, Any] | None = None,
    stream_mode: str | None = None,
) -> AsyncIterator[StreamEvent]:
    """Asynchronously stream graph events (FastAPI SSE / async handlers)."""
    if not hasattr(graph, "astream"):
        raise TypeError("graph must expose an astream(...) method")
    kwargs: dict[str, Any] = {}
    if config is not None:
        kwargs["config"] = dict(config)
    if stream_mode is not None:
        kwargs["stream_mode"] = stream_mode
    async for chunk in graph.astream(state, **kwargs):
        yield StreamEvent(kind="updates", data=chunk)


__all__ = [
    "DEFAULT_OPENROUTER_BASE_URL",
    "DEFAULT_OPENROUTER_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "OPENROUTER_API_KEY_ENV",
    "InvokeOutcome",
    "OpenRouterSettings",
    "RuntimeAuthError",
    "StreamEvent",
    "astream_graph",
    "invoke_graph",
    "openrouter_chat_model",
    "stream_graph",
]
