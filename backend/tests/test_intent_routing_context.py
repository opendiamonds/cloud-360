"""`U11 intent-router` 的 **L2 prompt 組裝**測試。**一個 mock 都不需要。**

本檔對應 `unit-test-instructions.md §三` 的第三列。

## 零 mock 是這一層存在的理由

`logical-components.md` §二 逐字：「L2 的純度是刻意設計的——取資料的 I/O 放在
它之外（呼叫端先取好再傳進來），使**「最少上下文」這條規則可以被一個不需要
mock 的測試驗證**。」

反過來說：若 I/O 留在這一層，驗 `BR6.1` 就得先替身兩個依賴、再從替身的呼叫
參數反推 prompt 內容——而那種測試驗的是「我記得去呼叫的那幾處」，不是
「送出去的東西裡有什麼」。`nfr-design` 審查 `R-01` 的 Critical 正是這一層的
純度在同一份產出裡被寫成兩個互斥答案。

## `NFR9.60` 不只是成本紀律，也是資料外送最小化

本單元的 `external_dependencies` 含 **OpenRouter（third-party-api）**，
亦即**使用者的自然語言輸入會離開本平台**。附上整段對話歷程等於把更多個人
內容送出去（ADR-0006 encryption 面）。`cost_discipline` 的原文只講成本，
所以這一組測試同時是安全測試。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import inspect
import unittest
from pathlib import Path

from services.intent_routing_context import (
    DEFAULT_MESSAGE_LIMIT,
    build_routing_prompt,
)
from services.intent_routing_types import ROUTABLE_CAPABILITIES

CONTEXT_PATH = (
    Path(__file__).resolve().parents[1] / "services" / "intent_routing_context.py"
)


def history(size, *, tail=()):
    """`size` 則填充訊息 ＋ 固定的尾段。尾段相同時 prompt 必須逐位元相同。"""
    filler = [("user", f"填充訊息 {i} " + "塞" * 200) for i in range(size)]
    return filler + list(tail)


class MinimalContextTest(unittest.TestCase):
    def test_the_prompt_carries_only_the_last_k_messages(self):
        """`BR6.1`／`NFR9.60`：**不得**整段附上完整歷程。

        斷言兩件事：尾段在裡面、而被截掉的那些**真的不在**。只驗前者會放行
        一個「把全部歷程都塞進去，順便把最後幾則再貼一次」的實作。
        """
        messages = history(
            40,
            tail=[
                ("assistant", "已產生訂單系統架構圖"),
                ("user", "獨一無二的尾段訊息"),
            ],
        )
        prompt = build_routing_prompt(
            user_text="把那張圖的資料庫換成 Aurora",
            work_target_hint="專案 #1",
            recent_messages=messages,
        )
        self.assertIn("獨一無二的尾段訊息", prompt.user)
        self.assertNotIn("填充訊息 0", prompt.user)
        self.assertNotIn("填充訊息 30", prompt.user)

    def test_the_prompt_length_does_not_grow_with_the_history(self):
        """`NFR9.61`：每輪成本與歷程長度線性相關，而歷程上限是**每段 200 則**。

        構造刻意讓兩次呼叫的**尾段完全相同**，所以正確的實作會產出**逐位元
        相同**的 prompt。這比「長度差不多」強：它同時證明被截掉的內容沒有以
        任何形式（摘要、計數、拼接）滲進去。
        """
        tail = [("user", "最後一則")] * DEFAULT_MESSAGE_LIMIT
        short = build_routing_prompt(
            user_text="改架構圖", recent_messages=history(0, tail=tail)
        )
        long = build_routing_prompt(
            user_text="改架構圖", recent_messages=history(400, tail=tail)
        )
        self.assertEqual(short.text, long.text)
        # 另一個方向：整段 200 則 × 4000 字元的最壞情況不得逼近 Jev 的
        # context 32000。這裡以字元數作為上界的代理指標。
        self.assertLess(len(long.text), 8000)


class ReferentPrecedenceTest(unittest.TestCase):
    def test_the_object_named_in_the_sentence_outranks_the_session_value(self):
        """`BR5.3`／`AC1.1.5`：輸入中直接點名的對象**優先於** session 當前值。

        prompt 必須同時具備兩樣東西才算表達了這條規則：句中的對象（它在
        `user_text` 裡）、以及**一條明文的優先序指示**。少了後者，模型沒有
        理由不沿用脈絡列上的那個值——而 `AC1.1.5` 的前提恰好是脈絡列顯示
        「尚未選定」或指向另一個系統。
        """
        prompt = build_routing_prompt(
            user_text="幫庫存系統畫一張架構圖",
            work_target_hint="專案 #1／系統 #7",
            recent_messages=[],
        )
        self.assertIn("庫存系統", prompt.user)
        self.assertIn("專案 #1／系統 #7", prompt.user)
        self.assertIn("優先於", prompt.user)

    def test_an_unset_work_target_is_stated_rather_than_omitted(self):
        """脈絡列顯示「尚未選定」是 `AC1.1.5` 的**前提**，不是異常。

        把這一行整段省略會讓模型無從分辨「沒有作業對象」與「我忘了給」。
        """
        prompt = build_routing_prompt(user_text="畫一張架構圖")
        self.assertIn("尚未選定", prompt.user)


class CapabilityCatalogueTest(unittest.TestCase):
    def test_every_routable_capability_appears_in_the_system_prompt(self):
        """`V-2` 的另一端：我方會拒絕列舉外的值，所以列舉必須**完整**地給出去。

        少給一個能力，模型就只能把那類需求硬塞進別的能力——而解析層不會報錯，
        因為它吐出的值合法。這個失敗模式在測試上看不出來，只有使用者會發現
        「它老是把估成本當成改架構圖」。
        """
        prompt = build_routing_prompt(user_text="估一下成本")
        for capability in ROUTABLE_CAPABILITIES:
            self.assertIn(capability, prompt.system)


class TypeBoundaryTest(unittest.TestCase):
    def test_the_signature_does_not_accept_a_session_object(self):
        """`NFR9.60` 的設計落法：**不給它，它就送不出去。**

        `BrainSession` 持有**全部三段**的完整歷程。把它傳進這一層就等於讓這
        一層有能力把 600 則訊息送出平台，而「它實際上沒送」只能靠 review
        確認。本條斷言的是**拿不到**，而那比「記得不要送」可靠。
        """
        params = inspect.signature(build_routing_prompt).parameters
        self.assertNotIn("session", params)
        for name in params:
            self.assertNotIn("session", name.lower())
        imported = set()
        tree = ast.parse(CONTEXT_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(alias.name for alias in node.names)
        self.assertNotIn("services.session_types", imported)
        self.assertNotIn("BrainSession", imported)


# ---------------------------------------------------------------------------
# 合併前必修第 13 項：L0 的記憶讀取（落點依 `unit-test-instructions.md` 的
# 「合併前必修第 5、13 項」一節指定在本檔）。受測的是 `intent_routing` 的 L0，
# 不是 L2；替身是手寫的最小類別，**仍不使用 `unittest.mock`**。
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from services.intent_routing import IntentRouter, fetch_routing_context  # noqa: E402
from services.intent_routing_config import RoutingConfig  # noqa: E402
from services.memory_errors import MemoryForbidden  # noqa: E402

_SECRET_UTTERANCE = "把訂單系統的資料庫密碼改成 hunter2"


class _Session:
    """只提供 L0 會讀的 `segment()`；空的共享段。"""

    def segment(self, segment_id):
        return SimpleNamespace(project_id=None, system_id=None, diagram_id=None, messages=())


class _Facade:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def search(self, principal, query, kinds=None, limit=None):
        self.calls += 1
        raise self.error


def _never(*_args):
    raise AssertionError("記憶被拒絕時不得建立模型 client 或呼叫模型")


def _router(facade, observations):
    return IntentRouter(
        memory_facade=facade,
        config=RoutingConfig(
            model="stub", timeout_seconds=5.0, max_calls_per_turn=1, max_retries=0, confidence_threshold=0.7
        ),
        model_factory=_never,
        graph_builder=_never,
        observer=observations.append,
    )


class MemoryForbiddenIsNotDegradedTest(unittest.TestCase):
    """`MemoryForbidden` 是**權限判定**，不是依賴不可用：不降級、原樣向上（使用者裁決：本輪以授權錯誤結束）。"""

    def test_a_memory_authorization_denial_ends_the_turn_before_any_model_call(self):
        """
        @purpose 記憶授權被拒（例：待核准帳號）時，路由器不得把它當成「記憶不可用」降級後照常分類；必須原樣向上傳遞，且模型從未被呼叫。
        @given MemoryFacade 替身的 search 拋 MemoryForbidden(reason="pending")；模型 factory 一被呼叫即失敗
        @step 呼叫 fetch_routing_context | 拋 MemoryForbidden（不是回 memory_degraded=True）
        @step 呼叫 IntentRouter.classify | 拋 MemoryForbidden；觀測事件 error_kind 為 MemoryForbidden；模型 factory 未被呼叫
        @step 讀 cloud360.intent_routing 的 WARNING 日誌 | 有一筆，且不含使用者輸入原文
        @pass 三步皆成立
        @story US6.1
        """
        with self.assertRaises(MemoryForbidden):
            fetch_routing_context(
                principal=object(), session=_Session(), text=_SECRET_UTTERANCE,
                memory_facade=_Facade(MemoryForbidden(reason="pending")),
            )
        observations = []
        router = _router(_Facade(MemoryForbidden(reason="pending")), observations)
        with self.assertLogs("cloud360.intent_routing", level="WARNING") as logs:
            with self.assertRaises(MemoryForbidden):
                asyncio.run(router.classify(object(), _Session(), _SECRET_UTTERANCE, turn_id="t-1"))
        self.assertEqual([o.error_kind for o in observations], ["MemoryForbidden"])
        self.assertTrue(logs.output)
        for line in logs.output:
            self.assertNotIn("hunter2", line)
            self.assertNotIn(_SECRET_UTTERANCE, line)

    def test_any_other_memory_failure_still_degrades(self):
        """
        @purpose D-1 不變：記憶依賴的一般故障仍降級為不帶記憶繼續，且降級可被觀測。
        @given MemoryFacade 替身的 search 拋 RuntimeError
        @step 呼叫 fetch_routing_context | 不拋例外；memory_degraded 為真、memory_notes 為空
        @pass 兩項皆成立
        @story US6.1
        """
        context = fetch_routing_context(
            principal=object(), session=_Session(), text="改架構圖",
            memory_facade=_Facade(RuntimeError("pgvector down")),
        )
        self.assertTrue(context.memory_degraded)
        self.assertEqual(context.memory_notes, ())


if __name__ == "__main__":
    unittest.main()
