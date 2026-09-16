"""Azure Pricing Calculator runner tests (stub mode)."""

import os
import unittest

os.environ["COST_AZURE_CALCULATOR_STUB"] = "1"

from cost.azure_calculator_runner import (  # noqa: E402
    AzureCalculatorError,
    export_azure_calculator_excel,
    run_azure_calculator_estimate,
)


class TestAzureCalculatorRunner(unittest.TestCase):
    def test_stub_returns_fixture_total(self):
        result = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 2, "label": "Web VM"}],
            stub=True,
        )
        self.assertEqual(float(result.total_usd), 1234.56)
        self.assertIn("stub", " ".join(result.assumptions).lower())
        self.assertEqual(len(result.calculator_lines), 1)
        self.assertEqual(result.calculator_lines[0]["label"], "Web VM")
        self.assertAlmostEqual(
            sum(float(r["monthly_usd"]) for r in result.calculator_lines),
            1234.56,
            places=2,
        )

    def test_export_excel_stub(self):
        xlsx, filename, source_url = export_azure_calculator_excel(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 1}],
            stub=True,
        )
        self.assertTrue(xlsx.startswith(b"PK"))
        self.assertTrue(filename.endswith(".xlsx"))
        self.assertIn("exportestimate", source_url.lower())

    def test_unknown_map_key_rejected(self):
        with self.assertRaises(AzureCalculatorError):
            run_azure_calculator_estimate("eastus", [{"map_key": "NotARealSku"}])

    def test_merge_same_map_key(self):
        result = run_azure_calculator_estimate(
            "eastus",
            [
                {"map_key": "VirtualMachines", "quantity": 1},
                {"map_key": "VirtualMachines", "quantity": 1},
            ],
            stub=True,
        )
        self.assertEqual(len(result.line_items), 1)
        self.assertEqual(result.line_items[0]["quantity"], 2)


if __name__ == "__main__":
    unittest.main()
