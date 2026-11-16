"""U22 progress-channel 的契約閘門（5 個）。

這些測試讀**原始碼文字／AST** 並斷言。形狀沿用
`backend/tests/test_hierarchy_migration.py` 的
`test_schema_rbac_sql_matches_migration_ddl`（由 U4 交付、現在就在跑）。

為什麼它們是測試而不是 `scripts/*.py --check`：`ci.yml` 的 backend job 會跑
`python -m unittest discover -s tests`，它自動撿到 `backend/tests/` 下的任何新檔
——所以把閘門寫成測試即等於進了 CI，**零設定變更**。附帶兩個好處：失敗訊息是
標準 unittest 輸出（會說明哪一個條件不成立，而非只有 exit code），且本機與 CI
行為一致。

**這五個閘門檢查的都是「某個東西不存在」，而這類檢查最容易寫成恆真**
（pattern 寫錯就永遠找不到，於是永遠綠）。每一個都有對應的突變驗證，結果記在
本單元 record 的 `code-summary.md`；下方各測試的 `@note` 寫明它對應哪一個突變。
"""

from __future__ import annotations

import ast
import unittest
import warnings
from pathlib import Path

from tests.helpers import backend_dir

REPO_ROOT = backend_dir.parent
DESIGN_AGENT = backend_dir / "services" / "design_agent.py"
PROGRESS_CHANNEL = backend_dir / "services" / "progress_channel.py"

#: 掃描時跳過的目錄：版控內部、快取、第三方與前端。**刻意不跳過 backend 以外
#: 的原始碼目錄**（scripts／tools 等）——閘門 1e 的全部價值在於呼叫點的清單
#: 是「數出來的」而不是「寫死的」，縮小掃描範圍等於把寫死換個位置。
_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}

#: 本模組**不得**出現的隨機／鍵鑄造來源（U22-V5）。
_MINTING_MODULES = ("uuid", "secrets", "random")

#: 鑄造端**允許**的來源（SEC-1）：CPython 下 `uuid.uuid4()` 走 `os.urandom`。
_ALLOWED_MINTING_SOURCES = ("secrets.", "uuid.uuid4", "uuid4(")

#: 鑄造端**禁止**出現在鍵的取值運算式裡的東西（SEC-1 逐字的禁止清單）。
#: 遞增計數器在行程重啟後從頭開始，而若有任何紀錄仍帶著舊鍵，重用會讓兩個不同
#: 請求在紀錄上無法區分。
_FORBIDDEN_MINTING_TOKENS = (
    "random",
    "time(",
    "time.",
    "now(",
    "counter",
    "count(",
    "thread_id",
    "current_user",
    "user.id",
    "user_id",
)


def _python_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def _is_test_fixture(path: Path) -> bool:
    """該檔是否位於測試目錄下。

    **判別以目錄為準而非檔名前綴**，這一點是刻意的：`backend/test_agent.py` 是
    一支 CLI 工具、是設計逐字點名的三個呼叫點之一，必須留在鑄造檢查的作用域內；
    若以 `test_` 前綴判別就會把它一起排除掉，而那會讓一個真實的入口端靜默脫離
    閘門——正是這道閘門存在要防的形狀。
    """
    return "tests" in path.parts[:-1]


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _find_call_sites(func_name: str) -> list[tuple[Path, ast.Call, str]]:
    """枚舉整個 repo 內對 `func_name` 的呼叫點。

    **這是閘門 1e 的核心，也是最容易被寫錯的地方。** 正確的寫法是「先枚舉出
    全部呼叫點，再逐點斷言」；錯的寫法是「grep 新參數有沒有出現在某幾支檔裡」
    ——後者在只改一處時也會過，而那正是 BR5.1 只列一個呼叫點所造成的缺口在
    修補裡重現一次。本函式不接受任何路徑清單參數：清單是數出來的。
    """
    sites: list[tuple[Path, ast.Call, str]] = []
    for path in _python_files(REPO_ROOT):
        try:
            source = path.read_text(encoding="utf-8")
            with warnings.catch_warnings():
                # repo 內有既有的非 raw 字串轉義警告（不屬本單元），不讓它
                # 污染本測試的輸出。
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - 非本單元的檔
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) == func_name:
                sites.append((path, node, source))
    return sites


class RetiredModuleStateTest(unittest.TestCase):
    def test_the_retired_module_level_state_is_gone(self):
        """
        @purpose U22 的完成判準有一半在「既有程式裡的符號消失」，而那是可 grep
                 的條件、不需判斷。舊符號留著即等於新通道只是多了一條路徑而非
                 取代——錯送路徑仍然可達。
        @given backend/services/design_agent.py 的原始碼文字
        @step 搜尋那個共用進度佇列的全域名 | 零命中
        @step 搜尋那個「最後一次產圖 XML」的全域名 | 零命中
        @step 搜尋「把該全域設回 None」那一行 | 零命中
        @step 確認 _drain_progress 已改為呼叫 ProgressChannel.drain | 命中
        @pass 三個退場符號皆零命中，且讀取端已改接新通道
        @story US13.1
        @note 對應突變 M1（把那個佇列的宣告一行加回 design_agent.py）。
              **檢查是純文字層而非 AST 層**，所以註解裡寫出舊名也會讓它紅
              ——這是刻意的：一個指名已不存在符號的註解本身就是腐化風險。
              正因如此，design_agent.py 的退場說明刻意不逐字寫出舊名。
        """
        source = DESIGN_AGENT.read_text(encoding="utf-8")

        # 兩個退場符號的名字在本測試檔內也不能寫成字面值，否則下一個人會
        # 複製貼上到被測檔裡。以組合方式產生。
        queue_global = "_" + "progress" + "_queue"
        xml_global = "_" + "last" + "_xml"

        self.assertNotIn(
            queue_global, source, "共用的模組層進度佇列必須已被刪除（U22-V3 1a）"
        )
        self.assertNotIn(
            xml_global, source, "死狀態『最後一次產圖的 XML』必須已被刪除（U22-V3 1b）"
        )
        self.assertNotIn(
            f"{queue_global} = None",
            source,
            "把全域設回 None 那一行必須已被刪除（U22-V3 1c）",
        )
        self.assertIn(
            "ProgressChannel.drain",
            source,
            "_drain_progress 必須已改寫為呼叫 ProgressChannel.drain（U22-V3 1d）",
        )


class RunDesignAgentCallSiteTest(unittest.TestCase):
    #: 本 intent 落地時實測的呼叫點數。**這不是一份白名單**——它只是防止枚舉
    #: 器壞掉之後測試恆真通過（找到 0 個呼叫點時所有斷言都真空成立）。合法
    #: 新增呼叫點會讓這個下限仍然成立；刪掉一個呼叫點才會紅，而那也該被看到。
    MINIMUM_KNOWN_CALL_SITES = 3

    def test_every_run_design_agent_call_site_supplies_a_request_key(self):
        """
        @purpose 進度鍵必須在**每一個**呼叫點都被傳入。漏掉任何一個的後果是該
                 路徑的全部 progress／xml 走 BR3.2 被記 log 丟棄——畫面上只是
                 沒有進度訊息，不會有錯誤，所以漏掉不會被人發現。
        @given 整個 repo 的 Python 檔
        @step 以 AST 枚舉出全部 run_design_agent 的呼叫點（不得寫死路徑清單）| 至少三個
        @step 對枚舉出的每一個呼叫點逐點檢查 | 每一個都有 request_key 關鍵字引數
        @pass 枚舉數不低於下限，且每一個呼叫點都帶 request_key
        @story US13.1
        @note 對應突變 M2——**六個突變裡最重要的一個**。M2 只把其中一個呼叫點
              改回不傳鍵（另兩處保持正確）。若本測試被寫成「grep request_key
              有沒有出現」，M2 會過（另兩處仍有該參數），而那就等於沒有本測試。
        """
        sites = _find_call_sites("run_design_agent")
        self.assertGreaterEqual(
            len(sites),
            self.MINIMUM_KNOWN_CALL_SITES,
            f"只枚舉到 {len(sites)} 個 run_design_agent 呼叫點，"
            f"低於實測下限 {self.MINIMUM_KNOWN_CALL_SITES}——"
            "枚舉器可能壞了，而壞掉的枚舉器會讓本測試恆真通過",
        )

        for path, call, _source in sites:
            with self.subTest(call_site=f"{path.relative_to(REPO_ROOT)}:{call.lineno}"):
                keywords = {kw.arg for kw in call.keywords if kw.arg}
                self.assertIn(
                    "request_key",
                    keywords,
                    f"{path.relative_to(REPO_ROOT)}:{call.lineno} 的 run_design_agent "
                    "呼叫沒有傳入 request_key——該路徑的進度事件會被整批丟棄",
                )

    def test_the_entry_points_mint_keys_from_a_cryptographic_source(self):
        """
        @purpose 鍵是這條通道**唯一**的存取控制機制（drain 不做任何身分檢查），
                 所以鍵的產生方式就是存取控制。禁止遞增計數器的理由不是怕外部
                 猜——這個 library 被同進程的自家程式呼叫，沒有不受信任的呼叫
                 端；真正的理由是同一行程內兩個請求的鍵必須互不碰撞、且不因
                 重啟而重用。
        @given 由上一個測試的同一套枚舉得出的呼叫點集合，**排除測試目錄下的夾具**
        @step 確認排除夾具後的呼叫點數仍不低於實測下限 | 是（否則有入口端脫離了閘門）
        @step 對每一個呼叫點取出 request_key 的取值運算式 | 可定位
        @step 檢查該運算式（或它所引用變數的指派）用的是 secrets 或 uuid4 | 是
        @step 檢查該運算式不含 random／時間戳／計數器／由使用者 id 或 thread_id 推導 | 皆不含
        @pass 全部呼叫點的鑄造端皆為密碼學安全來源，且無任何禁止來源
        @story US13.1
        @note 對應突變 M3（把其中一個呼叫點的鑄造改為 f"req-{counter}" 形狀）。
              **覆蓋的檔案集合來自枚舉而非寫死的兩支檔**——原規格只點名
              agent_router 與 wa_collab_orchestrator 兩支，漏了第三個呼叫點；
              由枚舉導出使第四個呼叫點也自動被覆蓋。
              **這件事已實地發生過一次**：本單元為整合邊界新增測試之後，枚舉
              器立刻把那支測試檔認成第四個呼叫點並紅燈（它的鍵是函式參數、
              追不到指派）。那正是閘門該有的反應，也是本測試與上一個測試作用域
              分家的由來；判別器以**目錄**而非檔名前綴判定，才不會連
              `backend/test_agent.py` 這個真實入口端一起排除。
        """
        all_sites = _find_call_sites("run_design_agent")
        self.assertGreaterEqual(len(all_sites), self.MINIMUM_KNOWN_CALL_SITES)

        # **作用域刻意小於上一個測試**：鑄造必須是密碼學安全來源，這是對
        # **產品入口端**的要求；測試夾具刻意用固定、可讀的鍵（`integ-key-A`
        # 之類），好讓失敗可重現、也好直接對特定鍵下斷言。對夾具要求隨機鍵
        # 會讓測試無法斷言鍵本身，而且夾具不是存取控制邊界。
        # 上一個測試（「每個呼叫點都要傳鍵」）的作用域**仍含夾具**——一個忘了
        # 傳鍵的測試本身就是壞測試。
        sites = [s for s in all_sites if not _is_test_fixture(s[0])]
        self.assertGreaterEqual(
            len(sites),
            self.MINIMUM_KNOWN_CALL_SITES,
            f"排除測試夾具後只剩 {len(sites)} 個呼叫點，低於實測下限 "
            f"{self.MINIMUM_KNOWN_CALL_SITES}——若有產品入口端被搬進 tests/ "
            "之下，它會從本閘門脫離，而這個下限就是為了讓那件事大聲紅",
        )

        for path, call, source in sites:
            rel = f"{path.relative_to(REPO_ROOT)}:{call.lineno}"
            with self.subTest(call_site=rel):
                key_expr = next(
                    (kw.value for kw in call.keywords if kw.arg == "request_key"), None
                )
                self.assertIsNotNone(key_expr, f"{rel} 沒有 request_key 引數")

                expressions = [ast.get_source_segment(source, key_expr) or ""]
                # 引數若是變數名，就把該檔內對它的全部指派一併納入檢查。
                if isinstance(key_expr, ast.Name):
                    tree = ast.parse(source)
                    assignments = [
                        ast.get_source_segment(source, node.value) or ""
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Assign)
                        and any(
                            isinstance(t, ast.Name) and t.id == key_expr.id
                            for t in node.targets
                        )
                    ]
                    self.assertTrue(
                        assignments,
                        f"{rel} 的 request_key 是變數 {key_expr.id} 但找不到它的指派",
                    )
                    expressions = assignments

                for expr in expressions:
                    self.assertTrue(
                        any(src in expr for src in _ALLOWED_MINTING_SOURCES),
                        f"{rel} 的鍵取值運算式 {expr!r} 沒有使用密碼學安全來源"
                        f"（允許 {_ALLOWED_MINTING_SOURCES}）",
                    )
                    for token in _FORBIDDEN_MINTING_TOKENS:
                        self.assertNotIn(
                            token,
                            expr,
                            f"{rel} 的鍵取值運算式 {expr!r} 含禁止的來源 {token!r}",
                        )


class ProgressChannelMintsNothingTest(unittest.TestCase):
    def test_progress_channel_contains_no_key_minting_function(self):
        """
        @purpose 鍵一律由參數傳入，本模組不鑄造它（鑄造在入口端）。本模組能
                 驗證的就只有「它自己沒有鑄造能力」這一半——鑄造端的正確性由
                 上一個測試承擔。
        @given backend/services/progress_channel.py 的 AST 與原始碼文字
        @step 以 AST 檢查 import 清單 | 不含 uuid／secrets／random
        @step 以 AST 檢查程式碼對這三個名字的引用 | 零命中（無隨機源可達即無法鑄造）
        @step 檢查有無名字像在鑄造鍵的函式 | 無（mint／new_key／generate 等）
        @pass 三個隨機源皆不可達，且無鑄造形狀的函式名
        @story US13.1
        @note 對應突變 M4（在 progress_channel.py 加一行 import uuid）。
              第二個子句（「無任何回傳新鍵的函式」）在原規格沒有可執行的
              pattern。本測試給它一個：**沒有隨機源可用的模組無法鑄造不可猜的
              鍵**，所以「三個模組皆不可達」就是它的可執行形式。函式名那一項
              是補充的 canary，不是證明——它抓的是「有人寫了一個鑄造函式」
              這個最可能的形狀，而真正的保證來自前一項。
        """
        tree = ast.parse(PROGRESS_CHANNEL.read_text(encoding="utf-8"))

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        # 全檔對這三個名字的**程式層**引用（Name 與 Attribute 的根），
        # 不含註解與 docstring——後者談論它們是允許且必要的。
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                referenced.add(node.value.id)

        for module in _MINTING_MODULES:
            self.assertNotIn(
                module,
                imported,
                f"progress_channel.py 不得 import {module}——本模組不鑄造鍵（U22-V5）",
            )
            self.assertNotIn(
                module,
                referenced,
                f"progress_channel.py 的程式碼不得引用 {module}；沒有隨機源可達，"
                "本模組就無法鑄造不可猜的鍵",
            )

        minting_name_fragments = ("mint", "new_key", "newkey", "make_key", "create_key")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                for fragment in minting_name_fragments:
                    self.assertNotIn(
                        fragment,
                        lowered,
                        f"函式 {node.name} 的名字看起來像在鑄造鍵（{fragment}）",
                    )


class NoExceptionTextReachesTheCallerTest(unittest.TestCase):
    #: 本 intent 落地後 design_agent.py 內 `except ... as <name>` 的綁定數。
    #:
    #: **這個數字是 0 而非設計所寫的 2，而 0 是更強的條件。** 設計要求「綁定數
    #: 等於 2 且兩者皆綁 `e`」，依據是它實測 HEAD 當時恰有兩個 `except
    #: Exception as e`。本單元把那兩個區塊的例外原文出口收斂成只有
    #: `logger.exception`，於是例外物件在這支檔裡**完全沒有使用者**，兩個
    #: handler 都改成了裸 `except Exception:`。
    #:
    #: 若照字面把它釘在 2，就必須寫回 `except Exception as e:` 並讓 `e` 成為
    #: 未被使用的變數——那會把這道閘門要監視的那個變數當成死碼重新引入。
    #: 釘在 0 保留了 canary 的全部意圖（新增任何綁定都讓它大聲紅），而且
    #: **比釘在 2 更早觸發**：它在第一個新綁定就紅，不是等到第三個。
    #: 此偏離已記入 code-summary.md。
    EXPECTED_EXCEPTION_BINDINGS = 0

    #: 第一個子句的形狀級 pattern 覆蓋得到的綁定名。第二個子句的真正不變量是
    #: 「**每一個存在的綁定都必須是這些名字之一**」——否則第一個子句的完整性
    #: 宣稱就不成立（改名的例外變數會從 pattern 底下逃掉）。
    COVERED_BINDING_NAMES = frozenset({"e", "exc"})

    def test_no_exception_text_reaches_the_caller(self):
        """
        @purpose 內部例外原文不得送達使用者。這是獨立於事件錯送之外的第二個
                 安全面：原狀有兩行把例外插進對外字串，其中一行直送 SSE、另一
                 行進入 LLM 的 context 再由模型決定要不要轉述給使用者。更要緊
                 的是 BR1.2 新增的 DuplicateChannelKey 會走同一條路——不修的話
                 修法本身會在它宣稱要封的那個面上開一個新口。
        @given backend/services/design_agent.py 的原始碼文字與 AST
        @step 搜尋把例外插進字串的四種樣式（{e}／{exc}／str(e)／repr(e)）| 全部零命中
        @step 以 AST 取出全部 except 的綁定名 | 綁定數等於釘住的值
        @step 檢查每一個綁定名 | 皆在第一個子句的 pattern 覆蓋範圍內
        @pass 四個樣式零命中，且綁定的集合與形狀都被釘住
        @story US13.1
        @note 對應突變 M5（把其中一處的固定字串改回插值形狀）與 M6（新增一個
              帶綁定的 except 區塊）。第一個子句是**形狀級而非字面級**：它不
              依賴訊息文字，所以日後有人新增第三個 except 並插入例外也會被抓
              到。射程限制如實記載：`"...".format(e)`、`"..." % e`、`{e.args}`
              以及任何改名的例外變數都能從這四個樣式底下逃掉——第二個子句就是
              為此存在，它把「綁定的名字與數量」釘住，使第一個子句的完整性
              宣稱持續成立。要真正完整需要 AST 層的 taint 分析，成本遠高於本
              單元的規模，故不做，但這個限制被寫下來而不是被宣稱為完整
              （見 code-summary.md 的 S-10）。
        """
        source = DESIGN_AGENT.read_text(encoding="utf-8")

        # --- 子句一：形狀級的插值樣式零命中 -------------------------------
        for pattern in ("{e}", "{exc}", "str(e)", "repr(e)"):
            self.assertNotIn(
                pattern,
                source,
                f"design_agent.py 內出現 {pattern!r}——內部例外原文可能送達使用者",
            )

        # --- 子句二：綁定的名字與數量被釘住 -------------------------------
        handlers = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ExceptHandler)
        ]
        bindings = [node.name for node in handlers if node.name]

        self.assertEqual(
            len(bindings),
            self.EXPECTED_EXCEPTION_BINDINGS,
            f"design_agent.py 的 `except ... as` 綁定數為 {len(bindings)}"
            f"（綁定名 {bindings}），與釘住的 {self.EXPECTED_EXCEPTION_BINDINGS} 不符。"
            "新增一個綁定本身不是錯，但它讓子句一的四個樣式不再足以涵蓋全檔"
            "——請確認新區塊沒有把例外原文送給呼叫端，再更新這個數字。",
        )
        for name in bindings:
            self.assertIn(
                name,
                self.COVERED_BINDING_NAMES,
                f"例外綁定名 {name!r} 不在子句一的 pattern 覆蓋範圍內"
                f"（{sorted(self.COVERED_BINDING_NAMES)}），插值會從檢查底下逃掉",
            )


if __name__ == "__main__":
    unittest.main()
