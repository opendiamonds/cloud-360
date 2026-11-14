"""`U15 memory-page-ui` 跨單元補上的「帳號已核准」檢查（`B1`–`B9`）。

本檔對應 `U15` 的 `unit-test-instructions.md §四之一`。

## 這個缺口是什麼

自行註冊的帳號在 `authorization_status == "pending"` 時**已取得 token**，而
`memory_router` 的 dependency 只有 `get_current_user`。修補前，pending 帳號可讀到
他人設為 `platform` 的記憶（`U15` nfr-requirements 審查 `R-01`）。

## 為什麼斷言放在 facade 而不只是 HTTP

`services/intent_routing.py` **同進程**直呼 `MemoryFacade`，不經 router。若檢查
只放在 router 的 dependency，HTTP 案例會全綠而同進程路徑仍是開的——`B6` 就是讓
那個錯誤落點變紅的那一條。

## `team.md` 的 A＋B 雙向

`B1`–`B4` 是 deny 側（pending → 403），`B5` 是同一組端點的 allow 側
（approved → 2xx）。只有 deny 側的話，一個把**所有人**都擋成 403 的實作也會綠。

## 設計：pending 帳號刻意給 `Platform_Admin` 角色（`B4`／`B5`）

放寬與稽核查詢本來就有角色模型的 403。若 pending 帳號的角色是一般角色，
移除已核准檢查後它**仍然**會因角色而得到 403——`B4` 就測不出任何東西。
給它 `Platform_Admin` 使「角色判定會放行」，於是 403 只可能來自已核准檢查。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest
from types import SimpleNamespace
from unittest import mock

from models import MemoryRecord, User
from services.hierarchy_facade import mint_principal
from services.embedding_port import StubAdapter, resolve_embedding_port
from services.memory_errors import MemoryForbidden
from services.memory_facade import REASON_PENDING, MemoryFacade
from services.memory_types import VISIBILITY_SCOPE_PLATFORM
from tests.helpers import make_user
from tests.test_memory_authz import MemoryAuthzTestBase

#: 一個保證不存在的 id。in-memory 庫每個測試獨立，SERIAL 從 1 起算。
MISSING_ID = "987654"


class PendingAuthzTestBase(MemoryAuthzTestBase):
    """在 `MemoryAuthzTestBase` 的三個使用者之上，加兩個待核准帳號。"""

    def setUp(self):
        super().setUp()
        # 一般角色的 pending 帳號（自行註冊者的典型形狀之一）。
        self.pending = make_user(
            self.db,
            username="u15_pending",
            role="Project_Architect",
            authorization_status="pending",
        )
        # 角色判定**會放行**的 pending 帳號：見檔頭「設計」。
        self.pending_admin = make_user(
            self.db,
            username="u15_pending_admin",
            role="Platform_Admin",
            authorization_status="pending",
        )


# ---------------------------------------------------------------------------
# B1–B4：deny 側
# ---------------------------------------------------------------------------


class PendingDeniedOverHttpTest(PendingAuthzTestBase):
    """pending 帳號對五條路由一律 403。"""

    def test_B1_pending_cannot_list_memories(self):
        """`B1`：清單含他人 `platform` 記憶——修補前 pending 帳號讀得到它。"""
        self.seed(owner=self.other, scope=VISIBILITY_SCOPE_PLATFORM, suffix="shared")
        self.act_as(self.pending)
        response = self.client.get("/api/memory/records")
        self.assertEqual(response.status_code, 403)
        # 回應本體不得帶任何記憶內容。
        self.assertNotIn("__u8_fixture__", response.text)

    def test_B2_pending_cannot_create_memory(self):
        """`B2`：拒絕且**不留下任何一列**（判定先於寫入）。"""
        self.act_as(self.pending)
        before = self.db.query(MemoryRecord).count()
        response = self.client.post(
            "/api/memory/records",
            json={"kind": "semantic", "content": "u15 pending write"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.query(MemoryRecord).count(), before)

    def test_B3_pending_delete_of_missing_id_is_403_not_404(self):
        """`B3`：判定先於取列。

        若檢查放在取列之後，不存在的 id 會先得到 404——那表示 pending 帳號仍能
        區分「存在／不存在」。同一個 403 對存在與不存在的 id 都成立才算關閉。
        """
        self.act_as(self.pending)
        missing = self.client.delete(f"/api/memory/records/{MISSING_ID}")
        self.assertEqual(missing.status_code, 403)

        # 對照：自己真實存在的一列也是 403，且該列不被刪除。
        mine = self.seed(owner=self.pending, suffix="mine")
        existing = self.client.delete(f"/api/memory/records/{mine.id}")
        self.assertEqual(existing.status_code, 403)
        self.assertIsNotNone(self.db.get(MemoryRecord, mine.id))

    def test_B4_pending_cannot_widen_scope_or_read_audit_even_with_admin_role(self):
        """`B4`：角色判定會放行（`Platform_Admin`），403 只能來自已核准檢查。"""
        target = self.seed(owner=self.other, suffix="target")
        self.act_as(self.pending_admin)

        widen = self.client.put(
            f"/api/memory/records/{target.id}/scope",
            json={"visibility_scope": VISIBILITY_SCOPE_PLATFORM},
        )
        self.assertEqual(widen.status_code, 403)
        self.db.refresh(target)
        self.assertNotEqual(target.visibility_scope, VISIBILITY_SCOPE_PLATFORM)

        audit = self.client.get("/api/memory/audit-events")
        self.assertEqual(audit.status_code, 403)


# ---------------------------------------------------------------------------
# B5：allow 側（雙向）
# ---------------------------------------------------------------------------


class ApprovedAllowedOverHttpTest(PendingAuthzTestBase):
    """`B5`：與 `B1`–`B4` 同一組端點，換成 approved 帳號 → 對應 2xx。"""

    def test_B5_approved_accounts_reach_all_five_routes(self):
        shared = self.seed(owner=self.other, scope=VISIBILITY_SCOPE_PLATFORM, suffix="shared")

        # 一般 approved 使用者：列出、建立、刪除自己的。
        self.act_as(self.owner)
        listed = self.client.get("/api/memory/records")
        self.assertEqual(listed.status_code, 200)
        self.assertIn(str(shared.id), self.ids_in(listed.json()))

        created = self.client.post(
            "/api/memory/records",
            json={"kind": "semantic", "content": "u15 approved write"},
        )
        self.assertEqual(created.status_code, 201)

        deleted = self.client.delete(
            f"/api/memory/records/{created.json()['memory_id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        # approved 的 Platform_Admin：放寬與稽核查詢。
        target = self.seed(owner=self.other, suffix="target")
        self.act_as(self.admin)
        widen = self.client.put(
            f"/api/memory/records/{target.id}/scope",
            json={"visibility_scope": VISIBILITY_SCOPE_PLATFORM},
        )
        self.assertEqual(widen.status_code, 200)
        self.assertEqual(widen.json()["visibility_scope"], VISIBILITY_SCOPE_PLATFORM)

        audit = self.client.get("/api/memory/audit-events")
        self.assertEqual(audit.status_code, 200)


# ---------------------------------------------------------------------------
# B6：同進程路徑（`intent_routing.py` 的那一條）
# ---------------------------------------------------------------------------


class PendingDeniedInProcessTest(PendingAuthzTestBase):
    def test_B6_pending_principal_is_rejected_by_facade_directly(self):
        """`B6`：不經 router。若檢查只在 router，這裡不會 raise。

        同時斷言拒絕日誌帶 `reason=pending`——那是營運端分辨「未核准帳號在
        探測」與其他拒絕的唯一手段（沿用 `NFR7.30` 的三欄位形狀）。
        """
        self.seed(owner=self.other, scope=VISIBILITY_SCOPE_PLATFORM, suffix="shared")
        principal = mint_principal(self.pending)
        with self.assertLogs("cloud360.memory_service", level="WARNING") as captured:
            with self.assertRaises(MemoryForbidden) as ctx:
                self.facade().list_records(principal)
        self.assertEqual(ctx.exception.reason, REASON_PENDING)
        self.assertTrue(
            any(f"reason={REASON_PENDING}" in line for line in captured.output),
            captured.output,
        )
        # 日誌不得帶記憶內容（`NFR7.31` 白名單）。
        self.assertFalse(any("__u8_fixture__" in line for line in captured.output))


class PendingSearchInProcessTest(PendingAuthzTestBase):
    """`B8`：`search` 的同進程路徑（審查 `R-02`）。

    `search` 沒有任何 HTTP 路由，唯一的呼叫端是 `intent_routing.py` 的同進程
    呼叫，而那裡把任何例外降級成「記憶不可用」並記 log——所以 `search` 的守衛
    若被拿掉，HTTP 案例與端到端都不會有訊號。本案是它唯一的自動化斷言。

    Port 用的是 `resolve_embedding_port()` 在 `EMBEDDING_PROVIDER=stub` 下解析出來
    的**真正** `StubAdapter`，只以 `wraps=` 觀察其公開的 `embed` 被呼叫幾次，不替換
    任何 `U6` 的行為（`unit-test-instructions.md §六`）。
    """

    def _spied_facade(self):
        port = resolve_embedding_port()
        self.assertIsInstance(port, StubAdapter)
        spy = mock.patch.object(port, "embed", wraps=port.embed)
        embed = spy.start()
        self.addCleanup(spy.stop)
        return MemoryFacade(self.db, port=port), embed

    def test_B8_pending_principal_search_is_rejected_before_embedding(self):
        self.seed(owner=self.other, scope=VISIBILITY_SCOPE_PLATFORM, suffix="shared")
        facade, embed = self._spied_facade()
        # 只替換**取向量之後**的 SQL 步驟：它用 pgvector 的 `<=>`，in-memory SQLite
        # 跑不了。替換它使「守衛被拿掉」的突變在 `assertRaises` 這一行變紅，而不是
        # 在 SQLite 的語法錯誤上變紅——後者在真實 PostgreSQL 上會靜默放行。
        sql_patch = mock.patch(
            "services.memory_service.search_records", return_value=[]
        )
        sql_step = sql_patch.start()
        self.addCleanup(sql_patch.stop)

        with self.assertRaises(MemoryForbidden) as ctx:
            facade.search(mint_principal(self.pending), "u15 pending probe")
        self.assertEqual(ctx.exception.reason, REASON_PENDING)
        # 判定先於取向量：pending 帳號的查詢字串從未送進 embedding Port。
        self.assertEqual(embed.call_count, 0)
        self.assertEqual(sql_step.call_count, 0)

        # 對照（allow 側）：同一個 spy 下 approved 帳號會真的取向量。少了這一半，
        # 一個從未接上的 spy 也會讓上面的 `call_count == 0` 恆真。
        result = facade.search(mint_principal(self.owner), "u15 approved probe")
        self.assertEqual(result, [])
        self.assertEqual(embed.call_count, 1)
        self.assertEqual(sql_step.call_count, 1)


# ---------------------------------------------------------------------------
# B7：鑄造入口
# ---------------------------------------------------------------------------


class MintPrincipalApprovalTest(PendingAuthzTestBase):
    def test_B7_mint_principal_reflects_authorization_status(self):
        rejected = make_user(
            self.db,
            username="u15_rejected",
            role="Project_Architect",
            authorization_status="rejected",
        )
        self.assertFalse(mint_principal(self.pending).is_approved)
        self.assertFalse(mint_principal(rejected).is_approved)
        self.assertTrue(mint_principal(self.owner).is_approved)


    def test_B9_missing_authorization_status_mints_approved(self):
        """`B9`：缺欄位／空值視為 approved 是**刻意的**（審查 `R-04`）。

        `services.rbac.user_is_approved` 以 `(status or "approved") == "approved"`
        判定；`tests_pg/test_membership_concurrency.py` 只帶 `.id`／`.role` 的輕量
        物件靠這一點鑄造出與欄位加入前相同的行為。DB 欄位為 `nullable=False`，
        故正式資料不可達此分支。若有人把鑄造改成「只有字面 `approved` 才放行」，
        本案會紅——那個改動需要先處理那些輕量物件，而不是悄悄改變語意。
        `pending` → False 的那一半由 `B7` 斷言，本案不重複。
        """
        unsaved = User(id=90001, role="Project_Architect", authorization_status=None)
        self.assertTrue(mint_principal(unsaved).is_approved)

        lightweight = SimpleNamespace(id=90002, role="Project_Architect")
        self.assertFalse(hasattr(lightweight, "authorization_status"))
        self.assertTrue(mint_principal(lightweight).is_approved)


if __name__ == "__main__":
    unittest.main()
