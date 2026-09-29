"""`U4 hierarchy-data` 的結構與遷移測試（三層，15 個案例）。

三個 `TestCase` 類對應 `code-generation-plan.md` 的三個可測層：

| 類 | 層 | 案例數 |
|---|---|---|
| `TestHierarchySchema` | 資料模型（步 3） | 7（計畫的 5 ＋ 本檔補 2，理由見下） |
| `TestHierarchyMigrationData` | 資料讀寫（步 5） | 3 |
| `TestHierarchyMigrationLogic` | 業務邏輯（步 7） | 5 |

**兩個計畫外的案例**（計畫定 13 個，本檔為 15 個），兩者都在此明白揭露：

1. `test_schema_rbac_sql_matches_migration_ddl` —— 本單元的 DDL 必然存在兩處：
   `schema_rbac.sql` 只在**空 data volume** 執行（`K-04` 的
   `context_why_migration_is_the_only_path` 逐字），既有環境的唯一演進路徑是遷移
   程序自己。`team.md` 的「單一真實來源」逐字要求「新增副本的同一個 PR 必須一併
   新增鎖住兩者一致的測試；無法寫測試的副本不新增」，而這個測試寫得出來，
   所以不寫等於違反該條。
2. `test_pre_existing_system_id_without_a_foreign_key_is_rejected` —— 它測的是
   `_ensure_hierarchy_schema` 的 raise 分支（欄位已存在但外鍵不在）。那是本站
   自己加的防禦路徑，`construction.md` 要求測試涵蓋 happy path 與至少兩個
   錯誤／邊界情境，而一條沒有任何案例碰過的 raise 路徑會靜默腐爛。

`TestHierarchySchema` 因此是 7 個案例，仍落在 Standard 策略的「每元件 5–8 個」
區間內。

**不用 `hypothesis`**：`rules.md §二` 實算的 `calculation` 類規則數為 0，沒有
值域性質可寫成 property；`ADR-0006` 的 PBT hard constraint 點名的三個模組
（IaC generator、cost calculator、agent routing）不含本單元。判定為 N/A 而非豁免。

**SQLite 與 PostgreSQL 的落差：本輪實測為零**。四項原本預期可能不可攜的機制
在 in-memory SQLite 上全部**真的擋住**：部分唯一索引（`WHERE is_default`）、
`ON DELETE RESTRICT`（需 `PRAGMA foreign_keys=ON`，見 `_set_sqlite_foreign_keys`）、
`CHECK (length(trim(...)) > 0)`、`CHECK (source IN (...))`。因此沒有任何案例被
標為「只能在真實 PostgreSQL 驗證」。真實 PG CI job（`U4-V1`–`U4-V5`）仍是必要
的——它驗的是 `schema_rbac.sql` 那一份 DDL 與 PG 專屬語法（`SERIAL`、
`TIMESTAMPTZ`、`DO $$` 區塊），本檔驗的是遷移模組那一份。

`@api`／`@ui` 在本檔**刻意缺席**：本單元交付零端點、零畫面（`SEC-1`／`SEC-3`），
依 `project.md` 的既有更正「受測對象既無端點也無 UI 時寧可缺、不得捏造」。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests import helpers
from services.hierarchy_migration import (
    CHANGE_RECORD_SOURCE_BRAIN,
    HierarchyMigrationError,
    MigrationCounts,
    migrate_hierarchy,
)
from services.hierarchy_migration import (
    _DIAGRAM_CHANGE_RECORDS,
    _PROJECTS,
    _SYSTEMS,
    _ensure_hierarchy_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_RBAC_SQL = REPO_ROOT / "schema_rbac.sql"

# 遷移之前寫進 user_diagrams.updated_at 的固定值。用固定的過去時間而不是讓
# ORM 的 server_default 填 CURRENT_TIMESTAMP：後者在 SQLite 只有秒級解析度，
# 同一秒內的重新觸發會產生相同的值，使 BR2.3 的斷言變成可能恆真。
PINNED_UPDATED_AT = "2020-01-02 03:04:05"


def _set_sqlite_foreign_keys(db, enabled: bool) -> None:
    """在 SQLite 上開關 FK 強制。非 SQLite 時為無操作（PostgreSQL 一律強制）。

    SQLite 預設 `foreign_keys=OFF`，而 `PRAGMA` 在交易內是無操作，所以必須先
    `commit()` 把連線交還給 pool 再設。`helpers.make_session()` 用 `StaticPool`
    ——整個 engine 只有一條連線，所以設一次就對這個 session 生效。
    """
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return
    db.commit()
    raw = bind.raw_connection()
    try:
        raw.driver_connection.execute(
            "PRAGMA foreign_keys=" + ("ON" if enabled else "OFF")
        )
    finally:
        raw.close()


def _insert_project(db, *, name: str, owner_user_id: int, is_default: bool) -> int:
    db.execute(
        _PROJECTS.insert().values(
            name=name, owner_user_id=owner_user_id, is_default=is_default
        )
    )
    db.commit()
    return int(
        db.execute(
            text("SELECT id FROM projects WHERE name = :n"), {"n": name}
        ).scalar()
    )


def _insert_system(db, *, name: str, project_id: int, is_default: bool) -> int:
    db.execute(
        _SYSTEMS.insert().values(
            name=name, project_id=project_id, is_default=is_default
        )
    )
    db.commit()
    return int(
        db.execute(text("SELECT id FROM systems WHERE name = :n"), {"n": name}).scalar()
    )


def _orphan_diagram(db, *, user_id: int, title: str) -> int:
    """直接以 SQL 插入一張圖，不經 ORM，讓 `user_id` 可以指向不存在的使用者。

    這是本檔構造「終檢有殘留」的手段。**在 PostgreSQL 上這個前置狀態不可達**
    （`user_diagrams.user_id` 有指向 `users.id` 的外鍵），所以它不是在主張孤兒
    列會在生產環境出現。終檢在生產環境的可達路徑是 `U4-V6` 的競爭窗口——遷移
    期間應用仍在接流量而新建了不帶 `system_id` 的圖，而那個有序靜止窗口目前
    尚無承載者（`S-9`）。本手段只是在單執行緒測試裡取得同一個資料面狀態。
    """
    db.execute(
        text(
            "INSERT INTO user_diagrams (user_id, title, xml_data) "
            "VALUES (:u, :t, '<mxGraphModel/>')"
        ),
        {"u": user_id, "t": title},
    )
    db.commit()
    return int(
        db.execute(
            text("SELECT id FROM user_diagrams WHERE title = :t"), {"t": title}
        ).scalar()
    )


def _system_id_of(db, diagram_id: int):
    return db.execute(
        text("SELECT system_id FROM user_diagrams WHERE id = :i"), {"i": diagram_id}
    ).scalar()


def _count(db, sql: str, params: dict | None = None) -> int:
    return int(db.execute(text(sql), params or {}).scalar() or 0)


def _columns_declared_in_schema_rbac(table: str) -> set[str]:
    """從 `schema_rbac.sql` 的 `CREATE TABLE IF NOT EXISTS <table> (...)` 取欄位名。

    只取欄位定義列，跳過表級約束列（`CONSTRAINT`／`PRIMARY`／`FOREIGN`／
    `CHECK`／`UNIQUE` 開頭）。
    """
    sql = SCHEMA_RBAC_SQL.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS " + re.escape(table) + r" \(\n(.*?)\n\);",
        sql,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(
            f"schema_rbac.sql 沒有 {table} 的 CREATE TABLE IF NOT EXISTS 區塊"
        )
    columns = set()
    for line in match.group(1).splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        head = stripped.split()[0].upper()
        if head in {"CONSTRAINT", "PRIMARY", "FOREIGN", "CHECK", "UNIQUE"}:
            continue
        columns.add(stripped.split()[0])
    return columns


class TestHierarchySchema(unittest.TestCase):
    """資料模型層：`BR1.1`／`BR1.2`／`BR1.3` 與新欄位的可空性、封閉列舉。"""

    def setUp(self):
        self.db = helpers.make_session()
        _ensure_hierarchy_schema(self.db)
        # BR1.1／BR1.2 是 FK 的 ON DELETE RESTRICT，SQLite 預設不強制 FK。
        _set_sqlite_foreign_keys(self.db, True)
        self.alice = helpers.make_user(
            self.db, username="alice", role="Project_Architect"
        )
        self.bob = helpers.make_user(self.db, username="bob", role="Developer")

    def tearDown(self):
        self.db.rollback()
        # 關掉 FK 再拆：`helpers.close_session` 會 drop Base.metadata 的表，而本
        # 單元的三張表不在 Base 裡、仍持有指向 users 的列，FK 開著會讓 drop 失敗。
        _set_sqlite_foreign_keys(self.db, False)
        helpers.close_session(self.db)

    def test_partial_unique_indexes_block_a_second_default_at_each_layer(self):
        """
        @purpose BR1.3 的兩個部分唯一索引必須各自擋住第二筆預設列，而且
                 「部分」要真的是部分——非預設列不受限，且 systems 那一層的
                 範圍是 project_id 而不是擁有者。
        @given 兩位使用者 alice／bob；alice 有一個預設專案與一個非預設專案
        @step 為 alice 插入第二個 is_default 為真的專案 | 被唯一索引拒絕
        @step 為 alice 插入 is_default 為假的第二個專案 | 允許（證明索引是部分的）
        @step 為 bob 插入 is_default 為真的專案 | 允許（範圍是每位擁有者）
        @step 在 alice 的預設專案下插入第二個預設系統 | 被唯一索引拒絕
        @step 在 alice 的**非**預設專案下插入預設系統 | 允許
        @pass 兩次重複插入皆拋 IntegrityError；三次合法插入皆成功
        @story US9.1
        @note 最後一步是這個案例的重點：它同時證明 systems 的唯一性以
              project_id 為範圍（若誤以擁有者為範圍，這一步會失敗——而
              entities.md 的審查 R-01 記載初版正是那樣寫的，照描述做不出來），
              並就地記下那個已知缺口：「預設系統掛在非預設專案底下」沒有任何
              約束擋住，該耦合由 BR2.5 的獨佔寫入紀律供應。
        """
        default_project = _insert_project(
            self.db, name="alice 的專案", owner_user_id=self.alice.id, is_default=True
        )

        with self.assertRaises(IntegrityError):
            _insert_project(
                self.db, name="第二個預設", owner_user_id=self.alice.id, is_default=True
            )
        self.db.rollback()

        plain_project = _insert_project(
            self.db, name="alice 的第二個專案", owner_user_id=self.alice.id, is_default=False
        )
        _insert_project(
            self.db, name="bob 的專案", owner_user_id=self.bob.id, is_default=True
        )
        self.assertEqual(3, _count(self.db, "SELECT count(*) FROM projects"))

        _insert_system(
            self.db, name="預設系統", project_id=default_project, is_default=True
        )
        with self.assertRaises(IntegrityError):
            _insert_system(
                self.db, name="第二個預設系統", project_id=default_project, is_default=True
            )
        self.db.rollback()

        # 同一位擁有者的另一個（非預設）專案下仍可有一個預設系統。
        _insert_system(
            self.db, name="非預設專案的預設系統", project_id=plain_project, is_default=True
        )
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM systems"))

    def test_on_delete_restrict_blocks_both_deletion_layers(self):
        """
        @purpose BR1.1／BR1.2：其下還有內容時，刪除 Project 與刪除 System
                 都必須被拒絕，而且拒絕是有條件的——清空之後刪得掉。
        @given alice 有預設專案、其下有預設系統、系統下掛著一張架構圖
        @step 刪除該 System | 被外鍵拒絕
        @step 刪除該 Project | 被外鍵拒絕
        @step 把該圖的 system_id 清空後刪除 System | 成功
        @step 再刪除 Project | 成功
        @pass 前兩次刪除皆拋 IntegrityError 且列數不變；清空後兩次刪除皆成功
        @story US9.1
        @note 兩層都要測。只鎖 System 那一層的話，刪 Project 時 System 連帶
              消失，其下的圖照樣懸空——contract-summary.md 的 DG-2 逐字就是
              「Project／System 刪除的 cascade 行為未定」兩個分支。
              後兩步是防恆真的關鍵：若 FK 根本沒生效，前兩步的 assertRaises
              會失敗；若刪除是被無條件擋住，後兩步會失敗。
        """
        project_id = _insert_project(
            self.db, name="alice 的專案", owner_user_id=self.alice.id, is_default=True
        )
        system_id = _insert_system(
            self.db, name="預設系統", project_id=project_id, is_default=True
        )
        diagram = helpers.make_diagram(self.db, owner=self.alice, title="掛好的圖")
        self.db.execute(
            text("UPDATE user_diagrams SET system_id = :s WHERE id = :d"),
            {"s": system_id, "d": diagram.id},
        )
        self.db.commit()

        with self.assertRaises(IntegrityError):
            self.db.execute(text("DELETE FROM systems WHERE id = :s"), {"s": system_id})
            self.db.commit()
        self.db.rollback()
        self.assertEqual(1, _count(self.db, "SELECT count(*) FROM systems"))
        self.assertEqual(system_id, _system_id_of(self.db, diagram.id))

        with self.assertRaises(IntegrityError):
            self.db.execute(
                text("DELETE FROM projects WHERE id = :p"), {"p": project_id}
            )
            self.db.commit()
        self.db.rollback()
        self.assertEqual(1, _count(self.db, "SELECT count(*) FROM projects"))

        self.db.execute(
            text("UPDATE user_diagrams SET system_id = NULL WHERE id = :d"),
            {"d": diagram.id},
        )
        self.db.commit()
        self.db.execute(text("DELETE FROM systems WHERE id = :s"), {"s": system_id})
        self.db.commit()
        self.db.execute(text("DELETE FROM projects WHERE id = :p"), {"p": project_id})
        self.db.commit()
        self.assertEqual(0, _count(self.db, "SELECT count(*) FROM systems"))
        self.assertEqual(0, _count(self.db, "SELECT count(*) FROM projects"))

    def test_system_id_is_nullable_so_a_pre_migration_diagram_can_exist(self):
        """
        @purpose user_diagrams.system_id 必須可為空——這是 U4-V2 的 CI 前置狀態
                 唯一造得出來的前提（S-7），也是 AC9.1.3 得以成立的原因：
                 既有頁面的插入不帶這一欄。
        @given 結構已建立（含 system_id 欄位）
        @step 以既有頁面的形狀插入一張不帶 system_id 的圖 | 插入成功
        @step 讀回該列的 system_id | 為 NULL
        @pass 插入不拋例外，且讀回的值是 None
        @story US9.1
        @note 這個案例的價值不在「NULL 可以存」這件小事，而在它把 OQ-H2 的
              牽制固定成可執行的事實：若日後把本欄收成 NOT NULL，本案例會紅，
              而那正是 S-7 要求「OQ-H2 的定案必須連帶回答它對測試夾具的影響」
              的機械形式。
        """
        diagram = helpers.make_diagram(self.db, owner=self.alice, title="遷移前的圖")
        self.assertIsNone(_system_id_of(self.db, diagram.id))
        self.assertEqual(
            1, _count(self.db, "SELECT count(*) FROM user_diagrams WHERE system_id IS NULL")
        )

    def test_change_record_requires_an_actor(self):
        """
        @purpose diagram_change_records.actor_user_id 必須為必填（SEC-4 第 4 處）：
                 一列說得出「圖變了」卻說不出「是誰讓它變的」的紀錄，不構成稽核。
        @given alice 有一張圖
        @step 插入一列帶 actor_user_id 的變更紀錄 | 成功（證明其餘欄位無誤）
        @step 插入一列缺 actor_user_id 的變更紀錄 | 被 NOT NULL 拒絕
        @pass 第一次插入成功，第二次拋 IntegrityError
        @story US9.1
        @note 先插入一列合法的再插入缺欄位的那一列，是為了排除「插入之所以失敗
              是因為別的欄位寫錯」這種假通過。
        """
        diagram = helpers.make_diagram(self.db, owner=self.alice, title="會被異動的圖")
        self.db.execute(
            _DIAGRAM_CHANGE_RECORDS.insert().values(
                diagram_id=diagram.id,
                source=CHANGE_RECORD_SOURCE_BRAIN,
                actor_user_id=self.alice.id,
                requirement_summary="把資料庫改成高可用",
                requirement_label="ha",
            )
        )
        self.db.commit()
        self.assertEqual(
            1, _count(self.db, "SELECT count(*) FROM diagram_change_records")
        )

        with self.assertRaises(IntegrityError):
            self.db.execute(
                text(
                    "INSERT INTO diagram_change_records "
                    "(diagram_id, source, requirement_summary, requirement_label) "
                    "VALUES (:d, :s, '摘要', '標籤')"
                ),
                {"d": diagram.id, "s": CHANGE_RECORD_SOURCE_BRAIN},
            )
            self.db.commit()
        self.db.rollback()
        self.assertEqual(
            1, _count(self.db, "SELECT count(*) FROM diagram_change_records")
        )

    def test_change_record_source_is_a_closed_enum(self):
        """
        @purpose diagram_change_records.source 是封閉列舉（BR3.1）：它讓這張表的
                 涵蓋面成為可查詢的事實，而不是散文裡的一句話。未定義的值必須
                 在資料庫層被拒絕。
        @given alice 有一張圖
        @step 以本輪唯一合法值 brain_orchestration 插入一列 | 成功
        @step 以 manual_edit 插入一列 | 被 CHECK 約束拒絕
        @step 以空字串插入一列 | 被 CHECK 約束拒絕
        @pass 合法值成功、兩個非法值皆拋 IntegrityError，且表內仍只有一列
        @story US9.1
        @note 若未來 A1 儲存路徑也要寫入，做法是新增一個列舉值（改 CHECK 約束），
              不需要 schema 遷移——這正是選欄位而不選改表名的理由。
        """
        diagram = helpers.make_diagram(self.db, owner=self.alice, title="會被異動的圖")
        self.db.execute(
            _DIAGRAM_CHANGE_RECORDS.insert().values(
                diagram_id=diagram.id,
                source=CHANGE_RECORD_SOURCE_BRAIN,
                actor_user_id=self.alice.id,
                requirement_summary="加一層快取",
                requirement_label="cache",
            )
        )
        self.db.commit()

        for illegal in ("manual_edit", ""):
            with self.subTest(source=illegal):
                with self.assertRaises(IntegrityError):
                    self.db.execute(
                        _DIAGRAM_CHANGE_RECORDS.insert().values(
                            diagram_id=diagram.id,
                            source=illegal,
                            actor_user_id=self.alice.id,
                            requirement_summary="加一層快取",
                            requirement_label="cache",
                        )
                    )
                    self.db.commit()
                self.db.rollback()

        self.assertEqual(
            1, _count(self.db, "SELECT count(*) FROM diagram_change_records")
        )

    def test_pre_existing_system_id_without_a_foreign_key_is_rejected(self):
        """
        @purpose 欄位已存在但外鍵不在時，結構檢查必須 **raise** 而不是繼續跑完
                 ——那種資料庫看起來完全正常，而刪除 System 會讓圖懸空
                 （BR1.2 靜默失效）。
        @given 一個乾淨資料庫，其 user_diagrams 已被人工加過 system_id 欄位
               但**沒有**指向 systems 的外鍵
        @step 呼叫結構檢查 | 拋出 HierarchyMigrationError
        @step 檢查例外訊息 | 指名 BR1.2 並給出補外鍵的 ALTER 敘述
        @pass 例外型別與訊息皆符合；**不是**記一行 warning 然後繼續
        @story US9.1
        @note 這個分支只可能來自人工介入——結構檢查自己的加欄與外鍵是同一條
              敘述，所以它自己的部分失敗不會留下這個狀態。它仍然要被測，因為
              `192.168.10.10` 是既有環境，而「有欄位、沒外鍵」在資料面上與
              「一切正常」完全無法區分。本案例是本檔第二個計畫外的案例，
              理由與第一個相同：它測的是本站自己寫的 raise 路徑，
              而未被覆蓋的 raise 路徑會靜默腐爛。
        """
        db = helpers.make_session()
        try:
            db.execute(text("ALTER TABLE user_diagrams ADD COLUMN system_id INTEGER"))
            db.commit()

            with self.assertRaises(HierarchyMigrationError) as ctx:
                _ensure_hierarchy_schema(db)
            message = str(ctx.exception)
            self.assertIn("BR1.2", message)
            self.assertIn("ON DELETE RESTRICT", message)
        finally:
            db.rollback()
            _set_sqlite_foreign_keys(db, False)
            helpers.close_session(db)

    def test_schema_rbac_sql_matches_migration_ddl(self):
        """
        @purpose 本單元的 DDL 必然存在兩處（schema_rbac.sql 與遷移模組），
                 而 team.md 的「單一真實來源」要求副本必須有鎖住一致性的測試。
                 本案例就是那把鎖。
        @given repo 根的 schema_rbac.sql 與 services/hierarchy_migration.py
        @step 從 schema_rbac.sql 解析三張表的欄位名 | 與遷移模組的 Table 定義逐表相同
        @step 檢查 schema_rbac.sql 有為 user_diagrams 加 system_id 的敘述 | 存在
        @step 檢查兩個部分唯一索引名稱都出現在 schema_rbac.sql | 兩者皆在
        @step 檢查 created_at 索引名稱出現在 schema_rbac.sql | 存在（U4-R1 的清除查詢依賴它）
        @pass 三個欄位集合相等，且四個識別字都在 schema_rbac.sql 內
        @story US9.1
        @note 為什麼兩處都需要：schema_rbac.sql 只在**空 data volume** 執行
              （兩份 compose 把它掛進 /docker-entrypoint-initdb.d/），既有環境
              永遠不會經過它；既有環境的唯一演進路徑是遷移程序自己（K-04 的
              context_why_migration_is_the_only_path）。本案例不比對型別與約束
              ——那需要一個真的 PostgreSQL，屬 U4-V1 的 CI job；本案例只鎖住
              最容易漏的那一類（加了欄位卻只改一邊）。
        """
        sql = SCHEMA_RBAC_SQL.read_text(encoding="utf-8")

        for table_obj in (_PROJECTS, _SYSTEMS, _DIAGRAM_CHANGE_RECORDS):
            with self.subTest(table=table_obj.name):
                self.assertEqual(
                    set(table_obj.c.keys()),
                    _columns_declared_in_schema_rbac(table_obj.name),
                    f"{table_obj.name} 的欄位集合在 schema_rbac.sql 與 "
                    "hierarchy_migration.py 之間不一致——兩處 DDL 必須同步",
                )

        self.assertRegex(
            sql,
            r"ALTER TABLE user_diagrams ADD COLUMN IF NOT EXISTS system_id",
            "schema_rbac.sql 缺少 user_diagrams.system_id 的加欄敘述",
        )
        for identifier in (
            "uq_projects_default_per_owner",
            "uq_systems_default_per_project",
            "ix_diagram_change_records_created_at",
        ):
            with self.subTest(identifier=identifier):
                self.assertIn(identifier, sql)


class TestHierarchyMigrationData(unittest.TestCase):
    """資料讀寫層：`BR2.5`（逐使用者、不持有圖者不建）與 `BR2.3`（不動既有欄位）。

    本類**刻意不**在 `setUp` 呼叫 `_ensure_hierarchy_schema`——讓
    `migrate_hierarchy` 自己建結構，順帶證明 `WF-1` 步 1–3 真的在遷移流程內。
    """

    def setUp(self):
        self.db = helpers.make_session()
        self.alice = helpers.make_user(
            self.db, username="alice", role="Project_Architect"
        )
        self.bob = helpers.make_user(self.db, username="bob", role="Developer")

    def tearDown(self):
        self.db.rollback()
        helpers.close_session(self.db)

    def test_each_users_diagrams_land_in_that_users_own_default_system(self):
        """
        @purpose BR2.5：遷移為每位持有圖的使用者建立恰好一組預設專案／系統，
                 並把該使用者的圖掛入**自己**那一組，不會互相錯掛。
        @given alice 有 2 張、bob 有 3 張 system_id 為空的圖
        @step 執行遷移 | 兩位各得一個預設專案與一個預設系統
        @step 檢查每張圖的 system_id | 等於其擁有者的預設系統 id
        @step 比較兩位的預設系統 id | 不相等
        @step 檢查每個預設系統所屬專案的 owner_user_id | 等於該圖的擁有者
        @pass 五張圖全部掛好、兩組預設互不相同、專案擁有者正確
        @story US9.1
        @note 「兩位的預設系統 id 不相等」與「專案擁有者正確」兩項缺一不可：
              一個把所有圖都掛到同一個系統的實作會通過「全部非空」的檢查，
              卻完全破壞 ADR-003 的「歸屬與現行擁有者一致」。
        """
        alice_diagrams = [
            helpers.make_diagram(self.db, owner=self.alice, title=f"a{i}")
            for i in range(2)
        ]
        bob_diagrams = [
            helpers.make_diagram(self.db, owner=self.bob, title=f"b{i}")
            for i in range(3)
        ]

        migrate_hierarchy(self.db)

        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM projects"))
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM systems"))

        def default_system_of(user_id: int) -> int:
            return int(
                self.db.execute(
                    text(
                        "SELECT s.id FROM systems s JOIN projects p ON p.id = s.project_id "
                        "WHERE p.owner_user_id = :u AND p.is_default = :t "
                        "AND s.is_default = :t"
                    ),
                    {"u": user_id, "t": True},
                ).scalar()
            )

        alice_system = default_system_of(self.alice.id)
        bob_system = default_system_of(self.bob.id)
        self.assertNotEqual(alice_system, bob_system)

        for diagram in alice_diagrams:
            self.assertEqual(alice_system, _system_id_of(self.db, diagram.id))
        for diagram in bob_diagrams:
            self.assertEqual(bob_system, _system_id_of(self.db, diagram.id))

        owners = self.db.execute(
            text(
                "SELECT s.id, p.owner_user_id FROM systems s "
                "JOIN projects p ON p.id = s.project_id ORDER BY s.id"
            )
        ).all()
        self.assertEqual(
            {(alice_system, self.alice.id), (bob_system, self.bob.id)},
            {(int(row[0]), int(row[1])) for row in owners},
        )

    def test_a_user_without_diagrams_gets_no_default_project(self):
        """
        @purpose BR2.5 的收窄：不持有任何架構圖的使用者**不**被建立預設專案，
                 否則會產生一批沒有內容的空專案。
        @given alice 有 1 張圖，bob 一張都沒有
        @step 執行遷移 | 只建立一組預設專案／系統
        @step 查 bob 名下的專案列數 | 為 0
        @pass projects 與 systems 各只有 1 列，且沒有一列屬於 bob
        @story US9.1
        @note 這條是本站對上游的收窄（K-04 的 migration.action 沒有明說），
              所以它必須有自己的斷言——只靠「alice 的圖掛好了」無法區分
              「只為持有者建」與「為全部使用者建」。
        """
        helpers.make_diagram(self.db, owner=self.alice, title="唯一的圖")

        counts = migrate_hierarchy(self.db)

        self.assertEqual(1, counts.users_processed)
        self.assertEqual(1, counts.default_pairs_created)
        self.assertEqual(1, _count(self.db, "SELECT count(*) FROM projects"))
        self.assertEqual(1, _count(self.db, "SELECT count(*) FROM systems"))
        self.assertEqual(
            0,
            _count(
                self.db,
                "SELECT count(*) FROM projects WHERE owner_user_id = :u",
                {"u": self.bob.id},
            ),
        )

    def test_migration_does_not_touch_any_existing_diagram_column(self):
        """
        @purpose BR2.3／AC9.1.3：遷移只寫 system_id，既有四欄
                 （user_id／title／xml_data／updated_at）逐欄不得變動。
        @given alice 有 2 張圖，其 updated_at 已被釘在一個固定的過去時間
        @step 逐欄記下遷移前的值 | 取得四欄的快照
        @step 執行遷移 | 完成
        @step 逐欄比對遷移後的值 | 四欄與快照完全相同
        @pass 每一張圖的四個欄位值前後相等，且 system_id 由 NULL 變為非 NULL
        @story US9.1
        @note 這是本檔最容易寫成恆真的一個案例。兩個防護：(1) 逐欄比值，不是
              只斷言列還在；(2) 先把 updated_at 釘成固定的過去時間——
              models.UserDiagram.updated_at 帶 onupdate=func.now()，若實作改走
              ORM 更新，updated_at 就會被改寫；不釘值的話 SQLite 的
              CURRENT_TIMESTAMP 只有秒級解析度，同一秒內前後值會相同而讓
              這個缺陷通過。
        """
        diagrams = [
            helpers.make_diagram(
                self.db, owner=self.alice, title=f"標題 {i}", xml_data=f"<mx id='{i}'/>"
            )
            for i in range(2)
        ]
        ids = [d.id for d in diagrams]
        self.db.execute(
            text("UPDATE user_diagrams SET updated_at = :ts"),
            {"ts": PINNED_UPDATED_AT},
        )
        self.db.commit()

        snapshot_sql = (
            "SELECT id, user_id, title, xml_data, updated_at "
            "FROM user_diagrams ORDER BY id"
        )
        before = {row[0]: tuple(row[1:]) for row in self.db.execute(text(snapshot_sql))}
        self.assertEqual(set(ids), set(before))

        migrate_hierarchy(self.db)

        after = {row[0]: tuple(row[1:]) for row in self.db.execute(text(snapshot_sql))}
        for diagram_id in ids:
            with self.subTest(diagram_id=diagram_id):
                for column, old, new in zip(
                    ("user_id", "title", "xml_data", "updated_at"),
                    before[diagram_id],
                    after[diagram_id],
                ):
                    self.assertEqual(
                        old,
                        new,
                        f"遷移改動了既有欄位 {column}（BR2.3）：{old!r} -> {new!r}",
                    )
                self.assertIsNotNone(_system_id_of(self.db, diagram_id))


class TestHierarchyMigrationLogic(unittest.TestCase):
    """業務邏輯層：終檢的失敗形式、計數、冪等、部分失敗後重跑、獨立指令結束碼。"""

    def setUp(self):
        self.db = helpers.make_session()
        self.alice = helpers.make_user(
            self.db, username="alice", role="Project_Architect"
        )
        self.bob = helpers.make_user(self.db, username="bob", role="Developer")

    def tearDown(self):
        self.db.rollback()
        helpers.close_session(self.db)

    def test_final_check_raises_with_the_residual_count(self):
        """
        @purpose BR2.1／AC9.1.4：終檢在 system_id IS NULL 的列數不為 0 時必須
                 **raise**，不得以 logger.warning 帶過，且訊息要帶出殘留列數。
        @given alice 有 2 張圖；另有 2 張圖的 user_id 指向不存在的使用者，
               因此不會被逐使用者迴圈處理
        @step 執行遷移 | 拋出 HierarchyMigrationError
        @step 檢查例外訊息 | 含殘留列數 2
        @step 檢查 alice 的圖 | 已被掛好（迴圈在終檢之前就 commit 過了）
        @pass 例外型別與訊息內容皆符合，且殘留列數確實為 2
        @story US9.1
        @note stories.md:426 逐字寫明 AC9.1.4 的目的是「直接否掉照抄既有
              logger.warning 形狀的實作」。所以本案例斷言的是 raise，不是
              「有沒有記 log」——一個只記 warning 的實作會讓 assertRaises 失敗。
              前置狀態的構造方式與其在 PostgreSQL 上的不可達性見
              `_orphan_diagram` 的 docstring。
        """
        alice_diagrams = [
            helpers.make_diagram(self.db, owner=self.alice, title=f"a{i}")
            for i in range(2)
        ]
        _ensure_hierarchy_schema(self.db)
        for i in range(2):
            _orphan_diagram(self.db, user_id=999_000 + i, title=f"orphan{i}")

        with self.assertRaises(HierarchyMigrationError) as ctx:
            migrate_hierarchy(self.db)
        self.db.rollback()

        self.assertIn("2", str(ctx.exception))
        self.assertIn("system_id IS NULL", str(ctx.exception))
        self.assertEqual(
            2,
            _count(
                self.db,
                "SELECT count(*) FROM user_diagrams WHERE system_id IS NULL",
            ),
        )
        for diagram in alice_diagrams:
            self.assertIsNotNone(_system_id_of(self.db, diagram.id))

    def test_counts_report_users_pairs_and_rewrites(self):
        """
        @purpose BR2.6：遷移必須回報三個計數，且它們的值要正確——部分失敗後
                 「做到哪」的判斷完全依賴它們。
        @given alice 有 2 張、bob 有 3 張 system_id 為空的圖
        @step 第一次執行遷移 | 回傳 (2, 2, 5)
        @step 第二次執行遷移 | 回傳 (2, 0, 0)
        @pass 兩次的三個計數逐一等於上述值
        @story US9.1
        @note 第二次的期望值是這個案例的重點：users_processed 仍為 2（重跑會
              走訪每位持有圖的使用者），但 default_pairs_created 與
              diagrams_assigned 必須歸零。若把 users_processed 也寫成 0，
              「有沒有走訪到」與「有沒有動到」就分不開了。
        """
        for i in range(2):
            helpers.make_diagram(self.db, owner=self.alice, title=f"a{i}")
        for i in range(3):
            helpers.make_diagram(self.db, owner=self.bob, title=f"b{i}")

        first = migrate_hierarchy(self.db)
        self.assertEqual(MigrationCounts(2, 2, 5), first)

        second = migrate_hierarchy(self.db)
        self.assertEqual(MigrationCounts(2, 0, 0), second)

    def test_rerun_creates_no_second_pair_and_reassigns_nothing(self):
        """
        @purpose BR2.2／U4-V5：重跑必須冪等——不得產生第二組預設專案／系統，
                 已掛好的圖不得被重新指派。
        @given alice 與 bob 各有 2 張圖，遷移已執行過一次
        @step 記下每張圖的 system_id 與兩表的列數 | 取得基準
        @step 再執行一次完整的遷移 | 完成且不拋例外
        @step 比對 projects／systems 的列數 | 仍是每位使用者各 1 列
        @step 逐張比對 system_id | 與第一次完全相同
        @pass 兩表列數不變、每張圖的 system_id 不變
        @story US9.1
        @note 只斷言「第二次沒有出錯」是恆真的——BR2.2 的
              violation_behaviour 逐字說那個失敗是「一個**看起來成功**的錯誤
              結果」。所以必須真的跑第二次，然後數列數並逐張比對 id。
              資料庫只擋得住「第二個預設 Project」；「第二**組**配對」靠的是
              BR2.5 先解析預設 Project 再以其 id 找 System 的順序，沒有約束
              擋它——所以這個案例是那條紀律唯一的自動化驗證。
        """
        diagrams = [
            helpers.make_diagram(self.db, owner=owner, title=f"{owner.username}{i}")
            for owner in (self.alice, self.bob)
            for i in range(2)
        ]
        migrate_hierarchy(self.db)
        baseline = {d.id: _system_id_of(self.db, d.id) for d in diagrams}
        self.assertTrue(all(value is not None for value in baseline.values()))

        migrate_hierarchy(self.db)

        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM projects"))
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM systems"))
        self.assertEqual(
            2,
            _count(
                self.db,
                "SELECT count(*) FROM projects WHERE is_default = :t",
                {"t": True},
            ),
        )
        self.assertEqual(
            2,
            _count(
                self.db,
                "SELECT count(*) FROM systems WHERE is_default = :t",
                {"t": True},
            ),
        )
        for diagram_id, system_id in baseline.items():
            with self.subTest(diagram_id=diagram_id):
                self.assertEqual(system_id, _system_id_of(self.db, diagram_id))

    def test_rerun_after_a_failure_completes_the_remaining_work(self):
        """
        @purpose S-8：逐使用者交易讓部分進度合法且可恢復——處置掉造成失敗的
                 原因之後重跑，未完成的被補上，已完成的不被推翻。
        @given alice 有 2 張圖、bob 有 1 張，另有 1 張孤兒圖使終檢必然失敗
        @step 第一次執行遷移 | 拋出 HierarchyMigrationError
        @step 檢查 alice 與 bob | 兩位都已各得一組預設專案／系統，三張圖都掛好
        @step 刪除那張孤兒圖 | 完成
        @step 重跑遷移 | 成功，回傳 (2, 0, 0)
        @step 比對三張圖的 system_id 與兩表列數 | 與第一次相同，沒有第二組
        @pass 第一次拋例外但進度保留；第二次成功且沒有重複建立或重新指派
        @story US9.1
        @note 這個案例與上一個的差別在於**失敗是真的發生過**：迴圈把兩位
              使用者 commit 掉之後，終檢才拋例外。若實作把整個遷移包在單一
              交易內，第一次的例外會把兩位的進度一併回滾，第二步的斷言就會紅
              ——那正是 S-8 要表達的性質。
        """
        alice_diagrams = [
            helpers.make_diagram(self.db, owner=self.alice, title=f"a{i}")
            for i in range(2)
        ]
        bob_diagram = helpers.make_diagram(self.db, owner=self.bob, title="b0")
        _ensure_hierarchy_schema(self.db)
        orphan_id = _orphan_diagram(self.db, user_id=999_001, title="orphan")

        with self.assertRaises(HierarchyMigrationError):
            migrate_hierarchy(self.db)
        self.db.rollback()

        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM projects"))
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM systems"))
        committed = {
            d.id: _system_id_of(self.db, d.id) for d in (*alice_diagrams, bob_diagram)
        }
        self.assertTrue(all(value is not None for value in committed.values()))

        self.db.execute(
            text("DELETE FROM user_diagrams WHERE id = :i"), {"i": orphan_id}
        )
        self.db.commit()

        counts = migrate_hierarchy(self.db)

        self.assertEqual(MigrationCounts(2, 0, 0), counts)
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM projects"))
        self.assertEqual(2, _count(self.db, "SELECT count(*) FROM systems"))
        for diagram_id, system_id in committed.items():
            with self.subTest(diagram_id=diagram_id):
                self.assertEqual(system_id, _system_id_of(self.db, diagram_id))

    def test_standalone_command_exits_non_zero_when_the_final_check_fails(self):
        """
        @purpose U4-V4／Q2=A：遷移是部署期的獨立指令，其失敗必須以**非零結束碼**
                 收場——掛在 init_db() 的啟動路徑上會變成一行日誌加一個看起來
                 正常啟動的服務。
        @given alice 有 1 張圖
        @step 在乾淨狀態下呼叫 main() | 回傳 0
        @step 插入一張孤兒圖使終檢必然失敗，再呼叫 main() | 回傳 1
        @step 以未知參數呼叫 main() | 回傳 2
        @pass 成功 0、終檢失敗 1、參數錯誤 2，三者互不相同
        @story US9.1
        @note 只斷言失敗回 1 是不夠的：一個永遠回 1 的實作也會通過。所以三個
              結束碼都斷言，且成功那一次排在前面。被 patch 的是 SessionLocal
              這個資料庫邊界，**不是遷移自己的邏輯**——unit-test-instructions
              §五逐字禁止後者。
        """
        import scripts.run_hierarchy_migration as command

        helpers.make_diagram(self.db, owner=self.alice, title="a0")

        with patch.object(command, "SessionLocal", lambda: self.db):
            self.assertEqual(0, command.main([]))

            _orphan_diagram(self.db, user_id=999_002, title="orphan")
            self.assertEqual(1, command.main([]))
            self.db.rollback()

            self.assertEqual(2, command.main(["--unknown"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
