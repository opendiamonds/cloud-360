import unittest

from tests.helpers import close_session, make_session

from services.rbac import (
    normalize_role,
    is_canonical_role,
    user_can,
    user_can_arch,
    sync_arch_permission_flags,
    permissions_map_for_role,
)


class TestRBAC(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        close_session(self.db)

    def test_normalize_role(self):
        self.assertEqual(normalize_role("Security_Admin"), "Security_Reviewer")
        self.assertEqual(normalize_role("Engineering_Manager"), "Project_Editor")
        self.assertEqual(normalize_role("Developer"), "Developer")

    def test_is_canonical_role(self):
        self.assertTrue(is_canonical_role("Project_Architect"))
        self.assertTrue(is_canonical_role("Security_Admin"))
        self.assertFalse(is_canonical_role("Non_Existent_Role"))

    def test_sync_arch_permission_flags(self):
        self.assertEqual(sync_arch_permission_flags(False, True, False), (True, True, False))
        self.assertEqual(sync_arch_permission_flags(False, False, True), (True, False, True))
        self.assertEqual(sync_arch_permission_flags(True, False, False), (True, False, False))

    def test_user_can(self):
        # 預設 seed 中，Project_Architect 應該可以編輯 A1 (架構圖生成)
        self.assertTrue(user_can(self.db, "Project_Architect", "A1", "edit"))
        self.assertTrue(user_can(self.db, "Project_Architect", "A1", "view"))
        
        # Developer 預設對 J3 (管理員面板) 沒有編輯權限
        self.assertFalse(user_can(self.db, "Developer", "J3", "edit"))

    def test_user_can_arch(self):
        self.assertTrue(user_can_arch(self.db, "Project_Architect", "edit"))
        self.assertTrue(user_can_arch(self.db, "Project_Architect", "view"))

    def test_permissions_map_for_role(self):
        perms = permissions_map_for_role(self.db, "Project_Architect")
        self.assertIn("A1", perms)
        self.assertEqual(perms["A2"], perms["A1"])
        self.assertEqual(perms["A4"], perms["A1"])

if __name__ == "__main__":
    unittest.main()
