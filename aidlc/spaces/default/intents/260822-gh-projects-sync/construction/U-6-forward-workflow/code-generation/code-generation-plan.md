# Code Generation Plan — U-6 正向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service
     Created: 2026-09-05T11:03:48Z（讀自 date -u） -->

## 交付物與落點

| 檔案 | 內容 |
| --- | --- |
| `.github/workflows/aidlc-sync-forward-impl.yml` | `on: workflow_call`，全參數化（ADR-A10）。編排的實體 |
| `.github/workflows/aidlc-sync-forward.yml` | 薄外層：`on: push` / `pull_request`，帶 concurrency，`uses:` 上面那支 |
| `.github/actions/aidlc-sync-forward/run-orchestration-tests.py` | 行為測試（見下方「測試策略」） |

複雜度 **M**。不新增依賴——五支 composite action（U-1～U-5）全部已交付且介面已核對。

**`workflow_call` 有先例**：`agentics-maintenance.yml` 已在用，非本 repo 首見。

## 開工前查證（唯讀，結果登錄於此供題幹與實作引用）

### 查證 1 — 五支上游 composite action 的介面（實讀 `action.yml` 與 `*.sh` 的 dispatch）

| action | operation 值域（實讀 dispatch case） |
| --- | --- |
| `aidlc-sync-map` | 單一操作（無 `operation` input）；outputs：`status`／`field_value`／`reason_code`／`traceable_row`／`scope_note` |
| `aidlc-sync-board` | `read_item`／`create_item`／`write_status`／`write_field`／`ensure_field`／`read_issue_state`／`write_body` |
| `aidlc-sync-record` | `read_binding`／`write_binding`／`read_sync_state`／`write_sync_state`／`commit_and_push` |
| `aidlc-sync-notify` | `notify`／`resolve_if_open` |
| `aidlc-sync-block` | 有 `operation` input（`render`／`parse` 等），outputs 含 `block_text`／`content_hash` |

R-7 群點名的每一個方法都對得上一個實際 operation，**無懸空契約**。

### 查證 2 — R-4.3 的前提已被 ADR-0016 推翻（**與 U-10a 同一形狀**）

R-4.3 逐字：「[Q2=A] 於 application-design 選的是 **GitHub App**（非 `GITHUB_TOKEN`），故防線②**確實會被執行**」。

**ADR-0016 §1 已讓 GitHub App 路徑退場**（標題逐字：「憑證拓樸由組織層 GitHub App 改為擁有者帳號 token」），身分改為 `opendiamonds` 帳號 token。`gh auth status` 實測 scopes 為 `admin:public_key, gist, project, read:org, repo, workflow`，與 ADR-0016 §1 記載一致。

**依 `functional-design:c22`（查證推翻的是理由而非決定時，只修理由不改決定）**：R-4.3 的**結論仍然成立**——關鍵區別從來不是「App vs `GITHUB_TOKEN`」，而是「**是不是 `GITHUB_TOKEN`**」：GitHub 明訂用 `GITHUB_TOKEN` 推的 push 不觸發 workflow，而任何其他憑證（App token 或 PAT）都會觸發。擁有者 PAT 屬後者，故防線②仍會被執行、不是恆真。

**但理由必須更正**，且這是**第二次**同一個假前提咬人（U-10a 的 `github.actor` 是第一次）——ADR-0016 改了身分卻沒有回頭掃「哪些設計依賴了舊身分的性質」。**本站標出、不回改上游**，指派 Bolt 1 gate。

### 查證 3 — `undecidable` 的自訂欄位行為（**這是實作阻塞，見下方 Q1**）

- ADR-0015 §14 逐字：「**在它落地之前，`undecidable` 的自訂欄位行為未定義——實作不得自行猜一個前綴**」，確認人 Bolt 1 gate。
- U-1 已交付的 `map.sh:416-424` **正確遵守**：`undecidable` 時 `compose_field_value` 回傳空字串並就地註明不猜。
- **但 U-3 的 `write_field` 對空值沒有任何守衛**：`board.sh:792` `local value="${AIDLC_FIELD_VALUE:-}"`，最終 `-f text="$value"` 直送 GraphQL。

**後果**：R-5.10 (a) 逐字要求 `undecidable` 照走 `write_field`，照字面實作會把自訂欄位**寫成空字串**，也就是**清掉它原有的內容**。清空是一種行為，選它就是在猜——與 ADR-0015 §14 的禁令牴觸。

**可達性已驗**（`functional-design:c10`）：`undecidable` 由 `map.sh:395` 產生，有專屬 fixture `r3-7-undecidable.md` 與通過的測試，**是真實可達的路徑**，不是理論分支。

### 查證 4 — registry 現況

`intents.json` 為 **6 個 intent**（`complete` 2、`in-flight` 4）。R-3.0 點名的 `260802-default` 確實在內且無綁定——第一次上線就會走到 FR-J3 的排除路徑。

## 計畫步驟

- [ ] **Step 1 — `aidlc-sync-forward-impl.yml` 的骨架與參數**：`on: workflow_call`，inputs 為 `project_number`／`project_owner`／`record_root`／`stage_field_name`／`whitelist`／`field_max_length`，secret 為同步 token（ADR-A10 的清單，`app_id`／`app_private_key` 依 ADR-0016 改為單一 token）。**追溯**：ADR-A10、ADR-0016 §1
- [ ] **Step 2 — 防線②（R-4.2）**：整輪開頭讀 HEAD commit 訊息，含 `[aidlc-sync]` 即整輪 skip。**標記從 `record.sh` 的 `SYNC_MARKER` 取，不自抄**（沿用 U-10a 的 `SEC-1b`／`MARKER-1` 已建立的形狀——這是本 intent 第三次用到同一個常數，前兩次各自抄一份的代價已經付過）。**追溯**：R-4.2、R-4.3
- [ ] **Step 3 — 迴圈之前的一次 label 查詢（R-2 群）**：以 `aidlc-sync-reverse` 列出 PR，**開啟中** → `reverse_pending`，**關閉未合併** → `reverse_rejected`（R-6.2a，執行期集合、不進 `Config`）。查詢失敗 → 整輪中止 ＋ `ExternalError` ＋ 紅燈 ＋ 通報（R-2.5 fail-closed，**不得** fail-open，**不得**偽裝成 `suppressed`（R-2.6））。**追溯**：R-2.1–R-2.6、R-6.2a
- [ ] **Step 4 — 逐 record 迴圈的順序**：`read_sync_state` → U-1 action → **R-3.0 閘門** → 綁定分流。**R-3.0 必須在綁定分流之前**——這是 iteration 5 C-2 的修正，把它放回寫入鏈裡會讓首建路徑繞過 FR-J3。**追溯**：R-3.0–R-3.3、business-logic-model 序列圖
- [ ] **Step 5 — 首建路徑（R-3.1）**：`create_item` → `write_binding`。**追溯**：R-3.1、[req:FR-A1]
- [ ] **Step 6 — 寫入理由判定（R-5.2 ∪ R-5.6）**：三欄比對**或**有告示待送，任一成立才進寫入鏈。**追溯**：R-5.2、R-5.5、R-5.6
- [ ] **Step 7 — 寫入鏈與 R-5.10 分岔**：`status` 非 `null` → `write_status`（`expected` 由 `SyncState` 三欄重建，**不得**改取當下 `read_item`，R-5.7）；為 `null` 且 `reason_code` ∈ {`parked`,`suppressed`,`undecidable`} → 跳過 `write_status` 續走其餘（(a) 支）；∈ {`unparseable`,`whitelisted`} → 深度防禦，不寫任何看板（(b) 支，正常情況已被 R-3.0 擋下）。**追溯**：R-5.7、R-5.10
- [ ] **Step 8 — `Context` 組裝與 `render` → `write_body` → 回讀**：`decided_at`（本輪 `date -u`）／`scope_note`（U-1 第五 output 逐字轉交）／`rejection_notice`（R-6.2b）。`managed_block_hash` **必須取自寫入後的 `read_item`**，不得對 `render` 的輸出算 hash（R-5.4 的等價性，ADR-0015 §10——這條錯了會讓 U-8 每天為每個 intent 開一則反向 PR）。**追溯**：R-5.4、R-7 的 `Context` 表
- [ ] **Step 9 — R-5.12 的逐欄回寫（四種失敗各不相同）**：`write_status` 失敗 → 完全不回寫；`write_field` 失敗 → `last_field_value` 維持原值；`write_body` 失敗 → `managed_block_hash` **與 `last_synced_at`** 皆維持原值；R-5.4 回讀失敗 → 完全不回寫。**這四種不可壓成三種**（iteration 6 的 C-6.1／C-6.2 就是壓縮造成的）。**追溯**：R-5.12、R-5.13
- [ ] **Step 10 — 迴圈之後的 `resolve_if_open`（R-6.1）**：對本輪成功的每個 intent，以五個失敗值域**逐一**構成鍵呼叫。**不得**用 `SyncState.last_reason_code` 當鍵（R-6.1d：不同命名空間，且只在成功時才寫）。**追溯**：R-6.1a–R-6.1d
- [ ] **Step 11 — 薄外層 `aidlc-sync-forward.yml`**：`concurrency.group` 逐字為 `aidlc-sync-event-${{ github.repository }}-${{ github.event.pull_request.head.ref || github.ref_name }}`，`cancel-in-progress: false`。**追溯**：R-1.1、R-1.2、R-1.3
- [ ] **Step 12 — 測試（見下節）**
- [ ] **Step 13 — 突變驗證**：每條規則至少一條突變，逐條 改壞 → 紅 → 還原 → 複跑綠。
- [ ] **Step 14 — `code-summary.md`**（orchestrator 執筆）。

## 測試策略（**吸取 U-10a 的教訓**）

U-10a 連續兩輪的 reviewer findings 都源於同一件事：**拿文字／結構斷言去抓行為缺陷**。本單元的規則絕大多數是**行為**（順序、分流、四種失敗的不同回寫），故測試以行為層為主：

| 層 | 工具 | 抓什麼 |
| --- | --- | --- |
| **行為（主）** | `run-orchestration-tests.py`：以 stub 取代五支 composite action，餵各種 `Decision`／`SyncState`／PR 集合，斷言**呼叫序列**與**回寫的欄位集合** | 分流錯、順序錯、R-5.12 四種失敗的回寫錯、R-3.0 閘門被繞過 |
| 結構（輔） | YAML 解析斷言 | concurrency group 逐字、`cancel-in-progress: false`、`workflow_call` 的 input 集合 |

**R-5.12 的四種失敗各要一條行為測試**——它們的差異正是「哪幾欄回寫」，只有行為測試分得出來。

**真實 API 不在本 stage**：完成判準（「新 intent 首次推送後看板出現 item 且 Status 為 `Ready`」）需要真打 Projects v2，屬 Bolt 1 整合驗證。憑證已就緒（`opendiamonds` 帶 `project`＋`repo`）、測試看板 #23 存在，**但是否於本 stage 動用需人工裁決**（見 Q2）。

## 需人工裁決的兩項（**Q1 是阻塞**）

### Q1（**阻塞**）— `undecidable` 的 `write_field` 行為

查證 3 的完整依據見上。照 R-5.10 (a) 字面實作會**清空**自訂欄位，而 ADR-0015 §14 明令不得自行決定該行為。三個方向：

- **A. `undecidable` 跳過 `write_field`**（其餘照走 `render`／`write_body`／回讀／回寫）。欄位維持原值，最貼近「不猜」；代價是 R-5.10 (a) 的字面被收窄，需在 summary 標出並指派 Bolt 1 gate 追認。
- **B. 照字面走 `write_field`（寫空值＝清空）**。忠於已核可規則字面；但清空是一個沒人核可過的可觀察行為，且與 §14 的禁令實質牴觸。
- **C. 當場定案第五個前綴**（§14 說「具體字面待實作期與 `format_version` bump 一併定」，確認人 Bolt 1 gate）。一次解決；但會連帶觸發 `format_version` bump 與重新基準化，範圍遠大於本單元。

### Q2 — 本 stage 是否動用真實 Projects API

憑證與測試看板 #23 都就緒。**A. 不動用**（行為測試以 stub 為主，真實驗證留 Bolt 1）／**B. 動用**（對 #23 跑一次端到端，取得執行期證據）。
