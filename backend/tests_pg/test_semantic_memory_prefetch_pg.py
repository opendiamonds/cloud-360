"""從對話寫入的語意記憶，下一輪的記憶預取讀得到——**只在真實 PostgreSQL**。

build-and-test 第二輪（2026-11-12）：**本階段新增、已核可 scope 尚未涵蓋的寫入路徑**（FR4.1 的語意
記憶至今沒有寫入者；回補項見 `construction/build-and-test/local-verify-fixes.md` 第二輪）。

閘道確認後呼叫的是 `MemoryFacade.write(principal, "semantic", content)`；下一輪 `_prefetch` 呼叫的是
`MemoryFacade.search(principal, query, kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT)`。`search` 的 SQL
在 SQLite 上編不出來（`memory_service.search_records` 的 docstring），故「寫得進去、預取讀得到、別人
讀不到」只能在這裡驗。本檔走的是**生產程式的那兩個呼叫**，參數取自 `brain_gateway` 的常數。

怎麼跑
------

    cd backend && EMBEDDING_PROVIDER=stub DATABASE_URL='postgresql+psycopg://postgres:<pw>@localhost:5432/cloud360' \\
      python3 -m unittest tests_pg.test_semantic_memory_prefetch_pg -v

**前置條件**：目標資料庫已套用 `schema_rbac.sql`（`memory` schema 與 `vector` extension）。
"""

from __future__ import annotations

import os
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from tests_pg import require_pg_url

from services.brain_gateway import PREFETCH_KINDS, PREFETCH_LIMIT
from services.memory_facade import MemoryFacade, mint_principal
from services.memory_types import VISIBILITY_SCOPE_OWNER

FIXTURE_PREFIX = "__btfix2_semantic_pg__"


class SemanticMemoryPrefetchPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        env = mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        self.user_ids: list[int] = []
        with self.engine.begin() as conn:
            for _ in range(2):
                self.user_ids.append(
                    conn.execute(
                        text(
                            "INSERT INTO users (username, password_hash, role, is_active) "
                            "VALUES (:u, 'unused', 'Project_Editor', true) RETURNING id"
                        ),
                        {"u": f"{FIXTURE_PREFIX}{uuid.uuid4().hex[:12]}"},
                    ).scalar_one()
                )

    def tearDown(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM memory.memory_audit_events WHERE actor_user_id = ANY(:u)"), {"u": self.user_ids}
            )
            conn.execute(
                text("DELETE FROM memory.memory_records WHERE owner_user_id = ANY(:o) AND content LIKE :p"),
                {"o": self.user_ids, "p": f"{FIXTURE_PREFIX}%"},
            )
            conn.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": self.user_ids})

    @staticmethod
    def _principal(user_id: int):
        return mint_principal(SimpleNamespace(id=user_id, role="Project_Editor", authorization_status="approved"))

    def test_written_semantic_memory_is_prefetched_for_owner_only(self):
        """
        @purpose 對話寫入的語意記憶，下一輪的預取（kinds=PREFETCH_KINDS）讀得到；別的使用者讀不到；可刪除。
        @given 真實 PostgreSQL（schema_rbac.sql）；EMBEDDING_PROVIDER=stub；兩個使用者
        @step 使用者甲 write(semantic, 偏好) | 回傳 owner=甲、scope=owner、embedding_model=stub-v1
        @step 甲以同一句 search(kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT) | 結果含該則
        @step 乙以同一句 search | 結果不含該則
        @step 甲 delete 後再 search | 不含該則
        @pass 寫入、預取可讀、他人不可讀、可刪除四項成立
        @story US4.1
        """
        owner, other = (self._principal(uid) for uid in self.user_ids)
        content = f"{FIXTURE_PREFIX} 我們團隊偏好把服務部署在 ap-northeast-1"
        with Session(self.engine) as db:
            view = MemoryFacade(db).write(owner, "semantic", content)
        self.assertEqual((view.owner_user_id, view.kind, view.visibility_scope), (self.user_ids[0], "semantic", VISIBILITY_SCOPE_OWNER))
        self.assertIn("semantic", PREFETCH_KINDS)
        with Session(self.engine) as db:
            mine = MemoryFacade(db).search(owner, content, kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT)
            theirs = MemoryFacade(db).search(other, content, kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT)
        self.assertIn(view.memory_id, [m.memory_id for m in mine])
        self.assertNotIn(view.memory_id, [m.memory_id for m in theirs])
        with Session(self.engine) as db:
            MemoryFacade(db).delete(owner, view.memory_id)
        with Session(self.engine) as db:
            after = MemoryFacade(db).search(owner, content, kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT)
        self.assertNotIn(view.memory_id, [m.memory_id for m in after])


if __name__ == "__main__":
    unittest.main()
