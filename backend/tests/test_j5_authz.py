"""J5 unit tests: pending gate, catalog, approve/reject helpers."""

from __future__ import annotations

import unittest

from fastapi import HTTPException

from tests.helpers import close_session, make_session, make_user

from models import RoleAuthorizationRequest
from services.rbac import user_can, admin_may_decide_role, permissions_map_for_role
from services.user_router import _build_role_catalog, _hard_delete_user


class TestJ5PendingGate(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        close_session(self.db)

    def test_pending_user_can_is_false(self):
        self.assertFalse(
            user_can(
                self.db,
                "Developer",
                "A1",
                "edit",
                authorization_status="pending",
            )
        )

    def test_approved_developer_can_arch_edit(self):
        self.assertTrue(
            user_can(
                self.db,
                "Developer",
                "A1",
                "edit",
                authorization_status="approved",
            )
        )

    def test_permissions_map_empty_when_pending(self):
        perms = permissions_map_for_role(
            self.db, "Developer", authorization_status="pending"
        )
        self.assertEqual(perms, {})

    def test_null_role_cannot(self):
        self.assertFalse(user_can(self.db, None, "A1", "view"))


class TestJ5AdminDecide(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.plat = make_user(self.db, username="jack", role="Platform_Admin")
        self.padm = make_user(self.db, username="catherine", role="Project_Admin")

    def tearDown(self):
        close_session(self.db)

    def test_platform_admin_may_approve_owner(self):
        self.assertTrue(admin_may_decide_role(self.plat, "Platform_Owner", self.db))

    def test_project_admin_cannot_approve_owner(self):
        self.assertFalse(admin_may_decide_role(self.padm, "Platform_Owner", self.db))

    def test_project_admin_may_approve_sre(self):
        self.assertTrue(admin_may_decide_role(self.padm, "SRE", self.db))


class TestJ5CatalogAndDelete(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        close_session(self.db)

    def test_catalog_has_canonical_roles(self):
        catalog = _build_role_catalog(self.db)
        roles = {c["role"] for c in catalog}
        self.assertIn("Developer", roles)
        self.assertIn("Platform_Admin", roles)
        self.assertTrue(any(c["features"] for c in catalog))
        # 功能摘要應為中文，不可直接露出 story 編號如 A3／B1
        for entry in catalog:
            for feat in entry["features"]:
                self.assertFalse(
                    feat.startswith(("A", "B", "C", "D", "E", "F", "G", "H", "J"))
                    and len(feat) <= 3,
                    msg=f"feature 仍為 story id：{feat}",
                )
                self.assertNotRegex(feat, r"^[A-HJ]\d")
        # Developer 應含「架構圖生成」中文名
        dev = next(c for c in catalog if c["role"] == "Developer")
        self.assertIn("架構圖生成", dev["features"])

    def test_hard_delete_pending_user(self):
        user = make_user(
            self.db,
            username="newbie",
            role=None,
            authorization_status="pending",
        )
        self.db.add(
            RoleAuthorizationRequest(
                user_id=user.id,
                requested_role="SRE",
                status="pending",
            )
        )
        self.db.commit()
        uid = user.id
        _hard_delete_user(self.db, user)
        from models import User

        self.assertIsNone(self.db.query(User).filter(User.id == uid).first())


if __name__ == "__main__":
    unittest.main()
