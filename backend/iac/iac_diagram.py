"""Load a diagram by id through the existing public diagram API."""

from __future__ import annotations

from dataclasses import dataclass

from iac.iac_generate import resources_from_diagram_summary
from iac.iac_types import IacGateError, Resource


@dataclass(frozen=True)
class DiagramAssessment:
    status: str
    node_count: int


def assess_diagram_xml(xml: str) -> DiagramAssessment:
    """ready needs a parsed diagram with at least one node. empty and unreadable cannot generate."""
    from services.wa_rule_engine import parse_diagram_summary

    try:
        summary = parse_diagram_summary(xml or "")
    except ValueError:
        return DiagramAssessment("unreadable", 0)
    count = len(summary.get("nodes") or [])
    if count < 1:
        return DiagramAssessment("empty", 0)
    return DiagramAssessment("ready", count)


def require_generatable(resources: list[Resource]) -> None:
    if not resources:
        raise IacGateError("diagram_empty", "diagram has no nodes that can become IaC")


def load_diagram_resources(diagram_id: int, user, db) -> list[Resource]:
    """Read one diagram the caller can already access. Does not own diagrams."""
    from fastapi import HTTPException

    from services.collab_router import _get_accessible_diagram
    from services.wa_rule_engine import parse_diagram_summary

    try:
        diagram = _get_accessible_diagram(diagram_id, user, db)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise IacGateError("invalid_diagram", "diagram_id is not available") from exc
        raise
    try:
        summary = parse_diagram_summary(diagram.xml_data or "")
    except ValueError as exc:
        raise IacGateError("diagram_unreadable", "diagram xml cannot be parsed") from exc
    return resources_from_diagram_summary(summary)


def list_visible_readiness(user, db) -> list[dict]:
    """Assess every diagram the caller can already open. Does not return XML."""
    from services.collab_router import _visible_diagrams

    rows = []
    for diagram in _visible_diagrams(user, db):
        assessed = assess_diagram_xml(diagram.xml_data or "")
        title = diagram.title if isinstance(diagram.title, str) and diagram.title.strip() else "未命名架構圖"
        rows.append(
            {
                "diagram_id": diagram.id,
                "title": title,
                "status": assessed.status,
                "node_count": assessed.node_count,
            }
        )
    return rows
