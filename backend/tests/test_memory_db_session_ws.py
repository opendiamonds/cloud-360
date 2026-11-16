"""合併前必修第 52 列／`MB-48` 的未完成半邊：WS 與編排路徑的記憶存取改走記憶專用連線。

**問題**（build-and-test `test-results.md` 待修 1）：記憶專用角色 `cloud360_memory` 只套在
HTTP 的五個記憶端點（`memory_router.get_memory_db`）；閘道的預取（`_prefetch`）、情節記憶
寫入（`_write_episodic`）、語意記憶寫入（`_write_semantic`）、編排器的程序記憶寫入
（`_write_procedure_memory`），以及刪帳號前的記憶參照計數（`user_router`），都以主連線
（擁有者帳號）存取 `memory` schema——資料庫層的 IAM 第二道邊界在這些路徑上沒有效力。

**做法**：判定只有一處（`memory_router.memory_session_source`），HTTP 與非 HTTP 共用；非 HTTP
呼叫端經 `memory_session_scope` 取 session。本檔與 `test_memory_db_session.py`（HTTP）同一個
技巧：`database.memory_db_boundary_enabled`／`get_memory_session` 以替身取代，「記憶專用
session」是同一個 in-memory SQLite 引擎上的**另一個** `Session` 物件，以物件身分區分兩條連線。

三種情境逐一驗：
- 已設定 → 交給 facade 的是記憶 session（不是主連線），用完 close；
- 未設定、本機（`APP_ENV=test`）→ 退回主連線（與 HTTP 一致）；
- 未設定、非本機（`APP_ENV=staging`）→ **不退回**：facade 從未被建立，各路徑沿用既有降級語意
  （預取降級、語意寫入回 `memory_write_failed`、情節寫入只記 WARNING、程序寫入只記 WARNING、
  刪帳號回 503 固定句）。

**突變驗證 M9**（暫存區副本，結果記於 `build-and-test/local-verify-fixes.md` 第三輪）：五處任一
改回直接用主連線 → 對應的 `*_uses_memory_session` 案紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

import database
from database import get_db
from main import app
from models import User
from services import brain_gateway as G
from services import brain_gateway_rules as R
from services import memory_router
from services import user_router
from services.auth import get_current_user
from services.memory_errors import MEMORY_STORAGE_UNAVAILABLE_DETAIL
from services.memory_facade import mint_principal
from services.work_orchestrator import WorkOrchestrator
from tests.brain_gateway_fakes import WS_PATH, Harness, hello, protocols, read_turn, types_of, user_message
from tests.helpers import close_session, make_session, make_user

PREFERENCE = "我們團隊偏好把服務部署在 ap-northeast-1"
SELECT_CONFIRM = {"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": R.MEMORY_CONFIRM_CANDIDATE_ID}}


class _MemorySessionMixin:
    """一個可辨識、會記錄 close 的「記憶專用 session」，以及三種情境的 patch。"""

    def make_memory_session(self, engine) -> Session:
        self.memory_db = Session(bind=engine)
        self.memory_db_closed = 0
        original_close = self.memory_db.close

        def _close():
            self.memory_db_closed += 1
            original_close()

        self.memory_db.close = _close  # type: ignore[method-assign]
        self.addCleanup(original_close)
        memory_router._warn_local_fallback_once.cache_clear()
        self.addCleanup(memory_router._warn_local_fallback_once.cache_clear)
        return self.memory_db

    def boundary_enabled(self):
        stack = [
            mock.patch.object(database, "memory_db_boundary_enabled", return_value=True),
            mock.patch.object(database, "get_memory_session", return_value=self.memory_db),
        ]
        return _Stack(stack)

    @staticmethod
    def boundary_unset(app_env: str):
        return _Stack(
            [
                mock.patch.object(database, "memory_db_boundary_enabled", return_value=False),
                mock.patch.dict(os.environ, {"APP_ENV": app_env}),
            ]
        )


class _Stack:
    def __init__(self, patches):
        self._patches = patches

    def __enter__(self):
        return [p.__enter__() for p in self._patches]

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.__exit__(*exc)
        return False


# ---------------------------------------------------------------------------
# 閘道：預取、情節寫入、語意寫入
# ---------------------------------------------------------------------------


class GatewayMemorySessionTest(_MemorySessionMixin, unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.addCleanup(self.h.close)
        self.alice = self.h.user("alice")
        self.token = self.h.token("alice")
        self.make_memory_session(self.h.db._test_engine)
        # 每次 `memory_facade_factory(db)` 拿到哪一個 session；主連線的 factory 被呼叫幾次。
        self.facade_sessions: list = []
        fake = self.h.memory

        def _recording(db):
            self.facade_sessions.append(db)
            return fake.factory(db)

        self.h.gw.memory_facade_factory = _recording
        self.main_sessions: list = []
        real_session = self.h.Session

        def _main():
            db = real_session()
            self.main_sessions.append(db)
            return db

        self.h.gw.session_factory = _main
        self.principal = mint_principal(self.alice)

    def _prefetch(self):
        turn = G.Turn(turn_id="t-prefetch")
        result = asyncio.run(self.h.gw._prefetch(self.principal, "畫一張架構圖", turn))
        return turn, result

    def _episodic(self):
        asyncio.run(self.h.gw._write_episodic(self.principal, "使用者：畫一張架構圖", "t-episodic"))

    def _semantic_confirm(self):
        with TestClient(self.h.app) as client, client.websocket_connect(
            WS_PATH, subprotocols=protocols(self.token)
        ) as ws:
            hello(ws)
            user_message(ws, f"記住：{PREFERENCE}")
            read_turn(ws)
            ws.send_json(SELECT_CONFIRM)
            return read_turn(ws)

    def _assert_only_memory_session(self, what: str):
        self.assertTrue(self.facade_sessions, f"{what}：facade 未被建立")
        for db in self.facade_sessions:
            self.assertIs(db, self.memory_db, f"{what}：MemoryFacade 拿到的不是記憶專用 session")
        for db in self.main_sessions:
            self.assertNotIn(db, self.facade_sessions, f"{what}：主連線被交給 MemoryFacade")
        self.assertGreaterEqual(self.memory_db_closed, 1, f"{what}：記憶 session 用完未 close")

    def test_prefetch_uses_memory_session(self):
        """
        @purpose MB-48：閘道的記憶預取經記憶專用連線，不經主連線（擁有者帳號）
        @given 記憶專用連線已設定（替身）；記憶替身回 1 筆
        @step 呼叫 BrainGateway._prefetch | 回 1 筆、turn.prefetch=hit
        @step 檢視 facade 拿到的 session | 恰為記憶 session、且已 close；主連線 factory 0 次
        @pass 預取只走記憶專用連線
        @story US4.4
        """
        self.h.memory.search_behaviour = [SimpleNamespace(kind="semantic", content="術語")]
        with self.boundary_enabled():
            turn, result = self._prefetch()
        self.assertEqual(turn.prefetch, "hit")
        self.assertEqual(len(result.hits), 1)
        self._assert_only_memory_session("預取")
        self.assertEqual(self.main_sessions, [], "邊界啟用時預取不得開主連線")

    def test_episodic_write_uses_memory_session(self):
        """
        @purpose MB-48：情節記憶寫入經記憶專用連線
        @given 記憶專用連線已設定（替身）
        @step 呼叫 BrainGateway._write_episodic | 寫入恰 1 次、kind=episodic
        @pass facade 拿到記憶 session、主連線 factory 0 次
        @story US4.4
        """
        with self.boundary_enabled():
            self._episodic()
        self.assertEqual([c.kind for c in self.h.memory.write_calls], ["episodic"])
        self._assert_only_memory_session("情節寫入")
        self.assertEqual(self.main_sessions, [])

    def test_semantic_write_uses_memory_session(self):
        """
        @purpose MB-48：使用者確認後的語意記憶寫入經記憶專用連線
        @given 記憶專用連線已設定（替身）；alice 已連線
        @step 送「記住：<偏好>」並確認 | token＋done
        @pass 寫入恰 1 次 kind=semantic；每次 facade 拿到的都是記憶 session（不是任何一個主連線 session）
        @story US4.4
        @api WS /api/brain/ws -> 101
        """
        with self.boundary_enabled():
            turn = self._semantic_confirm()
        self.assertEqual(types_of(turn), ["token", "done"])
        self.assertEqual([c.kind for c in self.h.memory.write_calls], ["semantic"])
        self._assert_only_memory_session("語意寫入")

    def test_unset_non_local_never_hands_any_session_to_the_facade(self):
        """
        @purpose MB-48 未設定且非本機（staging）：三條路徑都不退回主連線，沿用既有降級語意
        @given memory_db_boundary_enabled 為假；APP_ENV=staging
        @step 預取 | turn.prefetch=failed、hits=None（降級，照常分類）
        @step 情節寫入 | 不寫；cloud360.brain_gateway 記 episodic_write_failed 含 MemoryStorageUnavailable
        @step 語意寫入（確認） | error、message=memory_write_failed 固定句
        @pass facade 從未被建立；ERROR 日誌含 memory_db_unavailable 與 app_env=staging，不含連線字樣
        @story US4.4
        @api WS /api/brain/ws -> 101
        """
        with self.boundary_unset("staging"), self.assertLogs("cloud360", level="WARNING") as logs:
            turn, result = self._prefetch()
            self._episodic()
            semantic = self._semantic_confirm()
        self.assertEqual(turn.prefetch, "failed")
        self.assertIsNone(result.hits)
        self.assertEqual(types_of(semantic), ["error"])
        self.assertEqual(semantic[0]["payload"]["message"], R.ERROR_MESSAGES["memory_write_failed"])
        self.assertEqual(self.facade_sessions, [], "非本機未設定時不得把任何 session 交給 facade")
        self.assertEqual(self.h.memory.write_calls, [])
        joined = "\n".join(logs.output)
        self.assertIn("episodic_write_failed", joined)
        self.assertIn("MemoryStorageUnavailable", joined)
        self.assertIn(memory_router.EVENT_MEMORY_DB_UNAVAILABLE, joined)
        self.assertIn("app_env=staging", joined)
        for fragment in ("postgresql", "cloud360_memory", "MEMORY_DB_PASSWORD="):
            self.assertNotIn(fragment, joined)

    def test_unset_local_falls_back_to_main_like_http(self):
        """
        @purpose MB-48 未設定且本機（APP_ENV=test）：與 HTTP 記憶端點一致，退回主連線並記一次 WARNING
        @given memory_db_boundary_enabled 為假；APP_ENV=test
        @step 預取與情節寫入各一次 | 預取 empty、寫入 1 次
        @pass facade 拿到的都是主連線 session；memory_db_local_fallback 恰 1 筆
        @story US4.4
        """
        with self.boundary_unset("test"), self.assertLogs("cloud360.memory_router", level="WARNING") as logs:
            turn, _ = self._prefetch()
            self._episodic()
        self.assertEqual(turn.prefetch, "empty")
        self.assertEqual(len(self.h.memory.write_calls), 1)
        self.assertEqual(len(self.facade_sessions), 2)
        for db in self.facade_sessions:
            self.assertIn(db, self.main_sessions)
        fallback = [line for line in logs.output if memory_router.EVENT_MEMORY_DB_FALLBACK in line]
        self.assertEqual(len(fallback), 1)


# ---------------------------------------------------------------------------
# 編排器：程序記憶寫入（users 走主連線、記憶走記憶連線）
# ---------------------------------------------------------------------------


class OrchestratorProcedureMemorySessionTest(_MemorySessionMixin, unittest.TestCase):
    def setUp(self):
        self.main_db = make_session()
        self.addCleanup(close_session, self.main_db)
        engine = self.main_db._test_engine  # type: ignore[attr-defined]
        self.user = make_user(self.main_db, username="u52_proc", role="Project_Architect")
        self.make_memory_session(engine)
        self.MainSession = sessionmaker(bind=engine)
        self.main_sessions: list = []

        def _main():
            db = self.MainSession()
            self.main_sessions.append(db)
            return db

        self.writes: list = []

        class _Recorder:
            def __init__(inner, db):
                inner.db = db

            def write(inner, principal, kind, content):
                self.writes.append((inner.db, principal.user_id, kind, content))

        self.orch = WorkOrchestrator(
            object(),
            object(),
            session_factory=_main,
            memory_facade_factory=_Recorder,
            mint=mint_principal,
            user_model=User,
        )
        self.ctx = SimpleNamespace(user_id=self.user.id, item_id="wi-1", session_key="k", token="t", sink=None)
        self.item = {"capability": "cost-finops", "label": "估算月成本"}

    def _write(self):
        asyncio.run(self.orch._write_procedure_memory(self.ctx, self.item))

    def test_procedure_write_uses_memory_session(self):
        """
        @purpose MB-48：程序記憶寫入經記憶專用連線；讀 users（public）仍用主連線且兩者分開
        @given 記憶專用連線已設定（替身）；一位啟用中的使用者
        @step 呼叫 WorkOrchestrator._write_procedure_memory | 寫入恰 1 次、kind=procedure、擁有者為該使用者
        @pass 寫入拿到的是記憶 session；主連線恰開 1 次（讀 users）且不是寫入用的那個
        @story US4.4
        """
        with self.boundary_enabled():
            self._write()
        self.assertEqual(len(self.writes), 1)
        db, uid, kind, _ = self.writes[0]
        self.assertIs(db, self.memory_db, "程序記憶寫入拿到的不是記憶專用 session")
        self.assertEqual((uid, kind), (self.user.id, "procedure"))
        self.assertEqual(len(self.main_sessions), 1, "主連線只用來讀 users")
        self.assertIsNot(self.main_sessions[0], self.memory_db)
        self.assertEqual(self.memory_db_closed, 1)

    def test_unset_non_local_skips_write_and_warns(self):
        """
        @purpose MB-48 未設定且非本機：程序記憶不寫、不退回主連線，工作項不受影響（只記 WARNING，BR51.5）
        @given memory_db_boundary_enabled 為假；APP_ENV=staging
        @step 呼叫 _write_procedure_memory | 不拋例外
        @pass 寫入 0 次；cloud360.work_orchestrator 記 memory_write_failed error=MemoryStorageUnavailable
        @story US4.4
        """
        with self.boundary_unset("staging"), self.assertLogs("cloud360", level="WARNING") as logs:
            self._write()
        self.assertEqual(self.writes, [])
        self.assertTrue(
            any("memory_write_failed" in line and "MemoryStorageUnavailable" in line for line in logs.output),
            logs.output,
        )

    def test_unset_local_falls_back_to_main(self):
        """
        @purpose MB-48 未設定且本機：與 HTTP 一致退回主連線
        @given memory_db_boundary_enabled 為假；APP_ENV=test
        @step 呼叫 _write_procedure_memory | 寫入 1 次
        @pass 寫入拿到的是主連線 session（讀 users 之外另開的一個）
        @story US4.4
        """
        with self.boundary_unset("test"):
            self._write()
        self.assertEqual(len(self.writes), 1)
        self.assertIn(self.writes[0][0], self.main_sessions)
        self.assertIsNot(self.writes[0][0], self.memory_db)


# ---------------------------------------------------------------------------
# user_router：刪帳號前的記憶參照計數
# ---------------------------------------------------------------------------


class UserDeleteMemoryCountSessionTest(_MemorySessionMixin, unittest.TestCase):
    def setUp(self):
        self.main_db = make_session()
        self.addCleanup(close_session, self.main_db)
        self.make_memory_session(self.main_db._test_engine)  # type: ignore[attr-defined]
        self.admin = make_user(self.main_db, username="u52_admin", role="Platform_Admin")
        self.target = make_user(self.main_db, username="u52_target", role="Project_Architect")
        self.target.is_active = False
        self.main_db.commit()
        app.dependency_overrides[get_db] = lambda: self.main_db
        app.dependency_overrides[get_current_user] = lambda: self.admin
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.counted_on: list = []
        real = user_router.MemoryFacade

        def _recording(db, *a, **kw):
            self.counted_on.append(db)
            return real(db, *a, **kw)

        patcher = mock.patch.object(user_router, "MemoryFacade", side_effect=_recording)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_delete_user_memory_count_uses_memory_session(self):
        """
        @purpose MB-48：刪除帳號前的記憶參照計數經記憶專用連線，不以擁有者帳號讀 memory schema
        @given 記憶專用連線已設定（替身）；已停用、無任何參照的帳號
        @step 平台管理員 DELETE /api/auth/{user_id} | 2xx
        @pass 計數用的 MemoryFacade 恰建立 1 次且拿到記憶 session（不是請求的主連線）；記憶 session 已 close
        @story US4.4
        @api DELETE /api/auth/{user_id} -> 200 | 記憶專用連線
        """
        with self.boundary_enabled():
            res = self.client.delete(f"/api/auth/{self.target.id}")
        self.assertLess(res.status_code, 300, res.text[:300])
        self.assertEqual(self.counted_on, [self.memory_db])
        self.assertIsNot(self.counted_on[0], self.main_db)
        self.assertEqual(self.memory_db_closed, 1)

    def test_delete_user_unset_non_local_returns_503_and_deletes_nothing(self):
        """
        @purpose MB-48 未設定且非本機：刪帳號回 503 固定句，不退回主連線計數、帳號未被刪
        @given memory_db_boundary_enabled 為假；APP_ENV=staging
        @step 平台管理員 DELETE /api/auth/{user_id} | 503
        @pass detail 為固定句；MemoryFacade 0 次；帳號仍在
        @story US4.4
        @api DELETE /api/auth/{user_id} -> 503 | 非本機未設定記憶專用連線
        """
        with self.boundary_unset("staging"):
            res = self.client.delete(f"/api/auth/{self.target.id}")
        self.assertEqual(res.status_code, 503, res.text[:300])
        self.assertEqual(res.json()["detail"], MEMORY_STORAGE_UNAVAILABLE_DETAIL)
        self.assertEqual(self.counted_on, [])
        self.main_db.expire_all()
        self.assertIsNotNone(self.main_db.get(User, self.target.id))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
