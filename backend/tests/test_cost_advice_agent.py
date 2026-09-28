"""
@purpose Cost advice orchestrator / SSE (U7)
@api GET /api/cost/v1/sets/{set_id}/advice/stream
"""

from __future__ import annotations

import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from starlette.testclient import TestClient

from cost import advice_orchestrator as orch
from database import get_db
from main import app
from models import Advice, EstimateSet
from services.auth import get_current_user
from services.rbac import ensure_role_permissions_seeded
from tests.helpers import close_session, make_session, make_user


class CostAdviceAgentTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        self.owner = make_user(self.db, username="adv_owner", role="FinOps_Analyst")
        self.denied = make_user(self.db, username="adv_dev", role="Developer")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = TestClient(app)
        # Avoid real thread pool racing tests
        orch._run_agent = lambda payload: {
            "saving_text": "省下一成預留容量",
            "comparison_text": None,
            "quality_text": None,
            "unavailable_reasons": {"comparison": "insufficient_clouds"},
        }
        # Reuse the in-memory test session (do not open real Postgres).
        orch._session_factory = lambda: self.db

    def tearDown(self):
        orch._run_agent = None
        orch._session_factory = None
        orch._inflight.clear()
        app.dependency_overrides.clear()
        close_session(self.db)

    def _set(self) -> EstimateSet:
        row = EstimateSet(owner_user_id=self.owner.id, note="t")
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def test_enqueue_runs_agent_to_completed(self):
        s = self._set()
        with patch.object(orch, "_get_executor") as ex:
            # run job synchronously
            class _Immed:
                def submit(self, fn, *a, **k):
                    fn(*a, **k)

                    class F:
                        pass

                    return F()

            ex.return_value = _Immed()
            orch.enqueue_advice_job(s.id)
        row = self.db.query(Advice).filter(Advice.estimate_set_id == s.id).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.status, "completed")
        self.assertIn("省下", row.saving_text)

    def test_enqueue_after_ensure_shell_still_submits(self):
        """Intake creates generating shell before enqueue — must still run the job."""
        s = self._set()
        self.db.add(
            Advice(
                estimate_set_id=s.id,
                status="generating",
                started_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        submitted = []

        class _Immed:
            def submit(self, fn, *a, **k):
                submitted.append(1)
                fn(*a, **k)

        with patch.object(orch, "_get_executor", return_value=_Immed()):
            orch.enqueue_advice_job(s.id)
        self.assertEqual(submitted, [1])
        row = self.db.query(Advice).filter(Advice.estimate_set_id == s.id).first()
        self.assertEqual(row.status, "completed")

    def test_enqueue_dedupes_inflight(self):
        s = self._set()
        self.db.add(
            Advice(
                estimate_set_id=s.id,
                status="generating",
                started_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        orch._inflight.add(s.id)
        submitted = []

        class _Ex:
            def submit(self, fn, *a, **k):
                submitted.append(1)

        with patch.object(orch, "_get_executor", return_value=_Ex()):
            orch.enqueue_advice_job(s.id)
        self.assertEqual(submitted, [])

    def test_reclaim_stale_generating(self):
        s = self._set()
        self.db.add(
            Advice(
                estimate_set_id=s.id,
                status="generating",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=6),
            )
        )
        self.db.commit()
        n = orch.reclaim_stale_generating(self.db, s.id)
        self.assertEqual(n, 1)
        row = self.db.query(Advice).filter(Advice.estimate_set_id == s.id).first()
        self.assertEqual(row.status, "failed")
        reasons = json.loads(row.unavailable_reasons_json)
        self.assertTrue(reasons.get("timed_out"))

    def test_stream_requires_visibility(self):
        s = self._set()
        app.dependency_overrides[get_current_user] = lambda: self.denied
        r = self.client.get(f"/api/cost/v1/sets/{s.id}/advice/stream")
        self.assertEqual(r.status_code, 403)

    def test_agent_fallback_omits_secret(self):
        from cost.cost_advice_agent import generate_advice

        secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        with patch(
            "cost.cost_advice_agent._invoke_once",
            side_effect=RuntimeError(f"boom {secret}"),
        ):
            out = generate_advice({"estimate_set_id": 1, "clouds": [{"cloud": "aws", "lines": []}]})
        blob = json.dumps(out, ensure_ascii=False)
        self.assertNotIn(secret, blob)
        self.assertTrue(out["saving_text"])

    def test_strip_markdown_plain_layout(self):
        from cost.cost_advice_agent import strip_markdown

        raw = "## 標題\n\n**粗體**建議\n- 第一點\n- 第二點\n\n`code` 與 [連結](https://x)"
        plain = strip_markdown(raw)
        self.assertNotIn("**", plain)
        self.assertNotIn("##", plain)
        self.assertNotIn("`", plain)
        self.assertNotIn("](", plain)
        self.assertIn("・第一點", plain)
        self.assertIn("粗體建議", plain)


if __name__ == "__main__":
    unittest.main()
