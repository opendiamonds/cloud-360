"""intent_routing_errors.py — `U11 intent-router` 的四種失敗型別

**契約（同進程呼叫端依賴，請勿變更）**

`NFR3.74` 要求分類失敗率**按錯誤型別分計**，而那個要求的前提是四種失敗在程式裡
是**四個型別**，不是四個訊息字串（`reliability-design.md` §一）。

| 型別 | 觸發 | 使用者看到 |
|---|---|---|
| `LlmUnavailable` | 連線失敗、5xx、429、逾時 | 「請再說一次」 |
| `LlmBudgetExceeded` | 供應商回報用量上限 | 同上 |
| `EmptyCandidates` | 分類器回空清單（`BR2.4`／`V-1`） | 同上 |
| `MalformedRouting` | JSON 不合、`capability` 不在列舉、`slot` 不連續、超出上界 | 同上 |

**四個型別、一種使用者體驗**：使用者分不出來也不需要分，但**維運必須分得出來**
——`LlmUnavailable` 是供應商的事，`MalformedRouting` 是我們的 prompt 或 schema
壞了。混成一個 `RoutingError` 會讓這兩件事在圖表上長得一樣。

共同基底 `IntentRoutingError` 的用途與其風險
--------------------------------------------

基底存在的理由是 `U13` 需要一個 `except` 子句涵蓋全部四種（四者的使用者體驗
相同）。**風險是它讓「分型」可以被一行 `except IntentRoutingError` 抹平**，
所以：分型的識別字一律取 `type(exc).__name__`（具體類別名），**不得**以基底名
填 `RoutingObservation.error_kind`。`tests/test_intent_routing_structure.py`
斷言四個型別彼此不同且都不等於基底。

`PlatformSelfModificationRefused` **不是**失敗（`BR1.3`）
-------------------------------------------------------

它**刻意不繼承** `IntentRoutingError`。`prompt_guard` 命中時回的固定訊息
**是一個有內容的有效回覆**，該輪正常以 `done` 結束、**不是** `error`
（`K-10` 的 `hard_rules` 逐字）。把它歸進失敗基底，會讓一個
`except IntentRoutingError: send_error(...)` 的呼叫端把「系統正確地拒絕了」
呈現成「系統故障」——而那是狀態機上最容易畫錯的一條邊
（`functional-spec.md` §二）。
"""

from __future__ import annotations

from services.prompt_guard import REFUSAL_MESSAGE


class IntentRoutingError(Exception):
    """四種分類失敗的共同基底。**分型請用具體類別名，不要用它。**"""


class LlmUnavailable(IntentRoutingError):
    """連線失敗、5xx、429、逾時（`NFR3.68`；`K-10` 的 `raises`）。

    **429 也在這裡，而這是刻意的**：`NFR9.62` 逐字「不設本單元層級的速率限制
    或排隊機制。達到供應商速率限制時的行為是 `LlmUnavailable`（`BR8.2`
    大聲失敗），不是靜默排隊」。
    """


class LlmBudgetExceeded(IntentRoutingError):
    """供應商回報用量上限（`NFR3.68`；`K-10` 的 `raises`）。"""


class EmptyCandidates(IntentRoutingError):
    """分類器回空候選清單（`BR2.4`／`V-1`／`NFR3.69`）。

    **這是失敗，不是「判不出來」。** 判不出來是「有多個候選但選不出一個」。
    把失敗當成反問，會讓一個壞掉的分類器看起來像在謹慎發問——而
    `functional-spec.md` §二 的狀態機逐字要求 `failed` 與 `clarifying`
    不得共用出口。
    """


class MalformedRouting(IntentRoutingError):
    """模型回了不合 schema 的輸出（`NFR3.70`；`V-2`／`V-3`／`V-4`）。

    **超出上界走這裡而不是 `BR2.4`**：`BR2.4` 的逐字定義是「分類器回空候選
    清單」，與「`slot` 超出上界」是完全不同的條件。混計會污染 `NFR3.74` 的
    分型失敗率——把「供應商吐出一個失控的大槽位數」與「供應商真的吐空清單」
    計進同一條曲線（`performance-design.md` 修訂 1，審查 `R-04`）。

    **處置一律是失敗，不是截斷或補齊**——靜默修補正是 `functional-design`
    審查 `R-01` 查出的那個失敗模式。
    """


class PlatformSelfModificationRefused(Exception):
    """`prompt_guard` 命中。**不是失敗**——見模組 docstring。

    `K-10` 的 `public_interface` 把 `classify` 的 `returns` 固定為
    `IntentDecision`，而固定拒絕訊息**不是**一個 `IntentDecision`：
    `EC4`／`EC5` 要求 `intents` 與 `candidates` 恰有一邊非空，兩邊皆空的
    `IntentDecision` 違反 `EC5`。設計層沒有為這條路徑指定回傳形狀
    （`functional-spec.md` 的 `W2` 只說「回固定拒絕訊息」），故本站以一個
    **刻意不繼承失敗基底**的具名訊號承載它，並把 `message` 預填為
    `prompt_guard.REFUSAL_MESSAGE`（單一真實來源，不另抄一份字串）。

    **呼叫端義務（`BR1.3`）**：收到本訊號時送出 `self.message` 的內容並以
    `done` 結束該輪，**不得**以 `error` 結束。
    """

    def __init__(self, message: str = REFUSAL_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


__all__ = [
    "EmptyCandidates",
    "IntentRoutingError",
    "LlmBudgetExceeded",
    "LlmUnavailable",
    "MalformedRouting",
    "PlatformSelfModificationRefused",
]
