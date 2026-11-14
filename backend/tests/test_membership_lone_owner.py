"""合併前必修第 21 列：獨自一人的專案不擋停用（2026-10-25 使用者裁決）。

缺陷：停用守門 `projects_losing_last_admin` 對「該使用者是管理者、且除他以外
沒有任何合格成員」的專案一律擋下。只有自己一位成員的專案（**包含每位持圖使用者
的預設專案**）因此讓擁有者停用不了（409），而刪除端點要求先停用——這類使用者
既停用不了也刪除不了。

新規則：除被停用者之外**沒有任何成員**（不論合格與否）時放行；有其他成員但
皆不合格時仍擋下（第 1 列的判準不變）。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 拿掉放行條件（`project_id in projects_with_others and`）→ 案例 1、3 紅；
  M2 放行條件誤寫為不看其他成員（守門一律放行）→ 案例 2 紅。

SQLite 外鍵必須打開，理由同 `test_user_delete_hierarchy.py`：不開的話刪除端點的
「擋下」類斷言可能恆真。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from sqlalchemy import text
from starlette.testclient import TestClient

from database import get_db
from main import app
from models import Project, ProjectMember, System, User
from services.auth import get_current_user
from tests.helpers import close_session, make_session, make_user

ROLE_GLOBAL_ADMIN = "Platform_Admin"  # J3a view+edit：停用與刪除端點都需要它
ROLE_TARGET = "Project_Architect"      # K3 view+edit：本身是合格管理者
ROLE_UNQUALIFIED = "Developer"         # 只有 K3.view：不是合格接手人


class LoneOwnerTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.db.execute(text("PRAGMA foreign_keys=ON"))
        self.assertEqual(
            self.db.execute(text("PRAGMA foreign_keys")).scalar(),
            1,
            "SQLite 外鍵未啟用，刪除端點的擋下類斷言會失去鑑別力",
        )
        self.root = make_user(self.db, username="root", role=ROLE_GLOBAL_ADMIN)
        self.target = make_user(self.db, username="target", role=ROLE_TARGET)
        self.other = make_user(self.db, username="other", role=ROLE_UNQUALIFIED)
        self.target_id = self.target.id
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.root
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.db.rollback()
        self.db.execute(text("PRAGMA foreign_keys=OFF"))
        close_session(self.db)

    def make_project(self, *, is_default: bool) -> int:
        project = Project(
            name="target 的專案", owner_user_id=self.target_id, is_default=is_default
        )
        self.db.add(project)
        self.db.flush()
        self.db.add(System(project_id=project.id, name="預設系統", is_default=True))
        self.db.add(
            ProjectMember(
                project_id=project.id, user_id=self.target_id, role="project_admin"
            )
        )
        self.db.commit()
        return project.id

    def deactivate(self):
        return self.client.put(
            f"/api/auth/{self.target_id}/active", json={"is_active": False}
        )

    def is_active(self) -> bool:
        self.db.expire_all()
        return self.db.query(User).filter(User.id == self.target_id).one().is_active


class LoneOwnerTest(LoneOwnerTestBase):
    def test_lone_owner_of_default_project_can_be_deactivated_then_deleted(self):
        """
        @purpose 只有自己一位成員的預設專案擁有者，可以先停用、再刪除
        @given target 是空預設專案（含預設系統、無圖）的唯一成員與 project_admin
        @step 平台管理員 PUT /api/auth/{id}/active 停用 → DELETE /api/auth/{id}
        @pass 停用 200 且 is_active 為 False；刪除 200；專案與系統隨使用者清除
        @api PUT /api/auth/{user_id}/active -> 200 | 停用獨人專案的擁有者
        @api DELETE /api/auth/{user_id} -> 200 | 空預設專案隨使用者清除
        @story US12.3
        """
        project_id = self.make_project(is_default=True)

        res = self.deactivate()
        self.assertEqual(res.status_code, 200, res.text)
        self.assertFalse(self.is_active())

        deleted = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.db.expire_all()
        self.assertIsNone(self.db.query(User).filter(User.id == self.target_id).first())
        self.assertIsNone(self.db.query(Project).filter(Project.id == project_id).first())
        self.assertEqual(
            self.db.query(System).filter(System.project_id == project_id).count(), 0
        )

    def test_unqualified_other_member_still_blocks_deactivation(self):
        """
        @purpose 有其他成員但皆不合格時，停用仍被擋下（第 1 列判準不變）
        @given target 是專案唯一 project_admin，另有一位只有 K3.view 的一般成員
        @step 平台管理員 PUT /api/auth/{id}/active 停用
        @pass 409，回應列出該專案；is_active 仍為 True（檢查在寫入之前）
        @api PUT /api/auth/{user_id}/active -> 409 | 另有不合格成員時仍擋下
        @story US12.3
        """
        project_id = self.make_project(is_default=True)
        self.db.add(
            ProjectMember(project_id=project_id, user_id=self.other.id, role="member")
        )
        self.db.commit()

        res = self.deactivate()
        self.assertEqual(res.status_code, 409, res.text)
        self.assertIn(
            project_id, [ref["project_id"] for ref in res.json()["projects"]]
        )
        self.assertTrue(self.is_active())

    def test_lone_owner_of_non_default_project_is_deactivated_but_delete_still_409(self):
        """
        @purpose 非預設的獨人專案：停用放行，刪除仍依規則 2 回 409（不靜默刪專案）
        @given target 是一個非預設專案的唯一成員與 project_admin
        @step 停用 → 刪除
        @pass 停用 200；刪除 409 且 blocking_references 含 owned_projects；專案仍在
        @api PUT /api/auth/{user_id}/active -> 200 | 停用獨人專案的擁有者
        @api DELETE /api/auth/{user_id} -> 409 | 非預設專案仍擋刪除
        @story US12.3
        """
        project_id = self.make_project(is_default=False)

        self.assertEqual(self.deactivate().status_code, 200)
        self.assertFalse(self.is_active())

        deleted = self.client.delete(f"/api/auth/{self.target_id}")
        self.assertEqual(deleted.status_code, 409, deleted.text)
        categories = {
            ref["category"] for ref in deleted.json()["blocking_references"]
        }
        self.assertIn("owned_projects", categories)
        self.db.expire_all()
        self.assertIsNotNone(
            self.db.query(Project).filter(Project.id == project_id).first()
        )


if __name__ == "__main__":
    unittest.main()
