"""intent_routing_port.py — `U11 intent-router` 的 **L3**：唯一的出站 I/O 點

**契約（同進程呼叫端依賴，請勿變更）**

本檔是本單元**唯一跨越信任邊界**的一層：使用者的自然語言輸入在這裡離開本平台
（OpenRouter → `typesafe/jev-1.13`）。

硬約束
------

- **不得 `import httpx` 直打**（`SEC-2`）。出站一律經 `langgraph_runtime`
  ——它已經是所有 LLM 路徑的共同入口。
- **每輪最多 1 次模型呼叫**（`NFR3.62`），**重試 0 次**（`NFR3.63`），
  **硬逾時 5 秒**（`NFR3.61`）。三者皆由設定驅動，**不寫死**（`NFR3.64`／
  `BR6.3`）——重試這一項的「可設定」是靠 `openrouter_chat_model` 的
  `max_retries` 參數（預設 0）承載的，而**那個參數是本單元加上去的**：
  在那之前值被寫死，`BRAIN_ROUTER_MAX_RETRIES` 讀了卻無使用端。
- **四種失敗必須在型別上分得開**（`NFR3.74`）：`LlmUnavailable`／
  `LlmBudgetExceeded`／`EmptyCandidates`／`MalformedRouting`。混成一個
  `RoutingError` 會讓「供應商掛了」與「我們的 prompt／schema 壞了」在圖表上
  長得一樣。
- **不建 circuit breaker**（`reliability-design.md` §三）：斷路器狀態必須跨
  行程共享，而本單元對 `U10` 只有唯讀依賴（`BR7.4`），加它會新增一個寫入
  方向。正確落點是共用的出站層。
- **不設 fallback 模型**：換模型是**可替換**（改環境變數 ＋ 重啟）而不是自動
  切換（`NFR10`／`TS-2`）。

`TS-3a`：為什麼不直接用 `openrouter_chat_model` 的現行簽章
--------------------------------------------------------

Jev 的 `supported_parameters` 是**空陣列**（已實測，公開端點），而
`openrouter_chat_model` 原本**無條件**傳 `temperature=0.0`。本檔的
`router_chat_model` 明文傳 `temperature=None` 讓它被省略。該共用層的簽章已改為
`temperature: float | None = 0.0`——**預設不變**，故 A1／A3／C1 三個既有呼叫者
的行為逐位元不變（`D-3` 的驗收條件）。

`[D1]`=A：**扁平** schema，兩層的還原在我方
------------------------------------------

`NFR3.62` 定死每輪最多 1 次呼叫，所以 N 個槽位必須在**同一次**回應裡取得。
形狀是**扁平的 `candidates` 陣列 ＋ `slot` 整數索引**，外加平行的
`slot_labels`——對模型而言是最簡單的 schema（一層物件陣列，沒有巢狀陣列），
而 repo 零結構化輸出前例 ＋ 無金鑰無法先驗 Jev 的 schema 支援度，雙重未知下
選對模型要求最低的形狀。分組與驗證在 `intent_routing_parser`。

`RuntimeAuthError` **刻意不被轉型**
----------------------------------

`OPENROUTER_API_KEY` 缺失是**設定錯誤**，不是供應商不可用。把它轉成
`LlmUnavailable` 會讓一次 misconfiguration 在 `NFR3.74` 的曲線上長得像一次
供應商故障。它原樣向上傳遞（`TS-6` 已把金鑰列為 blocking 前置條件）。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Final, Mapping, Optional, TypedDict

from services.intent_routing_config import RoutingConfig
from services.intent_routing_context import RoutingPrompt
from services.intent_routing_errors import (
    IntentRoutingError,
    LlmBudgetExceeded,
    LlmUnavailable,
    MalformedRouting,
)
from services.intent_routing_types import (
    MAX_CANDIDATES_PER_SLOT,
    MAX_SLOTS,
    MAX_SLOT_INDEX,
    REFERENT_STATES,
    ROUTABLE_CAPABILITIES,
)

logger = logging.getLogger("cloud360.intent_routing")

#: 工具名。模型被要求**必須**呼叫它（`tool_choice`），因為一個回文字而不回
#: 結構的回應對本單元毫無用處。
ROUTING_TOOL_NAME: Final = "emit_routing_decision"

#: 供應商回報「用量上限」的訊息特徵。`402` 是主判準，字樣只是補強——
#: OpenRouter 的錯誤文字會變，狀態碼不會。
_BUDGET_MARKERS: Final = (
    "insufficient",
    "quota",
    "credit",
    "budget",
    "billing",
    "payment required",
)

#: 連線層失敗的類別名特徵（不 import `httpx`／`openai`，故以名稱比對）。
_TRANSPORT_MARKERS: Final = (
    "timeout",
    "connect",
    "connection",
    "readerror",
    "remoteprotocol",
    "apiconnection",
)


class _RouterState(TypedDict, total=False):
    """**具名 TypedDict**，不是 `dict`。

    `StateGraph(dict)` ＋ TypedDict 參數會讓 state 在
    `stream_mode="messages"` 下變成空的（`KeyError`）——那是
    `tests/test_a3_langgraph_migration.py` 釘住的已知 bug，形狀沿用
    `review_agent._compile_review_graph`（`StateGraph(_ReviewState)`）。
    """

    system: str
    user: str
    tool_args: dict


def routing_tool_spec() -> dict:
    """OpenAI 形式的 function schema。

    **寫成函式而不是模組層常數**：`NFR3.67` 禁止行程內的共享可變狀態，而一個
    模組層 `dict` 是可變綁定——呼叫端拿到它之後改一個欄位，下一輪的 schema
    就跟著變，而那不會有任何測試發現。每次呼叫回一份新的。

    上界都寫進 schema（`P-3`／`V-3`）：輸出 token 數是延遲的直接因子，而
    `len(slots)` 沒有上界時一個失控的回應可以宣告 1000 個槽位、`U12` 會據此
    建 1000 個工作項。**schema 的上界是提示，我方的 `V-3`／`V-4` 才是閘門**
    ——模型不保證遵守 schema，所以兩邊都要有。
    """
    return {
        "type": "function",
        "function": {
            "name": ROUTING_TOOL_NAME,
            "description": (
                "回報這句需求被判定成哪幾件事、每件事有哪些互斥的讀法。"
                "不要執行任何事，也不要決定執行順序。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_SLOTS * MAX_CANDIDATES_PER_SLOT,
                        "items": {
                            "type": "object",
                            "properties": {
                                "slot": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": MAX_SLOT_INDEX,
                                    "description": (
                                        "這個候選屬於第幾件事，自 0 連續編號。"
                                        "同一件事的互斥讀法共用同一個 slot。"
                                    ),
                                },
                                "rank": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": MAX_CANDIDATES_PER_SLOT,
                                    "description": "同一個 slot 內的名次，自 1 連續且唯一。",
                                },
                                "capability": {
                                    "type": "string",
                                    "enum": list(ROUTABLE_CAPABILITIES),
                                },
                                "label": {
                                    "type": "string",
                                    "maxLength": 120,
                                    "description": "給使用者看的候選說明。",
                                },
                                "tied_with_next": {
                                    "type": "boolean",
                                    "description": (
                                        "這個候選與下一名之間沒有嚴格優先（並列、"
                                        "分不出哪個更對）。最後一名一律 false。"
                                        "分不出來請填 true。"
                                    ),
                                },
                                "referent_state": {
                                    "type": "string",
                                    "enum": list(REFERENT_STATES),
                                    "description": (
                                        "absent：這句話沒有指涉詞；"
                                        "unresolved：有但無法判定指哪一個；"
                                        "resolved：已解析，referent 填出對象。"
                                    ),
                                },
                                "referent": {
                                    "type": ["string", "null"],
                                    "maxLength": 120,
                                },
                                "score": {
                                    "type": ["number", "null"],
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": (
                                        "0–1 的信心值。若無法給出可互相比較的"
                                        "分數，**全部**填 null，不要只給幾個。"
                                    ),
                                },
                            },
                            "required": [
                                "slot",
                                "rank",
                                "capability",
                                "label",
                                "tied_with_next",
                                "referent_state",
                            ],
                        },
                    },
                    "slot_labels": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_SLOTS,
                        "items": {"type": "string", "maxLength": 80},
                        "description": (
                            "與 slot 等長，每個是那件事的一句人話描述"
                            "（例如「改架構圖」「估成本差額」）。"
                        ),
                    },
                },
                "required": ["candidates", "slot_labels"],
            },
        },
    }


def router_chat_model(config: RoutingConfig) -> Any:
    """路由層專用的 client factory。

    `config` 是**顯式參數**而不是在這裡讀環境變數：設定解析的單一落點是
    `intent_routing_config`，而一個會自己讀 env 的 factory 會讓「這一輪用了
    哪個模型」無法從呼叫端看出來。

    `temperature=None` 是 `TS-3a` 的處置（見模組 docstring）。

    `max_retries` 傳 `config.max_retries`（預設 0）。**它曾經是一個不起作用的
    設定**：值被讀進 `RoutingConfig`、被記進啟動 INFO，然後沒有任何使用端
    ——`openrouter_chat_model` 把 `max_retries=0` 寫死在具名引數上，所以設
    `BRAIN_ROUTER_MAX_RETRIES=3` 不會改變任何行為。`BR6.3` 逐字要求三個數值
    （呼叫次數／重試／用量上限）的機制「必須存在且**可設定**」，而呼叫次數有
    `CallBudget` 這個真機制、重試沒有。接上之後 `BR6.3` 的「可設定」與
    `NFR3.63` 的「值為 0」同時成立，兩者不再互相矛盾。
    """
    from services.langgraph_runtime import openrouter_chat_model

    return openrouter_chat_model(
        model=config.model,
        timeout_seconds=config.timeout_seconds,
        temperature=None,
        max_retries=config.max_retries,
    )


class CallBudget:
    """每輪模型呼叫次數的上限（`NFR3.62`／`BR6.3`）。

    `BR6.3` 逐字要求「每輪的模型呼叫次數、重試次數與用量上限**必須存在且可
    設定**」。單節點圖「剛好只會呼叫一次」**不是**一個機制——它是一個巧合，
    而巧合會在有人加第二個節點的那天安靜地消失。本類別把它變成一個會拋例外
    的閘門。

    **實例層狀態，不是模組層**：每輪一個，用完即棄（`NFR3.67`／`NFR4.70`
    無狀態）。
    """

    def __init__(self, max_calls: int) -> None:
        self._max_calls = max_calls
        self._used = 0

    @property
    def used(self) -> int:
        return self._used

    def consume(self) -> None:
        if self._used >= self._max_calls:
            raise LlmBudgetExceeded(
                f"本輪的模型呼叫次數已達上限 {self._max_calls} 次"
                f"（BRAIN_ROUTER_MAX_CALLS_PER_TURN）"
            )
        self._used += 1


def _status_code(exc: BaseException) -> Optional[int]:
    for attribute in ("status_code", "http_status", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def classify_transport_failure(exc: BaseException) -> BaseException:
    """把一個出站失敗對應到**四種型別之一**，或原樣回傳。

    對應規則（`reliability-design.md` §一）：

    | 觸發 | 型別 |
    |---|---|
    | 供應商回報用量上限（HTTP 402 或訊息含用量字樣） | `LlmBudgetExceeded` |
    | 逾時、連線失敗、429、5xx、其他 4xx | `LlmUnavailable` |
    | 已經是本單元的四種型別之一 | **原樣** |
    | 其他（例如本單元自己的 `TypeError`） | **原樣** |

    **最後一列是刻意的。** 一個 `except Exception: raise LlmUnavailable` 的
    catch-all 會把**我們自己的 bug** 計進「供應商掛了」那條曲線，而分型
    （`NFR3.74`）的全部價值就是分出「是供應商的事」與「是我們的事」。
    代價是 `classify` 可能拋出 `K-10` 的 `raises` 清單之外的例外——那是如實
    記載的取捨：讓呼叫端看到真正的錯，比讓它看到一個錯的分類好。
    """
    if isinstance(exc, IntentRoutingError):
        return exc
    message = str(exc).lower()
    status = _status_code(exc)
    if status == 402 or any(marker in message for marker in _BUDGET_MARKERS):
        return LlmBudgetExceeded(f"路由層模型回報用量上限：{type(exc).__name__}")
    if isinstance(exc, TimeoutError):
        return LlmUnavailable(f"路由層模型逾時：{type(exc).__name__}")
    if status is not None and status >= 400:
        return LlmUnavailable(
            f"路由層模型回應 HTTP {status}：{type(exc).__name__}"
        )
    name = type(exc).__name__.lower()
    if any(marker in name for marker in _TRANSPORT_MARKERS):
        return LlmUnavailable(f"路由層模型連線失敗：{type(exc).__name__}")
    return exc


def _tool_args(message: Any) -> dict:
    """從回應裡取出 tool call 的引數。

    兩種形狀都接受：langchain 已解析的 `.tool_calls`（`args` 是 dict），
    以及原始的 `additional_kwargs["tool_calls"]`（`arguments` 是 JSON 字串）。
    兩者都拿不到時是 `MalformedRouting`——**不是** `LlmUnavailable`：模型回了
    東西，只是形狀不對，而那是我們的 prompt 或 schema 的問題。
    """
    calls = getattr(message, "tool_calls", None) or []
    for call in calls:
        args = call.get("args") if isinstance(call, Mapping) else None
        if isinstance(args, Mapping):
            return dict(args)
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError as exc:
                raise MalformedRouting(f"tool call 的引數不是合法 JSON：{exc}") from exc
            if isinstance(parsed, Mapping):
                return dict(parsed)
    extra = getattr(message, "additional_kwargs", None) or {}
    for call in extra.get("tool_calls", []) or []:
        raw = (call.get("function") or {}).get("arguments")
        if isinstance(raw, Mapping):
            return dict(raw)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise MalformedRouting(f"tool call 的引數不是合法 JSON：{exc}") from exc
            if isinstance(parsed, Mapping):
                return dict(parsed)
    raise MalformedRouting(
        "模型沒有呼叫路由工具（回了文字而不是結構化決策）"
    )


def compile_routing_graph(model: Any) -> Any:
    """單節點 `StateGraph`。

    **即使只有一次呼叫也包在圖裡**，這是既有慣例（`cost_advice_agent` 與
    `review_agent` 皆然）——它讓每條 LLM 路徑有同一個可觀測、可替身、可
    串流的外殼。

    `tool_choice` 釘住本工具：一個回文字而不回結構的回應對本單元毫無用處，
    而 Jev 的 `supports_tool_choice` 四項皆為 `true`（已實測）。
    """
    from langgraph.graph import END, StateGraph

    bound = model.bind_tools([routing_tool_spec()], tool_choice=ROUTING_TOOL_NAME)

    async def classify_node(state: _RouterState) -> _RouterState:
        from langchain_core.messages import HumanMessage, SystemMessage

        message = await bound.ainvoke(
            [
                SystemMessage(content=state["system"]),
                HumanMessage(content=state["user"]),
            ]
        )
        return {**state, "tool_args": _tool_args(message)}

    graph = StateGraph(_RouterState)
    graph.add_node("classify", classify_node)
    graph.set_entry_point("classify")
    graph.add_edge("classify", END)
    return graph.compile()


async def arun_routing(graph: Any, prompt: RoutingPrompt, budget: CallBudget) -> dict:
    """跑一次圖，回**未經驗證**的扁平 payload。

    驗證**不在這裡**：L3 的責任是「把東西拿回來」，`V-1`～`V-5` 是 L4 的
    （`intent_routing_parser`）。把兩者混在一層會讓解析層的 property 需要
    一個 mock 才能測。

    `budget.consume()` 在呼叫**之前**，所以上限為 0 時一次也不會發出去。
    """
    budget.consume()
    try:
        state = await graph.ainvoke({"system": prompt.system, "user": prompt.user})
    except BaseException as exc:  # 外部依賴邊界：分型後向上傳遞，不靜默
        mapped = classify_transport_failure(exc)
        logger.warning(
            "路由層模型呼叫失敗：%s -> %s",
            type(exc).__name__,
            type(mapped).__name__,
        )
        if mapped is exc:
            raise
        raise mapped from exc
    args = state.get("tool_args") if isinstance(state, Mapping) else None
    if not isinstance(args, Mapping):
        raise MalformedRouting("圖執行完成但沒有帶回 tool call 的引數")
    return dict(args)


__all__ = [
    "ROUTING_TOOL_NAME",
    "CallBudget",
    "arun_routing",
    "classify_transport_failure",
    "compile_routing_graph",
    "router_chat_model",
    "routing_tool_spec",
]
