"""合併前必修第 30 列 (a)(b)：一次性結構建立的後條件必須涵蓋 `J)` 區塊的全部外鍵與欄位數。

(b) `run_meta_schema_migration.EXPECTED_FK_DELETE_ACTIONS` 原本只核 `J)` 區塊 7 條外鍵中
的 3 條，且以（表、被參照表）為鍵，分不出 `project_members.user_id` 與 `invited_by`。
本檔解析 `schema_rbac.sql` 的 `J)` 區塊（與該腳本用的是同一個 `extract_blocks`），斷言
「後條件清單 ＝ 該區塊實際宣告的全部 REFERENCES（含欄名與 ON DELETE 行為）」。

(a) `verify_meta_schema.sql` 唯獨沒有對 `system_requirement_fields` 做「恰為 N 欄」的斷言；
本檔斷言 `P17` 存在且其 N 與 `J)` 區塊的欄位數、腳本的 `EXPECTED_TABLES` 三者一致。

真正的外鍵查詢只在 CI 的 `memory-schema` job（真實 PostgreSQL）執行；本檔鎖的是清單本身
不得與 DDL 漂移——那是本機唯一可驗的一半。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 從 `EXPECTED_FK_DELETE_ACTIONS` 刪掉 `invited_by` 那一列 → 案例 1 紅；
  M2 把 `system_id` 那一列的期望行為由 `c` 改為 `a` → 案例 1 紅；
  M3 刪掉 `verify_meta_schema.sql` 的 `P17` → 案例 2 紅；
  M4 把 `P17` 從結構類 DO 區塊的「全部通過」RAISE NOTICE 清單拿掉 → 案例 3 紅
     （結果記於 `project-meta-data` 的 `code-summary.md`）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import re
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND / "scripts"))

import run_meta_schema_migration as meta  # noqa: E402

VERIFY_SQL = BACKEND / "scripts" / "verify_meta_schema.sql"
_COLUMN_FK = re.compile(
    r"^\s*(\w+)\s+INTEGER\b[^,]*?\bREFERENCES\s+(\w+)\s*\(id\)(\s+ON DELETE CASCADE)?",
    re.IGNORECASE,
)
_CREATE = re.compile(r"CREATE TABLE IF NOT EXISTS (\w+) \(", re.IGNORECASE)


def _strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def _j_block_tables() -> dict:
    """{table: [column lines]}：`J)` 區塊每張表 `CREATE TABLE ( ... );` 內的欄位行。"""
    (_, text), = meta.extract_blocks(
        (REPO / "schema_rbac.sql").read_text(encoding="utf-8"), ("J",)
    )
    body = _strip_comments(text)
    tables: dict = {}
    for match in _CREATE.finditer(body):
        start = match.end()
        end = body.index(");", start)
        tables[match.group(1)] = [ln for ln in body[start:end].splitlines() if ln.strip()]
    return tables


class MetaSchemaExpectationsTest(unittest.TestCase):
    def test_fk_expectations_equal_every_reference_in_j_block(self):
        """
        @purpose 外鍵後條件涵蓋 J) 區塊的全部外鍵，以欄位為鍵、含 ON DELETE 行為
        @given schema_rbac.sql 的 J) 區塊（以 run_meta_schema_migration.extract_blocks 解析）
        @step 從每張表的欄位定義抽出 (表, 欄, 被參照表, CASCADE/NO ACTION)
        @pass 集合與 EXPECTED_FK_DELETE_ACTIONS 完全相等（7 條）
        @story US11.1
        """
        declared = set()
        for table, lines in _j_block_tables().items():
            for line in lines:
                m = _COLUMN_FK.match(line)
                if m:
                    declared.add(
                        ("public", table, m.group(1), m.group(2), "c" if m.group(3) else "a")
                    )
        self.assertEqual(len(declared), 7, declared)
        self.assertEqual(set(meta.EXPECTED_FK_DELETE_ACTIONS), declared)

    def test_p17_pins_system_requirement_fields_to_its_column_count(self):
        """
        @purpose verify_meta_schema.sql 對 system_requirement_fields 有「恰為 N 欄」的斷言，且 N 與 DDL、腳本一致
        @given verify_meta_schema.sql、J) 區塊、EXPECTED_TABLES
        @step 數 J) 區塊該表的欄位行；讀 P17 的 N；讀 EXPECTED_TABLES 的值
        @pass 三者皆為 9
        @story US11.1
        """
        lines = _j_block_tables()["system_requirement_fields"]
        # 表級約束（及其續行）不是欄位：`CONSTRAINT …` 之後的 `UNIQUE (…)`／`CHECK (…)`。
        table_level = ("CONSTRAINT", "UNIQUE", "CHECK", "PRIMARY KEY", "FOREIGN KEY")
        columns = [ln for ln in lines if not ln.strip().upper().startswith(table_level)]
        self.assertEqual(len(columns), 9, columns)
        expected = dict(((s, t), n) for s, t, n in meta.EXPECTED_TABLES)
        self.assertEqual(expected[("public", "system_requirement_fields")], 9)
        sql = VERIFY_SQL.read_text(encoding="utf-8")
        p17 = re.search(
            r"table_name = 'system_requirement_fields';\s*IF n <> (\d+) THEN\s*RAISE EXCEPTION\s*'P17 FAILED",
            sql,
        )
        self.assertIsNotNone(p17, "verify_meta_schema.sql 缺少 P17")
        self.assertEqual(int(p17.group(1)), 9)

    def test_structural_block_pass_notice_lists_every_assertion_in_the_block(self):
        """
        @purpose 結構類 DO 區塊的「全部通過」訊息列出的編號，恰為該區塊實際執行的斷言編號（CI log 不得讓某條斷言看起來沒跑）
        @given verify_meta_schema.sql 中含 'P17 FAILED' 的那個 DO $$ … END $$; 區塊
        @step 收集區塊內所有 'P<n> FAILED 的編號；取同區塊「全部通過」RAISE NOTICE 括號內的編號
        @pass 兩個編號集合相等，且皆含 P17
        @story US11.1
        """
        sql = VERIFY_SQL.read_text(encoding="utf-8")
        blocks = re.findall(r"^DO \$\$\n.*?^END \$\$;", sql, re.DOTALL | re.MULTILINE)
        structural = [b for b in blocks if "'P17 FAILED" in b]
        self.assertEqual(len(structural), 1, "應恰有一個 DO 區塊含 P17 斷言")
        block = structural[0]
        asserted = {int(n) for n in re.findall(r"'P(\d+) FAILED", block)}
        notice = re.search(r"RAISE NOTICE '[^'（]*（([^）]*)）全部通過'", block)
        self.assertIsNotNone(notice, "結構類 DO 區塊缺少「全部通過」RAISE NOTICE")
        listed = {int(n) for n in re.findall(r"P(\d+)", notice.group(1))}
        self.assertIn(17, asserted)
        self.assertEqual(listed, asserted)


if __name__ == "__main__":
    unittest.main()
