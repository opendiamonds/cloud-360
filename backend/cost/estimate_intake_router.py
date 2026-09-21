"""HTTP surface for /api/cost/v1 — estimate intake (C2 contract)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cost import estimate_intake_service as svc
from database import get_db
from models import User
from services.rbac import require_story_action

logger = logging.getLogger("cloud360.estimate_intake_router")

router = APIRouter(tags=["cost-estimate-v1"])


class ShareReplaceBody(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


class SaveEstimateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


def _read_uploads(files: list[UploadFile]) -> tuple[list[UploadFile], list[bytes]]:
    payloads: list[bytes] = []
    for uf in files:
        payloads.append(uf.file.read())
    return files, payloads


@router.post("/sets", status_code=status.HTTP_201_CREATED)
async def upload_estimate_set(
    files: Annotated[list[UploadFile], File(...)],
    diagram_id: Annotated[int | None, Form()] = None,
    cloud_overrides: Annotated[str | None, Form()] = None,
    note: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_story_action("C1", "edit")),
):
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


@router.get("/sets/{set_id}")
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
