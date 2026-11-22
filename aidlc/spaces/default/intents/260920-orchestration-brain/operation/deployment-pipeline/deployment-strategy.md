# 部署策略

> 精簡版：記錄現行策略，並寫出本次發佈特有的風險。不改設定。

## 現行策略

- **deploy-on-merge**：PR 合併進 `ut` 即觸發 `deploy.yml`，部署到唯一的 staging（`192.168.10.10`，經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc`，ADR-0007）。
- **就地重建**：在自架 runner 上以 `docker compose up -d --build` 建置與替換；沒有 blue/green，也沒有 canary，部署期間服務會短暫重啟。
- **部署即驗證**：部署 job 內建資料面、tunnel、Redis ACL、session 存活、大腦 WS 等探測（見 `cd-config.md`），任一失敗即觸發 `rollback` job。
- Construction 與 Operations 是連續的同一條管線（ADR-0008），不以「階段」切分部署與運行。

## 環境晉升矩陣

| 環境 | 設定來源 | 用途 | 晉升條件 |
|---|---|---|---|
| 本機 dev | `backend/.env`、`frontend/.env` | 開發；本機可用 `LLM_PROVIDER=claude-code` | — |
| CI 短生命週期 stack | `deploy/docker-compose.test.yml`（值內嵌） | PR 上的 `ui-regression` | PR 檢查全綠 |
| staging | `deploy/.env`（`render-env.sh` 產生） | 對外驗證 | PR 合併進 `ut` |
| production | — | **不在範圍**（`project.md` `## Scope Overrides`，需新 ADR） | — |

三套設定不得互相混用，由 `scripts/validate_env_contract.py` 在 CI 強制。

## feature flag

不使用 feature flag 服務。本機限定的行為以環境變數控制（`LLM_PROVIDER=claude-code` 只在 `APP_ENV=local` 生效），部署設定不得出現本機限定值。

## 本次發佈的特殊風險

| 風險 | 為什麼特別 | 處置 |
|---|---|---|
| 資料庫大版本升級（PG 16 → 18） | PGDATA 不跨大版本相容。先合併會讓 PG 18 映像對著舊資料啟動，postgres 進入重啟迴圈，但站台首頁（靜態檔）仍正常，看起來像成功 | 依 `DEPLOY.md` §5.4 的七步、以 dump／restore 在**合併前**完成；§5.5 磁碟門檻與 §5.6 記憶體處置先過 |
| 自動回滾不還原資料 | `rollback` job 只回程式碼；升版窗口內回滾會讓 PG 16 映像對著 PG 18 資料 | 使用者 2026-11-14 選定 **B**：維持現況，出事時走 `rollback-runbook.md` 的手動回滾；舊 volume 與 dump 保留至驗證通過 |
| 新增 schema 與一次性遷移 | 既有環境不會重跑 `schema_rbac.sql`，新表與 `cloud360_memory` 角色只能由遷移腳本建立 | 合併前在部署主機依序跑 `run_hierarchy_migration.py` → `run_meta_schema_migration.py`（`DEPLOY.md` §2.2.7、§2.2.9） |
| 新增必要 secret | 缺 `MEMORY_DB_PASSWORD` 時部署在 secret 檢查就失敗 | 合併前建立；確認名稱只在 secrets、不在 variables |
| 記憶專用角色 | 非本機環境未設定時不退回主連線：記憶預取降級、語意記憶寫入回錯、刪帳號回 503 | secret 與遷移都完成後，部署步驟會設定密碼；合併後實測記憶 API |
| 本 intent 有部分修正未經 code-generation 審查員複驗 | F1、F2、F4、語意記憶、MB-48 是在 build-and-test 內直接修的 | 已有 1482 個後端測試與 216 個 e2e 的實跑證據；合併後依手動測案 MT-01～MT-07 驗證 |
