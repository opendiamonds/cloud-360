"""`U19 membership-service` 的 HTTP 層測試（`E1`–`E7`）。

對應 `unit-test-instructions.md §三` 的第三列（API／端點，**7** 個）。

**`E4`–`E6` 是本單元最危險失效模式的唯一對策**：`logical-components.md §二之二`
把「既有停用端點的前置檢查未被呼叫」列為**靜默**失效——停用照常成功，而
`AC12.3.3` 的保護消失。**沒有這些測試，拿掉那道檢查不會有任何東西變紅。**

不需要真實資料庫：`get_db`（`database.py:31`）與 `get_current_user`
（`services/auth.py:39`）都是穩定的模組層函式，可用
`app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用**不觸發**
`@app.on_event("startup")` 的 `init_db()`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import ProjectMember, Project, ReselectionEvent
import services.hierarchy_service as hierarchy_service
import services.membership_service as membership_service
from services.auth import get_current_user
from services.hierarchy_facade import mint_principal
from services.membership_errors import MembershipLockTimeout
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole
from tests.helpers import close_session, make_session, make_user

ROLE_K3_EDIT = "Project_Architect"    # K3 view+edit、K2 view+edit、**無** J3a
ROLE_K3_VIEW = "Developer"            # K3 view=True、edit=False
ROLE_NO_K3 = "SRE"                    # K3 view=False、edit=False
ROLE_GLOBAL_ADMIN = "Platform_Admin"  # J3a view+edit（停用端點需要它）

MEMBER_FIELDS = {"user_id", "display_name", "role", "joined_at"}
GUARD_REPORT_FIELDS = {"projects"}
GUARDED_PROJECT_FIELDS = {"project_id", "name"}
RESELECTION_FIELDS = {
    "id",
    "project_id",
    "cause",
    "promoted_user_id",
    "previous_owner_user_id",
    "previous_role",
    "new_role",
    "occurred_at",
    "acknowledged_at",
}


class MembershipEndpointTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_K3_EDIT)
        self.bob = make_user(self.db, username="bob", role=ROLE_K3_EDIT)
        self.carol = make_user(self.db, username="carol", role=ROLE_K3_VIEW)
        self.dave = make_user(self.db, username="dave", role=ROLE_NO_K3)
        self.root = make_user(self.db, username="root", role=ROLE_GLOBAL_ADMIN)
        self.facade = MembershipFacade(self.db)
        self.project = self.facade.create_project_with_owner(
            mint_principal(self.alice), name="P"
        )
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def members_url(self, project_id=None) -> str:
        pid = self.project.id if project_id is None else project_id
        return f"/api/membership/projects/{pid}/members"


class AuthorizationTest(MembershipEndpointTestBase):
    def test_E1_allow_and_deny_both_directions(self):
        """`E1`：allow／deny **雙向**，缺一不可（`team.md` 規則 A ＋ B 交叉）。

        三個 deny 側分別打中**不同的那一層**（`BR1.2` 的兩層串聯）：
          (a) 無 `K3.view`（`SRE`）→ 全域層在 dependency 就擋下；
          (b) 具 `K3.edit` 但**非本專案成員**（bob）→ **per-project 層**擋下
              ——這是 `AC12.5.2` 的 deny 側，只檢查一層會讓它完全失效；
              合併前必修第 14 項（`[PP-MB14]`=A）起回 **404**「查不到專案」而非 403，
              與「專案不存在」逐位元相同（逐位元比較見 `test_E11`）；
          (c) 是成員但只有 `K3.view`（carol）→ 讀得到、寫不了（仍 403：全域層）。
        """
        # allow：alice 具 K3.view/edit 且是該專案的 project_admin。
        allowed = self.client_as(self.alice).get(self.members_url())
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(len(allowed.json()), 1)

        # (a) 全域層不過。
        self.assertEqual(self.client_as(self.dave).get(self.members_url()).status_code, 403)
        self.assertEqual(
            self.client_as(self.dave)
            .post(self.members_url(), json={"user_id": self.carol.id, "role": "member"})
            .status_code,
            403,
        )

        # (b) 全域層過、per-project 層不過 → 404（不洩漏專案存在）。
        self.assertEqual(self.client_as(self.bob).get(self.members_url()).status_code, 404)
        self.assertEqual(
            self.client_as(self.bob)
            .post(self.members_url(), json={"user_id": self.carol.id, "role": "member"})
            .status_code,
            404,
        )

        # (c) 是成員、只有 view。
        self.facade.invite_member(
            mint_principal(self.alice),
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        carol_client = self.client_as(self.carol)
        self.assertEqual(carol_client.get(self.members_url()).status_code, 200)
        self.assertEqual(
            carol_client.post(
                self.members_url(), json={"user_id": self.bob.id, "role": "member"}
            ).status_code,
            403,
        )
        self.assertEqual(
            carol_client.delete(f"{self.members_url()}/{self.alice.id}").status_code,
            403,
        )
        self.assertEqual(
            carol_client.patch(
                f"{self.members_url()}/{self.alice.id}", json={"role": "member"}
            ).status_code,
            403,
        )

    def test_E2_status_codes_and_response_model_field_sets(self):
        """`E2`／`team.md` 規則 B：狀態碼 ＋ `response_model` 的**欄位集合**。

        斷言**集合相等**而非「包含」：前者在漏欄位與多欄位兩個方向都失敗。
        `invited_by` 刻意**不**在 `MemberView` 裡（`OPEN-FD19-6`），
        所以「順手把它加進回應」會在這裡紅燈。
        """
        client = self.client_as(self.alice)

        # 清單：200 ＋ MemberView 欄位集合
        listed = client.get(self.members_url())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(set(listed.json()[0]), MEMBER_FIELDS)

        # 邀請：**201** ＋ MemberView
        created = client.post(
            self.members_url(), json={"user_id": self.carol.id, "role": "member"}
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(set(created.json()), MEMBER_FIELDS)
        self.assertEqual(created.json()["role"], "member")

        # 改角色：200 ＋ MemberView
        patched = client.patch(
            f"{self.members_url()}/{self.carol.id}", json={"role": "project_admin"}
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(set(patched.json()), MEMBER_FIELDS)
        self.assertEqual(patched.json()["role"], "project_admin")

        # 封閉列舉：不在 `ProjectRole` 裡的值由 pydantic 擋在 422。
        self.assertEqual(
            client.patch(
                f"{self.members_url()}/{self.carol.id}", json={"role": "project_owner"}
            ).status_code,
            422,
        )

        # 移出：**204**，且對已非成員仍是 204（冪等，`[FD2]`=A）
        self.assertEqual(
            client.delete(f"{self.members_url()}/{self.carol.id}").status_code, 204
        )
        self.assertEqual(
            client.delete(f"{self.members_url()}/{self.carol.id}").status_code, 204
        )

        # 橫幅清單：200 ＋ ReselectionOut 欄位集合。先造一筆真的自動改選事件。
        # 被改選的是 alice（`K3.edit`）：合併前必修第 1 ＋ 4 項起只有合格接手人
        # 會被選中，只有 `K3.view` 的 carol 不會。
        orphan = hierarchy_service.create_project(
            self.db, owner_user_id=self.bob.id, name="Orphan"
        )
        self.db.add(
            ProjectMember(
                project_id=orphan.id,
                user_id=self.alice.id,
                role=ProjectRole.MEMBER.value,
                joined_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        self.db.commit()
        self.facade.run_auto_reselection(deactivated_user_id=self.bob.id)
        pending = self.client_as(self.alice).get("/api/membership/reselections/pending")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(set(pending.json()[0]), RESELECTION_FIELDS)
        self.assertEqual(pending.json()[0]["cause"], "auto_reselection")

        # 確認：204，重按一次 404（已確認的事件不再「改到」）
        event_id = pending.json()[0]["id"]
        ack_url = f"/api/membership/reselections/{event_id}/acknowledge"
        self.assertEqual(self.client_as(self.alice).post(ack_url).status_code, 204)
        self.assertEqual(self.client_as(self.alice).post(ack_url).status_code, 404)

    def test_E3_guard_responses_carry_the_report_shape(self):
        """`E3`／`BR6.1`／`BR6.2`：409 的狀態碼 ＋ `LastAdminGuardReport` 欄位集合。

        **回應本體就是該 model**（不是 `{"detail": ...}` 的包裝）——宣告一個
        model 卻回一個包裝過的形狀，等於讓 spec 說一件回應沒有做的事。

        **必須含專案名稱**：`entities.md` 逐字「只給 id 的話畫面無法告知使用者
        是哪個專案」。

        三個入口都驗（停用端點、自我移出、自我降級），因為三者共用同一個不變量
        但各自有自己的回應路徑。
        """
        # (a) 既有停用端點（`[FD1]`=A：alice 是 P 的唯一管理者）
        res = self.client_as(self.root).put(
            f"/api/auth/{self.alice.id}/active", json={"is_active": False}
        )
        self.assertEqual(res.status_code, 409)
        body = res.json()
        self.assertEqual(set(body), GUARD_REPORT_FIELDS)
        self.assertEqual(len(body["projects"]), 1)
        self.assertEqual(set(body["projects"][0]), GUARDED_PROJECT_FIELDS)
        self.assertEqual(body["projects"][0]["project_id"], self.project.id)
        self.assertEqual(body["projects"][0]["name"], "P")

        # (b) 自我移出 (c) 自我降級
        client = self.client_as(self.alice)
        for res in (
            client.delete(f"{self.members_url()}/{self.alice.id}"),
            client.patch(
                f"{self.members_url()}/{self.alice.id}", json={"role": "member"}
            ),
        ):
            self.assertEqual(res.status_code, 409)
            self.assertEqual(set(res.json()), GUARD_REPORT_FIELDS)
            self.assertEqual(set(res.json()["projects"][0]), GUARDED_PROJECT_FIELDS)


class ExistingDeactivationEndpointTest(MembershipEndpointTestBase):
    """`E4`–`E6`／`BR6.3`：既有兩道保護不得被削弱，新守門在寫入之前。"""

    def test_E4_self_deactivation_guard_still_fires_before_the_write(self):
        """`E4`／`BR6.3` 第一道（`user_router.py:654`／`:655` 的條件與位置）。

        位置以「被拒之後 `is_active` 仍為 True」斷言——這是「在寫入之前」唯一
        的外部可觀察判準。
        """
        res = self.client_as(self.root).put(
            f"/api/auth/{self.root.id}/active", json={"is_active": False}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"], "無法停用自己的帳號")
        self.db.refresh(self.root)
        self.assertTrue(self.root.is_active)

    def test_E5_last_editable_global_admin_guard_still_fires_before_the_write(self):
        """`E5`／`BR6.3` 第二道（`user_router.py:676`／`:679` 的條件與位置）。

        **本測試必須以 `dependency_overrides` 構造一個真實認證路徑到不了的狀態，
        而那本身是一項發現（如實記載，不是本單元引入的）。**

        推導：這道守門只在 `admin_edit_count <= 1` 時觸發，而
        `admin_edit_count` 數的是**全部 active 且具 `J3a.edit`** 的使用者。
        要觸發它，必須 (i) 目標使用者具 `J3a.edit` 且 active（外層 `if` 的條件），
        且 (ii) 這種使用者只有一位。但**執行者**也必須具 `J3a.edit`
        （`require_story_action("J3a", "edit")`）而且必須 active
        （`services/auth.py:75` 的 `get_user_from_token` 對停用帳號回 403），
        所以執行者一定被數進去。若執行者 ≠ 目標，計數至少為 2；若執行者 ＝ 目標，
        **第一道**（自我停用）先擋下。兩種情況都到不了這一道。

        故這道守門在**正式路徑上不可達**。它是**既存**狀態，與本單元無關——
        `BR6.3` 要求本變更不得削弱它，而本變更原樣保留了它（diff 中該段為零
        改動）。本測試以覆寫身分的方式鎖住它的**條件與位置**，是目前唯一能
        證明「它還在、而且仍在寫入之前」的方法；它不能證明它在正式路徑上會跑。
        """
        # root 是唯一具 J3a.edit 的使用者（alice／bob／carol／dave 都沒有）。
        editors = [
            u
            for u in self.db.query(__import__("models").User).all()
            if membership_service.user_can(self.db, u.role, "J3a", "edit")
        ]
        self.assertEqual([u.username for u in editors], ["root"])

        # 以一個**本身不被計數**的執行者覆寫身分，才能讓計數停在 1。
        actor = make_user(
            self.db, username="ghost", role=ROLE_GLOBAL_ADMIN, is_active=False
        )
        res = self.client_as(actor).put(
            f"/api/auth/{self.root.id}/active", json={"is_active": False}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()["detail"],
            "無法停用：系統必須保留至少一位可編輯使用者角色的管理員",
        )
        self.db.refresh(self.root)
        self.assertTrue(self.root.is_active)

    def test_E6_the_new_guard_runs_before_is_active_is_written(self):
        """`E6`／`BR6.1`：**三道檢查都在 `is_active` 寫入之前。**

        突變驗證（`unit-test-instructions.md §七` 第 3 列）：把
        `assert_can_deactivate` 的呼叫移到 `target_user.is_active = ...`
        **之後**必須讓本測試紅燈——那個突變之下回應仍是 409，但帳號**已經被
        停用了**，而「寫入之後才檢查等於沒有檢查」。

        同時驗 allow 側：補上第二位管理者之後停用成功（200），且
        `is_active` 真的變成 False——沒有這一半，一個「永遠回 409」的實作
        也會通過。
        """
        res = self.client_as(self.root).put(
            f"/api/auth/{self.alice.id}/active", json={"is_active": False}
        )
        self.assertEqual(res.status_code, 409)
        self.db.refresh(self.alice)
        self.assertTrue(
            self.alice.is_active,
            "守門命中卻已經寫入 is_active——檢查被移到寫入之後了（BR6.1）",
        )

        self.facade.invite_member(
            mint_principal(self.alice),
            project_id=self.project.id,
            user_id=self.bob.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        ok = self.client_as(self.root).put(
            f"/api/auth/{self.alice.id}/active", json={"is_active": False}
        )
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(ok.json()["is_active"])
        self.db.refresh(self.alice)
        self.assertFalse(self.alice.is_active)


class CreateProjectWithOwnerTest(MembershipEndpointTestBase):
    def test_E7_creating_a_project_always_yields_a_member_row(self):
        """`E7`／`BR3.1`／`NFR12.18`／`[ND1]`=A：**不存在零成員的專案。**

        兩半都要：
          (a) 成功路徑 ⇒ 必然存在一列 `(project_id, 建立者, project_admin)`；
          (b) **部分失敗不得留下零成員專案**——這是 `NFR12.18` 的二元判準，
              也是 `OPEN-ND19-5` 的全部理由。以 patch 讓成員寫入失敗，
              然後斷言**連專案列都沒有**（同一交易一起回滾）。
              若 `U7` 的 `create_project` 仍自己 commit（即沒有走
              `create_project_nocommit` 那條路），(b) 會紅：專案會留下來。
        """
        client = self.client_as(self.alice)
        created = client.post("/api/hierarchy/projects", json={"name": "Fresh"})
        self.assertEqual(created.status_code, 201)
        new_id = created.json()["id"]
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=new_id, user_id=self.alice.id
            ),
            ProjectRole.PROJECT_ADMIN.value,
        )
        # 系統寫入的那一列沒有邀請者（`entities.md` 逐字）。
        row = (
            self.db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == new_id,
                ProjectMember.user_id == self.alice.id,
            )
            .one()
        )
        self.assertIsNone(row.invited_by)

        # (b) 部分失敗
        before = {p.id for p in self.db.query(Project).all()}
        with patch.object(
            membership_service, "add_member", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                client.post("/api/hierarchy/projects", json={"name": "Doomed"})
        after = {p.id for p in self.db.query(Project).all()}
        self.assertEqual(
            after,
            before,
            "成員寫入失敗後專案列仍留著——兩個寫入不在同一交易內（NFR12.18）",
        )
        self.assertEqual(
            self.db.query(Project).filter(Project.name == "Doomed").count(), 0
        )

        # 零成員專案數必須為 0（`monitoring-design.md §二` 的第 5 列判準）。
        orphans = (
            self.db.query(Project)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .filter(ProjectMember.id.is_(None))
            .count()
        )
        self.assertEqual(orphans, 0)


class MergeBlockerEndpointTest(MembershipEndpointTestBase):
    """`E8`–`E10`：合併前必修第 4、10、16 項的 HTTP 面。"""

    def _member(self, project, user, role=ProjectRole.MEMBER, when=None):
        self.db.add(
            ProjectMember(
                project_id=project.id,
                user_id=user.id,
                role=role.value,
                joined_at=when or datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        self.db.commit()

    def _rows(self, project, user):
        return (
            self.db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
            .count()
        )

    def test_E8_inviting_a_deactivated_or_pending_account_is_refused(self):
        """
        @purpose 停用或待核准的帳號不得被邀請為成員（合併前必修第 4 項）：加了他只會留下一列用不到、之後還可能被改選選中的成員資格
        @given alice 是專案 P 的 project_admin；ivy 是 Project_Editor 但已停用；pat 是 Project_Editor 但授權狀態為 pending
        @step alice 以 POST /api/membership/projects/{P}/members 邀請 ivy | 422，訊息含「帳號已停用」，P 無 ivy 的成員列
        @step alice 以同一端點邀請 pat | 422，訊息含「尚未通過授權核准」，P 無 pat 的成員列
        @step alice 邀請啟用且已核准的 erin（同角色） | 201（對照組：拒絕是因為帳號狀態而不是角色）
        @pass 兩種帳號狀態皆被拒且不留成員列，對照組成功
        @story US12.5
        @api POST /api/membership/projects/{project_id}/members
        """
        ivy = make_user(self.db, username="ivy", role=ROLE_K3_EDIT, is_active=False)
        pat = make_user(
            self.db, username="pat", role=ROLE_K3_EDIT, authorization_status="pending"
        )
        erin = make_user(self.db, username="erin", role=ROLE_K3_EDIT)
        client = self.client_as(self.alice)
        for user, phrase in ((ivy, "帳號已停用"), (pat, "尚未通過授權核准")):
            with self.subTest(user=user.username):
                res = client.post(
                    self.members_url(), json={"user_id": user.id, "role": "member"}
                )
                self.assertEqual(res.status_code, 422)
                self.assertIn(phrase, res.json()["detail"])
                self.assertEqual(self._rows(self.project, user), 0)
        ok = client.post(self.members_url(), json={"user_id": erin.id, "role": "member"})
        self.assertEqual(ok.status_code, 201)

    def test_E9_failed_reselection_returns_500_and_a_resend_completes_it(self):
        """
        @purpose 停用後的自動改選有專案失敗時必須回報（不再回 200 只記 log），且重送同一請求能補跑而不重複已完成的專案（合併前必修第 10 項）
        @given alice 是 P 與 R 兩個專案的唯一 project_admin；erin 是 P 的合格成員、frank 是 R 的合格成員；R 的改選被注入失敗
        @step root 以 PUT /api/auth/{alice}/active 送 is_active=false | 500，本體欄位為 detail／user_id／failed_project_ids，failed_project_ids == [R]
        @step 讀 alice 與兩個專案 | alice 已停用；erin 已是 P 的 project_admin；frank 仍是 R 的 member
        @step 移除注入的失敗，重送同一請求 | 200
        @step 讀事件與角色 | frank 成為 R 的 project_admin；P 的 auto_reselection 事件仍只有 1 筆
        @pass 失敗被回報、重送補跑成功且不重複
        @story US12.4
        @api PUT /api/auth/{user_id}/active
        """
        erin = make_user(self.db, username="erin", role=ROLE_K3_EDIT)
        frank = make_user(self.db, username="frank", role=ROLE_K3_EDIT)
        self._member(self.project, erin)
        r = self.facade.create_project_with_owner(mint_principal(self.alice), name="R")
        self._member(r, frank)

        original = membership_service.reselect_for_project

        def flaky(db, *, project_id, deactivated_user_id):
            if project_id == r.id:
                raise RuntimeError("injected reselection failure")
            return original(
                db, project_id=project_id, deactivated_user_id=deactivated_user_id
            )

        url = f"/api/auth/{self.alice.id}/active"
        with patch.object(membership_service, "reselect_for_project", side_effect=flaky):
            res = self.client_as(self.root).put(url, json={"is_active": False})
        self.assertEqual(res.status_code, 500)
        body = res.json()
        self.assertEqual(set(body), {"detail", "user_id", "failed_project_ids"})
        self.assertEqual(body["failed_project_ids"], [r.id])
        self.assertEqual(body["user_id"], self.alice.id)
        self.db.refresh(self.alice)
        self.assertFalse(self.alice.is_active)
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=erin.id
            ),
            ProjectRole.PROJECT_ADMIN.value,
        )
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=r.id, user_id=frank.id
            ),
            ProjectRole.MEMBER.value,
        )

        retry = self.client_as(self.root).put(url, json={"is_active": False})
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=r.id, user_id=frank.id
            ),
            ProjectRole.PROJECT_ADMIN.value,
        )
        p_events = (
            self.db.query(ReselectionEvent)
            .filter(ReselectionEvent.project_id == self.project.id)
            .count()
        )
        self.assertEqual(p_events, 1, "重送時已完成的專案又改選了一次（BR4.3）")

    def test_E10_lock_timeout_becomes_503_on_member_and_deactivation_endpoints(self):
        """
        @purpose 取鎖逾時要回 503「請稍後再試」而不是 500，交易已回滾不留半套（合併前必修第 16 項）
        @given 取鎖函式被替換為一律拋 MembershipLockTimeout
        @step alice 以 POST /api/membership/projects/{P}/members 邀請 erin | 503，P 無 erin 的成員列
        @step alice 以 PATCH 改 bob 的角色、以 DELETE 移出 bob | 皆 503
        @step root 停用 alice（P 有合格接手人 erin 已在 P） | 503，本體 failed_project_ids == [P]，alice 已停用
        @pass 三個成員端點與停用端點都回 503
        @story US12.3
        @api POST /api/membership/projects/{project_id}/members
        @api PATCH /api/membership/projects/{project_id}/members/{user_id}
        @api DELETE /api/membership/projects/{project_id}/members/{user_id}
        @api PUT /api/auth/{user_id}/active
        """
        erin = make_user(self.db, username="erin", role=ROLE_K3_EDIT)
        self._member(self.project, self.bob)

        def timeout(db, *, project_id):
            raise MembershipLockTimeout(project_id=project_id)

        client = self.client_as(self.alice)
        with patch.object(membership_service, "lock_project", side_effect=timeout):
            res = client.post(
                self.members_url(), json={"user_id": erin.id, "role": "member"}
            )
            self.assertEqual(res.status_code, 503)
            self.assertEqual(self._rows(self.project, erin), 0)
            self.assertEqual(
                client.patch(
                    f"{self.members_url()}/{self.bob.id}", json={"role": "project_admin"}
                ).status_code,
                503,
            )
            self.assertEqual(
                client.delete(f"{self.members_url()}/{self.bob.id}").status_code, 503
            )

        self._member(self.project, erin)
        with patch.object(membership_service, "lock_project", side_effect=timeout):
            res = self.client_as(self.root).put(
                f"/api/auth/{self.alice.id}/active", json={"is_active": False}
            )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["failed_project_ids"], [self.project.id])
        self.db.refresh(self.alice)
        self.assertFalse(self.alice.is_active)


class ProjectExistenceNotLeakedTest(MembershipEndpointTestBase):
    """合併前必修第 14 項（`[PP-MB14]`=A，2026-10-24）：成員端點不以 403／404 洩漏專案存在。

    「不存在的專案」與「存在但非成員」→ 同一個不含 id 的 404（比照
    `test_project_visibility_endpoints.test_E15`）；成員之內的角色不足與缺全域權限維持 403。
    """

    def _requests(self, project_id):
        """四個成員端點各一個請求（方法, URL, JSON 本體）。"""
        base = self.members_url(project_id)
        return [
            ("GET", base, None),
            ("POST", base, {"user_id": self.carol.id, "role": "member"}),
            ("DELETE", f"{base}/{self.alice.id}", None),
            ("PATCH", f"{base}/{self.alice.id}", {"role": "member"}),
        ]

    @staticmethod
    def _send(client, method, url, body):
        if body is None:
            return client.request(method, url)
        return client.request(method, url, json=body)

    def test_E11_missing_and_non_member_project_are_byte_identical(self):
        """N1：四端點 ×「不存在 vs 存在但非成員」→ status＋body 逐位元相同、不含專案 id。

        @purpose 具 `K3` 的人無法以成員端點的回應分辨某個專案編號是否存在（M14-1／M14-2）。
        @given   bob 具 `K3.edit`（`Project_Architect`）但不是專案 P 的成員；另取一個從未存在的 id。
        @step    以 bob 對兩個 id 分別打 GET／POST／DELETE／PATCH 成員端點。
        @pass    每個端點兩側皆 404、`response.content` 相等、本體為 `{"detail": "查不到專案"}`，
                 且不含任一 id 的字串；成員列數不變。
        @story   AC12.5.2
        @api     GET /api/membership/projects/{project_id}/members
        @api     POST /api/membership/projects/{project_id}/members
        @api     DELETE /api/membership/projects/{project_id}/members/{user_id}
        @api     PATCH /api/membership/projects/{project_id}/members/{user_id}
        """
        missing_id = self.project.id + 1000
        self.assertIsNone(self.db.get(Project, missing_id))
        rows_before = self.db.query(ProjectMember).count()
        client = self.client_as(self.bob)
        for (method, missing_url, body), (_, existing_url, _) in zip(
            self._requests(missing_id), self._requests(self.project.id)
        ):
            with self.subTest(method=method):
                missing = self._send(client, method, missing_url, body)
                invisible = self._send(client, method, existing_url, body)
                self.assertEqual(missing.status_code, 404, missing.text)
                self.assertEqual(invisible.status_code, missing.status_code, invisible.text)
                self.assertEqual(invisible.content, missing.content)
                self.assertEqual(invisible.json(), {"detail": "查不到專案"})
                for pid in (missing_id, self.project.id):
                    self.assertNotIn(str(pid).encode(), invisible.content)
        self.assertEqual(self.db.query(ProjectMember).count(), rows_before)

    def test_E12_in_membership_shortfall_and_missing_global_permission_stay_403(self):
        """N2：成員之內的角色不足 → 403；缺 `K3` → 403（且不依專案是否存在而變）。

        @purpose 改 404 只針對「非成員」；已是成員的人知道專案存在，角色不足仍回 403，
                 缺全域權限的 403 對存在與不存在的專案逐位元相同。
        @given   bob 以 `member` 身分加入 P（具 `K3.edit` 但不是 `project_admin`）；dave 無 `K3`。
        @step    bob 對 P 讀清單與三個寫入；dave 對 P 與不存在的 id 讀清單。
        @pass    bob 讀 200、三個寫入 403；dave 兩側皆 403 且 `content` 相等。
        @story   AC12.5.2
        @api     GET /api/membership/projects/{project_id}/members
        @api     POST /api/membership/projects/{project_id}/members
        @api     DELETE /api/membership/projects/{project_id}/members/{user_id}
        @api     PATCH /api/membership/projects/{project_id}/members/{user_id}
        """
        self.facade.invite_member(
            mint_principal(self.alice),
            project_id=self.project.id,
            user_id=self.bob.id,
            role=ProjectRole.MEMBER.value,
        )
        bob = self.client_as(self.bob)
        for method, url, body in self._requests(self.project.id):
            with self.subTest(member_method=method):
                response = self._send(bob, method, url, body)
                self.assertEqual(response.status_code, 200 if method == "GET" else 403,
                                 response.text)

        dave = self.client_as(self.dave)
        existing = dave.get(self.members_url())
        missing = dave.get(self.members_url(self.project.id + 1000))
        self.assertEqual(existing.status_code, 403)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(existing.content, missing.content)

    def test_E13_non_member_denial_is_still_logged(self):
        """非成員改回 404 之後，拒絕 log 照記（稽核不因對外改 404 而消失）。

        @purpose 對外改 404 不得順手拿掉 `membership.denied` 那一行。
        @given   bob 具 `K3.view` 但不是 P 的成員。
        @step    以 bob 讀 P 的成員清單。
        @pass    回 404，且 `cloud360.membership` 記一行含 bob 的 user_id 與 P 的 project_id 的 WARNING。
        @story   AC12.5.2
        @api     GET /api/membership/projects/{project_id}/members
        """
        with self.assertLogs("cloud360.membership", level="WARNING") as logs:
            response = self.client_as(self.bob).get(self.members_url())
        self.assertEqual(response.status_code, 404)
        messages = [record.getMessage() for record in logs.records]
        expected = (
            f"{membership_service.EVENT_DENIED} story_id={membership_service.MEMBERSHIP_STORY_ID} "
            f"action=list_members project_id={self.project.id} principal={self.bob.id}"
        )
        self.assertIn(expected, messages)


if __name__ == "__main__":
    unittest.main()
