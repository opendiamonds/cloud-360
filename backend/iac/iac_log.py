"""Structured logger for the IaC workspace.

Whitelist keys only. HCL, prompts, and JWTs are not log fields.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("cloud360.iac")

LOG_FIELDS = frozenset(
    {
        "request_id",
        "user_id",
        "diagram_id",
        "route",
        "status",
        "error_code",
        "duration_ms",
        "model",
        "llm_ms",
        "token_est",
        "exit_code",
        "checkov_ms",
        "reason",
    }
)
_MAX_VALUE_LEN = 200


def log_event(event: str, **fields: object) -> None:
    """Emit one INFO line. Unknown keys and oversized values are dropped."""
    safe: dict[str, object] = {}
    for key, value in fields.items():
        if key not in LOG_FIELDS or value is None:
            continue
        text = str(value)
        if len(text) > _MAX_VALUE_LEN or _blocked(text):
            continue
        safe[key] = value if isinstance(value, (int, float)) else text
    logger.info("%s %s", event, json.dumps(safe, sort_keys=True, default=str))


def _blocked(text: str) -> bool:
    lowered = text.lower()
    if "bearer " in lowered or lowered.startswith("eyj"):
        return True
    return False
