"""`U12 work-orchestrator` Step 8：純函式層的 property-based 測試（`NFR12.28`；ADR-0006）。

四個純函式各有 `@given` 性質；`PHRASES` 的每個句型各有一案（帶入項 8）。
`HYPOTHESIS_NO_SHRINK=1` 時關閉 shrinking（突變驗證用，見 `unit-test-instructions.md §四`）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import os
import unittest

from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from services import work_orchestrator_rules as R

if os.environ.get("HYPOTHESIS_NO_SHRINK") == "1":
    settings.register_profile(
        "no_shrink", phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target]
    )
    settings.load_profile("no_shrink")

capabilities = st.sampled_from([R.CAP_ARCHITECTURE, R.CAP_REVIEW, R.CAP_COST])
statuses = st.sampled_from(R.STATUSES)
events = st.sampled_from(R.EVENTS)
stages = st.sampled_from(R.DISPATCH_STAGES)


class TransitionPropertyTest(unittest.TestCase):
    @given(start=st.sampled_from([R.STATUS_PROCESSING, R.STATUS_WAITING]), seq=st.lists(events, max_size=12))
    def test_any_event_sequence_stays_in_the_five_values_and_never_leaves_a_terminal(self, start, seq):
        status = start
        for event in seq:
            was_terminal = status in R.TERMINAL_STATUSES
            try:
                status = R.transition(status, event)
            except R.InvalidTransition:
                continue
            self.assertFalse(was_terminal, "終態不得有向外的轉換")
            self.assertIn(status, R.STATUSES)

    @given(status=st.sampled_from(sorted(R.TERMINAL_STATUSES)), event=events)
    def test_terminal_states_reject_every_event(self, status, event):
        with self.assertRaises(R.InvalidTransition):
            R.transition(status, event)

    def test_exactly_the_six_legal_status_pairs(self):
        """`BR54.1`：合法的（來源, 目的）恰為六種。"""
        pairs = set()
        for status in R.STATUSES:
            for event in R.EVENTS:
                try:
                    pairs.add((status, R.transition(status, event)))
                except R.InvalidTransition:
                    pass
        self.assertEqual(
            pairs,
            {
                ("等待中", "處理中"), ("等待中", "失敗"), ("等待中", "已停掉"),
                ("處理中", "完成"), ("處理中", "失敗"), ("處理中", "已停掉"),
            },
        )


class PlanWaitsPropertyTest(unittest.TestCase):
    @given(caps=st.lists(capabilities, max_size=8))
    def test_only_cost_or_review_wait_on_the_nearest_earlier_architecture(self, caps):
        waits = R.plan_waits(caps)
        self.assertEqual(len(waits), len(caps))
        for index, target in enumerate(waits):
            earlier_arch = [i for i in range(index) if caps[i] == R.CAP_ARCHITECTURE]
            if caps[index] in (R.CAP_COST, R.CAP_REVIEW) and earlier_arch:
                self.assertEqual(target, earlier_arch[-1])
            else:
                self.assertIsNone(target)

    @given(caps=st.lists(capabilities, max_size=8))
    def test_waits_never_form_a_cycle(self, caps):
        waits = R.plan_waits(caps)
        for index in range(len(caps)):
            seen, cursor = set(), index
            while cursor is not None:
                self.assertNotIn(cursor, seen)
                seen.add(cursor)
                cursor = waits[cursor]


class SideEffectPropertyTest(unittest.TestCase):
    @given(capability=capabilities, stage=stages, name=st.text(max_size=10))
    def test_cost_and_not_dispatched_are_none_others_are_not(self, capability, stage, name):
        side = R.side_effect_on_stop(capability, stage, diagram_name=name)
        if capability == R.CAP_COST or stage == R.STAGE_NOT_DISPATCHED:
            self.assertEqual(side, R.SIDE_EFFECT_NONE)
        else:
            self.assertNotEqual(side, R.SIDE_EFFECT_NONE)
        if capability != R.CAP_COST and stage == R.STAGE_PERSISTING:
            self.assertTrue(side.startswith("可能已存回架構圖"))
        if capability != R.CAP_COST and stage == R.STAGE_REQUEST_SENT:
            self.assertEqual(side, R.SIDE_EFFECT_UNKNOWN)


class DependencyStoppedPropertyTest(unittest.TestCase):
    @given(capability=capabilities)
    def test_cost_proceeds_review_skips(self, capability):
        outcome = R.on_dependency_stopped(capability)
        if capability == R.CAP_COST:
            self.assertEqual(outcome, R.PROCEED)
        elif capability == R.CAP_REVIEW:
            self.assertEqual(outcome, R.SKIP)

    @given(capability=capabilities, dep=st.sampled_from(sorted(R.TERMINAL_STATUSES)))
    def test_dependency_terminal_event_is_always_legal_from_waiting(self, capability, dep):
        event = R.event_for_dependency_terminal(capability, dep)
        self.assertIn(R.transition(R.STATUS_WAITING, event), R.STATUSES)


class PhraseTest(unittest.TestCase):
    """`BR58.1` 的全部句型各一案（帶入項 8）：句型是 UI 字面，改動須有人看見。"""

    EXPECTED = {
        "created": ({"capability": "架構設計", "target": "架構圖 #1"}, "已交給架構設計處理架構圖 #1"),
        "waiting": ({"label": "成本分析", "waiting_label": "架構設計"}, "成本分析會在架構設計完成後開始"),
        "done": ({"label": "架構設計"}, "架構設計完成"),
        "done_cost": ({"label": "成本分析"}, "成本分析完成（依既有的估價表與已產生的建議，不會因改圖而重算）"),
        "done_review": ({"score": 80, "count": 3}, "檢視完成：整體分數80，3項發現"),
        "failed": ({"label": "L", "reason": "R"}, "L沒有完成：R"),
        "stopped": ({"label": "L"}, "已停掉L。請再說一次你要做什麼。"),
        "skipped": ({"label": "架構檢視", "dependency_label": "架構設計"}, "架構檢視沒有執行：前一項架構設計已停掉"),
        "forbidden": ({"capability": "成本分析"}, "你沒有使用成本分析的權限，或帳號已被停用"),
        "unauthorized": ({}, "登入已過期，請重新登入後再說一次"),
        "dependency_failed": ({"dependency_label": "D"}, "前一項D沒有完成，這一項沒有執行"),
        "no_target": ({}, "請先在脈絡列選定架構圖或系統"),
        "system_no_diagram": ({}, "這個系統下沒有掛上的架構圖，請在脈絡列選定圖"),
        "system_many_diagrams": ({}, "這個系統下有多張架構圖，請在脈絡列選定要用的那一張"),
        "a1_failed": ({}, "架構設計失敗"),
        "a1_no_xml": ({}, "架構設計沒有產出圖"),
        "diagram_modified": ({}, "這張圖在處理期間被修改過，未覆寫"),
        "a3_failed": ({}, "架構檢視失敗"),
        "a3_incomplete": ({}, "架構檢視沒有完成"),
        "unavailable": ({"capability": "架構檢視"}, "架構檢視暫時無法使用"),
        "timeout": ({"capability": "架構設計"}, "架構設計逾時"),
        "expired_on_recovery": ({}, "服務重新啟動或逾時，這一項沒有完成"),
        "cost_no_estimate": ({}, "這張圖尚無估價表，可到成本頁上傳（/cost）"),
        "cost_no_advice": ({"path": "/cost?estimate=7"}, "這份估價表還沒有產生建議，可到成本頁產生（/cost?estimate=7）"),
        "cost_failed": ({}, "成本分析失敗"),
        "cost_timeout": ({}, "成本分析逾時"),
        "cost_not_found": ({}, "找不到這份估價表的建議"),
        "connection_lost": ({}, "與成本服務的連線中斷"),
        "capacity_exceeded": ({}, "同時進行中的工作已達上限，這一項沒有開始"),
        "side_effect_maybe_persisted": ({"name": "〈A〉"}, "可能已存回架構圖〈A〉"),
        "side_effect_persisted": ({"name": "〈A〉"}, "已存回架構圖〈A〉"),
        "side_effect_review_created": ({}, "已建立一份檢視紀錄"),
        "side_effect_change_record_missing": ({"side_effect": "S"}, "S（變更紀錄未寫入）"),
    }

    def test_every_phrase_has_a_case(self):
        self.assertEqual(set(self.EXPECTED), set(R.PHRASES))

    def test_each_phrase_renders_exactly(self):
        for key, (values, expected) in self.EXPECTED.items():
            with self.subTest(phrase=key):
                self.assertEqual(R.PHRASES[key].format(**values), expected)

    def test_status_code_mapping(self):
        self.assertEqual(R.failure_for_status(R.CAP_COST, 401)[1], "unauthorized")
        self.assertEqual(R.failure_for_status(R.CAP_COST, 403)[1], "forbidden")
        self.assertEqual(R.failure_for_status(R.CAP_COST, 502)[1], "capability_failed")

    def test_label_omits_missing_target_and_never_contains_the_request(self):
        self.assertEqual(R.make_label(R.CAP_REVIEW, ""), "架構檢視")
        self.assertEqual(R.make_label(R.CAP_REVIEW, "系統 #3"), "架構檢視：系統 #3")


if __name__ == "__main__":
    unittest.main()
