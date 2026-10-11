"""
memory_types.py — `U8 memory-service` 的值物件與封閉集合

**契約（前端與同進程呼叫端依賴，請勿變更）**

本檔是契約 `K-08` 方法簽章引用的值物件的單一落點，以及
`functional-design/entities.md` 的 `EC3` 三處封閉集合的**應用層**承載點。

三處封閉集合在結構層的狀態**不一樣，而這個差別是載體的依據**：

| 集合 | `schema_rbac.sql` 的狀態 | 本檔的角色 |
|---|---|---|
| `kind` | **有** `ck_memory_records_kind` | 鏡像（寫入端先驗，錯誤訊息比 `IntegrityError` 可讀） |
| `action` | **有** `ck_memory_audit_events_action` | 鏡像（本單元只產生其中兩個值） |
| `visibilityScope`／`previousScope`／`newScope` | **沒有任何約束** | **唯一的防線**（`FD8-3`） |

第三列是 `entities.md §三` 逐字記載的「本單元的寫入端義務，漏做的後果是髒資料
而非寫入失敗」。前兩列有資料庫兜底，第三列沒有——這就是為什麼
`VISIBILITY_SCOPES` 的成員檢查必須出現在每一條寫入與放寬路徑上。

**欄位命名為 snake_case**，沿用本 repo 既有的回應慣例（`UserSchema` 的
`is_active`、`MemberView` 的 `user_id`／`joined_at`）。`entities.md` 的 camelCase
是技術中立的邏輯名，不是線上格式。

**`MemoryView` 刻意不含 `embedding`**：它是 1024 個浮點數，對任何消費端都無用，
而回傳它等於把向量搬到 `U11`／`U15` 的進程裡。`EC6` 的同一條理由。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# 封閉集合（`EC3`）
# ---------------------------------------------------------------------------

MEMORY_KINDS: tuple[str, ...] = ("semantic", "procedure", "episodic")
"""`FR4.1` 的三種記憶。與 `ck_memory_records_kind` 的值集合逐字相同。

**不是型別分支**（`entities.md` 逐字）：三者共用同一個實體、同一組授權欄位、
同一條檢索路徑。差別只有保存期（只有 `episodic` 有 `expires_at`）與寫入端。
"""

VISIBILITY_SCOPE_OWNER = "owner"
VISIBILITY_SCOPE_PLATFORM = "platform"

VISIBILITY_SCOPES: tuple[str, ...] = (
    VISIBILITY_SCOPE_OWNER,
    VISIBILITY_SCOPE_PLATFORM,
)
"""`[FD3]`=A 的兩值封閉集合。**結構層沒有對應的 CHECK**（`FD8-3`）。

**兩個值使「哪個更寬」可判定**（`BR5.2`）：`owner` < `platform`，故放寬只有一個
合法方向。第三個值會讓 `widen_scope` 的方向性失去依據——這是集合必須封閉的
實際理由，不是潔癖。
"""

SCOPE_WIDTH: dict[str, int] = {
    VISIBILITY_SCOPE_OWNER: 0,
    VISIBILITY_SCOPE_PLATFORM: 1,
}
"""可見範圍的寬度序（`BR5.2`）。由 `VISIBILITY_SCOPES` 的順序定義，兩者由
`test_memory_contract` 鎖住一致——漏掉一個值會讓 `widen_scope` 在它上面
`KeyError`，而那是大聲失敗，比靜默放行好。
"""

AUDIT_ACTION_DELETED_BY_USER = "deleted_by_user"
AUDIT_ACTION_SCOPE_CHANGED = "scope_changed"
AUDIT_ACTION_PURGED_BY_RETENTION = "purged_by_retention"

AUDIT_ACTIONS: tuple[str, ...] = (
    AUDIT_ACTION_DELETED_BY_USER,
    AUDIT_ACTION_PURGED_BY_RETENTION,
    AUDIT_ACTION_SCOPE_CHANGED,
)
"""`ck_memory_audit_events_action` 的封閉集合（三個值，順序照 DDL）。

**本單元只產生第一與第三個**（`BR7.4`／`entities.md §二之二`）：
`purged_by_retention` 由 `U9` 產生。而這個集合**沒有任何可用於「建立」的值**
——那正是本站裁決 `contract-summary.md:643` 與 `:1386` 矛盾的依據：
`write` 不留稽核（`BR7.4`），因為資料庫層根本沒有能表達它的值。
"""

AUDIT_ACTIONS_WRITTEN_BY_THIS_UNIT: tuple[str, ...] = (
    AUDIT_ACTION_DELETED_BY_USER,
    AUDIT_ACTION_SCOPE_CHANGED,
)
"""本單元實際寫入的兩個 action（`BR4.2`／`BR5.3`）。"""

EPISODIC_RETENTION_DAYS = 90
"""`EC1`／`FR4.5`：只有 `episodic` 受 90 天保存期約束，而它的 `expires_at`
**必填**——清除作業依該欄選列，NULL 的 episodic 列永遠不會被選中，
漏填的後果是永久保留且沒有任何跡象。
"""

SCOPE_WIDENING_ROLES: tuple[str, ...] = ("Platform_Admin", "Platform_Owner")
"""`BR5.1`／`BR6.1` 共用的角色集合——**刻意只有一份**。

`[FD2]`=A 把稽核讀取的角色集合與 `widen_scope` 對齊，故第二份宣告沒有存在理由。
兩個名稱都在 `services/rbac.py` 的 `CANONICAL_ROLES` 內（已查證），
由 `test_memory_contract` 鎖住——打錯字的後果是該角色永遠被拒，而**沒有錯誤**。

**這是角色模型，不是擁有者模型。** 具這兩個角色**不**因此能讀或刪他人的記憶
（`BR4.1` 的 note）：它們被授予的只有放寬可見範圍與查稽核兩件事。
"""


# ---------------------------------------------------------------------------
# 純函式層的輸入（`NFR3.24`）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredCandidate:
    """`rank_candidates`（`NFR3.24` 的純函式）的輸入元素。

    **刻意只含排序所需的兩個欄位**——多帶欄位會讓它看起來需要資料庫，而
    `memory_ranking` 的整個價值在於它不需要，使 property-based 測試有作用對象
    （`logical-components.md §1.1` 逐字：「`memory_ranking` 不讀 DB、不拋
    `HTTPException`」否則「property-based 測試就寫不下去」）。

    `frozen=True` 讓它可雜湊、可安全地放進 `hypothesis` 的生成策略，並讓
    「排列不變性」這個被測性質不會被輸入的就地修改干擾。形狀沿用
    `membership_types.MemberSnapshot` 的同一個理由。

    `identifier` 為 `str` 而非 `int`：`K-08` 的方法簽章逐字 `memory_id: str`，
    且 `entities.md` 把 `memoryId` 定為「對外為不透明識別字」。
    """

    identifier: str
    score: float


# ---------------------------------------------------------------------------
# 對外檢視（`K-08` 的回傳型別）
# ---------------------------------------------------------------------------


class MemoryView(BaseModel):
    """`K-08` 的 `MemoryView`：`write`／`search`／`widen_scope` 的回傳元素。

    **不含 `embedding`**：1024 個浮點數對 `U11`／`U15` 都無用，而回傳它等於
    把向量搬進消費端的進程。**不含任何他人的資料**——能拿到這個物件就表示
    `BR2.2` 已經放行過。
    """

    model_config = ConfigDict(from_attributes=True)

    memory_id: str
    kind: str
    owner_user_id: int
    visibility_scope: str
    content: str
    embedding_model: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class MemoryAuditEventView(BaseModel):
    """`K-08` 的 `MemoryAuditEventView`：`list_audit_events` 的回傳元素。

    **刻意不含記憶內容**（`EC6`）：稽核比它描述的記憶活得久（`BR2.1`／`DG-1`），
    若它含內容，「保留稽核」就等於「保留被刪除的使用者資料」——使用者以為刪了
    而它還在，`FR4.5` 的 90 天刪除形同虛設。

    `memory_exists` 是 `BR6.3` 要的那一位：`memory_id` 指不到記憶時**仍須回傳
    該事件**，並讓呼叫端**可分辨**這個狀態。少了這個欄位，呼叫端只能自己再查
    一次記憶（而它沒有權限）或把懸空事件誤讀成資料錯誤。
    """

    model_config = ConfigDict(from_attributes=True)

    audit_event_id: str
    memory_id: str
    actor_user_id: int
    action: str
    previous_scope: Optional[str] = None
    new_scope: Optional[str] = None
    occurred_at: datetime
    memory_exists: bool


__all__ = [
    "AUDIT_ACTIONS",
    "AUDIT_ACTIONS_WRITTEN_BY_THIS_UNIT",
    "AUDIT_ACTION_DELETED_BY_USER",
    "AUDIT_ACTION_PURGED_BY_RETENTION",
    "AUDIT_ACTION_SCOPE_CHANGED",
    "EPISODIC_RETENTION_DAYS",
    "MEMORY_KINDS",
    "MemoryAuditEventView",
    "MemoryView",
    "SCOPE_WIDENING_ROLES",
    "SCOPE_WIDTH",
    "ScoredCandidate",
    "VISIBILITY_SCOPES",
    "VISIBILITY_SCOPE_OWNER",
    "VISIBILITY_SCOPE_PLATFORM",
]
