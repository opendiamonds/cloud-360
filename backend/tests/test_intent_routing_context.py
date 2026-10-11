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


if __name__ == "__main__":
    unittest.main()
