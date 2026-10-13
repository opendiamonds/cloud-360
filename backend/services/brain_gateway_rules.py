"""
brain_gateway_rules.py — `U13 brain-gateway` 的純函式與純狀態機

**本模組不做任何 I/O**：無 socket、無 DB session、無 Redis、無 logger 呼叫、無時鐘。
時間一律由呼叫端以參數傳入（`now`），所以這裡的每一個函式都能被 property-based
測試直接驅動（`functional-spec.md` §七的五個性質；`NFR13.42`）。

契約（`brain_gateway.py` 依賴，請勿變更）：

| 名稱 | 規則 | 用途 |
|---|---|---|
| `parse_subprotocol_offer(header)` | `BR61.2` | 由 `Sec-WebSocket-Protocol` 取協定名與 bearer token |
| `session_key_for(u)`／`user_id_from_session_key(k)` | `BR62.3` | session key 的推導與反推 |
| `resolve_segment(page, page_modes)` | `BR62.5` | 一則訊息寫入哪一段 |
| `TurnLedger` | `BR64.7` | 一輪的終止語意（至多一個終止事件） |
| `error_for(exc)` | `BR67.1` | 例外 → 封閉的 (code, message) 表 |
| `match_referent(referent, catalog, selected_project_id)` | `BR64.9`／`BR64.11` | 高信心路徑的對象解析 |
| `scan_targets_in_utterance(utterance, catalog)` | `BR64.13`（由帶入項 1、2、11 改寫） | 反問選定意圖後的原句掃描 |
| `is_transient_memory_failure(exc)` | `NFR13.25` | 記憶熔斷的開啟條件 |
| `BreakerState` | `BR67.12` | 記憶熔斷的狀態機 |
| `RateLimiter` | `NFR13.20` | 每 key／每連線的滑動窗，另含握手頻率 |
| `hello_version(data)` | `BR61.8` | 首則訊息的版本判定與 4400 的 received |

協定名與 bearer 前綴**由契約模型取值**（`WsSubprotocol` 的字面型別），不在本模組另寫
一份字串（`team.md` 的單一真實來源）。
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple, get_args

from pydantic import ValidationError

from services.brain_ws_contract import WsSubprotocol
from services.hierarchy_facade import HierarchyForbidden, HierarchyNotFound
from services.intent_routing_errors import (
    EmptyCandidates,
    LlmBudgetExceeded,
    LlmUnavailable,
    MalformedRouting,
)
from services.session_errors import SessionBackendUnavailable, SessionMessageTooLong
from services.session_store import DEFAULT_MESSAGE_MAX_CHARS
from services.session_types import PAGE_SCOPES, SEGMENT_SHARED, SHARING_ISOLATED
from services.work_orchestrator import WorkItemNotFound

# ---------------------------------------------------------------------------
# 協定常數（由契約取值）
# ---------------------------------------------------------------------------

PROTOCOL_NAME: str = get_args(WsSubprotocol.model_fields["protocolName"].annotation)[0]
BEARER_PREFIX: str = (
    get_args(WsSubprotocol.model_fields["scheme"].annotation)[0]
    + get_args(WsSubprotocol.model_fields["separator"].annotation)[0]
)
PROTOCOL_VERSION = 1
SESSION_KEY_PREFIX = "brain:session:"
PAGE_ENTRY = "entry"

# ---------------------------------------------------------------------------
# 數值（全部為模組常數，NFR13.44：不新增環境變數）
# ---------------------------------------------------------------------------

#: `NFR13.17`／`NFR13.18`：每行程的佔位上限、每 session key 的佔位上限（`[GWN1]`=A）。
MAX_TOTAL_CONNECTIONS = 200
MAX_CONNECTIONS_PER_KEY = 10
#: `NFR13.19`：入站單一訊框的位元組上限（應用層，不動 uvicorn 的全域 ws_max_size）。
MAX_FRAME_BYTES = 65536
#: `NFR13.20`：滑動窗長度與兩個上限。
RATE_WINDOW_SEC = 60.0
RATE_USER_MESSAGES_PER_KEY = 20
RATE_FRAMES_PER_CONNECTION = 120
#: 帶入項 20（nfr-design R-03）：握手也納入限流。以 session key 計，認證之後、accept 之前判定。
#: 數值為本站選定：每分鐘 30 次握手容得下「10 條連線同時重連」三輪，擋住無上限的重連迴圈。
RATE_HANDSHAKES_PER_KEY = 30
#: 帶入項 29（nfr-design R-12）：同一連線在一個滑動窗內被拒（過大、過頻）達此數即以 1011 關閉。
REJECTED_FRAMES_CLOSE_THRESHOLD = 20
#: `NFR13.22`：載入中暫存佇列上限。
PENDING_OUTBOUND_MAX = 256
#: `BR64.12`：對象目錄的專案數上限。
CATALOG_PROJECT_MAX = 50
#: `BR67.12`：記憶熔斷開啟期。
BREAKER_OPEN_SEC = 30.0
#: 名稱掃描的最小名稱長度（`BR64.13`）。
SCAN_MIN_NAME_LEN = 2
#: 名稱掃描的句長上界（審查 R-01）：沿用既有的單則訊息上限，不另立數值。
SCAN_MAX_CHARS = DEFAULT_MESSAGE_MAX_CHARS

# ---------------------------------------------------------------------------
# 子協定（BR61.2）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubprotocolOffer:
    """握手請求的子協定解析結果。`bearer_token` 不進 `repr`（`BR62.2`）。"""

    has_protocol_name: bool
    bearer_token: Optional[str] = field(default=None, repr=False)


def parse_subprotocol_offer(header: Optional[str]) -> SubprotocolOffer:
    """逗號切分、去空白、逐字比對協定名；bearer 項以**第一個**點切分。

    不得以 `split('.')` 取兩段：JWT 本身含兩個點（`brain_ws_contract.WsSubprotocol`
    的實作陷阱）。本函式不讀 query string、不做 I/O。
    """
    offered = [item.strip() for item in (header or "").split(",")]
    has_name = PROTOCOL_NAME in offered
    token: Optional[str] = None
    for item in offered:
        if item.startswith(BEARER_PREFIX):
            token = item.split(".", 1)[1] if "." in item else ""
            break
    if not token:
        token = None
    return SubprotocolOffer(has_protocol_name=has_name, bearer_token=token)


# ---------------------------------------------------------------------------
# session key（BR62.3）
# ---------------------------------------------------------------------------

_SESSION_KEY_RE = re.compile(r"^brain:session:([1-9][0-9]*)$")


def session_key_for(user_id: int) -> str:
    """`brain:session:<正整數>`。bool 不是合法的 user id。"""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id 必須是正整數")
    return SESSION_KEY_PREFIX + str(user_id)


def user_id_from_session_key(session_key: str) -> int:
    match = _SESSION_KEY_RE.match(session_key or "")
    if match is None:
        raise ValueError("不是大腦 session key 的形狀")
    return int(match.group(1))


# ---------------------------------------------------------------------------
# 段（BR62.5）
# ---------------------------------------------------------------------------


def resolve_segment(page: str, page_modes: Mapping[str, str]) -> str:
    """`entry` → `shared`；工作頁在 `isolated` 模式下讀自己的段，否則讀共享段。"""
    if page == PAGE_ENTRY:
        return SEGMENT_SHARED
    if page in PAGE_SCOPES:
        return page if (page_modes or {}).get(page) == SHARING_ISOLATED else SEGMENT_SHARED
    raise ValueError("page 不在契約的三值內")


# ---------------------------------------------------------------------------
# 一輪的終止語意（BR64.7，PBT 性質三）
# ---------------------------------------------------------------------------

TURN_OPEN = "open"
TURN_CLARIFYING = "clarifying"
TURN_STREAMING = "streaming"
TURN_DONE = "done"
TURN_ERROR = "error"
TURN_ENDED_SILENT = "ended_silent"
_TERMINAL_STATES = frozenset({TURN_DONE, TURN_ERROR, TURN_ENDED_SILENT})
_CONTENT_KINDS = frozenset({"token", "cost_card"})

FINISH_DONE = "done"
FINISH_EMPTY = "EMPTY_RESPONSE"


class TurnLedger:
    """一輪的守門員。所有輪次訊息（token／clarify／cost_card／done／error）都先問它。

    狀態：open →(內容) streaming；open →(clarify) clarifying →(reopen) open；
    clarifying →(end_silent) ended_silent；open／streaming／clarifying →(finish／fail)
    done 或 error。三個終態之後一律拒絕。
    """

    def __init__(self) -> None:
        self._state = TURN_OPEN
        self._has_content = False

    @property
    def state(self) -> str:
        return self._state

    @property
    def has_content(self) -> bool:
        return self._has_content

    @property
    def is_terminal(self) -> bool:
        return self._state in _TERMINAL_STATES

    def allows(self, kind: str) -> bool:
        if self.is_terminal:
            return False
        if self._state == TURN_CLARIFYING:
            return kind == "error"
        if self._state == TURN_OPEN:
            return kind in ("token", "cost_card", "clarify", "error", "done")
        # streaming
        return kind in ("token", "cost_card", "error", "done")

    def clarify(self) -> bool:
        if self._state != TURN_OPEN:
            return False
        self._state = TURN_CLARIFYING
        return True

    def reopen(self) -> bool:
        if self._state != TURN_CLARIFYING:
            return False
        self._state = TURN_OPEN
        return True

    def content(self, kind: str) -> bool:
        if kind not in _CONTENT_KINDS or self._state not in (TURN_OPEN, TURN_STREAMING):
            return False
        self._state = TURN_STREAMING
        self._has_content = True
        return True

    def finish(self) -> Optional[str]:
        """要結束時：有內容 → `done`；否則 `EMPTY_RESPONSE`。已終止則回 `None`（不得再送）。"""
        if self.is_terminal:
            return None
        if self._has_content:
            self._state = TURN_DONE
            return FINISH_DONE
        self._state = TURN_ERROR
        return FINISH_EMPTY

    def fail(self) -> bool:
        if self.is_terminal:
            return False
        self._state = TURN_ERROR
        return True

    def end_silent(self) -> bool:
        if self._state != TURN_CLARIFYING:
            return False
        self._state = TURN_ENDED_SILENT
        return True


# ---------------------------------------------------------------------------
# 錯誤對應（BR67.1，封閉表）
# ---------------------------------------------------------------------------


class GatewayInvalidRequest(Exception):
    """本單元自己判定的不合法請求（空白訊息、識別字格式錯、無等待中的反問…）。"""


class FrameTooLarge(Exception):
    """`NFR13.19`：入站訊框超過位元組上限。"""


class RateLimited(Exception):
    """`NFR13.20`：超過頻率上限。"""


ERROR_MESSAGES: Mapping[str, str] = {
    "routing": "大腦暫時無法判讀這句話，請再說一次",
    "session": "工作階段暫時無法存取，請稍後再試",
    "too_long": "訊息太長，請縮短後再送出",
    "forbidden_target": "你沒有權限選擇這個作業對象",
    "target_not_found": "找不到這個作業對象",
    "work_item_not_found": "找不到這個工作項",
    "format": "訊息格式不正確",
    "rate": "訊息太頻繁，請稍候再送出",
    "internal": "處理時發生錯誤，請再說一次",
    "empty": "這一輪沒有產生任何回覆，請再說一次",
}

CODE_INVALID = "INVALID_REQUEST"
CODE_INTERNAL = "INTERNAL_ERROR"
CODE_UNAUTHORIZED = "UNAUTHORIZED"
CODE_EMPTY = "EMPTY_RESPONSE"


def error_for(exc: BaseException) -> Tuple[str, str]:
    """例外 → (code, message)。message 只取自 `ERROR_MESSAGES`，**永不含 `str(exc)`**。"""
    if isinstance(exc, (LlmUnavailable, LlmBudgetExceeded, EmptyCandidates, MalformedRouting)):
        return CODE_INTERNAL, ERROR_MESSAGES["routing"]
    if isinstance(exc, SessionBackendUnavailable):
        return CODE_INTERNAL, ERROR_MESSAGES["session"]
    if isinstance(exc, (SessionMessageTooLong, FrameTooLarge)):
        return CODE_INVALID, ERROR_MESSAGES["too_long"]
    if isinstance(exc, HierarchyForbidden):
        return CODE_UNAUTHORIZED, ERROR_MESSAGES["forbidden_target"]
    if isinstance(exc, HierarchyNotFound):
        return CODE_INVALID, ERROR_MESSAGES["target_not_found"]
    if isinstance(exc, WorkItemNotFound):
        return CODE_INVALID, ERROR_MESSAGES["work_item_not_found"]
    if isinstance(exc, RateLimited):
        return CODE_INVALID, ERROR_MESSAGES["rate"]
    # JSONDecodeError 是 ValueError 的子類，必須排在「其餘 ValueError → INTERNAL」之前。
    if isinstance(exc, (ValidationError, json.JSONDecodeError, GatewayInvalidRequest)):
        return CODE_INVALID, ERROR_MESSAGES["format"]
    return CODE_INTERNAL, ERROR_MESSAGES["internal"]


# ---------------------------------------------------------------------------
# 版本協商（BR61.8）
# ---------------------------------------------------------------------------


def hello_version(data: Any) -> Tuple[bool, str]:
    """回 `(相容與否, received 字串)`。received 只會是十進位整數或字面 `invalid`。"""
    if not isinstance(data, dict):
        return False, "invalid"
    raw_v = data.get("v")
    received = str(raw_v) if isinstance(raw_v, int) and not isinstance(raw_v, bool) else "invalid"
    if data.get("type") != "hello" or received != str(PROTOCOL_VERSION):
        return False, received
    return True, received


def close_reason_for_version(received: str) -> str:
    return f"expected={PROTOCOL_VERSION} received={received}"


# ---------------------------------------------------------------------------
# 對象目錄與名稱比對（BR64.9／BR64.12／BR64.13；帶入項 1、2、11）
# ---------------------------------------------------------------------------


def norm(name: str) -> str:
    """名稱正規化：去頭尾空白後 casefold（不動內部空白；NFR13.28）。"""
    return (name or "").strip().casefold()


@dataclass(frozen=True)
class TargetRef:
    """目錄中的一個對象。`system_id` 為 None 表示對象是專案本身。"""

    project_id: int
    system_id: Optional[int]
    name: str
    project_name: str

    @property
    def key(self) -> Tuple[int, Optional[int]]:
        return (self.project_id, self.system_id)


@dataclass(frozen=True)
class TargetCatalog:
    """`BR64.12` 的對象目錄。`truncated` 為真時 `systems` 只含已選專案的系統（或為空）。"""

    projects: Tuple[Tuple[int, str], ...] = ()
    systems: Tuple[Tuple[int, int, str], ...] = ()
    truncated: bool = False

    def entries(self) -> Tuple[TargetRef, ...]:
        """全部條目依目錄序：專案依序，各專案之後緊接其系統。"""
        names = {pid: pname for pid, pname in self.projects}
        out = []
        for pid, pname in self.projects:
            out.append(TargetRef(pid, None, pname, pname))
            for spid, sid, sname in self.systems:
                if spid == pid:
                    out.append(TargetRef(pid, sid, sname, pname))
        # 已選專案不在 projects 內（理論上不會發生）時，仍保留其系統。
        for spid, sid, sname in self.systems:
            if spid not in names:
                out.append(TargetRef(spid, sid, sname, ""))
        return tuple(out)


MATCH_UNIQUE = "unique"
MATCH_MANY = "many"
MATCH_NONE = "none"


@dataclass(frozen=True)
class MatchResult:
    kind: str
    targets: Tuple[TargetRef, ...] = ()


def _absorb_projects(hits: Sequence[TargetRef]) -> Tuple[TargetRef, ...]:
    """系統命中吸收其所屬專案的命中；依 (project_id, system_id) 去重、保持順序（帶入項 2）。"""
    projects_with_system = {t.project_id for t in hits if t.system_id is not None}
    out, seen = [], set()
    for t in hits:
        if t.system_id is None and t.project_id in projects_with_system:
            continue
        if t.key in seen:
            continue
        seen.add(t.key)
        out.append(t)
    return tuple(out)


def match_referent(
    referent: str, catalog: TargetCatalog, selected_project_id: Optional[int]
) -> MatchResult:
    """`BR64.9`：已選專案時先比對其系統；否則（含未選定）比對全部系統與專案名稱。

    比對為 `norm` 後**精確相等**。同名的專案與其自己的系統視為一個對象（該系統）。
    """
    wanted = norm(referent)
    if not wanted:
        return MatchResult(MATCH_NONE)
    entries = catalog.entries()
    if selected_project_id is not None:
        in_project = [
            t for t in entries
            if t.system_id is not None and t.project_id == selected_project_id and norm(t.name) == wanted
        ]
        if len(in_project) == 1:
            return MatchResult(MATCH_UNIQUE, (in_project[0],))
    hits = _absorb_projects([t for t in entries if norm(t.name) == wanted])
    if not hits:
        return MatchResult(MATCH_NONE)
    if len(hits) == 1:
        return MatchResult(MATCH_UNIQUE, hits)
    return MatchResult(MATCH_MANY, hits)


def _occurrences(haystack: str, needle: str) -> list:
    spans, start = [], 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            return spans
        spans.append((idx, idx + len(needle)))
        start = idx + 1


def scan_targets_in_utterance(utterance: str, catalog: TargetCatalog) -> list:
    """原句中的**最長完整名稱**（`reliability-design.md` §7.2）。

    1. 原句只 casefold，且只掃前 `SCAN_MAX_CHARS` 字（沿用既有的單則訊息上限）；條目名稱以 `norm`
       正規化，長度 < 2 者不參與。
    2. 取每個條目在原句中的全部出現區間（允許重疊）。
    3. 一個區間被**名稱不同且較長**的條目區間完全覆蓋即被支配；同名條目區間相同、互不支配。
    4. 條目命中 ⇔ 至少一個區間未被支配。
    5. 系統命中吸收其所屬專案。6. 依目錄序回傳、去重。

    **複雜度（審查 R-01）**：第 3 步不做兩兩比較，而是排序後單趟掃描線，O(S log S)（S＝區間數）。
    等價性：同一個區間只對應一個名稱（`u[s:e]`），名稱不同而區間相同不可能；名稱較長且完全覆蓋
    ⇔ 「起點 ≤ s、終點 ≥ e、且不是同一個區間」。依 (起點遞增, 終點遞減) 排序後，某區間被支配 ⇔
    排在它之前的區間的最大終點 ≥ 它的終點（排在前面者起點皆 ≤ 它；起點相同者終點皆較大）。
    本函式在事件迴圈上執行，不得退回兩兩比較（突變驗證鎖住）。
    """
    u = (utterance or "")[:SCAN_MAX_CHARS].casefold()
    entries = catalog.entries()
    named = [(entry, norm(entry.name)) for entry in entries]
    intervals = set()
    for _entry, name in named:
        if len(name) >= SCAN_MIN_NAME_LEN:
            intervals.update(_occurrences(u, name))

    undominated_names = set()
    max_end = -1
    for s, e in sorted(intervals, key=lambda iv: (iv[0], -iv[1])):
        if max_end < e:
            undominated_names.add(u[s:e])
        if e > max_end:
            max_end = e

    hits = [entry for entry, name in named if len(name) >= SCAN_MIN_NAME_LEN and name in undominated_names]
    return list(_absorb_projects(hits))


def target_label(target: TargetRef) -> str:
    """對象反問的候選標籤（`BR64.11` (a)）。"""
    if target.system_id is None:
        return f"專案：{target.project_name or target.name}"
    return f"{target.name}（專案：{target.project_name}）"


# ---------------------------------------------------------------------------
# 記憶熔斷（NFR13.25／BR67.12；帶入項 5、8、18）
# ---------------------------------------------------------------------------

_CHAIN_DEPTH = 5


def is_transient_memory_failure(exc: Optional[BaseException]) -> bool:
    """沿 `__cause__`／`__context__` 鏈（深度 ≤ 5）找逾時或連線類例外。

    `EmbeddingProviderUnavailable` 本身**不**開熔斷：只有它的鏈上有 httpx 的逾時或網路錯誤
    （`embedding_port.py:617-621` 的 `raise … from exc`）才算。`fulltext` 的設定錯誤、維度不符、
    HTTP 狀態錯誤都是立即失敗，熔斷沒有收益。
    """
    try:  # 與 embedding_port.py 同形：在函式內取 httpx 的型別，不新增模組層依賴
        import httpx

        transient: Tuple[type, ...] = (
            TimeoutError,
            ConnectionError,
            httpx.TimeoutException,
            httpx.NetworkError,
        )
    except ImportError:  # pragma: no cover - httpx 是既有依賴
        transient = (TimeoutError, ConnectionError)
    seen = set()
    frontier = [exc]
    depth = 0
    while frontier and depth <= _CHAIN_DEPTH:
        nxt = []
        for node in frontier:
            if node is None or id(node) in seen:
                continue
            seen.add(id(node))
            if isinstance(node, transient):
                return True
            nxt.extend([node.__cause__, node.__context__])
        frontier = nxt
        depth += 1
    return False


ADMIT_RUN = "run"
ADMIT_PROBE = "probe"
ADMIT_SKIP = "skip"


@dataclass
class BreakerState:
    """記憶熔斷（全域鍵，每行程一個）。純資料、只在事件迴圈執行緒讀寫。

    不變量：`skip` 只在 `open_until` 非 None 時發生；半開期間至多一個探測者；非暫時性例外
    永不使 `open_until` 由 None 轉為非 None；**無在途探測時 `probing` 必為假**——任何未執行
    試探的出口（含執行器滿而 `BUSY_SKIPPED`、被取消）都必須呼叫 `release_probe()`（帶入項 18）。
    """

    open_sec: float = BREAKER_OPEN_SEC
    open_until: Optional[float] = None
    probing: bool = False
    skipped: int = 0

    def admit(self, now: float) -> str:
        if self.open_until is None:
            return ADMIT_RUN
        if now < self.open_until:
            self.skipped += 1
            return ADMIT_SKIP
        if not self.probing:
            self.probing = True
            return ADMIT_PROBE
        self.skipped += 1
        return ADMIT_SKIP

    def release_probe(self) -> None:
        self.probing = False

    def on_success(self) -> Optional[int]:
        """回傳開啟期間的跳過次數（由開轉關時）；原本就關閉則回 None。"""
        was_open = self.open_until is not None
        skipped = self.skipped
        self.open_until = None
        self.probing = False
        self.skipped = 0
        return skipped if was_open else None

    def on_failure(self, exc: BaseException, now: float) -> bool:
        """回傳是否**由關閉轉為開啟**（呼叫端據以記一筆 WARNING）。"""
        self.probing = False
        if not is_transient_memory_failure(exc):
            return False
        opened = self.open_until is None
        self.open_until = now + self.open_sec
        return opened


# ---------------------------------------------------------------------------
# 頻率限制（NFR13.20；帶入項 20、29）
# ---------------------------------------------------------------------------

RATE_OK = None
RATE_CONN = "rate_conn"
RATE_KEY = "rate_key"


class RateLimiter:
    """行程內滑動窗。`now` 由呼叫端傳入（`GatewayTiming.monotonic()`）。

    **視窗的生命週期由時間決定，不由連線決定**（帶入項 20）：每 key 的 `user_message` 窗與
    握手窗在連線關閉時**不刪除**，只在修剪後為空時才移除鍵。每連線窗以 connId 為鍵，連線結束時
    由 `forget_connection` 移除——同一使用者重連得到新的每連線窗，但每 key 的上限不受影響。
    被拒的訊框**不**計入放行窗（否則持續超頻的客戶端會永遠鎖死自己），改計入 `rejected` 窗，
    供「被拒達門檻即關閉」使用（帶入項 29）。
    """

    def __init__(
        self,
        *,
        window_sec: float = RATE_WINDOW_SEC,
        per_key: int = RATE_USER_MESSAGES_PER_KEY,
        per_conn: int = RATE_FRAMES_PER_CONNECTION,
        handshakes_per_key: int = RATE_HANDSHAKES_PER_KEY,
        reject_threshold: int = REJECTED_FRAMES_CLOSE_THRESHOLD,
    ) -> None:
        self.window_sec = window_sec
        self.per_key = per_key
        self.per_conn = per_conn
        self.handshakes_per_key = handshakes_per_key
        self.reject_threshold = reject_threshold
        self._per_key: dict = {}
        self._per_conn: dict = {}
        self._handshakes: dict = {}
        self._rejected: dict = {}

    def _prune(self, table: dict, key: str, now: float) -> deque:
        window = table.get(key)
        if window is None:
            window = deque()
            table[key] = window
        while window and window[0] <= now - self.window_sec:
            window.popleft()
        return window

    def _drop_if_empty(self, table: dict, key: str) -> None:
        window = table.get(key)
        if window is not None and not window:
            del table[key]

    def admit(self, key: str, conn_id: str, is_user_message: bool, now: float) -> Optional[str]:
        """放行回 `None`；被拒回原因（`rate_conn`／`rate_key`）。"""
        conn_window = self._prune(self._per_conn, conn_id, now)
        if len(conn_window) >= self.per_conn:
            return RATE_CONN
        if is_user_message:
            key_window = self._prune(self._per_key, key, now)
            if len(key_window) >= self.per_key:
                return RATE_KEY
            key_window.append(now)
        conn_window.append(now)
        return RATE_OK

    def admit_handshake(self, key: str, now: float) -> bool:
        window = self._prune(self._handshakes, key, now)
        if len(window) >= self.handshakes_per_key:
            return False
        window.append(now)
        return True

    def note_rejected(self, conn_id: str, now: float) -> int:
        """記一則被拒訊框，回傳視窗內被拒總數。"""
        window = self._prune(self._rejected, conn_id, now)
        window.append(now)
        return len(window)

    def forget_connection(self, conn_id: str) -> None:
        self._per_conn.pop(conn_id, None)
        self._rejected.pop(conn_id, None)

    def sweep(self, now: float) -> None:
        """移除已整窗過期的 key（記憶體上界）；未過期的窗原樣保留。"""
        for table in (self._per_key, self._handshakes):
            for key in list(table):
                self._prune(table, key, now)
                self._drop_if_empty(table, key)

    def user_message_count(self, key: str) -> int:
        return len(self._per_key.get(key, ()))


__all__ = [
    "ADMIT_PROBE",
    "ADMIT_RUN",
    "ADMIT_SKIP",
    "BEARER_PREFIX",
    "BREAKER_OPEN_SEC",
    "BreakerState",
    "CATALOG_PROJECT_MAX",
    "ERROR_MESSAGES",
    "FrameTooLarge",
    "GatewayInvalidRequest",
    "MAX_CONNECTIONS_PER_KEY",
    "MAX_FRAME_BYTES",
    "MAX_TOTAL_CONNECTIONS",
    "MatchResult",
    "PENDING_OUTBOUND_MAX",
    "PROTOCOL_NAME",
    "RateLimited",
    "RateLimiter",
    "SubprotocolOffer",
    "TargetCatalog",
    "TargetRef",
    "TurnLedger",
    "close_reason_for_version",
    "error_for",
    "hello_version",
    "is_transient_memory_failure",
    "match_referent",
    "norm",
    "parse_subprotocol_offer",
    "resolve_segment",
    "scan_targets_in_utterance",
    "session_key_for",
    "target_label",
    "user_id_from_session_key",
]
