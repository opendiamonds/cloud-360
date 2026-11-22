# CI/CD Pipeline — `U10 session-store`

> 本檔是本站的 **review artifact**。
> 本單元**不新增任何 CI job**；它新增的是**一個部署後驗證步驟**與三項既有閘門的
> 新義務。下方逐項指名。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `reliability-design.md` | `NFR4.50`–`NFR4.57`：`noeviction`、還原五項、失敗分類 |
| `security-design.md` | Lua 的 ACL 前提（列為部署時查核項）；日誌禁令 |
| `observability-design.md` | `NFR4.64` 的還原驗證形狀與「重啟對象是 Redis 不是 backend」 |
| `performance-design.md` | 連線池與逾時參數——它們是部署設定的一部分 |
| `scalability-design.md` | `maxmemory` 與容器上限的連動關係 |
| `logical-components.md` | 模組分解——決定哪些既有閘門會碰到本單元 |
| `components.md` | `SessionContext` 的元件定位 |
| `functional-spec.md` | `W1`–`W8`；`EC3` |
| `contract-summary.md`（`K-01`） | 環境變數契約與 `render-env.sh` 的唯一產生點規則 |

## 一、既有的七個 CI job（實讀 `.github/workflows/ci.yml`）

| job id | name | 本單元會不會碰到它 |
|---|---|---|
| `gate` | Sync write-back gate | 否 |
| `repo-contract` | Repository contract | **是** — `validate_repo_contract.py` ＋ **`validate_env_contract.py`**。本單元的新環境變數必須通過後者 |
| `frontend` | Frontend (lint + typecheck + build) | 否（本單元零前端面） |
| `backend` | Backend (import + unit tests) | **是** — 新模組必須可 import；新測試會被 `python -m unittest discover` 撿到 |
| `memory-schema` | Memory schema (real PostgreSQL) | 否 — 本單元不碰任何 schema |
| `concurrency` | Concurrency (real PostgreSQL row locks) | 否 — 本單元的並發落在 Redis，不是 PostgreSQL row lock |
| `docker-build` | Docker images build | **是** — 新增 Python 依賴會改變 image 建置 |

**三個會碰到，四個不會。** 逐項列出的理由是：下一個人改本單元時要知道
**哪三個會紅**，而不是把七個全部當成相關。

### `concurrency` job 名稱的窄化風險（承 `memory-schema` 的既有先例）

`ci.yml` 對 `memory-schema` 有一段逐字註解說明「這個 job 的 id 與 name 現在都比它的
內容窄」，並刻意不改名（因為 branch protection 的必要檢查引用 name）。
**本單元的 Redis 並發不屬於 `concurrency` job**——該 job 的 name 逐字是
「Concurrency (**real PostgreSQL row locks**)」。把 Redis 的並發測試塞進去會讓
同一個名稱第二次失真。本單元**不這麼做**，此處明記以免下游誤為省事。

## 二、本單元對既有閘門的三項新義務

| # | 義務 | 由哪個閘門擋 | 失敗長什麼樣 |
|---|---|---|---|
| 1 | 新環境變數必須由 `render-env.sh` 寫、`deploy/.env.example` 與 `backend/.env.example` 列 | `repo-contract` 的 `validate_env_contract.py` | CI 紅燈，訊息指名缺哪一邊 |
| 2 | 新 Python 依賴進 `requirements.txt` | `backend`（import smoke）＋ `docker-build` | import 失敗或 image 建置失敗 |
| 3 | 新模組的單元測試被既有的 `python -m unittest discover -s tests` 撿到 | `backend` | 測試紅燈 |

**第 1 項是 blocking 且失敗模式無聲**（若繞過閘門）：`NFR8` 逐字引述既有實例
——`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖 icons 靜默退回
灰底佔位圖。本單元的同形風險是：上限參數若給了預設值，服務正常啟動、功能正常、
記憶體慢慢漲。`BR3.5`／`NFR8.40` 的「無預設值」就是為了讓它變成大聲失敗。

## 三、部署後的還原驗證（`[I1]`=B 的落地形狀）

**放在 `deploy.yml` 的部署後檢查序列中**，與既有的
`Verify the Redis ACL actually took effect`（`deploy.yml:195`）同類——該步驟是本
形狀的現成先例。

### 步驟設計

| # | 動作 | 斷言 |
|---|---|---|
| 1 | 以 app ACL 身分寫入一個 fixture session：三段皆存在、各有數則訊息、**各有不同的作業對象**、`pageModes` 其中一鍵為 `isolated`、TTL 已被續期過 | 寫入成功 |
| 2 | 讀回並記錄五項基準值 ＋ 當下剩餘 TTL | — |
| 3 | **重啟 redis 容器**（`docker compose restart redis`），等 healthcheck 轉綠 | healthcheck 通過 |
| 4 | 逐項讀回比對 | `NFR4.53` 三段皆在；`NFR4.54` 每段訊息與順序相同；`NFR4.55` 每段各自的作業對象相同；`NFR4.56` `pageModes` 兩鍵相同；`NFR4.57` 剩餘 TTL **落在區間內**（不是滿額、不是 0） |
| 5 | 刪除 fixture session | — |

**第 4 列的 `NFR4.56` 是最容易漏的一項**——`pageModes` 是指標不是資料，
而指標錯了的徵兆是「使用者回來時該頁讀到錯的段」，不是「資料不見了」。

**第 4 列的 `NFR4.57` 必須是區間而非等值**：重啟需要時間，TTL 會少掉那幾秒。
斷言等值會讓這個檢查變成不穩定的；斷言「< 原值且 > 原值 − 寬限」才是對的。

### 三項必須寫進產出的代價

1. **它不是 PR 閘門。** 壞掉要等合併後才知道。本專案是 deploy-on-merge，延遲是
   分鐘級，且 `deploy.yml` 已有 rollback job（還原 last-good、開 revert PR、
   dispatch Deploy Doctor）。
2. **重啟 redis 會讓當下在用 staging 的人掉 session。** 這一條不是理論上的——
   `cloud360.danniel.cc` 經 Cloudflare Tunnel 對外，可能有人正在用。
   **緩解**：該步驟放在部署序列中**已經重啟過整個 stack 之後**的位置，
   此時 session 本來就剛被打斷過，額外的一次重啟不新增使用者可感知的損失。
3. **失敗時的行為必須與既有部署後檢查一致**——即讓 deploy job 失敗並觸發既有的
   rollback job。**不得**寫成「記 warning 繼續」：那正是 `project.md` 一再記載的
   `except Exception: logger.warning` 形狀。

## 四、部署策略與回滾

| 面向 | 內容 | 來源 |
|---|---|---|
| 部署策略 | **Recreate**（`docker compose up` 重建受影響容器） | 既有 `deploy.yml` 的形狀；`infrastructure-guide.md` 的 Recreate 列逐字「Simple, no version mixing / Downtime during transition」——本專案接受該停機窗口 |
| 觸發 | PR merge 到 `ut`，或 `workflow_dispatch` | `team.md` 的 Deployment 段 |
| 並行控制 | `concurrency: deploy-10-10`，`cancel-in-progress: false` | 同上——部署中不可被新 run 打斷 |
| 回滾 | 既有 `rollback` job：還原 last-good、開 revert PR、dispatch Deploy Doctor | 同上 |
| **本單元的回滾特殊性** | **`noeviction` 的設定變更隨 compose 檔回滾而回滾**，但**已經被 Lua 寫成 Hash 的 session 資料不會回滾** | 見下 |

### 回滾的一個不對稱（本站查出，必須寫明）

若本單元上線後需要回滾，compose 的 `maxmemory-policy` 會回到 `allkeys-lru`，
但 **`redis_aof` volume 裡已經是 Hash 結構的 session 資料仍在**。舊版程式不認識
那個結構。

**後果與緩解**：舊版程式**完全不讀** Redis（`technology-stack.md:206` 實測：
回滾目標的 `backend/` 應用程式碼**零 Redis import**），所以它不會因為讀到不認識的
結構而壞——它根本不會去讀。**這是本單元首次上線時獨有的安全性質，第二次之後就不成立了**：
一旦有版本在讀 Hash，往回滾到另一個讀 Hash 的版本才需要考慮結構相容。
此處記下來，是因為「第一次回滾安全」很容易被誤推成「回滾一直安全」。

## 五、CI/CD 中的 secrets

| secret | 來源 | 本單元的變更 |
|---|---|---|
| `REDIS_PASSWORD` | GitHub Actions secret → `render-env.sh:65` 的缺值檢查 → `deploy/.env` | **無變更**。`U1` 已完成 |
| `REDIS_USER` | `render-env.sh:122` 的常數（非 secret） | 無變更 |
| 上限參數（本單元新增） | **非 secret**——它是設定不是憑證 | 以一般環境變數承載，列入 `.env.example`（secret 不得列入範本） |

**本單元不新增任何憑證型 secret**，故 `project.md` 逐字要求的「新增憑證型 secret
後須實地查證它落在 secrets 而非 variables」在本單元**不觸發**。此處明記以免下游
誤以為跳過了該檢查。

## 六、本單元**不**做的 CI/CD 變更（逐項附理由）

| 不做 | 理由 |
|---|---|
| 新增 CI job | `[I1]`=B 的直接目的。現有 backend 測試跑 in-memory SQLite、無 Redis；在 `ui-regression` 中重啟 redis 會讓 Playwright 不穩（`team.md` 逐字記載它是真閘門） |
| 給 CI 測試 stack 加 AOF／volume | `[I1]` 的選項 A，未採用。理由見該選項的代價 |
| 改 `docker-compose.test.yml` 的 `maxmemory-policy` | 實讀確認不需要——該 stack 無 `maxmemory` |
| 改 branch protection 的必要檢查 | 不新增 job 即不需要。`ut` 無任何必要檢查、`main` 只有 `Repository contract`（`ci.yml` 的註解逐字記載此實查結果） |
| 導入 SAST／DAST／依賴掃描 | 超出本單元範圍；本 repo 目前無此類閘門，導入是獨立的工具鏈決策 |
