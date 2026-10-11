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

