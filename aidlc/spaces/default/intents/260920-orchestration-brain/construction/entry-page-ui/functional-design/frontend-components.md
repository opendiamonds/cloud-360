# Frontend Components — `U14 entry-page-ui`

> 建檔時間 2026-10-17T00:00:48Z；**修訂 1** 2026-10-17T01:51:41Z（皆以 `date -u` 取值）。
> 規則正本 `rules.md`（`BR91`–`BR98`，49 條）；流程與狀態機正本 `functional-spec.md`。
> 修訂 1 依審查 R-01（樁訊框的型別承載）、R-02／R-03（子頁面同步）、R-06（lint 結構約束）改寫第一、二、三、四節。

## 零、上游來源

`interaction-spec.md` 的 ContextBar、WorkItemStore、WorkItemDock、ClarifyCandidates、CostAnswerCard、StreamingMessage；
`mockups.md` M0–M9；`contract-summary.md` K-13（掛載點、`onObjectSelected`）；`ws-contract.d.ts`；`U13` 交接 11 項
（`brain-gateway/code-generation/code-summary.md:228-244`）；`[EP1]`–`[EP6]`＝A；`team.md` 的前端 lint 結構約束。

## 一、既有程式的實測（決定了下列設計）

| 事實 | 出處 | 對設計的影響 |
|---|---|---|
| `DefaultRedirect` 的 `isPending` 在第一個權限判斷之前 | `App.tsx:27` | `K1` 插在 `isPending` 之後（`BR91.1`） |
| Sidebar 已有「專案」與「我的記憶」兩個獨立項，示範大腦項已移除 | `Sidebar.tsx:214-215`、`:229-230` | 「入口」置於兩者之前，獨立 `<nav>` |
| 唯一既有 WebSocket 消費者不帶子協定 | `useCollaboration.ts:25` | 本單元自寫 hook，不沿用 |
| subprotocol 字面量受 error 級 lint 禁止 | `eslint.config.js`（`ADR-0019 §5`） | 三個值由 `WsSubprotocol` 型別取值 |
| 子頁面圖清單含 `is_owner` | `WorkspacePage.tsx:13-17`、`AssessmentPage.tsx:16` | 回寫的擁有者判斷不需新 HTTP |
| `/workspace` 的 bootstrap effect 先 `await fetchDiagrams()` 再打 bootstrap，`finally` 設 `bootstrapDone` | `WorkspacePage.tsx:269-301`（`:297`） | 就緒閘門直接用既有 `bootstrapDone`（`BR97.5`） |
| `/workspace` 改變選定圖的位置 | `:282` bootstrap、`:313` 下拉、`:333` 新建空白、`:371` 刪除、`:823` 儲存新圖、`:441` 帶參數進評核 | `BR97.6` 逐一指定行為 |
| `/assessment` 選定圖＝`diagramOverride ?? urlDiagramId`；改變位置 | `AssessmentPage.tsx:238`；`:560`、`:743`、`:813`、`:1268` | 同上；評核頁沒有「清單已載入」旗標，需新增（在 `fetchDiagrams` 的回呼內設定） |
| **`frontend/tests` 不在任何 tsconfig 內** | `tsconfig.app.json:24`（`include: ["src"]`）、`tsconfig.node.json:23`（`include: ["vite.config.ts"]`）；`tsconfig.json` 只 references 這兩份 | e2e 檔不受 `tsc -b` 檢查——樁訊框的建構器必須放在 `src` 之下（`BR98.4`，審查 R-01） |
| CI 的 frontend job 跑 `npm run build`（＝`tsc -b && vite build`） | `.github/workflows/ci.yml:221-223`；`package.json` 的 `build` | 放在 `src` 的建構器每個 PR 都被型別檢查 |
| 既有 `LiveRegion` 元件（`role="status"` 寫死） | `frontend/src/components/LiveRegion.tsx` | 所有播報經它（`BR98.3`） |
| 已安裝 Playwright 1.61.1（含 `routeWebSocket`） | `node_modules/@playwright/test/package.json:3` | `BR98.4` 零新依賴 |

## 二、元件樹與檔案

```
App
└─ AuthProvider
   └─ BrainTranscriptKeyed                ← 讀 useAuth().user，以 user?.id ?? "anon" 作 key 掛載下一層（BR93.4，R-06）
      └─ BrainTranscriptProvider          ← App 層，記憶體，依段 ＋ turnId 對照（BR93.4、BR93.7）
         └─ BrowserRouter
            ├─ "/"  ProtectedRoute → DefaultRedirect
            │        └─ (K1) EntryPage
            │             ├─ EntryHeader（標題 ＋ MemoryShortcut［canSeeMemoryEntry］）
            │             ├─ BrainSession(page="entry")        ← useBrainConnection（BR92）
            │             │   ├─ ContextBar(sharingToggle=false)
            │             │   ├─ WorkItemDock
            │             │   ├─ ConversationView
            │             │   │   ├─ EntryEmptyState（卡 A／卡 C）
            │             │   │   ├─ UserMessage
            │             │   │   ├─ StreamingMessage
            │             │   │   ├─ ClarifyCandidates
            │             │   │   ├─ WorkItemList（錨定於某則大腦訊息）
            │             │   │   └─ CostAnswerCard
            │             │   ├─ ConnectionNotice（4401／放棄／版本不符）
            │             │   └─ BrainInput
            ├─ "/workspace"  既有 WorkspacePage
            │        └─ BrainSession(page="workspace", pageSync=useWorkspaceTargetSync)
            │             ├─ ContextBar(sharingToggle=true) ＋ SyncNotice
            │             └─ SubpageBrainPanel（收合；展開＝ConversationView ＋ BrainInput 的精簡版）
            ├─ "/assessment" 既有 AssessmentPage（同上，page="assessment"）
            └─ "*" → Navigate "/"
Sidebar：EntryNavItem（K1 view，置頂）
```

文字 fallback：`AuthProvider` 之下以 `BrainTranscriptKeyed` 依目前使用者 id 掛載 `BrainTranscriptProvider`（使用者改變即重新掛載、
紀錄重設）；入口頁內以 `BrainSession` 持有一條連線，下掛脈絡列、常駐區、對話視圖、連線提示與輸入列；兩個子頁面各掛一個
`BrainSession`，帶頁面同步掛點，只含脈絡列（可切換共享）、同步提示與收合的「問大腦」面板；萬用路由導回 `/`；Sidebar 多一個置頂的「入口」項。

**檔案拆分（`react-refresh/only-export-components`，審查 R-06）**：

| 檔 | 內容 |
|---|---|
| `src/brain/BrainTranscriptContext.tsx` | 只匯出元件：`BrainTranscriptProvider`、`BrainTranscriptKeyed` |
| `src/brain/brainTranscript.ts` | context 物件、型別、`useBrainTranscript` hook、純 reducer（段切換、turnId 合併） |
| `src/brain/useBrainConnection.ts` | 連線 hook（`use*` 命名慣例） |
| `src/brain/useWorkspaceTargetSync.ts`、`useAssessmentTargetSync.ts` | 子頁面同步掛點（`BR97.5`、`BR97.6`） |
| `src/brain/testing/wsFrames.ts` | 型別化的伺服器訊框建構器、情境序列、`encodeFrame(env: WsEnvelope): string`（`BR98.4`）；不被任何 app 程式 import |
| `src/pages/EntryPage.tsx`、`src/components/brain/*.tsx` | 頁面與元件（`PascalCase`） |

## 三、props／state 責任切分

| 元件／hook | 擁有的 state | 讀 | 寫（方法） |
|---|---|---|---|
| `useBrainConnection(page)` | 連線狀態（`functional-spec.md` 六之一）、本頁所讀段、各段最新 `work_target`、工作項集合、反問組、`awaitingReply` | 收到的訊息 | `sendUserMessage`、`selectCandidate`、`correctWorkItem`、`setSharingMode`（僅子頁面）、`setWorkTarget` |
| `BrainTranscriptProvider` | 三段的訊息陣列、turnId → (段, 位置) 對照 | — | `append(segment, item)`、`updateTurn(turnId, patch)`（跨段依對照找原訊息）、`interruptOpenTurns(connId)` |
| `useWorkspaceTargetSync`／`useAssessmentTargetSync` | `pendingInitialTarget`、首次對齊旗標、本頁最近一次送出的 diagramId | 頁面的選定圖、`bootstrapDone`／清單已結束旗標、圖清單（`is_owner`）、本段 `work_target` | 呼叫頁面既有的開圖函式（`handleLoadDiagram`／`setDiagramOverride`）；呼叫 `setWorkTarget`；`onDiagramDeleted(id)` 由頁面的刪除處理器明確呼叫 |
| `ContextBar` | 展開／收合 | `work_target`（含三個名稱）、`sharing_mode` | 呼叫 `setSharingMode`；渲染 `U16` 的選單掛載點，選定時呼叫 `setWorkTarget` |
| `SyncNotice` | 「作業對象已改為…」的待顯示項（在 `work_target` 訊息的事件回呼內設定） | 同步掛點的判斷結果；「別人分享」「未存檔」兩種說明由 render 推導 | 「開啟這張圖」→ 頁面既有開圖函式 |
| `WorkItemDock` | 收合（窄螢幕預設收合） | 工作項集合（過濾） | 呼叫 `correctWorkItem` |
| `WorkItemList` | 無 | 工作項集合（不過濾）＋ 錨點 | 呼叫 `correctWorkItem` |
| `ClarifyCandidates` | 該組狀態（default／picking／dismissed／stale／resolved） | `clarify` | 呼叫 `selectCandidate` |
| `CostAnswerCard` | 無 | `cost_card` | 無 |
| `StreamingMessage` | 無（狀態在 store） | 該 turn 的內容與狀態 | 重試 → 呼叫 `sendUserMessage`（原句） |
| `EntryEmptyState` | 無 | `can`／`canArch` | 填入輸入列（不送出） |
| `SubpageBrainPanel` | 展開／收合 | 本頁所讀段的紀錄 | 呼叫 `sendUserMessage` |

方法的呼叫端：`sendUserMessage`←`BrainInput`、`SubpageBrainPanel`、`StreamingMessage` 重試；`selectCandidate`←`ClarifyCandidates`；
`correctWorkItem`←`WorkItemDock`、`WorkItemList`；`setSharingMode`←子頁面 `ContextBar`；`setWorkTarget`←子頁面同步掛點（`BR97.6`）、
`U16` 回呼（`BR97.7`）；`interruptOpenTurns`←`useBrainConnection` 的 cleanup（`BR93.7`）；`onDiagramDeleted`←`WorkspacePage` 與
`AssessmentPage` 的刪除處理器。

## 四、資料抓取形狀與 lint 約束

本單元**不新增任何 HTTP 呼叫**（`BR98.5`）；評核頁新增的「清單請求已結束」旗標只在既有 `fetchDiagrams` 的 `.then`／`.finally` 回呼內設定。

| lint 規則（error 級） | 本單元的形狀 |
|---|---|
| `react-hooks/set-state-in-effect` | effect body 內不同步 setState。連線在 effect 內建立，訊息處理在 `onmessage` 事件回呼內 dispatch；同步掛點的 effect 只**送 WebSocket 訊息**（不是 setState）；登出清空以 `BrainTranscriptKeyed` 的 key 重新掛載達成，**不**以 effect 監聽 user（R-06） |
| `react-hooks/refs` | `WebSocket` 物件、退避計時器、首次對齊旗標、最近送出值放在 `useRef`；只在 effect 的 setup／cleanup 與事件回呼內讀寫，**render 期間不讀 ref**（R-06） |
| `react-hooks/immutability` | reducer 一律回傳新物件 |
| `react-refresh/only-export-components` | Provider 與 hook／型別拆兩檔（第二節） |
| `no-restricted-syntax`（`ADR-0019 §5`） | 子協定由 `WsSubprotocol` 型別取值，不寫字面量 |

## 五、表單驗證

| 輸入 | 規則 |
|---|---|
| `BrainInput` | 空白或純空白不送出（送出鈕停用）；ready 之前與 `awaitingReply` 期間停用；超過伺服器輸入上限時以伺服器回傳的 `error(INVALID_REQUEST)` 呈現（前端不另抄上限數字） |

## 六、API 整合點

| 契約 | 用法 |
|---|---|
| WS 端點（`U13`，`/api/` 之下） | `wsUrl()` 組出，無查詢參數；子協定 `[protocolName, scheme + separator + token]` 皆由 `components['schemas']['WsSubprotocol']` 的欄位型別取值 |
| `WsEnvelope`／`WsClientEnvelope`／`WsUnvalidatedEnvelope` | 入站先以寬鬆封包解析（`BR92.6`），出站以 `WsClientEnvelope` 建構 |
| `WorkTargetPayload` 的 C-8 增量 | `projectName`／`systemName`／`diagramName`（`str \| null`，必存在），由 `U13` 經 `U7` 的 `describe_work_target` 填入（C-8 範圍為 `U7`／`U2`／`U13` 三個單元）；型別檔重產後由 `ContextBar` 讀取 |
| `costPageUrl` | 卡片連結的 href 原樣使用 |

## 七、無障礙

| 元件 | 要求 |
|---|---|
| `ContextBar` | `region`、`aria-label="目前作業對象"`；展開鈕 `aria-expanded`；對象變更經 `LiveRegion` 播報新名稱 |
| `WorkItemDock` | `region`、`aria-label="進行中的工作"`；「不是這個」的 `aria-label` 含該項 label；狀態變更播報「<label>：<新狀態>」 |
| `ClarifyCandidates` | `role="group"`，intent：`aria-label="請選擇你指的是哪一件事"`；target：`aria-label="請選擇你指的是哪一個"`；回絕鈕為群組最後一個可聚焦項並以虛線邊框區分 |
| `StreamingMessage` | 串流中 `aria-busy="true"`、完成時播報一次；游標遵守 `prefers-reduced-motion` |
| `CostAnswerCard` | `article` ＋ 標題；連結文字自足（含估價表編號） |
| `EntryEmptyState` | 卡片為 `list` 內的 `button`，可及名稱為完整功能名 |
| `SyncNotice` | 經 `LiveRegion` 播報一次；「開啟這張圖」可聚焦 |
| Sidebar「入口」 | `aria-current="page"` |
| 斷點 | 只用 `md:`；窄螢幕常駐區與子頁面面板預設收合，長名稱換行不截斷、不橫向捲動 |

## 八、`data-testid` 命名

`brain-entry-page`、`brain-memory-shortcut`、`brain-context-bar`、`brain-context-toggle`、`brain-context-sharing-badge`、
`brain-context-switch-object`（僅 `U16` 掛載後）、`brain-context-name-project`／`-system`／`-diagram`、`brain-sync-notice`、
`brain-sync-open-diagram`、`brain-workitem-dock`、`brain-workitem-dock-toggle`、`brain-workitem-{id}`、`brain-workitem-{id}-status`、
`brain-workitem-{id}-reject`、`brain-clarify`、`brain-clarify-candidate-{id}`、`brain-clarify-restate`、`brain-cost-card`、
`brain-cost-card-text`、`brain-cost-card-link`、`brain-stream-message`、`brain-stream-cursor`、`brain-stream-retry`、`brain-input`、
`brain-send`、`brain-connection-notice`、`brain-empty-card-architecture`、`brain-empty-card-cost`、`brain-subpage-panel`、
`brain-subpage-panel-toggle`。

Sidebar 項為 `sidebar-entry-link`——沿用既有 Sidebar 的 `sidebar-*` 慣例（`sidebar-projects-link`、`sidebar-memory-link`），
不用 `brain-*`。`interaction-spec.md` 的 `brain-cost-card-total` 不採用（無總額欄位，`functional-spec.md` D-5），改為 `brain-cost-card-text`。

## 九、本單元刻意不做

| 事項 | 理由 |
|---|---|
| 「最近的對話」與「+ 新對話」 | `[EP5]`=A；使用者 2026-10-17 裁決移到另一個 intent（`OPEN-EP14-2`） |
| 六張大腦無法交辦的能力卡 | `[EP5]`=A |
| 對話紀錄寫入瀏覽器儲存 | `[EP4]`=A；ADR-0006 加密面 |
| 改寫子頁面既有對話區 | `[EP1]`=A；`AC8.1.4` |
| 前端以 HTTP 查名稱 | `[EP2]`=A；`contract-summary.md:916-917` |
| 新增 tests 用 tsconfig | 審查 R-01 的另一條路；理由見 `functional-spec.md` §十二 |
| 對象切換選單與建立表單 | 屬 `U16`；本單元只提供掛載點 |
| 脈絡列「最後異動」 | 無來源，`OPEN-EP14-11` |
| 前端能力名稱對照表 | 單一真實來源；`label` 已含能力名稱 |
