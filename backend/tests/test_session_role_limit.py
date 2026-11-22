"""合併前必修第 34 列 (a)：`append_message` 的 `role` 上限 32 字元。

`role` 原本只檢查非空；每段 200 KB 上限（第 18 列）的前提算式只計入 `text`，故超長
`role` 是那個上限的旁路（審查實測 300,000 字元的 `role` 被接受、段達 300,086 B）。
2026-10-31 裁決：`role` 限 32 字元，超過拒寫（拒絕而非截斷，與 `text` 同）。

以 `test_session_store_behaviour.make_store` 的 FakeRedis 夾具執行（不連 Redis）。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 拿掉 `role` 長度檢查 → 案例 2、3 紅；
  M2 上限誤寫為 31 → 案例 1 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from services.session_store import SESSION_ROLE_MAX_CHARS
from tests.test_session_store_behaviour import FIXTURE_KEY, make_store


class SessionRoleLimitTest(unittest.TestCase):
    def test_role_of_exactly_32_chars_is_accepted(self):
        """
        @purpose 恰 32 字元的 role 被接受（邊界內側）；上限常數為裁決值
        @given 新 session（FakeRedis）
        @step append_message(role = 32 個字元)
        @pass 不拋例外，且之後 load 回得到該則訊息
        @story US2.1
        """
        self.assertEqual(SESSION_ROLE_MAX_CHARS, 32)
        store, _, _, _ = make_store()
        store.append_message(FIXTURE_KEY, "shared", "r" * 32, "hello")
        loaded = store.load(FIXTURE_KEY)
        self.assertIsNotNone(loaded)

    def test_role_of_33_chars_is_rejected_and_nothing_is_written(self):
        """
        @purpose 超過 32 字元的 role 被拒寫，且 Redis 未收到任何寫入
        @given 新 session（FakeRedis）
        @step append_message(role = 33 個字元)
        @pass 拋 ValueError；訊息只帶長度不帶值；FakeRedis 無 EVALSHA／HSET 呼叫
        @story US2.1
        """
        store, client, _, _ = make_store()
        with self.assertRaises(ValueError) as ctx:
            store.append_message(FIXTURE_KEY, "shared", "r" * 33, "hello")
        self.assertIn("33", str(ctx.exception))
        self.assertNotIn("r" * 33, str(ctx.exception))
        write_cmds = ("HSET", "HSETNX", "EVALSHA", "EVAL")
        self.assertEqual([c for c in client.calls if c in write_cmds], [])
        # 對照：同一個 store 的合法追加確實會被這個過濾器看見（上一行不是恆真）。
        store.append_message(FIXTURE_KEY, "shared", "user", "hello")
        self.assertNotEqual([c for c in client.calls if c in write_cmds], [])

    def test_huge_role_cannot_bypass_the_segment_limit(self):
        """
        @purpose 審查實測的形狀（300,000 字元的 role）被擋在入口
        @given 新 session（FakeRedis）
        @step append_message(role = 300,000 個字元, text = 短字串)
        @pass 拋 ValueError
        @story US2.1
        """
        store, _, _, _ = make_store()
        with self.assertRaises(ValueError):
            store.append_message(FIXTURE_KEY, "shared", "x" * 300_000, "hi")


if __name__ == "__main__":
    unittest.main()
