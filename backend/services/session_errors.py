"""session_errors.py — `U10 session-store` 的例外型別與原因碼

**契約（同進程呼叫端依賴，請勿變更）**

契約 `K-09` 的 `public_interface` 對每一個方法都列 `raises:
[SessionBackendUnavailable]`。本檔是那個型別的落點，另加一個 `OQ-N4` 授權的
新型別。

安全邊界（`BR3.6`／`EC6`／`NFR4.45`）：

- **例外訊息只帶原因碼與方法名。** 不帶 `SessionMessage.text`、不帶整個
  `ConversationSegment`、不帶整個 `BrainSession`、不帶三層作業對象識別碼。
  本 repo 為 public 且 Actions log 公開可讀（`project.md` 逐字「一次意外 echo
  即等同公開發布」），而本單元持有的是**個人對話內容**。
- `SessionMessageTooLong` 只帶**長度數字**，不帶被拒的文字。長度是中繼資料，
  不是內容——這條界線與 `security-design.md §一` 的「識別碼不是內容」同形。

## 三個原因碼（`NFR4.62`）

`K-09` 的契約只有**一個**後端失效例外型別，本檔**不改它**；可區分性由
`reason` 欄位承載，而非新增型別。`observability-design.md §三` 的判定來源：

| 原因碼 | 判定方式 |
|---|---|
| `redis_unreachable` | 客戶端的連線層例外（連線拒絕／逾時／DNS） |
| `redis_oom` | Redis 回覆 `OOM ...`（`noeviction` 之下的寫入拒絕） |
| `redis_command_error` | 其他指令層錯誤（ACL 拒絕、腳本錯誤） |

三者在日誌上必須可區分，否則 `[N3]`=A 只是把無聲換成了含糊。

## 為什麼 `SessionMessageTooLong` 不是 `SessionBackendUnavailable`

「訊息太長」是**呼叫方的輸入問題**，後端完全健康。兩者同型會讓 `U13` 無法
分辨「請縮短訊息」與「稍後再試」，而 `nfr-design` 審查 `R-02`（Major）逐字
指出 `K-09` 的凍結介面裡沒有型別能承載前者。新增型別的授權依據是
`contract-summary.md:1433` 的 `OQ-N4`（逐字授權改 `U10` 的 `public_interface`）。
"""

from __future__ import annotations

#: 連線層失敗：連線被拒、逾時、名稱無法解析。
REDIS_UNREACHABLE = "redis_unreachable"

#: 記憶體耗盡造成的寫入拒絕（`noeviction`）。讀取在此狀態下仍可用（`NFR4.51`）。
REDIS_OOM = "redis_oom"

#: 其他指令層錯誤：ACL 拒絕（`NOPERM`）、腳本錯誤、型別錯誤。
REDIS_COMMAND_ERROR = "redis_command_error"

#: 封閉集合。`SessionBackendUnavailable` 拒絕任何不在其中的原因碼——
#: 一個拼錯的原因碼會讓 `NFR4.62` 的可區分性靜默失效。
REASON_CODES = frozenset({REDIS_UNREACHABLE, REDIS_OOM, REDIS_COMMAND_ERROR})


class SessionStoreError(Exception):
    """本單元所有例外的基底。刻意不繼承 `HTTPException`。

    `BR5.3`：本單元不暴露任何對外端點，故沒有「轉成 HTTP 狀態碼」這件事要做。
    `U13` 收到例外後自行決定對客戶端說什麼。
    """


class SessionBackendUnavailable(SessionStoreError):
    """Redis 不可用（`BR6.1`）。**不降級、不退回行程記憶體、不回空 session。**

    回一個空的 `BrainSession` 會讓畫面看起來「只是脈絡被清掉了」，而那與 TTL
    到期在使用者眼中完全相同——一個是正常行為、一個是基礎設施故障，兩者不可
    區分即等於故障不可偵測（`functional-spec.md` 的 `W8` 第 4 步）。
    """

    def __init__(self, reason: str, *, method: str) -> None:
        if reason not in REASON_CODES:
            raise ValueError(
                f"未知的原因碼 {reason!r}；允許值為 {sorted(REASON_CODES)}"
            )
        # 訊息只含原因碼與方法名——兩者都不是內容（`BR3.6`）。
        super().__init__(f"session 後端不可用：reason={reason} method={method}")
        self.reason = reason
        self.method = method


class SessionMessageTooLong(SessionStoreError):
    """單則訊息超過長度上限（`OPEN-N10-6`）。**不是後端失效。**

    `security-design.md §三` 定三件事，本型別承載第三件：超限的行為是**拒絕
    並回可辨識的錯誤**，不是截斷——截斷會讓使用者的訊息被默默改掉。

    **不帶被拒的文字**：只帶上限與實際長度，供 `U13` 組出「請縮短至 N 字元」
    這類訊息。
    """

    def __init__(self, *, limit: int, actual: int) -> None:
        super().__init__(f"訊息長度 {actual} 超過上限 {limit} 字元")
        self.limit = limit
        self.actual = actual


__all__ = [
    "REASON_CODES",
    "REDIS_COMMAND_ERROR",
    "REDIS_OOM",
    "REDIS_UNREACHABLE",
    "SessionBackendUnavailable",
    "SessionMessageTooLong",
    "SessionStoreError",
]
