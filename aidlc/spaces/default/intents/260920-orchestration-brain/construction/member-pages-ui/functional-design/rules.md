# Rules — `U24 member-pages-ui`

## 一、本檔存在的理由與範圍界線

> **為什麼一個 `ui` 單元有這份檔。** stage 檔的 `produces_kinds` 把 `rules` 限定在
> `[service, spec, library]`，`ui` 不在其中；但**同一個 stage 的 `traceability`
> sensor 無條件要求 `rules.md` 存在，且每個 `OK` 列的 target 必須指名至少一個
> `BRx.y`**（實測：缺檔時回 `required upstream artifact is missing: .../rules.md`，
> 11 個 `OK` 列全被判 `target must name at least one BRx.y ID`）。兩者直接牴觸，
> 記為 `OPEN-MP24-4`。
>
> **處置**：產出本檔，內容嚴格限定在本單元自己的 UI 層行為規則——
> 沒有一條是從 `U19` 的 `rules.md` 轉抄的。

### 識別字區段：`BR21.x`–`BR28.x`（修訂 1，審查 `R-04`）

**初版用了 `BR1.x`–`BR8.x`，而其中 13 條的 id 已被 `U19` 佔用且語意完全不同。**
實測 `construction/membership-service/functional-design/rules.md` 共 **29** 條，
把**群組 1 到 6 的子號全部用掉**（各群組的子號數依序為 6、3、6、4、6、4）。
為避免追溯 sensor 誤判，本節刻意**不寫出** `U19` 那些識別字的字面形式——
sensor 以 `/\bBR\d+\.\d+\b/g` 掃**整份** `rules.md`，任何出現在本檔的
他單元識別字都會被當成本檔的孤兒規則（初版即因此回報 16 個假孤兒）。

**這不是理論風險**：`U19` 的那些 id **已經寫進出貨的程式**
——`membership_router.py` 的 docstring 引用了群組 1、3、5、6 的**七個**子號
（同樣不在此寫出字面形式，理由見上）。其中群組 6 的第二個子號在那裡指
「必須顯式宣告 409 的 response model」、在本檔初版指「彙總態導向被點選的那個專案」
——**同一個識別字，兩個無關的意思**。下游的
`tcms-test-cases` 要求每個測案追溯到規則、`code-generation` 會在註解引用它們，
而 `U19`／`U24` 同屬一個功能域、同為 `U17` 的測試對象——那個識別字從此會是一個
**靜默解析到錯規則**的引用。

**本檔初版只查證了「內容沒有轉抄」，沒查證「id 有沒有被佔用」**，而
`project.md` 逐字記過同形教訓（會議結論的 `project_admin` 與既有全域角色同名不同義，
「查證成本是幾次 grep，不查的成本是一次回跳」）。

**修訂 1 把群組號整體 +20**，落在 `U19` 用不到的 `BR21`–`BR28` 區段
（sensor 要求 `BRx.y` 的字面形狀，故不能改用 `BR-U24-1.1` 這類前綴）。
對照表：`BR1.x→BR21.x`、`BR2.x→BR22.x`、`BR3.x→BR23.x`、`BR4.x→BR24.x`、
`BR5.x→BR25.x`、`BR6.x→BR26.x`、`BR7.x→BR27.x`、`BR8.x→BR28.x`。

### 修訂 1 新增的三條

`BR22.3`（`canManage` 的取得方式，審查 `R-01`）、
`BR24.3`（變更紀錄的必要欄位，審查 `R-13`）、
`BR26.3`（404 等價於成功，審查 `R-02`）。

下列規則**全部是外部可觀察的 UI 行為**，故 Playwright e2e 可驗——
這是它們有資格被稱為規則、而不只是實作註記的理由。

## 二、規則（machine-readable source of truth）

```yaml source-of-truth
rules:
  - id: BR21.1
    statement: 交棒橫幅的宿主元素必須無條件渲染並帶 role="status"
    category: constraint
    applies_to: ReselectionBannerHost
    trigger: 任何頁面落地
    logic: >
      IF 頁面渲染 THEN 宿主元素存在於初始 DOM 且其 role 屬性等於 "status"，
      不論待通知事件數為 0、抓取尚未完成、或抓取失敗
    violation: aria-live 掛在稍後插入的元素上不會被朗讀，AC12.4.3 靜默失效
    source: "[US:D-11]；[F1]=A 與 [F2]=A 合起來推導"
    observable: >
      查詢 [data-testid="reselection-banner-host"] 必須命中，**且**讀其 role
      屬性必須等於 "status"。（修訂 1／審查 R-03：初版只斷言選擇器命中，
      把 role 屬性整個拿掉仍會綠燈——而 role="status" 正是 §二之一 自述的
      結構前提。三份產出現統一使用這個 data-testid。）
  - id: BR21.2
    statement: 橫幅載入中不渲染骨架
    category: policy
    applies_to: ReselectionBannerHost
    trigger: 抓取進行中
    logic: IF 抓取進行中 THEN 宿主的 textContent 為空
    violation: 骨架會成為一則假通知——橫幅是通知不是內容
    source: functional-spec.md §六之一
    observable: 資料到達前宿主 textContent 為空
  - id: BR21.3
    statement: >
      橫幅抓取失敗不對使用者顯示錯誤；且權限不足屬永久失敗，不重試
    category: policy
    applies_to: ReselectionBannerHost
    trigger: 抓取失敗
    logic: >
      IF 回應為 403（缺 K3 view）THEN 視為永久失敗，本工作階段不再發出該請求；
      ELSE IF 抓取因其他原因失敗 THEN 宿主保持空、不顯示錯誤、下次落地重試。
      兩種情形皆不對使用者顯示任何錯誤訊息
    violation: >
      使用者沒有發起這個抓取，把它的失敗變成訊息會在每個落地頁產生無法處置的雜訊；
      而把永久失敗當成暫時失敗會讓三個角色每次換頁都固定打一個必定 403 的請求
    source: >
      functional-spec.md §六之一；修訂 1／審查 R-11——實測 rbac_seed_data.py:343-345
      的 SRE／Ops_Lead／Platform_Engineer 的 K3 view 為 False，而宿主在 Layout 裡，
      故這三個角色每一次落地都會發出一個必定 403 的請求
    observable: >
      以缺 K3 view 的角色登入後連續換頁，對 /reselections/pending 的請求數不隨頁數成長；
      且任何失敗情形下畫面皆無錯誤文字
  - id: BR22.1
    statement: per-project 控件的出現與否依據伺服器回傳的結論，前端不得推導
    category: authorization
    applies_to: MemberListPage, MemberRow, MemberDetailPage
    trigger: 渲染任何管理者專屬控件
    logic: >
      IF 渲染 [邀請成員] / [>] / 角色下拉 / [移出專案]
      THEN 依據 BR22.3 取得的 canManage，不得由前端持有的全域角色推導
    violation: 違反不變量 I-5；前端的猜測與伺服器判定會不一致
    source: "K-16 的 residual_gap；不變量 I-5"
    observable: >
      以**本專案的一般成員**（非管理者）身分開啟成員頁，四個控件皆不存在；
      以**本專案的管理者**身分開啟同一頁，四個控件皆存在。
      （修訂 1／審查 R-01：初版的 observable 是「伺服器回 403 時四個控件皆不可用」，
      而「是成員但非管理者」拿到的是 **200**，故該斷言對 [D9]=A 這個情境永不觸發。）
  - id: BR22.2
    statement: 成員清單列上不得有任何可直接改角色的控件
    category: constraint
    applies_to: MemberRow
    trigger: 渲染清單列
    logic: IF 渲染清單列 THEN 該列不含任何 select 或角色編輯入口
    violation: 角色只在成員詳情頁變更（[M2]=C）
    source: "AC12.2.3、[M2]=C"
    observable: 清單頁查詢角色 select 應為 0 命中
  - id: BR22.3
    statement: >
      canManage 以自身 user_id 在 list_members 的結果中查出自己的 role 取得，
      不另外呼叫任何端點、也不由全域角色推導
    category: calculation
    applies_to: MemberListPage, MemberDetailPage
    trigger: list_members 回應到達
    logic: >
      IF 回應到達 THEN canManage := (結果中 user_id 等於自身者的 role == "project_admin")；
      IF 結果中找不到自身 THEN canManage := false
    violation: >
      初版把 canManage 列為 props 並寫「來源：伺服器回應」，但**沒有任何端點提供它**
      ——MemberView 只有 user_id／display_name／role／joined_at，而 K-16 的
      resolve_project_role 的 consumed_by 是 [U20, U13, U21]、不含 U24 且無 HTTP 端點。
      照初版字面實作的人做不出來
    source: >
      修訂 1／審查 R-01。本規則採的是審查指出的那條合法解：讀的是**伺服器給的
      role 結論**，不是拿全域角色自己算，故不違反 I-5
    observable: >
      攔截 list_members 的回應並把自身那一列的 role 由 project_admin 改為 member，
      四個控件必須全部消失——這使「前端改用全域角色推導」成為可觸發的紅燈
    note: >
      「找不到自身即 false」這一支是刻意的：list_members 對非成員回 403（U19 的「非成員即拒」規則，見 membership_router.py:169 的 docstring），
      故 200 的結果裡理應有自己；若沒有，那是一個不該默默當成管理者的異常
  - id: BR23.1
    statement: >
      邀請被拒時對話框停留在開啟態且清單不新增任何列；
      只有 detail 為字串的 422 走拒絕態
    category: validation
    applies_to: InviteMemberDialog, MemberListPage
    trigger: 邀請端點回 422
    logic: >
      IF 回應為 422 AND detail 為字串
      THEN 對話框保持 open 並顯示該字串，AND 成員清單的列數不變；
      ELSE IF 回應為 422 AND detail 不是字串（pydantic 的驗證錯誤為物件陣列）
      THEN 走一般錯誤路徑，不把陣列當文案顯示
    violation: >
      關閉對話框會讓使用者以為動作完成；新增列會留下半套狀態；
      把物件陣列渲染成文字會顯示一串無意義的內容
    source: >
      AC12.5.1、AC12.5.3、FR12.6a；修訂 1／審查 R-12——membership_router.py:192-206
      的 422 描述逐字含「受邀者缺少對應的全域功能權限……**或角色不在封閉列舉內**」，
      後者的 detail 是物件陣列而非字串
    observable: >
      以缺全域權限的受邀者送出 → 對話框仍可見、顯示伺服器字串、清單列數不變；
      以列舉外的角色值送出 → 畫面不出現 "[object Object]" 或 JSON 片段
  - id: BR23.2
    statement: 邀請成功時以回應就地新增一列
    category: calculation
    applies_to: MemberListPage
    trigger: 邀請端點回 201
    logic: IF 回應為 201 THEN 以回傳的 MemberView 就地加入清單，不整份重抓
    violation: 成功邀請是一級行為；清單必然多一列
    source: "AC12.6.1、[F4]=A"
    observable: 201 後清單列數 +1 且新列為受邀者
  - id: BR24.1
    statement: 改角色成功時就地更新清單與詳情兩處
    category: calculation
    applies_to: MemberDetailPage, MemberListPage
    trigger: 角色變更端點回 200
    logic: >
      IF 回應為 200 THEN 以回傳的 MemberView 就地替換該成員於清單與詳情，
      不整份重抓
    violation: 整份重抓會每次操作閃一次整頁載入，字面通過 AC 但打斷工作流
    source: "AC12.2.1、[F4]=A、application-design:c15"
    observable: 200 後清單顯示新角色，且無整頁載入態出現
  - id: BR24.2
    statement: >
      改角色被守門拒絕時角色下拉還原為原值，並列出守門帶回的每一個專案名稱
    category: validation
    applies_to: MemberRoleSelect, MemberDetailPage
    trigger: 角色變更端點回 409
    logic: >
      IF 回應為 409 THEN 下拉還原為變更前的值
      AND 渲染 LastAdminGuardReport 帶回的**每一個**專案名稱
    violation: >
      留著被拒絕的值會讓畫面顯示一個伺服器拒絕過的狀態，且重新載入會無聲跳回；
      而守門理由若沒被渲染或渲染錯了，不會有任何東西變紅
    source: >
      functional-spec.md §六之三；修訂 1／審查 R-14——K-16 刻意讓 409 的回應本體
      就是 LastAdminGuardReport（含每個專案的 project_id 與 name），而本單元承載的
      五則故事裡沒有一條 AC 約束它的呈現
    observable: >
      409 後下拉的值等於操作前的值，**且** [data-testid="guard-report-projects"]
      內的列數等於回應中 projects 陣列的長度
  - id: BR24.3
    statement: 變更紀錄每一列必須同時呈現誰、何時、原值、新值四項
    category: constraint
    applies_to: MemberChangeLog
    trigger: 渲染變更紀錄
    logic: >
      IF 渲染變更紀錄的任一列
      THEN 該列同時含操作者、時間、變更前角色、變更後角色四項，缺一即不符
    violation: >
      AC12.2.2 的 Then 逐字要求「誰在何時把角色由什麼改為什麼」。
      初版把 AC12.2.2 的 target 掛在 BR22.1（控件可見性）上，那條規則沒有一個字
      約束變更紀錄的欄位，於是這條 AC 在本站沒有可機械失敗的落點
    source: "AC12.2.2；修訂 1／審查 R-13"
    observable: >
      改一次角色後，[data-testid="member-change-log"] 的最新一列同時含
      操作者名稱、時間、原角色、新角色——刪掉其中任一項即紅燈
  - id: BR25.1
    statement: 移出成員需二次確認且確認對話框的預設焦點在取消
    category: policy
    applies_to: RemoveMemberButton
    trigger: 點擊 [移出專案]
    logic: IF 點擊移出 THEN 先開啟確認對話框，預設焦點為取消
    violation: 破壞性動作無確認
    source: 線框 §25 的既有規定
    observable: 點擊後出現確認對話框，且焦點在取消鈕
  - id: BR25.2
    statement: 移出成功時就地移除該列
    category: calculation
    applies_to: MemberListPage
    trigger: 移出端點回 204
    logic: IF 回應為 204 THEN 導回清單並以 filter 就地移除該列
    violation: 成功移出是一級行為；清單必然少一列
    source: >
      AC12.6.2、[F4]=A。既有先例為 AdminPage.tsx:200 的 filter，但**只取其中一行**，
      理由見 note（修訂 1／審查 R-15）
    observable: 204 後清單列數 −1 且該成員不在清單上
    note: >
      AdminPage.tsx 的該先例共三行：:200 的 filter、:201 的 setTotal 遞減、
      :203 的 resyncCurrentPageInBackground。後兩行存在的理由寫在 :197-198 的註解，
      逐字「不重抓的話，下一頁會靜默略過一個帳號」——那是**分頁**的補償。
      本單元不適用：實測 list_members（membership_router.py:164-178）
      **沒有任何 page／limit／offset 參數**，成員清單一次回傳全部，故無 offset 位移可補
  - id: BR26.1
    statement: 橫幅已讀狀態以事件為鍵、寫在伺服器，不得使用瀏覽器儲存
    category: constraint
    applies_to: ReselectionBanner
    trigger: 按下「知道了」
    logic: >
      IF 按下「知道了」THEN 對每一筆事件各呼叫一次 acknowledge 端點，
      AND 不寫入 localStorage / sessionStorage / IndexedDB
    violation: >
      做成 per-user 布林值會讓同一人第二次被改選時看不到橫幅；
      放瀏覽器儲存則換裝置後橫幅會再出現
    source: "AC12.4.4、FR12.4c-i、[D10]=A"
    observable: 換瀏覽器重新登入後橫幅不再出現
  - id: BR26.2
    statement: 彙總態的「查看成員」導向被點選的那一個專案
    category: constraint
    applies_to: ReselectionProjectList
    trigger: 彙總態（事件數 ≥ 2）下點擊某專案
    logic: >
      IF 事件數 ≥ 2 AND 使用者點選其中一個專案
      THEN 導向該專案的成員清單，不得導向任意一個或第一個
    violation: 導錯專案會讓通知的目的落空
    source: "[D10]=A、functional-spec.md §五 W6 第 7 步"
    observable: 展開後點第 N 個專案，路由的 projectId 等於第 N 個
  - id: BR26.3
    statement: >
      acknowledge 的 404 等價於成功；已成功的事件必須從本機狀態移除，
      只有真正未成功的留下
    category: policy
    applies_to: ReselectionBanner
    trigger: acknowledge 端點的逐筆回應
    logic: >
      IF 回應為 204 OR 404 THEN 視為該事件已確認，從本機 events 移除；
      ELSE 保留該事件於本機 events。
      全部移除完畢 → host-empty；仍有留存 → 回到 shown-* 並顯示錯誤
    violation: >
      acknowledge **不冪等**：membership_router.py:328-358 逐字宣告
      404 為「查不到該事件、它不屬於你，或它已被確認」，docstring 逐字
      「重按一次「知道了」不是伺服器錯誤，但也不該回 204 說『改到了』」。
      初版規定「任一失敗 → shown-* 並顯示錯誤」且沒有移除已成功項的步驟，
      於是 N 筆中第 2 筆失敗後再按一次，第 1 筆回 404 → 又是「任一失敗」
      → **橫幅永遠清不掉**，而伺服器上那 N−1 筆已是已讀，本機與伺服器永久分歧。
      這正是 AC12.5.3 所拒絕的半套狀態
    source: "修訂 1／審查 R-02"
    observable: >
      以三筆事件、令第二筆回 500 → 橫幅剩一筆（第一筆因 204 移除、第三筆因成功移除）；
      再按一次「知道了」→ 橫幅清空（而非因第一筆的 404 而永遠留著）
  - id: BR27.1
    statement: 載入態與錯誤態一律經 live region 播報，不得使用四秒 toast
    category: constraint
    applies_to: MemberListPage, MemberDetailPage
    trigger: 進入載入態或錯誤態
    logic: >
      IF 進入載入態或錯誤態 THEN 文字寫入 U23 提供的 live region 元件，
      AND 不得沿用 AdminPage.tsx:104 的 4 秒 toast（它沒有 role / aria-live）
    violation: 螢幕閱讀器使用者收不到狀態變化
    source: "[US:D-08]、[F3]=A、unit-of-work.md 的 U23／U24 共同約束"
    observable: 載入與錯誤時存在帶 role 的 live region 且其內容非空
  - id: BR27.2
    statement: 前端不驗受邀者是否具備全域功能權限
    category: validation
    applies_to: InviteMemberDialog
    trigger: 送出邀請
    logic: >
      IF 送出邀請 THEN 不在前端判定受邀者的全域功能權限，一律交由伺服器回 422
    violation: >
      前端先猜一次會產生「畫面說不行但伺服器說可以」或反之的不一致，
      兩者都比多一次請求糟
    source: "FR12.6a、frontend-components.md §六"
    observable: 選任何受邀者時送出鈕都不因權限而停用
  - id: BR28.1
    statement: 任何 console 紀錄不得含使用者文字或識別字
    category: constraint
    applies_to: 本單元全部元件
    trigger: 寫出任何 console 紀錄
    logic: >
      IF 寫出 console 紀錄 THEN 只含例外型別名稱與端點標識，
      不含使用者輸入、顯示名稱、或專案名稱
    violation: 本 repo 為 public、Actions log 公開可讀；一次意外輸出即等同公開發布
    source: "ADR-0006 audit logging 面、project.md 的機敏資料禁令"
    observable: >
      以 page.on('console') 擷取輸出，觸發各錯誤路徑後不含測試資料的任何字串
```

## 三、規則摘要（人類可讀，衍生自 §二）

| ID | 類別 | 一句話 | 可觀察形式 |
|---|---|---|---|
| `BR21.1` | constraint | 橫幅宿主無條件渲染**且** `role="status"` | 選擇器命中 **＋** `role` 屬性等於 `status` |
| `BR21.2` | policy | 載入中不渲染骨架 | 資料到達前 `textContent` 為空 |
| `BR21.3` | policy | 抓取失敗不對使用者說話；403 屬永久失敗不重試 | 缺 `K3 view` 者換頁時請求數不成長 |
| `BR22.1` | authorization | per-project 控件依伺服器結論，前端不推導 | 一般成員看不到四個控件、管理者看得到 |
| `BR22.2` | constraint | 清單列沒有改角色的控件 | 清單頁角色 select 0 命中 |
| `BR22.3` | calculation | `canManage` 由 `list_members` 結果中自己那列的 `role` 取得 | 竄改自身那列的 `role` → 四個控件消失 |
| `BR23.1` | validation | 邀請被拒：對話框不關、清單不加列；僅字串 `detail` 走拒絕態 | 422 後列數不變；畫面不出現 JSON 片段 |
| `BR23.2` | calculation | 邀請成功：就地加一列 | 201 後列數 +1 |
| `BR24.1` | calculation | 改角色成功：就地更新兩處 | 200 後新角色可見且無整頁載入 |
| `BR24.2` | validation | 409：下拉還原原值**並**列出帶回的每個專案 | 下拉等於原值 ＋ 專案列數等於回應陣列長度 |
| `BR24.3` | constraint | 變更紀錄每列含誰／何時／原值／新值四項 | 最新一列四項俱在，缺一即紅燈 |
| `BR25.1` | policy | 移出需二次確認，焦點預設取消 | 點擊後出現確認框 |
| `BR25.2` | calculation | 移出成功：就地移除該列（清單不分頁，故無 offset 補償） | 204 後列數 −1 |
| `BR26.1` | constraint | 已讀以事件為鍵、寫伺服器、不用瀏覽器儲存 | 換裝置後不再出現 |
| `BR26.2` | constraint | 彙總態導向被點選的那個專案 | 第 N 個的 `projectId` 相符 |
| `BR26.3` | policy | 404 等價於成功；已成功者從本機移除 | 部分失敗後再按一次可清空 |
| `BR27.1` | constraint | 載入／錯誤經 live region，不用四秒 toast | 存在帶 `role` 的 live region |
| `BR27.2` | validation | 前端不驗全域功能權限 | 送出鈕不因權限停用 |
| `BR28.1` | constraint | console 不含使用者文字或識別字 | 錯誤路徑的輸出不含測試字串 |

**19 條（初版 16 ＋ 修訂 1 新增 3），全部外部可觀察。** 這是它們有資格進
`rules.md` 的判準——一條無法從外部觀察的「規則」在 UI 層只是實作註記，
而 UI 單元的唯一自動化驗證層是 Playwright e2e（`team.md` 既成事實：
前端無 unit／component 測試框架）。
