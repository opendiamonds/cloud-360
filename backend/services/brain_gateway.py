"""
brain_gateway.py — `U13 brain-gateway`：大腦唯一的 WebSocket 端點（`/api/brain/ws`）

契約（前端與同進程元件依賴，請勿變更；`K-12`、`ADR-0020`）：

| 項目 | 值 |
|---|---|
| 路徑 | `/api/brain/ws`（`main.py` 以 `prefix="/api/brain"` 掛載本模組的 `router`） |
| 請求子協定 | `cloud360.brain.v1` ＋ `bearer.<jwt>`（順序不限；**不讀 query string**） |
| 回應子協定 | 只回送 `cloud360.brain.v1`——token 不進回應標頭（`BR61.4`） |
| 首則訊息 | `hello{v:1}`，10 秒內；載入成功後回 `ready{protocolVersion:1}` |
| 關閉碼 | 4401 認證失敗或到期／4403 無 `K1`／4400 版本不相容／1011 內部錯誤 |
| 未 accept（HTTP 403） | 未提供協定名、全域額滿（200）、每位使用者額滿（10）、握手過頻 |
| `U12` 的 sink | `GatewaySink.emit_session`／`emit_in_turn`／`emit_turn` |
| `U11` 的記憶轉接器 | `MemoryPrefetchAdapter.search`（只讀 `ContextVar`，**無 I/O**） |

本模組的禁令（皆有測試鎖住，見 `tests/test_brain_gateway_limits.py`）：

1. **時間只經 `GatewayTiming`**：`time.monotonic`／`time.time`／`time.sleep`／`asyncio.sleep`／
   `asyncio.wait_for` 只允許出現在 `GatewayTiming` 的預設值（帶入項 9）。
2. **事件迴圈上沒有同步 I/O**：認證、session、對象目錄一律 `asyncio.to_thread`；會呼叫嵌入的
   工作一律走 `MemoryWorker` 的專用執行器（`BR67.5`、`BR67.12`）。
3. **不新增 LLM 呼叫、不直讀表、不碰進度通道與需求欄位**（`NFR13.6`、`NFR13.16`）。
4. **log 只經 `_log`**，欄位只限 `_ALLOWED`：不含 token、使用者文字、回覆、referent、候選標籤
   （`BR67.3`）；例外只記類別名。
5. **送出一律經契約模型**（`NFR13.40`）：不手組訊息 dict。
6. **唯一的成員關係依賴經注入**（ADR-0022 D-6）：本模組不 import 任何成員關係符號；名稱推送、
   對象目錄與直接設定作業對象三條讀取路徑所需的可見性判定，一律由建構時注入的
   `membership_facade_factory(db).project_visibility(principal)` 取得（唯一組裝點 `main.py`）。

單一行程假設（`BR63.1`）：連線登錄與限流都在行程記憶體內；多 worker 會讓扇出與推播**靜默**
失效。守門見 `tests/test_brain_gateway_startup.py`（Dockerfile、compose、範本不得設 worker 數）。
"""

from __future__ import annotations

import asyncio
import contextvars
import enum
import json
import logging
import os
import secrets
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Tuple

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from services import brain_gateway_rules as rules
from services.auth import get_user_from_token
from services.brain_ws_contract import (
    ClarifyCandidate,
    ClarifyPayload,
    CostCardPayload,
    DonePayload,
    ErrorPayload,
    ReadyPayload,
    SharingModePayload,
    TokenPayload,
    WorkItemsPayload,
    WorkTargetPayload,
    WsClientEnvelope,
    WsClientMessageType,
    WsEnvelope,
    WsServerMessageType,
    WsUnvalidatedEnvelope,
)
from services.embedding_port import EMBEDDING_TIMEOUT_SEC
from services.hierarchy_facade import HierarchyFacade, HierarchyForbidden, mint_principal
from services.intent_routing import IntentRouter
from services.intent_routing_errors import PlatformSelfModificationRefused
from services.intent_routing_predicate import intents_after_choice
from services.intent_routing_types import IntentDecision
from services.memory_errors import MemoryForbidden
from services.memory_facade import MemoryFacade
from services.prompt_guard import REFUSAL_MESSAGE, is_platform_self_modification
from services.rbac import user_can
from services.redis_gateway import RedisGateway, build_redis_client, redis_py_error_types
from services.session_errors import SessionBackendUnavailable
from services.session_store import DEFAULT_MESSAGE_MAX_CHARS, SessionStore, resolve_history_max
from services.session_types import (
    PAGE_SCOPES,
    SEGMENT_IDS,
    SEGMENT_SHARED,
    BrainSession,
    default_page_modes,
)
from services.work_orchestrator import WorkOrchestrator

logger = logging.getLogger("cloud360.brain_gateway")

# ---------------------------------------------------------------------------
# 模組常數（NFR13.44：一律常數，不新增環境變數）
# ---------------------------------------------------------------------------

HELLO_WAIT_SEC = 10.0
REVALIDATE_INTERVAL_SEC = 60.0
SEND_TIMEOUT_SEC = 10.0
MEMORY_WORKERS = 4
#: `NFR13.3`：預取等待上限。定值程序與量測表見 code-generation 的 `code-summary.md`。
PREFETCH_WAIT_SEC = 3.0
#: 帶入項 8：寫入路徑等待 = 嵌入逾時 + 5 秒（預設 15 秒，與 functional-design 一致）。
EPISODIC_WAIT_SEC = EMBEDDING_TIMEOUT_SEC + 5.0
#: 與 `U11` 的取用值相同（`intent_routing.py` 的 `_REFERENT_MEMORY_KINDS`／`_MEMORY_SEARCH_LIMIT`）；
#: 兩邊一致由 `tests/test_brain_gateway_memory.py` 的契約測試鎖住。
PREFETCH_KINDS: Tuple[str, ...] = ("semantic", "procedure")
PREFETCH_LIMIT = 5
#: 執行器滿而跳過時，每這麼多次記一筆 WARNING 計數（不逐則記，NFR13.37）。
BUSY_LOG_EVERY = 100

CLOSE_REASONS: Mapping[int, str] = {
    4401: "credentials-expired-or-invalid",
    4403: "forbidden",
    1011: "internal-error",
}

TOO_MANY_PROJECTS_MESSAGE = "專案太多，請先在脈絡列選定專案"
CONFLICTING_TARGETS_MESSAGE = "這句話提到了不同的對象，請一次只針對一個對象交辦，或先在脈絡列選定。"


def not_found_message(referent: str) -> str:
    return f"找不到名為「{referent}」的系統或專案。請在上方脈絡列選定作業對象後再說一次。"


# ---------------------------------------------------------------------------
# log 的唯一出口（BR67.3；observability-design.md §一）
# ---------------------------------------------------------------------------

_ALLOWED = frozenset(
    {
        "connId",
        "sessionKey",
        "turnId",
        "type",
        "code",
        "closeCode",
        "reason",
        "exc",
        "elapsedMs",
        "preClassifyMs",
        "classifyMs",
        "toFirstContentMs",
        "outcome",
        "prefetch",
        "count",
        "skipped",
    }
)


def _log(level: int, event: str, **fields: Any) -> None:
    unknown = set(fields) - _ALLOWED
    if unknown:
        raise ValueError(f"log 欄位不在白名單內：{sorted(unknown)}")
    logger.log(level, "%s " + " ".join(f"{k}=%s" for k in fields), event, *fields.values())


# ---------------------------------------------------------------------------
# 時間注入（帶入項 9；reliability-design.md §一）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GatewayTiming:
    """全部計時路徑的唯一注入點。只有這裡可以引用真正的時鐘與睡眠。"""

    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    wait_for: Callable[..., Awaitable[Any]] = asyncio.wait_for


def _ms(start: Optional[float], end: Optional[float]) -> Optional[int]:
    if start is None or end is None:
        return None
    return int(round((end - start) * 1000))


# ---------------------------------------------------------------------------
# 認證（BR61.4／BR62.1）
# ---------------------------------------------------------------------------


class AuthStatus(enum.Enum):
    OK = "ok"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class AuthResult:
    status: AuthStatus
    user_id: Optional[int] = None
    principal: Any = None


# ---------------------------------------------------------------------------
# 連線與登錄（BR63；scalability-design.md §一）
# ---------------------------------------------------------------------------


class Phase(enum.Enum):
    LOADING = "loading"
    READY = "ready"


@dataclass(eq=False)
class Connection:
    """一條已 accept 的連線。token 不進 `repr`（`BR62.2`）。"""

    gateway: "BrainGateway" = field(repr=False)
    ws: Any = field(repr=False)
    conn_id: str = ""
    session_key: str = ""
    user_id: int = 0
    token: str = field(default="", repr=False)
    principal: Any = field(default=None, repr=False)
    phase: Phase = Phase.LOADING
    pending: deque = field(default_factory=deque, repr=False)
    overflowed: bool = False
    dead: bool = False
    registered: bool = False
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    revalidate_task: Optional[asyncio.Task] = field(default=None, repr=False)
    pending_clarify: Optional["PendingClarify"] = field(default=None, repr=False)
    # 目前這則訊息開啟（或接續）的輪次：`user_message` 建立 `Turn`、`select_clarify_candidate`
    # 取出待選反問時設定；每則訊息處理前清空。未預期例外時據以判斷錯誤屬於哪一輪（BR2.8 T9）。
    open_turn: Optional["Turn"] = field(default=None, repr=False)

    async def send(self, envelope: WsEnvelope) -> bool:
        """經契約模型序列化後送出；失敗即移出登錄、標記 dead 並主動以 1011 關閉（帶入項 21）。"""
        if self.dead:
            return False
        frame_json = envelope.model_dump_json()
        async with self.send_lock:
            if self.dead:
                return False
            try:
                await self.gateway.timing.wait_for(self.ws.send_text(frame_json), SEND_TIMEOUT_SEC)
                return True
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # 外部邊界（socket）：降級並記 log，不向上拋（BR63.4）
                self._on_send_failure(exc)
                return False

    def _on_send_failure(self, exc: BaseException) -> None:
        gw = self.gateway
        gw.registry.unregister(self)
        self.dead = True
        _log(logging.DEBUG, "send_failed", connId=self.conn_id, exc=type(exc).__name__)
        gw.spawn(gw.close_ws(self.ws, 1011))


class ConnectionRegistry:
    """全域／每 key 佔位計數與已登錄連線。只在事件迴圈執行緒存取；方法皆同步、無 `await`。

    佔位與登錄是兩件事：**佔位**在 handler 一開始（全域）與認證之後、accept 之前（每 key）取得，
    `finally` 釋放；**登錄**在 hello 通過時（phase=loading）建立，是扇出的唯一依據。
    """

    def __init__(
        self,
        *,
        max_total: int = rules.MAX_TOTAL_CONNECTIONS,
        max_per_key: int = rules.MAX_CONNECTIONS_PER_KEY,
    ) -> None:
        self.max_total = max_total
        self.max_per_key = max_per_key
        self.total_slots = 0
        self.key_slots: Dict[str, int] = {}
        self._by_key: Dict[str, List[Connection]] = {}

    def try_reserve_total(self) -> bool:
        if self.total_slots >= self.max_total:
            return False
        self.total_slots += 1
        return True

    def release_total(self) -> None:
        self.total_slots = max(0, self.total_slots - 1)

    def try_reserve_key(self, key: str) -> bool:
        if self.key_slots.get(key, 0) >= self.max_per_key:
            return False
        self.key_slots[key] = self.key_slots.get(key, 0) + 1
        return True

    def release_key(self, key: str) -> None:
        remaining = self.key_slots.get(key, 0) - 1
        if remaining <= 0:
            self.key_slots.pop(key, None)
        else:
            self.key_slots[key] = remaining

    def register(self, conn: Connection) -> None:
        if conn.registered:
            return
        self._by_key.setdefault(conn.session_key, []).append(conn)
        conn.registered = True

    def unregister(self, conn: Connection) -> None:
        if not conn.registered:
            return
        conn.registered = False
        conns = self._by_key.get(conn.session_key, [])
        if conn in conns:
            conns.remove(conn)
        if not conns:
            self._by_key.pop(conn.session_key, None)
        conn.pending.clear()

    def snapshot(self, key: str) -> List[Connection]:
        return list(self._by_key.get(key, ()))

    def registered_count(self) -> int:
        return sum(len(v) for v in self._by_key.values())


# ---------------------------------------------------------------------------
# 記憶預取與執行器（BR67.10／BR67.12；帶入項 5、15、18、19、22）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryPrefetch:
    user_id: int
    query: str = field(repr=False)
    kinds: Tuple[str, ...]
    hits: Optional[Tuple[Any, ...]] = field(default=None, repr=False)
    #: 合併前必修第 13 項：facade 以 `MemoryForbidden` 拒絕時的 `reason`。非 None 時
    #: 轉接器對同一個 principal 重拋 `MemoryForbidden`，而**不是**當成預取失敗降級。
    forbidden_reason: Optional[str] = None

    @property
    def failed(self) -> bool:
        return self.hits is None


_PREFETCH: contextvars.ContextVar[Optional[MemoryPrefetch]] = contextvars.ContextVar(
    "brain_memory_prefetch", default=None
)


class PrefetchUnavailable(RuntimeError):
    """預取失敗、熔斷、或請求與預取不符。`U11` 依其既有設計降級為不帶記憶分類。"""


@dataclass(frozen=True)
class _PrefetchForbidden:
    """預取工作的回傳值：facade 以 `MemoryForbidden` 拒絕（只帶 `reason`，不帶任何記憶內容）。"""

    reason: str


class MemoryPrefetchAdapter:
    """注入 `IntentRouter(memory_facade=...)` 的轉接器。**內部無任何 I/O**：只讀 `ContextVar`。"""

    def search(self, principal: Any, query: str, kinds: Any = None, limit: Optional[int] = None):
        prefetch = _PREFETCH.get()
        if (
            prefetch is not None
            and prefetch.forbidden_reason is not None
            and getattr(principal, "user_id", None) == prefetch.user_id
        ):
            # 授權拒絕不是預取失敗：原樣交給 `U11`，由它向上傳遞（合併前必修第 13 項）。
            raise MemoryForbidden(reason=prefetch.forbidden_reason)
        if prefetch is None or prefetch.failed:
            raise PrefetchUnavailable("no-prefetch")
        if getattr(principal, "user_id", None) != prefetch.user_id or query != prefetch.query:
            raise PrefetchUnavailable("mismatch")
        wanted = tuple(kinds) if kinds is not None else prefetch.kinds
        if not set(wanted) <= set(prefetch.kinds):
            raise PrefetchUnavailable("kinds")
        hits = [h for h in prefetch.hits or () if getattr(h, "kind", None) in wanted]
        return hits[:limit] if limit is not None else hits


class Outcome(enum.Enum):
    OK = "ok"
    FAILED = "failed"
    BREAKER_OPEN = "breaker_open"
    BUSY_SKIPPED = "busy_skipped"


@dataclass(frozen=True)
class MemoryResult:
    outcome: Outcome
    value: Any = None
    exc_name: Optional[str] = None


class MemoryWorker:
    """會呼叫嵌入的工作專用的有界執行器＋熔斷。**執行器與號誌是實例屬性**（帶入項 22）。

    在途上限以「工作執行緒實際結束」計數：號誌在工作函式的 `finally` 歸還，而非 `wait_for`
    逾時之時（帶入項 15）——故執行器的內部佇列恆為空，滿時新工作立即 `BUSY_SKIPPED`。
    """

    def __init__(
        self,
        timing: GatewayTiming,
        *,
        max_workers: int = MEMORY_WORKERS,
        breaker_open_sec: float = rules.BREAKER_OPEN_SEC,
    ) -> None:
        self._timing = timing
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="brain-memory")
        self._slots = threading.BoundedSemaphore(max_workers)
        self.breaker = rules.BreakerState(open_sec=breaker_open_sec)
        self.busy_count = 0

    async def run(self, fn: Callable[[], Any], *, wait_sec: float) -> MemoryResult:
        breaker = self.breaker
        admitted = breaker.admit(self._timing.monotonic())
        if admitted == rules.ADMIT_SKIP:
            return MemoryResult(Outcome.BREAKER_OPEN)
        probing = admitted == rules.ADMIT_PROBE
        if not self._slots.acquire(blocking=False):
            if probing:
                breaker.release_probe()
            self._note_busy()
            return MemoryResult(Outcome.BUSY_SKIPPED)

        slots = self._slots

        def _job():
            try:
                return fn()
            finally:
                slots.release()

        def _release_if_never_ran(done) -> None:
            # 等待逾時或取消時若工作**尚未開始**，執行器的 future 會被成功取消、`_job` 永遠不跑——
            # 位子必須在這裡歸還，否則永久洩漏。已開始的工作取消不了，由 `_job` 的 finally 歸還（恰一次）。
            if done.cancelled():
                slots.release()

        try:
            submitted = self._executor.submit(_job)
        except Exception as exc:  # 例如 shutdown 後的 RuntimeError：位子必須歸還
            slots.release()
            if probing:
                breaker.release_probe()
            self._record_failure(exc)
            return MemoryResult(Outcome.FAILED, exc_name=type(exc).__name__)
        submitted.add_done_callback(_release_if_never_ran)
        future = asyncio.wrap_future(submitted)

        try:
            value = await self._timing.wait_for(future, wait_sec)
        except asyncio.CancelledError:
            # 取消不是記憶失敗：清除探測者身分後原樣重拋（帶入項 19）。
            if probing:
                breaker.release_probe()
            raise
        except Exception as exc:  # 外部依賴邊界：記入熔斷判定，呼叫端降級
            self._record_failure(exc)
            return MemoryResult(Outcome.FAILED, exc_name=type(exc).__name__)

        skipped = breaker.on_success()
        if skipped is not None:
            _log(logging.INFO, "memory_breaker_close", skipped=skipped)
        return MemoryResult(Outcome.OK, value=value)

    def _record_failure(self, exc: BaseException) -> None:
        if self.breaker.on_failure(exc, self._timing.monotonic()):
            _log(logging.WARNING, "memory_breaker_open", exc=type(exc).__name__)

    def _note_busy(self) -> None:
        self.busy_count += 1
        if self.busy_count == 1 or self.busy_count % BUSY_LOG_EVERY == 0:
            _log(logging.WARNING, "memory_busy", count=self.busy_count)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# 一輪與反問（BR64；TurnLedger 在 rules）
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class Turn:
    turn_id: str
    segment: str = SEGMENT_SHARED
    utterance: str = field(default="", repr=False)
    ledger: rules.TurnLedger = field(default_factory=rules.TurnLedger)
    texts: List[str] = field(default_factory=list, repr=False)
    dispatched: bool = False
    write_history: bool = True
    t_received: Optional[float] = None
    t_classify_start: Optional[float] = None
    t_classify_end: Optional[float] = None
    t_first_content: Optional[float] = None
    prefetch: Optional[str] = None
    # 終止事件（done／error）**實際送達**之後才設為 True（`_send_terminal`）。T9 以它而非
    # `ledger.is_terminal` 判斷「前端是否已收到終止事件」：`ledger.finish()` 先於 done 的送出，
    # 兩者之間拋例外時 ledger 已終止、前端卻什麼都沒收到（審查 review-02 發現 1）。
    terminal_sent: bool = False


@dataclass(eq=False)
class PendingClarify:
    turn: Turn
    kind: str
    candidate_ids: Tuple[str, ...]
    candidates: Mapping[str, Any] = field(default_factory=dict, repr=False)
    targets: Mapping[str, rules.TargetRef] = field(default_factory=dict, repr=False)
    decision: Any = field(default=None, repr=False)


def _mint_turn_id() -> str:
    return secrets.token_urlsafe(16)


# ---------------------------------------------------------------------------
# 交給 U12 的 sink（BR65）
# ---------------------------------------------------------------------------


class GatewaySink:
    """綁 session key 而不綁單一 socket；每次呼叫 `U12` 時新建（`BR65.1`）。"""

    def __init__(
        self,
        gateway: "BrainGateway",
        session_key: str,
        *,
        origin: Optional[Tuple[Connection, Turn]] = None,
        segment_id: Optional[str] = None,
    ) -> None:
        self._gw = gateway
        self._key = session_key
        self._origin = origin
        self._segment = segment_id

    async def emit_session(self, payload: WorkItemsPayload) -> None:
        await self._gw.fanout(self._key, self._gw.envelope(WsServerMessageType.WORK_ITEMS, None, payload))

    async def emit_in_turn(self, turn_id: str, payloads: List[TokenPayload]) -> None:
        origin = self._origin
        if origin is None or origin[1].turn_id != turn_id or not origin[1].ledger.allows("token"):
            _log(logging.WARNING, "in_turn_dropped", turnId=turn_id)
            return
        conn, turn = origin
        for payload in payloads:
            await self._gw.send_turn_message(conn, turn, WsServerMessageType.TOKEN, payload)

    async def emit_turn(self, payloads: List[Any]) -> None:
        gw = self._gw
        turn_id = _mint_turn_id()
        ledger = rules.TurnLedger()
        envelopes = []
        spoken = []
        for payload in payloads:
            if isinstance(payload, TokenPayload):
                kind, msg_type = "token", WsServerMessageType.TOKEN
                spoken.append(payload.text)
            elif isinstance(payload, CostCardPayload):
                kind, msg_type = "cost_card", WsServerMessageType.COST_CARD
            else:
                raise TypeError("emit_turn 只接受 TokenPayload／CostCardPayload")
            if ledger.content(kind):
                envelopes.append(gw.envelope(msg_type, turn_id, payload))
        if ledger.finish() == rules.FINISH_DONE:
            envelopes.append(gw.envelope(WsServerMessageType.DONE, turn_id, DonePayload(turnId=turn_id)))
        else:
            code, message = rules.CODE_EMPTY, rules.ERROR_MESSAGES["empty"]
            envelopes.append(
                gw.envelope(
                    WsServerMessageType.ERROR,
                    turn_id,
                    ErrorPayload(code=code, message=message, turnId=turn_id),
                )
            )
        await gw.fanout_many(self._key, envelopes)
        if self._segment is not None and spoken:
            gw.spawn(gw.append_assistant_background(self._key, self._segment, spoken))


# ---------------------------------------------------------------------------
# 名稱推送的共用小工具（ADR-0022 D-7）
_NO_NAMES = {"projectName": None, "systemName": None, "diagramName": None}


def _snapshot_segment_ids(session: Optional[BrainSession]) -> List[str]:
    """快照會送出 `work_target` 的段：session 內已有的段（依 `SEGMENT_IDS` 順序），無則只有共享段。"""
    segments = (session.segments or {}) if session is not None else {}
    return [s for s in SEGMENT_IDS if s in segments] or [SEGMENT_SHARED]


def _target_triple(session: Optional[BrainSession], segment_id: str) -> Tuple[Any, Any, Any]:
    segment = (session.segments or {}).get(segment_id) if session is not None else None
    return (
        getattr(segment, "project_id", None),
        getattr(segment, "system_id", None),
        getattr(segment, "diagram_id", None),
    )


# ---------------------------------------------------------------------------
# SessionStore 的 hierarchy 轉接器（每次呼叫開獨立 DB session，BR66.1）
# ---------------------------------------------------------------------------


class _HierarchyResolver:
    def __init__(
        self,
        session_factory: Callable[[], Any],
        facade_factory: Callable[[Any], Any],
        *,
        membership_facade_factory: Callable[[Any], Any],
    ) -> None:
        self._session_factory = session_factory
        self._facade_factory = facade_factory
        # ADR-0022 D-6：必填、無預設——預設只能是恆可見（靜默繞過）或恆不可見（大腦失效）。
        self._membership_facade_factory = membership_facade_factory

    def resolve_work_target(self, principal, *, project_id=None, system_id=None, diagram_id=None):
        db = self._session_factory()
        try:
            # `[EPD1]`=A：直接設定作業對象同受 `U23` 可見性守門；判定綁同一個 session。
            return self._facade_factory(db).resolve_work_target(
                principal,
                project_visible=self._membership_facade_factory(db).project_visibility(principal),
                project_id=project_id,
                system_id=system_id,
                diagram_id=diagram_id,
            )
        finally:
            db.close()


def _default_session_factory():
    from database import SessionLocal  # 延遲取得：測試以建構子注入替身

    return SessionLocal()


# ---------------------------------------------------------------------------
# 閘道
# ---------------------------------------------------------------------------


class BrainGateway:
    """行程內唯一的組裝物件，掛在 `app.state.brain_gateway`（`BR67.11`）。"""

    def __init__(
        self,
        *,
        store: Any,
        routers: Mapping[str, Any],
        orchestrator: Any,
        session_factory: Optional[Callable[[], Any]] = None,
        timing: Optional[GatewayTiming] = None,
        memory_facade_factory: Callable[[Any], Any] = MemoryFacade,
        hierarchy_facade_factory: Callable[[Any], Any] = HierarchyFacade,
        membership_facade_factory: Callable[[Any], Any],
        registry: Optional[ConnectionRegistry] = None,
        rate_limiter: Optional[rules.RateLimiter] = None,
        memory_worker: Optional[MemoryWorker] = None,
        prefetch_adapter: Optional[MemoryPrefetchAdapter] = None,
        prefetch_wait_sec: float = PREFETCH_WAIT_SEC,
        episodic_wait_sec: float = EPISODIC_WAIT_SEC,
    ) -> None:
        self.timing = timing or GatewayTiming()
        self.store = store
        self.routers = dict(routers)
        self.orchestrator = orchestrator
        self.session_factory = session_factory or _default_session_factory
        self.memory_facade_factory = memory_facade_factory
        self.hierarchy_facade_factory = hierarchy_facade_factory
        # ADR-0022 D-6：唯一的成員關係依賴，必填、無預設（`main.py` 傳 `MembershipFacade`）。
        self.membership_facade_factory = membership_facade_factory
        self.registry = registry or ConnectionRegistry()
        self.rate = rate_limiter or rules.RateLimiter()
        self.memory = memory_worker or MemoryWorker(self.timing)
        self.prefetch_adapter = prefetch_adapter or MemoryPrefetchAdapter()
        self.prefetch_wait_sec = prefetch_wait_sec
        self.episodic_wait_sec = episodic_wait_sec
        self._bg_tasks: set = set()

    # -- 共用工具 ------------------------------------------------------------

    def spawn(self, coro: Awaitable[Any]) -> asyncio.Task:
        task = asyncio.ensure_future(coro)
        self._bg_tasks.add(task)

        def _forget(done: asyncio.Task) -> None:
            self._bg_tasks.discard(done)
            if not done.cancelled() and done.exception() is not None:
                _log(logging.WARNING, "background_failed", exc=type(done.exception()).__name__)

        task.add_done_callback(_forget)
        return task

    @staticmethod
    def envelope(msg_type: WsServerMessageType, turn_id: Optional[str], payload: Any) -> WsEnvelope:
        return WsEnvelope(v=rules.PROTOCOL_VERSION, type=msg_type, turnId=turn_id, payload=payload)

    async def close_ws(self, ws: Any, code: int, reason: Optional[str] = None) -> None:
        try:
            await self.timing.wait_for(ws.close(code=code, reason=reason or CLOSE_REASONS.get(code, "")), SEND_TIMEOUT_SEC)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # socket 已關或已斷：只記 DEBUG
            _log(logging.DEBUG, "close_failed", closeCode=code, exc=type(exc).__name__)

    async def _accept_and_close(self, ws: Any, code: int, reason: Optional[str] = None) -> None:
        await ws.accept(subprotocol=rules.PROTOCOL_NAME)
        await self.close_ws(ws, code, reason)

    async def deliver(self, conn: Connection, envelope: WsEnvelope) -> None:
        """loading 的連線進暫存佇列（判斷與附加之間無 `await`，BR63.6）；ready 的直接送出。"""
        if conn.dead:
            return
        if conn.phase is Phase.LOADING:
            if len(conn.pending) >= rules.PENDING_OUTBOUND_MAX:
                conn.overflowed = True
                self.registry.unregister(conn)
                return
            conn.pending.append(envelope)
            return
        await conn.send(envelope)

    async def fanout(self, key: str, envelope: WsEnvelope) -> None:
        await self.fanout_many(key, [envelope])

    async def fanout_many(self, key: str, envelopes: List[WsEnvelope]) -> None:
        """對該 key 的每條連線依序送出 `envelopes`；**連線之間並行**（審查 R-05）。

        各連線的送出各自有 `SEND_TIMEOUT_SEC` 的上限，一條卡住的分頁不再讓其餘分頁排在它後面
        （依序時最壞延遲是「卡住的分頁數 × 10 秒」）。同一連線上的順序由逐則 `await` 與
        `send_lock` 保證。只有一條連線時直接送，不建 task（也使載入中「判斷與附加」維持在呼叫端
        的同一步內，`NFR13.26`）。
        """
        conns = self.registry.snapshot(key)
        if len(conns) == 1:
            await self._deliver_sequence(conns[0], envelopes)
        elif conns:
            await asyncio.gather(*(self._deliver_sequence(conn, envelopes) for conn in conns))

    async def _deliver_sequence(self, conn: Connection, envelopes: List[WsEnvelope]) -> None:
        for envelope in envelopes:
            if conn.dead:
                return
            await self.deliver(conn, envelope)

    # -- 認證（在 to_thread 內、同一個 DB session）-------------------------------

    def _auth_once(self, token: str, record: bool) -> AuthResult:
        db = self.session_factory()
        try:
            try:
                user = get_user_from_token(token, db, record=record)
            except HTTPException:
                return AuthResult(AuthStatus.UNAUTHENTICATED)
            if not user_can(db, user.role, "K1", "view", authorization_status=user.authorization_status):
                return AuthResult(AuthStatus.FORBIDDEN)
            return AuthResult(AuthStatus.OK, user_id=user.id, principal=mint_principal(user))
        finally:
            db.close()

    # -- 握手（GW-W1）--------------------------------------------------------

    async def handle(self, ws: WebSocket) -> None:
        registry = self.registry
        if not registry.try_reserve_total():  # ← 第一個可能拒絕的敘述，之前無 await（帶入項 7）
            _log(logging.INFO, "ws_refused", reason="global_limit")
            await ws.close()
            return
        conn: Optional[Connection] = None
        key_reserved: Optional[str] = None
        close_code: Optional[int] = None
        try:
            offer = rules.parse_subprotocol_offer(ws.headers.get("sec-websocket-protocol"))
            if not offer.has_protocol_name:
                _log(logging.INFO, "ws_refused", reason="no_protocol")
                await ws.close()
                return
            if offer.bearer_token is None:
                close_code = 4401
                await self._accept_and_close(ws, 4401)
                return
            try:
                auth = await asyncio.to_thread(self._auth_once, offer.bearer_token, True)
            except Exception as exc:  # 認證以外的失敗（DB 不可用等）
                _log(logging.WARNING, "handshake_auth_failed", exc=type(exc).__name__)
                close_code = 1011
                await self._accept_and_close(ws, 1011)
                return
            if auth.status is AuthStatus.UNAUTHENTICATED:
                close_code = 4401
                await self._accept_and_close(ws, 4401)
                return
            if auth.status is AuthStatus.FORBIDDEN:
                close_code = 4403
                await self._accept_and_close(ws, 4403)
                return
            key = rules.session_key_for(auth.user_id)
            if not self.rate.admit_handshake(key, self.timing.monotonic()):
                _log(logging.INFO, "ws_refused", reason="handshake_rate", sessionKey=key)
                await ws.close()
                return
            if not registry.try_reserve_key(key):
                _log(logging.INFO, "ws_refused", reason="per_key_limit", sessionKey=key)
                await ws.close()
                return
            key_reserved = key
            await ws.accept(subprotocol=rules.PROTOCOL_NAME)
            conn = Connection(
                gateway=self,
                ws=ws,
                conn_id=secrets.token_urlsafe(8),
                session_key=key,
                user_id=auth.user_id,
                token=offer.bearer_token,
                principal=auth.principal,
            )
            _log(logging.INFO, "ws_accepted", connId=conn.conn_id)
            close_code = await self._handshake_and_serve(conn)
        except WebSocketDisconnect:
            close_code = close_code or 1000
        finally:
            if conn is not None:
                registry.unregister(conn)
                conn.dead = True
                if conn.revalidate_task is not None:
                    conn.revalidate_task.cancel()
                if conn.pending_clarify is not None:
                    conn.pending_clarify.turn.ledger.end_silent()
                    conn.pending_clarify = None
                self.rate.forget_connection(conn.conn_id)
                self.rate.sweep(self.timing.monotonic())
            if key_reserved is not None:
                registry.release_key(key_reserved)
            registry.release_total()
            if conn is not None or close_code is not None:
                _log(
                    logging.INFO,
                    "ws_closed",
                    connId=conn.conn_id if conn else "",
                    sessionKey=conn.session_key if conn else "",
                    closeCode=close_code,
                )

    async def _handshake_and_serve(self, conn: Connection) -> Optional[int]:
        ws = conn.ws
        # 首則訊息：hello（BR61.8）
        try:
            message = await self.timing.wait_for(ws.receive(), HELLO_WAIT_SEC)
        except TimeoutError:
            await self.close_ws(ws, 4400, rules.close_reason_for_version("invalid"))
            return 4400
        if message.get("type") == "websocket.disconnect":
            return 1000
        hello_frame = message.get("text") or ""
        # hello 也受入站訊框的位元組上限與每連線頻率窗約束（審查 R-04；NFR13.19／NFR13.20）。
        self.rate.admit(conn.session_key, conn.conn_id, False, self.timing.monotonic())
        if len(hello_frame.encode("utf-8")) > rules.MAX_FRAME_BYTES:
            _log(logging.INFO, "frame_rejected", connId=conn.conn_id, reason="too_large", count=1)
            await self.close_ws(ws, 4400, rules.close_reason_for_version("invalid"))
            return 4400
        try:
            data = json.loads(hello_frame)
        except ValueError:
            data = None
        compatible, received = rules.hello_version(data)
        if compatible:
            try:
                WsClientEnvelope.model_validate(data)
            except ValidationError:
                compatible = False
        if not compatible:
            await self.close_ws(ws, 4400, rules.close_reason_for_version(received))
            return 4400

        # 先登錄（loading）再讀取：讀取期間的扇出一定進暫存佇列（BR63.1／BR63.6）
        self.registry.register(conn)
        try:
            session = await asyncio.to_thread(self.store.load, conn.session_key)
            items = await self.orchestrator.list_items(
                conn.principal,
                conn.session_key,
                bearer_token=conn.token,
                sink=GatewaySink(self, conn.session_key),
            )
        except Exception as exc:  # 握手內：任何失敗（含 SessionBackendUnavailable）→ 1011（[GW3]=A）
            self.registry.unregister(conn)
            _log(logging.WARNING, "handshake_load_failed", connId=conn.conn_id, exc=type(exc).__name__)
            await self.close_ws(ws, 1011)
            return 1011
        if conn.overflowed:
            await self.close_ws(ws, 1011)
            return 1011

        # 快照各段作業對象的三層名稱（ADR-0022 D-7）：一次 to_thread、一個 session；
        # `_names_for` 絕不往外拋，失敗只使名稱為 null，不讓握手 1011。
        snapshot_triples = {
            segment_id: _target_triple(session, segment_id) for segment_id in _snapshot_segment_ids(session)
        }
        names = await self._names_for(conn, list(snapshot_triples.values()))
        names_by_segment = {segment_id: names[t] for segment_id, t in snapshot_triples.items()}

        # ready ＋ 快照（只對本連線）。握手期內的未預期例外一律 1011（審查 R-03；[GW3]=A 的握手分界）。
        try:
            if not await conn.send(self.envelope(WsServerMessageType.READY, None, ReadyPayload(protocolVersion=1))):
                return 1011
            for envelope in self._snapshot_envelopes(session, items, names_by_segment):
                if not await conn.send(envelope):
                    return 1011
            # 送出暫存佇列：「確認已空」與「改為 ready」之間無任何 await（帶入項 3；NFR13.26）
            while conn.pending:
                envelope = conn.pending.popleft()
                if not await conn.send(envelope):
                    return 1011
                if conn.overflowed:
                    await self.close_ws(ws, 1011)
                    return 1011
        except Exception as exc:
            self.registry.unregister(conn)
            _log(logging.WARNING, "handshake_unexpected", connId=conn.conn_id, exc=type(exc).__name__)
            await self.close_ws(ws, 1011)
            return 1011
        # 溢位可能發生在 ready 與快照的送出期間（此時佇列已被清空、迴圈不會執行）：
        # 改 ready 前再檢查一次（審查 R-02）。這是同步判斷，不破壞上面的「無 await」保證。
        if conn.overflowed:
            await self.close_ws(ws, 1011)
            return 1011
        conn.phase = Phase.READY
        conn.revalidate_task = self.spawn(self._revalidate_loop(conn))
        _log(logging.INFO, "ws_ready", connId=conn.conn_id, sessionKey=conn.session_key)
        return await self._receive_loop(conn)

    def _snapshot_envelopes(
        self,
        session: Optional[BrainSession],
        items: Any,
        names_by_segment: Mapping[str, Mapping[str, Optional[str]]],
    ) -> List[WsEnvelope]:
        page_modes = dict(default_page_modes())
        if session is not None:
            page_modes.update(session.page_modes or {})
        out = [
            self.envelope(
                WsServerMessageType.SHARING_MODE,
                None,
                SharingModePayload(mode=page_modes.get(scope, "shared"), scope=scope),
            )
            for scope in PAGE_SCOPES
        ]
        for segment_id in _snapshot_segment_ids(session):
            out.append(self._work_target_envelope(session, segment_id, names_by_segment.get(segment_id, _NO_NAMES)))
        out.append(
            self.envelope(
                WsServerMessageType.WORK_ITEMS,
                None,
                WorkItemsPayload(items=[i.model_dump() if hasattr(i, "model_dump") else i for i in items or []]),
            )
        )
        return out

    def _work_target_envelope(
        self,
        session: Optional[BrainSession],
        segment_id: str,
        names: Mapping[str, Optional[str]],
    ) -> WsEnvelope:
        segment = (session.segments or {}).get(segment_id) if session is not None else None

        def _s(value: Optional[int]) -> Optional[str]:
            return None if value is None else str(value)

        return self.envelope(
            WsServerMessageType.WORK_TARGET,
            None,
            WorkTargetPayload(
                projectId=_s(getattr(segment, "project_id", None)),
                systemId=_s(getattr(segment, "system_id", None)),
                diagramId=_s(getattr(segment, "diagram_id", None)),
                segment=segment_id,
                projectName=names.get("projectName"),
                systemName=names.get("systemName"),
                diagramName=names.get("diagramName"),
            ),
        )

    async def _names_for(self, conn: "Connection", triples: List[Tuple[Any, Any, Any]]) -> Dict[tuple, dict]:
        """ADR-0022 D-7：一批作業對象三元組的三層名稱。**絕不往外拋。**

        去重（保序）、一次 `asyncio.to_thread`、一個 DB session、每組呼叫一次
        `describe_work_target`。`HierarchyForbidden` → 該組三名稱 null、**不記 log**（被拒絕是
        正常結果，nfr-design `R-04`）；其他例外 → 該組三名稱 null、記一筆 WARNING
        `work_target_names_failed`（只帶 `connId` 與例外類別名）、`rollback` 後繼續下一組；
        thread 外層失敗 → 全部 null ＋ 一筆 log。名稱不儲存、每次推送重查。
        """
        unique = list(dict.fromkeys(triples))

        def _run() -> Dict[tuple, dict]:
            out = {t: dict(_NO_NAMES) for t in unique}
            try:
                db = self.session_factory()
            except Exception as exc:
                _log(logging.WARNING, "work_target_names_failed", connId=conn.conn_id, exc=type(exc).__name__)
                return out
            try:
                facade = self.hierarchy_facade_factory(db)
                vis = self.membership_facade_factory(db)
                for pid, sid, did in unique:
                    try:
                        out[(pid, sid, did)] = dict(
                            facade.describe_work_target(
                                conn.principal,
                                project_visible=vis.project_visibility(conn.principal),
                                project_id=pid,
                                system_id=sid,
                                diagram_id=did,
                            )
                        )
                    except HierarchyForbidden:
                        pass  # 被拒絕是正常結果，不記（nfr-design R-04）；名稱維持 null
                    except Exception as exc:
                        _log(
                            logging.WARNING,
                            "work_target_names_failed",
                            connId=conn.conn_id,
                            exc=type(exc).__name__,
                        )
                        try:
                            db.rollback()
                        except Exception:  # rollback 再失敗只會使後續組也失敗；本組的 log 已記
                            pass
            finally:
                db.close()
            return out

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:  # 絕不往外拋：名稱失敗不得讓握手或扇出失敗
            _log(logging.WARNING, "work_target_names_failed", connId=conn.conn_id, exc=type(exc).__name__)
            return {t: dict(_NO_NAMES) for t in unique}

    async def _named_work_target_envelope(
        self, conn: "Connection", session: Optional[BrainSession], segment_id: str
    ) -> WsEnvelope:
        """扇出點共用：取該段三元組的名稱後組 `work_target`（ADR-0022 D-7 的三個扇出點）。"""
        triple = _target_triple(session, segment_id)
        names = await self._names_for(conn, [triple])
        return self._work_target_envelope(session, segment_id, names[triple])

    # -- 背景重驗（BR62.6）---------------------------------------------------

    async def _revalidate_loop(self, conn: Connection) -> None:
        while not conn.dead:
            await self.timing.sleep(REVALIDATE_INTERVAL_SEC)
            if conn.dead:
                return
            try:
                auth = await asyncio.to_thread(self._auth_once, conn.token, False)
            except Exception as exc:  # 非認證類：下一個週期再試，不關閉
                _log(logging.WARNING, "revalidate_failed", connId=conn.conn_id, exc=type(exc).__name__)
                continue
            if auth.status is AuthStatus.OK:
                conn.principal = auth.principal
                continue
            code = 4401 if auth.status is AuthStatus.UNAUTHENTICATED else 4403
            self.registry.unregister(conn)
            conn.dead = True
            _log(logging.INFO, "ws_revoked", connId=conn.conn_id, closeCode=code)
            await self.close_ws(conn.ws, code)
            return

    # -- 接收迴圈（每訊框：大小 → 頻率 → 重驗 → 信封 → 處理）----------------------

    async def _receive_loop(self, conn: Connection) -> Optional[int]:
        ws = conn.ws
        while True:
            if conn.dead:
                return None
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                return int(message.get("code") or 1000)
            if conn.dead:
                return None
            t_received = self.timing.monotonic()
            frame = message.get("text")
            if frame is None:  # 二進位訊框：本端點只收文字
                if await self._reject(conn, "binary", rules.GatewayInvalidRequest()):
                    return 1011
                continue
            if len(frame.encode("utf-8")) > rules.MAX_FRAME_BYTES:
                if await self._reject(conn, "too_large", rules.FrameTooLarge()):
                    return 1011
                continue
            try:
                data = json.loads(frame)
            except ValueError:
                data = None
            is_user_message = isinstance(data, dict) and data.get("type") == WsClientMessageType.USER_MESSAGE.value
            denied = self.rate.admit(conn.session_key, conn.conn_id, is_user_message, t_received)
            if denied is not None:
                if await self._reject(conn, denied, rules.RateLimited()):
                    return 1011
                continue
            # 重驗（BR62.1）：record=True
            try:
                auth = await asyncio.to_thread(self._auth_once, conn.token, True)
            except Exception as exc:  # (c) 其他例外：不關閉，本則不處理
                _log(logging.WARNING, "revalidate_failed", connId=conn.conn_id, exc=type(exc).__name__)
                await self._send_single_error(conn, *rules.error_for(exc))
                continue
            if auth.status is not AuthStatus.OK:
                code = 4401 if auth.status is AuthStatus.UNAUTHENTICATED else 4403
                self.registry.unregister(conn)
                conn.dead = True
                await self.close_ws(ws, code)
                return code
            conn.principal = auth.principal
            # 兩步信封驗證：原始 dict 交給 WsClientEnvelope（BR64.2）
            try:
                if not isinstance(data, dict):
                    raise rules.GatewayInvalidRequest()
                WsUnvalidatedEnvelope.model_validate(data)
                envelope = WsClientEnvelope.model_validate(data)
            except (ValidationError, rules.GatewayInvalidRequest) as exc:
                # BR2.8 T3：不屬於任何輪次（turnId=null）；不碰 pending_clarify——反問等待中格式錯誤的
                # 選擇訊息不算輪內，反問保留、使用者可重選（[GW-MB2]=A）。
                await self._send_single_error(conn, *rules.error_for(exc))
                continue
            conn.open_turn = None
            try:
                await self._dispatch_client_message(conn, envelope, t_received)
            except Exception as exc:  # 未預期例外：封閉表的 error，連線保留（審查 R-03；[GW3]=A）
                _log(logging.WARNING, "message_unexpected", connId=conn.conn_id, exc=type(exc).__name__)
                await self._on_unexpected(conn, exc)
            finally:
                conn.open_turn = None

    async def _on_unexpected(self, conn: Connection, exc: BaseException) -> None:
        """BR2.8 T9：這則訊息已開啟一輪且該輪的終止事件尚未送達 → 以該輪 turnId 結束它；否則 turnId=null。

        不結束那一輪的話，前端會一直等一個永遠不來的終止事件。若該輪正等待反問選擇，
        一併清除待選反問，使之後的選擇走 T5（無待選反問）而不是接續一個已終止的輪。

        判準是 `turn.terminal_sent`（終止事件是否**實際送出**），不是 `ledger.is_terminal`：`_end_turn`
        先 `ledger.finish()` 再送 done，兩者之間的例外會讓 ledger 已終止而前端沒收到任何終止事件
        （review-02 發現 1）。已送過終止事件 → 只回 turnId=null 的 error，絕不送第二個終止事件。
        刻意安靜結束的輪（`ended_silent`，AC1.2.3）依契約不送終止事件，也走 turnId=null。
        """
        turn = conn.open_turn
        if turn is not None and not turn.terminal_sent and turn.ledger.state != rules.TURN_ENDED_SILENT:
            if conn.pending_clarify is not None and conn.pending_clarify.turn is turn:
                conn.pending_clarify = None
            turn.ledger.fail()  # 已因 finish() 終止時為 no-op；送出與否由 terminal_sent 決定
            code, message = rules.error_for(exc)
            await self._send_terminal(
                conn,
                turn,
                self.envelope(
                    WsServerMessageType.ERROR,
                    turn.turn_id,
                    ErrorPayload(code=code, message=message, turnId=turn.turn_id),
                ),
            )
            self._log_turn(turn, f"error:{code}")
            return
        await self._send_single_error(conn, *rules.error_for(exc))

    async def _reject(self, conn: Connection, reason: str, exc: BaseException) -> bool:
        """被拒訊框：回一則 error，並計入關閉門檻（帶入項 29）。回傳是否已關閉連線。"""
        count = self.rate.note_rejected(conn.conn_id, self.timing.monotonic())
        _log(logging.INFO, "frame_rejected", connId=conn.conn_id, reason=reason, count=count)
        if count >= self.rate.reject_threshold:
            self.registry.unregister(conn)
            conn.dead = True
            await self.close_ws(conn.ws, 1011)
            return True
        await self._send_single_error(conn, *rules.error_for(exc))
        return False

    async def _send_single_error(self, conn: Connection, code: str, message: str) -> None:
        """不屬於任何輪次的錯誤（BR2.8 T1–T5、T7）：envelope 與 payload 的 turnId 一律為 null。

        契約逐字要求伺服器**不得**為非輪次錯誤捏造 turnId（`brain_ws_contract.py` 的 `ErrorPayload`）；
        輪內錯誤一律走 `_fail_turn`／`_end_turn`，帶該輪的 turnId。
        """
        await conn.send(
            self.envelope(WsServerMessageType.ERROR, None, ErrorPayload(code=code, message=message, turnId=None))
        )

    async def _dispatch_client_message(self, conn: Connection, envelope: WsClientEnvelope, t_received: float) -> None:
        kind = envelope.type
        payload = envelope.payload
        if kind is WsClientMessageType.USER_MESSAGE:
            await self._on_user_message(conn, payload, t_received)
        elif kind is WsClientMessageType.SELECT_CLARIFY_CANDIDATE:
            await self._on_select(conn, payload)
        elif kind is WsClientMessageType.SET_WORK_TARGET:
            await self._on_set_work_target(conn, payload)
        elif kind is WsClientMessageType.SET_SHARING_MODE:
            await self._on_set_sharing_mode(conn, payload)
        elif kind is WsClientMessageType.CORRECT_WORK_ITEM:
            await self._on_correct(conn, payload)
        else:  # ready 之後再收到 hello
            await self._send_single_error(conn, *rules.error_for(rules.GatewayInvalidRequest()))

    # -- 輪次訊息的送出 -------------------------------------------------------

    async def send_turn_message(self, conn: Connection, turn: Turn, msg_type: WsServerMessageType, payload: Any) -> bool:
        kind = msg_type.value
        if not turn.ledger.allows(kind):
            _log(logging.WARNING, "turn_message_refused", turnId=turn.turn_id, type=kind)
            return False
        sent = await conn.send(self.envelope(msg_type, turn.turn_id, payload))
        if not sent:
            return False
        if kind in ("token", "cost_card"):
            turn.ledger.content(kind)
            if isinstance(payload, TokenPayload):
                turn.texts.append(payload.text)
        elif kind == "clarify":
            turn.ledger.clarify()
        if turn.t_first_content is None and kind in ("token", "cost_card", "clarify"):
            turn.t_first_content = self.timing.monotonic()
        return True

    async def _send_terminal(self, conn: Connection, turn: Turn, envelope: WsEnvelope) -> bool:
        """送出該輪的終止事件（done／error）；**送達之後**才標記 `turn.terminal_sent`（T9 的判準）。"""
        sent = await conn.send(envelope)
        if sent:
            turn.terminal_sent = True
        return sent

    async def _fail_turn(self, conn: Connection, turn: Turn, code: str, message: str) -> None:
        if turn.ledger.fail():
            await self._send_terminal(
                conn,
                turn,
                self.envelope(
                    WsServerMessageType.ERROR,
                    turn.turn_id,
                    ErrorPayload(code=code, message=message, turnId=turn.turn_id),
                )
            )
        self._log_turn(turn, f"error:{code}")

    async def _fail_turn_exc(self, conn: Connection, turn: Turn, exc: BaseException) -> None:
        await self._fail_turn(conn, turn, *rules.error_for(exc))

    async def _end_turn(self, conn: Connection, turn: Turn) -> None:
        """有內容 → 寫回覆歷程後送 done；無內容 → error(EMPTY_RESPONSE)（BR64.7／BR64.10）。"""
        result = turn.ledger.finish()
        if result is None:
            return
        if result == rules.FINISH_EMPTY:
            await self._send_terminal(
                conn,
                turn,
                self.envelope(
                    WsServerMessageType.ERROR,
                    turn.turn_id,
                    ErrorPayload(code=rules.CODE_EMPTY, message=rules.ERROR_MESSAGES["empty"], turnId=turn.turn_id),
                )
            )
            self._log_turn(turn, f"error:{rules.CODE_EMPTY}")
            return
        if turn.write_history and turn.texts:
            try:
                await asyncio.to_thread(
                    self.store.append_message,
                    conn.session_key,
                    turn.segment,
                    "assistant",
                    _truncate("\n".join(turn.texts)),
                )
            except Exception as exc:  # 內容已送達使用者：只記 WARNING（BR64.10）
                _log(logging.WARNING, "assistant_history_failed", turnId=turn.turn_id, exc=type(exc).__name__)
        await self._send_terminal(
            conn, turn, self.envelope(WsServerMessageType.DONE, turn.turn_id, DonePayload(turnId=turn.turn_id))
        )
        self._log_turn(turn, "done")
        if turn.dispatched:
            content = _truncate(f"使用者：{turn.utterance}\n大腦：" + "\n".join(turn.texts))
            self.spawn(self._write_episodic(conn.principal, content, turn.turn_id))

    def _log_turn(self, turn: Turn, outcome: str) -> None:
        _log(
            logging.INFO,
            "turn_end",
            turnId=turn.turn_id,
            preClassifyMs=_ms(turn.t_received, turn.t_classify_start),
            classifyMs=_ms(turn.t_classify_start, turn.t_classify_end),
            toFirstContentMs=_ms(turn.t_classify_end, turn.t_first_content),
            outcome=outcome,
            prefetch=turn.prefetch,
        )

    # -- user_message（GW-W2）-------------------------------------------------

    async def _on_user_message(self, conn: Connection, payload: Any, t_received: float) -> None:
        turn = Turn(turn_id=_mint_turn_id(), utterance=payload.text, t_received=t_received)
        conn.open_turn = turn
        stale = conn.pending_clarify
        if stale is not None:  # 等待選擇時收到新訊息：舊輪安靜結束（BR64.8）
            stale.turn.ledger.end_silent()
            self._log_turn(stale.turn, "ended_silent")
            conn.pending_clarify = None
        utterance = payload.text
        if not utterance.strip():
            await self._fail_turn_exc(conn, turn, rules.GatewayInvalidRequest())
            return
        if len(utterance) > DEFAULT_MESSAGE_MAX_CHARS:
            await self._fail_turn(conn, turn, rules.CODE_INVALID, rules.ERROR_MESSAGES["too_long"])
            return
        if is_platform_self_modification(utterance):  # BR64.5：先於一切
            await self._refuse(conn, turn)
            return
        try:
            session = await asyncio.to_thread(self.store.load, conn.session_key)
        except Exception as exc:
            await self._fail_turn_exc(conn, turn, exc)
            return
        page_modes = session.page_modes if session is not None else default_page_modes()
        turn.segment = rules.resolve_segment(payload.page, page_modes)

        prefetch = await self._prefetch(conn.principal, utterance, turn)
        context_token = _PREFETCH.set(prefetch)
        router = self.routers[turn.segment]
        classify_exc: Optional[BaseException] = None
        decision = None
        turn.t_classify_start = self.timing.monotonic()
        try:
            decision = await router.classify(
                conn.principal,
                session if session is not None else BrainSession(session_key=conn.session_key),
                utterance,
                turn_id=turn.turn_id,
            )
        except PlatformSelfModificationRefused:
            turn.t_classify_end = self.timing.monotonic()
            await self._refuse(conn, turn)
            return
        except Exception as exc:  # 路由失敗：先寫使用者訊息，再以 error 結束（BR64.6）
            classify_exc = exc
        finally:
            _PREFETCH.reset(context_token)
        turn.t_classify_end = self.timing.monotonic()
        if isinstance(classify_exc, MemoryForbidden):
            # 安全事件（合併前必修第 13 項）：只記 turnId 與拒絕理由代碼，不記輸入原文、不記記憶內容。
            _log(logging.WARNING, "memory_forbidden", turnId=turn.turn_id, reason=classify_exc.reason)

        try:
            await asyncio.to_thread(self.store.append_message, conn.session_key, turn.segment, "user", utterance)
        except Exception as exc:
            await self._fail_turn_exc(conn, turn, exc)
            return
        if classify_exc is not None:
            await self._fail_turn_exc(conn, turn, classify_exc)
            return

        if decision.below_threshold:
            await self._clarify_intent(conn, turn, decision)
            return
        await self._resolve_and_dispatch(conn, turn, decision, scan=False, session=session)

    async def _refuse(self, conn: Connection, turn: Turn) -> None:
        turn.write_history = False
        await self.send_turn_message(conn, turn, WsServerMessageType.TOKEN, TokenPayload(text=REFUSAL_MESSAGE))
        if turn.ledger.finish() == rules.FINISH_DONE:
            await self._send_terminal(
                conn, turn, self.envelope(WsServerMessageType.DONE, turn.turn_id, DonePayload(turnId=turn.turn_id))
            )
        self._log_turn(turn, "guard")

    async def _clarify_intent(self, conn: Connection, turn: Turn, decision: IntentDecision) -> None:
        candidates = tuple(decision.candidates or ())
        if not candidates:
            await self._fail_turn(conn, turn, rules.CODE_INTERNAL, rules.ERROR_MESSAGES["internal"])
            return
        wire = [
            ClarifyCandidate(id=c.id, label=c.label, capability=c.capability, confidence=c.confidence)
            for c in candidates
        ]
        if not await self.send_turn_message(
            conn, turn, WsServerMessageType.CLARIFY, ClarifyPayload(candidates=wire, kind="intent")
        ):
            return
        conn.pending_clarify = PendingClarify(
            turn=turn,
            kind="intent",
            candidate_ids=tuple(c.id for c in candidates),
            candidates={c.id: c for c in candidates},
            decision=decision,  # 合併前必修第 5 項：保留行程內的還原對照（`decision.resolution`）
        )
        self._log_turn(turn, "clarify")

    async def _clarify_target(
        self, conn: Connection, turn: Turn, targets: Tuple[rules.TargetRef, ...], decision: IntentDecision
    ) -> None:
        capability = decision.intents[0].capability if decision.intents else ""
        ids = tuple(f"target-{n}" for n in range(1, len(targets) + 1))
        wire = [
            ClarifyCandidate(id=cid, label=rules.target_label(t), capability=capability, confidence=None)
            for cid, t in zip(ids, targets)
        ]
        if not await self.send_turn_message(
            conn, turn, WsServerMessageType.CLARIFY, ClarifyPayload(candidates=wire, kind="target")
        ):
            return
        conn.pending_clarify = PendingClarify(
            turn=turn,
            kind="target",
            candidate_ids=ids,
            targets=dict(zip(ids, targets)),
            decision=decision,
        )
        self._log_turn(turn, "clarify")

    async def _reply_and_end(self, conn: Connection, turn: Turn, reply: str) -> None:
        """`BR64.11` (b)(c) 與「專案太多」：一則固定句型 ＋ done；不交辦、不寫 episodic。"""
        await self.send_turn_message(conn, turn, WsServerMessageType.TOKEN, TokenPayload(text=reply))
        await self._end_turn(conn, turn)

    # -- 對象解析與交辦（BR64.9／BR64.11／BR64.12／BR64.13）---------------------

    def _build_catalog(self, principal: Any, selected_project_id: Optional[int]) -> rules.TargetCatalog:
        db = self.session_factory()
        try:
            facade = self.hierarchy_facade_factory(db)
            # nfr-requirements `R-01`：目錄（反問標籤與唯一命中）同受 `U23` 可見性守門；
            # 同一個 facade 實例使可見集合只查一次（ADR-0022 D-5）。
            vis = self.membership_facade_factory(db)
            projects = [
                (p.id, p.name)
                for p in facade.list_projects(principal, project_visible=vis.project_visibility(principal))
            ]
            systems: List[Tuple[int, int, str]] = []
            truncated = len(projects) > rules.CATALOG_PROJECT_MAX
            if not truncated:
                for pid, _name in projects:
                    systems.extend(
                        (pid, s.id, s.name)
                        for s in facade.list_systems(
                            principal, project_id=pid, project_visible=vis.project_visibility(principal)
                        )
                    )
            elif selected_project_id is not None and any(pid == selected_project_id for pid, _ in projects):
                systems.extend(
                    (selected_project_id, s.id, s.name)
                    for s in facade.list_systems(
                        principal,
                        project_id=selected_project_id,
                        project_visible=vis.project_visibility(principal),
                    )
                )
            return rules.TargetCatalog(projects=tuple(projects), systems=tuple(systems), truncated=truncated)
        finally:
            db.close()

    async def _catalog(self, conn: Connection, turn: Turn, session: Optional[BrainSession]):
        segment = (session.segments or {}).get(turn.segment) if session is not None else None
        selected = getattr(segment, "project_id", None)
        try:
            catalog = await asyncio.to_thread(self._build_catalog, conn.principal, selected)
        except Exception as exc:
            await self._fail_turn_exc(conn, turn, exc)
            return None, selected
        if catalog.truncated:
            _log(logging.INFO, "catalog_truncated", turnId=turn.turn_id, count=len(catalog.projects))
        return catalog, selected

    async def _resolve_and_dispatch(
        self,
        conn: Connection,
        turn: Turn,
        decision: IntentDecision,
        *,
        scan: bool,
        session: Optional[BrainSession],
    ) -> None:
        if scan:
            catalog, selected = await self._catalog(conn, turn, session)
            if catalog is None:
                return
            hits = rules.scan_targets_in_utterance(turn.utterance, catalog)
            if hits:  # 掃描命中一律以對象反問確認，不靜默改動作業對象（帶入項 1）
                await self._clarify_target(conn, turn, tuple(hits), decision)
                return
            if catalog.truncated and selected is None:  # 帶入項 28：不得靜默交辦給舊對象
                await self._reply_and_end(conn, turn, TOO_MANY_PROJECTS_MESSAGE)
                return
            await self._dispatch(conn, turn, decision)
            return

        referents = [i.referent.strip() for i in decision.intents if i.referent is not None and i.referent.strip()]
        if not referents:  # 未指名對象：依當前作業對象交辦（帶入項 13）
            await self._dispatch(conn, turn, decision)
            return
        if len({rules.norm(r) for r in referents}) > 1:
            await self._reply_and_end(conn, turn, CONFLICTING_TARGETS_MESSAGE)
            return
        catalog, selected = await self._catalog(conn, turn, session)
        if catalog is None:
            return
        match = rules.match_referent(referents[0], catalog, selected)
        if match.kind == rules.MATCH_UNIQUE:
            if await self._set_target_confirmed(conn, turn, turn.segment, match.targets[0]):
                await self._dispatch(conn, turn, decision)
            return
        if match.kind == rules.MATCH_MANY:
            await self._clarify_target(conn, turn, match.targets, decision)
            return
        reply = TOO_MANY_PROJECTS_MESSAGE if catalog.truncated else not_found_message(referents[0])
        await self._reply_and_end(conn, turn, reply)

    async def _set_target_confirmed(
        self, conn: Connection, turn: Optional[Turn], segment_id: str, target: rules.TargetRef
    ) -> bool:
        """set_work_target ＋ 扇出；`SessionBackendUnavailable` 時重讀確認「結果未知」（reliability-design §四）。"""
        try:
            session = await asyncio.to_thread(
                self.store.set_work_target,
                conn.session_key,
                segment_id,
                conn.principal,
                target.project_id,
                target.system_id,
                None,
            )
        except SessionBackendUnavailable as exc:
            session = await self._reread_target(conn, segment_id, target)
            if session is None:
                await self._error_for_request(conn, turn, exc)
                return False
        except Exception as exc:
            await self._error_for_request(conn, turn, exc)
            return False
        await self.fanout(conn.session_key, await self._named_work_target_envelope(conn, session, segment_id))
        return True

    async def _reread_target(self, conn: Connection, segment_id: str, target: rules.TargetRef):
        try:
            session = await asyncio.to_thread(self.store.load, conn.session_key)
        except Exception:
            return None
        segment = (session.segments or {}).get(segment_id) if session is not None else None
        if segment is not None and segment.project_id == target.project_id and segment.system_id == target.system_id:
            return session
        return None

    async def _error_for_request(self, conn: Connection, turn: Optional[Turn], exc: BaseException) -> None:
        if turn is not None:
            await self._fail_turn_exc(conn, turn, exc)
        else:
            await self._send_single_error(conn, *rules.error_for(exc))

    async def _dispatch(self, conn: Connection, turn: Turn, decision: IntentDecision) -> None:
        try:
            session = await asyncio.to_thread(self.store.load, conn.session_key)
        except Exception as exc:
            await self._fail_turn_exc(conn, turn, exc)
            return
        sink = GatewaySink(self, conn.session_key, origin=(conn, turn), segment_id=turn.segment)
        turn.dispatched = True
        try:
            await self.orchestrator.dispatch(
                conn.principal,
                session if session is not None else BrainSession(session_key=conn.session_key),
                decision,
                utterance=turn.utterance,
                segment_id=turn.segment,
                turn_id=turn.turn_id,
                bearer_token=conn.token,
                sink=sink,
            )
        except Exception as exc:  # dispatch 的 ValueError 等：INTERNAL_ERROR（BR67.1）
            await self._fail_turn_exc(conn, turn, exc)
            return
        await self._end_turn(conn, turn)

    # -- select_clarify_candidate（GW-W3）-------------------------------------

    async def _on_select(self, conn: Connection, payload: Any) -> None:
        pending = conn.pending_clarify
        if pending is None:
            await self._send_single_error(conn, *rules.error_for(rules.GatewayInvalidRequest()))
            return
        conn.pending_clarify = None
        turn = pending.turn
        conn.open_turn = turn
        candidate_id = payload.candidateId
        if candidate_id is None:  # 「都不是」：安靜結束，不送任何狀態訊息與終止事件（AC1.2.3）
            turn.ledger.end_silent()
            self._log_turn(turn, "ended_silent")
            return
        if candidate_id not in pending.candidate_ids:
            await self._fail_turn_exc(conn, turn, rules.GatewayInvalidRequest())
            return
        turn.ledger.reopen()
        if pending.kind == "target":
            if await self._set_target_confirmed(conn, turn, turn.segment, pending.targets[candidate_id]):
                await self._dispatch(conn, turn, pending.decision)
            return
        chosen = pending.candidates[candidate_id]
        # 合併前必修第 5 項：以「被選候選的完整 Intent（含 referent）＋ 其他已確定槽位的 Intent」
        # 依原句的槽位序重建；對照缺失或對不上即大聲失敗，不退回只帶 capability 的舊形狀。
        resolution = getattr(pending.decision, "resolution", None)
        intents = intents_after_choice(resolution, candidate_id) if resolution is not None else None
        if not intents:
            await self._fail_turn(conn, turn, rules.CODE_INTERNAL, rules.ERROR_MESSAGES["internal"])
            return
        decision = IntentDecision(
            intents=intents,
            confidence=chosen.confidence if chosen.confidence is not None else 0.0,
            below_threshold=False,
        )
        try:
            session = await asyncio.to_thread(self.store.load, conn.session_key)
        except Exception as exc:
            await self._fail_turn_exc(conn, turn, exc)
            return
        await self._resolve_and_dispatch(conn, turn, decision, scan=True, session=session)

    # -- set_work_target／set_sharing_mode／correct_work_item（GW-W4）-----------

    async def _on_set_work_target(self, conn: Connection, payload: Any) -> None:
        try:
            ids = [_parse_id(v) for v in (payload.projectId, payload.systemId, payload.diagramId)]
        except rules.GatewayInvalidRequest as exc:
            await self._send_single_error(conn, *rules.error_for(exc))
            return
        segment_id = payload.segment
        try:
            session = await asyncio.to_thread(
                self.store.set_work_target, conn.session_key, segment_id, conn.principal, *ids
            )
        except SessionBackendUnavailable as exc:
            try:
                session = await asyncio.to_thread(self.store.load, conn.session_key)
            except Exception:
                session = None
            segment = (session.segments or {}).get(segment_id) if session is not None else None
            if segment is None or [segment.project_id, segment.system_id, segment.diagram_id] != ids:
                await self._send_single_error(conn, *rules.error_for(exc))
                return
        except Exception as exc:
            await self._send_single_error(conn, *rules.error_for(exc))
            return
        await self.fanout(conn.session_key, await self._named_work_target_envelope(conn, session, segment_id))

    async def _on_set_sharing_mode(self, conn: Connection, payload: Any) -> None:
        scope, mode = payload.scope, payload.mode
        try:
            session = await asyncio.to_thread(self.store.set_sharing_mode, conn.session_key, scope, mode)
        except SessionBackendUnavailable as exc:
            try:
                session = await asyncio.to_thread(self.store.load, conn.session_key)
            except Exception:
                session = None
            if session is None or (session.page_modes or {}).get(scope) != mode:
                await self._send_single_error(conn, *rules.error_for(exc))
                return
        except Exception as exc:
            await self._send_single_error(conn, *rules.error_for(exc))
            return
        segment_id = rules.resolve_segment(scope, session.page_modes or {})
        work_target = await self._named_work_target_envelope(conn, session, segment_id)
        # 兩則同一次扇出：每條連線依序收兩則，連線之間並行（審查 R-05）。
        await self.fanout_many(
            conn.session_key,
            [
                self.envelope(WsServerMessageType.SHARING_MODE, None, SharingModePayload(mode=mode, scope=scope)),
                work_target,
            ],
        )

    async def _on_correct(self, conn: Connection, payload: Any) -> None:
        try:
            items = await asyncio.to_thread(self.store.load_work_items, conn.session_key)
            segment_id = (items.get(payload.workItemId) or {}).get("segmentId")
            await self.orchestrator.correct(
                conn.principal,
                conn.session_key,
                payload.workItemId,
                bearer_token=conn.token,
                sink=GatewaySink(self, conn.session_key, segment_id=segment_id),
            )
        except Exception as exc:  # WorkItemNotFound → INVALID_REQUEST；其餘依封閉表
            await self._send_single_error(conn, *rules.error_for(exc))

    # -- 記憶（BR67.7／BR67.10）-------------------------------------------------

    async def _prefetch(self, principal: Any, query: str, turn: Turn) -> MemoryPrefetch:
        factory = self.memory_facade_factory
        session_factory = self.session_factory

        def _search():
            db = session_factory()
            try:
                return tuple(factory(db).search(principal, query, kinds=PREFETCH_KINDS, limit=PREFETCH_LIMIT))
            except MemoryForbidden as exc:
                # 授權判定不是依賴故障：不計入熔斷、不降級，改以結果帶回（合併前必修第 13 項）。
                return _PrefetchForbidden(exc.reason)
            finally:
                db.close()

        _log(logging.DEBUG, "prefetch_start", turnId=turn.turn_id)
        started = self.timing.monotonic()
        result = await self.memory.run(_search, wait_sec=self.prefetch_wait_sec)
        if result.outcome is Outcome.OK and isinstance(result.value, _PrefetchForbidden):
            turn.prefetch = "forbidden"
            return MemoryPrefetch(
                user_id=principal.user_id,
                query=query,
                kinds=PREFETCH_KINDS,
                hits=None,
                forbidden_reason=result.value.reason,
            )
        hits = result.value if result.outcome is Outcome.OK else None
        if result.outcome is Outcome.OK:
            turn.prefetch = "hit" if hits else "empty"
        else:
            turn.prefetch = result.outcome.value
        _log(
            logging.DEBUG,
            "prefetch_end",
            turnId=turn.turn_id,
            prefetch=turn.prefetch,
            elapsedMs=_ms(started, self.timing.monotonic()),
            exc=result.exc_name,
        )
        return MemoryPrefetch(user_id=principal.user_id, query=query, kinds=PREFETCH_KINDS, hits=hits)

    async def _write_episodic(self, principal: Any, content: str, turn_id: str) -> None:
        factory = self.memory_facade_factory
        session_factory = self.session_factory

        def _write():
            db = session_factory()
            try:
                return factory(db).write(principal, "episodic", content)
            finally:
                db.close()

        result = await self.memory.run(_write, wait_sec=self.episodic_wait_sec)
        if result.outcome is Outcome.FAILED:
            _log(logging.WARNING, "episodic_write_failed", turnId=turn_id, exc=result.exc_name)

    async def append_assistant_background(self, key: str, segment_id: str, spoken: List[str]) -> None:
        try:
            await asyncio.to_thread(self.store.append_message, key, segment_id, "assistant", _truncate("\n".join(spoken)))
        except Exception as exc:  # 推播已送達：只記 WARNING（BR65.5）
            _log(logging.WARNING, "push_history_failed", exc=type(exc).__name__)

    # -- 關閉 ----------------------------------------------------------------

    def shutdown(self) -> None:
        """取消本閘道的背景 task、關閉**自己的**記憶執行器（帶入項 22）。"""
        for task in list(self._bg_tasks):
            if task.done():
                continue
            try:
                task.cancel()
            except RuntimeError:  # task 所屬的事件迴圈已關閉（測試環境）：無可取消
                _log(logging.DEBUG, "shutdown_cancel_skipped")
        self.memory.shutdown()


def _parse_id(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.isdecimal() or not value.isascii():
        raise rules.GatewayInvalidRequest()
    return int(value)


def _truncate(spoken: str, limit: int = DEFAULT_MESSAGE_MAX_CHARS) -> str:
    if len(spoken) <= limit:
        return spoken
    return spoken[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# 端點與啟動（BR61.1／BR67.11）
# ---------------------------------------------------------------------------

router = APIRouter()


@router.websocket("/ws")
async def brain_ws(websocket: WebSocket) -> None:
    gateway = getattr(websocket.app.state, "brain_gateway", None)
    if gateway is None:  # 未觸發 startup（或建立失敗）：不在請求路徑上延遲建立
        _log(logging.ERROR, "gateway_missing")
        offer = rules.parse_subprotocol_offer(websocket.headers.get("sec-websocket-protocol"))
        if not offer.has_protocol_name:
            await websocket.close()
            return
        await websocket.accept(subprotocol=rules.PROTOCOL_NAME)
        await websocket.close(code=1011, reason=CLOSE_REASONS[1011])
        return
    await gateway.handle(websocket)


def build_brain_gateway(app: Any, *, membership_facade_factory: Callable[[Any], Any]) -> BrainGateway:
    """startup hook 呼叫（`configure_intent_routing_env` 之後、`init_db` 之前）。

    三個 Redis 變數缺值 → `KeyError`；`REDIS_USER=default` → `ValueError`；兩者皆使啟動失敗。
    client 延遲連線，Redis 暫時不可達不阻止啟動，在握手時以 1011 呈現（`F-29`）。

    `membership_facade_factory`（ADR-0022 D-6）**必填、無預設**：漏傳即 `TypeError`、啟動失敗。
    同一個 factory 交給 `_HierarchyResolver`（直接設定作業對象）與 `BrainGateway`（名稱、目錄）。
    """
    client = build_redis_client(
        os.environ["REDIS_URL"],
        user=os.environ["REDIS_USER"],
        password=os.environ["REDIS_PASSWORD"],
    )
    session_factory = _default_session_factory
    store = SessionStore(
        RedisGateway(client, error_types=redis_py_error_types()),
        hierarchy_facade=_HierarchyResolver(
            session_factory, HierarchyFacade, membership_facade_factory=membership_facade_factory
        ),
        history_max=resolve_history_max(),
    )
    timing = GatewayTiming()
    adapter = MemoryPrefetchAdapter()
    routers = {segment: IntentRouter(memory_facade=adapter, segment_id=segment) for segment in SEGMENT_IDS}
    orchestrator = WorkOrchestrator(app, store)
    return BrainGateway(
        store=store,
        routers=routers,
        orchestrator=orchestrator,
        session_factory=session_factory,
        timing=timing,
        membership_facade_factory=membership_facade_factory,
        memory_worker=MemoryWorker(timing),
        prefetch_adapter=adapter,
    )


__all__ = [
    "BrainGateway",
    "ConnectionRegistry",
    "GatewaySink",
    "GatewayTiming",
    "MemoryPrefetchAdapter",
    "MemoryWorker",
    "Outcome",
    "build_brain_gateway",
    "router",
]
