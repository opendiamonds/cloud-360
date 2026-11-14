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

---

# 修訂 1（2026-10-02T23:11:16Z）— ADR-010 至 ADR-016

既有 `ADR-001`–`ADR-009` **全部有效**。`ADR-009` 未被取代，但其適用範圍由
`ADR-011` 明確界定。

## ADR-010：專案成員管理獨立為 `ProjectMembership` 元件

### Context

能力 12（`FR12.0`–`FR12.6b`）新增成員關係、角色與自動改選。既有 `ProjectHierarchy`
已擁有 `Project`／`System`／`DiagramChangeRecord` 三個實體，把成員加為第四個實體是
表面上最省的做法。

兩個查證過的事實使它不是最省的：① `ddd-patterns.md` 逐字「若兩個概念因**不同理由**
而改變，它們屬於不同的 bounded context」——成員變更的理由（人員進出、授權調整）與
階層變更的理由（新系統、新架構圖）無關。② `ProjectHierarchy.behaviour` 在
domain-design 的上一輪**已因自相矛盾被審查打回**（它寫「不得有任何繞過
`require_story_action` 的路徑，含同進程直呼 service 層」，而同一份機讀目錄自己宣告了
`SessionContext --sync--> ProjectHierarchy` 與 `WorkOrchestrator --sync--> ProjectHierarchy`
兩條 `sync` 入邊——`sync` 就是同進程呼叫）。再給它一個授權職責會讓那段 behaviour
更難寫對。

### Decision

新建 `ProjectMembership` 元件，擁有 `ProjectMember` 與 `ReselectionEvent` 兩個實體，
`depends_on` `ProjectHierarchy`（驗證專案存在、讀 `ownerUserId`）。

### Consequences

**正面**：成員與階層各自有清楚的擁有者；授權判定（`ADR-012`）有一個明確的落點；
`ProjectHierarchy` 的 behaviour 不需再擴寫。

**負面**：多一個元件邊界與一條 `depends_on` 邊；`AC12.1.3`（非成員看不到專案）需要
兩個元件一起判，故兩者的交易邊界必須明訂——**建立專案與寫入建立者的成員資格必須在
同一個交易內**，否則會出現沒有管理者的專案。此約束已寫進 `ProjectMembership.behaviour`。

**2026-10-02T23:28:04Z 補入（`review-02` 的 `R-03`，Major）——本 ADR 漏了一條 blocking 規則**：
`ProjectMembership` 新增 **`project_members`** 與 **`reselection_events`** 兩張表，
而 `project.md ## Mandated` 逐字要求新增表時**必做 1**（`schema_rbac.sql` 同步）與
**必做 2**（`DEPLOY.md` 同步）為 **blocking，未完成不得標示相關階段完成**。
**這不是沒注意到那條規則**——同一份檔案的 `ADR-009` 與 `N-11` 都正確點名了它
（`ADR-009` 逐字「並觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步」），
而本輪新增的表漏套用。兩張表的 DDL 須以 `IF NOT EXISTS` 等可重跑安全寫法寫進
`schema_rbac.sql` 的適當區塊並補 COMMENT；`DEPLOY.md` 的「這支 SQL 會建立的表／
欄位」表須同步，並補建議的 `psql` 驗證指令。見交接 `DG-9`。

### Alternatives Rejected

- **擴充 `ProjectHierarchy`**（`[E11]` 選項 B）：見 Context 的兩項理由。
- **新建但不依賴 `ProjectHierarchy`**（選項 C）：孤兒成員列無人擋，而把關聯完整性
  推給資料庫外鍵等於讓它在應用層不可測。

## ADR-011：兩個「需求」並存且改名，`ADR-009` 的適用範圍就此界定

### Context

**本站查出 `ADR-009` 與能力 11 直接牴觸。** `ADR-009` 的 Decision 逐字為「不建
`Requirement` 實體、不建需求↔系統的多對多關聯表」，改以 `DiagramChangeRecord` 的
`requirementSummary`（自由文字摘要）與 `requirementLabel`（輕量標籤）承載。

而能力 11 要求**結構化的固定欄位**：`[R12]`＝D 逐字否決自由鍵值對（理由是「自由欄位
會讓同一個概念出現多個名字，而畫面無從分辨」），`FR11.2` 要求按 agent 分組的固定
欄位，`FR11.3` 要求未填計數，線框 §17 畫出 SLA／尖峰 TPS／使用客群／月預算上限／
計費區域五個具名欄位。

**關鍵是兩者對「需求」指的不是同一件事**：`ADR-009` 的是**溯源概念**（哪個需求驅動
了這次架構圖變更），能力 11 的是**agent 需要的架構假設**。這是 `ddd-patterns.md`
點名的同名不同義（bounded context 的命名碰撞），也正是 `project.md` 記著的
「會議結論點名的識別字先查證是否已被佔用、既有語意是什麼」。

`ADR-009` 是**使用者在 `[DD:E2]` 重新框定後自己定案的**（逐字「需求不用被完整紀錄，
只要讓架構圖在被異動時被紀錄……紀錄內容只要是摘要即可」），故依 `project.md` 的
`approval-handoff:e2923632`，反轉它須由使用者裁決而不得由 AI 吸收。本站把它出成
`[E12]`。

### Decision

**兩者並存且改名**（`[E12]`＝A）。能力 11 的東西命名為 `SystemRequirementField`，
由新元件 `RequirementRegistry` 擁有（`ADR-009` 的那一組原樣保留在
`DiagramChangeRecord`）。兩處都標註「不要把這兩個『需求』當成同一件事」。

**`ADR-009` 未被取代**；它的適用範圍自此界定為「架構圖變更的來源需求**溯源摘要**」，
不涵蓋 agent 需要的架構假設欄位。

### Consequences

**正面**：`ADR-009` 與使用者在 `[DD:E2]` 的定案**不被推翻**；`[R12]`＝D 的固定欄位
要求得到一個名字不衝突的落點；兩者的基數差異（一次變更可由多個需求驅動 vs 每系統
一組固定欄位）不需要被硬接成多對多關聯表。

**負面**：產品裡有兩個都叫「需求」的東西。實務上**線框已經區分了**（§17 是「需求籤」、
§16 是「最近變更」），但**文件與對話中必須持續用全名**，否則下一個人會把兩者混為
一談。這是真實的持續成本，不是一次性的。

**2026-10-02T23:28:04Z 補入（`review-02` 的 `R-03`）**：`RequirementRegistry` 新增
**`system_requirement_fields`** 一張表，同樣觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的
**blocking** 同步（理由同 `ADR-010` 的補入段）。`ADR-015` 定下的清空語意
（保留列、`value` 為 `null`、`clearedAt` 有值）**必須反映在該表的 DDL 上**——
`value` 須可為 null、`clearedAt` 為獨立欄位，否則「從未填過」與「清空」在資料層
無法區分。見交接 `DG-9`。

**中性**：`SystemRequirementField` 的**擁有元件**（`RequirementRegistry`）是本站的
判定而非使用者的直接選擇——`[E12]` 的選項 C（由 `ProjectHierarchy` 擁有）被否決，
故「不由 `ProjectHierarchy` 擁有」是定案的直接後果；**新元件的名字是我取的**，
若團隊偏好別的名字，改名的成本僅限本站與下游的識別字。

### Alternatives Rejected

- **取代 `ADR-009`**（`[E12]` 選項 B）：推翻使用者自己的定案；且兩者基數不同，硬接
  會製造 `ADR-009` 明文拒絕的多對多關聯表。
- **掛在 `System` 實體上**（選項 C）：會讓 `ProjectHierarchy` 同時擁有階層、變更紀錄
  與 agent 契約三種職責；且欄位集合隨新 agent 上線而變，變更率與 `System` 完全不同。

## ADR-012：per-project 授權判定由 `ProjectMembership` 提供

### Context

`[DM:D9]`＝A 要求成員頁依「我在這個專案的角色」決定控件可見性，不變量 `I-5` 要求
一般成員視角的變更控件**不在 DOM 內**（不是 `disabled`）。既有的 `CapabilityRoute`
管的是**能力層**（story id），表達不了 per-project 判定。refined-mockups 把這個缺口
列為交接 `H-12`。

### Decision

判定方法由 `ProjectMembership` 提供（`[E13]`＝A），消費端以 `depends_on` 取用。
判定結論由**伺服器**產生並交給前端，前端不得自行推導。全域那一層仍由既有的
`require_story_action` 承載，本元件不重新實作它（`FR12.6` 的兩層串聯）。

### Consequences

**正面**：授權規則只有一份；資料與規則不分離。

**負面**：每個消費端多一條 `depends_on` 邊，且**設計上必須禁止繞過**——
`ProjectHierarchy` 上一輪正是在這裡自相矛盾（behaviour 寫「不得同進程直呼」而機讀
目錄自己宣告了 `sync` 入邊）。本 ADR 明記：`ProjectMembership` 的 `sync` 入邊是
**預期且允許**的呼叫方式，禁止的是**跳過它直接讀 `project_members` 表**——這兩件事
不同，而上一輪把它們寫成同一句話。

### Alternatives Rejected

- **獨立 `ProjectAuthorization` 元件**（`[E13]` 選項 B）：一個不擁有資料的元件正是
  `architecture-guide.md` 列為紅旗的 pass-through proxy，且它與 `ProjectMembership`
  會永遠一起改。
- **每個元件自己判**（選項 C）：`FR12.6` 的兩層串聯會在每個元件裡被重寫一次，
  其中任一處寫錯就是一個授權繞過；違反 `team.md` 的「單一真實來源」。

## ADR-013：`McpBridge` 為獨立元件

### Context

`[F16]`＝B 已定案 MCP 跑獨立進程、對外帶使用者 token 呼叫既有 API；
`requirements.md:614` 已定案它**不得對外暴露、僅供同主機**，且它是本 intent 的
**第二個**新增進程邊界（第一個是 Redis）。元件身分是另一件事（元件是「我們寫的
程式」，部署拓樸屬 units-generation）。

### Decision

新建 `McpBridge` 元件（`[E14]`＝A），擁有工具 schema 的宣告與 token 轉遞路徑，
零實體。

### Consequences

**正面**：`C-T11`（token 不得當工具引數）有明確的斷言落點——`AC11.4.2` 的白名單
斷言掛在這個元件上；`BrainGateway` 的 behaviour 不需同時描述兩種認證主體。

**負面**：多一個元件；且它是本站唯一**沒有既有程式可參照**的元件（repo 內零 MCP
基礎設施，`A-7`「MCP 生態可在本 repo 運作」**本輪未實測**）。

### Alternatives Rejected

- **併入 `BrainGateway`**（`[E14]` 選項 B）：認證主體、暴露範圍與失敗模式都不同；
  一個元件承擔兩種不該一起變的理由。
- **記為 `external_dependencies`**（選項 C）：stage 檔逐字只有第三方服務才是
  `external_dependencies`，而 MCP server 是我們要寫的程式。

## ADR-014：`ProgressChannel` 為獨立元件，並由它擁有清除端

### Context

`FR13.1` 要求把 `design_agent.py` 的模組層全域 `_progress_queue` 改為 per-key；
`FR13.2`／`FR13.3` 是其可觀察面。**US13 的 DoD 要求鍵是 per-request，但沒有要求
清除**——這個缺口是我在 refined-mockups 的契約端點三問查出的：只寫不刪會把跨使用者
錯送換成**無上界的記憶體成長**，即修掉一個失敗模式換來另一個。

### Decision

新建 `ProgressChannel` 元件（`[E15]`＝A），擁有 per-request 的進度通道**與其清除端**：
請求結束時必須移除該鍵。零實體（通道是行程內狀態，生命週期短於一次請求）。
對外的錯誤一律為固定訊息，不含例外原文。

**兩處上游引用的更正（2026-10-02T23:13:20Z，本站自檢 3 開檔核對）**：
- US13 的 DoD 與 `stories.md` 寫「形狀沿用 `cost/advice_orchestrator.py:23-24`」——
  **路徑前綴錯了**，真實路徑是 **`backend/cost/advice_orchestrator.py`**（不是
  `backend/services/cost/`）。行號與樣式本身正確：`:23` 為
  `_progress: dict[int, dict[str, Any]] = {}`、`:24` 為 `_progress_lock = threading.Lock()`。
- **但本元件不照抄它的 `threading.Lock`。** 那支檔案用 Lock 是因為它有
  `ThreadPoolExecutor`（`:21` 的 `_executor`），而 `ProgressChannel` 跑在單執行緒的
  asyncio 事件迴圈上——在那裡 `threading.Lock` 是 cargo cult，而且會在 `await` 邊界
  給出錯誤的安全感。這正是 `project.md` 的 `application-design:c15` 要求的：
  **指定「沿用既有機制」之前，先寫下該既有機制的副作用是否與新需求的意圖相容**。

### Consequences

**正面**：「誰清」有了擁有者；`FR13.2` 的互斥斷言有元件可掛；
`FR13.3` 的「內部例外文字外洩」這個獨立的 ADR-0006 面有明確的處置點。

**負面**：既有兩支檔案（`design_agent.py`、`wa_collab_orchestrator.py:79`）都要改動，
而它們在本站的機讀目錄裡是 `external_dependencies` 而非元件——**這個元件的完成條件
因此橫跨新程式與既有程式的改動**，`units-generation` 切單元時要注意這一點。

### Alternatives Rejected

- **修在既有模組內、不成為元件**（`[E15]` 選項 B）：「誰清」仍無人負責，且
  `FR13.2` 的互斥斷言會變成一條沒有元件可掛的斷言。
- **併入 `WorkOrchestrator`**（選項 C）：會讓「這個元件完成了嗎」同時指涉新程式與
  既有程式的改動，而 `WorkOrchestrator` 的既有職責是交辦與狀態事件轉譯。

## ADR-015：需求欄位的清空語意——保留列、值設為 `null`、記 `clearedAt`

### Context

線框 §17 自標出一個缺口並判給本站：「**清除端沒有任何畫面**：一個填過的欄位要怎麼
清空、清空與『從未填過』在畫面上是否可區分、以及 agent 寫錯時使用者如何撤銷」。
refined-mockups 的 M12 進一步要求「從未更新」與「由大腦更新但內容為空」必須可區分，
並把它列為交接 `H-9`。這是本站必須定案的事，不能再往下推。

### Decision

**保留列、`value` 設為 `null`、記 `clearedAt` 與 `updatedBy`。**
- **從未填過** ＝ 該 `(systemId, agentGroup, fieldKey)` **無列**。
- **清空** ＝ 該列存在、`value` 為 `null`、`clearedAt` 有值。
- 未填計數（`FR11.3`）把「無列」與「`value` 為 `null`」**都**算為未填。

### Consequences

**正面**：畫面得以區分兩種狀態（M12 的要求）；清空動作留下誰清、何時清的紀錄，
故 agent 寫錯時使用者能看出是誰寫的、也能清掉它；未填計數的定義是二元可判的。

**負面**：清空後的列不會消失，故表的列數只增不減（每個系統最多為欄位定義數）。
這個上限是有界的，但需要一個「欄位定義被移除後其值列如何處置」的後續決定——
**本 ADR 不處理那件事**，它屬於欄位定義變更（新 agent 上線／下線）的範圍，
指派 `units-generation`（2.7，**ALWAYS**）在切單元時明訂。

**中性**：未採「刪除該列」的做法，代價是多一個 `clearedAt` 欄位；換到的是
「清空」這個動作本身可被稽核。

### Alternatives Rejected

- **刪除該列**：清空與從未填過在資料層變成同一種狀態，M12 的區分要求無法滿足，
  且「誰清」的紀錄會隨列一起消失。
- **以哨兵值表示清空**（如空字串）：空字串與「使用者真的填了空白」無法區分，
  而 `ux-guide.md` 的錯誤預防要求的是讓錯誤難以發生，不是讓它難以察覺。

## ADR-016：對話歷史落在 `SessionContext`，保存參數的擁有者明訂

### Context

線框 §21 逐字寫「對話歷史的保存期限與筆數上限**本站不預選**」，並明寫它與
`U5`／`U8` 的 90 天記憶保存期是**不同的東西**（對話歷史是 session 層，記憶是內容層）。
refined-mockups 把它列為交接 `H-10` 並指派本站。

另一件必須一起說的事：refined-mockups 的可達性自檢查出
**`RecentConversations.hidden`（首次使用時不渲染該區）在使用者送出第一則訊息之後
就永遠不可達**，除非對話歷史有清除端——而清除端正是保存參數要決定的東西。

### Decision

對話歷史的**實體落點**為既有的 `SessionContext`（它已擁有 `BrainSession`，對話歷史
是同一個 session 層的狀態），**不新建元件**。

**保存期限與筆數上限本站同樣不定數值**，但明訂三件事：① 它是 `SessionContext` 的
職責，不是 `MemoryStore` 的（兩者分屬 session 層與內容層）；② 它必須**有**清除端，
否則 `RecentConversations.hidden` 這個狀態只在首次使用可達一次；③ 數值由
`nfr-requirements` 決定——而該站在本工作流程中是 `CONDITIONAL`，**若被 skip 則轉
`units-generation`（2.7，ALWAYS）**。

### Consequences

**正面**：落點明確，不再是一個無人承接的交接項；清除端的存在被記為硬要求而非選項。

**負面**：數值仍未定，故 `units-generation` 切單元時無法完整寫出該單元的完成條件。
**這是誠實的未決而非遺漏**：定一個沒有依據的數字（例如「30 天」）會讓下游以為它
有來源。

### Alternatives Rejected

- **新建 `ConversationHistory` 元件**：它與 `BrainSession` 的生命週期相同、資料來源
  相同、變更理由相同——`architecture-guide.md` 逐字「若兩個元件總是一起改，它們是
  一個元件」。
- **併入 `MemoryStore`**：會混淆 session 層與內容層，而 `[S12]` 已定案兩者是兩件事
  並存；且記憶的 90 天保存期會被誤用到對話歷史上。
- **本站直接定一個數值**：沒有依據。`[F5]`／`[S12]` 都沒有對話歷史的保存要求，
  憑空定數字正是 `project.md` 禁止的「填一個看起來合理的值」。
