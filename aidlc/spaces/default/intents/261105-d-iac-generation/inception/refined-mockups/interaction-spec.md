# Interaction Spec — Story D IaC 工作區

<!-- Stage: refined-mockups · Q1–Q6=A。元件規格採 component-spec-template。 -->

## 上游輸入

- **mockups.md**、**stories.md**、**wireframes.md**

## 全域互動原則

| 原則 | 行為 |
|---|---|
| 檢視 ≠ 執行 | 步驟導覽永不呼叫 D1／D2／D3；僅各步主鈕／API 執行 |
| 進行中不可重送 | 請求未結束時對應 `iac-run-d*` 為 busy／disabled |
| 切圖優先於進行中寫回 | 脈絡 `diagram_id` 變更後，進行中回應不得寫入可下載草稿 |
| 無權 | 入口 disabled＋說明；執行 API 403（故事層） |

---

## StepNav

| Field | Value |
|---|---|
| Component | StepNav |
| Description | 左側三步驟切換（生成／掃描／Secrets） |
| Category | navigation |

### States

| State | Description | Trigger |
|---|---|---|
| default | 三步可點 | 進入工作區 |
| current | `aria-current="step"` | 使用者點選或 footer 下一步 |
| disabled | 不使用（Q2=A 自由檢視） | — |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA | `nav` landmark；目前步 `aria-current="step"` |
| Keyboard | Tab 聚焦各步；Enter／Space 切換 |
| Focus | 切步後焦點留在步驟鈕或移至該步 h2 |

### Responsive

| Breakpoint | Behaviour |
|---|---|
| mobile (&lt;768px) | 改頂部橫向捲動步驟列 |
| desktop (&gt;1024px) | 左側直列（mockups M2） |

---

## DiagramContextCard

| Field | Value |
|---|---|
| Component | DiagramContextCard |
| Description | aside 脈絡：圖下拉＋上傳（Q1=A） |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| default | 顯示當前圖名 | 進場帶入活躍圖 |
| empty | 無圖阻擋文案＋回 Workspace | 無活躍／可選／上傳圖 |
| error | 上傳失敗文字；圖名不變 | 非法類型／5xx／413 |
| cleared | 切圖後提示已清空產物 | 下拉／上傳導致 id 變更 |

### Accessibility

| Requirement | Implementation |
|---|---|
| Label | 「架構圖」可見 label 關聯 `iac-diagram-select` |
| Upload | 檔案 input 有可見／`aria-label`；錯誤 `aria-describedby` |
| Live | 切圖清空用 `aria-live="polite"` 文字，不單靠 toast 色 |

---

## AgentStatusPanel

| Field | Value |
|---|---|
| Component | AgentStatusPanel |
| Description | aside 進行中／待命文案（Q3=A） |
| Category | feedback |

### States

| State | Description | Trigger |
|---|---|---|
| idle | 「待命」或上次完成摘要 | 無進行中請求 |
| loading | 「正在產生／掃描／改寫…」 | D1／D2／D3 請求中 |
| error | 錯誤摘要＋指向重試 | 步驟失敗 |

### Accessibility

| Requirement | Implementation |
|---|---|
| Live | 容器 `aria-live="polite"`（`iac-agent-status`） |
| 不單靠動畫 | 必有文字狀態 |

---

## RunActionButton

| Field | Value |
|---|---|
| Component | RunActionButton |
| Description | 執行生成／掃描／改寫主鈕 |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| default | 可點（有對應 `edit`＋前置滿足） | — |
| disabled | 缺草稿／缺 D2 報告／缺權；附說明 | US3.1／US4.1 |
| loading | busy，不可再送 | 請求中 |

### Accessibility

| Requirement | Implementation |
|---|---|
| Disabled | 可聚焦或具名說明為何不可啟動（AC1.1.3） |
| Name | 可見文字「執行生成／掃描／改寫」 |

---

## FindingsList

| Field | Value |
|---|---|
| Component | FindingsList |
| Description | 掃描 findings（右欄） |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| empty-draft | 「請先完成生成」 | 無 D1 草稿 |
| empty-findings | 「無 finding」 | D2 成功零 finding |
| populated | 列含嚴重度文字＋標題 | D2 成功 |
| loading | 列表區骨架 | D2 進行中 |

### Accessibility

| Requirement | Implementation |
|---|---|
| 1.4.1 | 每列嚴重度為文字（`HIGH`／`CRITICAL` 或繁中等價），非僅色票 |
| Keyboard | 列可聚焦（表格或 list） |

---

## RewriteList

| Field | Value |
|---|---|
| Component | RewriteList |
| Description | Secrets 改寫項目清單 |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| gated | 執行 disabled；說明需 D2 成功報告 | 無 D2 報告 |
| empty | 「無可改寫項」 | D3 成功無項 |
| populated | 路徑／變數名列表（無明文） | D3 成功 |
| warning | status／alert 建議改寫文案 | 進入 Secrets 步 |

---

## DownloadConfirmDialog

| Field | Value |
|---|---|
| Component | DownloadConfirmDialog |
| Description | HIGH／CRITICAL 下載前摘要（Q4=A） |
| Category | feedback |

### States

| State | Description | Trigger |
|---|---|---|
| closed | 不掛載 | 無 HIGH／CRITICAL 或未點下載 |
| open | 計數或短清單＋取消／仍要下載 | 有 HIGH／CRITICAL 且點下載 |

### Accessibility

| Requirement | Implementation |
|---|---|
| Role | `role="dialog"`＋`aria-modal="true"`＋標籤 |
| Focus | 開啟焦點入 dialog；陷阱；Esc／取消關閉且**不**下載；關閉後焦點回下載鈕 |
| Keyboard | Tab 在取消／確認間；Enter 啟用聚焦鈕 |

---

## CopyCurrentFile

| Field | Value |
|---|---|
| Component | CopyCurrentFile |
| Description | 複製目前預覽檔 |
| Category | input |

### States

| State | Description | Trigger |
|---|---|---|
| disabled | 未選檔或無草稿 | — |
| success | 可見「已複製」；剪貼簿＝預覽全文（或凍結截斷規則） | 複製成功 |

---

## FooterStepControls

| Field | Value |
|---|---|
| Component | FooterStepControls |
| Description | 上一步／下一步（純導覽） |
| Category | navigation |

**契約**：下一步 ≡ 點選下一步驟；**永不**觸發執行 API（Q2=A）。
