"""
@purpose U6 langgraph-runtime: OpenRouter client + graph invoke/stream helpers
@api services.langgraph_runtime
@unit langgraph-runtime
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.langgraph_runtime import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    OPENROUTER_API_KEY_ENV,
    InvokeOutcome,
    RuntimeAuthError,
    StreamEvent,
    astream_graph,
    invoke_graph,
    openrouter_chat_model,
    stream_graph,
)


class TestLangGraphRuntimeAuth(unittest.TestCase):
    def test_missing_api_key_raises_runtime_auth_error(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != OPENROUTER_API_KEY_ENV}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeAuthError) as ctx:
                openrouter_chat_model()
        err = ctx.exception
        self.assertEqual(err.code, "missing_openrouter_api_key")
        self.assertIn(OPENROUTER_API_KEY_ENV, str(err))
        self.assertIn(OPENROUTER_API_KEY_ENV, err.message)

    def test_empty_api_key_raises_runtime_auth_error(self) -> None:
        with patch.dict(os.environ, {OPENROUTER_API_KEY_ENV: "   "}, clear=False):
            with self.assertRaises(RuntimeAuthError) as ctx:
                openrouter_chat_model()
        self.assertIn(OPENROUTER_API_KEY_ENV, str(ctx.exception))


class TestOpenRouterChatModel(unittest.TestCase):
    def test_builds_client_with_defaults(self) -> None:
        fake_key = "sk-or-test-key-not-real"
        mock_chat = MagicMock(return_value=SimpleNamespace(marker="ok"))
        fake_mod = SimpleNamespace(ChatOpenAI=mock_chat)
        with patch.dict(os.environ, {OPENROUTER_API_KEY_ENV: fake_key}, clear=False):
            with patch.dict(sys.modules, {"langchain_openai": fake_mod}):
                client = openrouter_chat_model()
        self.assertEqual(client.marker, "ok")
        kwargs = mock_chat.call_args.kwargs
        self.assertEqual(kwargs["api_key"], fake_key)
        self.assertEqual(kwargs["base_url"], DEFAULT_OPENROUTER_BASE_URL)
        self.assertEqual(kwargs["model"], DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(kwargs["timeout"], DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(kwargs["max_retries"], 0)

    def test_default_timeout_is_sixty_seconds(self) -> None:
        mock_chat = MagicMock(return_value=object())
        fake_mod = SimpleNamespace(ChatOpenAI=mock_chat)
        with patch.dict(os.environ, {OPENROUTER_API_KEY_ENV: "k"}, clear=False):
            with patch.dict(sys.modules, {"langchain_openai": fake_mod}):
                openrouter_chat_model()
        self.assertEqual(mock_chat.call_args.kwargs["timeout"], 60.0)
        self.assertEqual(DEFAULT_TIMEOUT_SECONDS, 60.0)


class TestInvokeAndStream(unittest.TestCase):
    def test_invoke_graph_returns_invoke_outcome(self) -> None:
        graph = MagicMock()
        graph.invoke.return_value = {"done": True, "n": 1}
        outcome = invoke_graph(graph, {"n": 0})
        self.assertIsInstance(outcome, InvokeOutcome)
        self.assertEqual(outcome.state, {"done": True, "n": 1})
        graph.invoke.assert_called_once_with({"n": 0}, config=None)

    def test_stream_graph_yields_stream_events(self) -> None:
        graph = MagicMock()
        graph.stream.return_value = iter([{"a": 1}, {"b": 2}])
        events = list(stream_graph(graph, {"seed": True}))
        self.assertGreaterEqual(len(events), 1)
        self.assertTrue(all(isinstance(e, StreamEvent) for e in events))
        self.assertEqual(events[0].kind, "updates")
        self.assertEqual(events[0].data, {"a": 1})

    def test_astream_graph_yields_stream_events(self) -> None:
        class _AsyncGraph:
            async def astream(self, state, **kwargs):
                yield {"step": 1}
                yield {"step": 2}

        async def _run() -> list[StreamEvent]:
            return [e async for e in astream_graph(_AsyncGraph(), {"x": 1})]

        events = asyncio.run(_run())
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].data, {"step": 1})
        self.assertEqual(events[1].kind, "updates")


class TestSecretRedaction(unittest.TestCase):
    def test_error_and_events_must_not_contain_api_key_value(self) -> None:
        fake_key = "sk-or-LEAK-ME-1234567890abcdef"
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeAuthError) as ctx:
                openrouter_chat_model()
        self.assertNotIn(fake_key, str(ctx.exception))
        self.assertNotIn(fake_key, ctx.exception.message)

        graph = MagicMock()
        graph.stream.return_value = iter([{"msg": "ok", "note": "no secrets"}])
        for event in stream_graph(graph, {}):
            blob = f"{event.kind}:{event.data!r}"
            self.assertNotIn(fake_key, blob)

        # Injected exception path: public string must not retain key material.
        public = RuntimeAuthError(f"{OPENROUTER_API_KEY_ENV} is not set")
        self.assertNotIn(fake_key, public.message)
        self.assertNotIn(fake_key, str(public))


if __name__ == "__main__":
    unittest.main()
