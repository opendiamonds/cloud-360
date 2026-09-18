# A3 Well-Architected Review — Requirements

> AIDLC Inception → Requirements Analysis（A3 增量）  
> Branch: `luojingting/feat/a3-well-architected-review`  
> Answers: `inception/plans/a3-requirements-questions.md`（2026-07-23）  
> Baseline story: `user-stories/stories.md` §A3；現況 FE 有「Well-Architected」按鈕（`showComingSoon`）


### 1. Intent Analysis

| 項目 | 判定 |
|---|---|
| User request | 開始實作 A3（自動化 Well-Architected 評核） |
| Request type | New Feature（brownfield 增量） |
| Clarity | 經 Q1–Q8 澄清後可執行 |
| Scope | Multiple Components（backend 評核服務＋DB＋Workspace／儀表板 FE＋RBAC） |
| Complexity | Complex（規則＋LLM 混合、持久化、雙入口 UI） |
| Depth | Standard → Comprehensive（新能力＋安全／可測） |

### 2. Decisions（來自問答）

| # | 決策 |
|---|---|
| Q1 | **MVP**：單一架構圖評核 → 分數＋發現清單；**PDF 已於 2026-07-26 增量納入 FR-A3-11**；本期不做 SPOF／AZ 模擬動畫 |
| Q2 | **AWS 為主**；UI／API **預留** GCP／Azure 開關；本期只實作 AWS Well-Architected 語意 |
| Q3 | **混合入口**（見下） |
| Q4 | **混合引擎**：規則先掃硬性問題 → LLM 補建議文案；**LLM 層必須與 A1 同一 Agent 框架**（Anthropic Agent SDK + OpenRouter，見 `construction/a1/code/agent-sdk-summary.md`） |
| Q5 | **完整持久化**：新表（如 `architecture_reviews`），可查歷史／重開 |
| Q6 | **雙入口**：工作區快捷 ＋ 獨立評估儀表板（歷史） |
| Q7 | 沿用 `role_permissions` **A3** view／edit／review（缺則補 seed） |
| Q8 | **先補齊 Inception**（SRS／stories／U-A3）再進 Construction FD→Code |

#### Q3 入口（解讀並納入需求）

1. **A1 產圖後引導**：產圖成功後的引導／Toast 流程中，提供「進行 Well-Architected 評估」；點擊後對**當前圖**發起評核。  
2. **工作區既有按鈕**：`WorkspacePage` 現有「Well-Architected」按鈕由 Coming Soon **改為**對目前選中圖發起評核（或開結果／歷史）。  
3. **圖表選擇（對齊 B）**：評估儀表板（或同等 UI）可從**有權限的圖表列表**挑選任一張再執行。  
4. 本期**不**支援未入庫的任意上傳／貼上 XML 作為唯一路徑。

### 3. Functional Requirements

| ID | 需求 |
|---|---|
| FR-A3-01 | 具 A3.edit（或等價）者可對有權開啟的 diagram 發起評核 |
| FR-A3-02 | 輸入為選定 `user_diagrams.xml_data`（AWS 產圖語意為主） |
| FR-A3-03 | 規則引擎解析圖中節點／連線，產出可重現的硬性發現（例：缺備援、單點等可編碼規則） |
| FR-A3-04 | LLM／Agent 依規則結果＋XML 摘要產出改善建議文案（不取代規則判定的權威性） |
| FR-A3-04a | **Agent 框架對齊 A1（硬約束）**：建議生成路徑必須使用與 A1 相同之 **Anthropic Agent SDK（`claude-agent-sdk`）+ OpenRouter** 執行／環境映射（`design_agent` 模式或共用 agent runtime）；**禁止**另起平行 LLM SDK／直連客戶端作為主路徑。可新增 A3 專用 MCP tool／system prompt，但 runtime 與 A1 共用。 |
| FR-A3-05 | 畫面顯示總分／分支柱分數（至少 AWS WA 支柱維度，可先子集）＋發現清單 |
| FR-A3-06 | 結果寫入 DB；可列表歷史、開啟單次評核詳情 |
| FR-A3-07 | 工作區入口：產圖後 CTA ＋ Well-Architected 按鈕 |
| FR-A3-08 | 獨立評估儀表板：選圖、執行、瀏覽歷史 |
| FR-A3-09 | API／UI 帶 `provider` 或同等欄位預設 `aws`；gcp／azure 顯示但本期回「未實作」或 disabled |
| FR-A3-10 | 無權限 → 403；pending 使用者（J5）不可評核 |
| FR-A3-11 | 具 **A3.view** 且可讀該評核者，可對 `complete`／`rules_only` 報告**下載 PDF**（前端產生；含總分、RiskCounts、支柱分、發現、改善建議與 meta） |

### 4. Out of Scope（本期 MVP）

- ~~可下載 PDF 報告~~ → **已納入 FR-A3-11**（2026-07-26 增量）  
- SPOF／AZ 中斷模擬動畫與 RPO／RTO 估算 UI（故事全文 AC 延後）  
- GCP／Azure 規則實作  
- 未存檔 XML 上傳評核為主路徑  

### 5. Non-Functional Requirements

| ID | 類別 | 需求 |
|---|---|---|
| NFR-A3-01 | Security | 僅授權使用者；JWT；A3 RBAC；不把完整 XML／建議寫入公開 log |
| NFR-A3-02 | Testability | 規則引擎結果 deterministic，適合 unit／property-based 測試 |
| NFR-A3-03 | Reliability | 規則失敗與 LLM 失敗可分離：規則結果仍可存；LLM 失敗有明確錯誤態 |
| NFR-A3-04 | Performance | 單次評核目標：規則階段秒級；LLM 可非同步／進度提示（實作細節於 FD） |
| NFR-A3-05 | Bilingual docs | 所有 A3 aidlc-docs 雙語 |

### 6. Proposed Inception follow-through（Q8=A）

1. 修訂 `stories.md` A3 AC（標註 MVP vs 下期）  
2. 必要時對齊 `cloud-360-srs.md` 最佳實踐段落  
3. Units Generation：新增 `U-A3` 至 `unit-of-work*.md`  
4. Workflow Planning → Application Design（若需）→ Construction FD  

### 7. Extension Compliance（本階段）

| Extension | Status | Note |
|---|---|---|
| bilingual-docs | compliant | 本文件雙語 |
| security/baseline | applicable | NFR-A3-01；FD／Code 強制 |
| property-based | applicable | NFR-A3-02；規則輸出性質 |
| resiliency | N/A | 未啟用 |
