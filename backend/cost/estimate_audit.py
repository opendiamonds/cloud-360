"""Event-level audit for estimate intake (BR2.12 / FR8).

Never log amounts, raw line text, or file bytes.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from models import EstimateAuditEvent

logger = logging.getLogger("cloud360.estimate_audit")

ALLOWED_EVENT_TYPES = frozenset(
    {
        "upload",
        "share_replace",
        "delete",
        "advice_enqueue",
        "advice_enqueue_failed",
        "save",
    }
)


def write_audit_event(
    db: Session,
    *,
    actor_user_id: int,
    estimate_set_id: int,
    event_type: str,
    cloud: str | None = None,
    parsed_line_count: int | None = None,
    unparsed_line_count: int | None = None,
) -> EstimateAuditEvent:
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported audit event_type: {event_type}")
    event = EstimateAuditEvent(
        actor_user_id=actor_user_id,
        estimate_set_id=estimate_set_id,
        event_type=event_type,
        cloud=cloud,
        parsed_line_count=parsed_line_count,
        unparsed_line_count=unparsed_line_count,
    )
    db.add(event)
    logger.info(
        "estimate_audit event=%s set_id=%s actor=%s cloud=%s parsed=%s unparsed=%s",
        event_type,
        estimate_set_id,
        actor_user_id,
        cloud,
        parsed_line_count,
        unparsed_line_count,
    )
    return event


def safe_log_extra(**kwargs: Any) -> dict[str, Any]:
    """Strip forbidden keys from log extras (defense in depth)."""
    banned = {
        "amount",
        "amounts",
        "raw_text",
        "rawText",
        "file_bytes",
        "content",
        "password",
        "token",
    }
    return {k: v for k, v in kwargs.items() if k not in banned}
