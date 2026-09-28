"""
RBAC：依 role_permissions 檢查 story × action（view / edit / review）。
執行期以 DB 為準；預設矩陣見 rbac_seed_data / schema_rbac.sql。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import RolePermission, User
from services.auth import get_current_user
from services.rbac_seed_data import DEFAULT_ROLE_PERMISSIONS

logger = logging.getLogger("cloud360.rbac")

Action = Literal["view", "edit", "review"]

CANONICAL_ROLES: List[str] = [
    "Project_Architect",
    "Developer",
    "Project_Editor",
    "Project_Admin",
    "FinOps_Analyst",
    "SRE",
    "Ops_Lead",
    "Platform_Engineer",
    "Security_Reviewer",
    "Platform_Admin",
    "Platform_Owner",
]

STORY_IDS: List[str] = sorted({row[1] for row in DEFAULT_ROLE_PERMISSIONS})

# 架構圖生成：A1／A2／A4 視為同一功能（權限以 A1 為準，寫入時三者同步）
ARCH_DIAGRAM_STORIES: tuple[str, ...] = ("A1", "A2", "A4")
ARCH_CANONICAL_STORY = "A1"

# Stories 文件別名 → 正式 handle
ROLE_ALIASES = {
    "Security_Admin": "Security_Reviewer",
    "Engineering_Manager": "Project_Editor",
}


def normalize_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


def is_canonical_role(role: str) -> bool:
    return normalize_role(role) in CANONICAL_ROLES


def ensure_role_permissions_seeded(db: Session, force: bool = False) -> int:
    """
    若 role_permissions 為空（或 force=True）則寫入設計預設矩陣。
    回傳寫入列數。
    """
    count = db.query(RolePermission).count()
    if count > 0 and not force:
        return 0
    if force:
        db.query(RolePermission).delete()
    for role, story_id, can_view, can_edit, can_review in DEFAULT_ROLE_PERMISSIONS:
        db.add(
            RolePermission(
                role=role,
                story_id=story_id,
                can_view=can_view,
                can_edit=can_edit,
                can_review=can_review,
                updated_by="system_seed",
            )
        )
    db.commit()
    logger.info("已 seed role_permissions：%d 列", len(DEFAULT_ROLE_PERMISSIONS))
    return len(DEFAULT_ROLE_PERMISSIONS)


def ensure_missing_role_permissions(db: Session) -> int:
    """
    只 INSERT 缺失的 (role, story_id)；不 UPDATE／DELETE 既有列（ADR-C1-02）。
    """
    inserted = 0
    for role, story_id, can_view, can_edit, can_review in DEFAULT_ROLE_PERMISSIONS:
        exists = (
            db.query(RolePermission)
            .filter(RolePermission.role == role, RolePermission.story_id == story_id)
            .first()
        )
        if exists:
            continue
        db.add(
            RolePermission(
                role=role,
                story_id=story_id,
                can_view=can_view,
                can_edit=can_edit,
                can_review=can_review,
                updated_by="system_seed",
            )
        )
        inserted += 1
    if inserted:
        db.commit()
        logger.info("ensure_missing_role_permissions: inserted %d rows", inserted)
    return inserted


def get_permission_row(
    db: Session, role: str, story_id: str
) -> Optional[RolePermission]:
    role = normalize_role(role)
    return (
        db.query(RolePermission)
        .filter(RolePermission.role == role, RolePermission.story_id == story_id)
        .first()
    )


def user_is_approved(user: Optional[User] = None, authorization_status: Optional[str] = None) -> bool:
    """J5：僅 approved 帳號可擁有業務權限。"""
    status = authorization_status
    if user is not None:
        status = getattr(user, "authorization_status", None) or status
    return (status or "approved") == "approved"


def user_can(
    db: Session,
    role: Optional[str],
    story_id: str,
    action: Action,
    *,
    authorization_status: Optional[str] = None,
) -> bool:
    # J5：未核准一律無權限
    if authorization_status is not None and authorization_status != "approved":
        return False
    if not role or not is_canonical_role(role):
        return False
    # 架構圖三 story 統一讀 A1
    if story_id in ARCH_DIAGRAM_STORIES:
        story_id = ARCH_CANONICAL_STORY
    row = get_permission_row(db, role, story_id)
    if row is None:
        return False
    if action == "view":
        return bool(row.can_view or row.can_edit or row.can_review)
    if action == "edit":
        return bool(row.can_edit)
    if action == "review":
        return bool(row.can_review)
    return False


def user_can_arch(
    db: Session,
    role: Optional[str],
    action: Action,
    *,
    authorization_status: Optional[str] = None,
) -> bool:
    """架構圖生成（A1／A2／A4）權限檢查。"""
    return user_can(
        db, role, ARCH_CANONICAL_STORY, action, authorization_status=authorization_status
    )


def sync_arch_permission_flags(
    can_view: bool, can_edit: bool, can_review: bool
) -> tuple[bool, bool, bool]:
    """
    架構圖語意正規化：
    - 編輯：可做除審核外一切（檢視自動開啟；審核旗標可獨立）
    - 審核：可檢視＋審核，不可編輯（若同時勾編輯則保留編輯）
    - 僅檢視：可看被分享的圖，不可編輯／AI
    """
    if can_edit or can_review:
        can_view = True
    return can_view, can_edit, can_review


def require_arch_action(action: Action):
    """要求架構圖生成（A1／A2／A4）具備指定 action。"""

    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        status_val = getattr(current_user, "authorization_status", "approved")
        if status_val != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="帳號尚未通過管理員授權，無法使用業務功能",
            )
        if not user_can_arch(
            db, current_user.role, action, authorization_status=status_val
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"權限不足：需要架構圖生成.{action}，"
                    f"目前角色為 {current_user.role}"
                ),
            )
        return current_user

    return _dep


def permissions_map_for_role(
    db: Session,
    role: Optional[str],
    *,
    authorization_status: Optional[str] = None,
) -> Dict[str, dict]:
    """回傳 { story_id: {view, edit, review} }。A2／A4 與 A1 對齊。"""
    if authorization_status is not None and authorization_status != "approved":
        return {}
    if not role or not is_canonical_role(role):
        return {}
    role = normalize_role(role)
    rows = db.query(RolePermission).filter(RolePermission.role == role).all()
    result: Dict[str, dict] = {}
    for row in rows:
        result[row.story_id] = {
            "view": bool(row.can_view or row.can_edit or row.can_review),
            "edit": bool(row.can_edit),
            "review": bool(row.can_review),
            "can_view": bool(row.can_view),
            "can_edit": bool(row.can_edit),
            "can_review": bool(row.can_review),
        }
    # 強制 A2／A4 顯示與 A1 一致（執行期以 A1 為準）
    if ARCH_CANONICAL_STORY in result:
        for sid in ARCH_DIAGRAM_STORIES:
            if sid != ARCH_CANONICAL_STORY:
                result[sid] = dict(result[ARCH_CANONICAL_STORY])
    return result


def list_all_permissions(db: Session) -> List[RolePermission]:
    return (
        db.query(RolePermission)
        .order_by(RolePermission.role, RolePermission.story_id)
        .all()
    )


def require_story_action(story_id: str, action: Action):
    """FastAPI Depends：要求目前使用者對 story 具有指定 action。"""

    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        status_val = getattr(current_user, "authorization_status", "approved")
        if status_val != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="帳號尚未通過管理員授權，無法使用業務功能",
            )
        if not user_can(
            db, current_user.role, story_id, action, authorization_status=status_val
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"權限不足：需要 {story_id}.{action}，"
                    f"目前角色為 {current_user.role}"
                ),
            )
        return current_user

    return _dep


# 申請 Plat/Owner 僅 Platform_Admin 可核准
RESTRICTED_APPROVAL_ROLES = frozenset({"Platform_Admin", "Platform_Owner"})


def admin_may_decide_role(admin: User, requested_role: str, db: Session) -> bool:
    """BR-04：Platform_Admin 可核准全部；Project_Admin 不可核准 Plat/Owner。"""
    if not user_can(
        db,
        admin.role,
        "J3a",
        "edit",
        authorization_status=getattr(admin, "authorization_status", "approved"),
    ):
        return False
    req = normalize_role(requested_role)
    if admin.role == "Platform_Admin":
        return True
    if req in RESTRICTED_APPROVAL_ROLES:
        return False
    return admin.role == "Project_Admin"
