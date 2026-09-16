"""Live Azure Calculator integration (skipped unless COST_AZURE_CALCULATOR_LIVE=1)."""

import os
import unittest

from cost.azure_calculator_runner import (
    AzureCalculatorError,
    calculator_region_value,
    run_azure_calculator_estimate,
)


@unittest.skipUnless(
    os.environ.get("COST_AZURE_CALCULATOR_LIVE", "").strip() == "1",
    "set COST_AZURE_CALCULATOR_LIVE=1 to run live Playwright against azure.microsoft.com",
)
class TestAzureCalculatorLive(unittest.TestCase):
    def test_virtual_machines_eastus_monthly_total(self):
        result = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 1}],
            stub=False,
        )
        self.assertGreater(float(result.total_usd), 0.0)
        self.assertIn("live playwright", " ".join(result.assumptions))

    def test_aks_eastus_monthly_total(self):
        result = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "AzureKubernetesService", "quantity": 1}],
            stub=False,
        )
        self.assertGreater(float(result.total_usd), 0.0)

    def test_vm_and_aks_combined_total(self):
        result = run_azure_calculator_estimate(
            "eastus",
            [
                {"map_key": "VirtualMachines", "quantity": 1},
                {"map_key": "AzureKubernetesService", "quantity": 1},
            ],
            stub=False,
        )
        vm_only = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 1}],
            stub=False,
        )
        self.assertGreater(float(result.total_usd), float(vm_only.total_usd))
        self.assertEqual(len(result.calculator_lines), 2)
        names = {row["product_name"] for row in result.calculator_lines}
        self.assertTrue(any("Virtual Machine" in n for n in names))
        self.assertTrue(any("Kubernetes" in n for n in names))

    def test_quantity_doubles_vm_total(self):
        one = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 1}],
            stub=False,
        )
        two = run_azure_calculator_estimate(
            "eastus",
            [{"map_key": "VirtualMachines", "quantity": 2}],
            stub=False,
        )
        self.assertGreater(float(two.total_usd), float(one.total_usd))


class TestAzureCalculatorRegions(unittest.TestCase):
    def test_eastus_maps_to_us_east(self):
        self.assertEqual(calculator_region_value("eastus"), "us-east")

    def test_unknown_region_raises(self):
        with self.assertRaises(AzureCalculatorError):
            calculator_region_value("not-a-region")


if __name__ == "__main__":
    unittest.main()
