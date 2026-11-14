"""executor.py — 對 backend 的 HTTP 交換（`BR73.2`、`BR73.3`、`BR75.1`、`NFR21.1`、`NFR21.22`）。

**全單元唯一 import `httpx` 的模組。**

- `build_backend_client`：`follow_redirects=False`（token 不會被帶往重導目標）、無預設 `Authorization`、
  `trust_env=False`（不讀代理等環境設定）、cookie jar 政策為**拒收一切**
  （`DefaultCookiePolicy(allowed_domains=[])`，functional-design 審查 R-20 擇 (b)：jar 永遠為空，
  不需要在請求之間清空，也就沒有並發下「清空不是原子操作」的問題）、連線池上限等於並行上限。
- `exchange`：以 `build_request` 組請求、加上該次請求的 `Authorization` 原值、`send` **一次**；整段
  （送出＋逐塊讀取本體）包在 `asyncio.timeout(overall)` 之內，防止滴流 backend 無限延長。
- `classify_transport_error`：把例外歸為四值的 `TransportKind`；`dns` 的判定依 Step 1 的 K-10 實測
  （`socket.gaierror` 在 `__cause__`／`__context__` 鏈上可達）。

例外物件從不轉成文字進入任何輸出（`BR73.4`）。
"""

from __future__ import annotations

import asyncio
import http.cookiejar
import socket
from typing import Optional

import httpx

from .calls import BackendCall
from .credentials import RequestCredential
from .limits import BridgeLimits
from .outcomes import (
    ExchangeResult, InternalFailure, Received, ResponseTooLarge, TransportFailure, TransportKind,
)


def _rejecting_cookie_jar() -> http.cookiejar.CookieJar:
    return http.cookiejar.CookieJar(policy=http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))


def build_backend_client(base_url: str, limits: BridgeLimits = BridgeLimits(), *,
                         transport: Optional[httpx.AsyncBaseTransport] = None) -> httpx.AsyncClient:
    """共用的 backend client；不帶任何身分。`transport` 只供測試注入（`BR78.2`）。"""
    return httpx.AsyncClient(
        base_url=base_url,
        follow_redirects=False,
        trust_env=False,
        cookies=_rejecting_cookie_jar(),
        timeout=httpx.Timeout(connect=limits.connect_timeout_s, read=limits.overall_timeout_s,
                              write=limits.overall_timeout_s, pool=limits.connect_timeout_s),
        limits=httpx.Limits(max_connections=limits.max_concurrency,
                            max_keepalive_connections=limits.max_concurrency),
        transport=transport,
    )


def _chain(exc: BaseException):
    seen: set[int] = set()
    current: Optional[BaseException] = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def classify_transport_error(exc: BaseException) -> Optional[TransportFailure]:
    """四值歸類；不屬於傳輸失敗者回 `None`（呼叫端產生 `InternalFailure`）。"""
    if isinstance(exc, (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError)):
        return TransportFailure(TransportKind.TIMEOUT)
    if isinstance(exc, httpx.ConnectError):
        if any(isinstance(link, socket.gaierror) for link in _chain(exc)):
            return TransportFailure(TransportKind.DNS)
        return TransportFailure(TransportKind.REFUSED)
    if isinstance(exc, (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError)):
        return TransportFailure(TransportKind.PROTOCOL)
    return None


async def read_bounded(response: httpx.Response, limit: int) -> Optional[bytes]:
    """逐塊讀取本體；超過 `limit` 即停止並回 `None`（`ResponseTooLarge`）。"""
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > limit:
                return None
        except ValueError:
            pass
    chunks = bytearray()
    async for chunk in response.aiter_bytes():
        chunks.extend(chunk)
        if len(chunks) > limit:
            return None
    return bytes(chunks)


async def exchange(client: httpx.AsyncClient, call: BackendCall, credential: RequestCredential,
                   limits: BridgeLimits) -> ExchangeResult:
    """恰一次 backend 請求；不重試（`BR75.1`、`NFR21.27`）。"""
    try:
        request = client.build_request(
            call.method, call.path,
            params=list(call.query) or None,
            json=call.json_body,
            headers={"Authorization": credential.raw},
        )
        async with asyncio.timeout(limits.overall_timeout_s):
            response = await client.send(request, stream=True)
            try:
                body = await read_bounded(response, limits.max_response_body_bytes)
            finally:
                await response.aclose()
    except Exception as exc:  # 只在此處歸類；例外文字不外流
        failure = classify_transport_error(exc)
        return failure if failure is not None else InternalFailure()
    if body is None:
        return ResponseTooLarge()
    return Received(status=response.status_code, body=body)
