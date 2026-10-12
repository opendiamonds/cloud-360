"""
hierarchy_facade.py — `U7 hierarchy-service` 的授權門面

**契約（前端與同進程呼叫端依賴，請勿變更）**

本模組是 `projects`／`systems`／`diagram_change_records` 受保護操作的**唯一授權
入口**（契約 `K-07` 的 `sole_entry`）。FastAPI router 與同進程呼叫端**共用這一個
入口**，故 `K2` 的判定只有一份呼叫點。

安全邊界：

- `BR1.1`：`K2` 判定在本模組內，**不在 router**。拒絕時 raise
  `HierarchyForbidden`，**不是** `HTTPException`——router 層才轉成 403，
  同進程呼叫端自行處置。
- `BR1.2`：每個方法的**第一個位置參數**是 `principal`；資源識別一律為**具名**
  參數，不得藏在 payload 內。
- `BR1.3`（誠實宣告，非禁令）：底層 service 層**沒有第二道角色檢查**。
  判定只有一份，就在這裡。
- `BR1.4`：`Principal` 只能由本模組鑄造，使「拿不到 principal 就呼叫不了 facade」
  成為型別層事實。**誠實的限制**：這擋得住誤用，擋不住刻意的 `_MINT` 存取
  ——Python 沒有真正的封裝，本模組不把這個宣稱寫得比實際強。
- `BR1.5`：沒有任何單元繞過本 facade 直呼底層 service。**本單元無法自己驗證
  這一點**——它約束的是四個同進程呼叫端 `U10`／`U12`／`U19`／`U20`
  （`components.md:110-112`／`:156-158`／`:559-561`／`:618-620`），
  執行落點在那四個單元的 code-generation（`OPEN-H2`）。繞過一旦發生是**靜默的**。

列可見範圍分兩類，**不可混用**：

- **列舉型讀取**（`list_projects`／`list_systems`／`resolve_work_target`）套用
  `BR6.1` 的擁有者範圍；以識別碼直接解析他人資源時回「查不到」而非「無權限」。
- **判定支援型查詢**（`project_exists`／`get_project_owner`／
  `get_project_of_system`）**刻意不套列範圍**（`BR6.4`）——否則契約
  `K-16`／`K-17` 不可實作。改以三道約束取代，見各方法 docstring。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import User
from services.rbac import user_can, user_is_approved

logger = logging.getLogger("cloud360.hierarchy_facade")

# `services.hierarchy_service` 的匯入刻意放在**本檔末尾**，不在這裡——
# 兩個模組互相依賴：service 層需要本檔定義的四個例外型別，而本檔需要 service
# 層的函式。把 import 放在頂端會在 service 先被匯入時取到一個尚未定義例外的
# 半初始化模組（ImportError）。放在末尾則兩個方向都成立，因為本檔只在
# **呼叫時**才解析 `hierarchy_service.<fn>`，不在匯入時。


# ---------------------------------------------------------------------------
# 例外型別（`BR1.1`／`BR6.6`）
#
# 四者都**不是** `HTTPException` 的子類別，也不 raise 它。契約 `K-07` 的
# `on_denied` 逐字：「raise HierarchyForbidden(story_id='K2', action=…)
# —— **不是** HTTPException」。router 層負責轉譯；同進程呼叫端自行處置。
# ---------------------------------------------------------------------------


class HierarchyError(Exception):
    """本單元所有 facade 層例外的基底。刻意不繼承 HTTPException。"""


class HierarchyForbidden(HierarchyError):
    """授權未通過（`BR1.1`）。router 轉 403。"""

    def __init__(self, story_id: str, action: str) -> None:
        super().__init__(f"權限不足：需要 {story_id}.{action}")
        self.story_id = story_id
        self.action = action


class HierarchyNotFound(HierarchyError):
    """查不到。

    **也用於「存在但不屬於請求者」**（`BR6.1`／`BR6.5`）——刻意與真正的
    不存在**回同一種結果**，否則回應本身就是一個存在性預言機。
    """


class HierarchyValidationError(HierarchyError):
    """輸入不合法（`BR3.1`／`BR5.4`）。router 轉 422。"""


class HierarchyConflictError(HierarchyError):
    """衝突（`BR3.2`／`BR4.2`／`BR4.3`／`BR4.4`）。router 轉 **409**。

    `BR6.6`：這是對契約 `K-07` 的擴充——K-07 的 `raises` 沒有衝突型例外、
    其 OpenAPI 區塊沒有 409。router 必須**顯式**宣告
    `responses={409: {...}}`，否則該契約不進 spec、前端產不出型別，
    **而 CI 保持綠燈**（`unit-of-work.md:447` 逐字「非 2xx/422 的宣告數為 0」）。
    """


# ---------------------------------------------------------------------------
# Principal（`BR1.4`）
# ---------------------------------------------------------------------------

_MINT = object()
"""模組私有的鑄造令牌。不匯出、不出現在 `__all__`。"""


@dataclass(frozen=True)
class Principal:
    """已完成身分驗證的呼叫者。**只能由本模組鑄造**（`BR1.4`）。

    直接呼叫 `Principal(...)` 會 raise `TypeError`——必須持有 `_MINT`，
    而外部模組取不到它。這使「拿不到 principal 就呼叫不了 facade」成為
    型別層事實，關閉契約 `K-07` 具名 `residual_gap` 的一半。

    **另一半仍然開著**：「完全不碰 facade、直呼底層 service」擋不住
    （`BR1.5`／`OPEN-H2`）。
    """

    user_id: int
    role: Optional[str]
    _mint_token: Any = None
    #: 帳號是否已核准（`authorization_status == "approved"`）。由
    #: `mint_principal` 以 `services.rbac.user_is_approved` 填入——**沿用既有
    #: 判定，不另寫一份**（`team.md` 單一真實來源）。
    #:
    #: 置於 `_mint_token` **之後**且預設 `True`，使既有的位置參數順序不變。
    #: 預設 `True` 不是放寬：`Principal` 只能經 `mint_principal` 鑄造，而它
    #: 一律顯式傳入本欄位；預設值只對「不經鑄造入口」的路徑生效，而那條路徑
    #: 在 `__post_init__` 就被擋掉了。
    #:
    #: 目前的讀者只有 `MemoryFacade._authorize_approved`（`U15` 的
    #: code-generation 補上的待核准帳號缺口）。`HierarchyFacade` **尚未**讀它
    #: ——同類缺口已記為交接事項，不在本次範圍內。
    is_approved: bool = True

    def __post_init__(self) -> None:
        if self._mint_token is not _MINT:
            raise TypeError(
                "Principal 只能由 hierarchy_facade 鑄造（BR1.4）："
                "請呼叫 mint_principal()，不要直接建構。"
            )


def mint_principal(user: User) -> Principal:
    """由已驗證的 `User` 鑄造 `Principal`。這是唯一的鑄造入口。

    `is_approved` 以 `services.rbac.user_is_approved(user)` 判定：該函式以
    `getattr` 讀 `authorization_status`，缺欄位時視為 `approved`——故只帶
    `.id`／`.role` 的輕量物件（`tests_pg/test_membership_concurrency.py`）
    鑄造出來的行為與本欄位加入前相同。
    """
    return Principal(
        user_id=user.id,
        role=user.role,
        _mint_token=_MINT,
        is_approved=user_is_approved(user),
    )


class HierarchyFacade:
    """受保護操作的唯一授權入口（契約 `K-07` 的 `sole_entry`）。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    # -- 授權判定（唯一一份）------------------------------------------------

    def _authorize(self, principal: Principal, action: str) -> None:
        """`BR1.1`：`K2` 判定。不通過 raise `HierarchyForbidden`。

        **判定先於任何讀寫**，失敗即中止（契約 `K-07` 的 `hard_rule`）。
        刻意不走 `require_story_action` 這個 FastAPI dependency——它 raise
        `HTTPException`，而本層的拒絕必須是 `HierarchyForbidden`。
        """
        if not user_can(self._db, principal.role, "K2", action):
            raise HierarchyForbidden(story_id="K2", action=action)

    # -- 寫入路徑 -----------------------------------------------------------

    def create_project(self, principal: Principal, *, name: str):
        """`W1`。**非冪等，呼叫端不得自動重試**（`BR2.4`）。

        **本方法刻意不做 `BR6.5` 的擁有者檢查**：擁有者依定義就是請求者本人，
        沒有「別人的列」可碰。這是四條寫入路徑中唯一的例外，在此寫明以免
        被讀成漏寫。
        """
        self._authorize(principal, "edit")
        return hierarchy_service.create_project(
            self._db, owner_user_id=principal.user_id, name=name
        )

    def create_project_nocommit(self, principal: Principal, *, name: str):
        """`W1` 的**不 commit** 變體，供 `U19` 的組合寫入使用。

        與 `create_project()` 的唯一差別是**交易邊界歸呼叫端**：本方法 `flush`
        而不 `commit`，故「建立專案」與「寫入建立者的成員列」可以在同一個交易
        內（`U19` 的 `NFR12.18`／`[ND1]`=A／`OPEN-ND19-5`）。沒有它，組合實作
        會是兩個交易，中間失敗就留下一個**零成員專案**——正是 `[ND1]` 要消除的
        狀態。

        **`K2` 的授權判定與 `create_project()` 完全相同**，就在這裡、就這一份
        （`BR1.1`）。新增這個變體**沒有**開出一條繞過授權的路徑：它與另一支
        共用同一個 `_authorize`。

        呼叫端的義務：自行 `commit()`／`rollback()`。
        """
        self._authorize(principal, "edit")
        return hierarchy_service.create_project_nocommit(
            self._db, owner_user_id=principal.user_id, name=name
        )

    def create_system(self, principal: Principal, *, project_id: int, name: str):
        """`W2`。**非冪等**（`BR2.4`）。"""
        self._authorize(principal, "edit")
        # BR6.5：擁有者檢查**先於** BR2.2 的存在檢查，且兩者回同一種結果。
        hierarchy_service.assert_project_owned_by(
            self._db, project_id=project_id, user_id=principal.user_id
        )
        return hierarchy_service.create_system(
            self._db, project_id=project_id, name=name
        )

    def delete_project(self, principal: Principal, *, project_id: int) -> None:
        """`W6`（專案）。**任何情況都不級聯。**"""
        self._authorize(principal, "edit")
        # BR6.5 必須在 BR4.2／BR4.4 之前——那兩條完全不涉及擁有者
        # （它們管預設標記與底下還有沒有東西），擋不住「刪除他人的專案」。
        hierarchy_service.assert_project_owned_by(
            self._db, project_id=project_id, user_id=principal.user_id
        )
        hierarchy_service.delete_project(self._db, project_id=project_id)

    def delete_system(self, principal: Principal, *, system_id: int) -> None:
        """`W6`（系統）。**任何情況都不級聯。**"""
        self._authorize(principal, "edit")
        hierarchy_service.assert_system_owned_by(
            self._db, system_id=system_id, user_id=principal.user_id
        )
        hierarchy_service.delete_system(self._db, system_id=system_id)

    def record_diagram_change(
        self,
        principal: Principal,
        *,
        diagram_id: int,
        requirement_summary: str,
        requirement_label: str,
        actor_user_id: int,
    ):
        """`W4`。`U12 work-orchestrator` 是**唯一寫入端**（契約 `K-07`）。

        **非冪等（一次異動一列），不得重試**（`BR2.4`）。

        `BR5.6`：`actor_user_id` 是**必填的具名參數**，刻意**不**預設為
        `principal.user_id`——`U4` 的欄位註解（`schema_rbac.sql:420`）逐字要求
        寫入端存入「實際造成異動的人」且「**must NOT default to the session
        owner**」，而在大腦編排流程裡 `principal` 極可能就是 session 擁有者。
        把它做成必填參數，是讓那個預設**在型別層不可能發生**。
        """
        self._authorize(principal, "edit")
        hierarchy_service.assert_diagram_owned_by(
            self._db, diagram_id=diagram_id, user_id=principal.user_id
        )
        return hierarchy_service.record_diagram_change(
            self._db,
            diagram_id=diagram_id,
            requirement_summary=requirement_summary,
            requirement_label=requirement_label,
            actor_user_id=actor_user_id,
        )

    # -- 列舉型讀取（套用 `BR6.1` 的擁有者範圍）-----------------------------

    def list_projects(self, principal: Principal):
        """`W7`。只回傳 `owner_user_id` 等於請求者的列（`BR6.1`）。"""
        self._authorize(principal, "view")
        return hierarchy_service.list_projects(
            self._db, owner_user_id=principal.user_id
        )

    def list_systems(self, principal: Principal, *, project_id: int):
        """`W7`。先確認專案屬請求者，否則回「查不到」（`BR6.1`）。"""
        self._authorize(principal, "view")
        hierarchy_service.assert_project_owned_by(
            self._db, project_id=project_id, user_id=principal.user_id
        )
        return hierarchy_service.list_systems(self._db, project_id=project_id)

    def resolve_work_target(
        self,
        principal: Principal,
        *,
        project_id: Optional[int] = None,
        system_id: Optional[int] = None,
        diagram_id: Optional[int] = None,
    ) -> dict:
        """`W3`。`SessionContext`（`U10`）的消費路徑。

        **唯讀且冪等，可安全重試**（`BR2.4`）。
        資源識別為具名參數，不得藏在 payload 內（`BR1.2`）。

        `BR6.1`：解析的目標若不屬請求者，回「查不到」。少了這一步，
        `SessionContext` 可以把任何人的識別碼解析成合法的作業對象——
        而這是**同進程**路徑，**沒有任何 router 層會替它補上範圍檢查**。
        """
        self._authorize(principal, "view")
        return hierarchy_service.resolve_work_target(
            self._db,
            owner_user_id=principal.user_id,
            project_id=project_id,
            system_id=system_id,
            diagram_id=diagram_id,
        )

    def list_diagrams_of_system(
        self, principal: Principal, *, system_id: int
    ) -> list:
        """系統下呼叫者擁有的圖：`[(diagram_id, title), ...]`。**唯讀、冪等。**

        `U12 work-orchestrator` 的跨單元新增（`U12` functional-spec 2.4／
        `BR56.1`／`BR56.3`：作業對象只指定系統時，換成目標圖集合）。

        列舉型讀取，套用 `BR6.1` 的擁有者範圍：先 `_authorize(view)`，再以
        `assert_system_owned_by` 確認系統屬於請求者——不屬於者回「查不到」
        （`HierarchyNotFound`），與真正的不存在同一種結果。
        """
        self._authorize(principal, "view")
        hierarchy_service.assert_system_owned_by(
            self._db, system_id=system_id, user_id=principal.user_id
        )
        return hierarchy_service.list_diagrams_of_system(
            self._db, system_id=system_id, owner_user_id=principal.user_id
        )

    def list_diagram_changes(
        self,
        principal: Principal,
        *,
        label: Optional[str] = None,
        system_id: Optional[int] = None,
    ):
        """`W5`／`W8`。`DG-3` 的落地（`BR5.1`）。

        `BR6.3`：可見性以**架構圖自身的擁有者**（`user_diagrams.user_id`，
        NOT NULL）判定，**不上溯 `system`→`project`**。理由已實測：
        新建的圖從未被指派系統歸屬（`OPEN-H11`），上溯會對每一張新圖斷掉。

        **以系統為條件查詢時，新圖的紀錄一律查不到**——那是 `OPEN-H11` 的
        直接後果，不是本方法的缺陷。以標籤查詢不受影響。

        `NFR7.1`：回應**不得被呈現為完整變更歷史**；涵蓋範圍由 `source` 宣告。
        """
        self._authorize(principal, "view")
        return hierarchy_service.list_diagram_changes(
            self._db,
            owner_user_id=principal.user_id,
            label=label,
            system_id=system_id,
        )

    # -- 判定支援型查詢（**刻意不套列範圍**，`BR6.4`）------------------------
    #
    # 三道約束取代範圍過濾，**缺一即不成立**：
    #   (1) **只能同進程呼叫**——不得經任何 HTTP path 暴露。
    #       `hierarchy_router.py` 不 import 本組方法。
    #   (2) **只回傳判定所需的最小欄位**——`bool`／`int`／`int`。
    #       不回傳 model 物件、不回傳名稱、不回傳任何可列舉的集合，
    #       故只能驗證一個**已經知道識別碼**的資源，不能枚舉未知的。
    #       這是「可驗證」與「可枚舉」之間的唯一分界。
    #   (3) **呼叫端必須自己完成授權判定**——契約 `K-16`／`K-17` 的 `hard_rule`
    #       已如此要求，且兩層 facade **不得互相假設對方已檢查**。
    #
    # 為什麼不套列範圍：`components.md:559-561`／`:618-620` 的 `U19`／`U20`
    # interaction 逐字是「驗證專案存在、讀取 ownerUserId」與「驗證系統存在、
    # 取得其所屬專案」——**存在的目的就是查別人的專案**。
    # `K-16` 的 `assert_can_deactivate(principal, target_user_id)` 要查的是
    # **被停用者**名下的專案；套上範圍會讓 `LastAdminGuard` 永不觸發，
    # 而該契約的 `no_database_backstop` 逐字寫「**這個檢查是唯一防線**」。
    #
    # 代價已登錄為 `OPEN-H10`：本 facade 因此成為一個「可問出特定專案擁有者
    # 是誰」的通道。緩解靠上述三道約束，**不是**靠範圍過濾。

    def project_exists(self, principal: Principal, *, project_id: int) -> bool:
        """判定支援型。回傳 `bool`，**不套列範圍**（`BR6.4`）。"""
        self._authorize(principal, "view")
        return hierarchy_service.project_exists(self._db, project_id=project_id)

    def get_project_owner(self, principal: Principal, *, project_id: int) -> int:
        """判定支援型。回傳擁有者 id（`int`），**不套列範圍**（`BR6.4`）。"""
        self._authorize(principal, "view")
        return hierarchy_service.get_project_owner(self._db, project_id=project_id)

    def get_project_of_system(self, principal: Principal, *, system_id: int) -> int:
        """判定支援型。回傳所屬專案 id（`int`），**不套列範圍**（`BR6.4`）。"""
        self._authorize(principal, "view")
        return hierarchy_service.get_project_of_system(
            self._db, system_id=system_id
        )


# 循環依賴的另一端——理由見檔頭 logger 下方的註解。
import services.hierarchy_service as hierarchy_service  # noqa: E402

__all__ = [
    "HierarchyError",
    "HierarchyForbidden",
    "HierarchyNotFound",
    "HierarchyValidationError",
    "HierarchyConflictError",
    "Principal",
    "mint_principal",
    "HierarchyFacade",
]
