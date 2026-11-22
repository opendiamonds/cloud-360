"""全新庫啟動時，C1 退場 rename 不得留下誤導的 WARNING——**只在真實 PostgreSQL**。

由來：build-and-test `test-results.md` 待修 9（findings F7 第 3 點，既存缺陷，2026-09-20 的 cost
intent 引入）。全新庫套用 `schema_rbac.sql` 後跑 `database.init_db()`，啟動 log 逐字出現：

    WARNING:cloud360.database:Cost schema index rename 略過/失敗: (psycopg.errors.InFailedSqlTransaction)
    current transaction is aborted, commands ignored until end of transaction block

根因：`_ensure_cost_schema` 在同一個交易裡先做 `RENAME CONSTRAINT cost_audit_event_pkey`——全新庫上
該 constraint 本來就叫 `archive_cost_audit_event_pkey`，失敗是預期中的，`except: pass` 也吞掉了——
但 PostgreSQL 的交易已進入 aborted 狀態，下一句 `ALTER INDEX` 因而以 `InFailedSqlTransaction` 失敗並
記一行 WARNING。修法是每一句各包 `conn.begin_nested()`（SAVEPOINT）。

**為什麼只能在這裡驗**：SQLite 的失敗敘述不會讓交易進入 aborted 狀態，`backend/tests/` 的 in-memory
SQLite 上同一段程式無論有沒有 savepoint 都不會記 WARNING——在那裡寫這個測試會得到一個無鑑別力的綠燈。
而 `build-and-test` 當時把它列為「無自動化回歸測試」的理由是 `init_db` 在共用庫有寫入副作用；本檔
只呼叫 `_ensure_cost_schema` 一個函式，它在已套用 `schema_rbac.sql` 的庫上每一句都是 no-op
（`IF EXISTS` 或預期失敗並由 savepoint 回滾），不建表、不寫資料。

怎麼跑
------

    cd backend && DATABASE_URL='postgresql+psycopg://postgres:<pw>@localhost:5432/cloud360' \\
      python3 -m unittest tests_pg.test_cost_schema_startup_pg -v

**前置條件**：目標資料庫已套用 `schema_rbac.sql`（`archive_cost_audit_event` 與其 pkey 已存在）。
"""

from __future__ import annotations

import logging
import unittest
from unittest import mock

from sqlalchemy import create_engine, text

from tests_pg import require_pg_url

import database


class CostSchemaStartupPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_fresh_schema_startup_logs_no_cost_rename_warning(self) -> None:
        """
        @purpose 已套用 schema_rbac.sql 的全新庫上，C1 退場 rename 檢查不得記任何 WARNING：
                 預期中失敗的 RENAME CONSTRAINT 不得讓後面的 ALTER INDEX 以
                 InFailedSqlTransaction 失敗。
        @given 真實 PostgreSQL 已套用 schema_rbac.sql；archive_cost_audit_event 存在且其 pkey
               已叫 archive_cost_audit_event_pkey（RENAME CONSTRAINT cost_audit_event_pkey 必定失敗）
        @step 查 pg_constraint | archive_cost_audit_event_pkey 恰 1 筆、cost_audit_event_pkey 0 筆（前提成立）
        @step 以該庫的引擎呼叫 database._ensure_cost_schema() | 不拋例外
        @step 檢視 cloud360.database 的 log | 不得出現任何含「Cost schema」的 WARNING
        @step 檢視 cloud360.database 的 log | 出現「Cost schema 退場 rename 檢查完成」（函式跑到最後）
        @pass 前提成立、無例外、0 筆「Cost schema」WARNING，且完成訊息出現 1 次
        @story 無（既存缺陷，非本 intent 的故事；test-results.md 待修 9）
        @note 回歸防護：把 begin_nested() 拿掉（回到 HEAD 前的寫法）時，本案以
              「Cost schema index rename 略過/失敗: (psycopg.errors.InFailedSqlTransaction)」紅燈。
              前提斷言是為了防止「庫裡根本沒有那個 constraint、RENAME CONSTRAINT 沒失敗」
              這種讓本案無鑑別力地綠燈的環境。
        """
        with self.engine.connect() as conn:
            names = set(
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conname IN ('archive_cost_audit_event_pkey', 'cost_audit_event_pkey')"
                    )
                ).scalars()
            )
        self.assertEqual(names, {"archive_cost_audit_event_pkey"})

        with mock.patch.object(database, "engine", self.engine), self.assertLogs(
            "cloud360.database", level=logging.INFO
        ) as captured:
            database._ensure_cost_schema()

        warnings = [
            r.getMessage()
            for r in captured.records
            if r.levelno >= logging.WARNING and "Cost schema" in r.getMessage()
        ]
        self.assertEqual(warnings, [])
        done = [r for r in captured.records if "Cost schema 退場 rename 檢查完成" in r.getMessage()]
        self.assertEqual(len(done), 1)


if __name__ == "__main__":
    unittest.main()
