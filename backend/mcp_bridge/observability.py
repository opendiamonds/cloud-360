"""observability.py — bridge 進程唯一的 logging 設定點與事件紀錄（`BR77.1`、`BR77.2`、`NFR21.33`–`NFR21.36`）。

- logger 名稱只有 `cloud360.mcp_bridge`（`team.md` 的 logger 命名規則；本套件內 `getLogger` 只出現在此）。
- `configure_logging()`：根 logger WARNING ＋ 一個寫 stderr、以 `BridgeFormatter` 格式化的 handler；
  `cloud360.mcp_bridge` 為 INFO；`httpx`、`mcp` 為 WARNING（httpx 在 INFO 會記含 `system_id` 的 URL；
  SDK 每個請求有一行 INFO，Step 1 實測假設 S-11）。正式啟動與測試呼叫同一支。
- `BridgeFormatter`：格式化完成後把 `\\r`、`\\n` 換成字面跳脫，**每一筆紀錄恰為一行**，不論來源。
- 事件欄位只來自封閉集合或整數；呼叫端可控的字串（工具名、agent 宣告）一律先正規化。

本模組不 import `mcp`、`httpx`（它只以名稱設定其 logger 層級）。
"""

from __future__ import annotations

import json
import logging
import sys
from typing import IO, Iterable, Optional

LOGGER_NAME = "cloud360.mcp_bridge"
logger = logging.getLogger(LOGGER_NAME)

#: 第三方 logger 與其層級（`NFR21.33`；Step 1 的 S-10／S-11）。
THIRD_PARTY_LEVELS = {"httpx": logging.WARNING, "httpcore": logging.WARNING, "mcp": logging.WARNING}

#: `request_rejected` 的 `reason` 封閉集合與對應狀態碼。
REJECT_REASONS = {
    "over_concurrency": 503,
    "body_too_large": 413,
    "body_timeout": 408,
    "request_timeout": 503,
    "method_not_allowed": 405,
}

UNKNOWN_TOOL = "unknown"
_HANDLER_FLAG = "_cloud360_mcp_bridge_handler"


class BridgeFormatter(logging.Formatter):
    """單行格式：`<時間> <層級> <logger> <訊息>`，`\\r`／`\\n` 一律跳脫。"""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return text.replace("\r", "\\r").replace("\n", "\\n")


def configure_logging(stream: Optional[IO[str]] = None) -> None:
    """設定層級與 handler；重複呼叫不會疊加 handler。"""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_FLAG, False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(BridgeFormatter())
    setattr(handler, _HANDLER_FLAG, True)
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logger.setLevel(logging.INFO)
    for name, level in THIRD_PARTY_LEVELS.items():
        logging.getLogger(name).setLevel(level)


def normalize_tool(name: object, declared: Iterable[str]) -> str:
    """log 的 `tool` 欄：已宣告名原樣，其餘一律 `unknown`（nfr-requirements 審查 R-06）。"""
    return name if isinstance(name, str) and name in set(declared) else UNKNOWN_TOOL


def log_tool_call(*, tool: str, agent: str, outcome: str, http_status: Optional[int],
                  duration_ms: int) -> None:
    """每次 `tools/call` 恰一行 INFO（`BR77.1`）；只由 `dispatch.run_tool_call` 呼叫。"""
    status = "null" if http_status is None else str(int(http_status))
    duration = max(0, int(duration_ms))
    logger.info(
        "tool_call tool=%s agent=%s outcome=%s http_status=%s duration_ms=%d",
        tool, agent, outcome, status, duration,
        extra={"event": "tool_call", "fields": {
            "tool": tool, "agent": agent, "outcome": outcome,
            "http_status": http_status, "duration_ms": duration,
        }},
    )


def log_request_rejected(reason: str) -> None:
    """HTTP 層拒絕各記恰一行 WARNING；不含本體、標頭、來源位址或長度數值。"""
    status = REJECT_REASONS[reason]
    logger.warning("request_rejected reason=%s http_status=%d", reason, status,
                   extra={"event": "request_rejected",
                          "fields": {"reason": reason, "http_status": status}})


def log_internal_failure(exc_type: str) -> None:
    """總攔截到未預期例外：只記例外**型別名**（`BR77.2`）。"""
    safe = exc_type if exc_type.isidentifier() else "Exception"
    logger.warning("internal_failure exc_type=%s", safe,
                   extra={"event": "internal_failure", "fields": {"exc_type": safe}})


def log_startup(*, port: int, tools: int) -> None:
    logger.info("startup port=%d tools=%d", int(port), int(tools),
                extra={"event": "startup", "fields": {"port": int(port), "tools": int(tools)}})


def log_startup_failed(subject: str) -> None:
    """啟動自我驗證失敗：恰一行 ERROR，`subject` 以 ASCII JSON 字串輸出（單行、可讀）。"""
    rendered = json.dumps(str(subject), ensure_ascii=True)
    logger.error("startup_failed subject=%s", rendered,
                 extra={"event": "startup_failed", "fields": {"subject": str(subject)}})
