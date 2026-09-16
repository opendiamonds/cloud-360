"""C1 pricing agent planner + deterministic calculator path."""

import os
import unittest

os.environ.setdefault("COST_PRICING_STUB", "1")
os.environ["COST_AZURE_CALCULATOR_STUB"] = "1"
os.environ["COST_PRICING_AGENT"] = "1"

from cost.cost_pricing_agent import (  # noqa: E402
    plan_azure_line_items,
    run_cost_pricing_agent,
)


_AZURE_XML = (
    '<mxGraphModel><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="vm" value="Virtual Machines" style="azure2" vertex="1" parent="1"/>'
    '<mxCell id="aks" value="AKS" style="azure2" vertex="1" parent="1"/>'
    "</root></mxGraphModel>"
)


class TestCostPricingAgent(unittest.TestCase):
    def test_plan_azure_line_items(self):
        items, notes = plan_azure_line_items(_AZURE_XML, {"vm": 24, "aks": 48})
        keys = {row["map_key"] for row in items}
        self.assertIn("VirtualMachines", keys)
        self.assertIn("AzureKubernetesService", keys)
        aks = next(i for i in items if i["map_key"] == "AzureKubernetesService")
        self.assertEqual(aks["quantity"], 2)

    def test_deterministic_agent_uses_calculator_stub(self):
        result = run_cost_pricing_agent(
            xml_data=_AZURE_XML,
            region="eastus",
            hours_by_mxcell={"vm": 24, "aks": 24},
        )
        self.assertEqual(result.pricing_source, "azure_calculator")
        self.assertIsNotNone(result.total_usd)
        self.assertEqual(float(result.total_usd), 1234.56)


if __name__ == "__main__":
    unittest.main()
