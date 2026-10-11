"""`U11 intent-router` 的**結構斷言** ＋ L0 讀取層的三條行為斷言。

本檔對應 `unit-test-instructions.md §三` 的第五列。

## 為什麼這個檔案必須獨立存在

本單元的多數安全需求（`SEC-1` 不自取身分、`SEC-2` 不暴露端點、`NFR6.60`
不繞過 facade、`BR7.4` 對 session 唯讀、`NFR3.67` 無模組層可變狀態）是**形狀**
而非行為。用執行期測試驗它，等於去證明某件事不會發生——而那在測試裡永遠只能
驗到你想到的那幾條路徑。讀原始碼比對是二元可判的。

## 為什麼以 `ast` 解析而不是字串比對

形狀沿用 `test_session_contract.py`（既有前例，由 `U10` 交付、現在就在跑）。
本單元的七個模組都在 docstring 裡解釋「為什麼不自取身分」「為什麼不建端點」，
所以 `"get_current_user" in source` 對它們**必然成立**——一個字串比對的測試會
永遠紅燈，而把 docstring 刪掉來讓它變綠會損失本單元最需要被讀到的理由。

故本檔以 **import 集合 ＋ 程式行的識別字**（AST 節點，不含 docstring 與註解）
斷言。

## L0 的三條行為斷言為什麼也在這裡

`NFR7.62` 的驗證方式逐字是「**斷言 `kinds` 的實際傳值**（以替身捕捉呼叫
參數）」——它是行為而非形狀，但它守的是同一條安全邊界，而
`unit-test-instructions.md §三` 把它列在本檔。`D-1` 的降級／失敗差別待遇
（`U8` 降級、`U10` 向上傳遞）一併放在這裡，因為那兩條也是「把設計決定變成
會紅的東西」而非功能測試。

**本檔的測試數高於策略指引的每元件 5–8 個**（實際數字由檔尾的 `unittest`
輸出決定，不在此手寫一個會過期的值）。不壓低的理由：每條禁令逐條二元可判，
合併成一條會讓失敗訊息說不出是哪一條被違反；而 `NFR7.62` 與 `D-1` 的三條由
`unit-test-instructions.md` 指派在本檔。向上偏離不降低任何目標。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import dataclasses
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from services.intent_routing import (
    _REFERENT_MEMORY_KINDS,
    fetch_routing_context,
)
from services.intent_routing_types import (
    ROUTABLE_CAPABILITIES,
    RoutingObservation,
)
from services.session_types import (
    SEGMENT_SHARED,
    BrainSession,
    ConversationSegment,
    SessionMessage,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = BACKEND_DIR / "services"
MAIN_PATH = BACKEND_DIR / "main.py"
DEMO_GATEWAY_PATH = SERVICES_DIR / "brain_router.py"

ROUTING_PATH = SERVICES_DIR / "intent_routing.py"
TYPES_PATH = SERVICES_DIR / "intent_routing_types.py"
ERRORS_PATH = SERVICES_DIR / "intent_routing_errors.py"
CONFIG_PATH = SERVICES_DIR / "intent_routing_config.py"
CONTEXT_PATH = SERVICES_DIR / "intent_routing_context.py"
PARSER_PATH = SERVICES_DIR / "intent_routing_parser.py"
PREDICATE_PATH = SERVICES_DIR / "intent_routing_predicate.py"
PORT_PATH = SERVICES_DIR / "intent_routing_port.py"

#: 本單元的**全部**新模組。清單是**寫死的**而不是 glob——glob 會在有人漏建或
#: 改名時靜默少驗一個檔，而這一組測試的全部價值在於它涵蓋每一個模組。
UNIT_MODULES = (
    ROUTING_PATH,
    TYPES_PATH,
    ERRORS_PATH,
    CONFIG_PATH,
    CONTEXT_PATH,
    PARSER_PATH,
    PREDICATE_PATH,
    PORT_PATH,
)

#: `SEC-1`：不自取身分。自取身分會讓同進程呼叫者得以用別人的身分分類與讀記憶。
FORBIDDEN_IDENTITY_IDENTIFIERS = {
    "get_current_user",
    "get_user_from_token",
    "ContextVar",
    "Request",
    "WebSocket",
}

#: `SEC-1`／`SEC-2`：request／websocket 型別一律不得出現在 import 集合。
FORBIDDEN_IMPORT_ROOTS = {"fastapi", "starlette", "websockets", "httpx"}

#: `SEC-2`：不註冊任何 route。
FORBIDDEN_ROUTER_IDENTIFIERS = {"APIRouter", "include_router", "add_api_route"}

#: `NFR6.60`：讀記憶只經 `K-08` 的 `MemoryFacade`，不得繞過它或碰 DB session。
FORBIDDEN_MEMORY_MODULES = {
    "services.memory_service",
    "services.memory_types",
    "database",
    "models",
    "sqlalchemy",
    "sqlalchemy.orm",
}

#: `BR7.4`：對 `SessionContext` **唯讀**。四個寫入方法在此無從被呼叫。
FORBIDDEN_SESSION_WRITE_IDENTIFIERS = {
    "set_work_target",
    "append_message",
    "set_sharing_mode",
    "touch",
}

#: `BR7.3`：不判權。自建第二套判定會與既有授權層分歧。
FORBIDDEN_AUTHZ_IDENTIFIERS = {
    "require_story_action",
    "user_can",
    "ensure_role_permissions_seeded",
}


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


def imported_modules(tree: ast.Module) -> set:
    """被 import 的**完整模組路徑**集合（含函式內的延遲匯入）。"""
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            modules.add(node.module)
    return modules


def code_identifiers(tree: ast.Module) -> set:
    """**程式行**用到的識別字。刻意不含 docstring 與註解。"""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
    return found


def existing_modules() -> tuple:
    """本輪已落地的模組。**每一個缺檔都會由下方第一條測試點名**，

    不是靜默跳過——只有先確認清單完整，逐檔的禁令才有意義。
    """
    return tuple(p for p in UNIT_MODULES if p.exists())


def make_session(messages=(), *, project_id=None, system_id=None, diagram_id=None):
    segment = ConversationSegment(
        segment_id=SEGMENT_SHARED,
        created_at="2026-10-10T00:00:00+00:00",
        messages=tuple(messages),
        project_id=project_id,
        system_id=system_id,
        diagram_id=diagram_id,
    )
    return BrainSession(
        session_key="brain:1",
        user_id=1,
        segments={SEGMENT_SHARED: segment},
    )


class UnitModuleSetIsCompleteTest(unittest.TestCase):
    """缺檔必須是一個**紅燈**，不是一個少驗一條的靜默跳過。"""

    def test_every_declared_module_exists(self):
        missing = [p.name for p in UNIT_MODULES if not p.exists()]
        self.assertEqual(missing, [], f"本單元宣告的模組缺檔：{missing}")


class NoIdentityOfItsOwnTest(unittest.TestCase):
    """`SEC-1`：`principal` 一律由參數傳入。"""

    def test_no_module_takes_identity_from_the_transport(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = code_identifiers(parse(path)) & FORBIDDEN_IDENTITY_IDENTIFIERS
                self.assertEqual(hits, set())

    def test_no_module_imports_a_web_framework_or_http_client(self):
        """`SEC-2` 的一半：**不得** `import httpx` 直打。

        出站呼叫一律經 `langgraph_runtime`，而它是所有 LLM 路徑的共同入口
        ——在那裡建一次所有路徑都受益。
        """
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = imported_roots(parse(path)) & FORBIDDEN_IMPORT_ROOTS
                self.assertEqual(hits, set())


class NoExposedEndpointTest(unittest.TestCase):
    """`SEC-2`：不暴露任何對外端點。

    這同時是 `openapi.json` diff 為空的**來源**：沒有端點，就沒有 schema
    可漂移，CI 的 OpenAPI drift 閘門因此不會動。
    """

    def test_no_module_creates_or_registers_a_router(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = code_identifiers(parse(path)) & FORBIDDEN_ROUTER_IDENTIFIERS
                self.assertEqual(hits, set())

    def test_main_does_not_mount_an_intent_router_endpoint(self):
        """反向面：`main.py` 也不能把它掛上去。

        `SEC-2` 逐字「模組不建立 `APIRouter`，不被 `main.py` `include_router`」
        ——兩句話是兩個入口，只驗前者會讓違規換個位置存在。
        """
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
        for forbidden in (
            "intent_routing",
            "intent_router",
            "intent_routing_router",
        ):
            self.assertNotIn(forbidden, mounted)


class MemoryAccessGoesThroughTheFacadeTest(unittest.TestCase):
    """`NFR6.60`：不繞過 `MemoryFacade`、不碰 DB session 型別。"""

    def test_no_module_imports_the_memory_internals_or_a_db_session(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = imported_modules(parse(path)) & FORBIDDEN_MEMORY_MODULES
                self.assertEqual(hits, set())


class SessionContextIsReadOnlyTest(unittest.TestCase):
    """`BR7.4`：四個寫入方法在本單元**無從被呼叫**。

    `K-09` 的 `consumers` 是 `[U11, U12, U13]` 且**未按方法分拆**，所以契約
    本身擋不住一個好意的實作者在 `classify()` 裡呼叫 `set_work_target`
    ——那會製造第二個作業對象寫入端，並讓 `AC1.2.3` 的「不變」失去唯一的
    機制基礎（`functional-design` 審查 `R-05`）。
    """

    def test_no_module_calls_a_session_write_method(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = (
                    code_identifiers(parse(path))
                    & FORBIDDEN_SESSION_WRITE_IDENTIFIERS
                )
                self.assertEqual(hits, set())

    def test_no_module_imports_the_session_store(self):
        """最強形式：連 `session_store` 都不 import。

        拿不到比記得不要呼叫可靠。`session_types`（零 I/O、零 DB 的純資料
        形狀）仍可 import——段識別的封閉集合必須有單一真實來源。
        """
        for path in existing_modules():
            with self.subTest(module=path.name):
                self.assertNotIn(
                    "services.session_store", imported_modules(parse(path))
                )


class NoAuthorizationOfItsOwnTest(unittest.TestCase):
    """`BR7.1`／`BR7.3`：本單元不判權。"""

    def test_no_module_touches_the_permission_matrix(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                hits = code_identifiers(parse(path)) & FORBIDDEN_AUTHZ_IDENTIFIERS
                self.assertEqual(hits, set())


class CapabilityEnumHasASingleSourceTest(unittest.TestCase):
    """`team.md` 的「單一真實來源」：副本必須有一條鎖住一致性的測試。

    同一份能力 id 清單也存在於 `brain_router.py` 的 DEMO `_CAPABILITIES`。
    規則逐字要求「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試」——
    本條即是。`U13` 落地時 DEMO 整支被取代，屆時本條應改為鎖住正式閘道。
    """

    def test_the_demo_gateway_capability_ids_match_the_closed_enum(self):
        tree = parse(DEMO_GATEWAY_PATH)
        demo_ids = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
                node.targets[0], ast.Name
            ):
                name = node.targets[0].id
            else:
                continue
            if name != "_CAPABILITIES" or node.value is None:
                continue
            demo_ids = tuple(
                elt.elts[0].value
                for elt in node.value.elts
                if isinstance(elt, ast.Tuple) and elt.elts
            )
        self.assertIsNotNone(
            demo_ids, "找不到 brain_router.py 的 _CAPABILITIES——副本一致性無從鎖住"
        )
        self.assertEqual(
            set(demo_ids),
            set(ROUTABLE_CAPABILITIES),
            "DEMO 閘道與本單元的封閉列舉已漂移（team.md 單一真實來源）",
        )


class ReferentMemoryKindsExcludeEpisodicTest(unittest.TestCase):
    """`NFR7.62`／`BR5.5.logic_executable`：**斷言 `kinds` 的實際傳值**。

    `AC6.1.3`（獨立段無法解析指向共享產出的指涉詞）有兩個違反入口：讀錯段
    （由 `U10` 的段隔離結構性擋下）與**查記憶**——記憶不分段，它是長期、
    跨 session 的。本組擋的是第二個，而它是**現行防護**而非前置護欄：
    `memory_router.py` 的 `POST /api/memory/records` 已可寫入
    `kind=episodic`，使用者今天就能建一筆情節記憶。
    """

    def test_the_kinds_constant_excludes_episodic(self):
        self.assertNotIn("episodic", _REFERENT_MEMORY_KINDS)
        self.assertEqual(_REFERENT_MEMORY_KINDS, ("semantic", "procedure"))

    def test_search_is_actually_called_with_that_constant(self):
        """常數對不對是一回事，**實際傳出去的值**是另一回事。

        只斷言常數時，一個把 `kinds` 寫死在呼叫點的實作也會通過。
        """
        facade = MagicMock()
        facade.search.return_value = []
        fetch_routing_context(
            principal=object(),
            session=make_session(),
            text="把那張圖的資料庫換成 Aurora",
            memory_facade=facade,
        )
        self.assertEqual(facade.search.call_count, 1)
        kwargs = facade.search.call_args.kwargs
        self.assertEqual(kwargs["kinds"], _REFERENT_MEMORY_KINDS)
        self.assertNotIn("episodic", kwargs["kinds"])


class DependencyFailuresGetDifferentTreatmentTest(unittest.TestCase):
    """`D-1`：`U8` 降級、`U10` 向上傳遞。**差別待遇本身是設計決定。**"""

    def test_memory_failure_degrades_and_is_observable(self):
        """因為拿不到術語解釋就讓整輪失敗，是用使用者的體驗去換一個不存在的
        正確性。但降級**必須可被觀測**，否則它是無聲的長期降級。
        """
        facade = MagicMock()
        facade.search.side_effect = RuntimeError("pgvector down")
        context = fetch_routing_context(
            principal=object(),
            session=make_session(
                messages=(
                    SessionMessage(
                        sequence=1,
                        role="assistant",
                        text="已產生架構圖",
                        created_at="2026-10-10T00:00:01+00:00",
                    ),
                ),
                diagram_id=12,
            ),
            text="那張圖",
            memory_facade=facade,
        )
        self.assertTrue(context.memory_degraded)
        self.assertEqual(context.memory_notes, ())
        # 降級不是失敗：其餘上下文照常取得。
        self.assertEqual(context.work_target_hint, "架構圖 #12")
        self.assertEqual(len(context.recent_messages), 1)

    def test_session_read_failure_propagates_untouched(self):
        """`logical-components.md` §三 逐字「本單元不處理——它向上傳遞」。

        反向斷言：若本層對 session 讀取加了 `try/except`，「取不到脈絡」會變成
        一個看起來正常的結果，而指涉詞解析會在沒有脈絡的情況下猜——那正是
        `BR8.2` 要防的那件事。
        """
        broken = MagicMock()
        broken.segment.side_effect = RuntimeError("session backend unavailable")
        facade = MagicMock()
        facade.search.return_value = []
        with self.assertRaises(RuntimeError):
            fetch_routing_context(
                principal=object(),
                session=broken,
                text="改架構圖",
                memory_facade=facade,
            )


class NoModuleLevelMutableStateTest(unittest.TestCase):
    """`NFR3.67`／`NFR4.70`：模組層**無可變綁定**。

    `NFR3.67` 禁止「把行程內共享可變狀態當成擴展手段」（快取結果、計數器、
    持有跨請求語意狀態的連線池），`K-09` 的 `hard_rule` 同精神逐字「一律放
    Redis，**不得放行程記憶體**」。本單元無狀態（`NFR4.70` 是**結構性滿足**
    而非豁免），所以斷言是二元的：模組層不得有 `dict`／`list`／`set` 字面值。

    **唯一的例外是 `__all__`**，它是標準的匯出宣告而不是狀態。例外只開這一個
    且寫在這裡——`performance-design.md` §二 的 `P-4`（連線重用）原本預期會
    需要一個「client factory」白名單，而本站把 compiled graph 的快取放在
    `IntentRouter` **實例**上，所以那個例外不需要存在（理由寫在
    `IntentRouter` 的 docstring）。
    """

    #: 不是狀態，是匯出宣告。
    ALLOWED_NAMES = {"__all__"}

    def test_no_module_binds_a_mutable_literal_at_module_level(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                offenders = []
                for node in parse(path).body:
                    if isinstance(node, ast.Assign):
                        targets = [
                            t.id for t in node.targets if isinstance(t, ast.Name)
                        ]
                        value = node.value
                    elif isinstance(node, ast.AnnAssign) and isinstance(
                        node.target, ast.Name
                    ):
                        targets = [node.target.id]
                        value = node.value
                    else:
                        continue
                    if not isinstance(value, (ast.Dict, ast.List, ast.Set)):
                        continue
                    for name in targets:
                        if name not in self.ALLOWED_NAMES:
                            offenders.append(name)
                self.assertEqual(
                    offenders,
                    [],
                    f"{path.name} 在模組層綁定了可變字面值：{offenders}",
                )


class LogWhitelistIsATypeTest(unittest.TestCase):
    """`SEC-3`／`SEC-5`：白名單**就是** `RoutingObservation` 的欄位集合。

    白名單若只存在於文件，下一個人加一個欄位時不會有任何東西擋他。
    本 repo 為 public、Actions log 公開可讀——**一次意外 echo 即等同公開
    發布**（`project.md` 逐字）。

    **`referent` 最容易被漏**：它看起來像識別碼，實際上是解析使用者句子得到
    的系統名或圖名——那是使用者的內容。`label` 同理，它是模型對使用者輸入的
    **複述**；`U10` 的禁令只需涵蓋訊息內容，本單元還要涵蓋這一層。
    """

    FORBIDDEN_FIELDS = {
        "text",
        "label",
        "labels",
        "referent",
        "prompt",
        "content",
        "response",
        "memory_notes",
        "candidates",
    }

    def test_the_observation_type_cannot_carry_user_content(self):
        names = {f.name for f in dataclasses.fields(RoutingObservation)}
        self.assertEqual(names & self.FORBIDDEN_FIELDS, set())
        self.assertEqual(
            names,
            {
                "turn_id",
                "slot_count",
                "capability_ranks",
                "scores_available",
                "can_single_out",
                "elapsed_ms",
                "error_kind",
                "memory_degraded",
            },
        )

    def test_memory_degraded_is_present_because_d1_depends_on_it(self):
        """`D-1`（`U8` 不可用時降級而非失敗）的正當性**完全建立在**「降級可被
        觀測」這一個條件上。

        審查 `R-02` 抓到的正是這個欄位當時只存在於要求句裡、兩份
        `RoutingObservation` 定義都沒有它。條件沒落地，判斷就沒有依據。
        """
        names = {f.name for f in dataclasses.fields(RoutingObservation)}
        self.assertIn("memory_degraded", names)

    def test_the_observation_object_is_never_handed_to_the_logger(self):
        """形狀斷言：`log_routing_observation` 逐一列欄位，不把物件丟給 logger。

        dataclass 的 `__repr__` 會印出全部欄位——今天都在白名單上，但「把物件
        丟給 logger」這個形狀會讓下一個人加欄位時自動把它記出去。這與
        `session_types` 檔頭同一條紀律。
        """
        tree = parse(ROUTING_PATH)
        target = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "log_routing_observation"
            ):
                target = node
        self.assertIsNotNone(target, "找不到 log_routing_observation")
        for node in ast.walk(target):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            if not (isinstance(callee, ast.Attribute) and callee.attr in {
                "info", "warning", "error", "debug", "exception"
            }):
                continue
            for arg in node.args:
                self.assertFalse(
                    isinstance(arg, ast.Name) and arg.id == "observation",
                    "不得把 observation 物件整個交給 logger",
                )


class RouterModelIsItsOwnVariableTest(unittest.TestCase):
    """`NFR10.60`／`TS-2`：路由層模型由**獨立**環境變數決定。

    `TS-2` 的驗證方式逐字是「`grep` 斷言本單元**不讀** `LLM_MODEL`」。
    但**裸 `grep` 會命中註解**——`intent_routing_config.py` 第 48 行的註解
    正好逐字寫著「不得沿用 `LLM_MODEL`」，而那是這條規則最需要被讀到的理由。
    所以本條驗的是「它有沒有被**當成程式裡的字串**使用」（AST 的
    `ast.Constant`），不是「這三個字有沒有出現在檔案裡」。

    共用 `LLM_MODEL` 會讓 `[F1]`／`NFR10` 逐字允許的「編排層與功能 agent 得
    使用不同模型」**在設定層消失**——兩者會被同一個值綁在一起，而那個後果在
    任何功能測試上都看不出來。
    """

    def test_no_module_reads_the_functional_agents_model_variable(self):
        for path in existing_modules():
            with self.subTest(module=path.name):
                literals = {
                    node.value
                    for node in ast.walk(parse(path))
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                offenders = sorted(v for v in literals if "LLM_MODEL" in v)
                self.assertEqual(
                    offenders,
                    [],
                    f"{path.name} 把 LLM_MODEL 當成程式字串使用：{offenders}",
                )

    def test_the_router_model_variable_is_read_as_its_own_name(self):
        """反向斷言：**必須**真的有一個獨立變數被讀。

        前一條（零命中）單獨成立時，「完全不讀任何模型設定、寫死一個模型名」
        也會通過——而那會讓「換模型不需改程式」這句話變成假的。
        """
        from services.intent_routing_config import MODEL_ENV

        self.assertEqual(MODEL_ENV, "BRAIN_ROUTER_MODEL")
        literals = {
            node.value
            for node in ast.walk(parse(CONFIG_PATH))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn(MODEL_ENV, literals)


if __name__ == "__main__":
    unittest.main()
