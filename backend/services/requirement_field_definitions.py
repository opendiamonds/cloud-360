"""
requirement_field_definitions.py — `U20` 的需求欄位定義（程式內常數）

**契約（前端與同進程呼叫端依賴，請勿任意變更）**

欄位定義（agent 組 → 欄位）是**程式內的常數，不是資料**（契約 `K-17` 的
`field_definition_source`）。本模組是它的**唯一**物化：

- `RequirementFieldFacade` 以它做白名單（`BR42.1`–`BR42.3`）、以它為主迴圈合成回應
  （`BR44.5`）、以它計算未填數（`BR44.2`）；
- 組標題與欄位標籤隨 `GET` 回應送出，**`U23` 不得在前端另抄一份**（`OPEN-RF20-4`，
  `team.md` 的「單一真實來源」）。

第一版為兩組七欄，取自已核可線框 §17（`[FD2]`=A）。`group_key`／`field_key` 由
functional-design 命名（上游只有中文標籤，`functional-spec.md` 第十節的 assumption）。

## 移除定義的後果（`[UG:G9]`=A，先讀再刪）

某組的定義被移除後：其值列**保留**在資料庫、畫面**不渲染**該組、未填數只算
**當前已宣告**的欄位（計數下降，而不是留下幽靈欄位）。新增一組（新 agent 上線）
會讓每個系統的未填數增加該組的欄位數。兩者都是程式碼變更，會反映在
`tests/test_requirement_field_facade.py` 的定義相關斷言上。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

#: `group_key`／`field_key` 的合法形狀：小寫英數與底線，1–64 字（`entities.md`；
#: 64 對應 `system_requirement_fields.agent_group`／`field_key` 的 `VARCHAR(64)`）。
KEY_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")

#: 值去除首尾空白後的長度上限（`BR42.4`）。欄位是人填的短文字（線框 §17）。
MAX_VALUE_LENGTH = 2000

#: 填寫提示（nfr-design `security-design.md` 第一節）。欄位是自由文字，系統**無法保證**
#: 使用者或代寫的 agent 不會填入機敏內容；這句提示由 `U23` 顯示（`OPEN-RF20-9`）。
INPUT_HINT = "請勿填入密碼、金鑰或個人資料"


@dataclass(frozen=True)
class AgentFieldDefinition:
    """組內的一個欄位。"""

    field_key: str
    label: str


@dataclass(frozen=True)
class AgentFieldGroup:
    """一個 agent 需要的一組固定欄位。`fields` 的順序即畫面順序。"""

    group_key: str
    title: str
    display_order: int
    fields: Tuple[AgentFieldDefinition, ...]

    def find(self, field_key: str) -> Optional[AgentFieldDefinition]:
        for field in self.fields:
            if field.field_key == field_key:
                return field
        return None


_DECLARED: Tuple[AgentFieldGroup, ...] = (
    AgentFieldGroup(
        group_key="cost",
        title="成本 agent",
        display_order=1,
        fields=(
            AgentFieldDefinition("sla", "SLA"),
            AgentFieldDefinition("peak_tps", "尖峰 TPS"),
            AgentFieldDefinition("user_base", "使用客群"),
            AgentFieldDefinition("monthly_budget_cap", "月預算上限"),
            AgentFieldDefinition("billing_region", "計費區域"),
        ),
    ),
    AgentFieldGroup(
        group_key="architecture",
        title="架構 agent",
        display_order=2,
        fields=(
            AgentFieldDefinition("availability_target", "可用性目標"),
            AgentFieldDefinition("data_retention", "資料保存年限"),
        ),
    ),
)


def _validated(groups: Tuple[AgentFieldGroup, ...]) -> Tuple[AgentFieldGroup, ...]:
    """匯入時檢查定義本身。定義寫錯是程式錯誤，應在啟動時大聲失敗。"""
    seen_groups: set[str] = set()
    seen_orders: set[int] = set()
    for group in groups:
        if not KEY_PATTERN.match(group.group_key):
            raise ValueError(f"group_key 不合格式：{group.group_key!r}")
        if group.group_key in seen_groups:
            raise ValueError(f"group_key 重複：{group.group_key}")
        if group.display_order in seen_orders:
            raise ValueError(f"display_order 重複：{group.display_order}")
        if not group.fields:
            raise ValueError(f"{group.group_key} 至少要有一個欄位")
        keys = [field.field_key for field in group.fields]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{group.group_key} 的 field_key 重複")
        for key in keys:
            if not KEY_PATTERN.match(key):
                raise ValueError(f"field_key 不合格式：{group.group_key}/{key!r}")
        seen_groups.add(group.group_key)
        seen_orders.add(group.display_order)
    return tuple(sorted(groups, key=lambda group: group.display_order))


#: 依 `display_order` 排序的全部組（`BR44.6`：決定性排序，不依賴字典序）。
FIELD_GROUPS: Tuple[AgentFieldGroup, ...] = _validated(_DECLARED)

GROUPS_BY_KEY: Dict[str, AgentFieldGroup] = {
    group.group_key: group for group in FIELD_GROUPS
}


def find_group(group_key: object) -> Optional[AgentFieldGroup]:
    """依 `group_key` 找組；不是字串或未宣告回 `None`。"""
    if not isinstance(group_key, str):
        return None
    return GROUPS_BY_KEY.get(group_key)


def total_field_count() -> int:
    """當前已宣告的欄位總數（第一版為 7）。"""
    return sum(len(group.fields) for group in FIELD_GROUPS)


__all__ = [
    "AgentFieldDefinition",
    "AgentFieldGroup",
    "FIELD_GROUPS",
    "GROUPS_BY_KEY",
    "INPUT_HINT",
    "KEY_PATTERN",
    "MAX_VALUE_LENGTH",
    "find_group",
    "total_field_count",
]
