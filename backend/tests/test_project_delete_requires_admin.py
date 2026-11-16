"""合併前必修第 25 列：刪除專案與系統要求呼叫者為該專案 `project_admin`。

缺陷：`hierarchy_facade.delete_project`／`delete_system` 在可見性守門之後只做擁有者
檢查（`projects.owner_user_id`），不查 per-project 角色。建立者可被另一位管理者降為
一般成員（`MembershipFacade.change_role` 不排除擁有者——本檔案例 1 以 HTTP 實際走過
一次，即可達性的證明），降級後仍能刪除整個專案，連帶刪除其他管理者的成員列與全部
系統的需求欄位值。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 `delete_project` 拿掉 `project_admin` 檢查 → 案例 1 紅；
  M2 `delete_system` 拿掉同一檢查 → 案例 2 紅；
  M3 `can_administer_project` 一律回 False → 案例 3 紅（allow 側）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import Project, ProjectMember, System
from services.auth import get_current_user
from services.hierarchy_facade import PROJECT_ADMIN_REQUIRED_DETAIL, mint_principal
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole
from tests.helpers import close_session, make_session, make_user

ROLE_ARCHITECT = "Project_Architect"  # K2 view+edit、K3 view+edit


class ProjectDeleteRequiresAdminTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_ARCHITECT)
        self.bob = make_user(self.db, username="bob", role=ROLE_ARCHITECT)
        self.facade = MembershipFacade(self.db)
        self.project = self.facade.create_project_with_owner(
            mint_principal(self.alice), name="P"
        )
        self.project_id = self.project.id
        self.facade.invite_member(
            mint_principal(self.alice),
            project_id=self.project_id,
            user_id=self.bob.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def create_system(self, name: str = "S") -> int:
        res = self.client_as(self.alice).post(
            f"/api/hierarchy/projects/{self.project_id}/systems", json={"name": name}
        )
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()["id"]

    def demote_alice(self) -> None:
        """可達性：另一位管理者（bob）把建立者 alice 降為一般成員。"""
        res = self.client_as(self.bob).patch(
            f"/api/membership/projects/{self.project_id}/members/{self.alice.id}",
            json={"role": ProjectRole.MEMBER.value},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["role"], ProjectRole.MEMBER.value)

    def counts(self) -> tuple:
        self.db.expire_all()
        return (
            self.db.query(Project).filter(Project.id == self.project_id).count(),
            self.db.query(System).filter(System.project_id == self.project_id).count(),
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == self.project_id)
            .count(),
        )

    def test_demoted_creator_cannot_delete_project(self):
        """
        @purpose 被降為一般成員的建立者不能刪除專案，資料不變
        @given alice 建立專案 P（仍是 owner_user_id），bob 為另一位管理者並把 alice 降為一般成員
        @step alice DELETE /api/hierarchy/projects/{P} | 回 403，訊息為固定的管理者要求句
        @pass 專案、成員列筆數與刪除前相同
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 200 | 降級建立者（可達性）
        @api DELETE /api/hierarchy/projects/{project_id} -> 403 | 非管理者的擁有者
        @story AC12.6.3
        """
        self.demote_alice()
        before = self.counts()
        res = self.client_as(self.alice).delete(f"/api/hierarchy/projects/{self.project_id}")
        self.assertEqual(res.status_code, 403, res.text)
        self.assertEqual(res.json()["detail"], PROJECT_ADMIN_REQUIRED_DETAIL)
        self.assertEqual(self.counts(), before)
        self.assertEqual(before[0], 1)

    def test_demoted_creator_cannot_delete_system(self):
        """
        @purpose 被降為一般成員的建立者不能刪除專案底下的系統
        @given alice 建立專案 P 與系統 S，之後被 bob 降為一般成員
        @step alice DELETE /api/hierarchy/systems/{S} | 回 403
        @pass 系統仍在
        @api DELETE /api/hierarchy/systems/{system_id} -> 403 | 非管理者的擁有者
        @story AC12.6.3
        """
        system_id = self.create_system()
        self.demote_alice()
        res = self.client_as(self.alice).delete(f"/api/hierarchy/systems/{system_id}")
        self.assertEqual(res.status_code, 403, res.text)
        self.assertEqual(res.json()["detail"], PROJECT_ADMIN_REQUIRED_DETAIL)
        self.db.expire_all()
        self.assertIsNotNone(self.db.query(System).filter(System.id == system_id).first())

    def test_creator_who_is_still_admin_can_delete_system_then_project(self):
        """
        @purpose 仍為管理者的建立者照常刪除（allow 側；沒有它，永遠 403 的實作也會通過）
        @given alice 建立專案 P 與系統 S，仍是 project_admin
        @step alice DELETE /api/hierarchy/systems/{S} → DELETE /api/hierarchy/projects/{P}
        @pass 兩者皆 204，專案與系統皆不存在
        @api DELETE /api/hierarchy/systems/{system_id} -> 204 | 管理者刪除系統
        @api DELETE /api/hierarchy/projects/{project_id} -> 204 | 管理者刪除專案
        @story AC12.6.3
        """
        system_id = self.create_system()
        client = self.client_as(self.alice)
        self.assertEqual(client.delete(f"/api/hierarchy/systems/{system_id}").status_code, 204)
        self.assertEqual(
            client.delete(f"/api/hierarchy/projects/{self.project_id}").status_code, 204
        )
        self.assertEqual(self.counts()[:2], (0, 0))

    def test_non_owner_admin_still_gets_404_not_403(self):
        """
        @purpose 新檢查排在擁有者檢查之後：非擁有者的管理者仍得 404（不改變既有回應形狀）
        @given bob 是 P 的 project_admin 但不是擁有者
        @step bob DELETE /api/hierarchy/projects/{P}
        @pass 404（與既有擁有者檢查相同），專案仍在
        @api DELETE /api/hierarchy/projects/{project_id} -> 404 | 非擁有者
        @story AC12.6.3
        """
        res = self.client_as(self.bob).delete(f"/api/hierarchy/projects/{self.project_id}")
        self.assertEqual(res.status_code, 404, res.text)
        self.assertEqual(self.counts()[0], 1)


if __name__ == "__main__":
    unittest.main()
