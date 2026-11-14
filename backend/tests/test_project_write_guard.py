"""`U23 project-pages-ui`：三條寫入路徑的可見性守門（functional-design `R-01` 使用者裁決）。

`POST /api/hierarchy/projects/{project_id}/systems`、`DELETE /api/hierarchy/projects/{project_id}`、
`DELETE /api/hierarchy/systems/{system_id}` 三條路徑套用與列舉相同的可見性判準（`[PP3]`=A）：
被另一位管理者移出的建立者（`owner_user_id` 仍是他）不得再建立系統、刪除專案或系統。

矩陣（`security-design.md` §二之三）：

| 案 | 請求者 | 期待 |
|---|---|---|
| (a) | 擁有者且為成員 | 201／204 |
| (b) | 被移出的擁有者 | 404，四表列數不變 |
| (c) | 零成員列專案的擁有者 | 201／204 |
| (d) | 成員但非擁有者 | 404（既有擁有者檢查） |
| (e) | 被移出的擁有者刪「底下仍有系統」的專案 | 404，不是 409 |
| (e') | 被移出的擁有者刪「底下仍有架構圖」的系統 | 404，不是 409 |
| (f) | `Developer`（`K2` view 有、edit 無）的非成員 | 403，不是 404 |
| (g) | 不存在的 id vs (b) 的同一請求者 | 本體逐位元相等 |

(a)–(e') 的請求者皆持具 `K2 edit` 的 `Project_Editor`，否則會先在 403 停下而測不到守門。
另有 `[PPD1]`=A 的兩案：成功刪除時 log 含刪除者 `actor_user_id`、不含專案名或系統名。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import Project, ProjectMember, System, SystemRequirementField, UserDiagram
from services.auth import get_current_user
from tests.helpers import close_session, make_diagram, make_session
from tests.test_project_visibility_queries import VisibilityWorld

LOGGER = "cloud360.hierarchy_facade"


class WriteGuardTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.w = VisibilityWorld(self.db)
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    # -- 三條路徑 ---------------------------------------------------------

    def create_system(self, user, project_id, name="new-system"):
        return self.client_as(user).post(
            f"/api/hierarchy/projects/{project_id}/systems", json={"name": name}
        )

    def delete_project(self, user, project_id):
        return self.client_as(user).delete(f"/api/hierarchy/projects/{project_id}")

    def delete_system(self, user, system_id):
        return self.client_as(user).delete(f"/api/hierarchy/systems/{system_id}")

    # -- 構造 -------------------------------------------------------------

    def system_with_field(self, project, name: str) -> System:
        """建一個系統並為它寫一列需求欄位值（使「連帶刪除」有東西可刪）。"""
        system = self.w.add_system(project, name)
        self.db.add(
            SystemRequirementField(
                system_id=system.id,
                agent_group="cost",
                field_key="budget",
                value="100",
                updated_by=self.w.admin2.id,
            )
        )
        self.db.commit()
        return system

    def counts(self) -> tuple:
        self.db.expire_all()
        return (
            self.db.query(Project).count(),
            self.db.query(System).count(),
            self.db.query(ProjectMember).count(),
            self.db.query(SystemRequirementField).count(),
        )


class GuardAllowTest(WriteGuardTestBase):
    """(a)、(c)：可見的擁有者照常寫入。"""

    def test_a_create_system_owner_member_201(self):
        """(a) 建立系統：擁有者且為成員 → 201。

        @purpose 守門不得誤擋合法的擁有者。
        @story AC11.1.3
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.create_system(self.w.owner, self.w.p1.id).status_code, 201)

    def test_a_delete_project_owner_member_204(self):
        """(a) 刪除專案：擁有者且為成員、底下無系統 → 204。

        @purpose 守門不得誤擋合法的擁有者刪除空專案。
        @story AC12.6.3
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.assertEqual(self.delete_project(self.w.owner, self.w.p1.id).status_code, 204)

    def test_a_delete_system_owner_member_204(self):
        """(a) 刪除系統：擁有者且為成員、底下無架構圖 → 204。

        @purpose 守門不得誤擋合法的擁有者刪除系統。
        @story AC12.6.3
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p1, "S")
        self.assertEqual(self.delete_system(self.w.owner, system.id).status_code, 204)

    def test_c_create_system_zero_member_owner_201(self):
        """(c) 建立系統：零成員列專案的擁有者 → 201。

        @purpose 回填未跑時，擁有者仍能在自己的專案建系統。
        @story AC11.1.3
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.create_system(self.w.zero_owner, self.w.p5.id).status_code, 201)

    def test_c_delete_project_zero_member_owner_204(self):
        """(c) 刪除專案：零成員列專案的擁有者 → 204。

        @purpose 回填未跑時，擁有者仍能刪除自己的空專案。
        @story AC12.6.3
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.assertEqual(self.delete_project(self.w.zero_owner, self.w.p5.id).status_code, 204)

    def test_c_delete_system_zero_member_owner_204(self):
        """(c) 刪除系統：零成員列專案的擁有者 → 204。

        @purpose 回填未跑時，擁有者仍能刪除自己專案的系統。
        @story AC12.6.3
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p5, "S5")
        self.assertEqual(self.delete_system(self.w.zero_owner, system.id).status_code, 204)


class GuardDenyTest(WriteGuardTestBase):
    """(b)、(d)、(e)、(e')、(f)：不可見者、非擁有者與缺 `K2 edit` 者。"""

    def test_b_create_system_removed_owner_404_no_change(self):
        """(b) 建立系統：被移出的擁有者 → 404，四表列數不變。

        @purpose 被移出的建立者不能再於該專案建立系統（拿掉守門 → 201，`G1`）。
        @story AC12.6.2
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        before = self.counts()
        self.assertEqual(self.create_system(self.w.removed_owner, self.w.p4.id).status_code, 404)
        self.assertEqual(self.counts(), before)

    def test_b_delete_project_removed_owner_404_no_change(self):
        """(b) 刪除專案：被移出的擁有者對空專案 → 404，四表列數不變。

        @purpose 被移出的建立者不能刪除專案——否則連帶刪掉其他管理者的成員列（`G1`）。
        @story AC12.6.2
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        before = self.counts()
        self.assertEqual(self.delete_project(self.w.removed_owner, self.w.p4.id).status_code, 404)
        self.assertEqual(self.counts(), before)

    def test_b_delete_system_removed_owner_404_no_change(self):
        """(b) 刪除系統：被移出的擁有者 → 404，四表列數不變。

        @purpose 被移出的建立者不能刪除系統——否則連帶刪掉其他成員所填的需求欄位值（`G1`）。
        @story AC12.6.2
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.system_with_field(self.w.p4, "S4")
        before = self.counts()
        self.assertEqual(self.delete_system(self.w.removed_owner, system.id).status_code, 404)
        self.assertEqual(self.counts(), before)

    def test_d_create_system_member_not_owner_404(self):
        """(d) 建立系統：成員但非擁有者 → 404（既有擁有者檢查）。

        @purpose 本單元不放寬建立系統的擁有者限制（`BR87.6`）。
        @story AC11.1.1
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.create_system(self.w.member, self.w.p1.id).status_code, 404)

    def test_d_delete_project_member_not_owner_404(self):
        """(d) 刪除專案：成員但非擁有者 → 404。

        @purpose 成員不能刪除別人擁有的專案。
        @story AC12.6.3
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.assertEqual(self.delete_project(self.w.member, self.w.p1.id).status_code, 404)

    def test_d_delete_system_member_not_owner_404(self):
        """(d) 刪除系統：成員但非擁有者 → 404。

        @purpose 成員不能刪除別人擁有的專案底下的系統。
        @story AC12.6.3
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p1, "S")
        self.assertEqual(self.delete_system(self.w.member, system.id).status_code, 404)

    def test_e_delete_project_with_systems_removed_owner_404_not_409(self):
        """(e) 被移出的擁有者刪「底下仍有系統」的專案 → 404，不是 409。

        @purpose 409 的剩餘系統數不得外洩給看不到該專案的人（守門早於 409，`G3`）。
        @story AC12.6.2
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.system_with_field(self.w.p4, "S4")
        before = self.counts()
        response = self.delete_project(self.w.removed_owner, self.w.p4.id)
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.counts(), before)

    def test_e2_delete_system_with_diagram_removed_owner_404_not_409(self):
        """(e') 被移出的擁有者刪「底下仍有架構圖」的系統 → 404，不是 409。

        @purpose 409 的架構圖張數不得外洩給看不到該專案的人（`G3` 對 `delete_system`）。
        @story AC12.6.2
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.system_with_field(self.w.p4, "S4")
        diagram = make_diagram(self.db, owner=self.w.admin2)
        self.db.query(UserDiagram).filter(UserDiagram.id == diagram.id).update(
            {"system_id": system.id}
        )
        self.db.commit()
        before = self.counts()
        response = self.delete_system(self.w.removed_owner, system.id)
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.counts(), before)

    def test_f_create_system_developer_403_not_404(self):
        """(f) 建立系統：`Developer` 非成員 → 403，不是 404。

        @purpose `K2 edit` 判定先於守門（守門提前 → 404，`G2`）。
        @story AC12.6.2
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        self.assertEqual(self.create_system(self.w.developer, self.w.p1.id).status_code, 403)

    def test_f_delete_project_developer_403_not_404(self):
        """(f) 刪除專案：`Developer` 非成員 → 403。

        @purpose `K2 edit` 判定先於守門。
        @story AC12.6.2
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.assertEqual(self.delete_project(self.w.developer, self.w.p1.id).status_code, 403)

    def test_f_delete_system_developer_403_not_404(self):
        """(f) 刪除系統：`Developer` 非成員 → 403。

        @purpose `K2 edit` 判定先於取系統與守門。
        @story AC12.6.2
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p1, "S")
        self.assertEqual(self.delete_system(self.w.developer, system.id).status_code, 403)


class GuardIndistinguishableTest(WriteGuardTestBase):
    """(g)：「不存在」與「被移出者對既有資源」逐位元相同（`PPN-13`、`PPN-14c`）。"""

    def assert_identical(self, missing, invisible, detail: str) -> None:
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(invisible.status_code, missing.status_code)
        self.assertEqual(invisible.content, missing.content)
        self.assertEqual(invisible.json(), {"detail": detail})

    def test_g_create_system_missing_vs_invisible(self):
        """(g) 建立系統：不存在的專案 vs 被移出者的專案。

        @purpose 以建立系統探測專案是否存在，得到的回應完全相同。
        @story AC12.6.2
        @api POST /api/hierarchy/projects/{project_id}/systems
        """
        self.assert_identical(
            self.create_system(self.w.removed_owner, self.w.never_existed_project_id()),
            self.create_system(self.w.removed_owner, self.w.p4.id),
            "查不到專案",
        )

    def test_g_delete_project_missing_vs_invisible(self):
        """(g) 刪除專案：不存在的專案 vs 被移出者的專案。

        @purpose 以刪除專案探測專案是否存在，得到的回應完全相同。
        @story AC12.6.2
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        self.assert_identical(
            self.delete_project(self.w.removed_owner, self.w.never_existed_project_id()),
            self.delete_project(self.w.removed_owner, self.w.p4.id),
            "查不到專案",
        )

    def test_g_delete_system_missing_vs_invisible(self):
        """(g) 刪除系統：不存在的系統 vs 被移出者專案底下的系統——兩側皆為系統句。

        @purpose 以刪除系統探測系統是否存在，得到的回應完全相同（守門拋專案句 → 紅，`G6`）。
        @story AC12.6.2
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p4, "S4")
        self.assert_identical(
            self.delete_system(self.w.removed_owner, self.w.never_existed_system_id()),
            self.delete_system(self.w.removed_owner, system.id),
            "查不到系統",
        )


class DeleteActorLogTest(WriteGuardTestBase):
    """`[PPD1]`=A：成功刪除時記下刪除者。"""

    def test_log_delete_project_records_actor(self):
        """成功刪除專案 → INFO log 含 `actor_user_id=<請求者 id>`，不含專案名。

        @purpose 事後查得出是誰刪了專案（連帶刪除的成員列無法復原）。
        @story AC12.6.3
        @api DELETE /api/hierarchy/projects/{project_id}
        """
        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.delete_project(self.w.owner, self.w.p1.id)
        self.assertEqual(response.status_code, 204)
        joined = "\n".join(logs.output)
        self.assertIn(f"project_id={self.w.p1.id} actor_user_id={self.w.owner.id}", joined)
        self.assertNotIn("P1", joined)

    def test_log_delete_system_records_actor(self):
        """成功刪除系統 → INFO log 含 `actor_user_id=<請求者 id>`，不含系統名。

        @purpose 事後查得出是誰刪了系統（連帶刪除的需求欄位值無法復原）。
        @story AC12.6.3
        @api DELETE /api/hierarchy/systems/{system_id}
        """
        system = self.w.add_system(self.w.p1, "SysNameUnique")
        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.delete_system(self.w.owner, system.id)
        self.assertEqual(response.status_code, 204)
        joined = "\n".join(logs.output)
        self.assertIn(f"system_id={system.id} actor_user_id={self.w.owner.id}", joined)
        self.assertNotIn("SysNameUnique", joined)


if __name__ == "__main__":
    unittest.main()
