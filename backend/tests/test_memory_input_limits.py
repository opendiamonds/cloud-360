"""合併前必修第 33 列 (e)：`POST /api/memory/records` 的 `content` 上限 4000 字元。

內容會整段送進 embedding 提供者並寫入 `TEXT`；無上限時已認證使用者可用超大酬載
消耗 embedding 資源與儲存。2026-10-31 裁決：4000 字元，超過回 422。

邊界兩側都測：恰 4000 → 201（不是「4000 就擋」的差一錯誤）；4001 → 422 且**不寫入**。
以多位元組字元（中文）再測一次邊界，鎖住「以字元計、不以位元組計」。

`EMBEDDING_PROVIDER` 以 `stub` 執行（`unit-test-instructions.md §六`：不 mock U6 的內部）。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 拿掉 `max_length` → 案例 2、4 紅（4001 被接受）；
  M2 上限誤寫為 3999 → 案例 1、3 紅（4000 被擋）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import os
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from database import get_db
from main import app
from models import MemoryRecord
from services.auth import get_current_user
from services.memory_router import MEMORY_CONTENT_MAX_CHARS
from tests.helpers import close_session, make_session, make_user


class MemoryContentLimitTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"})
        self._env.start()
        self.db = make_session()
        self.user = make_user(self.db, username="alice", role="Developer")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        close_session(self.db)
        self._env.stop()

    def post(self, content: str):
        return self.client.post(
            "/api/memory/records", json={"kind": "semantic", "content": content}
        )

    def stored(self) -> int:
        self.db.expire_all()
        return self.db.query(MemoryRecord).count()

    def test_limit_value_is_4000(self):
        """
        @purpose 上限常數為裁決值 4000（避免日後被無聲改動）
        @given memory_router 模組
        @step 讀 MEMORY_CONTENT_MAX_CHARS
        @pass 等於 4000
        @story US4.1
        """
        self.assertEqual(MEMORY_CONTENT_MAX_CHARS, 4000)

    def test_exactly_4000_ascii_chars_is_accepted(self):
        """
        @purpose 恰為上限的內容被接受（邊界內側）
        @given 已認證、已核准的使用者
        @step POST 4000 個 ASCII 字元
        @pass 201，且資料表多一列
        @api POST /api/memory/records -> 201 | 恰 4000 字元
        @story US4.1
        """
        res = self.post("a" * 4000)
        self.assertEqual(res.status_code, 201, res.text[:300])
        self.assertEqual(self.stored(), 1)

    def test_4001_ascii_chars_is_rejected_with_422_and_not_stored(self):
        """
        @purpose 超過上限回 422，且不寫入、不送 embedding
        @given 已認證、已核准的使用者
        @step POST 4001 個 ASCII 字元
        @pass 422，資料表仍為 0 列
        @api POST /api/memory/records -> 422 | 超過 4000 字元
        @story US4.1
        """
        res = self.post("a" * 4001)
        self.assertEqual(res.status_code, 422, res.text[:300])
        self.assertEqual(self.stored(), 0)

    def test_boundary_counts_characters_not_bytes(self):
        """
        @purpose 上限以字元計：4000 個中文字（12000 位元組）被接受，4001 個被拒
        @given 已認證、已核准的使用者
        @step POST 4000 個「記」→ POST 4001 個「記」
        @pass 前者 201、後者 422
        @api POST /api/memory/records -> 201 | 4000 個多位元組字元
        @api POST /api/memory/records -> 422 | 4001 個多位元組字元
        @story US4.1
        """
        self.assertEqual(self.post("記" * 4000).status_code, 201)
        self.assertEqual(self.post("記" * 4001).status_code, 422)
        self.assertEqual(self.stored(), 1)


if __name__ == "__main__":
    unittest.main()
