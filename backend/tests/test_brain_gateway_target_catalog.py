"""閘道在 `classify` 前把使用者可見的專案／系統名稱交給 Decisions 路由（ADR-0024）。

`FakeRouter.needs_target_catalog` 與 `IntentRouter.needs_target_catalog` 同名同義：
Decisions port 為真、工具呼叫 port（本機 claude-code）為假。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import unittest

from starlette.testclient import TestClient

from tests.brain_gateway_fakes import WS_PATH, Harness, hello, protocols, read_turn, types_of, user_message

KEY = "brain:session:1"


class TargetCatalogTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.h.user("alice")
        self.token = self.h.token("alice")
        self.h.hierarchy.projects = [(1, "電商"), (2, "金流")]
        self.h.hierarchy.systems = {1: [(10, "電商前台系統")], 2: [(21, "支付")]}

    def tearDown(self):
        self.h.close()

    def _send(self, text):
        with TestClient(self.h.app) as client, client.websocket_connect(
            WS_PATH, subprotocols=protocols(self.token)
        ) as ws:
            hello(ws)
            user_message(ws, text)
            return read_turn(ws)

    def test_visible_names_reach_a_router_that_needs_them(self):
        """
        @purpose Decisions 路由需要 named_target 的選項：閘道在分類前把可見的專案與系統名稱交給 classify。
        @given 兩個專案、各一個系統；路由替身宣告需要目錄
        @step 送一句 | classify 收到四個名稱，順序同目錄（專案後緊接其系統）
        @pass 名稱來自與交辦相同的目錄來源
        @story US6.1
        """
        self.h.router_script.needs_target_catalog = True
        self._send("電商前台系統每個月要花多少")
        self.assertEqual(
            self.h.router_script.calls[0].target_catalog, ("電商", "電商前台系統", "金流", "支付")
        )

    def test_tool_calling_router_gets_no_catalog_and_no_extra_query(self):
        self._send("畫一張架構圖")
        self.assertIsNone(self.h.router_script.calls[0].target_catalog)
        self.assertEqual(self.h.hierarchy.list_projects_calls, 0)

    def test_catalog_failure_ends_the_turn_like_a_routing_failure(self):
        """
        @purpose 目錄取不到時不帶空目錄硬跑（那會把指名別的系統的句子交辦給目前對象）：本輪以 error 結束，且先寫使用者訊息。
        @given 路由替身需要目錄；目錄替身拒絕列舉
        @step 送一句 | 最後一則為 error；classify 未被呼叫；歷程含這句 user 訊息
        @pass 失敗大聲、不靜默降級
        """
        self.h.router_script.needs_target_catalog = True
        self.h.hierarchy.forbidden_list = True
        turn = self._send("改金流")
        self.assertEqual(types_of(turn)[-1], "error")
        self.assertEqual(self.h.router_script.calls, [])
        messages = self.h.store.load(KEY).segments["shared"].messages
        self.assertEqual([(m.role, m.text) for m in messages], [("user", "改金流")])


if __name__ == "__main__":
    unittest.main()
