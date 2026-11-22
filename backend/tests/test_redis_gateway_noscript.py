"""`redis_gateway` 冷啟動的回歸測試：redis-py 8.x 形狀的 `NOSCRIPT`。

由來（`U12 work-orchestrator` code-generation 的 F1，使用者 2026-10-12 裁決本批修正）：
redis-py 8.x 把 Redis 的 `NOSCRIPT` 回覆轉成 `redis.exceptions.NoScriptError`，其訊息為
`No matching script. Please use EVAL.`——**`NOSCRIPT` 前綴已被剝掉**。舊判定只看
`"NOSCRIPT" in str(exc)`，於是冷快取下的 `EVALSHA` 被分類成 `redis_command_error`、
不退回 `EVAL`，所有 Lua 方法都失敗且不會自行恢復。

既有替身（`FakeRedis`）的訊息帶 `NOSCRIPT` 前綴，看不到這個缺陷；本檔的替身改丟新版
形狀。真實 Redis 上的驗證見 `backend/tests_redis/test_work_item_lua.py` 的
`GatewayColdStartTest`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from services.redis_gateway import RedisErrorTypes, RedisGateway, is_noscript_error
from services.session_store import SessionStore
from tests.test_session_store_behaviour import (
    FakeConnectionError,
    FakeOutOfMemoryError,
    FakeRedis,
    FakeResponseError,
    StubClock,
)


class FakeNoScriptError(FakeResponseError):
    """對應 redis-py 8.x 的 `NoScriptError(ResponseError)`：訊息**不含** `NOSCRIPT`。"""


NEW_STYLE_MESSAGE = "No matching script. Please use EVAL."

NEW_STYLE_ERROR_TYPES = RedisErrorTypes(
    connection=(FakeConnectionError,),
    oom=(FakeOutOfMemoryError,),
    command=(FakeResponseError,),
    noscript=(FakeNoScriptError,),
)


class NewStyleNoScriptRedis(FakeRedis):
    """`EVALSHA` 冷快取時拋 redis-py 8.x 形狀的例外。"""

    error_types = NEW_STYLE_ERROR_TYPES

    def _cmd_evalsha(self, sha, numkeys, *rest):
        name = self.loaded.get(sha)
        if name is None:
            raise FakeNoScriptError(NEW_STYLE_MESSAGE)
        return self._run_script(name, int(numkeys), rest)


def _gateway(client):
    clock = StubClock()
    return RedisGateway(
        client,
        error_types=NEW_STYLE_ERROR_TYPES,
        clock=clock,
        sleep=clock.sleep,
        jitter=lambda: 0.0,
    )


class NewStyleNoScriptTest(unittest.TestCase):
    def test_cold_cache_evalsha_falls_back_to_eval_and_succeeds(self):
        """冷快取：`EVALSHA` 拋新版形狀 → 改用 `EVAL` 重送成功，之後 `EVALSHA` 命中。"""
        client = NewStyleNoScriptRedis()
        store = SessionStore(_gateway(client), hierarchy_facade=object(), history_max=5)
        store.append_message("k", "shared", "user", "第一則")
        self.assertEqual(client.calls.count("EVALSHA"), 1)
        self.assertEqual(client.calls.count("EVAL"), 1)
        store.append_message("k", "shared", "user", "第二則")
        self.assertEqual(client.calls.count("EVAL"), 1)  # 第二次直接命中快取
        self.assertEqual(
            [m.text for m in store.load("k").segment("shared").messages], ["第一則", "第二則"]
        )

    def test_both_shapes_are_recognised_and_other_errors_are_not(self):
        self.assertTrue(is_noscript_error(FakeNoScriptError(NEW_STYLE_MESSAGE), NEW_STYLE_ERROR_TYPES))
        self.assertTrue(
            is_noscript_error(FakeResponseError("NOSCRIPT No matching script."), NEW_STYLE_ERROR_TYPES)
        )
        self.assertFalse(is_noscript_error(FakeResponseError("NOPERM denied"), NEW_STYLE_ERROR_TYPES))
        self.assertFalse(is_noscript_error(FakeConnectionError("reset"), NEW_STYLE_ERROR_TYPES))

    def test_old_style_types_without_noscript_still_work(self):
        """沒有宣告 `noscript` 型別（舊版客戶端）時，仍以訊息前綴判定。"""
        legacy = RedisErrorTypes(command=(FakeResponseError,))
        self.assertTrue(is_noscript_error(FakeResponseError("NOSCRIPT x"), legacy))
        self.assertFalse(is_noscript_error(FakeNoScriptError(NEW_STYLE_MESSAGE), legacy))


if __name__ == "__main__":
    unittest.main()
