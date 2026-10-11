# Bolt Plan — 統一入口大腦

<!-- Stage: delivery-planning（Inception 2.9）· Record: 260920-orchestration-brain
     lead: aidlc-delivery-agent · support: aidlc-architect-agent -->

## 這份檔在做什麼

`units-generation`（2.7）產出了依賴圖——**什麼可以依賴什麼**。本檔決定**走哪一條路**：
哪一批先做、哪一批證明什麼。

本檔的單位是 **Bolt**：**一次建置通過，做完一個或多個工作單元，結束時有東西能跑、能展示**。
每個 Bolt 帶一份「怎樣算做完」、一個「做完會證明什麼」的假說、以及誰負責。
Bolt 不是 sprint，也不是一個功能。

**本檔不做的**：不改依賴拓樸（那是 2.7 已核可的）、不決定跑哪些 AIDLC 階段或深度
（那是 `/aidlc` 的 scope 選擇）、不做數值評分（理由見 `risk-and-sequencing-rationale.md`）。

**讀進來的上游**：`requirements.md`（需求與 NFR）、`stories.md`（20 則故事）、
`mockups.md`（10 格精修畫面——各 Bolt 的「展示」即以它描述的畫面為準）、
`components.md`（6 個元件）、`unit-of-work.md` 與 `unit-of-work-dependency.md`
（17 個單元與 25 條邊）、`unit-of-work-story-map.md`（故事 → 單元對應）、
`contract-summary.md`（17 條契約與 15 條未決事項）。
**`team-practices` 不存在於本 intent**——`practices-discovery` 只在
`260819-cost-finops` 與 `260802-last-login-column` 兩個 intent 跑過，其內容已 promote
至 `aidlc/spaces/default/memory/team.md`，本檔直接讀該層。

## 規模（實算，非目測）

**9 個 Bolt，涵蓋 17 個工作單元**，零遺漏、零重複；`unit-of-work-dependency.md` 的
**25 條依賴邊全部合規**（每條邊的被依賴方都在同一或更早的 Bolt，以腳本逐條驗證）。

## Bolt → 使用者故事（實算，非目測）

依 `unit-of-work-story-map.md` 的「故事 → 單元」對應，把 `stories.md` 的 20 則故事
對回 Bolt。一則故事**完整交付於它最後一個單元所在的那個 Bolt**——在那之前它的
部分單元已完成，但故事本身還不能驗收。

| Bolt | 完整交付的故事 | 數 |
|---|---|---|
| B1 | （無） | 0 |
| B2 | （無） | 0 |
| B3 | `US4.1`、`US4.3`、`US4.5` | 3 |
| B4 | （無） | 0 |
| B5 | `US6.1` | 1 |
| **B6** | `US1.1`、`US1.2`、`US1.3`、`US1.4`、`US2.1`、`US2.2`、`US3.1`、`US5.1`、`US7.1`、`US8.1`、`US9.1`、`US10.1`、`US10.2` | **13** |
| B7 | `US4.4`、`US9.2` | 2 |
| B8 | （無） | 0 |
| B9 | `US4.2` | 1 |
| | **合計** | **20** |

### 這張表揭露了兩件必須明講的事

**一、使用者可見價值高度集中在 B6。** 20 則故事有 **13 則（65%）**在 B6 才完整交付。
若 B6 出問題，超過六成的使用者可見價值跟著延後。這是**本計畫的最大集中風險**，
記入 `risk-and-sequencing-rationale.md` 的 R9。

原因是結構性的：`U14`（入口頁）出現在 **13 則故事**的單元清單裡（`unit-of-work-story-map.md`
的覆蓋表逐字記載），而它在依賴圖的第 5 層、依賴 `U13`，`U13` 又依賴 `U2`／`U11`／
`U12`／`U10`。**入口頁是幾乎所有故事的最後一哩**，這不是排序造成的，是這個 intent
的形狀本來如此。

**二、四個 Bolt 不完整交付任何故事**（B1／B2／B4／B8）。這**不代表它們沒有價值**——
`delivery-planning:c3` 的判準是「湊得出有意義的信心假說嗎」，不是「交付幾則故事」。
這四個各自的假說是可驗的：

- **B1**：兩道新 CI 閘門真的會擋（故意只改一邊 → 紅燈）；三個新基礎設施在主機上跑得起來
- **B2**：既有架構圖遷得進新階層且無孤兒；授權在同進程路徑上真的沒有繞過口
- **B4**：重啟 backend 後脈絡與作業對象完整還原
- **B8**：兩個新頁面通得過自動化無障礙掃描（移除一個 `aria-label` → 紅燈）

四者都是**二元可判、可展示**的，只是展示對象是工程面而非使用者面。

---

## 全域決定

| 項目 | 值 | 來源 |
|---|---|---|
| 順序原則 | **混合：風險打頭，後段轉價值**（`[D2]`=D） | 本站定案 |
| Bolt 粒度 | 以「分開後每個都湊得出有意義的信心假說嗎」為判準綁單元（`[D3]`=B） | `project.md` `delivery-planning:c3` 的逐字判準 |
| 平行度 | **一次一個，序列執行**（`[D4]`=A） | 本站定案 |
| 走 walking skeleton？ | **否**。不先做一個「打通全部架構層的最小端到端切片」 | `team.md` `## Walking Skeleton` Q3 定案 `skeleton: off`（**非本站決定**） |
| 分支與合併 | 每個 Bolt 一條分支，base 與 target 皆 `ut`，**squash-merge** | `team.md` `## Way of Working`（**非本站決定**） |
| 部署 | 合併進 `ut` 即部署到自有 staging——**每個 Bolt 邊界都是一次真實部署** | `org.md` `## Deployment`、ADR-0007 |
| 誰執行 | **全部由 AI 執行**（`aidlc-developer-agent`），無人類分工 | `team-formation`（1.5）未執行；詳見 `team-allocation.md` |

---

## B1 — 地基、契約來源與權限種子

**單元**：`U1` brain-infra、`U2` brain-ws-contract、`U3` rbac-story-ids、`U6` embedding-port
（Bolt 內順序：`U1` → `U6`，其餘無序）

**這個 Bolt 同時做兩件事**，兩者的完成判準必須分開看，不得讓「交付完成」被讀成
「未決事項也已定案」：

### (一) 交付

四個在自身與整條上游都**沒有未決事項**的單元——全 17 個單元中只有這四個是如此。

### (二) 定案五項跨單元的未決事項（`[D1]`=C）

| 未決事項 | 影響單元數 | 它是什麼 |
|---|---|---|
| **`OQ-N3`** | **4**（`U5`／`U8`／`U9`／`U15`） | 記憶功能**沒有寫入端**——`MemoryFacade.write` 全檔只有宣告、無任何呼叫者 |
| `DG-1` | 3（`U5`／`U8`／`U9`） | 稽核事件在其記憶被 90 天清除後的去向未定 |
| `DG-2` | 2（`U4`／`U7`） | `Project`／`System` 刪除的 cascade 行為未定 |
| `OQ-N2` | 2（`U7`／`U8`） | 授權門面唯一性的強制手段（加 lint 檢查，或接受只由 review 擋） |
| `OQ-N1` | 2（`U11`／`U12`） | 誰擁有「產生自然語言回覆」 |

**為什麼在這裡定案而不是留給各自的 Bolt**：這五項都是**跨單元的語意選擇**。留給
per-unit 的 `functional-design`（CONDITIONAL，skip 則轉 `code-generation`）等於讓單一
單元的實作者各自決定，很可能得出彼此不自洽的結果。

**為什麼不開一個只定案、不交付的前置 Bolt**：`delivery-planning:c3` 逐字說「湊不出
信心假說的 Bolt 沒有可展示的成果，也就沒有部署它的理由」。把定案掛在一個有產出的
Bolt 上，不需要為此開例外。

### 怎樣算做完

- [ ] **交付面**：Redis（第 5 服務）、Ollama（第 6 服務）、pgvector image 換版在
      `deploy` 與 `test` 兩個 compose 都到位；模型快取 volume 建立
- [ ] **交付面**：`render-env.sh`／`deploy/.env.example`／`LOCAL-DEV.md` **同批更新**
      （缺一即違反 `project.md ## Mandated`）；`python3 scripts/validate_env_contract.py` 通過
- [ ] **交付面**：`ws-contract.json` 與其前端型別檔產出並 commit；**兩道新 CI 閘門上線**
- [ ] **交付面**：`K1`／`K2` 兩個 story id 經 `ensure_missing_role_permissions` 插入
      （**不得依賴 `ensure_role_permissions_seeded(force=False)`**，該函式在表非空時整段 no-op）；
      `schema_rbac.sql` 與 `DEPLOY.md` 同步（blocking）
- [ ] **交付面**：`EmbeddingPort` 四個實作（`ollama`／`fastembed`／`fulltext`／`stub`）
      與設定切換；偵測不到選定提供者時**大聲失敗並列出可選值**
- [ ] **定案面**：五項未決事項各有一份書面決定，寫入 `functional-design` 的產出或
      一份新 ADR；每項註明它改變了哪些單元的責任
- [ ] **定案面**：若 `OQ-N1` 或 `OQ-N3` 的結論需要一條**新的依賴邊**（例如 `U13 → U8`），
      該邊必須回報本檔並重審後續 Bolt 順序——**不得直接在實作中加邊**

### 做完會證明什麼

1. **三個新基礎設施在自有 staging 主機上真的跑得起來**，含 Ollama 的 RAM 餘裕——
   這個數字 `domain-design` 明記**未實測**，B1 是它第一次被驗證。
2. **兩道新 CI 閘門真的會擋**：故意只改後端訊息模型而不重產型別檔，CI 必須紅燈。
   這是 `[RA:NFR5]` 的承載機制，而既有兩道漂移閘門對 WebSocket 完全無效。
3. **五項跨單元語意有了單一、自洽的答案**，後續七個 Bolt 站在已定案的地基上。

### 展示

部署後 `docker compose ps` 顯示六個服務健康；在一個分支上只改後端訊息模型、
不重產型別檔 → CI 紅燈；以無 `K1` 權限的帳號登入 → 不會落到入口頁且落地順序正確。

---

## B2 — 階層資料與服務

**單元**：`U4` hierarchy-data、`U7` hierarchy-service（Bolt 內順序：`U4` → `U7`）

**進入條件**：B1 已定案 `DG-2`（刪除的 cascade）與 `OQ-N2`（門面唯一性的強制手段）。

**仍未決**：`DG-3`（`DiagramChangeRecord` 無讀取端）——落點 `functional-design`；
本 Bolt 可在不解它的情況下完成，因為寫入端與 schema 都在，缺的是查詢面。

### 怎樣算做完

- [ ] `projects`／`systems`／`diagram_change_records` 三表 DDL ＋ `user_diagrams.system_id`
- [ ] 遷移程序有**可被 `unittest` 匯入並呼叫的入口**（不得只存在於 `init_db()` 的副作用，
      否則該驗收只能手動）
- [ ] 遷移後 `system_id IS NULL` 計數為 0，**不為 0 時大聲失敗**而非警告
- [ ] `HierarchyFacade` 為受保護操作的**唯一授權入口**；router 與同進程呼叫端共用它
- [ ] allow/deny 雙向 `TestClient`：有 `K2` → 2xx；無 `K2` → 403

### 做完會證明什麼

既有架構圖**遷得進新階層且沒有孤兒**（`system_id IS NULL` 為 0）；而且授權在同進程
路徑上**真的沒有繞過口**——這是 `components.md` 以絕對語氣寫下、但直到 B1 才有承載
手段的一條不變量。

### 展示

對一份既有的使用者架構圖執行遷移，顯示它掛進「預設專案／預設系統」；以無 `K2`
權限的帳號呼叫建立端點 → 403 且 `detail` 帶授權來源前綴。

---

## B3 — 記憶資料與服務

**單元**：`U5` memory-data、`U8` memory-service（Bolt 內順序：`U5` → `U8`）

**進入條件**：B1 已定案 `OQ-N3`（**寫入端在哪**）與 `DG-1`（稽核事件的去向）。

**仍未決**：`OQ-3`（episodic memory 的加密手段）——落點 `nfr-design`，CONDITIONAL
且其條件依賴 `nfr-requirements` 是否執行。本 Bolt 可完成，但加密手段未定須列在交接。

### 怎樣算做完

- [ ] 記憶獨立 schema ＋ grant 邊界 ＋ `vector(1024)` 欄位 ＋ `embeddingModel` 欄位
- [ ] **真實 PostgreSQL 的 CI job** 驗證 schema 建立、grant 邊界、跨 schema 查詢
      （既有測試走 in-memory SQLite，而 **SQLite 沒有 schema 概念**，對此完全無驗證路徑）
- [ ] 擁有者由寫入端依**已驗證身分**設定，**不得由呼叫方指定**；可見範圍預設最窄
- [ ] 放寬可見範圍僅 `Platform_Admin`／`Platform_Owner`，且每次變更留稽核
- [ ] 相似度檢索**只比對同一 `embeddingModel` 的列**（同維度不等於同向量空間，
      不加這道過濾會讓跨模型檢索回垃圾**且不報錯**）
- [ ] **B1 定案的寫入端真的被實作並被呼叫**——`MemoryFacade.write` 有指名的呼叫者

### 做完會證明什麼

**記憶不是空的。** 這是本計畫要攤開的第一個高風險項（`[D6]`=A）：`OQ-N3` 若沒解，
四個單元做出來是惰性的而 CI 會全綠。B3 是它第一次被真實驗證的地方。

### 展示

真實 PostgreSQL 的 CI job 綠燈；寫入一則記憶後以另一個使用者身分檢索 → 查不到
（可見範圍生效）；以 `Platform_Admin` 放寬範圍 → 查得到且稽核事件有 `previousScope`
與 `newScope`。

---

## B4 — session 與工作項編排

**單元**：`U10` session-store、`U12` work-orchestrator（Bolt 內順序：`U10` → `U12`）

**進入條件**：B1 已定案 `OQ-N1`（誰產生自然語言回覆）——若結論是 `U12`，本 Bolt 的
範圍會增加，且需要一條新的依賴邊送回本檔重審。

**仍未決**：`OQ-1`（切回共享時獨立那段的處置，**已三度轉手**）、`OQ-N4`（`BrainSession`
只有一個 `messageHistory`、撐不起 `[DD:E6]` 要求的「兩段」）、`H-3`（`等待中` 狀態的
可達性）。三項落點皆為 `functional-design`。**`OQ-N4` 會改 `U10` 的公開介面與資料形狀**，
故它必須在本 Bolt 開工前有答案。

### 怎樣算做完

- [ ] session 狀態**一律放 Redis，不得放行程記憶體**；單一 key ＋ TTL 24h 每次互動續期
- [ ] session key 由 `U13` 在握手時**由已驗證使用者 id 推導**（一使用者一個大腦 session）
- [ ] 工作項五狀態機（`處理中`／`等待中`／`完成`／`失敗`／`已停掉`）＋ `sideEffect` 欄位
      （`none`／`unknown`／說明文字——**`unknown` 是合法值**，系統不承諾停掉時不留半成品）
- [ ] 呼叫既有 C1 一律走 **HTTP 帶使用者 token**，**不得**同進程直呼 service 層
- [ ] 成本 job 的五種狀態事件轉譯進大腦訊息流；**不做 token 級巢狀串流轉送**
- [ ] `U12` 經 `HierarchyFacade.record_diagram_change` 寫入變更紀錄

### 做完會證明什麼

**重啟 backend 之後，既有對話的脈絡與作業對象完整還原**（`[RA:NFR4]` 的可測不變量）。
這條是本 intent 唯一一條可以用「關掉再開」直接驗的 NFR。

### 展示

建立一個 session、選定作業對象、送幾則訊息 → `docker compose restart backend` →
重新連線後脈絡列仍指向同一個「專案／系統／架構圖」三元組，對話歷程仍在。

---

## B5 — 路由層

**單元**：`U11` intent-router

**進入條件（阻塞性，必須先有答案）**：`OQ-10`（路由層能否產出可比較的信心值）與
`OQ-4`（路由層模型定案），**兩者必須一併決定，不得分開處理**。

> **這條進入條件的落點沒有自然承接站。** `OQ-10`／`OQ-4` 指派
> `nfr-requirements`（3.2，**CONDITIONAL**），而 `nfr-design` 的執行條件依賴
> `nfr-requirements` 已執行，故兩站會一併 skip。**該站若被 skip，須重新提交使用者裁決
> ——不得由實作者當場決定。** 理由：`[RA:FR1.6]` 逐字寫「若實作出一個不輸出信心值的
> 路由層，`FR1.3` 會**靜默永不觸發**，而文件上看起來已解決」。

**若 `OQ-10` 的結論為「無可用信心訊號」**：`FR1.3` 的觸發條件改以「候選意圖並列且
無單一最高分」表達，`FR1.7` 的 0.7 隨之不適用，本單元的責任敘述與其 property-based
測試的 property **都要改寫**。這不是實作細節，是本 Bolt 範圍的實質變更。

### 怎樣算做完

- [ ] 意圖分類、多意圖拆解、指涉詞解析
- [ ] **每一次入口頁輸入一律先過分類並產生信心值**（`[D-C10]`=C 定案：不採「跳過分類」
      的快路徑）
- [ ] 信心低於門檻時**不得交辦、不得產生任何結果**，改回 clarify 候選
- [ ] 判定意圖前先過既有 `prompt_guard`；命中則**不呼叫任何 LLM**，回固定拒絕訊息
      （該固定訊息**是有內容的有效回覆**，正常以 `done` 結束）
- [ ] **純函式的門檻比較有 property-based 測試**（ADR-0006 對 agent routing 的
      hard constraint 落點）
- [ ] 可替換的 LLM 執行介面，替換作用域限 **runtime 實例或單次測試**，不共享可變全域狀態；
      替身能確定性模擬正常串流／零內容／部分輸出後失敗／延遲取消四種情境
- [ ] 一致性測試鎖住六項連線常數與事件語彙對照表（見 `contract-summary.md` 的 `X-03`）

### 做完會證明什麼

**信心值真的可以與門檻比較，而且低於門檻時系統真的不交辦。** 這是本計畫要攤開的
第二個高風險項（`[D6]`=B）——它若不成立，反問路徑會靜默永不觸發。

### 展示

給一句明確的需求 → 交辦到正確能力；給一句模稜兩可的 → 不交辦、列出候選判讀並反問；
給一句試圖竄改平台的 → `prompt_guard` 命中、固定拒絕訊息、**LLM 呼叫次數為 0**。

---

## B6 — 閘道與入口頁（價值高峰）

**單元**：`U13` brain-gateway、`U14` entry-page-ui（Bolt 內順序：`U13` → `U14`）

**為什麼這兩個同批**：判準是 `[D3]`=B 的信心假說——閘道與其**唯一**消費端分開後，
前者湊不出可展示的成果（部署一個沒人呼叫的 WebSocket 端點）。
**注意這不是 `delivery-planning:c6` 的破壞性變更理由**，兩者在
`risk-and-sequencing-rationale.md` 有分開說明。

**仍未決**：`OQ-5`（兩種串流機制並存的邊界）、`OQ-8`（nginx／cloudflared 是否透傳
`Sec-WebSocket-Protocol`）。**`OQ-8` 是 token 傳輸方式的前提**，須在本 Bolt 開工前實測。

### 怎樣算做完

- [ ] WebSocket 掛在 **`/api/` 之下**（`location /` 走 `try_files … /index.html`，
      握手落那裡會拿到 HTML）
- [ ] token 走 `Sec-WebSocket-Protocol` 標頭，**不得放 query string**；
      **以 token 置於 query string 的握手必須被「拒絕」**，不是「我們不那樣寫」
- [ ] 握手以 **`record=True`** 呼叫 `get_user_from_token`（既有前例用 `record=False`，
      照抄會讓帳號活動稽核對大腦使用者**靜默失效**）
- [ ] 協定版本 `v` 欄位與握手比對；不相容以 4400 關閉並帶原因
- [ ] 終止語意：`done` 代表已產出**可呈現**的回覆；無有效回覆時送
      `error(code: EMPTY_RESPONSE)`；每輪至多一個終止事件；前端收到零內容 `done`
      視為**契約違規**，顯示備援提示並記錄異常，**不呈現空白成功態**
- [ ] 同一 session key 允許多條並存連線；狀態改變時對該 key 的**全部存活連線扇出**
- [ ] 入口頁：`BrainChat`／`ContextBar`／`WorkItemDock`／`ClarifyCandidates`／
      `CostAnswerCard`／`StreamingMessage` ＋ `DefaultRedirect` 的 `K1` 瀑布之首
- [ ] 前端新增資料來源走 `AdminPage.tsx` 的兩層抓取形狀
      （`react-hooks/set-state-in-effect` 為 **error** 級，違反即 CI 紅燈）

### 做完會證明什麼

**使用者在入口頁打一句話，看到逐字串流的回覆與工作項。** 這是本 intent 的核心價值
第一次成立，也是 `[D2]`=D 的「後段轉價值優先」的落點。同時驗收第三個高風險項
（`[D6]`=C）：三項 WebSocket 硬約束**每一項都與既有前例相反**，照抄就錯。

### 展示

登入 → 進入口頁 → 輸入「幫我畫一張三層式架構圖」→ 看到逐字出現的回覆與一個工作項
從「處理中」轉「完成」；另開一個分頁改作業對象 → **第一個分頁的脈絡列同步更新**
（扇出生效）；用 `?token=...` 的方式握手 → 連線被拒。

---

## B7 — 記憶頁與對象選單

**單元**：`U15` memory-page-ui、`U16` object-picker-ui

**為什麼 `U15` 排在這裡而不是更早**：`U15` 在依賴圖上只依賴 `U8`（B3 之後即可動工），
照價值優先本該提前。但它的信心假說是「記憶頁三區**有內容**」，而**寫入端落在哪個單元
由 `OQ-N3` 決定，最可能是 `U11`（B5）或 `U12`（B4）**。太早做的話頁面是空的，
而那跟我們最擔心的缺陷**長得一模一樣**，分不出來。

> **這是一條「信心假說造成的排序約束」，不是依賴邊。** 它不在 2.7 的 DAG 上，
> 只有把「這個 Bolt 要證明什麼」代入才會浮現。兩者性質不同：DAG 邊不可違反，
> 這一條可以由後續決定覆寫（若 `OQ-N3` 把寫入端定在 B3 之前可達的單元，`U15` 就能提前）。

### 怎樣算做完

- [ ] `/memory` 三區檢視與逐則刪除；走 `ProtectedRoute` **不包** `CapabilityRoute`
      （把關的是擁有者欄位而非角色，故**不需新 story id`）
- [ ] Sidebar 項 ＋ 入口頁捷徑（兩個入口一個顯示條件）
- [ ] 切換對象選單 ＋ 就地建立表單 ＋ `CreateConfirmCard`
- [ ] 兩個建立入口共用**同一條寫入路徑**，授權檢查、稽核紀錄與錯誤訊息各只有一份
- [ ] 選取對象經 `set_work_target` WebSocket 訊息傳到伺服器並持久化

### 做完會證明什麼

**記憶頁真的有東西**——回頭驗證 B3 的寫入端確實在寫，而不是「有寫入端但沒人呼叫」。
以及對象切換真的跨頁面持久化。

### 展示

對話幾輪後開 `/memory` → 三區各有內容且只看得到自己的；刪除一則 → 稽核事件出現；
在脈絡列切換專案 → 重新整理後仍是新選的那個。

---

## B8 — 無障礙閘門

**單元**：`U17` a11y-gate

**為什麼單獨成一個 Bolt**：它的驗證方式（axe 掃描）與任何其他單元都不同類，
而它單獨就湊得出一個二元可判的假說。

### 怎樣算做完

- [ ] `@axe-core/playwright` 導入（**這是既有 Playwright 層的 plugin、不是新測試框架**，
      故不落在 `[US:U9]`=A 拒絕引入前端 unit 測試框架的範圍）
- [ ] 對入口頁與記憶頁各一次掃描，違規即 CI 紅燈

### 做完會證明什麼

兩個新頁面通得過自動化無障礙掃描。**注意這只涵蓋可自動化的部分**——
`accessibility-checklist.md` 中標為 `[人工]` 的 23 項**仍無自動化承載**。

### 展示

CI 的 axe 步驟綠燈；故意移除一個 `aria-label` → CI 紅燈。

---

## B9 — 90 天清除（**條件式**）

**單元**：`U9` memory-purge

> **本 Bolt 是條件式的。** `OQ-13`（清除 workflow 如何取得資料庫連線——它跑在
> GitHub Actions 上而資料庫在自架 staging 主機後面）是 `U9` 的**單元層級阻塞**：
> **未定案前本單元無法完成**。其落點 `infrastructure-design`（3.4）與轉移目標
> `deployment-pipeline`（4.1）**皆為 CONDITIONAL**——兩者都 skip 時須重新提交使用者。
>
> **若到此仍未定案**：本 Bolt 不執行，`U9` 連同 `[RA:FR4.5]`（90 天保存）一併列為
> 本 intent 的已知未交付項，需明確告知而非靜默略過。

### 怎樣算做完

- [ ] 90 天逾期清除由 **gh-aw／GitHub Actions workflow** 承載，
      **不得**是 backend 內的排程程式（`project.md ## Forbidden`）
- [ ] 決定性的映射邏輯（算出哪些列逾期、發出刪除）放**純 Actions 步驟**，
      不交給 gh-aw 的 LLM 路徑——LLM 路徑是本 repo 三塊結構性盲區之一
- [ ] 清除動作本身留稽核；`DG-1` 在 B1 的定案在此被實作
- [ ] 逾期判定的常數與既有的 `OVERDUE_THRESHOLD`（`activity.py:31`，**帳號**逾期，
      同為 90 天）**命名區分**，避免兩個同值不同義的常數互相污染

### 做完會證明什麼

逾期的記憶真的會被清掉，且清除本身留下稽核。

### 展示

把一列記憶的 `expiresAt` 改到過去 → 手動觸發 workflow → 該列消失且稽核事件出現。

---

## Assumptions & Open Questions

- 9 個 Bolt 的切分以「信心假說」為判準（`[D3]`=B）。`B2`／`B3`／`B4`／`B6`／`B7` 各綁
  兩個單元，`B1` 綁四個，`B5`／`B8`／`B9` 各一個。**未做工時估計**——本檔不含任何
  時間或規模的數字，因為沒有實證輸入 [assumption]
- **`U15` 的排序約束來自信心假說而非依賴邊**（見 B7 的說明）。若 `OQ-N3` 把寫入端定在
  更早可達的單元，`U15` 可以提前，本檔不阻止 [assumption]
- **`B5` 的進入條件可能無人承接**：`OQ-10`／`OQ-4` 的落點 `nfr-requirements` 為
  CONDITIONAL 且無自然承接站。本檔明寫「該站若被 skip 須重新提交使用者」，
  但**沒有機制保證那件事會發生** [assumption]
- **`B9` 可能不執行**（`OQ-13`）。其落點與轉移目標皆為 CONDITIONAL [assumption]
- 本檔假設 B1 能在一個 Bolt 內同時完成四個單元的交付**與**五項跨單元未決事項的定案。
  若實際執行時發現定案需要比預期更多的探索，正確處置是把 B1 拆成兩個 Bolt 並回報，
  **而不是把未定案的項目推給後續 Bolt** [assumption]
- `[D6]` 未選的第四項風險（部署設定的無聲降級）**仍是 `U1` 的既有硬約束**，
  不因未被選為「最擔心」而放寬——B1 的完成判準已逐條列出 [assumption]

---

# 修訂 1（2026-10-03）— 能力 11／12／13 的四個新 Bolt

**既有 B1–B9 的單元歸屬、完成判準、信心假說與展示全部有效、不回改，編號不動。**
本修訂新增 **B10–B13** 四個 Bolt，Bolt 總數 **9 → 13**，涵蓋 `units-generation` 修訂 4
新增的 7 個單元與 `user-stories` 修訂 1 新增的 11 則故事。

## 一處就地更正：B1 的「做完會證明什麼」第 2 點已變假（`UG-3`）

`bolt-plan.md` 的 B1「做完會證明什麼」第 2 點逐字寫「這是 `[RA:NFR5]` 的承載機制，而
**既有兩道漂移閘門對 WebSocket 完全無效**」。該句在寫下的當天為真，**現在是假的**：
WS 漂移閘門**已交付**——`ws-contract.json`、`backend/services/brain_ws_contract.py`、
`backend/scripts/dump_ws_contract.py`、`backend/tests/test_ws_contract.py`、
`backend/tests/test_dump_ws_contract.py`、`frontend/src/types/ws-contract.d.ts` 全部存在，
`inception/decisions/0019-ws-contract-gates-and-generator-supply-chain.md` 即 ADR-0019。

**更正後的讀法**：`U2` 留在 B1 的理由（讓那道缺失的閘門提早上線）**已經實現**，
不再是待辦；B1 第 2 點要證明的事改為「**新增的 WebSocket 訊息型別已納入既有那份契約**，
故意只改後端訊息模型而不重產型別檔時 CI 仍會紅燈」。**原句不刪**（它是當時據以核可的
紀錄），以本節更正。來源：`units-generation` 修訂 4 的交接事項 `UG-3`，承
`user-stories` 的 `[Q-02]`。

## 編號是識別字，順序是另一張表（`[DP5]` 定案）

**這是本修訂最重要的結構決定，讀者不能依編號推測順序。**

出題時我假設新 Bolt 可以附在尾端，而以腳本逐條對照 DAG 後查出 **6 處順序違反**——
新單元不是疊在既有序列之上，而是**插在它中間**：

| 消費端 | 所在 Bolt | 依賴 | 若新 Bolt 附在尾端 |
|---|---|---|---|
| `U12` work-orchestrator | B4 | `U22` progress-channel | B10 ← 太晚 |
| `U13` brain-gateway | B6 | `U19` membership-service | B11 ← 太晚 |
| `U13` brain-gateway | B6 | `U20` requirement-field-service | B13 ← 太晚 |
| `U13` brain-gateway | B6 | `U22` progress-channel | B10 ← 太晚 |
| `U17` a11y-gate | B8 | `U23` project-pages-ui | B13 ← 太晚 |
| `U17` a11y-gate | B8 | `U24` member-pages-ui | B12 ← 太晚 |

既有本檔把「每條邊的被依賴方都在同一或更早的 Bolt」寫成**以腳本逐條驗證過的硬規則**，
故附在尾端會違反它 6 次。**處置**：Bolt 編號維持為**穩定識別字**（B1–B9 不動，新增
B10–B13），而 2.9 的交付物是下面這份**明列的執行順序**，它把新舊 Bolt 交錯。

不重新編號的理由與 `units-generation` 修訂 4 拒絕插號的理由同形：B1–B9 的編號在本站
五份產出、`units-generation` 的交接表、`contract-design` 與
`risk-and-sequencing-rationale.md` 裡被引用——編號是被引用的識別字，改它要跟著改所有
引用處。

### 執行順序（13 個 Bolt，腳本驗證 46 條邊 0 違反）

```text
B1 → B10 → B2 → B11 → B3 → B12 → B13 → B4 → B5 → B6 → B7 → B8 → B9
```

| 序 | Bolt | 單元 | 完整交付的故事數 |
|---|---|---|---|
| 1 | `B1` | `U1`、`U2`、`U3`、`U6` | 0 |
| 2 | **`B10`** | **`U22`** | **1** |
| 3 | `B2` | `U4`、`U7` | 0 |
| 4 | **`B11`** | **`U18`、`U19`** | **1** |
| 5 | `B3` | `U5`、`U8` | 3 |
| 6 | **`B12`** | **`U24`** | **5** |
| 7 | **`B13`** | **`U20`、`U23`、`U21`** | **4** |
| 8 | `B4` | `U10`、`U12` | 0 |
| 9 | `B5` | `U11` | 1 |
| 10 | `B6` | `U13`、`U14` | **13** |
| 11 | `B7` | `U15`、`U16` | 2 |
| 12 | `B8` | `U17` | 0 |
| 13 | `B9` | `U9`（條件式） | 1 |
| | | **合計** | **31** |

**以上每個數字由同一支腳本從 `unit-of-work-dependency.md` 的 yaml 邊塊與
`unit-of-work-story-map.md` 的主表解析後輸出**（判定方式：該故事**最後**一個單元落在
哪個 Bolt），不是手寫後再核對。驗證結果：24 個單元零遺漏零重複、**46 條邊 0 處順序
違反**、31 則故事全部有歸屬。

**新 Bolt 的最大集中度為 5 則（`B12`）**，沒有製造第二個 B6。B6 的 13 則（原 20 則中的
13，現 31 則中的 13）**本輪刻意不動**（`[DP3]`=A）——拆它需要拆已核可的 `U14`，而
`units-generation` 修訂 4 的前提是既有單元不改名、不插號、不重切。該風險原樣留在
`risk-and-sequencing-rationale.md`，不美化。

---

## B10 — 既有產圖路徑的跨帳號外洩修復

**單元**：`U22` progress-channel

**為什麼排在 B1 之後、B2 之前，而不是附在尾端**（`[DP2]`=A）：它是本輪唯一的**可平行根**
（`depends_on: []`），而它修的是**既有程式的跨帳號內容外洩**——實測一位使用者會收到
另一位使用者產生的架構圖 XML。`US13` 群說明逐字把它定性為 **ADR-0006 的 IAM 面**，
不是效能或整潔問題。它不依賴本 intent 的任何新東西，而 `U12`（B4）與 `U13`（B6）都依賴它。
**這句理由必須被寫下來**：少了它，下游重排時會把 `U22` 當成一個普通的 library 單元。

### 怎樣算做完

- [ ] 進度通道的鍵為 **per-request**，由入口端產生並一路傳遞（`[UG:G7]`=A）。
      **不得**把 `thread_id` 改成 per-request——`design_agent.py:198` 的
      `config = {"configurable": {"thread_id": thread_id}}` 證實它就是 LangGraph
      checkpointer 的 thread 鍵，改它等於關掉對話記憶
- [ ] 請求結束時**移除該鍵**（`ADR-014`）。只寫不刪會把跨使用者錯送換成無上界的記憶體成長
- [ ] 讀取不存在的通道**不崩潰**，且對外錯誤為**固定訊息、不含例外原文**
      （現狀 `design_agent.py:163` 的 `get_nowait()` 拋 `AttributeError`，**且該例外原文
      被送進 SSE 給使用者**——`AC13.1.3`，獨立的 ADR-0006 面）
- [ ] `design_agent.py` 的三個模組層可變狀態處置到位：`:31` `_progress_queue` 刪除、
      `:32` `_last_xml` 刪除、`:169` `memory = MemorySaver()` **保留**（它不是外洩路徑）
- [ ] `wa_collab_orchestrator.py:79` 補傳 per-request 的鍵
- [ ] 併發測試以 **`asyncio.Event` barrier** 釘住交錯順序，**不得以 `sleep` 製造**
      （`frontend/playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky，
      一個 flaky 的併發測試等於沒有測試，`[US:Q-07]`）
- [ ] 斷言兩個重疊請求的事件集合**互斥且各自非空**——非空那一半是必要的，
      否則空集合會讓互斥斷言真空成立（現狀實測 A 收到空、B 收到 A 的產出）
- [ ] `K-18` 契約的「被取代的既有符號」表逐項可 grep 驗證：五個標為刪除或改寫的符號
      在 repo 中不再以舊形式存在

### 做完會證明什麼

**一個今天就存在於生產環境的跨帳號內容外洩被關掉了**，而且是以**隔離**而非加授權的方式
關掉——這是 `FR13.2` 的可觀察面。附帶證明：既有的 `IsolatedAsyncioTestCase` 前例
（`backend/tests/test_langgraph_migration.py`）足以驗併發，**不需新 seam**。

### 展示

兩個瀏覽器分頁同時對不同輸入產圖；兩邊各自只看到自己的 progress 與 xml，
且兩邊的事件集合都非空。先完成的那一邊關閉後，另一邊**仍持續收到**自己的事件。

---

## B11 — 專案中介資料與成員服務

**單元**：`U18` project-meta-data、`U19` membership-service（Bolt 內順序：`U18` → `U19`）

**為什麼排在 B2 之後**：`U18` 的三張新表的 FK 指向 `projects`／`systems`（`U4`，B2），
`U19` 另需 `U7 hierarchy-service`（B2）與 `U3 rbac-story-ids`（B1）。

### 怎樣算做完

- [ ] 三張表建立：`project_members`（含 **NOT NULL 的 `joined_at`**——`FR12.4` 的挑選規則
      直接讀它）、`reselection_events`（含以**事件**為鍵的 `acknowledged_at`）、
      `system_requirement_fields`（`value` **可為 null** ＋ 獨立的 `cleared_at`，
      使「從未填過」與「清空」在資料層可區分，`ADR-015`）
- [ ] **`schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步完成**（`project.md ## Mandated`）
      ——未完成不得標示本 Bolt 完成
- [ ] `system_requirement_fields` 的 DDL COMMENT 寫明 `[UG:G9]`=A 的行為（欄位定義被移除後
      值列保留、畫面不渲染該組、未填計數只統計當前已宣告的欄位）
- [ ] `U3` 擴充為四個 story id（新增 `K3` 成員管理、`K4` 需求欄位），走
      `ensure_missing_role_permissions`（**不可**依賴 `force=False` 的種子），
      並補 **allow/deny 雙向 TestClient**
- [ ] `K-16` 的 facade 是 per-project 授權判定的**唯一**提供者；禁止跳過它直接讀
      `project_members` 表（`sync` 入邊本身是預期且允許的，`ADR-012` 明記這兩件事不同）
- [ ] 「專案不得失去最後一位管理者」的守門位在**三條路徑的共同上游**
      （既有停用端點、自我降級、自我移出），不是三處各寫一次（`[US:D-06]`）
- [ ] **既有停用端點的 409 與 `AdminPage.tsx` 同批交付**——`delivery-planning:c6` 的
      不可分批約束在此**對既有端點成立**（它改既有回應契約且有既有消費端）
- [ ] route decorator **顯式**宣告 `responses={409: ...}`，否則該契約不進 spec、
      前端也產不出型別（實測 `openapi.json` 的 55 個 operation 非 2xx/422 宣告數為 **0**，
      `dump_openapi.py --check` 會保持綠燈）
- [ ] `assert_can_deactivate` **不得削弱**該端點既有的兩道保護：`:645-646` 的自我停用守門、
      `:667-671` 的最後一位可編輯角色的全域管理員守門
- [ ] 自動改選的挑選函式為**不讀 DB 的純函式**，平手以 `(joinedAt, userId)` 決定性
      tie-break，並有 **property-based 測試驗排列不變性**（ADR-0006 的 PBT hard constraint；
      前例 `backend/cost/estimate_readers.py:247-251` 的 `best_clouds`）
- [ ] 改選稽核落在 **UI 讀得到的持久層**（`reselection_events`），
      **不得**只沿用 `user_router.py:213` 的 `_audit_append`（它寫 `logger.info`，UI 讀不到）

### 做完會證明什麼

**`US12.3`「這個專案不會變成沒有人能管」**——三條路徑都被同一個守門擋下。附帶證明：
per-project 授權判定有了單一來源，而既有停用端點的兩道保護沒有因為多一道檢查而失效。

### 展示

建立一個專案後自己是唯一管理者；三條路徑各試一次（在成員詳情頁把自己降級、按移出專案、
請系統管理者停用自己的帳號），三次都被拒並說明原因，第三次的回應是 **409 且列出那些專案**。

---

## B12 — 成員頁與交棒橫幅

**單元**：`U24` member-pages-ui

**為什麼排在 B11 之後、B13 之前**：它依賴 `U19`（B11）與 `U3`（B1）；而 `U17 a11y-gate`
（B8）依賴它，故它必須在 B8 之前。

### 怎樣算做完

- [ ] 成員頁（清單）、成員詳情頁（角色下拉、`[移出專案]`、變更紀錄）、邀請對話框
      （**含拒絕態**——§24 的既有 `(i)` 文案在 `FR12.6a` 之後變成假的，這是對齊修正）
- [ ] 成員清單上**沒有**可直接改角色的控件（`AC12.2.3`）
- [ ] 交棒橫幅落在使用者**自己的落地頁**（**不限入口頁**）——照「入口頁」實作會讓一個
      只有 `C1 view` 的合法成員**永遠看不到**這則通知（`[US:D-17]` 的 Critical）
- [ ] 橫幅**在落地時即存在於 DOM**，或改用等價的 `role="status"` 機制
      （`aria-live="polite"` 在其自述前提下不會被朗讀，`[US:D-11]`）
- [ ] 「知道了」與「查看成員」各有定義的效果：按下任一後橫幅不再出現，
      且該已讀狀態**伺服器持久化**（換裝置重新登入亦不再出現，`AC12.4.4`）
- [ ] 載入態與錯誤態有 live region，**不得**沿用 `AdminPage.tsx:104` 的 4 秒 toast 形狀
- [ ] 前端資料來源走 `AdminPage.tsx` 的兩層抓取形狀
      （`react-hooks/set-state-in-effect` 為 **error** 級，違反即 CI 紅燈）
- [ ] **前端不得自行推導 per-project 判定結論**（`I-5`）——結論由伺服器產生

### 做完會證明什麼

**五則 `US12` 故事一次交付**（`US12.1`／`US12.2`／`US12.4`／`US12.5`／`US12.6`），
含本輪最要緊的那一則 `US12.6`——**成功邀請與成功移出真的改變成員清單**，而不是兩個
沒有後果的按鈕。在它落地之前，其餘九條 `US12` AC 的 Given（「該專案另有成員」）
在資料上**不可構造**。

### 展示

邀請一位具全域權限的同事 → 清單多一列；他登入後看得到這個專案；把他改為管理者 →
變更紀錄顯示誰在何時把角色由什麼改為什麼；移出他 → 清單少一列、他再次讀取被拒；
邀請一位缺全域權限的人 → 當場被拒且清單未新增任何列。

---

## B13 — 需求欄位、專案頁與 MCP 通道

**單元**：`U20` requirement-field-service、`U23` project-pages-ui、`U21` mcp-bridge
（Bolt 內順序：`U20` → `U23` → `U21`）

**為什麼三個一起、且排在 B3 之後 B4 之前**：`U20` 依賴 `U18`／`U19`（B11）與 `U7`（B2）；
`U23` 另依賴 `U8 memory-service`（B3，記憶摘要籤）；而 `U13 brain-gateway`（B6）依賴
`U20`，`U17 a11y-gate`（B8）依賴 `U23`。三者合為一個 Bolt 是因為它們共同湊出一個
可展示的成果（需求頁可用且 agent 讀得到欄位）；單拆 `U20` 只會得到「一個沒有畫面的
端點」。

### 怎樣算做完（**分兩段，第一段不足以標示完成**）

**第一段——現在就可驗（`[DP4]`=A）**：

- [ ] 專案／系統清單頁、建立頁、詳情頁三籤（總覽／需求／記憶摘要）
- [ ] 首次使用時清單頁為**空狀態**（說明 ＋ 建立按鈕），不是一張空表（`AC11.1.2`）
- [ ] 未填欄位以**文字**標示「未填」，**不依賴顏色**（`AC11.2.1`）
- [ ] 總覽籤的未填計數與需求籤的明細**由同一次查詢的結果推導、在同一個回應內回傳**
      （不變量 `I-4`）——e2e 只驗得出「兩個數字相等」，驗不出「同一份來源」，
      故此約束在契約層而非前端
- [ ] 儲存失敗時**輸入值不消失**（`AC11.2.3`）
- [ ] 清空語意：保留列、`value` 設 null、記 `clearedAt` 與 `updatedBy`（`ADR-015`）
- [ ] MCP 工具 schema 的**白名單斷言**：宣告允許的欄位集合，其餘皆不得出現；
      底線斷言為不得出現任何名稱匹配 `token`／`key`／`secret`／`authorization`
      （不分大小寫）的欄位。**斷言必須排除根目錄的 `.mcp.json`**
      （那是 AI-DLC 框架自己的 client 設定，`[US:V-11]`）
- [ ] MCP 代使用者呼叫的 **allow/deny 雙向**：無權專案被拒、有權專案成功
- [ ] MCP server **不得對外暴露、僅供同主機的大腦進程連接**

**第二段——待 `OQ-15`／`OQ-16` 定案後才可驗**：

- [ ] 傳輸層的錯誤語意（連線中斷、逾時、半開連線）——`OQ-16` 定案 stdio 或 HTTP／SSE 之後
- [ ] token 進入該進程的機制與其生命週期——`OQ-15`

> **第一段完成不足以標示本 Bolt 完成。** `X-04` 的契約已自述為**部分契約**；
> `A-7`（MCP 生態可在本 repo 運作）**本 intent 全程未實測**，repo 內零 MCP 基礎設施。
> 不把 `U21` 設為條件式 Bolt（B9 的形狀），因為它承載 `US11.4` 這則 **Must** 故事；
> 不把 `A-7` 列為進入條件，因為它的承接站 `code-generation` 在 Bolt 之內而非之前。

### 做完會證明什麼

**四則 `US11` 故事**（`US11.1`／`US11.2`／`US11.3`／`US11.4`），其中 `US11.4`
是本 intent **唯一**驗證「agent 代我操作時我的身分不會被冒用」的地方——而
`C-T11`（token 不得當工具引數）是 ADR-0006 encryption 面唯一的新落點，
且它**不依賴傳輸形式**，所以第一段就能斷言。

### 展示

在新建的專案底下建一個系統 → 需求籤顯示按 agent 分組的固定欄位、未填者帶文字標示；
填一個欄位並儲存 → 切到總覽籤，未填計數由 N 變 N−1；
以 agent 身分經 MCP 讀一個無權專案的欄位 → 被拒，理由與直接存取時相同；
檢視每個工具的 `inputSchema.properties` → 不含任何憑證名稱的欄位。
