"""`Security_Reviewer` 取得 J3a 檢視權限的 allow/deny 雙向測試（PU-4）。

team-practices 測試底線 A：任何 `role_permissions` 預設值變更，必須有測試同時
驗證「該角色能做到」與「其他角色做不到」。單向測試會漏掉「把整欄都翻成 true」
這種錯誤。

**已知的涵蓋邊界（如實記載）**：本檔驗的是**種子預設值**，不涵蓋既有環境的
目標式套用（`_apply_security_reviewer_j3a_view`）—— 測試以強制模式直接建矩陣、
從不呼叫啟動流程，把那支函式整個刪掉本檔照樣通過。既有環境的套用以啟動日誌的
三態記錄 ＋ 部署後人工核對承接（見 `DEPLOY.md` 2.2.5）。
"""

import unittest

from tests.helpers import close_session, make_session
from services.rbac import CANONICAL_ROLES, ensure_role_permissions_seeded, user_can


class SecurityReviewerJ3aViewTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)

    def tearDown(self):
        close_session(self.db)

    # --- allow ---

    def test_security_reviewer_can_view_j3a(self):
        self.assertTrue(user_can(self.db, "Security_Reviewer", "J3a", "view"))

    # --- deny：邊界沒有被一起翻開 ---

    def test_security_reviewer_cannot_edit_j3a(self):
        """只開 view，不開 edit —— 稽核者是讀者，不是使用者管理者。"""
        self.assertFalse(user_can(self.db, "Security_Reviewer", "J3a", "edit"))

    def test_security_reviewer_cannot_review_j3a(self):
        self.assertFalse(user_can(self.db, "Security_Reviewer", "J3a", "review"))

    def test_security_reviewer_still_cannot_view_j3b(self):
        """J3b（細項權限設定）不在本次開通範圍。"""
        self.assertFalse(user_can(self.db, "Security_Reviewer", "J3b", "view"))

    def test_roles_without_the_grant_still_cannot_view_j3a(self):
        """其他角色的 J3a 檢視權限**不得**被本次變更波及。

        這是 deny 側最重要的一條：把整欄翻成 true 也能讓上面的 allow 通過。
        """
        expected_viewers = {
            role
            for role in CANONICAL_ROLES
            if user_can(self.db, role, "J3a", "view")
        }
        # 開通後應為既有的管理類角色 ＋ Security_Reviewer，且 Developer 這類
        # 一般角色仍不得檢視。
        self.assertIn("Security_Reviewer", expected_viewers)
        for role in ("Developer", "Project_Editor", "FinOps_Analyst"):
            with self.subTest(role=role):
                self.assertNotIn(role, expected_viewers)

    def test_pending_security_reviewer_cannot_view(self):
        """J5：未核准的帳號不得擁有業務權限，開通不繞過這道檢查。"""
        self.assertFalse(
            user_can(
                self.db,
                "Security_Reviewer",
                "J3a",
                "view",
                authorization_status="pending",
            )
        )



class J3aStartupPatchTest(unittest.TestCase):
    """啟動補丁 `_apply_security_reviewer_j3a_view` 的四態契約（U4 的 R4）。

    這支測試填補的正是先前**明文記載為「無自動化驗證」**的缺口 —— 既有環境的
    套用路徑。它不涵蓋真實的啟動流程（那仍需部署後人工核對日誌），但涵蓋了補丁
    函式本身的四個分支，其中「已被管理員異動」那一態是 R2 的死角。
    """

    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)

    def tearDown(self):
        close_session(self.db)

    def _row(self):
        from models import RolePermission

        return (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role == "Security_Reviewer",
                RolePermission.story_id == "J3a",
            )
            .first()
        )

    def test_applies_when_row_is_still_seed_written(self):
        from database import J3A_PATCH_MARKER, _apply_security_reviewer_j3a_view

        row = self._row()
        row.can_view = False
        row.updated_by = "system_seed"
        self.db.commit()

        _apply_security_reviewer_j3a_view(self.db)

        refreshed = self._row()
        self.assertTrue(refreshed.can_view)
        # 寫入補丁識別字，讓第二次啟動落在「已跳過」而非被誤判為管理員異動。
        self.assertEqual(refreshed.updated_by, J3A_PATCH_MARKER)

    def test_applies_when_row_came_from_the_sql_seed(self):
        """`schema_rbac.sql` 的 INSERT 不含 updated_by，故該欄為 NULL。

        真實 staging 的資料庫正是這個形狀 —— 若把 NULL 誤判為「人工調整」，
        套用會在最需要它的環境靜默失敗。
        """
        from database import _apply_security_reviewer_j3a_view

        row = self._row()
        row.can_view = False
        row.updated_by = None
        self.db.commit()

        _apply_security_reviewer_j3a_view(self.db)
        self.assertTrue(self._row().can_view)

    def test_does_not_overwrite_an_admin_adjustment(self):
        """R2 的死角：管理者刻意撤銷過，補丁不得覆寫。"""
        from database import _apply_security_reviewer_j3a_view

        row = self._row()
        row.can_view = False
        row.updated_by = "some_admin"
        self.db.commit()

        with self.assertLogs("cloud360.database", level="WARNING") as captured:
            _apply_security_reviewer_j3a_view(self.db)

        self.assertFalse(self._row().can_view)
        # 該態必須是 WARNING（與「未命中目標列」同級、需人工處置），不是常態跳過。
        self.assertTrue(
            any("已被管理員異動" in line for line in captured.output),
            captured.output,
        )

    def test_warns_when_target_row_is_missing_and_does_not_insert(self):
        from models import RolePermission
        from database import _apply_security_reviewer_j3a_view

        before = self.db.query(RolePermission).count()
        self.db.delete(self._row())
        self.db.commit()

        with self.assertLogs("cloud360.database", level="WARNING") as captured:
            _apply_security_reviewer_j3a_view(self.db)

        # **只更新不插入** —— 插入會在空表情境下建立孤兒列，使後續的 seed 整份
        # 跳過、308 列預設矩陣不被建立，而沒有任何測試會發現。
        self.assertEqual(self.db.query(RolePermission).count(), before - 1)
        self.assertTrue(
            any("未命中目標列" in line for line in captured.output), captured.output
        )

if __name__ == "__main__":
    unittest.main()
