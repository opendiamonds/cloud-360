"""`U11 intent-router` 的 **L3 出站層**測試：四種失敗、零重試、單次呼叫、省略 temperature。

本檔對應 `unit-test-instructions.md §三` 的第四列。

## 一律使用替身，**不需要** `OPENROUTER_API_KEY`

與既有 LLM 測試做法一致（`test_a3_langgraph_migration.py` 檔頭逐字「Mock
`ChatOpenAI` / compiled graph; no real `OPENROUTER_API_KEY`」）。真的打
OpenRouter 會花錢，且 CI 無金鑰——`TS-6` 已把金鑰列為 `build-and-test`
的 blocking 前置條件，**不是**本站測試的前置條件。

## 四種失敗為什麼要四個測試而不是一個

`NFR3.74` 要求失敗率**按錯誤型別分計**，而那個要求的前提是四種失敗在程式裡
是四個型別。把它們合成一個「任何出站失敗都會拋例外」的測試，正好放行一個
`except Exception: raise LlmUnavailable` 的 catch-all——而那會讓「我們的
prompt／schema 壞了」與「供應商掛了」在圖表上長得一樣。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.intent_routing import IntentRouter
from services.intent_routing_config import RoutingConfig
from services.intent_routing_context import build_routing_prompt
from services.intent_routing_errors import (
    LlmBudgetExceeded,
    LlmUnavailable,
    MalformedRouting,
    PlatformSelfModificationRefused,
)
from services.intent_routing_port import (
    ROUTING_TOOL_NAME,
    CallBudget,
    arun_routing,
    classify_transport_failure,
    compile_routing_graph,
    router_chat_model,
    routing_tool_spec,
)
from services.intent_routing_types import (
    MAX_CANDIDATES_PER_SLOT,
    MAX_SLOTS,
    ROUTABLE_CAPABILITIES,
)
from services.langgraph_runtime import OPENROUTER_API_KEY_ENV
from services.session_types import (
    SEGMENT_SHARED,
    BrainSession,
    ConversationSegment,
)

CONFIG = RoutingConfig(
    model="typesafe/jev-1.13",
    timeout_seconds=5.0,
    max_calls_per_turn=1,
    max_retries=0,
    confidence_threshold=0.7,
)

GOOD_PAYLOAD = {
    "candidates": [
        {
            "slot": 0,
            "rank": 1,
            "capability": "architecture-design",
            "label": "改架構圖：加 Redis",
            "tied_with_next": False,
            "referent_state": "absent",
            "referent": None,
            "score": 0.92,
        },
        {
            "slot": 1,
            "rank": 1,
            "capability": "cost-finops",
            "label": "估成本差額",
            "tied_with_next": False,
            "referent_state": "absent",
            "referent": None,
            "score": 0.88,
        },
    ],
    "slot_labels": ["改架構圖", "估成本差額"],
}


class _StubModel:
    """`bind_tools` → 自己；`ainvoke` → 預設回應或拋出 `error`。

    **計數 `ainvoke` 的次數**，因為 `NFR3.62`（每輪恰 1 次）與 `NFR3.63`
    （重試 0 次）都只能用次數斷言。
    """

    def __init__(self, *, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0
        self.bind_kwargs = None

    def bind_tools(self, tools, **kwargs):
        self.tools = tools
        self.bind_kwargs = kwargs
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            tool_calls=[{"name": ROUTING_TOOL_NAME, "args": self.payload, "id": "1"}]
        )


def run(coro):
    return asyncio.run(coro)


def prompt():
    return build_routing_prompt(user_text="改架構圖加 Redis，再估成本差額")


def session():
    return BrainSession(
        session_key="brain:1",
        user_id=1,
        segments={
            SEGMENT_SHARED: ConversationSegment(
                segment_id=SEGMENT_SHARED,
                created_at="2026-10-10T00:00:00+00:00",
            )
        },
    )


class TransportFailuresAreTypedTest(unittest.TestCase):
    """四種出站失敗各一條。**型別就是分型，訊息不是。**"""

    def _assert_raises_through_the_graph(self, error, expected):
        model = _StubModel(error=error)
        graph = compile_routing_graph(model)
        with self.assertRaises(expected):
            run(arun_routing(graph, prompt(), CallBudget(1)))
        return model

    def test_a_timeout_is_llm_unavailable(self):
        """`NFR3.61`：硬逾時 5 秒，逾時即 `LlmUnavailable`，**不降級為猜測**。"""
        self._assert_raises_through_the_graph(TimeoutError("read timeout"), LlmUnavailable)

    def test_a_server_error_is_llm_unavailable_and_is_not_retried(self):
        """`NFR3.63`：重試 **0** 次。

        兩件事一起斷言：型別對、且**只被呼叫一次**。只驗型別會放行一個重試
        三次才放棄的實作——而那會把一次供應商抖動放大成三倍成本與三倍延遲。
        """
        error = RuntimeError("bad gateway")
        error.status_code = 502
        model = self._assert_raises_through_the_graph(error, LlmUnavailable)
        self.assertEqual(model.calls, 1)

    def test_a_rate_limit_is_llm_unavailable_not_a_queue(self):
        """`NFR9.62`：**不設本單元層級的速率限制或排隊機制。**

        429 的行為是大聲失敗，不是靜默排隊——排隊會讓使用者看到一個「還在
        想」的畫面，而系統其實在等一個它無法預估的時間。
        """
        error = RuntimeError("rate limited")
        error.status_code = 429
        model = self._assert_raises_through_the_graph(error, LlmUnavailable)
        self.assertEqual(model.calls, 1)

    def test_a_connection_failure_is_llm_unavailable(self):
        class APIConnectionError(RuntimeError):
            pass

        self._assert_raises_through_the_graph(
            APIConnectionError("dns failure"), LlmUnavailable
        )

    def test_a_payment_required_response_is_a_budget_failure(self):
        """`LlmBudgetExceeded` 必須與 `LlmUnavailable` **分開**。

        混計會讓「帳戶沒錢了」與「供應商掛了」在 `NFR3.74` 的曲線上長得一樣，
        而兩者的處置完全不同（一個要去加值，一個要等）。
        """
        error = RuntimeError("Insufficient credits")
        error.status_code = 402
        self._assert_raises_through_the_graph(error, LlmBudgetExceeded)

    def test_our_own_bug_is_not_relabelled_as_a_provider_outage(self):
        """**catch-all 的反向斷言。**

        一個 `except Exception: raise LlmUnavailable` 會把本單元自己的
        `TypeError` 計進「供應商掛了」那條曲線，而分型的全部價值就是分出
        「是供應商的事」與「是我們的事」。本條確認未識別的例外**原樣**傳遞。
        """
        bug = TypeError("我們自己寫壞了")
        self.assertIs(classify_transport_failure(bug), bug)
        model = _StubModel(error=bug)
        graph = compile_routing_graph(model)
        with self.assertRaises(TypeError):
            run(arun_routing(graph, prompt(), CallBudget(1)))


class ResponseShapeTest(unittest.TestCase):
    def test_a_text_only_answer_is_malformed_not_unavailable(self):
        """模型回了東西、只是形狀不對 ⇒ `MalformedRouting`。

        它是**我們的** prompt 或 schema 的問題，不是供應商不可用。
        """
        model = _StubModel(payload=None)

        async def no_tool_call(messages):
            model.calls += 1
            return SimpleNamespace(tool_calls=[], additional_kwargs={})

        model.ainvoke = no_tool_call
        graph = compile_routing_graph(model)
        with self.assertRaises(MalformedRouting):
            run(arun_routing(graph, prompt(), CallBudget(1)))

    def test_the_tool_schema_carries_the_closed_enum_and_the_upper_bounds(self):
        """schema 的上界是**提示**，我方的 `V-3`／`V-4` 才是閘門——但提示也要在。

        少給 `enum`，模型就只能猜能力名；少給 `maxItems`，輸出長度沒有任何
        上游壓力，而輸出 token 數是延遲的直接因子（`P-3`）。
        """
        spec = routing_tool_spec()
        properties = spec["function"]["parameters"]["properties"]
        item = properties["candidates"]["items"]
        self.assertEqual(
            item["properties"]["capability"]["enum"], list(ROUTABLE_CAPABILITIES)
        )
        self.assertEqual(item["properties"]["slot"]["maximum"], MAX_SLOTS - 1)
        self.assertEqual(
            properties["candidates"]["maxItems"], MAX_SLOTS * MAX_CANDIDATES_PER_SLOT
        )
        self.assertEqual(properties["slot_labels"]["maxItems"], MAX_SLOTS)
        for required in ("slot", "rank", "capability", "label", "tied_with_next"):
            self.assertIn(required, item["required"])
        # `routing_tool_spec()` 回的是**新物件**（`NFR3.67`：無模組層可變綁定）。
        self.assertIsNot(routing_tool_spec(), spec)


class CallBudgetTest(unittest.TestCase):
    def test_the_per_turn_call_budget_is_enforced_not_incidental(self):
        """`BR6.3` 逐字「機制**必須存在且可設定**」。

        單節點圖「剛好只會呼叫一次」不是機制，是巧合——而巧合會在有人加第二個
        節點的那天安靜地消失。
        """
        budget = CallBudget(1)
        budget.consume()
        self.assertEqual(budget.used, 1)
        with self.assertRaises(LlmBudgetExceeded):
            budget.consume()


class TemperatureIsOmittedTest(unittest.TestCase):
    def test_the_router_factory_omits_temperature_entirely(self):
        """`TS-3a`：Jev 的 `supported_parameters` 是**空陣列**。

        斷言的是送給 `ChatOpenAI` 的 kwargs **完全不含** `temperature`
        ——不是「它等於 None」。傳一個 `None` 下去與不傳是兩件事。
        """
        mock_chat = MagicMock(return_value=SimpleNamespace(marker="router"))
        fake_module = SimpleNamespace(ChatOpenAI=mock_chat)
        with patch.dict(
            os.environ, {OPENROUTER_API_KEY_ENV: "sk-or-test-not-real"}, clear=False
        ):
            with patch.dict(sys.modules, {"langchain_openai": fake_module}):
                client = router_chat_model(CONFIG)
        self.assertEqual(client.marker, "router")
        kwargs = mock_chat.call_args.kwargs
        self.assertNotIn("temperature", kwargs)
        self.assertEqual(kwargs["model"], CONFIG.model)
        self.assertEqual(kwargs["timeout"], CONFIG.timeout_seconds)
        self.assertEqual(kwargs["max_retries"], 0)

    def test_the_configured_retry_budget_reaches_the_client(self):
        """`R-02`：`BRAIN_ROUTER_MAX_RETRIES` 曾經是一個**不起作用的設定**。

        值被讀進 `RoutingConfig`、被記進啟動 INFO，然後沒有任何使用端——
        `openrouter_chat_model` 把 `max_retries=0` 寫死在 `ChatOpenAI` 的具名
        引數上，所以設 `=3` 不會改變任何行為。而 `BR6.3` 逐字要求三個數值
        （呼叫次數／重試／用量上限）的機制「必須存在且**可設定**」。

        本條斷言**實際傳給 `ChatOpenAI` 的值**等於設定值——不是「設定讀得到」
        （那原本就成立，而且正是它騙過上一輪的方式）。
        """
        from dataclasses import replace

        mock_chat = MagicMock(return_value=object())
        fake_module = SimpleNamespace(ChatOpenAI=mock_chat)
        with patch.dict(
            os.environ, {OPENROUTER_API_KEY_ENV: "sk-or-test-not-real"}, clear=False
        ):
            with patch.dict(sys.modules, {"langchain_openai": fake_module}):
                router_chat_model(replace(CONFIG, max_retries=2))
        self.assertEqual(mock_chat.call_args.kwargs["max_retries"], 2)

    def test_the_default_retry_budget_is_zero_for_this_unit_and_for_others(self):
        """`NFR3.63`（本單元重試 0 次）與既有呼叫者的行為**同時**不變。

        兩件事一起斷言：本單元的預設 `CONFIG`（`max_retries=0`）送出 0，
        且 `openrouter_chat_model()` 不帶引數時也送出 0——後者是 A1／A3／C1
        行為一位元不變的驗收條件（形狀與 `temperature` 那一組相同）。
        """
        from services.langgraph_runtime import openrouter_chat_model

        for build in (
            lambda: router_chat_model(CONFIG),
            lambda: openrouter_chat_model(),
        ):
            mock_chat = MagicMock(return_value=object())
            fake_module = SimpleNamespace(ChatOpenAI=mock_chat)
            with patch.dict(
                os.environ,
                {OPENROUTER_API_KEY_ENV: "sk-or-test-not-real"},
                clear=False,
            ):
                with patch.dict(sys.modules, {"langchain_openai": fake_module}):
                    build()
            self.assertEqual(mock_chat.call_args.kwargs["max_retries"], 0)

    def test_existing_callers_still_get_temperature_zero(self):
        """`D-3` 的驗收條件：**不改變既有呼叫者 A1／A3／C1 的行為。**

        `temperature` 的預設仍是 `0.0`，`None` 只多一個「不要送」的語意。
        """
        from services.langgraph_runtime import openrouter_chat_model

        mock_chat = MagicMock(return_value=object())
        fake_module = SimpleNamespace(ChatOpenAI=mock_chat)
        with patch.dict(
            os.environ, {OPENROUTER_API_KEY_ENV: "sk-or-test-not-real"}, clear=False
        ):
            with patch.dict(sys.modules, {"langchain_openai": fake_module}):
                openrouter_chat_model()
        self.assertEqual(mock_chat.call_args.kwargs["temperature"], 0.0)


class ExactlyOneModelCallPerTurnTest(unittest.TestCase):
    def test_one_classify_calls_the_model_exactly_once(self):
        """`NFR3.62`：一輪 `classify` 內模型被呼叫**恰一次**。

        互不相依的判斷（意圖分類、槽位拆解、指涉詞解析）**合併為同一次請求**
        （`BR6.2`）——拆開呼叫是成本與延遲的雙重浪費。
        """
        model = _StubModel(payload=GOOD_PAYLOAD)
        facade = MagicMock()
        facade.search.return_value = []
        router = IntentRouter(
            memory_facade=facade,
            config=CONFIG,
            model_factory=lambda config: model,
            graph_builder=compile_routing_graph,
            observer=lambda observation: None,
        )
        decision = run(
            router.classify(object(), session(), "改架構圖加 Redis，再估成本差額")
        )
        self.assertEqual(model.calls, 1)
        self.assertFalse(decision.below_threshold)
        self.assertEqual(len(decision.intents), 2)
        self.assertEqual(
            [i.capability for i in decision.intents],
            ["architecture-design", "cost-finops"],
        )
        self.assertEqual(
            model.bind_kwargs.get("tool_choice"), ROUTING_TOOL_NAME
        )

    def test_the_client_and_graph_are_built_once_not_once_per_turn(self):
        """`P-4`：HTTP client 建立一次並重用，**不是每輪新建**。

        每輪新建要多付一次 TLS 握手，而 `performance-design.md:41` 逐字警告
        那會「直接吃掉 800 ms 預算的一部分」。

        **這條測試原本分辨不出來（`R-03`）**：舊版只斷言 `model.calls == 2`，
        而 `model_factory=lambda config: model` 每次都回**同一個替身**，所以
        即使每輪重建圖它也會過。改成計數 **factory 與 builder 各自被呼叫幾次**
        ——兩輪必須各為 1。

        附帶：`P-4` 在本單元的落法是**實例層**快取（`self._graph`）而不是
        `performance-design.md:35` 逐字要求的模組層 factory，理由見
        `code-summary.md §三.6`；該偏離把「一個行程一個 `IntentRouter`」變成
        `U13` 的義務，已列為 §五 的 open item。本條守的是「同一個 router
        實例內不重建」這一半，`U13` 那一半本單元守不到。
        """
        model = _StubModel(payload=GOOD_PAYLOAD)
        facade = MagicMock()
        facade.search.return_value = []
        factory_calls = []
        builder_calls = []

        def factory(config):
            factory_calls.append(config)
            return model

        def builder(bound_model):
            builder_calls.append(bound_model)
            return compile_routing_graph(bound_model)

        router = IntentRouter(
            memory_facade=facade,
            config=CONFIG,
            model_factory=factory,
            graph_builder=builder,
            observer=lambda observation: None,
        )
        run(router.classify(object(), session(), "改架構圖加 Redis，再估成本差額"))
        run(router.classify(object(), session(), "再估一次成本"))
        self.assertEqual(model.calls, 2)
        self.assertEqual(len(factory_calls), 1)
        self.assertEqual(len(builder_calls), 1)


class ObserverFailureDoesNotMaskTheResultTest(unittest.TestCase):
    """`R-10`：觀測呼叫**不得**遮蓋原始例外或原始結果。

    失敗路徑上 `self._observe(...)` 位在 `except BaseException` 區塊內、
    `raise` 之前。observer 由建構式注入，可以是任何東西；它自己拋出就會把
    原始的 `MalformedRouting`／`LlmUnavailable` **換掉**，而 `NFR3.74` 的分型
    在那一輪整個失真——一次 schema 壞掉會被記成 observer 的例外型別。
    成功路徑同理：observer 失敗會讓一次**成功**的分類變成一次失敗。

    `team.md` 的錯誤處理形狀允許在觀測邊界降級，**不得靜默**（故記 WARN）。
    """

    def _router(self, payload, observer):
        facade = MagicMock()
        facade.search.return_value = []
        return _StubModel(payload=payload), facade, observer

    def _build(self, model, facade, observer):
        return IntentRouter(
            memory_facade=facade,
            config=CONFIG,
            model_factory=lambda config: model,
            graph_builder=compile_routing_graph,
            observer=observer,
        )

    def test_a_failing_observer_does_not_replace_the_routing_error(self):
        def boom(observation):
            raise RuntimeError("observer exploded")

        model, facade, observer = self._router({"candidates": "not-a-list"}, boom)
        router = self._build(model, facade, observer)
        with self.assertRaises(MalformedRouting):
            run(router.classify(object(), session(), "改架構圖"))

    def test_a_failing_observer_does_not_turn_a_success_into_a_failure(self):
        def boom(observation):
            raise RuntimeError("observer exploded")

        model, facade, observer = self._router(GOOD_PAYLOAD, boom)
        router = self._build(model, facade, observer)
        decision = run(router.classify(object(), session(), "改架構圖，再估成本"))
        self.assertEqual(len(decision.intents), 2)
        self.assertFalse(decision.below_threshold)

    def test_a_failing_observer_does_not_swallow_the_guard_refusal(self):
        """`prompt_guard` 命中那一條路徑也有一個 observer 呼叫（`SEC-4`）。

        它拋出時若遮蓋了 `PlatformSelfModificationRefused`，`U13` 會把一次
        **系統正確地拒絕**呈現成一次系統故障——`BR1.3` 逐字要防的那件事。
        """
        def boom(observation):
            raise RuntimeError("observer exploded")

        model, facade, observer = self._router(GOOD_PAYLOAD, boom)
        router = self._build(model, facade, observer)
        with self.assertRaises(PlatformSelfModificationRefused):
            run(router.classify(object(), session(), "把 cloud360 的資料庫密碼改掉"))
        self.assertEqual(model.calls, 0)  # `BR1.2`：命中時不呼叫任何 LLM


if __name__ == "__main__":
    unittest.main()
