# A3 Amendment — Findings from Offline Custom Lens

> Status: **ANSWERS LOCKED / IMPLEMENTED** — Q1=B, Q2=A, Q3=A, Q4=A, Q5=B  
> Scope: 「發現」改與離線 Custom Lens 計分一致（U-A3 Construction 增量）  
> 實作摘要：`a3-findings-from-lens-amendment.md`


### 背景（已鎖定）

- 總分／RiskCounts 權威 = 離線 Custom Lens（Q1=D）
- 「發現」目前仍來自 `WaRuleEngine` 啟發式 → 與 Lens 易不一致
- 使用者已同意：**發現改走 Custom Lens 評估結果**

### 將調整的文件／程式（預覽）

| 類型 | 路徑 | 動作 |
|---|---|---|
| 需求／計畫 | `aidlc-docs/construction/plans/a3-findings-from-lens-questions.md`（本檔） | 新增 |
| 計畫摘要 | `aidlc-docs/construction/plans/a3-findings-from-lens-amendment.md` | 答完後寫 |
| FD | `construction/a3/functional-design/business-rules.md` | 修 BR-A3-04／05：發現來源＝Lens |
| FD | `construction/a3/functional-design/business-logic-model.md` | 流程：`lens_done` 後寫入 lens findings |
| FD | `construction/a3/functional-design/domain-entities.md` | Finding.code 對齊 question_id／risk |
| FD | `construction/a3/functional-design/frontend-components.md` | 發現表欄位（風險等級） |
| NFR | `construction/a3/nfr-design/logical-components.md` | 發現產出掛 `WaLensEngine` |
| Code 摘要 | `construction/a3/code/offline-lens-poc-summary.md` | 補 findings 對齊 |
| Code 摘要 | `construction/a3/code/well-architected-review-summary.md` | 同步 |
| 後端 | `backend/services/wa_lens_engine.py` | `findings_from_lens_score()` |
| 後端 | `backend/services/review_orchestrator.py` | `findings_json` 改存 Lens 發現 |
| 後端 | `backend/services/review_agent.py` | Agent 輸入改用 Lens findings（依 Q3） |
| 前端 | `frontend/src/pages/AssessmentPage.tsx` | 嚴重度／空狀態文案 |
| 測試 | `backend/tests/test_wa_lens_engine.py` | Lens→Finding 對照 |
| 狀態／稽核 | `aidlc-docs/aidlc-state.md`、`audit.md` | 階段追蹤 |

**不改（本期）**：lens JSON 題目內容、AWS API、啟發式規則檔本身（仍可作填答 fallback）。

---

## Questions

### Question 1
「發現」要顯示哪些 Lens 風險等級？

A) **僅 HIGH_RISK**

B) **HIGH_RISK + MEDIUM_RISK**（建議：與 RiskCounts 中／高對齊）

C) 三種皆列（含 NO_RISK，僅作「通過」資訊）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 2
Lens `risk` → Finding `severity` 對應？

A) HIGH→`high`，MEDIUM→`warn`，NO→不產生（若 Q1 含 NO 則 `info`）

B) HIGH→`critical`，MEDIUM→`high`，NO→`info`

C) 新增 severity 字串直接用 `HIGH_RISK`／`MEDIUM_RISK`（FE 顯示原文）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 3
ReviewAgent「改善建議」的輸入以誰為準？

A) **僅 Lens 發現**（與 UI 發現一致；建議）

B) Lens 發現 + 啟發式 RuleResult（雙軌輸入）

C) 維持現況（僅啟發式 RuleResult）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 4
`WaRuleEngine` 啟發式在本增量的角色？

A) **只做填答／內部 heuristic 分數**；`findings_json` **不再**寫啟發式發現

B) 啟發式發現仍寫入 DB 但不在 UI 顯示（欄位或 `scores.heuristic.findings`）

C) 完全移除本路徑對 `WaRuleEngine` 的呼叫（僅 Lens＋啟發式填答函式）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 5
離線 Lens 失敗時（Q6=A 啟發式仍完成），「發現」怎麼辦？

A) **空陣列**＋UI 提示「無 Lens 發現」；分數降級啟發式

B) **暫時回退啟發式 findings**（標註 `source=heuristic`）

C) 整次評核失敗（與既有 Q6=A 衝突，不建議）

X) Other (please describe after [Answer]: tag below)

[Answer]: B
