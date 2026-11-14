#!/usr/bin/env python3
"""`U9 memory-purge` 的保留系統 actor seed —— **既有環境的唯一取得路徑**。

為什麼需要一支獨立腳本（而不是重跑 `schema_rbac.sql`，也不是掛上既有的遷移腳本）
=================================================================================

`schema_rbac.sql` 只掛在 `/docker-entrypoint-initdb.d/`，故它**只在空 data volume
執行**——既有的 `192.168.10.10` 拿不到 `K)` 區塊的那一列。而另外兩條看起來順理成章
的路徑**各自有一個會造成實害的理由不能走**：

**(a) 不能「重跑整支 `schema_rbac.sql`」。** `infrastructure-specification.md §五`
第 2 步逐字把它寫成「既有環境取得 seed 的唯一路徑」，但該檔是**單一交易**且
`C) RBAC` 區塊開頭那條敘述逐字為 `DELETE FROM role_permissions;`，其後重播設計預設
矩陣。檔頭自己也警告過（逐字「role_permissions 會 DELETE 後重播預設（Admin UI 調過
請先備份）」）。所以在既有環境重跑整支檔，會**清掉任何經 Admin UI 調整過的權限
矩陣**——那不是「可重跑所以安全」，那是一次無聲的設定回退。

**(b) 不能掛進 `run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN`。** 那支腳本的
成功輸出逐字宣告它「**不塞任何資料**」，而那句話對應契約 `K-15` 的
`observable_side_effects`（逐字「不含任何資料寫入」）。把一個 `INSERT` 加進去會讓
它的可觀察副作用與自己宣告的契約不一致，而**那個不一致只有讀過契約的人才看得
出來**（執行結果看起來完全正常）。

SQL 只有一份
------------

本腳本**不複製 SQL、也不複製解析器**：它 `import` `run_meta_schema_migration` 的
`extract_blocks()`，解析 `schema_rbac.sql` 的 `K)` 區塊並原樣執行同一份文字
（`team.md` 的單一真實來源規則——「無法寫測試鎖住一致性的副本不新增」）。
三條路徑因此**不可能漂移**：

| 路徑 | 機制 |
|---|---|
| 空 data volume | `docker-entrypoint-initdb.d` 跑整支 `schema_rbac.sql`（含 `K)`） |
| 既有環境 | **本腳本**解析並執行 `K)` |
| CI | `memory-schema` job 以 `psql -f schema_rbac.sql` 套用整支檔 |

用法（於 `backend/` 目錄，且 `DATABASE_URL` 已指向目標資料庫）::

    cd backend && python3 scripts/seed_retention_system_actor.py

單一交易，所以結束碼可被信任
----------------------------

全部敘述包在**一個**交易內，並在 COMMIT **之前**逐項查證後條件（見
`verify_postconditions`）。於是：

    結束碼 0  ⟺  那一列存在，且四道鎖中可在資料庫層查證的三道都成立

任一後條件不成立即 rollback 並以非零碼結束。重跑安全：`K)` 的 `INSERT` 帶
`ON CONFLICT (username) DO NOTHING`。

輸出的禁令
----------

**本腳本不得輸出 `DATABASE_URL` 或其任何片段。** 本 repo 為 public 且 Actions log
公開可讀（`project.md` 的機敏資料禁令）。要指出連線目標時只印**主機與資料庫名**，
沿用 `run_meta_schema_migration.py` 的同一形狀。

`password_hash` 的值**不是機密**：它是一個一次性隨機明文的 bcrypt hash，而那個明文
從未被記錄於任何地方（無已知前像，不可反推）。即使如此本腳本也只印它的**前綴
是否符合 bcrypt 格式**，不印整個值——沒有任何人需要讀它。
"""

from __future__ import annotations

import logging
import re
import sys
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

for _path in (SCRIPTS_DIR, BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# 解析器與 schema 檔路徑都取自既有腳本——**不複製**（見模組 docstring）。
from run_meta_schema_migration import SCHEMA_FILE, extract_blocks  # noqa: E402

from database import engine  # noqa: E402

logger = logging.getLogger("cloud360.retention_system_actor_seed")

# ---------------------------------------------------------------------------
# 哨符常數
#
# 這三個值在本 repo 共有三處物化：本檔、`schema_rbac.sql` 的 `K)` 區塊、
# 以及 `backend/scripts/purge_expired_memory.sql`。跨語言邊界使副本無法避免
# （SQL 檔不能 import Python 常數），故依 `team.md` 的單一真實來源規則，
# 新增副本的同一個 PR 必須附上鎖住一致性的測試——那個測試是
# `backend/tests/test_retention_purge_contract.py` 的
# `test_sentinel_username_has_one_source`，它以 regex 從兩個 `.sql` 檔**解析**出
# 字串再與本檔比對，而不是在測試檔內重新手寫一次。
#
# 拼錯的後果分兩種，兩種都不會在寫的那一刻被發現：清除 SQL 內拼錯 →
# 子查詢回 NULL → `actor_user_id` 的 NOT NULL 違反 → 整個清除交易中止（大聲）；
# 本檔拼錯 → 後條件查不到那一列 → rollback（大聲）。
# ---------------------------------------------------------------------------
SENTINEL_USERNAME = "SYSTEM.retention-purge"
SENTINEL_ROLE = "system"

BLOCK_LETTER = "K"

# `K)` 區塊的**結構性**哨兵由 `run_meta_schema_migration.BLOCK_SENTINELS["K"]` 承載，
# 且由 `extract_blocks()` 自己強制——本檔不複製它們。本檔只多加一項它獨有的檢查：
# 解析到的文字必須含**本檔常數**的哨符 username。這不是 SQL 的副本，而是
# 「本檔的常數與 `K)` 區塊實際寫的是同一個字串」這件事在執行期的檢查。
#
# （那個字串在本 repo 只有三處物化：`K)` 區塊、`purge_expired_memory.sql`、
# 本檔的 `SENTINEL_USERNAME`。三者由 `test_retention_purge_contract.py` 的
# `test_sentinel_username_has_one_source` 鎖住。）
EXTRA_SENTINELS = (f"'{SENTINEL_USERNAME}'",)

# bcrypt 的 modular crypt 前綴。`$2a$`／`$2b$`／`$2y$` 三者都是合法的 bcrypt 變體。
BCRYPT_PREFIX = re.compile(r"^\$2[aby]\$")

# `K)` 區塊**不得**包含的東西：它是 seed，不是 DDL，也不該碰權限矩陣。
# 這是對「有人把別的東西塞進 K) 區塊」的防線——本腳本會原樣執行它解析到的文字。
BLOCK_FORBIDDEN = (
    "DELETE FROM role_permissions",
    "DROP ",
    "TRUNCATE ",
)


def _scalar(conn, sql: str, params: dict | None = None):
    from sqlalchemy import text

    return conn.execute(text(sql), params or {}).scalar()


def assert_prerequisites(conn) -> None:
    """`users` 必須已存在；缺了就給可讀訊息，而不是丟生的 `UndefinedTable`。"""
    if not _scalar(
        conn,
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'users'",
    ):
        raise RuntimeError(
            "前置條件不足：public schema 缺少 users。本腳本只 seed 一列，"
            "不建表——空 volume 由 schema_rbac.sql 整支建立，"
            "既有環境見 DEPLOY.md 第 2.1 節"
        )


def verify_postconditions(conn) -> list[str]:
    """逐項查證後條件。回傳問題清單；空清單代表全部成立。

    這四項就是「結束碼 0 代表什麼」的全部內容，沒有別的。四道鎖中的第 1 道
    （username 含大寫、登入查詢的 `.lower()` 永不產生它）是**字串性質**而非資料庫
    狀態，故由 `test_retention_purge_contract.py` 的靜態斷言承載，不在此處。
    """
    from sqlalchemy import text

    problems: list[str] = []

    rows = conn.execute(
        text(
            "SELECT id, role, is_active, password_hash "
            "FROM users WHERE username = :u"
        ),
        {"u": SENTINEL_USERNAME},
    ).fetchall()

    if len(rows) != 1:
        problems.append(
            f"username = {SENTINEL_USERNAME!r} 應恰有 1 列，實際 {len(rows)} 列。"
            "0 列代表 K) 區塊的 INSERT 沒有生效（或 username 拼錯）；"
            "多於 1 列在 UNIQUE 索引之下不可能發生，若真的看到請先查 ix_users_username"
        )
        return problems

    _id, role, is_active, password_hash = rows[0]

    # 本檔的 SENTINEL_ROLE 必須與 `K)` 區塊實際寫入的值一致。這一項讓
    # SENTINEL_ROLE 成為載重常數而非裝飾——否則本檔改了它而 `K)` 沒改，
    # 下方的輸出會宣稱一個與資料庫不符的 role。
    if role != SENTINEL_ROLE:
        problems.append(
            f"K) 區塊寫入的 role 是 {role!r}，而本檔的 SENTINEL_ROLE 是 "
            f"{SENTINEL_ROLE!r}——兩者必須逐字相同"
        )

    # 鎖 4：is_active = FALSE —— auth.py 與 user_router.py 的登入路徑都據此拒絕。
    if is_active is not False:
        problems.append(
            f"鎖 4 不成立：is_active 應為 false，實際 {is_active!r}。"
            "為 true 時這一列是一個可被嘗試登入的帳號"
        )

    # 鎖 3：role 不是 canonical role —— 以**資料庫內的實際權限矩陣**判定，而不是
    # import services.rbac。理由：那條 import 鏈經過 services.auth，而後者在
    # 模組載入時執行 _resolve_secret_key()，在 APP_ENV 非 local/test/ci 且無
    # JWT_SECRET 的 shell 上會拋 RuntimeError——一支 seed 腳本不該因為一個與
    # 它無關的理由在 staging 上崩掉。role_permissions 內出現過的 role 集合就是
    # 矩陣實際授權的那些；本列的 role 不在其中 ⇒ 它一條權限都沒有。
    # 程式層的 CANONICAL_ROLES 字面比對由 test_retention_purge_contract.py 承載
    # （測試環境的 import 是安全的）。
    distinct_roles = _scalar(conn, "SELECT count(DISTINCT role) FROM role_permissions")
    if not distinct_roles:
        problems.append(
            "role_permissions 是空的，故「role 不在授權矩陣內」這項查證會恆真——"
            "拒絕以一個恆真的檢查回報成功。先確認目標資料庫已套用過 "
            "schema_rbac.sql 的 C) 區塊（或後端已啟動過一次）"
        )
    else:
        granted = _scalar(
            conn,
            "SELECT count(*) FROM role_permissions WHERE role = :r",
            {"r": role},
        )
        if granted:
            problems.append(
                f"鎖 3 不成立：role {role!r} 在 role_permissions 內有 {granted} 列，"
                f"故它是一個被授權的角色（矩陣目前涵蓋 {distinct_roles} 個角色）"
            )

    # 鎖 2：password_hash 是**格式合法**的 bcrypt hash。
    # 非 bcrypt 格式才是危險的那一種：bcrypt.checkpw 對它會拋 ValueError
    # （實測 `ValueError: Invalid salt`）而不是回 False，而 verify_password()
    # 沒有 try/except —— 詳見 schema_rbac.sql 的 K) 區塊註解與
    # nfr-design/security-design.md §1.4。
    if not isinstance(password_hash, str) or not BCRYPT_PREFIX.match(password_hash):
        shape = type(password_hash).__name__ if password_hash is None else "字串"
        problems.append(
            "鎖 2 不成立：password_hash 不符合 bcrypt 格式（應以 $2a$／$2b$／$2y$ "
            f"開頭，實際型別／形狀為 {shape}）。非 bcrypt 格式的值會讓 "
            "bcrypt.checkpw 拋 ValueError 而非回 False，而那會把一個 401 變成"
            "**未經驗證即可遠端觸發的 500**"
        )

    return problems


def main(argv: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if argv:
        print(
            "本指令不接受參數；連線目標取自 DATABASE_URL。",
            file=sys.stderr,
        )
        return 2

    # 只印主機與資料庫名，**不印 DATABASE_URL 或其任何片段**。
    url = engine.url
    print(f"目標資料庫：host={url.host} database={url.database}", flush=True)

    try:
        blocks = extract_blocks(SCHEMA_FILE.read_text(encoding="utf-8"), (BLOCK_LETTER,))
    except Exception as exc:
        logger.error("無法從 %s 取出 K) 區塊：%s", SCHEMA_FILE.name, exc)
        traceback.print_exc(file=sys.stderr)
        return 1

    (_letter, body) = blocks[0]

    missing = [s for s in EXTRA_SENTINELS if s not in body]
    if missing:
        logger.error(
            "`K)` 區塊不含 %s——本檔的 SENTINEL_USERNAME 與該區塊實際寫入的 "
            "username 不一致。本腳本拒絕執行一段它認不出來的文字",
            ", ".join(repr(s) for s in missing),
        )
        return 1

    present = [s for s in BLOCK_FORBIDDEN if s in body]
    if present:
        logger.error(
            "`K)` 區塊含有不該出現在 seed 區塊內的敘述 %s。"
            "本腳本會原樣執行它解析到的文字，故在此擋下",
            ", ".join(repr(s) for s in present),
        )
        return 1

    try:
        # engine.begin()：成功則 commit、例外則 rollback。
        with engine.begin() as conn:
            assert_prerequisites(conn)

            # **不用 `conn.exec_driver_sql()` 送整個區塊**：它走 SQLAlchemy 的
            # pyformat 參數路徑，而 `password_hash` 的 bcrypt 值含 `$`、COMMENT
            # 內含百分比以外的各種字元——沿用 run_meta_schema_migration.py 已實測
            # 的做法：取 DBAPI cursor，psycopg v3 的 `execute()` 在**無參數**時
            # 不做任何 `%` 插值，並走 simple query protocol，故支援以分號分隔的
            # 多敘述字串（本區塊是 INSERT ＋ COMMENT 兩條）。
            # cursor 取自 `conn.connection`，與 `engine.begin()` 是同一個連線、
            # 同一個交易。
            dbapi_conn = conn.connection
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute(body)
            finally:
                cursor.close()
            logger.info("已套用 schema_rbac.sql 的 K) 區塊")

            problems = verify_postconditions(conn)
            if problems:
                raise RuntimeError(
                    "終檢未通過，已回滾：\n  - " + "\n  - ".join(problems)
                )
    except Exception as exc:
        # 不吞：訊息與完整 traceback 都寫到 stderr，並以非零結束碼收場。
        logger.error("保留系統 actor 的 seed 失敗：%s", exc)
        traceback.print_exc(file=sys.stderr)
        print(
            "seed 未完成，交易已回滾——資料庫維持本次執行之前的狀態。"
            "處置後重跑即可（INSERT 帶 ON CONFLICT DO NOTHING，重跑安全）。",
            file=sys.stderr,
        )
        return 1

    print("保留系統 actor 的 seed 完成（U9 memory-purge / NFR7.11）：")
    print(f"  username        {SENTINEL_USERNAME}")
    print(f"  role            {SENTINEL_ROLE}（不在 role_permissions 的授權集合內）")
    print("  is_active       false")
    print("  password_hash   符合 bcrypt 格式（值不輸出——沒有人需要讀它）")
    print(
        "終檢通過：上述三項已在目標資料庫中逐項查證。"
        "第四道鎖（username 含大寫，登入查詢的 .lower() 永不產生它）是字串性質，"
        "由 backend/tests/test_retention_purge_contract.py 承載。"
    )
    print(
        "提醒：**不要刪除這一列**。刪掉之後，90 天清除的稽核 INSERT 會全部因外鍵"
        "違反而失敗，而稽核與刪除在同一個交易內，所以整個清除交易中止。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
