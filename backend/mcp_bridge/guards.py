"""guards.py — `/mcp` 前置的 ASGI 中介層（`NFR21.19`–`NFR21.21`、`NFR21.28`；nfr-design 審查 R-01、R-06）。

層序（外 → 內）：

1. `PathRouter`：`/healthz` 精確比對，回固定本體，位於**全部閘門之外**（飽和或 backend 故障都不影響它）；
   `/mcp` 與 `/mcp/*` 進入 MCP 鏈；其餘 404。
2. `MethodGuard`：`/mcp*` 的非 POST 一律 405，**不佔名額**（Step 1 的 K-8：SDK 原生會讓舊式協定的
   GET 開一條永不結束的 SSE 串流，佔住一個名額）。
3. `ConcurrencyGate`：計「進行中的 `/mcp` 請求」（不是連線），超額 503 ＋ `Retry-After`；計數屬於**實例**，
   不是模組全域（`NFR21.23`）；名額在 `finally` 歸還。
4. `WallClock`：整個請求的牆鐘上限 `REQUEST_WALL_TIMEOUT_S`，逾時 503。**偏離計畫的層序**：計畫把它排在
   `BodyLimit` 之內，那樣最壞時間是 2 ＋ 12 秒，`stop_grace_period` 的關係式（12 ＋ 1 ≤ 13）就不成立；
   改排在 `BodyLimit` 之外，使 12 秒涵蓋本體讀取與 backend 交換的全程。
5. `BodyLimit`：先完整緩衝本體再交給內層；`Content-Length` 或累計位元組超量 413；讀取期限到 408。
6. `ExactPath`：路徑不等於 `/mcp` 者 404——`/mcp/` 與 `/mcp/x` 先經閘門與本體上限，但**不到達 SDK**。
7. `CredentialContext`：把 `Authorization` 與 `X-Cloud360-Agent` 的**全部原值**放進 `ContextVar`，
   `finally` 一律重設（`BR73.3`、`NFR21.28`）。

每個 HTTP 層拒絕各記恰一行 `request_rejected` WARNING（`observability.REJECT_REASONS`）；404 不記。
回應本體都是固定 JSON，不回顯任何請求內容。本模組不 import `mcp`、`httpx`。
"""

from __future__ import annotations

import asyncio
import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from .limits import BridgeLimits
from .observability import log_request_rejected

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

MCP_PATH = "/mcp"
HEALTH_PATH = "/healthz"
HEALTH_BODY = b'{"status":"ok"}'


@dataclass(frozen=True, repr=False)
class RawHeaders:
    """單一請求的身分材料原值；只存在於該請求的 context。"""

    authorization: tuple[str, ...]
    agent: tuple[str, ...]

    def __repr__(self) -> str:
        return "<redacted>"


#: 本請求的身分材料；值只在 `CredentialContext` 設定的 context 內可見。
CREDENTIALS: ContextVar[Optional[RawHeaders]] = ContextVar("cloud360_mcp_bridge_credentials",
                                                           default=None)


async def send_fixed(send: Send, status: int, document: dict,
                     extra_headers: tuple[tuple[bytes, bytes], ...] = ()) -> None:
    body = json.dumps(document, separators=(",", ":")).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")), *extra_headers],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _header_values(scope: Scope, name: bytes) -> tuple[str, ...]:
    return tuple(value.decode("latin-1") for key, value in scope.get("headers", [])
                 if key.lower() == name)


class CredentialContext:
    def __init__(self, inner: ASGIApp) -> None:
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        token = CREDENTIALS.set(RawHeaders(
            authorization=_header_values(scope, b"authorization"),
            agent=_header_values(scope, b"x-cloud360-agent"),
        ))
        try:
            await self.inner(scope, receive, send)
        finally:
            CREDENTIALS.reset(token)


class ExactPath:
    def __init__(self, inner: ASGIApp) -> None:
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("path") != MCP_PATH:
            await send_fixed(send, 404, {"error": "not_found"})
            return
        await self.inner(scope, receive, send)


class BodyLimit:
    def __init__(self, inner: ASGIApp, *, max_bytes: int, read_timeout_s: float) -> None:
        self.inner = inner
        self.max_bytes = max_bytes
        self.read_timeout_s = read_timeout_s

    async def _reject(self, send: Send, reason: str) -> None:
        log_request_rejected(reason)
        status = 413 if reason == "body_too_large" else 408
        await send_fixed(send, status, {"error": reason})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        declared = _header_values(scope, b"content-length")
        if declared:
            try:
                if int(declared[0]) > self.max_bytes:
                    await self._reject(send, "body_too_large")
                    return
            except ValueError:
                pass
        body = bytearray()
        try:
            async with asyncio.timeout(self.read_timeout_s):
                more = True
                while more:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > self.max_bytes:
                        await self._reject(send, "body_too_large")
                        return
                    more = bool(message.get("more_body", False))
        except TimeoutError:
            await self._reject(send, "body_timeout")
            return

        replayed = False

        async def replay() -> dict:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.inner(scope, replay, send)


class WallClock:
    def __init__(self, inner: ASGIApp, *, timeout_s: float) -> None:
        self.inner = inner
        self.timeout_s = timeout_s

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        started = False

        async def tracking_send(message: dict) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            async with asyncio.timeout(self.timeout_s):
                await self.inner(scope, receive, tracking_send)
        except TimeoutError:
            log_request_rejected("request_timeout")
            if not started:
                await send_fixed(send, 503, {"error": "timeout"})


class ConcurrencyGate:
    """進行中 `/mcp` 請求的計數；判定與遞增之間沒有 `await`，單執行緒事件迴圈下不需鎖。"""

    def __init__(self, inner: ASGIApp, *, limit: int) -> None:
        self.inner = inner
        self.limit = limit
        self.in_flight = 0
        #: 曾同時在途的最大名額數（只供觀測與測試；不影響判定）。
        self.peak = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.in_flight >= self.limit:
            log_request_rejected("over_concurrency")
            await send_fixed(send, 503, {"error": "busy"}, ((b"retry-after", b"1"),))
            return
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await self.inner(scope, receive, send)
        finally:
            self.in_flight -= 1


class MethodGuard:
    def __init__(self, inner: ASGIApp) -> None:
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("method") != "POST":
            log_request_rejected("method_not_allowed")
            await send_fixed(send, 405, {"error": "method_not_allowed"}, ((b"allow", b"POST"),))
            return
        await self.inner(scope, receive, send)


class PathRouter:
    def __init__(self, mcp_chain: ASGIApp) -> None:
        self.mcp_chain = mcp_chain

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            if scope.get("type") == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return
        path = scope.get("path", "")
        if path == HEALTH_PATH:
            await send_fixed(send, 200, {"status": "ok"})
            return
        if path == MCP_PATH or path.startswith(MCP_PATH + "/"):
            await self.mcp_chain(scope, receive, send)
            return
        await send_fixed(send, 404, {"error": "not_found"})


@dataclass
class GuardedApp:
    """組好的 HTTP 應用與它的並行閘（測試以 `gate.in_flight` 觀察名額）。"""

    asgi: ASGIApp
    gate: ConcurrencyGate


def build_guarded_app(inner: ASGIApp, limits: BridgeLimits) -> GuardedApp:
    chain: Any = CredentialContext(inner)
    chain = ExactPath(chain)
    chain = BodyLimit(chain, max_bytes=limits.max_request_body_bytes,
                      read_timeout_s=limits.body_read_timeout_s)
    chain = WallClock(chain, timeout_s=limits.request_wall_timeout_s)
    gate = ConcurrencyGate(chain, limit=limits.max_concurrency)
    return GuardedApp(asgi=PathRouter(MethodGuard(gate)), gate=gate)
