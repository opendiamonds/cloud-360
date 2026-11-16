# Tech Stack Decisions — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T02:11:18Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。

## 〇、選型（皆沿用既有，本站不重選）

| 層 | 選型 | 依據 |
|---|---|---|
| 前端 | React 19 ＋ TypeScript ＋ Vite ＋ `react-router-dom` 7 ＋ Tailwind 4 | `frontend/package.json`（`react ^19.2.6`、`react-router-dom ^7.18.2`）；`project.md ## Tech Stack` |
| 前端型別（WS） | `openapi-typescript` 由 `ws-contract.json` 產生 `src/types/ws-contract.d.ts`（`npm run gen:ws-types`） | `frontend/package.json:14`；ADR-0019 |
| 大腦通道 | 瀏覽器原生 `WebSocket`，`wsUrl()` 組址（`frontend/src/config/api.ts:31`） | `BR92.1`；`unit-of-work.md` 對 `U14` 的約束「沿用 `wsUrl()` 不自造 URL 組裝」 |
| 後端 | Python ／ FastAPI ／ SQLAlchemy（既有 `hierarchy_*`、`membership_*`、`brain_gateway*`、`brain_ws_contract`） | `project.md ## Tech Stack` |
| 後端測試 | `unittest` ＋ `starlette.testclient.TestClient` ＋ `ast`（靜態鎖） | `team.md ## Testing Posture`（非 pytest；B 規則） |
| 前端測試 | **僅** Playwright e2e（chromium 單一 project）；`routeWebSocket` 扮演伺服器 | `team.md`（D 項不採）；`codekb/chiton/technology-stack.md:119`；已安裝 `@playwright/test` 1.61.1（`node_modules/@playwright/test/package.json:3`），`routeWebSocket` 需 ≥ 1.48 |

## 一、決定

| ID | 決定 | 理由 | 檢查 |
|---|---|---|---|
| **`NFR5.140`** | C-8 的三個名稱欄位**只**加在 `U2` 的契約模組（`brain_ws_contract.py` 的 `WorkTargetPayload`），重 dump `ws-contract.json`、重產 `ws-contract.d.ts`；前端只經產生的型別讀它們，不另寫手寫 interface | 父條 `NFR5`（WebSocket 契約閘門，`requirements.md:510`）：兩道既有 WS 漂移閘門（CI `ci.yml:305` 的 `dump_ws_contract.py --check`、`:219` 的 `npm run check:ws-types`）只在契約有單一來源時才擋得住；手寫副本即繞過 | 兩道閘門於 `code-generation` 跑綠；`grep -rn "projectName" frontend/src --include=*.ts*` 的型別宣告處只在 `ws-contract.d.ts`；`BR98.4` 的突變（欄位改名 → `npm run build` 紅）結果寫進 `automation-test-plan.md` |
| **`NFR5.141`**（R-07） | 協定維持 `v: 1` 的論證改寫為可執行形式：**在本單元之前前端沒有任何 WS 消費者**（DEMO 頁已隨 `U13` 移除、`backend/services/brain_router.py` 不存在），而後端與前端在同一次部署上線，故欄位增量對 `v: 1` 安全、不需升版。合併前檢查只在**分支上、合併之前**執行（squash-merge 之後 `origin/ut..HEAD` 不再成立） | `functional-spec.md` §二之一第 5 點的「若 `U13` 先於 `U14` 進 `ut`」分支不可滿足（R-07）；本條給出不依賴該分支的論證 | 合併前於分支執行：`git log --oneline origin/ut..HEAD` 同時含 `U13` 與 `U14` 的 commit；`grep -c projectName ws-contract.json` ≥ 1；`test -e backend/services/brain_router.py` 為假。任一不成立即停止合併並回報 |
| **`NFR8.140`** | 本單元**零新環境變數、零 compose 變更** | 父條 `NFR8`（新增元件的部署設定完整性，`requirements.md:537`）：失敗模式無聲，故把「零」寫成可檢查的宣告；`functional-spec.md` §八之三第 5 點已宣告「不新增環境變數」 | `python3 scripts/validate_env_contract.py` 通過；`git diff --stat` 中 `deploy/`、`*.env.example` 零變更 |
| **`EPN-21`** | 前後端**零新依賴** | `team.md` Code Style；`routeWebSocket`、`page.clock`、`emulateMedia` 皆為已安裝 Playwright 的內建 API；後端計數用 SQLAlchemy 內建事件 | `frontend/package.json` 的 `dependencies`／`devDependencies` 鍵集合前後相同（`jq '.dependencies, .devDependencies \| keys'` 比對）；`backend/requirements.txt` 內容不變 |
| **`EPN-22`** | 樁訊框建構器放 `frontend/src/brain/testing/wsFrames.ts`，由既有 `tsc -b` 檢查；不新增 tests 用 tsconfig；以 ESLint `no-restricted-syntax` 限定 `frontend/tests/**` 不得出現含 `type` 鍵的物件字面量（`EPN-19`） | `BR98.4`；R-04 要求機械化；`eslint.config.js` 的 `files: ['**/*.{ts,tsx}']` 已涵蓋 tests 目錄，`globalIgnores` 只排除 `dist`，故新增規則不需改 lint 範圍 | `npm run lint`、`npm run build` 綠；`wsFrames.ts` 不被任何 app 程式 import（`grep -rn "brain/testing" frontend/src --include=*.tsx` 除自身外為 0），故不進正式 bundle |
| **`EPN-23`** | 伺服器 SQL 語句計數（`EPN-06`／`NFR3.141`）用 SQLAlchemy `event.listen(engine, "before_cursor_execute", …)`，`tearDown` 以 `event.remove` 清除 | 先例 `U23` 的 `PPN-22`；SQLAlchemy 已是依賴 | 監聽器的寫（`setUp`）、讀（斷言）、清（`tearDown`）三端皆在同一測試類別內 |
| **`EPN-24`** | 新增測試全部放在 `backend/tests/` 與既有 `frontend/tests/e2e/`，由既有 CI 指令撿到；e2e 分兩層：真實 stack（握手、ready、狀態推送、`prompt_guard`、錯誤呈現、`BR91` 落地、Sidebar）與 `routeWebSocket`（交辦類畫面、關閉碼、退避、對齊時序、未儲存畫布、上限、重連後狀態覆蓋）；真實 backend 重啟不在 e2e 內（`NFR4.140`） | `team.md`：`python -m unittest discover -s tests` 與 `ui-regression` 為現行閘門；`[EP6]`=A；CI 金鑰為空使真實 stack 走不到交辦（`cicd-pipeline.md:82-86`） | 不新增任何 CI job；`.github/workflows/ci.yml` 不因本單元變動；既有 `regression.spec.ts` 保持綠燈 |
| **`EPN-25`** | 新方法命名為 `HierarchyFacade.describe_work_target`，**與 `intent_routing.py:155` 的私有函式 `_describe_work_target` 同名不同義**（後者是 `U11` 把 segment 轉成提示字串）。不改名，但凡以名稱做的機械檢查（grep、ast）必須以 `HierarchyFacade` 的屬性呼叫或完整路徑錨定 | `project.md` 的 `scope-definition:71cb0eeb`：點名識別字前先查是否已被佔用；兩者在不同模組、一個有底線，執行期不衝突，但字串 grep 會互相命中 | `security-requirements.md` 的 `EPN-11a` 擴充靜態鎖時以 `ast.Attribute.attr == "describe_work_target"` 判定，不以字串 grep |
| **`EPN-26`** | `BR98.4` 的突變驗證與本站各條「必須紅燈的突變」在 `tcms-test-cases` 的 `automation-test-plan.md` 逐條記錄 | `project.md ## Mandated` 的 `tcms-test-cases` 必做 3 | `automation-test-plan.md` 對 `security-requirements.md` 與 `performance-requirements.md` 內每個「必須紅燈的突變」各有一列結果 |
| **`EPN-27`** | 前端**不寫死**使用者訊息的字數上限 | 正本為 `session_store.py:113` 的 `DEFAULT_MESSAGE_MAX_CHARS = 4000`，不在 `ws-contract.d.ts` 內；`team.md` 單一真實來源規則禁止無測試鎖的跨語言副本。超長由伺服器回 `error`，`BR92.6` 原樣顯示 | `grep -rn "4000" frontend/src/brain frontend/src/components` 為 0（實際目錄以 `code-generation` 為準） |

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| 前端 unit／component 測試框架（Vitest 等） | `team.md` D 項不採；紀錄 store 與對齊判斷以 e2e 驗證 |
| WebSocket 用戶端套件（如 `reconnecting-websocket`） | 新依賴；退避、抖動與終止碼分流（`EPN-02`／`EPN-03`）約數十行，且須配合 `BR92.5` 的累計時間判準與 4401／4403 分流，套件的預設行為反而要逐項覆寫 |
| 前端狀態管理庫（Redux、Zustand） | 新依賴；`BR93.4` 定為 App 層 Provider |
| 新增 tests 用 tsconfig | `BR98.4` 已排除（`functional-spec.md` §十二 R-01） |
| property-based 測試框架用於本單元 | `security-requirements.md` §七：PBT hard constraint 不適用 |

## 三、為什麼本單元不產出 scalability／reliability／observability

`produces_kinds` 把三份限定為 `[service]`，本單元為 `ui`；但 C-8 有後端變更，故逐份確認是否另有實質內容：

| 文件 | 若產出，內容會是 | 判定 |
|---|---|---|
| scalability | 「名稱查詢的語句數不隨資料量成長」與「每分頁一條連線」 | **已在 `performance-requirements.md` 的 `EPN-01`／`EPN-06` 表達**；另立一份只會重複並在修訂時漂移 |
| reliability | 名稱查詢失敗不阻斷、重連與終止碼、重啟還原 | 已在 `EPN-07`、`EPN-02`／`EPN-03`、`NFR4.140` 表達；本單元**沒有新增進程、佇列、外部依賴或持久化**，無可用性目標可設 |
| observability | 新 log、metric | 唯一新增的是一筆既有白名單內的 WARNING `work_target_names_failed`（`functional-spec.md` §二之一第 3 點），沿用 `U13` 的 `_log` 出口；本站管的是**不得輸出**（`EPN-14`）；無 metric 機制可接 |

## 四、與上游的落差（如實記載，設計檔不回改）

- **`functional-spec.md` §九之一 IAM 列的「不擴大可見範圍」**：由 R-01 裁決收緊為「擁有者範圍 ∩ `U23` 可見性」（`security-requirements.md` §〇、`EPN-11`）。
- **`functional-spec.md` §二之一第 2 點的「範圍」列**只寫擁有者範圍；本站加上可見性判定後，「每組 SQL 語句數」由 ≤ 3 變為 ≤ 4（`EPN-06`）。
- **`functional-spec.md` §二之一第 5 點的「若 `U13` 先於 `U14` 進 `ut`」**：由 `NFR5.141` 的論證取代（R-07）。
- **`rules.md` `BR93.4` 的「以目前使用者 id 為 React key 掛載」**：由 R-03 裁決取代為綁登入／登出事件（`EPN-15`）。
- **`rules.md` `BR97.5` (2) 的無條件改開**：由 R-02 裁決加上未儲存前置條件（`EPN-18`）。
- **`[EP4]` 選項 A 的「對話都在」**（`functional-design-questions.md:147`）：由 `EPN1`=A（2026-10-17T03:08:46Z）改讀為有上限——「最近 500 則都在」，超過時整則移除最舊者並顯示說明（`EPN-04`）；設計檔不回改。

## 五、送審前自檢（七項；四份產出 ＋ 問題檔共用）

> 全部產出寫完後實算，指令與值並列；本站未執行任何測試（限制）。

| # | 自檢 | 結果 |
|---|---|---|
| 1 | **可達性** | `EPN-11` (b) 被移出的建立者：經 `U24` 移出流程（專案另有管理者時允許）或以 ORM 直接構造「`owner_user_id`＝他、無成員列、另有一位成員」；(c) 零成員列以 ORM 建專案不寫成員列；(d) 非擁有者成員以 `U24` 邀請構造；(f) `K2 view` 撤銷以 `role_permissions` 測試資料構造。`EPN-15` 的「user 無 `id`」：`AuthContext.tsx:86` 先 `setUser` 不含 `id` 的物件、`:90-92` `/me` 失敗時保留——以 `page.route('/api/auth/me')` 回 500 即可達。`EPN-18` 的「晚到 `work_target`」：`routeWebSocket` 先拒握手（退避期間使用者編輯畫布）再接受，可達。`EPN-04` 的 501 則：`routeWebSocket` 直接送 501 個 turn，不受伺服器每分鐘 20 則的限制，可達。`EPN-02` 的 60 秒：`page.clock` 快轉，可達。`EPN-03` 的 4400：`ready` 版本不符或直接以 4400 關閉，可達 |
| 2 | **契約端點三問**（範圍：四份產出 ＋ 問題檔） | **可見性閉包**（`EPN-11`）：產生＝`MembershipFacade.project_visibility`；呼叫＝`describe_work_target`（唯一讀取端）；清＝閉包只在該次 `to_thread` 內存活。**注入點**（`EPN-11b`）：擁有＝組裝處（`build_brain_gateway` 的呼叫端或 factory 參數）；讀＝`_names_for`——形狀由 `nfr-design` 定，code-summary 重答三問。**對話紀錄上限**（`EPN-04`）：寫＝附加訊息時檢查長度；讀＝渲染時顯示說明；清＝登入／登出（`EPN-15`）。**turnId 對照**（`EPN-05`）：寫＝首見 turnId；讀＝`BR93.7` 合併；清＝訊息被移除時同步移除、登入／登出——**初稿漏了「訊息被移除時」這一端**，已補進 `EPN-05`。**退避計時器**（`EPN-02`）：寫＝每次失敗排程；讀＝到期發起連線；清＝成功、放棄、卸載、終止碼。**SQL 計數監聽器**（`EPN-23`）：`setUp`／斷言／`tearDown`。出現在少於兩份產出的識別字逐一判定：`EPN-25`／`EPN-26`／`EPN-27` 只在本檔與 `traceability.json`，屬本檔內部決定，非孤兒 |
| 3 | **引用逐字核對（分開驗事實與定位）** | 逐一開檔核對內容與行號：`brain_gateway_rules.py:69-79`（`:70` 每 key 10 條、`:75` 每分鐘 20 則、`:76` 每連線 120 訊框、`:79` 每 key 30 次握手）、`brain_gateway.py:98`、`:130-149`（`_ALLOWED`）、`:1043-1044`、`:1100`、`:1287`、`:1292`、`:1301`、`membership_facade.py:518-532`、`membership_service.py:367-379`（`:368` 「一條 SQL」、`:370-373` `M6`）、`hierarchy_facade.py:238-262`、`test_brain_gateway_limits.py:380-381`、`test_project_visibility_static.py:112`／`:135`／`:162`、`intent_routing.py:155`、`session_store.py:113`、`:117-140`、`redis_gateway.py:103`、`AuthContext.tsx:56`／`:82-93`、`auth-context.ts:29`、`WorkspacePage.tsx:118-121`、`main.tsx:7`、`api.ts:31`、`ci.yml:219`／`:305`、`requirements.md:430`／`:482`／`:500`／`:510`／`:537`／`:563`／`:591`、`functional-design-questions.md:144`／`:147`。**查出並更正兩處**：ADR-0006 表的起始行初寫 `:589`，實為 `:591`；`NFR3.141` 初稿寫名稱查詢「落在 `toFirstContentMs` 之前」，實讀 `:1100` 的計時區間為 `t_classify_end` → `t_first_content`，名稱查詢**在區間之內**，已改寫 |
| 4 | **檔案集合一致性** | 對照同為 `ui` 且有後端變更的 `project-pages-ui/nfr-requirements/`（不計 `reviews/`）：問題檔、performance、security、tech-stack、traceability 五份——**相同**。三份 `[service]` 文件不產出的理由見本檔 §三 |
| 5 | **跨檔傳播（按事實）** | 逐事實 grep 五份檔：①「每段 500 則、`EPN1`=A」——問題檔、performance 前言與 `EPN-04`、security §八 未提（不屬安全）、本檔 §四、traceability `EPN-04` 一致；②「SQL ≤ 4／≤ 12」——performance `EPN-06` 與 §三、本檔 §四、traceability 一致；③「擁有者範圍 ∩ 可見性、不可見三名稱皆 null」——security §〇、`EPN-11`、本檔 §四、traceability 一致；④「清空綁 `login()`／`logout()`、不依賴 `User.id`」——security `EPN-15`／`EPN-15a`、§八、本檔 §四一致；⑤「不設名稱查詢逾時」——問題檔 §一第 2 點、performance `EPN-07` 與 §四一致；⑥「零新依賴、零新環境變數」——本檔 `EPN-21`／`NFR8.140`、traceability 一致 |
| 6 | **可算的數字先算再寫** | `EPN-06`：1＋3＝4；3×4＝12。`EPN-01`：每 key 10 條 ÷ 每分頁 1 條＝10 個分頁。`traceability.json`（`jq` 取得）：`upstream_ids` **11**；`OK` **6**（`NFR2`、`NFR3`、`NFR4`、`NFR5`、`NFR8`、`NFR11`）、`N/A` **5**；繼承子條 **9**（`NFR2.140`／`.141`、`NFR3.140`／`.141`、`NFR4.140`、`NFR5.140`／`.141`、`NFR8.140`、`NFR11.140`），coverage target 的子條集合與三份產出中出現的 `NFR*.14x` 集合相同；`reverse` 孤兒 **29**（三份產出以粗體定義的 `EPN-*`：performance 9、security 13、tech-stack 7），與 `reverse` 的 id 集合以 `comm -3` 比對**零差異**；需求總數 9＋29＝**38** |
| 7 | **ADR-0006 四面向 ＋ PBT** | 見 `security-requirements.md` §六、§七，逐格對照上游 `functional-spec.md` §九之一：IAM **擴充**（理由：R-01 裁決，非重判），Encryption、Network exposure、Audit logging 與上游**相同**；PBT 不適用、與上游一致 |
