"""Persist a user-saved IaC draft. File contents stay in the row, never in logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from iac.iac_types import CheckItem, Draft, FileEntry, Finding, ScanReport
from models import IacSavedDraft

ADVICE_MAX_CHARS = 8000


def normalize_advice(value) -> str | None:
    """Keep a short note. Blank and non-text values are stored as absent."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[:ADVICE_MAX_CHARS]


def dump_scan(report: ScanReport) -> str:
    """Serialize one succeeded report. Callers must not log this payload."""
    return json.dumps(
        {
            "report_id": report.report_id,
            "draft_id": report.draft_id,
            "status": report.status,
            "max_severity": report.max_severity,
            "created_at": report.created_at,
            "seq": report.seq,
            "findings": [
                {
                    "id": item.id,
                    "severity": item.severity,
                    "title": item.title,
                    "detail": item.detail,
                    "path": item.path,
                }
                for item in report.findings
            ],
            "checks": [
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "path": item.path,
                    "resource": item.resource,
                }
                for item in report.checks
            ],
        },
        ensure_ascii=False,
    )


def load_scan(raw, diagram_id: int, draft_id: str) -> ScanReport | None:
    """Restore a report only when it belongs to this draft."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("status") != "succeeded" or data.get("draft_id") != draft_id:
        return None
    findings: list[Finding] = []
    for item in data.get("findings") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            return None
        findings.append(
            Finding(
                id=item["id"],
                severity=str(item.get("severity") or ""),
                title=str(item.get("title") or ""),
                detail=item.get("detail") if isinstance(item.get("detail"), str) else None,
                path=item.get("path") if isinstance(item.get("path"), str) else None,
            )
        )
    checks: list[CheckItem] = []
    for item in data.get("checks") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            return None
        status = item.get("status")
        if status not in {"passed", "failed", "skipped"}:
            return None
        checks.append(
            CheckItem(
                id=item["id"],
                title=str(item.get("title") or ""),
                status=status,
                path=item.get("path") if isinstance(item.get("path"), str) else None,
                resource=item.get("resource") if isinstance(item.get("resource"), str) else None,
            )
        )
    report_id = data.get("report_id")
    if not isinstance(report_id, str) or not report_id:
        return None
    return ScanReport(
        report_id=report_id,
        draft_id=draft_id,
        diagram_id=diagram_id,
        status="succeeded",
        findings=findings,
        max_severity=str(data.get("max_severity") or "NONE"),
        created_at=str(data.get("created_at") or ""),
        seq=int(data.get("seq") or 0),
        checks=checks,
    )


def save_draft(
    db,
    draft: Draft,
    advice: str | None = None,
    scan_advice: str | None = None,
    scan: ScanReport | None = None,
) -> str:
    saved_at = datetime.now(timezone.utc)
    payload = json.dumps(
        [{"path": entry.path, "content": entry.content} for entry in draft.files],
        ensure_ascii=False,
    )
    row = (
        db.query(IacSavedDraft)
        .filter(
            IacSavedDraft.user_id == draft.user_id,
            IacSavedDraft.diagram_id == draft.diagram_id,
        )
        .one_or_none()
    )
    if row is None:
        row = IacSavedDraft(
            user_id=draft.user_id,
            diagram_id=draft.diagram_id,
            draft_id=draft.draft_id,
            files_json=payload,
            advice_text=advice,
            scan_advice_text=scan_advice,
            scan_json=dump_scan(scan) if scan is not None else None,
            updated_at=saved_at,
        )
        db.add(row)
    else:
        row.draft_id = draft.draft_id
        row.files_json = payload
        row.advice_text = advice
        row.scan_advice_text = scan_advice
        row.scan_json = dump_scan(scan) if scan is not None else None
        row.updated_at = saved_at
    db.commit()
    return saved_at.isoformat()


def load_draft(db, user_id: int, diagram_id: int) -> Draft | None:
    row = (
        db.query(IacSavedDraft)
        .filter(
            IacSavedDraft.user_id == user_id,
            IacSavedDraft.diagram_id == diagram_id,
        )
        .one_or_none()
    )
    if row is None:
        return None
    try:
        raw = json.loads(row.files_json or "[]")
    except json.JSONDecodeError:
        return None
    files: list[FileEntry] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            content = item.get("content")
            if isinstance(path, str) and isinstance(content, str):
                files.append(FileEntry(path=path, content=content))
    if not files:
        return None
    updated = row.updated_at.isoformat() if row.updated_at is not None else ""
    return Draft(
        draft_id=row.draft_id,
        diagram_id=diagram_id,
        user_id=user_id,
        status="succeeded",
        files=files,
        created_at=updated,
    )


def save_scan_advice(db, user_id: int, diagram_id: int, advice: str | None) -> None:
    """Update the scan note on an existing saved draft. Does not create a row."""
    text = normalize_advice(advice)
    if text is None:
        return
    row = (
        db.query(IacSavedDraft)
        .filter(
            IacSavedDraft.user_id == user_id,
            IacSavedDraft.diagram_id == diagram_id,
        )
        .one_or_none()
    )
    if row is None:
        return
    row.scan_advice_text = text
    row.updated_at = datetime.now(timezone.utc)
    db.commit()


def load_saved(db, user_id: int, diagram_id: int) -> tuple[Draft, str | None, str | None, ScanReport | None] | None:
    draft = load_draft(db, user_id, diagram_id)
    if draft is None:
        return None
    row = (
        db.query(IacSavedDraft)
        .filter(
            IacSavedDraft.user_id == user_id,
            IacSavedDraft.diagram_id == diagram_id,
        )
        .one_or_none()
    )
    advice = normalize_advice(row.advice_text) if row is not None else None
    scan_advice = normalize_advice(row.scan_advice_text) if row is not None else None
    scan = load_scan(row.scan_json, diagram_id, draft.draft_id) if row is not None else None
    return draft, advice, scan_advice, scan
