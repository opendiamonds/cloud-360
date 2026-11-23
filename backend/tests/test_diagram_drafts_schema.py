"""261116-brain-create-diagram U1 diagram-drafts：草稿狀態欄位的資料模型與遷移。

追溯：FR6.1（草稿／正式兩種狀態）、FR6.5（既有圖一律為正式、遷移冪等）、契約 C3。
本檔只測資料層（遷移與約束），不經 HTTP，故無 `@api`／`@ui`。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import unittest
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests import helpers
from models import DIAGRAM_STATUS_DRAFT, DIAGRAM_STATUS_READY, User, UserDiagram
from services.hierarchy_migration import _ensure_hierarchy_schema

SCHEMA_RBAC_SQL = Path(__file__).resolve().parents[2] / "schema_rbac.sql"


def _rebuild_user_diagrams_without_status(db) -> None:
    """重建一張「部署本 intent 之前」的 user_diagrams：有 system_id（帶外鍵）、沒有 status。

    `make_session()` 依 ORM 建表，已含 status，所以要測「既有資料庫補欄位」
    必須整表重建；SQLite 無法 DROP 帶約束的欄位。
    """
    db.execute(text("DROP TABLE IF EXISTS diagram_change_records"))
    db.execute(text("DROP TABLE user_diagrams"))
    db.execute(
        text(
            "CREATE TABLE user_diagrams ("
            " id INTEGER NOT NULL PRIMARY KEY,"
            " user_id INTEGER NOT NULL REFERENCES users (id),"
            " title VARCHAR NOT NULL,"
            " xml_data TEXT NOT NULL,"
            " updated_at DATETIME,"
            " system_id INTEGER REFERENCES systems (id) ON DELETE RESTRICT"
            ")"
        )
    )
    db.commit()


class TestDiagramStatusMigration(unittest.TestCase):
    def setUp(self):
        self.db = helpers.make_session()
        _ensure_hierarchy_schema(self.db)
        self.user = User(username="drafts-owner", password_hash="x", role="Project_Architect")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        helpers.close_session(self.db)

    def _status_rows(self):
        return self.db.execute(
            text("SELECT title, status FROM user_diagrams ORDER BY id")
        ).fetchall()

    def test_existing_diagrams_become_ready_after_migration(self):
        """
        @purpose 已部署的資料庫補上狀態欄位後，所有既有圖都必須是正式（FR6.5）；
                 若預設值錯成 draft，既有圖會從評核、分享、專案頁計數中消失。
        @given 一張不含 status 欄位的 user_diagrams，其中已有兩張圖
        @step 執行 _ensure_hierarchy_schema | user_diagrams 出現 status 欄位
        @step 讀回兩張圖的 status | 兩張皆為 ready
        @pass 欄位存在且既有列全為 ready
        @story FR6.5
        """
        _rebuild_user_diagrams_without_status(self.db)
        for title in ("舊圖一", "舊圖二"):
            self.db.execute(
                text(
                    "INSERT INTO user_diagrams (user_id, title, xml_data) "
                    "VALUES (:u, :t, '<mxGraphModel/>')"
                ),
                {"u": self.user.id, "t": title},
            )
        self.db.commit()

        _ensure_hierarchy_schema(self.db)

        columns = {c["name"] for c in inspect(self.db.get_bind()).get_columns("user_diagrams")}
        self.assertIn("status", columns)
        self.assertEqual(
            [("舊圖一", "ready"), ("舊圖二", "ready")], [tuple(r) for r in self._status_rows()]
        )

    def test_rerunning_the_migration_is_idempotent_and_keeps_drafts(self):
        """
        @purpose 遷移可重跑：第二次執行不得報錯，也不得把已存在的草稿改回正式。
        @given 已補過欄位的資料庫，含一張 draft、一張 ready
        @step 再執行兩次 _ensure_hierarchy_schema | 不拋例外
        @step 讀回兩張圖的狀態 | 仍為 draft 與 ready
        @pass 狀態完全未變
        @story FR6.5
        """
        _rebuild_user_diagrams_without_status(self.db)
        _ensure_hierarchy_schema(self.db)
        self.db.execute(
            text(
                "INSERT INTO user_diagrams (user_id, title, xml_data, status) "
                "VALUES (:u, '草稿', '<x/>', 'draft'), (:u, '正式', '<x/>', 'ready')"
            ),
            {"u": self.user.id},
        )
        self.db.commit()

        _ensure_hierarchy_schema(self.db)
        _ensure_hierarchy_schema(self.db)

        self.assertEqual(
            [("草稿", "draft"), ("正式", "ready")], [tuple(r) for r in self._status_rows()]
        )

    def test_check_constraint_rejects_unknown_status(self):
        """
        @purpose 狀態是封閉列舉；遷移補上的欄位必須帶 CHECK，否則拼錯的值
                 （例如 'Draft'）會讓該圖既不被排除也不被計入。
        @given 經遷移補上 status 的資料庫
        @step 插入 status='published' 的圖 | 被 IntegrityError 拒絕
        @pass 拋出 IntegrityError
        @story FR6.1
        """
        _rebuild_user_diagrams_without_status(self.db)
        _ensure_hierarchy_schema(self.db)
        with self.assertRaises(IntegrityError):
            self.db.execute(
                text(
                    "INSERT INTO user_diagrams (user_id, title, xml_data, status) "
                    "VALUES (:u, '壞值', '<x/>', 'published')"
                ),
                {"u": self.user.id},
            )
            self.db.commit()
        self.db.rollback()

    def test_orm_defaults_to_ready_and_accepts_draft(self):
        """
        @purpose 不帶狀態建立的圖必須是正式（既有三條建圖路徑都不知道這一欄）；
                 明示 draft 時必須存成 draft。
        @given ORM 建立的資料庫
        @step 以 ORM 建一張不帶 status 的圖與一張 status=draft 的圖 | 兩張都寫入成功
        @pass 前者為 ready、後者為 draft；ORM 的 CHECK 也擋下非法值
        @story FR6.1、FR6.5
        """
        plain = UserDiagram(user_id=self.user.id, title="一般", xml_data="<x/>")
        draft = UserDiagram(
            user_id=self.user.id, title="草稿", xml_data="<x/>", status=DIAGRAM_STATUS_DRAFT
        )
        self.db.add_all([plain, draft])
        self.db.commit()
        self.assertEqual(DIAGRAM_STATUS_READY, plain.status)
        self.assertEqual(DIAGRAM_STATUS_DRAFT, draft.status)

        self.db.add(UserDiagram(user_id=self.user.id, title="壞", xml_data="<x/>", status="Draft"))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_schema_rbac_sql_declares_the_same_column_and_check(self):
        """
        @purpose DDL 存在兩處（schema_rbac.sql 與遷移模組）；本案例鎖住兩處都有
                 同一個欄位、預設與約束名稱，避免只改一邊（team.md 單一真實來源）。
        @given repo 根的 schema_rbac.sql
        @step 搜尋加欄敘述與約束 | 皆存在且預設為 ready
        @pass 兩個樣式都命中
        @story FR6.1
        """
        sql = SCHEMA_RBAC_SQL.read_text(encoding="utf-8")
        self.assertRegex(
            sql,
            r"ALTER TABLE user_diagrams\s+ADD COLUMN IF NOT EXISTS status VARCHAR\(16\) "
            r"NOT NULL DEFAULT 'ready'",
        )
        self.assertRegex(
            sql, r"ADD CONSTRAINT ck_user_diagrams_status\s+CHECK \(status IN \('draft', 'ready'\)\)"
        )


class TestDiagramStatusStartupPatch(unittest.TestCase):
    """修訂 1（審查 R-01／R-02 Major）：backend 啟動時只補 `user_diagrams.status`。

    `database._ensure_diagram_status_schema` 掛在 `init_db` 上，取代「部署前人工跑
    run_hierarchy_migration.py」的唯一補法。本類別鎖住三件事：既有圖補成 ready、
    可重跑、**不跑整套階層遷移**（不改寫 system_id、不建專案）。
    """

    def setUp(self):
        self.db = helpers.make_session()
        _ensure_hierarchy_schema(self.db)
        self.user = User(username="startup-owner", password_hash="x", role="Project_Architect")
        self.db.add(self.user)
        self.db.commit()
        _rebuild_user_diagrams_without_status(self.db)
        for title in ("舊圖一", "舊圖二"):
            self.db.execute(
                text(
                    "INSERT INTO user_diagrams (user_id, title, xml_data) "
                    "VALUES (:u, :t, '<mxGraphModel/>')"
                ),
                {"u": self.user.id, "t": title},
            )
        self.db.commit()

    def tearDown(self):
        helpers.close_session(self.db)

    def _rows(self):
        return [
            tuple(r)
            for r in self.db.execute(
                text("SELECT title, status, system_id FROM user_diagrams ORDER BY id")
            ).fetchall()
        ]

    def test_startup_patch_marks_existing_diagrams_ready(self):
        """
        @purpose 舊 volume 上新版 backend 啟動時要自行補上 status，否則讀圖端點全數 500
                 （ORM 已映射該欄），而部署後探針只打登入、抓不到。
        @given 一張不含 status 欄位的 user_diagrams，其中已有兩張圖
        @step 執行 database._ensure_diagram_status_schema | user_diagrams 出現 status 欄位
        @step 讀回兩張圖 | 皆為 ready
        @pass 欄位存在且既有列全為 ready
        @story FR6.5
        """
        import database

        database._ensure_diagram_status_schema(bind=self.db.get_bind())

        columns = {c["name"] for c in inspect(self.db.get_bind()).get_columns("user_diagrams")}
        self.assertIn("status", columns)
        self.assertEqual(["ready", "ready"], [r[1] for r in self._rows()])

    def test_startup_patch_is_idempotent_and_keeps_drafts(self):
        """
        @purpose 啟動補丁每次啟動都會執行；第二次起必須是無操作，且不得把草稿改回正式。
        @given 已補過欄位、其中一張改為 draft 的資料庫
        @step 再執行兩次 _ensure_diagram_status_schema | 不拋例外
        @step 讀回狀態 | draft 仍為 draft
        @pass 狀態完全未變
        @story FR6.5
        """
        import database

        bind = self.db.get_bind()
        database._ensure_diagram_status_schema(bind=bind)
        self.db.execute(text("UPDATE user_diagrams SET status = 'draft' WHERE title = '舊圖二'"))
        self.db.commit()

        database._ensure_diagram_status_schema(bind=bind)
        database._ensure_diagram_status_schema(bind=bind)

        self.assertEqual(["ready", "draft"], [r[1] for r in self._rows()])

    def test_startup_patch_does_not_run_the_hierarchy_migration(self):
        """
        @purpose 啟動補丁只補一欄；整套階層遷移會把 system_id 為空的圖重新指派到預設系統、
                 並建立預設專案，那不是啟動時該發生的事（使用者裁決：只補欄位）。
        @given 兩張 system_id 為空、尚無 status 的圖，且沒有任何專案
        @step 執行 _ensure_diagram_status_schema | 補上 status
        @step 讀回 system_id 與專案數 | system_id 仍為空、專案數仍為 0
        @pass 只有 status 被補上，其餘資料未動
        @story FR6.5
        """
        import database

        database._ensure_diagram_status_schema(bind=self.db.get_bind())

        self.assertEqual([None, None], [r[2] for r in self._rows()])
        self.assertEqual(0, self.db.execute(text("SELECT COUNT(*) FROM projects")).scalar())

    def test_init_db_calls_the_status_patch(self):
        """
        @purpose 補丁必須真的掛在啟動路徑上；只寫函式不呼叫，等於回到只靠文件。
        @given init_db 的其他步驟全換成替身
        @step 呼叫 database.init_db | _ensure_diagram_status_schema 被呼叫一次
        @pass 呼叫次數為 1
        @story FR6.5
        """
        from unittest import mock

        import database

        names = [
            "_ensure_vector_extension",
            "_ensure_a4_schema",
            "_ensure_j5_schema",
            "_ensure_a3_schema",
            "_ensure_cost_schema",
            "_ensure_estimate_intake_schema",
            "_ensure_last_activity_schema",
            "_ensure_iac_draft_schema",
        ]
        patches = [mock.patch.object(database, n) for n in names]
        patches.append(mock.patch.object(database.Base.metadata, "create_all"))
        patches.append(mock.patch.object(database, "SessionLocal", side_effect=RuntimeError("stop")))
        status_patch = mock.patch.object(database, "_ensure_diagram_status_schema")
        for p in patches:
            p.start()
        try:
            with status_patch as called:
                with self.assertRaises(RuntimeError):
                    database.init_db()
            called.assert_called_once_with()
        finally:
            for p in patches:
                p.stop()

    def test_startup_patch_failure_propagates_instead_of_being_swallowed(self):
        """
        @purpose 補欄位失敗時必須往外拋、讓啟動失敗；其他 `_ensure_*` 都吞成 warning，
                 若此函式被改成同樣吞掉，服務會帶著「讀圖必 500」的狀態啟動，而部署探針
                 只打登入、抓不到——DEPLOY.md 與 LOCAL-DEV.md 的回復段都依賴這個失敗。
        @given 一張不含 status 欄位的 user_diagrams，且補欄位的 DDL 會失敗
        @step 執行 database._ensure_diagram_status_schema | 拋出 DDL 的原始例外
        @step 讀回欄位 | user_diagrams 仍無 status（交易已回滾）
        @pass 例外原樣往外拋，且欄位未被補上
        @story FR6.5
        """
        from unittest import mock

        import database

        boom = RuntimeError("ddl failed")
        with mock.patch(
            "services.hierarchy_migration._ensure_diagram_status_column", side_effect=boom
        ):
            with self.assertRaises(RuntimeError) as ctx:
                database._ensure_diagram_status_schema(bind=self.db.get_bind())
        self.assertIs(boom, ctx.exception)

        columns = {c["name"] for c in inspect(self.db.get_bind()).get_columns("user_diagrams")}
        self.assertNotIn("status", columns)

    def test_init_db_fails_when_the_status_patch_fails(self):
        """
        @purpose 補丁的失敗必須傳到 init_db 之外（main.py 的 startup 事件），不得在
                 init_db 內被攔下；否則「失敗會往外拋」只在函式層成立、啟動照樣成功。
        @given init_db 的其他步驟全換成替身，且 status 補丁拋出例外
        @step 呼叫 database.init_db | 拋出同一個例外，且之後的種子步驟（SessionLocal）未執行
        @pass 例外原樣往外拋、SessionLocal 呼叫次數為 0
        @story FR6.5
        """
        from unittest import mock

        import database

        names = [
            "_ensure_vector_extension",
            "_ensure_a4_schema",
            "_ensure_j5_schema",
            "_ensure_a3_schema",
            "_ensure_cost_schema",
            "_ensure_estimate_intake_schema",
            "_ensure_last_activity_schema",
            "_ensure_iac_draft_schema",
        ]
        patches = [mock.patch.object(database, n) for n in names]
        patches.append(mock.patch.object(database.Base.metadata, "create_all"))
        boom = RuntimeError("status column missing")
        for p in patches:
            p.start()
        try:
            with mock.patch.object(
                database, "_ensure_diagram_status_schema", side_effect=boom
            ), mock.patch.object(database, "SessionLocal") as session_local:
                with self.assertRaises(RuntimeError) as ctx:
                    database.init_db()
            self.assertIs(boom, ctx.exception)
            session_local.assert_not_called()
        finally:
            for p in patches:
                p.stop()


if __name__ == "__main__":
    unittest.main()
