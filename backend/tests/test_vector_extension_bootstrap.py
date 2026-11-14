"""pgvector bootstrap 的順序、冪等與兩處同步（U1 `brain-infra`／`NFR6.2`、`NFR6.2a`）。

本檔守的是一條**二元判準**：`database._ensure_vector_extension()` 的呼叫必須出現在
`Base.metadata.create_all()` **之前**。這與本檔 `_ensure_*` 家族其餘六支的方向相反
（它們全在 `create_all()` 之後），所以照既有形狀實作就會放錯邊，而放錯邊的後果不是
「某個欄位沒補上」，是 **uvicorn 啟動失敗**：`vector` 型別不存在時，任何宣告
`vector(1024)` 欄位的表在 `create_all()` 裡就會以 `type "vector" does not exist`
失敗，而 `init_db()` 由 `backend/main.py` 的 startup 事件同步呼叫。

最後一個案例（`DEPLOY.md` 同步）把 `project.md ## Mandated` 的 schema↔deploy 同步
規則變成可執行的檢查，而不是只靠人記得——`DEPLOY.md` 是雙語分段文件，而「這支 SQL
會建立的物件」清單在中英兩半各有一份，blocking 規則的字面要求是兩處都補。

受測對象既無 HTTP 端點也無 UI route，故本檔不掛 `@api`／`@ui`；捏造一個假端點會
通過機械比對而無人察覺（同 `test_repo_contract_production_paths.py` 的既有先例）。
"""

from __future__ import annotations

import contextlib
import os
import re
import unittest
from pathlib import Path
from unittest import mock

# 必須早於任何 DB import：helpers 在 import 時 mock 掉 psycopg 並設好 sys.path。
from tests.helpers import close_session  # noqa: F401  (import for its side effects)

import database
from models import Base, RolePermission, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = REPO_ROOT / "schema_rbac.sql"
DEPLOY_MD = REPO_ROOT / "DEPLOY.md"

# 兩份檔都必須提到它。用 SQL 敘述本身當關鍵字，而不是「pgvector」這種泛稱——
# 泛稱可以在一句無關的說明裡湊巧出現，敘述不會。
EXTENSION_STATEMENT = "CREATE EXTENSION IF NOT EXISTS vector"

# `DEPLOY.md` 的英文半部由這個標題起算（`team.md` 禁止**新增**雙語分段，但這一份
# repo 根目錄文件的既有分段不在本單元的處置範圍內，見 cicd-pipeline.md §五 的
# 「DEPLOY.md 是雙語分段文件」專節）。
ENGLISH_HALF_MARKER = "## English Version"


def _sqlite_engine():
    """與 `tests/helpers.py` 同形的 in-memory engine（StaticPool 共用同一個 DB）。"""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


class EnsureVectorExtensionTest(unittest.TestCase):
    def test_function_exists_and_is_callable(self):
        """案例 1：承載者存在。名字錯或被改名時，下面每一個案例都失去意義。"""
        self.assertTrue(hasattr(database, "_ensure_vector_extension"))
        self.assertTrue(callable(database._ensure_vector_extension))

    def test_runs_before_create_all(self):
        """案例 2（核心）：呼叫順序。

        以**共用的 parent mock** 攔截兩者，`mock_calls` 保序，所以順序是被觀察到
        的事實而不是時間戳比較。六支既有 `_ensure_*` 一併攔下，確認它們仍在
        `create_all` 之後——否則「順序對了」可能只是因為別的東西也被搬動了。
        """
        parent = mock.Mock()
        session = mock.MagicMock()
        # init_db 的 DB 區段不是本案例的受測對象。讓第一個 query 就拋，讓
        # init_db 自己的 try/except 吃掉它——那段在 `db = SessionLocal()` 之後，
        # 所以不會逃出函式。
        session.query.side_effect = RuntimeError("DB section not under test")

        patches = [
            mock.patch.object(database, "_ensure_vector_extension", parent.ensure_vector),
            mock.patch.object(Base.metadata, "create_all", parent.create_all),
            mock.patch.object(database, "_ensure_a4_schema", parent.a4),
            mock.patch.object(database, "_ensure_j5_schema", parent.j5),
            mock.patch.object(database, "_ensure_a3_schema", parent.a3),
            mock.patch.object(database, "_ensure_cost_schema", parent.cost),
            mock.patch.object(database, "_ensure_estimate_intake_schema", parent.intake),
            mock.patch.object(database, "_ensure_last_activity_schema", parent.activity),
            mock.patch.object(database, "SessionLocal", mock.MagicMock(return_value=session)),
            mock.patch.object(database, "logger", mock.MagicMock()),
        ]
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            database.init_db()

        order = [call[0] for call in parent.mock_calls]
        self.assertIn("ensure_vector", order)
        self.assertIn("create_all", order)
        self.assertLess(
            order.index("ensure_vector"),
            order.index("create_all"),
            "_ensure_vector_extension() 必須在 Base.metadata.create_all() 之前呼叫："
            f"實際順序為 {order}",
        )
        for name in ("a4", "j5", "a3", "cost", "intake", "activity"):
            self.assertGreater(
                order.index(name),
                order.index("create_all"),
                f"_ensure_{name} 應維持在 create_all 之後（本單元不改它們的位置）",
            )

    def test_statement_is_idempotent_and_guarded(self):
        """案例 3：冪等。連呼兩次無例外，且兩次送出的 SQL 都帶 IF NOT EXISTS。"""
        fake_engine = mock.MagicMock()
        conn = fake_engine.begin.return_value.__enter__.return_value

        with mock.patch.object(database, "engine", fake_engine):
            database._ensure_vector_extension()
            database._ensure_vector_extension()

        self.assertEqual(conn.execute.call_count, 2)
        for call in conn.execute.call_args_list:
            sql = str(call.args[0])
            self.assertIn("IF NOT EXISTS", sql.upper())
            self.assertRegex(sql, r"\bvector\b")

    def test_swallows_failure_so_startup_survives_a_server_without_pgvector(self):
        """案例 3b：擴充建不起來時只記 warning，不把例外往上拋。

        沒有這個性質，案例 4（SQLite 下 `init_db()` 可執行）就不成立，而正式
        環境上的失敗訊息也會從 `create_all()` 的 `type "vector" does not exist`
        （指出缺什麼）退化成一個轉了一層的擴充錯誤。
        """
        fake_engine = mock.MagicMock()
        fake_engine.begin.side_effect = RuntimeError("could not open extension control file")
        logger = mock.MagicMock()

        with mock.patch.object(database, "engine", fake_engine), mock.patch.object(
            database, "logger", logger
        ):
            database._ensure_vector_extension()  # 不得拋出

        self.assertTrue(
            logger.warning.called,
            "吞掉例外時必須留下 warning——靜默失敗不可接受（construction.md）",
        )

    def test_init_db_runs_under_the_sqlite_test_environment(self):
        """案例 4：in-memory SQLite 下 `init_db()` 走得完，且真的建出東西。

        `CREATE EXTENSION` 在 SQLite 是語法錯誤，所以這個案例同時證明案例 3b 的
        吞例外行為在真實呼叫鏈上成立。斷言「建出了什麼」而不只是「沒有拋例外」——
        `init_db()` 的 DB 區段自帶 try/except，只斷言不拋會讓本案例空洞通過。
        """
        engine = _sqlite_engine()
        SessionLocal = sessionmaker(bind=engine)

        with mock.patch.object(database, "engine", engine), mock.patch.object(
            database, "SessionLocal", SessionLocal
        ), mock.patch.object(database, "logger", mock.MagicMock()), mock.patch.dict(
            os.environ, {"APP_ENV": "test"}, clear=False
        ):
            database.init_db()

        session = SessionLocal()
        try:
            admin = session.query(User).filter(User.username == "admin").first()
            self.assertIsNotNone(admin, "init_db 應在 APP_ENV=test 下建立 bootstrap admin")
            self.assertGreater(
                session.query(RolePermission).count(),
                0,
                "init_db 應 seed role_permissions；為 0 代表流程在 seed 之前就被吃掉了",
            )
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()


class SchemaAndDeployDocSyncTest(unittest.TestCase):
    def test_schema_rbac_declares_the_extension_before_any_vector_column(self):
        """案例 5：`schema_rbac.sql` 宣告擴充，且在任何 `vector(...)` 欄位之前。

        該檔是**單一交易**（`BEGIN` … `COMMIT`）：順序錯了不是「少一個擴充」，
        是整個交易中止、一張表都建不出來。`vector(` 欄位在本單元落地時尚不存在
        （由 `U5 memory-data` 帶入），所以行號比較現在是空集合上的真——它存在的
        理由是 `U5` 落地那一刻就要能擋。
        """
        lines = SCHEMA_SQL.read_text(encoding="utf-8").splitlines()

        ext_lines = [i for i, line in enumerate(lines) if EXTENSION_STATEMENT in line
                     and not line.lstrip().startswith("--")]
        self.assertTrue(
            ext_lines,
            f"schema_rbac.sql 必須含一條未被註解的 `{EXTENSION_STATEMENT};`",
        )
        ext_line = min(ext_lines)

        begin_lines = [i for i, line in enumerate(lines) if line.strip().upper() == "BEGIN;"]
        self.assertTrue(begin_lines, "schema_rbac.sql 應以 BEGIN; 開啟單一交易")
        self.assertGreater(
            ext_line, min(begin_lines), "CREATE EXTENSION 必須在 BEGIN; 之後"
        )

        column_pattern = re.compile(r"\bvector\s*\(\s*\d+\s*\)", re.IGNORECASE)
        vector_columns = [
            i
            for i, line in enumerate(lines)
            if column_pattern.search(line) and not line.lstrip().startswith("--")
        ]
        if vector_columns:
            self.assertLess(
                ext_line,
                min(vector_columns),
                "CREATE EXTENSION 的行號必須小於任何 vector(N) 欄位宣告的行號",
            )

    def test_deploy_md_documents_the_extension_in_both_halves(self):
        """案例 6（blocking 同步）：`schema_rbac.sql` 提到擴充 ⇒ `DEPLOY.md` 也要。

        `project.md ## Mandated` 要求 schema 變更時同步更新 `DEPLOY.md` 的
        「這支 SQL 會建立的表／欄位」表。`DEPLOY.md` 有中英兩個半部，而兩半各有
        一份那張清單，所以字面要求是**兩處都補**。這個案例把「記得改文件」從
        一條靠人遵守的規則變成一條會紅燈的檢查。
        """
        schema_text = SCHEMA_SQL.read_text(encoding="utf-8")
        if EXTENSION_STATEMENT not in schema_text:
            self.skipTest("schema_rbac.sql 未宣告 vector 擴充，同步義務不成立")

        deploy_text = DEPLOY_MD.read_text(encoding="utf-8")
        self.assertIn(
            ENGLISH_HALF_MARKER,
            deploy_text,
            "DEPLOY.md 的英文半部標題不見了；本案例的兩半切分失去依據，請重新確認",
        )
        chinese_half, english_half = deploy_text.split(ENGLISH_HALF_MARKER, 1)

        needle = EXTENSION_STATEMENT.lower()
        # assertIn 會把整份文件印進失敗訊息（500 行），淹掉真正的訊息；用
        # assertTrue 讓失敗輸出只剩下「哪一半缺、該補什麼」。
        self.assertTrue(
            needle in chinese_half.lower(),
            "DEPLOY.md 的中文半部（§2.2「這支 SQL 會建立的表／欄位」）未記載 "
            f"`{EXTENSION_STATEMENT}`，而 schema_rbac.sql 已宣告它。"
            "project.md ## Mandated 的 schema↔deploy 同步是 blocking 規則。",
        )
        self.assertTrue(
            needle in english_half.lower(),
            "DEPLOY.md 的英文半部（### Database）未記載 "
            f"`{EXTENSION_STATEMENT}`。該節同樣在列「這支 SQL 會建立的物件」，"
            "所以 blocking 規則的字面要求是兩處都補。",
        )


if __name__ == "__main__":
    unittest.main()
