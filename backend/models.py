"""
models.py — Cloud-360 ORM 模型

含使用者、架構圖、分享關聯、A4 聊天持久化，以及 J5 授權申請。
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

diagram_shares = Table(
    "diagram_shares",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("diagram_id", Integer, ForeignKey("user_diagrams.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    # 正式角色；pending 時為 NULL（J5）
    role = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    # pending | approved | rejected（執行期以本欄為準）
    authorization_status = Column(String(32), nullable=False, default="approved")
    last_opened_diagram_id = Column(
        Integer, ForeignKey("user_diagrams.id", ondelete="SET NULL"), nullable=True
    )
    # 最後活動時間（PU-1）：任何以有效憑證發出的請求都更新它，同一帳號至多每 5 分鐘寫一次。
    # 可為空 = 從未活動（上線前的既有帳號皆為此態，且不套用逾期標示）。
    # 刻意不設 server_default：預設值會讓「從未活動」與「剛建立」無法區分。
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    authorization_requests = relationship(
        "RoleAuthorizationRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "authorization_status": self.authorization_status,
            "last_opened_diagram_id": self.last_opened_diagram_id,
        }


class RoleAuthorizationRequest(Base):
    """J5：註冊時的角色授權申請。"""

    __tablename__ = "role_authorization_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_role = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    decided_by = Column(String(128), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="authorization_requests")


class UserDiagram(Base):
    __tablename__ = "user_diagrams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, default="未命名架構圖")
    xml_data = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("User", foreign_keys=[user_id])
    shared_users = relationship(
        "User", secondary=diagram_shares, backref="shared_diagrams"
    )


class UserDiagramChat(Base):
    """
    A4：每位使用者在每張架構圖上的獨立聊天紀錄。
    複合主鍵 (user_id, diagram_id)；messages_json 存 [{role, content}, ...]。
    """

    __tablename__ = "user_diagram_chats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    diagram_id = Column(Integer, ForeignKey("user_diagrams.id"), primary_key=True)
    messages_json = Column(Text, nullable=False, default="[]")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ArchitectureReview(Base):
    """A3：Well-Architected 評核結果（規則分數／發現＋LLM 建議）。"""

    __tablename__ = "architecture_reviews"

    id = Column(Integer, primary_key=True, index=True)
    diagram_id = Column(
        Integer,
        ForeignKey("user_diagrams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(16), nullable=False, default="aws")
    status = Column(String(32), nullable=False, default="pending")
    overall_score = Column(Integer, nullable=True)
    scores_json = Column(Text, nullable=True)
    findings_json = Column(Text, nullable=True, default="[]")
    suggestions_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    rule_pack_version = Column(String(64), nullable=True)
    xml_snapshot = Column(Text, nullable=True)
    archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WaLens(Base):
    """A3：Offline Custom Lens 現行標準（具 A3.review 者可編輯；每雲一份 active）。"""

    __tablename__ = "wa_lenses"

    id = Column(Integer, primary_key=True, index=True)
    lens_id = Column(String(64), nullable=False, default="cloud360-core-mvp", index=True)
    provider = Column(String(16), nullable=False, default="aws", index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    body_json = Column(Text, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RolePermission(Base):
    """
    RBAC：角色 × User Story 細項權限（檢視／編輯／審核）。
    預設資料見 schema_rbac.sql；可由 Admin 頁②調整。
    """

    __tablename__ = "role_permissions"

    role = Column(String(64), primary_key=True)
    story_id = Column(String(16), primary_key=True)
    can_view = Column(Boolean, nullable=False, default=False)
    can_edit = Column(Boolean, nullable=False, default=False)
    can_review = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by = Column(String(128), nullable=True)
