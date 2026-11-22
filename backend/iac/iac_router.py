"""IaC HTTP surface. RBAC and diagram_id gates live here; cores stay pure."""

from __future__ import annotations

import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from database import get_db
from iac.iac_log import log_event
from iac.iac_schemas import (
    CheckItemModel,
    DraftSummaryModel,
    FileEntryModel,
    FindingModel,
    GenerateResponseModel,
    ModuleTreeModel,
    ReadinessResponseModel,
    SaveDraftResponseModel,
    RewriteResponseModel,
    RewriteResultModel,
    ScanReportModel,
    ScanResponseModel,
    SessionSnapshotModel,
)
from iac.iac_session import get_session
from iac.iac_types import Draft, IacGateError, RewriteResult, ScanReport, SessionSnapshot
from models import User
from services.rbac import require_story_action
from sqlalchemy.orm import Session

router = APIRouter(tags=["iac"])

_STATUS = {
    "missing_diagram_id": 422,
    "invalid_diagram": 422,
    "diagram_mismatch": 422,
    "missing_draft": 422,
    "missing_scan_report": 422,
    "stale_report_id": 422,
    "slot_too_large": 422,
    "generate_failed": 422,
    "scan_failed": 422,
    "rewrite_failed": 422,
    "diagram_empty": 422,
    "diagram_unreadable": 422,
    "invalid_files": 422,
    "generate_busy": 429,
    "generate_timeout": 504,
}


def _upload_entries(raw) -> list:
    from iac.iac_types import FileEntry

    if raw is None:
        return []
    if not isinstance(raw, list):
        raise IacGateError("scan_failed", "Upload must contain .tf files.")
    if len(raw) > 32:
        raise IacGateError("slot_too_large", "Draft exceeds the 16 MiB slot limit.")
    entries = []
    for item in raw:
        if not isinstance(item, dict):
            raise IacGateError("scan_failed", "Upload must contain .tf files.")
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise IacGateError("scan_failed", "Upload must contain .tf files.")
        name = path.replace("\\", "/").split("/")[-1]
        if path != name or not name.endswith(".tf") or ".." in name:
            raise IacGateError("scan_failed", "Upload must contain .tf files.")
        entries.append(FileEntry(path=name, content=content))
    return entries


def _remember_saved_draft(db, user_id: int, diagram_id: int) -> None:
    if get_session()._succeeded_draft(user_id, diagram_id) is not None:
        return
    from iac.iac_store import load_saved

    saved = load_saved(db, user_id, diagram_id)
    if saved is not None:
        draft, advice, scan_advice, scan = saved
        get_session().remember_saved(user_id, diagram_id, draft, advice, scan_advice, scan)


def parse_diagram_id(raw) -> int:
    if raw is None or raw == "":
        raise IacGateError("missing_diagram_id", "diagram_id is required")
    if isinstance(raw, bool) or isinstance(raw, float):
        raise IacGateError("invalid_diagram", "diagram_id must be a positive integer")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and raw.isdecimal():
        value = int(raw)
    else:
        raise IacGateError("invalid_diagram", "diagram_id must be a positive integer")
    if value < 1:
        raise IacGateError("invalid_diagram", "diagram_id must be a positive integer")
    return value


def _request_id(request: Request) -> str:
    incoming = (request.headers.get("x-request-id") or "").strip()
    if incoming and len(incoming) <= 128 and all(ch.isalnum() or ch in "-_." for ch in incoming):
        return incoming
    return str(uuid.uuid4())


def _gate(exc: IacGateError, request_id: str) -> JSONResponse:
    status = _STATUS.get(exc.code, 422)
    response = JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                **({"reason": exc.reason} if exc.reason else {}),
            },
            "request_id": request_id,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


def _finish(request_id, user_id, diagram_id, route, status, started, error_code=None):
    log_event(
        "request_end",
        request_id=request_id,
        user_id=user_id,
        diagram_id=diagram_id,
        route=route,
        status=status,
        error_code=error_code,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _draft_model(draft: Draft) -> DraftSummaryModel:
    return DraftSummaryModel(
        draft_id=draft.draft_id,
        diagram_id=draft.diagram_id,
        status=draft.status,
        module_tree=ModuleTreeModel(
            files=[FileEntryModel(path=entry.path, content=entry.content) for entry in draft.files]
        ),
        created_at=draft.created_at,
    )


def _report_model(report: ScanReport) -> ScanReportModel:
    return ScanReportModel(
        report_id=report.report_id,
        draft_id=report.draft_id,
        diagram_id=report.diagram_id,
        status=report.status,
        findings=[
            FindingModel(
                id=finding.id,
                severity=finding.severity,
                title=finding.title,
                detail=finding.detail,
                path=finding.path,
            )
            for finding in report.findings
        ],
        max_severity=report.max_severity,
        created_at=report.created_at,
        checks=[
            CheckItemModel(
                id=item.id,
                title=item.title,
                status=item.status,
                path=item.path,
                resource=item.resource,
            )
            for item in report.checks
        ],
    )


def _rewrite_model(result: RewriteResult) -> RewriteResultModel:
    return RewriteResultModel(
        rewrite_id=result.rewrite_id,
        draft_id=result.draft_id,
        report_id=result.report_id,
        status=result.status,
        rewritten_paths=list(result.rewritten_paths),
        created_at=result.created_at,
    )


def _snapshot_model(snapshot: SessionSnapshot) -> SessionSnapshotModel:
    return SessionSnapshotModel(
        diagram_id=snapshot.diagram_id,
        draft=_draft_model(snapshot.draft) if snapshot.draft else None,
        latest_scan=_report_model(snapshot.latest_scan) if snapshot.latest_scan else None,
        latest_rewrite=_rewrite_model(snapshot.latest_rewrite) if snapshot.latest_rewrite else None,
        advice=snapshot.advice,
        scan_advice=snapshot.scan_advice,
    )


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in (request.headers.get("accept") or "")


def _sse(payload: dict) -> str:
    # The comment pad pushes each event past transport buffers so tokens paint
    # as they arrive, instead of waiting until the advice stream closes.
    data = "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
    return data + ":" + (" " * 2048) + "\n\n"


def _parse_generate_body(body: dict | None) -> int:
    if not isinstance(body, dict):
        raise IacGateError("missing_diagram_id", "diagram_id is required")
    return parse_diagram_id(body.get("diagram_id"))


def _advice_summary(draft) -> dict:
    """File text for the model only. Callers must not log this payload."""
    remaining = 12000
    files = []
    for entry in draft.files:
        if remaining <= 0:
            break
        content = entry.content[:remaining]
        remaining -= len(content)
        files.append({"path": entry.path, "content": content})
    return {"story": "generate", "diagram_id": draft.diagram_id, "files": files}


async def _advice_deltas(session, draft, request_id: str, user_id: int, diagram_id: int):
    summary = _advice_summary(draft)
    if session.agent_invoke is not None:
        text = str(session.agent_invoke(summary) or "")
        log_event(
            "agent_end",
            request_id=request_id or None,
            user_id=user_id,
            diagram_id=diagram_id,
            route="/api/iac/generate",
            token_est=max(1, len(text) // 4) if text else 0,
        )
        if text:
            yield text
        return
    from iac.iac_agent import stream_default_invoke

    parts: list[str] = []
    async for delta in stream_default_invoke(summary):
        parts.append(delta)
        yield delta
    notes = "".join(parts)
    log_event(
        "agent_end",
        request_id=request_id or None,
        user_id=user_id,
        diagram_id=diagram_id,
        route="/api/iac/generate",
        model="openrouter",
        token_est=max(1, len(notes) // 4) if notes else 0,
    )


async def _generate_events(user, diagram_id: int, resources, request_id: str):
    """Emit the local draft first, then stream an explanation of those files."""
    started = time.perf_counter()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def drive() -> None:
        try:
            draft = await asyncio.to_thread(
                lambda: get_session().generate(
                    user.id,
                    diagram_id,
                    resources,
                    request_id=request_id,
                    skip_agent=True,
                )
            )
            await queue.put({"type": "draft", "draft": _draft_model(draft).model_dump()})

            async def _pump_advice() -> None:
                async for delta in _advice_deltas(get_session(), draft, request_id, user.id, diagram_id):
                    await queue.put({"type": "message", "content": delta})

            try:
                await asyncio.wait_for(_pump_advice(), timeout=25)
            except asyncio.TimeoutError:
                await queue.put(
                    {
                        "type": "message",
                        "content": "AI 建議逾時。草稿已完成，不受影響。",
                    }
                )
            except Exception:
                await queue.put(
                    {
                        "type": "message",
                        "content": "AI 建議暫時無法產生。草稿已完成，不受影響。",
                    }
                )
        except IacGateError as exc:
            await queue.put({"type": "error", "code": exc.code, "message": exc.message})
        except Exception:
            await queue.put(
                {"type": "error", "code": "generate_failed", "message": "Generate failed. Retry the request."}
            )
        finally:
            await queue.put({"type": "_end"})

    task = asyncio.create_task(drive())
    draft_sent = False
    yield _sse({"type": "progress", "content": "正在產生 IaC 草稿 · 已進行 0 秒"})
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                elapsed = int(time.perf_counter() - started)
                if elapsed > 30:
                    if draft_sent:
                        yield _sse(
                            {
                                "type": "message",
                                "content": "AI 建議逾時。草稿已完成，不受影響。",
                            }
                        )
                    break
                label = "正在撰寫 AI 建議" if draft_sent else "正在產生 IaC 草稿"
                yield _sse({"type": "progress", "content": f"{label} · 已進行 {elapsed} 秒"})
                continue
            if event.get("type") == "_end":
                break
            if event.get("type") == "error":
                code = str(event.get("code") or "generate_failed")
                _finish(
                    request_id,
                    user.id,
                    diagram_id,
                    "/api/iac/generate",
                    _STATUS.get(code, 422),
                    started,
                    code,
                )
                yield _sse(event)
                break
            if event.get("type") == "draft":
                draft_sent = True
                _finish(request_id, user.id, diagram_id, "/api/iac/generate", 200, started)
                yield _sse(event)
                continue
            yield _sse(event)
    finally:
        if not task.done():
            task.cancel()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


@router.post(
    "/generate",
    response_model=GenerateResponseModel,
    operation_id="iacGenerate",
)
async def iac_generate(
    request: Request,
    response: Response,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D1", "edit")),
    db: Session = Depends(get_db),
):
    """D1 edit. JSON by default. Accept: text/event-stream yields progress, note tokens, then the draft."""
    started = time.perf_counter()
    request_id = _request_id(request)
    diagram_id = None
    try:
        diagram_id = _parse_generate_body(body)
        if _wants_stream(request):
            from iac.iac_diagram import require_generatable

            resources = get_session().diagram_loader(diagram_id, current_user, db)
            require_generatable(resources)
            return StreamingResponse(
                _generate_events(current_user, diagram_id, resources, request_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "X-Request-ID": request_id,
                },
            )
        draft = await asyncio.to_thread(
            lambda: get_session().generate_http(
                current_user,
                diagram_id,
                db,
                request_id=request_id,
            )
        )
    except IacGateError as exc:
        _finish(request_id, current_user.id, diagram_id, "/api/iac/generate", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, diagram_id, "/api/iac/generate", 200, started)
    return GenerateResponseModel(draft=_draft_model(draft))


async def _advice_only_events(user, diagram_id: int, request_id: str):
    """Stream an explanation of the draft already stored for this diagram."""
    draft = get_session().snapshot(user.id, diagram_id).draft
    if draft is None or draft.status != "succeeded":
        yield _sse({"type": "error", "code": "generate_failed", "message": "Generate failed. Retry the request."})
        return
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def drive() -> None:
        try:
            async def _pump() -> None:
                async for delta in _advice_deltas(get_session(), draft, request_id, user.id, diagram_id):
                    await queue.put({"type": "message", "content": delta})

            await asyncio.wait_for(_pump(), timeout=25)
        except asyncio.TimeoutError:
            await queue.put({"type": "message", "content": "AI 建議逾時。草稿已完成，不受影響。"})
        except Exception:
            await queue.put({"type": "message", "content": "AI 建議暫時無法產生。草稿已完成，不受影響。"})
        finally:
            await queue.put({"type": "_end"})

    task = asyncio.create_task(drive())
    try:
        while True:
            event = await queue.get()
            if event.get("type") == "_end":
                break
            yield _sse(event)
    finally:
        if not task.done():
            task.cancel()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


@router.post("/advice", operation_id="iacAdvice")
async def iac_advice(
    request: Request,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D1", "edit")),
):
    """D1 edit. Streams an explanation of the draft already produced for this diagram."""
    request_id = _request_id(request)
    try:
        diagram_id = _parse_generate_body(body)
    except IacGateError as exc:
        return _gate(exc, request_id)
    return StreamingResponse(
        _advice_only_events(current_user, diagram_id, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


def _scan_advice_summary(report) -> dict:
    """Check titles for the model only. Callers must not log this payload."""
    checks = []
    for item in list(report.checks)[:40]:
        checks.append(
            {
                "title": str(item.title)[:180],
                "status": item.status,
                "resource": item.resource,
                "path": item.path,
            }
        )
    return {"story": "scan", "diagram_id": report.diagram_id, "checks": checks}


async def _scan_advice_deltas(session, report, request_id: str, user_id: int, diagram_id: int):
    summary = _scan_advice_summary(report)
    if session.agent_invoke is not None:
        text = str(session.agent_invoke(summary) or "")
        log_event(
            "agent_end",
            request_id=request_id or None,
            user_id=user_id,
            diagram_id=diagram_id,
            route="/api/iac/scan-advice",
            token_est=max(1, len(text) // 4) if text else 0,
        )
        if text:
            yield text
        return
    from iac.iac_agent import stream_default_invoke

    parts: list[str] = []
    async for delta in stream_default_invoke(summary):
        parts.append(delta)
        yield delta
    notes = "".join(parts)
    log_event(
        "agent_end",
        request_id=request_id or None,
        user_id=user_id,
        diagram_id=diagram_id,
        route="/api/iac/scan-advice",
        model="openrouter",
        token_est=max(1, len(notes) // 4) if notes else 0,
    )


async def _scan_advice_events(user, diagram_id: int, request_id: str, db):
    """Stream a note about the latest succeeded scan, then store it."""
    snapshot = get_session().snapshot(user.id, diagram_id)
    report = snapshot.latest_scan
    if report is None or report.status != "succeeded":
        yield _sse({"type": "error", "code": "missing_scan_report", "message": "A succeeded scan report is required."})
        return
    queue: asyncio.Queue[dict] = asyncio.Queue()
    parts: list[str] = []

    async def drive() -> None:
        try:
            async def _pump() -> None:
                async for delta in _scan_advice_deltas(get_session(), report, request_id, user.id, diagram_id):
                    parts.append(delta)
                    await queue.put({"type": "message", "content": delta})

            await asyncio.wait_for(_pump(), timeout=25)
        except asyncio.TimeoutError:
            await queue.put({"type": "message", "content": "AI 建議逾時。掃描結果不受影響。"})
        except Exception:
            await queue.put({"type": "message", "content": "AI 建議暫時無法產生。掃描結果不受影響。"})
        finally:
            note = "".join(parts).strip()
            if note:
                get_session().remember_scan_advice(user.id, diagram_id, note)
                from iac.iac_store import save_scan_advice

                try:
                    save_scan_advice(db, user.id, diagram_id, note)
                except Exception:
                    pass
            await queue.put({"type": "_end"})

    task = asyncio.create_task(drive())
    try:
        while True:
            event = await queue.get()
            if event.get("type") == "_end":
                break
            yield _sse(event)
    finally:
        if not task.done():
            task.cancel()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


@router.post("/scan-advice", operation_id="iacScanAdvice")
async def iac_scan_advice(
    request: Request,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D2", "edit")),
    db: Session = Depends(get_db),
):
    """D2 edit. Streams a note about the latest scan. Does not rescan."""
    request_id = _request_id(request)
    try:
        diagram_id = _parse_generate_body(body)
        report = get_session().snapshot(current_user.id, diagram_id).latest_scan
        if report is None or report.status != "succeeded":
            raise IacGateError("missing_scan_report", "A succeeded scan report is required.")
    except IacGateError as exc:
        return _gate(exc, request_id)
    return StreamingResponse(
        _scan_advice_events(current_user, diagram_id, request_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


@router.post("/scan", response_model=ScanResponseModel, operation_id="iacScan")
def iac_scan(
    request: Request,
    response: Response,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D2", "edit")),
    db: Session = Depends(get_db),
):
    """D2 edit. diagram_id scans the saved draft. files scans uploaded .tf text and leaves the draft in place."""
    started = time.perf_counter()
    request_id = _request_id(request)
    diagram_id = None
    try:
        if not isinstance(body, dict):
            raise IacGateError("missing_diagram_id", "diagram_id is required")
        uploaded = _upload_entries(body.get("files"))
        if uploaded:
            report = get_session().scan_uploaded(
                current_user.id,
                uploaded,
                request_id=request_id,
            )
        else:
            diagram_id = parse_diagram_id(body.get("diagram_id"))
            _remember_saved_draft(db, current_user.id, diagram_id)
            report = get_session().scan(
                current_user.id,
                diagram_id,
                request_id=request_id,
            )
    except IacGateError as exc:
        _finish(request_id, current_user.id, diagram_id, "/api/iac/scan", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, diagram_id, "/api/iac/scan", 200, started)
    return ScanResponseModel(report=_report_model(report))


@router.post(
    "/secrets/rewrite",
    response_model=RewriteResponseModel,
    operation_id="iacSecretsRewrite",
)
def iac_secrets_rewrite(
    request: Request,
    response: Response,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D3", "edit")),
    db: Session = Depends(get_db),
):
    """D3 edit. Omitted report_id uses the latest succeeded report."""
    del db
    started = time.perf_counter()
    request_id = _request_id(request)
    diagram_id = None
    try:
        if not isinstance(body, dict):
            raise IacGateError("missing_diagram_id", "diagram_id is required")
        diagram_id = parse_diagram_id(body.get("diagram_id"))
        report_id = body.get("report_id")
        if report_id is not None and not isinstance(report_id, str):
            raise IacGateError("stale_report_id", "report_id is no longer valid.")
        result, draft = get_session().rewrite(
            current_user.id,
            diagram_id,
            report_id,
            request_id=request_id,
        )
    except IacGateError as exc:
        _finish(
            request_id,
            current_user.id,
            diagram_id,
            "/api/iac/secrets/rewrite",
            _STATUS.get(exc.code, 422),
            started,
            exc.code,
        )
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, diagram_id, "/api/iac/secrets/rewrite", 200, started)
    return RewriteResponseModel(rewrite=_rewrite_model(result), draft=_draft_model(draft))


@router.get("/readiness", response_model=ReadinessResponseModel, operation_id="iacGetReadiness")
def iac_get_readiness(
    request: Request,
    response: Response,
    current_user: User = Depends(require_story_action("D1", "view")),
    db: Session = Depends(get_db),
):
    """D1 view. Classifies visible diagrams before generate. Does not call a model."""
    from iac.iac_diagram import list_visible_readiness

    started = time.perf_counter()
    request_id = _request_id(request)
    rows = list_visible_readiness(current_user, db)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, None, "/api/iac/readiness", 200, started)
    return ReadinessResponseModel(diagrams=rows)


@router.post("/files", response_model=GenerateResponseModel, operation_id="iacReplaceDraftFiles")
def iac_replace_draft_files(
    request: Request,
    response: Response,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D1", "edit")),
):
    """D1 edit. Replaces the current draft's .tf text. Does not call a model."""
    started = time.perf_counter()
    request_id = _request_id(request)
    diagram_id = None
    try:
        if not isinstance(body, dict):
            raise IacGateError("missing_diagram_id", "diagram_id is required")
        diagram_id = parse_diagram_id(body.get("diagram_id"))
        try:
            entries = _upload_entries(body.get("files"))
        except IacGateError as exc:
            if exc.code == "scan_failed":
                raise IacGateError(
                    "invalid_files",
                    "Draft files must be main.tf, variables.tf, and outputs.tf.",
                ) from exc
            raise
        draft = get_session().replace_files(current_user.id, diagram_id, entries)
    except IacGateError as exc:
        _finish(request_id, current_user.id, diagram_id, "/api/iac/files", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, diagram_id, "/api/iac/files", 200, started)
    return GenerateResponseModel(draft=_draft_model(draft))


@router.post("/save", response_model=SaveDraftResponseModel, operation_id="iacSaveDraft")
def iac_save_draft(
    request: Request,
    response: Response,
    body: dict | None = Body(default=None),
    current_user: User = Depends(require_story_action("D1", "edit")),
    db: Session = Depends(get_db),
):
    """D1 edit. Writes the current draft, both notes, and the scan for that draft. Does not call a model."""
    from iac.iac_store import normalize_advice, save_draft

    started = time.perf_counter()
    request_id = _request_id(request)
    diagram_id = None
    try:
        if not isinstance(body, dict):
            raise IacGateError("missing_diagram_id", "diagram_id is required")
        diagram_id = parse_diagram_id(body.get("diagram_id"))
        saved = get_session()._succeeded_draft(current_user.id, diagram_id)
        if saved is None:
            raise IacGateError("missing_draft", "A succeeded draft is required.")
        advice = normalize_advice(body.get("advice"))
        snapshot = get_session().snapshot(current_user.id, diagram_id)
        scan = snapshot.latest_scan
        if scan is None or scan.status != "succeeded" or scan.draft_id != saved.draft_id:
            scan = None
        saved_at = save_draft(db, saved, advice, scan_advice=snapshot.scan_advice, scan=scan)
        get_session().remember_advice(current_user.id, diagram_id, advice)
    except IacGateError as exc:
        _finish(request_id, current_user.id, diagram_id, "/api/iac/save", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, diagram_id, "/api/iac/save", 200, started)
    return SaveDraftResponseModel(diagram_id=diagram_id, draft_id=saved.draft_id, saved_at=saved_at)


@router.get("/session", response_model=SessionSnapshotModel, operation_id="iacGetSession")
def iac_get_session(
    request: Request,
    response: Response,
    diagram_id: str | None = Query(default=None),
    current_user: User = Depends(require_story_action("D1", "view")),
    db: Session = Depends(get_db),
):
    """D1 view. An empty slot is 200 with null artifact fields. A saved draft is loaded when memory is empty."""
    started = time.perf_counter()
    request_id = _request_id(request)
    parsed = None
    try:
        parsed = parse_diagram_id(diagram_id)
        snapshot = get_session().snapshot(current_user.id, parsed)
        if snapshot.draft is None:
            from iac.iac_store import load_saved

            saved = load_saved(db, current_user.id, parsed)
            if saved is not None:
                draft, advice, scan_advice, scan = saved
                get_session().remember_saved(current_user.id, parsed, draft, advice, scan_advice, scan)
                snapshot = get_session().snapshot(current_user.id, parsed)
    except IacGateError as exc:
        _finish(request_id, current_user.id, parsed, "/api/iac/session", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    response.headers["X-Request-ID"] = request_id
    _finish(request_id, current_user.id, parsed, "/api/iac/session", 200, started)
    return _snapshot_model(snapshot)


@router.get("/download", operation_id="iacDownloadZip")
def iac_download(
    request: Request,
    diagram_id: str | None = Query(default=None),
    current_user: User = Depends(require_story_action("D1", "edit")),
    db: Session = Depends(get_db),
):
    """D1 edit. Severity does not block the zip."""
    del db
    started = time.perf_counter()
    request_id = _request_id(request)
    parsed = None
    try:
        parsed = parse_diagram_id(diagram_id)
        payload = get_session().download(current_user.id, parsed)
    except IacGateError as exc:
        _finish(request_id, current_user.id, parsed, "/api/iac/download", _STATUS.get(exc.code, 422), started, exc.code)
        return _gate(exc, request_id)
    _finish(request_id, current_user.id, parsed, "/api/iac/download", 200, started)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="iac-{parsed}.zip"',
            "X-Request-ID": request_id,
        },
    )
