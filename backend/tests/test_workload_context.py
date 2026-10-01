"""
@story C1-W1 FR1.7
@purpose Workload context normalize / dump / load for estimate advice
@api POST /api/cost/v1/sets | Form field workload_context（本檔測純函式）
"""

from __future__ import annotations

import json
import unittest

from cost.workload_context import (
    dumps_workload_context,
    loads_workload_context,
    normalize_workload_context,
)


class WorkloadContextTest(unittest.TestCase):
    def test_normalize_keeps_allowed_and_drops_unknown(self):
        raw = {
            "system_description": "  SaaS  ",
            "monthly_budget": "1200",
            "evil": 1,
            "monthly_egress_gb": -1,
            "availability_sla": "99.9",
        }
        out = normalize_workload_context(raw)
        assert out is not None
        self.assertEqual(out["system_description"], "SaaS")
        self.assertEqual(out["monthly_budget"], 1200.0)
        self.assertEqual(out["availability_sla"], "99.9")
        self.assertNotIn("evil", out)
        self.assertNotIn("monthly_egress_gb", out)

    def test_normalize_empty_and_bad_json(self):
        self.assertIsNone(normalize_workload_context(None))
        self.assertIsNone(normalize_workload_context(""))
        self.assertIsNone(normalize_workload_context("{}"))
        self.assertIsNone(normalize_workload_context("{not-json"))

    def test_roundtrip_dumps_loads(self):
        ctx = normalize_workload_context(
            {"system_description": "API", "monthly_budget": 10}
        )
        dumped = dumps_workload_context(ctx)
        self.assertIsInstance(dumped, str)
        loaded = loads_workload_context(dumped)
        self.assertEqual(loaded, ctx)
        self.assertEqual(json.loads(dumped)["monthly_budget"], 10.0)


if __name__ == "__main__":
    unittest.main()
