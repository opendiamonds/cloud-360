"""C1 cost snapshot orchestration."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from cost.config import COVERAGE_LIST, REGIONS_BY_CLOUD, SUPPORTED_REGIONS
from cost.cost_calculator import (
    LineForCalc,
    is_overspent,
    line_subtotal,
    pie_buckets,
    total_priced,
)
from cost.azure_calculator_runner import AzureCalculatorError, export_azure_calculator_excel
from cost.gcp_calculator_runner import GcpCalculatorError, export_gcp_calculator_csv
from cost.cost_pricing_agent import (
    plan_azure_line_items,
    plan_gcp_line_items,
    pricing_agent_enabled,
    run_cost_pricing_agent,
    run_gcp_pricing_agent,
)
from cost.diagram_extractor import extract_priceable_cells
from cost.price_cache import get_cached_hourly, write_cache
from cost.pricing_client import (
    PriceHit,
    PriceMiss,
    PriceUnsupported,
    fetch_hourly,
    supports_official_hourly,
)
from cost.sku_mapper import map_cell
from cost.sku_ai_resolver import infer_unmapped_cells, resolve_cell
from models import CostAuditEvent, DiagramCost, DiagramCostLine, User, UserDiagram
from services.collab_router import _user_can_access_diagram, _visible_diagrams
from services.rbac import user_can

logger = logging.getLogger(__name__)


def _assert_diagram_visible(user: User, diagram: Optional[UserDiagram]) -> UserDiagram:
    if diagram is None or not _user_can_access_diagram(user, diagram):
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


def _assert_c1_view(db: Session, user: User) -> None:
    if not user_can(
        db,
        user.role,
        "C1",
        "view",
        authorization_status=getattr(user, "authorization_status", "approved"),
    ):
        raise HTTPException(status_code=403, detail="權限不足：無 C1 檢視權限")


def _assert_story_edit(db: Session, user: User, story_id: str) -> None:
    if not user_can(
        db,
        user.role,
        story_id,
        "edit",
        authorization_status=getattr(user, "authorization_status", "approved"),
    ):
        raise HTTPException(status_code=403, detail=f"權限不足：無 {story_id} 編輯權限")


def _get_or_create_diagram_cost(db: Session, diagram_id: int) -> DiagramCost:
    row = db.query(DiagramCost).filter(DiagramCost.diagram_id == diagram_id).first()
    if row is None:
        row = DiagramCost(diagram_id=diagram_id)
        db.add(row)
        db.flush()
    return row


def align_lines(db: Session, diagram_id: int, cells) -> None:
    existing = (
        db.query(DiagramCostLine)
        .filter(DiagramCostLine.diagram_id == diagram_id)
        .all()
    )
    cell_ids = {c.mxcell_id for c in cells}
    for line in existing:
        if line.mxcell_id not in cell_ids:
            db.delete(line)
    for cell in cells:
        found = (
            db.query(DiagramCostLine)
            .filter(
                DiagramCostLine.diagram_id == diagram_id,
                DiagramCostLine.mxcell_id == cell.mxcell_id,
            )
            .first()
        )
        if found is None:
            db.add(
                DiagramCostLine(
                    diagram_id=diagram_id,
                    mxcell_id=cell.mxcell_id,
                    hours=24,
                )
            )
    db.flush()


def record_audit(
    db: Session,
    *,
    diagram_id: int,
    field: str,
    actor_username: str,
    new_value: str,
    old_value: Optional[str] = None,
    mxcell_id: Optional[str] = None,
) -> None:
    db.add(
        CostAuditEvent(
            diagram_id=diagram_id,
            field=field,
            mxcell_id=mxcell_id,
            old_value=old_value,
            new_value=new_value,
            actor_username=actor_username,
        )
    )


def _resolve_line(
    db: Session,
    *,
    cell,
    line_row: DiagramCostLine,
    region: Optional[str],
    cloud_hint: Optional[str] = None,
    llm_batch: Optional[dict] = None,
) -> Dict[str, Any]:
    label = cell.label_plain
    sku = line_row.sku_override
    category = "other"
    cloud = "aws"
    status = "unpriced"
    hourly_list: Optional[Decimal] = None
    hourly_for_calc: Optional[Decimal] = None

    if line_row.hourly_override is not None:
        hourly_list = Decimal(str(line_row.hourly_override))
        hourly_for_calc = hourly_list
        status = "manual_override"
        subtotal = line_subtotal(hourly_for_calc, line_row.hours)
        return {
            "mxcell_id": cell.mxcell_id,
            "label": label,
            "sku": sku,
            "category": category,
            "hourly_list": float(hourly_list) if hourly_list is not None else None,
            "hours": line_row.hours,
            "subtotal": float(subtotal),
            "status": status,
            "_calc": {
                "status": status,
                "hourly": hourly_for_calc,
                "hours": line_row.hours,
                "category": category,
            },
        }

    mapping_note: Optional[str] = None

    if not sku:
        mapped, mapping_note = resolve_cell(
            label,
            cell.style,
            cloud_hint=cloud_hint,
            mxcell_id=cell.mxcell_id,
            llm_batch=llm_batch,
        )
        if mapped.kind == "unique" and mapped.candidate:
            sku = mapped.candidate.sku
            cloud = mapped.candidate.cloud
            category = mapped.candidate.category
        else:
            return {
                "mxcell_id": cell.mxcell_id,
                "label": label,
                "sku": line_row.sku_override,
                "category": category,
                "hourly_list": None,
                "hours": line_row.hours,
                "subtotal": None,
                "status": "unpriced",
                "mapping_note": mapping_note,
                "_calc": None,
            }

    if not region:
        return {
            "mxcell_id": cell.mxcell_id,
            "label": label,
            "sku": sku,
            "category": category,
            "hourly_list": None,
            "hours": line_row.hours,
            "subtotal": None,
            "status": "unpriced",
            "_calc": None,
        }

    if not supports_official_hourly(sku):
        return {
            "mxcell_id": cell.mxcell_id,
            "label": label,
            "sku": sku,
            "category": category,
            "hourly_list": None,
            "hours": line_row.hours,
            "subtotal": None,
            "status": "unpriced",
            "_calc": None,
        }

    cached = get_cached_hourly(db, cloud, sku, region)
    if cached is not None:
        hourly_list = cached
        status = "priced"
    else:
        result = fetch_hourly(cloud, sku, region)
        if isinstance(result, PriceUnsupported):
            status = "unpriced"
        elif isinstance(result, PriceMiss):
            status = "price_fetch_failed"
        elif isinstance(result, PriceHit):
            hourly_list = result.hourly
            status = "priced"
            write_cache(db, cloud, sku, region, result.hourly, result.fetched_at)

    if hourly_list is not None and status == "priced":
        hourly_for_calc = hourly_list
        subtotal = line_subtotal(hourly_for_calc, line_row.hours)
        return {
            "mxcell_id": cell.mxcell_id,
            "label": label,
            "sku": sku,
            "category": category,
            "hourly_list": float(hourly_list) if hourly_list is not None else None,
            "hours": line_row.hours,
            "subtotal": float(subtotal),
            "status": status,
            "mapping_note": mapping_note,
            "_calc": {
                "status": status,
                "hourly": hourly_for_calc,
                "hours": line_row.hours,
                "category": category,
            },
        }

    return {
        "mxcell_id": cell.mxcell_id,
        "label": label,
        "sku": sku,
        "category": category,
        "hourly_list": None,
        "hours": line_row.hours,
        "subtotal": None,
        "status": status,
        "_calc": None,
    }


def build_snapshot(
    db: Session,
    user: User,
    diagram: UserDiagram,
    *,
    run_agent: bool = True,
) -> Dict[str, Any]:
    dc = _get_or_create_diagram_cost(db, diagram.id)
    region = dc.pricing_region
    cells = extract_priceable_cells(diagram.xml_data)
    align_lines(db, diagram.id, cells)
    diagram_cloud = _detect_diagram_cloud(cells)
    allowed_regions = _regions_for_cloud(diagram_cloud)

    # 已存區域若與偵測雲別不符，本輪不當有效估價區域（強制重選）
    if region and not _region_allowed(region, diagram_cloud):
        region = None

    if region:
        _warm_pricing_for_diagram(db, diagram, region)

    line_rows = {
        row.mxcell_id: row
        for row in db.query(DiagramCostLine)
        .filter(DiagramCostLine.diagram_id == diagram.id)
        .all()
    }

    llm_batch = infer_unmapped_cells(cells, cloud_hint=diagram_cloud)

    out_lines: List[Dict[str, Any]] = []
    calc_lines: List[LineForCalc] = []
    pricing_times: List[datetime] = []

    for cell in cells:
        row = line_rows[cell.mxcell_id]
        resolved = _resolve_line(
            db,
            cell=cell,
            line_row=row,
            region=region,
            cloud_hint=diagram_cloud,
            llm_batch=llm_batch,
        )
        calc = resolved.pop("_calc", None)
        out_lines.append(resolved)
        if calc:
            calc_lines.append(calc)  # type: ignore[arg-type]

    total = total_priced(calc_lines) if calc_lines else None
    pie = {k: float(v) for k, v in pie_buckets(calc_lines).items()} if calc_lines else {
        "compute": 0.0,
        "database": 0.0,
        "network": 0.0,
        "other": 0.0,
    }
    unpriced_count = sum(
        1 for line in out_lines if line["status"] in ("unpriced", "price_fetch_failed")
    )

    pricing_source: Optional[str] = None
    pricing_error: Optional[str] = None
    agent_assumptions: List[str] = []
    calculator_lines: List[Dict[str, Any]] = []
    pricing_as_of: Optional[str] = None
    use_calculator_agent = (
        run_agent
        and pricing_agent_enabled()
        and diagram_cloud in ("azure", "gcp")
        and region
    )
    if use_calculator_agent:
        hours_map = {mx: row.hours for mx, row in line_rows.items()}
        try:
            if diagram_cloud == "azure":
                estimate = run_cost_pricing_agent(
                    xml_data=diagram.xml_data,
                    region=region,
                    hours_by_mxcell=hours_map,
                )
            else:
                estimate = run_gcp_pricing_agent(
                    xml_data=diagram.xml_data,
                    region=region,
                    hours_by_mxcell=hours_map,
                )
        except RuntimeError:
            logger.exception("Pricing Calculator agent 無法在同步 context 執行")
            estimate = None

        if estimate is not None:
            pricing_source = estimate.pricing_source
            agent_assumptions = estimate.agent_assumptions
            calculator_lines = estimate.calculator_lines
            if estimate.pricing_as_of:
                pricing_as_of = estimate.pricing_as_of.isoformat()
            if estimate.total_usd is not None:
                total = estimate.total_usd
            else:
                total = None
                if estimate.error:
                    pricing_error = estimate.error
                    logger.warning("%s 估價失敗：%s", diagram_cloud, estimate.error)
        else:
            pricing_source = f"{diagram_cloud}_calculator_failed"
            total = None
            pricing_error = pricing_error or f"{diagram_cloud} pricing agent 無法執行"
    else:
        pricing_as_of = None

    return {
        "id": diagram.id,
        "region": region,
        "region_required": region is None or region == "",
        "diagram_cloud": diagram_cloud,
        "allowed_regions": allowed_regions,
        "lines": out_lines,
        "total": float(total) if total is not None else None,
        "unpriced_count": unpriced_count,
        "pie": pie,
        "pricing_as_of": pricing_as_of,
        "pricing_source": pricing_source,
        "pricing_error": pricing_error,
        "agent_assumptions": agent_assumptions or None,
        "calculator_lines": calculator_lines or None,
        "coverage": COVERAGE_LIST,
        "budget": None,
        "overspent": False,
    }


def get_snapshot(
    db: Session,
    user: User,
    diagram_id: int,
    *,
    run_agent: bool = True,
) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_c1_view(db, user)
    result = build_snapshot(db, user, diagram, run_agent=run_agent)
    db.commit()
    return result


def export_calculator_excel(db: Session, user: User, diagram_id: int) -> tuple[bytes, str, str]:
    """依架構圖 line_items 在雲端 Pricing Calculator 填表並匯出官方檔案。"""
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_c1_view(db, user)

    if not pricing_agent_enabled():
        raise HTTPException(status_code=503, detail="Pricing Calculator 匯出未啟用（需 COST_PRICING_AGENT=1）")

    dc = _get_or_create_diagram_cost(db, diagram.id)
    region = dc.pricing_region
    cells = extract_priceable_cells(diagram.xml_data)
    diagram_cloud = _detect_diagram_cloud(cells)
    if diagram_cloud not in ("azure", "gcp"):
        raise HTTPException(status_code=400, detail="僅 Azure／GCP 架構圖可匯出 Pricing Calculator")
    if not region or not _region_allowed(region, diagram_cloud):
        raise HTTPException(status_code=400, detail="請先選定有效的估價區域並完成估價")

    line_rows = {
        row.mxcell_id: row
        for row in db.query(DiagramCostLine)
        .filter(DiagramCostLine.diagram_id == diagram.id)
        .all()
    }
    hours_map = {mx: row.hours for mx, row in line_rows.items()}
    if diagram_cloud == "azure":
        line_items, _mapping_notes = plan_azure_line_items(diagram.xml_data, hours_map)
        if not line_items:
            raise HTTPException(status_code=400, detail="無可匯出至 Calculator 的 Azure 資源")
        try:
            export_bytes, filename, _source_url = export_azure_calculator_excel(region, line_items)
        except AzureCalculatorError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return export_bytes, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    line_items, _mapping_notes = plan_gcp_line_items(diagram.xml_data, hours_map)
    if not line_items:
        raise HTTPException(status_code=400, detail="無可匯出至 Calculator 的 GCP 資源")
    try:
        export_bytes, filename, _source_url = export_gcp_calculator_csv(region, line_items)
    except GcpCalculatorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return export_bytes, filename, "text/csv"


def list_diagrams(db: Session, user: User) -> Dict[str, Any]:
    _assert_c1_view(db, user)
    items = []
    for d in _visible_diagrams(user, db):
        if user_can(
            db,
            user.role,
            "C1",
            "view",
            authorization_status=getattr(user, "authorization_status", "approved"),
        ):
            items.append({"id": d.id, "title": d.title})
    return {"items": items}


def apply_hours(db: Session, user: User, diagram_id: int, mxcell_id: str, hours: int) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_story_edit(db, user, "C1h")
    line = (
        db.query(DiagramCostLine)
        .filter(
            DiagramCostLine.diagram_id == diagram_id,
            DiagramCostLine.mxcell_id == mxcell_id,
        )
        .first()
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    line.hours = hours
    db.commit()
    return {"mxcell_id": mxcell_id, "hours": hours}


def _detect_diagram_cloud(cells) -> Optional[str]:
    """Majority cloud from unique SKU mappings; None if nothing mapped."""
    counts: Counter[str] = Counter()
    for cell in cells:
        mapped = map_cell(cell.label_plain, cell.style)
        if mapped.kind == "unique" and mapped.candidate:
            counts[mapped.candidate.cloud] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _regions_for_cloud(cloud: Optional[str]) -> List[str]:
    if cloud and cloud in REGIONS_BY_CLOUD:
        return list(REGIONS_BY_CLOUD[cloud])
    return list(SUPPORTED_REGIONS)


def _region_allowed(region: str, cloud: Optional[str]) -> bool:
    return region in _regions_for_cloud(cloud)


def _collect_official_skus(cells) -> set[tuple[str, str]]:
    """Return unique (cloud, sku) pairs that support official hourly lookup."""
    pairs: set[tuple[str, str]] = set()
    for cell in cells:
        mapped = map_cell(cell.label_plain, cell.style)
        if mapped.kind != "unique" or not mapped.candidate:
            continue
        sku = mapped.candidate.sku
        if supports_official_hourly(sku):
            pairs.add((mapped.candidate.cloud, sku))
    return pairs


def _warm_pricing_for_diagram(db: Session, diagram: UserDiagram, region: str) -> None:
    """Pre-fetch official list prices when region changes (populates cache for GET)."""
    cells = extract_priceable_cells(diagram.xml_data)
    for cloud, sku in _collect_official_skus(cells):
        if get_cached_hourly(db, cloud, sku, region) is not None:
            continue
        result = fetch_hourly(cloud, sku, region)
        if isinstance(result, PriceHit):
            write_cache(db, cloud, sku, region, result.hourly, result.fetched_at)


def apply_region(db: Session, user: User, diagram_id: int, region: str) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_story_edit(db, user, "C1r")
    cells = extract_priceable_cells(diagram.xml_data)
    diagram_cloud = _detect_diagram_cloud(cells)
    if not _region_allowed(region, diagram_cloud):
        cloud_label = (diagram_cloud or "unknown").upper()
        allowed = ", ".join(_regions_for_cloud(diagram_cloud))
        raise HTTPException(
            status_code=400,
            detail=f"區域 {region} 不屬於此架構圖雲端（{cloud_label}）。可選：{allowed}",
        )
    dc = _get_or_create_diagram_cost(db, diagram_id)
    dc.pricing_region = region
    db.flush()
    _warm_pricing_for_diagram(db, diagram, region)
    db.commit()
    return {"region": region, "diagram_cloud": diagram_cloud}


def apply_sku(db: Session, user: User, diagram_id: int, mxcell_id: str, sku: str) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_story_edit(db, user, "C1o")
    line = (
        db.query(DiagramCostLine)
        .filter(
            DiagramCostLine.diagram_id == diagram_id,
            DiagramCostLine.mxcell_id == mxcell_id,
        )
        .first()
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    old = line.sku_override
    line.sku_override = sku
    record_audit(
        db,
        diagram_id=diagram_id,
        field="sku_override",
        mxcell_id=mxcell_id,
        old_value=old,
        new_value=sku,
        actor_username=user.username,
    )
    db.commit()
    return {"mxcell_id": mxcell_id, "sku": sku}


def apply_override(
    db: Session, user: User, diagram_id: int, mxcell_id: str, hourly: Decimal
) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_story_edit(db, user, "C1o")
    line = (
        db.query(DiagramCostLine)
        .filter(
            DiagramCostLine.diagram_id == diagram_id,
            DiagramCostLine.mxcell_id == mxcell_id,
        )
        .first()
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    old = str(line.hourly_override) if line.hourly_override is not None else None
    line.hourly_override = hourly
    record_audit(
        db,
        diagram_id=diagram_id,
        field="hourly_override",
        mxcell_id=mxcell_id,
        old_value=old,
        new_value=str(hourly),
        actor_username=user.username,
    )
    db.commit()
    return {"mxcell_id": mxcell_id, "hourly_override": float(hourly)}


def get_audit(db: Session, user: User, diagram_id: int) -> Dict[str, Any]:
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    diagram = _assert_diagram_visible(user, diagram)
    _assert_c1_view(db, user)
    rows = (
        db.query(CostAuditEvent)
        .filter(CostAuditEvent.diagram_id == diagram_id)
        .order_by(CostAuditEvent.created_at.desc())
        .all()
    )
    items = [
        {
            "at": row.created_at.isoformat() if row.created_at else None,
            "actor": row.actor_username,
            "diagram_id": row.diagram_id,
            "field": row.field,
            "mxcell_id": row.mxcell_id,
            "old_value": row.old_value,
            "new_value": row.new_value,
        }
        for row in rows
    ]
    return {"items": items}
