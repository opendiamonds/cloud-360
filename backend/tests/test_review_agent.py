"""Tests for review agent fallback suggestions (no live LLM)."""

from __future__ import annotations

import unittest

from services.review_agent import fallback_suggestions_from_findings


class TestReviewAgentFallback(unittest.TestCase):
    def test_fallback_empty(self) -> None:
        text = fallback_suggestions_from_findings([])
        # build-and-test 第三輪（待修 8）：備援句不再只教設定 OPENROUTER_API_KEY——LLM_PROVIDER
        # 也可能是本機的 claude-code，寫死 OpenRouter 會把使用者引向錯的設定。
        self.assertIn("LLM_PROVIDER", text)
        self.assertNotIn("OPENROUTER_API_KEY", text)

    def test_fallback_orders_by_severity(self) -> None:
        text = fallback_suggestions_from_findings(
            [
                {
                    "code": "OE-X",
                    "title": "info item",
                    "severity": "info",
                    "recommendation_hint": "hint-info",
                },
                {
                    "code": "SEC-Y",
                    "title": "crit item",
                    "severity": "critical",
                    "recommendation_hint": "hint-crit",
                },
            ]
        )
        self.assertLess(text.index("SEC-Y"), text.index("OE-X"))
        self.assertIn("hint-crit", text)
        self.assertNotIn("##", text)
        self.assertNotIn("###", text)


if __name__ == "__main__":
    unittest.main()
