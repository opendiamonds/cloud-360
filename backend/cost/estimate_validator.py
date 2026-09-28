"""Mechanical checks on ParseResult — pure functions (FR4 / BR4)."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Literal, TypedDict

from cost.estimate_parser import LineItem, ParseResult

TOLERANCE_PERCENT = Decimal("0.5")
TOLERANCE_RATIO = Decimal("0.005")


class TotalReconcileOutcome(TypedDict, total=False):
    attempted: bool
    withinTolerance: bool | None
    skippedReason: str | None
    tolerancePercent: float


class MechanicalCheckResult(TypedDict):
    currencyConsistent: bool
    currencyOffenders: list[int]
    currencyTie: bool
    quantityPositive: bool
    quantityOffenders: list[int]
    totalReconciled: TotalReconcileOutcome


def _parsed_lines(lines: list[LineItem]) -> list[LineItem]:
    return [line for line in lines if line.get("parseStatus") == "parsed"]


def _currency_check(lines: list[LineItem]) -> tuple[bool, list[int], bool]:
    parsed = _parsed_lines(lines)
    currencies = [
        (line["ordinal"], str(line["currency"]).strip())
        for line in parsed
        if line.get("currency")
    ]
    if not currencies:
        return True, [], False

    counts: Counter[str] = Counter(c for _, c in currencies)
    max_count = max(counts.values())
    leaders = sorted(c for c, n in counts.items() if n == max_count)
    tie = len(leaders) > 1
    majority = leaders[0]
    offenders = [ord_ for ord_, c in currencies if c != majority]
    return len(offenders) == 0, offenders, tie


def _quantity_check(lines: list[LineItem]) -> tuple[bool, list[int]]:
    offenders: list[int] = []
    for line in _parsed_lines(lines):
        qty = line.get("quantity")
        if qty is not None and qty < 0:
            offenders.append(line["ordinal"])
    return len(offenders) == 0, offenders


def _reconcile(result: ParseResult) -> TotalReconcileOutcome:
    lines = result["lines"]
    unidentifiable = [
        line for line in lines if line.get("parseStatus") == "unidentifiable"
    ]
    if unidentifiable:
        return {
            "attempted": False,
            "withinTolerance": None,
            "skippedReason": f"skipped: {len(unidentifiable)} unidentifiable line(s)",
            "tolerancePercent": float(TOLERANCE_PERCENT),
        }

    stated = result["totals"].get("statedTotal")
    if stated is None:
        return {
            "attempted": False,
            "withinTolerance": None,
            "skippedReason": "skipped: no stated total",
            "tolerancePercent": float(TOLERANCE_PERCENT),
        }

    amounts = [
        Decimal(str(line["amount"]))
        for line in _parsed_lines(lines)
        if line.get("amount") is not None
    ]
    total = sum(amounts, Decimal("0"))
    stated_dec = Decimal(str(stated))

    if stated_dec == 0:
        within = total == 0
    else:
        within = abs(total - stated_dec) / abs(stated_dec) <= TOLERANCE_RATIO

    return {
        "attempted": True,
        "withinTolerance": within,
        "skippedReason": None,
        "tolerancePercent": float(TOLERANCE_PERCENT),
    }


def validate(parse_result: ParseResult) -> MechanicalCheckResult:
    """Run BR4.1–BR4.4 mechanical checks (deterministic)."""
    if not isinstance(parse_result, dict) or "lines" not in parse_result:
        raise ValueError("parse_result must be a ParseResult mapping")

    currency_ok, currency_offenders, currency_tie = _currency_check(
        parse_result["lines"]
    )
    qty_ok, qty_offenders = _quantity_check(parse_result["lines"])
    return {
        "currencyConsistent": currency_ok,
        "currencyOffenders": currency_offenders,
        "currencyTie": currency_tie,
        "quantityPositive": qty_ok,
        "quantityOffenders": qty_offenders,
        "totalReconciled": _reconcile(parse_result),
    }
