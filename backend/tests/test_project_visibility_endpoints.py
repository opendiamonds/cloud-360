"""`U23 project-pages-ui`：兩支列舉端點的 allow／deny 雙向測試（`BR87.5`、`PPN-11`–`PPN-13`）。

`GET /api/hierarchy/projects` 與 `GET /api/hierarchy/projects/{project_id}/systems`
自 `U23` 起改為成員範圍（`[PP1]`=A、`[PP3]`=A）。本檔以五種身分 × 兩支端點斷言狀態碼
與內容，另加缺 `K2` 與「不存在 vs 不可見」的逐位元比較。身分的構造見
`tests/test_project_visibility_queries.py` 的 `VisibilityWorld`。

`team.md` 規則 A ＋ B：授權行為改變（列舉放寬）→ allow 與 deny 兩側都要有會紅的斷言；
端點修改 → `TestClient` 斷言狀態碼與回應欄位集合。授權不 mock：走真實 facade 與 `user_can`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from database import get_db
from main import app
from services.auth import get_current_user
from services.hierarchy_facade import HierarchyFacade, HierarchyForbidden, mint_principal
from tests.helpers import close_session, make_session, make_user
from tests.test_project_visibility_queries import ROLE_NON_CANONICAL, VisibilityWorld

PROJECT_FIELDS = {"id", "name", "owner_user_id", "is_default", "created_at"}
SYSTEM_FIELDS = {"id", "project_id", "name", "is_default", "created_at"}


class VisibilityEndpointTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.w = VisibilityWorld(self.db)
        self.sys1 = self.w.add_system(self.w.p1, "S1")
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def project_ids(self, user) -> list:
        response = self.client_as(user).get("/api/hierarchy/projects")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        for row in body:
            self.assertEqual(set(row), PROJECT_FIELDS)
        return [row["id"] for row in body]

    def systems(self, user, project_id):
        return self.client_as(user).get(f"/api/hierarchy/projects/{project_id}/systems")


class ProjectListIdentityTest(VisibilityEndpointTestBase):
    """專案清單：五種身分皆 200，斷言是否含目標專案。"""

    def test_E1_owner_with_member_row_lists_project(self):
        """① 擁有者且有成員列 → 清單含目標。

        @purpose 建立者在專案清單看得到自己的專案。
        @story AC12.6.3
        @api GET /api/hierarchy/projects
        """
        self.assertIn(self.w.p1.id, self.project_ids(self.w.owner))

    def test_E2_invited_member_lists_project(self):
        """② 被邀請的成員 → 清單含目標（`[PP1]`=A 的放寬本身）。

        @purpose 被邀請的成員在專案清單看得到該專案，而他不是擁有者。
        @story AC12.6.3
        @api GET /api/hierarchy/projects
        """
        self.assertEqual(self.project_ids(self.w.member), [self.w.p1.id])

    def test_E3_member_of_another_project_does_not_list_target(self):
        """③ 另一專案的成員 → 清單不含目標。

        @purpose 非成員看不到專案（只看得到自己是成員的那一個）。
        @story AC12.1.3
        @api GET /api/hierarchy/projects
        """
        self.assertEqual(self.project_ids(self.w.other_member), [self.w.p_other.id])

    def test_E4_removed_owner_does_not_list_project(self):
        """④ 被移出的擁有者 → 清單不含目標。

        @purpose 被另一位管理者移出的建立者，在專案清單看不到該專案。
        @story AC12.6.2
        @api GET /api/hierarchy/projects
        """
        self.assertNotIn(self.w.p4.id, self.project_ids(self.w.removed_owner))

    def test_E5_owner_of_zero_member_project_lists_it(self):
        """⑤ 零成員列專案的擁有者 → 清單含目標（回填前）。

        @purpose 回填未跑時，擁有者仍看得到自己的專案。
        @story AC12.6.3
        @api GET /api/hierarchy/projects
        """
        self.assertEqual(self.project_ids(self.w.zero_owner), [self.w.p5.id])


class SystemListIdentityTest(VisibilityEndpointTestBase):
    """系統清單：可見者 200、不可見者 404。"""

    def test_E6_owner_with_member_row_gets_200(self):
        """① → 200，內容為該專案的系統。

        @purpose 建立者打得開自己的專案。
        @story AC12.6.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        response = self.systems(self.w.owner, self.w.p1.id)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([s["id"] for s in response.json()], [self.sys1.id])
        self.assertEqual(set(response.json()[0]), SYSTEM_FIELDS)

    def test_E7_invited_member_gets_200(self):
        """② → 200（成員打得開專案；非擁有者）。

        @purpose 被邀請的成員看得到專案的系統。
        @story AC12.6.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        response = self.systems(self.w.member, self.w.p1.id)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([s["id"] for s in response.json()], [self.sys1.id])

    def test_E8_member_of_another_project_gets_404(self):
        """③ → 404。

        @purpose 非成員以網址直接打開專案得到「查不到」，而不是空清單。
        @story AC12.1.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.systems(self.w.other_member, self.w.p1.id).status_code, 404)

    def test_E9_removed_owner_gets_404(self):
        """④ → 404。

        @purpose 被移出的建立者以網址直接打開專案得到「查不到」。
        @story AC12.6.2
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.systems(self.w.removed_owner, self.w.p4.id).status_code, 404)

    def test_E10_owner_of_zero_member_project_gets_200(self):
        """⑤ → 200。

        @purpose 回填未跑時，擁有者打得開自己的專案。
        @story AC12.6.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        response = self.systems(self.w.zero_owner, self.w.p5.id)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])


class MissingK2Test(VisibilityEndpointTestBase):
    """缺 `K2 view`（非 canonical role）：兩支端點一律 403。"""

    def test_E11_non_canonical_member_is_denied_project_list(self):
        """非 canonical role、但**是**某專案的成員 → 專案清單 403。

        @purpose 全域功能權限是第一層，成員身分不能替代它。
        @story AC12.1.3
        @api GET /api/hierarchy/projects
        """
        self.w.add_member(self.w.p1, self.w.noncanon, "member")
        self.assertEqual(
            self.client_as(self.w.noncanon).get("/api/hierarchy/projects").status_code, 403
        )

    def test_E12_non_canonical_with_empty_visible_set_is_still_denied(self):
        """可見集合為空的非 canonical 使用者 → 仍 403，不是 200 `[]`（`M5` 的必要構造）。

        @purpose `K2` 判定在可見集合為空時也必須發生。
        @story AC12.1.3
        @api GET /api/hierarchy/projects
        """
        lone = make_user(self.db, username="lone-noncanon", role=ROLE_NON_CANONICAL)
        self.assertEqual(
            self.client_as(lone).get("/api/hierarchy/projects").status_code, 403
        )

    def test_E13_non_canonical_is_denied_system_list_of_existing_project(self):
        """系統清單對**存在**的專案 → 403（不是 404）。

        @purpose 缺 `K2` 的回應不得因專案存在與否而不同。
        @story AC12.1.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        self.w.add_member(self.w.p1, self.w.noncanon, "member")
        self.assertEqual(self.systems(self.w.noncanon, self.w.p1.id).status_code, 403)

    def test_E14_non_canonical_is_denied_system_list_of_missing_project(self):
        """系統清單對**不存在**的專案 → 403。

        @purpose 缺 `K2` 者連「存不存在」都得不到。
        @story AC12.1.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        missing = self.w.never_existed_project_id()
        self.assertEqual(self.systems(self.w.noncanon, missing).status_code, 403)

    def test_E14b_list_systems_unscoped_itself_requires_K2(self):
        """`HierarchyFacade.list_systems_unscoped` 自身第一行即 `K2 view` 判定（`M5` 第二變體）。

        @purpose 經 HTTP 時 `project_exists` 已先判定 `K2`，故拿掉本方法的判定不會讓任何
                 HTTP 案例變紅；`K2` 判定「只有一份且不假設呼叫端已檢查」由本案直接鎖住。
        @story AC12.1.3
        """
        with self.assertRaises(HierarchyForbidden):
            HierarchyFacade(self.db).list_systems_unscoped(
                mint_principal(self.w.noncanon), project_id=self.w.p1.id
            )
        with self.assertRaises(HierarchyForbidden):
            HierarchyFacade(self.db).list_projects_by_ids(
                mint_principal(self.w.noncanon), project_ids=[]
            )


class NotFoundIndistinguishableTest(VisibilityEndpointTestBase):
    def test_E15_missing_and_invisible_project_are_byte_identical(self):
        """`PPN-13`：「從未存在的 id」與「③ 不可見的既有 id」→ 狀態碼相等且本體逐位元相等。

        @purpose 以 id 枚舉系統清單，無法分辨專案存在與否（不構成存在性預言機）。
        @story AC12.1.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        missing = self.systems(self.w.other_member, self.w.never_existed_project_id())
        invisible = self.systems(self.w.other_member, self.w.p1.id)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invisible.status_code, missing.status_code)
        self.assertEqual(invisible.content, missing.content)
        self.assertEqual(invisible.json(), {"detail": "查不到專案"})


if __name__ == "__main__":
    unittest.main()
