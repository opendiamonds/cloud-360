# A3 Lens Editor — Functional Design（短）

> Unit `U-A3` 增量 · Requirements: `a3-lens-editor-requirements.md`  
> Execution: `a3-lens-editor-execution-plan.md`


### 1. 實體：`wa_lenses`

| 欄位 | 說明 |
|---|---|
| `id` | PK |
| `lens_id` | 穩定鍵，預設 `cloud360-core-mvp` |
| `is_active` | 僅一份 `true` 為現行標準 |
| `body_json` | 完整 Offline Custom Lens JSON（TEXT） |
| `updated_by` | FK → users |
| `updated_at` / `created_at` | 時間戳 |

### 2. 解析順序

`resolve_active_lens(db)` → active 列 → 否則 `cloud360-core-mvp-lens.json`。  
`start_review` 一律經此解析。

### 3. API（前綴 `/api/architecture`）

| Method | Path | 授權 |
|---|---|---|
| GET | `/lens/active` | **A3.review** |
| PUT | `/lens/active` | 同上；body = 完整 lens |
| GET | `/lens/new-question-template?pillar_id=` | 同上；回傳帶預設 riskRules 的題目 |
| POST | `/lens/suggest-improvement-plan` | 同上；`{ title }` → `{ displayText }` |

驗證：五柱 id 固定；每柱 ≥1 題；禁止 UI 路徑改既有 riskRules（PUT 時若客戶端送來完整 JSON，後端對**既有 question id** 強制保留原 `riskRules`／`id`；**新 id** 允許模板 riskRules）。

簡化實作（本期）：PUT 接受完整 JSON 並做結構驗證；前端編輯器**不展示** riskRules 編輯，新增題只插入模板；刪題前端強制每柱 ≥1。

### 4. UI

`AssessmentPage` 頂部 tab：`評核`｜`Lens 標準`（僅 `can('A3','review')`）。
Lens 標準：依柱展開題目，編 title／description／choices／improvementPlan；新增／刪除；儲存 PUT。

### 5. 部署

`schema_rbac.sql` 區塊 E 擴充 `wa_lenses`；`DEPLOY.md` 同步；`_ensure_a3_schema` 補表。
