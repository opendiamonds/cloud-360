# Functional Spec — `U24 member-pages-ui`

> **本檔為自足規格。** 單元類型 `ui`，`produces_kinds` 不含 `entities`／`rules`
> （兩者皆為 `[service, spec, library]`），故本檔的互動流程與畫面狀態轉移
> **不依賴實體檔**——這是 stage 檔對 UI-only 單元的逐字授權。
>
> **但本站仍產出了 `rules.md`**，因為同一個 stage 的 `traceability` sensor
> 無條件要求它存在（實測見 `rules.md` 檔頭與 `OPEN-MP24-4`）。該檔的內容嚴格
> 限定在本單元自己的 UI 層行為規則，沒有一條從 `U19` 轉抄。
> 故兩個衍生檢視的現況是：**ER 圖為 N/A**（無 `entities.md`，無來源可衍生），
> **規則摘要存在**（在 `rules.md` 內，由其 YAML 區塊衍生）。

## 零、上游來源（逐檔）

| 來源檔 | 本檔用到它的什麼 |
|---|---|
| `inception/units-generation/unit-of-work.md` | `U24` 的交付清單、驗證方式（Playwright e2e）、依賴（`U19`／`U3`）、被依賴（`U17`），以及四條硬約束（兩層抓取形狀、`apiUrl()`、live region、橫幅須在落地時即在 DOM、橫幅落點為落地頁） |
| `inception/units-generation/unit-of-work-story-map.md` | 本單元承載 `US12.1`／`US12.2`／`US12.4`／`US12.5`／`US12.6` 共五則（**`US12.3` 只落在 `U19`**），以及「畫面只顯示 `U19` 回的理由」這條責任切分 |
| `inception/requirements-analysis/requirements.md` | `FR12.1`–`FR12.6b`，特別是 `FR12.4c`（橫幅）與 `FR12.4c-i`（已讀須伺服器持久化）、`FR12.6a`（缺全域權限者不得被邀請） |
| `inception/domain-design/components.md` | `ProjectMembership` 的行為邊界；前端不得自行推導 per-project 權限（不變量 `I-5`） |
| `inception/contract-design/contract-summary.md` | `K-16` 的 `public_interface`：`list_members`／`invite_member`／`remove_member`／`change_role` 四個方法對 `U24` 以 **http** 形式提供；`on_denied` 為 `MembershipForbidden`（router 轉 403）；`ReselectionOut` 的欄位集合 |

**上游已定案、本站不重問**的九項列於 `functional-design-questions.md` §一，不在此重述。

## 一、這個單元要做什麼

四個畫面單位，全部是前端，**零後端程式碼**：

1. **成員清單頁** —— 專案的成員與其 per-project 角色。管理者視角有 `[邀請成員]`
   與進入詳情的 `[>]`；一般成員視角為**唯讀**（`[D9]`=A）。
2. **成員詳情頁** —— 角色下拉、`[移出專案]`（破壞性，需二次確認）、變更紀錄。
3. **邀請對話框** —— 含**拒絕態**（缺全域功能權限時，顯示 `U19` 回傳的理由）。
4. **交棒橫幅** —— 落在使用者**自己的落地頁**，一則彙總 ＋ 可展開列出專案名
   （`[D10]`=A），「知道了」與「查看成員」兩個動作各有定義的效果。

## 二、本站的四個定案及其後果

| # | 定案 | 直接後果（寫進規格的部分） |
|---|---|---|
| `[F1]`=A | 橫幅掛在既有 `Layout` 元件裡 | 一處實作涵蓋全部落地頁；`AC12.4.3` 對任何角色組合成立，不需維護一份「可能的落地頁」清單 |
| `[F2]`=A | 掛載時打一次 REST，按「知道了」後寫入 | 沿用兩層抓取形狀，零新機制；且**實測不需要任何新端點**（見 §四） |
| `[F3]`=A | live region 元件由 `U23` 建、`U24` 沿用 | `U24` 的完成條件含一條對 `U23` 的跨單元依賴；**不新增依賴圖上的邊**（`U23` 在交錯順序中本就較早） |
| `[F4]`=A | 改完角色後成員清單**就地更新** | 無閃爍；沿用 `AdminPage.tsx` 的就地更新形狀，符合 `react-hooks/immutability`（error 級） |

### 二之一、`[F1]`＋`[F2]` 合起來產生的硬約束（本站推導，非上游原文）

`[F1]`=A 把橫幅放進 `Layout`，`[F2]`=A 讓它的**內容**在掛載後才到達。兩者合起來
會重新產生 `[US:D-11]` 警告的那個缺陷——除非：

> **`<ReselectionBanner>` 的宿主元素必須無條件渲染並帶 `role="status"`，
> 即使當下沒有任何待通知事件。**

理由逐字對應 `[US:D-11]`：`aria-live="polite"` 掛在一個**稍後才被插入**的元素上
不會被朗讀；而插入到一個**已存在**的 `role="status"` 容器裡的內容**會**被朗讀。
故宿主空殼（零視覺高度、無邊框、無文字）是這個組合能滿足 `AC12.4.3` 的結構前提。

**可被 e2e 斷言的形式**（修訂 1／審查 `R-03` 統一三份產出的選擇器）：
落地後立刻查詢 **`[data-testid="reselection-banner-host"]`** 必須命中、
**且讀其 `role` 屬性必須等於 `"status"`**，且在資料到達前其 `textContent` 為空。
初版的斷言只查選擇器命中——把 `role` 屬性整個拿掉仍會綠燈，而
`role="status"` 正是本節自述的結構前提，那個斷言驗不到它自己的 statement。

### 二之二、live region 內不得放可互動內容（修訂 1／審查 `R-06`）

`role="status"` 隱含 **`aria-atomic="true"`**：區域內任何變動都會使**整個區域**
被重新播報。若把 `[D10]`=A 的可展開彙總（含兩個動作鈕與專案清單）整個巢在
宿主**之內**，使用者每按一次展開／收合，螢幕閱讀器就會把「你成了 N 個專案的
管理者」加上 N 個專案名**整串重讀一次**。

§六之一 寫「展開／收合不改變狀態」——狀態機層面正確，但 DOM 層面它改變了
live region 的內容，而初版沒有處理這個後果。**axe 不會回報「live region 內含
互動內容」這一類問題**，所以沒有任何機械閘門會抓到它。

> **處置**：宿主**只放要被朗讀的那段文字**；兩個動作鈕與可展開的專案清單
> 放在宿主**之外**的兄弟節點。元件樹見 `frontend-components.md` §二。
> 可觀察形式：展開／收合時 `[data-testid="reselection-banner-host"]` 的
> `textContent` **不變**。

## 三、畫面與路由

| 畫面 | 路由 | 進入方式 | 可見性把關 |
|---|---|---|---|
| 成員清單 | `/projects/:projectId/members` | 專案頁首的 `[成員]` 動作 | `K3 view`（`require_story_action("K3","view")` 已在端點側；前端沿用既有 `CapabilityRoute` 形狀做**能力層**可見性） |
| 成員詳情 | `/projects/:projectId/members/:userId` | 清單列的 `[>]`（**僅管理者視角可見**） | 同上；per-project 的管理者判定**由伺服器回傳決定**，前端不得推導（`I-5`） |
| 邀請對話框 | 無獨立路由（成員清單頁內的 modal） | `[邀請成員]` | 同上 |
| 交棒橫幅 | 無路由（`Layout` 內的常駐宿主） | 自動 | 端點以 `principal.user_id` 過濾，只回自己的事件 |

**per-project 角色不由前端推導，而取得方式是具體的**（修訂 1／審查 `R-01`）：
清單列的 `[>]`、`[邀請成員]`、`[移出專案]`、角色下拉這四個控件的出現與否，
依據 `canManage`，而 `canManage` 的唯一取得方式是 **`BR22.3`**：

> 以**自身 `user_id`** 在 `list_members` 的回應中找到自己那一列，讀它的 `role`；
> `role == "project_admin"` 即 `canManage` 為真。找不到自身即為假。

**初版在此寫了兩個經查證不成立的依據，必須更正**：
①「`list_members` 的結果是否包含管理者才拿得到的形狀」——**不存在這種形狀**，
`MemberView`（`membership_types.py:80-96`）對**所有**呼叫者回同一組四個欄位
（`user_id`／`display_name`／`role`／`joined_at`）；
②「或端點直接回 403」——`list_members` 的 403 依 `membership_router.py:169`
的 docstring 代表「**完全不是成員**」，而四個變更端點的 403 只在**動作送出後**
才出現，無法用來決定要不要渲染按鈕。
`K-16` 的 `resolve_project_role` 雖是 per-project 判定的宣告入口，但其
`consumed_by` 為 `[U20, U13, U21]`——**不含 `U24`**，且無對應 HTTP 端點。

`BR22.3` 讀的是**伺服器給的 `role` 結論**，不是拿全域角色自己算，故不違反
不變量 `I-5`。它同時讓 `[D9]`=A（一般成員唯讀清單）第一次有了可觸發的斷言：
以本專案的一般成員身分開啟成員頁，四個控件必須全部不存在——而初版的
observable 綁在 403 上，對「是成員但非管理者」（他拿到 **200**）永不觸發。
`K-16` 的 `residual_gap`（無機械強制）仍在，見 §八 `OPEN-MP24-2`。

## 四、API 消費點（**已實測存在於磁碟**，非設計推測）

`main.py` 以 `prefix="/api/membership"` 掛載 `membership_router`。

| # | 方法與路徑 | 回應 | 本單元的消費點 | 承載的 AC |
|---|---|---|---|---|
| 1 | `GET /api/membership/projects/{project_id}/members` | `List[MemberView]` | 成員清單頁掛載 | `AC12.1.1`、`AC12.2.1`、`AC12.6.1`、`AC12.6.2` 的觀察面 |
| 2 | `POST /api/membership/projects/{project_id}/members` | `MemberView`，**201** | 邀請對話框送出 | `AC12.6.1`；**422** 有**兩種**語意——`detail` 為字串＝缺全域權限（`AC12.5.1`），`detail` 為物件陣列＝pydantic 驗證錯誤（`BR23.1` 的分流） |
| 3 | `DELETE /api/membership/projects/{project_id}/members/{user_id}` | **204** | 詳情頁 `[移出專案]` ＋ 二次確認 | `AC12.6.2`；**409** 為最後一位管理者守門 |
| 4 | `PATCH /api/membership/projects/{project_id}/members/{user_id}` | `MemberView` | 詳情頁角色下拉存檔 | `AC12.2.1`；**409** 同上 |
| 5 | `GET /api/membership/reselections/pending` | `List[ReselectionOut]`；**403** 為缺 `K3 view`（永久失敗，不重試——`BR21.3`） | `Layout` 掛載（`[F2]`=A） | `AC12.4.3` |
| 6 | `POST /api/membership/reselections/{event_id}/acknowledge` | **204**；**404** 為「查不到／不屬於你／**已被確認**」——**等價於成功**（`BR26.3`，端點**不冪等**） | 橫幅「知道了」 | `AC12.4.4` |

**`[F2]`=A 不需要任何新端點**——第 5、6 兩個端點已存在且語意正好符合：
`GET` 只回自己未確認的 `cause='auto_reselection'` 事件，`POST` 以**事件**為鍵標記
已讀（不是 per-user 布林值）。這是本站把 `[F2]` 的四個選項逐一對照磁碟現況後的
查證結果，不是偏好。

### 四之一、`MemberView` 的欄位集合（照既有程式，不擴充）

`user_id`、`display_name`、`role`、`joined_at`。**刻意不含** `invited_by`
（`entities.md` 列為懸空契約端 `OPEN-FD19-6`，並明文要求不自行加入），
也**不含**任何全域角色或授權結論（`I-5`）。本單元不要求擴充它。

## 五、互動流程（numbered step sequences — 本檔是這些流程的**正本**）

### W1. 開啟成員清單（管理者視角）

1. 使用者在專案頁首點 `[成員]`，前端導向 `/projects/:projectId/members`。
2. 元件掛載 → 呼叫**純抓取函式** `fetchMembers(projectId)`（不碰 state，回傳資料）。
3. 呼叫端在 `.then` 設成員陣列、`.catch` 設錯誤訊息、`.finally` 關閉載入態；
   `useEffect` 內以 `cancelled` flag 防卸載後 setState（`react-hooks/set-state-in-effect`
   為 **error** 級，違反即 CI 紅燈）。
4. 載入中與錯誤態的文字寫進 `U23` 提供的 live region 元件（`[F3]`=A），
   **不得**沿用 `AdminPage.tsx:104` 的 4 秒 toast（無 `role`／`aria-live`）。
5. 成功 → 渲染清單；每列顯示顯示名稱、per-project 角色、加入時間、`[>]`。
   **清單上沒有任何可直接改角色的控件**（`AC12.2.3`）。

### W2. 開啟成員清單（一般成員視角，`[D9]`=A）

1–4. 同 W1。
5. 成功 → 渲染**唯讀**清單：看得到全部成員與角色，**無** `[邀請成員]`、
   **無** `[>]`、**無** `[移出專案]`。

### W3. 邀請成員

1. 管理者點 `[邀請成員]` → 開啟 modal，焦點移入第一個欄位。
2. 填入受邀者與角色（預設 `一般成員`），送出。
3. 送出中：按鈕進入忙碌態並**停用**（防重複送出），modal 不可關閉。
4. **201** → 以回傳的 `MemberView` **就地**把新列加進清單（`[F4]`=A 的同一形狀），
   關閉 modal，live region 播報「已邀請 {displayName}」。清單**必然多一列**
   （`AC12.6.1`）。
5. **422** → 先看 `detail` 的形狀（`BR23.1`，修訂 1／審查 `R-12`）：
   - **`detail` 為字串**（＝受邀者缺全域功能權限）→ **不關閉 modal**，在 modal 內
     顯示 `U19` 回傳的那個字串（畫面**不自行組字**，
     `unit-of-work-story-map.md:186-188`）。清單**不新增任何列**
     （`AC12.5.3`：拒絕不留半套狀態）。
   - **`detail` 不是字串**（＝pydantic 的驗證錯誤，物件陣列）→ 走一般錯誤路徑，
     **不把陣列當文案顯示**。

   > `membership_router.py:192-206` 的 422 描述逐字含「受邀者缺少對應的全域功能
   > 權限……**或角色不在封閉列舉內**」——後者的 `detail` 是物件陣列，而
   > `frontend-components.md` §五 的既有形狀是「取 `data.detail` 當錯誤訊息」，
   > 不分流就會把一個陣列渲染成文字。經設計的 UI 下可達性低（角色是封閉列舉的
   > select、受邀者來自選擇器），但不是零——請求可被改寫、列舉值可能漂移。
6. **403** → 關閉 modal，清單頁顯示「你沒有管理這個專案的權限」並重抓一次
   （權限可能剛被改）。

### W4. 改角色

1. 管理者在清單點某列 `[>]` → 導向 `/projects/:projectId/members/:userId`。
2. 詳情頁掛載，抓取該成員資料與變更紀錄（步驟形狀同 W1 第 2–4 步）。
3. 改角色下拉 → 存檔 → `PATCH`。
4. **200** → 以回傳的 `MemberView` **就地更新**清單與詳情兩處的該成員
   （`[F4]`=A；`setMembers(prev => prev.map(...))`，不整份重抓，無閃爍）。
   變更紀錄新增一列（誰、何時、由什麼改為什麼，`AC12.2.2`）。
5. **409（最後一位管理者）** → 角色下拉**還原為原值**，顯示守門理由並列出
   `LastAdminGuardReport` 帶回的專案。

### W5. 移出成員

1. 管理者在詳情頁點 `[移出專案]`。
2. 開啟**二次確認對話框**（破壞性動作，線框 §25 的既有規定）。
3. 確認 → `DELETE`。
4. **204** → 導回清單頁，**就地**移除該列（清單**必然少一列**，`AC12.6.2`），
   live region 播報「已將 {displayName} 移出專案」。
5. **409** → 留在詳情頁，顯示守門理由與專案清單。

### W6. 交棒橫幅

1. 任何頁面落地 → `Layout` 渲染 `<ReselectionBanner>` 的宿主
   （`role="status"`，**此時為空**，見 §二之一）。
2. 同一次掛載呼叫 `fetchPendingReselections()`（`[F2]`=A）。
3. 零筆 → 宿主保持空（不渲染任何可見內容；宿主本身仍在 DOM 裡）。
4. 一筆 → 顯示單一專案的文案。
5. 兩筆以上 → 顯示**一則彙總**「你成了 N 個專案的管理者」＋ 可展開
   （`[D10]`=A）；展開後列出各專案名與連結。
6. 「知道了」→ `POST .../acknowledge` **逐事件**呼叫（每筆一次），
   **逐筆記錄結果**（`BR26.3`）：
   - **204 或 404** → 視為該事件已確認，**從本機 `events` 移除**。
     404 的語意逐字是「查不到該事件、它不屬於你，或**它已被確認**」
     （`membership_router.py:328-358`），所以它等價於成功。
   - **其他回應** → 該事件**留在**本機 `events`。
   全部移除完畢 → 橫幅內容清空；仍有留存 → 回到 `shown-*` 並顯示錯誤。
   換裝置重新登入後不再出現（`AC12.4.4`，因已讀狀態在伺服器）。

   > **修訂 1／審查 `R-02`：這個端點不冪等，而初版的規定會讓橫幅永遠清不掉。**
   > 初版寫「全部 204 後移除」且 §六之一 規定「任一失敗 → `shown-*` 並顯示錯誤」，
   > 沒有任何移除已成功項的步驟。代入三筆事件、第二筆失敗：本機仍是三筆 →
   > 使用者再按一次 → **第一筆這次回 404** → 又是「任一失敗」→ 永遠停在
   > `shown-*`，而伺服器上那兩筆已是已讀、重新載入也不會回來，本機與伺服器
   > **永久分歧**。這正是 `AC12.5.3` 所拒絕的半套狀態——§六之二 為邀請流程
   > 特別處理了它，而 W6 初版沒有。
7. 「查看成員」→ 導向該專案的成員清單頁（`/projects/:projectId/members`）。
   **多筆彙總時**此動作導向展開清單中被點選的那一個專案，不是任意一個。

## 六、狀態機

### 六之一、交棒橫幅

| 狀態 | 進入條件 | 可見內容 | 離開 |
|---|---|---|---|
| `host-empty` | 落地即此態 | 宿主在 DOM，`textContent` 為空 | 抓取回傳 ≥1 筆 → `shown-single`／`shown-aggregate` |
| `loading` | 抓取進行中 | 宿主仍空（**不顯示骨架**——橫幅是通知不是內容，骨架會變成一則假通知） | 成功／失敗 |
| `shown-single` | 回傳恰 1 筆 | 單一專案文案 ＋「知道了」「查看成員」 | 「知道了」→ `acknowledging` |
| `shown-aggregate` | 回傳 ≥2 筆 | 彙總文案 ＋ 可展開 ＋ 兩個動作 | 同上；展開／收合不改變狀態 |
| `acknowledging` | 按下「知道了」 | 動作鈕忙碌並停用 | 逐筆處置（`BR26.3`）：**204 或 404** 的事件從本機移除；全部移除完畢 → `host-empty`；仍有留存 → `shown-*` 並顯示錯誤（**只顯示真正未成功的那幾筆**） |
| `fetch-failed` | 抓取失敗 | 宿主仍空；**不顯示錯誤給使用者** | **403（缺 `K3 view`）→ 永久失敗，本工作階段不再發出該請求**；其他原因 → 下次落地重試（`BR21.3`） |

**`fetch-failed` 刻意不對使用者說話**：橫幅的抓取是背景行為，使用者沒有發起它；
把它的失敗變成一則錯誤訊息，會在每個落地頁給出一個使用者無法處置的雜訊。
失敗只記 `console` 層級的紀錄（**不含任何使用者文字或識別字**，`BR28.1`）。

**403 必須與暫時性失敗分開**（修訂 1／審查 `R-11`）：端點 5／6 掛
`require_story_action("K3", "view")`，而實測 `rbac_seed_data.py:343-345` 顯示
`SRE`／`Ops_Lead`／`Platform_Engineer` 的 `K3 view` 為 **False**。宿主在
`Layout` 裡（`[F1]`=A），所以這三個角色的使用者**每一次落地**都會發出一個
必定 403 的請求，而初版的「下次落地重試」使該重試永遠不會成功。
行為上無害（`AC12.4.3` 不受影響——審查已另行證實：`membership_service.py:71-72`
要求**受邀者**具 `K3 view`，故缺它的人不可能成為成員、也不可能被自動改選），
但這是一個可零成本避免的固定開銷與 log 噪音。處置：宿主以
`can('K3','view')` 作為發出請求的前置條件（前端已有 `useAuth` 的 `can()`，
`RouteGuard.tsx:35` 的 `CapabilityRoute` 正在用它）。

### 六之二、邀請對話框

`closed` → `open`（焦點移入）→ `submitting`（按鈕停用）→
`closed`（201，清單多一列）｜ `rejected`（422，**停在 open 並顯示理由**）｜
`closed`（403，清單頁顯示權限訊息）。

`rejected` **不是** `closed` 的一種：`AC12.5.3` 要求拒絕時清單不新增任何列，
而關閉 modal 會讓使用者以為動作完成了。

### 六之三、成員詳情的角色下拉

`idle` → `dirty`（值被改但未存）→ `saving` → `idle`（200，就地更新兩處）｜
`idle`（409，**下拉還原為原值** ＋ 顯示守門理由）。

**409 必須還原**：留著使用者選的新值會讓畫面顯示一個伺服器拒絕過的狀態，
而下一次重新載入它會跳回舊值——那是一個無聲的不一致。

## 七、衍生檢視

**兩個衍生檢視的現況不同，必須分開陳述**（本節在 `rules.md` 落地後修訂）：

| 衍生檢視 | 現況 | 理由 |
|---|---|---|
| **ER 圖**（衍生自 `entities.md`） | **N/A** | 本單元不產出 `entities.md`（`produces_kinds` 的 `entities: [service, spec, library]` 不含 `ui`），**沒有來源可衍生**。不從 `U19` 的 `entities.md` 轉抄——轉抄會讓同一份實體模型物化第二份，違反 `team.md` 的單一真實來源 |
| **規則摘要**（衍生自 `rules.md`） | **存在**，位於 `rules.md` 的「規則摘要（人類可讀）」表 | 本站因 sensor 的無條件要求而產出 `rules.md`（見 `OPEN-MP24-4`）。既然來源存在，衍生檢視就該存在；它放在 `rules.md` 內與該檔的 YAML 區塊相鄰，而非複製到本檔 |

**本檔不複製那張摘要表**：同一份摘要出現在兩個檔案裡，第二份必定悄悄過期。

## 八、開放項與指派

| # | 項目 | 性質 | 落點 |
|---|---|---|---|
| `OPEN-MP24-1` | **`ReselectionOut` 沒有專案名稱，而 `[D10]`=A 要求橫幅「可展開**列出專案名**」。** 實測 `membership_router.py:81-102` 的 `ReselectionOut` 有**九個**欄位（`id`、`project_id`、`cause`、`promoted_user_id`、`previous_owner_user_id`、`previous_role`、`new_role`、`occurred_at`、`acknowledged_at`），**其中不含專案名稱**；其 docstring 逐字寫「消費端若需要名稱，那是一次**有明確來源的擴充**」。**修訂 1／審查 `R-07`：初版把這裡寫成「只有 `id` 與 `project_id`」，那會讓實作者以為手上只有兩個欄位，而事件其實已帶著足以組出完整文案的資訊，缺的只有名稱這一項**——`[D10]`=A 正是那個來源。兩條路：①`U19` 的回應模型加一個名稱欄位（一個欄位，有已核可來源）；②`U24` 對每筆事件再打一次專案端點取名（N+1 請求，且本 repo 無此形狀的先例）。**本站不逕自改 `U19` 已完成的程式**，標出缺口並指派 | 跨單元契約缺口 | **`U24` 的 `code-generation`（3.5，`ALWAYS`，在游標之後）**。`U19` 的 `code-generation` 已完成且在游標之前，故不是有效落點 |
| `OPEN-MP24-2` | **`K-16` 的 `residual_gap` 逐字：「per-project 判定結論由伺服器產生、前端不得推導（`I-5`），但沒有機制擋住前端自己猜」。** 本站把它寫成 §三 的規格條文（四個控件的出現依據伺服器回應），但那是**散文約束不是閘門**——前端仍可拿全域角色自己算而沒有任何東西變紅 | 殘留缺口，**非本站可關閉** | 承接 `K-16` 的原指派；本站只記載，不宣稱已解決 |
| `OPEN-MP24-4` | **stage 定義自我牴觸：`produces_kinds` 把 `rules` 排除在 `ui` 之外，而同一個 stage 的 `traceability` sensor 無條件要求 `rules.md` 存在、且每個 `OK` 列的 target 必須指名 `BRx.y`。** 實測：缺檔時 sensor 回 `required upstream artifact is missing: .../rules.md`，且 11 個 `OK` 列全被判 `target must name at least one BRx.y ID`。本站的處置是產出一份**只含本單元自己 UI 層行為規則**的 `rules.md`（**19** 條，全部外部可觀察），而非留著 sensor 紅燈或從 `U19` 轉抄。**附帶實測（審查 `R-04` 的連帶）**：sensor 以 `/\bBR\d+\.\d+\b/g` 掃**整份** `rules.md`，所以在該檔的散文裡寫出 `U19` 的識別字字面會被當成本檔的孤兒規則（初版即回報 16 個假孤兒）——本檔的識別字區段已改到 `BR21`–`BR28`，且談 `U19` 的 id 時一律不寫字面形式。**不得直接改 `.claude/` 下的 upstream 檔**（`project.md` 的禁令），故真正的修法須以 issue 或升級記錄承載 | 框架缺陷，非本 intent 可修 | 以 issue／升級記錄承載；本站只記載處置 |
| `OPEN-MP24-5` | **`AC12.1.3` 與 `AC12.6.3` 的畫面在 `U23`，而已核可的 story map 從未把 `U23` 列為這兩則故事的實作單元。** `unit-of-work-story-map.md:174-179` 把 `US12.1` 映射到 `U19`／`U24`／`U18`、`US12.6` 映射到 `U19`／`U24`——**兩列都沒有 `U23`**；`U23` 的映射只有 `US11.1`／`US11.2`／`US11.3`。兩條 AC 的 Then 確實落在專案清單頁（判定本身成立），但**沒有任何已核可文件讓那個單元知道它要承接**，實測 `construction/project-pages-ui/functional-design/traceability.json` 尚不存在。**修訂 1／審查 `R-05`**：初版把 target 直接寫成 `U23 project-pages-ui`，那是 `project.md` 記過三次的死指派形狀 | 上游映射缺口 | **`U23` 的 `code-generation`（3.5，`ALWAYS`，在游標之後）**確認承接。`U23` 的 `functional-design` 為 `CONDITIONAL`，故不作為唯一落點 |
| `OPEN-MP24-3` | **「變更紀錄」的分頁與保存期限未定。** `AC12.2.2` 只要求它顯示「誰在何時把角色由什麼改為什麼」，沒有規定列數上限或保存期；而一個長壽專案的紀錄會無上界成長 | 未定參數 | `U24` 的 `nfr-requirements`（3.2，下一站） |

## 九、自檢報告（七項，逐項）

| # | 自檢項 | 結果 |
|---|---|---|
| 1 | **可達性**——每條「偵測 X 狀態」的規則先驗 X 可達 | 通過。`fetch-failed`、`rejected`、`409 還原` 三個狀態的觸發條件都對應到**磁碟上實際存在**的端點回應（422／409／網路失敗），不是推測 |
| 2 | **契約端點三問**（誰寫／誰讀／誰清） | **查出一處缺口**：`ReselectionOut` 的**專案名稱有讀者（橫幅）無提供者** → `OPEN-MP24-1`。另三處完整：成員列由端點 2 寫、端點 1 讀、端點 3 清；角色由端點 4 寫、端點 1 讀；已讀狀態由端點 6 寫、端點 5 讀（過濾 `acknowledged_at IS NULL`） |
| 3 | **引用逐字核對**（分開驗事實與驗定位） | 通過。六個端點的路徑與回應碼以 `grep -n` 自 `membership_router.py` 取得並逐一開檔核對；`ReselectionOut` 的欄位集合引用 `:81-95`；`MemberView` 引用 `membership_types.py:80-96`（修訂 1／審查 `R-09`：初版寫 `:80-94`，而 `:94` 是 `display_name`，被引用的四個欄位裡 `role`／`joined_at` 落在 `:95`／`:96`、區間之外）；`AdminPage.tsx:104` 的 toast 形狀引用自 `unit-of-work.md` 的原文而非我的印象 |
| 4 | **檔案集合一致性** | **查出一處並已處置**。directive 的 `produces` 為三份（`functional-spec`／`traceability`／`frontend-components`），但同 stage 的 `traceability` sensor 無條件要求 `rules.md`——兩者牴觸。實際交付**四份**（＋`rules.md`），牴觸本身記為 `OPEN-MP24-4`。`entities.md` 仍不產出，理由在 §七 |
| 5 | **跨檔傳播** | **修訂 1／審查 `R-10`：初版只掃了四份交付檔中的兩份**（漏 `rules.md` 與 `traceability.json`），而同份自檢的第 4 項才剛寫下「實際交付四份」。重跑後的落點（以逐詞 `grep -c` 實算）：`[F1]` 在 `functional-spec` §二／§三／§五 W6／§六之一、`frontend-components` §一／§二／§三、`rules.md` 的 `BR21.1`、`traceability.json` 的 `AC12.4.3`；`[F2]` 在 `functional-spec` §二／§四／§五 W6、`rules.md` 的 `BR21.3`；`[F3]` 在 `functional-spec` §二／§五 W1、`frontend-components` §二／§八、`rules.md` 的 `BR27.1`；`[F4]` 在 `functional-spec` §二／§五 W3·W4·W5／§六之三、`frontend-components` §一、`rules.md` 的 `BR23.2`／`BR24.1`／`BR25.2`、`traceability.json` 的對應四列。**一次完整的傳播掃查正好會比對 `BR21.1` 的 observable 與 §二之一 的斷言——那就是審查 `R-03` 抓到的那一處** |
| 6 | **可算的數字先算再寫** | **修訂 1／審查 `R-08`：初版的「開放項 3 項」是錯的**（`OPEN-MP24-4` 是後補的，計數沒跟著重算），且「見 §九之一」只支持了 AC 一項。現為：承載故事 **5** 則、AC **17** 條、API 消費點 **6** 個、互動流程 **6** 條、狀態機 **3** 個、開放項 **5** 項、規則 **19** 條。六項的取得方式逐一列於 §九之一 |
| 7 | **ADR-0006 四面向 ＋ PBT hard constraint** | 見 §九之二。**不沿用任何上游表格的判定欄**——本單元的範圍與 `U19` 不同 |

### 九之一、七個數字各自的取得方式（修訂 1／審查 `R-08`）

初版只給了 AC 一項的來源，而自檢 6 逐字寫「全部……見 §九之一」。逐一補上：

| 數字 | 值 | 取得方式 |
|---|---|---|
| 承載故事 | **5** | `unit-of-work-story-map.md:220` 的「`U24` … 5」一列；另以 `:175-180` 的五列逐列核對（`US12.3` 不在其中，理由見 `:186-188`） |
| AC | **17** | `US12.1` 3 ＋ `US12.2` 4 ＋ `US12.4` 4 ＋ `US12.5` 3 ＋ `US12.6` 3，逐則取自 `stories.md:758-904` 的 AC 表列數；並與 `traceability.json` 的 `upstream_ids` 長度交叉核對。**修訂 1／審查 `R-09`：初版的區間寫 `:758-903`，而 `:903` 是 `AC12.6.2`、`AC12.6.3` 在 `:904`——那個區間排除了它所計入的 17 條之一** |
| API 消費點 | **6** | `grep -n "@router\.\(get\|post\|patch\|delete\)" backend/services/membership_router.py` 的命中數（`:164`／`:192`／`:234`／`:270`／`:309`／`:328`） |
| 互動流程 | **6** | 本檔 §五 的 `### W` 標題數（W1–W6） |
| 狀態機 | **3** | 本檔 §六 的子節數（§六之一／之二／之三） |
| 開放項 | **5** | 本檔 §八 表格的資料列數（`OPEN-MP24-1`／`-2`／`-4`／`-5`／`-3`） |
| 規則 | **19** | `rules.md` §二 YAML 區塊的 `- id:` 行數；並與 §三 摘要表的列數交叉核對 |

**計數是收尾動作**：上表在本輪最後一次內容改動之後才重算一次
（`project.md` 的 `user-stories:78fff…`：腳本跑的時間點必須晚於最後一次內容改動）。

### 九之二、ADR-0006 security baseline 四面向

| 面向 | 判定 | 依據 |
|---|---|---|
| **IAM** | **適用** | 本單元渲染四個受權限控制的控件。處置：per-project 判定**一律**來自伺服器回應，前端不得推導（§三）；能力層可見性沿用既有 `CapabilityRoute`。殘留缺口為 `OPEN-MP24-2`（無機械強制），**如實標為未關閉** |
| **Encryption** | **不適用** | 本單元不新增傳輸通道、不新增任何儲存（含 `localStorage`——`AC12.4.4` 的已讀狀態**必須**在伺服器，這同時排除了前端持久化）。沿用既有 HTTPS 與既有 `fetch` 形狀 |
| **Network exposure** | **不適用** | 零新端點、零新進程邊界。六個消費點全部是既有端點（§四實測） |
| **Audit logging** | **適用** | `AC12.2.2` 的變更紀錄是**使用者可見**的稽核面。處置：紀錄由 `U19` 的持久層提供、本單元只渲染；前端**不自行記錄**任何稽核事件。另：`fetch-failed` 的 console 紀錄**不得含使用者文字或識別字**（§六之一）——本 repo 為 public，Actions log 公開可讀 |
| **PBT（agent routing／IaC／cost calculator）** | **不適用** | ADR-0006 點名的三個落點皆非本單元；本單元無純函式計算核心。`AC12.4.2` 的決定性 tie-break 是 PBT 標的，但它**在 `U19`**（`select_successor` 純函式），`stories.md:838-842` 已明記本單元不承載它。前端無 unit／PBT 框架（`team.md` 既成事實），唯一自動化層是 Playwright e2e |
