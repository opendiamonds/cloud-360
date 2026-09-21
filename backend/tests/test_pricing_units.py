"""Unit tests for pricing unit normalization."""

import unittest
from decimal import Decimal

from cost.pricing_units import normalize_to_hourly


class TestPricingUnits(unittest.TestCase):
    def test_hours(self):
        self.assertEqual(normalize_to_hourly("Hrs", Decimal("0.01")), Decimal("0.01"))

    def test_gb_month_with_quantity(self):
        hourly = normalize_to_hourly("GB-Mo", Decimal("0.30"), assumed_quantity=Decimal("100"))
        self.assertEqual(hourly, Decimal("0.30") * Decimal("100") / Decimal("730"))

    def test_hosted_zone(self):
        hourly = normalize_to_hourly("HostedZone", Decimal("0.50"))
        self.assertEqual(hourly, Decimal("0.50") / Decimal("730"))

    def test_requests_assumed_quantity(self):
        hourly = normalize_to_hourly(
            "Requests", Decimal("0.0000002"), assumed_quantity=Decimal("1000000")
        )
        self.assertEqual(hourly, Decimal("0.0000002") * Decimal("1000000") / Decimal("730"))

    def test_metrics_assumed_quantity(self):
        hourly = normalize_to_hourly(
            "Metrics", Decimal("0.10"), assumed_quantity=Decimal("10")
        )
        self.assertEqual(hourly, Decimal("0.10") * Decimal("10") / Decimal("730"))

    def test_dpu_hour_like_hrs(self):
        self.assertEqual(
            normalize_to_hourly("DPU-Hour", Decimal("0.44")), Decimal("0.44")
        )

    def test_terabytes_assumed_quantity(self):
        hourly = normalize_to_hourly(
            "Terabytes", Decimal("5.00"), assumed_quantity=Decimal("1")
        )
        self.assertEqual(hourly, Decimal("5.00") / Decimal("730"))


if __name__ == "__main__":
    unittest.main()
