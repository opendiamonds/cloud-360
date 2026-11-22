"""outcomes.py — 工具呼叫結果的封閉表（`BR76.1`–`BR76.4`）。

`map_outcome` 是 `BR76.1` 封閉表**唯一**的實作點：執行層的一切結果先收斂成封閉聯集
`ExchangeResult`（`Received`／`TransportFailure`／`ResponseTooLarge`／`InternalFailure`），
本地拒絕則由三個建構函式產生，兩者都只產出 `ToolOutcome`。

- `TransportFailure.kind` 為**恰四值**的封閉枚舉（`refused`、`timeout`、`dns`、`protocol`），
  四值一律映射為 `backend_unavailable`、`retryable: true`。
- `ResponseTooLarge`、`InternalFailure` 映射為 `internal_error`、`retryable: false`。
- 訊息只用固定文字或經 `BR76.2` 過濾的 backend `detail`；例外的 `str()`／`repr()` 永不進入訊息。

純函式模組：不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。
"""

from __future__ import annotations

import enum
import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional, Union


class ErrorCode(str, enum.Enum):
    """`BR76.1` 的七種錯誤碼。"""

    UNAUTHENTICATED = "unauthenticated"
    AGENT_NOT_DECLARED = "agent_not_declared"
    INVALID_ARGUMENT = "invalid_argument"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    INTERNAL_ERROR = "internal_error"


class TransportKind(str, enum.Enum):
    """傳輸失敗的封閉枚舉：恰四值（nfr-design `reliability-design.md` §1.1）。"""

    REFUSED = "refused"
    TIMEOUT = "timeout"
    DNS = "dns"
    PROTOCOL = "protocol"


@dataclass(frozen=True)
class Received:
    """backend 回了一個完整的 HTTP 回應（本體已在上限內讀完）。"""

    status: int
    body: bytes


@dataclass(frozen=True)
class TransportFailure:
    kind: TransportKind


@dataclass(frozen=True)
class ResponseTooLarge:
    """回應本體超過 `MAX_RESPONSE_BODY_BYTES`；已停止讀取。"""


@dataclass(frozen=True)
class InternalFailure:
    """bridge 內部未預期的例外；不攜帶例外物件或其文字。"""


ExchangeResult = Union[Received, TransportFailure, ResponseTooLarge, InternalFailure]


# ---- 固定訊息（`BR76.1`、`BR76.2`） -----------------------------------------------------
MSG_UNAUTHENTICATED_LOCAL = "需要使用者登入憑證"
MSG_UNAUTHENTICATED_BACKEND = "使用者憑證無效或已過期"
MSG_AGENT_NOT_DECLARED = "呼叫端未宣告已登錄的 agent 身分"
MSG_BACKEND_UNAVAILABLE = "後端暫時無法使用"
MSG_INTERNAL_ERROR = "轉接層內部錯誤"
MSG_FORBIDDEN_FALLBACK = "沒有存取此資源的權限"
MSG_NOT_FOUND_FALLBACK = "找不到指定的資源"
MSG_INVALID_FALLBACK = "參數不被接受"
MSG_UNKNOWN_TOOL = "Unknown tool"

#: `BR76.2` 的 `detail` 長度上限。
MAX_DETAIL_LENGTH = 200


@dataclass(frozen=True)
class ToolOutcome:
    """一次工具呼叫的結果。`ok` 與 `error` 恰一者成立。

    `http_status` 只供 log（`BR77.1`），不進工具結果。`unknown_tool` 標記「工具名不在
    已載入清單」：`app.py` 據此改以 JSON-RPC 協定錯誤回應（17-A，`BR76.3`）。
    """

    ok: bool
    payload: Optional[dict] = None
    error: Optional[ErrorCode] = None
    message: Optional[str] = None
    retryable: bool = False
    http_status: Optional[int] = None
    unknown_tool: bool = False

    def __post_init__(self) -> None:
        if self.ok == (self.error is not None):
            raise ValueError("ToolOutcome requires exactly one of ok / error")

    @property
    def outcome_label(self) -> str:
        """log 的 `outcome` 欄：`ok` 或錯誤碼。"""
        return "ok" if self.ok else self.error.value  # type: ignore[union-attr]

    def error_document(self) -> dict:
        """`BR76.3` 的錯誤內容 `{error, message, retryable}`。"""
        if self.ok:
            raise ValueError("error_document on a successful outcome")
        return {
            "error": self.error.value,  # type: ignore[union-attr]
            "message": self.message,
            "retryable": self.retryable,
        }


def _failure(code: ErrorCode, message: str, *, retryable: bool = False,
             http_status: Optional[int] = None, unknown_tool: bool = False) -> ToolOutcome:
    return ToolOutcome(ok=False, error=code, message=message, retryable=retryable,
                       http_status=http_status, unknown_tool=unknown_tool)


# ---- 本地拒絕（不呼叫 backend） ------------------------------------------------------
def unauthenticated_local() -> ToolOutcome:
    return _failure(ErrorCode.UNAUTHENTICATED, MSG_UNAUTHENTICATED_LOCAL)


def agent_not_declared() -> ToolOutcome:
    return _failure(ErrorCode.AGENT_NOT_DECLARED, MSG_AGENT_NOT_DECLARED)


def invalid_argument(message: str) -> ToolOutcome:
    """`message` 必須是固定文字（只可含**已宣告的**參數名，不得回顯值）。"""
    return _failure(ErrorCode.INVALID_ARGUMENT, message)


def unknown_tool() -> ToolOutcome:
    """工具名不在已載入清單：log 記 `invalid_argument`，回應改為協定錯誤（17-A）。"""
    return _failure(ErrorCode.INVALID_ARGUMENT, MSG_UNKNOWN_TOOL, unknown_tool=True)


def internal_error() -> ToolOutcome:
    return _failure(ErrorCode.INTERNAL_ERROR, MSG_INTERNAL_ERROR)


# ---- `BR76.2` 的 detail 過濾 --------------------------------------------------------
def _has_control_char(text: str) -> bool:
    return any(unicodedata.category(ch) == "Cc" for ch in text)


def filtered_detail(body: bytes) -> Optional[str]:
    """本體恰為 `{"detail": <字串>}` 且通過過濾時回傳 detail；否則 `None`。"""
    try:
        document: Any = json.loads(body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(document, dict) or set(document) != {"detail"}:
        return None
    detail = document["detail"]
    if not isinstance(detail, str) or not detail:
        return None
    if len(detail) > MAX_DETAIL_LENGTH or _has_control_char(detail):
        return None
    return detail


# ---- 封閉表 ---------------------------------------------------------------------------
_DETAIL_ROWS = {
    403: (ErrorCode.FORBIDDEN, MSG_FORBIDDEN_FALLBACK),
    404: (ErrorCode.NOT_FOUND, MSG_NOT_FOUND_FALLBACK),
    422: (ErrorCode.INVALID_ARGUMENT, MSG_INVALID_FALLBACK),
}


def _map_received(result: Received) -> ToolOutcome:
    status = result.status
    if status == 200:
        try:
            payload = json.loads(result.body)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return _failure(ErrorCode.INTERNAL_ERROR, MSG_INTERNAL_ERROR, http_status=status)
        if not isinstance(payload, dict):
            return _failure(ErrorCode.INTERNAL_ERROR, MSG_INTERNAL_ERROR, http_status=status)
        return ToolOutcome(ok=True, payload=payload, http_status=status)
    if status == 401:
        return _failure(ErrorCode.UNAUTHENTICATED, MSG_UNAUTHENTICATED_BACKEND, http_status=status)
    if status in _DETAIL_ROWS:
        code, fallback = _DETAIL_ROWS[status]
        detail = filtered_detail(result.body)
        return _failure(code, detail if detail is not None else fallback, http_status=status)
    if 500 <= status <= 599:
        return _failure(ErrorCode.BACKEND_UNAVAILABLE, MSG_BACKEND_UNAVAILABLE,
                        retryable=True, http_status=status)
    return _failure(ErrorCode.INTERNAL_ERROR, MSG_INTERNAL_ERROR, http_status=status)


def map_outcome(result: ExchangeResult) -> ToolOutcome:
    """`BR76.1` 封閉表的唯一實作點。未登錄的輸入型別一律 `internal_error`。"""
    if isinstance(result, Received):
        return _map_received(result)
    if isinstance(result, TransportFailure):
        if not isinstance(result.kind, TransportKind):
            return internal_error()
        return _failure(ErrorCode.BACKEND_UNAVAILABLE, MSG_BACKEND_UNAVAILABLE, retryable=True)
    if isinstance(result, (ResponseTooLarge, InternalFailure)):
        return internal_error()
    return internal_error()
