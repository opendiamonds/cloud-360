"""Tests for estimate_validator (FR4 / BR4 / NFR4.1)."""

from __future__ import annotations

import unittest
from decimal import Decimal

from hypothesis import given, settings, strategies as st

from cost.estimate_parser import LineItem, ParseResult
from cost.estimate_validator import validate


def _result(lines: list[LineItem], stated: float | None = None) -> ParseResult:
    return {
        "detection": {"status": "resolved", "cloud": "aws"},
        "lines": lines,
        "totals": {"statedTotal": stated, "currency": "USD"},
        "sourceFormat": "csv",
    }


def _line(
    ordinal: int,
    *,
    qty: float | None,
    amount: float | None,
    currency: str | None = "USD",
    status: str = "parsed",
) -> LineItem:
    return {
        "ordinal": ordinal,
        "itemName": f"item-{ordinal}",
        "spec": "",
        "quantity": qty,
        "amount": amount,
        "currency": currency,
        "parseStatus": status,  # type: ignore[typeddict-item]
        "rawText": f"row-{ordinal}",
    }


class TestEstimateValidator(unittest.TestCase):
    def test_currency_majority_and_offenders(self):
        result = _result(
            [
                _line(0, qty=1, amount=1, currency="USD"),
                _line(1, qty=1, amount=1, currency="USD"),
                _line(2, qty=1, amount=1, currency="EUR"),
            ],
            stated=3.0,
        )
        check = validate(result)
        self.assertFalse(check["currencyConsistent"])
        self.assertEqual(check["currencyOffenders"], [2])
        self.assertFalse(check["currencyTie"])

    def test_negative_quantity_offenders(self):
        result = _result(
            [
                _line(0, qty=-1, amount=5, currency="USD"),
                _line(1, qty=0, amount=1, currency="USD"),
            ],
            stated=6.0,
        )
        check = validate(result)
        self.assertFalse(check["quantityPositive"])
        self.assertEqual(check["quantityOffenders"], [0])

    def test_skip_reconcile_when_unidentifiable(self):
        result = _result(
            [
                _line(0, qty=1, amount=1, currency="USD"),
                _line(1, qty=None, amount=None, status="unidentifiable"),
            ],
            stated=1.0,
        )
        check = validate(result)
        self.assertFalse(check["totalReconciled"]["attempted"])
        self.assertIn("unidentifiable", check["totalReconciled"]["skippedReason"] or "")

    def test_reconcile_within_tolerance(self):
        result = _result(
            [
                _line(0, qty=1, amount=100.0, currency="USD"),
                _line(1, qty=1, amount=0.4, currency="USD"),
            ],
            stated=100.0,
        )
        # |100.4 - 100| / 100 = 0.4% <= 0.5%
        check = validate(result)
        self.assertTrue(check["totalReconciled"]["attempted"])
        self.assertTrue(check["totalReconciled"]["withinTolerance"])

    def test_reconcile_outside_tolerance(self):
        result = _result(
            [_line(0, qty=1, amount=110.0, currency="USD")],
            stated=100.0,
        )
        check = validate(result)
        self.assertTrue(check["totalReconciled"]["attempted"])
        self.assertFalse(check["totalReconciled"]["withinTolerance"])


class TestEstimateValidatorProperties(unittest.TestCase):
    @given(
        st.lists(
            st.decimals(
                min_value=0, max_value=1000, places=2, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=8,
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_reconcile_deterministic(self, amounts):
        lines = [
            _line(i, qty=1, amount=float(a), currency="USD")
            for i, a in enumerate(amounts)
        ]
        stated = float(sum((Decimal(str(a)) for a in amounts), Decimal("0")))
        result = _result(lines, stated=stated)
        a = validate(result)
        b = validate(result)
        self.assertEqual(a, b)
        self.assertTrue(a["totalReconciled"]["attempted"])
        self.assertTrue(a["totalReconciled"]["withinTolerance"])


if __name__ == "__main__":
    unittest.main()
