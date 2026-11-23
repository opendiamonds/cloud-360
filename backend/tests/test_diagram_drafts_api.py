"""261116-brain-create-diagram U1 diagram-drafts：架構圖 API 的草稿狀態（契約 C1～C4）。

`team.md` B 規則：四支端點以 TestClient 斷言 status code 與回應**鍵集合**
（`response_model` 會靜默丟掉沒列的鍵——鍵集合斷言是唯一的機械防線）。
A 規則：`require_arch_action("edit")` 的 allow／deny 雙向（NFR5）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import io
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import (
    DRAFT_REJECTED_DETAIL,
    ArchitectureReview,
    EstimateSet,
    UserDiagram,
    diagram_shares,
)
from services.auth import get_current_user
from services.rbac import ensure_role_permissions_seeded
from tests.helpers import close_session, make_session, make_user

XML = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
XML2 = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/><mxCell id="2"/></root></mxGraphModel>'

CREATED_KEYS = {"id", "system_id", "status", "message", "diagram_status"}
SAVED_KEYS = {"status", "message", "diagram_status"}
ITEM_KEYS = {"id", "title", "updated_at", "is_owner", "system_id", "diagram_status"}
DETAIL_KEYS = {
    "id", "title", "xml_data", "updated_at", "is_owner", "shared_user_ids",
    "can_edit", "can_review", "diagram_status",
}


class _ApiFixture(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        # Project_Architect：A1 edit、A3 edit、C1 edit 皆有；FinOps_Analyst：K1 有、A1 edit 沒有。
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.bob = make_user(self.db, username="bob", role="Project_Architect")
        self.finops = make_user(self.db, username="finops", role="FinOps_Analyst")
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def _create(self, user, **extra):
        return self.client_as(user).post(
            "/api/collab/diagrams", json={"xml_data": XML, "title": "圖", **extra}
        )

    def _draft_of(self, user) -> int:
        res = self._create(user, as_draft=True)
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["id"]

    def _row(self, diagram_id) -> UserDiagram:
        self.db.expire_all()
        return self.db.query(UserDiagram).filter(UserDiagram.id == diagram_id).one()


class CreateAndReadTest(_ApiFixture):
    def test_as_draft_creates_a_draft_with_contract_keys(self):
        """
        @purpose 契約 C1：as_draft=true 建為草稿，回應鍵集合恰為 DiagramCreated
        @given alice（有架構圖編輯權）
        @step POST /api/collab/diagrams 帶 as_draft=true | 200，diagram_status=draft
        @pass 鍵集合等於契約清單，資料庫 status 為 draft
        @api POST /api/collab/diagrams -> 200 | 建立草稿
        @story FR6.1
        """
        res = self._create(self.alice, as_draft=True)
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(set(body), CREATED_KEYS)
        self.assertEqual((body["status"], body["diagram_status"]), ("success", "draft"))
        self.assertEqual(self._row(body["id"]).status, "draft")

    def test_without_as_draft_creates_ready(self):
        """
        @purpose 既有呼叫端不送 as_draft，行為不變：建為正式
        @given alice
        @step POST 不帶 as_draft | 200，diagram_status=ready
        @pass 資料庫 status 為 ready
        @api POST /api/collab/diagrams -> 200 | 建立正式圖
        @story FR6.5
        """
        res = self._create(self.alice)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["diagram_status"], "ready")
        self.assertEqual(self._row(res.json()["id"]).status, "ready")

    def test_list_and_detail_expose_diagram_status_with_contract_keys(self):
        """
        @purpose 契約 C3：清單與讀取都回 diagram_status，且既有欄位一個不少
        @given alice 一張草稿、一張正式圖
        @step GET /api/collab/diagrams | 每筆鍵集合等於 MyDiagramItem，狀態如實
        @step GET /api/collab/diagrams/{id} | 鍵集合等於 DiagramDetail
        @pass 兩支端點的鍵集合與狀態皆符合
        @api GET /api/collab/diagrams -> 200 | 清單含狀態
        @api GET /api/collab/diagrams/{diagram_id} -> 200 | 讀取含狀態
        @story FR6.4
        """
        draft = self._draft_of(self.alice)
        ready = self._create(self.alice).json()["id"]
        client = self.client_as(self.alice)

        listed = client.get("/api/collab/diagrams")
        self.assertEqual(listed.status_code, 200, listed.text)
        rows = {row["id"]: row for row in listed.json()}
        for row in rows.values():
            self.assertEqual(set(row), ITEM_KEYS)
        self.assertEqual((rows[draft]["diagram_status"], rows[ready]["diagram_status"]),
                         ("draft", "ready"))

        detail = client.get(f"/api/collab/diagrams/{draft}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(set(detail.json()), DETAIL_KEYS)
        self.assertEqual(detail.json()["diagram_status"], "draft")


class FinalizeTest(_ApiFixture):
    def _put(self, diagram_id, **extra):
        return self.client_as(self.alice).put(
            f"/api/collab/diagrams/{diagram_id}", json={"xml_data": XML2, "title": "新名", **extra}
        )

    def test_finalize_false_or_omitted_writes_content_but_keeps_draft(self):
        """
        @purpose FR6.2：自動存檔與評核前寫回不送 finalize，草稿不得因此轉正式
        @given alice 的草稿
        @step PUT 不帶 finalize | 200，diagram_status=draft，內容已更新
        @step PUT finalize=false | 仍為 draft
        @pass 兩次後狀態皆為 draft，xml 為新內容
        @api PUT /api/collab/diagrams/{diagram_id} -> 200 | 只寫內容
        @story FR6.2
        """
        did = self._draft_of(self.alice)
        res = self._put(did)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(set(res.json()), SAVED_KEYS)
        self.assertEqual(res.json()["diagram_status"], "draft")
        self.assertEqual(self._put(did, finalize=False).json()["diagram_status"], "draft")
        row = self._row(did)
        self.assertEqual((row.status, row.xml_data), ("draft", XML2))

    def test_finalize_true_turns_a_draft_ready_and_is_harmless_on_ready(self):
        """
        @purpose FR6.2：手動存檔（finalize=true）把草稿轉正式；對正式圖無作用
        @given alice 的一張草稿與一張正式圖
        @step PUT 草稿 finalize=true | diagram_status=ready
        @step PUT 正式圖 finalize=true | 仍為 ready
        @pass 兩張最後皆為 ready
        @api PUT /api/collab/diagrams/{diagram_id} -> 200 | 轉為正式
        @story FR6.2
        """
        did = self._draft_of(self.alice)
        self.assertEqual(self._put(did, finalize=True).json()["diagram_status"], "ready")
        self.assertEqual(self._row(did).status, "ready")
        ready = self._create(self.alice).json()["id"]
        self.assertEqual(self._put(ready, finalize=True).json()["diagram_status"], "ready")
        self.assertEqual(self._row(ready).status, "ready")


class DraftRejectedTest(_ApiFixture):
    def test_share_rejects_a_draft_and_writes_nothing(self):
        """
        @purpose FR6.4a：草稿不得分享
        @given alice 的草稿
        @step POST /share 給 bob | 409，detail 為固定常數
        @pass diagram_shares 沒有任何列
        @api POST /api/collab/diagrams/{diagram_id}/share -> 409 | 草稿不得分享
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        res = self.client_as(self.alice).post(
            f"/api/collab/diagrams/{did}/share", json={"user_ids": [self.bob.id]}
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(res.json()["detail"], DRAFT_REJECTED_DETAIL)
        self.assertEqual(self.db.execute(diagram_shares.select()).fetchall(), [])

    def test_share_by_non_owner_is_403_not_409(self):
        """
        @purpose 擁有權檢查先於草稿檢查，非擁有者不能以 409 探測他人圖的狀態
        @given alice 的草稿
        @step bob POST /share | 403
        @pass 回 403 而非 409
        @api POST /api/collab/diagrams/{diagram_id}/share -> 403 | 非擁有者
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        res = self.client_as(self.bob).post(
            f"/api/collab/diagrams/{did}/share", json={"user_ids": [self.alice.id]}
        )
        self.assertEqual(res.status_code, 403, res.text)

    def test_review_rejects_a_draft(self):
        """
        @purpose FR6.4a：評核不得以草稿為對象
        @given alice 的草稿
        @step POST /api/architecture/reviews 帶 diagram_id | 409
        @pass 沒有建立任何評核紀錄
        @api POST /api/architecture/reviews -> 409 | 草稿不得評核
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        res = self.client_as(self.alice).post(
            "/api/architecture/reviews", json={"diagram_id": did}
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(res.json()["detail"], DRAFT_REJECTED_DETAIL)
        self.assertEqual(self.db.query(ArchitectureReview).count(), 0)

    def test_commit_collab_rejects_a_draft_and_keeps_xml(self):
        """
        @purpose FR6.4a：評核共編的確認儲存不得覆寫草稿並記錄評核
        @given alice 的草稿（內容 XML）
        @step POST /api/architecture/reviews/commit-collab 帶新 XML | 409
        @pass 草稿 XML 未變、沒有評核紀錄
        @api POST /api/architecture/reviews/commit-collab -> 409 | 草稿不得評核
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        res = self.client_as(self.alice).post(
            "/api/architecture/reviews/commit-collab",
            json={"diagram_id": did, "xml_data": XML2, "overall_score": 90},
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(self._row(did).xml_data, XML)
        self.assertEqual(self.db.query(ArchitectureReview).count(), 0)

    def test_wa_collab_rejects_a_draft(self):
        """
        @purpose FR6.4a：WA 共編不得以草稿為對象
        @given alice 的草稿；模型金鑰檢查以替身略過（本案例不呼叫模型）
        @step POST /api/architecture/generate-wa-collab 帶 diagram_id | 409
        @pass 回 409 與固定訊息
        @api POST /api/architecture/generate-wa-collab -> 409 | 草稿不得共編
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        with patch("services.agent_router._ensure_llm_keys"), patch(
            "services.agent_router.run_wa_collab"
        ) as run:
            res = self.client_as(self.alice).post(
                "/api/architecture/generate-wa-collab",
                json={"messages": [{"role": "user", "content": "評核一下"}], "diagram_id": did},
            )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(res.json()["detail"], DRAFT_REJECTED_DETAIL)
        run.assert_not_called()


class EstimateBindingTest(_ApiFixture):
    def setUp(self):
        super().setUp()
        self._enqueue = patch("cost.estimate_intake_service.enqueue_advice_job")
        self._enqueue.start()

    def tearDown(self):
        self._enqueue.stop()
        super().tearDown()

    def _upload(self, user, diagram_id):
        parse_result = {
            "detection": {"status": "resolved", "cloud": "aws"},
            "lines": [{
                "ordinal": 1, "itemName": "EC2", "spec": "m5.large", "quantity": 1.0,
                "amount": 10.0, "currency": "USD", "parseStatus": "parsed",
                "rawText": "EC2,m5.large,1,10,USD",
            }],
            "totals": {"statedTotal": 10.0, "currency": "USD"},
            "sourceFormat": "csv",
        }
        files = [("files", ("est.csv", io.BytesIO(b"Description,Quantity,Cost\nEC2,1,10\n"), "text/csv"))]
        with patch("cost.estimate_intake_service.parse", return_value=parse_result):
            return self.client_as(user).post(
                "/api/cost/v1/sets", files=files, data={"diagram_id": str(diagram_id)}
            )

    def test_binding_own_draft_is_409_and_creates_no_set(self):
        """
        @purpose FR6.4a：估價不得綁自己的草稿
        @given alice 的草稿
        @step alice 上傳估價表帶該 diagram_id | 409
        @pass 沒有任何估價集被建立
        @api POST /api/cost/v1/sets -> 409 | 估價綁草稿
        @story FR6.4a
        """
        did = self._draft_of(self.alice)
        res = self._upload(self.alice, did)
        self.assertEqual(res.status_code, 409, res.text)
        self.assertEqual(res.json()["detail"], DRAFT_REJECTED_DETAIL)
        self.assertEqual(self.db.query(EstimateSet).count(), 0)

    def test_binding_someone_elses_draft_or_missing_diagram_keeps_current_behaviour(self):
        """
        @purpose 契約 C4 的擁有權優先：他人的圖或不存在的圖維持現況（原樣存入、不回錯）
                 ——否則 409 會成為探測他人圖狀態的管道
        @given bob 的草稿；一個不存在的 id
        @step alice 綁 bob 的草稿 | 201，diagram_id 原樣存入
        @step alice 綁不存在的 id | 201
        @pass 兩次都建立估價集
        @api POST /api/cost/v1/sets -> 201 | 他人或不存在的圖
        @story FR6.4a
        """
        bobs = self._draft_of(self.bob)
        res = self._upload(self.alice, bobs)
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["diagram_id"], bobs)
        self.assertEqual(self._upload(self.alice, 999999).status_code, 201)
        self.assertEqual(self.db.query(EstimateSet).count(), 2)


class CreatePermissionTest(_ApiFixture):
    def test_arch_edit_allows_and_k1_only_is_denied(self):
        """
        @purpose NFR5／FR4.1：建圖沿用架構編輯權；有 K1 但沒有架構編輯權者被拒且不建圖
        @given alice（Project_Architect）與 finops（FinOps_Analyst：K1 有、A1 edit 無）
        @step alice POST as_draft=true | 200
        @step finops POST as_draft=true | 403
        @pass 只有 alice 的一張圖存在
        @api POST /api/collab/diagrams -> 403 | 沒有架構編輯權
        @story FR4.1
        """
        self.assertEqual(self._create(self.alice, as_draft=True).status_code, 200)
        self.assertEqual(self._create(self.finops, as_draft=True).status_code, 403)
        self.db.expire_all()
        self.assertEqual(
            [self.alice.id], [d.user_id for d in self.db.query(UserDiagram).all()]
        )



class DraftRejectionIsDeclaredInOpenApiTest(unittest.TestCase):
    def test_every_draft_rejecting_endpoint_declares_409(self):
        """
        @purpose 契約 C4 的 409 必須進入 OpenAPI，前端產生型別與 tcms_validate 的介面比對才看得到；
                 只寫在實作裡，`openapi.json` 會宣稱這些端點只回 200／422。tcms-test-cases 的
                 機械檢查即因此對評核端點報 WARN。
        @given 本 app 產生的 OpenAPI
        @step 讀取五個拒收草稿的端點 | 各自的 responses 皆含 409
        @pass 五個端點全部宣告 409
        @api POST /api/architecture/reviews -> 409 | 草稿不得送評核
        @api POST /api/architecture/reviews/commit-collab -> 409 | 草稿不得寫回評核
        @api POST /api/architecture/generate-wa-collab -> 409 | 草稿不得用於 WA 共編
        @api POST /api/collab/diagrams/{diagram_id}/share -> 409 | 草稿不得分享
        @api POST /api/cost/v1/sets -> 409 | 自己的草稿不得綁估價
        @story FR6.4a
        """
        paths = app.openapi()["paths"]
        for path in (
            "/api/architecture/reviews",
            "/api/architecture/reviews/commit-collab",
            "/api/architecture/generate-wa-collab",
            "/api/collab/diagrams/{diagram_id}/share",
            "/api/cost/v1/sets",
        ):
            with self.subTest(path=path):
                self.assertIn("409", paths[path]["post"]["responses"])


if __name__ == "__main__":
    unittest.main()
