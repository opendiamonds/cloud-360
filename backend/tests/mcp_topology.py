"""`U21 mcp-bridge` 的驗證拓樸（`BR78.2`；nfr-design `reliability-design.md` §6.2）。

**路線 A（`same-interpreter`，Step 1 判定，`mcp==2.3.0`）**：官方 SDK client 經真實 HTTP 連到以 uvicorn 起在
`127.0.0.1` 預先綁定 socket 上的 bridge；bridge 以 `httpx.ASGITransport` 直達「記錄包裝(`main.app`)」——真實的
FastAPI 路由、`get_current_user` 與 facade 授權，只把 TCP 換成 ASGI 傳輸。

- `MCP_ROUTE` 是常數（不讀環境變數）：路線在 CI 與開發機上由同一行程式決定。
- 前置條件不成立（沒有 `mcp`、版本不對）一律 `AssertionError`，訊息指出建立指令——**不准 skip**（CC-3）。
- 記錄包裝內的屏障（`asyncio.Event`）與測試在同一個事件迴圈內，用來決定交錯順序（functional-design 審查 R-15）。
- bridge 與 uvicorn 用正式啟動的同一組設定（`server.build_uvicorn_server`、`server.serve_until_stopped`）。
- 每個端到端案例以 `asyncio.timeout(30)` 包住（`bounded`），逾時即 `AssertionError`。
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import importlib.metadata
import io
import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

MCP_ROUTE = "same-interpreter"
PINNED_MCP_VERSION = "2.3.0"
CASE_TIMEOUT_S = 30.0
READY_TIMEOUT_S = 10.0


def assert_prerequisites() -> None:
    """路線 A 的前置條件：本直譯器裝有所釘版本的 `mcp`。"""
    if MCP_ROUTE != "same-interpreter":
        raise AssertionError(f"未實作的 MCP_ROUTE：{MCP_ROUTE!r}")
    try:
        version = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        raise AssertionError(
            "本直譯器沒有安裝 mcp。請在 backend/ 執行：pip install -r requirements.txt"
        ) from None
    if version != PINNED_MCP_VERSION:
        raise AssertionError(
            f"mcp 版本為 {version}，本單元釘選 {PINNED_MCP_VERSION}。"
            "請在 backend/ 執行：pip install -r requirements.txt"
        )


_TOUCHED_LOGGERS = ("", "cloud360.mcp_bridge", "httpx", "httpcore", "mcp")


def preserve_logging(testcase) -> None:
    """`configure_logging()` 會改根 logger 的層級與 handler；測試結束時還原，避免影響同一行程內的其他測試。"""
    snapshot = {name: (logging.getLogger(name).level, list(logging.getLogger(name).handlers))
                for name in _TOUCHED_LOGGERS}

    def restore():
        for name, (level, handlers) in snapshot.items():
            target = logging.getLogger(name)
            target.setLevel(level)
            target.handlers[:] = handlers

    testcase.addCleanup(restore)


def bounded(test: Callable) -> Callable:
    """每案 30 秒上限；逾時以 `AssertionError` 失敗（nfr-design 審查 R-09）。"""

    @functools.wraps(test)
    async def wrapper(*args, **kwargs):
        try:
            async with asyncio.timeout(CASE_TIMEOUT_S):
                return await test(*args, **kwargs)
        except TimeoutError:
            raise AssertionError(f"端到端案例超過 {CASE_TIMEOUT_S:.0f} 秒") from None

    return wrapper


# ---- log 收集 ------------------------------------------------------------------------
class LogSource(logging.Handler):
    """收集 bridge 進程內**全部** logger 的格式化輸出（使用正式的 `BridgeFormatter`）。

    掛在根 logger，**不調整任何 logger 的層級**（層級由 `configure_logging()` 決定，`BR78.5`）。
    """

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        from mcp_bridge.observability import BridgeFormatter
        self.setFormatter(BridgeFormatter())
        self._lines: list[str] = []
        self.records: list[logging.LogRecord] = []
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        with self._lock:
            self._lines.append(line)
            self.records.append(record)

    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def text(self) -> str:
        return "\n".join(self.lines())

    def events(self, name: str) -> list[logging.LogRecord]:
        with self._lock:
            return [r for r in self.records if getattr(r, "event", None) == name]


# ---- backend 外層的記錄包裝與屏障 ------------------------------------------------------
@dataclass(frozen=True)
class BackendRecord:
    method: str
    path: str
    authorization: Optional[str]


class CallHookBarrier:
    """確定性的交錯點（程式審查 R-01）：掛在 `create_app(call_hook=…)`，位於工具處理函式**讀取身分材料之前**。

    A 的每一個呼叫在此等待，直到 B 有一個**新的**呼叫抵達同一點——B 抵達這裡時，它的 contextvar 已由
    `CredentialContext` 設定好。所以每一回合都把「另一個請求已寫入身分材料」確定性地安排在 A 讀取之前；
    身分材料若改存模組變數（突變 M09／M35），A 在該回合讀到的就是 B 的值。`rounds` 是成功安排的回合數，
    測試斷言它的下限，而不是依賴排程的機率。
    """

    def __init__(self, is_a: Callable[[Any], bool], is_b: Callable[[Any], bool],
                 timeout: float = 1.0) -> None:
        self.is_a = is_a
        self.is_b = is_b
        self.timeout = timeout
        self.condition = asyncio.Condition()
        self.b_arrivals = 0
        self.rounds = 0
        self.unpaired = 0

    async def __call__(self, params: Any) -> None:
        async with self.condition:
            if self.is_b(params):
                self.b_arrivals += 1
                self.condition.notify_all()
                return
            if not self.is_a(params):
                return
            seen = self.b_arrivals
            try:
                await asyncio.wait_for(
                    self.condition.wait_for(lambda: self.b_arrivals > seen), self.timeout)
                self.rounds += 1
            except TimeoutError:
                self.unpaired += 1


class RecordingBackend:
    """記錄每個 backend 請求的 (method, path, Authorization)，可注入屏障、延遲與故障。"""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.records: list[BackendRecord] = []
        #: 與 `records` 同序：每個請求的原始本體（寫入時用來斷言 `on_behalf_of`）。
        self.bodies: list[bytes] = []
        self.delay_s = 0.0
        self.fault: Optional[str] = None  # "418"、"nonjson200"、"503"、"big"

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        record = BackendRecord(scope["method"], scope["path"], headers.get("authorization"))
        self.records.append(record)
        index = len(self.bodies)
        self.bodies.append(b"")

        inner_receive = receive

        async def receive():
            message = await inner_receive()
            if message.get("type") == "http.request":
                self.bodies[index] += message.get("body", b"")
            return message
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.fault is not None:
            await self._fault(send)
            return
        await self.app(scope, receive, send)

    async def _fault(self, send) -> None:
        if self.fault == "big":
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json")]})
            for _ in range(32):  # 32 × 64 KiB = 2 MiB，逐塊送出
                await send({"type": "http.response.body", "body": b" " * 65536, "more_body": True})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})
            return
        status, body = {"418": (418, b'{"detail":"teapot"}'), "nonjson200": (200, b"<html>"),
                        "503": (503, b"busy")}[self.fault]
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})


# ---- 拓樸 ------------------------------------------------------------------------------
class BridgeTopology:
    """起 bridge（uvicorn、真實 HTTP）並連到記錄包裝；`async with` 使用。"""

    def __init__(self, *, backend_app: Any, tool_specs, registry, limits=None,
                 backend_transport: Any = None, call_hook: Any = None) -> None:
        assert_prerequisites()
        from mcp_bridge.limits import BridgeLimits
        self.recorder = RecordingBackend(backend_app)
        self.tool_specs = tuple(tool_specs)
        self.registry = registry
        self.limits = limits if limits is not None else BridgeLimits()
        self.backend_transport = backend_transport
        self.call_hook = call_hook
        self.logs = LogSource()
        self.port: Optional[int] = None
        self.app = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def __aenter__(self) -> "BridgeTopology":
        import httpx
        from mcp_bridge.app import create_app
        from mcp_bridge.executor import build_backend_client
        from mcp_bridge.limits import derive_allowed_hosts
        from mcp_bridge.observability import configure_logging
        from mcp_bridge.server import bind_socket, build_uvicorn_server, serve_until_stopped

        configure_logging(stream=io.StringIO())
        logging.getLogger().addHandler(self.logs)
        sock = bind_socket("127.0.0.1", 0)
        self.port = sock.getsockname()[1]
        transport = self.backend_transport or httpx.ASGITransport(app=self.recorder)
        self.client = build_backend_client("http://backend:8000", self.limits, transport=transport)
        self.app = create_app(backend_client=self.client, registry=self.registry,
                              tool_specs=self.tool_specs,
                              allowed_hosts=derive_allowed_hosts(self.port), limits=self.limits,
                              call_hook=self.call_hook)
        self.server = build_uvicorn_server(self.app)
        self.task = asyncio.create_task(serve_until_stopped(self.server, sock,
                                                            tools=len(self.tool_specs)))
        try:
            async with asyncio.timeout(READY_TIMEOUT_S):
                while not (self.server.started and self.logs.events("startup")):
                    if self.task.done():
                        raise AssertionError("bridge 未能啟動")
                    await asyncio.sleep(0.01)
        except TimeoutError:
            raise AssertionError(f"bridge 未在 {READY_TIMEOUT_S:.0f} 秒內就緒") from None
        return self

    async def __aexit__(self, *exc) -> None:
        self.server.should_exit = True
        with contextlib.suppress(Exception):
            async with asyncio.timeout(15):
                await self.task
        await self.client.aclose()
        logging.getLogger().removeHandler(self.logs)
