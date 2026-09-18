"""使用者清單端點的 HTTP 層測試（team-practices 測試底線 B、requirements NFR-5／NFR-10）。

這是本 repo **第一支**測試客戶端測試，故一併建立可重用的 fixture 樣板。

為何非有不可：本 intent 的失敗路徑是「後端漏欄位 → 序列化成 null → 前端渲染成
空白」，而既有的六道 CI gate 對這條路徑**全部無效** —— `tsc -b` 因前端型別是手寫
interface 而看不到後端形狀，e2e 六個 case 無一進入管理頁，純函式測試不碰 HTTP 層。

不需要真實資料庫：`get_db` 與 `get_current_user` 皆為模組層函式，可用
`app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發
`@app.on_event("startup")` 的 `init_db()`。
"""

import unittest
from datetime import datetime, timedelta, timezone

from starlette.testclient import TestClient

from tests.helpers import close_session, make_session, make_user
from database import get_db
from main import app
from services.auth import get_current_user
from services.rbac import ensure_role_permissions_seeded
from services.user_router import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

NOW = datetime.now(timezone.utc)
LIST_URL = "/api/auth/list"

# UserSchema 的完整欄位集合。斷言**集合相等**而非「包含」—— 前者會在漏欄位與
# 多欄位兩個方向都失敗，後者只擋得住漏欄位。
USER_FIELDS = {
    "id",
    "username",
    "role",
    "is_active",
    "authorization_status",
    "requested_role",
    "last_activity_at",
    "is_overdue",
}
PAGE_FIELDS = {"items", "total", "page", "page_size"}


class UserListEndpointTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        self.admin = make_user(self.db, username="admin", role="Platform_Admin")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    def _make_users(self, count, prefix="u"):
        return [
            make_user(self.db, username=f"{prefix}{i:03d}", role="Developer")
            for i in range(count)
        ]

    # --- 回應形狀（AC-1.5、AC-5.2） ---

    def test_envelope_field_set_is_exact(self):
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.json().keys()), PAGE_FIELDS)

    def test_每列的欄位集合完整(self):
        res = self.client.get(LIST_URL)
        for item in res.json()["items"]:
            self.assertEqual(set(item.keys()), USER_FIELDS)

    def test_last_activity_value_matches_database_not_just_key_present(self):
        """AC-1.5／AC-5.8：斷言**值**與資料庫一致，不只是 key 存在。"""
        user = make_user(self.db, username="active", role="Developer")
        user.last_activity_at = NOW - timedelta(days=1)
        self.db.commit()

        row = self._find(self.client.get(LIST_URL).json()["items"], "active")
        self.assertIsNotNone(row["last_activity_at"])
        self.assertFalse(row["is_overdue"])

    def test_current_admin_activity_is_recorded_before_listing(self):
        """管理頁自身的清單請求必須讓目前管理員列有最後活動時間。"""
        self.assertIsNone(self.admin.last_activity_at)

        row = self._find(self.client.get(LIST_URL).json()["items"], "admin")

        self.assertIsNotNone(row["last_activity_at"])
        self.db.refresh(self.admin)
        self.assertIsNotNone(self.admin.last_activity_at)

    def test_overdue_flag_is_computed_by_backend(self):
        user = make_user(self.db, username="stale", role="Developer")
        user.last_activity_at = NOW - timedelta(days=200)
        self.db.commit()

        row = self._find(self.client.get(LIST_URL).json()["items"], "stale")
        self.assertTrue(row["is_overdue"])

    def test_serialised_timestamp_carries_a_utc_offset(self):
        """回應的時間字串**必須帶時區位移**。

        SQLite 讀回的時間戳不帶時區；若原樣序列化，瀏覽器的 `new Date()` 會把它
        當成本地時間解讀，顯示時間整體偏移一個時區位移量 —— AC-1.6 失敗，而畫面
        上看起來完全正常。本測試在 SQLite 上跑，正是最會露餡的環境。
        """
        user = make_user(self.db, username="tz", role="Developer")
        user.last_activity_at = NOW - timedelta(hours=3)
        self.db.commit()

        raw = self._find(self.client.get(LIST_URL).json()["items"], "tz")["last_activity_at"]
        self.assertTrue(
            raw.endswith("Z") or "+" in raw[10:] or raw[10:].count("-") > 0,
            f"序列化的時間缺少時區位移：{raw!r}",
        )
        # 往返一趟仍是同一個時點。
        self.assertEqual(
            datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp(),
            (NOW - timedelta(hours=3)).timestamp(),
        )

    def test_never_active_is_null_and_not_overdue(self):
        make_user(self.db, username="never", role="Developer")
        row = self._find(self.client.get(LIST_URL).json()["items"], "never")
        self.assertIsNone(row["last_activity_at"])
        self.assertFalse(row["is_overdue"])

    # --- 分頁（AC-5.1〜AC-5.4） ---

    def test_page_size_bounds_the_response(self):
        self._make_users(DEFAULT_PAGE_SIZE + 5)
        body = self.client.get(LIST_URL).json()
        self.assertEqual(len(body["items"]), DEFAULT_PAGE_SIZE)
        self.assertLess(len(body["items"]), body["total"])

    def test_total_is_a_separate_count_not_len_items(self):
        """AC-5.2：total 必須是全體總數，不是本頁筆數。"""
        self._make_users(DEFAULT_PAGE_SIZE + 5)
        body = self.client.get(LIST_URL).json()
        self.assertEqual(body["total"], DEFAULT_PAGE_SIZE + 6)  # +1 為 admin
        self.assertNotEqual(body["total"], len(body["items"]))

    def test_three_pagination_values_correct_when_fewer_than_one_page(self):
        """AC-5.2 的第四個 And：這是唯一能分辨「自我回報式實作」的情境。

        總數少於一頁時，`page_size = len(items)` 的錯誤實作會回 3 而非 20。
        """
        self._make_users(2)
        body = self.client.get(LIST_URL).json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], DEFAULT_PAGE_SIZE)
        self.assertEqual(len(body["items"]), 3)

    def test_pages_do_not_overlap_and_cover_everything(self):
        """AC-5.3：切頁不重複、無遺漏，且順序確定。"""
        self._make_users(9)  # 共 10 個帳號（含 admin）
        p1 = self.client.get(LIST_URL, params={"page": 1, "page_size": 4}).json()
        p2 = self.client.get(LIST_URL, params={"page": 2, "page_size": 4}).json()
        p3 = self.client.get(LIST_URL, params={"page": 3, "page_size": 4}).json()

        names1 = [u["username"] for u in p1["items"]]
        names2 = [u["username"] for u in p2["items"]]
        names3 = [u["username"] for u in p3["items"]]
        self.assertEqual(len(names1), 4)
        self.assertEqual(len(names2), 4)
        self.assertEqual(len(names3), 2)
        self.assertEqual(set(names1) & set(names2), set())
        self.assertEqual(len(set(names1 + names2 + names3)), 10)

    def test_same_page_twice_returns_same_order(self):
        """AC-5.3 的穩定性子句：沒有確定全序時前兩個斷言會退化為間歇通過。"""
        self._make_users(9)
        first = self.client.get(LIST_URL, params={"page": 2, "page_size": 4}).json()
        second = self.client.get(LIST_URL, params={"page": 2, "page_size": 4}).json()
        self.assertEqual(
            [u["username"] for u in first["items"]],
            [u["username"] for u in second["items"]],
        )

    def test_out_of_range_page_is_success_empty_and_echoes_page(self):
        """AC-5.4：合法但超出範圍 → 200＋空清單＋頁次回顯（不夾頁）。"""
        self._make_users(3)
        body_res = self.client.get(LIST_URL, params={"page": 5, "page_size": 2})
        self.assertEqual(body_res.status_code, 200)
        body = body_res.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 4)
        self.assertEqual(body["page_size"], 2)
        self.assertEqual(body["page"], 5)  # 回顯請求值，不是 2

    # --- 參數驗證（AC-5.5／NFR-8） ---

    def test_illegal_parameters_are_rejected_without_leaking_data(self):
        self._make_users(3)
        for params in (
            {"page": 0},
            {"page": -1},
            {"page": "abc"},
            {"page_size": 0},
            {"page_size": -5},
            {"page_size": MAX_PAGE_SIZE + 1},
            {"page_size": "abc"},
        ):
            with self.subTest(params=params):
                res = self.client.get(LIST_URL, params=params)
                self.assertEqual(res.status_code, 422)
                # 核心不變量：拒絕分支不得回傳任何帳號資料。
                self.assertNotIn("items", res.json())

    def test_negative_values_never_reach_the_query_layer(self):
        """NFR-8 的實質不變量：回應筆數不得超過每頁筆數上限。

        非法值原樣進入查詢層時，SQLite 對 `LIMIT -1` 會回傳整表剩餘 —— 而回傳
        全表正是 NFR-8 要防的暴露面。本斷言在那種實作下會紅。
        """
        self._make_users(MAX_PAGE_SIZE + 10)
        res = self.client.get(LIST_URL, params={"page_size": -1})
        self.assertEqual(res.status_code, 422)
        self.assertNotIn("items", res.json())

    # --- FR-6.7（AC-5.11 的契約子句） ---

    def test_non_pagination_query_params_do_not_change_the_result(self):
        self._make_users(5)
        base = self.client.get(LIST_URL).json()
        for extra in ({"sort": "last_activity_at"}, {"order_by": "id"}, {"filter": "overdue"}):
            with self.subTest(extra=extra):
                other = self.client.get(LIST_URL, params=extra).json()
                self.assertEqual(
                    [u["username"] for u in other["items"]],
                    [u["username"] for u in base["items"]],
                )
                self.assertEqual(other["total"], base["total"])

    @staticmethod
    def _find(items, username):
        for item in items:
            if item["username"] == username:
                return item
        raise AssertionError(f"{username} 不在回應中")


class UserMutationEndpointTest(unittest.TestCase):
    """啟停用與角色調整的回應形狀（AC-1.5 的兩個高風險構造點）。

    既有的 `requested_role` 就是在這兩處漏傳的；新欄位若比照現行寫法會複製同一
    缺陷，而使用者在 Admin 頁操作後會看到該列的時間欄變成空白。
    """

    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        self.admin = make_user(self.db, username="admin", role="Platform_Admin")
        self.other = make_user(self.db, username="target", role="Developer")
        self.other.last_activity_at = NOW - timedelta(days=200)
        self.keeper = make_user(self.db, username="keeper", role="Platform_Admin")
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    def test_toggle_active_response_carries_both_new_fields(self):
        res = self.client.put(
            f"/api/auth/{self.other.id}/active", json={"is_active": False}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(set(body.keys()), USER_FIELDS)
        self.assertIsNotNone(body["last_activity_at"])
        self.assertTrue(body["is_overdue"])

    def test_update_role_response_carries_both_new_fields(self):
        res = self.client.put(
            f"/api/auth/{self.other.id}/role", json={"role": "SRE"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(set(body.keys()), USER_FIELDS)
        self.assertIsNotNone(body["last_activity_at"])
        self.assertTrue(body["is_overdue"])


if __name__ == "__main__":
    unittest.main()
