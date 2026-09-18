# U-A3 — NFR Requirements Plan

> Unit: `U-A3` (Well-Architected Review)  
> Status: **COMPLETE**（2026-07-23）— 已核准；下一階段 NFR Design


### Checklist

- [x] 釐清問題全部作答
- [x] 產出 `construction/a3/nfr-requirements/nfr-requirements.md`
- [x] 產出 `construction/a3/nfr-requirements/tech-stack-decisions.md`
- [x] Stage completion + audit（使用者核准後勾）

### 決策摘要

| Q | 答案 |
|---|---|
| 1 | B — 規則 p95 ≤ 5s |
| 2 | C — Agent 60s；並行不限制 |
| 3 | A — 結構化 audit（無 XML／建議全文） |
| 4 | A — Best-effort |
| 5 | A — 規則引擎 PBT ≥3 |
| 6 | B — 結構化 log；metrics 有則做 |
| 7 | A — 完全沿用 stack |
| 8 | A — UX 與 Workspace 同等 |

### 已鎖定（不重問）

| 來源 | 內容 |
|---|---|
| NFR-A3-01…05 | 見 inception requirements |
| AD／FD | Agent SDK + OpenRouter；monolith |
| Extensions | security/baseline、property-based 強制 |

---

## Questions

### Question 1
**規則階段**延遲目標（單次 `evaluate`，不含 LLM）？

A) **p95 ≤ 2 秒**（中等圖；失敗則記 log，仍回結果或 error）

B) **p95 ≤ 5 秒**（較寬鬆，適合較大 XML）

C) **無硬 SLO**；僅「體感秒級」＋手動驗收

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 2
**LLM／Agent** 逾時與併發？

A) 單次建議 **60s** timeout；同一使用者同時僅 **1** 個進行中評核（第二個 409）

B) 單次 **120s**；同使用者最多 **2** 個並行

C) 單次 **60s**；並行不限制（只靠伺服器資源）

X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 3
**安全性／稽核**（在 NFR-A3-01 之上）本期要到哪？

A) **最小**：既有 JWT＋A3 RBAC；評核發起／讀取 **結構化 audit log**（user_id、review_id、diagram_id、action；**不含** XML／建議全文）

B) 同上 + 建議全文僅存 DB；log 可含 suggestions **長度／hash**，不可含原文

C) 僅 RBAC；**不做**專用 audit 事件（沿用存取 log 即可）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 4
**可用性／可靠性**期望（本 MVP）？

A) **Best-effort**：隨現有 API 進程；重啟可中斷 SSE；客戶端可重開詳情／重試建議

B) 目標 **99%** 月可用（評核 API）；需額外監控告警（請在 Answer 註告警通道若有）

C) 評核請求入 **背景佇列**（Redis／worker）以提高韌性（允許引入新元件）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 5
**Property-based testing** 覆蓋期望？

A) **規則引擎核心**：分數加權、扣分、同 XML 不變性（至少 3 條 Hypothesis 性質）

B) A + Finding schema／severity 枚舉不變量

C) A + B + API authz 性質（無 token／無 A3 → 403）用 Hypothesis 或 parametrize 皆可，但須自動化

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 6
**可維護性／可觀測**？

A) 結構化 log：`review_id`、`status` 轉換、規則耗時、Agent 耗時／錯誤碼；**無**新 APM

B) A + 簡單 metrics 計數（評核成功／rules_only／unsupported）— 若現有堆疊無 metrics 則延後，FD 只要求 log

C) 必須接 OpenTelemetry／外部 APM（請在 Answer 指名）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 7
**Tech stack**（本 unit）？

A) **完全沿用**：FastAPI + SQLAlchemy／既有 models、React／Vite、Anthropic Agent SDK + OpenRouter、unittest + Hypothesis；**不**新增 DB 以外基礎設施

B) 允許新增輕量前端依賴（例 SSE helper）；後端不新加服務

C) 允許引入佇列／快取（與 Q4=C 對齊時選此）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 8
Assessment **可用性／UX**（非功能）？

A) 與現有 Workspace 同等：載入／錯誤／空狀態文案即可；無 WCAG 正式驗收

B) 基本鍵盤可操作主要按鈕＋對比度跟現有主題；無正式 audit

C) 需達到 WCAG 2.1 AA（請在 Answer 註範圍）

X) Other (please describe after [Answer]: tag below)

[Answer]: A
