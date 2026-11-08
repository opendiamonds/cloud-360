"""合併前必修第 33 列 (a)(b)：記憶表的計數經 `MemoryFacade`；基底例外更名。

(a) `user_router._blocking_user_references` 原本直接 `import MemoryRecord,
MemoryAuditEvent` 以 ORM 計數，繞過記憶表的唯一入口 `MemoryFacade`。本檔以兩種方式
鎖住：靜態——`user_router.py` 不得 import 這兩個記憶 ORM model；行為——刪除使用者的
預檢確實呼叫 `MemoryFacade.count_references_to_user`，且其筆數出現在 409 回應。

(b) `MemoryError` 與 Python 內建同名、會遮蔽內建類別；更名為 `MemoryServiceError`。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1a `user_router` 重新 import 兩個記憶 model → 案例 1 紅；
  M1b `user_router` 的記憶筆數改回直接 ORM 計數、不經 facade → 案例 2 紅；
  M2 `count_references_to_user` 的記憶列數固定回 0 → 案例 3 紅；
  M3 `memory_errors` 補回 `MemoryError = MemoryServiceError` 別名 → 案例 4 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import ast
import builtins
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import MemoryRecord
import services.memory_errors as memory_errors
import services.memory_facade as memory_facade
from services.auth import get_current_user
from services.memory_facade import MemoryFacade
from tests.helpers import close_session, make_session, make_user

USER_ROUTER = Path(__file__).resolve().parents[1] / "services" / "user_router.py"
MEMORY_MODELS = {"MemoryRecord", "MemoryAuditEvent"}


class MemoryCountsThroughFacadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.root = make_user(self.db, username="root", role="Platform_Admin")
        self.target = make_user(
            self.db, username="target", role="Developer", is_active=False
        )
        self.target_id = self.target.id
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.root
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def add_memory(self) -> None:
        self.db.add(
            MemoryRecord(
                kind="semantic",
                owner_user_id=self.target_id,
                visibility_scope="owner",
                content="x",
                embedding_model="stub",
                created_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

    def test_user_router_does_not_import_memory_models(self):
        """
        @purpose user_router 不得直接 import 記憶 ORM model（無宣告的旁路）
        @given backend/services/user_router.py 原始碼
        @step 以 ast 列出所有 import 的名稱
        @pass 不含 MemoryRecord、MemoryAuditEvent
        @story US9.1
        """
        tree = ast.parse(USER_ROUTER.read_text(encoding="utf-8"))
        imported = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertEqual(imported & MEMORY_MODELS, set())

    def test_delete_precheck_calls_the_facade_count(self):
        """
        @purpose 刪除使用者的預檢經 MemoryFacade.count_references_to_user 取得記憶筆數
        @given 已停用的 target 擁有 1 則記憶
        @step 管理員 DELETE /api/auth/{target}，同時監看 facade 方法
        @pass 409 且 memory_records 的筆數為 1；facade 方法以 target 的 id 被呼叫一次
        @api DELETE /api/auth/{user_id} -> 409 | 仍有記憶指向此使用者
        @story US9.1
        """
        self.add_memory()
        real = MemoryFacade.count_references_to_user
        with patch.object(
            MemoryFacade, "count_references_to_user", autospec=True, side_effect=real
        ) as spy:
            res = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(res.status_code, 409, res.text)
        refs = {r["category"]: r["count"] for r in res.json()["blocking_references"]}
        self.assertEqual(refs.get("memory_records"), 1)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.kwargs["user_id"], self.target_id)

    def test_facade_count_returns_both_counts(self):
        """
        @purpose facade 計數方法回傳記憶列數與稽核操作者列數
        @given target 擁有 1 則記憶、0 筆稽核
        @step MemoryFacade(db).count_references_to_user(user_id=target)
        @pass records == 1、audit_events_as_actor == 0
        @story US9.1
        """
        self.add_memory()
        counts = MemoryFacade(self.db).count_references_to_user(user_id=self.target_id)
        self.assertEqual(counts.records, 1)
        self.assertEqual(counts.audit_events_as_actor, 0)


class MemoryServiceErrorRenameTest(unittest.TestCase):
    def test_base_error_no_longer_shadows_builtin(self):
        """
        @purpose 基底例外改名為 MemoryServiceError，不再有遮蔽內建的 MemoryError
        @given services.memory_errors 與 services.memory_facade
        @step 檢查兩模組的屬性與 __all__、三個子類別的繼承
        @pass 兩模組皆無 MemoryError 屬性；MemoryServiceError 不是內建 MemoryError；三個子類別皆繼承它
        @story US4.1
        """
        for module in (memory_errors, memory_facade):
            self.assertFalse(hasattr(module, "MemoryError"), module.__name__)
            self.assertNotIn("MemoryError", module.__all__)
            self.assertIn("MemoryServiceError", module.__all__)
        base = memory_errors.MemoryServiceError
        self.assertIsNot(base, builtins.MemoryError)
        self.assertFalse(issubclass(base, builtins.MemoryError))
        for sub in (
            memory_errors.MemoryForbidden,
            memory_errors.MemoryNotFound,
            memory_errors.MemoryInvalidInput,
        ):
            self.assertTrue(issubclass(sub, base), sub.__name__)


if __name__ == "__main__":
    unittest.main()
