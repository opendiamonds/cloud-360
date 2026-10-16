"""
membership_facade.py — `U19 membership-service` 的授權門面

**契約（前端與同進程呼叫端依賴，請勿變更）**

本模組是 per-project 授權判定的**唯一提供者**，同時是成員關係受保護操作的
**唯一授權入口**（契約 `K-16` 的 `sole_entry` ＋ `ADR-012`）。
消費端：`U20`（同進程）、`U13`（同進程，WebSocket）、`U24`（HTTP）、
`U21`（獨立進程）、以及**既有的停用端點**（`user_router.update_user_active`）。

安全邊界
--------

- `BR1.1`：per-project 判定在本模組內，**不在 router**、不在 service 層。
  禁止的是**跳過本 facade 直接讀寫 `project_members` 表**。
- `BR1.2` **兩層串聯**：全域功能權限那一層由既有 `require_story_action` 承載
  （`membership_router` 的 dependency），per-project 那一層由本 facade 判定。
  **任一層不過即拒。** 本 facade 另以 `user_can(..., "K3", ...)` 自行驗一次
  全域層，理由是**同進程呼叫端沒有 dependency 鏈**（`U13` 是 WebSocket，
  握手之後每則訊息都不經 FastAPI 的 dependency）。HTTP 路徑因此驗兩次同一個
  謂詞——那是刻意的，成本是一次索引命中的讀取，而少了它 `U20`／`U13` 就會是
  只有一層的路徑。`user_can` **不是**重新實作 `require_story_action`：後者是
  前者的 FastAPI dependency 包裝，權限矩陣只有一份。
- `BR1.3`（消歧義宣告，非禁令）：`sync` 同進程呼叫本 facade 是**預期且允許**的。
- `BR1.4`：每個方法的**第一個位置參數**是 `principal`；`project_id` 一律為
  **具名**參數，不得藏在 payload 內。facade **不自行從 request 取身分**。
- `BR1.5`：拒絕時 raise `MembershipForbidden`／`MissingGlobalPermission`，
  **不是** `HTTPException`；判定先於任何寫入，失敗即中止。
- `BR1.6`：`resolve_project_role` 回 `None` 代表**非成員**，呼叫端須當成拒絕。

**殘留缺口，如實記載**：`BR1.1` 的「facade 是唯一入口」**無機械強制**
（承接 `K-07` 的 `OQ-N2`／`OPEN-FD19-3`）——任何人直接 `SELECT`
`project_members` 就繞過了全部授權，而繞過是靜默的。`[ND1]`=A 讓建立路徑
合規，但沒有任何機制擋住下一個人直接寫表。另一半：per-project 判定結論由
伺服器產生、前端不得推導（`I-5`），但**沒有機制擋住前端自己猜**。

`Principal` 為什麼沿用 `hierarchy_facade` 的那一個
--------------------------------------------------

它的欄位（`user_id` ＋ 全域 `role`）正是 `BR1.4` 要的，而 `team.md` 的
「單一真實來源」規則要求新增第二份物化前先確認是否有既有型別可用。
`U19 → U7` 的依賴方向本來就存在（`components.md:558-561`：本單元讀 `projects`
以驗證存在與取 `owner_user_id`），故沿用不新增依賴邊。附帶好處是
`_MINT` 令牌讓「拿不到 principal 就呼叫不了 facade」成為型別層事實。
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from models import ReselectionEvent
from services.hierarchy_facade import (
    PROJECT_NOT_FOUND_DETAIL,
    HierarchyFacade,
    HierarchyForbidden,
    HierarchyNotFound,
    Principal,
    mint_principal,
)
from services.membership_errors import (
    LastAdminGuard,
    MembershipError,
    MembershipForbidden,
    MembershipNotFound,
    MissingGlobalPermission,
)
import services.membership_service as membership_service
from services.membership_selection import select_successor
from services.membership_types import (
    GuardedProjectRef,
    LastAdminGuardReport,
    MemberSnapshot,
    MemberView,
    ProjectRole,
)
from services.rbac import user_can

logger = logging.getLogger("cloud360.membership")

STORY_ID = membership_service.MEMBERSHIP_STORY_ID


class MembershipFacade:
    """受保護操作的唯一授權入口（契約 `K-16`）。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    # -- 授權判定（唯一一份）------------------------------------------------

    def _authorize_global(
        self, principal: Principal, action: str, project_id: Optional[int] = None
    ) -> None:
        """`BR1.2` 的第一層：全域功能權限 `K3.<action>`。

        刻意不走 `require_story_action` 這個 FastAPI dependency——它 raise
        `HTTPException`，而本層的拒絕必須是 `MembershipForbidden`（`BR1.5`），
        且同進程呼叫端根本沒有 dependency 鏈。評估的謂詞與它完全相同
        （`user_can`），權限矩陣只有一份。
        """
        if not user_can(self._db, principal.role, STORY_ID, action):
            membership_service.log_denied(
                action=action,
                project_id=project_id,
                principal_user_id=principal.user_id,
            )
            raise MembershipForbidden(
                story_id=STORY_ID, action=action, project_id=project_id
            )

    def _assert_project_exists(self, principal: Principal, project_id: int) -> None:
        """經 `K-07` 驗證專案存在（`functional-spec.md §2.1` 步驟 2）。

        **經 `HierarchyFacade` 而非直呼 `hierarchy_service`**：`U7` 的 `BR1.5`
        逐字要求四個同進程呼叫端（含本單元）不得繞過它的 facade，而繞過是靜默的。

        `HierarchyForbidden`（呼叫端缺 `K2.view`）在此**轉成 `MembershipNotFound`**，
        理由有兩個：(a) 契約 `K-16` 宣告 `resolve_project_role` 只 raise
        `MembershipNotFound`，而它是 per-project 判定的熱路徑；(b) 沿用 `U7` 自己
        的 `BR6.1` 慣例——「回『查不到』而非『無權限』，不以錯誤碼洩漏該資源
        存在」。一個缺 `K2.view` 的呼叫端沒有理由得知某個專案是否存在。
        實務上這條分支極罕見：全部 11 個 canonical role 的 `K2.view` 都是 True，
        故只有非 canonical role 會走到它。
        """
        try:
            exists = HierarchyFacade(self._db).project_exists(
                principal, project_id=project_id
            )
        except HierarchyForbidden as exc:
            raise MembershipNotFound(f"查不到專案 {project_id}") from exc
        except HierarchyNotFound as exc:
            raise MembershipNotFound(f"查不到專案 {project_id}") from exc
        if not exists:
            raise MembershipNotFound(f"查不到專案 {project_id}")

    def _require_project_role(
        self, principal: Principal, *, project_id: int, action: str, admin: bool
    ) -> str:
        """`BR1.2` 的第二層：per-project 角色。回傳該 principal 的 per-project 角色。

        `admin=True` 要求 `project_admin`；`admin=False` 只要求**是成員**。
        非成員（`resolve_project_role` 回 `None`）一律拒絕（`BR1.6`）——
        這正是 `AC12.5.2` 的 deny 側：具全域權限但非本專案成員的人不得讀到
        專案資料。
        """
        role = membership_service.resolve_project_role(
            self._db, project_id=project_id, user_id=principal.user_id
        )
        if role is None or (admin and role != membership_service.ROLE_PROJECT_ADMIN):
            membership_service.log_denied(
                action=action,
                project_id=project_id,
                principal_user_id=principal.user_id,
            )
            raise MembershipForbidden(
                story_id=STORY_ID, action=action, project_id=project_id
            )
        return role

    @staticmethod
    def _validated_role(role: object) -> str:
        """把輸入收斂成封閉列舉的字串值（`BR5.4` 的應用層承載）。"""
        try:
            return ProjectRole(role).value
        except ValueError as exc:
            raise MembershipForbidden(
                story_id=STORY_ID, action="change_role"
            ) from exc

    # -- 1. per-project 判定（**唯一入口**，`BR1.6`）-------------------------

    def resolve_project_role(
        self, principal: Principal, *, project_id: int
    ) -> Optional[str]:
        """per-project 判定的唯一入口。**回 `None` 代表非成員。**

        契約 `K-16` 宣告它只 raise `MembershipNotFound`——**刻意沒有授權檢查**：
        它本身就是授權的原語，呼叫端拿它的結果去決定放行或拒絕。對它再加一層
        `K3` 檢查會讓每一個消費端為了「問一個問題」而需要一個與該問題無關的
        權限。

        唯讀、冪等，可安全重試（`NFR12.19`）。這是本單元最熱的路徑。
        """
        self._assert_project_exists(principal, project_id)
        return membership_service.resolve_project_role(
            self._db, project_id=project_id, user_id=principal.user_id
        )

    def resolve_project_role_of(
        self, principal: Principal, *, project_id: int, user_id: int
    ) -> Optional[str]:
        """同上，但問的是**別人**的角色。供既有停用端點與自動改選使用。

        需要 `K3.view`（問別人的角色不是授權原語，是一次讀取）。
        """
        self._authorize_global(principal, "view", project_id)
        self._assert_project_exists(principal, project_id)
        return membership_service.resolve_project_role(
            self._db, project_id=project_id, user_id=user_id
        )

    # -- 2. 成員清單 --------------------------------------------------------

    def list_members(
        self, principal: Principal, *, project_id: int
    ) -> List[MemberView]:
        """`U24` 成員頁的唯一資料來源。非成員即拒（`BR1.2`／`BR1.6`）。

        `AC12.2.3`（清單上沒有改角色的控件）的**伺服器側對應**：本方法
        **只回傳**成員檢視，不提供任何變更入口；角色變更的唯一入口是
        `change_role`。畫面側屬 `U24`。
        """
        self._authorize_global(principal, "view", project_id)
        self._assert_project_exists(principal, project_id)
        self._require_project_role(
            principal, project_id=project_id, action="list_members", admin=False
        )
        return membership_service.list_members(self._db, project_id=project_id)

    # -- 3. 邀請（**非冪等**，`BR3.3`）--------------------------------------

    def invite_member(
        self,
        principal: Principal,
        *,
        project_id: int,
        user_id: int,
        role: str,
    ) -> MemberView:
        """邀請一位成員。**成功是一級行為**（`BR3.6`）：成功 ⇒ 清單必然多一列。

        步驟與交易邊界（`NFR12.15`）：授權（兩層）→ 取鎖 → 受邀者的全域權限
        前置檢查 → 寫入 → **一次 commit**。全部在單一交易內，故被拒時
        `project_members` 的列數不變（`AC12.5.3`）——半套狀態尤其危險：
        清單多一列而那個人實際上用不了專案。

        **非冪等**（`BR3.3`）：重複邀請同一 `(project, user)` 被拒，
        不建立第二列；呼叫端不得自動重試。
        """
        self._authorize_global(principal, "edit", project_id)
        self._assert_project_exists(principal, project_id)
        self._require_project_role(
            principal, project_id=project_id, action="invite_member", admin=True
        )
        target_role = self._validated_role(role)
        try:
            membership_service.lock_project(self._db, project_id=project_id)
            membership_service.assert_invitee_has_global_permission(
                self._db, user_id=user_id
            )
            view = membership_service.add_member(
                self._db,
                project_id=project_id,
                user_id=user_id,
                role=target_role,
                invited_by=principal.user_id,
            )
            self._db.commit()
            return view
        except Exception:
            # `AC12.5.3`：被拒時不得留下半套狀態。rollback 覆蓋全部失敗路徑
            # （`MissingGlobalPermission`、唯一約束、取鎖失敗）。
            self._db.rollback()
            raise

    # -- 4. 移出（**冪等**，`BR3.4`／`[FD2]`=A）------------------------------

    def remove_member(
        self, principal: Principal, *, project_id: int, user_id: int
    ) -> None:
        """移出一位成員。**對已非成員回成功**（冪等）。

        守門（`BR2.1`）在鎖之內：移除後該專案的 `project_admin` 數不得歸零
        ——**含自我移出**，這是三條路徑之一。

        **成功 ⇒ 清單必然少一列，且該成員其後讀取本專案資料被拒**（`BR3.6`）
        ——後半句由 `resolve_project_role` 的 `None` 路徑自動成立，
        不需另寫邏輯。
        """
        self._authorize_global(principal, "edit", project_id)
        self._assert_project_exists(principal, project_id)
        self._require_project_role(
            principal, project_id=project_id, action="remove_member", admin=True
        )
        try:
            membership_service.lock_project(self._db, project_id=project_id)
            # 鎖之內重讀：目標可能在授權檢查之後被別人移出（`[FD2]`=A 的冪等）。
            current = membership_service.resolve_project_role(
                self._db, project_id=project_id, user_id=user_id
            )
            if current is None:
                self._db.commit()
                return None
            membership_service.assert_still_has_admin(
                self._db,
                project_id=project_id,
                changing_user_id=user_id,
                new_role=None,
            )
            membership_service.delete_member(
                self._db, project_id=project_id, user_id=user_id
            )
            self._db.commit()
            return None
        except Exception:
            self._db.rollback()
            raise

    # -- 5. 角色變更（`BR3.5`／`BR5.1`）-------------------------------------

    def change_role(
        self,
        principal: Principal,
        *,
        project_id: int,
        user_id: int,
        role: str,
    ) -> MemberView:
        """變更一位成員的 per-project 角色，並**寫一列稽核**。

        `BR3.5`：一個專案可同時有**多位** `project_admin`；指定第二位
        **不得覆寫**第一位。`AC12.2.4` 斷言「兩位都能執行管理動作」，
        使覆寫成為可觸發的紅燈。

        `BR2.1`：若此變更會使該專案的 `project_admin` 數降為 0（即把最後一位
        管理者改為 `member`，**含自我降級**）則 `LastAdminGuard`。

        `BR5.1`／`BR5.3`／`BR5.4`：成功時寫一列 `cause = manual_role_change`
        的稽核，`previous_owner_user_id` = **執行變更的 principal**，
        `acknowledged_at` 留空（`BR5.5`：它只對自動改選有意義）。
        角色更新與稽核寫入**同一交易**（`NFR12.16`）——角色改了而稽核沒寫會讓
        `AC12.2.2` 的變更紀錄漏一筆，而**沒有任何東西會報錯**，畫面只是少一列。
        """
        self._authorize_global(principal, "edit", project_id)
        self._assert_project_exists(principal, project_id)
        self._require_project_role(
            principal, project_id=project_id, action="change_role", admin=True
        )
        target_role = self._validated_role(role)
        try:
            membership_service.lock_project(self._db, project_id=project_id)
            previous_role = membership_service.resolve_project_role(
                self._db, project_id=project_id, user_id=user_id
            )
            if previous_role is None:
                raise MembershipNotFound(
                    f"使用者 {user_id} 不是專案 {project_id} 的成員"
                )
            membership_service.assert_still_has_admin(
                self._db,
                project_id=project_id,
                changing_user_id=user_id,
                new_role=target_role,
            )
            view = membership_service.set_member_role(
                self._db,
                project_id=project_id,
                user_id=user_id,
                role=target_role,
            )
            membership_service.write_role_change_audit(
                self._db,
                project_id=project_id,
                cause=membership_service.CAUSE_MANUAL_ROLE_CHANGE,
                promoted_user_id=user_id,
                previous_owner_user_id=principal.user_id,
                previous_role=previous_role,
                new_role=target_role,
            )
            self._db.commit()
            return view
        except Exception:
            self._db.rollback()
            raise

    # -- 6. 停用守門（既有端點呼叫；**唯讀、不取鎖**）-----------------------

    def assert_can_deactivate(
        self, principal: Principal, *, target_user_id: int
    ) -> None:
        """既有停用端點的前置檢查（`BR6.1`）。通過回 `None`。

        **唯讀、無副作用、可安全重試**（`BR2.3`）——有副作用的守門在被拒的
        路徑上會留下殘留狀態，而 `AC12.5.3` 要求拒絕不留下半套狀態。

        **不取鎖**（`NFR12.3`）：跨專案的唯讀掃描，取鎖會把一個管理者動作變成
        一次對該使用者全部專案的廣域鎖。

        契約 `K-16` 宣告它只 raise `LastAdminGuard`，故**刻意沒有 `K3` 檢查**：
        它的唯一呼叫端是既有停用端點，而該端點的 dependency 已是
        `require_story_action("J3a", "edit")`。對它再加一層 `K3.edit` 會讓
        `Project_Admin` 之外的全域管理者（`J3a.edit` 為 True 的只有
        `Platform_Admin` 與 `Project_Admin`）在一個與成員管理無關的動作上
        被擋下。

        `[FD1]`=A 使 409 的條件**比 `FR12.5` 的字面更嚴**：`FR12.5` 寫「唯一
        **成員**」，而本守門擋的是「最後一位**管理者**」。分歧點是「專案有
        `X`（唯一管理者）與 `Y`（一般成員），停用 `X`」——`FR12.5` 的字面不擋，
        而不擋會留下一個沒有任何管理者的專案，故 `[FD1]`=A 選擇擋下。
        `AC12.3.3` 的 Given 措辭（「唯一成員」）與本定案不一致，**上游不回改**，
        由本單元的測試依 `[FD1]`=A 的條件撰寫（`functional-spec.md §四`）。
        """
        blocked = membership_service.projects_losing_last_admin(
            self._db, target_user_id=target_user_id
        )
        if blocked:
            raise LastAdminGuard(blocked)
        return None

    # -- 7. 純函式（`BR4.1`；PBT 的作用對象）--------------------------------

    @staticmethod
    def select_successor(members: List[MemberSnapshot]) -> MemberSnapshot:
        """自動改選的挑選規則。**純函式，不讀 DB**（`BR4.1`）。

        `staticmethod` 不是風格選擇：它讓「本方法拿不到 `self._db`」成為型別層
        事實，使 ADR-0006 的 PBT hard constraint 的結構前提在本類別內也成立。
        實作在 `membership_selection.py`（整支檔案不 import 任何 DB 符號）。
        """
        return select_successor(members)

    # -- `[ND1]`=A：建立專案與建立者成員列同交易 ----------------------------

    def create_project_with_owner(self, principal: Principal, *, name: str):
        """建立專案，並在**同一交易**內寫入建立者的 `project_admin` 成員列。

        `BR3.1`／`NFR12.18`：專案建立成功 ⇒ 必然存在一列
        `(project_id, 建立者, project_admin)`；任一失敗則一起回滾。
        分開交易會出現**沒有管理者的專案**，而 `BR2.1` 的守門只在「減少管理者」
        時觸發，擋不住「一開始就沒有」。

        **不取鎖**：`NFR12.1` 的鎖保護的是「對**既有**專案的成員變更」，
        而建立時該專案尚不存在、沒有併發對手。（若不寫明，實作者會以為
        `NFR12.1` 的「任何成員關係變更」涵蓋它而去鎖一個還沒有的列。）

        **交易邊界歸本方法**（`OPEN-ND19-5`）：`U7` 的
        `HierarchyFacade.create_project_nocommit` 是為此新增的變體，它 `flush`
        而不 `commit`。走 facade 而非 service 層，故 `K2` 授權判定照常發生
        （`U7` 的 `BR1.5`：不得繞過它的 facade）。

        **刻意不要求 `K3.edit`**：這一列是**系統寫入**的（`invited_by` 為
        `NULL`，`entities.md` 逐字「建立專案時自動寫入的那一列沒有邀請者」），
        而 `BR3.1` 把它定為專案建立的**後果**而非一次成員管理動作。附帶的
        實證：`K2.edit` 與 `K3.edit` 的角色集合**完全相同**（皆為
        `Platform_Admin`／`Project_Admin`／`Project_Architect`／`Project_Editor`，
        實算自 `rbac_seed_data.py`），故加上它也不會改變誰能建立專案——
        只會讓 `POST /api/hierarchy/projects` 的既有授權語意多一個無差別的條件。
        """
        try:
            project = HierarchyFacade(self._db).create_project_nocommit(
                principal, name=name
            )
            membership_service.add_member(
                self._db,
                project_id=project.id,
                user_id=principal.user_id,
                role=membership_service.ROLE_PROJECT_ADMIN,
                invited_by=None,
            )
            self._db.commit()
            self._db.refresh(project)
            return project
        except Exception:
            self._db.rollback()
            raise

    # -- 專案可見性（`U23`；`BR87.1`–`BR87.3`，`[PP1]`=A、`[PP3]`=A）----------
    #
    # 呼叫方向為 router → 本 facade → `HierarchyFacade`；`U7` 不呼叫 `U19`。
    # `K2` 判定**不在這裡**：它只有一份，在 `HierarchyFacade` 內，由下列方法經
    # `project_exists`／`list_projects_by_ids`／`list_systems_unscoped` 的第一行觸發。
    # 可見性判定只呼叫 `membership_service.visible_project_ids`／`is_project_visible`
    # ——兩者都由同一個私有選取式組出，謂詞只有一份。

    def list_visible_projects(self, principal: Principal) -> List:
        """`GET /api/hierarchy/projects` 的資料來源：請求者可見的專案，依 id 遞增。

        可見 ＝ 成員列 ∪（擁有者 且 該專案零成員列）。`K2 view` 由
        `list_projects_by_ids` 的第一行判定——可見集合為空也判定，故缺 `K2` 者一律
        403 而非 200 `[]`。

        **如實記載的順序**：可見 id 的查詢早於 `K2` 判定一條語句（`list_projects_by_ids`
        需要 id 集合作參數）。被拒時該結果直接丟棄、不回傳任何東西，故不外洩；
        但「判定先於任何讀取」在這一支是**先讀一次 id、再判定**。
        """
        project_ids = membership_service.visible_project_ids(
            self._db, user_id=principal.user_id
        )
        return HierarchyFacade(self._db).list_projects_by_ids(
            principal, project_ids=project_ids
        )

    def list_visible_systems(self, principal: Principal, *, project_id: int) -> List:
        """`GET /api/hierarchy/projects/{project_id}/systems` 的資料來源（`BR87.2`）。

        判定順序固定為三步：

        1. `HierarchyFacade.project_exists`——其第一行即 `K2 view` 判定，
           `HierarchyForbidden` **原樣上拋**（router 轉 403）。**不得**改走
           `_assert_project_exists`：它把 `HierarchyForbidden` 轉成
           `MembershipNotFound`，會讓缺 `K2` 者得到 404（既有 `T2b` 紅燈）。
        2. 專案不存在 → `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)` → 404。
        3. 不在可見集合內 → **同一個例外、同一句訊息** → 404，與第 2 步的回應逐位元
           相同（nfr-requirements `R-01`）。可見 → `list_systems_unscoped`。
        """
        hierarchy = HierarchyFacade(self._db)
        if not hierarchy.project_exists(principal, project_id=project_id):
            raise MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)
        if not membership_service.is_project_visible(
            self._db, project_id=project_id, user_id=principal.user_id
        ):
            raise MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)
        return hierarchy.list_systems_unscoped(principal, project_id=project_id)

    def project_visibility(self, principal: Principal) -> Callable[[int], bool]:
        """`HierarchyFacade` 三條寫入路徑的守門判定（注入用，`security-design.md` §二之一）。

        回傳一個只在本次請求內存活的閉包；`HierarchyFacade` 只知道它是
        `Callable[[int], bool]`，原始碼不 import 任何成員關係符號（`BR87.3`）。
        **非測試程式唯一合法的 `project_visible` 來源就是本方法**（ast 靜態鎖第 3 條）。
        """
        db = self._db
        user_id = principal.user_id

        def _visible(project_id: int) -> bool:
            return membership_service.is_project_visible(
                db, project_id=project_id, user_id=user_id
            )

        return _visible

    # -- 橫幅（`BR5.5`／`BR5.6`）-------------------------------------------

    def list_my_pending_reselections(
        self, principal: Principal
    ) -> List[ReselectionEvent]:
        """我自己未確認的**自動改選**事件（`BR5.5`）。

        **刻意只問自己的**：以 `principal.user_id` 為條件，故不需要
        per-project 判定——一個人永遠有權知道自己被改選了。
        """
        return membership_service.list_unacknowledged_reselections(
            self._db, user_id=principal.user_id
        )

    def acknowledge_reselection(self, principal: Principal, *, event_id: int) -> bool:
        """把該**事件列**標為已讀（`BR5.6`）。以事件為鍵，不是 per-user 布林值。"""
        try:
            changed = membership_service.acknowledge_reselection(
                self._db, event_id=event_id, user_id=principal.user_id
            )
            self._db.commit()
            return changed
        except Exception:
            self._db.rollback()
            raise

    # -- 自動改選（系統發起；無 principal，因為沒有人按按鈕）---------------

    def run_auto_reselection(self, *, deactivated_user_id: int) -> List[ReselectionEvent]:
        """`BR4.4`：停用帳號**成功之後**對該使用者擁有的專案各跑一次改選。

        **沒有 `principal` 參數，而這是刻意的**：它由系統發起、無人按下按鈕
        （`BR5.1` 逐字「自動改選尤其必要：它由系統發起、無人按下按鈕」）。
        把一個 principal 塞進來會暗示有人授權了這次角色變更，而稽核列的
        `previous_owner_user_id` 在 `auto_reselection` 下記的是**被停用的
        owner**（`BR5.4`），不是執行停用的管理者。

        它不是受保護操作的入口——呼叫端（既有停用端點）的授權已在
        `require_story_action("J3a", "edit")` 完成，且**停用必須已經成功**。
        """
        return membership_service.run_auto_reselection(
            self._db, deactivated_user_id=deactivated_user_id
        )


def guard_report(exc: LastAdminGuard) -> LastAdminGuardReport:
    """把守門例外轉成 409 的回應本體（`BR6.2`）。"""
    return LastAdminGuardReport(projects=list(exc.projects))


__all__ = [
    "MembershipError",
    "MembershipFacade",
    "MembershipForbidden",
    "MembershipNotFound",
    "MissingGlobalPermission",
    "LastAdminGuard",
    "LastAdminGuardReport",
    "GuardedProjectRef",
    "MemberView",
    "ProjectRole",
    "Principal",
    "mint_principal",
    "guard_report",
]
