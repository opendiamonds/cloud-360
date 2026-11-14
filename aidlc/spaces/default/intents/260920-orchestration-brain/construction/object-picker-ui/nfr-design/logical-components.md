# Logical Components — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:14:17Z（`date -u` 取值）。
>
> 把 `performance-design.md` 與 `security-design.md` 的設計落到**元件層級**。`code-generation` 以 §一為改動清單。
> 本單元**無後端變更**、無新部署元件；失敗域全部在瀏覽器的單一分頁內。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../functional-design/frontend-components.md` §二、§三 | 元件拆分與檔案規劃（`:55-63`） |
| `inception/contract-design/contract-summary.md` `K-13`（`:1017` 起） | 掛載契約宣告 `ContextBar` 提供 `onObjectSelected`／`currentTarget` 兩個 prop（`:1028-1030`）；已交付的 `ContextBar` 沒有（`:22`），本單元改以 context 取值、不新增 prop（`functional-spec.md` §三之二）。本站沿用該處置：§一的 `ContextBar` 列不新增 prop，選單以 `useBrainSession()` 讀 `target`，與 `NFR2.160`「不持有副本」一致 |
| `performance-design.md`、`security-design.md` | 本站的設計決定 |
| `../nfr-requirements/tech-stack-decisions.md` ＋ `nfr-requirements-corrections.md` | `OPN-22`–`OPN-26`、`N-03`、`N-05` |
| repo 實測 | `ContextBar.tsx:20`（「本單元不渲染」註解）、`:22`（props 只有 `sharingToggle`）、`:43-49`（`<section>` 根節點）；`fanoutQueue.ts:49`；`a11y.spec.ts:177-181`（`isolate()` 中止未樁化的 `/api`）、`:711`（`scan()`）；`eslint.config.js:54-97` |

## 一、元件與改動清單

| 元件 | 新增／修改 | 責任 | 依賴 | 設計依據 |
|---|---|---|---|---|
| `frontend/src/components/brain/ContextBar.tsx`（**`U14` 的檔**） | 修改 | 渲染「切換對象」鈕（`brain-context-switch-object`，`aria-haspopup="dialog"`、`aria-expanded`）；`pickerOpen` state；衍生 `pickerVisible`；`<section>` 加 `tabIndex={-1}` 與 ref；斷線關閉時的焦點與播報；改寫 `:20` 註解 | `useBrainSession`、`ObjectPicker` | performance §五；`OPEN-OP16-4` |
| `frontend/src/components/brain/ObjectPicker.tsx` | 新增 | dialog（`role="dialog"`、`aria-modal="true"`、`aria-labelledby`）錨定在鈕下方、無遮罩；點外部即取消；焦點陷阱；搜尋框；選單內播報區 `brain-object-picker-live`（`role="status"`）；identity／清單／表單三組正交 state；開啟 epoch 與 `cancelled` 旗標 | `useAuth`、`useBrainSession`、`objectPickerData`、`objectPickerModel`、`objectCreateAction`、`createFanoutQueue`（只在搜尋補抓） | performance §一–§四；security §二–§四；`F-04`、`F-06` |
| `frontend/src/components/brain/ObjectPickerGroup.tsx` | 新增 | 一個專案群組：專案列（可選或停用＋說明）、展開鈕（`aria-expanded`、`aria-controls`）、系統清單（loading／error＋重試／空／列表）、「+ 新增系統」與其表單 | 父元件傳入的 props 與回呼；不自行抓取 | `N-02` 第 2、4 點 |
| `frontend/src/brain/objectPickerData.ts` | 新增 | 純抓取：`fetchProjects(token)`、`fetchSystems(token, projectId)`（包 `listProjects`／`listSystems`，不碰 state） | `projectsApi.ts` | `team.md` 資料抓取拆兩層 |
| `frontend/src/brain/objectPickerModel.ts` | 新增 | 純函式：`isOwnedByMe`、`targetIdsForProject`、`targetIdsForSystem`、`rowKey`、`currentRowKey`、`normalize`、`filterGroups` | 型別：`ProjectOut`／`SystemOut`／`WorkTargetPayload` | security §二之一、§五；performance §二 |
| `frontend/eslint.config.js` | 修改（**共用設定**） | 新增選單檔案集合的 lint 區塊 | — | security §一 |
| `frontend/tests/e2e/object-picker.spec.ts` | 新增 | 全部選單 e2e（每個 `test()` 前加 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui` 註解） | `wsFrames.ts` 建構器、`page.route`、`routeWebSocket` | `OPN-23` |
| `frontend/tests/e2e/a11y.spec.ts`（**`U17` 的檔**） | 修改 | 新增兩個掃描點（§二） | 既有 `scan()`、`isolate()` | `N-06`；`OPN-23` |

`fetchPickerGroups`（`frontend-components.md:62` 原規劃的一次性「列專案 → 扇出列系統」）**不建立**：`F-05`／`N-02` 之後沒有一次抓全部的時機，改為上表兩個單一抓取函式。

## 二、axe 掃描點（`OPN-07`、`N-06`）

| 掃描點 | 前置 | 樁化 |
|---|---|---|
| 選單 `default` | 入口頁已連線（沿用 `a11y.spec.ts` 的 `stageEntryConnected`）、開啟選單；三個專案，一個非擁有者（停用＋說明）、一個展開 | `page.route` 樁 `GET /api/hierarchy/projects` 與展開群組的 `GET …/systems`——`isolate()` 會中止任何未樁化的 `/api` 請求並使測試失敗 |
| 建立表單錯誤態 | 同上，點「+ 新增專案」、送出名稱，`POST /api/hierarchy/projects` 樁為 409 | 加樁 `POST` |

兩點都用 `scan()` 的既有 WCAG 2.1 AA 標籤與基準清單規則（`a11y-baseline.json` 的 `entries` 維持空陣列）。這兩點的 `include` 範圍為 dialog 節點，避免把頁面其餘部分重複計入（頁面已有自己的掃描點）。

## 三、比較基準（`N-05`）

`code-generation` 動工前記下：`git hash-object ws-contract.json`、`jq -c '.dependencies, .devDependencies | keys' frontend/package.json`、`git hash-object frontend/tests/e2e/a11y-baseline.json`；
完工時再取一次，三者都須相同（`NFR5.160`、`OPN-22`、`OPN-23`），結果寫進 code-summary。

## 四、失敗域與爆炸半徑

| 失敗 | 爆炸半徑 | 處置 |
|---|---|---|
| 專案清單請求失敗（含 403） | 本次開啟的選單 | `error` 態＋重試；建立入口仍可用（`BR12.2` 的保留部分） |
| 單一群組系統清單失敗 | 該群組 | 群組內錯誤＋重試；其他群組照常（`F-05`） |
| 身分未決 | 本次開啟的選單 | `identity: 'failed'`＋重試（performance §四） |
| 連線離開 `ready` | 選單關閉；脈絡列與對話不受影響 | performance §五 |
| 建立失敗 | 該表單 | 就地文案、名稱保留（`BR14.4`） |
| 選單 JS 例外 | 理論上可使整個 `ContextBar` 子樹崩潰 | 本 repo 無錯誤邊界慣例，本站不新增；以 e2e 涵蓋的特殊輸入（`OPN-13`／`OPN-14`）降低機率 |

沒有任何一種失敗會跨分頁、跨使用者或影響伺服器狀態——本單元唯一的寫入是 `objectCreateAction`（伺服器端交易）與 `set_work_target`（伺服器端驗證）。

## 五、共用資源

| 資源 | 共用者 | 本單元的使用方式 |
|---|---|---|
| 頁面大腦連線（`useBrainSession`） | `U14` 全部元件 | 只讀 `status`／`target`、只呼叫 `setWorkTarget`／`announce` |
| 頁面 `LiveRegion` | `U14` | 只在選單**關閉後**寫入（`F-04`） |
| `fanoutQueue` 模組 | `U23` 專案頁 | 每次搜尋補抓建立自己的佇列實例，與專案頁不共用實例 |
| 後端 SQLAlchemy 連線池（預設共 15 條，`fanoutQueue.ts:18-20`） | 全站 | 補抓同時最多 4 個請求；開啟與展開各 1 個 |

## 六、送審前自檢（七項；五份產出共用，數字由 grep／jq 取得，本站未執行任何測試）

| # | 自檢 | 結果 |
|---|---|---|
| 1 | 可達性 | `M11`（重連後選單自己出現）：`routeWebSocket` 先關閉再接受新連線並送 ready，可達；`M9`（連點競態）：`page.route` 延遲 POST 1 秒放大競態，可達；`N-01` 的身分夾具沿用上一站附錄（`/me` 回 200 缺 `id`，權限齊全使路由守衛放行） |
| 2 | 契約端點三問 | `systemsByProject`／`expanded`／`backfillStarted`：寫讀清見 performance §一之二。`pickerOpen`：寫＝切換鈕、讀＝`pickerVisible`、清＝關閉路徑與斷線（performance §五，兩種寫法待實證）。`submittingRef`：寫＝送出前、讀＝處理函式入口、清＝`finally`。選單內播報區：寫＝開啟期間播報、清＝卸載。出現少於兩份的識別字：`rowKey`、`normalize` 只在 security §五／performance §二與本檔 §一，屬 `objectPickerModel` 內部函式 |
| 3 | 引用逐字核對 | 以 `sed -n` 印出：`eslint.config.js:11-34`／`:54-97`／`:84-87`／`:88`、`projectsApi.ts:59-82`／`:71`／`:85-104`／`:106-130`、`fanoutQueue.ts:18-20`／`:37-43`／`:49`、`AuthContext.tsx:79-84`、`auth-context.ts:55`、`ContextBar.tsx:20`／`:22`／`:43-49`、`LiveRegion.tsx:51`、`BrainSession.tsx:19`、`a11y.spec.ts:177-181`／`:711`、`hierarchy_router.py:250-252`、`contract-summary.md:1017`／`:1028-1030`、`ws-contract.d.ts:319`。**查出並更正一處**：performance §七初稿把頁面 `LiveRegion` 的 testid 留給 code-generation 去查，實讀為 `live-region`，已寫死 |
| 4 | 檔案集合一致性 | 對照 `entry-page-ui/nfr-design/`（不計 `reviews/`）：問題檔、performance、security、logical-components、traceability 五份——相同 |
| 5 | 跨檔傳播 | `useRef` 單發鎖：performance §三、security M9；`pickerVisible`：performance §五、本檔 §一；`fanoutQueue` 只用於搜尋補抓：performance §一之三、本檔 §一／§五；兩個播報區 testid：performance §七、本檔 §一；`NFKC`：問題檔 §一、performance §二。無矛盾 |
| 6 | 可算的數字 | `traceability.json`：`upstream_ids` 25（本單元 23 ＋ 他單元先例 2：`NFR11.100`、`NFR11.140`，標 N/A）；23 條本單元需求全部 `OK`；突變 M1–M11 共 11 條 |
| 7 | ADR-0006 ＋ PBT | security §七、§八：四面向判定與上游 `security-requirements.md` §六全部相同；PBT 不適用、與上游一致 |
