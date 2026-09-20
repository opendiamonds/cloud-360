"""SSE advice stream — GET /sets/{set_id}/advice/stream (C3 / U7)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from cost import advice_orchestrator as orch
from cost.estimate_access import get_visible_set
from database import get_db
from models import Advice, User
from services.rbac import require_story_action

logger = logging.getLogger("cloud360.advice_stream_router")

router = APIRouter(tags=["cost-estimate-v1-advice"])

HEARTBEAT_SECONDS = 8.0


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _snapshot(row: Advice) -> dict:
    reasons = None
    if row.unavailable_reasons_json:
        try:
            reasons = json.loads(row.unavailable_reasons_json)
        except json.JSONDecodeError:
            reasons = {"raw": "invalid_json"}
    return {
        "status": row.status,
        "saving_text": row.saving_text,
        "comparison_text": row.comparison_text,
        "quality_text": row.quality_text,
        "unavailable_reasons": reasons,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _elapsed_seconds(row: Advice, now: datetime) -> int:
    started = row.started_at
    if started is None:
        return 0
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, int((now - started).total_seconds()))


def _progress_event(row: Advice, now: datetime) -> dict:
    prog = orch.get_progress(row.estimate_set_id)
    phase = str(prog.get("phase") or "running")
    message = str(
        prog.get("message")
        or orch.PHASE_MESSAGES.get(phase)
        or "正在分析估價內容"
    )
    elapsed = _elapsed_seconds(row, now)
    return {
        "type": "progress",
        "content": {
            "phase": phase,
            "message": message,
            "elapsed_seconds": elapsed,
            "status": prog.get("status") or row.status,
            "line_count": prog.get("line_count"),
            "updated_at": prog.get("updated_at"),
        },
    }


async def _event_stream(db: Session, set_id: int) -> AsyncIterator[str]:
    last_beat = datetime.now(timezone.utc)
    last_progress_key: tuple[Any, ...] | None = None
    # Immediate ack so the client knows the stream is live
    yield _sse(
        {
            "type": "progress",
            "content": {
                "phase": "connected",
                "message": "已連線，開始追蹤分析進度",
                "elapsed_seconds": 0,
            },
        }
    )

    while True:
        orch.reclaim_stale_generating(db, set_id)
        row = db.query(Advice).filter(Advice.estimate_set_id == set_id).first()
        now = datetime.now(timezone.utc)

        if row is None:
            yield _sse(
                {
                    "type": "progress",
                    "content": {
                        "phase": "none",
                        "message": "尚無建議任務，等待建立中",
                        "elapsed_seconds": 0,
                    },
                }
            )
            await asyncio.sleep(1.0)
            db.expire_all()
            continue

        if row.status == "completed":
            yield _sse({"type": "completed", "advice": _snapshot(row)})
            return
        if row.status == "failed":
            reasons = {}
            if row.unavailable_reasons_json:
                try:
                    reasons = json.loads(row.unavailable_reasons_json)
                except json.JSONDecodeError:
                    reasons = {}
            if reasons.get("timed_out"):
                yield _sse({"type": "timeout", "advice": _snapshot(row)})
            else:
                yield _sse({"type": "failed", "advice": _snapshot(row)})
            return

        event = _progress_event(row, now)
        content = event["content"]
        key = (
            content.get("phase"),
            content.get("message"),
            content.get("elapsed_seconds"),
        )
        due_heartbeat = (now - last_beat).total_seconds() >= HEARTBEAT_SECONDS
        if key != last_progress_key or due_heartbeat:
            yield _sse(event)
            last_progress_key = key
            if due_heartbeat:
                yield _sse(
                    {
                        "type": "heartbeat",
                        "content": {
                            "ts": now.isoformat(),
                            "message": content.get("message"),
                            "elapsed_seconds": content.get("elapsed_seconds"),
                            "phase": content.get("phase"),
                        },
                    }
                )
                last_beat = now

        await asyncio.sleep(1.0)
        db.expire_all()


@router.get("/sets/{set_id}/advice/stream")
async def stream_advice(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    visible = get_visible_set(db, set_id, current_user.id)
    if visible is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    return StreamingResponse(
        _event_stream(db, set_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
