"""build-and-test 本機驗證 F1（2026-11-12）：架構圖掛到系統。

**本階段新增、已核可 scope／requirements 尚未涵蓋**：FR9.1 只說系統對應架構圖檔、FR9.5 只要求
專案／系統的建立路徑。回補：requirements 新增「架構圖掛到系統」FR、user-stories 補 AC。

缺陷：全 backend 唯一寫入 `user_diagrams.system_id` 的是一次性遷移，新存的圖永遠 `system_id`
為 NULL，於是大腦的架構設計／評核／成本在任何新系統上都回「這個系統下沒有掛上的架構圖」。

兩條寫入路徑（同一份判定，`HierarchyFacade.assert_system_attachable`）：
  1. 存檔時掛：`POST /api/collab/diagrams` 帶 `system_id`；
  2. 系統頁掛圖／改掛／取消：`PUT /api/hierarchy/diagrams/{id}/system`。

授權（`team.md` 規則 A 的雙向）：呼叫者須擁有那張圖，且對目標系統所屬專案有寫入資格
（`K2 edit` ＋ 可見 ＋ 擁有者，與建立系統相同）。不符一律拒絕；存檔帶不合格系統時整個請求
失敗、不存成未掛載的圖。

**突變驗證**（結果記於 `construction/build-and-test/local-verify-fixes.md`）：
  M1 存檔路徑整個拿掉掛載資格判定 → 存檔帶不合格系統的三案紅；
  M1b 拿掉目標系統的擁有者檢查（只剩可見性） → 「成員但非擁有者」的存檔與掛圖兩案紅；
  M2 系統頁掛圖拿掉專案寫入資格檢查 → `test_attach_to_unwritable_system_is_rejected` 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import UserDiagram
from services.auth import get_current_user
from services.hierarchy_facade import HierarchyFacade, mint_principal
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole
from tests.helpers import close_session, make_session, make_user

ROLE_ARCHITECT = "Project_Architect"  # A1 edit、K2 view+edit
ROLE_DEVELOPER = "Developer"  # A1 edit、K2 只有 view

XML = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'


class DiagramSystemAttachTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_ARCHITECT)
        self.bob = make_user(self.db, username="bob", role=ROLE_ARCHITECT)
        self.dev = make_user(self.db, username="dev", role=ROLE_DEVELOPER)
        app.dependency_overrides[get_db] = lambda: self.db
        membership = MembershipFacade(self.db)
        self.p_alice = membership.create_project_with_owner(mint_principal(self.alice), name="電商").id
        self.p_bob = membership.create_project_with_owner(mint_principal(self.bob), name="金流").id
        self.s_alice = self._create_system(self.alice, self.p_alice, "電商前台系統")
        self.s_alice2 = self._create_system(self.alice, self.p_alice, "電商後台系統")
        self.s_bob = self._create_system(self.bob, self.p_bob, "支付系統")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def _create_system(self, user, project_id: int, name: str) -> int:
        res = self.client_as(user).post(
            f"/api/hierarchy/projects/{project_id}/systems", json={"name": name}
        )
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()["id"]

    def _create_diagram(self, user, **extra) -> int:
        res = self.client_as(user).post(
            "/api/collab/diagrams", json={"xml_data": XML, "title": "圖", **extra}
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["id"]

    def _system_of(self, diagram_id: int):
        self.db.expire_all()
        return self.db.query(UserDiagram).filter(UserDiagram.id == diagram_id).one().system_id

    def _diagram_count(self) -> int:
        self.db.expire_all()
        return self.db.query(UserDiagram).count()

    # -- 存檔時掛 -------------------------------------------------------------

    def test_create_with_owned_system_attaches_and_brain_can_list_it(self):
        """
        @purpose 存檔時帶目前作業對象的系統，圖就掛上；大腦讀系統下的圖（`list_diagrams_of_system`）撿得到
        @given alice 擁有專案「電商」與系統「電商前台系統」
        @step alice POST /api/collab/diagrams 帶 system_id | 200，回應含 id 與 system_id
        @step GET /api/collab/diagrams | 該圖的 system_id 為該系統
        @step 以大腦同一條讀取路徑列系統下的圖 | 含該圖
        @pass 三處皆指向同一系統
        @api POST /api/collab/diagrams -> 200 | 存檔時掛到系統
        @api GET /api/collab/diagrams -> 200 | 我的圖含 system_id
        @story US9.1
        """
        res = self.client_as(self.alice).post(
            "/api/collab/diagrams",
            json={"xml_data": XML, "title": "電商架構", "system_id": self.s_alice},
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(set(body), {"id", "system_id", "status", "message"})
        self.assertEqual(body["system_id"], self.s_alice)
        self.assertEqual(self._system_of(body["id"]), self.s_alice)

        listed = self.client_as(self.alice).get("/api/collab/diagrams").json()
        self.assertEqual(
            [(d["id"], d["system_id"]) for d in listed if d["id"] == body["id"]],
            [(body["id"], self.s_alice)],
        )
        # 大腦的 `_list_system_diagrams` 就是這一個 facade 呼叫（work_orchestrator.py）。
        brain_view = HierarchyFacade(self.db).list_diagrams_of_system(
            mint_principal(self.alice), system_id=self.s_alice
        )
        self.assertEqual(brain_view, [(body["id"], "電商架構")])

    def test_create_without_system_stays_unattached(self):
        """
        @purpose 不帶 system_id 時行為不變（未掛載），既有呼叫端不受影響
        @given alice
        @step POST /api/collab/diagrams 不帶 system_id | 200、system_id 為 null
        @pass 資料庫的 system_id 為 NULL
        @api POST /api/collab/diagrams -> 200 | 不帶系統
        @story US9.1
        """
        did = self._create_diagram(self.alice)
        self.assertIsNone(self._system_of(did))

    def test_create_with_unwritable_system_errors_and_creates_nothing(self):
        """
        @purpose 存檔帶了不合格的系統要明確回錯，不得悄悄存成未掛載的圖
        @given bob 的系統「支付系統」；alice 先被邀請為「金流」的成員（看得到、不是擁有者）
        @step alice POST 帶 bob 的 system_id（非成員時） | 404，圖數不變
        @step bob 邀請 alice 為一般成員後再 POST | 仍 404，圖數不變
        @pass 兩次都沒有新建任何圖
        @api POST /api/collab/diagrams -> 404 | 目標系統不可寫
        @story US9.1
        """
        before = self._diagram_count()
        res = self.client_as(self.alice).post(
            "/api/collab/diagrams",
            json={"xml_data": XML, "title": "偷掛", "system_id": self.s_bob},
        )
        self.assertEqual(res.status_code, 404, res.text)
        self.assertEqual(self._diagram_count(), before)

        MembershipFacade(self.db).invite_member(
            mint_principal(self.bob),
            project_id=self.p_bob,
            user_id=self.alice.id,
            role=ProjectRole.MEMBER.value,
        )
        res = self.client_as(self.alice).post(
            "/api/collab/diagrams",
            json={"xml_data": XML, "title": "偷掛", "system_id": self.s_bob},
        )
        self.assertEqual(res.status_code, 404, res.text)
        self.assertEqual(self._diagram_count(), before)

    def test_create_with_system_without_k2_edit_is_403_and_creates_nothing(self):
        """
        @purpose 有架構圖編輯權但沒有 K2 edit 的角色，帶系統存檔一律 403，不存圖
        @given dev（Developer：A1 edit、K2 只有 view）
        @step dev POST 帶 alice 的 system_id | 403
        @pass 圖數不變
        @api POST /api/collab/diagrams -> 403 | 缺 K2 edit
        @story US9.1
        """
        before = self._diagram_count()
        res = self.client_as(self.dev).post(
            "/api/collab/diagrams",
            json={"xml_data": XML, "title": "圖", "system_id": self.s_alice},
        )
        self.assertEqual(res.status_code, 403, res.text)
        self.assertEqual(self._diagram_count(), before)

    def test_create_with_nonexistent_system_is_404(self):
        """
        @purpose 不存在的系統與「不屬於你」回同一種結果
        @given alice
        @step POST 帶不存在的 system_id | 404，detail 與帶 bob 的系統相同
        @pass 不存在與不可寫不可區分
        @api POST /api/collab/diagrams -> 404 | 系統不存在
        @story US9.1
        """
        a = self.client_as(self.alice).post(
            "/api/collab/diagrams", json={"xml_data": XML, "title": "x", "system_id": 99999}
        )
        b = self.client_as(self.alice).post(
            "/api/collab/diagrams", json={"xml_data": XML, "title": "x", "system_id": self.s_bob}
        )
        self.assertEqual((a.status_code, b.status_code), (404, 404))
        self.assertEqual(a.json(), b.json())

    # -- 系統頁掛圖／改掛／取消 ---------------------------------------------------

    def test_owner_attaches_moves_and_detaches(self):
        """
        @purpose 擁有者把自己的圖掛到系統、改掛到另一個系統、再取消掛載
        @given alice 的一張未掛載的圖、兩個自己的系統
        @step PUT 掛到系統 1 | 200，{diagram_id, system_id}
        @step PUT 改掛到系統 2 | 200
        @step PUT system_id=null | 200，system_id 為 null
        @pass 每一步資料庫都同步
        @api PUT /api/hierarchy/diagrams/{diagram_id}/system -> 200 | 掛載、改掛、取消
        @story US9.1
        """
        did = self._create_diagram(self.alice)
        client = self.client_as(self.alice)
        for target in (self.s_alice, self.s_alice2, None):
            res = client.put(f"/api/hierarchy/diagrams/{did}/system", json={"system_id": target})
            self.assertEqual(res.status_code, 200, res.text)
            self.assertEqual(res.json(), {"diagram_id": did, "system_id": target})
            self.assertEqual(self._system_of(did), target)

    def test_non_owner_of_diagram_gets_404(self):
        """
        @purpose 只能掛自己的圖：別人的圖回 404（與不存在同一種結果），歸屬不變
        @given alice 的圖；bob 有自己可寫的系統
        @step bob PUT alice 的圖到 bob 的系統 | 404
        @pass alice 的圖仍未掛載
        @api PUT /api/hierarchy/diagrams/{diagram_id}/system -> 404 | 不是圖的擁有者
        @story US9.1
        """
        did = self._create_diagram(self.alice)
        res = self.client_as(self.bob).put(
            f"/api/hierarchy/diagrams/{did}/system", json={"system_id": self.s_bob}
        )
        self.assertEqual(res.status_code, 404, res.text)
        self.assertIsNone(self._system_of(did))

    def test_attach_to_unwritable_system_is_rejected(self):
        """
        @purpose 對目標系統所屬專案沒有寫入資格（非成員、或成員但不是擁有者）一律拒絕
        @given alice 的圖已掛在自己的系統；bob 的系統「支付系統」
        @step alice PUT 到 bob 的系統（非成員） | 404，歸屬不變
        @step bob 把 alice 邀為 project_admin 後再 PUT | 仍 404（不是擁有者），歸屬不變
        @pass 兩次歸屬都維持原系統
        @api PUT /api/hierarchy/diagrams/{diagram_id}/system -> 404 | 目標系統不可寫
        @story US9.1
        """
        did = self._create_diagram(self.alice, system_id=self.s_alice)
        client = self.client_as(self.alice)
        res = client.put(f"/api/hierarchy/diagrams/{did}/system", json={"system_id": self.s_bob})
        self.assertEqual(res.status_code, 404, res.text)
        self.assertEqual(self._system_of(did), self.s_alice)

        MembershipFacade(self.db).invite_member(
            mint_principal(self.bob),
            project_id=self.p_bob,
            user_id=self.alice.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        res = client.put(f"/api/hierarchy/diagrams/{did}/system", json={"system_id": self.s_bob})
        self.assertEqual(res.status_code, 404, res.text)
        self.assertEqual(self._system_of(did), self.s_alice)

    def test_without_k2_edit_is_403(self):
        """
        @purpose 缺 K2 edit 的角色不能改歸屬（含取消掛載）
        @given dev 自己的一張圖
        @step dev PUT system_id=null | 403
        @pass 歸屬不變
        @api PUT /api/hierarchy/diagrams/{diagram_id}/system -> 403 | 缺 K2 edit
        @story US9.1
        """
        did = self._create_diagram(self.dev)
        res = self.client_as(self.dev).put(
            f"/api/hierarchy/diagrams/{did}/system", json={"system_id": None}
        )
        self.assertEqual(res.status_code, 403, res.text)

    def test_missing_field_is_422_not_detach(self):
        """
        @purpose 漏傳 system_id 不得被讀成「取消掛載」
        @given alice 已掛載的圖
        @step PUT 空本體 | 422
        @pass 歸屬不變
        @api PUT /api/hierarchy/diagrams/{diagram_id}/system -> 422 | 缺欄位
        @story US9.1
        """
        did = self._create_diagram(self.alice, system_id=self.s_alice)
        res = self.client_as(self.alice).put(f"/api/hierarchy/diagrams/{did}/system", json={})
        self.assertEqual(res.status_code, 422, res.text)
        self.assertEqual(self._system_of(did), self.s_alice)

    def test_shared_diagram_list_does_not_expose_other_owners_system(self):
        """
        @purpose 我的圖清單只對自己擁有的圖給 system_id；別人分享給我的圖不外露其歸屬
        @given alice 的圖掛在她的系統並分享給 bob
        @step bob GET /api/collab/diagrams | 該圖 is_owner=false、system_id=null
        @pass 歸屬不外露
        @api GET /api/collab/diagrams -> 200 | 分享的圖
        @story US9.1
        """
        did = self._create_diagram(self.alice, system_id=self.s_alice)
        share = self.client_as(self.alice).post(
            f"/api/collab/diagrams/{did}/share", json={"user_ids": [self.bob.id]}
        )
        self.assertEqual(share.status_code, 200, share.text)
        listed = self.client_as(self.bob).get("/api/collab/diagrams").json()
        row = [d for d in listed if d["id"] == did]
        self.assertEqual(len(row), 1)
        self.assertFalse(row[0]["is_owner"])
        self.assertIsNone(row[0]["system_id"])


if __name__ == "__main__":
    unittest.main()
