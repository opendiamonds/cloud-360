# CD 設定（現況記錄）

> 精簡版：本站不新增、不修改部署設定。以下為 PR #650 head `660076b` 當下的實際內容，行號以 `grep -n` 實查（2026-11-14T06:01:59Z，`date -u`）。

## 觸發與執行環境（`.github/workflows/deploy.yml`）

| 項目 | 內容 | 位置 |
|---|---|---|
| 觸發 | `pull_request` 的 `closed` 事件、目標分支為 `ut`（job 內再判斷是否真的合併）；或手動 `workflow_dispatch` | `deploy.yml:10-15` |
| 權限 | 預設 `contents: read`；`rollback` job 另外提升為可寫 | `deploy.yml:17-18` |
| concurrency | `deploy-10-10`，`cancel-in-progress: false`（部署中不可被打斷） | `deploy.yml:20-22` |
| runner | 自架 `[self-hosted, linux, x64, cloud360]` | `deploy.yml:27`、`:728` |

## `deploy` job 的步驟

| 步驟（`- name:`） | 作用 | 位置 |
|---|---|---|
| Record the commit being deployed | 記錄本次部署的 commit | `:63` |
| Require the secrets that must not default | 必要 secret 缺任一即失敗 | `:80` |
| Write deploy/.env from secrets | 唯一產生點為 `deploy/render-env.sh`（`project.md` `## Mandated`） | `:113` |
| Build and start the stack | `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build --remove-orphans` | `:140-143` |
| Set the memory-only database role password | 以 `deploy/initdb/02-memory-role-password.sh` 設定 `cloud360_memory` 密碼 | `:159` |
| Wait for the frontend to answer locally | 本機回應等待 | `:173` |
| Verify the Redis ACL actually took effect | Redis ACL 實際生效驗證 | `:242` |
| Pull the embedding model into the Ollama volume | 拉 embedding 模型（暫時性失敗只發 warning） | `:300` |
| Probe the data plane through /api | frontend → backend → db 資料面探測 | `:363` |
| Wait for the public hostname to answer through the tunnel | Cloudflare Tunnel 公開網址驗證 | `:408` |
| Record mcp-bridge health (non-blocking) | MCP bridge 健康記錄，不阻擋 | `:438` |
| Verify sessions survive a Redis restart | session 跨 Redis 重啟存活（NFR4.53-57） | `:500` |
| Verify the brain WS subprotocol survives the tunnel | 大腦 WS 子協定穿過 tunnel | `:656` |
| Record this commit as the last-good deployment | 寫 `${HOME}/.cloud360/last-good-sha` | `:694-699` |
| Remove the generated env file | 刪除 `deploy/.env` | `:701` |

## `rollback` job（`deploy` 失敗時）

| 步驟 | 作用 | 位置 |
|---|---|---|
| Restore the last-good deployment | checkout `last-good-sha` 後重新 `up -d --build`；沒有 last-good 時只發 warning，不能回滾 | `:743`、`:785` |
| Open a revert PR for the bad merge | 為造成失敗的合併開 revert PR（手動 dispatch 沒有可 revert 的 PR） | `:865` |

**它只還原程式碼，不還原資料庫內容或 PGDATA**（`DEPLOY.md` §5.4 排序不變量 2）。

## 部署 stack（`deploy/docker-compose.deploy.yml`）

| 服務 | 映像／說明 | 位置 |
|---|---|---|
| `db` | `pgvector/pgvector:pg18`（本 intent 由 PG 16 升為 18） | `:35-40` |
| `backend` | repo 內建置 | `:79` |
| `redis` | `redis:8-alpine` | `:190-193` |
| `ollama` | `ollama/ollama:latest` | `:331-342` |
| `frontend` | repo 內建置 | `:372` |
| `cloudflared` | `cloudflare/cloudflared:latest` | `:394-395` |
| `mcp-bridge` | 第七個服務（U21） | `:419` |

網路分為 `edge`、`internal`、`mcp` 三段（`:489-491`）。

## 本 intent 對部署設定的改動

| 改動 | 位置 | 依據 |
|---|---|---|
| 資料庫映像改為 `pgvector/pgvector:pg18` | `docker-compose.deploy.yml:40` | U1 brain-infra；升版程序見 `DEPLOY.md` §5.4 |
| 新增必要 secret `MEMORY_DB_PASSWORD` | `render-env.sh:20`、`:77-82`、`:141`；`deploy/.env.example:121` | 合併前必修第 20／29 列；`DEPLOY.md` 記憶專用角色段 |
| 部署後設定記憶專用角色密碼的步驟 | `deploy.yml:159` | 同上 |
| Redis、Ollama、MCP bridge 服務與其驗證步驟 | 見上表 | U1、U10、U21 |

## 機密處理

- 機密只來自 GitHub **secrets**，`deploy/.env` 由 `render-env.sh` 產生、部署後刪除。
- 憑證值不得含 `$`（compose 內插會無聲截斷，`render-env.sh` 會擋）。
- 2026-11-14 以 `gh api` 只列名稱查證：`JWT_SECRET`、`OPENROUTER_API_KEY`、`POSTGRES_PASSWORD`、`REDIS_PASSWORD` 都在 secrets，variables 沒有同名項；**`MEMORY_DB_PASSWORD` 尚未建立**。
