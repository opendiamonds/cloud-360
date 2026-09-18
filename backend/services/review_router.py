"""
review_router.py — A3 Well-Architected reviews API（SSE + JSON）
支援：選圖評核、上傳 XML（可選建檔）、自動偵測 provider。
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import ArchitectureReview, User, UserDiagram
from services.rbac import require_story_action, user_can_arch
from services.review_orchestrator import (
    audit_log,
    get_accessible_diagram,
    retry_suggestions,
    review_to_dict,
    start_review,
    user_can_read_review,
)
from services.wa_rule_engine import detect_provider, parse_diagram_summary

logger = logging.getLogger("cloud360.review_router")

router = APIRouter()

MAX_UPLOAD_CHARS = 2 * 1024 * 1024


class StartReviewBody(BaseModel):
    diagram_id: Optional[int] = None
    xml_data: Optional[str] = None
    save_diagram: bool = False
    title: Optional[str] = None
    provider: str = "aws"
    auto_detect_provider: bool = True
    replace_latest: bool = False


class DetectProviderBody(BaseModel):
    xml_data: str = Field(..., min_length=1)


class CommitCollabReviewBody(BaseModel):
    diagram_id: int
    xml_data: str = Field(..., min_length=1)
    provider: str = "aws"
    overall_score: float
    pillar_scores: Optional[dict] = None
    findings: list = Field(default_factory=list)
    high_risk_count: int = 0
    passed: bool = False
    rule_pack_version: Optional[str] = None
    suggestions_text: Optional[str] = None
    lens: Optional[dict] = None
    collab_status: str = "complete"


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_response(generator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _validate_xml(xml: str) -> None:
    if not xml or not xml.strip():
        raise HTTPException(status_code=400, detail="xml_data 不可為空")
    if len(xml) > MAX_UPLOAD_CHARS:
        raise HTTPException(status_code=400, detail="架構圖檔過大（上限約 2MB）")
    try:
        parse_diagram_summary(xml)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/reviews/detect-provider")
def detect_review_provider(
    body: DetectProviderBody,
    current_user: User = Depends(require_story_action("A3", "edit")),
):
    _ = current_user
    _validate_xml(body.xml_data)
    summary = parse_diagram_summary(body.xml_data)
    return detect_provider(summary)


@router.post("/reviews")
async def create_review(
    body: StartReviewBody,
    current_user: User = Depends(require_story_action("A3", "edit")),
    db: Session = Depends(get_db),
):
    xml = body.xml_data
    diagram: Optional[UserDiagram] = None

    if body.save_diagram:
        if not xml:
            raise HTTPException(
                status_code=400, detail="save_diagram 時必須提供 xml_data"
            )
        if not user_can_arch(
            db,
            current_user.role,
            "edit",
            authorization_status=getattr(
                current_user, "authorization_status", "approved"
            ),
        ):
            raise HTTPException(
                status_code=403, detail="儲存架構圖需要架構圖編輯權限"
            )
        _validate_xml(xml)
        title = (body.title or "").strip() or "上傳的架構圖"
        diagram = UserDiagram(
            user_id=current_user.id,
            title=title,
            xml_data=xml,
        )
        db.add(diagram)
        db.commit()
        db.refresh(diagram)
    elif body.diagram_id is not None:
        diagram = get_accessible_diagram(db, current_user, body.diagram_id)
        if not diagram:
            raise HTTPException(status_code=403, detail="無法存取此架構圖或不存在")
        if not xml:
            xml = diagram.xml_data
    elif xml:
        _validate_xml(xml)
    else:
        raise HTTPException(
            status_code=400, detail="請提供 diagram_id 或 xml_data"
        )

    if xml:
        _validate_xml(xml)

    if body.auto_detect_provider and xml:
        provider = detect_provider(parse_diagram_summary(xml))["provider"]
    else:
        provider = (body.provider or "aws").lower()

    async def event_generator():
        async for event in start_review(
            db,
            current_user,
            diagram=diagram,
            xml_data=xml,
            provider=provider,
            replace_latest=body.replace_latest,
        ):
            if event.get("type") == "rules_done":
                event = {**event, "resolved_provider": provider}
            yield _sse(event)

    return _sse_response(event_generator())


@router.post("/reviews/commit-collab")
def commit_collab_review_endpoint(
    body: CommitCollabReviewBody,
    current_user: User = Depends(require_story_action("A3", "edit")),
    db: Session = Depends(get_db),
):
    """A3 優化確認儲存：覆寫原架構圖 XML（不更名）並寫入評核紀錄。"""
    if not user_can_arch(
        db,
        current_user.role,
        "edit",
        authorization_status=getattr(current_user, "authorization_status", "approved"),
    ):
        raise HTTPException(status_code=403, detail="儲存架構圖需要架構圖編輯權限")
    _validate_xml(body.xml_data)
    from services.wa_collab_orchestrator import commit_collab_review

    score_payload = {
        "overall_score": body.overall_score,
        "pillar_scores": body.pillar_scores or {},
        "findings": body.findings,
        "high_risk_count": body.high_risk_count,
        "passed": body.passed,
        "lens": body.lens,
        "rule_pack_version": body.rule_pack_version,
    }
    note = (body.suggestions_text or "").strip() or f"wa_collab commit: {body.collab_status}"
    try:
        diagram_id, review_id = commit_collab_review(
            db,
            current_user,
            diagram_id=body.diagram_id,
            xml=body.xml_data,
            score_payload=score_payload,
            provider=(body.provider or "aws").lower(),
            status_note=note,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    row = db.query(ArchitectureReview).filter(ArchitectureReview.id == review_id).first()
    audit_log(
        "review_commit_collab",
        user_id=current_user.id,
        review_id=review_id,
        diagram_id=diagram_id,
    )
    return review_to_dict(row, include_xml=True) if row else {"review_id": review_id, "diagram_id": diagram_id}


@router.get("/reviews")
def list_reviews(
    diagram_id: Optional[int] = Query(None),
    ephemeral: bool = Query(False),
    include_archived: bool = Query(False),
    current_user: User = Depends(require_story_action("A3", "view")),
    db: Session = Depends(get_db),
):
    if ephemeral:
        q = db.query(ArchitectureReview).filter(
            ArchitectureReview.created_by == current_user.id,
            ArchitectureReview.diagram_id.is_(None),
        )
    elif diagram_id is not None:
        diagram = get_accessible_diagram(db, current_user, diagram_id)
        if not diagram:
            raise HTTPException(status_code=403, detail="無法存取此架構圖或不存在")
        q = db.query(ArchitectureReview).filter(
            ArchitectureReview.diagram_id == diagram_id
        )
    else:
        raise HTTPException(
            status_code=400, detail="diagram_id 必填（或 ephemeral=true）"
        )

    if not include_archived:
        q = q.filter(ArchitectureReview.archived.is_(False))
    rows = q.order_by(ArchitectureReview.created_at.desc()).all()
    audit_log(
        "review_list",
        user_id=current_user.id,
        diagram_id=diagram_id,
    )
    return [review_to_dict(r) for r in rows]


@router.get("/reviews/{review_id}")
def get_review(
    review_id: int,
    current_user: User = Depends(require_story_action("A3", "view")),
    db: Session = Depends(get_db),
):
    row = db.query(ArchitectureReview).filter(ArchitectureReview.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="評核不存在")
    if not user_can_read_review(db, current_user, row):
        raise HTTPException(status_code=403, detail="無法存取此評核")
    audit_log(
        "review_get",
        user_id=current_user.id,
        review_id=row.id,
        diagram_id=row.diagram_id,
    )
    return review_to_dict(row, include_xml=True)


class PersistReviewDiagramBody(BaseModel):
    title: Optional[str] = None
    xml_data: Optional[str] = None


@router.post("/reviews/{review_id}/persist-diagram")
def persist_review_diagram(
    review_id: int,
    body: PersistReviewDiagramBody,
    current_user: User = Depends(require_story_action("A3", "edit")),
    db: Session = Depends(get_db),
):
    """上傳評核後尚未建檔：建立架構圖並將評核綁定到該圖（一次存圖＋評核）。"""
    if not user_can_arch(
        db,
        current_user.role,
        "edit",
        authorization_status=getattr(current_user, "authorization_status", "approved"),
    ):
        raise HTTPException(status_code=403, detail="儲存架構圖需要架構圖編輯權限")

    row = db.query(ArchitectureReview).filter(ArchitectureReview.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="評核不存在")
    if row.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="僅評核建立者可儲存此未建檔評核")
    if row.archived:
        raise HTTPException(status_code=400, detail="已刪除的評核無法再儲存")

    if row.diagram_id is not None:
        return {
            "diagram_id": row.diagram_id,
            "review_id": row.id,
            "already_persisted": True,
            "review": review_to_dict(row),
        }

    xml = (body.xml_data or row.xml_snapshot or "").strip()
    if not xml:
        raise HTTPException(status_code=400, detail="缺少架構圖 XML，無法儲存")
    _validate_xml(xml)
    title = (body.title or "").strip() or "上傳的架構圖"

    diagram = UserDiagram(
        user_id=current_user.id,
        title=title,
        xml_data=xml,
    )
    db.add(diagram)
    db.flush()
    row.diagram_id = diagram.id
    if not row.xml_snapshot:
        row.xml_snapshot = xml
    current_user.last_opened_diagram_id = diagram.id
    db.commit()
    db.refresh(row)
    audit_log(
        "review_persist_diagram",
        user_id=current_user.id,
        review_id=row.id,
        diagram_id=diagram.id,
    )
    return {
        "diagram_id": diagram.id,
        "review_id": row.id,
        "already_persisted": False,
        "review": review_to_dict(row),
    }


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(require_story_action("A3", "edit")),
    db: Session = Depends(get_db),
):
    """刪除評核結果（軟刪除：archived=true，自列表隱藏）。"""
    row = db.query(ArchitectureReview).filter(ArchitectureReview.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="評核不存在")
    if not user_can_read_review(db, current_user, row):
        raise HTTPException(status_code=403, detail="無法存取此評核")

    allowed = row.created_by == current_user.id
    if not allowed and row.diagram_id is not None:
        diagram = get_accessible_diagram(db, current_user, row.diagram_id)
        allowed = bool(diagram and diagram.user_id == current_user.id)
    if not allowed:
        raise HTTPException(status_code=403, detail="僅評核建立者或架構圖擁有者可刪除")

    row.archived = True
    db.commit()
    audit_log(
        "review_delete",
        user_id=current_user.id,
        review_id=row.id,
        diagram_id=row.diagram_id,
    )
    return {"status": "success", "review_id": review_id, "archived": True}


class RenderDiagramBody(BaseModel):
    xml_data: str = Field(..., min_length=1)


def _ensure_mxfile(xml: str) -> str:
    raw = (xml or "").strip()
    if not raw:
        return ""
    if "<mxfile" in raw.lower():
        return raw
    inner = (
        raw
        if "<mxGraphModel" in raw
        else f'<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>{raw}</root></mxGraphModel>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<mxfile host="Cloud-360" agent="Cloud-360" version="22.1.0" type="device">'
        f'<diagram id="export-1" name="Diagram">{inner}</diagram></mxfile>'
    )


@router.post("/diagrams/render-png")
async def render_diagram_png(
    body: RenderDiagramBody,
    current_user: User = Depends(require_story_action("A3", "view")),
):
    """Proxy diagrams.net export → PNG（供 PDF 嵌入架構圖）。"""
    _ = current_user
    _validate_xml(body.xml_data)
    mxfile = _ensure_mxfile(body.xml_data)
    import base64

    import httpx

    endpoints = (
        "https://convert.diagrams.net/node/export",
        "https://exp.draw.io/ImageExport4/export",
    )
    last_err = "export_failed"
    async with httpx.AsyncClient(timeout=90.0) as client:
        for url in endpoints:
            try:
                resp = await client.post(
                    url,
                    json={
                        "xml": mxfile,
                        "format": "png",
                        "embedXml": False,
                        "base64": True,
                        "scale": 1.5,
                    },
                )
                if resp.status_code >= 400:
                    last_err = f"{url} HTTP {resp.status_code}"
                    continue
                ctype = (resp.headers.get("content-type") or "").lower()
                raw = resp.content
                if "image/png" in ctype or (
                    len(raw) > 8 and raw[:8] == b"\x89PNG\r\n\x1a\n"
                ):
                    b64 = base64.b64encode(raw).decode("ascii")
                    return {"data_url": f"data:image/png;base64,{b64}"}
                text = resp.text.strip()
                if text.startswith("data:image"):
                    return {"data_url": text}
                # plain base64
                if len(text) > 100 and "\n" not in text[:80]:
                    return {"data_url": f"data:image/png;base64,{text}"}
                last_err = f"{url} unexpected body"
            except Exception as e:
                last_err = str(e)
                logger.warning("diagram render failed via %s: %s", url, e)
    raise HTTPException(
        status_code=502,
        detail=f"無法產生架構圖預覽圖：{last_err}",
    )


@router.post("/reviews/{review_id}/retry-suggestions")
async def retry_review_suggestions(
    review_id: int,
    current_user: User = Depends(require_story_action("A3", "edit")),
    db: Session = Depends(get_db),
):
    row = db.query(ArchitectureReview).filter(ArchitectureReview.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="評核不存在")
    if not user_can_read_review(db, current_user, row):
        raise HTTPException(status_code=403, detail="無法存取此架構圖")

    diagram = None
    if row.diagram_id is not None:
        diagram = get_accessible_diagram(db, current_user, row.diagram_id)

    async def event_generator():
        async for event in retry_suggestions(db, current_user, row, diagram):
            yield _sse(event)

    return _sse_response(event_generator())
