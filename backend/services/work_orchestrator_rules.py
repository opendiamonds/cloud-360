"""
work_orchestrator_rules.py — `U12 work-orchestrator` 的純函式層

**契約（`work_orchestrator.py` 與測試依賴，請勿變更）**

本模組**零 I/O**：不讀 Redis、不讀 DB、不連外、不 import `httpx`、不記 log。
它是 ADR-0006 property-based testing 的落點（`NFR12.28`；`project.md` 把 agent
routing 列為 PBT hard constraint，而編排是路由結果的落地）。四個純函式與它們的
性質（`test_work_orchestrator_rules.py` 以 `@given` 驗證）：

| 函式 | 性質 |
|---|---|
| `transition(status, event)` | 任何事件序列都不離開終態、不產生五值以外的狀態（`BR54.1`） |
| `plan_waits(capabilities)` | 只有成本或檢視會等待；等待對象是同一次交辦中排在它前面、最近的架構設計；不形成循環（`BR53.1`） |
| `side_effect_on_stop(capability, stage)` | 成本與 `not_dispatched` 恆為 `none`；其餘不為 `none`；`persisting` 為「可能已存回…」（`BR55.1`） |
| `on_dependency_stopped(capability)` | 成本恆為 proceed、檢視恆為 skip（`BR53.4`） |

另有使用者可見文字的**唯一**常數表 `PHRASES`（`BR58.1` 全部句型；`BR58.4`：
失敗原因只能取自本表）與目標圖解析的判定。

`side_effect_on_stop` 是 sideEffect 的**唯一對照**：停掉（`BR55.1`）、逾時
（`BR56.6`）、復原掃描（`BR56.7`）三處都呼叫它（`code-generation-plan.md` §二
第 6、8 項；`reliability-design.md` 第三節）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from services.intent_routing_types import ROUTABLE_CAPABILITIES

# ---------------------------------------------------------------------------
# 封閉集合
# ---------------------------------------------------------------------------

CAP_ARCHITECTURE, CAP_REVIEW, CAP_COST = ROUTABLE_CAPABILITIES

STATUS_PROCESSING = "處理中"
STATUS_WAITING = "等待中"
STATUS_DONE = "完成"
STATUS_FAILED = "失敗"
STATUS_STOPPED = "已停掉"
STATUSES = (STATUS_PROCESSING, STATUS_WAITING, STATUS_DONE, STATUS_FAILED, STATUS_STOPPED)
TERMINAL_STATUSES = frozenset({STATUS_DONE, STATUS_FAILED, STATUS_STOPPED})
ACTIVE_STATUSES = (STATUS_PROCESSING, STATUS_WAITING)

STAGE_NOT_DISPATCHED = "not_dispatched"
STAGE_REQUEST_SENT = "request_sent"
STAGE_PERSISTING = "persisting"
STAGE_RESULT_PERSISTED = "result_persisted"
DISPATCH_STAGES = (
    STAGE_NOT_DISPATCHED,
    STAGE_REQUEST_SENT,
    STAGE_PERSISTING,
    STAGE_RESULT_PERSISTED,
)

SIDE_EFFECT_NONE = "none"
SIDE_EFFECT_UNKNOWN = "unknown"

#: `BR52.2`：能力名稱的固定對照。
CAPABILITY_NAMES = {
    CAP_ARCHITECTURE: "架構設計",
    CAP_REVIEW: "架構檢視",
    CAP_COST: "成本分析",
}

#: `BR56.6`：牆鐘上限（秒）。成本長於 C1 自己的 5 分鐘逾時。
DEADLINE_SECONDS = {
    CAP_ARCHITECTURE: 300,
    CAP_REVIEW: 300,
    CAP_COST: 360,
}

#: `BR53.1`：會等待架構設計的能力。
WAITING_CAPABILITIES = frozenset({CAP_COST, CAP_REVIEW})

# ---------------------------------------------------------------------------
# 狀態機（`BR54.1`；functional-spec 第四節的事件詞彙）
# ---------------------------------------------------------------------------

EV_DEPENDENCY_COMPLETED = "dependency_completed"
EV_DEPENDENCY_STOPPED_PROCEED = "dependency_stopped_proceed"
EV_DEPENDENCY_STOPPED_SKIP = "dependency_stopped_skip"
EV_DEPENDENCY_FAILED = "dependency_failed"
EV_CAPABILITY_COMPLETED = "capability_completed"
EV_CAPABILITY_FAILED = "capability_failed"
EV_USER_CORRECTED = "user_corrected"
EVENTS = (
    EV_DEPENDENCY_COMPLETED,
    EV_DEPENDENCY_STOPPED_PROCEED,
    EV_DEPENDENCY_STOPPED_SKIP,
    EV_DEPENDENCY_FAILED,
    EV_CAPABILITY_COMPLETED,
    EV_CAPABILITY_FAILED,
    EV_USER_CORRECTED,
)

_TRANSITIONS = {
    (STATUS_WAITING, EV_DEPENDENCY_COMPLETED): STATUS_PROCESSING,
    (STATUS_WAITING, EV_DEPENDENCY_STOPPED_PROCEED): STATUS_PROCESSING,
    (STATUS_WAITING, EV_DEPENDENCY_STOPPED_SKIP): STATUS_STOPPED,
    (STATUS_WAITING, EV_DEPENDENCY_FAILED): STATUS_FAILED,
    (STATUS_WAITING, EV_USER_CORRECTED): STATUS_STOPPED,
    (STATUS_PROCESSING, EV_CAPABILITY_COMPLETED): STATUS_DONE,
    (STATUS_PROCESSING, EV_CAPABILITY_FAILED): STATUS_FAILED,
    (STATUS_PROCESSING, EV_USER_CORRECTED): STATUS_STOPPED,
}


class InvalidTransition(ValueError):
    """不在 `BR54.1` 轉換表內的（狀態, 事件）組合。"""

    def __init__(self, status: str, event: str) -> None:
        super().__init__(f"不合法的狀態轉換：{status} --{event}-->")
        self.status = status
        self.event = event


def transition(status: str, event: str) -> str:
    """`BR54.1` 的轉換表。不在表內的組合一律 raise `InvalidTransition`。

    終態（完成／失敗／已停掉）沒有任何向外的轉換。
    """
    try:
        return _TRANSITIONS[(status, event)]
    except KeyError:
        raise InvalidTransition(status, event) from None


# ---------------------------------------------------------------------------
# 等待推導（`BR53.1`）
# ---------------------------------------------------------------------------


def plan_waits(capabilities: Sequence[str]) -> list:
    """每一項回傳它等待的那一項的**索引**（不等待則為 `None`）。

    成本或檢視類工作項，若同一次交辦中在它**之前**有架構設計，等待**最近的**
    那一個；其他組合不等待。被等待者一定是架構設計，而架構設計自己從不等待，
    故不可能形成循環。
    """
    waits: list = []
    last_architecture: Optional[int] = None
    for index, capability in enumerate(capabilities):
        if capability in WAITING_CAPABILITIES and last_architecture is not None:
            waits.append(last_architecture)
        else:
            waits.append(None)
        if capability == CAP_ARCHITECTURE:
            last_architecture = index
    return waits


# ---------------------------------------------------------------------------
# 停掉時的副作用說明（`BR55.1`；唯一對照）
# ---------------------------------------------------------------------------


def diagram_display_name(title: Optional[str], diagram_id: Optional[int]) -> str:
    """圖的顯示名稱：有標題用標題，否則用 `#id`。"""
    if isinstance(title, str) and title.strip():
        return f"〈{title.strip()}〉"
    if diagram_id is not None:
        return f"#{diagram_id}"
    return ""


def side_effect_on_stop(
    capability: str, dispatch_stage: str, *, diagram_name: str = ""
) -> str:
    """停掉（或逾時、逾期掃描）當下，依儲存的 `dispatchStage` 說明是否留下東西。

    - 成本只讀取，恆為 `none`；`not_dispatched` 恆為 `none`。
    - `request_sent` → `unknown`（請求已送出，系統不知道對方是否已留下東西；A3 在
      串流開始時就建立檢視紀錄）。
    - `persisting` → 「可能已存回架構圖〈名稱〉」（存檔請求已送出、無法取消，`BR55.7`）。
    - `result_persisted` → 架構設計「已存回架構圖〈名稱〉」；架構檢視「已建立一份檢視紀錄」。
    """
    if capability == CAP_COST or dispatch_stage == STAGE_NOT_DISPATCHED:
        return SIDE_EFFECT_NONE
    if dispatch_stage == STAGE_REQUEST_SENT:
        return SIDE_EFFECT_UNKNOWN
    if dispatch_stage == STAGE_PERSISTING:
        return PHRASES["side_effect_maybe_persisted"].format(name=diagram_name)
    if dispatch_stage == STAGE_RESULT_PERSISTED:
        if capability == CAP_REVIEW:
            return PHRASES["side_effect_review_created"]
        return PHRASES["side_effect_persisted"].format(name=diagram_name)
    # 未知的 stage 不猜：誠實地說不知道。
    return SIDE_EFFECT_UNKNOWN


# ---------------------------------------------------------------------------
# 被等待者停掉時的處置（`BR53.4`）
# ---------------------------------------------------------------------------

PROCEED = "proceed"
SKIP = "skip"


def on_dependency_stopped(capability: str) -> str:
    """成本（唯讀）照常開始；檢視（會建立紀錄）不執行。

    架構設計從不等待（`plan_waits`），故不會走到這裡；對它保守地回 `skip`——
    不在使用者否定的判讀上自動執行任何會留下東西的能力。
    """
    return PROCEED if capability == CAP_COST else SKIP


def event_for_dependency_terminal(capability: str, dependency_status: str) -> str:
    """被等待者轉為終態時，等待者要套用的事件（`BR53.2`／`BR53.3`／`BR53.4`）。"""
    if dependency_status == STATUS_DONE:
        return EV_DEPENDENCY_COMPLETED
    if dependency_status == STATUS_STOPPED:
        if on_dependency_stopped(capability) == PROCEED:
            return EV_DEPENDENCY_STOPPED_PROCEED
        return EV_DEPENDENCY_STOPPED_SKIP
    return EV_DEPENDENCY_FAILED


# ---------------------------------------------------------------------------
# 目標圖解析（`BR56.1`／`BR56.3`）
# ---------------------------------------------------------------------------

TARGET_DIAGRAM = "diagram"
TARGET_SYSTEM = "system"
TARGET_NONE = "none"


@dataclass(frozen=True)
class TargetPlan:
    kind: str
    diagram_id: Optional[int] = None
    system_id: Optional[int] = None


def plan_target(diagram_id: Optional[int], system_id: Optional[int]) -> TargetPlan:
    """作業對象已指定圖則用它；只指定系統則需列出系統下的圖；否則無目標。"""
    if diagram_id is not None:
        return TargetPlan(TARGET_DIAGRAM, diagram_id=int(diagram_id))
    if system_id is not None:
        return TargetPlan(TARGET_SYSTEM, system_id=int(system_id))
    return TargetPlan(TARGET_NONE)


def pick_single_diagram(diagrams: Sequence) -> tuple:
    """系統下的圖 → `(diagram_id, None)` 或 `(None, 失敗原因鍵)`。

    零張 → `system_no_diagram`；多張 → `system_many_diagrams`（架構設計與檢視需要
    恰一張）。
    """
    if not diagrams:
        return None, "system_no_diagram"
    if len(diagrams) > 1:
        return None, "system_many_diagrams"
    return int(diagrams[0][0]), None


# ---------------------------------------------------------------------------
# 使用者可見文字（`BR58.1`；`BR58.4`：失敗原因只能取自本表）
# ---------------------------------------------------------------------------

COST_PAGE_PATH = "/cost"

PHRASES = {
    # 建立／等待／完成／失敗／停掉／跳過（`BR58.1`、`BR55.5`、`BR53.4`）
    "created": "已交給{capability}處理{target}",
    "waiting": "{label}會在{waiting_label}完成後開始",
    "done": "{label}完成",
    "done_cost": "{label}完成（依既有的估價表與已產生的建議，不會因改圖而重算）",
    "done_review": "檢視完成：整體分數{score}，{count}項發現",
    "failed": "{label}沒有完成：{reason}",
    "stopped": "已停掉{label}。請再說一次你要做什麼。",
    "skipped": "{label}沒有執行：前一項{dependency_label}已停掉",
    # 失敗原因
    "forbidden": "你沒有使用{capability}的權限，或帳號已被停用",
    "unauthorized": "登入已過期，請重新登入後再說一次",
    "dependency_failed": "前一項{dependency_label}沒有完成，這一項沒有執行",
    "no_target": "請先在脈絡列選定架構圖或系統",
    "system_no_diagram": "這個系統下沒有掛上的架構圖，請在脈絡列選定圖",
    "system_many_diagrams": "這個系統下有多張架構圖，請在脈絡列選定要用的那一張",
    "a1_failed": "架構設計失敗",
    "a1_no_xml": "架構設計沒有產出圖",
    "diagram_modified": "這張圖在處理期間被修改過，未覆寫",
    "a3_failed": "架構檢視失敗",
    "a3_incomplete": "架構檢視沒有完成",
    "unavailable": "{capability}暫時無法使用",
    "timeout": "{capability}逾時",
    "expired_on_recovery": "服務重新啟動或逾時，這一項沒有完成",
    "cost_no_estimate": "這張圖尚無估價表，可到成本頁上傳（" + COST_PAGE_PATH + "）",
    "cost_no_advice": "這份估價表還沒有產生建議，可到成本頁產生（{path}）",
    "cost_failed": "成本分析失敗",
    "cost_timeout": "成本分析逾時",
    "cost_not_found": "找不到這份估價表的建議",
    "connection_lost": "與成本服務的連線中斷",
    # sideEffect 說明文字
    "side_effect_maybe_persisted": "可能已存回架構圖{name}",
    "side_effect_persisted": "已存回架構圖{name}",
    "side_effect_review_created": "已建立一份檢視紀錄",
    "side_effect_change_record_missing": "{side_effect}（變更紀錄未寫入）",
}


def cost_page_url(estimate_set_id: Optional[int]) -> str:
    """成本頁路徑；有估價表時帶 `estimate` 查詢參數（`CostPage.tsx` 讀它）。"""
    if estimate_set_id is None:
        return COST_PAGE_PATH
    return f"{COST_PAGE_PATH}?estimate={int(estimate_set_id)}"


def capability_name(capability: str) -> str:
    return CAPABILITY_NAMES.get(capability, capability)


def target_display(
    diagram_id: Optional[int], system_id: Optional[int], project_id: Optional[int]
) -> str:
    """作業對象的顯示名稱。session 只存識別碼，故以 `架構圖 #12` 這類形式呈現。"""
    if diagram_id is not None:
        return f"架構圖 #{diagram_id}"
    if system_id is not None:
        return f"系統 #{system_id}"
    if project_id is not None:
        return f"專案 #{project_id}"
    return ""


def make_label(capability: str, target: str) -> str:
    """`BR52.2`：「〈能力名稱〉：〈作業對象名稱〉」；作業對象未定時省略後半。

    不放入使用者原句。
    """
    name = capability_name(capability)
    return f"{name}：{target}" if target else name


def failure_reason(key: str, **values: str) -> str:
    """失敗原因鍵 → 固定句型（`BR58.4`）。鍵不在表內即 `KeyError`。"""
    return PHRASES[key].format(**values)


def failure_for_status(capability: str, status_code: Optional[int]) -> tuple:
    """HTTP 狀態碼 → `(失敗原因文字, 失敗類別)`（`BR51.3`／`BR51.6`／`BR56.5`）。"""
    name = capability_name(capability)
    if status_code == 401:
        return PHRASES["unauthorized"], "unauthorized"
    if status_code == 403:
        return PHRASES["forbidden"].format(capability=name), "forbidden"
    return PHRASES["unavailable"].format(capability=name), "capability_failed"


__all__ = [
    "ACTIVE_STATUSES",
    "CAPABILITY_NAMES",
    "CAP_ARCHITECTURE",
    "CAP_COST",
    "CAP_REVIEW",
    "COST_PAGE_PATH",
    "DEADLINE_SECONDS",
    "DISPATCH_STAGES",
    "EVENTS",
    "InvalidTransition",
    "PHRASES",
    "PROCEED",
    "SIDE_EFFECT_NONE",
    "SIDE_EFFECT_UNKNOWN",
    "SKIP",
    "STATUSES",
    "TERMINAL_STATUSES",
    "TargetPlan",
    "capability_name",
    "cost_page_url",
    "diagram_display_name",
    "event_for_dependency_terminal",
    "failure_for_status",
    "failure_reason",
    "make_label",
    "on_dependency_stopped",
    "pick_single_diagram",
    "plan_target",
    "plan_waits",
    "side_effect_on_stop",
    "target_display",
    "transition",
]
