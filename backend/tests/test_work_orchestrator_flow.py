"""`U12 work-orchestrator` Step 8：`WorkOrchestrator` 的流程測試。

對應 `unit-test-instructions.md §三` 的 `test_work_orchestrator_flow.py` 一列（①–⑧）。
能力以 `FakeCapabilityApp`（一次回傳完整本體的 ASGI app）承接，**經真正的
`CapabilityClient` 與 `httpx.ASGITransport`**；Redis 以參考實作的替身承接；時間以
注入的 `FakeClock` 控制（不依賴第三方假時鐘工具）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import copy
import json
import logging
import threading
import time
import unittest
import uuid

from services import session_types as T
from services.intent_routing_types import Intent, IntentDecision
from services.brain_ws_contract import CostCardPayload, TokenPayload
from services.work_orchestrator import WorkItemNotFound, WorkOrchestrator
from tests.test_session_store_behaviour import FakeConnectionError
from tests.work_orchestrator_fakes import (
    SESSION_KEY,
    CostListApp,
    FacadeRecorder,
    FakeClock,
    RecordingSink,
    drain,
    fake_mint,
    fake_principal,
    make_store,
)

ARCH = "architecture-design"
REVIEW = "well-architected-review"
COST = "cost-finops"


def decision(*capabilities):
    return IntentDecision(
        intents=tuple(Intent(capability=c) for c in capabilities),
        confidence=0.9,
        below_threshold=False,
    )


def session(diagram_id=12, system_id=None, project_id=None):
    return T.BrainSession(
        session_key=SESSION_KEY,
        segments={
            "shared": T.ConversationSegment(
                segment_id="shared",
                created_at="",
                diagram_id=diagram_id,
                system_id=system_id,
                project_id=project_id,
            )
        },
    )


class Harness:
    def __init__(self, app=None, **kwargs):
        self.store, self.redis = make_store()
        self.clock = FakeClock()
        self.recorder = FacadeRecorder()
        self.app = app or CostListApp()
        self.sink = RecordingSink()
        self.orchestrator = WorkOrchestrator(
            self.app,
            self.store,
            clock=self.clock,
            sleep=self.clock.sleep,
            session_factory=self.recorder.session_factory,
            hierarchy_facade_factory=self.recorder.hierarchy_factory,
            memory_facade_factory=self.recorder.memory_factory,
            mint=fake_mint,
            user_model=object,
            **kwargs,
        )

    async def dispatch(self, *capabilities, token="tok", utterance="加上快取層", **target):
        return await self.orchestrator.dispatch(
            fake_principal(),
            session(**target) if target else session(),
            decision(*capabilities),
            utterance=utterance,
            segment_id="shared",
            turn_id="turn-1",
            bearer_token=token,
            sink=self.sink,
        )

    async def correct(self, work_item_id, token="tok"):
        return await self.orchestrator.correct(
            fake_principal(), SESSION_KEY, work_item_id, bearer_token=token, sink=self.sink
        )

    async def list_items(self, token="tok"):
        return await self.orchestrator.list_items(
            fake_principal(), SESSION_KEY, bearer_token=token, sink=self.sink
        )

    def items(self):
        return self.store.load_work_items(SESSION_KEY)

    def item(self, work_item_id):
        return self.items()[work_item_id]

    async def stop_all(self):
        for task in self.orchestrator._all_tasks():
            task.cancel()
        await asyncio.gather(*self.orchestrator._all_tasks(), return_exceptions=True)


def run(coro):
    return asyncio.run(coro)


class ReplyFirstTest(unittest.TestCase):
    def test_dispatch_replies_before_any_capability_returns(self):
        """① `NFR12.1`：能力永不返回，`dispatch` 仍在 1 秒內回傳且已送本輪建立訊息。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST /api/architecture/generate"}
            started = time.monotonic()
            created = await h.dispatch(ARCH)
            elapsed = time.monotonic() - started
            await asyncio.sleep(0)
            snapshot = (created, elapsed, list(h.sink.in_turn), h.items())
            await h.stop_all()
            return snapshot

        created, elapsed, in_turn, items = run(scenario())
        self.assertLess(elapsed, 1.0)
        self.assertEqual([w.status for w in created], ["處理中"])
        self.assertEqual(in_turn[0][0], "turn-1")
        self.assertEqual([p.text for p in in_turn[0][1]], ["已交給架構設計處理架構圖 #12"])
        self.assertIsNotNone(next(iter(items.values()))["deadlineAt"])

    def test_one_work_item_per_intent_and_below_threshold_creates_none(self):
        """`NFR12.15`／`BR52.1`：3 個意圖 → 恰 3 個工作項；信心不足 → 不建。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST", "GET"}
            made = await h.dispatch(ARCH, COST, REVIEW)
            low = await h.orchestrator.dispatch(
                fake_principal(), session(),
                IntentDecision(intents=(), confidence=0.2, below_threshold=True),
                utterance="?", segment_id="shared", turn_id="t2", bearer_token="tok", sink=h.sink,
            )
            await h.stop_all()
            return made, low, h.items()

        made, low, items = run(scenario())
        self.assertEqual(len(made), 3)
        self.assertEqual(len(items), 3)
        self.assertEqual(low, [])

    def test_unknown_segment_or_expired_session_raise_value_error(self):
        async def scenario():
            h = Harness()
            with self.assertRaises(ValueError):
                await h.orchestrator.dispatch(
                    fake_principal(), session(), decision(ARCH), utterance="x",
                    segment_id="workspace", turn_id="t", bearer_token="tok", sink=h.sink,
                )
            h.redis.hashes.pop(SESSION_KEY)
            with self.assertRaises(ValueError):
                await h.dispatch(ARCH)
            self.assertNotIn(SESSION_KEY, h.redis.hashes)

        run(scenario())


class ArchitectureHappyPathTest(unittest.TestCase):
    def test_architecture_design_persists_records_change_and_completes(self):
        async def scenario():
            h = Harness()
            created = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h, created[0].workItemId

        h, wid = run(scenario())
        item = h.item(wid)
        self.assertEqual((item["status"], item["dispatchStage"]), ("完成", "result_persisted"))
        self.assertEqual(item["sideEffect"], "已存回架構圖〈訂單系統〉")
        self.assertIsNone(item["deadlineAt"])
        self.assertEqual(len(h.recorder.changes), 1)
        self.assertEqual(h.recorder.changes[0]["actor"], 1)
        self.assertEqual(h.recorder.changes[0]["summary"], "加上快取層")
        self.assertEqual([m[1] for m in h.recorder.memories], ["procedure"])
        texts = h.sink.all_texts()
        self.assertIn("已依需求加上快取層", texts)  # BR58.3：A1 文字轉送
        self.assertIn("架構設計：架構圖 #12完成", texts)
        self.assertEqual(h.app.count("PUT"), 1)


class FacadeThreadTest(unittest.TestCase):
    def test_facade_calls_run_off_the_event_loop_thread(self):
        """② `NFR12.2`：facade 呼叫在非事件迴圈執行緒。"""

        async def scenario():
            h = Harness()
            h.recorder.system_diagrams[3] = [(12, "訂單系統")]
            loop_thread = threading.get_ident()
            await h.dispatch(ARCH, diagram_id=None, system_id=3)
            await drain(h.orchestrator)
            return h, loop_thread

        h, loop_thread = run(scenario())
        self.assertTrue(h.recorder.threads)
        self.assertNotIn(loop_thread, h.recorder.threads)
        self.assertEqual(h.recorder.calls[0][0], "list_diagrams_of_system")
        self.assertEqual(h.recorder.db_log.count(("close", h.recorder.db_log[0][1])) >= 1, True)

    def test_target_resolution_failures_use_distinct_phrases(self):
        cases = [
            ({"diagram_id": None, "system_id": None, "project_id": 4}, {}, "請先在脈絡列選定架構圖或系統"),
            ({"diagram_id": None, "system_id": 3}, {3: []}, "這個系統下沒有掛上的架構圖，請在脈絡列選定圖"),
            ({"diagram_id": None, "system_id": 3}, {3: [(1, "a"), (2, "b")]},
             "這個系統下有多張架構圖，請在脈絡列選定要用的那一張"),
        ]
        for target, diagrams, phrase in cases:
            with self.subTest(phrase=phrase):

                async def scenario():
                    h = Harness()
                    h.recorder.system_diagrams.update(diagrams)
                    made = await h.dispatch(ARCH, **target)
                    await drain(h.orchestrator)
                    return h.item(made[0].workItemId), h

                item, h = run(scenario())
                self.assertEqual((item["status"], item["failureReason"]), ("失敗", phrase))
                self.assertEqual(item["sideEffect"], "none")
                self.assertEqual(h.app.count("POST"), 0)


class CostPollingTest(unittest.TestCase):
    def test_polling_is_bounded_and_ends_in_cost_timeout(self):
        """③ `NFR12.3`：生成中一直不結束 → 360 秒內快照讀取 ≤ 180 次，之後失敗「成本分析逾時」。"""

        async def scenario():
            h = Harness()
            h.app.advice_snapshots = [{"status": "generating", "started_at": None}]
            made = await h.dispatch(COST)
            await drain(h.orchestrator)
            return h, made[0].workItemId

        h, wid = run(scenario())
        polls = h.app.count("GET /api/cost/v1/sets/7/advice")
        self.assertGreater(polls, 0)
        self.assertLessEqual(polls, 180)
        item = h.item(wid)
        self.assertEqual((item["status"], item["failureReason"]), ("失敗", "成本分析逾時"))
        self.assertEqual(item["estimateSetId"], 7)
        self.assertEqual(item["sideEffect"], "none")
        # AC10.1.2／BR57.1：生成中不新增訊息——整段輪詢只有最後那一則失敗訊息。
        self.assertEqual(
            [[p.text for p in ps] for ps in h.sink.turns],
            [["成本分析：架構圖 #12沒有完成：成本分析逾時"]],
        )

    def test_cost_completes_with_a_card_carrying_the_estimate_set_id(self):
        async def scenario():
            h = Harness()
            made = await h.dispatch(COST)
            await drain(h.orchestrator)
            return h, made[0].workItemId

        h, wid = run(scenario())
        self.assertEqual(h.item(wid)["status"], "完成")
        cards = [p for ps in h.sink.turns for p in ps if isinstance(p, CostCardPayload)]
        self.assertEqual(len(cards), 1)
        self.assertEqual((cards[0].estimateSetId, cards[0].costPageUrl), (7, "/cost?estimate=7"))
        self.assertEqual(cards[0].savingText, "可省 10%")

    def test_cost_failures_are_distinguishable(self):
        """`BR57.4`／`BR57.2`：逾時、失敗、404、連續三次讀取失敗各有不同句型。"""
        cases = [
            ({"status": "failed", "unavailable_reasons": {"timed_out": True}}, [], "成本分析逾時"),
            ({"status": "failed"}, [], "成本分析失敗"),
            ({"status": "completed"}, [404], "找不到這份估價表的建議"),
            ({"status": "completed"}, [500, 502, 503], "與成本服務的連線中斷"),
        ]
        for snapshot, errors, phrase in cases:
            with self.subTest(phrase=phrase):

                async def scenario():
                    h = Harness()
                    h.app.advice_snapshots = [snapshot]
                    h.app.advice_errors = list(errors)
                    made = await h.dispatch(COST)
                    await drain(h.orchestrator)
                    return h.item(made[0].workItemId)

                self.assertEqual(run(scenario())["failureReason"], phrase)

    def test_two_failed_reads_then_success_does_not_fail(self):
        """`NFR12.23` 後半：輪詢失敗 2 次後成功 → 不失敗。"""

        async def scenario():
            h = Harness()
            h.app.advice_errors = [500, 500, None]
            made = await h.dispatch(COST)
            await drain(h.orchestrator)
            return h.item(made[0].workItemId)

        self.assertEqual(run(scenario())["status"], "完成")

    def test_missing_estimate_or_advice_points_to_the_cost_page(self):
        cases = [
            ([[{"id": 9, "diagram_id": 99}]], "這張圖尚無估價表，可到成本頁上傳（/cost）"),
            ([[{"id": 7, "diagram_id": 12, "advice_status": "none"}]],
             "這份估價表還沒有產生建議，可到成本頁產生（/cost?estimate=7）"),
        ]
        for pages, phrase in cases:
            with self.subTest(phrase=phrase):

                async def scenario():
                    h = Harness()
                    h.app.estimate_pages = pages
                    made = await h.dispatch(COST)
                    await drain(h.orchestrator)
                    return h.item(made[0].workItemId)

                self.assertEqual(run(scenario())["failureReason"], phrase)


class WaitingTest(unittest.TestCase):
    def test_waiters_follow_the_architecture_item(self):
        """④ `BR53.1`／`BR53.2`：成本與檢視等待架構設計；它完成後兩者開始並完成。"""

        async def scenario():
            h = Harness()
            made = await h.dispatch(ARCH, COST, REVIEW)
            statuses = [w.status for w in made]
            waiting_on = [w.waitingOn for w in made]
            await drain(h.orchestrator)
            return h, made, statuses, waiting_on

        h, made, statuses, waiting_on = run(scenario())
        self.assertEqual(statuses, ["處理中", "等待中", "等待中"])
        self.assertEqual(waiting_on, [None, "架構設計：架構圖 #12", "架構設計：架構圖 #12"])
        self.assertEqual([h.item(w.workItemId)["status"] for w in made], ["完成"] * 3)
        self.assertIn("成本分析：架構圖 #12會在架構設計：架構圖 #12完成後開始", h.sink.in_turn[0][1][1].text)

    def test_stopping_the_dependency_starts_cost_but_skips_review(self):
        """④ `BR53.4`：停掉前一項 → 成本照常開始、檢視轉已停掉並說明，不呼叫 A3。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST /api/architecture/generate"}
            made = await h.dispatch(ARCH, COST, REVIEW)
            await asyncio.sleep(0)
            await h.correct(made[0].workItemId)
            await drain(h.orchestrator)
            return h, made

        h, made = run(scenario())
        arch, cost, review = (h.item(w.workItemId) for w in made)
        self.assertEqual(arch["status"], "已停掉")
        self.assertEqual(cost["status"], "完成")
        self.assertEqual((review["status"], review["sideEffect"]), ("已停掉", "none"))
        self.assertIsNone(review["dependsOn"])
        self.assertEqual(h.app.count("POST /api/architecture/reviews"), 0)
        self.assertIn(
            "架構檢視：架構圖 #12沒有執行：前一項架構設計：架構圖 #12已停掉", h.sink.all_texts()
        )
        self.assertIn("已停掉架構設計：架構圖 #12。請再說一次你要做什麼。", h.sink.all_texts())

    def test_failed_dependency_fails_the_waiters(self):
        """`BR53.3`。"""

        async def scenario():
            h = Harness()
            h.app.a1_events = [{"type": "error", "content": "x"}]
            made = await h.dispatch(ARCH, COST)
            await drain(h.orchestrator)
            return h.item(made[1].workItemId)

        cost = run(scenario())
        self.assertEqual(
            (cost["status"], cost["failureReason"]),
            ("失敗", "前一項架構設計：架構圖 #12沒有完成，這一項沒有執行"),
        )


class CorrectTest(unittest.TestCase):
    def test_correct_interleaved_with_background_advance_reports_the_real_stage(self):
        """⑤ `correct` 讀完之後、寫入之前，背景把 `dispatchStage` 推進到 request_sent：
        sideEffect 依推進後的真實值（unknown），不是 none（`BR52.7`）。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"GET /api/collab"}
            made = await h.dispatch(ARCH)
            await asyncio.sleep(0)
            wid = made[0].workItemId

            def background_advance(keys, argv):
                fields = h.redis.hashes[keys[0]]
                _, updated = T.ref_update_work_item(
                    fields, f"wi:{wid}", '["處理中"]', "not_dispatched",
                    '{"dispatchStage":"request_sent"}',
                )
                h.redis.hashes[keys[0]] = updated

            h.redis.before_update = background_advance
            await h.correct(wid)
            await h.stop_all()
            return h.item(wid)

        item = run(scenario())
        self.assertEqual(item["status"], "已停掉")
        self.assertEqual(item["dispatchStage"], "request_sent")
        self.assertEqual(item["sideEffect"], "unknown")

    def test_correct_is_a_no_op_on_terminal_items_and_rejects_unknown_ids(self):
        async def scenario():
            h = Harness()
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            pushes_before = len(h.sink.session)
            again = await h.correct(made[0].workItemId)
            with self.assertRaises(WorkItemNotFound):
                await h.correct("missing")
            return again, pushes_before, len(h.sink.session)

        again, before, after = run(scenario())
        self.assertEqual(again.status, "完成")
        self.assertEqual(before, after)

    def test_write_failure_before_request_means_nothing_is_sent(self):
        """`NFR12.21`：記 request_sent 的寫入回 False → A1 被呼叫 0 次。"""

        async def scenario():
            h = Harness()

            def steal(keys, argv):
                fields = h.redis.hashes[keys[0]]
                item = json.loads(fields[argv[0]])
                item["status"] = "已停掉"
                fields[argv[0]] = json.dumps(item, ensure_ascii=False)

            h.redis.before_update = steal
            await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h

        h = run(scenario())
        self.assertEqual(h.app.count("POST /api/architecture/generate"), 0)


class InFlightPersistTest(unittest.TestCase):
    """⑥ 在途存檔的四列（`reliability-design.md` 第二節；`NFR12.20`）。"""

    def _delayed(self, **kwargs):
        h = Harness(**kwargs)
        h.app.put_release = asyncio.Event()
        h.app.put_started = asyncio.Event()
        return h

    def test_stopped_while_put_in_flight_records_the_change(self):
        async def scenario():
            h = self._delayed()
            made = await h.dispatch(ARCH)
            wid = made[0].workItemId
            await asyncio.wait_for(h.app.put_started.wait(), 5)
            await h.correct(wid)
            stopped = dict(h.item(wid))
            h.app.put_release.set()
            await drain(h.orchestrator)
            return h, stopped, h.item(wid)

        h, stopped, item = run(scenario())
        self.assertEqual(stopped["sideEffect"], "可能已存回架構圖〈訂單系統〉")
        self.assertEqual(item["status"], "已停掉")
        self.assertEqual(item["sideEffect"], "已存回架構圖〈訂單系統〉")
        self.assertEqual(item["dispatchStage"], "result_persisted")
        self.assertEqual(len(h.recorder.changes), 1)
        self.assertEqual(h.recorder.memories, [])
        self.assertNotIn("架構設計：架構圖 #12完成", h.sink.all_texts())

    def test_timed_out_before_put_returns_still_records_the_change(self):
        async def scenario():
            h = self._delayed(persist_timeout=100_000)
            made = await h.dispatch(ARCH)
            wid = made[0].workItemId
            await asyncio.wait_for(h.app.put_started.wait(), 5)
            h.clock.advance(400)
            for _ in range(20):
                await asyncio.sleep(0)
                if h.item(wid)["status"] == "失敗":
                    break
            failed = dict(h.item(wid))
            h.app.put_release.set()
            await drain(h.orchestrator)
            return h, failed, h.item(wid)

        h, failed, item = run(scenario())
        self.assertEqual((failed["status"], failed["failureReason"]), ("失敗", "架構設計逾時"))
        self.assertEqual(failed["sideEffect"], "可能已存回架構圖〈訂單系統〉")
        self.assertEqual(item["status"], "失敗")
        self.assertEqual(item["sideEffect"], "已存回架構圖〈訂單系統〉")
        self.assertEqual(len(h.recorder.changes), 1)

    def test_put_rejected_while_processing_fails_with_no_side_effect(self):
        async def scenario():
            h = Harness()
            h.app.status_overrides["PUT /api/collab/diagrams/12"] = 500
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h, h.item(made[0].workItemId)

        h, item = run(scenario())
        self.assertEqual((item["status"], item["sideEffect"]), ("失敗", "none"))
        self.assertEqual(item["failureReason"], "架構設計暫時無法使用")
        self.assertEqual(h.recorder.changes, [])

    def test_put_rejected_after_stop_clears_the_maybe_side_effect(self):
        async def scenario():
            h = self._delayed()
            h.app.status_overrides["PUT"] = 500
            made = await h.dispatch(ARCH)
            wid = made[0].workItemId
            await asyncio.wait_for(h.app.put_started.wait(), 5)
            await h.correct(wid)
            h.app.put_release.set()
            await drain(h.orchestrator)
            return h.item(wid)

        item = run(scenario())
        self.assertEqual((item["status"], item["sideEffect"]), ("已停掉", "none"))


class CancellationTest(unittest.TestCase):
    """審查 R-01／R-03：失敗或完成的寫入成功之後，剩下的副作用不得被自己的執行鏈取消。

    `RecordingSink` 每次 emit 都讓出事件迴圈（R-02），這幾案在不讓出的替身上不可能紅。
    """

    def test_cost_timeout_still_pushes_and_says_so(self):
        """R-01：`_Failed(timeout)` 路徑寫成失敗後，work_items 推送與失敗訊息都送達。"""

        async def scenario():
            h = Harness()
            h.app.advice_snapshots = [{"status": "failed", "unavailable_reasons": {"timed_out": True}}]
            made = await h.dispatch(COST)
            await drain(h.orchestrator)
            return h, made[0].workItemId

        h, wid = run(scenario())
        self.assertEqual(h.item(wid)["status"], "失敗")
        self.assertEqual(h.sink.session[-1].items[0].status, "失敗")
        self.assertIn("成本分析：架構圖 #12沒有完成：成本分析逾時", h.sink.all_texts())

    def test_persist_timeout_still_advances_the_waiter(self):
        """R-01：在途存檔逾時（`_settle_put_unknown` 的 timeout）之後，等待者仍被推進為失敗。

        `_Failed(timeout)` 只出現在成本輪詢與存檔收尾兩處；會有等待者的只有架構設計，故
        「等待者推進」以存檔收尾這條路徑驗證。
        """

        async def scenario():
            h = Harness(persist_timeout=10)
            h.app.put_release = asyncio.Event()  # 永不放行：PUT 結果未知
            made = await h.dispatch(ARCH, COST)
            await drain(h.orchestrator)
            return h, made

        h, made = run(scenario())
        arch, cost = (h.item(w.workItemId) for w in made)
        self.assertEqual((arch["status"], arch["failureReason"]), ("失敗", "架構設計逾時"))
        self.assertEqual(arch["sideEffect"], "可能已存回架構圖〈訂單系統〉")
        self.assertEqual(cost["status"], "失敗")
        texts = h.sink.all_texts()
        self.assertIn("架構設計：架構圖 #12沒有完成：架構設計逾時", texts)
        self.assertIn(
            "成本分析：架構圖 #12沒有完成：前一項架構設計：架構圖 #12沒有完成，這一項沒有執行", texts
        )

    def test_watchdog_does_not_cut_off_completion_after_the_deadline(self):
        """R-03：完成的寫入成功後、送完成訊息時時鐘越過舊 deadline，收尾仍完整跑完。

        用架構檢視：它的完成收尾在 `_run` 的內層 task 裡（架構設計的完成在被 shield
        保護的存檔收尾 task 裡，看門迴圈本來就取消不到它）。
        """

        async def scenario():
            h = Harness()
            made = await h.dispatch(REVIEW)

            async def jump_past_deadline(kind, payloads):
                if kind == "turn" and any(
                    getattr(p, "text", "").startswith("檢視完成") for p in payloads
                ):
                    h.clock.advance(400)
                    for _ in range(5):
                        await asyncio.sleep(0)

            h.sink.on_emit = jump_past_deadline
            await drain(h.orchestrator)
            return h, made[0].workItemId

        h, wid = run(scenario())
        self.assertEqual(h.item(wid)["status"], "完成")
        self.assertIn("檢視完成：整體分數82，2項發現", h.sink.all_texts())


class TimeoutTest(unittest.TestCase):
    def test_capability_that_never_returns_times_out_at_300_seconds(self):
        """`NFR12.19`：A1 永不返回、注入時鐘推進到 300 秒 → 失敗「架構設計逾時」。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST /api/architecture/generate"}
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h, h.item(made[0].workItemId)

        h, item = run(scenario())
        self.assertEqual((item["status"], item["failureReason"]), ("失敗", "架構設計逾時"))
        self.assertEqual(item["sideEffect"], "unknown")
        elapsed = (h.clock.now - item_created(item)).total_seconds()
        self.assertGreaterEqual(elapsed, 300)


def item_created(item):
    from datetime import datetime

    return datetime.fromisoformat(item["createdAt"])


class RecoveryTest(unittest.TestCase):
    def test_expired_processing_item_is_failed_on_read(self):
        """⑦ `NFR12.17`：處理中且 deadlineAt 已過 → `list_items` 後為失敗。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST"}
            made = await h.dispatch(ARCH)
            await asyncio.sleep(0)
            await h.stop_all()  # 模擬行程重啟：task 消失
            fresh = Harness()
            fresh.store, fresh.redis = h.store, h.redis
            fresh.orchestrator._store = h.store
            fresh.clock.now = h.clock.now
            fresh.orchestrator._clock = fresh.clock
            fresh.clock.advance(301)
            listed = await fresh.list_items()
            return listed, made

        listed, made = run(scenario())
        self.assertEqual(listed[0].workItemId, made[0].workItemId)
        self.assertEqual(listed[0].status, "失敗")
        self.assertEqual(listed[0].failureReason, "服務重新啟動或逾時，這一項沒有完成")
        self.assertEqual(listed[0].sideEffect, "unknown")

    def test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans(self):
        """⑦ `NFR12.13`：被等待者已完成、等待者仍等待中；兩個復原掃描讀到同一份
        舊快照，只有比對後寫入成功的那一個啟動能力（能力被呼叫恰 1 次）。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST /api/architecture/generate"}
            made = await h.dispatch(ARCH, COST)
            await asyncio.sleep(0)
            await h.stop_all()
            arch_id, cost_id = made[0].workItemId, made[1].workItemId
            fields = h.redis.hashes[SESSION_KEY]
            arch = json.loads(fields[f"wi:{arch_id}"])
            arch.update({"status": "完成", "deadlineAt": None})
            fields[f"wi:{arch_id}"] = json.dumps(arch, ensure_ascii=False)

            # 第二個掃描者在第一個寫入**之前**就讀了快照（多 worker 的交錯）：先記下那份
            # 舊快照，第一個掃描照常執行；第二個掃描（只有它自己的 task）讀到舊快照。
            # 背景 task 一律讀真實值，否則它們會因讀到舊的「等待中」而提早結束，
            # 使「啟動了幾次」數不出來（sink 會讓出事件迴圈，R-02）。
            stale = h.store.load_work_items(SESSION_KEY)
            real_load = h.store.load_work_items
            scanner = {}

            def load(key):
                if asyncio.current_task() is scanner.get("task"):
                    return copy.deepcopy(stale)
                return real_load(key)

            h.store.load_work_items = load
            # 讓被啟動的成本 task 停在第一個能力呼叫（列估價表），以便計數。
            h.app.release.clear()
            h.app.hang = {"GET /api/cost/v1/sets"}
            await h.list_items()
            for _ in range(50):
                if "GET /api/cost/v1/sets" in h.app.calls:
                    break
                await asyncio.sleep(0)

            async def second_scan():
                scanner["task"] = asyncio.current_task()
                await h.list_items()

            await asyncio.create_task(second_scan())
            for _ in range(50):
                await asyncio.sleep(0)
            h.store.load_work_items = real_load
            h.app.hang = set()
            h.app.release.set()
            await drain(h.orchestrator)
            return h, cost_id

        h, cost_id = run(scenario())
        # 能力呼叫的第一步（列估價表）恰 1 次：第二個掃描的寫入回 False，不得再啟動。
        self.assertEqual(h.app.calls.count("GET /api/cost/v1/sets"), 1)
        self.assertEqual(h.app.count("GET /api/cost/v1/sets/7/advice"), 1)
        self.assertEqual(h.item(cost_id)["status"], "完成")
        cards = [p for ps in h.sink.turns for p in ps if isinstance(p, CostCardPayload)]
        self.assertEqual(len(cards), 1)

    def test_state_survives_dropping_the_orchestrator(self):
        """`NFR12.16`：丟棄實例、以新實例 `list_items` 取回同一集合。"""

        async def scenario():
            h = Harness()
            h.app.hang = {"POST"}
            made = await h.dispatch(ARCH, COST)
            await asyncio.sleep(0)
            await h.stop_all()
            other = WorkOrchestrator(h.app, h.store, clock=h.clock, sleep=h.clock.sleep)
            listed = await other.list_items(fake_principal(), SESSION_KEY, bearer_token="tok", sink=h.sink)
            return made, listed

        made, listed = run(scenario())
        self.assertEqual([w.workItemId for w in made], [w.workItemId for w in listed])


class RobustnessTest(unittest.TestCase):
    def test_unknown_write_result_is_confirmed_by_rereading(self):
        """⑧ 帶入項 19：寫入遇連線錯誤 → 重讀；已套用者視為成功（只啟動一次）。"""

        async def scenario():
            h = Harness()
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)

            def applied_then_lost(keys, argv):
                _, updated = T.ref_update_work_item(h.redis.hashes[keys[0]], *argv)
                h.redis.hashes[keys[0]] = updated
                raise FakeConnectionError("reply lost")

            h.redis.before_update = applied_then_lost
            stopped = await h.correct((await h.dispatch(REVIEW))[0].workItemId)
            await drain(h.orchestrator)
            return stopped

        self.assertEqual(run(scenario()).status, "已停掉")

    def test_sink_failures_do_not_change_the_outcome(self):
        """`NFR12.22`／`NFR12.26`：sink 一律拋例外，工作項照常完成並記 WARNING。"""

        async def scenario():
            h = Harness()
            h.sink.fail = True
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h.item(made[0].workItemId)

        with self.assertLogs("cloud360.work_orchestrator", level="WARNING") as logs:
            item = run(scenario())
        self.assertEqual(item["status"], "完成")
        self.assertTrue(any("sink_failed" in line for line in logs.output))

    def test_side_write_failures_warn_without_content_and_keep_the_outcome(self):
        """`NFR12.26`／`BR51.4`／`BR51.5`：變更紀錄與記憶寫入失敗各記 WARNING（只含類別名），
        工作項維持完成。"""
        marker = f"secret-{uuid.uuid4()}"

        async def scenario():
            h = Harness()
            h.recorder.change_error = RuntimeError(marker)
            h.recorder.memory_error = RuntimeError(marker)
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h.item(made[0].workItemId)

        with self.assertLogs("cloud360.work_orchestrator", level="WARNING") as logs:
            item = run(scenario())
        self.assertEqual(item["status"], "完成")
        self.assertEqual(item["sideEffect"], "已存回架構圖〈訂單系統〉（變更紀錄未寫入）")
        output = "\n".join(logs.output)
        self.assertIn("change_record_failed error=RuntimeError", output)
        self.assertIn("memory_write_failed error=RuntimeError", output)
        self.assertNotIn(marker, output)

    def test_capability_failures_are_not_retried(self):
        """`NFR12.23`／`BR56.4`：A1 回 500 → 被呼叫恰 1 次；401／403 也不重試。"""
        for status, reason in ((500, "架構設計暫時無法使用"), (401, "登入已過期，請重新登入後再說一次"),
                               (403, "你沒有使用架構設計的權限，或帳號已被停用")):
            with self.subTest(status=status):

                async def scenario():
                    h = Harness()
                    h.app.status_overrides["POST /api/architecture/generate"] = status
                    made = await h.dispatch(ARCH)
                    await drain(h.orchestrator)
                    return h, h.item(made[0].workItemId)

                h, item = run(scenario())
                self.assertEqual(h.app.count("POST /api/architecture/generate"), 1)
                self.assertEqual(item["failureReason"], reason)
                self.assertEqual(item["sideEffect"], "unknown")

    def test_disabled_before_persist_fails_without_put(self):
        """`NFR12.9` 第一案：A1 回應之前停用 → 失敗且未 PUT。"""

        async def scenario():
            h = Harness()

            def disable():
                h.recorder.users[1].is_active = False

            h.app.hooks["POST /api/architecture/generate"] = disable
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h, h.item(made[0].workItemId)

        h, item = run(scenario())
        self.assertEqual(item["status"], "失敗")
        self.assertEqual(item["failureReason"], "你沒有使用架構設計的權限，或帳號已被停用")
        self.assertEqual(h.app.count("PUT"), 0)

    def test_disabled_after_put_keeps_status_and_notes_missing_change_record(self):
        """`NFR12.9` 第二案（帶入項 10）：PUT 成功之後、寫變更紀錄之前停用 →
        有重鑄則變更紀錄未寫入、狀態維持完成、sideEffect 註明。"""

        async def scenario():
            h = Harness()

            def disable():
                h.recorder.users[1].is_active = False

            h.app.hooks["PUT"] = disable
            made = await h.dispatch(ARCH)
            await drain(h.orchestrator)
            return h, h.item(made[0].workItemId)

        h, item = run(scenario())
        self.assertEqual(item["status"], "完成")
        self.assertEqual(h.recorder.changes, [])
        self.assertEqual(item["sideEffect"], "已存回架構圖〈訂單系統〉（變更紀錄未寫入）")

    def test_token_and_request_text_never_reach_logs_and_token_never_reaches_redis(self):
        """`NFR12.6`／`NFR12.10`／`NFR12.11`：以唯一標記作 token 與原句，含失敗路徑。"""
        token = f"tok-{uuid.uuid4()}"
        utterance = f"原句-{uuid.uuid4()}"

        async def scenario():
            h = Harness()
            h.app.raise_in["POST /api/architecture/reviews"] = RuntimeError(f"boom {token}")
            await h.dispatch(ARCH, COST, REVIEW, token=token, utterance=utterance)
            await drain(h.orchestrator)
            return h

        with self.assertLogs("cloud360", level=logging.DEBUG) as logs:
            h = run(scenario())
        log_text = "\n".join(logs.output)
        self.assertNotIn(token, log_text)
        self.assertNotIn(utterance, log_text)
        redis_dump = json.dumps(h.redis.hashes, ensure_ascii=False)
        self.assertNotIn(token, redis_dump)
        self.assertNotIn(token, h.sink.dump())
        self.assertNotIn(utterance, h.sink.dump())
        failures = [line for line in logs.output if "failure=" in line]
        self.assertEqual(len(failures), 1)
        self.assertIn("failure=capability_failed", failures[0])

    def test_every_message_is_a_contract_model(self):
        """`NFR12.27`：sink 只接受契約模型（`RecordingSink` 會拒絕其他型別）。"""

        async def scenario():
            h = Harness()
            await h.dispatch(ARCH, COST, REVIEW)
            await drain(h.orchestrator)
            return h

        h = run(scenario())
        payloads = [p for _, ps in h.sink.in_turn for p in ps] + [p for ps in h.sink.turns for p in ps]
        self.assertTrue(payloads)
        for p in payloads:
            self.assertIsInstance(p, (TokenPayload, CostCardPayload))
        self.assertTrue(h.sink.session)


if __name__ == "__main__":
    unittest.main()
