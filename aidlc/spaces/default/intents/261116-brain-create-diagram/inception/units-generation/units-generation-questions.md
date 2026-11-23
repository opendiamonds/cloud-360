# Units Generation — 問題檔

> 上游已定案、不重問：`inception/domain-design/components.md`（修訂 1，已核可）的 10 個元件與 `decisions.md` 的 ADR-001～ADR-009；需求 `requirements.md`（修訂 2）。
> 由 repo 事實定案、不重問：**部署模型**為單一部署——本 repo 是一個 backend（FastAPI）加一個 frontend（React）的單體，合併進 `ut` 即一起部署到 staging（`org.md` `## Deployment`、ADR-0007）；各單元都是同一次部署的一部分，不是獨立服務。
> **單元目錄命名**：依 `project.md` 的學習紀錄，construction 目錄以裸單元名命名（引擎與既有目錄皆無 `u{n}-` 前綴），本站沿用。

## Q1. 工作單元要切多細？

背景：本功能跨三層——(1) 架構圖資料（草稿狀態、存檔轉正式、清單回傳狀態、各使用端排除或包含草稿：DiagramStore、HierarchyService、UserAccounts、AssessmentConsumers）；(2) 大腦流程（閘道預檢與交辦前建草稿、新反問種類、路由多問一題、大腦建圖元件、工作編排轉正式：BrainGateway、IntentRouter、BrainDiagramCreation、WorkOrchestrator、AccessControl 呼叫端）；(3) 前端（草稿標示、計數排除、手動存檔、新反問呈現：DiagramListsUI）。

- A. 三個單元：架構圖資料、大腦流程、前端；大腦流程與前端都依賴架構圖資料，前端另依賴大腦流程定義的新反問種類
- B. 一個單元：整個功能一起做、一起測
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:12:08Z 使用者以選單選定 -->

## 切分計畫核可

計畫：`diagram-drafts`（service，M）、`brain-create-flow`（service，L，依賴 `diagram-drafts`）、`draft-ui`（ui，M，依賴 `diagram-drafts` 與 `brain-create-flow`）。

[Answer]: Approve Plan <!-- 2026-11-17 使用者以選單選定 -->
