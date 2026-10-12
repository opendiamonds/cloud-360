"""`U20 requirement-field-service` 的 HTTP 層測試（`H1`–`H7`，`TestClient`）。

對應 `unit-test-instructions.md §三` 的第五列（API）。`team.md` 規則 A＋B：新端點須有
`TestClient` 測試，授權須 allow／deny 雙向，並斷言 `response_model` 的欄位集合。

不需要真實資料庫：`get_db` 與 `get_current_user` 以 `app.dependency_overrides` 覆寫；
`TestClient(app)` 不觸發 `@app.on_event("startup")`。**不 mock `user_can`**——
權限矩陣由 `ensure_role_permissions_seeded` 播種，真實的授權路徑必須被執行。

`H1` 是十二列 allow／deny 矩陣（`code-generation-plan.md` §二：`security-design.md`
第二節的九列，加上「另一個專案的成員」「`project_admin` 且有 `K4.edit` 的正向寫入」
「`Platform_Admin` 非成員」三列）。每一列的 deny 都同時斷言**對本表 0 條敘述**
（`NFR20.7`：判定先於任何讀寫）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import json
import unittest
import uuid
from unittest.mock import patch

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import SystemRequirementField
from services.auth import get_current_user
from services.hierarchy_facade import mint_principal
from services.membership_facade import MembershipFacade
from tests.helpers import close_session, make_user
from tests.test_requirement_field_facade import RequirementFieldFixture
from tests.test_requirement_field_service import QueryCounter

FIELD_SET_KEYS = {"system_id", "unfilled_count", "input_hint", "groups"}
GROUP_KEYS = {"group_key", "title", "filled_count", "total_count", "fields"}
FIELD_VIEW_KEYS = {
    "group_key", "field_key", "label", "value", "filled_state", "cleared_at",
    "updated_at", "updated_by", "updated_on_behalf_of",
}
MISSING_SYSTEM_ID = 987_654


class RequirementFieldHttpTestBase(RequirementFieldFixture, unittest.TestCase):
    def setUp(self) -> None:
        self.build_fixture()
        # ② 的「完全沒有任何成員身分」的人；⑩ 的 outsider 則是另一個專案的成員。
        self.stranger = make_user(self.db, username="stranger", role="Project_Editor")
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def client_as(self, user, **kwargs) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app, **kwargs)

    def url(self, system_id=None, group="cost", key="sla", *, collection=False):
        sid = self.system.id if system_id is None else system_id
        base = f"/api/requirements/systems/{sid}/fields"
        return base if collection else f"{base}/{group}/{key}"

    def call(self, user, method, *, system_id=None, body=None, group="cost",
             key="sla", **client_kwargs):
        client = self.client_as(user, **client_kwargs)
        if method == "GET":
            return client.get(self.url(system_id, collection=True))
        if method == "PUT":
            return client.put(
                self.url(system_id, group, key),
                json={"value": "99.9%"} if body is None else body,
            )
        return client.delete(self.url(system_id, group, key))

    def row_count(self) -> int:
        return self.db.query(SystemRequirementField).count()


class AuthorizationMatrixTest(RequirementFieldHttpTestBase):
    def test_H1_twelve_row_allow_deny_matrix(self):
        """`H1`／`NFR20.8`／`BR41.1`–`BR41.5`：十二列，每列 GET／PUT／DELETE 的期望狀態碼。

        突變驗證（`unit-test-instructions.md §四`）：拿掉 per-project 成員判定 → ②⑩⑫ 紅；
        拿掉全域 `K4.edit` 檢查 → ③⑤⑨ 紅；拿掉待核准檢查 → ⑥ 紅。
        """
        missing = MISSING_SYSTEM_ID
        rows = [
            # (編號, 使用者, system_id, {方法: 期望}, PUT 本體)
            ("①成員 Project_Editor", self.editor, None,
             {"GET": 200, "PUT": 200, "DELETE": 200}, None),
            ("②非成員 Project_Editor", self.stranger, None,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
            ("③成員 Developer（只有 view）", self.viewer, None,
             {"GET": 200, "PUT": 403, "DELETE": 403}, None),
            ("④成員 SRE（無 K4）", self.no_k4, None,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
            ("⑤project_admin＋Developer", self.admin_viewer, None,
             {"GET": 200, "PUT": 403, "DELETE": 403}, None),
            ("⑥待核准成員 Project_Editor", self.pending, None,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
            ("⑦Project_Editor，系統不存在", self.editor, missing,
             {"GET": 404, "PUT": 404, "DELETE": 404}, None),
            ("⑧SRE，系統不存在", self.no_k4, missing,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
            ("⑨成員 Developer 帶代寫標示", self.viewer, None,
             {"PUT": 403}, {"value": "v", "on_behalf_of": "cost"}),
            ("⑩另一個專案的成員（Project_Editor）", self.outsider, None,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
            ("⑪project_admin＋Project_Architect", self.owner, None,
             {"GET": 200, "PUT": 200, "DELETE": 200}, None),
            ("⑫Platform_Admin 非成員", self.root, None,
             {"GET": 403, "PUT": 403, "DELETE": 403}, None),
        ]
        self.assertEqual(len(rows), 12)
        for label, user, system_id, expected, body in rows:
            for method, status_code in expected.items():
                with self.subTest(row=label, method=method):
                    with QueryCounter(self.db) as counter:
                        response = self.call(user, method, system_id=system_id, body=body)
                    self.assertEqual(response.status_code, status_code, response.text)
                    if status_code in (403, 404):
                        self.assertEqual(counter.table_statements, 0, counter.statements)
                        self.assertEqual(set(response.json()), {"detail"})
                        self.assertIsInstance(response.json()["detail"], str)

    def test_H2_pending_and_unauthorized_callers_get_403_before_any_body_validation(self):
        """`H2`／`BR41.5`：授權先於驗證——壞本體、非整數 id 在無權者手上仍是 403，不是 422／404。"""
        self.assertEqual(
            self.call(self.pending, "PUT", body={"updated_by": 1}).status_code, 403
        )
        self.assertEqual(
            self.call(self.viewer, "PUT", body=["not", "an", "object"]).status_code, 403
        )
        self.assertEqual(self.call(self.no_k4, "GET", system_id="abc").status_code, 403)
        self.assertEqual(self.call(self.editor, "GET", system_id="abc").status_code, 404)
        self.assertEqual(
            self.call(self.editor, "PUT", system_id="12x", body={"value": "v"}).status_code,
            404,
        )


class ResponseShapeTest(RequirementFieldHttpTestBase):
    def test_H3_response_field_sets(self):
        """`H3`／`team.md` 規則 B：三個 `response_model` 的欄位集合與值。"""
        put = self.call(self.editor, "PUT", body={"value": " 99.9% ", "on_behalf_of": "cost"})
        self.assertEqual(put.status_code, 200)
        self.assertEqual(set(put.json()), FIELD_VIEW_KEYS)
        self.assertEqual(
            {k: put.json()[k] for k in ("group_key", "field_key", "label", "value",
                                        "filled_state", "updated_by",
                                        "updated_on_behalf_of", "cleared_at")},
            {"group_key": "cost", "field_key": "sla", "label": "SLA", "value": "99.9%",
             "filled_state": "filled", "updated_by": self.editor.id,
             "updated_on_behalf_of": "cost", "cleared_at": None},
        )

        get = self.call(self.editor, "GET").json()
        self.assertEqual(set(get), FIELD_SET_KEYS)
        self.assertEqual((get["system_id"], get["unfilled_count"]), (self.system.id, 6))
        self.assertEqual(
            [(g["group_key"], g["title"], g["filled_count"], g["total_count"])
             for g in get["groups"]],
            [("cost", "成本 agent", 1, 5), ("architecture", "架構 agent", 0, 2)],
        )
        for group in get["groups"]:
            self.assertEqual(set(group), GROUP_KEYS)
            for field in group["fields"]:
                self.assertEqual(set(field), FIELD_VIEW_KEYS)

        delete = self.call(self.editor, "DELETE")
        self.assertEqual(delete.status_code, 200)
        self.assertEqual(set(delete.json()), FIELD_VIEW_KEYS)
        self.assertEqual(
            (delete.json()["filled_state"], delete.json()["value"],
             delete.json()["updated_on_behalf_of"]),
            ("cleared", None, None),
        )
        self.assertIsNotNone(delete.json()["cleared_at"])

    def test_H4_writes_and_clears_are_idempotent_and_reads_are_constant_cost(self):
        """`H4`／`NFR20.21`／`NFR20.22`／`NFR20.2`／`NFR20.3`。

        連送兩次相同 `PUT` → 皆 200、列數 1；連送兩次 `DELETE` → 第二次的 `cleared_at`
        與第一次相同；整個 `GET` 的總查詢數在 0 列與 7 列兩種資料下相等；本 router 只有
        一個 GET 操作（沒有「只回計數」的端點）。
        """
        with QueryCounter(self.db) as empty:
            self.call(self.editor, "GET")
        for _ in range(2):
            self.assertEqual(self.call(self.editor, "PUT").status_code, 200)
        self.assertEqual(self.row_count(), 1)
        first = self.call(self.editor, "DELETE").json()
        second = self.call(self.editor, "DELETE").json()
        self.assertEqual(second["cleared_at"], first["cleared_at"])
        self.assertEqual(second["filled_state"], "cleared")

        for group, keys in (("cost", ("sla", "peak_tps", "user_base",
                                      "monthly_budget_cap", "billing_region")),
                            ("architecture", ("availability_target", "data_retention"))):
            for key in keys:
                self.call(self.editor, "PUT", group=group, key=key)
        self.assertEqual(self.row_count(), 7)
        with QueryCounter(self.db) as full:
            self.call(self.editor, "GET")
        self.assertEqual(full.total, empty.total)
        self.assertEqual(full.selects, 1)

        get_operations = [
            path for path, item in app.openapi()["paths"].items()
            if path.startswith("/api/requirements") and "get" in item
        ]
        self.assertEqual(get_operations, ["/api/requirements/systems/{system_id}/fields"])


class ValidationAndFailureTest(RequirementFieldHttpTestBase):
    def test_H5_four_kinds_of_422_do_not_echo_the_input(self):
        """`H5`／`NFR20.12`／`NFR20.14`／`NFR20.10`／`BR46.3`／`BR46.4`。

        錯綁別組、超長值、未宣告的代寫組、本體帶 `updated_by`：皆 422、本體只有字串
        `detail`、不含送出的唯一標記；且沒有任何列被寫入。
        """
        marker = f"marker-{uuid.uuid4()}"
        cases = {
            "錯綁別組": dict(group="architecture", key="sla", body={"value": marker}),
            "超長值": dict(body={"value": marker + "x" * 2000}),
            "未宣告的代寫組": dict(body={"value": "v", "on_behalf_of": marker}),
            "本體帶 updated_by": dict(body={"value": "v", "updated_by": marker}),
        }
        for label, kwargs in cases.items():
            with self.subTest(case=label):
                response = self.call(self.editor, "PUT", **kwargs)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(set(response.json()), {"detail"})
                self.assertIsInstance(response.json()["detail"], str)
                self.assertNotIn(marker, response.text)
        self.assertEqual(self.row_count(), 0)

        # 本體不是 JSON、缺 value、空白的代寫值、DELETE 未宣告欄位：同一種 422 形狀。
        client = self.client_as(self.editor)
        for response in (
            client.put(self.url(), content=b"{not json",
                       headers={"content-type": "application/json"}),
            client.put(self.url(), json={}),
            client.put(self.url(), json={"value": "  ", "on_behalf_of": "cost"}),
            client.delete(self.url(group="cost", key="nope")),
        ):
            with self.subTest(body=response.request.content[:20]):
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIsInstance(response.json()["detail"], str)

    def test_H6_dependency_failures_return_500_without_writes(self):
        """`H6`／`NFR20.11`／`NFR20.26`：依賴拋非預期例外 → 500，無寫入、無計數。

        `raise_server_exceptions=False`：否則 `TestClient` 會把伺服器例外直接重拋到測試，
        看不到 500 回應（nfr-requirements `review-01` R-03）。
        """
        with patch(
            "services.requirement_field_facade.MembershipFacade.resolve_project_role",
            side_effect=RuntimeError("membership store unavailable"),
        ):
            response = self.call(self.editor, "PUT", raise_server_exceptions=False)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.row_count(), 0)

        with patch(
            "services.requirement_field_service.fetch_rows",
            side_effect=RuntimeError("database unavailable"),
        ):
            response = self.call(self.editor, "GET", raise_server_exceptions=False)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("unfilled_count", response.text)

    def test_H7_project_admin_and_member_roles_both_write(self):
        """`H7`／`BR41.4`／`[FD4]`=A：per-project 角色不區分讀寫——`member` 與 `project_admin`
        只要全域有 `K4.edit` 都寫得進去（把 `BR41.4` 寫成「只放行 member」或「只放行
        project_admin」的突變在這裡紅）。"""
        MembershipFacade(self.db).change_role(
            mint_principal(self.owner),
            project_id=self.project.id, user_id=self.editor.id, role="project_admin",
        )
        self.assertEqual(
            self.call(self.editor, "PUT", body={"value": "as admin"}).status_code, 200
        )
        self.assertEqual(
            self.call(self.owner, "PUT", key="peak_tps",
                      body={"value": json.dumps({"tps": 1200})}).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
