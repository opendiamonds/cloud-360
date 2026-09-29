# Architecture Decision Records — 統一入口大腦（Domain Design）

<!-- Stage: domain-design（Inception 2.6）· Record: 260920-orchestration-brain
     格式依 phases/inception.md 的要求：Context／Decision／Consequences／
     Alternatives Rejected 四段缺一不可。 -->

## 讀法

`components.md` 的 Rationale 表是**每個元件為什麼獨立**的快速理由；本檔是本站
**重大設計選擇**的決策紀錄。編號 `ADR-001` 起，**本檔的編號自成一組**，與
`<record>/inception/decisions/` 下的 repo 級 ADR（ADR-0001…ADR-0018，四位數）
不同序列——兩者不可互相引用編號。

九個 ADR 對應本站九題（`[DD:E1]`–`[DD:E9]`）中有實質取捨的部分；`E3`、`E5`
併入相關 ADR。

---

## ADR-001：大腦切為六個元件

### Context

`[RA]` 的 10 個 FR 群組必須落到「我們要寫程式」的建構塊上。本 repo 是
**modular monolith**（單一 FastAPI 行程、7 個 router、單一 `DATABASE_URL`、
單 worker），故切分的目的不是部署獨立性，而是**變更理由的分離**——
`architecture-guide.md` 的判準：「若兩個元件總是一起部署、或總是一起改，它們是同一個元件」。

本 intent 的變更理由確實分散：路由層模型尚未定案（`OQ-4`／`OQ-10` 指派
`nfr-requirements`）、記憶層要一個全 repo 零前例的獨立 schema
（`[kb:architecture]` 約束七）、session 要外部化到 Redis（`[RA:NFR4]`）、
WebSocket 契約完全沒有機械閘門（約束二）、而階層要碰既有的 `user_diagrams` 表。

### Decision

切為六個元件：`BrainGateway`、`IntentRouter`、`SessionContext`、
`WorkOrchestrator`、`MemoryStore`、`ProjectHierarchy`。逐一的責任、依賴與實體
歸屬見 `components.md` 的 Part A。

### Consequences

**正面**：每個元件恰好對應一組獨立的變更理由——換路由層模型只動
`IntentRouter`；既有 A1／A3／C1 的契約改變只動 `WorkOrchestrator`；WebSocket
協定改變只動 `BrainGateway`。`MemoryStore` 與 `ProjectHierarchy` 是兩個
`depends_on: []` 的葉節點，可平行開工。依賴圖無環（DFS 實測）。

**負面**：六個元件對一個單體行程來說偏多，跨元件呼叫在同一個行程內只是函式呼叫
——**邊界靠紀律維持，沒有任何機械閘門阻止 `BrainGateway` 直接讀 Redis**。
本 repo 已有兩支 import 邊界 validator（`validate_cost_calculator_boundary.py`、
`validate_pricing_lookup_boundary.py`，`[kb:architecture]` 約束十），若要讓這六個
邊界可執行，需要第三支同型腳本——本站**不**要求它，列為觀察項。

### Alternatives Rejected

- **三個粗粒度**（`BrainCore` 全包路由＋編排＋session＋gateway）：拒絕理由是
  `BrainCore` 內部會同時裝協定層、狀態機與 LLM 呼叫，而這三件事的**測試方式與
  失敗模式完全不同**（協定層要 `websocket_connect`、狀態機是純邏輯、LLM 呼叫要替身）。
  `units-generation:c6` 的判準逐字為「工作單元的切分判準是驗證方式與失敗模式是否
  同類」——併入同一個元件會讓「這個元件完成了嗎」同時指涉三種不可互相替代的判準。
- **八個細粒度**（再拆 `CapabilityAdapter` 與 `ClarifyResolver`）：拒絕理由是這兩者
  都**沒有自己的實體、也沒有自己的變更理由**——`CapabilityAdapter` 與
  `WorkOrchestrator` 必然一起改（交辦與轉譯是同一件事的兩面），`ClarifyResolver`
  與 `IntentRouter` 同理（信心不足就產候選，是同一個判定的兩個出口）。
  `architecture-guide.md` 明列「只是 pass-through proxy 的元件」為邊界錯誤的紅旗。
- **兩個元件**（`Brain` ＋ `ProjectHierarchy`）：拒絕理由同三個粗粒度，程度更重
  ——`Brain` 會同時擁有記憶 schema、Redis session 與 WS 協定，審查時說不出它的責任是什麼。

---

## ADR-002：`user_diagrams.user_id` 保留，新增 nullable `system_id`

### Context

`[實測]`：`user_diagrams.user_id` 是 `nullable=False` 的 FK 指向 `users.id`，
且 `[kb:component-inventory]` 指出這是全 repo **唯一**的擁有關係。要插入
「專案 → 系統 → 架構圖」中介層，這個欄位的去向不可迴避，而 `[RA:FR9.2]`
只說「應能遷入新階層」，沒說怎麼接。

關鍵約束來自 `[kb:architecture]` 約束六：既有 staging 環境的**唯一** schema
演進路徑是 `backend/database.py` 的 6 支 `_ensure_*` 補丁，而它們
**全部以 `except Exception as e: logger.warning(...)` 吞掉失敗**
（`:204–209`、`:251–256`、`:321–326`、`:493–500`、`:519–526`）。

### Decision

保留 `user_id`（語意為「誰建的」），新增 nullable 的 `system_id`（語意為
「屬於哪個系統」），並**明訂 `system_id` 為歸屬的權威來源**。

### Consequences

**正面**：既有程式碼零改動、可回復（回復方式為清空 `system_id` 並刪除新建的
`projects`／`systems` 列）。`[US:AC9.1.3]`「遷移不改變既有頁面的使用方式」
因此結構上成立而非靠小心。

**負面**：擁有語意有兩個來源，而**只有本 ADR 這句話決定誰是權威**——沒有任何
機械機制阻止下游程式從 `user_id` 推導歸屬。這是一個必須靠文件維持的約束，
故在此明寫，並在 `components.md` 的 `ProjectHierarchy.behaviour` 重述一次。

**另一個未關閉的面**：本 ADR 把 `system_id` 立為權威，但**刪除 `System` 時它會懸空**
——那等於那張圖失去歸屬。這是本站自檢 2 查出的缺口 **DG-2**，見 `components.md`
的「契約端點三問的結果」與交接事項 H-7。本 ADR 不定案 cascade 行為。

### Alternatives Rejected

- **改指（移除 `user_id`，擁有者經 `systems → projects` 上溯）**：語意最乾淨，
  但需 backfill 全部既有列，而執行 backfill 的機制會**靜默吞掉失敗**（上述約束六）。
  一個不可逆的改動 ＋ 一個會靜默失敗的執行路徑，是本 repo 反覆受害的組合。
- **保留但標 deprecated**（新圖只寫 `system_id`、舊圖只有 `user_id`）：拒絕理由是
  每一個讀取點都會永遠有兩條分支，而「何時可以拒掉舊分支」沒有任何人會決定——
  `project.md` 的 `functional-design:c10` 警告的正是這種「文件上像已解決、實際是
  永久技術債」的形狀。

---

## ADR-003：遷移為「每人一個預設專案 ＋ 預設系統」

### Context

`[RA:FR9.3]` 把遷移的歸屬規則、步驟與回復方式指派給本站。
`[US:AC9.1.4]` 逐字要求：遷移後架構圖表中 `system_id IS NULL` 的列數必須為
**0**，**若不為 0，遷移程序必須大聲失敗**，不得以警告帶過。
既有的分享機制是 `diagram_shares` 多對多（`user_id` ＋ `diagram_id` 皆為 PK）。

### Decision

為每個持有架構圖的使用者建立「<使用者>的專案／預設系統」，其現有圖全部掛入。
使用者之後可改名、可搬移。回復方式：清空 `system_id` 並刪除新建的
`projects`／`systems` 列。

### Consequences

**正面**：每張圖的歸屬與其**現行擁有者一致**，不改變任何既有可見性。
`AC9.1.4` 的不變量在**遷移當下**可滿足（每張圖都有歸屬）。

**但該不變量在執行期可被打破**：遷移後若有人刪掉一個 `System`，其下架構圖的
`system_id` 會懸空，`AC9.1.4` 要求計數為 0 的條件即不再成立。這是缺口 **DG-2**
（見 `components.md` 的「契約端點三問的結果」），本 ADR 只保證遷移程序本身，
不保證遷移之後的維持。

**負面**：使用者數量決定新建列數，遷移後專案清單會有一批自動命名的項目。
且 `diagram_shares` 的被分享者在新階層下**看得到那張圖但不擁有它所屬的專案**
——本站不改變 `diagram_shares` 的行為，故被分享者的可見性維持既有規則，
但「他在專案清單裡看不到那個專案卻看得到裡面的圖」是一個新的呈現落差，
列為 `units-generation` 的注意事項。

### Alternatives Rejected

- **單一全域「未分類」專案**：拒絕理由是 `diagram_shares` 的多對多會讓不同使用者
  的圖混在同一個專案下，而專案層的可見性尚未定義——這會製造一個沒人決定過的
  可見性語意。
- **不自動遷移**（`system_id` 留 `NULL`）：**直接違反已核可的 `AC9.1.4`**
  （該 AC 要求 `NULL` 計數為 0 且不為 0 時須大聲失敗）。選它等於讓一條已核可的
  AC 永遠不可滿足。

---

## ADR-004：新增 story id `K1`（統一入口頁）與 `K2`（專案／系統階層）

### Context

`[RA:FR1.8]` 要求入口頁有自己的 story id 並置於 `DefaultRedirect` 瀑布之首；
`[RA:FR9.5]` 要求 `projects`／`systems` 的讀寫刪一律經 `require_story_action`。
`[DM:D1]`=C 已定案 `/memory` **不需要** story id（`App.tsx:38–41` 的
`/waiting-approval` 是 `ProtectedRoute` 單獨使用的前例，且記憶由擁有者欄位把關）。

`[實測]`：`DEFAULT_ROLE_PERMISSIONS` 為 **308 列＝11 角色 × 28 個 story id**，
五元組形狀 `(role, story_id, view, edit, review)`；已用字首 **A–H、J**，**K 起全空**。

### Decision

新增兩個 story id：`K1`（統一入口頁）、`K2`（專案／系統階層）。
`K` 為全新字首，與既有 A（架構）／C（成本）／J（管理）語意不重疊。
新增後矩陣為 11 × 30 ＝ **330 列**（實算：308 + 11 × 2）。

### Consequences

**正面**：「能進入口頁」與「能改階層」是兩個獨立開關。新字首讓大腦這個功能域
在權限矩陣上一眼可辨。

**負面**：觸發兩條 blocking 規則——`team.md` 的 allow/deny 雙向 TestClient 測試，
與 `project.md` 的 `schema_rbac.sql` ＋ `DEPLOY.md` 同步。且**不可依賴
`ensure_role_permissions_seeded(force=False)`**：`[kb:component-inventory]` 記載
該函式在表非空時整段 no-op（`rbac.py:63–65`），必須走
`ensure_missing_role_permissions`（`:84–111`，只 INSERT 缺失列）。
各角色的 22 列預設值本站未定，見 `components.md` 的 Assumptions。

### Alternatives Rejected

- **併入 A 字首**（`A5`／`A6`）：拒絕理由是 `canArch()` 這類既有 helper 的語意會
  變模糊——「統一入口」不是架構功能，它是所有功能的入口。
- **單一 `K1` 涵蓋全部**：拒絕理由是「能進入口頁」與「能刪別人的專案」會變成
  同一個開關，而前者應該幾乎人人都有、後者應該很少人有。
- **三個 id**（專案與系統分開）：拒絕理由是想不出「能建系統卻不能建專案」的實際
  情境；多一個 id 就多 11 列而無對應的授權需求。

---

## ADR-005：session 的存活期以「單一 key ＋ TTL 續期」承載

### Context

`[RA:NFR4]` 定案 session 放 Redis、重啟後脈絡可還原，但**誰清、何時清沒有定義**
——這是 requirements-analysis 自己的契約端點自檢查出的缺口（`OQ-9`）。
refined-mockups 的自檢又查出兩個同源缺口：工作項集合無人清除（**G-1**）、
作業對象無人清回「未選定」（**G-2**，使該狀態只在首次使用可達）。
三者是同一個問題的三個面。

### Decision

作業對象、共享／獨立狀態、工作項集合**全部放在同一個 Redis key 之下**，
TTL 24 小時、每次互動續期。TTL 到期三者一起消失，下次進入即為全新 session
且作業對象回到未選定。

### Consequences

**正面**：一個機制同時關掉 `OQ-9`、`G-1`、`G-2` 三個缺口。`no-object` 狀態因此
**真的可達**（不只首次使用），`ContextBar` 宣告的該狀態不再是死碼。

**負面**：使用者隔天回來會失去脈絡。這是「還原」的邊界被明確劃在 24 小時——
`[RA:NFR4]` 的可測不變量是「**重啟 backend 後**脈絡可還原」，而重啟遠短於 24 小時，
故本決定不違反該不變量。但它確實讓「跨日延續」成為一個未被承諾的行為。

### Alternatives Rejected

- **顯式清除、無 TTL**：拒絕理由是 `no-object` 仍然不可達（沒有任何事件會清作業
  對象），且從不登出的使用者其 key 無限成長。它沒有解掉 G-2。
- **TTL ＋ 顯式清除並存**：兩條清除路徑就是兩個要測的失敗模式，而 TTL 已足夠。
- **分成兩個 key**（作業對象長 TTL、工作項短 TTL）：拒絕理由是會出現「常駐區空了
  但脈絡列還在」的中間態，而 `[DM:D4]`=C 的兩個視圖共用同一份狀態的前提就不成立了。

---

## ADR-006：記憶可見範圍的放寬僅限 `Platform_Admin` 與 `Platform_Owner`

### Context

`[RA:FR4.3b]` 定案可見範圍預設最窄（僅擁有者可見），**放寬是一個獨立的、需授權的
操作，且每次變更須留稽核紀錄**（誰、何時、由什麼範圍改為什麼範圍）。
上游把「哪些角色」指派給本站（`OQ-12`）。

### Decision

僅 `Platform_Admin` 與 `Platform_Owner` 得放寬記憶列的可見範圍。
擁有者本人**不能**自行放寬。

### Consequences

**正面**：最窄。記憶是大腦對使用者的推論（偏好、慣用說法、過往對話），
使用者未必知道裡面有什麼——讓他在不完全知情的狀態下放寬，風險高於收益。
從窄放寬比從寬收緊安全。

**負面**：使用者無法主動分享自己的記憶（例如讓同組看見「這個專案的慣用命名」），
該需求若真實存在，要走平台管理者。這是刻意的摩擦。

### Alternatives Rejected

- **擁有者自己 ＋ 兩個平台角色**：拒絕理由見上（使用者未必知道記憶內容）。
- **只有擁有者自己**：拒絕理由是管理者就沒有任何路徑能處理誤放寬的列。
- **本版誰都不能**：拒絕理由是 `[RA:FR4.3b]` 已核可「放寬為一個獨立的、需授權的
  操作」——選它等於讓那句話在本版無實作，而該 FR 是已核可的。

---

## ADR-007：語意記憶採 pgvector，向量由本機 Ollama（bge-m3）產生

### Context

`OQ-2` 把「語意記憶是否採向量檢索」指派給本站。`[實測]`：本 repo
**零向量前例**（`pgvector`／`embedding`／`vector(` 在全 `backend/` 命中 0）、
DB image 為 `postgres:16-alpine`（不含 pgvector）、測試走 in-memory SQLite。

本題經三輪收斂（過程逐字記於問題檔的 `[DD:E7]` 註解）。使用者初選 pgvector，
我依 `project.md` 的規則具名指出兩項後果（兩個 compose 的 image 都要換、
embedding 是一條新的 LLM 路徑且落在 repo 已知盲區又無花費計量）；
使用者要求「用 pgvector 但找不用錢的方案」並追問 OpenRouter 有無免費模型。

**查證結果**：OpenRouter **沒有 embeddings 端點**——其 API reference 只有
`POST /api/v1/chat/completions` 與 `GET /api/v1/generation`，該頁與 FAQ 兩處對
"embedding" 零提及。故其 `:free` 模型是對話模型，產不出向量。這是技術上不通，
不是價格問題。

### Decision

採 pgvector；向量由**本機運算**產生，staging 以 Ollama 跑 bge-m3
（dense 1024 維、多語 100+ 語言，皆已查證）。零 API 費用。

### Consequences

**正面**：語意檢索品質遠優於全文比對，且 embedding 在本機算，故
`[F13]`=A 的「不做自身 LLM 花費計量」不再構成問題（沒有 API 費用要計量）。

**負面**（全部列入回補項 **N-11**）：
- DB image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`（Debian 基底），
  **deploy 與 test 兩個 compose 都要改**。PG 大版本相同故 `cloud360_db` volume 相容。
- Ollama 是**第 6 個服務**（Redis 第 5），觸發 env contract 的 blocking 規則。
- 新增模型快取 volume（bge-m3 約 1.2GB）、Ollama RAM 約 2GB，而
  **staging 主機的餘裕在 `DEPLOY.md`／`LOCAL-DEV.md` 皆無記載、本站未查證**。
- embedding 仍是一條 LLM 路徑，落在 repo 三塊結構性盲區之一。
- **衍生的硬約束**：`ui-regression` 每個 PR 起的短生命週期 stack 不可能拉 1.2GB
  模型，故 `MemoryStore` 必須以 `EmbeddingPort` 對外並提供決定性替身。見 ADR-008。

### Alternatives Rejected

- **PostgreSQL 全文檢索 ＋ 標籤**（本站原建議）：使用者曾一度選它又改回 pgvector。
  拒絕理由為檢索品質；其代價（零新基礎設施）已在選項中揭露。
- **別家的免費額度（如 Gemini `text-embedding-004`）**：拒絕理由是第二個 LLM 憑證
  要進一個 **public** repo，而 `project.md` 有一條規則專門講這件事（新增 secret 後
  須實地查證它落在 secrets 而非 variables，因 Actions log 公開可讀）；另有速率限制。
- **OpenRouter 的免費模型**：**技術上不可行**（無 embeddings 端點，已查證）。

---

## ADR-008：`EmbeddingPort` 四個實作，由設定切換，且不可用時大聲失敗

### Context

ADR-007 定案 staging 用 Ollama，但本機開發未必有它（使用者指出此需求）。
`[實測]`：**fastembed 不支援 bge-m3**，但支援 `intfloat/multilingual-e5-large`
（**1024** 維、多語）——與 bge-m3 **同維度**，故 pgvector 欄位可共用 `vector(1024)`。

**關鍵風險**：同維度**不等於**同向量空間。兩個模型各自的向量不可互相比較；
若本機寫 e5-large 的向量、staging 寫 bge-m3 的向量到同一 schema，
相似度檢索會回垃圾**而且不會報錯**。

### Decision

`MemoryStore` 以 `EmbeddingPort` 對外，四個實作由設定切換：
`ollama`（bge-m3，staging）、`fastembed`（multilingual-e5-large，本機無 Ollama 時）、
`fulltext`（不算向量，退回 PostgreSQL 全文檢索）、`stub`（決定性替身，CI 用）。
向量欄位為 `vector(1024)`。**每列記憶存 `embeddingModel`，相似度檢索只比對同一
`embeddingModel` 的列。**

**偵測不到選定的提供者時必須大聲失敗並列出可選值，不得靜默降級為全文檢索**
——這一條是**本站自行加上的約束**，不是使用者的定案。理由：向量與全文的檢索結果
差異大，靜默切換會讓「為什麼找不到我的記憶」變成無法除錯的問題；
`phases/construction.md` 明文要求「Errors must be surfaced」，而 `project.md`
反覆記載靜默失敗是本 repo 的主要受害形式（實例：`N8N_USER`／`N8N_PASSWORD`
從未被寫入，導致每次部署的架構圖 icons 靜默退回灰底佔位圖）。

### Consequences

**正面**：跨模型的不相容變成**結構上不可能靜默出錯**，而不是靠紀律避免。
`ui-regression` 的短生命週期 stack 用 `stub` 即可運行，不需拉模型。
本機開發者可依機器狀況三選一。

**負面**：`fulltext` 模式下建立的列其向量為 `NULL`，之後**不會被向量檢索看到**，
除非重新 embed——此事必須寫進 `LOCAL-DEV.md`，否則本機切換過模式的開發者會
遇到「舊記憶查不到」而無從理解。新增 `.env.example` 變數連帶觸發
`project.md` 的 blocking 規則（異動任一 `.env.example` 須同步更新 `LOCAL-DEV.md`）。

### Alternatives Rejected

- **兩邊都用同一個模型（本機也跑 Ollama）**：向量完全可互換、不需 `embeddingModel`
  欄位，但 `LOCAL-DEV.md` 的隱性硬依賴會從 2 個（`claude` CLI、n8n webhook）
  變成 3 個，且每位開發者本機都要拉 1.2GB 模型。使用者明確要求本機可不裝 Ollama。
- **本機一律退回全文檢索**：拒絕理由是本機就驗不到向量檢索路徑，而那正是最需要
  在本機試的東西；使用者亦明確要求保留 fastembed 這條路。

---

## ADR-009：「需求」不建為實體，改以架構圖變更紀錄的摘要與輕量標籤承載

### Context

使用者在 `[DD:E2]` 的回覆重新框定了階層：「一個專案，多個需求。一個需求有可能
影響多個系統……需求不用被完整紀錄，只要讓架構圖在被異動時被紀錄，因為什麼需求
被異動，紀錄內容只要是摘要即可」。

依 `project.md` 的 `application-design:260822-ad-L3`（重新框定須先查證是否等價）
與 `approval-handoff:e2923632`（推翻上游定案時須先界定反轉範圍、不得由 AI 逕自
吸收），本站先查證：

| 成分 | 是否為新 | 逐字證據 |
|---|---|---|
| 一個系統一份 drawio 架構圖、一份架構圖多個 tab | **不是新的** | `[RA:FR9.1]` 逐字「一個專案有多個系統、一個系統對應**一份架構圖檔與其中多張圖**」 |
| 專案 1:N 需求、需求 N:M 系統 | **是新的** | `scope-document.md:60` 能力 9 逐字只有「專案 → 系統 → 架構圖 階層」；`stories.md` `AC9.1.1` 逐字「**三層**路徑」；`models.py` 對 `Requirement` 命中 **0** |
| 架構圖異動時記錄來源需求摘要 | **是新的且需要新表** | `[實測]`：13 個模型**無任何變更歷程表**，`UserDiagram` 只有會被覆寫的 `updated_at` |

### Decision

不建 `Requirement` 實體、不建需求↔系統的多對多關聯表。新增
`DiagramChangeRecord`：架構圖每次被異動時寫一列，帶 `requirementSummary`
（自由文字摘要）與 `requirementLabel`（輕量標籤）。

### Consequences

**正面**：三層階層維持不變，故 `[RA:FR9.1]`、`[US:AC9.1.1]`、線框 §3、
`mockups.md` M4 **全部仍然成立，不需要修訂任何已核可產出**。
最貼合使用者自己說的「需求不用被完整紀錄、摘要即可」。

**負面**：輕量標籤可溯源但**不保證一致**——打錯字就是另一個需求，沒有任何機制
會發現。且本站為這張表寫了寫入端卻**沒有指名讀取端**（缺口 **DG-3**）——
使用者定案此選項的理由逐字是「可用同一標籤搜尋它影響過哪些圖」，那句話描述的
就是一個讀取端，而它在本站產出中不存在。本 repo 已有同型前例
（`estimate_audit_events` 只寫不讀）。這個代價已在提問時的選項說明中揭露。新增一張表列為回補項 **N-10**，
並觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步（本 intent 已因
`projects`／`systems` 觸發同一條規則，故邊際成本低）。

### Alternatives Rejected

- **建成第四個完整實體**（`requirements` 表 ＋ 多對多關聯表）：可查詢「這個需求
  影響哪些系統」，但會動到 **5 份已核可產出**（`scope-document.md` 能力 9 的定義、
  `requirements.md` FR9.1／FR9.5、`stories.md` `AC9.1.1` 的「三層」、線框 §3 的
  脈絡列三欄、`mockups.md` M4 的選單分組），且需先裁決「就地修訂 vs 重跑那四站」。
  使用者選了較輕的 C，故此路未走。
- **只做摘要、不做標籤**：無法回答「這個需求影響過哪些圖」，而使用者原文明確提到
  「一個需求有可能影響多個系統」——完全不留標籤就失去那個面向。
- **本 intent 不做、只記入文件**：使用者未選此項。
