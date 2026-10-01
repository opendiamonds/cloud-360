"""
A3 Assessment → LangGraph migration tests (Review + Lens).

@purpose Prove Review/Lens use langgraph_runtime OpenRouter path and never import Claude Agent SDK
@api POST /api/architecture/reviews (SSE suggestion_delta via run_review_agent)
@given Mock ChatOpenAI / compiled graph; no real OPENROUTER_API_KEY
@step Stream review chunks; validate lens JSON answers; assert sources lack claude_agent_sdk
@pass Chunks equal mock text; lens answers validated; RuntimeAuthError maps to auth_error_message without secrets
@story FR1 FR2 FR5 BR1.1 BR5.1
"""

from __future__ import annotations

import asyncio
import inspect
import json
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class _FakeChunk:
    def __init__(self, content: str) -> None:
        self.content = content


class TestA3LangGraphMigration(unittest.TestCase):
    def test_review_agent_source_has_no_claude_sdk_import(self) -> None:
        source = (BACKEND_ROOT / "services" / "review_agent.py").read_text(encoding="utf-8")
        self.assertNotIn("claude_agent_sdk", source)
        self.assertNotIn("ClaudeSDKClient", source)
        self.assertIn("openrouter_chat_model", source)
        self.assertIn("langgraph", source.lower())

    def test_wa_lens_engine_source_has_no_claude_sdk_import(self) -> None:
        source = (BACKEND_ROOT / "services" / "wa_lens_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("claude_agent_sdk", source)
        self.assertNotIn("ClaudeSDKClient", source)
        self.assertNotIn("emit_lens_answers", source)
        self.assertIn("openrouter_chat_model", source)

    def test_run_review_agent_streams_chunks_via_openrouter(self) -> None:
        from services import review_agent as ra

        fake_model = MagicMock()

        async def _fake_astream(state: dict[str, Any], **kwargs: Any):
            self.assertEqual(kwargs.get("stream_mode"), "messages")
            yield (_FakeChunk("建議一"), {"langgraph_node": "generate"})
            yield (_FakeChunk("建議二"), {"langgraph_node": "generate"})

        fake_compiled = MagicMock()
        fake_compiled.astream = _fake_astream

        with (
            patch.object(ra, "configure_provider_env"),
            patch(
                "services.langgraph_runtime.openrouter_chat_model",
                return_value=fake_model,
            ) as mock_model,
            patch.object(ra, "_compile_review_graph", return_value=fake_compiled),
            patch.object(ra, "get_review_model_name", return_value="google/gemini-3.7-flash"),
        ):

            async def _collect() -> list[str]:
                return [
                    chunk
                    async for chunk in ra.run_review_agent(
                        {"nodes": [], "node_count": 0},
                        {"findings": [], "overall_score": 50},
                    )
                ]

            chunks = asyncio.run(_collect())

        self.assertEqual(chunks, ["建議一", "建議二"])
        mock_model.assert_called_once()
        self.assertEqual(
            mock_model.call_args.kwargs.get("model"),
            "google/gemini-3.7-flash",
        )

    def test_run_review_agent_auth_error_raises_safe_message(self) -> None:
        from services import review_agent as ra
        from services.langgraph_runtime import RuntimeAuthError
        from services.llm_provider import auth_error_message

        with (
            patch.object(ra, "configure_provider_env"),
            patch(
                "services.langgraph_runtime.openrouter_chat_model",
                side_effect=RuntimeAuthError("OPENROUTER_API_KEY is not set"),
            ),
        ):

            async def _run() -> None:
                async for _ in ra.run_review_agent({}, {"findings": []}):
                    pass

            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(_run())

        msg = str(ctx.exception)
        self.assertEqual(msg, auth_error_message())
        self.assertNotIn("sk-", msg.lower())
        self.assertNotIn("token=", msg.lower())

    def test_answer_lens_with_agent_returns_validated_shape(self) -> None:
        from services import wa_lens_engine as wl

        lens = wl.load_lens()
        questions = wl.list_questions(lens)
        q0 = questions[0]
        qid = q0["question_id"]
        choice_ids = [c["id"] for c in q0["choices"] if c.get("id")]
        self.assertTrue(choice_ids)
        selected = [choice_ids[0]]
        payload = {
            "answers": [
                {
                    "question_id": qid,
                    "selected_choice_ids": selected + ["not_a_real_choice"],
                },
                {
                    "question_id": "unknown_question",
                    "selected_choice_ids": ["x"],
                },
            ]
        }

        fake_compiled = MagicMock()
        fake_compiled.ainvoke = AsyncMock(
            return_value={"text": json.dumps(payload, ensure_ascii=False)}
        )

        with (
            patch(
                "services.llm_provider.llm_auth_ready",
                return_value=True,
            ),
            patch(
                "services.llm_provider.configure_provider_env",
            ),
            patch(
                "services.langgraph_runtime.openrouter_chat_model",
                return_value=MagicMock(),
            ) as mock_model,
            patch.object(wl, "_compile_lens_graph", return_value=fake_compiled),
        ):
            answers = asyncio.run(
                wl.answer_lens_with_agent({"nodes": [], "node_count": 0}, lens)
            )

        self.assertIsInstance(answers, dict)
        self.assertEqual(answers.get(qid), selected)
        self.assertNotIn("unknown_question", answers)
        mock_model.assert_called_once()
        # Score path still consumes the shape
        scored = wl.score_answers(lens, answers)
        self.assertIn("overall_score", scored)

    def test_answer_lens_empty_model_raises(self) -> None:
        from services import wa_lens_engine as wl

        lens = wl.load_lens()
        fake_compiled = MagicMock()
        fake_compiled.ainvoke = AsyncMock(return_value={"text": '{"answers":[]}'})

        with (
            patch("services.llm_provider.llm_auth_ready", return_value=True),
            patch("services.llm_provider.configure_provider_env"),
            patch(
                "services.langgraph_runtime.openrouter_chat_model",
                return_value=MagicMock(),
            ),
            patch.object(wl, "_compile_lens_graph", return_value=fake_compiled),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(
                    wl.answer_lens_with_agent({"nodes": []}, lens)
                )
        self.assertIn("no answers", str(ctx.exception).lower())

    def test_review_graph_schema_exposes_user_prompt_channel(self) -> None:
        """Regression: StateGraph(dict)+TypedDict param emptied state under messages stream."""
        from services.review_agent import _compile_review_graph

        fake_model = MagicMock()
        compiled = _compile_review_graph(fake_model, "sys")
        channels = getattr(compiled, "channels", {})
        self.assertIn("user_prompt", channels)
        self.assertIn("text", channels)
        self.assertNotIn("__root__", channels)

    def test_lens_graph_schema_exposes_user_prompt_channel(self) -> None:
        from services.wa_lens_engine import _compile_lens_graph

        fake_model = MagicMock()
        compiled = _compile_lens_graph(fake_model, "sys")
        channels = getattr(compiled, "channels", {})
        self.assertIn("user_prompt", channels)
        self.assertIn("text", channels)

    def test_public_api_signatures_preserved(self) -> None:
        from services.review_agent import (
            _compact_payload,
            fallback_suggestions_from_findings,
            load_review_system_prompt,
            run_review_agent,
        )
        from services.wa_lens_engine import answer_lens_with_agent

        self.assertTrue(inspect.isasyncgenfunction(run_review_agent))
        self.assertTrue(inspect.iscoroutinefunction(answer_lens_with_agent))
        self.assertTrue(callable(load_review_system_prompt))
        self.assertTrue(callable(fallback_suggestions_from_findings))
        self.assertTrue(callable(_compact_payload))


if __name__ == "__main__":
    unittest.main()
