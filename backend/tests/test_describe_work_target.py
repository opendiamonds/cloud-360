"""`U14 entry-page-ui` 的後端名稱查詢、可見性批次與語句數測試（ADR-0022）。

四組：

- `VisibilityBatchTest`（3 案）：`MembershipFacade.project_visibility` 的批次形狀
  （ADR-0022 D-5）——同一實例、同一位使用者只查一次可見集合。
- `DescribeWorkTargetTest`（12 案，`code-generation-plan.md` §四之一 (a)–(j)）：
  `HierarchyFacade.describe_work_target` 對各身分的名稱結果（ADR-0022 D-2）。
- `StatementCountTest`（5 案）：每組 ≤ 5、只有圖 2、與擁有專案數無關、`list_projects`
  固定 3、`_names_for` 快照 ≤ 15 且只開一個 session（nfr-requirements `R-02`）。
- `CatalogStatementCountTest`（2 案）：`BrainGateway._build_catalog` 的語句數 3 ＋ 3N
  與截斷時的 3（nfr-design `R-02` 的落點與目錄總數的如實讀法）。

**授權不 mock**：走真實的 `HierarchyFacade`、`MembershipFacade`、`membership_service`
與 `user_can`，只以 in-memory SQLite 取代資料庫。

`@api` 在本檔**刻意缺席**：受測對象（facade、閘道內部方法）沒有 HTTP 端點，依
`project.md` 的既有更正「受測對象既無端點也無 UI 時寧可缺、不得捏造」。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import types
import unittest

from sqlalchemy import event

from models import Project, ProjectMember, RolePermission, System, UserDiagram
import services.hierarchy_service as hierarchy_service
from services.hierarchy_facade import (
    HierarchyFacade,
    HierarchyForbidden,
    mint_principal,
)
from services.membership_facade import MembershipFacade
from tests.helpers import close_session, make_session, make_user

ROLE_K2_EDIT = "Project_Editor"     # K2 view＋edit
ROLE_K2_REVOKED = "Developer"       # 本檔把它的 K2 列改為全否，模擬「K2 view 撤銷」

NO_NAMES = {"projectName": None, "systemName": None, "diagramName": None}


class NamesWorld:
    """`unit-test-instructions.md` §六 的身分構造（ORM 直接構造，比照 `U23`）。

    | 代號 | 使用者 | 專案／系統／圖 | 構造 |
    |---|---|---|---|
    | (a) | `owner` | `pa`／`sa`／`da` | `create_project_with_owner`（建立者有 `project_admin` 列） |
    | (b) | `removed` | `pb`／`sb`／`db_` | 建立 → `admin2` 寫 `project_admin` → 刪除建立者的成員列 |
    | (c) | `zero_owner` | `pc`／`sc`／`dc` | ORM 直接建 `Project`、不寫成員列 |
    | (d) | `member` | `pa` 的 `member` 列、自己的圖 `dd` 掛在 `sa` 下 | — |
    | (e) | `owner` | 孤兒圖 `de`（`system_id=None`） | — |
    | (j) | `owner` | 孤兒圖 `dj`，標題 `""` | — |
    | (f) | `revoked` | — | `Developer` 的 `K2` 列改為全否 |
    """

    def __init__(self, db) -> None:
        self.db = db
        self.owner = make_user(db, username="owner", role=ROLE_K2_EDIT)
        self.removed = make_user(db, username="removed", role=ROLE_K2_EDIT)
        self.admin2 = make_user(db, username="admin2", role=ROLE_K2_EDIT)
        self.zero_owner = make_user(db, username="zero_owner", role=ROLE_K2_EDIT)
        self.member = make_user(db, username="member", role=ROLE_K2_EDIT)
        self.revoked = make_user(db, username="revoked", role=ROLE_K2_REVOKED)

        facade = MembershipFacade(db)
        # (a)
        self.pa = facade.create_project_with_owner(mint_principal(self.owner), name="e2e-u14-專案A")
        self.sa = self.add_system(self.pa, "e2e-u14-系統A")
        self.da = self.add_diagram(self.owner, "e2e-u14-圖A", self.sa)
        # (b)
        self.pb = facade.create_project_with_owner(mint_principal(self.removed), name="e2e-u14-前專案B")
        self.sb = self.add_system(self.pb, "e2e-u14-系統B")
        self.db_ = self.add_diagram(self.removed, "e2e-u14-自己的圖B", self.sb)
        self.add_member(self.pb, self.admin2, "project_admin")
        self.remove_member(self.pb, self.removed)
        # (c)
        self.pc = Project(name="e2e-u14-專案C", owner_user_id=self.zero_owner.id, is_default=False)
        db.add(self.pc)
        db.commit()
        db.refresh(self.pc)
        self.sc = self.add_system(self.pc, "e2e-u14-系統C")
        self.dc = self.add_diagram(self.zero_owner, "e2e-u14-圖C", self.sc)
        # (d)
        self.add_member(self.pa, self.member, "member")
        self.dd = self.add_diagram(self.member, "e2e-u14-成員的圖D", self.sa)
        # (e)／(j)
        self.de = self.add_diagram(self.owner, "e2e-u14-孤兒圖E", None)
        self.dj = self.add_diagram(self.owner, "", None)
        # (f)
        row = (
            db.query(RolePermission)
            .filter(RolePermission.role == ROLE_K2_REVOKED, RolePermission.story_id == "K2")
            .one()
        )
        row.can_view = row.can_edit = row.can_review = False
        db.commit()

    def add_member(self, project, user, role: str) -> None:
        self.db.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
        self.db.commit()

    def remove_member(self, project, user) -> None:
        self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
        ).delete()
        self.db.commit()

    def add_system(self, project, name: str) -> System:
        system = System(project_id=project.id, name=name, is_default=False)
        self.db.add(system)
        self.db.commit()
        self.db.refresh(system)
        return system

    def add_diagram(self, user, title: str, system) -> UserDiagram:
        diagram = UserDiagram(
            user_id=user.id,
            title=title,
            xml_data="<mxGraphModel/>",
            system_id=None if system is None else system.id,
        )
        self.db.add(diagram)
        self.db.commit()
        self.db.refresh(diagram)
        return diagram

    def add_owned_project(self, user, name: str, *, with_member_row: bool = True) -> Project:
        if with_member_row:
            return MembershipFacade(self.db).create_project_with_owner(mint_principal(user), name=name)
        project = Project(name=name, owner_user_id=user.id, is_default=False)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def never_existed_project_id(self) -> int:
        return max(p.id for p in self.db.query(Project).all()) + 1000


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.w = NamesWorld(self.db)
        self.engine = self.db._test_engine  # type: ignore[attr-defined]
        self.count = 0

        def _on_execute(conn, cursor, statement, parameters, context, executemany):
            self.count += 1

        self._listener = _on_execute
        event.listen(self.engine, "before_cursor_execute", self._listener)

    def tearDown(self) -> None:
        # 清除端（`EPN-23`）：監聽器一律卸除，不讓計數器跨案存活。
        event.remove(self.engine, "before_cursor_execute", self._listener)
        close_session(self.db)

    def describe(self, user, **ids) -> dict:
        """以真實的 facade 與真實的可見性閉包呼叫（每次新實例：比照閘道每組新 session）。"""
        principal = mint_principal(user)
        vis = MembershipFacade(self.db)
        return HierarchyFacade(self.db).describe_work_target(
            principal, project_visible=vis.project_visibility(principal), **ids
        )


class VisibilityBatchTest(_Base):
    """ADR-0022 D-5：可見性閉包的批次形狀（nfr-design `R-02`）。"""

    def test_three_closures_ten_pids_issue_exactly_one_visibility_query(self):
        """
        @purpose 同一個 MembershipFacade 實例上，同一位使用者的可見性判定只能查一次可見集合；
                 退回逐專案一條 SQL 時目錄與 list_projects 的語句數會隨專案數線性成長（ND R-02）。
        @given 一個 MembershipFacade 實例；使用者 owner；10 個專案 id（含不存在者）
        @step 在同一實例上呼叫 project_visibility(principal) 三次，取得三個閉包（未判定前） | 0 條 SQL
        @step 三個閉包合計判定 10 個專案 id | 可見性 SQL 恰 1 條；pa 判為可見、他人專案判為不可見
        @pass 判定 10 個 id 只發出 1 條 SQL，且結果正確
        @story US2.1
        """
        principal = mint_principal(self.w.owner)
        facade = MembershipFacade(self.db)
        pids = [self.w.pa.id, self.w.pb.id, self.w.pc.id] + [9000 + i for i in range(7)]
        self.count = 0
        closures = [facade.project_visibility(principal) for _ in range(3)]
        self.assertEqual(self.count, 0)
        results = [closures[i % 3](pid) for i, pid in enumerate(pids)]
        self.assertEqual(self.count, 1)
        self.assertEqual(results[0], True)
        self.assertEqual(results[1:], [False] * 9)

    def test_two_users_on_one_instance_each_one_query_without_cross_pollution(self):
        """
        @purpose 暫存以使用者為鍵：同一實例上兩位使用者各自查一次，結果互不污染；
                 若暫存不分使用者，第二位會沿用第一位的可見集合（錯的人看到專案）。
        @given 一個 MembershipFacade 實例；owner 可見 pa；admin2 可見 pb（他是 pb 的 project_admin）
        @step owner 的閉包判定 pa、pb | 1 條 SQL；pa 真、pb 假
        @step admin2 的閉包判定 pa、pb | 再 1 條 SQL（合計 2）；pa 假、pb 真
        @step owner 的閉包再判定 pa | 不再發 SQL（合計仍 2）；結果仍為真
        @pass 兩位使用者各 1 條 SQL、結果與各自的可見集合一致
        @story US2.1
        """
        facade = MembershipFacade(self.db)
        owner_vis = facade.project_visibility(mint_principal(self.w.owner))
        admin_vis = facade.project_visibility(mint_principal(self.w.admin2))
        pa, pb = self.w.pa.id, self.w.pb.id
        self.count = 0
        self.assertTrue(owner_vis(pa))
        self.assertFalse(owner_vis(pb))
        self.assertEqual(self.count, 1)
        self.assertFalse(admin_vis(pa))
        self.assertTrue(admin_vis(pb))
        self.assertEqual(self.count, 2)
        self.assertTrue(owner_vis(pa))
        self.assertEqual(self.count, 2)

    def test_non_empty_visible_set_without_target_is_false(self):
        """
        @purpose 閉包必須判定「目標 pid 是否在集合內」，不是「是否有任何可見專案」。
                 V1 突變（回 bool(ids)）會讓另一專案的成員被當成目標專案的可見者。
        @given 被移出的建立者 removed：pb 不可見；另讓他成為 pa 的成員（可見集合非空）
        @step 以 removed 的閉包判定 pb | False
        @step 判定 pa | True
        @pass 可見集合非空但不含目標時回 False
        @story US2.1
        """
        self.w.add_member(self.w.pa, self.w.removed, "member")
        vis = MembershipFacade(self.db).project_visibility(mint_principal(self.w.removed))
        self.assertFalse(vis(self.w.pb.id))
        self.assertTrue(vis(self.w.pa.id))


class DescribeWorkTargetTest(_Base):
    """ADR-0022 D-2：`describe_work_target` 對各身分的名稱（§四之一 (a)–(j)）。"""

    def test_a_owner_and_member_gets_three_names(self):
        """
        @purpose 擁有者且為成員的完整三元組必須回三個名稱；否則脈絡列對一般使用者也顯示不出名稱（EPN-11）。
        @given owner 擁有 pa／sa／da 且有 project_admin 成員列
        @step 以完整三元組呼叫 facade 的 describe_work_target | 三名稱與資料庫一致
        @step 以同一三元組呼叫服務層 describe_work_target | names 相同、project_ids＝{pa}、explicit 為真
        @pass facade 與服務層皆回三個名稱
        @story US1.1
        """
        w = self.w
        got = self.describe(w.owner, project_id=w.pa.id, system_id=w.sa.id, diagram_id=w.da.id)
        expect = {"projectName": "e2e-u14-專案A", "systemName": "e2e-u14-系統A", "diagramName": "e2e-u14-圖A"}
        self.assertEqual(got, expect)
        found = hierarchy_service.describe_work_target(
            self.db, owner_user_id=w.owner.id, project_id=w.pa.id, system_id=w.sa.id, diagram_id=w.da.id
        )
        self.assertEqual(found.names, expect)
        self.assertEqual(found.project_ids, frozenset({w.pa.id}))
        self.assertTrue(found.explicit)

    def test_b_removed_creator_gets_all_null_including_own_diagram(self):
        """
        @purpose 被移出的建立者（owner_user_id 仍是他）不得經大腦取得前專案的任何名稱，含他自己的圖名
                 （functional-design R-01 使用者裁決；W1／W6 突變）。
        @given removed 建立 pb 後被 admin2 移出；sb、自己的圖 db_ 皆在 pb 下
        @step 以完整三元組呼叫 describe_work_target | 三名稱皆為 None，不拋例外
        @pass 三名稱皆 null
        @story US2.1
        """
        w = self.w
        got = self.describe(w.removed, project_id=w.pb.id, system_id=w.sb.id, diagram_id=w.db_.id)
        self.assertEqual(got, NO_NAMES)

    def test_b2_removed_creator_who_is_member_elsewhere_still_all_null(self):
        """
        @purpose 被移出的建立者另是第二專案的成員時，仍不得取得前專案的名稱；可見性判定若退化成
                 「是否有任何可見專案」（V1 突變）本案即紅（nfr-design R-03）。
        @given 同 (b)；另讓 removed 成為 pa 的成員（可見集合非空）
        @step 以 pb 的完整三元組呼叫 | 三名稱皆為 None
        @pass 三名稱皆 null
        @story US2.1
        """
        w = self.w
        w.add_member(w.pa, w.removed, "member")
        got = self.describe(w.removed, project_id=w.pb.id, system_id=w.sb.id, diagram_id=w.db_.id)
        self.assertEqual(got, NO_NAMES)

    def test_c_zero_member_creator_gets_three_names(self):
        """
        @purpose 零成員列專案的建立者可見該專案（U23 擁有者那一半），必須照常回三個名稱（雙向對照）。
        @given zero_owner 擁有 pc（無任何成員列）與 sc、dc
        @step 以完整三元組呼叫 | 三名稱與資料庫一致
        @pass 回三名稱
        @story US1.1
        """
        w = self.w
        got = self.describe(w.zero_owner, project_id=w.pc.id, system_id=w.sc.id, diagram_id=w.dc.id)
        self.assertEqual(
            got, {"projectName": "e2e-u14-專案C", "systemName": "e2e-u14-系統C", "diagramName": "e2e-u14-圖C"}
        )

    def test_d_non_owner_member_gets_only_own_diagram_name(self):
        """
        @purpose 非擁有者的成員：專案與系統不屬他（擁有者範圍），名稱為 null；圖是他自己的，圖名照常
                 （OPEN-EP14-9 的現況，不擴大可見範圍）。
        @given member 是 pa 的 member；他自己的圖 dd 掛在 sa 下
        @step 以 (pa, sa, dd) 呼叫 | projectName、systemName 為 None；diagramName 為 dd 的標題
        @pass 只有圖名有值
        @story US2.1
        """
        w = self.w
        got = self.describe(w.member, project_id=w.pa.id, system_id=w.sa.id, diagram_id=w.dd.id)
        self.assertEqual(got, {"projectName": None, "systemName": None, "diagramName": "e2e-u14-成員的圖D"})

    def test_e_own_orphan_diagram_gets_only_diagram_name(self):
        """
        @purpose 孤兒圖（system_id 為 null）的名稱必須查得到；既有列舉組合查不到它（[EP2] 修訂 1）。
        @given owner 的孤兒圖 de
        @step 只以 diagram_id 呼叫 facade | 只有 diagramName 有值
        @step 以服務層呼叫 | project_ids 為空、explicit 為假
        @pass 只有圖名
        @story US1.1
        """
        w = self.w
        got = self.describe(w.owner, diagram_id=w.de.id)
        self.assertEqual(got, {"projectName": None, "systemName": None, "diagramName": "e2e-u14-孤兒圖E"})
        found = hierarchy_service.describe_work_target(self.db, owner_user_id=w.owner.id, diagram_id=w.de.id)
        self.assertEqual(found.project_ids, frozenset())
        self.assertFalse(found.explicit)

    def test_e2_diagram_only_under_former_project_keeps_diagram_name(self):
        """
        @purpose 只有圖的三元組不推導上層、不判可見性：被移出者開自己掛在前專案下的圖，脈絡列只顯示圖名
                 （nfr-design R-01 使用者裁決；W3 突變）。
        @given removed 的圖 db_ 掛在 pb（對他不可見）的 sb 下
        @step 只以 diagram_id 呼叫 | 回 {None, None, "e2e-u14-自己的圖B"}
        @pass 三個名稱的實際值逐一相符
        @story US2.1
        """
        w = self.w
        got = self.describe(w.removed, diagram_id=w.db_.id)
        self.assertEqual(got, {"projectName": None, "systemName": None, "diagramName": "e2e-u14-自己的圖B"})

    def test_f_k2_view_revoked_raises_forbidden(self):
        """
        @purpose 授權判定先於任何讀取：K2 view 撤銷時 facade 必須拋 HierarchyForbidden，且不在本方法內
                 被吞掉（閘道層再決定不記 log，見 handshake 測試）。
        @given revoked 的角色 Developer 的 K2 列為全否
        @step 呼叫 describe_work_target | 拋 HierarchyForbidden
        @pass 拒絕以例外呈現
        @story US2.1
        """
        w = self.w
        with self.assertRaises(HierarchyForbidden):
            self.describe(w.revoked, project_id=w.pa.id)

    def test_g_nonexistent_project_gives_null_name(self):
        """
        @purpose 不存在的專案 id 不得拋查不到，只回 null（與不可見逐位元相同，EPN-12）。
        @given 從未存在的專案 id
        @step 以 facade 呼叫 | 三名稱皆 None、不拋例外
        @step 以服務層呼叫 | names 皆 None、project_ids 為空、explicit 為真
        @pass 回 null 而非例外
        @story US2.1
        """
        w = self.w
        pid = w.never_existed_project_id()
        self.assertEqual(self.describe(w.owner, project_id=pid), NO_NAMES)
        found = hierarchy_service.describe_work_target(self.db, owner_user_id=w.owner.id, project_id=pid)
        self.assertEqual(found.names, NO_NAMES)
        self.assertEqual(found.project_ids, frozenset())
        self.assertTrue(found.explicit)

    def test_h_missing_project_visible_is_type_error(self):
        """
        @purpose project_visible 必填、無預設：漏傳必須在呼叫當下 TypeError（fail-closed，EPN-11b；W2 突變）。
        @given owner 與 pa
        @step 不帶 project_visible 呼叫 describe_work_target | 拋 TypeError
        @pass 漏傳即失敗
        @story US2.1
        """
        with self.assertRaises(TypeError):
            HierarchyFacade(self.db).describe_work_target(mint_principal(self.w.owner), project_id=self.w.pa.id)

    def test_i_system_under_another_invisible_project_gives_all_null(self):
        """
        @purpose 三元組中出現的每個相異所屬專案都要判可見性：project_id 可見而系統屬另一個不可見專案時，
                 三名稱皆 null（nfr-design R-06；W4 突變——只判 project_id 參數）。
        @given removed 另擁有可見的專案 pi；sb 屬他不可見的 pb
        @step 以 (pi, sb) 呼叫 | 三名稱皆 None
        @step 對照：只以 (pi) 呼叫 | projectName 有值
        @pass 不可見的所屬專案使三名稱皆 null
        @story US2.1
        """
        w = self.w
        pi = w.add_owned_project(w.removed, "e2e-u14-可見專案I")
        self.assertEqual(self.describe(w.removed, project_id=pi.id, system_id=w.sb.id), NO_NAMES)
        self.assertEqual(
            self.describe(w.removed, project_id=pi.id),
            {"projectName": "e2e-u14-可見專案I", "systemName": None, "diagramName": None},
        )

    def test_j_empty_title_is_kept_as_empty_string(self):
        """
        @purpose 圖標題為空字串時原樣保留，不轉 null；否則前端把「（未命名）」誤顯示為「（無法顯示名稱）」
                 （functional-design R-06 後半）。
        @given owner 的孤兒圖 dj，標題 ""
        @step 只以 diagram_id 呼叫 | diagramName == ""（不是 None）
        @pass 空字串原樣
        @story US1.1
        """
        got = self.describe(self.w.owner, diagram_id=self.w.dj.id)
        self.assertEqual(got["diagramName"], "")
        self.assertIsNotNone(got["diagramName"])


class StatementCountTest(_Base):
    """nfr-requirements `R-02`：每組 ≤ 5、快照 ≤ 15，且與擁有專案數無關。

    每案先暖身一次（讓 `role_permissions` 等路徑一致），再以**新的** facade 實例量測
    （可見集合暫存綁實例，同一實例暖身會把可見性那一條吃掉）。
    """

    def measure(self, fn) -> int:
        fn()
        self.count = 0
        fn()
        return self.count

    def full_triple(self):
        w = self.w
        ids = dict(project_id=w.pa.id, system_id=w.sa.id, diagram_id=w.da.id)
        user = w.owner
        return lambda: self.describe(user, **ids)

    def test_full_triple_is_exactly_five_statements(self):
        """
        @purpose 完整三元組的名稱查詢上界 5（授權 1、三層各 1、可見性 1）；系統層若沿用兩條的
                 assert_system_owned_by 即變 6（W5 突變）。
        @given owner 的 (pa, sa, da)
        @step 暖身一次後量測一次 describe_work_target | 恰 5 條 SQL
        @pass 語句數恰為 5
        @story US2.1
        """
        self.w.pa.id, self.w.sa.id, self.w.da.id  # 預先載入，排除測試自身的 refresh
        self.assertEqual(self.measure(self.full_triple()), 5)

    def test_diagram_only_is_two_statements(self):
        """
        @purpose 只有圖的路徑不判可見性：授權 1 ＋ 圖層 1 ＝ 2（可見集合不查）。
        @given owner 的孤兒圖 de
        @step 暖身後量測 | 恰 2 條
        @pass 語句數恰為 2
        @story US2.1
        """
        user, did = self.w.owner, self.w.de.id
        self.assertEqual(self.measure(lambda: self.describe(user, diagram_id=did)), 2)

    def test_full_triple_same_count_with_one_and_fifty_projects(self):
        """
        @purpose 名稱查詢的語句數與擁有專案數無關（1 個與 50 個相同）；逐專案判可見性會隨 N 成長。
        @given owner 先擁有 1 個專案；再補到 50 個（皆有成員列）
        @step 量測完整三元組 | 記為 c1
        @step 補足 49 個專案後再量測 | 與 c1 相同（且為 5）
        @pass 兩次語句數相同
        @story US2.1
        """
        fn = self.full_triple()
        c1 = self.measure(fn)
        for i in range(49):
            self.w.add_owned_project(self.w.owner, f"e2e-u14-多專案-{i}")
        self.w.pa.id, self.w.sa.id, self.w.da.id
        c50 = self.measure(fn)
        self.assertEqual(c1, c50)
        self.assertEqual(c50, 5)

    def test_list_projects_is_three_statements_for_one_and_fifty_projects(self):
        """
        @purpose list_projects 的語句數固定 3（授權、列舉、可見集合），與擁有專案數無關（ND R-02；V2 突變）。
        @given owner 擁有 1 個專案；再補到 50 個
        @step 以新實例量測 list_projects | 恰 3 條，回傳只含可見專案
        @step 補足 49 個專案後再量測 | 仍恰 3 條
        @pass 兩次皆 3 條
        @story US2.1
        """
        user = self.w.owner

        def run():
            principal = mint_principal(user)
            vis = MembershipFacade(self.db)
            return HierarchyFacade(self.db).list_projects(
                principal, project_visible=vis.project_visibility(principal)
            )

        self.assertEqual(self.measure(run), 3)
        for i in range(49):
            self.w.add_owned_project(self.w.owner, f"e2e-u14-多專案-{i}")
        self.assertEqual(self.measure(run), 3)
        self.assertEqual(len(run()), 50)


    def test_names_for_snapshot_is_at_most_fifteen_with_one_session(self):
        """
        @purpose 快照三組名稱的總語句數 ≤ 15（每組 ≤ 5，含授權），且整批只開一個 DB session（EPN-06；G3 突變）。
        @given 真實 BrainGateway._names_for、真實 HierarchyFacade／MembershipFacade；owner 的三個不同三元組
        @step 以計數包裝的 session_factory 呼叫 _names_for | session_factory 恰呼叫 1 次
        @step 檢視語句數與結果 | ≤ 15 條；三組名稱與資料庫一致
        @pass 語句數在上界內且只開一個 session
        @story US2.1
        """
        from sqlalchemy.orm import sessionmaker

        from services import brain_gateway as G

        w = self.w
        triples = [(w.pa.id, w.sa.id, w.da.id), (w.pa.id, None, None), (None, None, w.de.id)]
        principal = mint_principal(w.owner)
        maker = sessionmaker(bind=self.engine)
        calls = []

        def counting_factory():
            calls.append(1)
            return maker()

        gw = G.BrainGateway(
            store=None,
            routers={},
            orchestrator=None,
            session_factory=counting_factory,
            membership_facade_factory=MembershipFacade,
        )
        try:
            conn = types.SimpleNamespace(conn_id="c-u14", principal=principal)
            self.count = 0
            out = asyncio.run(gw._names_for(conn, triples))
        finally:
            gw.shutdown()
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(self.count, 15)
        self.assertEqual(out[triples[0]]["systemName"], "e2e-u14-系統A")
        self.assertEqual(out[triples[1]]["projectName"], "e2e-u14-專案A")
        self.assertEqual(out[triples[2]]["diagramName"], "e2e-u14-孤兒圖E")


class CatalogStatementCountTest(_Base):
    """`BrainGateway._build_catalog` 的語句數（nfr-design `R-02` 的落點；`code-generation-plan.md` §七 第 1 點）。

    可見性成本為常數（＋1）；**總數仍隨 N 線性**——逐專案 `list_systems` 的授權、擁有者、列舉
    三條是 `U13` 既有成本（改前 2 ＋ 3N），本單元不改它的階，如實鎖住 3 ＋ 3N。
    """

    def build(self):
        from sqlalchemy.orm import sessionmaker

        from services import brain_gateway as G

        return G.BrainGateway(
            store=None,
            routers={},
            orchestrator=None,
            session_factory=sessionmaker(bind=self.engine),
            membership_facade_factory=MembershipFacade,
        )

    def measure(self, gw, principal, selected=None):
        gw._build_catalog(principal, selected)
        self.count = 0
        catalog = gw._build_catalog(principal, selected)
        return self.count, catalog

    def test_one_and_eight_projects_cost_three_plus_three_n(self):
        """
        @purpose 目錄的可見性成本為常數：N＝1 恰 6 條、N＝8 恰 27 條（3 ＋ 3N）；可見性若退回逐專案查詢會多出 N 條（V2）。
        @given 真實 facade；使用者 cat 擁有 N 個可見專案（皆有成員列）
        @step N＝1 時暖身後量測 _build_catalog | 恰 6 條、目錄含 1 個專案
        @step 補到 N＝8 後量測 | 恰 27 條、目錄含 8 個專案
        @pass 語句數為 3 ＋ 3N
        @story US1.1
        """
        cat = make_user(self.db, username="cat", role=ROLE_K2_EDIT)
        self.w.add_owned_project(cat, "e2e-u14-目錄-0")
        principal = mint_principal(cat)
        gw = self.build()
        try:
            n1, catalog = self.measure(gw, principal)
            self.assertEqual(len(catalog.projects), 1)
            self.assertEqual(n1, 3 + 3 * 1)
            for i in range(1, 8):
                self.w.add_owned_project(cat, f"e2e-u14-目錄-{i}")
            n8, catalog = self.measure(gw, principal)
            self.assertEqual(len(catalog.projects), 8)
            self.assertEqual(n8, 3 + 3 * 8)
        finally:
            gw.shutdown()

    def test_truncated_catalog_without_selection_is_three(self):
        """
        @purpose 專案數超過上限（51）且未選定專案時，目錄只列專案、不逐專案取系統：恰 3 條。
        @given 使用者 cat 擁有 51 個可見專案；未選定專案
        @step 暖身後量測 _build_catalog | 恰 3 條、truncated 為真、systems 為空
        @pass 截斷時語句數為常數 3
        @story US1.1
        """
        cat = make_user(self.db, username="cat", role=ROLE_K2_EDIT)
        for i in range(51):
            self.w.add_owned_project(cat, f"e2e-u14-目錄-{i}")
        principal = mint_principal(cat)
        gw = self.build()
        try:
            count, catalog = self.measure(gw, principal)
        finally:
            gw.shutdown()
        self.assertTrue(catalog.truncated)
        self.assertEqual(catalog.systems, ())
        self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
