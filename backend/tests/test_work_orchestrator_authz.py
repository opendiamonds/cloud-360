"""`U12 work-orchestrator` Step 8：經**真實 app** 的授權 allow／deny 雙向（`NFR12.7`；`team.md` 規則 A）。

`WorkOrchestrator` 以 `httpx.ASGITransport(app=main.app)` 呼叫既有端點，請求完整
走過 `get_current_user` → `require_arch_action`／`require_story_action`；資料庫為
`tests/helpers.py` 的 in-memory SQLite（覆寫 `get_db`）。**不 mock `user_can`、不
覆寫 `get_current_user`**——授權判定是真的。

唯一被替換的是 A1 端點**之後**的 LLM 呼叫（`agent_router.run_design_agent` 與
`_ensure_llm_keys`）：它們在授權 dependency 之後才執行，與本測試要驗的授權無關，
而真的呼叫 LLM 會讓測試依賴外部服務。

| 案例 | 角色 | 預期 |
|---|---|---|
| A1 allow | `Project_Architect`（A1 edit） | 進入 `request_sent`，完成並寫一列變更紀錄（actor 為本人） |
| A1 deny | `FinOps_Analyst`（A1 view、無 edit） | 失敗，原因為 `BR51.3` 的固定句型 |
| token 過期 | `Project_Architect` | 失敗，原因為 `BR51.6` 的固定句型 |
| C1 allow | `FinOps_Analyst`（C1 view） | 通過授權（因無估價表而以「尚無估價表」失敗，不是權限句型） |
| C1 deny | `Developer`（無 C1） | 失敗，原因為 `BR51.3` 的固定句型 |
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import unittest
from datetime import timedelta
from unittest import mock

from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models import DiagramChangeRecord
from services.auth import create_access_token
from services.hierarchy_facade import mint_principal
from services.work_orchestrator import WorkOrchestrator
from tests.helpers import close_session, make_diagram, make_session, make_user
from tests.test_work_orchestrator_flow import ARCH, COST, decision, session
from tests.work_orchestrator_fakes import (
    SESSION_KEY,
    FacadeRecorder,
    FakeClock,
    RecordingSink,
    drain,
    make_store,
)

FORBIDDEN_A1 = "你沒有使用架構設計的權限，或帳號已被停用"
FORBIDDEN_C1 = "你沒有使用成本分析的權限，或帳號已被停用"
EXPIRED = "登入已過期，請重新登入後再說一次"


async def _fake_design_agent(payload, current_xml, **_kwargs):
    yield {"type": "message", "content": "已調整"}
    yield {"type": "xml", "content": "<mxGraphModel><root><mxCell id=\"0\"/></root></mxGraphModel>"}


class RealAppAuthorizationTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.SessionLocal = sessionmaker(bind=self.db._test_engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.architect = make_user(self.db, username="alice", role="Project_Architect")
        self.finops = make_user(self.db, username="fin", role="FinOps_Analyst")
        self.developer = make_user(self.db, username="dev", role="Developer")
        self.patches = [
            mock.patch("services.agent_router._ensure_llm_keys", lambda: None),
            mock.patch("services.agent_router.run_design_agent", _fake_design_agent),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        app.dependency_overrides.clear()
        close_session(self.db)

    def _run(self, user, capability, *, diagram_id, token=None):
        store, _ = make_store()
        clock = FakeClock()
        recorder = FacadeRecorder()  # 只替換記憶寫入（嵌入 Port 與本案無關）
        sink = RecordingSink()
        orchestrator = WorkOrchestrator(
            app, store, clock=clock, sleep=clock.sleep,
            session_factory=self.SessionLocal,
            memory_facade_factory=recorder.memory_factory,
        )
        token = token or create_access_token({"sub": user.username})

        async def scenario():
            made = await orchestrator.dispatch(
                mint_principal(user), session(diagram_id=diagram_id), decision(capability),
                utterance="加上快取層", segment_id="shared", turn_id="t",
                bearer_token=token, sink=sink,
            )
            await drain(orchestrator)
            return store.load_work_items(SESSION_KEY)[made[0].workItemId]

        return asyncio.run(scenario())

    def test_a1_allowed_role_reaches_request_sent_and_completes(self):
        diagram = make_diagram(self.db, owner=self.architect, title="訂單")
        item = self._run(self.architect, ARCH, diagram_id=diagram.id)
        self.assertEqual((item["status"], item["dispatchStage"]), ("完成", "result_persisted"))
        records = self.db.query(DiagramChangeRecord).all()
        self.assertEqual([(r.diagram_id, r.actor_user_id) for r in records],
                         [(diagram.id, self.architect.id)])

    def test_a1_denied_role_fails_with_the_permission_phrase(self):
        """被分享的圖讓讀圖（A1 view）通過，拒絕發生在 A1 產圖端點本身（A1 edit）。"""
        diagram = make_diagram(self.db, owner=self.architect, title="訂單")
        diagram.shared_users.append(self.finops)
        self.db.commit()
        item = self._run(self.finops, ARCH, diagram_id=diagram.id)
        self.assertEqual((item["status"], item["failureReason"]), ("失敗", FORBIDDEN_A1))
        self.assertEqual(item["dispatchStage"], "request_sent")
        self.assertEqual(item["sideEffect"], "unknown")
        self.assertEqual(self.db.query(DiagramChangeRecord).count(), 0)

    def test_expired_token_fails_with_the_relogin_phrase(self):
        diagram = make_diagram(self.db, owner=self.architect, title="訂單")
        expired = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=-1))
        item = self._run(self.architect, ARCH, diagram_id=diagram.id, token=expired)
        self.assertEqual((item["status"], item["failureReason"]), ("失敗", EXPIRED))

    def test_c1_allowed_role_passes_authorization(self):
        diagram = make_diagram(self.db, owner=self.finops)
        item = self._run(self.finops, COST, diagram_id=diagram.id)
        self.assertEqual(item["status"], "失敗")
        self.assertEqual(item["failureReason"], "這張圖尚無估價表，可到成本頁上傳（/cost）")

    def test_c1_denied_role_fails_with_the_permission_phrase(self):
        diagram = make_diagram(self.db, owner=self.developer)
        item = self._run(self.developer, COST, diagram_id=diagram.id)
        self.assertEqual((item["status"], item["failureReason"]), ("失敗", FORBIDDEN_C1))


if __name__ == "__main__":
    unittest.main()
