#!/usr/bin/env python3
"""Fail if estimate parser modules import I/O layers (FR2.3 / FR9.6 / NFR6.1)."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COST_DIR = ROOT / "backend" / "cost"

# Primary modules plus reader helpers that parse() imports directly.
SEED_TARGETS = (
    COST_DIR / "estimate_parser.py",
    COST_DIR / "estimate_validator.py",
    COST_DIR / "estimate_readers.py",
)

FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(?:httpx|requests|sqlalchemy|fastapi)\b",
    re.MULTILINE,
)


def _local_cost_imports(path: Path) -> set[Path]:
    """Return same-package modules imported by ``path`` (relative / cost.*)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    found: set[Path] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # from cost.estimate_readers import ...  OR  from .estimate_readers import
            if node.module.startswith("cost."):
                rel = node.module[len("cost.") :].replace(".", "/") + ".py"
                candidate = COST_DIR / rel
                if candidate.is_file():
                    found.add(candidate)
            elif node.level and node.module:
                candidate = (path.parent / f"{node.module.replace('.', '/')}.py").resolve()
                try:
                    candidate.relative_to(COST_DIR.resolve())
                except ValueError:
                    continue
                if candidate.is_file():
                    found.add(candidate)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("cost."):
                    rel = alias.name[len("cost.") :].replace(".", "/") + ".py"
                    candidate = COST_DIR / rel
                    if candidate.is_file():
                        found.add(candidate)
    return found


def collect_targets() -> list[Path]:
    seen: set[Path] = set()
    queue = [p.resolve() for p in SEED_TARGETS]
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            for dep in _local_cost_imports(path):
                if dep not in seen:
                    queue.append(dep)
    return sorted(seen)


def main() -> int:
    targets = collect_targets()
    missing = [p for p in SEED_TARGETS if not p.is_file()]
    if missing:
        for path in missing:
            print(f"ERROR: missing {path.relative_to(ROOT)}", file=sys.stderr)
        return 1

    failed = False
    for path in targets:
        text = path.read_text(encoding="utf-8")
        hits = [m.group(0).strip() for m in FORBIDDEN.finditer(text)]
        if hits:
            failed = True
            print(
                f"ERROR: forbidden imports in {path.relative_to(ROOT)}:",
                file=sys.stderr,
            )
            for line in hits:
                print(f"  - {line}", file=sys.stderr)

    if failed:
        return 1

    for path in targets:
        print(f"OK: {path.relative_to(ROOT)} has no forbidden I/O imports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
