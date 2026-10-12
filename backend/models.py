"""
models.py — Cloud-360 ORM 模型

含使用者、架構圖、分享關聯、A4 聊天持久化，以及 J5 授權申請。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Table,
    Numeric,
    UniqueConstraint,
    CheckConstraint,
    Index,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func, text
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
    # U7/ADR-002：歸屬的權威來源（這張圖屬於哪個系統）。`user_id` 回答「誰建的」，
    # **不是**歸屬。可為空，且 DDL 已存在（`schema_rbac.sql:373`）——本單元只補上
    # ORM 映射，讓讀取端取得它；**三條建圖路徑都不傳這個參數**，故新建的圖仍留
    # NULL（具名缺口 `OPEN-H11`，本單元修不了：建圖不是本單元的路徑）。
    system_id = Column(
        Integer, ForeignKey("systems.id"), nullable=True, index=True
    )
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


# ---------------------------------------------------------------------------
# Estimate intake (U2 /api/cost/v1) — EstimateSet tree + Advice shell
# ---------------------------------------------------------------------------


class EstimateSet(Base):
    """一次上傳批次（最多三朵雲）；分享／建議／稽核的掛載根。"""

    __tablename__ = "estimate_sets"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    diagram_id = Column(Integer, nullable=True)  # 純標籤；不 FK、不參與授權
    note = Column(Text, nullable=True)
    # JSON: workload / budget / traffic context for advice agent (FR5.4).
    workload_context_json = Column(Text, nullable=True)
    # False until owner explicitly saves with a name (history drawer only shows saved).
    is_saved = Column(Boolean, nullable=False, default=False, server_default="false")

    estimates = relationship(
        "Estimate",
        back_populates="estimate_set",
        cascade="all, delete-orphan",
    )
    shares = relationship(
        "EstimateShare",
        back_populates="estimate_set",
        cascade="all, delete-orphan",
    )
    audit_events = relationship(
        "EstimateAuditEvent",
        back_populates="estimate_set",
        cascade="all, delete-orphan",
    )
    advice = relationship(
        "Advice",
        back_populates="estimate_set",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Estimate(Base):
    """批次內單一雲別的估價表彙總。"""

    __tablename__ = "estimates"
    __table_args__ = (
        UniqueConstraint("estimate_set_id", "cloud", name="uq_estimates_set_cloud"),
    )

    id = Column(Integer, primary_key=True, index=True)
    estimate_set_id = Column(
        Integer,
        ForeignKey("estimate_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cloud = Column(String(16), nullable=False)  # aws | azure | gcp
    stated_total = Column(Numeric(18, 6), nullable=True)
    currency = Column(String(16), nullable=True)
    parsed_line_count = Column(Integer, nullable=False, default=0)
    unparsed_line_count = Column(Integer, nullable=False, default=0)
    source_format = Column(String(8), nullable=False)  # csv | xlsx

    estimate_set = relationship("EstimateSet", back_populates="estimates")
    line_items = relationship(
        "EstimateLineItem",
        back_populates="estimate",
        cascade="all, delete-orphan",
        order_by="EstimateLineItem.ordinal",
    )


class EstimateLineItem(Base):
    """逐列明細（機械檢查不持久化）。"""

    __tablename__ = "estimate_line_items"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(
        Integer,
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal = Column(Integer, nullable=False)
    item_name = Column(Text, nullable=True)
    spec = Column(Text, nullable=True)
    spec_description = Column(Text, nullable=True)
    quantity = Column(Numeric(18, 6), nullable=True)
    amount = Column(Numeric(18, 6), nullable=True)
    currency = Column(String(16), nullable=True)
    parse_status = Column(String(32), nullable=False)  # parsed | unidentifiable
    raw_text = Column(Text, nullable=False)

    estimate = relationship("Estimate", back_populates="line_items")


class EstimateShare(Base):
    """批次分享關聯（擁有者＋名單）。"""

    __tablename__ = "estimate_shares"

    estimate_set_id = Column(
        Integer,
        ForeignKey("estimate_sets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    shared_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    estimate_set = relationship("EstimateSet", back_populates="shares")


class EstimateAuditEvent(Base):
    """事件層級稽核（不含金額／明細全文／檔案）。"""

    __tablename__ = "estimate_audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    estimate_set_id = Column(
        Integer,
        ForeignKey("estimate_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cloud = Column(String(16), nullable=True)
    parsed_line_count = Column(Integer, nullable=True)
    unparsed_line_count = Column(Integer, nullable=True)

    estimate_set = relationship("EstimateSet", back_populates="audit_events")


class Advice(Base):
    """建議列空殼（U7 擁有正文）；U2 觸發建立／薄讀。"""

    __tablename__ = "advice"

    estimate_set_id = Column(
        Integer,
        ForeignKey("estimate_sets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(String(32), nullable=False, default="generating")
    saving_text = Column(Text, nullable=True)
    comparison_text = Column(Text, nullable=True)
    quality_text = Column(Text, nullable=True)
    unavailable_reasons_json = Column(Text, nullable=True)  # JSON object
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    estimate_set = relationship("EstimateSet", back_populates="advice")


# ###########################################################################
# U7 hierarchy-service：projects / systems / diagram_change_records
#
# **本單元不擁有 DDL。** 權威來源是 `schema_rbac.sql:327`–`:420`（由已交付的
# `U4 hierarchy-data` 提供）；下列 model 只是對應**既有**欄位的 ORM 映射，
# 因此 `project.md` 的「schema_rbac.sql ＋ DEPLOY.md blocking 同步」規則
# **不觸發**（無新增／刪除／更名表或欄位、無索引或約束變更、無 seed 語意變更）。
#
# 為什麼需要 ORM 映射而不是在 service 層寫 raw SQL：`backend/tests/helpers.py`
# 的 in-memory SQLite 是以 `Base.metadata.create_all()` 建表的——走 raw SQL 的
# 程式在那個測試環境裡**沒有表可查**，故 ORM 是唯一能被 `TestClient` 測到的路徑。
#
# 兩份物化（ORM 欄位 vs DDL）由 `tests/test_hierarchy_service.py` 的 `T25`
# schema 對齊測試鎖住，這是 `team.md`「單一真實來源」規則的要求：
# 「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的副本不新增」。
# ###########################################################################


class Project(Base):
    """階層第一層。作業對象三層識別的最外層。"""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # U7：擁有者。被參照使用者的刪除行為**刻意未定案**（`OQ-H1`，落點本單元）
    # ——DDL 無 ON DELETE 子句。本站明寫退回並指派 `U19`（`OPEN-H12`）：
    # 擁有者消失時專案該轉給誰屬成員與接手人語意，屬契約 `K-16`。
    # **射程限定**：無 ON DELETE 等於 NO ACTION，故「會被參照完整性擋下」
    # **只對硬刪除成立**；既有停用端點（`user_router.py:682`）做的是 UPDATE，
    # 而外鍵對 UPDATE 零效力。
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    # U4/BR1.3：遷移冪等性載體。**只由 `services/hierarchy_migration.py` 寫入，
    # 不是使用者可編輯的屬性**——故本單元的建立路徑一律寫入 False（`BR2.3`）、
    # 改名路徑不得改動它（`BR4.1`）。
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # **約束必須與 DDL 逐條對齊，不只是欄位。** 理由是實測出來的：
    # `tests/helpers.py` 的 `make_session()` 先跑 `Base.metadata.create_all()`，
    # 而 `U4` 的 `_ensure_hierarchy_schema()` 用 `CREATE TABLE IF NOT EXISTS`
    # ——表已存在時它整段 no-op。所以把這三張表納入 `Base` 之後，**建表的
    # 權威就從 raw DDL 換成了這裡**；少寫一條 CHECK 就等於在測試環境裡
    # 悄悄移除它（`U4` 的 `test_change_record_source_is_a_closed_enum`
    # 在本單元第一次跑全套時就因此紅燈）。
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0", name="ck_projects_name_not_blank"
        ),
        # BR1.3 (1)：每位使用者至多一個 is_default 為真的專案。
        Index(
            "uq_projects_default_per_owner",
            "owner_user_id",
            unique=True,
            sqlite_where=text("is_default"),
            postgresql_where=text("is_default"),
        ),
    )


class System(Base):
    """階層第二層。架構圖的歸屬目標。"""

    __tablename__ = "systems"

    id = Column(Integer, primary_key=True, index=True)
    # DDL 為 ON DELETE RESTRICT——資料庫會擋下「刪除仍有系統的專案」，
    # 但錯誤訊息對使用者無意義，故服務層仍先檢查並附剩餘數量（`BR4.4`）。
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0", name="ck_systems_name_not_blank"
        ),
        # BR1.3 (2)：每個專案至多一個 is_default 為真的系統。
        Index(
            "uq_systems_default_per_project",
            "project_id",
            unique=True,
            sqlite_where=text("is_default"),
            postgresql_where=text("is_default"),
        ),
    )


class DiagramChangeRecord(Base):
    """架構圖每次被異動時留下的一列紀錄。

    **不是完整變更歷史，也不是永久稽核軌跡。** 三項減損皆為 `U4` 已交付的語意：
    ① `diagram_id` 為 ON DELETE CASCADE——圖被刪除時紀錄一併消失（`BR5.5`）；
    ② 保存期 90 天且**清除機制不在本 repo**（`OPEN-H8`）；
    ③ `source` 的允許值只有一個，故經既有 A1 頁面的異動**不會留下紀錄**
       （`BR5.3`；`U4` 註解逐字「rows here are NOT a complete change history」）。
    呈現前必須先讀 `source` 以確定涵蓋範圍（`BR6.3`／`NFR7.1`）。
    """

    __tablename__ = "diagram_change_records"

    id = Column(Integer, primary_key=True, index=True)
    diagram_id = Column(
        Integer,
        ForeignKey("user_diagrams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # U4/BR3.1：宣告本表涵蓋範圍的封閉列舉。本輪唯一合法值：brain_orchestration。
    source = Column(String(32), nullable=False)
    # U4/SEC-4：**是誰造成這次異動**。NOT NULL 是刻意的——一筆說「圖變了」
    # 卻不說「誰改的」的紀錄，在 audit-logging 面上是失敗的。
    # `BR5.6`：寫入端必須存入**實際造成異動的人**，**不得預設為 session 擁有者**。
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requirement_summary = Column(Text, nullable=False)
    requirement_label = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        # BR5.3：宣告本表涵蓋範圍的封閉列舉。本輪唯一合法值。
        CheckConstraint(
            "source IN ('brain_orchestration')",
            name="ck_diagram_change_records_source",
        ),
        # BR5.4：空摘要的紀錄對查詢端毫無價值。
        CheckConstraint(
            "length(trim(requirement_summary)) > 0",
            name="ck_diagram_change_records_summary_not_blank",
        ),
    )


# ###########################################################################
# U19 membership-service：project_members / reselection_events
#
# **本單元不擁有 DDL。** 權威來源是 `schema_rbac.sql` 的 `J)` 區塊（由已交付的
# `U18 project-meta-data` 提供）；下列 model 只是對應**既有**欄位的 ORM 映射。
# 唯一的例外是 `reselection_events.cause`——它是 `[FD3]`=A 於本單元定義、對
# `U18` 區塊的**跨單元回補**，故 `project.md` 的「schema_rbac.sql ＋ DEPLOY.md
# blocking 同步」規則**因它而觸發一次**（兩份都已同步，見 DEPLOY.md 第 2.2.9 節）。
#
# 為什麼需要 ORM 映射：本單元是這兩張表的**唯一寫入端**，而寫入走 SQLAlchemy
# ——`backend/services/*.py` 的 `db.execute(text(` 命中數為 0，raw SQL 不是本
# repo 的寫入慣例。且 `backend/tests/helpers.py` 的 in-memory SQLite 是以
# `Base.metadata.create_all()` 建表的，走 raw SQL 的程式在那個測試環境裡
# **沒有表可查**。
#
# **約束必須與 DDL 逐條對齊，不只是欄位**（`U7` 已踩過這個洞，教訓逐字寫在
# 上方 `Project.__table_args__` 的註解裡）。納入 `Base` 之後，`database.py:90`
# 的 `Base.metadata.create_all(bind=engine)` 就成為**第二條建表路徑**，於是
# 「少寫一條 CHECK」等於在測試環境裡悄悄移除它。逐條清單見
# `infrastructure-specification.md §四之二` 的十一列表；三項最容易寫錯的是
#   ① `ReselectionEvent.project_id` **不得**宣告 `ForeignKey`（`[ND1]`=A：
#      稽核須在專案被刪後存活）；
#   ② `ix_reselection_events_unack` 必須帶 `postgresql_where` ＋ `sqlite_where`
#      （partial；拿掉 WHERE 之後索引仍存在、查詢仍正確，失敗模式是效能而非
#      正確性，所以不會有人發現）；
#   ③ `previous_role`／`new_role` **不得**加 `CheckConstraint`（`U18` 刻意不加，
#      封閉列舉由應用層 `BR5.4`／`membership_types.ProjectRole` 承載）。
# 這三項加上欄位名集合由 `tests/test_membership_data.py` 的四條一致性測試鎖住。
#
# **已知限制（`OPEN-ID19-1`，不假裝已關閉）**：`create_all()` 建出來的表
# **沒有 COMMENT**，而 `verify_meta_schema.sql` 的斷言裡只有 `P12` 碰 COMMENT
# 且只驗 `system_requirement_fields`。兩條建表路徑在 COMMENT 上不等價，
# 而只有一條被驗。影響限本機（COMMENT 是給人讀的防呆機制，不影響行為）。
# ###########################################################################


class ProjectMember(Base):
    """某使用者在某專案中的成員身分與角色。per-project 授權判定的唯一資料來源。"""

    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True)
    # DDL 為 ON DELETE CASCADE，而這同時是在保護既有程式：
    # `hierarchy_service.delete_project()` 只守兩道門（預設專案、底下仍有系統），
    # **沒有任何一道關於成員**；RESTRICT 會讓 `db.delete(project)` 在 commit
    # 丟出未被捕捉的 IntegrityError（使用者看到 500 而非帶訊息的衝突回應）。
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    # **無 `ondelete`**：被參照使用者的硬刪除行為上游刻意未決（`OQ-H1`），
    # 沿用 `projects.owner_user_id` 的同一個慣例，不自行決定。
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # per-project 角色，**與全域角色同名不同義**（見 membership_types.ProjectRole
    # 的 docstring）。封閉列舉在本表由 DDL 的 CHECK 承載。
    role = Column(String(32), nullable=False)
    # **不得可為 null。** 自動改選的挑選規則（`BR4.2`）直接讀它，平手時與
    # `user_id` 組成決定性 tie-break 的鍵。可為 null 會讓挑選在空值上無序
    # ——每次選出不同人而**沒有任何錯誤**，是本表唯一完全靜默的失敗模式。
    joined_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 可為空：建立專案時自動寫入的那一列沒有邀請者。
    # **本輪有寫入端而無讀取端**（`OPEN-FD19-6`）：`invite_member` 寫它，而
    # `MemberView` 的四個欄位不含它。仍然寫入的理由是它在 `U18` 已核可的 DDL
    # 與 `entities.md` 裡；**不自行加進 `MemberView`**。
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # **刻意沒有額外索引**（兩個方向各有理由，見 `schema_rbac.sql` 的 `J)` 區塊）：
    # `project_id` 側由 `uq_project_members_project_user` 以它為前導欄覆蓋
    # （`resolve_project_role` 的最熱路徑、`list_members`、挑選過濾、CASCADE 的
    # 子側掃描全在其中）；`user_id` 側刻意不建——不需要的索引有寫入成本。
    # **不得自行補 `index=True`**，那會讓 ORM 與 DDL 的索引集合不相等。
    __table_args__ = (
        CheckConstraint(
            "role IN ('project_admin', 'member')",
            name="ck_project_members_role",
        ),
        UniqueConstraint(
            "project_id", "user_id", name="uq_project_members_project_user"
        ),
    )


class ReselectionEvent(Base):
    """一次 per-project 角色變更的稽核事件，兼橫幅已讀狀態的載體。

    **`[FD3]`=A 後涵蓋兩種來源**（`BR5.3`）：系統發起的自動改選，與管理者
    發起的人工角色變更，以 `cause` 區分、寫同一張表。同一張表的理由是
    `AC12.2.2` 的變更紀錄是**一次查詢、一個來源**，兩種來源天然按 `occurred_at`
    合併；另立一張表則需 UNION 兩表並自行排序，且兩表欄位幾乎相同而違反
    `team.md` 的「單一真實來源」。
    """

    __tablename__ = "reselection_events"

    id = Column(Integer, primary_key=True)
    # **刻意不對 `projects` 設外鍵**（`[ND1]`=A）：`FR12.4b` 存在的理由正是事後
    # 查得出某人的 `project_admin` 是怎麼來的，而 CASCADE 會把答案一起刪掉、
    # RESTRICT 會擋住專案刪除。代價明說：`project_id` **沒有參照完整性保護**，
    # 唯一寫入端是本單元的 facade（應用層保證，不是資料庫保證）。
    # 形狀與 `memory.memory_audit_events.memory_id` 一對一對照。
    project_id = Column(Integer, nullable=False)
    # `[FD3]`=A 新增的欄位，本單元是它的唯一寫入端。兩個值由 `[FD3]`=A 定案
    # （非未決事項），故**與 `previous_role`／`new_role` 不同**：這一欄有 CHECK。
    cause = Column(String(32), nullable=False)
    # 角色被改變的那個人。`cause` 為 `auto_reselection` 時即被選中者。
    promoted_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # **在兩種 `cause` 下指不同的人，而這是刻意的**（`BR5.4`）：
    #   auto_reselection   → 被停用的 owner
    #   manual_role_change → **執行變更的管理者**（`AC12.2.2` 的「誰」）
    # 兩者都回答「這次變更是誰造成的」。若覺得該拆成兩欄，先讀 `BR5.4` 的理由
    # ——拆欄會讓 `AC12.2.2` 的查詢需要依 `cause` 取不同欄位。
    previous_owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    # **刻意無 CHECK**（`U18` 的決定，逐字理由是「封閉列舉會替 `OPEN-ND18-3`
    # 先下結論」）。封閉列舉由應用層 `BR5.4` 承載。可為空——被提升者可能原本
    # 完全不是成員。
    previous_role = Column(String(32), nullable=True)
    new_role = Column(String(32), nullable=False)
    # 稽核自身的時鐘（不是被變更成員的加入時間）。**不是** purge key：本表
    # 沒有保存期限（見 `NFR12.14`）。
    occurred_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 以**事件**為鍵，不是 per-user 布林值（`BR5.6`）——後者會讓同一人第二次
    # 被改選時看不到橫幅，而那正是 `FR12.4c` 要防的情境。
    # **只對 `cause = 'auto_reselection'` 有意義**（`BR5.5`）：橫幅只為自動改選
    # 而發，`manual_role_change` 的列永遠為空，故橫幅查詢**必須同時過濾
    # `cause` 與 `acknowledged_at IS NULL`**。
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # `cause` 的兩個值由 `[FD3]`=A 定案，不是未決事項——這是它與
        # `previous_role`／`new_role`（刻意無 CHECK）的分野。
        CheckConstraint(
            "cause IN ('auto_reselection', 'manual_role_change')",
            name="ck_reselection_events_cause",
        ),
        # **partial index**：已確認的列會離開索引，故它的大小是「目前未確認的
        # 改選事件數」而非「歷來總數」。拿掉 WHERE 之後索引仍存在、查詢仍正確
        # ——失敗模式是**效能而非正確性**，所以它需要自己的斷言（DDL 側為 `P8`，
        # ORM 側為 `tests/test_membership_data.py` 的 partial 斷言）。
        # 形狀照既有先例 `uq_projects_default_per_owner`（兩個 dialect 都要寫）。
        Index(
            "ix_reselection_events_unack",
            "promoted_user_id",
            sqlite_where=text("acknowledged_at IS NULL"),
            postgresql_where=text("acknowledged_at IS NULL"),
        ),
        # 成員詳情頁的變更紀錄讀取端。本表無外鍵，所以這個索引不會被 FK
        # 順手帶出來。
        Index("ix_reselection_events_project_id", "project_id"),
    )


# ###########################################################################
# U20 requirement-field-service：system_requirement_fields
#
# **DDL 的權威來源仍是 `schema_rbac.sql` 的 `J)` 區塊**（表由 `U18` 交付；本單元
# 只把 `updated_on_behalf_of` 改為 agent 組識別字，`BR47.1`）。本 model 是對應它的
# ORM 映射（`BR47.4`），由 `tests/test_requirement_field_data.py` 鎖住兩者一致。
#
# 約束必須與 DDL 逐條對齊（`U7`／`U19` 已踩過的洞，見上方兩個區塊的註解）：
#   ① 三欄唯一鍵 `uq_system_requirement_fields_group_key`——它同時是 upsert
#      （`ON CONFLICT`）的衝突目標，SQLite 在缺它時會以「ON CONFLICT clause does
#      not match any PRIMARY KEY or UNIQUE constraint」失敗；
#   ② `ck_system_requirement_fields_cleared_has_null_value`——三態模型的第三態；
#   ③ `updated_on_behalf_of` 為 `String(64)` 且**不得**宣告 `ForeignKey`（`[FD1]`=A）；
#   ④ **不得**補 `index=True`：DDL 刻意沒有額外索引（唯一鍵以 `system_id` 為前導欄）。
#
# **刻意不掛 `before_create` 守門**（沿用 `U19` 對兄弟表的先例 `OPEN-ID19-1`）：
# 記憶表的守門擋的是「ORM 缺欄位、建出的表永久壞掉」，而本 model 與 DDL 欄位
# 完全等價；掛上它反而會讓後端在一個未跑遷移的既有資料庫上**整個起不來**
# （`database.py` 的 `create_all` 走訪整個 `Base.metadata`）。代價如實記下：
# 表不存在時，後端啟動的 `create_all` 會建出一張功能等價、**只缺 COMMENT** 的表；
# 之後執行 `run_meta_schema_migration.py`，`J)` 區塊的 `COMMENT ON` 會補上。
# ###########################################################################


class SystemRequirementField(Base):
    """某個系統的某個需求欄位的值與其溯源（`ADR-015` 的三態模型）。

    三態以列的有無與欄位組合表達：從未填過＝無列；已填＝`value` 非 null；
    已清空＝`value` 為 null 且 `cleared_at` 有值。欄位**定義**不在資料庫，
    在 `services/requirement_field_definitions.py`。
    """

    __tablename__ = "system_requirement_fields"

    id = Column(Integer, primary_key=True)
    # DDL 為 ON DELETE CASCADE：系統被刪後其需求欄位值失去意義（`[ND1]`=A）。
    # SQLite 測試庫未開 PRAGMA foreign_keys，故這條級聯只在 CI 的真實
    # PostgreSQL 上驗證（`memory-schema` job 的步驟 E）。
    system_id = Column(
        Integer,
        ForeignKey("systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_group = Column(String(64), nullable=False)
    field_key = Column(String(64), nullable=False)
    # 可為 null 是設計（`ADR-015`）：它讓「從未填過」與「已清空」可區分。
    value = Column(Text, nullable=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 實際發起者；由大腦代寫時仍是使用者本人（`BR45.1`）。
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    # `[FD1]`=A：agent 組識別字，**刻意沒有外鍵**。null＝使用者自己填的。
    updated_on_behalf_of = Column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "system_id",
            "agent_group",
            "field_key",
            name="uq_system_requirement_fields_group_key",
        ),
        CheckConstraint(
            "cleared_at IS NULL OR value IS NULL",
            name="ck_system_requirement_fields_cleared_has_null_value",
        ),
    )


# ###########################################################################
# U8 memory-service：memory.memory_records / memory.memory_audit_events
#
# **本單元不擁有 DDL。** 權威來源是 `schema_rbac.sql` 的 `I)` 區塊（由已交付的
# `U5 memory-data` 提供）；下列兩個 model 只是對應**既有**欄位的 ORM 映射，
# 本單元**不新增、不更名、不改型任何欄位**。
#
# 為什麼需要 ORM 映射（`code-generation-plan.md §1.1` 的實測）：`backend/models.py`
# 原本**零** Memory 模型，而 `backend/tests/helpers.py:50` 的
# `Base.metadata.create_all(bind=engine)` **只建有 ORM 模型的表**。沒有模型
# ⇒ in-memory SQLite 裡沒有那兩張表 ⇒ 連授權測試都跑不起來。
# 補模型使 `infrastructure-design/cicd-pipeline.md §三` 那句「授權判定、過濾、
# 交易邊界在 SQLite 上的語意與 PostgreSQL 一致」由「有條件成立」變成「成立」。
#
# ---------------------------------------------------------------------------
# **`embedding` 刻意不在 ORM 內**，而這是 `NFR8.20` 逼出來的
# ---------------------------------------------------------------------------
# `memory_records.embedding` 的型別是 pgvector 的 `vector(1024)`。在 SQLAlchemy
# 宣告它需要 `pgvector` Python 套件，而 `NFR8.20` 的第一項判準逐字是
# 「`backend/requirements.txt` 的 diff 為空」。故 ORM 是**八欄的部分鏡像**。
#
# 可接受的理由：**向量路徑本來就走原生 SQL**（`memory_service.SEARCH_SQL`）
# ——pgvector 的距離運算子在沒有該套件的情況下無法以 SQLAlchemy 表達式寫出。
# ORM 只服務非向量路徑（列出、刪除、放寬、稽核查詢）。
#
# 一致性測試因此斷言的是 **ORM 欄位集合 ∪ {embedding} ＝ SQL 欄位集合**，
# 而不是「兩者相等」。省略是刻意的、可機械判定的，不是漂移
# （`tests/test_memory_contract.py` 的 `C4`）。
#
# ---------------------------------------------------------------------------
# **約束必須與 DDL 逐條對齊，不只是欄位**
# ---------------------------------------------------------------------------
# 這是 `U7` 已踩過、`U19` 逐字記下的洞（見上方 `U19` 區塊的註解）：納入 `Base`
# 之後 `create_all` 就是**第二條建表路徑**，於是「少寫一條 CHECK」等於在測試
# 環境裡悄悄移除它。
#
# **故本區塊鏡像 `I)` 區塊的全部四條具名 CHECK 與四個索引**，由
# `tests/test_memory_contract.py` 的 `C4` 以**集合相等**鎖住。
# `code-generation-plan.md` Step 2.4 寫的是「不加 CheckConstraint」，而那條
# 與本 repo 的既有標準相反——`U18` 真正刻意不加 CHECK 的是
# `reselection_events.previous_role`／`new_role`（DDL 側**也**沒有），
# 而 `project_members.role` 的 `ck_project_members_role` 在 DDL 與 ORM **都有**。
# 判準是「DDL 有沒有」，不是「封閉集合由誰承載」：`visibility_scope` 的封閉集合
# 在 DDL 確實沒有約束（`FD8-3`），由 `memory_types.VISIBILITY_SCOPES` 承載；
# `kind` 與 `action` 的 DDL 有，故 ORM 必須有。
#
# **唯一無法鏡像的索引是 HNSW 那一個**（`ix_memory_records_embedding_hnsw`）：
# 它建在 `embedding` 上，而該欄不在 ORM 內。與 `embedding` 同一個根因、
# 同樣由 `C4` 以「∪ 已知刻意省略」的形式斷言。
# ###########################################################################


@event.listens_for(Engine, "connect")
def _attach_memory_schema_for_sqlite(dbapi_connection, connection_record):
    """SQLite 相容層：為 `schema="memory"` 的兩張表準備一個名為 `memory` 的庫。

    **這是上面那個 `schema="memory"` 宣告的直接後果，不是測試專用的 hack。**
    SQLite 沒有 schema 概念，它把 `memory.memory_records` 讀成「名為 `memory`
    的**已附加資料庫**裡的 `memory_records`」。沒有這個 ATTACH，
    `Base.metadata.create_all()` 會以 `unknown database memory` 失敗——而
    `create_all` 走訪的是**整個** `Base.metadata`，故受害的不只是本單元的測試，
    是 `backend/tests/` 的**每一個**測試檔（實測：21 個檔全數 error）。

    放在 `models.py` 而不是 `tests/helpers.py` 的理由有兩個：
      ① `helpers.py` 的既有語意不得被改動（`code-generation-plan.md` Step 2.2）；
      ② 本 shim 必須在**任何** engine 連線之前就位，而 `models.py` 的 import
         必然早於 `create_all`。放在呼叫端會讓每個呼叫端各記得一次。

    **對 PostgreSQL 是無作用的**（以 dialect 名稱守門）。ATTACH 的是
    `':memory:'`，故它與 in-memory 測試庫同生共死，不落地任何檔案。

    `StaticPool` 之下每個 engine 只連一次，故這裡每個測試 engine 執行一次。
    """
    # `Engine` 層級的 listener 會對行程內**全部** engine 觸發，含生產的
    # PostgreSQL engine——故守門是必要的，不是防衛性冗語。
    #
    # 以 dbapi 連線的型別判斷，而**不是** `connection_record.engine`：
    # 後者不存在（實測 `AttributeError: '_ConnectionRecord' object has no
    # attribute 'engine'`），而 `connection_record.__pool._dialect` 是私有屬性。
    # `sqlite3` 是標準庫，import 它不新增依賴（`NFR8.20`）。
    import sqlite3

    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("ATTACH DATABASE ':memory:' AS memory")
    except Exception:  # pragma: no cover - 同一連線重複 ATTACH 時才會到這裡
        # 已附加過即視為就緒。靜默在此是正確的：失敗的後果會立刻由
        # `create_all()` 以 `unknown database memory` 大聲表現出來，
        # 而不是被這個 except 吞掉。
        pass
    finally:
        cursor.close()


def _refuse_orm_as_ddl_source(target, connection, **kw):
    """在 PostgreSQL 上拒絕由 `create_all()` 建立記憶表（`NFR8.20` 的連帶防護）。

    **這個 listener 只在危險的那個情境觸發，正常路徑上是不存在的成本。**
    `create_all(checkfirst=True)`（`database.py:90` 的用法）先過濾掉已存在的表，
    故本 listener 在表已存在時**不會**被呼叫。

    它要擋的是一個**靜默且不可逆**的情境：若某個 PostgreSQL 庫有 `memory`
    schema 但沒有那兩張表（部分套用、手動建 schema），`create_all` 會照著
    ORM 建出一張**缺少 `embedding` 欄位**的 `memory_records`——而之後再跑
    `schema_rbac.sql` 也補不回來，因為 `CREATE TABLE IF NOT EXISTS` 整段 no-op。
    結果是向量檢索永久失效，且沒有任何錯誤訊息。

    `U19` 的 `OPEN-ID19-1` 記載過同形問題的較輕版本（`create_all` 建出來的表
    沒有 COMMENT）。本單元的版本嚴重得多，因為少的是一個**欄位**，
    所以這裡選擇大聲失敗而不是如實記載後放行。

    SQLite **不**在守門範圍內：在那裡 `create_all` 正是我們要的建表路徑
    （`code-generation-plan.md §1.1`）。
    """
    if connection.dialect.name != "postgresql":
        return
    raise RuntimeError(
        f"拒絕以 create_all() 建立 {target.schema}.{target.name}：記憶表的權威"
        " DDL 是 schema_rbac.sql 的 I) 區塊，而 ORM 刻意省略 embedding 欄位"
        "（NFR8.20：requirements.txt 的 diff 必須為空）。由 ORM 建表會產生一張"
        "缺少 embedding 的表，且之後重跑 schema_rbac.sql 也補不回來"
        "（CREATE TABLE IF NOT EXISTS 會整段 no-op），使向量檢索永久失效而"
        "無任何錯誤。處置：先套用 schema_rbac.sql，或執行"
        " backend/scripts/run_meta_schema_migration.py（它解析並執行 I) 區塊）。"
    )


class MemoryRecord(Base):
    """一則記憶。三種 `kind` 共用同一個實體與同一組授權欄位（`entities.md`）。

    **八欄的部分鏡像**：`embedding` 刻意不在此（見上方區塊註解）。
    """

    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True)
    # `kind` 是**屬性而非型別分支**：三者在同一張表，差別只在保存期與寫入端。
    kind = Column(String(16), nullable=False)
    # **寫入端強制**（`BR1.1`／`BR1.2`）：值一律取自呼叫者的已驗證身分，
    # 不來自任何請求酬載欄位。DDL 的 `REFERENCES public.users (id)` 在此以
    # `ForeignKey("users.id")` 表達——`users` 在預設 schema，故不加前綴。
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # **封閉集合在 DDL 側沒有任何約束**（`FD8-3`），故 ORM 側也不加 CHECK
    # ——判準是「DDL 有沒有」。唯一的防線是 `memory_types.VISIBILITY_SCOPES`，
    # 漏驗的後果是髒資料而非寫入失敗，而髒資料會讓 `BR5.2` 的方向性
    # （`owner` < `platform`）在那一列上失去依據。
    visibility_scope = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    # 即使 `embedding` 為 NULL 本欄仍必填（`entities.md` 逐字）。
    # **相似度檢索必須以它分群**（`BR3.2`）：同維度不等於同向量空間，
    # 少了那道過濾會回垃圾**且不報錯**——本單元唯一完全靜默的失敗模式。
    embedding_model = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 僅 `episodic` 必填（`EC1`）。清除作業**依本欄選列**，故一列 `expires_at`
    # 為空的 `episodic` 永遠不會被選中——漏填是永久保留且無跡象。
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # 以下三條逐字鏡像 `schema_rbac.sql` 的 `I)` 區塊。少寫一條等於在
        # SQLite 測試環境裡悄悄移除它（`U7` 已踩過這個洞）。
        CheckConstraint(
            "kind IN ('semantic', 'procedure', 'episodic')",
            name="ck_memory_records_kind",
        ),
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_memory_records_content_not_blank",
        ),
        CheckConstraint(
            "kind <> 'episodic' OR expires_at IS NOT NULL",
            name="ck_memory_records_episodic_has_expiry",
        ),
        # 三個可鏡像的索引。**第四個（HNSW）無法鏡像**——它建在 `embedding` 上。
        Index("ix_memory_records_owner_user_id", "owner_user_id"),
        Index("ix_memory_records_expires_at", "expires_at"),
        Index("ix_memory_records_embedding_model", "embedding_model"),
        {"schema": "memory"},
    )


class MemoryAuditEvent(Base):
    """對一則記憶做過什麼的紀錄。**七欄的完整鏡像**（無省略）。

    設計核心是**兩個刻意的缺席**（`entities.md`）：沒有指向記憶的外鍵，
    以及沒有記憶內容。
    """

    __tablename__ = "memory_audit_events"

    id = Column(Integer, primary_key=True)
    # **刻意不對 `memory_records` 設外鍵**（`BR2.1`／`DG-1`）：稽核必須比它描述
    # 的記憶活得久。有外鍵則兩個選項都會違反一條已核可需求——CASCADE 讓
    # `FR4.7`（刪除留稽核）在 90 天後變成空話，RESTRICT 讓 `FR4.5`（自動逾期）
    # 不可能。代價明寫：`memory_id` **沒有參照完整性**，唯一寫入端是 `K-08`
    # 的 facade（應用層保證，不是資料庫保證）。
    # 形狀與 `reselection_events.project_id` 一對一對照。
    memory_id = Column(Integer, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(32), nullable=False)
    # `scope_changed` 時兩者皆必填且彼此不同（`EC4`）；其餘為空（`EC5`）。
    # **DDL 側無約束**，故 ORM 側亦無——由 `BR5.3`／`BR5.4` 在應用層承載。
    previous_scope = Column(String(32), nullable=True)
    new_scope = Column(String(32), nullable=True)
    # **稽核自身的保存期鍵**（90 天，`NFR7.2`），不是它所描述記憶的時間。
    # 兩者是各自獨立的時鐘。
    occurred_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ('deleted_by_user', 'purged_by_retention', 'scope_changed')",
            name="ck_memory_audit_events_action",
        ),
        Index("ix_memory_audit_events_occurred_at", "occurred_at"),
        Index("ix_memory_audit_events_memory_id", "memory_id"),
        {"schema": "memory"},
    )


# 兩張記憶表各掛一次「不得由 ORM 建表」的守門（見該函式的 docstring）。
event.listen(MemoryRecord.__table__, "before_create", _refuse_orm_as_ddl_source)
event.listen(MemoryAuditEvent.__table__, "before_create", _refuse_orm_as_ddl_source)
