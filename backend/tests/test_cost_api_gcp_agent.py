"""API e2e: GCP diagram + COST_PRICING_AGENT uses Calculator stub total."""

import os
import unittest

os.environ.setdefault("COST_PRICING_STUB", "1")
os.environ["COST_PRICING_AGENT"] = "1"
os.environ["COST_GCP_CALCULATOR_STUB"] = "1"

from fastapi.testclient import TestClient

from database import get_db
from main import app
from services.auth import get_current_user
from tests.helpers import close_session, make_diagram, make_session, make_user

_GCP_XML = (
    '<mxGraphModel><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="ce" value="Compute Engine" style="shape=mxgraph.gcp2.compute_engine" vertex="1" parent="1"/>'
    '<mxCell id="gke" value="GKE" style="shape=mxgraph.gcp.gke" vertex="1" parent="1"/>'
    "</root></mxGraphModel>"
)


class TestCostApiGcpAgent(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.architect = make_user(self.db, username="gcp-arch", role="Project_Architect")
        self.finops = make_user(self.db, username="gcp-finops", role="FinOps_Analyst")
        self.diagram = make_diagram(
            self.db,
            owner=self.architect,
            title="GCP agent cost",
            xml_data=_GCP_XML,
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
            json={"region": "us-central1"},
        )
        self.assertEqual(put.status_code, 200, put.text)

        resp = client.get(f"/api/cost/diagrams/{self.diagram.id}")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body.get("diagram_cloud"), "gcp")
        self.assertEqual(body.get("pricing_source"), "gcp_calculator")
        self.assertEqual(body.get("total"), 987.65)
        self.assertIsNotNone(body.get("pricing_as_of"))
        self.assertIsInstance(body.get("agent_assumptions"), list)
        self.assertGreater(len(body.get("agent_assumptions") or []), 0)
        calc_lines = body.get("calculator_lines") or []
        self.assertGreaterEqual(len(calc_lines), 1)
        self.assertIn("product_name", calc_lines[0])
        self.assertIn("specification", calc_lines[0])
        self.assertIn("monthly_usd", calc_lines[0])

    def test_calculator_csv_export_returns_csv(self):
        client = self._client_as(self.architect)
        client.put(
            f"/api/cost/diagrams/{self.diagram.id}/region",
            json={"region": "us-central1"},
        )
        client.get(f"/api/cost/diagrams/{self.diagram.id}")
        resp = client.get(f"/api/cost/diagrams/{self.diagram.id}/calculator-export/csv")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.headers.get("content-type", "").startswith("text/csv"))
        self.assertIn(b"service_display_name", resp.content)
        self.assertIn("attachment", resp.headers.get("content-disposition", "").lower())
        self.assertIn(".csv", resp.headers.get("content-disposition", "").lower())

    def test_gcp_diagram_rejects_xlsx_export(self):
        client = self._client_as(self.architect)
        client.put(
            f"/api/cost/diagrams/{self.diagram.id}/region",
            json={"region": "us-central1"},
        )
        client.get(f"/api/cost/diagrams/{self.diagram.id}")
        resp = client.get(f"/api/cost/diagrams/{self.diagram.id}/calculator-export/xlsx")
        self.assertEqual(resp.status_code, 400, resp.text)


if __name__ == "__main__":
    unittest.main()
