"""`U20 requirement-field-service` 的資料模型測試（`D1`–`D5`，`BR47.4`）。

對應 `unit-test-instructions.md §三` 的第一列（ORM 模型，5 個）。

**為什麼需要它**：`SystemRequirementField` 納入 `Base` 之後，`database.py` 的
`Base.metadata.create_all()` 就成為這張表的**第二條建表路徑**（`models.py` 的
`U20` 區塊註解），而本單元刻意不掛 `before_create` 守門。於是 ORM 與
`schema_rbac.sql` 的 `J)` 區塊必須逐條一致，否則「少寫一條 CHECK」等於在測試環境
與未遷移的既有環境裡悄悄移除它。

**SQLite 測得到與測不到的**：`D5` 的 CHECK 在 SQLite 上有效；`system_id` 的
`ON DELETE CASCADE` **在這裡測不到**（`tests/helpers.py` 未開
`PRAGMA foreign_keys`），由 CI `memory-schema` job 的步驟 E 在真實 PostgreSQL 上
驗。收斂（`BR47.2`）同樣只在那裡驗。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import String
from sqlalchemy.exc import IntegrityError

from models import SystemRequirementField
from tests.helpers import close_session, make_session, make_user

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema_rbac.sql"
TABLE = "system_requirement_fields"


def ddl_block() -> str:
    """取出 `schema_rbac.sql` 裡本表的 `CREATE TABLE` 本體。"""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS " + TABLE + r"\s*\((.*?)\n\);", sql, re.S
    )
    assert match is not None, f"{TABLE} 的 DDL 找不到"
    return match.group(1)


def ddl_column_lines() -> dict[str, str]:
    """欄位名 → 該欄的 DDL 宣告行（略過約束宣告、其續行與註解）。"""
    columns: dict[str, str] = {}
    for line in ddl_block().splitlines():
        line = line.strip()
        if not line or line.startswith(
            ("CONSTRAINT", "CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "--", ")")
        ):
            continue
        columns[line.split()[0].strip(",")] = line
    return columns


def ddl_is_nullable(line: str) -> bool:
    return "NOT NULL" not in line and "PRIMARY KEY" not in line


class RequirementFieldSchemaAlignmentTest(unittest.TestCase):
    """`D1`–`D4`：ORM 與 `schema_rbac.sql` 兩份物化的一致性。"""

    def test_D1_orm_columns_match_the_authoritative_ddl(self):
        """`D1`：欄位名集合**相等**（漏欄位與多欄位兩個方向都紅）。"""
        orm = {c.name for c in SystemRequirementField.__table__.columns}
        ddl = set(ddl_column_lines())
        self.assertEqual(
            orm, ddl, f"ORM only={orm - ddl}, DDL only={ddl - orm}"
        )
        self.assertEqual(len(orm), 9, "DEPLOY.md 2.2.9 與遷移腳本的後條件都寫 9 欄")

    def test_D2_nullability_matches_the_ddl(self):
        """`D2`：每一欄的可空性與 DDL 一致。

        點名四欄（`unit-test-instructions.md §三`）：`value`／`cleared_at`／
        `updated_on_behalf_of` 可空（三態模型與「使用者自填」的表達方式），
        `updated_by` 不可空（「誰清的」那一半稽核）。
        """
        lines = ddl_column_lines()
        for column in SystemRequirementField.__table__.columns:
            self.assertEqual(
                column.nullable,
                ddl_is_nullable(lines[column.name]),
                f"{column.name} 的可空性與 DDL 不一致",
            )
        table = SystemRequirementField.__table__
        for name in ("value", "cleared_at", "updated_on_behalf_of"):
            self.assertTrue(table.c[name].nullable, f"{name} 必須可為 null")
        self.assertFalse(table.c.updated_by.nullable)

    def test_D3_on_behalf_of_is_a_64_char_string_without_foreign_key(self):
        """`D3`／`[FD1]`=A／`BR47.1`：代寫欄是 agent 組識別字，不是使用者 id。

        兩半都要：型別為長度 64 的字串、**沒有**外鍵。另鎖住其餘兩條外鍵仍在
        （`system_id` → `systems` CASCADE、`updated_by` → `users` 無 `ON DELETE`）
        ——把代寫欄的外鍵拿掉時順手拿掉 `updated_by` 那條，會讓稽核失去參照完整性。
        """
        column = SystemRequirementField.__table__.c.updated_on_behalf_of
        self.assertIsInstance(column.type, String)
        self.assertEqual(column.type.length, 64)
        self.assertEqual(column.foreign_keys, set())

        ddl_line = ddl_column_lines()["updated_on_behalf_of"]
        self.assertIn("VARCHAR(64)", ddl_line)
        self.assertNotIn("REFERENCES", ddl_line)

        actual = {
            fk.parent.name: (fk.column.table.name, fk.ondelete)
            for fk in SystemRequirementField.__table__.foreign_keys
        }
        self.assertEqual(
            actual,
            {"system_id": ("systems", "CASCADE"), "updated_by": ("users", None)},
        )

    def test_D4_unique_key_check_and_indexes_match_the_ddl(self):
        """`D4`：具名約束集合相等、三欄唯一鍵的欄位順序一致、沒有額外索引。

        三欄唯一鍵同時是 upsert 的衝突目標：漏宣告時 SQLite 會在執行期以
        「ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint」
        失敗，而那會被誤讀成方言問題（`tech-stack-decisions.md` 第一節）。
        """
        table = SystemRequirementField.__table__
        orm_constraints = {c.name for c in table.constraints if c.name is not None}
        ddl_constraints = set(re.findall(r"CONSTRAINT\s+(\w+)", ddl_block()))
        self.assertEqual(orm_constraints, ddl_constraints)

        unique = next(
            c for c in table.constraints
            if c.name == "uq_system_requirement_fields_group_key"
        )
        self.assertEqual(
            [c.name for c in unique.columns],
            ["system_id", "agent_group", "field_key"],
        )
        self.assertEqual({i.name for i in table.indexes}, set())


class RequirementFieldCheckConstraintTest(unittest.TestCase):
    """`D5`：CHECK 在 SQLite 測試庫上實際生效。"""

    def setUp(self) -> None:
        self.db = make_session()
        self.user = make_user(self.db, username="writer", role="Project_Architect")

    def tearDown(self) -> None:
        close_session(self.db)

    def test_D5_check_rejects_a_row_that_has_a_value_and_is_cleared(self):
        """`D5`／`ck_system_requirement_fields_cleared_has_null_value`。

        「有值且已清空」被拒；「已清空」（value 為 null）本身可以寫入——
        只驗前者會讓「CHECK 把清空也一起擋掉」通過。
        """
        now = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
        self.db.add(
            SystemRequirementField(
                system_id=1, agent_group="cost", field_key="sla",
                value=None, cleared_at=now, updated_at=now,
                updated_by=self.user.id,
            )
        )
        self.db.commit()

        self.db.add(
            SystemRequirementField(
                system_id=1, agent_group="cost", field_key="peak_tps",
                value="still has a value", cleared_at=now, updated_at=now,
                updated_by=self.user.id,
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
