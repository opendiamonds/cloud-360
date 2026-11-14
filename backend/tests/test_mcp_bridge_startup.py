"""`U21 mcp-bridge` 的啟動入口（T-8；`BR71.5`、`NFR21.6`、`NFR21.16` ①、`NFR21.35`）。

T-8 六案全部在主直譯器以 `main(argv, config_dir=暫存目錄)` 呼叫（functional-design 審查 R-17：具名入口），
每案回傳 1、恰一行 ERROR、沒有 traceback。正式三份檔不改，只改暫存目錄內的副本。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import ast
import io
import json
import logging
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

from mcp_bridge import cli
from mcp_bridge.limits import DEFAULT_MAX_CONCURRENCY
from mcp_bridge.observability import BridgeFormatter
from tests.mcp_topology import preserve_logging

BRIDGE_DIR = Path(__file__).resolve().parents[1] / "mcp_bridge"
FILES = ("generated_tools.json", "agents.json", "allowlist.json")


class StartupFailureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in FILES:
            shutil.copy(BRIDGE_DIR / name, self.tmp / name)

    def edit_tools(self, mutate):
        path = self.tmp / "generated_tools.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        mutate({t["name"]: t for t in doc["tools"]}, doc)
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def run_main(self, extra_argv=()):
        preserve_logging(self)
        stream = io.StringIO()
        from mcp_bridge.observability import configure_logging as original

        def configure_into_stream():
            original(stream=stream)

        saved_configure = cli.configure_logging
        cli.configure_logging = configure_into_stream
        self.addCleanup(setattr, cli, "configure_logging", saved_configure)
        # 替身 server 模組：驗證**意外通過**時，`main` 會呼叫它的 `serve`——記下來並立刻回 0，
        # 而不是真的起 uvicorn 把測試卡住。驗證失敗時它不得被呼叫。
        fake = types.ModuleType("mcp_bridge.server")
        fake.calls = []
        fake.serve = lambda loaded, args: fake.calls.append(loaded) or 0
        saved = sys.modules.get("mcp_bridge.server")
        sys.modules["mcp_bridge.server"] = fake
        try:
            code = cli.main(["--backend-url", "http://backend:8000", *extra_argv], config_dir=self.tmp)
        finally:
            if saved is not None:
                sys.modules["mcp_bridge.server"] = saved
            else:
                sys.modules.pop("mcp_bridge.server", None)
        self.assertEqual(fake.calls, [], "驗證應失敗，卻進到了 serve")
        lines = [line for line in stream.getvalue().splitlines() if line]
        return code, lines

    def assert_fatal(self, expected_subject, extra_argv=()):
        code, lines = self.run_main(extra_argv)
        self.assertEqual(code, 1)
        errors = [line for line in lines if " ERROR " in line]
        self.assertEqual(len(errors), 1, lines)
        self.assertIn(f'startup_failed subject="{expected_subject}"', errors[0])
        self.assertNotIn("Traceback", "\n".join(lines))
        return errors[0]

    def test_write_tool_without_requires_agent(self):
        self.edit_tools(lambda t, _: t["write_requirement_field"].__setitem__("requires_agent", False))
        self.assert_fatal("write_requirement_field")

    def test_membership_path_added(self):
        """產物與 allowlist **同時**加入成員管理項：只有路徑前綴白名單（`BR72.11`）擋得下。"""
        path = "/api/membership/projects/{project_id}/members"

        def mutate(tools, doc):
            extra = json.loads(json.dumps(tools["read_requirement_fields"]))
            extra["name"] = "invite_member"
            extra["binding"]["path"] = path
            doc["tools"].append(extra)
        self.edit_tools(mutate)
        allowlist_path = self.tmp / "allowlist.json"
        allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
        entry = json.loads(json.dumps(next(t for t in allowlist["tools"]
                                           if t["name"] == "read_requirement_fields")))
        entry.update(name="invite_member", path=path)
        allowlist["tools"].append(entry)
        allowlist_path.write_text(json.dumps(allowlist, ensure_ascii=False), encoding="utf-8")
        self.assert_fatal("invite_member")

    def test_api_key_property_added(self):
        self.edit_tools(lambda t, _: t["read_requirement_fields"]["inputSchema"]["properties"]
                        .__setitem__("api_key", {"type": "string"}))
        line = self.assert_fatal("read_requirement_fields")
        self.assertNotIn("api_key", line)

    def test_undeclared_input_schema_property(self):  # R-12 擇 (a)：以 allowlist.json 為獨立參考
        def mutate(tools, _):
            tools["read_requirement_fields"]["inputSchema"]["properties"]["region"] = {"type": "string"}
            tools["read_requirement_fields"]["binding"]["query_params"]["region"] = "region"
        self.edit_tools(mutate)
        self.assert_fatal("read_requirement_fields")

    def test_missing_file(self):
        (self.tmp / "agents.json").unlink()
        self.assert_fatal("agents.json")

    def test_non_json_file(self):
        (self.tmp / "generated_tools.json").write_text("{not json", encoding="utf-8")
        self.assert_fatal("generated_tools.json")

    def test_bad_encoding_file(self):
        (self.tmp / "allowlist.json").write_bytes(b"\xff\xfe\x00broken")
        self.assert_fatal("allowlist.json")

    def test_inject_removed(self):  # 程式審查 R-10：寫入會少了 on_behalf_of
        self.edit_tools(lambda t, _: t["write_requirement_field"]["binding"].__setitem__("inject", {}))
        self.assert_fatal("write_requirement_field")

    def test_body_param_mapped_to_on_behalf_of(self):  # 程式審查 R-10：呼叫端得以指定溯源標示
        self.edit_tools(lambda t, _: t["write_requirement_field"]["binding"]["body_params"]
                        .__setitem__("value", "on_behalf_of"))
        self.assert_fatal("write_requirement_field")

    def test_path_param_mapping_changed(self):  # 程式審查 R-10
        self.edit_tools(lambda t, _: t["clear_requirement_field"]["binding"]["path_params"]
                        .__setitem__("field", "agent_group"))
        self.assert_fatal("clear_requirement_field")

    def test_pattern_removed(self):  # 程式審查 R-10
        self.edit_tools(lambda t, _: t["write_requirement_field"]["inputSchema"]["properties"]["field"]
                        .pop("pattern"))
        self.assert_fatal("write_requirement_field")

    def test_port_out_of_range(self):  # 程式審查 R-04
        for port in ("0", "70000"):
            with self.subTest(port=port):
                self.assert_fatal("--port", ["--port", port])

    def test_max_concurrency_zero(self):  # 程式審查 R-04
        self.assert_fatal("--max-concurrency", ["--max-concurrency", "0"])

    def test_agent_value_outside_pattern(self):
        (self.tmp / "agents.json").write_text('{"cost": "../x"}', encoding="utf-8")
        self.assert_fatal("cost")


class ArgumentDefaultsTest(unittest.TestCase):
    def test_defaults(self):
        args = cli.parse_args(["--backend-url", "http://backend:8000"])
        self.assertEqual(args.host, "127.0.0.1")  # NFR21.16 ①
        self.assertEqual(args.port, 8080)
        self.assertEqual(args.max_concurrency, DEFAULT_MAX_CONCURRENCY)
        self.assertEqual(args.max_concurrency, 16)

    def test_backend_url_required(self):
        with self.assertRaises(SystemExit):
            cli.parse_args([])

    def test_main_module_shape(self):
        tree = ast.parse((BRIDGE_DIR / "__main__.py").read_text(encoding="utf-8"))
        kinds = [type(node).__name__ for node in tree.body]
        self.assertEqual(kinds.count("Raise"), 1)
        self.assertTrue(all(k in ("Import", "ImportFrom", "Raise") for k in kinds), kinds)
        self.assertEqual(len([k for k in kinds if k in ("Import", "ImportFrom")]), 2)

    def test_init_is_empty(self):
        text = (BRIDGE_DIR / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual([l for l in text.splitlines() if l.strip() and not l.strip().startswith("#")], [])

    def test_formatter_is_single_line(self):
        record = logging.LogRecord("x", logging.WARNING, __file__, 1, "a\nb\rc", None, None)
        self.assertNotIn("\n", BridgeFormatter().format(record))


if __name__ == "__main__":
    unittest.main()
