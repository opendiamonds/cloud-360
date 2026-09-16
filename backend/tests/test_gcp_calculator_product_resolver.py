"""GCP Calculator product resolver tests (no live Playwright / LLM)."""

import os
import unittest
from unittest.mock import patch

os.environ["COST_SKU_AI_INFER"] = "0"

from cost.gcp_calculator_product_resolver import (  # noqa: E402
    _ai_pick_product,
    ai_suggest_calculator_search_terms,
    filter_visible_products,
    label_search_variants,
    resolve_gcp_calculator_product,
    search_terms_for_item,
    search_terms_for_map_key,
)


class TestGcpCalculatorProductResolver(unittest.TestCase):
    def test_filter_no_products_matched_message(self):
        visible = filter_visible_products(
            ["No products matched your search", "Apigee"]
        )
        self.assertEqual(visible, ["Apigee"])

    def test_label_first_search_terms_for_apigee(self):
        terms = search_terms_for_item("Apigee", "Apigee API Gateway")
        self.assertEqual(terms[0], "Apigee API Gateway")
        self.assertIn("Apigee", terms)
        self.assertIn("Apigee API Management", terms)  # yaml alias fallback

    def test_apigee_label_picks_calculator_product_without_yaml_name(self):
        target = resolve_gcp_calculator_product(
            map_key="Apigee",
            visible_products=["Apigee"],
            diagram_label="Apigee",
        )
        self.assertEqual(target.click_title, "Apigee")
        self.assertEqual(target.source, "label")

    def test_networking_maps_from_cloud_load_balancing_search(self):
        target = resolve_gcp_calculator_product(
            map_key="Networking",
            visible_products=["Networking"],
            diagram_label="Cloud Load Balancer",
        )
        self.assertEqual(target.click_title, "Networking")
        self.assertEqual(target.service_type, "Cloud Load Balancing")
        self.assertEqual(target.source, "yaml")

    def test_cloud_monitoring_maps_to_cloud_operations(self):
        target = resolve_gcp_calculator_product(
            map_key="CloudObservability",
            visible_products=["Cloud Operations"],
            diagram_label="Cloud Monitoring",
        )
        self.assertEqual(target.click_title, "Cloud Operations")
        self.assertEqual(target.service_type, "Cloud Monitoring")

    def test_fuzzy_pick_when_only_similar_title_visible(self):
        target = resolve_gcp_calculator_product(
            map_key="ComputeEngine",
            visible_products=["Compute Engine"],
            diagram_label="GCE VM",
        )
        self.assertEqual(target.click_title, "Compute Engine")

    def test_search_terms_include_product_and_aliases(self):
        terms = search_terms_for_map_key("Networking")
        self.assertEqual(terms[0], "Networking")
        self.assertIn("Cloud Load Balancing", terms)

    def test_label_variants_skip_generic_cloud_token(self):
        variants = label_search_variants("Cloud Load Balancer")
        self.assertNotIn("Cloud", variants)
        self.assertIn("Cloud Load Balancer", variants)

    @patch("cost.gcp_calculator_product_resolver.llm_auth_ready", return_value=True)
    @patch("cost.gcp_calculator_product_resolver.sku_ai_infer_enabled", return_value=True)
    @patch(
        "cost.gcp_calculator_product_resolver._openrouter_chat",
        return_value='{"click_title":"Networking","service_type":"Cloud Load Balancing","confidence":0.91,"reason_zh":"Load Balancer 屬於 Networking 服務"}',
    )
    def test_ai_fallback_picks_visible_product(self, *_mocks):
        ai = _ai_pick_product(
            map_key="Networking",
            visible_products=["Networking", "Cloud CDN"],
            diagram_label="External HTTP(S) LB",
            yaml_service_type="Cloud Load Balancing",
        )
        self.assertIsNotNone(ai)
        assert ai is not None
        self.assertEqual(ai.click_title, "Networking")
        self.assertEqual(ai.service_type, "Cloud Load Balancing")
        self.assertEqual(ai.source, "ai")

    @patch("cost.gcp_calculator_product_resolver.llm_auth_ready", return_value=True)
    @patch("cost.gcp_calculator_product_resolver.sku_ai_infer_enabled", return_value=True)
    @patch(
        "cost.gcp_calculator_product_resolver._openrouter_chat",
        return_value='{"search_terms":["Apigee"],"confidence":0.88,"reason_zh":"Calculator 產品名為 Apigee"}',
    )
    def test_ai_suggest_search_terms(self, *_mocks):
        terms = ai_suggest_calculator_search_terms(
            diagram_label="Apigee API Management",
            map_key="Apigee",
            tried_terms=["Apigee API Management"],
            catalog_titles=["Apigee", "Compute Engine"],
        )
        self.assertEqual(terms, ["Apigee"])


if __name__ == "__main__":
    unittest.main()
