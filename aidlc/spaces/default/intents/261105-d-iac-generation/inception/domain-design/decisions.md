# Architecture Decisions — Story D Domain Design

<!-- Stage: domain-design · 本 intent 內 ADR 序號自 ADR-001 起（非 repo 根 ADR-000x）。 -->

## ADR-001: 四後端＋一前端元件切分

- **Context**：D1／D2／D3 有獨立 PBT 核心與失敗模式；執行閘與切圖清空是跨步狀態機；UI 已定單工作區殼。
- **Decision**：後端 `IacWorkspaceSession`＋`IacModuleGenerator`／`IacStaticScanner`／`IacSecretRedactor`；前端單一 `IacWorkspaceUi`。Session 呼叫三核心；核心互不直連。
- **Consequences**：閘與產物鍵集中，易測 R-01／切圖；元件數適中。HTTP 薄層屬 Session 邊界，units-generation 再分 deploy 單位。
- **Alternatives Rejected**：三後端無 Session（閘重複）；Orchestrator＋大 Core（目錄糊）；前端三 Panel（跨步協定重）；併入 WorkspacePage（職責膨脹）。

## ADR-002: 工作階段產物本輪不落新 Postgres 表

- **Context**：US1.3／US4.1 需可靠作廢舊 report；MVP 要可演示；schema／DEPLOY 同步成本高。
- **Decision**：`IacDraft`／`IacScanReport`／`IacRewriteResult` 由 Session 擁有，**行程內／可重建快取**；重新整理可丟失，同 session 內閘必須正確。
- **Consequences**：本輪免新表；多 tab／重載體驗弱。若產品後要求恢復草稿，再升持久化並走 schema 同步。
- **Alternatives Rejected**：立刻 Postgres（過早）；純前端 DTO 閘（可被舊 report_id 繞過）。

## ADR-003: 執行 API 採同步 HTTP JSON

- **Context**：生成／掃描可能數十秒；repo 已有 SSE，但 D 柱需最小契約與 TestClient 面。
- **Decision**：`POST` 執行等結果；UI aside 樂觀「進行中」；逾時依閘道／伺服器上限；LLM 可 stub。
- **Consequences**：實作與測試面小；長請求佔連線。若實測常超閘道，再評估 SSE（另開 ADR）。
- **Alternatives Rejected**：SSE（契約／測試較重）；Job＋輪詢（多實體）。

## ADR-004: LangGraph agent 不另列 Domain 元件

- **Context**：三 agent 必須可 stub、核心可離線 PBT；使用者關切「能否互通／以後好拆」。
- **Decision**：Agent 編排行為分別掛在三核心 `behaviour`；互通／串場由 `IacWorkspaceSession` 編排；`langgraph_runtime`／OpenRouter 為 external_dependencies（Q6b=A）。
- **Consequences**：catalogue 精簡、測試敘事清楚；agent 替換邊界在模組檔而非 Domain 節點。日後可再升獨立元件。
- **Alternatives Rejected**：三獨立 Agent 元件（膨脹且不自動多通訊匯流排）；單一 IacAgentHost（與離線核心敘事繞）。

## ADR-005: 架構圖不進入 IaC 擁有權

- **Context**：圖 CRUD 已在 Workspace／collab；cost 域曾挖私函成債。
- **Decision**：IaC 只存 `diagram_id`；讀寫走既有**公開**圖 API；缺則在圖域加最小公開包裝，不 import collab 私有授權函。
- **Consequences**：無雙圖庫；IaC 依賴圖域契約穩定性。
- **Alternatives Rejected**：IaC 自建上傳表；直接 import collab `_user_can_access_*`。
