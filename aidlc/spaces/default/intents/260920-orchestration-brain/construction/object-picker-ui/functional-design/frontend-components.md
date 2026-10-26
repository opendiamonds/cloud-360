# Frontend Components — `U16 object-picker-ui`

> 本檔規定元件階層、props／state 切分、資料抓取形狀、API 整合點、無障礙與
> `data-testid`。**互動流程與狀態機的正本是 `functional-spec.md`**（§五 `W1`–`W6`、§六），
> 規則的正本是 `rules.md`（`BR11`–`BR15`）；本檔只寫「這些流程與規則落在哪個元件、
> 由誰持有哪一份 state」，不重述流程。
>
> 程式片段僅為介面層示意（≤15 行），實作屬 `code-generation`。

## 零、上游來源

| 來源 | 本檔用它決定什麼 |
|---|---|
| `functional-spec.md`（本單元） | `W1`–`W6`、§六兩個狀態機、§四的實際 API 形狀 |
| `rules.md`（本單元） | 22 條 `BR11`–`BR15` |
| `inception/refined-mockups/interaction-spec.md:256-301` | `ObjectPicker` 的狀態、無障礙、test ids |
| `inception/contract-design/contract-summary.md:1017-1056`（`K-13`） | 掛載點、`data_fetch_shape`、`url_building`、`immutability` |
| `team.md ## Code Style` | 兩層資料抓取、immutability、非元件 TS 檔名 camelCase、Context 拆兩檔 |
| 既有程式（下節實測） | 可沿用的既有模組與形狀 |

## 一、既有程式的六項實測（本站開檔核對，各決定一個設計選擇）

| 實測 | 位置 | 決定 |
|---|---|---|
| ① `ContextBar` 只有 `sharingToggle` 一個 prop，作業對象與送出由 context 提供 | `ContextBar.tsx:22`；`brainSession.ts:30-34`、`:57` | 選單以 `useBrainSession()` 取得，不補 prop（`BR11.1`）；**修改 `U14` 的檔**（`functional-spec.md §三之二`） |
| ② `setWorkTarget` 回 `boolean`，未 ready 時不送 | `useBrainConnection.ts:331-335` | 切換鈕只在 ready 時渲染；仍處理 `false`（`BR11.2`） |
| ③ 每頁一個大腦 `LiveRegion`，由 `announce` 寫入 | `BrainSession.tsx:9`、`:19` | 選單不另掛播報區（`BR15.4`） |
| ④ 專案與系統的純抓取函式已存在，型別取自產生的 `api.d.ts` | `projectsApi.ts:23-24`、`:85-105` | 直接沿用，不新寫 fetch、不手寫 interface |
| ⑤ 扇出佇列已存在，含 `cancel()` 語意 | `fanoutQueue.ts:1-28` | 系統清單的扇出沿用（`BR12.1`／`BR12.4`） |
| ⑥ 既有五個 modal 只做初始 `.focus()`，無焦點陷阱、無焦點返還 | `design-system-mapping.md` 修訂 1 §11 的 `InviteMemberDialog` 列；`InviteMemberDialog.tsx:60` | 本單元新建陷阱與返還，限於 `ObjectPicker` 內，不抽共用工具（只有一個使用點） |

## 二、元件樹

```
EntryPage／WorkspacePage／AssessmentPage（既有，不改）
└── <BrainSession>（既有，提供 useBrainSession 與 LiveRegion）
    └── <ContextBar sharingToggle />（U14 的檔，本單元擴充）            BR11.1
        ├── 作業對象名稱節點（既有，不動）
        ├── <button 切換對象>  僅 status === 'ready'                   brain-context-switch-object
        ├── 共享徽章與「改為獨立對話」（既有，屬 U14，不動）
        └── <ObjectPicker onClose />  僅 pickerOpen                   components/brain/ObjectPicker.tsx
            ├── 標題「切換作業對象」＋ 搜尋框                          BR15.1／BR13.4
            ├── 狀態區：loading／empty／error／no-match                BR12.2／BR14.6
            ├── <ObjectPickerGroup /> × N                             components/brain/ObjectPickerGroup.tsx
            │   ├── 專案列（可選或 aria-disabled）＋「目前」           BR13.1–BR13.3
            │   ├── 非擁有者說明（僅不可選時）                          BR13.2
            │   ├── 「+ 新增系統」（僅擁有者 且 K2 edit）              BR14.3
            │   ├── <ObjectCreateForm kind="system" />（僅此群組的表單開啟時）
            │   └── 系統列 × M（可選或 aria-disabled）＋「目前」
            └── 底部「+ 新增專案」（僅 K2 edit）＋ <ObjectCreateForm kind="project" />   BR14.2
```

**文字說明**：三個頁面與 `BrainSession` 不改。`ContextBar` 新增「切換對象」鈕（只在連線
ready 時）與 `pickerOpen` 狀態；開啟時渲染 `ObjectPicker`。選單有標題與搜尋框、狀態區、
每個專案一個 `ObjectPickerGroup`（專案列、必要時的非擁有者說明、必要時的「+ 新增系統」
與其表單、系統列），底部為「+ 新增專案」與其表單。

非元件模組（檔名 camelCase，依 `team.md` 命名慣例）：

| 檔案 | 內容 | 性質 |
|---|---|---|
| `frontend/src/brain/objectPickerData.ts` | `fetchPickerGroups(token, queue): Promise<PickerGroup[]>`（`listProjects` → 扇出 `listSystems`） | 純抓取，不碰 state |
| `frontend/src/brain/objectPickerModel.ts` | `isOwnedByMe`、`targetIdsForProject`／`targetIdsForSystem`、`currentRowKey`、`filterGroups` | 純函式，不碰 state、不碰 `fetch`（§五之二） |

建立一律呼叫既有 `frontend/src/projects/objectCreateAction.ts`（`BR14.1`），本單元不新增任何
寫入模組。**不新增 Context**：選單的 state 只在選單開啟期間存在。

## 三、`ContextBar` 的擴充（逐點）

| 項 | 內容 |
|---|---|
| 新增 state | `pickerOpen: boolean`（`useState`） |
| 新增節點 | 「切換對象」鈕：放在名稱 `<span>` 之後、`{sharingToggle && ...}` 之前；`aria-haspopup="dialog"`、`aria-expanded={pickerOpen}`；以 `ref` 保存供焦點返還 |
| 渲染條件 | `status === 'ready'`（`state` 為 `default`／`independent`／`no-object` 時）；`connecting`／`unavailable` 時不渲染 |
| 不動的部分 | `data-state` 的五態判定、`brain-context-name-*` 名稱節點、`brain-context-none`、共享徽章與切換、展開的 `<dl>` |
| 註解 | `:20` 的「本單元不渲染」改寫為「切換對象鈕與選單由 `U16` 實作，見 `ObjectPicker.tsx`」 |

## 四、props／state 責任切分

| 元件 | 持有的 state | 接收的 props | 不得持有 |
|---|---|---|---|
| `ContextBar` | `expanded`（既有）、`pickerOpen` | `sharingToggle`（既有） | 清單資料；任何建立狀態 |
| `ObjectPicker` | `status: 'loading'\|'default'\|'empty'\|'error'`、`errorKind: 'forbidden'\|'other'\|null`、`groups: PickerGroup[]`、`query: string`、`openForm: {kind:'project'}\|{kind:'system', projectId:number}\|null`、`switchError: string\|null` | `onClose(): void`、`returnFocusRef` | 作業對象的副本（一律讀 `useBrainSession().target`）；`no-match` 不另存（由 `filterGroups(groups, query)` 的結果為空推得） |
| `ObjectPickerGroup` | 無 | `group`、`selectable: boolean`、`canCreateSystem: boolean`、`currentKey`、`onPick(ids)`、`onOpenCreate()`、`formOpen: boolean`、`renderForm` | 自行判定擁有者（由 `ObjectPicker` 以 `isOwnedByMe` 算好傳入，判定只有一處） |
| `ObjectCreateForm` | `name: string`、`pending: boolean`、`error: string\|null`；進行中旗標 `inFlight`（`useRef`） | `kind`、`projectId?`、`onCreated(obj)`、`onCancel()` | 直接呼叫 `createProject`／`createSystem`（只准經 `objectCreateAction`） |

### 四之一、擁有者判定只有一處（`functional-spec.md §二之一`）

- `ObjectPicker` 讀 `useAuth().user?.id`；**在它成為 `number` 前 `status` 維持 `loading`**
  （`BR12.3`），不以 `undefined` 比較。
- 每個群組在 `ObjectPicker` 內算一次 `owned = isOwnedByMe(group.project, userId)`，
  然後 `selectable = owned`、`canCreateSystem = owned && can('K2','edit')` 傳給
  `ObjectPickerGroup`。`BR13.2` 與 `BR14.3` 因此**不可能**分歧。
- **這不是授權**（`functional-spec.md §九之二` IAM 列）。

### 四之二、選定與建立後的流向

| 事件 | 呼叫 | 之後 |
|---|---|---|
| 選定可選列 | `setWorkTarget(targetIdsFor…(row))` | `true` → `onClose()`；`false` → `setSwitchError(...)`、`announce(...)` |
| 建立成功 | `ObjectCreateForm` 呼叫 `onCreated(obj)` → `ObjectPicker` 以 `setWorkTarget(targetIdsFor…(obj))` 切換 | `true` → `announce('已建立並切換到 …')`、`onClose()`；`false` → 保持開啟、提示「已建立，但目前無法切換」、重抓清單 |

state 更新一律回傳新物件（`react-hooks/immutability` 為 error 級）。

## 五、資料抓取形狀

### 五之一、兩層抓取（`team.md` 的 lint 結構約束，違反即 CI 紅燈）

```ts
// objectPickerData.ts —— 純抓取，不碰 state
export async function fetchPickerGroups(token: string, queue: FanoutQueue): Promise<PickerGroup[]> {
  const projects = await listProjects(token);
  const systems = await Promise.all(projects.map((p) => queue.enqueue(() => listSystems(token, p.id))));
  return projects.map((project, i) => ({ project, systems: systems[i] }));
}
// ObjectPicker.tsx 的 useEffect：建 queue → fetchPickerGroups(...).then(setGroups／setStatus)
//   .catch(依 ApiError.status 403 → errorKind 'forbidden'，其餘 'other'；FanoutCancelled 忽略)
//   cleanup：cancelled = true；queue.cancel()                         （BR12.4）
```

重試（error 態的按鈕）以一個 `reloadKey` 計數 state 觸發同一個 effect，不在事件處理器內直接
`setState` 抓取結果以外的東西。

### 五之二、可寫成純函式的計算（`functional-spec.md §九之三` 的要求）

| 函式 | 輸入 → 輸出 | 規則 |
|---|---|---|
| `isOwnedByMe(project, userId)` | `ProjectOut, number` → `boolean` | `BR13.2`、`BR14.3` |
| `targetIdsForProject(p)`／`targetIdsForSystem(s)` | → `{projectId, systemId, diagramId}`（字串化、`diagramId` 恆 `null`） | `BR11.2`、`BR14.5` |
| `currentRowKey(target)` | `WorkTargetPayload \| null` → `'system:<id>' \| 'project:<id>' \| null` | `BR13.3` |
| `filterGroups(groups, query)` | → 過濾後群組（專案名命中整組保留；否則只留命中系統） | `BR13.4` |

## 六、表單驗證

| 欄位 | 規則 | 落點 |
|---|---|---|
| 名稱（專案／系統） | 去頭尾空白後為空 → 不發請求、顯示「請輸入名稱」 | `objectCreateAction.ts:76-77`（既有，本單元不另做） |
| 名稱重複 | 伺服器 409 → 「已有同名的專案／這個專案已有同名的系統，請換一個名稱」 | `objectCreateAction.ts:26-39`、`:51-57` |
| 無權限 | 伺服器 403 → 「你沒有建立專案的權限……／你沒有在這個專案建立系統的權限」 | 同上（`AC9.2.3` 的畫面面） |
| 其他 | 422、網路失敗等 → 「建立專案／系統失敗，請稍後再試」 | 同上 |

前端不做名稱長度或字元限制——伺服器只有非空約束，前端多做一道會與伺服器規則分歧。

## 七、API 整合點

| 呼叫 | 來源模組 | 端點／訊息 |
|---|---|---|
| `listProjects(token)` | `projectsApi.ts:85` | `GET /api/hierarchy/projects` |
| `listSystems(token, id)` | `projectsApi.ts:96` | `GET /api/hierarchy/projects/{id}/systems` |
| `objectCreateAction(...)` | `objectCreateAction.ts:59` | `POST /api/hierarchy/projects`、`POST /api/hierarchy/projects/{id}/systems` |
| `setWorkTarget(ids)` | `useBrainSession()` | WebSocket `set_work_target`（帶本頁讀取段） |

全部經既有模組，本單元**不新增 `fetch` 呼叫點**，故不新增手寫 `Authorization` 標頭；
URL 組裝已由既有模組的 `apiUrl()` 承擔（K-13 `url_building`）。

## 八、無障礙

| 要求 | 實作 | 規則 |
|---|---|---|
| 覆蓋層語意 | `role="dialog"`、`aria-modal="true"`、`aria-labelledby` 指向可見標題 | `BR15.1` |
| 開啟時焦點 | 移到搜尋框 | `BR15.1` |
| 焦點陷阱 | 監聽選單內 `keydown` 的 Tab／Shift+Tab，首尾循環 | `BR15.2` |
| Escape | `creating` 時收表單、焦點回開啟它的入口；否則關閉 | `BR15.2` |
| 焦點返還 | 任何關閉路徑後焦點回 `ContextBar` 的切換鈕（`returnFocusRef`） | `BR15.2` |
| 清單列 | 每列為 `<button>`；不可選列 `aria-disabled="true"` ＋ `aria-describedby` 指向非擁有者說明；可聚焦、啟用無效 | `BR13.2`、`BR15.3` |
| 方向鍵 | 上下鍵在目前可見列間移動焦點（roving `tabIndex`），首尾不循環 | `BR15.3` |
| 目前對象 | 文字「目前」＋ `aria-current="true"` | `BR13.3` |
| 搜尋框 | `aria-label="搜尋作業對象"` | `BR15.1` |
| 播報 | `announce()`：清單載入完成、`no-match`、建立成功、切換失敗 | `BR15.4` |
| 表單錯誤 | 錯誤文字以 `aria-describedby` 連到名稱欄 | `BR14.4` |
| 對比 | 沿用既有 Tailwind token；建立送出鈕為 primary | `design-system-mapping.md` |

## 九、`data-testid` 命名

| testid | 元素 | 來源 |
|---|---|---|
| `brain-context-switch-object` | `ContextBar` 內的切換鈕 | `entry-page-ui/functional-design/frontend-components.md:143` |
| `brain-object-picker` | dialog 根節點；`data-state` 為 `loading`／`default`／`empty`／`error`／`no-match` | `interaction-spec.md:300`；`data-state` 為本站新增供 e2e |
| `brain-object-search` | 搜尋框 | `interaction-spec.md:300` |
| `brain-object-project-{projectId}` | 專案列（可選或停用）；帶 `data-selectable="true\|false"` | **本站新增**（`[OP2]`=A 對齊修正） |
| `brain-object-item-{systemId}` | 系統列；帶 `data-selectable` | `interaction-spec.md:300` |
| `brain-object-not-owned-{projectId}` | 非擁有者說明 | **本站新增**（`[OP3]`=A） |
| `brain-object-create-project` | 底部「+ 新增專案」 | `interaction-spec.md:301` |
| `brain-object-create-system-{projectId}` | 群組旁「+ 新增系統」 | **本站改名**（原 `brain-object-create-system`；`[OP4]`=A 對齊修正） |
| `brain-object-create-name` | 表單名稱欄（同時只有一張表單，故不需帶 id） | `interaction-spec.md:301` |
| `brain-object-create-submit`／`brain-object-create-cancel`／`brain-object-create-error` | 表單送出、取消、錯誤文字 | **本站新增** |
| `brain-object-retry` | error 態的重試鈕 | **本站新增** |
| `brain-object-switch-error` | 切換送出失敗的就地訊息 | **本站新增** |

`{projectId}`／`{systemId}` 分屬兩張表，id 可能相同，故專案列與系統列使用不同前綴，
不共用 `brain-object-item-{id}`。

## 十、驗證落點與本單元刻意不做

### 十之一、驗證落點（Playwright e2e 為唯一前端自動化層）

新 spec `frontend/tests/e2e/object-picker.spec.ts`，沿用 `entry-page.spec.ts` 的假大腦
伺服器（`page.routeWebSocket` ＋ `src/brain/testing/wsFrames.ts`）與 `page.route` 攔截 HTTP：

| 案例 | 斷言 | 規則／AC |
|---|---|---|
| 選系統 | `set_work_target` 訊框 payload 為 `{projectId:'P', systemId:'S', diagramId:null, segment:'shared'}`；回推前脈絡列不變、回推後更新 | `BR11.2`、`AC9.2.2` |
| 選零系統的專案 | payload 為 `{projectId:'P', systemId:null, diagramId:null, …}` | `BR13.1`、`AC9.2.1` |
| 建專案（K2 edit） | `POST /api/hierarchy/projects` 恰一次；成功後送出指向新專案的 `set_work_target`；再開選單時新專案列 `data-selectable="true"` | `BR14.2`、`BR14.5`、`AC9.2.1` |
| 建系統（擁有者 ＋ K2 edit） | `POST …/projects/{P}/systems` 恰一次；切到新系統 | `BR14.3`、`BR14.5`、`AC9.2.2` |
| 無 K2 edit | 兩種建立入口都不存在；空清單只顯示說明 | `BR14.2`、`BR14.6`、`AC9.2.3` |
| 建立回 403 | 表單顯示「無權限」文案、名稱保留、表單不收 | `BR14.4`、`AC9.2.3` |
| 非擁有者專案 | 該專案列與其系統列 `data-selectable="false"`、說明可見；點擊後**無** `set_work_target` 訊框；群組旁無「+ 新增系統」 | `BR13.2`、`BR14.3` |
| 清單失敗 | 第二個 `listSystems` 回 500 → `data-state="error"`，不渲染任何群組 | `BR12.2` |
| 鍵盤 | 開啟後焦點在搜尋框；Tab 循環不離開 dialog；Escape 關閉且焦點回切換鈕 | `BR15.1`、`BR15.2` |
| 子頁面 | `/workspace` 開啟選單並選取，送出的 `segment` 為 `workspace`；`U14` 的「已改為」提示出現 | `BR11.4` |
| `D-7` 附帶 | 無系統歸屬的既有圖在 `/workspace` 照常開啟、脈絡列只顯示圖名 | `AC9.1.3`（非本單元 AC） |

既有 brain e2e（`entry-page.spec.ts`、`entry-page-live.spec.ts`）須全綠，作為「修改 `U14`
檔案未破壞其斷言」的證據（`OPEN-OP16-4`）。`U17` 的 axe 掃描若涵蓋入口頁，選單開啟態的
掃描由 `U17` 決定是否納入，本單元不擴充 `a11y.spec.ts`。

### 十之二、刻意不做

| 不做 | 理由 |
|---|---|
| `CreateConfirmCard` | `[OP1]`=A；無觸發端（`OPEN-OP16-1`） |
| 選單內的刪除、改名 | 不在交付清單；刪除被拒訊息的指派不承接（`D-4`） |
| 架構圖層的選取 | `[OP2]`=A 未含；無依系統列圖的端點 |
| 新建圖時指派系統 | 無寫入端點（`D-5`） |
| 清除作業對象（回到「尚未選定」） | 不在交付清單；`interaction-spec.md` 的 `G-2` 落點不是本單元 |
| 前端快取清單 | `BR12.1` |
| 修改 `useWorkspaceTargetSync` | `BR11.4` |
