"""`U8 memory-service` 的向量寫入／檢索與併發刪除——**只在真實 PostgreSQL**。

對應 `construction/functional-design/merge-blockers.md` 第 22 項的 (b)、(c)
（`code-generation-plan.md` 第十一節的 Step 13、Step 14）。

為什麼這兩組斷言只能在這裡
==========================

**`V1`（Step 13）**：`memory_service.create_record` 在 SQLite 上**刻意跳過**
`UPDATE memory.memory_records SET embedding = CAST(:embedding AS vector)`
（SQLite 沒有 `embedding` 欄位，`_supports_vector` 以 dialect 判斷），而
`search_records` 的 `SEARCH_SQL` 在 SQLite 上**編不出來**。所以向量寫入一旦
失效，每一列的 `embedding` 都是 NULL，`SEARCH_SQL` 的 `embedding IS NOT NULL`
把它們全部濾掉，**檢索永遠回空而不報任何錯**——`backend/tests/` 的 50 個記憶
測試照樣全綠。`verify_memory_schema.sql` 的 `S15` 也驗不到它：那裡的 fixture
是直接 `INSERT` 向量，不經 `create_record`。本檔走的是**生產程式的那一條路**。

**`D1`／`D2`（Step 14）**：兩個 session 各自取到同一列後刪除。舊實作的
`db.delete(record)` 在第二次刪除時影響 0 列，SQLAlchemy 只發一個警告而不報錯，
於是第二筆 `deleted_by_user` 稽核照樣寫入（審查 review-03 實測稽核列數為 2），
違反 `BR4.3`（重複刪除不得產生稽核）。`D2` 需要兩條**真正並行**的連線與真實
的列鎖，而 in-memory SQLite 的整庫鎖之下兩個「交易」本來就不會並行——寫在
`backend/tests/` 會綠燈而什麼都沒驗到（理由全文見 `tests_pg/__init__.py`）。

`D2` 的交錯以 barrier 釘住，不用 `sleep`
=======================================

兩個執行緒各自在「即將對 `memory.memory_records` 送出 `DELETE`」的那一刻
（連線層的 `before_cursor_execute` 事件）於同一個 barrier 會合，然後同時送出。
先拿到列鎖的那一個刪除並 commit；另一個的 `DELETE` 被列鎖擋住，鎖釋放後
**重新評估 WHERE** 得 0 列——正確實作據此拋 `MemoryNotFound` 且不寫稽核。
兩方都到得了 barrier（兩者都還沒送出任何刪除），故 barrier 必然成立；
`Barrier.wait(timeout)` 是有界的條件等待。形狀沿用
`test_requirement_field_pg.py` 的 `G3`。

怎麼跑
------

    cd backend && DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/cloud360' \\
      python3 -m unittest tests_pg.test_memory_service_pg -v

**前置條件**：目標資料庫已套用 `schema_rbac.sql`（`I)` 區塊的 `memory` schema
與 `vector` extension）。
"""

from __future__ import annotations

import threading
import unittest
import uuid

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from tests_pg import require_pg_url

import services.memory_service as memory_service
from services.memory_errors import MemoryNotFound
from services.memory_ranking import rank_candidates
from services.memory_types import AUDIT_ACTION_DELETED_BY_USER

#: fixture 的 `content` 前綴。清理一律依它與本檔建立的 id，**不得** TRUNCATE
#: 或用無 WHERE 的 DELETE（`unit-test-instructions.md §七`）。
FIXTURE_PREFIX = "__u8_service_pg__"
DIMENSIONS = 1024
BARRIER_TIMEOUT_S = 15.0
JOIN_TIMEOUT_S = 60.0


def unit_vector(*hot_indices: int) -> list[float]:
    """1024 維、在指定位置為 1 的向量。cosine 距離只看方向，故不必正規化。"""
    values = [0.0] * DIMENSIONS
    for index in hot_indices:
        values[index] = 1.0
    return values


class MemoryServicePostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())
        with cls.engine.connect() as conn:
            udt = conn.execute(
                text(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_schema = 'memory' "
                    "AND table_name = 'memory_records' "
                    "AND column_name = 'embedding'"
                )
            ).scalar()
        if udt != "vector":
            raise RuntimeError(
                "前置條件不足：memory.memory_records.embedding 應為 pgvector 的 "
                f"vector 型別，實際 {udt!r}。請先對目標資料庫套用 schema_rbac.sql"
                "（CI 的 concurrency job 會做這件事；本機見 LOCAL-DEV.md 第 2 節）"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        # 每個測試一個專屬的 embedding_model：SEARCH_SQL 以它過濾，故檢索結果
        # 只可能是本測試建立的列，與資料庫裡任何其他資料無關。
        self.embedding_model = f"u8pg-{uuid.uuid4().hex[:16]}"
        with self.engine.begin() as conn:
            # 以 raw SQL 建使用者：理由同 test_membership_concurrency._user
            # （只套過 DDL 的 CI 資料庫上，ORM 的 User 比 users 表多一欄）。
            self.owner_id = conn.execute(
                text(
                    "INSERT INTO users (username, password_hash, role, is_active) "
                    "VALUES (:u, 'unused', 'Project_Editor', true) RETURNING id"
                ),
                {"u": f"{FIXTURE_PREFIX}{uuid.uuid4().hex[:12]}"},
            ).scalar_one()
        self.memory_ids: list[int] = []

    def tearDown(self) -> None:
        with self.engine.begin() as conn:
            if self.memory_ids:
                conn.execute(
                    text(
                        "DELETE FROM memory.memory_audit_events "
                        "WHERE memory_id = ANY(:ids) AND actor_user_id = :actor"
                    ),
                    {"ids": self.memory_ids, "actor": self.owner_id},
                )
            conn.execute(
                text(
                    "DELETE FROM memory.memory_records "
                    "WHERE owner_user_id = :o AND content LIKE :p"
                ),
                {"o": self.owner_id, "p": f"{FIXTURE_PREFIX}%"},
            )
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": self.owner_id})

    # -- helpers ------------------------------------------------------------

    def _create(self, label: str, embedding) -> int:
        """經**生產用的** `create_record` 寫入，不是直接 INSERT。"""
        with Session(self.engine) as db:
            record = memory_service.create_record(
                db,
                owner_user_id=self.owner_id,
                kind="semantic",
                content=f"{FIXTURE_PREFIX}{label}",
                embedding_model=self.embedding_model,
                embedding=embedding,
            )
            self.memory_ids.append(record.id)
            return record.id

    def _embedding_is_set(self, memory_id: int) -> bool:
        with self.engine.connect() as conn:
            return bool(
                conn.execute(
                    text(
                        "SELECT embedding IS NOT NULL FROM memory.memory_records "
                        "WHERE id = :id"
                    ),
                    {"id": memory_id},
                ).scalar_one()
            )

    def _deletion_audits(self, memory_id: int) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                text(
                    "SELECT count(*) FROM memory.memory_audit_events "
                    "WHERE memory_id = :id AND action = :a"
                ),
                {"id": memory_id, "a": AUDIT_ACTION_DELETED_BY_USER},
            ).scalar_one()

    def _record_exists(self, memory_id: int) -> bool:
        with self.engine.connect() as conn:
            return bool(
                conn.execute(
                    text("SELECT count(*) FROM memory.memory_records WHERE id = :id"),
                    {"id": memory_id},
                ).scalar_one()
            )

    # -- V1：Step 13，向量寫入 → 檢索（merge-blockers #22 (b)）-----------------

    def test_V1_create_record_writes_embedding_and_search_finds_it(self):
        """`create_record` → `search_records`：寫進向量，且檢索查得到、依距離排序。

        三筆的寫入順序刻意是「遠、中、近」，使「照寫入順序回傳」的實作也會紅。
        最後一段把結果照 `MemoryFacade.search` 的組合方式送進
        `scored_candidates` → `rank_candidates`，在**真實的 `<=>` 距離**上再驗一次
        取負號（Step 12 的單元測試驗的是手造距離）。
        """
        far = self._create("far", unit_vector(1))
        mid = self._create("mid", unit_vector(0, 1))
        near = self._create("near", unit_vector(0))

        for memory_id in (far, mid, near):
            self.assertTrue(
                self._embedding_is_set(memory_id),
                f"id={memory_id} 的 embedding 是 NULL——create_record 的 "
                "UPDATE ... SET embedding 沒有生效，檢索會永遠回空且不報錯",
            )

        with Session(self.engine) as db:
            pairs = memory_service.search_records(
                db,
                principal_user_id=self.owner_id,
                query_vector=unit_vector(0),
                embedding_model=self.embedding_model,
                kinds=["semantic"],
                limit=10,
            )
            self.assertEqual(
                [record.id for record, _ in pairs],
                [near, mid, far],
                "SEARCH_SQL 應依 cosine 距離遞增回傳本測試寫入的三筆",
            )
            self.assertAlmostEqual(pairs[0][1], 0.0, places=6)

            ranked = rank_candidates(memory_service.scored_candidates(pairs))
        self.assertEqual(
            [c.identifier for c in ranked],
            [str(near), str(mid), str(far)],
            "經 scored_candidates → rank_candidates 後，最近的必須排第一",
        )

    # -- D1／D2：Step 14，雙重刪除只寫一筆稽核（merge-blockers #22 (c)）------

    def test_D1_second_session_deleting_a_stale_row_gets_not_found_and_no_audit(self):
        """兩個 session 都先取到同一列，再**依序**刪除。

        這正是審查 review-03 的重現步驟。第二次刪除時該列已不存在：必須拋
        `MemoryNotFound`，且稽核 `deleted_by_user` 恰一筆（`BR4.3`）。
        """
        memory_id = self._create("stale", None)

        with Session(self.engine) as first, Session(self.engine) as second:
            first_record = memory_service.get_record(first, memory_id)
            second_record = memory_service.get_record(second, memory_id)
            self.assertIsNotNone(first_record)
            self.assertIsNotNone(second_record)

            memory_service.delete_with_audit(
                first, record=first_record, actor_user_id=self.owner_id
            )
            with self.assertRaises(MemoryNotFound):
                memory_service.delete_with_audit(
                    second, record=second_record, actor_user_id=self.owner_id
                )

        self.assertFalse(self._record_exists(memory_id))
        self.assertEqual(
            self._deletion_audits(memory_id),
            1,
            "同一列被刪兩次只能留下一筆 deleted_by_user 稽核（BR4.3）",
        )

    def test_D2_concurrent_deletes_leave_exactly_one_audit(self):
        """兩條連線在同一刻送出 `DELETE`：恰一方成功、另一方得 `MemoryNotFound`。"""
        memory_id = self._create("race", None)
        barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT_S)
        waited = threading.local()

        def _rendezvous(conn, cursor, statement, parameters, context, executemany):
            if (
                statement.lstrip().upper().startswith("DELETE FROM MEMORY.MEMORY_RECORDS")
                and not getattr(waited, "done", False)
            ):
                waited.done = True
                barrier.wait()

        outcomes: dict[str, str] = {}

        def _delete(label: str) -> None:
            try:
                with Session(self.engine) as db:
                    record = memory_service.get_record(db, memory_id)
                    if record is None:
                        outcomes[label] = "absent-before-delete"
                        return
                    memory_service.delete_with_audit(
                        db, record=record, actor_user_id=self.owner_id
                    )
                outcomes[label] = "deleted"
            except MemoryNotFound:
                outcomes[label] = "not-found"
            except Exception as exc:  # 記下型別，讓斷言訊息說得出發生什麼事
                outcomes[label] = f"error:{type(exc).__name__}"

        event.listen(self.engine, "before_cursor_execute", _rendezvous)
        try:
            threads = [
                threading.Thread(target=_delete, args=(label,)) for label in ("a", "b")
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(JOIN_TIMEOUT_S)
                self.assertFalse(thread.is_alive(), "併發刪除卡住未結束")
        finally:
            event.remove(self.engine, "before_cursor_execute", _rendezvous)

        self.assertEqual(
            sorted(outcomes.values()),
            ["deleted", "not-found"],
            f"兩個併發刪除應恰一方成功、另一方 MemoryNotFound；實際 {outcomes}",
        )
        self.assertFalse(self._record_exists(memory_id))
        self.assertEqual(
            self._deletion_audits(memory_id),
            1,
            "併發雙重刪除只能留下一筆 deleted_by_user 稽核（BR4.3）",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
