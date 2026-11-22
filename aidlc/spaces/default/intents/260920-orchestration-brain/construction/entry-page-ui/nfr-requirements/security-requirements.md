# Security Requirements — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T02:11:18Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。
> 本站兼任 devsecops／compliance／quality 的視角；以下每一條都附「可二元判定的檢查」與「必須紅燈的突變」。

## 〇、上游依據

| 來源 | 內容 |
|---|---|
| `functional-design/rules.md` | `BR91.1`／`BR91.2`（`K1` 落地判斷）、`BR92.1`（子協定帶 token、網址不帶參數）、`BR92.8`（不碰 token、console 不記內容）、`BR93.4`（記憶體 store、不寫瀏覽器儲存）、`BR97.5`／`BR97.6`（同步只回寫自有圖） |
| `functional-design/functional-spec.md` | §二之一（C-8：`describe_work_target`、`_names_for`）；§九之一（ADR-0006 四面向，本站逐格對照，見 §六） |
| `carried-review-items.md` | **R-01／R-02／R-03 使用者裁決**（2026-10-17T02:06:14Z）；R-04（樁訊框建構器只收原始型別引數） |
| `inception/requirements-analysis/requirements.md` | ADR-0006 四面向表（`:591` 起）：四面向皆適用；FR8.5（token 不進 query string） |
| repo 實測 | `hierarchy_facade.py:238-262`（寫入路徑守門順序與 `project_visible` 必填）、`membership_facade.py:518-532`（`project_visibility`，唯一合法來源）、`test_brain_gateway_limits.py:380-381`（`brain_gateway` 不得 import `services.membership_facade`）、`test_project_visibility_static.py:112`／`:135`／`:162`（`S2`／`S3`／`S4` 靜態鎖）、`brain_gateway.py:130-155`（log 欄位白名單）、`AuthContext.tsx:56`／`:82-93`（logout／login；`/me` 失敗時 user 無 `id`）、`auth-context.ts:29`（`id?: number`） |

**一處與已核可設計檔的字面衝突（如實記載，設計檔不回改）**：`functional-spec.md` §九之一 IAM 列逐字「`U7` 新方法……以擁有者範圍逐層查，他人資料回 null——**不擴大可見範圍**」。
審查 R-01 指出此句只對照擁有者範圍、未對照 `U23` 的成員可見性守門；使用者 2026-10-17T02:06:14Z 裁決以 `U23` 判準收緊。本站以裁決為準寫成 `EPN-11`／`EPN-12`；
§二之一第 2 點的擁有者範圍**照舊有效**，可見性判定是**再加一道**（交集），不是取代。

## 一、資料分類

| 資料 | 分類 | 出現處 | 處置 |
|---|---|---|---|
| 使用者原句 | 使用者內容（可能含架構細節） | 送出的 `user_message`、對話紀錄 store | 只在記憶體；不寫瀏覽器儲存（`EPN-13`）；不進 console（`EPN-14`） |
| 大腦回覆、成本卡片文字 | 系統產出（可能複述使用者內容） | 對話紀錄 store | 同上 |
| 專案／系統／圖的名稱 | 業務資料（內部） | `work_target` 推送、脈絡列 | 只經授權與可見性判定後推送（`EPN-11`）；不寫 console；後端 log 不記（`EPN-14`） |
| 存取 token | 憑證 | `new WebSocket` 的子協定陣列 | 不進網址、不進 console、本單元不讀寫其儲存（`EPN-16`）。token 存在 `sessionStorage` 是**既有**行為（`AuthContext.tsx:84`），非本單元新增 |
| 作業對象識別碼 | 內部識別碼 | `work_target`、`set_work_target` | 回寫只送自有圖（`BR97.6`）；不進 console |

## 二、IAM：名稱查詢的可見性（R-01 使用者裁決）

| ID | 要求 | 可二元判定的檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`EPN-11`** | `describe_work_target` 回傳名稱的條件為**三者皆真**：① `_authorize(principal, "view")` 通過；② §二之一第 2 點的擁有者範圍成立；③ `U23` 的可見性判定（擁有者僅在零成員列時生效 ∪ 成員）對該三元組所屬專案為真。③ 為假時**三個名稱皆 null**——含圖名，即使該圖是請求者自己的資料列 | `unittest`（`TestClient` 或 facade 層）六案：(a) 擁有者且為成員 → 三名稱；(b) **被移出的建立者**（`owner_user_id` 仍是他、無成員列、專案另有成員）→ 三名稱皆 null；(c) 建立者、專案零成員列 → 三名稱（擁有者那一半生效）；(d) 非擁有者的成員 → null（② 不成立，記錄 `OPEN-EP14-9` 的現況）；(e) 自有孤兒圖 → 只有 `diagramName`；(f) `K2 view` 撤銷 → `HierarchyForbidden`，經 `_names_for` 後三名稱 null ＋ WARNING | 拿掉 ③ → (b) 紅；把 ③ 的外層 `project_id` 條件拿掉（`membership_service.py:370-373` 的 `M6` 形狀）→ (b) 紅 |
| **`EPN-11a`** | ③ 的判定**只有一份**：非測試程式只能取自 `MembershipFacade.project_visibility`（`membership_facade.py:518`）；`HierarchyFacade` 與 `brain_gateway` **都不得** import 成員關係符號 | 既有靜態鎖保持綠燈且**不得放寬**：`test_brain_gateway_limits.py:380-381` 的禁止清單仍含 `services.membership_facade`、`services.membership_service`；`test_project_visibility_static.py` 的 `S4`（`:162`，`project_visibility` 只定義在 `MembershipFacade`）不改。**擴充**：該檔 `S2`（`:112`，`project_visible` 必為無預設的 keyword-only）與 `S3`（`:135`，每個呼叫點都以 `<…>.project_visibility(...)` 注入）目前只涵蓋 `WRITE_METHODS` 三個寫入方法——新的讀取方法若採同一參數形狀，須納入同一組靜態斷言（集合改名或另立一組，由 `code-generation` 定），使唯一的讀取路徑與三條寫入路徑受同等的機械鎖 | 在 `brain_gateway.py` 加 `from services.membership_facade import …` → 既有靜態測試紅；呼叫 `describe_work_target` 時傳入自寫的 lambda → 擴充後的 `S3` 紅 |
| **`EPN-11b`** | 可見性判定以**必填、無預設、keyword-only** 的參數或等價的注入形狀進入名稱查詢（比照 `create_system` 等三條寫入路徑，`hierarchy_facade.py:251-262`）；注入點在組裝處（`build_brain_gateway` 的呼叫端或其 factory 參數），不在 `U13` 模組內自取 | 呼叫 `describe_work_target` 時漏傳可見性 → `TypeError`（fail-closed），不是「略過守門回名稱」；`unittest` 一案 | 把參數改成 `project_visible=None` 並在 None 時略過 → 該案紅 |
| **`EPN-12`** | 「不存在」「不屬請求者」「不可見」「查詢失敗」四種情形對前端**逐位元相同**：該層（或三層）皆為 null、`work_target` 照常推送、不另送 `error` | `unittest`：四情形的 `work_target` payload 序列化後逐位元比對 | 不可見時改回 `error(UNAUTHORIZED)` → 比對紅（可被用來探測專案存在） |

形狀（例如在 `U7` facade 內接收注入的判定，或由組裝處把判定與 facade 一併交給 `U13`）由 `nfr-design`／`code-generation` 定案（R-01 裁決原文）；
本節只鎖住**結果**（`EPN-11`）、**唯一來源**（`EPN-11a`）與 **fail-closed**（`EPN-11b`）。

## 三、IAM：前端落地與回寫

| ID | 要求 | 檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`EPN-17`** | `K1` 判斷是**呈現**，真正的拒絕在 `U13`（握手 4403、每則訊息重驗）；前端判斷位置在 `isPending` 之後、其他權限之前（`BR91.1`） | Playwright 雙向：有 `K1` → `/` 渲染入口頁；無 `K1` → 既有瀑布（最終 `/403` 或其他落點）；`isPending` → `/waiting-approval` | 把 `K1` 判斷移到 `isPending` 之前 → `isPending` 案紅 |
| **`EPN-17a`** | 子頁面只回寫**自有**圖（`BR97.6` ①）；別人分享的圖不送 `set_work_target` | Playwright（`routeWebSocket` 記錄客戶端送出訊框）：開別人分享的圖 → 客戶端送出的 `set_work_target` **0** 則 | 拿掉 `is_owner` 條件 → 計數 1，紅 |

## 四、資料完整性與隔離（R-02、R-03 使用者裁決）

| ID | 要求 | 檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`EPN-18`**（R-02） | 首次對齊（`BR97.5` (2)）在畫布**有未儲存內容**時**不自動開圖**，改顯示提示讓使用者自行切換；無未儲存內容時才自動開啟。`/workspace` 的「未儲存」判定沿用既有判定式（`WorkspacePage.tsx:118-121`：`saveStatus` 為 `unsaved`／`saving`，或 `no-file` 且畫布 XML 非空），**不另寫第二份不同定義**；`/assessment` 的未存檔上傳同理（判定式由 `nfr-design` 定案並在 code-summary 指名） | Playwright（`routeWebSocket`）：畫布先有未儲存內容 → **重連後**才送出首筆相符 `work_target`（晚到）→ 畫布 XML 不變、提示出現、按提示後才換圖；對照案：畫布乾淨 → 自動開啟 | 拿掉未儲存判定 → 晚到案的畫布被取代，紅 |
| **`EPN-15`**（R-03） | 對話紀錄的清空綁在 `AuthContext` 的 **`login()` 與 `logout()` 事件本身**（`AuthContext.tsx:82`、`:56`；含 `/me` 初始化失敗、`checkAuthSession` 失敗、4401 後登出等全部經 `logout()` 的路徑），**不依賴** `User.id`（`auth-context.ts:29` 為可選），**不得**以重掛整個路由樹的方式清空 | Playwright：使用者 A 登入並對話 → 以 `page.route` 使 `/api/auth/me` 回 500（user 因此無 `id`）→ 登出 → 使用者 B 登入 → 入口頁與兩子頁面的對話區皆為空。附帶斷言：A 登入後的導航只發生一次（`BrowserRouter` 子樹未重掛，以頁面上一個非受控輸入的值在登入前後保留驗證，或以 render 計數替代，形狀由 `nfr-design` 定） | 改回以 `user?.id ?? "anon"` 為 key → `/me` 失敗案的 key 不變，B 看到 A 的對話，紅 |
| **`EPN-15a`** | 不經登出而直接再次 `login()`（例如在 `/login` 以另一帳號登入）也清空 | 同上 e2e 的變體：A 登入 → 直接導 `/login` 以 B 登入 → 對話區為空 | 只在 `logout()` 清 → 紅 |

## 五、資料保護、log 與憑證

| ID | 要求 | 檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`EPN-13`** | 本單元新增的前端程式**不寫** `localStorage`、`sessionStorage`、IndexedDB、Cache Storage（`BR93.4`） | Playwright：完成一次對話後 `page.evaluate` 取 `localStorage`／`sessionStorage` 的鍵集合，與對話前相同；且兩者的全部值都不含測試原句。另以 `grep -rnE "localStorage|sessionStorage|indexedDB|caches\." frontend/src/brain frontend/src/components/brain`（實際目錄以 code-generation 為準）為 **0** | 在 store 加一行 `sessionStorage.setItem` → e2e 紅 |
| **`EPN-14`** | **log 不含使用者文字、名稱、token**。前端：console 只記 type、code、關閉碼、turnId（`BR92.8`、`BR93.2`）；後端：`work_target_names_failed` 只帶 `connId` 與 `exc`（例外類別名），既有白名單 `_ALLOWED`（`brain_gateway.py:130-149`）**不新增欄位** | Playwright：`page.on('console')` 收集全部訊息，斷言不含測試原句、不含三個測試名稱、不含 token 子字串；`unittest`：`assertLogs` 斷言 `work_target_names_failed` 一筆且訊息不含名稱；`_ALLOWED` 的集合在本單元前後相等 | `console.warn(payload)` → e2e 紅；在 `_log` 加 `name=` → 既有白名單 `ValueError` |
| **`EPN-16`** | token 只出現在 `new WebSocket` 的子協定陣列；網址**不含**查詢字串（FR8.5、`AC8.1.3`）；子協定值以 `WsSubprotocol` 型別取值（ADR-0019 §5 的既有 lint 規則） | Playwright：`page.on('websocket')` 的 `url()` 不含 `?` 且不含 token 子字串；`npm run lint` 綠 | 把 token 放進 `?token=` → 紅 |
| **`EPN-19`**（R-04） | e2e 樁訊框只能由 `src/brain/testing/wsFrames.ts` 的建構器產生；建構器**只收原始型別引數**（字串、數字、布林、null），內部先以具名 payload 型別（如 `WorkTargetPayload`）宣告區域變數再放入 envelope；spec 不得手寫含 `type` 鍵的物件字面量 | `npm run build`（`tsc -b`）綠；ESLint `no-restricted-syntax` 限 `frontend/tests/**`：含 `type` 鍵的物件字面量為 error（`eslint.config.js` 的 `files: ['**/*.{ts,tsx}']` 已涵蓋 tests 目錄，`globalIgnores` 只排除 `dist`） | 契約欄位改名重產型別 → `npm run build` 紅（`BR98.4` 的突變驗證）；spec 內手寫 `{ type: "work_target", … }` → lint 紅 |

## 六、ADR-0006 四面向（逐格對照上游 `functional-spec.md` §九之一）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用 | **適用（擴充）** | 上游的「不擴大可見範圍」已由 R-01 裁決收緊為「擁有者範圍 ∩ `U23` 可見性」（`EPN-11`–`EPN-12`）；另加前端回寫只送自有圖的可觀察檢查（`EPN-17a`）。擴充來自裁決，非重判 |
| **Encryption** | 適用 | **適用（相同）** | 傳輸沿用 `U13` 的 `wss`；對話紀錄只在記憶體（`EPN-13`），C-8 不新增任何持久化。token 的 `sessionStorage` 為既有落點，本單元不新增也不改變 |
| **Network exposure** | 適用 | **適用（相同）** | 不新增對外端點；每分頁至多一條連線（`EPN-01`）、終止碼不重連（`EPN-03`）、退避加抖動（`EPN-02`）；`describe_work_target` 只在進程內被 `U13` 呼叫，不新增路由；前端不新增 HTTP（`EPN-08`） |
| **Audit logging** | 適用（本單元不新增稽核寫入） | **適用（相同）** | 活動時間由 `U13` 的 `record=True` 承擔；名稱查詢唯讀不寫稽核；本站補的是**不得記錄**的一面（`EPN-14`），不是新增稽核事件 |

## 七、PBT hard constraint

**不適用**，與上游 `functional-spec.md` §九之二一致。ADR-0006 點名的三個核心模組（IaC generator、cost calculator、agent routing）本單元皆不觸及；
`describe_work_target` 是唯讀查詢、`_names_for` 是推送前的組裝，皆非 `U11` 路由核心。`EPN-11` 的六案以**窮舉身分**驗證可見性（比照 `U23` 的五身分窮舉），
不以 `hypothesis` 取代；前端純函式（紀錄 store、首次對齊判斷）無 unit 框架（`team.md` D 項不採），由 Playwright 以例子驗證。

## 八、帶入項對照（`carried-review-items.md`）

| 帶入項 | 本站落點 | 留給後續站 |
|---|---|---|
| **R-01**（Major，裁決） | `EPN-11`、`EPN-11a`、`EPN-11b`、`EPN-12`；效能面 `EPN-06` 把可見性判定計入語句數上界 | 注入形狀 → `nfr-design`；實作與六案測試 → `code-generation` |
| **R-02**（Major，裁決） | `EPN-18`（含既有判定式的沿用要求） | `/assessment` 未存檔判定式 → `nfr-design`；e2e → `code-generation` |
| **R-03**（Major，裁決） | `EPN-15`、`EPN-15a` | 清空訊號的元件形狀（例如 `AuthProvider` 暴露事件或 epoch 並由紀錄 Provider 在事件回呼中重設）→ `nfr-design` |
| **R-04**（Minor） | `EPN-19`（建構器只收原始型別、lint 機械化） | `code-generation` |
| **R-05**（Minor，回聲抑制以集合或序號比對） | 非 NFR，本站不處置 | `code-generation`（code-summary 記明） |
| **R-06**（Minor，`/workspace` 清單請求成功旗標、空字串名稱） | 非 NFR，本站不處置 | `code-generation` |
| **R-07**（Minor，合併前檢查與升版論證） | 部分：`tech-stack-decisions.md` 的 `NFR5.140` 寫明「前端在本單元之前無 WS 消費者」的論證與合併前在分支上執行的檢查 | `code-generation` |
| **R-08**（Minor，bootstrap 自動開圖不回寫） | 非 NFR，本站不處置 | `code-generation` |
| OPEN-EP14-2（最近的對話） | 已移到另一 intent，本站不處置 | — |
| OPEN-EP14-1 子項（`U7` 加 `describe_work_target`） | `EPN-06`、`EPN-11` 系列、`tech-stack-decisions.md` 的 `EPN-25` | `code-generation` |

## 九、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 被拒絕的名稱查詢另記 log | `U7`／`U19` 家族目前零處記拒絕（`U23` 同站已以 grep 查證，`project-pages-ui/nfr-requirements/security-requirements.md` §五）；不可見回 null 是正常結果，不是事件 |
| 前端清除 token 的新機制 | token 的儲存與清除屬 `AuthContext` 既有行為；本單元只要求不讀、不寫、不記錄（`BR92.8`） |
| 對話紀錄加密 | 只在記憶體、不落地（`EPN-13`），無靜態落點可加密 |
