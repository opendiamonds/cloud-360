"""`U20 requirement-field-service` 的資料存取層——**只在真實 PostgreSQL**（`G1`–`G3`）。

對應 `unit-test-instructions.md §三` 的第三列（3 個）。

為什麼需要這一檔（infrastructure-design `review-01` R-07）
=========================================================

`requirement_field_service.upsert_value` 依連線方言選建構式：測試的 in-memory SQLite
走 `sqlalchemy.dialects.sqlite.insert`，正式環境走 `sqlalchemy.dialects.postgresql.insert`。
**生產用的那一支在 `backend/tests/` 裡從未被執行**——它若有錯，只會在 staging 的第一次
寫入時才發現。本檔讓它在 CI 的 `concurrency` job（`discover -s tests_pg`）上執行。

`G3` 的交錯以 barrier 釘住，不用 `sleep`
========================================

兩個執行緒各自在「即將對本表送出 `UPDATE`」的那一刻（連線層的
`before_cursor_execute` 事件）於同一個 barrier 會合，然後同時送出。

- 正確實作（單一條件式 `UPDATE … WHERE value IS NOT NULL`）：先拿到列鎖的那個寫入並
  commit，另一個在鎖釋放後**重新評估 WHERE**、得到 0 列——恰一次生效。
- 突變「改回先讀後改」：兩個執行緒在 barrier 之前都已讀到「已填」，barrier 之後兩個
  無條件 `UPDATE` 都生效——第二個覆寫 `cleared_at` 與 `updated_by`，違反 `BR43.4`。
  本測試斷言「恰一次生效」，故它會紅。

正確實作下兩方都到得了 barrier（兩者都還沒送出任何寫入），故 barrier 必然成立、
不會卡住；`Barrier.wait(timeout)` 是有界的條件等待。
"""

from __future__ import annotations

import threading
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from tests_pg import require_pg_url

import services.requirement_field_service as service

UNIQUE_TAG = "u20pg"
BARRIER_TIMEOUT_S = 15.0
JOIN_TIMEOUT_S = 60.0
T1 = datetime(2026, 10, 12, 9, 0, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 10, 12, 9, 5, 0, tzinfo=timezone.utc)
T3 = datetime(2026, 10, 12, 9, 6, 0, tzinfo=timezone.utc)


class RequirementFieldPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())
        with cls.engine.connect() as conn:
            data_type = conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'system_requirement_fields' "
                    "AND column_name = 'updated_on_behalf_of'"
                )
            ).scalar()
        if data_type != "character varying":
            raise RuntimeError(
                "前置條件不足：public.system_requirement_fields.updated_on_behalf_of "
                f"應為 character varying，實際 {data_type!r}。請先對目標資料庫套用 "
                "schema_rbac.sql（含 U20 的 J) 區塊），或執行 "
                "backend/scripts/run_meta_schema_migration.py"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    # -- fixtures（以 raw SQL 建立：理由同 test_membership_concurrency._user）----

    def setUp(self) -> None:
        self.steps: dict[str, str] = {}
        with self.engine.begin() as conn:
            self.user_ids = [
                conn.execute(
                    text(
                        "INSERT INTO users (username, password_hash, role, is_active) "
                        "VALUES (:u, 'unused', 'Project_Editor', true) RETURNING id"
                    ),
                    {"u": f"{UNIQUE_TAG}-{label}-{id(self)}"},
                ).scalar_one()
                for label in ("alice", "bob")
            ]
            self.project_id = conn.execute(
                text(
                    "INSERT INTO projects (name, owner_user_id, is_default) "
                    "VALUES (:n, :o, false) RETURNING id"
                ),
                {"n": f"{UNIQUE_TAG}-{id(self)}", "o": self.user_ids[0]},
            ).scalar_one()
            self.system_id = conn.execute(
                text(
                    "INSERT INTO systems (name, project_id, is_default) "
                    "VALUES (:n, :p, false) RETURNING id"
                ),
                {"n": f"{UNIQUE_TAG}-{id(self)}", "p": self.project_id},
            ).scalar_one()

    def tearDown(self) -> None:
        # system 的 ON DELETE CASCADE 帶走本表的列；之後依外鍵順序清 project 與 user。
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM systems WHERE id = :s"), {"s": self.system_id})
            conn.execute(text("DELETE FROM projects WHERE id = :p"), {"p": self.project_id})
            conn.execute(
                text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": self.user_ids}
            )

    def _upsert(self, value, *, by, on_behalf_of=None, now=T1):
        with Session(self.engine) as db:
            row = service.upsert_value(
                db, system_id=self.system_id, agent_group="cost", field_key="sla",
                value=value, updated_by=by, on_behalf_of=on_behalf_of, now=now,
            )
            db.commit()
            return row

    def _current(self):
        with Session(self.engine) as db:
            return service.fetch_row(
                db, system_id=self.system_id, agent_group="cost", field_key="sla"
            )

    def _row_count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                text("SELECT count(*) FROM system_requirement_fields WHERE system_id = :s"),
                {"s": self.system_id},
            ).scalar_one()

    # -- G1：PostgreSQL 方言的 upsert -------------------------------------

    def test_G1_postgresql_upsert_inserts_then_overwrites_one_row(self):
        """`G1`／`BR43.5`／`NFR20.31`：PostgreSQL 方言的 `ON CONFLICT … DO UPDATE`。

        第一次插入、第二次覆寫同一列（含代寫標示 'cost' 寫進 varchar 欄位——欄位若仍
        是 integer，這裡就是型別錯誤）；列數恆為 1、`RETURNING` 取回的是寫入後的值。
        """
        with Session(self.engine) as db:
            self.assertEqual(service.dialect_name(db), "postgresql")
        first = self._upsert("99.9%", by=self.user_ids[0])
        second = self._upsert("99.95%", by=self.user_ids[1], on_behalf_of="cost", now=T2)
        self.assertEqual(self._row_count(), 1)
        self.assertEqual(first.value, "99.9%")
        self.assertEqual(
            (second.value, second.updated_by, second.updated_on_behalf_of, second.updated_at),
            ("99.95%", self.user_ids[1], "cost", T2),
        )

    # -- G2：條件式清空 ---------------------------------------------------

    def test_G2_conditional_clear_runs_once_then_is_a_noop(self):
        """`G2`／`BR43.4`／`BR43.7`：清空已填欄位一次生效；再清空回 `None` 且不改任何欄位。"""
        self._upsert("99.9%", by=self.user_ids[0], on_behalf_of="cost")
        with Session(self.engine) as db:
            cleared = service.clear_if_filled(
                db, system_id=self.system_id, agent_group="cost", field_key="sla",
                updated_by=self.user_ids[1], now=T2,
            )
            db.commit()
        self.assertEqual(
            (cleared.value, cleared.cleared_at, cleared.updated_by,
             cleared.updated_on_behalf_of),
            (None, T2, self.user_ids[1], None),
        )
        with Session(self.engine) as db:
            again = service.clear_if_filled(
                db, system_id=self.system_id, agent_group="cost", field_key="sla",
                updated_by=self.user_ids[0], now=T3,
            )
            db.commit()
        self.assertIsNone(again)
        current = self._current()
        self.assertEqual((current.cleared_at, current.updated_by), (T2, self.user_ids[1]))

    # -- G3：兩個併發清空只生效一次 ----------------------------------------

    def test_G3_two_concurrent_clears_take_effect_exactly_once(self):
        """`G3`／`NFR20.22`：兩個併發清空，恰一個生效，`cleared_at`／`updated_by` 屬於它。

        突變驗證（`unit-test-instructions.md §四`）：清空改回「先讀後改」→ 兩個都生效 → 紅。
        """
        self._upsert("99.9%", by=self.user_ids[0])
        barrier = threading.Barrier(2)
        results: dict[str, object] = {}

        def worker(name: str, user_id: int, now: datetime) -> None:
            try:
                with self.engine.connect() as conn:
                    def gate(_conn, _cursor, statement, *_args):
                        if statement.lstrip().upper().startswith(
                            "UPDATE SYSTEM_REQUIREMENT_FIELDS"
                        ):
                            self.steps[name] = "at_barrier"
                            barrier.wait(BARRIER_TIMEOUT_S)
                            self.steps[name] = "sent_update"

                    event.listen(conn, "before_cursor_execute", gate)
                    with Session(bind=conn) as db:
                        row = service.clear_if_filled(
                            db, system_id=self.system_id, agent_group="cost",
                            field_key="sla", updated_by=user_id, now=now,
                        )
                        db.commit()
                    results[name] = (user_id, now) if row is not None else None
                    self.steps[name] = "committed"
            except Exception as exc:  # noqa: BLE001 - 轉成診斷訊息而非吞掉
                self.steps[name] = f"error:{type(exc).__name__}:{exc}"

        threads = [
            threading.Thread(target=worker, args=("A", self.user_ids[0], T2)),
            threading.Thread(target=worker, args=("B", self.user_ids[1], T3)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(JOIN_TIMEOUT_S)
        self.assertFalse(
            any(thread.is_alive() for thread in threads),
            f"執行緒卡住：{self.steps}",
        )
        self.assertEqual(
            sorted(self.steps.values()), ["committed", "committed"], self.steps
        )

        effective = [value for value in results.values() if value is not None]
        self.assertEqual(
            len(effective), 1,
            f"兩個併發清空應恰一個生效，實際 {len(effective)} 個（{results}）",
        )
        winner_user, winner_now = effective[0]
        current = self._current()
        self.assertIsNone(current.value)
        self.assertEqual((current.updated_by, current.cleared_at), (winner_user, winner_now))


if __name__ == "__main__":
    unittest.main()
