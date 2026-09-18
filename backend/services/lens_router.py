"""
lens_router.py — A3 Lens criteria editor API (requires A3.review).
Supports per-cloud active lens via ?provider=aws|gcp|azure.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.lens_service import (
    get_active_lens_row,
    make_question_template,
    resolve_active_lens,
    save_active_lens,
    suggest_improvement_plan,
    validate_lens,
)
from services.rbac import require_story_action
from services.wa_rule_engine import SUPPORTED_PROVIDERS

router = APIRouter()


class SuggestImprovementBody(BaseModel):
    title: str = Field(..., min_length=1)


class PutLensBody(BaseModel):
    lens: dict[str, Any]
    provider: str = "aws"


def _provider_or_400(provider: str) -> str:
    p = (provider or "aws").lower()
    if p not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {p}")
    return p


@router.get("/lens/active")
def get_active_lens(
    provider: str = Query("aws"),
    current_user: User = Depends(require_story_action("A3", "review")),
    db: Session = Depends(get_db),
):
    provider = _provider_or_400(provider)
    lens = resolve_active_lens(db, provider)
    return {
        "source": "database" if get_active_lens_row(db, provider) else "file",
        "provider": provider,
        "lens": lens,
        "updated_by": current_user.id,
    }


@router.put("/lens/active")
def put_active_lens(
    body: PutLensBody,
    current_user: User = Depends(require_story_action("A3", "review")),
    db: Session = Depends(get_db),
):
    provider = _provider_or_400(body.provider)
    try:
        saved = save_active_lens(db, body.lens, current_user, provider=provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "source": "database", "provider": provider, "lens": saved}


@router.get("/lens/new-question-template")
def new_question_template(
    pillar_id: str = Query(...),
    title: str = Query("New review question"),
    current_user: User = Depends(require_story_action("A3", "review")),
):
    _ = current_user
    try:
        return {"question": make_question_template(pillar_id, title)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/lens/suggest-improvement-plan")
def post_suggest_improvement(
    body: SuggestImprovementBody,
    current_user: User = Depends(require_story_action("A3", "review")),
):
    _ = current_user
    return {"displayText": suggest_improvement_plan(body.title)}


@router.post("/lens/validate")
def post_validate_lens(
    body: PutLensBody,
    current_user: User = Depends(require_story_action("A3", "review")),
):
    _ = current_user
    try:
        validate_lens(body.lens)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}
