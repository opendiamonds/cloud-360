"""合併前必修第 27、28 列：刪除使用者的稽核筆數與 409 的下一步提示。

第 27 列：刪除使用者時規則 1 會在同一交易清除其空預設專案、系統與其下的需求欄位，
但兩個成功路徑的稽核訊息只寫刪了哪個帳號——不可復原的刪除沒有留下可追的痕跡
（ADR-0006 audit logging）。本檔斷言兩個入口的稽核內容都含三類筆數。

第 28 列 (c)：409 的 `detail` 缺下一步提示；本檔斷言它含「維持停用」的提示。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 刪除端點的稽核訊息拿掉 `purge_summary.audit_text()` → 案例 1、3 紅；
  M2 拒絕申請端點同樣拿掉 → 案例 2 紅；
  M3 409 `detail` 拿掉下一步提示 → 案例 4 紅；
  M4 `_purge_empty_default_projects` 的需求欄位筆數固定回 0 → 案例 1 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest
from unittest.mock import patch

from sqlalchemy import text
from starlette.testclient import TestClient

from database import get_db
from main import app
from models import Project, ProjectMember, RoleAuthorizationRequest, System, SystemRequirementField
from services.auth import get_current_user
from tests.helpers import close_session, make_session, make_user

ROLE_GLOBAL_ADMIN = "Platform_Admin"
ROLE_TARGET = "Developer"


class UserDeleteAuditCountsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.db.execute(text("PRAGMA foreign_keys=ON"))
        self.assertEqual(self.db.execute(text("PRAGMA foreign_keys")).scalar(), 1)
        self.root = make_user(self.db, username="root", role=ROLE_GLOBAL_ADMIN)
        self.target = make_user(
            self.db, username="target", role=ROLE_TARGET, is_active=False
        )
        self.target_id = self.target.id
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.root
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.db.rollback()
        self.db.execute(text("PRAGMA foreign_keys=OFF"))
        close_session(self.db)

    def make_default_project(self, owner_id: int, *, fields: int) -> int:
        project = Project(name="預設專案", owner_user_id=owner_id, is_default=True)
        self.db.add(project)
        self.db.flush()
        system = System(project_id=project.id, name="預設系統", is_default=True)
        self.db.add(system)
        self.db.flush()
        self.db.add(
            ProjectMember(project_id=project.id, user_id=owner_id, role="project_admin")
        )
        for i in range(fields):
            self.db.add(
                SystemRequirementField(
                    system_id=system.id,
                    agent_group="cost",
                    field_key=f"k{i}",
                    value="v",
                    updated_by=owner_id,
                )
            )
        self.db.commit()
        return project.id

    def audit_outcomes(self, audit_mock) -> list:
        # `_audit_append(title, request_raw, outcome, approver)`：第三個位置引數是結果描述。
        return [c.args[2] for c in audit_mock.call_args_list]

    def test_delete_endpoint_audit_records_purged_counts(self):
        """
        @purpose 刪除使用者成功時，稽核訊息寫出連帶清除的專案／系統／需求欄位筆數
        @given 已停用的 target 只擁有一個空預設專案（1 個系統、2 筆需求欄位值）
        @step 管理員 DELETE /api/auth/{target} | 回 200
        @pass 稽核結果描述含「空預設專案 1 筆、系統 1 筆、需求欄位值 2 筆」
        @api DELETE /api/auth/{user_id} -> 200 | 刪除使用者並寫稽核筆數
        @story US9.1
        """
        self.make_default_project(self.target_id, fields=2)
        with patch("services.user_router._audit_append") as audit:
            res = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(res.status_code, 200, res.text)
        outcomes = self.audit_outcomes(audit)
        self.assertEqual(len(outcomes), 1)
        self.assertIn("空預設專案 1 筆、系統 1 筆、需求欄位值 2 筆", outcomes[0])

    def test_reject_endpoint_audit_records_purged_counts(self):
        """
        @purpose 拒絕授權申請並刪除帳號時，稽核訊息同樣寫出清除筆數
        @given 待核准的 pending 帳號有一筆申請與一個空預設專案（1 個系統、1 筆需求欄位值）
        @step 管理員 POST /api/auth/authorization-requests/{id}/reject | 回 200
        @pass 稽核結果描述含「空預設專案 1 筆、系統 1 筆、需求欄位值 1 筆」
        @api POST /api/auth/authorization-requests/{request_id}/reject -> 200 | 拒絕並刪除帳號
        @story US9.1
        """
        pending = make_user(
            self.db, username="pending", role=None, authorization_status="pending"
        )
        req = RoleAuthorizationRequest(
            user_id=pending.id, requested_role=ROLE_TARGET, status="pending"
        )
        self.db.add(req)
        self.db.commit()
        self.make_default_project(pending.id, fields=1)
        with patch("services.user_router._audit_append") as audit:
            res = self.client.post(f"/api/auth/authorization-requests/{req.id}/reject")
        self.assertEqual(res.status_code, 200, res.text)
        outcomes = self.audit_outcomes(audit)
        self.assertEqual(len(outcomes), 1)
        self.assertIn("空預設專案 1 筆、系統 1 筆、需求欄位值 1 筆", outcomes[0])

    def test_delete_without_default_project_records_zero_counts(self):
        """
        @purpose 沒有任何連帶清除時，稽核訊息仍明寫 0 筆（不是省略）
        @given 已停用的 target 沒有任何專案
        @step 管理員 DELETE /api/auth/{target} | 回 200
        @pass 稽核結果描述含「空預設專案 0 筆、系統 0 筆、需求欄位值 0 筆」
        @api DELETE /api/auth/{user_id} -> 200 | 無連帶清除
        @story US9.1
        """
        with patch("services.user_router._audit_append") as audit:
            res = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(res.status_code, 200, res.text)
        self.assertIn(
            "空預設專案 0 筆、系統 0 筆、需求欄位值 0 筆", self.audit_outcomes(audit)[0]
        )

    def test_blocked_delete_409_detail_carries_next_step_hint(self):
        """
        @purpose 被擋下的刪除，409 的 detail 告訴管理員下一步（維持停用）
        @given 已停用的 target 擁有一個非預設專案
        @step 管理員 DELETE /api/auth/{target} | 回 409
        @pass detail 仍列出擋下的類別，且含「請維持停用帳號」；不寫成功稽核
        @api DELETE /api/auth/{user_id} -> 409 | 刪除被擋下
        @story US9.1
        """
        project = Project(name="P", owner_user_id=self.target_id, is_default=False)
        self.db.add(project)
        self.db.commit()
        with patch("services.user_router._audit_append") as audit:
            res = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(res.status_code, 409, res.text)
        detail = res.json()["detail"]
        self.assertIn("非空或非預設的專案", detail)
        self.assertIn("請維持停用帳號", detail)
        self.assertEqual(audit.call_count, 0)


if __name__ == "__main__":
    unittest.main()
