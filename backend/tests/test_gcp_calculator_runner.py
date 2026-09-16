"""Google Cloud Pricing Calculator runner tests (stub mode)."""

import os
import unittest

os.environ["COST_GCP_CALCULATOR_STUB"] = "1"

from cost.gcp_calculator_runner import (  # noqa: E402
    GcpCalculatorError,
    _gcp_timeout_ms,
    export_gcp_calculator_csv,
    run_gcp_calculator_estimate,
)


class TestGcpCalculatorRunner(unittest.TestCase):
    def test_stub_returns_fixture_total(self):
        result = run_gcp_calculator_estimate(
            "us-central1",
            [{"map_key": "ComputeEngine", "quantity": 2, "label": "Web VM"}],
            stub=True,
        )
        self.assertEqual(float(result.total_usd), 987.65)
        self.assertIn("stub", " ".join(result.assumptions).lower())
        self.assertEqual(len(result.calculator_lines), 1)
        self.assertEqual(result.calculator_lines[0]["label"], "Web VM")

    def test_export_csv_stub(self):
        csv_bytes, filename, source_url = export_gcp_calculator_csv(
            "us-central1",
            [{"map_key": "ComputeEngine", "quantity": 1}],
            stub=True,
        )
        self.assertIn(b"service_display_name", csv_bytes)
        self.assertTrue(filename.endswith(".csv"))
        self.assertIn("cloud.google.com", source_url.lower())

    def test_unknown_map_key_rejected(self):
        with self.assertRaises(GcpCalculatorError):
            run_gcp_calculator_estimate("us-central1", [{"map_key": "NotARealSku"}])

    def test_timeout_scales_with_item_count(self):
        prev = os.environ.pop("COST_GCP_CALCULATOR_TIMEOUT", None)
        try:
            self.assertGreaterEqual(_gcp_timeout_ms(13), 400_000)
            self.assertGreaterEqual(_gcp_timeout_ms(13), _gcp_timeout_ms(7))
        finally:
            if prev is not None:
                os.environ["COST_GCP_CALCULATOR_TIMEOUT"] = prev

    def test_merge_same_map_key(self):
        result = run_gcp_calculator_estimate(
            "us-central1",
            [
                {"map_key": "ComputeEngine", "quantity": 1},
                {"map_key": "ComputeEngine", "quantity": 1},
            ],
            stub=True,
        )
        self.assertEqual(len(result.line_items), 1)
        self.assertEqual(result.line_items[0]["quantity"], 2)


if __name__ == "__main__":
    unittest.main()
