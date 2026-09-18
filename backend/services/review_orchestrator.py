"""
review_orchestrator.py — A3 評核狀態機（timeout／audit／SSE 事件序）
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import ArchitectureReview, User, UserDiagram, diagram_shares
from services.review_agent import fallback_suggestions_from_findings, run_review_agent
from services.wa_lens_engine import (
    LENS_ID,
    answer_lens_with_agent,
    findings_from_lens_score,
    heuristic_answers_from_diagram,
    score_answers,
)
from services.lens_service import resolve_active_lens
from services.wa_rule_engine import (
    RULE_PACK_BY_PROVIDER,
    RULE_PACK_VERSION,
    evaluate,
    parse_diagram_summary,
)

logger = logging.getLogger("cloud360.review_orchestrator")

AGENT_TIMEOUT_SEC = 75.0
LENS_AGENT_TIMEOUT_SEC = 90.0


def audit_log(
    action: str,
    *,
    user_id: int,
    review_id: Optional[int] = None,
    diagram_id: Optional[int] = None,
) -> None:
    logger.info(
        "a3_audit action=%s user_id=%s review_id=%s diagram_id=%s",
        action,
        user_id,
        review_id,
        diagram_id,
    )


def user_can_read_diagram(db: Session, user: User, diagram: UserDiagram) -> bool:
    if diagram.user_id == user.id:
        return True
    shared = (
        db.query(diagram_shares)
        .filter(
            diagram_shares.c.user_id == user.id,
            diagram_shares.c.diagram_id == diagram.id,
        )
        .first()
    )
    return shared is not None


def get_accessible_diagram(
    db: Session, user: User, diagram_id: int
) -> Optional[UserDiagram]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    if not diagram:
        return None
    if not user_can_read_diagram(db, user, diagram):
        return None
    return diagram


def review_to_dict(
    row: ArchitectureReview, *, include_xml: bool = False
) -> dict[str, Any]:
    findings = []
    scores = None
    try:
        findings = json.loads(row.findings_json or "[]")
    except json.JSONDecodeError:
        findings = []
    try:
        scores = json.loads(row.scores_json) if row.scores_json else None
    except json.JSONDecodeError:
        scores = None
    out: dict[str, Any] = {
        "id": row.id,
        "diagram_id": row.diagram_id,
        "created_by": row.created_by,
        "provider": row.provider,
        "status": row.status,
        "overall_score": row.overall_score,
        "scores": scores,
        "findings": findings,
        "suggestions_text": row.suggestions_text,
        "error_message": row.error_message,
        "rule_pack_version": row.rule_pack_version,
        "archived": bool(row.archived),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "has_xml_snapshot": bool(row.xml_snapshot),
    }
    if include_xml:
        out["xml_snapshot"] = row.xml_snapshot
    return out


def _archive_previous(db: Session, diagram_id: int) -> None:
    rows = (
        db.query(ArchitectureReview)
        .filter(
            ArchitectureReview.diagram_id == diagram_id,
            ArchitectureReview.archived.is_(False),
            ArchitectureReview.status.in_(("complete", "rules_only", "unsupported")),
        )
        .all()
    )
    for r in rows:
        r.archived = True
    if rows:
        db.commit()


def user_can_read_review(db: Session, user: User, row: ArchitectureReview) -> bool:
    if row.created_by == user.id:
        return True
    if row.diagram_id is None:
        return False
    diagram = db.query(UserDiagram).filter(UserDiagram.id == row.diagram_id).first()
    if not diagram:
        return False
    return user_can_read_diagram(db, user, diagram)


async def start_review(
    db: Session,
    user: User,
    *,
    diagram: Optional[UserDiagram] = None,
    xml_data: Optional[str] = None,
    provider: str = "aws",
    replace_latest: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    provider = (provider or "aws").lower()
    xml = (xml_data if xml_data is not None else None) or (
        diagram.xml_data if diagram else ""
    )
    xml = xml or ""
    try:
        parse_diagram_summary(xml)
    except ValueError as e:
        yield {
            "type": "error",
            "code": "invalid_xml",
            "message": str(e),
        }
        return

    if replace_latest and diagram is not None:
        _archive_previous(db, diagram.id)

    pack = RULE_PACK_BY_PROVIDER.get(provider, RULE_PACK_VERSION)
    row = ArchitectureReview(
        diagram_id=diagram.id if diagram else None,
        created_by=user.id,
        provider=provider,
        status="pending",
        findings_json="[]",
        xml_snapshot=xml,
        archived=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit_log(
        "review_start",
        user_id=user.id,
        review_id=row.id,
        diagram_id=diagram.id if diagram else None,
    )

    t0 = time.perf_counter()
    try:
        result = evaluate(xml, provider=provider)
    except Exception as e:
        logger.exception("rule engine failed review_id=%s", row.id)
        row.status = "rules_only"
        row.error_message = f"rule_engine_error: {e}"
        db.commit()
        yield {
            "type": "error",
            "review_id": row.id,
            "code": "rule_engine_error",
            "message": str(e),
        }
        return

    rules_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "a3_timing review_id=%s phase=rules ms=%s status=ok provider=%s",
        row.id,
        rules_ms,
        provider,
    )

    row.status = "rules_complete"
    heuristic_block = {
        "pillar_scores": result.pillar_scores,
        "weights": result.weights_snapshot,
        "overall_score": result.overall_score,
        "rule_pack_version": result.rule_pack_version,
    }
    heuristic_findings = [f.__dict__ for f in result.findings]
    for hf in heuristic_findings:
        hf["source"] = "heuristic"
    row.overall_score = int(round(result.overall_score))
    row.scores_json = json.dumps(
        {
            "source_of_truth": "pending_lens",
            "heuristic": heuristic_block,
            "pillar_scores": result.pillar_scores,
            "weights": result.weights_snapshot,
            "overall_score": result.overall_score,
            "provider": provider,
        },
        ensure_ascii=False,
    )
    row.findings_json = "[]"
    row.rule_pack_version = result.rule_pack_version or pack
    db.commit()

    yield {
        "type": "rules_done",
        "review_id": row.id,
        "overall_score": row.overall_score,
        "scores": json.loads(row.scores_json),
        "findings": [],
        "rule_pack_version": row.rule_pack_version,
        "provider": provider,
    }

    summary = parse_diagram_summary(xml)
    lens_error: str | None = None
    lens_block: dict | None = None
    lens_findings: list[dict[str, Any]] = []
    try:
        lens = resolve_active_lens(db, provider)
        try:
            answers = await asyncio.wait_for(
                answer_lens_with_agent(summary, lens),
                timeout=LENS_AGENT_TIMEOUT_SEC,
            )
            heur = heuristic_answers_from_diagram(xml, lens)
            for qid, ids in heur.items():
                if qid not in answers or not answers[qid]:
                    answers[qid] = ids
        except Exception as le:
            logger.warning("lens agent unavailable review_id=%s: %s", row.id, le)
            lens_error = str(le)[:500]
            answers = heuristic_answers_from_diagram(xml, lens)

        lens_block = score_answers(lens, answers)
        lens_findings = findings_from_lens_score(lens, lens_block, source="offline_lens")
        scores_obj = json.loads(row.scores_json or "{}")
        scores_obj["source_of_truth"] = "offline_lens"
        scores_obj["lens"] = lens_block
        scores_obj["heuristic"] = heuristic_block
        scores_obj["pillar_scores"] = lens_block["pillar_scores"]
        scores_obj["overall_score"] = lens_block["overall_score"]
        scores_obj["risk_counts"] = lens_block["risk_counts"]
        scores_obj["weights"] = lens_block["weights"]
        scores_obj["findings_source"] = "offline_lens"
        scores_obj["provider"] = provider
        if lens_error:
            scores_obj["lens_note"] = f"agent_fallback_heuristic:{lens_error}"
        row.scores_json = json.dumps(scores_obj, ensure_ascii=False)
        row.findings_json = json.dumps(lens_findings, ensure_ascii=False)
        row.overall_score = int(round(lens_block["overall_score"]))
        row.rule_pack_version = f"{result.rule_pack_version}+{LENS_ID}"
        db.commit()
        yield {
            "type": "lens_done",
            "review_id": row.id,
            "overall_score": row.overall_score,
            "scores": scores_obj,
            "lens": lens_block,
            "findings": lens_findings,
        }
    except Exception as e:
        logger.exception("offline lens failed review_id=%s", row.id)
        lens_error = str(e)[:500]
        scores_obj = json.loads(row.scores_json or "{}")
        scores_obj["source_of_truth"] = "heuristic"
        scores_obj["lens_error"] = lens_error
        scores_obj["findings_source"] = "heuristic"
        row.scores_json = json.dumps(scores_obj, ensure_ascii=False)
        row.findings_json = json.dumps(heuristic_findings, ensure_ascii=False)
        db.commit()
        yield {
            "type": "error",
            "review_id": row.id,
            "code": "lens_error",
            "message": str(e),
            "status": "rules_complete",
            "findings": heuristic_findings,
            "scores": scores_obj,
        }

    agent_findings = (
        lens_findings
        if lens_findings
        else json.loads(row.findings_json or "[]")
    )
    scores_for_agent = json.loads(row.scores_json or "{}")
    agent_rule_result = {
        "provider": row.provider,
        "rule_pack_version": row.rule_pack_version or pack,
        "pillar_scores": scores_for_agent.get("pillar_scores") or {},
        "overall_score": row.overall_score,
        "weights_snapshot": scores_for_agent.get("weights") or {},
        "findings": agent_findings,
        "findings_source": scores_for_agent.get("findings_source") or "offline_lens",
    }

    suggestions_parts: list[str] = []
    t1 = time.perf_counter()
    deadline = time.monotonic() + AGENT_TIMEOUT_SEC
    try:
        agen = run_review_agent(summary, agent_rule_result)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"ReviewAgent 超過 {int(AGENT_TIMEOUT_SEC)}s 逾時"
                )
            try:
                chunk = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                break
            suggestions_parts.append(chunk)
            yield {"type": "suggestion_delta", "content": chunk, "review_id": row.id}

        text = "".join(suggestions_parts).strip()
        if not text:
            raise RuntimeError("ReviewAgent 未產出 suggestions")
        row.suggestions_text = text
        row.status = "complete"
        if lens_block:
            row.overall_score = int(round(lens_block["overall_score"]))
        row.error_message = None
        db.commit()
        logger.info(
            "a3_timing review_id=%s phase=agent ms=%s status=complete",
            row.id,
            int((time.perf_counter() - t1) * 1000),
        )
        yield {
            "type": "complete",
            "review_id": row.id,
            "status": "complete",
            "suggestions_text": text,
            "overall_score": row.overall_score,
            "scores": json.loads(row.scores_json or "{}"),
            "findings": json.loads(row.findings_json or "[]"),
        }
        audit_log(
            "review_complete",
            user_id=user.id,
            review_id=row.id,
            diagram_id=diagram.id if diagram else None,
        )
    except Exception as e:
        logger.exception("agent failed review_id=%s", row.id)
        findings_list = agent_findings
        fallback = fallback_suggestions_from_findings(findings_list)
        row.suggestions_text = fallback
        row.status = "rules_only"
        row.error_message = str(e)[:2000]
        if lens_block:
            row.overall_score = int(round(lens_block["overall_score"]))
        db.commit()
        logger.info(
            "a3_timing review_id=%s phase=agent ms=%s status=rules_only",
            row.id,
            int((time.perf_counter() - t1) * 1000),
        )
        for piece in (
            fallback[i : i + 120] for i in range(0, len(fallback), 120)
        ):
            yield {
                "type": "suggestion_delta",
                "content": piece,
                "review_id": row.id,
                "fallback": True,
            }
        yield {
            "type": "error",
            "review_id": row.id,
            "code": "agent_error",
            "message": str(e),
            "status": "rules_only",
            "suggestions_text": fallback,
            "overall_score": row.overall_score,
            "scores": json.loads(row.scores_json or "{}"),
            "findings": findings_list,
        }
        audit_log(
            "review_rules_only",
            user_id=user.id,
            review_id=row.id,
            diagram_id=diagram.id if diagram else None,
        )


async def retry_suggestions(
    db: Session,
    user: User,
    row: ArchitectureReview,
    diagram: Optional[UserDiagram] = None,
) -> AsyncIterator[dict[str, Any]]:
    if row.status != "rules_only":
        yield {
            "type": "error",
            "code": "invalid_status",
            "message": "僅 rules_only 可重試建議",
            "review_id": row.id,
        }
        return

    audit_log(
        "review_retry_suggestions",
        user_id=user.id,
        review_id=row.id,
        diagram_id=row.diagram_id,
    )
    try:
        findings = json.loads(row.findings_json or "[]")
        scores = json.loads(row.scores_json or "{}")
    except json.JSONDecodeError:
        findings, scores = [], {}

    rule_result = {
        "provider": row.provider,
        "rule_pack_version": row.rule_pack_version or RULE_PACK_VERSION,
        "pillar_scores": scores.get("pillar_scores") or {},
        "overall_score": row.overall_score,
        "weights_snapshot": scores.get("weights") or {},
        "findings": findings,
    }
    xml = row.xml_snapshot or (diagram.xml_data if diagram else "") or ""
    summary = parse_diagram_summary(xml)
    parts: list[str] = []
    try:
        agen = run_review_agent(summary, rule_result)
        deadline = time.monotonic() + AGENT_TIMEOUT_SEC
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"ReviewAgent 超過 {int(AGENT_TIMEOUT_SEC)}s 逾時"
                )
            try:
                chunk = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                break
            parts.append(chunk)
            yield {"type": "suggestion_delta", "content": chunk, "review_id": row.id}
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("ReviewAgent 未產出 suggestions")
        row.suggestions_text = text
        row.status = "complete"
        row.error_message = None
        db.commit()
        yield {
            "type": "complete",
            "review_id": row.id,
            "status": "complete",
            "suggestions_text": text,
            "overall_score": row.overall_score,
        }
    except Exception as e:
        fallback = fallback_suggestions_from_findings(findings)
        row.suggestions_text = fallback
        row.error_message = str(e)[:2000]
        db.commit()
        for piece in (fallback[i : i + 120] for i in range(0, max(len(fallback), 1), 120)):
            if not piece:
                break
            yield {
                "type": "suggestion_delta",
                "content": piece,
                "review_id": row.id,
                "fallback": True,
            }
        yield {
            "type": "error",
            "review_id": row.id,
            "code": "agent_error",
            "message": str(e),
            "status": "rules_only",
            "suggestions_text": fallback,
        }
