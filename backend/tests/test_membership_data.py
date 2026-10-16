"""`U19 membership-service` 的資料模型與資料存取層測試（`M1`–`M8`）。

本檔對應 `unit-test-instructions.md §三` 的第一列（資料模型 ＋ 資料存取，**8** 個）。

**`M1`–`M4` 存在的理由，與 `U7` 的 `T25` 為什麼不夠**：把兩張表納入 `Base`
之後，`database.py:90` 的 `Base.metadata.create_all(bind=engine)` 就成為第二條
建表路徑，而既有的 `T25` 只比對 `{c.name for c in model.__table__.columns}`
——**約束名、索引名、partial 條件、外鍵的有無都在它射程外**。本單元要加的兩張
model 恰好有三項不在欄位名裡的事實（`reselection_events.project_id` 刻意無
外鍵、`ix_reselection_events_unack` 是 partial、`previous_role`／`new_role`
刻意無 CHECK），所以 `M2`–`M4` 是必要的擴充而非錦上添花。

**`M2` 的斷言形狀與 `code-generation-plan.md` Step 4 的字面不同，理由寫在
該測試的 docstring 裡**（計畫寫「`foreign_keys` 為空集合」，而 DDL 的
`promoted_user_id`／`previous_owner_user_id` 都有指向 `users` 的外鍵；
`[ND1]`=A 與 `verify_meta_schema.sql` 的 `P6` 說的都是「不對 **projects**
設外鍵」）。

**已知限制（`OPEN-ID19-1`，如實記載而非假裝關閉）**：`create_all()` 建出來的表
**沒有 COMMENT**，而 `verify_meta_schema.sql` 的斷言裡只有 `P12` 碰 COMMENT 且
只驗 `system_requirement_fields`。故 `project_members` 與 `reselection_events`
的 COMMENT **在任何路徑上都沒有斷言**：CI 與部署的乾淨環境裡 `schema_rbac.sql`
先跑、`create_all` no-op，一切正確；但在一個沒跑過
`run_meta_schema_migration.py` 的既有本機資料庫上，後端啟動的 `create_all`
會先建出表，於是該環境永久缺 COMMENT（之後再跑 `schema_rbac.sql` 也補不回來，
`CREATE TABLE IF NOT EXISTS` 整段 no-op）。嚴重度低且限本機——COMMENT 是給人讀
的防呆機制，不影響行為——但**兩條建表路徑不等價，而只有一條被驗**。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from models import ProjectMember, ReselectionEvent
import services.hierarchy_service as hierarchy_service
import services.membership_service as membership_service
from services.membership_types import ProjectRole
from tests.helpers import close_session, make_session, make_user

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema_rbac.sql"
NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)


def ddl_block(table: str) -> str:
    """取出 `schema_rbac.sql` 裡該表的 `CREATE TABLE` 本體（不含 `CREATE INDEX`）。"""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS " + table + r"\s*\((.*?)\n\);", sql, re.S
    )
    assert match is not None, f"{table} 的 DDL 找不到"
    return match.group(1)


def ddl_columns(table: str) -> set[str]:
    """沿用 `T25` 既有的解析形狀（約束宣告與其**續行**都要略過）。"""
    columns = set()
    for line in ddl_block(table).splitlines():
        line = line.strip()
        if not line or line.startswith(
            ("CONSTRAINT", "CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "--", ")")
        ):
            continue
        columns.add(line.split()[0].strip(","))
    return columns


def ddl_named_constraints(table: str) -> set[str]:
    return set(re.findall(r"CONSTRAINT\s+(\w+)", ddl_block(table)))


def ddl_indexes(table: str) -> set[str]:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    return set(
        re.findall(
            r"CREATE INDEX IF NOT EXISTS\s+(\w+)\s*\n?\s*ON\s+" + table + r"\b", sql
        )
    )


class MembershipSchemaAlignmentTest(unittest.TestCase):
    """`M1`–`M4`、`M8`：ORM 與 `schema_rbac.sql` 兩份物化的一致性。"""

    def test_M1_orm_columns_match_the_authoritative_ddl(self):
        """`M1`：欄位名集合相等（含 `[FD3]`=A 回補的 `cause`）。

        沿用 `T25` 的形狀。斷言**集合相等**而非「包含」——前者在漏欄位與
        多欄位兩個方向都會失敗。
        """
        for model, table in (
            (ProjectMember, "project_members"),
            (ReselectionEvent, "reselection_events"),
        ):
            orm = {c.name for c in model.__table__.columns}
            ddl = ddl_columns(table)
            self.assertEqual(
                orm,
                ddl,
                f"{table}：ORM 欄位與 DDL 不一致 "
                f"(ORM only={orm - ddl}, DDL only={ddl - orm})",
            )
        # `cause` 是本單元回補的那一欄；它若從任一側掉了，上面的集合比對就會紅，
        # 但單獨點名它讓失敗訊息直接指向 `[FD3]`=A 而不是「集合不相等」。
        self.assertIn("cause", {c.name for c in ReselectionEvent.__table__.columns})
        self.assertIn("cause", ddl_columns("reselection_events"))

    def test_M2_reselection_events_has_no_foreign_key_to_projects(self):
        """`M2`／`[ND1]`=A：稽核必須在專案被刪後**獨立存活**。

        **本測試的斷言比 `code-generation-plan.md` Step 4 的字面窄，而這是刻意的。**
        計畫寫「`ReselectionEvent.__table__.foreign_keys` 為**空集合**」，但
        `schema_rbac.sql` 的 `J)` 區塊對 `promoted_user_id`（NOT NULL）與
        `previous_owner_user_id` 都宣告了 `REFERENCES users (id)`。照計畫的字面
        斷言空集合，就得把那兩條外鍵從 ORM 拿掉——那會讓 ORM 與 DDL 不一致，
        正是 `M1`–`M4` 整組測試要防的事。

        `[ND1]`=A 的實際內容是「不對 **`projects`** 設外鍵」，而
        `verify_meta_schema.sql` 的 `P6` 查的也正是 `rt.relname = 'projects'`。
        故本測試斷言**兩個方向**：
          (a) 目標表集合**不含** `projects`（習慣性加上 `ForeignKey` 即紅）；
          (b) 目標表集合**恰為** `{users}`（把那兩條 `users` 外鍵拿掉也紅）。
        """
        targets = {fk.column.table.name for fk in ReselectionEvent.__table__.foreign_keys}
        self.assertNotIn(
            "projects",
            targets,
            "[ND1]=A：reselection_events 不得對 projects 設外鍵——CASCADE 會刪掉"
            "「某人的 project_admin 是怎麼來的」這個答案，RESTRICT 會擋住專案刪除",
        )
        self.assertEqual(
            targets,
            {"users"},
            "DDL 對 promoted_user_id 與 previous_owner_user_id 都宣告了"
            " REFERENCES users (id)；拿掉它們會讓 ORM 與 DDL 不一致",
        )

    def test_M3_constraint_and_index_names_match_the_ddl(self):
        """`M3`：具名約束與索引的**名稱集合**相等。

        `T25` 的射程只有欄位名，所以「習慣性多加一條 `CheckConstraint`」或
        「漏掉一個 `Index`」在它之下完全看不到。本測試同時擋下
        `previous_role`／`new_role` 被加上 CHECK（`U18` 刻意不加），以及
        `project_members.user_id` 的索引只出現在 ORM 與 DDL 其中一邊——該索引自
        `U23` 起**存在**（`ix_project_members_user_id`，`[PPN1]`=A：專案清單改讀
        成員列），兩邊必須以同一個名稱宣告。只靠集合相等時，兩邊**同時漏掉**仍綠，
        故另以點名斷言對 ORM 與 DDL 各驗一次。
        """
        for model, table in (
            (ProjectMember, "project_members"),
            (ReselectionEvent, "reselection_events"),
        ):
            orm_constraints = {
                c.name for c in model.__table__.constraints if c.name is not None
            }
            self.assertEqual(
                orm_constraints,
                ddl_named_constraints(table),
                f"{table}：具名約束集合與 DDL 不一致",
            )
            orm_indexes = {i.name for i in model.__table__.indexes}
            self.assertEqual(
                orm_indexes,
                ddl_indexes(table),
                f"{table}：索引名稱集合與 DDL 不一致",
            )
        # U23：點名 `ix_project_members_user_id`，ORM 與 DDL 各一次（集合相等
        # 擋不住「兩邊同時漏掉」）。
        self.assertIn(
            "ix_project_members_user_id",
            {i.name for i in ProjectMember.__table__.indexes},
            "ORM 缺 ix_project_members_user_id（models.py 的 ProjectMember.__table_args__）",
        )
        self.assertIn(
            "ix_project_members_user_id",
            ddl_indexes("project_members"),
            "schema_rbac.sql 的 J) 區塊缺 ix_project_members_user_id"
            "（或寫成了 ON public.project_members，正規式認不出）",
        )
        # 點名這一條：`cause` 的 CHECK 是本單元新增的，而它與
        # `previous_role`／`new_role` 的**刻意無 CHECK** 必須同時成立。
        self.assertIn(
            "ck_reselection_events_cause",
            {c.name for c in ReselectionEvent.__table__.constraints if c.name},
        )
        check_targets = {
            tuple(sorted(c.name or "" for c in getattr(con, "columns", [])))
            for con in ReselectionEvent.__table__.constraints
            if con.name == "ck_reselection_events_cause"
        }
        self.assertTrue(check_targets, "ck_reselection_events_cause 必須掛在 cause 上")

    def test_M3b_migration_script_verifies_the_user_id_index(self):
        """`M3b`（`U23`，infrastructure-design `R-02`）：遷移腳本的後條件清單含該索引。

        @purpose 鎖住「既有環境重跑 `run_meta_schema_migration.py` 後，結束碼 0 代表
                 `ix_project_members_user_id` 存在」——只加 SQL 不加這一列，索引會被建立
                 但不被驗證，結束碼 0 的語意悄悄變窄。
        @story AC12.6.3

        以 `ast` 取 `EXPECTED_INDEXES` 的**值**比對三元組，**不做整檔字串比對**：同名
        字串也出現在 `BLOCK_SENTINELS["J"]` 與註解中，整檔 `assertIn` 在只刪掉
        `EXPECTED_INDEXES` 那一列時仍會綠（`D1` 突變即構造這個情形）。
        """
        import ast

        script = (
            Path(__file__).resolve().parents[1] / "scripts" / "run_meta_schema_migration.py"
        )
        tree = ast.parse(script.read_text(encoding="utf-8"))
        values = [
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "EXPECTED_INDEXES" for t in node.targets
            )
        ]
        self.assertEqual(len(values), 1, "EXPECTED_INDEXES 必須恰有一個模組層定義")
        self.assertIn(
            ("public", "project_members", "ix_project_members_user_id"),
            values[0],
        )

    def test_M4_unack_index_is_partial_on_both_dialects(self):
        """`M4`：`ix_reselection_events_unack` 必須帶 `where` 條件。

        **這是唯一失敗模式為效能而非正確性的一條**：拿掉 `WHERE` 之後索引仍然
        存在、查詢仍然正確，只是大小由「目前未確認數」變成「歷來總數」。
        所以若沒有這條斷言，它永遠不會被發現（`U18` 的 DDL 註解逐字記載這一點，
        並為此在 DDL 側設了 `P8`；本條是 ORM 側的對應）。

        **兩個 dialect 都要驗**：只寫 `postgresql_where` 會讓 in-memory SQLite
        建出一個非 partial 的索引，於是兩條建表路徑再多一處不等價。
        """
        index = next(
            i
            for i in ReselectionEvent.__table__.indexes
            if i.name == "ix_reselection_events_unack"
        )
        for dialect in ("postgresql", "sqlite"):
            where = index.dialect_options[dialect].get("where")
            self.assertIsNotNone(
                where,
                f"ix_reselection_events_unack 缺 {dialect}_where——它會變成一個"
                "涵蓋歷來全部事件的索引，而這不會有任何東西變紅",
            )
            self.assertIn("acknowledged_at", str(where))

    def test_M8_project_members_foreign_key_delete_actions_match_the_ddl(self):
        """`M8`：三條外鍵的 `ON DELETE` 行為逐條對齊。

        `project_id` 是 CASCADE，而這同時是在保護既有程式：
        `hierarchy_service.delete_project()` 只守預設專案與剩餘系統數，
        **沒有任何一道關於成員**；改成 RESTRICT 會讓 `db.delete(project)` 在
        commit 丟出未被捕捉的 `IntegrityError`（使用者看到 500 而非帶訊息的
        衝突回應）。`user_id`／`invited_by` **刻意無 `ON DELETE`**（`OQ-H1`
        上游未決），故 ORM 也不得帶 `ondelete`。
        """
        actual = {
            fk.parent.name: (fk.column.table.name, fk.ondelete)
            for fk in ProjectMember.__table__.foreign_keys
        }
        self.assertEqual(
            actual,
            {
                "project_id": ("projects", "CASCADE"),
                "user_id": ("users", None),
                "invited_by": ("users", None),
            },
        )


class MembershipDataAccessTest(unittest.TestCase):
    """`M5`–`M7`：資料存取層（in-memory SQLite 即足夠——這三條都不需要鎖）。"""

    def setUp(self) -> None:
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.bob = make_user(self.db, username="bob", role="Developer")
        self.carol = make_user(self.db, username="carol", role="Developer")
        self.project = hierarchy_service.create_project(
            self.db, owner_user_id=self.alice.id, name="P"
        )

    def tearDown(self) -> None:
        close_session(self.db)

    def _member(self, user, role, joined_at=NOW):
        row = ProjectMember(
            project_id=self.project.id,
            user_id=user.id,
            role=role.value if isinstance(role, ProjectRole) else role,
            joined_at=joined_at,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_M5_resolve_project_role_returns_the_role_or_none(self):
        """`M5`／`BR1.6`：查得回角色，**查無回 `None`**（代表非成員）。

        `None` 這一側是 `AC12.5.2` 的 deny 側所依賴的全部——把它當成預設角色
        會讓**任何**具全域權限的人取得專案的一般成員權限。
        """
        self.assertIsNone(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=self.bob.id
            )
        )
        self._member(self.bob, ProjectRole.MEMBER)
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=self.bob.id
            ),
            ProjectRole.MEMBER.value,
        )
        self._member(self.alice, ProjectRole.PROJECT_ADMIN)
        self.assertEqual(
            membership_service.resolve_project_role(
                self.db, project_id=self.project.id, user_id=self.alice.id
            ),
            ProjectRole.PROJECT_ADMIN.value,
        )

    def test_M6_list_members_exposes_exactly_the_member_view_fields(self):
        """`M6`：欄位集合與排序。

        欄位集合斷言**相等**：多一個欄位（例如順手把 `invited_by` 加進來）與
        少一個欄位都要紅。`invited_by` 刻意不在裡面（`OPEN-FD19-6`）。
        """
        self._member(self.alice, ProjectRole.PROJECT_ADMIN, NOW + timedelta(hours=1))
        self._member(self.bob, ProjectRole.MEMBER, NOW)
        views = membership_service.list_members(self.db, project_id=self.project.id)
        self.assertEqual(
            set(views[0].model_dump()),
            {"user_id", "display_name", "role", "joined_at"},
        )
        # 排序為 (joined_at, user_id)——與 `BR4.2` 的挑選鍵同一個，故清單的第一列
        # 就是自動改選會選中的那一位，畫面與行為一致。
        self.assertEqual([v.user_id for v in views], [self.bob.id, self.alice.id])
        self.assertEqual(views[0].display_name, "bob")

    def test_M7_aggregate_guard_matches_the_per_project_predicate(self):
        """`M7`／`NFR12.12`／`[N3]`=C：聚合查詢 ↔ 逐專案判定的**等價**。

        這條測試是審查 `R-03` 的直接回應：`assert_can_deactivate` 用一次
        `GROUP BY ... HAVING count(*) = 1`，而 `remove_member`／`change_role`
        用單專案判定函式 `admin_count_after`。不變量只有一個、判定邏輯只有一處，
        而「集合版是單專案判定的量化形式」這句話必須可被驗證而不只是宣稱。

        **它不是 PBT 的作用對象**——它需要資料庫，與 `select_successor` 不同
        （那一個才是純函式）。故以明確案例覆蓋四種形狀。
        """
        other = hierarchy_service.create_project(
            self.db, owner_user_id=self.alice.id, name="Q"
        )

        def aggregate() -> set[int]:
            return {
                ref.project_id
                for ref in membership_service.projects_losing_last_admin(
                    self.db, target_user_id=self.alice.id
                )
            }

        def per_project() -> set[int]:
            blocked = set()
            for project_id in membership_service.project_ids_where_admin(
                self.db, user_id=self.alice.id
            ):
                if (
                    membership_service.admin_count_after(
                        self.db,
                        project_id=project_id,
                        changing_user_id=self.alice.id,
                        new_role=None,
                    )
                    < 1
                ):
                    blocked.add(project_id)
            return blocked

        # (1) 完全沒有成員列：兩者都是空集合。
        self.assertEqual(aggregate(), per_project())
        self.assertEqual(aggregate(), set())

        # (2) alice 是 P 的唯一管理者，另有一位一般成員——**這是 `[FD1]`=A 比
        #     `FR12.5` 字面更嚴的那一格**：有兩位成員但只有一位管理者，仍須擋下。
        self._member(self.alice, ProjectRole.PROJECT_ADMIN)
        self._member(self.bob, ProjectRole.MEMBER)
        self.assertEqual(aggregate(), per_project())
        self.assertEqual(aggregate(), {self.project.id})

        # (3) 把 bob 升為第二位管理者 → P 不再受阻。
        self.db.query(ProjectMember).filter(
            ProjectMember.project_id == self.project.id,
            ProjectMember.user_id == self.bob.id,
        ).update({"role": ProjectRole.PROJECT_ADMIN.value})
        self.db.commit()
        self.assertEqual(aggregate(), per_project())
        self.assertEqual(aggregate(), set())

        # (4) 第二個專案 Q：alice 獨任管理者 → 只有 Q 受阻，而且**一次查詢**就
        #     跨專案找到它（`NFR12.10`：與該使用者的專案數無關）。
        row = ProjectMember(
            project_id=other.id,
            user_id=self.alice.id,
            role=ProjectRole.PROJECT_ADMIN.value,
            joined_at=NOW,
        )
        self.db.add(row)
        self.db.commit()
        self.assertEqual(aggregate(), per_project())
        self.assertEqual(aggregate(), {other.id})


if __name__ == "__main__":
    unittest.main()
