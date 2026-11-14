# Frontend Components — `U23 project-pages-ui`

> 建檔時間 2026-10-15T14:57:34Z（以 `date -u` 取值）。本檔描述元件層級、props／state
> 責任與 API 整合點；互動流程與狀態轉移的正本在 `functional-spec.md`，規則在 `rules.md`。
> **修訂 1**（2026-10-15T22:33:15Z）：審查 R-02（`K4 edit` 唯讀）、R-06（更新者標題來源）、
> R-08（重讀失敗）、R-10（最近變更標示）、R-11（扇出並行上限）落入 §二、§三、§六、§七、§八。

## 零、上游來源

| 檔案 | 取用的內容 |
|---|---|
| `ideation/rough-mockups/wireframes.md` §14–§18 | Sidebar「專案」項、清單／建立、三籤的版面 |
| `inception/refined-mockups/mockups.md` M10–M12 | 清單五態、建立系統入口、需求籤的未填標示與更新者 |
| `inception/refined-mockups/interaction-spec.md` | `ProjectList`、`SystemCreateAction`、`ObjectCreateAction`、不變量 `I-4` |
| `inception/contract-design/contract-summary.md` `K-19` | 本單元畫面是 `U17` 的掃描標的、四條無障礙行為 |
| `construction/requirement-field-service/code-generation/code-summary.md` §七 | 給本單元的四條交接 |
| `construction/member-pages-ui/` | `LiveRegion` 的沿用、`[成員]` 入口、`api.d.ts` 取型別的先例 |

## 一、既有程式的實測（決定了下列設計）

| 實測 | 結果 | 設計後果 |
|---|---|---|
| `frontend/src/App.tsx` 的路由 | 無任何 `/projects` 頁；只有 `U24` 的 `/projects/:projectId/members` 與其詳情 | 本單元新增三條路由，與既有兩條共存（react-router-dom `^7.18.2` 以靜態段優先於參數段，`/projects/new` 不會被 `:projectId` 吃掉） |
| `frontend/src/components/Sidebar.tsx` | `<NavLink` 共 7 處；能力判定用 `useAuth().can(story, action)`（`:8`、`:19-21`） | 「專案」項沿用同一判定與 `linkClass`，位置依線框 §14 為第一層獨立項 |
| `frontend/src/components/LiveRegion.tsx` | `U24` 已交付，`role="status"` 寫死，props 為 `message`、`srOnly` | 沿用，不另建 |
| `openapi.json` 的 hierarchy 路徑 | 無單一專案 `GET`；`ProjectOut` 欄位為 `id`／`name`／`owner_user_id`／`is_default`／`created_at`，無系統數 | 詳情頁的專案資料取自清單回應；系統數由各專案的系統清單得出 |
| `FieldSetView` | 必有 `system_id`／`unfilled_count`／`input_hint`／`groups`；`FieldGroupView` 有 `title`／`filled_count`／`total_count`／`fields` | 標籤、組標題、`x/y`、提示文字全部取自回應 |

## 二、元件樹

```
App.tsx（就地修改：新增三條路由）
├── /projects            → ProtectedRoute → CapabilityRoute(K2, view) → ProjectsListPage
├── /projects/new        → ProtectedRoute → CapabilityRoute(K2, edit) → ProjectCreatePage
└── /projects/:projectId → ProtectedRoute → CapabilityRoute(K2, view) → ProjectDetailPage

Sidebar.tsx（就地修改：第一層新增「專案」NavLink，can('K2','view') 時渲染）

ProjectsListPage
├── <h1>專案</h1> ＋ [+ 建立專案]（can('K2','edit') 時；main 內第一個可聚焦元素）
├── ProjectListSkeleton           （loading）
├── ProjectListEmpty              （empty：說明 ＋ [+ 建立第一個專案]）
├── ProjectListError              （error：「這不是你沒有專案」＋ [重試]）
├── <ul> ProjectListRow × n       （default：名稱、系統數、建立日期、系統名或「尚無系統」、[>]）
└── <LiveRegion />                （既有，U24）

ProjectCreatePage
├── <form> label「專案名稱」＋ input ＋ [建立]（pending 態）＋ 錯誤文字
└── <LiveRegion />

ProjectDetailPage（持有 BR85.1 的單一欄位狀態）
├── ProjectDetailHeader          （麵包屑「專案 / <名稱>」、[成員]）
├── ProjectTabs                  （role="tablist"；總覽／需求（K4 時）／記憶摘要）
├── OverviewTab   （tabpanel）
│   ├── CountList：系統 N ＋ SystemCreateAction、架構圖「尚無法取得」、未填需求欄位 N（K4 時）
│   ├── RecentChanges            （只含經大腦、且為你自己擁有之圖的變更，最多 5 筆，BR86.2）
│   └── PendingRequirements      （K4 時；由同一份欄位狀態推導）
├── RequirementsTab（tabpanel，K4 view 時）
│   ├── RequirementsEmpty        （無系統：說明 ＋ SystemCreateAction）
│   ├── SystemSelect             （作業對象：該專案的系統）
│   ├── ReadonlyNotice           （無 K4 edit 時：「你可以檢視需求欄位，但沒有編輯權限」，BR84.7）
│   ├── input_hint 文字
│   ├── <fieldset> FieldGroup × g（legend＝title，x/y＝filled_count/total_count）
│   │   └── RequirementField × f （label ＋ input（無 K4 edit 時 readOnly）＋「未填」＋ 更新者
│   │                              ＋「未儲存」或「已儲存、重新整理失敗」）
│   ├── [儲存]                   （僅 K4 edit 時渲染，BR84.7）
│   └── [重新整理]               （儲存後重讀失敗時，BR85.6）
├── MemorySummaryTab（tabpanel）  （固定說明「專案記憶的彙整尚未提供」＋ 唯讀說明）
├── ProjectNotFound              （BR83.4）
└── <LiveRegion />

非視覺模組
├── src/projects/projectsApi.ts     （純抓取：listProjects／listSystems／createProject／createSystem／listDiagramChanges）
├── src/projects/requirementsApi.ts （純抓取：readFields／writeField）
└── src/projects/objectCreateAction.ts（BR82.1 的唯一建立寫入點，U16 之後沿用）
```

`SystemCreateAction` 是同一個元件在兩處渲染（總覽計數旁、需求籤空狀態），兩處都呼叫
`objectCreateAction`。

## 三、props／state 責任切分

| 元件 | 持有的 state | 從 props 取得 |
|---|---|---|
| `ProjectsListPage` | `projects`、`systemsByProject`（每專案：清單或失敗）、`status`、`liveMsg` | — |
| `ProjectCreatePage` | `name`、`pending`、`error`（三類之一） | — |
| `ProjectDetailPage` | `project`（自清單回應挑出）、`systems`、`fieldsBySystem: Map<system_id, FieldSetView \| 'failed'>`、`status`、`liveMsg`；目前籤取自網址 | — |
| `OverviewTab` | `changes`、`changesStatus` | `systems`、`fieldsBySystem`、`canSeeFields`、`isOwner` |
| `RequirementsTab` | `selectedSystemId`、`drafts: Map<field, string>`、`fieldErrors`、`savedStale: Set<field>`、`saving` | `systems`、`fieldsBySystem`、`canEdit`（= `can('K4','edit')`）、`groups`（供 `BR84.4` 的標題比對）、`onSaved(systemId): Promise<'ok' \| 'reload-failed'>` |
| `SystemCreateAction` | `open`、`name`、`pending`、`error` | `projectId`、`onCreated()` |
| `RequirementField` | — | `field: FieldView`、`draft`、`error`、`stale`、`readOnly`、`requesterTitle`（`BR84.4` 比對結果，`null` 時顯示「由大腦」）、`onChange` |

**`fieldsBySystem` 只有一份，由 `ProjectDetailPage` 持有**（`BR85.1`）。總覽與需求籤都只讀
它；`RequirementsTab` 儲存完成後呼叫 `onSaved(systemId)`，由頁面重讀該系統並以新物件取代
Map 中那一筆（不就地修改，`react-hooks/immutability`）。

**`drafts` 與伺服器值分開**：重讀結果只覆蓋「沒有未儲存草稿」的欄位；失敗欄位的草稿保留
（`BR84.5`）。`onSaved` 回 `'reload-failed'` 時，成功欄位的草稿**也不清除**、改列入
`savedStale`，頁面把 `fieldsBySystem` 該筆設為 `'failed'`（`BR85.6`）。`canEdit` 為假時
不建立任何草稿（`BR84.7`）。

## 四、資料抓取形狀（`BR88.1`）

照 `AdminPage.tsx` 的兩層形狀：

```text
// 純抓取：不碰 state
export async function listSystems(token: string, projectId: number): Promise<SystemOut[]>;

// 呼叫端（effect 內）
useEffect(() => {
  let cancelled = false;
  loadDetail(token, projectId)
    .then((d) => { if (!cancelled) setDetail(d); })
    .catch(() => { if (!cancelled) setStatus('error'); });
  return () => { cancelled = true; };
}, [token, projectId]);
```

`loading` 的初始播報文字以 `useState` 初始值帶入，不在 effect body 內同步 `setState`
（`U24` code-summary §三 第 2 點實測過 lint 會擋）。

型別一律取自 `src/types/api.d.ts` 的 `components['schemas'][...]`（`ProjectOut`、`SystemOut`、
`FieldSetView`、`FieldGroupView`、`FieldView`、`DiagramChangeOut`），不手寫 interface——沿用 `U24`。

## 五、表單驗證

| 表單 | 規則 | 失敗呈現 |
|---|---|---|
| 建立專案／系統 | 名稱去頭尾空白後不得為空 | 送出前擋下，輸入框下方文字「請輸入名稱」，以 `aria-describedby` 關聯 |
| 建立專案／系統 | 伺服器 409／403／其他 | 三類文案（`BR82.2`），名稱保留 |
| 需求欄位 | 前端不做格式驗證（欄位語意由後端定義，前端不持有欄位規格） | 伺服器 422 的 `detail` 逐字顯示於該欄下方，並標「未儲存」 |

## 六、API 整合點

| # | 方法與路徑 | 呼叫點 | 次數 |
|---|---|---|---|
| 1 | `GET /api/hierarchy/projects` | 清單頁、詳情頁（挑出該專案） | 每次進頁 1 |
| 2 | `GET /api/hierarchy/projects/{project_id}/systems` | 清單頁每列、詳情頁 | 清單頁 P 次；詳情頁 1 次 ＋ 建立系統後 1 次 |
| 3 | `POST /api/hierarchy/projects` | `objectCreateAction(kind='project')` | 每次使用者送出 1 |
| 4 | `POST /api/hierarchy/projects/{project_id}/systems` | `objectCreateAction(kind='system')` | 每次使用者送出 1 |
| 5 | `GET /api/requirements/systems/{system_id}/fields` | 詳情頁（K4 時） | 進頁 S 次；每次儲存完成後 1 次 |
| 6 | `PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key}` | `RequirementsTab` 儲存 | 每個已改動欄位 1 |
| 7 | `GET /api/hierarchy/diagram-changes?system_id=` | `OverviewTab` 最近變更 | S 次 |

P 為可見專案數、S 為該專案系統數。**本單元不呼叫** `DELETE .../fields/...`（清空走空值
`PUT`，`BR84.6`）、任何 `/api/memory/*`（`BR86.3`）、`/api/collab/diagrams`（`BR86.1`）。
請求數上界交 `nfr-requirements`（`OPEN-PP23-5`）；**未定案前的預設**是 `BR88.3`：清單頁的 P 次
端點 2、詳情頁的 S 次端點 5 與 S 次端點 7，各頁共用一個**並行上限 4** 的佇列，依 id 遞增發出、
不截斷總數。端點 6 的 k 次 `PUT` 是一次使用者動作，不進佇列（它們彼此獨立，且 k 為使用者
改動的欄位數）。

端點 1、2 的伺服器行為由本單元的 code-generation 修改（`BR87`），前端呼叫形狀不變。
端點 6 只在 `can('K4','edit')` 時可能被呼叫（`BR84.7`）。

## 七、無障礙

| 元件 | 要求 | 規則 |
|---|---|---|
| 清單頁 | `h1`「專案」；清單為 `ul`／`li`；建立按鈕為 `main` 內第一個可聚焦元素；空狀態說明為靜態文字 | 線框 §15 |
| 清單頁 | loading → error 播報一次 | `BR88.2` |
| 三籤 | `role="tablist"`／`tab`／`tabpanel`、`aria-selected`、`aria-controls`；左右方向鍵移動、Home／End 到首尾；僅目前籤 `tabIndex=0` | `BR83.1` |
| 計數 | `h2` 之下的清單（`dl` 或 `ul`），數字不靠顏色 | 線框 §16 |
| 建立系統 | 可及名稱為「建立系統」完整字串，`aria-describedby` 指向「系統 N」 | `interaction-spec.md` |
| 需求欄位 | `fieldset`＋`legend`；`label` 在輸入框上方；「未填」「未儲存」「已儲存、重新整理失敗」皆為文字並由 `aria-describedby` 關聯 | `BR84.2`、`BR84.5`、`BR85.6` |
| 需求欄位（無 `K4 edit`） | 以 `readOnly` 輸入框呈現（不用 `disabled`：`readOnly` 仍可聚焦、可被讀出值與可及描述）；唯讀說明為靜態文字、位於欄位組之前 | `BR84.7` |
| 儲存結果 | 全部成功／部分失敗／已儲存但重新整理失敗各播報一次 | `BR88.2`、`BR85.6` |

`U17 a11y-gate` 以 `K-19` 掃描本單元畫面；可定址的掃描點為 `/projects`、`/projects/new`、
`/projects/:id?tab=overview`、`?tab=requirements`、`?tab=memory`。

## 八、`data-testid` 命名

沿用 `U24` 實際落地的無前綴形式（`member-list-row-<id>` 等），本單元用 `project-` 前綴：

| testid | 元素 |
|---|---|
| `sidebar-projects-link` | Sidebar「專案」項 |
| `project-list`、`project-list-row-<id>`、`project-list-empty`、`project-list-error`、`project-list-retry` | 清單頁 |
| `project-create-button`、`project-create-name`、`project-create-submit`、`project-create-error` | 建立 |
| `project-tab-overview`、`project-tab-requirements`、`project-tab-memory` | 籤 |
| `project-count-systems`、`project-count-diagrams`、`project-count-unfilled` | 總覽計數 |
| `system-create-action` | 建立系統 |
| `project-recent-changes`、`project-pending-requirements` | 總覽兩區 |
| `requirements-empty`、`requirements-system-select`、`requirements-group-<group_key>`、`requirements-field-<group_key>-<field_key>`、`requirements-unfilled-<group_key>-<field_key>`、`requirements-save`（僅 `K4 edit` 時存在） | 需求籤 |
| `requirements-readonly-notice`（僅無 `K4 edit` 時存在）、`requirements-updater-<group_key>-<field_key>` | 需求籤的唯讀狀態與更新者標示（`BR84.7`、`BR84.4`） |
| `requirements-saved-stale-<group_key>-<field_key>`、`requirements-reload` | 儲存後重讀失敗（`BR85.6`） |
| `memory-summary-unavailable` | 記憶摘要籤 |
| `project-members-link` | 頁首 `[成員]` |
| `project-not-found` | 查不到態 |

`K-19` 寫「沿用 `U14` 的 `brain-*` 慣例」，但 `U14` 尚未落地、而 `U24` 已落地的實際形式是
無前綴；本單元以已交付程式為準，與 `U24` 一致（見 `functional-spec.md` 開放項 `OPEN-PP23-7`）。

## 九、本單元刻意不做

| 不做 | 理由 |
|---|---|
| 專屬的清空控件 | `[US:D-15]`；空值儲存即清空（`BR84.6`） |
| `[設定]` 按鈕 | `[PP2]`=A，無目的地（`OPEN-PP23-4`） |
| 架構圖計數、專案記憶彙整的資料來源 | `[PP2]`=A（`OPEN-PP23-1`、`OPEN-PP23-3`） |
| 另建 live region 元件 | 沿用 `U24` 的 `LiveRegion` |
| 刪除專案／系統的畫面 | 已核可線框 §15–§18 沒有它 |
| 前端欄位格式驗證 | 前端不持有欄位規格；單一真實來源在後端 |
