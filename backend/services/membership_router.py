"""
membership_router.py — `U19 membership-service` 的 HTTP 表面

**契約（前端依賴，請勿變更）**

每個 handler 只做三件事：**取身分 → 呼叫 facade → 轉譯例外**。
**不得自行呼叫 `membership_service`**（否則 facade 不再是唯一授權入口，
`BR1.1`），故本檔**不 import `membership_service`**。

授權分兩層，而兩層都在這裡看得見（`BR1.2`）：

1. **全域功能權限**由既有 `require_story_action("K3", <action>)` 這個
   **FastAPI dependency** 承載——`BR1.2` 逐字「全域那一層仍由既有
   `require_story_action` 承載（本元件**不重新實作它**）」。
2. **per-project** 那一層在 `MembershipFacade` 內。

本檔與 `hierarchy_router` 在這一點上刻意不同（那一支把 `K2` 判定完全放進
facade、dependency 只取身分）。理由是契約不同：`K-07` 沒有「兩層串聯」這一條，
`K-16` 有，而它指名了第一層的承載者。facade 另以 `user_can` 自行驗一次全域層，
使**同進程呼叫端**（`U20`／`U13`，沒有 dependency 鏈）也是兩層的
——HTTP 路徑因此驗兩次同一個謂詞，那是刻意的。

**`responses={409: {"model": LastAdminGuardReport}}` 的顯式宣告是必要的**
（`BR6.2`）：FastAPI **不**從 `raise HTTPException` 推導狀態碼，故不宣告則該
契約不進 `openapi.json`、前端產不出型別，而
`backend/scripts/dump_openapi.py --check` 與 `npm run check:types`
**兩道漂移閘門都保持綠燈**。這是本單元唯一「違反後沒有任何東西變紅」的規則。

**409 的回應本體是 `LastAdminGuardReport` 本身，不是 `{"detail": ...}`**：
`AC12.3.3` 的 Then 要求列出那些專案，而宣告一個 model 卻回一個包裝過的
形狀，等於讓 spec 說一件回應沒有做的事。故守門命中時以 `JSONResponse`
回傳，而不是 `raise HTTPException`。

**掛在既有 `/api/` 之下，不新增監聽埠**（`embedded`）：`deploy/nginx.conf`
只反向代理 `/api/`，而本單元零新進程、零新環境變數、不改 `deploy/` 任何檔案。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.membership_errors import (
    LastAdminGuard,
    MembershipForbidden,
    MembershipLockTimeout,
    MembershipNotFound,
    MissingGlobalPermission,
)
from services.membership_facade import MembershipFacade, guard_report, mint_principal
from services.membership_types import LastAdminGuardReport, MemberView, ProjectRole
from services.rbac import require_story_action

logger = logging.getLogger("cloud360.membership_router")

router = APIRouter()


# ---------------------------------------------------------------------------
# 請求／回應模型（`team.md` 規則 B 要求測試斷言其欄位集合）
# ---------------------------------------------------------------------------


class InviteMemberIn(BaseModel):
    user_id: int
    role: ProjectRole


class ChangeRoleIn(BaseModel):
    role: ProjectRole


class ReselectionOut(BaseModel):
    """一筆未確認的自動改選事件。

    **刻意只含事件本身的欄位，不含專案名稱**：橫幅的**顯示**形狀屬 `U23`／`U24`
    （本單元無前端面——實測 `frontend/src` 對 `projects` 的命中數為 0）。
    這一點與 `LastAdminGuardReport` 刻意帶名稱不同，而差別有依據：後者的名稱
    需求來自 `entities.md` 的逐字約束（「只給 id 的話畫面無法告知使用者是哪個
    專案」），而橫幅的對應需求沒有任何已核可 AC 指定它的欄位集合。消費端若
    需要名稱，那是一次有明確來源的擴充，不是本單元自行放大回傳形狀。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    cause: str
    promoted_user_id: int
    previous_owner_user_id: Optional[int] = None
    previous_role: Optional[str] = None
    new_role: str
    occurred_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None


LAST_ADMIN_GUARD_RESPONSE = {
    409: {
        "model": LastAdminGuardReport,
        "description": (
            "守門命中：此操作會讓列出的專案失去最後一位專案管理者"
            "（`BR2.1`）。回應本體即 `LastAdminGuardReport`，含每個專案的 "
            "`project_id` 與 `name`"
        ),
    }
}
"""`BR6.2`：必須顯式宣告，否則不進 `openapi.json`，而 CI 保持綠燈。"""

NOT_FOUND_RESPONSE = {
    404: {
        "description": (
            "查不到該專案（不存在，或呼叫者不是該專案的成員——兩者回應逐位元相同、"
            "不含專案 id，合併前必修第 14 項），或查不到該成員"
        )
    }
}
FORBIDDEN_RESPONSE = {
    403: {
        "description": (
            "缺 `K3` 的全域功能權限，或是該專案的成員但不是專案管理者"
            "（`BR1.2` 兩層串聯；非成員回 404，不回 403）"
        )
    }
}
LOCK_TIMEOUT_RESPONSE = {
    503: {
        "description": (
            "取專案列鎖的等待超過上限（`LOCK_TIMEOUT_MS`，合併前必修第 16 項）："
            "另一筆對同一專案的成員變更尚未結束。交易已回滾、未做任何變更，"
            "請稍後再試"
        )
    }
}
"""只宣告在**會取鎖**的三個端點（邀請、移出、改角色）；清單與橫幅不取鎖。"""


def _facade(db: Session) -> MembershipFacade:
    return MembershipFacade(db)


def _translate(exc: Exception) -> HTTPException:
    """把領域例外轉成 HTTP。**這是唯一的轉譯點。**

    `LastAdminGuard` **不在這裡**——它需要一個完整的回應本體而非 `detail`
    字串，故由各 handler 以 `JSONResponse` 處理（見 `_guard_response`）。
    """
    if isinstance(exc, MembershipForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, MembershipNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, MissingGlobalPermission):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    if isinstance(exc, MembershipLockTimeout):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    raise exc


def _guard_response(exc: LastAdminGuard) -> JSONResponse:
    """`BR6.2`：409 的本體**就是** `LastAdminGuardReport`。"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder(guard_report(exc)),
    )


# ---------------------------------------------------------------------------
# 1：成員清單（`AC12.1.1`／`AC12.2.1`／`AC12.6.1`／`AC12.6.2` 的觀察面）
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/members",
    response_model=List[MemberView],
    responses={**FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def list_members(
    project_id: int,
    current_user: User = Depends(require_story_action("K3", "view")),
    db: Session = Depends(get_db),
):
    """`U24` 成員頁的唯一資料來源。**非成員即拒**（`BR1.6`）。

    `AC12.2.3`（清單上沒有改角色的控件）的伺服器側對應：本端點**只回傳**
    成員檢視，不提供任何變更入口。
    """
    try:
        return _facade(db).list_members(
            mint_principal(current_user), project_id=project_id
        )
    except Exception as exc:  # noqa: BLE001 - 轉譯後重新拋出
        raise _translate(exc) from exc


# ---------------------------------------------------------------------------
# 2：邀請（**非冪等**，`BR3.3`）
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/members",
    response_model=MemberView,
    status_code=status.HTTP_201_CREATED,
    responses={
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **LOCK_TIMEOUT_RESPONSE,
        422: {
            "description": (
                "受邀者缺少對應的全域功能權限（`BR3.2`／`AC12.5.1`），"
                "或角色不在封閉列舉內"
            )
        },
    },
)
def invite_member(
    project_id: int,
    payload: InviteMemberIn,
    current_user: User = Depends(require_story_action("K3", "edit")),
    db: Session = Depends(get_db),
):
    """邀請一位成員。**非冪等，呼叫端不得自動重試**（`BR3.3`）。

    成功是一級行為（`BR3.6`）：成功 ⇒ 成員清單必然多一列。
    被拒時成員清單**不新增任何列**（`AC12.5.3`，由 facade 的單一交易保證）。
    """
    try:
        return _facade(db).invite_member(
            mint_principal(current_user),
            project_id=project_id,
            user_id=payload.user_id,
            role=payload.role.value,
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


# ---------------------------------------------------------------------------
# 3：移出（**冪等**，`BR3.4`／`[FD2]`=A；可命中守門）
# ---------------------------------------------------------------------------


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **LAST_ADMIN_GUARD_RESPONSE,
        **LOCK_TIMEOUT_RESPONSE,
    },
)
def remove_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(require_story_action("K3", "edit")),
    db: Session = Depends(get_db),
):
    """移出一位成員。**對已非成員回 204**（冪等，`[FD2]`=A）。

    守門命中（含**自我移出**最後一位管理者）時回 **409** ＋
    `LastAdminGuardReport`。
    """
    try:
        _facade(db).remove_member(
            mint_principal(current_user), project_id=project_id, user_id=user_id
        )
    except LastAdminGuard as exc:
        return _guard_response(exc)
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 4：角色變更（`BR3.5`／`BR5.1`；可命中守門）
# ---------------------------------------------------------------------------


@router.patch(
    "/projects/{project_id}/members/{user_id}",
    response_model=MemberView,
    responses={
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **LAST_ADMIN_GUARD_RESPONSE,
        **LOCK_TIMEOUT_RESPONSE,
    },
)
def change_member_role(
    project_id: int,
    user_id: int,
    payload: ChangeRoleIn,
    current_user: User = Depends(require_story_action("K3", "edit")),
    db: Session = Depends(get_db),
):
    """變更一位成員的 per-project 角色，並寫一列稽核（`BR5.1`）。

    一個專案可同時有**多位** `project_admin`；指定第二位**不覆寫**第一位
    （`BR3.5`）。把最後一位管理者改為 `member`（含**自我降級**）時回 **409**。
    """
    try:
        return _facade(db).change_role(
            mint_principal(current_user),
            project_id=project_id,
            user_id=user_id,
            role=payload.role.value,
        )
    except LastAdminGuard as exc:
        return _guard_response(exc)
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


# ---------------------------------------------------------------------------
# 5／6：橫幅（`BR5.5`／`BR5.6`）
# ---------------------------------------------------------------------------


@router.get("/reselections/pending", response_model=List[ReselectionOut])
def list_pending_reselections(
    current_user: User = Depends(require_story_action("K3", "view")),
    db: Session = Depends(get_db),
):
    """我自己未確認的**自動改選**事件。

    `BR5.5`：查詢同時過濾 `cause = 'auto_reselection'` 與
    `acknowledged_at IS NULL`。漏掉 `cause` 過濾會讓**每一次人工角色變更**都
    彈出一則橫幅，而文案是「系統自動把管理權交給你」——對人工變更是錯的訊息。

    只問自己的（以 `principal.user_id` 為條件），故不需要 per-project 判定。
    """
    try:
        return _facade(db).list_my_pending_reselections(mint_principal(current_user))
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


@router.post(
    "/reselections/{event_id}/acknowledge",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "查不到該事件、它不屬於你，或它已被確認"}},
)
def acknowledge_reselection(
    event_id: int,
    current_user: User = Depends(require_story_action("K3", "view")),
    db: Session = Depends(get_db),
):
    """把該**事件列**標為已讀（`BR5.6`）。

    以**事件**為鍵而不是 per-user 布林值：後者會讓同一人第二次被改選時看不到
    橫幅，而那正是 `FR12.4c` 要防的情境。狀態在伺服器端，故跨裝置一致
    （`AC12.4.4`）。

    已確認或不屬於你的事件回 **404**——重按一次「知道了」不是伺服器錯誤，
    但也不該回 204 說「改到了」。
    """
    try:
        changed = _facade(db).acknowledge_reselection(
            mint_principal(current_user), event_id=event_id
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="查不到未確認的改選事件",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
