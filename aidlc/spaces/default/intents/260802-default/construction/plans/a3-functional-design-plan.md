# U-A3 — Functional Design Plan

> Unit: `U-A3` (Well-Architected Review)  
> Story: **A3** MVP（分數＋發現＋LLM 建議；無 PDF／SPOF）  
> Inputs: `a3-well-architected-requirements.md`, `stories.md` §A3, `application-design/a3-*.md`  
> Branch: `luojingting/feat/a3-well-architected-review`  
> Status: **COMPLETE**（2026-07-23）— 已核准；下一階段 NFR Requirements


### Checklist

- [x] 釐清問題全部作答（見下方 Questions + Q2b）
- [x] 產出 `construction/a3/functional-design/domain-entities.md`
- [x] 產出 `construction/a3/functional-design/business-rules.md`
- [x] 產出 `construction/a3/functional-design/business-logic-model.md`
- [x] 產出 `construction/a3/functional-design/frontend-components.md`
- [x] Stage completion + audit（使用者核准後勾）

### 決策摘要

| Q | 答案 |
|---|---|
| 1 | A — 五支柱全開 |
| 2 | B — 加權平均 |
| 2b | C — OE 10% · Sec 30% · Rel 30% · Perf 15% · Cost 15% |
| 3 | B — Finding 含 `recommendation_hint` |
| 4 | C — 新建 + 可選 `replace_latest` 軟隱藏 |
| 5 | A — A3.view + diagram 讀取 ACL |
| 6 | B — 中等規則包 ~15–20 |
| 7 | A — 結構化摘要 + RuleResult（無完整 XML） |
| 8 | A — `/assessment`；Sidebar「評估儀表板」 |
| 9 | B — 非 aws → `status=unsupported` 列 |
| 10 | A — `rules_only` + 重試建議 |

### 範圍摘要

```text
User (A3.edit + diagram ACL)
  → POST /api/architecture/reviews { diagram_id, provider, replace_latest? }
  → WaRuleEngine.evaluate(xml) → ArchitectureReview (rules_complete)
  → SSE rules_done
  → ReviewAgent suggestions (SSE deltas)  // summary + RuleResult only
  → ArchitectureReview (complete | rules_only)
  → GET list/detail (A3.view + diagram ACL)
  → retry-suggestions when rules_only
```

---

## Questions

（歷史問答保留；答案見上表。）

### Question 1
本期 MVP 規則引擎要覆蓋哪些 **AWS Well-Architected 支柱**？

A) **五支柱全開**（Operational Excellence、Security、Reliability、Performance Efficiency、Cost Optimization）— 規則可淺，但分數維度齊全

B) **三支柱優先**：Security + Reliability + Cost Optimization（其餘 UI 顯示 N/A／0，標「下期」）

C) **四支柱**：Security + Reliability + Performance Efficiency + Cost Optimization（Operational Excellence 下期）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 2
**分數模型**怎麼定？

A) 每支柱 **0–100**；總分＝支柱算術平均；發現依 severity 扣分（規則表固定權重）

B) 每支柱 **0–100**；總分＝加權平均（請在 Answer 後附權重，例 Sec 30%／Rel 30%／…）

C) 僅顯示 **發現計數＋severity 分布**；無 0–100「健康分」（支柱用 pass／fail／warn）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 3
單一 **Finding** 最少要有哪些欄位？（影響 schema／FE 列表）

A) `code`, `pillar`, `severity`（info｜warn｜high｜critical）, `title`, `message`, `node_ids[]`（可空）

B) 同上，另加 `recommendation_hint`（規則端短提示；LLM 再擴寫全文）

C) 精簡：`pillar`, `severity`, `message` only（無穩定 code／無 node 對應）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 4
對**同一 diagram** 再次發起評核時？

A) **永遠新建** `architecture_reviews` 列（歷史完整保留；列表最新在上）

B) 若存在 `status` 進行中（`pending`／`rules_complete`）→ **拒絕**新請求（409）；完成後才可再建

C) 新建，但可選 `replace_latest=true` 軟隱藏舊完整列（仍可查 archived）

X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 5
**讀取權限**：誰可 `GET` 某次評核詳情／歷史？

A) 具備 **A3.view**，且對該 `diagram_id` 有讀取權（owner 或已分享）— Fiona 可看 Hannah 對分享圖跑出的同一報告

B) 僅 **評核發起者**＋具 A3.view 的 Platform_Admin／Project_Admin

C) 凡有 A3.view 即可看租戶內所有評核（不綁 diagram ACL）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 6
規則引擎 **MVP 規則包**深度？

A) **最小可測包**（約 5–8 條）：例單 AZ／無備援 DB、公開 SG 樣式、缺監控節點、單一區域、無備份標註等（以 draw.io 標籤／shape 啟發式）

B) **中等包**（約 15–20 條）對齊常見 WA 檢查項（仍啟發式，不連 AWS API）

C) 先做 **規則框架＋2–3 示範規則**；其餘規則 Code Gen 後迭代（FD 只定 schema／介面）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 7
送給 **ReviewAgent** 的輸入粒度？

A) **結構化摘要**：節點／邊精簡 JSON + 完整 `RuleResult`（**不**傳完整 mxGraph XML）

B) 摘要 + RuleResult + **截斷後的 XML**（上限 N KB；請在 Answer 寫 N，預設 64）

C) 盡量送 **完整 XML** + RuleResult（靠模型上下文；超長則失敗 SSE error）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 8
Assessment 前端路由與 Sidebar 標籤？

A) 路徑 **`/assessment`**；Sidebar「評估儀表板」（需 A3.view）

B) 路徑 **`/reviews`**；Sidebar「Well-Architected」

C) 路徑 **`/assessment`**；Sidebar「Well-Architected 評核」

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 9
`provider` 非 `aws`（gcp／azure）時 API 行為？

A) **HTTP 400**（或 501）＋明確 `not_implemented`；FE 控件 disabled

B) 允許建立 review 列但 `status=unsupported`；不跑規則／Agent

C) FE 完全隱藏非 aws；API 若收到非 aws 仍 400

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 10
LLM／Agent 失敗後的 **review.status** 與 UI？

A) `rules_only`：規則分數／發現可看；建議區顯示錯誤＋「可重試建議」（不重跑規則）

B) `failed`：整次評核標失敗，但規則 JSON 仍存檔可看

C) 與 A 相同，另提供「整次重跑」（新建一列）按鈕為主、不單獨重試建議

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Follow-up（必答 — Q2 加權未定義）

### Question 2b
Q2 選 **B（加權平均）**，請定五支柱權重（加總須為 **100%**）。建議預設如下，可改：

A) **採用建議權重**：Operational Excellence 15% · Security 25% · Reliability 25% · Performance Efficiency 15% · Cost Optimization 20%

B) **等權**：每支柱 20%

C) **安全／可靠優先**：OE 10% · Sec 30% · Rel 30% · Perf 15% · Cost 15%

X) Other — 請在 Answer 後寫出五個百分比（加總 100）

[Answer]: C
