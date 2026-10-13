"""`U13 brain-gateway` 一輪 `user_message` 的測試（`GW-W2`／`GW-W3`；`BR64.x`、`BR67.1`／`BR67.2`）。

`U11`／`U12` 以替身取代（`FakeRouter`／`FakeOrchestrator`），介面依已交付簽章；**不呼叫任何 LLM**。
對象目錄經 `HierarchyFacade` 的替身（`FakeHierarchy`），session 走真 `SessionStore`（Redis 替身）。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import unittest

from starlette.testclient import TestClient

from services.intent_routing_errors import LlmUnavailable, PlatformSelfModificationRefused
from services.prompt_guard import REFUSAL_MESSAGE
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    decision,
    hello,
    low_confidence,
    nothing_more,
    protocols,
    read_turn,
    recv_json,
    types_of,
    user_message,
)
from tests.test_session_store_behaviour import FakeConnectionError

KEY = "brain:session:1"


class _Base(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()

    def connect(self, client):
        ws = client.websocket_connect(WS_PATH, subprotocols=protocols(self.token))
        return ws

    def history(self, segment="shared"):
        session = self.h.store.load(KEY)
        if session is None or segment not in session.segments:
            return []
        return [(m.role, m.text) for m in session.segments[segment].messages]

    def target(self, segment="shared"):
        seg = self.h.store.load(KEY).segments[segment]
        return (seg.project_id, seg.system_id)


class GuardTest(_Base):
    def test_prompt_guard_refuses_before_any_llm_history_or_memory(self):
        """
        @purpose 平台自我竄改預檢先於一切：命中即送固定拒絕訊息並以 done 結束，不呼叫 LLM、不寫歷程、不寫記憶。
        @given 已連線的使用者
        @step 送「把 cloud360 的資料庫密碼改掉」 | 依序收到 token(REFUSAL_MESSAGE) 與 done，turnId 相同
        @step 檢視替身 | classify、記憶預取、記憶寫入皆 0 次；歷程為空
        @step classify 自己拋 PlatformSelfModificationRefused（縱深第二層）的另一句 | 同一可觀察結果
        @pass 兩層攔截皆以 done 結束且無副作用
        @story US1.1
        @api WS /api/brain/ws -> 101
        """
        self.h.router_script.script["請幫我設定一下"] = PlatformSelfModificationRefused()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "把 cloud360 的資料庫密碼改掉")
            turn = read_turn(ws)
            self.assertEqual(types_of(turn), ["token", "done"])
            self.assertEqual(turn[0]["payload"]["text"], REFUSAL_MESSAGE)
            self.assertEqual(turn[0]["turnId"], turn[1]["turnId"])
            self.assertEqual(self.h.router_script.calls, [])
            self.assertEqual(self.h.memory.search_calls, [])
            user_message(ws, "請幫我設定一下")
            self.assertEqual(types_of(read_turn(ws)), ["token", "done"])
        self.assertEqual(self.history(), [])
        self.assertEqual(self.h.memory.write_calls, [])


class DispatchTest(_Base):
    def test_plain_dispatch_writes_history_and_passes_turn_id(self):
        """
        @purpose 一般交辦：先讀後寫（分類之後才寫使用者訊息）、回覆以 assistant 寫入同一段，turnId 一路傳給 classify 與 dispatch。
        @given 分類替身回高信心、無 referent 的意圖
        @step 送一句需求 | 收到 work_items、token、done，token 與 done 同 turnId
        @step 檢視 classify／dispatch 收到的 turn_id | 等於客戶端收到的 turnId
        @step 檢視共享段歷程 | 恰為 user 原句、assistant 回覆兩筆
        @pass 歷程與關聯鍵皆正確
        @story US1.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "畫一張架構圖")
            turn = read_turn(ws)
        self.assertEqual(types_of(turn), ["work_items", "token", "done"])
        turn_id = turn[-1]["turnId"]
        self.assertEqual(self.h.router_script.calls[0].turn_id, turn_id)
        self.assertEqual(self.h.orchestrator.dispatch_calls[0].turn_id, turn_id)
        self.assertEqual(self.history(), [("user", "畫一張架構圖"), ("assistant", "已交辦：建立架構圖")])

    def test_isolated_page_uses_its_own_segment(self):
        """
        @purpose 各頁獨立對話（FR3.2）：page=workspace 且該頁為獨立模式時，分類與交辦都用 workspace 段。
        @given 已把 workspace 切成 isolated
        @step 以 page=workspace 送一句 | done
        @step 檢視分類器與交辦的段 | 皆為 workspace；共享段不含這句
        @pass 段選擇正確
        @story US3.1
        """
        self.h.store.set_sharing_mode(KEY, "workspace", "isolated")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "加一個快取", page="workspace")
            self.assertEqual(types_of(read_turn(ws))[-1], "done")
        self.assertEqual(self.h.router_script.calls[0].segment, "workspace")
        self.assertEqual(self.h.orchestrator.dispatch_calls[0].segment_id, "workspace")
        self.assertNotIn(("user", "加一個快取"), self.history("shared"))

    def test_empty_response_and_routing_failure(self):
        """
        @purpose 零內容不得以 done 結束（EMPTY_RESPONSE）；路由失敗時先寫使用者訊息再以 INTERNAL_ERROR 結束。
        @given 第一句：交辦後 U12 未送任何 token；第二句：classify 拋 LlmUnavailable
        @step 送第一句 | error(EMPTY_RESPONSE)
        @step 送第二句 | error(INTERNAL_ERROR)，訊息為封閉表的句子；歷程含第二句 user 訊息
        @pass 兩種終止皆正確
        @story US8.1
        """
        self.h.orchestrator.reply_texts = []
        self.h.router_script.script["第二句"] = LlmUnavailable("upstream 500 secret-detail")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "第一句")
            first = read_turn(ws)
            self.assertEqual(first[-1]["payload"]["code"], "EMPTY_RESPONSE")
            user_message(ws, "第二句")
            second = read_turn(ws)
        self.assertEqual(second[-1]["payload"]["code"], "INTERNAL_ERROR")
        self.assertEqual(second[-1]["payload"]["message"], "大腦暫時無法判讀這句話，請再說一次")
        self.assertIn(("user", "第二句"), self.history())

    def test_invalid_messages_never_reach_classify(self):
        """
        @purpose 身分只來自連線：夾帶 userId 或 turnId、缺 page、空白、超長的訊息皆以 INVALID_REQUEST 拒絕且不呼叫分類。
        @given 已連線的使用者
        @step 依序送五種不合法訊息 | 各收到 error(INVALID_REQUEST)，連線保留
        @step 最後送一則合法訊息 | done
        @pass 不合法者 classify 0 次，合法者照常
        @story US8.1
        """
        bad = [
            {"v": 1, "type": "user_message", "payload": {"text": "x", "page": "entry", "userId": 2}},
            {"v": 1, "type": "user_message", "turnId": "t", "payload": {"text": "x", "page": "entry"}},
            {"v": 1, "type": "user_message", "payload": {"text": "x"}},
        ]
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            for frame in bad:
                ws.send_json(frame)
                self.assertEqual(recv_json(ws)["payload"]["code"], "INVALID_REQUEST")
            user_message(ws, "   ")
            self.assertEqual(read_turn(ws)[-1]["payload"]["code"], "INVALID_REQUEST")
            user_message(ws, "長" * 4001)
            self.assertEqual(read_turn(ws)[-1]["payload"]["message"], "訊息太長，請縮短後再送出")
            self.assertEqual(self.h.router_script.calls, [])
            user_message(ws, "正常的一句")
            self.assertEqual(types_of(read_turn(ws))[-1], "done")

    def test_redis_failure_after_ready_keeps_connection(self):
        """
        @purpose [GW3]=A 後半：ready 之後 Redis 不可用 → 該輪 error(INTERNAL_ERROR)「工作階段暫時無法存取」，連線保留，恢復後照常。
        @given 已 ready；下一則訊息的 load 連續失敗
        @step 送一句 | 收到 error，訊息為「工作階段暫時無法存取，請稍後再試」，未收到關閉碼
        @step Redis 恢復後再送一句 | done
        @pass 連線未被關閉且可恢復
        @story US8.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            self.h.redis.fail_next = [FakeConnectionError("down")] * 3
            user_message(ws, "第一句")
            turn = read_turn(ws)
            self.assertEqual(turn[-1]["payload"]["message"], "工作階段暫時無法存取，請稍後再試")
            self.h.redis.fail_next = []
            user_message(ws, "第二句")
            self.assertEqual(types_of(read_turn(ws))[-1], "done")


class ClarifyTest(_Base):
    def test_intent_clarify_select_and_none(self):
        """
        @purpose 低於門檻送 clarify(kind=intent)；選定候選後沿用同一 turnId 交辦並以 done 結束；選「都不是」安靜結束，不送任何訊息。
        @given 第一句、第二句皆低信心
        @step 送第一句 | clarify，kind=intent，候選 c1
        @step 選 c1 | 收到 work_items、token、done，token 與 done 的 turnId 等於 clarify 的 turnId
        @step 送第二句後選 null | 之後沒有任何訊息（無 work_target、work_items、終止事件）
        @pass 兩條路徑皆符合 AC1.2.2／AC1.2.3
        @story US1.2
        """
        self.h.router_script.default = low_confidence("建一張架構圖")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "弄一下")
            clarify = read_turn(ws)[-1]
            self.assertEqual((clarify["type"], clarify["payload"]["kind"]), ("clarify", "intent"))
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "c1"}})
            rest = read_turn(ws)
            self.assertEqual(types_of(rest), ["work_items", "token", "done"])
            self.assertEqual({m["turnId"] for m in rest[1:]}, {clarify["turnId"]})
            user_message(ws, "再弄一下")
            read_turn(ws)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": None}})
            self.assertTrue(nothing_more(ws))
        self.assertEqual(len(self.h.orchestrator.dispatch_calls), 1)

    def test_scan_after_select_uses_longest_name_and_always_asks(self):
        """
        @purpose 反問選定意圖後以原句掃描對象：只認最長完整名稱（「改訂單系統的圖」不得把專案「訂單」也算進來），
                 且命中一律以對象反問確認，不靜默改動作業對象（帶入項 1）。
        @given 目錄：專案「電商」含系統「訂單系統」、專案「訂單」；分類低信心
        @step 送「改訂單系統的圖」並選定意圖候選 | 收到 clarify，kind=target，恰 1 個候選（訂單系統）
        @step 此時檢視作業對象與交辦 | 作業對象未變、dispatch 0 次
        @step 選定該對象 | 收到 work_target（系統 10）、work_items、token、done；dispatch 1 次
        @pass 掃描結果唯一且需確認
        @story US1.2
        """
        self.h.hierarchy.projects = [(1, "電商"), (2, "訂單")]
        self.h.hierarchy.systems = {1: [(10, "訂單系統")]}
        self.h.router_script.default = low_confidence("改架構圖")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "改訂單系統的圖")
            read_turn(ws)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "c1"}})
            clarify = read_turn(ws)[-1]
            self.assertEqual(clarify["payload"]["kind"], "target")
            self.assertEqual([c["label"] for c in clarify["payload"]["candidates"]], ["訂單系統（專案：電商）"])
            self.assertEqual(self.h.orchestrator.dispatch_calls, [])
            self.assertEqual(self.target(), (None, None))
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "target-1"}})
            rest = read_turn(ws)
        self.assertEqual(types_of(rest), ["work_target", "work_items", "token", "done"])
        self.assertEqual(rest[0]["payload"]["systemId"], "10")
        self.assertEqual(len(self.h.orchestrator.dispatch_calls), 1)

    def test_generic_single_hit_still_asks_and_no_hit_dispatches(self):
        """
        @purpose 單一命中也要反問（通用名稱如「系統」不得被靜默當成對象）；原句未點名任何對象則依當前作業對象交辦。
        @given 目錄含系統「系統」；分類低信心
        @step 送「這個系統要加快取」並選定意圖 | clarify(kind=target)；set_work_target 0 次、dispatch 0 次
        @step 選「都不是」，再送「加快取」並選定意圖 | 直接交辦（work_items、token、done）
        @pass 兩案皆如預期
        @story US1.2
        """
        self.h.hierarchy.projects = [(1, "電商")]
        self.h.hierarchy.systems = {1: [(10, "系統")]}
        self.h.router_script.default = low_confidence("加快取")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "這個系統要加快取")
            read_turn(ws)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "c1"}})
            self.assertEqual(read_turn(ws)[-1]["payload"]["kind"], "target")
            self.assertEqual(self.h.orchestrator.dispatch_calls, [])
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": None}})
            user_message(ws, "加快取")
            read_turn(ws)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "c1"}})
            self.assertEqual(types_of(read_turn(ws)), ["work_items", "token", "done"])


class ReferentTest(_Base):
    def test_unselected_unique_system_name_updates_target_then_dispatches(self):
        """
        @purpose AC1.1.5 主情境：脈絡列未選定、句中為系統名稱且在目錄中唯一 → 先更新作業對象（扇出 work_target）再交辦。
        @given 兩個專案，其一含唯一系統「支付」；分類回 referent=支付
        @step 送「改支付的架構」 | 依序 work_target（systemId=21）、work_items、token、done
        @step 檢視 session | 共享段作業對象為 (2, 21)
        @pass 對象更新且已交辦
        @story US1.1
        """
        self.h.hierarchy.projects = [(1, "電商"), (2, "金流")]
        self.h.hierarchy.systems = {1: [(10, "訂單")], 2: [(21, "支付")]}
        self.h.router_script.default = decision(referent="支付")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "改支付的架構")
            turn = read_turn(ws)
        self.assertEqual(types_of(turn), ["work_target", "work_items", "token", "done"])
        self.assertEqual(turn[0]["payload"]["systemId"], "21")
        self.assertEqual(self.target(), (2, 21))

    def test_ambiguous_referent_asks_and_selection_dispatches_all_intents(self):
        """
        @purpose 同名系統分屬不同專案時不得交辦給舊對象：改送 clarify(kind=target)；選定後以原判定（全部意圖）交辦。
        @given 兩個專案各有系統「訂單」；分類回兩個意圖，referent 皆為「訂單」
        @step 送一句 | clarify(kind=target)，2 個候選，標籤含專案名
        @step 選 target-2 | work_target（系統 20）、work_items、token、done；dispatch 收到 2 個意圖
        @pass 反問後才交辦且意圖完整
        @story US1.1
        """
        self.h.hierarchy.projects = [(1, "電商"), (2, "金流")]
        self.h.hierarchy.systems = {1: [(10, "訂單")], 2: [(20, "訂單")]}
        from services.intent_routing_types import Intent

        self.h.router_script.default = decision("architecture-design", "訂單", Intent("well-architected-review", "訂單"))
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "檢查並改訂單")
            clarify = read_turn(ws)[-1]
            self.assertEqual(clarify["payload"]["kind"], "target")
            self.assertEqual(len(clarify["payload"]["candidates"]), 2)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "target-2"}})
            rest = read_turn(ws)
        self.assertEqual(rest[0]["payload"]["systemId"], "20")
        self.assertEqual(len(self.h.orchestrator.dispatch_calls[0].decision.intents), 2)

    def test_not_found_and_conflicting_referents_reply_without_dispatch(self):
        """
        @purpose BR64.11 (b)(c)：零筆相符與多個意圖指向不同對象都不交辦，只回固定句型；歷程恰增加兩筆、作業對象不變、不寫記憶。
        @given 目錄只有「電商」；第一句 referent「不存在」，第二句兩個意圖 referent 不同
        @step 送第一句 | token「找不到名為「不存在」的系統或專案…」、done
        @step 送第二句 | token「這句話提到了不同的對象…」、done
        @step 檢視 | dispatch 0 次、歷程 4 筆、作業對象仍為空、記憶寫入 0 次
        @pass 兩案皆無副作用
        @story US1.1
        """
        from services.intent_routing_types import Intent

        self.h.hierarchy.projects = [(1, "電商")]
        self.h.router_script.script["第一句"] = decision(referent="不存在")
        self.h.router_script.script["第二句"] = decision("architecture-design", "電商", Intent("cost-finops", "金流"))
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "第一句")
            first = read_turn(ws)
            user_message(ws, "第二句")
            second = read_turn(ws)
        self.assertTrue(first[0]["payload"]["text"].startswith("找不到名為「不存在」"))
        self.assertTrue(second[0]["payload"]["text"].startswith("這句話提到了不同的對象"))
        self.assertEqual(self.h.orchestrator.dispatch_calls, [])
        self.assertEqual(len(self.history()), 4)
        self.assertEqual(self.target(), (None, None))
        self.assertEqual(self.h.memory.write_calls, [])

    def test_more_than_fifty_projects(self):
        """
        @purpose 專案數超過 50：未選定時句中確實指名的系統無法解析 → 回「專案太多…」（不得回不實的「找不到」）；
                 已選定專案時照常比對該專案的系統並交辦；未指名對象時照常交辦。
        @given 51 個專案；專案 51 含系統「支付」；分類回 referent=支付
        @step 未選定時送一句 | token 恰為「專案太多，請先在脈絡列選定專案」，list_systems 0 次
        @step 選定專案 51 後再送一句 | work_target（系統 5101）、…、done；list_systems 1 次
        @step 送 referent 為 null 的一句 | 直接交辦
        @pass 三案皆如預期
        @story US1.1
        """
        self.h.hierarchy.projects = [(i, f"專案{i}") for i in range(1, 52)]
        self.h.hierarchy.systems = {51: [(5101, "支付")]}
        self.h.router_script.script["改支付"] = decision(referent="支付")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "改支付")
            first = read_turn(ws)
            self.assertEqual(first[0]["payload"]["text"], "專案太多，請先在脈絡列選定專案")
            self.assertEqual(self.h.hierarchy.list_systems_calls, 0)
            ws.send_json({"v": 1, "type": "set_work_target", "payload": {"projectId": "51", "systemId": None, "diagramId": None, "segment": "shared"}})
            recv_json(ws)
            user_message(ws, "改支付")
            second = read_turn(ws)
            self.assertEqual(second[0]["payload"]["systemId"], "5101")
            self.assertEqual(self.h.hierarchy.list_systems_calls, 1)
            user_message(ws, "加快取")
            self.assertEqual(types_of(read_turn(ws)), ["work_items", "token", "done"])

    def test_selected_project_truncated_scan_without_hit_dispatches_current_target(self):
        """
        @purpose 偏離 D6（使用者 2026-10-14 核可）：專案 > 50、脈絡列**已選定**專案時，反問選定意圖後原句掃描零命中 → 照常交辦給
                 目前作業對象（不回「專案太多」）。已知殘留：點名的是其他專案的系統時，因目錄截斷不在掃描範圍內，同樣交辦給目前對象。
        @given 51 個專案；已選定專案 51（其系統「支付」在目錄內）；專案 1 的系統「訂單」不在截斷後的目錄內；分類低信心
        @step 送「改訂單」並選定意圖 | 直接交辦（work_items、token、done），沒有對象反問、沒有「專案太多」
        @step 檢視交辦時的作業對象 | 仍為專案 51
        @pass 行為鎖定為有意的決定
        @story US1.2
        """
        self.h.hierarchy.projects = [(i, f"專案{i}") for i in range(1, 52)]
        self.h.hierarchy.systems = {1: [(101, "訂單")], 51: [(5101, "支付")]}
        self.h.router_script.default = low_confidence("改架構")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            ws.send_json({"v": 1, "type": "set_work_target", "payload": {"projectId": "51", "systemId": None, "diagramId": None, "segment": "shared"}})
            recv_json(ws)
            user_message(ws, "改訂單")
            read_turn(ws)
            ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "c1"}})
            self.assertEqual(types_of(read_turn(ws)), ["work_items", "token", "done"])
        self.assertEqual(self.target(), (51, None))

    def test_unexpected_error_in_a_message_keeps_connection(self):
        """
        @purpose 連線建立後的未預期例外 → 封閉表的 error(INTERNAL_ERROR)，連線保留，log 只含例外類別名（審查 R-03；[GW3]=A）。
        @given set_sharing_mode 的處理拋出含標記字串的 RuntimeError
        @step 送 set_sharing_mode | error(INTERNAL_ERROR)「處理時發生錯誤，請再說一次」
        @step 再送一句交辦 | done
        @pass 連線保留且無洩漏
        @story US8.1
        """
        async def boom(conn, payload):
            raise RuntimeError("SECRET-MARKER")

        self.h.gw._on_set_sharing_mode = boom
        with self.assertLogs("cloud360.brain_gateway", level="WARNING") as logs:
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                ws.send_json({"v": 1, "type": "set_sharing_mode", "payload": {"mode": "isolated", "scope": "workspace"}})
                err = recv_json(ws)
                self.assertEqual((err["payload"]["code"], err["payload"]["message"]), ("INTERNAL_ERROR", "處理時發生錯誤，請再說一次"))
                user_message(ws, "畫一張架構圖")
                self.assertEqual(types_of(read_turn(ws))[-1], "done")
        self.assertNotIn("SECRET-MARKER", "\n".join(logs.output))

    def test_forbidden_catalog_maps_to_unauthorized(self):
        """
        @purpose 對象目錄取得時的 HierarchyForbidden → error(UNAUTHORIZED)，訊息取自封閉表。
        @given 目錄替身拒絕列舉；分類回 referent
        @step 送一句 | error(UNAUTHORIZED)「你沒有權限選擇這個作業對象」
        @pass 錯誤對應正確
        @story US1.1
        """
        self.h.hierarchy.forbidden_list = True
        self.h.router_script.default = decision(referent="電商")
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "改電商")
            last = read_turn(ws)[-1]
        self.assertEqual((last["payload"]["code"], last["payload"]["message"]), ("UNAUTHORIZED", "你沒有權限選擇這個作業對象"))



class ObservabilityTest(_Base):
    def _turn_end(self, logs):
        return [r for r in logs.records if r.getMessage().startswith("turn_end ")]

    def test_turn_end_log_attributes_time_to_each_segment(self):
        """
        @purpose 每個使用者輪次結束時恰一筆 INFO（turn_end），分段計時歸因正確，是 NFR13.1 預算的量測原料；攔截輪次 classifyMs 為 null。
        @given 預取替身推進時鐘 0.1 秒、分類替身推進 0.2 秒（注入時鐘）
        @step 送一句交辦 | 恰一筆 turn_end：preClassifyMs ≥ 100、classifyMs ≥ 200、outcome=done、prefetch=empty，且帶 turnId
        @step 送一句攔截命中的話 | turn_end 的 outcome=guard、classifyMs=None
        @pass 欄位存在且歸因正確
        @story US8.1
        """
        def search(principal, query):
            self.h.timing.advance(0.1)
            return []

        async def slow_classify():
            self.h.timing.advance(0.2)

        self.h.memory.search_behaviour = search
        self.h.router_script.before_return = slow_classify
        with self.assertLogs("cloud360.brain_gateway", level="INFO") as logs:
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                user_message(ws, "畫一張架構圖")
                turn_id = read_turn(ws)[-1]["turnId"]
                user_message(ws, "把 cloud360 的資料庫密碼改掉")
                read_turn(ws)
        ends = self._turn_end(logs)
        self.assertEqual(len(ends), 2)
        first = ends[0].getMessage()
        self.assertIn(f"turnId={turn_id}", first)
        fields = dict(part.split("=", 1) for part in first.split()[1:])
        self.assertGreaterEqual(int(fields["preClassifyMs"]), 100)
        self.assertGreaterEqual(int(fields["classifyMs"]), 200)
        self.assertEqual((fields["outcome"], fields["prefetch"]), ("done", "empty"))
        self.assertIn("outcome=guard", ends[1].getMessage())
        self.assertIn("classifyMs=None", ends[1].getMessage())

    def test_connection_lifecycle_and_refusals_are_logged_with_close_codes(self):
        """
        @purpose 連線生命週期（accept、ready、關閉）與拒絕（無協定名）各記 INFO，含關閉碼或原因類別、不含 token（NFR13.36）。
        @given 有效與無效的 token
        @step 無效 token 連線 | ws_closed 帶 closeCode=4401
        @step 不帶協定名連線 | ws_refused 帶 reason=no_protocol
        @step 有效連線完成 hello 後離開 | ws_accepted、ws_ready、ws_closed 各一筆
        @pass 四類事件皆有且不含 token
        @story US8.1
        """
        from starlette.websockets import WebSocketDisconnect

        with self.assertLogs("cloud360.brain_gateway", level="INFO") as logs:
            with TestClient(self.h.app) as client:
                with client.websocket_connect(WS_PATH, subprotocols=protocols("bad-token")) as ws:
                    recv_json(ws)
                with self.assertRaises(WebSocketDisconnect):
                    with client.websocket_connect(WS_PATH, subprotocols=["bearer." + self.token]):
                        pass
                with self.connect(client) as ws:
                    hello(ws)
        joined = "\n".join(r.getMessage() for r in logs.records)
        self.assertIn("closeCode=4401", joined)
        self.assertIn("ws_refused reason=no_protocol", joined)
        for event in ("ws_accepted", "ws_ready", "ws_closed"):
            self.assertIn(event, joined)
        self.assertNotIn(self.token, joined)


class FirstContentTest(_Base):
    def test_first_token_is_sent_before_dispatch_returns_and_episodic_does_not_delay_done(self):
        """
        @purpose 第一則內容不被尾段工作延後（NFR13.2）：U12 交來的 token 收到即送，不等 dispatch 回傳；episodic 寫入在 done 之後於背景進行。
        @given dispatch 替身先送一則 token 再等待一個由測試控制的事件；記憶寫入替身阻塞直到測試放行
        @step 送一句 | 1 秒內收到 token，此時 dispatch 尚未回傳
        @step 放行 dispatch | 收到 done，此時記憶寫入仍在阻塞中
        @step 放行寫入 | 寫入恰 1 次
        @pass 兩種尾段工作都不延後使用者看到的內容
        @story US8.1
        """
        import asyncio
        import threading
        import time

        release_dispatch = asyncio.Event()
        write_gate = threading.Event()
        self.h.orchestrator.reply_texts = []

        async def emit_then_wait(sink, turn_id):
            from services.brain_ws_contract import TokenPayload

            await sink.emit_in_turn(turn_id, [TokenPayload(text="已收到，處理中")])
            await release_dispatch.wait()

        self.h.orchestrator.dispatch_hook = emit_then_wait
        self.h.memory.write_behaviour = lambda principal, kind: write_gate.wait(5)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "畫一張架構圖")
            self.assertEqual(recv_json(ws)["type"], "work_items")
            self.assertEqual(recv_json(ws, timeout=1)["type"], "token")
            client.portal.call(release_dispatch.set)
            self.assertEqual(recv_json(ws, timeout=1)["type"], "done")
            self.assertFalse(write_gate.is_set())
            write_gate.set()
            deadline = time.time() + 2
            while not self.h.memory.write_calls and time.time() < deadline:
                time.sleep(0.01)
        self.assertEqual(len(self.h.memory.write_calls), 1)


class RestartTest(_Base):
    def test_state_survives_gateway_rebuild_through_redis(self):
        """
        @purpose 行程內不保存會話狀態（NFR4／NFR13.31）：重建閘道（模擬重啟）後，新連線由 Redis 取回與重建前相同的共享模式、作業對象與工作項。
        @given 一條連線設定作業對象、把 workspace 切成獨立對話、交辦一項
        @step 關閉連線並重建閘道元件（Redis 替身沿用） | —
        @step 新連線完成 hello | sharing_mode、work_target、work_items 與重建前最後一次扇出的值逐欄相同
        @pass 狀態完整還原
        @story US2.1
        """
        self.h.hierarchy.projects = [(3, "電商")]
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            ws.send_json({"v": 1, "type": "set_work_target", "payload": {"projectId": "3", "systemId": None, "diagramId": None, "segment": "shared"}})
            target_before = recv_json(ws)
            ws.send_json({"v": 1, "type": "set_sharing_mode", "payload": {"mode": "isolated", "scope": "workspace"}})
            mode_before = recv_json(ws)
            recv_json(ws)
            user_message(ws, "畫一張架構圖")
            items_before = read_turn(ws)[0]
        self.h.rebuild()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            snapshot = hello(ws)
        modes = {m["payload"]["scope"]: m["payload"] for m in snapshot if m["type"] == "sharing_mode"}
        targets = {m["payload"]["segment"]: m["payload"] for m in snapshot if m["type"] == "work_target"}
        self.assertEqual(modes["workspace"], mode_before["payload"])
        self.assertEqual(targets["shared"], target_before["payload"])
        self.assertEqual(snapshot[-1]["payload"], items_before["payload"])


if __name__ == "__main__":
    unittest.main()
