"""
diagram_builder.py — A1 架構圖組裝模組

職責：
  將 LLM tool 回傳的 groups / nodes / edges（絕對座標）轉成 draw.io mxGraphModel XML。
  節點圖示透過 n8n webhook 取得 SVG；失敗時使用灰底 fallback。

注意：
  - 本模組不含 LLM 呼叫，僅負責幾何巢狀與 XML 字串組裝。
  - 行為需與重構前 agent_router 內嵌邏輯一致。
"""

from __future__ import annotations

import base64
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 進度回呼：用於 SSE progress（例如「正在取得 EC2 圖示」）
ProgressCallback = Callable[[str], Awaitable[None]]

# draw.io AWS 群組樣式（與重構前相同）
GROUP_STYLES = {
    "aws_cloud": (
        "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;"
        "strokeColor=#232F3E;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#232F3E;dashed=0;"
    ),
    "vpc": (
        "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc2;"
        "strokeColor=#8C4FFF;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#AAB7B8;dashed=0;"
    ),
    "az": (
        "fillColor=none;strokeColor=#147EBA;dashed=1;verticalAlign=top;"
        "fontStyle=0;fontColor=#147EBA;whiteSpace=wrap;html=1;"
    ),
    "public_subnet": (
        "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;grStroke=0;"
        "strokeColor=#7AA116;fillColor=#F2F6E8;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#248814;dashed=0;"
    ),
    "private_subnet": (
        "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_security_group;grStroke=0;"
        "strokeColor=#00A4A6;fillColor=#E6F6F7;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#147EBA;dashed=0;"
    ),
    "gcp_cloud": (
        "shape=mxgraph.aws4.group;strokeColor=#4285F4;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#4285F4;dashed=0;"
    ),
    "gcp_vpc": (
        "shape=mxgraph.aws4.group;strokeColor=#34A853;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#34A853;dashed=0;"
    ),
    "gcp_subnet": (
        "shape=mxgraph.aws4.group;strokeColor=#FBBC05;fillColor=#FFFDF0;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#FBBC05;dashed=0;"
    ),
    "azure_cloud": (
        "shape=mxgraph.aws4.group;strokeColor=#0078D4;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#0078D4;dashed=0;"
    ),
    "azure_vnet": (
        "shape=mxgraph.aws4.group;strokeColor=#5C2D91;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#5C2D91;dashed=0;"
    ),
    "azure_resource_group": (
        "shape=mxgraph.aws4.group;strokeColor=#008272;fillColor=none;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#008272;dashed=0;"
    ),
    "azure_subnet": (
        "shape=mxgraph.aws4.group;strokeColor=#00BCF2;fillColor=#F0F9FE;verticalAlign=top;align=left;"
        "spacingLeft=30;fontColor=#00BCF2;dashed=0;"
    ),
}


def is_inside(child: dict[str, Any], parent: dict[str, Any]) -> bool:
    """判斷 child 的邊界盒是否完全落在 parent 內（節點預設 80x80）。"""
    cw = child.get("width", 80)
    ch = child.get("height", 80)
    return (
        child["x"] >= parent["x"]
        and child["y"] >= parent["y"]
        and child["x"] + cw <= parent["x"] + parent.get("width", 0)
        and child["y"] + ch <= parent["y"] + parent.get("height", 0)
    )


def edge_anchor_ports(
    src: dict[str, Any], tgt: dict[str, Any]
) -> tuple[float, float, float, float]:
    """
    依來源／目標節點中心相對位置，選 mid-side exit／entry ports，
    讓正交邊接在 icon 邊緣而非穿過圖示中心。
    回傳 (exitX, exitY, entryX, entryY)，座標為 0–1 相對單元。
    """
    sw = float(src.get("width", 80))
    sh = float(src.get("height", 80))
    tw = float(tgt.get("width", 80))
    th = float(tgt.get("height", 80))
    sx = float(src["x"]) + sw / 2.0
    sy = float(src["y"]) + sh / 2.0
    tx = float(tgt["x"]) + tw / 2.0
    ty = float(tgt["y"]) + th / 2.0
    dx = tx - sx
    dy = ty - sy
    if abs(dx) >= abs(dy):
        if dx >= 0:
            return (1.0, 0.5, 0.0, 0.5)
        return (0.0, 0.5, 1.0, 0.5)
    if dy >= 0:
        return (0.5, 1.0, 0.5, 0.0)
    return (0.5, 0.0, 0.5, 1.0)


# 路徑與其他 icon 的最小間距（像素）— 寧可多拐彎，避免壓到圖示／文字
_EDGE_CLEARANCE = 22.0
# 進出邊垂直 stub：確保線從／到邊的正中心垂直進出（短 stub，不穿障礙）
_PORT_STUB = 20.0
# 節點標籤（verticalLabelPosition=bottom）佔位估算，供避障用
_LABEL_CHAR_W = 7.0
_LABEL_MAX_W = 160.0
_LABEL_HEIGHT = 28.0
_LABEL_GAP = 4.0
# 節點與 group 排版
_NODE_W = 80
_NODE_H = 80
_NODE_GAP_X = 48
_NODE_GAP_Y = 36
_GROUP_PAD_X = 28
_GROUP_PAD_TOP = 52  # AWS／雲 group 標題列
_GROUP_PAD_BOTTOM = 20
_LABEL_RESERVE = _LABEL_GAP + _LABEL_HEIGHT  # icon 下方文字保留高度
_LABEL_SEP = 16  # 相鄰標籤之間的最小間隙
_SIBLING_GAP = 48  # 同層 sibling group 間距（避免填色遮住隔壁圖示／文字）
_ROW_Y_TOL = 80  # 判斷同列 sibling 的 Y 容差
_CONTENT_INSET = 8  # 標籤相對 layer 邊的內縮


def _node_footprint_h() -> float:
    """icon + 下方標籤佔用的垂直高度。"""
    return float(_NODE_H + _LABEL_RESERVE)


def _label_width(node: dict[str, Any]) -> float:
    """估算節點下方標籤寬度（與避障用公式一致）。"""
    label = str(node.get("name") or node.get("label") or "").strip()
    if not label:
        return float(_NODE_W)
    return float(max(_NODE_W, min(_LABEL_MAX_W, len(label) * _LABEL_CHAR_W)))


def _side_pad_for_nodes(nodes: list[dict[str, Any]]) -> float:
    """水平內距：基本 padding + 最長標籤相對 icon 的外伸，確保文字不穿出 layer。"""
    if not nodes:
        return float(_GROUP_PAD_X)
    max_overhang = max(0.0, max((_label_width(n) - _NODE_W) / 2.0 for n in nodes))
    return float(_GROUP_PAD_X + max_overhang + _CONTENT_INSET)


def _node_pitch_x(nodes: list[dict[str, Any]]) -> float:
    """
    水平節點間距（左緣到左緣）：依最長標籤拉開，避免文字互疊。
    標籤置中於 icon 下，故 pitch >= max_label + _LABEL_SEP。
    """
    if not nodes:
        return float(_NODE_W + _NODE_GAP_X)
    max_lw = max(_label_width(n) for n in nodes)
    return float(max(_NODE_W + _NODE_GAP_X, max_lw + _LABEL_SEP))


def _point_in_group(g: dict[str, Any], px: float, py: float) -> bool:
    return (
        float(g["x"]) <= px <= float(g["x"]) + float(g.get("width", 0))
        and float(g["y"]) <= py <= float(g["y"]) + float(g.get("height", 0))
    )


def _bbox_overlaps_group(node: dict[str, Any], g: dict[str, Any]) -> bool:
    nx0 = float(node["x"])
    ny0 = float(node["y"])
    nx1 = nx0 + float(node.get("width", _NODE_W))
    ny1 = ny0 + _node_footprint_h()
    gx0 = float(g["x"])
    gy0 = float(g["y"])
    gx1 = gx0 + float(g.get("width", 0))
    gy1 = gy0 + float(g.get("height", 0))
    return not (nx1 < gx0 or nx0 > gx1 or ny1 < gy0 or ny0 > gy1)


def _smallest_covering_group(
    groups: list[dict[str, Any]], px: float, py: float
) -> dict[str, Any] | None:
    """面積由小到大：回傳包含點的最小 group。"""
    ordered = sorted(
        groups, key=lambda g: float(g.get("width", 0)) * float(g.get("height", 0))
    )
    for g in ordered:
        if _point_in_group(g, px, py):
            return g
    return None


def _assign_nodes_to_groups(
    groups: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> None:
    """依中心點（退而求重疊）指定 layout group；寫入 node['_layout_gid']。"""
    for node in nodes:
        node["width"] = _NODE_W
        node["height"] = _NODE_H
        cx = float(node["x"]) + _NODE_W / 2.0
        cy = float(node["y"]) + _NODE_H / 2.0
        best = _smallest_covering_group(groups, cx, cy)
        if best is None:
            ordered = sorted(
                groups,
                key=lambda g: float(g.get("width", 0)) * float(g.get("height", 0)),
            )
            for g in ordered:
                if _bbox_overlaps_group(node, g):
                    best = g
                    break
        node["_layout_gid"] = best["id"] if best else None


def _grow_group_to_fit(
    g: dict[str, Any],
    *,
    need_w: float,
    need_h: float,
) -> None:
    """以 group 原點不動，向右／下擴大內容區以容納 need_w × need_h。"""
    min_w = need_w + 2 * _GROUP_PAD_X
    min_h = need_h + _GROUP_PAD_TOP + _GROUP_PAD_BOTTOM
    g["width"] = max(float(g.get("width", 0)), min_w)
    g["height"] = max(float(g.get("height", 0)), min_h)


def _layout_nodes_inside_group(
    g: dict[str, Any], children: list[dict[str, Any]]
) -> None:
    """
    同 group 內節點：網格排列後「整坨」水平＋垂直置中（含多排）。
    最後一排若不滿，該排也在整塊寬度內水平置中；側邊／底部內距含標籤。
    """
    if not children:
        return
    children = sorted(
        children, key=lambda n: (float(n.get("y", 0)), float(n.get("x", 0)))
    )
    n = len(children)
    cell_w = float(_NODE_W)
    cell_h = _node_footprint_h()
    pitch_x = _node_pitch_x(children)
    gap_y = float(_NODE_GAP_Y)
    side_pad = _side_pad_for_nodes(children)
    bottom_pad = float(_GROUP_PAD_BOTTOM + _CONTENT_INSET)

    inner_w = max(1.0, float(g.get("width", 0)) - 2 * side_pad)
    cols = max(1, min(n, int((inner_w - cell_w) // pitch_x) + 1 if pitch_x > 0 else 1))
    cols = max(1, min(n, cols))
    rows_n = (n + cols - 1) // cols
    row_lists = [children[r * cols : (r + 1) * cols] for r in range(rows_n)]

    # 相對座標：每排以 x=0 為中線置中，再垂直堆疊 → 整塊後移到 layer 正中
    y_cursor = 0.0
    for row_nodes in row_lists:
        count = len(row_nodes)
        row_w = cell_w + (count - 1) * pitch_x if count else 0.0
        x0 = -row_w / 2.0
        for j, child in enumerate(row_nodes):
            child["x"] = x0 + j * pitch_x
            child["y"] = y_cursor
            child["width"] = _NODE_W
            child["height"] = _NODE_H
        y_cursor += cell_h + gap_y

    def _content_bbox(node: dict[str, Any]) -> tuple[float, float, float, float]:
        lw = _label_width(node)
        cx = float(node["x"]) + cell_w / 2.0
        return (
            cx - lw / 2.0,
            float(node["y"]),
            cx + lw / 2.0,
            float(node["y"]) + cell_h,
        )

    boxes = [_content_bbox(node) for node in children]
    min_x = min(b[0] for b in boxes)
    max_x = max(b[2] for b in boxes)
    min_y = min(b[1] for b in boxes)
    max_y = max(b[3] for b in boxes)
    block_w = max_x - min_x
    block_h = max_y - min_y

    g["width"] = max(float(g.get("width", 0)), block_w + 2 * side_pad)
    g["height"] = max(
        float(g.get("height", 0)), block_h + _GROUP_PAD_TOP + bottom_pad
    )

    target_cx = float(g["x"]) + float(g["width"]) / 2.0
    target_cy = (
        float(g["y"])
        + _GROUP_PAD_TOP
        + (float(g["height"]) - _GROUP_PAD_TOP - bottom_pad) / 2.0
    )
    cur_cx = (min_x + max_x) / 2.0
    cur_cy = (min_y + max_y) / 2.0
    dx = target_cx - cur_cx
    dy = target_cy - cur_cy
    for child in children:
        child["x"] = int(round(float(child["x"]) + dx))
        child["y"] = int(round(float(child["y"]) + dy))


def _assign_group_parents(groups: list[dict[str, Any]]) -> None:
    """
    為每個 group 指定最小包覆父層；寫入 `_layout_parent_gid`（只應在排版初期呼叫一次）。
    優先：子框完全在父內；其次：中心在父內且重疊面積 ≥ 子面積一半。
    """
    ordered = sorted(
        groups, key=lambda x: float(x.get("width", 0)) * float(x.get("height", 0))
    )
    for g in groups:
        parent = None
        g_area = max(1.0, float(g.get("width", 0)) * float(g.get("height", 0)))
        for cand in ordered:
            if cand["id"] == g["id"]:
                continue
            c_area = float(cand.get("width", 0)) * float(cand.get("height", 0))
            if c_area <= g_area:
                continue
            if is_inside(g, cand):
                parent = cand
                break
        if parent is None:
            cx = float(g["x"]) + float(g.get("width", 0)) / 2.0
            cy = float(g["y"]) + float(g.get("height", 0)) / 2.0
            for cand in ordered:
                if cand["id"] == g["id"]:
                    continue
                c_area = float(cand.get("width", 0)) * float(cand.get("height", 0))
                if c_area <= g_area * 1.2:
                    continue
                if not _point_in_group(cand, cx, cy):
                    continue
                # 重疊比例
                gx0, gy0 = float(g["x"]), float(g["y"])
                gx1 = gx0 + float(g.get("width", 0))
                gy1 = gy0 + float(g.get("height", 0))
                cx0, cy0 = float(cand["x"]), float(cand["y"])
                cx1 = cx0 + float(cand.get("width", 0))
                cy1 = cy0 + float(cand.get("height", 0))
                ix0, iy0 = max(gx0, cx0), max(gy0, cy0)
                ix1, iy1 = min(gx1, cx1), min(gy1, cy1)
                if ix1 <= ix0 or iy1 <= iy0:
                    continue
                inter = (ix1 - ix0) * (iy1 - iy0)
                if inter / g_area >= 0.5:
                    parent = cand
                    break
        g["_layout_parent_gid"] = parent["id"] if parent else None


def _build_group_child_map(
    groups: list[dict[str, Any]],
) -> dict[Any, list[dict[str, Any]]]:
    child_map: dict[Any, list[dict[str, Any]]] = {}
    for g in groups:
        pid = g.get("_layout_parent_gid")
        child_map.setdefault(pid, []).append(g)
    return child_map


def _move_group_subtree(
    g: dict[str, Any],
    new_x: float,
    new_y: float,
    *,
    child_map: dict[Any, list[dict[str, Any]]],
    nodes: list[dict[str, Any]],
) -> None:
    """平移 group 及其後代 groups／所屬 nodes（相對幾何不變）。"""
    dx = float(new_x) - float(g["x"])
    dy = float(new_y) - float(g["y"])
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return
    g["x"] = int(round(new_x))
    g["y"] = int(round(new_y))
    moved: set[Any] = {g["id"]}
    stack = list(child_map.get(g["id"], []))
    while stack:
        cg = stack.pop()
        cg["x"] = int(round(float(cg["x"]) + dx))
        cg["y"] = int(round(float(cg["y"]) + dy))
        moved.add(cg["id"])
        stack.extend(child_map.get(cg["id"], []))
    for node in nodes:
        if node.get("_layout_gid") in moved:
            node["x"] = int(round(float(node["x"]) + dx))
            node["y"] = int(round(float(node["y"]) + dy))


def _groups_bbox_overlap(
    a: dict[str, Any], b: dict[str, Any], gap: float = _SIBLING_GAP
) -> bool:
    """兩 group 在 gap 間距下是否仍相交（是＝需要再拉開）。"""
    ax0, ay0 = float(a["x"]), float(a["y"])
    ax1 = ax0 + float(a.get("width", 0))
    ay1 = ay0 + float(a.get("height", 0))
    bx0, by0 = float(b["x"]), float(b["y"])
    bx1 = bx0 + float(b.get("width", 0))
    by1 = by0 + float(b.get("height", 0))
    return not (
        ax1 + gap <= bx0
        or bx1 + gap <= ax0
        or ay1 + gap <= by0
        or by1 + gap <= ay0
    )


def _cluster_sibling_rows(
    siblings: list[dict[str, Any]], y_tol: float = _ROW_Y_TOL
) -> list[list[dict[str, Any]]]:
    """
    分列規則：
    - Y 接近且與列內任一框「幾何不重疊」才可並排
    - 若與列內已有框重疊（常見：上下疊的 subnet），強制換行，避免互遮
    """
    ordered = sorted(siblings, key=lambda g: (float(g["y"]), float(g["x"])))
    rows: list[list[dict[str, Any]]] = []
    for g in ordered:
        placed = False
        for row in rows:
            row_y = sum(float(x["y"]) for x in row) / len(row)
            if abs(float(g["y"]) - row_y) > y_tol:
                continue
            if any(_groups_bbox_overlap(g, other, gap=_SIBLING_GAP) for other in row):
                continue
            row.append(g)
            placed = True
            break
        if not placed:
            rows.append([g])
    for row in rows:
        row.sort(key=lambda g: float(g["x"]))
    return rows


def _layout_sibling_groups(
    siblings: list[dict[str, Any]],
    parent: dict[str, Any] | None,
    *,
    child_map: dict[Any, list[dict[str, Any]]],
    nodes: list[dict[str, Any]],
) -> None:
    """
    同層 sibling：分列後左→右、上→下等距頂對齊；以 gap 強制不重疊。
    不把欄寬強制拉齊到互撞；僅列高對齊。
    """
    if len(siblings) <= 1:
        return
    rows = _cluster_sibling_rows(siblings)
    if parent is not None:
        origin_x = float(parent["x"]) + _GROUP_PAD_X
        origin_y = float(parent["y"]) + _GROUP_PAD_TOP
    else:
        origin_x = min(float(g["x"]) for g in siblings)
        origin_y = min(float(g["y"]) for g in siblings)

    cy = origin_y
    placed_rows: list[list[dict[str, Any]]] = []
    for row in rows:
        max_h = max(float(g.get("height", 0)) for g in row)
        cx = origin_x
        placed_row: list[dict[str, Any]] = []
        for g in row:
            g["height"] = max(float(g.get("height", 0)), max_h)
            _move_group_subtree(g, cx, cy, child_map=child_map, nodes=nodes)
            cx = float(g["x"]) + float(g.get("width", 0)) + _SIBLING_GAP
            placed_row.append(g)
        placed_rows.append(placed_row)
        cy = (
            max(float(g["y"]) + float(g.get("height", 0)) for g in placed_row)
            + _SIBLING_GAP
        )

    flat = [g for row in placed_rows for g in row]
    for _ in range(max(12, len(flat) * 4)):
        moved = False
        ordered = sorted(flat, key=lambda g: (float(g["y"]), float(g["x"])))
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                a, b = ordered[i], ordered[j]
                if not _groups_bbox_overlap(a, b, gap=_SIBLING_GAP):
                    continue
                ax0, ay0 = float(a["x"]), float(a["y"])
                aw, ah = float(a.get("width", 0)), float(a.get("height", 0))
                bx0, by0 = float(b["x"]), float(b["y"])
                bw, bh = float(b.get("width", 0)), float(b.get("height", 0))
                overlap_x = min(ax0 + aw, bx0 + bw) - max(ax0, bx0)
                overlap_y = min(ay0 + ah, by0 + bh) - max(ay0, by0)
                if overlap_x >= overlap_y:
                    _move_group_subtree(
                        b, ax0 + aw + _SIBLING_GAP, by0, child_map=child_map, nodes=nodes
                    )
                else:
                    _move_group_subtree(
                        b, bx0, ay0 + ah + _SIBLING_GAP, child_map=child_map, nodes=nodes
                    )
                moved = True
        if not moved:
            break

    if parent is not None:
        right = max(float(g["x"]) + float(g.get("width", 0)) for g in flat) + _GROUP_PAD_X
        bottom = (
            max(float(g["y"]) + float(g.get("height", 0)) for g in flat)
            + _GROUP_PAD_BOTTOM
        )
        parent["width"] = max(float(parent.get("width", 0)), right - float(parent["x"]))
        parent["height"] = max(
            float(parent.get("height", 0)), bottom - float(parent["y"])
        )


def _align_groups_hierarchy(
    groups: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> None:
    """由深到淺對齊各層 sibling，避免 layer 互疊。不重算父子（沿用已鎖定的連結）。"""
    if len(groups) < 2:
        return
    if any(g.get("_layout_parent_gid", "__missing__") == "__missing__" for g in groups):
        _assign_group_parents(groups)
    child_map = _build_group_child_map(groups)
    group_by_id = {g["id"]: g for g in groups}

    def _depth(g: dict[str, Any]) -> int:
        d = 0
        seen: set[Any] = set()
        cur: Any = g.get("_layout_parent_gid")
        while cur is not None and cur not in seen:
            seen.add(cur)
            d += 1
            parent = group_by_id.get(cur)
            cur = parent.get("_layout_parent_gid") if parent else None
        return d

    # 父層深度由深到淺：先排內層 sibling，再排外層
    parent_ids = sorted(
        child_map.keys(),
        key=lambda pid: (
            -(_depth(group_by_id[pid]) if pid in group_by_id else -1),
            str(pid),
        ),
    )
    for pid in parent_ids:
        siblings = child_map.get(pid) or []
        if len(siblings) < 2:
            continue
        parent = group_by_id.get(pid) if pid is not None else None
        _layout_sibling_groups(
            siblings, parent, child_map=child_map, nodes=nodes
        )


def _grow_ancestors_for_groups(
    groups: list[dict[str, Any]],
    nodes: list[dict[str, Any]] | None = None,
) -> None:
    """依鎖定的 `_layout_parent_gid`，由小到大擴大父框以包住子框。"""
    nodes = nodes or []
    if any(g.get("_layout_parent_gid", "__missing__") == "__missing__" for g in groups):
        _assign_group_parents(groups)
    group_by_id = {g["id"]: g for g in groups}
    ordered = sorted(
        groups, key=lambda g: float(g.get("width", 0)) * float(g.get("height", 0))
    )
    child_map = _build_group_child_map(groups)
    for child in ordered:
        pid = child.get("_layout_parent_gid")
        parent = group_by_id.get(pid) if pid is not None else None
        if parent is None:
            continue
        pad = _GROUP_PAD_X
        right = float(child["x"]) + float(child.get("width", 0)) + pad
        bottom = float(child["y"]) + float(child.get("height", 0)) + pad
        min_x = float(parent["x"]) + pad
        min_y = float(parent["y"]) + _GROUP_PAD_TOP
        dx = dy = 0.0
        if float(child["x"]) < min_x:
            dx = min_x - float(child["x"])
        if float(child["y"]) < min_y:
            dy = min_y - float(child["y"])
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            _move_group_subtree(
                child,
                float(child["x"]) + dx,
                float(child["y"]) + dy,
                child_map=child_map,
                nodes=nodes,
            )
            right = float(child["x"]) + float(child.get("width", 0)) + pad
            bottom = float(child["y"]) + float(child.get("height", 0)) + pad
        parent["width"] = max(float(parent.get("width", 0)), right - float(parent["x"]))
        parent["height"] = max(
            float(parent.get("height", 0)), bottom - float(parent["y"])
        )


def normalize_diagram_layout(
    groups: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]] | None,
) -> None:
    """
    產圖前排版正規化（原地修改）：
    - 節點歸屬最小包覆 layer／group
    - 同層內網格排列並水平／垂直置中；依標籤寬度拉開間距
    - 同層 sibling group 對齊且不重疊
    - 預留標籤高度，避免超出底部
    - 必要時擴大 group，並連帶擴大祖先
    """
    groups = groups or []
    nodes = nodes or []
    if not groups:
        for node in nodes:
            node["width"] = _NODE_W
            node["height"] = _NODE_H
        return
    if not nodes:
        _assign_group_parents(groups)
        _align_groups_hierarchy(groups, nodes)
        _grow_ancestors_for_groups(groups, nodes)
        return

    # 先鎖定親子關係（依 LLM 初始座標），後續對齊不得重算以免兄弟互吞
    _assign_group_parents(groups)
    _assign_nodes_to_groups(groups, nodes)
    by_gid: dict[Any, list[dict[str, Any]]] = {}
    for node in nodes:
        gid = node.get("_layout_gid")
        if gid is None:
            continue
        by_gid.setdefault(gid, []).append(node)

    # 由小 group 開始排，較不易被父框舊尺寸卡住
    for g in sorted(
        groups, key=lambda x: float(x.get("width", 0)) * float(x.get("height", 0))
    ):
        _layout_nodes_inside_group(g, by_gid.get(g["id"], []))

    _grow_ancestors_for_groups(groups, nodes)
    _align_groups_hierarchy(groups, nodes)
    _grow_ancestors_for_groups(groups, nodes)

    # 對齊／平移後再置中一次（標籤間距仍生效）
    by_gid = {}
    for node in nodes:
        gid = node.get("_layout_gid")
        if gid is None:
            continue
        by_gid.setdefault(gid, []).append(node)
    for g in groups:
        _layout_nodes_inside_group(g, by_gid.get(g["id"], []))
    _grow_ancestors_for_groups(groups, nodes)
    # 節點／祖先長高後可能再度互壓，再對齊一次
    _align_groups_hierarchy(groups, nodes)
    _grow_ancestors_for_groups(groups, nodes)

    # 最終夾緊：icon + 標籤必須完整落在所屬 layer（無所屬則跳過）
    group_by_id = {g["id"]: g for g in groups}
    by_gid = {}
    for node in nodes:
        gid = node.get("_layout_gid")
        if gid is None:
            continue
        by_gid.setdefault(gid, []).append(node)

    for gid, children in by_gid.items():
        g = group_by_id.get(gid)
        if not g:
            continue
        side_pad = _side_pad_for_nodes(children)
        bottom_pad = float(_GROUP_PAD_BOTTOM + _CONTENT_INSET)
        for node in children:
            lw = _label_width(node)
            half = lw / 2.0
            # 標籤左右／icon+字上下都在 layer 內
            min_x = float(g["x"]) + side_pad + half - _NODE_W / 2.0
            max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
            min_y = float(g["y"]) + _GROUP_PAD_TOP
            max_y = (
                float(g["y"])
                + float(g["height"])
                - bottom_pad
                - _node_footprint_h()
            )
            if max_x < min_x:
                # 撐寬後置中
                need_w = lw + 2 * side_pad
                g["width"] = max(float(g["width"]), need_w)
                min_x = float(g["x"]) + side_pad + half - _NODE_W / 2.0
                max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
            if max_y < min_y:
                need_h = _GROUP_PAD_TOP + _node_footprint_h() + bottom_pad
                g["height"] = max(float(g["height"]), need_h)
                max_y = (
                    float(g["y"])
                    + float(g["height"])
                    - bottom_pad
                    - _node_footprint_h()
                )
            node["x"] = int(round(min(max(float(node["x"]), min_x), max(min_x, max_x))))
            node["y"] = int(round(min(max(float(node["y"]), min_y), max(min_y, max_y))))

    _grow_ancestors_for_groups(groups, nodes)
    _align_groups_hierarchy(groups, nodes)


def _node_aabb(node: dict[str, Any], margin: float = _EDGE_CLEARANCE) -> tuple[float, float, float, float]:
    """
    節點障礙盒 = icon 外接框（不含標籤擴寬）。
    標籤區請用 `_node_obstacle_boxes`，避免把下方標籤寬度灌進整段高度。
    """
    w = float(node.get("width", 80))
    h = float(node.get("height", 80))
    x = float(node["x"])
    y = float(node["y"])
    return (x - margin, y - margin, x + w + margin, y + h + margin)


def _node_obstacle_boxes(
    node: dict[str, Any], margin: float = _EDGE_CLEARANCE
) -> list[tuple[float, float, float, float]]:
    """icon 盒 +（若有名稱）下方標籤盒，供邊線避障。"""
    boxes = [_node_aabb(node, margin=margin)]
    w = float(node.get("width", 80))
    h = float(node.get("height", 80))
    x = float(node["x"])
    y = float(node["y"])
    label = str(node.get("name") or node.get("label") or "").strip()
    if not label:
        return boxes
    label_w = max(w, min(_LABEL_MAX_W, len(label) * _LABEL_CHAR_W))
    lx0 = x + w / 2.0 - label_w / 2.0
    lx1 = lx0 + label_w
    ly0 = y + h + _LABEL_GAP
    ly1 = ly0 + _LABEL_HEIGHT
    boxes.append((lx0 - margin, ly0 - margin, lx1 + margin, ly1 + margin))
    return boxes


def _anchor_point(node: dict[str, Any], ax: float, ay: float) -> tuple[float, float]:
    w = float(node.get("width", 80))
    h = float(node.get("height", 80))
    return (float(node["x"]) + ax * w, float(node["y"]) + ay * h)


def _outward_stub(
    ax: float, ay: float, point: tuple[float, float], stub: float = _PORT_STUB
) -> tuple[float, float]:
    """從邊中點沿法線向外一小段，保證直角進出。"""
    x, y = point
    if ax >= 1.0 - 1e-9:  # 右邊
        return (x + stub, y)
    if ax <= 1e-9:  # 左邊
        return (x - stub, y)
    if ay >= 1.0 - 1e-9:  # 下邊
        return (x, y + stub)
    return (x, y - stub)  # 上邊


def _fmt_port(v: float) -> str:
    if abs(v - 0.5) < 1e-9:
        return "0.5"
    if abs(v) < 1e-9:
        return "0"
    if abs(v - 1.0) < 1e-9:
        return "1"
    return str(round(v, 3))


def _seg_hits_aabb(
    x0: float, y0: float, x1: float, y1: float, box: tuple[float, float, float, float]
) -> bool:
    """軸對齊線段是否與 AABB 相交（含貼邊視為碰撞，逼路徑外移）。"""
    bx0, by0, bx1, by1 = box
    # 水平線
    if abs(y0 - y1) < 1e-6:
        y = y0
        if y < by0 or y > by1:
            return False
        lo, hi = sorted((x0, x1))
        return not (hi < bx0 or lo > bx1)
    # 垂直線
    if abs(x0 - x1) < 1e-6:
        x = x0
        if x < bx0 or x > bx1:
            return False
        lo, hi = sorted((y0, y1))
        return not (hi < by0 or lo > by1)
    return False


def _path_clear(
    points: list[tuple[float, float]],
    obstacles: list[tuple[float, float, float, float]],
    *,
    skip_end_stubs: bool = True,
) -> bool:
    """
    檢查折線是否穿過障礙。
    skip_end_stubs：略過首尾垂直 stub（貼近端點，可能進入鄰近 icon 的 clearance）。
    """
    nseg = len(points) - 1
    for i in range(nseg):
        if skip_end_stubs and nseg >= 2 and (i == 0 or i == nseg - 1):
            continue
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        for box in obstacles:
            if _seg_hits_aabb(x0, y0, x1, y1, box):
                return False
    return True


def _path_collision_count(
    points: list[tuple[float, float]],
    obstacles: list[tuple[float, float, float, float]],
    *,
    skip_end_stubs: bool = True,
) -> int:
    hits = 0
    nseg = len(points) - 1
    for i in range(nseg):
        if skip_end_stubs and nseg >= 2 and (i == 0 or i == nseg - 1):
            continue
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        for box in obstacles:
            if _seg_hits_aabb(x0, y0, x1, y1, box):
                hits += 1
    return hits


def _point_strictly_inside_obstacle(
    point: tuple[float, float],
    obstacles: list[tuple[float, float, float, float]],
    *,
    eps: float = 0.75,
) -> bool:
    x, y = point
    for bx0, by0, bx1, by1 in obstacles:
        if bx0 + eps < x < bx1 - eps and by0 + eps < y < by1 - eps:
            return True
    return False


def _clean_polyline(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """僅去除連續重點；保留共線 stub，避免進出邊被折掉。"""
    cleaned: list[tuple[float, float]] = []
    for p in points:
        if not cleaned or (
            abs(cleaned[-1][0] - p[0]) > 1e-6 or abs(cleaned[-1][1] - p[1]) > 1e-6
        ):
            cleaned.append(p)
    return cleaned


def _nudge_point_clear(
    ax: float,
    ay: float,
    point: tuple[float, float],
    obstacles: list[tuple[float, float, float, float]],
) -> tuple[float, float]:
    """
    若 stub 落在障礙（含 clearance）內：投影到障礙外側最近點，
    優先側向／回退，禁止沿 port 長距貫穿障礙中央。
    """
    p = point
    if not _point_strictly_inside_obstacle(p, obstacles):
        return p
    candidates: list[tuple[float, float]] = []
    for bx0, by0, bx1, by1 in obstacles:
        if not (bx0 < p[0] < bx1 and by0 < p[1] < by1):
            continue
        candidates.extend(
            [
                (bx0 - 1.0, p[1]),
                (bx1 + 1.0, p[1]),
                (p[0], by0 - 1.0),
                (p[0], by1 + 1.0),
            ]
        )
    candidates.append(_outward_stub(ax, ay, p, stub=6.0))
    best = p
    best_d = 1e18
    for c in candidates:
        if _point_strictly_inside_obstacle(c, obstacles):
            continue
        d = abs(c[0] - p[0]) + abs(c[1] - p[1])
        if d < best_d:
            best_d = d
            best = c
    return best


def _route_orthogonal_astar(
    start: tuple[float, float],
    goal: tuple[float, float],
    obstacles: list[tuple[float, float, float, float]],
    *,
    pad: float,
) -> list[tuple[float, float]] | None:
    """
    正交可見性網格 A*：在障礙外框通道上尋路。
    回傳含 start／goal 的折線；找不到則 None。
    """
    from heapq import heappop, heappush

    if _path_clear([start, goal], obstacles, skip_end_stubs=False) and (
        abs(start[0] - goal[0]) < 1e-6 or abs(start[1] - goal[1]) < 1e-6
    ):
        return [start, goal]

    xs: set[float] = {start[0], goal[0]}
    ys: set[float] = {start[1], goal[1]}
    for bx0, by0, bx1, by1 in obstacles:
        xs.update((bx0 - pad, bx1 + pad, start[0], goal[0]))
        ys.update((by0 - pad, by1 + pad, start[1], goal[1]))
    if obstacles:
        all_x0 = min(b[0] for b in obstacles)
        all_y0 = min(b[1] for b in obstacles)
        all_x1 = max(b[2] for b in obstacles)
        all_y1 = max(b[3] for b in obstacles)
        xs.update((all_x0 - pad * 2, all_x1 + pad * 2, start[0], goal[0]))
        ys.update((all_y0 - pad * 2, all_y1 + pad * 2, start[1], goal[1]))
    xs_l = sorted(xs)
    ys_l = sorted(ys)
    x_index = {v: i for i, v in enumerate(xs_l)}
    y_index = {v: i for i, v in enumerate(ys_l)}

    def key(p: tuple[float, float]) -> tuple[float, float]:
        return (round(p[0], 3), round(p[1], 3))

    free: set[tuple[float, float]] = set()
    for x in xs_l:
        for y in ys_l:
            pt = (x, y)
            if not _point_strictly_inside_obstacle(pt, obstacles):
                free.add(key(pt))

    start_k = key(start)
    goal_k = key(goal)
    free.add(start_k)
    free.add(goal_k)

    def neighbors(p: tuple[float, float]) -> list[tuple[float, float]]:
        x, y = p
        out: list[tuple[float, float]] = []
        xi = x_index.get(x)
        yi = y_index.get(y)
        if xi is None or yi is None:
            xi = min(range(len(xs_l)), key=lambda i: abs(xs_l[i] - x))
            yi = min(range(len(ys_l)), key=lambda i: abs(ys_l[i] - y))
            x, y = xs_l[xi], ys_l[yi]
        for nxi in (xi - 1, xi + 1):
            if 0 <= nxi < len(xs_l):
                q = (xs_l[nxi], y)
                if key(q) in free and _path_clear([p, q], obstacles, skip_end_stubs=False):
                    out.append(q)
        for nyi in (yi - 1, yi + 1):
            if 0 <= nyi < len(ys_l):
                q = (x, ys_l[nyi])
                if key(q) in free and _path_clear([p, q], obstacles, skip_end_stubs=False):
                    out.append(q)
        return out

    def heur(p: tuple[float, float]) -> float:
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

    open_h: list[tuple[float, float, tuple[float, float]]] = []
    heappush(open_h, (heur(start), 0.0, start))
    came: dict[tuple[float, float], tuple[float, float]] = {}
    gscore: dict[tuple[float, float], float] = {start_k: 0.0}
    closed: set[tuple[float, float]] = set()

    while open_h:
        _f, g, current = heappop(open_h)
        ck = key(current)
        if ck in closed:
            continue
        if abs(current[0] - goal[0]) < 1e-3 and abs(current[1] - goal[1]) < 1e-3:
            path = [current]
            while ck in came:
                prev = came[ck]
                path.append(prev)
                ck = key(prev)
            path.reverse()
            if key(path[0]) != start_k:
                path.insert(0, start)
            if key(path[-1]) != goal_k:
                path.append(goal)
            return path
        closed.add(ck)
        for nxt in neighbors(current):
            nk = key(nxt)
            ng = g + abs(nxt[0] - current[0]) + abs(nxt[1] - current[1])
            if ng + 1e-6 < gscore.get(nk, 1e100):
                gscore[nk] = ng
                came[nk] = current
                heappush(open_h, (ng + heur(nxt), ng, nxt))
    return None


def _path_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        total += abs(points[i][0] - points[i + 1][0]) + abs(
            points[i][1] - points[i + 1][1]
        )
    return total


def _merged_node_bbox(
    node: dict[str, Any], margin: float = 0.0
) -> tuple[float, float, float, float]:
    """icon + 標籤合併外接盒。"""
    boxes = _node_obstacle_boxes(node, margin=margin)
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _bboxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    gap: float = 0.0,
) -> bool:
    return not (
        a[2] + gap <= b[0]
        or b[2] + gap <= a[0]
        or a[3] + gap <= b[1]
        or b[3] + gap <= a[1]
    )


def _clamp_node_into_group(
    node: dict[str, Any], g: dict[str, Any], siblings: list[dict[str, Any]]
) -> None:
    """把節點（含標籤）夾回 group，必要時撐大 group。"""
    side_pad = _side_pad_for_nodes(siblings)
    bottom_pad = float(_GROUP_PAD_BOTTOM + _CONTENT_INSET)
    lw = _label_width(node)
    half = lw / 2.0
    min_x = float(g["x"]) + side_pad + half - _NODE_W / 2.0
    max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
    min_y = float(g["y"]) + _GROUP_PAD_TOP
    max_y = (
        float(g["y"]) + float(g["height"]) - bottom_pad - _node_footprint_h()
    )
    if max_x < min_x:
        g["width"] = max(float(g["width"]), lw + 2 * side_pad)
        min_x = float(g["x"]) + side_pad + half - _NODE_W / 2.0
        max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
    if max_y < min_y:
        g["height"] = max(
            float(g["height"]), _GROUP_PAD_TOP + _node_footprint_h() + bottom_pad
        )
        max_y = (
            float(g["y"]) + float(g["height"]) - bottom_pad - _node_footprint_h()
        )
    # 若仍裝不下，向右／下撐
    if float(node["x"]) > max_x:
        g["width"] = max(
            float(g["width"]),
            float(node["x"]) + _NODE_W / 2.0 + half + side_pad - float(g["x"]),
        )
        max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
    if float(node["y"]) > max_y:
        g["height"] = max(
            float(g["height"]),
            float(node["y"]) + _node_footprint_h() + bottom_pad - float(g["y"]),
        )
        max_y = (
            float(g["y"]) + float(g["height"]) - bottom_pad - _node_footprint_h()
        )
    node["x"] = int(round(min(max(float(node["x"]), min_x), max(min_x, max_x))))
    node["y"] = int(round(min(max(float(node["y"]), min_y), max(min_y, max_y))))


def _ensure_icons_non_overlapping(
    groups: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    *,
    gap: float = 16.0,
) -> None:
    """同 layer 內 icon＋標籤互不重疊；必要時推開並撐大 layer。"""
    if len(nodes) < 2:
        return
    group_by_id = {g["id"]: g for g in groups}
    by_gid: dict[Any, list[dict[str, Any]]] = {}
    for n in nodes:
        by_gid.setdefault(n.get("_layout_gid"), []).append(n)

    for gid, children in by_gid.items():
        if gid is None or len(children) < 2:
            continue
        g = group_by_id.get(gid)
        if not g:
            continue
        for _ in range(max(8, len(children) * 5)):
            moved = False
            ordered = sorted(
                children, key=lambda n: (float(n["y"]), float(n["x"]), str(n.get("id")))
            )
            for i in range(len(ordered)):
                for j in range(i + 1, len(ordered)):
                    a, b = ordered[i], ordered[j]
                    aa = _merged_node_bbox(a)
                    bb = _merged_node_bbox(b)
                    if not _bboxes_overlap(aa, bb, gap=gap):
                        continue
                    overlap_x = min(aa[2], bb[2]) - max(aa[0], bb[0])
                    overlap_y = min(aa[3], bb[3]) - max(aa[1], bb[1])
                    if overlap_x >= overlap_y:
                        delta = aa[2] + gap - bb[0]
                        if delta > 0:
                            b["x"] = int(round(float(b["x"]) + delta))
                            moved = True
                    else:
                        delta = aa[3] + gap - bb[1]
                        if delta > 0:
                            b["y"] = int(round(float(b["y"]) + delta))
                            moved = True
            for child in children:
                _clamp_node_into_group(child, g, children)
            if not moved:
                break


def _edge_path_points(
    src: dict[str, Any],
    tgt: dict[str, Any],
    all_nodes: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    ports, waypoints = compute_edge_waypoints(src, tgt, all_nodes)
    exit_x, exit_y, entry_x, entry_y = ports
    start = _anchor_point(src, exit_x, exit_y)
    end = _anchor_point(tgt, entry_x, entry_y)
    return [start, *waypoints, end]


def _count_foreign_edge_hits(
    node: dict[str, Any],
    all_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    node_by_id: dict[Any, dict[str, Any]],
) -> int:
    """統計「非以此節點為端點」的邊有多少線段穿過本節點 icon／標籤。"""
    nid = node.get("id")
    if nid is None:
        return 0
    boxes = _node_obstacle_boxes(node)
    hits = 0
    for edge in edges:
        src_id, tgt_id = edge.get("source"), edge.get("target")
        if nid in (src_id, tgt_id):
            continue
        src = node_by_id.get(src_id)
        tgt = node_by_id.get(tgt_id)
        if src is None or tgt is None:
            continue
        path = _edge_path_points(src, tgt, all_nodes)
        for i in range(len(path) - 1):
            x0, y0 = path[i]
            x1, y1 = path[i + 1]
            for box in boxes:
                if _seg_hits_aabb(x0, y0, x1, y1, box):
                    hits += 1
                    break
    return hits


def _iter_group_candidate_positions(
    g: dict[str, Any],
    siblings: list[dict[str, Any]],
    node: dict[str, Any],
    *,
    step: float = 36.0,
) -> list[tuple[int, int]]:
    """同 layer 內容區內的候選座標（含原點）。"""
    side_pad = _side_pad_for_nodes(siblings)
    bottom_pad = float(_GROUP_PAD_BOTTOM + _CONTENT_INSET)
    lw = _label_width(node)
    half = lw / 2.0
    min_x = float(g["x"]) + side_pad + half - _NODE_W / 2.0
    max_x = float(g["x"]) + float(g["width"]) - side_pad - half - _NODE_W / 2.0
    min_y = float(g["y"]) + _GROUP_PAD_TOP
    max_y = (
        float(g["y"]) + float(g["height"]) - bottom_pad - _node_footprint_h()
    )
    if max_x < min_x or max_y < min_y:
        return [(int(node["x"]), int(node["y"]))]
    coords: list[tuple[int, int]] = [(int(node["x"]), int(node["y"]))]
    x = min_x
    while x <= max_x + 1e-6:
        y = min_y
        while y <= max_y + 1e-6:
            coords.append((int(round(x)), int(round(y))))
            y += step
        x += step
    # 去重、限制數量
    seen: set[tuple[int, int]] = set()
    uniq: list[tuple[int, int]] = []
    for c in coords:
        if c in seen:
            continue
        seen.add(c)
        uniq.append(c)
    return uniq[:80]


def _position_conflicts(
    node: dict[str, Any],
    siblings: list[dict[str, Any]],
    *,
    gap: float = 16.0,
) -> bool:
    mine = _merged_node_bbox(node)
    for other in siblings:
        if other is node or other.get("id") == node.get("id"):
            continue
        if _bboxes_overlap(mine, _merged_node_bbox(other), gap=gap):
            return True
    return False


def relieve_icon_edge_congestion(
    groups: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]] | None,
    edges: list[dict[str, Any]] | None,
    *,
    hit_threshold: int = 1,
    rounds: int = 2,
) -> None:
    """
    若有邊線穿過非端點 icon，於「同一 layer」內平移到過線較少的空位。
    並在前／後確保同層 icon 不互疊。
    """
    groups = groups or []
    nodes = nodes or []
    edges = edges or []
    if not nodes or not edges:
        _ensure_icons_non_overlapping(groups, nodes)
        return

    _ensure_icons_non_overlapping(groups, nodes)
    group_by_id = {g["id"]: g for g in groups}
    node_by_id = {n.get("id"): n for n in nodes if n.get("id") is not None}

    for _ in range(rounds):
        scored: list[tuple[int, dict[str, Any]]] = []
        for node in nodes:
            if node.get("_layout_gid") is None:
                continue
            hits = _count_foreign_edge_hits(node, nodes, edges, node_by_id)
            if hits >= hit_threshold:
                scored.append((hits, node))
        if not scored:
            break
        scored.sort(key=lambda t: (-t[0], str(t[1].get("id"))))
        moved_any = False
        for hits, node in scored[:8]:
            gid = node.get("_layout_gid")
            g = group_by_id.get(gid) if gid is not None else None
            if not g:
                continue
            siblings = [
                n for n in nodes if n.get("_layout_gid") == gid
            ]
            orig = (int(node["x"]), int(node["y"]))
            best = orig
            best_hits = hits
            for cx, cy in _iter_group_candidate_positions(g, siblings, node):
                node["x"], node["y"] = cx, cy
                if _position_conflicts(node, siblings):
                    continue
                h = _count_foreign_edge_hits(node, nodes, edges, node_by_id)
                if h < best_hits or (
                    h == best_hits
                    and abs(cx - orig[0]) + abs(cy - orig[1])
                    < abs(best[0] - orig[0]) + abs(best[1] - orig[1])
                ):
                    best_hits = h
                    best = (cx, cy)
                    if h == 0:
                        break
            node["x"], node["y"] = best[0], best[1]
            _clamp_node_into_group(node, g, siblings)
            if (int(node["x"]), int(node["y"])) != orig and best_hits < hits:
                moved_any = True
        _ensure_icons_non_overlapping(groups, nodes)
        if not moved_any:
            break
    _grow_ancestors_for_groups(groups, nodes)


def compute_edge_waypoints(
    src: dict[str, Any],
    tgt: dict[str, Any],
    all_nodes: list[dict[str, Any]],
) -> tuple[tuple[float, float, float, float], list[tuple[float, float]]]:
    """
    為正交邊計算 mid-side ports 與繞過其他 icon／標籤的中繼點。
    優先保證零碰撞（可多拐彎）；嘗試多組進出邊與 A* 通道繞行。
    """
    ignore = {src.get("id"), tgt.get("id")}
    obstacles: list[tuple[float, float, float, float]] = []
    for n in all_nodes:
        if n.get("id") in ignore or "x" not in n or "y" not in n:
            continue
        obstacles.extend(_node_obstacle_boxes(n))

    pad = _EDGE_CLEARANCE
    preferred = edge_anchor_ports(src, tgt)
    side_ports = ((1.0, 0.5), (0.0, 0.5), (0.5, 1.0), (0.5, 0.0))
    port_list: list[tuple[float, float, float, float]] = [preferred]
    for ex, ey in side_ports:
        for enx, eny in side_ports:
            cand = (ex, ey, enx, eny)
            if cand not in port_list:
                port_list.append(cand)

    best_clear: tuple[
        tuple[int, int, int, float],
        tuple[float, float, float, float],
        list[tuple[float, float]],
    ] | None = None
    best_any: tuple[
        tuple[int, int, int, float],
        tuple[float, float, float, float],
        list[tuple[float, float]],
    ] | None = None

    for ports in port_list:
        exit_x, exit_y, entry_x, entry_y = ports
        start = _anchor_point(src, exit_x, exit_y)
        end = _anchor_point(tgt, entry_x, entry_y)
        out_s = _nudge_point_clear(
            exit_x, exit_y, _outward_stub(exit_x, exit_y, start), obstacles
        )
        in_s = _nudge_point_clear(
            entry_x, entry_y, _outward_stub(entry_x, entry_y, end), obstacles
        )

        mid_paths: list[list[tuple[float, float]]] = [
            [out_s, in_s],
            [out_s, (in_s[0], out_s[1]), in_s],
            [out_s, (out_s[0], in_s[1]), in_s],
        ]
        routed = _route_orthogonal_astar(out_s, in_s, obstacles, pad=pad)
        if routed:
            mid_paths.append(routed)

        if obstacles:
            xs = [b[0] for b in obstacles] + [b[2] for b in obstacles] + [
                out_s[0],
                in_s[0],
            ]
            ys = [b[1] for b in obstacles] + [b[3] for b in obstacles] + [
                out_s[1],
                in_s[1],
            ]
            top_y = min(ys) - pad
            bot_y = max(ys) + pad
            left_x = min(xs) - pad
            right_x = max(xs) + pad
            ox, oy = out_s
            ix, iy = in_s
            mid_paths.extend(
                [
                    [out_s, (ox, top_y), (ix, top_y), in_s],
                    [out_s, (ox, bot_y), (ix, bot_y), in_s],
                    [out_s, (left_x, oy), (left_x, iy), in_s],
                    [out_s, (right_x, oy), (right_x, iy), in_s],
                    [out_s, (ox, top_y), (right_x, top_y), (right_x, iy), in_s],
                    [out_s, (ox, bot_y), (left_x, bot_y), (left_x, iy), in_s],
                    [out_s, (ox, top_y), (left_x, top_y), (left_x, iy), in_s],
                    [out_s, (ox, bot_y), (right_x, bot_y), (right_x, iy), in_s],
                ]
            )
            for bx0, by0, bx1, by1 in obstacles:
                mid_paths.extend(
                    [
                        [out_s, (ox, by0 - pad), (ix, by0 - pad), in_s],
                        [out_s, (ox, by1 + pad), (ix, by1 + pad), in_s],
                        [out_s, (bx0 - pad, oy), (bx0 - pad, iy), in_s],
                        [out_s, (bx1 + pad, oy), (bx1 + pad, iy), in_s],
                        [
                            out_s,
                            (ox, by0 - pad),
                            (bx1 + pad, by0 - pad),
                            (bx1 + pad, iy),
                            in_s,
                        ],
                        [
                            out_s,
                            (ox, by1 + pad),
                            (bx0 - pad, by1 + pad),
                            (bx0 - pad, iy),
                            in_s,
                        ],
                        [
                            out_s,
                            (bx0 - pad, oy),
                            (bx0 - pad, by0 - pad),
                            (ix, by0 - pad),
                            in_s,
                        ],
                        [
                            out_s,
                            (bx1 + pad, oy),
                            (bx1 + pad, by1 + pad),
                            (ix, by1 + pad),
                            in_s,
                        ],
                    ]
                )

        for mids in mid_paths:
            full = _clean_polyline([start, *mids, end])
            if len(full) < 2:
                continue
            hits = _path_collision_count(full, obstacles, skip_end_stubs=True)
            bends = max(0, len(full) - 2)
            plen = _path_length(full)
            waypoints = full[1:-1]
            # 零碰撞優先；寧可多拐彎；preferred ports 略優先
            prefer_penalty = 0 if ports == preferred else 1
            score = (hits, prefer_penalty, bends, plen)
            if hits == 0 and (best_clear is None or score < best_clear[0]):
                best_clear = (score, ports, waypoints)
            if best_any is None or score < best_any[0]:
                best_any = (score, ports, waypoints)

    if best_clear is not None:
        return best_clear[1], best_clear[2]
    if best_any is not None:
        return best_any[1], best_any[2]
    # 最後保底
    ports = preferred
    exit_x, exit_y, entry_x, entry_y = ports
    start = _anchor_point(src, exit_x, exit_y)
    end = _anchor_point(tgt, entry_x, entry_y)
    out_s = _outward_stub(exit_x, exit_y, start)
    in_s = _outward_stub(entry_x, entry_y, end)
    full = _clean_polyline([start, out_s, in_s, end])
    return ports, full[1:-1]


def _waypoints_xml(waypoints: list[tuple[float, float]]) -> str:
    if not waypoints:
        return '<mxGeometry relative="1" as="geometry"/>'
    pts = "".join(
        f'<mxPoint x="{round(x, 1)}" y="{round(y, 1)}"/>' for x, y in waypoints
    )
    return (
        '<mxGeometry relative="1" as="geometry">'
        f'<Array as="points">{pts}</Array>'
        "</mxGeometry>"
    )


# n8n 的圖示目錄用服務全名（`Simple Notification Service`），架構圖用縮寫
# （`SNS`）。兩者沒有共同子字串，純比對必然落空——這裡把縮寫展開成目錄裡
# 實際存在的名稱。每一條都對照 webhook 回傳的目錄驗證過；查無對應的縮寫
# （如 EFS）不放進來，寧可落到灰底也不要指向錯的圖示。
_SERVICE_ABBREVIATIONS = {
    "asg": "auto scaling",
    "cdn": "cloudfront",
    "ecr": "elastic container registry",
    "ecs": "elastic container service",
    "eks": "elastic kubernetes service",
    "elb": "elastic load balancing",
    "iam": "identity and access management",
    "kms": "key management service",
    "msk": "managed streaming for apache kafka",
    "s3": "simple storage service",
    "ses": "simple email service",
    "sns": "simple notification service",
    "sqs": "simple queue service",
    "vpc": "virtual private cloud",
}


def _normalise_icon_name(text: str) -> str:
    """比對用的正規化形式。

    目錄裡同一個服務有三種寫法：`AWS Lambda`、`CloudWatch`、
    `Auto-Scaling-group.svg`。統一成小寫、無副檔名、無 AWS/Amazon 前綴、
    以單一空白分隔的詞序列，好讓「完全相同」成為可判定的條件。
    """
    text = re.sub(r"\.svg$", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower().strip()
    text = re.sub(r"^(aws|amazon)\s+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _icon_match_score(service_name: str, icon_name: str) -> int:
    """這個目錄項有多像目標服務。0 代表不算匹配。

    分數的用途是**排序候選**，不是門檻。關鍵在於精確匹配必須贏過子字串
    包含：`S3` 對 `S3 on Outposts` 是子字串命中，對 `Simple Storage
    Service` 才是（展開後的）完全相同，而後者才是要的那一個。
    """
    service = _normalise_icon_name(service_name)
    icon = _normalise_icon_name(icon_name)
    if not service or not icon:
        return 0

    if service == icon:
        return 100

    expanded = _SERVICE_ABBREVIATIONS.get(service)
    if expanded and expanded == icon:
        return 90
    if expanded and expanded in icon:
        return 60

    # 詞邊界包含優於單純的字元包含：`ecs` 不該命中 `secsomething`。
    if f" {service} " in f" {icon} ":
        return 50
    # 只認「服務名是目錄名的一部分」這個方向。反向（目錄名是服務名的一部分）
    # 實測會讓 `BigQuery` 命中目錄裡叫 `Q` 的圖示、`Cloud Spanner` 命中
    # `AWS-Cloud`——目錄只收 AWS，非 AWS 服務本來就該落到灰底。長度下限擋掉
    # 短字串的偶然包含；縮寫由上面的對應表處理，不倚賴這條。
    if len(service) >= 4 and service in icon:
        return 10
    return 0


def _select_icon_entry(entries: list[dict[str, Any]], service_name: str) -> dict[str, Any] | None:
    """挑出最像 `service_name` 的目錄項；沒有像的回 None。

    回 None 而不是退回 `entries[0]`：退回第一項會讓「查無此圖示」看起來
    像成功，實際交出的是目錄裡碰巧排第一的那個服務（實測是
    `Auto-Scaling-group`）。錯的圖示比灰底佔位圖更難發現。
    """
    best: tuple[int, int, dict[str, Any]] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("icon_name") or entry.get("service") or ""
        score = _icon_match_score(service_name, name)
        if score == 0:
            continue
        # 同分時取較短的名稱：`CloudWatch` 勝過 `CloudWatch Logs`。
        candidate = (score, -len(name), entry)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else None


def _svg_from_entry(entry: dict[str, Any]) -> str | None:
    """目錄項裡的 SVG 內容，欄位名兩種都接受。"""
    for key in ("svg_content", "svg"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


async def fetch_icon_from_n8n(service_name: str, provider: str = "AWS") -> str:
    """
    向 n8n webhook 取得服務 SVG。
    若未設定 N8N_WEBHOOK_URL 或請求失敗，回傳灰底文字 fallback SVG。
    """
    webhook_url = os.environ.get("N8N_WEBHOOK_URL")
    n8n_user = os.environ.get("N8N_USER")
    n8n_password = os.environ.get("N8N_PASSWORD")
    fallback_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" fill="#cccccc"/>'
        f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
        f'fill="black" font-size="14">{service_name}</text></svg>'
    )

    if not webhook_url:
        return fallback_svg

    auth = None
    if n8n_user and n8n_password:
        auth = (n8n_user, n8n_password)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"service": service_name, "provider": provider},
                auth=auth,
                timeout=5.0
            )
            if response.status_code != 200:
                # 這條路徑原本靜默 return，是最難查的一種降級：服務照常回圖，
                # 只是每個 icon 都變灰底，沒有任何地方說得出為什麼。
                logger.warning(
                    "n8n 取得 %s 圖示（供應商：%s）回應 HTTP %s，改用灰底佔位圖",
                    service_name,
                    provider,
                    response.status_code,
                )
                return fallback_svg

            content = response.text.strip()
            if content.startswith("<svg"):
                return content

            try:
                data = response.json()

                if isinstance(data, list):
                    entry = _select_icon_entry(data, service_name)
                    if entry is None:
                        logger.warning(
                            "n8n 目錄（%d 項）查無 %s（供應商：%s）的圖示，改用灰底佔位圖",
                            len(data),
                            service_name,
                            provider,
                        )
                        return fallback_svg
                    svg = _svg_from_entry(entry)
                    if svg:
                        return svg
                    logger.warning(
                        "n8n 目錄項 %r 匹配到 %s，但不含 SVG 內容，改用灰底佔位圖",
                        entry.get("icon_name") or entry.get("name"),
                        service_name,
                    )
                    return fallback_svg

                elif isinstance(data, dict):
                    svg = _svg_from_entry(data)
                    if svg:
                        return svg
                    nested = data.get("data")
                    if isinstance(nested, dict):
                        svg = _svg_from_entry(nested)
                        if svg:
                            return svg

            except Exception as e:
                logger.warning("解析 n8n 回應失敗: %s", e)
    except Exception as e:
        logger.warning("向 n8n 取得 %s 圖示（供應商：%s）失敗: %s", service_name, provider, e)

    return fallback_svg


async def build_mxgraph_xml(
    groups: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]] | None,
    edges: list[dict[str, Any]] | None,
    on_progress: ProgressCallback | None = None,
    provider: str | None = None,
) -> str:
    """
    將 groups/nodes/edges 組裝為 mxGraphModel XML 字串。

    流程：
      1. normalize_diagram_layout：節點夾在所屬 layer 內並置中
      2. relieve_icon_edge_congestion：同層不互疊，並挪走被邊線壓到的 icon
      3. 依面積排序 groups，用 is_inside 推算 parent 與相對座標
      4. 為 nodes 找最小包覆 group
      5. 輸出 group / node（含 n8n icon）/ orthogonal edge cells
    """
    groups = list(groups or [])
    nodes = list(nodes or [])
    edges = list(edges or [])
    normalize_diagram_layout(groups, nodes)
    # 同層 icon 不互疊；被多餘邊線壓到的 icon 在同 layer 內挪到較少過線處
    relieve_icon_edge_congestion(groups, nodes, edges)

    if not provider:
        # 根據群組的類型自動偵測雲端平台供應商
        g_types = {g.get("type") for g in groups if g}
        if any(t in ("azure_cloud", "azure_vnet", "azure_resource_group", "azure_subnet") for t in g_types):
            provider = "Azure"
        elif any(t in ("gcp_cloud", "gcp_vpc", "gcp_subnet") for t in g_types):
            provider = "GCP"
        else:
            provider = "AWS"

    if not nodes and not groups:
        raise ValueError("groups 與 nodes 皆為空，無法產圖")

    cells: list[str] = []

    # --- 巢狀：group 面積由大到小 ---
    for g in groups:
        g["area"] = g.get("width", 0) * g.get("height", 0)
    groups_sorted = sorted(groups, key=lambda x: x["area"], reverse=True)

    for g in groups_sorted:
        parent_id = "1"
        rel_x, rel_y = g["x"], g["y"]
        for potential_parent in groups_sorted:
            if g["id"] != potential_parent["id"] and potential_parent["area"] > g["area"]:
                if is_inside(g, potential_parent):
                    parent_id = potential_parent["id"]
                    rel_x = g["x"] - potential_parent["x"]
                    rel_y = g["y"] - potential_parent["y"]
        g["parent_id"] = parent_id
        g["rel_x"] = rel_x
        g["rel_y"] = rel_y

    for node in nodes:
        parent_id = "1"
        rel_x, rel_y = node["x"], node["y"]
        node["width"] = 80
        node["height"] = 80

        best_group = None
        for g in groups_sorted:
            if is_inside(node, g):
                best_group = g
        if best_group:
            parent_id = best_group["id"]
            rel_x = node["x"] - best_group["x"]
            rel_y = node["y"] - best_group["y"]

        node["parent_id"] = parent_id
        node["rel_x"] = rel_x
        node["rel_y"] = rel_y

    # --- Groups ---
    for g in groups_sorted:
        gid = g["id"]
        gname = g.get("name", "")
        gtype = g.get("type", "vpc")
        style = GROUP_STYLES.get(gtype, GROUP_STYLES["vpc"])
        w, h = g.get("width", 200), g.get("height", 200)
        pid = g["parent_id"]
        rx, ry = g["rel_x"], g["rel_y"]
        cells.append(
            f'<mxCell id="{gid}" value="{gname}" style="{style}" vertex="1" parent="{pid}">'
            f'<mxGeometry x="{rx}" y="{ry}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )

    # --- Nodes + n8n icons ---
    for idx, node in enumerate(nodes):
        node_id = node.get("id", f"node_{idx}")
        comp = node.get("name", "Unknown")
        pid = node["parent_id"]
        rx, ry = node["rel_x"], node["rel_y"]

        if on_progress:
            await on_progress(
                f"🔄 正在取得 {comp.upper()} 圖示 ({idx + 1}/{len(nodes)})..."
            )

        svg_content = await fetch_icon_from_n8n(comp, provider=provider)
        b64_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
        style = (
            f"shape=image;image=data:image/svg+xml,{b64_svg};"
            "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
            "spacingTop=4;perimeter=rectanglePerimeter;movable=1;"
        )
        cells.append(
            f'<mxCell id="{node_id}" value="{comp.upper()}" style="{style}" vertex="1" parent="{pid}">'
            f'<mxGeometry x="{rx}" y="{ry}" width="80" height="80" as="geometry"/></mxCell>'
        )

    # --- Edges（正交＋ports＋繞過其他 icon 的 waypoints）---
    node_by_id = {n.get("id"): n for n in nodes if n.get("id")}
    for idx, edge in enumerate(edges):
        src = edge.get("source")
        tgt = edge.get("target")
        if src and tgt:
            edge_id = f"edge_{idx}"
            ports = (1.0, 0.5, 0.0, 0.5)
            waypoints: list[tuple[float, float]] = []
            src_node = node_by_id.get(src)
            tgt_node = node_by_id.get(tgt)
            if src_node is not None and tgt_node is not None:
                ports, waypoints = compute_edge_waypoints(src_node, tgt_node, nodes)
            exit_x, exit_y, entry_x, entry_y = ports
            edge_style = (
                "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                "jettySize=0;html=1;endArrow=block;endFill=1;startArrow=none;"
                "exitPerimeter=0;entryPerimeter=0;"
                "sourcePerimeterSpacing=0;targetPerimeterSpacing=0;"
                f"exitX={_fmt_port(exit_x)};exitY={_fmt_port(exit_y)};exitDx=0;exitDy=0;"
                f"entryX={_fmt_port(entry_x)};entryY={_fmt_port(entry_y)};entryDx=0;entryDy=0;"
            )
            geom = _waypoints_xml(waypoints)
            cells.append(
                f'<mxCell id="{edge_id}" edge="1" parent="1" source="{src}" target="{tgt}" '
                f'style="{edge_style}">{geom}</mxCell>'
            )

    inner_xml = "".join(cells)
    return (
        f"<mxGraphModel><root><mxCell id=\"0\"/><mxCell id=\"1\" parent=\"0\"/>"
        f"{inner_xml}</root></mxGraphModel>"
    )
