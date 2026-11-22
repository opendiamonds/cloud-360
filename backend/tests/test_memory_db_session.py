"""合併前必修第 48 列 Major（`OPEN-CG5-1`）：記憶端點改走記憶專用連線。

**問題**：`brain-infra` 已在 `database.py` 提供 `get_memory_session()`（以只授
`memory` schema 的 `cloud360_memory` 角色連線），但 `memory_router.py` 的五個端點仍
`Depends(get_db)`——以擁有者帳號存取記憶表，資料庫層的 IAM 邊界在執行期沒有效力，
而 CI 的 R0–R3 全綠也看不出這件事（R0–R3 驗的是角色本身，不是程式有沒有用它）。

**2026-11-07 使用者裁決「只在本機／測試退回」**：記憶專用連線未設定時，`APP_ENV`
屬 `database.LOCAL_APP_ENVS`（local／test／ci）才退回主連線並記 WARNING；其他環境
一律 503 並記 ERROR（不輸出連線字串或密碼）。

本檔四組案例對應 `code-generation-plan.md` §十三 13c 的 (1)–(4)。

不需要真實資料庫：`get_db`／`get_current_user` 以 `app.dependency_overrides` 覆寫，
「記憶專用 session」是同一個 in-memory SQLite 引擎上的**另一個** `Session` 物件，
以物件身分區分兩條連線。

**突變驗證**（暫存區副本，結果記於本單元 `code-summary.md` 2026-11-07 一節）：
  M1 五個端點的 dependency 改回 `get_db` → (1) 與 (4) 的路由檢查紅（(4) 的呼叫者
     檢查此時仍綠：`get_memory_db` 還在、只是沒人用——故 (4) 另有逐條路由的斷言）；
  M1b `get_memory_db` 不再呼叫 `get_memory_session()`（邊界啟用時也退回主連線）
     → (1) 與 (4) 的呼叫者檢查紅；
  M2 非本機分支改成一律退回 → (2) 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import os
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

import database
from database import get_db
from main import app
from models import MemoryRecord
from services import memory_router
from services.auth import get_current_user
from services.memory_errors import MEMORY_STORAGE_UNAVAILABLE_DETAIL
from services.memory_types import VISIBILITY_SCOPE_OWNER
from tests.helpers import close_session, make_session, make_user

SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
FIXTURE_PREFIX = "__u8_memdb__"


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._env = mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"})
        self._env.start()
        self.addCleanup(self._env.stop)

        self.main_db = make_session()
        engine = self.main_db._test_engine  # type: ignore[attr-defined]
        # 同一個 in-memory 引擎上的第二個 session：代表 `cloud360_memory` 那條連線。
        self.memory_db = Session(bind=engine)
        self.memory_db_closed = False
        original_close = self.memory_db.close

        def _close():
            self.memory_db_closed = True
            original_close()

        self.memory_db.close = _close  # type: ignore[method-assign]

        self.owner = make_user(self.main_db, username="u8_memdb_owner", role="Project_Architect")
        self.admin = make_user(self.main_db, username="u8_memdb_admin", role="Platform_Admin")
        self.acting = self.owner

        app.dependency_overrides[get_db] = lambda: self.main_db
        app.dependency_overrides[get_current_user] = lambda: self.acting
        self.client = TestClient(app)

        # 記錄每次 `MemoryFacade(db)` 拿到的是哪一個 session。
        self.facade_sessions: list = []
        real_facade = memory_router.MemoryFacade

        def _recording_facade(db, *args, **kwargs):
            self.facade_sessions.append(db)
            return real_facade(db, *args, **kwargs)

        patcher = mock.patch.object(memory_router, "MemoryFacade", side_effect=_recording_facade)
        patcher.start()
        self.addCleanup(patcher.stop)
        memory_router._warn_local_fallback_once.cache_clear()
        self.addCleanup(memory_router._warn_local_fallback_once.cache_clear)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        try:
            self.memory_db.close()
        finally:
            close_session(self.main_db)

    def seed(self) -> MemoryRecord:
        from datetime import datetime, timezone

        record = MemoryRecord(
            kind="semantic",
            owner_user_id=self.owner.id,
            visibility_scope=VISIBILITY_SCOPE_OWNER,
            content=f"{FIXTURE_PREFIX} owner",
            embedding_model="stub-v1",
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        self.main_db.add(record)
        self.main_db.commit()
        self.main_db.refresh(record)
        return record

    def call_all_five(self, record_id: int) -> dict:
        """依序打五個端點，回 `{名稱: 狀態碼}`。"""
        codes = {}
        self.acting = self.owner
        codes["POST"] = self.client.post(
            "/api/memory/records", json={"kind": "semantic", "content": f"{FIXTURE_PREFIX} new"}
        ).status_code
        codes["GET records"] = self.client.get("/api/memory/records").status_code
        self.acting = self.admin
        codes["PUT scope"] = self.client.put(
            f"/api/memory/records/{record_id}/scope", json={"visibility_scope": "platform"}
        ).status_code
        codes["GET audit"] = self.client.get("/api/memory/audit-events").status_code
        self.acting = self.owner
        codes["DELETE"] = self.client.delete(f"/api/memory/records/{record_id}").status_code
        return codes


class MemoryBoundaryEnabledTest(_Base):
    def test_all_five_endpoints_use_the_memory_session_when_boundary_enabled(self):
        """
        @purpose 記憶專用連線已設定時，五個記憶端點交給 MemoryFacade 的都是記憶 session，不是 get_db 的主連線（OPEN-CG5-1）
        @given database.memory_db_boundary_enabled() 為真；get_memory_session() 回一個與主連線不同的 session 物件；一則擁有者的記憶
        @step 以擁有者 POST、GET 清單、DELETE，以平台管理員 PUT scope、GET 稽核
        @pass 五個請求皆非 5xx；MemoryFacade 被建立 5 次，每次拿到的都是記憶 session、沒有一次是主連線；請求結束後記憶 session 已 close
        @api POST /api/memory/records -> 201 | 記憶專用連線
        @api GET /api/memory/records -> 200 | 記憶專用連線
        @api PUT /api/memory/records/{memory_id}/scope -> 200 | 記憶專用連線
        @api GET /api/memory/audit-events -> 200 | 記憶專用連線
        @api DELETE /api/memory/records/{memory_id} -> 204 | 記憶專用連線
        @story US4.4
        """
        record = self.seed()
        with mock.patch.object(database, "memory_db_boundary_enabled", return_value=True), \
                mock.patch.object(database, "get_memory_session", return_value=self.memory_db) as getter:
            codes = self.call_all_five(record.id)

        self.assertEqual(
            codes,
            {"POST": 201, "GET records": 200, "PUT scope": 200, "GET audit": 200, "DELETE": 204},
        )
        self.assertEqual(getter.call_count, 5, "每個請求各取一次記憶 session")
        self.assertEqual(len(self.facade_sessions), 5)
        for db in self.facade_sessions:
            self.assertIs(db, self.memory_db, "MemoryFacade 拿到的不是記憶專用 session")
            self.assertIsNot(db, self.main_db, "MemoryFacade 拿到主連線：IAM 邊界在執行期無效")
        self.assertTrue(self.memory_db_closed, "記憶 session 在請求結束後必須 close")


class MemoryBoundaryNotConfiguredTest(_Base):
    def test_non_local_env_returns_503_with_fixed_detail_and_no_connection_info_in_log(self):
        """
        @purpose 非本機環境未設定記憶專用連線時不退回主連線：記憶端點回 503、detail 固定、ERROR log 不含連線字串或密碼
        @given database.memory_db_boundary_enabled() 為假；APP_ENV=staging；DATABASE_URL 含可辨識的主機與密碼片段
        @step 以擁有者 GET /api/memory/records 與 POST /api/memory/records
        @pass 兩者皆 503 且 detail 等於固定句；MemoryFacade 從未被建立；cloud360.memory_router 有 ERROR 紀錄，且其內容不含 DATABASE_URL 的任何片段與 postgresql 字樣
        @api GET /api/memory/records -> 503 | 非本機環境未設定記憶專用連線
        @api POST /api/memory/records -> 503 | 非本機環境未設定記憶專用連線
        @story US4.4
        """
        secret_url = "postgresql+psycopg://owner_user:[REDACTED-pw-u8]@db-host-u8:5432/cloud360"
        with mock.patch.object(database, "memory_db_boundary_enabled", return_value=False), \
                mock.patch.object(database, "DATABASE_URL", secret_url), \
                mock.patch.dict(os.environ, {"APP_ENV": "staging", "DATABASE_URL": secret_url}), \
                self.assertLogs("cloud360.memory_router", level="ERROR") as captured:
            listed = self.client.get("/api/memory/records")
            created = self.client.post(
                "/api/memory/records", json={"kind": "semantic", "content": f"{FIXTURE_PREFIX} x"}
            )

        for res in (listed, created):
            self.assertEqual(res.status_code, 503, res.text[:200])
            self.assertEqual(res.json()["detail"], MEMORY_STORAGE_UNAVAILABLE_DETAIL)
        self.assertEqual(self.facade_sessions, [], "非本機環境不得把任何 session 交給 facade")
        joined = "\n".join(captured.output)
        self.assertIn(memory_router.EVENT_MEMORY_DB_UNAVAILABLE, joined)
        self.assertIn("app_env=staging", joined)
        for fragment in ("postgresql", "owner_user", "REDACTED-pw-u8", "db-host-u8", "5432", "cloud360_memory"):
            self.assertNotIn(fragment, joined, f"ERROR log 洩漏連線資訊片段 {fragment!r}")
        self.assertEqual(self.main_db.query(MemoryRecord).count(), 0, "503 時不得寫入")

    def test_local_env_falls_back_to_main_connection_and_warns_once(self):
        """
        @purpose 本機／測試環境未設定記憶專用連線時退回主連線，記憶照常可讀寫，WARNING 每程序只記一次
        @given database.memory_db_boundary_enabled() 為假；APP_ENV=test；退回旗標已清空
        @step 以擁有者 POST 一則記憶、GET 清單兩次
        @pass POST 201、清單含該則；MemoryFacade 拿到的都是主連線；三個請求只產生一筆 memory_db_local_fallback WARNING
        @api POST /api/memory/records -> 201 | 本機退回主連線
        @api GET /api/memory/records -> 200 | 本機退回主連線
        @story US4.1
        """
        with mock.patch.object(database, "memory_db_boundary_enabled", return_value=False), \
                mock.patch.dict(os.environ, {"APP_ENV": "test"}), \
                self.assertLogs("cloud360.memory_router", level="WARNING") as captured:
            created = self.client.post(
                "/api/memory/records", json={"kind": "semantic", "content": f"{FIXTURE_PREFIX} local"}
            )
            first = self.client.get("/api/memory/records")
            second = self.client.get("/api/memory/records")

        self.assertEqual(created.status_code, 201, created.text[:200])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertIn(created.json()["memory_id"], {item["memory_id"] for item in first.json()})
        self.assertEqual(len(self.facade_sessions), 3)
        for db in self.facade_sessions:
            self.assertIs(db, self.main_db)
        fallback_lines = [
            line for line in captured.output if memory_router.EVENT_MEMORY_DB_FALLBACK in line
        ]
        self.assertEqual(len(fallback_lines), 1, f"退回 WARNING 應每程序一次，實際 {captured.output}")
        self.assertTrue(fallback_lines[0].startswith("WARNING:"))


class MemorySessionHasProductionCallerTest(unittest.TestCase):
    def test_every_memory_route_takes_its_session_from_get_memory_db(self):
        """
        @purpose 呼叫者存在還不夠：memory_router 的每一條路由都必須經 get_memory_db 取 session，沒有一條直接 Depends(get_db)
        @given backend/services/memory_router.py 的原始碼
        @step 以 ast 找出所有以 @router.<method> 裝飾的函式，讀其參數預設值中的 Depends(...) 目標
        @pass 恰 5 條路由；每一條都有 Depends(get_memory_db)，沒有一條有 Depends(get_db)
        @story US4.4
        """
        tree = ast.parse((SERVICES_DIR / "memory_router.py").read_text(encoding="utf-8"))
        routes = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            decorated = any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and isinstance(d.func.value, ast.Name)
                and d.func.value.id == "router"
                for d in node.decorator_list
            )
            if not decorated:
                continue
            targets = [
                default.args[0].id
                for default in node.args.defaults + node.args.kw_defaults
                if isinstance(default, ast.Call)
                and getattr(default.func, "id", None) == "Depends"
                and default.args
                and isinstance(default.args[0], ast.Name)
            ]
            routes[node.name] = targets
        self.assertEqual(len(routes), 5, f"記憶路由應為 5 條，實際 {sorted(routes)}")
        for name, targets in routes.items():
            with self.subTest(route=name):
                self.assertIn("get_memory_db", targets, f"{name} 未經 get_memory_db 取 session")
                self.assertNotIn("get_db", targets, f"{name} 直接 Depends(get_db)：以擁有者帳號存取記憶表")

    def test_get_memory_session_has_a_non_test_caller_in_services(self):
        """
        @purpose 對應 OPEN-CG5-1 的關閉條件：get_memory_session 在非測試程式中至少有一個呼叫者（不再是零呼叫者的死碼）
        @given backend/services/ 下全部 .py 檔
        @step 以 ast 解析每個檔，找出呼叫 get_memory_session 的 Call 節點（Name 或 Attribute 形式皆算）
        @pass 至少一處，且其中之一落在 memory_router.py
        @story US4.4
        """
        callers = []
        for path in sorted(SERVICES_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if name == "get_memory_session":
                    callers.append(f"{path.name}:{node.lineno}")
        self.assertTrue(callers, "backend/services/ 內沒有任何 get_memory_session() 呼叫")
        self.assertTrue(
            any(c.startswith("memory_router.py:") for c in callers),
            f"memory_router.py 未呼叫 get_memory_session；實際呼叫點 {callers}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
