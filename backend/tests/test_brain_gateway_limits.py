"""`U13 brain-gateway` 限流、訊框上限、重驗與結構性禁令的測試（`NFR13.4`、`NFR13.6`、`NFR13.11`、`NFR13.14`–`NFR13.16`、
`NFR13.19`、`NFR13.20`、`NFR13.34`、`NFR13.40`、`NFR13.44`；帶入項 9、20、25、29）。

結構性禁令以 **AST** 檢查（字串 grep 對別名、函式內 import 與下標形式無效，見 `security-design.md` §六）。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import ast
import logging
import socket
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

import httpx
from starlette.testclient import TestClient

from models import User
from services import brain_gateway as G
from services import brain_gateway_rules as R
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    assert_non_turn_error,
    decision,
    hello,
    nothing_more,
    protocols,
    read_turn,
    recv_json,
    types_of,
    user_message,
)

SERVICES = Path(__file__).resolve().parents[1] / "services"
MODULES = (SERVICES / "brain_gateway.py", SERVICES / "brain_gateway_rules.py")


class _Base(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.alice = self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()

    def connect(self, client):
        return client.websocket_connect(WS_PATH, subprotocols=protocols(self.token))


class RateLimitTest(_Base):
    def test_per_user_message_limit_spans_tabs_and_survives_reconnect(self):
        """
        @purpose 同一使用者每 60 秒至多 20 則 user_message（跨分頁合計）；關掉全部連線再重連不得重置（帶入項 20）。
                 超過者不重驗、不分類，只回「訊息太頻繁」。
        @given 同一使用者兩條連線
        @step 兩條合計送 20 則 | 皆 done
        @step 全部關閉後重連，送第 21 則 | error(INVALID_REQUEST)「訊息太頻繁，請稍候再送出」；classify 與認證皆未因它被呼叫
        @step 推進 60 秒後再送 | done
        @pass 上限以使用者為鍵、以時間為生命週期
        @story US8.1
        """
        with TestClient(self.h.app) as client:
            with self.connect(client) as a1, self.connect(client) as a2:
                hello(a1)
                hello(a2)
                for i in range(20):
                    ws = a1 if i % 2 == 0 else a2
                    user_message(ws, f"第{i}句")
                    self.assertEqual(types_of(read_turn(ws))[-1], "done")
                    if ws is a1:
                        recv_json(a2)  # 另一條收到的 work_items 扇出
                    else:
                        recv_json(a1)
            deadline = time.time() + 2
            while self.h.registry.total_slots and time.time() < deadline:
                time.sleep(0.01)
            classify_before = len(self.h.router_script.calls)
            auth_calls = []
            original = self.h.gw._auth_once
            self.h.gw._auth_once = lambda token, record: auth_calls.append(record) or original(token, record)
            with self.connect(client) as a3:
                hello(a3)
                auth_calls.clear()
                user_message(a3, "第21句")
                err = read_turn(a3)[-1]
                self.assertEqual(err["payload"]["message"], "訊息太頻繁，請稍候再送出")
                self.assertEqual(len(self.h.router_script.calls), classify_before)
                self.assertEqual(auth_calls, [])
                self.h.timing.advance(60)
                user_message(a3, "第22句")
                self.assertEqual(types_of(read_turn(a3))[-1], "done")

    def test_oversized_frame_rejected_before_parsing_and_rejections_close_connection(self):
        """
        @purpose 單一訊框超過 65536 位元組 → 不解析、不重驗，回「訊息太長」；連線保留。被拒的訊框計入關閉門檻：
                 視窗內被拒達 20 次即以 1011 關閉（帶入項 29），持續送被拒訊框的客戶端無法無限消耗事件迴圈。
        @given 已連線
        @step 送 65537 位元組的文字訊框 | error「訊息太長，請縮短後再送出」，classify 0 次
        @step 送 4000 字的合法訊息 | done
        @step 再送 19 個過大訊框 | 第 20 次被拒時收到 1011
        @pass 大小上限與關閉門檻皆生效
        @story US8.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            ws.send_text("x" * 65537)
            err = recv_json(ws)
            self.assertEqual(err["payload"]["message"], "訊息太長，請縮短後再送出")
            self.assertEqual(self.h.router_script.calls, [])
            user_message(ws, "字" * 4000)
            self.assertEqual(types_of(read_turn(ws))[-1], "done")
            last = None
            for _ in range(19):
                ws.send_text("x" * 65537)
                last = recv_json(ws)
                if "__close__" in last:
                    break
            self.assertEqual(last.get("__close__"), 1011)

    def test_per_connection_frame_limit(self):
        """
        @purpose 單一連線每 60 秒至多 120 個訊框（點選類訊息也算）；第 121 個不處理，回「訊息太頻繁」。
        @given 已連線
        @step hello 計入第 1 個訊框（審查 R-04）；再送 119 個 set_sharing_mode | 皆生效（各收到 sharing_mode 與 work_target）
        @step 送第 121 個訊框 | error「訊息太頻繁，請稍候再送出」；set_sharing_mode 未因它被呼叫
        @pass 每連線上限生效（含 hello）
        @story US8.1
        """
        calls = []
        original = self.h.store.set_sharing_mode
        self.h.store.set_sharing_mode = lambda *a: calls.append(a) or original(*a)
        frame = {"v": 1, "type": "set_sharing_mode", "payload": {"mode": "shared", "scope": "workspace"}}
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            for _ in range(119):
                ws.send_json(frame)
                recv_json(ws)
                recv_json(ws)
            ws.send_json(frame)
            self.assertEqual(recv_json(ws)["payload"]["message"], "訊息太頻繁，請稍候再送出")
        self.assertEqual(len(calls), 119)


class RevalidationTest(_Base):
    def _set_user(self, **fields):
        db = self.h.Session()
        try:
            user = db.get(User, self.alice.id)
            for k, v in fields.items():
                setattr(user, k, v)
            db.commit()
        finally:
            db.close()

    def test_each_message_revalidates_with_record_true(self):
        """
        @purpose 每則訊息在同一 DB session 內重驗並重鑄 principal（record=True）；帳號停用後的下一則即 4401，且不分類。
        @given 已連線；記錄每次認證的 record 參數
        @step 送一則 | done；該則的認證 record 為 True
        @step 停用帳號後再送一則 | 4401；classify 次數不增加
        @pass 撤權在下一則訊息生效
        @story US8.1
        """
        records = []
        original = self.h.gw._auth_once
        self.h.gw._auth_once = lambda token, record: records.append(record) or original(token, record)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "第一句")
            read_turn(ws)
            self.assertEqual(records, [True, True])
            self._set_user(is_active=False)
            user_message(ws, "第二句")
            self.assertEqual(recv_json(ws).get("__close__"), 4401)
        self.assertEqual(len(self.h.router_script.calls), 1)

    def test_idle_connection_revalidates_every_sixty_seconds(self):
        """
        @purpose 閒置連線每 60 秒背景重驗（record=False，閒置不算活動）；停用 → 4401、撤 K1 → 4403，撤權外洩窗 ≤ 60 秒。
        @given 兩個帳號各一條閒置連線；記錄 record 參數
        @step 停用 Alice、把 Bob 改為無 K1 的角色，推進 60 秒 | Alice 收到 4401、Bob 收到 4403
        @step 檢視背景重驗的 record | 皆為 False
        @pass 背景重驗生效且不更新最後活動
        @story US8.1
        """
        self.h.user("bob")
        records = []
        original = self.h.gw._auth_once
        self.h.gw._auth_once = lambda token, record: records.append(record) or original(token, record)
        with TestClient(self.h.app) as client:
            with self.connect(client) as a, client.websocket_connect(WS_PATH, subprotocols=protocols(self.h.token("bob"))) as b:
                hello(a)
                hello(b)
                deadline = time.time() + 2
                while self.h.timing.sleeper_count() < 2 and time.time() < deadline:
                    time.sleep(0.01)
                records.clear()
                self._set_user(is_active=False)
                db = self.h.Session()
                db.get(User, self.h.users["bob"].id).role = "SRE"
                db.commit()
                db.close()
                self.h.timing.advance(60)
                self.assertEqual(recv_json(a).get("__close__"), 4401)
                self.assertEqual(recv_json(b).get("__close__"), 4403)
        self.assertEqual(set(records), {False})

    def test_non_auth_failure_keeps_connection(self):
        """
        @purpose 重驗遇非認證類例外（DB 暫時不可用）不關閉：訊息路徑回 INTERNAL_ERROR，背景路徑只記 WARNING。
        @given 認證暫時拋 RuntimeError
        @step 送一則 | error(INTERNAL_ERROR)，未收到關閉碼
        @step 推進 60 秒（背景重驗失敗） | 記 revalidate_failed WARNING；連線仍可用
        @step 認證恢復後送一則 | done
        @pass 連線保留
        @story US8.1
        """
        original = self.h.gw._auth_once
        broken = {"on": False}

        def auth(token, record):
            if broken["on"]:
                raise RuntimeError("db down")
            return original(token, record)

        self.h.gw._auth_once = auth
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            broken["on"] = True
            user_message(ws, "第一句")
            self.assertEqual(recv_json(ws)["payload"]["code"], "INTERNAL_ERROR")
            with self.assertLogs("cloud360.brain_gateway", level="WARNING") as logs:
                self.h.timing.advance(60)
                deadline = time.time() + 2
                while not any("revalidate_failed" in o for o in logs.output) and time.time() < deadline:
                    time.sleep(0.01)
            broken["on"] = False
            user_message(ws, "第二句")
            self.assertEqual(types_of(read_turn(ws))[-1], "done")


class NonTurnErrorTurnIdTest(unittest.TestCase):
    """BR2.8 T1／T2：被拒訊框與重驗例外的 `error` 不屬於任何輪次，`turnId` 為 null（合併前必修第 2 項(a)）。"""

    def setUp(self):
        self.h = Harness(rate=R.RateLimiter(per_key=1))
        self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()

    def test_rejected_frames_carry_null_turn_id(self):
        """
        @purpose T1：二進位訊框、過大訊框、頻率超限三種被拒訊框的 error 都不得帶捏造的 turnId；連線保留。
        @given 每使用者 60 秒 1 則 user_message 的限流器；已連線
        @step 送一個二進位訊框 | error(INVALID_REQUEST)，envelope 與 payload 的 turnId 皆為 null
        @step 送 65537 位元組的文字訊框 | error(INVALID_REQUEST)「訊息太長」，turnId 皆為 null
        @step 送一句（done）後再送一句 | 第二句收到 error(INVALID_REQUEST)「訊息太頻繁」，turnId 皆為 null
        @pass 三種被拒訊框皆為非輪次錯誤
        @story US8.1
        @api WS /api/brain/ws -> 101
        """
        with TestClient(self.h.app) as client, client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
            hello(ws)
            ws.send_bytes(b"\x00\x01")
            assert_non_turn_error(self, recv_json(ws), "INVALID_REQUEST")
            ws.send_text("x" * 65537)
            too_large = recv_json(ws)
            assert_non_turn_error(self, too_large, "INVALID_REQUEST")
            self.assertEqual(too_large["payload"]["message"], "訊息太長，請縮短後再送出")
            user_message(ws, "第一句")
            self.assertEqual(types_of(read_turn(ws))[-1], "done")
            user_message(ws, "第二句")
            limited = recv_json(ws)
            assert_non_turn_error(self, limited, "INVALID_REQUEST")
            self.assertEqual(limited["payload"]["message"], "訊息太頻繁，請稍候再送出")

    def test_revalidation_exception_carries_null_turn_id(self):
        """
        @purpose T2：每則重驗拋非認證類例外時，回的 error 不屬於任何輪次（該則訊息根本未被處理），turnId 為 null。
        @given 已連線；認證暫時拋 RuntimeError
        @step 送一句 | error(INTERNAL_ERROR)，envelope 與 payload 的 turnId 皆為 null；classify 0 次
        @pass 非輪次錯誤
        @story US8.1
        @api WS /api/brain/ws -> 101
        """
        original = self.h.gw._auth_once
        broken = {"on": False}

        def auth(token, record):
            if broken["on"]:
                raise RuntimeError("db down")
            return original(token, record)

        self.h.gw._auth_once = auth
        with TestClient(self.h.app) as client, client.websocket_connect(WS_PATH, subprotocols=protocols(self.token)) as ws:
            hello(ws)
            broken["on"] = True
            user_message(ws, "第一句")
            assert_non_turn_error(self, recv_json(ws), "INTERNAL_ERROR")
        self.assertEqual(self.h.router_script.calls, [])


class ThreadAndOutboundTest(_Base):
    def test_blocking_calls_leave_the_event_loop_and_no_outbound_connection(self):
        """
        @purpose 本單元的同步呼叫（認證、session、對象目錄）一律離開事件迴圈；一輪完整交辦期間本單元不產生任何出站連線
                 （不新增 LLM 呼叫）。
        @given 記錄 SessionStore 方法與目錄替身的執行緒；httpx 與 socket 的出站呼叫一被觸發即記錄
        @step 握手、一則帶 referent 的交辦（觸發對象目錄）、set_work_target、set_sharing_mode、correct_work_item | 皆完成
        @step 比對執行緒 | 全部不是事件迴圈執行緒；出站呼叫 0 次
        @pass 迴圈不被阻塞且無出站
        @story US8.1
        """
        threads, loop_threads, outbound = [], [], []
        # U12 替身對 store 的同步呼叫（OPEN-GW13-4 的具名殘留）不屬本單元：讓它走未包裝的方法。
        from types import SimpleNamespace

        self.h.orchestrator.store = SimpleNamespace(
            load_work_items=self.h.store.load_work_items, put_work_item=self.h.store.put_work_item
        )
        for name in ("load", "append_message", "set_work_target", "set_sharing_mode", "load_work_items"):
            original = getattr(self.h.store, name)

            def wrapped(*a, _o=original, **k):
                threads.append(threading.get_ident())
                return _o(*a, **k)

            setattr(self.h.store, name, wrapped)
        auth_original = self.h.gw._auth_once

        def auth(token, record):
            threads.append(threading.get_ident())
            return auth_original(token, record)

        self.h.gw._auth_once = auth
        self.h.hierarchy.projects = [(1, "電商")]
        self.h.hierarchy.systems = {1: [(10, "訂單")]}
        self.h.router_script.default = decision(referent="訂單")

        async def note_loop(sink, turn_id):
            loop_threads.append(threading.get_ident())

        self.h.orchestrator.dispatch_hook = note_loop
        # 只攔真正會出網的傳輸層（TestClient 自己走 _TestClientTransport，不受影響）。
        with mock.patch.object(httpx.HTTPTransport, "handle_request", side_effect=lambda *a, **k: outbound.append(1)), \
                mock.patch.object(httpx.AsyncHTTPTransport, "handle_async_request", side_effect=lambda *a, **k: outbound.append(1)), \
                mock.patch.object(socket, "create_connection", side_effect=lambda *a, **k: outbound.append(1)):
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                user_message(ws, "改訂單")
                turn = read_turn(ws)
                wid = turn[1]["payload"]["items"][0]["workItemId"]
                ws.send_json({"v": 1, "type": "set_work_target", "payload": {"projectId": "1", "systemId": None, "diagramId": None, "segment": "shared"}})
                recv_json(ws)
                ws.send_json({"v": 1, "type": "set_sharing_mode", "payload": {"mode": "isolated", "scope": "workspace"}})
                recv_json(ws)
                recv_json(ws)
                ws.send_json({"v": 1, "type": "correct_work_item", "payload": {"workItemId": wid}})
                read_turn(ws)
        self.assertTrue(loop_threads)
        self.assertTrue(threads)
        self.assertNotIn(loop_threads[0], set(threads) | set(self.h.hierarchy.threads))
        self.assertEqual(outbound, [])


class LogHygieneTest(_Base):
    def test_logs_never_contain_token_text_referent_or_labels(self):
        """
        @purpose log 不得含 token、使用者文字、回覆、referent 與候選標籤（repo 公開、Actions log 公開）。
        @given 以 uuid 產生的唯一標記：token 在子協定、原句、referent 與專案名
        @step 走：握手、一輪交辦、一次 referent 多筆相符的對象反問、一次失敗路徑 | 皆完成
        @step 以根 logger 擷取 DEBUG 以上全部紀錄 | 無任一筆含任一標記
        @pass log 無洩漏
        @story US8.1
        """
        mark = uuid.uuid4().hex
        self.h.hierarchy.projects = [(1, f"P{mark}"), (2, f"Q{mark}")]
        self.h.hierarchy.systems = {1: [(10, f"S{mark}")], 2: [(20, f"S{mark}")]}
        self.h.router_script.script[f"U{mark}"] = decision(referent=f"S{mark}")
        with self.assertLogs(level="DEBUG") as logs:
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                user_message(ws, "第一句")
                read_turn(ws)
                user_message(ws, f"U{mark}")
                self.assertEqual(read_turn(ws)[-1]["payload"]["kind"], "target")
                ws.send_json({"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": "nope"}})
                recv_json(ws)
                logging.getLogger("cloud360.brain_gateway").debug("probe")
        joined = "\n".join(logs.output)
        for needle in (self.token, mark):
            self.assertNotIn(needle, joined)


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _gateway_timing_defaults(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "GatewayTiming":
            return {id(n) for n in ast.walk(node)}
    return set()


class StructuralTest(unittest.TestCase):
    def test_no_direct_clock_or_sleep_outside_gateway_timing(self):
        """
        @purpose 全部計時路徑經注入的 GatewayTiming（帶入項 9）：直呼 time.monotonic／time.time／time.sleep／asyncio.sleep／
                 asyncio.wait_for 只允許出現在 GatewayTiming 的預設值；新增一處直呼即紅燈。
        @given 兩個模組的 AST
        @step 收集上列五個屬性存取的位置 | 全部落在 GatewayTiming 類別內
        @pass 無直呼
        @story US8.1
        """
        banned = {("time", "monotonic"), ("time", "time"), ("time", "sleep"), ("asyncio", "sleep"), ("asyncio", "wait_for")}
        for path in MODULES:
            tree = _tree(path)
            allowed = _gateway_timing_defaults(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and (node.value.id, node.attr) in banned:
                    with self.subTest(module=path.name, line=node.lineno):
                        self.assertIn(id(node), allowed)

    def test_forbidden_imports_names_and_hand_built_messages(self):
        """
        @purpose 只經 facade、不碰進度通道與需求欄位、不新增 LLM 呼叫、不讀 query string、不直寫 SQL、訊息必經契約模型（NFR13.16、NFR13.40）。
        @given 兩個模組的 AST（含函式內 import）
        @step 檢查 import | 不含禁止清單；無 importlib、__import__
        @step 檢查名稱 | 無 request_key、query_params、execute 存取，無名為 text 的變數，無自 sqlalchemy 匯入 text
        @step 檢查 dict 字面 | 無以 "type" 為鍵者
        @pass 全部為零
        @story US8.1
        """
        forbidden_modules = (
            "services.hierarchy_service", "services.memory_service", "services.membership_service",
            "services.membership_facade", "services.requirement_field_facade", "services.requirement_field_service",
            "services.progress_channel", "services.llm_provider", "openai", "langchain", "langgraph", "main",
        )
        for path in MODULES:
            tree = _tree(path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                    if (node.module or "").startswith("sqlalchemy"):
                        self.assertNotIn("text", [a.name for a in node.names])
                for name in names:
                    with self.subTest(module=path.name, imported=name):
                        self.assertFalse(any(name == f or name.startswith(f + ".") or (f in ("langchain", "langgraph") and name.startswith(f)) for f in forbidden_modules))
                if isinstance(node, ast.Name):
                    self.assertNotIn(node.id, {"importlib", "__import__", "request_key", "query_params", "text"})
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"request_key", "query_params", "execute", "url"})
                if isinstance(node, ast.Dict):
                    keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
                    self.assertNotIn("type", keys)

    def test_env_reads_logger_name_and_single_log_exit(self):
        """
        @purpose 本單元只讀三個既有的 Redis 環境變數（含 os.environ[...] 下標形式）；logger 名為 cloud360.brain_gateway；
                 log 只經 _log 一個出口（NFR13.34、NFR13.44）。
        @given 兩個模組的 AST
        @step 收集 os.environ[...]、os.environ.get、os.getenv 的鍵 | ⊆ {REDIS_URL, REDIS_USER, REDIS_PASSWORD}
        @step 收集 getLogger 的引數 | 恰為 "cloud360.brain_gateway"
        @step 收集 logger.* 的直接呼叫 | 只有 _log 內的一處
        @pass 三項成立
        @story US8.1
        """
        env_keys, logger_names, direct_logger_calls = set(), set(), 0
        for path in MODULES:
            for node in ast.walk(_tree(path)):
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
                    env_keys.add(node.slice.value)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("getenv",) or (node.func.attr == "get" and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "environ"):
                        env_keys.add(node.args[0].value)
                    if node.func.attr == "getLogger":
                        logger_names.add(node.args[0].value)
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
                        direct_logger_calls += 1
        self.assertLessEqual(env_keys, {"REDIS_URL", "REDIS_USER", "REDIS_PASSWORD"})
        self.assertEqual(env_keys, {"REDIS_URL", "REDIS_USER", "REDIS_PASSWORD"})
        self.assertEqual(logger_names, {"cloud360.brain_gateway"})
        self.assertEqual(direct_logger_calls, 1)

    def test_mint_turn_id_only_where_a_turn_really_opens(self):
        """
        @purpose BR2.8（合併前必修第 2 項(a)）：只有真正開啟一輪的兩處可以產生新 turnId——`BrainGateway._on_user_message`
                 建立 `Turn`、`GatewaySink.emit_turn` 推播；其他任何位置（非輪次錯誤、作業對象等）新增一處即紅燈。
        @given `brain_gateway.py` 的 AST
        @step 收集名稱 `_mint_turn_id` 的全部出現位置（定義除外） | 恰 2 處，且皆為直接呼叫
        @step 對照所在的類別與方法 | 恰為 {BrainGateway._on_user_message, GatewaySink.emit_turn}
        @pass 沒有任何捏造 turnId 的呼叫點
        @story US8.1
        """
        tree = _tree(SERVICES / "brain_gateway.py")
        calls, names = [], []

        def visit(node, scope):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, scope + (child.name,))
                    continue
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "_mint_turn_id":
                    calls.append(".".join(scope))
                if isinstance(child, ast.Name) and child.id == "_mint_turn_id":
                    names.append(".".join(scope))
                visit(child, scope)

        visit(tree, ())
        self.assertEqual(len(names), 2, names)
        self.assertEqual(sorted(calls), ["BrainGateway._on_user_message", "GatewaySink.emit_turn"])

    def test_close_reasons_are_ascii_short_and_token_free(self):
        """
        @purpose 關閉原因只用 ASCII、≤ 123 位元組、不含 token（RFC 6455 控制訊框上限；BR67.4）。
        @given 全部固定關閉原因與 4400 的兩種形狀
        @step 逐一檢查 | isascii、長度 ≤ 123、不含 bearer
        @pass 全部成立
        @story US8.1
        """
        reasons = list(G.CLOSE_REASONS.values()) + [R.close_reason_for_version("2"), R.close_reason_for_version("invalid")]
        for reason in reasons:
            self.assertTrue(reason.isascii())
            self.assertLessEqual(len(reason.encode()), 123)
            self.assertNotIn("bearer", reason)


if __name__ == "__main__":
    unittest.main()
