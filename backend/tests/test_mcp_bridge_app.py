"""`U21 mcp-bridge` 的 `create_app`（`BR78.3`、`BR71.2`、`BR71.3`、`BR71.6`、`BR73.1`、`BR76.3`）。

以 `httpx.ASGITransport` 直接驅動 `create_app`，backend 是回固定內容的替身。兩種協定版本都測：
舊式 handshake（`2025-06-18`，或不帶版本標頭）與現代（`2026-07-28`，官方 client 預設走這條）——
Step 1 實測兩者的錯誤狀態碼與例外外洩行為不同（S-3、S-9）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import io
import json
import unittest
from pathlib import Path
from unittest import mock

import httpx

from mcp_bridge.agents import AgentRegistry
from mcp_bridge.executor import build_backend_client
from mcp_bridge.generator import generate_tools, parse_allowlist
from mcp_bridge.limits import derive_allowed_hosts
from mcp_bridge.observability import configure_logging
from tests.mcp_topology import assert_prerequisites, preserve_logging

REPO_ROOT = Path(__file__).resolve().parents[2]
TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1In0.APPTESTsignature"
LEGACY = "2025-06-18"
MODERN = "2026-07-28"
PORT = 8080
HOST = f"127.0.0.1:{PORT}"


def repo_specs():
    openapi = json.loads((REPO_ROOT / "openapi.json").read_text(encoding="utf-8"))
    allowlist = parse_allowlist(json.loads(
        (REPO_ROOT / "backend" / "mcp_bridge" / "allowlist.json").read_text(encoding="utf-8")))
    return generate_tools(openapi, allowlist)


class FakeBackend:
    def __init__(self):
        self.requests = []

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return
        headers = {k.decode(): v.decode() for k, v in scope["headers"]}
        self.requests.append((scope["method"], scope["path"], headers.get("authorization")))
        body = json.dumps({"system_id": 1, "unfilled_count": 0, "input_hint": "", "groups": []}).encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})


def rpc(method, params=None, *, era=LEGACY, req_id=1):
    body = {"jsonrpc": "2.0", "id": req_id, "method": method}
    params = dict(params or {})
    headers = {"content-type": "application/json", "accept": "application/json, text/event-stream",
               "host": HOST}
    if era == MODERN:
        params["_meta"] = {
            "io.modelcontextprotocol/protocolVersion": MODERN,
            "io.modelcontextprotocol/clientInfo": {"name": "t", "version": "0"},
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        headers["mcp-protocol-version"] = MODERN
        headers["mcp-method"] = method
        if method == "tools/call":
            headers["mcp-name"] = params["name"]
    elif era is not None:
        headers["mcp-protocol-version"] = era
    if params:
        body["params"] = params
    return body, headers


def with_running(test):
    """session manager 的 task group 必須在同一個 task 內進出（anyio），故每個測試自己包住。"""
    import functools

    @functools.wraps(test)
    async def wrapper(self):
        async with self.app.running():
            await test(self)
    return wrapper


class CreateAppTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 缺 mcp 或版本不對時以 AssertionError 指出安裝指令（不是 skip，也不是讓整個執行中止的 import 失敗）；
        # 含 mcp 的 app 模組因此在這裡才載入。
        assert_prerequisites()
        from mcp_bridge.app import create_app
        preserve_logging(self)
        self.log_stream = io.StringIO()
        configure_logging(stream=self.log_stream)
        self.backend = FakeBackend()
        backend_client = build_backend_client("http://backend:8000",
                                              transport=httpx.ASGITransport(app=self.backend))
        self.addAsyncCleanup(backend_client.aclose)
        self.app = create_app(backend_client=backend_client,
                              registry=AgentRegistry.from_mapping({"cost": "cost"}),
                              tool_specs=repo_specs(), allowed_hosts=derive_allowed_hosts(PORT))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                        base_url=f"http://{HOST}", timeout=10)
        self.addAsyncCleanup(self.client.aclose)

    async def post(self, method, params=None, *, era=LEGACY, extra=None):
        body, headers = rpc(method, params, era=era)
        headers.update(extra or {})
        return await self.client.post("/mcp", json=body, headers=headers)

    @with_running
    async def test_list_tools_without_auth_and_without_binding(self):
        for era in (None, LEGACY, MODERN):
            with self.subTest(era=era):
                if era != MODERN:
                    init = await self.post("initialize", {
                        "protocolVersion": LEGACY, "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"}}, era=era)
                    self.assertEqual(init.status_code, 200)
                response = await self.post("tools/list", era=era)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "application/json")
                self.assertNotIn("mcp-session-id", response.headers)
                tools = response.json()["result"]["tools"]
                self.assertEqual({t["name"] for t in tools}, {
                    "read_requirement_fields", "write_requirement_field", "clear_requirement_field"})
                for tool in tools:
                    self.assertEqual(set(tool) - {"title", "annotations", "icons"},
                                     {"name", "description", "inputSchema"})
                    self.assertNotIn("binding", json.dumps(tool))
        self.assertEqual(self.backend.requests, [])

    @with_running
    async def test_call_without_authorization_is_unauthenticated(self):
        for era in (LEGACY, MODERN):
            with self.subTest(era=era):
                response = await self.post("tools/call", {"name": "read_requirement_fields",
                                                          "arguments": {"system_id": "1"}}, era=era)
                result = response.json()["result"]
                self.assertTrue(result["isError"])
                self.assertEqual(result["structuredContent"]["error"], "unauthenticated")
        self.assertEqual(self.backend.requests, [])

    @with_running
    async def test_success_returns_backend_body(self):
        for era in (LEGACY, MODERN):
            with self.subTest(era=era):
                response = await self.post("tools/call", {"name": "read_requirement_fields",
                                                          "arguments": {"system_id": "1"}},
                                           era=era, extra={"authorization": TOKEN})
                result = response.json()["result"]
                self.assertFalse(result["isError"])
                self.assertEqual(result["structuredContent"]["system_id"], 1)
                self.assertNotIn(TOKEN.split()[1], response.text)
        self.assertEqual([r[2] for r in self.backend.requests], [TOKEN, TOKEN])

    @with_running
    async def test_host_not_allowed_is_rejected(self):
        for era in (LEGACY, MODERN):
            with self.subTest(era=era):
                response = await self.post("tools/list", era=era, extra={"host": "evil.example"})
                self.assertEqual(response.status_code, 421)

    @with_running
    async def test_unknown_tool_is_protocol_error_without_echo(self):  # 17-A
        expected_status = {LEGACY: 200, MODERN: 400}
        for era in (LEGACY, MODERN):
            with self.subTest(era=era):
                response = await self.post("tools/call", {"name": "steal_SECRETNAME", "arguments": {}},
                                           era=era, extra={"authorization": TOKEN})
                self.assertEqual(response.status_code, expected_status[era])
                document = response.json()
                self.assertNotIn("result", document)
                self.assertEqual(document["error"]["code"], -32602)
                self.assertEqual(document["error"]["message"], "Unknown tool")
                self.assertNotIn("SECRETNAME", response.text)
                self.assertNotIn("SECRETNAME", self.log_stream.getvalue())

    @with_running
    async def test_no_exception_reaches_the_sdk(self):
        with mock.patch("mcp_bridge.calls.build_backend_call",
                        side_effect=RuntimeError("SECRET-LEAK-" + TOKEN)):
            for era in (LEGACY, MODERN):
                with self.subTest(era=era):
                    response = await self.post("tools/call", {"name": "read_requirement_fields",
                                                              "arguments": {"system_id": "1"}},
                                               era=era, extra={"authorization": TOKEN})
                    self.assertEqual(response.status_code, 200)
                    result = response.json()["result"]
                    self.assertTrue(result["isError"])
                    self.assertEqual(result["structuredContent"],
                                     {"error": "internal_error", "message": "轉接層內部錯誤",
                                      "retryable": False})
                    self.assertNotIn("SECRET-LEAK", response.text)

    @with_running
    async def test_healthz_fixed_body(self):
        response = await self.client.get("/healthz")
        self.assertEqual((response.status_code, response.json()), (200, {"status": "ok"}))
        response = await self.client.get("/healthz", headers={"host": "evil.example"})
        self.assertEqual(response.status_code, 200)


    @with_running
    async def test_result_serialization_failure_is_internal_error(self):  # 程式審查 R-05
        with mock.patch("mcp_bridge.app.to_call_tool_result",
                        side_effect=RuntimeError("SECRET-SER-" + TOKEN)):
            for era in (LEGACY, MODERN):
                with self.subTest(era=era):
                    response = await self.post("tools/call", {"name": "read_requirement_fields",
                                                              "arguments": {"system_id": "1"}},
                                               era=era, extra={"authorization": TOKEN})
                    self.assertEqual(response.status_code, 200)
                    result = response.json()["result"]
                    self.assertTrue(result["isError"])
                    self.assertEqual(result["structuredContent"]["error"], "internal_error")
                    self.assertNotIn("SECRET-SER", response.text)
                    self.assertNotIn("SECRET-SER", self.log_stream.getvalue())
        self.assertIn("internal_failure exc_type=RuntimeError", self.log_stream.getvalue())


class LifespanFailureTest(unittest.IsolatedAsyncioTestCase):  # 程式審查 R-04
    async def asyncSetUp(self):
        assert_prerequisites()
        preserve_logging(self)
        self.log_stream = io.StringIO()
        configure_logging(stream=self.log_stream)

    @staticmethod
    async def failing_lifespan_app(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.failed", "message": "boom"})

    async def test_serve_until_stopped_reports_failure(self):
        from mcp_bridge.server import bind_socket, build_uvicorn_server, serve_until_stopped
        sock = bind_socket("127.0.0.1", 0)
        started = await serve_until_stopped(build_uvicorn_server(self.failing_lifespan_app), sock, tools=3)
        self.assertFalse(started)
        self.assertIn('startup_failed subject="lifespan"', self.log_stream.getvalue())
        self.assertNotIn("startup port=", self.log_stream.getvalue())

    async def test_run_returns_non_zero_on_lifespan_failure(self):
        import argparse
        from mcp_bridge import server
        from mcp_bridge.startup import load_and_validate
        args = argparse.Namespace(backend_url="http://backend:8000", host="127.0.0.1", port=0,
                                  max_concurrency=16)
        with mock.patch.object(server, "create_app", return_value=self.failing_lifespan_app):
            self.assertEqual(await server._run(load_and_validate(), args), 1)


if __name__ == "__main__":
    unittest.main()
