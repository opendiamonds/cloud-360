# A3 Domain Entities — Well-Architected Review

> Unit `U-A3` · Story A3 MVP  
> Decisions: `construction/plans/a3-functional-design-plan.md`（Q1–Q10 + Q2b）


### 1. 實體關係

```text
User ──owns/shares──> UserDiagram (U-A2)
                          │
                          │ 1:N
                          v
                   ArchitectureReview
                          │
                          ├── scores_json (支柱分數 + 總分)
                          ├── findings_json (Finding[])
                          ├── suggestions_text / suggestions_stream 累積
                          └── created_by → User
```

### 2. ArchitectureReview（表 `architecture_reviews`）

| 欄位 | 型別（邏輯） | 說明 |
|---|---|---|
| `id` | UUID / int PK | 評核 ID |
| `diagram_id` | FK → user_diagrams | 評核對象 |
| `created_by` | FK → users | 發起者 |
| `provider` | enum string | `aws`｜`gcp`｜`azure`（MVP 僅 aws 跑引擎） |
| `status` | enum | 見下表 |
| `overall_score` | float nullable | 加權總分 0–100；`unsupported` 可 null |
| `scores_json` | JSON | 五支柱分數 + 權重快照 |
| `findings_json` | JSON | Finding[] |
| `suggestions_text` | text nullable | Agent 建議全文（完成後） |
| `error_message` | text nullable | Agent／管線錯誤（`rules_only` 時） |
| `rule_pack_version` | string | 例 `wa-aws-mvp-1` |
| `archived` | bool | `replace_latest=true` 時舊完整列設 true（仍可查） |
| `created_at` / `updated_at` | datetime | |

#### status

| 值 | 意義 |
|---|---|
| `pending` | 已建列、規則尚未寫入 |
| `rules_complete` | 規則完成；Agent 進行中 |
| `complete` | 規則＋建議皆完成 |
| `rules_only` | 規則完成；Agent 失敗（可重試建議） |
| `unsupported` | `provider`≠aws；不跑規則／Agent（Q9=B） |

### 3. Finding（存於 `findings_json`）

| 欄位 | 說明 |
|---|---|
| `code` | 穩定規則碼（例 `REL-SINGLE-AZ-DB`） |
| `pillar` | `operational_excellence`｜`security`｜`reliability`｜`performance_efficiency`｜`cost_optimization` |
| `severity` | `info`｜`warn`｜`high`｜`critical` |
| `title` | 短標題 |
| `message` | 規則說明 |
| `node_ids` | string[]（draw.io cell id；可空） |
| `recommendation_hint` | 規則端短提示；LLM 擴寫全文建議（Q3=B） |

### 4. RuleResult（引擎輸出 DTO，非表）

| 欄位 | 說明 |
|---|---|
| `provider` | aws |
| `rule_pack_version` | |
| `pillar_scores` | map pillar → 0–100 |
| `overall_score` | 加權總分 |
| `weights_snapshot` | 本次使用權重 |
| `findings` | Finding[] |

### 5. DiagramSummary（給 ReviewAgent，非表）

結構化摘要：**節點／邊精簡 JSON** + 完整 `RuleResult`；**不傳**完整 mxGraph XML（Q7=A）。

### 6. 權重快照（Q2=B，Q2b=C）

| Pillar | Weight |
|---|---|
| operational_excellence | 10% |
| security | 30% |
| reliability | 30% |
| performance_efficiency | 15% |
| cost_optimization | 15% |

寫入每次 `scores_json.weights`，避免日後改權重影響歷史解讀。

### 7. 權限語意（與實體）

| 旗標 | 行為 |
|---|---|
| A3.edit | `POST` 發起評核；重試建議 |
| A3.view | `GET` list／detail（**且**對 diagram 有讀取權：owner 或分享）（Q5=A） |
| A3.review | 審核語意預留；MVP 不另開流程 |

Pending 使用者（J5）→ 不可評核（FR-A3-10）。
