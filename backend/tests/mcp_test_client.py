"""`BR78.1` 的最小測試 client：官方 SDK 的 streamable HTTP client，帶 `Authorization` 與 `X-Cloud360-Agent`。

只存在於 `backend/tests/`，不是產品元件。提供 `list_tools` 與 `call_tool` 兩個操作（`McpClientPort`）。

**兩個協定版本都要測**（Step 1 中途關卡核可的調整 1）：SDK 2.3.0 的 `Client(mode="auto")` 會協商到現代協定版本
`2026-07-28`，`mode="legacy"` 走舊式 handshake（`2025-11-25`）。兩者在 bridge 內走不同的 SDK 程式路徑。
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

MODES = ("legacy", "auto")


@dataclass
class CallResult:
    """一次 `tools/call` 的結果；協定錯誤時 `protocol_error` 為 (code, message)。"""

    is_error: bool
    structured: Optional[dict]
    text: str
    raw: str
    protocol_error: Optional[tuple[int, str]] = None


class McpSession:
    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def protocol_version(self) -> str:
        return self._client.protocol_version

    async def list_tools(self) -> list[dict]:
        result = await self._client.list_tools()
        return [t.model_dump(by_alias=True, exclude_none=True) for t in result.tools]

    async def call_tool(self, name: str, arguments: dict) -> CallResult:
        from mcp.shared.exceptions import MCPError
        try:
            result = await self._client.call_tool(name, arguments)
        except MCPError as err:
            return CallResult(is_error=True, structured=None, text=err.message,
                              raw=repr(err.error.model_dump()), protocol_error=(err.code, err.message))
        text = "".join(getattr(c, "text", "") for c in result.content)
        return CallResult(is_error=bool(result.is_error), structured=result.structured_content,
                          text=text, raw=result.model_dump_json(by_alias=True))


class SdkClientPort:
    """`McpClientPort` 的路線 A 實作。"""

    def __init__(self, url: str, mode: str = "auto") -> None:
        if mode not in MODES:
            raise ValueError(mode)
        self.url = url
        self.mode = mode

    @contextlib.asynccontextmanager
    async def session(self, *, token: Optional[str] = None,
                      agent: Optional[str] = None) -> AsyncIterator[McpSession]:
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client

        headers = {}
        if token is not None:
            headers["Authorization"] = token
        if agent is not None:
            headers["X-Cloud360-Agent"] = agent
        http = httpx2.AsyncClient(headers=headers, timeout=15)
        try:
            async with Client(streamable_http_client(self.url, http_client=http), mode=self.mode,
                              cache=None) as client:
                yield McpSession(client)
        finally:
            await http.aclose()
