# Code Summary — `U24 member-pages-ui`

> 方法論 **`test-after`**（指紋 `sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77`，
> 與 dispatch 標記相符）。適用層只有 **Frontend behavior**——data model／repository／
> API endpoint 三層皆屬 `U19`，故照計畫 Step 1–14 逐步執行，未重排成 TDD。
>
> **零新依賴、零新環境變數、零後端變更、零 schema／seed 變更**（逐項查證見 §六）。

## 一、建立與修改的檔案（10 支，2333 行含註解）

| # | 檔案 | 行數 | 性質 |
|---|---|---|---|
| 1 | `frontend/src/membership/failureSignal.ts` | 67 | 新建 |
| 2 | `frontend/src/membership/membershipApi.ts` | 336 | 新建 |
| 3 | `frontend/src/components/LiveRegion.tsx` | 56 | 新建（可共用，`HO-U24-1`） |
| 4 | `frontend/src/components/membership/ReselectionBanner.tsx` | 257 | 新建 |
| 5 | `frontend/src/components/membership/InviteMemberDialog.tsx` | 189 | 新建 |
| 6 | `frontend/src/pages/MembersListPage.tsx` | 227 | 新建 |
| 7 | `frontend/src/pages/MemberDetailPage.tsx` | 357 | 新建 |
| 8 | `frontend/src/components/Layout.tsx` | 32 | **就地修改**（`+10`，原 22 行） |
| 9 | `frontend/src/App.tsx` | 195 | **就地修改**（`+35`，兩條路由） |
| 10 | `frontend/tests/e2e/member-pages.spec.ts` | 617 | 新建（8 個案例） |

Brownfield 規則已遵守：第 8、9 項為**既有檔就地修改**，未產生任何 `*_modified.tsx`。
完整清單與「刻意未改動」的 9 項見 `source-manifest.json`。

### 一之一、幾個值得指名的實作決定

- **型別取自產生的 `api.d.ts`，不手寫 interface**（`membershipApi.ts` 的
  `components['schemas']['MemberView']` 等）。這沿用 `AdminPage.tsx:8-13` 的逐字
  理由，也是對 `team.md` 所記「`tsc -b` 對前後端 schema 落差無效」那條缺口能做的
  最大縮窄——手寫 interface 與後端回應之間沒有任何編譯期連結。
- **`FailureSignal` 的兩欄是字面值聯集**，故 `kind: \`x:${displayName}\`` 與
  `endpoint: '/api/membership/projects/7/members/42'` **都無法編譯**。
  `emitFailureSignal()` 的簽章只收 `FailureSignal`，呼叫端在語法上無處附加
  使用者文字。
- **`<LiveRegion />` 的 `role="status"` 寫死、不開放 prop**（`[ND1]`=C 被排除：
  `role="alert"` 會打斷朗讀，而上游無任何需求區分 polite／assertive）。
  可共用性已由本單元的**三個**消費點（清單頁、詳情頁、邀請對話框）實地證明。
- **橫幅直接渲染於 `Layout.tsx` 的 React 樹內**，未使用 `slotRegistry` portal——
  三個理由中最硬的一條是 `slotRegistry.tsx:9-10` 在元素不存在時
  `return () => undefined`（**靜默 no-op**），而 `BR21.1` 要求無條件渲染。
- **`BR21.3` 的 403 永久失敗閂**（`bannerForbiddenInThisSession`）是我在收尾
  自檢時發現漏掉後補上的：`can("K3","view")` 前置條件只擋「本來就沒權限」，
  規則另要求「發出後才發現 403」時本工作階段不再發請求。閂放在模組層而非
  state（要跨元件實例存活），且**不得用瀏覽器儲存**（`NFR4.80` 禁止），
  故整頁重新載入時會重置——如實記載，不假裝是「永久」。

## 二、8 個案例與突變驗證（**全部實跑，非清單**）

`describe` 為 **`U24 member pages`**（`spec:196`）；8 個 `test` 字串**已凍結**
（TCMS 以 `<describe> › <test>` 為鍵，改名會讓既有案例變成孤兒）。

執行指令（單元範圍、精確到檔）：

```bash
cd frontend && npx playwright test tests/e2e/member-pages.spec.ts
```

**結果：8 passed**（對生產建置連續 4 次全綠，見 §五）。

| # | 案例（test 字串） | 突變內容 | 紅燈？ | 還原後 |
|---|---|---|---|---|
| 1 | `renders the member list up to 100 rows…` | 渲染閘 `>` 改為 `>=`（off-by-one） | **RED** | GREEN |
| 2 | `queries pending reselections once per landing…` | 移除 `can('K3','view')` 前置條件（退回 `BR21.3` 的重試語意） | **RED** | GREEN |
| 3 | `updates the list in place after invite…` | `handleRemove` 的 `.then` 內多呼叫一次 `fetchMembers` | **RED** | GREEN |
| 4 | `issues exactly one member-list request…` | effect 內多呼叫一次 `fetchMembers`（模擬 `canManage` 另發請求） | **RED** | GREEN |
| 5 | `hides all four manager controls for a project admin lacking global K3 edit` | `canManage` 去掉 `&& can('K3','edit')`（只留 per-project 段） | **RED** | GREEN |
| 6 | `shows a read-only list to a plain project member…` | `canManage` 去掉 per-project 段（只留全域 `can('K3','edit')`） | **RED** | GREEN |
| 7 | `emits a console signal for every user-silent failure path…` | 關掉橫幅失敗路徑的 `emitFailureSignal` | **RED** | GREEN |
| 8 | `always renders the reselection banner host with role status` | 移除宿主的 `role="status"`（保留選擇器與 testid） | **RED** | GREEN |
| 9（額外） | 案例 4 內新增的 `BR27.1` 斷言 | 移除 `<LiveRegion />` 的 `role="status"` | **RED** | GREEN |

**9 個突變、9 個紅燈、0 個倖存**。還原後以 `diff -q` 逐檔確認與突變前**位元組相同**，
再重建並複驗全綠。

**兩個最值得記的突變結果**：

- **m5 與 m6 各打中 `canManage` 兩段式的一邊**。這不是湊數——它證明兩個案例
  不是同一件事的兩種寫法：拿掉全域段只有案例 5 紅、拿掉 per-project 段只有
  案例 6 紅。審查 `R-01` 查出的那個可達壞狀態（per-project admin 但缺
  `K3.edit`）因此真的有一條會紅的斷言守著。
- **m3 證明案例 3 對「移出」的斷言是真的可失敗面**。我把它寫成「差額恰為 1」
  而非「0」（理由見發現 F-2），這很容易被讀成放水；m3 顯示處理器自己重抓時
  差額會變成 **2** 而紅燈，所以那個 1 卡住的正是要防的行為。

## 三、本輪自己查出並修掉的三個缺陷（**不是審查抓的**）

1. **`tsc -b` 擋下兩個真錯**：`MemberDetailPage` 的 `selectedRole === ''` 被判為
   不可能的比較（TS2367——`dirty` 的 aliased narrowing 已排除 `''`），以及
   `MembersListPage` 未使用的 `MembershipForbiddenError` import。已改為逐條
   直接縮小型別。**這一項值得點名**：`team.md` 記載 `tsc -b` 對「後端加欄、
   前端漏接」無效，那是對的，但它對本單元這兩類錯誤**有效**——兩件事不要混為一談。
2. **`react-hooks/set-state-in-effect`（error 級）擋下兩處**：我在兩個頁面的
   effect body 內各同步呼叫了一次 `setLiveMsg`。改為以 `useState` 初始值帶入
   載入訊息——播報義務（`BR27.1`）在這個形式下同樣成立，且不碰 lint 紅線。
3. **`BR21.3` 的 403 永久失敗閂原本漏掉**（見 §一之一）。收尾逐條對照 19 條
   規則時發現：我只實作了前置條件，而規則另有一句「發出後才發現 403 則本
   工作階段不再發出」。已補上。

## 四、七處**我沒有達成或無法達成**的目標（逐項，不美化）

> 依派工約束 13：不得為了讓步驟過關而放寬目標；做不到就留著並報告。

### F-1 — 計畫 Step 10 的 Sidebar 入口**不可建構**，我沒有改 `Sidebar.tsx`

計畫 Step 10 要求「`Sidebar.tsx` 依既有的按 user story 大類分層慣例新增入口」。
**查證後它與另一份已核可產出直接牴觸，且本身不可建構**：

- `infrastructure-specification.md` §二 逐字宣告「**唯一要碰的共用檔：`Layout.tsx`**」。
- 成員路由以 `projectId` **參數化**（`/projects/:projectId/members`），而側欄連結
  是**靜態 URL**，無法指名 `projectId`。
- 前端**不存在**任何專案頁或 `/projects` 路由：實測 `grep -rn "'/projects\|ProjectsPage\|ProjectPage" frontend/src`
  的命中數為 **0**（唯二命中是本單元新增的那兩條路由）；`src/pages/` 下無任何
  專案頁檔案。`functional-spec.md` §三 也把入口寫成「**專案頁首的 `[成員]` 動作**」
  ——那是 `U23` 的交付物，不是側欄。

依 `project.md` 的裁決規則（已核可產出互相矛盾時，讓**已交付的結構**裁決並寫明依據），
裁決者是磁碟現況：沒有專案頁，所以靜態側欄入口只能指向一個死連結，或夾帶一個
`U23` 的專案選擇頁（計畫 §四 明文禁止夾帶）。**我選擇不改 `Sidebar.tsx`**。

**後果（必須被看見）**：`US12.1` 的「入口可達性」目前**只能**靠手打 URL，或等
`U23` 的專案頁首落地。兩條路由本身已實作並以 `CapabilityRoute`（`K3`／`view`）
把關，`SEC-U24-3` 不受影響。

### F-2 — `UIP-3` 的「移出後額外請求數 0」與 `BR25.2` 的「filter 就地移除」，在本設計下不可達

三者兩兩相容、三者不相容：

- `functional-spec.md` §五 W5 第 4 步：204 後**導回清單頁**；
- `BR25.2`：**以 filter 就地移除該列**；
- `UIP-4`：清單頁首次可互動前**恰 1 次**請求（即清單頁擁有自己的掛載抓取）。

導回清單頁 ⇒ 清單頁重新掛載 ⇒ 依 `UIP-4` 它必然抓一次 ⇒ 「就地 filter」的結果
被該次回應取代，而 `UIP-3` 的「額外 0」對移出路徑為假。

**處置**：採「導回清單頁 ＋ 由伺服器的下一次回應呈現少一列」。使用者可見結果
與規則一致（清單少一列），**機制不同**（非 in-place filter）。案例 3 因此斷言
**差額恰為 1**，並以 m3 證明處理器自己重抓會是 2 而紅燈——嚴格的 0 差額斷言
保留給邀請與改角色（兩者皆停在原畫面）。

**未解的部分**：若要讓字面的「0」成立，必須把成員清單狀態提升到 `Layout` 之上
或引入共享 state，那是設計層的改動、不在本單元範圍。已如實標在
`traceability.json` 的 `UIP-3` 與 `BR25.2` 兩列。

### F-3 — `UIP-4` 的字面目標與 `UIP-2` **互斥**

`performance-requirements.md` §二 的 `UIP-4` 逐字為「進入成員頁後對
**`/api/membership/**`** 的請求數為 **1**」，而同節 `UIP-2` 要求橫幅查詢
「每次 `Layout` 掛載**恰 1 次**」。橫幅宿主在 `Layout` 裡且其端點
（`/api/membership/reselections/pending`）**共用同一個前綴**，故成員頁落地時
該前綴下的總數**必然是 2**，兩條要求不可能同時為 1。

**處置**：案例 4 斷言 `members` 端點為 **1**（`UIP-4` 的實質內容——`canManage`
不另發請求，由 m4 證明可失敗），並如實斷言總數為 **2**（members 1 ＋ 橫幅 1）。
未調整任何目標數字，只把「對哪個集合計數」寫清楚。

### F-4 — `BR21.3` 的 403 永久失敗閂**已實作但無 e2e 斷言**

其觀察面是「同一份文件內收到 403 之後，client-side 換頁不再發請求」。8 個案例
由 `cicd-pipeline.md` §五 固定，沒有這個構造，而我不自行增加第 9 個案例（案例
名稱是 TCMS 的鍵，新增案例屬該站的決定）。另：閂因禁用瀏覽器儲存而在整頁
重新載入時重置。

### F-5／F-6／F-7 — 三條已實作但無 e2e 斷言的規則

| 規則 | 已實作的落點 | 為什麼沒有斷言 |
|---|---|---|
| `BR23.1` 的**字串 `detail`** 拒絕態（`AC12.5.1`） | `InviteRejectedError` → `invite-dialog-rejection-reason` | 8 個固定案例只構造了物件陣列分支（案例 7 已斷言它） |
| `BR24.2` 409 守門（下拉還原 ＋ 列出每一個專案） | `MemberDetailPage` 的 `guard-report-projects` | 409 不在 8 個斷言標的內；守門的三條 AC 屬 `US12.3`、不在本單元承載的五則。`rules.md` 自己逐字寫「這份資訊若沒被渲染或渲染錯了，不會有任何東西變紅」——**該陳述在本輪仍然成立** |
| `BR26.2`／`BR26.3`（導向被點選專案、404 等價成功且逐筆處置） | `ReselectionBannerActions` 逐項綁定、`handleAcknowledge` 的逐筆 filter | 構造需要「三筆事件、第二筆回 500、再按一次」與「展開後點第 N 個」，皆不在 8 個案例內。`BR26.3` 是審查 `R-02` 修掉「橫幅永遠清不掉」的那條，未被斷言值得點名 |

三者皆列在 `traceability.json`（`BR24.2`／`BR26.2`／`BR26.3` 另進 `reverse` 段），
以免它們在覆蓋表上看起來與有斷言的列無異。

### F-8 — `AC12.2.2`／`BR24.3`／`UIP-5` 三者同被 `OPEN-MP24-7` 阻塞

變更紀錄**沒有任何可取得資料的端點**。依計畫 Step 9 渲染明確的
「尚無法取得變更紀錄（後端尚未提供查詢端點，OPEN-MP24-7）」佔位，並在程式註解
指向該開放項——**不捏造資料、不留空白區塊**。三者在 `traceability.json` 皆為
**`Deferred`**，未洗成 `OK`。修法屬 `U19` 的契約擴充，而 `U19` 已完成且在游標之前
（本 intent 內無自然承接站）。

## 五、驗證結果（逐項，含環境的重要前提）

| 檢查 | 指令 | 結果 |
|---|---|---|
| Lint | `cd frontend && npm run lint` | **0 errors**, 2 warnings |
| Typecheck | `cd frontend && npx tsc -b` | **通過**（無輸出） |
| Build | `cd frontend && npm run build` | 通過 |
| 單元範圍 e2e | `cd frontend && npx playwright test tests/e2e/member-pages.spec.ts` | **8 passed** |
| 穩定性 | 同上連續 4 次 | 4／4 全綠（4.6–4.7s） |

**兩則 warning 皆為既存且非本單元檔案**：`AssessmentPage.tsx:365` 與
`WorkspacePage.tsx:302`（皆 `react-hooks/exhaustive-deps`）。本單元七支應用檔
與 spec 檔的 lint 命中數為 **0**。
（註：`team.md` 記載的基準是「0 errors, 3 warnings」且列出 `LoginPage.tsx:36`；
現況為 2 warnings，該筆已不在——此漂移發生在本輪之前，非本單元造成。）

### 五之一、`tsc -b` 通過**不是**資料形狀正確的證據

`team.md` 逐字記載這道閘門對「後端加欄、前端漏接」無效：`AdminPage.tsx` 的
`DbUser` 曾是手寫本地 interface，而 `res.json()` 在執行期是 `any`、型別只是斷言。
本單元**已盡可能縮窄**該缺口（型別一律取自 `openapi.json → api.d.ts` 產生的
`components['schemas'][...]`，不手寫 interface），但縮窄不等於消除：
`res.json()` 的回傳仍是執行期的 `any`。**資料形狀的保證由 §二 的 8 個 e2e 承擔**，
不由 `tsc -b` 承擔。

### 五之二、計數類斷言**必須對生產建置執行**（本輪實測的一個陷阱）

`main.tsx:7` 的 `StrictMode` 在**開發模式**下會重複呼叫 effect，使每次掛載的
請求數加倍。我第一輪對 `npm run dev` 執行時，案例 2／3／4 因此**偽紅**
（`membersGets()` 回 2 而非 1）——那不是實作缺陷。改對 `npm run build` ＋
`vite preview` 執行後全綠。`ui-regression` 跑的是建置後的前端（nginx 服務
`deploy/docker-compose.test.yml` 的 stack），故與本輪的驗證環境一致。

### 五之三、案例 2 曾有約 50% 的偽紅，根因是**我的測試同步點錯了**

第一版以「宿主已出現」（`toBeAttached()`）作為「該次落地的請求已發出」的同步點。
**那是錯的，而且錯在一個有教育意義的地方**：宿主是**無條件**渲染的（`BR21.1`
的全部內容），它在 `/api/auth/me` 回來之前就在 DOM 裡了。以它當同步點時，
第二次 `goto` 會在第一次的請求發出前就把它取消（診斷實測到
`net::ERR_ABORTED`）或直接搶先，總數停在 1。

我寫了一支臨時診斷 spec 實地取證（已刪除），確認 `afterFirst` 有時完全沒有橫幅
請求。改以「每次落地各自等到該次請求被記錄」為同步點後，連續 6 次全綠；
`m2` 重跑仍紅，確認修同步點**沒有弱化斷言**。

附帶發現：`route.fulfill` 的回應若無 `Cache-Control`，Chromium 會對相同 URL 的
第二次導航命中 HTTP 快取而**不觸發 request 事件**。已在 stub 加 `no-store`
消除這個變數。這只影響測試替身；真實端點的快取標頭屬 `U19`，本單元不改。

## 六、約束逐項查證（**全部機械查證，非宣稱**）

| 約束 | 查證方式 | 結果 |
|---|---|---|
| 應用程式碼不進 record 目錄 | `git status` | 10 支全在 `frontend/` 之下 ✔ |
| Brownfield 就地修改 | `git diff --stat` | `Layout.tsx +10`、`App.tsx +35`，無 `*_modified.*` ✔ |
| 零新依賴 | `git status -- frontend/package.json frontend/package-lock.json` | 無改動 ✔ |
| 零新環境變數 | `git status -- deploy/ '*.env.example'` | 無改動 ✔ |
| 零後端變更 | `git status -- backend/ schema_rbac.sql` | 無改動 ✔ |
| 零瀏覽器儲存（`NFR4.80`） | `grep -rn "localStorage\|sessionStorage\|indexedDB"` 於七支應用檔 | **0 命中** ✔ |
| 零 `dangerouslySetInnerHTML` | 同上 grep | **0 命中** ✔ |
| 不走 `slotRegistry` portal | `grep -rn "slotRegistry\|mountCostSlot"` 於本單元檔案 | **0 命中** ✔ |
| `canManage` 兩段式 | 程式碼 ＋ m5／m6 兩個突變 | 兩邊各自可失敗 ✔ |
| `FailureSignal` 為封閉聯集 | `failureSignal.ts` 無 `string` 型欄位、無 `message`／`detail`／`displayName` | ✔ |
| `role="status"` 寫死（不開放 prop） | `LiveRegion.tsx` 無 role prop | ✔ |
| URL 一律經 `apiUrl()` | `membershipApi.ts` 六個函式 | 6／6 ✔ |
| 手寫 `Authorization: Bearer` | 同上 | 6／6，沿用既有 40 處形狀 ✔ |
| `describe` 字串 | `spec:196` | `U24 member pages` ✔ |

### 六之一、ADR-0006 四面向 ＋ PBT（第七項自檢，逐格比對上游）

| 面向 | 本輪判定 | 與 `nfr-design/security-design.md` §五 一致？ |
|---|---|---|
| IAM | **適用** | 一致。`canManage` 兩段式落地，兩個突變各守一邊；殘留缺口 `OPEN-MP24-2`（前端仍可自己猜，無機械強制）**未關閉**，如實記載 |
| Encryption | **不適用** | 一致。零新通道、零新儲存、零瀏覽器儲存（grep 0 命中） |
| Network exposure | **不適用** | 一致。零新端點、零新進程邊界，六個消費點全屬 `U19` 既有端點 |
| Audit logging | **適用** | 一致。使用者可見稽核面因 `OPEN-MP24-7` **不可達**（渲染佔位）；console 訊號以字面值聯集關閉 `SEC-U24-1` 的禁止內容，並由案例 7 斷言不含四個獨特測試字串 |
| PBT hard constraint | **不適用** | 一致。ADR-0006 點名的三個落點（IaC generator／cost calculator／agent routing）皆非本單元；前端無 PBT 框架，唯一自動化層是 Playwright e2e |

**無一格與上游判定相反**，故無需「範圍不同」的差異說明。

## 七、自 `source-manifest.json` 移出的三個欄位（逐字保留）

引擎的 `REVIEW_REQUESTED` 只接受 `stage`／`unit`／`version`／`writes` 四個欄位，
其餘一律回 `source-manifest.json has unknown field(s)` 並拒絕記錄審查請求。
原檔的 `deletes`（空）、`unchanged_by_design`（9 項）與 `verification`（5 項）因此移出，
**內容逐字保留於下**，不因格式限制而遺失：

```json
{
  "deletes": [],
  "unchanged_by_design": [
    {
      "path": "frontend/src/components/Sidebar.tsx",
      "reason": "計畫 Step 10 的 Sidebar 半邊**不可建構**：成員路由以 projectId 參數化，而前端不存在任何專案頁或 /projects 路由（實測 grep 命中數 0，唯二命中是本單元新增的兩條），故靜態側欄連結無法指名 projectId。另 infrastructure-specification.md §二 逐字宣告「唯一要碰的共用檔：Layout.tsx」，與 Step 10 直接牴觸。見 code-summary.md 的發現 F-1"
    },
    {
      "path": "frontend/package.json",
      "reason": "TS-U24-1 零新依賴"
    },
    {
      "path": "frontend/package-lock.json",
      "reason": "TS-U24-1 零新依賴"
    },
    {
      "path": "frontend/playwright.config.ts",
      "reason": "testDir 已涵蓋新 spec 檔，無需新增設定"
    },
    {
      "path": "backend/**",
      "reason": "本單元零後端變更；OPEN-MP24-6／OPEN-MP24-7 的伺服器端那一半屬 U19，已完成且在游標之前"
    },
    {
      "path": "schema_rbac.sql",
      "reason": "零 schema／seed 變更，故 project.md 的 blocking 同步義務為空集合"
    },
    {
      "path": "DEPLOY.md",
      "reason": "同上"
    },
    {
      "path": "deploy/**",
      "reason": "TS-U24-7／NFR8.80 零新環境變數，render-env.sh 與 deploy/.env.example 的同步義務為空集合"
    },
    {
      "path": "LOCAL-DEV.md",
      "reason": "未異動 database.py 的 schema 補丁、nginx.conf、任一 .env.example 或 render-env.sh，故該 blocking 規則未觸發"
    }
  ],
  "verification": {
    "lint": "cd frontend && npm run lint → 0 errors, 2 warnings（兩則皆為既存，落在 AssessmentPage.tsx:365 與 WorkspacePage.tsx:302，皆非本單元檔案）",
    "typecheck": "cd frontend && npx tsc -b → 通過（無輸出）",
    "build": "cd frontend && npm run build → 通過",
    "unit_scoped_tests": "cd frontend && npx playwright test tests/e2e/member-pages.spec.ts → 8 passed",
    "tests_environment_caveat": "計數類斷言須對**生產建置**執行。npm run dev 之下 main.tsx 的 StrictMode 會重複呼叫 effect，使請求數加倍並讓案例 2／3／4 偽紅（本輪實測）。ui-regression 跑的是建置後的前端，故與本輪驗證環境一致"
  }
}
```

### 七之一、`writes[]` 的 `change`／`note` 兩欄同樣被移出（逐字保留）

`writes[]` 的每個元素也只接受 `path`——多給 `change` 或 `note` 會回
`writes[0] has unknown field(s): change, note`。原始內容：

```json
[
  {
    "path": "frontend/src/membership/failureSignal.ts",
    "change": "created",
    "note": "SEC-U24-6 的訊號形狀；兩欄皆為字面值聯集（SEC-U24-1 的型別層保證）"
  },
  {
    "path": "frontend/src/membership/membershipApi.ts",
    "change": "created",
    "note": "六個端點的純抓取函式層；型別取自產生的 api.d.ts，不手寫 interface"
  },
  {
    "path": "frontend/src/components/LiveRegion.tsx",
    "change": "created",
    "note": "[N4]=A／HO-U24-1：本單元自建、可共用，U23 之後沿用；role=\"status\" 寫死"
  },
  {
    "path": "frontend/src/components/membership/ReselectionBanner.tsx",
    "change": "created",
    "note": "宿主（role=\"status\"、無條件渲染、僅文字）＋ 操作列（宿主之外的兄弟節點）"
  },
  {
    "path": "frontend/src/components/membership/InviteMemberDialog.tsx",
    "change": "created",
    "note": "422 以 detail 的型別分流（BR23.1）；拒絕態停在 open"
  },
  {
    "path": "frontend/src/pages/MembersListPage.tsx",
    "change": "created",
    "note": "canManage 兩段式、100 列渲染閘、就地新增"
  },
  {
    "path": "frontend/src/pages/MemberDetailPage.tsx",
    "change": "created",
    "note": "角色下拉（409 還原）、二次確認移出、變更紀錄的 OPEN-MP24-7 佔位"
  },
  {
    "path": "frontend/src/components/Layout.tsx",
    "change": "modified",
    "note": "就地修改既有檔（22 行）：在 data-slot=\"cost-banner\" 之後、{children} 之前直接渲染 <ReselectionBanner />，不走 slotRegistry portal"
  },
  {
    "path": "frontend/src/App.tsx",
    "change": "modified",
    "note": "就地修改既有檔：新增兩條路由，各以既有 CapabilityRoute（K3／view）包覆"
  },
  {
    "path": "frontend/tests/e2e/member-pages.spec.ts",
    "change": "created",
    "note": "8 個 Playwright e2e 案例；describe 為 U24 member pages（名稱凍結）"
  }
]
```

## 八、審查 `review-01.md` 的六項處置（NOT-READY：Major 3、Minor 3）

審查為 advisory 單輪，無修復迴圈；以下處置在記下 `REVIEW_COMPLETED` **之後**執行，
每一項都附獨立複驗結果。**六項全部處置，無一項留為 Accepted risk。**

| ID | 嚴重度 | 處置 | 複驗 |
|---|---|---|---|
| `R-01` | Major | **已修**。`MemberDetailPage` 與 `MembersListPage` 各新增 `actionError` state，與閘住主內容的 `error` 分離；寫入／權限錯誤只寫 `actionError` 並以非阻斷訊息渲染（`member-detail-action-error`／`member-list-action-error`），控件保持掛載以便重試 | 新增案例 10『keeps the member block and its controls mounted after a failed write』；**突變驗證**：把 `setActionError` 改回 `setError` → **紅**，還原 → **綠** |
| `R-02` | Major | **已修**。`bannerForbiddenInThisSession`（裸布林）改為 `bannerForbiddenForToken`（以 token 為鍵）。根因已獨立複驗：`logout()` 只做 `setToken(null)`＋`setUser(null)`（`AuthContext.tsx:56-61`），**不觸發整頁導航**，故模組不重載、裸布林會留給同分頁內下一位登入者 | 型別與 lint 通過、10/10 綠。**無 e2e 斷言**——構造同分頁換人需驅動登入流程，不在本單元的案例集合內。逐項宣告於 §九 |
| `R-03` | Major | **部分處置**。補上 `BR26.3` 的案例 9（審查指名的最吃重一條：它是先前 `R-02` Critical 的修法本身，原本零迴歸保護）。**並採納審查對兩個理由的駁回**：`cicd-pipeline.md` §五 的標題是「需要**新增**的 e2e 案例」＝下限非上限；TCMS 的名稱穩定性約束的是 `--summary-template` 不得改，**新增 test 只會新建案例、不會讓既有案例變成孤兒** | 案例 9『treats a 404 acknowledge as success and keeps genuinely failed ones pending』；**突變驗證**：移除 `res.status === 404` 的等價 → **紅**，還原 → **綠**。其餘四條仍無斷言，逐項宣告於 §九 |
| `R-04` | Minor | **已修**。兩個頁面的 `isProjectManager` 移除 `|| ownRole === 'project_owner'` 死分支。獨立複驗：`ck_project_members_role`（`schema_rbac.sql:598`）限定 `('project_admin','member')`，`membership_types.py` 的 `ProjectRole` docstring 逐字說 owner 是 `projects.owner_user_id` 承載的**專案屬性**，前端 `ProjectRole` 由 generated schema 推導 | `tsc -b` 通過、10/10 綠。無功能損失（建立者在同一交易被寫成 `project_admin`） |
| `R-05` | Minor | **已修**。審查指名的兩處「恰 N 次」改為**先等網路靜止再以一般 `expect` 斷言終值**，不用首次命中即通過的 `expect.poll`。另**自行掃全檔**：`:268` 的 poll 是同步點（真正的計數斷言在迴圈後的 plain `expect`），形狀正確、**刻意不動**；`:539`／`:546` 是等待 console 訊息出現，polling 本來就對 | 10/10 綠 |
| `R-06` | Minor | **已修**（採用審查的第二個選項，而非改寫宣稱）。夾具改為可變：DELETE 之後 `list_members` 真的少一列；案例 3 新增斷言 `member-list-row-<OTHER_ID>` 為 **0 命中**，使 `BR25.2` 的 observable 由預測變成已驗證 | 10/10 綠 |

## 九、修訂後仍**無 e2e 斷言**的五項（逐項宣告，不藏）

`R-03` 的理由已被駁回，故這裡不再用「案例集合是上限」當藉口；以下是逐項的真實狀態：

| 規則／修法 | 為何仍無斷言 |
|---|---|
| `R-02` 的 token-keyed 閂 | 構造需在**同一個 page session 內**換人登入（登出不重載模組才是這個 bug 的前提），而那要驅動登入 UI——跨出本單元的頁面範圍。修法本身是三行且可靜態複驗 |
| `BR21.3` 的 403 session 閂 | 同上：要證明「第二次落地不再發請求」需要兩次落地 ＋ 計數，案例 2 已涵蓋「缺 `K3 view` 者 0 次」，但**未**涵蓋「有權限卻收到 403 後不再重試」 |
| `BR23.1` 的字串型 `detail` 拒絕態 | 案例 7 涵蓋物件陣列型（驗證錯誤）的 console 訊號，**未**涵蓋字串型（缺全域權限）在對話框內的文案呈現 |
| `BR24.2` 的最後管理者守門報告 | `rules.md` 自述「nothing will turn red」——它的 observable 本身就不可機械判定 |
| `BR26.2` 的「查看成員」導向被點選的專案 | 需要多筆事件 ＋ 比對導航目標的 `projectId`；`NFR11.81` 的量測母體問題亦未解（見 `performance-design.md` §一） |

**這五項是真實的覆蓋缺口**，不是「不需要測」。它們進入核可關卡供裁決是否值得在本輪補齊。

## 重新查驗與合併前必修第 9 項

> 記錄時間 `2026-10-23T11:20:31Z`（`date -u` 取值）。來源：使用者對整站送 Request Changes，
> 本單元承接 `functional-design/merge-blockers.md` 第 9 項，裁決「前端分頁顯示全部」（計畫 §五之一）。

### 一、Steps 1–14 重新查驗（逐格開檔）

| Step | 結果 | 查證依據 |
|---|---|---|
| 1 | 勾回 | `git status` 對 `frontend/package.json`、`package-lock.json`、`playwright.config.ts` 無改動；`testDir: './tests/e2e'` 仍在 |
| 2 | 勾回 | `npx playwright test tests/e2e/member-pages.spec.ts --list` 可收集（輸出見 §四）；指令仍記於 `unit-test-instructions.md` §二 |
| 3 | 勾回 | `failureSignal.ts` 的 `SignalKind`（5 個字面值，:29-34）、`SignalEndpoint`（6 個，:42-48），無 `message`／`detail`／`displayName` 欄位 |
| 4 | 勾回 | `LiveRegion.tsx:50-51` 的 `role="status"` 與 `data-testid="live-region"` 寫死 |
| 5 | 勾回 | `membershipApi.ts` 六個函式皆經 `apiUrl()`，422 以 `typeof detail` 分流（:106-110、:173-176），各失敗路徑呼叫 `emitFailureSignal` |
| 6 | 勾回 | `ReselectionBanner.tsx:180` 的 `can('K3', 'view')` 前置、`:247` 宿主 `role="status"`；`Layout.tsx:26` 直接渲染，未走 `slotRegistry` |
| 7 | 勾回 | `MembersListPage.tsx` 兩層抓取、`canManage` 兩段式不變；**100 列閘已由 Step 15 取代為分頁**（見 §二） |
| 8 | 勾回 | `InviteMemberDialog.tsx` 未改，案例 4、8（現編號）仍綠 |
| 9 | 勾回 | `MemberDetailPage.tsx:296`／`:319` 的 `OPEN-MP24-7` 佔位仍在 |
| 10 | **維持未勾** | 路由半邊已完成（`App.tsx` 兩條路由皆以 `CapabilityRoute` `K3`／`view` 包覆）；`Sidebar.tsx` 半邊依 §四 F-1 刻意未做。**前提已變動（如實記載，不自行改判）**：F-1 寫「前端不存在任何專案頁或 `/projects` 路由」，現況 `U23`（commit `8677b7d`）已加入 `Sidebar.tsx` 的 `/projects` 入口與 `ProjectDetailPage.tsx:83` 的 `project-members-link`，故成員頁現在可由「側欄 → 專案 → 成員」到達。本單元仍未改 `Sidebar.tsx`，是否據此視為 Step 10 已滿足由 conductor／使用者判定 |
| 11 | 勾回 | spec 現為 **11** 個案例（原 10 ＋ 本輪 1b），對生產建置實跑 11/11 綠 |
| 12 | 勾回 | `npm run lint` 0 errors、`npm run build`（含 `tsc -b`）通過，輸出見 §四 |
| 13 | 勾回 | `source-manifest.json` 存在、可解析；本輪改動的兩支檔已在 `writes[]` 內，無新增路徑 |
| 14 | 勾回 | 本檔與 `traceability.json` 已更新（見 §五） |

**共用檔被其他單元改動的影響**：`membership-service` 把 `PUT /api/auth/{user_id}/active` 的 409 改為
`Union[LastAdminGuardReport, ReservedAccountConflict]` 並新增 500／503，`openapi.json` 與 `api.d.ts` 隨之重產。
**本單元不消費該端點**：`membershipApi.ts` 對 `/active` 的命中數為 0，`MemberDetailPage` 的 409 來自
`PATCH`／`DELETE /api/membership/projects/{id}/members/{uid}`（`membershipApi.ts:222`、`:256`），本體仍是
`LastAdminGuardReport`；停用端點的唯一前端消費者是 `AdminPage.tsx`（不屬本單元）。重產後的 `api.d.ts`
仍匯出 `LastAdminGuardReport`（:1492），`tsc -b` 通過。結論：**對本單元無影響**。

### 二、Step 15 改動（檔:行）

| 檔案 | 改動 |
|---|---|
| `frontend/src/pages/MembersListPage.tsx:18-30` | 刪除 `MAX_RENDERED_MEMBERS = 100` 與其註解，改為 `MEMBERS_PER_PAGE = 50` 與「為什麼是前端分頁」的註解 |
| `:49-50` | 新增 `requestedPage` state |
| `:121-131` | `handleInvited` 新列附加後跳到新列所在頁（`:126`，`Math.ceil((members.length + 1) / 50)`） |
| `:145-155` | `totalPages`／`currentPage`／`visibleMembers` 皆為導出值；`currentPage` 夾在 [1, 總頁數]，當前頁變空即退回最後一個非空頁——**不用 effect**（`react-hooks/set-state-in-effect`） |
| `:192-197` | 刪除「成員過多，請聯絡管理者」提示與 `tooMany` 閘；表格無條件渲染（載入完成且無抓取錯誤時） |
| `:211` | 列的 `map` 改走 `visibleMembers` |
| `:243-277` | 分頁列 `member-list-pagination`（表格之外）：`member-list-prev-page`、`member-list-page-info`（「第 N／M 頁、共 K 位」）、`member-list-next-page`；邊界呈現但停用 |
| `frontend/tests/e2e/member-pages.spec.ts:209-288` | 案例 1 改寫並改名、新增案例 1b，皆附 `@purpose`／`@api`／`@ui`／`@given`／`@step`／`@pass`／`@story` |

`canManage` 仍以**完整** `members` 找自身那一列（不受切頁影響）；切頁不發請求，案例 1 另斷言翻頁全程 `membersGets() === 1`。
後端零改動，`OPEN-MP24-6`（伺服器分頁）仍開放。`MAX_RENDERED_MEMBERS`／`member-list-too-many`／「成員過多」在 `src` 與 `tests` 的 grep 命中數皆為 **0**。

### 三、測試名稱變更（TCMS 孤兒案例處置用，`unit-test-instructions.md` §七）

| 動作 | `test()` 字串 |
|---|---|
| 舊名（作廢） | `U24 member pages › renders the member list up to 100 rows and replaces it with a notice beyond that` |
| 新名（取代舊名） | `U24 member pages › paginates more than 100 members 50 per page so every member stays reachable` |
| 新增 | `U24 member pages › splits exactly 100 members into two pages of 50` |

改名是必要的：舊名斷言的正是缺陷本身（「超過 100 改顯示提示」），沿用舊名會讓 TCMS 案例描述與行為相反。
TCMS 上舊名案例將變成無執行結果的孤兒，同步時須手動封存。

### 四、各命令實際輸出

| 命令 | 實際輸出（摘錄） |
|---|---|
| `cd frontend && npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`——`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`（皆 `exhaustive-deps`，非本單元檔案；行號較前次記載漂移，屬他檔改動） |
| `cd frontend && npm run build` | `✓ 324 modules transformed.` … `✓ built in 828ms`（另有既存的 chunk > 500 kB 提示） |
| `npx playwright test tests/e2e/member-pages.spec.ts --list` | `Total: 11 tests in 1 file` |
| `BASE_URL=http://localhost:4179 npx playwright test tests/e2e/member-pages.spec.ts`（對 `npx vite preview --port 4179` 的生產建置） | `11 passed (9.7s)`；還原突變後重建重跑 `11 passed (7.8s)` |

**環境說明**：本 spec 全部走 `page.route()` 攔截，不需要後端與資料庫，故以 `npm run build` ＋ `vite preview`
服務生產建置即可實跑（沿用 §五之二：計數類斷言須對生產建置執行）。**未**對 `deploy/docker-compose.test.yml` 的完整 stack 執行，
那一層由 CI 的 `ui-regression` 承擔。

### 五、突變驗證

| 突變 | 受測案例 | 結果 | 還原後 |
|---|---|---|---|
| 表格條件加回 `members.length <= 100`（還原整表隱藏閘） | 1 | **RED**（`expect(locator).toBeVisible() failed … element(s) not found`，spec:238） | GREEN |
| `totalPages` 改為 `Math.floor(len / 50) + 1`（off-by-one） | 1b | **RED**（Expected `第 1／2 頁、共 100 位`，Received `第 1／3 頁、共 100 位`）；案例 1 在此突變下仍綠（101 位兩式皆得 3） | GREEN |

兩個突變還原後以 grep 確認 `<= 100`／`floor` 命中數為 0，重建後全套 11/11 綠。

### 六、未驗項（如實記載）

| 項目 | 狀態 |
|---|---|
| 「當前頁變空退回前一頁」 | 已實作（導出值夾取），**無 e2e 斷言**。現行三種操作中只有移出會減少成員，而移出會導回清單頁重新掛載（頁次重置為 1），故此路徑在現有流程中不可由使用者觸發；它是對未來就地移除的防護 |
| 「邀請後跳到新列所在頁」 | 已實作，**無 e2e 斷言**（案例 3 只有 2 位成員，新列本就在第 1 頁） |
| 完整 stack（`docker-compose.test.yml`）上的 e2e | 未跑，由 CI `ui-regression` 承擔 |
| TCMS 同步 | 未做；舊名案例需在 `tcms-test-cases` 站處置 |

### 七、偏離

1. **未重用既有 `PaginationControl.tsx`**，在本頁內寫一組分頁列。理由：該元件為深色主題（`bg-slate-800`）、`aria-label` 寫死為「使用者清單分頁」、總數字樣為「筆」，且語意是伺服器分頁（`pageSize` 取自回應）；修改它會波及 `AdminPage`。計畫要求「沿用既有 Tailwind 樣式與 `data-testid` 慣例」，本頁沿用的是自己的淺色樣式與 `member-list-*` testid 前綴。
2. **新增「邀請後跳到新列所在頁」**，計畫未明列。理由：不跳頁時在第 1 頁邀請的新列會落在看不見的最後一頁，「就地新增一列」（`BR23.2`）在超過 50 位時不可觀察。未增加任何請求。
3. **案例 1 改名**（見 §三）。計畫已預見「若必須改 `test()` 字串」並要求記錄。
4. `source-manifest.json` **未改**：本輪改動的兩支檔已在 `writes[]` 內，無新增或刪除的 application-source 路徑。


## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T14:47:12Z -->

本輪只查驗、未改任何程式或測試。計畫 20 格勾選 18 格（機械計數：`[x]` 18、`[ ]` 2）。

| 格 | 未勾理由 |
|---|---|
| Step 9 `[移出專案]` 就地移除 | 實作為移出成功後 `navigate()` 回清單頁、清單頁重新掛載時再抓一次（`MemberDetailPage.tsx` 的 `handleRemove`），不是就地移除；本檔 F-2 已記「本設計下不可達」，案例 3 斷言清單請求多恰好 1 次。角色下拉就地更新、二次確認、409 守門文案、`OPEN-MP24-7` 佔位皆已完成 |
| Step 10 在 `Sidebar.tsx` 新增入口 | 兩條路由已以 `CapabilityRoute` `K3`／`view` 包住（`App.tsx:169-198`），但本單元未改 `Sidebar.tsx`；成員頁經「側欄專案 → `/projects` → `ProjectDetailPage.tsx:83` 成員連結」可達（U23 `8677b7d`）。`merge-blockers.md` 第 9 列記 review-03 判定已滿足；本輪照字面維持未勾 |

測試與檢查（本機實跑）：`npm run lint` 0 errors、2 個既有 `exhaustive-deps` warning（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`，非本單元）；`npx tsc -b`、`check:types`、`check:ws-types` 通過；`vite build` 成功（輸出指到 scratchpad，未覆寫 `frontend/dist`）。e2e：本 spec 的請求全以 `page.route()` 攔截，以 `vite preview` 服務 scratchpad 建置實跑 `member-pages.spec.ts` **14 passed**，跑完已停 preview；`docker-compose.test.yml` 全 stack 未跑，由 CI `ui-regression` 承擔。後端完整套件 1319 OK（skipped 3）。突變未重跑，沿用本檔既有紀錄。repo 內測試輸出與快取 mtime 未變。

合併前必修 **#9 屬實已解決**：`MAX_RENDERED_MEMBERS`／「成員過多」／`member-list-too-many` 在 `frontend/src` 與 `tests` 零命中；`MembersListPage.tsx` 改為 `MEMBERS_PER_PAGE = 50` 的前端分頁，不再整表隱藏；案例 1（101 位：第 1 頁 50 列、「第 1／3 頁、共 101 位」、第 3 頁可見並進入第 101 位，清單請求僅 1 次）與 1b（剛好 100 位為 2 頁）實跑綠。後端分頁（`OPEN-MP24-6`）仍為開放項。#14 為本單元的依賴：前端對 404 一律顯示「查不到這個專案」，三個 404／403 案例實跑綠；後端部分屬 `project-pages-ui`。

已核可計畫／測試說明與程式的落差（不回改計畫）：`unit-test-instructions.md` §四寫 8 個案例，spec 實為 14 個（新增 1b 與 review、#14 的 404／403 案例；案例 1 改名對照見本檔）；Step 7 的「100 列渲染閘」已被 Step 15 前端分頁取代，依 Step 15 勾選；Step 15 的「當前頁變空退回前一頁」與「邀請後跳到新列所在頁」有實作但無 e2e 斷言，且前者在現行流程不可達。

候選問題（未修，交審查判定）：(1) 網址 `projectId`（或詳情頁 `userId`）非數字時，effect 直接 return，畫面永遠停在「載入中…」且無 console 訊號，與 `SEC-U24-6` 不符；(2) 邀請與移出確認兩個對話框宣告 `role="dialog" aria-modal="true"`，但沒有焦點圈限、不能按 Escape 關閉，鍵盤可 Tab 到背景；(3) `inviteMember` 網路失敗時發出的訊號種類為 `invite-validation-failed`，語意錯誤；(4) 已接受的提醒：分頁列無 `aria-live`、按鈕觸控尺寸未達 44px、快速連續邀請時 `handleInvited` 讀舊的 `members.length`。

## 合併前必修第 23 項處置（2026-10-26）

<!-- 寫入時間：2026-10-26T14:24:00Z -->

依計畫 §五之二（Step 16–20）處置 `merge-blockers.md` 第 23 項的 (a)–(d)。訊號種類標錯那一項（Minor）不在範圍，未改。

### 一、程式改動（行號為本次寫入後的現況）

| 檔案 | 位置 | 改動 |
|---|---|---|
| `frontend/src/pages/MembersListPage.tsx` | :52 | `invalidProjectId = !Number.isFinite(projectId)`（導出值，不進 state） |
| 同上 | :75、:96 | 抓取 effect 以 `invalidProjectId` 判斷跳過；依賴陣列補上它 |
| 同上 | :101-104 | 新 effect：`invalidProjectId` 為真時呼叫 `emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' })`——與 404 走同一組種類／端點，effect 內不 setState |
| 同上 | :106-108、:208、:225-229、:245、:297 | `showLoading`／`shownError`／`shownLiveMsg` 三個導出值：非數字時不顯示「載入中…」、錯誤區塊與 live region 都顯示固定句 `PROJECT_NOT_FOUND_MESSAGE`（「查不到這個專案」），表格與分頁列不渲染 |
| 同上 | :68、:156-159、:171、:185、:215、:332 | `inviteButtonRef` ＋ `closeInvite()`：取消、Escape、201、403 四條關閉路徑都把焦點還給「邀請成員」鈕 |
| `frontend/src/components/membership/InviteMemberDialog.tsx` | :4、:58、:68、:111 | 掛上 `useDialogKeyboard`；送出中 Escape 不關閉（與停用的「取消」一致） |
| `frontend/src/pages/MemberDetailPage.tsx` | :5、:65-84、:195、:201、:206、:350、:364、:379 | `confirmDialogRef`／`removeButtonRef` ＋ `closeConfirm()`；掛上 `useDialogKeyboard`（`open: confirmOpen`，移出中 Escape 不關閉）；取消、Escape、409、403、其他錯誤五條留在本頁的關閉路徑都把焦點還給「移出專案」鈕 |
| `frontend/src/hooks/useDialogKeyboard.ts`（**新檔**，68 行） | 全檔 | 共用 hook：Escape 關閉、Tab／Shift+Tab 在對話框內首尾循環，焦點已在對話框外時下一次 Tab 收回。焦點圈限沿用 `components/brain/ObjectPicker.tsx` 的 `onKeyDown` 形狀；監聽掛在 `window` 沿用 `components/ShareModal.tsx`／`components/cost/EstimateSaveModal.tsx`。不新增依賴 |
| `frontend/tests/e2e/member-pages.spec.ts` | :896、:932、:987 | 三個新案例（見二），各附 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui` 規格註解；非數字案例沒有任何 API 請求，故不寫 `@api` |

`source-manifest.json` 加入 `frontend/src/hooks/useDialogKeyboard.ts`。`traceability.json` 只改一處變為不實的註記：`BR25.1` 原寫「焦點預設在取消已實作但未斷言」，現由新案例斷言。

### 二、新增的 e2e 案例（名稱一經合併不得再改）

1. `shows the fixed not-found sentence instead of loading forever when the project id is not a number`：開 `/projects/abc/members` → 錯誤區塊恰為「查不到這個專案」、「載入中…」0 命中、表格 0 命中；網路靜止後 `[membership] ` 開頭的 console 恰一筆 `members-fetch-failed GET /projects/:id/members`、不含 `abc`；members 端點請求 0 次。
2. `keeps keyboard focus inside the invite dialog, closes it on Escape and returns focus to the invite button`：開啟後焦點在使用者 ID 欄；連按 Tab 六次每次都在對話框內；第一欄 Shift+Tab 到「取消」；Escape 後對話框消失、焦點在「邀請成員」鈕；再開一次按「取消」焦點同樣回原鈕。
3. `keeps keyboard focus inside the remove confirmation, closes it on Escape and returns focus to the remove button`：開啟後焦點在「取消」；Tab 四次都在確認框內；「取消」上 Shift+Tab 到「確認移出」；Escape 後確認框消失、焦點在「移出專案」鈕、DELETE 請求 0 次。

### 三、測試結果（本機實跑）

- `npx eslint .`：**0 errors**、2 warnings（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的既有 `exhaustive-deps`，非本單元）。
- `npx tsc -b`：通過。
- `npx vite build --outDir <scratchpad>/fe23-dist`：成功（未寫 `frontend/dist`）。
- 以 `vite preview` 在 4823 埠服務該建置：`member-pages.spec.ts` **17 passed**（原 14 ＋ 新 3）；`a11y.spec.ts` **27 passed**（含掃描點 11 邀請對話框初始狀態、12 邀請對話框拒絕狀態、15 移出確認對話框）。輸出目錄指到 scratchpad，跑完已停 preview；repo 內 `test-results/`、`pw-report.json`、`junit.xml` 的 mtime 未變。
- `deploy/docker-compose.test.yml` 全 stack 未跑，由 CI `ui-regression` 承擔。

### 四、突變驗證（只改暫存區副本 `fe23-mut`，`node_modules` 以 symlink 共用；repo 檔案未動）

每次突變都重新建置、在 4824 埠預覽，以 repo 的 spec 跑對應案例。

| # | 突變 | 結果 |
|---|---|---|
| M1 | 拿掉 Step 16：`invalidProjectId` 固定為 false，抓取 effect 改回原本的提早 return | 案例 1 **紅**：`member-list-error` 找不到（畫面停在「載入中…」） |
| M1b | 只拿掉訊號 effect 內的 `emitFailureSignal` 呼叫 | 案例 1 **紅**：console 訊號陣列為空，期望恰一筆 |
| M2 | hook 內拿掉 Tab 處理（焦點圈限） | 案例 2 **紅**（第 3 次 Tab 後焦點離開對話框）、案例 3 **紅**（第 2 次 Tab 後焦點離開確認框） |
| M3 | hook 內拿掉 Escape 關閉 | 案例 2、3 **紅**：Escape 後對話框仍在（count 1，期望 0） |
| M4 | 拿掉 `closeInvite`／`closeConfirm` 內的焦點回復 | 案例 2、3 **紅**：Escape 後觸發按鈕未取得焦點 |

還原後以 `diff -r` 確認副本 `src/` 與 repo 完全相同，再跑三個新案例 **3 passed**。

### 五、未做與留意

- **詳情頁的非數字 `projectId` 仍會停在「載入中…」**：`MemberDetailPage.tsx` 的抓取 effect 同樣在 `!Number.isFinite(projectId)` 時直接 return。第 23 項與 Step 16 只點名清單頁（第 23 項逐字說詳情頁的非數字 `userId` 會顯示「找不到這位成員」），故本輪未改，交審查判定是否另列。
- `merge-blockers.md` 第 9 列引用的 `MembersListPage.tsx` 行號（:30、:152-155、:243-277、:126）因本輪插入而位移；本輪不得編輯該檔，未更正。
- `traceability.json` 的 `US12.1` 一列仍引用案例 1 的舊名（第 9 項改名前即如此，非本輪造成），本輪依指示未動。
- 邀請 201 後焦點也回到「邀請成員」鈕（與另外三條關閉路徑一致）；新列所在頁的跳頁行為不變。

## 合併前必修第 23 項補修：成員詳情頁（2026-10-26）

<!-- 寫入時間：2026-10-26T15:10:31Z -->

依計畫 §五之三（Step 21–24）處置審查 `review-05` 的 `R-11`（Major：詳情頁非數字 `projectId` 永遠停在「載入中…」）與 `R-15`（Minor：對話框其餘關閉路徑缺焦點斷言）。上節「五、未做與留意」第一點所記的詳情頁缺口由本節關閉。

### 一、程式改動（行號為本次寫入後的現況）

| 檔案 | 位置 | 改動 |
|---|---|---|
| `frontend/src/pages/MemberDetailPage.tsx` | :6、:10 | 匯入 `emitFailureSignal` 與 `PROJECT_NOT_FOUND_MESSAGE` |
| 同上 | :44-56 | 註解 ＋ `invalidProjectId = !Number.isFinite(projectId)`（導出值，不進 state）。只看 `projectId`：`userId` 非數字時抓取照常、畫面顯示「找不到這位成員」，本來就不會卡住 |
| 同上 | :105、:128 | 抓取 effect 以 `invalidProjectId` 判斷跳過；依賴陣列補上它 |
| 同上 | :130-136 | 新 effect：`invalidProjectId` 為真時呼叫 `emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' })`——與 404 同一組種類／端點、與清單頁同形；effect 內不 setState |
| 同上 | :138-140、:247、:257、:259-261 | `showLoading`／`shownError`／`shownLiveMsg` 三個導出值：非數字時不顯示「載入中…」、錯誤區塊（`member-detail-error`）與 live region 顯示固定句「查不到這個專案」；主內容與「找不到這位成員」仍以 `isLoading` 閘住，故不渲染 |
| `frontend/tests/e2e/member-pages.spec.ts` | :1024-1152 | 三個新案例（見二），各附 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui` 規格註解；後兩案另附 `@api`。非數字案例沒有任何 API 請求，故不寫 `@api` |

`InviteMemberDialog.tsx`、`MembersListPage.tsx`、`useDialogKeyboard.ts` 本輪**未改**：(b)(c) 兩條路徑的行為在 §五之二 已實作，本輪只補斷言。`source-manifest.json` **未改**（無新增或刪除的 application-source 路徑；`MemberDetailPage.tsx` 與 spec 已在 `writes[]` 內）。`traceability.json` **未改**：逐筆檢查後無因本輪變為不實的註記（`BR25.1` 的註記仍成立）。

### 二、e2e 案例名稱（§五之二 與 §五之三 新增者，供 `tcms-test-cases` 同步；名稱一經合併不得再改）

TCMS 案例名為 `U24 member pages › <test>`：

| 來源 | `test()` 字串 | spec 行 |
|---|---|---|
| §五之二 Step 18 (a) | `shows the fixed not-found sentence instead of loading forever when the project id is not a number` | :896 |
| §五之二 Step 18 (b) | `keeps keyboard focus inside the invite dialog, closes it on Escape and returns focus to the invite button` | :932 |
| §五之二 Step 18 (b) | `keeps keyboard focus inside the remove confirmation, closes it on Escape and returns focus to the remove button` | :987 |
| §五之三 Step 22 (a) | `shows the fixed not-found sentence instead of loading forever when the detail page project id is not a number` | :1033 |
| §五之三 Step 22 (b) | `ignores Escape while an invite is in flight and returns focus to the invite button once it completes` | :1067 |
| §五之三 Step 22 (c) | `returns focus to the remove button after the remove confirmation is closed by a last-admin 409` | :1124 |

各案內容：
- (a) 開 `/projects/abc/members/1` → `member-detail-error` 恰為「查不到這個專案」、「載入中…」與「找不到這位成員。」皆 0 命中；網路靜止後 `[membership] ` 開頭的 console 恰一筆 `members-fetch-failed GET /projects/:id/members` 且不含 `abc`；members 端點請求 0 次。
- (b) 以 route 延遲 POST（測試自持一個 promise 放行）→ 送出鈕顯示「送出中…」且確認 POST 已到達後按 Escape，等一個 animation frame 後對話框數仍為 1；放行（201）後對話框數為 0、新成員出現在表格、「邀請成員」鈕取得焦點。
- (c) DELETE 回 409（`LastAdminGuardReport`，一個專案）→ 確認框數為 0、`guard-report` 可見、「移出專案」鈕取得焦點。選 409 而非 403：兩條在 `handleRemove` 都經 `closeConfirm()`，409 另有可見的守門回報，可同時確認走的是錯誤分支而非取消。

`unit-test-instructions.md` 仍寫「8 個案例」（凍結文件，本輪依指示不改）；spec 實為 **20** 個案例（`--list`：`Total: 20 tests in 1 file`）。

### 三、測試結果（本機實跑）

- `npx eslint .`：**0 errors**、2 warnings（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的既有 `exhaustive-deps`，非本單元）。
- `npx tsc -b`：通過。
- `npx vite build --outDir <scratchpad>/fe23b-dist`：成功（未寫 `frontend/dist`；既存 chunk > 500 kB 提示）。
- 以 `vite preview` 在 4853 埠服務該建置，`npx playwright test tests/e2e/member-pages.spec.ts tests/e2e/a11y.spec.ts --reporter=list --output=<scratchpad>/pw23b`：**47 passed**（`member-pages.spec.ts` **20**＝原 17 ＋ 新 3；`a11y.spec.ts` **27**）。跑完已停 preview。以 `--reporter=list` 覆寫設定檔的 json／junit reporter，repo 內 `pw-report.json`、`junit.xml`（mtime 22:23 CST，早於本輪）與 `test-results/` 未被寫入。
- `deploy/docker-compose.test.yml` 全 stack 未跑，由 CI `ui-regression` 承擔。

### 四、突變驗證（只改暫存區副本 `fe23b-mut`，`node_modules` 以 symlink 共用；repo 檔案未動）

每次突變都重新建置、在 4854 埠預覽，以 repo 的 spec 以 `-g` 跑對應案例。

| # | 突變 | 結果 |
|---|---|---|
| M5 | 拿掉 Step 21：`invalidProjectId` 固定為 false，抓取 effect 改回 `!Number.isFinite(projectId)` 提早 return | 案例 (a) **紅**：`member-detail-error` 找不到（畫面停在「載入中…」），spec:1044 |
| M6 | `InviteMemberDialog.tsx` 的 `escapeDisabled: submitting` 改為恆 false（送出中的 Escape 停用條件改錯） | 案例 (b) **紅**：送出中 Escape 後對話框數 Expected 1、Received 0，spec:1106 |
| M7 | `MemberDetailPage.tsx` 的 409 分支以 `setConfirmOpen(false)` 取代 `closeConfirm()`（拿掉錯誤路徑的焦點回復） | 案例 (c) **紅**：`member-detail-remove` 未取得焦點（Received inactive），spec:1150 |

每次還原後以 `diff -r` 確認副本 `src/` 與 repo 完全相同；全部還原後重跑三個新案例 **3 passed**。

### 五、計畫勾選（本輪重新查驗）

29 格勾 27 格、未勾 2 格（機械計數：`[x]` 27、`[ ]` 2）。Steps 1–8、11–24 依現況成立：`package.json`／`package-lock.json`／`playwright.config.ts` 無 diff；`--list` 可收集 20 案；`failureSignal.ts` 仍為 5 個 `SignalKind`、6 個 `SignalEndpoint`；`LiveRegion.tsx:50-51` 的 `role="status"`／`data-testid`；`ReselectionBanner.tsx:180` 的 `can('K3', 'view')`、`Layout.tsx:26` 直接渲染；`App.tsx:176`、`:189` 兩條路由；`merge-blockers.md` 第 9 列已回填。未勾兩格與前輪同理由：

| 格 | 未勾理由 |
|---|---|
| Step 9 `[移出專案]` 就地移除 | 實作為移出成功後 `navigate()` 回清單頁、清單頁重新掛載時再抓一次，不是就地移除；其餘（角色下拉就地更新、二次確認、409 守門文案、`OPEN-MP24-7` 佔位）皆成立 |
| Step 10 在 `Sidebar.tsx` 新增入口 | 路由半邊成立；本單元未改 `Sidebar.tsx`。成員頁經「側欄專案 → `/projects` → `ProjectDetailPage.tsx:83` 成員連結」可達，`merge-blockers.md` 第 9 列記 review-03 判定已滿足；照計畫字面維持未勾，是否改判由 conductor／使用者決定 |

### 六、未做與留意

- `review-05` 的 `R-08`（分頁列 `aria-live` 與 44px）、`R-09`／`R-14`（邀請後跳頁的閉包長度與無斷言）、`R-13`（訊號種類標錯）不在 §五之三 範圍，未改。
- (c) 只斷言 409 一條錯誤路徑；403 與「其他錯誤」兩條同樣經 `closeConfirm()`，未各自斷言。
- `merge-blockers.md`、`unit-test-instructions.md`、問題檔依指示未動。
