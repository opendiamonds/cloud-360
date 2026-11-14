# Tech Stack Decisions — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T01:07:04Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。

## 〇、選型（皆沿用既有，本站不重選）

| 層 | 選型 | 依據 |
|---|---|---|
| 前端 | React 19 ＋ TypeScript ＋ Vite ＋ Tailwind 4 | `frontend/package.json`；`project.md ## Tech Stack` |
| HTTP 抓取 | `U23` 的 `projectsApi.ts`（`listProjects`／`listSystems`）與 `objectCreateAction.ts` | `functional-spec.md` §四；`BR14.1` |
| 切換作業對象 | `useBrainSession().setWorkTarget`（`U14`），型別取自產生的 `ws-contract.d.ts` | `brainSession.ts:57`；ADR-0019 |
| 前端測試 | **僅** Playwright e2e；`page.route` 樁 HTTP、`routeWebSocket` 扮演伺服器；樁訊框只經 `frontend/src/brain/testing/wsFrames.ts` 的建構器 | `team.md`（D 項不採）；`codekb/chiton/technology-stack.md:119`（「前端測試框架仍只有 Playwright」）；`U14` 的 `EPN-19`／`EPN-22`（`eslint.config.js:94` 對 tests 目錄禁止手寫訊框） |
| 無障礙掃描 | `@axe-core/playwright` 4.13.0（`U17` 已引入） | `frontend/package.json:25` |
| 後端 | **無變更** | `functional-spec.md` §三之一末句 |

## 一、決定

| ID | 決定 | 理由 | 檢查 |
|---|---|---|---|
| **`NFR5.160`** | 選單**不新增**任何 WebSocket 訊息型別；`set_work_target` 只經 `setWorkTarget` 送出，選單程式不直接操作 `WebSocket` 物件、不手寫訊框 | 父條 `NFR5`（WebSocket 契約閘門，`requirements.md:510`）：兩道既有 WS 漂移閘門只在契約有單一來源時擋得住；`[OP1]`=B／`[OP2]`=D 會新增訊息型別，皆未被選 | `ws-contract.json` 在本單元前後位元相同（`git diff --stat` 零變更）；選單相關檔案內 `new WebSocket`、`.send(` 為 **0** |
| **`NFR8.160`** | 本單元**零新環境變數、零 compose 變更** | 父條 `NFR8`（新增元件的部署設定完整性，`requirements.md:537`）：把「零」寫成可檢查的宣告 | `python3 scripts/validate_env_contract.py` 通過；`git diff --stat` 中 `deploy/`、`*.env.example` 零變更 |
| **`OPN-21`** | **識別碼型別在送出邊界轉換**：HTTP 回應的 `ProjectOut.id`／`SystemOut.id` 是數字，`WorkTargetIds` 與 `work_target` 的三層 id 是字串（`brainSession.ts:30-34`、`ws-contract.d.ts:203`／`:214`）。選單在呼叫 `setWorkTarget` 時以 `String(id)` 轉換；`BR13.3` 的「目前」標示以同一方向比較（`String(p.id) === target.projectId`），轉換只寫在 `objectPickerModel` 一處 | 數字與字串以 `===` 比較恆為假：漏轉會讓「目前」標示永遠不出現，且 `tsc` 不一定擋得住（`WorkTargetPayload` 的欄位若經寬鬆型別傳遞） | Playwright（`routeWebSocket` 記錄客戶端訊框）：選定專案 7 → 送出的 `projectId` 為字串 `"7"`；伺服器回推 `projectId: "7"` 後重開選單 → 專案 7 那列有「目前」 |
| **`OPN-22`** | 前後端**零新依賴** | `team.md` Code Style；`routeWebSocket`、`page.route`、`AxeBuilder` 皆已安裝 | `frontend/package.json` 的 `dependencies`／`devDependencies` 鍵集合前後相同；`backend/requirements.txt` 不變 |
| **`OPN-23`** | 選單的 e2e 放新檔 `frontend/tests/e2e/object-picker.spec.ts`，由既有 `ui-regression` 撿到；axe 掃描點加進 `U17` 的 `a11y.spec.ts` 掃描清單（`OPN-07`），**這是修改已交付的 `U17` 檔案**，與 `ContextBar.tsx`（`OPEN-OP16-4`）同屬重開，`code-generation` 須在 code-summary 揭露並跑 `U17` 全部 22 個測試 | 不新增 CI job；掃描標準只有一份（`U17` 的 `WCAG_TAGS` 與基準清單規則），另寫一份會讓兩處標準漂移 | `.github/workflows/` 不因本單元變動；`a11y-baseline.json` 的 `entries` 在本單元前後皆為空陣列 |
| **`OPN-24`** | **不使用 `fanoutQueue`**；系統清單在展開群組時以單一 `listSystems` 呼叫取得（`F-05`）。關閉選單以 `cancelled` 旗標丟棄在途結果，不中止請求 | `F-05` 之後沒有扇出；`requestJson` 不收 `AbortSignal`（`projectsApi.ts:59-82`），改簽名等於重開 `U23`。`rules.md` `BR12.1` 提到 `fanoutQueue` 的那半句由 `F-05` 取代 | 選單相關檔案內 `fanoutQueue` 匯入為 **0**；`OPN-02` 的 e2e |
| **`OPN-25`** | 本站各條「必須紅燈的突變」在 `tcms-test-cases` 的 `automation-test-plan.md` 逐條記錄結果 | `project.md ## Mandated` 的 `tcms-test-cases` 必做 3 | `automation-test-plan.md` 對 `security-requirements.md` 與本檔每個突變各有一列 |
| **`OPN-26`** | `team.md` 測試底線的適用判定：**A 不適用**（不改 `role_permissions`）、**B 不適用**（不新增或修改 HTTP 端點）、**C 適用**（新的前端畫面與資料形狀 → e2e 斷言，即 `OPN-01`–`OPN-07`、`OPN-11`–`OPN-16`） | 逐條對照 `team.md ## Testing Posture` 的 A／B／C，不以「沒有後端」整批帶過 | `code-summary.md` 列出 C 規則對應的 e2e 案例名稱 |

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| 前端 unit／component 測試框架 | `team.md` D 項不採；純函式（擁有者判定、搜尋過濾、id 轉換）以 e2e 驗證 |
| 下拉／對話框元件庫（Headless UI、Radix 等） | 新依賴；焦點陷阱與方向鍵移動（`BR15.2`／`BR15.3`）以既有 Tailwind 與原生事件實作 |
| 修改 `projectsApi.ts` 加入 `AbortSignal` | 重開 `U23`；丟棄已足以滿足 `BR12.4`（`OPN-24`） |
| 修改 `objectCreateAction.ts` 暴露狀態碼 | 重開 `U23` 唯一寫入路徑；改以不可達處理（`OPN-16`） |

## 三、為什麼本單元不產出 scalability／reliability／observability

`produces_kinds` 把三份限定為 `[service]`，本單元為 `ui` 且**無後端變更**，逐份確認：

| 文件 | 若產出，內容會是 | 判定 |
|---|---|---|
| scalability | 「每次開啟的請求數不隨專案數成長」 | 已在 `performance-requirements.md` 的 `OPN-01` 表達 |
| reliability | 身分未決、斷線、請求失敗時的行為 | 已在 `OPN-04`、`OPN-05`、`F-05` 的每群組錯誤表達；本單元**沒有新增進程、佇列、外部依賴或持久化**，無可用性目標可設 |
| observability | 新 log、metric | 本單元**不得**輸出主控台訊息（`OPN-15`）；無後端程式可加 log；無 metric 機制可接 |

## 四、與上游的落差（如實記載，設計檔不回改）

- **`rules.md` `BR12.1` 的「扇出沿用 `fanoutQueue`」**：由 `F-05` 取代為展開群組時才抓（`OPN-01`、`OPN-24`）。
- **`rules.md` `BR12.2` 的「任一請求失敗即整個清單進 `error`」**：由 `F-05` 收窄為只有專案清單失敗才整體 `error`，單一群組的系統清單失敗只影響該群組。
- **`rules.md` `BR15.4` 的「一律寫入頁面 `LiveRegion`」**：由 `F-04` 取代為時間分工（`OPN-07`）。
- **`functional-spec.md` §五 W1 第 3 步的「保持 `loading`，待其成為數字」**：由 `F-03` 取代為呼叫一次 `refreshMe()` 後轉 `error`（`OPN-04`）。
- **`F-01` 的二擇一**：本站選第二支（不可達），理由見 `security-requirements.md` §二。

## 五、送審前自檢（七項；四份產出 ＋ 問題檔共用）

> 全部產出寫完後實算，指令與值並列；本站未執行任何測試（限制）。

| # | 自檢 | 結果 |
|---|---|---|
| 1 | **可達性** | `OPN-04`：`page.route('/api/auth/me')` 回 500 使 `user.id` 缺漏——`AuthContext.tsx` 初始化在 `/me` 失敗時走 `logout()`（`:94`），故須在**登入後**才讓 `/me` 失敗（`login()` 先以不含 `id` 的物件 `setUser`，`U14` 的 `EPN-15` 已驗證此路徑可達）。`OPN-05`：`routeWebSocket` 由伺服器端關閉，可達。`OPN-16` (b)：自有群組的 `POST` 以 `page.route` 回 404，可達。`OPN-21`：`routeWebSocket` 記錄客戶端訊框，可達。`OPN-02`：`page.route` 延遲與計次，可達 |
| 2 | **契約端點三問**（範圍：四份產出 ＋ 問題檔） | **`cancelled` 旗標**（`OPN-24`）：寫＝關閉選單時設真；讀＝每個抓取的 `.then`；清＝每次開啟以新的旗標重設。**選單內播報區**（`OPN-07`）：寫＝開啟期間的播報；讀＝螢幕閱讀器；清＝隨選單卸載。**`refreshMe` 呼叫計數**（`OPN-04`）：寫＝每次開啟最多一次、重試鈕各一次；讀＝決定是否轉 `error`；清＝關閉選單。**id 轉換**（`OPN-21`）：擁有＝`objectPickerModel`；呼叫＝`setWorkTarget` 前與「目前」比較兩處。出現在少於兩份產出的識別字逐一判定：`OPN-21`–`OPN-26` 只在本檔與 `traceability.json`，屬本檔內部決定，非孤兒 |
| 3 | **引用逐字核對（分開驗事實與定位）** | 逐一以 `sed -n` 印出核對：`projectsApi.ts:14-17`／`:59-82`／`:71`／`:85-104`、`objectCreateAction.ts:9-10`／`:51-57`／`:76-77`、`AuthContext.tsx:59`／`:79-84`／`:94`、`auth-context.ts:29`／`:55`、`brainSession.ts:30-34`／`:56-57`、`ws-contract.d.ts:203`／`:214`、`fanoutQueue.ts:22`、`eslint.config.js:94`、`package.json:25`、`a11y.spec.ts:38`／`:711`、`requirements.md:430`／`:510`／`:537`／`:563`／`:577-578`／`:591`。結果見本表下方的實跑紀錄 |
| 4 | **檔案集合一致性** | 對照同為 `ui` 的 `entry-page-ui/nfr-requirements/`（不計 `reviews/`）：問題檔、performance、security、tech-stack、traceability 五份——**相同** |
| 5 | **跨檔傳播（按事實）** | ①「系統清單展開才抓、不用 `fanoutQueue`」——問題檔 §〇、performance `OPN-01` 與 §三、security §八 `F-05` 列、本檔 `OPN-24` 與 §四；②「`F-01` 選第二支」——問題檔 §一第 5 點、security `OPN-16` 與 §二末段、本檔 §四；③「不設逾時」——問題檔 §一第 1 點、performance §三；④「零主控台、零儲存」——security `OPN-15`、本檔 §三；⑤「axe 掃描點加進 `U17`」——performance `OPN-07`、本檔 `OPN-23`。實跑結果見下方 |
| 6 | **可算的數字先算再寫** | 見下方實跑紀錄（`traceability.json` 的計數以 `jq` 取得） |
| 7 | **ADR-0006 四面向 ＋ PBT** | 見 `security-requirements.md` §六、§七，逐格對照上游 `functional-spec.md` §九之二：四面向判定**全部與上游相同**；PBT 不適用、與上游一致 |

### 五之一、實跑紀錄

| 項 | 指令 | 值 |
|---|---|---|
| 自檢 3：引用定位 | 每個 `<file>:<n>` 以 `sed -n '<n>p'` 印出 | 全部相符；**查出並更正一處事實錯誤**：問題檔 §一第 1 點初稿寫「全站 52 處 `fetch()` 皆同」（沿用 `team.md` 的舊數字），實算 `grep -rc "fetch("` 加總為 **74**，且 `EstimateAdvicePanel.tsx` 用了 `AbortController`（為取消串流）——已改寫為「74 處無一設逾時」並點名該例外。另 `OPN-02` 初稿以「無 React 卸載後更新警告」判定，React 19 已移除該警告，會是恆真斷言——已改為「晚到的舊回應永不上畫面」 |
| 自檢 5：跨檔傳播 | 每個事實對五份檔各 `grep -c` | `fanoutQueue`：0／1／2／4（問題檔不提該名稱，以「展開群組時才抓」表達同一事實）；「第二支」：1／0／1／2（performance 不涉及）；「逾時」：3／1／0／1（security 不涉及）；「主控台」：0／1／6／2；「`U17`」：0／1／0／3（security 不涉及）。無矛盾敘述 |
| 自檢 6：`traceability.json` | `jq` | `upstream_ids` **11**；`OK` **4**（`NFR2`、`NFR5`、`NFR8`、`NFR11`）、`N/A` **7**；繼承子條 **4**（`NFR2.160`、`NFR5.160`、`NFR8.160`、`NFR11.160`），與三份產出中出現的 `NFR*.16x` 集合相同；`reverse` 孤兒 **19**（三份產出以粗體定義的 `OPN-*`：performance 7、security 6、tech-stack 6），與 `reverse` 的 id 集合以 `comm -3` 比對**零差異**；需求總數 4＋19＝**23** |
