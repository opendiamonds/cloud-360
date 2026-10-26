"""`U21 mcp-bridge` 其餘純函式（`calls`／`outcomes`／`credentials`／`agents`／`limits`）。

性質六（`BR75.4`）：任意字串作為路徑參數，`validate_arguments` 要嘛拒絕，要嘛以 httpx
`build_request` **實際組出**的 URL 滿足——段數等於樣板段數、前綴等於 allowlist 前綴、不含 `.`／`..`
段、各段解碼後等於參數值。判準是 httpx 組出的 URL，不是計畫字串（審查 R-01：httpx 會正規化
dot-segment）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import json
import os
import unittest
from pathlib import Path
from urllib.parse import unquote

import httpx
from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from mcp_bridge.agents import (
    UNDECLARED, UNREGISTERED, AgentNotDeclared, AgentRegistry, normalize_agent, resolve_agent,
)
from mcp_bridge.calls import (
    MSG_BLANK_VALUE, MSG_UNDECLARED_ARGUMENT, SEGMENT_PATTERN, SYSTEM_ID_PATTERN,
    ArgumentRejected, build_backend_call, validate_arguments,
)
from mcp_bridge.credentials import MAX_AUTHORIZATION_BYTES, RequestCredential, parse_credential
from mcp_bridge.generator import ALLOWED_PATH_PREFIXES, generate_tools, parse_allowlist
from mcp_bridge.limits import (
    BridgeLimits, DEFAULT_MAX_CONCURRENCY, REQUEST_WALL_TIMEOUT_S, derive_allowed_hosts,
)
from mcp_bridge.outcomes import (
    ErrorCode, InternalFailure, MAX_DETAIL_LENGTH, Received, ResponseTooLarge, TransportFailure,
    TransportKind, agent_not_declared, filtered_detail, internal_error, invalid_argument,
    map_outcome, unauthenticated_local, unknown_tool,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_PHASES = (
    (Phase.explicit, Phase.reuse, Phase.generate)
    if os.environ.get("HYPOTHESIS_NO_SHRINK") == "1"
    else (Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink)
)
PBT = settings(max_examples=200, derandomize=True, database=None, deadline=None, phases=_PHASES)

TRICKY = (".", "..", "/", "a/b", "%2e%2e", "%2E%2E", "?", "#", " ", "", "é", "cost\n", "co\nst",
          "\ncost", "sla", "cost", "a" * 64, "a" * 65, "..%2f", "ok_1", "\t", "1", "01")


def repo_specs():
    openapi = json.loads((REPO_ROOT / "openapi.json").read_text(encoding="utf-8"))
    allowlist = parse_allowlist(json.loads(
        (REPO_ROOT / "backend" / "mcp_bridge" / "allowlist.json").read_text(encoding="utf-8")))
    return {s.name: s for s in generate_tools(openapi, allowlist)}


SPECS = repo_specs()
REGISTRY = AgentRegistry.from_mapping({"cost": "cost", "architecture": "architecture"})


class PathSegmentPropertyTest(unittest.TestCase):
    """性質六與 T-4 的單元層。"""

    @PBT
    @given(st.one_of(st.sampled_from(TRICKY), st.text(max_size=12)),
           st.one_of(st.sampled_from(TRICKY), st.text(max_size=12)),
           st.one_of(st.sampled_from(TRICKY), st.text(max_size=6)))
    def test_property_six(self, group, field, system_id):
        spec = SPECS["write_requirement_field"]
        args = {"system_id": system_id, "agent_group": group, "field": field, "value": "v"}
        try:
            accepted = validate_arguments(spec, args)
        except ArgumentRejected:
            return
        call = build_backend_call(spec, accepted, "cost")
        request = httpx.AsyncClient(base_url="http://backend:8000").build_request(call.method, call.path)
        raw = request.url.raw_path.decode("ascii").split("?")[0]
        segments = raw.split("/")
        template = spec.binding["path"].split("/")
        self.assertEqual(len(segments), len(template))
        self.assertTrue(raw.startswith(ALLOWED_PATH_PREFIXES[0]))
        self.assertNotIn(".", segments)
        self.assertNotIn("..", segments)
        values = {"{system_id}": system_id, "{agent_group}": group, "{field_key}": field}
        for seg, tmpl in zip(segments, template):
            self.assertEqual(unquote(seg), values.get(tmpl, tmpl))

    def test_required_dot_segment_inputs_rejected(self):
        """T-4 單元層：`"."`、`".."`、`"a/b"`、`"%2e%2e"`、`"cost\\n"` 皆 invalid_argument。"""
        for name in ("write_requirement_field", "clear_requirement_field"):
            for param in ("agent_group", "field"):
                for bad in (".", "..", "a/b", "%2e%2e", "cost\n"):
                    args = {"system_id": "1", "agent_group": "cost", "field": "sla"}
                    if name == "write_requirement_field":
                        args["value"] = "v"
                    args[param] = bad
                    with self.subTest(tool=name, param=param, value=bad):
                        with self.assertRaises(ArgumentRejected) as ctx:
                            validate_arguments(SPECS[name], args)
                        self.assertNotIn(bad.strip() or "x", ctx.exception.message.replace(param, ""))

    def test_fullmatch_rejects_trailing_newline(self):
        self.assertIsNotNone(SEGMENT_PATTERN.match("cost\n"))  # 這正是 `.match()` 的陷阱
        self.assertIsNone(SEGMENT_PATTERN.fullmatch("cost\n"))
        self.assertIsNone(SYSTEM_ID_PATTERN.fullmatch("1\n"))


class ValidateArgumentsTest(unittest.TestCase):
    def test_undeclared_argument_not_echoed(self):
        with self.assertRaises(ArgumentRejected) as ctx:
            validate_arguments(SPECS["read_requirement_fields"], {"system_id": "1", "evil\nkey": "x"})
        self.assertEqual(ctx.exception.message, MSG_UNDECLARED_ARGUMENT)

    def test_on_behalf_of_argument_rejected(self):
        args = {"system_id": "1", "agent_group": "cost", "field": "sla", "value": "v",
                "on_behalf_of": "architecture"}
        with self.assertRaises(ArgumentRejected):
            validate_arguments(SPECS["write_requirement_field"], args)

    def test_blank_value_rejected_with_hint(self):  # BR74.6
        for blank in ("", "   ", "\t\n"):
            args = {"system_id": "1", "agent_group": "cost", "field": "sla", "value": blank}
            with self.assertRaises(ArgumentRejected) as ctx:
                validate_arguments(SPECS["write_requirement_field"], args)
            self.assertEqual(ctx.exception.message, MSG_BLANK_VALUE)

    def test_non_string_and_missing(self):
        with self.assertRaises(ArgumentRejected):
            validate_arguments(SPECS["read_requirement_fields"], {"system_id": 1})
        with self.assertRaises(ArgumentRejected):
            validate_arguments(SPECS["read_requirement_fields"], {})
        with self.assertRaises(ArgumentRejected):
            validate_arguments(SPECS["read_requirement_fields"], ["1"])

    def test_write_body_injects_registry_group(self):
        spec = SPECS["write_requirement_field"]
        args = validate_arguments(spec, {"system_id": "7", "agent_group": "cost", "field": "sla",
                                         "value": "99.9%"})
        call = build_backend_call(spec, args, "architecture")
        self.assertEqual(call.method, "PUT")
        self.assertEqual(call.path, "/api/requirements/systems/7/fields/cost/sla")
        self.assertEqual(call.json_body, {"value": "99.9%", "on_behalf_of": "architecture"})

    def test_clear_has_no_body_and_read_has_no_body(self):
        spec = SPECS["clear_requirement_field"]
        call = build_backend_call(spec, validate_arguments(
            spec, {"system_id": "7", "agent_group": "cost", "field": "sla"}), "cost")
        self.assertEqual((call.method, call.json_body), ("DELETE", None))
        spec = SPECS["read_requirement_fields"]
        call = build_backend_call(spec, validate_arguments(spec, {"system_id": "7"}), None)
        self.assertEqual((call.method, call.path, call.json_body),
                         ("GET", "/api/requirements/systems/7/fields", None))


class MapOutcomeTest(unittest.TestCase):
    """`BR76.1` 封閉表逐列。"""

    def test_closed_table_rows(self):
        rows = [
            (Received(200, b'{"a": 1}'), True, None, False),
            (Received(401, b'{"detail": "x"}'), False, ErrorCode.UNAUTHENTICATED, False),
            (Received(403, b'{"detail": "no"}'), False, ErrorCode.FORBIDDEN, False),
            (Received(404, b'{"detail": "no"}'), False, ErrorCode.NOT_FOUND, False),
            (Received(422, b'{"detail": "no"}'), False, ErrorCode.INVALID_ARGUMENT, False),
            (Received(500, b"boom"), False, ErrorCode.BACKEND_UNAVAILABLE, True),
            (Received(502, b""), False, ErrorCode.BACKEND_UNAVAILABLE, True),
            (Received(503, b""), False, ErrorCode.BACKEND_UNAVAILABLE, True),
            (Received(418, b"{}"), False, ErrorCode.INTERNAL_ERROR, False),
            (Received(302, b""), False, ErrorCode.INTERNAL_ERROR, False),
            (Received(200, b"not json"), False, ErrorCode.INTERNAL_ERROR, False),
            (Received(200, b"[1, 2]"), False, ErrorCode.INTERNAL_ERROR, False),
            (ResponseTooLarge(), False, ErrorCode.INTERNAL_ERROR, False),
            (InternalFailure(), False, ErrorCode.INTERNAL_ERROR, False),
        ]
        for result, ok, code, retryable in rows:
            with self.subTest(result=result):
                out = map_outcome(result)
                self.assertEqual(out.ok, ok)
                self.assertEqual(out.error, code)
                self.assertEqual(out.retryable, retryable)

    def test_transport_kind_is_exactly_four_values(self):
        self.assertEqual({k.value for k in TransportKind}, {"refused", "timeout", "dns", "protocol"})
        for kind in TransportKind:
            out = map_outcome(TransportFailure(kind))
            self.assertEqual((out.error, out.retryable, out.http_status),
                             (ErrorCode.BACKEND_UNAVAILABLE, True, None))

    def test_seven_error_codes(self):
        self.assertEqual(len(ErrorCode), 7)

    def test_local_constructors(self):
        self.assertEqual(unauthenticated_local().error, ErrorCode.UNAUTHENTICATED)
        self.assertEqual(agent_not_declared().error, ErrorCode.AGENT_NOT_DECLARED)
        self.assertEqual(invalid_argument("參數不合格：field").error, ErrorCode.INVALID_ARGUMENT)
        self.assertTrue(unknown_tool().unknown_tool)
        self.assertEqual(internal_error().error_document(),
                         {"error": "internal_error", "message": "轉接層內部錯誤", "retryable": False})


class DetailFilterTest(unittest.TestCase):
    """`BR76.2`：通過與退回。"""

    def test_passes_exact_detail(self):
        self.assertEqual(filtered_detail(b'{"detail": "not a member"}'), "not a member")
        out = map_outcome(Received(403, json.dumps({"detail": "非專案成員"}).encode()))
        self.assertEqual(out.message, "非專案成員")

    def test_rejections_fall_back_to_fixed_text(self):
        bad = [
            b'{"detail": "x", "extra": 1}',                     # 多鍵
            b'{"detail": ["x"]}',                               # 非字串
            json.dumps({"detail": "y" * (MAX_DETAIL_LENGTH + 1)}).encode(),  # 超長
            json.dumps({"detail": "a\nb"}).encode(),            # 控制字元
            json.dumps({"detail": "a\x00b"}).encode(),
            b"not json",
            b'{"detail": ""}',
        ]
        for body in bad:
            with self.subTest(body=body[:30]):
                self.assertIsNone(filtered_detail(body))
                self.assertEqual(map_outcome(Received(404, body)).message, "找不到指定的資源")


class CredentialTest(unittest.TestCase):
    def test_valid(self):
        cred = parse_credential(("Bearer abc.DEF-123_~+/=",))
        self.assertIsNotNone(cred)
        self.assertEqual(repr(cred), "<redacted>")
        self.assertEqual(str(cred), "<redacted>")
        self.assertNotIn("abc", f"{cred!r} {cred}")

    def test_rejections(self):
        cases = [
            (),                                              # 缺漏
            ("Bearer a", "Bearer b"),                        # 多值
            ("Basic abc",),                                  # 非 Bearer
            ("Bearer ",),                                    # 空 token
            ("Bearer a b",),                                 # 含空白
            ("Bearer a\nb",),
            ("Bearer " + "a" * (MAX_AUTHORIZATION_BYTES - 6),),  # 超過 8192 位元組
        ]
        for values in cases:
            with self.subTest(values=[v[:12] for v in values]):
                self.assertIsNone(parse_credential(values))
        self.assertIsNotNone(parse_credential(("Bearer " + "a" * (MAX_AUTHORIZATION_BYTES - 7),)))

    def test_not_picklable(self):
        import pickle
        with self.assertRaises(TypeError):
            pickle.dumps(RequestCredential(raw="Bearer x"))


class AgentTest(unittest.TestCase):
    def test_read_does_not_require_agent(self):
        res = resolve_agent((), REGISTRY, requires_agent=False)
        self.assertEqual((res.group, res.log_name), (None, UNDECLARED))

    def test_write_requires_registered_agent(self):
        with self.assertRaises(AgentNotDeclared):
            resolve_agent((), REGISTRY, requires_agent=True)
        with self.assertRaises(AgentNotDeclared):
            resolve_agent(("rogue",), REGISTRY, requires_agent=True)
        with self.assertRaises(AgentNotDeclared):
            resolve_agent(("cost", "cost"), REGISTRY, requires_agent=True)
        res = resolve_agent(("cost",), REGISTRY, requires_agent=True)
        self.assertEqual((res.group, res.log_name), ("cost", "cost"))

    def test_log_name_never_echoes_raw_value(self):
        self.assertEqual(normalize_agent(("evil\nINJECTED",), REGISTRY), UNREGISTERED)
        self.assertEqual(normalize_agent((), REGISTRY), UNDECLARED)

    def test_registry_validation(self):
        with self.assertRaises(ValueError):
            AgentRegistry.from_mapping({"Bad Name": "cost"})
        with self.assertRaises(ValueError) as ctx:
            AgentRegistry.from_mapping({"cost": "../x"})
        self.assertEqual(str(ctx.exception), "cost")


class LimitsTest(unittest.TestCase):
    def test_default_port_hosts(self):
        self.assertEqual(derive_allowed_hosts(8080),
                         ("mcp-bridge:8080", "localhost:8080", "127.0.0.1:8080"))

    def test_non_default_port_hosts(self):
        self.assertEqual(derive_allowed_hosts(18080),
                         ("mcp-bridge:18080", "localhost:18080", "127.0.0.1:18080"))
        with self.assertRaises(ValueError):
            derive_allowed_hosts(0)

    def test_defaults_and_relationship(self):
        limits = BridgeLimits()
        self.assertEqual(limits.max_concurrency, DEFAULT_MAX_CONCURRENCY)
        self.assertEqual(limits.max_concurrency, 16)
        # 程式審查 R-02：牆鐘必須**嚴格大於**本體期限＋backend 整體上限（留 1 秒給 SDK 序列化與回應），
        # 且牆鐘＋1 < stop_grace_period 的 15 秒。
        self.assertGreater(limits.request_wall_timeout_s,
                           limits.overall_timeout_s + limits.body_read_timeout_s)
        self.assertGreaterEqual(limits.request_wall_timeout_s,
                                limits.overall_timeout_s + limits.body_read_timeout_s + 1)
        self.assertLess(REQUEST_WALL_TIMEOUT_S + 1, 15)
        with self.assertRaises(ValueError):
            BridgeLimits(max_concurrency=0)


if __name__ == "__main__":
    unittest.main()
