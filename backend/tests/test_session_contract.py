"""`U10 session-store` 的**靜態**契約斷言（**零執行、零 DB、零 Redis**）。

本檔對應 `unit-test-instructions.md §三` 的第二列。全部斷言都只讀**版控檔案的
內容**，故它們在任何環境、任何順序下都成立。

## 為什麼這個檔案必須獨立存在

`NFR4.46` 的三項禁令（**不判權／不取身分／不對外**）是**形狀**而非行為。
用執行期測試驗它，等於去證明某件事不會發生——而那在測試裡永遠只能驗到你想到
的那幾條路徑。讀原始碼比對是二元可判的。

同理 `NFR4.63` 的日誌白名單：執行期只能驗「我記得去呼叫的那幾處」，而真正要
擋的是**下一個人新增的那一處**。擋得住它的是建構函式的**簽章**，而本檔斷言
那個簽章。

## 為什麼以 `ast` 解析而不是字串比對

`services/memory_selection` 家族已有明文前例（`test_memory_contract.py` 檔頭）：
本單元的三個模組都在 docstring 裡解釋「為什麼不判權」「為什麼不取身分」，
所以 `"require_story_action" in source` 對它們**必然成立**——一個字串比對的
測試會永遠紅燈，而把 docstring 刪掉來讓它變綠會損失本單元最需要被讀到的理由。

故本檔以 **import 集合 ＋ 程式行的識別字**（AST 節點，不含 docstring 與註解）
斷言。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import unittest
from pathlib import Path

from services.redis_gateway import LOG_FIELD_NAMES

BACKEND_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = BACKEND_DIR / "services"
SCRIPTS_DIR = SERVICES_DIR / "session_scripts"

TYPES_PATH = SERVICES_DIR / "session_types.py"
ERRORS_PATH = SERVICES_DIR / "session_errors.py"
GATEWAY_PATH = SERVICES_DIR / "redis_gateway.py"
STORE_PATH = SERVICES_DIR / "session_store.py"
MAIN_PATH = BACKEND_DIR / "main.py"

APPEND_SCRIPT = SCRIPTS_DIR / "append_message.lua"
SWITCH_SCRIPT = SCRIPTS_DIR / "switch_to_isolated.lua"

#: 本單元的四個新模組。
UNIT_MODULES = (TYPES_PATH, ERRORS_PATH, GATEWAY_PATH, STORE_PATH)

#: `BR5.2`／`NFR4.46`：request／websocket 型別一律不得出現在 import 集合。
#: 自取身分會讓同進程呼叫者得以用別人的身分寫入。
FORBIDDEN_IMPORT_ROOTS = {"fastapi", "starlette", "websockets"}

#: `BR5.1`：授權委派給 `K-07`，本單元不讀權限矩陣。
FORBIDDEN_AUTHZ_IDENTIFIERS = {
    "require_story_action",
    "user_can",
    "ensure_role_permissions_seeded",
    "get_current_user",
}

#: `BR5.3`：不註冊任何 router。
FORBIDDEN_ROUTER_IDENTIFIERS = {"APIRouter", "include_router", "add_api_route"}


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_roots(tree: ast.Module) -> set:
    """模組 import 的**頂層套件名**集合（含函式內的延遲匯入）。"""
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def module_level_imported_roots(tree: ast.Module) -> set:
    """**只看 `tree.body`** 的 import——函式內的延遲匯入不算。

    這個區別是載體：`redis_gateway` 刻意把 redis-py 的匯入放在函式內，讓本模組
    在測試中（替身注入）與未安裝該套件的開發機上都可被匯入。
    """
    roots = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    return roots


def code_identifiers(tree: ast.Module) -> set:
    """**程式行**用到的識別字。刻意不含 docstring 與註解。"""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
    return found


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"找不到函式 {name}")


class NoAuthorizationOfItsOwnTest(unittest.TestCase):
    """`BR5.1`／`NFR4.46`：`require_story_action` 零命中。"""

    def test_no_module_touches_the_permission_matrix(self):
        """自建第二套判定會與 `K-07` 分歧，且兩層 facade **不得互相假設對方
        已檢查**（`K-09.authorization_responsibility` 逐字）。"""
        for path in UNIT_MODULES:
            with self.subTest(module=path.name):
                hits = code_identifiers(parse(path)) & FORBIDDEN_AUTHZ_IDENTIFIERS
                self.assertEqual(hits, set())

    def test_store_delegates_work_target_authorization_to_the_facade(self):
        """反向斷言：`BR4.6` 要求**一定**要委派。

        前一條（零命中）單獨成立時，「完全不做授權」也會通過——兩條合起來才
        表達「不自己判，但一定要委派」。
        """
        self.assertIn("resolve_work_target", code_identifiers(parse(STORE_PATH)))


class NoIdentityFromRequestTest(unittest.TestCase):
    """`BR5.2`／`NFR4.46`：不 import request／websocket 型別。"""

    def test_no_module_imports_a_web_framework_type(self):
        for path in UNIT_MODULES:
            with self.subTest(module=path.name):
                hits = imported_roots(parse(path)) & FORBIDDEN_IMPORT_ROOTS
                self.assertEqual(hits, set())

    def test_principal_is_a_parameter_of_set_work_target(self):
        """`BR5.2` 的反向面：身分**必須**是參數。

        只斷言「沒有 import request」時，一個從模組層全域變數取身分的實作也會
        通過。
        """
        func = find_function(parse(STORE_PATH), "set_work_target")
        arg_names = [a.arg for a in func.args.args]
        self.assertIn("principal", arg_names)


class NoExposedEndpointTest(unittest.TestCase):
    """`BR5.3`／`NFR4.46`：無 router 註冊。"""

    def test_no_module_creates_or_registers_a_router(self):
        for path in UNIT_MODULES:
            with self.subTest(module=path.name):
                hits = code_identifiers(parse(path)) & FORBIDDEN_ROUTER_IDENTIFIERS
                self.assertEqual(hits, set())

    def test_main_does_not_mount_a_session_store_router(self):
        """新增對外面會繞過 `U13` 的握手與身分驗證。對外一律經 `U13` 的既有端點。

        這一條同時是 `openapi.json` diff 為空的**來源**：沒有端點，就沒有
        schema 可漂移。
        """
        source = MAIN_PATH.read_text(encoding="utf-8")
        for forbidden in ("session_store", "session_router", "redis_gateway"):
            self.assertNotIn(f"import {forbidden} ", source)
        mounted = set()
        for node in ast.walk(parse(MAIN_PATH)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "include_router"
                and node.args
                and isinstance(node.args[0], ast.Name)
            ):
                mounted.add(node.args[0].id)
        # 既有的八個 router 都在，而本單元**不加第九個**。
        self.assertIn("memory_router", mounted)
        for forbidden in ("session_router", "session_store_router", "brain_session_router"):
            self.assertNotIn(forbidden, mounted)


class LogWhitelistIsASignatureTest(unittest.TestCase):
    """`NFR4.63`／`BR3.6`：白名單**就是**建構函式的簽章。

    `observability-design.md §一` 逐字：「白名單若只存在於文件，下一個人加一個
    欄位時不會有任何東西擋他。」突變 `M6`（改為接受 `**kwargs`）正是這一組抓的。
    """

    def test_log_field_builder_accepts_no_arbitrary_kwargs(self):
        func = find_function(parse(GATEWAY_PATH), "session_log_fields")
        self.assertIsNone(func.args.kwarg, "session_log_fields 不得接受 **kwargs")
        self.assertIsNone(func.args.vararg, "session_log_fields 不得接受 *args")

    def test_log_field_builder_takes_exactly_the_whitelist_as_keyword_only(self):
        func = find_function(parse(GATEWAY_PATH), "session_log_fields")
        self.assertEqual(func.args.args, [], "全部欄位必須是 keyword-only")
        self.assertEqual(
            tuple(a.arg for a in func.args.kwonlyargs), tuple(LOG_FIELD_NAMES)
        )

    def test_the_whitelist_is_exactly_the_six_designed_fields_plus_attempt(self):
        """`observability-design.md §一`／`§二` 的欄位集合，逐字。"""
        self.assertEqual(
            set(LOG_FIELD_NAMES),
            {
                "sessionKey",
                "segmentId",
                "method",
                "reason",
                "elapsedMs",
                "droppedCount",
                "attempt",
            },
        )

    def test_no_module_formats_a_session_object_into_a_log_call(self):
        """本單元最容易出的錯是 `logger.warning(f"...{session}")`——它在功能上
        完全正常、測試也會綠，而它把整段對話寫進公開可讀的日誌。

        故本條斷言：`logger.<level>(...)` 的直接呼叫只出現在
        `log_session_event` 之外的**設定／資訊**用途，且其引數裡不得出現
        `session`／`segment`／`text`／`messages` 這些識別字。
        """
        suspicious = {"text", "messages", "segment", "session"}
        for path in (GATEWAY_PATH, STORE_PATH):
            tree = parse(path)
            # `log_session_event` 自己的 `logger.log(...)` 是**唯一**被授權的
            # 輸出點，而它收到的 `fields` 已經過白名單守衛。把它排除，否則這條
            # 斷言會把唯一正確的實作判為違規。
            sanctioned = {
                n.lineno
                for fn in ast.walk(tree)
                if isinstance(fn, ast.FunctionDef) and fn.name == "log_session_event"
                for n in ast.walk(fn)
                if hasattr(n, "lineno")
            }
            for node in ast.walk(tree):
                if getattr(node, "lineno", None) in sanctioned:
                    continue
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "logger"
                ):
                    continue
                names = set()
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    names |= {
                        child.id
                        for child in ast.walk(arg)
                        if isinstance(child, ast.Name)
                    }
                with self.subTest(module=path.name, line=node.lineno):
                    self.assertEqual(names & suspicious, set())


class LuaIsTheOnlyTrimCarrierTest(unittest.TestCase):
    """`performance-design.md` 的**唯一載體**原則。

    逐字：「`BR3.4` 的修剪語意只能有一個載體。Python 端**不得**另外實作一次
    修剪——兩份實作遲早分歧，而分歧的徵兆是『筆數偶爾是 201』這種沒人會注意
    的東西。」
    """

    def test_production_modules_never_call_the_reference_implementation(self):
        for path in (GATEWAY_PATH, STORE_PATH):
            with self.subTest(module=path.name):
                self.assertNotIn("trim_history", code_identifiers(parse(path)))

    def test_the_lua_script_contains_the_trim_loop(self):
        """反向斷言：載體**必須**真的在 Lua 裡。

        前一條單獨成立時，「兩邊都不修剪」也會通過。
        """
        source = APPEND_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("table.remove(arr, 1)", source)
        # 修剪條件是「筆數上限**或**位元組上限」任一超過就丟（兩者取較嚴者，
        # `merge-blockers.md` 第 18 項）。兩個條件都必須在迴圈條件裡——只剩筆數
        # 那一半時，最壞情況回到每 session 約 7 MB。
        self.assertIn(
            "while #arr > 1 and (#arr > cap or total > max_bytes) do", source
        )
        # 位元組以 `string.len`（位元組數）量 cjson 的輸出，而不是 `#`（Lua 的 `#`
        # 對字串也是位元組數，但用具名函式讓「量的是位元組」在原始碼上可讀）。
        self.assertIn("string.len(cjson.encode(arr[i]))", source)

    def test_scripts_are_static_files_with_a_dispatch_marker(self):
        """`security-design.md §二`：腳本為**靜態常數**，使用者資料一律經
        `ARGV`，**絕不**以字串拼接組成腳本（與既有的「SQL 一律參數化」同一條
        紀律）。
        """
        for script in (APPEND_SCRIPT, SWITCH_SCRIPT):
            with self.subTest(script=script.name):
                source = script.read_text(encoding="utf-8")
                self.assertIn(f"-- script: {script.stem}", source)
                # 腳本不得記錄 `ARGV` 的內容。
                #
                # **只比對非註解行**：兩支腳本的檔頭都逐字寫著「本腳本不呼叫
                # `redis.log`」，所以對整個檔案跑字串比對會各命中一次——就是
                # 那段說明自己。這是 `test_memory_contract.py` 檔頭記過的同一
                # 個陷阱（「量測純度要看程式行，不是整個檔案的字串命中」），
                # 而本條第一次寫出來時就踩了它。
                code = "\n".join(
                    line
                    for line in source.splitlines()
                    if not line.lstrip().startswith("--")
                )
                self.assertNotIn("redis.log", code)

    def test_switch_to_isolated_does_everything_in_one_script(self):
        """`EC3`：建段＋複製作業對象＋改 `pageModes` 必須在同一支腳本內。

        三次獨立寫入之間崩潰會留下「模式已改為 isolated 但段不存在」。
        """
        source = SWITCH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("HEXISTS", source)   # 建段判定
        self.assertIn("pageModes", source)  # 改模式
        self.assertIn("EXPIRE", source)     # 續期
        self.assertIn("source_tgt_field", source)  # 複製作業對象


class PureFunctionLayerTest(unittest.TestCase):
    """三層形狀（`team.md`）：純函式層不得接觸 I/O。"""

    def test_session_types_imports_no_redis_and_no_db(self):
        """`session_types` 是 property-based 測試的落點，而 PBT 的前提是被測
        對象是純函式。"""
        roots = imported_roots(parse(TYPES_PATH))
        self.assertEqual(roots & {"redis", "sqlalchemy", "models", "database"}, set())
        self.assertEqual(roots & FORBIDDEN_IMPORT_ROOTS, set())

    def test_session_store_does_not_import_the_db_layer(self):
        """`K-07` 的 facade 是**鴨子型別注入**的，刻意不 import——否則
        `sqlalchemy` 與 `models` 會進入本模組的 import 集合。"""
        roots = imported_roots(parse(STORE_PATH))
        self.assertEqual(roots & {"sqlalchemy", "models", "database"}, set())

    def test_redis_py_is_imported_lazily_not_at_module_level(self):
        """延遲匯入讓本模組在測試中（替身注入）與未安裝 redis-py 的開發機上
        都可被匯入。"""
        self.assertNotIn("redis", module_level_imported_roots(parse(GATEWAY_PATH)))
        self.assertIn("redis", imported_roots(parse(GATEWAY_PATH)))

    def test_only_the_gateway_talks_to_the_redis_client(self):
        """分層斷言：`session_store` 不得自己發 Redis 指令。"""
        self.assertNotIn("execute_command", code_identifiers(parse(STORE_PATH)))


class StartupFailureIsLoudTest(unittest.TestCase):
    """`BR3.5`：上限參數缺值時**不得**以無上限啟動。"""

    def test_the_history_cap_has_no_default_value_anywhere(self):
        """以無上限啟動會讓單一 Redis key 無上界成長，而那是無聲的。

        本條斷言 `resolve_history_max` 的缺值路徑是 `raise`，不是 `return`
        一個預設值——既有前例是 `ADR-008`／`K-01` 的 `EMBEDDING_PROVIDER`。
        """
        func = find_function(parse(STORE_PATH), "resolve_history_max")
        raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(len(raises), 2)

    def test_main_validates_the_configuration_at_startup(self):
        """掛在 startup hook（而非 import 時）是刻意的：既有測試完全不設定本
        變數，而以 `TestClient(app)` 不觸發該 hook。"""
        source = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn("configure_session_env", source)


if __name__ == "__main__":
    unittest.main()
