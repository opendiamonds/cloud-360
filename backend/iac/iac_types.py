"""Value types for the IaC workspace. No HTTP, database, or network imports."""

from __future__ import annotations

from dataclasses import dataclass, field


class IacGateError(Exception):
    """Domain gate failure. The router maps ``code`` to an HTTP status."""

    def __init__(self, code: str, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.reason = reason


@dataclass(frozen=True)
class Resource:
    name: str
    cloud: str
    kind: str


@dataclass(frozen=True)
class FileEntry:
    path: str
    content: str


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    title: str
    detail: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class CheckItem:
    """One Checkov check that ran. ``status`` is passed, failed, or skipped."""

    id: str
    title: str
    status: str
    path: str | None = None
    resource: str | None = None


@dataclass
class Draft:
    draft_id: str
    diagram_id: int
    user_id: int
    status: str
    files: list[FileEntry]
    created_at: str


@dataclass
class ScanReport:
    report_id: str
    draft_id: str
    diagram_id: int
    status: str
    findings: list[Finding]
    max_severity: str
    created_at: str
    seq: int = 0
    checks: list[CheckItem] = field(default_factory=list)


@dataclass
class RewriteResult:
    rewrite_id: str
    draft_id: str
    report_id: str
    status: str
    rewritten_paths: list[str]
    created_at: str


@dataclass
class SessionSnapshot:
    diagram_id: int
    draft: Draft | None = None
    latest_scan: ScanReport | None = None
    latest_rewrite: RewriteResult | None = None
    advice: str | None = None
    scan_advice: str | None = None


@dataclass
class Redaction:
    files: list[FileEntry]
    rewritten_paths: list[str] = field(default_factory=list)


@dataclass
class ScanOutcome:
    status: str
    findings: list[Finding]
    max_severity: str
    message: str = ""
    checks: list[CheckItem] = field(default_factory=list)
