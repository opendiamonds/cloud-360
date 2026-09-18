"""Unit tests for design_agent prompt helpers (A1 / A2 partial-update path)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from tests.helpers import backend_dir  # noqa: F401 — ensures path + psycopg2 mock

from services.design_agent import build_system_prompt, format_user_prompt


class TestBuildSystemPrompt(unittest.TestCase):
    @patch("services.design_agent.load_system_prompt", return_value="BASE_PROMPT")
    def test_without_current_xml(self, _mock):
        out = build_system_prompt(None)
        self.assertEqual(out, "BASE_PROMPT")
        self.assertNotIn("目前的架構草稿", out)

    @patch("services.design_agent.load_system_prompt", return_value="BASE_PROMPT")
    def test_with_current_xml_appends_draft(self, _mock):
        xml = '<mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>'
        out = build_system_prompt(xml)
        self.assertTrue(out.startswith("BASE_PROMPT"))
        self.assertIn("目前的架構草稿", out)
        self.assertIn(xml, out)
        self.assertIn("修改", out)

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=25, deadline=None)
    def test_current_xml_always_embedded(self, xml: str):
        with patch(
            "services.design_agent.load_system_prompt", return_value="BASE"
        ):
            out = build_system_prompt(xml)
            self.assertIn(xml, out)
            self.assertIn("```xml", out)


class TestFormatUserPrompt(unittest.TestCase):
    def test_empty_messages_still_instructs_tool(self):
        out = format_user_prompt([])
        self.assertIn("對話歷史", out)
        self.assertIn("draw_architecture_diagram", out)
        self.assertIn("不要使用 Markdown", out)

    def test_loaded_prompt_forbids_markdown_in_chat(self):
        from services.design_agent import load_system_prompt

        prompt = load_system_prompt()
        self.assertIn("禁止使用 Markdown", prompt)
        self.assertIn("一般口語對答", prompt)

    def test_roles_labeled(self):
        out = format_user_prompt(
            [
                {"role": "user", "content": "要一個 VPC"},
                {"role": "assistant", "content": "好的"},
            ]
        )
        self.assertIn("使用者：要一個 VPC", out)
        self.assertIn("助理：好的", out)

    @given(
        st.lists(
            st.fixed_dictionaries(
                {
                    "role": st.sampled_from(["user", "assistant"]),
                    "content": st.text(max_size=80),
                }
            ),
            max_size=20,
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_all_contents_appear(self, messages):
        out = format_user_prompt(messages)
        for m in messages:
            self.assertIn(m["content"], out)


if __name__ == "__main__":
    unittest.main()
