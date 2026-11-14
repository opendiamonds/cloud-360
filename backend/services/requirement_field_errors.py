"""
requirement_field_errors.py — `U20 requirement-field-service` 的領域例外

**契約（同進程呼叫端依賴，請勿變更）**

四個例外型別**都不是** `HTTPException` 的子類別（契約 `K-17` 的 `on_denied`：
`raise RequirementFieldForbidden(...)`）。`U13 brain-gateway` 是同進程呼叫端，
沒有 HTTP 回應可回；轉譯成狀態碼的唯一落點是 `requirement_field_router._translate()`：

| 例外 | HTTP | 規則 |
|---|---|---|
| `RequirementFieldForbidden` | 403 | `BR41.1`／`BR41.2` |
| `RequirementFieldNotFound` | 404 | `BR41.3`、`BR41.4`（非成員；合併前必修第 14 項） |
| `UnknownFieldKey` | 422 | `BR42.1`／`BR42.2` |
| `RequirementFieldValidationError` | 422 | `BR42.3`–`BR42.5`、值含 NUL（合併前必修第 24 項）、請求本體形狀（`BR46.4`） |

**每個例外的訊息都是固定文字**（`BR46.3`／`NFR20.14`）：只帶錯誤類別與定址欄位
（`system_id`、`agent_group`、`field_key`），**永不**帶欄位值、代寫標示的值或任何
輸入原文——router 把 `str(exc)` 原樣作為 `detail` 送出，所以這裡就是「錯誤回應不含值」
的唯一保證處。
"""

from __future__ import annotations

from typing import Optional

from services.hierarchy_facade import SYSTEM_NOT_FOUND_DETAIL
from services.requirement_field_definitions import KEY_PATTERN

STORY_ID = "K4"

NOT_FOUND_DETAIL = SYSTEM_NOT_FOUND_DETAIL
"""404 的唯一訊息（不存在、非整數 id、缺 `K2.view`、非成員皆同；合併前必修第 14 項）。

**不另抄字串**：沿用 `hierarchy_facade.SYSTEM_NOT_FOUND_DETAIL`（單一真實來源），
與階層端點的「查不到系統」同一句。
"""


class RequirementFieldError(Exception):
    """本單元所有領域例外的基底。**刻意不繼承 `HTTPException`。**"""


class RequirementFieldForbidden(RequirementFieldError):
    """授權未通過。router 轉 403。

    `reason` 只有 `pending`（`BR41.1`）／`global`（`BR41.2`）兩種，與拒絕 log 的
    `reason` 欄位一對一對應（`NFR20.27`）。**對外訊息不區分兩者。**

    **非成員不走本例外**（合併前必修第 14 項，`[PP-MB14]`=A）：`not_member`（`BR41.4`）
    只是拒絕 log 的 `reason` 值——`requirement_field_facade._authorize` 照記
    `requirement_field.denied ... reason=not_member` 的 WARNING 後丟的是
    `RequirementFieldNotFound`，對外為 404，與「系統不存在」逐位元相同。
    """

    def __init__(
        self,
        *,
        action: str,
        reason: str,
        system_id: Optional[int] = None,
        story_id: str = STORY_ID,
    ) -> None:
        super().__init__(f"權限不足：無法{_ACTION_LABELS.get(action, action)}此系統的需求欄位")
        self.story_id = story_id
        self.action = action
        self.reason = reason
        self.system_id = system_id


class RequirementFieldNotFound(RequirementFieldError):
    """查不到該系統（`BR41.3`）。router 轉 404。

    也用於非整數的 `system_id`（它不可能是任何一個系統）與「呼叫端缺 `K2.view`」
    ——後者與 `U19` 對同一情形的處置一致（`membership_facade._assert_project_exists`）。

    **也用於「系統存在但呼叫者不是所屬專案的成員」**（合併前必修第 14 項，
    `[PP-MB14]`=A）。故訊息**固定為 `NOT_FOUND_DETAIL`、不含 id**：兩種情形的回應
    必須逐位元相同，帶 id 只會讓訊息成為另一個可比對的訊號。`system_id` 仍留在屬性上
    供同進程呼叫端與 log 使用，不進對外訊息。
    """

    def __init__(self, system_id: Optional[int] = None) -> None:
        super().__init__(NOT_FOUND_DETAIL)
        self.system_id = system_id


class UnknownFieldKey(RequirementFieldError):
    """`agent_group` 未宣告，或 `field_key` 不在該組底下（`BR42.1`／`BR42.2`）。

    **錯綁到別組也是這個例外**（`AC11.2.2`）：判定對象是程式內定義，不是資料表內
    已有的列。訊息帶的兩個值來自 URL 路徑（定址欄位），不是使用者填寫的欄位值。
    """

    def __init__(self, agent_group: str, field_key: str) -> None:
        # 只在兩者都是合格識別字形狀時才寫進訊息：路徑片段雖不是欄位值，但不合
        # 形狀的字串沒有定址價值，原樣回顯只會把任意輸入帶進回應本體。
        if all(
            isinstance(part, str) and KEY_PATTERN.match(part)
            for part in (agent_group, field_key)
        ):
            super().__init__(f"未宣告的需求欄位：{agent_group}/{field_key}")
        else:
            super().__init__("未宣告的需求欄位")
        self.agent_group = agent_group
        self.field_key = field_key


class RequirementFieldValidationError(RequirementFieldError):
    """輸入不合法。router 轉 422。

    `field` 只會是固定集合之一：`value`／`on_behalf_of`／`body`／`system_id`。
    訊息由呼叫端從 `_VALIDATION_MESSAGES` 選，不接受任意文字，故不可能夾帶輸入。
    """

    def __init__(self, field: str, problem: str) -> None:
        message = _VALIDATION_MESSAGES.get((field, problem))
        if message is None:
            raise ValueError(f"未登錄的驗證錯誤：{field}/{problem}")
        super().__init__(message)
        self.field = field
        self.problem = problem


_ACTION_LABELS = {"view": "讀取", "edit": "修改"}

_VALIDATION_MESSAGES = {
    ("value", "type"): "value 必須是字串",
    ("value", "too_long"): "value 去除首尾空白後不得超過 2000 字",
    # 合併前必修第 24 項：PostgreSQL 的 text／varchar 不能存 NUL（0x00），psycopg 在
    # dump 階段拋 `DataError`，未擋下時會成為 500。固定文字、不回顯值。
    ("value", "nul_char"): "value 不得含 NUL 字元（U+0000）",
    ("value", "blank_on_behalf"): (
        "代寫路徑不得以空值清空欄位；要清空請呼叫清空操作（DELETE）"
    ),
    ("on_behalf_of", "type"): "on_behalf_of 必須是字串或 null",
    ("on_behalf_of", "unknown_group"): "on_behalf_of 必須是已宣告的 agent 組或 null",
    ("body", "not_json_object"): "請求本體必須是 JSON 物件",
    ("body", "missing_value"): "請求本體缺少 value",
    ("body", "unknown_field"): "請求本體含未宣告的欄位；只接受 value 與 on_behalf_of",
}


__all__ = [
    "NOT_FOUND_DETAIL",
    "RequirementFieldError",
    "RequirementFieldForbidden",
    "RequirementFieldNotFound",
    "RequirementFieldValidationError",
    "STORY_ID",
    "UnknownFieldKey",
]
