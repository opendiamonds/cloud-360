"""Workload / budget context for cost advice (sent with estimate upload)."""

from __future__ import annotations

import json
from typing import Any

# Keys accepted from the upload form / API. Unknown keys are dropped.
ALLOWED_KEYS = frozenset(
    {
        "system_description",
        "information_requirements",
        "monthly_budget",
        "budget_currency",
        "cost_constraints",
        "monthly_egress_gb",
        "peak_bandwidth_mbps",
        "cross_region_traffic",
        "monthly_active_users",
        "concurrent_users",
        "api_requests_per_month",
        "storage_hot_gb",
        "storage_backup_gb",
        "availability_sla",
        "primary_regions",
        "environment",
        "growth_pct_year",
        "workload_pattern",
    }
)

_NUMERIC_KEYS = frozenset(
    {
        "monthly_budget",
        "monthly_egress_gb",
        "peak_bandwidth_mbps",
        "monthly_active_users",
        "concurrent_users",
        "api_requests_per_month",
        "storage_hot_gb",
        "storage_backup_gb",
        "growth_pct_year",
    }
)

_MAX_TEXT = 4000
_MAX_JSON_CHARS = 24_000


def normalize_workload_context(raw: str | dict[str, Any] | None) -> dict[str, Any] | None:
    """Parse and sanitize workload context. Returns None if empty."""
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if len(text) > _MAX_JSON_CHARS:
            text = text[:_MAX_JSON_CHARS]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw, dict):
        data = raw
    else:
        return None
    if not isinstance(data, dict):
        return None

    out: dict[str, Any] = {}
    for key, value in data.items():
        if key not in ALLOWED_KEYS:
            continue
        if value is None:
            continue
        if key in _NUMERIC_KEYS:
            try:
                num = float(value)
            except (TypeError, ValueError):
                continue
            if num < 0 or num != num:  # NaN
                continue
            out[key] = num
            continue
        text = str(value).strip()
        if not text:
            continue
        out[key] = text[:_MAX_TEXT]
    return out or None


def dumps_workload_context(ctx: dict[str, Any] | None) -> str | None:
    if not ctx:
        return None
    return json.dumps(ctx, ensure_ascii=False)


def loads_workload_context(raw: str | None) -> dict[str, Any] | None:
    if not raw or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return normalize_workload_context(data)
