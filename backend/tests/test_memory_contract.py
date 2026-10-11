"""`U8 memory-service` 的靜態契約斷言（`C1`–`C7`，**零 DB、零網路**）。

本檔對應 `unit-test-instructions.md §4.1`。全部斷言都只讀**版控檔案的內容**，
故它們在任何環境、任何順序下都成立，且不需要資料庫。

## 為什麼以 `ast` 解析而不是字串比對

`services/membership_selection.py` 的檔頭逐字記下了這個陷阱：

> 對本檔跑裸 `grep` 會各命中一次——就是上面這段散文自己。
> **量測純度要看 import 集合與程式行，不是整個檔案的字串命中。**

本單元的三個模組都在 docstring 裡解釋「為什麼不拋 `HTTPException`」，
所以 `"HTTPException" in source` 對 `memory_facade.py` 與 `memory_ranking.py`
**必然成立**——一個照 `code-generation-plan.md` Step 6.1 ①② 字面實作的
字串比對測試會**永遠紅燈**，而把 docstring 刪掉來讓它變綠會損失本單元
最需要被讀到的那幾段理由。

故 `C1`／`C2` 以 import 集合 ＋ **程式行**（AST 節點，不含 docstring 與註解）
斷言，`C3` 以**非 docstring 的字串字面值**斷言。這是對計畫字面的刻意偏離，
理由是 repo 既有的明文教訓。

## `C6`／`C7` 是本檔對計畫的兩項**新增**

- `C6`（`SEARCH_SQL` 的結構 ＋ 與 `S15` 的一致性）：計畫的突變 3 是
  「`search` 改為先查 `LIMIT n` 再於應用層過濾」，期望 `S15` ③ 紅燈。
  但 `S15` 是**純 psql**——它執行的是 `.sql` 檔裡的查詢，**看不到 Python**，
  故改 Python 不會讓它變色。`C6` 是讓那個突變真的有東西變紅的那一條。
- `C7`（`NFR7.33` 的 logger 命名）：二元可判、零成本。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import re
import unittest
from pathlib import Path

from models import MemoryAuditEvent, MemoryRecord
from services import memory_service
from services.memory_types import (
    SCOPE_WIDENING_ROLES,
    SCOPE_WIDTH,
    VISIBILITY_SCOPES,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SCHEMA_PATH = REPO_ROOT / "schema_rbac.sql"
VERIFY_SQL_PATH = BACKEND_DIR / "scripts" / "verify_memory_schema.sql"

RANKING_PATH = BACKEND_DIR / "services" / "memory_ranking.py"
FACADE_PATH = BACKEND_DIR / "services" / "memory_facade.py"
ROUTER_PATH = BACKEND_DIR / "services" / "memory_router.py"
SERVICE_PATH = BACKEND_DIR / "services" / "memory_service.py"

NEW_MODULES = (RANKING_PATH, FACADE_PATH, ROUTER_PATH, SERVICE_PATH)

#: `embedding` 刻意不在 ORM 內（`NFR8.20`：宣告 `vector(1024)` 需要 `pgvector`
#: 套件，而 `requirements.txt` 的 diff 必須為空）。見 `models.py` 的區塊註解。
DELIBERATE_COLUMN_OMISSIONS = {"memory.memory_records": {"embedding"}}

#: HNSW 索引建在 `embedding` 上，故與該欄同一個根因、同樣無法鏡像。
DELIBERATE_INDEX_OMISSIONS = {
    "memory.memory_records": {"ix_memory_records_embedding_hnsw"}
}

#: `C5` 的識別字黑名單：這些名字在本單元幾乎一定是「整列」或「整個事件」。
MODEL_ISH_NAMES = {
    "record",
    "records",
    "memory",
    "memories",
    "event",
    "events",
    "row",
    "rows",
    "payload",
    "content",
    "embedding",
    "vector",
    "vectors",
}


# ---------------------------------------------------------------------------
# AST 工具
# ---------------------------------------------------------------------------


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_roots(tree: ast.Module) -> set[str]:
    """模組 import 的**頂層套件名**集合。"""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # 相對 import
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def imported_names(tree: ast.Module) -> set[str]:
    """`from x import Y` 與 `import x as Y` 帶進來的**名字**集合。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def code_identifiers(tree: ast.Module) -> set[str]:
    """**程式行**用到的識別字（`Name` 與 `Attribute` 的屬性名）。

    刻意不含 docstring 與註解——那是本檔整個 AST 取徑的理由。
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
    return found


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """全部 docstring 的 `Constant` 節點 id（用來從字面值集合裡排除）。"""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def non_docstring_string_literals(tree: ast.Module) -> list[str]:
    """非 docstring 的字串字面值。`C3` 的量測對象。"""
    skip = _docstring_nodes(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
        ):
            out.append(node.value)
    return out


def logger_calls(tree: ast.Module) -> list[ast.Call]:
    """`logger.<level>(...)` 形式的呼叫。"""
    calls = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "logger"
        ):
            calls.append(node)
    return calls


# ---------------------------------------------------------------------------
# DDL 解析（沿用 `tests/test_membership_data.py` 的 `T25` 形狀）
# ---------------------------------------------------------------------------


def ddl_block(table: str) -> str:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS " + re.escape(table) + r"\s*\((.*?)\n\);", sql, re.S
    )
    assert match is not None, f"{table} 的 DDL 找不到"
    return match.group(1)


def ddl_columns(table: str) -> set[str]:
    """約束宣告與其**續行**都要略過（沿用 `T25` 既有的解析形狀）。"""
    columns = set()
    for line in ddl_block(table).splitlines():
        line = line.strip()
        if not line or line.startswith(
            ("CONSTRAINT", "CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "--", ")")
        ):
            continue
        columns.add(line.split()[0].strip(","))
    return columns


def ddl_named_constraints(table: str) -> set[str]:
    return set(re.findall(r"CONSTRAINT\s+(\w+)", ddl_block(table)))


def ddl_indexes(table: str) -> set[str]:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    return set(
        re.findall(
            r"CREATE INDEX IF NOT EXISTS\s+(\w+)\s*\n?\s*ON\s+" + re.escape(table) + r"\b",
            sql,
        )
    )


def normalise_sql(sql: str) -> str:
    """壓掉空白差異，保留 token 順序。"""
    return re.sub(r"\s+", " ", sql).strip().lower()


# ---------------------------------------------------------------------------
# C1／C2：四層的禁令（`logical-components.md §1.1`）
# ---------------------------------------------------------------------------


class LayerProhibitionTest(unittest.TestCase):
    """`C1`／`C2`：純函式層與 facade 層的禁令是**結構前提**，不是風格偏好。"""

    def test_C1_ranking_module_is_pure(self):
        """`C1`：`memory_ranking` 不讀 DB、不拋 `HTTPException`。

        違反它會壞掉的東西逐字寫在 `logical-components.md §1.1`：
        「**property-based 測試就寫不下去**」——`hypothesis` 無法對一個需要
        資料庫 session 的函式生成輸入。這是 `NFR3.24` 可驗的結構前提。

        斷言 import 集合**恰為兩項**（而不是「不含某些項」）：前者在
        「多了一個 import」時會紅，後者只在「多了黑名單上那幾個」時會紅。
        """
        tree = parse(RANKING_PATH)
        self.assertEqual(
            imported_roots(tree),
            {"__future__", "typing"},
            "memory_ranking 的 import 集合必須恰為 {__future__, typing}："
            "多一個 import 就是純度的缺口，而純度是 NFR3.24 的 PBT 落點的前提",
        )
        identifiers = code_identifiers(tree)
        for forbidden in ("Session", "HTTPException", "db", "engine", "execute"):
            self.assertNotIn(
                forbidden,
                identifiers,
                f"memory_ranking 的程式行不得出現 {forbidden}",
            )

    def test_C2_facade_does_not_raise_http_exceptions(self):
        """`C2`：`memory_facade` 不 import、不使用 `HTTPException`。

        `MemoryFacade` **同時**被 HTTP（`U15`）與同進程（`U11`，經 `K-10`）
        消費。拋 `HTTPException` 會讓 `U11` 收到一個它無法處理、也無處可回
        的型別——它不在 FastAPI 的 dependency 鏈上。

        `memory_service` 一併斷言：它是交易邊界的持有者，HTTP 關注點混進來
        會讓交易範圍難以推理。
        """
        for path in (FACADE_PATH, SERVICE_PATH):
            tree = parse(path)
            with self.subTest(module=path.name):
                self.assertNotIn(
                    "HTTPException",
                    imported_names(tree),
                    f"{path.name} 不得 import HTTPException",
                )
                self.assertNotIn(
                    "HTTPException",
                    code_identifiers(tree),
                    f"{path.name} 的程式行不得出現 HTTPException",
                )
                self.assertNotIn(
                    "fastapi",
                    imported_roots(tree),
                    f"{path.name} 不得 import fastapi：HTTP 關注點只屬 router 層",
                )

    def test_C3_router_contains_no_authorization(self):
        """`C3`：`memory_router` 不含任何角色名稱字面值。

        授權判定在 facade（`K-08` 的 `sole_entry`）。router 裡出現角色名稱
        就表示授權有了第二份實作，而兩份實作遲早分歧。

        量測的是**非 docstring 的字串字面值**：router 的檔頭要解釋
        「為什麼這一層沒有授權」，而那段散文本身不是違規。
        """
        tree = parse(ROUTER_PATH)
        literals = non_docstring_string_literals(tree)
        for role in SCOPE_WIDENING_ROLES:
            offenders = [lit for lit in literals if role in lit]
            self.assertEqual(
                offenders,
                [],
                f"memory_router 的程式行不得出現角色名稱 {role!r}："
                f"授權判定只屬 MemoryFacade（K-08 的 sole_entry）。命中：{offenders}",
            )
        self.assertNotIn(
            "memory_service",
            imported_names(parse(ROUTER_PATH)),
            "memory_router 不得 import memory_service——那會繞過 facade，"
            "使 K-08 的 sole_entry 保證失效（形狀沿用 membership_router）",
        )


# ---------------------------------------------------------------------------
# C4：ORM ↔ SQL 一致性
# ---------------------------------------------------------------------------


class OrmSchemaAlignmentTest(unittest.TestCase):
    """`C4`：兩份物化的一致性。

    納入 `Base` 之後，`database.py:90` 的 `Base.metadata.create_all()` 就成為
    **第二條建表路徑**（`models.py` 的 `U19` 區塊逐字記下了這個洞，而 `U7`
    已經踩過）。於是「少寫一條 CHECK」等於在 SQLite 測試環境裡悄悄移除它
    ——實測確認那三條 CHECK 在 SQLite 上**真的會擋**，故漏寫的代價是實際的。
    """

    TABLES = (
        (MemoryRecord, "memory.memory_records"),
        (MemoryAuditEvent, "memory.memory_audit_events"),
    )

    def test_C4_orm_mirrors_sql_columns(self):
        """欄位集合：**ORM ∪ 刻意省略 ＝ DDL**。

        欄位清單**以 regex 從 `schema_rbac.sql` 解析**，不在本檔重新手寫
        ——`unit-test-instructions.md §4.1` 逐字要求，理由是手寫會讓
        「被檢查的東西」與「檢查的依據」變成同一個人的記憶
        （`project.md` 已記過這個形）。
        """
        for model, table in self.TABLES:
            with self.subTest(table=table):
                orm = {c.name for c in model.__table__.columns}
                omitted = DELIBERATE_COLUMN_OMISSIONS.get(table, set())
                ddl = ddl_columns(table)
                self.assertEqual(
                    orm | omitted,
                    ddl,
                    f"{table}：ORM ∪ {omitted or '{}'} 應等於 DDL "
                    f"(ORM only={orm - ddl}, DDL only={ddl - orm - omitted})",
                )
                # 省略必須**恰好**是宣告的那些，不能多：少宣告一個會讓上面的
                # 等式在「ORM 漏欄位」時仍然成立。
                self.assertEqual(
                    orm & omitted,
                    set(),
                    f"{table}：{omitted} 宣告為刻意省略，卻出現在 ORM 內",
                )

    def test_C4_orm_mirrors_sql_named_constraints_and_indexes(self):
        """具名約束**完全相等**；索引為 **ORM ∪ 刻意省略 ＝ DDL**。

        `code-generation-plan.md` Step 2.4 寫「不加 `CheckConstraint`」，而本測試
        斷言相反。理由不是偏好：`models.py` 的 `U19` 區塊逐字要求「約束必須與
        DDL 逐條對齊，不只是欄位」，而 `U18` 真正刻意不加 CHECK 的
        （`previous_role`／`new_role`）在 **DDL 側也沒有**。判準是「DDL 有沒有」。
        """
        for model, table in self.TABLES:
            with self.subTest(table=table):
                orm_constraints = {
                    c.name for c in model.__table__.constraints if c.name is not None
                }
                self.assertEqual(
                    orm_constraints,
                    ddl_named_constraints(table),
                    f"{table}：具名約束集合與 DDL 不一致。少寫一條等於在 SQLite "
                    f"測試環境裡悄悄移除它",
                )
                orm_indexes = {i.name for i in model.__table__.indexes}
                omitted = DELIBERATE_INDEX_OMISSIONS.get(table, set())
                self.assertEqual(
                    orm_indexes | omitted,
                    ddl_indexes(table),
                    f"{table}：索引名稱集合 ∪ {omitted or '{}'} 與 DDL 不一致",
                )

    def test_C4_closed_sets_agree_with_the_width_order(self):
        """`VISIBILITY_SCOPES` 與 `SCOPE_WIDTH` 的鍵集合必須相同。

        漏掉一個值會讓 `widen_scope` 在它上面取不到寬度。本測試讓那個缺口
        在 import 時就被發現，而不是在某個 scope 上才 `KeyError`。
        """
        self.assertEqual(set(VISIBILITY_SCOPES), set(SCOPE_WIDTH.keys()))
        self.assertEqual(
            len(set(SCOPE_WIDTH.values())),
            len(VISIBILITY_SCOPES),
            "每個可見範圍必須有相異的寬度，否則 BR5.2 的方向性失去依據",
        )


# ---------------------------------------------------------------------------
# C5／C7：日誌衛生與命名（`NFR6.21`／`NFR7.31`／`NFR7.33`）
# ---------------------------------------------------------------------------


class LoggingHygieneTest(unittest.TestCase):
    """`C5`／`C7`：公開可讀的日誌裡不得有個人對話歷程。

    本 repo 為 public 且 Actions log 公開可讀（`project.md` 逐字「一次意外
    echo 即等同公開發布」），而本單元處理的是個人對話歷程。

    **這是本單元最容易出的錯**：`logger.warning(f"denied: {memory}")` 在功能上
    完全正常、測試也會綠，而它把整列（含 `content`）寫進公開可讀的日誌。
    故本測試是**靜態**的——執行期的字串比對（`test_memory_authz` 第 12 條）
    只在被觸發的路徑上有效。
    """

    def test_C5_logging_never_passes_whole_model(self):
        """日誌呼叫不得有 f-string，也不得有「整個物件」形狀的引數。

        **禁 f-string 是這一條的主力**：`%s` 的惰性格式化是本 repo 既有慣例
        （`membership_service.log_denied` 的形狀），而 f-string 是把整個物件
        插進日誌的最短路徑。兩道規則合起來使「順手把整列傳進去」沒有寫法。
        """
        for path in NEW_MODULES:
            tree = parse(path)
            for call in logger_calls(tree):
                with self.subTest(module=path.name, line=call.lineno):
                    for arg in call.args:
                        self.assertNotIsInstance(
                            arg,
                            ast.JoinedStr,
                            f"{path.name}:{call.lineno} 的日誌引數是 f-string。"
                            "改用 %s 惰性格式化——f-string 是把整列（含 content）"
                            "寫進公開可讀日誌的最短路徑",
                        )
                        if isinstance(arg, ast.Name):
                            self.assertNotIn(
                                arg.id,
                                MODEL_ISH_NAMES,
                                f"{path.name}:{call.lineno} 把 {arg.id!r} 整個傳給"
                                "日誌。只允許 principal 識別字、memoryId、kind、"
                                "reason 與筆數（NFR6.21 的欄位白名單）",
                            )
                        if isinstance(arg, ast.Attribute):
                            self.assertNotIn(
                                arg.attr,
                                {"content", "embedding"},
                                f"{path.name}:{call.lineno} 記錄了 .{arg.attr}"
                                "——NFR7.31 明文禁止",
                            )

    def test_C7_loggers_follow_the_cloud360_naming(self):
        """`NFR7.33`：新增模組的 logger 一律 `cloud360.<module>`，不用 `__name__`。

        `team.md ## Code Style` 逐字「新模組一律 `"cloud360.<module>"` 形式」。
        既有 repo 有 5 支模組用 `__name__`（已知不一致），新模組不沿用那一邊。

        **`memory_ranking` 刻意有 0 個 logger，而這不是漏寫**：一個 module 層
        的 logger 是模組級物件，而記日誌是副作用——兩者都與
        `logical-components.md §1.1` 對該層的要求（純函式、無 I/O）相牴觸。
        本測試因此對它斷言**恰為 0**，對其餘三層斷言**恰為 1**。
        第一版把四個模組一律斷言為 1，被這一條自己抓到。
        """
        pattern = re.compile(r"^cloud360\.[a-z_]+$")
        expected_counts = {
            RANKING_PATH: 0,  # 純函式層：不記日誌
            FACADE_PATH: 1,
            ROUTER_PATH: 1,
            SERVICE_PATH: 1,
        }
        for path in NEW_MODULES:
            tree = parse(path)
            calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "getLogger"
            ]
            with self.subTest(module=path.name):
                self.assertEqual(
                    len(calls),
                    expected_counts[path],
                    f"{path.name} 的 getLogger 呼叫數應為 "
                    f"{expected_counts[path]}，實際 {len(calls)}",
                )
                for call in calls:
                    arg = call.args[0]
                    self.assertIsInstance(
                        arg, ast.Constant, f"{path.name} 的 logger 名必須是字面值"
                    )
                    self.assertRegex(arg.value, pattern)
        # 純函式層連 `logging` 都不該 import——由 `C1` 的 import 集合斷言
        # （恰為 `{__future__, typing}`）涵蓋，此處只點名理由。
        self.assertNotIn("logging", imported_roots(parse(RANKING_PATH)))


# ---------------------------------------------------------------------------
# C6：檢索 SQL 的結構，以及它與 `S15` 的一致性
# ---------------------------------------------------------------------------


class SearchSqlContractTest(unittest.TestCase):
    """`C6`（**本檔對計畫的新增**）：單一 SQL 的結構斷言。

    ## 為什麼需要它

    `code-generation-plan.md` Step 9 的突變 3 是「`search` 改為先查 `LIMIT n`
    再於應用層過濾」，期望 **`S15` ③** 紅燈。

    但 `S15` 是**純 psql**：它執行 `verify_memory_schema.sql` 裡的查詢，
    **完全看不到 Python**。把 `memory_service.search_records` 改成先查再過濾
    不會讓 `S15` 的任何一條變色——三條都會留在綠燈。

    故 `S15` 證明的是「**這樣寫的 SQL** 在真實 PostgreSQL 上行為正確」，
    而**不是**「服務真的這樣查」。後者需要 Python 側的斷言，就是本測試。

    ## 兩份物化與 `team.md` 的「單一真實來源」

    同一個查詢在 `memory_service.SEARCH_SQL` 與 `verify_memory_schema.sql`
    的 `S15` 各有一份。`team.md ## Code Style` 逐字要求「若確實無法避免
    （如跨語言邊界），**新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試**」
    ——psql 無法 import Python，這正是「跨語言邊界」。本測試是那個鎖。
    """

    S15_BEGIN = "-- >>> S15_SEARCH_QUERY_BEGIN"
    S15_END = "-- <<< S15_SEARCH_QUERY_END"

    def _s15_query(self) -> str:
        sql = VERIFY_SQL_PATH.read_text(encoding="utf-8")
        self.assertIn(
            self.S15_BEGIN,
            sql,
            "verify_memory_schema.sql 必須以哨兵註解標出 S15 的檢索查詢，"
            "否則本鎖無法定位它",
        )
        body = sql.split(self.S15_BEGIN, 1)[1].split(self.S15_END, 1)[0]
        return body

    def test_C6_search_sql_is_one_statement_with_both_filters(self):
        """`SEARCH_SQL`：一條敘述、兩道過濾、`ORDER BY` 距離、`LIMIT` 在最後。

        **子句順序是這一條的重點**：`LIMIT` 必須在兩道過濾**之後**。
        先取 `LIMIT n` 再於應用層過濾會讓回傳筆數錯（過濾後可能剩不足 n），
        且不可見的列會先進入進程（洩漏面擴大）。
        """
        sql = normalise_sql(memory_service.SEARCH_SQL)

        self.assertEqual(
            sql.count("select"), 1, "檢索必須是**一條** SELECT，不是先查再查"
        )
        self.assertNotIn(";", sql, "不得是多條敘述")

        where_at = sql.find(" where ")
        order_at = sql.find(" order by ")
        limit_at = sql.find(" limit ")
        self.assertGreater(where_at, 0, "缺 WHERE")
        self.assertGreater(order_at, where_at, "ORDER BY 必須在 WHERE 之後")
        self.assertGreater(limit_at, order_at, "LIMIT 必須在 ORDER BY 之後")

        where_clause = sql[where_at:order_at]
        # `BR2.2`：可見範圍過濾。
        self.assertIn("owner_user_id = :principal_user_id", where_clause)
        self.assertIn("visibility_scope = :platform_scope", where_clause)
        # `BR3.2`：向量空間分群。本單元**唯一完全靜默**的失敗模式。
        self.assertIn(
            "embedding_model = :embedding_model",
            where_clause,
            "少了 embeddingModel 過濾，型別／維度／索引／查詢全部仍然合法，"
            "但結果是跨向量空間的垃圾**且不報錯**（BR3.2）",
        )
        # `BR3.3`：無向量的列不被向量檢索看到，而這不是錯誤。
        self.assertIn("embedding is not null", where_clause)

    def test_C6_search_sql_operator_matches_the_index_opclass(self):
        """`ORDER BY` 的距離運算子必須與 HNSW 索引的 opclass 相符。

        不相符時索引被**靜默忽略**：查詢仍然正確、仍回精確最近鄰，只是退化為
        循序掃描，而在空表上延遲看起來一樣好。已實測（見 `code-summary.md`）：
        `<=>` 對 `vector_cosine_ops` 得 `Index Scan`，`<->` 對同一個索引得
        `Seq Scan`，即使 `enable_seqscan = off`。

        這一對的另一半由 `S14` 在真實 PostgreSQL 上斷言；本測試鎖的是
        **Python 側的運算子**與 **DDL 側的 opclass** 是同一對。
        """
        sql = normalise_sql(memory_service.SEARCH_SQL)
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        operator_to_opclass = {"<=>": "vector_cosine_ops", "<->": "vector_l2_ops"}
        used = [op for op in operator_to_opclass if op in sql]
        self.assertEqual(
            len(used), 1, f"SEARCH_SQL 應恰用一個距離運算子，實際 {used}"
        )
        expected_opclass = operator_to_opclass[used[0]]

        match = re.search(
            r"CREATE INDEX IF NOT EXISTS\s+(\w+)\s*\n?\s*ON\s+memory\.memory_records"
            r"\s+USING\s+hnsw\s*\(\s*embedding\s+(\w+)\s*\)",
            schema,
        )
        self.assertIsNotNone(
            match, "schema_rbac.sql 的 I) 區塊找不到 embedding 的 HNSW 索引"
        )
        self.assertEqual(
            match.group(2),
            expected_opclass,
            f"SEARCH_SQL 用 {used[0]}，故索引的 opclass 必須是 "
            f"{expected_opclass}，實際 {match.group(2)}",
        )

    def test_C6_s15_query_agrees_with_the_service_sql(self):
        """`S15` 的查詢與 `SEARCH_SQL` 在三個承載語意的子句上一致。

        斷言的是**語意子句**而非位元組相等：`S15` 必須把 `:param` 換成字面值
        才能在 psql 的 `DO` 區塊裡跑，故兩份文字必然不同。一致性的意義在於
        「兩道過濾 ＋ `ORDER BY` 距離 ＋ `LIMIT` 在最後」這個形狀，
        而那正是 `S15` ③ 要驗的東西。
        """
        s15 = normalise_sql(self._s15_query())
        service = normalise_sql(memory_service.SEARCH_SQL)

        for fragment, label in (
            ("from memory.memory_records", "來源表"),
            ("visibility_scope", "可見範圍過濾（BR2.2）"),
            ("embedding_model", "向量空間分群（BR3.2）"),
            ("embedding is not null", "無向量的列（BR3.3）"),
            ("order by", "距離排序"),
            ("limit", "LIMIT"),
        ):
            with self.subTest(fragment=label):
                self.assertIn(fragment, s15, f"S15 的查詢缺 {label}")
                self.assertIn(fragment, service, f"SEARCH_SQL 缺 {label}")

        # 兩側用同一個距離運算子——否則 `S15` 驗的是另一個查詢。
        for operator in ("<=>", "<->"):
            self.assertEqual(
                operator in s15,
                operator in service,
                f"S15 與 SEARCH_SQL 的距離運算子不一致（{operator}）",
            )

        # 子句順序：`LIMIT` 在 `ORDER BY` 之後，兩側都要成立。
        self.assertGreater(s15.rfind(" limit "), s15.find(" order by "))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
