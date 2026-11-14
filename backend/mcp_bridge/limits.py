"""limits.py — bridge 全部數值上限的單一來源（`NFR21.24`）。

七個具名常數各定義恰一次；其他模組一律經 `BridgeLimits` 取值，不另立數字。
`derive_allowed_hosts` 是 Host 允許清單的唯一推導點（`BR71.6`；nfr-requirements 審查 R-04：
清單隨實際埠推導，預設埠 8080 時恰為三項）。

本模組不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。

## 時限的關係式（寫進 compose 的 `stop_grace_period` 註解）

`REQUEST_WALL_TIMEOUT_S`（13 秒）涵蓋一次 `/mcp` 請求從通過並行閘到回應送完的全程，
其中本體讀取期限 `BODY_READ_TIMEOUT_S`（2 秒）與對 backend 的整體上限 `OVERALL_TIMEOUT_S`
（10 秒）都在它之內，並另留 1 秒給 SDK 的序列化與回應（程式審查 R-02：原本 12 秒恰等於 2 ＋ 10、零餘裕，
backend 掛住時牆鐘可能先觸發，client 得到裸 503 而不是 `backend_unavailable`）。
關係式：本體期限 ＋ 整體上限 ＋ 1 ≤ 牆鐘（2 ＋ 10 ＋ 1 ≤ 13），牆鐘 ＋ 1 < `stop_grace_period`（13 ＋ 1 = 14 < 15），
SIGKILL 不會截斷進行中的請求。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 對 backend 建立連線的上限（`BR75.1`）。
CONNECT_TIMEOUT_S = 3.0
#: 一次 backend 交換（送出＋逐塊讀取本體）的整體上限（`BR76.1`、`NFR21.1`）。
OVERALL_TIMEOUT_S = 10.0
#: `/mcp` 請求本體的上限（`NFR21.20`）。
MAX_REQUEST_BODY_BYTES = 65536
#: 同時處理中的 `/mcp` 請求上限的預設值（`NFR21.21`；`--max-concurrency` 可覆寫）。
DEFAULT_MAX_CONCURRENCY = 16
#: backend 回應本體的上限（`NFR21.22`）。
MAX_RESPONSE_BODY_BYTES = 1048576
#: 讀完請求本體的期限，逾時回 408（nfr-design 審查 R-01）。
BODY_READ_TIMEOUT_S = 2.0
#: 一次 `/mcp` 請求的牆鐘上限，逾時回 503（nfr-design 審查 R-01）。
REQUEST_WALL_TIMEOUT_S = 13.0


@dataclass(frozen=True)
class BridgeLimits:
    """一個 bridge 實例的全部上限；預設值取自上列常數。"""

    connect_timeout_s: float = CONNECT_TIMEOUT_S
    overall_timeout_s: float = OVERALL_TIMEOUT_S
    max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    max_response_body_bytes: int = MAX_RESPONSE_BODY_BYTES
    body_read_timeout_s: float = BODY_READ_TIMEOUT_S
    request_wall_timeout_s: float = REQUEST_WALL_TIMEOUT_S

    def __post_init__(self) -> None:
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")


def derive_allowed_hosts(port: int) -> tuple[str, ...]:
    """Host 允許清單：compose 服務名與兩種本機迴環寫法，皆帶實際埠（`BR71.6`）。"""
    if not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536:
        raise ValueError("port must be an integer in 1..65535")
    return (f"mcp-bridge:{port}", f"localhost:{port}", f"127.0.0.1:{port}")
