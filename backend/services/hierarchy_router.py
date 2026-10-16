"""
hierarchy_router.py — `U7 hierarchy-service` 的 HTTP 表面

**契約（前端依賴，請勿變更）**

契約 `K-07` 的實作注意逐字：「每個 router handler 只做『取身分 → 呼叫 facade →
轉譯例外』，**不得自行呼叫底層 service**（否則 facade 不再是唯一授權入口）」。

本檔因此**不 import `hierarchy_service`**，也**不 import 判定支援型查詢**
（`project_exists`／`get_project_owner`／`get_project_of_system`）——後者是
`BR6.4` 三道約束的第 (1) 項：它們**只能同進程呼叫，不得經任何 HTTP path 暴露**。
把它們接上端點會讓 `BR6.1` 的列範圍被整個繞過。

**授權不掛在 dependency 上**（`BR1.1`）：`require_story_action` 會 raise
`HTTPException`，而本單元的拒絕必須是 `HierarchyForbidden`，且判定必須與同進程
呼叫端**共用同一個落點**。故這裡只取已驗證的使用者，`K2` 判定在 facade 內。

五個 path 中前四個來自 `K-07` 的 OpenAPI 區塊（消費端 `U16`／`U23`）；
第五個（`/diagram-changes`）是 `DG-3` 的落地（`BR5.1`／`[F2]`=A），
**不在 K-07 內**，故在落地前不受既有兩道漂移閘門保護（`OPEN-H9`）。

`responses={409: ...}` 的**顯式宣告是必要的**（`NFR5.2`／`BR6.6`）：
`unit-of-work.md:447` 逐字「實測 `openapi.json` 的 55 個 operation 宣告的狀態碼
只有 `{200:53, 422:45, 201:1, 204:1}`，**非 2xx/422 的宣告數為 0**」。
不宣告則該契約不進 spec、前端產不出型別，**而 CI 保持綠燈**——
這是本單元唯一不會被任何自動化抓到的遺漏。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.auth import get_current_user
from services.hierarchy_facade import (
    HierarchyConflictError,
    HierarchyFacade,
    HierarchyForbidden,
    HierarchyNotFound,
    HierarchyValidationError,
    mint_principal,
)
# `[ND1]`=A：建立專案的 handler 退化為對 `U19` 的薄委派（見 `create_project`）。
# **以模組形式匯入**，不從它匯入名稱：`membership_facade` 匯入
# `hierarchy_facade`，而本檔也匯入它——模組形式讓解析發生在**呼叫時**而非
# 匯入時，與本檔底部 `hierarchy_service` 的處理同一個理由。
import services.membership_facade as membership_facade
from services.membership_errors import MembershipNotFound

logger = logging.getLogger("cloud360.hierarchy_router")

router = APIRouter()


# ---------------------------------------------------------------------------
# 回應模型（`team.md` 規則 B 要求測試斷言其欄位集合）
# ---------------------------------------------------------------------------


class ProjectOut(BaseModel):
    # **欄位命名沿用本 repo 既有的 snake_case 回應慣例**（`UserSchema` 的
    # `is_active`／`authorization_status`／`last_activity_at`），不自創 camelCase
    # ——`team.md` 要求新增呼叫點沿用現有形狀，不單點自創抽象。
    # `entities.md` 的 camelCase 是**技術中立的邏輯名**，不是線上格式。
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_user_id: int
    is_default: bool
    created_at: Optional[datetime] = None


class SystemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    is_default: bool
    created_at: Optional[datetime] = None


class DiagramChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    diagram_id: int
    # `source` 刻意出現在回應中：`NFR7.1`／`BR6.3` 要求讀者能知道涵蓋範圍由
    # 它宣告，而非由資料表名稱宣告（`U4` 註解逐字「read source before
    # presenting anything」）。**本回應不是完整變更歷史。**
    source: str
    actor_user_id: int
    requirement_summary: str
    requirement_label: str
    created_at: Optional[datetime] = None


class CreateProjectIn(BaseModel):
    name: str


class CreateSystemIn(BaseModel):
    name: str


CONFLICT_RESPONSE = {
    409: {
        "description": (
            "衝突：名稱重複、預設組不可刪除，或底下仍有系統／架構圖"
            "（訊息含剩餘數量）"
        )
    }
}
"""`NFR5.2`／`BR6.6`：必須顯式宣告，否則不進 `openapi.json`。"""


def _facade(db: Session) -> HierarchyFacade:
    return HierarchyFacade(db)


def _translate(exc: Exception) -> HTTPException:
    """把 facade 層例外轉成 HTTP。**這是唯一的轉譯點。**"""
    if isinstance(exc, HierarchyForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (HierarchyNotFound, MembershipNotFound)):
        # `MembershipNotFound`：`[ND1]`=A 之後 `create_project` 走 `U19` 的
        # 組合路徑，而它會在找不到建立者時 raise 這一個。
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, HierarchyConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, HierarchyValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    raise exc


# ---------------------------------------------------------------------------
# 1 / 2：專案（`W7` 列舉、`W1` 建立）
# ---------------------------------------------------------------------------


@router.get("/projects", response_model=List[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W7`：列出**使用者可見的**專案，依 id 遞增。

    「可見」＝請求者有成員列的專案 ∪ 請求者是擁有者、且該專案尚無任何成員列的專案
    （`U23`，`BR87.1`）。被邀請的成員看得到專案；被另一位管理者移出的建立者看不到。
    缺 `K2 view` 時回 403——即使可見集合為空。
    """
    try:
        return membership_facade.MembershipFacade(db).list_visible_projects(
            mint_principal(current_user)
        )
    except Exception as exc:  # noqa: BLE001 - 轉譯後重新拋出
        raise _translate(exc) from exc


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_RESPONSE,
)
def create_project(
    payload: CreateProjectIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W1`：建立專案。**非冪等，不得自動重試**（`BR2.4`）。

    **本 handler 自 `U19` 起退化為薄委派**（`[ND1]`=A／`NFR12.18`／`BR3.1`）：
    它呼叫 `MembershipFacade.create_project_with_owner`，後者在**同一個交易**內
    建立專案並寫入建立者的 `project_admin` 成員列。

    為什麼不能留在這裡直呼 `HierarchyFacade.create_project`：那一支自己
    `db.commit()`，於是「建專案」與「寫成員列」會是**兩個交易**，中間失敗就
    留下一個**零成員專案**——正是 `[ND1]`=A 要消除的狀態，而 `BR2.1` 的守門只
    在「減少管理者」時觸發，擋不住「一開始就沒有」。

    **`K2` 的授權判定沒有改變**：`create_project_with_owner` 內部仍走
    `HierarchyFacade.create_project_nocommit`，而它與 `create_project` 共用
    同一個 `_authorize(principal, "edit")`。**路徑、回應模型與狀態碼都不變**，
    故 `openapi.json` 不因本變更漂移。

    `U19` 的例外在這裡也要轉譯：`MembershipNotFound` → 404。其餘
    （`HierarchyConflictError` → 409 等）沿用既有的 `_translate`。
    """
    try:
        return membership_facade.MembershipFacade(db).create_project_with_owner(
            mint_principal(current_user), name=payload.name
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


# ---------------------------------------------------------------------------
# 3 / 4：系統（`W7` 列舉、`W2` 建立）
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/systems",
    response_model=List[SystemOut],
    responses={404: {"description": "查不到該專案（含「不屬於你」——刻意同一種結果）"}},
)
def list_systems(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W7`：列出該專案的系統，依 id 遞增。

    只對該專案的可見者回 200（`U23`，`BR87.2`：成員；或擁有者且專案尚無任何成員列）。
    缺 `K2 view` 一律 403（不論專案是否存在）；專案不存在與存在但不可見一律 **404**，
    且兩者的回應本體相同。
    """
    try:
        return membership_facade.MembershipFacade(db).list_visible_systems(
            mint_principal(current_user), project_id=project_id
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


@router.post(
    "/projects/{project_id}/systems",
    response_model=SystemOut,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_RESPONSE,
)
def create_system(
    project_id: int,
    payload: CreateSystemIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W2`：在指定專案下建立系統。`BR6.5` 的擁有者檢查在 facade 內。"""
    # `U23`（functional-design `R-01` 使用者裁決）：可見性守門也在 facade 內，判定由
    # `U19` 的 `MembershipFacade.project_visibility` 產生並注入。不在請求者可見集合內
    # 的專案（含被移出的建立者）回 404，與真正的不存在逐位元相同。
    # 刻意寫成註解而非 docstring：docstring 是 operation 的 description，改它會讓
    # `openapi.json` 多漂移一支（本單元只讓兩支列舉端點的 description 漂移，`BR87.4`）。
    try:
        principal = mint_principal(current_user)
        return _facade(db).create_system(
            principal,
            project_id=project_id,
            name=payload.name,
            project_visible=membership_facade.MembershipFacade(db).project_visibility(
                principal
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc


# ---------------------------------------------------------------------------
# 5 / 6：刪除（`W6`）—— **任何情況都不級聯**
# ---------------------------------------------------------------------------


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=CONFLICT_RESPONSE,
)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W6`（專案）。底下仍有系統時回 **409** 並說明剩餘數量（`BR4.4`）。"""
    # `U23`：可見性守門早於擁有者檢查與 409——不可見者一律 404「查不到專案」。
    try:
        principal = mint_principal(current_user)
        _facade(db).delete_project(
            principal,
            project_id=project_id,
            project_visible=membership_facade.MembershipFacade(db).project_visibility(
                principal
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc
    return None


@router.delete(
    "/systems/{system_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=CONFLICT_RESPONSE,
)
def delete_system(
    system_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W6`（系統）。仍有架構圖歸屬時回 **409** 並說明張數（`BR4.3`）。"""
    # `U23`：可見性守門早於擁有者檢查與 409——系統不存在、或其所屬專案不在請求者的
    # 可見集合內，一律 404「查不到系統」。
    try:
        principal = mint_principal(current_user)
        _facade(db).delete_system(
            principal,
            system_id=system_id,
            project_visible=membership_facade.MembershipFacade(db).project_visibility(
                principal
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc
    return None


# ---------------------------------------------------------------------------
# 7：變更紀錄查詢（`W5`／`W8`、`DG-3` 的落地）
# ---------------------------------------------------------------------------


@router.get("/diagram-changes", response_model=List[DiagramChangeOut])
def list_diagram_changes(
    label: Optional[str] = Query(None, description="以輕量標籤比對"),
    system_id: Optional[int] = Query(
        None,
        description=(
            "以系統上溯比對。注意：`system_id` 為空的架構圖查不到"
            "——新建的圖從未被指派系統歸屬（OPEN-H11）"
        ),
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """`W5`／`W8`：查詢變更紀錄。

    **回應不是完整變更歷史**（`NFR7.1`）：涵蓋範圍由每一列的 `source` 宣告，
    而非由資料表名稱宣告。經既有 A1 頁面的異動**不會出現在這裡**
    （`BR5.3`：`source` 的允許值只有 `brain_orchestration`）。
    紀錄壽命另有兩個界限：隨架構圖級聯刪除、保存期 90 天（`BR5.5`）。
    """
    try:
        return _facade(db).list_diagram_changes(
            mint_principal(current_user), label=label, system_id=system_id
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate(exc) from exc
