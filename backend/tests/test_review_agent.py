"""Tests for review agent fallback suggestions (no live LLM)."""

from __future__ import annotations

import unittest

from services.review_agent import fallback_suggestions_from_findings


class TestReviewAgentFallback(unittest.TestCase):
    def test_fallback_empty(self) -> None:
        text = fallback_suggestions_from_findings([])
        self.assertIn("OPENROUTER_API_KEY", text)

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
