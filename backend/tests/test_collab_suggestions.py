"""Tests for collab optimize suggestions."""

from __future__ import annotations

import unittest

from services.collab_suggestions import build_optimize_suggestions_summary, finding_advice


class TestCollabSuggestions(unittest.TestCase):
    def test_remaining_uses_hint_field(self):
        baseline = [
            {
                "code": "LENS-SEC-EDGE",
                "pillar": "security",
                "severity": "high",
                "title": "Edge",
                "message": "no waf",
                "recommendation_hint": "Add WAF",
                "lens_risk": "HIGH_RISK",
            }
        ]
        remaining = [
            {
                "code": "LENS-SEC-DATA",
                "pillar": "security",
                "severity": "warn",
                "title": "Data",
                "message": "no encrypt",
                "hint": "Enable SSE-KMS",
                "lens_risk": "MEDIUM_RISK",
            }
        ]
        text = build_optimize_suggestions_summary(baseline, remaining)
        self.assertIn("剩餘風險與建議", text)
        self.assertIn("Enable SSE-KMS", text)
        self.assertIn("**建議**", text)

    def test_finding_advice_fallback(self):
        advice = finding_advice(
            {
                "code": "X",
                "title": "Missing HA",
                "lens_risk": "HIGH_RISK",
            }
        )
        self.assertIn("Missing HA", advice)
        self.assertIn("高風險", advice)


if __name__ == "__main__":
    unittest.main()
