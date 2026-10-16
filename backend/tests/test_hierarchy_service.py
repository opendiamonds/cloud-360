"""`U7 hierarchy-service` 的測試（`T1`–`T26`，見 unit-test-instructions.md）。

**測試指示的一處前提在實作時被查證推翻，已就地調整並記錄**：指示的 `T2` 寫
「**不具 `K2`** 的角色呼叫五個 path 皆得 403」，但 `rbac_seed_data.py:327-337`
顯示**全部 11 個 canonical role 的 `K2` view 都是 True**，只有 4 個
（`Project_Architect`／`Project_Editor`／`Project_Admin`／`Platform_Admin`）
edit 為 True。故「不具 K2」在本 repo 的 seed 下不存在於 canonical role。

deny 側改為兩條**真實存在**的路徑，兩者都有可失敗的行為：
  (a) `Developer`（K2 view=True、edit=False）→ 讀 200、三條寫入 403；
  (b) 非 canonical role → `user_can` 的 `is_canonical_role` 檢查回 False
      → 五個 path 全 403。
照原指示寫會得到一個**恆真**的測試（找不到這種角色），這正是
`project.md` 記過的「恆真驗收標準」形狀。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 psycopg stub 與 sys.path

import inspect
import re
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import DiagramChangeRecord, Project, System, UserDiagram
from services.auth import get_current_user
from services.hierarchy_facade import (
    HierarchyConflictError,
    HierarchyFacade,
    HierarchyForbidden,
    HierarchyNotFound,
    HierarchyValidationError,
    Principal,
    mint_principal,
)
import services.hierarchy_service as hierarchy_service
from tests.helpers import (
    ALWAYS_VISIBLE,
    close_session,
    make_diagram,
    make_session,
    make_user,
)

ROLE_EDIT = "Project_Architect"   # K2 view+edit
ROLE_VIEW_ONLY = "Developer"      # K2 view 但 edit=False
ROLE_NON_CANONICAL = "Totally_Not_A_Role"


class HierarchyTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role=ROLE_EDIT)
        self.bob = make_user(self.db, username="bob", role=ROLE_EDIT)
        self.viewer = make_user(self.db, username="viewer", role=ROLE_VIEW_ONLY)
        self.outsider = make_user(
            self.db, username="outsider", role=ROLE_NON_CANONICAL
        )
        self.facade = HierarchyFacade(self.db)
        self.p_alice = mint_principal(self.alice)
        self.p_bob = mint_principal(self.bob)
        self.p_viewer = mint_principal(self.viewer)
        self.p_outsider = mint_principal(self.outsider)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user) -> TestClient:
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def a_project(self, owner, name="proj") -> Project:
        return hierarchy_service.create_project(
            self.db, owner_user_id=owner.id, name=name
        )

    def a_system(self, project, name="sys") -> System:
        return hierarchy_service.create_system(
            self.db, project_id=project.id, name=name
        )


# ===========================================================================
# A 群——授權
# ===========================================================================


class TestAuthorization(HierarchyTestBase):
    def test_T1_edit_role_gets_2xx_on_all_five_paths(self):
        """`T1`／`BR1.1`：具 `K2` view＋edit 的角色，五個 path 皆 2xx。"""
        c = self.client_as(self.alice)
        r = c.post("/api/hierarchy/projects", json={"name": "P"})
        self.assertEqual(r.status_code, 201, r.text)
        pid = r.json()["id"]
        self.assertEqual(c.get("/api/hierarchy/projects").status_code, 200)
        r = c.post(f"/api/hierarchy/projects/{pid}/systems", json={"name": "S"})
        self.assertEqual(r.status_code, 201, r.text)
        sid = r.json()["id"]
        self.assertEqual(
            c.get(f"/api/hierarchy/projects/{pid}/systems").status_code, 200
        )
        self.assertEqual(
            c.get("/api/hierarchy/diagram-changes").status_code, 200
        )
        self.assertEqual(
            c.delete(f"/api/hierarchy/systems/{sid}").status_code, 204
        )
        self.assertEqual(
            c.delete(f"/api/hierarchy/projects/{pid}").status_code, 204
        )

    def test_T2a_view_only_role_is_denied_on_every_write_path(self):
        """`T2`(a)／`BR1.1`：`K2` edit=False 的角色，三條寫入路徑全 403。"""
        project = self.a_project(self.viewer)
        c = self.client_as(self.viewer)
        self.assertEqual(
            c.post("/api/hierarchy/projects", json={"name": "X"}).status_code, 403
        )
        self.assertEqual(
            c.post(
                f"/api/hierarchy/projects/{project.id}/systems", json={"name": "X"}
            ).status_code,
            403,
        )
        self.assertEqual(
            c.delete(f"/api/hierarchy/projects/{project.id}").status_code, 403
        )
        # 讀取仍可（view=True）——deny 必須是**針對 action**的，不是全有全無
        self.assertEqual(c.get("/api/hierarchy/projects").status_code, 200)

    def test_T2b_non_canonical_role_is_denied_everywhere(self):
        """`T2`(b)／`BR1.1`：非 canonical role 五個 path 全 403。"""
        c = self.client_as(self.outsider)
        self.assertEqual(c.get("/api/hierarchy/projects").status_code, 403)
        self.assertEqual(c.get("/api/hierarchy/diagram-changes").status_code, 403)
        self.assertEqual(
            c.post("/api/hierarchy/projects", json={"name": "X"}).status_code, 403
        )
        self.assertEqual(
            c.get("/api/hierarchy/projects/1/systems").status_code, 403
        )
        self.assertEqual(c.delete("/api/hierarchy/systems/1").status_code, 403)

    def test_T3_facade_raises_hierarchy_forbidden_not_http_exception(self):
        """`T3`／K-07 `on_denied`：facade 的拒絕**不是** `HTTPException`。"""
        from fastapi import HTTPException

        with self.assertRaises(HierarchyForbidden) as ctx:
            self.facade.create_project(self.p_outsider, name="X")
        exc = ctx.exception
        self.assertNotIsInstance(exc, HTTPException)
        self.assertEqual(exc.story_id, "K2")
        self.assertEqual(exc.action, "edit")

    def test_T4_principal_cannot_be_constructed_outside_the_facade_module(self):
        """`T4`／`BR1.4`：`Principal` 只能由 facade 鑄造。"""
        with self.assertRaises(TypeError):
            Principal(user_id=self.alice.id, role=ROLE_EDIT)
        with self.assertRaises(TypeError):
            Principal(user_id=self.alice.id, role=ROLE_EDIT, _mint_token=object())
        minted = mint_principal(self.alice)
        self.assertEqual(minted.user_id, self.alice.id)
        # 每個 facade 方法的第一個位置參數都是 principal（`BR1.2`）
        for name in (
            "create_project", "create_system", "delete_project", "delete_system",
            "record_diagram_change", "list_projects", "list_systems",
            "resolve_work_target", "list_diagram_changes",
            "project_exists", "get_project_owner", "get_project_of_system",
        ):
            params = list(
                inspect.signature(getattr(HierarchyFacade, name)).parameters
            )
            self.assertEqual(params[1], "principal", f"{name} 的第一參數應為 principal")


# ===========================================================================
# B 群——列可見範圍（本輪兩個 Critical 的處置）
# ===========================================================================


class TestRowVisibility(HierarchyTestBase):
    def test_T5_list_projects_excludes_other_users_rows(self):
        """`T5`／`BR6.1`：清單不含他人的專案。"""
        self.a_project(self.alice, "alice-p")
        self.a_project(self.bob, "bob-p")
        names = [p.name for p in self.facade.list_projects(self.p_alice)]
        self.assertEqual(names, ["alice-p"])
        self.assertNotIn("bob-p", names)

    def test_T6_listing_someone_elses_systems_reports_not_found_not_forbidden(self):
        """`T6`／`BR6.1`：回「查不到」而非「無權限」，不洩漏存在性。"""
        bob_p = self.a_project(self.bob, "bob-p")
        with self.assertRaises(HierarchyNotFound):
            self.facade.list_systems(self.p_alice, project_id=bob_p.id)
        c = self.client_as(self.alice)
        r = c.get(f"/api/hierarchy/projects/{bob_p.id}/systems")
        self.assertEqual(r.status_code, 404)
        # 與**真正不存在**的 id 回同一種結果——否則狀態碼本身就是預言機
        r_absent = c.get("/api/hierarchy/projects/999999/systems")
        self.assertEqual(r_absent.status_code, 404)

    def test_T7_resolve_work_target_rejects_other_users_ids(self):
        """`T7`／`BR6.1`：同進程解析路徑同受列範圍限制。"""
        bob_p = self.a_project(self.bob, "bob-p")
        bob_s = self.a_system(bob_p, "bob-s")
        with self.assertRaises(HierarchyNotFound):
            self.facade.resolve_work_target(self.p_alice, project_id=bob_p.id)
        with self.assertRaises(HierarchyNotFound):
            self.facade.resolve_work_target(self.p_alice, system_id=bob_s.id)
        alice_p = self.a_project(self.alice, "alice-p")
        resolved = self.facade.resolve_work_target(
            self.p_alice, project_id=alice_p.id
        )
        self.assertEqual(resolved["projectId"], alice_p.id)

    def test_T8_cannot_create_a_system_under_someone_elses_project(self):
        """`T8`／`BR6.5`：寫入面的擁有者檢查（比讀取外洩更嚴重）。"""
        bob_p = self.a_project(self.bob, "bob-p")
        with self.assertRaises(HierarchyNotFound):
            self.facade.create_system(
                self.p_alice, project_id=bob_p.id, name="sneaky", project_visible=ALWAYS_VISIBLE
            )
        self.assertEqual(
            self.db.query(System).filter(System.project_id == bob_p.id).count(), 0
        )

    def test_T9_cannot_delete_someone_elses_project_or_system(self):
        """`T9`／`BR6.5`：刪除是破壞性的，不可由讀取範圍限制擋下。"""
        bob_p = self.a_project(self.bob, "bob-p")
        bob_s = self.a_system(bob_p, "bob-s")
        with self.assertRaises(HierarchyNotFound):
            self.facade.delete_system(self.p_alice, system_id=bob_s.id, project_visible=ALWAYS_VISIBLE)
        with self.assertRaises(HierarchyNotFound):
            self.facade.delete_project(self.p_alice, project_id=bob_p.id, project_visible=ALWAYS_VISIBLE)
        self.assertIsNotNone(self.db.get(System, bob_s.id))
        self.assertIsNotNone(self.db.get(Project, bob_p.id))

    def test_T10_decision_support_queries_answer_for_others_and_leak_nothing(self):
        """`T10`／`BR6.4`：**必須**回答他人的 id，且只回最小欄位。

        這是 `[F9]`=A 的**正面**斷言：套上列範圍會讓契約 `K-16`／`K-17`
        不可實作（`assert_can_deactivate` 要查被停用者名下的專案）。
        """
        bob_p = self.a_project(self.bob, "bob-p")
        bob_s = self.a_system(bob_p, "bob-s")
        self.assertIs(
            self.facade.project_exists(self.p_alice, project_id=bob_p.id), True
        )
        owner = self.facade.get_project_owner(self.p_alice, project_id=bob_p.id)
        self.assertEqual(owner, self.bob.id)
        parent = self.facade.get_project_of_system(self.p_alice, system_id=bob_s.id)
        self.assertEqual(parent, bob_p.id)
        # 最小欄位是「可驗證已知 id」與「可枚舉未知 id」的唯一分界
        self.assertIsInstance(
            self.facade.project_exists(self.p_alice, project_id=bob_p.id), bool
        )
        self.assertIsInstance(owner, int)
        self.assertIsInstance(parent, int)
        for value in (owner, parent):
            self.assertNotIsInstance(value, (Project, System, list, dict, tuple))

    def test_T10b_decision_support_queries_are_not_exposed_over_http(self):
        """`T10`／`BR6.4` 約束 (1)：不得經任何 HTTP path 暴露。"""
        source = Path(
            hierarchy_service.__file__
        ).with_name("hierarchy_router.py").read_text(encoding="utf-8")
        for leaked in ("project_exists", "get_project_owner", "get_project_of_system"):
            self.assertNotIn(
                f"{leaked}(", source,
                f"router 不得呼叫判定支援型方法 {leaked}（BR6.4 約束 1）",
            )

    def test_T11_change_record_visibility_is_scoped_to_the_diagram_owner(self):
        """`T11`／`BR6.3`：以 `user_diagrams.user_id` 判定。"""
        alice_d = make_diagram(self.db, owner=self.alice, title="alice-d")
        bob_d = make_diagram(self.db, owner=self.bob, title="bob-d")
        hierarchy_service.record_diagram_change(
            self.db, diagram_id=alice_d.id, requirement_summary="a",
            requirement_label="L", actor_user_id=self.alice.id,
        )
        hierarchy_service.record_diagram_change(
            self.db, diagram_id=bob_d.id, requirement_summary="b",
            requirement_label="L", actor_user_id=self.bob.id,
        )
        rows = self.facade.list_diagram_changes(self.p_alice)
        self.assertEqual([r.diagram_id for r in rows], [alice_d.id])


# ===========================================================================
# C 群——建立與名稱
# ===========================================================================


class TestCreateAndNaming(HierarchyTestBase):
    def test_T12_blank_names_are_rejected_with_a_validation_error(self):
        """`T12`／`BR3.1`：空白名稱不得變成 500。"""
        for bad in ("", "   ", "\t\n"):
            with self.assertRaises(HierarchyValidationError):
                self.facade.create_project(self.p_alice, name=bad)
        c = self.client_as(self.alice)
        self.assertEqual(
            c.post("/api/hierarchy/projects", json={"name": "   "}).status_code, 422
        )

    def test_T13_duplicate_name_is_a_conflict_and_surfaces_as_409(self):
        """`T13`／`BR3.2`＋`BR6.6`：衝突回 409。"""
        self.a_project(self.alice, "dup")
        with self.assertRaises(HierarchyConflictError):
            self.facade.create_project(self.p_alice, name="dup")
        c = self.client_as(self.alice)
        self.assertEqual(
            c.post("/api/hierarchy/projects", json={"name": "dup"}).status_code, 409
        )
        # 名稱唯一性只在**同一擁有者**範圍內——bob 可以用同一個名稱
        other = hierarchy_service.create_project(
            self.db, owner_user_id=self.bob.id, name="dup"
        )
        self.assertIsNotNone(other.id)

    def test_T14_new_rows_are_never_marked_default(self):
        """`T14`／`BR2.3`：`is_default` 只由遷移程式寫入。"""
        project = self.facade.create_project(self.p_alice, name="P")
        self.assertFalse(project.is_default)
        system = self.facade.create_system(
            self.p_alice, project_id=project.id, name="S", project_visible=ALWAYS_VISIBLE
        )
        self.assertFalse(system.is_default)

    def test_T15_creating_a_system_under_a_missing_project_is_not_found(self):
        """`T15`／`BR2.2`：目標專案不存在即拒絕。"""
        with self.assertRaises(HierarchyNotFound):
            self.facade.create_system(self.p_alice, project_id=999999, name="S", project_visible=ALWAYS_VISIBLE)


# ===========================================================================
# D 群——刪除
# ===========================================================================


class TestDeletion(HierarchyTestBase):
    def test_T16_default_rows_cannot_be_deleted(self):
        """`T16`／`BR4.2`：預設組不可刪除。"""
        project = self.a_project(self.alice, "default-p")
        project.is_default = True
        self.db.commit()
        with self.assertRaises(HierarchyConflictError):
            self.facade.delete_project(self.p_alice, project_id=project.id, project_visible=ALWAYS_VISIBLE)
        system = self.a_system(project, "default-s")
        system.is_default = True
        self.db.commit()
        with self.assertRaises(HierarchyConflictError):
            self.facade.delete_system(self.p_alice, system_id=system.id, project_visible=ALWAYS_VISIBLE)

    def test_T17_deleting_a_project_with_systems_states_the_remaining_count(self):
        """`T17`／`BR4.4`：訊息**必須含剩餘系統數**。"""
        project = self.a_project(self.alice, "P")
        self.a_system(project, "s1")
        self.a_system(project, "s2")
        with self.assertRaises(HierarchyConflictError) as ctx:
            self.facade.delete_project(self.p_alice, project_id=project.id, project_visible=ALWAYS_VISIBLE)
        self.assertIn("2", str(ctx.exception))
        c = self.client_as(self.alice)
        r = c.delete(f"/api/hierarchy/projects/{project.id}")
        self.assertEqual(r.status_code, 409)
        self.assertIn("2", r.json()["detail"])

    def test_T18_deleting_a_system_with_diagrams_states_how_many(self):
        """`T18`／`BR4.3`：仍有架構圖即拒絕並說明張數。"""
        project = self.a_project(self.alice, "P")
        system = self.a_system(project, "S")
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        diagram.system_id = system.id
        self.db.commit()
        with self.assertRaises(HierarchyConflictError) as ctx:
            self.facade.delete_system(self.p_alice, system_id=system.id, project_visible=ALWAYS_VISIBLE)
        self.assertIn("1", str(ctx.exception))

    def test_T19_a_clean_delete_succeeds_and_never_cascades(self):
        """`T19`／`BR4.3`＋`BR4.4`：**任何情況都不級聯**。"""
        project = self.a_project(self.alice, "P")
        system = self.a_system(project, "S")
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        diagram.system_id = system.id
        self.db.commit()
        # 先把圖移出系統，刪系統才會成功
        diagram.system_id = None
        self.db.commit()
        self.facade.delete_system(self.p_alice, system_id=system.id, project_visible=ALWAYS_VISIBLE)
        self.assertIsNone(self.db.get(System, system.id))
        # **圖沒有被連帶刪除**
        self.assertIsNotNone(self.db.get(UserDiagram, diagram.id))
        self.facade.delete_project(self.p_alice, project_id=project.id, project_visible=ALWAYS_VISIBLE)
        self.assertIsNone(self.db.get(Project, project.id))
        self.assertIsNotNone(self.db.get(UserDiagram, diagram.id))


# ===========================================================================
# E 群——變更紀錄
# ===========================================================================


class TestChangeRecords(HierarchyTestBase):
    def test_T20_only_the_brain_orchestration_source_is_accepted(self):
        """`T20`／`BR5.3`：允許值只有一個。"""
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        with self.assertRaises(HierarchyValidationError):
            hierarchy_service.record_diagram_change(
                self.db, diagram_id=diagram.id, requirement_summary="s",
                requirement_label="L", actor_user_id=self.alice.id,
                source="a1_design_page",
            )
        ok = hierarchy_service.record_diagram_change(
            self.db, diagram_id=diagram.id, requirement_summary="s",
            requirement_label="L", actor_user_id=self.alice.id,
        )
        self.assertEqual(ok.source, "brain_orchestration")

    def test_T21_blank_requirement_summary_is_rejected(self):
        """`T21`／`BR5.4`：空摘要的紀錄對查詢端毫無價值。"""
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        for bad in ("", "   "):
            with self.assertRaises(HierarchyValidationError):
                hierarchy_service.record_diagram_change(
                    self.db, diagram_id=diagram.id, requirement_summary=bad,
                    requirement_label="L", actor_user_id=self.alice.id,
                )

    def test_T22_actor_is_the_causing_user_not_the_session_owner(self):
        """`T22`／`BR5.6`：`actor_user_id` **不得**預設為 session 擁有者。

        情境：`principal` 是 alice（session 擁有者），而實際造成異動的是 bob。
        """
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        record = self.facade.record_diagram_change(
            self.p_alice,
            diagram_id=diagram.id,
            requirement_summary="s",
            requirement_label="L",
            actor_user_id=self.bob.id,   # ← 與 principal 不同
        )
        self.assertEqual(record.actor_user_id, self.bob.id)
        self.assertNotEqual(record.actor_user_id, self.p_alice.user_id)
        # 型別層保證：`actor_user_id` 是**必填的具名參數**，沒有預設值
        sig = inspect.signature(HierarchyFacade.record_diagram_change)
        self.assertIs(sig.parameters["actor_user_id"].default, inspect.Parameter.empty)

    def test_T23_label_query_works_and_system_query_misses_unassigned_diagrams(self):
        """`T23`／`BR5.1`＋`OPEN-H11`：斷言**現實**而非願望。"""
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        self.assertIsNone(diagram.system_id)  # 新建的圖沒有系統歸屬
        hierarchy_service.record_diagram_change(
            self.db, diagram_id=diagram.id, requirement_summary="s",
            requirement_label="auth-rework", actor_user_id=self.alice.id,
        )
        by_label = self.facade.list_diagram_changes(
            self.p_alice, label="auth-rework"
        )
        self.assertEqual(len(by_label), 1)
        project = self.a_project(self.alice, "P")
        system = self.a_system(project, "S")
        # `OPEN-H11`：以系統查詢時，`system_id` 為空的圖一律查不到
        by_system = self.facade.list_diagram_changes(
            self.p_alice, system_id=system.id
        )
        self.assertEqual(by_system, [])


# ===========================================================================
# F 群——NFR 與契約
# ===========================================================================


class TestContractAndNfr(HierarchyTestBase):
    def test_T24_response_models_expose_exactly_the_specified_fields(self):
        """`T24`／`NFR5.1`、`team.md` 規則 B：斷言欄位集合。"""
        c = self.client_as(self.alice)
        pid = c.post("/api/hierarchy/projects", json={"name": "P"}).json()["id"]
        project_row = c.get("/api/hierarchy/projects").json()[0]
        self.assertEqual(
            set(project_row),
            {"id", "name", "owner_user_id", "is_default", "created_at"},
        )
        c.post(f"/api/hierarchy/projects/{pid}/systems", json={"name": "S"})
        system_row = c.get(f"/api/hierarchy/projects/{pid}/systems").json()[0]
        self.assertEqual(
            set(system_row),
            {"id", "project_id", "name", "is_default", "created_at"},
        )
        diagram = make_diagram(self.db, owner=self.alice, title="d")
        hierarchy_service.record_diagram_change(
            self.db, diagram_id=diagram.id, requirement_summary="s",
            requirement_label="L", actor_user_id=self.alice.id,
        )
        change_row = c.get("/api/hierarchy/diagram-changes").json()[0]
        self.assertEqual(
            set(change_row),
            {
                "id", "diagram_id", "source", "actor_user_id",
                "requirement_summary", "requirement_label", "created_at",
            },
        )
        # `source` 必須在回應中——`NFR7.1`／`BR6.3` 要求讀者能判斷涵蓋範圍
        self.assertIn("source", change_row)

    def test_T25_orm_columns_match_the_authoritative_ddl(self):
        """`T25`：鎖住 ORM 與 `schema_rbac.sql` 兩份物化的一致性。

        `team.md` 的「單一真實來源」規則逐字：「新增副本的同一個 PR 必須一併
        新增鎖住兩者一致的測試；無法寫測試的副本不新增」。**沒有這支測試，
        新增 ORM model 這個決定就不合規。**
        """
        sql_path = Path(__file__).resolve().parents[2] / "schema_rbac.sql"
        sql = sql_path.read_text(encoding="utf-8")
        for model, table in (
            (Project, "projects"),
            (System, "systems"),
            (DiagramChangeRecord, "diagram_change_records"),
        ):
            m = re.search(
                r"CREATE TABLE IF NOT EXISTS " + table + r"\s*\((.*?)\n\);",
                sql,
                re.S,
            )
            self.assertIsNotNone(m, f"{table} 的 DDL 找不到")
            ddl_cols = set()
            for line in m.group(1).splitlines():
                line = line.strip()
                # 略過約束宣告及其**續行**：`CONSTRAINT ck_x\n  CHECK (...)`
                # 的第二行以 `CHECK` 開頭，只擋 `CONSTRAINT` 會把 `CHECK`
                # 誤收成欄位名（本測試第一次跑就抓到這個解析 bug）。
                if not line or line.startswith(
                    ("CONSTRAINT", "CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "--", ")")
                ):
                    continue
                ddl_cols.add(line.split()[0].strip(","))
            orm_cols = {c.name for c in model.__table__.columns}
            self.assertEqual(
                orm_cols, ddl_cols,
                f"{table}：ORM 欄位與 DDL 不一致 "
                f"(ORM only={orm_cols - ddl_cols}, DDL only={ddl_cols - orm_cols})",
            )

    def test_T26_modules_hold_no_mutable_module_level_state(self):
        """`T26`／`NFR4.1`：不得持有進程內狀態。

        自動滿足（三實體全部經 DB 讀寫），但容易被無聲破壞——加一個模組級
        dict 當快取就違反它，而且不會有任何錯誤訊息。
        """
        import services.hierarchy_facade as facade_mod
        import services.hierarchy_router as router_mod

        for module in (facade_mod, hierarchy_service, router_mod):
            for name, value in vars(module).items():
                if name.startswith("__") or inspect.ismodule(value):
                    continue
                if isinstance(value, (dict, list, set)) and not isinstance(
                    value, frozenset
                ):
                    # 允許清單：不可變的 frozenset 與 FastAPI 的宣告用 dict
                    self.assertIn(
                        name, {"CONFLICT_RESPONSE", "ALLOWED_CHANGE_SOURCES"},
                        f"{module.__name__}.{name} 是模組級可變狀態（違反 NFR4.1）",
                    )


if __name__ == "__main__":
    unittest.main()
