#!/usr/bin/env python3
"""Fail if PricingLookup boundaries are violated (BR5.7–5.8 / NFR7.1).

1. Estimate intake write-path modules must not import pricing_client / pricing_sdk.
2. backend/ Python outside the pricing_* survival set must not hard-code
   allowlisted catalog-price hosts (direct Pricing API calls).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
COST = BACKEND / "cost"

INTAKE_WRITE_MODULES = (
    COST / "estimate_intake_router.py",
    COST / "estimate_intake_service.py",
    COST / "estimate_access.py",
    COST / "estimate_audit.py",
)

FORBIDDEN_PRICING_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(?:cost\.)?(?:pricing_client|pricing_sdk)\b"
    r"|^\s*from\s+cost\s+import\s+.*\b(?:pricing_client|pricing_sdk)\b",
    re.MULTILINE,
)

ALLOWLIST_HOSTS = (
    "pricing.us-east-1.amazonaws.com",
    "cloudbilling.googleapis.com",
    "prices.azure.com",
)

# Modules allowed to mention / call catalog-price hosts.
SURVIVAL_RELATIVE = {
    "cost/pricing_client.py",
    "cost/pricing_sdk.py",
    "cost/pricing_gcp.py",
    "cost/pricing_azure.py",
    "cost/pricing_offer_parser.py",
    "cost/pricing_query_parser.py",
    "cost/pricing_units.py",
    "cost/config.py",
    "cost/sku_catalog.py",
}


def _rel_backend(path: Path) -> str:
    return path.resolve().relative_to(BACKEND.resolve()).as_posix()


def check_intake_imports() -> list[str]:
    errors: list[str] = []
    for path in INTAKE_WRITE_MODULES:
        if not path.is_file():
            errors.append(f"missing intake module: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_PRICING_IMPORT.search(text):
            errors.append(
                f"{path.relative_to(ROOT)}: must not import pricing_client/pricing_sdk (AH-6)"
            )
        # AST pass for `from cost import pricing_client as x` variants
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: syntax error ({exc})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("cost.pricing_client", "cost.pricing_sdk") or alias.name.endswith(
                        ".pricing_client"
                    ) or alias.name.endswith(".pricing_sdk"):
                        errors.append(
                            f"{path.relative_to(ROOT)}: forbidden import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in ("cost.pricing_client", "cost.pricing_sdk", "pricing_client", "pricing_sdk"):
                    errors.append(
                        f"{path.relative_to(ROOT)}: forbidden from-import {mod}"
                    )
                if mod == "cost":
                    for alias in node.names:
                        if alias.name in ("pricing_client", "pricing_sdk"):
                            errors.append(
                                f"{path.relative_to(ROOT)}: forbidden from cost import {alias.name}"
                            )
    return errors


def check_host_literals() -> list[str]:
    errors: list[str] = []
    for path in BACKEND.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = _rel_backend(path)
        if rel in SURVIVAL_RELATIVE:
            continue
        # tests may assert allowlist hosts
        if rel.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for host in ALLOWLIST_HOSTS:
            if host in text:
                errors.append(
                    f"{rel}: mentions allowlist host {host!r} outside pricing survival set"
                )
    return errors


def main() -> int:
    errors = check_intake_imports() + check_host_literals()
    if errors:
        print("ERROR: pricing-lookup boundary violations:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        "OK: pricing-lookup boundary "
        f"(intake={len(INTAKE_WRITE_MODULES)} modules; survival={len(SURVIVAL_RELATIVE)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
