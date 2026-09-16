"""API e2e: Azure diagram + COST_PRICING_AGENT uses Calculator stub total."""

import os
import unittest

os.environ.setdefault("COST_PRICING_STUB", "1")
os.environ["COST_PRICING_AGENT"] = "1"
os.environ["COST_AZURE_CALCULATOR_STUB"] = "1"

from fastapi.testclient import TestClient

from database import get_db
from main import app
from services.auth import get_current_user
from tests.helpers import close_session, make_diagram, make_session, make_user

_AZURE_XML = (
    '<mxGraphModel><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="vm" value="Virtual Machines" style="azure2" vertex="1" parent="1"/>'
    '<mxCell id="aks" value="AKS" style="azure2" vertex="1" parent="1"/>'
    "</root></mxGraphModel>"
)


class TestCostApiAzureAgent(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.architect = make_user(self.db, username="azure-arch", role="Project_Architect")
        self.finops = make_user(self.db, username="azure-finops", role="FinOps_Analyst")
        self.diagram = make_diagram(
            self.db,
            owner=self.architect,
            title="Azure agent cost",
            xml_data=_AZURE_XML,
        )
        self.db.commit()

    def tearDown(self):
        close_session(self.db)
        app.dependency_overrides.clear()

    def _client_as(self, user):
        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def test_snapshot_uses_calculator_total_when_agent_enabled(self):
        client = self._client_as(self.architect)
        put = client.put(
            f"/api/cost/diagrams/{self.diagram.id}/region",
            json={"region": "eastus"},
        )
        self.assertEqual(put.status_code, 200, put.text)

        resp = client.get(f"/api/cost/diagrams/{self.diagram.id}")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body.get("diagram_cloud"), "azure")
        self.assertEqual(body.get("pricing_source"), "azure_calculator")
        self.assertEqual(body.get("total"), 1234.56)
        self.assertIsNotNone(body.get("pricing_as_of"))
        self.assertIsInstance(body.get("agent_assumptions"), list)
        self.assertGreater(len(body.get("agent_assumptions") or []), 0)
        calc_lines = body.get("calculator_lines") or []
        self.assertGreaterEqual(len(calc_lines), 1)
        self.assertIn("product_name", calc_lines[0])
        self.assertIn("specification", calc_lines[0])
        self.assertIn("monthly_usd", calc_lines[0])
        lines_total = sum(float(row["monthly_usd"]) for row in calc_lines)
        self.assertAlmostEqual(lines_total, 1234.56, places=2)

    def test_aws_diagram_unchanged_without_calculator_total(self):
        aws = make_diagram(
            self.db,
            owner=self.architect,
            title="AWS still line sum",
            xml_data=(
                '<mxGraphModel><root>'
                '<mxCell id="0"/><mxCell id="1" parent="0"/>'
                '<mxCell id="2" value="EC2" style="aws4" vertex="1" parent="1"/>'
                "</root></mxGraphModel>"
            ),
        )
        self.db.commit()
        client = self._client_as(self.architect)
        client.put(f"/api/cost/diagrams/{aws.id}/region", json={"region": "us-east-1"})
        body = client.get(f"/api/cost/diagrams/{aws.id}").json()
        self.assertEqual(body.get("diagram_cloud"), "aws")
        self.assertIsNone(body.get("pricing_source"))

    def test_calculator_excel_export_returns_xlsx(self):
        client = self._client_as(self.architect)
        client.put(
            f"/api/cost/diagrams/{self.diagram.id}/region",
            json={"region": "eastus"},
        )
        client.get(f"/api/cost/diagrams/{self.diagram.id}")
        resp = client.get(f"/api/cost/diagrams/{self.diagram.id}/calculator-export/xlsx")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(
            resp.headers.get("content-type", "").startswith(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        )
        self.assertTrue(resp.content.startswith(b"PK"))
        self.assertIn("attachment", resp.headers.get("content-disposition", "").lower())
        self.assertIn(".xlsx", resp.headers.get("content-disposition", "").lower())


if __name__ == "__main__":
    unittest.main()
