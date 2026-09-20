"""Advice job orchestration — enqueue, timeout, ThreadPoolExecutor (U7)."""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Advice, Estimate, EstimateLineItem, EstimateSet

logger = logging.getLogger("cloud360.advice_orchestrator")

TIMEOUT = timedelta(minutes=5)
_MAX_WORKERS = 2
_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()
_progress: dict[int, dict[str, Any]] = {}
_progress_lock = threading.Lock()
# set_ids with a worker submitted / running (survives "already generating" shell rows)
_inflight: set[int] = set()

# Injected by tests
_run_agent: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None
_session_factory: Optional[Callable[[], Session]] = None

# Human-readable phases for SSE (繁中由 router／前端再對照亦可直接用 message)
PHASE_MESSAGES = {
    "queued": "已排入分析佇列",
    "loading": "正在整理估價明細",
    "pricing": "正在查詢目錄價對照",
    "llm": "正在呼叫 AI 產生建議",
    "saving": "正在寫入建議結果",
    "running": "正在分析估價內容",
    "done": "分析完成",
    "failed": "分析失敗",
    "timeout": "分析逾時",
}


def _db() -> Session:
    factory = _session_factory or SessionLocal
    return factory()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_MAX_WORKERS, thread_name_prefix="advice-job"
            )
        return _executor


def set_progress(set_id: int, **fields: Any) -> None:
    with _progress_lock:
        cur = _progress.get(set_id, {})
        cur.update(fields)
        if "message" not in fields:
            phase = str(cur.get("phase") or "")
            if phase:
                cur["message"] = PHASE_MESSAGES.get(
                    phase, cur.get("message") or "分析進行中"
                )
        cur["updated_at"] = datetime.now(timezone.utc).isoformat()
        _progress[set_id] = cur


def get_progress(set_id: int) -> dict[str, Any]:
    with _progress_lock:
        return dict(_progress.get(set_id, {}))


def clear_progress(set_id: int) -> None:
    with _progress_lock:
        _progress.pop(set_id, None)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def mark_timed_out(db: Session, row: Advice) -> Advice:
    reasons: dict[str, Any] = {}
    if row.unavailable_reasons_json:
        try:
            reasons = json.loads(row.unavailable_reasons_json)
        except json.JSONDecodeError:
            reasons = {}
    reasons["timed_out"] = True
    row.status = "failed"
    row.unavailable_reasons_json = json.dumps(reasons, ensure_ascii=False)
    row.completed_at = _utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    set_progress(
        row.estimate_set_id,
        phase="timeout",
        status="failed",
        message=PHASE_MESSAGES["timeout"],
    )
    return row


def reclaim_stale_generating(db: Session, set_id: int | None = None) -> int:
    """Mark generating rows past TIMEOUT as failed. Returns count."""
    q = db.query(Advice).filter(Advice.status == "generating")
    if set_id is not None:
        q = q.filter(Advice.estimate_set_id == set_id)
    now = _utcnow()
    n = 0
    for row in q.all():
        started = row.started_at
        if started is None:
            continue
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if now - started >= TIMEOUT:
            mark_timed_out(db, row)
            with _executor_lock:
                _inflight.discard(row.estimate_set_id)
            n += 1
    return n


def _load_payload(db: Session, set_id: int) -> dict[str, Any]:
    """Build agent payload — only priced service lines, capped for LLM size."""
    _MAX_LINES_PER_CLOUD = 80

    tree = db.query(EstimateSet).filter(EstimateSet.id == set_id).first()
    if tree is None:
        raise ValueError(f"estimate_set {set_id} missing")
    estimates = (
        db.query(Estimate).filter(Estimate.estimate_set_id == set_id).all()
    )
    clouds: list[dict[str, Any]] = []
    for est in estimates:
        lines = (
            db.query(EstimateLineItem)
            .filter(EstimateLineItem.estimate_id == est.id)
            .order_by(EstimateLineItem.ordinal.asc())
            .all()
        )
        usable = [
            ln
            for ln in lines
            if (ln.item_name or "").strip()
            and ln.amount is not None
            and (ln.parse_status or "") != "unidentifiable"
        ]
        usable.sort(
            key=lambda ln: float(ln.amount) if ln.amount is not None else 0.0,
            reverse=True,
        )
        usable = usable[:_MAX_LINES_PER_CLOUD]
        usable.sort(key=lambda ln: int(ln.ordinal))
        stated = est.stated_total
        clouds.append(
            {
                "cloud": est.cloud,
                "currency": est.currency,
                "stated_total": str(stated) if stated is not None else None,
                "lines": [
                    {
                        "sku": ln.spec or ln.item_name,
                        "description": ln.item_name,
                        "quantity": str(ln.quantity)
                        if ln.quantity is not None
                        else None,
                        "amount": str(ln.amount) if ln.amount is not None else None,
                        "region": None,
                    }
                    for ln in usable
                ],
            }
        )
    return {"estimate_set_id": set_id, "clouds": clouds}


def _default_run_agent(payload: dict[str, Any]) -> dict[str, Any]:
    from cost.cost_advice_agent import generate_advice

    set_id = int(payload.get("estimate_set_id") or 0)

    def on_phase(phase: str, message: str | None = None) -> None:
        if set_id:
            set_progress(
                set_id,
                phase=phase,
                status="generating",
                message=message or PHASE_MESSAGES.get(phase, "分析進行中"),
            )

    return generate_advice(payload, on_phase=on_phase)


def _job(set_id: int) -> None:
    owned = _session_factory is None
    db = _db()
    try:
        logger.info("advice job start set_id=%s", set_id)
        reclaim_stale_generating(db, set_id)
        row = db.query(Advice).filter(Advice.estimate_set_id == set_id).first()
        if row is None or row.status != "generating":
            logger.info(
                "advice job skip set_id=%s status=%s",
                set_id,
                None if row is None else row.status,
            )
            return
        set_progress(
            set_id,
            phase="loading",
            status="generating",
            message=PHASE_MESSAGES["loading"],
        )
        payload = _load_payload(db, set_id)
        line_n = sum(len(c.get("lines") or []) for c in payload.get("clouds") or [])
        set_progress(
            set_id,
            phase="running",
            status="generating",
            message=f"正在分析 {line_n} 筆明細",
            line_count=line_n,
        )
        runner = _run_agent or _default_run_agent
        try:
            result = runner(payload)
        except Exception as exc:  # noqa: BLE001 — persist failure, no secret leak
            logger.warning(
                "advice job failed set_id=%s err=%s",
                set_id,
                type(exc).__name__,
            )
            reasons = {"error": type(exc).__name__}
            row.status = "failed"
            row.unavailable_reasons_json = json.dumps(reasons, ensure_ascii=False)
            row.completed_at = _utcnow()
            db.add(row)
            db.commit()
            set_progress(
                set_id,
                phase="failed",
                status="failed",
                message=PHASE_MESSAGES["failed"],
            )
            return

        set_progress(
            set_id,
            phase="saving",
            status="generating",
            message=PHASE_MESSAGES["saving"],
        )
        db.refresh(row)
        started = row.started_at
        if started and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started and _utcnow() - started >= TIMEOUT:
            mark_timed_out(db, row)
            return

        row.saving_text = result.get("saving_text") or ""
        row.comparison_text = result.get("comparison_text")
        row.quality_text = result.get("quality_text")
        reasons = result.get("unavailable_reasons") or {}
        row.unavailable_reasons_json = json.dumps(reasons, ensure_ascii=False)
        if not row.saving_text.strip():
            row.status = "failed"
            reasons["saving"] = "empty"
            row.unavailable_reasons_json = json.dumps(reasons, ensure_ascii=False)
        else:
            row.status = "completed"
        row.completed_at = _utcnow()
        db.add(row)
        db.commit()
        set_progress(
            set_id,
            phase="done",
            status=row.status,
            message=PHASE_MESSAGES["done"]
            if row.status == "completed"
            else PHASE_MESSAGES["failed"],
        )
        logger.info("advice job end set_id=%s status=%s", set_id, row.status)
    finally:
        with _executor_lock:
            _inflight.discard(set_id)
        if owned:
            db.close()


def enqueue_advice_job(estimate_set_id: int) -> None:
    """Schedule advice generation (replaces U2 no-op hook)."""
    owned = _session_factory is None
    db = _db()
    try:
        reclaim_stale_generating(db, estimate_set_id)
        row = db.query(Advice).filter(Advice.estimate_set_id == estimate_set_id).first()
        if row is None:
            row = Advice(
                estimate_set_id=estimate_set_id,
                status="generating",
                started_at=_utcnow(),
            )
            db.add(row)
            db.commit()
        elif row.status == "generating":
            # Intake creates the shell row first (ensure_advice_generating), then
            # calls enqueue — that is NOT a duplicate. Only skip when a worker
            # is already submitted / running for this set.
            with _executor_lock:
                already = estimate_set_id in _inflight
            if already:
                logger.info(
                    "advice enqueue dedupe set_id=%s (inflight)", estimate_set_id
                )
                return
            started = row.started_at
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if started and _utcnow() - started >= TIMEOUT:
                row.started_at = _utcnow()
                row.completed_at = None
                db.add(row)
                db.commit()
        else:
            # completed / failed: do not auto-rerun (BR7.5)
            return

        set_progress(
            estimate_set_id,
            phase="queued",
            status="generating",
            message=PHASE_MESSAGES["queued"],
        )
        with _executor_lock:
            _inflight.add(estimate_set_id)
        logger.info("advice enqueue submit set_id=%s", estimate_set_id)
        _get_executor().submit(_job, estimate_set_id)
    finally:
        if owned:
            db.close()
