"""合併前必修第 3 項：刪除使用者不得回 500（`U4 hierarchy-data` 計畫步 10）。

缺陷：`projects.owner_user_id` 等十餘欄指向 `users.id` 卻**沒有** `ON DELETE`，
而預設專案由遷移／首次建圖自動建立，所以 `_hard_delete_user` 在 commit 時拋
`IntegrityError` → 500。`OQ-H1` 於 2026-10-20 裁決：**空的預設專案一併清掉，
其餘改回 409**。

七個 TestClient 案例 (a)–(g) 對應 `unit-test-instructions.md` 的同名表。

**SQLite 外鍵必須打開。** SQLite 預設不強制外鍵；不開的話 (b)–(e) 在缺陷存在時
也會綠（`db.delete(user)` 直接成功，看不到 IntegrityError），整份測試恆真。
`setUp` 以 `PRAGMA foreign_keys` 讀回 1 守門，讀不到 1 就讓整個案例失敗而非靜默放行。

不需要真實資料庫：`get_db` 與 `get_current_user` 以 `app.dependency_overrides`
覆寫；`TestClient(app)` 不觸發 startup 的 `init_db()`。`raise_server_exceptions=False`
讓未被處理的例外回成 500 回應，而不是在測試裡直接拋出——「不是 500」才是
可斷言的形狀。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from sqlalchemy import text
from starlette.testclient import TestClient

from database import get_db
from main import app
from models import (
    DiagramChangeRecord,
    Project,
    ProjectMember,
    RoleAuthorizationRequest,
    System,
    User,
    UserDiagram,
)
from services.auth import get_current_user
from tests.helpers import close_session, make_diagram, make_session, make_user

ROLE_GLOBAL_ADMIN = "Platform_Admin"  # J3a view+edit：兩個刪除路徑都需要它
ROLE_TARGET = "Developer"
CONFLICT_FIELDS = {"detail", "blocking_references"}
REFERENCE_FIELDS = {"category", "label", "count"}


class UserDeleteHierarchyBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.db.execute(text("PRAGMA foreign_keys=ON"))
        enabled = self.db.execute(text("PRAGMA foreign_keys")).scalar()
        # 守門：外鍵沒開時本檔所有「擋下」類斷言都可能恆真。
        self.assertEqual(enabled, 1, "SQLite 外鍵未啟用，本檔案例會失去鑑別力")
        self.root = make_user(self.db, username="root", role=ROLE_GLOBAL_ADMIN)
        self.alice = make_user(self.db, username="alice", role=ROLE_TARGET)
        self.target = make_user(
            self.db, username="target", role=ROLE_TARGET, is_active=False
        )
        self.target_id = self.target.id
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.root
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        # drop_all 不依外鍵拓樸刪表；外鍵開著時 DROP TABLE users 會被擋下。
        self.db.rollback()
        self.db.execute(text("PRAGMA foreign_keys=OFF"))
        close_session(self.db)

    # -- 夾具 ---------------------------------------------------------------

    def make_default_project(self, owner: User, *, with_member: bool = True):
        """遷移／首次建圖會產生的形狀：預設專案 ＋ 預設系統（＋本人成員列）。"""
        project = Project(
            name=f"{owner.username} 的專案", owner_user_id=owner.id, is_default=True
        )
        self.db.add(project)
        self.db.flush()
        system = System(project_id=project.id, name="預設系統", is_default=True)
        self.db.add(system)
        if with_member:
            self.db.add(
                ProjectMember(
                    project_id=project.id, user_id=owner.id, role="project_admin"
                )
            )
        self.db.commit()
        return project.id, system.id

    def make_plain_project(self, owner: User, name: str = "P") -> int:
        project = Project(name=name, owner_user_id=owner.id, is_default=False)
        self.db.add(project)
        self.db.flush()
        self.db.add(
            ProjectMember(project_id=project.id, user_id=owner.id, role="project_admin")
        )
        self.db.commit()
        return project.id

    # -- 查詢 ---------------------------------------------------------------

    def exists(self, model, **filters) -> bool:
        self.db.expire_all()
        return self.db.query(model).filter_by(**filters).first() is not None

    def delete_target(self):
        return self.client.delete(f"/api/auth/{self.target_id}")

    def assert_conflict_lists(self, response, category: str, label: str) -> None:
        self.assertEqual(response.status_code, 409, response.text)
        body = response.json()
        self.assertEqual(set(body), CONFLICT_FIELDS)
        categories = {ref["category"]: ref for ref in body["blocking_references"]}
        self.assertIn(category, categories, body)
        self.assertEqual(set(categories[category]), REFERENCE_FIELDS)
        self.assertGreaterEqual(categories[category]["count"], 1)
        # detail 必須仍是字串且列出該類別——既有前端以 data.detail 顯示錯誤訊息。
        self.assertIsInstance(body["detail"], str)
        self.assertIn(label, body["detail"])


class DeleteUserHierarchyTest(UserDeleteHierarchyBase):
    def test_a_empty_default_project_is_purged_with_the_user(self):
        """
        @purpose 只有空預設專案的使用者必須能被刪除，且其預設專案、系統、成員列
                 一併清掉。缺陷版本在此回 500（projects.owner_user_id 無 ON DELETE）。
        @given 已停用的 target 擁有預設專案（含預設系統與本人成員列），無架構圖
        @step 管理員 DELETE /api/auth/{target} | 回 200
        @step 查 users、projects、systems、project_members | target 與其預設專案、
              系統、成員列皆不存在
        @pass 回 200 且四類列皆已刪除
        @api DELETE /api/auth/{user_id} -> 200 | 刪除使用者並清除其空預設專案
        @story US9.1
        @note 合併前必修第 3 項／OQ-H1 規則 1。突變 M-D1（拿掉清除）使本案紅燈。
        """
        project_id, system_id = self.make_default_project(self.target)

        response = self.delete_target()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(self.exists(User, id=self.target_id))
        self.assertFalse(self.exists(Project, id=project_id))
        self.assertFalse(self.exists(System, id=system_id))
        self.assertFalse(self.exists(ProjectMember, project_id=project_id))

    def test_b_default_project_holding_a_diagram_is_not_a_500(self):
        """
        @purpose 預設專案下仍有架構圖時，刪除必須被擋下且不得是 500。
        @given target 擁有一張掛在其預設系統的架構圖
        @step 管理員 DELETE /api/auth/{target} | 回 403（既有「仍擁有架構圖」守門）或 409
        @step 查 users、projects | target 與其預設專案仍在
        @pass 狀態碼不是 500，且使用者與專案未被刪除
        @api DELETE /api/auth/{user_id} -> 403 | 仍擁有架構圖時拒絕刪除
        @story US9.1
        @note 規則 4：既有 403 不在本項範圍內改狀態碼，故斷言接受 403 或 409。
        """
        project_id, system_id = self.make_default_project(self.target)
        diagram = make_diagram(self.db, owner=self.target)
        diagram.system_id = system_id
        self.db.commit()

        response = self.delete_target()

        self.assertNotEqual(response.status_code, 500, response.text)
        self.assertIn(response.status_code, (403, 409), response.text)
        self.assertTrue(self.exists(User, id=self.target_id))
        self.assertTrue(self.exists(Project, id=project_id))

    def test_c_membership_in_another_users_project_is_a_409(self):
        """
        @purpose 使用者是他人專案的成員時必須回 409 並列出成員資格，不得刪成員列。
        @given alice 擁有專案 P；target 是 P 的 member
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 含
              project_memberships，detail 含「其他專案的成員資格」
        @step 查 users、project_members | target 與其成員列仍在
        @pass 409 且回應列出成員資格，資料未變
        @api DELETE /api/auth/{user_id} -> 409 | 仍有資料指向該使用者時拒絕刪除
        @story US9.1
        @note 突變 M-D2（拿掉預檢）會讓本案落到保底 409、清單為空 → 紅燈。
        """
        project_id = self.make_plain_project(self.alice)
        self.db.add(
            ProjectMember(project_id=project_id, user_id=self.target_id, role="member")
        )
        self.db.commit()

        response = self.delete_target()

        self.assert_conflict_lists(response, "project_memberships", "其他專案的成員資格")
        self.assertTrue(self.exists(User, id=self.target_id))
        self.assertTrue(
            self.exists(ProjectMember, project_id=project_id, user_id=self.target_id)
        )

    def test_d_change_record_actor_is_a_409_and_the_record_survives(self):
        """
        @purpose 稽核類紀錄（架構圖變更紀錄的操作者）不得被刪，刪除使用者改回 409。
        @given alice 的架構圖有一筆 diagram_change_records，操作者為 target
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 含
              diagram_change_records
        @step 查 diagram_change_records | 該筆紀錄仍在
        @pass 409 且稽核紀錄與使用者皆未被刪除
        @api DELETE /api/auth/{user_id} -> 409 | 仍有稽核紀錄指向該使用者時拒絕刪除
        @story US9.1
        @note 「稽核類紀錄不刪」是 OQ-H1 裁決的一部分，故斷言紀錄仍在而非只看狀態碼。
        """
        diagram = make_diagram(self.db, owner=self.alice)
        record = DiagramChangeRecord(
            diagram_id=diagram.id,
            source="brain_orchestration",
            actor_user_id=self.target_id,
            requirement_summary="改圖",
            requirement_label="需求",
        )
        self.db.add(record)
        self.db.commit()
        record_id = record.id

        response = self.delete_target()

        self.assert_conflict_lists(
            response, "diagram_change_records", "架構圖變更紀錄（操作者）"
        )
        self.assertTrue(self.exists(DiagramChangeRecord, id=record_id))
        self.assertTrue(self.exists(User, id=self.target_id))

    def test_e_owned_non_default_project_is_a_409(self):
        """
        @purpose 擁有非預設專案的使用者不得被刪除，專案不得被連帶清掉。
        @given target 擁有一個非預設專案（含本人成員列）
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 含
              owned_projects
        @step 查 projects | 該專案仍在
        @pass 409 且專案與使用者皆未被刪除
        @api DELETE /api/auth/{user_id} -> 409 | 仍擁有專案時拒絕刪除
        @story US9.1
        @note 規則 1 只清「預設且空」的專案；本案守住它不被放寬成清掉所有專案。
        """
        project_id = self.make_plain_project(self.target, name="自建專案")

        response = self.delete_target()

        self.assert_conflict_lists(response, "owned_projects", "非空或非預設的專案")
        self.assertTrue(self.exists(Project, id=project_id))
        self.assertTrue(self.exists(User, id=self.target_id))

    def test_f_reject_and_delete_purges_the_empty_default_project(self):
        """
        @purpose 拒絕授權申請並刪除帳號的路徑與 DELETE 共用同一規則（規則 5）。
        @given 待審帳號 pending 有一筆 pending 申請，並擁有空預設專案
        @step 管理員 POST /api/auth/authorization-requests/{id}/reject | 回 200，
              deleted_username 為該帳號
        @step 查 users、projects | 帳號與其預設專案皆不存在
        @pass 回 200 且帳號與預設專案皆已刪除
        @api POST /api/auth/authorization-requests/{request_id}/reject -> 200 | 拒絕申請並刪除帳號
        @story US9.1
        @note 兩個呼叫點若各自實作，這一條會先漂移；故以同一夾具形狀驗第二個入口。
        """
        pending = make_user(
            self.db,
            username="pending",
            role=None,
            authorization_status="pending",
        )
        pending_id = pending.id
        req = RoleAuthorizationRequest(
            user_id=pending_id, requested_role=ROLE_TARGET, status="pending"
        )
        self.db.add(req)
        self.db.commit()
        project_id, _ = self.make_default_project(pending)

        response = self.client.post(
            f"/api/auth/authorization-requests/{req.id}/reject"
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deleted_username"], "pending")
        self.assertFalse(self.exists(User, id=pending_id))
        self.assertFalse(self.exists(Project, id=project_id))

    def test_g_uncovered_foreign_key_falls_back_to_409_not_500(self):
        """
        @purpose 預檢沒涵蓋的外鍵（之後新增的表）在 commit 被資料庫擋下時，
                 必須 rollback 並回 409，不得回 500。
        @given 一張預檢不認識、以外鍵指向 users 的表，有一列指向 target；
               target 另擁有空預設專案
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 為空清單
        @step 查 users、projects | target 與其預設專案仍在（清除已隨交易回滾）
        @pass 409 而非 500，且交易已回滾
        @api DELETE /api/auth/{user_id} -> 409 | 參照完整性保底
        @story US9.1
        @note 以真實外鍵而非 mock 注入 IntegrityError：SQLite 外鍵開啟時，刪除父列
              會在 commit 的 flush 拋出真正的 IntegrityError，與正式環境同形。
              突變 M-D3（拿掉保底）使本案回 500 → 紅燈。
        """
        project_id, _ = self.make_default_project(self.target)
        self.db.execute(
            text(
                "CREATE TABLE future_user_refs ("
                " id INTEGER PRIMARY KEY,"
                " user_id INTEGER NOT NULL REFERENCES users (id))"
            )
        )
        self.db.execute(
            text("INSERT INTO future_user_refs (user_id) VALUES (:uid)"),
            {"uid": self.target_id},
        )
        self.db.commit()

        response = self.delete_target()

        self.assertEqual(response.status_code, 409, response.text)
        body = response.json()
        self.assertEqual(set(body), CONFLICT_FIELDS)
        self.assertEqual(body["blocking_references"], [])
        self.assertTrue(self.exists(User, id=self.target_id))
        self.assertTrue(self.exists(Project, id=project_id))

    def test_h_default_project_with_another_member_is_not_purged(self):
        """
        @purpose 預設專案除本人外還有其他成員時，不得被當成「空」而隨使用者清掉——
                 否則他人的成員資格會經 ON DELETE CASCADE 一併消失。
        @given target 擁有預設專案（無架構圖），alice 是該專案的 member
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 含 owned_projects
        @step 查 projects、project_members | 該專案與 alice 的成員列仍在
        @pass 409 且專案、alice 的成員列、target 皆未被刪除
        @api DELETE /api/auth/{user_id} -> 409 | 仍擁有非空專案時拒絕刪除
        @story US9.1
        @note 審查 R-01（hierarchy-data code-generation review-02）補測。突變 M-D4
              （拿掉 other_member 條件）使本案回 200 → 紅燈。
        """
        project_id, _ = self.make_default_project(self.target)
        self.db.add(
            ProjectMember(project_id=project_id, user_id=self.alice.id, role="member")
        )
        self.db.commit()

        response = self.delete_target()

        self.assert_conflict_lists(response, "owned_projects", "非空或非預設的專案")
        self.assertTrue(self.exists(Project, id=project_id))
        self.assertTrue(
            self.exists(ProjectMember, project_id=project_id, user_id=self.alice.id)
        )
        self.assertTrue(self.exists(User, id=self.target_id))

    def test_i_default_project_holding_someone_elses_diagram_is_not_purged(self):
        """
        @purpose 預設專案下有架構圖時，不論圖的建立者是誰都不得被清掉；本案讓圖屬於
                 alice，使既有「target 仍擁有架構圖 → 403」守門不會先觸發，
                 直接驗證 has_diagram 這個條件本身。
        @given target 擁有預設專案；其預設系統下掛了一張 alice 的架構圖；target 本人無圖
        @step 管理員 DELETE /api/auth/{target} | 回 409，blocking_references 含 owned_projects
        @step 查 projects、user_diagrams | 專案與 alice 的圖仍在
        @pass 409 且專案、系統、圖、target 皆未被刪除
        @api DELETE /api/auth/{user_id} -> 409 | 仍擁有非空專案時拒絕刪除
        @story US9.1
        @note 審查 R-01 補測。test_b 的圖屬於 target，只走到既有 403，碰不到本條件。
              突變 M-D5（拿掉 has_diagram 條件）使本案回 200 或 500 → 紅燈。
        """
        project_id, system_id = self.make_default_project(self.target)
        diagram = make_diagram(self.db, owner=self.alice)
        diagram.system_id = system_id
        self.db.commit()
        diagram_id = diagram.id

        response = self.delete_target()

        self.assert_conflict_lists(response, "owned_projects", "非空或非預設的專案")
        self.assertTrue(self.exists(Project, id=project_id))
        self.assertTrue(self.exists(System, id=system_id))
        self.assertTrue(self.exists(UserDiagram, id=diagram_id))
        self.assertTrue(self.exists(User, id=self.target_id))


if __name__ == "__main__":
    unittest.main()
