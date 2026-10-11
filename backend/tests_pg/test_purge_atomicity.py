"""`U9 memory-purge` 的原子性測試（`A1`–`A3`）——**只在真實 PostgreSQL**。

這是審查 `R-01` 最壞情況的**可執行證明**，而不是一段敘述
============================================================

`infrastructure-design/reviews/review-01.md` 的 `R-01` 指出：清除與 `deploy.yml`
共用同一台自架 runner，而 `deploy.yml` 的 `docker compose up -d --build
--remove-orphans`（`deploy.yml:124`／`:471`）會**重建 `db` 容器**。若兩者的窗口
重疊，清除的連線會在交易提交邊界附近被切斷。審查要求的處置逐字是「連線中斷早於
COMMIT 確認時，PostgreSQL 會回滾該交易，不會留下部分寫入；**但此結論未被本站驗證
或寫下，應補上**」。

本檔補的是可執行的證明：`A1` 以第二條連線對第一條跑 `pg_terminate_backend`，
斷言記憶列與稽核列**完全不變**。

為什麼不能放在 `backend/tests/`
-------------------------------

`backend/tests/` 全部走 in-memory SQLite（`tests/helpers.py` 在任何 DB import 之前
就換掉驅動）。SQLite **沒有 `pg_terminate_backend`**，也沒有兩條真正並行的連線，
於是整個檔會變成一個綠燈的空殼——那比不寫它更糟。隔離的機制與理由見
`tests_pg/__init__.py`。

被測對象是**生產用的那一份 SQL**
--------------------------------

本檔不重寫清除 SQL，而是從 `backend/scripts/purge_expired_memory.sql` 解析出它的
兩條敘述再執行。重寫一份等價的 SQL 會讓這三條斷言驗到一個副本，而副本與生產
那一份之間沒有任何機制保證一致。

怎麼跑
------

    cd backend && DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/cloud360' \\
      python3 -m unittest tests_pg.test_purge_atomicity -v

**前置條件**：目標資料庫已套用 `schema_rbac.sql`（含 `K)` 區塊的保留系統 actor）。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests_pg import require_pg_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
PURGE_SQL = BACKEND_DIR / "scripts" / "purge_expired_memory.sql"

# fixture 的 `content` 前綴。清理一律依它，**不得** TRUNCATE 或用無 WHERE 的
# DELETE——一個會清空整張表的清理動作，在本單元的語境下與被測的缺陷長得一樣。
FIXTURE_PREFIX = "__u9_atomicity__"
FIXTURE_OWNER = "__u9_atomicity_owner__"
SENTINEL_USERNAME = "SYSTEM.retention-purge"


def executable_statements(sql_text: str) -> list[str]:
    """把 `.sql` 檔切成**顯式交易內的可執行敘述**，照檔內順序回傳。

    做法：先丟掉 psql 元指令（`\\` 開頭的行），再把每行在第一個 `--` 處截斷，
    最後以單獨成行的 `BEGIN;` / `COMMIT;` 為界取出中間的文字。

    這個做法對本檔要解析的那一支 `.sql` 是正確的，而它的前提由
    `backend/tests/test_retention_purge_contract.py` 的
    `test_sql_comment_stripping_assumptions_hold` 機械驗證（無 `/* */` 區塊註解、
    無 `$$` 錢號引用、`--` 不出現在字串字面值內）。**前提被破壞時那條測試會紅燈**，
    而不是本檔靜默地解析出錯的文字。
    """
    kept: list[str] = []
    for raw in sql_text.splitlines():
        if raw.lstrip().startswith("\\"):
            continue
        kept.append(raw.split("--", 1)[0])

    statements: list[str] = []
    current: list[str] | None = None
    for line in kept:
        stripped = line.strip()
        if stripped == "BEGIN;":
            current = []
            continue
        if stripped == "COMMIT;":
            if current is not None:
                statements.append("\n".join(current).strip())
            current = None
            continue
        if current is not None:
            current.append(line)
    return [s for s in statements if s]


class PurgeAtomicityTest(unittest.TestCase):
    """真實 PostgreSQL 上的三條原子性斷言。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())

        statements = executable_statements(PURGE_SQL.read_text(encoding="utf-8"))
        if len(statements) != 2:
            raise RuntimeError(
                f"{PURGE_SQL.name} 應有恰好 2 個顯式交易，解析到 {len(statements)} 個。"
                "本檔以單獨成行的 BEGIN;／COMMIT; 為界切敘述——該檔的交易邊界被改過"
            )
        cls.purge_memories_sql, cls.purge_audit_sql = statements
        # 哨兵：解析到的第一條敘述必須真的是那個 CTE，否則下面三條斷言測的是別的東西。
        for needle in ("DELETE FROM memory.memory_records", "purged_by_retention"):
            if needle not in cls.purge_memories_sql:
                raise RuntimeError(
                    f"解析到的第 1 條敘述不含 {needle!r}——{PURGE_SQL.name} 的結構被改過"
                )
        if "memory_audit_events" not in cls.purge_audit_sql:
            raise RuntimeError(
                f"解析到的第 2 條敘述不是稽核清除——{PURGE_SQL.name} 的結構被改過"
            )

        with cls.engine.connect() as conn:
            missing = [
                name
                for schema, name in (
                    ("memory", "memory_records"),
                    ("memory", "memory_audit_events"),
                    ("public", "users"),
                )
                if not conn.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = :s AND table_name = :t"
                    ),
                    {"s": schema, "t": name},
                ).scalar()
            ]
            if missing:
                raise RuntimeError(
                    "前置條件不足：缺少 "
                    + "、".join(missing)
                    + "。請先對目標資料庫套用 schema_rbac.sql"
                    "（CI 的 concurrency job 會做這件事；本機見 LOCAL-DEV.md 第 2 節）"
                )
            if not conn.execute(
                text("SELECT count(*) FROM users WHERE username = :u"),
                {"u": SENTINEL_USERNAME},
            ).scalar():
                raise RuntimeError(
                    f"前置條件不足：保留系統 actor（{SENTINEL_USERNAME}）不存在。"
                    "它由 schema_rbac.sql 的 K) 區塊 seed；既有環境見 "
                    "backend/scripts/seed_retention_system_actor.py。"
                    "沒有它，清除的稽核 INSERT 會讓整個交易中止，"
                    "而那會讓 A1／A2 以錯的理由失敗"
                )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    # -- fixtures ---------------------------------------------------------

    def setUp(self) -> None:
        self._cleanup()
        with self.engine.begin() as conn:
            self.owner_id = conn.execute(
                text(
                    "INSERT INTO users (username, password_hash, role, is_active) "
                    "VALUES (:u, 'unused', 'Project_Architect', true) RETURNING id"
                ),
                {"u": FIXTURE_OWNER},
            ).scalar()
            self.sentinel_id = conn.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": SENTINEL_USERNAME},
            ).scalar()
            # 本檔即將跑**生產用的**清除敘述，它會刪掉資料庫內**所有**逾期 episodic
            # 列，不只 fixture。若此時存在不屬於 fixture 的那種列，繼續執行會真的
            # 刪掉它們（第一條斷言的交易會回滾，但 A2 的不會）。大聲擋下。
            stray = conn.execute(
                text(
                    "SELECT count(*) FROM memory.memory_records "
                    "WHERE kind = 'episodic' AND expires_at < now() "
                    "AND content NOT LIKE :p"
                ),
                {"p": FIXTURE_PREFIX + "%"},
            ).scalar()
            self.assertEqual(
                stray,
                0,
                "目標資料庫有不屬於本檔 fixture 的逾期 episodic 記憶。"
                "本檔會執行真正的清除敘述並在 A2 中 COMMIT，所以那些列會被真的刪掉。"
                "請改對一個可丟棄的資料庫執行（CI 的 service container）",
            )

    def tearDown(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM memory.memory_audit_events WHERE memory_id IN "
                    "(SELECT id FROM memory.memory_records WHERE content LIKE :p)"
                ),
                {"p": FIXTURE_PREFIX + "%"},
            )
            conn.execute(
                text(
                    "DELETE FROM memory.memory_audit_events WHERE actor_user_id IN "
                    "(SELECT id FROM users WHERE username = :u)"
                ),
                {"u": FIXTURE_OWNER},
            )
            # A1／A2 刪掉記憶列之後，它們寫的稽核列**刻意沒有外鍵**（DG-1），
            # 故必須以記下來的 id 清理，不能靠 CASCADE。
            for memory_id in getattr(self, "_fixture_memory_ids", []):
                conn.execute(
                    text(
                        "DELETE FROM memory.memory_audit_events WHERE memory_id = :m"
                    ),
                    {"m": memory_id},
                )
            conn.execute(
                text("DELETE FROM memory.memory_records WHERE content LIKE :p"),
                {"p": FIXTURE_PREFIX + "%"},
            )
            conn.execute(
                text("DELETE FROM users WHERE username = :u"), {"u": FIXTURE_OWNER}
            )
        self._fixture_memory_ids = []

    def _expired_episodic(self, label: str) -> int:
        """建一列已逾期的 episodic 記憶（清除應該選到它），回傳 id。"""
        with self.engine.begin() as conn:
            memory_id = conn.execute(
                text(
                    "INSERT INTO memory.memory_records "
                    "(kind, owner_user_id, visibility_scope, content, "
                    " embedding_model, expires_at) "
                    "VALUES ('episodic', :o, 'private', :c, 'bge-m3', "
                    "        now() - interval '1 day') RETURNING id"
                ),
                {"o": self.owner_id, "c": f"{FIXTURE_PREFIX}{label}"},
            ).scalar()
        ids = getattr(self, "_fixture_memory_ids", [])
        ids.append(memory_id)
        self._fixture_memory_ids = ids
        return memory_id

    def _counts(self, memory_id: int) -> tuple[int, int]:
        """(該記憶列是否還在, 針對它的 purged_by_retention 稽核列數)。"""
        with self.engine.connect() as conn:
            memories = conn.execute(
                text("SELECT count(*) FROM memory.memory_records WHERE id = :i"),
                {"i": memory_id},
            ).scalar()
            audits = conn.execute(
                text(
                    "SELECT count(*) FROM memory.memory_audit_events "
                    "WHERE memory_id = :i AND action = 'purged_by_retention'"
                ),
                {"i": memory_id},
            ).scalar()
        return memories, audits

    # -- A1 ---------------------------------------------------------------

    def test_terminated_before_commit_deletes_nothing(self) -> None:
        """`A1`：連線在 COMMIT 之前被切斷時，一列都沒被刪、一列稽核都沒寫。

        這就是 `R-01` 的最壞情境：`deploy.yml` 的
        `docker compose up -d --build --remove-orphans` 重建 `db` 容器，而清除的
        連線正好在交易提交邊界附近。本測試不等待那個巧合發生，直接以
        `pg_terminate_backend` 製造它。
        """
        memory_id = self._expired_episodic("a1")
        self.assertEqual(self._counts(memory_id), (1, 0), "fixture 建立失敗")

        conn_a = self.engine.connect()
        trans = conn_a.begin()
        pid = conn_a.execute(text("SELECT pg_backend_pid()")).scalar()
        # 跑完整個清除 CTE（刪除 ＋ 稽核），但**不 COMMIT**。
        conn_a.execute(text(self.purge_memories_sql))

        # 在 A 的交易尚未提交時，第二條連線看不到它的任何變更（READ COMMITTED）。
        self.assertEqual(
            self._counts(memory_id),
            (1, 0),
            "另一條連線在 COMMIT 之前就看到了未提交的變更——隔離等級不是預期的那樣",
        )

        with self.engine.connect() as conn_b:
            terminated = conn_b.execute(
                text("SELECT pg_terminate_backend(:pid)"), {"pid": pid}
            ).scalar()
        self.assertTrue(
            terminated, "pg_terminate_backend 回 false——連線沒有被切斷，本測試無效"
        )

        # 連線已死：收尾動作一律吞掉它們自己的錯誤。被測的是資料庫狀態，
        # 不是 SQLAlchemy 對一個已死連線的 rollback 會不會拋。
        for closer in (trans.rollback, conn_a.close):
            try:
                closer()
            except Exception:  # noqa: BLE001 - 連線已被切斷，這是預期的
                pass

        self.assertEqual(
            self._counts(memory_id),
            (1, 0),
            "連線在 COMMIT 之前被切斷，PostgreSQL 必須回滾整個交易——"
            "記憶列應仍存在且沒有任何稽核列。若記憶列不見了，"
            "那表示清除會在部署重建 db 容器時留下不可復原的部分寫入",
        )

    # -- A2 ---------------------------------------------------------------

    def test_committed_purge_writes_one_audit_row_per_deleted_memory(self) -> None:
        """`A2`：正常 COMMIT 後，刪除數 == 新稽核數，且皆非零（`NFR7.11`）。

        恆等性由 CTE 的形狀保證（稽核列的來源是 DELETE 自己的 `RETURNING`），
        本測試驗那個保證在真實 PostgreSQL 上確實成立。
        """
        memory_id = self._expired_episodic("a2")

        with self.engine.begin() as conn:
            row = conn.execute(text(self.purge_memories_sql)).one()
        memories_purged, audit_rows_written = row[0], row[1]

        self.assertGreater(
            memories_purged, 0, "清除沒有選到任何列——fixture 應該有一列逾期 episodic"
        )
        self.assertEqual(
            memories_purged,
            audit_rows_written,
            "刪除的記憶列數必須等於寫入的稽核列數（NFR7.11／FR4.7）",
        )

        present, audits = self._counts(memory_id)
        self.assertEqual(present, 0, "逾期的 episodic 列應已被刪除")
        self.assertEqual(audits, 1, "被刪除的那一列應恰有 1 筆 purged_by_retention 稽核")

        with self.engine.connect() as conn:
            actor = conn.execute(
                text(
                    "SELECT actor_user_id FROM memory.memory_audit_events "
                    "WHERE memory_id = :i AND action = 'purged_by_retention'"
                ),
                {"i": memory_id},
            ).scalar()
        self.assertEqual(
            actor,
            self.sentinel_id,
            "稽核的 actor 必須是保留系統 actor，不是記憶擁有者——"
            "填擁有者會讓稽核對「誰刪的」說謊",
        )
        self.assertNotEqual(
            actor, self.owner_id, "稽核的 actor 不得是記憶擁有者"
        )

    # -- A3 ---------------------------------------------------------------

    def test_missing_system_actor_aborts_whole_transaction(self) -> None:
        """`A3`：哨符列不可用時，整個交易中止且記憶列**一列都沒少**。

        `security-design.md §1.4` 要求這裡是**大聲失敗**：以 username 查 id 而非
        寫死整數，查不到時子查詢回 NULL → `actor_user_id` 的 `NOT NULL` 違反 →
        整個交易中止。那正是要的行為，因為替代品是「稽核說謊」或「悄悄不寫稽核」。

        **本測試不真的刪掉哨符列**：它在一個會被 rollback 的交易內把它改名。
        刪除會撞上 `memory_audit_events.actor_user_id` 的外鍵（若同一座資料庫上
        已有引用它的稽核列），於是測試會以一個與被測行為無關的理由失敗。
        """
        memory_id = self._expired_episodic("a3")

        conn = self.engine.connect()
        trans = conn.begin()
        try:
            renamed = conn.execute(
                text(
                    "UPDATE users SET username = username || '__u9_absent' "
                    "WHERE username = :u RETURNING id"
                ),
                {"u": SENTINEL_USERNAME},
            ).scalar()
            self.assertIsNotNone(renamed, "哨符列不存在——setUpClass 的前置檢查應已擋下")

            with self.assertRaises(DBAPIError) as caught:
                conn.execute(text(self.purge_memories_sql))
            self.assertIn(
                "actor_user_id",
                str(caught.exception).lower(),
                "錯誤訊息應指向 actor_user_id 的 NOT NULL 違反，"
                f"實際為：{caught.exception}",
            )
        finally:
            trans.rollback()
            conn.close()

        present, audits = self._counts(memory_id)
        self.assertEqual(
            present,
            1,
            "哨符列不可用時整個清除交易必須中止——記憶列一列都不得被刪除。"
            "若它消失了，代表刪除與稽核不在同一個交易內，而 FR4.7 在那一刻被破壞",
        )
        self.assertEqual(audits, 0, "交易中止後不得留下任何稽核列")

        with self.engine.connect() as check:
            restored = check.execute(
                text("SELECT count(*) FROM users WHERE username = :u"),
                {"u": SENTINEL_USERNAME},
            ).scalar()
        self.assertEqual(
            restored, 1, "rollback 之後哨符列必須恢復原名——否則後續測試會以錯的理由失敗"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
