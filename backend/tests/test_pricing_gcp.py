"""Unit tests for GCP Catalog pricing helpers."""

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import patch

from cost.pricing_gcp import (
    _money_to_decimal,
    _sku_matches_filters,
    _sku_matches_region,
    _to_hourly,
    fetch_hourly_via_gcp_catalog,
    supports_gcp_official,
)


class TestPricingGcp(unittest.TestCase):
    def test_supports_known_sku(self):
        self.assertTrue(supports_gcp_official("ComputeEngine"))
        self.assertFalse(supports_gcp_official("NotAService"))

    def test_money_to_decimal(self):
        self.assertEqual(
            _money_to_decimal({"units": "1", "nanos": 500000000}),
            Decimal("1.5"),
        )

    def test_region_and_filters(self):
        sku = {
            "description": "E2 Instance Core running in Iowa",
            "serviceRegions": ["us-central1"],
            "category": {
                "resourceFamily": "Compute",
                "resourceGroup": "CPU",
                "usageType": "OnDemand",
            },
        }
        self.assertTrue(_sku_matches_region(sku, "us-central1"))
        self.assertFalse(_sku_matches_region(sku, "europe-west1"))
        self.assertTrue(
            _sku_matches_filters(
                sku,
                {
                    "usage_type": "OnDemand",
                    "resource_family": "Compute",
                    "resource_group": "CPU",
                    "description_contains": ["E2 Instance Core"],
                    "description_excludes": ["Preemptible"],
                },
            )
        )

    def test_to_hourly_h(self):
        self.assertEqual(_to_hourly(Decimal("0.02"), "h", Decimal("1")), Decimal("0.02"))

    @patch("cost.pricing_gcp._list_skus")
    @patch("cost.pricing_gcp._api_key", return_value="test-key")
    def test_fetch_picks_matching_sku(self, _key, list_mock):
        list_mock.return_value = [
            {
                "description": "E2 Instance Core running in Iowa",
                "serviceRegions": ["us-central1"],
                "category": {
                    "resourceFamily": "Compute",
                    "resourceGroup": "CPU",
                    "usageType": "OnDemand",
                },
                "pricingInfo": [
                    {
                        "pricingExpression": {
                            "usageUnit": "h",
                            "tieredRates": [
                                {
                                    "startUsageAmount": 0,
                                    "unitPrice": {"units": "0", "nanos": 33452000},
                                }
                            ],
                        }
                    }
                ],
            }
        ]
        hourly = fetch_hourly_via_gcp_catalog("ComputeEngine", "us-central1")
        self.assertEqual(hourly, Decimal("0.033452000"))


if __name__ == "__main__":
    unittest.main()
