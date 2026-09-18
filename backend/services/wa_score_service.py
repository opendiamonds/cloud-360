"""
wa_score_service.py — 對架構圖 XML 做 A3 同源 lens 打分（不強制寫入 review）
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from services.lens_service import resolve_active_lens
from services.wa_lens_engine import (
    LENS_ID,
    answer_lens_with_agent,
    enrich_findings_recommendations,
    findings_from_lens_score,
    heuristic_answers_from_diagram,
    score_answers,
)
from services.wa_rule_engine import evaluate, parse_diagram_summary

logger = logging.getLogger("cloud360.wa_score_service")

LENS_AGENT_TIMEOUT_SEC = 90.0
TARGET_SCORE = 80  # 協作達標：無 HIGH_RISK 且 overall_score ≥ 此值


def _high_risk_count(lens_block: dict[str, Any], findings: list[dict[str, Any]]) -> int:
    counts = lens_block.get("risk_counts") or {}
    n = int(counts.get("HIGH_RISK") or 0)
    if n > 0:
        return n
    return sum(
        1
        for f in findings
        if (f.get("lens_risk") == "HIGH_RISK" or f.get("severity") == "high")
    )


async def score_xml(
    db: Session,
    xml: str,
    *,
    provider: str = "aws",
) -> dict[str, Any]:
    """
    回傳：
      overall_score, pillar_scores, findings, summary, rule_result,
      provider, rule_pack_version, source_of_truth, high_risk_count, passed
    passed = 無 HIGH_RISK 且 overall_score ≥ TARGET_SCORE
    """
    provider = (provider or "aws").lower()
    summary = parse_diagram_summary(xml)
    result = evaluate(xml, provider=provider)
    heuristic_findings = [f.__dict__ for f in result.findings]
    for hf in heuristic_findings:
        hf["source"] = "heuristic"

    lens = resolve_active_lens(db, provider)
    lens_error: Optional[str] = None
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
        logger.warning("lens agent unavailable in score_xml: %s", le)
        lens_error = str(le)[:500]
        answers = heuristic_answers_from_diagram(xml, lens)

    lens_block = score_answers(lens, answers)
    lens_findings = findings_from_lens_score(lens, lens_block, source="offline_lens")
    lens_findings = enrich_findings_recommendations(lens_findings, lens)
    high_risk_count = _high_risk_count(lens_block, lens_findings)
    overall = float(lens_block["overall_score"])
    score_ok = overall >= TARGET_SCORE

    return {
        "overall_score": overall,
        "pillar_scores": lens_block["pillar_scores"],
        "findings": lens_findings,
        "heuristic_findings": heuristic_findings,
        "summary": summary,
        "rule_result": {
            "overall_score": result.overall_score,
            "pillar_scores": result.pillar_scores,
            "findings": heuristic_findings,
            "rule_pack_version": result.rule_pack_version,
        },
        "lens": lens_block,
        "provider": provider,
        "rule_pack_version": f"{result.rule_pack_version}+{LENS_ID}",
        "source_of_truth": "offline_lens",
        "lens_note": f"agent_fallback_heuristic:{lens_error}" if lens_error else None,
        "high_risk_count": high_risk_count,
        "passed": high_risk_count == 0 and score_ok,
        "score_at_or_above_target": score_ok,
    }
