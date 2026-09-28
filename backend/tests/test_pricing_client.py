"""Unit tests for pricing_client and offer parser."""

from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from cost.pricing_client import PriceMiss, PriceUnsupported, fetch_hourly, supports_official_hourly
from cost.pricing_offer_parser import parse_on_demand_hourly

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "aws_ec2_offer_snippet.json"


class TestPricingOfferParser(unittest.TestCase):
    def setUp(self):
        with _FIXTURE.open(encoding="utf-8") as f:
            self.offer = json.load(f)

    def test_parse_ec2_t3_micro(self):
        hourly = parse_on_demand_hourly(
            self.offer,
            product_family="Compute Instance",
            attribute_filters={
                "instanceType": "t3.micro",
                "operatingSystem": "Linux",
                "tenancy": "Shared",
                "preInstalledSw": "NA",
                "capacitystatus": "Used",
            },
        )
        self.assertEqual(hourly, Decimal("0.0104000000"))

    def test_parse_miss_when_no_match(self):
        hourly = parse_on_demand_hourly(
            self.offer,
            product_family="Compute Instance",
            attribute_filters={"instanceType": "m5.24xlarge"},
        )
        self.assertIsNone(hourly)


class TestPricingClient(unittest.TestCase):
    def test_gcp_without_api_key_miss(self):
        os.environ.pop("GCP_BILLING_API_KEY", None)
        result = fetch_hourly("gcp", "ComputeEngine", "us-central1")
        self.assertIsInstance(result, PriceMiss)

    def test_azure_unconfigured_sku_miss(self):
        result = fetch_hourly("azure", "Compute", "eastus")
        self.assertIsInstance(result, PriceMiss)

    def test_azure_aks_supported(self):
        self.assertTrue(supports_official_hourly("AzureKubernetesService"))

    def test_s3_supported_with_assumed_storage(self):
        self.assertTrue(supports_official_hourly("AmazonS3"))

    @patch("cost.pricing_client.fetch_hourly_via_sdk")
    @patch("cost.pricing_client.use_sdk_enabled")
    def test_sdk_path_before_bulk(self, sdk_enabled_mock, sdk_fetch_mock):
        os.environ["COST_PRICING_USE_SDK"] = "1"
        sdk_enabled_mock.return_value = True
        sdk_fetch_mock.return_value = Decimal("0.0104")
        result = fetch_hourly("aws", "AmazonEC2", "us-east-1")
        self.assertEqual(result.kind, "hit")
        self.assertEqual(result.hourly, Decimal("0.0104"))
        self.assertEqual(result.source, "aws_sdk")
        sdk_fetch_mock.assert_called_once_with("AmazonEC2", "us-east-1")

    @patch("cost.pricing_client._download_offer")
    def test_live_parse_path(self, download_mock):
        with _FIXTURE.open(encoding="utf-8") as f:
            download_mock.return_value = json.load(f)
        result = fetch_hourly("aws", "AmazonEC2", "us-east-1")
        self.assertEqual(result.kind, "hit")
        self.assertEqual(result.hourly, Decimal("0.0104000000"))

    def test_rejects_non_allowlisted_url(self):
        from cost.pricing_client import _host_allowed

        self.assertFalse(_host_allowed("https://evil.example.com/offers/v1.0/aws/index.json"))
        self.assertTrue(
            _host_allowed(
                "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json"
            )
        )
        self.assertTrue(_host_allowed("https://prices.azure.com/api/retail/prices"))

    def test_unknown_cloud_unsupported(self):
        result = fetch_hourly("oracle", "Anything", "us-east-1")
        self.assertIsInstance(result, PriceUnsupported)

    @patch("cost.pricing_client._fetch_via_bulk_api")
    @patch("cost.pricing_client.fetch_hourly_via_sdk")
    @patch("cost.pricing_client.use_sdk_enabled")
    def test_sdk_failure_degrades_to_bulk(self, sdk_enabled_mock, sdk_fetch_mock, bulk_mock):
        sdk_enabled_mock.return_value = True
        sdk_fetch_mock.return_value = None
        bulk_mock.return_value = Decimal("0.02")
        result = fetch_hourly("aws", "AmazonEC2", "us-east-1")
        self.assertEqual(result.kind, "hit")
        self.assertEqual(result.source, "bulk_api")
        bulk_mock.assert_called_once()

    @patch("cost.pricing_client._write_disk_cache")
    @patch("cost.pricing_client._read_disk_cache", return_value=None)
    @patch("cost.pricing_client._download_offer")
    @patch("cost.pricing_client.use_sdk_enabled", return_value=False)
    def test_disk_cache_payload_has_no_secrets(
        self, _sdk_off, download_mock, _read_cache, write_mock
    ):
        with _FIXTURE.open(encoding="utf-8") as f:
            download_mock.return_value = json.load(f)
        os.environ["AWS_SECRET_ACCESS_KEY"] = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        try:
            result = fetch_hourly("aws", "AmazonEC2", "us-east-1")
            self.assertEqual(result.kind, "hit")
            self.assertTrue(write_mock.called)
            args, kwargs = write_mock.call_args
            blob = str(args) + str(kwargs) + str(result)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", blob)
            self.assertNotIn("wJalrXUtnFEMI", blob)
        finally:
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)

    @patch("cost.pricing_sdk._get_pricing_client")
    def test_sdk_log_omits_secret_on_client_error(self, client_mock):
        from botocore.exceptions import ClientError
        from cost.pricing_sdk import fetch_hourly_via_sdk, reset_client_for_tests

        reset_client_for_tests()
        fake_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        os.environ["COST_PRICING_USE_SDK"] = "1"
        os.environ["AWS_SECRET_ACCESS_KEY"] = fake_secret
        err = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": f"bad {fake_secret}"}},
            "GetProducts",
        )
        client_mock.return_value.get_products.side_effect = err
        with self.assertLogs("cost.pricing_sdk", level="WARNING") as cm:
            out = fetch_hourly_via_sdk("AmazonEC2", "us-east-1")
        self.assertIsNone(out)
        joined = "\n".join(cm.output)
        self.assertNotIn(fake_secret, joined)
        self.assertIn("AccessDenied", joined)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)


if __name__ == "__main__":
    unittest.main()
