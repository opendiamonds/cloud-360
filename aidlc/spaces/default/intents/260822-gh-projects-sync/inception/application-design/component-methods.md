# Component Methods — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: application-design（Inception 2.5）· Record: 260822-gh-projects-sync
     方法簽章與錯誤處理；詳細商業規則屬 Functional Design，本檔只到「這個方法負責什麼、
     輸入輸出是什麼、失敗時怎麼辦」的層次。上游輸入清單見 `components.md` §上游輸入。
     型別以語言中立的形式表達——承載形式為 composite action 與 workflow step，
     實際語言留給 construction。 -->

## 共用型別

```
Decision        = { status: Status | null, field_value: string, reason_code: ReasonCode,
                    traceable_row: string }
Status          = "Ready" | "In progress" | "In review" | "Done"
ReasonCode      = "mapped"            // 正常映射，status 非 null
                | "parked"            // Parked 非空，不寫 Status（FR-B6）
                | "unparseable"       // 必要區塊缺失，跳過（FR-J3）
                | "whitelisted"       // 已知結構性例外（FR-J5）
                | "undecidable"       // 訊號不落在對照表任一列（S-2 AC 4）
                | "suppressed"        // 有未處理反向紀錄，暫停覆寫（FR-G3）
ParsedRecord    = { intent_id, current_stage, runtime_status, parked, parked_at_stage,
                    stages: [{ slug, checkbox, in_scope }], binding: int | null }
Unparseable     = { intent_id | null, missing: [string] }
ItemState       = { status, field_value, managed_block_hash, issue_number, issue_state }
WriteResult     = Written | Aborted { actual, expected } | Failed { http_status, message }
```

**`Status = null` 是合法輸出**，不是錯誤。`reason_code` 一律非空——[US:S-2 AC 15] 的總函式性要求「恰好輸出一個 Status 或一個明確的不寫理由」，沒有第三種結果。

## C-1 `sync-map`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `map` | `(ParsedRecord \| Unparseable, Config) -> Decision` | 唯一的映射入口 | **不拋例外。** `Unparseable` 輸入回 `reason_code = "unparseable"`（白名單內則 `"whitelisted"`）；訊號不落在對照表任一列回 `"undecidable"` 且 `status = null`（[US:S-2 AC 4]／[AC 15]） |
| `field_value_for` | `(Decision, Config) -> string` | 組出自訂欄位值 | 純函式。格式見下方 §自訂欄位格式 |

**判定順序**（優先序由高至低，[req:FR-B] 表格 ＋ [F4=A]）：

1. `parked` 非空 → `status = null`，`reason_code = "parked"`（**優先於其餘全部**）
2. 有未處理反向紀錄 → `status = null`，`reason_code = "suppressed"`（[req:FR-G3]）
3. `runtime_status == "Completed"` → `Done`（[US:S-2 AC 3]，讀 `Status` 欄位而非推導 checkbox）
4. 任一 in-scope stage 為 `[?]` → `In review`
5. 任一 in-scope stage 為 `[-]` 或 `[R]` → `In progress`
6. 無任何 in-scope stage 動過 → `Ready`
7. 以上皆不符 → `status = null`，`reason_code = "undecidable"`

> 第 3 條先於第 4／5 條是刻意的：`Completed` 的 record 不應因殘留的 `[?]` 而回退。
> **第 1 條與第 3 條互斥**——實測 `aidlc-state.ts:830-832`，`handlePark` 在 `Status == "Completed"` 時直接拒絕，故 `Parked` 與 `Done` 不可能同時成立（此事實已記入 `stories.md` S-4 註記）。

**自訂欄位格式**（[US-OQ-4] 的定案，[Q3=C] 的收斂）：

```
<短前綴><stage-slug> (<編號>)
```

- 短前綴限一個字元類，四選一：無（正常）、`parked @ `、`skipped `、`frozen: `。
- **長度上限 50 字元**；超出時截斷 stage-slug 尾端並保留前綴與編號（前綴是狀態訊號，不可被截斷）。
- **完整敘述一律在受管區塊**（C-6）。**兩處不一致時以受管區塊為準**（ADR-A4）。

> **經 ADR-0015 §14 標記（指標補於 2026-08-30T01:31:09Z）**：上述前綴為四選一，但 `undecidable` 這個 `reason_code`（由 functional-design 依 [US:S-2 AC 4] 的缺口 G-1 新增）**沒有對應前綴**——`skipped ` 對應的是 `[S]` 標記，語意不同。前綴集合須增列第五項，字面待與 §12 的 `format_version` bump 一併定。**在此之前 `undecidable` 的自訂欄位行為未定義，實作不得自行猜**。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。確認人為 Bolt 1 的 gate。

## C-2 `record-reader`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `parse` | `(state_md_text, intents_json_text, record_path) -> ParsedRecord \| Unparseable` | 唯一的解析入口 | **不拋例外**；缺必要區塊回 `Unparseable{missing}` |
| `get_field` | `(text, field_name) -> string \| null` | 複製引擎 `getField()` 語意 | 行錨定（行首即 `- `）、全檔搜尋、**第一個 match 即回傳**、缺席回 `null` |
| `list_stages` | `(text) -> [{slug, checkbox, in_scope}]` | 逐檔解析 stage 清單，**不寫死**（[req:FR-J4]） | 無 `## Stage Progress` 區塊 → 併入 `Unparseable` |

**`get_field` 的四條行為**（[US:S-2 AC 7–10]，全部可用純文字 fixture 驗）：

1. 正式欄位之前另有同名行 → 回**第一個** match
2. 欄位存在但值為空（`- **X**: ` 後無內容）→ 回**空字串**，不是下一行的內容
3. 欄位完全缺席 → 回 `null`，且呼叫端走**與空字串不同**的分支
4. 縮排的 `  - **X**: ` → **不視為 match**

> 第 3 條直接保護 C-1 的第 1 條判定順序：現況 record 的 `## Runtime State` 只有
> `- **Revision Count**: 0`，`Parked` 是**缺席**而非空值。混同會讓 park 特判永不觸發。

**intent 選取的邊界**（[Q4=A] 的連帶決定，reviewer iteration 1 Finding 2 後擴大適用範圍）：**事件路徑（S-A）與排程路徑（S-B／S-C）一律以 `intents.json` 的 registry 為選取來源**（[req:FR-J1]：`intents.json` 只用於列舉有哪些 intent），**不得依事件 diff 推導 record**。fixture record 不註冊進 registry，因此**兩條路徑都不會選中它**——`<record>/.test-fixtures/` 不會變成第 7 個 intent，也不會被事件觸發送進配置給 Project #16 的 C-3。

> 先前版本只把這條規則寫在列舉（C-7）那一側，使 ADR-A3 的「fixture 永不進入 P3 視野」只對一半路徑成立。此為 reviewer iteration 1 Finding 2（Critical）的修正。

## C-3 `board-client`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `read_item` | `(binding, Config) -> ItemState` | 回讀 | API 錯誤 → 拋 `ExternalError{http_status}` |
| `create_item` | `(intent_id, Config) -> binding` | 首建（[req:FR-A1]） | **先檢查 record 是否已有綁定編號**；有則不建、回既有值（[US:S-1 AC 6]）。目標 Project 不符 Config → 中止（[req:FR-C2]） |
| `write_status` | `(binding, expected: ItemState, desired: Status) -> WriteResult` | 唯一的 Status 寫入點 | **必先回讀**；`actual != expected` → 回 `Aborted`，**不送出寫入、不開 issue**（開 issue 是 C-5 的職責） |
| `write_field` | `(binding, value) -> WriteResult` | 自訂欄位寫入 | 欄位不存在 → 嘗試建立；建立失敗 → 回 `Failed`，**但不影響 Status 寫入**（[US:S-5 AC 2] 的「欄位失敗不連坐」） |
| `ensure_field` | `(Config) -> FieldRef \| CannotCreate` | 欄位自動建立（[req:FR-F2]） | 三種可達失敗前提：憑證缺 Projects 寫入權／同名欄位型別不同／組織政策阻擋。任一者回 `CannotCreate`，呼叫端交 C-5 通報「需人工建立欄位」 |
| `read_issue_state` | `(binding) -> "open" \| "closed"` | [US:S-9 AC 5] 的 issue 開關偵測 | 同 `read_item` |

> **經 ADR-0015 §11 增設 `write_body`（指標補於 2026-08-30T00:48:38Z）**：上表六個方法**無一寫 issue body**，而 C-6 的 `render` 產生的受管區塊只能存在於 issue body。缺它時 `read_item` 回傳的 `managed_block_hash` 恆為 `null`，U-8 的反向同步比對 `null` 對 `null` ⇒ **FR-G 全組與 [US:S-6] 全部 AC 永遠不觸發，且沒有任何紅燈**。
>
> | 方法 | 簽章 | 目的 | 錯誤處理 |
> | --- | --- | --- | --- |
> | `write_body` | `(binding, block_text) -> WriteResult` | 把受管區塊寫進 issue body | 與 `write_field` 同形：回傳值而非例外；失敗回 `Failed`，不連坐 Status 寫入 |
>
> **注意 `write_field` 不是它**——本檔 §自訂欄位格式明訂該欄位「長度上限 50 字元」且「完整敘述一律在受管區塊」，上游自己把兩者定義為不同的東西。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。確認人為 Bolt 1 的 gate。

**分頁與欄位 id**：Projects v2 的 item 列舉與欄位 id 查詢都需分頁。本 repo **無先例**（[kb] 實測 11 支 workflow 沒有一支寫過 Projects v2），實作細節留給 construction，但 `read_item` 的介面刻意不暴露分頁——呼叫端只給 binding。

**權限邊界的可觀察面**（[US:S-10 AC 5]）：本元件**不得**提供任何「推 commit 到 `ut`」或「改 record 目錄以外的檔案」的方法。

> **但「介面不提供」與「嘗試時回 403」是兩件事**（reviewer iteration 2 Critical）：AC 5 的兩個例子中，**只有「直推 `ut`／`main`」可由 [Q2=A] 的分支保護產生真的 403**；「改 record 目錄以外的檔案」在本設計下**無機制可產生 403**——GitHub App 沒有路徑層級授權。候選機制與其實測項見 ADR-A2 與 PRE-1-a。此處先前的措辭把兩個例子一併宣稱為可斷言，與 ADR-A2 修正後的內容矛盾，已更正。

## C-4 `binding-store`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `read_binding` | `(record_path) -> int \| null` | 取綁定編號 | 缺席回 `null`（觸發首建） |
| `write_binding` | `(record_path, issue_number)` | 寫綁定編號 | 檔案寫入失敗 → 拋 `ExternalError` |
| `read_sync_state` / `write_sync_state` | `(record_path[, state])` | `<record>/sync-state.json`（[req:C-N1]） | read-modify-write；並行衝突由 `commit_and_push` 的 push 失敗表現 |
| `commit_and_push` | `(branch, paths, message) -> Pushed \| Rejected` | 回寫（[req:FR-A3]） | **只推觸發分支**；`paths` 限 record 目錄下的綁定編號與 `sync-state.json`；訊息必含 `[aidlc-sync]`。push 被分支保護拒絕 → 回 `Rejected`，交 C-5 通報 ＋ 紅燈 |

**避免觸發 `ci.yml`**（[US:S-1 AC 7]）：本元件不能單方面解決——`ci.yml` 的 `on: pull_request` 無分支過濾且 `cancel-in-progress: true`。設計上的落點是**在同一個 PR 內修改 `ci.yml`**，為它加 `paths-ignore`（涵蓋 `**/sync-state.json` 與綁定編號檔）或等價手段。此為對既有檔案的修改，已記入 `component-dependency.md` 的碰撞面表。

## C-5 `notifier`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `notify` | `(FailureIdentity, detail) -> IssueRef` | 通報 | 通報本身失敗 → 拋（不可遞迴通報） |
| `resolve_if_open` | `(FailureIdentity)` | 失敗不再發生時收斂 | 找不到既有 issue → no-op |

```
FailureIdentity = { intent_id, reason_code }
```

**收斂演算法**（[Q5=A]，記憶體是 GitHub issue 本身，**不新增任何持久狀態**）：

1. 以 `FailureIdentity` 為鍵搜尋**開啟中**的通報 issue（label ＋ 標題慣例）。
2. 命中 → 追加一則 comment（含本輪的時間戳與細節），更新標題的計數。
3. 未命中 → 開新 issue，內文含 intent 識別字、stage 標識、ISO 8601 時間戳三者（[req:FR-E3]）。

**可補回 S-8 的二元 AC**（[US-OQ-1] 要求本站產出）：

> **Given** 同一個 `(intent_id, reason_code)` 的失敗連續發生兩輪，**When** 第二輪結束，**Then** 該鍵對應的**開啟中**通報 issue 數為 1，且該 issue 的 comment 數增加 1。

**不使 workflow 紅燈的兩種情形**（[US:S-8 AC 1] 的適用前提）：`reason_code` 為 `"suppressed"`／`"parked"`／`"unparseable"`／`"whitelisted"`／`"undecidable"` 時屬機制的正常判斷；`Aborted`（回讀不符）屬 [req:FR-C1] 的主動中止；對帳成功補平屬 [US:S-7 AC 5]。**只有 `ExternalError` 與 `Rejected` 紅燈。**

## C-6 `managed-block`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `render` | `(Decision, Context) -> string` | 產生受管區塊 | 純函式 |
| `parse` | `(issue_body) -> Block \| null` | 取出既有區塊 | 無標記回 `null` |
| `content_hash` | `(Block) -> sha256` | 防迴圈第一道（[req:FR-G4]） | 純函式 |

> **經 ADR-0015 §6 標記（指標補於 2026-08-30T00:48:38Z）**：`parse` 的兩種 `null`（完全無標記／版本高於當前渲染器）在型別上無法分辨，使 U-2 的 R-3.4「不覆寫較新版本的區塊」**字面不成立**——而 ADR-A6 把該路徑點名為本設計最危險的失敗模式。二選一：(a) 三態回傳；(b) 另加述詞 `has_managed_marker(issue_body) -> bool`。確認人為 Bolt 1 的 gate。
>
> **經 ADR-0015 §12 增設 `Block.rejection_notice`**：型別為 `{ closed_at: ISO 8601 } | null`，承載 [US:S-6 AC 5] 的「該次人工改動未被採納」告示。**這是一次格式變更**，須 bump `format_version` 並於同一個 PR 重新基準化（ADR-A6）；Bolt 1 首次上線時既有受管 item 數為 0，是最便宜的時點。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。

**受管區塊必載的內容**（[US-OQ-3] 的定案）：

- 目前的 Status 與其對照表列（`traceable_row`），或**機制決定不寫的原因類別與 ISO 8601 時間戳**。
- `[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）的差別（[req:FR-F3]）。
- 一段固定說明：**「Status 欄位為權威來源；本 issue 依 OOS-2 不自動關閉，其開／關狀態不表示進度」**——這解掉 `Done` 卡片下掛開啟中 issue 的誤讀（design agent 的 C-4）。
- 一段固定說明：**「自訂欄位為空的 item 不由本機制維護」**（[Q6=A] 的規則落點）。

## C-7 `reconciler`

| 方法 | 簽章 | 目的 | 錯誤處理 |
| --- | --- | --- | --- |
| `reconcile` | `(Config) -> ReconcileReport` | 每日對帳 | 單一 intent 失敗不中止整輪；計入報告後續跑 |

```
ReconcileReport = { backfilled_count: int,
                    consistency: { denominator: int, numerator: int },
                    awaiting_human: [intent_id],      // 有未處理反向紀錄
                    parked: [intent_id],              // Parked 非空
                    aborted: [intent_id],             // 回讀不符已中止
                    unparseable: [intent_id],         // 白名單外解析不出
                    issue_status_mismatch: [intent_id],  // S-9 AC 5
                    latency_samples: [seconds] }
```

> **經 ADR-0015 §7 標記（指標補於 2026-08-30T00:48:38Z）**：`latency_samples` 的擁有權應移出 U-7——NFR-P1 量測的是**事件觸發**路徑（U-6）的延遲，而 U-7 是每日批次、沒有任何機制擷取「push 完成時刻」。二選一：(a) 擁有權移到 U-6；(b) `SyncState` 新增觸發時刻欄位由 U-6 寫、U-7 讀。**在此之前 U-7 不填該欄位，且不得以「本輪執行耗時」冒充。** 另 **G-1**（[US:S-2 AC 4] 要求對帳報告有「無法判定」清單，而本結構只有 `unparseable`——兩個 `reason_code` 不能互相頂替）：`ReconcileReport` 亦須含 `undecidable: [intent_id]`，該缺口由 units-generation 標出並指派 functional-design，已於 U-7 關閉。**先前此處誤寫為「§12 相關」，而 §12 是 `Block.rejection_notice`、且 ADR 全文不含 `undecidable`——指標解析不到（2026-08-30T01:31:09Z 更正，reviewer iteration 4 Group B M-7）。**此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。確認人為 Bolt 2 的 gate。

**一致率**（[US:S-9 AC 1] 的定案，**維持上游 NFR-O2 的兩類排除**）：

- 分母 = 已綁定的 intent − `awaiting_human` − `parked`
- 分子 = 分母內「看板與 record 不一致」者，**含 `aborted`**（它們是待清理的真實不一致）
- `aborted` 另列獨立清單使 P4 可分辨，但**不移出分母**——理由見 `stories.md` S-9 AC 1 與 ADR-A5

**處理量上限**（[US:S-7 AC 3]）：以 workflow input `reconcile_batch_size` 宣告；改該值後下一輪處理量隨之改變。上限的實際值待 PRE-1 實測 C-T5 後定。
