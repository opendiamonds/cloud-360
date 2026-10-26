"""`U21 mcp-bridge` 的結構規則（靜態檢查；`BR71.1`、`BR73.5`、`BR75.1`、`NFR21.12`、`NFR21.17`、`NFR21.18`、`NFR21.24`、`NFR21.38`、`NFR21.40`；CC-1–CC-3）。"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import ast
import re
import unittest
from pathlib import Path

from tests.mcp_topology import MCP_ROUTE, PINNED_MCP_VERSION

BACKEND_DIR = Path(__file__).resolve().parents[1]
BRIDGE_DIR = BACKEND_DIR / "mcp_bridge"
TESTS_DIR = BACKEND_DIR / "tests"
GEN_SCRIPT = BACKEND_DIR / "scripts" / "gen_mcp_tools.py"
PURE_MODULES = ("generator.py", "calls.py", "outcomes.py", "credentials.py", "agents.py", "limits.py")
NON_SDK_MODULES = PURE_MODULES + ("cli.py", "startup.py", "observability.py", "guards.py",
                                  "dispatch.py", "executor.py", "__main__.py", "__init__.py")
CONSTANTS = ("CONNECT_TIMEOUT_S", "OVERALL_TIMEOUT_S", "MAX_REQUEST_BODY_BYTES",
             "DEFAULT_MAX_CONCURRENCY", "MAX_RESPONSE_BODY_BYTES", "BODY_READ_TIMEOUT_S",
             "REQUEST_WALL_TIMEOUT_S")


def bridge_files():
    return sorted(BRIDGE_DIR.glob("*.py"))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def importers_of(*modules: str) -> set[str]:
    return {p.name for p in bridge_files() if imported_modules(p) & set(modules)}


class ImportBoundaryTest(unittest.TestCase):
    def test_only_app_and_server_import_mcp(self):  # R-11、CC-2
        importers = importers_of("mcp", "mcp_types")
        self.assertIn("app.py", importers)
        self.assertLessEqual(importers, {"app.py", "server.py"})

    def test_only_executor_imports_httpx(self):
        self.assertEqual(importers_of("httpx", "httpx2"), {"executor.py"})

    def test_pure_modules_import_nothing_heavy(self):  # NFR21.40
        for name in PURE_MODULES:
            with self.subTest(module=name):
                self.assertFalse(imported_modules(BRIDGE_DIR / name)
                                 & {"mcp", "mcp_types", "httpx", "sqlalchemy", "fastapi", "starlette"})

    def test_non_sdk_modules_do_not_import_mcp(self):
        for name in NON_SDK_MODULES:
            with self.subTest(module=name):
                self.assertNotIn("mcp", imported_modules(BRIDGE_DIR / name))

    def test_bridge_never_imports_backend_services(self):  # BR75.3、NFR21.12
        forbidden = {"services", "models", "database", "main"}
        for path in bridge_files():
            with self.subTest(module=path.name):
                self.assertFalse(imported_modules(path) & forbidden)

    def test_generator_script_imports_only_pure_generator(self):  # CC-2
        mods = imported_modules(GEN_SCRIPT)
        self.assertFalse(mods & {"main", "mcp", "mcp_types", "httpx", "os"})
        self.assertIn("from mcp_bridge.generator import", GEN_SCRIPT.read_text(encoding="utf-8"))

    def test_init_is_empty(self):
        lines = [l for l in (BRIDGE_DIR / "__init__.py").read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        self.assertEqual(lines, [])

    def test_backend_process_never_imports_bridge(self):  # CC-1
        offenders = []
        for path in BACKEND_DIR.rglob("*.py"):
            rel = path.relative_to(BACKEND_DIR)
            if rel.parts[0] in ("mcp_bridge", "tests", "tests_pg", "tests_redis", "scripts") \
                    or "site-packages" in rel.parts:
                continue
            if "mcp_bridge" in imported_modules(path):
                offenders.append(str(rel))
        self.assertEqual(offenders, [])


class SourceRulesTest(unittest.TestCase):
    def sources(self):
        return {p.name: p.read_text(encoding="utf-8") for p in bridge_files()}

    def test_no_environment_reads(self):  # BR71.1、NFR21.17
        pattern = re.compile(r"os\.environ|os\.getenv|getenv\(|environ\[")
        for name, text in list(self.sources().items()) + [("gen_mcp_tools.py", GEN_SCRIPT.read_text(encoding="utf-8"))]:
            with self.subTest(module=name):
                self.assertIsNone(pattern.search(text))

    def test_single_logger_name(self):
        calls = [(n, m) for n, t in self.sources().items() for m in re.findall(r"getLogger\(([^)]*)\)", t)]
        own = [c for c in calls if c[1] not in ('"httpx"', "", "name")]
        self.assertEqual([c[0] for c in own], ["observability.py"])
        self.assertIn('LOGGER_NAME = "cloud360.mcp_bridge"', self.sources()["observability.py"])

    def test_seven_constants_defined_once(self):  # NFR21.24
        all_text = "\n".join(self.sources().values())
        for const in CONSTANTS:
            with self.subTest(constant=const):
                self.assertEqual(len(re.findall(rf"^{const}\s*=", all_text, flags=re.M)), 1)
        for value in ("65536", "1048576"):
            hits = [n for n, t in self.sources().items() if value in t]
            self.assertEqual(hits, ["limits.py"], value)

    def test_no_jwt_decoding(self):  # BR73.5、NFR21.18
        for path in bridge_files():
            with self.subTest(module=path.name):
                self.assertFalse(imported_modules(path) & {"jwt", "jose", "base64"})

    def test_no_authorization_logic(self):  # BR75.1、NFR21.12
        for name, text in self.sources().items():
            for word in ("require_story_action", "user_can", "resolve_project_role"):
                with self.subTest(module=name, word=word):
                    self.assertNotIn(word, text)

    def test_file_io_only_in_startup(self):  # NFR21.2
        hits = {n for n, t in self.sources().items() if re.search(r"(?<![\w.])open\(", t)}
        self.assertEqual(hits, {"startup.py"})

    def test_no_blocking_io(self):  # NFR21.2
        for name, text in self.sources().items():
            with self.subTest(module=name):
                self.assertNotIn("time.sleep", text)
                self.assertNotIn("httpx.Client(", text)
                self.assertNotIn("import requests", text)


class TestDisciplineTest(unittest.TestCase):
    def test_no_skips_in_unit_tests(self):  # CC-3
        files = sorted(TESTS_DIR.glob("test_mcp_bridge_*.py")) + [TESTS_DIR / "mcp_topology.py",
                                                                    TESTS_DIR / "mcp_test_client.py"]
        self.assertEqual(len(files), 13)
        words = ("skip" + "Test", "skip" + "Unless", "skip" + "If", "Skip" + "Test")
        for path in files:
            text = path.read_text(encoding="utf-8")
            for word in words:
                with self.subTest(file=path.name, word=word):
                    self.assertNotIn(word, text)


class DependencyRouteTest(unittest.TestCase):  # NFR21.37、NFR21.38
    def non_comment_lines(self, path):
        return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.strip().startswith("#")]

    def test_route_a_single_exact_pin(self):
        self.assertEqual(MCP_ROUTE, "same-interpreter")
        lines = self.non_comment_lines(BACKEND_DIR / "requirements.txt")
        mcp_lines = [l for l in lines if re.match(r"^mcp\b", l)]
        self.assertEqual(mcp_lines, [f"mcp=={PINNED_MCP_VERSION}"])
        self.assertIn("fastapi==0.111.0", lines)
        self.assertIn("pydantic==2.13.4", lines)
        self.assertFalse((BACKEND_DIR / "requirements-mcp.txt").exists())
        self.assertNotIn("mcp", (BACKEND_DIR / "Dockerfile").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
