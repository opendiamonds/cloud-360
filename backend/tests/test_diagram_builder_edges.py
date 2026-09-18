"""Edge exit/entry port and obstacle-avoiding waypoint assertions (FR-EDGE)."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from tests.helpers import backend_dir  # noqa: F401

from services.diagram_builder import (
    build_mxgraph_xml,
    compute_edge_waypoints,
    edge_anchor_ports,
)


class TestEdgeAnchorPorts(unittest.TestCase):
    def test_horizontal_left_to_right(self):
        src = {"x": 0, "y": 0, "width": 80, "height": 80}
        tgt = {"x": 200, "y": 0, "width": 80, "height": 80}
        self.assertEqual(edge_anchor_ports(src, tgt), (1.0, 0.5, 0.0, 0.5))

    def test_horizontal_right_to_left(self):
        src = {"x": 200, "y": 0, "width": 80, "height": 80}
        tgt = {"x": 0, "y": 0, "width": 80, "height": 80}
        self.assertEqual(edge_anchor_ports(src, tgt), (0.0, 0.5, 1.0, 0.5))

    def test_vertical_top_to_bottom(self):
        src = {"x": 0, "y": 0, "width": 80, "height": 80}
        tgt = {"x": 0, "y": 200, "width": 80, "height": 80}
        self.assertEqual(edge_anchor_ports(src, tgt), (0.5, 1.0, 0.5, 0.0))


class TestComputeEdgeWaypoints(unittest.TestCase):
    def test_detours_around_middle_icon(self):
        """A — B — C 同一列；A→C 不得穿過 B 本體／clearance。"""
        from services.diagram_builder import _node_obstacle_boxes, _path_clear

        a = {"id": "a", "x": 0, "y": 0, "width": 80, "height": 80}
        b = {"id": "b", "x": 120, "y": 0, "width": 80, "height": 80}
        c = {"id": "c", "x": 240, "y": 0, "width": 80, "height": 80}
        ports, waypoints = compute_edge_waypoints(a, c, [a, b, c])
        # ports 須為邊中點
        ex, ey, enx, eny = ports
        self.assertTrue((ex in (0.0, 1.0) and ey == 0.5) or (ey in (0.0, 1.0) and ex == 0.5))
        self.assertTrue(
            (enx in (0.0, 1.0) and eny == 0.5) or (eny in (0.0, 1.0) and enx == 0.5)
        )
        start = (a["x"] + a["width"] * ex, a["y"] + a["height"] * ey)
        end = (c["x"] + c["width"] * enx, c["y"] + c["height"] * eny)
        path = [start, *waypoints, end]
        self.assertTrue(
            _path_clear(path, _node_obstacle_boxes(b)),
            f"expected clear around B, ports={ports}, waypoints={waypoints}",
        )
        self.assertTrue(
            any(abs(y - 40.0) > 15 for _x, y in waypoints)
            or any(abs(x - 160.0) > 40 for x, _y in waypoints),
            f"expected detour off B center, got {waypoints}",
        )

    def test_detours_around_middle_label(self):
        """水平幹線若會穿過下方標籤帶，須改走避開標籤的路徑。"""
        from services.diagram_builder import _node_obstacle_boxes, _path_clear, _seg_hits_aabb

        a = {"id": "a", "name": "Left", "x": 0, "y": 0, "width": 80, "height": 80}
        b = {
            "id": "b",
            "name": "VeryLongServiceNameLabel",
            "x": 120,
            "y": 0,
            "width": 80,
            "height": 80,
        }
        c = {"id": "c", "name": "Right", "x": 300, "y": 0, "width": 80, "height": 80}
        label_box = _node_obstacle_boxes(b, margin=0)[1]
        # 人工「穿標籤」水平線（icon 正下方）必須判定為碰撞
        self.assertTrue(
            _seg_hits_aabb(0, label_box[1] + 5, 400, label_box[1] + 5, label_box)
        )
        ports, waypoints = compute_edge_waypoints(a, c, [a, b, c])
        self.assertEqual(ports, (1.0, 0.5, 0.0, 0.5))
        path = [(80.0, 40.0), *waypoints, (300.0, 40.0)]
        boxes = _node_obstacle_boxes(b)
        self.assertTrue(
            _path_clear(path, boxes),
            f"path should avoid icon+label boxes {boxes}, got {waypoints}",
        )

    def test_detours_around_two_blockers(self):
        """兩顆中間障礙時路徑仍應零碰撞（可多拐彎）。"""
        from services.diagram_builder import _node_obstacle_boxes, _path_clear

        a = {"id": "a", "name": "Left", "x": 0, "y": 40, "width": 80, "height": 80}
        b1 = {"id": "b1", "name": "Mid1", "x": 120, "y": 0, "width": 80, "height": 80}
        b2 = {"id": "b2", "name": "Mid2", "x": 120, "y": 120, "width": 80, "height": 80}
        c = {"id": "c", "name": "Right", "x": 280, "y": 40, "width": 80, "height": 80}
        ports, waypoints = compute_edge_waypoints(a, c, [a, b1, b2, c])
        path = [
            (a["x"] + a["width"] * ports[0], a["y"] + a["height"] * ports[1]),
            *waypoints,
            (c["x"] + c["width"] * ports[2], c["y"] + c["height"] * ports[3]),
        ]
        boxes = _node_obstacle_boxes(b1) + _node_obstacle_boxes(b2)
        self.assertTrue(
            _path_clear(path, boxes),
            f"expected clear detour, ports={ports}, waypoints={waypoints}",
        )
        from services.diagram_builder import _node_aabb, _node_obstacle_boxes

        n = {
            "id": "n",
            "name": "VeryLongServiceNameLabel",
            "x": 10,
            "y": 20,
            "width": 80,
            "height": 80,
        }
        x0, y0, x1, y1 = _node_aabb(n, margin=0)
        self.assertEqual((x0, y0, x1, y1), (10.0, 20.0, 90.0, 100.0))
        boxes = _node_obstacle_boxes(n, margin=0)
        self.assertEqual(len(boxes), 2)
        _lx0, ly0, _lx1, ly1 = boxes[1]
        self.assertGreater(ly0, 100.0 - 1e-6)
        self.assertGreater(ly1, ly0)
        self.assertLess(boxes[1][0], 10.0)  # long label wider than icon
        self.assertGreater(boxes[1][2], 90.0)

    def test_clear_horizontal_uses_mid_edge_stubs(self):
        """無障礙時仍有垂直 stub，保證從邊正中進出。"""
        a = {"id": "a", "x": 0, "y": 0, "width": 80, "height": 80}
        c = {"id": "c", "x": 200, "y": 0, "width": 80, "height": 80}
        ports, waypoints = compute_edge_waypoints(a, c, [a, c])
        self.assertEqual(ports, (1.0, 0.5, 0.0, 0.5))
        # 右中點 (80,40) → stub；左中點 (200,40) ← stub
        self.assertEqual(waypoints[0], (80 + 20, 40.0))
        self.assertEqual(waypoints[-1], (200 - 20, 40.0))
        # stub y 必須等於邊中點 y
        for _x, y in waypoints:
            self.assertAlmostEqual(y, 40.0)

    def test_ports_are_always_cardinal_mids(self):
        cases = [
            ({"x": 0, "y": 0}, {"x": 100, "y": 50}),
            ({"x": 0, "y": 0}, {"x": 50, "y": 100}),
            ({"x": 100, "y": 0}, {"x": 0, "y": 0}),
            ({"x": 0, "y": 100}, {"x": 0, "y": 0}),
        ]
        for s, t in cases:
            src = {**s, "width": 80, "height": 80}
            tgt = {**t, "width": 80, "height": 80}
            ex, ey, enx, eny = edge_anchor_ports(src, tgt)
            # 起點／終點各自恰有一軸為 0 或 1，另一軸為 0.5
            self.assertTrue({ex, ey} <= {0.0, 0.5, 1.0})
            self.assertTrue({enx, eny} <= {0.0, 0.5, 1.0})
            self.assertTrue((ex in (0.0, 1.0) and ey == 0.5) or (ey in (0.0, 1.0) and ex == 0.5))
            self.assertTrue(
                (enx in (0.0, 1.0) and eny == 0.5) or (eny in (0.0, 1.0) and enx == 0.5)
            )


class TestBuildMxgraphXmlEdges(unittest.TestCase):
    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value="<svg></svg>",
    )
    def test_edge_style_includes_exit_entry(self, _icon):
        nodes = [
            {"id": "n1", "name": "ec2", "x": 40, "y": 40},
            {"id": "n2", "name": "rds", "x": 220, "y": 40},
        ]
        edges = [{"source": "n1", "target": "n2"}]
        xml = asyncio.run(build_mxgraph_xml(None, nodes, edges))
        self.assertIn("exitX=1", xml)
        self.assertIn("exitY=0.5", xml)
        self.assertIn("entryX=0", xml)
        self.assertIn("entryY=0.5", xml)
        self.assertIn("exitPerimeter=0", xml)
        self.assertIn("entryPerimeter=0", xml)
        self.assertIn("jettySize=0", xml)
        self.assertIn("edgeStyle=orthogonalEdgeStyle", xml)

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value="<svg></svg>",
    )
    def test_aws_sample_edges_have_ports(self, _icon):
        groups = [
            {
                "id": "g1",
                "name": "VPC",
                "type": "vpc",
                "x": 0,
                "y": 0,
                "width": 500,
                "height": 300,
            }
        ]
        nodes = [
            {"id": "alb", "name": "alb", "x": 40, "y": 40},
            {"id": "ec2", "name": "ec2", "x": 200, "y": 40},
            {"id": "rds", "name": "rds", "x": 200, "y": 180},
        ]
        edges = [
            {"source": "alb", "target": "ec2"},
            {"source": "ec2", "target": "rds"},
        ]
        xml = asyncio.run(build_mxgraph_xml(groups, nodes, edges, provider="AWS"))
        self.assertIn("exitX=", xml)
        self.assertIn("entryX=", xml)
        self.assertGreaterEqual(xml.count("exitX="), 2)

    @patch(
        "services.diagram_builder.fetch_icon_from_n8n",
        new_callable=AsyncMock,
        return_value="<svg></svg>",
    )
    def test_edge_xml_has_waypoints_when_blocked(self, _icon):
        nodes = [
            {"id": "a", "name": "alb", "x": 0, "y": 0},
            {"id": "b", "name": "ec2", "x": 120, "y": 0},
            {"id": "c", "name": "rds", "x": 240, "y": 0},
        ]
        edges = [{"source": "a", "target": "c"}]
        xml = asyncio.run(build_mxgraph_xml(None, nodes, edges, provider="AWS"))
        self.assertIn('<Array as="points">', xml)
        self.assertIn("<mxPoint", xml)


if __name__ == "__main__":
    unittest.main()
