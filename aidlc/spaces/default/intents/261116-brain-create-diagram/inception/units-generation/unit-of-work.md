# Units of Work — 讓大腦直接建立新的架構圖（修訂 1）

> 來源：`units-generation-questions.md` Q1=A（三個單元）與切分計畫核可；元件與決策見 `inception/domain-design/components.md`（修訂 1）、`decisions.md`；需求見 `inception/requirements-analysis/requirements.md`（修訂 2）。
> **修訂 1（2026-11-17）**：依 `reviews/review-01.md` 修正——列圖參數與其現行呼叫端都歸 U1；FR7.1 標為跨單元；AccessControl 歸 U2；補上舊前端遇到新反問種類的行為分析；移除暗示跨單元順序的字句。
>
> **部署模型**：三個單元都屬同一個單體（一個 backend、一個 frontend），合併進 `ut` 即一起部署到 staging；不是獨立服務。
> **目錄命名**：construction 目錄以裸單元名命名（依 `project.md` 的學習紀錄：引擎以 `construction/<name>/` 組路徑，既有目錄皆無 `u{n}-` 前綴），故下表 `Directory` 欄即單元名。

| Unit ID | Name | Directory | Kind | Complexity | Deployment |
|---|---|---|---|---|---|
| U1 | diagram-drafts | `diagram-drafts` | service | M | 共用（單體 backend） |
| U2 | brain-create-flow | `brain-create-flow` | service | L | 共用（單體 backend） |
| U3 | draft-ui | `draft-ui` | ui | M | 共用（單體 frontend） |

## U1 — diagram-drafts（架構圖的草稿狀態）

- **描述**：讓架構圖有「草稿／正式」兩種狀態，並讓每個用到架構圖的地方依用途排除或包含草稿。
- **涵蓋元件**：DiagramStore、HierarchyService、UserAccounts、AssessmentConsumers（各自的本 intent 改動部分）。
- **負責與交付**：
  - `user_diagrams` 新增狀態欄位；`hierarchy_migration._ensure_hierarchy_schema()` 為既有資料庫補欄位、預設正式；`schema_rbac.sql` 與 `DEPLOY.md` 同步（blocking，ADR-003）。
  - 建圖可指定建立為草稿；存檔區分「手動存檔，轉為正式」與「只寫內容」（FR6.2）。
  - 「我的架構圖」清單（`GET /api/collab/diagrams`）回傳狀態；分享不得分享草稿。
  - `list_diagrams_of_system` 加必填的含不含草稿參數，**並一併修改現行唯一呼叫端** `backend/services/work_orchestrator.py:967` 改為明示包含草稿（ADR-005）。參數與呼叫端在同一單元內完成，U1 單獨合入也不會讓既有呼叫失效。
  - 刪除系統、清除預設專案、刪除使用者三處直接查詢計入草稿（FR6.4b）。
  - 評核、WA 共編、估價綁圖拒絕草稿並回覆「這張圖還是草稿，請先完成產圖」（FR6.4a）。
  - 「經大腦建立」的變更紀錄（FR7.1）。
- **實作注意**：架構圖 API 回應改變須重新產生 `openapi.json` 與前端型別（OpenAPI 漂移檢查）；新增或修改的端點依 `team.md` B 規則補 TestClient 測試；資料表變更若動到 `backend/database.py` 的啟動補丁須同步 `LOCAL-DEV.md`。

## U2 — brain-create-flow（大腦新建架構圖的流程）

- **描述**：使用者說要畫圖時，大腦判定新建或修改、預檢權限、在交辦前建草稿並切換作業對象，或以可點選的反問補齊不足的資訊。
- **涵蓋元件**：BrainGateway、IntentRouter、BrainDiagramCreation（新）、WorkOrchestrator、AccessControl（本 intent 不改它的規則，只在 U2 新增閘道對 `user_can_arch` 的呼叫，故歸 U2）。
- **負責與交付**：
  - 意圖路由在同一次 Decisions 請求多問「是否要新的一張」（FR2.2）。
  - 大腦建圖元件：純函式模組（新建或修改的判定、取名）以 property-based 測試鎖住；I/O 模組以使用者 token 建草稿、記錄變更（ADR-001）。
  - 閘道：`user_can_arch(edit)` 預檢（ADR-009）、交辦前建草稿並切換作業對象（ADR-008）、新反問種類、點選時核對候選集合並重新驗證（ADR-002）。
  - 工作編排：產圖成功時轉為正式。（`list_diagrams_of_system` 呼叫端的明示已在 U1 完成。）
  - 大腦建圖元件建草稿後，呼叫 U1 提供的變更紀錄寫入「經大腦建立」（FR7.1 的寫入端在 U2，紀錄能力在 U1）。
- **實作注意**：新反問種類改變 WebSocket 契約，須同步 `dump_ws_contract` 與前端型別（契約漂移檢查）；把作業對象切到「一張圖」需擴充既有的 `_set_target_confirmed` 或沿用使用者手動切換的路徑（領域設計審查 review-02 的遺留項，由 contract-design 定案）；新呼叫建圖需在 `CapabilityClient` 補建圖呼叫；路由屬 ADR-0006 PBT hard constraint。

## U3 — draft-ui（前端的草稿呈現與存檔區分）

- **描述**：讓使用者在畫面上看得出哪些是草稿，並讓手動存檔與自動存檔有不同結果；呈現新的可點選反問。
- **涵蓋元件**：DiagramListsUI。
- **負責與交付**：
  - 專案頁「系統的架構圖」、工作區歷史清單、切換對象選單標示「草稿」（FR6.4）。
  - 專案頁「架構圖」計數（`OverviewTab.tsx` 的 `attachedCount`）不計草稿（FR6.4a）。
  - 工作區「儲存架構圖」按鈕轉為正式；自動存檔與評核前寫回只寫內容（FR6.2）。
  - 呈現新的反問種類（選系統、選圖、接著畫哪張草稿或新建、新建或修改），點選即送出（FR3.4）。
- **實作注意**：依 `team.md` C 規則，資料形狀改變須有 Playwright 斷言（草稿標示、計數排除）；前端 lint 結構約束（資料抓取拆兩層、不可就地修改物件）照舊。

## Assumptions & Open Questions

- **舊前端遇到新反問種類**：U2 新增的反問種類若先於 U3 上線，舊前端會收到不認得的 `kind`。前端依產生的型別解析 WebSocket 訊息，不認得的種類可能被忽略或顯示錯誤，使用者看不到候選而卡住。這正是下一條「同一批合入」的理由；contract-design 須另定舊前端遇到未知種類時的退路（例如以文字列出候選）。〔推導〕
- 三個單元同屬一次部署：U1 改變架構圖 API 的回應、U2 改變 WebSocket 契約，而 U3 是它們的消費端。依 `project.md` 的學習紀錄，破壞性契約變更與其消費端不得分批上線；本 intent 沒有 delivery-planning 站，故在 code-generation 合併時三者應同一批合入 `ut`。〔推導〕
- 契約形狀（新反問種類、清單回傳狀態、存檔轉正式的區分、建圖可指定草稿）由下一站 contract-design 定案。
