"""`U12 work-orchestrator` Step 8：比對後寫入的模型式 PBT（`NFR12.12`；帶入項 7、8）。

`hypothesis.stateful.RuleBasedStateMachine` 隨機交錯五種操作——背景推進
`dispatchStage`、寫 `estimateSetId`、`correct`（可在讀完與寫入之間被背景推進插隊）、
復原掃描、被等待者轉終態——全部走**真正的** `WorkOrchestrator` 與 `SessionStore`，
Redis 為以參考實作模擬 Lua 的替身。不變量（`scalability-design.md` 第三節）：

(a) 請求已送出（`dispatchStage` ≠ not_dispatched）時停掉，`sideEffect` 不為 none（成本除外）
(b) 終態不被改寫
(c) `estimateSetId` 一旦非 null 永不回到 null
(d) `status=處理中 ⇔ deadlineAt 非 null`
(e) `status=等待中 ⇔ dependsOn 非 null`

背景執行的 task 在本測試中**不啟動**（`_start` 只記錄），使每一步都是可重現的
同步交錯；能力呼叫的行為由流程測試承擔。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import os
import unittest

from hypothesis import HealthCheck, Phase, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from services import session_types as T
from services import work_orchestrator_rules as R
from services.intent_routing_types import Intent, IntentDecision
from services.work_orchestrator import WorkOrchestrator, _Ctx, _StepAborted
from tests.work_orchestrator_fakes import (
    SESSION_KEY,
    UPDATE_CAPACITY_ARGS,
    CostListApp,
    FacadeRecorder,
    FakeClock,
    RecordingSink,
    fake_mint,
    fake_principal,
    make_store,
)

_NO_SHRINK = os.environ.get("HYPOTHESIS_NO_SHRINK") == "1"

_NEXT_STAGE = {
    R.CAP_ARCHITECTURE: {
        R.STAGE_NOT_DISPATCHED: R.STAGE_REQUEST_SENT,
        R.STAGE_REQUEST_SENT: R.STAGE_PERSISTING,
        R.STAGE_PERSISTING: R.STAGE_RESULT_PERSISTED,
    },
    R.CAP_REVIEW: {
        R.STAGE_NOT_DISPATCHED: R.STAGE_REQUEST_SENT,
        R.STAGE_REQUEST_SENT: R.STAGE_RESULT_PERSISTED,
    },
}


def _session():
    return T.BrainSession(
        session_key=SESSION_KEY,
        segments={"shared": T.ConversationSegment(segment_id="shared", created_at="", diagram_id=12)},
    )


class WorkItemMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.store, self.redis = make_store()
        self.clock = FakeClock()
        self.sink = RecordingSink()
        recorder = FacadeRecorder()
        self.orch = WorkOrchestrator(
            CostListApp(), self.store, clock=self.clock, sleep=self.clock.sleep,
            session_factory=recorder.session_factory,
            hierarchy_facade_factory=recorder.hierarchy_factory,
            memory_facade_factory=recorder.memory_factory, mint=fake_mint, user_model=object,
        )
        self.started = []
        self.orch._start = lambda ctx: self.started.append(ctx.item_id)
        for caps in (
            (R.CAP_ARCHITECTURE, R.CAP_COST, R.CAP_REVIEW),
            (R.CAP_COST,),
            (R.CAP_REVIEW,),
        ):
            asyncio.run(self.orch.dispatch(
                fake_principal(), _session(),
                IntentDecision(intents=tuple(Intent(c) for c in caps), confidence=0.9, below_threshold=False),
                utterance="需求", segment_id="shared", turn_id="t", bearer_token="tok", sink=self.sink,
            ))
        self.ids = sorted(self.items())
        self.terminal_seen = {}
        self.estimate_seen = set()
        self.next_estimate = 100

    # -- helpers -------------------------------------------------------------

    def items(self):
        return self.store.load_work_items(SESSION_KEY)

    def pick(self, index):
        return self.items()[self.ids[index % len(self.ids)]]

    def _ctx(self, item):
        return _Ctx(SESSION_KEY, item["workItemId"], 1, "tok", self.sink)

    def _background_advance(self, item):
        nxt = _NEXT_STAGE.get(item["capability"], {}).get(item["dispatchStage"])
        if item["status"] != R.STATUS_PROCESSING or nxt is None:
            return False
        return self.orch._cas(SESSION_KEY, item, [R.STATUS_PROCESSING], {"dispatchStage": nxt})

    # -- rules ---------------------------------------------------------------

    @rule(index=st.integers(min_value=0, max_value=20))
    def background_advance(self, index):
        self._background_advance(self.pick(index))

    @rule(index=st.integers(min_value=0, max_value=20))
    def write_estimate_set_id(self, index):
        item = self.pick(index)
        if item["capability"] == R.CAP_COST and item["status"] == R.STATUS_PROCESSING \
                and item.get("estimateSetId") is None:
            self.next_estimate += 1
            self.orch._cas(SESSION_KEY, item, [R.STATUS_PROCESSING], {"estimateSetId": self.next_estimate})

    @rule(index=st.integers(min_value=0, max_value=20), interleave=st.booleans())
    def correct(self, index, interleave):
        item = self.pick(index)
        if interleave:
            wid = item["workItemId"]

            def background_jumps_in(keys, argv):
                current = self.store.load_work_items(SESSION_KEY).get(wid)
                if current is not None:
                    nxt = _NEXT_STAGE.get(current["capability"], {}).get(current["dispatchStage"])
                    if current["status"] == R.STATUS_PROCESSING and nxt is not None:
                        _, updated = T.ref_update_work_item(
                            self.redis.hashes[keys[0]], f"wi:{wid}", '["處理中"]',
                            current["dispatchStage"], '{"dispatchStage":"%s"}' % nxt,
                            *UPDATE_CAPACITY_ARGS,
                        )
                        self.redis.hashes[keys[0]] = updated

            self.redis.before_update = background_jumps_in
        asyncio.run(self.orch.correct(
            fake_principal(), SESSION_KEY, item["workItemId"], bearer_token="tok", sink=self.sink
        ))
        self.redis.before_update = None

    @rule(seconds=st.integers(min_value=0, max_value=400))
    def recovery_scan(self, seconds):
        self.clock.advance(seconds)
        asyncio.run(self.orch.list_items(fake_principal(), SESSION_KEY, bearer_token="tok", sink=self.sink))

    @rule(index=st.integers(min_value=0, max_value=20), succeed=st.booleans())
    def dependency_turns_terminal(self, index, succeed):
        item = self.pick(index)
        if item["status"] != R.STATUS_PROCESSING:
            return

        async def go():
            if succeed:
                try:
                    await self.orch._complete(self._ctx(item), item, {}, [self.orch._token("完成")])
                except _StepAborted:
                    pass
            else:
                await self.orch._fail_item(self._ctx(item), item, "失敗了", "capability_failed")

        asyncio.run(go())

    # -- invariants ------------------------------------------------------------

    @invariant()
    def a_stop_after_sending_is_never_none(self):
        for item in self.items().values():
            if item["status"] == R.STATUS_STOPPED and item["capability"] != R.CAP_COST \
                    and item["dispatchStage"] != R.STAGE_NOT_DISPATCHED:
                assert item["sideEffect"] != R.SIDE_EFFECT_NONE, item

    @invariant()
    def b_terminal_is_never_rewritten(self):
        for wid, item in self.items().items():
            if wid in self.terminal_seen:
                assert (item["status"], item.get("failureReason")) == self.terminal_seen[wid], item
            elif item["status"] in R.TERMINAL_STATUSES:
                self.terminal_seen[wid] = (item["status"], item.get("failureReason"))

    @invariant()
    def c_estimate_set_id_is_never_cleared(self):
        for wid, item in self.items().items():
            if wid in self.estimate_seen:
                assert item.get("estimateSetId") is not None, item
            elif item.get("estimateSetId") is not None:
                self.estimate_seen.add(wid)

    @invariant()
    def d_processing_iff_deadline(self):
        for item in self.items().values():
            assert (item["status"] == R.STATUS_PROCESSING) == (item.get("deadlineAt") is not None), item

    @invariant()
    def e_waiting_iff_depends_on(self):
        for item in self.items().values():
            assert (item["status"] == R.STATUS_WAITING) == (item.get("dependsOn") is not None), item


_phases = [Phase.explicit, Phase.reuse, Phase.generate] if _NO_SHRINK else list(Phase)
WorkItemMachine.TestCase.settings = settings(
    max_examples=60,
    stateful_step_count=25,
    deadline=None,
    phases=_phases,
    suppress_health_check=[HealthCheck.too_slow],
)


class WorkItemModelTest(WorkItemMachine.TestCase):
    """`NFR12.12`：交由 hypothesis 產生交錯序列。"""


if __name__ == "__main__":
    unittest.main()
