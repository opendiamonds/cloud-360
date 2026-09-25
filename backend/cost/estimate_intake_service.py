"""Estimate intake coordination — validate, parse, persist, enqueue (U2).

HTTP error ``detail`` strings are fixed phrases only (NFR Q1=A).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from cost.estimate_access import (
    can_view_set,
    get_visible_set,
    is_owner,
    list_visible_set_ids,
)
from cost.estimate_audit import write_audit_event
from cost.estimate_parser import ParseResult, parse
from cost.estimate_validator import validate
from models import (
    Advice,
    Estimate,
    EstimateLineItem,
    EstimateSet,
    EstimateShare,
    User,
)

logger = logging.getLogger("cloud360.estimate_intake")

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 3
MIN_FILES = 1
LIST_PAGE_SIZE_MAX = 50
LIST_PAGE_SIZE_DEFAULT = 20

CloudId = Literal["aws", "azure", "gcp"]
VALID_CLOUDS = frozenset({"aws", "azure", "gcp"})

# Fixed client-facing detail phrases (NFR Q1=A)
DETAIL_INVALID_TYPE = "invalid file type"
DETAIL_FILE_TOO_LARGE = "file too large"
DETAIL_TOO_MANY_FILES = "too many files"
DETAIL_TOO_FEW_FILES = "at least one file required"
DETAIL_AMBIGUOUS = "cloud ambiguous; provide cloud_overrides"
DETAIL_BAD_OVERRIDES = "invalid cloud_overrides"
DETAIL_DUPLICATE_CLOUD = "duplicate cloud in upload"
DETAIL_BAD_DIAGRAM_ID = "diagram_id must be a positive integer"
DETAIL_PARSE_FAILED = "unable to parse estimate file"
DETAIL_NAME_REQUIRED = "name required"


class IntakeError(Exception):
    """Maps to HTTPException with fixed detail."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def enqueue_advice_job(estimate_set_id: int) -> None:
    """Delegate to U7 AdviceOrchestrator (ThreadPool)."""
    from cost.advice_orchestrator import enqueue_advice_job as _u7_enqueue

    _u7_enqueue(estimate_set_id)


def _ext_ok(filename: str | None) -> str | None:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".xlsx"):
        return "xlsx"
    return None


def _magic_ok(ext: str, payload: bytes) -> bool:
    if ext == "xlsx":
        return payload[:2] == b"PK"
    if ext == "csv":
        # Reject ZIP/XLSX disguised as CSV
        return payload[:2] != b"PK"
    return False


def validate_upload_files(files: list[UploadFile], payloads: list[bytes]) -> None:
    n = len(files)
    if n < MIN_FILES:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_TOO_FEW_FILES)
    if n > MAX_FILES:
        raise IntakeError(status.HTTP_413_CONTENT_TOO_LARGE, DETAIL_TOO_MANY_FILES)
    for uf, data in zip(files, payloads):
        if len(data) > MAX_FILE_BYTES:
            raise IntakeError(
                status.HTTP_413_CONTENT_TOO_LARGE, DETAIL_FILE_TOO_LARGE
            )
        ext = _ext_ok(uf.filename)
        if ext is None or not _magic_ok(ext, data):
            raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_INVALID_TYPE)


def parse_cloud_overrides(raw: str | None, file_count: int) -> list[CloudId | None]:
    if raw is None or raw.strip() == "":
        return [None] * file_count
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_BAD_OVERRIDES) from exc
    if not isinstance(parsed, list) or len(parsed) != file_count:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_BAD_OVERRIDES)
    out: list[CloudId | None] = []
    for item in parsed:
        if item is None:
            out.append(None)
            continue
        if not isinstance(item, str) or item not in VALID_CLOUDS:
            raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_BAD_OVERRIDES)
        out.append(item)  # type: ignore[arg-type]
    return out


def _resolve_cloud(
    result: ParseResult, override: CloudId | None
) -> CloudId:
    detection = result["detection"]
    status_val = detection.get("status")
    if status_val == "resolved":
        cloud = detection.get("cloud")
        if cloud not in VALID_CLOUDS:
            raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_PARSE_FAILED)
        return cloud  # type: ignore[return-value]
    # ambiguous
    if override is None:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_AMBIGUOUS)
    return override


def _line_to_orm(estimate_id: int, line: dict[str, Any]) -> EstimateLineItem:
    qty = line.get("quantity")
    amt = line.get("amount")
    return EstimateLineItem(
        estimate_id=estimate_id,
        ordinal=int(line["ordinal"]),
        item_name=line.get("itemName") or None,
        spec=line.get("spec") or None,
        spec_description=line.get("specDescription") or None,
        quantity=Decimal(str(qty)) if qty is not None else None,
        amount=Decimal(str(amt)) if amt is not None else None,
        currency=line.get("currency"),
        parse_status=str(line.get("parseStatus") or "unidentifiable"),
        raw_text=str(line.get("rawText") or ""),
    )


def _parse_result_from_estimate(est: Estimate) -> ParseResult:
    lines = []
    for li in est.line_items:
        lines.append(
            {
                "ordinal": li.ordinal,
                "itemName": li.item_name or "",
                "spec": li.spec or "",
                "quantity": float(li.quantity) if li.quantity is not None else None,
                "amount": float(li.amount) if li.amount is not None else None,
                "currency": li.currency,
                "parseStatus": li.parse_status,
                "rawText": li.raw_text,
            }
        )
    return {
        "detection": {"status": "resolved", "cloud": est.cloud},  # type: ignore[typeddict-item]
        "lines": lines,
        "totals": {
            "statedTotal": float(est.stated_total)
            if est.stated_total is not None
            else None,
            "currency": est.currency,
        },
        "sourceFormat": est.source_format,  # type: ignore[typeddict-item]
    }


def _checks_view(parse_result: ParseResult) -> dict[str, Any]:
    raw = validate(parse_result)
    tr = raw["totalReconciled"]
    return {
        "currency_consistent": raw["currencyConsistent"],
        "currency_tie": raw["currencyTie"],
        "quantity_positive": raw["quantityPositive"],
        "total_reconciled": {
            "attempted": tr.get("attempted"),
            "within_tolerance": tr.get("withinTolerance"),
            "skipped_reason": tr.get("skippedReason"),
        },
        "offenders": {
            "currency_ordinals": list(raw["currencyOffenders"]),
            "quantity_ordinals": list(raw["quantityOffenders"]),
        },
    }


def _line_view(li: EstimateLineItem) -> dict[str, Any]:
    return {
        "ordinal": li.ordinal,
        "item_name": li.item_name,
        "spec": li.spec,
        "spec_description": getattr(li, "spec_description", None),
        "quantity": float(li.quantity) if li.quantity is not None else None,
        "amount": float(li.amount) if li.amount is not None else None,
        "currency": li.currency,
        "parse_status": li.parse_status,
        "raw_text": li.raw_text,
    }


def _cloud_estimate_view(est: Estimate) -> dict[str, Any]:
    pr = _parse_result_from_estimate(est)
    return {
        "cloud": est.cloud,
        "stated_total": float(est.stated_total) if est.stated_total is not None else None,
        "currency": est.currency,
        "lines": [_line_view(li) for li in est.line_items],
        "checks": _checks_view(pr),
    }


def _advice_status(set_row: EstimateSet) -> str | None:
    if set_row.advice is None:
        return "none"
    return set_row.advice.status


def _privacy(set_row: EstimateSet) -> str:
    return "shared" if set_row.shares else "private"


def summary_view(set_row: EstimateSet, viewer_id: int) -> dict[str, Any]:
    clouds = []
    for est in set_row.estimates:
        clouds.append(
            {
                "cloud": est.cloud,
                "stated_total": float(est.stated_total)
                if est.stated_total is not None
                else None,
                "currency": est.currency,
                "line_count": int(est.parsed_line_count) + int(est.unparsed_line_count),
                "unparsed_count": int(est.unparsed_line_count),
            }
        )
    created = set_row.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {
        "id": set_row.id,
        "created_at": created.isoformat() if created else None,
        "note": set_row.note,
        "diagram_id": set_row.diagram_id,
        "is_owner": is_owner(set_row, viewer_id),
        "privacy": _privacy(set_row),
        "is_saved": bool(getattr(set_row, "is_saved", False)),
        "clouds": clouds,
        "advice_status": _advice_status(set_row),
    }


def detail_view(set_row: EstimateSet, viewer_id: int) -> dict[str, Any]:
    base = summary_view(set_row, viewer_id)
    base["estimates"] = [_cloud_estimate_view(est) for est in set_row.estimates]
    return base


def load_set_tree(db: Session, set_id: int) -> EstimateSet | None:
    return (
        db.query(EstimateSet)
        .options(
            joinedload(EstimateSet.estimates).joinedload(Estimate.line_items),
            joinedload(EstimateSet.shares),
            joinedload(EstimateSet.advice),
        )
        .filter(EstimateSet.id == set_id)
        .first()
    )


def _load_set_tree(db: Session, set_id: int) -> EstimateSet | None:
    return load_set_tree(db, set_id)


def create_estimate_set(
    db: Session,
    *,
    owner: User,
    files: list[UploadFile],
    payloads: list[bytes],
    diagram_id: int | None,
    cloud_overrides_raw: str | None,
    note: str | None = None,
) -> EstimateSet:
    started = time.monotonic()
    validate_upload_files(files, payloads)
    if diagram_id is not None and diagram_id < 1:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_BAD_DIAGRAM_ID)

    overrides = parse_cloud_overrides(cloud_overrides_raw, len(files))
    resolved: list[tuple[CloudId, ParseResult, str]] = []
    seen_clouds: set[str] = set()

    for uf, data, override in zip(files, payloads, overrides):
        try:
            # Use module-global ``parse`` so tests can patch it.
            result = parse(data, uf.filename)
            # Ambiguous detection / column map left lines empty; re-parse with
            # the caller's cloud override so line items are still extracted.
            if (
                result["detection"].get("status") == "ambiguous"
                and override is not None
            ):
                result = parse(data, uf.filename, forced_cloud=override)
        except Exception:
            logger.warning(
                "parse exception type=%s filename_ext=%s",
                "Error",
                _ext_ok(uf.filename),
            )
            raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_PARSE_FAILED)
        cloud = _resolve_cloud(result, override)
        if cloud in seen_clouds:
            raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_DUPLICATE_CLOUD)
        seen_clouds.add(cloud)
        fmt = result.get("sourceFormat") or _ext_ok(uf.filename) or "csv"
        resolved.append((cloud, result, str(fmt)))

    # Drop payloads from local scope after parse (BR2.3 intent)
    del payloads

    set_row = EstimateSet(
        owner_user_id=owner.id,
        diagram_id=diagram_id,
        note=note,
        is_saved=False,
    )
    db.add(set_row)
    db.flush()

    for cloud, result, fmt in resolved:
        lines = result.get("lines") or []
        parsed_n = sum(1 for ln in lines if ln.get("parseStatus") == "parsed")
        unparsed_n = len(lines) - parsed_n
        totals = result.get("totals") or {}
        stated = totals.get("statedTotal")
        est = Estimate(
            estimate_set_id=set_row.id,
            cloud=cloud,
            stated_total=Decimal(str(stated)) if stated is not None else None,
            currency=totals.get("currency"),
            parsed_line_count=parsed_n,
            unparsed_line_count=unparsed_n,
            source_format=fmt,
        )
        db.add(est)
        db.flush()
        try:
            from cost.sku_catalog import enrich_line_specs

            enrich_line_specs(cloud, lines)
        except Exception:
            logger.info("sku catalog enrich skipped cloud=%s", cloud)
        for line in lines:
            db.add(_line_to_orm(est.id, line))
        write_audit_event(
            db,
            actor_user_id=owner.id,
            estimate_set_id=set_row.id,
            event_type="upload",
            cloud=cloud,
            parsed_line_count=parsed_n,
            unparsed_line_count=unparsed_n,
        )

    db.commit()
    elapsed = time.monotonic() - started
    if elapsed > 10.0:
        logger.warning(
            "upload slow set_id=%s elapsed_s=%.2f", set_row.id, elapsed
        )
    loaded = _load_set_tree(db, set_row.id)
    assert loaded is not None
    return loaded


def ensure_advice_generating(db: Session, estimate_set_id: int) -> Advice:
    row = db.query(Advice).filter(Advice.estimate_set_id == estimate_set_id).first()
    if row is None:
        row = Advice(
            estimate_set_id=estimate_set_id,
            status="generating",
            started_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.status = "generating"
        row.started_at = datetime.now(timezone.utc)
        row.completed_at = None
    db.commit()
    db.refresh(row)
    return row


def mark_advice_failed(db: Session, estimate_set_id: int) -> Advice:
    row = db.query(Advice).filter(Advice.estimate_set_id == estimate_set_id).first()
    if row is None:
        row = Advice(
            estimate_set_id=estimate_set_id,
            status="failed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.status = "failed"
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def run_enqueue_with_audit(
    db: Session, *, actor_user_id: int, estimate_set_id: int
) -> None:
    """Create Advice shell and call enqueue hook; on failure → failed + audit."""
    ensure_advice_generating(db, estimate_set_id)
    try:
        enqueue_advice_job(estimate_set_id)
    except Exception as exc:
        logger.warning(
            "advice enqueue failed set_id=%s exc_type=%s",
            estimate_set_id,
            type(exc).__name__,
        )
        mark_advice_failed(db, estimate_set_id)
        write_audit_event(
            db,
            actor_user_id=actor_user_id,
            estimate_set_id=estimate_set_id,
            event_type="advice_enqueue_failed",
        )
        db.commit()
        return
    write_audit_event(
        db,
        actor_user_id=actor_user_id,
        estimate_set_id=estimate_set_id,
        event_type="advice_enqueue",
    )
    db.commit()


def list_sets(
    db: Session,
    *,
    viewer: User,
    include_history: bool = True,
    page: int = 1,
    page_size: int = LIST_PAGE_SIZE_DEFAULT,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(LIST_PAGE_SIZE_MAX, max(1, page_size))
    ids = list_visible_set_ids(db, viewer.id)
    if not ids:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    q = (
        db.query(EstimateSet)
        .options(
            joinedload(EstimateSet.estimates),
            joinedload(EstimateSet.shares),
            joinedload(EstimateSet.advice),
        )
        .filter(EstimateSet.id.in_(ids))
        .filter(EstimateSet.is_saved.is_(True))
        .order_by(EstimateSet.created_at.desc(), EstimateSet.id.desc())
    )
    rows = q.all()
    if not include_history and rows:
        rows = rows[:1]
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "items": [summary_view(r, viewer.id) for r in page_rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def get_set_detail(db: Session, *, viewer: User, set_id: int) -> dict[str, Any]:
    started = time.monotonic()
    row = get_visible_set(db, set_id, viewer.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    tree = _load_set_tree(db, set_id)
    assert tree is not None
    if not can_view_set(db, tree, viewer.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    elapsed = time.monotonic() - started
    if elapsed > 10.0:
        logger.warning("get detail slow set_id=%s elapsed_s=%.2f", set_id, elapsed)
    return detail_view(tree, viewer.id)


def delete_set(db: Session, *, viewer: User, set_id: int) -> None:
    row = db.query(EstimateSet).filter(EstimateSet.id == set_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_owner(row, viewer.id):
        # Invisible vs forbidden: non-viewer → 404; viewer-not-owner → 403
        if not can_view_set(db, row, viewer.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not owner")
    # BR2.7 級聯刪除含 Audit；刪除事件僅寫應用日誌（列無法在 Set 刪後保留）
    logger.info(
        "estimate_audit event=delete set_id=%s actor=%s", set_id, viewer.id
    )
    db.delete(row)
    db.commit()


def list_shares(db: Session, *, viewer: User, set_id: int) -> dict[str, Any]:
    row = get_visible_set(db, set_id, viewer.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    shares = (
        db.query(EstimateShare, User)
        .join(User, User.id == EstimateShare.user_id)
        .filter(EstimateShare.estimate_set_id == set_id)
        .all()
    )
    entries = []
    for share, user in shares:
        shared_at = share.shared_at
        if shared_at is not None and shared_at.tzinfo is None:
            shared_at = shared_at.replace(tzinfo=timezone.utc)
        entries.append(
            {
                "user_id": user.id,
                "username": user.username,
                "shared_at": shared_at.isoformat() if shared_at else None,
            }
        )
    return {"shares": entries}


def save_estimate_set(
    db: Session, *, viewer: User, set_id: int, name: str
) -> dict[str, Any]:
    """Mark a draft set as saved into history with a display name (stored in note)."""
    cleaned = (name or "").strip()
    if not cleaned:
        raise IntakeError(status.HTTP_400_BAD_REQUEST, DETAIL_NAME_REQUIRED)
    if len(cleaned) > 200:
        cleaned = cleaned[:200]

    row = db.query(EstimateSet).filter(EstimateSet.id == set_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_owner(row, viewer.id):
        if not can_view_set(db, row, viewer.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not owner")

    row.note = cleaned
    row.is_saved = True
    db.add(row)
    write_audit_event(
        db,
        actor_user_id=viewer.id,
        estimate_set_id=set_id,
        event_type="save",
    )
    db.commit()
    tree = _load_set_tree(db, set_id)
    assert tree is not None
    return detail_view(tree, viewer.id)


def list_share_users(db: Session, *, viewer: User) -> list[dict[str, Any]]:
    """Users available as estimate share targets (C1; not arch-edit gated)."""
    users = (
        db.query(User)
        .filter(User.id != viewer.id)
        .order_by(User.username.asc())
        .all()
    )
    return [
        {"id": u.id, "username": u.username, "role": u.role or ""}
        for u in users
    ]


def replace_shares(
    db: Session, *, viewer: User, set_id: int, user_ids: list[int]
) -> dict[str, Any]:
    row = db.query(EstimateSet).filter(EstimateSet.id == set_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_owner(row, viewer.id):
        if not can_view_set(db, row, viewer.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not owner")

    # Deduplicate; ignore owner id in share list
    wanted = {int(uid) for uid in user_ids if int(uid) != int(viewer.id)}
    db.query(EstimateShare).filter(EstimateShare.estimate_set_id == set_id).delete()
    for uid in sorted(wanted):
        user = db.query(User).filter(User.id == uid).first()
        if user is None:
            continue
        db.add(EstimateShare(estimate_set_id=set_id, user_id=uid))
    write_audit_event(
        db,
        actor_user_id=viewer.id,
        estimate_set_id=set_id,
        event_type="share_replace",
    )
    db.commit()
    return list_shares(db, viewer=viewer, set_id=set_id)


def get_advice_snapshot(
    db: Session, *, viewer: User, set_id: int
) -> dict[str, Any]:
    row = get_visible_set(db, set_id, viewer.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    advice = db.query(Advice).filter(Advice.estimate_set_id == set_id).first()
    if advice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    reasons = None
    if advice.unavailable_reasons_json:
        try:
            reasons = json.loads(advice.unavailable_reasons_json)
        except json.JSONDecodeError:
            reasons = None

    def _iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    return {
        "estimate_set_id": set_id,
        "status": advice.status,
        "saving_text": advice.saving_text,
        "comparison_text": advice.comparison_text,
        "quality_text": advice.quality_text,
        "unavailable_reasons": reasons,
        "started_at": _iso(advice.started_at),
        "completed_at": _iso(advice.completed_at),
    }


def raise_as_http(exc: IntakeError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
