# 資料庫 Schema — C1 估價上傳（Estimate Intake）

> Intent：`260916-estimate-upload-rework`  
> 本檔為本 record 的 **governing database schema section**，對齊 `schema_rbac.sql`、`backend/models.py`、`backend/database.py::_ensure_estimate_intake_schema()`、`DEPLOY.md` §2.2.5。  
> baseline A2／A4 schema 見 `260802-default/construction/database-schema.md`（不含估價表）。

## 契約變更聲明（本 PR 補登）

下列欄位為**刻意的資料庫契約變更**（非可省略的實作細節），對應 FR1.7／FR13／C1-W1／C1-S1：

| 表 | 欄位 | 型別 | 可空 | 用途 |
|---|---|---|---|---|
| `estimate_sets` | `workload_context_json` | `TEXT` | 是 | 上傳時選填的工作負載／預算 JSON；供 Advice agent（FR5.4）；空／無效視為 null，不得擋上傳 |
| `estimate_line_items` | `spec_description` | `TEXT` | 是 | 目錄價 API 查出的**規格文字描述**；原始 `spec` 必須保留；**不得**寫入 hourly／單價（FR13／AH-6） |

既有環境升級：啟動時 `_ensure_estimate_intake_schema()` 以 `ADD COLUMN IF NOT EXISTS` 補欄；新環境可由 `schema_rbac.sql` 一次建立。

---

## 1. ERD

```mermaid
erDiagram
    users ||--o{ estimate_sets : owns
    estimate_sets ||--o{ estimates : contains
    estimates ||--o{ estimate_line_items : has
    estimate_sets ||--o{ estimate_shares : shared_as
    users ||--o{ estimate_shares : shared_with
    estimate_sets ||--o{ estimate_audit_events : audited
    estimate_sets ||--o| advice : has

    estimate_sets {
        int id PK
        int owner_user_id FK
        timestamptz created_at
        int diagram_id "nullable label only"
        text note
        text workload_context_json "nullable FR1.7"
        boolean is_saved
    }

    estimates {
        int id PK
        int estimate_set_id FK
        string cloud
        numeric stated_total
        string currency
        int parsed_line_count
        int unparsed_line_count
        string source_format
    }

    estimate_line_items {
        int id PK
        int estimate_id FK
        int ordinal
        text item_name
        text spec
        text spec_description "nullable FR13"
        numeric quantity
        numeric amount
        string currency
        string parse_status
        text raw_text
    }

    estimate_shares {
        int estimate_set_id PK_FK
        int user_id PK_FK
        timestamptz shared_at
    }

    estimate_audit_events {
        int id PK
        int actor_user_id FK
        int estimate_set_id FK
        string event_type
        timestamptz occurred_at
        string cloud
        int parsed_line_count
        int unparsed_line_count
    }

    advice {
        int estimate_set_id PK_FK
        string status
        text saving_text
        text comparison_text
        text quality_text
        text unavailable_reasons_json
        timestamptz started_at
        timestamptz completed_at
    }
```

文字 fallback：`users` 擁有多個 `estimate_sets`；每個 Set 含多筆 `estimates`（每雲至多一筆），每筆 Estimate 含多筆 `estimate_line_items`；分享、稽核、Advice 皆掛在 Set 上。

---

## 2. 資料表說明

### 2.1 `estimate_sets`

上傳批次根。`diagram_id` 為純標籤（不 FK、不參與授權）。`is_saved=false` 為分析草稿，命名儲存後才進歷史。

- **`workload_context_json`**：選填；序列化後的工作負載／預算上下文（系統說明、資訊需求、費用限制、流量與負載指標等）。寫入路徑見 `cost/workload_context.py`；讀取路徑見 Advice orchestrator。

### 2.2 `estimates`

同 Set 內 `cloud` UNIQUE（`aws`／`azure`／`gcp`）。

### 2.3 `estimate_line_items`

解析明細。機械檢查結果**不落庫**（每次 GET 重算）。

- **`spec`**：檔案內原始規格（含 SKU 代碼）。
- **`spec_description`**：僅當規格「看起來像目錄 SKU」時由 `cost/sku_catalog.py` 補齊；查不到／失敗則空；UI 優先顯示此欄。

### 2.4 `estimate_shares`

複合 PK `(estimate_set_id, user_id)`。授權只看擁有者＋此名單。

### 2.5 `estimate_audit_events`

事件層稽核；不得寫入金額、列原文、檔案內容。

### 2.6 `advice`

與 Set 一對一（PK＝`estimate_set_id`）。空殼由 U2 建立；正文屬 U7。

---

## 3. 對照實作

| 來源 | 路徑 |
|---|---|
| 靜態 DDL | `schema_rbac.sql`（C1 Estimate intake 區塊） |
| ORM | `backend/models.py`（`EstimateSet`、`Estimate`、`EstimateLineItem`、…） |
| 啟動補欄 | `backend/database.py` → `_ensure_estimate_intake_schema()` |
| 部署說明 | `DEPLOY.md` §2.2.5 |
| FD 實體 | `construction/estimate-intake-api/functional-design/entities.md` |
| 故事 | `inception/user-stories/stories.md`（C1-W1、C1-S1） |

## 4. 驗證建議

```bash
psql "$DATABASE_URL" -c "\d estimate_sets"
psql "$DATABASE_URL" -c "\d estimate_line_items"
# 預期欄位含 workload_context_json、spec_description
```
