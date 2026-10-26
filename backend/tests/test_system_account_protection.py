"""系統保留帳號的 HTTP 層保護（合併前必修第 11 項，`U9 memory-purge`）。

保留帳號 `SYSTEM.retention-purge` 是 90 天記憶清除的稽核 actor（`schema_rbac.sql`
的 `K)` 區塊 seed，`is_active=FALSE`、role `system`）。在本修正之前應用程式完全
不認得它：`DELETE /api/auth/{id}` 只要求對象已停用，而它 seed 時就是停用的，故
可被直接刪除；刪除之後清除的稽核 INSERT 全部外鍵違反，而稽核與刪除同一個交易，
90 天清除整個停擺。`GET /api/auth/list` 也會把它列給管理者看。

既有自動化層為何沒抓到：`test_retention_purge_contract.py` 只鎖 SQL／seed 的文字，
`test_user_list_endpoint.py` 與 `test_user_delete_hierarchy.py` 的 fixture 裡從來
沒有這一列——SQLite 測試路徑看不到 `K)` 的 seed（`OPEN-ID9-3`）。

以 `app.dependency_overrides` 覆寫 `get_db`／`get_current_user`，in-memory SQLite。
保留帳號的 username 從 `services.system_accounts` 取用，**不在本檔重新手寫**；
A5 以 AST 從 seed 腳本**解析**出 `SENTINEL_USERNAME` 與之比對（不 import 該腳本，
它在 import 時會調整 `sys.path` 並依賴 `DATABASE_URL`）。
"""

import ast
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from tests.helpers import close_session, make_session, make_user
from database import get_db
from main import app
from models import RoleAuthorizationRequest, User
from services.auth import get_current_user
from services.rbac import ensure_role_permissions_seeded
from services.system_accounts import (
    RETENTION_SYSTEM_ACTOR_USERNAME,
    is_reserved_system_account,
)

SEED_SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "seed_retention_system_actor.py"
)


def _module_string_constant(path: Path, name: str) -> str:
    """以 AST 取出模組層 `NAME = "..."` 的字串值；找不到即失敗。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        return value.value
    raise AssertionError(f"{path.name} 找不到模組層字串常數 {name}")


class SystemAccountProtectionTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        ensure_role_permissions_seeded(self.db, force=True)
        self.admin = make_user(self.db, username="admin", role="Platform_Admin")
        # 與 K) 區塊同形：停用、非 canonical 角色。
        self.reserved = make_user(
            self.db,
            username=RETENTION_SYSTEM_ACTOR_USERNAME,
            role="system",
            is_active=False,
        )
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    def _reload_reserved(self) -> User:
        self.db.expire_all()
        row = (
            self.db.query(User)
            .filter(User.username == RETENTION_SYSTEM_ACTOR_USERNAME)
            .first()
        )
        self.assertIsNotNone(row, "保留帳號的列不應消失")
        return row

    def test_delete_reserved_account_is_rejected_and_row_survives(self):
        """
        @purpose A1：保留帳號 seed 時即為停用，「須先停用才能刪」擋不住它；刪除必須回 409 且列仍在，否則 90 天清除自此每次中止。
        @api DELETE /api/auth/{user_id} → 409
        @given SQLite 內 seed 保留帳號 SYSTEM.retention-purge（is_active=False、role=system），操作者為 Platform_Admin
        @step 以保留帳號的 id 呼叫 DELETE /api/auth/{id}
        @pass 狀態碼 409；回應 detail 提到「系統保留帳號」且 blocking_references 為空清單；資料庫內該列仍存在
        @story MB-11 NFR7.11 FR4.7
        """
        res = self.client.delete(f"/api/auth/{self.reserved.id}")
        self.assertEqual(res.status_code, 409, res.text)
        body = res.json()
        self.assertIn("系統保留帳號", body["detail"])
        self.assertEqual(body["blocking_references"], [])
        self._reload_reserved()

    def test_change_role_of_reserved_account_is_rejected(self):
        """
        @purpose A2：把保留帳號改成 canonical 角色會拆掉它「零權限」那道鎖；改角色必須回 409 且角色不變。
        @api PUT /api/auth/{user_id}/role → 409
        @given 同 A1
        @step 以保留帳號的 id 呼叫 PUT /api/auth/{id}/role，body {"role": "Developer"}
        @pass 狀態碼 409；資料庫內該列 role 仍為 system
        @story MB-11 NFR7.11
        """
        res = self.client.put(
            f"/api/auth/{self.reserved.id}/role", json={"role": "Developer"}
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertIn("系統保留帳號", res.json()["detail"])
        self.assertEqual(self._reload_reserved().role, "system")

    def test_activate_reserved_account_is_rejected(self):
        """
        @purpose A3：啟用保留帳號會拆掉 is_active=FALSE 那道鎖；啟用必須回 409 且仍為停用。
        @api PUT /api/auth/{user_id}/active → 409
        @given 同 A1
        @step 以保留帳號的 id 呼叫 PUT /api/auth/{id}/active，body {"is_active": true}
        @pass 狀態碼 409；回應 detail 提到「系統保留帳號」；資料庫內該列 is_active 仍為 False
        @story MB-11 NFR7.11
        """
        res = self.client.put(
            f"/api/auth/{self.reserved.id}/active", json={"is_active": True}
        )
        self.assertEqual(res.status_code, 409, res.text)
        self.assertIn("系統保留帳號", res.json()["detail"])
        self.assertFalse(self._reload_reserved().is_active)

    def test_list_excludes_reserved_account_from_items_and_total(self):
        """
        @purpose A4：使用者清單不得列出保留帳號，且 total 與分頁一致地排除（只濾當頁會使 total 多 1）。
        @api GET /api/auth/list → 200
        @ui /admin
        @given 同 A1，另有兩位一般使用者（admin 與 dev1，共兩位非保留帳號）
        @step 呼叫 GET /api/auth/list?page=1&page_size=1 與 GET /api/auth/list?page=2&page_size=1，再呼叫 page_size=50
        @pass 每一頁的 items 都不含保留帳號；total 恆為 2；兩頁的 username 聯集恰為 {admin, dev1}
        @story MB-11
        """
        make_user(self.db, username="dev1", role="Developer")

        seen = []
        for page in (1, 2):
            res = self.client.get(f"/api/auth/list?page={page}&page_size=1")
            self.assertEqual(res.status_code, 200, res.text)
            body = res.json()
            self.assertEqual(body["total"], 2)
            seen.extend(item["username"] for item in body["items"])
        self.assertEqual(set(seen), {"admin", "dev1"})

        body = self.client.get("/api/auth/list?page_size=50").json()
        usernames = {item["username"] for item in body["items"]}
        self.assertNotIn(RETENTION_SYSTEM_ACTOR_USERNAME, usernames)
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["items"]), 2)

    def test_service_constant_matches_seed_script_sentinel(self):
        """
        @purpose A5：應用程式辨識保留帳號用的常數必須與 seed 腳本實際寫入的 username 逐字相同；拼錯即保護全部失效而無人察覺。
        @given 讀取 backend/scripts/seed_retention_system_actor.py 原始碼（不 import）
        @step 以 AST 解析出模組層 SENTINEL_USERNAME，與 services.system_accounts.RETENTION_SYSTEM_ACTOR_USERNAME 比對
        @pass 兩者逐字相同
        @story MB-11 NFR7.11
        """
        self.assertEqual(
            _module_string_constant(SEED_SCRIPT, "SENTINEL_USERNAME"),
            RETENTION_SYSTEM_ACTOR_USERNAME,
        )

    def test_reject_authorization_request_cannot_delete_reserved_account(self):
        """
        @purpose A6：「拒絕授權申請」會一併硬刪除帳號，是第二條刪除路徑；若保留帳號帶有待審申請，拒絕必須回 409 且帳號與申請都不動。
        @api POST /api/auth/authorization-requests/{request_id}/reject → 409
        @given 同 A1，並人工插入一筆指向保留帳號的 pending 授權申請（正常流程不會產生，屬縱深防禦）
        @step 呼叫 POST /api/auth/authorization-requests/{id}/reject
        @pass 狀態碼 409；保留帳號的列仍存在；該申請 status 仍為 pending
        @story MB-11
        """
        req = RoleAuthorizationRequest(
            user_id=self.reserved.id, requested_role="Developer", status="pending"
        )
        self.db.add(req)
        self.db.commit()
        req_id = req.id

        res = self.client.post(f"/api/auth/authorization-requests/{req_id}/reject")
        self.assertEqual(res.status_code, 409, res.text)
        self._reload_reserved()
        req_row = (
            self.db.query(RoleAuthorizationRequest)
            .filter(RoleAuthorizationRequest.id == req_id)
            .first()
        )
        self.assertIsNotNone(req_row)
        self.assertEqual(req_row.status, "pending")

    def test_ordinary_inactive_user_is_not_treated_as_reserved(self):
        """
        @purpose A7：保護只針對保留帳號——一般停用帳號（含名稱為保留名的小寫變體）仍可刪除，判定不得被放寬成「停用即保護」。
        @api DELETE /api/auth/{user_id} → 200
        @given 一位停用的一般使用者，username 為保留名的全小寫形式
        @step 呼叫 DELETE /api/auth/{id}
        @pass 狀態碼 200 且回應的 deleted_username 為該使用者；is_reserved_system_account 對它回 False
        @story MB-11
        """
        lookalike = make_user(
            self.db,
            username=RETENTION_SYSTEM_ACTOR_USERNAME.lower(),
            role="Developer",
            is_active=False,
        )
        self.assertFalse(is_reserved_system_account(lookalike))
        res = self.client.delete(f"/api/auth/{lookalike.id}")
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["deleted_username"], lookalike.username)


if __name__ == "__main__":
    unittest.main()
