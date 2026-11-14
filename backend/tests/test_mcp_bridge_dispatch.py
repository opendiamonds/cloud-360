"""`U21 mcp-bridge` 的 `run_tool_call` 與 `executor`（`BR76.1`、`BR77.1`、`BR77.2`、`NFR21.14`、`NFR21.22`、`NFR21.26`、`NFR21.29`）。

全部在主直譯器以替身驅動，不需要 `mcp`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import io
import json
import logging
import unittest
from pathlib import Path

import httpx

from mcp_bridge.agents import AgentRegistry
from mcp_bridge.calls import BackendCall
from mcp_bridge.credentials import RequestCredential
from mcp_bridge.dispatch import run_tool_call
from mcp_bridge.executor import build_backend_client, classify_transport_error, exchange, read_bounded
from mcp_bridge.generator import generate_tools, parse_allowlist
from mcp_bridge.limits import BridgeLimits
from mcp_bridge.observability import LOGGER_NAME, BridgeFormatter, configure_logging
from tests.mcp_topology import preserve_logging
from mcp_bridge.outcomes import (
    ErrorCode, InternalFailure, Received, ResponseTooLarge, TransportFailure, TransportKind,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = AgentRegistry.from_mapping({"cost": "cost", "architecture": "architecture"})
TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1In0.SIGNATUREsegmentXYZ123"


def repo_specs():
    openapi = json.loads((REPO_ROOT / "openapi.json").read_text(encoding="utf-8"))
    allowlist = parse_allowlist(json.loads(
        (REPO_ROOT / "backend" / "mcp_bridge" / "allowlist.json").read_text(encoding="utf-8")))
    return {s.name: s for s in generate_tools(openapi, allowlist)}


SPECS = repo_specs()
WRITE_ARGS = {"system_id": "1", "agent_group": "cost", "field": "sla", "value": "99.9%"}


class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(BridgeFormatter())
        self.records = []
        self.lines = []

    def emit(self, record):
        self.records.append(record)
        self.lines.append(self.format(record))

    def tool_calls(self):
        return [r for r in self.records if getattr(r, "event", None) == "tool_call"]


class DispatchTestBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        preserve_logging(self)
        configure_logging(stream=io.StringIO())
        self.capture = LogCapture()
        logging.getLogger().addHandler(self.capture)
        self.addCleanup(logging.getLogger().removeHandler, self.capture)

    async def run_call(self, name, args, *, auth=(TOKEN,), agent=("cost",), result=None, exc=None):
        sent = []

        async def fake_exchange(call, credential):
            sent.append((call, credential))
            if exc is not None:
                raise exc
            return result if result is not None else Received(200, b'{"ok": true}')

        outcome = await run_tool_call(SPECS.get(name), args, auth, agent, fake_exchange,
                                      registry=REGISTRY)
        return outcome, sent


class RunToolCallTest(DispatchTestBase):
    async def test_each_branch_writes_exactly_one_line(self):
        branches = [
            ("unknown tool", dict(name="nope", args={})),
            ("unauthenticated", dict(name="read_requirement_fields", args={"system_id": "1"}, auth=())),
            ("agent", dict(name="write_requirement_field", args=WRITE_ARGS, agent=())),
            ("invalid", dict(name="write_requirement_field", args=dict(WRITE_ARGS, field=".."))),
            ("ok", dict(name="write_requirement_field", args=WRITE_ARGS)),
            ("403", dict(name="read_requirement_fields", args={"system_id": "1"},
                         result=Received(403, b'{"detail":"x"}'))),
            ("transport", dict(name="read_requirement_fields", args={"system_id": "1"},
                               result=TransportFailure(TransportKind.REFUSED))),
            ("too large", dict(name="read_requirement_fields", args={"system_id": "1"},
                               result=ResponseTooLarge())),
            ("crash", dict(name="read_requirement_fields", args={"system_id": "1"},
                           exc=RuntimeError("SECRET-MARKER"))),
        ]
        for label, kwargs in branches:
            with self.subTest(branch=label):
                before = len(self.capture.tool_calls())
                await self.run_call(kwargs.pop("name"), kwargs.pop("args"), **kwargs)
                self.assertEqual(len(self.capture.tool_calls()) - before, 1)

    async def test_local_rejections_never_call_backend(self):
        cases = [
            ("read_requirement_fields", {"system_id": "1"}, dict(auth=()), ErrorCode.UNAUTHENTICATED),
            ("read_requirement_fields", {"system_id": "1"}, dict(auth=("Basic x",)), ErrorCode.UNAUTHENTICATED),
            ("write_requirement_field", WRITE_ARGS, dict(agent=()), ErrorCode.AGENT_NOT_DECLARED),
            ("write_requirement_field", WRITE_ARGS, dict(agent=("rogue",)), ErrorCode.AGENT_NOT_DECLARED),
            ("clear_requirement_field", {"system_id": "1", "agent_group": "cost", "field": "sla"},
             dict(agent=()), ErrorCode.AGENT_NOT_DECLARED),
            ("write_requirement_field", dict(WRITE_ARGS, value="  "), {}, ErrorCode.INVALID_ARGUMENT),
            ("read_requirement_fields", {"system_id": "1", "extra": "x"}, {}, ErrorCode.INVALID_ARGUMENT),
        ]
        for name, args, kwargs, code in cases:
            with self.subTest(name=name, code=code):
                outcome, sent = await self.run_call(name, args, **kwargs)
                self.assertEqual(outcome.error, code)
                self.assertEqual(sent, [])

    async def test_secret_marker_not_in_result_or_log(self):  # NFR21.29
        outcome, _ = await self.run_call("read_requirement_fields", {"system_id": "1"},
                                         exc=RuntimeError("SECRET-MARKER"))
        self.assertEqual(outcome.error, ErrorCode.INTERNAL_ERROR)
        self.assertNotIn("SECRET-MARKER", json.dumps(outcome.error_document(), ensure_ascii=False))
        self.assertNotIn("SECRET-MARKER", "\n".join(self.capture.lines))
        self.assertTrue(any("exc_type=RuntimeError" in line for line in self.capture.lines))
        outcome, _ = await self.run_call("read_requirement_fields", {"system_id": "1"})
        self.assertTrue(outcome.ok)

    async def test_unknown_tool_logged_as_unknown_without_injection(self):
        outcome = await run_tool_call(None, {}, (TOKEN,), (), None, registry=REGISTRY,
                                      requested_name="evil\nINJECTED")
        self.assertTrue(outcome.unknown_tool)
        fields = self.capture.tool_calls()[-1].fields
        self.assertEqual((fields["tool"], fields["outcome"]), ("unknown", "invalid_argument"))
        self.assertNotIn("INJECTED", "\n".join(self.capture.lines))

    async def test_agent_header_injection_normalized(self):
        await self.run_call("read_requirement_fields", {"system_id": "1"}, agent=("evil\nINJECTED",))
        self.assertEqual(self.capture.tool_calls()[-1].fields["agent"], "unregistered")
        self.assertNotIn("INJECTED", "\n".join(self.capture.lines))

    async def test_token_never_logged_and_write_body_shape(self):
        outcome, sent = await self.run_call("write_requirement_field", WRITE_ARGS, agent=("architecture",))
        self.assertTrue(outcome.ok)
        call, credential = sent[0]
        self.assertEqual(call.json_body, {"value": "99.9%", "on_behalf_of": "architecture"})
        self.assertEqual(credential.raw, TOKEN)
        text = "\n".join(self.capture.lines)
        self.assertNotIn(TOKEN.split()[1], text)
        self.assertNotIn("99.9%", text)
        line = self.capture.tool_calls()[-1].getMessage()
        self.assertRegex(line, r"^tool_call tool=write_requirement_field agent=architecture outcome=ok "
                               r"http_status=200 duration_ms=\d+$")


class ExecutorTest(unittest.IsolatedAsyncioTestCase):
    CALL = BackendCall(method="GET", path="/api/requirements/systems/1/fields", json_body=None)
    CRED = RequestCredential(raw=TOKEN)

    def client(self, handler, **limits):
        client = build_backend_client("http://backend:8000", BridgeLimits(**limits),
                                      transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return client

    async def test_classification_table(self):
        request = httpx.Request("GET", "http://backend:8000/")
        cases = [
            (httpx.ConnectError("refused", request=request), TransportKind.REFUSED),
            (httpx.ReadTimeout("t", request=request), TransportKind.TIMEOUT),
            (httpx.PoolTimeout("t", request=request), TransportKind.TIMEOUT),
            (httpx.ConnectTimeout("t", request=request), TransportKind.TIMEOUT),
            (TimeoutError(), TransportKind.TIMEOUT),
            (httpx.RemoteProtocolError("p", request=request), TransportKind.PROTOCOL),
            (httpx.ReadError("r", request=request), TransportKind.PROTOCOL),
        ]
        for exc, kind in cases:
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(classify_transport_error(exc), TransportFailure(kind))
        self.assertIsNone(classify_transport_error(ValueError("x")))

    async def test_dns_failure_classified_from_real_resolution(self):  # K-10
        client = build_backend_client("http://backend.invalid:8000", BridgeLimits())
        self.addAsyncCleanup(client.aclose)
        result = await exchange(client, self.CALL, self.CRED, BridgeLimits())
        self.assertEqual(result, TransportFailure(TransportKind.DNS))

    async def test_unexpected_exception_is_internal_failure(self):
        def handler(request):
            raise ValueError("boom")
        self.assertEqual(await exchange(self.client(handler), self.CALL, self.CRED, BridgeLimits()),
                         InternalFailure())

    async def test_read_bounded_stops_on_large_stream(self):
        produced = []

        async def stream():
            for _ in range(32):  # 32 × 64 KiB = 2 MiB
                produced.append(1)
                yield b"x" * 65536

        def handler(request):
            return httpx.Response(200, content=stream())

        result = await exchange(self.client(handler), self.CALL, self.CRED, BridgeLimits())
        self.assertEqual(result, ResponseTooLarge())
        self.assertLess(len(produced), 32)

    async def test_declared_content_length_over_limit_not_read(self):
        def handler(request):
            return httpx.Response(200, content=b"y" * 2048, headers={"content-length": "2048"})
        response = httpx.Response(200, content=b"y" * 2048)
        self.assertIsNone(await read_bounded(response, 1024))
        result = await exchange(self.client(handler), self.CALL, self.CRED,
                                BridgeLimits(max_response_body_bytes=1024))
        self.assertEqual(result, ResponseTooLarge())

    async def test_set_cookie_never_stored_or_sent(self):  # NFR21.14
        seen_cookies = []

        def handler(request):
            seen_cookies.append(request.headers.get("cookie"))
            return httpx.Response(200, json={"a": 1}, headers={"set-cookie": "session=LEAK; Path=/"})

        client = self.client(handler)
        for _ in range(3):
            self.assertIsInstance(await exchange(client, self.CALL, self.CRED, BridgeLimits()), Received)
        self.assertEqual(seen_cookies, [None, None, None])
        self.assertEqual(len(client.cookies.jar), 0)

    async def test_authorization_only_from_credential_and_no_redirect(self):
        seen = []

        def handler(request):
            seen.append(dict(request.headers))
            return httpx.Response(302, headers={"location": "http://evil.example/"})

        result = await exchange(self.client(handler), self.CALL, self.CRED, BridgeLimits())
        self.assertEqual(result.status, 302)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["authorization"], TOKEN)
        self.assertNotIn("x-cloud360-agent", seen[0])


if __name__ == "__main__":
    unittest.main()
