"""`U21 mcp-bridge` 驗證拓樸的自測（`BR78.1`、`BR78.2`；不依賴正式的三份檔）。

以替身工具宣告（由一份最小 openapi ＋ allowlist 產生）與替身 backend 驗證：拓樸可起、兩種協定版本的
官方 SDK client 都能 `list_tools` 與 `call_tool`、Host 依實際埠推導、`LogSource` 讀得到啟動紀錄、
前置條件缺失時是 `AssertionError`（不是 skip）、逾時是 `AssertionError`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import asyncio
import json
import unittest
from unittest import mock

import httpx

from mcp_bridge.agents import AgentRegistry
from mcp_bridge.generator import generate_tools, parse_allowlist
from tests import mcp_topology
from tests.mcp_test_client import MODES, SdkClientPort
from tests.mcp_topology import BridgeTopology, bounded

TOKEN = "Bearer topology.self.test"
OPENAPI = {"paths": {"/api/requirements/echo/{item_id}": {"get": {
    "parameters": [{"in": "path", "name": "item_id", "required": True, "schema": {"type": "string"}}],
    "security": [{"HTTPBearer": []}]}}}}
ALLOWLIST = {"version": 1, "tools": [{
    "name": "echo_item", "method": "GET", "path": "/api/requirements/echo/{item_id}",
    "description": "替身工具", "properties": ["item_id"],
    "property_descriptions": {"item_id": "替身"}, "requires_agent": False}]}


async def fake_backend(scope, receive, send):
    if scope["type"] != "http":
        return
    body = json.dumps({"path": scope["path"]}).encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


def topology():
    specs = generate_tools(OPENAPI, parse_allowlist(ALLOWLIST))
    return BridgeTopology(backend_app=fake_backend, tool_specs=specs,
                          registry=AgentRegistry.from_mapping({"cost": "cost"}))


class TopologySelfTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mcp_topology.preserve_logging(self)

    @bounded
    async def test_topology_serves_both_protocol_versions(self):
        async with topology() as topo:
            for mode in MODES:
                with self.subTest(mode=mode):
                    async with SdkClientPort(topo.url, mode).session(token=TOKEN) as session:
                        expected = "2026-07-28" if mode == "auto" else "2025-11-25"
                        self.assertEqual(session.protocol_version, expected)
                        tools = await session.list_tools()
                        self.assertEqual([t["name"] for t in tools], ["echo_item"])
                        result = await session.call_tool("echo_item", {"item_id": "abc"})
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured, {"path": "/api/requirements/echo/abc"})
            self.assertEqual([r.authorization for r in topo.recorder.records], [TOKEN, TOKEN])

    @bounded
    async def test_host_derived_from_actual_port_and_startup_logged(self):
        async with topology() as topo:
            self.assertIn(f"startup port={topo.port} tools=1", topo.logs.text())
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            headers = {"content-type": "application/json",
                       "accept": "application/json, text/event-stream"}
            async with httpx.AsyncClient(timeout=10) as client:
                ok = await client.post(topo.url, json=body, headers=headers)
                evil = await client.post(topo.url, json=body, headers=dict(headers, host="evil.example"))
                stale = await client.post(topo.url, json=body,
                                          headers=dict(headers, host="127.0.0.1:8080"))
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(evil.status_code, 421)
            if topo.port != 8080:
                self.assertEqual(stale.status_code, 421)

    def test_missing_prerequisite_is_assertion_error(self):
        with mock.patch.object(mcp_topology.importlib.metadata, "version", return_value="1.29.0"):
            with self.assertRaises(AssertionError) as ctx:
                mcp_topology.assert_prerequisites()
        self.assertIn("pip install -r requirements.txt", str(ctx.exception))

        def missing(_name):
            raise mcp_topology.importlib.metadata.PackageNotFoundError("mcp")

        with mock.patch.object(mcp_topology.importlib.metadata, "version", side_effect=missing):
            with self.assertRaises(AssertionError):
                mcp_topology.assert_prerequisites()

    async def test_bounded_turns_timeout_into_assertion(self):
        async def slow(_self):
            await asyncio.sleep(5)

        with mock.patch.object(mcp_topology, "CASE_TIMEOUT_S", 0.05):
            with self.assertRaises(AssertionError):
                await bounded(slow)(self)

    def test_route_constant(self):
        self.assertEqual(mcp_topology.MCP_ROUTE, "same-interpreter")


if __name__ == "__main__":
    unittest.main()
