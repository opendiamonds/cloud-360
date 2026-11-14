"""app.py — bridge ASGI 應用的**唯一**組裝點 `create_app`（`BR78.3`、`BR71.2`、`BR71.3`、`BR71.6`、`BR73.3`）。

正式啟動（`server.serve`）與全部測試都經它建立，差別只在傳入的 `backend_client` 與 `registry`。它**不**讀檔、
不解析命令列、不建立 client、不設定 logging。本模組與 `server.py` 是本套件中唯二 import `mcp` 的模組。

SDK 接線（`mcp==2.3.0`，Step 1 實測紀錄見 code-summary）：

- 低階 `Server(on_list_tools=…, on_call_tool=…)`：2.x 沒有 `call_tool` 裝飾器，也沒有 `validate_input`；
  SDK 不依 `inputSchema` 驗證參數（K-5），驗證全由 `calls.validate_arguments` 承擔。
- `get_tool_input_schema`：以 `tool_specs` 純查表提供；不給的話，現代協定版本每次帶參數的 `tools/call`
  都會先多跑一次 `tools/list` 處理函式（S-13）。
- 未知工具：處理函式拋 `MCPError(-32602, 固定訊息)`，回 JSON-RPC 協定錯誤、不回顯工具名（17-A，`BR76.3`）。
  舊式協定版本 HTTP 200、現代協定版本 HTTP 400（S-3）。
- `StreamableHTTPSessionManager(stateless=True, json_response=True, …)`：不發 `Mcp-Session-Id`（K-2）；
  `json_response=True` 是 16-A 成立的前提（S-6）；Host 檢查用 `derive_allowed_hosts` 的結果（K-3，拒絕為 421）；
  SDK 自帶的本體上限設為與 `BodyLimit` 相同，使 413 一律由 `BodyLimit` 判定並留紀錄（S-12）。
- session manager 必須在 lifespan 內 `run()`，且一個實例只能進一次（K-9）。
"""

from __future__ import annotations

import contextlib
import json
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, Optional

import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError

from . import executor
from .agents import AgentRegistry
from .dispatch import declared_tool, run_tool_call
from .generator import ToolSpec
from .guards import CREDENTIALS, GuardedApp, build_guarded_app
from .limits import BridgeLimits
from .observability import log_internal_failure
from .outcomes import MSG_UNKNOWN_TOOL, ToolOutcome, internal_error

SERVER_NAME = "cloud360-mcp-bridge"
INVALID_PARAMS = -32602


def to_call_tool_result(outcome: ToolOutcome) -> types.CallToolResult:
    """`BR76.3`／`BR76.4`：成功為 backend 本體；錯誤為 `isError` 與 `{error, message, retryable}`。"""
    document = outcome.payload if outcome.ok else outcome.error_document()
    text = json.dumps(document, ensure_ascii=False, sort_keys=True)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structured_content=document,
        is_error=not outcome.ok,
    )


class BridgeApp:
    """ASGI 應用；`running()` 讓不經 ASGI lifespan 的測試傳輸也能進入 session manager。"""

    def __init__(self, guarded: GuardedApp, manager: StreamableHTTPSessionManager) -> None:
        self._guarded = guarded
        self._manager = manager

    @property
    def gate(self):
        return self._guarded.gate

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator["BridgeApp"]:
        async with self._manager.run():
            yield self

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        await self._guarded.asgi(scope, receive, send)

    async def _lifespan(self, receive, send) -> None:
        message = await receive()
        if message["type"] != "lifespan.startup":
            return
        try:
            async with self.running():
                await send({"type": "lifespan.startup.complete"})
                while (await receive())["type"] != "lifespan.shutdown":
                    pass
        except Exception:
            await send({"type": "lifespan.startup.failed", "message": "bridge startup failed"})
            return
        await send({"type": "lifespan.shutdown.complete"})


def _internal_error_result() -> types.CallToolResult:
    """不經 `to_call_tool_result` 的固定 `internal_error` 結果（序列化失敗時的退路）。"""
    document = internal_error().error_document()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(document, ensure_ascii=False))],
        structured_content=document,
        is_error=True,
    )


def create_app(*, backend_client: Any, registry: AgentRegistry,
               tool_specs: tuple[ToolSpec, ...], allowed_hosts: tuple[str, ...],
               limits: BridgeLimits = BridgeLimits(),
               call_hook: Optional[Callable[[Any], Awaitable[None]]] = None) -> BridgeApp:
    """組裝 bridge；四個必填加一個帶預設的 `limits`（functional-design 審查 R-17）。

    `backend_client` 為 `executor.build_backend_client` 建立的 `httpx.AsyncClient`（本模組不 import
    `httpx`，型別標註因此寫 `Any`：全單元只有 `executor.py` import `httpx`）。

    `call_hook` 是**測試縫**（程式審查 R-01）：在工具處理函式讀取本請求的身分材料**之前** await 它，使身分隔離
    測試能確定性地把「另一個請求已設定其 contextvar」安排在這個讀取點之前。正式啟動（`server.py`）不傳，
    值為 `None` 時沒有任何作用。
    """
    specs_by_name: Mapping[str, ToolSpec] = {spec.name: spec for spec in tool_specs}
    tools = [
        types.Tool(name=spec.name, description=spec.description,
                   input_schema=dict(spec.input_schema))
        for spec in sorted(tool_specs, key=lambda s: s.name)
    ]

    async def send_to_backend(call, credential):
        return await executor.exchange(backend_client, call, credential, limits)

    async def on_list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    async def on_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        if call_hook is not None:
            await call_hook(params)
        headers = CREDENTIALS.get()
        outcome = await run_tool_call(
            declared_tool(specs_by_name, params.name),
            params.arguments,
            headers.authorization if headers is not None else (),
            headers.agent if headers is not None else (),
            send_to_backend,
            registry=registry,
            requested_name=params.name,
        )
        if outcome.unknown_tool:
            raise MCPError(code=INVALID_PARAMS, message=MSG_UNKNOWN_TOOL)
        try:
            return to_call_tool_result(outcome)
        except Exception as exc:  # 程式審查 R-05：結果序列化也在總攔截之內，例外文字永不回給 SDK
            log_internal_failure(type(exc).__name__)
            return _internal_error_result()

    def input_schema_of(name: str) -> Optional[Mapping[str, Any]]:
        spec = specs_by_name.get(name)
        return dict(spec.input_schema) if spec is not None else None

    server = Server(SERVER_NAME, on_list_tools=on_list_tools, on_call_tool=on_call_tool,
                    get_tool_input_schema=input_schema_of)
    manager = StreamableHTTPSessionManager(
        app=server,
        json_response=True,
        stateless=True,
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(allowed_hosts),
            allowed_origins=[],
        ),
        max_request_body_size=limits.max_request_body_bytes,
    )
    guarded = build_guarded_app(manager.handle_request, limits)
    return BridgeApp(guarded, manager)
