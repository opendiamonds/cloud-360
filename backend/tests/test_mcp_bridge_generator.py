"""`U21 mcp-bridge` 產生器的 PBT 與 example（T-3；`BR72.1`–`BR72.11`）。

閘門是**決定性的**（functional-design 審查 R-14 擇 (a)）：八個類別各寫一個 `@given`，每個測試只生成
自己的類別，所以不設比例下限——成功分支本身就是 `consistent`／`renamed_clean` 兩個測試的生成目標。
策略先產生一致的 (openapi, allowlist) 配對（allowlist 一律由 openapi 衍生），再施加且只施加一種破壞。

每個類別斷言**單一**結果（不接受「任一碼皆可」），並一併檢查性質四（決定性、鍵順序無關）。
`derandomize=True`、`database=None`：每次執行抽到同一組樣本，且不寫 `.hypothesis/`。
設 `HYPOTHESIS_NO_SHRINK=1` 時關閉 shrinking（突變驗證時用，`unit-test-instructions.md` §四）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import copy
import json
import os
import unittest
from pathlib import Path

from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from mcp_bridge.generator import (
    CREDENTIAL_LIKE,
    GeneratorError,
    ToolSpec,
    _property_names_anywhere,
    dump_specs,
    generate_tools,
    parse_allowlist,
    validate_tool_specs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = REPO_ROOT / "backend" / "mcp_bridge"

_PHASES = (
    (Phase.explicit, Phase.reuse, Phase.generate)
    if os.environ.get("HYPOTHESIS_NO_SHRINK") == "1"
    else (Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink)
)
PBT = settings(max_examples=60, derandomize=True, database=None, deadline=None, phases=_PHASES)

#: 乾淨字母表：任何名稱都不含 token／key／secret／authorization 子字串。
CLEAN = (
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "theta", "iota", "lambda_x",
    "omega", "item_id", "label", "note", "color", "size", "value", "system_id", "group",
    "region", "tier",
)
#: 命中黑名單的名稱，含大小寫變體。
DIRTY = (
    "token", "Token", "api_key", "API_KEY", "client_secret", "Secret", "authorization",
    "Authorization", "access_token", "SessionKey", "refreshTOKEN",
)
METHODS = ("GET", "PUT", "DELETE", "POST", "PATCH")
STRIP_FIELD = "on_behalf_of"
SCOPE_PATH = "/api/membership/projects/{project_id}/members"

assert not any(CREDENTIAL_LIKE.search(n) for n in CLEAN)
assert all(CREDENTIAL_LIKE.search(n) for n in DIRTY)


# ---- 一致配對的策略 -----------------------------------------------------------------------
@st.composite
def consistent_pair(draw):
    """回傳 (openapi, allowlist_doc, ops)。ops[0] 恆為有本體的非 GET operation。"""
    pool = list(draw(st.permutations(CLEAN)))
    n_ops = draw(st.integers(min_value=1, max_value=3))
    ops = []
    for i in range(n_ops):
        method = "PUT" if i == 0 else draw(st.sampled_from(METHODS))
        n_path = draw(st.integers(min_value=0, max_value=2))
        path_params = [pool.pop() for _ in range(n_path)]
        query = [pool.pop() for _ in range(draw(st.integers(min_value=0, max_value=1)))]
        body, required_body, strip, inject = [], [], [], {}
        if method != "GET":
            body = [pool.pop() for _ in range(draw(st.integers(min_value=1, max_value=2)))]
            required_body = [b for b in body if draw(st.booleans())]
            if draw(st.booleans()):
                strip = [STRIP_FIELD]
                if draw(st.booleans()):
                    inject = {STRIP_FIELD: "agent_group_of_declared_agent"}
        path = f"/api/requirements/res{i}" + "".join("/{" + p + "}" for p in path_params)
        ops.append({
            "name": f"tool_{i}", "method": method, "path": path, "path_params": path_params,
            "query": query, "body": body, "required_body": required_body,
            "strip": strip, "inject": inject,
            "requires_agent": True if (method != "GET" or inject) else draw(st.booleans()),
        })
    openapi = build_openapi(ops)
    allowlist = {"version": 1, "tools": [entry_for(op) for op in ops]}
    return openapi, allowlist, ops


def build_openapi(ops, extra_query=None, extra_body=None):
    paths = {}
    for op in ops:
        params = [{"in": "path", "name": p, "required": True,
                   "schema": {"type": "string", "title": p}} for p in op["path_params"]]
        params += [{"in": "query", "name": q, "required": False,
                    "schema": {"type": "string", "title": q}} for q in op["query"]]
        operation = {"operationId": op["name"], "parameters": params,
                     "security": [{"HTTPBearer": []}]}
        body_names = list(op["body"]) + (list(op["strip"]))
        if body_names:
            props = {b: {"type": "string", "title": b, "description": "x"} for b in op["body"]}
            for s in op["strip"]:
                props[s] = {"anyOf": [{"type": "string"}, {"type": "null"}], "title": s}
            operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "additionalProperties": False, "properties": props,
                "required": list(op["required_body"]),
            }}}}
        paths.setdefault(op["path"], {})[op["method"].lower()] = operation
    paths[SCOPE_PATH] = {"post": {
        "operationId": "invite", "security": [{"HTTPBearer": []}],
        "parameters": [{"in": "path", "name": "project_id", "required": True,
                        "schema": {"type": "string"}}],
        "requestBody": {"content": {"application/json": {"schema": {
            "type": "object", "properties": {"user_id": {"type": "string"}}}}}},
    }}
    paths["/api/other/things"] = {"get": {"operationId": "other", "parameters": []}}
    return {"openapi": "3.1.0", "paths": paths, "components": {"securitySchemes": {
        "HTTPBearer": {"type": "http", "scheme": "bearer"}}}}


def entry_for(op):
    props = list(op["path_params"]) + list(op["query"]) + list(op["body"])
    entry = {
        "name": op["name"], "method": op["method"], "path": op["path"],
        "description": "測試工具", "properties": props,
        "property_descriptions": {p: "描述" for p in props},
        "requires_agent": op["requires_agent"],
    }
    if op["strip"]:
        entry["strip_body_fields"] = list(op["strip"])
    if op["inject"]:
        entry["inject"] = dict(op["inject"])
    return entry


def outcome(openapi, allowlist_doc):
    try:
        specs = generate_tools(openapi, parse_allowlist(allowlist_doc))
    except GeneratorError as err:
        return ("error", err.code, err.tool_name)
    return ("ok", dump_specs(specs))


def reorder(openapi):
    """性質四：反轉 paths 與每個本體 properties 的鍵順序。"""
    shuffled = copy.deepcopy(openapi)
    shuffled["paths"] = dict(reversed(list(shuffled["paths"].items())))
    for item in shuffled["paths"].values():
        for op in item.values():
            schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if schema and "properties" in schema:
                schema["properties"] = dict(reversed(list(schema["properties"].items())))
    return shuffled


class GeneratorPropertyTest(unittest.TestCase):
    def assert_deterministic(self, openapi, allowlist_doc):
        first = outcome(openapi, allowlist_doc)
        self.assertEqual(first, outcome(copy.deepcopy(openapi), copy.deepcopy(allowlist_doc)))
        self.assertEqual(first, outcome(reorder(openapi), allowlist_doc))
        return first

    def assert_success_properties(self, openapi, allowlist_doc):
        specs = generate_tools(openapi, parse_allowlist(allowlist_doc))
        allowed_ops = {(t["method"], t["path"]) for t in allowlist_doc["tools"]}
        declared = {t["name"]: set(t["properties"]) for t in allowlist_doc["tools"]}
        for spec in specs:
            names = _property_names_anywhere(spec.input_schema)
            # 性質一：任何深度都不命中黑名單
            self.assertFalse([n for n in names if CREDENTIAL_LIKE.search(n)])
            # 性質二：(method, path) ⊆ allowlist
            self.assertIn((spec.binding["method"], spec.binding["path"]), allowed_ops)
            # 性質三：strip／inject 的鍵、security scheme 名不進屬性
            self.assertNotIn(STRIP_FIELD, names)
            self.assertNotIn("HTTPBearer", names)
            self.assertFalse(set(spec.binding["inject"]) & set(names))
            # 性質五：屬性鍵集合 = 宣告集合
            self.assertEqual(set(spec.input_schema["properties"]), declared[spec.name])
            self.assertIs(spec.input_schema["additionalProperties"], False)
            # 性質七：非 GET 或有 inject ⇒ requires_agent
            if spec.binding["method"] != "GET" or spec.binding["inject"]:
                self.assertTrue(spec.requires_agent)
        return specs

    @PBT
    @given(consistent_pair())
    def test_consistent(self, pair):
        openapi, allowlist_doc, _ = pair
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result[0], "ok", result)
        self.assert_success_properties(openapi, allowlist_doc)

    @PBT
    @given(consistent_pair(), st.sampled_from(DIRTY))
    def test_renamed_clean(self, pair, dirty):
        openapi, allowlist_doc, ops = pair
        ops[0]["query"] = list(ops[0]["query"]) + [dirty]
        openapi = build_openapi(ops)
        entry = allowlist_doc["tools"][0]
        entry["rename"] = {dirty: "renamed_ok"}
        entry["properties"].append("renamed_ok")
        entry["property_descriptions"]["renamed_ok"] = "改名後"
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result[0], "ok", result)
        specs = self.assert_success_properties(openapi, allowlist_doc)
        spec = {s.name: s for s in specs}["tool_0"]
        self.assertIn("renamed_ok", spec.input_schema["properties"])
        self.assertEqual(spec.binding["query_params"]["renamed_ok"], dirty)

    @PBT
    @given(consistent_pair(), st.sampled_from(DIRTY),
           st.sampled_from(("query", "body_top", "body_nested")), st.booleans())
    def test_credential_injected(self, pair, dirty, location, in_whitelist):
        openapi, allowlist_doc, ops = pair
        entry = allowlist_doc["tools"][0]
        if location == "query":
            ops[0]["query"] = list(ops[0]["query"]) + [dirty]
            openapi = build_openapi(ops)
            whitelisted = dirty
        else:
            openapi = build_openapi(ops)
            schema = openapi["paths"][ops[0]["path"]]["put"]["requestBody"]["content"][
                "application/json"]["schema"]
            if location == "body_top":
                schema["properties"][dirty] = {"type": "string"}
                whitelisted = dirty
            else:
                schema["properties"]["wrapper"] = {
                    "type": "object", "properties": {dirty: {"type": "string"}}}
                whitelisted = "wrapper"
        if in_whitelist:
            entry["properties"].append(whitelisted)
            entry["property_descriptions"][whitelisted] = "x"
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "credential_like_property", "tool_0"))

    @PBT
    @given(consistent_pair(), st.sampled_from(DIRTY))
    def test_renamed_dirty(self, pair, dirty):
        openapi, allowlist_doc, ops = pair
        entry = allowlist_doc["tools"][0]
        victim = entry["properties"][0]
        entry["rename"] = {victim: dirty}
        entry["properties"] = [dirty if p == victim else p for p in entry["properties"]]
        entry["property_descriptions"] = {p: "x" for p in entry["properties"]}
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "credential_like_property", "tool_0"))

    @PBT
    @given(consistent_pair(), st.booleans())
    def test_whitelist_drift(self, pair, add):
        openapi, allowlist_doc, _ = pair
        entry = allowlist_doc["tools"][0]
        if add or not entry["properties"]:
            entry["properties"].append("extra_clean")
            entry["property_descriptions"]["extra_clean"] = "x"
        else:
            removed = entry["properties"].pop()
            del entry["property_descriptions"][removed]
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "whitelist_mismatch", "tool_0"))

    @PBT
    @given(consistent_pair())
    def test_missing_op(self, pair):
        openapi, allowlist_doc, _ = pair
        allowlist_doc["tools"].append({
            "name": "tool_missing", "method": "GET", "path": "/api/requirements/does_not_exist",
            "description": "x", "properties": [], "property_descriptions": {},
            "requires_agent": False,
        })
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "missing_operation", "tool_missing"))

    @PBT
    @given(consistent_pair(), st.sampled_from((SCOPE_PATH, "/api/other/things")))
    def test_out_of_scope(self, pair, path):
        openapi, allowlist_doc, _ = pair
        method, props = ("POST", ["project_id", "user_id"]) if path == SCOPE_PATH else ("GET", [])
        allowlist_doc["tools"].append({
            "name": "tool_scope", "method": method, "path": path, "description": "x",
            "properties": props, "property_descriptions": {p: "x" for p in props},
            "requires_agent": True,
        })
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "path_outside_scope", "tool_scope"))

    @PBT
    @given(consistent_pair())
    def test_agent_mismatch(self, pair):
        openapi, allowlist_doc, _ = pair
        allowlist_doc["tools"][0]["requires_agent"] = False  # tool_0 恆為 PUT
        result = self.assert_deterministic(openapi, allowlist_doc)
        self.assertEqual(result, ("error", "agent_requirement_mismatch", "tool_0"))


class RepoArtifactExampleTest(unittest.TestCase):
    """以 repo 的 `openapi.json` ＋ `allowlist.json` 產生成功——證明黑名單檢查在 rename 之後。"""

    def setUp(self):
        self.openapi = json.loads((REPO_ROOT / "openapi.json").read_text(encoding="utf-8"))
        self.allowlist = parse_allowlist(json.loads((BRIDGE_DIR / "allowlist.json").read_text(encoding="utf-8")))

    def test_repo_inputs_generate_three_tools(self):
        specs = generate_tools(self.openapi, self.allowlist)
        by_name = {s.name: s for s in specs}
        self.assertEqual(set(by_name), {"read_requirement_fields", "write_requirement_field",
                                        "clear_requirement_field"})
        for name in ("write_requirement_field", "clear_requirement_field"):
            props = by_name[name].input_schema["properties"]
            self.assertIn("field", props)
            self.assertNotIn("field_key", props)
            self.assertEqual(by_name[name].binding["path_params"]["field"], "field_key")
        self.assertNotIn("on_behalf_of", by_name["write_requirement_field"].input_schema["properties"])
        self.assertEqual(by_name["write_requirement_field"].input_schema["properties"]["value"]["minLength"], 1)
        validate_tool_specs(specs, self.allowlist)

    def test_validate_rejects_hand_edited_specs(self):
        specs = generate_tools(self.openapi, self.allowlist)

        def edited(mutate):
            docs = [s.to_json() for s in specs]
            mutate(docs)
            return tuple(ToolSpec.from_json(d) for d in docs)

        def drop_agent(docs):
            next(d for d in docs if d["name"] == "write_requirement_field")["requires_agent"] = False

        def add_membership(docs):
            next(d for d in docs if d["name"] == "read_requirement_fields")["binding"]["path"] = \
                "/api/membership/projects/{project_id}/members"

        def add_api_key(docs):
            d = next(d for d in docs if d["name"] == "read_requirement_fields")
            d["inputSchema"]["properties"]["api_key"] = {"type": "string"}

        def add_extra(docs):
            d = next(d for d in docs if d["name"] == "read_requirement_fields")
            d["inputSchema"]["properties"]["extra"] = {"type": "string"}

        cases = (
            (drop_agent, "agent_requirement_mismatch", "write_requirement_field"),
            (add_membership, "path_outside_scope", "read_requirement_fields"),
            (add_api_key, "credential_like_property", "read_requirement_fields"),
            (add_extra, "whitelist_mismatch", "read_requirement_fields"),
        )
        for mutate, code, tool in cases:
            with self.subTest(code=code):
                with self.assertRaises(GeneratorError) as ctx:
                    validate_tool_specs(edited(mutate), self.allowlist)
                self.assertEqual((ctx.exception.code, ctx.exception.tool_name), (code, tool))

    def test_dump_is_byte_deterministic(self):
        first = dump_specs(generate_tools(self.openapi, self.allowlist))
        second = dump_specs(generate_tools(reorder(self.openapi), self.allowlist))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
