"""Convert AWS Price List units to hourly USD for C1 calculator."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

HOURS_PER_MONTH_LIST = Decimal("730")


def normalize_to_hourly(
    unit: str,
    price_usd: Decimal,
    *,
    assumed_quantity: Decimal = Decimal("1"),
) -> Optional[Decimal]:
    """Map AWS list price + unit to an hourly rate used by ``line_subtotal``."""
    if not price_usd.is_finite() or price_usd < 0:
        return None
    qty = assumed_quantity if assumed_quantity > 0 else Decimal("1")
    u = (unit or "").strip()

    if u in (
        "Hrs",
        "hours",
        "Hours",
        "DPU-Hour",
        "M-DPU-Hour",
        "Node-hour",
    ):
        return price_usd * qty
    # 月費／計量單位 → 以 assumed_quantity 換算成等效 hourly（730h/月）
    if u in (
        "Mo",
        "Month",
        "HostedZone",
        "GB-Mo",
        "GB",
        "Terabytes",
        "Request",
        "Requests",
        "Metrics",
        "Alarms",
        "Lambda-GB-Second",
    ):
        return (price_usd * qty) / HOURS_PER_MONTH_LIST
    return None
