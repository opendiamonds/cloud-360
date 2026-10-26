"""
user_router — 登入／註冊／使用者角色／角色權限矩陣／J5 授權申請 API
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import logging
import re

from database import get_db
from models import User, RolePermission, RoleAuthorizationRequest, UserDiagram, UserDiagramChat
from models import diagram_shares
# 合併前必修第 3 項（OQ-H1 裁決）：刪除使用者前的參照預檢與空預設專案清除。
# 依 team.md 的 user_router.py 規則就地沿用既有形狀，不抽 service 層。
from models import (
    ArchitectureReview,
    DiagramChangeRecord,
    EstimateAuditEvent,
    MemoryAuditEvent,
    MemoryRecord,
    Project,
    ProjectMember,
    ReselectionEvent,
    System,
    SystemRequirementField,
    WaLens,
)
from services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from services.activity import as_aware_utc, is_overdue, record_activity
# U19 membership-service（契約 `K-16` 的 `existing_endpoint_extension`）：
# 停用端點的 per-project 前置檢查與自動改選。經 **facade** 而非 service 層
# ——`BR1.1` 要求 `MembershipFacade` 是唯一入口。
from services.membership_errors import LastAdminGuard
from services.membership_facade import MembershipFacade, guard_report, mint_principal
from services.membership_types import LastAdminGuardReport, ReselectionFailureReport
from services.rbac import (
    CANONICAL_ROLES,
    STORY_IDS,
    ARCH_DIAGRAM_STORIES,
    is_canonical_role,
    normalize_role,
    permissions_map_for_role,
    list_all_permissions,
    require_story_action,
    user_can,
    ensure_role_permissions_seeded,
    sync_arch_permission_flags,
    admin_may_decide_role,
    RESTRICTED_APPROVAL_ROLES,
)
# 合併前必修第 11 項：系統保留帳號（90 天清除的稽核 actor）的唯一辨識點。
from services.system_accounts import (
    RESERVED_ACCOUNT_CONFLICT_DETAIL,
    RESERVED_SYSTEM_USERNAMES,
    is_reserved_system_account,
)

logger = logging.getLogger("cloud360.user_router")
router = APIRouter()

ROLE_DISPLAY_NAMES = {
    "Project_Architect": "雲端架構師",
    "Developer": "開發者",
    "Project_Editor": "專案編輯",
    "Project_Admin": "專案管理員",
    "FinOps_Analyst": "FinOps 分析師",
    "SRE": "SRE",
    "Ops_Lead": "維運主管",
    "Platform_Engineer": "平台工程師",
    "Security_Reviewer": "資安審查員",
    "Platform_Admin": "平台管理員",
    "Platform_Owner": "平台擁有者",
}

# 註冊角色目錄「可使用功能」顯示名（對齊 Admin 矩陣／role-permission-design）
STORY_FEATURE_LABELS = {
    "A1": "架構圖生成",
    "A2": "架構圖生成",
    "A4": "架構圖生成",
    "A3": "Well-Architected 評核",
    "B1": "單一雲端評選",
    "B2": "生態相容掃描",
    "B3": "地緣合規與延遲",
    "C1": "上傳與檢視估價表",
    "C2": "資源優化定價",
    "C3": "Egress 隱性成本",
    "D1": "Terraform 產出",
    "D2": "IaC 安全掃描",
    "D3": "Secret／敏感值",
    "E1": "Right-sizing",
    "E2": "架構現代化",
    "E3": "Runbooks 生成",
    "F1": "跨雲健康查詢",
    "F2": "變更與回滾",
    "F3": "高風險審批閘門",
    "G1": "CSPM 持續合規",
    "G2": "IAM 最小權限",
    "G3": "Policy-as-Code",
    "H1": "內部 API 註冊",
    "H2": "Agent 存取邊界",
    "H3": "MCP／Skill 生命週期",
    "J3a": "使用者設定",
    "J3b": "細項設定",
    # K 字首：U3 rbac-story-ids 新增的四個能力（BR4.3′）。
    # 這四個標籤會出現在**公開的** /roles/catalog（無 Depends(get_current_user)）
    # ——照 J3a／J3b 的既有先例發布，刻意**不**加入 CATALOG_EXCLUDED_STORIES
    # （BR4.5）。該端點本就逐角色列出其持有能力的中文標籤，這是它的既有設計
    # 目的；它不揭露的是「誰是什麼角色」。K1–K4 不改變揭露的類別。
    "K1": "統一入口頁",
    "K2": "專案／系統階層",
    "K3": "專案成員管理",
    "K4": "需求欄位",
}
# 登入能力不列入註冊功能摘要
CATALOG_EXCLUDED_STORIES = frozenset({"J1"})


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    requested_role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: Optional[str] = None
    authorization_status: str = "approved"


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Optional[str] = None
    is_active: bool
    authorization_status: str = "approved"
    requested_role: Optional[str] = None
    # PU-1／PU-3：兩欄**刻意不設預設值**。三個構造點皆為手寫具名引數，帶預設值時
    # 漏傳會靜默通過（既有的 requested_role 就是這樣漏掉的）；無預設值讓漏傳在
    # 構造當下就是 ValidationError。
    last_activity_at: Optional[datetime]
    is_overdue: bool


# 每頁筆數（AD-10）：預設 20、上限 100。上限讓單次回應有界（NFR-8）。
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class UserListPage(BaseModel):
    """使用者清單的分頁回應（PU-6／AD-10）。

    四欄**皆必填、皆無預設值**：這是本 intent 的第四個回應構造點，帶預設值會讓
    「完全沒讀查詢參數的實作」也輸出四個形狀正確的 key，使驗收只能驗到 key 存在。
    """

    items: List[UserSchema]
    total: int
    page: int
    page_size: int


class MeResponse(BaseModel):
    id: int
    username: str
    role: Optional[str] = None
    is_active: bool
    authorization_status: str
    permissions: Dict[str, dict]
    pending_request: Optional[dict] = None
    # 規格 §4.1.2 要求 /me 帶出此欄位。欄位本身早已存在（models.py 的 User
    # 欄、database.py 的補欄、collab_router 的讀寫），只有這個回應模型漏掉，
    # 所以 spec-sync 把它報成漂移（#468）。可為 null：使用者尚未開過任何圖，
    # 或原圖已被刪除（外鍵為 ON DELETE SET NULL）。
    last_opened_diagram_id: Optional[int] = None


class UpdateRoleRequest(BaseModel):
    role: str


class UpdateActiveRequest(BaseModel):
    is_active: bool


class PatchAuthorizationRequest(BaseModel):
    requested_role: str


class RolePermissionRow(BaseModel):
    role: str
    story_id: str
    can_view: bool
    can_edit: bool
    can_review: bool
    updated_by: Optional[str] = None


class RolePermissionUpdate(BaseModel):
    role: str
    story_id: str
    can_view: bool
    can_edit: bool
    can_review: bool


class BulkRolePermissionUpdate(BaseModel):
    rows: List[RolePermissionUpdate] = Field(min_length=1)


class ResetDefaultsResponse(BaseModel):
    seeded: int
    message: str


class AuthorizationRequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    requested_role: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None


def _audit_append(title: str, request_raw: str, outcome: str, approver: str) -> None:
    """記錄一筆權限稽核事件到應用程式日誌。

    原本寫入某台開發機的絕對路徑（AI-DLC v1 的 `aidlc-docs/audit.md`），被
    `os.path.exists` 擋著，實際上在任何環境都不會執行。AI-DLC 的 audit 由框架
    引擎寫入 record 的 per-clone shard，不該由應用程式 runtime 寫入 —— 兩者
    是不同的稽核軌跡。此處改走標準 logger，由既有的日誌收集管線承接。
    """
    logger.info(
        "【權限稽核】%s | 請求: %s | 結果: %s | 核准者: %s",
        title,
        request_raw,
        outcome,
        approver,
    )


def _pending_request_for_user(db: Session, user_id: int) -> Optional[RoleAuthorizationRequest]:
    return (
        db.query(RoleAuthorizationRequest)
        .filter(
            RoleAuthorizationRequest.user_id == user_id,
            RoleAuthorizationRequest.status == "pending",
        )
        .order_by(RoleAuthorizationRequest.id.desc())
        .first()
    )


def _feature_label(story_id: str) -> Optional[str]:
    """將 story_id 轉成中文功能名；排除不應出現在註冊摘要的項目。"""
    if story_id in CATALOG_EXCLUDED_STORIES:
        return None
    return STORY_FEATURE_LABELS.get(story_id)


def _build_role_catalog(db: Session) -> List[dict]:
    catalog = []
    for role in CANONICAL_ROLES:
        rows = (
            db.query(RolePermission)
            .filter(RolePermission.role == role)
            .all()
        )
        features: List[str] = []
        seen_labels: set[str] = set()
        for row in rows:
            if not (row.can_view or row.can_edit or row.can_review):
                continue
            label = _feature_label(row.story_id)
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)
            features.append(label)
        catalog.append(
            {
                "role": role,
                "display_name": ROLE_DISPLAY_NAMES.get(role, role),
                "features": features,
            }
        )
    return catalog


def _serialize_auth_request(req: RoleAuthorizationRequest, username: str) -> dict:
    return {
        "id": req.id,
        "user_id": req.user_id,
        "username": username,
        "requested_role": req.requested_role,
        "status": req.status,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "decided_by": req.decided_by,
        "decided_at": req.decided_at,
    }


class DeleteUserBlockingReference(BaseModel):
    """刪除使用者被擋下時，仍指向該使用者的一類資料。"""

    category: str
    label: str
    count: int


class DeleteUserConflict(BaseModel):
    """刪除使用者的 409 回應本體（合併前必修第 3 項／OQ-H1）。

    `detail` 維持**字串**：既有前端一律以 `data.detail` 當錯誤訊息顯示
    （`AdminPage.tsx`、`AuthorizationRequestsPage.tsx`），改成物件會顯示成
    `[object Object]`。結構化清單另放 `blocking_references`。

    `blocking_references` 有預設值、在 spec 中**非必填**：拒絕授權申請端點
    既有的另一種 409（「此申請已處理」）只有 `detail`；保底路徑（預檢未涵蓋的
    外鍵，規則 3）回空清單。
    """

    detail: str
    blocking_references: List[DeleteUserBlockingReference] = Field(default_factory=list)


class _UserDeleteBlocked(Exception):
    """`_hard_delete_user` 拒絕刪除；兩個呼叫端點轉成 409 的 `JSONResponse`。"""

    def __init__(self, conflict: DeleteUserConflict) -> None:
        super().__init__(conflict.detail)
        self.conflict = conflict


_DELETE_USER_409_DOC = {
    409: {
        "model": DeleteUserConflict,
        "description": (
            "合併前必修第 3 項（OQ-H1）：刪除被拒——仍有資料指向該使用者"
            "（非空或非預設專案、其他專案的成員資格、記憶、稽核操作者紀錄等）。"
            "`blocking_references` 逐類列出筆數；預檢未涵蓋的外鍵於 commit 時"
            "被資料庫擋下時，回通用訊息與空清單。**稽核類紀錄不會被刪除**。"
            "合併前必修第 11 項：對象是系統保留帳號（90 天記憶清除的稽核操作者）"
            "時同樣回 409，`blocking_references` 為空清單。"
        ),
    }
}


def _delete_blocked_response(exc: _UserDeleteBlocked) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder(exc.conflict),
    )


class ReservedAccountConflict(BaseModel):
    """合併前必修第 11 項：對系統保留帳號的改動被拒時的 409 回應本體。

    `detail` 為字串，沿用既有前端以 `data.detail` 顯示錯誤的形狀。
    """

    detail: str


_RESERVED_ACCOUNT_409_DESCRIPTION = (
    "合併前必修第 11 項：對象是系統保留帳號（90 天記憶清除的稽核操作者），"
    "不得刪除、改角色或啟停用——刪改它會讓 90 天記憶清除整個停擺。"
)


def _reserved_account_response(*, for_delete: bool = False) -> JSONResponse:
    """保留帳號的 409。刪除類端點回 `DeleteUserConflict` 形狀以符合其既有宣告。"""
    body: BaseModel
    if for_delete:
        body = DeleteUserConflict(
            detail=RESERVED_ACCOUNT_CONFLICT_DETAIL, blocking_references=[]
        )
    else:
        body = ReservedAccountConflict(detail=RESERVED_ACCOUNT_CONFLICT_DETAIL)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder(body),
    )


def _empty_default_project_ids(db: Session, uid: int) -> List[int]:
    """OQ-H1 規則 1：可隨使用者一併清除的預設專案。

    條件四者同時成立：該使用者擁有、`is_default` 為真、其下所有 system 皆無
    架構圖（不論圖的建立者是誰）、除他本人外沒有其他成員列。
    """
    candidates = (
        db.query(Project.id)
        .filter(Project.owner_user_id == uid, Project.is_default == True)  # noqa: E712
        .all()
    )
    result: List[int] = []
    for (project_id,) in candidates:
        has_diagram = (
            db.query(UserDiagram.id)
            .join(System, UserDiagram.system_id == System.id)
            .filter(System.project_id == project_id)
            .first()
        )
        if has_diagram is not None:
            continue
        other_member = (
            db.query(ProjectMember.id)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id != uid)
            .first()
        )
        if other_member is not None:
            continue
        result.append(project_id)
    return result


def _blocking_user_references(
    db: Session, uid: int, purge_project_ids: List[int]
) -> List[DeleteUserBlockingReference]:
    """OQ-H1 規則 2：一次列舉所有仍指向該使用者、且不在規則 1 清除範圍內的參照。

    涵蓋 `schema_rbac.sql` 中**沒有** `ON DELETE` 子句、指向 `users.id` 的每一欄，
    扣除既有流程已處理的三欄（`user_diagrams.user_id` 由 403 守門、
    `diagram_shares`／`user_diagram_chats` 由本函式的呼叫端先刪）。
    新增指向 `users` 的外鍵時必須同步加進這裡；漏了會落到規則 3 的保底 409。
    """
    purge_system_ids = (
        [
            sid
            for (sid,) in db.query(System.id)
            .filter(System.project_id.in_(purge_project_ids))
            .all()
        ]
        if purge_project_ids
        else []
    )
    checks = [
        (
            "owned_projects",
            "非空或非預設的專案（擁有者）",
            db.query(Project).filter(
                Project.owner_user_id == uid, Project.id.notin_(purge_project_ids)
            ),
        ),
        (
            "project_memberships",
            "其他專案的成員資格",
            db.query(ProjectMember).filter(
                ProjectMember.user_id == uid,
                ProjectMember.project_id.notin_(purge_project_ids),
            ),
        ),
        (
            "project_member_invitations",
            "邀請他人加入專案的紀錄",
            db.query(ProjectMember).filter(
                ProjectMember.invited_by == uid,
                ProjectMember.project_id.notin_(purge_project_ids),
            ),
        ),
        (
            "reselection_events",
            "專案角色變更稽核紀錄",
            db.query(ReselectionEvent).filter(
                or_(
                    ReselectionEvent.promoted_user_id == uid,
                    ReselectionEvent.previous_owner_user_id == uid,
                )
            ),
        ),
        (
            "system_requirement_fields",
            "系統需求欄位的最後修改者紀錄",
            db.query(SystemRequirementField).filter(
                SystemRequirementField.updated_by == uid,
                SystemRequirementField.system_id.notin_(purge_system_ids),
            ),
        ),
        (
            "memory_records",
            "記憶",
            db.query(MemoryRecord).filter(MemoryRecord.owner_user_id == uid),
        ),
        (
            "memory_audit_events",
            "記憶稽核紀錄（操作者）",
            db.query(MemoryAuditEvent).filter(MemoryAuditEvent.actor_user_id == uid),
        ),
        (
            "diagram_change_records",
            "架構圖變更紀錄（操作者）",
            db.query(DiagramChangeRecord).filter(
                DiagramChangeRecord.actor_user_id == uid
            ),
        ),
        (
            "estimate_audit_events",
            "估價稽核紀錄（操作者）",
            db.query(EstimateAuditEvent).filter(EstimateAuditEvent.actor_user_id == uid),
        ),
        (
            "architecture_reviews",
            "架構審查紀錄（建立者）",
            db.query(ArchitectureReview).filter(ArchitectureReview.created_by == uid),
        ),
        (
            "wa_lenses",
            "WA Lens 修改者紀錄",
            db.query(WaLens).filter(WaLens.updated_by == uid),
        ),
    ]
    blocking: List[DeleteUserBlockingReference] = []
    for category, label, query in checks:
        count = query.count()
        if count:
            blocking.append(
                DeleteUserBlockingReference(category=category, label=label, count=count)
            )
    return blocking


def _purge_empty_default_projects(db: Session, project_ids: List[int]) -> None:
    """OQ-H1 規則 1 的清除（與刪除使用者同一交易）。

    子列以明確刪除處理，而非只依賴資料庫的 `ON DELETE CASCADE`：
    `project_members`／`system_requirement_fields` 的 CASCADE 在 PostgreSQL 生效，
    但 bulk `query.delete()` 不走 ORM cascade，而 SQLite 未開外鍵時也不會連帶刪除。
    明確刪除讓兩種方言結果一致。
    """
    if not project_ids:
        return
    system_ids = [
        sid
        for (sid,) in db.query(System.id).filter(System.project_id.in_(project_ids)).all()
    ]
    if system_ids:
        db.query(SystemRequirementField).filter(
            SystemRequirementField.system_id.in_(system_ids)
        ).delete(synchronize_session=False)
    db.query(System).filter(System.project_id.in_(project_ids)).delete(
        synchronize_session=False
    )
    db.query(ProjectMember).filter(ProjectMember.project_id.in_(project_ids)).delete(
        synchronize_session=False
    )
    db.query(Project).filter(Project.id.in_(project_ids)).delete(
        synchronize_session=False
    )


def _hard_delete_user(db: Session, user: User) -> None:
    """硬刪除使用者。被拒時 raise `_UserDeleteBlocked`（409）或既有的 403。

    OQ-H1 裁決（2026-10-20，合併前必修第 3 項）：空的預設專案一併清掉，其餘改回
    409，**不回 500**：
      1. 規則 1：空預設專案在同一交易內清除；
      2. 規則 2：預檢仍有參照即 409，回應逐類列出筆數，稽核類紀錄不刪；
      3. 規則 3：commit 時仍拋 `IntegrityError`（預檢漏列的新外鍵）→ rollback、
         記 log、回通用 409；
      4. 既有「仍擁有架構圖 → 403」維持不變。
    """
    uid = user.id
    db.query(UserDiagramChat).filter(UserDiagramChat.user_id == uid).delete(
        synchronize_session=False
    )
    db.execute(diagram_shares.delete().where(diagram_shares.c.user_id == uid))
    owned = db.query(UserDiagram).filter(UserDiagram.user_id == uid).count()
    if owned > 0:
        raise HTTPException(
            status_code=403,
            detail="無法刪除：使用者仍擁有架構圖，請先轉移或刪除圖表",
        )

    purge_project_ids = _empty_default_project_ids(db, uid)
    blocking = _blocking_user_references(db, uid, purge_project_ids)
    if blocking:
        db.rollback()
        summary = "、".join(f"{ref.label} {ref.count} 筆" for ref in blocking)
        raise _UserDeleteBlocked(
            DeleteUserConflict(
                detail=f"無法刪除：仍有資料指向此使用者——{summary}",
                blocking_references=blocking,
            )
        )

    db.query(RoleAuthorizationRequest).filter(
        RoleAuthorizationRequest.user_id == uid
    ).delete(synchronize_session=False)
    _purge_empty_default_projects(db, purge_project_ids)
    db.delete(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # 規則 3 保底：預檢沒涵蓋到的外鍵（多半是之後新增、未同步進
        # `_blocking_user_references` 的表）。不得變成 500。
        db.rollback()
        logger.error(
            "刪除使用者 id=%s 於 commit 被參照完整性拒絕（預檢未涵蓋的外鍵）：%s",
            uid,
            exc.orig,
        )
        raise _UserDeleteBlocked(
            DeleteUserConflict(
                detail="無法刪除：此使用者仍被其他資料參照，請聯絡系統管理員",
                blocking_references=[],
            )
        ) from exc


@router.get("/roles/catalog")
def roles_catalog(db: Session = Depends(get_db)):
    """公開：註冊頁角色功能目錄（動態來自 role_permissions）。"""
    ensure_role_permissions_seeded(db, force=False)
    return {"roles": _build_role_catalog(db)}


@router.post("/register", response_model=LoginResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = request.username.strip().lower()
    password = request.password
    requested_role = normalize_role(request.requested_role.strip())

    if not username or not password:
        raise HTTPException(status_code=400, detail="帳號與密碼不可為空")
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(status_code=400, detail="帳號長度必須在 3 到 20 個字元之間")
    if len(password) < 6 or len(password) > 30:
        raise HTTPException(status_code=400, detail="密碼長度必須在 6 到 30 個字元之間")
    if not re.match("^[a-zA-Z0-9_]+$", username):
        raise HTTPException(status_code=400, detail="帳號只能包含英文、數字與底線")
    if not is_canonical_role(requested_role):
        raise HTTPException(status_code=400, detail="請選擇有效的申請角色")

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="該帳號已被註冊使用")

    hashed_pw = get_password_hash(password)
    new_user = User(
        username=username,
        password_hash=hashed_pw,
        role=None,
        is_active=True,
        authorization_status="pending",
    )
    db.add(new_user)
    db.flush()
    auth_req = RoleAuthorizationRequest(
        user_id=new_user.id,
        requested_role=requested_role,
        status="pending",
    )
    db.add(auth_req)
    db.commit()
    db.refresh(new_user)

    logger.info(
        "【新帳號註冊】使用者 '%s' pending，申請角色 '%s'",
        username,
        requested_role,
    )
    _audit_append(
        "User Registration",
        f"註冊新帳號 {username} 申請 {requested_role}",
        f"使用者 {username} 註冊成功，authorization_status=pending，等待管理員核准。",
        "System_Auto",
    )

    access_token = create_access_token(data={"sub": new_user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": new_user.username,
        "role": None,
        "authorization_status": "pending",
    }


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="帳號或密碼錯誤",
    )

    user = db.query(User).filter(User.username == request.username.lower()).first()
    if not user:
        raise auth_exception
    if not verify_password(request.password, user.password_hash):
        raise auth_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的帳號已被停用，請聯絡平台管理員",
        )

    if record_activity(db, user):
        db.refresh(user)
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "authorization_status": user.authorization_status or "approved",
    }


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    status_val = current_user.authorization_status or "approved"
    pending = None
    if status_val == "pending":
        req = _pending_request_for_user(db, current_user.id)
        if req:
            pending = {
                "id": req.id,
                "requested_role": req.requested_role,
                "created_at": req.created_at,
                "updated_at": req.updated_at,
            }
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "authorization_status": status_val,
        "permissions": permissions_map_for_role(
            db, current_user.role, authorization_status=status_val
        ),
        "pending_request": pending,
        "last_opened_diagram_id": current_user.last_opened_diagram_id,
    }


@router.patch("/me/authorization-request")
def patch_my_authorization_request(
    body: PatchAuthorizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if (current_user.authorization_status or "approved") != "pending":
        raise HTTPException(400, detail="僅待授權帳號可更改申請角色")
    requested_role = normalize_role(body.requested_role.strip())
    if not is_canonical_role(requested_role):
        raise HTTPException(400, detail="請選擇有效的申請角色")
    req = _pending_request_for_user(db, current_user.id)
    if not req:
        raise HTTPException(404, detail="找不到待處理的授權申請")
    req.requested_role = requested_role
    req.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return _serialize_auth_request(req, current_user.username)


@router.get("/roles")
def list_canonical_roles(
    _: User = Depends(get_current_user),
):
    return {"roles": CANONICAL_ROLES, "stories": STORY_IDS}


def _to_user_schema(
    user: User, now: datetime, requested_role: Optional[str] = None
) -> UserSchema:
    """`UserSchema` 的單一共用工廠（C-4）。

    三個回應構造點（清單、啟停用、角色調整）一律經此函式，使它們不可能分歧。
    `is_overdue` 是**衍生值**、由後端計算（AD-2：客戶端時鐘不可信，稽核用途下
    由裝置時間決定合規標示不可接受），ORM 物件上不存在該屬性。
    """
    return UserSchema(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        authorization_status=user.authorization_status or "approved",
        requested_role=requested_role,
        # **正規化後才輸出**：資料庫可能回傳不帶時區的值（SQLite 會，PostgreSQL
        # 不會），而不帶位移的字串會被瀏覽器當成本地時間解讀 —— 顯示時間整體偏移
        # 一個時區位移量，AC-1.6 失敗且畫面看起來完全正常。回應一律為 UTC。
        last_activity_at=(
            as_aware_utc(user.last_activity_at) if user.last_activity_at else None
        ),
        is_overdue=is_overdue(user.last_activity_at, now),
    )


@router.get("/list", response_model=UserListPage)
def list_users(
    page: int = Query(1, ge=1, description="頁次，1 起算"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="每頁筆數"
    ),
    admin_user: User = Depends(require_story_action("J3a", "view")),
    db: Session = Depends(get_db),
):
    """使用者清單（分頁，PU-6）。

    `page`／`page_size` 的範圍約束以框架原生形式宣告（AD-11）：非法值在進入本
    函式**之前**就被擋下並回 422，結構上到不了查詢層；且約束會出現在 OpenAPI
    規格中，因此同時被型別契約與規格漂移 gate 覆蓋。

    頁次**合法但超出範圍**時不是錯誤：offset 超過總數，查詢自然回空清單，
    `page` 照樣回顯請求值（FR-6.4，不夾到最後一頁）。
    """
    if record_activity(db, admin_user):
        db.refresh(admin_user)
    now = datetime.now(timezone.utc)
    # 合併前必修第 11 項：系統保留帳號在**查詢層**排除，計數與分頁共用同一個
    # 基底查詢——只過濾當頁會讓 total 多 1、且某頁少一列。
    listable = db.query(User).filter(User.username.notin_(sorted(RESERVED_SYSTEM_USERNAMES)))
    # total 為獨立的計數查詢，**不得**由 len(items) 導出——後者只在多頁時才錯，
    # 而目前的資料量下多頁情境不會自然出現（BR-P2）。
    total = listable.count()
    # ORDER BY id 是「重複請求同一頁得到相同順序」的結構前提，不得移除（BR-P3）。
    users = (
        listable
        .order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for u in users:
        requested = None
        if (u.authorization_status or "approved") == "pending":
            req = _pending_request_for_user(db, u.id)
            if req:
                requested = req.requested_role
        items.append(_to_user_schema(u, now, requested_role=requested))
    return UserListPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/authorization-requests")
def list_authorization_requests(
    status_filter: Optional[str] = Query("pending", alias="status"),
    _: User = Depends(require_story_action("J3a", "view")),
    db: Session = Depends(get_db),
):
    q = db.query(RoleAuthorizationRequest, User).join(
        User, User.id == RoleAuthorizationRequest.user_id
    )
    if status_filter:
        q = q.filter(RoleAuthorizationRequest.status == status_filter)
    rows = q.order_by(RoleAuthorizationRequest.created_at.desc()).all()
    return [_serialize_auth_request(req, user.username) for req, user in rows]


@router.post(
    "/authorization-requests/{request_id}/approve",
    # 合併前必修第 11 項：顯式宣告 409（FastAPI 不從 return/raise 推導狀態碼）。
    # 既存的「此申請已處理」409 本體同為 `{"detail": str}`，與此 model 相容。
    responses={
        409: {
            "model": ReservedAccountConflict,
            "description": _RESERVED_ACCOUNT_409_DESCRIPTION
            + "另：申請已處理時亦回 409（同一形狀）。",
        }
    },
)
def approve_authorization_request(
    request_id: int,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    req = (
        db.query(RoleAuthorizationRequest)
        .filter(RoleAuthorizationRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(404, detail="找不到授權申請")
    if req.status != "pending":
        raise HTTPException(409, detail="此申請已處理，無法重複核准")

    if not admin_may_decide_role(admin_user, req.requested_role, db):
        raise HTTPException(
            status_code=403,
            detail=(
                f"權限不足：不可核准角色 {req.requested_role}"
                f"（{RESTRICTED_APPROVAL_ROLES} 僅 Platform_Admin 可核准）"
            ),
        )

    target = db.query(User).filter(User.id == req.user_id).first()
    if not target:
        raise HTTPException(404, detail="找不到申請人")
    # 合併前必修第 11 項：核准會把保留帳號改成 canonical 角色，拆掉它的第三道鎖。
    # 正常流程不會為它產生申請；此處是縱深防禦。
    if is_reserved_system_account(target):
        return _reserved_account_response()

    target.role = req.requested_role
    target.authorization_status = "approved"
    req.status = "approved"
    req.decided_by = admin_user.username
    req.decided_at = datetime.now(timezone.utc)
    db.commit()

    _audit_append(
        "Authorization Request Approved",
        f"核准 {target.username} → {req.requested_role}",
        f"管理員 {admin_user.username} 已核准授權申請 #{request_id}。",
        admin_user.username,
    )
    return {"ok": True, "username": target.username, "role": target.role}


@router.post(
    "/authorization-requests/{request_id}/reject",
    # 合併前必修第 3 項：顯式宣告 409（FastAPI 不從 raise 推導狀態碼，比照
    # `PUT /{user_id}/active`）。本端點另有既存的「此申請已處理」409，其本體只有
    # `detail`——故 `blocking_references` 在 model 中非必填。
    responses=_DELETE_USER_409_DOC,
)
def reject_authorization_request(
    request_id: int,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    req = (
        db.query(RoleAuthorizationRequest)
        .filter(RoleAuthorizationRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(404, detail="找不到授權申請")
    if req.status != "pending":
        raise HTTPException(409, detail="此申請已處理")

    if not admin_may_decide_role(admin_user, req.requested_role, db):
        raise HTTPException(403, detail=f"權限不足：不可拒絕／處理角色 {req.requested_role}")

    target = db.query(User).filter(User.id == req.user_id).first()
    if not target:
        raise HTTPException(404, detail="找不到申請人")
    # 合併前必修第 11 項：拒絕即刪除帳號——保留帳號不得經此路徑被刪。
    # 在改動申請狀態**之前**判定，故申請維持 pending、帳號不動。
    if is_reserved_system_account(target):
        return _reserved_account_response(for_delete=True)

    username = target.username
    # 先取值：`_hard_delete_user` 會刪掉這筆申請並 commit，之後再讀
    # `req.requested_role` 會觸發 refresh → ObjectDeletedError → 500
    # （合併前必修第 3 項的 (f) 案例實測抓到的既存缺陷；刪除其實已成功）。
    requested_role = req.requested_role
    req.status = "rejected"
    req.decided_by = admin_user.username
    req.decided_at = datetime.now(timezone.utc)
    db.flush()
    try:
        _hard_delete_user(db, target)
    except _UserDeleteBlocked as exc:
        # 已 rollback：申請維持 pending，帳號不動。
        return _delete_blocked_response(exc)

    _audit_append(
        "Authorization Request Rejected",
        f"拒絕並刪除 {username}（申請 {requested_role}）",
        f"管理員 {admin_user.username} 拒絕申請 #{request_id} 並刪除帳號。",
        admin_user.username,
    )
    return {"ok": True, "deleted_username": username}


@router.put(
    "/{user_id}/active",
    response_model=UserSchema,
    # U19/BR6.2：**顯式宣告 409 的 response model。** FastAPI 不從
    # `raise HTTPException` 推導狀態碼，故不宣告則此契約不會進入 openapi.json、
    # 前端也產不出型別，**而 `dump_openapi.py --check` 與 `npm run check:types`
    # 兩道漂移閘門都保持綠燈**——這是本變更唯一「違反後沒有任何東西變紅」的
    # 規則。回應本體**就是** LastAdminGuardReport（不是 {"detail": ...} 的包裝），
    # 因為 AC12.3.3 的 Then 要求列出那些專案；宣告一個 model 卻回一個包裝過的
    # 形狀，等於讓 spec 說一件回應沒有做的事。
    responses={
        409: {
            # 合併前必修第 11 項：409 有兩種本體。原有的守門報告形狀**不變**
            # （前端 MemberDetailPage 依賴它），保留帳號另回 `{"detail": str}`。
            "model": Union[LastAdminGuardReport, ReservedAccountConflict],
            "description": (
                "U19/BR6.1：停用被拒——該使用者是列出的每一個專案的"
                "**最後一位專案管理者**。回應本體即 `LastAdminGuardReport`，"
                "含每個專案的 `project_id` 與 `name`。"
                + _RESERVED_ACCOUNT_409_DESCRIPTION
                + "此情形的本體為 `ReservedAccountConflict`"
            ),
        },
        # 合併前必修第 10 項：停用之後的自動改選若有專案失敗，**不再回 200**。
        # 與上面的 409 同理必須顯式宣告，否則不進 openapi.json 而 CI 照樣綠燈。
        500: {
            "model": ReselectionFailureReport,
            "description": (
                "帳號**已停用**，但列出的專案自動改選失敗（交易已回滾，該專案此刻"
                "可能沒有可運作的管理者）。重送同一請求（`is_active=false`）即可補跑；"
                "改選冪等，已完成的專案不會重複"
            ),
        },
        # 合併前必修第 16 項：失敗**全部**是取鎖逾時時回 503，本體同上。
        503: {
            "model": ReselectionFailureReport,
            "description": (
                "帳號**已停用**，但列出的專案在取鎖時逾時（另一筆成員變更進行中）。"
                "稍後重送同一請求即可補跑"
            ),
        },
    },
)
def update_user_active(
    user_id: int,
    request: UpdateActiveRequest,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(404, detail="找不到該使用者")
    # 合併前必修第 11 項：保留帳號的 is_active 是它的第四道鎖，兩個方向都不得改
    # （重送停用也擋：那會觸發與它無關的自動改選）。
    if is_reserved_system_account(target_user):
        return _reserved_account_response()
    if target_user.id == admin_user.id and not request.is_active:
        raise HTTPException(400, detail="無法停用自己的帳號")

    # 停用最後一位 J3a.edit 管理員
    if target_user.is_active and not request.is_active:
        if user_can(
            db,
            target_user.role,
            "J3a",
            "edit",
            authorization_status=target_user.authorization_status,
        ):
            admin_edit_count = 0
            for u in db.query(User).filter(User.is_active == True).all():  # noqa: E712
                if user_can(
                    db,
                    u.role,
                    "J3a",
                    "edit",
                    authorization_status=getattr(u, "authorization_status", "approved"),
                ):
                    admin_edit_count += 1
            if admin_edit_count <= 1:
                raise HTTPException(
                    400,
                    detail="無法停用：系統必須保留至少一位可編輯使用者角色的管理員",
                )

    # U19/BR6.1：**第三道**前置檢查——per-project 的「最後一位管理者」守門。
    #
    # 三道都必須在下面那行 `target_user.is_active = request.is_active` **之前**
    # 執行；寫入之後才檢查等於沒有檢查。上面兩道（自我停用、最後一位可編輯
    # 角色的全域管理員）**照原樣保留**（BR6.3）——它們與這一道是**不同層級**：
    # 前兩者管的是全域管理員與自我，這一道管的是 per-project。
    #
    # **這個檢查是唯一防線**（契約 K-16 的 no_database_backstop）：本端點做的是
    # UPDATE，而外鍵對 UPDATE **零效力**；`projects.owner_user_id` 的 COMMENT
    # 逐字是「deletion behaviour ... deliberately NOT decided」，那是刻意留的
    # 未決項，不是既有的保護。
    #
    # 守門**唯讀、無副作用、不取鎖**（BR2.3／NFR12.3）：它是跨專案的唯讀掃描，
    # 取鎖會讓一次停用鎖住該使用者的全部專案。誠實的代價（OPEN-N19-2）：
    # 它回「通過」之後、下面寫入之前仍有一個窗口讓另一個交易改變該使用者的
    # 管理者身分；關閉它要把本端點整支納入同一個鎖範圍，而那會跨越 U19 與
    # 本模組的邊界。
    deactivating = bool(target_user.is_active and not request.is_active)
    if deactivating:
        try:
            MembershipFacade(db).assert_can_deactivate(
                mint_principal(admin_user), target_user_id=target_user.id
            )
        except LastAdminGuard as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=jsonable_encoder(guard_report(exc)),
            )

    target_user.is_active = request.is_active
    db.commit()
    db.refresh(target_user)
    payload = _to_user_schema(target_user, datetime.now(timezone.utc))

    # U19/BR4.4：自動改選的觸發條件是 `project_owner` 的**帳號被停用**，
    # 且它在停用**成功之後**才跑。次序反了會對一個其實沒被停用的帳號產生改選
    # 事件。守門先判（可能擋下整個停用，上面那一段），改選在這裡。
    #
    # **逐專案獨立交易**（scalability-design §二）：各自取鎖、各自 commit、
    # 各自釋放，故本呼叫不影響上面那次 commit，而部分失敗後重跑可收斂
    # （BR4.3 的冪等性）。
    #
    # 合併前必修第 10 項（2026-10-20 使用者裁決：回報失敗＋可重送）：
    # - 條件是 `not request.is_active` 而**不是** `deactivating`：對一個**已經**
    #   停用的帳號再送 `is_active=false`，不是 active→inactive 的轉換，故上面的
    #   守門不重跑；但改選要**重跑**，這就是「重送同一請求即可補跑」的機制。
    #   BR4.3 的冪等性使已改好的專案不產生第二筆事件。
    # - 任何專案改選失敗 → 500（全部是取鎖逾時 → 503），本體列出失敗的專案
    #   並說明帳號已停用。在此之前這裡回 200 而失敗只記 log，沒有人負責重跑，
    #   失敗的專案會永久沒有管理者。
    if not request.is_active:
        outcome = MembershipFacade(db).run_auto_reselection(
            deactivated_user_id=target_user.id
        )
        if outcome.failed_project_ids:
            all_lock_timeouts = set(outcome.failed_project_ids) == set(
                outcome.lock_timeout_project_ids
            )
            report = ReselectionFailureReport(
                detail=(
                    "帳號已停用，但下列專案的自動改選失敗，這些專案此刻可能沒有可運作的"
                    "專案管理者。請重送同一個停用請求補跑；已完成的專案不會重複改選。"
                ),
                user_id=target_user.id,
                failed_project_ids=list(outcome.failed_project_ids),
            )
            return JSONResponse(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if all_lock_timeouts
                    else status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                content=jsonable_encoder(report),
            )
    return payload


@router.delete("/{user_id}", responses=_DELETE_USER_409_DOC)
def delete_user(
    user_id: int,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(404, detail="找不到該使用者")
    # 合併前必修第 11 項：保留帳號 seed 時即為停用，原本只靠「須先停用」擋不住。
    # 刪掉它之後清除的稽核 INSERT 全部外鍵違反、整個清除交易中止。
    if is_reserved_system_account(target_user):
        return _reserved_account_response(for_delete=True)
    if target_user.id == admin_user.id:
        raise HTTPException(400, detail="無法刪除自己的帳號")
    if target_user.is_active:
        raise HTTPException(400, detail="請先停用帳號後再刪除")

    if user_can(
        db,
        target_user.role,
        "J3a",
        "edit",
        authorization_status=target_user.authorization_status,
    ):
        admin_edit_count = 0
        for u in db.query(User).filter(User.is_active == True).all():  # noqa: E712
            if user_can(
                db,
                u.role,
                "J3a",
                "edit",
                authorization_status=getattr(u, "authorization_status", "approved"),
            ):
                admin_edit_count += 1
        # target already inactive so not counted; still guard if they were last approved admin somehow
        if admin_edit_count < 1 and (target_user.authorization_status or "") == "approved":
            pass  # already inactive

    username = target_user.username
    try:
        _hard_delete_user(db, target_user)
    except _UserDeleteBlocked as exc:
        return _delete_blocked_response(exc)
    _audit_append(
        "User Deleted",
        f"刪除使用者 {username}",
        f"管理員 {admin_user.username} 已刪除帳號 {username}。",
        admin_user.username,
    )
    return {"ok": True, "deleted_username": username}


@router.put(
    "/{user_id}/role",
    response_model=UserSchema,
    # 合併前必修第 11 項：顯式宣告 409（FastAPI 不從 return 推導狀態碼）。
    responses={
        409: {
            "model": ReservedAccountConflict,
            "description": _RESERVED_ACCOUNT_409_DESCRIPTION,
        }
    },
)
def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    new_role = normalize_role(request.role.strip())
    if not is_canonical_role(new_role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無效角色：必須為 {CANONICAL_ROLES} 之一",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="找不到該使用者")
    # 合併前必修第 11 項：改成 canonical 角色會拆掉保留帳號的第三道鎖。
    if is_reserved_system_account(target_user):
        return _reserved_account_response()
    if (target_user.authorization_status or "approved") != "approved":
        raise HTTPException(
            400, detail="待授權使用者請至「授權申請」頁核准，不可直接改角色"
        )

    if target_user.role != new_role:
        had_admin_edit = user_can(db, target_user.role, "J3a", "edit")
        will_have = user_can(db, new_role, "J3a", "edit")
        if had_admin_edit and not will_have:
            admin_edit_count = 0
            for u in db.query(User).filter(User.is_active == True).all():  # noqa: E712
                if user_can(db, u.role, "J3a", "edit"):
                    admin_edit_count += 1
            if admin_edit_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="無法更新角色：系統必須保留至少一位可編輯使用者角色的管理員",
                )

    old_role = target_user.role
    target_user.role = new_role
    db.commit()
    db.refresh(target_user)

    _audit_append(
        "User Privilege Re-assignment",
        f"變更使用者 {target_user.username} 角色為 {target_user.role}",
        f"角色成功從 {old_role} 變更為 {target_user.role}，下次重新整理時生效。",
        admin_user.username,
    )
    return _to_user_schema(target_user, datetime.now(timezone.utc))


@router.get("/role-permissions", response_model=List[RolePermissionRow])
def get_role_permissions(
    _: User = Depends(require_story_action("J3b", "view")),
    db: Session = Depends(get_db),
):
    rows = list_all_permissions(db)
    return [
        RolePermissionRow(
            role=r.role,
            story_id=r.story_id,
            can_view=r.can_view,
            can_edit=r.can_edit,
            can_review=r.can_review,
            updated_by=r.updated_by,
        )
        for r in rows
    ]


@router.put("/role-permissions", response_model=List[RolePermissionRow])
def put_role_permissions(
    body: BulkRolePermissionUpdate,
    admin_user: User = Depends(require_story_action("J3b", "edit")),
    db: Session = Depends(get_db),
):
    expanded: List[RolePermissionUpdate] = []
    seen_arch_roles: set[str] = set()
    for item in body.rows:
        role = normalize_role(item.role)
        if item.story_id in ARCH_DIAGRAM_STORIES:
            if role in seen_arch_roles:
                continue
            seen_arch_roles.add(role)
            v, e, r = sync_arch_permission_flags(
                item.can_view, item.can_edit, item.can_review
            )
            for sid in ARCH_DIAGRAM_STORIES:
                expanded.append(
                    RolePermissionUpdate(
                        role=role,
                        story_id=sid,
                        can_view=v,
                        can_edit=e,
                        can_review=r,
                    )
                )
        else:
            expanded.append(item)

    updated: List[RolePermission] = []
    for item in expanded:
        role = normalize_role(item.role)
        if not is_canonical_role(role):
            raise HTTPException(400, detail=f"無效角色：{item.role}")
        if item.story_id not in STORY_IDS:
            raise HTTPException(400, detail=f"無效 story_id：{item.story_id}")

        row = (
            db.query(RolePermission)
            .filter(
                RolePermission.role == role,
                RolePermission.story_id == item.story_id,
            )
            .first()
        )
        if row is None:
            row = RolePermission(
                role=role,
                story_id=item.story_id,
                can_view=item.can_view,
                can_edit=item.can_edit,
                can_review=item.can_review,
                updated_by=admin_user.username,
            )
            db.add(row)
        else:
            row.can_view = item.can_view
            row.can_edit = item.can_edit
            row.can_review = item.can_review
            row.updated_by = admin_user.username
        updated.append(row)

    db.commit()
    for row in updated:
        db.refresh(row)

    _audit_append(
        "Role Permission Matrix Update",
        f"更新 {len(expanded)} 列 role_permissions",
        f"管理員 {admin_user.username} 已更新角色細項權限矩陣。",
        admin_user.username,
    )
    return [
        RolePermissionRow(
            role=r.role,
            story_id=r.story_id,
            can_view=r.can_view,
            can_edit=r.can_edit,
            can_review=r.can_review,
            updated_by=r.updated_by,
        )
        for r in updated
    ]


@router.post("/role-permissions/reset-defaults", response_model=ResetDefaultsResponse)
def reset_role_permissions_defaults(
    admin_user: User = Depends(require_story_action("J3b", "review")),
    db: Session = Depends(get_db),
):
    n = ensure_role_permissions_seeded(db, force=True)
    _audit_append(
        "Role Permission Matrix Reset",
        "還原 role_permissions 為設計預設",
        f"已重播 {n} 列預設矩陣。",
        admin_user.username,
    )
    return ResetDefaultsResponse(seeded=n, message=f"已還原 {n} 列預設權限")
