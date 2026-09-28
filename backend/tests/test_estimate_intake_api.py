"""
@purpose Estimate intake API (/api/cost/v1) — upload, ACL, RBAC, enqueue
@api POST /api/cost/v1/sets
@api GET /api/cost/v1/sets
@api GET /api/cost/v1/sets/{set_id}
@api DELETE /api/cost/v1/sets/{set_id}
@api GET /api/cost/v1/sets/{set_id}/advice
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from cost.estimate_parser import ParseResult
from database import get_db
from main import app
from models import Advice, EstimateAuditEvent, EstimateSet
from services.auth import get_current_user
from services.rbac import STORY_IDS, ensure_role_permissions_seeded, user_can
from tests.helpers import close_session, make_session, make_user

SETS_URL = "/api/cost/v1/sets"

DETAIL_FIELDS = {
    "id",
    "created_at",
    "note",
    "diagram_id",
    "is_owner",
    "is_saved",
    "privacy",
    "clouds",
    "advice_status",
    "estimates",
}


def _sample_parse(cloud: str = "aws") -> ParseResult:
    return {
        "detection": {"status": "resolved", "cloud": cloud},  # type: ignore[typeddict-item]
        "lines": [
            {
                "ordinal": 1,
                "itemName": "EC2",
                "spec": "m5.large",
                "quantity": 1.0,
                "amount": 10.0,
                "currency": "USD",
                "parseStatus": "parsed",
                "rawText": "EC2,m5.large,1,10,USD",
            }
        ],
        "totals": {"statedTotal": 10.0, "currency": "USD"},
        "sourceFormat": "csv",
    }


def _ambiguous_parse() -> ParseResult:
    return {
        "detection": {
            "status": "ambiguous",
            "reason": "tie",
            "candidates": ["aws", "gcp"],
        },
        "lines": [],
        "totals": {"statedTotal": None, "currency": None},
        "sourceFormat": "csv",
    }


class EstimateIntakeApiTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        self.owner = make_user(
            self.db, username="finops", role="FinOps_Analyst"
        )
        self.denied = make_user(
            self.db, username="dev", role="Developer"
        )
        self.viewer = make_user(
            self.db, username="sre", role="SRE"
        )  # C1 view, no edit
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = TestClient(app)
        # U7 enqueue opens its own session; keep intake tests isolated.
        self._enqueue_patcher = patch(
            "cost.estimate_intake_service.enqueue_advice_job"
        )
        self._enqueue_mock = self._enqueue_patcher.start()

    def tearDown(self):
        self._enqueue_patcher.stop()
        app.dependency_overrides.clear()
        close_session(self.db)

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def _upload(
        self,
        *,
        content: bytes = b"Description,Quantity,Cost\nEC2,1,10\n",
        filename: str = "est.csv",
        cloud_overrides: str | None = None,
        diagram_id: int | None = None,
        parse_result: ParseResult | None = None,
    ):
        files = [("files", (filename, io.BytesIO(content), "text/csv"))]
        data = {}
        if cloud_overrides is not None:
            data["cloud_overrides"] = cloud_overrides
        if diagram_id is not None:
            data["diagram_id"] = str(diagram_id)
        pr = parse_result if parse_result is not None else _sample_parse()

        def _fake_parse(file_bytes, filename=None, *, forced_cloud=None):
            if forced_cloud is not None and pr["detection"].get("status") == "ambiguous":
                return _sample_parse(cloud=forced_cloud)
            return pr

        with patch(
            "cost.estimate_intake_service.parse", side_effect=_fake_parse
        ):
            return self.client.post(SETS_URL, files=files, data=data)

    def test_upload_with_c1_edit_returns_201_detail(self):
        res = self._upload()
        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertEqual(set(body.keys()), DETAIL_FIELDS)
        self.assertEqual(len(body["estimates"]), 1)
        est = body["estimates"][0]
        self.assertIn("checks", est)
        self.assertIn("lines", est)
        self.assertEqual(est["cloud"], "aws")
        self.assertTrue(body["is_owner"])
        self.assertFalse(body["is_saved"])

    def test_save_puts_set_into_history(self):
        created = self._upload()
        self.assertEqual(created.status_code, 201)
        set_id = created.json()["id"]
        listed = self.client.get(f"{SETS_URL}?include_history=true")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["total"], 0)

        saved = self.client.patch(
            f"{SETS_URL}/{set_id}",
            json={"name": "電商估價"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertTrue(saved.json()["is_saved"])
        self.assertEqual(saved.json()["note"], "電商估價")

        listed2 = self.client.get(f"{SETS_URL}?include_history=true")
        self.assertEqual(listed2.status_code, 200)
        self.assertEqual(listed2.json()["total"], 1)
        self.assertEqual(listed2.json()["items"][0]["note"], "電商估價")

    def test_share_users_lists_other_accounts(self):
        res = self.client.get("/api/cost/v1/share-users")
        self.assertEqual(res.status_code, 200, res.text)
        rows = res.json()
        self.assertIsInstance(rows, list)
        ids = {r["id"] for r in rows}
        self.assertNotIn(self.owner.id, ids)
        self.assertIn(self.denied.id, ids)

    def test_upload_without_c1_returns_403(self):
        self._as(self.denied)
        res = self._upload()
        self.assertEqual(res.status_code, 403)

    def test_file_too_large_returns_413(self):
        big = b"a" * (5 * 1024 * 1024 + 1)
        res = self._upload(content=big, filename="big.csv")
        self.assertEqual(res.status_code, 413)
        self.assertEqual(res.json()["detail"], "file too large")
        self.assertEqual(self.db.query(EstimateSet).count(), 0)

    def test_bad_extension_returns_400(self):
        res = self._upload(content=b"hello", filename="est.txt")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"], "invalid file type")
        self.assertEqual(self.db.query(EstimateSet).count(), 0)

    def test_ambiguous_without_override_returns_400(self):
        res = self._upload(parse_result=_ambiguous_parse())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()["detail"], "cloud ambiguous; provide cloud_overrides"
        )

    def test_ambiguous_with_override_succeeds(self):
        res = self._upload(
            parse_result=_ambiguous_parse(),
            cloud_overrides=json.dumps(["gcp"]),
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["estimates"][0]["cloud"], "gcp")

    def test_non_owner_non_share_get_returns_404(self):
        created = self._upload()
        self.assertEqual(created.status_code, 201)
        set_id = created.json()["id"]
        other = make_user(self.db, username="other", role="FinOps_Analyst")
        self._as(other)
        res = self.client.get(f"{SETS_URL}/{set_id}")
        self.assertEqual(res.status_code, 404)

    def test_owner_delete_then_get_404(self):
        created = self._upload()
        set_id = created.json()["id"]
        del_res = self.client.delete(f"{SETS_URL}/{set_id}")
        self.assertEqual(del_res.status_code, 204)
        get_res = self.client.get(f"{SETS_URL}/{set_id}")
        self.assertEqual(get_res.status_code, 404)

    def test_enqueue_failure_still_201_with_failed_advice(self):
        def _boom(_set_id):
            raise RuntimeError("queue down")

        with patch(
            "cost.estimate_intake_service.enqueue_advice_job", side_effect=_boom
        ):
            res = self._upload()
        self.assertEqual(res.status_code, 201, res.text)
        set_id = res.json()["id"]
        # BackgroundTasks run before TestClient returns when using default
        advice = (
            self.db.query(Advice)
            .filter(Advice.estimate_set_id == set_id)
            .first()
        )
        self.assertIsNotNone(advice)
        self.assertEqual(advice.status, "failed")
        events = (
            self.db.query(EstimateAuditEvent)
            .filter(
                EstimateAuditEvent.estimate_set_id == set_id,
                EstimateAuditEvent.event_type == "advice_enqueue_failed",
            )
            .all()
        )
        self.assertTrue(len(events) >= 1)

    def test_seed_has_no_legacy_c1_stories_and_allow_deny(self):
        for sid in ("C1h", "C1r", "C1o", "C1b"):
            self.assertNotIn(sid, STORY_IDS)
        self.assertIn("C1", STORY_IDS)
        self.assertTrue(
            user_can(self.db, "FinOps_Analyst", "C1", "edit")
        )
        self.assertFalse(user_can(self.db, "Developer", "C1", "view"))
        self.assertTrue(user_can(self.db, "SRE", "C1", "view"))
        self.assertFalse(user_can(self.db, "SRE", "C1", "edit"))

    def test_view_only_role_cannot_upload(self):
        self._as(self.viewer)
        res = self._upload()
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
