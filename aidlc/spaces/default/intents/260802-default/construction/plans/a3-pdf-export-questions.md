# A3 Amendment — PDF Report Download

> Status: **ANSWERS LOCKED / IMPLEMENTED** — Q1=B, Q2=B, Q3=B, Q4=A  
> Context: 原 MVP 不做 PDF；已補回 FR-A3-11（前端 html2canvas＋jsPDF）


### 背景

| 現況 | 說明 |
|---|---|
| 需求 | FR 無 PDF；Out of Scope 列「可下載 PDF 報告」 |
| FD | `frontend-components.md` 標 PDF 下載鈕為下期 |
| 程式 | Assessment 尚無匯出 |

本增量將 PDF 從 out-of-scope **拉回本期**，並更新 requirements／FD／Code。

### 將調整的文件（預覽）

| 路徑 | 動作 |
|---|---|
| `inception/requirements/a3-well-architected-requirements.md` | 新增 FR-A3-11；Out of Scope 移除 PDF |
| `construction/a3/functional-design/frontend-components.md` | 下載鈕／內容範圍 |
| `construction/a3/functional-design/business-rules.md` | BR：誰可下載、僅 complete／rules_only |
| `construction/a3/code/*-summary.md` | 實作摘要 |
| `frontend` Assessment 匯出 UI＋產生 PDF | Code Gen |
| （可選）`backend` PDF endpoint | 僅當選伺服端方案 |

---

## Questions

### Question 1
PDF 產生方式？

A) **瀏覽器列印／另存 PDF**（`window.print` 專用預覽樣式；無新依賴，最快）

B) **前端產生檔案下載**（例 html2canvas／jsPDF，一鍵 `.pdf`）

C) **後端產生 PDF**（API 回傳檔案；需服務端套件）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 2
PDF 內容要包含哪些？

A) **精簡**：總分、RiskCounts、支柱分、發現清單（不含建議全文）

B) **完整**（建議）：上列 ＋ 改善建議全文 ＋ 評核 meta（id／時間／diagram／Lens 名）

C) 僅分數與 RiskCounts（無發現／建議）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 3
何時可下載？

A) **僅 `complete`**

B) **`complete` 或 `rules_only`**（有分數／發現即可；建議可空）（建議）

C) 任一已存歷史列（含 unsupported）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 4
權限？

A) 有 **A3.view** 且能讀該評核即可下載（建議）

B) 僅 **A3.edit**

X) Other (please describe after [Answer]: tag below)

[Answer]: A
