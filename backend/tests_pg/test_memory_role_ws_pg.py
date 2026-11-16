"""WS／編排路徑的記憶存取實際以 `cloud360_memory` 連線——**只在真實 PostgreSQL**。

合併前必修第 52 列／`MB-48` 的未完成半邊（build-and-test 第三輪，2026-11-14）。`tests/test_memory_db_session_ws.py`
以替身證明「交給 facade 的是記憶 session 物件」；本檔證明的是替身證明不了的那一半：**那個 session 真的是以
`cloud360_memory` 角色連線、讀不到 `public`，而生產程式的寫入與預取在這個角色之下照樣成立**。

走的是生產程式本身：`database` 模組在匯入時依 `DATABASE_URL` ＋ `MEMORY_DB_PASSWORD` 建立兩個引擎；
`BrainGateway._write_episodic`／`_prefetch` 與 `WorkOrchestrator._write_procedure_memory` 以預設的
`MemoryFacade` 與 `database.SessionLocal` 執行，不注入任何記憶替身。以兩個引擎的 `before_cursor_execute`
事件記錄每一句 SQL 走的是哪一條連線。

怎麼跑
------

    cd backend && EMBEDDING_PROVIDER=stub \\
      DATABASE_URL='postgresql+psycopg://postgres:<pw>@localhost:5432/cloud360' \\
      MEMORY_DB_PASSWORD='<與 02-memory-role-password.sh 設定的相同>' \\
      python3 -m unittest tests_pg.test_memory_role_ws_pg -v

**前置條件**：已套用 `schema_rbac.sql`，且已以 `deploy/initdb/02-memory-role-password.sh` 為
`cloud360_memory` 設定密碼。**`MEMORY_DB_PASSWORD` 缺值時本檔大聲失敗**（同 `require_pg_url` 的理由：
跳過與通過在 `unittest` 輸出上無法分辨，記憶邊界的覆蓋會靜默消失而 CI 全綠）。
"""

from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError

from tests_pg import require_pg_url

FIXTURE_PREFIX = "__btfix3_memrole_pg__"


def _require_memory_password() -> str:
    password = os.environ.get("MEMORY_DB_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "tests_pg.test_memory_role_ws_pg 需要 MEMORY_DB_PASSWORD（與 02-memory-role-password.sh 設定的相同）；"
            "缺值時不跳過——跳過會讓記憶邊界的覆蓋靜默消失。"
        )
    return password


class MemoryRoleWsPathPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        require_pg_url()
        _require_memory_password()
        import database  # 匯入時依環境變數建立主引擎與記憶專用引擎

        cls.database = database
        if not database.memory_db_boundary_enabled():
            raise RuntimeError("database.memory_db_boundary_enabled() 為假：記憶專用引擎沒有建立")
        # 編排器以 ORM `User` 讀使用者，而 `users.authorization_status` 只由啟動補丁
        # `_ensure_j5_schema` 加上（`schema_rbac.sql` 沒有；見第三輪紀錄的範圍外發現）。
        # 跑生產啟動時的那兩支補丁（皆 IF NOT EXISTS、可重跑），不在測試裡另寫 DDL。
        database._ensure_a4_schema()
        database._ensure_j5_schema()
        cls.statements: list[tuple[str, str]] = []

        def _recorder(label):
            def _listen(conn, cursor, statement, parameters, context, executemany):
                cls.statements.append((label, statement))

            return _listen

        cls._listeners = [
            (database.engine, _recorder("main")),
            (database.memory_engine, _recorder("memory")),
        ]
        for engine, fn in cls._listeners:
            event.listen(engine, "before_cursor_execute", fn)

    @classmethod
    def tearDownClass(cls) -> None:
        for engine, fn in cls._listeners:
            event.remove(engine, "before_cursor_execute", fn)

    def setUp(self) -> None:
        env = mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        self.statements.clear()
        with self.database.engine.begin() as conn:
            self.user_id = conn.execute(
                text(
                    "INSERT INTO users (username, password_hash, role, is_active) "
                    "VALUES (:u, 'unused', 'Project_Architect', true) RETURNING id"
                ),
                {"u": f"{FIXTURE_PREFIX}{uuid.uuid4().hex[:12]}"},
            ).scalar_one()

    def tearDown(self) -> None:
        with self.database.engine.begin() as conn:
            conn.execute(text("DELETE FROM memory.memory_audit_events WHERE actor_user_id = :u"), {"u": self.user_id})
            conn.execute(text("DELETE FROM memory.memory_records WHERE owner_user_id = :u"), {"u": self.user_id})
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": self.user_id})

    def _memory_statements_on(self, label: str) -> list[str]:
        return [s for lab, s in self.statements if lab == label and "memory_records" in s]

    def test_memory_role_cannot_read_public_users(self):
        """
        @purpose 記憶專用連線的身分真的是 cloud360_memory，且讀不到 public.users（IAM 第二道邊界）
        @given 真實 PostgreSQL；MEMORY_DB_PASSWORD 已以 02-memory-role-password.sh 設定
        @step 以 database.get_memory_session() 查 current_user | cloud360_memory
        @step 同一連線 SELECT count(*) FROM public.users | permission denied（InsufficientPrivilege）
        @pass 兩步皆成立
        @story US4.4
        """
        db = self.database.get_memory_session()
        try:
            self.assertEqual(db.execute(text("SELECT current_user")).scalar_one(), "cloud360_memory")
            with self.assertRaises(ProgrammingError) as ctx:
                db.execute(text("SELECT count(*) FROM public.users")).scalar_one()
            self.assertIn("permission denied", str(ctx.exception).lower())
        finally:
            db.rollback()
            db.close()

    def test_cross_schema_join_executes_in_the_same_database(self):
        """
        @purpose AC4.5.2：記憶 schema 與既有 schema 在同一個 database，需要同時讀兩者的查詢可執行（跨 schema join 為原生能力）
        @given 真實 PostgreSQL；一位使用者與其一則記憶（以記憶專用連線寫入）
        @step 以主連線（擁有者帳號）執行 memory.memory_records JOIN public.users | 回 1 列、username 即該使用者
        @pass 查詢可執行且結果正確
        @story US4.5
        """
        from services.memory_facade import MemoryFacade, mint_principal

        principal = mint_principal(
            SimpleNamespace(id=self.user_id, role="Project_Architect", authorization_status="approved")
        )
        db = self.database.get_memory_session()
        try:
            MemoryFacade(db).write(principal, "semantic", f"{FIXTURE_PREFIX} 偏好東京區域")
        finally:
            db.close()
        with self.database.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT u.username, m.kind FROM memory.memory_records m "
                    "JOIN public.users u ON u.id = m.owner_user_id WHERE u.id = :u"
                ),
                {"u": self.user_id},
            ).all()
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(rows[0][0].startswith(FIXTURE_PREFIX))
        self.assertEqual(rows[0][1], "semantic")

    def test_gateway_and_orchestrator_write_and_prefetch_as_memory_role(self):
        """
        @purpose MB-48：閘道的情節寫入、編排器的程序寫入、閘道的預取，在真實 PG 上以 cloud360_memory 執行且照常成立
        @given 真實 PostgreSQL；EMBEDDING_PROVIDER=stub；一位啟用中的使用者；生產預設的 MemoryFacade 與 database.SessionLocal
        @step WorkOrchestrator._write_procedure_memory | memory_records 新增 1 列 kind=procedure、擁有者為該使用者
        @step BrainGateway._write_episodic | memory_records 新增 1 列 kind=episodic
        @step BrainGateway._prefetch（以程序記憶的內容為查詢） | turn.prefetch=hit、結果含該程序記憶
        @pass 三步成立；所有觸及 memory_records 的 SQL 都走記憶專用引擎，主引擎 0 句；主引擎只用來讀 users
        @story US4.4
        """
        from models import User
        from services import brain_gateway as G
        from services.memory_facade import mint_principal
        from services.work_orchestrator import WorkOrchestrator
        from services import work_orchestrator_rules as R

        orch = WorkOrchestrator(object(), object(), mint=mint_principal, user_model=User)
        ctx = SimpleNamespace(user_id=self.user_id, item_id="wi-pg", session_key="k", token="t", sink=None)
        item = {"capability": "cost-finops", "label": f"{FIXTURE_PREFIX} 估算月成本"}
        asyncio.run(orch._write_procedure_memory(ctx, item))
        procedure_content = f"{R.capability_name(item['capability'])}（{item['label']}）"

        gw = G.BrainGateway(store=None, routers={}, orchestrator=None, membership_facade_factory=lambda db: None)
        self.addCleanup(gw.shutdown)
        principal = mint_principal(
            SimpleNamespace(id=self.user_id, role="Project_Architect", authorization_status="approved")
        )
        asyncio.run(gw._write_episodic(principal, f"使用者：{FIXTURE_PREFIX} 畫一張架構圖", "t-pg"))
        turn = G.Turn(turn_id="t-pg-prefetch")
        prefetch = asyncio.run(gw._prefetch(principal, procedure_content, turn))
        # 生產程式的 SQL 到此為止；下面的驗證查詢本身走主引擎，不得算進去。
        on_memory = self._memory_statements_on("memory")
        on_main = self._memory_statements_on("main")
        main_read_users = any("users" in s for lab, s in self.statements if lab == "main")

        with self.database.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT kind, content FROM memory.memory_records WHERE owner_user_id = :u ORDER BY id"),
                {"u": self.user_id},
            ).all()
        self.assertEqual([kind for kind, _ in rows], ["procedure", "episodic"], rows)
        self.assertEqual(rows[0][1], procedure_content)
        self.assertEqual(turn.prefetch, "hit", f"預取應命中；實際 {turn.prefetch}")
        self.assertIn(procedure_content, [h.content for h in prefetch.hits])

        self.assertGreaterEqual(len(on_memory), 3, "寫入兩次與預取一次都應出現在記憶專用引擎")
        self.assertEqual(on_main, [], f"主引擎不得觸及 memory_records：{on_main[:2]}")
        self.assertTrue(main_read_users, "編排器應以主引擎讀 users")


if __name__ == "__main__":
    unittest.main()
