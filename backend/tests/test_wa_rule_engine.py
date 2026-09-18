"""Property-based + unit tests for WaRuleEngine (A3)."""

from __future__ import annotations

import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

import tests.helpers  # noqa: F401 — path / psycopg2 setup
from services.wa_rule_engine import (
    WEIGHTS,
    evaluate,
    score_findings,
    Finding,
    PILLARS,
)


def _mx(cells: list[str]) -> str:
    inner = "".join(cells)
    return f"<mxGraphModel><root><mxCell id=\"0\"/><mxCell id=\"1\" parent=\"0\"/>{inner}</root></mxGraphModel>"


class TestWaRuleEngine(unittest.TestCase):
    def test_empty_diagram_has_finding(self):
        result = evaluate(_mx([]))
        codes = {f.code for f in result.findings}
        self.assertIn("OE-EMPTY-DIAGRAM", codes)
        self.assertEqual(result.rule_pack_version, "wa-aws-mvp-1")

    def test_db_without_standby(self):
        xml = _mx(
            [
                '<mxCell id="10" value="Aurora PostgreSQL" style="shape=mxgraph.aws4.rds;" vertex="1" parent="1"/>',
            ]
        )
        result = evaluate(xml)
        codes = {f.code for f in result.findings}
        self.assertIn("REL-DB-NO-STANDBY", codes)

    @given(
        severities=st.lists(
            st.sampled_from(["info", "warn", "high", "critical"]),
            min_size=0,
            max_size=8,
        )
    )
    @settings(max_examples=40)
    def test_scores_bounded_and_weighted(self, severities):
        findings = [
            Finding(
                code=f"T-{i}",
                pillar=PILLARS[i % len(PILLARS)],
                severity=sev,
                title="t",
                message="m",
            )
            for i, sev in enumerate(severities)
        ]
        pillar_scores, overall = score_findings(findings)
        for p in PILLARS:
            self.assertGreaterEqual(pillar_scores[p], 0.0)
            self.assertLessEqual(pillar_scores[p], 100.0)
        expected = sum(pillar_scores[p] * WEIGHTS[p] for p in PILLARS)
        self.assertAlmostEqual(overall, round(expected, 2), places=2)

    @given(n=st.integers(min_value=0, max_value=5))
    @settings(max_examples=20)
    def test_same_xml_deterministic(self, n):
        cells = [
            f'<mxCell id="{i+10}" value="EC2 app {i}" style="shape=mxgraph.aws4.ec2;" vertex="1" parent="1"/>'
            for i in range(n)
        ]
        xml = _mx(cells)
        a = evaluate(xml)
        b = evaluate(xml)
        self.assertEqual(
            [f.code for f in a.findings],
            [f.code for f in b.findings],
        )
        self.assertEqual(a.overall_score, b.overall_score)
        self.assertEqual(a.pillar_scores, b.pillar_scores)

    def test_deduction_lowers_score(self):
        findings = [
            Finding(
                code="X",
                pillar="security",
                severity="critical",
                title="t",
                message="m",
            )
        ]
        pillar_scores, _ = score_findings(findings)
        self.assertEqual(pillar_scores["security"], 75.0)

    def test_gcp_provider_runs(self):
        xml = _mx(
            [
                '<mxCell id="10" value="Cloud SQL" style="shape=mxgraph.gcp.cloudsql;" vertex="1" parent="1"/>',
            ]
        )
        result = evaluate(xml, provider="gcp")
        self.assertEqual(result.provider, "gcp")
        self.assertEqual(result.rule_pack_version, "wa-gcp-mvp-1")
        codes = {f.code for f in result.findings}
        self.assertIn("GCP-REL-DB-NO-HA", codes)

    def test_azure_provider_runs(self):
        xml = _mx(
            [
                '<mxCell id="10" value="Azure SQL" style="shape=mxgraph.azure.sql;" vertex="1" parent="1"/>',
            ]
        )
        result = evaluate(xml, provider="azure")
        self.assertEqual(result.rule_pack_version, "wa-azure-mvp-1")
        codes = {f.code for f in result.findings}
        self.assertIn("AZ-REL-DB-NO-HA", codes)

    def test_detect_provider_gcp(self):
        from services.wa_rule_engine import detect_provider, parse_diagram_summary

        xml = _mx(
            [
                '<mxCell id="10" value="GKE cluster" style="shape=mxgraph.gcp.gke;" vertex="1" parent="1"/>',
            ]
        )
        det = detect_provider(parse_diagram_summary(xml))
        self.assertEqual(det["provider"], "gcp")

    def test_parse_tolerates_bare_amp_and_nbsp(self):
        from services.wa_rule_engine import parse_diagram_summary

        xml = _mx(
            [
                '<mxCell id="10" value="Front Door & WAF" style="shape=mxgraph.azure.front;" vertex="1" parent="1"/>',
                '<mxCell id="11" value="A&nbsp;B" style="shape=mxgraph.aws4.ec2;" vertex="1" parent="1"/>',
                '<mxCell id="12" value="CPU < 80%" style="shape=mxgraph.gcp.gce;" vertex="1" parent="1"/>',
            ]
        )
        summary = parse_diagram_summary(xml)
        labels = " ".join(n["label"] for n in summary["nodes"])
        self.assertIn("front door", labels)
        self.assertIn("waf", labels)
        self.assertGreaterEqual(summary["node_count"], 2)


if __name__ == "__main__":
    unittest.main()
