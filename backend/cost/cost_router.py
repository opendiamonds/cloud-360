"""FastAPI routes for /api/cost (B1 — no budget/banner)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cost import cost_service
from database import get_db
from models import User
from services.auth import get_current_user

router = APIRouter()


class RegionBody(BaseModel):
    region: str = Field(..., min_length=1, max_length=64)


class HoursBody(BaseModel):
    hours: int = Field(..., ge=0, le=24)


class SkuBody(BaseModel):
    sku: str = Field(..., min_length=1)


class OverrideBody(BaseModel):
    hourly_override: Decimal = Field(..., ge=0)


@router.get("/diagrams")
def list_diagrams(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.list_diagrams(db, user)


@router.get("/diagrams/{diagram_id}")
def get_snapshot(
    diagram_id: int,
    run_agent: bool = Query(
        True,
        description="Azure 架構圖是否執行 Pricing Calculator agent（false 僅載入設定與資源列）",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.get_snapshot(db, user, diagram_id, run_agent=run_agent)


@router.get("/diagrams/{diagram_id}/calculator-export/xlsx")
def get_calculator_excel(
    diagram_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Azure Pricing Calculator 官方 Excel 匯出。"""
    xlsx_bytes, filename, media_type = cost_service.export_calculator_excel(db, user, diagram_id)
    if media_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        raise HTTPException(status_code=400, detail="此架構圖請使用 CSV 匯出端點")
    return Response(
        content=xlsx_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/diagrams/{diagram_id}/calculator-export/csv")
def get_calculator_csv(
    diagram_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Google Cloud Pricing Calculator 官方 CSV 匯出。"""
    csv_bytes, filename, media_type = cost_service.export_calculator_excel(db, user, diagram_id)
    if media_type != "text/csv":
        raise HTTPException(status_code=400, detail="此架構圖請使用 Excel 匯出端點")
    return Response(
        content=csv_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/diagrams/{diagram_id}/region")
def put_region(
    diagram_id: int,
    body: RegionBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.apply_region(db, user, diagram_id, body.region)


@router.put("/diagrams/{diagram_id}/lines/{mxcell_id}/hours")
def put_hours(
    diagram_id: int,
    mxcell_id: str,
    body: HoursBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.apply_hours(db, user, diagram_id, mxcell_id, body.hours)


@router.put("/diagrams/{diagram_id}/lines/{mxcell_id}/sku")
def put_sku(
    diagram_id: int,
    mxcell_id: str,
    body: SkuBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.apply_sku(db, user, diagram_id, mxcell_id, body.sku)


@router.put("/diagrams/{diagram_id}/lines/{mxcell_id}/override")
def put_override(
    diagram_id: int,
    mxcell_id: str,
    body: OverrideBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.apply_override(
        db, user, diagram_id, mxcell_id, body.hourly_override
    )


@router.get("/diagrams/{diagram_id}/audit")
def get_audit(
    diagram_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cost_service.get_audit(db, user, diagram_id)
