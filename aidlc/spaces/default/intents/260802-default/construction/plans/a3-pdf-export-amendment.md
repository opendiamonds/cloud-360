# A3 Amendment — PDF Report Download

> Status: **IMPLEMENTED** — Q1=B, Q2=B, Q3=B, Q4=A


### 決策

| Q | 答案 |
|---|---|
| 1 | B — 前端 jsPDF＋html2canvas 一鍵下載 |
| 2 | B — 完整：分數／RiskCounts／支柱／發現／建議／meta |
| 3 | B — `complete` 或 `rules_only` |
| 4 | A — A3.view 即可 |

### 實作

- `frontend/src/utils/exportReviewPdf.ts`
- `AssessmentPage`「下載 PDF」鈕
- 依賴：`jspdf`、`html2canvas`
- 需求／FD：FR-A3-11、`frontend-components.md`、`business-rules.md` BR-A3-08

### Extension compliance

| Extension | Status |
|---|---|
| security/baseline | compliant（僅授權可讀評核之客戶端匯出；無新公網 API） |
| testing/property-based | N/A（UI 匯出） |
| bilingual-docs | compliant |
