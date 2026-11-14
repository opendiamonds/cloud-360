"""
requirement_field_types.py — `U20 requirement-field-service` 的檢視型別與請求本體

**契約（前端依賴，請勿變更）**：這些 pydantic model 同時是 facade 的回傳型別與
router 的 `response_model`，故它們的欄位集合就是 `openapi.json` 與
`frontend/src/types/api.d.ts` 裡的形狀（`team.md` 規則 B 的測試斷言它）。

## 命名：snake_case，而不是設計文件的 camelCase

`entities.md`／`functional-spec.md` 以 camelCase 記名（`unfilledCount`、`filledState`），
那是設計記法；本 repo 的回應模型一律 snake_case（`membership_router`、`memory_types`），
而 `K-17` 的 `returns` 字面本身就是 `unfilled_count`。故這裡取 snake_case，使
`K-17` 的這一個字面不需要追認（`OPEN-RF20-5` 由六項中少一項）。

## 相對於 `K-17` 的增量（`OPEN-RF20-5`，下一輪契約修訂追認）

`FieldGroupView` 的 `title`／`filled_count`／`total_count`、`FieldView` 的 `label`
（functional-spec 2.3），以及 `FieldSetView.input_hint`（nfr-design 的填寫提示，
`OPEN-RF20-9`）。理由都是同一條：組標題、欄位標籤與提示是程式內定義的一部分，
不隨回應送出，`U23` 就得在前端另抄一份。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FilledState(str, Enum):
    """三態（`ADR-015`；推導規則見 `BR44.1`）。"""

    NEVER_FILLED = "never_filled"
    FILLED = "filled"
    CLEARED = "cleared"


class FieldView(BaseModel):
    """單一欄位的檢視（`write_field`／`clear_field` 的回傳、`FieldGroupView` 的元素）。

    `never_filled`（含第四種列）一律回 null 的 `cleared_at`／`updated_at`／
    `updated_by`／`updated_on_behalf_of`（functional-design `review-02` R-06）：
    回列上的值會讓一個「從未填過」的欄位帶著「最後更新者」，畫面無從判斷該不該顯示。
    """

    group_key: str
    field_key: str
    label: str
    value: Optional[str] = None
    filled_state: FilledState
    cleared_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    updated_on_behalf_of: Optional[str] = None


class FieldGroupView(BaseModel):
    """一個 agent 組的明細。`fields` 恆等於該組宣告的欄位集合（`BR44.5`）。"""

    group_key: str
    title: str
    filled_count: int
    total_count: int
    fields: List[FieldView]


class FieldSetView(BaseModel):
    """`read_fields` 的回傳。

    **`unfilled_count` 與 `groups` 由同一次資料庫查詢推導、在同一個回應內回傳**
    （不變量 `I-4`／`BR44.4`）：總覽籤與需求籤讀的是同一個 `GET` 的同一個回應，
    本 router 刻意沒有「只回計數」的端點（`NFR20.3`）。
    """

    system_id: int
    unfilled_count: int
    input_hint: str
    groups: List[FieldGroupView]


class RequirementFieldWriteIn(BaseModel):
    """`PUT` 的請求本體：`{ "value": str, "on_behalf_of": str | null }`。

    **`extra="forbid"`**：本體帶 `updated_by`（或任何未宣告欄位）→ 422
    （`NFR20.10`，使用者 2026-10-12 同意）。寫入者恆為已驗證的 principal（`BR45.1`）。

    **本 model 不由 FastAPI 驗證**：router 讀原始本體，由 facade 在**授權通過之後**
    以 `model_validate_json` 解析（`BR41.5`／`BR46.4`）——否則框架的 422 會早於授權，
    且其 `detail` 會回顯輸入。router 只用它的 JSON schema 宣告 OpenAPI 的
    `requestBody`，使產生的型別檔仍有本體形狀。
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    value: str = Field(
        description="欄位值。去除首尾空白後為空字串時，視為清空（僅限不帶 on_behalf_of 者）"
    )
    on_behalf_of: Optional[str] = Field(
        default=None,
        description="代寫標示：大腦代某個 agent 寫入時為該 agent 組（例如 cost）；"
        "使用者自填時省略或為 null。只是標示，不授予任何權限",
    )


__all__ = [
    "FieldGroupView",
    "FieldSetView",
    "FieldView",
    "FilledState",
    "RequirementFieldWriteIn",
]
