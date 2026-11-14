# 基礎設施規格 — `U9 memory-purge`

> **本單元與 `U7`／`U19` 相反：它的交付物就是基礎設施。** 那兩個 `service` 單元在
> 本站的結論是「零基礎設施變更」；本單元是一個 GitHub Actions workflow，
> 故本站是它的實質站，四份產出全部適用（`packaging` 在四者的 `produces_kinds` 內）。

## 一、上游依據（逐一指名）

| 上游 | 本站用到它的什麼 |
|---|---|
| `nfr-design/security-design.md` | 清除的兩個目標、順序（稽核先於記憶）、交易邊界、系統 actor 的形狀、`NFR6.10` 的更正、不需重試的理由 |
| `nfr-requirements/security-requirements.md` | 八條 `NFR`（`NFR7.10`–`NFR7.15`、`NFR6.10`、`NFR8.10`）與其二元判準 |
| `nfr-requirements/tech-stack-decisions.md` | 零新技術的選擇表；既有排程 workflow 全在 GitHub 託管的雙向查證 |
| `inception/contract-design/contract-summary.md` | `K-05`（消費的 schema 契約）；本單元為無消費端的葉節點 |
| `inception/domain-design/components.md` | 架構脈絡（本單元在元件目錄中無對應的程式元件——它是部署面構件） |
| `.github/workflows/deploy.yml`（版控） | 自架 runner 標籤、`docker compose exec -T` 形狀、`db` 無 host port |
| `.github/workflows/daily-digest.md`（版控） | 既有排程 workflow 的權限形狀（`actions: read` 有先例、`issues: write` 無先例） |

## 二、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| 計算模型 | **兩個 GitHub Actions workflow**，無容器、無常駐進程 | 清除本體（自架 runner）＋ 監看者（GitHub 託管）。`FR4.5a` 禁止以 `backend/` 內的排程程式承載 |
| 清除本體的執行環境 | 既有自架 runner `[self-hosted, linux, x64, cloud360]` | `[N1]`=A。`db` 無 host port，故這是唯一到達方式 |
| 監看者的執行環境 | **GitHub 託管**（`ubuntu-latest`） | `[ID1]`=A。它必須在自架 runner 離線時仍能執行——這是它存在的全部理由 |
| 網路拓樸 | **零新監聽埠、零新 tunnel、`db` 不取得 host port** | `NFR7.12`。清除走 compose 內部網路；監看者只打 GitHub 自己的 API |
| 儲存策略 | **零新資料庫物件**；清除只 DELETE，`[ND1]`=A 的系統 actor 是對既有 `users` 表的一列 seed | 兩張表與兩個索引由 `U5` 交付（`K-05`） |
| 環境設定 | **零新環境變數、零新 GitHub secret** | `NFR8.10`／`NFR7.12`。監看者用內建 `GITHUB_TOKEN` |
| IaC 取徑 | **不動 `deploy/`**。變更只在 `.github/workflows/`（兩個新檔）與 `schema_rbac.sql`／`DEPLOY.md`（seed ＋ 同步） | `NFR8.10` 的二元判準 |
| 資源配額 | 不新增任何容器配額 | 清除是兩條 SQL；監看者是一次 API 呼叫 |

### 2.1 兩個 workflow 的落點與排程（本站定案，`OPEN-N9-3` 關閉）

| # | 檔案 | runner | 觸發 | 職責 |
|---|---|---|---|---|
| 1 | `.github/workflows/memory-retention-purge.yml` | **自架** | `on: schedule`（每日，UTC 離峰）＋ `workflow_dispatch` | 執行清除（兩條 DELETE ＋ 一次稽核 INSERT） |
| 2 | `.github/workflows/memory-retention-watchdog.yml` | **GitHub 託管** | `on: schedule`（每日）＋ `workflow_dispatch` | 查 #1 最後成功時間，逾門檻開 issue |

**檔名不以 `.md` 結尾**：那是 gh-aw 的慣例，而兩者都刻意不走 LLM 路徑（`NFR7.14`）。
**兩者都加 `workflow_dispatch`**：`FR4.5` 要求自動，但手動觸發對驗證與補跑是必要的，
且它不取代排程。

### 2.2 零新部署設定的二元判準（驗證落點在 `code-generation`）

1. `python3 scripts/validate_env_contract.py` 綠燈；
2. 本單元 diff **不含** `deploy/`、`deploy/render-env.sh`、任一 `.env.example`、
   `deploy/docker-compose.*.yml`、`deploy/nginx.conf`；
3. `gh api repos/<owner>/<repo>/actions/secrets` 的名稱集合**不變**。

### 2.3 `LOCAL-DEV.md` 的同步義務：不觸發

`project.md` 的觸發清單為「異動 `backend/database.py` 的 schema 補丁、
`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh`」——本單元四者皆不動。

**但 `DEPLOY.md` 的 blocking 同步觸發了**：`[ND1]`=A 的系統 actor seed 是對
`schema_rbac.sql` 的變更（見 §四）。

## 三、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| PostgreSQL（既有） | database | **不變**：不改隔離等級、不改連線池、不新增索引 | 清除以 `docker compose exec -T db psql` 連入，身分為 `POSTGRES_USER`（即 superuser，見 `[ND2]`=A 的更正） |
| GitHub Actions（既有） | scheduler ＋ CI | 兩個新 workflow；#1 用自架 runner、#2 用託管 runner | 這是本單元的**執行基礎設施**，不是附屬品 |
| GitHub Actions API | 監看的資料來源 | `gh api` 讀 #1 的 run 歷史；需 `actions: read` | **有先例**：`daily-digest.md:13` 即 `actions: read` |
| GitHub Issues | 告警管道 | 監看者逾門檻時 `gh issue create`；需 **`issues: write`** | **無先例**（見 `monitoring-design.md §二之三`）——既有排程 workflow 只有 `issues: read` ＋ gh-aw 的 `safe-outputs` |
| logging 管線（既有） | log | 不變 | 清除的輸出是 Actions log；不新增轉送或保留規則 |

**本單元不新增的服務類別**：cache、queue、search、CDN、DNS、load balancer、
secrets store、容器、監聽埠。

## 四、Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `memory.memory_records` | `U5`（`K-05`） | `U8`（讀寫）、**本單元（DELETE）** | grant 只開放 `memory` schema；**該邊界目前不是真正的邊界**（`[ND2]`=A：連線身分即 superuser） |
| `memory.memory_audit_events` | `U5`（`K-05`） | `U8`（寫）、**本單元（INSERT ＋ DELETE）** | 同上。本單元是它**唯一的 DELETE 端**（`NFR7.2` 的 90 天保存） |
| `public.users` | baseline | 全系統 | **本單元新增一列 seed（系統 actor）**。這是本單元對共用資源唯一的寫入 |
| 自架 runner | `deploy.yml`（既有使用者） | `deploy.yml` 的兩個 job ＋ **本單元的 #1** | 共用。**本單元是第一個在它上面排程觸發的 workflow**——既有兩個都是事件觸發 |
| GitHub Actions 配額 | — | 全 repo | 每日兩次執行，可忽略 |

### 4.1 本站查出的一項跨單元影響：本單元是 `memory_audit_events` 唯一的 DELETE 端

`U5` 為 `NFR7.2` 建了 `ix_memory_audit_events_occurred_at`，其註解逐字說明
該表本輪**沒有任何讀取端**（`US4.3` 的查詢面是回補項 `N-8`，屬 `U8`），
「所以不會有人順手建它」。

**後果**：若本單元的清除未落地，該表**無上界成長**且沒有任何其他機制會清它。
而 `U8` 只寫不刪。這使本單元不只是「保存期合規」的承載者，也是該表的
**唯一垃圾回收路徑**——`NFR7.13` 的漏跑偵測因此保護兩件事，不是一件。

## 五、既有環境的執行順序

本單元**不新增一次性腳本**，但它的系統 actor seed 依賴既有的遷移路徑：

| # | 動作 | 前置 | 跳過的後果 |
|---|---|---|---|
| 1 | `U5`＋`U18` 的 `run_meta_schema_migration.py` | `U4` 的階層遷移 | `memory` schema 與兩張表不存在 → 清除的 DELETE 拋 `UndefinedTable` |
| 2 | **重跑 `schema_rbac.sql`**（既有環境取得 seed 的唯一路徑） | 第 1 步 | 系統 actor 列不存在 → 清除的稽核 INSERT **全部失敗**（`NOT NULL` 外鍵），而那是**大聲失敗**（整個交易中止、workflow 非零碼） |
| 3 | 兩個 workflow 隨 merge 進 `ut` 自動生效 | — | — |

### 5.1 seed 必須可安全重跑（承審查 `R-03`）

`DEPLOY.md` 證實既有環境取得 schema 變更的唯一路徑是**手動重跑整支
`schema_rbac.sql`**（`docker-entrypoint-initdb.d` 只在空 data volume 執行一次）。

故系統 actor 的 seed **必須**寫成 `INSERT ... ON CONFLICT (username) DO NOTHING`
或等價形式。**不這樣寫的後果不是「seed 失敗」，是整支腳本從那一行起全部中止**
——`ix_users_username` 的 UNIQUE 違反會擋下其後的所有陳述，包含本次要新增的其他 DDL。

`project.md ## Mandated` 逐字要求本檔新增內容「使用 `IF NOT EXISTS` 等可重跑安全寫法」。

### 5.2 `DEPLOY.md` 的 blocking 同步（本單元觸發）

| 落點 | 內容 |
|---|---|
| `DEPLOY.md` 的「這支 SQL 會建立的表／欄位」區 | 新增系統 actor seed 的說明：它是什麼、為何不可登入、**刪掉它會讓清除的稽核 INSERT 全部失敗** |
| 驗證指令 | `psql -c "SELECT id, username, role, is_active FROM users WHERE username = '<哨符>'"` 應回一列、`is_active` 為 `f` |
| 只寫 `## 中文版` 半部 | 沿用 `U5`／`U18` 的既有處置 |

## 六、ADR-0006 四面向：本站的增量

逐格對照 `nfr-design/security-design.md §四`。**本站不改任何一格的判定**。

| 面向 | 判定（與上游一致） | 本站的基礎設施增量 |
|---|---|---|
| **IAM** | 適用，但 `NFR6.10` 不構成邊界（`[ND2]`=A） | **本站新增一項上游沒有的 IAM 面**：監看者需要 **`issues: write`**，而本 repo 既有排程 workflow**無此先例**（只有 `issues: read` ＋ gh-aw 的 `safe-outputs`）。處置與替代方案見 `monitoring-design.md §二之三` |
| **Encryption** | 本單元無落點（承 `U5` 的 `NFR6.1`／`NFR6.2`） | **不寫「不適用」**。清除流量留在 compose 內部；監看者只打 GitHub API（HTTPS，由 `gh` CLI 承載），**不傳輸任何記憶內容**——它只讀 workflow run 的時間戳 |
| **Network exposure** | 零增量 | 維持：`db` 無 host port、無新 tunnel、無新監聽埠。**監看者不是暴露面**——它是**出向**呼叫 GitHub API，不接受任何入向連線 |
| **Audit logging** | 適用 | 稽核列由清除寫入（`NFR7.11`）。**本站新增一層**：監看者開的 issue 本身是「清除漏跑」這件事的紀錄，且它在 GitHub 上、不在那台可能離線的主機上 |

### PBT：**N/A（非豁免）**，與上游一致

兩個 workflow 與其中的 SQL／`gh api` 呼叫，無本單元擁有的純函式。
