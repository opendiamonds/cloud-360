"""`U19 membership-service` 的業務邏輯測試（`F1`–`F8`）。

對應 `unit-test-instructions.md §三` 的第二列（業務邏輯 ＋ 純函式 ＋ 稽核，**8** 個）。

**`F1` 是 blocking 的**：ADR-0006 的 property-based testing hard constraint 在
本單元是**適用且 blocking**，而不是前三個單元的 N/A——前三個是 DDL、沒有任何
函式，本單元有，且上游已經點名了哪一個（`unit-of-query.md` 不存在，點名處是
`unit-of-work.md:448` 與 `K-16` 的 `select_successor`）。

**被測的性質是排列不變性，不是「同一組輸入選出同一人」**——後者對純函式恆真，
是恆真斷言（`project.md` 記過那個形狀）。排列不變性會真的失敗：只以 `joined_at`
排序時，加入時間相同的兩位成員沒有穩定順序，`min()` 回傳的是**迭代順序中第一個
最小元素**，於是不同排列選出不同人。故生成策略刻意把 `joined_at` 抽自一個**只有
三個值的池**——時間戳撞在一起是這條性質唯一能失敗的情境，而從完整
`st.datetimes()` 範圍抽樣幾乎永遠撞不到。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from models import ProjectMember, ReselectionEvent
import services.hierarchy_service as hierarchy_service
import services.membership_service as membership_service
from services.hierarchy_facade import mint_principal
from services.membership_errors import (
    LastAdminGuard,
    MembershipForbidden,
    MembershipNotFound,
    MissingGlobalPermission,
)
from services.membership_facade import MembershipFacade
from services.membership_selection import select_successor
from services.membership_types import MemberSnapshot, ProjectRole
from tests.helpers import close_session, make_session, make_user

ROLE_ADMIN = "Project_Architect"   # K3 view+edit
ROLE_VIEW_ONLY = "Developer"       # K3 view=True、edit=False
ROLE_NO_K3 = "SRE"                 # K3 view=False、edit=False

# **只有三個值的時間池**：讓 `joined_at` 撞在一起成為常見而非罕見的情形。
# 沒有這個收斂，`F1` 的突變（tie-break 只按 joined_at）不會被抓到。
_TIME_POOL = [
    datetime(2026, 1, 1, tzinfo=timezone.utc),
    datetime(2026, 6, 1, tzinfo=timezone.utc),
    datetime(2026, 10, 1, tzinfo=timezone.utc),
]

_snapshot = st.builds(
    MemberSnapshot,
    user_id=st.integers(min_value=1, max_value=50),
    joined_at=st.sampled_from(_TIME_POOL),
    role=st.sampled_from([r.value for r in ProjectRole]),
)


@st.composite
def _members_and_a_permutation(draw):
    members = draw(
        st.lists(_snapshot, min_size=1, max_size=8, unique_by=lambda s: s.user_id)
    )
    return members, draw(st.permutations(members))


class SelectSuccessorPropertyTest(unittest.TestCase):
    """`F1`（**blocking**，ADR-0006）：`select_successor` 的排列不變性。"""

    @settings(max_examples=200, deadline=None)
    @given(_members_and_a_permutation())
    def test_F1_select_successor_is_permutation_invariant(self, pair):
        """對同一組成員的**任意排列**，輸出必須相同（`BR4.2`／`AC12.4.2`）。

        突變驗證（`unit-test-instructions.md §七` 第 1 列）：把排序鍵改成只按
        `joined_at`（移除 `user_id`）必須讓本測試紅燈。它會紅，因為 `min()` 在
        平手時回傳迭代順序中第一個最小元素，而兩個排列的迭代順序不同。

        第二個斷言（輸出必須是輸入的元素）不是恆真的裝飾：一個「回傳新建
        snapshot」或「回傳 `None`」的實作會在這裡失敗。
        """
        members, permuted = pair
        chosen = select_successor(members)
        self.assertEqual(chosen, select_successor(permuted))
        self.assertIn(chosen, members)

    def test_F1b_empty_input_fails_loudly(self):
        """空集合**大聲失敗**而非回 `None`。

        回 `None` 會把一個邏輯錯誤（呼叫端沒先跑 `BR4.3` 的冪等檢查或
        `BR4.4` 的「另有成員」條件）變成一個要在下游解包的 `Optional`。
        """
        with self.assertRaises(ValueError):
            select_successor([])


class MembershipFacadeTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_ADMIN)
        self.bob = make_user(self.db, username="bob", role=ROLE_ADMIN)
        self.carol = make_user(self.db, username="carol", role=ROLE_VIEW_ONLY)
        self.dave = make_user(self.db, username="dave", role=ROLE_NO_K3)
        self.facade = MembershipFacade(self.db)
        self.p_alice = mint_principal(self.alice)
        self.p_bob = mint_principal(self.bob)
        self.p_carol = mint_principal(self.carol)
        self.p_dave = mint_principal(self.dave)
        self.project = self.facade.create_project_with_owner(self.p_alice, name="P")

    def tearDown(self) -> None:
        close_session(self.db)

    def _add(self, user, role, joined_at=None):
        row = ProjectMember(
            project_id=self.project.id,
            user_id=user.id,
            role=role.value if isinstance(role, ProjectRole) else role,
            joined_at=joined_at or datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def _events(self):
        return self.db.query(ReselectionEvent).order_by(ReselectionEvent.id).all()


class LastAdminGuardTest(MembershipFacadeTestBase):
    """`F2`：守門的三條路徑各自命中與各自放行（`BR2.1`）。"""

    def test_F2_the_three_paths_share_one_guard_and_each_blocks_and_allows(self):
        """三條路徑：停用帳號、自我降級、自我移出。

        `create_project_with_owner` 已讓 alice 成為唯一的 `project_admin`，
        所以三條路徑在**同一個狀態**下都該命中——這正是「共同上游」的意思：
        不是三處各寫一次，而是同一個不變量的三個入口
        （`functional-design:c34`：修在單一入口會把違規挪位置而不是消除它）。
        """
        # --- deny 側（三條路徑都命中）---
        with self.assertRaises(LastAdminGuard) as ctx:
            self.facade.assert_can_deactivate(
                self.p_bob, target_user_id=self.alice.id
            )
        self.assertEqual(
            [p.project_id for p in ctx.exception.projects], [self.project.id]
        )
        self.assertEqual([p.name for p in ctx.exception.projects], ["P"])

        with self.assertRaises(LastAdminGuard):
            self.facade.change_role(
                self.p_alice,
                project_id=self.project.id,
                user_id=self.alice.id,
                role=ProjectRole.MEMBER.value,
            )
        with self.assertRaises(LastAdminGuard):
            self.facade.remove_member(
                self.p_alice, project_id=self.project.id, user_id=self.alice.id
            )
        # 被拒之後狀態必須完好（`BR2.3`：守門唯讀無副作用）。
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=self.alice.id
            ),
            ProjectRole.PROJECT_ADMIN.value,
        )

        # --- allow 側（補上第二位管理者之後三條路徑都放行）---
        self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.bob.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        self.assertIsNone(
            self.facade.assert_can_deactivate(
                self.p_bob, target_user_id=self.alice.id
            )
        )
        view = self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.alice.id,
            role=ProjectRole.MEMBER.value,
        )
        self.assertEqual(view.role, ProjectRole.MEMBER.value)
        self.facade.remove_member(
            self.p_bob, project_id=self.project.id, user_id=self.alice.id
        )
        self.assertIsNone(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=self.alice.id
            )
        )

    def test_F2b_guard_blocks_when_there_are_two_members_but_one_admin(self):
        """`[FD1]`=A **比 `FR12.5` 的字面更嚴**的那一格。

        `FR12.5` 寫「唯一**成員**」，本守門擋的是「最後一位**管理者**」。
        分歧點：專案有 alice（唯一管理者）與 carol（一般成員），停用 alice
        ——`FR12.5` 的字面**不擋**，而不擋會留下一個沒有任何管理者的專案。

        `AC12.3.3` 的 Given 措辭與本定案不一致（`functional-spec.md §四` 已標出
        並指派回補），故本測試依 `[FD1]`=A 的條件撰寫而非依該 AC 的字面。
        """
        self._add(self.carol, ProjectRole.MEMBER)
        self.assertEqual(
            len(membership_service.list_members(self.db, project_id=self.project.id)),
            2,
        )
        with self.assertRaises(LastAdminGuard):
            self.facade.assert_can_deactivate(
                self.p_bob, target_user_id=self.alice.id
            )


class MembershipLifecycleTest(MembershipFacadeTestBase):
    """`F3`–`F5`：邀請的非冪等、移出的冪等、多位管理者不互相覆寫。"""

    def test_F3_invite_is_not_idempotent_and_leaves_no_half_state(self):
        """`F3`／`BR3.3`／`BR3.2`／`AC12.5.3`。

        三件事一起驗，因為它們共用「單一交易」這個前提：
        (a) 成功邀請是**一級行為**（`BR3.6`）——清單必然多一列；
        (b) 重複邀請同一 `(project, user)` 被拒且**不建立第二列**；
        (c) 受邀者缺全域權限時被拒，且**清單不新增任何列**。
        """
        before = len(membership_service.list_members(self.db, project_id=self.project.id))
        view = self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        self.assertEqual(view.user_id, self.carol.id)
        self.assertEqual(
            len(membership_service.list_members(self.db, project_id=self.project.id)),
            before + 1,
        )

        with self.assertRaises(MembershipNotFound):
            self.facade.invite_member(
                self.p_alice,
                project_id=self.project.id,
                user_id=self.carol.id,
                role=ProjectRole.MEMBER.value,
            )
        self.assertEqual(
            self.db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == self.project.id,
                ProjectMember.user_id == self.carol.id,
            )
            .count(),
            1,
        )

        # dave 的全域角色是 SRE（`K3.view` 為 False）→ `BR3.2` 擋下，且不留半套。
        count_before = self.db.query(ProjectMember).count()
        with self.assertRaises(MissingGlobalPermission) as ctx:
            self.facade.invite_member(
                self.p_alice,
                project_id=self.project.id,
                user_id=self.dave.id,
                role=ProjectRole.MEMBER.value,
            )
        self.assertEqual(ctx.exception.user_id, self.dave.id)
        self.assertEqual(ctx.exception.story_id, "K3")
        self.assertEqual(self.db.query(ProjectMember).count(), count_before)

    def test_F4_remove_is_idempotent(self):
        """`F4`／`BR3.4`／`[FD2]`=A：對**已非成員**回成功，不 raise。

        價值在於 `U24` 不需要處理「404 其實是成功」，且競態下兩位管理者同時
        移除同一人時兩邊畫面一致。
        """
        self._add(self.carol, ProjectRole.MEMBER)
        self.facade.remove_member(
            self.p_alice, project_id=self.project.id, user_id=self.carol.id
        )
        # 第二次：已非成員 → **回成功**（本行不得 raise）。
        self.assertIsNone(
            self.facade.remove_member(
                self.p_alice, project_id=self.project.id, user_id=self.carol.id
            )
        )
        # 從未是成員的人也一樣。
        self.assertIsNone(
            self.facade.remove_member(
                self.p_alice, project_id=self.project.id, user_id=self.dave.id
            )
        )

    def test_F5_a_second_admin_does_not_displace_the_first(self):
        """`F5`／`BR3.5`／`AC12.2.4`：指定第二位後**兩位都能執行管理動作**。

        **斷言的是「都能執行」而非「都是管理者」**，而這個區別是本測試能不能
        抓到突變的全部：把 `change_role` 寫成「先把其他 admin 降級再升新的」
        之下，第二位仍是管理者（角色欄位檢查照樣綠），**被降級的是第一位**
        ——只有真的拿第一位去執行一次管理動作才會紅。
        """
        self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.bob.id,
            role=ProjectRole.MEMBER.value,
        )
        self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.bob.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        # 兩位都是管理者……
        for user in (self.alice, self.bob):
            self.assertEqual(
                membership_service.resolve_project_role(
                    self.db, project_id=self.project.id, user_id=user.id
                ),
                ProjectRole.PROJECT_ADMIN.value,
            )
        # ……而且兩位**都能執行**管理動作（這一半才抓得到覆寫突變）。
        self.facade.invite_member(
            self.p_bob,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )

    def test_F5b_both_layers_must_pass(self):
        """`BR1.2` 的兩層串聯：全域層與 per-project 層**缺一即拒**。

        這是 `AC12.5.2` 的 deny 側：bob 具 `K3.edit`（全域層過）但**不是**
        該專案的成員 → 仍須被拒。只檢查一層會讓「具全域權限但非本專案成員」
        的人讀到專案資料。
        """
        # 全域層過、per-project 層不過。
        with self.assertRaises(MembershipForbidden):
            self.facade.list_members(self.p_bob, project_id=self.project.id)
        # per-project 層過（carol 是成員）、全域層不過（`K3.edit` 為 False）。
        self._add(self.carol, ProjectRole.PROJECT_ADMIN)
        self.assertTrue(self.facade.list_members(self.p_carol, project_id=self.project.id))
        with self.assertRaises(MembershipForbidden) as ctx:
            self.facade.invite_member(
                self.p_carol,
                project_id=self.project.id,
                user_id=self.bob.id,
                role=ProjectRole.MEMBER.value,
            )
        self.assertEqual(ctx.exception.action, "edit")
        # 兩層都不過（dave 無 `K3.view`、也不是成員）。
        with self.assertRaises(MembershipForbidden):
            self.facade.list_members(self.p_dave, project_id=self.project.id)


class MembershipAuditTest(MembershipFacadeTestBase):
    """`F6`–`F8`：稽核的五個事實、`cause` 的雙語意、橫幅的 `cause` 過濾與冪等。"""

    def test_F6_manual_role_change_writes_all_five_audit_facts(self):
        """`F6`／`BR5.1`／`BR5.3`：五個事實齊備且 `cause` 正確。

        `BR5.2`：稽核必須寫進 **UI 讀得到的持久層**，不得只用 `logger.info`
        ——`AC12.2.2` 斷言的是**使用者可見的**變更紀錄，寫進 log 會讓該 AC
        永遠紅燈。本測試查的是資料列，正是在鎖住這一點。
        """
        self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        self.assertEqual(self._events(), [])  # 邀請本身不是角色變更，不留稽核
        self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        events = self._events()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.project_id, self.project.id)             # 對哪個專案
        self.assertEqual(event.cause, membership_service.CAUSE_MANUAL_ROLE_CHANGE)
        self.assertEqual(event.promoted_user_id, self.carol.id)         # 對誰
        self.assertEqual(event.previous_owner_user_id, self.alice.id)   # 誰
        self.assertEqual(event.previous_role, ProjectRole.MEMBER.value)  # 舊角色
        self.assertEqual(event.new_role, ProjectRole.PROJECT_ADMIN.value)  # 新角色
        self.assertIsNotNone(event.occurred_at)                         # 何時
        # `BR5.5`：人工變更的列**永遠**不帶已讀狀態。
        self.assertIsNone(event.acknowledged_at)

    def test_F7_previous_owner_means_a_different_person_per_cause(self):
        """`F7`／`BR5.4`：同一欄在兩種 `cause` 下指**不同的人**，而這是刻意的。

        `manual_role_change` → **執行變更的管理者**（`AC12.2.2` 的「誰」）；
        `auto_reselection` → **被停用的 owner**。
        兩者都回答「這次變更是誰造成的」。寫下這條測試的理由與 `BR5.4` 相同：
        下一個人看到同一欄指兩種人會想拆成兩欄，而拆欄會讓 `AC12.2.2` 的查詢
        需要依 `cause` 取不同欄位。
        """
        self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        manual = self._events()[-1]
        self.assertEqual(manual.cause, membership_service.CAUSE_MANUAL_ROLE_CHANGE)
        self.assertEqual(manual.previous_owner_user_id, self.alice.id)

        # 自動改選的情境：owner（**bob**）不是該專案的成員，故它沒有管理者。
        # 這個狀態是可達的——既有專案在回填之前全部零成員，而
        # `projects.owner_user_id` 與 `project_members` 是兩回事。
        #
        # **owner 刻意用 bob 而不是 alice**：alice 擁有 `P`，而她在 `P` 裡是
        # 唯一的管理者。實跑時 `run_auto_reselection(alice)` 因此會**同時**對
        # `P` 改選（排除被停用的 owner 之後 `P` 也沒有管理者了），產生第二筆
        # 事件。那不是缺陷——在真實流程裡 `assert_can_deactivate` 會先擋下
        # 停用 alice 這件事，所以 `run_auto_reselection(alice)` 根本不會被呼叫。
        # 直接呼叫它等於構造一個守門本來就會攔住的狀態。
        orphan = hierarchy_service.create_project(
            self.db, owner_user_id=self.bob.id, name="Orphan"
        )
        for user, when in (
            (self.dave, datetime(2026, 3, 1, tzinfo=timezone.utc)),
            (self.carol, datetime(2026, 2, 1, tzinfo=timezone.utc)),
        ):
            self.db.add(
                ProjectMember(
                    project_id=orphan.id,
                    user_id=user.id,
                    role=ProjectRole.MEMBER.value,
                    joined_at=when,
                )
            )
        self.db.commit()
        events = self.facade.run_auto_reselection(deactivated_user_id=self.bob.id)
        self.assertEqual(len(events), 1)
        auto = events[0]
        self.assertEqual(auto.project_id, orphan.id)
        self.assertEqual(auto.cause, membership_service.CAUSE_AUTO_RESELECTION)
        # `BR4.2`：最早加入者（carol，2 月）而不是 dave（3 月）。
        self.assertEqual(auto.promoted_user_id, self.carol.id)
        # **同一欄，不同的人**：人工那一列是 alice（執行變更的管理者），
        # 這一列是 bob（被停用的 owner）。兩者都回答「這次變更是誰造成的」。
        self.assertEqual(auto.previous_owner_user_id, self.bob.id)
        self.assertNotEqual(auto.previous_owner_user_id, manual.previous_owner_user_id)
        self.assertEqual(auto.previous_role, ProjectRole.MEMBER.value)
        self.assertEqual(auto.new_role, ProjectRole.PROJECT_ADMIN.value)

    def test_F8_banner_filters_on_cause_and_reselection_is_idempotent(self):
        """`F8`／`BR5.5`／`BR4.3`：橫幅只為自動改選而發，且重跑不產生第二筆。

        突變驗證（`§七` 第 4 列）：移除橫幅查詢的
        `cause = 'auto_reselection'` 條件必須讓本測試紅燈——少了它，
        **每一次人工角色變更都會彈出一則橫幅**，而文案是「系統自動把管理權
        交給你」，對人工變更是錯的訊息。這是 `[FD3]`=A 引入的新失敗面。
        """
        # (a) 人工角色變更**不得**產生橫幅。
        self.facade.invite_member(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.MEMBER.value,
        )
        self.facade.change_role(
            self.p_alice,
            project_id=self.project.id,
            user_id=self.carol.id,
            role=ProjectRole.PROJECT_ADMIN.value,
        )
        self.assertEqual(len(self._events()), 1)  # 稽核列有寫
        self.assertEqual(
            self.facade.list_my_pending_reselections(self.p_carol), []
        )  # 但橫幅沒有

        # (b) 自動改選**要**產生橫幅。
        orphan = hierarchy_service.create_project(
            self.db, owner_user_id=self.bob.id, name="Orphan"
        )
        self.db.add(
            ProjectMember(
                project_id=orphan.id,
                user_id=self.carol.id,
                role=ProjectRole.MEMBER.value,
                joined_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        self.db.commit()
        self.assertEqual(
            len(self.facade.run_auto_reselection(deactivated_user_id=self.bob.id)), 1
        )
        pending = self.facade.list_my_pending_reselections(self.p_carol)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].cause, membership_service.CAUSE_AUTO_RESELECTION)

        # (c) `BR4.3` 冪等：重跑**不執行、不寫事件**（carol 現在已是管理者）。
        total_before = len(self._events())
        self.assertEqual(
            self.facade.run_auto_reselection(deactivated_user_id=self.bob.id), []
        )
        self.assertEqual(len(self._events()), total_before)

        # (d) `BR5.6`：已讀以**事件**為鍵；確認之後該事件不再出現，
        #     但同一人第二次被改選時仍看得到（事件不同列）。
        self.assertTrue(
            self.facade.acknowledge_reselection(
                self.p_carol, event_id=pending[0].id
            )
        )
        self.assertEqual(self.facade.list_my_pending_reselections(self.p_carol), [])
        self.assertFalse(
            self.facade.acknowledge_reselection(
                self.p_carol, event_id=pending[0].id
            )
        )


if __name__ == "__main__":
    unittest.main()
