# Infrastructure Specification — `U11 intent-router`

> **本單元不新增任何基礎設施元件。** 它是 `in-process`（`K-10`），活在既有的
> backend 容器內。本檔的價值不在「要蓋什麼」，而在**明確記下「什麼都不蓋」這件事
> 是查證過的，不是略過**——以及它確實帶來的三項變更（五個環境變數、一條
> `workflow_dispatch` 量測 job、一處上游前置條件的修正）。
>
> 設計階段：程式／設定片段 ≤15 行，完整 IaC 屬 `code-generation`。

## 零、本檔的上游（九份，逐份記下它給了什麼）

| 上游 | 它給了什麼基礎設施面的輸入 |
|---|---|
| `nfr-design/logical-components.md` | §五 的三件事：不需要新基礎設施元件、新增五個環境變數、新增一條出站連線（**標為待查證**，本站已關閉） |
| `nfr-design/performance-design.md` | P-4 的連線重用（`NFR3.67` 的界線）；§四 的計時標記設計——它讓交接膠水時間**可被量測**，是 `monitoring-design.md` 延遲指標的前提 |
| `nfr-design/security-design.md` | `SEC-2`（入站零增量）定了本檔 Deployment 表的「不暴露 port」列；§二 的日誌白名單定了 `monitoring-design.md` §四 的禁止欄位；§四 的 `router_chat_model` factory 定了 `BRAIN_ROUTER_MODEL` 為獨立變數 |
| `nfr-design/reliability-design.md` | §一 的四個失敗型別定了 `monitoring-design.md` §一 的「失敗率按型別」；§四「不建健康檢查端點」定了本檔不在 compose 加 `healthcheck`；§五 的單一降級路徑定了 `cicd-pipeline.md` §三 的回滾後果分析 |
| `nfr-design/scalability-design.md` | §二「本單元隨 backend 走、無自己的部署單位」直接定了本檔 Deployment 表的「無新增容器」；§五 的 `U8` 讀取負載是本檔共享資源表第二列的來源 |
| `nfr-design/observability-design.md` | §一 的 `RoutingObservation` 型別、§二 的七個訊號、§四 的「無告警通道」——`monitoring-design.md` 是它的平台落地版，§二 的 `Routes to` 欄全部「無通道」即沿用它 |
| `inception/domain-design/components.md`（`:66-90`） | `IntentRouter` 的 `external_dependencies` 列出 **OpenRouter**，`depends_on` 為 `SessionContext`（讀）與 `MemoryStore`（**讀該使用者的語意與程序記憶**）——**後者獨立佐證了 `NFR7.62` 的 `kinds` 排除情節記憶**：網域設計本身就只說語意與程序 |
| `construction/intent-router/functional-design/functional-spec.md` | `W1`–`W8` 的流程定了哪些步驟會產生可觀測事件；§二 的狀態機定了 `refused`（`done`）與 `failed`（`error`）必須在日誌上分得開 |
| `inception/contract-design/contract-summary.md` | `K-10` 的 `in-process` 宣告是「無新增容器」的根據；`K-09`／`K-08` 的消費端清單是共享資源表的根據；`NFR9` 的「上限由 OpenRouter 後台承載」定了本檔不設配額切分 |

## 一、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| **Compute model** | **既有 backend 容器內的一個模組**，無獨立行程 | `K-10` 宣告 `in-process`；`SEC-2` 禁止本單元建立 `APIRouter` 或任何端點 |
| **新增容器** | **無** | 五層分解（`nfr-design/logical-components.md` §一）全部是函式與一個 client factory，沒有任何需要獨立生命週期的東西 |
| **Networking — 入站** | **零增量** | `SEC-2`：不暴露任何 port，不被 `main.py` `include_router` |
| **Networking — 出站** | **零增量（已查證，非推論）** | backend 容器**已經**對 OpenRouter 出站——A1（`design_agent`）、A3（`review_agent`）、C1（`cost_advice_agent`）都經 `langgraph_runtime` 打同一個 base URL。本單元多一條邏輯呼叫，**不新增任何網路目的地或防火牆規則**。這把 `nfr-design` 的 `D-6`（當時只是推論）升為已查證 |
| **Storage** | **零增量** | 本單元無狀態（`NFR4.70`）、不寫任何持久層。它**唯讀**既有的 Redis（`U10`）與 PostgreSQL（`U8`） |
| **Environments** | 本機 dev／CI 測試／部署 staging，**三者維持既有分離** | `project.md` 的 blocking 規則；`validate_env_contract.py` 機械檢查 |
| **IaC approach** | **Docker Compose**（既有），非 CDK／Terraform | ADR-0001／ADR-0002：雲端供應商 production 不在範圍內。本 repo 的部署標的是自架主機 `192.168.10.10`（ADR-0007） |
| **Resource sizing** | **零增量** | 本單元的 CPU 成本是純函式的常數級比較、記憶體無狀態無快取（`nfr-design/scalability-design.md` §三）。真正的資源消耗在外部模型供應商側 |
| **Restart / 生命週期** | 沿用 backend 的 `restart: unless-stopped`（`docker-compose.deploy.yml:83`） | 本單元無獨立生命週期可設定 |

### 唯一的部署面變更：五個環境變數

`[I2]`=A 定案，比照 `U10` 的 `BRAIN_SESSION_HISTORY_MAX` 既有形狀
（`render-env.sh:130` 寫字面值、`.env.example:143` 列它、`compose:130` 消費它）。

| 變數 | `render-env.sh` | `deploy/.env.example` | `compose` | `backend/.env.example` | 缺值行為 |
|---|---|---|---|---|---|
| `BRAIN_ROUTER_MODEL` | `=typesafe/jev-1.13`（字面值） | 列出 | 消費 | 列出 | 取預設 ＋ INFO |
| `BRAIN_ROUTER_TIMEOUT_SEC` | `=5` | 列出 | 消費 | 列出 | 取預設 ＋ WARN |
| `BRAIN_ROUTER_MAX_CALLS_PER_TURN` | `=1` | 列出 | 消費 | 列出 | 取預設 ＋ WARN |
| `BRAIN_ROUTER_MAX_RETRIES` | `=0` | 列出 | 消費 | 列出 | 取預設 ＋ WARN |
| **`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`** | **`=0.7`（字面值）** | 列出 | 消費 | 列出 | **啟動失敗**（`BR3.4`） |

**`[I2]`=A 的理由，寫在這裡以免被讀成「把 required 降級成有預設」**：
應用層**依然 required-no-default**（缺值即大聲失敗，`BR3.4` 逐字「缺值不得以
預設值靜默啟動」成立）；部署層**明確、可見、進版控地**供給它。這與
`BRAIN_SESSION_HISTORY_MAX=200` 是同一個形狀——**不是靜默預設，是顯式供給**。

**為什麼不加進那兩道「不得取預設」的守衛**（`deploy.yml:71-85` ＋
`render-env.sh:57-69`）：那兩道的三個成員（`POSTGRES_PASSWORD`／`JWT_SECRET`／
`REDIS_PASSWORD`）**都是憑證**，而守衛的錯誤訊息逐字在講「`JWT_SECRET` 簽每一個
登入 token，缺了任何人都能偽造 admin session」。混進一個調校參數會讓那段訊息
對不上，而且它仍需要有人去 GitHub 設一個 secret——**把一個應該被看見的數字
藏進 secret**。字面值寫在 `render-env.sh` 裡，改它要走 PR，可稽核；而 `NFR1`
的校正程序本來就要求裁決紀錄寫出新舊對照，用 PR 承載正好。

## 二、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| **（無新增）** | — | — | 本單元不引入任何資料庫／快取／佇列／搜尋／CDN／DNS／LB |
| Redis（既有，`U1`／`U10` 擁有） | cache／session store | 不變 | 本單元**唯讀**，經 `SessionStore`。`BR7.4` 禁止呼叫任何寫入方法 |
| PostgreSQL ＋ pgvector（既有，`U1`／`U8` 擁有） | database | 不變 | 本單元**唯讀**，經 `MemoryFacade.search`，`kinds` 排除 episodic（`NFR7.62`）。**本單元為 `U8` 帶來每輪一次的讀取負載**（`D-4`，`limit` 本站定 5） |
| OpenRouter → `typesafe/jev-1.13`（外部） | 第三方推論 API | `BRAIN_ROUTER_MODEL` 指定；逾時 5 秒；每輪 1 次；0 重試 | **唯一跨信任邊界的依賴**。帳戶額度上限由 OpenRouter 後台承載（`NFR9`），本 intent 不建計量 |

## 三、Shared Infrastructure

本單元**不擁有**任何共享資源，但它**消費**三項。按 stage 檔要求的表格形式：

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| Redis（session） | `U10 session-store`（容器由 `U1 brain-infra` 提供） | `U11`（唯讀）、`U12`、`U13` | `U11` 僅 `SessionStore` 的讀取方法；寫入方法由 `BR7.4` 禁止，並以結構斷言檢查 |
| PostgreSQL `memory` schema | `U8 memory-service`（容器由 `U1` 提供） | `U11`（唯讀）、`U5`、`U9`、`U15` | `U11` 僅經 `MemoryFacade.search`，且 `kinds` 由模組層常數固定為語意／程序（`NFR7.62`） |
| OpenRouter 帳戶額度 | 平台（無單一 owner unit） | A1、A3、C1、`U11` | 每輪 1 次呼叫；無本單元層級的速率限制（`NFR9.62`：達供應商上限即大聲失敗，不排隊） |

**第三列值得一句話**：OpenRouter 額度是**本 intent 之前就已存在的共享資源**，
而本單元是第四個消費者。`NFR9` 已定案「上限由後台承載、不建計量」，所以本站
不設計配額切分——但把它列進共享資源表，是因為**它是唯一一個會被本單元的流量
影響到既有功能（A1／A3／C1）的資源**。
