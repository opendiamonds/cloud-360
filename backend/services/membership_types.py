"""
membership_types.py — `U19 membership-service` 的四個值物件

**契約（前端與同進程呼叫端依賴，請勿變更）**

本檔是契約 `K-16` 方法簽章引用的四個值物件的單一落點
（`entities.md` 的 `value_objects` 區塊）：

- `ProjectRole`：per-project 角色的**封閉列舉**。
- `MemberSnapshot`：純函式 `select_successor` 的輸入元素。
- `MemberView`：facade 對外回傳的成員檢視。
- `LastAdminGuardReport`：守門命中時的回報酬載，**同時是 409 的 response model**。

兩種形狀刻意並存，不是不一致：

- `MemberSnapshot` 是**純 dataclass**（`dataclasses`），因為它是 `BR4.1` 的純函式
  輸入，而 `hypothesis` 的 `@given` 要直接建構它；讓它背著 pydantic 的驗證層
  只會讓 property-based 測試多一層與被測性質無關的失敗面。
- `MemberView`／`GuardedProjectRef`／`LastAdminGuardReport` 是 **pydantic model**，
  因為它們同時是 HTTP 回應模型——`BR6.2` 要求 `LastAdminGuardReport` 必須能被
  `responses={409: {"model": ...}}` 顯式宣告，而那需要一個 pydantic model。

**欄位命名為 snake_case**，沿用本 repo 既有的回應慣例（`UserSchema` 的
`is_active`／`last_activity_at`、`ProjectOut` 的 `owner_user_id`）。
`entities.md` 的 camelCase 是技術中立的邏輯名，不是線上格式。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict


class ProjectRole(str, Enum):
    """per-project 角色的封閉列舉（`entities.md` 的 `ProjectRole`）。

    **刻意不含 `project_owner`**：`owner` 是 `projects.owner_user_id` 承載的
    **專案屬性**，不是成員角色。建立者同時是 owner 且是 `project_admin`
    （`FR12.1`），兩者是不同的事實——混為一談會讓「改某人的角色」意外改到
    專案的擁有權。

    **與全域角色同名不同義**：本列舉的 `project_admin` 是**專案內**的身分，
    與 `services/rbac.py` 的 `CANONICAL_ROLES` 裡的全域 `Project_Admin` 是兩回事
    （`schema_rbac.sql` 的 `project_members.role` COMMENT 逐字記載這一點）。
    `FR12.6` 要求兩層串聯、任一層不過即拒，兩者不互相取代。

    封閉性由**應用層**承載（`BR5.4`）：`reselection_events` 的
    `previous_role`／`new_role` 在 DDL 刻意沒有 CHECK。
    """

    PROJECT_ADMIN = "project_admin"
    MEMBER = "member"


PROJECT_ROLE_VALUES: tuple[str, ...] = tuple(role.value for role in ProjectRole)
"""封閉列舉的字串值集合。`project_members.role` 的 DDL CHECK 以同一組值宣告。"""


@dataclass(frozen=True)
class MemberSnapshot:
    """`select_successor`（`BR4.1` 的純函式）的輸入元素。

    **刻意只含挑選所需的三個欄位**——多帶欄位會讓它看起來需要 DB，而
    `BR4.1` 的整個價值在於這個函式不需要資料庫，使 ADR-0006 的 PBT
    hard constraint 有作用對象。

    `frozen=True` 讓它可雜湊、可安全地放進 `hypothesis` 的生成策略，
    並讓「排列不變性」這個被測性質不會被輸入的就地修改干擾。
    """

    user_id: int
    joined_at: datetime
    role: str


class MemberView(BaseModel):
    """facade 對外回傳的成員檢視（`list_members`／`invite_member`／`change_role`）。

    **不含 per-project 判定以外的授權結論，也不含全域角色**——前端不得自行
    推導 per-project 權限（不變量 `I-5`），它只讀本元件給的結論。

    **不含 `invited_by`**：`entities.md` 逐字把它列為「本輪有寫入端而無讀取端」
    的懸空契約端（`OPEN-FD19-6`），並明文要求**不自行把它加進 `MemberView`**
    ——那會擴大一個已核可的回傳形狀而沒有任何 AC 要求它。
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    display_name: str
    role: str
    joined_at: datetime


class GuardedProjectRef(BaseModel):
    """`LastAdminGuardReport` 的一項。

    **必須同時含 id 與名稱**：`entities.md` 逐字「只給 id 的話畫面無法告知
    使用者是哪個專案」。
    """

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    name: str


class LastAdminGuardReport(BaseModel):
    """守門命中時的回報酬載，**同時是既有停用端點 409 的 response model**。

    `AC12.3.3` 的 Then 要求停用被拒時**列出那些專案**，故這個形狀就是 409 的
    回應本體（不是 `{"detail": ...}` 的包裝）。

    `BR6.2`：它**必須**被 `responses={409: {"model": LastAdminGuardReport}}`
    顯式宣告。FastAPI 不從 `raise HTTPException` 推導狀態碼，故不宣告則該契約
    不進 `openapi.json`、前端產不出型別，而 `dump_openapi.py --check` 與
    `npm run check:types` **兩道漂移閘門都保持綠燈**——這是本單元唯一
    「違反後沒有任何東西變紅」的規則。
    """

    model_config = ConfigDict(from_attributes=True)

    projects: List[GuardedProjectRef]


class ReselectionFailureReport(BaseModel):
    """停用端點在**自動改選部分失敗**時的回應本體（合併前必修第 10 項）。

    出現在 `PUT /api/auth/{user_id}/active` 的 **500**（任一專案改選失敗）與
    **503**（失敗全部是取鎖逾時，合併前必修第 16 項）。兩者的共同事實是：
    **帳號已經停用了**（停用與改選是兩段交易，改選在停用成功之後才跑），而
    `failed_project_ids` 列出的專案此刻可能沒有可運作的管理者。

    `detail` 告訴呼叫端**重送同一個請求**即可補跑：對已停用的帳號再送
    `is_active=false` 不會重跑守門，但會重跑改選，而改選是冪等的（`BR4.3`），
    已改好的專案不會產生第二筆事件。

    在此之前這條路徑回 200 且只記 log，沒有任何呼叫者負責重跑，失敗的專案會
    永久沒有管理者（`nfr-design` review-02 `R-04`）。
    """

    detail: str
    user_id: int
    failed_project_ids: List[int]


__all__ = [
    "ProjectRole",
    "PROJECT_ROLE_VALUES",
    "MemberSnapshot",
    "MemberView",
    "GuardedProjectRef",
    "LastAdminGuardReport",
    "ReselectionFailureReport",
]
