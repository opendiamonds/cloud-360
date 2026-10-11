# Frontend Components — `U24 member-pages-ui`

> 本檔為 `produces_kinds` 對 `ui` 單元的條件產出（`frontend-components: [ui]`）。
> 設計層級，非實作：元件樹、props／state 的責任切分、互動流程落點、表單驗證、
> API 整合點。**不含完整函式本體**（stage 檔的 Constraints：程式碼限於 ≤15 行的
> 說明性片段）。

## 零、上游來源

| 來源檔 | 用到它的什麼 |
|---|---|
| `inception/units-generation/unit-of-work.md` | `U23`／`U24` 共同的四條前端硬約束（兩層抓取、`apiUrl()`、live region、不得沿用 `AdminPage.tsx:104` 的 toast），以及 `U24` 專屬的兩條（橫幅須在落地時即在 DOM、落點為落地頁） |
| `inception/contract-design/contract-summary.md` | `K-16` 的四個 http 方法與 `on_denied`；`ReselectionOut` 的欄位集合 |
| `inception/requirements-analysis/requirements.md` | `FR12.4c`／`FR12.4c-i`／`FR12.6a` |
| `functional-spec.md`（同站） | W1–W6 流程、三個狀態機、§二之一 的 `role="status"` 硬約束 |

## 一、既有程式的三項實測（本站開檔核對，決定了三個設計選擇）

| 實測 | 位置 | 對本單元的後果 |
|---|---|---|
| **`Layout` 已有一個 banner slot** | `frontend/src/components/Layout.tsx:16` 逐字為 `<div data-slot="cost-banner" />`，位置在 `{children}` **之上**、滾動容器之內 | `[F1]`=A 不需要新的掛載機制——沿用同一個 `data-slot` 慣例加一個兄弟節點即可。這同時給了「落地時即在 DOM」一個現成的位置 |
| **就地更新有三個既有先例** | `AdminPage.tsx:153`（`map` 換一列）、`:179`（`map` 換一列）、`:200`（**`filter` 移除一列**） | `[F4]`=A 零新形狀。W5 的「移出後清單少一列」對應 `:200` 的 `filter`。**修訂 1／審查 `R-15`：該先例共三行，初版只取一行而未交代被省略的兩行。** `:201` 的 `setTotal` 遞減與 `:203` 的 `resyncCurrentPageInBackground` 存在的理由寫在 `:197-198` 的註解，逐字「不重抓的話，**下一頁會靜默略過一個帳號**」——那是**分頁**的補償。本單元不適用：實測 `list_members`（`membership_router.py:164-178`）**沒有任何 `page`／`limit`／`offset` 參數**，成員清單一次回傳全部，故無 offset 位移可補 |
| **`CapabilityRoute` 管的是能力層** | `RouteGuard.tsx:35` | 能力層可見性沿用它；**per-project 判定不能用它表達**（`K-16` 的 `two_layer_rule`），故 per-project 控件的出現依據伺服器回應 |

## 二、元件樹

```
App（既有）
└── ProtectedRoute（既有，RouteGuard.tsx:15）
    └── Layout（既有，Layout.tsx:9）
        ├── Sidebar（既有）
        ├── <div data-slot="cost-banner" />   ← 既有，不動
        ├── <div data-slot="reselection-banner">   ← 【新】[F1]=A 的落點（無 role）
        │   ├── <ReselectionBannerHost />      ← role="status"，**只放要被朗讀的文字**
        │   └── <ReselectionBannerActions />   ← **在 host 之外**（審查 R-06）
        │       ├── [知道了] [查看成員]
        │       └── <ReselectionProjectList />（可展開，[D10]=A）
        └── {children}
            └── CapabilityRoute（既有，能力層）
                ├── <MemberListPage />                 ← 【新】
                │   ├── <LiveRegion />（由 U23 提供，[F3]=A）
                │   ├── <MemberTable />
                │   │   └── <MemberRow />（管理者視角才渲染 [>]）
                │   └── <InviteMemberDialog />         ← 【新】
                └── <MemberDetailPage />               ← 【新】
                    ├── <LiveRegion />（同上）
                    ├── <MemberRoleSelect />
                    ├── <RemoveMemberButton />
                    │   └── <ConfirmDialog />（二次確認）
                    └── <MemberChangeLog />
```

**`<LiveRegion />` 不在本單元的新建清單裡**——`[F3]`=A 定它由 `U23` 建、`U24` 沿用。
本單元的完成條件因此含一條對 `U23` 的跨單元依賴，且**不新增依賴圖上的邊**
（`U23` 在既有交錯順序中本就較早落地）。

## 三、`<ReselectionBannerHost />` —— 本單元最細的一個約束

```tsx
// 說明性片段（≤15 行）。宿主無條件渲染；可互動內容在它之外。
<div data-slot="reselection-banner">
  <div role="status" data-testid="reselection-banner-host">
    {events.length > 0 && summaryText(events)}    {/* 只有文字 */}
  </div>
  {events.length > 0 && (
    <ReselectionBannerActions events={events} … />  {/* 鈕與可展開清單 */}
  )}
</div>
```

**四條不可違反的規定**（前三條來自 `functional-spec.md` §二之一，
第 4 條來自 §二之二／審查 `R-06`）：

1. **宿主無條件渲染**，即使 `events` 為空、即使抓取失敗、即使尚在載入。
2. **`role="status"` 掛在宿主上**，不是掛在稍後才插入的節點上。
   掛在後者等於把 live region 連同內容一起插入 DOM，而
   `aria-live="polite"` 在這個形狀下不會被朗讀（`[US:D-11]`）。
3. **載入中不渲染骨架。** 橫幅是通知不是內容；骨架會變成一則假通知。
4. **宿主內不得放任何可互動內容。** `role="status"` 隱含 `aria-atomic="true"`，
   所以區域內任何變動都會重新播報**整個區域**——把可展開的專案清單與兩個
   動作鈕巢在宿主內，每次展開／收合都會讓螢幕閱讀器把整則橫幅重讀一次。
   兩者放 `<ReselectionBannerActions />`（宿主的兄弟節點）。
   **axe 不會回報這一類問題**，所以沒有任何機械閘門會抓到它。

可被 e2e 斷言的形式（修訂 1／審查 `R-03`：三份產出統一用這個 `data-testid`，
且同時斷言 `role` 屬性）：落地後立刻查詢
`[data-testid="reselection-banner-host"]` 必須命中、其 `role` 屬性等於
`"status"`、資料到達前 `textContent` 為空；**展開／收合時該元素的
`textContent` 不變**（審查 `R-06`）。初版只斷言選擇器命中——把 `role`
整個拿掉仍會綠燈，而那正是整條約束的結構前提。

## 四、props／state 責任切分

| 元件 | props | 自有 state | 不得持有 |
|---|---|---|---|
| `ReselectionBannerHost` | 無（自己抓） | `events`、`loading`、`error`、`acknowledging` | 任何 per-project 授權結論 |
| `ReselectionBanner` | `events`、`onAcknowledge`、`onViewMembers` | `expanded`（純呈現狀態） | 不自己抓資料、不自己呼叫端點 |
| `MemberListPage` | 由路由取 `projectId` | `members`、`loading`、`error`、`inviteOpen`、`canManage`（**由 `BR22.3` 從 `members` 推得**） | 不自行推導「我是不是管理者」——`canManage` 只能照 `BR22.3` 從 `list_members` 結果中自己那列的 `role` 取得 |
| `MemberTable` | `members`、`canManage`、`onOpenDetail` | 無（受控） | — |
| `MemberRow` | `member`、`canManage` | 無 | **任何改角色的控件**（`AC12.2.3`） |
| `InviteMemberDialog` | `projectId`、`onInvited`、`onClose` | 表單欄位、`submitting`、`rejectionReason` | 不自行組拒絕文案（顯示 `U19` 回的理由） |
| `MemberDetailPage` | 由路由取 `projectId`／`userId` | `member`、`changeLog`、`saving`、`guardReport` | — |
| `MemberRoleSelect` | `value`、`onChange`、`disabled` | 無（受控） | — |
| `MemberChangeLog` | `entries` | 無 | 不自行記錄稽核事件 |

**`canManage` 的來源（修訂 1／審查 `R-01`）**：初版只寫「伺服器回應」，
而**沒有任何端點提供這個欄位**——`MemberView`（`membership_types.py:80-96`）
只有 `user_id`／`display_name`／`role`／`joined_at`，`K-16` 的
`resolve_project_role` 的 `consumed_by` 是 `[U20, U13, U21]`、**不含 `U24`**
且無 HTTP 端點。照初版字面實作的人做不出來。

現以 **`BR22.3`** 明訂唯一取得方式：**以自身 `user_id` 在 `list_members` 的
結果中找到自己那一列，讀它的 `role`**；`project_admin` 即 `canManage` 為真，
找不到自身即為假。讀的是伺服器給的 `role` 結論，不是拿全域角色自己算，
故不違反 `I-5`。`MemberListPage` 推得它之後以 props 傳給下層元件。

## 五、資料抓取形狀（四條新資料來源一律照此形狀）

`react-hooks/set-state-in-effect` 是 **error** 級，違反即 CI 紅燈。三層拆分：

```tsx
// ① 純抓取函式：不碰 state，回傳資料
async function fetchMembers(projectId: number): Promise<MemberView[]> {
  const res = await fetch(apiUrl(`/api/membership/projects/${projectId}/members`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? '讀取成員失敗');
  return res.json();
}
// ② 呼叫端在 .then/.catch/.finally 更新 state
// ③ useEffect 內以 cancelled flag 防卸載後 setState
```

沿用既有形狀的三處：`apiUrl()` 組 URL（不自造）、手寫 `Authorization: Bearer`
（既有 40 處同形）、以 `res.ok` 判斷並取 `data.detail` 當錯誤訊息。

## 六、表單驗證

| 欄位 | 規則 | 落點 |
|---|---|---|
| 邀請的受邀者 | 必填；未選即**停用送出鈕**（inline validation，不等送出） | 前端 |
| 邀請的角色 | 必填，預設 `一般成員`；值域為封閉列舉 `project_admin \| member` | 前端（值域）＋ 伺服器（權威） |
| **「受邀者是否具備全域功能權限」** | **前端不驗** | **僅伺服器**（端點 2 的 422）。前端無法可靠判定它，自行預判會產生一個與伺服器不一致的拒絕 |
| 角色下拉 | 與當前值相同時停用存檔鈕 | 前端 |
| 移出確認 | 需二次確認對話框 | 前端 |

**「前端不驗全域權限」是刻意的**：`FR12.6a` 的判定在伺服器，前端若先猜一次，
就會出現「畫面說不行但伺服器說可以」或反之的兩種不一致，而兩者都比多一次請求糟。

## 七、API 整合點

六個消費點與其回應處置列於 `functional-spec.md` §四，不在此重複。本檔只補**前端側**的三條：

1. **401** → 沿用既有的全站處置（不在本單元新增 401 邏輯）。
2. **403** → 關閉進行中的 modal，重抓一次清單（權限可能剛被改），並以 live region 播報。
   **橫幅的 403 是例外**（審查 `R-11`）：端點 5 的 403 代表缺 `K3 view`，屬**永久失敗**
   ——`ReselectionBannerHost` 以 `can('K3','view')` 作為發出請求的前置條件，
   不重試、也不對使用者顯示任何訊息（`BR21.3`）。實測
   `rbac_seed_data.py:343-345`：`SRE`／`Ops_Lead`／`Platform_Engineer` 的
   `K3 view` 為 False，而宿主在 `Layout` 裡，故不設前置條件時這三個角色
   **每一次落地**都會打一個必定 403 的請求。
3. **404**（僅端點 6，審查 `R-02`）→ **等價於成功**。語意逐字是「查不到該事件、
   它不屬於你，或**它已被確認**」，而該端點**不冪等**；把它當失敗會讓橫幅
   永遠清不掉（`BR26.3`）。
4. **409** → **還原**使用者剛改的值（角色下拉），並渲染 `LastAdminGuardReport`
   帶回的**每一個**專案名稱（`BR24.2`）。
5. **422**（僅端點 2，審查 `R-12`）→ 依 `detail` 的形狀分流：為**字串**時走拒絕態
   並顯示該字串；**不是字串**時（pydantic 的物件陣列）走一般錯誤路徑，
   **不把陣列當文案顯示**（`BR23.1`）。

## 八、無障礙

| 項目 | 處置 | 來源 |
|---|---|---|
| 橫幅朗讀 | 宿主 `role="status"` 無條件渲染（§三） | `[US:D-11]` |
| 載入／錯誤播報 | 經 `U23` 的 live region 元件；**不得**用 `AdminPage.tsx:104` 的 4 秒 toast | `[US:D-08]`、`[F3]`=A |
| modal 焦點 | 開啟時移入第一個欄位，關閉時歸還觸發元素 | `interaction-design-patterns.md` 既有規定 |
| 二次確認 | 破壞性動作需明確確認，焦點預設在**取消** | 線框 §25 |
| axe 掃描 | 本單元的兩頁納入 `U17 a11y-gate` 的四頁範圍 | `unit-of-work.md` 的 `U17` 變更列 |

## 九、`data-testid` 命名

依 `code-generation-guide.md` 的 `{component}-{element-role}` 與 kebab-case，
且**不得**綁動態值。本單元的清單：

`member-list-table`、`member-list-row-{userId}`、`member-list-row-detail-link`、
`member-list-invite-button`、`invite-dialog`、`invite-dialog-submit`、
`invite-dialog-rejection-reason`、`member-detail-role-select`、
`member-detail-save`、`member-detail-remove`、`remove-confirm-dialog`、
`remove-confirm-accept`、`member-change-log`、`reselection-banner-host`、
`reselection-banner-acknowledge`、`reselection-banner-view-members`、
`reselection-banner-expand`、
**`guard-report`**、**`guard-report-projects`**（修訂 1／審查 `R-14`）。

**後兩個是 `R-14` 補的**：W4／W5 的 409 分支要求畫面列出
`LastAdminGuardReport` 帶回的專案，而初版 17 個 testid 裡沒有任何一個對應
守門理由或其專案清單。守門本身的三條 AC（`AC12.3.1`–`.3`）屬 `US12.3`、
**不在本單元承載的五則內**，所以這段呈現在本站既沒有 AC、也沒有可定位的
斷言目標——這份資訊若沒被渲染或渲染錯了，不會有任何東西變紅。
`BR24.2` 的 observable 現已補上「`[data-testid="guard-report-projects"]` 內的
列數等於回應中 `projects` 陣列的長度」。

`member-list-row-{userId}` 是唯一帶動態片段的一個，且它是**容器**
（`code-generation-guide.md` 逐字允許 `user-table-row-{id}` 這個形狀），
不是 `button-${index}` 那種以索引命名的形式。

## 十、本單元刻意不做

| 不做 | 理由 |
|---|---|
| 不建 live region 元件 | `[F3]`=A：由 `U23` 建 |
| 不新增任何後端端點 | 六個消費點全部已存在（實測） |
| 不改 `ReselectionOut` | 它屬 `U19`；缺名稱的缺口是 `OPEN-MP24-1`，指派 `U24` 的 `code-generation` |
| 不自行推導 per-project 權限 | 不變量 `I-5` |
| 不前端驗全域功能權限 | §六 |
| 不碰 `AC12.4.1`／`AC12.4.2`／`AC12.5.2` | 三者皆為 `U19` 的服務側行為 |
| 不引入前端 unit／component 測試框架 | `team.md` 的 D 項不採用；唯一自動化層是 Playwright e2e |
| 不新增任何前端依賴 | 沿用既有 React／Tailwind／既有 helper |
