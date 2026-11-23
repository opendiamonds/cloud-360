"""261116-brain-create-diagram U2 brain-create-flow：路由、能力呼叫與閘道新建流程。

追溯：FR1.1～FR1.5、FR2.2、FR3.1～FR3.6、FR4.1、FR6.2、FR6.3、FR6.3a、FR6.4a、FR7.1、
NFR2（路由只發一次）、NFR3（冪等三案）、NFR5（權限雙向）；契約 C4、C5、C6、C7。

替身：模型（Decisions HTTP）以 `httpx.MockTransport`；閘道的 Redis 走 `WorkItemFakeRedis`、
工作編排走 `FakeOrchestrator`；**作業對象與圖的查詢走真的 `HierarchyFacade` 與 SQLite**，
建草稿以 `FakeDiagramClient` 直接寫 SQLite（與 `POST /api/collab/diagrams` 的 `as_draft`
同形——端點本身由 `test_diagram_drafts_api.py` 與本檔的 `CapabilityClientTest` 覆蓋）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import dataclasses
import json
import unittest

import httpx
from starlette.testclient import TestClient

from database import get_db
from main import app as main_app
from models import (
    DRAFT_REJECTED_DETAIL,
    DiagramChangeRecord,
    RolePermission,
    UserDiagram,
)
from services import brain_gateway as G
from services import work_orchestrator_rules as R
from services.auth import get_current_user
from services.hierarchy_facade import HierarchyFacade, mint_principal
from services.intent_routing_decisions import (
    Q_WANTS_NEW_DIAGRAM,
    build_questions,
    parse_answers,
    routing_from_answers,
)
from services.intent_routing_types import Intent, IntentDecision
from services.session_store import SessionStore
from services.redis_gateway import RedisGateway
from services.work_orchestrator_capabilities import CapabilityClient, CapabilityError
from tests.brain_gateway_fakes import (
    WS_PATH,
    FakeOrchestrator,
    Harness,
    hello,
    low_confidence,
    protocols,
    read_turn,
    recv_json,
    types_of,
    user_message,
)
from tests.helpers import close_session, make_session, make_user
from tests.test_intent_routing_decisions import DRAW_SHOP, FakeHttp, classify
from tests.test_session_store_behaviour import FAKE_ERROR_TYPES, StubClock
from tests.test_work_orchestrator_flow import ARCH, Harness as OrchestratorHarness, run
from tests.work_orchestrator_fakes import drain

KEY = "brain:session:1"
DRAW = "幫我畫一張電商網站的 AWS 架構圖"


# ---------------------------------------------------------------------------
# Step 13：路由與能力呼叫
# ---------------------------------------------------------------------------


def _with_new_diagram(body: dict, p: float) -> dict:
    out = json.loads(json.dumps(body))
    out["answers"][Q_WANTS_NEW_DIAGRAM] = {"type": "noul", "noul": p, "confidence": abs(p - 0.5) * 2}
    return out


class RoutingTest(unittest.TestCase):
    def test_new_question_rides_on_the_single_routing_request(self):
        """
        @purpose FR2.2／NFR2：「是否要一張新的圖」併入既有的同一次路由請求，不多一次模型往返
        @given 假 Decisions HTTP 回實測形狀加上 wants_new_diagram=0.93
        @step classify 一句畫圖請求 | 恰送出 1 次請求，questions 含 wants_new_diagram
        @step 讀判定結果 | new_diagram_probability 為 0.93；不在 repr 中（不進 log）
        @pass 一次請求、p 原樣留在行程內
        @story FR2.2
        """
        http = FakeHttp(_with_new_diagram(DRAW_SHOP, 0.93))
        decision, _obs = classify(http, DRAW)
        self.assertEqual(1, len(http.requests))
        self.assertIn(Q_WANTS_NEW_DIAGRAM, http.sent()["questions"])
        self.assertEqual(0.93, decision.new_diagram_probability)
        self.assertNotIn("0.93", repr(decision))

    def test_missing_answer_is_none_and_bad_answer_is_malformed(self):
        """
        @purpose 回應缺這一題時 p=None（判定視為不明），出現但越界時與其他題一樣拒絕
        @given 不含／含越界 wants_new_diagram 的回應
        @step parse_answers 與 routing_from_answers | 缺題為 None；越界拋 MalformedRouting
        @pass 兩種情況分流正確
        @story FR2.2
        """
        from services.intent_routing_errors import MalformedRouting

        answers = parse_answers(DRAW_SHOP, ("t0", "t1", "t2"))
        self.assertIsNone(answers.new_diagram_probability)
        self.assertIsNone(routing_from_answers(answers, 0.7).new_diagram_probability)
        with self.assertRaises(MalformedRouting):
            parse_answers(_with_new_diagram(DRAW_SHOP, 1.5), ("t0", "t1", "t2"))
        self.assertIn(Q_WANTS_NEW_DIAGRAM, build_questions(()))


class PhrasesTest(unittest.TestCase):
    def test_draft_rejected_phrase_equals_the_endpoint_constant(self):
        """
        @purpose 契約 C4：工作項的失敗原因文字與端點的 409 detail 逐字相同（避免文字分歧）
        @given PHRASES 與 DRAFT_REJECTED_DETAIL
        @step 比較 | 相等
        @pass 相等；failure_for_status 只在 409＋draft_rejected 時用它
        @story FR6.4a
        """
        self.assertEqual(R.PHRASES["draft_rejected"], DRAFT_REJECTED_DETAIL)
        self.assertEqual(
            (DRAFT_REJECTED_DETAIL, "draft_rejected"),
            R.failure_for_status(ARCH, 409, draft_rejected=True),
        )
        self.assertEqual("capability_failed", R.failure_for_status(ARCH, 409)[1])


class CapabilityClientTest(unittest.TestCase):
    """經真的 app（ASGI 傳輸）：create_diagram、put_diagram(finalize)、409 辨識。"""

    def setUp(self):
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        main_app.dependency_overrides[get_db] = lambda: self.db
        main_app.dependency_overrides[get_current_user] = lambda: self.alice

    def tearDown(self):
        main_app.dependency_overrides.clear()
        close_session(self.db)

    def _system(self):
        principal = mint_principal(self.alice)
        facade = HierarchyFacade(self.db)
        project = facade.create_project(principal, name="P")
        return facade.create_system(principal, project_id=project.id, name="S",
                                    project_visible=lambda _p: True).id

    def test_create_draft_then_finalize_turns_it_ready(self):
        """
        @purpose 契約 C7：create_diagram 固定建草稿；put_diagram(finalize=True) 轉正式（FR6.2）
        @given alice 的系統
        @step create_diagram | 回新 id，資料庫為 draft、掛在該系統
        @step put_diagram(finalize=False) | 仍為 draft
        @step put_diagram(finalize=True) | 轉為 ready
        @pass 三步狀態皆符合
        @api POST /api/collab/diagrams -> 200 | 大腦建草稿
        @api PUT /api/collab/diagrams/{diagram_id} -> 200 | 產圖存回轉正式
        @story FR1.1、FR6.2
        """
        sid = self._system()

        async def scenario():
            async with CapabilityClient(main_app, "tok") as client:
                did = await client.create_diagram(title="T", xml_data=G.creation.BLANK_DIAGRAM_XML,
                                                  system_id=sid)
                statuses = [self._status(did)]
                await client.put_diagram(did, title="T", xml_data=G.creation.BLANK_DIAGRAM_XML)
                statuses.append(self._status(did))
                await client.put_diagram(did, title="T", xml_data=G.creation.BLANK_DIAGRAM_XML,
                                         finalize=True)
                statuses.append(self._status(did))
                return did, statuses

        did, statuses = asyncio.run(scenario())
        self.assertEqual(["draft", "draft", "ready"], statuses)
        self.db.expire_all()
        self.assertEqual(sid, self.db.get(UserDiagram, did).system_id)

    def _status(self, did):
        self.db.expire_all()
        return self.db.get(UserDiagram, did).status

    def test_draft_rejected_is_true_only_for_the_constant_409(self):
        """
        @purpose 契約 C4：只有 409 且 detail 等於常數時 draft_rejected 為真；回應內容不被保存
        @given 草稿與一支回其他 409 的假 app
        @step 對草稿 start_review | CapabilityError(409, draft_rejected=True)，訊息不含 detail 原文
        @step 對回「名稱重複」409 的 app 發請求 | draft_rejected=False
        @pass 兩者分流正確
        @api POST /api/architecture/reviews -> 409 | 草稿被拒
        @story FR6.4a
        """
        sid = self._system()

        async def scenario():
            async with CapabilityClient(main_app, "tok") as client:
                did = await client.create_diagram(title="T", xml_data=G.creation.BLANK_DIAGRAM_XML,
                                                  system_id=sid)
                with self.assertRaises(CapabilityError) as ctx:
                    await client.start_review(did)
                return ctx.exception

        exc = asyncio.run(scenario())
        self.assertEqual((exc.status_code, exc.draft_rejected), (409, True))
        self.assertNotIn(DRAFT_REJECTED_DETAIL, str(exc))

        async def other_conflict(scope, receive, send):
            await send({"type": "http.response.start", "status": 409,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"detail":"\xe5\x90\x8d\xe7\xa8\xb1\xe9\x87\x8d\xe8\xa4\x87"}'})

        async def scenario2():
            async with CapabilityClient(other_conflict, "tok") as client:
                with self.assertRaises(CapabilityError) as ctx:
                    await client.start_review(1)
                return ctx.exception

        self.assertFalse(asyncio.run(scenario2()).draft_rejected)

    def test_forbidden_is_classified_by_its_source(self):
        """
        @purpose 修訂 1（FR4.1）：建圖 403 有兩個來源；只有缺架構編輯權的 403 才 arch_forbidden=True，
                 K2 edit 被拒的 403 必須為 False，否則大腦會叫使用者去申請錯的角色。
        @given 端點本身（ASGI 傳輸）；alice 的系統
        @step alice 改為 FinOps_Analyst 後建圖 | 403、arch_forbidden=True、訊息不含 detail 原文
        @step alice 為 Project_Architect、但 K2 edit 被撤掉後建圖 | 403、arch_forbidden=False
        @pass 兩種 403 分流正確
        @api POST /api/collab/diagrams -> 403 | 缺架構編輯權或 K2 edit
        @story FR4.1
        """
        sid = self._system()

        async def create():
            async with CapabilityClient(main_app, "tok") as client:
                with self.assertRaises(CapabilityError) as ctx:
                    await client.create_diagram(title="T", xml_data=G.creation.BLANK_DIAGRAM_XML,
                                                system_id=sid)
                return ctx.exception

        self.alice.role = "FinOps_Analyst"
        self.db.commit()
        arch = asyncio.run(create())
        self.assertEqual((403, True), (arch.status_code, arch.arch_forbidden))
        self.assertNotIn("FinOps_Analyst", str(arch))

        self.alice.role = "Project_Architect"
        row = (self.db.query(RolePermission)
               .filter(RolePermission.role == "Project_Architect", RolePermission.story_id == "K2")
               .one())
        row.can_edit = False
        self.db.commit()
        k2 = asyncio.run(create())
        self.assertEqual((403, False), (k2.status_code, k2.arch_forbidden))


class OrchestratorFinalizeTest(unittest.TestCase):
    def test_successful_store_back_sends_finalize_and_never_creates(self):
        """
        @purpose FR6.2／ADR-008：工作編排產圖存回時送 finalize=true，且工作編排本身從不建圖
                 （重試與復原掃描只會處理同一張圖，NFR3 的兩案由結構保證）
        @given 作業對象為圖 #12 的架構設計工作項
        @step 交辦並跑完 | PUT 本體含 "finalize": true
        @step 再跑一次復原掃描（list_items） | 全程 POST /api/collab/diagrams 0 次
        @pass PUT 帶 finalize、沒有任何建圖請求
        @story FR6.2、NFR3
        """
        async def scenario():
            h = OrchestratorHarness()
            await h.dispatch(ARCH, diagram_id=12)
            await drain(h.orchestrator)
            await h.list_items()
            await drain(h.orchestrator)
            return h

        h = run(scenario())
        puts = [json.loads(b) for k, b in h.app.bodies if k.startswith("PUT /api/collab/diagrams/")]
        self.assertEqual(1, len(puts))
        self.assertIs(True, puts[0]["finalize"])
        self.assertEqual(0, h.app.count("POST /api/collab/diagrams"))

    def test_failed_generation_never_puts_so_the_draft_stays(self):
        """
        @purpose FR6.3：產圖失敗時沒有存回（圖維持草稿），工作項失敗並說明原因
        @given A1 回 error 事件
        @step 交辦並跑完 | 沒有任何 PUT；工作項為失敗「架構設計失敗」
        @pass PUT 0 次
        @story FR6.3
        """
        async def scenario():
            h = OrchestratorHarness()
            h.app.a1_events = [{"type": "error", "content": "x"}]
            made = await h.dispatch(ARCH, diagram_id=12)
            await drain(h.orchestrator)
            return h, h.store.load_work_items("brain:session:u-test").get(made[0].workItemId)

        h, item = run(scenario())
        self.assertEqual(0, h.app.count("PUT"))
        self.assertEqual(R.PHRASES["a1_failed"], (item or {}).get("failureReason"))


# ---------------------------------------------------------------------------
# Step 15：閘道新建流程
# ---------------------------------------------------------------------------


def draw(p):
    return IntentDecision(
        intents=(Intent("architecture-design", None),), confidence=0.95, below_threshold=False,
        new_diagram_probability=p,
    )


class FakeDiagramClient:
    """`CapabilityClient` 的建圖替身：與 `POST /api/collab/diagrams`（as_draft=true）同形，直接寫 SQLite。"""

    def __init__(self, harness, owner_id):
        self.h = harness
        self.owner_id = owner_id
        self.calls = []
        self.error = None
        # 修訂 1：hang_next=True 時下一次呼叫永遠不回（直到被取消）。
        self.hang_next = False
        self.hanging = False
        self.cancelled = False

    def __call__(self, token):
        self.token = token
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def create_diagram(self, *, title, xml_data, system_id):
        self.calls.append((title, system_id))
        if self.hang_next:
            self.hang_next = False
            self.hanging = True
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        if self.error is not None:
            raise self.error
        db = self.h.Session()
        try:
            row = UserDiagram(user_id=self.owner_id, title=title, xml_data=xml_data,
                              system_id=system_id, status="draft")
            db.add(row)
            db.commit()
            return row.id
        finally:
            db.close()


class _GatewayBase(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.alice = self.h.user("alice")
        self.token = self.h.token("alice")
        self.principal = mint_principal(self.alice)
        # 作業對象與圖的查詢改走真的 HierarchyFacade（SQLite）；可見性沿用替身（全部可見）。
        self.h.store = SessionStore(
            RedisGateway(self.h.redis, error_types=FAKE_ERROR_TYPES, clock=StubClock(),
                         sleep=StubClock().sleep, jitter=lambda: 0.0),
            hierarchy_facade=G._HierarchyResolver(
                self.h.Session, HierarchyFacade, membership_facade_factory=self.h.visibility.factory
            ),
            history_max=50,
        )
        self.h.orchestrator = FakeOrchestrator(self.h.store)
        self.client_factory = FakeDiagramClient(self.h, self.alice.id)
        self._rebuild()
        facade = HierarchyFacade(self.h.db)
        self.project = facade.create_project(self.principal, name="電商")
        self.system = facade.create_system(self.principal, project_id=self.project.id,
                                           name="前台", project_visible=lambda _p: True)

    def _rebuild(self):
        self.h.rebuild()
        self.h.gw.hierarchy_facade_factory = HierarchyFacade
        self.h.gw.diagram_client_factory = self.client_factory

    def tearDown(self):
        self.h.close()

    def target_system(self, system_id=None):
        self.h.store.set_work_target(KEY, "shared", self.principal, None,
                                     system_id or self.system.id, None)

    def target_diagram(self, diagram_id):
        self.h.store.set_work_target(KEY, "shared", self.principal, None, None, diagram_id)

    def segment(self):
        return self.h.store.load(KEY).segments["shared"]

    def diagrams(self):
        self.h.db.expire_all()
        return [(d.id, d.status) for d in self.h.db.query(UserDiagram).order_by(UserDiagram.id)]

    def add_diagram(self, title, status="ready", system_id=None):
        row = UserDiagram(user_id=self.alice.id, title=title, xml_data="<mxGraphModel/>",
                          system_id=system_id or self.system.id, status=status)
        self.h.db.add(row)
        self.h.db.commit()
        return row.id

    def say(self, ws, text=DRAW):
        user_message(ws, text)
        return read_turn(ws)

    def select(self, ws, candidate_id):
        ws.send_json({"v": 1, "type": "select_clarify_candidate",
                      "payload": {"candidateId": candidate_id}})
        return read_turn(ws)

    def connect(self, client):
        return client.websocket_connect(WS_PATH, subprotocols=protocols(self.token))


class CreateFlowTest(_GatewayBase):
    def test_system_without_diagrams_creates_one_draft_switches_and_dispatches(self):
        """
        @purpose FR1.1／FR1.3／FR1.5／FR7.1：只有系統沒有圖 → 建一張草稿、作業對象切到它、交辦、記變更紀錄
        @given alice 的系統「前台」，下面沒有圖；路由判定 p=0.9
        @step 說「幫我畫一張電商網站的 AWS 架構圖」 | 收到 work_target 後交辦並以 done 結束
        @step 檢查 | 系統下恰一張草稿、名稱由句子取出；作業對象為該圖；交辦恰一次；變更紀錄一筆
        @pass 全部符合
        @api WS /api/brain/ws -> 101
        @story FR1.5、FR7.1
        """
        self.h.router_script.default = draw(0.9)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            turn = self.say(ws)
        self.assertEqual("done", turn[-1]["type"])
        self.assertIn("work_target", types_of(turn))
        (did, status), = self.diagrams()
        self.assertEqual("draft", status)
        self.assertEqual([("電商網站的 AWS 架構圖", self.system.id)], self.client_factory.calls)
        self.assertEqual(did, self.segment().diagram_id)
        self.assertEqual(1, len(self.h.orchestrator.dispatch_calls))
        self.assertEqual(did, self.h.orchestrator.dispatch_calls[0].session.segments["shared"].diagram_id)
        self.h.db.expire_all()
        record = self.h.db.query(DiagramChangeRecord).one()
        self.assertEqual(("經大腦建立「電商網站的 AWS 架構圖」", "大腦建立架構圖"),
                         (record.requirement_summary, record.requirement_label))

    def test_saying_it_again_continues_the_same_draft(self):
        """
        @purpose NFR3／FR6.3：建圖後（產圖失敗）再說一次同一句 → 接著畫同一張草稿，不建第二張
        @given 上一輪已建草稿且作業對象為它；路由判定 p=0.95
        @step 再說一次 | 交辦第二次，對象仍是同一張；建圖呼叫仍只有 1 次
        @pass 系統下仍只有一張圖
        @api WS /api/brain/ws -> 101
        @story FR6.3、FR6.3b、NFR3
        """
        self.h.router_script.default = draw(0.95)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            self.say(ws)
            self.say(ws)
        self.assertEqual(1, len(self.client_factory.calls))
        self.assertEqual(1, len(self.diagrams()))
        targets = [c.session.segments["shared"].diagram_id for c in self.h.orchestrator.dispatch_calls]
        self.assertEqual(2, len(targets))
        self.assertEqual(targets[0], targets[1])

    def test_decision_is_logged_by_category_without_utterance_or_title(self):
        """
        @purpose NFR4：路由觀測要看得到「新建／修改／反問」的判定類別，但日誌不得含使用者
                 原文與圖名（team.md：logger 不寫使用者文字）。build-and-test 盤點時發現此
                 目標只有實作、沒有任何斷言，故補上。
        @given 作業對象為系統、路由判定 p=0.95
        @step 說「幫我畫一張電商網站的 AWS 架構圖」 | cloud360.brain_gateway 記一筆 diagram_decision
        @pass 該筆含 category=create，且所有 brain_gateway 日誌都不含原文、主題字與圖名
        @api WS /api/brain/ws -> 101
        @story NFR4
        """
        self.h.router_script.default = draw(0.95)
        self.target_system()
        with self.assertLogs("cloud360.brain_gateway", level="INFO") as logs:
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                self.say(ws)
        from services import brain_diagram_creation as creation

        decisions = [line for line in logs.output if "diagram_decision" in line]
        self.assertEqual(1, len(decisions))
        self.assertIn(f"category={creation.decision_category(creation.CREATE)}", decisions[0])
        self.h.db.expire_all()
        titles = [d.title for d in self.h.db.query(UserDiagram)]
        self.assertTrue(titles, "應已建立一張草稿")
        for line in logs.output:
            self.assertNotIn(DRAW, line)
            self.assertNotIn("電商網站", line)
            for title in titles:
                self.assertNotIn(title, line)

    def test_without_arch_edit_nothing_is_created(self):
        """
        @purpose NFR5 deny／FR4.1：有 K1 但沒有架構編輯權 → 不建、不交辦、回說明
        @given FinOps_Analyst（K1 有、A1 edit 無）擁有一個系統
        @step 說要畫圖 | token 為固定說明後 done
        @pass 建圖 0 次、交辦 0 次、資料庫沒有圖
        @api WS /api/brain/ws -> 101
        @story FR4.1、NFR5
        """
        self.alice.role = "FinOps_Analyst"
        self.h.db.commit()
        self.h.router_script.default = draw(0.9)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            turn = self.say(ws)
        self.assertEqual(["token", "done"], types_of(turn)[-2:])
        self.assertEqual(G.NEED_ARCH_EDIT_MESSAGE, turn[-2]["payload"]["text"])
        self.assertEqual([], self.client_factory.calls)
        self.assertEqual([], self.h.orchestrator.dispatch_calls)
        self.assertEqual([], self.diagrams())

    def test_create_timeout_is_not_retried_and_not_dispatched(self):
        """
        @purpose 契約 C5 錯誤表：建圖逾時（結果未知）→ 不重試、不交辦，回覆到工作區確認
        @given 建圖替身拋傳輸類 CapabilityError
        @step 說要畫圖 | token 為「結果不確定」說明
        @pass 建圖呼叫恰 1 次、交辦 0 次
        @api WS /api/brain/ws -> 101
        @story FR1.4、NFR3
        """
        self.client_factory.error = CapabilityError("transport", error_class="ReadTimeout")
        self.h.router_script.default = draw(0.9)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            turn = self.say(ws)
        self.assertEqual(G.CREATE_UNKNOWN_MESSAGE, turn[-2]["payload"]["text"])
        self.assertEqual(1, len(self.client_factory.calls))
        self.assertEqual([], self.h.orchestrator.dispatch_calls)

    def test_create_that_hangs_times_out_and_the_connection_keeps_working(self):
        """
        @purpose 修訂 1（契約 C5 錯誤表「建圖逾時」）：建圖呼叫真的卡住時必須在期限內放棄——
                 同一連線的訊息依序處理，沒有期限會讓該連線之後所有訊息都收不到回覆。
        @given 建圖替身第一次呼叫永遠不回；閘道的 wait_for 等替身確實卡住後才觸發逾時（注入時鐘）
        @step 說要畫圖 | token 為「結果不確定」說明、done；卡住的呼叫被取消；沒有交辦
        @step 同一連線再說一次 | 這次建圖成功並交辦
        @pass 逾時以 DIAGRAM_CREATE_TIMEOUT_SEC 為期限、第一次不重試、連線仍可處理下一則
        @api WS /api/brain/ws -> 101
        @story FR1.4、NFR3
        """
        self.client_factory.hang_next = True
        expired = []
        original = self.h.gw.timing

        async def wait_for(aw, timeout):
            if timeout != G.DIAGRAM_CREATE_TIMEOUT_SEC or expired:
                return await original.wait_for(aw, timeout)
            expired.append(timeout)
            task = asyncio.ensure_future(aw)
            while not self.client_factory.hanging:
                if task.done():
                    return task.result()
                await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise asyncio.TimeoutError()

        self.h.gw.timing = G.GatewayTiming(
            monotonic=original.monotonic, sleep=original.sleep, wait_for=wait_for
        )
        self.h.router_script.default = draw(0.9)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            first = self.say(ws)
            self.assertEqual(G.CREATE_UNKNOWN_MESSAGE, first[-2]["payload"]["text"])
            self.assertEqual("done", first[-1]["type"])
            self.assertEqual([], self.h.orchestrator.dispatch_calls)
            second = self.say(ws)
        self.assertEqual([G.DIAGRAM_CREATE_TIMEOUT_SEC], expired)
        self.assertTrue(self.client_factory.cancelled)
        self.assertEqual("done", second[-1]["type"])
        self.assertEqual(2, len(self.client_factory.calls))
        self.assertEqual(1, len(self.h.orchestrator.dispatch_calls))
        self.assertEqual(["draft"], [s for _i, s in self.diagrams()])

    def test_forbidden_403_text_depends_on_its_source(self):
        """
        @purpose 修訂 1（FR4.1）：建圖 403 只有在「缺架構編輯權」時才回申請角色的說明；
                 K2 或擁有權的 403 回不指向角色申請的說明。
        @given 建圖替身依序拋 arch_forbidden=True 與 False 的 403
        @step 說要畫圖（第一次） | 回 NEED_ARCH_EDIT_MESSAGE
        @step 再說一次 | 回 CREATE_FORBIDDEN_MESSAGE
        @pass 兩次都不交辦，文字分流正確
        @api WS /api/brain/ws -> 101
        @story FR4.1
        """
        self.h.router_script.default = draw(0.9)
        self.target_system()
        replies = []
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            for arch in (True, False):
                self.client_factory.error = CapabilityError("http", status_code=403, arch_forbidden=arch)
                replies.append(self.say(ws)[-2]["payload"]["text"])
        self.assertEqual([G.NEED_ARCH_EDIT_MESSAGE, G.CREATE_FORBIDDEN_MESSAGE], replies)
        # 使用者裁決：非架構權的 403 指向平台管理者檢查角色權限（專案管理者改不了 K2），
        # 且不得再指回「架構編輯權」這個原因。
        self.assertIn("平台管理者", G.CREATE_FORBIDDEN_MESSAGE)
        self.assertNotIn("架構編輯權", G.CREATE_FORBIDDEN_MESSAGE)
        self.assertNotIn("專案管理者", G.CREATE_FORBIDDEN_MESSAGE)
        self.assertEqual([], self.h.orchestrator.dispatch_calls)

    def test_create_404_is_reported_as_permanent_not_retry_later(self):
        """
        @purpose 建圖回 404 代表系統已不存在或已無法存取，是永久性失敗；
                 回「請稍後再試一次」會讓使用者白白重試。
        @given 建圖替身拋 404 的 CapabilityError
        @step 說要畫圖 | 回 CREATE_NOT_FOUND_MESSAGE，不交辦
        @pass 回覆為 CREATE_NOT_FOUND_MESSAGE 且不含「稍後」、交辦次數為 0
        @api WS /api/brain/ws -> 101
        @story FR4.1
        """
        self.h.router_script.default = draw(0.9)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            self.client_factory.error = CapabilityError("http", status_code=404)
            reply = self.say(ws)[-2]["payload"]["text"]
        self.assertEqual(G.CREATE_NOT_FOUND_MESSAGE, reply)
        self.assertNotIn("稍後", reply)
        self.assertEqual([], self.h.orchestrator.dispatch_calls)


class ClarifyFlowTest(_GatewayBase):
    def test_intent_clarify_keeps_the_new_diagram_probability(self):
        """
        @purpose 修訂 1（FR2.4）：先回答「意圖」反問後，原判定的新建機率 p 必須帶回；
                 丟掉 p 會變成不明，系統下沒有圖時「要修改」的句子會被誤建一張新圖。
        @given 系統下沒有圖、作業對象為該系統；路由判定信心不足（意圖反問）且 p=0.05（要修改）
        @step 說話 | 收到意圖反問
        @step 點選唯一的意圖候選 | 收到 new_or_modify 反問且只列「新建」（FR2.4），沒有建圖
        @pass 建圖 0 次、交辦 0 次
        @api WS /api/brain/ws -> 101
        @story FR2.4
        """
        self.h.router_script.default = dataclasses.replace(low_confidence("改一下架構"),
                                                           new_diagram_probability=0.05)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            # 不含專案名「電商」：含名稱的句子會先被對象掃描攔下改問對象。
            intent_clarify = self.say(ws, "幫我把架構改一下")[-1]
            self.assertEqual("clarify", intent_clarify["type"])
            cand = intent_clarify["payload"]["candidates"][0]["id"]
            after = self.select(ws, cand)
        self.assertEqual(("clarify", "new_or_modify"), (after[-1]["type"], after[-1]["payload"]["kind"]))
        self.assertEqual(["create"], [c["action"] for c in after[-1]["payload"]["candidates"]])
        self.assertEqual([], self.client_factory.calls)
        self.assertEqual([], self.h.orchestrator.dispatch_calls)

    def test_pick_system_lists_owned_systems_and_selection_creates(self):
        """
        @purpose FR3.1／FR3.4：沒有作業對象 → 反問掛在哪個系統（可點選）；點選後建草稿並交辦
        @given alice 有系統「前台」，作業對象未設定
        @step 說要畫圖 | clarify kind=pick_system，候選帶 systemId
        @step 點選該候選 | 建一張草稿並交辦，對象切到新圖
        @pass 候選只列 alice 的系統、點選後恰建一張
        @api WS /api/brain/ws -> 101
        @story FR3.1、FR3.4
        """
        self.h.router_script.default = draw(0.9)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            clarify = self.say(ws)[-1]
            self.assertEqual(("clarify", "pick_system"), (clarify["type"], clarify["payload"]["kind"]))
            cands = clarify["payload"]["candidates"]
            self.assertEqual([str(self.system.id)], [c["systemId"] for c in cands])
            turn = self.select(ws, cands[0]["id"])
        self.assertEqual("done", turn[-1]["type"])
        self.assertEqual(1, len(self.diagrams()))
        self.assertEqual(1, len(self.h.orchestrator.dispatch_calls))

    def test_no_systems_replies_with_project_page_path(self):
        """
        @purpose FR3.3：名下沒有任何系統 → 回覆先建立專案與系統，不自動建立
        @given 另一位沒有任何專案的使用者 bob
        @step bob 說要畫圖 | token 為固定說明（含 /projects）後 done
        @pass 建圖 0 次
        @api WS /api/brain/ws -> 101
        @story FR3.3
        """
        self.h.user("bob")
        self.token = self.h.token("bob")
        self.h.router_script.default = draw(0.9)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            turn = self.say(ws)
        self.assertEqual(G.NO_SYSTEM_MESSAGE, turn[-2]["payload"]["text"])
        self.assertIn("/projects", G.NO_SYSTEM_MESSAGE)
        self.assertEqual([], self.client_factory.calls)

    def test_resume_draft_or_new_comes_first_when_a_draft_exists(self):
        """
        @purpose FR6.3a：系統下已有草稿，即使 p ≥ t 也先反問；選草稿 → 切到草稿交辦、不建新圖
        @given 系統下一張草稿；p=0.95
        @step 說要畫圖 | clarify kind=resume_draft_or_new，草稿在前、「新建」在最後
        @step 點選草稿 | 交辦，作業對象為該草稿
        @pass 建圖 0 次
        @api WS /api/brain/ws -> 101
        @story FR6.3a
        """
        draft = self.add_diagram("舊草稿", status="draft")
        self.h.router_script.default = draw(0.95)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            clarify = self.say(ws)[-1]
            self.assertEqual("resume_draft_or_new", clarify["payload"]["kind"])
            cands = clarify["payload"]["candidates"]
            self.assertEqual([str(draft), None], [c["diagramId"] for c in cands])
            self.assertEqual(["modify", "create"], [c["action"] for c in cands])
            self.select(ws, cands[0]["id"])
        self.assertEqual([], self.client_factory.calls)
        self.assertEqual(draft, self.segment().diagram_id)
        self.assertEqual(1, len(self.h.orchestrator.dispatch_calls))

    def test_new_or_modify_when_unclear_and_create_choice_creates(self):
        """
        @purpose FR2.2：作業對象是正式圖、p 落在不明區 → 反問新建或修改；選新建 → 建在該圖的系統下
        @given 系統下一張正式圖且作業對象為它；p=0.5
        @step 說要畫圖 | clarify kind=new_or_modify，新建在前
        @step 點選新建 | 建一張草稿並交辦
        @pass 系統下共兩張圖，新的一張為 draft
        @api WS /api/brain/ws -> 101
        @story FR2.1、FR2.2
        """
        ready = self.add_diagram("正式圖")
        self.target_diagram(ready)
        self.h.router_script.default = draw(0.5)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            clarify = self.say(ws)[-1]
            self.assertEqual("new_or_modify", clarify["payload"]["kind"])
            self.assertEqual(["create", "modify"], [c["action"] for c in clarify["payload"]["candidates"]])
            self.select(ws, "create")
        self.assertEqual([(ready, "ready"), (ready + 1, "draft")], self.diagrams())

    def test_pick_diagram_for_modify_and_a_stale_candidate_is_relisted(self):
        """
        @purpose FR3.2／FR3.5：要修改但系統下多張圖 → 反問改哪一張；點選的圖已被刪 → 不執行、重新列出
        @given 系統下兩張正式圖；p=0.05（要修改）
        @step 說要改 | clarify kind=pick_diagram，兩筆、新到舊
        @step 刪掉第一筆的圖後點選它 | 再收到 clarify（pick_diagram），只剩一筆；沒有交辦
        @pass 失效候選不被執行
        @api WS /api/brain/ws -> 101
        @story FR3.2、FR3.5
        """
        first = self.add_diagram("一號")
        second = self.add_diagram("二號")
        self.h.router_script.default = draw(0.05)
        self.target_system()
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            clarify = self.say(ws)[-1]
            self.assertEqual("pick_diagram", clarify["payload"]["kind"])
            cands = clarify["payload"]["candidates"]
            self.assertEqual({str(first), str(second)}, {c["diagramId"] for c in cands})
            stale = next(c for c in cands if c["diagramId"] == str(second))
            self.h.db.query(UserDiagram).filter(UserDiagram.id == second).delete()
            self.h.db.commit()
            again = self.select(ws, stale["id"])
        self.assertEqual(("clarify", "pick_diagram"),
                         (again[-1]["type"], again[-1]["payload"]["kind"]))
        self.assertEqual([str(first)], [c["diagramId"] for c in again[-1]["payload"]["candidates"]])
        # 只剩一張也重新列出、不改由另一張代替（FR3.5）；沒有交辦、沒有建圖。
        self.assertEqual([], self.h.orchestrator.dispatch_calls)
        self.assertEqual([], self.client_factory.calls)

    def test_more_than_ten_candidates_lists_ten_with_a_note(self):
        """
        @purpose FR3.6：候選超過上限只列 10 筆並說明「其餘請用切換對象選取」
        @given alice 有 12 個系統、未設定作業對象
        @step 說要畫圖 | pick_system 恰 10 筆，最後一筆標籤帶說明
        @pass 筆數與說明皆符合
        @api WS /api/brain/ws -> 101
        @story FR3.6
        """
        facade = HierarchyFacade(self.h.db)
        for n in range(11):
            facade.create_system(self.principal, project_id=self.project.id, name=f"系統{n:02d}",
                                 project_visible=lambda _p: True)
        self.h.router_script.default = draw(0.9)
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            clarify = self.say(ws)[-1]
        cands = clarify["payload"]["candidates"]
        self.assertEqual(10, len(cands))
        self.assertTrue(cands[-1]["label"].endswith("（其餘請用切換對象選取）"))


class RereadTargetTest(unittest.TestCase):
    def test_reread_compares_the_diagram(self):
        """
        @purpose 契約 C7：Redis 失誤後重讀時，切到圖必須比對 diagram_id，否則會把未寫入誤判為已確認
        @given 段內為系統 3、沒有圖
        @step 以 diagram_id=9 的目標重讀 | None（未確認）
        @step 段內為圖 9 時重讀 | 取回 session
        @pass 兩者分流正確
        @story FR1.3
        """
        from types import SimpleNamespace
        from services import brain_gateway_rules as rules

        def gateway_with(segment):
            gw = G.BrainGateway.__new__(G.BrainGateway)
            gw.store = SimpleNamespace(load=lambda _k: SimpleNamespace(segments={"shared": segment}))
            return gw

        conn = SimpleNamespace(session_key=KEY)
        target = rules.TargetRef(None, 3, "", "", diagram_id=9)
        stale = SimpleNamespace(project_id=1, system_id=3, diagram_id=None)
        fresh = SimpleNamespace(project_id=1, system_id=3, diagram_id=9)
        self.assertIsNone(asyncio.run(gateway_with(stale)._reread_target(conn, "shared", target)))
        self.assertIsNotNone(asyncio.run(gateway_with(fresh)._reread_target(conn, "shared", target)))


if __name__ == "__main__":
    unittest.main()
