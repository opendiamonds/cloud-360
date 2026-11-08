"""In-process IaC session keyed by (user_id, diagram_id)."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import datetime, timezone

from iac.iac_agent import run_story_agent
from iac.iac_diagram import load_diagram_resources
from iac.iac_generate import REQUIRED_PATHS, generate_module_tree, is_safe_relative_path
from iac.iac_limits import (
    CHECKOV_TIMEOUT_SECONDS,
    GENERATE_TIMEOUT_SECONDS,
    MAX_GENERATE_IN_FLIGHT,
    MAX_SLOTS_PER_USER,
    SLOT_LIMIT_BYTES,
)
from iac.iac_log import log_event
from iac.iac_redact import redact_files
from iac.iac_scan import default_checkov_runner, run_checkov
from iac.iac_types import (
    Draft,
    FileEntry,
    IacGateError,
    Resource,
    RewriteResult,
    ScanReport,
    SessionSnapshot,
)
from iac.iac_zip import build_module_zip


def call_with_deadline(fn, timeout_s: float):
    """Run ``fn`` once. A deadline raises TimeoutError and does not retry."""
    if timeout_s <= 0:
        raise TimeoutError("deadline")
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="iac")
    future = pool.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FuturesTimeout as exc:
        raise TimeoutError("deadline") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def slot_nbytes(files: list[FileEntry]) -> int:
    total = 0
    for entry in files:
        total += len(entry.path.encode("utf-8"))
        total += len(entry.content.encode("utf-8"))
    return total


@dataclass
class _Slot:
    draft: Draft | None = None
    reports: list[ScanReport] = field(default_factory=list)
    rewrites: list[RewriteResult] = field(default_factory=list)
    advice: str | None = None
    scan_advice: str | None = None
    void: bool = False


class IacWorkspaceSession:
    """One process store. Restarting the process drops every slot."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._slots: dict[tuple[int, int], _Slot] = {}
        self._active: dict[int, int] = {}
        self._epoch: dict[int, int] = {}
        self._lru: dict[int, list[int]] = {}
        self._stale: set[str] = set()
        self._writing: set[tuple[int, int]] = set()
        self._seq = 0
        self._sem = threading.BoundedSemaphore(MAX_GENERATE_IN_FLIGHT)
        self.agent_invoke = None
        self.diagram_loader = load_diagram_resources
        self.generator = generate_module_tree
        self.checkov_runner = default_checkov_runner

    def generate(
        self,
        user_id: int,
        diagram_id: int,
        resources: list[Resource],
        *,
        timeout_s: float | None = None,
        request_id: str = "",
        skip_agent: bool = False,
    ) -> Draft:
        timeout_s = GENERATE_TIMEOUT_SECONDS if timeout_s is None else timeout_s
        epoch = self._activate(user_id, diagram_id)
        if not self._sem.acquire(blocking=False):
            raise IacGateError(
                "generate_busy",
                "Too many in-flight generate requests.",
            )
        key = (user_id, diagram_id)
        try:
            with self._lock:
                if key in self._writing:
                    raise IacGateError(
                        "generate_busy",
                        "A generate is already running for this diagram.",
                    )
                self._writing.add(key)
            try:
                started = time.perf_counter()
                files = self._generate_once(
                    resources,
                    timeout_s,
                    request_id=request_id,
                    user_id=user_id,
                    diagram_id=diagram_id,
                    skip_agent=skip_agent,
                )
                draft = self._commit_draft(user_id, diagram_id, epoch, files)
                log_event(
                    "generate_end",
                    request_id=request_id or None,
                    user_id=user_id,
                    diagram_id=diagram_id,
                    route="/api/iac/generate",
                    status=200,
                    duration_ms=_elapsed_ms(started),
                    llm_ms=_elapsed_ms(started),
                )
                return draft
            finally:
                with self._lock:
                    self._writing.discard(key)
        finally:
            self._sem.release()

    def generate_http(self, user, diagram_id: int, db, *, request_id: str = "") -> Draft:
        from iac.iac_diagram import require_generatable

        resources = self.diagram_loader(diagram_id, user, db)
        require_generatable(resources)
        return self.generate(
            user.id,
            diagram_id,
            resources,
            request_id=request_id,
            skip_agent=True,
        )

    def scan(
        self,
        user_id: int,
        diagram_id: int,
        *,
        runner=None,
        timeout_s: float | None = None,
        request_id: str = "",
    ) -> ScanReport:
        self._activate(user_id, diagram_id)
        started = time.perf_counter()
        draft = self._succeeded_draft(user_id, diagram_id)
        if draft is None:
            raise IacGateError("missing_draft", "A succeeded draft is required.")
        outcome = run_checkov(
            draft.files,
            runner=runner or self.checkov_runner,
            timeout_s=CHECKOV_TIMEOUT_SECONDS if timeout_s is None else timeout_s,
        )
        report = self._store_report(user_id, diagram_id, draft, outcome)
        log_event(
            "checkov_end",
            request_id=request_id or None,
            user_id=user_id,
            diagram_id=diagram_id,
            route="/api/iac/scan",
            status=200 if outcome.status == "succeeded" else 422,
            error_code=None if outcome.status == "succeeded" else "scan_failed",
            reason=None if outcome.status == "succeeded" else outcome.message,
            duration_ms=_elapsed_ms(started),
            checkov_ms=_elapsed_ms(started),
            exit_code=0 if outcome.status == "succeeded" else 1,
        )
        if outcome.status != "succeeded":
            raise IacGateError(
                "scan_failed",
                "Static scan failed. Retry the request.",
                reason=outcome.message or None,
            )
        return report

    def scan_uploaded(
        self,
        user_id: int,
        files: list[FileEntry],
        *,
        runner=None,
        timeout_s: float | None = None,
        request_id: str = "",
    ) -> ScanReport:
        """Scan caller-supplied .tf files. Does not replace a saved diagram draft."""
        started = time.perf_counter()
        if not files:
            raise IacGateError("missing_draft", "A succeeded draft is required.")
        for entry in files:
            if not is_safe_relative_path(entry.path) or not entry.path.endswith(".tf"):
                raise IacGateError("scan_failed", "Upload must contain .tf files.")
        if slot_nbytes(files) > SLOT_LIMIT_BYTES:
            raise IacGateError("slot_too_large", "Draft exceeds the 16 MiB slot limit.")
        outcome = run_checkov(
            files,
            runner=runner or self.checkov_runner,
            timeout_s=CHECKOV_TIMEOUT_SECONDS if timeout_s is None else timeout_s,
        )
        if outcome.status != "succeeded":
            raise IacGateError(
                "scan_failed",
                "Static scan failed. Retry the request.",
                reason=outcome.message or None,
            )
        report = ScanReport(
            report_id=str(uuid.uuid4()),
            draft_id="upload",
            diagram_id=0,
            status="succeeded",
            findings=list(outcome.findings),
            max_severity=outcome.max_severity,
            created_at=_now(),
            checks=list(outcome.checks),
        )
        log_event(
            "checkov_end",
            request_id=request_id or None,
            user_id=user_id,
            diagram_id=None,
            route="/api/iac/scan",
            status=200,
            duration_ms=_elapsed_ms(started),
            checkov_ms=_elapsed_ms(started),
            exit_code=0,
        )
        return report

    def rewrite(
        self,
        user_id: int,
        diagram_id: int,
        report_id: str | None = None,
        *,
        request_id: str = "",
    ) -> tuple[RewriteResult, Draft]:
        started = time.perf_counter()
        self._activate(user_id, diagram_id)
        draft = self._succeeded_draft(user_id, diagram_id)
        if draft is None:
            raise IacGateError("missing_draft", "A succeeded draft is required.")
        report = self._select_report(user_id, diagram_id, report_id)
        self._note_agent("secrets/rewrite", user_id, diagram_id, len(draft.files), request_id)
        redaction = redact_files(draft.files)
        if slot_nbytes(redaction.files) > SLOT_LIMIT_BYTES:
            raise IacGateError("slot_too_large", "Draft exceeds the 16 MiB slot limit.")
        updated = Draft(
            draft_id=draft.draft_id,
            diagram_id=draft.diagram_id,
            user_id=draft.user_id,
            status="succeeded",
            files=list(redaction.files),
            created_at=draft.created_at,
        )
        result = RewriteResult(
            rewrite_id=str(uuid.uuid4()),
            draft_id=draft.draft_id,
            report_id=report.report_id,
            status="succeeded",
            rewritten_paths=list(redaction.rewritten_paths),
            created_at=_now(),
        )
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void or slot.draft is None:
                raise IacGateError("diagram_mismatch", "diagram_id changed during rewrite.")
            if slot.draft.draft_id != draft.draft_id:
                raise IacGateError("diagram_mismatch", "diagram_id changed during rewrite.")
            slot.draft = updated
            slot.rewrites.append(result)
        log_event(
            "request_end",
            request_id=request_id or None,
            user_id=user_id,
            diagram_id=diagram_id,
            route="/api/iac/secrets/rewrite",
            status=200,
            duration_ms=_elapsed_ms(started),
        )
        return result, updated

    def download(self, user_id: int, diagram_id: int) -> bytes:
        self._activate(user_id, diagram_id)
        draft = self._succeeded_draft(user_id, diagram_id)
        if draft is None:
            raise IacGateError("missing_draft", "A succeeded draft is required.")
        return build_module_zip(draft.files)

    def remember_saved(
        self,
        user_id: int,
        diagram_id: int,
        draft: Draft,
        advice: str | None = None,
        scan_advice: str | None = None,
        scan: ScanReport | None = None,
    ) -> None:
        """Put a database draft into an empty slot so download and scan can see it."""
        self._activate(user_id, diagram_id)
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void:
                slot = _Slot()
                self._slots[(user_id, diagram_id)] = slot
            if slot.draft is not None and slot.draft.status == "succeeded":
                if advice and not slot.advice:
                    slot.advice = advice
                if scan_advice and not slot.scan_advice:
                    slot.scan_advice = scan_advice
                _keep_saved_scan(slot, scan)
                return
            slot.draft = draft
            slot.advice = advice or None
            slot.scan_advice = scan_advice or None
            slot.reports.clear()
            _keep_saved_scan(slot, scan)
            slot.void = False

    def remember_advice(self, user_id: int, diagram_id: int, advice: str | None) -> None:
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void:
                return
            slot.advice = advice or None

    def remember_scan_advice(self, user_id: int, diagram_id: int, advice: str | None) -> None:
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void:
                return
            slot.scan_advice = advice or None

    def snapshot(self, user_id: int, diagram_id: int) -> SessionSnapshot:
        self._activate(user_id, diagram_id)
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            draft = None
            latest_scan = None
            latest_rewrite = None
            advice = None
            scan_advice = None
            if slot is not None and not slot.void:
                if slot.draft is not None and slot.draft.status == "succeeded":
                    draft = slot.draft
                latest_scan = _latest_succeeded(slot.reports)
                latest_rewrite = slot.rewrites[-1] if slot.rewrites else None
                advice = slot.advice or None
                scan_advice = slot.scan_advice or None
        return SessionSnapshot(
            diagram_id=diagram_id,
            draft=draft,
            latest_scan=latest_scan,
            latest_rewrite=latest_rewrite,
            advice=advice,
            scan_advice=scan_advice,
        )

    def _note_agent(self, story, user_id, diagram_id, count, request_id) -> None:
        failure = {
            "generate": "generate_failed",
            "scan": "scan_failed",
            "secrets/rewrite": "rewrite_failed",
        }.get(story, "generate_failed")
        try:
            run_story_agent(
                story,
                {"resource_count": count, "diagram_id": diagram_id},
                invoke=self.agent_invoke,
                request_id=request_id,
                user_id=user_id,
                diagram_id=diagram_id,
            )
        except IacGateError:
            raise
        except Exception as exc:
            raise IacGateError(failure, "The request failed. Retry.") from exc

    def _generate_once(
        self,
        resources: list[Resource],
        timeout_s: float,
        *,
        request_id: str,
        user_id: int,
        diagram_id: int,
        skip_agent: bool = False,
    ) -> list[FileEntry]:
        def _work():
            if not skip_agent:
                run_story_agent(
                    "generate",
                    {"resource_count": len(resources), "diagram_id": diagram_id},
                    invoke=self.agent_invoke,
                    request_id=request_id,
                    user_id=user_id,
                    diagram_id=diagram_id,
                )
            return self.generator(list(resources))

        try:
            files = call_with_deadline(_work, timeout_s)
        except TimeoutError as exc:
            raise IacGateError(
                "generate_timeout",
                "Generate timed out. Retry the request.",
            ) from exc
        except IacGateError:
            raise
        except Exception as exc:
            raise IacGateError(
                "generate_failed",
                "Generate failed. Retry the request.",
            ) from exc
        return files

    def _commit_draft(
        self,
        user_id: int,
        diagram_id: int,
        epoch: int,
        files: list[FileEntry],
    ) -> Draft:
        paths = {entry.path for entry in files}
        if not set(REQUIRED_PATHS) <= paths:
            raise IacGateError("generate_failed", "Generate failed. Retry the request.")
        for entry in files:
            if not is_safe_relative_path(entry.path):
                raise IacGateError("generate_failed", "Generate failed. Retry the request.")
        if slot_nbytes(files) > SLOT_LIMIT_BYTES:
            raise IacGateError("slot_too_large", "Draft exceeds the 16 MiB slot limit.")
        draft = Draft(
            draft_id=str(uuid.uuid4()),
            diagram_id=diagram_id,
            user_id=user_id,
            status="succeeded",
            files=list(files),
            created_at=_now(),
        )
        with self._lock:
            if self._epoch.get(user_id) != epoch or self._active.get(user_id) != diagram_id:
                raise IacGateError(
                    "diagram_mismatch",
                    "diagram_id changed while generate was in progress.",
                )
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void:
                raise IacGateError(
                    "diagram_mismatch",
                    "diagram_id changed while generate was in progress.",
                )
            for report in slot.reports:
                self._stale.add(report.report_id)
            slot.reports.clear()
            slot.rewrites.clear()
            slot.draft = draft
            slot.advice = None
            slot.scan_advice = None
        return draft

    def _store_report(self, user_id, diagram_id, draft: Draft, outcome) -> ScanReport:
        with self._lock:
            self._seq += 1
            report = ScanReport(
                report_id=str(uuid.uuid4()),
                draft_id=draft.draft_id,
                diagram_id=diagram_id,
                status=outcome.status,
                findings=list(outcome.findings),
                max_severity=outcome.max_severity if outcome.status == "succeeded" else "NONE",
                created_at=_now(),
                seq=self._seq,
                checks=list(outcome.checks),
            )
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void or slot.draft is None:
                raise IacGateError("diagram_mismatch", "diagram_id changed during scan.")
            if slot.draft.draft_id != draft.draft_id:
                raise IacGateError("stale_report_id", "The draft changed before scan finished.")
            slot.reports.append(report)
        return report

    def _select_report(self, user_id: int, diagram_id: int, report_id: str | None) -> ScanReport:
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            reports = list(slot.reports) if slot is not None and not slot.void else []
            stale = set(self._stale)
        succeeded = [report for report in reports if report.status == "succeeded"]
        if report_id is None:
            latest = _latest_succeeded(succeeded)
            if latest is None:
                raise IacGateError(
                    "missing_scan_report",
                    "A succeeded scan report is required.",
                )
            return latest
        if report_id in stale:
            raise IacGateError("stale_report_id", "report_id is no longer valid.")
        match = next((report for report in reports if report.report_id == report_id), None)
        if match is None or match.status != "succeeded":
            raise IacGateError("stale_report_id", "report_id is no longer valid.")
        return match

    def replace_files(self, user_id: int, diagram_id: int, files: list[FileEntry]) -> Draft:
        """Replace the current draft's three .tf files. Prior scans no longer apply."""
        self._activate(user_id, diagram_id)
        if len(files) != len(REQUIRED_PATHS) or {entry.path for entry in files} != set(REQUIRED_PATHS):
            raise IacGateError(
                "invalid_files",
                "Draft files must be main.tf, variables.tf, and outputs.tf.",
            )
        for entry in files:
            if not is_safe_relative_path(entry.path):
                raise IacGateError(
                    "invalid_files",
                    "Draft files must be main.tf, variables.tf, and outputs.tf.",
                )
        if slot_nbytes(files) > SLOT_LIMIT_BYTES:
            raise IacGateError("slot_too_large", "Draft exceeds the 16 MiB slot limit.")
        by_path = {entry.path: entry for entry in files}
        ordered = [by_path[path] for path in REQUIRED_PATHS]
        draft = Draft(
            draft_id=str(uuid.uuid4()),
            diagram_id=diagram_id,
            user_id=user_id,
            status="succeeded",
            files=ordered,
            created_at=_now(),
        )
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void or slot.draft is None or slot.draft.status != "succeeded":
                raise IacGateError("missing_draft", "A succeeded draft is required.")
            for report in slot.reports:
                self._stale.add(report.report_id)
            slot.reports.clear()
            slot.rewrites.clear()
            slot.draft = draft
            slot.scan_advice = None
        return draft

    def _succeeded_draft(self, user_id: int, diagram_id: int) -> Draft | None:
        with self._lock:
            slot = self._slots.get((user_id, diagram_id))
            if slot is None or slot.void or slot.draft is None:
                return None
            if slot.draft.status != "succeeded":
                return None
            return slot.draft

    def _activate(self, user_id: int, diagram_id: int) -> int:
        with self._lock:
            current = self._active.get(user_id)
            if current != diagram_id:
                if current is not None:
                    self._void_slot_locked(user_id, current)
                self._epoch[user_id] = self._epoch.get(user_id, 0) + 1
                self._active[user_id] = diagram_id
            else:
                self._epoch.setdefault(user_id, 1)
            key = (user_id, diagram_id)
            slot = self._slots.get(key)
            if slot is None or slot.void:
                self._slots[key] = _Slot()
            self._touch_lru_locked(user_id, diagram_id)
            return self._epoch[user_id]

    def _void_slot_locked(self, user_id: int, diagram_id: int) -> None:
        slot = self._slots.get((user_id, diagram_id))
        if slot is None:
            return
        for report in slot.reports:
            self._stale.add(report.report_id)
        slot.draft = None
        slot.reports.clear()
        slot.rewrites.clear()
        slot.advice = None
        slot.scan_advice = None
        slot.void = True

    def _touch_lru_locked(self, user_id: int, diagram_id: int) -> None:
        order = self._lru.setdefault(user_id, [])
        if diagram_id in order:
            order.remove(diagram_id)
        order.append(diagram_id)
        while len(order) > MAX_SLOTS_PER_USER:
            evict = order.pop(0)
            if evict == diagram_id:
                order.append(evict)
                break
            self._void_slot_locked(user_id, evict)
            self._slots.pop((user_id, evict), None)


_singleton: IacWorkspaceSession | None = None
_singleton_lock = threading.Lock()


def get_session() -> IacWorkspaceSession:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = IacWorkspaceSession()
        return _singleton


def reset_session() -> IacWorkspaceSession:
    global _singleton
    with _singleton_lock:
        _singleton = IacWorkspaceSession()
        return _singleton


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _keep_saved_scan(slot: _Slot, scan: ScanReport | None) -> None:
    if scan is None or scan.status != "succeeded":
        return
    if slot.draft is None or scan.draft_id != slot.draft.draft_id:
        return
    if _latest_succeeded(slot.reports) is not None:
        return
    slot.reports.append(scan)


def _latest_succeeded(reports: list[ScanReport]) -> ScanReport | None:
    succeeded = [report for report in reports if report.status == "succeeded"]
    if not succeeded:
        return None
    return max(succeeded, key=lambda report: report.seq)
