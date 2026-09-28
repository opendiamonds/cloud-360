# Domain Entities — U-7 對帳 workflow 與編排器

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## `ReconcileReport`（含缺口 G-1 的修補）

[ad:component-methods.md] §C-7 已給欄位。**本檔補入 `undecidable`**——那是 units-generation 標為 **G-1** 並指派本 stage 的缺口。

| 欄位 | 型別 | 語意 |
| --- | --- | --- |
| `backfilled_count` | int | 本輪實際補平數 |
| `consistency` | `{denominator, numerator}` | 一致率，兩類排除見下 |
| `awaiting_human` | [intent_id] | 有未處理反向紀錄 |
| `parked` | [intent_id] | `Parked` 非空 |
| `aborted` | [intent_id] | 回讀不符已中止 |
| `unparseable` | [intent_id] | **白名單外**解析不出（`reason_code = "unparseable"`） |
| **`undecidable`** | **[intent_id]** | **本檔新增（G-1）**：訊號不落在對照表任一列（`reason_code = "undecidable"`） |
| `issue_status_mismatch` | [intent_id] | issue 已關閉而 Status 不為 `Done`（[US:S-9 AC 5]） |
| `latency_samples` | [seconds] | **本單元填不出值，見下方**。原記為「NFR-P1 的量測樣本」 |

### 為什麼 `undecidable` 不能用 `unparseable` 頂替（G-1 的核心）

[US:S-2 AC 4] 要求「未列舉輸入不寫，且**進對帳報告的『無法判定』清單**」。而 `unparseable` 與 `undecidable` 是 U-1 的 `ReasonCode` 中**兩個不同的值**，語意不可互換：

| `reason_code` | 意思 | 誰的問題 |
| --- | --- | --- |
| `unparseable` | record 的**必要區塊缺失**，連讀都讀不出來 | record 的結構壞了 |
| `undecidable` | record **讀得出來**，但訊號組合**不落在對照表任一列** | 對照表沒涵蓋到這個組合 |

**兩者的處置完全不同**：`unparseable` 要修 record，`undecidable` 要修對照表。合成一個清單會讓 P4 看到一堆 id 卻不知道該修哪邊——而 [US:S-9] 的價值正是「可信度本身看得到」。

> **這是 units-generation 標出、指派本 stage 的缺口 G-1**，來源見 `unit-of-work-story-map.md` 的 S-2 AC 4 列（「判定屬 U-1，清單成員身分屬 U-7。**且目前不可滿足**」）與 `unit-of-work.md` 的 G-1 記載。**本檔在此關閉它。**

### `whitelisted` 刻意沒有清單

`ReasonCode` 的六個值中，`mapped`（正常）與 `whitelisted`（已知結構性例外）**不進任何清單**。

`whitelisted` 的意思是「這個 record 解析不出來，**而我們已經知道且接受**」（[req:FR-J5]）。把它列進報告等於每天提醒一次一件已經決定不處理的事。[US:S-3 AC 6] 逐字要求「白名單外者進『無法解析』清單、**白名單內者不進**」——本項是該 AC 的直接後果，不是遺漏。

> **`latency_samples` 的語意在本單元的資料流下無法被填值（reviewer iteration 1 Critical，2026-08-29T15:26:25Z）。**
>
> NFR-P1 與 [US:S-9 AC 6] 量測的是「**自 record 被推送起算**到看板 Status 更新」的延遲——那是**事件觸發**路徑（U-6）的量。本單元是每日批次工作：它不由 push 觸發，也沒有任何機制擷取或儲存「push 完成時刻」（已跨 U-4 的完整 `SyncState` schema 與 U-6 的序列核對，兩處都沒有這個欄位或步驟）。**本單元能算出的只有「本輪自己跑了多久」，那不是 NFR-P1。**
>
> **指派**：欄位定義在 [ad:component-methods.md] §C-7（已核可上游），故標出不逕改。**本項已由 ADR-0015 §7 承載**（送審前自檢遷移，2026-08-29T23:42:35Z；理由同該 ADR 的 Context 段——單元產出內的指派對已定稿上游沒有收件人）。兩條可行修法——(a) 把 `latency_samples` 的擁有權移到 U-6（事件路徑，它知道觸發時刻），本單元不再宣稱擁有它；(b) 若要留在對帳報告裡，`SyncState` 須新增一個「觸發時刻」欄位由 U-6 寫入、本單元讀取。**確認人為 Bolt 2 的 gate**（本單元交付時）；指派目標 stage 為 EXECUTE。
>
> **在修正落地前，本單元不填此欄位**，且不得以「本輪執行耗時」冒充——那會讓 NFR-P1 的量測看起來存在而實際上量的是別的東西。

## 一致率的兩類排除（維持上游，本站不動）

- 分母 = 已綁定的 intent − `awaiting_human` − `parked`
- 分子 = 分母內「看板與 record 不一致」者，**含 `aborted`**

**`undecidable` 的新增不改變分母**。它與 `aborted` 同類——都是「機制放棄擔保」而非「機制刻意不動」，因此**計入分母也計入分子**，另列獨立清單供 P4 分辨。ADR-A5 已明文駁回「擴為三類排除」，本站的新增不觸及那個決定。

## 與上游的對應

本單元對 C-4 的使用（`write_sync_state`／`commit_and_push`，R-6 群）源自 **ADR-0015 §13**——`components.md` 原給 reconcile 的元件鏈不含 C-4，該修訂由人工裁決 Q5=A 促成；分支落點（`ref: ut`、推自 `ut` 分叉的自建分支、報告記 `ut` HEAD SHA，R-7 群）源自人工裁決 **Q6=A**（使用者原話「不應該在main上跑」）。**這兩段於 2026-08-30T01:31:09Z 補上（reviewer iteration 4 Group A C-4：Q5=A 的承接在本單元的序列圖、fallback、與上游對應三處零傳播）。**

`ReconcileReport` 的欄位、一致率定義與處理量上限引自 [ad:component-methods.md] §C-7；兩類排除的維持引自 [ad:decisions.md] ADR-A5；`ReasonCode` 的值域與語意引自 U-1 的 `domain-entities.md` 與 `business-rules.md` R-3／R-4 群；[req:FR-J5]／[req:FR-D1]／[req:FR-D3]／[req:NFR-O2] 引自 `requirements.md`；[US:S-2 AC 4]／[US:S-3 AC 6]／[US:S-7]／[US:S-9] 引自 `stories.md`；缺口 G-1 的來源與指派引自 [ug:unit-of-work.md] 與 [ug:unit-of-work-story-map.md]；元件分層引自 [ad:components.md]；S-B 的生命週期引自 [ad:services.md]。
