"""`U13 brain-gateway` 扇出與推播測試（`BR63.x`、`BR65.x`；`AC7.1.1`–`AC7.1.3`；`NFR13.22`、`NFR13.26`、`NFR13.30`）。

`GatewaySink` 由 `U12` 呼叫；本檔以 `TestClient.portal` 在 app 的事件迴圈上直接呼叫 sink（模擬 `U12` 的背景工作）。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import asyncio
import time
import unittest

from starlette.testclient import TestClient

from services import brain_gateway as G
from services.brain_ws_contract import TokenPayload, WorkItemsPayload, WsServerMessageType
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    hello,
    nothing_more,
    protocols,
    read_turn,
    recv_json,
    types_of,
    user_message,
)

KEY_A = "brain:session:1"


def _items_marker(label: str) -> WorkItemsPayload:
    return WorkItemsPayload(
        items=[{"workItemId": label, "label": label, "status": "處理中", "capability": "architecture-design",
                "waitingOn": None, "failureReason": None, "sideEffect": "none"}]
    )


class _Base(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.h.user("alice")
        self.h.user("bob")
        self.a = self.h.token("alice")
        self.b = self.h.token("bob")

    def tearDown(self):
        self.h.close()

    def push(self, client, key, payloads, segment=None):
        sink = G.GatewaySink(self.h.gw, key, segment_id=segment)
        client.portal.call(sink.emit_turn, payloads)


class FanoutTest(_Base):
    def test_state_messages_reach_all_tabs_but_tokens_only_the_origin(self):
        """
        @purpose 狀態訊息扇出給同一使用者的全部連線（同一作業對象跨頁一致）；本輪 token 只進發起它的那一條。
        @given 同一使用者兩條連線 A1、A2
        @step A1 送一句交辦 | A1 收到 work_items、token、done
        @step 讀 A2 | A2 只收到 work_items，沒有 token 或 done
        @pass 扇出與本輪送出的範圍皆正確
        @story US2.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a2:
                hello(a1)
                hello(a2)
                user_message(a1, "畫一張架構圖")
                self.assertEqual(types_of(read_turn(a1)), ["work_items", "token", "done"])
                self.assertEqual(recv_json(a2)["type"], "work_items")
                self.assertTrue(nothing_more(a2))

    def test_push_goes_only_to_the_dispatchers_connections(self):
        """
        @purpose AC7.1.1／AC7.1.3：背景完成、失敗、逾時的推播只送給交辦者本人的全部連線；別人收不到。AC7.1.2：失敗與逾時的
                 句型原樣轉送、可分辨。
        @given Alice 兩條連線、Bob 一條
        @step 對 Alice 的 key 推送「完成」「失敗：A1 回傳錯誤」「逾時：超過 10 分鐘」三輪 | Alice 兩條各收到三輪，每輪 token → done、新 turnId
        @step 讀 Bob | 沒有任何訊息
        @pass 推播範圍與文字皆正確
        @story US7.1
        """
        texts = ["完成：架構圖已更新", "失敗：A1 回傳錯誤", "逾時：超過 10 分鐘"]
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a2, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.b)) as b1:
                for ws in (a1, a2, b1):
                    hello(ws)
                for t in texts:
                    self.push(client, KEY_A, [TokenPayload(text=t)])
                for ws in (a1, a2):
                    got = [read_turn(ws) for _ in texts]
                    self.assertEqual([types_of(g) for g in got], [["token", "done"]] * 3)
                    self.assertEqual([g[0]["payload"]["text"] for g in got], texts)
                    self.assertEqual(len({g[0]["turnId"] for g in got}), 3)
                    for g in got:
                        self.assertEqual(g[0]["turnId"], g[1]["payload"]["turnId"])
                self.assertTrue(nothing_more(b1))

    def test_push_with_known_segment_is_written_to_history(self):
        """
        @purpose 段已知的推播以 assistant 寫入該段歷程，使下一輪的「剛才那個」看得到；段不明（復原掃描）不寫。
        @given 一條連線
        @step 以段 shared 推送一則、以段 None 推送一則 | 兩則皆送達
        @step 檢視共享段歷程 | 只含第一則
        @pass 歷程寫入範圍正確
        @story US7.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1:
                hello(a1)
                self.h.store.append_message(KEY_A, "shared", "user", "先有一段")
                self.push(client, KEY_A, [TokenPayload(text="有段的推播")], segment="shared")
                self.push(client, KEY_A, [TokenPayload(text="沒段的推播")], segment=None)
                read_turn(a1)
                read_turn(a1)
                deadline = time.time() + 2
                while time.time() < deadline:
                    texts = [m.text for m in self.h.store.load(KEY_A).segments["shared"].messages]
                    if "有段的推播" in texts:
                        break
                    time.sleep(0.02)
        self.assertIn("有段的推播", texts)
        self.assertNotIn("沒段的推播", texts)


class LoadingQueueTest(_Base):
    def _connect_with_hook(self, hook):
        self.h.orchestrator.list_hook = hook

    def test_messages_during_loading_are_queued_in_order_after_snapshot(self):
        """
        @purpose 載入中的連線不直接收訊息：扇出先進暫存佇列，ready 與快照之後依產生順序送出。
        @given list_items 執行期間注入三則可辨識的 work_items 扇出
        @step 完成 hello | 序列為 ready → 快照（含其 work_items）→ 三則暫存訊息，順序與注入相同
        @pass 不早於 ready、不亂序
        @story US2.1
        """
        async def hook(sink):
            for label in ("q1", "q2", "q3"):
                await sink.emit_session(_items_marker(label))

        self._connect_with_hook(hook)
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as ws:
                msgs = hello(ws) + [recv_json(ws) for _ in range(3)]
        self.assertEqual(msgs[0]["type"], "ready")
        labels = [m["payload"]["items"][0]["workItemId"] for m in msgs[-3:]]
        self.assertEqual(labels, ["q1", "q2", "q3"])

    def test_overflow_closes_1011_and_exact_limit_is_delivered(self):
        """
        @purpose 暫存佇列上限 256：第 257 則 → 以 1011 關閉並移出登錄（不丟單則）；恰 256 則照常全部送達。
        @given 兩次連線分別在載入中注入 257 與 256 則扇出
        @step 第一次 | 收到 1011、登錄為空
        @step 第二次 | 收到 ready、快照與 256 則暫存
        @pass 上限生效
        @story US2.1
        """
        count = {"n": 257}

        async def hook(sink):
            for i in range(count["n"]):
                await sink.emit_session(_items_marker(f"q{i}"))

        self._connect_with_hook(hook)
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as ws:
                ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                self.assertEqual(recv_json(ws).get("__close__"), 1011)
            self.assertEqual(self.h.registry.registered_count(), 0)
            count["n"] = 256
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as ws:
                msgs = hello(ws) + [recv_json(ws) for _ in range(256)]
        self.assertEqual(msgs[-1]["payload"]["items"][0]["workItemId"], "q255")

    def test_message_arriving_while_draining_is_delivered_once_and_last(self):
        """
        @purpose 送出暫存佇列時新到的扇出不得漏送或重送：「確認已空」與「改為 ready」之間無任何 await（帶入項 3，NFR13.26）。
        @given 載入中注入兩則；送出最後一則暫存訊息時，另起一個扇出（注入點在送出途中）
        @step 完成 hello 並讀完 | 新訊息恰出現 1 次，且在兩則暫存之後
        @step 檢視連線狀態 | phase 為 ready
        @pass 收斂且無遺漏
        @story US2.1
        """
        gw = self.h.gw

        async def hook(sink):
            await sink.emit_session(_items_marker("p1"))
            await sink.emit_session(_items_marker("p2"))
            conn = gw.registry.snapshot(KEY_A)[0]
            original = conn.ws.send_text

            async def send_text(data):
                if '"p2"' in data:
                    asyncio.ensure_future(
                        gw.fanout(KEY_A, gw.envelope(WsServerMessageType.WORK_ITEMS, None, _items_marker("late")))
                    )
                await original(data)

            conn.ws.send_text = send_text

        self._connect_with_hook(hook)
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as ws:
                msgs = hello(ws) + [recv_json(ws) for _ in range(3)]
                self.assertTrue(nothing_more(ws))
                conn = gw.registry.snapshot(KEY_A)[0]
                self.assertIs(conn.phase, G.Phase.READY)
        labels = [m["payload"]["items"][0]["workItemId"] for m in msgs[-3:]]
        self.assertEqual(labels, ["p1", "p2", "late"])

    def test_overflow_during_snapshot_send_closes_1011(self):
        """
        @purpose 溢位若發生在 ready 與快照送出期間（佇列已被清空、排空迴圈不會執行），改 ready 前仍須發現並以 1011 關閉；
                 否則留下一條已移出登錄卻仍在服務、永遠收不到扇出的連線（審查 R-02）。
        @given 送出 ready 那一則時，同步注入 257 則扇出
        @step 完成 hello | 收到 ready 與部分快照後，收到 1011
        @step 檢視登錄 | 為空
        @pass 不會靜默失效
        @story US2.1
        """
        gw = self.h.gw

        async def hook(sink):
            conn = gw.registry.snapshot(KEY_A)[0]
            original = conn.ws.send_text
            fired = {"done": False}

            async def send_text(data):
                await original(data)
                if '"ready"' in data and not fired["done"]:
                    fired["done"] = True
                    for i in range(257):
                        await sink.emit_session(_items_marker(f"o{i}"))

            conn.ws.send_text = send_text

        self.h.orchestrator.list_hook = hook
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as ws:
                ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                msgs = []
                while True:
                    msg = recv_json(ws)
                    msgs.append(msg)
                    if "__close__" in msg:
                        break
        self.assertEqual(msgs[0]["type"], "ready")
        self.assertEqual(msgs[-1]["__close__"], 1011)
        self.assertEqual(self.h.registry.registered_count(), 0)



class SendFailureTest(_Base):
    def test_failed_send_unregisters_and_closes_1011_without_affecting_others(self):
        """
        @purpose 一條連線送出失敗：移出登錄並主動以 1011 關閉（客戶端才會重連取得快照），不影響其他連線、不向上拋（帶入項 21）。
        @given 同一使用者三條連線；其中一條的 send_text 改為拋例外
        @step 由第一條送 set_sharing_mode 觸發扇出 | 壞掉的那條收到 1011
        @step 讀另兩條 | 各收到 sharing_mode 與 work_target
        @step 檢視登錄 | 剩 2 條
        @pass 失敗隔離且主動關閉
        @story US2.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a2, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a3:
                for ws in (a1, a2, a3):
                    hello(ws)
                broken = self.h.registry.snapshot(KEY_A)[2]

                async def boom(data):
                    raise RuntimeError("socket gone")

                broken.ws.send_text = boom
                a1.send_json({"v": 1, "type": "set_sharing_mode", "payload": {"mode": "isolated", "scope": "workspace"}})
                self.assertEqual(recv_json(a3).get("__close__"), 1011)
                for ws in (a1, a2):
                    self.assertEqual([recv_json(ws)["type"], recv_json(ws)["type"]], ["sharing_mode", "work_target"])
                self.assertEqual(self.h.registry.registered_count(), 2)

    def test_slow_tab_does_not_delay_other_tabs(self):
        """
        @purpose 同一使用者多條連線的扇出並行送出（審查 R-05）：一條卡住（未失敗、只是慢）的分頁不得讓其他分頁的狀態訊息排在它後面。
        @given 同一使用者兩條連線；**先登錄**的那條（扇出順序在前）的 send_text 卡在一個由測試控制的事件上
        @step 由第二條送 set_sharing_mode | 第二條在 1 秒內收到 sharing_mode 與 work_target（第一條仍卡住）
        @step 放行卡住的送出 | 第一條也收到兩則
        @pass 慢分頁只拖慢自己
        @story US2.1
        """
        import asyncio

        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1, \
                    client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a2:
                hello(a1)
                hello(a2)
                slow = self.h.registry.snapshot(KEY_A)[0]  # a1：依序扇出時排在最前
                gate = client.portal.call(asyncio.Event)
                original = slow.ws.send_text

                async def stuck(data):
                    await gate.wait()
                    await original(data)

                slow.ws.send_text = stuck
                a2.send_json({"v": 1, "type": "set_sharing_mode", "payload": {"mode": "isolated", "scope": "workspace"}})
                self.assertEqual([recv_json(a2, timeout=1)["type"], recv_json(a2, timeout=1)["type"]], ["sharing_mode", "work_target"])
                self.assertTrue(nothing_more(a1, wait=0.2))
                client.portal.call(gate.set)
                self.assertEqual([recv_json(a1)["type"], recv_json(a1)["type"]], ["sharing_mode", "work_target"])

    def test_correct_work_item_push_ends_with_done(self):
        """
        @purpose correct_work_item 成功時由 U12 經 sink 開新一輪（emit_turn）：新 turnId、內容後以 done 終止；找不到工作項回 INVALID_REQUEST。
        @given 已交辦一個工作項
        @step 送 correct_work_item 指向它 | 收到 token「已停掉」與 done，turnId 為新值
        @step 送 correct_work_item 指向不存在的 id | error(INVALID_REQUEST)「找不到這個工作項」
        @pass 兩案皆正確
        @story US1.4
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.a)) as a1:
                hello(a1)
                user_message(a1, "畫一張架構圖")
                first = read_turn(a1)
                work_item_id = first[0]["payload"]["items"][0]["workItemId"]
                a1.send_json({"v": 1, "type": "correct_work_item", "payload": {"workItemId": work_item_id}})
                pushed = read_turn(a1)
                self.assertEqual(types_of(pushed), ["token", "done"])
                self.assertNotEqual(pushed[0]["turnId"], first[-1]["turnId"])
                a1.send_json({"v": 1, "type": "correct_work_item", "payload": {"workItemId": "nope"}})
                err = recv_json(a1)
        self.assertEqual((err["payload"]["code"], err["payload"]["message"]), ("INVALID_REQUEST", "找不到這個工作項"))
        self.assertEqual(self.h.orchestrator.correct_calls[0].sink._segment, "shared")


if __name__ == "__main__":
    unittest.main()
