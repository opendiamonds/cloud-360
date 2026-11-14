# Security Requirements — `U24 member-pages-ui`

> 本檔為本站的 **review artifact**。
>
> **識別字**：可誠實繼承 inception NFR 的用 `NFR<parent>.80+`；其餘以
> `SEC-U24-n` 宣告為孤兒（形狀沿用 `U11` 那站的 `SEC-1`–`SEC-5`）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/functional-design/functional-spec.md` | §三 的可見性規則、§四 的六個端點、§九之二 的 ADR-0006 四面向 |
| `construction/member-pages-ui/functional-design/rules.md` | `BR22.1`／`BR22.3`／`BR26.1`／`BR27.2`／`BR28.1` |
| `inception/requirements-analysis/requirements.md` | `NFR4`／`NFR7`／`NFR8` 的逐字原文 |
| `inception/contract-design/contract-summary.md` | `K-16` 的 `authorization_model`、`residual_gap`、不變量 `I-5` |

## 一、ADR-0006 security baseline 四面向（逐項判定，**不留空白**）

**不沿用任何上游表格的判定欄**——本單元的範圍與 `U19` 不同。

| 面向 | 判定 | 本單元的處置 |
|---|---|---|
| **IAM** | **適用** | 四個管理者控件的可見性**一律依伺服器回傳的 `role` 結論**（`BR22.3`），前端不得由全域角色推導（不變量 `I-5`）。能力層可見性沿用既有 `CapabilityRoute`（`RouteGuard.tsx:35`）。**殘留缺口**：`K-16` 的 `residual_gap` 逐字「沒有機制擋住前端自己猜」，本單元只能把它寫成可審查的條文 ＋ 一條會紅的 e2e（`BR22.3` 的 observable），**無機械強制** |
| **Encryption** | **不適用** | 零新傳輸通道、零新儲存。**特別是：本單元不得使用任何瀏覽器儲存**——`AC12.4.4` 要求橫幅已讀狀態跨裝置一致，故它必須在伺服器（`BR26.1`／`SEC-U24-2`） |
| **Network exposure** | **不適用** | 零新端點、零新進程邊界。六個消費點全部是 `U19` 已交付的既有端點（實測 `membership_router.py`） |
| **Audit logging** | **適用** | `AC12.2.2` 的變更紀錄是**使用者可見**的稽核面，本單元只渲染、**不自行記錄任何稽核事件**。另：本單元的 console 輸出受 `SEC-U24-1` 限制。**本站查證後的更正**：原寫「資料由 `U19` 的持久層提供」只對了一半——資料**存在**（`reselection_events`，`U19/[FD3]=A` 把兩類變更都收進該表），但**沒有任何端點或 facade 方法可以取它**（六個路由、**17 個** facade 方法逐一核對——`grep -c '^    def '` = 17，其中公開 12、`__init__` 與四個 `_` 前綴共 5；另模組層函式 1。見 `performance-requirements.md` §五之一。**審查 `R-04` 第二輪更正**：原寫「13 個」，那是舊 regex 的輸出；`R-04` 的 Location 欄指名了兩個落點，我第一輪只改了 `performance-requirements.md` 那一處，正是 `project.md` 的 `refined-mockups:a33fc270` 記過的形狀）。故這個稽核面目前**在前端不可達**，列為 `OPEN-MP24-7`。不把「表裡有資料」寫成「稽核面已具備」 |
| **PBT hard constraint** | **不適用** | ADR-0006 點名的三個落點（IaC generator／cost calculator／agent routing）皆非本單元；前端無 unit／PBT 框架（`team.md` 既成事實），唯一自動化層是 Playwright e2e |

## 二、可繼承 inception NFR 的要求

| ID | 要求 | 可測不變量 | 父條與繼承理由 |
|---|---|---|---|
| `NFR4.80` | 本單元**不得**把任何狀態放進瀏覽器儲存（`localStorage`／`sessionStorage`／`IndexedDB`） | AST／原始碼掃描：三個識別字在本單元的檔案中命中數為 **0** | `NFR4`（狀態外部化，逐字「一律放 Redis，不得放行程記憶體」）。前端的同構對應是「不得放瀏覽器儲存」——`AC12.4.4` 的跨裝置語意只有伺服器端持久化能滿足 |
| `NFR8.80` | 本單元**不新增任何環境變數**，故 `render-env.sh`／`deploy/.env.example` 的同步義務對本單元為**空集合** | `git diff` 顯示本單元未改動該兩檔 | `NFR8`（新增元件的部署設定完整性）。父條的失敗模式逐字是「無聲降級」；本單元零新變數，故該失敗模式不可達——這是**結構性滿足**而非豁免 |

## 三、本單元自有的安全要求（孤兒，無 inception 父條）

| ID | 要求 | 可測不變量 |
|---|---|---|
| `SEC-U24-1` | 任何 console 輸出**不得**含使用者輸入、顯示名稱或專案名稱；只許例外型別名稱與端點標識 | e2e 以 `page.on('console')` 擷取輸出，觸發各錯誤路徑後不含測試資料的任何字串（`BR28.1`） |
| `SEC-U24-2` | 橫幅已讀狀態以**事件**為鍵寫在伺服器；**不得**為 per-user 布林值、**不得**放瀏覽器儲存 | 換瀏覽器重新登入後橫幅不再出現；同一人第二次被改選時橫幅**再次**出現（`BR26.1`） |
| `SEC-U24-3` | 前端**不驗**受邀者的全域功能權限；一律交由伺服器回 422 | 選任何受邀者時送出鈕都不因權限而停用（`BR27.2`） |
| `SEC-U24-4` | 422 的 `detail` **非字串**時不得當文案渲染 | 以列舉外的角色值送出 → 畫面不出現 `[object Object]` 或 JSON 片段（`BR23.1`） |
| `SEC-U24-5` | 四個管理者控件在「本專案一般成員」身分下**全部不存在** | 以一般成員開啟成員頁 → 四個控件皆 0 命中；竄改 `list_members` 回應中自身那列的 `role` 為 `member` → 同樣 0 命中（`BR22.3`） |

### 三之一、`SEC-U24-5` 是 `[D9]`=A 的唯一可失敗落點

`[D9]`=A（一般成員看唯讀清單）在本單元的 `functional-design` 初版**零可驗證機制**
——審查 `R-01` 查出 `BR22.1` 的 observable 綁在 403 上，而「是成員但非管理者」
拿到的是 **200**，該斷言永不觸發。修訂 1 以 `BR22.3` 補上取得方式之後，
`SEC-U24-5` 的第二句（竄改回應）才成為那條已核可決定的**會紅的斷言**。

### 三之二、`SEC-U24-6` — `[N3]`=B 的**肯定**義務（審查 `R-02` 補）

`[N3]`=B 的作答逐字是「**只記 console（型別名稱與端點標識，不含使用者文字）**」。
那是一個**肯定義務**（要記什麼），而本檔原先只落下 `SEC-U24-1` 的**禁令**
（不得含使用者文字）——該禁令在上游早已由 `BR28.1` 定案，並列在問題檔 §一
「本站不重問」。後果可機械判定：**完全不輸出任何 console 即滿足 `SEC-U24-1`**，
故原產出無法區分 `[N3]`=A（不產生任何訊號）與 `[N3]`=B。

| ID | 要求 | 可測不變量 |
|---|---|---|
| `SEC-U24-6` | **兜底規則（審查 `R-07` 補）**：本單元**每一條對使用者無聲的失敗路徑**都必須輸出一筆 console 訊號，內容**限於**型別名稱與端點標識。已點名的三條為最低限度：① 成員清單抓取失敗（`fetch-failed`）、② **橫幅查詢的任何非 2xx 與網路失敗**（含 403，但不只 403）、③ 邀請收到 422 的**物件陣列**型 `detail`（`BR23.1` 的驗證錯誤分支） | e2e 以 `page.on('console')` 收集輸出：構造三種失敗後各斷言**至少一筆**相符訊號存在（缺一即紅燈），**且**斷言該筆訊號不含受測帳號的 `display_name` 與 email（`SEC-U24-1` 的另一面）。②的構造以 stub 回 403 與 500 各一次，兩者皆須有訊號 |

**這個選項的代價，逐字寫進產出而不只留在問題檔**：`[N3]`=B 的選項文字逐字為
「生產環境沒有人在看 console，等於只對開發期有用」。本 intent 至今無任何
dashboard 或告警通道（`U10` 的 `OPEN-N10-4`），故 `SEC-U24-6` 的實際消費者是
開發者的 devtools 與 e2e 斷言——**不把「有 console 訊號」寫成「有監控」**。
選它而非 `[N3]`=C 的理由也在選項裡：C 會讓本單元新增一個對外請求與一個端點依賴，
推翻「零新端點、零新持久層」這條結構宣稱。

附帶：`construction.md` 的 phase guardrail 逐字「Errors must be surfaced to the
caller or logged — silent failures are not acceptable」，而本站是 `[N3]` 的唯一落點，
故這條肯定義務不是可選的加分項。

**為什麼是兜底規則而不是三條列舉（審查 `R-07`）**：`rules.md` 的 `BR21.3` logic 逐字為
「IF 回應為 403（缺 K3 view）THEN 視為永久失敗……ELSE IF 抓取因其他原因失敗 THEN
宿主保持空、不顯示錯誤、下次落地重試。**兩種情形皆不對使用者顯示任何錯誤訊息**」
——所以橫幅的**網路錯誤與 5xx** 對使用者同樣無聲。初版只為 403 訂了 console 義務，
於是那些路徑**同時**滿足 `SEC-U24-1`（禁令）與初版的 `SEC-U24-6`（三條之外），
構成 phase guardrail 逐字禁止的 silent failure。**這正是 `R-02` 的修法要消除的那一類缺陷，
而我用列舉三條的方式收尾又留下了同一類殘留**——列舉型要求若沒有兜底句，
沒被點名的路徑就是新的靜默面。

## 四、STRIDE 速查（本單元的攻擊面只有一個：瀏覽器端的渲染判定）

| 類別 | 本單元是否引入新面 | 處置 |
|---|---|---|
| Spoofing | 否 | 身分由既有 `ProtectedRoute`／JWT 承載，本單元不處理身分 |
| Tampering | **是**（唯一一項） | 攻擊者可竄改 `list_members` 的回應使前端誤顯示管理者控件。**但那不構成授權提升**：四個端點的授權判定全在 `U19`，點了也會被拒。`SEC-U24-5` 把它變成可斷言的 |
| Repudiation | 否 | 變更紀錄由 `U19` 持久化 |
| Information disclosure | **是** | console 與錯誤訊息。處置為 `SEC-U24-1`（本 repo 為 public、Actions log 公開可讀） |
| Denial of service | **否（但有一項已揭露、未設界的負載）** | **判定依據**：本單元不新增端點、不新增任何可被匿名觸發的路徑，六個消費點全部要求已驗證身分（`require_story_action`），故不構成可被外部放大的 DoS 面。**但本站新定的 `UIP-2`（`[N2]`=A）確實對一個既有端點新增負載**：橫幅查詢每次 `Layout` 掛載各一次、刻意不快取，請求量與使用者換頁頻率成正比且**本站未為它設界**——該選項逐字揭露的代價是「換頁密集時的固定請求開銷，且該端點對多數使用者永遠回空陣列」。縮小範圍的既有機制只有 `BR21.3`（缺 `K3 view` 的三個角色 0 次）。判定維持「否」的理由是**負載來自已驗證使用者的正常操作、且上界由人的換頁速度決定**，不是沒有負載。**審查 `R-06` 更正**：原理由只答了渲染成本與新端點，沒答本站剛定下的請求量 |
| Elevation of privilege | 否 | 見 Tampering——前端的顯示判定不是授權判定 |

## 五、送審前自檢（七項，**逐項報告結果**）

依 `project.md`：六項送審前自檢 ＋ 第七項（逐一對照本專案 hard constraint）。
**沒有出現在這張表裡就等於沒跑。**

| # | 自檢項 | 本站結果 |
|---|---|---|
| 1 | **可達性**——每條「偵測 X 狀態」的規則先驗 X 可達 | **查出一項不可達**。`UIP-5`（變更紀錄 100 列上限）的量測需要一條把紀錄取回前端的路徑，而該路徑不存在（§五之一）。已分開記載「參數已定案」與「尚不可量測」，不用前者蓋掉後者。其餘要求逐條可達：`UIP-1`／`UIP-3`／`UIP-4` 以 Playwright 攔截請求可驗、`UIP-2` 的兩個分支（有／無 `K3 view`）皆可構造、`NFR4.80`／`NFR8.80` 為可 grep 的零命中斷言 |
| 2 | **契約端點三問**（每個欄位誰寫／誰讀／誰清；每個方法誰擁有／誰呼叫）——**範圍是整站全部產出** | **四項狀態逐一指名，查出一腿懸空**。① 橫幅已讀 `acknowledged_at`：寫＝`POST /reselections/{id}/acknowledge`（`membership_router.py:328`），讀＝`GET /reselections/pending`（`:309`），清＝**不清**（`schema_rbac.sql` COMMENT 逐字「the row is never deleted」）✅。② 成員列：寫＝`invite_member`（`membership_facade.py:224`），讀＝`list_members`（`:206`），清＝`remove_member`（`:270`）✅。③ **變更紀錄列：寫＝`change_role`（`:313`，逐字 `cause=membership_service.CAUSE_MANUAL_ROLE_CHANGE`）與 `run_auto_reselection`（`:497`），唯一建構點 `membership_service.py:472`；讀＝無任何可達路徑 ❌** → `OPEN-MP24-7`。④ `UIP-2` 的「不快取」刻意無狀態，無三問標的 |
| 3 | **引用逐字核對**——每個來源標籤開檔驗證（**事實與定位分開驗**） | **全部實開驗過，且本輪的數字全部由下列指令直接輸出**（審查 `R-04` 更正：原表把 `grep -cE '^[[:space:]]{0,4}def [a-z]'` 的結果 **13** 描述成「頂層 `def` 計數」，而頂層 `def` 實為 **1**——那個 13 是「公開方法 12 ＋ 模組層函式 1」的和，描述與指令不符）。`user_router.py:146-147` = `DEFAULT_PAGE_SIZE = 20` ／ `MAX_PAGE_SIZE = 100` ✅。`grep -cE '^@router\.(get\|post\|patch\|delete\|put)' backend/services/membership_router.py` = **6** ✅。`grep -c '^    def ' backend/services/membership_facade.py` = **17**（其中 `grep -cE '^    def [a-z]'` 公開 **12**、`__init__` 與四個 `_` 前綴共 5），另 `grep -c '^def '` 模組層 **1**（`guard_report`）——**覆蓋宣稱改為 17 個方法全部核對**（`:88`–`:497` 逐一讀過方法名與簽章；審查獨立複驗同一結論）。`grep -c 'the row is never deleted' schema_rbac.sql` = **1**（`:679`）——**此處維持原值**：審查 `R-04` 回報 2，但那是較寬的片語 `never deleted`（`grep -c` = **2**）的結果，本表引用的是加引號的完整句。**審查的附帶發現有用且已採納**：第二處 `:663` 逐字「There is deliberately NO retention period here (unlike memory.memory_audit_events, NFR7.2) … the event row itself is never deleted. Do NOT add a 90-day purge」，是比 `:679` 更直接的保存期限依據，已補引於 `performance-requirements.md` §五 |
| 4 | **檔案集合一致性**——同類單元之間 diff 產出檔清單 | **本單元的四份是唯一組合，且有依據**。同 intent 的 15 個單元中，`service` 類（`intent-router`／`membership-service`／`memory-service`／`session-store`／`hierarchy-service`）各有七份；`data`／`library` 類（`memory-data`／`project-meta-data`／`brain-infra` 等）只有 security ＋ tech-stack ＋ traceability。本單元是**唯一**有 `performance-requirements` 而無 scalability／reliability／observability 的——正是 `produces_kinds` 對 `ui` 的字面結果（performance 為 `[service, ui]`，其餘三份為 `[service]`），不是漏寫 |
| 5 | **跨檔傳播**——列出改動的**事實**，每個事實用它的幾種表達形式各 grep 一次 | **四個事實各掃一次，數字由指令輸出**（審查 `R-04` 更正：原表的「問題檔 1 ＋ performance 8 ＋ security 1 ＋ tech-stack 2」四個數字**兩種計數法都重現不了**——它們來自一個多分支 `grep -o '100 列\|100 筆\|MAX_PAGE_SIZE\|最多 100'`，而**多分支 `-o` 回報的是哪個分支先出現，不是哪些分支存在**；我在 `user-stories` 那站才為同一個陷阱寫過教訓，這次又踩）。A「變更紀錄資料由 `U19` 持久層提供」舊說法殘留 = **0**；B 含「100」的**行數** = 問題檔 **3**／performance **12**／security **3**／tech-stack **3**（出現次數：questions **5**、performance **17**、tech-stack **3**；**security 一欄刻意不寫固定值**——理由見下。審查 `R-04` 第二輪更正：原寫 3，那是**行數**不是出現次數，而我在同一列宣稱數字「由指令輸出」。**為什麼 security 不寫固定值**：本檔就是記載這個計數的地方，所以每次更正這一行都會讓 `grep -o '100' security-requirements.md` 的結果再加一——第一次改完是 6，寫上 6 之後變 7。這是自我指涉，寫任何定值都會在寫下的同時失效。正確的做法是給指令而非給值：`grep -o '100' security-requirements.md \| wc -l`，讀者自行執行。其餘三欄不含自我指涉，故給定值），語意一致；C「200 列」殘留 = **4**（問題檔 2 ＋ performance 1 ＋ security 1），逐處判讀後全部刻意保留（原選項文字不改寫、更正註解、產出內對該更正的說明、以及本列自身的記述）；D 端點數 **6** 與 facade 方法數 **17** 在各處一致 |
| 6 | **可算的數字先算再寫** | **本輪全部重跑於最後一次內容改動之後**（`user-stories:78ffe68d`：計數是收尾動作）。`traceability.json`：`coverage` **11** 列（OK **3**／N/A **8**）、`upstream_ids` **11**、`reverse` **17** 列。識別字集合：`UIP-1`…`-5`（**5**）、`SEC-U24-1`…`-6`（**6**，`-6` 為審查 `R-02` 新增）、`TS-U24-1`…`-7`（**7**）、`NFR4.80`／`NFR8.80`／`NFR11.80`／`NFR11.81`（**4**）、`OPEN-MP24-1`／`-3`／`-6`／`-7`（**4**）、`HO-U24-1`…`-3`（**3**）。`reverse` 為 17 而非 18 仍是**刻意**的：`TS-U24-7` 不是孤兒（它是 `NFR8.80` 的依據，已在 `coverage` 段），理由寫在 `tech-stack-decisions.md` §一之一。**審查 `R-04` 的教訓已內化為做法**：自檢表的每個數字都附產生它的指令，不再由我讀完輸出再手寫 |
| 7 | **逐一對照本專案 hard constraint**（ADR-0006 四面向 ＋ PBT） | **§一 的五列表格即為此項**，四面向逐項判定無空白、PBT 另列一行。本站**不沿用** `U19` 的判定欄（範圍不同）；與上游 `requirements.md` 的判定不同處已逐格比對——`Encryption` 在上游判「適用」而本單元判「不適用」，差異原因是**範圍**，不是覆蓋：上游那張表共有**兩**列 Encryption——`requirements.md:598` 的「適用」理由是 `NFR7`（episodic memory 的靜態與傳輸加密），`:618` 的「適用（新增一處）」理由逐字是 **`FR11.5` 的 `C-T11`：MCP 傳輸層承載使用者 token**。兩者都落在伺服器側與 `U11`／記憶層，而本單元零新儲存、零新傳輸通道、六個消費點全是既有端點。依 `user-stories:d0658da6` 的教訓，差異不靜默覆蓋而寫出理由。**附帶一則本站查出的更正**：本輪自檢第 3 項開檔核對時發現，先前站引用的 `requirements.md:606` 行號**已失效**（該行現為一段審查敘述），正確行號是 `:598` 與 `:618`。事實對、定位錯——正是 `feasibility:cb353d32` 記過的形狀，故在此更正並寫明 |

### 五之一、五支宣告 sensor 的實測結果

`stage-graph.json` 對本站宣告的是**五支**：`required-sections`／`upstream-coverage`／
`linter`／`type-check`／`traceability`。

| sensor | 結果 |
|---|---|
| `required-sections` | `pass: true` × 3，findings 0。**收尾重算的 h2 數**：performance **6**、security **6**、tech-stack **5**（`grep -c '^## '`）。審查 `R-04` 更正：原表寫 security=5、tech-stack=4，那是**附加本節與交接事項之前**跑的 sensor 輸出——數字沒造假，但它是舊的，而舊數字與錯數字在文件上長得一樣 |
| `upstream-coverage` | `pass: true`，`unreferenced: []`，findings 0（`--consumes` 用 artifact slug、`--deliverables` 用檔名 stem） |
| `traceability` | `pass: true`，gaps／orphans／invalid 全空，findings 0 |
| `linter` | **`no-eslint-config`** — 工具不可用（設定檔在 `frontend/`），**不是 pass** |
| `type-check` | **`no-tsconfig-found`** — 同上，**不是 pass** |

後兩支在本站結構上不適用：四份產出全為 `.md`／`.json`，本站產出**零個**
`.ts`／`.tsx`／`.py` 檔。如實記載 tool-unavailable，不寫成通過。
