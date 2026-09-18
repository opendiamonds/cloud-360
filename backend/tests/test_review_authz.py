"""A3 review authz / ACL unit tests."""

from __future__ import annotations

import unittest

from tests.helpers import close_session, make_diagram, make_session, make_user
from models import ArchitectureReview
from services.rbac import user_can
from services.review_orchestrator import get_accessible_diagram, review_to_dict


class TestReviewAuthz(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()

    def tearDown(self) -> None:
        close_session(self.db)

    def test_finops_no_a3_edit(self):
        # FinOps_Analyst has A3 all false in seed
        self.assertFalse(
            user_can(
                self.db,
                "FinOps_Analyst",
                "A3",
                "edit",
                authorization_status="approved",
            )
        )
        self.assertFalse(
            user_can(
                self.db,
                "FinOps_Analyst",
                "A3",
                "view",
                authorization_status="approved",
            )
        )

    def test_architect_has_a3_edit(self):
        self.assertTrue(
            user_can(
                self.db,
                "Project_Architect",
                "A3",
                "edit",
                authorization_status="approved",
            )
        )

    def test_pending_user_cannot(self):
        self.assertFalse(
            user_can(
                self.db,
                "Project_Architect",
                "A3",
                "edit",
                authorization_status="pending",
            )
        )

    def test_diagram_acl_owner_ok_stranger_denied(self):
        owner = make_user(self.db, username="owner1", role="Project_Architect")
        other = make_user(self.db, username="other1", role="Security_Reviewer")
        diagram = make_diagram(self.db, owner=owner, xml_data="<mxGraphModel/>")
        self.assertIsNotNone(get_accessible_diagram(self.db, owner, diagram.id))
        self.assertIsNone(get_accessible_diagram(self.db, other, diagram.id))

    def test_review_to_dict_roundtrip_fields(self):
        owner = make_user(self.db, username="owner2", role="Project_Editor")
        diagram = make_diagram(self.db, owner=owner)
        row = ArchitectureReview(
            diagram_id=diagram.id,
            created_by=owner.id,
            provider="aws",
            status="complete",
            overall_score=88,
            scores_json='{"overall_score": 88}',
            findings_json="[]",
            archived=False,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        d = review_to_dict(row)
        self.assertEqual(d["status"], "complete")
        self.assertEqual(d["overall_score"], 88)
        self.assertEqual(d["diagram_id"], diagram.id)


if __name__ == "__main__":
    unittest.main()
