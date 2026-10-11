"""intent_routing_predicate.py — `U11 intent-router` 的 **L5**：述詞與聚合

**契約（同進程呼叫端依賴，請勿變更）**

本檔是 `ADR-0006` 的 **property-based testing hard constraint 落點**。
`ADR-0006` 逐字點名 **agent routing** 為三個落點之一，而本單元就是 agent
routing；`contract-summary.md:797-799` 的 `pbt_note` 逐字指定受測對象為
「門檻比較這個純函式」。**本單元的 PBT 判定是 blocking，不是 N/A。**

硬約束
------

- **純函式**：輸入只有 `ClassificationResult`／`CandidateRanking` 與門檻；
  **無 I/O、無模型呼叫、無時間相依、無隨機值**（`BR3.6`／`NFR3.65`）。
  不純就無法做 property-based 測試。
- **述詞永不失敗**：對任何**合法**的 ranking（`EC1`：非空；`EC2`：分數全有或
  全無）都回傳布林值，不 raise、不回 `None`（`BR8.3`／`NFR3.71`）。
  空清單是**不合法**的輸入，由 `intent_routing_parser` 的 `V-1` 以
  `EmptyCandidates` 擋在本層之前——本檔**刻意不**為它加防禦性分支：那會把
  「分類失敗」靜默變成「判不出來」，正是 `BR2.4` 禁止的事。
- **`below_threshold` 的唯一判定點就是本檔**（`BR3.1`）。在述詞之外另有一條
  判定路徑，就會有兩個真實來源。

兩層求值（`R-01` 的處置，`BR3.2`／`BR3.3` vs `BR4.2`）
----------------------------------------------------

`can_single_out` 作用於**一個槽位**；整句判定是對**全部槽位的 AND**
（`can_dispatch`）。把兩者合成一個函式會讓人以為述詞吃的是整句，而那正是
`functional-design` 審查 `R-01` 的來源。

| 層 | 函式 | 規則 |
|---|---|---|
| 一個槽位 | `can_single_out(ranking, threshold)` | `BR3.2`（有分數）／`BR3.3`（無分數） |
| 整句 | `can_dispatch(result, threshold)` | `BR4.2` 的 AND 聚合 |
| 基數 | `intents_for(result)` | `BR4.4`／`EC7` 的**等式** |
| 攤平 | `clarify_candidates_for(result, threshold)` | `BR4.5`／`EC8` |

`BR3.3`（無分數分支）是整組裡最容易被略過、而後果最嚴重的一條
---------------------------------------------------------

少了它，無分數時述詞會退化成「永遠可單選」，`FR1.3` 於是**靜默永不觸發**。
`FR1.6` 逐字警告的正是這個後果。該分支的唯一輸入是
`CandidateIntent.tied_with_next`——由分類器宣告「第一名與第二名之間有沒有
嚴格優先」（`BR3.3` 逐字「分類器宣告的嚴格優先」）。**不能用 `rank` 本身代替**：
`rank` 依 `V-4` 永遠是 1、2、3…，用它判定等於永遠「嚴格」，就是上面那個
靜默失效。
"""

from __future__ import annotations

from typing import Final, Tuple

from services.intent_routing_types import (
    REFERENT_UNRESOLVED,
    CandidateRanking,
    ClarifyCandidate,
    ClassificationResult,
    Intent,
    IntentDecision,
)

#: `derive_contract_confidence` 在「整張清單無分數且整句不可交辦」時的取值。
#: 它**不是**一個量測到的信心值——理由見該函式的 docstring。
_NO_SIGNAL_BELOW: Final = 0.0


def has_unresolved_referent(ranking: CandidateRanking) -> bool:
    """該槽位是否有任何候選宣告「有指涉詞但解析不出來」（`BR5.2`／`AC6.1.2`）。

    **只有 `unresolved` 算**。`absent`（這句話本來就沒有指涉詞，例如「幫我畫
    一張架構圖」）是**完全正常**的情形，不得連帶擋下——那會讓每一句不帶指涉詞
    的輸入都被反問，把一個 Must 功能變成不可用。這是本函式最容易做錯的地方，
    故以 `== REFERENT_UNRESOLVED` 的等值比對表達，而不是「不等於 resolved」。

    **為什麼看全部候選而不只看 `rank == 1`**：`BR5.2` 的 `logic` 逐字是
    「IF **指涉詞**不可唯一解析 THEN `can_single_out` 為假」——不可唯一解析是
    **這句話**（這個槽位）的性質，不是某一個讀法的性質；欄位之所以掛在候選上，
    只因為 `[D1]`=A 的扁平 schema 把一切都掛在候選上。
    看全部候選是**較保守**的那一邊，而兩種錯的代價不對稱：多問一次的代價是
    一次互動，少問一次的代價是 `FR1.3` 逐字要防的「擅自做出我沒要的東西」。
    """
    return any(
        candidate.referent_state == REFERENT_UNRESOLVED
        for candidate in ranking.candidates
    )


def can_single_out(ranking: CandidateRanking, threshold: float) -> bool:
    """**對一個槽位**求值：這件事能不能單選出一個讀法。

    三道條件，依序：

    1. **`BR5.2`／`AC6.1.2`**：該槽位有任何候選宣告 `referent_state` 為
       `unresolved` ⇒ **為假**，不論分數多高。`AC6.1.2` 的 Then 逐字
       「系統走 `US1.2` 的反問路徑，**不擅自挑一個**」。
    2. `BR3.2`（`scoresAvailable` 為真）：該槽位最高分 ≥ 門檻。
    3. `BR3.3`（為假）：候選數為 1，**或**第一名與第二名之間存在分類器宣告的
       嚴格優先（亦即第一名未被標為與下一名並列）。

    **第 1 道是這一輪補的，而它之前是一個缺口而不是一個簡化**：`referent_state`
    有寫入端（parser）、有 schema（port）、有 prompt 指示（context），卻**沒有
    任何讀取端**，於是「模型回單一候選、無分數、未並列、但 `referent_state` 為
    `unresolved`」這條**可構造**的路徑會交辦一個 `referent=None` 的 `Intent`
    ——而 `Intent` 的欄位集合由 `K-10` 固定為 `{capability, referent}`，該狀態
    也不跨契約邊界，所以 `U13` 同樣補不了這個判斷。
    加上第 1 道之後另有一個由構造成立的後果：**可交辦的槽位其 rank 1 的
    `referent` 必然不是「解析失敗」**，要嘛是一個解析成功的字串、要嘛是
    `absent` 的 `None`。

    分支 2／3 由**資料本身**決定（`scores_available` 是 `CandidateRanking` 的
    衍生 property），不由設定或模型名稱決定——這是 `[IR1]`=A 的機制，使 `OQ-10`
    的兩種結論都不需要改述詞。第 1 道**與分數無關**，故它在 `OQ-10` 的兩種
    結論下都成立。

    `ranking.candidates` 為空時本函式會 raise `IndexError`。那是**不合法**的
    輸入（`EC1`），已由 `V-1` 以 `EmptyCandidates` 擋下；`NFR3.71` 的「永不
    失敗」逐字只涵蓋**合法**的 ranking。
    """
    if has_unresolved_referent(ranking):
        return False
    top = ranking.candidates[0]
    if ranking.scores_available:
        return top.score >= threshold
    return len(ranking.candidates) == 1 or not top.tied_with_next


def can_dispatch(result: ClassificationResult, threshold: float) -> bool:
    """**整句**判定（`BR4.2`）：⟺ **每一個**槽位都可單選。

    任一槽位為假則整句走反問，**不產生任何 `Intent`**——即使其中某個槽位本身
    很明確。`FR1.3` 逐字「不得交辦、不得產生任何結果」，而「任何」涵蓋多意圖
    情境；逐槽位反問會讓畫面同時出現工作項與反問（違反 `BR3.5`）。

    `slots` 為空時回 `False`：沒有任何一件事要做，就沒有東西可交辦。該情況
    已由 `V-1`／`V-3` 擋在本層之前（至少一個槽位），此處的 `bool(...)` 只是
    讓本函式對全部輸入都有定義，而不是一條語意分支。
    """
    return bool(result.slots) and all(
        can_single_out(slot, threshold) for slot in result.slots
    )


def derive_contract_confidence(
    result: ClassificationResult,
    threshold: float,
    dispatchable: bool,
) -> float:
    """推導 `K-10` 的 `IntentDecision.confidence`（型別 `float`，**非 nullable**）。

    `K-10` 的 `data_shape` 逐字「`float`，定義域 0–1」，**無 null**；
    `entities.md` 把這個欄位標為 `pending`，改寫權明文屬 `nfr-requirements`，
    而本單元**沒有** `OQ-N4` 那種逐字授權。故本函式的存在就是
    `entities.md` 要求的那個「**顯式的失敗點**」——把「無可比較的信心訊號」
    集中在一個具名、可觀測、單一落點的推導裡，而**不是**悄悄把型別放寬成
    `Optional[float]`。

    推導方式讓 `K-10` 自己宣告的關係**逐字成立**
    （`below_threshold: "bool —— confidence < threshold"`）：

    - **有分數時**：取各槽位最高分的**最小值**。`BR4.2` 的 AND 聚合
      ⟺ `all(top_i >= t)` ⟺ `min(top_i) >= t`，故 `below_threshold`
      與 `confidence < threshold` 在兩個方向上都一致。
    - **無分數時**：沒有一個量測到的數字可以填。回傳**能讓同一個關係維持為真
      的最小資訊量**——可交辦時回門檻本身（`threshold < threshold` 為偽），
      不可交辦時回 `0.0`（`0.0 < threshold` 為真，因為
      `intent_routing_config` 保證 `0 < threshold <= 1`）。

    **這個值不是信心度，讀它的人必須知道這件事。** 同一輪的
    `RoutingObservation.scores_available` 為假即為標記——`OQ-10` 定案後
    （承接 `build-and-test`）本函式與 `K-10` 的欄位語意須一併重新檢視。
    """
    if result.scores_available:
        return min(slot.candidates[0].score for slot in result.slots)
    return threshold if dispatchable else _NO_SIGNAL_BELOW


def intents_for(result: ClassificationResult) -> Tuple[Intent, ...]:
    """`BR4.4`／`EC7` 的**基數等式**：`len(intents) == len(slots)`。

    第 i 個 `Intent` 取第 i 個槽位 `rank == 1` 的候選，`capability` 與
    `referent` **逐欄複製**。

    **少了這條等式，`FR5.1` 的官方可測不變量可以用 1 個 `Intent` 滿足**
    （`BR3.5` 只說 `intents` 非空）：使用者只看到一個工作項，第二個請求被靜默
    丟棄，而 `US5.1` 在追溯表上仍標 `OK`。這是 `functional-design` 審查
    `R-01` 的直接修補。

    本函式**不附帶順序或依賴標記**（`BR4.3`）——那是
    `U12 work-orchestrator` 的狀態機，兩處各判一次必定分歧。
    """
    return tuple(
        Intent(
            capability=slot.candidates[0].capability,
            referent=slot.candidates[0].referent,
        )
        for slot in result.slots
    )


def _clarify_label(result: ClassificationResult, slot_index: int, label: str) -> str:
    """`EC8`：攤平後的 `label` 必須寫出它屬於哪一件事。

    出處由**程式附加**，不依賴模型自己寫進 `label`——依賴模型是一個**無法
    驗證**的要求：模型寫了什麼都像是合理的 `label`，沒有任何斷言能判定
    「它有沒有帶出處」（`reliability-design.md` §二之二）。

    前綴只在**多槽位**時加，依 `BR4.5` 的 trigger 逐字「整句聚合為假**且槽位
    數大於 1**」。單槽位時沒有「哪一件事」的歧義，加前綴只是噪音。
    """
    if len(result.slots) <= 1:
        return label
    if slot_index < len(result.slot_labels):
        return f"「{result.slot_labels[slot_index]}」：{label}"
    return label


def clarify_candidates_for(
    result: ClassificationResult,
    threshold: float,
) -> Tuple[ClarifyCandidate, ...]:
    """`BR4.5`／`EC8`：**所有不可單選槽位**的候選攤平成一張清單。

    `K-10` 的 `ClarifyCandidate` 欄位集合固定為
    `{id, label, capability, confidence}`，**沒有槽位欄位**（本單元無權加），
    所以多槽位同時不可單選時只能攤平——而攤平後使用者會看到一串來源不明的
    候選。`label` 是唯一能承載「這是在問哪件事」的欄位。

    `id` 由槽位序與 `rank` **決定性地**推導而不是 `uuid4`：L5 是純函式層，
    隨機值會讓 property-based 測試無法對同一輸入斷言同一輸出。它在一次判定
    之內唯一（槽位序 ＋ `rank` 的組合由 `V-3`／`V-4` 保證唯一）。
    """
    out = []
    for index, slot in enumerate(result.slots):
        if can_single_out(slot, threshold):
            continue
        for candidate in slot.candidates:
            out.append(
                ClarifyCandidate(
                    id=f"s{index}r{candidate.rank}:{candidate.capability}",
                    label=_clarify_label(result, index, candidate.label),
                    capability=candidate.capability,
                    confidence=candidate.score,
                )
            )
    return tuple(out)


def decide(result: ClassificationResult, threshold: float) -> IntentDecision:
    """把一次分類結果收斂成 `K-10` 的 `IntentDecision`。

    `EC4`／`EC5` 是**一對**，兩者都由本函式的兩條分支構造成立：

    - `below_threshold` 為真 ⇒ `intents` 為空 **且** `candidates` 非空。
    - `below_threshold` 為假 ⇒ `intents` 非空 **且** `candidates` 為
      `None`。

    只寫 `EC4` 是不夠的：`FR1.3` 說「不得交辦」，但沒說「交辦時不得同時附
    候選」。一個同時給出工作項與候選清單的實作在字面上沒有違反 `FR1.3`，
    而它會讓畫面同時出現工作項與反問。
    """
    dispatchable = can_dispatch(result, threshold)
    confidence = derive_contract_confidence(result, threshold, dispatchable)
    if dispatchable:
        return IntentDecision(
            intents=intents_for(result),
            confidence=confidence,
            below_threshold=False,
            candidates=None,
        )
    return IntentDecision(
        intents=(),
        confidence=confidence,
        below_threshold=True,
        candidates=clarify_candidates_for(result, threshold),
    )


__all__ = [
    "can_dispatch",
    "has_unresolved_referent",
    "can_single_out",
    "clarify_candidates_for",
    "decide",
    "derive_contract_confidence",
    "intents_for",
]
