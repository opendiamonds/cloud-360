"""
@purpose 目錄形 SKU 才查規格說明；查到的是描述字串，不是單價。
@given 無外網；_lookup 以 mock 回傳
@api POST /api/cost/v1/sets -> 201 | 上傳後明細可帶 spec_description（本檔測 enrich 純函式）
@step 對 m5.large／區域字串呼叫 looks_like_catalog_sku | 回 False，不外呼
@step 對 GCP XXXX-XXXX-XXXX 且 mock 有描述 | 列上出現 specDescription
@step mock 回 None | 列上沒有 specDescription
@pass 非 SKU 不查詢；命中時只寫描述
@story C1-S1 FR13
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from cost.sku_catalog import _MAX_UNIQUE, enrich_line_specs, looks_like_catalog_sku


class LooksLikeSkuTest(unittest.TestCase):
    def test_gcp_four_part_id(self):
        self.assertTrue(looks_like_catalog_sku("gcp", "2DA5-2C43-66E6"))

    def test_rejects_region_and_test_stubs(self):
        self.assertFalse(looks_like_catalog_sku("gcp", "SKU1"))
        self.assertFalse(looks_like_catalog_sku("aws", "us-east-1"))
        self.assertFalse(looks_like_catalog_sku("azure", "eastus"))
        self.assertFalse(looks_like_catalog_sku("aws", "m5.large"))

    def test_azure_ids(self):
        self.assertTrue(looks_like_catalog_sku("azure", "DZH318Z0BQ4B"))
        self.assertTrue(looks_like_catalog_sku("azure", "Standard_B1s"))


class EnrichLineSpecsTest(unittest.TestCase):
    def test_skips_non_sku_and_does_not_call_network(self):
        lines = [{"spec": "us-east-1", "itemName": "EC2"}]
        with patch("cost.sku_catalog._lookup") as lookup:
            enrich_line_specs("aws", lines)
            lookup.assert_not_called()
        self.assertNotIn("specDescription", lines[0])

    def test_fills_description_from_lookup(self):
        lines = [{"spec": "2DA5-2C43-66E6", "serviceId": "6F81-5844-456A"}]
        with patch("cost.sku_catalog._lookup", return_value="N1 Predefined Instance Core running in Americas"):
            enrich_line_specs("gcp", lines)
        self.assertEqual(
            lines[0]["specDescription"],
            "N1 Predefined Instance Core running in Americas",
        )

    def test_lookup_miss_leaves_line_unchanged(self):
        lines = [{"spec": "2DA5-2C43-66E6"}]
        with patch("cost.sku_catalog._lookup", return_value=None):
            enrich_line_specs("gcp", lines)
        self.assertNotIn("specDescription", lines[0])

    def test_skips_description_matching_item_name(self):
        lines = [
            {
                "spec": "2DA5-2C43-66E6",
                "itemName": "N1 Predefined Instance Core running in Americas",
            }
        ]
        with patch(
            "cost.sku_catalog._lookup",
            return_value="N1 Predefined Instance Core running in Americas",
        ):
            enrich_line_specs("gcp", lines)
        self.assertNotIn("specDescription", lines[0])

    def test_uses_catalog_sku_when_spec_is_display_name(self):
        lines = [
            {
                "itemName": "Instances (Compute Engine)",
                "spec": "N4 Core",
                "catalogSku": "2DA5-2C43-66E6",
                "serviceId": "6F81-5844-456A",
            }
        ]
        with patch(
            "cost.sku_catalog._lookup",
            return_value="Extra catalog detail",
        ) as lookup:
            enrich_line_specs("gcp", lines)
        lookup.assert_called_once_with("gcp", "2DA5-2C43-66E6", "6F81-5844-456A")
        self.assertEqual(lines[0]["specDescription"], "Extra catalog detail")

    def test_caps_unique_lookups(self):
        lines = [
            {"spec": f"{i:04X}-AAAA-0001"}
            for i in range(_MAX_UNIQUE + 1)
        ]
        with patch("cost.sku_catalog._lookup", return_value="desc") as lookup:
            enrich_line_specs("gcp", lines)
        self.assertEqual(lookup.call_count, _MAX_UNIQUE)
        self.assertEqual(lines[0]["specDescription"], "desc")
        self.assertNotIn("specDescription", lines[-1])
