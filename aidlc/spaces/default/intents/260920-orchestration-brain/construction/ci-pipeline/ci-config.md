# CI 設定（現況記錄）

> 本站為精簡版：不新增、不修改 CI 設定檔。以下是 PR #650 head `48f6349` 當下的實際設定，與本 intent 對它做過的改動。來源皆為 repo 內檔案，可逐行複驗。

## 工具與觸發

- **工具**：GitHub Actions。另有 gh-aw agentic workflow，以 `.md` 原始檔編譯成 `.lock.yml`，GitHub 實際執行的是 lock 檔。
- **`ci.yml` 觸發條件**：
  - `pull_request`：不加路徑過濾。理由見檔內註解：PR 路徑過濾比對的是整個 PR 的檔案集合，過濾永遠不成立。
  - `push`：限 `main`、`ut`、`danniel/**`、`chore/**`，只排除同步機制回寫的 `sync-state.json`。
- **concurrency**：同 ref 的舊 run 會被取消。
- **衝突時不觸發**：PR 與目標分支衝突時，GitHub **不會**建立任何 `pull_request` run。PR #650 於 2026-11-14 實際遇到：推送後只有 push 事件的 CI 跑，合併 `ut` 解衝突後 PR 檢查才觸發。

## `ci.yml` 的 job（九個，`gate` 之外全部並行）

| job | 內容（步驟名取自 `- name:`） |
|---|---|
| `gate` | 判斷這次 run 是否來自同步機制回寫，是則讓後續 job 跳過 |
| `repo-contract` | repo 契約、環境設定契約、cost calculator import 邊界、pricing lookup 邊界、embedding provider 值 |
| `frontend` | Lint、API 型別契約漂移、WS 契約型別漂移、型別檢查＋build、spec 不得被靜態提供 |
| `backend` | 匯入 FastAPI app、OpenAPI spec 漂移、WS 契約 spec 漂移、MCP tool spec 漂移、unittest 全套 |
| `memory-schema` | 套用與重套 `schema_rbac.sql`（冪等）、記憶 schema 斷言 S1–S13、記憶專用角色邊界 R0–R3、project-meta 斷言 P1–P17、U20 遷移步驟 A–E、記憶清除行為 R1–R10 |
| `concurrency` | 套用 `schema_rbac.sql`、設定記憶專用角色密碼、真實 PostgreSQL 測試（`backend/tests_pg/`） |
| `docker-build` | 建 backend 與 frontend 映像（只建不推） |

## PR 上的其他 workflow（本次全部 `success`）

- `UI Regression Reporter`（`ui-regression`）：在短生命週期 stack 上跑 Playwright 全套，`post-steps` 讀 `pw-report.json` 的 `stats.unexpected`，非 0 即失敗。這是**真閘門**。
- `AI-DLC Sync Selftest`：同步機制自我測試。掃描面上的腳本不得出現代理式呼叫字樣（R-1.2），且掃描面必須落在觸發 allowlist 內（COVERAGE-2）。
- `Contract Guard`、`Code Drift Alert`、`Local Dev Drift`、`Lint Fixer`、`PR Reviewer`、`AI-DLC Sync Forward`。

## 部署（`deploy.yml`，非本站範圍，僅記錄銜接點）

- **觸發**：PR 合併（`closed`）進 `ut`，或手動 `workflow_dispatch`。
- **runner**：自架 `[self-hosted, linux, x64, cloud360]`。
- **流程**：
  1. 必要 secret 檢查。
  2. 由 `deploy/render-env.sh` 產生 `deploy/.env`。
  3. `docker compose up -d --build`。
  4. 設定記憶專用角色密碼。
  5. 資料面與 tunnel 探測、Redis ACL 驗證、session 跨 Redis 重啟驗證、大腦 WS 子協定穿過 tunnel 驗證。
  6. 記錄 last-good。
  7. 刪除 `deploy/.env`。

## 本 intent 對 CI 的改動

| 檔案 | 改動 | 理由 |
|---|---|---|
| `.github/workflows/ci.yml` | `concurrency` job 新增「Set the memory-only role password」一步（沿用 `memory-schema` job 的同一支腳本） | MB-48：WS 路徑改走記憶專用連線，`tests_pg` 新增以 `cloud360_memory` 實連的測試 |
| `.github/workflows/ci.yml` | 真實 PostgreSQL 步驟名中的檔案數隨 `tests_pg` 增加更新 | 規則：步驟名與 `tests_pg` 檔案一致 |
| `.github/workflows/aidlc-sync-selftest.yml` | 觸發 allowlist 補 `deploy/initdb/02-memory-role-password.sh` | COVERAGE-2：`ci.yml` 的 `run:` 直接呼叫它 |
| `scripts/validate_env_contract.py` | 本機限定 provider 名稱改自 `backend/services/llm_provider.py` 讀取 | R-1.2：掃描面上的腳本不得寫死該字樣；同時符合單一真實來源 |

## 本次實跑證據

| workflow | run | 結果 |
|---|---|---|
| CI（pull_request） | 43556488824 | success |
| AI-DLC Sync Selftest | 43556488890 | success（前一個 head `e2ca1ac` 的 run 43555309359 為 failure，已修） |
| UI Regression Reporter | 43556488900 | success：`215 passed`，`unexpected=0 flaky=0` |
| Contract Guard、Code Drift Alert、Local Dev Drift、Lint Fixer、PR Reviewer、AI-DLC Sync Forward | 同 head | success |
