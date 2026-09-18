"""Unit tests for A1↔A3 multi-agent helpers."""

from __future__ import annotations

import unittest

from services.wa_collab_orchestrator import MAX_ROUNDS, _compact_findings
from services.wa_score_service import TARGET_SCORE


class TestWaCollabConstants(unittest.TestCase):
    def test_target_and_rounds(self):
        self.assertEqual(TARGET_SCORE, 80)
        self.assertEqual(MAX_ROUNDS, 2)

    def test_compact_findings(self):
        raw = [
            {
                "code": "SEC-1",
                "pillar": "security",
                "severity": "high",
                "title": "No WAF",
                "recommendation_hint": "Add WAF",
                "lens_risk": "HIGH_RISK",
                "extra": "drop-me",
            }
        ]
        out = _compact_findings(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["code"], "SEC-1")
        self.assertEqual(out[0]["hint"], "Add WAF")
        self.assertEqual(out[0]["lens_risk"], "HIGH_RISK")
        self.assertNotIn("extra", out[0])

    def test_high_risk_findings(self):
        from services.wa_collab_orchestrator import _high_risk_findings

        raw = [
            {"code": "A", "severity": "high", "lens_risk": "HIGH_RISK", "title": "a"},
            {"code": "B", "severity": "warn", "lens_risk": "MEDIUM_RISK", "title": "b"},
        ]
        high = _high_risk_findings(raw)
        self.assertEqual(len(high), 1)
        self.assertEqual(high[0]["code"], "A")


if __name__ == "__main__":
    unittest.main()
