# Business Logic Model — U-7 對帳 workflow 與編排器

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## 這個單元在做什麼

每天一次掃過全部 intent，把看板與 record 之間的落差**補平**，並產出一份說得出「補了幾筆、一致率多少、哪些沒補」的報告。

交付 `aidlc-sync-reconcile.yml` ＋ 其 `*-impl.yml` ＋ 編排邏輯（[ad:components.md] 的 C-7 `reconciler`）。複雜度 **L**，與 U-3 並列本 intent 最重的兩個單元之一。

**它與 U-6 的差別不是「做什麼」，是「為什麼」**：U-6 由事件驅動、只在有漂移時寫；本單元由排程驅動、**主動去找**漂移。兩者用同一組元件，但 U-6 的失敗是「這次沒同步到」，本單元的失敗是「**沒有人在看**」。

## 一輪對帳的序列

```
排程觸發（每日一次，cron 避開三個既有排程）
   │
   ├─► actions/checkout ref: ut（R-7.1——不釘就會讀到 main 的過期 record）
   │        └─► 記下 ut HEAD SHA，寫進報告（R-7.3）
   │
   ├─► reverse_pending（同 U-6 的 fail-closed：查不到即整輪中止）
   │
   └─► 掃 intents.json registry，讀 sync-state.json 取 binding；
       binding 為 null 者跳過（不計入分母）；已綁定者至多 reconcile_batch_size 個：
          │
          ├─ U-4 read_sync_state ──► SyncState（三欄 ＋ binding）
          │
          ├─ U-1 map() ──► reason_code 決定清單成員身分（R-1 群）
          │                   ├─ suppressed ──► awaiting_human（排除於分母）
          │                   ├─ parked ─────► parked（排除於分母）
          │                   ├─ unparseable ► unparseable
          │                   ├─ undecidable ► undecidable  ← G-1 新增
          │                   └─ whitelisted ► 不進任何清單
          │
          ├─ U-3 read_item ──► ItemState（看板現況）
          │      └─ 三方比對：看板 ／ Decision ／ SyncState
          │           ├─ 看板 == Decision
          │           │     ├─ SyncState == Decision ──► 一致，計入分母不計分子，不寫
          │           │     └─ SyncState != Decision ──► **遺失的回寫**（R-6.5）
          │           │              └─► U-4 write_sync_state（修復三欄
          │           │                    ＋ managed_block_hash ＋ last_synced_at，R-6.8）
          │           └─ 看板 != Decision ──► 補平：
          │                 U-3 write_status(expected = 剛讀到的 ItemState, desired = Decision.status)
          │                     ├─ Written ──► backfilled_count +1
          │                     │      └─► U-4 write_sync_state（R-6.1，回寫四欄）
          │                     └─ Aborted ─► aborted 清單，計入分子，**不回寫**（R-6.3）
          │
          ├─ U-3 read_issue_state ──► issue 關閉但 Status ≠ Done ► issue_status_mismatch
          │
          └─ U-4 commit_and_push（本 intent 至多一次，R-6.6）
                 └─► 推「從 ut 分叉的自建分支」（R-7.2），失敗 ──► U-5 notify，續跑其餘
   │
   └─► 產出 ReconcileReport（[req:FR-D4] 的可讀取指標，含 ut HEAD SHA）
```

文字 fallback：先把工作樹釘在 `ut`（排程只在預設分支 `main` 觸發，不釘就會拿過期的 record 對帳且不會有任何錯誤），記下該版本的 SHA；接著取得暫停清單（取不到就整輪中止）；然後掃 registry，跳過未綁定者，對每個已綁定 intent 讀狀態檔與看板現況，把「看板／本輪判定／狀態檔」三者一起比：看板已等於判定時，若狀態檔卻不等於，那是 U-6 遺失的回寫，就地修復；看板不等於判定時補平，補平用的 `expected` 取自**剛讀到的看板現況**，寫成功才回寫狀態檔、`Aborted` 則列入清單且不回寫。另外檢查 issue 開關與 Status 是否相稱。每個 intent 至多推送一次，推送落點是從 `ut` 分叉的自建分支。最後產出報告。

> **這張圖與 fallback 於 2026-08-30T01:31:09Z 整組重畫（reviewer iteration 4 Group A C-4／C-5，兩項皆 Critical）。**
>
> 1. **C-4：Q5=A 的整個承接零傳播。** `business-rules.md` 新增了 R-6 群（補平後回寫 `SyncState`）與 R-7 群（分支落點），而本檔的序列圖、fallback、與上游對應三處**完全沒提**。這與 iteration 3 判給 U-6 的 C-2 是同一個形狀（改了規則沒改圖），且落在本輪唯一的核心修法上。
> 2. **C-5：本單元的 `expected` 來源全單元未定義。** 本單元是 `write_status` 的具名呼叫者，但圖上只寫「補平（write_status）」，沒有任何規則說 `expected` 從哪來。圖上唯一能推得的來源（剛做的 `read_item`）正是 iteration 3 判 C-1 的**恆真形狀**。
>
> **本單元的 `expected` 為什麼可以取自剛讀到的 `ItemState`，而 U-6 不行**：兩者的守門目的不同。U-6 要偵測「**我上次寫進去之後**有沒有別人動過」，基準必須是它自己上次寫的值（`SyncState`）。本單元是**對帳**——它要的是「我讀到的當下狀態到我寫入之間有沒有人插隊」，那是一個**單輪內**的樂觀鎖，基準本來就該是剛讀到的值。**兩者不是同一條規則的兩種取法，是兩個不同的問題。** 本單元的 `Aborted` 因此仍然可達（並行的 U-6 事件寫入會觸發它），`ReconcileReport.aborted` 與 [req:FR-C3] 在本側成立。

> **序列圖補上「已綁定」過濾（reviewer iteration 1 Major，2026-08-29T15:26:25Z）。** 先前的圖從「掃 registry」直接進入 `U-1 map()`，缺少 [req:FR-D2] 要求的過濾步驟，而 `map()` 的判定規則**沒有任何一條檢查 `binding`**——未綁定的 intent 會被送進判定並產生一個沒有 item 可比對的結果。
>
> **正確的序列**：掃 registry → **對每個 intent 讀 `sync-state.json` 取 `binding`；`binding` 為 `null` 者跳過（不是錯誤，是尚未首建，屬 U-6 的首建路徑）** → 已綁定者才進 `U-1 map()`。跳過的 intent **不計入分母**（分母定義為「已綁定的 intent − …」，見 R-2.1）。

## 缺口 G-1 在此關閉

units-generation 標出：[US:S-2 AC 4] 要求對帳報告有「無法判定」清單，而 `ReconcileReport` 只有 `unparseable`；**兩個 `reason_code` 不能互相頂替**。

本單元加入 **`undecidable: [intent_id]`**。核心理由不是「欄位少了一個」，是**兩者的處置不同**——`unparseable` 要修 record、`undecidable` 要修對照表。完整說明見 `domain-entities.md`。

> **這個缺口曾經有落空的風險**：G-1 指派給 `functional-design`，而該 stage 是 **CONDITIONAL 且 per-unit**——U-7 這一輪若被判「無新資料模型」而 skip，修補會連帶被跳過。本輪的 CONDITIONAL 判定為 **EXECUTE**（`ReconcileReport` 確為新資料模型），風險未實現。

## 一致率的分母與批次上限之間有一個交界

`business-rules.md` 的 R-3.4 記載：**若批次上限真的會被觸發，而報告無法區分「本輪未處理」與「已處理且一致」，一致率就會失真**——分母把未處理的也算進去了。

上游沒有寫這一項，因為兩條規則來自不同的 AC（分母定義來自 [US:S-9 AC 1]、批次上限來自 [US:S-7 AC 3]），**各自都對，合起來才顯出問題**。

**本站不裁定具體形式**（取決於 PRE-1 第 2 項實測 C-T5 後，批次上限是否真的會被觸發），但把交界寫下來。

## 錯誤處理

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| `reverse_pending` 查不到 | **整輪中止**，紅燈 | R-4.2（同 U-6 的 fail-closed） |
| 單一 intent 的 API 失敗 | **不中止整輪**，計入報告後續跑 | R-4.1（[ad:component-methods.md] 逐字） |
| 補平時回讀不符 | `Aborted` → `aborted` 清單，計入分子 | R-1 群、[req:FR-C1] |
| 超出批次上限 | 本輪不處理，下一輪涵蓋 | R-3.1；**但見 R-3.4 的交界** |

**R-4.1 與 R-4.2 的分界是影響範圍，不是嚴重度**——與 U-6 的同一條分界一致。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| `reason_code` 為 `whitelisted` | **不進任何清單** | [US:S-3 AC 6] 明文，非遺漏 |
| `reason_code` 為 `undecidable` | 進 `undecidable` 清單，**計入分母與分子** | R-1／R-2（G-1） |
| 某 intent 同時 `Parked` 且看板不一致 | 進 `parked`，**排除於分母** | R-2.1（機制刻意不動，非放棄擔保） |
| 對帳與事件同步同時在跑 | **可並行**，各自 concurrency group | [req:NFR-P3] |
| 補平成功 | **不通報、不紅燈** | [US:S-7 AC 5] |
| 單一 intent 的 `ExternalError` | 續跑其餘 **＋ 通報（C-5）** | [req:FR-E1]、[US:S-8 AC 1] |
| 迴圈結束後 | 呼叫 **C-5 `resolve_if_open`** 關閉已不再成立的通報 issue | U-5 的 J-2；同 U-6 的 R-6.1 |

> **上面兩列是 reviewer iteration 1 Major 的補正（2026-08-29T15:26:59Z）。** 本單元先前的錯誤表與「與上游的對應」段**完全沒有提到 C-5**，但 [ad:components.md] 把 reconcile 的元件集合定為 `C-7 →（內部）C-2／C-1／C-3／**C-5**`——C-5 一直在集合裡，只是本單元從未寫下何時呼叫它。
>
> 第二列同時承接 U-5 的缺口 J-2（`resolve_if_open` 先前沒有任何呼叫者）：U-6 每輪事件觸發時關一次，本單元每日全掃時再收一次殘留。

## 與上游的對應

`reconcile` 的契約、`ReconcileReport` 與批次上限引自 [ad:component-methods.md] §C-7；S-B 的生命週期與並行性引自 [ad:services.md]；兩類排除引自 [ad:decisions.md] ADR-A5；元件分層與 reconcile 的元件集合（含 C-5）引自 [ad:components.md]；`notify`／`resolve_if_open` 的契約引自 U-5 的 `business-logic-model.md`；[req:FR-C1]／[FR-D1]／[FR-D3]／[FR-D4]／[NFR-O1]／[NFR-O2]／[NFR-P3] 引自 `requirements.md`；[US:S-2 AC 4]／[US:S-3 AC 6]／[US:S-7]／[US:S-9] 引自 `stories.md`；G-1 的來源、指派與 CONDITIONAL skip 風險引自 [ug:unit-of-work.md] 與 [ug:unit-of-work-story-map.md]；`ReasonCode` 引自 U-1 的 `domain-entities.md`；`reverse_pending` 的 fail-closed 引自 U-6 的 `business-rules.md`。

**本檔對上游的補充**：`undecidable` 欄位（G-1 的關閉）與分母／批次上限的交界（R-3.4）。**一致率的兩類排除、`reconcile` 的簽章、單一 intent 失敗不中止整輪一字未改。**

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:14:17Z
**Iteration**: 1

### 對指定重點的逐項核對

**1. 缺口 G-1 的關閉（(a)(b)(c) 三項）**

- **(a) [US:S-2 AC 4] 原文核對**：`stories.md` AC 4 逐字為「該 record 出現在對帳報告的**『無法判定』**清單中」，與 S-3 AC 6 的「進『無法解析』清單」用字不同（分別對應 `undecidable` 與 `unparseable`）。`domain-entities.md` 的主張成立。
- **(b) `undecidable` 與 `unparseable` 不能互相頂替的論證**：`component-methods.md` 定義 `Unparseable`（C-2 `parse` 的失敗輸出）與 `reason_code="undecidable"`（C-1 `map` 對**已解析成功**的訊號組合找不到對應列）是不同階段、不同輸入的兩件事，`domain-entities.md` 的處置表（誰的問題／要修哪裡）成立，論證站得住。
- **(c) `undecidable` 的可達性（**最重要**）**：本輪逐一核對 `U-1` 的 `business-rules.md`（R-3.1–R-3.7）與 `domain-entities.md` 的 `checkbox` 值域。R-3.6（「無任何 in-scope stage 動過」＝全部落在 `{" ","S"}`）與 R-3.4／R-3.5（`"?"`／`{"-","R"}`）合起來窮盡了 `{" ","S","?","-","R"}` 五個值，唯一未被覆蓋、會落到 R-3.7（`undecidable`）的組合是「至少一個 in-scope stage 為 `"x"`，且無任何 stage 為 `"?"`／`"-"`／`"R"`，且 `runtime_status ≠ "Completed"`」——這正是 `stories.md` S-2 AC 15 明文舉出且描述為「**gate 核可後到下一個 stage 起跑之間的窗口，也是 `--single` 模式的常態**」的真實可達狀態，不是自相矛盾的死碼（與本 intent 先前的 `functional-design:c10` 前例——`pending_reverse` 規則因騎在唯一寫入路徑上而不可達——性質不同）。`component-methods.md` 對 [US:S-2 AC 15] 的官方解讀（「恰好輸出一個 Status **或**一個明確的不寫理由」）也印證「總函式性」指的是「Status∪明確不寫理由」的總函式，`undecidable` 正是完成這個總函式的窮盡分支，與「對照表是總函式」不矛盾。**本項核對通過，G-1 的關閉在機制上成立。**

**2. R-3.4（本站新增）**

- 與 [req:FR-D3]／[FR-D4] 一致：FR-D3 只要求「上限存在且可調」、FR-D4 只要求「補平計數可讀取」，兩者字面都不禁止 R-3.4 描述的「未處理與已處理且一致無法區分」這個交集缺口，R-3.4 的推導（分母定義來自 [US:S-9 AC 1]、批次上限來自 [US:S-7 AC 3]，兩者疊加才顯出問題）站得住，屬本站正確發現的新缺口。
- 但「**本站不裁定具體形式**」在本 intent 沒有 G-1 那種乾淨的下游接手點——見下方 Major #3。

**3. 一致率的分母／分子定義 vs NFR-O2 逐字比對**

- **排除（分母）兩類維持**：`requirements.md` NFR-O2「分母 = 已綁定的 intent − 有未處理反向紀錄者 − `Parked` 非空者」與 R-2.1 逐字一致；R-2.3「不得擴為三類排除」與 ADR-A5 的 Alternatives Rejected 一致，**排除類別數未被本站擴大**。
- **但分子（「計入」類）的擴張未被追蹤到——見下方 Major #4，這是本輪查證中發現的實質問題，不是單純的文件用字問題。**

**4. 報告清單欄位數**

- 自行重算：`ReconcileReport` 的清單型（`[intent_id]`）欄位為 `awaiting_human`／`parked`／`aborted`／`unparseable`／`issue_status_mismatch` 五個（`component-methods.md` §C-7 原文），加 `undecidable` 為六個，`functional-design-questions.md` 的「原五份＋undecidable＝六份」核算無誤。與 [US:S-9 AC 2] 明列的「等待人工裁決、已暫停、回讀不符已中止」三份**具名**清單確為不同的量（後者是前者的子集且用途不同：AC 2 只鎖定三個特定清單需獨立列出，不是清單總數），本站的「不可混用」提醒成立，未發現混用。

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
|---|---|---|---|---|
| 1 | Critical | `domain-entities.md:19`（`latency_samples` 欄位）、`business-logic-model.md:13-38`（一輪對帳的序列圖） | `domain-entities.md` 明文將 `ReconcileReport.latency_samples` 定義為「NFR-P1 的量測樣本」，而 NFR-P1／[US:S-9 AC 6] 量測的是「**事件觸發**同步」的『push 完成 → 看板 Status 更新』間隔（`stories.md` S-9 AC 6 逐字：「連續 20 次**事件觸發**的同步」）。U-7 是**每日排程**執行的批次工作，其序列圖（本檔 13-38 行）從頭到尾沒有任何步驟讀取或計算「push 完成時間」；且核對 `sync-state.json` 的完整 schema（U-4 `domain-entities.md`：`schema_version`／`binding`／`last_status`／`last_field_value`／`last_reason_code`／`managed_block_hash`／`last_synced_at`／`pending_reverse`）**不存在任何欄位記錄「push 完成時刻」或「事件觸發延遲」**，U-6 的 `business-rules.md` 與 `services.md` 的 S-A 定義也都沒有描述寫入這類延遲樣本。也就是說：`ReconcileReport.latency_samples` 這個欄位被 U-7 宣稱承載 NFR-P1 的量測，但**沒有任何已核可或本站自己的機制能把事件路徑的延遲資料送進這個每日批次任務**——這不是「留給 construction 決定怎麼量」的實作細節，是欄位語意在本單元的資料流下缺乏可行的填值路徑，屬於「規則描述的狀態不可達」同型缺陷（`project.md` 的 `functional-design:c10`），但這次落在輸出欄位而非狀態判定。開發者依本檔實作 `reconcile()` 時，無法從 U-7 自己掌握的資料算出這個欄位該填什麼。 | 二擇一並修正：(a) 明確劃出 `latency_samples` 不屬本單元，NFR-P1／S-9 AC 6 的量測改由 U-6（S-A）自行記錄與暴露（例如寫進 workflow run 的自訂 metric 或另開一個小型量測產出），`ReconcileReport` 移除該欄位或改記本單元自己有意義的量測（如「本輪處理每個 intent 的耗時」）；(b) 若堅持由 `ReconcileReport` 承載，須在 U-6／U-4 補上「事件觸發時刻」的儲存機制（如 `sync-state.json` 新增欄位，或 U-6 直接把單次延遲寫進一個共用產出），並在本檔的序列圖明確畫出 U-7 從哪裡讀到這批樣本。 |
| 2 | Major | `business-logic-model.md:20-27`（序列圖：`掃 intents.json registry...` 直接進入 `U-1 map()`） | [req:FR-D2] 明文「對帳的處理清單等於『record 內存在 FR-A2 綁定編號』**且**『Parked 欄位為空』的 intent 集合」，`services.md` S-B 行也寫「掃描全部**已綁定**且未 park 的 intent」。但本檔序列圖從「掃 registry」直接進入「U-1 `map()`」，中間沒有任何「過濾未綁定 intent」的步驟；核對 U-1 的 `business-rules.md` R-3.1–R-3.7（判定順序）與 `domain-entities.md` 的 `ParsedRecord.binding` 欄位，**`map()` 的七條判定規則沒有一條檢查 `binding`**——`parked`（R-3.1）有明確的排除路徑，但「未綁定」沒有對應規則。若照本檔序列圖字面實作，`map()` 會對未綁定的 intent 照常算出一個 Status，接著序列圖的下一步「U-3 `read_item`」（`component-methods.md` §C-3：`read_item(binding, Config) -> ItemState`）需要一個 `binding` 參數卻沒有——這是一個真正會在實作時卡住、需要回頭問設計者「未綁定的 intent 該在哪一步被擋下」的缺口，不是可以憑常識填補的細節。 | 在序列圖的「掃 registry」與「U-1 `map()`」之間補一個明確的過濾步驟（例如：`read_binding(record_path) -> binding；binding == null → 略過，不計入分母分子，不進任何清單`），並在 `business-rules.md` 新增一條對應規則（可比照 R-3.1 的形式），使「已綁定」這個 FR-D2 明文要求的前提條件在 U-7 自己的規則清單裡可被追蹤，而不是隱含在序列圖的省略號裡。 |
| 3 | Major | `domain-entities.md:40-45`（一致率的兩類排除）、`business-rules.md:24-34`（R-2 群） | `business-rules.md` 在標題「R-2 群：一致率（**維持上游**）」下，把 `unparseable`／`whitelisted`（連同新增的 `undecidable`）都判為「計入分母✅ 計入分子✅」（R-1 群表格），但逐字核對其唯一引用的上游依據——`component-methods.md` §C-7「一致率」段與 `decisions.md` ADR-A5——**兩者都只討論 `aborted`** 是否計入分子，完全沒有提到 `unparseable` 或 `whitelisted` 該如何計入。這不是文件用字問題：ADR-A5 把 `aborted` 計入分子的理由是「那些 item 的看板值是機制自己判定**無法擔保**」——`aborted` 之所以能被判定「不一致」，是因為 `map()` **確實算出了一個期望 Status**、C-3 寫入前回讀時發現看板現值與期望不符。但 `unparseable`／`whitelisted` 的情形是 `map()` **從未算出任何期望 Status**（`unparseable` 連 `parse()` 都失敗；`whitelisted` 是已知結構性例外，刻意不寫），此時「看板與 record 是否一致」根本沒有可比較的基準值——把它們計入「看板與 record **不一致**者」（NFR-O2 的分子定義原文）在語意上站不住。這個延伸還有一個本檔完全未揭露的後果：`260802-default` 目前在白名單中（`requirements.md` FR-J5），依本檔的規則它會**永久**計入分子，使 NFR-O2 明文的「目標為 0」在該 record 被移出白名單或修好前**結構性不可達**——這正是 `project.md`（`refined-mockups:c4`）要求「承認某組合是已知風險時必須把最壞情境實際畫進範例再判定可否接受」的情境，本檔未做這個判斷就把延伸範圍寫成「維持上游，本站不動」。 | 二擇一：(a) 把 `unparseable`／`whitelisted` 移出分子（維持在分母內或另議），只讓有真實「期望值 vs 實際值不符」的 `aborted`／`undecidable`（`undecidable` 雖無 Status 期望值，但至少代表 `map()` 已嘗試判定而失敗，性質更接近 `aborted`，可個案論證）計入分子；(b) 若堅持全部計入，須明確補一句「本延伸超出 ADR-A5 原範圍，是本站新的解讀」而非「維持上游」，並在文件中具體算出並承認「至少 1 筆（`260802-default`）之數字使一致率的分子恆不為 0」這個後果，讓下游知道這是刻意接受的殘留代價而非疏漏。 |
| 4 | Major | `business-rules.md:44`（R-3.4）、`functional-design-questions.md:28-34` | R-3.4 是本站自行發現的真實缺口（分母定義與批次上限交界），但「**本站不裁定具體形式**」在本 intent 沒有像 G-1 那樣的乾淨下游接手點：G-1 由 `unit-of-work.md` 在 units-generation 階段就明確「指派 functional-design」並寫出具體修法（增設 `undecidable` 欄位）；R-3.4 則是 functional-design **自己**在執行中發現、自己延後決定，且未指名任何具體 stage／owner／觸發時機來拍板「`deferred` 欄位要不要加」。核對 `delivery-planning/bolt-plan.md` 的 Bolt 2 DoD（「PRE-1 第 2 項……已綠並反映在 [US:S-7 AC 3] 的上限設定」），該文件是在本次 functional-design 之前就已核可，**完全不知道 R-3.4 的存在**，不會自動把「PRE-1 第 2 項出爐後要不要動 `ReconcileReport` schema」納入 Bolt 2 的 gate 檢查項。若無人明確承接，實作 code-generation 時會遇到一個業務規則清楚寫著「有這個問題」卻沒有寫「要不要修、誰來拍板」的規格，正是本審查準則「開發者能否在不問架構師的情況下實作」的失敗案例。 | 明確指定一個具體落點與觸發時機，例如：「PRE-1 第 2 項實測結果出爐後，若批次上限確實會在現有 6 個 intent 規模下於可預見時間內被觸發，由 Bolt 2 的 gate（`bolt-plan.md` 已列的 PRE-1 第 2 項檢查）一併判斷是否需要在 `ReconcileReport` 補 `deferred` 欄位；若判斷需要，此為對已核可 `component-methods.md` 型別的擴充，須在 Bolt 2 的 PR 說明中一併記載，不隱含在既有 schema 變更流程之外」，並在 `bolt-plan.md` 或本檔任一處留下可被下一個讀者找到的觸發指標，而非只停在「不裁定」。 |
| 5 | Minor | `business-logic-model.md:31-33`（補平 → `write_status`）；跨 `U-4 domain-entities.md`／`U-6 business-rules.md` | 本檔（與 U-6 的 `business-rules.md`）都沒有描述：U-7 透過 C-3 `write_status` 成功補平之後，是否／如何呼叫 C-4 的 `write_sync_state` 更新 `sync-state.json` 的 `last_status`／`last_reason_code`／`last_synced_at` 等欄位。`services.md` 明文「S-A 比對的是 `sync-map` 判定結果 vs **本地快取**的 `sync-state.json`」——若 U-7 補平後這份快取沒有同步更新，U-6 下一輪event-triggered 執行會拿著過期快取誤判「仍有漂移」而重新嘗試寫入，其 C-3 `write_status` 的「必先回讀」比對用的 `expected` 若也源自這份過期快取，將與 U-7 剛寫入的真實看板值不符而觸發假性 `Aborted`（進而依 FR-C1 開一則不必要的 issue）。此為「狀態欄位三問」（誰寫／誰讀／誰清）在 `sync-state.json` 的快取欄位上未被回答的一例，但 U-6 的 `business-rules.md` 同樣沒有處理這個角落（U-6 自己寫入後是否更新快取也未寫明），故判為 Minor 而非 Major——這是兩個服務類單元共有的缺口，不是 U-7 獨有的設計錯誤。 | 在 R-4 群或「與上游的對應」補一句：補平成功（`Written`）後是否呼叫 `write_sync_state` 寫回 `last_status`／`last_reason_code`／`last_synced_at`；若答案是「否，因為 S-B 的判定是即時回讀而非依賴快取」，則需同時確認 U-6 是否會因此在下一輪把 U-7 剛修好的值誤判為漂移，並把此結論記入本檔。 |
| 6 | Minor | `functional-design-questions.md:16-34`（本站裁定，未經人工提問） | 本檔記載「使用者在本 session 中止一次 AskUserQuestion 並輸入『continue』」作為 G-1／R-3.4 兩項自行裁定的授權來源，時間戳標註「讀自 date -u」。本輪審查範圍內可讀的檔案（`functional-design-questions.md` 本身）沒有可佐證此事件的來源（`memory.md`、audit shard 不在本次審查的可讀清單內），故本項**無法被本輪獨立驗證**，但也未發現與已讀內容矛盾之處；且兩項自行裁定的內容本身經查證都站得住（G-1 是落實 units-generation 已核可的指派，R-3.4 明確標示「不裁定具體形式」未逾越自行裁定的合理邊界）。鑑於本 intent 過去多次因時間戳／人工確認的可驗證性問題被判定嚴重缺陷（`project.md` 的 `user-stories:260822-us-L1`／`L2`／`L3`），僅此一點記為 Minor 提醒：建議下一輪由持有更廣讀取範圍的一方（conductor 或下一位 reviewer）核對 audit shard 是否確有對應的人工 `continue` 事件。 | 請 conductor 在下一次核可前，核對 `<record>/audit/` 或 `functional-design/memory.md` 是否記載了此次「continue」事件，並在 stage summary 中確認；若能確認，此項可在下一輪標記為已驗證並移除。 |

### Summary

G-1 缺口關閉的核心論證（本輪最重點核對的可達性問題）站得住：`undecidable` 是真實可達、非死碼的狀態，[US:S-2 AC 4]／[AC 15] 與 U-1 的判定規則之間沒有矛盾。但本輪查證發現一個 Critical（`latency_samples` 欄位語意在本單元的資料流下無法被填值，NFR-P1／S-9 AC 6 的量測機制實質缺失）與三個 Major（對帳流程缺「已綁定」過濾步驟、一致率分子把 `unparseable`／`whitelisted` 併入「不一致」卻缺乏語意基礎且未揭露其令 NFR-O2「目標為 0」永久不可達的後果、R-3.4 的「不裁定具體形式」沒有指定下游接手點）——這些都是開發者依本檔實作時會實際卡住、需要回頭問架構師的缺口，不是可被文件潤飾解決的措辭問題，故判定 NOT-READY。

## Review (Iteration 2)

**Verdict**: READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T16:13:50Z
**Iteration**: 2

### 查證方法

本輪為驗證輪，範圍限定為 iteration 1 的六項發現（1 Critical、4 Major、1 Minor）是否落地，並對本輪修正動作本身做「有沒有引入新問題」的查證。逐字重讀 U-7 全部四份產出（`business-logic-model.md`／`business-rules.md`／`domain-entities.md`／`functional-design-questions.md`）；依 dispatch 的承接落點清單開檔核對 U-6 的 `business-rules.md`（R-6.1／R-5 群／R-7 群）／`business-logic-model.md`（錯誤表）、U-3 的 `domain-entities.md`（`read_issue_state` 的擁有者）；核對上游 `application-design`（`components.md`／`component-methods.md`）、`requirements.md`（NFR-O2 逐字）、`stories.md`（S-2 AC 4、S-9 AC 1/2/3/5/6）、`delivery-planning/bolt-plan.md`（Bolt 0～3 的 DoD 全文，含 PRE-1 表）。

### 逐項查證表

| # | 查證項 | 結果 | 依據 |
|---|---|---|---|
| 5 | `latency_samples` 的處置（標為填不出值＋兩條修法＋Bolt 2 gate＋不得冒充） | **通過**。`domain-entities.md:19,40-46` 已把欄位標為「本單元填不出值」並附完整推導：NFR-P1／S-9 AC 6 量測的是事件觸發路徑（U-6）的延遲，核對 U-6 全份 `business-rules.md`／`business-logic-model.md`（本輪已重讀）確認其序列圖與規則群皆無「push 完成時刻」的擷取或儲存步驟，此結論站得住；兩條修法（移轉擁有權予 U-6／或於 `SyncState` 新增觸發時刻欄位）具體可行；「在修正落地前不填此欄位，且不得以本輪執行耗時冒充」是正確的保守處置。**唯一的殘留**：`bolt-plan.md` 的 Bolt 2 DoD（:59）未見對應追蹤行，與 K-1／NFR-S1 在 Bolt 0 PRE-1 表已落地的深度不同——但本項使用了正確的「標出不逕改」措辭（:44），未過度宣稱，判 Minor 而非 Major，見下方「新引入的問題」 | `domain-entities.md:19,40-46`；`bolt-plan.md:54-60` |
| 6 | 序列圖補上「已綁定」過濾後，與 R-2.1 的分母定義是否一致 | **通過**。`business-logic-model.md:42-44` 新增的過濾步驟明確寫「跳過的 intent 不計入分母（分母定義為『已綁定的 intent − …』，見 R-2.1）」，逐字核對 `business-rules.md:28`「R-2.1｜分母 = 已綁定的 intent − awaiting_human − parked」與 `stories.md` S-9 AC 1（k 個已綁定 intent 起算）三處定義一致。**附帶觀察（Minor）**：過濾步驟插入「掃 registry，至多 `reconcile_batch_size` 個」與「已綁定者才進 `map()`」之間的確切次序未明寫——若批次上限套用在**含未綁定項的原始 registry 掃描**上，未綁定項會佔用批次名額但不產出任何清單成員，可能讓實際處理的已綁定 intent 數少於批次上限；若套用在**已過濾的已綁定集合**上則無此問題。兩者對 [req:FR-D2]「處理清單＝已綁定且未 park」的字面同樣成立，但影響批次涵蓋率。目前 registry 僅 6 個 intent，實務影響低，且與已標出的 R-3.4（deferred 可辨識性）同屬一類尚待 PRE-1 第 2 項實測後才具體化的問題，不獨立列為 Major | `business-logic-model.md:13-44`；`business-rules.md:56-58`（R-3.1/R-3.2） |
| 7 | 分子擴張的後果揭露＋指派 requirements-analysis 的 NFR-O2 列，是否為恰當處置 | **揭露本身確實、論證站得住，但指派的落地深度不足**。`business-rules.md:34-38` 的分子擴張說明——把 `unparseable`／`whitelisted` 併入分子會讓 `260802-default`（已核實在白名單，`requirements.md` FR-J5）使分子恆 ≥ 1，令 NFR-O2「目標為 0」結構性不可達——邏輯正確、已具體算出後果，比 iteration 1 時的「維持上游，本站不動」有實質進步。但**與本專案對同等分量問題的既有處置基準（K-1）相比明顯較弱**：K-1 同樣是「已核可需求文件的驗收準則與設計矛盾」，最終走了正式 ADR（ADR-0014）流程，使 `requirements.md` 的 NFR-S1 拿到一則指向 ADR 的可追蹤註記（`requirements.md:147`）；而分子擴張這裡只留一句「指派 requirements-analysis 的 NFR-O2 列，確認人為 Bolt 2 的 gate」在 U-7 自己的 `business-rules.md` 裡，**逐字核對 `requirements.md:154`，NFR-O2 列完全沒有任何註記、指標或指向本缺口的線索**——任何只讀 `requirements.md` 的人（含未來的 reviewer 或 Bolt 2 gate 執行者）無從發現這個已被證明的結構性不可達。這不是「延伸決策本身錯誤」，是**指派的可發現性弱於本專案已示範過的正規做法**，判 Major | `business-rules.md:24-38`；`requirements.md:154`；ADR-0014 對照 |
| 8 | R-3.4 的接手點指派（`bolt-plan.md` 的 Bolt 2 DoD）是否真的有名字了 | **指派本身有名字，但「已增列」的字面陳述與實際檔案不符**。逐字核對 `bolt-plan.md` 的 Bolt 2 段落（:54-60），Definition of Done 一行原文為「U-7 完成判準通過；PRE-1 第 2 項（單次操作上限實際值）已綠並反映在 [US:S-7 AC 3] 的上限設定；`stories.md` 全域 DoD 的排程不衝突...成立」，**沒有任何一句提及「今天沒處理到」／`deferred`／R-3.4**——與同一小節內 G-1 的處置（:60 明文「本 Bolt 的 gate 必須確認它沒有被跳過」）形成對照。`business-rules.md:60` 的原句「**明確指派**：`delivery-planning/bolt-plan.md` 的 Bolt 2 DoD **增列一條**『對帳報告能區分...』」讀起來像是已對 `bolt-plan.md` 動筆，但查證後並未發生；且與本專案對同類情境（K-1、U-6 的 R-6.2、U-5 對 U-8-C5 的指派）一律使用的「**標出不逕改**」明文聲明**不同**——那三處都清楚寫出上游未被本站編輯，本處沒有。「接手點現在有名字了」這句話因此有誤導性：名字目前只存在於 U-7 自己的檔案裡，`bolt-plan.md` 本身無任何痕跡，與 iteration 1 原始建議「並在 `bolt-plan.md` **或本檔**任一處留下可被下一個讀者找到的觸發指標」的字面雖勉強滿足（本檔確有指標），但措辭已逾越「留下指標」進到「聲稱已編輯上游」，判 **Major** | `business-rules.md:52-64`；`bolt-plan.md:54-60` |
| 9(a) | [US:S-9 AC 5] 原文是否真的要求 R-4 群所述的偵測 | **通過**。`stories.md:267` 逐字：「一個已綁定的 intent，其對應 issue 已被關閉而其 item 的 Status 不為 `Done`，When 對帳執行，Then 該 intent 出現在對帳輸出的『issue 與 Status 不相稱』清單中。僅偵測與列出，不關閉 issue、不改寫 Status。」與 `business-rules.md:40-48` 的 R-4 群逐字對應，`read_issue_state(binding) -> "open"|"closed"`（C-3，見 `component-methods.md:91`）的孤兒契約判斷（「全 intent 的 functional-design 產出中只有擁有者 U-3 提到它」）在本輪可查核的範圍內（U-3 `domain-entities.md`、U-6 全份）成立——兩處均未見該方法的呼叫者 | `stories.md:267`；`component-methods.md:91`；U-3 `domain-entities.md` |
| 9(b) | R-4.3「issue 已關閉不影響一致率分母與分子」的正交論證是否成立 | **通過**。R-4.3（`business-rules.md:48`）與同檔 R-1.2（:22，「`issue_status_mismatch` 是正交維度，不參與一致率計算」）互相印證；AC 5 本文「僅偵測與列出，不關閉 issue、不改寫 Status」未賦予該狀態任何影響一致率的語意，論證站得住，未發現與 `resolve_if_open`（不同的 issue：通報 issue 而非綁定 issue）或其他規則的交叉污染 | `business-rules.md:40-50`；`stories.md:267` |
| 10 | 本輪新增的 `functional-design-questions.md` 是否比照 U-6／U-8 的揭露格式 | **部分可驗**。本審查範圍未含 U-6／U-8 的 `functional-design-questions.md`（不在 dispatch 承接落點清單內，依 reviewer 的跨單元查證邊界不逕行開啟），僅能以 U-6／U-7 的 `business-rules.md`／`business-logic-model.md` 內反覆出現的揭露慣例（`> **[事項]（reviewer iteration 1 [嚴重度]，[時間戳]）。**` 起頭、附「標出不逕改」與具名確認人）為基準比對。U-7 本檔的「本站裁定（未經人工提問）」節（`functional-design-questions.md:16-34`）格式與此一致：清楚陳述授權來源（使用者中止提問並輸入 continue）、逐項標明「本站裁定，非人工裁決」與 `date -u` 時間戳、並列「送審前自檢六項」表。**未發現格式缺漏**，但如查證項 8 所述，R-3.4 段落本身在措辭精確度上弱於同檔 G-1 段落與 U-6／U-5 的對應段落 | `functional-design-questions.md` 全文 |

### 新引入的問題（本輪修正）

**Major #1**：R-4 群的規則編號在本檔內**重複且衝突**——`business-rules.md:40`「## R-4 群：`read_issue_state` 的承接」定義 R-4.1／R-4.2／R-4.3（`read_issue_state` 呼叫、closed 者列清單、正交性），這是本輪為回應「送審前自檢第 2 項」（`functional-design-questions.md` 未提及但表頭時間戳與 U-6 R-7 群同批，2026-08-29T15:28:15Z）新增的段落；但同檔 `:66`「## R-4 群：單一 intent 失敗不中止整輪」**已存在**且同樣使用 R-4.1（:70，「與 U-6 的 R-2.5...刻意不同」）／R-4.2（:72，「本單元同樣需要 `reverse_pending`...同樣適用 U-6 的 fail-closed」）——**兩組完全不同語意的規則共用同一組編號**。`business-logic-model.md` 的錯誤表（:62-69）引用「R-4.2（同 U-6 的 fail-closed）」與「R-4.1（[ad:component-methods.md] 逐字）」時，意圖指向的是**第二個** R-4 群，但單純以編號在 `business-rules.md` 內搜尋 `R-4.1`／`R-4.2` 會先命中**第一個**（`read_issue_state`）群，語意完全不同——這正是 `project.md`（`units-generation:260822-ug-L1`／`260822-ug-L2`）反覆強調「拆分或新增被計數的實體時，編號本身就是受影響事實，須逐一核對」的具體案例，本輪修正新增 R-4 群時未檢查既有編號空間已被佔用。**建議**：把新增的 `read_issue_state` 承接群重新編號（例如併入 R-1 群後方成為 R-1.3～R-1.5，或獨立編為 R-6 群，避開既有的 R-3／R-4／R-5），並同步檢查 `domain-entities.md`／`business-logic-model.md` 有無引用到衝突編號。

**Major #2**：見查證項 8——R-3.4 對 `bolt-plan.md` 的「明確指派...增列一條」措辭與實際檔案內容不符，且未使用本專案對同類情境已建立的「標出不逕改」慣用語，構成本輪修正過程中新產生的可驗證性缺口（K-1 型過度宣稱的同型復發，儘管幅度較小）。

**Minor（延續，非新增）**：查證項 6（批次上限與已綁定過濾的次序未明寫）、查證項 7（NFR-O2 分子擴張的指派落地深度弱於 K-1 基準，惟已達 Major 門檻故已計入上方）。

### Summary

Iteration 1 的 Critical（`latency_samples`）與四個 Major 中的三個（G-1 可達性——iteration 1 已判通過、序列圖漏「已綁定」過濾、一致率分子擴張未揭露、R-3.4 無接手點）在本輪均得到實質修正：`latency_samples` 已誠實標為填不出值並具體指派；序列圖已補過濾步驟且與 R-2.1 分母定義一致；分子擴張的後果已具體算出並揭露。但本輪修正過程本身**新引入一個 Major**（R-4 群編號在同一檔案內重複且語意衝突，會讓依編號查找規則的開發者取得錯誤內容），並且對 R-3.4（Bolt 2 DoD）與分子擴張（NFR-O2）兩項的下游指派，其「已有接手點」的措辭與 `bolt-plan.md`／`requirements.md` 的實際內容有落差，其中 R-3.4 一項因缺少本專案慣用的「標出不逕改」揭露語而判為第二個 Major。總計 2 個 Major、0 個 Critical，未超過 READY 門檻（≤2 Major），但兩項 Major 均需在下一輪修正：(1) 重新編號 R-4 群避免衝突；(2) 為 R-3.4 補上「標出不逕改」措辭並以 `bolt-plan.md` 或本檔任一處更精確地表達「尚未落地、待 Bolt 2 gate 確認」的狀態，勿使用暗示已完成編輯的措辭。判定 READY（附帶必修事項）。

## Review (Iteration 3 — 驗證輪，契約端點與 ADR 承載)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T00:18:15Z
**Iteration**: 3
**涵蓋單元**: U-2 / U-5 / U-7 / U-11

### 逐單元判定

| 單元 | 判定 | 一句理由 |
| --- | --- | --- |
| **U-2** | **NOT-READY** | 3 Critical：`render()` 的輸出在全份已核可契約中**沒有寫入者**；`Block` 六欄無 `rejection_notice` 而 `domain-entities.md:48` 宣稱它「經由 `Block`」進雜湊；R-1.5 的「`null` 支逐字相同」與同批宣告的「須 bump `format_version`」不可同真。另 2 Major（`Context.scope_note` 在呼叫端不可達、第二批改動未傳播到同單元另兩份產出） |
| **U-5** | **READY** | 本單元四份產出無 Critical、無自身歸屬的 Major；iteration 2 兩項 Minor 未再惡化，ADR-0015 §5 的引用節號與內容逐字相符。惟其 §5／§8 兩處引用的**有效性**受下方 F5／F6 影響，且 §8 所涉的 `nfr-requirements/security-requirements.md` 不在 dispatch 可讀範圍、本輪無法查證 |
| **U-7** | **READY** | iteration 2 的兩項必修（R-4→R-8 重編號、R-3.4 措辭與承載）**皆已實質落地並經逐字複驗**；殘留為 1 Minor（R-3.4 仍把 `latency_samples` 當本單元在填的欄位）＋ 1 Minor（R-8 群插在 R-2 與 R-3 之間） |
| **U-11** | **READY** | iteration 2 唯一的新增 Minor（自相矛盾的 HTML 註記）已改寫正確；未修正的原 Minor（`REQUIRED_TEXT` 「已鎖住」措辭）依審查紀律不重提 |

**整組判定 NOT-READY**：任一 Critical 即整組 NOT-READY，U-2 有 3 個。

### 第一批查證：iteration 2 的必修事項

| # | 查證項 | 結論 | 依據（檔名:行＋引文） |
| --- | --- | --- | --- |
| 1a | U-7 Major #1：R-4 群撞號是否已解除，新編號在同檔內不撞號 | **通過** | `business-rules.md:40` 現為「## R-8 群：`read_issue_state` 的承接（…編號由 R-4 改為 R-8，因與既有 R-4 群撞號…）」，:46-48 為 R-8.1／R-8.2／R-8.3（**實數三條**）。同檔群序為 R-1(:5)→R-2(:24)→R-8(:40)→R-3(:52)→R-4(:67)→R-5(:75)，`R-8` 全檔唯一，R-6／R-7 未使用，無二次撞號 |
| 1b | 依編號的交叉引用是否指向正確的群 | **通過** | `business-logic-model.md:66-67` 的錯誤表引「R-4.2（同 U-6 的 fail-closed）」「R-4.1（[ad:component-methods.md] 逐字）」，現在唯一命中 `business-rules.md:67`「## R-4 群：單一 intent 失敗不中止整輪」下的 R-4.1(:71)／R-4.2(:73)，語意正確。`domain-entities.md:58` 的「`business-rules.md` R-3／R-4 群」指的是 **U-1** 的檔案（該句主語為 `ReasonCode` 的值域），非本檔，不構成誤指 |
| 2 | U-7 Major #2：R-3.4 是否改用「標出不逕改」且承載於 ADR-0015 §3；節號與內容是否相符 | **通過** | `business-rules.md:60` 現含逐字「**實際上沒有，該檔逐字重讀後無此條目**（reviewer iteration 2 Major）。`bolt-plan.md` 是已核可上游，**標出不逕改**」；:61「本項已由 **ADR-0015 §3** 承載」。開 `0015-…md:30-32`：「### 3. Bolt 2 的 DoD 增列一條／對帳報告須能區分「今天沒處理到」與「今天處理了且一致」（U-7 的 R-3.4）」——節號與內容逐字對應。並複驗 `bolt-plan.md:59` Bolt 2 DoD 確實仍無該條目，措辭與事實一致 |
| 3 | U-11 iteration 2 Minor #1：自相矛盾的 HTML 註記 | **通過** | `business-logic-model.md:40` 現為「本節原引用 `[ad:components.md]`，經 reviewer iteration 1 Finding #1 核對為誤植——該逐字原句實際出自 `component-dependency.md:98`。已於 2026-08-29T16:14:22Z 改為 `[ad:component-dependency.md]`」，方向已一致，不再與上方 :34 的更正說明相反 |
| 4 | U-2 iteration 2 Major #1：`business-logic-model.md` 的邊界表與「`parse` 的版本分派」節是否同步誠實揭露 | **通過** | `business-logic-model.md:50-52` 新增引文塊「三條路徑回的是同一個 `null`，呼叫端分不出來…**後果**：R-3.4 宣稱的「該 item 不被覆寫」**目前不成立**」；:74 邊界表該列改為「`parse` 回 `null`。**「不被覆寫」目前不成立**…」——兩處皆已補上 |
| 5 | U-2 iteration 2 Minor #2／#4：`reason_category` 的「直接對應」誤述、R-2.3 句尾「U-6／U-9」殘留 | **通過** | `domain-entities.md:20-22` 已改為「該對應**不成立**，已於 2026-08-29T16:14:22Z 更正…前者是「永遠有值」，後者是「與另一欄互斥」」；`business-rules.md:34` 句尾已改為「但那是 U-9 的落點（[Q2=A] 的選項本文原寫「U-6／U-9」…本 intent 的自我測試層只有 U-9），本站只標出」 |
| 6 | U-5 iteration 2：兩項 Minor 未惡化 | **通過** | `business-logic-model.md:86` 維持「標出不逕改」的如實措辭並改指 ADR-0015 §5；`0015-…md:38-40`「### 5. `components.md` 的 workflow 對照表為 `aidlc-sync-reverse.yml` 補上 **C-5**」與其主張逐字對應 |

### 第二批查證：送審前自檢改動（2026-08-29T23:42:35Z 自述）

| # | 查證項 | 結論 | 依據（檔名:行＋引文） |
| --- | --- | --- | --- |
| 7 | 「`Block` 的三個欄位不可能從 `Decision` 來」的推導是否成立 | **部分通過（兩項成立、第三項不是 `Block` 欄位）** | 開 U-1 `domain-entities.md:50-55`：`Decision` **恰有四欄**（`status`／`field_value`／`reason_code`／`traceable_row`），無時間戳、無 scope 資訊 ⇒ `decided_at`、`scope_note` 確實推不出，成立。但第三列「告示（[US:S-6 AC 5]）」**不在 `Block` 的六欄之內**（`domain-entities.md:9-16`），故 :30 的「`Block` 的**六個欄位**裡有**三個**不可能從 `Decision` 推出來」實算為 **2**——見 F2 |
| 8 | `Block` 六欄的來源分配是否無遺漏 | **通過（就六欄而言）** | `format_version`（渲染器常數，:38／:56-62）、`status`／`traceable_row`／`reason_category`（皆為 `Decision` 有的欄，U-1 `domain-entities.md:50-55`）、`decided_at`／`scope_note`（`Context`）——六欄各有來源，無無源欄位。真正的問題不是遺漏而是**多出一個沒有欄位承接的資訊**（告示），見 F2 |
| 9 | `scope_note`「由呼叫端自 `ParsedRecord` 取得」——呼叫端是否真的取得並傳遞 | **未通過（新的懸空契約）** | 見 F4 |
| 10 | R-1.5 與「四項皆為 [US-OQ-3] 定案、本站一項未增未減」的切分是否誠實 | **大致誠實，但未傳播** | `business-rules.md:17` 明白限縮為「講的是 R-1.1～R-1.4」並指名 R-1.5 來源為 [US:S-6 AC 5]，屬誠實切分而非換位置藏矛盾。但 `functional-design-questions.md:20` 的「已定案不重問」表逐字仍為「受管區塊**必載的四項內容**」且該檔本批未被觸及——見 F7／F8 |
| 11 | 告示 × `content_hash` 的完整時序是否有斷點 | **時序本身無斷點；必要性論證兩個支點皆不成立** | 見 F2。逐輪推演：告示輪由 R-5.6 第二子句觸發寫入 → R-5.4 以**寫入後回讀**取得雜湊回寫（U-6 `business-rules.md:75`，ADR-0015 §10）；下一輪無漂移且已離開 `reverse_rejected`（R-6.2c）⇒ 不寫、看板與記錄仍一致；告示消失的那一輪由三欄漂移觸發，R-5.4 同樣回寫新雜湊。**三種情形都沒有斷點**——但這正是因為 R-5.4 每次寫入都回讀，使 `domain-entities.md:48` 描述的「回寫後看板已變而記錄的雜湊未變」在構造上不可能發生 |
| 12 | R-1.5 可判定方式第二子句 vs「須 bump `format_version` 並重新基準化」 | **未通過（直接矛盾）** | 見 F3 |
| 13 | ADR-0015 六處回填的節號與內容是否相符 | **五處相符、一處（§8）內容不涵蓋所標缺口** | §3↔U-7 R-3.4 ✅（查證 2）；§7↔U-7 `domain-entities.md:44` ✅（`0015-…md:46-48` 兩條候選修法與「不得以本輪執行耗時冒充」逐字對應）；§9↔U-7 `business-rules.md:36` ✅（兩條候選修法逐字對應）；§6↔U-2 `business-rules.md:55` ✅（三態／`has_managed_marker` 逐字對應）；§5↔U-5 `business-logic-model.md:86` ✅。**§8 見 F6。** ADR 實數 §1–§10 共十節，與本輪引用一致 |
| 14 | §8 的「附帶」段是否涵蓋 U-8 的 P-1（權限實為四項） | **無法查證＋§8 本身不完整** | 見 F6。`construction/U-5-notifier/nfr-requirements/security-requirements.md` 與 U-8 的同名檔**不在 `.aidlc-reviewer-dispatch.json` 的 `exempt` 清單內**，實測被 reviewer scope hook 擋下，本輪無法逐字核對 P-1 |

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| **F1** | **Critical** | U-2 `business-logic-model.md:21`；對照 `component-methods.md` §C-3（:全表）與 §C-6:137-138 | **`render()` 產出的受管區塊字串在全份已核可契約中沒有任何寫入者。** `component-methods.md:137` 逐字「`render` │ `(Decision, Context) -> string` │ **產生受管區塊** │ 純函式」；C-3 `board-client` 的六個方法（`read_item`／`create_item`／`write_status`／`write_field`／`ensure_field`／`read_issue_state`）**無一寫 issue body**——全檔 `grep "body\|受管區塊"` 僅四處命中（:58 ADR-A4、:137 `render`、:138 `parse(issue_body)`、:141 必載內容），沒有寫入端。U-2 本檔 :21 逐字「區塊文字 ──► **（U-3 寫進 issue body）**」未指名任何方法；U-6 `business-rules.md:169` 進一步把它具名為「受管區塊的寫入路徑是 `U-2 render → U-3 write_field`」，但 `write_field: (binding, value) -> WriteResult` 的目的欄逐字為「**自訂欄位寫入**」、錯誤處理為「欄位不存在 → 嘗試建立」，其值由 U-1 `field_value_for` 產出並受 `Config.field_max_length`（**預設 50**，U-1 `domain-entities.md:68`）約束——結構上不可能承載受管區塊。**後果**：[US-OQ-3] 的必載內容永不出現在 issue、[req:FR-G4] 的內容雜湊比對沒有可比對的對象、U-8 的 R-1.1／R-1.2 整條反向路徑失效、U-6 R-5.4 的「寫入後回讀取得雜湊」沒有東西可回讀。**這是「契約端點三問」漏掉的最重一項，且與本批找到的 `Context` 落在同一個方法（`render`）的另一端**——第二批自述「檢查範圍是整個 stage 的全部產出」，但 `render` 的輸出端沒有被問過。 | 二擇一並記入 ADR-0015 新增一節：(a) C-3 增設一個明確的 issue body 寫入方法（例如 `write_body(binding, block_text) -> WriteResult`），由 U-3 擁有、U-6 呼叫，並在 U-2／U-6 兩處的資料流與方法表同步具名；(b) 若既有某方法確實承擔此職責，逐字指出是哪一個並更正 `component-methods.md` 對它的目的敘述。在此之前 U-6 的寫入鏈不可實作，U-2 :21 的括號敘述應改為「**目前無具名寫入者，見 F1**」而非以推定語氣帶過。 |
| **F2** | **Critical** | U-2 `domain-entities.md:9-16`（`Block` 表）、:30-37（三欄推導表）、:48（雜湊必要性） | **`Block` 沒有承接告示的欄位，但同檔宣稱告示「經由 `Block` 進入雜湊涵蓋範圍」。** (a) `Block` 表實數六欄，無 `rejection_notice`／告示欄；(b) :30 逐字「`Block` 的**六個欄位**裡有**三個**不可能從 `Decision` 推出來」，但表列第三項「告示（[US:S-6 AC 5]）」根本不是 `Block` 欄位，實算為 **2**（可算的數字未算）；(c) :48 逐字「**`rejection_notice` 進不進 `content_hash`？進。** 它經由 `Block` 進入雜湊涵蓋範圍（上一節：`content_hash` 吃的是整個 `Block`）」——而 :66 逐字「簽章是 `(Block) -> sha256`——**吃的是 parse 後的結構，不是渲染出來的字串**」，故未進 `Block` 的文字結構上不進雜湊，此宣稱在現行欄位表下為假；(d) 其必要性論證的後果推導亦與機制相反：U-8 `business-rules.md` R-1.1「讀看板現況 → 以 U-2 的 `content_hash` 與 `sync-state.json` 記錄的雜湊比對」、R-1.2「**雜湊未變 → 不產生 PR**」——若告示不進雜湊，比對兩側同樣看不到它 ⇒ 雜湊相等 ⇒ **不會**開 PR，與 :48 宣稱的「U-8 會把告示讀成人為變更並開 PR」相反；(e) 且 U-6 R-5.4 已改為「寫入後再呼叫一次 `read_item`」取雜湊（ADR-0015 §10），:48 描述的「回寫後看板已變而記錄的雜湊未變」在該構造下不可能發生。**這條錯誤的必要性論證正是「須 bump `format_version`」那個高成本決定（會讓所有既有 item 的雜湊失效）的唯一支撐。** | 先裁定告示是不是 `Block` 的一部分：(a) 若是 → `Block` 表增列第七欄並說明 `parse` 如何把它讀回來，同步更新 :30 的「三個／六個」與 R-2.2「任一欄位不同必得不同雜湊」的涵蓋範圍；(b) 若否（比照 :24 兩段固定說明的處置）→ 刪除 :48 整段必要性論證，改記「告示為渲染層文字，不進 `Block`、不進雜湊；其後果是人若竄改告示文字不會被 U-8 偵測到，此代價可接受」。無論哪一支，:30 的計數都必須重算。 |
| **F3** | **Critical** | U-2 `business-rules.md:15`（R-1.5 可判定方式）、:19（其理由）；U-2 `domain-entities.md:11`、:52、:62；U-2 `business-rules.md:30`（R-2.4）；U-6 `business-rules.md:185` | **R-1.5 的第二個可判定子句與同批宣告的格式變更義務不可同真。** :15 逐字要求「且 `null` 支的輸出與 R-1.5 引入前**逐字相同**」，:19 給的理由是「否則所有既有 item 的 `Block` 都會改變、雜湊全數失效——那是 ADR-A6 的最危險失效模式」。但同批的 `domain-entities.md:52` 逐字「`rejection_notice` 是 `Block` 的新增資訊，其上線是一次 ADR-A6 意義下的**格式變更**，必須…（**須 bump `format_version` 並重新基準化**）」，U-6 `business-rules.md:185` 逐字重複同一句。而 `format_version` 依 `domain-entities.md:11`「**內嵌於區塊文字中**」、依 R-2.4「在涵蓋範圍內」、依 :62「**bump 版本會讓所有既有 item 的雜湊改變**」——**一旦 bump，`null` 支的區塊文字（含版本標記）就不可能與引入前逐字相同，而「所有既有 item 的雜湊改變」正是 :19 宣稱要避免、:52 卻已明文接受的事**。這不是措辭鬆散：R-4.1（golden fixture 快照與渲染器輸出**逐位元**一致）會把矛盾變成 CI 上的實際紅燈——開發者無法同時讓 null 支快照維持舊版本標記、又讓 `FORMAT_VERSION` 通過 R-4.2。**兩個相矛盾的陳述由同一批修正在同一天寫入三份檔案**，屬「把矛盾換個位置留著」。 | 二擇一並三處同步：(a) 承認要 bump ⇒ 刪除 :15 的「逐字相同」子句與 :19 的理由，改為「`null` 支除版本標記外逐字相同；bump 造成的全量雜湊變動由 R-4.3 的重新基準化說明承接」；(b) 主張不需 bump（告示不進 `Block`，與 F2 的 (b) 支一致）⇒ 刪除 `domain-entities.md:52` 與 U-6 :185 的「須 bump」句，改為「渲染層新增文字、`Block` 結構未變，故非 ADR-A6 意義下的格式變更」。**不得兩句並存。** |
| **F4** | **Major** | U-2 `domain-entities.md:43`、:46；U-1 `domain-entities.md:83`、:92；U-6 三份產出（grep 零命中） | **`Context.scope_note`（連同 `decided_at`）在呼叫端沒有可行的取得路徑——新的懸空契約。** :43 逐字「由呼叫端自 `ParsedRecord` 取得」、:46 逐字「**呼叫端是 U-6**…`decided_at`／`scope_note` 每輪必填」。但 U-1 `domain-entities.md:83` 逐字「三個型別都是**單次 workflow run 內的程序內值**」、:92 逐字「產出唯一的 `Decision`，由 composite action 的**四個 output** 交給呼叫端」——`ParsedRecord` **不跨越 U-1 的邊界**，四個 output 即 `Decision` 的四欄，無一帶 `[S]`／`— SKIP` 的差別（該差別存在於 `ParsedRecord.stages[].checkbox`／`in_scope`，U-1 `domain-entities.md:29-35`）。實測 grep U-6 三份產出，`scope_note`／`decided_at` **零命中**：R-6.2b 只填 `rejection_notice`；R-7 群（:130-141，該表存在的目的正是「每個宣告的方法都要有具名呼叫者」）列了 `render(Decision, Context)` 卻沒有任何一列說誰組 `Context`；`domain-entities.md:31-43` 的「`Config` 在本單元的組裝責任」表也沒有 `Context` 的對應段。**後果**：R-1.2（[req:FR-F3]、[US-OQ-3] 的必載項）目前沒有填值路徑，與上一輪 `latency_samples` 被判 Critical 的形狀相同，只是落在輸入側。要補則需 U-1 的 composite action 增加**第五個 output**，那是對本 stage 已寫定的 U-1 契約的變更，目前無任何一處記載。 | 在 U-2 `domain-entities.md` 的 `Context` 表就地標出「`scope_note` 的來源目前不可達：`ParsedRecord` 不跨 U-1 邊界」，並二擇一指派：(a) U-1 的 composite action 增加一個 output（例如 `scope_note` 或整段 stage 摘要），同步更新 U-1 `domain-entities.md:92` 的「四個 output」計數；(b) 由 U-1 的 `Decision.traceable_row` 承載該差別並改寫 R-1.2 的可判定方式。無論哪一支，U-6 的 R-7 群與 `Context` 組裝責任表都必須新增對應列，使「誰寫 `Context` 的每一欄」可被指名。 |
| **F5** | **Major** | `0015-…md:72`（Consequences）；實測九份被 `Amends` 點名的上游 artifact；`bolt-plan.md:21-27`、:51、:59 | **ADR-0015 宣稱「一律以指標方式更正，與 ADR-0013、ADR-0014 的做法一致」，但被它 `Amends` 的上游檔案裡對 `0015` 零命中。** 實測 `grep -rn "0015\|ADR-0015"` 於 `requirements.md`／`bolt-plan.md`／`components.md`／`component-methods.md`／`unit-of-work-story-map.md`／`unit-of-work.md`／`stories.md`／`services.md`／`decisions.md` ⇒ **0 命中**。對照組：ADR-0014 的做法確實含就地指標——`requirements.md:147` 的 NFR-S1「需求」欄逐字含「（**經 ADR-0014 更正**：權限集合為**三項**……更正內容與理由見 `../decisions/0014-permission-set-and-alert-convergence.md`）」。故「與 ADR-0014 的做法一致」為**經實測不成立的宣稱**。連帶：§1 要求 PRE-1 表增列 PRE-1-b，而 `bolt-plan.md:21-27` 的 PRE-1 表**實數仍為五列**（1／2／3／4／PRE-1-a，與 §1 所述「現行五項」相符）；§2 要求 Bolt 1 DoD 增列兩條，而 :51 逐字仍只有「PRE-1 第 **1／3／4** 項已綠」；§3 要求 Bolt 2 DoD 增列一條，而 :59 無該條目。**六處回填共同宣告的「確認人為 Bolt 0／1／2／3 的 gate」，在 `bolt-plan.md` 上沒有任何痕跡**——這正是 ADR-0015 自己 Context 段點名的「一張沒有收件人的便條」，只是從單元產出升到了 ADR 層。這是 iteration 2 對 U-7 Major #2 的修正動作留下的同型殘留：措辭已改對，但承載機制的有效性建立在一個不成立的宣稱上。 | 二擇一：(a) 比照 ADR-0014 的實際做法，在 `bolt-plan.md` 的 PRE-1 表、Bolt 1／2／3 的 DoD、`requirements.md` 的 NFR-S1／NFR-O2、`components.md` 的 workflow 對照表、`component-methods.md` 的 `parse`／§C-7、story map 的 S-6 AC 5 各就地補一則「（經 ADR-0015 §N 更正，原文維持）」括號指標；(b) 若刻意不改上游檔案，把 Consequences 那句改寫為如實記載（「本 ADR 未在被修訂檔案內留下指標，其被讀到的唯一保證是 `project.md` 的『既有 ADR 納入唯讀查證範圍』規則」），並明確指定一個人在 Bolt 0 開工前逐節核對。**不得同時保留「與 ADR-0014 一致」的宣稱與零指標的現況。** |
| **F6** | **Major** | `0015-…md:50-54`（§8 及其「附帶」段）；`requirements.md:147`；`bolt-plan.md:23` | **§8 記載了「權限實為四項」卻沒有給任何更正指令，NFR-S1 的驗收判準在四項讀法下仍會擋掉正確的憑證。** §8 標題與本文只要求「`requirements.md` 的 NFR-S1 驗收判準**補上 ADR-0014 的指標**」（＝三項），而 `requirements.md:147` 的驗收判準欄逐字仍為「憑證實際被授予的權限集合等於上述**兩項**，無額外授予。**見下方「已解消的矛盾 R-1」**」。其「附帶」段逐字「**權限集合實為四項**——`deploy.yml:174-175`…把推分支（`contents: write`）與開 PR（`pull-requests: write`）分列兩行」，但**既未說驗收判準應改成幾項，也未指名確認人或閘門**——與 §6／§7／§9 一律給「二選一候選修法」的體例不同。§8 自己引用 ADR-0014 的那句「**這條驗收準則會主動阻止正確的憑證**」，在照 §8 做完（改為三項）之後、在四項讀法下**仍然成立**。連帶 `bolt-plan.md:23` 的 PRE-1 第 1 項逐字仍為「憑證帶**三項**權限」，亦未反映四項。**至於 U-8 的 P-1 是否與此一致，本輪無法查證**：`construction/U-5-notifier/nfr-requirements/security-requirements.md` 與 U-8 的同名檔不在 `.aidlc-reviewer-dispatch.json` 的 `exempt` 清單內，實測被 reviewer scope hook 擋下——**dispatch 清單與本輪指定的查證範圍不一致，本身是一項應修正的流程缺口**。 | (1) §8 的「附帶」段升格為與 §6／§7／§9 同體例的可執行決定：明寫驗收判準的目標值（三項或四項，二擇一）與確認閘門（Bolt 0 的 PRE-1）；(2) 同批把 `bolt-plan.md:23` 的「三項」納入該決定的傳播清單；(3) 下一輪 dispatch 若仍要求核對 `nfr-requirements/security-requirements.md`，請把該路徑加入 `exempt`，否則該查證項無法完成。 |
| **F7** | **Major** | U-2 `business-logic-model.md:29-38`、:38、:68-77、:83；U-2 `functional-design-questions.md:20`（mtime 2026-08-29 19:42 CST ＝ 11:42Z） | **第二批對 U-2 的兩項最大改動（`Context` 型別、R-1.5）沒有傳播到同單元的另外兩份產出——與 iteration 2 對 U-2 的唯一 Major 是同型復發。** (a) 「`render` 的組成序列」(:29-37) 仍為**四步**、無告示步驟，且 :38 逐字「第 2 步的二分是**窮盡的**……所以不存在第三支」——該句在 R-1.5 之後仍成立（告示是附加段而非第三支），但整節未提告示，讀者無從得知渲染器多了一段條件輸出；(b) 邊界情形表 (:68-77) 無告示相關列（例如「`rejection_notice` 非 `null`」「連續兩輪無漂移但上一輪送過告示」）；(c) :83「本檔對上游的補充」列了「`Block` 的欄位結構、`format_version` 的內嵌與 `parse` 的版本分派」，**未列 `Context` 的定義**——而那是本批最大的新增；(d) `functional-design-questions.md` 本批完全未被觸及（mtime 早於自述的 23:42:35Z 約 12 小時），其「已定案不重問」約束表 :20 逐字仍為「受管區塊**必載的四項內容**」，`Context`／`R-1.5`／「送審前自檢」在該檔 grep **零命中**——U-5／U-6／U-7 的同批改動都在正文留有具名揭露，U-2 的沒有進它自己的裁定紀錄檔。 | 把本批改動按「事實」而非「改過的字串」逐一傳播：`render` 組成序列補第 5 步（條件性告示）、邊界表補告示列、:83 補列 `Context`、`functional-design-questions.md` 補一則「本站裁定（送審前自檢）」段落記錄 `Context` 與 R-1.5 兩項新增及其來源，並把 :20 的「四項」改為「四項＋R-1.5 的條件性第五項（來源 [US:S-6 AC 5]，非 [US-OQ-3]）」。 |
| **F8** | Minor | U-2 `business-rules.md:7`、:17 | R-1 群前言逐字「四項皆為 [US-OQ-3] 定案…**本站一項未增未減**」，其下表格實列**五條**。:17 的註記已明白限縮該句為 R-1.1～R-1.4 並指名 R-1.5 的不同來源，**判定為誠實切分而非把矛盾換位置**；但前言與表格列數的表面不一致仍需靠讀者跟進註記才能消解，且該「四項」在 `functional-design-questions.md:20` 有第二個落點未同步（見 F7）。 | 把 :7 改寫為「R-1.1～R-1.4 四項皆為 [US-OQ-3] 定案…本站一項未增未減；R-1.5 為本站新增，來源 [US:S-6 AC 5]，見下方註記」，使前言自身即可判。 |
| **F9** | Minor | U-7 `business-rules.md:63`；對照 `domain-entities.md:19`、:44-46 | R-3.4 的處置句逐字「報告加一個 `deferred: [intent_id]` 欄位，或在 **`latency_samples` 之外**另記本輪的處理起訖位置」——這句把 `latency_samples` 當成本單元仍在填的報告欄位，與同單元 `domain-entities.md:19`「**本單元填不出值**」、:46「**在修正落地前，本單元不填此欄位**」不一致。屬 iteration 2 修 `latency_samples` 時未傳播到 R-3.4 的殘留。 | 改為「報告加一個 `deferred: [intent_id]` 欄位，或另記本輪的處理起訖位置」，刪去對 `latency_samples` 的並列引用。 |
| **F10** | Minor | U-7 `business-rules.md:40`（R-8 群位置）；`0015-…md:4`（Date）對照檔案 mtime 與 ADR-0014 | (a) 重編號正確且無二次撞號（查證 1a／1b），但 R-8 群插在 R-2 與 R-3 之間、R-6／R-7 未使用，循序閱讀者會以為漏了兩群；(b) ADR-0015 的 `Date: 2026-08-30`，而其檔案 mtime 為 `2026-08-30T00:18:39+0800` ＝ **2026-08-29T16:18:39Z**，寫入當下的 UTC 日期是 08-29；對照 ADR-0014（mtime `2026-08-29T21:02:02+0800` ＝ 13:02Z，`Date: 2026-08-29`）採 UTC 日期，兩份 ADR 的日期基準不一致。本 intent 的 `project.md` 有明文教訓要求時間戳一律取自 `date -u`。 | (a) 把 R-8 群移到 R-5 之後，或在群標題旁註明「編號承接自舊 R-4，位置維持以免動搖既有引用」；(b) 統一 ADR 日期基準為 UTC，或在兩份 ADR 註明採本地日期。 |

### 新引入的問題（本輪的歸屬）

- **來自第二批（送審前自檢，2026-08-29T23:42:35Z）**：F1（`render` 輸出無寫入者——該批自述已跑完「契約端點三問，檢查範圍是整個 stage 的全部產出」，卻只問了 `render` 的輸入端）、F2、F3、F4、F7、F8。其中 **F3 與 F2 是「修正的修正」自己製造的**：為了讓 `Context` 的告示欄有依據，同批在三份檔案寫下「須 bump `format_version`」，又在同批的 R-1.5 寫下「`null` 支逐字相同」，兩者不可同真；而支撐「須 bump」的必要性論證（F2 的 (c)(d)(e)）其兩個支點——`Block` 涵蓋告示、U-8 會誤判——經核對皆不成立。
- **來自 iteration 2 的修正動作**：F5（改走 ADR-0015 承載後，「與 ADR-0014 做法一致」的宣稱經實測不成立）、F9（修 `latency_samples` 時漏了 R-3.4 的並列引用）。
- **流程缺口**：F6 末段——本輪被指定核對的兩份 `nfr-requirements/security-requirements.md` 不在 dispatch `exempt` 清單內，查證無法完成。

### Summary

iteration 2 的四項必修（U-7 的 R-4→R-8 重編號與 R-3.4 措辭、U-2 的 `business-logic-model` 同步揭露與兩項 Minor、U-11 的自相矛盾註記）**全部實質落地並經逐字複驗**，U-5／U-7／U-11 三個單元本輪判 READY。整組 NOT-READY 來自第二批「送審前自檢」對 U-2 的改動：它正確地找出了 `Context` 這個從未被定義的型別，卻在補它的同時新增了三個 Critical——`render()` 的**輸出端**同樣沒有寫入者（與 `Context` 是同一個方法的另一端，而該批自述已檢查過整個 stage 的全部產出）、`Block` 沒有欄位承接告示卻宣稱它「經由 `Block`」進雜湊（且其必要性論證的兩個支點經 U-8 R-1.1／R-1.2 與 U-6 R-5.4 核對皆與機制相反）、R-1.5 的「`null` 支逐字相同」與同批寫進三份檔案的「須 bump `format_version`」不可同真。另有兩項 Major 是「承載機制本身」的問題：`Context.scope_note` 指定的來源 `ParsedRecord` 不跨 U-1 的 composite action 邊界，以及 ADR-0015 宣稱的「以指標方式更正、與 ADR-0014 一致」在被它 `Amends` 的九份檔案中零命中——後者使六處回填共同依賴的「Bolt gate 確認人」在 `bolt-plan.md` 上仍無任何痕跡，等於把上一輪判定的「沒有收件人的便條」升了一層而非解決。
