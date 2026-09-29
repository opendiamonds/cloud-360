"""Unit tests for diagram_builder geometry + XML assembly (A1)."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from hypothesis import given, settings, strategies as st

from tests.helpers import backend_dir  # noqa: F401

from services.diagram_builder import build_mxgraph_xml, is_inside


class TestIsInside(unittest.TestCase):
    def test_fully_inside(self):
        parent = {"x": 0, "y": 0, "width": 400, "height": 300}
        child = {"x": 10, "y": 10, "width": 80, "height": 80}
        self.assertTrue(is_inside(child, parent))

    def test_outside(self):
        parent = {"x": 0, "y": 0, "width": 100, "height": 100}
        child = {"x": 50, "y": 50, "width": 80, "height": 80}
        self.assertFalse(is_inside(child, parent))

    def test_exact_fit(self):
        box = {"x": 0, "y": 0, "width": 80, "height": 80}
        self.assertTrue(is_inside(box, box))

    @given(
        st.integers(min_value=0, max_value=500),
        st.integers(min_value=0, max_value=500),
        st.integers(min_value=50, max_value=800),
        st.integers(min_value=50, max_value=800),
    )
    @settings(max_examples=40, deadline=None)
    def test_self_contained_when_same_box(self, x, y, w, h):
        box = {"x": x, "y": y, "width": w, "height": h}
        self.assertTrue(is_inside(box, box))

    @given(
        st.integers(min_value=0, max_value=200),
        st.integers(min_value=0, max_value=200),
    )
    @settings(max_examples=30, deadline=None)
    def test_child_outside_when_shifted_beyond(self, dx, dy):
        parent = {"x": 0, "y": 0, "width": 100, "height": 100}
        # Default child size 80x80; place so bottom-right exceeds parent
        child = {"x": 100 + dx, "y": 100 + dy}
        self.assertFalse(is_inside(child, parent))


class TestBuildMxgraphXml(unittest.TestCase):
    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            asyncio.run(build_mxgraph_xml([], [], []))

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value='<svg xmlns="http://www.w3.org/2000/svg"></svg>',
    )
    def test_nodes_and_edges_produce_mxgraph(self, _icon):
        groups = [
            {
                "id": "g1",
                "name": "VPC",
                "type": "vpc",
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 300,
            }
        ]
        nodes = [
            {"id": "n1", "name": "ec2", "x": 40, "y": 40},
            {"id": "n2", "name": "rds", "x": 200, "y": 40},
        ]
        edges = [{"source": "n1", "target": "n2"}]
        xml = asyncio.run(build_mxgraph_xml(groups, nodes, edges))
        self.assertIn("<mxGraphModel>", xml)
        self.assertIn('id="g1"', xml)
        self.assertIn('id="n1"', xml)
        self.assertIn('source="n1" target="n2"', xml)
        # Nested node should reference group as parent when inside
        self.assertIn('parent="g1"', xml)

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value="<svg></svg>",
    )
    def test_edge_omitted_without_endpoints(self, _icon):
        nodes = [{"id": "n1", "name": "ec2", "x": 0, "y": 0}]
        xml = asyncio.run(
            build_mxgraph_xml(None, nodes, [{"source": "n1"}])  # missing target
        )
        self.assertNotIn("edge_", xml)

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value='<svg xmlns="http://www.w3.org/2000/svg"></svg>',
    )
    def test_gcp_groups_produce_mxgraph(self, _icon):
        groups = [
            {
                "id": "g_gcp_cloud",
                "name": "GCP Project",
                "type": "gcp_cloud",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "id": "g_gcp_vpc",
                "name": "GCP VPC Network",
                "type": "gcp_vpc",
                "x": 40,
                "y": 40,
                "width": 700,
                "height": 500,
            },
            {
                "id": "g_gcp_subnet",
                "name": "GCP Subnet",
                "type": "gcp_subnet",
                "x": 80,
                "y": 80,
                "width": 600,
                "height": 400,
            }
        ]
        nodes = [
            {"id": "n1", "name": "gce", "x": 100, "y": 100},
            {"id": "n2", "name": "gcs", "x": 300, "y": 100},
        ]
        edges = [{"source": "n1", "target": "n2"}]
        xml = asyncio.run(build_mxgraph_xml(groups, nodes, edges))
        self.assertIn("<mxGraphModel>", xml)
        self.assertIn('id="g_gcp_cloud"', xml)
        self.assertIn('id="g_gcp_vpc"', xml)
        self.assertIn('id="g_gcp_subnet"', xml)
        self.assertIn('id="n1"', xml)
        self.assertIn('parent="g_gcp_subnet"', xml)
        self.assertIn('strokeColor=#4285F4', xml)  # GCP Cloud style color
        self.assertIn('strokeColor=#34A853', xml)  # GCP VPC style color
        self.assertIn('strokeColor=#FBBC05', xml)  # GCP Subnet style color

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value='<svg xmlns="http://www.w3.org/2000/svg"></svg>',
    )
    def test_azure_groups_produce_mxgraph(self, mock_icon):
        groups = [
            {
                "id": "g_az_cloud",
                "name": "Azure Subscription",
                "type": "azure_cloud",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "id": "g_az_vnet",
                "name": "Azure VNet",
                "type": "azure_vnet",
                "x": 40,
                "y": 40,
                "width": 700,
                "height": 500,
            },
            {
                "id": "g_az_subnet",
                "name": "Frontend Subnet",
                "type": "azure_subnet",
                "x": 80,
                "y": 80,
                "width": 600,
                "height": 400,
            }
        ]
        nodes = [
            {"id": "n1", "name": "aks", "x": 100, "y": 100},
        ]
        edges = []
        xml = asyncio.run(build_mxgraph_xml(groups, nodes, edges))
        self.assertIn("<mxGraphModel>", xml)
        self.assertIn('id="g_az_cloud"', xml)
        self.assertIn('id="g_az_vnet"', xml)
        self.assertIn('id="g_az_subnet"', xml)
        self.assertIn('parent="g_az_subnet"', xml)
        self.assertIn('strokeColor=#0078D4', xml)  # Azure Cloud style color
        self.assertIn('strokeColor=#5C2D91', xml)  # Azure VNet style color
        self.assertIn('strokeColor=#00BCF2', xml)  # Azure Subnet style color
        mock_icon.assert_called_once_with("aks", provider="Azure")


class TestNormalizeDiagramLayout(unittest.TestCase):
    def test_overflow_nodes_stay_inside_group_with_label(self):
        from services.diagram_builder import (
            _label_width,
            _node_footprint_h,
            normalize_diagram_layout,
        )

        groups = [
            {
                "id": "sub",
                "name": "Private Subnet",
                "type": "private_subnet",
                "x": 0,
                "y": 0,
                "width": 220,
                "height": 100,  # 故意偏矮，節點＋標籤會溢出
            }
        ]
        nodes = [
            {"id": "n1", "name": "ec2", "x": 10, "y": 70},
            {"id": "n2", "name": "rds", "x": 140, "y": 70},
        ]
        normalize_diagram_layout(groups, nodes)
        g = groups[0]
        for n in nodes:
            lw = _label_width(n)
            cx = n["x"] + 40
            self.assertGreaterEqual(cx - lw / 2, g["x"] - 0.5)
            self.assertLessEqual(cx + lw / 2, g["x"] + g["width"] + 0.5)
            self.assertGreaterEqual(n["y"], g["y"] - 0.5)
            self.assertLessEqual(
                n["y"] + _node_footprint_h(),
                g["y"] + g["height"] + 0.5,
            )

    def test_stacked_overlapping_layers_get_gap(self):
        """上下幾乎重叠的 sibling 必須被拉開間距。"""
        from services.diagram_builder import _SIBLING_GAP, normalize_diagram_layout

        groups = [
            {
                "id": "az",
                "name": "AZ1",
                "type": "az",
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 400,
            },
            {
                "id": "pub",
                "name": "Public",
                "type": "public_subnet",
                "x": 40,
                "y": 60,
                "width": 300,
                "height": 160,
            },
            {
                "id": "priv",
                "name": "Private",
                "type": "private_subnet",
                "x": 50,
                "y": 100,  # 與 public 重叠
                "width": 300,
                "height": 180,
            },
        ]
        nodes = [
            {"id": "n1", "name": "alb", "x": 60, "y": 90},
            {"id": "n2", "name": "ec2", "x": 70, "y": 140},
        ]
        normalize_diagram_layout(groups, nodes)
        pub = next(g for g in groups if g["id"] == "pub")
        priv = next(g for g in groups if g["id"] == "priv")
        top, bot = (pub, priv) if pub["y"] <= priv["y"] else (priv, pub)
        self.assertLessEqual(
            float(top["y"]) + float(top["height"]) + _SIBLING_GAP - 1e-6,
            float(bot["y"]),
        )

    def test_nodes_are_centered_inside_group(self):
        from services.diagram_builder import normalize_diagram_layout

        groups = [
            {
                "id": "sub",
                "name": "Public Subnet",
                "type": "public_subnet",
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 280,
            }
        ]
        nodes = [
            {"id": "n1", "name": "alb", "x": 0, "y": 0},
            {"id": "n2", "name": "ec2", "x": 20, "y": 0},
        ]
        normalize_diagram_layout(groups, nodes)
        g = groups[0]
        mid_x = g["x"] + g["width"] / 2.0
        mid_y = g["y"] + g["height"] / 2.0
        node_mid_x = sum(n["x"] + 40 for n in nodes) / len(nodes)
        node_mid_y = sum(n["y"] + 40 for n in nodes) / len(nodes)
        self.assertAlmostEqual(node_mid_x, mid_x, delta=30)
        # 垂直：網格＋標籤保留後中心應接近內容區中線
        self.assertAlmostEqual(node_mid_y, mid_y, delta=40)

    def test_multi_row_block_is_centered_as_a_whole(self):
        """多排時整坨置中；最後一排不滿也於該排內水平置中。"""
        from services.diagram_builder import (
            _GROUP_PAD_BOTTOM,
            _GROUP_PAD_TOP,
            _CONTENT_INSET,
            _label_width,
            _node_footprint_h,
            normalize_diagram_layout,
        )

        groups = [
            {
                "id": "sub",
                "name": "Private Subnet",
                "type": "private_subnet",
                "x": 0,
                "y": 0,
                "width": 360,  # 約兩欄寬 → 3 個 icon 變兩排
                "height": 320,
            }
        ]
        nodes = [
            {"id": "n1", "name": "a", "x": 0, "y": 0},
            {"id": "n2", "name": "b", "x": 10, "y": 0},
            {"id": "n3", "name": "c", "x": 20, "y": 0},
        ]
        normalize_diagram_layout(groups, nodes)
        g = groups[0]
        # 以標籤盒算整塊中心，應對齊 layer 內容區中心
        boxes = []
        for n in nodes:
            lw = _label_width(n)
            cx = n["x"] + 40
            boxes.append(
                (cx - lw / 2, n["y"], cx + lw / 2, n["y"] + _node_footprint_h())
            )
        min_x = min(b[0] for b in boxes)
        max_x = max(b[2] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_y = max(b[3] for b in boxes)
        block_cx = (min_x + max_x) / 2
        block_cy = (min_y + max_y) / 2
        content_cx = g["x"] + g["width"] / 2
        content_cy = (
            g["y"]
            + _GROUP_PAD_TOP
            + (g["height"] - _GROUP_PAD_TOP - _GROUP_PAD_BOTTOM - _CONTENT_INSET) / 2
        )
        self.assertAlmostEqual(block_cx, content_cx, delta=8)
        self.assertAlmostEqual(block_cy, content_cy, delta=12)

        # 最後一排（通常 1 個）應靠近水平中線，而非貼齊第一排左緣
        ys = sorted({n["y"] for n in nodes})
        self.assertGreaterEqual(len(ys), 2)
        last_row = [n for n in nodes if n["y"] == max(ys)]
        last_cx = sum(n["x"] + 40 for n in last_row) / len(last_row)
        self.assertAlmostEqual(last_cx, content_cx, delta=8)

    def test_long_labels_increase_icon_spacing(self):
        from services.diagram_builder import _label_width, normalize_diagram_layout

        groups = [
            {
                "id": "sub",
                "name": "Private Subnet",
                "type": "private_subnet",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 300,
            }
        ]
        nodes = [
            {"id": "n1", "name": "NATGatewayEndpointVeryLong", "x": 10, "y": 60},
            {"id": "n2", "name": "ApplicationLoadBalancerLong", "x": 100, "y": 60},
        ]
        normalize_diagram_layout(groups, nodes)
        dx = abs(nodes[1]["x"] - nodes[0]["x"])
        # 兩標籤半寬 + 間隙 約等於 pitch；應明顯大於預設 80+48
        min_needed = (_label_width(nodes[0]) + _label_width(nodes[1])) / 2 + 8
        self.assertGreaterEqual(dx, min(min_needed, 160))
        # 標籤盒不重疊（置中於 icon）
        def label_span(n):
            lw = _label_width(n)
            cx = n["x"] + 40
            return cx - lw / 2, cx + lw / 2

        a0, a1 = label_span(nodes[0])
        b0, b1 = label_span(nodes[1])
        self.assertTrue(a1 <= b0 + 1e-6 or b1 <= a0 + 1e-6)

    def test_sibling_layers_do_not_overlap_and_align(self):
        from services.diagram_builder import _SIBLING_GAP, _groups_bbox_overlap, normalize_diagram_layout

        groups = [
            {
                "id": "vpc",
                "name": "VPC",
                "type": "vpc",
                "x": 0,
                "y": 0,
                "width": 500,
                "height": 400,
            },
            {
                "id": "az1",
                "name": "AZ1",
                "type": "az",
                "x": 40,
                "y": 60,
                "width": 220,
                "height": 280,
            },
            {
                "id": "az2",
                "name": "AZ2",
                "type": "az",
                "x": 180,  # 故意與 az1 重疊
                "y": 80,
                "width": 220,
                "height": 260,
            },
        ]
        nodes = [
            {"id": "n1", "name": "ec2", "x": 60, "y": 120},
            {"id": "n2", "name": "rds", "x": 200, "y": 140},
        ]
        normalize_diagram_layout(groups, nodes)
        az1 = next(g for g in groups if g["id"] == "az1")
        az2 = next(g for g in groups if g["id"] == "az2")
        self.assertFalse(
            _groups_bbox_overlap(az1, az2, gap=_SIBLING_GAP),
            f"siblings still overlap: {az1} vs {az2}",
        )
        # 若並排則頂對齊；若上下排列則左緣對齊
        if abs(float(az1["y"]) - float(az2["y"])) <= 1.0:
            self.assertAlmostEqual(float(az1["y"]), float(az2["y"]), delta=1.0)
        else:
            self.assertAlmostEqual(float(az1["x"]), float(az2["x"]), delta=1.0)


class TestIconOverlapAndCongestion(unittest.TestCase):
    def test_ensure_icons_non_overlapping_same_layer(self):
        from services.diagram_builder import (
            _bboxes_overlap,
            _merged_node_bbox,
            relieve_icon_edge_congestion,
        )

        groups = [
            {
                "id": "sub",
                "name": "Subnet",
                "type": "private_subnet",
                "x": 0,
                "y": 0,
                "width": 500,
                "height": 320,
            }
        ]
        nodes = [
            {"id": "n1", "name": "ec2", "x": 100, "y": 80, "_layout_gid": "sub"},
            {"id": "n2", "name": "rds", "x": 110, "y": 85, "_layout_gid": "sub"},
        ]
        relieve_icon_edge_congestion(groups, nodes, edges=[])
        self.assertFalse(
            _bboxes_overlap(
                _merged_node_bbox(nodes[0]), _merged_node_bbox(nodes[1]), gap=16
            )
        )

    def test_relocate_icon_away_from_crossing_edge(self):
        """中間 icon 被 A→C 穿過時，應在同層移到過線較少處。"""
        from services.diagram_builder import (
            _count_foreign_edge_hits,
            relieve_icon_edge_congestion,
        )

        groups = [
            {
                "id": "sub",
                "name": "Subnet",
                "type": "public_subnet",
                "x": 0,
                "y": 0,
                "width": 520,
                "height": 360,
            }
        ]
        nodes = [
            {
                "id": "a",
                "name": "left",
                "x": 40,
                "y": 140,
                "width": 80,
                "height": 80,
                "_layout_gid": "sub",
            },
            {
                "id": "b",
                "name": "blocker",
                "x": 200,
                "y": 140,
                "width": 80,
                "height": 80,
                "_layout_gid": "sub",
            },
            {
                "id": "c",
                "name": "right",
                "x": 380,
                "y": 140,
                "width": 80,
                "height": 80,
                "_layout_gid": "sub",
            },
        ]
        edges = [{"source": "a", "target": "c"}]
        before_b = (nodes[1]["x"], nodes[1]["y"])
        relieve_icon_edge_congestion(groups, nodes, edges, hit_threshold=1, rounds=2)
        node_by_id = {n["id"]: n for n in nodes}
        hits_after = _count_foreign_edge_hits(
            node_by_id["b"], nodes, edges, node_by_id
        )
        self.assertTrue(
            hits_after == 0 or (nodes[1]["x"], nodes[1]["y"]) != before_b,
            f"blocker not relocated; hits={hits_after}, pos={(nodes[1]['x'], nodes[1]['y'])}",
        )


if __name__ == "__main__":
    unittest.main()
