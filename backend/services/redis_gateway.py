"""redis_gateway.py — `U10 session-store` 的儲存層

**契約（`session_store.py` 依賴，請勿變更）**

本模組是**唯一**接觸 Redis 客戶端的地方。它刻意**不認識** `BrainSession` 的
語意——段、歷程、作業對象、頁面模式一概不懂，只懂 Hash 欄位、TTL 與 Lua。
分層的理由是 `team.md` 的「新模組一律走三層形狀，純運算下沉到不讀 DB 的
函式」：`session_store`（商業邏輯）→ `redis_gateway`（儲存層）→
`session_types`（純函式）。

## 日誌白名單是一個**簽章**，不是一份文件（`NFR4.63`／`BR3.6`）

`session_log_fields()` 的參數列**就是** `NFR4.63` 的白名單，沒有第二份清單，
而且它**不接受任意 `**kwargs`**。`observability-design.md §一` 逐字：
「白名單若只存在於文件，下一個人加一個欄位時不會有任何東西擋他。」

本單元最容易出的錯是 `logger.warning(f"...{session}")`——它在功能上完全正常、
測試也會綠，而它把整段對話寫進公開可讀的日誌（本 repo 為 public，Actions log
公開可讀）。故白名單做成簽章，簽章擋得住，文件擋不住。

**參數名刻意是 camelCase**：它們是**日誌欄位名**（wire format），與
`observability-design.md §一` 的 JSON 逐字相同。既有前例是
`hierarchy_service.resolve_work_target` 回的 `{"projectId": ...}`——序列化邊界
用 camelCase 是本 repo 的既成慣例。讓簽章與欄位名逐字相同，是為了讓
「白名單 = 簽章」這句話在讀程式時不需要再轉換一次。

## 三種原因碼的判定（`NFR4.62`）

判定是**型別優先、字串前綴為退路**：

1. 客戶端的連線層例外（`ConnectionError`／`TimeoutError`）→ `redis_unreachable`
2. 專屬的 OOM 型別，或回覆以 `OOM ` 開頭 → `redis_oom`
3. 其餘指令層錯誤（`NOPERM`、腳本錯誤）→ `redis_command_error`

`observability-design.md §三` 把第 2 項標為**中風險**：靠字串比對時，錯誤訊息
文字是 Redis 的實作細節。本檔的處置是先試型別（`OutOfMemoryError`），字串前綴
只在客戶端沒有該型別時生效，並把這個退路明寫在 `classify_client_error` 的
docstring 裡（`OPEN-N10-5` 的承接）。

## 為什麼客戶端是**注入**的

`unit-test-instructions.md §四` 定下手寫 in-memory 替身（`NFR8.41` 只授權**一個**
新依賴，不含 `fakeredis` 之類的測試套件）。注入點是建構子，故本模組在測試中
**完全不 import redis-py**——真實客戶端只在 `build_redis_client()` 內被延遲
匯入。這同時讓本模組在未安裝 redis-py 的開發機上仍可被匯入與測試。

## 替身證明不了什麼（如實記載）

替身是單執行緒 Python 物件，「原子」在它身上是免費的，所以它**證明不了** Lua
在真實 Redis 上的原子性；它也沒有記憶體上限與 AOF。三者的真實驗證點是
`[I1]`=B 的部署後步驟，不是 CI。
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from services.session_errors import (
    REDIS_COMMAND_ERROR,
    REDIS_OOM,
    REDIS_UNREACHABLE,
    SessionBackendUnavailable,
)

logger = logging.getLogger("cloud360.session_store")

# ---------------------------------------------------------------------------
# 連線池與逾時（`performance-design.md` 的算式；`[D2]`=A）
# ---------------------------------------------------------------------------
#
#   Pool size = RPS × 平均請求時間(s) × 1.5 = 300 × 0.02 × 1.5 = 9
#
# `min 5` 讓閒置期維持暖連線（避免首次互動吃到建立連線的成本）；`max 20` 是
# 算式結果的兩倍餘裕。算式的輸入有一項是**假設**（每個 session 每秒一次互動），
# 如實標明；未來有實測 RPS 須重算。
POOL_MIN_SIZE = 5
POOL_MAX_SIZE = 20
POOL_IDLE_TIMEOUT_SECONDS = 600
POOL_MAX_LIFETIME_SECONDS = 1800

#: 只在建立連線時發生；`POOL_MIN_SIZE` 的暖連線使它不在穩態路徑上。
CONNECT_TIMEOUT_SECONDS = 2.0

#: **它是 P99 的上界，不是 P95 的**：`NFR3.40`／`NFR3.41` 的 20ms 是 P95，
#: 而一次逾時會產生一個 1 秒的樣本。
COMMAND_TIMEOUT_SECONDS = 1.0

#: 冪等方法的重試次數上界（`BR6.2`）。最壞情況
#: `1s + backoff + 1s + backoff + 1s ≈ 3.3s`——**這超過 `NFR3` 的 2 秒首字預算**，
#: 明寫而非隱含：重試只保護**可救的抖動**，Redis 真的不可用時使用者會等到
#: 逾時鏈走完。兩者不矛盾（`NFR3` 的判定逐字以 **P50** 為門檻）。
MAX_RETRIES = 2
RETRY_BACKOFF_BASE_SECONDS = 0.05

#: `ADR-005`：24 小時，每次互動續期（`BR1.3`）。
SESSION_TTL_SECONDS = 86400

SCRIPTS_DIR = Path(__file__).resolve().parent / "session_scripts"

SCRIPT_APPEND_MESSAGE = "append_message"
SCRIPT_SWITCH_TO_ISOLATED = "switch_to_isolated"


# ---------------------------------------------------------------------------
# 日誌白名單（`NFR4.63`）——**簽章就是清單**
# ---------------------------------------------------------------------------

#: `observability-design.md §一` 的欄位集合，逐字。`test_session_contract.py`
#: 以 AST 斷言 `session_log_fields` 的 keyword-only 參數名**恰為**這七個，
#: 且它沒有 `*args`／`**kwargs`。
LOG_FIELD_NAMES = (
    "sessionKey",
    "segmentId",
    "method",
    "reason",
    "elapsedMs",
    "droppedCount",
    "attempt",
)

#: **明確排除**（`security-design.md §一`／`observability-design.md §一`）：
#: `SessionMessage.text`、整個 `ConversationSegment`、整個 `BrainSession`、
#: 以及三層作業對象識別碼的**組合**（分級為 Internal，逐字「組合起來會洩漏
#: 某人正在看哪個專案」）。白名單原本就不含它們——此處把「不在白名單內」
#: 這件事講明白，避免被讀成未定。
LOG_FIELDS_EXPLICITLY_EXCLUDED = (
    "text",
    "messages",
    "segment",
    "session",
    "projectId",
    "systemId",
    "diagramId",
)


def session_log_fields(
    *,
    sessionKey: Optional[str] = None,
    segmentId: Optional[str] = None,
    method: Optional[str] = None,
    reason: Optional[str] = None,
    elapsedMs: Optional[int] = None,
    droppedCount: Optional[int] = None,
    attempt: Optional[int] = None,
) -> dict:
    """唯一被允許組出日誌欄位的函式（`NFR4.63`）。

    **不接受任意 `**kwargs`**——這是本單元的安全邊界，不是風格選擇。
    要加一個欄位必須改這個簽章，而改簽章會被 `test_session_contract.py` 擋下，
    於是「加欄位」變成一個需要解釋的動作而不是一次手滑。
    """
    candidate = {
        "sessionKey": sessionKey,
        "segmentId": segmentId,
        "method": method,
        "reason": reason,
        "elapsedMs": elapsedMs,
        "droppedCount": droppedCount,
        "attempt": attempt,
    }
    return {name: value for name, value in candidate.items() if value is not None}


def log_session_event(level: int, event: str, fields: Mapping[str, Any]) -> None:
    """輸出一筆結構化日誌。`fields` **必須**來自 `session_log_fields()`。

    執行期再擋一次白名單：簽章擋得住靜態的誤用，但 `log_session_event(…, {…})`
    可以被塞一個手工 dict。兩層都有，缺一層就是只擋得住一半。
    """
    unknown = sorted(set(fields) - set(LOG_FIELD_NAMES))
    if unknown:
        raise ValueError(
            f"日誌欄位 {unknown} 不在白名單 {list(LOG_FIELD_NAMES)} 內（NFR4.63）"
        )
    logger.log(level, "%s %s", event, json.dumps(dict(fields), sort_keys=True))


# ---------------------------------------------------------------------------
# 原因碼分類（`NFR4.62`）——純函式，型別集合由呼叫端提供
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RedisErrorTypes:
    """客戶端的三組例外型別。

    由客戶端自己宣告，而不是由本模組猜——真實客戶端給 redis-py 的型別，
    in-memory 替身給它自己的型別。**同一個分類函式跑兩種來源**，使
    `classify_client_error` 的邏輯真的被測到，而未被測到的只剩
    `redis_py_error_types()` 那五行延遲匯入。
    """

    connection: tuple = ()
    oom: tuple = ()
    command: tuple = ()
    #: `EVALSHA` 冷快取的專屬型別（redis-py 8.x 的 `NoScriptError`）。**預設為空**：
    #: 舊版客戶端沒有它，此時 `is_noscript_error` 只靠訊息前綴判定（原行為不變）。
    noscript: tuple = ()


def classify_client_error(exc: BaseException, types: RedisErrorTypes) -> Optional[str]:
    """把客戶端例外對應到三個原因碼之一；非 Redis 例外回 `None`。

    回 `None` 的意思是「這不是後端失效」——呼叫端必須**原樣重拋**，不得包成
    `SessionBackendUnavailable`。`HierarchyForbidden` 要能穿過本層（`BR4.6`
    逐字「原樣向上傳遞」），而把它誤分類成後端失效會讓一個授權拒絕看起來像
    基礎設施故障。

    判定順序是**型別優先**：

    1. `types.oom` —— redis-py 的 `OutOfMemoryError`。
    2. `types.connection` —— 連線拒絕／逾時／DNS。
    3. `types.command` —— 指令層錯誤；此時再看字串前綴 `OOM `。

    **第 3 步的字串前綴是退路，不是主判據**（`observability-design.md §三` 把
    它標為中風險：錯誤訊息文字是 Redis 的實作細節）。它存在是因為舊版客戶端
    可能沒有 `OutOfMemoryError` 這個子型別，而 `noeviction` 的整個意義就是讓
    容量問題**有聲**——退化成 `redis_command_error` 會讓排查往 ACL 方向走。
    """
    if types.oom and isinstance(exc, types.oom):
        return REDIS_OOM
    if types.connection and isinstance(exc, types.connection):
        return REDIS_UNREACHABLE
    if types.command and isinstance(exc, types.command):
        if str(exc).startswith("OOM "):
            return REDIS_OOM
        return REDIS_COMMAND_ERROR
    return None


def is_noscript_error(exc: BaseException, types: RedisErrorTypes) -> bool:
    """`EVALSHA` 的腳本不在 Redis 的腳本快取裡（`NOSCRIPT`）。

    這**不是**失敗——它是正常的冷啟動路徑（Redis 重啟會清空腳本快取），
    處置是以 `EVAL` 送出完整腳本原文。分類成 `redis_command_error` 會讓每次
    Redis 重啟後的第一個 `append_message` 變成一次假故障。
    """
    # redis-py 8.x 把 `NOSCRIPT` 回覆轉成 `NoScriptError`，訊息為
    # `No matching script. Please use EVAL.`——**前綴已被剝掉**，只看字串會把每次
    # Redis 重啟後的冷快取判成 `redis_command_error`，且永遠不會以 `EVAL` 補上快取
    # （`U12` code-generation 的 F1，以真實 Redis 實測）。故先認型別，字串前綴保留為
    # 舊版客戶端的退路。
    if types.noscript and isinstance(exc, types.noscript):
        return True
    return bool(types.command) and isinstance(exc, types.command) and "NOSCRIPT" in str(exc)


def redis_py_error_types() -> RedisErrorTypes:
    """延遲匯入 redis-py 並取出三組型別。

    **延遲**是刻意的：本模組在測試中完全不 import redis-py（替身注入），
    而未安裝該套件的開發機也要能匯入本模組。`OutOfMemoryError` 以
    `getattr` 取得——舊版客戶端沒有它時退回字串前綴判定（見
    `classify_client_error`）。
    """
    from redis import exceptions as redis_exceptions  # 延遲匯入：見 docstring

    oom = getattr(redis_exceptions, "OutOfMemoryError", None)
    # `NoScriptError` 同樣以 `getattr` 取得：舊版客戶端沒有它時不得 import 失敗。
    noscript = getattr(redis_exceptions, "NoScriptError", None)
    return RedisErrorTypes(
        connection=(
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
        ),
        oom=(oom,) if oom is not None else (),
        command=(redis_exceptions.ResponseError,),
        noscript=(noscript,) if noscript is not None else (),
    )


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


def _as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


class RedisGateway:
    """Hash／TTL／Lua 的薄封裝。**不認識 session 語意。**

    `clock` 與 `sleep` 是注入的（`unit-test-instructions.md §六`：不用
    `time.sleep`），讓重試與 `elapsedMs` 的測試可預測。
    """

    def __init__(
        self,
        client: Any,
        *,
        error_types: Optional[RedisErrorTypes] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        max_retries: int = MAX_RETRIES,
        scripts_dir: Path = SCRIPTS_DIR,
    ) -> None:
        self._client = client
        self._error_types = (
            error_types
            if error_types is not None
            else getattr(client, "error_types", RedisErrorTypes())
        )
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        self._max_retries = max_retries
        self._scripts_dir = scripts_dir
        self._script_cache: dict = {}

    # -- 腳本載入（`Step 5.5`）---------------------------------------------

    def script_source(self, name: str) -> str:
        """腳本原文。**靜態常數，從檔案讀取，絕不以字串拼接組成**
        （`security-design.md §二` 的腳本注入處置）。使用者資料一律經 `ARGV`。
        """
        cached = self._script_cache.get(name)
        if cached is None:
            source = (self._scripts_dir / f"{name}.lua").read_text(encoding="utf-8")
            cached = (source, hashlib.sha1(source.encode("utf-8")).hexdigest())
            self._script_cache[name] = cached
        return cached[0]

    def script_sha(self, name: str) -> str:
        self.script_source(name)
        return self._script_cache[name][1]

    # -- 指令執行、重試與分類（`Step 5.2`／`5.3`）---------------------------

    def _call(
        self,
        method: str,
        fn: Callable[[], Any],
        *,
        idempotent: bool,
        session_key: Optional[str] = None,
        segment_id=None,
    ):
        """`session_key` 是**必要的日誌欄位**，不是選用的裝飾。

        `NFR4.61` 逐字要求每一次 `SessionBackendUnavailable` 的 ERROR 日誌
        「含 `sessionKey` 與失敗的方法名」。少了它，一筆後端失效日誌說得出
        「`load` 失敗了」卻說不出**是誰的 session**——在一台同時服務多人的
        staging 上，那筆日誌排查不了任何事。

        `observability-design.md §二` 對 `session_retry`（WARN）也列了同一個
        欄位，理由相同：重試是用來解釋「某人偶爾很慢」的，而「某人」就是
        `sessionKey`。
        """
        attempt = 1
        while True:
            started = self._clock()
            try:
                return fn()
            except BaseException as exc:  # noqa: BLE001 - 立刻分類後重拋
                reason = classify_client_error(exc, self._error_types)
                if reason is None:
                    # 非 Redis 例外（例如 `HierarchyForbidden` 穿過本層）
                    # **原樣重拋**，不得包成後端失效（`BR4.6`）。
                    raise
                elapsed_ms = int((self._clock() - started) * 1000)
                if idempotent and attempt <= self._max_retries:
                    log_session_event(
                        logging.WARNING,
                        "session_retry",
                        session_log_fields(
                            sessionKey=session_key,
                            method=method,
                            reason=reason,
                            attempt=attempt,
                        ),
                    )
                    # 指數退避**含抖動**（`[D2]`=A）。抖動避免多個 worker 在
                    # 同一毫秒重試，把一次抖動放大成一次尖峰。
                    backoff = RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    self._sleep(backoff * (1.0 + self._jitter()))
                    attempt += 1
                    continue
                log_session_event(
                    logging.ERROR,
                    "session_backend_unavailable",
                    session_log_fields(
                        sessionKey=session_key,
                        method=method,
                        reason=reason,
                        elapsedMs=elapsed_ms,
                        segmentId=segment_id,
                    ),
                )
                raise SessionBackendUnavailable(reason, method=method) from exc

    def _command(
        self,
        method: str,
        *args: Any,
        idempotent: bool,
        session_key: Optional[str] = None,
        segment_id=None,
    ):
        return self._call(
            method,
            lambda: self._client.execute_command(*args),
            idempotent=idempotent,
            session_key=session_key,
            segment_id=segment_id,
        )

    # -- Hash／TTL ---------------------------------------------------------

    def hgetall(self, method: str, key: str) -> dict:
        """`load` 的單次 round-trip（`NFR3.40`）。"""
        raw = self._command(method, "HGETALL", key, idempotent=True, session_key=key) or {}
        if isinstance(raw, Mapping):
            items = raw.items()
        else:  # RESP2 的平坦陣列形式
            flat = list(raw)
            items = zip(flat[0::2], flat[1::2])
        return {_as_text(k): _as_text(v) for k, v in items}

    def hget(self, method: str, key: str, field: str) -> Optional[str]:
        return _as_text(
            self._command(method, "HGET", key, field, idempotent=True, session_key=key)
        )

    def hset(self, method: str, key: str, field: str, value: str, *, idempotent: bool, segment_id=None) -> None:
        self._command(
            method,
            "HSET",
            key,
            field,
            value,
            idempotent=idempotent,
            session_key=key,
            segment_id=segment_id,
        )

    def exists(self, method: str, key: str) -> bool:
        return bool(
            int(self._command(method, "EXISTS", key, idempotent=True, session_key=key) or 0)
        )

    def expire(self, method: str, key: str, ttl_seconds: int) -> None:
        self._command(
            method, "EXPIRE", key, ttl_seconds, idempotent=True, session_key=key
        )

    def ttl(self, method: str, key: str) -> Optional[int]:
        """剩餘秒數。`-1`（無 TTL）與 `-2`（key 不存在）回 `None`——
        兩者都不是「剩餘期」，把它們當數字傳下去會讓 `NFR4.57` 的區間斷言
        在錯誤的前提下通過。"""
        raw = self._command(method, "TTL", key, idempotent=True, session_key=key)
        value = int(raw) if raw is not None else -2
        return value if value >= 0 else None

    def delete(self, method: str, key: str) -> None:
        self._command(method, "DEL", key, idempotent=True, session_key=key)

    # -- Lua（`EVALSHA` ＋ `NOSCRIPT` 退回 `EVAL`）--------------------------

    def eval_script(
        self,
        method: str,
        name: str,
        keys: Sequence[str],
        args: Sequence[Any],
        *,
        idempotent: bool,
        segment_id=None,
    ):
        def run():
            sha = self.script_sha(name)
            try:
                return self._client.execute_command(
                    "EVALSHA", sha, len(keys), *keys, *args
                )
            except BaseException as exc:  # noqa: BLE001
                if not is_noscript_error(exc, self._error_types):
                    raise
                return self._client.execute_command(
                    "EVAL", self.script_source(name), len(keys), *keys, *args
                )

        return self._call(
            method,
            run,
            idempotent=idempotent,
            session_key=keys[0] if keys else None,
            segment_id=segment_id,
        )


# ---------------------------------------------------------------------------
# 真實客戶端（生產路徑；測試不走這裡）
# ---------------------------------------------------------------------------


def build_redis_client(url: str, *, user: str, password: str):
    """以 `REDIS_USER` 的 ACL 身分建立連線池（`NFR4.44`）。

    **不得以 `default` 連線**：`default` 已被 `U1` 收窄為 `+@connection`，故誤用
    會在第一個資料指令上失敗。本函式對 `default` **直接拒絕**，不等那個失敗——
    `U1` 已建立的保護值得一道更早、訊息更清楚的閘門。

    redis-py 在此**延遲匯入**（見模組 docstring）。`decode_responses=True` 讓
    `HGETALL` 直接回 `str`，與 in-memory 替身的行為一致。
    """
    if user == "default":
        raise ValueError(
            "REDIS_USER 不得為 `default`（NFR4.44）：default 已被收窄為 "
            "+@connection，以它連線會在第一個資料指令上失敗。"
        )
    import redis  # 延遲匯入：見模組 docstring

    pool = redis.ConnectionPool.from_url(
        url,
        username=user,
        password=password,
        max_connections=POOL_MAX_SIZE,
        socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
        socket_timeout=COMMAND_TIMEOUT_SECONDS,
        decode_responses=True,
    )
    return redis.Redis(connection_pool=pool)


__all__ = [
    "COMMAND_TIMEOUT_SECONDS",
    "CONNECT_TIMEOUT_SECONDS",
    "LOG_FIELD_NAMES",
    "LOG_FIELDS_EXPLICITLY_EXCLUDED",
    "MAX_RETRIES",
    "POOL_IDLE_TIMEOUT_SECONDS",
    "POOL_MAX_LIFETIME_SECONDS",
    "POOL_MAX_SIZE",
    "POOL_MIN_SIZE",
    "RedisErrorTypes",
    "RedisGateway",
    "SCRIPT_APPEND_MESSAGE",
    "SCRIPT_SWITCH_TO_ISOLATED",
    "SCRIPTS_DIR",
    "SESSION_TTL_SECONDS",
    "build_redis_client",
    "classify_client_error",
    "is_noscript_error",
    "log_session_event",
    "redis_py_error_types",
    "session_log_fields",
]
