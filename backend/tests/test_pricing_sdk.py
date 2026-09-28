"""Unit tests for AWS SDK pricing wrapper."""

from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from cost.pricing_sdk import fetch_hourly_via_sdk, reset_client_for_tests, use_sdk_enabled

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "aws_cli_get_products_ec2.json"


class TestPricingSdk(unittest.TestCase):
    def setUp(self):
        reset_client_for_tests()

    def tearDown(self):
        reset_client_for_tests()
        os.environ.pop("COST_PRICING_USE_SDK", None)
        os.environ.pop("COST_PRICING_USE_CLI", None)

    def test_use_sdk_respects_disable(self):
        os.environ["COST_PRICING_USE_SDK"] = "0"
        self.assertFalse(use_sdk_enabled())

    @patch("cost.pricing_sdk.boto3.client")
    def test_fetch_ec2_via_sdk(self, client_factory):
        os.environ["COST_PRICING_USE_SDK"] = "1"
        payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        client = MagicMock()
        client.get_products.return_value = payload
        client_factory.return_value = client

        hourly = fetch_hourly_via_sdk("AmazonEC2", "us-east-1")
        self.assertEqual(hourly, Decimal("0.0104000000"))
        client.get_products.assert_called_once()
        kwargs = client.get_products.call_args.kwargs
        self.assertEqual(kwargs["ServiceCode"], "AmazonEC2")
        self.assertEqual(kwargs["FormatVersion"], "aws_v1")

    @patch("cost.pricing_sdk.boto3.client")
    def test_sdk_failure_returns_none(self, client_factory):
        os.environ["COST_PRICING_USE_SDK"] = "1"
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_products.side_effect = ClientError(
            {"Error": {"Code": "UnrecognizedClientException", "Message": "bad creds"}},
            "GetProducts",
        )
        client_factory.return_value = client
        self.assertIsNone(fetch_hourly_via_sdk("AmazonEC2", "us-east-1"))


if __name__ == "__main__":
    unittest.main()
