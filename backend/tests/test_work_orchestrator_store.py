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

from services import session_types as T
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
        T.ref_put_work_item(fields, "wi:b", "{}")
        T.ref_update_work_item(
            fields, "wi:a", '["處理中"]', "not_dispatched", '{"status":"失敗"}'
        )
        self.assertEqual(fields, snapshot)


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
