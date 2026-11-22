"""server.py — 以 uvicorn 起 bridge（MB-W1 第 3–5 步；`NFR21.35`、`NFR21.36`）。

- 先綁定 socket 再建 app：Host 允許清單依**實際**埠推導（`derive_allowed_hosts`），綁定後記一行
  `startup port=<實際埠> tools=<數量>`。
- `uvicorn.Config(access_log=False, log_config=None)`：關閉存取 log（`/healthz` 不洗版），也不讓 uvicorn
  覆寫 `configure_logging` 的設定。
- 啟動不呼叫 backend（`BR71.4`）：httpx client 為惰性連線。

驗證拓樸（`backend/tests/mcp_topology.py`）重用 `build_uvicorn_server` 與 `serve_until_stopped`，使測試與
正式啟動走同一組 uvicorn 設定。
"""

from __future__ import annotations

import argparse
import asyncio
import socket

import uvicorn

from .app import BridgeApp, create_app
from .executor import build_backend_client
from .limits import BridgeLimits, derive_allowed_hosts
from .observability import log_startup, log_startup_failed
from .startup import LoadedConfig


def build_uvicorn_server(app: BridgeApp) -> uvicorn.Server:
    config = uvicorn.Config(app, access_log=False, log_config=None, lifespan="on")
    return uvicorn.Server(config)


def bind_socket(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


async def serve_until_stopped(server: uvicorn.Server, sock: socket.socket, *, tools: int) -> bool:
    """起服務、在 uvicorn 開始接受連線後記啟動 INFO，並等它停止。

    回傳是否曾成功啟動。lifespan 啟動失敗時（程式審查 R-04）：所釘環境的 uvicorn 0.54 在 `serve` 內
    `sys.exit(3)`；uvicorn 未釘版，其他版本可能正常返回而 `started` 維持 False。兩種形狀都在這裡收斂為
    一行 `startup_failed subject="lifespan"` 並回傳 False，使行程以非零碼結束、原因留在 log。
    """
    async def run() -> None:
        # SystemExit 若從 task 內拋出，asyncio 會讓整個事件迴圈中止，而不是在 await 時交回；
        # 所以在 task 自己的協程內接住。已啟動之後的 SystemExit（例如訊號）照常往外傳。
        try:
            await server.serve(sockets=[sock])
        except SystemExit:
            if server.started:
                raise

    task = asyncio.create_task(run())
    while not server.started and not task.done():
        await asyncio.sleep(0.01)
    if server.started:
        log_startup(port=sock.getsockname()[1], tools=tools)
    await task
    if not server.started:
        log_startup_failed("lifespan")
        return False
    return True


async def _run(loaded: LoadedConfig, args: argparse.Namespace) -> int:
    limits = BridgeLimits(max_concurrency=args.max_concurrency)
    try:
        sock = bind_socket(args.host, args.port)
    except OSError:
        log_startup_failed("listen")
        return 1
    port = sock.getsockname()[1]
    client = build_backend_client(args.backend_url, limits)
    try:
        app = create_app(backend_client=client, registry=loaded.registry,
                         tool_specs=loaded.tool_specs, allowed_hosts=derive_allowed_hosts(port),
                         limits=limits)
        started = await serve_until_stopped(build_uvicorn_server(app), sock,
                                            tools=len(loaded.tool_specs))
    finally:
        await client.aclose()
    return 0 if started else 1


def serve(loaded: LoadedConfig, args: argparse.Namespace) -> int:
    return asyncio.run(_run(loaded, args))
