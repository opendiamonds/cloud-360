"""Pure Checkov result mapping and a stubbable CLI runner.

The mapping functions do not spawn a process. ``default_checkov_runner`` is
the only place that executes the pinned Checkov CLI.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from iac.iac_generate import is_safe_relative_path
from iac.iac_limits import CHECKOV_TIMEOUT_SECONDS, CHECKOV_VERSION
from iac.iac_types import CheckItem, FileEntry, Finding, ScanOutcome

SEVERITY_RANK = {
    "NONE": 0,
    "INFO": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}
ALLOWED_SEVERITIES = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")

Runner = Callable[[list[FileEntry], float], Any]


def max_severity(findings: list[Finding]) -> str:
    if not findings:
        return "NONE"
    return max(findings, key=lambda finding: SEVERITY_RANK[finding.severity]).severity


def checks_from_checkov_payload(payload: Any) -> list[CheckItem]:
    """Map every evaluated Checkov check, failed ones first."""
    items: list[CheckItem] = []
    for status, key in (
        ("failed", "failed_checks"),
        ("passed", "passed_checks"),
        ("skipped", "skipped_checks"),
    ):
        for index, check in enumerate(_named_checks(payload, key)):
            if not isinstance(check, dict):
                raise ValueError("checkov check is not an object")
            resource = check.get("resource")
            items.append(
                CheckItem(
                    id=str(check.get("check_id") or f"CKV_{status}_{index}"),
                    title=str(check.get("check_name") or check.get("check_id") or "check"),
                    status=status,
                    path=_relative_check_path(check.get("file_path") or check.get("repo_file_path")),
                    resource=str(resource) if resource else None,
                )
            )
    return items


def findings_from_checkov_payload(payload: Any) -> list[Finding]:
    """Map Checkov JSON to findings. Unknown severities raise ValueError."""
    checks = _failed_checks(payload)
    findings: list[Finding] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise ValueError("checkov check is not an object")
        severity = _severity_of(check)
        check_id = str(check.get("check_id") or f"CKV_{index}")
        title = str(check.get("check_name") or check.get("check_id") or "finding")
        detail = check.get("guideline") or check.get("description")
        path = _relative_check_path(check.get("file_path") or check.get("repo_file_path"))
        findings.append(
            Finding(
                id=check_id,
                severity=severity,
                title=title,
                detail=str(detail) if detail else None,
                path=path,
            )
        )
    return findings


def run_checkov(
    files: list[FileEntry],
    *,
    runner: Runner,
    timeout_s: float = CHECKOV_TIMEOUT_SECONDS,
) -> ScanOutcome:
    """Run ``runner`` and map the result. Missing CLI or a bad payload fails."""
    try:
        completed = runner(files, timeout_s)
    except FileNotFoundError:
        return ScanOutcome("failed", [], "NONE", "checkov_missing")
    except TimeoutError:
        return ScanOutcome("failed", [], "NONE", "checkov_timeout")
    returncode = getattr(completed, "returncode", 1)
    stdout = getattr(completed, "stdout", "") or ""
    if returncode not in (0, 1):
        return ScanOutcome("failed", [], "NONE", "checkov_exit")
    if not stdout.strip():
        if returncode == 0:
            return ScanOutcome("succeeded", [], "NONE", "")
        return ScanOutcome("failed", [], "NONE", "checkov_empty")
    try:
        payload = json.loads(stdout)
        findings = findings_from_checkov_payload(payload)
        checks = checks_from_checkov_payload(payload)
    except (json.JSONDecodeError, ValueError, KeyError):
        return ScanOutcome("failed", [], "NONE", "checkov_unparsed")
    return ScanOutcome("succeeded", findings, max_severity(findings), "", checks)


def default_checkov_runner(files: list[FileEntry], timeout_s: float):
    """Execute the pinned Checkov CLI. Raises FileNotFoundError when it is absent."""
    import os
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="iac-scan-") as directory:
        for entry in files:
            if not is_safe_relative_path(entry.path):
                raise ValueError("unsafe path")
            target = os.path.join(directory, entry.path)
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(entry.content)
        try:
            return subprocess.run(
                ["checkov", "-d", directory, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("checkov timed out") from exc


def _severity_of(check: dict) -> str:
    raw = check.get("severity")
    if raw is None or raw == "":
        return "INFO"
    severity = str(raw).upper()
    if severity not in SEVERITY_RANK or severity == "NONE":
        raise ValueError(f"unknown severity {severity}")
    return severity


def _relative_check_path(raw: Any) -> str | None:
    if not raw:
        return None
    path = str(raw).replace("\\", "/").lstrip("/")
    if not is_safe_relative_path(path):
        return None
    return path


def _failed_checks(payload: Any) -> list:
    return _named_checks(payload, "failed_checks")


def _named_checks(payload: Any, key: str) -> list:
    if isinstance(payload, list):
        checks: list = []
        for item in payload:
            checks.extend(_named_checks(item, key))
        return checks
    if not isinstance(payload, dict):
        raise ValueError("checkov payload")
    results = payload.get("results")
    if isinstance(results, dict):
        return list(results.get(key) or [])
    if key in payload:
        return list(payload.get(key) or [])
    return []


# Re-exported so image pin and parser stay on one constant.
PINNED_CHECKOV_VERSION = CHECKOV_VERSION
