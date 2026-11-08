# Domain Design — 釐清問題

> Stage: domain-design（Inception，inline）· Depth: Standard · Scope: feature  
> Intent: `261105-d-iac-generation`（Story D）  
> 元件＝**要寫的邏輯構件**；DB／CLI／OpenRouter 為 `external_dependencies`。部署拓樸不在本站（units-generation）。  
> **成本揭露**：本題組共 6 題。答完並確認摘要後產出 `components.md`、`decisions.md`、`traceability.json`。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 領域套件 `backend/iac/`；檔名領域語彙；禁 `d1_*` 前綴；權限仍 `require_story_action("D1"\|"D2"\|"D3")` | [tp] Q5=B |
| 三 agent 走 `langgraph_runtime`＋OpenRouter；不收斂 `design_agent` | [tp] Q6=A |
| Generator／scanner／redactor 皆 PBT 核心；決定性核心先於 LLM | [tp] Q5／Q6 |
| 獨立 `/api/iac/...`；不塞 `agent_router`／`user_router` | [stories]／[tp] |
| 執行 D3 需 D1∧D2 成功報告；自由檢視步驟；切圖清空 | [stories] US4.1／US1.3 |
| UI：Workspace 內固定三欄殼；不代 apply | [rm] Q1–Q6=A |
| 不新增 CI IaC scan job | [tp] Q3=A |

## Sources

- [req] `../requirements-analysis/requirements.md`
- [stories] `../user-stories/stories.md`
- [rm] `../refined-mockups/mockups.md`
- [tp] `../practices-discovery/team-practices.md`
- [kb] `aidlc/spaces/default/codekb/cloud/architecture.md`、`component-inventory.md`（`iac-d-pillar-surface`、`langgraph-runtime`、`cost-domain`）

---

## Q1. 後端邏輯構件怎麼切？

> practices 已定 `backend/iac/` 與三核心＋三 agent，但「幾個 Domain 元件」未釘。這影響 units-generation 與 traceability 顆粒度。實體擁有權也跟切法走。

A. **四個後端元件**：`IacWorkspaceSession`（工作階段／產物鍵／執行閘／HTTP 編排）、`IacModuleGenerator`（決定性 generator＋D1 agent）、`IacStaticScanner`（報告形狀＋D2 agent）、`IacSecretRedactor`（改寫＋D3 agent）。Session 呼叫後三者；核心互不直接呼叫。**（建議）** 對齊 D1／D2／D3 邊界與 R-01 閘集中一處。
B. **三個後端元件**：Generate／Scan／Secret 各自含自己的 HTTP 薄層＋核心＋agent；無獨立 Session——閘與產物鍵散落三處。代價：D2→D3 前置易重複實作。
C. **兩個後端元件**：`IacOrchestrator`（含三 agent 編排＋閘）＋`IacDeterministicCore`（generator／scanner／redactor 同元件三模組）。代價：核心邊界在目錄清楚、在元件目錄糊。
D. Not yet defined
X. Other (please specify)

[Answer]:A

---

## Q2. 工作階段產物（草稿／報告／改寫）誰擁有、存哪裡？

> US1.3／US4.1 要求 `(session|user, diagram_id)` 鍵、切圖作廢、舊 `report_id`→4xx。需釘實體擁有元件與持久化深度（本站只定擁有權＋形狀名，完整 schema 留給 functional-design）。

A. **`IacWorkspaceSession` 擁有** `IacDraft`、`IacScanReport`、`IacRewriteResult`（或等價三實體）；**本輪預設行程內／可重建快取**（進程記憶體或短 TTL），不要求新 Postgres 表。重新整理可丟失，但同 session 內切圖／閘必須正確。**（建議）** 對齊 MVP「可演示」與較少 schema 同步。
B. **同上三實體，但必須落 Postgres**（新表），跨重新整理可恢復同圖草稿。代價：`schema_rbac.sql`／`DEPLOY.md` 同步義務立刻啟動。
C. **不建模實體**：只當暫時 DTO；閘只靠前端帶 revision。代價：API 易被舊 `report_id` 繞過，違反 US1.3／US4.1。
D. Not yet defined
X. Other (please specify)

[Answer]:A

---

## Q3. 前端邏輯構件怎麼切？

> refined-mockups 已定殼與 test-id。Domain 元件是「要寫的前端邏輯邊界」，不是每個 React 檔都算一個元件。

A. **一個前端元件 `IacWorkspaceUi`**：擁有步驟狀態機、選圖脈絡、呼叫 `/api/iac/*`、下載 modal／空錯誤態；視覺子塊（檔案樹、findings）為其內部模組，不另列 Domain 元件。**（建議）** 對齊「單工作區」與 Cost 頁「一頁一域」粒度。
B. **三個前端元件**（GeneratePanel／ScanPanel／SecretsPanel）＋薄 `IacShell`。代價：步驟閘與切圖清空需跨元件協定。
C. **併入現有 `WorkspacePage` 元件擴充**：不新增 Domain 前端元件。代價：Workspace 職責膨脹，與 A／C 分離成本頁的先例不一致。
D. Not yet defined
X. Other (please specify)

[Answer]:A

---

## Q4. 架構圖可讀／上傳與既有 collab 怎麼接？

> D 需要活躍圖、改選、上傳 `.drawio`／`.xml`，但圖 CRUD 已在 collab／Workspace。Domain 應避免再造圖庫，也避免偷呼叫 `collab_router` 私有函式（cost 域教訓）。

A. **`IacWorkspaceSession`（或 UI）只依賴既有公開圖 API／服務**（list／get／upload 走現有 Workspace／collab 契約）；IaC 域**不**擁有 `Diagram` 實體，只存 `diagram_id` 參照。缺公開介面時本 intent 只加**最小公開讀取／上傳包裝**（仍屬既有圖域），不把授權私函從 collab 挖進 iac。**（建議）**
B. **IaC 域自建輕量圖上傳表**，與 Workspace 圖資產分叉。代價：雙圖庫、切圖語意混亂。
C. **直接 import `collab_router` 私有 `_user_can_access_diagram` 等**。代價：重蹈 cost FR7.3 債。
D. Not yet defined
X. Other (please specify)

[Answer]:A

---

## Q5. D1／D2／D3 執行的 API 互動風格？

> 生成／掃描可能數十秒；Workspace／Cost 已有 SSE 先例。需定 Domain 互動風格（非部署拓樸）。

A. **同步 HTTP JSON 為主**（`POST` 執行→等結果）；進度靠短輪詢或回應前的 aside 樂觀「進行中」（前端自管）。LLM 可 stub；逾時用閘道／伺服器上限。代價：長請求佔連線，但實作面最小。**（建議，若預期 &lt; 閘道逾時）**
B. **執行用 SSE**（對齊 review／cost-advice）：進度事件＋最終結果事件。代價：多一條 stream 契約與測試面。
C. **執行建 job＋輪詢**（需 `IacJob` 實體）。代價：本輪實體與表變多。
D. Not yet defined
X. Other (please specify)

[Answer]:A

---

## Q6. LangGraph agent 算不算獨立 Domain 元件？

> 三 agent 檔在 `backend/iac/`，底座是既有 `langgraph-runtime`（inventory 已有）。要避免把基礎設施當元件，也要能追溯「誰擁有編排行為」。

A. **不算獨立元件**：D1／D2／D3 agent 編排行為分別掛在 `IacModuleGenerator`／`IacStaticScanner`／`IacSecretRedactor` 的 `behaviour` 內；`langgraph_runtime`／OpenRouter 列為各核心的 `external_dependencies`。**（建議）** 與 inventory「runtime 不擁有業務 graph」一致。
B. **三個獨立 Agent 元件**外加三核心。代價：元件數膨脹，depends_on 圖變吵。
C. **一個 `IacAgentHost` 元件**擁有三 graph，核心只被它呼叫。代價：與「決定性核心可離線、agent 可 stub」的測試敘事較繞。
D. Not yet defined
X. Other (please specify)

[Answer]: A（附條件；見 Q6b 釐清）

---

## Q6b. 釐清：你要的「agent 可互通／可調架構」在 A 方案下是否足夠？

> 你選 A 但附帶：「前提是 AI agent 可以互相溝通，或未來架構調整可以快速因應；不行就選 B。」  
> **澄清（非新決策）**：Domain 元件切分 ≠ 執行期能否串場。  
> - **A**：三個 agent **不是**獨立 Domain 元件，但編排仍可由 `IacWorkspaceSession` 依序呼叫 Generator→Scanner→Redactor（含各 agent）；日後若要加「掃描結果回寫生成」仍可在 Session 加一步，或把某 agent 升成獨立元件而不改外部 API。  
> - **B**：三個 Agent **另列** Domain 元件——主要多的是目錄／依賴圖節點，**不自動**多出一種「agent 對 agent 通訊匯流排」。  
> 若你要的是「同一工作階段可 D1→D2→D3 串接＋之後好拆」，A 已滿足；若你要「catalogue 上三個 Agent 節點可見、方便單獨替換」，選 B。

A. **維持 A** — Session 串接＋核心內含 agent 行為即足夠；不另列 Agent 元件。**（建議，對齊你 Q1=A）**
B. **改為 B** — 三核心外再列三個獨立 Agent Domain 元件（目錄上可單獨替換）。
C. **維持 A，但加一條 Mandated** — Session 必須保留「可插入跨步回呼／補償」的編排點（仍不把 Agent 列成元件）。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

1. **Q1=A** — 四後端元件：`IacWorkspaceSession`＋`IacModuleGenerator`／`IacStaticScanner`／`IacSecretRedactor`；Session 呼叫後三者，核心互不直連。
2. **Q2=A** — Session 擁有 `IacDraft`／`IacScanReport`／`IacRewriteResult`；本輪行程內／可重建快取，不強制新 Postgres 表。
3. **Q3=A** — 單一前端 Domain 元件 `IacWorkspaceUi`（子塊為內部模組）。
4. **Q4=A** — 圖資產走既有公開 API；IaC 只存 `diagram_id`；不挖 collab 私函。
5. **Q5=A** — 執行以同步 HTTP JSON 為主；進行中由前端 aside 樂觀顯示。
6. **Q6=A＋Q6b=A** — Agent 不另列 Domain 元件；編排行為掛在三核心；互通／串場由 Session 負責。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
