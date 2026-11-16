"""`AC6.1.1`：第二輪以指涉詞（「那張圖」）指向上一輪的架構圖時，作用在**該張**圖上。

build-and-test 第三輪（2026-11-14，cross-unit 閘門指派落空項）。查證結論：

- 大腦的架構設計能力**只改作業對象那張既有的圖**（`work_orchestrator._execute_architecture`：
  `_resolve_single_diagram` → `get_diagram` → `generate_architecture` → PUT 回同一張），從不另建新圖；
  工作區產出或開啟的圖則由前端 `useWorkspaceTargetSync` 送 `set_work_target` 設為作業對象。所以
  「第一輪產出的那張圖」就是該段的作業對象，第二輪依作業對象交辦即作用在同一張。
- **缺口**：模型把「那張圖」填進 `referent` 時，閘道的 `refers_to_current_target` 只認「這」系列指示詞
  （`DEICTIC_REFERENTS` 有「這張圖」沒有「那張圖」），於是落到目錄比對 → 回「找不到名為「那張圖」」，
  AC6.1.1 在這條路徑上不成立。修法：補「那」系列指示詞。

**突變驗證 M11**（結果記於 `build-and-test/local-verify-fixes.md` 第三輪）：把「那」系列從
`DEICTIC_REFERENTS` 移除 → 本檔案例 1、2 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from services import brain_gateway_rules as R
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    decision,
    hello,
    protocols,
    read_turn,
    recv_json,
    types_of,
    user_message,
)

DIAGRAM_ID = 100


class FollowUpSameDiagramTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.addCleanup(self.h.close)
        self.h.user("alice")
        self.token = self.h.token("alice")
        self.h.hierarchy.projects = [(1, "電商")]
        self.h.hierarchy.systems = {1: [(10, "電商前台系統")]}
        self.h.hierarchy.names_by_triple = {
            (1, 10, DIAGRAM_ID): {"projectName": "電商", "systemName": "電商前台系統", "diagramName": "前台架構"}
        }

    def _two_rounds(self, second_referent):
        with TestClient(self.h.app) as client, client.websocket_connect(
            WS_PATH, subprotocols=protocols(self.token)
        ) as ws:
            hello(ws)
            ws.send_json(
                {
                    "v": 1,
                    "type": "set_work_target",
                    "payload": {"projectId": "1", "systemId": "10", "diagramId": str(DIAGRAM_ID), "segment": "shared"},
                }
            )
            self.assertEqual(recv_json(ws)["type"], "work_target")
            self.h.router_script.default = decision("architecture-design", None)
            user_message(ws, "幫我畫電商前台的架構，加上快取層")
            first = read_turn(ws)
            self.h.router_script.default = decision("architecture-design", second_referent)
            user_message(ws, "把那張圖的資料庫換成 Aurora")
            second = read_turn(ws)
        return first, second

    def _assert_both_rounds_on_the_same_diagram(self, first, second):
        self.assertIn("work_items", types_of(first))
        self.assertIn("work_items", types_of(second))
        for m in second:
            if m["type"] == "token":
                self.assertNotIn("找不到名為", m["payload"].get("text") or "")
        calls = self.h.orchestrator.dispatch_calls
        self.assertEqual(len(calls), 2, "兩輪都應交辦")
        targets = [c.session.segments[c.segment_id].diagram_id for c in calls]
        self.assertEqual(targets, [DIAGRAM_ID, DIAGRAM_ID], "第二輪必須作用在同一張圖")

    def test_that_diagram_referent_acts_on_the_same_diagram(self):
        """
        @purpose AC6.1.1：第一輪作用於某張架構圖後，第二輪說「把那張圖的資料庫換成 Aurora」且模型把「那張圖」填成 referent，系統仍作用在該張圖、不需重新指定
        @given 作業對象為專案 1／系統 10／架構圖 100；第一輪分類 architecture-design、未指名；第二輪分類 architecture-design、referent「那張圖」
        @step 送第一句 | work_items（交辦）
        @step 送「把那張圖的資料庫換成 Aurora」 | work_items（交辦），沒有「找不到名為」
        @pass dispatch 2 次，兩次交辦時該段的 diagram_id 都是 100
        @story US6.1
        @api WS /api/brain/ws -> 101
        """
        first, second = self._two_rounds("那張圖")
        self._assert_both_rounds_on_the_same_diagram(first, second)

    def test_that_family_deictics_are_current_target(self):
        """
        @purpose 「那」系列指示詞（那張圖、那張架構圖、那個系統…）與「這」系列同樣視為目前作業對象
        @given 目前作業對象為專案 1／系統 10
        @step 對每個「那」系列說法呼叫 refers_to_current_target | 皆為 True
        @pass 全部成立；真正的名稱（如「支付系統」）仍為 False
        @story US6.1
        """
        current = R.CurrentTarget(project_id=1, system_id=10, project_name="電商", system_name="電商前台系統")
        for referent in ("那張圖", "那張架構圖", "那個架構圖", "那份架構圖", "那個系統", "那個專案", "那個", "那張"):
            with self.subTest(referent=referent):
                self.assertTrue(R.refers_to_current_target(referent, current))
        self.assertFalse(R.refers_to_current_target("支付系統", current))

    def test_unnamed_follow_up_acts_on_the_same_diagram(self):
        """
        @purpose AC6.1.1 的另一條路徑：模型未填 referent 時，第二輪依作業對象交辦到同一張圖
        @given 同上；第二輪 referent 為 None
        @step 送兩句 | 兩輪皆交辦
        @pass 兩次交辦時該段的 diagram_id 都是 100
        @story US6.1
        @api WS /api/brain/ws -> 101
        """
        first, second = self._two_rounds(None)
        self._assert_both_rounds_on_the_same_diagram(first, second)


if __name__ == "__main__":
    unittest.main()
