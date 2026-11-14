# Performance Design — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:14:17Z（`date -u` 取值）。本站未執行任何程式；行號皆於撰寫當下實讀。
>
> **綁定**：`nfr-requirements-corrections.md` 的 `N-01`、`N-02`、`N-06` 取代凍結的 `performance-requirements.md` 中 `OPN-01`、`OPN-04`、`OPN-06` 的目標與量測；
> 本檔以取代後的版本為準。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/performance-requirements.md` ＋ `nfr-requirements-corrections.md` | `NFR2.160`、`NFR11.160`、`OPN-01`–`OPN-07`（含 `N-01`／`N-02`／`N-06` 的取代） |
| `../functional-design/functional-spec.md` ＋ `functional-spec-corrections.md` | W1–W6、兩個狀態機；`F-02`／`F-03`／`F-05`／`F-06` |
| repo 實測 | `projectsApi.ts:85-104`（`listProjects`／`listSystems`）、`fanoutQueue.ts:37-43`（`FanoutQueue` 介面：`enqueue`、`cancel`）、`:49`（`createFanoutQueue(limit = FANOUT_CONCURRENCY)`）、`AuthContext.tsx:79-84`（`refreshMe`）、`ContextBar.tsx:22-25`（元件簽章與 `status`）、`useBrainConnection.ts:65`（`attempt` 只在 hook 內部） |

## 一、一次開啟的生命週期（`OPN-01`、`OPN-02`）

### 一之一、開啟 epoch

`ObjectPicker` 掛載即代表一次開啟；卸載即結束。每個非同步結果在寫入 state 前檢查一個**本次掛載專屬**的 `cancelled` 旗標（`useEffect` 的區域變數，
沿用 `team.md` Code Style「資料抓取拆兩層」的既有形狀），卸載時設真。再開啟是新的掛載、新的旗標，所以晚到的舊回應永遠寫不進新的那一次（`OPN-02`）。
抓取函式無 `AbortSignal`（`projectsApi.ts:59-82`），故以丟棄而非中止達成。

### 一之二、群組系統清單的狀態

| state | 型別 | 寫 | 讀 | 清 |
|---|---|---|---|---|
| `systemsByProject` | `Map<number, { status: 'idle' \| 'loading' \| 'loaded' \| 'error'; systems: SystemOut[] }>` | `ensureSystems(projectId)`：只在 `idle` 或使用者按該群組的重試鈕（`error`）時轉 `loading` 並發 1 次 `listSystems` | 群組渲染、搜尋過濾、「目前」標示 | 卸載 |
| `expanded` | `Set<number>` | 展開鈕、搜尋命中自動展開（問題檔 §一第 2 點） | 群組渲染 | 卸載；清空搜尋時回到搜尋前的快照 |
| `backfillStarted` | `boolean` | 搜尋框第一次非空輸入 | 決定是否補抓 | 卸載 |

`ensureSystems` 是**冪等**的：同一次掛載內，一個專案的 `listSystems` 只會在 `idle → loading` 時發出一次；`error` 只有使用者按重試才再發（`OPN-01`「至多 1 次」的例外僅此一條，
屬使用者觸發，不計入上界）。

### 一之三、三個觸發點與請求數（`N-02`）

| 觸發 | 動作 | 請求數 |
|---|---|---|
| 掛載 | `listProjects` 1 次；回應後若目前作業對象所在專案在清單內，`ensureSystems(該專案)` 並加入 `expanded` | 1～2 |
| 展開鈕 | `ensureSystems(p)` | 0（已載入）或 1 |
| 搜尋第一次非空 | 對所有 `idle` 群組以 `createFanoutQueue()` 的 `enqueue` 呼叫 `ensureSystems`（同時最多 4 個、FIFO）；`backfillStarted = true` | 至多 P − 已載入數 |
| 之後的搜尋輸入 | 只跑純函式 `filterGroups` | 0 |

佇列在卸載時 `cancel()`（尚未發出者以 `FanoutCancelled` 拒絕，呼叫端忽略），在途者由 `cancelled` 旗標丟棄。佇列只在補抓時建立，開啟與展開不經佇列。

**「目前作業對象所在專案」的判定**：`target.projectId`（字串）與 `String(p.id)` 比較（`OPN-21`）。目前對象只有圖、沒有專案時（`projectId` 為 null），不預設展開任何群組，開啟請求為 1。

## 二、搜尋（`OPN-06`、問題檔 §一）

`filterGroups(groups, systemsByProject, query)` 為 `objectPickerModel.ts` 的純函式：`normalize = (s) => s.normalize('NFKC').trim().toLowerCase()`，以 `includes` 比對專案名與
`loaded` 群組的系統名；不建立正規表示式（`OPN-14`）。補抓期間 `aria-busy="true"` 掛在清單容器，並顯示一行「正在載入系統清單」；全部補抓結束（`Promise.allSettled`）後移除。

## 三、建立的單發保證（`OPN-03`）

state 更新是非同步的，連點兩次時第二次點擊可能仍讀到 `submitting === false`。因此擋重複觸發用 **`useRef<boolean>`**（在呼叫 `objectCreateAction` 之前同步設真、`finally` 設回），
`submitting` state 只負責畫面（停用送出鈕）。Enter 鍵送出走同一個處理函式。

## 四、身分未決（`OPN-04`，以 `N-01` 為準）

掛載時若 `typeof user?.id !== 'number'`：進 `identity: 'resolving'`，呼叫一次 `refreshMe()`，以 `try/catch` 接住其拋錯（`AuthContext.tsx:79-84` 無 catch）。
`refreshMe` 完成後 `AuthContext` 重新渲染，選單於下一次渲染讀新的 `user.id`：是數字即繼續 W1 第 4 步；不是數字或呼叫拋錯即 `identity: 'failed'`，顯示「無法確認你的身分，請重新整理頁面」與重試鈕。
重試鈕再呼叫一次 `refreshMe()`。為避免 effect 依賴 `user` 而重複觸發，「本次掛載已嘗試過」以 `useRef` 記錄。`refreshMe` 不觸發身分邊界通知（`auth-context.ts:55`），不會清空 `U14` 的對話紀錄。

## 五、連線離開 `ready`（`OPN-05`、`F-02`）

| 面向 | 設計 |
|---|---|
| 立即消失 | `ContextBar` 以**衍生值**決定是否渲染：`pickerVisible = pickerOpen && status === 'ready'`。`status` 一變，同一次渲染選單即卸載——不靠 effect 設 state，故不觸發 `react-hooks/set-state-in-effect`（error 級） |
| 不在重連後自己冒出來 | `pickerOpen` 必須被清掉。首選「依前值調整 state」寫法（`const [prevStatus, setPrevStatus] = useState(status)`，渲染中比較不同時一併 `setPickerOpen(false)`）；若 `react-hooks/set-state-in-render` 擋下此寫法，改由 `ObjectPicker` 卸載清理函式呼叫 `onConnectionLost()` 回呼清掉。**`code-generation` 須以 `npm run lint` 實證採用的是哪一個，並寫進 code-summary** |
| 焦點 | `<section data-testid="brain-context-bar">` 加 `tabIndex={-1}` 與 ref；選單因斷線卸載時把焦點移到它 |
| 播報 | 斷線關閉時呼叫 `conn.announce('連線中斷，已關閉作業對象選單')`，此時 dialog 已不存在，頁面 `LiveRegion` 可被唸出（`F-04`）；與「焦點」同一個觸發點，且只在「選單原本可見」時觸發（以 ref 記錄上一輪可見性），避免每次斷線都播報 |
| 送出 | 卸載後不會再呼叫 `setWorkTarget`（處理函式隨元件卸載）；`setWorkTarget` 本身在未 ready 時回 false 且不送（`brainSession.ts:56-57`） |

## 六、`NFR2.160` 與 `NFR11.160`

- `NFR2.160`：選單**不持有**作業對象的副本；選取只呼叫 `setWorkTarget`，脈絡列與「目前」標示都讀 `conn.target`（伺服器回推值）。選取成功即關閉選單，不在選單內樂觀標示新的「目前」。
- `NFR11.160`：選單不呼叫 `navigate`、不渲染 `<Link>`；建立成功後只切作業對象與關閉選單。靜態：選單檔案集合內 `useNavigate`／`<Link` 為 0（由 `security-design.md` §一的 lint 區塊之外以 e2e 的 pathname 序列驗證，不另加 lint）。

## 七、量測法（`OPN-05`、`OPN-07`，以 `N-06` 為準）

- 播報計次：`page.addInitScript` 掛 `MutationObserver`，觀察頁面 `LiveRegion`（`[data-testid="live-region"]`，`frontend/src/components/LiveRegion.tsx:51`；大腦頁面只掛一個，`BrainSession.tsx:19`）
  與選單內播報區 `[data-testid="brain-object-picker-live"]` 的文字變化，非空內容推入 `window.__announcements`（陣列元素含來源 testid）。
- 請求計數：`page.on('request')` 過濾 `/api/hierarchy`，以 pathname 與 method 分組。

## 八、刻意不做

| 不做 | 理由 |
|---|---|
| 跨開啟快取 | `BR12.1`；問題檔（nfr-requirements）§一第 2 點 |
| 預抓（開啟前就抓） | 會在使用者沒打開選單時也付請求；違反 `OPN-01` 的「每次開啟」上界語意 |
| 虛擬捲動 | nfr-requirements 問題檔 §一第 3 點 |
