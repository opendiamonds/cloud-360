# Security Requirements — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T01:07:04Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。
> 本站兼任 devsecops／compliance／quality 的視角；以下每一條都附「可二元判定的檢查」與「必須紅燈的突變」。
>
> **綁定**：`functional-spec-corrections.md` 的 `F-01`–`F-08` 在本檔 §八逐條對照落點；衝突時以該附錄為準。

## 〇、上游依據

| 來源 | 內容 |
|---|---|
| `functional-design/rules.md` | `BR13.2`（非擁有者停用，且明寫**不是授權**）、`BR14.1`（建立只經 `objectCreateAction`）、`BR14.2`／`BR14.3`（建立入口的渲染條件）、`BR13.4`（前端搜尋） |
| `functional-design/functional-spec.md` | §四之一（清單可見範圍 ≠ 大腦解析範圍）、§四之二（`K2 edit` 只有 4 個角色）、§九之二（ADR-0006 四面向，本站逐格對照，見 §六） |
| `functional-design/functional-spec-corrections.md` | `F-01`（`AC9.2.3` 改讀 `Deferred`、404 路徑）、`F-02`–`F-08` |
| `inception/requirements-analysis/requirements.md` | ADR-0006 四面向表（`:591` 起） |
| repo 實測 | `projectsApi.ts:14-17`（`createProject`／`createSystem` 只准由 `objectCreateAction` 呼叫、本檔零主控台輸出）、`objectCreateAction.ts:51-57`（`classify`：只認 409／403，其餘含 404 歸 `other`）、`hierarchy_router.py:237-272`（伺服器端建立的 `K2` ＋ 擁有者檢查）、`hierarchy_service.py:299-309`（作業對象以擁有者範圍解析）、`AuthContext.tsx:79-84`（`refreshMe`）、`auth-context.ts:29`（`id?: number`） |

## 一、資料分類

| 資料 | 分類 | 出現處 | 處置 |
|---|---|---|---|
| 專案／系統名稱（含**他人**建立、經成員關係可見者） | 業務資料（內部；名稱由其他使用者輸入，屬不可信輸入） | 選單清單、建立表單 | 以文字節點呈現、不經 HTML 解析（`OPN-13`）；不寫瀏覽器儲存、不進主控台（`OPN-15`） |
| 使用者在建立表單輸入的名稱 | 使用者內容 | 表單 state、`POST` 主體 | 失敗時保留在表單（`BR14.4`）；關閉選單即丟棄；不進主控台 |
| 搜尋字串 | 使用者內容 | 搜尋框 state | 只做子字串比對、不編譯成正規表示式（`OPN-14`）；不送出到任何地方 |
| 存取 token | 憑證 | 既有 `Authorization: Bearer` 標頭（`projectsApi.ts:71`） | 本單元不讀寫其儲存、不放進網址、不進主控台（`OPN-15`） |
| 作業對象識別碼 | 內部識別碼 | `set_work_target` 訊框 | 只經 `setWorkTarget` 送出（`NFR5.160`） |

## 二、IAM：前端判定是呈現，不是授權

| ID | 要求 | 可二元判定的檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`OPN-11`** | 建立入口的渲染依 `can('K2','edit')`（`BR14.2`）與擁有者條件（`BR14.3`）；兩者都只決定**是否顯示**，伺服器仍以 `require_story_action`（`K2`）＋ 擁有者檢查判定（`hierarchy_router.py:237-272`）。建立**只**經 `objectCreateAction`（`BR14.1`），選單程式不得直接呼叫 `createProject`／`createSystem` | Playwright 雙向：持 `K2 edit` 的角色 → 「+ 新增專案」可見；無 `K2 edit`（如 `Developer`）→ 不可見，且 `empty` 態只有說明（`BR14.6`）。靜態：`grep -rnE "createProject\(\|createSystem\("` 對 `frontend/src` 的非宣告命中**只在** `objectCreateAction.ts` | 拿掉 `can('K2','edit')` 條件 → 無權限案紅；選單直接呼叫 `createProject` → 靜態檢查紅 |
| **`OPN-12`** | 擁有者判定**只有一份**：`BR13.2`（可選性）與 `BR14.3`（可建系統）呼叫同一個純函式（`functional-spec.md` §二之一的 `isOwnedByMe`），以 `owner_user_id === user.id` 比較 | 靜態：選單相關檔案內 `owner_user_id` 的比較式恰 **1** 處（在 `isOwnedByMe` 內）；Playwright：以 `page.route` 回一個 `owner_user_id` 不是目前使用者的專案 → 該群組停用**且**無「+ 新增系統」；自有專案 → 可選**且**（有 `K2 edit` 時）有「+ 新增系統」 | 在建立入口另寫一份方向相反的比較 → 「選不了卻能建」的組合出現，e2e 紅 |
| **`OPN-16`**（`F-01`） | 「在別人的專案下建系統」在選單內**不可達**；若伺服器仍回 404（例如擁有權在選單開啟後轉移），顯示 `objectCreateAction` 的 `other` 文案、名稱保留、表單不收、不崩潰 | Playwright：(a) 非擁有者群組無 `brain-object-create-system-{id}`；(b) 以 `page.route` 讓自有群組的 `POST …/systems` 回 404 → 出現「建立系統失敗，請稍後再試」、名稱仍在欄位內 | 移除 `BR14.3` 的擁有者條件 → (a) 紅 |

**為什麼選 `F-01` 的第二支**：`objectCreateAction.ts:51-57` 的 `classify` 只把 409／403 分出來，404 一律是 `other`，且 `ObjectCreateError` 不帶狀態碼。
要顯示權限文案只能改 `U23` 已交付的唯一寫入路徑（`INV-2`）；本單元的前端條件已讓該路徑不可達，故不重開 `U23`。`AC9.2.3` 字面與 `U7` 實作的矛盾
（`F-01` 第一點）屬交關卡事項 `G-2`，本站不處置。

## 三、輸入與輸出處理

| ID | 要求 | 檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`OPN-13`** | 專案與系統名稱一律以 React 文字節點呈現；選單程式**不得**使用 `dangerouslySetInnerHTML`、`innerHTML` 或任何把名稱當 HTML 解析的方式 | 靜態：`grep -rn "dangerouslySetInnerHTML\|innerHTML"` 對選單相關檔案為 **0**（全 `frontend/src` 現況亦為 0）；Playwright：以 `page.route` 回一個名稱為 `<img src=x onerror="window.__xss=1">` 的專案 → 清單上看得到該字串原文，且 `window.__xss` 為 `undefined` | 改用 `dangerouslySetInnerHTML` 呈現名稱 → `window.__xss` 為 1，紅 |
| **`OPN-14`** | 搜尋以**子字串比對**實作，不把使用者輸入編譯成正規表示式 | 靜態：選單相關檔案內 `new RegExp` 為 **0**；Playwright：輸入 `(`、`[`、`\` 各一次 → 不拋例外、畫面不崩潰、出現 `no-match` 或正確命中 | 改成 `new RegExp(query)` → 輸入 `(` 拋 `SyntaxError`，紅 |

## 四、資料保護與 log

| ID | 要求 | 檢查 | 必須紅燈的突變 |
|---|---|---|---|
| **`OPN-15`** | 選單程式**不寫**任何瀏覽器儲存（`localStorage`、`sessionStorage`、IndexedDB、Cache Storage），**不輸出**任何主控台訊息（沿用 `projectsApi.ts:17` 與 `fanoutQueue.ts:22` 的零主控台慣例）；token 不出現在任何網址 | 靜態：選單相關檔案內 `localStorage\|sessionStorage\|indexedDB\|caches\.` 與 `console\.` 皆為 **0**；Playwright：開啟、搜尋、建立一輪後 `localStorage`／`sessionStorage` 鍵集合與之前相同；`page.on('console')` 收集到的訊息不含測試專案名稱；所有 `/api/hierarchy` 請求的 URL 不含 `?` | 在選單加 `sessionStorage.setItem('picker', …)` → 鍵集合比對紅；`console.log(groups)` → 靜態檢查紅 |

## 五、身分邊界

選單的清單 state 每次開啟重抓、關閉即丟（`BR12.1`、`BR12.4`），不跨開啟保留，故換人登入時沒有可殘留的清單。身分邊界的既有機制
（`AuthContext.tsx:59` 的 `login()`／`logout()` 首行同步通知）屬 `U14`，本單元不訂閱也不需要訂閱。`OPN-04` 的 `refreshMe()` 呼叫
**不**觸發該通知（`auth-context.ts:55` 逐字「`refreshMe()` 與權限更新**不**通知」），故不會意外清空 `U14` 的對話紀錄。

## 六、ADR-0006 四面向（逐格對照上游 `functional-spec.md` §九之二）

| 面向 | 上游判定 | 本站判定 | 差異與理由 |
|---|---|---|---|
| **IAM** | 適用（呈現層） | **適用（相同）** | 本站把上游的「三者都不是授權」寫成可測形式：雙向 e2e（`OPN-11`）、單一判定函式（`OPN-12`）、不可達路徑（`OPN-16`）。不新增 story id、不改權限矩陣 |
| **Encryption** | 不適用（本單元無新增落點） | **不適用（相同）** | 零新增持久化（`OPN-15` 把「不寫瀏覽器儲存」變成檢查，使上游的判定失效條件可被偵測）；傳輸沿用既有 HTTPS 與 `wss` |
| **Network exposure** | 不適用（本單元無新增落點） | **不適用（相同）** | 零新端點、零新進程、零新環境變數（`NFR8.160`）；請求數有上界（`OPN-01`） |
| **Audit logging** | 不適用（本單元無新增落點） | **不適用（相同）** | 建立的稽核由 `U7` 的 `create_*` 承擔（`contract-summary.md:534`）；本單元經 `objectCreateAction` 呼叫同一端點，不繞過。本站補的是**不得記錄**的一面（`OPN-15`） |

## 七、PBT hard constraint

**不適用**，與上游 `functional-spec.md` §九之三一致：ADR-0006 點名的 IaC generator、cost calculator、agent routing 本單元皆不觸及。上游指出的兩個純函式
（擁有者判定、搜尋過濾）以例子驗證：`OPN-12` 的兩種擁有者、`OPN-14` 的三個特殊字元；前端無 unit 框架（`team.md` D 項不採），不以 `fast-check` 取代。

## 八、更正附錄對照（`functional-spec-corrections.md`）

| 更正 | 本站落點 | 留給後續站 |
|---|---|---|
| **F-01**（Major） | `OPN-16`（不可達 ＋ 404 文案）；`traceability.json` 不再引用 `AC9.2.3`（本站上游為 inception NFR） | `AC9.2.3` 的字面裁決 → 關卡 `G-2`；`code-generation` 的追溯以 `Deferred` 處理 `AC9.2.3` |
| **F-02**（Major） | `performance-requirements.md` 的 `OPN-05` | 焦點返還與容器 `tabIndex={-1}` 的實作 → `code-generation` |
| **F-03** | `OPN-04` | — |
| **F-04** | `OPN-07`（每個播報事件只寫一處） | 選單內播報區的元件形狀 → `nfr-design` |
| **F-05** | `OPN-01`；`tech-stack-decisions.md` 的 `OPN-24`（不用 `fanoutQueue`） | 每群組錯誤與重試的呈現 → `code-generation` |
| **F-06** | 非 NFR（狀態正交、三問、版面）；本站不處置 | `nfr-design`／`code-generation` |
| **F-07** | 非 NFR（追溯與範圍縮減的下游文件）；本站不處置 | 關卡 `G-1` |
| **F-08** | 非 NFR（刪除路徑不存在）；本站不處置 | 關卡 `G-3` |

## 九、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 前端記錄被拒的建立或切換 | 伺服器已是授權點；前端記錄會違反 `OPN-15` 的零主控台，且本 repo 無前端遙測 |
| 擴大大腦的作業對象解析範圍讓成員可選 | `[OP3]`=D 未被選（`functional-spec.md` §九之二 IAM 列）；屬關卡 `G-5` |
| 名稱長度或字元的前端驗證 | 名稱規則的正本在伺服器（`objectCreateAction` 只做去空白後非空檢查，`objectCreateAction.ts:76-77`）；前端另寫一份違反 `team.md` 的「單一真實來源」 |
