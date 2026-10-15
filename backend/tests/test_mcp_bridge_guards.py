"""`U21 mcp-bridge` 的三個閘門與路由（`NFR21.19`–`NFR21.21`、`NFR21.28`；nfr-design 審查 R-01、R-06）。

以假內層應用驅動（不需要 `mcp`）。判準 ①–⑤ 見 `scalability-design.md` §1.3。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import asyncio
import io
import logging
import unittest

import httpx

from mcp_bridge.guards import CREDENTIALS, build_guarded_app
from mcp_bridge.limits import BridgeLimits
from mcp_bridge.observability import LOGGER_NAME, configure_logging
from tests.mcp_topology import preserve_logging

BASE = "http://bridge.test"
JSON_HDR = {"content-type": "application/json"}


class Collector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def events(self, name):
        return [r for r in self.records if getattr(r, "event", None) == name]


class FakeInner:
    """記錄呼叫次數；`hold` 為 True 時扣住每個請求直到 `release` 被設定。"""

    def __init__(self, hold=False, raise_first=False, sleep=0.0):
        self.calls = 0
        self.hold = hold
        self.release = asyncio.Event()
        self.entered = asyncio.Event()
        self.raise_first = raise_first
        self.sleep = sleep
        self.seen_credentials = []

    async def __call__(self, scope, receive, send):
        self.calls += 1
        self.seen_credentials.append(CREDENTIALS.get())
        message = await receive()
        self.entered.set()
        if self.raise_first and self.calls == 1:
            raise RuntimeError("inner failure")
        if self.hold:
            await self.release.wait()
        if self.sleep:
            await asyncio.sleep(self.sleep)
        body = b'{"echo":%d}' % len(message.get("body", b""))
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})


class GuardTestBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        preserve_logging(self)
        configure_logging(stream=io.StringIO())
        self.collector = Collector()
        logging.getLogger(LOGGER_NAME).addHandler(self.collector)

    def tearDown(self):
        logging.getLogger(LOGGER_NAME).removeHandler(self.collector)

    def make(self, inner, **limits):
        guarded = build_guarded_app(inner, BridgeLimits(**limits))
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=guarded.asgi), base_url=BASE,
                                   timeout=30)
        self.addAsyncCleanup(client.aclose)
        return guarded, client

    async def wait_in_flight(self, guarded, n):
        for _ in range(500):
            if guarded.gate.in_flight == n:
                return
            await asyncio.sleep(0.01)
        self.fail(f"in_flight never reached {n} (now {guarded.gate.in_flight})")


class ConcurrencyGateTest(GuardTestBase):
    async def test_over_limit_503_and_recovery(self):  # ① ②
        inner = FakeInner(hold=True)
        guarded, client = self.make(inner, max_concurrency=2)
        held = [asyncio.create_task(client.post("/mcp", content=b"{}", headers=JSON_HDR)) for _ in range(2)]
        await self.wait_in_flight(guarded, 2)
        third = await client.post("/mcp", content=b"{}", headers=JSON_HDR)
        self.assertEqual(third.status_code, 503)
        self.assertEqual(third.headers.get("retry-after"), "1")
        self.assertEqual(inner.calls, 2)
        rejected = self.collector.events("request_rejected")
        self.assertEqual([r.fields for r in rejected], [{"reason": "over_concurrency", "http_status": 503}])
        inner.release.set()
        self.assertEqual([r.status_code for r in await asyncio.gather(*held)], [200, 200])
        fourth = await client.post("/mcp", content=b"{}", headers=JSON_HDR)  # 同一個 client／連線池
        self.assertEqual(fourth.status_code, 200)
        self.assertEqual(guarded.gate.in_flight, 0)

    async def test_healthz_exempt_when_saturated(self):  # ③
        inner = FakeInner(hold=True)
        guarded, client = self.make(inner)
        held = [asyncio.create_task(client.post("/mcp", content=b"{}", headers=JSON_HDR)) for _ in range(16)]
        await self.wait_in_flight(guarded, 16)
        health = await client.get("/healthz")
        self.assertEqual((health.status_code, health.json()), (200, {"status": "ok"}))
        self.assertEqual((await client.post("/mcp", content=b"{}", headers=JSON_HDR)).status_code, 503)
        inner.release.set()
        await asyncio.gather(*held)

    async def test_default_limit_is_16(self):  # ④
        self.assertEqual(BridgeLimits().max_concurrency, 16)
        guarded, _ = self.make(FakeInner())
        self.assertEqual(guarded.gate.limit, 16)

    async def test_instances_independent(self):  # ⑤
        inner_x = FakeInner(hold=True)
        gx, cx = self.make(inner_x, max_concurrency=2)
        _, cy = self.make(FakeInner(), max_concurrency=2)
        held = [asyncio.create_task(cx.post("/mcp", content=b"{}", headers=JSON_HDR)) for _ in range(2)]
        await self.wait_in_flight(gx, 2)
        self.assertEqual((await cy.post("/mcp", content=b"{}", headers=JSON_HDR)).status_code, 200)
        inner_x.release.set()
        await asyncio.gather(*held)


class BodyLimitTest(GuardTestBase):
    async def test_content_length_over_limit(self):
        inner = FakeInner()
        _, client = self.make(inner)
        response = await client.post("/mcp", content=b"x" * 65537, headers=JSON_HDR)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(inner.calls, 0)
        self.assertEqual([r.fields["reason"] for r in self.collector.events("request_rejected")],
                         ["body_too_large"])
        self.assertNotIn("65537", " ".join(r.getMessage() for r in self.collector.records))

    async def test_chunked_over_limit(self):
        inner = FakeInner()
        _, client = self.make(inner)

        async def chunks():
            for _ in range(70):
                yield b"y" * 1024

        response = await client.post("/mcp", content=chunks(), headers=JSON_HDR)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(inner.calls, 0)

    async def test_within_limit_reaches_inner_with_full_body(self):
        inner = FakeInner()
        _, client = self.make(inner)
        response = await client.post("/mcp", content=b"z" * 65536, headers=JSON_HDR)
        self.assertEqual((response.status_code, response.json()), (200, {"echo": 65536}))

    async def test_slow_uploads_time_out_and_release_slots(self):
        inner = FakeInner()
        guarded, client = self.make(inner)

        async def trickle():
            for _ in range(10):
                yield b"a"
                await asyncio.sleep(1.0)

        uploads = [asyncio.create_task(client.post("/mcp", content=trickle(), headers=JSON_HDR))
                   for _ in range(16)]
        await self.wait_in_flight(guarded, 16)
        self.assertEqual((await client.get("/healthz")).status_code, 200)
        statuses = [r.status_code for r in await asyncio.gather(*uploads)]
        self.assertEqual(statuses, [408] * 16)
        self.assertEqual(guarded.gate.in_flight, 0)
        self.assertEqual(inner.calls, 0)
        self.assertEqual((await client.get("/healthz")).status_code, 200)
        self.assertEqual(len(self.collector.events("request_rejected")), 16)


class MethodAndPathTest(GuardTestBase):
    async def test_get_sse_is_405_without_slot(self):
        inner = FakeInner()
        guarded, client = self.make(inner, max_concurrency=1)
        response = await client.get("/mcp", headers={"accept": "text/event-stream"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers.get("allow"), "POST")
        self.assertEqual((inner.calls, guarded.gate.in_flight), (0, 0))
        self.assertEqual((await client.delete("/mcp")).status_code, 405)
        self.assertEqual([r.fields["reason"] for r in self.collector.events("request_rejected")],
                         ["method_not_allowed", "method_not_allowed"])

    async def test_mcp_subpaths_are_404_and_never_reach_inner(self):
        inner = FakeInner()
        _, client = self.make(inner)
        for path in ("/mcp/", "/mcp/x"):
            with self.subTest(path=path):
                self.assertEqual((await client.post(path, content=b"{}", headers=JSON_HDR)).status_code, 404)
                over = await client.post(path, content=b"x" * 70000, headers=JSON_HDR)
                self.assertEqual(over.status_code, 413)
        self.assertEqual((await client.post("/other", content=b"{}")).status_code, 404)
        self.assertEqual(inner.calls, 0)

    async def test_wall_clock_timeout(self):
        inner = FakeInner(sleep=1.0)
        _, client = self.make(inner, request_wall_timeout_s=0.2)
        response = await client.post("/mcp", content=b"{}", headers=JSON_HDR)
        self.assertEqual(response.status_code, 503)
        self.assertEqual([r.fields["reason"] for r in self.collector.events("request_rejected")],
                         ["request_timeout"])


class CredentialContextTest(GuardTestBase):
    async def test_reset_after_inner_exception(self):  # NFR21.28 單元層
        inner = FakeInner(raise_first=True)
        _, client = self.make(inner)
        with self.assertRaises(RuntimeError):
            await client.post("/mcp", content=b"{}",
                              headers=dict(JSON_HDR, authorization="Bearer AAA", **{"x-cloud360-agent": "cost"}))
        await client.post("/mcp", content=b"{}", headers=JSON_HDR)
        first, second = inner.seen_credentials
        self.assertEqual(first.authorization, ("Bearer AAA",))
        self.assertEqual(first.agent, ("cost",))
        self.assertEqual((second.authorization, second.agent), ((), ()))
        self.assertIsNone(CREDENTIALS.get())
        self.assertEqual(repr(first), "<redacted>")


if __name__ == "__main__":
    unittest.main()
