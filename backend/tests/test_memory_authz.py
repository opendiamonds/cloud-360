"""`U8 memory-service` 的授權與端點契約測試（`A1`–`A14`，TestClient ＋ SQLite）。

本檔對應 `unit-test-instructions.md §4.3`。

## 為什麼這些路徑在 SQLite 上測得起來，而 `search` 不行

`unit-test-instructions.md §三` 的分界線逐字：**由「SQLite 能不能跑那段 SQL」
決定，不是由測試型態決定。**

本檔涵蓋的路徑（授權、過濾、酬載忽略、`limit` 上限、分頁、交易邊界）
**都不碰向量**，而 `models.py` 新增的 ORM 鏡像使 SQLite 有表可用
（`code-generation-plan.md §1.1`）。

**`search` 的向量路徑不在本檔內**：SQLite 無向量型別、無距離運算子——那條
SQL **編不出來**。它由 `backend/scripts/verify_memory_schema.sql` 的 `S15`
在真實 PostgreSQL 上覆蓋（`cicd-pipeline.md §三之二`）。

## `U6 EmbeddingPort` 以 **`stub` 提供者設定**，不 mock 它的內部

`unit-test-instructions.md §六` 逐字：「以 `stub` 提供者**設定**；
**不 mock `U6` 的內部**——它有自己的契約（`K-06`）」。

故本檔在 `setUp` 設 `EMBEDDING_PROVIDER=stub`，讓 `resolve_embedding_port()`
走它自己真正的解析路徑並回一個真的 `StubAdapter`。

**這不是比注入更方便，是唯一可行的那條**：`memory_router` 的 handler 自己
`MemoryFacade(db)`（不帶 port），所以 HTTP 路徑上沒有注入點——注入只對
直接呼叫 facade 的測試有效，而本檔大半是 HTTP 測試。
第一版用注入，三條 `POST` 測試隨即以
`ValueError: EMBEDDING_PROVIDER 未設定` 失敗——那個失敗本身正是 `U6` 的
`BR1.6`（不得靜默降級）在運作。

## `[D1]`=A 的三案例為什麼**缺一不可**（`A4`／`A5`／`A6`）

三者的對外狀態碼刻意是 `204`／`404`／`404`，差異只在日誌。

只測 `A5` 的話，一個把兩者都收斂到 404 且**連日誌也收斂**的實作會通過
——而那會讓枚舉行為完全不可見（`nfr-design/security-design.md §二之二`：
`[D1]`=A 之後，日誌是區分「誤刪」與「枚舉」的**唯一**手段）。
故 `A5` 與 `A6` 必須同時斷言「狀態碼相同」與「日誌可區分」。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import os
import unittest
from typing import Optional
from unittest import mock

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import MemoryAuditEvent, MemoryRecord, User
from services.auth import get_current_user
from services.memory_facade import MemoryFacade, mint_principal
from services.memory_service import MAX_LIST_PAGE_SIZE
from services.memory_types import (
    VISIBILITY_SCOPE_OWNER,
    VISIBILITY_SCOPE_PLATFORM,
)
from tests.helpers import close_session, make_session, make_user

#: fixture 的 `content` 一律帶這個前綴（`unit-test-instructions.md §七`）：
#: 清理依前綴，不碰其他資料。本檔每個測試用獨立的 in-memory 庫，故實際上
#: 不需要清理——前綴保留的理由是它同時是 `A12`（404 回應體不含 `content`）
#: 的比對目標，一個獨特的字串使那條斷言不會被別的文字偶然滿足。
FIXTURE_PREFIX = "__u8_fixture__"

#: `stub` 提供者的 `model_id`（`embedding_port.STUB_MODEL_ID`）。寫成字面值
#: 而非 import 那個常數是刻意的：若 `U6` 改了它，本檔的 fixture 與斷言應該
#: **一起紅**，而共用來源會讓兩邊同時漂移而測試照樣綠。
STUB_MODEL_ID = "stub-v1"


class MemoryAuthzTestBase(unittest.TestCase):
    """共用 fixture：三個使用者 ＋ 覆寫 `get_db`／`get_current_user`。

    形狀沿用 `tests/helpers.py` 既有的樣板（`psycopg` stub ＋ in-memory SQLite
    ＋ `app.dependency_overrides`）。**不自創第二套**（`§六` 逐字）。
    """

    def setUp(self):
        # `U6` 的設定：`stub` 提供者。`EMBEDDING_PROVIDER` **刻意沒有預設值**
        # （`embedding_port._reject` 逐字），故不設就會大聲失敗——那是 `BR1.6`
        # 在運作，不是測試環境的缺陷。
        self._env = mock.patch.dict(
            os.environ, {"EMBEDDING_PROVIDER": "stub"}, clear=False
        )
        self._env.start()
        self.addCleanup(self._env.stop)

        self.db = make_session()
        # 擁有者、另一個普通使用者、以及一個平台管理員。
        self.owner = make_user(
            self.db, username="u8_owner", role="Project_Architect"
        )
        self.other = make_user(
            self.db, username="u8_other", role="Project_Architect"
        )
        self.admin = make_user(self.db, username="u8_admin", role="Platform_Admin")

        self._acting_as = self.owner

        def override_get_db():
            yield self.db

        def override_get_current_user():
            return self._acting_as

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        # `TestClient(app)` 刻意**不**觸發 `@app.on_event("startup")`，故
        # `init_db()` 與 `configure_embedding_env()` 都不會跑——既有測試全綠
        # 本身就是這個選擇的驗證（`embedding_port.configure_embedding_env`
        # 的 docstring 逐字）。
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        close_session(self.db)

    # -- 工具 ---------------------------------------------------------------

    def act_as(self, user: User) -> None:
        self._acting_as = user

    def facade(self) -> MemoryFacade:
        """走與 router 完全相同的 Port 解析路徑（不注入），見檔頭。"""
        return MemoryFacade(self.db)

    def seed(
        self,
        *,
        owner: User,
        kind: str = "semantic",
        scope: str = VISIBILITY_SCOPE_OWNER,
        suffix: str = "",
        embedding_model: str = STUB_MODEL_ID,
    ) -> MemoryRecord:
        """直接插一列。**刻意不經 facade**——fixture 不應依賴被測路徑。

        `expires_at` 只對 `episodic` 設（`EC1`），由 service 的 `expiry_for`
        共用同一條規則而不在此重寫。
        """
        from services.memory_service import expiry_for
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            kind=kind,
            owner_user_id=owner.id,
            visibility_scope=scope,
            content=f"{FIXTURE_PREFIX} {owner.username} {suffix}".strip(),
            embedding_model=embedding_model,
            created_at=now,
            expires_at=expiry_for(kind, now),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def ids_in(self, payload) -> set:
        return {item["memory_id"] for item in payload}

    def audit_rows(self, memory_id: Optional[int] = None):
        query = self.db.query(MemoryAuditEvent)
        if memory_id is not None:
            query = query.filter(MemoryAuditEvent.memory_id == memory_id)
        return query.all()


# ---------------------------------------------------------------------------
# A1–A3：擁有者模型的讀取過濾（`BR2.2`）
# ---------------------------------------------------------------------------


class OwnerVisibilityTest(MemoryAuthzTestBase):
    """`A1`–`A3`：讀取一律只回該呼叫者依可見範圍有權讀取的列。

    **過濾而非拒絕**（`BR2.2` 的 `violation_behaviour` 逐字）：
    「看不到別人的記憶」不是一個錯誤狀態，故這三條都期望 **200**。
    """

    def test_A1_owner_sees_own_memory(self):
        mine = self.seed(owner=self.owner, suffix="mine")
        self.act_as(self.owner)
        response = self.client.get("/api/memory/records")
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(mine.id), self.ids_in(response.json()))

    def test_A2_owner_scoped_memory_of_others_is_not_listed(self):
        """`AC4.1.2`：他人的 `owner` 範圍記憶**不出現**在我的列表。

        這是本單元最基本的授權斷言。它與 `A1` 一起構成 `team.md` A 規則
        要求的 allow/deny 雙向。
        """
        theirs = self.seed(owner=self.other, suffix="theirs")
        self.act_as(self.owner)
        response = self.client.get("/api/memory/records")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(str(theirs.id), self.ids_in(response.json()))

    def test_A3_platform_scoped_memory_of_others_is_listed(self):
        """`platform` 範圍的記憶出現在他人列表。

        **反方向的斷言，而它不是對稱的裝飾**：少了它，一個「只回自己的列」
        的實作（完全忽略 `visibilityScope`）會通過 `A1` 與 `A2`
        ——而那會讓 `widen_scope` 這整個操作沒有任何可觀察效果。
        """
        shared = self.seed(
            owner=self.other, scope=VISIBILITY_SCOPE_PLATFORM, suffix="shared"
        )
        self.act_as(self.owner)
        response = self.client.get("/api/memory/records")
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(shared.id), self.ids_in(response.json()))


# ---------------------------------------------------------------------------
# A4–A7：刪除與 `[D1]`=A 的回應收斂
# ---------------------------------------------------------------------------


class DeleteResponseCollapseTest(MemoryAuthzTestBase):
    """`A4`–`A7`：`[D1]`=A 的三案例 ＋ 角色不授予跨使用者刪除權。"""

    def test_A4_owner_deletes_own_memory(self):
        """① 擁有者 → **204**，且留下一筆 `deleted_by_user` 稽核（`BR4.2`）。"""
        mine = self.seed(owner=self.owner, suffix="to-delete")
        memory_id = mine.id
        self.act_as(self.owner)
        response = self.client.delete(f"/api/memory/records/{memory_id}")
        self.assertEqual(response.status_code, 204)

        self.assertIsNone(
            self.db.query(MemoryRecord).filter(MemoryRecord.id == memory_id).first()
        )
        events = self.audit_rows(memory_id)
        self.assertEqual(len(events), 1, "刪除必須留下恰一筆稽核")
        self.assertEqual(events[0].action, "deleted_by_user")
        self.assertEqual(events[0].actor_user_id, self.owner.id)
        # `EC5`：非 `scope_changed` 的事件兩個範圍欄皆須為空，避免讀者把刪除
        # 事件的空白範圍誤讀為「改成了空」。
        self.assertIsNone(events[0].previous_scope)
        self.assertIsNone(events[0].new_scope)

    def test_A5_other_user_deleting_gets_404_and_an_owner_reason_log(self):
        """② 他人刪除 → **404（非 403）** ＋ 日誌**含** `reason=owner`。

        `[D1]`=A：`schema_rbac.sql` 的 `id SERIAL PRIMARY KEY` 是連續整數，
        403／404 的差異讓任何已認證使用者得以走訪 `1..N` 取得**整張表哪些 id
        存在**。收斂關掉那個 oracle。

        **日誌斷言與狀態碼斷言缺一不可**（見檔頭）：這一條與 `A6` 的對外回應
        刻意相同，若連日誌也收斂，枚舉行為就完全不可見。
        """
        mine = self.seed(owner=self.owner, suffix="guarded")
        memory_id = mine.id
        self.act_as(self.other)

        with self.assertLogs("cloud360.memory_service", level="WARNING") as captured:
            response = self.client.delete(f"/api/memory/records/{memory_id}")

        self.assertEqual(
            response.status_code,
            404,
            "非擁有者必須得到 404 而非 403（[D1]=A）——403 會重開整張表的枚舉 oracle",
        )
        joined = "\n".join(captured.output)
        self.assertIn("reason=owner", joined)
        self.assertIn(f"memory_id={memory_id}", joined)
        self.assertIn(f"principal={self.other.id}", joined)

        # 記憶**沒有**被刪，而且沒有稽核事件——拒絕路徑不得留稽核。
        self.assertIsNotNone(
            self.db.query(MemoryRecord).filter(MemoryRecord.id == memory_id).first()
        )
        self.assertEqual(self.audit_rows(memory_id), [])

    def test_A6_deleting_a_missing_id_gets_404_without_an_owner_reason_log(self):
        """③ 不存在的 id → **404** ＋ 日誌**不含** `reason=owner`。

        與 `A5` 的狀態碼刻意相同，差異只在日誌——這是 oracle 被關閉的證據。

        以 `assertNoLogs` 斷言「什麼都沒記」，而不是斷言「記了但不含某字串」：
        前者在「順手補了一筆 `reason=owner`」時會紅，後者不會。
        """
        self.act_as(self.other)
        missing_id = 999_999

        with self.assertNoLogs("cloud360.memory_service", level="WARNING"):
            response = self.client.delete(f"/api/memory/records/{missing_id}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.audit_rows(missing_id), [], "`BR4.3`：不得產生稽核")

    def test_A5_A6_are_externally_indistinguishable(self):
        """**兩者的對外回應必須逐欄相同**，否則 oracle 從狀態碼搬到回應本體。

        `MemoryNotFound` 刻意不帶任何查到的欄位，所以兩個 `detail` 只差那個
        由呼叫端自己送來的 id。本測試把 id 正規化後比對整個 JSON。
        """
        mine = self.seed(owner=self.owner, suffix="probe")
        self.act_as(self.other)

        forbidden = self.client.delete(f"/api/memory/records/{mine.id}")
        missing = self.client.delete("/api/memory/records/999999")

        self.assertEqual(forbidden.status_code, missing.status_code)
        normalise = lambda body, mid: str(body).replace(str(mid), "<id>")  # noqa: E731
        self.assertEqual(
            normalise(forbidden.json(), mine.id),
            normalise(missing.json(), 999999),
            "非擁有者與不存在的回應本體必須無法區分",
        )

    def test_A7_platform_admin_cannot_delete_another_users_memory(self):
        """`A7`：`Platform_Admin` 刪他人記憶 → **404**。角色不授予刪除權。

        **這是兩套授權模型不可互換的證據**（`rules.md §2.1`）：同一個角色
        在 `A8` 有放寬權，在這裡**沒有**刪除權。

        只測 `A8` 的話，一個用角色模型判刪除的實作也會通過——而它會讓
        `Platform_Admin` 得以刪除全平台任何人的對話歷程。
        """
        mine = self.seed(owner=self.owner, suffix="admin-cannot-delete")
        memory_id = mine.id
        self.act_as(self.admin)

        response = self.client.delete(f"/api/memory/records/{memory_id}")
        self.assertEqual(
            response.status_code,
            404,
            "Platform_Admin 不因其角色而能刪除他人的記憶（BR4.1 的 note）",
        )
        self.assertIsNotNone(
            self.db.query(MemoryRecord).filter(MemoryRecord.id == memory_id).first()
        )


# ---------------------------------------------------------------------------
# A8–A10：角色模型（放寬可見範圍）
# ---------------------------------------------------------------------------


class ScopeWideningTest(MemoryAuthzTestBase):
    """`A8`–`A10`：`BR5.1` 的 allow/deny 雙向 ＋ `NFR7.22` 的順序。

    **`BR5.1` 在上游沒有任何 AC**（`FD8-5`：上游要求「僅管理員得放寬」卻無 AC
    斷言「非管理員不能放寬」）。本組是 `nfr-design` 以 `NFR7.22` 的雙向判準
    補上的可驗性，也是 `team.md` A 規則（授權變更需 allow/deny 雙向）的落實。
    """

    def test_A8_platform_admin_widens_scope_and_audit_records_both_values(self):
        """`A8`：具角色 → **200** ＋ 稽核含**前後值**（`AC4.3.1`／`BR5.3`）。"""
        target = self.seed(owner=self.owner, suffix="to-widen")
        memory_id = target.id
        self.act_as(self.admin)

        response = self.client.put(
            f"/api/memory/records/{memory_id}/scope",
            json={"visibility_scope": VISIBILITY_SCOPE_PLATFORM},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["visibility_scope"], VISIBILITY_SCOPE_PLATFORM
        )

        events = self.audit_rows(memory_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "scope_changed")
        self.assertEqual(events[0].actor_user_id, self.admin.id)
        # `EC4`：兩者皆須非空且**彼此不同**。
        self.assertEqual(events[0].previous_scope, VISIBILITY_SCOPE_OWNER)
        self.assertEqual(events[0].new_scope, VISIBILITY_SCOPE_PLATFORM)
        self.assertNotEqual(events[0].previous_scope, events[0].new_scope)

    def test_A9_non_admin_widening_is_forbidden(self):
        """`A9`：不具角色 → **403**（不是 404，也不是靜默成功）。

        **擁有者本人也不行**，而這是刻意的：`FR4.3b` 把放寬定為「獨立的、
        需授權的操作」。故這裡用**擁有者自己**當 principal——用第三人會讓
        這條測試同時被擁有者模型滿足而失去針對性。
        """
        target = self.seed(owner=self.owner, suffix="owner-cannot-widen")
        self.act_as(self.owner)

        with self.assertLogs("cloud360.memory_service", level="WARNING") as captured:
            response = self.client.put(
                f"/api/memory/records/{target.id}/scope",
                json={"visibility_scope": VISIBILITY_SCOPE_PLATFORM},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("reason=scope", "\n".join(captured.output))
        self.db.refresh(target)
        self.assertEqual(target.visibility_scope, VISIBILITY_SCOPE_OWNER)
        self.assertEqual(self.audit_rows(target.id), [])

    def test_A10_non_admin_widening_a_missing_id_gets_403_not_404(self):
        """`A10`：無權 ＋ 不存在 → **403**（不是 404）。

        **這一條與 `A6` 形狀相反，而那是刻意的**（`security-design.md §三`）：
        放寬路徑**先判角色、後取記憶**，故無權者在任何 id 上都得到同一個 403
        ——oracle 本來就不存在，不需要收斂。

        `NFR7.22` 的判準逐字把這個第三案例列為「這一條的重點」：
        只測前兩個的話，**一個把順序寫反的實作也會通過**。
        """
        self.act_as(self.owner)
        response = self.client.put(
            "/api/memory/records/999999/scope",
            json={"visibility_scope": VISIBILITY_SCOPE_PLATFORM},
        )
        self.assertEqual(
            response.status_code,
            403,
            "授權判定必須先於記憶存在性判定（NFR7.22）——回 404 等於洩漏"
            "「這個 id 不存在」給一個無權者",
        )

    def test_A10b_widening_must_not_narrow(self):
        """`BR5.2`：放寬只有一個合法方向（`platform` → `owner` 被拒）。

        收窄是否允許、由誰允許，上游未定（`FD8-4`），故本輪明文拒絕而不是
        默默照辦。
        """
        target = self.seed(
            owner=self.owner, scope=VISIBILITY_SCOPE_PLATFORM, suffix="already-wide"
        )
        self.act_as(self.admin)
        response = self.client.put(
            f"/api/memory/records/{target.id}/scope",
            json={"visibility_scope": VISIBILITY_SCOPE_OWNER},
        )
        self.assertEqual(response.status_code, 422)
        self.db.refresh(target)
        self.assertEqual(target.visibility_scope, VISIBILITY_SCOPE_PLATFORM)
        self.assertEqual(self.audit_rows(target.id), [], "`BR5.4`：不產生事件")


# ---------------------------------------------------------------------------
# A11：稽核查詢（角色模型，與放寬共用判定）
# ---------------------------------------------------------------------------


class AuditQueryTest(MemoryAuthzTestBase):
    """`A11`：`BR6.1` 的 allow/deny ＋ `BR6.3` 的懸空參照。"""

    def test_A11_admin_can_read_audit_events_and_owner_cannot(self):
        """`AC4.3.3`：具角色 → 200；不具 → **403**。

        擁有者**看不到**自己記憶的稽核事件（`[FD2]`=A）：選項 B 被否決的理由是
        它會讓同一個端點有兩種過濾語意，而 `AC4.3.3` 的「被拒絕」在擁有者身上
        會變成「回空集合」——兩者是不同的可觀察結果。
        """
        target = self.seed(owner=self.owner, suffix="audited")
        memory_id = target.id
        # 以 facade 刪除，製造一筆真的稽核事件（不手插，使本條也覆蓋寫入端）。
        self.facade().delete(mint_principal(self.owner), str(memory_id))

        self.act_as(self.admin)
        allowed = self.client.get("/api/memory/audit-events")
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(len(allowed.json()), 1)
        self.assertEqual(allowed.json()[0]["action"], "deleted_by_user")

        self.act_as(self.owner)
        denied = self.client.get("/api/memory/audit-events")
        self.assertEqual(
            denied.status_code,
            403,
            "擁有者讀稽核必須是 403（被拒絕），不是 200 ＋ 空集合",
        )

    def test_A11b_dangling_audit_event_is_still_returned(self):
        """`BR6.3`：`memoryId` 指不到記憶的事件**仍須回傳**，且可分辨。

        過濾掉它會讓 `FR4.7` 在 90 天後變成空話——稽核存在的全部理由就是
        記憶消失之後還答得出「誰刪的」。

        刪除之後記憶列已不存在，故這一筆天然是懸空的：`memory_exists`
        必須是 `False`，而事件本身必須在結果裡。
        """
        target = self.seed(owner=self.owner, suffix="dangling")
        memory_id = target.id
        self.facade().delete(mint_principal(self.owner), str(memory_id))

        self.act_as(self.admin)
        response = self.client.get(
            "/api/memory/audit-events", params={"memory_id": str(memory_id)}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["memory_id"], str(memory_id))
        self.assertFalse(
            body[0]["memory_exists"],
            "記憶已被刪除，故 memory_exists 必須為 False——呼叫端要分辨得出"
            "「稽核指向一則已不存在的記憶」這個狀態（BR6.3）",
        )

    def test_A11c_audit_view_never_carries_memory_content(self):
        """`EC6`：稽核檢視不得含記憶內容。

        稽核比記憶活得久，若它含內容，「保留稽核」就等於「保留被刪除的
        使用者資料」——使用者以為刪了而它還在，`FR4.5` 的 90 天刪除形同虛設。
        """
        target = self.seed(owner=self.owner, suffix="secret-content")
        self.facade().delete(mint_principal(self.owner), str(target.id))

        self.act_as(self.admin)
        response = self.client.get("/api/memory/audit-events")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(FIXTURE_PREFIX, response.text)
        for item in response.json():
            self.assertNotIn("content", item)
            self.assertNotIn("embedding", item)


# ---------------------------------------------------------------------------
# A12–A14：寫入端強制、回應衛生、分頁上限
# ---------------------------------------------------------------------------


class WriteSideEnforcementTest(MemoryAuthzTestBase):
    """`A12`–`A14`：`NFR7.20`／`NFR7.21`／`NFR7.26`／`NFR7.29`。"""

    def test_A13_payload_owner_and_scope_are_ignored_not_rejected(self):
        """`AC4.4.1`／`AC4.4.2`／`AC4.4.3`：酬載帶那兩欄 → **成功（非 422）**。

        **「回成功而非 422」是這一條的全部重點**（`BR1.2` 的
        `violation_behaviour` 逐字）：回錯誤會讓呼叫端以為「換個欄位名就能
        指定」，而忽略使該能力不存在。

        只斷言 `ownerUserId` 等於已驗證身分是不夠的——`BR1.2` 的 note 逐字：
        「只有 `BR1.1` 的話，一個從不檢查酬載的實作也能通過，因為它碰巧沒有讀
        那個欄位。`BR1.2` 要求的是**即使酬載有，也不生效**」。
        """
        self.act_as(self.owner)
        response = self.client.post(
            "/api/memory/records",
            json={
                "kind": "semantic",
                "content": f"{FIXTURE_PREFIX} written by owner",
                # 以下兩欄刻意送出，且刻意指向**別人**與**較寬的範圍**。
                "owner_user_id": self.other.id,
                "ownerUserId": self.other.id,
                "visibility_scope": VISIBILITY_SCOPE_PLATFORM,
                "visibilityScope": VISIBILITY_SCOPE_PLATFORM,
            },
        )
        self.assertEqual(
            response.status_code,
            201,
            "帶了擁有者／可見範圍的酬載必須**成功**而非 422（BR1.2）",
        )
        body = response.json()
        self.assertEqual(
            body["owner_user_id"],
            self.owner.id,
            "擁有者必須是已驗證身分，不是酬載指定的那個（NFR7.20）",
        )
        self.assertEqual(
            body["visibility_scope"],
            VISIBILITY_SCOPE_OWNER,
            "新記憶的可見範圍一律最窄，酬載帶 platform 也不生效（NFR7.21）",
        )

    def test_A13b_write_produces_no_audit_event(self):
        """`NFR7.26`／`BR7.4`：寫入後稽核列數**不變**。

        `action` 的封閉集合沒有任何可用於建立的值——這正是本站裁決
        `contract-summary.md:643`（宣稱 write 也寫稽核）與 `:1386`（只列
        delete 與 widen_scope）矛盾的依據：後者與結構一致。
        """
        before = len(self.audit_rows())
        self.act_as(self.owner)
        response = self.client.post(
            "/api/memory/records",
            json={"kind": "procedure", "content": f"{FIXTURE_PREFIX} no audit"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.audit_rows()), before)

    def test_A13c_write_rejects_values_outside_the_closed_sets(self):
        """`EC2`／`EC3`：`kind` 不在封閉集合、`content` 空白 → **422**。

        與上面的「靜默忽略」刻意不同：那兩欄是**不存在的參數**，
        而這兩個是**不合法的值**。`BR2.3` 的 `violation_behaviour` 要求
        回報不合法的值與合法集合，故訊息裡要有合法值。
        """
        self.act_as(self.owner)
        bad_kind = self.client.post(
            "/api/memory/records",
            json={"kind": "telepathic", "content": f"{FIXTURE_PREFIX} x"},
        )
        self.assertEqual(bad_kind.status_code, 422)
        self.assertIn("semantic", bad_kind.text, "訊息必須列出合法值")

        blank = self.client.post(
            "/api/memory/records", json={"kind": "semantic", "content": "   "}
        )
        self.assertEqual(blank.status_code, 422)

    def test_A13d_episodic_gets_an_expiry_and_others_do_not(self):
        """`EC1`：只有 `episodic` 有 `expiresAt`；另兩種為空。

        **反方向同樣重要**：把 90 天套到 `semantic`／`procedure` 會讓長期記憶
        被清除作業選中。`FR4.5` 的保存期**只**約束 `episodic`。
        """
        self.act_as(self.owner)
        episodic = self.client.post(
            "/api/memory/records",
            json={"kind": "episodic", "content": f"{FIXTURE_PREFIX} episodic"},
        ).json()
        self.assertIsNotNone(episodic["expires_at"])
        for kind in ("semantic", "procedure"):
            body = self.client.post(
                "/api/memory/records",
                json={"kind": kind, "content": f"{FIXTURE_PREFIX} {kind}"},
            ).json()
            self.assertIsNone(body["expires_at"], f"{kind} 不得有保存期上界")

    def test_A12_404_body_never_contains_the_fixture_content(self):
        """`NFR7.31`：404 回應體不含 fixture 記憶的 `content`（字串比對）。

        判準逐字是**字串比對**，不是人工審查。這一條守的是「錯誤訊息不得回傳
        他人記憶的任何欄位」——`MemoryNotFound` 刻意不帶任何查到的欄位。
        """
        mine = self.seed(owner=self.owner, suffix="never-leaked")
        self.act_as(self.other)
        response = self.client.delete(f"/api/memory/records/{mine.id}")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(FIXTURE_PREFIX, response.text)
        self.assertNotIn(self.owner.username, response.text)

    def test_A14_oversized_limit_is_clamped_not_honoured(self):
        """`NFR7.29`：以超大 `limit` 呼叫，回傳筆數**不超過伺服器上限**。

        **收斂而非拒絕**：超大 `limit` 不是錯誤。故期望 **200** 加上被截斷的
        筆數，而不是 422。

        fixture 只有 `MAX_LIST_PAGE_SIZE + 3` 列，使「上限真的生效」可被觀察
        ——若列數少於上限，任何 `limit` 都會回全部，斷言就恆真。
        """
        total = MAX_LIST_PAGE_SIZE + 3
        for index in range(total):
            self.seed(owner=self.owner, suffix=f"bulk-{index}")
        self.act_as(self.owner)

        response = self.client.get(
            "/api/memory/records", params={"limit": 10_000_000}
        )
        self.assertEqual(response.status_code, 200, "超大 limit 不是錯誤")
        self.assertEqual(
            len(response.json()),
            MAX_LIST_PAGE_SIZE,
            f"回傳筆數必須收斂到伺服器上限 {MAX_LIST_PAGE_SIZE}",
        )

    def test_A14b_pagination_offset_does_not_repeat_or_skip_rows(self):
        """`NFR7.28`：分頁不得重複或漏掉列。

        排序鍵含 `id`（次級鍵），故相鄰頁的邊界是穩定的。少了它，
        `created_at` 同值的列在兩頁之間會重複或消失，而那是**靜默的**。
        """
        for index in range(7):
            self.seed(owner=self.owner, suffix=f"page-{index}")
        self.act_as(self.owner)

        first = self.client.get(
            "/api/memory/records", params={"offset": 0, "limit": 3}
        ).json()
        second = self.client.get(
            "/api/memory/records", params={"offset": 3, "limit": 3}
        ).json()
        third = self.client.get(
            "/api/memory/records", params={"offset": 6, "limit": 3}
        ).json()

        self.assertEqual([len(first), len(second), len(third)], [3, 3, 1])
        ids = self.ids_in(first) | self.ids_in(second) | self.ids_in(third)
        self.assertEqual(len(ids), 7, "三頁的聯集必須恰為 7 列，無重複無遺漏")


# ---------------------------------------------------------------------------
# A15：交易邊界（`NFR4.21`）
# ---------------------------------------------------------------------------


class TransactionBoundaryTest(MemoryAuthzTestBase):
    """`A15`：稽核寫入與資料變更同交易；任一失敗則兩者皆不生效。

    `NFR4.21` 的判準逐字：「以交易中止測試：強制失敗後記憶列數與稽核列數
    皆不變」。

    強制失敗的手法是讓稽核寫入違反 `ck_memory_audit_events_action`
    ——那是**資料庫層**的中止，與「應用層自己檢查後放棄」不同：後者證明不了
    交易邊界，只證明有個 if。而那條 CHECK 在 SQLite 上**真的會擋**
    （已實測），故這條測試在 SQLite 上是有效的。
    """

    def test_A15_audit_failure_rolls_back_the_deletion(self):
        import services.memory_service as memory_service

        target = self.seed(owner=self.owner, suffix="transactional")
        memory_id = target.id
        records_before = self.db.query(MemoryRecord).count()
        audits_before = len(self.audit_rows())

        original = memory_service.AUDIT_ACTION_DELETED_BY_USER
        try:
            # 把 action 換成封閉集合外的值，使稽核 INSERT 觸發 CHECK 違反。
            memory_service.AUDIT_ACTION_DELETED_BY_USER = "quietly_vanished"
            with self.assertRaises(Exception):
                memory_service.delete_with_audit(
                    self.db,
                    record=self.db.query(MemoryRecord)
                    .filter(MemoryRecord.id == memory_id)
                    .first(),
                    actor_user_id=self.owner.id,
                )
        finally:
            memory_service.AUDIT_ACTION_DELETED_BY_USER = original
            self.db.rollback()

        self.assertEqual(
            self.db.query(MemoryRecord).count(),
            records_before,
            "稽核寫入失敗時記憶**不得**被刪除——兩次 commit 的實作會在這裡紅",
        )
        self.assertEqual(len(self.audit_rows()), audits_before)
        self.assertIsNotNone(
            self.db.query(MemoryRecord).filter(MemoryRecord.id == memory_id).first()
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
