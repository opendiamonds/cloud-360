"""intent_routing_types.py — `U11 intent-router` 的純資料形狀

**契約（同進程呼叫端依賴，請勿變更）**

本檔是 `functional-design/entities.md` 四個實體（`CandidateIntent`／
`CandidateRanking`／`ClassificationResult`／`IntentDecision`）與 `K-10` 的兩個
線上形狀（`Intent`／`ClarifyCandidate`）在程式層的落點，另含
`RoutingObservation`——它的**欄位集合即日誌白名單**（`SEC-3`／`SEC-5`）。

硬約束
------

- **零 I/O、零 DB、零網路、零 web framework 型別。** 本檔與
  `intent_routing_predicate`／`intent_routing_parser`／`intent_routing_context`
  同屬純函式區，而 `ADR-0006` 對 agent routing 的 property-based 測試
  hard constraint 的前提是被測對象為純函式（`BR3.6`）。
- **本檔的 dataclass 一律不 raise。** 形狀的驗證在 `intent_routing_parser`
  （`V-1`～`V-5`），不在建構子——述詞 `can_single_out` 必須對任何合法 ranking
  回傳布林值而不 raise（`BR8.3`／`NFR3.71`），把驗證放進建構子會讓
  property-based 測試在產生輸入的那一步就炸掉，驗不到述詞本身。
- **`RoutingObservation` 不得新增任何輸入衍生欄位。** `text`／`label`／
  `referent` 一律不在其中（`SEC-3`／`SEC-5`）。本 repo 為 public、Actions log
  公開可讀，而本單元處理的是使用者自由文字——白名單寫成型別是為了讓「記出去」
  在型別層不可能，而不是靠下一個人記得不要記。

槽位與候選是兩個不同的軸（`EC6`）
--------------------------------

同一個 `CandidateRanking` 內的候選是**互斥**的（對同一件事的幾種讀法，只能選
一個）；不同 `CandidateRanking`（槽位）之間是**並存**的（兩件事都要做）。
把兩者壓成一張清單時「輸出幾個 `Intent`」就沒有規則可循，而最直覺的實作會
靜默丟掉第二個意圖——那是 `functional-design` 審查 `R-01` 的 Critical。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional, Tuple

# ---------------------------------------------------------------------------
# 封閉集合
# ---------------------------------------------------------------------------

#: `BR2.2`／`V-2`：`capability` 的**封閉**值域。值域由既有能力集合決定，
#: **不由本單元發明**（`entities.md` 的 `CandidateIntent.capability` 逐字）。
#:
#: 單一真實來源的處置（`team.md` 的「單一真實來源」規則）：同一份能力 id 清單
#: 也存在於 `brain_router.py` 的 DEMO `_CAPABILITIES`（該檔自述為 DEMO SCOPE，
#: `U13` 落地時整支取代）。兩份並存期間由
#: `tests/test_intent_routing_structure.py` 的一條測試鎖住兩者一致——
#: 規則逐字要求「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試」。
ROUTABLE_CAPABILITIES: Final[Tuple[str, ...]] = (
    "architecture-design",
    "well-architected-review",
    "cost-finops",
)

#: `EC3`／`BR5.4`：`referent` 為 `None` 時必須能區分兩種情況，否則 `AC6.1.2`
#: （「指涉詞無法判定指哪一個 ⇒ 走反問路徑」）**不可構造**。
#:
#: 這是 `OPEN-IR11-1` 的處置：`functional-design` 只鎖定「必須可區分」這個
#: 不變量、把形狀留給本站，本站選的是一個**顯式的狀態欄位**而非 sentinel
#: 字串——sentinel 會被當成真的 referent 值往下游傳。
REFERENT_ABSENT: Final = "absent"
REFERENT_UNRESOLVED: Final = "unresolved"
REFERENT_RESOLVED: Final = "resolved"
REFERENT_STATES: Final[Tuple[str, ...]] = (
    REFERENT_ABSENT,
    REFERENT_UNRESOLVED,
    REFERENT_RESOLVED,
)

#: `V-3`：槽位數上界。**`4` 是暫定值**（`performance-design.md` §三 的 `D-7`）：
#: 它的依據只是 `FR5.1` 的唯一官方例子（2 個意圖）乘一個安全係數，而超界的後果
#: 是**整輪失敗**而非降級。覆核工具是 `NFR3.73` 的槽位數分佈（`build-and-test`）。
#:
#: 上界本身**不是**暫定的：`slot` 是模型填的整數，沒有上界時一個失控的回應可以
#: 宣告 1000 個槽位，而 `U12` 會據此建 1000 個工作項。
MAX_SLOTS: Final = 4
MAX_SLOT_INDEX: Final = MAX_SLOTS - 1

#: `P-3`：每槽位候選數上界（tool schema 的 `maxItems`）。輸出 token 數是延遲的
#: 直接因子，而 `NFR3.60` 的預算是 P50 ≤ 800 ms。
MAX_CANDIDATES_PER_SLOT: Final = 8


# ---------------------------------------------------------------------------
# 實體（`functional-design/entities.md`）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateIntent:
    """分類器對一句輸入提出的一個候選判讀。**值物件**。

    `rank` **一定有**、`score` **可能沒有**，而這個不對稱是刻意的：`OQ-10`
    問的就是分數存不存在，而排序無論如何都存在——分類器總能給出「最可能的是
    這個」（`BR2.3`）。

    `tied_with_next` **刻意無預設值**。它是 `BR3.3`（無分數分支）唯一的輸入，
    而一個「預設不並列」會讓無分數時述詞退化成永遠可單選——`FR1.6` 逐字警告的
    正是這個後果：「`FR1.3` 會**靜默永不觸發**，而文件上看起來已解決」。
    沒有預設值，呼叫端就必須想一次。
    """

    capability: str
    rank: int
    label: str
    tied_with_next: bool
    referent_state: str
    referent: Optional[str] = None
    score: Optional[float] = None


@dataclass(frozen=True)
class CandidateRanking:
    """**一個槽位**的完整候選清單。述詞 `can_single_out` 的唯一輸入。

    `candidates` 依 `rank` 遞增排序（`BR2.2`）。**至少一個**（`EC1`）——
    空清單是分類失敗（`EmptyCandidates`）而不是「判不出來」，由
    `intent_routing_parser` 的 `V-1` 擋下。
    """

    candidates: Tuple[CandidateIntent, ...]

    @property
    def scores_available(self) -> bool:
        """`EC2`／`BR2.5`：是否**每一個**候選都帶 `score`。

        寫成 property 而不是欄位，是為了讓 `EC2` 由構造成立：兩份資料
        （清單與旗標）遲早分歧，而分歧的徵兆是「某次判定走了錯的分支」這種
        不會有人注意的東西。**它決定述詞走哪一個求值分支**，而分支由資料本身
        決定——使 `OQ-10` 的兩種結論都不需要改述詞。
        """
        return bool(self.candidates) and all(
            c.score is not None for c in self.candidates
        )


@dataclass(frozen=True)
class ClassificationResult:
    """一次分類的完整結果：**N 個槽位**，每個槽位一張自己的候選清單（`EC6`）。

    本單元**內部**形狀，不出現在 `K-10` 的線上形狀——`U13` 收到的是
    `IntentDecision`。

    `slot_labels` 與 `slots` **等長**，第 i 個是第 i 個槽位的人話任務描述。
    它的來源是同一次 tool call 的平行欄位（仍是扁平的，不違反 `[D1]`=A），
    用途是 `EC8`／`BR4.5`：多槽位同時不可單選時候選要攤平成一張清單，而
    `K-10` 的 `ClarifyCandidate` **沒有槽位欄位**，`label` 是唯一能承載
    「這是在問哪件事」的欄位。**出處由程式附加，不依賴模型自己寫進 `label`**
    ——依賴模型是一個無法驗證的要求（`reliability-design.md` §二之二）。
    """

    slots: Tuple[CandidateRanking, ...]
    slot_labels: Tuple[str, ...]

    @property
    def scores_available(self) -> bool:
        """跨**整張清單**的全有或全無（`V-5` 逐字「跨整張清單，非每組」）。

        `intent_routing_parser` 在建立本物件時已把「部分有分數」降級為整張清單
        無分數，故各槽位的 `scores_available` 彼此一致；本 property 以 `all`
        表達該一致性而不另存一份。
        """
        return bool(self.slots) and all(slot.scores_available for slot in self.slots)


# ---------------------------------------------------------------------------
# `K-10` 的線上形狀（**欄位集合由契約固定，本單元不改**）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Intent:
    """`K-10` 逐字 `{ capability: str, referent: "str|None" }`。"""

    capability: str
    referent: Optional[str] = None


@dataclass(frozen=True)
class ClarifyCandidate:
    """`K-10` 逐字 `{ id, label, capability, confidence: "float|None" }`。

    `id` 由 `intent_routing_predicate` **決定性地**由槽位序與 `rank` 推導，
    不用 `uuid4`——L5 是純函式層（`BR3.6`），而隨機值會讓 property-based
    測試無法對同一輸入斷言同一輸出。
    """

    id: str
    label: str
    capability: str
    confidence: Optional[float] = None


@dataclass(frozen=True)
class IntentDecision:
    """本單元對外的判定結果。**欄位集合由 `K-10` 固定。**

    `below_threshold` 由述詞 `can_single_out` 的否定（對全部槽位 AND 聚合後）
    **填入**，**不是**由 `confidence < 0.7` 直接算出（`BR3.1`／`[IR1]`=A）。

    `confidence` 的型別照 `K-10` 原樣轉錄為 `float`（`contract-summary.md:761`
    逐字「`float`，定義域 0–1」，**無 null**）。`entities.md` 把它標為
    `pending`，改寫權屬 `nfr-requirements`，而本站**沒有**放寬成 nullable 的
    授權——故本站的處置是讓無分數時的取值成為一個**具名、可觀測、單一落點**的
    推導（見 `intent_routing_predicate.derive_contract_confidence`），而不是
    悄悄把型別改成 `Optional[float]`。
    """

    intents: Tuple[Intent, ...]
    confidence: float
    below_threshold: bool
    candidates: Optional[Tuple[ClarifyCandidate, ...]] = None


# ---------------------------------------------------------------------------
# 觀測（`SEC-3`／`SEC-5`／`observability-design.md` §一）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingObservation:
    """**欄位集合即日誌白名單。**

    白名單寫成型別的理由：黑名單靠紀律，型別靠編譯。`text` 不在這個 dataclass
    裡，就沒有一條路徑能把它記出去。

    禁止側（**不得**新增）：`text`、`label`、`referent`、記憶內容、prompt 全文、
    模型原始回應。**`referent` 最容易被漏**——它看起來像識別碼，實際上是解析
    使用者句子得到的系統名或圖名，那是使用者的內容。

    `error_kind` 是**型別名**而不是訊息（`NFR3.74` 的分型計數前提）；
    `prompt_guard` 命中沿用同一個型別，`error_kind` 填
    `PROMPT_GUARD_HIT`（`SEC-4`）。

    `memory_degraded` 是 `D-1`（`U8` 不可用時降級而非失敗）**唯一的保險**：
    少了它，「記憶永遠取不到」是一個無聲的長期降級（`project.md` 記過的
    `N8N_USER` 那類失敗——服務照常啟動、功能靜默降級）。
    """

    turn_id: str
    slot_count: int
    capability_ranks: Tuple[Tuple[str, int], ...]
    scores_available: bool
    can_single_out: bool
    elapsed_ms: int
    error_kind: Optional[str]
    memory_degraded: bool


#: `SEC-4`：`prompt_guard` 命中事件的 `error_kind` 取值。它是安全事件、必須
#: 可被計數，但計數不需要知道他說了什麼。
PROMPT_GUARD_HIT: Final = "PROMPT_GUARD_HIT"


__all__ = [
    "MAX_CANDIDATES_PER_SLOT",
    "MAX_SLOTS",
    "MAX_SLOT_INDEX",
    "PROMPT_GUARD_HIT",
    "REFERENT_ABSENT",
    "REFERENT_RESOLVED",
    "REFERENT_STATES",
    "REFERENT_UNRESOLVED",
    "ROUTABLE_CAPABILITIES",
    "CandidateIntent",
    "CandidateRanking",
    "ClarifyCandidate",
    "ClassificationResult",
    "Intent",
    "IntentDecision",
    "RoutingObservation",
]
