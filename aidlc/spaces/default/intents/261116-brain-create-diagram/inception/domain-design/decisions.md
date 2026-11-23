# Architecture Decisions — 讓大腦直接建立新的架構圖（domain-design）

> 來源：`domain-design-questions.md` 作答 Q1～Q6；需求 `inception/requirements-analysis/requirements.md`（修訂 2）。ADR-006、ADR-007、ADR-009 為分析者依需求與既有程式推導，可在核可關卡推翻。
>
> **修訂 1（2026-11-17）**：依 `reviews/review-01.md` 修正——ADR-004 由 ADR-008 取代（Q6=A）；新增 ADR-009（權限預檢）；ADR-005、ADR-007 對齊實際程式的呼叫端。

## ADR-001: 新增 BrainDiagramCreation 元件承載判定、取名與建草稿

- **Context**：新功能有三組會一起變動的規則：新建或修改的判定（FR2，屬 agent routing 的 PBT hard constraint）、新圖取名（FR5）、建草稿且一個工作項至多一張（FR1.4）。它們可以分散放在意圖路由與工作編排，也可以集中成一個元件。
- **Decision**：新增 `BrainDiagramCreation`（Q5=B）。依 `team.md` 的三層形狀：判定與取名是不讀 DB、不連外、不拋 `HTTPException` 的純函式，以 property-based 測試鎖住；建圖與查詢經 DiagramStore、HierarchyService 執行。意圖路由只提供機率 p，不判定新建或修改。
- **Consequences**：判定規則有單一落點，PBT 直接對它；工作編排與閘道只呼叫它，不重複規則。代價是多一個模組與兩條呼叫邊（閘道與工作編排都依賴它）。
- **Alternatives Rejected**：判定放在意圖路由、建圖放在工作編排、不新增元件（Q5 選項 A）——改動面較小，但規則分散兩處，取名與冪等沒有明確擁有者。

## ADR-002: 可點選反問新增線上種類，候選帶系統或圖的識別碼

- **Context**：FR3.4 要求反問候選可直接點選；大腦已有 `kind="target"` 的前例，線上只送不透明 id，對照存在伺服器（`backend/services/brain_gateway.py:1468-1487`）。
- **Decision**：新增線上的反問種類與欄位，候選帶系統或圖的識別碼，前端依種類呈現（Q1=B）。伺服器在點選時**一律重新驗證**識別碼指向的系統或圖仍存在、使用者仍擁有，不依客戶端值直接執行（FR3.5）。線上形狀由 contract-design 定案。
- **Consequences**：前端可依種類呈現不同的反問（選系統、選圖、選草稿或新建、新建或修改）；要改 WebSocket 契約、前端型別與 `dump_ws_contract` 漂移檢查，且識別碼暴露在線上，重新驗證是必要的授權防線（ADR-0006 IAM）。
- **Alternatives Rejected**：沿用既有 `kind="target"`、只擴充伺服器端的對象參照（Q1 選項 A）——不改契約形狀，但前端無法依反問種類呈現。

## ADR-003: 草稿狀態放在 user_diagrams 的欄位

- **Context**：FR6 要求圖有草稿與正式兩種狀態，既有圖一律為正式，舊版程式讀到新欄位不受影響。
- **Decision**：`user_diagrams` 新增狀態欄位，由 DiagramStore 擁有（Q2=A）。既有非空資料庫經 `hierarchy_migration._ensure_hierarchy_schema()` 補欄位、預設正式；`schema_rbac.sql` 與 `DEPLOY.md` 同步更新（blocking）。
- **Consequences**：狀態與圖同列，查詢簡單；需要一次資料表變更與遷移。
- **Alternatives Rejected**：另開一張表記錄草稿（Q2 選項 B）——不動既有表，但每個要判斷草稿的查詢都得 join，容易漏。

## ADR-004: 工作項記錄它建立的圖（**已由 ADR-008 取代**）

> 取代原因：架構審查 `review-01` 指出 (1) 工作編排無法設定作業對象，建圖後切到新圖沒人做；(2) 圖建在 PostgreSQL、圖 id 寫在 Redis，兩者之間當機會重複建圖——與本 ADR 拒絕選項 B 的理由相同。使用者以 Q6=A 改由閘道在交辦前建草稿。以下為原紀錄，保留以供追溯。

- **Context**：FR1.4 要求一個工作項至多建立一張圖，重試、復原掃描與「再說一次接著畫」都不得再建。
- **Decision**：Redis session 的工作項加一個「已建立的圖」欄位，建圖成功即寫入，後續步驟與復原掃描讀它沿用（Q3=A）。
- **Consequences**：冪等依賴工作項的保存；工作項過期後，接著畫改依 FR6.3 以作業對象（已切到草稿）判斷，不依賴工作項。
- **Alternatives Rejected**：資料庫另記「工作項 ↔ 圖」對照（Q3 選項 B）——更持久，但工作項本身在 Redis，跨兩個儲存容易不一致。

## ADR-005: 列圖方法以必填參數明示是否包含草稿

- **Context**：同一個「列出系統下的圖」要同時供「排除草稿」與「包含草稿」兩種用途（FR6.4a、FR6.4b）。
- **Decision**：`list_diagrams_of_system` 加一個必填、沒有預設值的參數（例如 `include_drafts`），每個呼叫端必須寫明（Q4=A）。
- **Consequences**：漏寫會在呼叫時直接報錯，而不是默默用錯。現行唯一呼叫端是工作編排（`backend/services/work_orchestrator.py:967`），新呼叫端是閘道候選與大腦建圖的重名判斷，三者都包含草稿。刪除系統檢查（`hierarchy_service.py:212`）、清除預設專案與刪除使用者（`user_router.py:438`、`:651`）是直接查詢、不經這個方法，另行保證包含草稿；專案頁計數由前端計算（`OverviewTab.tsx`），在前端排除草稿（見 ADR-007）。
- **Alternatives Rejected**：拆成兩個名字不同的函式（Q4 選項 B）——一樣明確，但兩份實作容易漂移。

## ADR-006: 待決反問的原始請求存在連線上

- **Context**：可點選反問後要「依該候選繼續原本的請求」（FR3.4），原始請求必須保存到使用者點選為止（requirements OQ6）。
- **Decision**：沿用既有的連線內 `PendingClarify`，把原始請求與候選一起存放；斷線或換一輪對話即失效，使用者重說一次即可。〔推導：沿用既有機制，未另問使用者〕
- **Consequences**：不新增儲存；全站一條連線（前一個 intent 的全站小助手），換頁不斷線，失效情境只剩真正斷線。
- **Alternatives Rejected**：存進 Redis session——可跨斷線保留，但待決反問本來就短命，增加清除與一致性負擔不划算。

## ADR-007: 草稿依用途分為「排除」與「包含」兩類

- **Context**：Q11=A 要求其他地方一律排除草稿，但刪除系統檢查與清除預設專案若排除草稿會出錯（需求審查 review-02）。
- **Decision**：拿圖來用或對外呈現的地方排除草稿——專案頁計數（前端 `OverviewTab.tsx`，資料來自 `GET /api/collab/diagrams` 回傳的狀態）、評核、WA 共編、估價綁圖、分享；判斷「底下有沒有圖」的地方包含草稿——刪除系統（HierarchyService）、清除預設專案與刪除使用者（UserAccounts）、反問候選、重名判斷。〔推導：依需求 FR6.4a、FR6.4b〕
- **Consequences**：規則依用途而非一律排除，每個使用端都有明確歸類，可逐一以測試驗證。
- **Alternatives Rejected**：一律排除——會讓刪除系統撞上資料庫限制、清除掉仍有草稿的預設專案。

## ADR-008: 閘道在交辦前建立草稿並切換作業對象（取代 ADR-004）

- **Context**：只有閘道能設定作業對象（`backend/services/brain_gateway.py:1592` 的 `_set_target_confirmed`，其中呼叫 `store.set_work_target` 並扇出）；工作編排沒有這個能力，也沒有回呼閘道的路徑。若由工作編排建圖，FR1.3「建圖成功即切到新圖」沒人做，且跨 PostgreSQL／Redis 的冪等有原子性缺口（架構審查 review-01）。
- **Decision**：閘道判定要新建、且通過權限預檢後，先請 BrainDiagramCreation 以使用者 token 建草稿，成功即以 `_set_target_confirmed` 把作業對象切到它，再照既有流程交辦；工作編排不建圖（Q6=A）。
- **Consequences**：建草稿發生在工作項存在之前，工作編排的重試與復原掃描只會處理同一張圖，一個工作項不可能建出第二張（FR1.4 的目的由結構保證，不需在工作項記圖 id）。代價：建草稿與切換之間若斷線或當機，系統下會留一張草稿；下次說要畫圖時 FR6.3a 會反問「接著畫或新建」，不會默默多一張，故不另設清除。首字回應前多一次同行程的建圖呼叫，build-and-test 須量測仍符合 NFR3。
- **Alternatives Rejected**：維持工作編排建圖，建圖端點接受工作項 id 作為冪等鍵（新欄位＋唯一約束），並新增通知閘道切換作業對象的路徑（Q6 選項 B）——可在資料庫層保證冪等，但多一個欄位、一個約束與一條新的跨元件回呼路徑。

## ADR-009: 新建前的權限預檢由閘道呼叫 user_can_arch

- **Context**：FR4.1 要求沒有架構編輯權的人說要畫圖時，不新建並明確說明；建圖端點的檢查（`require_arch_action("edit")`，`backend/services/rbac.py:198`）只在最後一步回 403，閘道與工作編排原本沒有權限檢查（架構審查 review-01）。
- **Decision**：閘道判定要新建時，先呼叫 `user_can_arch(db, role, "edit", authorization_status)`——與端點檢查同一個函式；不通過就回覆需要架構編輯權並請向平台管理者申請，不建草稿、不交辦。〔推導：沿用閘道既有以 `user_can` 檢查 K1 的作法，`brain_gateway.py:802`〕
- **Consequences**：權限判斷只有一個來源，預檢與端點不會分歧；端點的檢查仍保留，作為最終防線。
- **Alternatives Rejected**：只靠端點回 403 再轉成說明——使用者要等到建圖那一步才被擋，且 403 的原文不是給使用者看的說明。

## ADR-0006 Security Baseline 四面向（本站）

| 面向 | 判定 | 說明 |
|---|---|---|
| IAM | 適用 | 閘道以 `user_can_arch(edit)` 預檢、建圖端點仍以 `require_arch_action("edit")` 把關，建圖以使用者 token 執行（ADR-008、ADR-009）；可點選候選先確認是本次提供的候選、再重新驗證存在與擁有權（ADR-002）；候選只列使用者擁有的系統與自己的圖 |
| Encryption | 不適用 | 不新增儲存或傳輸機密的路徑；狀態欄位與候選識別碼不是敏感資料 |
| Network exposure | 適用 | 不新增對外端點；擴充既有 `/api/brain/ws` 的反問種類與既有架構圖 API，須通過契約漂移檢查 |
| Audit logging | 適用 | 經大腦建立記入 `diagram_change_records`；日誌不得含使用者原文與圖名 |
