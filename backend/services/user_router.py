"""
user_router — 登入／註冊／使用者角色／角色權限矩陣／J5 授權申請 API
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
import logging
import re

from database import get_db
from models import User, RolePermission, RoleAuthorizationRequest, UserDiagram, UserDiagramChat
from models import diagram_shares
from services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from services.activity import as_aware_utc, is_overdue, record_activity
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
    "C1": "TCO 與流量預算",
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


def _hard_delete_user(db: Session, user: User) -> None:
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
    db.query(RoleAuthorizationRequest).filter(
        RoleAuthorizationRequest.user_id == uid
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()


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
    # total 為獨立的計數查詢，**不得**由 len(items) 導出——後者只在多頁時才錯，
    # 而目前的資料量下多頁情境不會自然出現（BR-P2）。
    total = db.query(User).count()
    # ORDER BY id 是「重複請求同一頁得到相同順序」的結構前提，不得移除（BR-P3）。
    users = (
        db.query(User)
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


@router.post("/authorization-requests/{request_id}/approve")
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


@router.post("/authorization-requests/{request_id}/reject")
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

    username = target.username
    req.status = "rejected"
    req.decided_by = admin_user.username
    req.decided_at = datetime.now(timezone.utc)
    db.flush()
    _hard_delete_user(db, target)

    _audit_append(
        "Authorization Request Rejected",
        f"拒絕並刪除 {username}（申請 {req.requested_role}）",
        f"管理員 {admin_user.username} 拒絕申請 #{request_id} 並刪除帳號。",
        admin_user.username,
    )
    return {"ok": True, "deleted_username": username}


@router.put("/{user_id}/active", response_model=UserSchema)
def update_user_active(
    user_id: int,
    request: UpdateActiveRequest,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(404, detail="找不到該使用者")
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

    target_user.is_active = request.is_active
    db.commit()
    db.refresh(target_user)
    return _to_user_schema(target_user, datetime.now(timezone.utc))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin_user: User = Depends(require_story_action("J3a", "edit")),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(404, detail="找不到該使用者")
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
    _hard_delete_user(db, target_user)
    _audit_append(
        "User Deleted",
        f"刪除使用者 {username}",
        f"管理員 {admin_user.username} 已刪除帳號 {username}。",
        admin_user.username,
    )
    return {"ok": True, "deleted_username": username}


@router.put("/{user_id}/role", response_model=UserSchema)
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
