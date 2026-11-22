# Functional Design 問題檔 — `U7 hierarchy-service`

> Stage：`functional-design`（Construction）　Unit：`U7 hierarchy-service`（`service`，M）
> 建立時間：2026-10-05
> Depth：standard（5–8 題）。本檔 **6 題**。

---

## 前言：本站不重問的事

下列事項已由上游核可，**本站不重問**，逐項可引用到具體定案：

| 已定案 | 出處（逐字可查） |
|---|---|
| 三層資料模型（專案 → 系統 → 架構圖）與其 DDL | `U4 hierarchy-data` 已交付並已登記完成；`schema_rbac.sql` 的 `projects`／`systems`／`user_diagrams.system_id` 實體已在磁碟 |
| `system_id` 為歸屬的權威來源；`user_id` 保留為「誰建的」 | `components.md` `ProjectHierarchy.behaviour`；`decisions.md` ADR-002 |
| 遷移後 `system_id IS NULL` 的列數必須為 0，不為 0 即大聲失敗 | 同上；`U4` 已交付（`tests.test_hierarchy_migration` 15 OK，含失敗路徑） |
| 讀／建／改／刪一律經 `require_story_action(K2)` | `components.md` `behaviour`；`unit-of-work.md:247` ADR-0006 IAM 列 |
| `K1`／`K2` 兩個 story id 與 330 列權限矩陣 | `U3 rbac-story-ids` 已交付並已登記完成 |
| 建立路徑有**兩個使用者入口**但共用**同一條寫入路徑**，授權／稽核／錯誤訊息各只有一份 | `components.md` `behaviour`、`responsibilities` |
| 不建 `Requirement` 實體、不建需求↔系統多對多關聯表 | `components.md` `behaviour`；ADR-009 |
| 驗證方式為 TestClient HTTP ＋ allow/deny 雙向 | `unit-of-work.md:111`；`team.md` 規則 A／B |

## 本站承接的兩項上游未決事項（**不是本站新開的題**）

`unit-of-work.md` 把兩項明文指派給 `functional-design`，即本站：

1. **`:222`**——「授權**只掛在 dependency 層**，service 層無第二道角色檢查——同進程直呼 service 函式會完整繞過 RBAC。（審查 R-01 指出本 intent 的 `U10`／`U12` → `U7` 兩條 `sync` 邊落在此風險上，已記為 Accepted risk 並指派 `functional-design`）」→ 本檔 **[F1]**
2. **`:220`**——`DG-3`：`DiagramChangeRecord` 有寫入端（`U12`）與 schema 保管（`U4`）但**沒有讀取端**，而使用者定案 `[DD:E8]`=C 的理由逐字是「可用同一標籤搜尋它影響過哪些圖」——那句話描述的就是一個讀取端。「故其解決落點是 `U7`」→ 本檔 **[F2]**

---

## [F1] `SessionContext`／`WorkOrchestrator` 要怎麼取用階層資料，而不繞過 `require_story_action(K2)`？

**這是本站最重要的一題，而它是一個已被記錄的自我矛盾。** `components.md` 的
`ProjectHierarchy.behaviour` 逐字寫「讀、建立、修改、刪除一律經 require_story_action
（story id K2），**不得有任何繞過該 dependency 的路徑，含同進程直呼 service 層**」；
而**同一份檔**的機讀區塊宣告兩條入邊：

| 消費端 | 宣告的互動 | 邊的性質 |
|---|---|---|
| `SessionContext`（`U10 session-store`） | 驗證並解析作業對象的三層識別 | `sync` |
| `WorkOrchestrator`（`U12 work-orchestrator`） | 架構圖被異動時寫入變更紀錄 | `sync` |

`sync` 就是同進程呼叫，也就是 `behaviour` 那句話禁止的東西。兩句話直接對撞。
`require_story_action` 是 FastAPI dependency，只在 HTTP 請求經過路由時才會執行；
同進程直呼 service 函式**完全不會觸發它**。

- **A — 兩個消費端一律走 HTTP 並帶使用者 token**：`U10`／`U12` 不呼叫 service 函式，
  改以 `httpx` 對自己的 `/api/...` 端點發請求並帶上該使用者的 token，授權因此必然
  經過 `require_story_action`。代價：同進程 HTTP 的額外延遲與連線開銷；大腦端必須
  持有可轉發的使用者 token（`U13 brain-gateway` 的 WS 握持的是 token，這點可行）；
  本 repo 已有同型先例（`project.md` 逐字要求呼叫既有 C1「一律走 HTTP 帶使用者
  token，**不得**同進程直呼 `estimate_intake_service`」）。**與既有規則一致。**
- **B — service 層加第二道授權檢查（縱深防禦）**：service 函式簽名改為必須收一個
  已解析的 principal，函式內自行再查一次 `K2` 權限。代價：授權邏輯有兩份，
  兩份會漂移；但同進程與 HTTP 兩條路都被保護，且不需要轉發 token。
- **C — service 層只接受「授權憑證」物件，且只有 dependency 能鑄造它**：
  service 函式收一個不可偽造的 `AuthorizedPrincipal`，其建構子只在
  `require_story_action` 內被呼叫。同進程呼叫者拿不到它，因此編譯期（型別層）
  就擋住繞過。代價：新增一個型別與一條鑄造規則；授權邏輯仍只有一份。
- **D — 接受繞過，明文記為殘餘風險**：維持現狀，在 `rules.md` 與 `functional-spec.md`
  明寫「同進程呼叫不受 `K2` 保護」，並把它交給 `U10`／`U12` 自己負責。
  代價：`behaviour` 那句「不得有任何繞過」成為假敘述，而這正是上游已經接受過
  一次的狀態——本站若再接受一次，等於這個指派從未被處理。

[Answer]: A — 兩個消費端一律走 HTTP 並帶使用者 token

## [F2] `DiagramChangeRecord` 要不要有讀取端？（`DG-3`）

寫入端在 `U12`、schema 在 `U4`，**讀取端目前不存在**。`[DD:E8]`=C 的理由逐字是
「可用同一標籤搜尋它影響過哪些圖」。本 repo 已有同型前例：`estimate_audit_events`
只寫不讀。

- **A — 本單元提供一個查詢端點**：`GET` 以標籤或系統查變更紀錄，經
  `require_story_action(K2)`，並依 `team.md` 規則 B 補 `TestClient` 測試。
  這讓 `[DD:E8]`=C 的那句理由成真。代價：本單元多一個端點與一組測試。
- **B — 不提供，明文記為已知的只寫不讀**：與 `estimate_audit_events` 同形，
  在 `rules.md` 記明「寫入供日後查核，本輪無讀取端」。代價：`[DD:E8]`=C 的理由
  在本輪不成立，`DG-3` 原樣留著。
- **C — 提供，但只給平台管理者**：端點存在但權限收在 `Platform_Admin`／
  `Platform_Owner`，不走 `K2`。代價：引入第二套授權語意（`U8` 的可見範圍模型
  已經是第二套），而本單元其餘端點都走 `K2`。

[Answer]: A — 本單元提供一個查詢端點

## [F3] 刪除專案時，若它底下還有系統，行為是什麼？

**資料庫已經做了一半的決定**（實讀 `schema_rbac.sql`）：
`systems.project_id` 是 `INTEGER NOT NULL REFERENCES projects (id) **ON DELETE RESTRICT**`，
所以**資料庫層就會拒絕**刪除一個還有系統的專案。`projects.owner_user_id` 則是
`NOT NULL REFERENCES users (id)` 且**沒有 `ON DELETE` 子句**。

- **A — 端點照資料庫語意回 409 Conflict，並說明還有幾個系統**：不試圖級聯，
  把 `RESTRICT` 原樣呈現為「請先刪除或搬移底下的系統」。與 DDL 一致，不需改 schema。
- **B — 端點級聯刪除（先刪系統再刪專案）**：需在 service 層自行依序刪除。
  但底下的系統可能還掛著架構圖（`user_diagrams.system_id`），級聯會連帶影響使用者
  的既有圖——而「架構圖的歸屬」是本單元的責任之一。
- **C — 不提供刪除端點**：`behaviour` 列了「刪」，但本輪只實作讀／建／改。
  代價：與 `behaviour` 的逐字清單不符，須明記為本輪縮減。

[Answer]: A — 端點照資料庫語意回 409 Conflict，並說明還有幾個系統

## [F4] 「兩個入口共用同一條寫入路徑」在設計上如何被保證？

`components.md` 要求「建立路徑有兩個使用者入口（脈絡列選單的表單、對話式建立的
確認卡）但共用同一條寫入路徑，授權檢查、稽核紀錄與錯誤訊息各只有一份」。
`unit-of-work.md:109` 把它列為本單元的交付物之一。

- **A — 一個 HTTP 端點，兩個 UI 入口都打它**：寫入路徑的唯一性由「只有一個端點」
  保證，可機械驗證（端點數 = 1）。對話式建立由大腦端轉成對同一端點的呼叫。
- **B — 兩個端點共用一個 service 函式**：寫入邏輯唯一，但授權與錯誤訊息各在兩個
  端點上，仍可能漂移；需另加測試斷言兩者訊息相同。
- **C — 一個端點，但接受一個「來源」欄位以區分入口**：單一寫入路徑，且稽核紀錄
  能記下是哪個入口建的。代價：多一個請求欄位與其值域驗證。

[Answer]: A — 一個 HTTP 端點，兩個 UI 入口都打它

## [F5] 專案與系統的名稱唯一性範圍是什麼？

DDL 目前只有 `CHECK (length(trim(name)) > 0)`——**沒有任何唯一約束**（實讀
`schema_rbac.sql`）。另有「兩個部分唯一索引」記在檔頭第 11 行，其對象是
`is_default`，不是 `name`。

- **A — 不設唯一性，同名允許**：維持 DDL 現狀，零 schema 變更。使用者可建兩個
  同名專案，靠 id 區分。代價：作業對象選擇器會出現兩個看起來一樣的選項。
- **B — 專案名在同一 owner 內唯一、系統名在同一專案內唯一**：符合直覺，但這是
  **schema 變更**（新增兩個唯一索引），會觸發 `project.md` 的 blocking 規則
  （`schema_rbac.sql` ＋ `DEPLOY.md` 同步），且 `U4` 已登記完成——等於回頭改一個
  已交付單元的 schema。
- **C — 不設 DB 約束，但在 service 層檢查並回 409**：無 schema 變更，訊息友善；
  代價是併發下仍可能建出同名（檢查與寫入之間有空窗），屬已知的 TOCTOU。

[Answer]: C — 不設 DB 約束，但在 service 層檢查並回 409

## [F6] 預設專案／預設系統（`is_default`）可以被改名或刪除嗎？

遷移為每個持有圖的使用者建立「預設專案／預設系統」（`is_default = TRUE`）。
DDL 有 `is_default BOOLEAN NOT NULL DEFAULT FALSE` 與檔頭提到的兩個部分唯一索引。

- **A — 可改名，不可刪除**：改名無害（`system_id` 才是權威來源，不是名稱）；
  刪除會讓既有圖的 `system_id` 懸空，而「遷移後 `system_id IS NULL` 必須為 0」
  是已核可的不變量。
- **B — 皆不可**：預設組完全不可變，最保守；代價是使用者被迫看著一個叫
  「預設專案」的東西。
- **C — 皆可，但刪除前必須先把圖搬走**：最自由；代價是需要一個「搬移圖到另一個
  系統」的能力，而那不在本單元的交付清單內。

[Answer]: A — 可改名，不可刪除

---

## [F7] 追問：`DiagramChangeRecord` 的寫入端點歸誰交付？

**本題不是本站主動開的，是 `[F1]`=A 的直接後果，由 Step 3 的強制歧義分析查出。**

`[F1]`=A 讓兩條 `sync` 邊都變成 HTTP 呼叫。逐一對照已核可的交付清單
（`unit-of-work.md:109` 逐字「ProjectHierarchy 的讀／建／改／刪 HTTP 端點，
全經 require_story_action(K2)；建立路徑的單一寫入端（兩個入口共用）」）：

| 邊 | 宣告的互動 | 變成什麼 | 在交付清單內？ |
|---|---|---|---|
| `SessionContext` → `ProjectHierarchy` | 驗證並解析作業對象的三層識別 | **讀**取端點 | 是——「讀」涵蓋 |
| `WorkOrchestrator` → `ProjectHierarchy` | 架構圖被異動時寫入變更紀錄 | `DiagramChangeRecord` 的**寫入**端點 | **否** |

`ProjectHierarchy` 的 `entities` 清單包含 `DiagramChangeRecord`，故該端點依
**擁有權**屬本單元；但它不在本單元**已核可的範圍**內。

- **A — 本單元現在一併交付，並明標為範圍新增**
- **B — 記為具名缺口，指派 `U12` 的 `functional-design`**
- **C — 本單元只交付讀取端，`U12` 自行決定寫入方式**

[Answer]: A — 本單元現在一併交付，並明標為範圍新增

### 作答後果（依 `project.md` 的規則，於此明文揭露）

採 A 之後，本單元的交付比 `unit-of-work.md:109` 的已核可清單**多兩個端點**，
兩者都源自本站的裁決而非上游：

| 新增 | 來源 | 範圍狀態 |
|---|---|---|
| `DiagramChangeRecord` **查詢**端點 | `[F2]`=A（解決 `DG-3`） | **本階段新增，scope 尚未涵蓋** |
| `DiagramChangeRecord` **寫入**端點 | `[F7]`=A（`[F1]`=A 的後果） | **本階段新增，scope 尚未涵蓋** |

兩項都必須在 `functional-spec.md` 與 `traceability.json` 就地標記並要求回補
`scope-document`，不得當成既有能力 9 的自然延伸吸收。

---

## Supersession 註記（2026-10-06）：`[F1]` 與 `[F7]` 的作答被已核可契約 K-07 推翻

**上方 `[F1]`／`[F7]` 的原作答與選項本文一律不改寫**，保留它們是為了讓
「A 曾被選過、而它為何不成立」可被追溯。本節記載推翻的來源與範圍。

### 怎麼發現的

`upstream-coverage` sensor 回報 `contract-summary` 未被本站任何產出引用
（`unreferenced: [unit-of-work-story-map, requirements, contract-summary]`）。
追查時才讀 `contract-summary.md`——**而它早已決定 `[F1]` 問的那件事**。
`functional-design.md` 的 `consumes` 把 `contract-summary` 標為 `required: false`，
我因此在 Step 1 跳過它；**那是我的錯**，不是 sensor 的誤報。

### K-07 逐字說了什麼

契約 `K-07 hierarchy-authorized-facade`（owner `U7`，即本單元）：

| 鍵 | 逐字內容 | 與 `[F1]`=A 的關係 |
|---|---|---|
| `consumers.in_process` | `[U10 session-store, U12 work-orchestrator]` | **直接牴觸**——A 說這兩者改走 HTTP |
| `sole_entry` | 「`HierarchyFacade` —— 受保護操作的**唯一**授權入口」 | A 之下不存在 facade |
| `rule` | 「FastAPI router 與同進程呼叫端**共用這一個入口**，故 `require_story_action` 的判定只有一份呼叫點」 | A 之下同進程呼叫端根本不呼叫 |
| `identity_passing` | 「每個 facade 方法的第一個參數為 `principal`……由呼叫端傳入；facade 不自行從 request 取身分」 | A 之下身分走 HTTP 標頭 |
| `on_denied` | 「raise `HierarchyForbidden(story_id='K2', action=…)` —— **不是** `HTTPException`」 | A 之下拒絕走 HTTP 403 |
| `residual_gap` | 「『facade 是唯一入口』**無機械強制**——繞過它直呼底層 service 只能靠 code review 擋下。本站如實記載此缺口，不宣稱已解決」 | **這正是 `unit-of-work.md:222` 指派給本站的那個缺口** |

`[F7]` 同樣已被回答：K-07 的 `public_interface` 列有
`HierarchyFacade.record_diagram_change`，`consumed_by: [U12]`，並註明
「**U12 是 DiagramChangeRecord 的唯一寫入端**」。故寫入路徑屬本單元**是對的**
（`[F7]`=A 的結論成立），但承載形式是 **facade 方法**而非新的 HTTP 端點。

### 本站誤解了指派的性質

`unit-of-work.md:222` 指派給 `functional-design` 的，不是「替 `sync` 邊另選一種
通訊機制」，而是**把 K-07 已經選定的 facade 模型的「唯一入口」性質變成可強制的**
——K-07 自己逐字說那一點「無機械強制」。`[F1]` 的選項 C（不可偽造的憑證，
只有入口能鑄造）正是該模型的自然強化；選項 A 則是把模型整個換掉。

### 使用者裁決（2026-10-06）

**遵循 K-07，並以不可偽造的 principal 關閉其 `residual_gap`。**

[Answer]: Follow K-07; close its gap with an unforgeable principal

### 受影響的產出

| 產出 | 影響 |
|---|---|
| `entities.md` | **不受影響**（資料形狀與授權機制無關） |
| `traceability.json` | 不受影響；但 `BR1.2`／`BR1.3` 的 `reverse` 說明需隨規則改寫同步 |
| `rules.md` | `BR1.2`／`BR1.3` 重寫，另增 `BR1.4`（principal 的鑄造限制） |
| `functional-spec.md` | W3／W4 重寫；§四、§八 的相關段落同步 |

> **上表第 2 列於 2026-10-06 更正。** 原文寫 `traceability.json`「不受影響」，
> 實際受影響且一度漏改——`BR5.2` 的 `reverse` 說明整段是依 `[F1]`=A 的 HTTP
> 模型寫的（逐字「由 [F1]=A 的後果逼出（WorkOrchestrator 改走 HTTP 就需要一個
> 端點可打）……不在已核可交付清單內，同樣已標記並要求回補」），而 `functional-spec.md`
> §一 的表已先行更正。審查 `R-04` 抓到此跨檔傳播失敗，現已同步。

---

## `[F8]` 讀取時「使用者可見的專案」指的是什麼？

**本題不是本站主動開題，是審查 iteration 1 的 `R-02`（Critical）逼出的。**
契約 K-07 的 OpenAPI 逐字寫「`get`: 列出使用者**可見**的專案」，而「可見」
在本站當時的 22 條規則裡**沒有任何定義**；`K2` 是 `role_permissions` 層的
**全域**角色權限（契約 K-03 逐字「11 個既有角色 × 2 個 story id」），
**不帶任何列層範圍**。故照本站原規格最直接的實作是：**任何具 `K2` 的角色
都能列出並解析任何人的專案**——跨使用者外洩。

| 選項 | 完整文字 |
|---|---|
| **A（建議）** | **本輪以擁有者範圍為限，並記為具名缺口指向 `K-16`。** 讀取與 `resolve_work_target` 只回傳 `ownerUserId` 等於請求者的列；以識別碼直接解析他人資源時回「查不到」而非「無權限」（不以錯誤碼洩漏存在）。立即關閉外洩，代價是**被分享或以成員身分取得的存取在本輪看不到任何東西**。該缺口記明指向契約 `K-16`（per-project 授權判定的唯一來源），並點名 `OQ-14` 未被回答的那一半（`requirements.md:795` 逐字「以及是否沿用 `diagram_shares` 形狀的多對多分享」——承接它的 `domain-design` E4 只回答了 story id 的字首與數量那一半）。 |
| **B** | **本輪即委由 `K-16` 判定。** 語意最完整，但**會形成循環依賴**：`ProjectMembership`（`U19`）已 `depends_on` `ProjectHierarchy`（`U7`）且 `style: sync`（`components.md:559`，interaction 逐字「驗證專案存在、讀取 ownerUserId」），`U7` 反向呼叫 `K-16` 即成環；且 `K-16`／`K-17` 契約明訂兩層 facade **不得互相假設對方已檢查**。拆解該循環是本單元之上的設計變更。 |
| **C** | **維持現狀，只把缺口記下來。** 不加任何列層規則，在殘餘風險段寫明「可見範圍未定義」。代價是把一個**可被利用的跨使用者外洩**留給下游，而它是靜默的——不會有錯誤，只會沒有範圍。 |

[Answer]: A — Owner-scoped now; flag membership as the known successor

落點：`rules.md` 新增 `BR6.1`（範圍）、`BR6.2`（收窄宣告與依賴方向理由）、
`BR6.3`（變更紀錄的範圍與完整性）；`functional-spec.md` 新增 `W7`／`W8`
與 `W3` 的補充；`traceability.json` 新增 `OPEN-H7`。

---

## `[F9]` `BR6.1` 的列範圍要不要區分「列舉」與「判定支援」兩類呼叫？

**本題是審查 iteration 2 的 `R-12`（Critical）逼出的，而它是 `[F8]`=A 的代價——
那個代價在 `[F8]` 的三個選項裡完全沒有被揭露。依 `project.md` 的規則，
使用者選的選項製造出新的正確性問題時，我必須指名會壞掉的是什麼並請其重選。**

### 會壞掉的是什麼（已逐一查證，非推測）

`BR6.1` 寫「讀取只回傳 `ownerUserId` 等於請求者的列」。但本單元有兩個同進程呼叫端
**存在的目的就是查別人的專案**：

| 呼叫端 | `components.md` 逐字的 interaction | 在 `BR6.1` 之下會怎樣 |
|---|---|---|
| `ProjectMembership`（`U19`） | `:559-561`「驗證專案存在、**讀取 ownerUserId**」 | 讀不到別人的列 → 讀不到 `ownerUserId` |
| `RequirementRegistry`（`U20`） | `:618-620`「驗證系統存在、取得其所屬專案」 | 同上 |

具體到契約 `K-16` 的兩個方法：

- **`MembershipFacade.assert_can_deactivate(principal, target_user_id)`**
  （`contract-summary.md` `consumed_by: ["既有停用端點 user_router.py:673"]`）
  要檢查的是**被停用者**名下的專案會不會失去最後一位管理者。
  管理員停用別人時，`principal` 是管理員、要查的列屬於 `target_user_id`
  ——`BR6.1` 之下回「查不到」，於是 `LastAdminGuard` **永遠不會觸發**。
  而該契約的 `no_database_backstop` 逐字寫「**這個檢查是唯一防線**」
  （停用端點做的是 UPDATE，外鍵對 UPDATE 零效力）。
- **`MembershipFacade.resolve_project_role`**（三個消費端）服務的正是
  **不是擁有者**的成員——`BR6.1` 之下他們的專案一律「查不到」。

即 `K-16`／`K-17` 在 `BR6.1` 之下**不可實作**。

| 選項 | 完整文字 |
|---|---|
| **A（建議）** | **把 `BR6.1` 拆成兩類操作。** ①**列舉型讀取**（`list_projects`、列出某專案的系統、`resolve_work_target`）維持請求者範圍限制——`R-02` 要堵的外洩就在這一類。②**判定支援型查詢**（專案是否存在、取得 `ownerUserId`、取得某系統所屬專案）不受列範圍限制，但同時受三道約束：(i) **只能同進程呼叫**，不經任何 HTTP path 暴露；(ii) **只回傳判定所需的最小欄位**（存在性布林、擁有者 id、所屬專案 id），**不回傳名稱、不回傳清單、不回傳可列舉的集合**；(iii) 每個呼叫端必須自己完成授權判定——`K-16`／`K-17` 的 `hard_rule` 已逐字如此要求。代價誠實說：`U7` 因此成為一個「可問出專案 42 的擁有者是誰」的通道，緩解靠上述三道約束而非靠範圍過濾，須記為具名缺口。 |
| **B** | **讓 `K-16` 不經 `U7`，直接讀資料表取 `ownerUserId`。** 代價：直接打破契約 K-07 的 `sole_entry`（`HierarchyFacade` 是 projects／systems 受保護操作的**唯一**授權入口），且本單元 `BR1.5`「沒有任何單元繞過 facade 直呼底層 service」會立刻有一個官方例外——**本單元最核心的保證因此失效**，而這個保證正是 `unit-of-work.md:222` 指派給本站要強化的那一個。 |
| **C** | **撤回 `BR6.1`，回到「具 `K2` 即可讀任何列」，把可見範圍整個交給 `K-16`。** 代價：`R-02` 的跨使用者外洩重新打開，且 `U19` 在本輪**不交付**（它是另一個單元），所以在它落地前**完全沒有**列層範圍——這正是 `[F8]` 當時選 A 而非 C 的理由。 |
| **D** | **判定支援型查詢改由 `U4` 的資料層直接提供**（新增一個不帶授權的唯讀 accessor，明標僅供同進程授權判定）。代價：新增一個刻意不授權的入口，且 `U4` 已登記完成——要回頭動一個已完成單元，並觸發 `project.md` 的 schema／部署同步規則判定。 |

[Answer]: A — 拆成列舉型與判定支援型

---

## `[R-13]` 變更紀錄的可見性判定依據（審查 iteration 2 的 `R-13`，Critical）

已實測三項，`BR6.3` 原本「空的系統參照在健康的系統中不可達」的宣稱為假：
`UserDiagram`（`backend/models.py:91-105`）沒有該欄位的 ORM 屬性；三條建圖路徑
（`collab_router.py:517`、`review_router.py:131`／`:327`）全走 ORM 故一律留空；
唯一寫入者 `hierarchy_migration.py:469-472` 只被獨立腳本呼叫（該檔 `:13` 逐字
「**不掛在啟動路徑上**」）。故 `AC9.1.4` 的不變量只在遷移當下成立。

| 選項 | 完整文字 |
|---|---|
| **A（建議）** | **本單元改用圖的 `user_id` 判定可見性，缺口上報。** 以 `user_diagrams.user_id`（`NOT NULL`、直接可得）判定，不再上溯 `system`→`project`，fail-closed 分支因此回歸真正罕見。但「新建的圖永遠沒有系統歸屬」這個缺口本單元修不了，記為具名缺口並指派擁有建立路徑的單元，同時明寫它讓 `W5` 的 `systemId` 篩選對新圖無效。 |
| **B** | **本輪就把建立路徑一併修掉。** 在本單元的設計裡一併規定三條建立路徑都要指派 `system_id`。代價是跨出本單元的交付邊界（`collab_router`／`review_router` 屬既有模組），且 `team.md` 明訂修改既有 router 不得夾帶重構，而這三處目前沒有 HTTP 層測試保護。 |
| **C** | **只記缺口，不改可見性判定。** 維持上溯判定。代價是 `W5`／`W8`——本單元唯一真正新增的交付物、也是 `DG-3` 的落點——對所有新圖的紀錄回傳空集合，等於 `DG-3` 實際上沒有關閉。 |

[Answer]: A — 本單元改用圖的 user_id，缺口上報

---

## Consolidated Summary Confirmation

本站（`U7 hierarchy-service` 的 functional-design）四份產出已定稿，請確認下列摘要
與你的裁決一致：

**九題裁決**：`[F1]`=A（**已於同日被 K-07 推翻**，見 `OPEN-H6` 的 supersession）、
`[F2]`=A 提供變更紀錄查詢端點、`[F3]`=A 刪除有系統的專案回 409 並說明數量、
`[F4]`=A 一個端點兩個 UI 入口、`[F5]`=C service 層檢查名稱且零 schema 變更、
`[F6]`=A 預設組可改名不可刪除、`[F7]`=A（**射程已收窄**：寫入路徑早在 K-07
就被契約化，故不是本階段新增）、`[F8]`=A 擁有者範圍（**射程已由 `[F9]` 收窄**）、
`[F9]`=A 拆成列舉型與判定支援型、`[R-13]`=A 改用圖的 `user_id` 判定可見性。

**產出**：`entities.md`（3 個實體）、`rules.md`（**29 條**規則，由 parser 實算：
`BR1` 5／`BR2` 4／`BR3` 3／`BR4` 5／`BR5` 6／`BR6` 6）、`functional-spec.md`
（8 個工作流程 W1–W8、6 處上游落差、ADR-0006 四面向逐項判定 ＋ PBT 判為 N/A）、
`traceability.json`（8 個 upstream id、27 筆 reverse、**12 項 open_items**）。

**兩輪審查**：iteration 1 判 NOT-READY（11 項），iteration 2 判 NOT-READY
（19 項：Critical 4／Major 10／Minor 5；iteration-1 的 11 項判 5 Resolved／
6 Unresolved）。**審查額度已用盡（上限 2）**，故本輪的修正**無人複驗**——
其中包含兩個 Critical 的處置（新增 `BR6.4`／`BR6.5`／`BR6.6` 三條規則、
`BR6.3` 的判定依據改寫）。本輪 14 項發現已逐一處置，並以 parser 實算計數、
腳本化引用掃查（逐一印出每個 `<檔>:<行>` 的實際內容）、事實掃查三種機械檢查複驗。

**須你知悉的三件事**：
1. **`OPEN-H11` 可能沒有有效的承接站。** 「新建的圖從未被指派系統歸屬」在建立
   路徑上，而本 intent 的 24 個單元**沒有一個擁有建圖路徑**。依規則，找不到誠實
   的轉移目標時要寫「無自然承接站」並交回你裁決，不得填一個看起來合理的站。
2. **本站查出並更正了一處上游引用錯誤**：兩份已核可上游都把既有停用端點寫成
   `user_router.py:673`，實為 `:682`（端點 decorator 在 `:644`）。事實正確、
   只有定位錯；依規則不回改已核可上游，已記為第 6 處落差。
3. **`BR6.6` 是對已核可契約 K-07 的擴充**（新增 `HierarchyConflictError` ＋ 409
   宣告），已列入 §一 的範圍新增表並要求回補契約。

[Answer]: Looks correct
