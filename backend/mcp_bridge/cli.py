"""cli.py — 命令列入口（`BR71.1`、`NFR21.6`、`NFR21.16` ①、`NFR21.35`）。

設定一律走命令列參數，模組不讀環境變數。`--host` 預設 `127.0.0.1`（functional-design 審查 R-18；compose 的
`command` 明列 `--host 0.0.0.0`）；`--port` 預設 8080；`--max-concurrency` 預設 `DEFAULT_MAX_CONCURRENCY`。

`main` 在自我驗證**通過之後**才 import 含 `mcp` 的 `server` 模組，使設定錯誤的四份手改產物測試在沒有 SDK
的直譯器中也能直接呼叫 `main(argv, config_dir=…)` 得到回傳值 1。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from .limits import DEFAULT_MAX_CONCURRENCY
from .observability import configure_logging, log_startup_failed
from .startup import PACKAGE_DIR, StartupConfigError, load_and_validate

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m mcp_bridge",
                                     description="Cloud-360 MCP bridge（需求欄位工具）")
    parser.add_argument("--backend-url", required=True, help="backend 的 base URL，例如 http://backend:8000")
    parser.add_argument("--host", default=DEFAULT_HOST, help="監聽位址（預設 127.0.0.1）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="監聽埠（預設 8080）")
    parser.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY,
                        help="同時處理中的 /mcp 請求上限（預設 16）")
    return parser.parse_args(list(argv) if argv is not None else [])


def main(argv: Optional[Sequence[str]], *, config_dir: Path = PACKAGE_DIR) -> int:
    args = parse_args(argv)
    configure_logging()
    # 程式審查 R-04：範圍外的數值走與設定錯誤相同的單行 ERROR，而不是以 traceback 結束。
    if not 1 <= args.port <= 65535:
        log_startup_failed("--port")
        return 1
    if args.max_concurrency < 1:
        log_startup_failed("--max-concurrency")
        return 1
    try:
        loaded = load_and_validate(config_dir)
    except StartupConfigError as err:
        log_startup_failed(err.subject)
        return 1
    # 驗證通過後才載入含 mcp 的模組（刻意的函式內 import，見模組說明）。
    from .server import serve
    return serve(loaded, args)
