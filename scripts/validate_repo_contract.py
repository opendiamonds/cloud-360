#!/usr/bin/env python3
"""Validate the Cloud-360 repository contract.

AI-DLC v2 (ADR-0011) keeps workflow artifacts in a per-intent record directory
under ``aidlc/spaces/<space>/intents/<record>/`` instead of the flat
``aidlc-docs/`` root v1 used. The record directory name is minted by the engine
(``<YYMMDD>-<label>``), so the baseline artifacts cannot be pinned by literal
path any more. They are declared record-relative in ``REQUIRED_RECORD_FILES`` /
``REQUIRED_RECORD_TEXT`` and resolved at runtime against whichever record holds
the full baseline set.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Every AI-DLC intent record lives here; a record is identified by its state file.
RECORD_GLOB = "aidlc/spaces/*/intents/*"
RECORD_STATE_FILE = "aidlc-state.md"

# Repo-root-relative files that must exist regardless of the AI-DLC layout.
REQUIRED_FILES = (
    "README.md",
    ".gitignore",
    ".github/workflows/ci.yml",
    "scripts/validate_repo_contract.py",
    "CLAUDE.md",
    # Local development: the only path by which a developer can run every
    # feature outside CI, and the only place the implicit runtime dependencies
    # are written down.
    "LOCAL-DEV.md",
    # Test-case format contract. Tool-agnostic on purpose -- contributors on
    # Cursor or Antigravity never load the AI-DLC knowledge tree, so the
    # contract cannot live only there. tcms_validate.py reads its
    # `required-sections` marker, so this file IS the field list, not a copy.
    "TESTING.md",
    # Environment-configuration separation (local dev vs deploy stack).
    "scripts/validate_env_contract.py",
    "deploy/render-env.sh",
    # AI-DLC v2 entry points and rule surface (ADR-0011).
    ".claude/CLAUDE.md",
    ".claude/skills/aidlc/SKILL.md",
    ".claude/tools/aidlc-version.ts",
    "aidlc/spaces/default/memory/org.md",
    "aidlc/spaces/default/memory/team.md",
    "aidlc/spaces/default/memory/project.md",
    # The tcms plugin's stage (see .claude/README-cloud360.md § 調整 3). It is
    # hand-written but sits under .claude/, so an AI-DLC upgrade's bulk copy of
    # upstream dist/claude/ can remove it. Losing it is silent -- the stage
    # simply stops running and project.md's blocking rule points at a stage that
    # no longer exists. Listing it here turns that into a red CI gate.
    ".claude/aidlc-common/stages/construction/tcms-test-cases.md",
    # The verification gate. Hand-written and under .claude/, so it carries the
    # same upgrade risk as the stage file above.
    ".claude/skills/tcms-verify/SKILL.md",
    # The authoring standard the stage is judged against. Outside .claude/, so
    # an upgrade cannot touch it -- listed because the stage is useless without it.
    "aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md",
    "scripts/tcms_sync.py",
    "scripts/tcms_validate.py",
)

# Baseline artifacts, declared relative to the intent record that carries them.
REQUIRED_RECORD_FILES = (
    RECORD_STATE_FILE,
    "README.md",
    "decisions-log.md",
    "inception/requirements-analysis/cloud-360-srs.md",
    "inception/application-design/system-architecture.md",
    "inception/user-stories/stories.md",
    "inception/user-stories/personas.md",
    "inception/decisions/0001-repo-scope.md",
    "inception/decisions/0002-agent-routing-layer.md",
    "inception/decisions/0003-web-based-experience.md",
    "inception/decisions/0004-mcp-skill-management.md",
    "inception/decisions/0005-bilingual-documentation.md",
    "inception/decisions/0006-adopt-aidlc-framework.md",
    "inception/decisions/0009-traditional-chinese-docs.md",
    "inception/decisions/0011-adopt-aidlc-v2.md",
)

REQUIRED_TEXT = {
    "README.md": (
        "Cloud-360",
        "AWS",
        "GCP",
        "Azure",
        "draw.io",
        "Mobile Web",
        "Cloud Security Posture",
        "human approval gate",
        "MCP & Skill Management",
        # U-11（intent 260822-gh-projects-sync）：README 的需求正本指路段落。
        # 在此登錄之前，刪掉整段不會讓任何檢查變紅——本段是該 intent 對外唯一的
        # 「需求正本在哪」宣告，沒有斷言等於沒有交付。
        "Requirements Source",
        "https://github.com/users/opendiamonds/projects/16",
    ),
    "CLAUDE.md": (
        "AIDLC",
        ".claude/skills/aidlc/SKILL.md",
        "aidlc/spaces/<active-space>/memory/",
        "Standing Constraints",
        "validate_repo_contract.py",
    ),
    # AI-DLC v2 memory layers — the project rule surface (ADR-0011). org.md
    # stays upstream/English; team.md and project.md carry the Cloud-360 rules
    # and are Traditional Chinese.
    "aidlc/spaces/default/memory/team.md": (
        "<uploader>/<type>/<slug>",
        "feat",
        "fix",
        "docs",
        "chore",
        "refactor",
        "test",
        "danniel",
        "功能",
        "修正",
        "<record>/decisions-log.md",
    ),
    "aidlc/spaces/default/memory/project.md": (
        "property-based",
        "schema_rbac.sql",
        "DEPLOY.md",
        "validate_repo_contract.py",
        "Scope Overrides",
    ),
}

REQUIRED_RECORD_TEXT = {
    "inception/requirements-analysis/cloud-360-srs.md": (
        "AI Multi-Cloud Operations",
        "Cloud Security Posture & Policy Advisory",
        "Mobile Web",
        "MCP servers",
        "Terraform / OpenTofu",
        "MCP & Skill Management",
    ),
    "inception/application-design/system-architecture.md": (
        "Agent Routing Layer",
        "Cloud Operation Integration Layer",
        "draw.io",
        "Security Policy Advisor Agent",
        "MCP / Skill Registry",
    ),
    "inception/user-stories/stories.md": (
        "Architecture Design",
        "Cost Estimation & FinOps",
        "Cloud Security Posture",
        "Mobile",
    ),
    "inception/user-stories/personas.md": (
        "Cloud Architect",
        "SRE",
        "Platform Engineer",
        "Security Reviewer",
    ),
    "inception/decisions/0001-repo-scope.md": (
        "Spec-Driven Development",
        "feature/cloud_architecture",
        "read-only",
    ),
    "inception/decisions/0002-agent-routing-layer.md": (
        "Routing Agent",
        "Security Policy Advisor Agent",
        "human approval",
    ),
    "inception/decisions/0003-web-based-experience.md": (
        "Web-first",
        "Mobile Web",
        "Native iOS app",
        "Native Android app",
    ),
    "inception/decisions/0004-mcp-skill-management.md": (
        "MCP and Skill Management",
        "Permission and Risk Classification",
        "Agent Routing Integration",
        "Health Checks",
    ),
    "inception/decisions/0005-bilingual-documentation.md": (
        "Bilingual Documentation",
    ),
    # ADR-0006 is a historical record: it still describes the v1 extension
    # mechanism verbatim, which is correct for a decision made under v1. The
    # contract only pins terms that are stable regardless of framework version.
    "inception/decisions/0006-adopt-aidlc-framework.md": (
        "Adopt AIDLC",
        "AIDLC v0.1.8",
        "Hybrid",
    ),
    "inception/decisions/0011-adopt-aidlc-v2.md": (
        "AI-DLC v2",
        "aidlc/spaces",
        "Alternatives",
    ),
    RECORD_STATE_FILE: (
        "Project Type",
        "Brownfield",
        "State Version",
        "Standing Constraints",
        "Security baseline",
        "Property-based testing",
    ),
    "README.md": (
        "AI-DLC",
    ),
    "decisions-log.md": (
        "Project Decisions Log",
    ),
}

FORBIDDEN_NEW_PATH_PARTS = {
    "prod",
    "production",
    "secrets",
}

FORBIDDEN_CONTENT_PATTERNS = (
    "BEGIN " + "PRIVATE KEY",
    "AWS_" + "SECRET_ACCESS_KEY",
    "AZURE_" + "CLIENT_SECRET=",
    "GOOGLE_" + "APPLICATION_CREDENTIALS=",
)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def git_ls_files() -> list[str]:
    """Every file tracked by git, as repo-root-relative paths.

    ``-z`` returns NUL-separated, unquoted paths. Without it git applies
    ``core.quotePath`` and escapes non-ASCII names, which would corrupt the
    path parts this contract compares against.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [path for path in result.stdout.split("\0") if path]


def all_record_roots() -> list[Path]:
    """Every AI-DLC intent record in the workspace, in stable order."""
    return sorted(
        path
        for path in ROOT.glob(RECORD_GLOB)
        if (path / RECORD_STATE_FILE).is_file()
    )


def resolve_baseline_record() -> tuple[Path | None, list[str]]:
    """Locate the record carrying the Cloud-360 baseline artifacts.

    Records born for later intents legitimately lack the baseline set, so the
    contract is satisfied when ANY record holds all of it. On failure we report
    the closest candidate's gaps rather than every record's.
    """
    records = all_record_roots()
    if not records:
        return None, [f"no AI-DLC intent record found under {RECORD_GLOB}"]

    closest: Path | None = None
    closest_missing: list[str] | None = None
    for record in records:
        missing = [rel for rel in REQUIRED_RECORD_FILES if not (record / rel).is_file()]
        if not missing:
            return record, []
        if closest_missing is None or len(missing) < len(closest_missing):
            closest, closest_missing = record, missing

    assert closest is not None and closest_missing is not None
    prefix = closest.relative_to(ROOT).as_posix()
    return None, [f"{prefix}/{rel}" for rel in closest_missing]


# Resolved once; every check reads the same record.
BASELINE_RECORD, BASELINE_MISSING = resolve_baseline_record()


def validate_required_files() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        return fail("Missing required contract files: " + ", ".join(missing))
    if BASELINE_RECORD is None:
        return fail(
            "No AI-DLC intent record holds the Cloud-360 baseline artifacts; "
            "closest candidate is missing: " + ", ".join(BASELINE_MISSING)
        )
    # The pre-v2 flat audit.md is a per-clone shard set after migration; require
    # at least one shard so the decision history stays in the contract.
    shards = sorted((BASELINE_RECORD / "audit").glob("*.md"))
    if not shards:
        prefix = BASELINE_RECORD.relative_to(ROOT).as_posix()
        return fail(f"No audit shard found under {prefix}/audit/*.md")
    return 0


def contract_files() -> list[tuple[str, Path]]:
    """Every file the contract governs, as (display path, absolute path)."""
    files = [(rel, ROOT / rel) for rel in REQUIRED_FILES]
    if BASELINE_RECORD is not None:
        prefix = BASELINE_RECORD.relative_to(ROOT).as_posix()
        files += [
            (f"{prefix}/{rel}", BASELINE_RECORD / rel) for rel in REQUIRED_RECORD_FILES
        ]
        files += [
            (path.relative_to(ROOT).as_posix(), path)
            for path in sorted((BASELINE_RECORD / "audit").glob("*.md"))
        ]
    return files


def validate_required_text() -> int:
    violations: list[str] = []

    checks: list[tuple[str, Path, tuple[str, ...]]] = [
        (rel, ROOT / rel, terms) for rel, terms in REQUIRED_TEXT.items()
    ]
    if BASELINE_RECORD is not None:
        prefix = BASELINE_RECORD.relative_to(ROOT).as_posix()
        checks += [
            (f"{prefix}/{rel}", BASELINE_RECORD / rel, terms)
            for rel, terms in REQUIRED_RECORD_TEXT.items()
        ]

    for display, path, required_terms in checks:
        text = path.read_text(encoding="utf-8")
        for term in required_terms:
            if term not in text:
                violations.append(f"{display} missing {term!r}")
    if violations:
        return fail("Required contract text missing: " + "; ".join(violations))
    return 0


def validate_docs_traditional_chinese() -> int:
    """AIDLC docs are Traditional-Chinese-only (see ADR-0009). Reject any leftover
    English-version heading so retrofitted docs stay single-language. Scans every
    intent record, not just the baseline one — the rule covers all AI-DLC output."""
    violations: list[str] = []
    for record in all_record_roots():
        for path in sorted(record.rglob("*.md")):
            rel_path = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(?m)^##\s+English Version", text):
                violations.append(rel_path)
    if violations:
        return fail(
            "Docs are Traditional-Chinese-only; remove the English section from: "
            + ", ".join(violations)
        )
    return 0


def validate_no_production_config_added() -> int:
    """Reject any tracked file whose path carries a forbidden part.

    This scans EVERY tracked file (``git ls-files``), deliberately NOT a diff.
    Do not "optimise" it back to a diff base: CI checks out a clean tree, so
    ``git diff`` and ``git diff --cached`` are both empty there, the loop never
    runs, and the check passes unconditionally on every PR. It only ever fired
    on a dirty local working tree, which made the rule's claim ("CI blocks it")
    stronger than the mechanism (see issue #509). A whole-repo scan needs no
    base ref, so it behaves identically in CI, on a shallow clone, and locally.

    Matching stays part-exact via ``Path(path).parts`` rather than substring:
    ``aidlc-product-agent.md`` contains "prod" without being a "prod" path
    part, and 10 such files legitimately exist in this repo.
    """
    violations: list[str] = []

    for path in git_ls_files():
        parts = {part.lower() for part in Path(path).parts}
        if parts & FORBIDDEN_NEW_PATH_PARTS:
            violations.append(path)

    if violations:
        return fail(
            "Production/secret-scoped paths are out of scope for this contract: "
            + ", ".join(sorted(violations))
        )
    return 0


def validate_no_obvious_secrets() -> int:
    violations: list[str] = []
    for display, path in contract_files():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_CONTENT_PATTERNS:
            if pattern in text:
                violations.append(f"{display}: {pattern}")
    if violations:
        return fail("Forbidden secret-like content found: " + ", ".join(violations))
    return 0


def main() -> int:
    checks = (
        validate_required_files,
        validate_required_text,
        validate_docs_traditional_chinese,
        validate_no_production_config_added,
        validate_no_obvious_secrets,
    )
    for check in checks:
        result = check()
        if result != 0:
            return result

    print("Cloud-360 repository contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
