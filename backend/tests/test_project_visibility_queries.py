"""`U23 project-pages-ui` 的可見性謂詞與列舉語句數測試。

兩組：

- `VisibilityPredicateTest`（7 案）：`membership_service.visible_project_ids` 與
  `is_project_visible` 對五種身分的結果（`BR87.1`、`[PP3]`=A）。這兩支是可見性的
  **唯一**公開入口，兩者都只由 `_visible_project_ids_select` 組出。
- `ListingStatementCountTest`（2 案）：兩支列舉端點的 SQL 語句數與可見專案數 P、
  系統數 S 無關（`PPN-06`）。

`VisibilityWorld` 是本單元三支後端測試共用的資料構造（身分的定義見
`unit-test-instructions.md` §六、`security-design.md` §二之三／§三）。放在本檔而
不另開模組：計畫列出的新增檔就是這四支，不多開第五支。

**授權不 mock**：走真實的 `MembershipFacade`、`membership_service` 與 `user_can`，
只以 in-memory SQLite 取代資料庫。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from sqlalchemy import event
from starlette.testclient import TestClient

from database import get_db
from main import app
from models import Project, ProjectMember, System
import services.membership_service as membership_service
from services.auth import get_current_user
from services.hierarchy_facade import mint_principal
from services.membership_facade import MembershipFacade
from tests.helpers import close_session, make_session, make_user

ROLE_K2_EDIT = "Project_Editor"       # K2 view+edit、K3 view+edit、K4 view+edit
ROLE_K2_VIEW_ONLY = "Developer"       # K2 view=True、edit=False
ROLE_NON_CANONICAL = "Not_A_Canonical_Role"  # 全部 11 個 canonical role 的 K2 view 皆為 True


class VisibilityWorld:
    """五種身分與它們各自的目標專案。

    | 身分 | 使用者 | 目標專案 | 構造 |
    |---|---|---|---|
    | ① 擁有者且有成員列 | `owner` | `p1` | `create_project_with_owner`（同交易寫入建立者的 `project_admin`） |
    | ② 成員 | `member` | `p1` | ORM 為他加一筆 `member` 列 |
    | ③ **另一專案的成員** | `other_member` | `p1` | 他是 `p_other` 的成員、**不是** `p1` 的 |
    | ④ 被移出的擁有者 | `removed_owner` | `p4` | 建立 → ORM 為 `admin2` 寫 `project_admin` → ORM 刪除建立者的列 |
    | ⑤ 零成員列專案的擁有者 | `zero_owner` | `p5` | ORM 直接建 `Project`、不寫成員列（模擬回填前） |

    ③ 必須是「**另一專案的**成員」而不是「完全沒有成員列的人」：可見性子句漏掉與
    目標專案的關聯（有任何成員列即可見）時，後者照樣看不到，測試會綠
    （functional-design `R-03`）。

    ④ 的構造與真實的「另一位管理者把建立者移出」是同一個資料狀態：`owner_user_id`
    仍是建立者、該專案有成員列而建立者不在其中（`functional-spec.md` §四之二）。
    """

    def __init__(self, db) -> None:
        self.db = db
        self.owner = make_user(db, username="owner", role=ROLE_K2_EDIT)
        self.member = make_user(db, username="member", role=ROLE_K2_EDIT)
        self.other_member = make_user(db, username="other_member", role=ROLE_K2_EDIT)
        self.removed_owner = make_user(db, username="removed_owner", role=ROLE_K2_EDIT)
        self.zero_owner = make_user(db, username="zero_owner", role=ROLE_K2_EDIT)
        self.admin2 = make_user(db, username="admin2", role=ROLE_K2_EDIT)
        self.stranger = make_user(db, username="stranger", role=ROLE_K2_EDIT)
        self.developer = make_user(db, username="developer", role=ROLE_K2_VIEW_ONLY)
        self.noncanon = make_user(db, username="noncanon", role=ROLE_NON_CANONICAL)

        facade = MembershipFacade(db)
        # ① ＋ ②
        self.p1 = facade.create_project_with_owner(mint_principal(self.owner), name="P1")
        self.add_member(self.p1, self.member, "member")
        # ③：另一專案的成員
        self.p_other = facade.create_project_with_owner(
            mint_principal(self.admin2), name="P-other"
        )
        self.add_member(self.p_other, self.other_member, "member")
        # ④：被移出的擁有者
        self.p4 = facade.create_project_with_owner(
            mint_principal(self.removed_owner), name="P4"
        )
        self.add_member(self.p4, self.admin2, "project_admin")
        db.query(ProjectMember).filter(
            ProjectMember.project_id == self.p4.id,
            ProjectMember.user_id == self.removed_owner.id,
        ).delete()
        db.commit()
        # ⑤：零成員列專案的擁有者
        self.p5 = Project(name="P5", owner_user_id=self.zero_owner.id, is_default=False)
        db.add(self.p5)
        db.commit()
        db.refresh(self.p5)

    def add_member(self, project, user, role: str) -> None:
        self.db.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
        self.db.commit()

    def add_system(self, project, name: str) -> System:
        system = System(project_id=project.id, name=name, is_default=False)
        self.db.add(system)
        self.db.commit()
        self.db.refresh(system)
        return system

    def never_existed_project_id(self) -> int:
        """從未存在的 id：`max(id)+1000`（`security-design.md` §一之三）。"""
        top = max(p.id for p in self.db.query(Project).all())
        return top + 1000

    def never_existed_system_id(self) -> int:
        ids = [s.id for s in self.db.query(System).all()]
        return (max(ids) if ids else 0) + 1000


class VisibilityTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.w = VisibilityWorld(self.db)

    def tearDown(self) -> None:
        close_session(self.db)

    def visible(self, user) -> list:
        return membership_service.visible_project_ids(self.db, user_id=user.id)

    def is_visible(self, project, user) -> bool:
        return membership_service.is_project_visible(
            self.db, project_id=project.id, user_id=user.id
        )


class VisibilityPredicateTest(VisibilityTestBase):
    """`BR87.1`：可見集合 ＝ 成員列 ∪（擁有者 且 該專案零成員列）。"""

    def test_V1_owner_with_member_row_sees_project(self):
        """① 擁有者且有成員列。

        @purpose 建立者（同交易寫入 `project_admin` 列）看得到自己的專案。
        @story AC12.6.3
        """
        self.assertIn(self.w.p1.id, self.visible(self.w.owner))
        self.assertTrue(self.is_visible(self.w.p1, self.w.owner))

    def test_V2_invited_member_sees_project(self):
        """② 被邀請的成員（非擁有者）。`M1`（拿掉成員那一半）使本案紅。

        @purpose 成員列是可見性的主要來源：被邀請的成員看得到專案。
        @story AC12.6.3
        """
        self.assertEqual(self.visible(self.w.member), [self.w.p1.id])
        self.assertTrue(self.is_visible(self.w.p1, self.w.member))

    def test_V3_member_of_another_project_does_not_see_target(self):
        """③ 另一專案的成員。`M6`（漏掉與目標專案的關聯）使本案紅。

        @purpose 「有任何成員列」不等於「看得到這個專案」。
        @story AC12.1.3
        """
        self.assertEqual(self.visible(self.w.other_member), [self.w.p_other.id])
        self.assertNotIn(self.w.p1.id, self.visible(self.w.other_member))
        self.assertFalse(self.is_visible(self.w.p1, self.w.other_member))
        self.assertTrue(self.is_visible(self.w.p_other, self.w.other_member))

    def test_V4_removed_owner_does_not_see_project(self):
        """④ 被移出的擁有者。`M2`（拿掉「零成員列」條件）使本案紅。

        @purpose 被另一位管理者移出的建立者，即使 `owner_user_id` 仍是他，也看不到該專案。
        @story AC12.6.2
        """
        self.assertNotIn(self.w.p4.id, self.visible(self.w.removed_owner))
        self.assertFalse(self.is_visible(self.w.p4, self.w.removed_owner))
        # 對照：留下的管理者看得到——同一專案、同一份資料，結論只取決於成員列。
        self.assertTrue(self.is_visible(self.w.p4, self.w.admin2))

    def test_V5_owner_of_zero_member_project_sees_it(self):
        """⑤ 零成員列專案的擁有者（回填前）。`M3`（拿掉擁有者那一半）使本案紅。

        @purpose 回填未跑時，擁有者仍看得到自己的專案。
        @story AC12.6.3
        """
        self.assertEqual(self.visible(self.w.zero_owner), [self.w.p5.id])
        self.assertTrue(self.is_visible(self.w.p5, self.w.zero_owner))

    def test_V6_unrelated_user_sees_nothing(self):
        """⑥ 既非成員也非擁有者的使用者：可見集合為空，對每個專案皆為否。

        @purpose 可見性不會因為「預設放行」而外洩。
        @story AC12.1.3
        """
        self.assertEqual(self.visible(self.w.stranger), [])
        for project in (self.w.p1, self.w.p_other, self.w.p4, self.w.p5):
            self.assertFalse(self.is_visible(project, self.w.stranger))

    def test_V7_visible_ids_are_ascending_and_union_both_halves(self):
        """可見 id 依遞增排序，且兩半的聯集不重複。

        @purpose 呼叫端依 id 遞增渲染與入列；同一專案同時滿足兩半時只出現一次。
        @story AC12.6.3
        """
        # admin2 是 p_other（建立者）與 p4（被加入）的成員；另讓他擁有一個零成員專案。
        extra = Project(name="P-extra", owner_user_id=self.w.admin2.id, is_default=False)
        self.db.add(extra)
        self.db.commit()
        got = self.visible(self.w.admin2)
        self.assertEqual(got, sorted(got))
        self.assertEqual(got, sorted({self.w.p_other.id, self.w.p4.id, extra.id}))
        self.assertEqual(len(got), len(set(got)))


class ListingStatementCountTest(unittest.TestCase):
    """`PPN-06`：兩支列舉端點的 SQL 語句數與 P、S 無關。

    `before_cursor_execute` 監聽器在 `setUp` 掛上、`tearDown` 以 `event.remove`
    卸除（清除端）。每案先暖身一次（排除首次的 lazy 載入與權限快取差異），歸零後
    再量。
    """

    def setUp(self) -> None:
        self.db = make_session()
        self.engine = self.db._test_engine  # type: ignore[attr-defined]
        self.count = 0

        def _on_execute(conn, cursor, statement, parameters, context, executemany):
            self.count += 1

        self._listener = _on_execute
        event.listen(self.engine, "before_cursor_execute", self._listener)
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        event.remove(self.engine, "before_cursor_execute", self._listener)
        app.dependency_overrides.clear()
        close_session(self.db)

    def measure(self, user, url: str) -> int:
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)
        warm = client.get(url)
        self.assertEqual(warm.status_code, 200, warm.text)
        self.count = 0
        response = client.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        return self.count

    def test_Q_project_list_statement_count_is_independent_of_P(self):
        """專案清單：P＝1 與 P＝8 的語句數相等。

        @purpose 專案清單不得對每個專案各發一次查詢（`Q1`／`Q2` 突變使本案紅）。
        @story AC12.6.3
        @api GET /api/hierarchy/projects
        """
        one = make_user(self.db, username="one", role=ROLE_K2_EDIT)
        eight = make_user(self.db, username="eight", role=ROLE_K2_EDIT)
        facade = MembershipFacade(self.db)
        facade.create_project_with_owner(mint_principal(one), name="only")
        for i in range(8):
            facade.create_project_with_owner(mint_principal(eight), name=f"p{i}")
        c1 = self.measure(one, "/api/hierarchy/projects")
        c8 = self.measure(eight, "/api/hierarchy/projects")
        self.assertEqual(c1, c8, f"P=1 發 {c1} 條、P=8 發 {c8} 條")

    def test_Q_system_list_statement_count_is_independent_of_S(self):
        """系統清單：S＝1 與 S＝8 的語句數相等。

        @purpose 系統清單不得對每個系統各發一次查詢（`Q3` 突變使本案紅）。
        @story AC12.6.3
        @api GET /api/hierarchy/projects/{project_id}/systems
        """
        user = make_user(self.db, username="sys-owner", role=ROLE_K2_EDIT)
        facade = MembershipFacade(self.db)
        small = facade.create_project_with_owner(mint_principal(user), name="small")
        big = facade.create_project_with_owner(mint_principal(user), name="big")
        self.db.add(System(project_id=small.id, name="s0", is_default=False))
        for i in range(8):
            self.db.add(System(project_id=big.id, name=f"s{i}", is_default=False))
        self.db.commit()
        c1 = self.measure(user, f"/api/hierarchy/projects/{small.id}/systems")
        c8 = self.measure(user, f"/api/hierarchy/projects/{big.id}/systems")
        self.assertEqual(c1, c8, f"S=1 發 {c1} 條、S=8 發 {c8} 條")


if __name__ == "__main__":
    unittest.main()
