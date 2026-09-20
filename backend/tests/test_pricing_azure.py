"""Unit tests for Azure Retail Prices client."""

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from cost.pricing_azure import (
    _normalize_azure_unit,
    _pick_hourly,
    fetch_hourly_via_azure_retail,
    supports_azure_official,
)
from cost.pricing_client import PriceHit, PriceMiss, fetch_hourly


class TestAzureUnits(unittest.TestCase):
    def test_hour_units(self):
        self.assertEqual(
            _normalize_azure_unit("1 Hour", Decimal("0.1"), Decimal("1")),
            Decimal("0.1"),
        )
        self.assertEqual(
            _normalize_azure_unit("1/Hour", Decimal("0.2"), Decimal("1")),
            Decimal("0.2"),
        )

    def test_month_unit(self):
        hourly = _normalize_azure_unit("1/Month", Decimal("35"), Decimal("1"))
        self.assertEqual(hourly, Decimal("35") / Decimal("730"))


class TestAzurePick(unittest.TestCase):
    def test_prefers_positive_price(self):
        items = [
            {
                "retailPrice": 0,
                "unitOfMeasure": "1/Hour",
                "armRegionName": "eastus",
                "meterName": "Free",
            },
            {
                "retailPrice": 0.008,
                "unitOfMeasure": "1/Hour",
                "armRegionName": "eastus",
                "meterName": "100 RU/s",
            },
        ]
        hourly = _pick_hourly(items, {"assumed_quantity": 1}, "eastus")
        self.assertEqual(hourly, Decimal("0.008"))


class TestAzureClient(unittest.TestCase):
    def test_supports_aks(self):
        self.assertTrue(supports_azure_official("AzureKubernetesService"))
        self.assertFalse(supports_azure_official("NotARealSku"))

    @patch("cost.pricing_azure.httpx.Client")
    def test_fetch_parses_retail_price(self, client_cls):
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client
        client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "Items": [
                    {
                        "retailPrice": 0.1,
                        "unitOfMeasure": "1 Hour",
                        "armRegionName": "eastus",
                        "meterName": "Standard Uptime SLA",
                    }
                ]
            },
        )
        hourly = fetch_hourly_via_azure_retail("AzureKubernetesService", "eastus")
        self.assertEqual(hourly, Decimal("0.1"))

    @patch("cost.pricing_client.fetch_hourly_via_azure_retail")
    def test_fetch_hourly_routes_azure(self, azure_fetch):
        azure_fetch.return_value = Decimal("0.1")
        result = fetch_hourly("azure", "AzureKubernetesService", "eastus")
        self.assertIsInstance(result, PriceHit)
        self.assertEqual(result.hourly, Decimal("0.1"))
        self.assertEqual(result.source, "azure_retail")

    @patch("cost.pricing_client.fetch_hourly_via_azure_retail")
    def test_fetch_hourly_azure_miss(self, azure_fetch):
        azure_fetch.return_value = None
        result = fetch_hourly("azure", "AzureKubernetesService", "eastus")
        self.assertIsInstance(result, PriceMiss)


if __name__ == "__main__":
    unittest.main()
