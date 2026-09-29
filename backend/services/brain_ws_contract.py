"""
brain_ws_contract.py — `U2 brain-ws-contract`：大腦 WebSocket 訊息契約

職責：
  - 宣告 `/api/brain/ws` 上**兩個方向**的全部訊息型別（envelope、payload、列舉）
  - 強制三條可機械斷言的封包層不變量：`BR1.2`（payload 形狀由 type 唯一決定）、
    `BR1.5`（終止事件兩份 turnId 必須相等）、`BR1.6`（turnId 的輪次／非輪次二分）
  - 宣告握手 subprotocol 的格式（`WsSubprotocol`，`ADR-0019 §3`）
  - **不做任何 I/O**：無 router、無 FastAPI、無 DB session、無 `httpx`、
    無 `HTTPException`、無 logger。純 Pydantic。這是刻意的結構前提——
    `dump_ws_contract.py` 只 import 本模組，所以那道閘門的紅燈只代表
    「契約漂移了」，不會被應用程式任何無關的 import 失敗連帶染紅。

契約（前端依賴，請勿變更）：
  本模組是**唯一人手改的真實來源**（`K-02 source_of_truth`）。兩個衍生物
  皆 commit 進版控但**不得手改**（`BR4.1`）：

    repo 根 `ws-contract.json`
        由 `python scripts/dump_ws_contract.py`（於 `backend/` 執行）產生。
        CI backend job 以 `--check` 斷言「規格檔 == 本模組」。
    `frontend/src/types/ws-contract.d.ts`
        由 `npm run gen:ws-types` 從上面那份規格檔產生。
        CI frontend job 以 `npm run check:ws-types` 斷言
        「committed 型別檔 == 由規格檔重產的型別檔」。

  改動本模組的任一欄位，就必須重跑上面兩步並把兩個衍生物一併 commit
  （`functional-spec.md` 的 WF-1）。**兩道閘門缺一不可**（`BR4.3`）：
  `tsc -b` 驗的是「用法符不符合型別檔」，不是「型別檔符不符合規格檔」。

  訊息封包（伺服器→客戶端）
      `{ v: 1, type: <九值之一>, turnId: string|null, payload: {...} }`
  訊息封包（客戶端→伺服器）
      `{ v: 1, type: <六值之一>, payload: {...} }`
      **沒有 turnId**（`BR2.13`）——turnId 由伺服器產生，客戶端沒有合法理由寫它。
  入站第一步的寬鬆封包
      `WsUnvalidatedEnvelope`：`v: int`、`type: str`（`BR1.1` 的明文例外）
  握手
      `Sec-WebSocket-Protocol: f"{scheme}{separator}{token}"`，格式見 `WsSubprotocol`

為何欄位名是 camelCase 而不是本 repo 的 Python 慣例 snake_case：
  這些名稱**就是線上契約本身**，前端型別檔逐字沿用它們。改成 snake_case 會需要
  一層 alias，而那層 alias 會成為第二份真實來源。`entities.md` 的欄位名是
  camelCase，本模組逐字照抄。

本模組**不定義**的東西（刻意的界線，非遺漏）：
  turnId 的產生方式、candidateId 是否屬於當前輪次、WebSocket 關閉碼與其
  `expected`／`received`、端點路徑、握手步驟、`record=True` 的活動記錄——
  全屬 `U13`／`K-12`。作業對象三層之間的階層一致性屬 `U7`。
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# 全部契約模型共用的設定。`extra="forbid"` 不只是衛生問題，它是 `NFR5.7`
# （授權繞過必須在型別層不可構造）的第一層：客戶端偷帶 `turnId`、`userId`、
# `role` 等欄位時直接 `ValidationError`，而不是被靜默忽略。
_CONTRACT_CONFIG = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# type 列舉（兩個方向各一）
# ---------------------------------------------------------------------------


class WsServerMessageType(str, Enum):
    """伺服器→客戶端的 type 值域（**九值**）。

    `K-02:215–269` 逐字列舉八個；`ready` 為 `functional-design` 審查 R-01 新增
    （`K-12:948` 要求版本相容時回 `ready`，而 `K-02` 的清單沒有它——兩個已核可
    契約直接矛盾）。九值須與 `_SERVER_PAYLOAD_BY_TYPE` 一一對應（`BR1.4`）。
    """

    READY = "ready"
    TOKEN = "token"
    CLARIFY = "clarify"
    WORK_ITEMS = "work_items"
    COST_CARD = "cost_card"
    SHARING_MODE = "sharing_mode"
    WORK_TARGET = "work_target"
    DONE = "done"
    ERROR = "error"


class WsClientMessageType(str, Enum):
    """客戶端→伺服器的 type 值域（**六值**）。

    `K-02:270–305` 逐字列舉五個；`select_clarify_candidate` 為
    `functional-design` 審查 R-02 新增（`AC1.2.2`／`AC1.2.3` 在原契約下傳輸面
    不可構造——五個既有 type 沒有一個能承載候選的 id）。**此擴充超出 `K-02`
    的條款，由 `ADR-0019` 作為上游追認的載體。**
    """

    HELLO = "hello"
    USER_MESSAGE = "user_message"
    SELECT_CLARIFY_CANDIDATE = "select_clarify_candidate"
    CORRECT_WORK_ITEM = "correct_work_item"
    SET_SHARING_MODE = "set_sharing_mode"
    SET_WORK_TARGET = "set_work_target"


# ---------------------------------------------------------------------------
# 被組成的子實體
# ---------------------------------------------------------------------------


class ClarifyCandidate(BaseModel):
    """一個候選判讀。`ClarifyPayload` 的組成元素。"""

    model_config = _CONTRACT_CONFIG

    id: str = Field(
        description="候選的識別。唯一的讀取端是 SelectClarifyCandidatePayload.candidateId。"
    )
    label: str = Field(description="給使用者看的候選說明。")
    capability: str = Field(description="該候選會交辦給哪一個能力。")
    confidence: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None,
        description=(
            "BR2.4：定義域 0–1（含端點）的信心值，可與門檻比較。"
            "**選填且不得改為必填**（BR2.3）——OQ-10 質疑路由層能否產出可比較的"
            "信心值，容許 null 使該 OQ 若收斂為「不能」時本型別不需改動。"
            "門檻判斷本身在 U11，不在本契約。"
        ),
    )


class WorkItem(BaseModel):
    """一個工作項。`WorkItemsPayload` 的組成元素。"""

    model_config = _CONTRACT_CONFIG

    workItemId: str = Field(description="工作項的識別；correct_work_item 以它指定對象。")
    label: str = Field(description="給使用者看的工作項說明。")
    status: Literal["處理中", "等待中", "完成", "失敗", "已停掉"] = Field(
        description="工作項狀態。五值為下限（[RA:FR1.2]），新增成員須改契約並重跑兩道閘門。"
    )
    capability: str = Field(description="承接這個工作項的能力。")
    waitingOn: Optional[str] = Field(
        description=(
            "null 表示未等待任何東西；status 為「等待中」時應為非 null（BR2.5）。"
            "**BR2.5 在型別層無法強制**（需要相依型別），它是伺服器端的驗證責任；"
            "且「等待中」狀態的可達性本身是未解的 H-3，落點 U12／K-11。"
        )
    )
    failureReason: Optional[str] = Field(
        description="null 表示未失敗；status 為「失敗」時應為非 null（BR2.5，同上的型別層限制）。"
    )
    sideEffect: str = Field(
        description=(
            "副作用描述，含兩個哨兵值（BR2.10，不得合併或省略其語意）："
            '"none" 表示確定沒有副作用；'
            '"unknown" 是**合法值**且語意明確——系統誠實地不知道，**不是「還沒填」**'
            "（components.md 逐字「系統不承諾停掉時不留半成品」）；"
            "其餘任意字串為副作用的描述文字。"
            "把 unknown 當成 none 處理，等於對使用者宣稱「停掉不留半成品」，"
            "而系統並不承諾那件事。"
            "**本段說明是 BR4.4 斷言的對象**：TypeScript 會把 "
            '`"none" | "unknown" | string` 塌縮為 `string`，IDE 不提示那兩個字面值，'
            "所以這兩個哨兵值的語意只能靠產生的型別檔保留本註解來傳達。"
            "拿掉本 description= 會讓註解在 ws-contract.d.ts 靜默消失——"
            "`npm run check:ws-types` 的 BR4.4 斷言就是為此存在。"
        )
    )


# ---------------------------------------------------------------------------
# server → client payloads（九個）
# ---------------------------------------------------------------------------


class ReadyPayload(BaseModel):
    """握手完成訊號（`K-12` x-handshake.step_3：版本相容時回 `ready`）。"""

    model_config = _CONTRACT_CONFIG

    protocolVersion: Literal[1] = Field(
        description=(
            "伺服器接受的協定版本。帶它而非用空 payload 的理由：空 payload 會讓"
            "「ready 到了」與「ready 的內容正確」無法區分。"
            "**BR3.5 要求前端必須核對它**——不核對就會讓本欄位成為無讀取端的欄位。"
        )
    )


class TokenPayload(BaseModel):
    """內容 token。串流回覆的最小單位。"""

    model_config = _CONTRACT_CONFIG

    text: str = Field(
        min_length=1,
        description=(
            "BR2.1：**非空白**字串。空白 token 不算內容，送出它會讓「已產出內容」"
            "的判定失真，進而繞過 BR2.6（零內容不得以 done 結束）。"
        ),
    )

    @field_validator("text")
    @classmethod
    def _br2_1_non_blank(cls, value: str) -> str:
        # min_length=1 擋不住 " "／"\n"——BR2.1 要的是「非空白」而不是「非空」。
        if not value.strip():
            raise ValueError(
                "BR2.1：token 的 text 必須是非空白字串（收到只含空白的值）。"
            )
        return value


class ClarifyPayload(BaseModel):
    """信心值低於門檻時列出的候選判讀（`AC1.2.1`–`AC1.2.3` 的傳輸面）。"""

    model_config = _CONTRACT_CONFIG

    candidates: list[ClarifyCandidate] = Field(
        min_length=1,
        description=(
            "BR2.2：**不得為空陣列**。空陣列在語意上無意義——若無候選則不應送 "
            "clarify（改送 error 或依 U11 的規格處置）。"
            "使用者看到「請選一個」卻沒有可選項是本規則要防的畫面。"
        ),
    )


class WorkItemsPayload(BaseModel):
    """工作項集合的**當前狀態**。狀態訊息，狀態改變時扇出給同一 session key 的全部存活連線。"""

    model_config = _CONTRACT_CONFIG

    items: list[WorkItem] = Field(
        description="空陣列合法（尚無工作項），與 clarify 的 candidates 不同。"
    )


class CostCardPayload(BaseModel):
    """成本卡片。"""

    model_config = _CONTRACT_CONFIG

    estimateSetId: int = Field(
        description=(
            "BR2.11：**必填整數**，K-02 X-01 的不變量。改為選填即違反上游——"
            "成本卡片會無法連回估價集合。"
        )
    )
    savingText: Optional[str] = Field(description="節省說明；null 表示沒有可說的。")
    comparisonText: Optional[str] = Field(description="比較說明；null 表示沒有可說的。")
    qualityText: Optional[str] = Field(description="品質說明；null 表示沒有可說的。")
    unavailableReasons: Optional[dict[str, Any]] = Field(
        description="無法取價的原因物件；null 表示全部可取價。形狀由 K-02 留為開放物件。"
    )
    costPageUrl: str = Field(description="連回成本頁的路徑。")


class SharingModePayload(BaseModel):
    """當前共享模式。狀態訊息，會扇出；亦於連線建立時推送。"""

    model_config = _CONTRACT_CONFIG

    mode: Literal["shared", "isolated"] = Field(description="共享或獨立對話。")


class WorkTargetPayload(BaseModel):
    """當前作業對象（專案／系統／架構圖三層）。狀態訊息，會扇出；亦於連線建立時推送。"""

    model_config = _CONTRACT_CONFIG

    projectId: Optional[str] = Field(description="null 表示尚未選定。")
    systemId: Optional[str] = Field(description="null 表示尚未選定。")
    diagramId: Optional[str] = Field(
        description=(
            "null 表示尚未選定。**三層之間的階層一致性規則不由本契約定義**"
            "（例如 systemId 非 null 時 projectId 是否必須非 null）——那是 "
            "U7 hierarchy-service 的責任。這是刻意的界線，不是遺漏。"
        )
    )


class DonePayload(BaseModel):
    """終止事件——成功產出可呈現的回覆。"""

    model_config = _CONTRACT_CONFIG

    turnId: str = Field(
        description=(
            "BR1.5：必須等於其 envelope 的 turnId。這是 turnId 在終止事件上的"
            "**第二份物化**（沿用 K-02:267／:269 的原形狀），兩份一致由 "
            "WsEnvelope 的 validator 鎖住——team.md 的「單一真實來源」要求"
            "無法避免的副本必須在同一個 PR 內附上鎖住一致性的測試。"
        )
    )


class ErrorPayload(BaseModel):
    """終止事件——未能產出可呈現的回覆。"""

    model_config = _CONTRACT_CONFIG

    code: Literal["EMPTY_RESPONSE", "INTERNAL_ERROR", "UNAUTHORIZED", "INVALID_REQUEST"] = Field(
        description=(
            "BR2.8：**封閉列舉**。各值的判準——"
            "EMPTY_RESPONSE ＝ 上游結束但無有效回覆（BR2.6，不得改送 done）；"
            "INVALID_REQUEST ＝ 客戶端請求本身不合法（作業對象三層解析不出、"
            "階層不一致、candidateId 格式錯誤、客戶端偷帶 turnId 等），"
            "**不得**把使用者輸入問題報成 INTERNAL_ERROR；"
            "UNAUTHORIZED ＝ 有權限問題但連線仍在（連線建立期的無權限走 4403 "
            "關閉，不走這裡）；"
            "INTERNAL_ERROR ＝ 以上皆非的伺服器端失敗。"
            "新增一個 code 必須改本模組、重跑 dump、重產型別檔、兩道閘門通過——"
            "前端的窮盡 switch 會立刻因缺分支而 tsc -b 紅燈，那是封閉列舉的價值。"
        )
    )
    message: str = Field(
        description=(
            "BR2.9：人類可讀的說明，**不得包含內部實作細節**（堆疊、SQL、內部路徑、"
            "模組名）。**型別擋不住字串內容**——`message: str` 無論如何都通過，"
            "所以這條的落點是伺服器端的 error 構造（U13），本契約只寫下要求。"
        )
    )
    turnId: str = Field(description="BR1.5：必須等於其 envelope 的 turnId（同 DonePayload）。")


# ---------------------------------------------------------------------------
# client → server payloads（六個）
# ---------------------------------------------------------------------------


class HelloPayload(BaseModel):
    """握手後**首則**訊息，承載協定版本（`K-12` x-handshake.step_2）。"""

    model_config = _CONTRACT_CONFIG

    v: Literal[1] = Field(
        description=(
            "與 WsClientEnvelope.v 同值同型別；不相容的入站 hello 見 "
            "WsUnvalidatedEnvelope。"
            "**token 不在此處**——走 Sec-WebSocket-Protocol 標頭（見 WsSubprotocol）。"
            "**界線**：本 payload 不含 token 欄位，只排除了「token 放在訊息內」"
            "這一條路徑；它對 query string **零約束**（query string 在 URL，"
            "不在 envelope 內，本契約的型別碰不到它）。實際擋住 AC8.1.3 的是 "
            "K-12 的 x-hard-constraints.token_transport，落點 U13。"
        )
    )


class UserMessagePayload(BaseModel):
    """使用者送出的一句需求。**非冪等**——每則觸發一輪分類與可能的交辦（BR3.4）。"""

    model_config = _CONTRACT_CONFIG

    text: str = Field(description="使用者輸入的原文。")


class SelectClarifyCandidatePayload(BaseModel):
    """選定一個候選判讀。`ClarifyCandidate.id` 的唯一讀取端。"""

    model_config = _CONTRACT_CONFIG

    candidateId: Optional[str] = Field(
        description=(
            "**非 null** 表示選定該候選（值必須是同一輪 clarify 送出的某個 "
            "ClarifyCandidate.id），伺服器依該候選交辦（AC1.2.2）。"
            "**null** 表示「都不是，我再講一次」（AC1.2.3）：該輪結束，伺服器"
            "**不送 work_target、不送 work_items、不送任何終止事件**（BR2.14）。"
            "**已知的可區分性缺陷（BR2.14 逐字記載）**：一欄兩義使「使用者按了"
            "都不是」與「客戶端把欄位序列化成 null」在傳輸上完全不可區分，"
            "而 null 在本契約其他各處一貫表示「沒有值／尚未設定」。"
            "前提：客戶端不得在使用者未做選擇時送出本訊息。"
            "**本契約不驗證 candidateId 是否屬於當前輪次**——那需要 session 狀態"
            "持有上一輪的候選集合，屬 U13。"
        )
    )


class CorrectWorkItemPayload(BaseModel):
    """逐項更正一個工作項（[RA:FR1.4]）。其餘工作項不受影響；**冪等**（已停掉者再更正為 no-op）。"""

    model_config = _CONTRACT_CONFIG

    workItemId: str = Field(description="要更正的工作項。")


class SetSharingModePayload(BaseModel):
    """把「改為獨立對話」的選擇傳到伺服器。"""

    model_config = _CONTRACT_CONFIG

    mode: Literal["shared", "isolated"] = Field(description="要切換到的模式。")


class SetWorkTargetPayload(BaseModel):
    """把選定的作業對象傳到伺服器。"""

    model_config = _CONTRACT_CONFIG

    projectId: Optional[str] = Field(description="null 表示清除該層的選定。")
    systemId: Optional[str] = Field(description="null 表示清除該層的選定。")
    diagramId: Optional[str] = Field(description="null 表示清除該層的選定。")


# ---------------------------------------------------------------------------
# 握手 subprotocol（ADR-0019 §3）
# ---------------------------------------------------------------------------


class WsSubprotocol(BaseModel):
    """握手用 subprotocol 的格式；實際值為 ``f"{scheme}{separator}{token}"``。

    為何它在契約檔內：`K-12:876` 只規定「token 走 `Sec-WebSocket-Protocol`
    標頭」，**全檔未定其值格式**。它是前後端必須逐字一致的共用字串，而在納入
    契約之前它既不在任何規格檔（無漂移閘門）、也沒有任何契約明文擁有它——
    前端改了格式而後端沒跟上時，**握手直接失敗且沒有任何閘門會紅燈**
    （`functional-spec.md §八` 第四列逐字稱它是最靜默的一個）。

    兩個欄位為字面型別，所以前端只要以
    ``const SCHEME: Sub['scheme'] = 'bearer'`` 的形狀取值，後端改值即 `tsc -b`
    紅燈。**這條保護只在前端真的由型別取值時成立**——寫死
    ``[`bearer.${token}`]`` 時型別層碰不到它，故另有一條 error 級 ESLint 規則
    （`ADR-0019 §5`）禁止 `new WebSocket` 的第二引數出現字串／模板字面量。

    **實作陷阱（落點 `U13`）**：JWT 本身以 ``.`` 分三段，所以 ``bearer.<jwt>``
    的解析必須以**第一個** ``.`` 切分（``split('.', 1)``），不得 ``split('.')``
    取兩段——後者在任何真實 token 上都會拿到四段。
    """

    model_config = _CONTRACT_CONFIG

    scheme: Literal["bearer"] = Field(description="subprotocol 的前綴，與 HTTP 的 Bearer 慣例一致。")
    separator: Literal["."] = Field(description="前綴與 token 之間的分隔字元。")


# ---------------------------------------------------------------------------
# payload 聯集與 type→payload 對應（BR1.2／BR1.4 的執行期承載）
# ---------------------------------------------------------------------------

WsServerPayload = Union[
    ReadyPayload,
    TokenPayload,
    ClarifyPayload,
    WorkItemsPayload,
    CostCardPayload,
    SharingModePayload,
    WorkTargetPayload,
    DonePayload,
    ErrorPayload,
]

WsClientPayload = Union[
    HelloPayload,
    UserMessagePayload,
    SelectClarifyCandidatePayload,
    CorrectWorkItemPayload,
    SetSharingModePayload,
    SetWorkTargetPayload,
]

# `BR1.2`：payload 形狀由 type **唯一**決定。這張表是它的執行期承載——
# 產生的 TypeScript 只會是一個 anyOf 聯集（見模組 docstring 對消費端的說明），
# 所以伺服器側必須自己鎖住對應關係，否則 `type="ready"` 配一個 TokenPayload
# 在型別上是合法的。
_SERVER_PAYLOAD_BY_TYPE: dict[WsServerMessageType, type[BaseModel]] = {
    WsServerMessageType.READY: ReadyPayload,
    WsServerMessageType.TOKEN: TokenPayload,
    WsServerMessageType.CLARIFY: ClarifyPayload,
    WsServerMessageType.WORK_ITEMS: WorkItemsPayload,
    WsServerMessageType.COST_CARD: CostCardPayload,
    WsServerMessageType.SHARING_MODE: SharingModePayload,
    WsServerMessageType.WORK_TARGET: WorkTargetPayload,
    WsServerMessageType.DONE: DonePayload,
    WsServerMessageType.ERROR: ErrorPayload,
}

_CLIENT_PAYLOAD_BY_TYPE: dict[WsClientMessageType, type[BaseModel]] = {
    WsClientMessageType.HELLO: HelloPayload,
    WsClientMessageType.USER_MESSAGE: UserMessagePayload,
    WsClientMessageType.SELECT_CLARIFY_CANDIDATE: SelectClarifyCandidatePayload,
    WsClientMessageType.CORRECT_WORK_ITEM: CorrectWorkItemPayload,
    WsClientMessageType.SET_SHARING_MODE: SetSharingModePayload,
    WsClientMessageType.SET_WORK_TARGET: SetWorkTargetPayload,
}

_SERVER_PAYLOAD_BY_VALUE: dict[str, type[BaseModel]] = {
    key.value: model for key, model in _SERVER_PAYLOAD_BY_TYPE.items()
}
_CLIENT_PAYLOAD_BY_VALUE: dict[str, type[BaseModel]] = {
    key.value: model for key, model in _CLIENT_PAYLOAD_BY_TYPE.items()
}

# `BR1.4` 在**程式物件**層的斷言（`dump_ws_contract.py` 另有一份在**規格檔**
# 層的）。兩份不重複：這一份擋「加了 type 卻沒在對應表補 payload 類別」，
# 那一份擋「加了 type 卻沒有同名 payload 實體」。
if set(_SERVER_PAYLOAD_BY_TYPE) != set(WsServerMessageType):
    raise RuntimeError(
        "BR1.4 違反：WsServerMessageType 與 _SERVER_PAYLOAD_BY_TYPE 不等勢。缺少 "
        f"{sorted(t.value for t in set(WsServerMessageType) - set(_SERVER_PAYLOAD_BY_TYPE))}"
    )
if set(_CLIENT_PAYLOAD_BY_TYPE) != set(WsClientMessageType):
    raise RuntimeError(
        "BR1.4 違反：WsClientMessageType 與 _CLIENT_PAYLOAD_BY_TYPE 不等勢。缺少 "
        f"{sorted(t.value for t in set(WsClientMessageType) - set(_CLIENT_PAYLOAD_BY_TYPE))}"
    )

# `BR1.6`：伺服器訊息分兩類，**互斥且窮盡**九個 type。
#   輪次訊息 → turnId 必為非 null（同一輪共用同一個值）
#   非輪次訊息 → turnId 必為 null
# 非輪次的四個各有明文依據：`ready` 在任何一輪之前送出（ReadyPayload 的
# entity_constraints 逐字）；`sharing_mode`／`work_target`／`work_items` 是狀態
# 訊息（`functional-spec.md §二` 逐字「它們不屬於任何一輪」）。
_TURN_SCOPED_TYPES: frozenset[WsServerMessageType] = frozenset(
    {
        WsServerMessageType.TOKEN,
        WsServerMessageType.CLARIFY,
        WsServerMessageType.COST_CARD,
        WsServerMessageType.DONE,
        WsServerMessageType.ERROR,
    }
)
_SESSION_SCOPED_TYPES: frozenset[WsServerMessageType] = frozenset(
    {
        WsServerMessageType.READY,
        WsServerMessageType.SHARING_MODE,
        WsServerMessageType.WORK_TARGET,
        WsServerMessageType.WORK_ITEMS,
    }
)

# 互斥且窮盡的機械斷言。刻意在 **import 時** fail-fast 而非等到某一則訊息剛好
# 落在缺口上：一個分類不全的 BR1.6 會讓某些 type 完全不受 turnId 檢查，
# 而那件事在執行期不會有任何訊號。
if _TURN_SCOPED_TYPES & _SESSION_SCOPED_TYPES:
    raise RuntimeError(
        "BR1.6 違反：輪次與非輪次兩集合不互斥，重疊於 "
        f"{sorted(t.value for t in _TURN_SCOPED_TYPES & _SESSION_SCOPED_TYPES)}"
    )
if _TURN_SCOPED_TYPES | _SESSION_SCOPED_TYPES != set(WsServerMessageType):
    _uncovered = set(WsServerMessageType) - (_TURN_SCOPED_TYPES | _SESSION_SCOPED_TYPES)
    raise RuntimeError(
        "BR1.6 違反：輪次與非輪次兩集合未窮盡九個伺服器 type，未分類的有 "
        f"{sorted(t.value for t in _uncovered)}"
    )

# `done` 與 `error` 是終止事件（`K-12` x-termination-semantics），也是唯二
# 在 payload 內帶第二份 turnId 的型別——`BR1.5` 只對它們成立。
_TERMINAL_TYPE_VALUES: frozenset[str] = frozenset(
    {WsServerMessageType.DONE.value, WsServerMessageType.ERROR.value}
)

_MISSING = object()


def _read_turn_id(payload: Any) -> Any:
    """從尚未驗證的 payload 取 turnId，取不到時回 `_MISSING`（與 `None` 有別）。

    「欄位不存在」與「欄位是 null」在 `BR1.5` 下是兩種不同的違反，訊息必須分開，
    否則排查的人看到「不一致」卻找不到不一致的兩個值。
    """
    if isinstance(payload, Mapping):
        return payload.get("turnId", _MISSING)
    if isinstance(payload, BaseModel):
        return getattr(payload, "turnId", _MISSING)
    return _MISSING


def _coerce_payload(data: Mapping[str, Any], by_value: Mapping[str, type[BaseModel]]) -> Any:
    """依 type 把 raw payload 綁到**唯一**對應的 payload 模型（`BR1.2`）。

    不靠 Pydantic 的 smart union 猜：猜中與猜錯在輸出上沒有差別，而猜錯時
    消費端會拿到一個形狀對不上 type 的 payload。
    """
    raw_type = data.get("type")
    type_value = raw_type.value if isinstance(raw_type, Enum) else raw_type
    model = by_value.get(type_value) if isinstance(type_value, str) else None
    payload = data.get("payload")
    if model is None or not isinstance(payload, Mapping):
        return data
    return {**data, "payload": model.model_validate(payload)}


# ---------------------------------------------------------------------------
# 三個 envelope
# ---------------------------------------------------------------------------


class WsEnvelope(BaseModel):
    """**伺服器→客戶端**訊息的外層封包（`K-02:215` 逐字 `direction: server_to_client`）。

    客戶端方向見 `WsClientEnvelope`——它**沒有** turnId（`BR2.13`）。
    """

    model_config = _CONTRACT_CONFIG

    v: Literal[1] = Field(
        description=(
            "BR1.1：協定版本的**字面值**，由 K-02 的 `type: integer` 收窄而來。"
            "收窄的理由：相容判準是「完全相等」，而完全相等在型別層的忠實表達"
            "就是字面值；且它讓「當前協定版本是 1」只存在於契約一處。"
            "升版時把字面值改為 2 會讓所有仍寫 1 的消費端立即成為型別錯誤——"
            "那正是選字面型別的整個目的。"
            "不符本版的**入站**訊息在本型別下不可表示，見 WsUnvalidatedEnvelope。"
        )
    )
    type: WsServerMessageType = Field(
        description="判別欄位。值域為 WsServerMessageType 的九值。"
    )
    turnId: Optional[str] = Field(
        description=(
            "BR1.6：**欄位必存在，但值可為 null**。"
            "輪次訊息（token／clarify／cost_card／done／error）必為非 null，"
            "同一輪的所有訊息共用同一個值（BR1.3）；"
            "非輪次訊息（ready／sharing_mode／work_target／work_items）必為 null。"
            "**本契約不定義它的產生方式**，也**無法強制「同一輪相同」**"
            "（那是執行期性質）——兩者皆屬 U13。"
        )
    )
    payload: WsServerPayload = Field(
        description="形狀由 type 唯一決定（BR1.2）；對應關係由本模型的 validator 鎖住。"
    )

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, data: Any) -> Any:
        """`BR1.5` ＋ `BR1.2` 的綁定，兩者都必須在 payload 自身的欄位驗證**之前**跑。

        為何 `BR1.5` 不能放 `mode="after"`：終止事件的 payload 缺 turnId 時，
        `DonePayload` 自己的必填檢查會先擋下並回報「field required」——那個訊息
        沒有指出違反的是 `BR1.5`（兩份 turnId 的一致性），排查的人只會以為漏填
        了一個欄位，而不知道那個欄位的值受另一個欄位約束。
        """
        if not isinstance(data, Mapping):
            return data

        raw_type = data.get("type")
        type_value = raw_type.value if isinstance(raw_type, Enum) else raw_type

        if type_value in _TERMINAL_TYPE_VALUES:
            payload_turn_id = _read_turn_id(data.get("payload"))
            envelope_turn_id = data.get("turnId")
            if payload_turn_id is _MISSING:
                raise ValueError(
                    f"BR1.5：終止事件 {type_value} 的 payload 必須帶 turnId 並等於 "
                    f"envelope 的 turnId（envelope.turnId={envelope_turn_id!r}，"
                    "payload 完全沒有 turnId）。"
                )
            if payload_turn_id != envelope_turn_id:
                raise ValueError(
                    f"BR1.5：終止事件 {type_value} 的兩份 turnId 不一致"
                    f"（envelope.turnId={envelope_turn_id!r}，"
                    f"payload.turnId={payload_turn_id!r}）。"
                    "消費端會把終止事件歸到錯誤的一輪。"
                )

        return _coerce_payload(data, _SERVER_PAYLOAD_BY_VALUE)

    @model_validator(mode="after")
    def _br1_2_payload_matches_type(self) -> WsEnvelope:
        expected = _SERVER_PAYLOAD_BY_TYPE[self.type]
        if not isinstance(self.payload, expected):
            raise ValueError(
                f"BR1.2：type={self.type.value} 的 payload 形狀必須是 "
                f"{expected.__name__}，收到 {type(self.payload).__name__}。"
            )
        return self

    @model_validator(mode="after")
    def _br1_6_turn_id_partition(self) -> WsEnvelope:
        if self.type in _TURN_SCOPED_TYPES:
            if self.turnId is None:
                raise ValueError(
                    f"BR1.6：輪次訊息 {self.type.value} 的 turnId 必為非 null"
                    "（消費端無法把它歸到任何一輪）。"
                )
        else:
            if self.turnId is not None:
                raise ValueError(
                    f"BR1.6：非輪次訊息 {self.type.value} 的 turnId 必為 null，"
                    f"收到 {self.turnId!r}（消費端會把狀態訊息誤歸到某一輪）。"
                )
        return self


class WsClientEnvelope(BaseModel):
    """**客戶端→伺服器**訊息的外層封包。

    **刻意沒有 turnId 欄位**（`BR2.13`）：turnId 由伺服器產生（`U13`），客戶端
    沒有任何合法理由寫它。配上 `extra="forbid"`，客戶端偷帶 turnId 會直接
    `ValidationError` 而不是被靜默忽略——**靜默忽略比拒絕更糟**，客戶端會以為
    自己成功指定了輪次。伺服器對這種訊息的對外回應是
    `error(code: INVALID_REQUEST)`，落點 `U13`。

    同一個 `extra="forbid"` 也是 `BR2.12`（客戶端訊息不得攜帶身分）的第一層：
    `userId`／`role`／`token`／`actor`／`onBehalfOf` 一律不可構造。
    principal 綁在**連線**上（握手時由 `Sec-WebSocket-Protocol` 的 token 建立）。
    第二層是 `dump_ws_contract.py` 的白名單斷言（`NFR5.7`）——它擋的是
    「契約自己悄悄長出一個身分欄位」，那是 review 抓不到的那一半。
    """

    model_config = _CONTRACT_CONFIG

    v: Literal[1] = Field(description="同 WsEnvelope.v；不相容的入站 hello 見 WsUnvalidatedEnvelope。")
    type: WsClientMessageType = Field(description="判別欄位。值域為 WsClientMessageType 的六值。")
    payload: WsClientPayload = Field(description="形狀由 type 唯一決定（BR1.2）。")

    @model_validator(mode="before")
    @classmethod
    def _bind_payload_to_type(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        return _coerce_payload(data, _CLIENT_PAYLOAD_BY_VALUE)

    @model_validator(mode="after")
    def _br1_2_payload_matches_type(self) -> WsClientEnvelope:
        expected = _CLIENT_PAYLOAD_BY_TYPE[self.type]
        if not isinstance(self.payload, expected):
            raise ValueError(
                f"BR1.2：type={self.type.value} 的 payload 形狀必須是 "
                f"{expected.__name__}，收到 {type(self.payload).__name__}。"
            )
        return self


class WsUnvalidatedEnvelope(BaseModel):
    """任一方在**信任邊界**上解析入站訊息所用的寬鬆封包。

    它是 `BR1.1` 的**明文例外**：`v` 刻意是 `int` 而非字面 `1`、`type` 刻意是
    `str` 而非列舉，因為它存在的目的就是表示**不符本版**的值。

    伺服器側：讓不相容的 `hello` 能被反序列化，使 `U13` 取得 `K-12` 的 `4400`
    關閉所要求的 `received`。
    客戶端側：讓 `BR3.2`（未知 type 安全忽略）與 `BR3.5`（核對
    `ready.protocolVersion`）有型別承載——那兩條規則的處置**本身就發生在驗證
    失敗的分支上**，必須讀得到未驗證的值。

    **只用於入站解析的第一步**，不得用於構造出站訊息。驗證通過即轉為
    `WsEnvelope` 或 `WsClientEnvelope`。

    **轉換時必須把原始的 dict 餵給 `WsClientEnvelope`，不得以本模型的欄位子集
    重建**：本模型是寬鬆的，客戶端偷帶的 `turnId` 在這裡會被丟掉，若之後用
    「本模型的欄位」重組一個 dict 再驗證，`WsClientEnvelope` 的
    `extra="forbid"` 就永遠看不到那個欄位，`BR2.13` 的執行期拒絕隨即失效。

    `expected`／`received` 兩個欄位**沒有型別承載**：`K-12:991` 要求 `4400`
    關閉「帶 expected 與 received」，但那是**關閉訊框的原因字串**，不是訊息
    payload。落點 `U13`／`K-12`。
    """

    # 刻意**不是** `_CONTRACT_CONFIG`：入站訊息可能來自不同版本的客戶端，
    # 帶著本版沒有的欄位是預期情形，在這一層 forbid 會讓 4400 協商路徑
    # 拿不到 received 而直接爆掉。
    model_config = ConfigDict(extra="ignore")

    v: int = Field(description="**整數，不收窄為字面值**——這正是它與 WsClientEnvelope 的差別。")
    type: str = Field(
        description="**寬鬆字串，不收窄為列舉**——收窄會讓「未知 type」在型別層不可表示，而 BR3.2 正需要能表示它。"
    )
    payload: dict[str, Any] = Field(description="未經驗證的原始物件；驗證通過後才轉為具體 payload 型別。")


# `dump_ws_contract.py` 從這裡取要 dump 的頂層模型，而不是自己維護一份清單——
# 契約的公開面由契約自己宣告。三個 envelope 加 WsSubprotocol 即可遞移涵蓋
# 全部 15 個 payload、2 個子實體與 2 個列舉。
CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    WsEnvelope,
    WsClientEnvelope,
    WsUnvalidatedEnvelope,
    WsSubprotocol,
)

# `NFR5.7` 的白名單斷言要比對的七個客戶端物件。放在契約模組內而非 dump 腳本，
# 是為了讓「新增一個客戶端物件」的人在改契約的同一個檔案裡看到這份清單。
# 預期的**欄位集合**釘在 `dump_ws_contract.py`（`ADR-0019 §6`）。
CLIENT_FACING_MODELS: tuple[type[BaseModel], ...] = (
    WsClientEnvelope,
    HelloPayload,
    UserMessagePayload,
    SelectClarifyCandidatePayload,
    CorrectWorkItemPayload,
    SetSharingModePayload,
    SetWorkTargetPayload,
)
