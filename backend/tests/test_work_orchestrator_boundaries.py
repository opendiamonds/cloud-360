"""`U12 work-orchestrator` Step 8：邊界測試（§二 第 14、21 項；`NFR12.5`／`NFR12.8`／`NFR12.24`）。

以 **AST** 掃本單元三個模組的 `import`／`from … import`（含函式內的延遲匯入），
取代純字串 grep：字串 grep 可被別名、`from x import y`、動態匯入繞過。另以 patch
`httpx.AsyncClient.send` 斷言本單元送出的**每一個**請求，其 transport 皆為
`httpx.ASGITransport`——對外只經同進程 ASGI，不經網路、不直呼 service 層。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import asyncio
import unittest
from pathlib import Path
from unittest import mock

import httpx

from tests.work_orchestrator_fakes import drain
from tests.test_work_orchestrator_flow import ARCH, COST, REVIEW, Harness

SERVICES = Path(__file__).resolve().parents[1] / "services"
UNIT_MODULES = [
    SERVICES / "work_orchestrator.py",
    SERVICES / "work_orchestrator_rules.py",
    SERVICES / "work_orchestrator_capabilities.py",
]

#: `NFR12.8`／`NFR12.5`：不得匯入的模組（含 `main`：`app` 由 `U13` 傳入）。
FORBIDDEN_MODULES = {
    "main",
    "cost.estimate_intake_service",
    "cost.advice_orchestrator",
    "services.design_agent",
    "services.review_orchestrator",
    "services.collab_router",
    "services.llm_provider",
    "services.agent_router",
    "services.review_router",
    "cost.estimate_intake_router",
}
#: `NFR12.5`：LLM 套件。
FORBIDDEN_PACKAGES = {"openai", "anthropic", "langchain", "langgraph", "langchain_openai"}
FORBIDDEN_NAMES = {"importlib", "__import__"}


def imported_modules(path: Path, *, source: str = None) -> set:
    tree = ast.parse(source if source is not None else path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            # `from services import design_agent` 也算匯入 services.design_agent。
            names |= {f"{base}.{alias.name}" if base else alias.name for alias in node.names}
    return names


def referenced_names(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    }


class ImportBoundaryTest(unittest.TestCase):
    def test_no_module_imports_existing_capability_internals_or_main(self):
        for path in UNIT_MODULES:
            with self.subTest(module=path.name):
                found = imported_modules(path)
                self.assertEqual(found & FORBIDDEN_MODULES, set())
                for name in found:
                    self.assertNotIn(name.split(".")[0], FORBIDDEN_PACKAGES)

    def test_no_dynamic_import(self):
        for path in UNIT_MODULES:
            with self.subTest(module=path.name):
                self.assertEqual(
                    (imported_modules(path) | referenced_names(path)) & FORBIDDEN_NAMES, set()
                )

    def test_rules_module_is_pure(self):
        """純函式層零 I/O：不匯入 httpx、DB、Redis、logging。"""
        found = imported_modules(SERVICES / "work_orchestrator_rules.py")
        for banned in ("httpx", "sqlalchemy", "database", "models", "redis", "logging"):
            with self.subTest(banned=banned):
                self.assertFalse(any(n == banned or n.startswith(banned + ".") for n in found))

    def test_scanner_catches_the_shapes_it_claims_to(self):
        """反向斷言：掃描器真的認得 `from x import y` 與函式內匯入。"""
        source = "def f():\n    from services import design_agent\n    import main\n"
        self.assertTrue(
            {"services.design_agent", "main"} <= imported_modules(None, source=source)
        )

    def test_logger_name(self):
        """`NFR12.24`。"""
        source = (SERVICES / "work_orchestrator.py").read_text(encoding="utf-8")
        self.assertIn('logger = logging.getLogger("cloud360.work_orchestrator")', source)
        # 另兩個模組不建 logger（rules 為純函式、capabilities 不記 log）；若日後新增，
        # 名稱必須相同。
        for name in ("work_orchestrator_rules.py", "work_orchestrator_capabilities.py"):
            other = (SERVICES / name).read_text(encoding="utf-8")
            for line in other.splitlines():
                if "getLogger(" in line:
                    self.assertIn('getLogger("cloud360.work_orchestrator")', line)


class TransportBoundaryTest(unittest.TestCase):
    def test_every_request_goes_through_asgi_transport(self):
        seen = []
        original = httpx.AsyncClient.send

        async def spy(client, request, *args, **kwargs):
            seen.append(type(client._transport))
            return await original(client, request, *args, **kwargs)

        async def scenario():
            h = Harness()
            await h.dispatch(ARCH, COST, REVIEW)
            await drain(h.orchestrator)

        with mock.patch.object(httpx.AsyncClient, "send", spy):
            asyncio.run(scenario())
        self.assertGreater(len(seen), 5)
        self.assertEqual(set(seen), {httpx.ASGITransport})


if __name__ == "__main__":
    unittest.main()
