"""
membership_errors.py — `U19 membership-service` 的領域例外

**契約（同進程呼叫端依賴，請勿變更）**

四個例外型別**都不是** `HTTPException` 的子類別，也都不 raise 它
（`BR1.5`；契約 `K-16` 的 `on_denied` 逐字「raise MembershipForbidden(...)
—— **不是** HTTPException」）。

為什麼這件事是結構性的而不是風格偏好：`U13 brain-gateway` 是 **WebSocket**
消費端，握手之後每則訊息都在同一個連線裡、**不經 FastAPI 的 dependency 鏈**
——它根本沒有 HTTP 回應可回。若本層 raise `HTTPException`，它與 `U20`
（同進程 facade）都會被迫處理一個對它們無意義的 HTTP 層型別。

轉譯成 HTTP 狀態碼的唯一落點是 `membership_router._translate()`：
`MembershipForbidden` → 403、`MembershipNotFound` → 404、
`MissingGlobalPermission` → 422、`LastAdminGuard` → **409**、
`MembershipLockTimeout` → **503**（合併前必修第 16 項）。
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from services.membership_types import GuardedProjectRef


class MembershipError(Exception):
    """本單元所有領域例外的基底。**刻意不繼承 `HTTPException`。**"""


class MembershipForbidden(MembershipError):
    """per-project 授權未通過（`BR1.5`）。router 轉 403。

    三個屬性與 `NFR12.6` 的拒絕 log 欄位集合一對一對應
    （`security-design.md §二`：`story_id`／`action`／`project_id`／`principal`），
    使 log 與例外可互相對照。`principal` 不放進例外——它是呼叫端已經持有的東西，
    放進例外只會讓錯誤訊息多帶一個身分識別。
    """

    def __init__(
        self, story_id: str, action: str, project_id: Optional[int] = None
    ) -> None:
        super().__init__(
            f"權限不足：需要 {story_id}.{action}"
            + (f"（專案 {project_id}）" if project_id is not None else "")
        )
        self.story_id = story_id
        self.action = action
        self.project_id = project_id


class MembershipNotFound(MembershipError):
    """查不到專案或成員列。router 轉 404。

    `resolve_project_role` 對「非成員」**仍回 `None`**（`BR1.6`），不是例外。
    把非成員做成例外會讓 `resolve_project_role` 的熱路徑用例外控制流程，
    且 `K-16` 的 `public_interface` 第一項逐字要求回 `None`。

    **但受保護操作**（清單、邀請、移出、改角色）對非成員的拒絕自合併前必修第 14 項
    （`[PP-MB14]`=A）起改用本例外、訊息 `PROJECT_NOT_FOUND_DETAIL`，與「專案不存在」
    逐位元相同（`MembershipFacade._require_project_role`）。
    """


class MissingGlobalPermission(MembershipError):
    """受邀者缺少對應的全域功能權限（`BR3.2`／`FR12.6a`）。router 轉 422。

    **主詞是受邀者，不是 principal**：principal 自己的授權不足是
    `MembershipForbidden`。兩者分開的理由是 `AC12.5.1` 要求「**說明他缺什麼**」
    ——訊息的對象是執行邀請的管理者，而缺權限的是被邀請的人。
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        action: str,
        reason: Optional[str] = None,
    ) -> None:
        # `reason`（合併前必修第 4 項）：拒絕原因是**帳號狀態**（已停用、待核准）
        # 而非角色時，訊息要說出是哪一個，否則管理者會去改一個本來就對的角色。
        if reason:
            message = f"無法邀請：使用者 {user_id} {reason}"
        else:
            message = f"無法邀請：使用者 {user_id} 缺少全域功能權限 {story_id}.{action}"
        super().__init__(message)
        self.user_id = user_id
        self.story_id = story_id
        self.action = action
        self.reason = reason


class LastAdminGuard(MembershipError):
    """守門命中：該操作會讓某些專案失去最後一位 `project_admin`（`BR2.1`）。

    router 轉 **409**，酬載為 `LastAdminGuardReport`（`BR6.1`／`BR6.2`）。

    `projects` 必須同時帶 id 與名稱——`AC12.3.3` 的 Then 要求列出**那些專案**，
    而只給 id 的話畫面無法告知使用者是哪一個（`entities.md` 逐字）。
    """

    def __init__(self, projects: Sequence[GuardedProjectRef]) -> None:
        self.projects: List[GuardedProjectRef] = list(projects)
        names = "、".join(f"{p.name}（#{p.project_id}）" for p in self.projects)
        super().__init__(
            "操作被拒：下列專案會因此失去最後一位專案管理者，"
            f"請先指定接手人——{names}"
        )


class MembershipLockTimeout(MembershipError):
    """取專案列鎖的等待超過上限（合併前必修第 16 項）。router 轉 **503**。

    由 `membership_service.lock_project` 在 PostgreSQL 回 SQLSTATE `55P03`
    （`lock_not_available`，即 `lock_timeout` 到期）時拋出。拋出時資料庫已中止
    該交易；呼叫端的 `rollback()` 會把連線還給連線池。

    存在的理由：沒有逾時時，一筆卡住不放的交易會讓其他請求無限期排隊，
    每個排隊的請求各佔一條連線，而連線池預設只有 15 條——等於一筆卡住的交易
    可以拖垮整個 backend。逾時後回 503「請稍後再試」，連線立即釋放。
    """

    def __init__(self, project_id: int) -> None:
        super().__init__(f"專案 {project_id} 目前有其他成員變更進行中，請稍後再試")
        self.project_id = project_id


class NoQualifiedSuccessor(MembershipError):
    """自動改選時，該專案既沒有其他合格管理者、也沒有合格接手人。

    停用守門會擋下「被停用者是管理者且無合格接手人」的情況，故走到這裡的是
    守門之後才變得無人合格的專案（競態、重送），或被停用者擁有但不管理、而專案
    本來就沒有合格管理者的專案。不論哪一種，結果都是**沒有人能管的專案**——
    合併前必修第 10 項要求這種結果不得無聲，故以例外回報，由
    `run_auto_reselection` 計入 `failed_project_ids`（code-generation review-03 的 Minor 2）。
    """

    def __init__(self, project_id: int) -> None:
        super().__init__(f"專案 {project_id} 沒有合格的管理者或接手人")
        self.project_id = project_id


__all__ = [
    "MembershipError",
    "MembershipForbidden",
    "MembershipNotFound",
    "MissingGlobalPermission",
    "LastAdminGuard",
    "MembershipLockTimeout",
    "NoQualifiedSuccessor",
]
