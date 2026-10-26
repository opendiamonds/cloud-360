"""`U21 mcp-bridge` 的三份進版控檔與產生腳本（T-5、T-6、T-7；`BR72.6`、`BR72.7`、`BR72.9`、`BR74.2`、`BR75.4`）。"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import builtins
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from mcp_bridge import agents as bridge_agents
from mcp_bridge.calls import SEGMENT_PATTERN
from mcp_bridge.generator import CREDENTIAL_LIKE, _property_names_anywhere
from services.requirement_field_definitions import GROUPS_BY_KEY, KEY_PATTERN

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
BRIDGE_DIR = BACKEND_DIR / "mcp_bridge"
SCRIPT = BACKEND_DIR / "scripts" / "gen_mcp_tools.py"

#: AC11.4.2 的期望白名單：**寫在測試檔內的字面值**，不讀 allowlist.json（T-5、functional-spec §六）。
#: 擴充工具時本字面值必須在同一個 PR 修改，使白名單變動在 diff 上顯式可見。
EXPECTED_WHITELIST = {
    "read_requirement_fields": {"system_id"},
    "write_requirement_field": {"system_id", "agent_group", "field", "value"},
    "clear_requirement_field": {"system_id", "agent_group", "field"},
}


def load_script():
    spec = importlib.util.spec_from_file_location("gen_mcp_tools_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LiteralWhitelistTest(unittest.TestCase):  # T-5
    def test_generated_properties_equal_literal_whitelist(self):
        tools = {t["name"]: t for t in read_json(BRIDGE_DIR / "generated_tools.json")["tools"]}
        self.assertEqual(set(tools), set(EXPECTED_WHITELIST))
        for name, expected in EXPECTED_WHITELIST.items():
            with self.subTest(tool=name):
                schema = tools[name]["inputSchema"]
                self.assertEqual(set(schema["properties"]), expected)
                self.assertIs(schema["additionalProperties"], False)
                names = _property_names_anywhere(schema)
                self.assertEqual([n for n in names if CREDENTIAL_LIKE.search(n)], [])
                for forbidden in ("token", "key", "secret", "authorization"):
                    self.assertFalse(any(forbidden in n.lower() for n in names))


class ScriptReadClosureTest(unittest.TestCase):  # T-6
    def setUp(self):
        self.module = load_script()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.output = self.tmp / "generated_tools.json"
        shutil.copy(BRIDGE_DIR / "generated_tools.json", self.output)

    def run_mode(self, argv):
        opened = []
        real_open = builtins.open

        def spying_open(file, mode="r", *args, **kwargs):
            opened.append((Path(file).resolve(), mode))
            return real_open(file, mode, *args, **kwargs)

        captured = {}
        real_generate = self.module.generate_tools

        def spying_generate(openapi, allowlist):
            captured["args"] = (openapi, allowlist)
            return real_generate(openapi, allowlist)

        with mock.patch.object(self.module, "OUTPUT_PATH", self.output), \
                mock.patch.object(self.module, "generate_tools", spying_generate), \
                mock.patch("builtins.open", spying_open), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = self.module.main(argv)
        return code, opened, captured["args"]

    def assert_closed(self, opened, *, check_mode):
        openapi = (REPO_ROOT / "openapi.json").resolve()
        allowlist = (BRIDGE_DIR / "allowlist.json").resolve()
        output = self.output.resolve()
        reads = {p for p, mode in opened if "r" in mode}
        writes = {p for p, mode in opened if "w" in mode or "a" in mode}
        allowed_reads = {openapi, allowlist} | ({output} if check_mode else set())
        self.assertLessEqual(reads, allowed_reads)
        self.assertIn(openapi, reads)
        self.assertIn(allowlist, reads)
        self.assertEqual(output in reads, check_mode)
        self.assertEqual(writes, set() if check_mode else {output})
        self.assertNotIn((REPO_ROOT / ".mcp.json").resolve(), {p for p, _ in opened})

    def test_write_mode_reads_only_inputs(self):
        code, opened, (openapi, allowlist) = self.run_mode([])
        self.assertEqual(code, 0)
        self.assert_closed(opened, check_mode=False)
        self.assertEqual(openapi, read_json(REPO_ROOT / "openapi.json"))
        self.assertEqual({e.name for e in allowlist.entries},
                         {t["name"] for t in read_json(BRIDGE_DIR / "allowlist.json")["tools"]})

    def test_check_mode_reads_inputs_and_output_only(self):
        code, opened, _ = self.run_mode(["--check"])
        self.assertEqual(code, 0)
        self.assert_closed(opened, check_mode=True)

    def test_check_mode_red_after_hand_edit(self):
        doc = read_json(self.output)
        doc["tools"][0]["description"] += "（手改）"
        self.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        code, _, _ = self.run_mode(["--check"])
        self.assertEqual(code, 1)

    def test_repo_artifact_is_in_sync(self):
        module = load_script()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--check"]), 0)


class PatternConsistencyTest(unittest.TestCase):  # T-7
    def test_segment_pattern_equals_backend_key_pattern(self):
        self.assertEqual(SEGMENT_PATTERN.pattern, KEY_PATTERN.pattern)
        self.assertIs(bridge_agents.SEGMENT_PATTERN, SEGMENT_PATTERN)

    def test_allowlist_property_patterns_equal_constant(self):
        patterns = [p for t in read_json(BRIDGE_DIR / "allowlist.json")["tools"]
                    for p in t.get("property_patterns", {}).values()]
        self.assertEqual(len(patterns), 4)
        self.assertEqual(set(patterns), {SEGMENT_PATTERN.pattern})
        generated = [s["pattern"] for t in read_json(BRIDGE_DIR / "generated_tools.json")["tools"]
                     for s in t["inputSchema"]["properties"].values() if "pattern" in s]
        self.assertEqual(set(generated), {KEY_PATTERN.pattern})

    def test_agents_values_subset_of_backend_groups(self):
        values = set(read_json(BRIDGE_DIR / "agents.json").values())
        self.assertTrue(values)
        self.assertLessEqual(values, set(GROUPS_BY_KEY))


if __name__ == "__main__":
    unittest.main()
