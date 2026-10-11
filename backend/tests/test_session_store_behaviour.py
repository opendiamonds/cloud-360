"""`U10 session-store` 的行為測試：五個方法、授權委派、段隔離、重入、原因碼。

本檔對應 `unit-test-instructions.md §三` 的第三列。它涵蓋**兩個**元件
（`redis_gateway` ＋ `session_store`），故條數取 `standard` 策略的上緣。

## 替身的範圍（`unit-test-instructions.md §四`，逐字對齊）

**支援**：`HGET`／`HSET`／`HGETALL`／`HDEL`／`EXPIRE`／`TTL`／`EXISTS`／`DEL`／
`EVAL`／`EVALSHA`。Lua 以**呼叫 `session_types` 的參考實作**模擬腳本效果。

**不支援、也不假裝支援**：

- **真正的原子性。** 替身是單執行緒 Python 物件，「原子」在它身上是免費的，
  所以它**證明不了** Lua 在真實 Redis 上的原子性。本檔能證明的是**呼叫形狀**
  （`switch_to_isolated` 只發一次 `EVALSHA`／`EVAL`、零次直接 `HSET`），
  那是突變 `M4` 實際會變紅的那一條，而不是原子性本身。
- **`noeviction` 的 OOM 行為。** 替身無記憶體上限；`redis_oom` 的測試以
  「替身被設定為對下一次指令回覆 `OOM ...`」驅動，驗的是**分類邏輯**。
- **AOF 與重啟還原。** 替身沒有持久化概念。

**這三項的真實驗證點是 `[I1]`=B 的部署後步驟**，不是 CI。這段話寫在這裡，
是為了讓「三個指令全綠」不被讀成「Redis 行為已驗證」。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import hashlib
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.hierarchy_facade import HierarchyForbidden, HierarchyNotFound
from services.redis_gateway import (
    MAX_RETRIES,
    RedisErrorTypes,
    RedisGateway,
    classify_client_error,
    log_session_event,
    session_log_fields,
)
from services.session_errors import (
    REDIS_COMMAND_ERROR,
    REDIS_OOM,
    REDIS_UNREACHABLE,
    SessionBackendUnavailable,
    SessionMessageTooLong,
)
from services.session_store import (
    DEFAULT_MESSAGE_MAX_CHARS,
    HISTORY_MAX_ENV,
    SessionStore,
    resolve_history_max,
)
from services import session_types as T

# ---------------------------------------------------------------------------
# 替身的例外型別（模擬 redis-py 的三組型別，見 `RedisErrorTypes` 的 docstring）
# ---------------------------------------------------------------------------


class FakeConnectionError(Exception):
    """對應 redis-py 的 `ConnectionError`／`TimeoutError`（連線層）。"""


class FakeResponseError(Exception):
    """對應 redis-py 的 `ResponseError`（指令層）。"""


class FakeOutOfMemoryError(FakeResponseError):
    """對應 redis-py 的 `OutOfMemoryError(ResponseError)`。"""


FAKE_ERROR_TYPES = RedisErrorTypes(
    connection=(FakeConnectionError,),
    oom=(FakeOutOfMemoryError,),
    command=(FakeResponseError,),
)


class FakeRedis:
    """手寫 in-memory 替身。**不新增任何測試依賴**（`NFR8.41` 只授權一個）。

    `error_types` 由替身自己宣告，與真實客戶端走**同一個** `classify_client_error`
    ——分類邏輯因此真的被測到。
    """

    error_types = FAKE_ERROR_TYPES

    def __init__(self) -> None:
        self.hashes: dict = {}
        self.ttls: dict = {}
        self.calls: list = []
        self.loaded: dict = {}
        self.fail_next: list = []

    # -- 指令分派 ---------------------------------------------------------

    def execute_command(self, command, *args):
        self.calls.append(command)
        if self.fail_next:
            raise self.fail_next.pop(0)
        handler = getattr(self, f"_cmd_{command.lower().replace(' ', '_')}", None)
        if handler is None:
            raise FakeResponseError(f"ERR unknown command '{command}'")
        return handler(*args)

    def _cmd_hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def _cmd_hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def _cmd_hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value
        return 1

    def _cmd_hdel(self, key, field):
        return 1 if self.hashes.get(key, {}).pop(field, None) is not None else 0

    def _cmd_exists(self, key):
        return 1 if key in self.hashes else 0

    def _cmd_del(self, key):
        self.hashes.pop(key, None)
        self.ttls.pop(key, None)
        return 1

    def _cmd_expire(self, key, ttl):
        self.ttls[key] = int(ttl)
        return 1

    def _cmd_ttl(self, key):
        if key not in self.hashes:
            return -2
        return self.ttls.get(key, -1)

    # -- Lua：EVALSHA 冷啟動 → NOSCRIPT → EVAL（與真實 Redis 同形）---------

    def _cmd_evalsha(self, sha, numkeys, *rest):
        name = self.loaded.get(sha)
        if name is None:
            raise FakeResponseError("NOSCRIPT No matching script. Please use EVAL.")
        return self._run_script(name, int(numkeys), rest)

    def _cmd_eval(self, source, numkeys, *rest):
        name = self._script_name(source)
        self.loaded[hashlib.sha1(source.encode("utf-8")).hexdigest()] = name
        return self._run_script(name, int(numkeys), rest)

    @staticmethod
    def _script_name(source):
        for line in source.splitlines():
            if line.startswith("-- script:"):
                return line.split(":", 1)[1].strip()
        raise FakeResponseError("ERR script is missing its `-- script:` marker")

    def _run_script(self, name, numkeys, rest):
        keys = list(rest[:numkeys])
        argv = list(rest[numkeys:])
        return getattr(self, f"_script_{name}")(keys, argv)

    def _script_append_message(self, keys, argv):
        """以 `session_types.trim_history` 模擬腳本效果（§四 逐字授權）。"""
        key = keys[0]
        field, message_json, cap, ttl = argv[0], argv[1], int(argv[2]), int(argv[3])
        fields = self.hashes.setdefault(key, {})
        arr = json.loads(fields.get(field) or "[]")
        message = json.loads(message_json)
        # 與 `append_message.lua` 同形：`sequence` 在腳本內計算（`BR3.3`）。
        message["sequence"] = (arr[-1]["sequence"] + 1) if arr else 1
        arr.append(message)
        before = len(arr)
        arr = T.trim_history(arr, cap)
        fields[field] = json.dumps(arr, ensure_ascii=False, separators=(",", ":"))
        self.ttls[key] = ttl
        return [len(arr), before - len(arr)]

    def _script_switch_to_isolated(self, keys, argv):
        key = keys[0]
        (
            seg_field,
            tgt_field,
            source_tgt_field,
            meta_field,
            scope,
            created_at,
            ttl,
            empty_messages,
            empty_target,
            default_meta,
        ) = argv
        fields = self.hashes.setdefault(key, {})
        created = 0
        if seg_field not in fields:
            fields[seg_field] = empty_messages
            fields[tgt_field] = fields.get(source_tgt_field, empty_target)
            created = 1
        meta = json.loads(fields.get(meta_field) or default_meta)
        meta.setdefault("pageModes", {})[scope] = "isolated"
        if created:
            meta.setdefault("createdAt", {})[scope] = created_at
        fields[meta_field] = json.dumps(meta, separators=(",", ":"))
        self.ttls[key] = int(ttl)
        return [created]


class StubClock:
    """注入的 clock（`unit-test-instructions.md §六`：不用 `time.sleep`）。"""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list = []

    def __call__(self) -> float:
        self.now += 0.001
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make_gateway(client=None, **kwargs):
    clock = StubClock()
    gateway = RedisGateway(
        client if client is not None else FakeRedis(),
        error_types=FAKE_ERROR_TYPES,
        clock=clock,
        sleep=clock.sleep,
        jitter=lambda: 0.0,
        **kwargs,
    )
    return gateway, clock


# ---------------------------------------------------------------------------
# `redis_gateway`：原因碼分類、重試、日誌白名單
# ---------------------------------------------------------------------------


class ReasonCodeClassificationTest(unittest.TestCase):
    """`NFR4.62`：三種成因必須可區分。兩者同形只是把無聲換成含糊。"""

    def test_connection_layer_failure_is_redis_unreachable(self):
        client = FakeRedis()
        client.fail_next.append(FakeConnectionError("Connection refused"))
        gateway, _ = make_gateway(client, max_retries=0)
        with self.assertRaises(SessionBackendUnavailable) as ctx:
            gateway.hgetall("load", "fixture-key")
        self.assertEqual(ctx.exception.reason, REDIS_UNREACHABLE)
        self.assertEqual(ctx.exception.method, "load")

    def test_oom_reply_is_redis_oom_by_type_and_by_prefix(self):
        """型別優先、字串前綴為退路——兩條路徑各驗一次。

        `noeviction` 的整個意義是讓容量問題**有聲**；退化成
        `redis_command_error` 會讓排查往 ACL 方向走而完全找錯方向。
        """
        for failure in (
            FakeOutOfMemoryError("OOM command not allowed when used memory > 'maxmemory'."),
            FakeResponseError("OOM command not allowed when used memory > 'maxmemory'."),
        ):
            with self.subTest(failure=type(failure).__name__):
                client = FakeRedis()
                client.fail_next.append(failure)
                gateway, _ = make_gateway(client, max_retries=0)
                with self.assertRaises(SessionBackendUnavailable) as ctx:
                    gateway.hset("set_work_target", "fixture-key", "tgt:shared", "{}", idempotent=False)
                self.assertEqual(ctx.exception.reason, REDIS_OOM)

    def test_other_command_errors_are_redis_command_error(self):
        client = FakeRedis()
        client.fail_next.append(FakeResponseError("NOPERM this user has no permissions"))
        gateway, _ = make_gateway(client, max_retries=0)
        with self.assertRaises(SessionBackendUnavailable) as ctx:
            gateway.hgetall("load", "fixture-key")
        self.assertEqual(ctx.exception.reason, REDIS_COMMAND_ERROR)

    def test_non_redis_exceptions_are_re_raised_unchanged(self):
        """`BR4.6`：`HierarchyForbidden` 要能**穿過**本層。把它誤分類成後端
        失效會讓一個授權拒絕看起來像基礎設施故障。"""
        self.assertIsNone(
            classify_client_error(HierarchyForbidden(story_id="K2", action="view"), FAKE_ERROR_TYPES)
        )


class RetryBehaviourTest(unittest.TestCase):
    """`BR6.2`／`[D2]`=A：冪等方法可重試，`append_message` 不重試。"""

    def test_idempotent_command_retries_up_to_the_cap_then_fails(self):
        client = FakeRedis()
        client.fail_next.extend(FakeConnectionError("flap") for _ in range(MAX_RETRIES + 1))
        gateway, clock = make_gateway(client)
        with self.assertRaises(SessionBackendUnavailable):
            gateway.hgetall("load", "fixture-key")
        self.assertEqual(len(clock.slept), MAX_RETRIES)
        self.assertEqual(client.calls.count("HGETALL"), MAX_RETRIES + 1)

    def test_idempotent_command_recovers_when_the_flap_is_transient(self):
        client = FakeRedis()
        client.hashes["fixture-key"] = {"meta": "{}"}
        client.fail_next.append(FakeConnectionError("flap"))
        gateway, _ = make_gateway(client)
        self.assertEqual(gateway.hgetall("load", "fixture-key"), {"meta": "{}"})

    def test_non_idempotent_command_is_not_retried(self):
        """重試 `append_message` 會製造第二則訊息（`K-09` 逐字「非冪等」）。"""
        client = FakeRedis()
        client.fail_next.append(FakeConnectionError("flap"))
        gateway, clock = make_gateway(client)
        with self.assertRaises(SessionBackendUnavailable):
            gateway.hset("append_message", "fixture-key", "seg:shared", "[]", idempotent=False)
        self.assertEqual(clock.slept, [])
        self.assertEqual(client.calls.count("HSET"), 1)


class LogWhitelistRuntimeTest(unittest.TestCase):
    """`NFR4.63`：簽章擋靜態誤用，執行期守衛擋手工 dict。兩層缺一只擋一半。"""

    def test_fields_outside_the_whitelist_are_rejected_at_runtime(self):
        with self.assertRaises(ValueError):
            log_session_event(logging.ERROR, "x", {"text": "fixture-msg-1"})

    def test_none_valued_fields_are_dropped_rather_than_logged_as_null(self):
        self.assertEqual(session_log_fields(method="load"), {"method": "load"})

    def test_error_log_carries_the_session_key(self):
        """`NFR4.61` 逐字：每次拋出都須產生一筆 **ERROR** 級日誌，**含
        `sessionKey`** 與失敗的方法名。

        少了它，一筆日誌說得出「`load` 失敗了」卻說不出**是誰的 session**——
        在一台同時服務多人的 staging 上那排查不了任何事。

        這一條是回歸測試：`sessionKey` 原本**真的漏了**（`_call` 收不到 key），
        而白名單斷言只驗「不得多」、不驗「不得少」，所以沒有任何東西擋住它。
        """
        client = FakeRedis()
        client.fail_next.append(FakeConnectionError("Connection refused"))
        gateway, _ = make_gateway(client, max_retries=0)
        with self.assertLogs("cloud360.session_store", level="ERROR") as captured:
            with self.assertRaises(SessionBackendUnavailable):
                gateway.hgetall("load", "fixture-key")
        record = json.loads(captured.output[0].split("session_backend_unavailable ")[1])
        self.assertEqual(record["sessionKey"], "fixture-key")
        self.assertEqual(record["method"], "load")
        self.assertEqual(record["reason"], REDIS_UNREACHABLE)

    def test_retry_log_carries_the_session_key(self):
        """`observability-design.md §二` 對 `session_retry`（WARN）列了同一個
        欄位，理由相同：重試是用來解釋「某人偶爾很慢」的，而「某人」就是
        `sessionKey`。

        與上一條是**同一個缺陷的第二個入口**——只修被點名的那一處，等於把違規
        從一個位置挪到另一個位置。
        """
        client = FakeRedis()
        client.fail_next.append(FakeConnectionError("flap"))
        client.hashes["fixture-key"] = {"meta": "{}"}
        gateway, _ = make_gateway(client)
        with self.assertLogs("cloud360.session_store", level="WARNING") as captured:
            gateway.hgetall("load", "fixture-key")
        retry = [line for line in captured.output if "session_retry" in line]
        self.assertEqual(len(retry), 1)
        record = json.loads(retry[0].split("session_retry ")[1])
        self.assertEqual(record["sessionKey"], "fixture-key")
        self.assertEqual(record["attempt"], 1)

    def test_every_public_gateway_method_threads_the_session_key_into_its_log(self):
        """**全部**公開方法，不只我想到的那兩個。

        `functional-design:c34` 的形狀：先盤點這個缺陷共有幾個入口，再修。
        gateway 的每一個公開方法都收得到 key，所以每一個失敗路徑都必須帶它出來。
        """
        cases = (
            ("hgetall", lambda g: g.hgetall("load", "fixture-key")),
            ("hget", lambda g: g.hget("load", "fixture-key", "meta")),
            ("hset", lambda g: g.hset("touch", "fixture-key", "meta", "{}", idempotent=True)),
            ("exists", lambda g: g.exists("touch", "fixture-key")),
            ("expire", lambda g: g.expire("touch", "fixture-key", 86400)),
            ("ttl", lambda g: g.ttl("load", "fixture-key")),
            ("delete", lambda g: g.delete("touch", "fixture-key")),
            (
                "eval_script",
                lambda g: g.eval_script(
                    "append_message", "append_message", ["fixture-key"], [], idempotent=False
                ),
            ),
        )
        for label, action in cases:
            with self.subTest(method=label):
                client = FakeRedis()
                client.fail_next.append(FakeConnectionError("Connection refused"))
                gateway, _ = make_gateway(client, max_retries=0)
                with self.assertLogs("cloud360.session_store", level="ERROR") as captured:
                    with self.assertRaises(SessionBackendUnavailable):
                        action(gateway)
                blob = "\n".join(captured.output)
                self.assertIn('"sessionKey": "fixture-key"', blob)

    def test_backend_unavailable_log_carries_no_session_content(self):
        client = FakeRedis()
        client.fail_next.append(FakeConnectionError("Connection refused"))
        gateway, _ = make_gateway(client, max_retries=0)
        with self.assertLogs("cloud360.session_store", level="ERROR") as captured:
            with self.assertRaises(SessionBackendUnavailable):
                gateway.hgetall("load", "fixture-key")
        blob = "\n".join(captured.output)
        self.assertIn("session_backend_unavailable", blob)
        for forbidden in ("fixture-msg", "text", "messages"):
            self.assertNotIn(forbidden, blob)


class ScriptLoadingTest(unittest.TestCase):
    """`Step 5.5`：`EVALSHA` 快取；`NOSCRIPT` 時回退 `EVAL`。

    `NOSCRIPT` 是**正常的冷啟動路徑**（Redis 重啟會清空腳本快取），不是失敗。
    分類成 `redis_command_error` 會讓每次 Redis 重啟後的第一個
    `append_message` 變成一次假故障。
    """

    def test_noscript_falls_back_to_eval_and_then_evalsha_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_dir = Path(tmp)
            (script_dir / "probe.lua").write_text(
                "-- script: probe\nreturn 1\n", encoding="utf-8"
            )
            client = FakeRedis()
            client._script_probe = lambda keys, argv: 1  # type: ignore[attr-defined]
            gateway, _ = make_gateway(client, scripts_dir=script_dir)
            self.assertEqual(
                gateway.eval_script("touch", "probe", ["fixture-key"], [], idempotent=True), 1
            )
            self.assertEqual(client.calls, ["EVALSHA", "EVAL"])
            client.calls.clear()
            gateway.eval_script("touch", "probe", ["fixture-key"], [], idempotent=True)
            self.assertEqual(client.calls, ["EVALSHA"])

    def test_script_source_is_read_from_a_file_not_concatenated(self):
        """`security-design.md §二`：腳本為靜態常數，使用者資料一律經 `ARGV`。"""
        gateway, _ = make_gateway()
        source = gateway.script_source("append_message")
        self.assertIn("-- script: append_message", source)
        self.assertEqual(
            gateway.script_sha("append_message"),
            hashlib.sha1(source.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# `session_store`：五個方法、授權委派、段隔離、重入、長度上限
# ---------------------------------------------------------------------------

FIXTURE_KEY = "brain:session:fixture-user-1"
RESOLVED_FULL = {"projectId": 7, "systemId": 8, "diagramId": 9}
#: `EC7` 的實測形狀：`OPEN-H11` 的新圖沒有系統歸屬，`K-07` 回部分三元組
#: 並**刻意不拒絕**（`hierarchy_service.py:261-273`）。
RESOLVED_PARTIAL = {"projectId": None, "systemId": None, "diagramId": 42}


class FakePrincipal:
    """`unit-test-instructions.md §六`：簡單的具名物件，帶 `user_id`。

    不用真實的 `get_current_user`／`mint_principal`——`BR5.2` 的重點正是本單元
    **不自行取身分**，所以它對 principal 的內部形狀沒有任何要求。
    """

    def __init__(self, user_id: int = 1) -> None:
        self.user_id = user_id


def make_store(facade=None, *, history_max=5, message_max_chars=50):
    client = FakeRedis()
    gateway, clock = make_gateway(client)
    if facade is None:
        facade = Mock()
        facade.resolve_work_target.return_value = dict(RESOLVED_FULL)
    store = SessionStore(
        gateway,
        hierarchy_facade=facade,
        history_max=history_max,
        message_max_chars=message_max_chars,
        now=lambda: "2026-10-09T00:00:00+00:00",
    )
    return store, client, facade, clock


class HappyPathTest(unittest.TestCase):
    """五個方法的 happy path ＋ `BR1.3`／`BR1.6`。"""

    def test_load_returns_none_for_a_missing_key_and_still_renews_ttl(self):
        """`BR1.6`：不存在回「無」而非錯誤——那是新 session 的合法起點。

        `BR1.3`：`W1` 第 4 步逐字「**無論哪一種結果**都續期 TTL」，故 `EXPIRE`
        仍然發出（key 不存在時它是 no-op）。少一個分支就少一個會漏續期的地方。
        """
        store, client, _, _ = make_store()
        self.assertIsNone(store.load(FIXTURE_KEY))
        self.assertIn("EXPIRE", client.calls)

    def test_all_five_methods_renew_the_ttl(self):
        """`BR1.3`：`K-09.observable_side_effects` 逐字「全部方法都會續期 TTL」。

        未續期即等同縮短使用者的 session，屬缺陷。
        """
        store, client, _, _ = make_store()
        store.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-1")
        for label, action in (
            ("load", lambda: store.load(FIXTURE_KEY)),
            ("touch", lambda: store.touch(FIXTURE_KEY)),
            (
                "append_message",
                lambda: store.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-2"),
            ),
            (
                "set_sharing_mode",
                lambda: store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated"),
            ),
            (
                "set_work_target",
                lambda: store.set_work_target(FIXTURE_KEY, "shared", FakePrincipal(), project_id=7),
            ),
        ):
            with self.subTest(method=label):
                client.ttls.pop(FIXTURE_KEY, None)
                action()
                self.assertEqual(client.ttls.get(FIXTURE_KEY), 86400)

    def test_expires_at_comes_from_the_backend_not_from_process_memory(self):
        """`BR1.2`／`EC5`：`expiresAt` 由 TTL **推導**而非獨立可寫。

        本條驗的是它**來自 Redis 的 `TTL` 回覆**，不是在行程內算出來的——
        `BR1.2` 逐字禁止任何狀態放行程記憶體，而一個在 Python 算出的到期時刻
        正是那種狀態（重啟後它會是錯的，而畫面看不出來）。

        ⚠ 這裡**不能**斷言「少於滿額」：`BR1.3` 要求 `load` 自己也續期，故續期
        之後的剩餘期本來就是滿額。`NFR4.57` 的「少於原值」只有在**重啟**這個
        情境下才有意義，而重啟是 `[I1]`=B 的部署後步驟的範圍，替身沒有持久化
        概念（見本檔檔頭）。
        """
        store, client, _, _ = make_store()
        store.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-1")
        client.calls.clear()
        session = store.load(FIXTURE_KEY)
        self.assertIn("TTL", client.calls)
        self.assertEqual(session.expires_at_seconds, client.ttls[FIXTURE_KEY])

    def test_ttl_sentinels_are_not_reported_as_a_remaining_window(self):
        """Redis 的 `-1`（無 TTL）與 `-2`（key 不存在）都**不是**剩餘期。

        把它們當數字傳下去會讓 `NFR4.57` 的區間斷言在錯誤的前提下通過。
        """
        gateway, _ = make_gateway()
        self.assertIsNone(gateway.ttl("load", "missing-key"))

    def test_session_key_must_be_supplied_by_the_caller(self):
        """`BR1.1`：本單元不產生 session key，也不自行推導。"""
        store, _, _, _ = make_store()
        for bad in (None, "", 123):
            with self.subTest(session_key=bad):
                with self.assertRaises(ValueError):
                    store.load(bad)


class AppendMessageTest(unittest.TestCase):
    """`BR3.1`／`BR3.2`／`BR3.3`／`BR3.4`／`OPEN-N10-6`。"""

    def test_segment_id_is_required_and_never_defaults_to_shared(self):
        """`BR3.1`：沒有段識別的追加是**錯誤**，不得預設為共享段。

        預設為共享段正是 `OQ-N4` 逐字指出的壞結果（「附加進同一份歷程 →
        `FR3.2` 在切回時被違反」）。突變 `M2` 正是這一條抓的。
        """
        store, client, _, _ = make_store()
        with self.assertRaises(ValueError):
            store.append_message(FIXTURE_KEY, None, "user", "fixture-msg-1")
        with self.assertRaises(ValueError):
            store.append_message(FIXTURE_KEY, "nope", "user", "fixture-msg-1")
        # 被拒的呼叫**不得留下任何寫入**。
        self.assertNotIn("EVALSHA", client.calls)
        self.assertNotIn("EVAL", client.calls)

    def test_segments_are_isolated(self):
        """`BR3.2`／`AC3.1.2`／`AC6.1.3`：讀某段只得到該段的訊息。

        突變 `M2`（預設寫 shared）在這一條上也會變紅：獨立段會是空的。
        """
        store, _, _, _ = make_store()
        store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        store.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-shared")
        store.append_message(FIXTURE_KEY, "workspace", "user", "fixture-msg-isolated")
        session = store.load(FIXTURE_KEY)
        self.assertEqual(
            [m.text for m in session.segment("shared").messages], ["fixture-msg-shared"]
        )
        self.assertEqual(
            [m.text for m in session.segment("workspace").messages],
            ["fixture-msg-isolated"],
        )

    def test_history_is_trimmed_from_the_oldest_end_per_segment(self):
        """`BR3.4`：上限**每段獨立計算**，超限時丟**最舊**。

        套在「全部段之和」上會讓一頁的活躍對話擠掉另一頁的歷程，而兩者在
        使用者眼中無關。
        """
        store, _, _, _ = make_store(history_max=3)
        store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        for i in range(1, 6):
            store.append_message(FIXTURE_KEY, "shared", "user", f"fixture-msg-{i}")
        store.append_message(FIXTURE_KEY, "workspace", "user", "fixture-msg-w1")
        session = store.load(FIXTURE_KEY)
        self.assertEqual(
            [m.text for m in session.segment("shared").messages],
            ["fixture-msg-3", "fixture-msg-4", "fixture-msg-5"],
        )
        # 另一段不受影響。
        self.assertEqual(len(session.segment("workspace").messages), 1)

    def test_sequence_is_monotonic_within_a_segment(self):
        """`BR3.3`：順序即寫入順序，且 `sequence` 遞增——`U11` 的「第 N−1 輪
        產出」靠它定位（`FR6.1`）。"""
        store, _, _, _ = make_store(history_max=10)
        for i in range(1, 4):
            store.append_message(FIXTURE_KEY, "shared", "user", f"fixture-msg-{i}")
        seqs = [m.sequence for m in store.load(FIXTURE_KEY).segment("shared").messages]
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual(len(set(seqs)), len(seqs))

    def test_too_long_message_raises_message_too_long_not_backend_unavailable(self):
        """`OPEN-N10-6`：訊息太長是**呼叫方的輸入問題**，後端完全健康。

        兩者同型會讓 `U13` 無法分辨「請縮短訊息」與「稍後再試」。
        突變 `M5`（移除長度檢查）正是這一條抓的。
        """
        store, client, _, _ = make_store(message_max_chars=10)
        with self.assertRaises(SessionMessageTooLong) as ctx:
            store.append_message(FIXTURE_KEY, "shared", "user", "x" * 11)
        self.assertNotIsInstance(ctx.exception, SessionBackendUnavailable)
        self.assertEqual((ctx.exception.limit, ctx.exception.actual), (10, 11))
        # 例外訊息**不得含被拒的文字**（`BR3.6`）。
        self.assertNotIn("xxxxx", str(ctx.exception))
        # 被拒的呼叫不留下任何寫入。
        self.assertNotIn("EVALSHA", client.calls)

    def test_message_at_the_limit_is_accepted(self):
        store, _, _, _ = make_store(message_max_chars=10)
        store.append_message(FIXTURE_KEY, "shared", "user", "x" * 10)
        self.assertEqual(len(store.load(FIXTURE_KEY).segment("shared").messages), 1)


class SharingModeTest(unittest.TestCase):
    """`BR2.2`／`BR2.4`／`BR2.5`／`EC3`。"""

    def test_entry_page_cannot_switch_mode(self):
        """`BR2.2`：入口頁恆讀共享段，**不得切換**。

        `AC3.1.1` 逐字「入口頁的脈絡不受影響」。`/cost` 與 `/admin/*` 同樣被拒
        （`BR2.8`：它們不讀任何段，也不出現在 `pageModes`）。
        """
        store, client, _, _ = make_store()
        for scope in ("shared", "entry", "cost", "admin"):
            with self.subTest(scope=scope):
                with self.assertRaises(ValueError):
                    store.set_sharing_mode(FIXTURE_KEY, scope, "isolated")
        self.assertNotIn("EVALSHA", client.calls)

    def test_switching_back_keeps_the_segment_and_re_entering_returns_to_it(self):
        """`BR2.5`／`BR2.4`／`[S2]`=A：切回共享**不刪段**；再切到獨立**回到同一段**。

        每次都新建會讓可重入失效並讓單一 key 無上界成長；刪除即違反已核可的
        `unit-of-work.md:133`「保留」。
        """
        store, _, _, _ = make_store()
        store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        store.append_message(FIXTURE_KEY, "workspace", "user", "fixture-msg-isolated")

        after_back = store.set_sharing_mode(FIXTURE_KEY, "workspace", "shared")
        self.assertEqual(after_back.page_modes["workspace"], "shared")
        # 段仍在，且內容完整。
        self.assertEqual(
            [m.text for m in after_back.segment("workspace").messages],
            ["fixture-msg-isolated"],
        )

        again = store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        self.assertEqual(again.page_modes["workspace"], "isolated")
        self.assertEqual(
            [m.text for m in again.segment("workspace").messages],
            ["fixture-msg-isolated"],
        )

    def test_switching_one_page_leaves_the_other_untouched(self):
        """`BR2.3`：只改 `pageModes[P]`，其餘頁面不動。"""
        store, _, _, _ = make_store()
        session = store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        self.assertEqual(session.page_modes["workspace"], "isolated")
        self.assertEqual(session.page_modes["assessment"], "shared")
        self.assertNotIn("assessment", session.segments)

    def test_new_segment_inherits_the_shared_work_target(self):
        """`BR4.2`／`AC3.1.3`：新建獨立段時以共享段**當下**的作業對象初始化
        （逐欄複製，含 `null`）——否則獨立對話第一則訊息說「這張圖」會失敗。"""
        store, _, _, _ = make_store()
        store.set_work_target(FIXTURE_KEY, "shared", FakePrincipal(), project_id=7)
        session = store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        shared = session.segment("shared")
        isolated = session.segment("workspace")
        self.assertEqual(
            (isolated.project_id, isolated.system_id, isolated.diagram_id),
            (shared.project_id, shared.system_id, shared.diagram_id),
        )

    def test_switch_to_isolated_is_a_single_script_call_not_three_writes(self):
        """`EC3`／`reliability-design.md §三` 第 3 列：建段＋複製＋改模式必須在
        **同一支 Lua** 內——三次獨立寫入之間崩潰會留下「模式已改為 isolated 但
        段不存在」。

        ⚠ **這一條驗的是呼叫形狀，不是原子性。** 替身是單執行緒 Python 物件，
        「原子」在它身上是免費的。能被機械判定的是：切換路徑**只發一次**
        `EVALSHA`／`EVAL`、**零次**直接 `HSET`。突變 `M4`（改回三次獨立寫入）
        在這一條上變紅；真正的原子性只能在真實 Redis 上驗，而那是 `[I1]`=B
        的部署後步驟的範圍。
        """
        store, client, _, _ = make_store()
        # **先讓 session 存在**，使 `_ensure_meta` 成為 no-op。
        #
        # 這一行是審查 `R-01` 的修正帶來的：`set_sharing_mode` 現在會在第一次
        # 寫入時建立 `meta` 與 `seg:shared`（`EC1`），那是**兩次正當的 HSET**，
        # 與本條要驗的三步驟無關。把 session 的「建立」與「切換」分開，才讓
        # 下面的 `HSET == 0` 仍然精確指向「切換路徑本身不發直接寫入」——
        # 改成斷言 `HSET == 2` 會把 `_ensure_meta` 的內部實作寫進斷言裡，
        # 而那會在它多寫一個欄位時假性紅燈。
        store.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-1")
        client.calls.clear()
        store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        script_calls = [c for c in client.calls if c in ("EVAL", "EVALSHA")]
        # 冷啟動：EVALSHA → NOSCRIPT → EVAL，故恰好一次腳本執行。
        self.assertEqual(script_calls, ["EVALSHA", "EVAL"])
        self.assertEqual(client.calls.count("HSET"), 0)


class FirstWriteEstablishesTheSharedSegmentTest(unittest.TestCase):
    """`EC1`：**任何**第一次寫入都必須讓 `segments` 含 `shared`。

    這是審查 `R-01`（Major）的回歸測試。`set_sharing_mode` 原本**沒有**呼叫
    `_ensure_meta`（`append_message` 與 `set_work_target` 都有），於是「使用者
    開了 `/workspace`，在送出任何訊息之前就切換模式」這條真實路徑會留下
    `segments == {}`（切 `shared`）或只有 `workspace` 而無 `shared`
    （切 `isolated`）——兩者都讓 `EC1` 為假。

    **為什麼 79 條測試全都沒碰到它**：每一個 `set_sharing_mode` 的測試都在
    `make_store()` 之後直接切模式，但斷言的是**模式與段內容**，沒有一條斷言
    「`shared` 段存在」；而其他測試若先 `append_message` 就已經順手建立了
    `shared`。缺的不是一個案例，是**一整類斷言**：我驗了「不得多」
    （日誌不得含內容、被拒的呼叫不得留下寫入），從來沒有驗「**必須有**」。
    這與 `NFR4.61` 的 `sessionKey` 漏失是**同一個形狀**的疏漏。

    故本類**逐一枚舉全部四個寫入入口**，而不是只補被點名的那一個。
    """

    #: 四個會寫入的入口（`load`／`touch` 刻意不在內——`BR1.6` 要求 `load` 對
    #: 不存在的 key 回 `None`，而讓 `touch` 建立 session 會把「續期」變成
    #: 「建立」，兩者都不該建段）。
    FIRST_WRITES = (
        ("append_message", lambda st: st.append_message(FIXTURE_KEY, "shared", "user", "fixture-msg-1")),
        ("set_work_target", lambda st: st.set_work_target(FIXTURE_KEY, "shared", FakePrincipal(), project_id=7)),
        ("set_sharing_mode(shared)", lambda st: st.set_sharing_mode(FIXTURE_KEY, "workspace", "shared")),
        ("set_sharing_mode(isolated)", lambda st: st.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")),
    )

    def test_every_write_entry_point_creates_the_shared_segment(self):
        for label, action in self.FIRST_WRITES:
            with self.subTest(first_write=label):
                store, _, _, _ = make_store()
                action(store)
                session = store.load(FIXTURE_KEY)
                self.assertIsNotNone(session, "第一次寫入之後 load 不得回 None")
                self.assertIn(
                    "shared",
                    session.segments,
                    f"{label} 作為第一次寫入沒有建立 shared 段——EC1 為假",
                )

    def test_isolated_first_write_satisfies_ec1_and_ec3_together(self):
        """`EC3`（`pageModes[P] == isolated` ⇒ `segments[P]` 存在）原本**成立**，
        而 `EC1` 不成立——所以只檢查 `EC3` 的人看不到這個缺陷。兩條一起斷言。
        """
        store, _, _, _ = make_store()
        session = store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        self.assertIn("shared", session.segments)          # EC1
        self.assertEqual(session.page_modes["workspace"], "isolated")
        self.assertIn("workspace", session.segments)        # EC3

    def test_load_and_touch_do_not_create_a_session(self):
        """反向界線：`EC1` 的修法**不得**蔓延成「任何方法都建段」。

        `BR1.6` 要求 `load` 對不存在的 key 回 `None`（那是新 session 的合法
        起點）；`touch` 只續期。若它們也建段，`load` 就再也不會回 `None`，
        而 `U13` 的 `W1` 第 5 步（回「無」時建立新 session）會變成死碼。
        """
        store, client, _, _ = make_store()
        self.assertIsNone(store.load(FIXTURE_KEY))
        store.touch(FIXTURE_KEY)
        self.assertNotIn(FIXTURE_KEY, client.hashes)
        self.assertIsNone(store.load(FIXTURE_KEY))


class WorkTargetAuthorizationTest(unittest.TestCase):
    """`BR4.6`／`BR4.7`／`NFR4.47`：授權委派與**逐段**驗證。ADR-0006 的 IAM 面。"""

    def test_resolved_result_is_stored_not_the_caller_supplied_ids(self):
        """`security-design.md §一` 第 2 點：寫入**解析結果**。

        若寫入呼叫方傳入的原始識別碼，`K-07` 的檢查就只是一道裝飾。
        突變 `M3` 正是這一條抓的。
        """
        facade = Mock()
        facade.resolve_work_target.return_value = {
            "projectId": 101,
            "systemId": 202,
            "diagramId": 303,
        }
        store, _, _, _ = make_store(facade)
        session = store.set_work_target(
            FIXTURE_KEY, "shared", FakePrincipal(), project_id=1, system_id=2, diagram_id=3
        )
        segment = session.segment("shared")
        self.assertEqual(
            (segment.project_id, segment.system_id, segment.diagram_id), (101, 202, 303)
        )

    def test_hierarchy_exceptions_propagate_unchanged_and_nothing_lands(self):
        """`BR4.6` 逐字「原樣向上傳遞」。**且不落地**（`NFR4.47` 的 deny 面）。

        若包成 `SessionBackendUnavailable`，一個授權拒絕看起來就像基礎設施故障。
        """
        for failure in (
            HierarchyForbidden(story_id="K2", action="view"),
            HierarchyNotFound("查不到"),
        ):
            with self.subTest(failure=type(failure).__name__):
                facade = Mock()
                facade.resolve_work_target.side_effect = failure
                store, client, _, _ = make_store(facade)
                with self.assertRaises(type(failure)):
                    store.set_work_target(
                        FIXTURE_KEY, "shared", FakePrincipal(), project_id=7
                    )
                stored = client.hashes.get(FIXTURE_KEY, {})
                self.assertNotIn("tgt:shared", stored)

    def test_second_segment_is_validated_on_its_own(self):
        """`BR4.7`／`NFR4.47`：**對第二段也跑一次 allow/deny**。

        `[S3]`=A 把作業對象從一組變成每段一組；驗證若仍只跑一次，段數一多就有
        N−1 組未驗的值。只測 `shared` 段會漏掉 `[S3]`=A 新引入的那一面。
        """
        # allow
        facade = Mock()
        facade.resolve_work_target.return_value = dict(RESOLVED_FULL)
        store, _, _, _ = make_store(facade)
        store.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        session = store.set_work_target(
            FIXTURE_KEY, "workspace", FakePrincipal(), project_id=7
        )
        self.assertEqual(session.segment("workspace").project_id, 7)
        self.assertEqual(facade.resolve_work_target.call_count, 1)

        # deny — 同一段、同一個呼叫形狀，只有 facade 的結果不同
        facade_deny = Mock()
        facade_deny.resolve_work_target.side_effect = HierarchyForbidden(
            story_id="K2", action="view"
        )
        store2, client2, _, _ = make_store(facade_deny)
        store2.set_sharing_mode(FIXTURE_KEY, "workspace", "isolated")
        # `tgt:workspace` 此時**已經存在**——它是 `BR4.2` 的初始化複製寫的，
        # 來源是已驗證過的共享段值（那正是 `BR4.7` 唯一的例外）。故 deny 面的
        # 正確斷言不是「欄位不存在」，而是「**被拒的那次呼叫沒有改動它**」。
        before = client2.hashes[FIXTURE_KEY]["tgt:workspace"]
        with self.assertRaises(HierarchyForbidden):
            store2.set_work_target(
                FIXTURE_KEY, "workspace", FakePrincipal(), project_id=7
            )
        self.assertEqual(client2.hashes[FIXTURE_KEY]["tgt:workspace"], before)
        self.assertNotIn("7", client2.hashes[FIXTURE_KEY]["tgt:workspace"])

    def test_partial_work_target_is_stored_verbatim_without_inference(self):
        """`BR4.5`／`EC7`：`OPEN-H11` 的新圖沒有系統歸屬。

        本單元**不推導、不補齊、不拒絕**；推導會與 `K-07` 形成兩套可能分歧的
        規則，拒絕會讓那些既有架構圖無法被選為作業對象。
        """
        facade = Mock()
        facade.resolve_work_target.return_value = dict(RESOLVED_PARTIAL)
        store, _, _, _ = make_store(facade)
        segment = store.set_work_target(
            FIXTURE_KEY, "shared", FakePrincipal(), diagram_id=42
        ).segment("shared")
        self.assertEqual(
            (segment.project_id, segment.system_id, segment.diagram_id), (None, None, 42)
        )

    def test_principal_must_be_passed_in(self):
        """`BR5.2`：本模組沒有第二個取得身分的途徑，故 `None` 是呼叫錯誤。"""
        store, _, facade, _ = make_store()
        with self.assertRaises(ValueError):
            store.set_work_target(FIXTURE_KEY, "shared", None, project_id=7)
        facade.resolve_work_target.assert_not_called()

    def test_segment_id_is_required_for_set_work_target(self):
        """`BR4.3`：只改**指定**那一段——寫到別段會讓該段的「離開時狀態」被
        遠端改寫。"""
        store, _, facade, _ = make_store()
        with self.assertRaises(ValueError):
            store.set_work_target(FIXTURE_KEY, "nope", FakePrincipal(), project_id=7)
        facade.resolve_work_target.assert_not_called()


class StartupConfigurationTest(unittest.TestCase):
    """`BR3.5`／`NFR8.40`：上限參數缺值時**大聲失敗**。"""

    def test_missing_history_max_refuses_to_start(self):
        """把缺值讀成「無上限」會讓單一 Redis key 無上界成長，而那是無聲的。"""
        for env in ({}, {HISTORY_MAX_ENV: ""}, {HISTORY_MAX_ENV: "   "}):
            with self.subTest(env=env):
                with self.assertRaises(RuntimeError) as ctx:
                    resolve_history_max(env)
                self.assertIn(HISTORY_MAX_ENV, str(ctx.exception))

    def test_non_positive_or_non_numeric_history_max_refuses_to_start(self):
        for value in ("0", "-1", "abc", "1.5"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    resolve_history_max({HISTORY_MAX_ENV: value})

    def test_valid_history_max_is_parsed(self):
        self.assertEqual(resolve_history_max({HISTORY_MAX_ENV: "200"}), 200)

    def test_message_cap_default_is_a_named_constant(self):
        """`OPEN-N10-6` 的數值是本站選的；它是具名常數而不是魔術數字，
        且**刻意不是**第二個環境變數（見 `session_store` 的註解）。"""
        self.assertIsInstance(DEFAULT_MESSAGE_MAX_CHARS, int)
        self.assertGreater(DEFAULT_MESSAGE_MAX_CHARS, 0)
