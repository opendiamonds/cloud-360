"""261116-brain-create-diagram U1 diagram-drafts：列圖、刪除系統、清除預設專案與草稿。

追溯：FR6.4b（判斷「底下有沒有圖」的地方包含草稿）、FR6.4c／ADR-005（列圖必須明示
是否包含草稿）、契約 C5（回傳四元組、新到舊排序）。
本檔只測同行程函式與資料層，不經 HTTP，故無 `@api`／`@ui`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from sqlalchemy import text

from models import DIAGRAM_STATUS_DRAFT, System
from services import hierarchy_service
from services.hierarchy_facade import HierarchyConflictError, HierarchyFacade, mint_principal
from services.user_router import _empty_default_project_ids
from tests.helpers import ALWAYS_VISIBLE, close_session, make_diagram, make_session, make_user


class _HierarchyFixture(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.principal = mint_principal(self.alice)
        self.facade = HierarchyFacade(self.db)
        self.project = self.facade.create_project(self.principal, name="電商")
        self.system = self.facade.create_system(
            self.principal, project_id=self.project.id, name="前台", project_visible=ALWAYS_VISIBLE
        )

    def tearDown(self):
        close_session(self.db)

    def _attach(self, title, *, status="ready", updated_at=None):
        diagram = make_diagram(self.db, owner=self.alice, title=title)
        diagram.system_id = self.system.id
        diagram.status = status
        self.db.commit()
        if updated_at is not None:
            # 以原始 SQL 寫固定時間：ORM 的 onupdate 會把它蓋成 now()。
            self.db.execute(
                text("UPDATE user_diagrams SET updated_at = :t WHERE id = :i"),
                {"t": updated_at, "i": diagram.id},
            )
            self.db.commit()
        return diagram.id


class ListDiagramsOfSystemDraftsTest(_HierarchyFixture):
    def test_include_drafts_is_required_at_both_layers(self):
        """
        @purpose ADR-005：呼叫端必須明示要不要包含草稿；漏寫要在呼叫時就失敗，
                 不得默默用某個預設值（FR6.4c）。
        @given 一個系統
        @step 呼叫 service 與 facade 的 list_diagrams_of_system 但不傳 include_drafts | 兩者皆 TypeError
        @pass 兩層都拋出 TypeError
        @story FR6.4c
        """
        with self.assertRaises(TypeError):
            hierarchy_service.list_diagrams_of_system(
                self.db, system_id=self.system.id, owner_user_id=self.alice.id
            )
        with self.assertRaises(TypeError):
            self.facade.list_diagrams_of_system(self.principal, system_id=self.system.id)

    def test_true_includes_drafts_and_false_excludes_them(self):
        """
        @purpose 同一個列圖函式要同時服務「包含草稿」與「排除草稿」兩種用途（ADR-007）。
        @given 系統下一張正式圖、一張草稿
        @step include_drafts=True | 兩張都在，狀態欄如實
        @step include_drafts=False | 只有正式圖
        @pass 兩種結果的 id 集合正確
        @story FR6.4b、FR6.4c
        """
        ready = self._attach("正式", updated_at="2026-01-01 00:00:00")
        draft = self._attach("草稿", status=DIAGRAM_STATUS_DRAFT, updated_at="2026-01-02 00:00:00")

        included = self.facade.list_diagrams_of_system(
            self.principal, system_id=self.system.id, include_drafts=True
        )
        excluded = self.facade.list_diagrams_of_system(
            self.principal, system_id=self.system.id, include_drafts=False
        )
        self.assertEqual(
            [(draft, "草稿", "draft"), (ready, "正式", "ready")], [r[:3] for r in included]
        )
        self.assertEqual([(ready, "正式", "ready")], [r[:3] for r in excluded])

    def test_order_is_newest_first_with_id_descending_tie_break(self):
        """
        @purpose 契約 C5 的排序：updated_at 降冪，相同時 diagram_id 降冪；反問候選
                 與「新到舊」的呈現都依賴它，必須決定性。
        @given 三張圖：最舊的一張、以及兩張 updated_at 相同的較新圖
        @step 列出 | 較新兩張依 id 降冪在前，最舊一張在最後
        @pass 順序完全等於預期；第四欄為 updated_at
        @story FR3.6
        """
        old = self._attach("舊", updated_at="2025-12-31 00:00:00")
        tie_a = self._attach("同時甲", updated_at="2026-02-01 00:00:00")
        tie_b = self._attach("同時乙", updated_at="2026-02-01 00:00:00")

        rows = self.facade.list_diagrams_of_system(
            self.principal, system_id=self.system.id, include_drafts=True
        )
        self.assertEqual([tie_b, tie_a, old], [r[0] for r in rows])
        self.assertIsNotNone(rows[0][3])
        self.assertGreater(tie_b, tie_a)

    def test_diagrams_without_updated_at_sort_last_on_every_dialect(self):
        """
        @purpose build-and-test 在本機一次性 PostgreSQL 17 實測：`ORDER BY updated_at DESC`
                 不帶 NULLS 子句時，PostgreSQL 把沒有更新時間的圖排在**最前**、SQLite 排最後，
                 使反問候選的前 10 筆在正式環境與測試環境不同。SQLite 本身就把 NULL 排後，
                 所以只看結果抓不到 PostgreSQL 的差異——另外鎖住送出的 SQL 明訂 NULLS LAST。
        @given 一張有更新時間的圖、一張 updated_at 為 NULL 的圖
        @step 列出並攔下送出的 SQL | NULL 的那張在最後，且 ORDER BY 含 NULLS LAST
        @pass 順序為 [有時間, NULL]，SQL 含 "NULLS LAST"
        @story FR3.6
        """
        from sqlalchemy import event

        dated = self._attach("有時間", updated_at="2026-01-01 00:00:00")
        undated = self._attach("沒有時間")
        self.db.execute(
            text("UPDATE user_diagrams SET updated_at = NULL WHERE id = :i"), {"i": undated}
        )
        self.db.commit()

        statements = []

        def capture(_conn, _cursor, statement, *_args):
            statements.append(statement)

        engine = self.db.get_bind()
        event.listen(engine, "before_cursor_execute", capture)
        try:
            rows = self.facade.list_diagrams_of_system(
                self.principal, system_id=self.system.id, include_drafts=True
            )
        finally:
            event.remove(engine, "before_cursor_execute", capture)

        self.assertEqual([dated, undated], [r[0] for r in rows])
        ordered = [s for s in statements if "FROM user_diagrams" in s and "ORDER BY" in s]
        self.assertTrue(ordered, "沒有攔到列圖查詢")
        self.assertIn("NULLS LAST", ordered[-1].upper())


class DraftsCountAsDiagramsTest(_HierarchyFixture):
    def test_system_with_only_a_draft_cannot_be_deleted(self):
        """
        @purpose FR6.4b：刪除系統的檢查必須把草稿算進去，否則只有草稿的系統會通過
                 檢查、再撞上資料庫的 ON DELETE RESTRICT（使用者看到 500 而非說明）。
        @given 系統下只有一張草稿
        @step 刪除該系統 | 拋出 HierarchyConflictError，訊息說仍有 1 張架構圖
        @pass 系統仍存在
        @story FR6.4b
        """
        self._attach("只有草稿", status=DIAGRAM_STATUS_DRAFT)
        with self.assertRaises(HierarchyConflictError) as ctx:
            hierarchy_service.delete_system(self.db, system_id=self.system.id)
        self.assertIn("1 張架構圖", str(ctx.exception))
        self.db.rollback()
        self.assertEqual(
            1, self.db.query(System).filter(System.id == self.system.id).count()
        )

    def test_default_project_holding_only_drafts_is_not_purged(self):
        """
        @purpose FR6.4b：刪除使用者時「可一併清除的空預設專案」判斷必須把草稿算成有圖；
                 排除草稿會把仍有草稿的預設專案列入清除。
        @given alice 的預設專案與預設系統，系統下只有一張草稿
        @step 計算可清除的預設專案 | 不含該專案
        @step 把草稿刪掉再算一次 | 含該專案（對照組：證明判斷真的看圖）
        @pass 有草稿時不清除、無圖時清除
        @story FR6.4b
        """
        default_project = self.facade.create_project(self.principal, name="預設")
        default_project.is_default = True
        self.db.commit()
        default_system = self.facade.create_system(
            self.principal, project_id=default_project.id, name="預設系統",
            project_visible=ALWAYS_VISIBLE,
        )
        draft = make_diagram(self.db, owner=self.alice, title="草稿")
        draft.system_id = default_system.id
        draft.status = DIAGRAM_STATUS_DRAFT
        self.db.commit()

        self.assertNotIn(default_project.id, _empty_default_project_ids(self.db, self.alice.id))

        self.db.delete(draft)
        self.db.commit()
        self.assertIn(default_project.id, _empty_default_project_ids(self.db, self.alice.id))


if __name__ == "__main__":
    unittest.main()
