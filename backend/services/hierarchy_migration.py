"""U4 `hierarchy-data`：專案／系統階層的結構與一次性資料遷移。

契約（下游依賴，請勿變更）
--------------------------

**公開介面只有一個**：`migrate_hierarchy(db) -> MigrationCounts`。
本模組刻意**不**提供任何 router、任何供他人呼叫的讀寫函式、任何 HTTP 或外部
連線（`SEC-1`／`SEC-3`）。`projects`／`systems` 的執行期存取一律經 `K-07` 的
facade（`U7`）；本模組不開第二條路。除了上述入口，其餘皆為底線前綴的私有
輔助函式，只由本模組與其測試使用。

**執行位置**：部署期的獨立指令（`Q2=A`），入口腳本為
`backend/scripts/run_hierarchy_migration.py`。**不掛在啟動路徑上**——
`main.py` 不匯入本模組，`init_db()` 不呼叫它。

**它做什麼**（`WF-1`，順序不可調換）：

1. 建立 `projects`／`systems`／`diagram_change_records` 三表（可重跑安全）
2. 為 `user_diagrams` 增加 `system_id` 欄位（可為空）
3. 建立 `BR1.3` 的兩個部分唯一索引（**必須在步 4 之前**：約束先存在，
   遷移才受它保護；反過來的話，步 4 中途失敗後的重跑會先建出重複資料，
   約束就再也建不起來）
4. 逐使用者：取得或建立其預設專案與預設系統，把其 `system_id` 為空的圖掛入
5. `BR1.1`／`BR1.2` 的刪除約束（以 FK 的 `ON DELETE RESTRICT` 承載，
   與步 1／2 同時建立——它們是欄位定義的一部分，無法延後）
6. 終檢：`system_id IS NULL` 的列數必須為 0，**不為 0 即 raise**

**交易邊界是逐使用者一個交易**（`S-8`）：某位使用者的專案／系統建立與其圖的
改寫在同一個交易內，要麼全成要麼全不成；跨使用者可留下部分進度，由重跑補完。
「部分使用者已遷移」是**合法且可恢復**的狀態（見 `DEPLOY.md` 2.2.7）。

**失敗形式**（`BR2.1`／`AC9.1.4`／`U4-V4`）：終檢不為 0 時 **raise**
`HierarchyMigrationError`，**不是** `logger.warning`。唯一約束的拒絕**往外拋**，
不被 `except` 吞掉。本檔刻意**不**沿用 `backend/database.py` 的 `_ensure_*`
形狀——那六支逐句 `except Exception: logger.warning`，而 `stories.md:426` 逐字
要求本單元「直接否掉照抄既有 logger.warning 形狀的實作」。

**DDL 存在兩處**：本檔與 repo 根的 `schema_rbac.sql`。這不是冗餘而是必要——
`schema_rbac.sql` 只在**空 data volume** 執行（兩份 compose 把它掛進
`/docker-entrypoint-initdb.d/`），既有環境永遠不會經過它。兩處的一致性由
`backend/tests/test_hierarchy_migration.py` 的
`test_schema_rbac_sql_matches_migration_ddl` 鎖住；改一處必須改另一處。

**遷移不改變任何既有欄位**（`BR2.3`／`AC9.1.3`）：`system_id` 的寫入走
`sqlalchemy.text()` 的 UPDATE，**刻意不走 ORM**——`models.UserDiagram.updated_at`
帶 `onupdate=func.now()`，經 ORM 更新會連帶改寫 `updated_at`，那就違反 BR2.3。
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import Session

logger = logging.getLogger("cloud360.hierarchy_migration")

# `DiagramChangeRecord.source` 本輪唯一合法值（BR3.1）。寫入端是 U12，不是本模組；
# 在此定義是為了讓 CHECK 約束與未來的寫入端共用同一個字面值。
CHANGE_RECORD_SOURCE_BRAIN = "brain_orchestration"


# ---------------------------------------------------------------------------
# 結構定義（`WF-1` 步 1–3、5 的承載）
# ---------------------------------------------------------------------------
# 獨立的 MetaData，**不掛在 models.Base 上**。理由有兩個：
#   (1) 掛上去會讓 init_db() 的 create_all() 在啟動時建這三張表，而 Q2=A 明訂
#       遷移只走部署期的獨立指令、不上啟動路徑；
#   (2) 掛上去也會讓「本模組被匯入」成為 Base.metadata 內容的隱性前提，
#       而那是一個依匯入順序而變的全域副作用。
# `users` 與 `user_diagrams` 只以「參照用殘根」形式登記，讓 FK 能解析目標；
# 它們**永不**被傳進 create_all()，所以不會被本模組建立或修改。
_METADATA = MetaData()

Table("users", _METADATA, Column("id", Integer, primary_key=True))
Table("user_diagrams", _METADATA, Column("id", Integer, primary_key=True))

_PROJECTS = Table(
    "projects",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("owner_user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("is_default", Boolean, nullable=False, server_default=text("FALSE")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("length(trim(name)) > 0", name="ck_projects_name_not_blank"),
)

Index("ix_projects_owner_user_id", _PROJECTS.c.owner_user_id)

# BR1.3 (1)：範圍只引用本表欄位。唯一性約束無法以另一張表 join 來的值為範圍，
# 所以 systems 那一層只能以 project_id 為範圍（見下），不是以擁有者。
Index(
    "uq_projects_default_per_owner",
    _PROJECTS.c.owner_user_id,
    unique=True,
    postgresql_where=text("is_default"),
    sqlite_where=text("is_default"),
)

_SYSTEMS = Table(
    "systems",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column(
        "project_id",
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("name", String(255), nullable=False),
    Column("is_default", Boolean, nullable=False, server_default=text("FALSE")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("length(trim(name)) > 0", name="ck_systems_name_not_blank"),
)

Index("ix_systems_project_id", _SYSTEMS.c.project_id)

# BR1.3 (2)：範圍為 project_id。「每位使用者至多一組預設專案／系統」是兩層的
# **遞移**結果，且另需「預設 System 總是建在該使用者的預設 Project 底下」——
# 那一點**沒有任何約束擋住**，由本模組 `_resolve_default_pair()` 的順序供應。
Index(
    "uq_systems_default_per_project",
    _SYSTEMS.c.project_id,
    unique=True,
    postgresql_where=text("is_default"),
    sqlite_where=text("is_default"),
)

_DIAGRAM_CHANGE_RECORDS = Table(
    "diagram_change_records",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column(
        "diagram_id",
        Integer,
        ForeignKey("user_diagrams.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("source", String(32), nullable=False),
    Column("actor_user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("requirement_summary", Text, nullable=False),
    Column("requirement_label", String(255), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint(
        f"source IN ('{CHANGE_RECORD_SOURCE_BRAIN}')",
        name="ck_diagram_change_records_source",
    ),
    CheckConstraint(
        "length(trim(requirement_summary)) > 0",
        name="ck_diagram_change_records_summary_not_blank",
    ),
)

Index("ix_diagram_change_records_diagram_id", _DIAGRAM_CHANGE_RECORDS.c.diagram_id)

# U4-R1：90 天保存期的清除查詢以 created_at 為截止欄位。沒有索引它是全表掃描，
# 而本輪這張表零讀取端，沒有任何查詢會順手建它。
Index("ix_diagram_change_records_created_at", _DIAGRAM_CHANGE_RECORDS.c.created_at)

_MANAGED_TABLES = (_PROJECTS, _SYSTEMS, _DIAGRAM_CHANGE_RECORDS)


class MigrationCounts(NamedTuple):
    """`BR2.6`：遷移每一次執行都要留下可據以判斷進度的三個計數。

    - `users_processed`：本次走訪了幾位持有架構圖的使用者（重跑時仍會走訪，
      所以這個數字不會因冪等而歸零——歸零的是下面兩個）
    - `default_pairs_created`：本次**新建**了幾組預設專案／系統
    - `diagrams_assigned`：本次**改寫**了幾張圖的 `system_id`
    """

    users_processed: int
    default_pairs_created: int
    diagrams_assigned: int


class HierarchyMigrationError(RuntimeError):
    """遷移的不變量被違反。**這是錯誤，不是警告**（`BR2.1`／`AC9.1.4`）。"""


def migrate_hierarchy(db: Session) -> MigrationCounts:
    """本模組的唯一公開入口（`BR2.4`：可被 unittest 匯入並呼叫）。

    :param db: 一個已連線的 SQLAlchemy session。本函式自行管理交易邊界
        （逐使用者 commit），呼叫端不需要、也不應該先開交易。
    :returns: 三個計數（`BR2.6`）。
    :raises HierarchyMigrationError: 終檢時 `system_id IS NULL` 的列數不為 0。
    :raises Exception: 任何資料庫層的拒絕（唯一約束、FK、CHECK）**原樣往外拋**
        （`U4-V4`）。當下使用者的交易已回滾，先前使用者的進度保留。
    """
    _ensure_hierarchy_schema(db)

    user_ids = _users_holding_diagrams(db)
    logger.info("hierarchy migration: %d 位使用者持有架構圖", len(user_ids))

    users_processed = 0
    default_pairs_created = 0
    diagrams_assigned = 0

    for user_id, username in user_ids:
        # S-8：逐使用者一個交易。這一位的建立與改寫要麼全成要麼全不成；
        # 例外往外拋之前先回滾**這一位**，先前已 commit 的使用者不受影響。
        try:
            system_id, created = _resolve_default_pair(db, user_id, username)
            assigned = _assign_unassigned_diagrams(db, user_id, system_id)
            db.commit()
        except Exception:
            db.rollback()
            logger.error(
                "hierarchy migration: 使用者 id=%s 失敗並已回滾；"
                "先前使用者的進度保留，修正後重跑可補完（S-8）。"
                "本次在失敗前已處理 %d 位、建立 %d 組、改寫 %d 張",
                user_id,
                users_processed,
                default_pairs_created,
                diagrams_assigned,
            )
            raise

        users_processed += 1
        default_pairs_created += 1 if created else 0
        diagrams_assigned += assigned

    counts = MigrationCounts(
        users_processed=users_processed,
        default_pairs_created=default_pairs_created,
        diagrams_assigned=diagrams_assigned,
    )
    logger.info(
        "hierarchy migration 計數：處理 %d 位使用者、建立 %d 組預設專案／系統、"
        "改寫 %d 張圖的 system_id",
        counts.users_processed,
        counts.default_pairs_created,
        counts.diagrams_assigned,
    )

    _assert_no_unassigned_diagrams(db)
    return counts


# ---------------------------------------------------------------------------
# 以下皆為私有輔助函式。公開介面只有 migrate_hierarchy()（SEC-1）。
# ---------------------------------------------------------------------------


def _ensure_hierarchy_schema(db: Session) -> None:
    """`WF-1` 步 1–3、5：以可重跑安全的方式建立結構。重跑時為無操作。

    失敗**不吞**：任何 DDL 錯誤原樣往外拋，由呼叫端（獨立指令）以非零結束碼
    收場。這與 `backend/database.py` 的 `_ensure_*` 家族刻意相反。
    """
    bind = db.get_bind()

    # 步 1：三表 ＋ 兩個部分唯一索引 ＋ created_at 索引。checkfirst 讓重跑無操作。
    # 只傳本模組擁有的三張表——`users`／`user_diagrams` 的殘根永不進 create_all。
    _METADATA.create_all(bind=bind, tables=list(_MANAGED_TABLES), checkfirst=True)

    # 步 1b：索引的補建與守門（iteration 1 審查 R-01，Major）。
    #
    # `create_all(checkfirst=True)` 的判定是**表層級**的：表已存在就整張跳過，
    # 連同它的索引一起跳過。於是「表在、唯一索引不在」這個狀態既不會被建、
    # 也不會被發現——而 `BR2.2` 的整個冪等論證就架在那兩個部分唯一索引上，
    # 少了它們，重跑會安靜地建出第二組預設專案／系統。
    #
    # 這不是假想狀態：本次變更自己加進 `schema.sql` 的 `H)` 區塊就是建表而不建
    # 這三個索引（該檔為參考用、未被掛載，但它是一份會被人拿去跑的 SQL）。
    #
    # 處置是補建而非只偵測：三個索引都能以 `IF NOT EXISTS` 冪等建立，所以
    # 不論表是怎麼來的，跑完這一段之後它們一定在。建不起來就原樣往外拋。
    for index in (
        _PROJECTS.indexes | _SYSTEMS.indexes | _DIAGRAM_CHANGE_RECORDS.indexes
    ):
        index.create(bind=bind, checkfirst=True)

    # 步 2 ＋ 步 5 的 user_diagrams 那一半：加欄並同時帶上 ON DELETE RESTRICT。
    # 兩者必須在**同一條敘述**內完成——SQLite 無法對既有表追加 FK 約束，
    # 拆成兩步會讓測試環境永遠拿不到 BR1.2 的保護。
    inspector = inspect(bind)
    diagram_columns = {col["name"] for col in inspector.get_columns("user_diagrams")}
    if "system_id" not in diagram_columns:
        db.execute(
            text(
                "ALTER TABLE user_diagrams ADD COLUMN system_id INTEGER "
                "REFERENCES systems (id) ON DELETE RESTRICT"
            )
        )
        db.commit()
        logger.info("hierarchy migration: 已為 user_diagrams 加上 system_id 欄位")
    else:
        # 欄位已存在（只可能來自人工介入——本函式的加欄與 FK 是同一條敘述，
        # 所以自己的部分失敗不會留下「有欄位沒 FK」的狀態）。此時**必須**確認
        # BR1.2 的 FK 也在且動作正確：欄位有、FK 沒有（或 FK 動作是 SET NULL）
        # 的資料庫看起來完全正常，而刪除 System 會讓圖懸空。不可只記 warning
        # ——那正是本單元被明文要求否掉的形狀。
        system_fks = [
            fk
            for fk in inspector.get_foreign_keys("user_diagrams")
            if "system_id" in (fk.get("constrained_columns") or [])
            and fk.get("referred_table") == "systems"
        ]
        if not system_fks:
            raise HierarchyMigrationError(
                "user_diagrams.system_id 已存在，但沒有指向 systems 的外鍵——"
                "BR1.2（刪除 System 時拒絕，而非讓 system_id 懸空）因此未生效。"
                "請先手動補上：ALTER TABLE user_diagrams ADD CONSTRAINT "
                "fk_user_diagrams_system FOREIGN KEY (system_id) "
                "REFERENCES systems (id) ON DELETE RESTRICT;"
            )
        # `ondelete` 的可見性依方言而異：PostgreSQL 會回報 SET NULL／CASCADE
        # 等非預設動作（NO ACTION 回報為空），SQLite 一律回報為空。所以
        # **回報到的值不是 RESTRICT 才判為錯**；回報為空時只能代表
        # 「NO ACTION（PostgreSQL，行為上同樣拒絕）或方言不提供」，
        # 不足以判定違反，也不得反過來聲稱已驗證。
        ondelete = (system_fks[0].get("options") or {}).get("ondelete") or ""
        if ondelete and ondelete.upper() != "RESTRICT":
            raise HierarchyMigrationError(
                "user_diagrams.system_id 的外鍵存在，但 ON DELETE 動作是 "
                f"{ondelete.upper()} 而非 RESTRICT——刪除 System 時它會"
                "把圖的 system_id 設為空或連帶刪圖，兩者都直接製造 BR2.1 的違反。"
                "請先改為 ON DELETE RESTRICT 再重跑遷移。"
            )
        logger.info(
            "hierarchy migration: user_diagrams.system_id 已存在且外鍵指向 "
            "systems（ON DELETE 回報值=%r；空值代表 NO ACTION 或方言不提供）",
            ondelete,
        )

    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_user_diagrams_system_id "
            "ON user_diagrams (system_id)"
        )
    )
    db.commit()
    logger.info("hierarchy migration: 結構檢查完成（三表 ＋ system_id ＋ 索引）")


def _users_holding_diagrams(db: Session) -> list[tuple[int, str]]:
    """`BR2.5`：持有至少一張架構圖的使用者。不持有圖者**不**建立預設專案。

    以 `users` 做 join 而不是只取 `user_diagrams.user_id` 的 distinct 值：
    `projects.owner_user_id` 有指向 `users.id` 的外鍵，對一個不存在的使用者建
    專案在 PostgreSQL 上必然被 FK 拒絕。指向不存在使用者的孤兒圖因此不會被
    處理，而它們會在終檢時被計入殘留並讓遷移大聲失敗——那是正確的結果：
    孤兒列需要人工判斷，不是遷移該默默決定的事。
    """
    rows = db.execute(
        text(
            "SELECT DISTINCT u.id, u.username "
            "FROM users u JOIN user_diagrams d ON d.user_id = u.id "
            "ORDER BY u.id"
        )
    ).all()
    return [(int(row[0]), str(row[1])) for row in rows]


def _resolve_default_pair(
    db: Session, user_id: int, username: str
) -> tuple[int, bool]:
    """取得或建立該使用者的預設專案與預設系統，回傳 `(system_id, 是否新建)`。

    **順序是 `BR2.5` 獨佔寫入紀律的全部內容，不可調換**：先解析出預設
    **專案**，再**以該專案的 id 為範圍**找預設系統。複合性質「每位使用者至多
    一組預設專案／系統」靠的就是這個順序——資料庫只保證「每位使用者至多一個
    預設專案」與「每個專案至多一個預設系統」兩件事，**沒有任何約束**擋住
    「預設系統掛在非預設專案底下」。今天它成立的唯一理由是本函式是
    `is_default` 的唯一寫入端。

    「是否新建」以**專案**是否新建為準：預設專案與預設系統成對建立，兩者在同
    一個交易內，所以專案新建等價於這一組新建。
    """
    project_row = db.execute(
        text(
            "SELECT id FROM projects "
            "WHERE owner_user_id = :owner AND is_default = :truthy"
        ),
        {"owner": user_id, "truthy": True},
    ).first()

    created = project_row is None
    if project_row is None:
        # created_at 刻意不由本函式提供：兩處 DDL 都給了 server default
        # （PostgreSQL 的 now()、SQLite 的 CURRENT_TIMESTAMP），交給資料庫填
        # 可免去 tz-aware datetime 在不同 dialect 上的綁定差異。
        db.execute(
            _PROJECTS.insert().values(
                name=f"{username} 的專案",
                owner_user_id=user_id,
                is_default=True,
            )
        )
        project_row = db.execute(
            text(
                "SELECT id FROM projects "
                "WHERE owner_user_id = :owner AND is_default = :truthy"
            ),
            {"owner": user_id, "truthy": True},
        ).first()
        if project_row is None:  # pragma: no cover - 防禦性；插入成功後必然讀得到
            raise HierarchyMigrationError(
                f"使用者 id={user_id} 的預設專案插入後讀不回來，遷移中止"
            )

    project_id = int(project_row[0])

    system_row = db.execute(
        text(
            "SELECT id FROM systems WHERE project_id = :project AND is_default = :truthy"
        ),
        {"project": project_id, "truthy": True},
    ).first()
    if system_row is None:
        db.execute(
            _SYSTEMS.insert().values(
                project_id=project_id,
                name="預設系統",
                is_default=True,
            )
        )
        system_row = db.execute(
            text(
                "SELECT id FROM systems "
                "WHERE project_id = :project AND is_default = :truthy"
            ),
            {"project": project_id, "truthy": True},
        ).first()
        if system_row is None:  # pragma: no cover - 防禦性
            raise HierarchyMigrationError(
                f"專案 id={project_id} 的預設系統插入後讀不回來，遷移中止"
            )

    return int(system_row[0]), created


def _assign_unassigned_diagrams(db: Session, user_id: int, system_id: int) -> int:
    """把該使用者 `system_id` 為空的圖掛入指定系統，回傳改寫的列數。

    `BR2.2` 的冪等判準是 `system_id IS NOT NULL`——已掛好的圖**不**重新指派。
    `BR2.3`：只寫 `system_id`。刻意走 `text()` 而不走 ORM，因為
    `models.UserDiagram.updated_at` 帶 `onupdate=func.now()`，ORM 更新會連帶
    改寫它，而 `owner_user_id`／`title`／`xml_data`／`updated_at` 四欄逐欄
    不得變動。
    """
    result = db.execute(
        text(
            "UPDATE user_diagrams SET system_id = :system "
            "WHERE user_id = :owner AND system_id IS NULL"
        ),
        {"system": system_id, "owner": user_id},
    )
    return int(result.rowcount or 0)


def _assert_no_unassigned_diagrams(db: Session) -> None:
    """`WF-1` 步 6／`BR2.1`／`AC9.1.4`：終檢。**不為 0 即 raise，不是 warning。**

    可達路徑有兩條：(1) 遷移期間應用寫入了新圖（`U4-V6` 要求的靜止窗口尚無
    承載者，見 `S-9`）；(2) 實作本身有缺陷。兩條都必須讓程序以非零結束碼收場
    ——一次「看起來成功」的遷移比一次失敗的遷移危險得多。
    """
    residual = db.execute(
        text("SELECT count(*) FROM user_diagrams WHERE system_id IS NULL")
    ).scalar()
    residual = int(residual or 0)
    if residual:
        raise HierarchyMigrationError(
            f"遷移終檢失敗：user_diagrams 仍有 {residual} 列 system_id IS NULL"
            "（BR2.1／AC9.1.4，該數必須為 0）。可能原因：遷移期間應用仍在接"
            "流量而新建了圖（U4-V6 要求的靜止窗口），或存在指向不存在使用者的"
            "孤兒列。請查 SELECT id, user_id FROM user_diagrams "
            "WHERE system_id IS NULL; 後人工處置再重跑。"
        )
    logger.info("hierarchy migration 終檢通過：system_id IS NULL 的列數為 0")
