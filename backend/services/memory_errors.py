"""
memory_errors.py — `U8 memory-service` 的領域例外

**契約（同進程呼叫端依賴，請勿變更）**

四個例外型別**都不是** `HTTPException` 的子類別，也都不 raise 它
（契約 `K-08` 的 `on_denied`；`logical-components.md §1.1` 逐字）。

為什麼這件事是結構性的而不是風格偏好：`MemoryFacade` **同時**被 HTTP
（`U15 memory-page-ui`）與**同進程**（`U11 intent-router`，經 `K-10`）消費。
`U11` 的 `classify` 不在 FastAPI 的 dependency 鏈上，拋 `HTTPException` 會讓它
收到一個它無法處理、也無處可回的型別。

轉譯成 HTTP 狀態碼的唯一落點是 `memory_router._translate()`：

| 例外 | HTTP |
|---|---|
| `MemoryForbidden` | 403 |
| `MemoryNotFound` | **404** |
| `MemoryInvalidInput` | 422 |
| `EmbeddingProviderUnavailable`（`U6` 的，非本檔） | 503 |

## `[D1]`=A：刪除路徑**不**使用 `MemoryForbidden`

`BR4.1` 的 `violation_behaviour` 原文是
`MemoryForbidden(reason="owner") → 403`，而 `nfr-design/security-design.md §二`
的 `[D1]`=A **推翻了它的對外半邊**：刪除路徑把「不存在」與「非擁有者」
**收斂為同一個 404**。

理由是 `schema_rbac.sql` 的 `id SERIAL PRIMARY KEY` 是**連續整數**，故
403／404 的差異讓任何已認證使用者得以走訪 `1..N` 取得**整張表哪些 id 存在**
——那是整張表的枚舉，不是單點存在性洩漏。

**內部保留區分**：`MemoryFacade` 在拋 `MemoryNotFound` 之前以 `reason="owner"`
寫一筆拒絕日誌（`NFR7.30`）。若連日誌也收斂，營運端就無法分辨
「使用者誤刪已刪除的記憶」與「有人在枚舉」——而後者是需要被看到的。

**故 `MemoryForbidden` 在本單元只由角色模型使用**（`BR5.1`／`BR6.1`，
`reason="scope"`）。那兩條路徑不需要收斂，因為它們**先判角色、後取記憶**
（`NFR7.22`），無權者在任何 id 上都得到同一個 403，oracle 本來就不存在。

**代價已記為 `D8-1`**（偏離 `K-08` 宣告的 `raises`／403），須在下一輪契約修訂
追認。本單元**不改已核可的契約檔**。
"""

from __future__ import annotations

from typing import Optional, Sequence


class MemoryError(Exception):
    """本單元所有領域例外的基底。**刻意不繼承 `HTTPException`。**"""


class MemoryForbidden(MemoryError):
    """授權未通過。router 轉 403。

    `reason` 的兩個值對應 `rules.md §2.1` 的兩套授權模型，而它同時是
    `NFR7.30` 拒絕日誌的欄位之一，使日誌與例外可互相對照：

    - `"scope"`：**角色模型**（`BR5.1` 放寬、`BR6.1` 稽核查詢）。
    - `"owner"`：**擁有者模型**（`BR4.1`）。**刪除路徑不拋本例外**——
      見本檔檔頭的 `[D1]`=A；該值保留給日誌與未來可能的非收斂路徑。

    `principal` 刻意不放進例外：它是呼叫端已經持有的東西，放進去只會讓錯誤
    訊息多帶一個身分識別（沿用 `MembershipForbidden` 的同一個決定）。
    """

    def __init__(self, reason: str, memory_id: Optional[str] = None) -> None:
        super().__init__(
            f"權限不足（{reason}）"
            + (f"：記憶 {memory_id}" if memory_id is not None else "")
        )
        self.reason = reason
        self.memory_id = memory_id


class MemoryNotFound(MemoryError):
    """查不到該記憶。router 轉 404。

    **在刪除路徑上，本例外同時涵蓋「不存在」與「非擁有者」**（`[D1]`=A）。
    這是刻意的收斂，而**訊息不得洩漏任何差異**——訊息文字是對外可見的，
    若兩種情境的 `detail` 不同，枚舉 oracle 就從狀態碼搬到了回應本體裡，
    收斂等於沒做。故本例外**不接受**任何描述記憶內容或擁有者的參數。

    `AC4.2.*`／`BR4.3`：重複刪除已不存在的記憶回報本例外，且**不產生稽核事件**
    ——若產生，一個重試迴圈會為同一次刪除製造多筆稽核，使 `AC4.3.2` 的查詢
    結果失真。
    """

    def __init__(self, memory_id: Optional[str] = None) -> None:
        # 刻意只帶 id（呼叫端自己送來的值），不帶任何查到的欄位。
        super().__init__(
            "找不到該記憶" + (f"：{memory_id}" if memory_id is not None else "")
        )
        self.memory_id = memory_id


class MemoryInvalidInput(MemoryError):
    """輸入不合封閉集合或欄位約束。router 轉 422。

    承載 `EC2`（`content` 去除前後空白後非空）、`EC3`（`kind` 與
    `visibilityScope` 的封閉集合）與 `BR5.2`（放寬的方向）。

    **與 `BR1.2` 的靜默忽略刻意不同**：酬載帶 `ownerUserId`／`visibilityScope`
    **不**拋本例外，而是忽略且回成功。回 422 會讓呼叫端以為「換個欄位名就能
    指定」，而忽略使該能力不存在（`NFR7.20`／`NFR7.21`）。

    訊息必須同時給出**不合法的值與合法集合**（`BR2.3` 的
    `violation_behaviour` 逐字）——只說「不合法」的訊息會讓呼叫端去猜。
    """

    def __init__(
        self, field: str, value: object, allowed: Optional[Sequence[str]] = None
    ) -> None:
        detail = f"{field} 的值 {value!r} 不合法"
        if allowed:
            detail += "；合法值為 " + "｜".join(allowed)
        super().__init__(detail)
        self.field = field
        self.value = value
        self.allowed = tuple(allowed) if allowed else ()


__all__ = [
    "MemoryError",
    "MemoryForbidden",
    "MemoryInvalidInput",
    "MemoryNotFound",
]
