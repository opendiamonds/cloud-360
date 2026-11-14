"""credentials.py — 使用者 token 的格式檢查（`BR73.1`）。

token 的唯一來源是該次 MCP HTTP 請求的 `Authorization` 標頭。格式為
`^Bearer [A-Za-z0-9._~+/=-]+$`、整個標頭值 ≤ 8192 位元組、恰一個值；缺漏、多值、格式不符、
超長一律判為未認證（不呼叫 backend）。bridge **不解碼** JWT（`BR73.5`）。

`RequestCredential` 是本單元唯一持有 token 的物件：`repr` 一律回固定字串，不可序列化。

純函式模組：不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

#: `Authorization` 標頭值的格式（`BR73.1`）。
AUTHORIZATION_PATTERN = re.compile(r"^Bearer [A-Za-z0-9._~+/=-]+$")
#: 標頭值長度上限（位元組，`NFR21.11`）。
MAX_AUTHORIZATION_BYTES = 8192


@dataclass(frozen=True, repr=False)
class RequestCredential:
    """單一請求內的使用者憑證；`raw` 為 `Authorization` 標頭原值（含 `Bearer `）。"""

    raw: str

    def __repr__(self) -> str:  # 防止 token 經 repr／log／例外訊息外流（`BR73.4`）
        return "<redacted>"

    __str__ = __repr__

    def __reduce__(self):  # 禁止 pickle 序列化
        raise TypeError("RequestCredential is not serializable")


def parse_credential(values: Sequence[str]) -> Optional[RequestCredential]:
    """回傳合格的憑證；不合格（含缺漏與多值）回 `None`，呼叫端判為 `unauthenticated`。"""
    if len(values) != 1:
        return None
    value = values[0]
    if not isinstance(value, str):
        return None
    try:
        size = len(value.encode("latin-1"))
    except UnicodeEncodeError:
        return None
    if size > MAX_AUTHORIZATION_BYTES:
        return None
    if AUTHORIZATION_PATTERN.fullmatch(value) is None:
        return None
    return RequestCredential(raw=value)
