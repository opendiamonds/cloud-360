# A3 Lens Editor — Requirements（增量）

> AIDLC Inception → Requirements Analysis（A3 增量：動態編輯 Offline Custom Lens）  
> 問答：`inception/plans/a3-lens-editor-questions.md` + `a3-lens-editor-clarification-questions.md`（2026-07-26）  
> 基線：`a3-well-architected-requirements.md`；執行期 Lens：`backend/lenses/cloud360-core-mvp-lens.json`


### 1. Intent Analysis

| 項目 | 判定 |
|---|---|
| User request | `Security_Reviewer` 可在 A3 動態編輯五大柱審核標準 |
| Request type | Enhancement（A3／U-A3 增量） |
| Clarity | 經 Q1–Q7 + Clarification Q1–Q3 後可執行 |
| Scope | Multiple Components（DB + API + Assessment UI + `load_lens` + 測） |
| Complexity | Moderate–Complex（可編輯 JSON、模板、RBAC、部署同步） |
| Depth | Comprehensive（完整增量 Inception → Construction） |

### 2. Decisions（鎖定）

| # | 決策 |
|---|---|
| Q2 | **DB 為準**：新表存 active Lens JSON；評核／讀取優先 DB，無列則 fallback 檔案 |
| Q3 | **具 A3.review（審核）者** 可寫入（Admin 矩陣可調；預設 seed：`Security_Reviewer`＝VER） |
| Q4 | **只影響之後新評核**；歷史 `architecture_reviews` 已存 scores／findings **不變**（本期不存 lens 快照／版本 UI） |
| Q5 | UI 在 **Assessment 儀表板** 內「Lens 標準」分頁／區塊（僅 Fiona 可見可編） |
| CQ1 | **可增刪**五大柱下題目；既有題改文案；新增題套用**系統結構模板**（choices／`riskRules`／improvementPlan）；**本期 UI 不開放手改 riskRules 條件式** |
| CQ2 | 「預設建議」＝依題目標題產生／可編輯的 **improvementPlan.displayText**（非 LLM 必選；可為規則模板字串） |
| CQ3 | 刪除：**每柱至少 1 題**；刪前確認；刪後只影響新評核 |
| Q7 | 完整增量 Inception 後再 Construction |

**覆寫原 Q1=A**：以 Clarification Q1=A 為準（可增刪＋模板；非純文案鎖定）。

### 3. Functional Requirements

| ID | 需求 |
|---|---|
| FR-A3-L01 | 系統維護**一份** active Offline Custom Lens（語意相容現有 `schemaVersion`／pillars／questions／choices／riskRules） |
| FR-A3-L02 | 首次使用：若 DB 無 active 列，以 `cloud360-core-mvp-lens.json` **seed／fallback**；儲存後之後讀寫皆走 DB |
| FR-A3-L03 | 具 **A3.review** 者可讀取完整可編輯檢視（五大柱＋題目＋choices 文案＋improvementPlan） |
| FR-A3-L04 | 可編輯既有題：`title`、`description`、choice `title`、`improvementPlan.displayText`；**不可**經 UI 改既有 `id` 或 `riskRules` |
| FR-A3-L05 | 可在既有五柱（禁止增刪支柱／禁止 Sustainability）下**新增題目**：系統產生穩定 `id`＋預設 choices／`riskRules`；使用者填標題等文案 |
| FR-A3-L06 | 新增／編輯時可取得 **improvementPlan 預設建議**（依標題模板）；可接受或改寫 |
| FR-A3-L07 | 可刪題：確認後刪除；**每柱剩餘 ≥ 1**；否則 400 |
| FR-A3-L08 | 儲存為整份 Lens 替換（或等價原子更新）；寫入後新評核使用新標準 |
| FR-A3-L09 | 無 **A3.review**：GET 編輯 API／UI 隱藏或 403；評核讀取仍用 active Lens |
| FR-A3-L10 | Assessment 頁提供「Lens 標準」入口（僅有 A3.review 時） |
| FR-A3-L11 | 依 `aidlc/spaces/default/memory/project.md` 的 `## Mandated`：DDL 同步 `schema_rbac.sql` + `DEPLOY.md`（中英） |

### 4. Out of Scope（本期）

- UI 手改 `riskRules` condition／風險等級矩陣進階編輯器  
- Lens 版本歷史、評核列綁定 lens 快照顯示  
- 一鍵重跑舊評核套用新標準  
- 匯出／匯入 JSON 檔（Q2 未選 C）  
- 覆寫 repo 內 JSON 檔作為唯一持久化  
- 增減支柱、加入 Sustainability  
- `Platform_Admin` 等其他角色編輯（除非 Admin 矩陣勾選 A3 審核）  

### 5. Non-Functional Requirements

| ID | 類別 | 需求 |
|---|---|---|
| NFR-A3-L01 | Security | 寫入僅 **A3.review** + approved；審計可用既有 user 操作 log（若有）或至少 API 層拒絕 |
| NFR-A3-L02 | Integrity | 儲存前驗證 JSON 結構（五柱 id 集合、每柱 ≥1 題、riskRules 可被引擎解析） |
| NFR-A3-L03 | Compatibility | `wa_lens_engine.load_lens`／評核管線改為「DB 優先」且行為與檔案 lens 相容 |
| NFR-A3-L04 | Testability | unit：驗證、模板、權限、fallback；property：可選「任意合法編輯後仍可 score」 |
| NFR-A3-L05 | Bilingual docs | 本增量 aidlc-docs 雙語 |

### 6. Extension Compliance（本階段）

| Extension | Status | Note |
|---|---|---|
| bilingual-docs | compliant | 本文件雙語 |
| security/baseline | applicable | NFR-A3-L01；Code 強制角色閘 |
| property-based | applicable | NFR-A3-L04；Code／Build 評估 |
| resiliency | N/A | 未啟用 |
