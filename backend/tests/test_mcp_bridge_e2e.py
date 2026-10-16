"""`U21 mcp-bridge` 端到端（`AC11.4.1`–`AC11.4.3`；T-1、T-2、T-4；`BR78.2`、`BR78.4`、`BR78.5`）。

拓樸（路線 A）：官方 SDK client → 真實 HTTP → bridge（uvicorn）→ `ASGITransport` → 記錄包裝 → 真實 `main.app`
（`get_current_user`、facade 授權、SQLite 測試資料庫）。**授權不 mock**；token 以 backend 的
`create_access_token` 簽發。兩種協定版本（`legacy`、`auto`＝現代）都跑（Step 1 中途關卡調整 1）。

資料庫：沿用 `RequirementFieldFixture`（同一個 in-memory SQLite）。並發的 backend 請求跑在執行緒池裡，而
SQLAlchemy 的 `Session` 不是執行緒安全的，所以 `get_db` 覆寫以一把鎖讓 backend 端**逐一**使用 session——
這只序列化 backend 內部的 DB 存取；bridge 端的請求交錯（T-1 要驗的東西）不受影響。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import json
import threading
import unittest
from unittest import mock

import httpx

from database import get_db
from main import app as backend_app
from mcp_bridge.limits import BridgeLimits
from mcp_bridge.startup import load_and_validate
from models import SystemRequirementField
from services.auth import create_access_token
from services.hierarchy_facade import HierarchyFacade, mint_principal
from tests.helpers import ALWAYS_VISIBLE, close_session
from tests.mcp_test_client import MODES, SdkClientPort
from tests.mcp_topology import BridgeTopology, CallHookBarrier, bounded, preserve_logging
from tests.test_requirement_field_facade import RequirementFieldFixture

CONFIG = load_and_validate()
EXPECTED_WHITELIST = {  # AC11.4.2：測試檔內的字面值，不讀 allowlist.json
    "read_requirement_fields": {"system_id"},
    "write_requirement_field": {"system_id", "agent_group", "field", "value"},
    "clear_requirement_field": {"system_id", "agent_group", "field"},
}
BLACKLIST = ("token", "key", "secret", "authorization")


def all_property_names(schema):
    names = []
    if isinstance(schema, dict):
        for key, sub in (schema.get("properties") or {}).items():
            names.append(key)
            names.extend(all_property_names(sub))
        for key in ("items", "additionalProperties"):
            names.extend(all_property_names(schema.get(key)))
        for key in ("anyOf", "oneOf", "allOf"):
            for sub in schema.get(key) or []:
                names.extend(all_property_names(sub))
    return names


class E2EBase(RequirementFieldFixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        preserve_logging(self)
        self.build_fixture()
        self.system2 = HierarchyFacade(self.db).create_system(
            mint_principal(self.outsider), project_id=self.other_project.id, name="S2",
            project_visible=ALWAYS_VISIBLE)
        self.db.commit()
        self.owner_token = "Bearer " + create_access_token({"sub": self.owner.username})
        self.outsider_token = "Bearer " + create_access_token({"sub": self.outsider.username})
        lock = threading.Lock()

        def locked_db():
            with lock:
                yield self.db

        backend_app.dependency_overrides[get_db] = locked_db

    def tearDown(self):
        backend_app.dependency_overrides.clear()
        close_session(self.db)

    def topology(self, **kwargs):
        return BridgeTopology(backend_app=backend_app, tool_specs=CONFIG.tool_specs,
                              registry=CONFIG.registry, **kwargs)

    async def call(self, topo, mode, name, args, *, token=None, agent=None):
        async with SdkClientPort(topo.url, mode).session(token=token, agent=agent) as session:
            return await session.call_tool(name, args)

    async def direct(self, method, path, token, **kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app),
                                     base_url="http://backend") as client:
            return await client.request(method, path, headers={"Authorization": token}, **kwargs)

    def row(self, system_id, group, key):
        self.db.expire_all()
        return self.db.query(SystemRequirementField).filter_by(
            system_id=system_id, agent_group=group, field_key=key).one_or_none()


class AcceptanceTest(E2EBase):
    @bounded
    async def test_ac11_4_3_member_read_equals_direct_get(self):
        async with self.topology() as topo:
            direct = await self.direct("GET", f"/api/requirements/systems/{self.system.id}/fields",
                                       self.owner_token)
            self.assertEqual(direct.status_code, 200)
            for mode in MODES:
                with self.subTest(mode=mode):
                    result = await self.call(topo, mode, "read_requirement_fields",
                                             {"system_id": str(self.system.id)}, token=self.owner_token)
                    self.assertFalse(result.is_error, result.raw)
                    self.assertEqual(result.structured, direct.json())
                    self.assertEqual(json.loads(result.text), direct.json())
            self.assertEqual([r.authorization for r in topo.recorder.records], [self.owner_token] * 2)

    @bounded
    async def test_ac11_4_1_non_member_rejected_with_same_reason(self):
        async with self.topology() as topo:
            direct = await self.direct("GET", f"/api/requirements/systems/{self.system.id}/fields",
                                       self.outsider_token)
            self.assertEqual(direct.status_code, 403)
            for mode in MODES:
                with self.subTest(mode=mode):
                    before = len(topo.recorder.records)
                    result = await self.call(topo, mode, "read_requirement_fields",
                                             {"system_id": str(self.system.id)}, token=self.outsider_token)
                    self.assertTrue(result.is_error)
                    self.assertEqual(result.structured["error"], "forbidden")
                    self.assertEqual(result.structured["message"], direct.json()["detail"])
                    self.assertFalse(result.structured["retryable"])
                    new = topo.recorder.records[before:]
                    self.assertEqual([r.authorization for r in new], [self.outsider_token])

    @bounded
    async def test_ac11_4_2_tools_list_has_no_credential_like_property(self):
        async with self.topology() as topo:
            for mode in MODES:
                with self.subTest(mode=mode):
                    async with SdkClientPort(topo.url, mode).session() as session:
                        tools = await session.list_tools()
                    by_name = {t["name"]: t for t in tools}
                    self.assertEqual(set(by_name), set(EXPECTED_WHITELIST))
                    for name, expected in EXPECTED_WHITELIST.items():
                        schema = by_name[name]["inputSchema"]
                        self.assertEqual(set(schema["properties"]), expected)
                        for prop in all_property_names(schema):
                            self.assertFalse(any(b in prop.lower() for b in BLACKLIST), prop)
                        self.assertNotIn("binding", json.dumps(by_name[name]))
            self.assertEqual(topo.recorder.records, [])

    @bounded
    async def test_write_fills_on_behalf_of_from_registry_and_clear_uses_delete(self):
        async with self.topology() as topo:
            result = await self.call(topo, "auto", "write_requirement_field",
                                     {"system_id": str(self.system.id), "agent_group": "cost",
                                      "field": "sla", "value": "99.9%"},
                                     token=self.owner_token, agent="architecture")
            self.assertFalse(result.is_error, result.raw)
            row = self.row(self.system.id, "cost", "sla")
            self.assertEqual((row.value, row.updated_by, row.updated_on_behalf_of),
                             ("99.9%", self.owner.id, "architecture"))
            result = await self.call(topo, "legacy", "clear_requirement_field",
                                     {"system_id": str(self.system.id), "agent_group": "cost",
                                      "field": "sla"}, token=self.owner_token, agent="cost")
            self.assertFalse(result.is_error, result.raw)
            self.assertEqual([r.method for r in topo.recorder.records], ["PUT", "DELETE"])
            self.assertIsNotNone(self.row(self.system.id, "cost", "sla").cleared_at)
            agents = [r.fields["agent"] for r in topo.logs.events("tool_call")]
            self.assertEqual(agents, ["architecture", "cost"])


class IdentityIsolationTest(E2EBase):  # T-1、BR78.4（程式審查 R-01）
    """兩位使用者帶**不同**的 token 與**不同**的 agent 宣告交錯呼叫。

    交錯點由 `CallHookBarrier` 確定性地安排在工具處理函式讀取身分材料之前（不靠排程機率），
    並斷言成功安排的回合數下限。斷言：backend 收到的每個請求，其 `Authorization` 屬於路徑中系統的擁有者；
    寫入時每個請求本體的 `on_behalf_of` 屬於該使用者宣告的 agent，持久列的 `updated_by`／
    `updated_on_behalf_of` 亦然。
    """

    MIN_ROUNDS = 10

    def hook(self):
        def system_of(params):
            return str((params.arguments or {}).get("system_id"))
        return CallHookBarrier(is_a=lambda p: system_of(p) == str(self.system.id),
                               is_b=lambda p: system_of(p) == str(self.system2.id))

    async def interleave(self, topo, barrier, mode, name, make_args, *, per_user=20):
        port = SdkClientPort(topo.url, mode)
        agents = {self.owner_token: "cost", self.outsider_token: "architecture"}

        async def worker(token, system_id, count, offset):
            results = []
            async with port.session(token=token, agent=agents[token]) as session:
                for i in range(count):
                    results.append(await session.call_tool(name, make_args(system_id, offset + i)))
            return results

        start_rounds = barrier.rounds
        start_records = len(topo.recorder.records)
        jobs = []
        for w in range(4):
            jobs.append(worker(self.owner_token, self.system.id, per_user // 4, w * 100))
            jobs.append(worker(self.outsider_token, self.system2.id, per_user // 4, w * 100))
        outcomes = [r for batch in await asyncio.gather(*jobs) for r in batch]
        self.assertEqual(len(outcomes), 2 * per_user)
        self.assertFalse([o.raw for o in outcomes if o.is_error])
        self.assertGreaterEqual(barrier.rounds - start_rounds, self.MIN_ROUNDS)
        owner_of = {f"/{self.system.id}/": self.owner_token, f"/{self.system2.id}/": self.outsider_token}
        records = topo.recorder.records[start_records:]
        bodies = topo.recorder.bodies[start_records:]
        self.assertEqual(len(records), 2 * per_user)
        for record, body in zip(records, bodies):
            expected = next(tok for marker, tok in owner_of.items() if marker in record.path + "/")
            self.assertEqual(record.authorization, expected, record.path)
            if record.method == "PUT":
                self.assertEqual(json.loads(body)["on_behalf_of"], agents[expected], record.path)

    @bounded
    async def test_interleaved_reads_keep_identity(self):
        barrier = self.hook()
        async with self.topology(limits=BridgeLimits(max_concurrency=32), call_hook=barrier) as topo:
            for mode in MODES:
                with self.subTest(mode=mode):
                    await self.interleave(topo, barrier, mode, "read_requirement_fields",
                                          lambda sid, i: {"system_id": str(sid)})

    @bounded
    async def test_interleaved_writes_keep_identity_and_agent(self):
        barrier = self.hook()
        async with self.topology(limits=BridgeLimits(max_concurrency=32), call_hook=barrier) as topo:
            for mode in MODES:
                with self.subTest(mode=mode):
                    await self.interleave(
                        topo, barrier, mode, "write_requirement_field",
                        lambda sid, i: {"system_id": str(sid), "agent_group": "cost",
                                        "field": "peak_tps", "value": f"{sid}-{i}"})
            owner_row = self.row(self.system.id, "cost", "peak_tps")
            outsider_row = self.row(self.system2.id, "cost", "peak_tps")
            self.assertEqual((owner_row.updated_by, owner_row.updated_on_behalf_of),
                             (self.owner.id, "cost"))
            self.assertEqual((outsider_row.updated_by, outsider_row.updated_on_behalf_of),
                             (self.outsider.id, "architecture"))


class NoLeakTest(E2EBase):  # T-2、BR78.5
    def secrets(self, token):
        raw = token.split(" ", 1)[1]
        return (raw, raw.split(".")[2], "Bearer " + raw)

    def assert_clean(self, topo, result, *tokens):
        haystack = result.raw + "\n" + topo.logs.text()
        for token in tokens:
            for secret in self.secrets(token):
                self.assertNotIn(secret, haystack)

    @bounded
    async def test_every_branch_and_success_leak_nothing(self):
        sid = str(self.system.id)
        tampered = self.owner_token[:-1] + ("A" if self.owner_token[-1] != "A" else "B")
        write = {"system_id": sid, "agent_group": "cost", "field": "sla", "value": "v1"}
        branches = [
            ("unauthenticated (缺標頭)", "read_requirement_fields", {"system_id": sid}, None, None, None,
             "unauthenticated"),
            ("unauthenticated (格式錯)", "read_requirement_fields", {"system_id": sid}, "Token abc", None,
             None, "unauthenticated"),
            ("backend 401", "read_requirement_fields", {"system_id": sid}, tampered, None, None,
             "unauthenticated"),
            ("agent_not_declared", "write_requirement_field", write, self.owner_token, None, None,
             "agent_not_declared"),
            ("invalid 多餘參數", "read_requirement_fields", {"system_id": sid, "x": "1"},
             self.owner_token, None, None, "invalid_argument"),
            ("invalid ..", "write_requirement_field", dict(write, field=".."), self.owner_token, "cost",
             None, "invalid_argument"),
            ("invalid 空白", "write_requirement_field", dict(write, value="  "), self.owner_token, "cost",
             None, "invalid_argument"),
            ("forbidden", "read_requirement_fields", {"system_id": sid}, self.outsider_token, None, None,
             "forbidden"),
            ("not_found", "read_requirement_fields", {"system_id": "987654"}, self.owner_token, None,
             None, "not_found"),
            ("backend 422", "write_requirement_field", dict(write, field="no_such_key"),
             self.owner_token, "cost", None, "invalid_argument"),
            ("backend 503", "read_requirement_fields", {"system_id": sid}, self.owner_token, None, "503",
             "backend_unavailable"),
            ("418", "read_requirement_fields", {"system_id": sid}, self.owner_token, None, "418",
             "internal_error"),
            ("200 非 JSON", "read_requirement_fields", {"system_id": sid}, self.owner_token, None,
             "nonjson200", "internal_error"),
            ("回應過大", "read_requirement_fields", {"system_id": sid}, self.owner_token, None, "big",
             "internal_error"),
            ("成功的讀", "read_requirement_fields", {"system_id": sid}, self.owner_token, None, None, None),
            ("成功的寫", "write_requirement_field", write, self.owner_token, "cost", None, None),
        ]
        async with self.topology() as topo:
            for mode in MODES:
                for label, name, args, token, agent, fault, code in branches:
                    with self.subTest(mode=mode, branch=label):
                        topo.recorder.fault = fault
                        result = await self.call(topo, mode, name, args, token=token, agent=agent)
                        if code is None:
                            self.assertFalse(result.is_error, result.raw)
                        else:
                            self.assertEqual(result.structured["error"], code, result.raw)
                            self.assertEqual(result.structured["retryable"], code == "backend_unavailable")
                        self.assert_clean(topo, result, self.owner_token, self.outsider_token, tampered)
                topo.recorder.fault = None

    @bounded
    async def test_transport_failures_and_internal_crash_leak_nothing(self):
        def refuse(request):
            raise httpx.ConnectError("connection refused", request=request)

        async with self.topology(backend_transport=httpx.MockTransport(refuse)) as topo:
            for mode in MODES:
                with self.subTest(mode=mode, branch="refused"):
                    result = await self.call(topo, mode, "read_requirement_fields",
                                             {"system_id": "1"}, token=self.owner_token)
                    self.assertEqual((result.structured["error"], result.structured["retryable"]),
                                     ("backend_unavailable", True))
                    self.assert_clean(topo, result, self.owner_token)
                with self.subTest(mode=mode, branch="crash"), mock.patch(
                        "mcp_bridge.calls.build_backend_call",
                        side_effect=RuntimeError("SECRET-" + self.owner_token)):
                    result = await self.call(topo, mode, "read_requirement_fields",
                                             {"system_id": "1"}, token=self.owner_token)
                    self.assertEqual(result.structured["error"], "internal_error")
                    self.assertNotIn("SECRET-", result.raw + topo.logs.text())
                    self.assert_clean(topo, result, self.owner_token)
            health = await httpx.AsyncClient().get(topo.base + "/healthz")
            self.assertEqual(health.status_code, 200)  # 進程存活


class PathInjectionTest(E2EBase):  # T-4
    @bounded
    async def test_dot_segments_never_reach_backend(self):
        async with self.topology() as topo:
            for mode in MODES:
                for param in ("agent_group", "field"):
                    for bad in (".", "..", "a/b", "%2e%2e", "cost\n"):
                        with self.subTest(mode=mode, param=param, value=bad):
                            args = {"system_id": str(self.system.id), "agent_group": "cost",
                                    "field": "sla", "value": "v"}
                            args[param] = bad
                            result = await self.call(topo, mode, "write_requirement_field", args,
                                                     token=self.owner_token, agent="cost")
                            self.assertEqual(result.structured["error"], "invalid_argument")
            self.assertEqual(topo.recorder.records, [])


class TransportBehaviourTest(E2EBase):
    @bounded
    async def test_timeout_is_backend_unavailable_and_process_survives(self):
        async with self.topology(limits=BridgeLimits(overall_timeout_s=0.3)) as topo:
            topo.recorder.delay_s = 1.0
            result = await self.call(topo, "auto", "read_requirement_fields",
                                     {"system_id": str(self.system.id)}, token=self.owner_token)
            self.assertEqual((result.structured["error"], result.structured["retryable"]),
                             ("backend_unavailable", True))
            topo.recorder.delay_s = 0
            result = await self.call(topo, "auto", "read_requirement_fields",
                                     {"system_id": str(self.system.id)}, token=self.owner_token)
            self.assertFalse(result.is_error, result.raw)

    @bounded
    async def test_wall_clock_timeout_cancels_handler_with_real_sdk(self):
        """程式審查 R-06：牆鐘逾時取消的是外層 ASGI 呼叫；以真實 SDK 驗證處理函式與 backend 交換一併被取消，
        名額歸還時沒有仍在跑的處理函式（兩種協定版本）。"""
        limits = BridgeLimits(request_wall_timeout_s=0.5, overall_timeout_s=3.0)
        for era in (None, "2026-07-28"):
            with self.subTest(era=era):
                async with self.topology(limits=limits) as topo:
                    topo.recorder.delay_s = 1.5
                    params = {"name": "read_requirement_fields",
                              "arguments": {"system_id": str(self.system.id)}}
                    headers = {"accept": "application/json, text/event-stream",
                               "authorization": self.owner_token}
                    if era:
                        params["_meta"] = {"io.modelcontextprotocol/protocolVersion": era,
                                           "io.modelcontextprotocol/clientInfo": {"name": "t", "version": "0"},
                                           "io.modelcontextprotocol/clientCapabilities": {}}
                        headers.update({"mcp-protocol-version": era, "mcp-method": "tools/call",
                                        "mcp-name": "read_requirement_fields"})
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.post(topo.url, headers=headers, json={
                            "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(topo.app.gate.in_flight, 0)
                    lines = topo.logs.events("tool_call")
                    self.assertEqual([l.fields["outcome"] for l in lines], ["internal_error"])
                    await asyncio.sleep(1.5)  # 超過 backend 延遲：若處理函式仍在跑，這裡會多出一行
                    self.assertEqual(len(topo.logs.events("tool_call")), 1)
                    self.assertEqual(len(topo.recorder.records), 1)
                    self.assertEqual([r.fields["reason"] for r in topo.logs.events("request_rejected")],
                                     ["request_timeout"])

    @bounded
    async def test_no_session_id_and_healthz_not_access_logged(self):
        async with self.topology() as topo:
            async with httpx.AsyncClient(timeout=10) as client:
                for _ in range(5):
                    self.assertEqual((await client.get(topo.base + "/healthz")).status_code, 200)
                response = await client.post(topo.url, json={"jsonrpc": "2.0", "id": 1,
                                                             "method": "tools/list"},
                                             headers={"accept": "application/json, text/event-stream"})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("mcp-session-id", response.headers)
            self.assertNotIn("healthz", topo.logs.text())
            self.assertEqual([r for r in topo.logs.records if r.name.startswith("uvicorn.access")], [])

    @bounded
    async def test_credential_context_cleared_after_backend_exception(self):  # NFR21.28 端到端
        async def exploding(scope, receive, send):
            raise RuntimeError("backend exploded")

        async with self.topology() as topo:
            topo.recorder.app = exploding
            result = await self.call(topo, "legacy", "read_requirement_fields",
                                     {"system_id": "1"}, token=self.owner_token)
            self.assertEqual(result.structured["error"], "internal_error")
            before = len(topo.recorder.records)
            result = await self.call(topo, "legacy", "read_requirement_fields", {"system_id": "1"})
            self.assertEqual(result.structured["error"], "unauthenticated")
            self.assertEqual(len(topo.recorder.records), before)


class DisconnectTest(E2EBase):  # OPEN-MB21-16 → 16-A
    def raw_request(self, port, name, args, token, agent):
        body = json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                           "params": {"name": name, "arguments": args}}).encode()
        head = (f"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\n"
                f"Accept: application/json, text/event-stream\r\nAuthorization: {token}\r\n"
                f"X-Cloud360-Agent: {agent}\r\nContent-Length: {len(body)}\r\n\r\n")
        return head.encode() + body

    async def send_and_drop(self, port, payload, after):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(payload)
        await writer.drain()
        await asyncio.sleep(after)
        writer.close()
        await writer.wait_closed()

    async def wait_tool_calls(self, topo, n, limit=11.0):
        try:
            async with asyncio.timeout(limit):
                while len(topo.logs.events("tool_call")) < n:
                    await asyncio.sleep(0.05)
        except TimeoutError:
            raise AssertionError(f"{limit} 秒內未出現 {n} 行 tool_call") from None

    @bounded
    async def test_backend_request_completes_and_logs_once_after_client_drop(self):
        async with self.topology() as topo:
            topo.recorder.delay_s = 0.5
            payload = self.raw_request(topo.port, "write_requirement_field",
                                       {"system_id": str(self.system.id), "agent_group": "cost",
                                        "field": "sla", "value": "after-drop"}, self.owner_token, "cost")
            await self.send_and_drop(topo.port, payload, after=0.1)
            await self.wait_tool_calls(topo, 1)
            await asyncio.sleep(0.3)
            lines = topo.logs.events("tool_call")
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0].fields["outcome"], "ok")
            self.assertEqual(len(topo.recorder.records), 1)
            self.assertEqual(self.row(self.system.id, "cost", "sla").value, "after-drop")

    @bounded
    async def test_slow_backend_with_drop_loop_does_not_exhaust_pool(self):
        """24 條連線送出後斷線、backend 每次慢 0.5 秒：壓力必須真的頂到並行上限，事後名額與連線池都回到可用。

        程式審查 R-03：判準加上壓力前提——並行閘的峰值必須**等於上限**（16），且抵達 backend 的請求數
        ≥ 上限；超出者以 503 拒絕。連線在 uvicorn 把請求交給 app 之前就關閉者不會產生工具呼叫，所以
        「抵達 backend 的請求數＝`tool_call` 行數」，而不是固定 24。
        """
        async with self.topology() as topo:
            topo.recorder.delay_s = 0.5
            payload = self.raw_request(topo.port, "read_requirement_fields",
                                       {"system_id": str(self.system.id)}, self.owner_token, "cost")
            await asyncio.gather(*(self.send_and_drop(topo.port, payload, after=0.2) for _ in range(24)))
            stable_rounds, last = 0, None
            for _ in range(200):
                snapshot = (topo.app.gate.in_flight, len(topo.recorder.records),
                            len(topo.logs.events("tool_call")))
                stable_rounds = stable_rounds + 1 if snapshot == last and snapshot[0] == 0 else 0
                last = snapshot
                if stable_rounds >= 10:
                    break
                await asyncio.sleep(0.05)
            in_flight, records, lines = last
            limit = topo.app.gate.limit
            self.assertEqual(topo.app.gate.peak, limit)            # 壓力前提：頂到上限
            self.assertGreaterEqual(records, limit)                 # 抵達 backend 的請求數下限
            self.assertEqual(in_flight, 0)                          # 名額全部歸還
            self.assertEqual(lines, records)                        # 每個抵達者恰一行
            rejected = [r.fields["reason"] for r in topo.logs.events("request_rejected")]
            self.assertGreaterEqual(rejected.count("over_concurrency"), 1)
            topo.recorder.delay_s = 0
            result = await self.call(topo, "auto", "read_requirement_fields",
                                     {"system_id": str(self.system.id)}, token=self.owner_token)
            self.assertFalse(result.is_error, result.raw)

if __name__ == "__main__":
    unittest.main()
