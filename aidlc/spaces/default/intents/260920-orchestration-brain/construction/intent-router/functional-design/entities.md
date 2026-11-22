# Entity Model — `U11 intent-router`

> 本檔是本單元**實體形狀**的唯一真實來源。決策邏輯在 `rules.md`；
> 工作流程與狀態轉換在 `functional-spec.md`。技術無關。
>
> **修訂 1（審查 `review-01.md` 之後）**：`R-01`（Critical）查出原設計把
> 「對同一個決策槽位的互斥候選」與「一句話裡並存的 N 個可分離意圖」壓進同一張
> 扁平清單，使 `FR5.1` 的官方可測不變量在規則字面下會靜默輸出 1 個意圖。
> 處置是新增 `ClassificationResult`（槽位層）並補上 `intents` 的基數規則；
> `R-02` 另把 `confidence` 的型別由已定案的 `number|null` 退回暫定。
> 六項發現的處置全表見 `functional-spec.md` §八。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `components.md` 的 `IntentRouter` 宣告 | summary 逐字「把一句自然語言判定為意圖類別並輸出可與門檻比較的信心值」；`depends_on`：`SessionContext`、`MemoryStore`；`dependents`：`BrainGateway` |
| `requirements.md` 的 `FR1.1`／`FR1.3`／`FR1.5`／`FR1.6`／`FR1.7`、`FR5.1`／`FR5.2`、`FR6.1` | 本單元全部行為的需求來源 |
| `unit-of-work.md:141`／`:143-154`／`:156-158` | `U11` 的交付（`:141`）、它自己附的阻塞警語（`:143-154`）、驗證方式與 PBT 註（`:156-158`） |
| `unit-of-work-story-map.md:116` | `U11` 承載 `US1.1`／`US1.2`／`US5.1`／`US6.1` 四則故事 |
| `contract-summary.md:745-800`（`K-10`） | 對 `U13` 的 `public_interface` 與 `data_shape`，以及 `hard_rules`、`threshold`、`cost_discipline`、`pbt_note` |

## `[IR1]`=A 的授權邊界（先講清楚，以免被讀成改契約）

`[IR1]`=A 把反問的判定寫成「**候選清單上的述詞**」，而 `K-10` 的 `data_shape`
已核可且**本站沒有任何改它的授權**（`U10` 改 `K-09` 是靠 `OQ-N4` 逐字授權，
本單元**沒有**對應的授權）。故：

| 層 | `[IR1]`=A 改不改 | 說明 |
|---|---|---|
| `K-10` 的 `IntentDecision` 欄位集合（`intents`／`confidence`／`below_threshold`／`candidates`） | **不改** | 它是與 `U13` 的線上契約 |
| 本單元**內部**的純函式層 | **改** | 新增 `CandidateRanking` 與述詞 `can_single_out`；`below_threshold` 與 `candidates` 由述詞的結果**填入**，而不是由一條 `confidence < 0.7` 直接算出 |

**所以 `[IR1]`=A 是一次內部抽象化，不是契約變更。** 若 `OQ-10` 結論為
「無可用信心訊號」，要改的是 `K-10` 的 `confidence` 欄位語意——那是**下一站**
（`nfr-requirements`）連同 `OQ-4` 一起決定的事，本站不預判。

> **修訂 1／`R-02`：「不預判」這句話原本沒有被本檔自己遵守。** 下方 YAML 原先把
> `IntentDecision.confidence` 的 `logical_type` 寫成 `number|null` 且
> `required: true`——那是一個**已定案的型別宣告**，而本檔自稱是本單元實體形狀的
> **唯一真實來源**，`code-generation` 的實作者只會讀它、不會回頭讀
> `contract-summary.md:1424`。`K-10` 的 `data_shape` 逐字是「`float`，定義域 0–1」
> （`contract-summary.md:761`），**無 null**；改寫權明文屬 `nfr-requirements`
> （`:1424`），而 `OQ-N4`（`:1433`）那種逐字授權本單元並沒有。修訂後改標為
> **暫定**並指名誰有權定案。

## Source of truth

```yaml
entity_model_version: 1
unit: intent-router

entities:
  - name: CandidateIntent
    summary: 分類器對一句輸入提出的一個候選判讀。值物件——同能力、同指涉、同分數者不可區分。
    identifier: null
    attributes:
      - name: capability
        logical_type: enum
        required: true
        description: >
          判定落到哪一個既有功能能力（架構設計／Well-Architected 檢視／成本估價 等）。
          **值域由既有能力集合決定，不由本單元發明**。
      - name: referent
        logical_type: "string|null"
        required: false
        description: >
          指涉詞解析後的作用對象（`FR6.1`）。`null` 表示這句話沒有指涉詞，
          或指涉詞無法解析——**兩者不可合併**，見 `EC3`。
      - name: score
        logical_type: "number|null"
        required: false
        min: 0
        max: 1
        description: >
          **可為 null**，而這正是 `[IR1]`=A 的關鍵。有分數時它落在 0–1；
          `OQ-10` 若結論為「無可用信心訊號」，整張清單的 score 皆為 `null`
          而排序仍然存在。**本單元的述詞對兩種情況都要有定義**。
      - name: rank
        logical_type: integer
        required: true
        min: 1
        description: 在候選清單中的名次，自 1 起。**排序永遠存在，分數未必**。
      - name: label
        logical_type: string
        required: true
        description: 給使用者看的候選說明（`FR1.3` 的「列出候選判讀」要顯示它）。

  - name: CandidateRanking
    summary: 一次分類的完整候選清單。述詞 `can_single_out` 的唯一輸入。
    identifier: null
    attributes:
      - name: candidates
        logical_type: "ordered list<CandidateIntent>"
        required: true
        min_size: 1
        description: >
          依 `rank` 遞增排序。**至少一個**——分類器回空清單是失敗而非「判不出來」，
          見 `BR2.4`。
      - name: scoresAvailable
        logical_type: boolean
        required: true
        derived: true
        description: >
          衍生值：是否每一個候選都帶 `score`。**它決定述詞走哪一個求值分支**，
          而不是由設定或模型名稱決定——分支由資料本身決定，使 `OQ-10` 的兩種
          結論都不需要改述詞。
    entity_constraints:
      - id: EC1
        statement: "`candidates` 不得為空。"
        why: "空清單不是『判不出來』——判不出來是『有多個候選但選不出一個』。把兩者混為一談會讓分類器失敗被當成正常的反問路徑。"
      - id: EC2
        statement: "`scoresAvailable` 為真 ⟺ 每一個候選的 `score` 皆非 null。**不得有部分帶分數的清單**。"
        why: >
          混合清單無法定義一致的比較。若模型只對部分候選給分，本單元**整張清單
          視為無分數**（`scoresAvailable = false`），而不是對有分數的那幾個用門檻。

  - name: ClassificationResult
    summary: >
      一次分類的完整結果：**N 個意圖槽位**，每個槽位一張自己的候選清單。
      修訂 1 新增（審查 `R-01`）。本單元內部，不出現在 `K-10` 的線上形狀。
    identifier: null
    attributes:
      - name: slots
        logical_type: "ordered list<CandidateRanking>"
        required: true
        min_size: 1
        description: >
          **一個槽位 = 一件使用者要系統做的事**。一句單意圖輸入產生 1 個槽位；
          `FR5.1` 的「改架構圖加 Redis 快取，然後估一下成本差額」產生 **2 個**。
          排序沿用輸入中出現的先後，**但不附帶執行順序或依賴**（`BR4.3`）。
    entity_constraints:
      - id: EC6
        statement: >
          **槽位與候選是兩個不同的軸，不得壓成一張清單。** 同一槽位內的
          `CandidateIntent` 是**互斥**的（對這件事的幾種讀法，只能選一個）；
          不同槽位之間是**並存**的（兩件事都要做）。
        why: >
          這是 `R-01` 的 Critical。原設計只有一張 `CandidateRanking`，而
          `BR3.2` 的述詞只看 `candidates[0]`、`BR3.5` 只說「`intents` 非空」——
          把 `FR5.1` 的官方可測不變量（`requirements.md:176` 逐字：改圖＋估成本
          **應產生 2 個**）代進去，最直覺的實作（`intents=[candidates[0]]`，
          因為同槽位候選本來就互斥）會**靜默丟掉第二個意圖**，而 `US5.1` 在
          追溯表上仍標 `OK`。兩個軸必須在型別上分開，才不會靠實作者猜。

  - name: IntentDecision
    summary: 本單元對外的判定結果。**欄位集合由 `K-10` 固定，本站不改。**
    identifier: null
    attributes:
      - name: intents
        logical_type: "list<Intent>"
        required: true
        description: >
          一句含 N 個可分離意圖者輸出 N 個（`FR5.1`）。**基數不是自由的**：
          見 `EC7`——每個槽位恰好貢獻一個 `Intent`，取該槽位 `rank == 1` 的候選。
          任一槽位不可單選時**整個清單必為空**（`EC4` ＋ `BR4.2`）。
      - name: confidence
        logical_type: "float"
        pending: true
        pending_owner: "nfr-requirements（3.2，連同 OQ-4 與 OQ-10 一併決定）"
        required: true
        description: >
          **型別照 `K-10` 原樣轉錄，本站不改**：`contract-summary.md:761` 逐字
          「`float`，定義域 0–1」，**無 null**。`OQ-10` 若結論為「無可用信心訊號」，
          此欄位語意（含是否可為 null）須改寫，而**改寫權明文屬 `nfr-requirements`**
          （`contract-summary.md:1424`）——本單元沒有 `OQ-N4`（`:1433`）那種逐字
          授權。故本站以 `pending: true` 標記待定、**不先行寫入具體型別**（`R-02`）。
          實作時若 `OQ-10` 尚未定案，以契約型別 `float` 為準並讓缺值成為一個
          **顯式的失敗點**，而不是悄悄放寬成 nullable。
      - name: below_threshold
        logical_type: boolean
        required: true
        description: "由述詞 `can_single_out` 的否定填入，**不是**由 `confidence < 0.7` 直接算出（`[IR1]`=A）。"
      - name: candidates
        logical_type: "list<ClarifyCandidate>|null"
        required: false
        description: "`below_threshold` 為真時**必為非空**（`K-10` 逐字）。"
    entity_constraints:
      - id: EC3
        statement: "`referent` 為 `null` 時，必須能區分「這句話沒有指涉詞」與「有指涉詞但解析不出來」。"
        why: >
          後者是 `AC6.1.2` 的觸發條件（「指涉詞無法判定指哪一個 ⇒ 走反問路徑」），
          前者不是。兩者都用 `null` 表達會讓 `AC6.1.2` 不可構造。
          **處置**：以 `CandidateIntent.label` 之外的一個旗標區分，形狀留 `code-generation`；
          本站只鎖定「必須可區分」這個不變量。
      - id: EC4
        statement: "`below_threshold` 為真 ⇒ `intents` 為空 **且** `candidates` 非空。"
        why: "`FR1.3` 逐字「不得交辦、不得產生任何結果」。兩個欄位任一不符即違反。"
      - id: EC5
        statement: "`below_threshold` 為假 ⇒ `intents` 非空 **且** `candidates` 為空或 null。"
        why: "反向不變量。少了它，一個同時給出工作項與候選清單的回應會通過 `EC4`。"
      - id: EC7
        statement: >
          **`intents` 的基數規則（修訂 1 新增，審查 `R-01`）**：
          `below_threshold` 為假時，`len(intents)` **恰等於** `len(slots)`，
          且第 i 個 `Intent` 由第 i 個槽位 `rank == 1` 的候選轉成
          （`capability` 與 `referent` 逐欄複製）。
        why: >
          原設計只說「非空」，於是「輸出幾個」要靠實作者猜，而最直覺的猜法
          會丟掉第二個意圖。寫成等式之後它可被 property 直接斷言（見
          `functional-spec.md` §五 的 `P6`）。
      - id: EC8
        statement: >
          **`candidates` 的來源規則（修訂 1 新增，審查 `R-01`）**：
          `below_threshold` 為真時，`candidates` 是**所有不可單選槽位**的候選
          攤平後的清單；`ClarifyCandidate.label` 必須寫出它屬於哪一件事。
        why: >
          `K-10` 的 `ClarifyCandidate` 欄位集合固定為
          `{id, label, capability, confidence}`，**沒有槽位欄位**——多槽位同時
          不可單選時只能攤平，而攤平後使用者會看到一串來源不明的候選。
          `label` 是唯一能承載「這是在問哪件事」的欄位，故把它寫成不變量。
          **這條刻意不改 `K-10`**（本站無授權），而是在既有形狀內解決。

relationships:
  - from: CandidateRanking
    to: CandidateIntent
    cardinality: "1 — 1..N"
    kind: composition
  - from: ClassificationResult
    to: CandidateRanking
    cardinality: "1 — 1..N"
    kind: composition
    note: "一個槽位一張候選清單。單意圖輸入是 N=1 的特例，不是另一條路徑。"
  - from: IntentDecision
    to: ClassificationResult
    cardinality: "1 — 1"
    kind: "derived_from（本單元內部，不出現在 K-10 的線上形狀）"
    note: >
      述詞對**每一個槽位的 ranking** 分別求值，再依 `BR4.2` 聚合成整句判定，
      結果填入 IntentDecision。ClassificationResult 本身不送給 U13。
  - from: CandidateIntent
    to: "既有能力（A1／A3／C1 …）"
    cardinality: "1 — 1"
    kind: reference_by_enum
```

## 實體集合的人話摘要

本單元有**四個**實體（修訂 1 由三個增為四個），而中間兩個都是本站新增：
`CandidateRanking` 是 `[IR1]`=A 的全部重點，`ClassificationResult` 是審查
`R-01` 的處置。

- **`CandidateIntent`** 是一個候選判讀。它有 `rank`（**一定有**）與 `score`
  （**可能沒有**）。這個不對稱是刻意的：`OQ-10` 問的就是分數存不存在，而排序
  無論如何都存在——分類器總能給出「最可能的是這個」。
- **`CandidateRanking`** 是述詞的唯一輸入。它的 `scoresAvailable` 讓**資料自己**
  決定述詞走哪一個分支，而不是靠設定或模型名稱。這是 `[IR1]`=A 能在 `OQ-10`
  兩種結論下都不重寫的機制。
- **`ClassificationResult`** 是**槽位層**，修訂 1 新增。它存在的理由只有一個：
  **槽位與候選是兩個不同的軸**。同一槽位內的候選互斥（對這件事的幾種讀法），
  不同槽位之間並存（兩件事都要做）。壓成一張清單時，「輸出幾個 `Intent`」
  就沒有規則可循，而最直覺的猜法會丟掉第二個意圖——見 `EC6`。
- **`IntentDecision`** 是對 `U13` 的既有契約形狀，**欄位集合不動**。
  它的 `below_threshold` 由述詞（對全部槽位聚合後）的否定填入，
  `intents` 的基數由 `EC7` 鎖住、`candidates` 的來源由 `EC8` 鎖住。

**`EC4` 與 `EC5` 是一對**，而只寫 `EC4` 是不夠的：`FR1.3` 說「不得交辦」，
但沒說「交辦時不得同時附候選」。一個同時給出工作項與候選清單的實作在字面上
沒有違反 `FR1.3`，而它會讓畫面同時出現工作項與反問——`EC5` 是為了擋這個。
