# Business Overview — Cloud-360

> **基準**：commit `dc4b687`（2026-09-22）、branch `danniel/docs/orchestration-brain-ideation`。
> 本輪為 **Full rescan（廣度）＋ partial（深度）**。深度分佈見
> `reverse-engineering-timestamp.md` 的 `## Scope of Analysis`：33 個路徑實讀、
> 其餘僅取簽章或計數。**不要把本檔的任何一節讀成「整個 repo 都被讀過」。**
>
> **證據標記**（全 codekb 適用）：`[讀]` 實際開檔逐行讀過｜`[簽]` 僅取函式／路由簽章
> ｜`[算]` 由本輪實際執行的指令計算（指令或方法附於該處）｜`[未驗]` 本輪未執行、
> 未複驗的靜態觀察。**本輪未以任何測試、lint 或 CI validator 的執行結果作為本 codekb 的事實來源**（唯一的例外是寫檔後跑過一次 `validate_repo_contract.py` 做落檔安全檢查，那不是對程式碼品質的判斷），
> 故本 codekb 不出現任何「通過／全綠」類宣稱。

---

## 系統定位

Cloud-360 是一個 **AI-native 多雲架構與維運平台**，以對話驅動的方式協助團隊
產出、評核、共編與估價雲端架構。目前對外的產品面由三條能力線構成：

| 能力線 | 故事代號 | 現況 |
|---|---|---|
| 對話產出架構圖（drawio） | A1 | 已上線，SSE 串流 `[讀]` `agent_router.py:129` |
| Well-Architected 評核與改善建議 | A3 | 已上線，SSE 串流 `[讀]` `review_router.py:173` |
| 架構圖共編與聊天持久化 | A4 | 已上線，WebSocket `[讀]` `collab_router.py:266` |
| 成本／估價（上傳官方估價表 → 檢查 → LLM 建議） | C1 | 已上線，10 個 HTTP operation `[讀]` |
| 帳號授權、角色權限治理、帳號活動稽核 | J3a／J3b／J5 | 已上線 `[算]` `openapi.json` 解析 |

專案方法論基礎為 Spec-Driven Development；AI-DLC v2 的工作區（`aidlc/`）與
框架殼（`.claude/`）同住此 repo，但**不是應用程式碼**，本輪未掃描。

## 服務對象與角色

`services/rbac.py:23–35` 的 `CANONICAL_ROLES` 是角色清單的正本，共 **11 個角色** `[讀]`；
權限矩陣為 **11 角色 × 28 個 story id = 308 列** `[算]`（import `services.rbac_seed_data`
實算 `DEFAULT_ROLE_PERMISSIONS` 長度）。

每個 `(角色, story)` 格有 `view` / `edit` / `review` 三個旗標。以 C1 為例 `[算]`：
具 `edit` 者為 `Project_Architect`、`Project_Editor`、`Project_Admin`、
`FinOps_Analyst`、`Platform_Admin`；`Developer`、`Platform_Engineer`、
`Security_Reviewer` 三者 C1 三旗標全 false，Sidebar 與 `/cost` 路由對他們隱藏或 403。

> **既有教訓（仍有效）**：RBAC 種子可以**早於**產品面存在。看到某個 story id 出現在
> 權限矩陣，不代表對應的 router、頁面或資料表存在。C1 曾長期處於此狀態；本輪 C1
> 的 router 與資料表都已存在（見下），但這條讀法原則對未來的 story id 仍然成立。

## 核心業務流程主線

### 主線一：取得帳號與授權
註冊 → `authorization_status` 待審 → 管理者於授權審核頁核可 → 取得角色。
`require_story_action` 在**任何** story 授權檢查之前先擋 `authorization_status != "approved"`
並直接 403 `[讀]` `rbac.py:262–267`。

### 主線二：對話產圖（A1）
使用者在 Workspace 輸入需求 → `prompt_guard` 前置檢查（平台自我竄改預檢）→
`design_agent` 以子行程驅動 `claude` CLI → `diagram_builder` 產出 drawio XML →
SSE 逐步回送。`[讀]` `agent_router.py`、`[簽]` `design_agent.py`／`diagram_builder.py`。

### 主線三：架構評核（A3）
以 WA Lens 規則引擎（`wa_rule_engine`／`wa_lens_engine`）加 LLM 評核，
結果寫入 `architecture_reviews`，可匯出 PDF／PNG。`[簽]`

### 主線四：估價與成本建議（C1）
上傳三雲官方估價表（AWS CSV／Azure XLSX／GCP CSV）→ 解析器轉為
`estimate_sets` / `estimates` / `estimate_line_items` → 檢查面板 →
LangGraph agent 產生節費建議，寫入 `advice` 表 → 前端以 SSE 取進度。`[讀]`

> **業務規則（本輪實讀確認）**：估價數字一律來自**使用者上傳的官方估價表**，
> 不由系統自動取價產生。計價 Port（`pricing_client`）只用於 agent 產生建議時
> 確認現價，結果寫入建議文字。此規則有兩支 CI validator 承載
> （`scripts/validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`）`[簽]`。

### 主線五：權限治理與帳號稽核（J3a／J3b／J5）
管理者頁面可改角色、停用帳號、逐格調整權限矩陣、檢視帳號最後活動時間。
`users.last_activity_at` 由 `activity.record_activity` 以 5 分鐘節流寫入 `[讀]` `activity.py:25`。

## 業務邊界與非目標

- ❌ 雲端供應商 production 環境、production credentials、直接對雲 IaC apply、
  破壞性雲端操作、原生行動 App（ADR-0001／ADR-0002）。
- ❌ 帳單與用量類計價 API（Cost Explorer、CUR、Cost Management、Billing Export）
  全面禁止；目錄價類端點已於 ADR-0018 解禁。
- ⚠️ **退役但仍在 schema 內的能力**：`archive_diagram_cost`、`archive_diagram_cost_line`、
  `archive_pricing_cache`、`archive_cost_audit_event` 四張表是 C1 舊實作的遺骸。
  `schema_rbac.sql:166–167` 的區塊標題逐字為
  `C1 Cost / FinOps tables — RETIRED (U3 legacy-cost-retirement)`、
  `應用零讀寫；保留 ≥90 天後另開 chore DROP` `[讀]`；
  `database.py:330–383` 的 `_ensure_cost_schema()` 在啟動時把 live 表 RENAME 成 `archive_*` `[讀]`。
  **grep 到 `*_cost*` 表名不等於成本能力存在於該處**——現行成本資料在
  `estimate_sets` 等六張表（`schema_rbac.sql:216–296`）。

## 與作用中 intent（`260920-orchestration-brain`）的關係

本 intent 要建一個統一入口的「大腦」，編排既有的子功能 agent。與本檔的交集：

1. 既有能力中**只有 C1 具備完整的 HTTP 可編排面**（10 個 operation，授權全掛在
   FastAPI dependency 上）。A1／A3 的對外面是 SSE，A4 是 WebSocket。
2. intent 要建的 `專案 → 系統 → 架構圖` 階層在目前的業務模型中**不存在**——
   現行唯一擁有關係是 `users → user_diagrams` 加 `diagram_shares` 多對多 `[讀]` `models.py:25–30,91–105`。
3. intent 的「成本關注者」角色在 RBAC 已有落點（`FinOps_Analyst`），且 C1 能力已實作。

## 詞彙表

| 詞 | 意義 |
|---|---|
| story id | RBAC 權限矩陣的欄位鍵（A1／A3／A4／C1／J3a…共 28 個） |
| Lens | Well-Architected 評核用的規則集，存於 `wa_lenses` 表與 `backend/lenses/` |
| estimate set | 一次估價工作的根物件，底下掛 estimates → line items |
| advice | C1 的 LLM 節費建議，一列對應一個 estimate set |
| archive_* | C1 舊實作退役後改名保留的表，應用不得讀寫 |
| slot registry | 前端成本頁的插槽註冊表（`frontend/src/cost/slotRegistry.tsx`） |
