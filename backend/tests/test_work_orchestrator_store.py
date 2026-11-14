"""`U12 work-orchestrator` Step 4：資料模型層測試。

涵蓋 `unit-test-instructions.md §三` 的第一列：`SessionStore` 的三個工作項方法、
兩支 Lua 的 Python 參考實作（替身以它模擬腳本效果），以及 `U7` 新增的
`HierarchyFacade.list_diagrams_of_system`。

**替身證明不了真實原子性**（見 `tests/work_orchestrator_fakes.py` 檔頭）；
真實 Redis 上的一致性在 `backend/tests_redis/test_work_item_lua.py`（opt-in）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import json
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from services import session_types as T
from services import work_orchestrator_rules as R
from services.session_store import WorkItemPutResult
from services.hierarchy_facade import HierarchyFacade, HierarchyNotFound, mint_principal
from services.session_errors import SessionBackendUnavailable
from tests.helpers import (
    ALWAYS_VISIBLE,
    close_session,
    make_diagram,
    make_session,
    make_user,
)
from tests.test_session_store_behaviour import FakeConnectionError
from tests.work_orchestrator_fakes import SESSION_KEY, make_store


def _item(work_item_id="w1", **overrides):
    item = {
        "workItemId": work_item_id,
        "sessionKey": SESSION_KEY,
        "label": "架構設計：架構圖 #12",
        "status": "處理中",
        "capability": "architecture-design",
        "waitingOn": None,
        "failureReason": None,
        "sideEffect": "none",
        "createdAt": "2026-10-12T08:00:00+00:00",
        "estimateSetId": None,
        "dependsOn": None,
        "targetDiagramId": 12,
        "targetSystemId": None,
        "segmentId": "shared",
        "deadlineAt": "2026-10-12T08:05:00+00:00",
        "dispatchStage": "not_dispatched",
        "requestText": "加上快取層",
        "dispatchIndex": 0,
        "tags": [],
    }
    item.update(overrides)
    return item


class PutWorkItemTest(unittest.TestCase):
    def test_put_succeeds_on_a_live_session_and_is_readable(self):
        """① 建項成功，`load_work_items` 讀回同一份。"""
        store, client = make_store()
        self.assertTrue(store.put_work_item(SESSION_KEY, _item()))
        loaded = store.load_work_items(SESSION_KEY)
        self.assertEqual(list(loaded), ["w1"])
        self.assertEqual(loaded["w1"]["label"], "架構設計：架構圖 #12")
        self.assertIn("wi:w1", client.hashes[SESSION_KEY])

    def test_put_rejects_an_existing_field_without_overwriting(self):
        """② 同一個 workItemId 第二次寫入被拒，原值不被覆寫。"""
        store, _ = make_store()
        store.put_work_item(SESSION_KEY, _item())
        self.assertFalse(store.put_work_item(SESSION_KEY, _item(label="別的")))
        self.assertEqual(
            store.load_work_items(SESSION_KEY)["w1"]["label"], "架構設計：架構圖 #12"
        )

    def test_put_on_a_missing_key_is_rejected_and_does_not_create_the_key(self):
        """③ `NFR12.18`：key 不存在 → False，且 key 仍不存在（`EXISTS` 為 0）。"""
        store, client = make_store(create_key=False)
        self.assertFalse(store.put_work_item(SESSION_KEY, _item()))
        self.assertNotIn(SESSION_KEY, client.hashes)
        self.assertEqual(client._cmd_exists(SESSION_KEY), 0)

    def test_update_on_a_missing_key_is_rejected_and_does_not_create_the_key(self):
        store, client = make_store(create_key=False)
        ok = store.update_work_item(
            SESSION_KEY, "w1", ["處理中"], "not_dispatched", {"status": "失敗"}
        )
        self.assertFalse(ok)
        self.assertNotIn(SESSION_KEY, client.hashes)


class UpdateWorkItemTest(unittest.TestCase):
    def setUp(self):
        self.store, self.client = make_store()
        self.store.put_work_item(SESSION_KEY, _item())

    def _get(self):
        return self.store.load_work_items(SESSION_KEY)["w1"]

    def test_update_requires_both_status_and_dispatch_stage_to_match(self):
        """④ 比對 status 與 `dispatchStage`，任一不符即拒絕且不寫入。"""
        self.assertFalse(
            self.store.update_work_item(
                SESSION_KEY, "w1", ["等待中"], "not_dispatched", {"status": "已停掉"}
            )
        )
        self.assertFalse(
            self.store.update_work_item(
                SESSION_KEY, "w1", ["處理中"], "request_sent", {"status": "已停掉"}
            )
        )
        self.assertEqual(self._get()["status"], "處理中")
        self.assertTrue(
            self.store.update_work_item(
                SESSION_KEY, "w1", ["處理中", "等待中"], "not_dispatched",
                {"status": "已停掉"},
            )
        )
        self.assertEqual(self._get()["status"], "已停掉")

    def test_patch_only_changes_named_fields_and_keeps_estimate_set_id(self):
        """⑤ 補丁合併：`estimateSetId` 不在補丁中就不會被過期值覆寫（帶入項 4）。"""
        self.store.update_work_item(
            SESSION_KEY, "w1", ["處理中"], "not_dispatched", {"estimateSetId": 7}
        )
        # 呼叫端手上是寫入 estimateSetId **之前**讀到的那份；它只送補丁。
        self.store.update_work_item(
            SESSION_KEY, "w1", ["處理中"], "not_dispatched",
            {"dispatchStage": "request_sent"},
        )
        current = self._get()
        self.assertEqual(current["estimateSetId"], 7)
        self.assertEqual(current["dispatchStage"], "request_sent")
        self.assertEqual(current["label"], "架構設計：架構圖 #12")

    def test_null_in_patch_sets_null_and_empty_arrays_survive(self):
        """⑥ 補丁值 null → 設為 null（不是刪除欄位）；空陣列寫回仍是 `[]`。"""
        self.store.update_work_item(
            SESSION_KEY, "w1", ["處理中"], "not_dispatched",
            {"deadlineAt": None, "status": "失敗", "failureReason": "x"},
        )
        raw = json.loads(self.client.hashes[SESSION_KEY]["wi:w1"])
        self.assertIn("deadlineAt", raw)
        self.assertIsNone(raw["deadlineAt"])
        self.assertEqual(raw["tags"], [])

    def test_ttl_is_not_touched_by_put_or_update(self):
        """⑦ 兩個寫入方法都不續期（`BR52.4`：隨工作階段既有的到期時間）。"""
        self.client.ttls[SESSION_KEY] = 1234
        self.store.put_work_item(SESSION_KEY, _item("w2"))
        self.store.update_work_item(
            SESSION_KEY, "w2", ["處理中"], "not_dispatched", {"status": "完成"}
        )
        self.store.load_work_items(SESSION_KEY)
        self.assertEqual(self.client.ttls[SESSION_KEY], 1234)

    def test_scripts_are_not_retried_on_a_connection_error(self):
        """`idempotent=False`（帶入項 7）：連線錯誤不重送，結果未知交給呼叫端。"""
        self.client.calls.clear()
        self.client.fail_next.append(FakeConnectionError("reset"))
        with self.assertRaises(SessionBackendUnavailable):
            self.store.update_work_item(
                SESSION_KEY, "w1", ["處理中"], "not_dispatched", {"status": "失敗"}
            )
        self.assertEqual(
            sum(1 for c in self.client.calls if c in ("EVALSHA", "EVAL")), 1
        )

    def test_unknown_work_item_is_rejected(self):
        self.assertFalse(
            self.store.update_work_item(
                SESSION_KEY, "nope", ["處理中"], "not_dispatched", {"status": "失敗"}
            )
        )
        self.assertNotIn("wi:nope", self.client.hashes[SESSION_KEY])

    def test_session_decoding_ignores_work_item_fields(self):
        """`OPEN-N10-7`：工作項欄位不改變既有的 session 讀取。"""
        session = self.store.load(SESSION_KEY)
        self.assertEqual(set(session.segments), {"shared"})


class ReferenceImplementationPurityTest(unittest.TestCase):
    def test_reference_functions_do_not_mutate_their_input(self):
        fields = {"meta": "{}", "wi:a": json.dumps(_item("a"))}
        snapshot = dict(fields)
        T.ref_put_work_item(fields, "wi:b", "{}", "5", _TERMINAL_JSON)
        T.ref_update_work_item(
            fields, "wi:a", '["處理中"]', "not_dispatched", '{"status":"失敗"}',
            "20", _TERMINAL_JSON,
        )
        self.assertEqual(fields, snapshot)


# ---------------------------------------------------------------------------
# 合併前必修第 18 項（`OPEN-N10-3`；計畫 §六 Step 14）：工作項容量
# ---------------------------------------------------------------------------

_TERMINAL_JSON = json.dumps(sorted(R.TERMINAL_STATUSES), ensure_ascii=False, separators=(",", ":"))


def _seed(client, *items):
    """直接把工作項寫進替身的 Hash（繞過上限，只用來準備「已存在」的狀態）。"""
    for item in items:
        client.hashes[SESSION_KEY][f"wi:{item['workItemId']}"] = json.dumps(
            item, ensure_ascii=False, separators=(",", ":")
        )


def _created(minute: int) -> str:
    return f"2026-10-12T{8 + minute // 60:02d}:{minute % 60:02d}:00+00:00"


class WorkItemCapacityTest(unittest.TestCase):
    """進行中上限 5、已結束保留 20（`MAX_ACTIVE_WORK_ITEMS`／`MAX_TERMINAL_WORK_ITEMS`）。"""

    def setUp(self):
        self.store, self.client = make_store()

    def _fields(self):
        return set(f for f in self.client.hashes[SESSION_KEY] if f.startswith("wi:"))

    def test_constants_are_the_ruled_values(self):
        """使用者裁決 `[WO-MB18]`=A 的兩個數字；改它就是改容量承諾（`DEPLOY.md`）。"""
        self.assertEqual(R.MAX_ACTIVE_WORK_ITEMS, 5)
        self.assertEqual(R.MAX_TERMINAL_WORK_ITEMS, 20)

    def test_sixth_active_item_is_rejected_and_not_written(self):
        """
        @purpose 同一工作階段的第 6 筆進行中工作項被拒，且不留下任何欄位
        @given 已有 3 筆處理中、2 筆等待中
        @step 再寫入第 6 筆
        @pass 回 `CAPACITY_EXCEEDED`、`bool` 為假，Hash 內沒有該欄位
        @story US1.1
        """
        for i in range(3):
            self.assertIs(self.store.put_work_item(SESSION_KEY, _item(f"p{i}")), WorkItemPutResult.WRITTEN)
        for i in range(2):
            self.store.put_work_item(SESSION_KEY, _item(f"w{i}", status="等待中"))
        result = self.store.put_work_item(SESSION_KEY, _item("sixth"))
        self.assertIs(result, WorkItemPutResult.CAPACITY_EXCEEDED)
        self.assertFalse(result)
        self.assertNotIn("wi:sixth", self.client.hashes[SESSION_KEY])
        self.assertEqual(len(self._fields()), 5)

    def test_terminal_items_do_not_count_toward_the_active_limit(self):
        """終態（完成、失敗、已停掉）不計入；4 筆進行中 ＋ 任意多筆終態仍可再建 1 筆。"""
        _seed(
            self.client,
            *[_item(f"t{i}", status=s) for i, s in enumerate(["完成", "失敗", "已停掉"] * 4)],
        )
        for i in range(4):
            self.store.put_work_item(SESSION_KEY, _item(f"p{i}"))
        self.assertIs(self.store.put_work_item(SESSION_KEY, _item("fifth")), WorkItemPutResult.WRITTEN)
        self.assertIs(
            self.store.put_work_item(SESSION_KEY, _item("sixth")), WorkItemPutResult.CAPACITY_EXCEEDED
        )

    def test_missing_key_and_duplicate_field_still_return_rejected(self):
        """key 不存在或欄位重複仍是原本的「未寫入」，不與「已達上限」混淆。"""
        store, client = make_store(create_key=False)
        self.assertIs(store.put_work_item(SESSION_KEY, _item()), WorkItemPutResult.REJECTED)
        self.assertNotIn(SESSION_KEY, client.hashes)
        self.store.put_work_item(SESSION_KEY, _item())
        self.assertIs(self.store.put_work_item(SESSION_KEY, _item()), WorkItemPutResult.REJECTED)
        # 已達上限時重複寫同一個欄位：仍回 REJECTED（欄位存在的判定在上限之前）。
        for i in range(4):
            self.store.put_work_item(SESSION_KEY, _item(f"p{i}"))
        self.assertIs(self.store.put_work_item(SESSION_KEY, _item()), WorkItemPutResult.REJECTED)

    def test_transition_to_terminal_prunes_the_oldest_terminal_items_beyond_20(self):
        """
        @purpose 第 21 筆終態出現時刪最舊的終態項，進行中項永不被刪
        @given 20 筆終態（createdAt 由舊到新 t00..t19）、1 筆更舊的處理中項、1 筆要轉終態的處理中項
        @step 把後者轉為完成
        @pass 終態恰 20 筆、刪掉的是 t00、兩筆進行中／剛轉終態的項都還在
        @story US1.1
        """
        _seed(self.client, _item("old-active", createdAt=_created(0)))
        _seed(self.client, *[_item(f"t{i:02d}", status="完成", createdAt=_created(10 + i)) for i in range(20)])
        _seed(self.client, _item("ending", createdAt=_created(100)))
        self.assertTrue(
            self.store.update_work_item(SESSION_KEY, "ending", ["處理中"], "not_dispatched", {"status": "完成"})
        )
        fields = self._fields()
        self.assertNotIn("wi:t00", fields)
        self.assertIn("wi:t01", fields)
        self.assertIn("wi:old-active", fields)
        self.assertIn("wi:ending", fields)
        items = self.store.load_work_items(SESSION_KEY)
        self.assertEqual(sum(1 for i in items.values() if i["status"] in R.TERMINAL_STATUSES), 20)

    def test_the_item_that_just_ended_is_never_its_own_victim(self):
        """`createdAt` 是建立時間：最舊的那筆跑完時，被刪的是**其他**最舊終態項，不是它自己。"""
        _seed(self.client, _item("ancient", createdAt=_created(0)))
        _seed(self.client, *[_item(f"t{i:02d}", status="失敗", createdAt=_created(10 + i)) for i in range(20)])
        self.store.update_work_item(SESSION_KEY, "ancient", ["處理中"], "not_dispatched", {"status": "失敗"})
        fields = self._fields()
        self.assertIn("wi:ancient", fields)
        self.assertNotIn("wi:t00", fields)
        self.assertEqual(len(fields), 20)

    def test_tie_on_created_at_is_broken_by_field_name(self):
        """同一次交辦的項 `createdAt` 相同；刪除順序以欄位名決定，結果可重現。"""
        same = _created(5)
        _seed(self.client, *[_item(name, status="已停掉", createdAt=same) for name in ("c", "a", "b")])
        _seed(self.client, *[_item(f"t{i:02d}", status="完成", createdAt=_created(10 + i)) for i in range(17)])
        _seed(self.client, _item("ending", createdAt=_created(100)))
        # 20 筆終態 ＋ 本項 = 21 → 刪 1 筆：同時間的 a／b／c 中欄位名最小的 wi:a。
        self.store.update_work_item(SESSION_KEY, "ending", ["處理中"], "not_dispatched", {"status": "已停掉"})
        fields = self._fields()
        self.assertNotIn("wi:a", fields)
        self.assertIn("wi:b", fields)
        self.assertIn("wi:c", fields)

    def test_terminal_to_terminal_patches_do_not_prune(self):
        """只有「非終態 → 終態」那一次修剪；終態項的後續補丁（在途存檔收尾）不觸發。"""
        _seed(self.client, *[_item(f"t{i:02d}", status="完成", createdAt=_created(10 + i)) for i in range(21)])
        self.store.update_work_item(SESSION_KEY, "t20", ["完成"], "not_dispatched", {"sideEffect": "unknown"})
        self.assertEqual(len(self._fields()), 21)

    def test_failed_compare_does_not_prune(self):
        _seed(self.client, *[_item(f"t{i:02d}", status="完成", createdAt=_created(10 + i)) for i in range(20)])
        _seed(self.client, _item("ending", createdAt=_created(100)))
        self.assertFalse(
            self.store.update_work_item(SESSION_KEY, "ending", ["等待中"], "not_dispatched", {"status": "完成"})
        )
        self.assertEqual(len(self._fields()), 21)

    def test_ttl_is_not_touched_when_pruning(self):
        _seed(self.client, *[_item(f"t{i:02d}", status="完成", createdAt=_created(10 + i)) for i in range(20)])
        _seed(self.client, _item("ending", createdAt=_created(100)))
        self.client.ttls[SESSION_KEY] = 777
        self.store.update_work_item(SESSION_KEY, "ending", ["處理中"], "not_dispatched", {"status": "完成"})
        self.assertEqual(self.client.ttls[SESSION_KEY], 777)


# 交辦與轉終態的任意序列（`@given`）：每步是「建立 1 筆」或「把第 n 筆進行中項轉為某終態」。
_STEP = st.one_of(
    st.tuples(st.just("put"), st.sampled_from(["處理中", "等待中"])),
    st.tuples(st.just("end"), st.integers(min_value=0, max_value=10), st.sampled_from(sorted(R.TERMINAL_STATUSES))),
)


class WorkItemCapacityPropertyTest(unittest.TestCase):
    @settings(max_examples=60, deadline=None)
    @given(steps=st.lists(_STEP, min_size=1, max_size=80))
    def test_any_sequence_keeps_active_at_most_5_and_terminal_at_most_20(self, steps):
        """任意交辦與轉終態序列後，進行中 ≤ 5、終態 ≤ 20，且進行中項從不被刪。"""
        store, client = make_store()
        # 先放 18 筆較新的終態項，使短序列也會走到修剪（否則 hypothesis 產生的短序列
        # 很少累積到 20 筆終態，性質形同只驗上限；突變驗證實測過這個盲點）。
        _seed(client, *[
            _item(f"seed{i:02d}", status="完成", createdAt=_created(500 + i)) for i in range(18)
        ])
        alive_active: set = set()
        for index, step in enumerate(steps):
            if step[0] == "put":
                wid = f"x{index:03d}"
                result = store.put_work_item(
                    SESSION_KEY, _item(wid, status=step[1], createdAt=_created(index))
                )
                if result:
                    alive_active.add(wid)
            else:
                active = sorted(alive_active)
                if not active:
                    continue
                wid = active[step[1] % len(active)]
                current = store.load_work_items(SESSION_KEY)[wid]
                store.update_work_item(
                    SESSION_KEY, wid, [current["status"]], current["dispatchStage"], {"status": step[2]}
                )
                alive_active.discard(wid)
            items = store.load_work_items(SESSION_KEY)
            active_now = {k for k, v in items.items() if v["status"] not in R.TERMINAL_STATUSES}
            terminal_now = len(items) - len(active_now)
            self.assertLessEqual(len(active_now), R.MAX_ACTIVE_WORK_ITEMS)
            self.assertLessEqual(terminal_now, R.MAX_TERMINAL_WORK_ITEMS)
            self.assertEqual(active_now, alive_active)


class ListDiagramsOfSystemTest(unittest.TestCase):
    """⑧ `U7` 新增的 `list_diagrams_of_system`：擁有者／非擁有者／零張。"""

    def setUp(self):
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.bob = make_user(self.db, username="bob", role="Project_Architect")
        facade = HierarchyFacade(self.db)
        self.alice_p = mint_principal(self.alice)
        self.bob_p = mint_principal(self.bob)
        project = facade.create_project(self.alice_p, name="P")
        self.system = facade.create_system(
            self.alice_p, project_id=project.id, name="S", project_visible=ALWAYS_VISIBLE
        )
        self.empty_system = facade.create_system(
            self.alice_p, project_id=project.id, name="E", project_visible=ALWAYS_VISIBLE
        )
        self.d1 = make_diagram(self.db, owner=self.alice, title="一號")
        self.d2 = make_diagram(self.db, owner=self.alice, title="二號")
        self.unattached = make_diagram(self.db, owner=self.alice, title="未掛")
        self.d1.system_id = self.system.id
        self.d2.system_id = self.system.id
        self.db.commit()
        self.facade = facade

    def tearDown(self):
        close_session(self.db)

    def test_owner_gets_the_diagrams_of_the_system_only(self):
        result = self.facade.list_diagrams_of_system(self.alice_p, system_id=self.system.id)
        self.assertEqual(result, [(self.d1.id, "一號"), (self.d2.id, "二號")])

    def test_non_owner_gets_not_found(self):
        with self.assertRaises(HierarchyNotFound):
            self.facade.list_diagrams_of_system(self.bob_p, system_id=self.system.id)

    def test_system_without_attached_diagrams_returns_empty(self):
        """`OPEN-H11`：系統下沒有掛圖是真實可達的狀態，回空清單而非錯誤。"""
        self.assertEqual(
            self.facade.list_diagrams_of_system(self.alice_p, system_id=self.empty_system.id),
            [],
        )


if __name__ == "__main__":
    unittest.main()
