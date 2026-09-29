"""
wa_collab_orchestrator.py — A1 Design ↔ A3 Review 雙 agent 協作（最多 2 輪）

目標：架構圖無 HIGH_RISK 且 lens 分數 ≥ TARGET_SCORE；過程 SSE 推送 transcript 與 xml_preview。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import ArchitectureReview, User, UserDiagram
from services.collab_suggestions import build_optimize_suggestions_summary
from services.design_agent import run_design_agent
from services.review_agent import (
    fallback_suggestions_from_findings,
    run_review_agent,
)
from services.wa_rule_engine import detect_provider, parse_diagram_summary
from services.wa_score_service import TARGET_SCORE, score_xml

logger = logging.getLogger("cloud360.wa_collab")

MAX_ROUNDS = 2


def _compact_findings(findings: list[dict[str, Any]], limit: int = 10) -> list[dict]:
    out = []
    for f in (findings or [])[:limit]:
        hint = f.get("recommendation_hint") or f.get("message")
        out.append(
            {
                "code": f.get("code"),
                "pillar": f.get("pillar"),
                "severity": f.get("severity") or f.get("risk"),
                "title": f.get("title"),
                "message": f.get("message") or "",
                "hint": hint,
                "recommendation_hint": hint,
                "lens_risk": f.get("lens_risk"),
            }
        )
    return out


def _high_risk_findings(findings: list[dict[str, Any]]) -> list[dict]:
    return [
        f
        for f in _compact_findings(findings, limit=20)
        if f.get("lens_risk") == "HIGH_RISK" or f.get("severity") == "high"
    ]


def _score_event(score_payload: dict[str, Any], round_no: int, provider: str) -> dict[str, Any]:
    return {
        "type": "score",
        "round": round_no,
        "overall_score": score_payload["overall_score"],
        "pillar_scores": score_payload["pillar_scores"],
        "findings": _compact_findings(score_payload["findings"]),
        "high_risk_count": score_payload.get("high_risk_count", 0),
        "passed": score_payload["passed"],
        "provider": provider,
    }


async def _remap_design_events(
    messages: list[dict[str, str]],
    current_xml: Optional[str],
    *,
    round_no: int,
) -> AsyncIterator[dict[str, Any]]:
    """執行 Design Agent，將 xml → xml_preview，message 加上 speaker=design。"""
    last_xml: Optional[str] = None
    async for event in run_design_agent(messages, current_xml):
        et = event.get("type")
        if et == "message":
            yield {
                "type": "message",
                "speaker": "design",
                "content": event.get("content") or "",
                "round": round_no,
            }
        elif et == "progress":
            yield {"type": "progress", "content": event.get("content") or "", "round": round_no}
        elif et == "xml":
            last_xml = event.get("content") or ""
            yield {
                "type": "xml_preview",
                "content": last_xml,
                "round": round_no,
            }
        elif et == "error":
            yield {"type": "error", "content": event.get("content") or "Design Agent 錯誤"}
            return
        else:
            yield event
    if last_xml is not None:
        yield {"type": "_internal_xml", "content": last_xml}


async def _review_speak(
    summary: dict[str, Any],
    score_payload: dict[str, Any],
    *,
    round_no: int,
) -> AsyncIterator[dict[str, Any]]:
    """Review Agent 依 findings 發言（不改圖）；優先消除 HIGH_RISK。"""
    high = _high_risk_findings(score_payload.get("findings") or [])
    rule_for_agent = {
        "overall_score": score_payload["overall_score"],
        "pillar_scores": score_payload["pillar_scores"],
        "high_risk_count": score_payload.get("high_risk_count", len(high)),
        "high_risk_findings": high,
        "findings": score_payload.get("findings") or [],
    }
    parts: list[str] = []
    hr = int(score_payload.get("high_risk_count") or len(high))
    score_now = int(round(float(score_payload.get("overall_score") or 0)))
    yield {
        "type": "progress",
        "content": (
            f"進入評核建議階段，請稍待…"
            f"（高風險 {hr} 項；分數 {score_now}／目標 {TARGET_SCORE}）"
        ),
        "round": round_no,
    }
    try:
        async for chunk in run_review_agent(summary, rule_for_agent):
            parts.append(chunk)
            yield {
                "type": "message",
                "speaker": "review",
                "content": chunk,
                "round": round_no,
            }
    except Exception as e:
        logger.warning("review speak fallback: %s", e)
        text = fallback_suggestions_from_findings(score_payload.get("findings"))
        text = (
            f"目前有 {hr} 項 HIGH_RISK，lens 總分 {score_now}。"
            f"達標需：無高風險且分數 ≥ {TARGET_SCORE}。"
            f"請 Design Agent 優先消高風險並提升分數後再改圖：\n\n{text}"
        )
        parts.append(text)
        yield {
            "type": "message",
            "speaker": "review",
            "content": text,
            "round": round_no,
        }
    full = "".join(parts).strip()
    yield {"type": "_internal_review_text", "content": full}


def _draft_review_block(
    score_payload: dict[str, Any],
    *,
    provider: str,
    collab_status: str,
    suggestions_text: str = "",
) -> dict[str, Any]:
    lens = score_payload.get("lens") or {}
    return {
        "overall_score": score_payload["overall_score"],
        "pillar_scores": score_payload.get("pillar_scores"),
        "findings": score_payload.get("findings") or [],
        "high_risk_count": score_payload.get("high_risk_count", 0),
        "passed": score_payload.get("passed"),
        "lens": lens,
        "risk_counts": lens.get("risk_counts"),
        "rule_pack_version": score_payload.get("rule_pack_version"),
        "provider": provider,
        "collab_status": collab_status,
        "suggestions_text": suggestions_text,
    }


def _complete_event(
    *,
    status: str,
    best_xml: str,
    best_score: dict[str, Any],
    round_no: int,
    provider: str,
    review_id: Optional[int],
    message: str,
    persist_review: bool,
    suggestions_text: str = "",
    baseline_findings: Optional[list[dict[str, Any]]] = None,
    baseline_overall_score: Optional[float] = None,
) -> dict[str, Any]:
    full_findings = best_score.get("findings") or []
    ev: dict[str, Any] = {
        "type": "complete",
        "status": status,
        "overall_score": best_score["overall_score"],
        "high_risk_count": int(best_score.get("high_risk_count") or 0),
        "xml": best_xml,
        "findings": full_findings if not persist_review else _compact_findings(full_findings),
        "review_id": review_id,
        "round": round_no,
        "provider": provider,
        "message": message,
        "persisted": bool(review_id),
    }
    if not persist_review:
        draft_suggestions = suggestions_text.strip() or build_optimize_suggestions_summary(
            baseline_findings or [],
            full_findings,
            baseline_score=baseline_overall_score,
            new_score=best_score.get("overall_score"),
            new_high_risk=int(best_score.get("high_risk_count") or 0),
        )
        ev["draft_review"] = _draft_review_block(
            best_score,
            provider=provider,
            collab_status=status,
            suggestions_text=draft_suggestions,
        )
    return ev


def commit_collab_review(
    db: Session,
    user: User,
    *,
    diagram_id: int,
    xml: str,
    score_payload: dict[str, Any],
    provider: str,
    status_note: str,
) -> tuple[int, int]:
    """覆寫架構圖 XML 並寫入評核紀錄。回傳 (diagram_id, review_id)。"""
    from services.review_orchestrator import get_accessible_diagram

    diagram = get_accessible_diagram(db, user, diagram_id)
    if not diagram:
        raise ValueError("找不到架構圖或無權限")
    diagram.xml_data = xml
    db.commit()
    rid = _persist_review(
        db,
        user,
        diagram=diagram,
        xml=xml,
        provider=provider,
        score_payload=score_payload,
        status_note=status_note,
    )
    if rid is None:
        raise RuntimeError("寫入評核紀錄失敗")
    return diagram.id, rid


def _persist_review(
    db: Session,
    user: User,
    *,
    diagram: Optional[UserDiagram],
    xml: str,
    provider: str,
    score_payload: dict[str, Any],
    status_note: str,
) -> Optional[int]:
    try:
        row = ArchitectureReview(
            diagram_id=diagram.id if diagram else None,
            created_by=user.id,
            provider=provider,
            status="complete" if score_payload.get("passed") else "rules_only",
            overall_score=int(round(score_payload["overall_score"])),
            scores_json=json.dumps(
                {
                    "source_of_truth": "offline_lens",
                    "overall_score": score_payload["overall_score"],
                    "pillar_scores": score_payload["pillar_scores"],
                    "lens": score_payload.get("lens"),
                    "wa_collab": True,
                    "note": status_note,
                },
                ensure_ascii=False,
            ),
            findings_json=json.dumps(score_payload.get("findings") or [], ensure_ascii=False),
            suggestions_text=status_note,
            rule_pack_version=score_payload.get("rule_pack_version"),
            xml_snapshot=xml,
            archived=False,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    except Exception:
        logger.exception("persist collab review failed")
        db.rollback()
        return None


async def run_wa_collab(
    db: Session,
    user: User,
    *,
    messages: list[dict[str, str]],
    current_xml: Optional[str] = None,
    provider: Optional[str] = None,
    diagram: Optional[UserDiagram] = None,
    persist_review: bool = True,
    baseline_findings: Optional[list[dict[str, Any]]] = None,
    baseline_overall_score: Optional[float] = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    雙 agent 協作主流程。yield SSE 事件（見 FD）。
    """
    yield {
        "type": "progress",
        "content": (
            f"啟動 Design ↔ Review 協作（目標：消除 HIGH_RISK 且分數 ≥ {TARGET_SCORE}，"
            f"最多 {MAX_ROUNDS} 輪）"
        ),
    }

    # —— Round 1：Design 產圖／改圖 ——
    yield {"type": "progress", "content": "第 1 輪：Design Agent 產圖中…", "round": 1}
    xml_r1: Optional[str] = None
    async for ev in _remap_design_events(messages, current_xml, round_no=1):
        if ev.get("type") == "_internal_xml":
            xml_r1 = ev.get("content")
            continue
        if ev.get("type") == "error":
            yield ev
            return
        yield ev

    if not xml_r1:
        # 僅對話未產圖：結束（與舊 generate 行為相容）
        yield {
            "type": "complete",
            "status": "no_diagram",
            "overall_score": None,
            "xml": None,
            "findings": [],
            "message": "尚未產圖，協作評核未啟動。",
        }
        return

    yield {
        "type": "message",
        "speaker": "system",
        "content": (
            "架構圖已繪製完成。接下來會進入評核階段，請稍待；"
            "評核進行期間請先不要異動架構圖，待評核與建議完成後再調整。"
        ),
        "round": 1,
    }
    yield {
        "type": "progress",
        "content": "架構圖已完成，進入評核階段，請稍待（請勿異動架構圖）…",
        "round": 1,
    }

    # provider
    resolved_provider = (provider or "").lower().strip()
    if resolved_provider not in ("aws", "gcp", "azure"):
        try:
            det = detect_provider(parse_diagram_summary(xml_r1))
            resolved_provider = (det.get("provider") or "aws").lower()
        except Exception:
            resolved_provider = "aws"

    yield {
        "type": "progress",
        "content": (
            f"進入評核階段，請稍待…"
            f"（第 1 輪：以 {resolved_provider} Active Lens 評分中；請勿異動架構圖）"
        ),
        "round": 1,
    }
    try:
        score1 = await score_xml(db, xml_r1, provider=resolved_provider)
    except Exception as e:
        logger.exception("score round1 failed")
        yield {"type": "error", "content": f"評核失敗：{e}"}
        return

    yield _score_event(score1, 1, resolved_provider)

    best_xml = xml_r1
    best_score = score1

    if score1["passed"]:
        rid = (
            _persist_review(
                db,
                user,
                diagram=diagram,
                xml=best_xml,
                provider=resolved_provider,
                score_payload=score1,
                status_note="wa_collab passed: no HIGH_RISK and score>=target on round 1",
            )
            if persist_review
            else None
        )
        yield _complete_event(
            status="passed",
            best_xml=best_xml,
            best_score=score1,
            round_no=1,
            provider=resolved_provider,
            review_id=rid,
            message=f"已達標（無高風險且分數 ≥ {TARGET_SCORE}），請確認後儲存以覆蓋原架構圖。"
            if not persist_review
            else f"已達標（無高風險且分數 ≥ {TARGET_SCORE}），架構圖可直接使用。",
            persist_review=persist_review,
            baseline_findings=baseline_findings,
            baseline_overall_score=baseline_overall_score,
        )
        return

    # Review 發言
    review_text = ""
    async for ev in _review_speak(score1["summary"], score1, round_no=1):
        if ev.get("type") == "_internal_review_text":
            review_text = ev.get("content") or ""
            continue
        yield ev

    # —— Round 2：Design 依 Review 改圖 ——
    yield {
        "type": "progress",
        "content": "第 2 輪：Design Agent 依 Review 意見改圖（消高風險／提升分數）…",
        "round": 2,
    }
    high_json = json.dumps(
        _high_risk_findings(score1["findings"]),
        ensure_ascii=False,
    )
    findings_json = json.dumps(
        _compact_findings(score1["findings"]),
        ensure_ascii=False,
    )
    hr = int(score1.get("high_risk_count") or 0)
    score_now = int(round(score1["overall_score"]))
    revise_msg = (
        f"Well-Architected Review Agent 評核：高風險 {hr} 項，lens 總分 {score_now}。"
        f"達標條件：HIGH_RISK = 0 且分數 ≥ {TARGET_SCORE}。"
        f"請優先消除所有 HIGH_RISK，並改善分數至 ≥ {TARGET_SCORE}，"
        f"然後呼叫 draw_architecture_diagram 改圖。\n\n"
        f"【必須優先處理的高風險】\n{high_json}\n\n"
        f"【Review Agent 發言】\n{review_text}\n\n"
        f"【全部 findings】\n{findings_json}"
    )
    round2_messages = list(messages) + [
        {"role": "assistant", "content": review_text or "（Review 無文字）"},
        {"role": "user", "content": revise_msg},
    ]

    xml_r2: Optional[str] = None
    async for ev in _remap_design_events(round2_messages, best_xml, round_no=2):
        if ev.get("type") == "_internal_xml":
            xml_r2 = ev.get("content")
            continue
        if ev.get("type") == "error":
            yield ev
            # 仍可用 round1 結果收尾
            break
        yield ev

    if xml_r2:
        best_xml = xml_r2
        yield {
            "type": "progress",
            "content": (
                f"改圖完成，再次進入評核階段，請稍待…"
                f"（第 2 輪：以 {resolved_provider} Active Lens 評分中）"
            ),
            "round": 2,
        }
        try:
            score2 = await score_xml(db, best_xml, provider=resolved_provider)
            best_score = score2
            yield _score_event(score2, 2, resolved_provider)
            if not score2["passed"]:
                # Review 再簡短回應一次（對話可見）
                async for ev in _review_speak(score2["summary"], score2, round_no=2):
                    if ev.get("type") == "_internal_review_text":
                        continue
                    yield ev
        except Exception as e:
            logger.exception("score round2 failed")
            yield {
                "type": "progress",
                "content": f"第 2 輪評核失敗，沿用第 1 輪分數：{e}",
            }

    status = "passed" if best_score.get("passed") else "failed"
    hr_final = int(best_score.get("high_risk_count") or 0)
    score_final = int(round(float(best_score.get("overall_score") or 0)))
    note = (
        f"wa_collab passed: no HIGH_RISK and score>={TARGET_SCORE} on round 2"
        if status == "passed"
        else (
            f"wa_collab failed after {MAX_ROUNDS} rounds; "
            f"high_risk={hr_final}; score={score_final}; needs human"
        )
    )
    rid = (
        _persist_review(
            db,
            user,
            diagram=diagram,
            xml=best_xml,
            provider=resolved_provider,
            score_payload=best_score,
            status_note=note,
        )
        if persist_review
        else None
    )
    yield _complete_event(
        status=status,
        best_xml=best_xml,
        best_score=best_score,
        round_no=2,
        provider=resolved_provider,
        review_id=rid,
        message=(
            f"已達標（無高風險且分數 ≥ {TARGET_SCORE}），請確認後儲存以覆蓋原架構圖。"
            if not persist_review and status == "passed"
            else (
                f"兩輪後尚未達標（高風險 {hr_final} 項、分數 {score_final}），請確認後儲存或取消。"
                if not persist_review
                else (
                    f"已達標（無高風險且分數 ≥ {TARGET_SCORE}），架構圖可直接使用。"
                    if status == "passed"
                    else (
                        f"兩輪後尚未達標（高風險 {hr_final} 項、分數 {score_final}），"
                        "請人工調整後再優化；目前最佳圖已寫入。"
                    )
                )
            )
        ),
        persist_review=persist_review,
        baseline_findings=baseline_findings,
        baseline_overall_score=baseline_overall_score,
    )
