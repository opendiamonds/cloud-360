"""Tests for compound cloud diagram builder and n8n icon service gateway (Unit U1 & U2).

Verifies:
- U1: fetch_icon_from_n8n with provider="compound"
- U1: 5.0-second timeout fallback handling
- U1: 40x40 gray-background text fallback SVG generation with uppercase truncated text
- U1: in-memory caching for repeated lookups
"""

import logging
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import tests.helpers  # noqa: F401  -- installs psycopg2 stub if needed

import httpx
import xml.etree.ElementTree as ET

from services.diagram_builder import (
    _normalise_icon_name,
    build_compound_diagram_xml,
    fetch_icon_from_n8n,
    generate_fallback_svg,
)


def _response(status_code=200, payload=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=payload)
    return response


def _client_returning(response=None, side_effect=None):
    client = MagicMock()
    if side_effect:
        client.post = AsyncMock(side_effect=side_effect)
    else:
        client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestFallbackSvgSpec(unittest.TestCase):
    """Verifies Fallback SVG meets the 40x40 dimension and visual specs."""

    def test_fallback_svg_dimensions_and_colors(self):
        svg = generate_fallback_svg("CloudSQL")
        self.assertIn('viewBox="0 0 40 40"', svg)
        self.assertIn('width="40"', svg)
        self.assertIn('height="40"', svg)
        self.assertIn('fill="#F1F5F9"', svg)
        self.assertIn('stroke="#CBD5E1"', svg)
        self.assertIn('fill="#475569"', svg)
        # Should truncate to first 4 uppercase characters
        self.assertIn(">CLOU</text>", svg)

    def test_fallback_svg_short_name(self):
        svg = generate_fallback_svg("s3")
        self.assertIn(">S3</text>", svg)

    def test_fallback_svg_xml_escaping(self):
        svg = generate_fallback_svg("<>&\"")
        self.assertIn("&lt;&gt;&amp;", svg)


class TestIconServiceGateway(unittest.IsolatedAsyncioTestCase):
    """Verifies U1: fetch_icon_from_n8n compound provider behavior and resilience."""

    async def test_fetch_icon_compound_payload_success(self):
        """BR1.1: Payload contains service and provider='compound'."""
        mock_resp = _response(status_code=200, text='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><circle cx="20" cy="20" r="15"/></svg>')
        client = _client_returning(response=mock_resp)

        with patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://n8n.example/webhook", "DISABLE_ICON_CACHE": "1"}):
            with patch("httpx.AsyncClient", return_value=client):
                svg = await fetch_icon_from_n8n("ec2success", provider="compound")

        self.assertIn("<circle", svg)
        client.post.assert_called_once()
        _, kwargs = client.post.call_args
        self.assertEqual(kwargs.get("json"), {"service": "ec2success", "provider": "compound"})
        self.assertEqual(kwargs.get("timeout"), 5.0)

    async def test_fetch_icon_compound_timeout_fallback(self):
        """BR1.2 & BR1.3: Timeout triggers fallback SVG without unhandled exception."""
        client = _client_returning(side_effect=httpx.TimeoutException("Read timeout after 5.0s"))

        with patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://n8n.example/webhook"}):
            with patch("httpx.AsyncClient", return_value=client):
                svg = await fetch_icon_from_n8n("bigquery", provider="compound")

        self.assertIn('viewBox="0 0 40 40"', svg)
        self.assertIn(">BIGQ</text>", svg)

    async def test_fetch_icon_compound_http_error_fallback(self):
        """BR1.3: Non-200 responses fallback gracefully."""
        mock_resp = _response(status_code=500, text="Internal Server Error")
        client = _client_returning(response=mock_resp)

        with patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://n8n.example/webhook"}):
            with patch("httpx.AsyncClient", return_value=client):
                svg = await fetch_icon_from_n8n("aks", provider="compound")

        self.assertIn('viewBox="0 0 40 40"', svg)
        self.assertIn(">AKS</text>", svg)

    async def test_fetch_icon_caching(self):
        """NFR1.1: Repeated icon lookup uses cache and avoids redundant HTTP POST."""
        mock_resp = _response(status_code=200, text='<svg>cached_ec2</svg>')
        client = _client_returning(response=mock_resp)

        with patch.dict(os.environ, {"N8N_WEBHOOK_URL": "https://n8n.example/webhook"}):
            with patch("httpx.AsyncClient", return_value=client):
                svg1 = await fetch_icon_from_n8n("rds_mysql", provider="compound")
                svg2 = await fetch_icon_from_n8n("rds_mysql", provider="compound")

        self.assertEqual(svg1, "<svg>cached_ec2</svg>")
        self.assertEqual(svg2, "<svg>cached_ec2</svg>")
        # Call count should be exactly 1 due to in-memory caching
        self.assertEqual(client.post.call_count, 1)


class TestCompoundDiagramBuilder(unittest.IsolatedAsyncioTestCase):
    """Verifies U2: build_compound_diagram_xml geometric topology and cross-cloud edge rendering."""

    def setUp(self):
        self.clouds_spec = [
            {
                "id": "aws_c",
                "provider": "aws",
                "title": "AWS Primary Region",
                "nodes": [
                    {"id": "aws_ec2", "service_name": "ec2", "label": "Web App EC2"},
                    {"id": "aws_rds", "service_name": "rds", "label": "Primary RDS"},
                ],
            },
            {
                "id": "azure_c",
                "provider": "azure",
                "title": "Azure Secondary Region",
                "nodes": [
                    {"id": "azure_vm", "service_name": "virtual-machines", "label": "App VM"},
                ],
            },
            {
                "id": "gcp_c",
                "provider": "gcp",
                "title": "GCP Analytics Region",
                "nodes": [
                    {"id": "gcp_bq", "service_name": "bigquery", "label": "Data Warehouse"},
                ],
            },
        ]
        self.connections_spec = [
            {
                "source_node_id": "azure_vm",
                "target_node_id": "aws_ec2",
                "protocol_name": "VPN Tunnel",
            },
            {
                "source_node_id": "aws_ec2",
                "target_node_id": "gcp_bq",
                "protocol_name": "Cloud Interconnect",
            },
        ]

    async def _build(self, clouds, conns=None):
        with patch.dict(os.environ, {"N8N_WEBHOOK_URL": ""}):
            return await build_compound_diagram_xml(clouds, conns)

    async def test_hub_and_spoke_layout_ordering_and_buffer(self):
        """BR2.2 & BR2.3: Order Azure (left) -> AWS (center) -> GCP (right) with 120px corridor."""
        xml_str = await self._build(self.clouds_spec, self.connections_spec)
        root = ET.fromstring(xml_str)

        # 查找三個雲端容器 mxCell
        azure_cell = root.find(".//mxCell[@id='azure_c']")
        aws_cell = root.find(".//mxCell[@id='aws_c']")
        gcp_cell = root.find(".//mxCell[@id='gcp_c']")

        self.assertIsNotNone(azure_cell)
        self.assertIsNotNone(aws_cell)
        self.assertIsNotNone(gcp_cell)

        az_geom = azure_cell.find("mxGeometry")
        aws_geom = aws_cell.find("mxGeometry")
        gcp_geom = gcp_cell.find("mxGeometry")

        az_x = float(az_geom.attrib["x"])
        az_w = float(az_geom.attrib["width"])
        aws_x = float(aws_geom.attrib["x"])
        aws_w = float(aws_geom.attrib["width"])
        gcp_x = float(gcp_geom.attrib["x"])

        # 驗證水平排列：Azure 在最左側，AWS 在中間，GCP 在右側
        self.assertLess(az_x, aws_x)
        self.assertLess(aws_x, gcp_x)

        # 驗證 Azure 與 AWS 間隔恰為 120px 走廊
        self.assertAlmostEqual(aws_x, az_x + az_w + 120.0, delta=1.0)
        # 驗證 AWS 與 GCP 間隔恰為 120px 走廊
        self.assertAlmostEqual(gcp_x, aws_x + aws_w + 120.0, delta=1.0)

        # 驗證中央 AWS 寬度 >= 480，雙翼 >= 360
        self.assertGreaterEqual(aws_w, 480.0)
        self.assertGreaterEqual(az_w, 360.0)

    async def test_group_styles_application(self):
        """BR2.1: Containers apply correct group styles."""
        from services.diagram_builder import GROUP_STYLES

        xml_str = await self._build(self.clouds_spec)
        root = ET.fromstring(xml_str)

        azure_cell = root.find(".//mxCell[@id='azure_c']")
        aws_cell = root.find(".//mxCell[@id='aws_c']")
        gcp_cell = root.find(".//mxCell[@id='gcp_c']")

        self.assertEqual(azure_cell.attrib.get("style", ""), GROUP_STYLES["azure_cloud"])
        self.assertEqual(aws_cell.attrib.get("style", ""), GROUP_STYLES["aws_cloud"])
        self.assertEqual(gcp_cell.attrib.get("style", ""), GROUP_STYLES["gcp_cloud"])

    async def test_cross_cloud_orthogonal_edges_and_capsule_labels(self):
        """BR2.4 & BR2.5: Edge has orthogonal routing and white capsule protocol label."""
        xml_str = await self._build(self.clouds_spec, self.connections_spec)
        root = ET.fromstring(xml_str)

        conn_0 = root.find(".//mxCell[@id='conn_0']")
        conn_1 = root.find(".//mxCell[@id='conn_1']")

        self.assertIsNotNone(conn_0)
        self.assertIsNotNone(conn_1)

        # 檢查直角折線樣式
        self.assertIn("edgeStyle=orthogonalEdgeStyle", conn_0.attrib["style"])
        self.assertIn("edgeStyle=orthogonalEdgeStyle", conn_1.attrib["style"])

        # 檢查白色膠囊圓角背景標籤樣式
        self.assertIn("labelBackgroundColor=#FFFFFF", conn_0.attrib["style"])
        self.assertIn("labelBackgroundColor=#FFFFFF", conn_1.attrib["style"])
        self.assertIn("fontColor=#1E293B", conn_0.attrib["style"])
        self.assertIn("rounded=1", conn_0.attrib["style"])

        # 檢查標籤文字
        self.assertEqual(conn_0.attrib["value"], "VPN Tunnel")
        self.assertEqual(conn_1.attrib["value"], "Cloud Interconnect")

    async def test_compound_xml_validity(self):
        """NFR4.1: Valid Draw.io / mxGraph XML document."""
        xml_str = await self._build(self.clouds_spec, self.connections_spec)
        root = ET.fromstring(xml_str)
        self.assertEqual(root.tag, "mxfile")
        diagram = root.find("diagram")
        self.assertIsNotNone(diagram)
        mx_graph_model = diagram.find("mxGraphModel")
        self.assertIsNotNone(mx_graph_model)


if __name__ == "__main__":
    unittest.main()

