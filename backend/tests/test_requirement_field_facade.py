"""`U20 requirement-field-service` 的業務邏輯測試（`F1`–`F8`，同進程呼叫 facade）。

對應 `unit-test-instructions.md §三` 的第四列（業務邏輯，8 個）。

本檔直接呼叫 `RequirementFieldFacade`，也就是 `U13 brain-gateway` 會走的**同進程**
路徑——它沒有 router、沒有 dependency 鏈，所以待核准與全域層的拒絕（`F7`）必須在
facade 內發生，HTTP 層的同名測試擋不住這條路徑上的缺口。

測試資料（`unit-test-instructions.md §六`）：
- 專案與成員以 `MembershipFacade.create_project_with_owner`／`invite_member` 建立，
  **不直接插 `project_members` 列**（避免繞過 `U19` 的不變量）。
- 角色與核准狀態直接寫 `users`；權限矩陣由 `ensure_role_permissions_seeded` 播種，
  **不 mock `user_can`**——真實的授權路徑必須被執行。
- 時間由注入的固定時鐘產生；值與代寫標示用 `uuid4()` 產生的唯一標記，以斷言 log
  與錯誤訊息不含它。

`RequirementFieldFixture` 供 `test_requirement_field_http.py` 共用（它不是 `TestCase`，
被匯入時不會讓測試跑兩次）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import logging
import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import insert

from models import SystemRequirementField
from services.hierarchy_facade import HierarchyFacade, mint_principal
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole
from services.requirement_field_definitions import FIELD_GROUPS, total_field_count
from services.requirement_field_errors import (
    RequirementFieldForbidden,
    RequirementFieldNotFound,
    RequirementFieldValidationError,
    UnknownFieldKey,
)
from services.requirement_field_facade import RequirementFieldFacade
from services.requirement_field_types import FilledState
from tests.helpers import ALWAYS_VISIBLE, close_session, make_session, make_user
from tests.test_requirement_field_service import QueryCounter

LOGGER = "cloud360.requirement_fields"
T0 = datetime(2026, 10, 1, 8, 0, 0)
T1 = datetime(2026, 10, 12, 9, 0, 0)
T2 = datetime(2026, 10, 12, 9, 30, 0)


class FixedClock:
    """可推進的固定時鐘：`clock.now = T2` 之後的呼叫拿到 T2。"""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class RequirementFieldFixture:
    """一個專案、一個系統，以及授權矩陣各列需要的使用者。

    `K4`（`rbac_seed_data.py`）：`Project_Architect`／`Project_Editor`／`Platform_Admin`
    有 view＋edit；`Developer` 只有 view；`SRE` 皆無。
    """

    def build_fixture(self) -> None:
        self.db = make_session()
        self.clock = FixedClock(T1)
        # owner：建立專案者，per-project 角色為 project_admin，全域有 K4.edit。
        self.owner = make_user(self.db, username="owner", role="Project_Architect")
        self.editor = make_user(self.db, username="editor", role="Project_Editor")
        self.viewer = make_user(self.db, username="viewer", role="Developer")
        self.admin_viewer = make_user(self.db, username="admin_viewer", role="Developer")
        self.no_k4 = make_user(self.db, username="no_k4", role="Developer")
        self.pending = make_user(self.db, username="pending", role="Project_Editor")
        self.outsider = make_user(self.db, username="outsider", role="Project_Editor")
        self.root = make_user(self.db, username="root", role="Platform_Admin")

        membership = MembershipFacade(self.db)
        self.project = membership.create_project_with_owner(
            mint_principal(self.owner), name="P"
        )
        self.system = HierarchyFacade(self.db).create_system(
            mint_principal(self.owner),
            project_id=self.project.id,
            name="S",
            project_visible=ALWAYS_VISIBLE,
        )
        for user, role in (
            (self.editor, ProjectRole.MEMBER),
            (self.viewer, ProjectRole.MEMBER),
            (self.admin_viewer, ProjectRole.PROJECT_ADMIN),
            (self.no_k4, ProjectRole.MEMBER),
            (self.pending, ProjectRole.MEMBER),
        ):
            membership.invite_member(
                mint_principal(self.owner), project_id=self.project.id,
                user_id=user.id, role=role.value,
            )
        # 「另一個專案的成員」：outsider 擁有自己的專案，但不是目標系統所屬專案的成員
        # （security-design 審查 R-03：完全沒有成員身分的人測不出「誤查任何專案」的錯）。
        self.other_project = membership.create_project_with_owner(
            mint_principal(self.outsider), name="Q"
        )

        # 邀請之後才改成無 K3.view 的角色／待核准（受邀者需要 K3.view，SRE 邀不進來）。
        self.no_k4.role = "SRE"
        self.pending.authorization_status = "pending"
        self.db.commit()

    def facade(self) -> RequirementFieldFacade:
        return RequirementFieldFacade(self.db, clock=self.clock)

    def insert_row(self, group, key, *, value, cleared_at=None, updated_at=T0,
                   on_behalf_of=None, system_id=None):
        self.db.execute(
            insert(SystemRequirementField.__table__).values(
                system_id=system_id or self.system.id, agent_group=group,
                field_key=key, value=value, cleared_at=cleared_at,
                updated_at=updated_at, updated_by=self.owner.id,
                updated_on_behalf_of=on_behalf_of,
            )
        )
        self.db.commit()


def field_of(field_set, group_key, field_key):
    group = next(g for g in field_set.groups if g.group_key == group_key)
    return next(f for f in group.fields if f.field_key == field_key)


class RequirementFieldFacadeTest(RequirementFieldFixture, unittest.TestCase):
    def setUp(self) -> None:
        self.build_fixture()

    def tearDown(self) -> None:
        close_session(self.db)

    def read(self, user=None):
        return self.facade().read_fields(
            mint_principal(user or self.editor), system_id=self.system.id
        )

    def write(self, key, value, *, user=None, group="cost", on_behalf_of=None):
        return self.facade().write_field(
            mint_principal(user or self.editor), system_id=self.system.id,
            agent_group=group, field_key=key, value=value, on_behalf_of=on_behalf_of,
        )

    # -- F1：三態推導 ------------------------------------------------------

    def test_F1_three_states_and_the_fourth_kind_of_row(self):
        """`F1`／`BR44.1`／`AC11.2.1`：未填與否由資料決定，第四種列回 `never_filled` 且溯源全為 null。"""
        self.write("sla", "99.9%")
        self.write("peak_tps", "1200")
        self.facade().clear_field(
            mint_principal(self.editor), system_id=self.system.id,
            agent_group="cost", field_key="peak_tps",
        )
        self.insert_row("cost", "user_base", value=None, cleared_at=None)

        field_set = self.read()
        sla = field_of(field_set, "cost", "sla")
        cleared = field_of(field_set, "cost", "peak_tps")
        fourth = field_of(field_set, "cost", "user_base")
        never = field_of(field_set, "cost", "billing_region")

        self.assertEqual(
            (sla.filled_state, sla.value, sla.updated_by, sla.updated_at),
            (FilledState.FILLED, "99.9%", self.editor.id, T1),
        )
        self.assertEqual(
            (cleared.filled_state, cleared.value, cleared.cleared_at),
            (FilledState.CLEARED, None, T1),
        )
        for view in (fourth, never):
            self.assertEqual(view.filled_state, FilledState.NEVER_FILLED)
            self.assertEqual(
                (view.value, view.cleared_at, view.updated_at, view.updated_by,
                 view.updated_on_behalf_of),
                (None, None, None, None, None),
                "never_filled 不得帶最後更新者（review-02 R-06）",
            )

    # -- F2：計數同源 ------------------------------------------------------

    def test_F2_counts_derive_from_the_same_detail(self):
        """`F2`／`BR44.2`／`BR44.4`／`AC11.3.1`–`AC11.3.3`：計數與明細同源、且隨狀態一起變。

        每一步都以**同一個回應**的明細重算計數並比對——不是比對兩個各自查詢的數字。
        讀取對本表恰 1 次 SELECT（`NFR20.1`）。
        """
        def assert_consistent(field_set, expected_unfilled):
            recount = 0
            for group in field_set.groups:
                filled = sum(1 for f in group.fields
                             if f.filled_state is FilledState.FILLED)
                self.assertEqual(group.filled_count, filled)
                self.assertEqual(group.total_count, len(group.fields))
                recount += group.total_count - filled
            self.assertEqual(field_set.unfilled_count, recount)
            self.assertEqual(field_set.unfilled_count, expected_unfilled)

        total = total_field_count()
        self.assertEqual(total, 7)
        assert_consistent(self.read(), total)
        self.write("sla", "99.9%")
        self.write("availability_target", "99.95%", group="architecture")
        assert_consistent(self.read(), total - 2)
        self.write("sla", "   ")  # 使用者把輸入框刪空 → 清空 → 回到未填
        with QueryCounter(self.db) as counter:
            field_set = self.read()
        assert_consistent(field_set, total - 1)
        self.assertEqual(counter.selects, 1)

        self.assertEqual(
            [(g.group_key, g.title, [f.field_key for f in g.fields]) for g in field_set.groups],
            [(g.group_key, g.title, [d.field_key for d in g.fields]) for g in FIELD_GROUPS],
            "AC11.2.2：組依宣告順序、標題為 agent 名稱、組內欄位集合與宣告一致",
        )

    # -- F3：定義外的保留列 ------------------------------------------------

    def test_F3_rows_outside_the_definitions_are_neither_shown_nor_counted(self):
        """`F3`／`BR44.3`／`[UG:G9]`=A：保留列不顯示、不計數、也不被刪除。"""
        self.insert_row("retired_agent", "sla", value="kept")
        self.insert_row("cost", "retired_key", value="kept")
        field_set = self.read()
        self.assertEqual({g.group_key for g in field_set.groups}, {"cost", "architecture"})
        self.assertNotIn("retired_key", {f.field_key for f in field_set.groups[0].fields})
        self.assertEqual(field_set.unfilled_count, total_field_count())

    # -- F4：使用者的空值寫入即清空 -----------------------------------------

    def test_F4_blank_user_write_clears_and_blank_on_never_filled_is_a_noop(self):
        """`F4`／`BR43.2`／`BR43.3`／`BR45.3`：只有空白的使用者寫入 = 清空；對從未填過的欄位不建列。"""
        self.write("sla", "99.9%", on_behalf_of="cost")
        self.clock.now = T2
        cleared = self.write("sla", "  \n ")
        self.assertEqual(
            (cleared.filled_state, cleared.value, cleared.cleared_at,
             cleared.updated_on_behalf_of),
            (FilledState.CLEARED, None, T2, None),
        )
        never = self.write("billing_region", "")
        self.assertEqual(never.filled_state, FilledState.NEVER_FILLED)
        self.assertEqual(
            self.db.query(SystemRequirementField)
            .filter_by(field_key="billing_region").count(),
            0,
        )

    # -- F5：代寫路徑的空值被拒 --------------------------------------------

    def test_F5_blank_write_on_behalf_of_an_agent_is_rejected(self):
        """`F5`／`BR42.5`：代寫路徑的空值不是清空——拒絕，且該欄不變。"""
        self.write("sla", "99.9%")
        with self.assertRaises(RequirementFieldValidationError) as caught:
            self.write("sla", "   ", on_behalf_of="cost")
        self.assertEqual(caught.exception.field, "value")
        sla = field_of(self.read(), "cost", "sla")
        self.assertEqual((sla.filled_state, sla.value), (FilledState.FILLED, "99.9%"))

    # -- F6：輸入白名單 ----------------------------------------------------

    def test_F6_wrong_group_unknown_on_behalf_and_overlong_value_are_rejected(self):
        """`F6`／`BR42.1`–`BR42.4`／`AC11.2.2`：錯綁到別組、未宣告的代寫組、超長值都被拒；錯誤訊息不含值。"""
        marker = f"marker-{uuid.uuid4()}"
        cases = [
            (UnknownFieldKey, dict(group="architecture", key="sla", value=marker)),
            (UnknownFieldKey, dict(group="nope", key="sla", value=marker)),
            (RequirementFieldValidationError,
             dict(group="cost", key="sla", value="v", on_behalf_of=marker)),
            (RequirementFieldValidationError,
             dict(group="cost", key="sla", value=marker + "x" * 2000)),
        ]
        for error, kwargs in cases:
            with self.subTest(**{k: v[:20] for k, v in kwargs.items()}):
                with self.assertRaises(error) as caught:
                    self.write(kwargs["key"], kwargs["value"], group=kwargs["group"],
                               on_behalf_of=kwargs.get("on_behalf_of"))
                self.assertNotIn(marker, str(caught.exception))
        self.assertEqual(self.db.query(SystemRequirementField).count(), 0)

        # 2000 字（去空白後）恰好是上限，可以寫入。
        self.assertEqual(self.write("sla", " " + "y" * 2000 + " ").value, "y" * 2000)

    # -- F7：同進程路徑上的拒絕 --------------------------------------------

    def test_F7_in_process_callers_are_denied_by_the_facade_itself(self):
        """`F7`／`BR41.1`／`BR41.2`／`BR41.4`／`BR45.4`：`U13` 的同進程路徑沒有 router。

        待核准、無 `K4.view`、只有 view 卻寫入（含帶代寫標示）、非成員——四者都必須在
        facade 內被拒，且拒絕時對本表 0 條敘述（`NFR20.7`）。不存在的系統、非整數 id 為 404。
        合併前必修第 14 項（`[PP-MB14]`=A）起，**非成員**的拒絕是 `RequirementFieldNotFound`
        （訊息與「系統不存在」相同、不含 id），其餘三種仍是 `RequirementFieldForbidden`。
        """
        denied = [
            ("pending", self.pending, "read"),
            ("global", self.no_k4, "read"),
            ("global", self.viewer, "write"),
            ("global", self.viewer, "write_on_behalf"),
            ("not_member", self.outsider, "read"),
            ("not_member", self.outsider, "write"),
            ("not_member", self.root, "write"),
        ]
        for reason, user, operation in denied:
            expected = (RequirementFieldNotFound if reason == "not_member"
                        else RequirementFieldForbidden)
            with self.subTest(user=user.username, operation=operation):
                with QueryCounter(self.db) as counter:
                    with self.assertRaises(expected) as caught:
                        if operation == "read":
                            self.read(user)
                        else:
                            self.write("sla", "v", user=user, on_behalf_of=(
                                "cost" if operation == "write_on_behalf" else None))
                if reason == "not_member":
                    self.assertEqual(str(caught.exception), str(RequirementFieldNotFound()))
                else:
                    self.assertEqual(caught.exception.reason, reason)
                self.assertEqual(counter.table_statements, 0, counter.statements)

        for missing in (999_999, "abc", "99999999999", -1):
            with self.assertRaises(RequirementFieldNotFound):
                self.facade().read_fields(mint_principal(self.editor), system_id=missing)

        # 正向：project_admin 但只有 K4.view 的人讀得到；成員 project_admin＋K4.edit 寫得進去。
        self.read(self.admin_viewer)
        self.assertEqual(self.write("sla", "ok", user=self.owner).updated_by, self.owner.id)

    # -- F8：log、no-op、依賴失敗、回滾 -------------------------------------

    def test_F8_logs_noop_dependency_failure_and_rollback(self):
        """`F8`／`BR41.6`／`NFR20.11`／`NFR20.19`／`NFR20.27`–`NFR20.29`。

        (a) 拒絕恰一行 WARNING，欄位正確；(b) 全部 log 不含值或代寫標示的值；
        (c) 重複清空的第二次不記 INFO；(d) 依賴拋非預期例外時不放行、不寫入；
        (e) commit 失敗時已 rollback，同一連線上重讀（即已提交狀態）值與狀態不變。
        """
        marker = f"marker-{uuid.uuid4()}"
        with self.assertLogs(LOGGER, level="INFO") as logs:
            with self.assertRaises(RequirementFieldNotFound):
                self.write("sla", marker, user=self.outsider)
            self.write("sla", marker, on_behalf_of="cost")
            self.facade().clear_field(mint_principal(self.editor),
                                      system_id=self.system.id,
                                      agent_group="cost", field_key="sla")
        denied = [r for r in logs.records if r.levelno == logging.WARNING]
        self.assertEqual(len(denied), 1)
        self.assertEqual(
            (denied[0].story_id, denied[0].action, denied[0].system_id,
             denied[0].user_id, denied[0].reason),
            ("K4", "edit", self.system.id, self.outsider.id, "not_member"),
        )
        self.assertEqual(
            [r.getMessage().split()[0] for r in logs.records],
            ["requirement_field.denied", "requirement_field.written",
             "requirement_field.cleared"],
        )
        self.assertEqual(logs.records[1].on_behalf, True)
        for record in logs.records:
            self.assertNotIn(marker, record.getMessage())
            self.assertNotIn(marker, repr(record.__dict__))

        # (c) 已清空再清空：不記 INFO。
        with self.assertNoLogs(LOGGER, level="INFO"):
            self.facade().clear_field(mint_principal(self.editor),
                                      system_id=self.system.id,
                                      agent_group="cost", field_key="sla")

        # (d) per-project 判定的依賴拋非預期例外 → 傳播，不放行、不寫入。
        with patch(
            "services.requirement_field_facade.MembershipFacade.resolve_project_role",
            side_effect=RuntimeError("membership store unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self.write("peak_tps", "1200")
        self.assertEqual(
            self.db.query(SystemRequirementField).filter_by(field_key="peak_tps").count(), 0
        )

        # (e) commit 拋錯 → rollback → 值與狀態維持呼叫前。
        self.write("sla", "before")
        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            with patch.object(self.db, "rollback", wraps=self.db.rollback) as rollback:
                with self.assertRaises(RuntimeError):
                    self.write("sla", "after")
        rollback.assert_called_once()
        sla = field_of(self.read(), "cost", "sla")
        self.assertEqual((sla.filled_state, sla.value), (FilledState.FILLED, "before"))

    # -- R1–R3：成功讀取的稽核 log（merge-blockers 第 8 項） -----------------

    @staticmethod
    def read_records(logs):
        return [r for r in logs.records
                if r.getMessage().split()[0] == "requirement_field.read"]

    def test_R1_successful_read_logs_reader_identity_once(self):
        """成功讀取恰記一行 `requirement_field.read`，帶讀取者本人與授權後的 id。

        @purpose 稽核主體必須是使用者本人在讀取面也成立（`requirements.md:620` ③）；
                 拿掉這行 log 時本案紅燈（突變 M-A）。
        @given   editor 是目標系統所屬專案的成員且有 `K4.view`；`system_id` 以字串傳入。
        @step    以 editor 呼叫 `read_fields`。
        @pass    恰一筆 `requirement_field.read`（INFO），`user_id`＝editor、`system_id`＝整數
                 系統 id（授權後的 `known_id`，不是輸入原值）、`action`＝`view`、`on_behalf` 為 False。
        @story   US11.4
        """
        with self.assertLogs(LOGGER, level="INFO") as logs:
            self.facade().read_fields(mint_principal(self.editor),
                                      system_id=str(self.system.id))
        records = self.read_records(logs)
        self.assertEqual(len(records), 1, [r.getMessage() for r in logs.records])
        record = records[0]
        self.assertEqual(record.levelno, logging.INFO)
        self.assertEqual(
            (record.story_id, record.action, record.system_id, record.user_id,
             record.on_behalf),
            ("K4", "view", self.system.id, self.editor.id, False),
        )
        self.assertIsInstance(record.system_id, int)
        self.assertIn(f"user_id={self.editor.id}", record.getMessage())

    def test_R2_read_log_never_carries_field_values(self):
        """讀取 log 不含欄位值（突變 M-B：log 改記欄位值時紅燈）。

        @purpose 讀取稽核行只記身分與系統，不把被讀到的需求欄位值寫進 log。
        @given   editor 先寫入一個以 `uuid4()` 產生的唯一標記值。
        @step    以 editor 呼叫 `read_fields`，只擷取讀取期間的 log。
        @pass    回傳值含該標記（證明讀得到）；該次 `requirement_field.read` 的訊息與
                 `__dict__`（含全部 `extra`）都不含該標記。
        @story   US11.4
        """
        marker = f"marker-{uuid.uuid4()}"
        self.write("sla", marker)
        with self.assertLogs(LOGGER, level="INFO") as logs:
            field_set = self.read()
        self.assertEqual(field_of(field_set, "cost", "sla").value, marker)
        records = self.read_records(logs)
        self.assertEqual(len(records), 1)
        for record in logs.records:
            self.assertNotIn(marker, record.getMessage())
            self.assertNotIn(marker, repr(record.__dict__))

    def test_R3_denied_read_logs_only_the_denial(self):
        """被拒讀取只有 `requirement_field.denied`，沒有 `requirement_field.read`（突變 M-C）。

        @purpose 讀取稽核行必須在授權通過之後才記；記在授權之前會讓被拒的讀取也留下
                 「已讀」紀錄。
        @given   outsider 不是目標系統所屬專案的成員。
        @step    以 outsider 呼叫 `read_fields`。
        @pass    拋 `RequirementFieldNotFound`（合併前必修第 14 項：非成員對外為 404）；log 恰一行
                 `requirement_field.denied`（reason=not_member），`requirement_field.read` 為 0 筆。
        @story   US11.4
        """
        with self.assertLogs(LOGGER, level="INFO") as logs:
            with self.assertRaises(RequirementFieldNotFound):
                self.read(self.outsider)
        self.assertEqual(
            [r.getMessage().split()[0] for r in logs.records],
            ["requirement_field.denied"],
        )
        self.assertEqual(logs.records[0].reason, "not_member")
        self.assertEqual(self.read_records(logs), [])

    def test_R5_not_found_read_logs_nothing(self):
        """讀取不存在的系統拋 not-found，且不留 `requirement_field.read`（審查 review-02 R-13）。

        @purpose 讀取稽核行只在授權通過後才記；不存在或不可見的系統不得留下「已讀」紀錄。
                 把 log 移到 `_authorize` 之前時本案紅燈。
        @given   editor 是目標專案成員且有 `K4.view`；目標 id 為不存在的整數、非整數字串、
                 超出範圍的數字字串與負數。
        @step    以 editor 對每個 id 呼叫 `read_fields`。
        @pass    每次都拋 `RequirementFieldNotFound`；`cloud360.requirement_fields` 在 INFO 以上
                 沒有任何一筆紀錄（因此 `requirement_field.read` 為 0 筆）。
        @story   US11.4
        """
        for missing in (999_999, "abc", "99999999999", -1):
            with self.subTest(system_id=missing):
                with self.assertNoLogs(LOGGER, level="INFO"):
                    with self.assertRaises(RequirementFieldNotFound):
                        self.facade().read_fields(mint_principal(self.editor),
                                                  system_id=missing)


if __name__ == "__main__":
    unittest.main()
