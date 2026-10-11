"""`U9 memory-purge` 的靜態契約斷言——把「CI 不會抓」變成「CI 會抓」。

本檔讀取版控檔案的內容並比對，**不碰資料庫、不連網路、零新依賴**，落在既有
`backend` job 的 `python -m unittest discover -s tests` 之內。

為什麼需要它
============

本單元交付 SQL 與 YAML，而既有的六道 CI 閘門對它們幾乎完全無效：

| 閘門 | 對本單元 |
|---|---|
| `repo-contract` | 只讀 12 個 repo 層必要檔，看不到 `backend/scripts/*.sql` |
| frontend lint／`tsc -b` | 零前端面 |
| OpenAPI drift | 零端點 |
| `backend` 的 `unittest` | 既有測試走 in-memory SQLite，**沒有任何清除測試存在** |
| `memory-schema` | 驗 schema 形狀，不驗清除 SQL 的文字 |
| `ui-regression` | 零畫面 |

而本單元最危險的幾個缺陷**全部是單字之差**：

1. `RETURNING` 的欄位清單寫成星號 → 把個人對話歷程印進**公開可讀**的 Actions log。
2. 清除的 `WHERE` 少了 `kind = 'episodic'` → 刪掉 `FR4.5` 明文不約束的列（永久資料損失）。
3. dry-run 裡出現一條 DML → 一個名不副實的 dry-run，而操作者會據它按下啟用。
4. 哨符 username 在三處物化中有一處拼錯 → 外鍵違反，或永不命中。
5. 哨符 `password_hash` 不是合法的 bcrypt 格式 → **未經驗證即可遠端觸發的 500**。
6. watchdog 的查詢少了 `status=success` → 「每天都失敗」被判為新鮮。

這九條斷言讓上述每一項都變成 CI 的紅燈。

被檢查的是**可執行的 SQL**，不是整個檔案
=========================================

這些 `.sql` 檔帶大量說明性註解，其中會提到被禁止的樣式本身（例如解釋為什麼不能
用星號、或為什麼 `kind = 'episodic'` 不可省）。對**整個檔案**做子字串比對會有兩個
相反方向的缺陷，而第二個會讓斷言失去全部意義：

* 偽陽性：一句解釋禁令的註解讓禁令的斷言永遠紅燈。
* **偽陰性**：`test_purge_sql_scopes_to_episodic` 要求 `kind = 'episodic'`
  **存在**——而該字串也出現在同檔的註解裡。若比對整檔，把它從 `WHERE` 子句
  **刪掉**之後測試仍會綠燈，因為註解還在。那是一條驗不到東西的斷言。

故下方的 `executable_sql()` 先剝掉 psql 元指令與 `--` 註解。它的前提（無 `/* */`
區塊註解、無 `$$` 錢號引用、`--` 不出現在字串字面值內）由
`test_sql_comment_stripping_assumptions_hold` 機械驗證——前提被破壞時那條會紅燈，
而不是其他斷言靜默地檢查錯的文字。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# `tests.helpers` 的 import 只為它的**副作用**：把 `backend/` 與 `backend/services/`
# 放上 `sys.path`，並在驅動沒裝時 stub `psycopg`。沿用既有形狀（`test_rbac.py` 等
# 全部這樣做），不自創一套路徑設定。本檔不碰資料庫，故不用它的 session 工具。
import tests.helpers  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

SCHEMA_FILE = REPO_ROOT / "schema_rbac.sql"
PURGE_SQL = BACKEND_DIR / "scripts" / "purge_expired_memory.sql"
DRY_RUN_SQL = BACKEND_DIR / "scripts" / "purge_dry_run.sql"
SEED_SCRIPT = BACKEND_DIR / "scripts" / "seed_retention_system_actor.py"
WATCHDOG_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "memory-retention-watchdog.yml"
PURGE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "memory-retention-purge.yml"

SQL_FILES_UNDER_TEST = (PURGE_SQL, DRY_RUN_SQL)


def executable_sql(sql_text: str) -> str:
    """回傳剝掉 psql 元指令與 `--` 註解之後的 SQL 文字。

    規則只有兩條，刻意保持到可以一眼核對的程度：
      1. 丟掉以 `\\` 開頭的行（`\\set`／`\\echo`／`\\i` 等 psql 元指令）。
      2. 其餘每行在第一個 `--` 處截斷。

    前提由 `test_sql_comment_stripping_assumptions_hold` 驗證。
    """
    kept: list[str] = []
    for raw in sql_text.splitlines():
        if raw.lstrip().startswith("\\"):
            continue
        kept.append(raw.split("--", 1)[0])
    return "\n".join(kept)


def k_block(schema_text: str) -> str:
    """從 `schema_rbac.sql` 取出 `K)` 區塊的文字。

    **刻意不 import `run_meta_schema_migration.extract_blocks()`**，雖然那是生產
    用的解析器。理由是 `project.md` 的那條教訓：被檢查的東西與檢查的依據不該是
    同一個人的記憶——若那支解析器抓錯範圍，借用它的測試會**跟著抓錯**而仍然綠燈。
    這裡以區塊標題的形狀獨立重新界定邊界，故兩者不一致時會有人發現。
    附帶好處：本檔不因此把 `database.py`／SQLAlchemy engine 拉進 `backend` job
    的 import 鏈。
    """
    lines = schema_text.splitlines(keepends=True)
    banner = re.compile(r"^--\s*#{10,}\s*$")
    letter = re.compile(r"^--\s+([A-Z])\)")

    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if banner.match(line) and i + 1 < len(lines):
            m = letter.match(lines[i + 1])
            if m:
                starts.append((i, m.group(1)))

    commit_at = next(
        (i for i, line in enumerate(lines) if line.strip() == "COMMIT;"), len(lines)
    )

    hits = [idx for idx, (_, lt) in enumerate(starts) if lt == "K"]
    if len(hits) != 1:
        raise AssertionError(
            f"{SCHEMA_FILE.name} 應有恰好一個 `K)` 區塊標題，實際 {len(hits)} 個"
        )
    at = hits[0]
    start = starts[at][0]
    end = starts[at + 1][0] if at + 1 < len(starts) else commit_at
    return "".join(lines[start:end])


# `K)` 區塊的 INSERT：四個欄位的值依序為 username／password_hash／role／is_active。
K_BLOCK_INSERT = re.compile(
    r"INSERT\s+INTO\s+users\s*\(\s*username\s*,\s*password_hash\s*,\s*role\s*,"
    r"\s*is_active\s*\)\s*VALUES\s*\(\s*"
    r"'([^']*)'\s*,\s*"  # username
    r"'([^']*)'\s*,\s*"  # password_hash
    r"'([^']*)'\s*,\s*"  # role
    r"(TRUE|FALSE)\s*\)",
    re.IGNORECASE,
)

BCRYPT_PREFIX = re.compile(r"^\$2[aby]\$")


class RetentionPurgeContractTest(unittest.TestCase):
    """九條靜態斷言 ＋ 一條保護前提的斷言。"""

    @classmethod
    def setUpClass(cls) -> None:
        for path in (
            SCHEMA_FILE,
            PURGE_SQL,
            DRY_RUN_SQL,
            SEED_SCRIPT,
            WATCHDOG_WORKFLOW,
            PURGE_WORKFLOW,
        ):
            if not path.exists():
                raise AssertionError(f"本單元的交付物不存在：{path}")
        cls.schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
        cls.k_block_text = k_block(cls.schema_text)
        # 與兩個 `.sql` 檔同樣的理由，而這一處是**實測踩到的**：`K)` 區塊的註解
        # 逐字解釋為什麼 `ON CONFLICT (username) DO NOTHING` 不可省，於是對整個
        # 區塊做子字串比對時，把那個子句從 `INSERT` **刪掉**之後斷言仍然綠燈。
        # 突變驗證 3 抓到了它（`memory-schema` 的「第二次套用」步驟紅燈，而這條
        # 斷言沒有），故本檔的 `K)` 相關斷言一律跑在剝除後的文字上。
        cls.k_block_exec = executable_sql(cls.k_block_text)
        cls.purge_text = PURGE_SQL.read_text(encoding="utf-8")
        cls.purge_exec = executable_sql(cls.purge_text)
        cls.dry_run_text = DRY_RUN_SQL.read_text(encoding="utf-8")
        cls.dry_run_exec = executable_sql(cls.dry_run_text)
        cls.seed_text = SEED_SCRIPT.read_text(encoding="utf-8")
        cls.watchdog_text = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
        cls.purge_workflow_text = PURGE_WORKFLOW.read_text(encoding="utf-8")

        m = K_BLOCK_INSERT.search(cls.k_block_exec)
        if not m:
            raise AssertionError(
                f"在 {SCHEMA_FILE.name} 的 `K)` 區塊內找不到預期形狀的 "
                "`INSERT INTO users (username, password_hash, role, is_active) VALUES (…)`"
                "——區塊內容被改過，本檔的其餘斷言失去依據"
            )
        cls.seed_username, cls.seed_hash, cls.seed_role, cls.seed_is_active = m.groups()

    # -- 0：保護上面那個剝除器的前提 --------------------------------------

    def test_sql_comment_stripping_assumptions_hold(self) -> None:
        """`executable_sql()` 的兩條規則只在三個前提下正確，這裡逐一驗證。

        它不是「多一條保險」：本檔有五條斷言建立在剝除結果上，前提被破壞時
        它們會**靜默地**檢查錯的文字。
        """
        subjects = [
            (p.name, p.read_text(encoding="utf-8")) for p in SQL_FILES_UNDER_TEST
        ]
        subjects.append((f"{SCHEMA_FILE.name} 的 K) 區塊", self.k_block_text))
        for name, text in subjects:
            with self.subTest(file=name):
                self.assertNotIn(
                    "/*",
                    text,
                    "本檔的剝除器不處理 `/* */` 區塊註解。要用它請先擴充剝除器",
                )
                self.assertNotIn(
                    "$$",
                    text,
                    "本檔的剝除器不處理 `$$` 錢號引用（其中的 `--` 不是註解）。"
                    "要用它請先擴充剝除器",
                )
                for lineno, raw in enumerate(text.splitlines(), start=1):
                    if raw.lstrip().startswith("\\"):
                        continue
                    head = raw.split("--", 1)[0]
                    if "--" not in raw:
                        continue
                    self.assertEqual(
                        head.count("'") % 2,
                        0,
                        f"{name}:{lineno} 的 `--` 出現在一個未閉合的字串字面值"
                        "之內，故它不是註解——剝除器會從那裡截斷並丟掉真正的 SQL",
                    )

    # -- 1 --------------------------------------------------------------

    def test_purge_sql_never_returns_all_columns(self) -> None:
        """清除 SQL 只許 `RETURNING id`，絕不許回傳全部欄位。

        後果不是「log 太長」：本 repo 為 public、Actions log 公開可讀，而被回傳的
        列含 `content`——使用者的私人對話歷程。一個單字之差，等同公開發布。
        """
        offenders = re.findall(r"RETURNING\s+\*", self.purge_exec, re.IGNORECASE)
        self.assertEqual(
            offenders,
            [],
            "purge_expired_memory.sql 的可執行 SQL 回傳了全部欄位。"
            "那會把 memory_records.content 印進公開可讀的 Actions log"
            "（monitoring-design.md §五之一）。只許 RETURNING id",
        )
        returning = re.findall(r"RETURNING\s+([A-Za-z_*]+)", self.purge_exec)
        self.assertNotEqual(returning, [], "清除 SQL 應至少有一個 RETURNING 子句")
        for column in returning:
            self.assertEqual(
                column.lower(), "id", f"RETURNING 只許取 id，實際取了 {column!r}"
            )

    # -- 2 --------------------------------------------------------------

    def test_purge_sql_scopes_to_episodic(self) -> None:
        """清除的選取條件必須含 `kind = 'episodic'`。

        `FR4.5` 逐字只約束 episodic memory，而 `ck_memory_records_episodic_has_expiry`
        **不禁止**非 episodic 的列帶 `expires_at`——所以少了這個條件，一列
        `kind = 'semantic'` 而恰好帶了過去 `expires_at` 的記憶會被刪除，
        而那是 `FR4.5` 明文不約束的**永久資料損失**。
        """
        self.assertIn(
            "kind = 'episodic'",
            self.purge_exec,
            "purge_expired_memory.sql 的可執行 SQL 不含 kind = 'episodic'。"
            "少了它，清除會刪到 FR4.5 不約束的非 episodic 列（永久資料損失）。"
            "注意本斷言比對的是**剝掉註解後**的 SQL——同檔註解裡的那個字串不算",
        )
        self.assertIn(
            "expires_at < now()",
            self.purge_exec,
            "清除的截止欄位必須是 expires_at（K-05 的欄位契約）",
        )

    # -- 3 --------------------------------------------------------------

    def test_purge_sql_does_not_override_connection_identity(self) -> None:
        """清除不得顯式以其他身分連線（`NFR6.10` 保留的實質要求）。

        `NFR6.10` 本身目前是恆真的（`POSTGRES_USER` 即 superuser，`[ND2]`=A），
        所以它宣稱的不是「建立了一道邊界」，而是「維持現況、不新增更高權限的路徑」。
        可審查的內容就是這一條：SQL 與呼叫端都不得帶身分覆寫或額外的連線字串。
        """
        self.assertNotIn(
            " -U ",
            self.purge_text,
            "purge_expired_memory.sql 含身分覆寫旗標。連線身分由 "
            "docker compose exec 進入容器後決定（nfr-design/security-design.md §二）",
        )
        for needle in ("PGPASSWORD", "postgresql://", "postgres://", "password="):
            self.assertNotIn(
                needle,
                self.purge_text,
                f"purge_expired_memory.sql 含 {needle!r}——不得出現任何連線字串或密碼",
            )
        # 呼叫端（workflow）同樣不得覆寫。這一半在上游的二元判準裡被逐字點名
        # （「workflow 的 psql 呼叫不含 -U 覆寫」），所以它也該被機械檢查。
        for line in self.purge_workflow_text.splitlines():
            if "psql" not in line:
                continue
            # 跳過註解行。本 workflow 的註解**刻意**討論這條禁令（說明為什麼
            # 身分是從容器自己的環境取得而非覆寫），而一條解釋禁令的註解不該
            # 讓禁令的斷言紅燈——這與 `project.md` 對 secret 掃描樣式的警告同形。
            if line.lstrip().startswith("#"):
                continue
            self.assertNotIn(
                " -U ",
                line,
                "memory-retention-purge.yml 的 psql 呼叫帶了身分覆寫旗標："
                f"{line.strip()}",
            )

    # -- 4 --------------------------------------------------------------

    def test_dry_run_sql_is_read_only(self) -> None:
        """dry-run 必須只讀。

        它存在的理由是「清除不可回滾」（`OPEN-ID9-4`）：操作者會據它的輸出
        決定要不要啟用排程。一個名不副實的 dry-run 比沒有 dry-run 更糟。
        """
        forbidden = ("delete", "insert", "update", "truncate", "drop", "alter", "create")
        found = sorted(
            {
                kw
                for kw in forbidden
                if re.search(rf"\b{kw}\b", self.dry_run_exec, re.IGNORECASE)
            }
        )
        self.assertEqual(
            found,
            [],
            f"purge_dry_run.sql 的可執行 SQL 含 DML／DDL 關鍵字 {found}——"
            "dry-run 必須只有 SELECT",
        )
        self.assertIn("select", self.dry_run_exec.lower(), "dry-run 應該有 SELECT")
        # 不得印出可識別資料。`content` 與 `embedding` 一個字都不許出現在
        # 可執行的 SELECT 清單裡，`*` 同理（它會把兩者一起帶出來）。
        for needle in ("content", "embedding"):
            self.assertNotIn(
                needle,
                self.dry_run_exec.lower(),
                f"purge_dry_run.sql 的可執行 SQL 提到 {needle!r}——"
                "Actions log 公開可讀，不得印出記憶內容或向量",
            )
        self.assertNotIn(
            "select *",
            re.sub(r"\s+", " ", self.dry_run_exec).lower(),
            "purge_dry_run.sql 不得 SELECT *——那會把 content 與 embedding 一起印出來",
        )

    # -- 5 --------------------------------------------------------------

    def test_system_actor_seed_is_rerunnable(self) -> None:
        """`K)` 區塊的 seed 必須可安全重跑。

        `schema_rbac.sql` 是**單一交易**，而 `ix_users_username` 是 UNIQUE。
        少了 `ON CONFLICT ... DO NOTHING`，重跑整支檔的後果不是「seed 失敗」，
        是**整支腳本從那一行起全部中止**——包含其下方的整個 `C) RBAC` 區塊。
        """
        self.assertIn(
            "ON CONFLICT (username) DO NOTHING",
            self.k_block_exec,
            "schema_rbac.sql 的 K) 區塊缺少 ON CONFLICT (username) DO NOTHING。"
            "本檔是單一交易，UNIQUE 違反會讓其後的所有敘述一併中止",
        )

    # -- 6 --------------------------------------------------------------

    def test_sentinel_username_has_one_source(self) -> None:
        """哨符 username 的三處物化必須逐字相同。

        跨語言邊界使副本無法避免（`.sql` 檔不能 import Python 常數），故依
        `team.md` 的單一真實來源規則，這個測試就是那個「鎖住兩者一致的測試」。

        **三個值都是從被測檔案本身解析出來的**，測試檔內不重新手寫哨符值——
        手寫會讓測試與被測內容變成同一個人的記憶（`project.md` 逐字：
        「腳本必須從產出檔本身解析輸入，不得在腳本裡重新列舉」）。
        """
        from_purge = re.findall(
            r"FROM\s+users\s+WHERE\s+username\s*=\s*'([^']+)'", self.purge_exec
        )
        self.assertEqual(
            len(from_purge),
            1,
            "purge_expired_memory.sql 的可執行 SQL 應有恰好一處以 username 查 "
            f"actor id，實際 {len(from_purge)} 處",
        )

        from_seed = re.findall(
            r'^SENTINEL_USERNAME\s*=\s*"([^"]+)"', self.seed_text, re.MULTILINE
        )
        self.assertEqual(
            len(from_seed), 1, "seed 腳本應有恰好一個 SENTINEL_USERNAME 常數"
        )

        self.assertEqual(
            {self.seed_username, from_purge[0], from_seed[0]},
            {self.seed_username},
            "哨符 username 在三處不一致："
            f"schema_rbac.sql 的 K) 區塊={self.seed_username!r}、"
            f"purge_expired_memory.sql={from_purge[0]!r}、"
            f"seed 腳本={from_seed[0]!r}。"
            "清除 SQL 內拼錯 → 子查詢回 NULL → actor_user_id 的 NOT NULL 違反；"
            "seed 腳本拼錯 → 後條件查不到那一列。兩者都是大聲失敗，但都在上線後才發生",
        )

        # 第一道鎖：username **含大寫字母**，故 user_router.py 登入查詢的
        # `.lower()` 永遠不可能產生它 → 查詢回 None → 401，而
        # `verify_password` 根本不被呼叫。
        self.assertNotEqual(
            self.seed_username,
            self.seed_username.lower(),
            "哨符 username 必須含大寫字母：登入查詢是 "
            "`User.username == request.username.lower()`，全小寫的哨符是**可被命中的**，"
            "而被命中之後走的是 verify_password（見 test_sentinel_hash_...）",
        )

    # -- 7 --------------------------------------------------------------

    def test_sentinel_hash_rejects_cleanly_without_raising(self) -> None:
        """`verify_password(任意, 哨符 hash)` 必須回 `False` **且不拋例外**。

        這是本檔最重要的一條，因為它把一句轉述變成可執行的斷言。

        上游 `security-design.md §1.2` 要求 `password_hash` 是「結構上不可能比對
        成功的哨符字串（**非 bcrypt 格式**）」，理由逐字是「給一個非 bcrypt 格式的
        值使 `bcrypt.checkpw` 不可能回 True」。**那個理由正確但不完整**：
        `bcrypt.checkpw` 對非 bcrypt 格式的 hash **拋 `ValueError`**（實測
        `ValueError: Invalid salt`），而 `verify_password` 沒有任何 `try/except`，
        於是 401 會變成 **500**——而 500／401 的差異構成一個帳號存在性 oracle。

        故本單元改用**格式合法**的 bcrypt hash（明文為一次性隨機值且未被記錄）。
        `assertFalse` 不夠：必須同時確認**不拋例外**，因為拋例外正是那個 500 的成因。
        """
        from services.auth import verify_password

        self.assertRegex(
            self.seed_hash,
            BCRYPT_PREFIX,
            "哨符 password_hash 必須是格式合法的 bcrypt hash（$2a$／$2b$／$2y$ 開頭）",
        )

        # 候選明文上限 **72 位元組**，而這個上限是本輪實測發現的一件事，不是湊數：
        # `bcrypt.checkpw` 對**超過 72 位元組的明文**也拋
        # `ValueError: password cannot be longer than 72 bytes`——與 hash 的格式
        # 無關。而 `verify_password` 沒有 try/except，`user_router.py` 的登入又是
        # 先查使用者、再比對密碼，所以
        #   **任何已存在的帳號 ＋ 73 位元組以上的密碼 → 500（而不存在的帳號 → 401）**
        # 是一個今天就可用、未經驗證即可遠端觸發的帳號存在性 oracle。
        #
        # 那是**既有缺陷**（`auth.py` 不屬本 packaging 單元，且 `team.md` 明文反對
        # 在功能變更的同一個 PR 夾帶既有共用程式的重構），本輪記入 `OPEN-CG9-2`
        # 並在 `code-summary.md` 具名回報。**此處刻意不為它寫斷言**：斷言它會拋
        # 等於把缺陷鎖進契約，而斷言它不拋會讓 CI 為一個不在範圍內的既有問題紅燈。
        # 本測試要驗的是**哨符 hash 本身**乾淨地回 False，故候選限於合法長度。
        for candidate in ("", "anything", self.seed_username, "x" * 72):
            with self.subTest(candidate=candidate[:20]):
                try:
                    result = verify_password(candidate, self.seed_hash)
                except Exception as exc:  # noqa: BLE001 - 拋例外本身就是被測的缺陷
                    self.fail(
                        f"verify_password 對哨符 hash 拋了 {type(exc).__name__}: {exc}。"
                        "那正是 POST /api/auth/login 變成未經驗證即可遠端觸發的 500 的"
                        "成因（user_router.py 先比對密碼、後查 is_active）"
                    )
                self.assertFalse(
                    result,
                    "哨符 hash 不得與任何明文比對成功——它的明文是一次性隨機值，"
                    "從未被記錄，所以這裡回 True 代表 hash 被換掉了",
                )

    # -- 8 --------------------------------------------------------------

    def test_watchdog_filters_to_successful_runs(self) -> None:
        """watchdog 的查詢必須帶 `status=success`。

        `gh api .../runs` 預設回**所有** run，含失敗的。只取最新一筆並看它的時間，
        則「**每天都失敗**」會被判為新鮮——而那正是最需要告警的狀況之一
        （`cicd-pipeline.md §四之一`）。
        """
        # **比對的是那一行查詢本身，不是整個檔案。** 整檔比對在本輪的突變驗證 6
        # 實測為**偽陰性**：把 `status=success` 從 `gh api` 的 URL 拿掉之後，
        # 一句解釋這條禁令的註解與一句 issue 文案仍然含有那個字串，於是斷言綠燈
        # 而 watchdog 已經壞了。這與 `k_block` 那一處是同一個形狀，本輪一併修正。
        query_lines = [
            line
            for line in self.watchdog_text.splitlines()
            if "/runs?" in line and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            len(query_lines),
            1,
            "memory-retention-watchdog.yml 應有恰好一行查詢 run 歷史的 `gh api`，"
            f"實際 {len(query_lines)} 行",
        )
        self.assertIn(
            "status=success",
            query_lines[0],
            "memory-retention-watchdog.yml 的 run 查詢沒有過濾 status=success。"
            "少了它，一個每天都失敗的清除會被判為新鮮——而那正是最需要告警的"
            f"狀況之一（cicd-pipeline.md §四之一）。該行：{query_lines[0].strip()}",
        )
        self.assertIn(
            "event=schedule",
            query_lines[0],
            "memory-retention-watchdog.yml 的 run 查詢沒有過濾 event=schedule。"
            "少了它，一次 dry_run=true 的手動觸發（它成功但什麼都沒刪）會把新鮮度"
            "時鐘歸零，蓋掉數週沒有真正清除的事實",
        )
        self.assertNotIn(
            "engine: copilot",
            self.watchdog_text,
            "watchdog 必須是純 Actions（NFR7.14）：一個二元的時間戳比較不該走 LLM 路徑",
        )
        self.assertIn(
            "issues: write",
            self.watchdog_text,
            "watchdog 需要 issues: write 才能開告警 issue（OPEN-ID9-2 的具名權限增量）",
        )

    # -- 9 --------------------------------------------------------------

    def test_sentinel_role_is_not_canonical(self) -> None:
        """第三道鎖：哨符列的 `role` 不得是 canonical role。

        `rbac.py` 的 `is_canonical_role()` 是權限判定的入口，`CANONICAL_ROLES` 是
        **角色清單的正本**（`team.md`）。seed 腳本與 `verify_memory_schema.sql` 的
        `S13` 都以**資料庫內的權限矩陣**判這一項（它們不能 import `services.rbac`：
        那條 import 鏈經過 `services.auth`，而後者在 `APP_ENV` 非 local／test／ci
        且無 `JWT_SECRET` 的 shell 上會在模組載入時拋 `RuntimeError`，而一支 seed
        腳本不該因為一個與它無關的理由在 staging 上崩掉）。

        **這裡是那條程式層斷言唯一安全的落點**：測試環境的 import 沒有那個問題。
        """
        from services.rbac import CANONICAL_ROLES, is_canonical_role

        self.assertNotIn(
            self.seed_role,
            CANONICAL_ROLES,
            f"哨符列的 role {self.seed_role!r} 在 CANONICAL_ROLES 內——"
            "它會通過權限判定",
        )
        self.assertFalse(
            is_canonical_role(self.seed_role),
            f"is_canonical_role({self.seed_role!r}) 回 True。"
            "注意 ROLE_ALIASES 會先做一次 normalize，故別名也不能用",
        )
        self.assertEqual(
            self.seed_is_active.upper(),
            "FALSE",
            "第四道鎖：哨符列的 is_active 必須是 FALSE",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
