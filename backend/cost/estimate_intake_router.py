"""HTTP surface for /api/cost/v1 — estimate intake (C2 contract)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cost import estimate_intake_service as svc
from database import get_db
from models import DIAGRAM_STATUS_DRAFT, DRAFT_REJECTED_DETAIL, DRAFT_REJECTED_RESPONSE, User, UserDiagram
from services.rbac import require_story_action

logger = logging.getLogger("cloud360.estimate_intake_router")

router = APIRouter(tags=["cost-estimate-v1"])


class ShareReplaceBody(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


class SaveEstimateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class LineItemView(BaseModel):
    ordinal: int
    item_name: str | None = None
    spec: str | None = None
    spec_description: str | None = None
    quantity: float | None = None
    amount: float | None = None
    currency: str | None = None
    parse_status: str
    raw_text: str


class TotalReconciledView(BaseModel):
    attempted: bool | None = None
    within_tolerance: bool | None = None
    skipped_reason: str | None = None


class OffendersView(BaseModel):
    currency_ordinals: list[int]
    quantity_ordinals: list[int]


class MechanicalCheckView(BaseModel):
    currency_consistent: bool
    currency_tie: bool
    quantity_positive: bool
    total_reconciled: TotalReconciledView
    offenders: OffendersView


class CloudEstimateView(BaseModel):
    cloud: str
    stated_total: float | None = None
    currency: str | None = None
    lines: list[LineItemView]
    checks: MechanicalCheckView


class CloudSummaryView(BaseModel):
    cloud: str
    stated_total: float | None = None
    currency: str | None = None
    line_count: int
    unparsed_count: int


class EstimateSetSummaryView(BaseModel):
    id: int
    created_at: str | None = None
    note: str | None = None
    diagram_id: int | None = None
    is_owner: bool
    is_saved: bool
    privacy: str
    clouds: list[CloudSummaryView]
    advice_status: str | None = None


class EstimateSetDetailView(EstimateSetSummaryView):
    estimates: list[CloudEstimateView]
    workload_context: dict | None = None


def _reject_own_draft_diagram(db: Session, user: User, diagram_id: int | None) -> None:
    """261116-brain-create-diagram FR6.4a／契約 C4：估價不得綁草稿。

    判定順序是**擁有權優先**：只有「圖存在、屬於呼叫者、且為草稿」才回 409。
    圖不存在或不屬於呼叫者時維持現況——`diagram_id` 原樣存入、不回錯誤
    （`estimate_access.py`：diagram_id is never consulted）——本 intent 不改變那個
    既有行為，也因此不會成為探測他人圖狀態的管道。
    """
    if diagram_id is None:
        return
    status_value = (
        db.query(UserDiagram.status)
        .filter(UserDiagram.id == diagram_id, UserDiagram.user_id == user.id)
        .scalar()
    )
    if status_value == DIAGRAM_STATUS_DRAFT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DRAFT_REJECTED_DETAIL)


def _read_uploads(files: list[UploadFile]) -> tuple[list[UploadFile], list[bytes]]:
    payloads: list[bytes] = []
    for uf in files:
        payloads.append(uf.file.read())
    return files, payloads


@router.post(
    "/sets",
    status_code=status.HTTP_201_CREATED,
    response_model=EstimateSetDetailView,
    responses=DRAFT_REJECTED_RESPONSE,
)
async def upload_estimate_set(
    files: Annotated[list[UploadFile], File(...)],
    diagram_id: Annotated[int | None, Form()] = None,
    cloud_overrides: Annotated[str | None, Form()] = None,
    note: Annotated[str | None, Form()] = None,
    workload_context: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "edit")),
):
    _reject_own_draft_diagram(db, current_user, diagram_id)
    files_list, payloads = _read_uploads(files)
    try:
        set_row = svc.create_estimate_set(
            db,
            owner=current_user,
            files=files_list,
            payloads=payloads,
            diagram_id=diagram_id,
            cloud_overrides_raw=cloud_overrides,
            note=note,
            workload_context_raw=workload_context,
        )
    except svc.IntakeError as exc:
        svc.raise_as_http(exc)

    # Same-request enqueue of U7 advice job (BR2.8). Failures → Advice=failed + audit; still 201.
    svc.run_enqueue_with_audit(
        db, actor_user_id=current_user.id, estimate_set_id=set_row.id
    )
    tree = svc.load_set_tree(db, set_row.id)
    assert tree is not None
    return svc.detail_view(tree, current_user.id)


@router.patch("/sets/{set_id}")
def save_estimate_set(
    set_id: int,
    body: SaveEstimateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "edit")),
):
    try:
        return svc.save_estimate_set(
            db, viewer=current_user, set_id=set_id, name=body.name
        )
    except svc.IntakeError as exc:
        svc.raise_as_http(exc)


@router.get("/share-users")
def list_share_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    return svc.list_share_users(db, viewer=current_user)


@router.get("/sets")
def list_estimate_sets(
    include_history: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(
        svc.LIST_PAGE_SIZE_DEFAULT, ge=1, le=svc.LIST_PAGE_SIZE_MAX
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    return svc.list_sets(
        db,
        viewer=current_user,
        include_history=include_history,
        page=page,
        page_size=page_size,
    )


@router.get("/sets/{set_id}", response_model=EstimateSetDetailView)
def get_estimate_set(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    return svc.get_set_detail(db, viewer=current_user, set_id=set_id)


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate_set(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "edit")),
):
    svc.delete_set(db, viewer=current_user, set_id=set_id)
    return None


@router.get("/sets/{set_id}/shares")
def list_shares(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    return svc.list_shares(db, viewer=current_user, set_id=set_id)


@router.put("/sets/{set_id}/shares")
def replace_shares(
    set_id: int,
    body: ShareReplaceBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "edit")),
):
    return svc.replace_shares(
        db, viewer=current_user, set_id=set_id, user_ids=body.user_ids
    )


@router.get("/sets/{set_id}/advice")
def get_advice_snapshot(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "view")),
):
    return svc.get_advice_snapshot(db, viewer=current_user, set_id=set_id)
