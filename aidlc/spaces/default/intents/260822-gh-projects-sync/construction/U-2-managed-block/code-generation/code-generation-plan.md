# Code Generation Plan — U-2 受管區塊渲染與雜湊

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-2-managed-block · kind: library
     Generated: 2026-08-30T07:42:07Z（讀自 date -u） -->

## 交付

`.github/actions/aidlc-sync-block/`，`using: composite` ＋ `shell: bash`，以 `operation: render|parse|hash` 分派（[Q1=A]）。複雜度 **S**。

沿用 U-1 已核可的形狀：**邏輯放 `block.sh`，`action.yml` 只做介面轉接**。理由與 U-1 同——`unit-of-work.md` 的驗證方式是「純文字渲染與雜湊」，邏輯內嵌進 YAML 會讓 fixture 斷言必須先起 workflow。此形狀已在 U-1 經人工核可並實測可行。

## 三項需一併裁決的決定

### 決定 1：是否現在補 `has_managed_marker`（關掉 R-3.4 的 Critical）

`business-rules.md` R-3.4 要求「版本高於當前渲染器 → 回 `null`」，用意是**不覆寫**比自己新的區塊。但 `parse` 的簽章 `(issue_body) -> Block | null` 讓 R-3.1（沒有標記）與 R-3.4（版本較新）**回同一個 `null`**，呼叫端分不出來——於是最自然的實作「`parse` 回 `null` ⇒ 渲染一個寫進去」恰恰是 R-3.4 要防的覆寫。**R-3.4 的保護目前字面上不存在。**

ADR-0015 §6 已承載此項並給兩個修法，確認人指定為 **Bolt 1 gate**：(a) `parse` 回三態；(b) 另加廉價述詞 `has_managed_marker(issue_body) -> bool`。

**計畫傾向 (b)**：它是**純新增**，不動 `parse` 已核可的簽章，成本是一個 grep。(a) 要改上游定稿的簽章。

**但這是 gate 的決定，不是我的**——ADR-0015 §6 指名 Bolt 1 gate 為確認人，而 Plan Approval 正是一個人工閘門。若你選不做，實作會在 `block.sh` 與 `action.yml` 明寫「**R-3.4 的保護尚未生效，不得預設它已生效**」（`business-rules.md` 明文要求此註解）。

### 決定 2：`FORMAT_VERSION` 的起始值

`rejection_notice` 進 `Block` 被定為一次格式變更、須 bump（ADR-0015 §12）。但**本 intent 是首次上線，既有受管 item 數為 0**——「bump」在此沒有可重新基準化的對象。

- **傾向：起始值 `1`**，`format-migrations` 登錄表首筆記為初版、重新基準化說明寫「首次上線，既有受管 item 數 0，無需基準化」。ADR-0015 §12 的 bump 論證本來就以「這是最便宜的時點，因為既有 item 是 0」為理由——起始即含該欄位，等價於在零成本時點完成 bump。
- **替代：起始值 `2`**，登錄表補一筆不存在的 `1` 版。忠於「bump」字面，但會留下一個從未上線的版本號。

### 決定 3：`format-migrations` 登錄表的檔案形式

R-4.2／R-4.3 的互鎖要讀它。**傾向 `.github/actions/aidlc-sync-block/format-migrations.md`**（markdown 表格，人可讀、diff 好看，互鎖以 python3 解析最後一列），與 repo 既有 `scripts/*.py` 檢查工具的形狀一致。替代是 `.json`（解析簡單但人不易讀）。

## 實作步驟

### Step 1 — 目錄與骨架
- [x] `.github/actions/aidlc-sync-block/`：`action.yml`（`operation` 分派、逐操作在 `description` 列出必要 input 與有效 output）＋ `block.sh`
- [x] `operation` 值不合法時**立即以非零 exit 失敗**，不得靜默回空值（[Q1=A] 選項本文的承接方式）
- **追溯**：[Q1=A]、[ad:C-6]

### Step 2 — 格式常數
- [x] `MANAGED_BLOCK_BEGIN` / `MANAGED_BLOCK_END` 標記、`FORMAT_VERSION`（內嵌於區塊文字）
- [x] 兩段固定說明（OOS-2 不自動關閉、「自訂欄位為空的 item 不由本機制維護」）為**渲染器常數**，不是 `Block` 欄位
- **追溯**：R-1.3、R-1.4

### Step 3 — `render`（R-1 群五條）
- [x] R-1.1 兩支（有 Status ＋ `traceable_row`／不寫的 `reason_category` ＋ `decided_at`）
- [x] R-1.2 `scope_note` 使 `[S]` 與 `— SKIP` 的差別可見
- [x] R-1.3／R-1.4 固定說明逐字
- [x] R-1.5 `rejection_notice` 非 `null` 時額外載明「該次人工改動未被採納」與 `closed_at`；為 `null` 時**不渲染該段**
- [x] **`decided_at` 只在 `status = null` 的分支輸出**——值域已於 iteration 4 更正為可 `null`
- **追溯**：[US-OQ-3]、[US:S-6 AC 5]、[req:FR-F3]

### Step 4 — `parse`（R-3 群）
- [x] R-3.1 無標記 → `null`；R-3.2 版本缺失／不可解析 → `null`；R-3.3 已知版本 → 套對應解析器；R-3.4 版本較新 → `null`
- [x] **依決定 1**：補 `has_managed_marker` 或寫下「保護未生效」的實作註解
- [x] **round-trip**：`scope_note` 必須能原樣取回（U-1 的 R-6.3／R-6.5 為此而設；ADR-0015 §10 的雜湊等價不變式依賴它）
- **追溯**：R-3 群、ADR-A6、ADR-0015 §10

### Step 5 — `content_hash`（R-2 群）
- [x] 手工**正規化序列化**：固定欄位順序、固定分隔符、固定跳脫規則，再 `sha256sum`／`shasum -a 256`
- [x] R-2.3 `decided_at`、R-2.4 `format_version` 皆在涵蓋範圍內
- [x] **實作註解必須寫下 R-2.3 的隱含依賴**：churn 不發生只因為 [ad:services.md] S-A 的「有漂移才寫」。**這條依賴不在任何依賴圖上，也沒有任何測試會在它被破壞時失敗**——未來若有人加「定期刷新」或「每輪蓋一次以自癒」，每個 item 每輪都會變，且反向同步會讀成人為變更
- **追溯**：R-2 群、[Q2=A]

### Step 6 — 格式互鎖三道（R-4 群，ADR-A6 指派的機制）
- [x] R-4.1 golden fixture 快照與當前渲染器輸出**逐位元**一致
- [x] R-4.2 `FORMAT_VERSION` 等於 `format-migrations` 登錄表最後一筆的版本
- [x] R-4.3 登錄表最後一筆含**非空**的重新基準化說明與執行方式
- [x] **天花板要寫進註解**：三道互鎖保證作者無法「忘記」，**不保證他「做了」**——登錄表可被寫成空殼。這是 [Q1=C] 選項本文已載明的取捨，不是缺陷
- **追溯**：ADR-A6、[Q1=C]

### Step 7 — fixture 集
- [x] R-1.1 兩支各一；R-1.2 兩個只差 `scope_note` 的 `Context`；R-1.5 兩個只差 `rejection_notice` 的 `Context`（且 `parse` 回來分別為該值與 `null`）
- [x] R-3.1／3.2／3.3／3.4 各一；golden 快照
- **追溯**：R-1 群「可判定方式」欄

### Step 8 — 測試（Standard）
- [x] `run-fixtures.py`（沿用 U-1 的形狀）：渲染逐位元比對、round-trip、雜湊決定性
- [x] **完成判準三條各有斷言**：相同輸入相同雜湊／格式變更使雜湊改變／`parse` 對無標記 body 回 `null`
- [x] R-2.2 的「任一欄位不同必得不同雜湊」——逐欄位變動各一個斷言（`Block` 七欄）
- **追溯**：[ug:unit-of-work.md] U-2 完成判準

### Step 9 — 突變驗證
- [x] 至少 3 條：拿掉 R-1.5 的 `null` 分支、把 `decided_at` 移出雜湊涵蓋範圍、破壞 `scope_note` 的 round-trip。各自確認紅燈 → 還原 → 複驗綠

## 不在本單元範圍
- 寫入 issue body（U-3 的 `write_body`）、填 `Context` 的值（U-6）、告警（U-5）
- R-2.3 的 churn 斷言（「連續兩輪無語意變化 ⇒ `updated_at` 不變」）落在 **U-9**，本站只標出
