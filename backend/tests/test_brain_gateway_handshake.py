"""`U13 brain-gateway` 握手測試（`GW-W1`；`BR61.x`；`NFR13.7`–`NFR13.10`、`NFR13.17`／`NFR13.18`、`NFR13.23` ①）。

以 `starlette.testclient.TestClient.websocket_connect` 驅動真的 WebSocket handler；授權走真實
`get_user_from_token`／`user_can`／`mint_principal`（SQLite ＋ 播種）。

**限制（揭露）**：TestClient 下「不 accept」表現為客戶端收到關閉碼 1000（`WebSocketDisconnect`），
真實 uvicorn 為 HTTP 403；本檔只斷言「未 accept」。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import threading
import time
import unittest
from datetime import datetime, timezone

from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from models import User
from services import brain_gateway_rules as R
from services.session_errors import SessionBackendUnavailable
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    hello,
    protocols,
    recv_json,
    types_of,
)
from tests.test_session_store_behaviour import FakeConnectionError


class _Base(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.alice = self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()


class SubprotocolTest(_Base):
    def test_accepts_with_protocol_name_only_and_never_echoes_token(self):
        """
        @purpose 伺服器只回送 cloud360.brain.v1：token 不得出現在回應標頭（比請求標頭更常被代理與開發工具記錄）。
        @given 已核准、具 K1.view 的帳號；token 為唯一標記字串
        @step 以兩個子協定連線 | accepted_subprotocol 為 cloud360.brain.v1
        @step 檢視回應標頭 | 任何鍵值皆不含 token
        @step 送 hello | 收到 ready 與快照
        @pass 只回送協定名、回應標頭無 token、握手完成
        @story US8.1
        @api WS /api/brain/ws -> 101
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                self.assertEqual(ws.accepted_subprotocol, R.PROTOCOL_NAME)
                for name, value in ws.extra_headers or []:
                    self.assertNotIn(self.token.encode(), name + value)
                self.assertEqual(types_of(hello(ws))[0], "ready")

    def test_token_only_in_query_string_is_rejected_in_both_shapes(self):
        """
        @purpose AC8.1.3：token 只放在 query string 的握手一定被拒，兩種形狀分別斷言（本端點從不讀 query string）。
        @given 有效 token
        @step (a) 帶 cloud360.brain.v1、token 只在 ?token= | accept 後立刻收到 4401
        @step (b) 不帶 cloud360.brain.v1（舊 DEMO 形狀，只有 bearer 項） | 從未 accept（TestClient 表現為關閉碼 1000）
        @pass 兩案皆被拒，且 (a) 的 session 讀取次數為 0
        @story US8.1
        @api WS /api/brain/ws -> 403
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(f"{WS_PATH}?token={self.token}", subprotocols=[R.PROTOCOL_NAME]) as ws:
                self.assertEqual(recv_json(ws).get("__close__"), 4401)
            with self.assertRaises(WebSocketDisconnect) as caught:
                with client.websocket_connect(WS_PATH, subprotocols=[R.BEARER_PREFIX + self.token]):
                    pass
            self.assertEqual(caught.exception.code, 1000)
        self.assertEqual(self.h.redis.calls.count("HGETALL"), 0)


class AuthorizationTest(_Base):
    def _close_code(self, token):
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(token)) as ws:
                ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                msg = recv_json(ws)
                if "__close__" in msg:
                    return msg["__close__"]
                return msg.get("type")

    def test_k1_allow_deny_and_disabled_account(self):
        """
        @purpose K1 授權 allow／deny 雙向（team.md 規則 A）：有 K1.view 且已核准才取得通道，其餘依原因以 4401／4403 關閉。
        @given 四個帳號：Project_Architect（有 K1）、SRE（無 K1）、未核准的架構師、已停用的架構師
        @step 各自連線 | 依序收到 ready、4403、4403、4401
        @step 無效 token | 4401
        @pass 五案皆如預期
        @story US8.1
        """
        self.h.user("sre", role="SRE")
        self.h.user("pending", authorization_status="pending")
        self.h.user("gone", is_active=False)
        self.assertEqual(self._close_code(self.token), "ready")
        self.assertEqual(self._close_code(self.h.token("sre")), 4403)
        self.assertEqual(self._close_code(self.h.token("pending")), 4403)
        self.assertEqual(self._close_code(self.h.token("gone")), 4401)
        self.assertEqual(self._close_code("not-a-jwt"), 4401)

    def test_failed_auth_reads_no_frame_and_touches_no_session(self):
        """
        @purpose 未通過認證者從未取得可讀寫的通道：伺服器不讀任何訊框、不寫任何 session 狀態、登錄為空。
        @given 無效 token
        @step 連線 | 收到 4401
        @step 檢視 Redis 替身的指令與登錄 | 0 個指令、登錄為空、佔位歸零
        @pass 無任何 session 存取
        @story US8.1
        """
        self.assertEqual(self._close_code("bad"), 4401)
        self.assertEqual(self.h.redis.calls, [])
        self.assertEqual(self.h.registry.registered_count(), 0)
        self.assertEqual(self.h.registry.total_slots, 0)

    def test_handshake_records_last_activity(self):
        """
        @purpose AC8.1.2：握手以 record=True 驗證 token，使長連線也更新最後活動時間（審計面）。
        @given last_activity_at 為空的帳號
        @step 連線並完成 hello | 收到 ready
        @step 以新的 DB session 讀回該帳號 | last_activity_at 非空
        @pass 最後活動時間已更新
        @story US8.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                hello(ws)
        db = self.h.Session()
        try:
            self.assertIsNotNone(db.get(User, self.alice.id).last_activity_at)
        finally:
            db.close()


class VersionTest(_Base):
    def test_incompatible_hello_and_timeout_close_with_4400(self):
        """
        @purpose 首則訊息必須是 hello 且 v=1；不相容或 10 秒內沒來即以 4400 關閉並帶 expected／received。
        @given 有效帳號
        @step 送 hello v=2 | 4400，reason 為 expected=1 received=2
        @step 不送任何訊息（以注入時鐘令 10 秒等待逾時） | 4400，reason 為 expected=1 received=invalid
        @pass 兩案皆 4400 且不進入載入
        @story US8.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                ws.send_json({"v": 2, "type": "hello", "payload": {"v": 2}})
                msg = recv_json(ws)
                self.assertEqual((msg["__close__"], msg["reason"]), (4400, "expected=1 received=2"))
            self.h.timing.expire_once[10.0] = 1
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                msg = recv_json(ws)
                self.assertEqual((msg["__close__"], msg["reason"]), (4400, "expected=1 received=invalid"))
        self.assertEqual(self.h.orchestrator.list_calls, [])


    def test_oversized_hello_is_rejected(self):
        """
        @purpose hello 也受入站單一訊框 64 KiB 上限約束（審查 R-04；NFR13.19），且計入每連線頻率窗。
        @given 有效帳號
        @step 送 65537 位元組的首則訊框 | 4400，reason 為 expected=1 received=invalid；不進入載入
        @step 正常 hello 的連線 | 每連線頻率窗已記 1 個訊框
        @pass 首則訊框無例外
        @story US8.1
        """
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                ws.send_text("x" * 65537)
                msg = recv_json(ws)
                self.assertEqual((msg["__close__"], msg["reason"]), (4400, "expected=1 received=invalid"))
            self.assertEqual(self.h.orchestrator.list_calls, [])
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                hello(ws)
                conn = self.h.registry.snapshot("brain:session:1")[0]
                self.assertEqual(len(self.h.gw.rate._per_conn[conn.conn_id]), 1)

    def test_unexpected_error_during_snapshot_closes_1011(self):
        """
        @purpose 握手期（ready 送出前後的快照）未預期例外 → 1011 並移出登錄，log 只含例外類別名（審查 R-03）。
        @given 快照組裝拋出含標記字串的 RuntimeError
        @step 完成 hello | 收到 ready 後 1011
        @step 檢視登錄與 log | 登錄為空；log 有 handshake_unexpected 且不含標記
        @pass 握手失敗形狀一致
        @story US8.1
        """
        def boom(*a, **k):
            raise RuntimeError("SECRET-MARKER")

        self.h.gw._snapshot_envelopes = boom
        with self.assertLogs("cloud360.brain_gateway", level="WARNING") as logs:
            with TestClient(self.h.app) as client:
                with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                    ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                    self.assertEqual(recv_json(ws)["type"], "ready")
                    self.assertEqual(recv_json(ws).get("__close__"), 1011)
        self.assertEqual(self.h.registry.registered_count(), 0)
        joined = "\n".join(logs.output)
        self.assertIn("handshake_unexpected", joined)
        self.assertNotIn("SECRET-MARKER", joined)

class SlotTest(unittest.TestCase):
    def tearDown(self):
        self.h.close()

    def test_concurrent_handshakes_cannot_exceed_global_limit(self):
        """
        @purpose 全域佔位在握手一開始（認證之前）就計數：一波同時湧入的握手中，超出上限者在付出任何 DB 成本前即被拒（帶入項 7）。
        @given 全域上限注入為 3；認證被一個 threading.Event 擋住
        @step 4 條執行緒同時連線，待 3 條進入認證 | 第 4 條未 accept、認證被呼叫恰 3 次
        @step 放行認證 | 3 條皆收到 ready
        @step 全部關閉 | 佔位歸零
        @pass 併發下不超過上限且不洩漏佔位
        @story US8.1
        """
        self.h = Harness(max_total=3)
        for i in range(4):
            self.h.user(f"u{i}")
        gate, entered = threading.Event(), []
        original = self.h.gw._auth_once
        sqlite_lock = threading.Lock()  # 測試 DB 是單一連線的 in-memory SQLite：DB 存取在此序列化

        def gated(token, record):
            entered.append(token)
            gate.wait(5)
            with sqlite_lock:
                return original(token, record)

        self.h.gw._auth_once = gated
        results, release = [], threading.Event()
        with TestClient(self.h.app) as client:

            def worker(name):
                try:
                    with client.websocket_connect(WS_PATH, subprotocols=protocols(self.h.token(name))) as ws:
                        results.append(types_of(hello(ws))[0])
                        release.wait(5)
                except WebSocketDisconnect as exc:
                    results.append(("refused", exc.code))

            threads = [threading.Thread(target=worker, args=(f"u{i}",)) for i in range(4)]
            for t in threads:
                t.start()
            deadline = time.time() + 5
            while (len(entered) < 3 or len(results) < 1) and time.time() < deadline:
                time.sleep(0.01)
            time.sleep(0.2)
            self.assertEqual(len(entered), 3)
            self.assertEqual(results, [("refused", 1000)])
            gate.set()
            deadline = time.time() + 5
            while len(results) < 4 and time.time() < deadline:
                time.sleep(0.01)
            self.assertEqual(sorted(map(str, results)), sorted(map(str, [("refused", 1000), "ready", "ready", "ready"])))
            release.set()
            for t in threads:
                t.join(5)
        self.assertEqual(self.h.registry.total_slots, 0)
        self.assertEqual(self.h.registry.key_slots, {})

    def test_per_key_limit_refuses_extra_tab_without_affecting_open_ones(self):
        """
        @purpose [GWN1]=A：同一使用者超過上限的新分頁連不上，已開的分頁不受影響；關掉一條後重試即可。
        @given 每 key 上限注入為 2
        @step 同一使用者開 2 條並完成 hello | 皆 ready
        @step 開第 3 條 | 未 accept
        @step 關閉其中 1 條後重試 | ready
        @pass 上限生效且釋放後可用
        @story US8.1
        """
        self.h = Harness(max_per_key=2)
        self.h.user("alice")
        token = self.h.token("alice")
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(token)) as ws1:
                hello(ws1)
                with client.websocket_connect(WS_PATH, subprotocols=protocols(token)) as ws2:
                    hello(ws2)
                    with self.assertRaises(WebSocketDisconnect):
                        with client.websocket_connect(WS_PATH, subprotocols=protocols(token)):
                            pass
                deadline = time.time() + 5
                while self.h.registry.key_slots.get("brain:session:1", 0) > 1 and time.time() < deadline:
                    time.sleep(0.01)
                with client.websocket_connect(WS_PATH, subprotocols=protocols(token)) as ws3:
                    self.assertEqual(types_of(hello(ws3))[0], "ready")

    def test_handshake_rate_is_limited_per_user(self):
        """
        @purpose 握手本身也納入限流（帶入項 20）：重連迴圈不得無限次觸發載入與登錄。
        @given 每 key 握手上限注入為 2
        @step 同一使用者連續握手 3 次 | 前 2 次 ready、第 3 次未 accept
        @pass 第 3 次被拒
        @story US8.1
        """
        self.h = Harness(rate=R.RateLimiter(handshakes_per_key=2))
        self.h.user("alice")
        token = self.h.token("alice")
        with TestClient(self.h.app) as client:
            for _ in range(2):
                with client.websocket_connect(WS_PATH, subprotocols=protocols(token)) as ws:
                    hello(ws)
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect(WS_PATH, subprotocols=protocols(token)):
                    pass


class LoadFailureTest(_Base):
    def test_redis_unavailable_during_handshake_closes_1011_and_unregisters(self):
        """
        @purpose [GW3]=A 前半：握手期（ready 之前）Redis 不可用 → 1011，先移出登錄、丟棄暫存，不回空 session 繼續服務。
        @given Redis 替身在 load 時連續拋連線錯誤（超過閘道的重試次數）
        @step 連線並送 hello | 收到 1011
        @step 檢視登錄與佔位 | 皆為空
        @pass 1011 且無殘留
        @story US8.1
        """
        self.h.redis.fail_next = [FakeConnectionError("down")] * 10
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                self.assertEqual(recv_json(ws).get("__close__"), 1011)
        self.assertEqual(self.h.registry.registered_count(), 0)
        self.assertEqual(self.h.registry.total_slots, 0)

    def test_missing_gateway_component_closes_1011(self):
        """
        @purpose app.state 沒有閘道元件（未觸發 startup）時不在請求路徑上延遲建立，而以 1011 關閉。
        @given 自 app.state 移除 brain_gateway
        @step 連線 | accept 後收到 1011
        @pass 1011
        @story US8.1
        """
        del self.h.app.state.brain_gateway
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                self.assertEqual(recv_json(ws).get("__close__"), 1011)

    def test_state_change_during_load_reaches_new_connection_last(self):
        """
        @purpose 先登錄再讀取：讀取期間另一分頁改了作業對象，新連線最後收到的 work_target 必為新值（BR63.2 排序保證）。
        @given list_items 執行期間（已登錄、尚未 ready）有一次 set_work_target 的扇出
        @step 完成 hello 並讀完快照與暫存佇列 | 最後一則 shared 段的 work_target 帶新的 projectId
        @pass 收斂到最新狀態
        @story US2.1
        """
        self.h.hierarchy.projects = [(7, "電商")]

        async def inject(sink):
            gw = self.h.gw
            conn = gw.registry.snapshot("brain:session:1")[0]
            await gw._set_target_confirmed(conn, None, "shared", R.TargetRef(7, None, "電商", "電商"))

        self.h.orchestrator.list_hook = inject
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                msgs = hello(ws)
                msgs.append(recv_json(ws))
        targets = [m for m in msgs if m.get("type") == "work_target" and m["payload"]["segment"] == "shared"]
        self.assertEqual(targets[-1]["payload"]["projectId"], "7")
        self.assertEqual(types_of(msgs)[0], "ready")


class WorkTargetNamesSnapshotTest(_Base):
    """ADR-0022 D-7：握手快照的 `work_target` 帶三層名稱；名稱失敗不讓握手失敗。"""

    KEY = "brain:session:1"

    def _set(self, segment, pid, sid=None, did=None):
        from services.hierarchy_facade import mint_principal

        self.h.store.set_work_target(self.KEY, segment, mint_principal(self.alice), pid, sid, did)

    def _snapshot_targets(self):
        with TestClient(self.h.app) as client:
            with client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
                messages = hello(ws)
        self.assertEqual(types_of(messages)[0], "ready")
        return {m["payload"]["segment"]: m["payload"] for m in messages if m["type"] == "work_target"}

    def test_snapshot_work_target_carries_names_with_one_session(self):
        """
        @purpose 連線建立時推送的作業對象必須帶名稱（AC1.1.5、AC9.1.1）；三段的名稱查詢共用一個 DB
                 session（G3 突變：每組各開一個 session）。
        @given /api/brain/ws；workspace、assessment 為獨立模式；三段各設不同作業對象；替身回三組名稱
        @step 連線並送 hello | 收到 ready 與快照
        @step 檢視三則 work_target | 各段名稱與替身設定逐一相同
        @step 檢視名稱查詢所用的 DB session | describe_work_target 呼叫 3 次、全部落在同一個 session
        @pass 快照帶名稱且只開一個 session
        @story US1.1
        """
        self.h.hierarchy.projects = [(3, "e2e-u14-電商"), (4, "e2e-u14-金流")]
        self.h.hierarchy.systems = {3: [(30, "e2e-u14-訂單系統")], 4: [(40, "e2e-u14-支付")]}
        # 獨立段只在該頁為獨立模式時存在於 session（快照才會推送該段的 work_target）
        self.h.store.set_sharing_mode(self.KEY, "workspace", "isolated")
        self.h.store.set_sharing_mode(self.KEY, "assessment", "isolated")
        self._set("shared", 3)
        self._set("workspace", None, 30)
        self._set("assessment", None, 40)
        names = {
            (3, None, None): {"projectName": "e2e-u14-電商", "systemName": None, "diagramName": None},
            (3, 30, None): {"projectName": "e2e-u14-電商", "systemName": "e2e-u14-訂單系統", "diagramName": None},
            (4, 40, None): {"projectName": "e2e-u14-金流", "systemName": "e2e-u14-支付", "diagramName": None},
        }
        self.h.hierarchy.names_by_triple = names
        sessions_seen = []
        original = self.h.gw.hierarchy_facade_factory

        def recording_factory(db):
            sessions_seen.append(db)
            return original(db)

        self.h.gw.hierarchy_facade_factory = recording_factory
        targets = self._snapshot_targets()
        self.assertEqual(
            {seg: (t["projectName"], t["systemName"], t["diagramName"]) for seg, t in targets.items()},
            {
                "shared": ("e2e-u14-電商", None, None),
                "workspace": ("e2e-u14-電商", "e2e-u14-訂單系統", None),
                "assessment": ("e2e-u14-金流", "e2e-u14-支付", None),
            },
        )
        self.assertEqual(len(self.h.hierarchy.describe_calls), 3)
        self.assertEqual(set(self.h.hierarchy.describe_calls), set(names))
        self.assertEqual(len({id(db) for db in sessions_seen}), 1)

    def test_names_failure_still_completes_handshake_and_logs_once(self):
        """
        @purpose 名稱查詢失敗只使名稱為 null：握手照常完成（不得 1011），並記一筆不含名稱的
                 work_target_names_failed（G1 突變：_names_for 往外拋即得 1011）。
        @given /api/brain/ws；共享段作業對象為專案 3；describe_work_target 拋含標記字串的 RuntimeError
        @step 連線並送 hello | 收到 ready 與快照、無關閉碼
        @step 檢視 work_target | 三名稱皆 null、projectId 仍為 "3"
        @step 檢視 log | 恰一筆 work_target_names_failed、exc=RuntimeError、不含標記與名稱
        @pass 握手完成、名稱 null、log 一筆
        @story US2.1
        """
        self.h.hierarchy.projects = [(3, "e2e-u14-電商")]
        self._set("shared", 3)
        self.h.hierarchy.describe_raises = RuntimeError("e2e-u14-SECRET-MARKER")
        with self.assertLogs("cloud360.brain_gateway", level="WARNING") as logs:
            targets = self._snapshot_targets()
        shared = targets["shared"]
        self.assertEqual(shared["projectId"], "3")
        self.assertEqual((shared["projectName"], shared["systemName"], shared["diagramName"]), (None, None, None))
        failed = [line for line in logs.output if "work_target_names_failed" in line]
        self.assertEqual(len(failed), 1, logs.output)
        self.assertIn("exc=RuntimeError", failed[0])
        joined = "\n".join(logs.output)
        self.assertNotIn("e2e-u14-SECRET-MARKER", joined)
        self.assertNotIn("e2e-u14-電商", joined)

    def test_forbidden_names_are_null_without_any_log(self):
        """
        @purpose K2 view 撤銷（HierarchyForbidden）是正常的拒絕結果：名稱為 null 且不記任何 WARNING
                 （nfr-design R-04；G2 突變：HierarchyForbidden 也記 log）。
        @given /api/brain/ws；共享段作業對象為專案 3；describe_work_target 拋 HierarchyForbidden
        @step 連線並送 hello | 收到 ready 與快照
        @step 檢視 work_target 與 log | 三名稱皆 null；cloud360.brain_gateway 無 WARNING
        @pass 名稱 null 且無 log
        @story US2.1
        """
        from services.hierarchy_facade import HierarchyForbidden

        self.h.hierarchy.projects = [(3, "e2e-u14-電商")]
        self._set("shared", 3)
        self.h.hierarchy.describe_raises = HierarchyForbidden(story_id="K2", action="view")
        with self.assertNoLogs("cloud360.brain_gateway", level="WARNING"):
            targets = self._snapshot_targets()
        shared = targets["shared"]
        self.assertEqual((shared["projectName"], shared["systemName"], shared["diagramName"]), (None, None, None))


if __name__ == "__main__":
    unittest.main()
