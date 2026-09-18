"""`GET /api/auth/me` 的回應形狀測試（起因 #468 的規格漂移報告）。

漂移的形狀：`frontend-backend-specification.md` §4.1.2 要求回應帶
`last_opened_diagram_id`，但 `MeResponse` 漏了它。欄位本身**早就存在**——
`models.py` 有欄、`database.py` 有補欄、`collab_router.py` 讀寫它——只有這個
回應模型沒宣告，於是 FastAPI 在序列化時把它丟掉。

為何既有的閘門都攔不到：`tsc -b` 檢查的是「用法對型別檔」，不是「型別檔對規格」；
e2e 沒有任何 case 讀 `/me` 的這個欄位；OpenAPI 漂移檢查比對的是「committed spec
對 committed types」，兩者一起漏就一起過。只有直接斷言 HTTP 回應的欄位集合才擋得住。

斷言**集合相等**而非「包含」：前者在漏欄位與多欄位兩個方向都會失敗。
"""

import unittest

from starlette.testclient import TestClient

from tests.helpers import close_session, make_session, make_user
from database import get_db
from main import app
from services.auth import get_current_user
from services.rbac import ensure_role_permissions_seeded

ME_URL = "/api/auth/me"

ME_FIELDS = {
    "id",
    "username",
    "role",
    "is_active",
    "authorization_status",
    "permissions",
    "pending_request",
    "last_opened_diagram_id",
}


class MeEndpointTest(unittest.TestCase):
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

    def test_response_field_set_matches_the_specification(self):
        resp = self.client.get(ME_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.json().keys()), ME_FIELDS)

    def test_last_opened_diagram_id_is_null_when_never_opened(self):
        """尚未開過任何圖時為 null —— 不是缺欄位，也不是 0。"""
        resp = self.client.get(ME_URL)
        self.assertIn("last_opened_diagram_id", resp.json())
        self.assertIsNone(resp.json()["last_opened_diagram_id"])

    def test_last_opened_diagram_id_carries_the_stored_value(self):
        """有值時必須真的帶出來。

        這是本次漂移的核心斷言：漏宣告欄位時，序列化會靜默丟棄它，回應看起來
        「正常」但少一個鍵——上面的 null 測試單獨存在時擋不住這種情況，因為
        「值是 None」與「欄位被丟掉」在寬鬆斷言下長得一樣。
        """
        self.admin.last_opened_diagram_id = 12
        self.db.commit()
        resp = self.client.get(ME_URL)
        self.assertEqual(resp.json()["last_opened_diagram_id"], 12)


if __name__ == "__main__":
    unittest.main()
