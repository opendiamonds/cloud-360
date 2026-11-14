# 業務規則 — `U7 hierarchy-service`

> 本檔的 ```yaml 區塊是**規則的單一真實來源**。`functional-spec.md` 的規則摘要為
> **衍生檢視**。`traceability.json` 的每個 `OK` 目標都必須指名此處存在的 `BRx.y`。

## 規則定義（單一真實來源）

```yaml
rules:
  # ---- BR1.x 授權（本站承接的上游未決事項之一）----
  - id: BR1.1
    statement: >
      專案與系統的讀、建立、修改、刪除，一律經 `require_story_action(K2)` 的判定，
      而該判定的**唯一呼叫點**在 `HierarchyFacade`。
    category: authorization
    applies_to: Project、System 的全部受保護操作
    trigger: 每一次受保護操作被請求時（HTTP 路由或同進程呼叫皆然）
    logic: >
      IF 請求者不具 `K2` 權限 THEN 拒絕，且拒絕**經由既有的
      `require_story_action` 判定**產生，不自建第二套判定。
      `HierarchyFacade` 是受保護操作的唯一授權入口；FastAPI router 與同進程
      呼叫端**共用這一個入口**，故判定只有一份呼叫點。
    violation_behaviour: >
      raise `HierarchyForbidden(story_id='K2', action=<action>)`——**不是**
      `HTTPException`（契約 K-07 `on_denied` 逐字）。router 層把它轉成 403 ＋
      detail 前綴；同進程呼叫端自行處置。
      **此處與 repo 既有慣例相反，故必須明寫**：`team.md` 的既有錯誤處理形狀逐字是
      「DB／驗證錯誤直接 `raise HTTPException`」，預設沿用它就會違反本契約。
      另兩種例外同樣由 K-07 `public_interface` 的 `raises` 指定：
      驗證失敗為 `HierarchyValidationError`、查不到為 `HierarchyNotFound`。
      `AC9.2.3` 逐字要求「拒絕經由既有的 `require_story_action` 路徑」，
      故自建拒絕邏輯即違反該 AC，不只是風格問題。
    source: >
      AC9.2.3、**契約 K-07 `hierarchy-authorized-facade` 的 `sole_entry` 與 `rule`
      （逐字）**、components.md ProjectHierarchy.behaviour、
      unit-of-work.md:247（ADR-0006 IAM 列）

  - id: BR1.2
    statement: >
      受保護操作一律經 `HierarchyFacade`；**不得繞過它直呼底層服務層函式**。
    category: authorization
    applies_to: >
      ProjectHierarchy 的全部入邊——**四個同進程呼叫端**（`U10 session-store`、
      `U12 work-orchestrator`、`U19 membership-service`、`U20 requirement-field-service`）
      ＋ router（HTTP 消費端 `U16 object-picker-ui`、`U23 project-pages-ui`）
    trigger: 任何呼叫端要執行受保護操作時
    logic: >
      IF 呼叫端是同進程元件（`SessionContext`／`WorkOrchestrator`／
      `ProjectMembership`／`RequirementRegistry`）
      THEN 它呼叫 `HierarchyFacade` 的方法，並把已驗證的 `principal` 作為
      **第一個參數**傳入（facade 不自行從 request 取身分）；
      受保護資源的識別為**具名參數**，不得藏在 payload 內。
      ELSE（繞過 facade 直呼底層 service）授權判定不會執行。
    violation_behaviour: >
      **靜默的完整授權繞過。** 判定掛在 facade 上；繞過它直呼底層 service
      完全不觸發判定，且不會有任何錯誤——這就是它危險的地方。
    source: >
      **契約 K-07 的 `consumers.in_process`、`sole_entry`、`identity_passing`、
      `resource_context`（逐字）。** 本條是本站承接的上游未決事項的解決：
      `components.md` 的 `behaviour` 逐字禁止繞過，而同一份檔的機讀區塊宣告
      `SessionContext` 與 `WorkOrchestrator` 兩條 `sync` 入邊——兩句話直接對撞，
      `unit-of-work.md:222` 將其記為 Accepted risk 並**指派 `functional-design`**。
      **指派的內容是把 K-07 已選定的 facade 模型的「唯一入口」性質變成可強制的**
      （K-07 自己的 `residual_gap` 逐字說它「無機械強制」），
      不是替 `sync` 邊另選一種通訊機制——後者會把已核可的契約整個換掉。

  - id: BR1.3
    statement: >
      授權判定只有**一份**（在 facade），底層服務層不設第二道角色檢查。
    category: policy
    applies_to: 本單元 facade 之下的服務層函式
    trigger: 設計邊界的宣告
    logic: >
      服務層假設呼叫者已通過 facade 的判定。該假設的成立條件**完全依賴
      `BR1.2` 與 `BR1.4`**。
    violation_behaviour: >
      不適用——本條是**誠實宣告**而非禁令。寫下它的理由：若不寫，下游會以為
      服務層自己也會擋，而它不會。`BR1.2` 一旦被違反，本條就是傷害的放大器。
    source: >
      契約 K-07 的 `rule`（判定只有一份呼叫點）。這是契約的選擇，不是本站的——
      本站只負責讓它可被強制（`BR1.4`）。

  - id: BR1.4
    statement: >
      `principal` **只能由授權入口鑄造**；呼叫端無法自行構造一個。
    category: constraint
    applies_to: HierarchyFacade 的 principal 參數
    trigger: 任何呼叫端準備呼叫 facade 方法時
    logic: >
      IF 呼叫端能自行構造 `principal` THEN `BR1.2` 退化成純約定——繞過者只需
      自己造一個就能通過。
      THEREFORE `principal` 的構造必須收斂到**驗證身分的那一處**，
      使「沒有通過驗證就拿不到 `principal`」成為型別層的事實，而非 code review
      的責任。
    violation_behaviour: >
      `BR1.2` 由可強制的約束退化為慣例。**這正是 K-07 自己具名的 `residual_gap`**：
      「『facade 是唯一入口』無機械強制——繞過它直呼底層 service 只能靠 code
      review 擋下。本站如實記載此缺口，不宣稱已解決。」
    source: >
      使用者裁決（2026-10-06）：遵循 K-07 並以不可偽造的 principal 關閉該缺口。
      **本條是 `unit-of-work.md:222` 指派給本站的事項的實際落地點。**
      注意其射程：它讓「拿不到 principal 就呼叫不了 facade」成立，但**不會**
      阻止某人完全不碰 facade 而直呼底層 service——那一半仍需 `BR1.5` 的檢查。

  - id: BR1.5
    statement: >
      「沒有其他單元 import 底層服務層」須由一道可執行的檢查守住，而非 code review。
    category: policy
    applies_to: >
      `U10`、`U12`、`U19`、`U20`，以及任何未來的同進程呼叫端
    trigger: 下游單元的 code-generation
    logic: >
      掃描**四個**同進程呼叫端的原始碼，斷言它們 import 的是 facade 而非底層
      service 模組。**四個不是兩個**——`components.md` 實測有四條 `component:
      ProjectHierarchy` 的 `depends_on` 入邊（`:110` SessionContext、`:156`
      WorkOrchestrator、`:559` ProjectMembership、`:618` RequirementRegistry），
      而 K-07 的「既有四條的消費端擴充」表（`contract-summary.md:1551`，其前言
      逐字「原列不回改，擴充列於此」）為 K-07 新增 `U19`／`U20`／`U23`。
      **`U19 ProjectMembership` 讀的正是 `ownerUserId`**——per-project 授權所依賴
      的那個欄位——故漏掉它的後果最重。
    violation_behaviour: >
      繞過重新打開，且是靜默的。
    source: >
      K-07 的 `residual_gap` 的另一半。**本條的執行落點不在本單元**——它約束的是
      **四個**同進程呼叫端 `U10`／`U12`／`U19`／`U20`
      （`components.md:110-112`／`:156-158`／`:559-561`／`:618-620`，四條 `style: sync`
      入邊；消費端清單見 `contract-summary.md:1551` 的 K-07 擴充表），
      故本單元只能定義它並在 traceability 記為具名缺口（`OPEN-H2`）。
      本單元自己無法驗證它。
      **本條同時是 `OQ-N2` 的答覆**：`bolt-plan.md:108` 逐字把 `OQ-N2` 記為
      「授權門面唯一性的強制手段（加 lint 檢查，或接受只由 review 擋）」、涵蓋
      `U7`／`U8` 兩個單元，而 `:155` 把它列為 **B1 的進入條件**。
      本站的答覆是**加機制**（可執行的 import 掃查）而非「接受只由 review 擋」；
      執行落點在上述四個消費端的 code-generation。**`U8` 那一半不屬本單元**
      ——那是記憶服務的門面，本站不代它定案。
      （審查 iteration 2 的 `R-01`／`R-16`：原文只寫兩個呼叫端，與同一條規則的
      `applies_to` 自相矛盾，且全檔對 `OQ-N2` 零命中。）

  # ---- BR2.x 建立路徑 ----
  - id: BR2.1
    statement: >
      建立專案與建立系統各**恰有一個** HTTP 端點；兩個使用者入口都呼叫它。
    category: constraint
    applies_to: 建立路徑
    trigger: 設計時與實作時
    logic: >
      IF 要新增一個建立入口（例如對話式建立的確認卡）
      THEN 它必須呼叫既有的那一個端點，不得新增第二個寫入端點。
    violation_behaviour: >
      授權檢查、稽核紀錄與錯誤訊息會各有兩份，而 `components.md` 逐字要求
      「各只有一份」。兩份必有一份悄悄漂移。
    source: >
      `[F4]`=A、components.md behaviour 與 responsibilities、unit-of-work.md:109。
      選 A 的理由：寫入路徑的唯一性因此**可機械驗證**（端點數 = 1），
      而非靠紀律維持——選項 B 的代價正是「仍可能漂移，需另加測試斷言訊息相同」。

  - id: BR2.2
    statement: 建立系統時，目標專案必須存在。
    category: validation
    applies_to: System 的建立端點
    trigger: 建立系統的請求
    logic: IF 指定的專案不存在 THEN 拒絕並說明該專案不存在。
    violation_behaviour: 建立失敗；不得建出孤兒系統。
      **例外型別**：raise `HierarchyNotFound`（目標專案不存在）——**不是** `HTTPException`。
      router 層才轉成對應的 HTTP 狀態碼；同進程呼叫端自行處置
      （契約 K-07 的 `on_denied` 逐字「**不是** `HTTPException`」，
      本條沿用同一形狀。審查 iteration 2 的 `R-09`）。
    source: entities.md System.projectId（必填參照）、AC9.2.2

  - id: BR2.3
    statement: 新建的專案與系統，其預設標記一律為否。
    category: constraint
    applies_to: Project、System 的建立端點
    trigger: 建立請求
    logic: >
      IF 經由建立端點建立 THEN 預設標記為否。
      預設組**只**由遷移程序產生（`U4` 擁有），端點不得製造第二個預設組。
    violation_behaviour: >
      會出現多個預設專案／系統，而 `U4` 已交付的實體對預設標記有部分唯一索引
      ——違反會被參照完整性擋下，但錯誤訊息不會說明原因。
    source: entities.md isDefault、schema_rbac.sql 檔頭第 11 行（兩個部分唯一索引）

  - id: BR2.4
    statement: >
      建立類操作**非冪等**；呼叫端不得自動重試。
    category: constraint
    applies_to: 建立專案、建立系統
    trigger: 呼叫端遇到逾時或不確定結果時
    logic: >
      IF 重複呼叫建立 THEN 會建立第二個同名物件（`BR3.2` 的檢查在併發下
      也擋不住——見 `BR3.3`）。
      THEREFORE 呼叫端不得把建立類操作放進自動重試邏輯。
      相對地，解析作業對象為唯讀且冪等，可安全重試。
    violation_behaviour: >
      使用者會得到兩個同名專案或系統，而沒有任何錯誤訊息。
    source: >
      **契約 K-07 的 `retry_and_idempotency` 逐字**（「create_project／create_system
      **非冪等**……呼叫端不得自動重試建立類操作」「resolve_work_target 為唯讀且
      冪等，可安全重試」「record_diagram_change **非冪等**（一次異動一列），不得重試」）。

  # ---- BR3.x 名稱 ----
  - id: BR3.1
    statement: 專案與系統的名稱去除前後空白後長度必須大於 0。
    category: validation
    applies_to: Project.name、System.name
    trigger: 建立與改名
    logic: IF 去空白後為空字串 THEN 拒絕。
    violation_behaviour: >
      建立或改名失敗。此約束在 `U4` 已交付的實體層亦存在，故即使服務層漏檢
      也會被擋下——但錯誤訊息會是資料庫層的，對使用者無意義。
      **例外型別**：raise `HierarchyValidationError`（名稱為空白）——**不是** `HTTPException`。
      router 層才轉成對應的 HTTP 狀態碼；同進程呼叫端自行處置
      （契約 K-07 的 `on_denied` 逐字「**不是** `HTTPException`」，
      本條沿用同一形狀。審查 iteration 2 的 `R-09`）。
    source: 實讀 U4 交付物的 name 非空白約束

  - id: BR3.2
    statement: >
      名稱衝突時回「衝突」並說明，不以資料庫唯一約束承載。
    category: validation
    applies_to: Project.name（同一擁有者內）、System.name（同一專案內）
    trigger: 建立與改名
    logic: >
      IF 同範圍內已有同名 THEN 拒絕並回「衝突」。
    violation_behaviour: 建立或改名失敗，訊息指名衝突的名稱。
    source: >
      `[F5]`=C。選 C 而非 B 的理由已在問題檔逐字揭露：B 是 **schema 變更**，
      會觸發 `project.md` 的 blocking 同步規則並回頭改一個**已登記完成**的單元
      （`U4`）的 schema。

  - id: BR3.3
    statement: >
      `BR3.2` 的唯一性是**最佳努力**，不是不變量——併發下仍可能建出同名。
    category: policy
    applies_to: BR3.2
    trigger: 兩個併發的建立請求使用同一個名稱
    logic: >
      檢查與寫入之間存在空窗（TOCTOU）。資料層沒有唯一約束可以收尾，
      故兩者都會成功。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：`BR3.2` 讀起來像一個不變量，
      而它不是。若不寫，下游會以為「名稱不會重複」並據此設計（例如以名稱當鍵）。
      **名稱永遠不是鍵，識別碼才是。**
    source: "`[F5]`=C 的已知代價，問題檔選項 C 逐字記載「屬已知的 TOCTOU」"

  # ---- BR4.x 刪除與預設組 ----
  - id: BR4.1
    statement: 預設專案與預設系統**可以**改名。
    category: policy
    applies_to: isDefault 為真的 Project、System
    trigger: 改名請求
    logic: >
      IF 目標的預設標記為真 THEN 改名照常允許。
    violation_behaviour: 不適用（本條為允許規則）。
    source: >
      `[F6]`=A。理由：歸屬的權威來源是系統的識別碼，不是名稱
      （entities.md System → Diagram 關係），故改名不影響任何不變量。

  - id: BR4.2
    statement: 預設專案與預設系統**不得**刪除。
    category: constraint
    applies_to: isDefault 為真的 Project、System
    trigger: 刪除請求
    logic: IF 目標的預設標記為真 THEN 拒絕刪除。
    violation_behaviour: >
      刪除預設系統會讓其底下架構圖的歸屬懸空，而「遷移後歸屬為空的架構圖列數
      必須為 0」是**已核可的不變量**且 `U4` 已有測試保護它。
      **例外型別**：raise `HierarchyConflictError`（預設組不可刪除）——**不是** `HTTPException`。
      router 層才轉成對應的 HTTP 狀態碼；同進程呼叫端自行處置
      （契約 K-07 的 `on_denied` 逐字「**不是** `HTTPException`」，
      本條沿用同一形狀。審查 iteration 2 的 `R-09`）。
    source: "`[F6]`=A、entities.md System → Diagram 關係的約束"

  - id: BR4.3
    statement: 不得刪除仍有架構圖歸屬於它的系統。
    category: constraint
    applies_to: System 的刪除端點
    trigger: 刪除系統的請求
    logic: >
      IF 仍有架構圖的歸屬指向該系統 THEN 拒絕並說明還有幾張圖。
    violation_behaviour: 同 `BR4.2`——會製造歸屬為空的架構圖。
      **例外型別**：raise `HierarchyConflictError`（系統底下仍有架構圖）——**不是** `HTTPException`。
      router 層才轉成對應的 HTTP 狀態碼；同進程呼叫端自行處置
      （契約 K-07 的 `on_denied` 逐字「**不是** `HTTPException`」，
      本條沿用同一形狀。審查 iteration 2 的 `R-09`）。
    source: >
      entities.md System → Diagram 的約束。**本條不是 `[F3]` 的答案的一部分**
      ——`[F3]` 問的是刪除**專案**，本條管刪除**系統**；兩者的理由同形
      （不製造懸空），但觸發條件不同，故分列。

  - id: BR4.4
    statement: >
      不得刪除底下仍有系統的專案；拒絕時說明還有幾個系統。**不級聯**。
    category: constraint
    applies_to: Project 的刪除端點
    trigger: 刪除專案的請求
    logic: >
      IF 該專案底下仍有系統 THEN 拒絕並回「衝突」，訊息含剩餘系統數。
    violation_behaviour: >
      級聯刪除會穿過系統觸及使用者的既有架構圖，而「架構圖對系統的歸屬」
      是本單元的責任之一——破壞它的正是本單元就不可接受。
      **例外型別**：raise `HierarchyConflictError`（專案底下仍有系統）——**不是** `HTTPException`。
      router 層才轉成對應的 HTTP 狀態碼；同進程呼叫端自行處置
      （契約 K-07 的 `on_denied` 逐字「**不是** `HTTPException`」，
      本條沿用同一形狀。審查 iteration 2 的 `R-09`）。
    source: >
      `[F3]`=A。**資料庫已經做了一半的決定**：`U4` 交付的實體把系統對專案的
      參照宣告為 restrict，故資料層本就會拒絕。本條把該語意呈現為一個有用的
      訊息（含剩餘數量），而不是一個資料庫錯誤。

  - id: BR4.5
    statement: >
      本輪的 HTTP 介面**沒有改名端點**；`BR4.1` 的「可改名」目前只在 facade 層成立。
    category: policy
    applies_to: Project.name、System.name 的修改
    trigger: 使用者想改名時
    logic: >
      `components.md` 的 `behaviour` 列了「讀、建立、**修改**、刪除」，
      而契約 K-07 的 OpenAPI 區塊只有 `get`／`post`／`delete`——**沒有任何
      `patch` 或 `put`**。故「改」在本輪的 HTTP 表面上不可達。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：`BR4.1`（預設組可改名）讀起來
      像一個已可使用的能力，而在本輪的 HTTP 介面上它**沒有入口**。
      若不寫，`U23 project-pages-ui` 會以為有端點可打。
    source: >
      本站比對 `components.md` 的 `behaviour` 與契約 K-07 的 OpenAPI 區塊查出的落差。
      兩者都是已核可產出，落差不是本站造成的；本站只負責讓它可見（具名缺口 `OPEN-H5`）。

  # ---- BR5.x 變更紀錄（DG-3 的落地）----
  - id: BR5.1
    statement: >
      本單元提供變更紀錄的**查詢**端點，經 `require_story_action(K2)`。
    category: policy
    applies_to: DiagramChangeRecord
    trigger: 查詢請求
    logic: >
      以標籤或系統查詢變更紀錄；經系統查詢時須經架構圖上溯（間接關係）。
    violation_behaviour: 不適用（本條為能力宣告）。
    source: >
      `[F2]`=A，**`DG-3` 的解決**。**契約 K-07 的 `known_gap` 逐字記載此缺口**，
      其 `landing` 為「本單元 `U7`（讀取端屬服務層）；經 `functional-design`」，
      且 `if_implemented` 逐字要求「該查詢端點須經 `require_story_action` 並依
      `team.md` 規則 B 補 `TestClient` 測試」。
      **範圍狀態**：K-07 的 `public_interface` **沒有**讀取方法，故這是新增的介面；
      但它是 K-07 **已預見並寫下條件的分支**，不是本站憑空擴張。
      仍不在 `unit-of-work.md:109` 的交付清單內，故仍要求回補 scope-document。

  - id: BR5.2
    statement: >
      變更紀錄的寫入由 `HierarchyFacade.record_diagram_change` 承載，經 `K2` 判定。
    category: policy
    applies_to: DiagramChangeRecord
    trigger: 架構圖被異動時，由 `WorkOrchestrator` 呼叫
    logic: >
      IF 架構圖被異動 THEN `WorkOrchestrator` 以 `principal` 作為第一參數呼叫
      `record_diagram_change(principal, diagram_id, requirement_summary,
      requirement_label)`，寫入一列紀錄。
    violation_behaviour: 不適用（本條為能力宣告）。
    source: >
      **契約 K-07 的 `public_interface` 逐字已列此方法**，`consumed_by: [U12]`，
      並註明「**U12 是 DiagramChangeRecord 的唯一寫入端**」。
      **範圍狀態更正**：本條原記為「本階段新增、scope 尚未涵蓋」（依 `[F7]`=A），
      該判定**不成立**——寫入路徑早在 K-07 就被契約化，不是本站新增的。
      本站的貢獻只有「它是 facade 方法而非新 HTTP 端點」這個澄清。

  - id: BR5.3
    statement: >
      變更紀錄的來源欄位在資料層**只容納大腦編排這一條路徑**。
    category: constraint
    applies_to: DiagramChangeRecord.source
    trigger: 寫入請求
    logic: >
      IF 來源值不在允許值集合內 THEN 寫入被參照完整性擋下。
      允許值集合目前**只有一個元素**。
    violation_behaviour: >
      寫入失敗。**後果必須被下游知道**：任何非大腦路徑的架構圖異動
      （例如既有 A1 設計 agent 直接改圖）**無法**寫變更紀錄，除非先擴充
      允許值集合——而那是 `U4` 的 schema 變更，不是本單元可做的。
    source: >
      實讀 `U4` 已交付的實體。**`components.md` 的實體屬性清單沒有這個欄位**，
      這是本站查出的落差，記於 entities.md 與 functional-spec.md。

  - id: BR5.4
    statement: 變更紀錄的來源需求摘要去除前後空白後不得為空。
    category: validation
    applies_to: DiagramChangeRecord.requirementSummary
    trigger: 寫入請求
    logic: IF 去空白後為空字串 THEN 拒絕。
    violation_behaviour: 寫入失敗。空摘要的紀錄對查詢端毫無價值。
    source: 實讀 U4 交付物的摘要非空白約束

  - id: BR5.5
    statement: >
      變更紀錄**不是永久稽核軌跡**——它的壽命綁在架構圖上。
    category: policy
    applies_to: DiagramChangeRecord
    trigger: 架構圖被刪除時
    logic: >
      架構圖被刪除時其變更紀錄一併消失（級聯）。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：`unit-of-work.md:250` 把變更
      紀錄列在 ADR-0006 的 audit logging 面下，而稽核軌跡的通常預期是「不會
      因為被稽核的對象消失而消失」。這裡不是那樣，且這是 `U4` 已交付的語意，
      不是本站可改的。
    source: >
      實讀 `U4` 交付物的 `diagramId` 參照（宣告為級聯刪除）。
      **本條原本不完整**（審查 `R-07`）：壽命其實有**兩個**界限，而原文只寫了一個。
      第二個是**保存期**——`U4` 的資料表註解逐字（`schema_rbac.sql:416`）「Retention **90 days** keyed on
      `created_at` (`U4-R1`); the purge mechanism itself is **not in this repo**
      (`U4-R2`)」。故紀錄最長只活 90 天，**而執行清除的機制並不存在於本 repo**；
      兩者都不是本單元可改的。

  - id: BR5.6
    statement: >
      `actorUserId` 必須是**實際造成該次異動的人**，**不得預設為 session 擁有者**。
    category: constraint
    applies_to: DiagramChangeRecord.actorUserId、HierarchyFacade.record_diagram_change
    trigger: 寫入變更紀錄時
    logic: >
      IF 寫入端以「目前 session 的擁有者」填入 `actorUserId`
      THEN 在大腦編排流程中該值極可能**不是**真正造成異動的人。
      THEREFORE `actorUserId` 取自**造成該次異動的行為者**，而非 session。
    violation_behaviour: >
      稽核面失效：紀錄會說「圖被改了」並指向錯誤的人。
      `U4` 的欄位註解逐字（`schema_rbac.sql:420`）「NOT NULL on purpose — a record that says 'the diagram
      changed' but not 'who changed it' fails the audit-logging face」。
    source: >
      **`U4` 已交付 DDL 的欄位註解逐字指派**（`schema_rbac.sql:420`）：「The writer (U12) must store the user
      who actually caused the change and **must NOT default to the session owner**
      (**OQ-H3 still open**)」。審查 `R-07` 指出這一條直接打在本站定義的 facade
      簽名上——`BR1.2` 強制 `principal` 為第一參數，而在大腦編排流程裡 `principal`
      極可能**就是** session 擁有者，正是 `U4` 警告的那個預設。
      本單元是 facade 的擁有者，故是唯一能規定此取值來源的地方。
      **`OQ-H3` 由本條關閉**（就本單元能控制的那一面：facade 的契約）；
      寫入端實際傳什麼值，驗證落點在 `U12` 的 code-generation。

  # ---- BR6.x 讀取的列可見範圍（審查 R-02 的處置）----
  - id: BR6.1
    statement: >
      讀取與 `resolve_work_target` 的列範圍限於**請求者擁有的**專案與其底下的系統。
    category: authorization
    applies_to: >
      **列舉型讀取**：`list_projects`、列出某專案的系統、`resolve_work_target`
      的使用者路徑。**不含**判定支援型查詢（見 `BR6.4`），
      亦不含寫入路徑的擁有者檢查（見 `BR6.5`）。
    trigger: 每一次列舉型讀取或使用者路徑的解析請求
    logic: >
      IF 目標專案的 `ownerUserId` 不是請求者 THEN 該列不出現在結果中；
      以識別碼直接解析他人的專案或系統時，回「查不到」而非「無權限」
      （不以錯誤碼洩漏該資源存在）。
      **本條只管列舉與使用者自己的解析路徑。** 受信任同進程消費端為了做自己的
      授權判定而需要的存在性查詢，走 `BR6.4` 的另一組方法，不套本條的列範圍
      ——否則契約 `K-16`／`K-17` 不可實作（審查 `R-12`）。
    violation_behaviour: >
      **跨使用者外洩。** `K2` 是 `role_permissions` 層的**全域**角色權限
      （契約 K-03 逐字「11 個既有角色 × 2 個 story id」），**不帶任何列層範圍**；
      少了本條，照規格最直接的實作是「有 `K2` 即可列出並解析**任何人**的專案」。
    source: >
      **審查 iteration 1 的 `R-02`（Critical）**。K-07 的 OpenAPI 逐字寫
      「`get`: 列出使用者**可見**的專案」，而「可見」在本站原本沒有任何定義——
      22 條規則裡沒有一條規範讀取的列範圍。使用者裁決（2026-10-06）：
      以 `ownerUserId` 範圍為限。
      **射程於同日由 `[F9]`=A 收窄**（審查 iteration 2 的 `R-12`，Critical）：
      原文把 `resolve_work_target` 整個納入，而 `components.md:559-561`／`:618-620`
      的 `U19`／`U20` interaction 逐字就是「驗證專案存在、讀取 ownerUserId」與
      「驗證系統存在、取得其所屬專案」——**存在的目的就是查別人的專案**。
      具體斷點：`K-16` 的 `assert_can_deactivate(principal, target_user_id)`
      要查的是**被停用者**名下的專案，本條之下回「查不到」，於是 `LastAdminGuard`
      永不觸發；而該契約的 `no_database_backstop` 逐字寫「**這個檢查是唯一防線**」
      （停用端點做的是 UPDATE，`unit-of-work.md:446` 逐字「外鍵對 UPDATE 零效力」）。
      故本條改為只管列舉與使用者自己的解析路徑。

  - id: BR6.2
    statement: >
      `BR6.1` 的擁有者範圍是**本輪的收窄**，不是最終的可見範圍模型。
    category: policy
    applies_to: BR6.1
    trigger: 日後引入成員或分享語意時
    logic: >
      最終模型應委由 `K-16`（契約逐字「**per-project 授權判定的唯一來源**」）。
      本輪不這麼做的理由是**依賴方向**：`ProjectMembership`（`U19`）已
      `depends_on` `ProjectHierarchy`（`U7`）且 `style: sync`
      （`components.md:559-561`，interaction 逐字「驗證專案存在、讀取 ownerUserId」），
      故 `U7` 反向呼叫 `K-16` 會形成循環；且 `K-16`／`K-17` 契約明訂兩層 facade
      **不得互相假設對方已檢查**。拆解該循環是本單元之上的設計變更。
    violation_behaviour: >
      不適用——本條是**誠實宣告**。寫下它的理由：`BR6.1` 讀起來像最終答案，
      而它是一個刻意比最終狀態更窄的版本——**被分享或以成員身分取得的存取在本輪
      看不到任何東西**。若不寫，`U19`／`U23` 會以為可見範圍已經解決。
    source: >
      審查 `R-02` 的 required action 逐字要求「若不在本站定案，則必須記為具名缺口、
      點名 `OQ-14` 未被回答的那一半」。本站**有**定案（`BR6.1`），但定案是收窄版，
      故仍記明缺口：`requirements.md:795` 的 `OQ-14` 逐字包含「**以及是否沿用
      `diagram_shares` 形狀的多對多分享**」，而承接它的 `domain-design` E4 只回答了
      story id 的字首與數量那一半，分享／可見範圍那一半**從未被回答**。
      承接站：`U19 membership-service` 的 `functional-design`（per-unit，
      CONDITIONAL；轉移目標 `code-generation`，ALWAYS）。

  - id: BR6.3
    statement: >
      變更紀錄的讀取同受 `BR6.1` 的範圍限制，且**不得被呈現為完整的變更歷史**。
    category: policy
    applies_to: BR5.1 的查詢介面
    trigger: 每一次查詢變更紀錄
    logic: >
      IF 該紀錄所屬的架構圖上溯到的專案不屬請求者 THEN 不出現在結果中。
      AND **可見性以架構圖自身的擁有者判定，不上溯 `system`→`project`**：
      以 `user_diagrams.user_id` 為準（該欄 `NOT NULL`，直接可得）。
      AND 仍保留 fail-closed：若連圖都取不到，排除而非放行
      （「判定不出來」與「判定為不可見」在實作上極易被寫成前者放行）。
      **可見性與歸屬是兩件事，刻意分開**：`system_id` 仍是**歸屬**的權威來源
      （`contract-summary.md` K-04 `column_added` 逐字「為歸屬的權威來源，
      decisions.md ADR-002」），而本條只用擁有者判**可見性**。
      兩者分開的理由見下方 `source`——上溯路徑在本 repo 的現況下會對新圖整個斷掉。
      AND 回應必須讓讀者知道涵蓋範圍由 `source` 宣告，而非由資料表名稱宣告。
    violation_behaviour: >
      ① 跨使用者外洩（同 `BR6.1`）。
      ② **錯誤的完整性感**：`U4` 的資料表註解逐字（`schema_rbac.sql:416`）「Coverage is declared by the
      `source` column, NOT by the table name — **read source before presenting
      anything**」且「Edits made through the existing A1 page do NOT pass through
      the writer, so rows here are **NOT a complete change history**」。
      把它當成完整歷史呈現，會讓使用者以為沒有紀錄就等於沒有被改過。
    source: >
      審查 `R-02`（範圍）＋ 實讀 `U4` 的資料表註解（完整性）。
      **判定依據於 2026-10-06 由上溯 `system`→`project` 改為架構圖自身的擁有者**
      （審查 iteration 2 的 `R-13`，Critical；使用者裁決 `[R-13]`=A）。
      原文宣稱空的系統參照「在健康的系統中**不可達**」，**該宣稱為假**，
      本站已逐一實測：
      (1) `UserDiagram`（`backend/models.py:91-105`）**根本沒有 `system_id` 這個
      對應屬性**——只有 `id`／`user_id`／`title`／`xml_data`／`updated_at`；
      (2) 三條建圖路徑（`collab_router.py:517`、`review_router.py:131`／`:327`）
      全部以 ORM 建構，故**一律留下空值**；
      (3) 唯一的寫入者是 `hierarchy_migration.py:469-472` 的 raw
      `UPDATE user_diagrams SET system_id = :system WHERE ... IS NULL`，
      而 `hierarchy_migration.py:13` 逐字「**不掛在啟動路徑上**」，
      只有 `backend/scripts/run_hierarchy_migration.py` 這支獨立腳本會跑它。
      **後果**：`AC9.1.4` 的「`system_id IS NULL` 列數為 0」只在遷移跑完的那一刻
      成立，之後**每一張新建的圖都讓它再度不成立**——而大腦寫變更紀錄的對象
      正是新圖。若沿用上溯判定，`W5`／`W8`（本單元唯一真正新增的交付物、
      也是 `DG-3` 的落點）會對所有新圖的紀錄回傳空集合，等於 `DG-3` 實際上沒關閉。
      改以 `user_diagrams.user_id` 判定後，可見性不再依賴那個會斷的參照。
      **「新建的圖永遠沒有系統歸屬」這個缺口本單元修不了**（建立圖不是本單元的
      路徑），記為 `OPEN-H11` 並指派擁有建立路徑的單元。
  - id: BR6.4
    statement: >
      受信任同進程消費端的**存在驗證與擁有者查詢**不套列範圍，但受三道約束。
    category: authorization
    applies_to: >
      供 `U19`／`U20` 做自己的授權判定用的查詢：專案是否存在、取得某專案的
      `ownerUserId`、取得某系統所屬的專案。
    trigger: 受信任同進程消費端呼叫時
    logic: >
      這組方法**不**過濾列擁有者（否則 `K-16`／`K-17` 不可實作），改以三道約束
      取代範圍過濾，三者**缺一即不成立**：
      (1) **只能同進程呼叫**——不得經任何 HTTP path 暴露，`BR6.1` 的列舉端點
      不得以本組方法實作；
      (2) **只回傳判定所需的最小欄位**——存在性布林、擁有者 id、所屬專案 id。
      **不回傳名稱、不回傳清單、不回傳任何可列舉的集合**，故它無法被用來
      枚舉他人的專案，只能用來驗證一個**已經知道識別碼**的資源；
      (3) **呼叫端必須自己完成授權判定**——契約 `K-16`／`K-17` 的 `hard_rule`
      已逐字如此要求（「授權未通過時不得執行受保護操作；判定先於任何讀寫」），
      且 `K-16`／`K-17` 明訂兩層 facade **不得互相假設對方已檢查**。
    violation_behaviour: >
      **若違反 (1)**：列範圍限制被一個 HTTP 端點整個繞過，`R-02` 的外洩重新打開。
      **若違反 (2)**：本組方法成為枚舉通道——這是本條與 `BR6.1` 的實質差別所在，
      最小欄位是「可驗證一個已知 id」與「可列舉未知 id」之間的唯一分界。
      **若違反 (3)**：兩層 facade 互相假設對方已檢查，於是沒有人檢查。
    source: >
      **使用者裁決 `[F9]`=A（2026-10-06），審查 iteration 2 的 `R-12`（Critical）。**
      `[F8]`=A 的代價在當時的三個選項裡完全未揭露，故依 `project.md` 的規則
      回頭指名會壞掉的是什麼並請使用者重選。
      **本條的代價如實記載**：`U7` 因此成為一個「可問出專案 42 的擁有者是誰」的
      通道，緩解靠上述三道約束而非靠範圍過濾。記為具名缺口 `OPEN-H10`。

  - id: BR6.5
    statement: >
      **寫入路徑同樣需要擁有者檢查**，而 `BR6.1` 只涵蓋讀取面。
    category: authorization
    applies_to: create_system、delete_project、delete_system、以及 `BR4.1` 允許的改名
    trigger: 每一次寫入或刪除請求
    logic: >
      IF 目標專案（或目標系統所屬的專案）的 `ownerUserId` 不是請求者
      THEN 拒絕，且以與 `BR6.1` 相同的形狀回「查不到」而非「無權限」。
      本條與 `BR1.1` 的 `K2` 判定**兩者都要過**：`K2` 判「這個角色能不能做這件事」，
      本條判「這一列是不是他的」。
    violation_behaviour: >
      **跨使用者寫入與破壞。** 少了本條，具 `K2` 的任何角色可以在**他人的專案底下
      建立系統**，或**刪除他人的專案與系統**——比 `R-02` 的讀取外洩更嚴重，
      因為它是破壞性的且不可由讀取範圍限制擋下。
      注意 `BR4.2`／`BR4.3`／`BR4.4` 的刪除前置條件**完全不涉及擁有者**
      （它們管的是預設標記與底下還有沒有東西），所以那三條擋不住這一類。
    source: >
      **審查 iteration 2 的 `R-15`（Major，previously-missed）。**
      `[F8]` 與 `[F9]` 兩題的題幹都只談讀取（「列出使用者可見的專案」），
      故寫入面在兩次裁決中都沒有被問到；但 `components.md` 的
      `ProjectHierarchy.behaviour` 逐字涵蓋「讀、建立、修改、刪除」四者。
      本條是把已定案的擁有者範圍一致地套用到其餘三者，**不是新的產品決定**。

  - id: BR6.6
    statement: >
      衝突型拒絕（名稱重複、底下仍有東西）需要一個**契約上存在**的承載方式。
    category: constraint
    applies_to: BR3.2、BR4.2、BR4.3、BR4.4 的拒絕路徑
    trigger: 任一條衝突型規則命中時
    logic: >
      本檔四條規則要求回「衝突」並附數量說明，而契約 K-07 的 `raises` **沒有**
      衝突型的例外、其 OpenAPI 區塊**沒有** 409 宣告。故本單元必須新增
      `HierarchyConflictError`（facade 層）並由 router 轉為 **409**，
      且 route decorator 必須**顯式**宣告 `responses={409: {...}}`。
    violation_behaviour: >
      不顯式宣告則**該契約不會進入 spec、前端也產不出型別，而 CI 保持綠燈**。
      `unit-of-work.md:447` 逐字：實測 `openapi.json` 的 55 個 operation 宣告的
      狀態碼只有 `{200:53, 422:45, 201:1, 204:1}`，**非 2xx/422 的宣告數為 0**。
      同一份檔對 `U19` 已記過這個形狀，本單元的四條衝突規則踩的是同一個洞。
    source: >
      **審查 iteration 2 的 `R-17`（Major，previously-missed）。**
      這是對 K-07 `raises` 與其 OpenAPI 區塊的**契約擴充**，已列入
      `functional-spec.md` §一 的範圍新增表。
```

## 規則摘要（衍生檢視）

| 群組 | 條數 | 管什麼 | 其中「誠實宣告」而非禁令 |
|---|---|---|---|
| `BR1.x` | 5 | 授權：facade 為唯一判定點、禁繞過、判定只有一份、principal 不可偽造、import 檢查 | `BR1.3` |
| `BR2.x` | 4 | 建立路徑的唯一性、前置條件、預設標記、非冪等 | — |
| `BR3.x` | 3 | 名稱的非空白、衝突處置、唯一性的真實強度 | `BR3.3` |
| `BR4.x` | 5 | 刪除、預設組的可變性、改名端點的缺席 | `BR4.5` |
| `BR5.x` | 6 | 變更紀錄的讀寫端、來源限制、行為者取值、壽命與保存期 | `BR5.5` |
| `BR6.x` | 6 | 列舉型讀取的列範圍、其收窄宣告、變更紀錄的範圍與完整性、判定支援型查詢的三道替代約束、寫入面的擁有者檢查、衝突型拒絕的承載方式 | `BR6.2` |

合計 **29 條**。本數字由腳本**以 `yaml.safe_load` 解析本檔的 yaml 區塊、取 `rules[].id`**
實算，不是 grep、也**不是**各群條數相加的結果——先前某一版正是以相加得出 22 而碰巧與
本檔實況一致，但它的危險在於群組欄本身若漏列一群（當時新增的 `BR6.x` 即是）相加仍會自洽。
逐群數字供閱讀，總數以解析結果為準：5＋4＋3＋5＋6＋6＝29，兩者相符。
**改用 parser 而非 grep 的理由**：本區塊在 2026-10-06 之前**從未被任何 YAML parser
成功載入過**（兩處 `source:` 的值以反引號開頭，而反引號在 YAML 是保留指示字元，
解析在第 217 行即中止），而五個 sensor 全部沒有發現——它們分別只數 H2、只讀
`traceability.json`、只做字串比對、或對 Markdown 回 `no-eslint-config`／`no-tsconfig-found`。
「sensor 全綠」與「本區塊真的可機讀」是兩件沒有交集的事，故本檔的計數一律由解析結果產生。

五條 `policy` 類規則刻意寫成「誠實宣告」而非禁令（`BR1.3`／`BR3.3`／`BR4.5`／
`BR5.5`／`BR6.2`）：它們的 `violation_behaviour` 都是「不適用」。寫下它們的理由一致——
**若不寫，下游會對本單元的保證強度產生過高的預期**：以為底層服務層也會擋授權、
以為名稱不會重複、以為改名已有端點可打、以為變更紀錄是永久的、以為可見範圍已經解決。
**前四者的不成立都不是本站的選擇造成的**（分別來自契約 K-07 的授權模型、
`[F5]`=C 的已知代價、K-07 的 OpenAPI 與 `components.md` 的落差、`U4` 已交付的語意）；
**第五者（`BR6.2`）不同——它是本站刻意選的收窄**（`[F8]`=A），理由是依賴方向而非外部限制，
故它比其餘四者更需要被下游看見：最終模型屬 `K-16`，而本輪的擁有者範圍會讓
被分享或以成員身分取得的存取**看不到任何東西**。

### 本檔與上游契約的關係

`BR1.x` 與 `BR2.1`／`BR2.4`／`BR5.2` **不是本站發明的**——它們是契約
`K-07 hierarchy-authorized-facade` 既有條款在規則層的落地。本站的實質貢獻有四項
（原為兩項，審查 iteration 1 後增為四項）：

1. **`BR1.4`**（principal 不可偽造）——關閉 K-07 自己具名的 `residual_gap`，
   即 `unit-of-work.md:222` 指派給本站的事項。
2. **`BR6.1`–`BR6.3`**（讀取的列可見範圍）——**審查 `R-02`（Critical）＋使用者
   `[F8]`=A 裁決**。K-07 的 OpenAPI 用了「可見」這個詞而從未定義它，`K2` 又是
   不帶列層範圍的全域角色權限；本站補上定義並誠實標記它是收窄版。
3. **`BR5.6`**（行為者不得預設為 session 擁有者）——`U4` 的欄位註解
   （`schema_rbac.sql:420`）逐字指派，且它直接打在本站定義的 facade 簽名上
   （`BR1.2` 的 `principal` 第一參數在編排流程中極可能**就是** session 擁有者）。
   本單元是 facade 的擁有者，故是唯一能規定取值來源的地方。
4. **`BR4.5`**／**`BR5.3`**／**`BR5.5`**——把三處上游之間的落差變成可見的具名限制，
   而非讓下游自行撞上。
