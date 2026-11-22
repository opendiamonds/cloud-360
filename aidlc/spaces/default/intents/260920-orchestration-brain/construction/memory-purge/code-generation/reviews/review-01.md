## Review

**Verdict:** READY

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-08T12:07:57Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/tests_pg/test_purge_atomicity.py:58` (`SENTINEL_USERNAME = "SYSTEM.retention-purge"`) | The plan (Step 7, assertion 6) and `code-summary.md` both claim the sentinel username is materialized in exactly three places and that `test_sentinel_username_has_one_source` locks all three to the same string. There is in fact a **fourth** hardcoded copy in `test_purge_atomicity.py`, and that test is not checked by `test_sentinel_username_has_one_source` (which only parses `schema_rbac.sql`'s `K)` block, `purge_expired_memory.sql`, and `seed_retention_system_actor.py`). A future rename of the sentinel in the three guarded places would leave this fourth copy stale and unguarded. Impact is bounded — a mismatch would surface as a loud test failure (actor not found) rather than a silent one — but the "single source of truth, locked by a test" claim as written is inaccurate. | Either add `test_purge_atomicity.py` as a fourth file parsed by `test_sentinel_username_has_one_source`, or import `SENTINEL_USERNAME` from `seed_retention_system_actor.py` instead of re-declaring it, and correct the "three places" wording in `code-summary.md`/the plan. | New |
| R-02 | Minor | `backend/services/user_router.py:403-408` / `backend/services/auth.py:37-40` (pre-existing, confirmed via `code-summary.md` finding `F-1`) | Empirically reproduced via `TestClient`: a login request with a password longer than 72 bytes against an **existing** username raises an uncaught `ValueError` from `bcrypt.checkpw` inside `verify_password` (confirmed locally: 72-byte password → clean 401; 73-byte password → unhandled `ValueError: password cannot be longer than 72 bytes`), which FastAPI would turn into an unauthenticated 500 in production — a real account-existence oracle. This is pre-existing code outside this unit's `packaging` scope, and `code-summary.md` discloses it honestly as `OPEN-CG9-2` with a reasoned "won't fix here" (does not belong to this unit, team.md bars bundling unrelated refactors). The sentinel actor's own hash is unaffected (verified clean `False` return for legal-length inputs via the contract test). Recorded here only to confirm the disclosure is accurate and the risk is real, not to block this unit. | No action required in this unit; track `OPEN-CG9-2` as a separate issue against `auth.py` as the plan already proposes. | New |

### 摘要
- `new-design-problem`: 1 (R-01)
- `pre-existing-unreviewed`: 1 (R-02 — pre-existing, but correctly surfaced and disclosed by this unit rather than left unreviewed; recorded for completeness)
- `propagated-from-upstream`: 0

### 覆蓋範圍

**已查證**（全部對 repo 當前檔案與一個拋棄式真實 PostgreSQL 17 + pgvector 實例執行，非僅讀文件）：

- **(a) `--env-file` 決定（D-1，最高優先）**：讀過 `memory-retention-purge.yml` 全文、`deploy.yml:124/137/198/250/349/350/364/376-378/471-472`、`deploy/docker-compose.deploy.yml`、`deploy/.env.example`、`scripts/validate_env_contract.py`（實跑 `python3 scripts/validate_env_contract.py` → 綠燈）。確認：呼叫形式是 `exec -T`（非 `up`），不重建容器；`PGUSER`/`PGDATABASE` 取自容器自身既有環境（compose `environment:` 於 `up` 時寫入，`exec` 沿用容器建立時的環境，不受 `--env-file` 內容影響）；`.env.example` 對 `docker-compose.deploy.yml` 所有無預設值變數（含 `CLOUDFLARED_CREDENTIALS_FILE`）都有值，CI 驗證過；workflow 自帶 `ps --status running --services | grep -qx db` 前置檢查，失敗時給可讀錯誤而非盲目 `exec`。未發現可把錯誤/示範值寫進執行中容器的路徑。
- **(b) 清除是否會刪錯列**：讀過 `purge_expired_memory.sql`、`schema_rbac.sql` 的 `memory_records`/`memory_audit_events` 約束。`kind = 'episodic'` 條件存在；CTE 的 `DELETE ... RETURNING` 餵給 `INSERT ... RETURNING`，結構上保證 1:1；`actor_user_id NOT NULL REFERENCES users(id)` 確認哨符列缺席時交易會整體中止（已用 `test_missing_system_actor_aborts_whole_transaction` 實跑驗證）。**以真實 PostgreSQL 實跑 `verify_purge_sql.sql`，R1–R10 全部通過**；另以手動突變（把 `kind = 'episodic'` 換成 `1=1`）重跑，確認 `R4` 會變紅燈（`R4 FAILED ... kind = semantic ... 必須保留，實際 0 列`），之後還原並清理殘留 fixture。
- **(c) 公開 log 洩漏**：逐行讀過 `purge_expired_memory.sql`、`purge_dry_run.sql`、`verify_purge_sql.sql`、`seed_retention_system_actor.py`、兩個 workflow。確認全部 `RETURNING` 皆為 `RETURNING id`；dry-run 只印 `id`/`kind`/時間戳/計數，無 `content`/`embedding`；seed 腳本只印 host/database 名，不印 `DATABASE_URL`；workflow 不 echo 任何連線字串或密碼。
- **(d) SQL 只存在一份**：確認 `schema_rbac.sql` 的 `K)` 區塊是唯一手寫的 seed SQL；`seed_retention_system_actor.py` 透過 `extract_blocks()` 解析同一區塊執行，未複製解析邏輯或 SQL 文字；`run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN` 確認仍為 `("X", "I", "J")`（未變），`BLOCK_SENTINELS["K"]` 只是查表登錄、不含哨符 username 字面值。全 repo grep `SYSTEM.retention-purge` 確認共 10 個檔有命中，其中 4 個是 SQL/workflow 讀取端、1 個是 seed 腳本常數、1 個是 contract 測試的解析對象——唯一的落差是 R-01（`test_purge_atomicity.py` 的第四份硬編常數未被一致性測試覆蓋）。
- **(e) watchdog**：讀過 `memory-retention-watchdog.yml` 全文。確認 `status=success&event=schedule` 篩掉手動 dry-run；`gh api` 失敗、`never` 狀態、`unreachable` 都會被判為逾期（不會誤判為新鮮）；3 天門檻是 `age_days > 3`，與程式碼內的兩套措辭不一致（已被 workflow 自己的註解誠實記載，非隱藏缺陷）；去重以標題前綴 `gh issue list` 比對。
- **(f) 測試是否真實**：
  - `python3 -m unittest tests.test_retention_purge_contract -v`：10/10 通過。
  - 對真實 PostgreSQL 17（本機拋棄式 initdb instance，含 pgvector）套用 `schema_rbac.sql`（含重跑一次驗證 idempotency）、`verify_memory_schema.sql`（S1–S13 全通過）、`verify_purge_sql.sql`（R1–R10 全通過，且以上述突變驗證 R4 非恆真）。
  - `DATABASE_URL` 指向同一個真實 PostgreSQL，執行 `python3 -m unittest tests_pg.test_purge_atomicity -v`：`A1`/`A2`/`A3` 3/3 通過（含 `pg_terminate_backend` 的連線中斷情境）。
  - 以 `TestClient` 對真實 `app`（in-memory SQLite）實測 F-1（見 R-02）：確認其為真實、可重現的既有缺陷，而非 `code-summary.md` 的誤述。
- **(g) 引用逐字核對**：核對過 `deploy.yml:124/137/198/250/349/350/364/376-378/471-472`、`backend/services/auth.py:37-40`、`backend/services/user_router.py:403-408`、`schema_rbac.sql` 的 `memory_records`/`memory_audit_events`/`K)` 區塊行號與內容、`docker-compose.deploy.yml` 的 `db` service 環境變數、`ci.yml` 的 `memory-schema` job 新增步驟（確認無 `working-directory` 覆寫，`\i` 相對路徑解析正確）。全部核對的引用內容與行號一致，未發現本 intent 之前記錄過的「內容對、行號錯」形狀。

**未深入查證**：

- 突變驗證表（Step 11）的其餘 5 項（`RETURNING *`、`ON CONFLICT` 移除、CTE 拆兩條敘述並中途 `COMMIT`、`interval` 正負號反轉、watchdog 移除 `status=success`）只驗證了第 1 項（`kind = 'episodic'`）；其餘 5 項依賴 `code-summary.md` 的自述結果，未逐一重跑突變。
- `ci.yml` 整份 diff 與 `DEPLOY.md` §2.2.11 全文只讀了關鍵段落，未逐字核對是否有其他章節的交叉引用殘留（如行號引用）。
- watchdog workflow 從未在真實 GitHub Actions 環境跑過（`gh api` 呼叫、issue 去重、`date -u -d` 在 GNU/ubuntu-latest 上的行為未實測，只靠讀程式碼判斷）。
- `D-3`（`PGUSER`/`PGDATABASE` 取自容器環境）的 compose/docker 行為語意是依工具知識核對而非在真實 self-hosted runner 上實跑一次 `exec` 驗證。
- `OPEN-CG9-2`（既有 500 oracle）以外的 `OPEN-*`/`F-2`/`F-3`/`F-4` 等其餘「計畫沒有預料到的發現」條目未逐項複核。
- 未檢查 `.github/workflows/ci.yml` 是否還有本單元之外、因本次編輯而意外受影響的既有步驟（僅看了新增的那一步與其直接上下文）。

### Summary

本單元的七個優先查證項（a–g）在以本機真實 PostgreSQL 17 + pgvector 實跑，以及對照 repo 原始碼逐行核對後，均未發現會導致刪錯資料、洩漏個資到公開 log、或讓清除靜默失敗的設計缺陷；`--env-file deploy/.env.example` 的偏離（D-1）有堅實的機制依據（`exec` 不重建容器、身分取自容器既有環境、CI 保證範本完整）。唯二發現均為 Minor：一個是測試覆蓋聲明與實際實作之間的小落差（`test_purge_atomicity.py` 的第四份哨符常數未被一致性測試鎖住），另一個是對既有（非本單元引入）帳號存在性 oracle 的獨立驗證，確認 `code-summary.md` 的揭露準確、處置合理。沒有一項達到 Critical 或構成阻擋合併的理由。

VERDICT: READY
