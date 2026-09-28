# Code Generation Plan — U-8 反向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service
     Created: 2026-09-05T17:42:42Z（讀自 date -u） -->

## 交付物

| 檔案 | 內容 |
| --- | --- |
| `.github/workflows/aidlc-sync-reverse-impl.yml` | `on: workflow_call`，全參數化（ADR-A10） |
| `.github/workflows/aidlc-sync-reverse.yml` | 薄外層：`schedule` ＋ `workflow_dispatch` ＋ concurrency |
| `.github/actions/aidlc-sync-reverse/run-reverse-tests.py` | 行為測試（stub，離線）——**主力** |

複雜度 **M**。不新增依賴。

## 開工前查證（**含 `open-items.md` 全項與條目內但書**——U-7 的教訓）

### 查證 1 — `open-items.md` 四項與其內部但書

| 項目 | 對 U-8 的意義 |
| --- | --- |
| **C-7.1** | **已於 U-7 修好**（R-6.1 不再推進 `last_synced_at`）。U-8 是讓它「從潛伏變成真的」的單元——修好之後這條路已關 |
| **C-7.2** | 實作面已由 U-6 滿足；殘留的四處上游文件不由本站回改 |
| **M-7.1／M-7.2** | 落點寫 `code-generation`，已由 U-6 的實作涵蓋（見 U-7 的 summary 交叉核對表） |
| **#11**（U-7 iteration 2 新增） | R-6.8 的 `last_synced_at` 殘留視窗。**U-8 上線會讓它可達**——但修法屬上游 R-6.8，不由本站修 |

**條目內但書的追查**（U-7 漏掉的那一層）：`open-items.md:137` 的「該欄現有三個寫者，本輪只對兩個做了語意對齊」已由 #11 承接，無其他未追的但書。

### 查證 2 — `REVERSE_PR_LABEL` 的來源（Q1 的由來）

`grep -n 'REVERSE_PR_LABEL='` 實測：唯一字面在 **U-6 的 `forward-impl:157`**，U-7 於 `reconcile-impl:222` 以 `sed` 推導。**U-8 依 Q1=A 同樣推導**，全 repo 維持一份字面。

### 查證 3 — U-8 讓兩項既有風險變成可達

| 風險 | 狀態 |
| --- | --- |
| C-7.1 | **已關**（U-7 修） |
| open item #11（R-6.8 殘留視窗） | **本單元上線後可達**，修法屬上游，已登錄 |
| **U-8 ＋ U-10b 是真捆綁** | R-5 逐字：U-8 先上而 U-10b 未上線 ⇒ **每個反向 PR 都送進含 6 次 LLM agent 執行的完整 gauntlet**。本站不實作排除（那是 U-10b），但必須產生可被排除的標記（R-2.3 的分支名前綴） |

### 查證 4 — C-2／C-6 在本單元的設計中已正確

R-4c 的更正註明確寫「`parse` 與 `content_hash` 原標為 C-2，實際屬 **C-6 `managed-block`**」。**本站沿用該更正**，不重蹈 U-7 的代號混淆。

## 計畫步驟

- [ ] **Step 1 — impl 骨架與參數**：`on: workflow_call`，inputs 沿用 U-7 那一組（含 `trunk_ref`）；secret 為同步 token。**追溯**：ADR-A10、ADR-0016 §1
- [ ] **Step 2 — R-1 群：何時開 PR**。`read_item` → `parse`（`null` ⇒ **跳過，不視為人為變更**）→ `content_hash` → 與 `sync-state.json` 的 `managed_block_hash` 比對。**雜湊未變 ⇒ 不產生 PR**（完成判準第二條，防迴圈第一道防線在反向側的體現）。**追溯**：R-1.1–R-1.5
- [ ] **Step 3 — R-1.4／E-2：每個有變更的 intent 各開一個 PR**（不是單一 PR 含全部）。**追溯**：R-1.4、R-3.1
- [ ] **Step 4 — R-6.1：防重複開 PR 用即時查詢**，以 label 查該 intent 是否已有**開啟中**的反向 PR。**不看儲存欄位**——把「PR 的內容」與「PR 是否存在」混為一談正是 iteration 1 那個 Critical 的成因。**追溯**：R-6.1
- [ ] **Step 5 — R-2 群：PR 的內容邊界**。diff **只含**該 intent 的 `<record>/sync-state.json`；**不得含 `aidlc-state.md` 任何一行**。R-2.1 在 E-1 之下結構性成立，**但仍要有斷言**（R-2.1 自己的原文）。分支名 `aidlc-sync/reverse/<intent_id>-<date>`，label 由 Q1=A 推導。**追溯**：R-2.1–R-2.3
- [ ] **Step 6 — R-1.5：PR 的 base 為 `ut`，不得直接推 `ut`**。**追溯**：R-1.5、[req:FR-G1]
- [ ] **Step 7 — R-6.3：E-1 的原子性失敗**。`pending_reverse` 已 commit 但 PR 開不成 ⇒ **刪除該分支**；刪除也失敗則保留孤兒分支。**兩種情形都在同一次執行內記入報告並紅燈**，附 intent id 與分支名。**不留給下一輪、不留給 U-7**。**追溯**：R-6.3、R-6.0
- [ ] **Step 8 — R-6.2：不清除 `pending_reverse`**（沒有讀者就沒有陳舊問題）。**追溯**：R-6.2
- [ ] **Step 9 — Q2=A：`notify`／C-5**。外部失敗時開通報 issue，比照 U-6／U-7 的形狀。**追溯**：R-4c、ADR-0015 §5、[req:FR-E1]／[US:S-8 AC 1]
- [ ] **Step 10 — 薄外層**：`schedule`（cron 避開 `0 23 * * 1-5`／`37 0 * * *`／`39 16 * * 1` 與 U-7 的值）＋ `workflow_dispatch` ＋ 自成一組的 concurrency。**追溯**：R-5（U-7）、NFR-P3
- [ ] **Step 11 — 測試**（見下節）
- [ ] **Step 12 — 突變驗證**
- [ ] **Step 13 — `code-summary.md`**（orchestrator 執筆）

## 測試策略（吸取 U-6／U-7 四輪 review 的教訓）

**硬要求，逐條**：

1. **行為測試為主**，stub 取代上游元件，斷言**呼叫序列**與**每次寫入的內容**。
2. **每條測試都要有前提斷言**——先確認情境真的發生了再斷言後果。**計畫鍵名一律 `"exit"`**（U-6 用錯成 `"rc"` 讓整條測試在空前提上恆真通過）。
3. **突變要打中「對應的那一條」**，不是打中別條（U-6 的 M18 就是打中別條而誤以為有效）。
4. **錯誤處理分支必須各有測試**——U-7 有兩條零覆蓋的錯誤分支，是「整段拿掉仍全綠」才被抓到的。本單元的 R-6.3（PR 開不成 → 刪分支 → 刪不掉 → 孤兒）**三種結局各要一條**。

**必測清單**：
- R-1.2 雜湊未變 ⇒ **零 PR、零寫入**（防迴圈第一道防線）
- `parse` 回 `null` ⇒ **跳過**，不誤判為人為變更
- R-2.1 diff **不含 `aidlc-state.md`**（結構上成立仍要斷言——R-2.1 自己的要求）
- R-2.2 diff **只含**該 intent 的 `sync-state.json`
- R-1.4／E-2：兩個 intent 有變更 ⇒ **兩個 PR**，不是一個
- R-6.1 已有開啟中的 PR ⇒ **不開第二個**（且用即時查詢，不看儲存欄位）
- R-6.3 的三種結局各一條
- **Q3=A：over-suppression 的反例**——PR 含 X 不含 Y ⇒ 該 PR 只貢獻 X 一個 intent id。**測試註解須明寫它不能取代 Bolt 3 的實測**
- Q2=A：外部失敗 ⇒ 通報 issue（不只紅燈）
- 薄外層 cron 不與四個既有值碰撞（靜態斷言）
- `REVERSE_PR_LABEL` 從 U-6 推導（漂移即紅）

**不動用真實 API**：不得開真實 PR（public repo 會留下永久編號），不得寫 #16／#23。
