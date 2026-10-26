#!/usr/bin/env python3
"""`U5 memory-data` ＋ `U18 project-meta-data` 的一次性結構建立指令。

**部署期執行，不在啟動路徑上**（`NFR8.4`：`backend/database.py` 的 diff 為空）。

為什麼是獨立指令而不是啟動補丁（`[P1]`=A）
------------------------------------------

`schema_rbac.sql` 只掛在 `/docker-entrypoint-initdb.d/`，故它**只在空 volume 執行**
（`BR3.2`）——既有的 `192.168.10.10` 這五張表加一個 schema **一張都拿不到**。
而既有環境的另一條路徑（`database.py` 的 `_ensure_*` 補丁家族）**全部吞掉失敗**：
`except Exception` ＋ `logger.warning(...)` 後繼續（`:257`／`:304`），而 `init_db()`
自身的 `except`（`:192`）也只是 `logger.error` ＋ `rollback()` 後**不 re-raise**。
照抄那個形狀的後果是：**表沒建起來而服務照常啟動**，之後 `U19`／`U20` 的每一次
查詢都失敗，而根因在啟動時只留了一行 warning（`BR3.1`）。

把補丁改成 re-raise 也不行：`restart: unless-stopped` 之下任何建表失敗會變成
**重啟迴圈**，而那比「少幾張表」更難診斷。所以走獨立指令，與 `U4` 的
`run_hierarchy_migration.py` 同形。

DDL 只有一份（與 `U4` 刻意不同）
--------------------------------

`U4` 的 DDL 在 `schema_rbac.sql` 與 `services/hierarchy_migration.py` **各有一份**
（`schema_rbac.sql` 的檔頭逐字「DDL 兩處並存，改一處必須改另一處」）。本腳本**不複製
DDL**：它直接解析 `schema_rbac.sql` 的 `X)`／`I)`／`J)` 三個區塊並執行同一份文字。
理由是 `team.md` 的單一真實來源規則——「無法寫測試鎖住一致性的副本不新增」。
副作用是 CI 的 `memory-schema` job（它套用 `schema_rbac.sql`）與本腳本**不可能漂移**。

用法（於 `backend/` 目錄，且 `DATABASE_URL` 已指向目標資料庫）::

    python scripts/run_meta_schema_migration.py

**前置條件**：`projects` 與 `systems` 必須已存在，也就是 `U4` 的
`python scripts/run_hierarchy_migration.py` 必須先跑過（`J)` 的兩條外鍵指向它們）。
本腳本會先檢查並以可讀訊息擋下，而不是丟一個生的 `UndefinedTable`。

單一交易，所以結束碼可被信任（`NFR8.3`）
----------------------------------------

PostgreSQL 的 DDL 可交易，故全部敘述包在**一個**交易內，並在 COMMIT **之前**對
`information_schema`／`pg_catalog` 逐項查證後條件。於是：

    結束碼 0  ⟺  下方 `EXPECTED_*` 清單的每一個物件都存在

`BR2.1` 的 `IF NOT EXISTS` 讓重跑安全，所以單一交易的價值**不在**可重跑，而在
**消除「部分成功而回報成功」這個狀態**——沒有它，一次中途失敗會留下半套結構，
而操作者從輸出看不出跑到哪裡。

任一後條件不成立即 rollback 並以非零碼結束（`NFR8.3`）。

輸出的禁令
----------

**本腳本不得輸出 `DATABASE_URL` 或其任何片段。** 本 repo 為 public 且 Actions log
公開可讀（`project.md` 的機敏資料禁令）。要指出連線目標時只印**主機與資料庫名**
（`security-design.md §二之三` 逐字）。失敗路徑沿用 `U4` 的
`traceback.print_exc()` 是安全的——該站已實測 SQLAlchemy／psycopg 的連線失敗訊息
**不含密碼、不含使用者名稱**（只含主機與埠）。
"""

from __future__ import annotations

import logging
import re
import sys
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SCHEMA_FILE = REPO_ROOT / "schema_rbac.sql"

for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from database import engine  # noqa: E402

logger = logging.getLogger("cloud360.meta_schema_migration")

# 要執行的區塊，照 schema_rbac.sql 的順序。X) 必須最先——`vector` 型別必須先存在，
# memory_records 的 vector(1024) 欄位才建得起來。
#
# **`K)` 刻意不在這個清單內，而且不得被加進來。** `schema_rbac.sql` 的 `K)` 區塊是
# `U9 memory-purge` 的保留系統 actor **seed**（`INSERT INTO users`），不是 DDL。
# 本腳本下方的成功輸出逐字宣告它「不塞任何資料」，而那句話對應契約 `K-15` 的
# `observable_side_effects`（逐字「不含任何資料寫入」）——把 `K)` 加進來會讓這支
# 腳本的可觀察副作用與它自己宣告的契約不一致，而**那個不一致只有讀過契約的人
# 才看得出來**（執行結果看起來完全正常）。
#
# `K)` 的既有環境執行路徑是**另一支腳本**：
#     cd backend && python3 scripts/seed_retention_system_actor.py
# 它 `import` 本模組的 `extract_blocks()`，所以解析邏輯與 SQL 都**只有一份**。
BLOCKS_TO_RUN = ("X", "I", "J")

# 每個區塊的哨兵字串：解析出來的文字必須含它。區塊標題被改名時，解析會抓到錯的範圍
# 或空字串，而那在輸出上與「本來就沒事可做」長得一樣——哨兵讓它**大聲失敗**。
#
# **這是「區塊 → 哨兵」的登錄表，不是「要執行哪些區塊」的清單**（後者是上方的
# `BLOCKS_TO_RUN`）。`extract_blocks()` 以 `BLOCK_SENTINELS[letter]` 查表，故任何
# 呼叫端要解析的字母都必須先登錄於此，否則是 `KeyError`。`K)` 登錄在這裡而**刻意
# 不在 `BLOCKS_TO_RUN` 內**——它由 `seed_retention_system_actor.py` 解析並執行。
BLOCK_SENTINELS = {
    "X": ("CREATE EXTENSION IF NOT EXISTS vector",),
    "I": (
        "CREATE SCHEMA IF NOT EXISTS memory",
        "CREATE TABLE IF NOT EXISTS memory.memory_records",
        "CREATE TABLE IF NOT EXISTS memory.memory_audit_events",
        "GRANT USAGE ON SCHEMA memory",
    ),
    "J": (
        "CREATE TABLE IF NOT EXISTS project_members",
        "CREATE TABLE IF NOT EXISTS reselection_events",
        "CREATE TABLE IF NOT EXISTS system_requirement_fields",
        "ix_reselection_events_unack",
        # U23（[PPN1]=A）：有人把這個 CREATE INDEX 移出 `J)` 區塊時在解析階段就失敗。
        "ix_project_members_user_id",
    ),
    # U9 memory-purge 的保留系統 actor seed。**不在 `BLOCKS_TO_RUN` 內**（見該處
    # 註解：本腳本宣告它不塞任何資料，契約 K-15）；登錄在此是為了讓
    # `seed_retention_system_actor.py` 能以同一個解析器＋同一套哨兵機制取出它，
    # 而不是複製一份解析邏輯。
    # **刻意不列哨符 username 字面值**：那個字串在本 repo 只有三處物化
    # （`K)` 區塊、`purge_expired_memory.sql`、`seed_retention_system_actor.py`
    # 的常數），由 `test_retention_purge_contract.py` 鎖住三者一致。
    # 在這裡再寫一次會變成第四處，而沒有任何測試會鎖它。
    "K": (
        "INSERT INTO users (username, password_hash, role, is_active)",
        "ON CONFLICT (username) DO NOTHING",
        "COMMENT ON TABLE users IS",
    ),
}

# `J)` 的外鍵指向這兩張表；它們屬 U4，不由本腳本建立。
REQUIRED_PREEXISTING_TABLES = ("users", "projects", "systems")

# ---------------------------------------------------------------------------
# 後條件清單 —— 「結束碼 0 代表什麼」就是這四張表的內容，沒有別的
# ---------------------------------------------------------------------------

EXPECTED_SCHEMAS = ("memory",)

# (schema, table, 欄位數)
EXPECTED_TABLES = (
    ("memory", "memory_records", 9),
    ("memory", "memory_audit_events", 7),
    ("public", "project_members", 6),
    # 9 欄（原 8 欄）：第 9 欄是 U19 membership-service 依 [FD3]=A 回補的 `cause`。
    # 這個數字與 verify_meta_schema.sql 的 P5 必須一致——兩邊都是「結束碼 0 代表
    # 什麼」的一部分，漂移的後果是這支腳本在一個其實正確的資料庫上 rollback。
    ("public", "reselection_events", 9),
    ("public", "system_requirement_fields", 9),
)

# (schema, table, index)
EXPECTED_INDEXES = (
    ("memory", "memory_records", "ix_memory_records_owner_user_id"),
    ("memory", "memory_records", "ix_memory_records_expires_at"),
    ("memory", "memory_records", "ix_memory_records_embedding_model"),
    # U8/NFR3.22（[N2]=B）：相似度檢索的 HNSW 索引。
    #
    # **只加 SQL 而不加這一列的後果是「索引被建立但不被驗證」**——這支腳本
    # 「結束碼 0」的語意會悄悄變窄而無人察覺
    # （infrastructure-specification.md §二之二 的第 3 項，blocking）。
    # 反方向（只加這一列而不加 SQL）則會讓腳本在一個其實正確的資料庫上
    # rollback。兩者都要做，順序無關。
    ("memory", "memory_records", "ix_memory_records_embedding_hnsw"),
    ("memory", "memory_audit_events", "ix_memory_audit_events_occurred_at"),
    ("memory", "memory_audit_events", "ix_memory_audit_events_memory_id"),
    ("public", "reselection_events", "ix_reselection_events_unack"),
    ("public", "reselection_events", "ix_reselection_events_project_id"),
    # U23（[PPN1]=A）：專案清單改讀成員列，可見性查詢的成員那一半以 user_id 出發。
    # 與 `BLOCK_SENTINELS["J"]` 的哨兵不同：哨兵只證明 DDL 文字在區塊內，這一列
    # 才證明索引真的被建立（test_membership_data.test_M3b 鎖住這一列）。
    ("public", "project_members", "ix_project_members_user_id"),
)

EXPECTED_CONSTRAINTS = (
    "ck_memory_records_kind",
    "ck_memory_records_content_not_blank",
    "ck_memory_records_episodic_has_expiry",
    "ck_memory_audit_events_action",
    "ck_project_members_role",
    "uq_project_members_project_user",
    # U19/[FD3]=A：cause 的封閉列舉。與 previous_role／new_role（刻意無 CHECK）
    # 的分野是它的兩個值是定案而非未決事項。缺它的後果不是寫入失敗而是
    # **橫幅永遠不出現**（BR5.5 以字面值比對 cause，拼錯即永不命中且無錯誤）。
    "ck_reselection_events_cause",
    "uq_system_requirement_fields_group_key",
    "ck_system_requirement_fields_cleared_has_null_value",
)

# (schema.table, 被參照的表, 期望的 confdeltype)：'c' = CASCADE、'a' = NO ACTION
EXPECTED_FK_DELETE_ACTIONS = (
    ("public", "project_members", "projects", "c"),
    ("public", "project_members", "users", "a"),
    ("public", "system_requirement_fields", "systems", "c"),
)

# 必須**沒有**外鍵的那一對（[ND1]=A：改選稽核在專案被刪後獨立存活）。
FORBIDDEN_FKS = (("public", "reselection_events", "projects"),)

# ---------------------------------------------------------------------------
# U20 的欄位級後條件（BR47.3／NFR20.25）
#
# **不能**用上面的 `FORBIDDEN_FKS` 表達：它以（表、被參照表）為鍵，而同一張表的
# `updated_by` 合法地指向 `users`——加 (system_requirement_fields, users) 會把那條
# 合法外鍵一起擋掉。所以這裡以**欄位**為單位，並把「`updated_by` 的外鍵仍在」
# 寫成正向條件，使「收斂時誤刪了 updated_by 的外鍵」也會讓結束碼非零。
# ---------------------------------------------------------------------------

# (schema, table, column, information_schema.columns.data_type, 字元長度上限)
EXPECTED_COLUMN_TYPES = (
    ("public", "system_requirement_fields", "updated_on_behalf_of",
     "character varying", 64),
)

# (schema, table, column)：這一欄上不得有任何外鍵（[FD1]=A：agent 組識別字）
COLUMNS_WITHOUT_FK = (
    ("public", "system_requirement_fields", "updated_on_behalf_of"),
)

# (schema, table, column, 被參照的表)：這一欄上必須有指向該表的外鍵
EXPECTED_COLUMN_FKS = (
    ("public", "system_requirement_fields", "updated_by", "users"),
)

# 某一欄上的外鍵：以 conkey 比對欄位，而不是以約束名稱（名稱由 PostgreSQL 自動產生）。
_COLUMN_FK_SQL = (
    "SELECT count(*) FROM pg_constraint con "
    "JOIN pg_class t ON t.oid = con.conrelid "
    "JOIN pg_namespace ns ON ns.oid = t.relnamespace "
    "JOIN pg_attribute a ON a.attrelid = con.conrelid "
    "AND a.attnum = ANY (con.conkey) "
    "JOIN pg_class rt ON rt.oid = con.confrelid "
    "WHERE ns.nspname = :s AND t.relname = :t AND con.contype = 'f' "
    "AND a.attname = :c"
)

# 表 COMMENT 不得為空的那些（BR2.2 與 U5 的 DG-1 都把 COMMENT 當防呆機制）。
EXPECTED_TABLE_COMMENTS = (
    "public.system_requirement_fields",
    "public.project_members",
    "public.reselection_events",
    "memory.memory_audit_events",
)


def extract_blocks(sql_text: str, letters: tuple[str, ...]) -> list[tuple[str, str]]:
    """從 `schema_rbac.sql` 取出指定的區塊文字，照 `letters` 給定的順序回傳。

    區塊標題的形狀是「`-- ####…` 行 ＋ `-- <字母>) …` 行」，區塊的範圍是從它自己的
    `####` 行到**下一個**區塊標題的 `####` 行（或檔尾的 `COMMIT;`）。
    """
    lines = sql_text.splitlines(keepends=True)
    banner = re.compile(r"^--\s*#{10,}\s*$")
    letter_line = re.compile(r"^--\s+([A-Z])\)")

    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not banner.match(line):
            continue
        if i + 1 < len(lines):
            m = letter_line.match(lines[i + 1])
            if m:
                starts.append((i, m.group(1)))

    commit_at = next(
        (i for i, line in enumerate(lines) if line.strip() == "COMMIT;"), len(lines)
    )

    spans: dict[str, str] = {}
    for idx, (start, letter) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else commit_at
        if letter in spans:
            raise RuntimeError(
                f"{SCHEMA_FILE.name} 有兩個 `{letter})` 區塊標題——"
                "本腳本以字母定位區塊，重複會讓它執行錯的那一個"
            )
        spans[letter] = "".join(lines[start:end])

    extracted: list[tuple[str, str]] = []
    for letter in letters:
        body = spans.get(letter)
        if body is None:
            raise RuntimeError(
                f"在 {SCHEMA_FILE.name} 找不到 `{letter})` 區塊。"
                "區塊標題被改名或移除了——本腳本是既有環境取得這些物件的唯一路徑，"
                "所以這裡不能靜默跳過"
            )
        for sentinel in BLOCK_SENTINELS[letter]:
            if sentinel not in body:
                raise RuntimeError(
                    f"`{letter})` 區塊缺少哨兵字串 {sentinel!r}——"
                    "解析抓到的範圍不對，或該區塊的內容被搬走了"
                )
        extracted.append((letter, body))
    return extracted


def _scalar(conn, sql: str, params: dict | None = None):
    from sqlalchemy import text

    return conn.execute(text(sql), params or {}).scalar()


def assert_prerequisites(conn) -> None:
    """`J)` 的外鍵指向 U4 的表；缺了就以可讀訊息擋下，而不是丟生的 UndefinedTable。"""
    missing = [
        name
        for name in REQUIRED_PREEXISTING_TABLES
        if not _scalar(
            conn,
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t",
            {"t": name},
        )
    ]
    if missing:
        raise RuntimeError(
            "前置條件不足：public schema 缺少 " + "、".join(missing) + "。"
            "J) 的 project_members.project_id 與 system_requirement_fields.system_id "
            "指向 projects／systems（U4 的表），故 U4 的遷移必須先跑過："
            "cd backend && python scripts/run_hierarchy_migration.py"
            "（見 DEPLOY.md 第 2.2.7 節）"
        )


def verify_column_postconditions(conn) -> list[str]:
    """`U20` 的欄位級後條件（`BR47.3`／`NFR20.25`）。回傳問題清單。

    單獨成一個函式，是因為它驗的是 `J)` 區塊裡**條件式收斂**的結果：
    全新建立的表必然通過，真正要擋的是「既有資料庫的收斂沒有發生或做錯了」——
    而那只有在這支腳本上才會被執行到（`psql -f schema_rbac.sql` 沒有後條件）。
    """
    problems: list[str] = []

    for schema, table, column, data_type, max_length in EXPECTED_COLUMN_TYPES:
        row = conn.execute(
            _text(
                "SELECT data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema = :s AND table_name = :t AND column_name = :c"
            ),
            {"s": schema, "t": table, "c": column},
        ).first()
        if row is None:
            problems.append(f"欄位 {schema}.{table}.{column} 不存在")
        elif row[0] != data_type or row[1] != max_length:
            problems.append(
                f"欄位 {schema}.{table}.{column} 應為 {data_type}({max_length})，"
                f"實際 {row[0]}({row[1]})——J) 區塊的收斂沒有發生（BR47.2）"
            )

    for schema, table, column in COLUMNS_WITHOUT_FK:
        found = _scalar(conn, _COLUMN_FK_SQL, {"s": schema, "t": table, "c": column})
        if found:
            problems.append(
                f"{schema}.{table}.{column} 不得有外鍵（[FD1]=A：它是 agent 組識別字），"
                f"實際有 {found} 條"
            )

    for schema, table, column, referenced in EXPECTED_COLUMN_FKS:
        found = _scalar(
            conn,
            _COLUMN_FK_SQL + " AND rt.relname = :r",
            {"s": schema, "t": table, "c": column, "r": referenced},
        )
        if not found:
            problems.append(
                f"{schema}.{table}.{column} 缺少指向 {referenced} 的外鍵"
                "（收斂只應移除 updated_on_behalf_of 的那一條）"
            )

    return problems


def _text(sql: str):
    from sqlalchemy import text

    return text(sql)


def verify_postconditions(conn) -> list[str]:
    """逐項查證後條件。回傳問題清單；空清單代表全部存在。"""
    problems: list[str] = []

    if not _scalar(conn, "SELECT count(*) FROM pg_extension WHERE extname = 'vector'"):
        problems.append("擴充 vector 不存在（memory_records 的 vector(1024) 需要它）")

    for schema in EXPECTED_SCHEMAS:
        if not _scalar(
            conn,
            "SELECT count(*) FROM information_schema.schemata "
            "WHERE schema_name = :s",
            {"s": schema},
        ):
            problems.append(f"schema {schema} 不存在")

    for schema, table, columns in EXPECTED_TABLES:
        actual = _scalar(
            conn,
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = :t",
            {"s": schema, "t": table},
        )
        if actual == 0:
            problems.append(f"表 {schema}.{table} 不存在")
        elif actual != columns:
            problems.append(
                f"表 {schema}.{table} 應有 {columns} 欄，實際 {actual} 欄"
            )

    for schema, table, index in EXPECTED_INDEXES:
        if not _scalar(
            conn,
            "SELECT count(*) FROM pg_indexes "
            "WHERE schemaname = :s AND tablename = :t AND indexname = :i",
            {"s": schema, "t": table, "i": index},
        ):
            problems.append(f"索引 {index}（{schema}.{table}）不存在")

    # partial index 的 WHERE 子句被拿掉之後索引仍然存在、查詢仍然正確，只是大小
    # 由「目前未確認數」變成「歷來總數」——失敗模式是效能，故必須單獨查。
    unack_def = _scalar(
        conn,
        "SELECT indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND indexname = 'ix_reselection_events_unack'",
    )
    if unack_def and "WHERE" not in unack_def.upper():
        problems.append(
            "ix_reselection_events_unack 不是 partial index（缺 WHERE "
            "acknowledged_at IS NULL）"
        )

    for name in EXPECTED_CONSTRAINTS:
        if not _scalar(
            conn, "SELECT count(*) FROM pg_constraint WHERE conname = :c", {"c": name}
        ):
            problems.append(f"約束 {name} 不存在")

    for schema, table, referenced, expected in EXPECTED_FK_DELETE_ACTIONS:
        actual = _scalar(
            conn,
            "SELECT con.confdeltype::text FROM pg_constraint con "
            "JOIN pg_class t ON t.oid = con.conrelid "
            "JOIN pg_namespace ns ON ns.oid = t.relnamespace "
            "JOIN pg_class rt ON rt.oid = con.confrelid "
            "WHERE ns.nspname = :s AND t.relname = :t AND con.contype = 'f' "
            "AND rt.relname = :r",
            {"s": schema, "t": table, "r": referenced},
        )
        if actual is None:
            problems.append(f"{schema}.{table} 缺少指向 {referenced} 的外鍵")
        elif actual != expected:
            problems.append(
                f"{schema}.{table} → {referenced} 的 ON DELETE 應為 "
                f"confdeltype={expected}，實際 {actual}"
            )

    for schema, table, referenced in FORBIDDEN_FKS:
        extra = _scalar(
            conn,
            "SELECT count(*) FROM pg_constraint con "
            "JOIN pg_class t ON t.oid = con.conrelid "
            "JOIN pg_namespace ns ON ns.oid = t.relnamespace "
            "JOIN pg_class rt ON rt.oid = con.confrelid "
            "WHERE ns.nspname = :s AND t.relname = :t AND con.contype = 'f' "
            "AND rt.relname = :r",
            {"s": schema, "t": table, "r": referenced},
        )
        if extra:
            problems.append(
                f"{schema}.{table} 不得有指向 {referenced} 的外鍵（[ND1]=A："
                "改選稽核必須在專案被刪後獨立存活），實際有 "
                f"{extra} 條"
            )

    problems.extend(verify_column_postconditions(conn))

    for qualified in EXPECTED_TABLE_COMMENTS:
        comment = _scalar(
            conn,
            # `cast(... AS regclass)` 而不是 `:q::regclass`——後者的 `::` 會讓
            # SQLAlchemy 的 `text()` 認不出 `:q` 是 bindparam，於是冒號原樣送到
            # 伺服器並以 `syntax error at or near ":"` 失敗（本機實測）。
            "SELECT obj_description(cast(:q AS regclass), 'pg_class')",
            {"q": qualified},
        )
        if not comment or not comment.strip():
            problems.append(f"表 {qualified} 的 COMMENT 為空")

    # BR1.2 的 grant 邊界：只開放 memory schema。
    if not _scalar(
        conn,
        "SELECT has_schema_privilege(current_user, 'memory', 'USAGE')",
    ):
        problems.append("current_user 對 schema memory 沒有 USAGE 權限")

    return problems


def main(argv: list[str] | None = None) -> int:
    """建立 `U5` ＋ `U18` 的全部新物件。回傳 0（成功）或非零（任何失敗）。

    `argv` 目前不接受任何選項；保留參數是為了讓測試能以同一個簽章呼叫。
    """
    if argv:
        print(f"未知的參數：{argv}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # 只印主機與資料庫名，**不印 DATABASE_URL 或其任何片段**。
    url = engine.url
    print(f"目標資料庫：host={url.host} database={url.database}", flush=True)

    try:
        blocks = extract_blocks(
            SCHEMA_FILE.read_text(encoding="utf-8"), BLOCKS_TO_RUN
        )
    except Exception as exc:
        logger.error("無法從 %s 取出 DDL：%s", SCHEMA_FILE.name, exc)
        traceback.print_exc(file=sys.stderr)
        return 1

    convergence_notices: list[str] = []
    try:
        # engine.begin()：成功則 commit、例外則 rollback。PostgreSQL 的 DDL 可交易，
        # 所以「部分成功而回報成功」這個狀態在這裡不存在。
        with engine.begin() as conn:
            assert_prerequisites(conn)

            # **不能用 `conn.exec_driver_sql()`**：它走 SQLAlchemy 的 pyformat
            # 參數路徑，於是 I) 區塊裡 `format('GRANT ... TO %I', current_user)`
            # 的 `%I` 會被當成參數佔位符而以
            # `only '%s', '%b', '%t' are allowed as placeholders, got '%I'` 失敗
            # （本機實測）。改走 DBAPI cursor：psycopg v3 的 `execute()` 在
            # **無參數**時不做任何 `%` 插值，並走 simple query protocol，故支援
            # 以分號分隔的多敘述字串——區塊內的 `DO $$ … $$` 因此可以原樣送出。
            # cursor 取自 `conn.connection`，與上面的 `engine.begin()` 是同一個
            # 連線、同一個交易。
            dbapi_conn = conn.connection
            # U20（OPEN-RF20-8）：J) 區塊的條件式收斂以 NOTICE 回報它做了什麼。
            # 只收以「U20 」開頭的那幾則——其餘區塊的 IF NOT EXISTS 會產生大量
            # 「already exists, skipping」通知，全部印出只會淹沒真正的訊息。
            driver_conn = getattr(dbapi_conn, "driver_connection", dbapi_conn)
            notice_handler = _u20_notice_collector(convergence_notices)
            can_listen = hasattr(driver_conn, "add_notice_handler")
            if can_listen:
                driver_conn.add_notice_handler(notice_handler)
            try:
                for letter, body in blocks:
                    cursor = dbapi_conn.cursor()
                    try:
                        cursor.execute(body)
                    finally:
                        cursor.close()
                    logger.info("已套用 schema_rbac.sql 的 %s) 區塊", letter)
            finally:
                if can_listen:
                    driver_conn.remove_notice_handler(notice_handler)

            problems = verify_postconditions(conn)
            if problems:
                raise RuntimeError(
                    "終檢未通過，已回滾（NFR8.3）：\n  - " + "\n  - ".join(problems)
                )
    except Exception as exc:
        # 不吞：訊息與完整 traceback 都寫到 stderr，並以非零結束碼收場（NFR8.3）。
        # 這與 backend/database.py 的 `_ensure_*` 家族刻意相反——那裡是
        # `logger.warning` 後繼續，於是「表沒建起來」會變成一行日誌加一個看起來
        # 正常啟動的服務。
        logger.error("meta schema migration 失敗：%s", exc)
        traceback.print_exc(file=sys.stderr)
        print(
            "結構未建立完成，交易已回滾——資料庫維持本次執行之前的狀態。"
            "處置後重跑即可（全部 DDL 為 IF NOT EXISTS 形狀，BR2.1）。",
            file=sys.stderr,
        )
        return 1

    print("meta schema migration 完成（U5 ＋ U18 ＋ U20 的欄位收斂）：")
    print(f"  schema          {len(EXPECTED_SCHEMAS)} 個：memory")
    print(f"  表              {len(EXPECTED_TABLES)} 張："
          + "、".join(f"{s}.{t}" for s, t, _ in EXPECTED_TABLES))
    print(f"  索引            {len(EXPECTED_INDEXES)} 個")
    print(f"  CHECK／UNIQUE   {len(EXPECTED_CONSTRAINTS)} 條")
    print(f"  外鍵刪除行為    {len(EXPECTED_FK_DELETE_ACTIONS)} 條已逐條核對"
          f"（另驗 {len(FORBIDDEN_FKS)} 條**必須不存在**的外鍵）")
    print(f"  欄位級條件      {len(EXPECTED_COLUMN_TYPES)} 條型別、"
          f"{len(COLUMNS_WITHOUT_FK)} 條「該欄無外鍵」、"
          f"{len(EXPECTED_COLUMN_FKS)} 條「該欄外鍵仍在」已核對：\n"
          "                  system_requirement_fields.updated_on_behalf_of 為 "
          "character varying(64) 且無外鍵、updated_by 指向 users 的外鍵仍在（BR47.3）")
    if convergence_notices:
        print("  U20 欄位收斂    本次**有執行**（欄位原為舊定義 integer）：")
        for message in convergence_notices:
            print(f"                  {message}")
    else:
        print("  U20 欄位收斂    本次未執行（欄位已是 varchar(64)；重跑不改動任何資料）")
    print("終檢通過：上述每一個物件都已在目標資料庫中查證存在（NFR8.3）。")
    print(
        "注意：本指令**不驗證** schema_rbac.sql 的其餘區塊，也不塞任何資料。"
        "唯一的例外是 U20 的欄位收斂（OPEN-RF20-8）：它只在 updated_on_behalf_of "
        "仍為舊定義 integer 時執行，型別轉換會重寫該欄並把舊值轉為 NULL"
        "（被清掉的非空值筆數見上方；契約 K-15 的「不含任何資料寫入」在這一點上"
        "不再逐字成立）。"
    )
    return 0


def _u20_notice_collector(sink: list[str]):
    """回傳一個 psycopg notice handler：只收 `J)` 區塊收斂敘述發出的通知。"""

    def handle(diagnostic) -> None:
        message = getattr(diagnostic, "message_primary", None) or ""
        if message.startswith("U20 "):
            sink.append(message)

    return handle


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
