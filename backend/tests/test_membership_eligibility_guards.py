"""合併前必修第 31 列 (a)(e)(f)：管理者計數、升任與全域層一律套合格判定。

- (a) `admin_count_after` 只數**合格**管理者：另一位管理者已停用或待核准時，最後一位
  合格管理者不得自我降級或自我移出（原本按原始列數計，會留下無人能管的專案）。
- (e) `change_role` 升為 `project_admin` 時要求對象合格（啟用、已核准、全域 `K3.edit`）。
- (f) `_authorize_global` 擋待核准的 principal；重選橫幅兩方法補全域層 `K3.view` 判定。

allow／deny 雙向（`team.md` 規則 A ＋ B）。(a)(e) 走 HTTP（`TestClient`），(f) 直呼
facade——它防的是同進程呼叫端（HTTP 端點本來就有 `require_story_action`）。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 `admin_count_after` 拿掉合格判定（回到原始列數）→ (a) 兩個 deny 案紅；
  M2 `change_role` 拿掉升任檢查 → (e) deny 案紅；
  M3 `_authorize_global` 拿掉 `is_approved` → (f) 待核准案紅；
  M4 橫幅兩方法拿掉 `_authorize_global` → (f) 橫幅 deny 案紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import ProjectMember, User
from services.auth import get_current_user
from services.hierarchy_facade import mint_principal
from services.membership_errors import MembershipForbidden
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole
from tests.helpers import close_session, make_session, make_user

ROLE_K3_EDIT = "Project_Architect"  # K3 view+edit：合格管理者
ROLE_K3_VIEW = "Developer"          # 只有 K3.view：不合格
ROLE_NO_K3 = "SRE"                  # 無 K3


class EligibilityTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_K3_EDIT)
        self.bob = make_user(self.db, username="bob", role=ROLE_K3_EDIT)
        self.carol = make_user(self.db, username="carol", role=ROLE_K3_VIEW)
        self.facade = MembershipFacade(self.db)
        self.project = self.facade.create_project_with_owner(
            mint_principal(self.alice), name="P"
        )
        self.pid = self.project.id
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def add_member(self, user, role: str) -> None:
        self.db.add(ProjectMember(project_id=self.pid, user_id=user.id, role=role))
        self.db.commit()

    def role_of(self, user) -> str:
        self.db.expire_all()
        row = (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == self.pid, ProjectMember.user_id == user.id)
            .first()
        )
        return row.role if row else None

    def set_user(self, user, **fields) -> None:
        self.db.query(User).filter(User.id == user.id).update(fields)
        self.db.commit()

    def member_url(self, user) -> str:
        return f"/api/membership/projects/{self.pid}/members/{user.id}"


class AdminCountQualifiedOnlyTest(EligibilityTestBase):
    """(a)"""

    def test_self_demotion_blocked_when_other_admin_is_deactivated(self):
        """
        @purpose 另一位管理者已停用時，最後一位合格管理者不得自我降級
        @given alice、bob 皆為 P 的 project_admin，bob 帳號已停用
        @step alice PATCH 自己的角色為 member
        @pass 409，alice 仍為 project_admin
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 409 | 只剩停用的管理者
        @story US12.3
        """
        self.add_member(self.bob, ProjectRole.PROJECT_ADMIN.value)
        self.set_user(self.bob, is_active=False)
        res = self.client_as(self.alice).patch(
            self.member_url(self.alice), json={"role": ProjectRole.MEMBER.value}
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(self.role_of(self.alice), ProjectRole.PROJECT_ADMIN.value)

    def test_self_removal_blocked_when_other_admin_is_pending(self):
        """
        @purpose 另一位管理者待核准時，最後一位合格管理者不得自我移出
        @given alice、bob 皆為 P 的 project_admin，bob 的 J5 狀態為 pending
        @step alice DELETE 自己的成員列
        @pass 409，alice 仍是成員
        @api DELETE /api/membership/projects/{project_id}/members/{user_id} -> 409 | 只剩待核准的管理者
        @story US12.3
        """
        self.add_member(self.bob, ProjectRole.PROJECT_ADMIN.value)
        self.set_user(self.bob, authorization_status="pending")
        res = self.client_as(self.alice).delete(self.member_url(self.alice))
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(self.role_of(self.alice), ProjectRole.PROJECT_ADMIN.value)

    def test_self_demotion_allowed_when_other_admin_is_qualified(self):
        """
        @purpose allow 側：另一位管理者合格時，自我降級照常成功
        @given alice、bob 皆為 P 的 project_admin，兩人皆合格
        @step alice PATCH 自己的角色為 member
        @pass 200，alice 變成 member
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 200 | 尚有合格管理者
        @story US12.3
        """
        self.add_member(self.bob, ProjectRole.PROJECT_ADMIN.value)
        res = self.client_as(self.alice).patch(
            self.member_url(self.alice), json={"role": ProjectRole.MEMBER.value}
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(self.role_of(self.alice), ProjectRole.MEMBER.value)


class PromotionRequiresQualifiedTest(EligibilityTestBase):
    """(e)"""

    def test_promoting_unqualified_member_is_rejected(self):
        """
        @purpose 不得把無全域 K3.edit 的成員升為管理者
        @given carol（只有 K3.view）是 P 的一般成員
        @step alice PATCH carol 的角色為 project_admin
        @pass 422，carol 仍為 member
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 422 | 升任對象不合格
        @story US12.2
        """
        self.add_member(self.carol, ProjectRole.MEMBER.value)
        res = self.client_as(self.alice).patch(
            self.member_url(self.carol), json={"role": ProjectRole.PROJECT_ADMIN.value}
        )
        self.assertEqual(res.status_code, 422, res.text)
        self.assertEqual(self.role_of(self.carol), ProjectRole.MEMBER.value)

    def test_promoting_pending_member_is_rejected(self):
        """
        @purpose 不得把待核准帳號升為管理者（角色本身持有 K3.edit 也不行）
        @given bob（Project_Architect，但 J5 為 pending）是 P 的一般成員
        @step alice PATCH bob 的角色為 project_admin
        @pass 422，bob 仍為 member
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 422 | 升任對象待核准
        @story US12.2
        """
        self.add_member(self.bob, ProjectRole.MEMBER.value)
        self.set_user(self.bob, authorization_status="pending")
        res = self.client_as(self.alice).patch(
            self.member_url(self.bob), json={"role": ProjectRole.PROJECT_ADMIN.value}
        )
        self.assertEqual(res.status_code, 422, res.text)
        self.assertEqual(self.role_of(self.bob), ProjectRole.MEMBER.value)

    def test_promoting_qualified_member_succeeds(self):
        """
        @purpose allow 側：合格成員照常升任
        @given bob（Project_Architect，已核准、啟用）是 P 的一般成員
        @step alice PATCH bob 的角色為 project_admin
        @pass 200，bob 為 project_admin
        @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 200 | 升任合格成員
        @story US12.2
        """
        self.add_member(self.bob, ProjectRole.MEMBER.value)
        res = self.client_as(self.alice).patch(
            self.member_url(self.bob), json={"role": ProjectRole.PROJECT_ADMIN.value}
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(self.role_of(self.bob), ProjectRole.PROJECT_ADMIN.value)


class GlobalLayerTest(EligibilityTestBase):
    """(f)：同進程呼叫端直呼 facade。"""

    def test_pending_principal_is_denied_by_the_global_layer(self):
        """
        @purpose 待核准帳號的 principal 不得通過全域層（同進程呼叫端無 require_story_action）
        @given alice 是 P 的 project_admin，但其 J5 狀態改為 pending
        @step 以 alice 的 principal 直呼 facade.list_members
        @pass raise MembershipForbidden；改回 approved 後同一呼叫成功
        @story US12.5
        """
        self.set_user(self.alice, authorization_status="pending")
        self.db.refresh(self.alice)
        with self.assertRaises(MembershipForbidden):
            MembershipFacade(self.db).list_members(
                mint_principal(self.alice), project_id=self.pid
            )
        self.set_user(self.alice, authorization_status="approved")
        self.db.refresh(self.alice)
        members = MembershipFacade(self.db).list_members(
            mint_principal(self.alice), project_id=self.pid
        )
        self.assertEqual(len(members), 1)

    def test_reselection_banner_methods_require_k3_view(self):
        """
        @purpose 重選橫幅兩方法自己判全域層 K3.view，不依賴呼叫端
        @given dave 的全域角色無 K3；carol 只有 K3.view
        @step 以 dave 直呼 list_my_pending_reselections 與 acknowledge_reselection；以 carol 再呼叫一次
        @pass dave 兩者皆 raise MembershipForbidden；carol 回空清單且 acknowledge 回 False
        @story US12.4
        """
        dave = make_user(self.db, username="dave", role=ROLE_NO_K3)
        facade = MembershipFacade(self.db)
        with self.assertRaises(MembershipForbidden):
            facade.list_my_pending_reselections(mint_principal(dave))
        with self.assertRaises(MembershipForbidden):
            facade.acknowledge_reselection(mint_principal(dave), event_id=1)
        self.assertEqual(facade.list_my_pending_reselections(mint_principal(self.carol)), [])
        self.assertFalse(facade.acknowledge_reselection(mint_principal(self.carol), event_id=999))


if __name__ == "__main__":
    unittest.main()
