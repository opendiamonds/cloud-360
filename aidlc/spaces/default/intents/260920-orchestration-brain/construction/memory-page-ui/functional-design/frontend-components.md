# Frontend Components — `U15 memory-page-ui`

> 本檔規定元件階層、props／state 切分、資料抓取形狀、API 整合點、無障礙與
> `data-testid`。**互動流程與狀態機的正本是 `functional-spec.md`**（§五 `W1`–`W5`、
> §六），規則的正本是 `rules.md`（`BR31`–`BR35`）；本檔只寫「這些流程與規則落在
> 哪個元件、由誰持有哪一份 state」，不重述流程本身。
>
> 程式片段僅為介面層示意（≤15 行），實作屬 `code-generation`。

## 零、上游來源

| 來源 | 本檔用它決定什麼 |
|---|---|
| `functional-spec.md`（本單元） | `W1`–`W5` 的步驟、§六的兩個狀態機、§四的 API 實際形狀 |
| `rules.md`（本單元） | 19 條 `BR31`–`BR35` |
| `inception/refined-mockups/interaction-spec.md` Test ids、Accessibility、States 表 | `data-testid`、`region`／`h2`／live region、每區五態 |
| `inception/contract-design/contract-summary.md` `K-14` | 路由、守衛、`data_fetch_shape`、`url_building` |
| `team.md ## Code Style` | 兩層資料抓取、Context 拆兩檔、immutability、非元件 TS 檔名 camelCase |
| 既有程式（下節實測） | 可沿用的既有元件與既有形狀 |

## 一、既有程式的五項實測（本站開檔核對，各決定一個設計選擇）

| 實測 | 位置 | 決定 |
|---|---|---|
| ① `User.id` 宣告為**選填**（`id?: number`），且 `login()` 先以**不含 `id`** 的物件 `setUser`，`fetchMe` 回來後才補上 | `frontend/src/context/auth-context.ts` 的 `User`；`frontend/src/context/AuthContext.tsx` 的 `login` 與 `fetchMe`（`id: data.id`） | 登入後到 `/api/auth/me` 回來之間存在一段 `user.id === undefined` 的視窗。此時 `BR35.1` 的「你／其他使用者」**不可判定**——照字面比較會把自己的記憶標成「其他使用者」。處置見 §四之一 |
| ② `MemoryView` 已在產生的型別中，8 個欄位，`owner_user_id: number`、`expires_at?: string \| null` | `frontend/src/types/api.d.ts` 的 `components['schemas']['MemoryView']` | 型別一律取自產生的 `api.d.ts`，**不手寫 interface**（同 `membershipApi.ts` 檔頭逐字理由） |
| ③ 成員域已有「純抓取函式層」的落點與形狀 | `frontend/src/membership/membershipApi.ts`（`apiUrl()` ＋ 手寫 `Bearer` ＋ `res.ok`／`data.detail`，完全不碰 state） | 記憶域照同一形狀，新建 `frontend/src/memory/` 目錄，與 `membership/` 平行 |
| ④ `LiveRegion` 為可共用元件，`role="status"` 寫死，每頁各掛一個實例 | `frontend/src/components/LiveRegion.tsx` | 記憶頁掛一個實例，不另造播報機制 |
| ⑤ Sidebar 的 `/brain` 區塊被註解標為 `DEMO SCOPE`，「屆時整段取代」 | `frontend/src/components/Sidebar.tsx:209-216` | 「我的記憶」項**不放進**該區塊內，放在其後的獨立 `<div>`，使 `U14` 整段取代 demo 區塊時不連帶刪除它 |

附帶查出一處上游字面與出貨行為的落差（不影響本單元設計，如實記載）：產生的
`api.d.ts` 中 `MemoryView` 的 docstring 寫「**不含任何他人的資料**」，而
`memory_service.py:270-283` 的 `_visible_to` 會放行他人設為 `platform` 的列
（`functional-spec.md §四之三`）。該句在「`owner` 可見範圍的列」這個子集上為真、
對 `platform` 列為假。本單元的設計依**行為**而非該 docstring（`BR35.1`／`BR35.2`）。

## 二、元件樹

```
App.tsx
└── <Route path="/memory"> → <ProtectedRoute> → <MemoryPage />      (BR31.1)
    └── <Layout>（既有）
        ├── <Sidebar />（既有，新增一項「我的記憶」，以 canSeeMemoryEntry 判定）(BR31.2)
        └── <MemoryPage />                                  pages/MemoryPage.tsx
            ├── <h1>我的記憶</h1> ＋ 說明文字（§三之一的更正文案）
            ├── <MemoryZone kind="semantic" />              components/memory/MemoryZone.tsx
            │   └── <MemoryItem /> × N                      components/memory/MemoryItem.tsx
            │       └── <DeleteConfirmRow />（僅擁有者，confirming 時）
            ├── <MemoryZone kind="procedure" />
            │   └── <MemoryItem /> × N
            ├── <MemoryZone kind="episodic" />
            │   ├── <MemoryItem /> × N（另帶日期與保存期限列）
            │   └── <EpisodicPager />                       components/memory/EpisodicPager.tsx
            └── <LiveRegion />（既有）
```

**文字說明**：路由 `/memory` 以 `ProtectedRoute` 包 `MemoryPage`。頁面內固定三個
`MemoryZone`（語意 → 程序 → 情節，`BR32.1`），每區渲染多個 `MemoryItem`；只有
擁有者的條目在確認階段展開 `DeleteConfirmRow`；情節區另帶 `EpisodicPager`；
整頁一個 `LiveRegion`。

非元件模組（檔名 camelCase，依 `team.md` 命名慣例）：

| 檔案 | 內容 | 性質 |
|---|---|---|
| `frontend/src/memory/memoryApi.ts` | `fetchMemoryRecords(kind, offset, limit)`、`deleteMemoryRecord(id)` | 純抓取，不碰 state |
| `frontend/src/memory/memoryPaging.ts` | `EPISODIC_PAGE_SIZE = 20`、`computeEpisodicPage(items, page)`、`pageAfterRemoval(rendered, page)`、`zoneCountLabel(n, limit)` | 純函式，不碰 state、不碰 `fetch`（§五之二） |
| `frontend/src/memory/memoryEntry.ts` | `canSeeMemoryEntry(auth)` | INV-3 的單一判定（`BR31.2`） |
| `frontend/src/memory/memoryLabels.ts` | kind → 區標題、kind → test id 片段、可見範圍 → 文字 | 顯式映射表（§九之一） |

**不新增 Context**：記憶頁的 state 全部是頁面區域性的，不跨路由共享。新增 Context
依 `team.md` 須拆兩檔，而這裡沒有需要它的消費者。

## 三、頁面層的兩處文字

### 三之一、說明文字（對齊修正後的版本）

依 `functional-spec.md §三之一` 第二列，`MemoryPage` 的說明文字為：

> 這裡是大腦記住的關於你的事。你可以刪掉**自己的**任何一則；標為「平台可見
> （他人的記憶）」的列由其擁有者管理。

已核可線框的「你可以刪掉任何一則」不沿用（`BR35.2`）。

### 三之二、保存期限列

情節記憶的 `MemoryItem` 若 `expires_at` 非空，顯示「保存至 <日期>」；語意／程序
記憶的 `expires_at` 為 `null`（`memory_service.py:181-191`），**不渲染此列**，
而不是顯示「永久」——伺服器沒有宣告永久，只是沒有上界。

## 四、props／state 責任切分

| 元件 | 持有的 state | 接收的 props | 不得持有 |
|---|---|---|---|
| `MemoryPage` | `liveMessage: string` | 無 | 任何一區的條目陣列（各區自持，`BR32.2`） |
| `MemoryZone` | `status: 'loading'\|'default'\|'empty'\|'error'`、`items: MemoryView[]`、`limitUsed: number`；情節區另有 `page: number`、`hasNext: boolean` | `kind`、`currentUserId: number`、`announce(msg)` | 他區的任何 state；總筆數（不存在，`BR33.1`） |
| `MemoryItem` | `itemState: 'idle'\|'confirming'\|'deleting'\|'failed'`、`errorText: string` | `record`、`canDelete: boolean`、`onRemoved(id)` | `fetch` 以外的任何資料來源；可見範圍的輸入或放寬控件（`BR35.3`） |
| `DeleteConfirmRow` | 無 | `summary`、`onConfirm`、`onCancel` | 自己的焦點目標以外的焦點管理 |
| `EpisodicPager` | 無 | `page`、`pageSize`、`renderedCount`、`hasNext`、`isBusy`、`onPageChange` | `total`（不存在）；自行抓取 |

### 四之一、擁有者判定與 `user.id` 的未決視窗（§一實測①的處置）

- `MemoryPage` 讀 `useAuth().user?.id`。**在它成為 `number` 之前，三個
  `MemoryZone` 不掛載**（頁面顯示既有的整頁載入態）。理由：`BR35.1` 的
  「你／其他使用者」與 `BR35.2` 的 `canDelete` 都以 `user.id` 為比較基準，
  `undefined` 時兩者不可判定；先渲染再修正會讓自己的記憶短暫被標為
  「其他使用者」且沒有刪除鍵——那是一個對使用者錯誤的畫面，不是過渡動畫。
- 掛載後 `currentUserId` 以 prop 下傳；`MemoryZone` 對每則算
  `canDelete = record.owner_user_id === currentUserId`（`BR35.2`），
  `MemoryItem` 不自行讀 `useAuth()`——判定只有一處。
- **這不是授權**（`functional-spec.md §九之二` IAM 列）：前端放行一個刪除鍵，
  伺服器仍以 404 拒絕非擁有者。移除 `canDelete` 只會讓畫面出現一個必然失敗的
  按鈕，不會讓任何人刪得掉他人的記憶。
- **不過濾**（`BR31.3`）：`canDelete` 為 false 的列照樣渲染，改帶
  「平台可見（他人的記憶）」標記。

### 四之二、刪除後的集合更新

`MemoryItem` 在 204／404 時呼叫 `onRemoved(id)`；`MemoryZone` 以
`setItems((prev) => prev.filter((r) => r.memory_id !== id))` 回傳新陣列
（`BR34.4`；`react-hooks/immutability` 為 error 級）。隨後若為情節區且
`pageAfterRemoval(...)` 回傳的頁次不同，才觸發該區重抓（`BR34.6`）——
這是**頁次改變**造成的重抓，不是 `[M3]`=A 排除的「刪除後重抓」。

## 五、資料抓取形狀

### 五之一、兩層抓取（`team.md` 的 lint 結構約束，違反即 CI 紅燈）

1. `memoryApi.ts` 的函式只發請求、回傳資料或拋例外，**不碰 state**。
2. `MemoryZone` 在 `.then`／`.catch`／`.finally` 更新自己的 state。
3. `useEffect` 內以 `cancelled` flag 防卸載後 setState（翻頁時前一次請求晚到
   亦由同一 flag 丟棄，避免舊頁覆蓋新頁）。

```ts
// 介面示意，非實作
export async function fetchMemoryRecords(
  kind: MemoryKind, offset: number, limit: number,
): Promise<MemoryView[]>;          // GET /api/memory/records?kind=&offset=&limit=
export async function deleteMemoryRecord(
  memoryId: string,
): Promise<'deleted' | 'already-gone'>;  // 204 → deleted、404 → already-gone，其餘拋例外
```

`deleteMemoryRecord` 把 404 映射為一個**具名結果**而非例外，使 `BR34.5` 的
「404 視同成功」在型別上可見，而不是藏在 `catch` 裡的狀態碼比較。

### 五之二、可寫成純函式的計算（`functional-spec.md §九之三` 的要求）

| 函式 | 輸入 → 輸出 | 規則 | 要防的失敗 |
|---|---|---|---|
| `computeEpisodicPage(items, page)` | 至多 21 筆 → `{ rendered: 前 20 筆, hasNext, rangeStart, rangeEnd }` | `BR33.1`、`BR33.2` | 第 21 筆被渲染；「第 N–M 則」錯一位 |
| `pageAfterRemoval(renderedCount, page)` | → 新頁次 | `BR34.6` | 刪空後停在空白頁；第一頁時錯誤退到第 0 頁 |
| `zoneCountLabel(n, limit)` | → `"N 則"` 或 `"N+ 則"` | `BR32.4` | 滿頁時宣稱精確數 |

三者不碰 state、不碰 `fetch`、不讀 `useAuth()`。**前端無 unit 測試框架**
（`team.md`：`devDependencies` 只有 `@playwright/test`），故本輪的驗證層仍是
Playwright e2e；抽成純函式的價值是讓日後導入 unit／property-based 測試時零重構，
而不是本輪就有 PBT。導入框架是 `team.md` 的 `D（不採用）`，不由本單元夾帶。

### 五之三、三區的請求參數（`BR32.2`、`BR33.1`、`BR33.3`）

| 區 | 請求 | 取 `limit` 的理由 |
|---|---|---|
| 語意 | `?kind=semantic&limit=200` | 伺服器上限；不帶則套預設 50 |
| 程序 | `?kind=procedure&limit=200` | 同上 |
| 情節 | `?kind=episodic&offset=<(page-1)*20>&limit=21` | `20 + 1` 探測；`21 ≤ 200` 故不被 `clamp_page_size` 收斂（`functional-spec.md §四之一`） |

**不顯示總數、不使用 `PaginationControl`**（`BR33.2`）：該元件的 `total` prop
（`PaginationControl.tsx:8-11`）無資料可餵。改用本單元的 `EpisodicPager`：
「第 N–M 則」＋「上一頁」「下一頁」。

## 六、表單驗證

**本單元沒有表單**。唯一的寫入操作是刪除，而刪除沒有使用者輸入的欄位——
`memory_id` 來自伺服器回應，不經使用者編輯。可見範圍不提供任何輸入（`BR35.3`）。
故本節無驗證規則；寫下來是為了讓「沒有」成為一個可被核對的判定，而不是遺漏。

## 七、API 整合點

| 操作 | 呼叫者 | 方法與路徑 | 狀態碼處置 |
|---|---|---|---|
| 列出 | `MemoryZone`（每區一次，`W1`／`W3`） | `GET /api/memory/records` | 200 → `default`／`empty`；其餘（含 403、網路錯誤）→ 該區 `error`，**不得**顯示 empty 文案（`BR32.3`） |
| 刪除 | `MemoryItem`（`W4`） | `DELETE /api/memory/records/{memory_id}` | 204／404 → 移除該列並播報（`BR34.5`）；其餘 → `failed`，就地顯示錯誤並播報，**不移除** |

兩者皆經 `apiUrl()`（`K-14` `url_building`）並手寫 `Authorization: Bearer`。
`memory_id` 為字串（`api.d.ts` 的路徑參數型別），直接放入路徑，不轉數字。

**本單元不消費**：`POST /api/memory/records`、`PUT .../scope`、
`GET /api/memory/audit-events`（理由見 `functional-spec.md §四`）。

## 八、無障礙

| 項 | 落點 | 規格來源 |
|---|---|---|
| `h1`「我的記憶」＋ 三個 `h2`，不跳級 | `MemoryPage`、`MemoryZone` | `interaction-spec.md` Accessibility |
| 每區 `role="region"` ＋ `aria-labelledby` 指向其 `h2` | `MemoryZone` | 同上 |
| 區內 `list`／`listitem` | `MemoryZone`、`MemoryItem` | 同上 |
| `[刪除]` 的 `aria-label` 含內容摘要（「刪除：<前 30 字>」） | `MemoryItem` | 同上 |
| 確認列展開後焦點移到確認鍵；Escape 取消並還原焦點 | `DeleteConfirmRow` | `BR34.2` |
| 刪除成功後焦點移到該區 `h2`（原焦點目標已不存在） | `MemoryZone` | `functional-spec.md` `W4` 第 5 步 |
| `deleting` 的條目以 `aria-disabled` 表示，不移出 DOM | `MemoryItem` | `BR34.3` |
| 載入、載入完成、刪除成功、刪除失敗經 `LiveRegion` 播報 | `MemoryPage`（`announce` 下傳） | `interaction-spec.md`；`LiveRegion.tsx` 契約段 |
| 錯誤態的重試控件為 `<button>`，有可見文字 | `MemoryZone` | `BR32.3` |

**`role="status"` 數量**（沿用 `LiveRegion.tsx` 記載的 `OPEN-ND24-1` 同形殘留）：
記憶頁掛載時，`Layout` 的橫幅宿主與本頁的 `LiveRegion` 各一個，共兩個。
同時變動時的播報順序未定義，落點 `U17 a11y-gate`，本單元不另開項。

## 九、`data-testid` 命名

沿用 `interaction-spec.md` Test ids 的已核可名稱，並補上本站新增控件的名稱：

| test id | 元素 | 來源 |
|---|---|---|
| `memory-page` | 頁面根節點 | 已核可 |
| `memory-zone-semantic`／`memory-zone-procedural`／`memory-zone-episodic` | 三個 region | 已核可 |
| `memory-item-{id}` | 每一則（`{id}` 為 `memory_id`） | 已核可 |
| `memory-item-{id}-delete` | 刪除入口（僅擁有者） | 已核可 |
| `memory-item-{id}-delete-confirm` | 確認列的「刪除」 | 已核可 |
| `memory-pagination` | `EpisodicPager` 根節點 | 已核可 |
| `memory-item-{id}-owner` | 擁有者欄位（帶 `data-owner-user-id`） | **本站新增**（`BR35.1`） |
| `memory-item-{id}-scope` | 可見範圍欄位 | **本站新增**（`BR35.1`） |
| `memory-item-{id}-delete-cancel` | 確認列的「取消」 | **本站新增**（`BR34.2`） |
| `memory-zone-{kind}-count` | 區標題的「N 則」／「N+ 則」 | **本站新增**（`BR32.4`） |
| `memory-zone-{kind}-error`／`memory-zone-{kind}-empty`／`memory-zone-{kind}-retry` | 錯誤態、空態、重試鍵 | **本站新增**（`BR32.3`，使兩態可被機械區分） |
| `memory-pagination-prev`／`memory-pagination-next`／`memory-pagination-range` | 兩鍵與「第 N–M 則」 | **本站新增**（`BR33.2`） |
| `sidebar-memory-link` | Sidebar 的「我的記憶」 | **本站新增**（`BR31.2`） |

`{kind}` 一律取 §九之一的 test id 片段，不取 API 值。

### 九之一、`kind` 的顯式映射（`functional-spec.md §三之二`、`OPEN-MP15-4`）

| API 值（`memory_types.py:41`） | test id 片段（已核可） | 區標題 |
|---|---|---|
| `semantic` | `semantic` | 語意記憶 |
| `procedure` | `procedural` | 程序記憶 |
| `episodic` | `episodic` | 情節記憶 |

映射集中在 `memoryLabels.ts` 一處。**API 值與 test id 不得互相代用**：以
`procedure` 組 test id 會讓已核可的 `memory-zone-procedural` 永遠找不到元素；
以 `procedural` 發請求會被伺服器的封閉集合拒絕。

## 十、驗證落點與本單元刻意不做

### 十之一、驗證落點（Playwright e2e 為唯一前端自動化層）

| 對象 | 驗證方式 | 備註 |
|---|---|---|
| `BR31.1`／`BR31.2`（Sidebar 那一半） | e2e：登入後 Sidebar 出現 `sidebar-memory-link`，點擊進入 `memory-page` | INV-3 的捷徑那一半屬 `U14`（`OPEN-MP15-1`） |
| `BR32.1`–`BR32.4` | e2e：三區存在且順序固定；以路由攔截讓單一區失敗，斷言只有該區出現 `-error` 且無 `-empty` | 失敗以 Playwright 的 request interception 構造 |
| `BR33.1`／`BR33.2` | e2e：建立 21 則情節記憶，斷言第一頁 20 則、`-next` 可按、`-range` 為「第 1–20 則」 | 寫入端為 `U8` 的 `POST /api/memory/records`（`OQ-N3` 已由上游解決） |
| `BR34.1`–`BR34.6` | e2e：確認列、Escape、就地移除、刪空第二頁退回第一頁 | — |
| `BR35.1` | e2e：自己的列 `-owner` 文字為「你」且 `data-owner-user-id` 等於自己的 id | — |
| `BR35.2`（非擁有者的列） | **需要兩個使用者 ＋ 一個平台角色先執行 `PUT .../scope`**（`functional-spec.md §九` 自檢 1）。e2e 若構造成本過高，改由後端 `TestClient` 驗「放寬後他人的清單含該列」，前端 e2e 只驗「`canDelete` 為 false 的列無 `-delete`」並以路由攔截餵入他人的列 | 與 `U24` 的同形處置；最終取捨由 `code-generation` 的計畫定案 |

### 十之二、刻意不做

| 不做 | 理由 |
|---|---|
| 入口頁捷徑的渲染 | `[M4]`=A，屬 `U14`；本單元只提供 `canSeeMemoryEntry` |
| 在 `/brain` demo 區塊掛捷徑或把 Sidebar 項放進該區塊 | `Sidebar.tsx:209` 註解逐字「屆時整段取代」 |
| 顯示總筆數或沿用 `PaginationControl` | 回應無總筆數（`BR33.2`、`OPEN-MP15-2`） |
| 前端過濾他人的列 | `BR31.3`；`K-14` 逐字「前端不自行過濾」 |
| 可見範圍的設定或放寬控件 | `BR35.3`；`OQ-12` 未定案 |
| 顯示 `embedding_model` | 對「記得對不對、要不要刪」無判斷價值（`functional-spec.md §四之二`） |
| undo 刪除 | 已核可為確認而非 undo（`mockups.md` M6） |
| 本機快取記憶內容（`localStorage` 等） | 會使 ADR-0006 encryption 面由不適用轉為適用（`functional-spec.md §九之二`） |
| 導入前端 unit／component 測試框架 | `team.md` 的 `D（不採用）` |
