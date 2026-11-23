# Domain Design — 問題檔

> 上游已定案、不重問：`inception/requirements-analysis/requirements.md`（修訂 2，已核可）的 FR1～FR7、NFR1～NFR5 與其作答。本站回答它指派給 domain-design 的 OQ3、OQ4、OQ6、OQ8，並定元件邊界。

## 出題前查證（唯讀；檔:行為 2026-11-17 `origin/ut`）

- **可點選的反問已有前例**：大腦已有「選對象」的反問（`kind="target"`）。線上只送不透明的候選 id（`target-1`…）與文字，伺服器把 id 對應到哪個對象存在連線上的 `PendingClarify.targets`（`backend/services/brain_gateway.py:1468-1487`）；使用者點選後，伺服器以 `_set_target_confirmed` 重新確認並設定作業對象，再把原本的請求交辦出去（`:1680-1683`）。線上 `ClarifyPayload.kind` 只允許 `intent`、`target`（`backend/services/brain_ws_contract.py:229`）。
- 伺服器端的對象參照 `TargetRef` 目前只有專案與系統（`project_id`、`system_id`、名稱），沒有圖（`backend/services/brain_gateway_rules.py:363-369`）。
- 待決的反問 `PendingClarify` 只存在連線物件上（行程內），斷線即清除（`backend/services/brain_gateway.py:231`、`:874-876`）。
- 工作項存在 Redis session（`backend/services/session_store.py` 的 `update_work_item`，`:543`），欄位含 `workItemId`、`status`、`capability`、`sideEffect` 等（`backend/services/work_orchestrator.py:181-187`）。
- 「列出系統下的圖」：`hierarchy_facade.list_diagrams_of_system`（`:604`）→ `hierarchy_service.list_diagrams_of_system`（`:288`），回傳呼叫者擁有的 `(diagram_id, title)`，供工作編排把「只選到系統」換成目標圖。
- 架構圖資料表 `user_diagrams` 沒有狀態欄位（`backend/models.py:98-110`）；既有非空 volume 的演進路徑是 `hierarchy_migration._ensure_hierarchy_schema()`（`schema_rbac.sql:346-347`）。

## Q1. （FR3.4／OQ6）可點選的反問（選系統、選圖、選草稿或新建、新建或修改）怎麼做？

- A. 沿用既有的 `kind="target"` 機制：線上仍只送不透明 id 與文字，伺服器端把 `TargetRef` 擴充為能指向圖、並能代表「新建」；待決的原始請求仍存在連線上的 `PendingClarify`（斷線即失效，使用者重說一次即可）。**不改 WebSocket 契約的形狀**
- B. 新增線上的反問種類與欄位（例如候選帶 `systemId`／`diagramId`），前端依種類呈現；要改 WebSocket 契約、前端型別與漂移檢查
- C. Not yet defined
- X. Other（請說明）

[Answer]: B <!-- 2026-11-17T05:46:35Z 使用者以選單選定 -->

## Q2. （OQ3）草稿狀態放在哪裡？

- A. `user_diagrams` 加一個狀態欄位（草稿／正式），由架構圖實體擁有；既有資料庫以 `_ensure_hierarchy_schema()` 補欄位、預設正式
- B. 另開一張表記錄哪些圖是草稿
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T05:46:35Z 使用者以選單選定 -->

## Q3. （OQ4）工作項怎麼記住「它建立的圖」，以免重試或復原時再建一張？

- A. Redis session 的工作項加一個欄位記錄已建立的圖 id；建圖成功即寫入，後續步驟與復原掃描讀它
- B. 資料庫另記「工作項 ↔ 圖」對照
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T05:46:35Z 使用者以選單選定 -->

> 修訂 1 註記：Q3=A 已由 Q6=A 取代（閘道在交辦前建草稿，工作編排不建圖，故不需在工作項記圖 id）。原作答保留以供追溯。

## Q4. （OQ8）「列出系統下的圖」怎麼讓呼叫端明示要不要包含草稿？

- A. 加一個**必填、沒有預設值**的參數（例如 `include_drafts`），每個呼叫端都必須寫明
- B. 拆成兩個名字不同的函式（只列正式／全部列出）
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T05:46:35Z 使用者以選單選定 -->

## Q5. 「判斷新建或修改」與「建圖」的邏輯放在哪個元件？

- A. 判定規則是意圖路由裡的純函式（不讀 DB、不連外，PBT 鎖住）；建圖是工作編排在既有「讀圖 → 產圖 → 存圖」前面多一步，經 `CapabilityClient` 以使用者 token 呼叫建圖端點；不新增元件
- B. 新增一個獨立的「大腦建圖」元件，負責判定與建圖，工作編排呼叫它
- C. Not yet defined
- X. Other（請說明）

[Answer]: B <!-- 2026-11-17T05:49:59Z 使用者以選單選定 -->

## 修訂 1 追問（2026-11-17，核可關卡「要求修改」：處理 `reviews/review-01.md`）

## Q6. （review-01 Major：作業對象切換與冪等）誰建立草稿？

背景：原設計讓工作編排建圖、把圖 id 記在 Redis 的工作項（Q3=A）。審查指出兩個問題：(1) 只有閘道能設定作業對象（`backend/services/brain_gateway.py:1592` `_set_target_confirmed`），工作編排沒有這個能力，建圖後「切到新圖」（FR1.3）沒人做；(2) 圖建在 PostgreSQL、圖 id 寫在 Redis，兩者之間當機，重試會再建一張——正是 ADR-004 拒絕選項 B 的理由。

- A. **改由閘道在交辦前建草稿**：閘道判定要新建後，先經「大腦建圖」元件以使用者 token 建草稿，再以既有的 `_set_target_confirmed` 把作業對象切到它，然後照既有流程交辦（對象已是一張圖，走既有的讀圖 → 產圖 → 存圖）。工作編排不建圖，也就不需要在工作項記圖 id（**取代 Q3=A**）。若建草稿後、切換前當機，系統下會留一張草稿，下次說要畫圖時依 FR6.3a 反問「接著畫還是新建」，不會默默多一張
- B. 維持工作編排建圖，改以資料庫保證冪等：建圖端點接受工作項 id 作為冪等鍵並記在圖上（新增欄位與唯一約束），重試時取回同一張；並新增一條讓工作編排通知閘道切換作業對象的路徑。改動較多
- C. Not yet defined
- X. Other（請說明）

[Answer]: A <!-- 2026-11-17T06:03:19Z 使用者以選單選定；取代 Q3=A -->
