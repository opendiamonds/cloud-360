"""U3 legacy-cost-retirement：舊 HTTP 不可達、存活集可 import、無 playwright、不碰 archive ORM。

@purpose 驗證 FR9 退場後契約：舊 /api/cost/diagrams 404、U5 Port 可載入、requirements 無 playwright
@api GET /api/cost/diagrams
@step 1. TestClient 打舊路徑 → 404
@step 2. import cost.pricing_sdk／pricing_client
@step 3. 掃描應用碼不得映射 archive_* 表
@step 4. requirements.txt 無裸 playwright 行
"""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_SCAN_ROOTS = (
    BACKEND_ROOT / "cost",
    BACKEND_ROOT / "services",
    BACKEND_ROOT / "models.py",
    BACKEND_ROOT / "main.py",
)
ARCHIVE_TABLES = (
    "archive_diagram_cost",
    "archive_diagram_cost_line",
    "archive_pricing_cache",
    "archive_cost_audit_event",
)


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for root in APP_SCAN_ROOTS:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return [p for p in files if "__pycache__" not in p.parts]


class LegacyCostRetirementTest(unittest.TestCase):
    def test_legacy_cost_diagrams_returns_404(self):
        client = TestClient(app)
        res = client.get("/api/cost/diagrams")
        self.assertEqual(res.status_code, 404)

    def test_pricing_survival_modules_import(self):
        importlib.import_module("cost.pricing_sdk")
        importlib.import_module("cost.pricing_client")
        importlib.import_module("cost.config")
        importlib.import_module("cost.pricing_units")
        importlib.import_module("cost.pricing_offer_parser")
        importlib.import_module("cost.pricing_gcp")
        importlib.import_module("cost.pricing_azure")
        importlib.import_module("cost.pricing_query_parser")

    def test_app_code_has_no_archive_orm_mapping(self):
        """允許 database.py／schema／DEPLOY 字串；應用業務碼不得出現 archive_* 表名。"""
        offenders: list[str] = []
        for path in _iter_py_files():
            if path.name in {"database.py"}:
                continue
            text = path.read_text(encoding="utf-8")
            for table in ARCHIVE_TABLES:
                if table in text:
                    offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{table}")
        self.assertEqual(offenders, [])

    def test_requirements_has_no_playwright_package(self):
        req = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8")
        for line in req.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            pkg = stripped.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
            self.assertNotEqual(pkg, "playwright", msg=f"found playwright line: {stripped}")

    def test_e2e_regression_has_no_legacy_cost_stub_amount(self):
        e2e = REPO_ROOT / "frontend" / "tests" / "e2e" / "regression.spec.ts"
        text = e2e.read_text(encoding="utf-8")
        self.assertNotIn("$86.40", text)
        self.assertNotIn("/api/cost/diagrams", text)

    def test_no_cost_router_module(self):
        self.assertFalse((BACKEND_ROOT / "cost" / "cost_router.py").exists())
        self.assertFalse((BACKEND_ROOT / "cost" / "cost_service.py").exists())


if __name__ == "__main__":
    unittest.main()
