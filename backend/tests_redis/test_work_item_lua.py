"""`U12 work-orchestrator`：兩支工作項 Lua 在**真實 Redis** 上與參考實作逐案一致。

opt-in，不在 CI（理由見 `tests_redis/__init__.py`）。`REDIS_URL` 未設定或 `redis`
套件不可匯入時整個類別 skip，並在 skip 訊息內寫明原因。

每個案例的做法相同：在真實 Redis 上以隨機前綴的 key 準備一份 Hash 快照、執行
腳本；同一份快照交給 `session_types.ref_*`；比對 (1) 回傳值、(2) 執行後的 Hash
內容（工作項欄位以 JSON 語意比對，因 cjson 與 Python 的鍵序與跳脫不同）、
(3) TTL 不變、(4) key 不存在時腳本不建 key。
"""

from __future__ import annotations

import json
import os
import unittest
import uuid

from tests_redis import redis_skip_reason

_SKIP = redis_skip_reason()

if _SKIP is None:  # pragma: no cover - 取決於環境
    import redis

    from services.redis_gateway import RedisGateway, redis_py_error_types
    from services.session_store import SCRIPT_PUT_WORK_ITEM, SCRIPT_UPDATE_WORK_ITEM
    from services import session_types as T


def _item(**overrides):
    item = {
        "workItemId": "w1",
        "label": "架構設計：架構圖 #12",
        "status": "處理中",
        "capability": "architecture-design",
        "waitingOn": None,
        "failureReason": None,
        "sideEffect": "none",
        "estimateSetId": None,
        "deadlineAt": "2026-10-12T08:05:00+00:00",
        "dispatchStage": "not_dispatched",
        "tags": [],
    }
    item.update(overrides)
    return item


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _semantic(fields):
    """把 Hash 快照轉成可比對的形狀：`wi:*` 欄位以 JSON 語意比對。"""
    if not fields:
        return None
    return {
        name: (json.loads(value) if name.startswith("wi:") else value)
        for name, value in fields.items()
    }


UPDATE_CASES = [
    # (名稱, 初始工作項, 預期 status, 預期 dispatchStage, 補丁)
    ("match_patch", _item(), ["處理中"], "not_dispatched", {"dispatchStage": "request_sent"}),
    ("status_mismatch", _item(), ["等待中"], "not_dispatched", {"status": "已停掉"}),
    ("stage_mismatch", _item(), ["處理中"], "request_sent", {"status": "已停掉"}),
    ("multi_status", _item(status="等待中"), ["處理中", "等待中"], "not_dispatched",
     {"status": "已停掉", "deadlineAt": None}),
    ("null_sets_null", _item(), ["處理中"], "not_dispatched",
     {"failureReason": "逾時", "deadlineAt": None, "status": "失敗"}),
    ("keeps_unpatched", _item(estimateSetId=7), ["處理中"], "not_dispatched",
     {"dispatchStage": "request_sent"}),
    ("empty_array_kept", _item(tags=[]), ["處理中"], "not_dispatched", {"sideEffect": "unknown"}),
    ("unicode", _item(), ["處理中"], "not_dispatched", {"sideEffect": "已存回架構圖〈訂單〉"}),
]


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class WorkItemLuaParityTest(unittest.TestCase):
    """兩支腳本在真實 Redis 上的結果 == 參考實作的結果。"""

    @classmethod
    def setUpClass(cls):
        cls.client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        cls.gateway = RedisGateway(cls.client, error_types=redis_py_error_types())
        # 預先 `SCRIPT LOAD`，讓 gateway 的 `EVALSHA` 直接命中：本類別只驗 Lua 與
        # 參考實作的一致性；冷啟動路徑（`NOSCRIPT` → 退回 `EVAL`）由下面的
        # `GatewayColdStartTest` 單獨驗證，兩件事不互相遮蔽。
        for name in (SCRIPT_PUT_WORK_ITEM, SCRIPT_UPDATE_WORK_ITEM):
            loaded = cls.client.script_load(cls.gateway.script_source(name))
            assert loaded == cls.gateway.script_sha(name)

    def setUp(self):
        self.key = f"u12-lua-test:{uuid.uuid4().hex}"

    def tearDown(self):
        self.client.delete(self.key)

    def _seed(self, fields):
        if fields:
            self.client.hset(self.key, mapping=fields)
            self.client.expire(self.key, 4321)

    def _snapshot(self):
        return self.client.hgetall(self.key) or None

    def _run(self, script, args):
        return int(
            self.gateway.eval_script("test", script, [self.key], args, idempotent=False) or 0
        )

    def test_update_cases_match_the_reference(self):
        for name, item, statuses, stage, patch in UPDATE_CASES:
            with self.subTest(case=name):
                self.client.delete(self.key)
                fields = {"meta": "{}", "wi:w1": _dumps(item)}
                self._seed(fields)
                args = ["wi:w1", _dumps(statuses), stage, _dumps(patch)]
                expected_result, expected_fields = T.ref_update_work_item(fields, *args)
                actual = self._run(SCRIPT_UPDATE_WORK_ITEM, args)
                self.assertEqual(actual, expected_result)
                self.assertEqual(_semantic(self._snapshot()), _semantic(expected_fields))
                self.assertEqual(self.client.ttl(self.key), 4321)

    def test_update_on_missing_key_or_field(self):
        args = ["wi:w1", _dumps(["處理中"]), "not_dispatched", _dumps({"status": "失敗"})]
        self.assertEqual(self._run(SCRIPT_UPDATE_WORK_ITEM, args), 0)
        self.assertEqual(self.client.exists(self.key), 0)
        self._seed({"meta": "{}"})
        self.assertEqual(self._run(SCRIPT_UPDATE_WORK_ITEM, args), 0)
        self.assertEqual(self._snapshot(), {"meta": "{}"})

    def test_put_cases_match_the_reference(self):
        payload = _dumps(_item())
        # key 不存在：不建 key。
        self.assertEqual(self._run(SCRIPT_PUT_WORK_ITEM, ["wi:w1", payload]), 0)
        self.assertEqual(self.client.exists(self.key), 0)
        self.assertEqual(T.ref_put_work_item(None, "wi:w1", payload), (0, None))
        # key 存在：寫入；第二次被拒且不覆寫。
        self._seed({"meta": "{}"})
        self.assertEqual(self._run(SCRIPT_PUT_WORK_ITEM, ["wi:w1", payload]), 1)
        self.assertEqual(self._run(SCRIPT_PUT_WORK_ITEM, ["wi:w1", _dumps({"x": 1})]), 0)
        expected = T.ref_put_work_item({"meta": "{}"}, "wi:w1", payload)[1]
        self.assertEqual(_semantic(self._snapshot()), _semantic(expected))
        self.assertEqual(self.client.ttl(self.key), 4321)

    def test_array_mt_setting_is_restored_for_other_scripts(self):
        """`update_work_item.lua` 暫開 `decode_array_with_array_mt`，結束時必須還原。

        還原失敗會改變 `append_message.lua` 等其他腳本的解碼行為；以一支只回
        `cjson.encode(cjson.decode('[]'))` 的腳本觀察還原後的狀態。
        """
        self._seed({"meta": "{}", "wi:w1": _dumps(_item())})
        self._run(
            SCRIPT_UPDATE_WORK_ITEM,
            ["wi:w1", _dumps(["處理中"]), "not_dispatched", _dumps({"sideEffect": "x"})],
        )
        observed = self.client.eval("return cjson.encode(cjson.decode('[]'))", 0)
        self.assertEqual(observed, "{}")



@unittest.skipIf(_SKIP is not None, _SKIP or "")
class GatewayColdStartTest(unittest.TestCase):
    """**`U10` 冷啟動缺陷的回歸測試（真實 Redis）。**

    redis-py 8.x 把 `NOSCRIPT` 回覆轉成 `NoScriptError`，訊息為
    `No matching script. Please use EVAL.`（前綴已被剝掉）。修正前
    `redis_gateway.is_noscript_error` 只看 `"NOSCRIPT" in str(exc)`，於是腳本快取為空時
    （每次 Redis 重啟後）所有 Lua 方法都拋 `SessionBackendUnavailable`。本測試原以
    `expectedFailure` 記錄該缺陷；使用者 2026-10-12 裁決於本批修正（`is_noscript_error`
    另認 `RedisErrorTypes.noscript`），故改為一般測試。CI 的對應回歸測試是
    `tests/test_redis_gateway_noscript.py`（替身丟新版形狀）。
    """

    def test_evalsha_cold_start_falls_back_to_eval(self):
        client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        client.script_flush()
        gateway = RedisGateway(client, error_types=redis_py_error_types())
        key = f"u12-lua-test:{uuid.uuid4().hex}"
        try:
            client.hset(key, mapping={"meta": "{}"})
            result = gateway.eval_script(
                "test", SCRIPT_PUT_WORK_ITEM, [key], ["wi:w1", "{}"], idempotent=False
            )
            self.assertEqual(int(result), 1)
        finally:
            client.delete(key)


if __name__ == "__main__":
    unittest.main()
