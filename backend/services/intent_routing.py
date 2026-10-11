"""intent_routing.py — `U11 intent-router` 的編排層（L0 讀取 ＋ L1 guard ＋ L1 編排）

**契約（同進程呼叫端依賴，請勿變更）**

`K-10` 的唯一公開方法：

    IntentRouter.classify(principal, session: BrainSession, text: str) -> IntentDecision
    form: async        raises: [LlmUnavailable, LlmBudgetExceeded]

消費端**只有** `U13 brain-gateway`（`K-10.consumers` 逐字）。

六層分解中本檔承擔哪幾層（`nfr-design/logical-components.md` §一）
----------------------------------------------------------------

| 層 | 落點 | 純度 |
|---|---|---|
| L1 guard | 本檔（`prompt_guard` 前置） | 既有純函式 |
| **L0 fetch** | **本檔**——**本單元唯一的讀取 I/O 點** | **不純** |
| L2 context-builder | `intent_routing_context.py` | 純函式 |
| L3 model-port | `intent_routing_port.py`——唯一的出站 I/O 點 | 不純 |
| L4 parser | `intent_routing_parser.py` | 純函式 |
| L5 predicate | `intent_routing_predicate.py` | 純函式（**PBT 落點**） |

**L0 與 L2 分離是刻意的**：取資料的 I/O 放在 L2 之外（本檔先取好再傳進去），
使 `BR6.1`「最少上下文」可以被一個**不需要 mock 的測試**驗證。那正是本單元
測試策略的基礎（`logical-components.md` §二 的表格）。

安全邊界（`SEC-1`／`SEC-2`／`NFR6.60`／`BR7.x`）
----------------------------------------------

- **不自取身分**：`principal` 一律由參數傳入。本檔**不得** import
  `fastapi`／`starlette` 的請求型別、`services.auth.get_current_user`，
  也不得用 context-local 身分來源（`SEC-1`）。
- **不暴露端點**：不建立 `APIRouter`、不被 `main.py` `include_router`
  （`SEC-2`）。出站呼叫一律經 `intent_routing_port`，它再經
  `langgraph_runtime`——本檔與 port **都不得** `import httpx` 直打。
- **不判權**：讀記憶只經 `K-08` 的 `MemoryFacade`，授權由它承擔
  （`BR7.1`／`NFR6.60`）。本檔不 import `memory_service`、不 import 任何
  DB session 型別。
- **不建立工作項、不決定狀態、不呼叫既有能力**（`BR7.3`）——那是
  `U12 work-orchestrator`。本檔只回 `IntentDecision`。
- **對 `SessionContext` 唯讀**（`BR7.4`）：本檔**不 import `session_store`**，
  因此 `set_work_target`／`append_message`／`set_sharing_mode`／`touch`
  四個寫入方法在這裡**無從被呼叫**。拿不到比記得不要呼叫可靠。

`session` 為什麼是參數而不是本檔去 `load`
----------------------------------------

`K-10` 把 `classify` 的第二個參數固定為 `session: BrainSession`——session
**已經由 `U13` 載入並傳進來**。故本檔對 `U10` 的讀取是「讀傳進來的物件」
而非一次 Redis 往返：

- 這是 `BR7.4` 的最強形式：`SessionStore.load` 會順帶續期 TTL（`BR1.3`），
  在本單元再呼叫一次等於多一個副作用，而且是多餘的。
- `logical-components.md` §三 逐字「`U10` 不可用……**本單元不處理**——它向上
  傳遞，由 `U13` 終止該輪」：session 由 `U13` 載入時，`SessionBackendUnavailable`
  在 `classify` 被呼叫之前就已拋出，該句由構造成立。
- 本檔**不得**對讀取 session 的程式碼加 `try/except`——那會把「取不到脈絡」
  變成一個看起來正常的結果，而 `BR8.2` 的主軸是把「不知道」如實往上傳。

讀哪一段（`BR5.1` 的「該段」）
-----------------------------

`classify` 的簽章**沒有段識別參數**。本單元服務的是**統一入口頁**，而
`U10` 的段規則逐字「入口頁恆讀共享段」，故本檔讀 `SEGMENT_SHARED`。
段識別取自 `session_types` 的封閉集合，**不在本檔另抄一份字串**。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Final, Optional, Sequence, Tuple

from services.intent_routing_config import RoutingConfig, resolve_routing_config
from services.intent_routing_context import RoutingPrompt, build_routing_prompt
from services.intent_routing_errors import PlatformSelfModificationRefused
from services.intent_routing_parser import parse_classification
from services.intent_routing_port import (
    CallBudget,
    arun_routing,
    compile_routing_graph,
    router_chat_model,
)
from services.intent_routing_predicate import can_dispatch, decide
from services.intent_routing_types import (
    PROMPT_GUARD_HIT,
    ClassificationResult,
    IntentDecision,
    RoutingObservation,
)
from services.prompt_guard import is_platform_self_modification
from services.session_types import SEGMENT_SHARED

logger = logging.getLogger("cloud360.intent_routing")

#: `NFR7.62`／`BR5.5.logic_executable`：呼叫 `MemoryFacade.search` 時的 `kinds`。
#:
#: **模組層常數，不是預設參數值**——預設值可以被覆寫，常數不行。呼叫端無從傳入
#: `episodic`。`AC6.1.3`（獨立段無法解析指向共享產出的指涉詞）有**兩個**違反
#: 入口：讀錯段（由 `U10` 的段隔離結構性擋下）與**查記憶**（記憶不分段，它是
#: 長期、跨 session 的）。本常數擋的是第二個。
#:
#: **這是現行防護，不是前置護欄**：`memory_router.py` 的
#: `POST /api/memory/records` 已可寫入 `kind=episodic`，使用者今天就能建一筆
#: 情節記憶（`security-requirements.md` §三 的實讀查證）。
_REFERENT_MEMORY_KINDS: Final[Tuple[str, ...]] = ("semantic", "procedure")

#: `scalability-design.md` §五：`limit` 刻意小——指涉詞解析需要的是最相關的
#: 幾筆術語，不是全文檢索。每輪 1 次 `search`，故 `U8` 的讀取 QPS ≈ 入口頁
#: 送出 QPS。
_MEMORY_SEARCH_LIMIT: Final = 5

#: `BR6.1`／`NFR9.60`／`NFR9.61`：帶進 prompt 的歷程則數上界。歷程上限是
#: **每段 200 則**，而每輪成本與歷程長度線性相關——整段附上會逼近 Jev 的
#: context 32000 上界。這個 K 刻意遠小於 200。
#:
#: 它同時是**資料外送最小化**（ADR-0006 encryption 面）：附上整段對話等於把
#: 更多個人內容送出平台，而 OpenRouter 在信任邊界外。
_RECENT_MESSAGE_LIMIT: Final = 6

#: 單筆記憶帶進 prompt 的字元上界。理由同上：長度即外送量與成本。
_MEMORY_NOTE_MAX_CHARS: Final = 240


@dataclass(frozen=True)
class RoutingContext:
    """L0 取得的全部資料。**L2 的唯一輸入**（它不自己做 I/O）。

    `work_target_hint` 是**三層識別的文字呈現**而不是人話名稱。差別與其理由
    見 `IntentRouter` 的 docstring「已知缺口」段。

    `memory_degraded` 是 `D-1` 的唯一保險：`U8` 不可用時本單元**降級**
    （不帶記憶繼續）而非失敗，而降級**必須可被觀測**，否則「記憶永遠取不到」
    是一個無聲的長期降級。
    """

    work_target_hint: Optional[str]
    recent_messages: Tuple[Tuple[str, str], ...]
    memory_notes: Tuple[str, ...]
    memory_degraded: bool


def guard_hits(text: str) -> bool:
    """L1：`BR1.1`——在呼叫任何 LLM **之前**先過既有的 `prompt_guard`。

    命中時**不呼叫任何 LLM**（`BR1.2`）。這條規則的價值正在於省下那次呼叫
    與其風險，所以順序本身就是需求：先呼叫模型再檢查，等於已經把惡意輸入
    送進去了。
    """
    return is_platform_self_modification(text)


def _describe_work_target(segment: Any) -> Optional[str]:
    """把該段的三層作業對象寫成一行文字。

    `ConversationSegment` 的三個欄位**允許部分非空**（`U10` 的 `EC7`，含
    「只有 `diagramId`」這種組合），故本函式**不推導、不補齊、不拒絕**，
    只如實呈現非空的那幾層。
    """
    if segment is None:
        return None
    parts = []
    for label, value in (
        ("專案", getattr(segment, "project_id", None)),
        ("系統", getattr(segment, "system_id", None)),
        ("架構圖", getattr(segment, "diagram_id", None)),
    ):
        if value is not None:
            parts.append(f"{label} #{value}")
    return "／".join(parts) if parts else None


def _recent_messages(segment: Any, limit: int) -> Tuple[Tuple[str, str], ...]:
    """該段歷程的**最後 `limit` 則**（`BR6.1`）。

    截斷在**本層**而不是只在 L2，是為了讓 L2 連「完整歷程」都拿不到——
    `NFR9.60` 的設計原則是「不給它，它就送不出去」。L2 另有自己的上界，
    兩層都有不是重複而是縱深。
    """
    if segment is None:
        return ()
    messages: Sequence[Any] = getattr(segment, "messages", ()) or ()
    tail = list(messages)[-limit:] if limit > 0 else []
    return tuple(
        (str(getattr(m, "role", "") or ""), str(getattr(m, "text", "") or ""))
        for m in tail
    )


def _memory_notes(
    memory_facade: Any,
    principal: Any,
    text: str,
    limit: int,
) -> Tuple[Tuple[str, ...], bool]:
    """經 `K-08` 的 `MemoryFacade` 讀語意／程序記憶。回 `(notes, degraded)`。

    **`U8` 不可用時降級而非失敗（`D-1`）**，這是本單元唯一一處偏離「一律大聲
    失敗」的判斷，理由具體：記憶在本單元的用途是**理解偏好與術語**
    （`BR5.5`），不是解析 `referent` 的必要輸入——`BR5.1` 逐字說指涉詞解析讀
    的是「`SessionContext` 的當前作業對象與該段歷程」。因為拿不到術語解釋就讓
    整輪失敗，是用使用者的體驗去換一個不存在的正確性。

    `try/except` 用在外部依賴邊界且**必須降級或記 log，不得靜默**
    （`team.md` 的錯誤處理形狀）。

    **殘留風險，如實記載**：記憶降級**可能改變分類結果**而不只是少一點輔助
    ——模型在實際生成 `capability`／`referent` 時無法把「理解術語」與「決定
    指涉」切開。本站不發明一個功能性保險（`OQ-10` 未定案前，任何依賴分數的
    保險都可能是走不到的分支），而是讓 `memory_degraded` 使它**事後可歸因**。
    """
    if memory_facade is None:
        return (), True
    try:
        hits = memory_facade.search(
            principal,
            text,
            kinds=_REFERENT_MEMORY_KINDS,
            limit=limit,
        )
    except Exception as exc:  # 外部依賴邊界：降級並記 log，不靜默
        logger.warning(
            "記憶檢索失敗，本輪降級為不帶記憶繼續分類（D-1）：%s",
            type(exc).__name__,
        )
        return (), True
    notes = []
    for hit in hits or []:
        content = str(getattr(hit, "content", "") or "").strip()
        if content:
            notes.append(content[:_MEMORY_NOTE_MAX_CHARS])
    return tuple(notes), False


def fetch_routing_context(
    *,
    principal: Any,
    session: Any,
    text: str,
    memory_facade: Any,
    segment_id: str = SEGMENT_SHARED,
    recent_message_limit: int = _RECENT_MESSAGE_LIMIT,
    memory_limit: int = _MEMORY_SEARCH_LIMIT,
) -> RoutingContext:
    """**L0**：本單元唯一的讀取 I/O 點。

    兩個來源的失敗**待遇不同**，而這個差別是設計決定（`D-1`）：

    | 來源 | 不可用時 | 理由 |
    |---|---|---|
    | `U10`（session） | **失敗**（例外原樣向上傳遞） | 沒有該段歷程與作業對象，指涉詞解析不可能正確。猜測＝`BR8.2` 要防的那件事 |
    | `U8`（記憶） | **降級**並記一個觀測事件 | 它是加分項（`BR5.5`） |

    注意 session 這一側**刻意沒有 `try/except`**：它是傳進來的物件，讀它若
    失敗（例如 `U13` 傳進一個壞掉的代理物件），那是真的壞了。
    """
    segment = session.segment(segment_id) if session is not None else None
    notes, degraded = _memory_notes(memory_facade, principal, text, memory_limit)
    return RoutingContext(
        work_target_hint=_describe_work_target(segment),
        recent_messages=_recent_messages(segment, recent_message_limit),
        memory_notes=notes,
        memory_degraded=degraded,
    )


def log_routing_observation(observation: RoutingObservation) -> None:
    """預設的觀測落點：一行結構化 log。

    **欄位逐一列出，不是 `observation` 整個丟給 logger**（`SEC-3`／`SEC-5`）。
    `RoutingObservation` 是 frozen dataclass，而 dataclass 的 `__repr__` 會印出
    全部欄位——今天那些欄位都在白名單上，但「把物件丟給 logger」這個形狀會讓
    下一個人加欄位時自動把它記出去。這與 `U10` 的
    `session_types` 檔頭同一條紀律（「呼叫端不得把本檔的任何物件交給 logger」）。

    本 repo 為 public、Actions log 公開可讀——**一次意外 echo 即等同公開發布**。

    告警：**本 intent 沒有任何告警通道**（`U10` 的 `OPEN-N10-4` 已查證並
    登記）。在它關閉之前，這些指標的實際消費方式是人工查詢結構化日誌。
    本檔不自行發明一個——那會是憑推論加的基礎設施。
    """
    logger.info(
        "intent routing turn=%s slots=%s scores_available=%s can_single_out=%s "
        "elapsed_ms=%s error_kind=%s memory_degraded=%s caps=%s",
        observation.turn_id,
        observation.slot_count,
        observation.scores_available,
        observation.can_single_out,
        observation.elapsed_ms,
        observation.error_kind,
        observation.memory_degraded,
        observation.capability_ranks,
    )


def _capability_ranks(result: Optional[ClassificationResult]) -> Tuple:
    """`(capability, rank)` 的扁平序列。**不含 `label`、不含 `referent`。**"""
    if result is None:
        return ()
    return tuple(
        (candidate.capability, candidate.rank)
        for slot in result.slots
        for candidate in slot.candidates
    )


class IntentRouter:
    """`K-10` 的唯一公開型別。**一個行程一個實例**（由 `U13` 建立）。

    依賴以參數注入，**不以模組層變數持有**（`NFR3.67`／`NFR4.70`）：

    | 參數 | 用途 |
    |---|---|
    | `memory_facade` | `K-08` 的 `MemoryFacade`（唯讀）。`None` 時視為記憶降級 |
    | `config` | `RoutingConfig`；省略則於建構時解析環境變數（門檻缺值即拋） |
    | `model_factory` | 預設 `router_chat_model`；測試以替身取代 |
    | `graph_builder` | 預設 `compile_routing_graph` |
    | `observer` | 預設 `log_routing_observation` |

    **`P-4`（連線重用）的落法是實例層快取，不是模組層。**
    `performance-design.md` §二 的 P-4 要求 HTTP client「建立一次並重用，不是
    每輪新建」，理由是每輪一次 TLS 握手會直接吃掉 800 ms 預算的一部分。
    該檔把它寫成「模組層的 factory」，而本站改放在**實例**上：一個行程一個
    `IntentRouter`，效果相同（握手只付一次），但**完全不產生模組層狀態**
    ——`NFR3.67` 的結構斷言因此不需要為它開一個白名單例外。
    快取在第一次 `classify` 時建立；事件迴圈是單執行緒的，故不需要鎖
    （`threading.Lock` 在 asyncio 的 `await` 邊界上只會給出錯誤的安全感）。
    """

    def __init__(
        self,
        *,
        memory_facade: Any = None,
        config: Optional[RoutingConfig] = None,
        model_factory: Optional[Callable[[RoutingConfig], Any]] = None,
        graph_builder: Optional[Callable[[Any], Any]] = None,
        observer: Optional[Callable[[RoutingObservation], None]] = None,
        segment_id: str = SEGMENT_SHARED,
    ) -> None:
        self._memory_facade = memory_facade
        self._config = config if config is not None else resolve_routing_config()
        self._model_factory = model_factory or router_chat_model
        self._graph_builder = graph_builder or compile_routing_graph
        self._observer = observer or log_routing_observation
        self._segment_id = segment_id
        self._graph: Any = None

    @property
    def config(self) -> RoutingConfig:
        return self._config

    def _observe(self, observation: RoutingObservation) -> None:
        """寫出一筆觀測，**並且吞掉它自己的失敗**。

        `observer` 由建構式注入，可以是任何東西。原本兩處都是
        `self._observer(...)` 直呼，而失敗路徑的那一處位在 `except BaseException`
        區塊內、`raise` 之前——observer 自己拋出就會把原始的
        `MalformedRouting`／`LlmUnavailable` **換掉**，`NFR3.74` 的分型在那一輪
        整個失真（一次 schema 壞掉會被記成 observer 的例外型別）。
        成功路徑同理：observer 失敗會讓一次**成功**的分類變成一次失敗。

        `team.md` 的錯誤處理形狀允許在觀測邊界降級，**不得靜默**——故記一行
        WARN。這裡刻意捕 `Exception` 而不是 `BaseException`：
        `KeyboardInterrupt`／`SystemExit` 不該被一個 log 寫出動作吞掉。
        """
        try:
            self._observer(observation)
        except Exception as exc:  # 觀測邊界：降級並記 log，不得遮蓋原始結果
            logger.warning(
                "觀測事件寫出失敗，本輪的判定結果與例外不受影響：%s",
                type(exc).__name__,
            )

    def _compiled_graph(self) -> Any:
        if self._graph is None:
            self._graph = self._graph_builder(self._model_factory(self._config))
        return self._graph

    def build_prompt(self, context: RoutingContext, text: str) -> RoutingPrompt:
        """L0 的產出 → L2 的輸入。拆成一個方法只為了讓它可被單獨讀。"""
        return build_routing_prompt(
            user_text=text,
            work_target_hint=context.work_target_hint,
            recent_messages=context.recent_messages,
            memory_notes=context.memory_notes,
        )

    async def classify(
        self,
        principal: Any,
        session: Any,
        text: str,
        *,
        turn_id: str = "",
    ) -> IntentDecision:
        """`K-10`：把一句自然語言判定為 `IntentDecision`。

        `W1` 的九步在這裡的對應：

        1. `prompt_guard` 前置（`BR1.1`）——命中即止，**不呼叫任何 LLM**
           （`BR1.2`）並拋 `PlatformSelfModificationRefused`。
        2. L0 取該段作業對象與歷程、取語意／程序記憶（`BR5.1`／`NFR7.62`）。
        3. L2 組出**最少上下文**的 prompt（`BR6.1`）。
        4. L3 發出**恰一次** tool call（`NFR3.62`／`NFR3.63`）。
        5. L4 把扁平回應還原成**槽位 × 候選**兩層並跑 `V-1`～`V-5`。
        6. L5 對每槽位求 `can_single_out`、以 `BR4.2` AND 聚合、填入
           `IntentDecision`。

        **本方法不建立工作項、不決定狀態、不呼叫既有能力**（`BR7.3`）——
        那是 `U12`。也**不寫 `SessionContext`**（`BR7.4`）。

        `turn_id` 是**關鍵字、選用**的附加參數。`K-10` 的 `params` 固定為
        `principal, session, text`，而 `RoutingObservation.turn_id`
        （`observability-design.md` §三：`turn_id` 是唯一的串接鍵）需要它。
        以 keyword-only 預設值的形式附加，不改變契約要求的那三個參數。
        省略時觀測仍會產生，只是無法與 `U13`／`U12` 的事件串起來。

        **`prompt_guard` 命中為什麼拋例外而不回 `IntentDecision`**：
        固定拒絕訊息不是一個 `IntentDecision`（兩邊皆空會違反 `EC5`），
        而 `K-10` 把 `returns` 固定為 `IntentDecision`。該訊號**刻意不繼承**
        失敗基底，且呼叫端義務（以 `done` 而非 `error` 結束，`BR1.3`）寫在
        它的 docstring 裡。既有的 DEMO 閘道也在自己那一層做了同樣的檢查
        ——**雙重檢查是刻意的縱深**，而 `BR1.1` 要求的是「在呼叫任何 LLM
        之前」，不是「只有一處」。
        """
        started = time.perf_counter()
        context: Optional[RoutingContext] = None
        result: Optional[ClassificationResult] = None

        def elapsed_ms() -> int:
            return int((time.perf_counter() - started) * 1000)

        if guard_hits(text):
            self._observe(
                RoutingObservation(
                    turn_id=turn_id,
                    slot_count=0,
                    capability_ranks=(),
                    scores_available=False,
                    can_single_out=False,
                    elapsed_ms=elapsed_ms(),
                    error_kind=PROMPT_GUARD_HIT,
                    memory_degraded=False,
                )
            )
            raise PlatformSelfModificationRefused()

        try:
            context = fetch_routing_context(
                principal=principal,
                session=session,
                text=text,
                memory_facade=self._memory_facade,
                segment_id=self._segment_id,
            )
            payload = await arun_routing(
                self._compiled_graph(),
                self.build_prompt(context, text),
                CallBudget(self._config.max_calls_per_turn),
            )
            result = parse_classification(payload)
            decision = decide(result, self._config.confidence_threshold)
        except BaseException as exc:
            self._observe(
                RoutingObservation(
                    turn_id=turn_id,
                    slot_count=0 if result is None else len(result.slots),
                    capability_ranks=_capability_ranks(result),
                    scores_available=(
                        False if result is None else result.scores_available
                    ),
                    can_single_out=False,
                    elapsed_ms=elapsed_ms(),
                    error_kind=type(exc).__name__,
                    memory_degraded=(
                        False if context is None else context.memory_degraded
                    ),
                )
            )
            raise

        self._observe(
            RoutingObservation(
                turn_id=turn_id,
                slot_count=len(result.slots),
                capability_ranks=_capability_ranks(result),
                scores_available=result.scores_available,
                can_single_out=can_dispatch(
                    result, self._config.confidence_threshold
                ),
                elapsed_ms=elapsed_ms(),
                error_kind=None,
                memory_degraded=context.memory_degraded,
            )
        )
        return decision


__all__ = [
    "IntentRouter",
    "RoutingContext",
    "fetch_routing_context",
    "guard_hits",
    "log_routing_observation",
]
