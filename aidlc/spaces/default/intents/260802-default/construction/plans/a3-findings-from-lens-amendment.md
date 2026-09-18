# A3 Amendment — Findings from Offline Custom Lens

> Status: **IMPLEMENTED** — Q1–Q5 locked (B/A/A/A/B)


### 鎖定決策

| Q | 答案 |
|---|---|
| 1 | B — HIGH＋MEDIUM |
| 2 | A — high／warn |
| 3 | A — Agent 用 Lens findings |
| 4 | A — 啟發式不寫權威 findings |
| 5 | B — Lens 失敗回退啟發式 findings |

### 已更新 artifacts

- FD：`business-rules.md`
- NFR：`logical-components.md`
- Code 摘要：`offline-lens-poc-summary.md`
- 實作：`wa_lens_engine.findings_from_lens_score`、`review_orchestrator`、`AssessmentPage`、prompt、tests

### Extension compliance

| Extension | Status |
|---|---|
| security/baseline | N/A（無 IAM／網路變更） |
| testing/property-based | compliant（單元測 Lens→Finding） |
| bilingual-docs | compliant |
