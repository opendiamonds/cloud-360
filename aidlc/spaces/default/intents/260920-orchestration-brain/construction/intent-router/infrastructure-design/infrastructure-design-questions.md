# Infrastructure Design 問題檔 — `U11 intent-router`

> depth 為 **Minimal**。本單元**不新增任何基礎設施元件**（無新容器、無新 port、
> 無新 volume——`nfr-design/logical-components.md` §五 已定），所以本站的問題只有
> 兩個，而**兩個都是本站實地查證後才浮現的**，不是從上游抄下來的待辦。

## 本站的實地查證（兩題都建立在這些事實上）

| # | 事實 | 取得方式 |
|---|---|---|
| **V1** | **`ci.yml` 全檔 `OPENROUTER` 零命中。** CI 沒有任何一個 job 拿得到金鑰 | `[跑]` `grep -n "OPENROUTER" .github/workflows/ci.yml` |
| **V2** | 現有的 LLM 相關測試**全部用替身**：`test_a3_langgraph_migration.py:6` 檔頭逐字「Mock `ChatOpenAI` / compiled graph; **no real `OPENROUTER_API_KEY`**」、`:95` 以 `side_effect=RuntimeAuthError` 模擬缺金鑰 | `[讀]` 該檔 |
| **V3** | **部署路徑的金鑰是通的**：`deploy.yml:109`／`:577` 從 `secrets.OPENROUTER_API_KEY` 餵入 → `render-env.sh:104` 寫進 `deploy/.env` → `docker-compose.deploy.yml:91` 餵進 backend 容器 | `[讀]` 四處 |
| **V4** | **但它在部署端是 optional**：`render-env.sh:21` 逐字「`OPENROUTER_API_KEY` **optional** A1 design agent; **empty disables generation**」，`:104` 為 `${OPENROUTER_API_KEY:-}`（缺值即空字串，不中斷） | `[讀]` 同檔 |
| **V5** | `ci.yml` 的觸發是**裸 `pull_request`**（無 `paths-ignore`，檔頭有逐字說明為何刻意不加） | `[讀]` `ci.yml:7-11` |
| **V6** | **本 repo 為 public**，而 `project.md` 逐字：「Actions log 公開可讀——**一次意外 echo 即等同公開發布**」 | `project.md ## Mandated` |
| **V7** | `U10` 的同類變數已有完整先例：`render-env.sh:130` 寫**字面值** `BRAIN_SESSION_HISTORY_MAX=200`、`.env.example:143` 列它、`docker-compose.deploy.yml:130` 消費它 | `[讀]` 三處 |
| **V8** | 「不得取預設」的三個 secret 有**兩道**守衛：`deploy.yml:71-85` 的 `Require the secrets that must not default`（workflow 層，容器起來**之前**）＋ `render-env.sh:57-69` 的自有檢查（`:64` 註解逐字說它是 **rollback 路徑上唯一的** missing-value 守衛） | `[讀]` 兩處 |

---

## [I1] `NFR1` 的準確率量測需要真實的 Jev 回應，而 CI 現在沒有金鑰——走哪條路

`nfr-requirements` 的 `TS-6` 已把 `OPENROUTER_API_KEY` 列為 blocking 前置條件，
但當時的描述是「使用者把金鑰寫進 `backend/.env`」。**V1 顯示問題比那個更大**：
`NFR1`／`NFR10`／`OQ-10` 的量測機制落在 `build-and-test`（3.6），而**它在 CI 裡跑，
而 CI 全檔沒有這個金鑰**。本機的 `.env` 不會進 CI。

### 選項

- **A（建議）— 量測不放 `pull_request` CI，改用 `workflow_dispatch` 的獨立 job。**
  在 `ci.yml` 之外新增一個**手動觸發**的 workflow（或在既有 workflow 加
  `workflow_dispatch` 入口），只在那裡注入 `secrets.OPENROUTER_API_KEY`，
  跑 ≥50 筆標註集、輸出準確率與延遲。
  - **安全面**：`pull_request` 觸發的 run **完全不碰金鑰**。V5 顯示 `ci.yml` 是裸
    `pull_request`——雖然 GitHub 對 **fork** 的 PR 本來就不傳 secrets，但**同 repo
    的分支 PR 會拿到**，而任何一個 PR 作者都能在自己的 workflow 改動裡 echo 它。
    V6 逐字：一次意外 echo 等同公開發布。手動觸發把「誰能跑」收斂到有權限的人。
  - **成本面**：≥50 筆標註集每跑一次就是 50 次付費呼叫。綁在每個 PR 上等於每次
    推送都付一次，而**那個數字不會因為改了一行前端而改變**。
  - **代價**：它不是自動閘門——有人必須記得去按。處置是把它寫進
    `build-and-test` 的核可關卡（該站本來就要裁決 `0.7`／`80%` 的校正）。
- **B — 直接把 `secrets.OPENROUTER_API_KEY` 加進 `ci.yml` 的 backend job。**
  - **好處**：`build-and-test` 變成真正的自動閘門，每個 PR 都驗。
  - **代價**：①同 repo 分支的 PR 都拿得到一個付費金鑰，而 V6 的風險是公開發布；
    ②每個 PR 付 50 次呼叫的錢；③fork 的 PR 拿不到金鑰 → 那些 PR 的量測會
    **靜默跳過或紅燈**，而「有時驗有時不驗」的閘門比沒有閘門更難解讀。
- **C — 在自架 runner 上跑（`deploy.yml` 已在用的那台）。**
  V3 顯示部署路徑的金鑰已經通了，且 runner 是 `[self-hosted, linux, x64, cloud360]`。
  - **好處**：金鑰不需要再多暴露一處。
  - **代價**：那台 runner 的 `concurrency` 是 `deploy-10-10` 且
    `cancel-in-progress: false`——量測若跑在上面會與部署互卡。且它目前只在
    merge 到 `ut` 之後才動，等於量測只在**合併後**才跑，失去 PR 階段的回饋。
- **D — 本站不決定，維持 `TS-6` 現狀（只記為 blocking 前置條件）。**
  - **代價**：`TS-6` 目前的描述建立在「寫進 `backend/.env`」上，而 V1 證明那對 CI
    無效。不修正它等於讓一個**已知錯誤的**前置條件描述留在交接表上。

[Answer]: A（`workflow_dispatch` 手動觸發的獨立 job，`pull_request` 不碰金鑰）
<!-- answered 2026-10-10T01:05:44Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## [I2] `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` 缺值會讓 backend 啟動失敗——守衛放哪一層

`BR3.4` 逐字「缺值**不得**以預設值靜默啟動」，所以 `tech-stack-decisions.md` 的
`TS-4` 定它 **required、無預設**。後果：若 `deploy/.env` 沒有它，
**`docker compose up` 會成功、backend 容器會起來然後 crash-loop**。

V7 給了一個現成先例（`BRAIN_SESSION_HISTORY_MAX=200` 直接寫字面值），
V8 給了另一條路（加進兩道「不得取預設」的守衛）。

### 選項

- **A（建議）— 比照 `V7`：`render-env.sh` 寫字面值 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD=0.7`，不加進 secret 守衛。**
  - **理由**：它**不是 secret**，是一個調校參數。V8 的兩道守衛是為了
    「沒有它系統就不安全」的憑證（`JWT_SECRET` 缺了會用公開 fallback key），
    把一個門檻值放進去會稀釋那道守衛的語意。
  - **`BR3.4` 仍然成立**：應用層依然 required-no-default（缺值即大聲失敗），
    而部署層**明確、可見、進版控地**供給它——這正是 `BRAIN_SESSION_HISTORY_MAX`
    的既有形狀，不是「靜默預設」。
  - **改門檻的方式**：改 `render-env.sh` 的那一行並走 PR，**可稽核**。
    而 `NFR1` 的校正程序本來就要求裁決紀錄寫出新舊對照——用 PR 承載正好。
  - **代價**：不能在不改 code 的情況下換門檻（例如在 runner 上臨時改 env）。
- **B — 加進 `deploy.yml:71` 與 `render-env.sh:57` 的「不得取預設」守衛。**
  - **好處**：缺值時在**容器起來之前**就失敗，不是 crash-loop。
  - **代價**：那兩道守衛目前的三個成員都是**憑證**，而守衛的錯誤訊息逐字在講
    「`JWT_SECRET` 簽每一個登入 token，缺了任何人都能偽造 admin session」。
    混進一個調校參數會讓那段訊息對不上。且它仍需要有人去 GitHub 設一個 secret，
    而門檻值放進 secret 是把一個**應該被看見**的數字藏起來。
- **C — A ＋ B 都做**（寫字面值，同時加守衛）。
  - **代價**：守衛永遠不會觸發（字面值保證它存在），是一條死碼——
    `project.md` 記過「不可達的規則是死碼，卻在文件上長得像已解決」。
- **D — 維持 required-no-default 且**不**在 `render-env.sh` 寫它，靠 crash-loop 暴露。
  - **代價**：部署會「成功」而服務起不來，這正是 `NFR8` 逐字要防的無聲失敗形狀
    （既有實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，圖示靜默退回灰底）。
    差別只在於這次不是靜默降級而是 crash-loop——**比靜默好，但仍然比「部署前就擋下」差**。

[Answer]: A（`render-env.sh` 寫字面值 `0.7`，不加進 secret 守衛）
<!-- answered 2026-10-10T01:05:44Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## 本站自行定案、不提問

| # | 決定 | 理由 |
|---|---|---|
| 1 | **不新增任何基礎設施元件**（容器／port／volume／網路） | `nfr-design/logical-components.md` §五 已定；本單元 `in-process`，活在既有 backend 容器內 |
| 2 | **egress 零增量**（`D-6` 的查證項） | V3 證實 backend 容器**已經**對 OpenRouter 出站（A1／A3／C1 都在用，同一個 base URL）。本單元多一條邏輯上的呼叫，但**不新增任何網路目的地或規則**。`D-6` 由「推論」升為**已查證** |
| 3 | 其餘四個 `BRAIN_ROUTER_*` 變數比照 `V7` 的形狀寫進三處 | `NFR8.61` 的三處同步義務；`validate_env_contract.py` 會機械檢查 |
| 4 | **不新增 CI job**（除了 `[I1]` 的結果可能帶來的那一個） | 本單元的測試（純函式 PBT、替身、解析層）全部跑在既有 `backend` job 內，零新依賴 |

## 上游已定案、不重問

| 事項 | 出處 |
|---|---|
| 路由層模型＝`typesafe/jev-1.13`；`OQ-10` 承接 `build-and-test` | `nfr-requirements` 的 `[N1]`／`[N3]` |
| 五個環境變數與其缺值行為 | `tech-stack-decisions.md` 的 `TS-4` |
| 無告警通道（沿用 `U10` 的 `OPEN-N10-4`，不開第二個同義缺口） | `nfr-design/observability-design.md` §四 |
| 不引入 tracing 套件 | `nfr-design/observability-design.md` §三（審查已複驗四跳全同進程） |
