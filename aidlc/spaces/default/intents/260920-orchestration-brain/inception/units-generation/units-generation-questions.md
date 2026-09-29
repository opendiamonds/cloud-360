# Units Generation Questions — 統一入口大腦

<!-- Stage: units-generation（Inception 2.7）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-delivery-agent
     mode: inline · summary_confirmation: required · review_class: advisory
     兩道關卡：Step 4 的 Plan Approval ＋ 產出前的 Consolidated Summary Confirmation -->

## 來源標籤慣例

| 標籤 | 指向 |
|---|---|
| `[Q<n>]`／`[F<n>]`／`[S<n>]` | intent-capture／feasibility／scope-definition |
| `[R<n>]` | rough-mockups |
| `[RA:...]` | requirements-analysis |
| `[US:U<n>]` | user-stories 的**作答**（注意：與本站的 Unit id `U{n}` 不同物，見下方警告） |
| `[DM:D<n>]` | refined-mockups |
| `[DD:E<n>]` | domain-design |
| `[UG:G<n>]` | **本站新增**——units-generation 的作答 |
| `[實測]` | 本站對 repo 現況的唯讀查證 |

> **一處必須避開的撞號**：`[US:U<n>]` 是 user-stories 的**問題編號**（U1–U9），
> 而本站的 **Unit id 也叫 `U{n}`**（stage 檔要求）。兩者形狀相同、意義完全不同。
> 本檔一律以 `[US:U<n>]`（帶前綴）指前者、以裸 `U1`／`U2` 指 Unit，
> 且每次首次出現時加註「Unit」二字。

## 出題前的查證

| # | 查證項 | 結果 |
|---|---|---|
| V-1 | 本專案既有的 unit 數區間 | **5／9／12**（`260819-cost-finops` 5 個、`260916-estimate-upload-rework` 9 個、`260822-gh-projects-sync` 12 個）。故 12 是既有實務的上界 |
| V-2 | unit 命名慣例 | **兩種並存**：描述式 kebab-case（`cost-schema-rbac`、`estimate-parser`——2 個 intent，含最新的 260916）與 `U-{n}-{描述}`（`U-1-map-parse-action`——1 個 intent）。本站採**描述式**（較新且較多），另依 stage 檔在 `unit-of-work.md` 附 `U{n}` id 與目錄對照表 |
| V-3 | 既有 unit 的 kind 分佈 | 五種都用過：`spec`（schema／種子）、`library`（純函式）、`service`（HTTP／workflow）、`ui`（Playwright 驗）、`packaging`（CI／排除規則）；亦有刻意省略 kind 者（`cost-budget-banner`、`U-11-readme-pointer`） |
| V-4 | 部署模型的既有定案 | `cost-finops` 的 unit-of-work 逐字寫「**embedded**：同一 FastAPI process、同一 SPA bundle。Unit = 邏輯 Module，不是微服務」 |

## 已由上游或既有架構決定、本站不問

依 `project.md` 的 `requirements-analysis:260822-ra-c5`——單一可行解不出成題目，
改在摘要揭露後果。下列三項**沒有第二個可行解**，故不問：

| 項 | 為什麼沒有第二解 |
|---|---|
| **部署模型 ＝ embedded** | 既有架構是 modular monolith（單一 FastAPI `app`、7 個 router `include_router` 進同一 process、單一 `DATABASE_URL`、`Dockerfile` 無 `--workers`），前端是單一 SPA bundle。Unit 是**邏輯模組**而非可獨立部署的服務——這是既有事實，不是本站的選擇。`cost-finops` 已為同一結論留下前例 |
| **依賴表達 ＝ 拓樸 ＋ 可平行集合** | stage 檔明文禁止本站推薦施工順序或指認關鍵路徑（那是 2.9 的經濟決策），並要求列出可平行機會。故「嚴格拓樸序 vs 允許平行」不是選擇——兩者都要有：DAG 給拓樸，可平行集合給 2.9 當輸入 |
| **既有模組不進 yaml** | `project.md` 的 `units-generation:c22` 逐字：yaml 邊只列本 intent 待建 unit，已存在的 brownfield 模組寫在散文前提、不進 compiler |

---

## G1. 單元切成幾個，用什麼軸？

`[DD:E1]`=A 定案六個元件，但元件不等於單元——`project.md` 的 `units-generation:c6`
逐字：**切分判準是「驗證方式與失敗模式是否同類」**，不是元件該怎麼分配。
本 intent 的驗證方式橫跨六類：schema DDL（真實 PostgreSQL CI job）、純函式
（property-based）、HTTP 端點（`TestClient`）、WebSocket（`websocket_connect`）、
前端（Playwright）、基礎設施（compose ＋ env contract）。

`[實測 V-1]`：本專案既有 unit 數為 5／9／12。

- **A. 中粒度，約 12 個**（建議）：每個單元對應**一種驗證方式 × 一個資料擁有者**。
  schema 類獨立（真實 PG job 驗）、純函式類獨立（PBT 驗）、HTTP 類按資料擁有者分
  （階層／記憶）、WS 閘門獨立、前端按畫面群分、基礎設施獨立。落在既有實務上界。
- **B. 粗粒度，約 8 個**：六個元件各一個，加基礎設施與前端各一。單元較少、
  跨單元契約少；但每個單元內會混多種驗證方式（例如記憶單元同時含 schema DDL、
  純函式檢索與 HTTP 端點），「這個單元完成了嗎」會同時指涉三種判準。
- **C. 細粒度，約 16 個**：B 的八個再按驗證方式全部拆開，含把每個前端畫面獨立。
  邊界最清楚，但**超出本專案既有實務上界（12）**，且跨單元契約數量成長。
- **D. 依元件一對一，6 個**：最貼合 `components.md`，但基礎設施（Redis／Ollama／
  pgvector image）與前端畫面無元件可歸，會被硬塞進某個元件內。

[Answer]: A
<!-- A = 中粒度，約 12 個單元；軸為「一種驗證方式 × 一個資料擁有者」｜作答時間 2026-09-25T17:27:35Z（date -u 取值）。依選項內容比對回寫。 -->

## G2. 基礎設施（Redis、Ollama、pgvector image、env 同步）要獨立成單元嗎？

回補項 **N-11** 含：DB image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`
（deploy ＋ test 兩個 compose）、Redis 第 5 個服務、Ollama 第 6 個服務、
模型快取 volume、`render-env.sh`／`.env.example`／`LOCAL-DEV.md` 三處同步。
這些的失敗模式與程式碼完全不同——它們由 `scripts/validate_env_contract.py`
與部署本身驗證，不由任何測試驗證。

- **A. 獨立一個單元**（建議）：`brain-infra`。理由是它的驗證方式（env contract
  腳本 ＋ 實際部署）與所有程式碼單元不同類，且它是**其他單元的前置**——沒有 Redis
  就跑不了 session、沒有 pgvector 就建不了記憶 schema。
- **B. 併入各自的消費者**：Redis 併進 session 單元、pgvector 併進記憶 schema 單元、
  Ollama 併進 embedding 單元。每個單元自帶其基礎設施，較內聚；但 compose 檔會被
  三個單元同時改，而 `validate_env_contract.py` 是**一次驗全部**，無法分單元判定。
- **C. 拆兩個**：`brain-infra-db`（pgvector image ＋ 記憶 schema 的前置）與
  `brain-infra-services`（Redis ＋ Ollama ＋ env 同步）。

[Answer]: A
<!-- A = 基礎設施獨立為一個單元 `brain-infra`｜作答時間 2026-09-25T17:27:35Z（date -u 取值）。依選項內容比對回寫。 -->

## G3. 契約與 schema 類單元要獨立於它們的消費者嗎？

兩個候選：**WS 訊息型別契約**（回補項 N-1／`[RA:NFR5]`，含一道新的 CI 一致性檢查）
與 **schema DDL**（階層三表、記憶 schema）。兩者都是「消費者要靠它才能動工」的
建置期契約。`[實測 V-3]`：既有 intent 把 schema／種子歸為 `spec`、把純函式歸為
`library`，兩者都獨立於其 `service` 消費者。

- **A. 兩者都獨立**（建議）：`brain-ws-contract`（`spec`）與兩個 schema 單元
  （`spec`）。理由是它們是 `depends_on: []` 的可平行根——契約先定，消費者才能並行；
  且 CI 一致性檢查的失敗模式（規格漂移）與端點測試完全不同。
- **B. 契約獨立、schema 併入其服務**：WS 契約獨立（它跨前後端），但 schema DDL
  併進擁有它的服務單元（記憶 schema 進記憶服務、階層 schema 進階層服務）。
- **C. 兩者都併入消費者**：不設 `spec` 類單元。單元數最少，但**會讓前後端無法平行
  開工**——前端要等後端定出訊息型別。

[Answer]: A
<!-- A = WS 契約與兩個 schema 皆獨立為 `spec` 類單元，是可平行根｜作答時間 2026-09-25T17:27:35Z（date -u 取值）。依選項內容比對回寫。 -->

## G4. 前端要切成幾個單元？

本 intent 的前端面有四塊：入口頁（`BrainChat`／`ContextBar`／`WorkItemDock`／
`ClarifyCandidates`／`CostAnswerCard`／`StreamingMessage`，共 10 個元件規格）、
`/memory` 頁、切換對象選單與建立表單、以及無障礙閘門（N-9 的 axe）。
全部由 Playwright 驗，但**資料來源不同**：入口頁靠 WS、記憶頁靠 HTTP、
選單靠階層 API。

- **A. 三個：入口頁 ／ 記憶頁 ／ 對象選單與建立**（建議）：按**資料來源**切，
  三者各自依賴不同的後端單元，故可在後端就緒後分別開工。axe 閘門獨立為
  `packaging`（它改的是 CI 與依賴，不是畫面）。
- **B. 一個 `brain-ui` 全包**：前端只有一個單元。最內聚，但它會同時依賴 WS 契約、
  記憶 API 與階層 API——**三個後端單元全部就緒才能開始**，失去平行機會。
- **C. 四個**：A 的三個再把 axe 閘門也算前端單元之一（而非 `packaging`）。
- **D. 五個**：入口頁再按畫面拆（對話區／脈絡列與工作項／成本卡片）。

[Answer]: A
<!-- A = 前端三個單元（入口頁／記憶頁／對象選單與建立），axe 閘門獨立為 `packaging`｜作答時間 2026-09-25T17:27:35Z（date -u 取值）。依選項內容比對回寫。 -->

## G5. 切回共享對話時，獨立那段的內容如何處置？（`OQ-1`，domain-design 轉移來的 `H-2`）

`[RA:FR3.3]` 逐字：「使用者得隨時切回共享對話。切回時獨立那段的內容如何處置未定」。
此題原指派 `domain-design`，該站**未定案**並轉移至本站（其交接事項 H-2），
理由是它屬對話歷程的保留語意而非元件邊界。

已被決定的外框（`[DD:E6]`=A）：作業對象、共享／獨立狀態、工作項集合與對話歷程
**全部在同一個 Redis session key 之下，TTL 24 小時、每次互動續期**——所以兩段對話
都活在同一個 key 裡、一起到期。剩下的是「切回共享時，獨立那段怎麼辦」。

- **A. 保留但不併入**（建議）：獨立那段留在 session 內，切回共享後**不出現在
  共享對話流中**；再次切為獨立時原樣接續。使用者在該頁的獨立對話是一個可來回的
  分軌。可測不變量：切為獨立 → 講一句 → 切回共享 → 再切為獨立，該句仍在。
- **B. 捨棄**：切回共享即丟棄獨立那段。最省（不需保留第二份歷程），但使用者在
  子頁面講過的話會無聲消失——而 `[RA:FR3.2]` 的獨立對話「不共享訊息歷程」是
  刻意的設計，丟棄它等於那段對話從未存在。
- **C. 併入共享流末端**：切回時把獨立那段接到共享對話後面。歷程只有一份，
  但這會**推翻 `[RA:FR3.2]`**（該條逐字定案獨立對話「不共享任何訊息歷程」）。
- **D. 保留且可回溯**：獨立那段保留，並在共享流中留一個可展開的入口指向它。
  最完整，但需要一個新的使用者可見面（`mockups.md` 與 `interaction-spec.md`
  皆未畫），會是本站新增的 scope 項。

[Answer]: A
<!-- A = 保留但不併入：獨立那段留在 session 內，切回共享後不出現在共享流，再切為獨立時原樣接續｜作答時間 2026-09-25T17:27:35Z（date -u 取值）。依選項內容比對回寫。
     **`OQ-1` 至此定案。** 它的路徑是：requirements-analysis 記為 Open Question 並
     指派 `domain-design` → `domain-design` 未定案、以其交接事項 H-2 轉移至本站
     → 本站定案 A。定案不推翻任何已核可需求：`[RA:FR3.2]`（獨立對話不共享任何
     訊息歷程）成立，因為保留的那段**不進共享流**；`[DD:E6]`=A（單一 session key
     ＋ TTL）成立，因為兩段都在同一個 key 之下、一起到期。
     可測不變量：切為獨立 → 講一句 → 切回共享（該句不出現在共享流）→ 再切為獨立
     （該句仍在）。 -->

## Plan Approval

**分解計畫**（依 `[UG:G1]`=A 的軸「一種驗證方式 × 一個資料擁有者」實際枚舉）：

**17 個單元**、23 條依賴邊、**無環**、**4 個可平行根**、7 層。kind 分佈：
`spec` 4、`service` 6、`ui` 3、`packaging` 3、`library` 1。

> **此處的「23 條依賴邊」是計畫核可當時的數字，刻意不改**（修訂 3 標記）。
> 修訂 2 補回兩條 `components.md` 宣告而本站遺漏的邊後，實際為 **25 條**。
> 本區塊是**當時呈現給使用者、並據以取得核可的計畫紀錄**，改它等於竄改那份紀錄；
> 現行數字以 `unit-of-work-dependency.md` 為準。


| 層 | 可互相平行的單元 |
|---|---|
| 0 | `brain-infra`、`brain-ws-contract`、`rbac-story-ids`、`hierarchy-data` |
| 1 | `memory-data`、`embedding-port`、`hierarchy-service` |
| 2 | `memory-service`、`memory-purge`、`session-store` |
| 3 | `intent-router`、`work-orchestrator`、`memory-page-ui` |
| 4 | `brain-gateway` |
| 5 | `entry-page-ui` |
| 6 | `object-picker-ui`、`a11y-gate` |

> 上表是**拓樸分層**，**不是** Bolt 順序。stage 檔明文禁止本站推薦施工順序或指認
> 關鍵路徑——那是 2.9 Delivery Planning 的經濟決策。分層只表達「哪些單元之間沒有
> 依賴、因此可以平行」。

**我在 `[UG:G1]` 的選項裡寫錯了一個數字，如實記載**：該選項的標題是「中粒度，
**約 12 個**」，但那是我**沒有實際枚舉就寫下的估計**。照該選項自己定的軸誠實展開，
結果是 **17 個**。這正是 `project.md` 的
`260920-orchestration-brain:delivery-planning:dp-L1` 那條規則所警告的形狀——
「寫下任何可以被計算的數字之前先實際算一次」——而我在同一個 intent 內又犯了一次。

**兩項連帶揭露**：

1. **17 超出本專案既有實務的上界**。實測既有三個 intent 為 5（`260819-cost-finops`）、
   9（`260916-estimate-upload-rework`）、12（`260822-gh-projects-sync`）個單元。
2. **壓到 12 需要 5 次合併，每一次都把兩種驗證方式塞進同一個單元**——而那正是
   `[UG:G1]` 選項 B（粗粒度）的代價，使用者已在該題拒絕 B。故「12」不是一個
   與 `[UG:G1]`=A 相容的數字。

使用者在此關卡選擇**接受 17 個**。

[Answer]: Approve Plan
<!-- 作答時間 2026-09-25T17:38:14Z（date -u 取值）。使用者在看過「我估 12、實算 17」的落差、
     17 超出既有實務上界、以及壓到 12 的具體代價之後，選擇接受 17 個單元。 -->

## Consolidated Summary Confirmation

<!-- 修訂 2：修訂 1 的收據 3f63c784 已因本輪修訂失效，整份重取。 -->

**五題定案不變**（G1–G5）。**DAG 有實質更正**：邊數 **23 → 25**，可平行根 4、
層數 7、完全獨立對 56 皆不變（兩條新邊連接的單元原本就有間接路徑相連）。
五個 sensor 全綠。

**修訂 2 處理複審的兩項**：

| 複審 | 修了什麼 | 我自查出的額外部分 |
|---|---|---|
| **R-03**（Unresolved） | 補回 `U12 work-orchestrator → U7 hierarchy-service` 這條 `components.md` 宣告而本站 yaml 缺少的邊；`DG-3` 的歸屬三處統一 | **把自檢 2 的基準改對之後，又查出第二條缺邊** `U13 brain-gateway → U10 session-store`，複審沒看見它。`DG-3` 的修法不是二選一而是把 `DiagramChangeRecord` 的**三個角色分開講**：寫入端 `U12`、schema 保管 `U4`、讀取端落點 `U7`——`DG-3` 缺的是讀取端，故落點為 `U7` |
| **R-05**（Minor） | `U14` 的單元內故事順序補入 `US2.1` 與 `US3.1`（10 → 12） | 一併記下它為何漏：三張衍生表同源，修訂 1 只重生了其中兩張 |

**自檢 2 的基準已修正，這是本輪最重要的改變**：原本比對「本站 yaml」與「本站整合
點表」，而後者是我**從前者生成的**——同源必然一致，也必然同時錯。改為比對**上游
`components.md` 的 8 條元件邊**，經「元件 → 單元」映射後逐條確認本站 yaml 有對應
邊。改基準後一次查出兩條缺邊（一條複審抓到、一條沒有）。

**三支 sensor 實跑結果（修訂 3）**：`required-sections` 三份產出皆 `pass: true`
（H2 數 7／7／6，`edge_block: ok`）；`traceability` `pass: true`（gaps／orphans／
invalid 皆空）；`upstream-coverage` `pass: true`（`components`／`decisions`／
`requirements`／`stories` 四個 consume 皆被引用，`unreferenced` 為空）。

**七項送審前自檢**

| # | 自檢項 | 結果 |
|---|---|---|
| 1 | 可達性 | 通過。拓樸排序覆蓋 17／17，無環 |
| 2 | 契約端點三問（**基準已修正**） | 通過。以 `components.md` 的 8 條元件邊為基準、經「元件 → 單元」映射逐條比對，8／8 皆有對應單元邊（修訂 3 重跑，結果同修訂 2） |
| 3 | 引用逐字核對 | 通過。修訂 3 新增文字的兩處引用已開檔核對：`components.md:327` 逐字為 `WorkOrchestrator -->|"架構圖被異動時寫入變更紀錄"| ProjectHierarchy`、`:321` 逐字為 `BrainGateway -->|"取出與更新該連線的作業對象與共享狀態"| SessionContext` |
| 4 | 檔案集合一致性 | 通過。4 個 produces 與實際相符。同 kind 單元的落點形狀亦一致：16 個有故事的單元各有且僅有一個 `construction/u<N>-<name>/`，`<N>-<name>` 與單元清單的 U↔name 映射逐筆相符；`U17` 無故事故無列（已在檔內說明理由） |
| 5 | 跨檔傳播 | 通過。本輪改動的事實是「邊數為 25」，其三種表達形式（yaml `depends_on`、mermaid 箭頭、整合點表列）已正規化方向後逐邊比對，**三者集合完全相等、皆為 25，差異為空**；`DG-3`／`ADR-0006` 集中於 `unit-of-work.md` 是刻意的 |
| 6 | 可算的數字先算再寫（**步驟定義於修訂 3 擴為兩步**） | **部分通過，修訂 3 補齊**。**正向驗證通過**：我挑的 8 個數字實算全部相符（yaml 邊 25／整合點表 25／mermaid 邊 25／`unit-of-work-dependency.md` 寫的邊數 25／故事 20／`U14` 承載 12／`U14` 順序表 12／traceability 20），17 個單元的「依賴／被依賴」行亦以腳本逐一比對過。**但反向驗證當時沒做**，於是漏掉 `unit-of-work.md:274` 仍寫「23 條邊」——**該處是審查 R-06 抓到的，不是我自檢抓到的**，而修訂 2 的本表當時宣稱「8 個數字全部相符」，那句話對那一處而言是不實的。根因：正向驗證只覆蓋**我挑的位置**。`project.md` 的 `units-generation:rev1-L1` 逐字要求「改完後對每一類被計數的實體各跑一次**舊數字**的 grep」——規則我有、沒跑。**修訂 3 起自檢 6 定義為兩步**：(1) 實算每個宣稱的數字；(2) grep 每一個被改動過的**舊**數字，逐一判定命中處是殘留還是合法的歷史敘述。做完第二步後找到的是**兩處**而非審查說的一處——第二處在本檔的 Plan Approval 區，經判定為**合法的歷史紀錄**（那是當時呈現並據以核可的計畫，改它等於竄改紀錄），已就地加標記而不改數字。**修訂 3 實跑後補記第二步的性質**：反向 grep 會產出**偽陽性**，必須逐一判定而不得逐一改掉——本輪的 `16 個單元` 一詞命中 `unit-of-work-story-map.md:104`，它不是舊的單元總數殘留，而是「17 個單元中有 16 個帶故事」這個**當前為真**的陳述（已以腳本重算覆蓋表：17 列、16 列計數大於 0、`U17` 為 0、20／20 故事全部指派）。所以第二步的產出是**待判定清單**，不是待修清單。修訂 3 本輪重算的其餘數字：可平行根 4（`U1`／`U2`／`U3`／`U4`）、層數 7、kind 分佈 `spec` 4／`service` 6／`ui` 3／`packaging` 3／`library` 1、完全互相獨立的單元對 56（以可達性閉包實算，與檔內宣稱相符）、懸空依賴 0 |
| 7 | 逐項對照 hard constraint | 通過。ADR-0006 四面向逐項判定表 4 列齊備、涵蓋 11 個單元、無空白格；PBT 落點在 `U11`／`U12`／`U6` |

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-26T01:52:32Z（以 `date -u` 取值）。修訂 3 的確認第三次重取（redo jump 後）。前兩次收據 29bbc986、ade04d5c 皆已作廢。

     為什麼走到 redo jump（如實記載，因為這一段是我的流程失誤）：
     - 複審 R-06 後我報了 `revised`，該報告把本站置為 revising（狀態檔 `[R]`）。
     - 之後我報 `awaiting-approval`，引擎回「已在等待核可」，我據此以為閘門開著——
       但狀態檔的 checkbox 仍是 `[R]`，閘門其實沒開。
     - 於是兩輪 READY 審查（review-04 的 iteration 1、review-06 的 iteration 2 復原審查）
       的收據都掛在一個 revising 的站上，核可時以 REVIEW_EVIDENCE_MISSING 被拒。
     - 引擎只提供一個復原動作（redo jump），使用者選擇執行，於 2026-09-26T01:50:10Z 完成，
       `stages_reset: ["units-generation"]`，作答與四份產出皆保留。

     另一項我低估的代價：在核可關卡折入 R-07 會改動產出，使審查過期
     （ARTIFACT_REVIEW_STALE），而「復原審查」引擎語意上只給一次。提供該選項時我只
     說了「重取摘要確認」，沒說會觸發復原審查——這是我算漏的，不是使用者選錯。

     修訂 3 的改動範圍（四處，皆非設計變更）：
     (1) `unit-of-work.md:274` 的「23 條邊」改為「25 條邊」——複審 R-06 抓到的殘留舊值；
     (2) 本檔 Plan Approval 區的「23 條依賴邊」**刻意保留**，就地加標記說明它是計畫
         核可當時的紀錄、現行數字以 `unit-of-work-dependency.md` 為準；
     (3) 自檢 6 的定義由一步擴為兩步（正向實算 ＋ 反向 grep 每個改動過的舊數字），
         並把修訂 2 那句不實的「8 個數字全部相符」就地改為誠實敘述；
     (4) 折入審查 R-07（Minor）：`unit-of-work-story-map.md` 的「讀法」節補一段，說明
         `traceability` sensor 的 schema 對 `coverage[].target` 只允許單一字串
         （`aidlc-sensor-traceability.ts:15,122`），故 manifest 每則故事只記第一個單元，
         權威映射是該檔表格。審查說「18 of the 20 rows」，實算是 **17 則**；復原審查
         （review-06）獨立複算後確認 17 正確、它自己的 18 是錯的。

     尚未處置的 open item：**R-08**（Minor，由 R-07 的折入引入）——`:7` 的「17 個單元」
     與 `:14` 的「17 則故事」是兩個意義不同、數值相等純屬巧合的 17，建議就地消歧。
     使用者在閘門上選擇 Approve、不折入，故 R-08 以 open item 帶進閘門紀錄。 -->

