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
from services.intent_routing_context import (
    TARGET_LAYERS,
    format_work_target,
    sanitize_target_name,
)
from services.intent_routing_errors import (
    EmptyCandidates,
    LlmBudgetExceeded,
    LlmUnavailable,
    MalformedRouting,
)
from services.memory_errors import MemoryForbidden
from services.session_errors import SessionBackendUnavailable, SessionMessageTooLong
from services.session_store import DEFAULT_MESSAGE_MAX_CHARS
from services.session_types import PAGE_SCOPES, SEGMENT_SHARED, SHARING_ISOLATED
from services.work_orchestrator import WorkCapacityExceeded, WorkItemNotFound

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
    "forbidden_memory": "你目前沒有權限使用大腦的記憶，這一輪已停止",
    "target_not_found": "找不到這個作業對象",
    "work_item_not_found": "找不到這個工作項",
    # 合併前必修第 18 項（`U12` 的進行中上限）：固定字串，數字與
    # `work_orchestrator_rules.MAX_ACTIVE_WORK_ITEMS` 一致（測試鎖住兩者）。
    # 句子只陳述上限與「這次會超過」：預檢在「現有＋本批 > 上限」時觸發，現有
    # 進行中可能少於 5（例如 4 ＋ 2），不得說成「已達 5 項」（U12 審查 review-01 R-03）。
    "work_capacity": "同時進行中的工作最多 5 項，這次交辦會超過上限，請等其中一項完成後再交辦。",
    "format": "訊息格式不正確",
    "rate": "訊息太頻繁，請稍候再送出",
    "internal": "處理時發生錯誤，請再說一次",
    "empty": "這一輪沒有產生任何回覆，請再說一次",
    # build-and-test 第二輪（語意記憶寫入）：`EMBEDDING_PROVIDER=fulltext` 之下記憶層沒有向量 Port，
    # 寫入必然失敗（`MemoryFacade._require_port`）。照實告知，不假裝成功。
    "memory_fulltext": "目前的記憶設定（EMBEDDING_PROVIDER=fulltext）無法寫入語意記憶，這句話沒有被記住。請管理員改用支援向量的設定後再試。",
    "memory_write_failed": "這次沒能寫入記憶，這句話沒有被記住，請稍後再說一次。",
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
    # 合併前必修第 13 項：記憶授權拒絕以既有的授權類代碼結束本輪（不新增代碼）。
    if isinstance(exc, MemoryForbidden):
        return CODE_UNAUTHORIZED, ERROR_MESSAGES["forbidden_memory"]
    if isinstance(exc, HierarchyNotFound):
        return CODE_INVALID, ERROR_MESSAGES["target_not_found"]
    if isinstance(exc, WorkItemNotFound):
        return CODE_INVALID, ERROR_MESSAGES["work_item_not_found"]
    # 合併前必修第 18 項：沿用既有代碼 INVALID_REQUEST，**不改 WS 契約**的 code 列舉。
    if isinstance(exc, WorkCapacityExceeded):
        return CODE_INVALID, ERROR_MESSAGES["work_capacity"]
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


# ---------------------------------------------------------------------------
# 指涉詞是否就是「目前作業對象」（build-and-test 本機驗證 F2，2026-11-12）
#
# 缺陷：路由脈絡原本以「專案 #1／系統 #1」描述作業對象，模型把它抄成 `referent`，
# `match_referent` 以名稱精確比對比不到，回「找不到名為『系統 #1』」——作業對象明明已選定。
# 修法分兩半：prompt 改寫名稱（`intent_routing_context.format_work_target`），以及本段：
# 指涉詞**指的就是目前作業對象**時，依目前作業對象交辦。
#
# **界線（不得放寬成「比不到就退回目前對象」）**：只有指涉詞等於目前對象的某一種表達
# 形式（名稱、prompt 裡的寫法、舊的 `#id` 代號、或指示詞）才算；真正指名了另一個不存在的
# 對象，仍走 `match_referent` → 找不到。一律退回會把指名錯誤靜默吞掉，交辦到使用者沒說的對象。
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CurrentTarget:
    """該段目前的作業對象：三層識別碼與（閘道以 `describe_work_target` 取得的）名稱。"""

    project_id: Optional[int] = None
    system_id: Optional[int] = None
    diagram_id: Optional[int] = None
    project_name: Optional[str] = None
    system_name: Optional[str] = None
    diagram_name: Optional[str] = None

    @property
    def is_set(self) -> bool:
        return not (self.project_id is None and self.system_id is None and self.diagram_id is None)

    def ids(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        return (self.project_id, self.system_id, self.diagram_id)

    def names(self) -> dict:
        return {
            "projectName": self.project_name,
            "systemName": self.system_name,
            "diagramName": self.diagram_name,
        }


#: 指示詞：指的就是「目前這一個」。只在目前對象已選定時生效。
DEICTIC_REFERENTS = (
    "這", "這個", "它", "此", "該", "這張", "這張圖", "這張架構圖", "這個架構圖", "這份架構圖",
    "該架構圖", "這個系統", "該系統", "這個專案", "該專案", "目前的系統", "目前系統",
    "目前的專案", "目前專案", "目前的架構圖", "目前架構圖", "目前的對象", "目前對象",
    "作業對象", "目前的作業對象", "目前作業對象", "當前作業對象", "當前的作業對象",
    "現在的作業對象", "選定的對象", "目前選定的對象",
    # build-and-test 第三輪（AC6.1.1）：「那」系列。第二輪說「把那張圖的資料庫換成 Aurora」時模型可能把
    # 「那張圖」填成 referent；缺這一組時它落到目錄比對而回「找不到」，AC6.1.1 不成立。
    "那", "那個", "那張", "那張圖", "那張架構圖", "那個架構圖", "那份架構圖", "那個系統", "那個專案",
)

_CURRENT_PREFIX = re.compile(r"^(?:目前|當前|現在|選定)?(?:的)?(?:作業)?對象[:：]?")
_CURRENT_SUFFIX = re.compile(r"(?:底下|之下|下面|裡面|裡|中|下)?(?:的)?(?:所有)?(?:架構圖|圖)$")
_WRAPPING_QUOTES = "「」『』\"'`“”‘’"


def current_target_key(raw: Optional[str]) -> str:
    """「是否指目前對象」判定用的寬鬆正規化：casefold、去全部空白、統一全形符號、去外層引號。

    只用在本段的判定，**不改** `norm`（`match_referent` 的精確比對，`NFR13.28`）。
    """
    s = (raw or "").casefold()
    s = "".join(s.split())
    s = s.replace("＃", "#").replace("/", "／").replace(":", "：")
    return s.strip(_WRAPPING_QUOTES)


def current_target_expressions(current: CurrentTarget) -> frozenset:
    """目前作業對象的全部表達形式（已正規化）。目前對象未選定 → 空集合。"""
    if not current.is_set:
        return frozenset()
    out = set()
    hint = format_work_target(current.ids(), current.names())
    if hint:
        out.add(hint)
    legacy = []
    for (label, key), value in zip(TARGET_LAYERS, current.ids()):
        if value is None:
            continue
        code = f"{label}#{value}"
        legacy.append(code)
        out.add(code)
        raw = current.names().get(key)
        for name in (raw, sanitize_target_name(raw)):
            if name and name.strip():
                out.add(name)
                out.add(f"{label}「{name}」")
                out.add(f"{label}{name}")
    if legacy:
        out.add("／".join(legacy))
    keyed = {current_target_key(x) for x in out}
    keyed.update(current_target_key(x) for x in DEICTIC_REFERENTS)
    keyed.discard("")
    return frozenset(keyed)


def refers_to_current_target(referent: Optional[str], current: CurrentTarget) -> bool:
    """指涉詞是否就是目前作業對象。目前對象未選定時一律 False（照舊走目錄比對）。

    比對三個候選：整句、去掉「目前作業對象：」前綴、再去掉「下的架構圖」這類後綴。
    前綴去掉後為空（整句就是「目前作業對象」）也算。
    """
    if not current.is_set:
        return False
    key = current_target_key(referent)
    if not key:
        return False
    no_prefix = _CURRENT_PREFIX.sub("", key, count=1)
    if not no_prefix:
        return True
    stripped = _CURRENT_SUFFIX.sub("", no_prefix, count=1)
    if no_prefix != key and not stripped:  # 「目前的對象下的架構圖」：前綴＋後綴，中間沒有別的
        return True
    # 去掉前後綴後再去一次外層引號：「系統「A」下的架構圖」去後綴後才露出結尾的「」」。
    candidates = {c.strip(_WRAPPING_QUOTES) for c in (key, no_prefix, stripped)}
    candidates.discard("")
    return bool(candidates & current_target_expressions(current))


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


# ---------------------------------------------------------------------------
# 從對話寫入語意記憶（build-and-test 第二輪，2026-11-12）
#
# **本階段新增、已核可 scope 尚未涵蓋的寫入路徑**：FR4.1 要三種記憶，但 OQ-N3 只落地
# 情節記憶的寫入端，語意記憶至今沒有任何寫入者。2026-11-12 使用者在本機驗證後選定
# 「本輪補對話寫入語意記憶」。回補項：requirements 補語意記憶寫入 FR、user-stories 補 AC。
# 程序記憶本輪不做。
#
# 辨識以**決定性規則**而非 LLM 分類（`project.md`：同一行為可由程式或模型做時選程式那邊，
# 可驗證性才是判準）：只有明確的「記住／記下」句首才進入本路徑，其餘句子照舊走 `U11`
# 路由，既有能力路由完全不受影響。寫入前一律經使用者確認（反問一個候選）。
# ---------------------------------------------------------------------------

#: 確認反問唯一候選的 id。沿用既有 `clarify`（kind=intent）訊息形狀，**不新增訊息型別**。
MEMORY_CONFIRM_CANDIDATE_ID = "memory-confirm"
#: 確認反問候選的 capability 欄（`ClarifyCandidate.capability` 為自由字串）。前端不讀它。
MEMORY_CONFIRM_CAPABILITY = "memory"
#: 從對話寫入的單則語意記憶上限（字元，code point）。遠小於記憶層 HTTP 上限 4000
#: （`memory_router.MEMORY_CONTENT_MAX_CHARS`，測試鎖住「不超過」）：語意記憶是一句偏好或
#: 慣用說法，且全文會出現在確認反問的候選說明裡。
SEMANTIC_MEMORY_MAX_CHARS = 500

_REMEMBER_ZH = re.compile(
    r"^\s*(?:請|麻煩)?\s*(?:你)?\s*(?:幫我|替我)?\s*(?:記住|記下來|記下|記一下)(?:一下)?"
)
_REMEMBER_EN = re.compile(r"^\s*(?:please\s+)?remember(?:\s*:|\s+that\b)", re.IGNORECASE)
#: 「記住」之後緊接這些字代表問句或回顧（「你記住了嗎」「記住過」），不是要求記住。
_NOT_A_REQUEST = re.compile(r"^(?:了|過|嗎|沒|没)")
_LEADING_PUNCT = re.compile(r"^[\s：:，,、。．.;；\-—]+")
_QUOTES = "「」『』\"'“”"


def parse_remember_request(utterance: str) -> Optional[str]:
    """使用者要大腦記住某句話時回該句內容（可能為空字串）；否則回 `None`。

    只認句首的明確動詞：中文「（請）（幫我）記住／記下／記一下」，英文
    「remember:」「remember that」。內容去掉前導標點與成對的外層引號。
    """
    if not utterance:
        return None
    match = _REMEMBER_ZH.match(utterance) or _REMEMBER_EN.match(utterance)
    if match is None:
        return None
    rest = utterance[match.end():]
    if _NOT_A_REQUEST.match(rest.lstrip()):
        return None
    content = _LEADING_PUNCT.sub("", rest).strip()
    while len(content) >= 2 and content[0] in _QUOTES and content[-1] in _QUOTES:
        content = content[1:-1].strip()
    return content


# 疑似憑證：關鍵字後緊接賦值（「密碼是…」「api key: …」）。只出現關鍵字不算——
# 「我們偏好用 Secrets Manager 管理密碼」是一句合法偏好。
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?:密碼|口令|密鑰|金鑰|私鑰|憑證|password|passwd|pwd|passphrase|token|api[\s_-]?key|apikey|"
    r"secret|credential|access[\s_-]?key)"
    r"\s*(?:是|為|為：|=|:|：)\s*\S",
    re.IGNORECASE,
)
_CREDENTIAL_SHAPES = (
    re.compile(r"-{5}BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|pk|rk|ghp|gho|ghs|github_pat|xox[abprs])[-_][A-Za-z0-9_\-]{16,}"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\."),
)
#: 長度 ≥ 32、同時含英文字母與數字的連續字元：隨機金鑰的形狀（ARN、網址以 `:`／`/` 斷開，不會命中）。
_OPAQUE_RUN = re.compile(r"[A-Za-z0-9+_=\-]{32,}")
_PERSONAL_SHAPES = (
    re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"),  # 電子郵件
    re.compile(r"\b[A-Z][12]\d{8}\b"),  # 身分證字號
    re.compile(r"(?<!\d)09\d{2}-?\d{3}-?\d{3}(?!\d)"),  # 手機號碼
    re.compile(r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)"),  # 卡號形狀的長數字
)

MEMORY_REJECT_EMPTY = "empty"
MEMORY_REJECT_TOO_LONG = "too_long"
MEMORY_REJECT_CREDENTIAL = "credential"
MEMORY_REJECT_PERSONAL = "personal"

#: 拒寫時給使用者的回覆（固定字串；不引用使用者原文）。
MEMORY_REJECT_REPLIES: Mapping[str, str] = {
    MEMORY_REJECT_EMPTY: "要我記住什麼呢？請在「記住：」後面寫出要記住的內容。",
    MEMORY_REJECT_TOO_LONG: f"要記住的內容太長（上限 {SEMANTIC_MEMORY_MAX_CHARS} 字），請精簡成一句後再說一次。",
    MEMORY_REJECT_CREDENTIAL: "這句話看起來含有密碼、金鑰或 token，為了安全我不會記住它。請拿掉這些內容後再說一次。",
    MEMORY_REJECT_PERSONAL: "這句話看起來含有個人資料（例如電子郵件、電話或證號），為了安全我不會記住它。請拿掉這些內容後再說一次。",
}


def _looks_opaque(run: str) -> bool:
    return any(c.isalpha() for c in run) and any(c.isdigit() for c in run)


def memory_content_rejection(content: str) -> Optional[str]:
    """要寫入語意記憶的內容不可寫入時回理由代碼（`MEMORY_REJECT_*`）；可寫入回 `None`。

    依序：空白 → 長度 → 疑似憑證 → 疑似個資。判定是最小、可測的樣式比對，
    寧可多擋（使用者可改寫後再說一次）也不把秘密寫進可被檢索的記憶。
    """
    if content is None or not content.strip():
        return MEMORY_REJECT_EMPTY
    if len(content) > SEMANTIC_MEMORY_MAX_CHARS:
        return MEMORY_REJECT_TOO_LONG
    if _CREDENTIAL_ASSIGNMENT.search(content) or any(p.search(content) for p in _CREDENTIAL_SHAPES):
        return MEMORY_REJECT_CREDENTIAL
    if any(_looks_opaque(m.group(0)) for m in _OPAQUE_RUN.finditer(content)):
        return MEMORY_REJECT_CREDENTIAL
    if any(p.search(content) for p in _PERSONAL_SHAPES):
        return MEMORY_REJECT_PERSONAL
    return None


def memory_confirm_label(content: str) -> str:
    """確認反問唯一候選的說明：完整呈現擬寫入的內容（使用者確認的就是這句）。"""
    return f"記住這句話（語意記憶，只有你看得到）：「{content}」"


def memory_saved_reply(content: str) -> str:
    return f"好，我記住了：「{content}」。之後判讀你的需求時會參考它；你可以在「我的記憶」的語意記憶區查看或刪除。"


__all__ = [
    "MEMORY_CONFIRM_CANDIDATE_ID",
    "MEMORY_CONFIRM_CAPABILITY",
    "MEMORY_REJECT_REPLIES",
    "SEMANTIC_MEMORY_MAX_CHARS",
    "memory_confirm_label",
    "memory_content_rejection",
    "memory_saved_reply",
    "parse_remember_request",
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
