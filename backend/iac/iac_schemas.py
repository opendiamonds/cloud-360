"""HTTP schemas for /api/iac. Field names follow the contract summary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GateCode = Literal[
    "missing_draft",
    "missing_scan_report",
    "stale_report_id",
    "missing_diagram_id",
    "invalid_diagram",
    "diagram_mismatch",
    "slot_too_large",
    "generate_busy",
    "generate_timeout",
    "generate_failed",
    "scan_failed",
    "rewrite_failed",
    "diagram_empty",
    "diagram_unreadable",
    "invalid_files",
]

Severity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
MaxSeverity = Literal["NONE", "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
RunStatus = Literal["succeeded", "failed"]
CheckStatus = Literal["passed", "failed", "skipped"]


class ErrorBody(BaseModel):
    code: GateCode
    message: str
    reason: str | None = None


class GateErrorModel(BaseModel):
    error: ErrorBody
    request_id: str | None = None


class FileEntryModel(BaseModel):
    path: str
    content: str


class ModuleTreeModel(BaseModel):
    files: list[FileEntryModel]


class DraftSummaryModel(BaseModel):
    draft_id: str
    diagram_id: int
    status: RunStatus
    module_tree: ModuleTreeModel
    created_at: str


class FindingModel(BaseModel):
    id: str
    severity: Severity
    title: str
    detail: str | None = None
    path: str | None = None


class CheckItemModel(BaseModel):
    id: str
    title: str
    status: CheckStatus
    path: str | None = None
    resource: str | None = None


class ScanReportModel(BaseModel):
    report_id: str
    draft_id: str
    diagram_id: int
    status: RunStatus
    findings: list[FindingModel]
    max_severity: MaxSeverity
    created_at: str
    checks: list[CheckItemModel] = Field(default_factory=list)


class RewriteResultModel(BaseModel):
    rewrite_id: str
    draft_id: str
    report_id: str
    status: RunStatus
    rewritten_paths: list[str]
    created_at: str


class GenerateResponseModel(BaseModel):
    draft: DraftSummaryModel


class ScanResponseModel(BaseModel):
    report: ScanReportModel


class RewriteResponseModel(BaseModel):
    rewrite: RewriteResultModel
    draft: DraftSummaryModel


class SessionSnapshotModel(BaseModel):
    diagram_id: int
    draft: DraftSummaryModel | None = None
    latest_scan: ScanReportModel | None = None
    latest_rewrite: RewriteResultModel | None = None
    advice: str | None = None
    scan_advice: str | None = None


ReadinessStatus = Literal["ready", "empty", "unreadable"]


class DiagramReadinessModel(BaseModel):
    diagram_id: int
    title: str
    status: ReadinessStatus
    node_count: int


class ReadinessResponseModel(BaseModel):
    diagrams: list[DiagramReadinessModel]


class SaveDraftResponseModel(BaseModel):
    diagram_id: int
    draft_id: str
    saved_at: str
