# Rules — `U15 memory-page-ui`

## 一、本檔存在的理由與識別字區段

> **為什麼一個 `ui` 單元有這份檔。** stage 檔的 `produces_kinds` 把 `rules` 限定在
> `[service, spec, library]`，`ui` 不在其中；但**同一個 stage 的 `traceability`
> sensor 無條件要求 `rules.md` 存在**，且每個 `OK` 列的 target 必須指名至少一個
> `BRx.y` 並存在於本檔（`.claude/tools/aidlc-sensor-traceability.ts:493-502`）。
> 兩者牴觸，先例 `U24 member-pages-ui` 同為 `ui` 且同樣產出本檔，記為 `OPEN-MP24-4`。
> 本單元沿用同一處置，不重複開一個同義的 open item。

### 識別字區段：`BR31.x`–`BR35.x`

sensor 以 `/\bBR\d+\.\d+\b/g` 掃**整份** `rules.md`，任何出現在本檔的他單元識別字
都會被當成本檔的孤兒規則。本 intent 已出現過的區段（實算 13 份 `rules.md`）：

| 區段 | 佔用者 |
|---|---|
| `BR1`–`BR8` | 11 個 `service`／`spec`／`library` 單元各自使用，**含同功能域的 `U8 memory-service`（`BR1`–`BR7`）** |
| `BR21`–`BR28` | `U24 member-pages-ui` |

本單元取 **`BR31`–`BR35`**。理由與 `U24` 相同但落點不同：`U15` 的功能域兄弟是
`U8 memory-service`，而 `U8` 的 `BR1`–`BR7` **已寫進出貨程式的 docstring**
（`memory_router.py`、`memory_facade.py`、`memory_service.py` 皆引用），沿用 `BR1.x`
會讓同一個識別字在同一個功能域裡指兩件無關的事。

**本檔刻意不寫出 `U8` 那些識別字的字面形式**——寫出來就會被 sensor 當成本檔的孤兒。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR31：路由、入口與授權責任 ----------------------------------------
  - id: BR31.1
    statement: "`/memory` 走 `ProtectedRoute`，**不包** `CapabilityRoute`"
    category: authorization
    applies_to: "路由宣告"
    trigger: "任何使用者導向 `/memory`"
    logic: >
      IF 未登入 THEN 由既有 `ProtectedRoute` 導向登入頁；
      IF 已登入 THEN 渲染記憶頁，**不再檢查任何 story id**。
    violation_behaviour: "包上 `CapabilityRoute` 會要求一個不存在的 story id，使所有人被導向 /403"
    source: "K-14 provides.guard；mockups.md M0 的查證"
    note: >
      前例是 `/waiting-approval`。**上游的行號citation 有兩層錯誤，本站更正**：
      `mockups.md` M0 寫 `App.tsx:38–41`、`K-14` 修訂 1「精修」為 `37–44`
      並逐行narration（37 `<Route`、38 `path=`…）。實讀磁碟：
      `:37` 是 `<Routes>`、`:39` 是 `/403`，該區塊**現為 `App.tsx:40-47`**
      （40 `<Route`、41 `path=`、42 `element={`、43 `<ProtectedRoute>`、
      44 頁面、45 `</ProtectedRoute>`、46 `}`、47 `/>`）。
      兩種偏差都已查明成因：① `K-14` 的 `37` 在寫下當時即錯一行——
      `git show HEAD~2:frontend/src/App.tsx` 顯示 `U24` 之前該區塊是 `38-45`；
      ② `U24` 在其後插入 member 路由（App.tsx +35 行），再推下 2 行。
      依 `refined-mockups:c3` **不回改上游**，更正記在本站。

  - id: BR31.2
    statement: "記憶的兩個入口（Sidebar 項、入口頁捷徑）使用**同一個**顯示條件判定"
    category: constraint
    applies_to: "Sidebar 項、入口頁捷徑"
    trigger: "渲染任一入口"
    logic: >
      兩個呼叫點一律呼叫同一個判定（本單元提供的單一函式／常數），
      判定內容為「已登入」；
      IF 任一呼叫點自行判斷 THEN 違反 INV-3。
    violation_behaviour: "兩處各自判斷時，下一個加權限的人只會改一處，另一處靜默失去把關"
    source: "interaction-spec.md:33 的 INV-3；[M4]=A"
    note: >
      `[M4]`=A：本單元實作判定本體與 Sidebar 這一個呼叫點；入口頁捷徑的**渲染**
      留給 `U14 entry-page-ui` 匯入同一個判定。故本單元的 e2e 只驗得到
      Sidebar 那一半，另一半的驗證義務隨判定一起交給 `U14`——已列為
      `OPEN-MP15-1`。**本單元不在 `/brain` 掛捷徑**：`Sidebar.tsx:209` 的註解
      逐字寫「正式落點是 `U14`……**屆時整段取代**」，掛上去會被連帶刪除。

  - id: BR31.3
    statement: "前端**不自行過濾**記憶的擁有者或可見範圍"
    category: authorization
    applies_to: "三區的資料抓取與渲染"
    trigger: "收到 `GET /api/memory/records` 的回應"
    logic: >
      IF 回應為 200 THEN 渲染回應中的**每一列**；
      不得以 `owner_user_id`／`visibility_scope` 把任何一列移出畫面。
    violation_behaviour: "前端再濾一次就有第二份可見範圍實作，兩份遲早分歧"
    source: "K-14 behaviour_semantics.authorization_responsibility 逐字「前端不自行過濾」"
    note: >
      `memory_service.py:271-274` 逐字「不可見的列從未離開資料庫，且 `LIMIT`
      作用在已過濾的集合上」。本規則與 `BR35.2`（不渲染非擁有者的刪除鍵）
      **不衝突**：前者管「哪些列出現」，後者管「某列上有哪些控件」。

  # ---- BR32：三區的檢視 --------------------------------------------------
  - id: BR32.1
    statement: "三區固定存在、順序固定（語意 → 程序 → 情節），即使某區為空"
    category: constraint
    applies_to: "記憶頁版面"
    trigger: "頁面渲染"
    logic: >
      三個 `region` 一律在 DOM 中，順序為 semantic、procedure、episodic；
      IF 某區無資料 THEN 該區顯示 `empty` 態，**不隱藏該區**。
    violation_behaviour: "隱藏空區會讓使用者以為系統只有某幾類記憶，且區塊位置隨資料變動"
    source: "wireframes.md §9；mockups.md M6；AC4.1.3 的「三者皆可被取得」在畫面層的對應"

  - id: BR32.2
    statement: "每區各自抓取、各自擁有 `loading`／`error`／`empty` 三態"
    category: constraint
    applies_to: "三區的資料抓取"
    trigger: "頁面載入、情節記憶翻頁、刪除後的頁次調整"
    logic: >
      對每個 kind 各發一次 `GET /api/memory/records?kind=<kind>`；
      IF 某區失敗 THEN **只有該區**進入 `error`，其餘兩區不受影響。
    violation_behaviour: "單一請求時一次失敗就是三區全失敗，直接違反 States 表"
    source: "interaction-spec.md States 表；[M2]=A"

  - id: BR32.3
    statement: "`empty` 與 `error` 必須是**可區分**的畫面"
    category: constraint
    applies_to: "每個 region"
    trigger: "該區無資料，或該區抓取失敗"
    logic: >
      IF 回應 200 且陣列為空 THEN 顯示「大腦還沒記住……」＋ 說明何時開始累積；
      IF 抓取失敗 THEN 顯示「無法載入」＋ 重試控件，**不得**顯示 empty 文案。
    violation_behaviour: "共用畫面時，讀取失敗會被使用者讀成「我的記憶被清空了」——而記憶正是他被承諾可稽核與刪除的資料"
    source: "interaction-spec.md:502-503（該檔明文定案）"

  - id: BR32.4
    statement: "區標題的則數在回傳筆數等於請求上限時顯示「N+ 則」，不宣稱精確數"
    category: validation
    applies_to: "三區的標題計數"
    trigger: "渲染區標題"
    logic: >
      IF `items.length < 請求的 limit` THEN 顯示「<items.length> 則」；
      IF `items.length === 請求的 limit` THEN 顯示「<items.length>+ 則」。
    violation_behaviour: "一律顯示 `items.length` 時，第 201 筆起的使用者會看到「200 則」——一個錯的數字"
    source: "[M1]=A 的原則一致套用；memory_service.py:72-73 的 DEFAULT_LIST_PAGE_SIZE=50／MAX_LIST_PAGE_SIZE=200"

  # ---- BR33：分頁 --------------------------------------------------------
  - id: BR33.1
    statement: "情節記憶以 `limit = pageSize + 1` 探測是否還有下一頁；第 `pageSize+1` 筆不渲染"
    category: calculation
    applies_to: "情節記憶區"
    trigger: "載入情節記憶，或翻頁"
    logic: >
      請求 `?kind=episodic&offset=<(page-1)*pageSize>&limit=<pageSize+1>`；
      `hasNext = items.length > pageSize`；渲染 `items.slice(0, pageSize)`。
    violation_behaviour: "無此探測時「下一頁」要麼永遠可按（按到空頁），要麼永遠不可按"
    source: "[M1]=A"
    note: >
      **總筆數不存在**：`GET /api/memory/records` 整條路徑沒有任何 `count()`
      （`memory_router.py` 的 `response_model=List[MemoryView]`、
      `memory_facade.py:299-318`、`memory_service.py` 的
      `.offset(...).limit(size).all()`）。

  - id: BR33.2
    statement: "情節記憶顯示「第 N–M 則」，**不**顯示總數、**不**使用 `PaginationControl`"
    category: constraint
    applies_to: "情節記憶區的分頁控件"
    trigger: "渲染情節記憶區"
    logic: >
      顯示「第 <offset+1>–<offset+rendered> 則」＋「上一頁」「下一頁」兩鍵；
      第一頁時「上一頁」停用；`hasNext` 為 false 時「下一頁」停用。
    violation_behaviour: >
      `PaginationControl` 的 props 逐字要求 `total: number`
      （`PaginationControl.tsx:8-11`，註解「總筆數，取自回應」），
      而回應沒有這個值——餵近似值會顯示一個隨翻頁變大的錯數字。
    source: "[M1]=A"
    note: >
      **這是對已核可線框的偏離，記為對齊修正**：`mockups.md` M6 逐字畫了
      `情節記憶 2 則 / 共 34 則` 並逐字寫「沿用既有 `PaginationControl` 元件」。
      兩處皆因總筆數不存在而不可滿足。依 `refined-mockups:c3` 不回改上游；
      修法（擴充端點回 `{items, total}`）列為 `OPEN-MP15-2`。

  - id: BR33.3
    statement: "語意與程序記憶不分頁，各以 `limit = 200` 一次取得"
    category: constraint
    applies_to: "語意記憶區、程序記憶區"
    trigger: "頁面載入"
    logic: >
      請求 `?kind=semantic&limit=200` 與 `?kind=procedure&limit=200`；
      不帶 `offset`，不渲染分頁控件。
    violation_behaviour: "不帶 `limit` 時伺服器套用預設 50（`clamp_page_size`），第 51 筆起看不到且無分頁可翻"
    source: "interaction-spec.md:509-510「不分頁」；memory_service.py:72-73 的 MAX_LIST_PAGE_SIZE=200"
    note: "200 是伺服器上限，帶更大的值會被 `clamp_page_size` 收斂回 200——故 200 是本區能取得的最大集合"

  # ---- BR34：逐則刪除 ----------------------------------------------------
  - id: BR34.1
    statement: "刪除必須經**就地確認列**，不得使用 `window.confirm`"
    category: constraint
    applies_to: "每一則記憶的刪除控件"
    trigger: "使用者點該則的「刪除」"
    logic: >
      該則原地展開「確定刪除？[刪除] [取消]」；
      確認文案必須說明兩件事：大腦不再依據它回答、此刪除會被記錄。
    violation_behaviour: "`window.confirm` 是瀏覽器 modal，阻塞事件迴圈且無法套用無障礙規格"
    source: "interaction-spec.md「刪除的確認」；mockups.md M6「刪除的確認」"

  - id: BR34.2
    statement: "確認列出現後焦點移到「刪除」，Escape 取消"
    category: constraint
    applies_to: "就地確認列"
    trigger: "確認列展開"
    logic: "展開後焦點程式化移至確認列的「刪除」；按下 Escape 收起確認列並把焦點還給原本的「刪除」入口"
    violation_behaviour: "焦點不移動時鍵盤使用者必須額外 Tab 才找得到確認鍵，且 Escape 無作用時只能用滑鼠取消"
    source: "interaction-spec.md Accessibility 表 Keyboard interaction"

  - id: BR34.3
    statement: "刪除進行中**只有該則**淡化並停用，其餘可用"
    category: constraint
    applies_to: "該則的 `deleting` 態"
    trigger: "確認刪除後、回應回來之前"
    logic: "該則 `aria-disabled` ＋ 視覺淡化；**該區不進入 `loading`**；其餘各則與其他兩區照常可互動"
    violation_behaviour: "整區 loading 與 States 表逐字「該條目淡化並停用，其餘可用」衝突，且會讓使用者誤以為整區在重載"
    source: "interaction-spec.md States 表的 `deleting` 列"

  - id: BR34.4
    statement: "刪除成功後**就地移除**該列，不重抓"
    category: constraint
    applies_to: "刪除成功的後續"
    trigger: "`DELETE` 回 204"
    logic: >
      以回傳新陣列的方式移除該列（不得就地修改既有陣列）；
      播報「已刪除：<摘要>」；不發任何重抓請求。
    violation_behaviour: >
      重抓會讓該區進入 `loading`，與 `BR34.3` 衝突；
      就地修改既有陣列違反 `react-hooks/immutability`（error 級，CI 紅燈）。
    source: "[M3]=A；team.md ## Code Style 的 immutability 條款"

  - id: BR34.5
    statement: "`DELETE` 回 404 視同成功；其他失敗使該則恢復可用並顯示錯誤，不靜默"
    category: policy
    applies_to: "刪除的失敗路徑"
    trigger: "`DELETE` 回非 204"
    logic: >
      IF 404 THEN 與 204 同路徑處理（移除該列並播報）；
      ELSE 該則離開 `deleting` 回到可用，就地顯示錯誤訊息並播報。
    violation_behaviour: "把 404 當失敗會讓「已被 90 天清除或他處刪除」的列永久留在畫面上，且使用者每次重試都看到錯誤"
    source: "memory_facade.py:322-339（`delete` 冪等，已刪除者再刪為 `MemoryNotFound` → 404）；K-14 retry_and_idempotency 逐字「刪除在 K-08 側冪等……故前端重試安全」"
    note: >
      `[D1]`=A 使「非擁有者」也收斂為 404。本規則之下那一條路徑**不可達**，
      因為 `BR35.2` 不為非擁有者的列渲染刪除控件——兩條規則合起來才讓
      「404 視同成功」在語意上成立而非掩蓋授權失敗。

  - id: BR34.6
    statement: "情節記憶刪到該頁變空且非第一頁時，退回前一頁並重抓該區"
    category: calculation
    applies_to: "情節記憶區"
    trigger: "`BR34.4` 的移除之後，該區渲染筆數為 0"
    logic: >
      IF `rendered === 0` 且 `page > 1` THEN `page -= 1` 並重抓該區；
      IF `rendered === 0` 且 `page === 1` THEN 該區進入 `empty` 態。
    violation_behaviour: "不退頁時使用者停在一個空白頁，而「上一頁」是唯一出路卻沒有任何說明"
    source: "[M3]=A 的選項本文逐字「情節記憶若刪到該頁變空且非第一頁，自動退回前一頁」"
    note: "此處的重抓是**頁次改變**造成的，不是 `[M3]`=A 所排除的「刪除後重抓」——兩者觸發條件不同"

  # ---- BR35：擁有者與可見範圍的檢視 --------------------------------------
  - id: BR35.1
    statement: "每一則顯示其擁有者與可見範圍"
    category: constraint
    applies_to: "三區的每一則"
    trigger: "渲染一則記憶"
    logic: >
      擁有者：`owner_user_id === user.id` 時顯示「你」，否則顯示「其他使用者」，
      並一律把數值寫入 `data-owner-user-id`；
      可見範圍：`visibility_scope === 'owner'` 顯示「僅你可見」、
      `'platform'` 顯示「平台可見」。
    violation_behaviour: >
      線框三區的條目形狀（`interaction-spec.md:509-511`）只有內容與日期，
      沒有這兩個欄位——照它實作會讓 `AC4.4.1`（檢視擁有者欄位）與
      `AC4.4.3`（檢視可見範圍）**在本 intent 沒有任何落點**。
    source: "AC4.4.1、AC4.4.3；[M5]=A"
    note: >
      **可見文字不含他人的數值 id**（避免把一個識別字洩漏到畫面上），
      而 `data-owner-user-id` 讓 e2e 得以精確斷言「該欄位是寫入時的已驗證身分」。
      這是對已核可條目形狀的**增補**，記為對齊修正。

  - id: BR35.2
    statement: "**非擁有者**的列不渲染刪除控件"
    category: authorization
    applies_to: "每一則的刪除控件"
    trigger: "渲染一則記憶"
    logic: >
      `canDelete = record.owner_user_id === user.id`；
      IF `canDelete` 為 false THEN 不渲染刪除入口，改顯示「平台可見（他人的記憶）」標記。
    violation_behaviour: >
      渲染一個寫入必然被拒的控件：`DELETE` 對非擁有者回 404
      （`[D1]`=A），而該 404 與「這則已被別人刪掉」**不可分辨**——
      使用者點了只會看到一則記憶沒消失卻沒有任何解釋。
    source: "[M5]=A；U24 兩段式 `canManage` 的同一條理由（MembersListPage.tsx:80-117 的 docstring）"
    note: >
      **此狀態今天就可達**：`memory_service.py:270-283` 的 `_visible_to` 是
      `owner_user_id == me` **OR** `visibility_scope == 'platform'`，而
      `PUT /api/memory/records/{id}/scope` 已上線，`Platform_Admin`／
      `Platform_Owner`（`memory_types.py:100`）得把任何一則放寬為 `platform`。
      已核可線框逐字「**你可以刪掉任何一則**」對這些列為**假**；
      本規則是該句的對齊修正，文案更正見 `functional-spec.md §三之一`。

  - id: BR35.3
    statement: "新建記憶的可見範圍由伺服器決定為最窄，畫面**不提供**可見範圍的設定或放寬控件"
    category: policy
    applies_to: "記憶頁的全部控件"
    trigger: "任何寫入意圖"
    logic: >
      記憶頁的唯一寫入操作是刪除；
      不渲染任何 `visibility_scope` 的輸入、下拉或放寬按鈕。
    violation_behaviour: "放寬是獨立的、需授權的操作（僅兩個平台角色），放進使用者自己的記憶頁等於把一個授權邊界畫成一般設定"
    source: "AC4.4.3；FR4.3b；K-08 authorization_model.scope_widening"
    note: >
      `OQ-12`（哪些角色得放寬、在哪裡放寬）**仍未定案**，故本單元明文不提供該操作，
      而不是沉默地沒做。`MemoryCreateRequest` 連欄位都沒有
      （`memory_router.py` 的 docstring 逐字說明 `visibilityScope` 不是本模型的欄位）。
```

## 三、規則摘要（derived view）

| id | 類別 | 一句話 | 違反的後果 |
|---|---|---|---|
| `BR31.1` | authorization | `/memory` 只要登入，不查 story id | 包 `CapabilityRoute` → 全員 /403 |
| `BR31.2` | constraint | 兩個入口一個判定（INV-3） | 下一個加權限的人只改一處 |
| `BR31.3` | authorization | 前端不自行過濾 | 出現第二份可見範圍實作 |
| `BR32.1` | constraint | 三區固定存在、順序固定 | 區塊位置隨資料變動 |
| `BR32.2` | constraint | 每區獨立抓取與獨立三態 | 一次失敗三區全失敗 |
| `BR32.3` | constraint | `empty` 與 `error` 可區分 | 讀取失敗被讀成記憶被清空 |
| `BR32.4` | validation | 滿頁時顯示「N+ 則」 | 顯示一個錯的精確數 |
| `BR33.1` | calculation | 以 `limit+1` 探測下一頁 | 「下一頁」永遠可按或永遠不可按 |
| `BR33.2` | constraint | 顯示「第 N–M 則」，不用 `PaginationControl` | 餵近似 `total` → 隨翻頁變大的錯數字 |
| `BR33.3` | constraint | 語意／程序以 `limit=200` 一次取得 | 預設 50 之後的記憶看不到也翻不到 |
| `BR34.1` | constraint | 就地確認列，不用 `window.confirm` | 阻塞事件迴圈、無法套無障礙規格 |
| `BR34.2` | constraint | 焦點移到確認鍵，Escape 取消 | 鍵盤使用者只能用滑鼠取消 |
| `BR34.3` | constraint | 只有該則 `deleting`，其餘可用 | 整區 loading 與 States 表衝突 |
| `BR34.4` | constraint | 就地移除，不重抓 | 整區閃動 ＋ 違反 immutability lint |
| `BR34.5` | policy | 404 視同成功，其他失敗不靜默 | 已清除的列永久留在畫面上 |
| `BR34.6` | calculation | 刪空該頁則退回前一頁 | 使用者停在無說明的空白頁 |
| `BR35.1` | constraint | 每則顯示擁有者與可見範圍 | `AC4.4.1`／`AC4.4.3` 無落點 |
| `BR35.2` | authorization | 非擁有者的列不渲染刪除鍵 | 一個永遠 404 的按鈕，且 404 不可分辨 |
| `BR35.3` | policy | 畫面不提供可見範圍放寬 | 把授權邊界畫成一般設定 |

**19 條**（`BR31` 3、`BR32` 4、`BR33` 3、`BR34` 6、`BR35` 3 ＝ 3+4+3+6+3 ＝ 19）。
計數由本表列數實算，不是估計。
