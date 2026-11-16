"""LangGraph runtime helpers for OpenRouter (OpenAI-compatible) execution.

Parallel to ``llm_provider`` / ``claude-agent-sdk`` — this module does not
modify CLI / Anthropic env semantics. Cost-advice graph nodes and prompts
belong to U7; this unit only builds the client and runs a caller-supplied
compiled graph.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
#: OpenRouter Decisions API (classification models such as ``typesafe/jev-1.14``).
#: The ``alpha`` path segment means OpenRouter does not promise stability; see
#: ADR-0024 for the risk and why the intent router accepts it.
DEFAULT_OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
#: HTTP statuses worth retrying when a caller grants a retry budget. 4xx other
#: than 408/429 are request errors: retrying them only repeats the bill.
_RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
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
    temperature: float | None = 0.0,
    max_retries: int = 0,
    **kwargs: Any,
):
    """Build a ``ChatOpenAI`` client pointed at OpenRouter.

    Raises ``RuntimeAuthError`` when ``OPENROUTER_API_KEY`` is missing/empty.
    Does not mutate ``llm_provider`` environment semantics.

    ``temperature=None`` omits the parameter entirely instead of sending a
    value. Some OpenRouter-hosted models advertise an EMPTY
    ``supported_parameters`` array (``typesafe/jev-1.13`` was one), and for those
    an unconditional ``temperature=0.0`` is a parameter the provider may reject
    or silently ignore -- see U11's ``tech-stack-decisions.md`` TS-3a.

    ``max_retries`` is a parameter rather than a hard-coded ``0`` so that a
    caller which owns a configurable retry budget can pass it through. U11's
    ``BR6.3`` requires the per-turn call count, the retry count AND the usage
    cap to each be "a mechanism that exists and is configurable"; with the
    value frozen here, ``BRAIN_ROUTER_MAX_RETRIES`` was read, logged and then
    ignored -- a setting that changes nothing.

    Both defaults are the previous hard-coded values (``temperature=0.0``,
    ``max_retries=0``), so every existing caller (A1 design agent, A3
    review/lens agents, C1 cost advice) keeps its current behaviour byte for
    byte. ``None``/a non-zero retry budget only add ways to say otherwise.
    """
    api_key = _require_openrouter_api_key()
    from langchain_openai import ChatOpenAI

    resolved_timeout = (
        DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else float(timeout_seconds)
    )
    resolved_model = model or DEFAULT_OPENROUTER_MODEL
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatOpenAI(
        model=resolved_model,
        api_key=api_key,
        base_url=DEFAULT_OPENROUTER_BASE_URL,
        timeout=resolved_timeout,
        max_retries=max_retries,
        **kwargs,
    )


def chat_model(
    *,
    openrouter_builder: Callable[[], Any] | None = None,
    **kwargs: Any,
):
    """The single place an LLM client is chosen; all LLM call sites go through it.

    On openrouter this forwards ``kwargs`` unchanged to
    :func:`openrouter_chat_model`, or calls ``openrouter_builder`` when the
    caller builds a different client for that path (the A1 design agent's
    ``ChatAnthropic``). Behaviour on openrouter is therefore exactly what each
    caller had before this function existed.

    On claude-code (local development only, see ``services.llm_provider``) it
    returns a ``ClaudeCodeChatModel``; only ``model`` and ``timeout_seconds`` apply.
    Raises ``RuntimeAuthError`` when the ``claude`` CLI is not on PATH, the same
    domain error a missing OpenRouter key produces, so callers need no new branch.
    """
    from services.llm_provider import (
        CLAUDE_CODE,
        auth_error_message,
        get_provider,
        llm_auth_ready,
    )

    if get_provider() != CLAUDE_CODE:
        if openrouter_builder is not None:
            return openrouter_builder()
        return openrouter_chat_model(**kwargs)

    if not llm_auth_ready():
        raise RuntimeAuthError(auth_error_message(), code="claude_cli_not_found")
    from services.claude_code_chat import ClaudeCodeChatModel

    timeout_seconds = kwargs.get("timeout_seconds")
    return ClaudeCodeChatModel(
        cli_model=kwargs.get("model"),
        timeout_seconds=(
            DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else float(timeout_seconds)
        ),
    )


class DecisionsMalformedResponse(Exception):
    """The Decisions API answered 2xx but the body is not a JSON object.

    Kept distinct from transport failures: the provider responded, the shape is
    wrong. Callers map it to their own "malformed" category by class name.
    """


async def openrouter_decide(
    *,
    model: str,
    state: str,
    questions: Mapping[str, Any],
    timeout_seconds: float,
    max_retries: int = 0,
    transport: Any = None,
) -> dict:
    """POST one request to OpenRouter's Decisions API and return the JSON body.

    This is the only place the Decisions endpoint is called, so the outbound
    path stays inside this runtime module (U11 ``SEC-2``: router modules must
    not import an HTTP client themselves).

    - Raises ``RuntimeAuthError`` when ``OPENROUTER_API_KEY`` is missing.
    - Raises ``httpx.HTTPStatusError`` for a non-2xx answer (status on
      ``exc.response.status_code``) and ``httpx.TransportError`` subclasses for
      timeouts/connection failures, after ``max_retries`` extra attempts on the
      retryable subset only.
    - Raises ``DecisionsMalformedResponse`` when a 2xx body is not a JSON object.

    ``transport`` is an ``httpx`` transport for tests (``httpx.MockTransport``);
    production passes ``None``.
    """
    api_key = _require_openrouter_api_key()
    import httpx

    body = {"model": model, "state": state, "questions": dict(questions)}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    attempts = 1 + max(0, int(max_retries))
    last_exc: BaseException | None = None
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(float(timeout_seconds)), transport=transport
    ) as client:
        for attempt in range(attempts):
            try:
                response = await client.post(
                    DEFAULT_OPENROUTER_DECISIONS_URL, json=body, headers=headers
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in _RETRYABLE_STATUSES and attempt + 1 < attempts:
                    continue
                raise
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt + 1 < attempts:
                    continue
                raise
            try:
                parsed = response.json()
            except ValueError as exc:
                raise DecisionsMalformedResponse("decisions response is not JSON") from exc
            if not isinstance(parsed, dict):
                raise DecisionsMalformedResponse("decisions response is not a JSON object")
            return parsed
    raise last_exc if last_exc is not None else RuntimeError("unreachable")


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
    "DEFAULT_OPENROUTER_DECISIONS_URL",
    "DEFAULT_OPENROUTER_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "OPENROUTER_API_KEY_ENV",
    "DecisionsMalformedResponse",
    "InvokeOutcome",
    "OpenRouterSettings",
    "RuntimeAuthError",
    "StreamEvent",
    "astream_graph",
    "chat_model",
    "invoke_graph",
    "openrouter_chat_model",
    "openrouter_decide",
    "stream_graph",
]
