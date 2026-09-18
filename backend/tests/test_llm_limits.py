"""Unit tests for LLM token limit helpers."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.llm_limits import (
    get_llm_max_output_tokens,
    get_xml_context_max_chars,
    truncate_text_for_llm,
)


class TestLlmLimits(unittest.TestCase):
    def test_default_max_output_tokens(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_llm_max_output_tokens(), 12_000)

    def test_env_max_output_tokens(self):
        with patch.dict(os.environ, {"LLM_MAX_OUTPUT_TOKENS": "8192"}, clear=True):
            self.assertEqual(get_llm_max_output_tokens(), 8192)

    def test_max_output_tokens_clamped(self):
        with patch.dict(os.environ, {"LLM_MAX_OUTPUT_TOKENS": "999999"}, clear=True):
            self.assertEqual(get_llm_max_output_tokens(), 24_000)

    def test_truncate_xml(self):
        text = "x" * 100
        out = truncate_text_for_llm(text, max_chars=40, label="架構 XML")
        self.assertIn("架構 XML已截斷", out)
        self.assertLessEqual(len(out), 120)

    def test_xml_context_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_xml_context_max_chars(), 32_000)


if __name__ == "__main__":
    unittest.main()
