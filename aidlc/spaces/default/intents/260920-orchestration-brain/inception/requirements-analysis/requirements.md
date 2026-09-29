# Requirements — 統一入口大腦

<!-- Stage: requirements-analysis（Inception 2.3）· Record: 260920-orchestration-brain
     FR{n} / FR{n}.{m} / NFR{n} 為永久追溯鍵，下游 stage 必須原樣保留，
     不得重新編號或改以散文引用。 -->

## 來源標籤慣例（含一處必須避開的撞號）

| 標籤 | 指向 |
|---|---|
| `[Q<n>]` | intent-capture 的作答 |
| `[F<n>]` | feasibility 的作答 |
| `[S<n>]` | scope-definition 的作答 |
| `[H<n>]` | approval-handoff 的作答 |
| `[R<n>]` | **rough-mockups** 的作答（R1–R8） |
| `[RA:R<n>]` | **本站**的作答（R1–R9） |
| `[線框 §<n>]` | rough-mockups 的 `wireframes.md` 第 n 節（**不是**作答，是線框本身的內容） |
| `[線框 assumption]` | `wireframes.md` 的 `## Assumptions & Open Questions` 條目 |
| `[kb:<檔>]` | codekb `cloud-360` 的該檔（基準 `dc4b687`，2026-09-24 重建）。可指向該 store 的任一份，不限本站宣告消費的三份 |
| `[desc]` | `project-description.json` 的原始需求敘述（使用者的原話） |
| `[memory:M<n>]` | `aidlc/spaces/default/memory/` 的規則層 |
| `[C-T<n>]`／`[C-O<n>]`／`[C-S<n>]`／`[C-R<n>]` | `constraint-register.md` 的約束 id |
| `[raid-log <id>]` | `raid-log.md` 的風險／假設／依賴 id |
| `[本站自檢]` | 本站的送審前自檢或矛盾／覆蓋檢查所得，非上游來源 |
| `[user-flow Flow <n>]` | rough-mockups 的 `user-flow.md` 第 n 條流程（**與 `[線框 §n]` 是不同的檔案**） |
| `[project.md …]`／`[team.md …]` | 規則層的具名條款 |
| `[initiative-brief 交接表]` | approval-handoff 的 12 列交接表 |
| `[feasibility <id>]` | `feasibility-assessment.md` 的具名項（如假設 A-2） |
| `[ADR-<n> …]` | 該 ADR 的具名面向 |
| `[H<n> 形狀]` | 借用某題定下的**處置形狀**（非其內容）——目前僅 `[H4 形狀]`（CONDITIONAL 站須附轉移目標） |
| `[本站修訂 <n> 的人工裁決]` | 本站在核可關卡上取得的人工裁決（修訂 2 起使用） |

**證據標記**（`[讀]`／`[簽]`／`[算]`／`[未驗]`）是**另一套正交的標記**，不是來源
標籤：它標的是「這個事實怎麼取得的」，而非「這個主張來自哪份文件」。兩者會同時
出現，例如 `[kb:architecture `[讀]`]` 意為「來自 codekb 的 architecture.md，
且該事實是實際開檔讀過的」。[R-09 的修正]

<!-- R-19 的修正：此處原寫「全檔共 25 處證據標記」。該計數已刪除而非改正——
     它的值取決於「說明段與 A-6 的元敘述算不算在內」這個任意的範圍選擇（全檔 31、
     扣說明段 26、審查採較窄範圍得 22 與 21），而它不承載任何下游判讀。
     一個四種合理算法各有不同答案、又沒人讀的數字，正確處置是移除。 -->


**撞號警告**：rough-mockups 與本站都用 `R1`–`R8` 編號。本站的作答一律加
`RA:` 前綴引用，**下游引用時務必看前綴**——`[R6]` 是「另開新對話的入口由脈絡
元件承載」，`[RA:R6]` 是「大腦 WS 不照抄既有前例」，兩者完全不同。

**codekb 證據強度**：引用 codekb 的事實一併帶其原始證據標記——`[讀]` 實際開檔
讀過、`[簽]` 僅取簽章、`[算]` 由指令計算、`[未驗]` 本輪未複驗。codekb 本輪為
Full rescan（廣度）＋ `kind: partial`（深度），33 個路徑實讀，**不得把它的任何
一節讀成「整個 repo 都被讀過」**。

---

## Intent Analysis

使用者要達成的目標，不是功能清單：

1. **讓使用者不必先知道該用哪個功能。** 目前 Cloud-360 的 AI 能力分散在
   `/workspace`（A1 產圖）、`/assessment`（A3 評核）、`/cost`（C1 估價）三個
   獨立入口，使用者得自己判斷該去哪一頁 [Q1][kb:business-overview `[讀]`]。
2. **讓上下文在頁面之間不斷掉。** 在某一頁講過的對象與意圖，換頁後要重講一次
   [Q1]。
3. **讓能力可以組合。** 一個需求需要多個功能接力時，目前沒有任何機制能把它
   拆成幾件工作並分派出去 [Q1]。

達成這三項的前提是系統能指出**使用者當下正在處理哪一個對象**，本次以
「專案 → 系統 → 架構圖」三層識別並記錄 [Q5]。

**本次不做的**：不新建成本計算能力（編排既有的 `/api/cost/v1`）[Q12]；不納入
「跨雲分析（by 專案）」[Q12]；不建本平台自身 LLM 花費的計量與 admin 設定 [F13]。

---

## Functional Requirements

### FR1 — 統一入口的意圖識別與工作交辦（能力 1，Must）

- **FR1.1** 系統應在統一入口頁接受使用者的自然語言輸入，判定其意圖類別，並把
  工作交辦給對應的既有功能能力。[Q1][S9]
- **FR1.2** 交辦結果應在畫面上以可見的工作項呈現，每個工作項帶一個狀態。
  狀態值集合為**五個**：`處理中`／`等待中`／`完成`／`失敗`／`已停掉`。
  [線框 §8][線框 §13][線框 assumption]
  - `等待中` 用於「依賴前一項先完成才算得準」的工作項（線框 §8 的第 2 項即此形狀）。
  - `已停掉` 用於使用者更正後該項必須呈現的終止狀態（由線框 §13 引入）。
  - 實際狀態機（轉換條件與終端性）待下游定案；本站只鎖定**狀態值集合不得少於
    這五個**。
- **FR1.3** 當意圖判定的信心未達門檻時，系統**不得交辦、不得產生任何結果**，
  應列出候選判讀並反問使用者。[線框 §12]
- **FR1.4** 使用者得對已交辦的工作項逐項更正（「不是這個」）。更正後該工作項
  應轉為**可見的終止狀態**，且畫面應明講原本那件**有沒有留下東西**。
  更正為逐項，其餘工作項不受影響。[線框 §13]
- **FR1.5** 判定意圖前應執行既有的平台自我竄改預檢（`prompt_guard` 形狀）；
  命中則不呼叫 LLM，回固定拒絕訊息。[project.md `## Mandated`][kb:architecture `[讀]`]
- **FR1.6** 路由層**必須輸出一個可與門檻比較的信心值**，定義域 0–1。
  這是一條獨立需求，不是 FR1.3 的前提句——若實作出一個不輸出信心值的路由層，
  FR1.3 會**靜默永不觸發**，而文件上看起來已解決。[本站自檢][線框 assumption]
  - 上游已登記此事的不確定性：線框的 assumption 逐字寫「該訊號是否存在取決於
    路由層模型——校準過的信心分數是某些模型的原生輸出，另一些只能自陳（自陳值
    未必校準）」，並把它與路由層選型一同指派 `nfr-requirements`。本站不重複
    指派，改為把「必須輸出」升為需求，使選型時這是一項**硬條件**而非偏好。
  - 上游同時給了替代表達：若最終模型無法提供可用的信心訊號，FR1.3 的觸發條件
    得改以其他可判定條件表達（例如**候選意圖並列且無單一最高分**），畫面不變。
    採用替代表達時 FR1.7 的數值門檻隨之不適用，須改寫為該條件的判定規則。見 OQ-10。
- **FR1.7** 信心門檻的初版設定值為 **0.7**。判定為二元：`信心值 < 0.7` 即進入
  FR1.3 的反問路徑，否則交辦。門檻為**設定值**而非常數，得依 NFR1 的校正程序
  調整。[線框 assumption 逐字把「信心低於多少才不交辦」指派給 requirements-analysis]
  - 0.7 與 NFR1 的 80% 同屬**無實證基礎的工程判斷**，理由與代價見 A-3。
- **FR1.8** 統一入口頁應有**自己的 RBAC story id**，並置於既有
  `DefaultRedirect` 權限瀑布之**首**：有該權限者 `/` 導入口頁，沒有的沿用現行
  瀑布順序落地（`canArch('view')` → `/workspace` → `can('A3','view')` →
  `/assessment` → `can('C1','view')` → `/cost` → `can('J3a','view')` →
  `/admin/users` → `can('J3b','view')` → `/admin/role-permissions`），**皆不符
  者仍導 `/403`，不得繞過**。無該權限時 Sidebar 不顯示入口項目。[R8]
  - **不存在「無權限的入口頁」畫面**——該狀態不可達。[R8][user-flow Flow 4]
  - **此為 `role_permissions` seed 語意變更**，連帶觸發兩條 blocking 規則：
    `team.md` 的 allow/deny 雙向測試（有該權限 → 2xx／導入口頁；無該權限 →
    不得到達入口頁且落地順序正確），以及 `project.md` 的 `schema_rbac.sql` ＋
    `DEPLOY.md` 同步。[R8 的作答後果段逐字：「此為本站定案所引入的下游義務，
    需由 requirements-analysis 以後的站承接」]
  - 具體的 story id 字串與哪些角色預設持有該權限，見 OQ-11。

### FR2 — 跨功能共享的對話脈絡與自動切換（能力 2，Must）

- **FR2.1** 同一段對話脈絡應可跨統一入口、`/workspace`、`/assessment` 三處延續；
  **不含** `/admin/*` 與 `/cost`。[Q7]
- **FR2.2** 切換到子功能頁時，脈絡列應顯示**同一個**作業對象（專案／系統／
  架構圖），使用者不需重講。[R3]
- **FR2.3** 作業對象的識別與記錄應以「專案 → 系統 → 架構圖」三層為單位。[Q5]

### FR3 — 子功能頁另開新對話（能力 3，Must）

- **FR3.1** 使用者得在 `/workspace` 與 `/assessment` 由脈絡元件開啟一段新對話。
  [R6]
- **FR3.2** 新對話**不共享任何訊息歷程**，但**沿用當前的作業對象**。
  可測不變量：新對話的第一則訊息即可指涉「這張圖」而不需重新指定。[RA:R4]
- **FR3.3** 使用者得隨時切回共享對話。切回時獨立那段的內容如何處置未定
  （見 Open Questions）。

### FR4 — 長短期記憶（能力 4，Must）

- **FR4.1** 系統應提供三種記憶：語意記憶（semantic）、程序記憶（procedure）、
  情節記憶（episodic，by user）。[Q9]
- **FR4.2** 三者應落在**同一個 PostgreSQL database 的獨立 schema**，以保留原生
  跨 schema join 能力。[F3]
- **FR4.3** 記憶層應內建最小權限模型（記憶列帶擁有者與可見範圍欄位），讀取一律
  經過該模型；介接的應用系統以自身角色映射到這組欄位。[F9]
- **FR4.3a**（**寫入端**）記憶列的**擁有者**欄位應由記憶層在寫入時依**呼叫者的
  已驗證身分**設定，**不得由呼叫方自行指定**。[本站自檢]
- **FR4.3b**（**寫入端**）記憶列的**可見範圍**欄位的預設值應為最窄（僅擁有者
  可見）。放寬可見範圍為一個**獨立的、需授權的操作**，且**每次變更須留稽核
  紀錄**（誰、何時、由什麼範圍改為什麼範圍）。[本站自檢][ADR-0006 IAM ＋ audit logging]
  - 未指名寫入端的後果是安全相關的：任何介接系統都能自行把一列記憶標成較寬的
    可見範圍。A-5 談的是介接系統如何映射自身角色去**讀**，不涵蓋誰能**寫**。
  - 「哪些角色得放寬可見範圍」見 OQ-12。
- **FR4.4** 資料庫層的邊界以「grant 只開放記憶 schema」承載。[F3]
- **FR4.5** episodic memory 保存 **90 天**，逾期自動刪除。[RA:R2]
- **FR4.5a**（**承載形式**）「逾期自動刪除」為**排程觸發、無人在迴圈內**的流程
  自動化，因此依 `project.md ## Forbidden` **必須以 gh-aw 或 GitHub Actions
  workflow 承載，不得以 `backend/` 內新增的排程程式承載**。該條禁令的邊界判準
  逐字為「由事件或排程觸發、無人在迴圈內的（`on: push`／`pull_request`／
  `schedule`／`workflow_dispatch` 等）屬本條禁止範圍」——90 天清除正落在其中。
  [project.md `## Forbidden`][本站自檢]
  - 決定性的映射邏輯（算出哪些列逾期、發出刪除）應放在**純 Actions 步驟**，
    不交給 gh-aw 的 LLM 路徑——本 repo 三塊結構性盲區之一正是「所有 LLM 路徑」。
    [project.md `## Forbidden` 同條的附註]
  - 清除動作本身仍須留稽核紀錄（承 FR4.7）。
  - workflow 的具體落點與其取得資料庫連線的方式見 OQ-13。
- **FR4.6** 使用者得自行刪除自己的記憶。[F5]
- **FR4.7** 記憶的**刪除動作本身**應留下稽核紀錄（否則稽核需求與刪除權互相
  抵消）。[F5][C-R2][raid-log R-7]

### FR5 — 多意圖識別（能力 5，Must）

- **FR5.1** 一句含 N 個可分離意圖的輸入，應產生 **N 個各自帶可見狀態的工作項**。
  可測不變量：輸入「改架構圖加 Redis 快取，然後估一下成本差額」應產生 2 個
  工作項，各自有獨立狀態。[本站直接定義，於摘要確認時呈現][線框 §8]
- **FR5.2** 多意圖情境下的更正為**逐項**（承 FR1.4）。

### FR6 — 多輪對話（能力 6，Must）

- **FR6.1** 第 N 輪應能正確解析指向第 N−1 輪產出的指涉詞（「那個」「剛剛那張圖」）。
  可測不變量：第一輪產出一張圖後，第二輪說「把那張圖的資料庫換成 Aurora」
  應作用在該張圖上，不需重新指定。[本站直接定義，於摘要確認時呈現]

### FR7 — 主動通知推播（能力 7，**Should**）

- **FR7.1** 系統應在**使用者自己交辦的長時工作**完成或失敗時推播通知，接收
  對象為**交辦者本人**。[RA:R3]
- **FR7.2** 推播通道即 FR8 的 WebSocket。[F4]
- **FR7.3** 推播的終態集合對齊既有成本 job 的三種終態：`completed`、`failed`、
  `timeout`。[RA:R3][kb:architecture `[讀]` `advice_stream_router.py:81–158`]
- **FR7.4** 本項為唯一的 Should；未交付時 FR8 仍須獨立成立。[S9][S11]

### FR8 — 串流式互動（能力 8，Must）

- **FR8.1** 大腦的回覆應逐步顯示，不得等整段產生完才送出。[Q9]
- **FR8.2** 傳輸機制為 **WebSocket**；既有 5 個 SSE 端點不在本次變更範圍。
  [F4][kb:api-documentation `[算]`——既有為 **5** 個 SSE 端點，`team.md` 記載的
  「3 個」是前端消費點數，非後端表面]
- **FR8.3** WebSocket 端點必須掛在 `/api/` 之下（`location /` 走
  `try_files … /index.html`，握手落在那裡會拿到 HTML）。
  [kb:architecture 約束一 `[讀]`]
- **FR8.4** 大腦的 WebSocket **必須更新** `users.last_activity_at`（即不得沿用
  既有前例的 `record=False`）。可測不變量：經大腦互動後，Admin 頁的最後活動
  時間應更新；節流仍為既有的 5 分鐘。[RA:R6][kb:architecture 約束三 `[讀]`]
- **FR8.5** 認證 token **不得放在 query string**，應走 `Sec-WebSocket-Protocol`
  標頭或握手後首則訊息。[RA:R6]

### FR9 — 專案 → 系統 → 架構圖 階層（能力 9，Must）

- **FR9.1** 系統應建立「一個專案有多個系統、一個系統對應一份架構圖檔與其中
  多張圖」的資料模型。[Q5][desc]
- **FR9.2** 既有架構圖（目前直接掛在使用者底下，`users → user_diagrams` 加
  `diagram_shares` 多對多）應能遷入新階層。[Q5][kb:business-overview `[讀]` `models.py:25–30,91–105`]
- **FR9.3** 遷移的歸屬規則、遷移步驟與回復方式由 `domain-design`（2.6）產出；
  若該站被 skip，義務轉移至 `units-generation`（2.7）。[H3][initiative-brief 交接表]
- **FR9.4** 跨雲分析為**專案層級**的面向，但本次不納入。[Q12][desc]
- **FR9.5**（**存取控制，本輪補**）`projects` 與 `systems` 的讀、建立、修改、
  刪除**一律經 `require_story_action`**，不得有任何繞過該 dependency 的路徑
  （含同進程直呼 service 層）。這是本 repo 的既有形狀：所有存取都走該
  dependency，新核心資料模型不得例外。[本站自檢][kb:architecture `[讀]` `rbac.py:255–280`]
  - **建立路徑必須存在且被指名**：已核可線框第 3 節有「[切換對象]」（選取既有
    對象）的控件，但**沒有建立路徑**；沒有建立路徑，FR9.1 的資料模型就只有
    FR9.2 的遷移能產生資料。本站要求建立路徑為顯性需求，不得留給實作推斷。
  - 具體的 story id、哪些角色得建立／修改／刪除專案與系統、以及是否沿用
    `diagram_shares` 形狀的多對多分享，見 OQ-14。
  - 此項與 FR1.8 同屬 ADR-0006 IAM 面向的落點，兩者皆為本輪補入。

### FR10 — 成本／FinOps 能力的編排（能力 10，Must）

- **FR10.1** 大腦應辨識成本類需求，並路由到**既有的** `/api/cost/v1`。[Q12]
- **FR10.2** 呼叫一律走 **HTTP 並帶使用者的 token**，使既有的
  `require_story_action("C1", …)` dependency 照常執行。**不得以同進程呼叫
  service 層繞過該授權**——`estimate_intake_service` 內無第二道角色檢查。
  [F14][C-S5][kb:architecture `[讀]`]
- **FR10.3** 稽核的行為主體為**使用者本人**，不是大腦。[F14]
- **FR10.4** 大腦應把成本 job 的狀態事件（`progress` / `completed` / `failed` /
  `timeout` / `heartbeat`）轉譯進自己的訊息流；**不得等 job 完成才開始回覆**。
  [F15][C-S6]
- **FR10.5** `timeout` 與 `failed` 兩種終態各須有可見訊息，使用者能分辨
  「還在跑」與「已失敗」。[raid-log R-9]
- **FR10.6** `progress` 以**單一則就地更新**的訊息呈現；`completed` 後該則訊息
  被**結構化卡片**取代，卡片附連往成本頁的連結。[R5][R4]
- **FR10.7** 成本答案**就地在入口頁呈現**，使用者不需離開入口頁。[Q14]
- **FR10.8** 大腦不得對成本能力做 token 級的巢狀串流轉送——來源端沒有逐字可轉
  （C1 的「串流」是每秒輪詢 DB 的狀態事件，真正的 LLM 呼叫是同步 `invoke`）。
  [C-T10][kb:architecture `[讀]` `cost_advice_agent.py:156`]

---

## Non-Functional Requirements

### NFR1 — 意圖識別準確率

**≥ 80%**，對一組 **≥ 50 筆人工標註的輸入**量測。[RA:R1]

- **量測母體**：該 ≥ 50 筆標註集，每筆為「一句使用者輸入 → 應交辦給哪一個功能
  能力」的配對。
- **判定方式**：系統實際交辦的目標與標註目標相同即為命中；準確率＝命中數 ÷ 總數。
  多意圖輸入（FR5.1）以**逐工作項**計分，一句話產生 N 個工作項即貢獻 N 筆判定。
- **標註集**由 `user-stories`（2.4）產生，與該站的 Given/When/Then 同源。[RA:R9]
  - **`user-stories` 為 `CONDITIONAL`**（本輪查證，非 ALWAYS）。若它被判定不適用
    而 skip，標註集的產生義務**自動轉移**至 `build-and-test`（3.6，
    `execution: ALWAYS`）；確認者是屆時執行該站者。缺這條轉移規則，`[RA:R9]`
    的指派會在 skip 當下無聲落空，而 NFR1 隨之不可驗證。[本站自檢]
- **量測機制**（跑標註集、算準確率、輸出數字）由 `build-and-test`（3.6，
  `execution: ALWAYS`）承載。選這一站是因為它**不可能被 skip**（本輪查證
  `stage-graph.json` 確認），且量測機制本質是一組測試。[本站自檢]
- **校正程序（R-08 補，R-15 擴充適用範圍）**：本程序**同時涵蓋四個無實證基礎的
  數值**——NFR1 的 80%、FR1.7 的信心門檻 0.7、NFR2 的 95%、NFR3 的 2 秒。
  首次實測後任一項未達標時，處置**不是自動改寫門檻**。判準與權責為：由**決策者**
  在 `build-and-test` 的核可關卡裁決，三種處置——(a) 接受實測值為新門檻並記錄
  理由、(b) 維持原值並要求改善後重測、(c) 判定門檻本身設錯並重定。
  - **連動條款（落實 A-7）**：**調整 NFR1 的 80% 時必須同時處理 FR1.7 的 0.7，
    兩者不得分開調**。理由是它們會互相補償：調高信心門檻會讓系統多反問、少交辦，
    準確率的帳面數字因此上升，但那不是識別變準了。裁決紀錄必須同時寫出兩個值
    的新舊對照，只改一個即為無效的校正。
  - **各項的驗收立場**：校正前，第一版對四項的立場**一律是「未達標即為驗收
    未通過」**，不得因為「門檻本來就沒有依據」而視為已通過。NFR2 與 NFR3 先前
    未寫校正立場，本輪補齊（R-15）。
  [本站自檢][A-7]

### NFR2 — 跨頁面上下文保留率

**≥ 95%**：切換功能後系統仍正確指向同一個作業對象、使用者不需重講的比例。
[RA:R1][Q3]

- **量測母體（R-04 補）**：一次量測為一個**頁面切換事件**——使用者在共享工作
  階段涵蓋的三處（入口頁、`/workspace`、`/assessment`，見 FR2.1）之間切換一次。
  分母為切換事件總數，分子為切換後脈絡列仍正確指向切換前同一個「專案／系統／
  架構圖」三元組的事件數。
- **判定方式**：切換後脈絡列顯示的三元組與切換前**逐欄相同**即為命中。
  「使用者不需重講」以此為代理指標，不另行量測使用者行為。
- **量測機制（R-14 修正）**：比率**不能**由 `ui-regression` 的既有閘門承載——
  `team.md` 記載它讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`，
  只能產出「全過／失敗」，產不出 95%，照字面執行實際門檻會變成 100%。
  正確形狀為：**一組具名的 N 個切換情境，全部放在同一個 Playwright `test()`
  之內**。該 test 內部逐一走完 N 個情境，以**自行計數**記錄每個情境的通過與否
  ——逐情境以 `try`／布林值捕捉結果，**不對單一情境下任何 `expect` 或
  `expect.soft`**——最後**只對比率下一次斷言**：`通過數 / N ≥ 0.95`。
  落點 `build-and-test`（3.6，`ALWAYS`）。
  - **約束句**：單一情境失敗**不得使該 test 被判為失敗**（不是「不得中止」——
    在 Playwright 下這兩者不是同一件事，見下）。
  - **`expect.soft()` 不適用於本條**：它**不中止**測試，但**仍會把該 test 判為
    失敗**。因此若逐情境以 soft assertion 記錄，只要有一個情境未通過，該 test
    即失敗、`.stats.unexpected` 非 0、`ui-regression` 隨即 `exit 1`——**比率斷言
    是否通過完全不影響結果，門檻回到 100%**，正是本條要消除的形狀。只有「自行
    計數」能真正讓 0.95 成為門檻。[R-20 的修正]
  - **為什麼必須是「同一個 `test()` 內、只斷言一次」**：本 repo 的 e2e 全部在
    同一次 `npx playwright test` 中執行（`ui-regression.md:191`），而該 workflow
    讀 `pw-report.json` 的 `.stats.unexpected`、非 0 即 `exit 1`（同檔 281–284 行）。
    **若把每個情境寫成各自的 `test()`，任一情境失敗就會讓 `.stats.unexpected`
    非 0，門檻實際上回到 100%**，比率門檻無從表達。
  - **「寫成一支獨立於該判定之外的測試」在本 repo 不可行**（修訂 2 的寫法照字面
    不成立，此為 R-14 的第二次修正）：`frontend/playwright.config.ts` 只有一個
    `chromium` project 且 `testDir: './tests/e2e'`，同目錄下的測試無法豁免於
    該次執行的統計；而 Playwright 是前端唯一的瀏覽器自動化層
    （`team.md ## Testing Posture`），沒有第二個載體可選。
  - 因此 `.stats.unexpected` 在本 NFR 下的語意是：**只有比率未達 0.95 時才計為
    unexpected**；單一情境失敗只反映在該 test 內部的計數上。
  - N 的具體值與情境清單由 `user-stories`（2.4）產生；skip 時轉移
    `build-and-test`（3.6）——同 NFR1 的轉移規則。
  - **NFR11 不受此限**：它的判定是「每個情境的切換次數都嚴格少於基準」，屬全體
    量化條件，可以寫成各自的 `test()`（任一情境未達即應整體失敗）。兩條 NFR 的
    量測形狀不同，**不得互相套用**。
  [本站自檢][team.md `## Testing Posture` C 規則與 `## Deployment` 的 ui-regression 記載]
- **「頁面切換次數下降」已移出本條，改為獨立的 NFR11**（不是移除）。理由：
  這條 NFR 的判準是**比率**，而切換次數的判準是**次數**，兩者不可互相替代；
  併在一條內會讓「這條達標了嗎」同時指涉兩種判準。**上游把它記為成功指標的
  組成部分**（`intent-statement.md` 逐字：「第一版要以下列**三項可量測結果**
  判斷是否成功」，且跨頁面上下文保留率那一項逐字寫「**本項一併涵蓋**『完成
  一個跨功能任務所需的頁面切換次數下降』」），故它必須有落點，見 NFR11。
  [Q3][本站修訂 2 的人工裁決]

### NFR3 — 首字回應時間

**P50 ≤ 2 秒**（從使用者送出到畫面出現第一個字）。[RA:R1]

- **量測母體（R-04 補）**：入口頁的每一次使用者送出。分母為送出次數，統計量為
  「送出時刻 → WebSocket 收到第一個內容 token 的時刻」的 P50。
- **判定方式**：伺服器端以該兩個時刻的差計時，不含使用者的網路往返；
  以 P50 為門檻（非平均值），避免長尾把判定拉歪。
- **量測機制**：同 NFR1／NFR2，落點 `build-and-test`（3.6）。[本站自檢]
- **校正立場**：同 NFR1 的校正程序。

**與 NFR10 的連動（必讀）**：這條預算幾乎全部被**路由層的 LLM 呼叫**吃掉。
FR4 的 Redis 往返在同一個 compose 網路內約 1ms，可忽略；真正的成本是「大腦
先判意圖、再交辦」這個兩段式流程的第一段。因此本 NFR 能否達成，實質上由
**路由層的模型選擇**決定——即 `initiative-brief.md` 交接表第 11 列
（`typesafe/jev-1.13`，指派 `nfr-requirements`）的主題。兩者必須互相引用。
[本站的矛盾／覆蓋檢查]

### NFR4 — 狀態外部化與重啟還原

大腦的 session 與工作狀態**一律放 Redis，不得放行程記憶體**。[RA:R7]

可測不變量：**重啟 backend 後，既有對話的脈絡與作業對象仍可完整還原。**

既有三處行程內狀態容器（`collab_router` 的連線字典、`advice_orchestrator` 的
`_executor`／`_progress`／`_inflight`、`pricing_client` 的磁碟快取）**不在本
intent 範圍內**，維持原狀。[RA:R7][kb:architecture 約束四 `[讀]`]

### NFR5 — WebSocket 契約閘門

新 WebSocket 應有一份**前後端共用的訊息型別契約來源**，並有一個 **CI 檢查
斷言兩端一致**。[RA:R5]

理由是機械事實而非偏好：`/api/collab/ws/...` 存在於程式但**不在 `openapi.json`
的 42 個 path 內**（FastAPI 不登錄 websocket route），故 `dump_openapi.py --check`
與 `npm run check:types` 兩道既有漂移閘門**對 WebSocket 完全無效**。
[kb:architecture 約束二 `[算]`]

### NFR6 — 記憶層的 schema 隔離與其驗證

FR4.2 的「獨立 schema」應有一個**對真實 PostgreSQL 執行的 CI job**
（`postgres:16-alpine` 作為 service container）驗證，範圍限於：schema 建立、
grant 邊界、跨 schema 查詢。[RA:R8]

理由同樣是機械事實：全樹零 `CREATE SCHEMA`、零 `search_path`，而既有測試在
`tests/helpers.py` 以 `sys.modules.setdefault("psycopg2", MagicMock())` 換掉驅動、
改走 in-memory SQLite——**SQLite 沒有 PostgreSQL 的 schema 概念**，現有測試
基礎設施對 FR4.2 沒有任何驗證路徑。[kb:architecture 約束七 `[算]`/`[簽]`]

### NFR7 — episodic memory 的保存與刪除稽核

保存 90 天（FR4.5）；刪除動作留稽核（FR4.7）。episodic memory 為 by-user 的
對話歷程，屬個人可識別的使用歷程，其靜態儲存與傳輸的加密要求須於設計階段
明確。[RA:R2][F5][feasibility ADR-0006 encryption 面向]

### NFR8 — 新增元件的部署設定完整性

Redis 作為第 5 個容器引入時，其新增的環境變數**必須在同一個 PR 內**讓
`deploy/render-env.sh` 寫它、`deploy/.env.example` 列它。[F2][C-O1]

理由是此失敗模式**無聲**：無 fallback 的變數缺值時只會變成空字串，服務照常
啟動但功能降級（既有實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次
部署的架構圖 icons 靜默退回灰底佔位圖）。另：憑證值不得含 `$`。
[project.md `## Mandated`][kb:architecture 約束八 `[讀]`]

### NFR9 — 成本原則

本平台自身的 LLM 花費上限由 **OpenRouter 後台**承載，本 intent 不建計量或
admin 設定機制。[F13] 編排層以「盡量省」為設計原則：優先選便宜快速的模型，
昂貴模型只用在真正需要處。此為設計原則，**非可量測的門檻**。[F11][C-O4]

### NFR10 — 路由層模型的可替換性

編排層（意圖識別）與功能 agent **得使用不同模型**。[F1]

`typesafe/jev-1.13` 為路由層候選，於 `nfr-requirements`（3.2）在有實測準確率與
延遲基準後決定。若該站被 skip，本工作流程**沒有自然承接站**，屆時判定 skip 的
執行者必須把它重新提交給使用者裁決。[initiative-brief 交接表第 11 列][H4 形狀]

---

### NFR11 — 跨功能任務的頁面切換次數

完成一個跨功能任務所需的**頁面切換次數**應**嚴格少於**現行流程的基準值。
[Q3][本站修訂 2 的人工裁決]

- **量測母體**：一組**具名的跨功能任務情境**（例如「依需求改一張架構圖，然後
  取得改動後的成本差額」）。情境集合由 `user-stories`（2.4）與該站的故事同源
  產生；`user-stories` 為 `CONDITIONAL`，skip 時義務轉移至
  `build-and-test`（3.6，`ALWAYS`）——與 NFR1 的標註集同一條轉移規則。
- **基準值**：每個情境在**現行 UI**（無大腦）下所需的切換次數，由人工依現行
  11 條路由實際清點得出，不是估計值。[kb:code-structure `[讀]` `App.tsx:35–135`]
- **判定方式**：對每個情境比較「有大腦」與「現行」兩者的切換次數；
  **每一個情境都必須嚴格少於其基準值**才算達標。二元可判，且不需要發明一個
  百分比——改善幅度是結果，不是門檻。
- **量測機制**：以 Playwright e2e 走完每個情境並計數頁面切換（`App.tsx` 的
  路由變更次數），落點 `build-and-test`（3.6）。這條用次數而非比率，
  因此**與 e2e 的二元閘門相容**（每個情境是一個斷言：切換次數 < 基準值）。
- **校正立場**：同 NFR1 的校正程序（見該節）。若某情境的切換次數無法少於基準，
  處置是由決策者裁決該情境是否屬於大腦的設計目標，不得自動放寬門檻。

**本輪修訂紀錄（R-10）**：修訂 1 把這個子句從 NFR2 **刪除**，並在刪除說明中
稱它「改列為 `intent-statement.md` 已記載的預期成果」——**該說法與上游原文
不符**：上游把它記為三項可量測結果之一的組成部分，不是軟性預期成果。審查逐字
核對後判為 Critical。修訂 2 依人工裁決**恢復為獨立的 NFR11**，並給它原本缺少的
母體、基準與門檻。

---

## ADR-0006 Security Baseline 四面向逐項判定

`project.md` 明列此為 hard constraint，四面向缺一不可；判定為不適用者亦須附理由。

| 面向 | 判定 | 本站的具體要求 |
|---|---|---|
| **IAM** | **適用** | **FR1.8（本輪補）**：統一入口頁有自己的 story id、置於權限瀑布之首、無權限者不得繞過 `/403`——這是本 intent 新增的**唯一使用者入口**，其授權落點；屬 `role_permissions` seed 變更。**FR9.5（本輪補）**：`projects`／`systems` 的讀寫刪一律經 `require_story_action`，且建立路徑須被指名。**FR4.3／FR4.4／FR4.3a／FR4.3b**：記憶層兩層授權（DB grant 鎖到 schema ＋ 記憶列的擁有者與可見範圍），且**寫入端**已指名——擁有者由記憶層依已驗證身分設定、可見範圍預設最窄、放寬為需授權且留稽核的獨立操作。**FR10.2**：大腦代呼叫成本能力一律走 HTTP 帶使用者 token，**不得**同進程繞過 `require_story_action`。另：Redis 連線憑證須最小權限 |
| **Encryption** | **適用** | NFR7：episodic memory 為 by-user 對話歷程，其靜態儲存與傳輸加密要求須於設計階段明確（OQ-3）。本站不預選手段 |
| **Network exposure** | **適用** | FR8.3（WS 必須掛在 `/api/` 之下）；FR8.5（**token 不得進 query string**——既有前例會讓 token 進 nginx 與 cloudflared 的 access log）；Redis 容器對外暴露面必須為零，僅限 compose 內部網路 |
| **Audit logging** | **適用** | FR4.7（記憶刪除須留稽核）；**FR4.3b（本輪補）**（可見範圍變更須留稽核）；FR10.3（成本稽核的行為主體為使用者本人）；FR8.4（大腦 WS 必須更新 `last_activity_at`，否則既有的帳號活動稽核對大腦使用者靜默失效） |

四面向皆適用，無不適用項。

**本輪修訂紀錄**：IAM 列原先只列了記憶層、成本代呼叫與 Redis 憑證，**漏掉本
intent 新增的唯一使用者入口（入口頁）與新核心資料模型（`projects`／`systems`）
的授權落點**，卻仍宣稱「四面向皆適用，無不適用項」。該漏項由審查的 R-01／R-03
查出；FR1.8、FR9.5、FR4.3a、FR4.3b 為本輪補入的對應需求。

---

## Constraints

承自 `constraint-register.md`，本站不重新開放，僅列出對本站需求最有約束力者：

| ID | 約束 | 對應需求 |
|---|---|---|
| `C-T3` | 新增或變更端點連動兩道機械檢查（`openapi.json` 漂移、前端 `api.d.ts` 重產） | FR10.1 若新增 REST 端點；**NFR5 指出 WS 不受這兩道保護** |
| `C-T5` | 現用 `postgres:16-alpine` 不含 pgvector | 語意記憶若採向量檢索需換映像（見 Open Questions） |
| `C-T6` | `schema_rbac.sql` 只在**空 data volume** 執行 | FR9.2 的既有環境遷移必須手動；且該檔 L319 有裸的 `DELETE FROM role_permissions;`，對既有 staging 重跑會抹掉管理者的人工調整 [kb:architecture 約束六 `[讀]`] |
| `C-T8` | PostgreSQL 不支援跨 database 查詢 | FR4.2 的落點因此是「同一 database、獨立 schema」 |
| `C-T10` | 成本 agent 的回覆為非同步 job，其 SSE 為狀態事件而非 token 串流 | FR10.4／FR10.8 |
| `C-O1` | **blocking**：新增 compose 變數須同 PR 寫入 `render-env.sh` 與 `.env.example` | NFR8 |
| `C-O2` | **blocking**：資料庫結構變更時 `schema_rbac.sql` 與 `DEPLOY.md` 必須同步 | FR4.2、FR9.1 |
| `C-S5` | 大腦呼叫成本能力一律走 HTTP 帶 token，不得繞過授權 | FR10.2 |
| `C-S7` | 大腦自建 LangGraph 執行層，與既有 `services/langgraph_runtime.py` 並行；**附帶義務**是須有鎖住兩者一致性的驗證 | 落點 `contract-design`（2.8）[H4] |
| `C-R1` | 只部署至自有 staging，無外部法規框架適用 | 本站不做法規對應 |

**本站新查出、需下游注意的兩條**（來自 codekb，非 `constraint-register.md`）：

| 來源 | 約束 | 對應 |
|---|---|---|
| `kb:architecture` 約束九 `[讀]` | 大腦自建 runtime 後實際是**第三個** OpenRouter 入口，不是第二個。且 `llm_provider.configure_provider_env()` 會**改寫整個行程的環境變數**（把 `ANTHROPIC_API_KEY` 設為空字串），並在**每個** A1／A3 請求都被呼叫 | 新增第三份客戶端時此耦合必須被明寫；`C-S7` 的一致性驗證範圍應涵蓋它 |
| `kb:code-structure` 結構性風險 1 `[讀]` | `backend/` 內新增模組可能誤觸兩支 import 邊界 validator（一支以 AST 遞移追 import、一支掃全 `backend/` 禁止硬編 3 個計價 host） | 大腦若放進 `backend/`，落點須先確認不觸發這兩支 |

---

## Assumptions

- **A-1** nginx 與 cloudflared 會原樣透傳 `Sec-WebSocket-Protocol` 標頭。
  **本輪未查證**——codekb 只確認 `location /api/` 有設 `Upgrade` 與 `Connection`，
  未涵蓋其他握手標頭。FR8.5 建立在此假設上，須由設計階段實測。[RA:R6]
- **A-2** 語意記憶採向量檢索。若不採用，`C-T5`（換映像取得 pgvector）即不成立。
  未確認。[feasibility A-2]
- **A-3** NFR1 的 80% 門檻是工程判斷，**現在沒有依據**——能力 1 尚未存在，
  無任何基準可比。[RA:R1]
- **A-4** 「盡量省」是否足以守住 OpenRouter 後台的成本上限**無法驗證**：
  本專案不掌握該上限數值。[F11][F13][raid-log A-4]
- **A-5** 記憶層內建的最小權限模型足以讓介接系統映射自身角色，不需要記憶層
  理解各系統的角色語意。未確認。[F9][raid-log A-5]
- **A-6** 本站引用的 codekb 事實中，標記 `[簽]`／`[算]`／`[未驗]` 者**不是實讀
  驗證過的行為事實**。凡以它們為前提的需求，其前提強度不高於該標記。
  - 附帶：審查於本輪**實測複驗**了本站引用的機械事實（42 個 openapi path 且 ws
    不在其中、SSE 實為 5 個、`collab_router.py:257` 的 `record=False`、
    `Dockerfile` 無 `--workers`、`CREATE SCHEMA` 零命中、`helpers.py` 的 SQLite
    替換、成本 job 五種事件、`invoke_graph` 同步），**全部成立**。故本 A-6 的
    保留適用於**未被複驗的其餘引用**，不適用於上列這八項。
- **A-7** FR1.7 的信心門檻 0.7 與 NFR1 的 80% 一樣**沒有實證基礎**。兩者同時
  為真時的組合效果未被評估：門檻訂太高會讓系統過度反問（使用者體驗變差但準確率
  帳面上升），訂太低會讓錯誤交辦增加。**這兩個數字必須一起校正，不得分開調**，
  否則會出現「調高門檻換取準確率」的度量失真。[本站自檢]

---

## Out of Scope

承自上游，本站未新增亦未移除：

- 雲端供應商 production 環境、production credentials、environment-specific
  secrets、direct production IaC、destructive cloud operations、native
  iOS/Android app。[memory:M2]
- 成本計算本身（本次編排既有能力）。[Q12]
- 「跨雲分析（by 專案）」。[Q12]
- 本平台自身 LLM 花費的計量與 admin 設定機制。[F13]
- 管理功能頁面與 `/cost` 頁不納入共享工作階段。[Q7][Q14]
- **既有三處行程內狀態容器的外部化**——NFR4 明確把它們排除在本 intent 之外。
  [RA:R7]

---

## 本階段新增、已核可 scope 尚未涵蓋的項目（**需回補**）

依 `project.md` 的 requirements 規則，逐項明標，不當成既有能力的自然延伸吸收。
**七項**，分三類——**驗證機制或資料交付物**（N-1、N-2、N-3）、**權限模型變更**
（N-5）、**新交付物或新使用者可見面**（N-4、N-6、N-7）。三類的工作量性質不同，
`delivery-planning` 編 Bolt 時不可一視同仁：N-5 觸發兩條 blocking 規則、N-7 是
一個線框零畫面的全新使用者可見面，兩者都不是測試資產。[R-13 的修正]

| # | 新增項 | 來源 | 為什麼不是既有能力的延伸 |
|---|---|---|---|
| **N-1** | 一份前後端共用的 WS 訊息型別契約來源 ＋ 一個新的 CI 一致性檢查 | NFR5（`[RA:R5]`） | 能力 8 是「使用者看到回覆逐步顯示」；契約閘門是保護它的機制，不在能力清單內 |
| **N-2** | 一個對真實 PostgreSQL 執行的新 CI job | NFR6（`[RA:R8]`） | 能力 4 是「長短期記憶」；跑 PG 的 CI job 是驗證它的機制，不在能力清單內 |
| **N-3** | ≥ 50 筆人工標註的意圖測試集 ＋ **三條 NFR 的量測機制本身**（跑標註集算準確率、e2e 斷言脈絡保留、伺服器端計時 P50） | NFR1／NFR2／NFR3 ＋ `[RA:R9]` | 這是量測能力 1、2、8 所需的資料交付物**與**量測程式；`user-stories` 的既有職責是寫故事與 AC、`build-and-test` 的既有職責是跑既有測試，兩者都不含「建立一套新的指標量測機制」。**本輪擴充**：初版只寫了資料集，漏了量測機制（審查 R-04） |
| **N-4** | 一套與既有前例不同的 WS 握手認證方式 | FR8.5（`[RA:R6]`） | 最接近能力 8，但既有前例（token 在 query string）是可直接沿用的；改變它是本站為了 ADR-0006 network exposure 面向而新加的要求 |
| **N-5** | **新增一個 RBAC story id ＋ 權限矩陣項目**（入口頁），連帶 allow/deny 雙向測試與 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步 | FR1.8（`[R8]`） | **本輪補入**（審查 R-01）。這是已核可上游決定所**隱含**的義務，`[R8]` 的作答後果段逐字寫「需由 requirements-analysis 以後的站承接」——不是本站的新選擇，但確實是 `scope-document.md` 10 項能力之外多出來的工作量，且觸發兩條 blocking 規則 |
| **N-6** | **一支承載 90 天清除的 gh-aw／GitHub Actions workflow**（不得是 `backend/` 內的排程程式） | FR4.5a（`[RA:R2]` ＋ `project.md ## Forbidden`） | **本輪補入**（審查 R-05）。`[RA:R2]` 只選了「90 天」這個數字；「由什麼承載」是 `project.md` 禁止 repo 內無人值守排程的條款逼出來的新交付物，不在能力清單內 |
| **N-7** | **專案／系統的建立路徑，含其使用者可見面**（建立表單或流程、其入口、以及建立後的導向） | FR9.5（本站自檢 ＋ 審查 R-12） | **修訂 2 補入**。`scope-document.md` 的能力 9 逐字只有「專案 → 系統 → 架構圖 階層」六個字，指的是**資料模型**；線框第 3 節只有 `[切換對象]`（選取既有）與 `[改為獨立對話]`，**零建立畫面**。沒有建立路徑，FR9.1 的資料模型只有 FR9.2 的遷移能產生資料。這是一個全新的使用者可見面，不是能力 9 的自然延伸——它需要線框、需要互動設計、需要授權決定 |

**回補請求**：七項應於下一次回到 `scope-definition` 時，或由
`delivery-planning`（2.9）在編 Bolt 時，明確納入工作量估算。本站不擅自把它們
寫成新能力。

### 人工確認範圍的落差與其處置（R-11）

**落差（複審 R-11 查出）**：修訂 1 的確認收據涵蓋的是「四項（N-1 至 N-4）」，
而本表在修訂 2 後已有七項；**修訂 2 當時**，`0.7` 這個數字在問題檔零出現。
第 5、6、7 項與 FR1.7 的數值因此落在**當時那份**收據的涵蓋範圍之外。
（現況見下方第 3 點與結語：重取確認後兩者皆已涵蓋。）[R-21 的修正]

**處置沿革（三個回合，如實記載）**：

1. 修訂 2 的第一版處置是「當場追認 ＋ 問題檔刻意不動」，理由是問題檔被雜湊綁定、
   編輯會使收據失效。**該處置被複審的 R-18 判為不當**——使用者的裁決原文要求
   「補寫進問題檔的確認區塊」，而我把紀錄落點換到 artifact 卻沒回頭取得同意。
2. 第二次嘗試以 **HTML 註解**寫入問題檔，假設註解不構成 section 故不影響 digest。
   **實測失敗**：引擎回 `SUMMARY_CONTENT_STALE`，摘要 digest 涵蓋整份檔案。
3. **修訂 3 的最終處置**：接受真實代價，**重取一輪 Consolidated Summary
   Confirmation**。問題檔的確認區塊已改寫為實際內容——七項回補交付物（N-1 至
   N-7）與 FR1.7 的 0.7 皆列入——並由使用者重新確認。

**因此本節不再是「兩份文件不一致的解釋」，而是沿革紀錄**：確認收據現已完整
涵蓋本清單的七項與 FR1.7 的數值，`0.7` 與 N-5／N-6／N-7 都在使用者確認過的
範圍內。前兩次處置的失敗過程保留在此，因為它們各自是一個可複用的教訓：
**紀錄落點不能由 AI 單方面替換**（R-18），而**HTML 註解不在摘要 digest 的
豁免範圍內**（本輪實測所得，規格的「註解不構成 section」講的是 section 判定，
不是 digest 範圍）。

---

**判準的修訂（審查 R-05／R-01 逼出）**：初版只收集「本站在答案裡明確選出來的
新機制」，因此漏了 N-5 與 N-6——它們是**上游已核可決定所隱含、但本站未落地的
義務**。正確判準是「**本站之後多出來的工作量**」，不是「本站做的選擇」。

---

## Open Questions

留給下游的未決事項，每項附指定落點：

| # | 未決事項 | 指定落點 | execution |
|---|---|---|---|
| OQ-1 | 切回共享對話時，獨立那段的內容如何處置（保留／捨棄／可回溯）—— FR3.3 | `domain-design`（2.6） | CONDITIONAL，skip 則轉 `units-generation`（2.7） |
| OQ-2 | 語意記憶是否採向量檢索（決定 `C-T5` 是否成立）—— A-2 | `domain-design`（2.6） | CONDITIONAL，同上 |
| OQ-3 | episodic memory 的加密手段（靜態與傳輸）—— NFR7 | `nfr-design`（3.3） | CONDITIONAL；其條件依賴 `nfr-requirements` 是否執行 |
| OQ-4 | 路由層模型定案（`typesafe/jev-1.13` vs `gemini-3.7-flash`）—— NFR10 | `nfr-requirements`（3.2） | CONDITIONAL，**無自然承接站**，skip 時須重新提交使用者 |
| OQ-5 | 兩種串流機制並存的邊界（哪些路徑走 WebSocket、哪些維持 SSE）—— FR8.2 | 設計階段 | 承自 `[F4]`，上游未細分落點 |
| OQ-6 | 外部成本上限觸發時的系統行為（方向為明確降級而非靜默失敗）—— NFR9 | 設計階段 | 承自 `[F13]`，上游未細分落點 |
| OQ-7 | 三份 OpenRouter 客戶端的一致性驗證範圍（含 `configure_provider_env` 的行程級環境變數耦合） | `contract-design`（2.8） | CONDITIONAL，skip 則轉 `tcms-test-cases`（3.8） |
| OQ-8 | `A-1`（nginx／cloudflared 是否透傳 `Sec-WebSocket-Protocol`）的實測 | `domain-design`（2.6）或 `infrastructure-design`（3.4） | 皆 CONDITIONAL |
| OQ-9 | **Redis 中 session 狀態的存活期與清除條件**——NFR4 定了「放 Redis」，但誰清、何時清沒有定義。FR4.5 的 90 天只管 PostgreSQL 的 episodic memory，不管 Redis 的 session。本站的契約端點自檢查出「誰清」這一端懸空 | `domain-design`（2.6） | CONDITIONAL，skip 則轉 `units-generation`（2.7） |
| OQ-10 | **FR1.6 能否成立**：路由層是否能產出可比較的信心值。若不能，FR1.3 須改採替代觸發條件（候選並列且無單一最高分），FR1.7 的 0.7 隨之不適用。須與 OQ-4 的模型定案一併決定，不得分開處理。**上游已登記此不確定性並指派 `nfr-requirements`**，本站不重複指派，只把「必須輸出」升為 FR1.6 | `nfr-requirements`（3.2） | CONDITIONAL，**無自然承接站**（同 OQ-4），skip 時須重新提交使用者 |
| OQ-11 | 入口頁的 **story id 字串**，以及哪些角色預設持有該權限（`role_permissions` seed 的具體列）—— FR1.8 | `domain-design`（2.6） | CONDITIONAL，skip 則轉 `units-generation`（2.7） |
| OQ-12 | 哪些角色得**放寬記憶列的可見範圍**（FR4.3b 的授權端）—— FR4.3b | `domain-design`（2.6） | CONDITIONAL，同上 |
| OQ-13 | 90 天清除 workflow 的**落點與其取得資料庫連線的方式**（它跑在 GitHub Actions 上，而資料庫在自架 staging 主機後面）—— FR4.5a | `infrastructure-design`（3.4） | CONDITIONAL，skip 則轉 `deployment-pipeline`（4.1，亦 CONDITIONAL）——**兩者皆 CONDITIONAL，若都 skip 須重新提交使用者** |
| OQ-14 | `projects`／`systems` 的 **story id、建立／修改／刪除的角色集合**，以及是否沿用 `diagram_shares` 形狀的多對多分享—— FR9.5 | `domain-design`（2.6） | CONDITIONAL，同 OQ-11 |

**本表的 execution 欄與轉移目標為本輪查證 `.claude/tools/data/stage-graph.json`
的結果，不是憑印象**：本工作流程編譯後 34 站中，`requirements-analysis`（2.3）、
**`units-generation`（2.7）**、`build-and-test`（3.6）、`tcms-test-cases`（3.8）、
`delivery-planning`（2.9）、`code-generation`（3.5）為 `ALWAYS`；`user-stories`（2.4）、
`domain-design`（2.6）、`contract-design`（2.8）、`nfr-requirements`（3.2）、
`nfr-design`（3.3）、`infrastructure-design`（3.4）、`deployment-pipeline`（4.1）
皆為 `CONDITIONAL`。**指派落在 CONDITIONAL 站者一律附轉移目標**；OQ-10 與 OQ-13
是本表中找不到有效轉移目標的兩項，已明寫「須重新提交使用者」而非填一個看起來
合理的站。**`units-generation`（2.7）為 `ALWAYS`**，這一點決定了本表最常用的
轉移目標（OQ-1、OQ-2、OQ-9、OQ-11、OQ-12 與 FR9.3 皆轉移至它）是有效的；
上一版註腳漏列它，讀者無從確認這六項轉移不是又落到另一個 CONDITIONAL 站上。
[R-17 的修正]
