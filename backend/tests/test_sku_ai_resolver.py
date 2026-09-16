"""SKU fuzzy / AI resolver tests (no live LLM)."""

import os
import unittest

os.environ["COST_SKU_AI_INFER"] = "0"

from cost.sku_ai_resolver import _fuzzy_infer, resolve_cell  # noqa: E402
from cost.sku_mapper import map_cell  # noqa: E402


class TestSkuAiResolver(unittest.TestCase):
    def test_exact_map_unchanged(self):
        mapped, note = resolve_cell(
            "AKS",
            "shape=image;image=x",
            cloud_hint="azure",
            mxcell_id="aks1",
        )
        self.assertIsNone(note)
        self.assertEqual(mapped.kind, "unique")
        assert mapped.candidate is not None
        self.assertEqual(mapped.candidate.sku, "AzureKubernetesService")

    def test_fuzzy_azure_cdn_label(self):
        direct = map_cell("Azure Content Delivery Network", "shape=azure2;vertex=1")
        self.assertEqual(direct.kind, "none")
        fuzzy = _fuzzy_infer(
            "Azure Content Delivery Network",
            "shape=azure2;vertex=1",
            "azure",
        )
        self.assertIsNotNone(fuzzy)
        assert fuzzy is not None
        self.assertEqual(fuzzy.candidate.sku, "AzureCDN")

    def test_fuzzy_k8s_to_aks(self):
        fuzzy = _fuzzy_infer("Kubernetes cluster", "shape=azure2", "azure")
        self.assertIsNotNone(fuzzy)
        assert fuzzy is not None
        self.assertEqual(fuzzy.candidate.sku, "AzureKubernetesService")

    def test_resolve_cell_uses_fuzzy_when_exact_misses(self):
        mapped, note = resolve_cell(
            "Microsoft CDN edge",
            "shape=azure2",
            cloud_hint="azure",
            mxcell_id="cdn1",
        )
        self.assertEqual(mapped.kind, "unique")
        assert mapped.candidate is not None
        self.assertEqual(mapped.candidate.sku, "AzureCDN")
        self.assertIsNotNone(note)
        assert note is not None
        self.assertIn("模糊比對", note)


if __name__ == "__main__":
    unittest.main()
