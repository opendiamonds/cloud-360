"""U22 progress-channel 的行為測試（7 個）。

框架為 Python 內建 `unittest`（**不是 pytest**）；併發測試用
`IsolatedAsyncioTestCase`，前例 `backend/tests/test_langgraph_migration.py`。

**關鍵紀律（BR5.2）**：交錯順序一律以 `asyncio.Event` barrier 釘住，**不得以
`sleep` 製造**。品質 agent 已實測 `sleep` 版本會通過（假綠燈），而
`frontend/playwright.config.ts` 的 `retries` 與 `ui-regression` 都容忍 flaky
——一個 flaky 的併發測試等於沒有測試。
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage

from tests.helpers import backend_dir  # noqa: F401 — ensures path + psycopg stub

from services import design_agent
from services.progress_channel import (
    DROPPABLE_EVENT_TYPES,
    MAX_BUFFERED_EVENTS,
    DuplicateChannelKey,
    # 整合測試必須用**模組單例**而非自建 registry：design_agent 用的是這一個。
    ProgressChannel,
    ProgressChannelRegistry,
    ProgressEvent,
)


class ProgressChannelBehaviourTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # 每個測試用自己的 registry 實例而不是模組單例：測試之間不得經由共享
        # 狀態互相影響，而本單元存在的全部理由就是共享狀態會出事。
        self.registry = ProgressChannelRegistry()

    async def _collect(self, key: str) -> list[tuple[str, str]]:
        return [(e.type, e.content) async for e in self.registry.drain(key)]

    async def test_two_overlapping_requests_get_disjoint_and_nonempty_event_sets(self):
        """
        @purpose 兩個重疊請求的進度事件必須互斥**且各自非空**。現狀下 A 的集合是
                 空的而 B 收到 A 的產出，所以「互斥」在壞碼上真空成立——只斷言
                 互斥的測試會通過。非空那一半是這個案例的實質內容。
        @given 兩個併發的請求 A 與 B，各自 open 自己的鍵
        @step A 的工具寫入一則 progress 後停在 barrier | A 的事件在 A 的通道內
        @step B 在 A 停住時 open 並寫入自己的 progress 與 xml | B 的事件在 B 的通道內
        @step 放開 barrier，A 再寫入自己的 xml | 不影響 B
        @step 兩邊各自 drain | 兩個集合互斥，且各自非空
        @pass A 只拿到 A 寫的、B 只拿到 B 寫的，兩者皆非空集合
        @story US13.1
        @note 交錯順序以 asyncio.Event 釘住，不用 sleep（BR5.2）。
        """
        key_a, key_b = "key-A", "key-B"
        b_has_published = asyncio.Event()
        a_reached_barrier = asyncio.Event()

        async def request_a():
            self.registry.open(key_a)
            await self.registry.publish(key_a, ProgressEvent("progress", "A-1"))
            a_reached_barrier.set()
            await b_has_published.wait()  # 讓 B 的整段寫入夾在 A 的兩次寫入中間
            await self.registry.publish(key_a, ProgressEvent("xml", "<A-xml/>"))
            return await self._collect(key_a)

        async def request_b():
            await a_reached_barrier.wait()
            self.registry.open(key_b)
            await self.registry.publish(key_b, ProgressEvent("progress", "B-1"))
            await self.registry.publish(key_b, ProgressEvent("xml", "<B-xml/>"))
            b_has_published.set()
            return await self._collect(key_b)

        events_a, events_b = await asyncio.gather(request_a(), request_b())

        self.assertTrue(events_a, "A 的事件集合為空——互斥會真空成立，這就是壞碼的症狀")
        self.assertTrue(events_b, "B 的事件集合為空")
        self.assertEqual(events_a, [("progress", "A-1"), ("xml", "<A-xml/>")])
        self.assertEqual(events_b, [("progress", "B-1"), ("xml", "<B-xml/>")])
        self.assertEqual(
            set(events_a) & set(events_b), set(), "兩個請求的事件集合必須互斥"
        )

    async def test_the_other_request_still_receives_its_events_after_one_closes(self):
        """
        @purpose 先結束的請求不得使另一個還在跑的請求失去自己的通道。現狀是
                 另一個請求**崩潰**（對 None 呼叫 get_nowait 拋 AttributeError），
                 不是「事件被靜默丟棄」。所以斷言的是「A 仍收到自己的事件」
                 ——那是可失敗的；斷言「沒有事件被靜默丟棄」在修前修後都會過。
        @given A 與 B 重疊，B 先 close
        @step B close 自己的鍵 | 只移除 B 的那一筆
        @step A 的工具其後 publish | 寫進 A 的通道，不拋例外
        @step A drain | 仍取得自己全部的事件
        @pass A 取得 close 之後寫入的事件，且全程無例外
        @story US13.1
        """
        key_a, key_b = "key-A", "key-B"
        self.registry.open(key_a)
        self.registry.open(key_b)
        await self.registry.publish(key_a, ProgressEvent("progress", "A-before"))

        self.registry.close(key_b)  # B 先結束

        await self.registry.publish(key_a, ProgressEvent("xml", "<A-after/>"))
        events_a = await self._collect(key_a)

        self.assertEqual(
            events_a, [("progress", "A-before"), ("xml", "<A-after/>")]
        )

    async def test_drain_on_a_missing_key_returns_an_empty_iterator(self):
        """
        @purpose drain 一個不存在的鍵必須回空迭代器而非崩潰，且**已關閉與從未
                 存在在對外行為上不可區分**——可區分的話呼叫端就能探知某個鍵
                 曾經存在，而鍵的不可猜性是這條通道唯一的可見性機制。
        @given 一個從未 open 的鍵，以及一個 open 後 close 且仍有未取事件的鍵
        @step drain 從未存在的鍵 | 回空列表，不拋例外
        @step drain 已關閉的鍵 | 同樣回空列表
        @pass 兩者皆為空且行為相同
        @story US13.1
        """
        never = await self._collect("never-existed")
        self.assertEqual(never, [])

        self.registry.open("was-open")
        await self.registry.publish("was-open", ProgressEvent("progress", "x"))
        self.registry.close("was-open")
        closed = await self._collect("was-open")

        self.assertEqual(closed, [])
        self.assertEqual(closed, never, "已關閉與從未存在必須不可區分")

    async def test_open_on_an_existing_key_raises_duplicate_channel_key(self):
        """
        @purpose 同鍵重複 open 必須拋 DuplicateChannelKey 且**不覆寫**既有通道。
                 靜默覆寫會讓前一個請求已寫入但還沒被讀走的事件憑空消失，而那
                 比錯送更難察覺：使用者只是少收到東西，沒有任何錯誤。
        @given 一個已 open 且已寫入一則事件的鍵
        @step 以同一個鍵再 open | 拋 DuplicateChannelKey
        @step 例外的 key 屬性 | 等於該鍵
        @step 例外訊息 | 不含鍵本身（鍵是可見性機制，不應出現在可被轉述的字串裡）
        @step drain 原鍵 | 原本寫入的事件仍在（證明沒有被換成一個新的空通道）
        @pass 例外被拋出且原通道的事件完好
        @story US13.1
        """
        self.registry.open("dup")
        await self.registry.publish("dup", ProgressEvent("xml", "<original/>"))

        with self.assertRaises(DuplicateChannelKey) as ctx:
            self.registry.open("dup")
        self.assertEqual(ctx.exception.key, "dup")
        self.assertNotIn("dup", str(ctx.exception))

        self.assertEqual(await self._collect("dup"), [("xml", "<original/>")])

    async def test_close_is_idempotent(self):
        """
        @purpose close 必須冪等。非冪等會使 BR2.1 的 finally 在「正常路徑已關閉
                 ＋ 異常路徑再關一次」時拋出第二個例外，覆蓋掉原始失敗原因。
        @given 一個已 open 的鍵與一個從未存在的鍵
        @step close 已存在的鍵兩次 | 兩次皆不拋例外
        @step close 從未存在的鍵 | 不拋例外
        @pass 三次呼叫全部視為成功
        @story US13.1
        """
        self.registry.open("idem")
        self.registry.close("idem")
        self.registry.close("idem")  # 第二次
        self.registry.close("never-opened")

    async def test_an_abandoned_request_leaves_no_key_behind(self):
        """
        @purpose 被中途放棄的請求結束後鍵不得殘留。殘留即把跨使用者錯送換成
                 無上界的記憶體成長，只是走異常路徑。**本案例必須存在而不能
                 以推論代替**：「Starlette 斷線時會關閉 generator 所以 finally
                 會跑」是推論不是證據——若 generator 是被 GC 而非顯式 aclose，
                 finally 的執行時機不保證。
        @given 一個把 open/close 包在 try/finally 內的回應 generator
        @step 迭代它一次後 aclose（模擬客戶端斷線）| generator 的 finally 執行
        @step 檢查 registry | 不含該鍵
        @pass 鍵已消失，且被放棄前已產生的事件不再可取得
        @story US13.1
        """
        key = "abandoned"
        registry = self.registry

        async def response_generator():
            registry.open(key)
            try:
                await registry.publish(key, ProgressEvent("progress", "first"))
                async for event in registry.drain(key):
                    yield event
                # 客戶端會在這裡斷線——下面這行永遠不會被執行到
                await registry.publish(key, ProgressEvent("xml", "<never/>"))
            finally:
                registry.close(key)

        gen = response_generator()
        first = await anext(gen)
        self.assertEqual(first.content, "first")
        self.assertIn(key, registry._channels, "斷線前鍵應該還在，否則本案例驗不到東西")

        await gen.aclose()  # 模擬客戶端斷線

        self.assertNotIn(key, registry._channels, "被放棄的請求留下了鍵")
        self.assertEqual(await self._collect(key), [])

    async def test_capacity_pressure_drops_oldest_progress_but_never_xml_or_error(self):
        """
        @purpose buffer 滿載時丟棄最舊的 progress；xml 與 error **永不丟棄**。
                 丟 xml 會讓使用者看到一次「成功但沒有圖」的產圖；丟 error 會讓
                 一次失敗變成無聲無息。兩者都比丟掉一則進度訊息嚴重得多。
                 且任何丟棄都必須留下 WARN 痕跡（無聲丟棄使「使用者說少看到
                 東西」這類回報無法被查證）。
        @given 一個鍵，先寫入一則 xml 再把 buffer 填到上界
        @step 填滿後再寫一則 progress | 最舊的 progress 被丟棄，WARN log 出現
        @step 檢查 xml 是否還在 | 仍在（它不可丟棄）
        @step 寫入 error 與另一則 xml | 兩者皆寫入，buffer 暫時超過上界
        @step 把 buffer 填成全部不可丟棄後再寫 progress | 拒絕寫入新的 progress，WARN log 出現
        @pass xml 與 error 一則都沒少，被丟的只有 progress，且每次都有 WARN
        @story US13.1
        @note 可丟棄集合只有 progress（DROPPABLE_EVENT_TYPES），所以 message 與
              xml／error 同樣永不丟棄。
        """
        key = "cap"
        self.registry.open(key)
        self.assertEqual(DROPPABLE_EVENT_TYPES, frozenset({"progress"}))

        # 第一則是 xml，其後填滿 progress 到上界
        await self.registry.publish(key, ProgressEvent("xml", "<keep-me/>"))
        for i in range(MAX_BUFFERED_EVENTS - 1):
            await self.registry.publish(key, ProgressEvent("progress", f"p{i}"))
        channel = self.registry._channels[key]
        self.assertEqual(len(channel.buffer), MAX_BUFFERED_EVENTS)

        # 滿載後再寫一則 progress → 丟最舊的 progress（不是最舊的事件，那是 xml）
        with self.assertLogs("cloud360.progress_channel", level="WARNING") as logs:
            await self.registry.publish(key, ProgressEvent("progress", "newest"))
        self.assertTrue(any("丟棄" in line for line in logs.output))
        self.assertTrue(
            all("p0" not in line and "keep-me" not in line for line in logs.output),
            "WARN log 不得含事件的 content（SEC-3：xml 的 content 是使用者的架構圖）",
        )

        contents = [e.content for e in channel.buffer]
        self.assertIn("<keep-me/>", contents, "xml 被丟棄了")
        self.assertNotIn("p0", contents, "最舊的 progress 應該被丟棄")
        self.assertIn("newest", contents)

        # 滿載時的 xml／error 一律寫入，buffer 可暫時超過上界
        before = len(channel.buffer)
        await self.registry.publish(key, ProgressEvent("error", "boom"))
        await self.registry.publish(key, ProgressEvent("xml", "<second/>"))
        self.assertEqual(len(channel.buffer), before + 2)
        self.assertGreater(len(channel.buffer), MAX_BUFFERED_EVENTS)

        # buffer 全為不可丟棄時，拒絕寫入新的 progress 而不犧牲任何 xml／error
        channel.buffer.clear()
        for i in range(MAX_BUFFERED_EVENTS):
            await self.registry.publish(key, ProgressEvent("error", f"e{i}"))
        with self.assertLogs("cloud360.progress_channel", level="WARNING") as logs:
            await self.registry.publish(key, ProgressEvent("progress", "refused"))
        self.assertTrue(any("拒絕寫入" in line for line in logs.output))
        remaining = [e.type for e in channel.buffer]
        self.assertEqual(
            remaining, ["error"] * MAX_BUFFERED_EVENTS, "沒有 error 應該被丟棄或擠掉"
        )


class RunDesignAgentIsolationIntegrationTest(unittest.IsolatedAsyncioTestCase):
    """`run_design_agent` ↔ 工具 ↔ ProgressChannel 的整合邊界。

    **本測試是已核可的 12 個測試之外的新增，理由如下。** 那 12 個裡 7 個直接
    對 registry 操作、5 個讀原始碼文字，**沒有一個走真實的呼叫路徑**：
    `run_design_agent` 把鍵放進 LangGraph 的 `config["configurable"]`，工具以
    注入的 `RunnableConfig` 把它讀回來。那段接線斷掉的話——例如有人拿掉工具
    簽章上的 `config` 參數、或拿掉 config dict 裡的那個欄位——12 個測試**全部
    仍然綠**：library 的行為沒變、原始碼文字的 grep 也沒變。而生產環境的症狀
    是每一則事件都走 BR3.2 被記 ERROR 丟棄，畫面上只是沒有進度訊息，使用者
    看不到任何錯誤。那正是本單元存在要消滅的那一類安靜失敗。

    Testing Contract 的 `standard` 策略逐字要求「Unit tests plus integration
    tests for key boundaries」，而這就是那個 key boundary。突變 M7 驗證它不是
    恆真（見 code-summary.md）。
    """

    #: barrier 的逾時。正常路徑約 0.05 秒；10 秒純粹是為了讓「接線斷掉」這個
    #: 失敗模式變成一句清楚的 assertion 而不是一個卡住的 job。
    BARRIER_TIMEOUT_SECONDS = 10

    async def _await_barrier(self, event: asyncio.Event, what: str) -> None:
        try:
            await asyncio.wait_for(event.wait(), timeout=self.BARRIER_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            self.fail(
                f"等待「{what}」逾時（{self.BARRIER_TIMEOUT_SECONDS} 秒）。"
                "最可能的原因是 run_design_agent 一則 xml 事件都沒產出，"
                "也就是進度鍵的接線斷了——工具簽章上的 config 注入、或 "
                "run_design_agent 放進 config[\"configurable\"] 的那個欄位。"
            )

    @staticmethod
    def _fake_llm(provider: str):
        """第一次呼叫要求產圖，第二次回文字——驅動 graph 走完 agent→tools→agent。"""
        calls = {"n": 0}

        class FakeLLM:
            def bind_tools(self, tools):
                return self

            async def ainvoke(self, messages):
                calls["n"] += 1
                if calls["n"] == 1:
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "draw_architecture_diagram",
                                "id": "call-1",
                                "args": {
                                    "provider": provider,
                                    "groups": [],
                                    "nodes": [],
                                    "edges": [],
                                },
                            }
                        ],
                    )
                return AIMessage(content=f"{provider} 完成")

        return FakeLLM()

    @staticmethod
    async def _fake_build_mxgraph_xml(
        groups, nodes, edges, on_progress=None, provider=None
    ):
        """替掉佈局引擎，但**不碰工具本體**——工具的取鍵與 publish 走真實程式。"""
        if on_progress:
            await on_progress(f"{provider}-icon")
        return f"<{provider}-xml/>"

    async def _run(self, provider: str, request_key: str, *, hold=None, signal=None):
        collected: list[tuple[str, str]] = []
        with patch(
            "services.design_agent.ChatAnthropic",
            side_effect=lambda **kwargs: self._fake_llm(provider),
        ), patch("services.design_agent.configure_provider_env"), patch(
            "services.design_agent.llm_auth_ready", return_value=True
        ), patch(
            "services.design_agent.get_design_model_name", return_value="fake-model"
        ), patch(
            "services.design_agent.build_system_prompt", return_value="sys"
        ), patch(
            "services.design_agent.format_user_prompt", return_value="usr"
        ), patch(
            "services.design_agent.build_mxgraph_xml", self._fake_build_mxgraph_xml
        ):
            ProgressChannel.open(request_key)
            try:
                async for event in design_agent.run_design_agent(
                    [{"role": "user", "content": "畫一張圖"}],
                    thread_id=f"thread-{provider}",
                    request_key=request_key,
                ):
                    collected.append((event["type"], event["content"]))
                    if signal is not None and event["type"] == "xml":
                        # 把 B 的整段執行夾在 A 收到 xml 之後、結束之前
                        signal.set()
                        await self._await_barrier(hold, "另一個請求跑完")
            finally:
                ProgressChannel.close(request_key)
        return collected

    async def test_two_overlapping_run_design_agent_calls_keep_their_own_events(self):
        """
        @purpose 經**真實呼叫路徑**（run_design_agent → LangGraph config → 工具
                 → ProgressChannel → drain）的兩個重疊請求，事件必須各回各家。
                 這條路徑是本單元主要失敗模式的所在，而斷掉時 12 個已核可測試
                 全部仍綠。
        @given 兩個併發的 run_design_agent 呼叫，各自的鍵與 thread_id 皆不同，
               LLM 與佈局引擎為替身（前例 test_langgraph_migration.py，不需新 seam）
        @step A 跑到收到自己的 xml 後停在 barrier | A 已收到自己的進度與 xml
        @step B 在 A 停住時整段跑完 | B 收到自己的進度與 xml
        @step 放開 barrier 讓 A 結束 | A 的事件未被 B 汙染
        @step 比對兩邊 provider 專屬的內容 | A 只含 A 的、B 只含 B 的
        @step 檢查 registry | 兩個鍵都已被 finally 清掉
        @pass 兩邊皆非空、provider 專屬內容完全分離、結束後無殘留鍵
        @story US13.1
        @note 交錯以 asyncio.Event 釘住，不用 sleep（BR5.2）。斷言用的是
              **provider 專屬**的內容而非整個集合的交集——兩個請求都會發出
              逐字相同的開場訊息「🧠 正在規劃進階架構拓樸...」，那是兩條獨立
              通道各自產生的同一個字串，不是錯送。拿整體交集當斷言會把它誤判
              成跨請求汙染。
        """
        a_at_barrier = asyncio.Event()
        b_finished = asyncio.Event()

        async def task_b():
            await self._await_barrier(a_at_barrier, "A 收到自己的 xml 事件")
            out = await self._run("BBB", "integ-key-B")
            b_finished.set()
            return out

        events_a, events_b = await asyncio.gather(
            self._run("AAA", "integ-key-A", hold=b_finished, signal=a_at_barrier),
            task_b(),
        )

        self.assertTrue(events_a, "A 的事件集合為空——接線斷掉時正是這個症狀")
        self.assertTrue(events_b, "B 的事件集合為空")

        contents_a = {content for _, content in events_a}
        contents_b = {content for _, content in events_b}

        self.assertIn("<AAA-xml/>", contents_a)
        self.assertIn("<BBB-xml/>", contents_b)
        self.assertNotIn("<BBB-xml/>", contents_a, "A 收到了 B 的架構圖 XML")
        self.assertNotIn("<AAA-xml/>", contents_b, "B 收到了 A 的架構圖 XML")
        self.assertIn("AAA-icon", contents_a)
        self.assertNotIn("BBB-icon", contents_a, "A 收到了 B 的進度訊息")
        self.assertIn("BBB-icon", contents_b)
        self.assertNotIn("AAA-icon", contents_b, "B 收到了 A 的進度訊息")

        self.assertNotIn("integ-key-A", ProgressChannel._channels)
        self.assertNotIn("integ-key-B", ProgressChannel._channels)


if __name__ == "__main__":
    unittest.main()
