"""`U13 brain-gateway` 記憶預取、熔斷與 episodic 寫入的測試（`BR67.7`／`BR67.10`／`BR67.12`；`NFR13.3`、`NFR13.5`、
`NFR13.24`、`NFR13.25`；帶入項 5、8、15、18、19、22）。

**替身限制（揭露）**：嵌入替身拋**實際**例外型別 `EmbeddingProviderUnavailable`（以 `raise … from httpx.ReadTimeout`
構造），但不經真 httpx 與 Ollama；另一支契約測試以真實 `OllamaAdapter` 的包裝方式（patch `httpx.Client.post`，不連網）
鎖住例外鏈形狀（`OPEN-GW13-20`）。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import asyncio
import logging
import threading
import time
import unittest
from unittest import mock

import httpx
from starlette.testclient import TestClient

from services import brain_gateway as G
from services import brain_gateway_rules as R
from services import intent_routing
from services.embedding_port import (
    DEFAULT_OLLAMA_EMBED_MODEL,
    PROVIDER_OLLAMA,
    EmbeddingProviderUnavailable,
    OllamaAdapter,
    ProviderSelection,
)
from tests.brain_gateway_fakes import (
    WS_PATH,
    FakeTiming,
    Harness,
    decision,
    hello,
    memory_hit,
    protocols,
    read_turn,
    types_of,
    user_message,
)


def _wrapped_timeout() -> EmbeddingProviderUnavailable:
    try:
        try:
            raise httpx.ReadTimeout("slow")
        except httpx.ReadTimeout as inner:
            raise EmbeddingProviderUnavailable("ollama", detail="timeout") from inner
    except EmbeddingProviderUnavailable as exc:
        return exc


class PrefetchIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()

    def _turns(self, *utterances):
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                hello(ws)
                out = []
                for u in utterances:
                    user_message(ws, u)
                    out.append(read_turn(ws))
                return out

    def test_prefetch_reaches_u11_through_contextvar_on_memory_threads(self):
        """
        @purpose 記憶檢索在分類之前於專用執行器上預取，經 ContextVar 交給 U11 的轉接器；轉接器本身無 I/O，
                 且預取與寫入都在 brain-memory 執行緒上（不佔共用執行緒池）。
        @given 記憶替身回兩筆（semantic、procedure）
        @step 送一句 | 分類器經轉接器取到 2 筆；預取 kinds 為 (semantic, procedure)、limit 5
        @step 檢視記憶呼叫的執行緒名 | 皆以 brain-memory 開頭
        @step 在 ContextVar 之外直接呼叫轉接器 | 拋例外（不做 I/O）
        @pass 預取交接正確且隔離
        @story US4.1
        """
        self.h.memory.search_behaviour = [memory_hit("semantic"), memory_hit("procedure")]
        self._turns("畫一張架構圖")
        self.assertEqual(self.h.router_script.memory_seen, [("hits", 2)])
        call = self.h.memory.search_calls[0]
        self.assertEqual((call.kinds, call.limit), (("semantic", "procedure"), 5))
        deadline = time.time() + 2
        while len(self.h.memory.threads) < 2 and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(all(name.startswith("brain-memory") for name in self.h.memory.threads))
        with self.assertRaises(G.PrefetchUnavailable):
            self.h.adapter.search(object(), "x", kinds=("semantic",), limit=5)

    def test_prefetch_contract_matches_u11(self):
        """
        @purpose 預取的 kinds 與 limit 必須與 U11 實際取用的值一致；不一致時轉接器會因 kinds 不是子集而拋出，記憶永遠用不上。
        @given 兩個模組常數
        @step 比對 | 相等
        @pass 契約一致
        @story US4.1
        """
        self.assertEqual(G.PREFETCH_KINDS, intent_routing._REFERENT_MEMORY_KINDS)
        self.assertEqual(G.PREFETCH_LIMIT, intent_routing._MEMORY_SEARCH_LIMIT)

    def test_breaker_opens_on_wrapped_timeout_only_and_recovers(self):
        """
        @purpose 熔斷只在逾時／連線類（含被 EmbeddingProviderUnavailable 包住的 httpx 例外）開啟；開啟期間不預取、U11 降級；
                 30 秒後再試、成功即關閉。非暫時性錯誤不開熔斷。
        @given 第一句的預取拋 ValueError、第二句拋包住 ReadTimeout 的 EmbeddingProviderUnavailable、其後成功
        @step 送第一、二、三句 | 預取次數依序 1、2、2（第三句熔斷開啟不預取），三句皆 done
        @step 推進 30 秒後送第四句 | 預取次數 3，熔斷關閉
        @pass 開啟條件與恢復皆正確
        @story US4.1
        """
        behaviours = [ValueError("bad"), _wrapped_timeout(), [], []]

        def search(principal, query):
            b = behaviours.pop(0)
            if isinstance(b, BaseException):
                raise b
            return b

        self.h.memory.search_behaviour = search
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                hello(ws)
                counts = []
                for u in ("一", "二", "三"):
                    user_message(ws, u)
                    self.assertEqual(types_of(read_turn(ws))[-1], "done")
                    counts.append(len(self.h.memory.search_calls))
                self.assertEqual(counts, [1, 2, 2])
                self.assertIsNotNone(self.h.gw.memory.breaker.open_until)
                self.h.timing.advance(30)
                user_message(ws, "四")
                read_turn(ws)
        self.assertEqual(len(self.h.memory.search_calls), 3)
        self.assertIsNone(self.h.gw.memory.breaker.open_until)
        self.assertEqual(self.h.router_script.memory_seen[2][0], "degraded")

    def test_prefetch_wait_limit_degrades_classification_without_waiting(self):
        """
        @purpose 預取等待上限一到（NFR13.3 ②），分類照常進行、轉接器拋出而 U11 降級為不帶記憶；逾時屬暫時性，熔斷開啟。
        @given 注入時鐘令下一次預取等待（PREFETCH_WAIT_SEC）立即逾時
        @step 送一句 | done；U11 經轉接器得到的是降級（PrefetchUnavailable）
        @step 檢視熔斷 | 已開啟
        @pass 逾時不拖住分類且觸發熔斷
        @story US4.1
        """
        self.h.timing.expire_once[G.PREFETCH_WAIT_SEC] = 1
        turns = self._turns("畫一張架構圖")
        self.assertEqual(types_of(turns[0])[-1], "done")
        self.assertEqual(self.h.router_script.memory_seen, [("degraded", "PrefetchUnavailable")])
        self.assertIsNotNone(self.h.gw.memory.breaker.open_until)

    def test_episodic_only_after_dispatched_done_and_failure_only_warns(self):
        """
        @purpose episodic 只在「以 done 結束、非攔截、有交辦」的輪次於 done 之後背景寫入；寫入失敗只記 WARNING（只含例外類別名），
                 不影響該輪與後續。
        @given 第一句一般交辦；第二句攔截命中；第三句交辦但寫入拋例外
        @step 送三句 | 三句皆以 done 結束
        @step 檢視寫入 | 恰 2 次（第一、三句）；第一次內容以「使用者：」起首
        @step 檢視 log | 恰一筆 episodic_write_failed，含 RuntimeError、不含使用者文字
        @pass 寫入範圍與失敗處置皆正確
        @story US4.1
        """
        calls = {"n": 0}

        def write(principal, kind):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("db down 秘密")
            return None

        self.h.memory.write_behaviour = write
        with self.assertLogs("cloud360.brain_gateway", level="WARNING") as logs:
            turns = self._turns("畫一張架構圖", "把 cloud360 的資料庫密碼改掉", "第三句需求")
            deadline = time.time() + 2
            while len(self.h.memory.write_calls) < 2 and time.time() < deadline:
                time.sleep(0.02)
            time.sleep(0.1)
        self.assertEqual([types_of(t)[-1] for t in turns], ["done", "done", "done"])
        self.assertEqual(len(self.h.memory.write_calls), 2)
        self.assertTrue(self.h.memory.write_calls[0].content.startswith("使用者：畫一張架構圖"))
        failed = [r for r in logs.output if "episodic_write_failed" in r]
        self.assertEqual(len(failed), 1)
        self.assertIn("RuntimeError", failed[0])
        self.assertNotIn("第三句", failed[0])
        self.assertNotIn("秘密", failed[0])


class MemoryWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.timing = FakeTiming()
        self.worker = G.MemoryWorker(self.timing.timing())

    async def asyncTearDown(self):
        self.worker.shutdown()

    async def test_busy_skip_does_not_open_breaker_and_timed_out_jobs_keep_their_slot(self):
        """
        @purpose 在途上限以實際執行緒完成計數：wait_for 已逾時、但執行緒仍在跑的工作仍佔位；滿時新工作立即 BUSY_SKIPPED，且不開熔斷（NFR13.5、帶入項 15）。
        @given 真時鐘的 MemoryWorker；4 個阻塞工作佔滿執行器，其中 2 個以 0.05 秒等待上限逾時（執行緒仍在跑）
        @step 兩件逾時回 FAILED 後，重設熔斷以隔離「位子計數」這件事 | 熔斷關閉
        @step 送第 5 件 | 立即 BUSY_SKIPPED，熔斷仍關閉
        @step 放行阻塞工作後送第 6 件 | OK
        @pass 位子在執行緒結束時才歸還
        @story US4.1
        """
        worker = G.MemoryWorker(G.GatewayTiming())
        try:
            gate, started = threading.Event(), []

            def blocker():
                started.append(1)
                gate.wait(5)
                return "late"

            short = [asyncio.ensure_future(worker.run(blocker, wait_sec=0.05)) for _ in range(2)]
            long = [asyncio.ensure_future(worker.run(blocker, wait_sec=5)) for _ in range(2)]
            self.assertEqual([r.outcome for r in await asyncio.gather(*short)], [G.Outcome.FAILED] * 2)
            self.assertEqual(len(started), 4)
            worker.breaker = R.BreakerState()
            result = await worker.run(lambda: "x", wait_sec=5)
            self.assertIs(result.outcome, G.Outcome.BUSY_SKIPPED)
            self.assertIsNone(worker.breaker.open_until)
            gate.set()
            await asyncio.gather(*long)
            for _ in range(50):
                if (await worker.run(lambda: "ok", wait_sec=5)).outcome is G.Outcome.OK:
                    break
                await asyncio.sleep(0.02)
            else:
                self.fail("位子未歸還")
        finally:
            worker.shutdown()

    async def test_slot_is_returned_when_wait_expires_before_job_starts(self):
        """
        @purpose 等待上限在工作開始前就到（執行器的 future 被成功取消、工作永遠不跑）時，位子仍必須歸還，否則永久洩漏。
        @given 注入時鐘令接下來 4 次等待立即逾時
        @step 連送 4 件 | 皆 FAILED
        @step 再送 4 件（不逾時） | 皆 OK（位子沒有洩漏）
        @pass 位子全數歸還
        @story US4.1
        """
        self.timing.expire_once[3.0] = 4
        for _ in range(4):
            self.worker.breaker = R.BreakerState()  # 每件都經過等待（不被熔斷擋下）
            self.assertIs((await self.worker.run(lambda: "x", wait_sec=3.0)).outcome, G.Outcome.FAILED)
        self.worker.breaker = R.BreakerState()
        results = [await self.worker.run(lambda: "ok", wait_sec=3.0) for _ in range(4)]
        self.assertEqual({r.outcome for r in results}, {G.Outcome.OK})

    async def test_half_open_probe_skipped_when_busy_is_released_and_breaker_recovers(self):
        """
        @purpose 半開探測者若因執行器滿而 BUSY_SKIPPED，必須清除 probing；否則熔斷永久開啟、全體記憶停擺且無告警（帶入項 18，Critical）。
        @given 一次逾時使熔斷開啟；4 個阻塞工作佔滿執行器
        @step 推進 30 秒、送一件 | BUSY_SKIPPED，且 probing 為假
        @step 放行阻塞工作、送下一件（成功） | 成為探測者並成功，熔斷關閉
        @pass 熔斷可恢復
        @story US4.1
        """
        self.assertIs((await self.worker.run(self._raise(_wrapped_timeout()), wait_sec=3.0)).outcome, G.Outcome.FAILED)
        self.assertIsNotNone(self.worker.breaker.open_until)
        self.timing.advance(30)
        gate, tasks = await self._occupy_bypassing_breaker(4)
        result = await self.worker.run(lambda: "x", wait_sec=3.0)
        self.assertIs(result.outcome, G.Outcome.BUSY_SKIPPED)
        self.assertFalse(self.worker.breaker.probing)
        gate.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.05)
        self.assertIs((await self.worker.run(lambda: "ok", wait_sec=3.0)).outcome, G.Outcome.OK)
        self.assertIsNone(self.worker.breaker.open_until)

    async def _occupy_bypassing_breaker(self, n):
        """直接佔用執行器的位子（不經熔斷判定），模擬「開啟前已在跑、仍卡住」的嵌入呼叫。"""
        gate = threading.Event()
        started = []
        slots = self.worker._slots

        def blocker():
            try:
                started.append(1)
                gate.wait(5)
            finally:
                slots.release()

        loop = asyncio.get_running_loop()
        futures = []
        for _ in range(n):
            self.assertTrue(slots.acquire(blocking=False))
            futures.append(loop.run_in_executor(self.worker._executor, blocker))
        while len(started) < n:
            await asyncio.sleep(0.01)
        return gate, futures

    @staticmethod
    def _raise(exc):
        def fn():
            raise exc

        return fn

    async def test_cancellation_is_reraised_and_probe_cleared(self):
        """
        @purpose 取消（行程關閉、連線收尾）一律重拋，不得被轉成記憶失敗吞掉；探測者身分同時清除（帶入項 19）。
        @given 熔斷半開，一件阻塞工作正在探測
        @step 取消等待它的 task | CancelledError 傳到呼叫端
        @step 檢視熔斷 | probing 為假、open_until 未被改動為關閉
        @pass 取消語意正確
        @story US4.1
        """
        await self.worker.run(self._raise(TimeoutError()), wait_sec=3.0)
        self.timing.advance(30)
        gate = threading.Event()
        task = asyncio.ensure_future(self.worker.run(lambda: gate.wait(5), wait_sec=3.0))
        await asyncio.sleep(0.05)
        self.assertTrue(self.worker.breaker.probing)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.worker.breaker.probing)
        gate.set()

    async def test_executors_are_per_instance(self):
        """
        @purpose 執行器與號誌是實例屬性：關閉一個閘道的執行器不得影響另一個（帶入項 22）。
        @given 兩個 MemoryWorker
        @step 關閉第一個後以第二個執行工作 | OK
        @step 以第一個執行工作 | FAILED（RuntimeError），位子仍歸還
        @pass 互不影響
        @story US4.1
        """
        other = G.MemoryWorker(self.timing.timing())
        try:
            self.worker.shutdown()
            self.assertIs((await other.run(lambda: 1, wait_sec=3.0)).outcome, G.Outcome.OK)
            failed = await self.worker.run(lambda: 1, wait_sec=3.0)
            self.assertIs(failed.outcome, G.Outcome.FAILED)
            self.assertTrue(self.worker._slots.acquire(blocking=False))
        finally:
            other.shutdown()

    async def test_breaker_open_logs_one_warning_and_close_one_info(self):
        """
        @purpose 熔斷開啟記一筆 WARNING（含例外類別名）、關閉記一筆 INFO（含跳過次數）；期間的跳過不逐則記 WARNING（NFR13.37）。
        @given 一次逾時
        @step 開啟後 5 次 run | 皆 BREAKER_OPEN
        @step 推進 30 秒後成功一次 | 熔斷關閉
        @pass 恰 1 筆 open WARNING、1 筆 close INFO（skipped=5）
        @story US4.1
        """
        with self.assertLogs("cloud360.brain_gateway", level="INFO") as logs:
            await self.worker.run(self._raise(TimeoutError()), wait_sec=3.0)
            for _ in range(5):
                self.assertIs((await self.worker.run(lambda: 1, wait_sec=3.0)).outcome, G.Outcome.BREAKER_OPEN)
            self.timing.advance(30)
            await self.worker.run(lambda: 1, wait_sec=3.0)
        opens = [r for r in logs.records if "memory_breaker_open" in r.getMessage()]
        closes = [r for r in logs.records if "memory_breaker_close" in r.getMessage()]
        self.assertEqual((len(opens), len(closes)), (1, 1))
        self.assertEqual(opens[0].levelno, logging.WARNING)
        self.assertIn("TimeoutError", opens[0].getMessage())
        self.assertIn("skipped=5", closes[0].getMessage())


class OllamaChainContractTest(unittest.TestCase):
    def test_real_ollama_adapter_preserves_httpx_cause(self):
        """
        @purpose 熔斷判定依賴 U6 以 raise … from 保留 httpx 例外；若上游改成不帶 __cause__，熔斷將永不由嵌入逾時開啟而無測試察覺（OPEN-GW13-20）。
        @given 真實 OllamaAdapter；httpx.Client.post 被替換為拋 ReadTimeout（不連網）
        @step 呼叫 embed | 拋 EmbeddingProviderUnavailable
        @step 檢視例外鏈 | __cause__ 為 httpx.ReadTimeout，且 is_transient_memory_failure 為真
        @pass 例外鏈形狀與熔斷判定一致
        @story US4.1
        """
        port = OllamaAdapter(ProviderSelection(PROVIDER_OLLAMA, True, DEFAULT_OLLAMA_EMBED_MODEL, "http://ollama:11434"))
        with mock.patch.object(httpx.Client, "post", side_effect=httpx.ReadTimeout("slow")):
            with self.assertRaises(EmbeddingProviderUnavailable) as caught:
                port.embed(["x"])
        self.assertIsInstance(caught.exception.__cause__, httpx.ReadTimeout)
        self.assertTrue(R.is_transient_memory_failure(caught.exception))


if __name__ == "__main__":
    unittest.main()
