# A1 ↔ A3 Multi-Agent 協作需求

> AIDLC Inception → Requirements Analysis  
> Branch: `luojingting/feat/a1-ux-optimize`  
> 問答：`inception/plans/a1-a3-multi-agent-questions.md`


### 1. Intent

| 項目 | 判定 |
|---|---|
| 使用者意圖 | 產架構圖時讓 Design 與 WA Review 對話迭代，目標 lens 總分 ≥ 80 |
| 類型 | Brownfield（A1 產圖路徑＋A3 評核回饋） |
| 複雜度 | High |
| Depth | Standard（MVP 雙 agent＋2 輪＋預覽套用） |

### 2. 決策摘要（Q1–Q8）

| # | 決策 |
|---|---|
| Q1 | Workspace **聊天產圖自動**進入協作迴圈 |
| Q2 | **真雙 agent 對話**：Design ↔ Review 輪流發言，transcript 可見 |
| Q3 | **硬門檻** `overall_score >= 80`；達最大輪數仍未達標 → 失敗／需人工 |
| Q4 | 最多 **2** 輪（初產＋一次依對話改圖） |
| Q5 | 達標分數以 **offline lens 加權**為準（與正式 A3 一致） |
| Q6 | ~~預覽後套用~~ → **產圖後直接呈現畫布／評估來源**（2026-07-28 使用者覆寫） |
| Q7 | **Workspace＋Assessment**「依建議改圖」皆可進同一迴圈 |
| Q8 | 沿用 **aws／gcp／azure** provider（偵測＋覆寫） |

### 3. Functional Requirements

| ID | 需求 |
|---|---|
| FR-MA-01 | Workspace 送出產圖請求後，後端啟動 Design→評核→Review 發言→（必要時）Design 改圖→再評核 |
| FR-MA-02 | SSE 串流：`message`（含 `speaker`: design／review）、`progress`、`xml_preview`、`score`、`complete`／`error` |
| FR-MA-03 | 每輪改圖以 `xml_preview`／`complete.xml` 推送並**立即寫入畫布或 Assessment 評估來源**（不經「套用預覽」確認） |
| FR-MA-03b | Assessment「優化」：報告含 **HIGH_RISK** 時可點；評核進行中或無高風險時反灰；按鈕文案為「優化」 |
| FR-MA-04 | 第 1 輪：Design 產圖 → lens 打分；**無 HIGH_RISK** 則成功結束；有高風險則 Review 依 findings（優先高風險）發言 |
| FR-MA-05 | 第 2 輪：Design 讀取 Review 發言＋高風險清單＋現有 XML 改圖 → 再 lens 打分 |
| FR-MA-06 | 第 2 輪後仍有 HIGH_RISK → `complete.status=failed`，回傳最佳圖、分數、剩餘 findings |
| FR-MA-07 | Assessment：對目前圖／上傳 XML 提供「優化至 WA ≥ 80」，重用同一 API（`current_xml`＋優化意圖） |
| FR-MA-08 | provider：請求可帶；未帶則偵測；與 A3 規則／Active Lens 一致 |
| FR-MA-09 | 協作結束可選寫入一筆 `architecture_reviews`（與正式評核同源分數），供歷史查詢 |
| FR-MA-10 | 權限：啟動需 A1 編輯（產圖／改圖）；Assessment 入口需 A3.edit；套用寫入畫布需存圖權 |

### 4. Non-Goals（本期不做）

- 超過 2 輪自動迭代
- 未達 80 仍自動寫入畫布
- 呼叫雲端官方 WA API
- 完整 OpenClaw Routing Agent（僅 A1↔A3 專用 orchestrator）

### 5. Acceptance（摘要）

1. Workspace 產圖自動出現 Design／Review 交替訊息與分數進度。  
2. 達 ≥80 時提示成功並可「套用」圖面。  
3. 兩輪後仍未達標時明確失敗提示，不阻擋使用者手動改圖後重試。  
4. Assessment「優化至 WA ≥ 80」可對既有圖啟動相同流程。  
5. 分數與 Assessment 正式評核同源（lens）。
