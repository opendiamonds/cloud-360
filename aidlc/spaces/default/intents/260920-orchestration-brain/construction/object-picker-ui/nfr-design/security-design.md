# Security Design — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:14:17Z（`date -u` 取值）。本站未執行任何程式；行號皆於撰寫當下實讀。
>
> **綁定**：`nfr-requirements-corrections.md` 的 `N-03`（lint 承載）、`N-04`（`F-01` 選擇與 404 成因）、`N-05`（範圍與基準）取代凍結的
> `security-requirements.md` 對應段落；`functional-spec-corrections.md` 的 `F-01`／`F-04` 同時生效。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/security-requirements.md` ＋ `nfr-requirements-corrections.md` | `OPN-11`–`OPN-16`、`N-03`–`N-05` |
| `../nfr-requirements/tech-stack-decisions.md` | `NFR5.160`、`NFR8.160`、`OPN-21`–`OPN-26` |
| `../functional-design/functional-spec.md` §二之一、§九之二 | 擁有者判定同源、ADR-0006 四面向 |
| repo 實測 | `frontend/eslint.config.js:11-34`（`WS_SUBPROTOCOL_RESTRICTIONS`）、`:54-97`（flat config 兩個區塊）、`:88`（app 區塊的 `no-restricted-syntax`）；`projectsApi.ts:106-130`（`createProject`／`createSystem` 匯出）；`objectCreateAction.ts:51-57`（`classify`）；`hierarchy_router.py:250-252`（被移出的建立者回 404） |

## 一、lint 區塊：把「必須紅燈」接到 CI（`N-03`）

在 `frontend/eslint.config.js` 的 `defineConfig([...])` 陣列**末端**新增一個區塊（置於 tests 區塊之後；選單檔案不在 `tests/` 下，兩區塊不重疊）：

```js
// U16（nfr-requirements N-03）：選單檔案集合的禁令。no-restricted-syntax 在 flat config
// 以後者取代前者，故必須展開 WS_SUBPROTOCOL_RESTRICTIONS，否則這幾個檔會失去 ADR-0019 §5 的三條。
const OBJECT_PICKER_RESTRICTIONS = [
  { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: '選單名稱一律以文字節點呈現（OPN-13）。' },
  { selector: "AssignmentExpression > MemberExpression.left[property.name=/^(innerHTML|outerHTML)$/]", message: '選單不得指派 innerHTML／outerHTML（OPN-13）。' },
  { selector: "NewExpression[callee.name='RegExp']", message: '搜尋以子字串比對，不得把輸入編譯成正規表示式（OPN-14）。' },
  { selector: "CallExpression[callee.name='RegExp']", message: '搜尋以子字串比對，不得把輸入編譯成正規表示式（OPN-14）。' },
  { selector: "NewExpression[callee.name='WebSocket']", message: '選單只經 useBrainSession().setWorkTarget 送出（NFR5.160）。' },
]
```

```js
{
  files: ['src/brain/objectPickerData.ts', 'src/brain/objectPickerModel.ts', 'src/components/brain/ObjectPicker*.tsx'],
  rules: {
    'no-console': 'error',
    'no-restricted-globals': ['error',
      { name: 'localStorage', message: 'OPN-15' }, { name: 'sessionStorage', message: 'OPN-15' },
      { name: 'indexedDB', message: 'OPN-15' }, { name: 'caches', message: 'OPN-15' }],
    'no-restricted-imports': ['error', { paths: [{
      name: '../../projects/projectsApi', importNames: ['createProject', 'createSystem'],
      message: '建立一律經 objectCreateAction（BR14.1／OPN-11）。' }, {
      name: '../projects/projectsApi', importNames: ['createProject', 'createSystem'],
      message: '建立一律經 objectCreateAction（BR14.1／OPN-11）。' }] }],
    'no-restricted-syntax': ['error', ...WS_SUBPROTOCOL_RESTRICTIONS, ...OBJECT_PICKER_RESTRICTIONS],
  },
},
```

**注意事項**：
- `no-restricted-imports` 以**匯入路徑字串**比對，兩個深度（`src/brain/` 與 `src/components/brain/`）各寫一筆；`code-generation` 依實際相對路徑核對。
- `no-restricted-globals` 擋不住 `window.localStorage`；補一條 `no-restricted-syntax` 選擇器 `MemberExpression[object.name='window'][property.name=/^(localStorage|sessionStorage|indexedDB|caches)$/]`。
- 突變驗證（`OPN-25`）：對每條規則各加一行違規 → `npm run lint` 紅 → 還原；結果記入 `automation-test-plan.md`。
- 這是修改共用設定檔，code-summary 須揭露；既有兩個區塊的內容**一行不動**。

## 二、IAM：呈現層判定（`OPN-11`、`OPN-12`、`OPN-16`）

### 二之一、單一擁有者判定

`objectPickerModel.ts` 匯出 `isOwnedByMe(project: ProjectOut, userId: number): boolean`，回傳 `project.owner_user_id === userId`。可選性（`BR13.2`）與「+ 新增系統」的渲染（`BR14.3`）
**都呼叫它**，不得另寫比較式。`userId` 只在 `identity === 'ok'`（`performance-design.md` §四）時存在，選單在此之前不渲染任何可選列（`BR12.3`），故不需要處理 `undefined`。

### 二之二、建立入口

| 入口 | 渲染條件 | 伺服器的實際判定 |
|---|---|---|
| 「+ 新增專案」 | `can('K2','edit')` | `require_story_action` 經 facade `user_can`（`F-01` 更正後的描述） |
| 「+ 新增系統」（每群組） | `isOwnedByMe(p, userId) && can('K2','edit')` | 同上 ＋ 擁有者檢查 ＋ 可見性守門（不可見回 404） |

### 二之三、404 路徑（`OPN-16`，以 `N-04` 為準）

可達情境只有「建立者在選單開啟後被移出專案」：前端條件仍放行，伺服器回 404，`objectCreateAction` 歸 `other`，顯示「建立系統失敗，請稍後再試」、名稱保留。
本站不改 `objectCreateAction`（`INV-2`）；此情境的文案是否可接受為關卡事項 `G-6`。**下次開啟選單時該專案已不在清單**（`list_visible_projects` 不再回它），
使用者不會被困在重試迴圈超過一次開啟。

## 三、輸入與輸出（`OPN-13`、`OPN-14`）

- 名稱一律以 JSX 文字子節點呈現；`title`／`aria-label` 屬性若帶名稱，同樣以 React 屬性傳值（會被跳脫）。由 §一的 lint 擋 `dangerouslySetInnerHTML` 與 `innerHTML`。
- 搜尋以 `performance-design.md` §二的 `normalize` ＋ `includes`；lint 擋 `RegExp`。e2e 以 `(`、`[`、`\` 驗證不拋錯。

## 四、資料保護與 log（`OPN-15`）

- lint 擋 `console`、四種瀏覽器儲存。
- e2e 以**進入選單前為基準**計數主控台訊息，選單一輪期間新增 **0**（`N-03`；不比對名稱字串）。
- 選單不碰 token：`listProjects`／`listSystems`／`objectCreateAction` 以 `useAuth().token` 為引數呼叫，標頭由既有 `requestJson` 組（`projectsApi.ts:71`）。

## 五、型別邊界（`OPN-21`）

`objectPickerModel.ts` 的 `targetIdsForProject(p)` 回 `{ projectId: String(p.id), systemId: null, diagramId: null }`、`targetIdsForSystem(p, s)` 回
`{ projectId: String(p.id), systemId: String(s.id), diagramId: null }`；`currentRowKey(target)` 讀 `WorkTargetPayload`（`ws-contract.d.ts:319` 起）的字串 id 產生
`"p:<id>"`／`"s:<id>"`，群組與列的 key 以 **同一個函式**從數字 id 產生（`rowKey('p', p.id)` 內部 `String()`），兩邊都經過轉換，杜絕一邊漏轉。

## 六、突變清單（`code-generation` 逐一執行，結果記入 code-summary 與 `automation-test-plan.md`）

| # | 突變 | 預期紅燈 |
|---|---|---|
| M1 | 拿掉「+ 新增專案」的 `can('K2','edit')` | e2e：無 `K2 edit` 角色看得到入口 |
| M2 | 「+ 新增系統」改用另一份比較式（方向相反） | e2e：非擁有者群組出現入口 |
| M3 | 名稱改用 `dangerouslySetInnerHTML` | lint ＋ e2e（`window.__xss`） |
| M4 | 搜尋改 `new RegExp(query)` | lint ＋ e2e（輸入 `(`） |
| M5 | 加 `console.log(groups)` | lint ＋ e2e 主控台計數 |
| M6 | 加 `sessionStorage.setItem` | lint ＋ e2e 鍵集合比對 |
| M7 | 直接 `import { createProject }` | lint |
| M8 | `setWorkTarget` 傳數字 id | e2e：送出訊框的 `projectId` 不是字串、「目前」不出現 |
| M9 | 拿掉送出鈕的 `useRef` 單發鎖、只靠 state | e2e：連點 3 次發出 2 次以上 POST（以延遲回應放大競態） |
| M10 | `ensureSystems` 不檢查 `idle` | e2e：收起再展開時系統請求增加 |
| M11 | 斷線時不清 `pickerOpen` | e2e：重連 ready 後選單自己出現 |

## 七、ADR-0006 四面向（逐格對照上游 `security-requirements.md` §六）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用（相同） | **適用（相同）** | §二把判定落成單一函式與明確渲染條件；伺服器仍是授權點 |
| **Encryption** | 不適用 | **不適用（相同）** | 零持久化；§四的 lint 讓「不寫瀏覽器儲存」可被 CI 偵測，上游的判定失效條件因此有了機械守門 |
| **Network exposure** | 不適用 | **不適用（相同）** | 零新端點；請求數上界見 `performance-design.md` §一之三 |
| **Audit logging** | 不適用 | **不適用（相同）** | 建立的稽核由 `U7` 承擔；本單元零主控台輸出 |

## 八、PBT hard constraint

**不適用**，與上游一致。`isOwnedByMe`、`filterGroups`、`rowKey` 三個純函式以 e2e 例子驗證（M2、M4、M8）；前端無 unit 框架（`team.md` D 不採）。

## 九、殘留（供關卡知情接受）

| # | 殘留 | 處置 |
|---|---|---|
| S-1 | lint 只以 AST 比對，擋不住經變數間接取得的儲存或主控台物件（例如 `const g = globalThis; g['local' + 'Storage']`） | 擋無心之失、擋不住刻意繞過（與 `eslint.config.js:84-87` 對 ADR-0019 §5 的殘留同型）；刻意繞過會在 code review 留痕 |
| S-2 | 被移出的建立者看到「請稍後再試」 | 關卡 `G-6` |
| S-3 | `F-02` 清 `pickerOpen` 的兩種寫法未實證通過 lint | `code-generation` 以 `npm run lint` 實證並寫入 code-summary（`performance-design.md` §五） |

## 十、更正附錄的逐條落點

| 更正 | 本站落點 |
|---|---|
| `F-01` | §二之二、§二之三 |
| `F-02` | `performance-design.md` §五 |
| `F-03` | `performance-design.md` §四 |
| `F-04` | `logical-components.md` §一（選單內播報區）；`performance-design.md` §五、§七 |
| `F-05` | `performance-design.md` §一之二、§一之三 |
| `F-06` | `logical-components.md` §一、§二 |
| `F-07`、`F-08` | 非本站範圍（關卡 `G-1`、`G-3`） |
| `N-01` | `performance-design.md` §四 |
| `N-02` | `performance-design.md` §一、§二 |
| `N-03` | §一、§四 |
| `N-04` | §二之三 |
| `N-05` | §一（檔案集合）；比較基準見 `logical-components.md` §三 |
| `N-06` | `performance-design.md` §七；axe 兩態見 `logical-components.md` §二 |
| `N-07` | §五 |
