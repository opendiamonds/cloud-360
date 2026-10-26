"""`U20 requirement-field-service` 的資料存取層測試（`S1`–`S8`，in-memory SQLite）。

對應 `unit-test-instructions.md §三` 的第二列（資料存取，8 個）。PostgreSQL 方言的
upsert、條件式清空與「兩個併發清空只生效一次」在 `tests_pg/test_requirement_field_pg.py`
——SQLite 的整庫鎖之下兩個交易本來就不會真的並行，在這裡寫併發測試會產生假的覆蓋證據
（理由同 `tests_pg/__init__.py`）。

`QueryCounter` 供本單元其餘測試檔共用（`NFR20.32`：查詢次數以
`before_cursor_execute` 事件計數、依目標表名過濾，不另造量測方式）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import sqlite3
import unittest
from datetime import datetime, timezone

from sqlalchemy import event, func, insert, select

from models import SystemRequirementField
import services.requirement_field_service as service
from tests.helpers import close_session, make_session, make_user

TABLE_NAME = "system_requirement_fields"
T0 = datetime(2026, 10, 1, 8, 0, 0)
T1 = datetime(2026, 10, 12, 9, 30, 0)
T2 = datetime(2026, 10, 12, 10, 45, 0)


class QueryCounter:
    """記錄一段程式對 `system_requirement_fields` 發出的每一條 SQL。

    以 `with QueryCounter(db) as counter:` 使用；`selects`／`writes` 只計目標為本表的
    敘述，`total` 計全部（`NFR20.2` 要比較的是整個請求的總數）。
    """

    def __init__(self, db) -> None:
        self._engine = db.get_bind()
        self.statements: list[str] = []

    def _record(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(" ".join(statement.split()))

    def __enter__(self) -> "QueryCounter":
        event.listen(self._engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(self._engine, "before_cursor_execute", self._record)

    @property
    def total(self) -> int:
        return len(self.statements)

    @property
    def selects(self) -> int:
        return sum(
            1 for s in self.statements
            if s.upper().startswith("SELECT") and f"FROM {TABLE_NAME}" in s
        )

    @property
    def writes(self) -> int:
        return sum(
            1 for s in self.statements
            if s.upper().startswith((f"INSERT INTO {TABLE_NAME}".upper(),
                                     f"UPDATE {TABLE_NAME}".upper()))
        )

    @property
    def table_statements(self) -> int:
        return sum(1 for s in self.statements if TABLE_NAME in s)


class RequirementFieldServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.bob = make_user(self.db, username="bob", role="Project_Editor")
        self.system_id = 7

    def tearDown(self) -> None:
        close_session(self.db)

    # -- fixtures ---------------------------------------------------------

    def _insert_row(self, field_key, *, value, cleared_at=None, group="cost",
                    updated_by=None, on_behalf_of=None, updated_at=T0):
        """直接插列：構造「列已存在」「已清空」「第四種列」等前置狀態。"""
        self.db.execute(
            insert(SystemRequirementField.__table__).values(
                system_id=self.system_id, agent_group=group, field_key=field_key,
                value=value, cleared_at=cleared_at, updated_at=updated_at,
                updated_by=updated_by or self.alice.id,
                updated_on_behalf_of=on_behalf_of,
            )
        )
        self.db.commit()

    def _row_count(self) -> int:
        return self.db.execute(
            select(func.count()).select_from(SystemRequirementField.__table__)
        ).scalar_one()

    def _upsert(self, field_key, value, *, by=None, on_behalf_of=None, now=T1):
        row = service.upsert_value(
            self.db, system_id=self.system_id, agent_group="cost",
            field_key=field_key, value=value, updated_by=(by or self.alice).id,
            on_behalf_of=on_behalf_of, now=now,
        )
        self.db.commit()
        return row

    def _clear(self, field_key, *, by=None, now=T1):
        row = service.clear_if_filled(
            self.db, system_id=self.system_id, agent_group="cost",
            field_key=field_key, updated_by=(by or self.alice).id, now=now,
        )
        self.db.commit()
        return row

    # -- S1–S5：寫入與清空的語意 -------------------------------------------

    def test_S1_writing_the_same_field_twice_keeps_one_row(self):
        """`S1`／`BR43.5`／`NFR20.15`：同一欄位重複寫入，列數仍為 1、值為最後一次。"""
        self._upsert("sla", "99.9%")
        row = self._upsert("sla", "99.95%", by=self.bob, on_behalf_of="cost", now=T2)
        self.assertEqual(self._row_count(), 1)
        self.assertEqual(row.value, "99.95%")
        self.assertEqual(row.updated_by, self.bob.id)
        self.assertEqual(row.updated_on_behalf_of, "cost")
        self.assertEqual(row.updated_at, T2)

    def test_S2_first_write_path_on_an_existing_row_does_not_raise(self):
        """`S2`／`NFR20.17`：列已存在時走首寫路徑不拋 `IntegrityError`。

        以直接插列造出「另一個請求剛寫入」的狀態（而且是**已清空**的列），再呼叫
        同一支 upsert：先查後寫的實作在這裡會撞唯一鍵。另驗覆寫時 `cleared_at` 被設回
        null——否則 CHECK 會擋下「有值且已清空」，而那也是一個 500。
        """
        self._insert_row("peak_tps", value=None, cleared_at=T0)
        row = self._upsert("peak_tps", "1200")
        self.assertEqual(row.value, "1200")
        self.assertIsNone(row.cleared_at)
        self.assertEqual(self._row_count(), 1)

    def test_S3_clearing_a_never_filled_field_is_a_noop_without_a_row(self):
        """`S3`／`BR43.3`：從未填過的欄位清空 → 不寫入、**不建列**。

        建一列「已清空」會讓一個從未有過值的欄位被標為清空，三態的語意就破了。
        """
        self.assertIsNone(self._clear("sla"))
        self.assertEqual(self._row_count(), 0)

    def test_S4_clearing_twice_keeps_the_first_clear(self):
        """`S4`／`BR43.4`／`NFR20.22`：已清空再清空為 no-op，`cleared_at` 與
        `updated_by` 不變（固定時鐘注入，故「不更新」與「更新成同值」可分辨）。"""
        self._upsert("sla", "99.9%", now=T0)
        first = self._clear("sla", by=self.alice, now=T1)
        self.assertIsNotNone(first)
        self.assertIsNone(first.value)
        self.assertEqual(first.cleared_at, T1)
        self.assertIsNone(first.updated_on_behalf_of)

        self.assertIsNone(self._clear("sla", by=self.bob, now=T2))
        current = service.fetch_row(
            self.db, system_id=self.system_id, agent_group="cost", field_key="sla"
        )
        self.assertEqual(current.cleared_at, T1)
        self.assertEqual(current.updated_at, T1)
        self.assertEqual(current.updated_by, self.alice.id)

    def test_S5_clearing_the_fourth_kind_of_row_is_a_noop(self):
        """`S5`／`BR44.1`：第四種列（`value` 與 `cleared_at` 皆為 null）清空為 no-op。"""
        self._insert_row("user_base", value=None, cleared_at=None, updated_at=T0)
        self.assertIsNone(self._clear("user_base", now=T2))
        current = service.fetch_row(
            self.db, system_id=self.system_id, agent_group="cost",
            field_key="user_base",
        )
        self.assertIsNone(current.cleared_at)
        self.assertEqual(current.updated_at, T0)

    # -- S6–S7：查詢次數（`NFR20.1`／`NFR20.4`） ----------------------------

    def test_S6_reading_issues_exactly_one_select_for_zero_and_eight_rows(self):
        """`S6`／`NFR20.1`：讀取對本表恰 1 次 SELECT——0 列與 8 列（7 欄 ＋ 1 列
        定義外的保留列）兩種資料下皆然，與列數無關。"""
        with QueryCounter(self.db) as empty:
            self.assertEqual(service.fetch_rows(self.db, system_id=self.system_id), [])
        self.assertEqual((empty.selects, empty.table_statements), (1, 1))

        for key in ("sla", "peak_tps", "user_base", "monthly_budget_cap",
                    "billing_region"):
            self._insert_row(key, value="x")
        self._insert_row("availability_target", value="x", group="architecture")
        self._insert_row("data_retention", value="x", group="architecture")
        self._insert_row("retired_field", value="x", group="retired_agent")

        with QueryCounter(self.db) as full:
            rows = service.fetch_rows(self.db, system_id=self.system_id)
        self.assertEqual(len(rows), 8)
        self.assertEqual((full.selects, full.table_statements), (1, 1))

    def test_S7_writing_issues_one_write_statement_and_no_select(self):
        """`S7`／`NFR20.4`：寫入對本表恰 1 條寫入敘述、0 次 SELECT（`RETURNING` 取回列）。

        兩種前置都驗：無列（INSERT 分支）與列已存在（DO UPDATE 分支）。
        """
        for _ in range(2):
            with QueryCounter(self.db) as counter:
                service.upsert_value(
                    self.db, system_id=self.system_id, agent_group="cost",
                    field_key="sla", value="99.9%", updated_by=self.alice.id,
                    on_behalf_of=None, now=T1,
                )
            self.db.commit()
            self.assertEqual((counter.writes, counter.selects), (1, 0),
                             counter.statements)

    # -- S8：RETURNING 的前提 ---------------------------------------------

    def test_S8_sqlite_supports_returning(self):
        """`S8`：SQLite ≥ 3.35 才支援 `RETURNING`（`performance-design.md` 第二節）。

        版本不足時這裡以明確訊息失敗，而不是讓上面的 upsert 測試以難懂的語法錯誤失敗。
        """
        version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
        self.assertGreaterEqual(
            version, (3, 35, 0),
            f"本機 SQLite 為 {sqlite3.sqlite_version}，低於 RETURNING 所需的 3.35；"
            "requirement_field_service 的 upsert 與條件式清空都依賴它",
        )
        self.assertEqual(service.dialect_name(self.db), "sqlite")


if __name__ == "__main__":
    unittest.main()
