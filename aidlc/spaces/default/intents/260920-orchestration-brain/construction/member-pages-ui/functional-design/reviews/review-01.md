## Review

**Verdict:** NOT-READY

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-10T04:40:20Z
**Iteration:** 1
**Unit:** `U24 member-pages-ui`（`ui`）
**Review artifact:** `functional-spec.md`（連同 `rules.md`／`frontend-components.md`／`traceability.json`／`functional-design-questions.md` 一併審）

### 執行方式與限制

依派工限制，本輪**未執行任何 Python／npm／playwright／tsc**，亦未寫入除本檔以外的任何檔案。
所有引用一律開檔核對，並**分開驗事實與驗定位**。實際查證過的檔案：
`backend/services/membership_router.py`、`backend/services/membership_types.py`、
`backend/services/membership_facade.py`、`backend/services/membership_service.py`、
`backend/services/rbac_seed_data.py`、`backend/main.py`、
`frontend/src/components/Layout.tsx`、`frontend/src/components/RouteGuard.tsx`、
`frontend/src/pages/AdminPage.tsx`、
`inception/contract-design/contract-summary.md`（`K-16` 全段）、
`inception/user-stories/stories.md:753-935`、
`inception/units-generation/unit-of-work-story-map.md:170-235`，
以及依派工的 spot-check carve-out 各開一次的兩個兄弟單元檔
（`construction/membership-service/functional-design/rules.md` 的 id 清單、
`construction/project-pages-ui/functional-design/traceability.json` 的存在性）。

轉述的 sensor 結果視為資料。`linter`／`type-check` 的 `no-eslint-config`／`no-tsconfig-found`
確屬 tool-unavailable 的 fall-through，不計為通過；`traceability` 的 `pass: true` 只保證
每列有可解析的 target，**不保證該 target 與該 AC 的語意相符**——R-13 即落在這個縫裡。

### 先說結論：哪些主張經查證成立

把這些列出來，是為了讓下方發現的範圍清楚，而不是背書。

- **§二之一 的 `role="status"` 無障礙主張正確**（派工要我用力打的第 2 點）。
  `role="status"` 的隱含 `aria-live` 為 `polite`（並隱含 `aria-atomic="true"`）；
  「live region 必須在內容變動之前就存在於 DOM，否則不會被朗讀」是標準行為。
  故「宿主無條件渲染」這條硬約束**站得住**，`BR1.1` 的 statement 與 `AC12.4.3` 的
  覆蓋判定不需要重做。但它的**可觀察形式**有問題，見 R-03；而這個結構另外帶進一個
  未被討論的後果，見 R-06。
- **`[F2]`=A 不需要新端點，成立。** 端點 5／6 實存於 `membership_router.py:309`／`:328`，
  `list_pending_reselections` 的 docstring 逐字確認同時過濾 `cause = 'auto_reselection'`
  與 `acknowledged_at IS NULL`，`acknowledge` 以**事件**為鍵。§四 其餘五列的路徑、
  方法、`response_model`、201／204 逐一與 router 相符。
- **`Layout.tsx:16` 逐字為 `<div data-slot="cost-banner" />`**，且確實在 `{children}`
  之上、滾動容器之內。`Layout.tsx:9`、`RouteGuard.tsx:15`／`:35`、
  `AdminPage.tsx:104`／`:153`／`:179`／`:200` 七處引用**定位與事實皆正確**，
  `:200` 確為 `filter`、`:104` 確為 4000ms 的 `setTimeout`。`main.py:94` 的
  `prefix="/api/membership"` 正確。
- **§零 說 `K-16` 有四個方法對 `U24` 以 http 提供，正確**（`K-16` 的 `public_interface`
  共七個方法，其中 `consumed_by` 含 `U24` 的恰為 `list_members`／`invite_member`／
  `remove_member`／`change_role` 四個）。
- **六個 `N/A` 中有四個判定正確**：`AC12.2.4`／`AC12.4.1`／`AC12.4.2`／`AC12.5.2`
  的 Then 都斷言伺服器側判定，`U19` 是對的落點。另兩個有問題，見 R-05。
- **`BR8.1` 在 Playwright 可斷言**（派工的獨立檢查）：`page.on('console')` 可擷取
  console 輸出，「觸發各錯誤路徑後輸出不含測試資料字串」是可執行的斷言。
  「16 條全部外部可觀察」這個宣稱本身我未找到反例。
- **`OPEN-MP24-1` 的落點判定正確**（派工要我打的第 4 點）：`U19` 的
  `code-generation` 確已完成（`membership_router.py`／`membership_facade.py`／
  `membership_service.py` 皆已在磁碟上且含完整 docstring 契約），而
  `aidlc-state.md:227`／`:290` 顯示 `Active Unit: member-pages-ui`、
  `Current Stage: functional-design`，故 `U24` 的 `code-generation`（3.5）確在游標之後。
  指派有效。該列的**理由**另有一處事實錯誤，見 R-07。
- **`[F1]`=A 把橫幅放進 `Layout` 不會重現 `[D-17]` 的失敗**：我原本懷疑
  「只有 `C1 view` 的成員」會因缺 `K3 view` 而在端點 5 吃 403，使 `AC12.4.3` 仍然
  靜默失效。查證後**不成立**：`membership_service.py:71-72` 的
  `REQUIRED_INVITEE_STORY_ID = "K3"`／`REQUIRED_INVITEE_ACTION = "view"` 使缺
  `K3 view` 的人根本不可能被邀請成為成員，因此也不可能被自動改選。
  `traceability.json` 對 `AC12.4.3` 的「這同時關掉 `[D-17]`」宣稱成立。
  但同一組事實帶出另一個較輕的問題，見 R-11。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `functional-spec.md` §三（第 62-74 行的可見性表與其後段）＋ `frontend-components.md` §四（`MemberTable`／`MemberRow` 的 `canManage` props）＋ `rules.md` `BR2.1` | **`canManage` 是一個有讀者、無提供者的契約端，而它決定四個控件的存亡。** `frontend-components.md` §四 把 `canManage` 列為 `MemberTable`／`MemberRow` 的 props 並寫「來源：伺服器回應」，`BR2.1` 以它為渲染依據。但**沒有任何端點提供它**：`list_members` 的 `response_model` 是 `List[MemberView]`，而 `MemberView`（`membership_types.py:80-96`）只有 `user_id`／`display_name`／`role`／`joined_at`；`K-16` 的 `resolve_project_role` 雖被標為「per-project 判定的唯一入口」，其 `consumed_by` 是 `[U20, U13, U21]`，**不含 `U24`**，且無對應 HTTP 端點。§三 給的兩個依據都與查證結果矛盾：①「`list_members` 的結果是否包含管理者才拿得到的形狀」——回應形狀對所有呼叫者**完全相同**，不存在管理者專屬形狀；②「或端點直接回 403」——`list_members` 的 403 依 router 的 `BR1.6`（`:169` docstring「非成員即拒」）代表**完全不是成員**，而四個變更端點的 403 只在**動作送出後**才出現，無法用來決定要不要渲染按鈕。連帶兩個後果：(a) **`[D9]`=A（一般成員唯讀清單）在本站零可驗證機制**——W2 描述了它，`BR2.1` 名義上覆蓋它，但 `BR2.1` 的 observable「伺服器回 403 時這四個控件皆不可用」對「是本專案成員但非管理者」這個情境**永不觸發**（他拿到的是 200）；(b) 自檢 2 報告「查出一處缺口」並列「另三處完整」，而這是第二處、且是同一類的寫入端缺口。附帶：存在一條未被寫下的合法解（在 `list_members` 的結果中以自己的 `user_id` 查出自己的 `role`，那是讀伺服器結論、不違反 `I-5`），但規格從未指出它，照 §三 字面實作的人做不出來 | 把 `canManage` 的取得方式寫成可執行的規格：或明訂「以自身 `user_id` 在 `list_members` 結果中查出 `role`」並補一條鎖住它的規則與 observable，或比照 `OPEN-MP24-1` 標為跨單元契約缺口並指派落點（`MemberView` 增欄／新增 per-project 角色端點）。同時改寫 `BR2.1` 的 observable，使「成員但非管理者」這個情境可被 e2e 斷言，否則 `[D9]`=A 無任何機制 | New |
| R-02 | Critical | `functional-spec.md` §五 W6 第 6 步（第 162-164 行）＋ §六之一 的 `acknowledging` 列 ＋ §四 第 6 列 | **「知道了」的逐事件呼叫在部分失敗時進入一個設計上無法離開的狀態，而這是因為 acknowledge 端點不冪等。** `membership_router.py:328-358` 逐字宣告 `responses={404: {"description": "查不到該事件、它不屬於你，或它已被確認"}}`，docstring 逐字「已確認或不屬於你的事件回 **404**——重按一次「知道了」不是伺服器錯誤，但也不該回 204 說『改到了』」。把它代入設計：N 筆事件、第 1 筆 204、第 2 筆失敗 → §六之一 規定「任一失敗 → `shown-*` 並顯示錯誤」，而本機 `events` 仍是 N 筆（規格沒有任何移除已成功項的步驟）→ 使用者再按一次，第 1 筆這次回 **404** → 又是「任一失敗」→ **橫幅永遠清不掉**。已成功的那 N−1 筆在伺服器上已是已讀，故重新載入後它們也不再回來，使本機狀態與伺服器永久分歧。這正是 `AC12.5.3` 所拒絕的半套狀態，而 §六之二 為邀請流程特別處理了它、W6 沒有。附帶：§四 第 6 列的「回應」欄只寫 **204**，`frontend-components.md` §七 列了 401／403／409 而**沒有 404**——這個已在 router 顯式宣告的狀態碼在本站四份產出中完全缺席 | 明訂部分成功的處置：逐筆記錄結果、把已 204 的事件從本機 `events` 移除、並把 `404` 視為**等價於成功**（它的語意就是「已經是已讀」）而非失敗；只有真正未確認成功的事件才留在 `shown-*`。同時把 404 補進 §四 第 6 列與 `frontend-components.md` §七，並在 `BR6.1` 的 logic 寫出這個分支 | New |
| R-03 | Major | `rules.md` §二 `BR1.1` 的 `observable`（第 35 行）＋ §三 摘要表 `BR1.1` 列 ＋ `functional-spec.md` §二之一（第 57-58 行）＋ `frontend-components.md` §九 | **本單元最重要的那條規則，它的 observable 驗不到它自己的 statement。** `BR1.1` 的 statement 是「宿主必須無條件渲染**並帶 `role="status"`**」，而它的 observable 逐字是「落地後查詢 `[data-slot="reselection-banner"]` 必須命中」——把 `role` 屬性整個拿掉，這條 observable 依然綠燈。而 §二之一 自己把斷言寫成「查詢 `[role="status"]` 必須命中」。同一個斷言在三份產出用三個不同的選擇器表達：`functional-spec.md` 用 `[role="status"]`、`rules.md` 用 `[data-slot="reselection-banner"]`、`frontend-components.md` §九 的 `data-testid` 清單登記 `reselection-banner-host`（§三 的程式片段又只寫 `data-slot`，沒有 `data-testid`）。`role="status"` 是整個 `AC12.4.3` 成立的結構前提（§二之一 自述如此），而 e2e 要照 `rules.md` 的 observable 寫就抓不到它的遺漏 | 把 `BR1.1` 的 observable 改成同時斷言宿主存在**與** `role="status"`（例如查詢 `[data-testid="reselection-banner-host"]` 並讀其 `role` 屬性），並讓三份產出對這個元素使用同一組選擇器 | New |
| R-04 | Major | `rules.md` §二 全部 16 條的 `id` 欄 | **`BR*` 的識別字空間與 `U19` 直接碰撞：16 條裡有 13 條的 id 已被 `U19` 用掉，而且指的是完全不同的事。** 實測 `construction/membership-service/functional-design/rules.md` 共 **29** 條，id 為 `BR1.1`–`BR1.6`／`BR2.1`–`BR2.3`／`BR3.1`–`BR3.6`／`BR4.1`–`BR4.4`／`BR5.1`–`BR5.6`／`BR6.1`–`BR6.4`。對照本檔：`U19` 的 `BR1.1` 是「受保護操作的唯一入口是 `MembershipFacade`」、本檔的 `BR1.1` 是橫幅宿主；`U19` 的 `BR2.1` 是「每個專案至少一位 `project_admin`」、本檔的 `BR2.1` 是前端控件可見性；`U19` 的 `BR4.1` 是「`selectSuccessor` 是純函式」、本檔的 `BR4.1` 是就地更新。只有 `BR7.1`／`BR7.2`／`BR8.1` 未被佔用。**這不是理論風險**：`U19` 的那些 id **已經寫進出貨的程式**——`membership_router.py` 的 docstring 引用 `BR1.1`／`BR1.2`／`BR1.6`／`BR3.3`／`BR5.5`／`BR5.6`／`BR6.2`，而 `BR6.2` 在那裡指「必須顯式宣告 409 的 response model」、在本檔指「彙總態導向被點選的那個專案」。下游的 `tcms-test-cases` 要求每個測案追溯到規則、`code-generation` 會在註解引用它們，而 `U19`／`U24` 同屬一個功能域、同為 `U17` 的測試對象——`BR6.2` 從此是一個會靜默解析錯的引用。`project.md` 逐字記過同形教訓（會議結論的 `project_admin` 與既有全域角色同名不同義，「查證成本是幾次 grep，不查的成本是一次回跳」），而本檔 §一 只查證了「內容沒有轉抄」，沒查證「id 有沒有被佔用」 | 為本單元的規則改用不衝突的識別字前綴（例如 `BR-U24-1.1`，或續編到 `BR7.x`／`BR8.x` 以上的未占用區段），並同步 `rules.md` §二／§三、`functional-spec.md` 的引用與 `traceability.json` 的 `target`／`reverse` 兩段。若因 sensor 要求 `BRx.y` 字面形狀而不能改前綴，則在本檔與 `traceability.json` 的每一處引用加上單元限定並記為交接事項 | New |
| R-05 | Major | `traceability.json` 的 `AC12.1.3` 與 `AC12.6.3` 兩列（`target` 欄） | **兩個 `N/A` 把 AC 推給一個上游從未指派該故事的單元，等於沒有人接。** 兩列的 `target` 是 `U23 project-pages-ui`，而已核可的 `unit-of-work-story-map.md:174-179` 把 `US12.1` 映射到 `U19`／`U24`／`U18`、把 `US12.6` 映射到 `U19`／`U24`——**兩列都沒有 `U23`**；`U23` 的映射只有 `US11.1`／`US11.2`／`US11.3`（同檔的「七個新單元的承載則數」表逐字如此）。所以 `U23` 的 `functional-design` 在跑它自己的站時，會依 story map 列舉 `US11.x`，不會看到 `AC12.1.3`／`AC12.6.3`（實測 `construction/project-pages-ui/functional-design/traceability.json` 尚不存在，故目前無人承接已成事實而非推測）。這正是 `project.md` 記過三次的死指派形狀（「填假目標會讓交接表看起來完整而實際上是死指派，比空著更糟」）。兩條 AC 的 Then 確實落在專案清單頁（判定本身我同意），問題在於**沒有任何已核可文件讓那個單元知道它要承接**。附帶：`AC12.1.3` 是 `user-stories` 為補足 3–6 條指引而特意新增的「非成員看不到」那一面，`AC12.6.3` 是兩層串聯的 allow 側——兩者都不是可犧牲的湊數斷言 | 比照 `OPEN-MP24-1` 的形狀把它記成一個開放項：寫明「`US12.1`／`US12.6` 整則由 story map 指給 `U24`，但這兩條 AC 的畫面在 `U23`，而 story map 未把 `U23` 列為這兩則的實作單元」，並指派一個**在游標之後**的 `ALWAYS` 落點（`U23` 的 `functional-design` 為 `CONDITIONAL`，須附轉移目標至 `code-generation`）確認承接 | New |
| R-06 | Major | `frontend-components.md` §二 元件樹（第 33-37 行）＋ §三 的程式片段 ＋ `functional-spec.md` §六之一 的 `shown-aggregate` 列 | **把可互動內容放進 `role="status"` 容器內，會讓每次展開／收合重新朗讀整個橫幅。** 元件樹讓 `<ReselectionBanner>`（含兩個動作鈕與可展開的 `<ReselectionProjectList>`）整個**巢在**帶 `role="status"` 的宿主裡；§三 的片段逐字就是這個形狀。而 `role="status"` 隱含 `aria-atomic="true"`：區域內任何變動都會使**整個區域**被重新播報。`[D10]`=A 的彙總態下，使用者每按一次展開／收合，螢幕閱讀器就把「你成了 N 個專案的管理者」加上 N 個專案名整串重讀一次。§六之一 寫「展開／收合不改變狀態」——狀態機層面對，但 DOM 層面它改變了 live region 的內容，而規格沒有處理這個後果。這不是假警報：本單元的無障礙論證（`[US:D-11]`／`[US:D-08]`）正是以螢幕閱讀器使用者為對象，而 `U17` 的 axe 掃描不會回報「live region 內含互動內容」這一類問題，故沒有任何機械閘門會抓到它 | 把 live region 與可互動內容分離：宿主只放要被朗讀的文字（或在展開／收合時以 `aria-live="off"`／移出 atomic 區域抑制重播），並在 §三 的「三條不可違反的規定」補上這一條與其可觀察形式 | New |
| R-07 | Major | `functional-spec.md` §八 `OPEN-MP24-1` 列（第 217 行） | **「`ReselectionOut` 只有 `id` 與 `project_id`」是錯的，而這句話就寫在要交給 `code-generation` 的那一列裡。** 實測 `membership_router.py:81-102`，`ReselectionOut` 有**九個**欄位：`id`、`project_id`、`cause`、`promoted_user_id`、`previous_owner_user_id`、`previous_role`、`new_role`、`occurred_at`、`acknowledged_at`。缺口本身（**沒有專案名稱**）成立，引用的 docstring 原文也成立，但照這句話去實作的人會以為手上只有兩個欄位——而實際上事件已帶著足以組出完整文案的資訊，缺的只有名稱這一項。這與本檔自檢 3 宣稱「`ReselectionOut` 的欄位集合引用 `:81-95`」互相矛盾：若真的逐一核對過欄位集合，就不會寫成兩個欄位 | 把該列改寫為「`ReselectionOut` 的九個欄位中**不含專案名稱**」並列出欄位集合，使 `code-generation` 的實作者知道哪些資訊已經在手上 | New |
| R-08 | Minor | `functional-spec.md` §九 第 6 項（第 231 行）＋ §九之一（第 234-238 行） | **自檢 6 的六個數字裡有一個是錯的，而它宣稱「全部實算」。** §八 的開放項表實際有**四**列（`OPEN-MP24-1`／`-2`／`-4`／`-3`），§九 第 6 項寫「開放項 **3** 項」——`OPEN-MP24-4` 是本站後補的那一個，計數沒有跟著重算。另五個數字（故事 5、AC 17、API 消費點 6、流程 6、狀態機 3）我逐一複算**皆正確**（AC 17 = 3+4+4+3+3，與 `upstream_ids` 的長度相符；W1–W6 六條；§六之一／之二／之三 三個）。另一個問題是 §九之一 只給了 AC 一項的來源，而 §九 第 6 項逐字「全部由 `traceability.json` 與本檔的章節實算，見 §九之一」——那一節並未支持其餘五個數字 | 把「3 項」改為「4 項」，並讓 §九之一 逐一給出六個數字各自的取得方式（或刪掉「見 §九之一」這個指向） | New |
| R-09 | Minor | `functional-spec.md` §八 `OPEN-MP24-1`（`:81-95`）、§九 第 3 項（`membership_types.py:80-94`）、§九之一（`stories.md:758-903`） | **三處引用的行號區間都把它們所宣稱的內容切掉一部分——事實對、定位不對。** ①`ReselectionOut` 的 class 實際橫跨 `membership_router.py:81-102`（`:95` 落在欄位清單中間的 `project_id`，其後還有七個欄位）；②`MemberView` 實際橫跨 `membership_types.py:80-96`，而引用寫 `:80-94`——`:94` 是 `display_name`，被引用的四個欄位裡有兩個（`role`／`joined_at`，在 `:95`／`:96`）落在區間之外；③`stories.md:758-903` 用來支持「AC 17 條」的逐則計數，但 `:903` 是 **`AC12.6.2`**，`AC12.6.3` 在 `:904`——區間排除了它所計入的 17 條之一。三者的結論都不受影響，但照行號去讀的人會讀到不完整的東西，而這正是 `project.md` 記過三次、審查員也曾漏驗的那個形狀 | 把三處區間改為 `:81-102`、`:80-96`、`:758-904` | New |
| R-10 | Minor | `functional-spec.md` §九 第 5 項（第 230 行） | **跨檔傳播自檢只掃了四份交付檔中的兩份。** 第 5 項列舉 `[F1]`–`[F4]` 的落點時，只點到 `functional-spec.md` 的章節與 `frontend-components.md`，完全沒有 `rules.md` 與 `traceability.json`。實測（固定字串逐詞計數）四個標籤在 `rules.md` 的命中數為 `[F1]` 1、`[F2]` 1、`[F3]` 1、`[F4]` 3，在 `traceability.json` 為 1／1／0／1——`rules.md` 的 `BR1.1`／`BR3.2`／`BR4.1`／`BR5.2`／`BR7.1` 的 `source` 欄逐字引用這些定案。而同一份 §九 的第 4 項自己才剛寫下「實際交付**四份**」。這一項之所以要緊：一次完整的傳播掃查正好會比對 `BR1.1` 的 observable 與 §二之一 的斷言，也就是 R-03 | 重跑第 5 項並把 `rules.md`／`traceability.json` 納入檔案集合，逐一列出四個定案在這兩份檔裡的落點 | New |
| R-11 | Minor | `rules.md` `BR1.3` ＋ `functional-spec.md` §四 第 5 列、§六之一 的 `fetch-failed` 列 | **橫幅的背景抓取對三個角色是每次換頁都保證失敗一次，而設計把這種永久性失敗與暫時性網路失敗歸為同一類。** 端點 5／6 掛 `require_story_action("K3", "view")`，而 `rbac_seed_data.py:343-345` 顯示 `SRE`／`Ops_Lead`／`Platform_Engineer` 的 `K3` view 為 **False**。宿主在 `Layout` 裡（`[F1]`=A），故這三個角色的使用者**每一次落地**都會發出一個必定回 403 的請求；`BR1.3` 的處置是「保持空且不顯示錯誤；**下次落地重試**」——於是重試永遠不會成功。行為上無害（`AC12.4.3` 不受影響，理由見上方「結論」一節），但這是一個可零成本避免的固定開銷與 log 噪音：前端已有 `useAuth` 的 `can()`（`RouteGuard.tsx:35` 的 `CapabilityRoute` 正在用它），宿主可在缺 `K3 view` 時直接跳過抓取。另：§四 第 5 列的「回應」欄沒有提到 403 | 在 `BR1.3` 區分「權限不足（403，永久）」與「暫時失敗」，前者不重試；或在 `ReselectionBannerHost` 明訂以 `can('K3','view')` 作為發出請求的前置條件，並把 403 補進 §四 第 5 列 | New |
| R-12 | Minor | `functional-spec.md` §五 W3 第 5 步、§四 第 2 列 ＋ `rules.md` `BR3.1` | **422 在這個端點有兩種語意，而設計只以狀態碼分流。** `membership_router.py:192-206` 的 422 描述逐字為「受邀者缺少對應的全域功能權限（`BR3.2`／`AC12.5.1`），**或角色不在封閉列舉內**」。後者是 FastAPI／pydantic 的驗證錯誤，其 `detail` 是**物件陣列**而非字串；而 `frontend-components.md` §五 的既有形狀是「取 `data.detail` 當錯誤訊息」。W3 第 5 步與 `BR3.1` 把所有 422 都當成「顯示 `U19` 回傳的理由」，於是驗證型 422 會把一個陣列渲染成文字。經設計的 UI 下角色是封閉列舉的 select、受邀者來自選擇器，故可達性低，但不是零（請求可被改寫、列舉值可能漂移） | 在 W3 第 5 步與 `BR3.1` 明訂只有 `detail` 為字串的 422 走拒絕態，形狀不符者走一般錯誤路徑，不把陣列當文案顯示 | New |
| R-13 | Minor | `traceability.json` 的 `AC12.1.1`／`AC12.2.2` 兩列（`target` 欄） | **兩列的 `target` 指向一條與該 AC 的實質內容無關的規則，而 sensor 只驗 target 可解析。** `AC12.2.2` 的 Then 是「變更紀錄顯示**誰在何時把角色由什麼改為什麼**」，`target` 填 `BR2.1`——`BR2.1` 整條只談 per-project 控件的可見性依據，沒有一個字約束變更紀錄要顯示哪些欄位；該列的 note 自己寫「對應規則 `BR2.1`（紀錄的渲染同樣受伺服器回應控制）」，那是為了滿足「target 必須指名至少一個 `BRx.y`」而做的映射。`AC12.1.1`（清單恰一列、即自己、角色為專案管理者）同樣掛 `BR2.1`。結果是：16 條規則裡**沒有一條**約束變更紀錄的必要欄位，而 `<MemberChangeLog />` 的 props 只有 `entries`，`data-testid` 只有一個容器 `member-change-log`——`AC12.2.2` 在本站實際上沒有可機械失敗的落點 | 補一條規則約束變更紀錄每列必須呈現的四項（誰／何時／原值／新值）與其 observable，並把 `AC12.2.2` 的 target 改指它；`AC12.1.1` 同理（它的實質是清單內容而非控件可見性） | New |
| R-14 | Minor | `frontend-components.md` §九 `data-testid` 清單（第 150-156 行）＋ `functional-spec.md` §五 W4 第 5 步、W5 第 5 步 | **W4／W5 的 409 分支要求畫面列出 `LastAdminGuardReport` 帶回的專案，而這個區塊沒有 `data-testid`。** 17 個 testid 裡沒有任何一個對應守門理由或其專案清單。`BR4.2` 的 observable 只斷言「下拉的值等於操作前的值」，不含「列出那些專案」這一半；而守門本身的三條 AC（`AC12.3.1`–`.3`）屬 `US12.3`，**不在本單元承載的五則內**，所以這段呈現在本站既沒有 AC、也沒有可定位的斷言目標。`K-16` 的 409 契約刻意讓回應本體就是 `LastAdminGuardReport`（含每個專案的 `project_id` 與 `name`），這份資訊若沒被渲染或渲染錯了，不會有任何東西變紅 | 為守門理由區塊與其專案清單各補一個 `data-testid`，並把「列出帶回的每一個專案名稱」寫進 `BR4.2` 的 observable | New |
| R-15 | Minor | `frontend-components.md` §一 第二列（第 22 行）＋ `rules.md` `BR5.2` | **引用 `AdminPage.tsx:200` 作為「就地移除」的先例時，只取了那個先例的三分之一。** `:200` 的 `filter` 之後緊接著 `:201` 的 `setTotal((prev) => Math.max(0, prev - 1))` 與 `:203` 的 `resyncCurrentPageInBackground(page)`，而 `:197-198` 的註解逐字說明第三行存在的理由是「不重抓的話，**下一頁會靜默略過一個帳號**」。本檔寫「W5 的『移出後清單少一列』直接對應 `:200` 的 `filter` 先例」，沒有說明被省略的那兩行為什麼不需要——而答案取決於成員清單**是否分頁**，這件事在本站四份產出中從未陳述（`OPEN-MP24-3` 只涵蓋變更紀錄的分頁）。`project.md` 的 `application-design:c15` 逐字要求「為新行為指定『沿用既有機制』之前，必須先寫下該既有機制的副作用是否與新需求的意圖相容」 | 寫明成員清單不分頁（故 `:201`／`:203` 兩行不適用），或若可能分頁則一併承接該先例的補償步驟 | New |

### 三類計數（依缺陷來源）

| 來源 | 件數 | 說明 |
|---|---|---|
| **新引入**（前一輪修正動作造成） | **0** | 本站為 iteration 1，無前一輪修正，故此類必然為 0 |
| **既存漏審**（上游或既有程式已有的事實，本站未反映） | **2** | `R-11`（`rbac_seed_data.py` 的三個 `K3 view: False` 角色）、`R-12`（router 自己宣告的 422 雙語意） |
| **新設計問題**（本站自己的設計或敘述產生） | **13** | `R-01`–`R-10`、`R-13`–`R-15` |

合計 **15** 項：Critical **2**、Major **5**、Minor **8**。

### Summary

兩項 Critical 都是「契約有一端懸空」而非品味問題：`canManage` 有讀者、有規則、有 props 欄位，
卻沒有任何端點提供它，而 §三 給的兩個取得依據經開檔核對皆與 `MemberView`／`K-16` 矛盾——
照規格字面實作的人做不出來，`[D9]`=A 也因此沒有可觸發的斷言；交棒橫幅的「知道了」在部分失敗時
會因 acknowledge 端點**不冪等**（router 逐字宣告已確認者回 404）而永遠清不掉，而那個 404
在本站四份產出中完全沒有出現。五項 Major 中最值得在閘門上決定的是 `R-04`：`rules.md` 的
16 條規則有 13 條沿用了 `U19` 已經寫進出貨程式的識別字而語意不同，這會讓下游的測案追溯與
程式註解靜默解析到錯的規則——派工問「`rules.md` 該不該存在」，我的答案是**該存在、但它的
識別字空間必須先修**。其餘查證結果大多支持本站的判斷：`role="status"` 的無障礙推導正確、
`[F2]`=A 不需新端點正確、七處既有程式引用的定位與事實全對、`OPEN-MP24-1` 的落點判定正確、
`[D-17]` 的失敗路徑確已被上游的受邀者權限門檻關閉。

VERDICT: NOT-READY
