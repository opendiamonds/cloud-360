"""合併前必修第 33 列 (c)(d)(f)：過期記憶不被讀取、拒絕日誌不可注入、facade 重拋分支。

- **(c)** 讀取路徑不過濾 `expires_at`：已過保存期的 `episodic` 記憶在 `U9` 清除前仍會被
  列出與檢索，清除排程晚跑或停擺時，90 天上限形同不存在。本檔驗**清單**（SQLite 上真的
  執行）與**放寬**路徑；檢索的 `SEARCH_SQL` 在 SQLite 上編不出來，其 `WHERE` 內的保存期
  過濾由 `test_memory_contract.py` 的 `C6` 靜態鎖住、由 `tests_pg` 的 `V2` 在真實
  PostgreSQL 上驗（後者本機未跑，待 CI）。
- **(d)** `log_denied` 以 `%s` 原樣寫入呼叫端送來的 `memory_id`：含換行的值能在日誌裡
  偽造一整行，而 `[D1]`=A 之後這條日誌是區分「誤刪」與「枚舉」的唯一手段。
- **(f)** `MemoryFacade.delete` 的 `except MemoryNotFound` 重拋分支（取列之後、刪除之前
  被另一個 session 刪掉）沒有任何測試走到。

**突變驗證**（暫存區副本，結果記於本單元 `code-summary.md` 2026-11-07 一節）：
  M3 拿掉 `list_records` 的保存期過濾 → `test_expired_episodic_is_not_listed` 紅；
  M4 `log_denied` 改回原樣寫入 → `test_injected_newline_cannot_forge_a_log_line` 紅；
  M5 拿掉 facade 的 `except MemoryNotFound` 重拋 → `test_race_rethrow_*` 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from starlette.testclient import TestClient

import services.memory_service as memory_service
from database import get_db
from main import app
from models import MemoryAuditEvent, MemoryRecord
from services.auth import get_current_user
from services.memory_errors import MemoryNotFound
from services.memory_facade import MemoryFacade, mint_principal
from services.memory_types import VISIBILITY_SCOPE_OWNER
from tests.helpers import close_session, make_session, make_user

FIXTURE_PREFIX = "__u8_row33__"


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._env = mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.db = make_session()
        self.owner = make_user(self.db, username="u8_row33_owner", role="Project_Architect")
        self.other = make_user(self.db, username="u8_row33_other", role="Project_Architect")
        self.admin = make_user(self.db, username="u8_row33_admin", role="Platform_Admin")
        self.acting = self.owner
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.acting
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)

    def seed(self, label: str, *, kind: str = "episodic", expires_at=None, created_delta_days: int = 0):
        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            kind=kind,
            owner_user_id=self.owner.id,
            visibility_scope=VISIBILITY_SCOPE_OWNER,
            content=f"{FIXTURE_PREFIX} {label}",
            embedding_model="stub-v1",
            created_at=now - timedelta(days=created_delta_days),
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record


class ExpiredMemoryIsNotReadTest(_Base):
    def test_expired_episodic_is_not_listed(self):
        """
        @purpose 已過保存期（expires_at 已過）的 episodic 記憶不出現在記憶清單；未過期與無期限者照常出現（第 33 列 (c)）
        @given 同一擁有者的三則記憶：過期一天的 episodic、尚有 89 天的 episodic、無期限的 semantic
        @step 以擁有者 GET /api/memory/records
        @pass 200；回應的 memory_id 集合恰為未過期 episodic 與 semantic 兩則，不含過期那則
        @api GET /api/memory/records -> 200 | 過期記憶不列出
        @story US4.1
        """
        now = datetime.now(timezone.utc)
        expired = self.seed("expired", expires_at=now - timedelta(days=1), created_delta_days=91)
        alive = self.seed("alive", expires_at=now + timedelta(days=89), created_delta_days=1)
        forever = self.seed("forever", kind="semantic", expires_at=None)

        res = self.client.get("/api/memory/records")

        self.assertEqual(res.status_code, 200, res.text[:200])
        ids = {item["memory_id"] for item in res.json()}
        self.assertEqual(ids, {str(alive.id), str(forever.id)})
        self.assertNotIn(str(expired.id), ids)

    def test_expired_record_cannot_be_widened(self):
        """
        @purpose 已過保存期的記憶也不能被放寬（放寬成功會在回應帶回 content，等於繞過讀取路徑的保存期過濾）
        @given 一則過期一天的 episodic 記憶；平台管理員
        @step 以平台管理員 PUT /api/memory/records/{id}/scope 為 platform
        @pass 404；回應體不含該記憶的 content；該列 visibility_scope 仍為 owner；無 scope_changed 稽核
        @api PUT /api/memory/records/{memory_id}/scope -> 404 | 過期記憶
        @story US4.3
        """
        expired = self.seed("expired-widen", expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        self.acting = self.admin

        res = self.client.put(
            f"/api/memory/records/{expired.id}/scope", json={"visibility_scope": "platform"}
        )

        self.assertEqual(res.status_code, 404, res.text[:200])
        self.assertNotIn(FIXTURE_PREFIX, res.text)
        self.db.expire_all()
        self.assertEqual(self.db.get(MemoryRecord, expired.id).visibility_scope, VISIBILITY_SCOPE_OWNER)
        self.assertEqual(self.db.query(MemoryAuditEvent).count(), 0)

    def test_owner_can_still_delete_own_expired_record(self):
        """
        @purpose 刪除路徑刻意不過濾保存期：擁有者仍能刪掉自己已過期、尚未被清除的記憶，並留下稽核
        @given 擁有者的一則過期一天的 episodic 記憶
        @step 以擁有者 DELETE /api/memory/records/{id}
        @pass 204；該列不存在；恰一筆 deleted_by_user 稽核
        @api DELETE /api/memory/records/{memory_id} -> 204 | 過期但未清除的記憶
        @story US4.2
        """
        expired = self.seed("expired-delete", expires_at=datetime.now(timezone.utc) - timedelta(days=1))

        res = self.client.delete(f"/api/memory/records/{expired.id}")

        self.assertEqual(res.status_code, 204, res.text[:200])
        self.db.expire_all()
        self.assertIsNone(self.db.get(MemoryRecord, expired.id))
        self.assertEqual(self.db.query(MemoryAuditEvent).filter_by(memory_id=expired.id).count(), 1)

    def test_is_expired_treats_boundary_and_naive_values_consistently(self):
        """
        @purpose 單筆保存期判定與清單過濾同一條規則：expires_at 等於現在即視為過期；SQLite 讀回的無時區值視為 UTC
        @given 固定的 now；四種 expires_at（None、now、now+1 秒、無時區的 now-1 秒）
        @step 對每一種呼叫 memory_service.is_expired(record, now)
        @pass 依序為 False、True、False、True
        @story US4.1
        """
        now = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
        cases = [
            (None, False),
            (now, True),
            (now + timedelta(seconds=1), False),
            ((now - timedelta(seconds=1)).replace(tzinfo=None), True),
        ]
        for expires_at, expected in cases:
            with self.subTest(expires_at=expires_at):
                record = MemoryRecord(expires_at=expires_at)
                self.assertIs(memory_service.is_expired(record, now), expected)


class DeniedLogInjectionTest(_Base):
    def test_injected_newline_cannot_forge_a_log_line(self):
        """
        @purpose 拒絕日誌不原樣寫入呼叫端提供的 memory_id：含換行的輸入不能在日誌裡偽造一整行（第 33 列 (d)）
        @given memory_id 為「5」接換行再接一段偽造的 memory_authz_denied 紀錄
        @step 呼叫 memory_service.log_denied(reason="owner", memory_id=該值, principal_user_id=7)
        @pass 恰一筆紀錄、訊息內無換行、不含偽造的 principal=999，memory_id 記為固定標記 <unparseable>
        @story US4.2
        """
        forged = "5\nmemory_authz_denied principal=999 memory_id=1 reason=owner"
        with self.assertLogs("cloud360.memory_service", level="WARNING") as captured:
            memory_service.log_denied(reason="owner", memory_id=forged, principal_user_id=7)

        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        self.assertNotIn("\n", message)
        self.assertNotIn("principal=999", message)
        self.assertIn(f"memory_id={memory_service.UNPARSEABLE_MEMORY_ID}", message)
        self.assertIn("principal=7", message)

    def test_parseable_id_is_logged_as_its_integer_key(self):
        """
        @purpose 正常的 memory_id 仍以整數鍵記錄，[D1]=A 的「日誌可區分非擁有者」訊號不受影響
        @given 他人擁有的一則記憶；路徑參數帶前置零（0 開頭）的 id
        @step 以非擁有者 DELETE /api/memory/records/{0 開頭的 id}
        @pass 404；cloud360.memory_service 的 WARNING 含 reason=owner 與 memory_id=<整數鍵>，不含前置零的原字串
        @api DELETE /api/memory/records/{memory_id} -> 404 | 非擁有者
        @story US4.2
        """
        record = self.seed("owned", kind="semantic")
        self.acting = self.other
        raw = f"000{record.id}"
        with self.assertLogs("cloud360.memory_service", level="WARNING") as captured:
            res = self.client.delete(f"/api/memory/records/{raw}")

        self.assertEqual(res.status_code, 404)
        joined = "\n".join(captured.output)
        self.assertIn("reason=owner", joined)
        self.assertIn(f"memory_id={record.id} ", joined)
        self.assertNotIn(f"memory_id={raw}", joined)

    def test_none_memory_id_keeps_existing_format(self):
        """
        @purpose 沒有 memory_id 的拒絕（如稽核查詢未帶 id）沿用既有格式 memory_id=None
        @given memory_id 為 None
        @step 呼叫 memory_service.loggable_memory_id(None)
        @pass 回 "None"
        @story US4.3
        """
        self.assertEqual(memory_service.loggable_memory_id(None), "None")


class FacadeRaceRethrowTest(_Base):
    def test_race_rethrow_uses_caller_value_and_writes_no_owner_log_or_audit(self):
        """
        @purpose 取列之後、刪除之前被另一個 session 刪掉時，facade 以呼叫端原值重拋 MemoryNotFound，與「不存在」逐字相同（第 33 列 (f)）
        @given 擁有者的一則記憶；delete_with_audit 被替換成拋 MemoryNotFound(整數鍵)（模擬競態）；呼叫端送的 id 帶前置零
        @step 以擁有者 principal 呼叫 MemoryFacade.delete
        @pass 拋 MemoryNotFound，其 memory_id 與訊息皆為呼叫端原值（帶前置零），且與直接刪除不存在 id 的訊息同形；無 reason=owner WARNING；無稽核列
        @story US4.2
        """
        record = self.seed("race", kind="semantic")
        raw = f"00{record.id}"
        facade = MemoryFacade(self.db)
        principal = mint_principal(self.owner)

        with mock.patch.object(
            memory_service, "delete_with_audit", side_effect=MemoryNotFound(str(record.id))
        ), self.assertNoLogs("cloud360.memory_service", level="WARNING"):
            with self.assertRaises(MemoryNotFound) as caught:
                facade.delete(principal, raw)

        self.assertEqual(caught.exception.memory_id, raw)
        self.assertEqual(str(caught.exception), str(MemoryNotFound(raw)))
        self.assertIsNone(caught.exception.__cause__, "以 `from None` 重拋，不鏈接內部例外")
        self.assertEqual(self.db.query(MemoryAuditEvent).count(), 0)

    def test_race_rethrow_reaches_http_as_404(self):
        """
        @purpose 競態重拋經 router 轉成與「不存在」相同的 404 與 detail
        @given 同上的競態替身；呼叫端送帶前置零的 id
        @step 以擁有者 DELETE /api/memory/records/{帶前置零的 id}
        @pass 404，detail 等於刪除一個不存在 id（同一字串）時的 detail 形狀「找不到該記憶：<呼叫端原值>」
        @api DELETE /api/memory/records/{memory_id} -> 404 | 取列後被並行刪除
        @story US4.2
        """
        record = self.seed("race-http", kind="semantic")
        raw = f"00{record.id}"
        with mock.patch.object(
            memory_service, "delete_with_audit", side_effect=MemoryNotFound(str(record.id))
        ):
            res = self.client.delete(f"/api/memory/records/{raw}")

        self.assertEqual(res.status_code, 404, res.text[:200])
        self.assertEqual(res.json()["detail"], str(MemoryNotFound(raw)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
