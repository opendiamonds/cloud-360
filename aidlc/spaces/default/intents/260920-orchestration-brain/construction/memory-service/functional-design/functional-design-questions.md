# Functional Design 問題檔 — `U8 memory-service`

> 本單元為 `service`、size `L`，擁有 `US4.1`／`US4.2`／`US4.3`／`US4.4` 共 12 條 AC。
> 契約為 `K-08`（`facade` ＋ `http`），授權模型是本 repo 的**第二套**
> （擁有者 ＋ 可見範圍，非 story-action）。
>
> **本站只問三題**，全部是上游明文指派或查證後確認不存在的決定；
> 其餘設計面已由 `components.md` 的 `MemoryStore` behaviour 與 `K-08` 鎖定。

## 〇、不重問的事（上游已定案，逐項附依據）

| 事項 | 定案處 |
|---|---|
| 三種記憶落在同一 database 的獨立 schema；grant 只開放記憶 schema | `FR4.2`／`FR4.4`；`K-05` |
| 擁有者由本單元依**呼叫者的已驗證身分**設定，不得由呼叫方指定 | `FR4.3a`；`K-08` 的 `write_side_enforcement` |
| 可見範圍預設最窄（僅擁有者可見） | `FR4.3b`；`K-08` 的 `default_scope` |
| 放寬可見範圍僅 `Platform_Admin`／`Platform_Owner`，且每次留稽核 | `K-08` 的 `scope_widening`（`OQ-12` 已由它定案） |
| 相似度檢索只比對同一 `embeddingModel` 的列 | `MemoryStore.behaviour`；`schema_rbac.sql:473-474` 的 COMMENT |
| 五個 facade 方法與四條 HTTP path | `K-08` 的 `public_interface` ＋ OpenAPI 半邊 |
| `MemoryForbidden(reason=<owner\|scope>)` → 403 ＋ detail 前綴 | `K-08` 的 `on_denied` |
| `write` 非冪等、`search` 唯讀冪等、`delete` 冪等（再刪為 `MemoryNotFound`） | `K-08` 的 `retry_and_idempotency` |
| `/memory` 走 `ProtectedRoute` 但不包 `CapabilityRoute`，不需新 story id | `K-08` 的路由守衛註記 |
| `DG-1`（稽核事件在其記憶被清除後的去向） | **已關閉**：`U5` 的 DDL 定案（刻意無外鍵，稽核比記憶活得久），`U9` 的 `nfr-requirements §三` 已逐項核對關閉 |
| 90 天清除由 workflow 承載、`expires_at` 為 `createdAt + 90 days` | `FR4.5`／`FR4.5a`；`schema_rbac.sql:477-478`；`U9` 已交付 |

### 〇之一、本站查證並就地裁決的一項矛盾（不出成題目，因為 DDL 已裁決）

`contract-summary.md:643` 的 `observable_side_effects` 逐字寫
「**write**／delete／widen_scope **皆**寫稽核事件」，
而**同一份檔**的 `:1386`（ADR-0006 表）只寫「`delete` 與 `widen_scope` 皆寫稽核事件」
——**同一份已核可 artifact 內部自相矛盾**。

**由資料庫裁決，不由我選**：

| 依據 | 逐字內容 |
|---|---|
| `schema_rbac.sql:489-490` | `CONSTRAINT ck_memory_audit_events_action CHECK (action IN ('deleted_by_user', 'purged_by_retention', 'scope_changed'))` |
| 可用於「建立」的 action 值 | **不存在** |
| `FR4.7`（`requirements.md:170`） | 逐字只約束「記憶的**刪除動作本身**應留下稽核紀錄」 |

故 `write` 寫稽核在資料庫層**不可能成立**（違反 CHECK → 整個交易中止）。
本站採 `:1386`，並在 `rules.md` 明記此矛盾與裁決依據。
**若硬要讓 `write` 留稽核，必須改 `ck_memory_audit_events_action`**，
那會觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步——不在本單元範圍。

### 〇之二、另一項不一致（記錄，不改上游）

`components.md:206` 給 `MemoryStore` 的 `depends_on` 是 `[]`，
而同一個元件的 `behaviour`（`:189`）逐字「向量由 EmbeddingPort 產生」、
`responsibilities`（`:203`）列「經 EmbeddingPort 取得向量」、
unit DAG 亦有 `U8` → `U6 embedding-port` 的邊。
本站以 unit DAG 與 behaviour 為準，不回改已核可的 `components.md`。

---

## 一、`[FD1]` 誰呼叫 `MemoryFacade.write`？（`OQ-N3`，Critical）

### 這一題是上游明文指派給本站的

`contract-summary.md:1432` 逐字把 `OQ-N3` 的實務落點指向
`functional-design`（3.1），並逐字警告：
**「本站不以推論指派……自行加一條就是審查 R-01／R-07／R-10 的同型錯誤第四次」**。

### 查證到的機械事實

| 查證項 | 結果 |
|---|---|
| `MemoryFacade.write` 的 `consumed_by` | **不存在**（該方法名在 `contract-summary.md` 只出現一次，就是它自己的宣告） |
| `K-08` 的 HTTP 半邊 | 只有 `GET /records`、`DELETE /records/{memoryId}`、`PUT /records/{memoryId}/scope`、`GET /audit-events`——**無建立路徑** |
| 唯一的同進程消費端 `U11 intent-router` | 依 `K-10` 自己的契約是**唯讀**（唯一方法 `classify`） |
| `U13 brain-gateway` 的 `depends_on` | `[brain-ws-contract, intent-router, work-orchestrator, session-store]`——**無 `→ U8`** |
| `US4.1` 的三條 AC | `stories.md` 自己記載其 Given「**無法構造**」，並指派 `domain-design`——**而該站已執行且未解決** |

### 後果（為什麼它是 Critical）

無寫入端則 `memory_records` 永不被填：`MemoryFacade.search` 永遠回空、
`U15` 的三區永遠空白、`U9` 剛交付的 90 天清除**沒有東西可清**。
`FR4.1`／`FR4.5`／`FR4.6`／`FR4.7` 四條全部失去機制，
受阻單元為 `U5`、`U8`、`U9`、`U15`。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **`U13 brain-gateway` 每輪對話結束時寫一筆 episodic 記憶**；semantic／procedure 本輪**不設自動寫入端**，改由新增 `POST /api/memory/records` 讓使用者在 `U15` 手動建立 | 讓 `US4.1`「不用每次從頭交代」真的成立——episodic 自動累積是該故事的本意。代價：**新增一條 `U13 → U8` 的邊**（`contract-summary.md:1432` 逐字要求「該邊必須送到 `delivery-planning`（2.9，ALWAYS）」，否則 2.9 排出的 Bolt 序缺這條約束）＋ 一條新 HTTP 建立路徑（觸發 OpenAPI drift 閘門，須重 dump `openapi.json`）。semantic／procedure 仍無自動寫入端，但**不再是惰性的**（有手動路徑） |
| **B** | `U12 work-orchestrator` 在工作項完成時寫 procedure 記憶，`U13` 寫 episodic，semantic 不設寫入端 | 覆蓋面比 A 大（procedure 自動化），但**新增兩條邊**（`U12 → U8` ＋ `U13 → U8`），兩者都要送 2.9；且 `U12` 的契約目前是「編排與呼叫既有能力」，寫記憶是新責任，會擴大該單元 |
| **C** | **只新增 `POST /api/memory/records`**，三種記憶全部由使用者手動建立，**零新同進程邊** | 改動最小、不動任何單元的依賴圖。但 **`US4.1` 的核心價值落空**——「系統跨對話記得」變成「使用者自己記下來」，而該故事的 persona 需求逐字是「我不用每次從頭交代背景」 |
| **D** | **與 `OQ-N1` 併案**：等「產生自然語言回覆」的落點定了，由同一個單元一併寫記憶 | `contract-summary.md:1478`（`J-14`）逐字說兩者「**很可能是同一個答案**」，故併案有依據。代價：本站不定案，`U8` 的 `write` 保留無呼叫者，上述四個單元的惰性風險**原樣帶到下游**，且 `OQ-N1` 本身也只指派到 `functional-design`／`code-generation`——可能兩站都不解決 |

[Answer]: B U12 寫 procedure ＋ U13 寫 episodic
<!-- 作答時間 2026-10-08T13:44:57Z，以 `date -u` 取值 -->

---

## 二、`[FD2]` 誰可以讀稽核事件？（`AC4.3.3` 要求一條拒絕路徑，而規則不存在）

### 查證到的缺口

`AC4.3.3` 逐字：「**Given** 我不具備稽核紀錄的檢視權限，**When** 我嘗試取得，
**Then** 我被拒絕，且拒絕走既有的授權路徑」。

| 查證項 | 結果 |
|---|---|
| `K-08` 為 `widen_scope` 指定的授權 | `僅 Platform_Admin 與 Platform_Owner` |
| `K-08` 為 `list_audit_events` 指定的授權 | **只寫 `raises: [MemoryForbidden]`，未定誰可通過** |
| `US4.3` 的 persona | 管理者／平台維運者 `[P-4]` |
| `K-08` 的路由註記 | 逐字「`/memory` 走 ProtectedRoute 但**不包** CapabilityRoute……故不需新 story id」——但那條查證是針對**記憶列的擁有者模型**，未涵蓋稽核查詢面 |

**沒有這條規則，`AC4.3.3` 不可實作**：facade 不知道該拒誰。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **僅 `Platform_Admin`／`Platform_Owner`**，與 `widen_scope` 同一組角色；不通過者 `MemoryForbidden(reason="scope")` → 403 | 與 `US4.3` 的 persona（`P-4` 管理者／平台維運者）一致；與 `widen_scope` 用同一組角色，facade 內只有一份角色判定，不新增第二套語彙。**零 schema 變更、零新 story id**，`K-08` 的「不需新 story id」結論維持成立 |
| **B** | 擁有者可看**自己**記憶的事件 ＋ `Platform_Admin`／`Owner` 看全部 | 對使用者更有用（能看自己的記憶被誰放寬過）。但 `US4.3` 只要求管理者那一面，這是**本站自行擴大範圍**；且它讓同一個端點有兩種過濾語意（全量 vs 自己的），`AC4.3.3` 的「被拒絕」在擁有者身上變成「回空集合」——那是兩種不同的可觀察結果，需要再一條 AC 才驗得出來 |
| **C** | 新增一個 story id 走 `require_story_action` | 與 repo 其餘 RBAC 一致。但**直接推翻 `K-08` 已查證的「不需新 story id」**，且新增 story id 會觸發 `schema_rbac.sql`（`role_permissions` seed）＋ `DEPLOY.md` 的 **blocking** 同步，並需 allow/deny 雙向 TestClient（`team.md` 的 A 規則） |

[Answer]: A 僅 Platform_Admin / Platform_Owner
<!-- 作答時間 2026-10-08T13:44:57Z，以 `date -u` 取值 -->

---

## 三、`[FD3]` `visibilityScope` 的合法值集合是什麼？

### 查證到的缺口

`visibility_scope VARCHAR(32) NOT NULL`（`schema_rbac.sql:445`），
**沒有 CHECK 約束**；`previous_scope`／`new_scope` 同樣無 CHECK。
上游只說「預設最窄（僅擁有者可見）」與「放寬是一個獨立的、需授權的操作」,
**從未列出那個集合**。而 `entities.md` 的 `allowed_values` 與 `rules.md` 的
放寬規則都需要它。

**關鍵的實作約束（已查證）**：`memory_records` 的九個欄位是
`id`／`kind`／`owner_user_id`／`visibility_scope`／`content`／`embedding`／
`embedding_model`／`created_at`／`expires_at`——**沒有任何專案或系統的參照欄位**。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **兩值封閉集合：`owner`（預設、最窄）與 `platform`（放寬後全平台可見）** | 與上游逐字一致——「預設最窄」＋「放寬是**一個**操作」，兩值正好是一條放寬路徑的兩端。零 schema 變更（以應用層封閉列舉承載，同 `U18` 的 `ProjectRole` 形狀——`infrastructure-specification.md` 已有「ORM 不得加 CheckConstraint」的先例）。`AC4.3.1` 的「由什麼範圍改成什麼範圍」有確定的兩個值可斷言 |
| **B** | 三值：`owner`／`project`／`platform` | 表達力更強。**但 `project` 不可實作**：`memory_records` 上沒有專案參照欄位，一列記憶無法知道自己屬於哪個專案——要支援它必須加欄位，觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，而那是 `U5` 的資料模型範圍、不是本單元的 |
| **C** | 不設封閉集合，接受任意字串 | 零設計成本。但 `project.md` 已記過同型教訓（`previous_role`／`new_role` 刻意無 CHECK 是因為它們的值集合**當時是未決問題**，而這裡不是）；且開放字串讓「放寬」失去可判定的方向性——無法回答「`a` 比 `b` 寬嗎」，`widen_scope` 的授權判定與 `AC4.3.1` 的斷言都失去依據 |

[Answer]: A owner / platform 兩值
<!-- 作答時間 2026-10-08T13:44:57Z，以 `date -u` 取值 -->

---

## 四、`[FD4]` 追問：`[FD1]`=B 讓 `AC4.1.3` 的 Given 對 semantic 不可構造

### 為什麼加問這一題

`project.md` 逐字要求：「當使用者選的選項會製造新的正確性問題時，說出具體理由
並請其重選，不得照單全收；理由須**指名會壞掉的是什麼**」。

`[FD1]`=B 給了 procedure（`U12` 於工作項完成時寫）與 episodic（`U13` 每輪對話寫）
各自的自動寫入端，**但 semantic 完全沒有任何寫入端**——沒有自動的，也沒有手動的
（選項 A 原本以新增 `POST /api/memory/records` 承載這一塊，B 沒有）。

### 會壞掉的是哪一條

`AC4.1.3` 逐字：
**Given** 三種記憶（語意／程序／情節）**各有資料**，**When** 系統組裝脈絡，
**Then** 三者皆可被取得，不是只有其中一種 `[FR4.1]`

| 事實 | 後果 |
|---|---|
| `semantic` 無任何寫入端 | `memory_records` 永遠不會有 `kind = 'semantic'` 的列 |
| 故 `AC4.1.3` 的 Given「三種記憶各有資料」 | **對 semantic 那一份不可構造** |

這正是 `stories.md` 自己為 `US4.1` 記載過的缺陷類型（逐字「**無法構造**」），
也是 `project.md` 列為零容忍的那一類（「不可構造的 Given」）。
`FR4.1` 逐字要求「系統應提供**三種**記憶」，而 B 之下只有兩種會有資料。

### 選項

| 選項 | 做法 | 代價 |
|---|---|---|
| **A（建議）** | **B ＋ 新增 `POST /api/memory/records`**：procedure 與 episodic 維持 `[FD1]`=B 的自動寫入端不變，另補一條手動建立路徑讓 semantic（以及任何需要人工補的記憶）有寫入端 | `AC4.1.3` 三種皆可構造，`FR4.1` 的「三種」成立。代價：一條新 HTTP 端點（觸發 OpenAPI drift 閘門，須重 dump `openapi.json` 與前端型別）＋ 該端點需 `TestClient` 測試（`team.md` 的 B 規則）。**兩條新邊（`U12 → U8`、`U13 → U8`）不變**，仍須送 `delivery-planning` |
| **B** | **維持 `[FD1]`=B 原樣**，semantic 本輪確實沒有寫入端 | 零額外成本。但 `AC4.1.3` 必須在本站被明確標為**部分不可滿足**（semantic 那一份），並列為新開放項帶到下游；`U15` 的三區會有一區永遠空白，而那與「功能壞了」在畫面上長得一樣 |
| **C** | **維持 `[FD1]`=B，並把 semantic 從本輪範圍移除**：改寫 `AC4.1.3` 為只涵蓋 procedure 與 episodic | 誠實且不留假覆蓋。但它**推翻已核可的 `FR4.1`**（逐字「三種記憶」）與 `AC4.1.3` 的文字，屬 scope 變更，依 `project.md` 須回 `scope-definition` 以 Modify 模式處理並重走核可關卡 |

[Answer]: A B ＋ 新增 POST 端點
<!-- 作答時間 2026-10-08T22:51:13Z，以 `date -u` 取值 -->
