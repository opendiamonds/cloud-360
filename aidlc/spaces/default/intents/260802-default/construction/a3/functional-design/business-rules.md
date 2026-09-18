# A3 Business Rules — Well-Architected Review

> Unit `U-A3` · Story A3 MVP


### BR-A3-01 發起評核

1. 呼叫者須通過 JWT、非 Pending，且具 **A3.edit**。
2. 對 `diagram_id` 須有讀取權（owner 或分享可讀）；否則 **403**。
3. Body：`{ diagram_id, provider?, replace_latest? }`；`provider` 預設 `aws`。
4. 若 `provider ∈ {gcp, azure}`：建立列 `status=unsupported`，**不**跑規則／Agent；可經 SSE／JSON 回傳明確「未實作」（Q9=B）。FE 控件建議 disabled，但 API 允許建列。
5. 若 `provider=aws`：建列 `pending` → 載入 `xml_data` → 規則 → Agent（見流程模型）。

### BR-A3-02 歷史與 replace_latest（Q4=C）

1. 每次發起（含 unsupported）**新建**一列。
2. 若 `replace_latest=true`：將該 diagram 上先前 **非 archived** 且 `status ∈ {complete, rules_only, unsupported}` 的列設 `archived=true`（進行中列不強制 archive）。
3. 預設列表：`archived=false`，`created_at` 降序；詳情可依 id 讀 archived。

### BR-A3-03 讀取（Q5=A）

1. `GET` list／detail 需 **A3.view** + 對該 review 所屬 diagram 的讀取權。
2. 發起者與被分享者（含 Fiona）可看**同一報告**；無 diagram ACL → **403**（即使有 A3.view）。

### BR-A3-04 分數模型（離線 Lens 權威）

1. 五支柱皆計分（Operational Excellence、Security、Reliability、Performance Efficiency、Cost Optimization）。
2. **權威總分／支柱分／RiskCounts** 來自離線 Custom Lens `riskRules`（見 `wa_lens_engine`）。
3. `WaRuleEngine` 啟發式分數僅作內部／fallback（`scores.heuristic`），**不**作為 UI 權威總分。
4. Lens 風險換算分數：NO_RISK=100、MEDIUM_RISK=70、HIGH_RISK=40；總分 = Σ (pillar × weight)。

### BR-A3-05 規則引擎與發現（Findings←Lens 增量）

1. `WaRuleEngine.evaluate` 仍為純函式，用於填答輔助與 Lens 失敗備援；同 XML → 同啟發式結果。
2. **`findings_json`（UI「發現」）以離線 Lens 為準**（Q1=B：僅 HIGH＋MEDIUM；Q2=A：severity high／warn）。
3. Finding `code` 形如 `LENS-{question_id}`；`recommendation_hint` 取自未勾選 choice 的 `improvementPlan`。
4. Q4=A：啟發式發現**不**寫入權威 `findings_json`（僅 `source=heuristic` 於 Lens 失敗備援，Q5=B）。
5. 規則／Lens 解析崩潰 → SSE `error`；列保留 + `error_message`。

### BR-A3-06 Agent 建議（鎖定 AD）

1. 僅在規則成功且 `provider=aws` 後呼叫 **ReviewAgent**（Anthropic Agent SDK + OpenRouter；獨立模組）。
2. 輸入：DiagramSummary + **Lens findings**（與 UI 一致；Q3=A）；無完整 XML。
3. 建議**不推翻** Lens 發現；可引用 `code`／hint 擴寫。
4. Agent 失敗 → `status=rules_only`；分數／發現保留；UI「重試建議」只重跑 Agent。
5. 重試建議需 A3.edit + 同 diagram ACL；成功 → `complete`。

### BR-A3-07 SSE 契約

| 事件 | 時機 |
|---|---|
| `rules_done` | 啟發式分數寫入後（`findings` 暫空，待 Lens） |
| `lens_done` | Lens 計分完成（含權威 scores／**findings**） |
| `suggestion_delta` | Agent 文字增量 |
| `complete` | 建議寫入完成 |
| `error` | 管線／Agent／Lens 錯誤（`lens_error` 時可帶啟發式 findings） |
| `unsupported` | provider 非 aws 建列後 |

### BR-A3-08 PDF 匯出（FR-A3-11）

1. 呼叫者須具 **A3.view**，且對該評核所屬 diagram 有讀取權（與 GET detail 相同）。
2. 僅 `status ∈ {complete, rules_only}` 可下載。
3. **前端**以 html2canvas＋jsPDF 產生檔案（不含後端 PDF API）；內容含總分、RiskCounts、支柱分、發現、改善建議與 meta。
4. 檔名建議：`cloud360-wa-review-{id}.pdf`。

### BR-A3-09 Out of scope（本期）

SPOF／AZ 模擬與動畫、連雲端 Live 檢查。

### Testable Properties

| ID | 性質 |
|---|---|
| P-A3-01 | 同 XML + 同 rule_pack → findings code 集合與分數相同 |
| P-A3-02 | overall = 加權和（誤差 ≤ 0.01） |
| P-A3-03 | 無 A3.edit → POST 403 |
| P-A3-04 | 無 diagram 讀取權 → GET／POST 403 |
| P-A3-05 | Agent 失敗後 overall／findings 仍可讀；status=`rules_only` |
| P-A3-06 | `replace_latest=true` 後舊 complete 列 `archived=true` 且仍可 get by id |
