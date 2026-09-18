"""
agent_router.py — A1 架構對話／產圖 API（SSE 適配層）

職責：
  - 驗證 JWT 與請求 body
  - 將 design_agent 事件轉成 SSE（message / progress / xml / error）
  - A1↔A3 Multi-Agent：generate-wa-collab（雙 agent＋lens ≥80）
  - 不直接呼叫 OpenRouter；LLM 迴圈由 design_agent（Agent SDK）負責

契約（前端依賴，請勿變更）：
  POST /api/architecture/generate
  body: { messages: [{role, content}], current_xml?: string }
  response: text/event-stream，data 為 JSON {type, content}

  POST /api/architecture/generate-wa-collab
  body: { messages, current_xml?, provider?, diagram_id? }
  response: SSE {type: message|progress|xml_preview|score|complete|error, ...}
"""

from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.design_agent import run_design_agent
from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    llm_auth_ready,
)
from services.prompt_guard import (
    REFUSAL_MESSAGE,
    is_platform_self_modification,
    latest_user_text,
)
from services.rbac import require_arch_action
from services.review_orchestrator import get_accessible_diagram
from services.wa_collab_orchestrator import run_wa_collab

logger = logging.getLogger(__name__)

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    current_xml: Optional[str] = None


class WaCollabRequest(BaseModel):
    messages: List[Message]
    current_xml: Optional[str] = None
    provider: Optional[str] = None
    diagram_id: Optional[int] = None
    persist_review: bool = True
    baseline_findings: Optional[List[dict[str, Any]]] = None
    baseline_overall_score: Optional[float] = None


def _ensure_llm_keys() -> None:
    configure_provider_env()
    if not llm_auth_ready():
        raise HTTPException(status_code=500, detail=auth_error_message())


def _refusal_sse() -> StreamingResponse:
    """SSE: fixed refusal, no Design Agent / LLM call."""

    async def event_generator():
        yield (
            "data: "
            + json.dumps(
                {"type": "message", "content": REFUSAL_MESSAGE},
                ensure_ascii=False,
            )
            + "\n\n"
        )
        yield (
            "data: "
            + json.dumps({"type": "complete"}, ensure_ascii=False)
            + "\n\n"
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/generate")
async def chat_and_generate(
    request: ChatRequest,
    current_user: User = Depends(require_arch_action("edit")),
):
    """
    A1 入口：轉發至 Design Agent，以 SSE 串流回傳。
    需具備架構圖生成編輯權（A1／A2／A4）。
    """
    messages = request.messages
    if not messages:
        raise HTTPException(status_code=400, detail="對話不可為空")

    payload = [{"role": m.role, "content": m.content} for m in messages]
    if is_platform_self_modification(latest_user_text(payload)):
        logger.info(
            "prompt_guard 攔截平台自改請求 user=%s",
            current_user.username,
        )
        return _refusal_sse()

    _ensure_llm_keys()
    logger.info("收到畫圖/對話請求（Agent SDK 路徑），user=%s", current_user.username)

    async def event_generator():
        async for event in run_design_agent(payload, request.current_xml):
            chunk = json.dumps(event, ensure_ascii=False)
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/generate-wa-collab")
async def chat_and_generate_wa_collab(
    request: WaCollabRequest,
    current_user: User = Depends(require_arch_action("edit")),
    db: Session = Depends(get_db),
):
    """
    A1↔A3 Multi-Agent：Design 與 Review 對話，目標無 HIGH_RISK 且分數 ≥ 80（最多 2 輪）。
    回傳 xml_preview；Assessment 優化流程可草稿後再確認儲存。
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="對話不可為空")

    payload = [{"role": m.role, "content": m.content} for m in request.messages]
    if is_platform_self_modification(latest_user_text(payload)):
        logger.info(
            "prompt_guard 攔截 WA collab 平台自改請求 user=%s",
            current_user.username,
        )
        return _refusal_sse()

    _ensure_llm_keys()
    logger.info(
        "收到 WA collab 請求 user=%s diagram_id=%s provider=%s",
        current_user.username,
        request.diagram_id,
        request.provider,
    )

    diagram = None
    if request.diagram_id is not None:
        diagram = get_accessible_diagram(db, current_user, request.diagram_id)
        if not diagram:
            raise HTTPException(status_code=404, detail="找不到架構圖或無權限")

    current_xml = request.current_xml
    if not current_xml and diagram is not None:
        current_xml = diagram.xml_data

    async def event_generator():
        async for event in run_wa_collab(
            db,
            current_user,
            messages=payload,
            current_xml=current_xml,
            provider=request.provider,
            diagram=diagram,
            persist_review=request.persist_review,
            baseline_findings=request.baseline_findings,
            baseline_overall_score=request.baseline_overall_score,
        ):
            chunk = json.dumps(event, ensure_ascii=False)
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
