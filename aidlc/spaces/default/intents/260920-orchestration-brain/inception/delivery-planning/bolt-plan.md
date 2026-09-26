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
