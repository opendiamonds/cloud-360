# 效能設計 — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:06:39Z（`date -u` 取值）。
>
> 單元類型 `ui`；`produces_kinds` 使本站產出 performance／security／logical-components／traceability 四份
> （scalability／reliability／observability 為 `[service]`，不適用；理由見 `logical-components.md` §四）。
> 本檔把 `../nfr-requirements/performance-requirements.md` 的 `EPN-01`–`EPN-09` 與 `NFR2.140`／`.141`、`NFR3.140`／`.141`、
> `NFR4.140`、`NFR11.140` 落成具體結構，並處置帶入項 nfr-requirements `R-02`（裁決）、`R-04`、`R-05`、`R-07` 與
> functional-design `R-06`。本站未執行任何程式；行號皆於撰寫當下實讀。本檔不含 `[EPD1]` 相關段落（該題只影響 security 與 logical-components）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/performance-requirements.md` | `EPN-01`–`EPN-09`、六條繼承子條、§三（`EPN-06` 的推導，本檔依裁決改寫） |
| `../carried-review-items.md` | nfr-requirements `R-02`（使用者裁決：每組 ≤ 5、快照 ≤ 15）、`R-04`、`R-05`、`R-07`；functional-design `R-06` |
| `../functional-design/rules.md` | `BR92.1`、`BR92.5`、`BR93.1`、`BR93.4`、`BR93.7`、`BR97.5`、`BR98.3`、`BR98.5` |
| `../functional-design/functional-spec.md` | §二之一（C-8 的 `_names_for` 與四個呼叫點）、§六之一（連線狀態機） |
| `inception/contract-design/contract-summary.md` | `x-concurrent-connections`（`:910` 起：三處各一條、同 key 多條並存）、`:990`（4403＝無 `K1`） |
| repo 實測 | `brain_gateway_rules.py:69-79`（`:70` 每 key 10 條、`:79` 每 key 每分鐘 30 次握手）、`:642-647`（`admit_handshake`：被拒者**不**記入窗）；`brain_gateway.py:743-746`（限流在 accept 之前、以 `ws.close()` 拒絕）、`:1226-1243`（`_build_catalog`）；`hierarchy_facade.py:194-202`（`_authorize`）、`:366-379`（`list_projects`／`list_systems`）；`hierarchy_service.py:73-77`（擁有者檢查一條 SQL）、`:291-323`；`membership_service.py:367-379`（`is_project_visible` 一條 SQL）；`frontend/src/main.tsx:7`（`StrictMode`） |

## 一、連線（`EPN-01`、`EPN-02`、`EPN-03`；帶入項 nfr-requirements `R-04`、`R-05`、`R-07`）

### 一之一、每頁一條連線與 StrictMode（`EPN-01`、`R-04`）

- `useBrainConnection(page)` 在**一個** effect 內建立 `WebSocket`，`WebSocket` 物件、退避計時器、首次失敗時刻放在 `useRef`；
  cleanup 依序：清除退避計時器 → 把本連線未終止的輪次轉 interrupted（`BR93.7`）→ `ws.close(1000)` → ref 歸 null。
- React Router 換頁時，舊頁的 cleanup 在新頁的 effect 之前執行（同一次 commit），故「舊連線在新連線 open 之前或同時進入
  CLOSING」由框架順序保證；e2e 以 `page.on('websocket')` 記錄 open／close 驗證（量測方式沿用 `EPN-01`）。
- **StrictMode 的處置（`R-04`，撤回「可量測」宣稱）**：e2e 跑在正式建置上，碰不到開發模式的雙重 effect。改為 **code review 檢查項**，
  code-summary 逐條回報：(a) cleanup 一定關閉連線並清計時器；(b) **不得**以 ref 去重（`if (wsRef.current) return`）——那會讓 StrictMode
  第二次 setup 沿用已被 cleanup 關閉的物件；(c) 沒有任何在 effect 外建立連線的路徑。另列一個以 `vite dev` 執行的手動案（只能手動桶，
  交 `tcms-test-cases` 分桶），**不進 CI**。

### 一之二、退避排程與放棄判準（`EPN-02`）

| 項 | 設計 |
|---|---|
| 排程 | 第 n 次失敗後等待 `BASE[min(n,5)] × r`，`BASE = [1, 2, 4, 8, 15, 15] 秒`，`r = 0.8 + 0.2 × Math.random()`；單次 ≤ 15 秒 |
| 放棄 | 首次失敗時以 `Date.now()` 記 `firstFailureAt`；每次失敗後若 `Date.now() − firstFailureAt ≥ 60000` 即放棄，**不**排下一次 |
| 重設 | 收到相符版本的 `ready` 時 `firstFailureAt` 與 n 歸零 |
| 放棄後 | 自動嘗試 0 次；只由「重新連線」按鈕（事件回呼）重新開始 |
| 時鐘 | 只用 `Date.now()` 與 `setTimeout`，兩者皆受 Playwright `page.clock` 控制，快轉可驗 |

逐次嘗試數（實算，見 §一之三）：`r` 恆為 1.0 時，等待累計為 1、3、7、15、30、45、60 秒 → 7 次重試 ＋ 首次 ＝ **8** 次握手；
`r` 恆為 0.8 時累計為 0.8、2.4、5.6、12、24、36、48、60 秒 → 8 次重試 ＋ 首次 ＝ **9** 次。故單一分頁在放棄前至多 9 次握手。

### 一之三、抖動與握手預算（`R-07`：理由改述為「降低同步」）

實查推翻了上游「保護限流」的前提：

- `admit_handshake`（`brain_gateway_rules.py:642-647`）在窗已滿時回 `False` **且不記入窗**；`brain_gateway.py:743-746` 以 `ws.close()`
  在 accept 之前關閉。被限流的握手在前端與「握手未被接受」無法區分，依 `BR92.5` 歸「其他」→ 續退避——**超額只會被拒，不會累積成鎖死**。
- 後端行程重啟會清空行程內的 `RateLimiter`；後端完全離線期間的嘗試在 TCP／代理層就失敗，根本不進限流。

因此握手預算真正被消耗的情境只有一種：**後端在線、握手被 accept 之後以 1011 關閉**（例如 Redis 不可達）。此時每分頁一分鐘內至多 9 次被計入，
`⌊30 ÷ 9⌋ ＝ 3`：**同一使用者至多 3 個分頁能把 60 秒的退避完整跑完而不被限流**；第 4 個以後的分頁會有部分嘗試被拒，仍在 60 秒後照常進入「放棄」。
這是本設計**宣告的支援數**，寫進 code-summary；放寬抖動範圍不會改變它（被計入的是嘗試次數，不是時刻）。

**定案**：抖動範圍維持 ×[0.8, 1.0]、只往下抖（不改寫 `BR92.5` 的「單次上限 15 秒」）。理由改述為「**降低同秒重連**」：
後端恢復時，同一使用者在同一時刻斷線的多個分頁，其重試時刻被打散，第一次成功前的同秒握手數下降。上游 `EPN-02` 的
「理由：保護每 key 30 次握手」一句以本節為準（設計檔不回改上游）。

### 一之四、終止碼（`EPN-03`；`R-05` 的計數範圍）

- 4401、4400、4403 在 `onclose` 事件回呼內設 `terminal` 狀態並**不**排退避（setState 在事件回呼內，lint 允許）。
- **計數範圍限定為「同一頁面實例」**（`R-05`）：`EPN-03` 的「自動發起的新連線 0 條」只對發生終止碼的那個 `useBrainConnection` 實例成立。
  換頁後新頁面實例的連線不在計數內——它是新頁面掛載的正常行為，不是重連。
- 4403 的落點設計見 `security-design.md` §六之二：**不導航**；呼叫一次既有 `refreshMe()`，入口頁由 `DefaultRedirect` 依新權限重判，
  子頁面的大腦掛點在 `K1` 失效時卸載。這使「入口頁又被 4403 關閉、停在無法恢復的畫面」變成可預期的終止提示，且不形成迴圈。

## 二、對話紀錄（`EPN-04`、`EPN-05`、`NFR3.140`、`NFR4.140`）

### 二之一、收到即呈現（`NFR3.140`）

`onmessage` 收到 `token`／`cost_card` 即 dispatch 到紀錄 reducer，**不**累積到 `done` 才寫入、不以 `requestAnimationFrame` 或計時器批次合併。
React 的自動批次只合併同一事件迴圈內的更新，不延後到 `done`，不違反本條。突變：改為只在 `done` 時寫入 → 「送 token 不送 done」的 e2e 紅。

### 二之二、上限與 turnId 對照（`EPN-04`、`EPN-05`）

**對照表形狀改變（`EPN-04` 的直接後果，非新選擇）**：`frontend-components.md` §三 把對照定為「turnId → (段, 訊息索引)」。
`EPN1`=A 的「超過 500 則從最舊整則移除」會使該段所有索引減一，原形狀必然把下一個 token 寫到**錯的訊息**。本站改為：

| 結構 | 形狀 |
|---|---|
| 每段 | `{ items: TranscriptItem[]; truncated: boolean }`，`items.length ≤ TRANSCRIPT_MAX_PER_SEGMENT`（`= 500`，`brainTranscript.ts` 的模組常數） |
| 對照 | `turnSegment: Record<turnId, SegmentId>`——只記段；位置在該段 `items` 內以 `turnId` 尋找（≤ 500 筆，線性搜尋） |

reducer 的四個動作（全部回傳新物件，`react-hooks/immutability`）：

| 動作 | 行為 |
|---|---|
| `append(segment, item)` | 若該段已 500 則：移除 `items[0]`；若被移除者帶 turnId → 同時刪除 `turnSegment` 的該鍵；`truncated = true`。再附加新項；新項帶 turnId → 寫入對照 |
| `updateTurn(turnId, patch)` | 查 `turnSegment` 得段，於該段找 turnId；**找不到**（已被移除）→ 視為首見，依 `BR93.5` 在接收頁目前讀取段 `append` 一則新訊息，不拋例外 |
| `interruptOpenTurns(connId)` | 不變（`BR93.7`） |
| `reset()` | 三段 ＋ 對照一起回到初值（由登入／登出事件觸發，`security-design.md` §六之一） |

不變式（`EPN-05`）：`keys(turnSegment) ⊆ { item.turnId | item ∈ 任一段 }`，每次 `append`／`reset` 後成立。前端無 unit 框架，
以 `EPN-04` 的 e2e 附帶斷言（被移除那一輪再收到 `token` 時畫面多出一則、不崩潰）驗證。`truncated` 為真時該段頂端渲染
「較早的對話已不在畫面上」（`data-testid="brain-transcript-truncated"`）。

### 二之三、重連後以伺服器推送覆蓋（`NFR4.140`）

`useBrainConnection` 持有的作業對象、工作項、`sharing_mode` 在每次 `ready` 後被快照逐項**取代**（不合併、不保留本地值）；紀錄 store 不屬此列，保留。
突變：重連後以本地值優先 → `routeWebSocket` 版的「第二次 ready 後推送不同值」案紅。

## 三、名稱查詢的語句數（`EPN-06`、`EPN-07`、`NFR3.141`；帶入項 nfr-requirements `R-02`，使用者裁決）

### 三之一、上界改為每組 ≤ 5、快照 ≤ 15

| 步驟（`describe_work_target` 的固定順序，`security-design.md` §二之一） | SQL 條數 | 依據 |
|---|---|---|
| ① `_authorize(principal, "view")` | 1 | `hierarchy_facade.py:194-202` → `user_can` → `get_permission_row`（`rbac.py:124-132`，一條 `role_permissions` 查詢） |
| ② 專案層（`project_id` 非 null）：主鍵查詢含擁有者條件 | ≤ 1 | `hierarchy_service.py:73-77` 的形狀 |
| ③ 系統層（`system_id` 非 null）：`systems` 以主鍵查詢並**連帶**取所屬專案的 `owner_user_id`（一條 join） | ≤ 1 | 既有 `assert_system_owned_by` 為兩條（`:80-86`），本方法不沿用它——用 join 省一條，否則上界變 6 |
| ④ 圖層（`diagram_id` 非 null）：主鍵查詢含 `user_id` 條件 | ≤ 1 | `hierarchy_service.py:89-96` 的形狀 |
| ④' 只有圖、且圖掛在某系統下：以 `systems` 主鍵取 `project_id`，作為可見性判定的對象 | ≤ 1（與 ②③ 互斥） | §二之一「所屬專案」的定義 |
| ⑤ 所屬專案非 null：注入的 `project_visible(pid)` | ≤ 1 | `membership_service.py:367-379`（docstring 逐字「一條 SQL」） |

完整三元組：1 ＋ 1 ＋ 1 ＋ 1 ＋ 1 ＝ **5**；只有圖且有系統：1 ＋ 1 ＋ 1 ＋ 1 ＝ 4；孤兒圖：1 ＋ 1 ＝ 2（無所屬專案，⑤ 不執行）。
快照至多 3 組（三段），每組各自付一次 ①（facade 方法是無狀態的，每次呼叫都授權）：3 × 5 ＝ **15**。扇出點每次 1 組：≤ 5。
「1 個與 50 個專案語句數相同」的判準保留——上表沒有任何一步隨資料量成長。

**不採的寫法**：把 ① 提到 `_names_for` 只做一次——那需要一個「已授權」的 facade 入口，等於開一條不授權的讀取路徑，換來每次快照省 2 條。

### 三之二、一次 thread、一個 session、失敗不外拋（`EPN-07`）

`_names_for(conn, triples)` 去重後只做**一次** `asyncio.to_thread`，thread 內只開**一個** DB session（`self.session_factory()`），
逐組呼叫 `describe_work_target`；某組拋任何例外 → 該組三名稱 null、記一筆 `work_target_names_failed`（`connId`、`exc`＝例外類別名；
兩者皆在 `brain_gateway.py:130-149` 的 `_ALLOWED` 內）、`db.rollback()`（其本身再失敗則吞下，避免失敗交易使後續組全部連帶失敗以外的副作用），
繼續下一組。thread 外層（例如 `session_factory` 本身失敗）同樣捕捉，全部組回 null ＋ 一筆 log。**不設逾時**（上游 §一第 2 點）。

### 三之三、目錄路徑的成本變化（揭露，非 `EPN-06` 範圍）

nfr-requirements `R-01` 裁決使 `_build_catalog`（`brain_gateway.py:1226-1243`）也套可見性（`security-design.md` §三）。
現行語句數為 2 ＋ 3N（N＝擁有的專案數，未截斷時逐專案 `list_systems` 各付授權、擁有者、列舉三條）。改後 `list_projects` 逐專案判可見性（＋N）、
`list_systems` 多一道可見性（＋N）：**2 ＋ 5N**；N 上限 50（`CATALOG_PROJECT_MAX`，`brain_gateway_rules.py:85`）時由 152 增為 252。
這段在交辦的關鍵路徑上、計入首字預算（`NFR3`），但形狀仍是既有的「隨擁有專案數線性」，本單元不改它的階；改成集合式判定需要
`U13` 取得「可見專案 id 集合」的第二個注入方法，違反「判定只有一份」（`EPN-11a`）。列為已知成本，code-summary 記明。

## 四、子頁面首次對齊的時序（`NFR2.140`、`NFR2.141`）

- **就緒的觸發點不在 effect 內**：首次對齊可能要開圖（`handleLoadDiagram` 內有 setState），而 `react-hooks/set-state-in-effect`
  會追到 effect 同步呼叫的函式內部（`AssessmentPage.tsx:185-186` 的既有註解逐字記載此事）。故對齊只在兩處執行：
  (i) `work_target` 的 `onmessage` 回呼；(ii) 頁面在**既有的非同步續延**中呼叫同步掛點的 `onPageReady(snapshot)`——
  `/workspace` 為 bootstrap 的 `finally`（`WorkspacePage.tsx:296-298`），`/assessment` 為圖清單請求的 `.then`／`.catch`（`:246`）。
- **`onPageReady` 的引數由頁面以區域變數明確傳入**，不讀 ref：bootstrap 的 `setCurrentDiagramId` 在同一段非同步流程內才發生、尚未 commit，
  此時任何由 effect 同步的 ref 都還是舊值。`/workspace` 傳 `{ openedDiagramId, openedBy: 'bootstrap', diagrams, listOk, unsaved }`；
  `/assessment` 傳 `{ diagrams, listOk }`，其餘取自 ref（評核頁的選定圖與未存檔狀態在清單回來之前不會被程式改動）。
- 快照先到 → `pendingInitialTarget` 存 ref、旗標不消耗；`onPageReady` 時對齊。快照後到 → `onmessage` 時對齊。兩案進同一個純函式
  `decideInitialAlignment(input) → 'open' | 'hold' | 'writeback' | 'none'`（`useWorkspaceTargetSync.ts` 內，無 React 依賴），
  使「先到、後到最終三元組相同」（`NFR2.141`）由同一份判斷承載。
- `NFR2.140` 的可量測面：`brain-context-name-project`／`-system`／`-diagram`（`frontend-components.md` §八）各帶 `data-id` 屬性（識別碼字串，null 時不設屬性）；
  `brain-context-bar` 帶 `data-state`（`connecting`／`no-object`／`default`／`independent`／`unavailable`）。

## 五、其他

| 需求 | 設計 |
|---|---|
| `EPN-08` 零 HTTP | 本單元新增的前端程式不呼叫 `fetch`。**唯一例外**：收到 4403 時呼叫一次**既有**的 `refreshMe()`（`/api/auth/me`，既有端點），只在終止路徑上、每個頁面實例至多一次（`security-design.md` §六之二）。`EPN-08` 的量測在一般流程上進行，不受影響；code-summary 記明此例外 |
| `EPN-09` 無障礙 | 串流中該則 `aria-busy="true"`；`done`／`error` 的事件回呼內寫入既有 `LiveRegion` **一次**（寫入點只有這一處）；游標以 Tailwind `motion-reduce:animate-none` 關閉動畫 |
| `NFR11.140` 入口頁零換頁 | 入口頁的交辦、反問、更正、成本卡片皆不呼叫 `navigate`；只有使用者點擊的連結（記憶捷徑、工作項連結）換頁，且不在量測的交辦流程內 |
| functional-design `R-06` 前半 | `/workspace` 的 `fetchDiagrams`（`WorkspacePage.tsx:152-164`）改為回傳 `{ ok: boolean; list: Diagram[] }`，僅在 `response.ok` 分支 `ok = true`；既有呼叫端忽略回傳值不受影響。`listOk` 傳入 `onPageReady`；為假時兩個方向都不同步並顯示 `BR97.5` 末段的說明 |

## 六、本檔各節與需求的對應

| 需求 | 節 |
|---|---|
| `EPN-01` | §一之一 |
| `EPN-02` | §一之二、§一之三 |
| `EPN-03` | §一之四 |
| `EPN-04`、`EPN-05` | §二之二 |
| `EPN-06`、`NFR3.141` | §三之一 |
| `EPN-07` | §三之二 |
| `EPN-08`、`EPN-09`、`NFR11.140` | §五 |
| `NFR2.140`、`NFR2.141` | §四 |
| `NFR3.140` | §二之一 |
| `NFR4.140` | §二之三 |
