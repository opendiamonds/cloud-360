## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Resolved | Minor | `backend/tests_pg/test_purge_atomicity.py:51-60` 改為 `from services.system_accounts import RETENTION_SYSTEM_ACTOR_USERNAME as SENTINEL_USERNAME`，手寫字面字串已刪。`test_sentinel_username_has_one_source`（`test_retention_purge_contract.py:406`）以 AST 掃全 repo 的 `.py`，字面值只准出現在允許清單兩檔（`:149`），且斷言允許清單不得過期（`:455-475`）。`tests_pg/__init__.py:55-57` 已把 `backend/` 放上 `sys.path`，故此 import 在無資料庫時成立。副本實跑 19 案 OK。 |
| R-02 | Still applies | Minor | `services/auth.py` 的 `verify_password` 未改，仍無 try/except；本輪依計畫不改、不開 issue，`traceability.json` 的 `OPEN-CG9-2` 仍在。屬既有缺陷、不屬本單元，維持原結論：無須本單元處置。 |
| R-04 | Resolved | Minor | 新增 A8（核准保留帳號回 409、角色與申請狀態不變，`test_system_account_protection.py:199`）與 A9（重送停用被擋，`:231`）。我在副本把 `user_router.py:975` 的核准判定改成 `if False:`，只有 A8 轉紅（`Ran 9`、`FAILED (failures=1)`）；另把 `:1106` 收窄成只擋啟用方向，只有 A9 轉紅，與摘要所稱一致。`user_router.py` 本單元未改（其未提交差異來自 brain-infra 第 21 列）。 |
| R-05 | Resolved | Minor | `traceability.json` 的 `open_items` 已有 `OPEN-CG9-6`，指名 `collab_router.py` 的 `get_users` 並寫明承接者（擁有 `collab_router.py` 的後續單元或 intent，由 conductor 決定是否另列 merge-blockers 項）。 |
| R-07 | Resolved | Minor | `DEPLOY.md:1250-1260` 已寫明併入 `main` 當天必有一則假的「清除逾期」issue，並給出三項同時成立的辨識條件與處置（等第一次排程成功後手動關閉）。issue 標題前綴、`state=never`、06:23／17:41 UTC 皆與 workflow 對得上。我未開 `merge-blockers.md`，該檔「併入前即會觸發」措辭是否已更正不在本次驗證範圍。 |
| R-08 | Resolved | Minor | `memory-retention-purge.yml` 檔頭註解已改以 `deploy.yml` 的步驟名與 key 引用。我逐一在 `deploy.yml` 核對：`Build and start the stack`、`Remove the generated env file`、`Restore the last-good deployment`、`Set the memory-only database role password` 各恰好一處，`concurrency.group` 為 `deploy-10-10`。`git diff -U0` 中非 `#` 開頭的增刪行為 0；`deploy.yml:` 後接數字的行號引用全檔 0 命中。 |
| R-09 | Resolved | Minor | `DEPLOY.md:1244-1249` 明寫併入 `main` 後那次 `dry_run=true` 的 `workflow_dispatch` 同時是 `docker compose exec` 路徑的首次煙霧測試，失敗即先停用排程再修。 |
| R-10 | Resolved | — | 原列即為「無」，沒有可複驗的發現。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-purge/code-generation/code-generation-plan.md > Step 1 的 1.3 與 Step 12 的 12.5（共 2 格，現為未勾） | 這兩格的字面條件是「`git diff --stat -- backend/database.py` 必須為空」。目前工作樹該檔有 +72 行未提交差異，內容是記憶專用資料庫連線（`MEMORY_DB_ROLE`、`MemoryDatabaseNotConfigured`），歸屬為 brain-infra 第 20／29 列，與清除單元無關（清除走 `psql`，不經 `database.py`）。所以條件在本單元範圍內成立、在全檔範圍內不成立。維持未勾並寫明理由是誠實的處置，不是缺陷；但這兩格的敘述與歸屬無關，只要 brain-infra 的變更未提交，格子就永遠打不勾，其中 12.5 還把「兩支驗證器綠」與「database.py 為空」綁成一格，使已成立的部分也無法顯示為完成。 | 在 `code-summary.md` 或下一次計畫修訂中，把這兩格的條件改寫為「本單元未新增任何 `backend/database.py` 的 hunk」，並把驗證器通過獨立成一格；或在格子旁註明「因 brain-infra 的未提交變更而依字面不成立，已確認非本單元所致」。不必為此再開審查。 |
| Minor | backend/tests_pg/test_purge_atomicity.py:8（模組 docstring 的 `deploy.yml:124／:471`） | 模組 docstring 仍以行號引用 `deploy.yml`，而 `deploy.yml` 的行號已漂移（R-08 已因同一原因修正 workflow 檔頭）。實作方在摘要「交 conductor」第 3 點已自行揭露，屬同類殘留。事實本身不變，只是後來的維護者照行號查不到證據。 | 改以 `deploy.yml` 的步驟名稱（如 `Build and start the stack`）引用，與 workflow 檔頭一致。只改註解。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest tests.test_retention_purge_contract tests.test_system_account_protection`（scratchpad 副本，`backend/.venv/bin/python -B`） | `Ran 19 tests`、`OK` | 與摘要一致（契約 10 ＋ 保護 A1–A9）。 |
| 突變 1：副本 `user_router.py:975` 核准判定改 `if False:` | 僅 A8 轉紅（`failures=1`） | A8 能抓到核准入口失守，R-04 缺口已補上。 |
| 突變 2：副本 `user_router.py:1106` 改為 `... and request.is_active` | 僅 A9 轉紅（`failures=1`） | A9 是抓「只擋啟用、不擋重送停用」變體的唯一測試。 |
| `python3 -B scripts/validate_repo_contract.py` | passed | 通過。 |
| `python3 -B scripts/validate_env_contract.py` | passed | 通過。 |
| 工作流註解證明 | 非 `#` 行差異 0；步驟名皆存在於 `deploy.yml` | 檔頭只動註解，`-U`、`RETURNING *` 禁令未被碰到（`grep` 僅 `:177` 一行註解提及 `-U`）。 |
| 勾選計數 | 已勾 55、未勾 7（`grep -c`） | 與摘要一致。未勾的 7 格為 1.3、1.4、2.6、8.1、12.5 及 Step 14 兩格，理由皆已寫入摘要。 |
| 副本與暫存目錄 | 已刪除；repo 內未寫入任何檔案 | 符合限制。 |

### Summary

(a)(c)(e) 三項實作與測試都成立：哨符名稱現在只有正本與 seed 腳本兩處字面字串並有全 repo 掃描鎖住，核准與重送停用兩個入口各有能被突變打紅的測試，workflow 檔頭只動了註解。八列先前發現中七列已修正、一列（R-02，既有缺陷）依計畫維持由 `OPEN-CG9-2` 追蹤。本輪只有兩項 Minor（1.3／12.5 兩格敘述與歸屬脫鉤、`tests_pg` docstring 的過時行號）。新發現分類：新引入 0、既存漏審 2、新設計問題 0。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/tests_pg/test_purge_atomicity.py:58` (`SENTINEL_USERNAME = "SYSTEM.retention-purge"`) | The plan (Step 7, assertion 6) and `code-summary.md` both claim the sentinel username is materialized in exactly three places and that `test_sentinel_username_has_one_source` locks all three to the same string. There is in fact a **fourth** hardcoded copy in `test_purge_atomicity.py`, and that test is not checked by `test_sentinel_username_has_one_source` (which only parses `schema_rbac.sql`'s `K)` block, `purge_expired_memory.sql`, and `seed_retention_system_actor.py`). A future rename of the sentinel in the three guarded places would leave this fourth copy stale and unguarded. Impact is bounded — a mismatch would surface as a loud test failure (actor not found) rather than a silent one — but the "single source of truth, locked by a test" claim as written is inaccurate. | Either add `test_purge_atomicity.py` as a fourth file parsed by `test_sentinel_username_has_one_source`, or import `SENTINEL_USERNAME` from `seed_retention_system_actor.py` instead of re-declaring it, and correct the "three places" wording in `code-summary.md`/the plan. | Unresolved |
| R-02 | Minor | `backend/services/user_router.py:403-408` / `backend/services/auth.py:37-40` (pre-existing, confirmed via `code-summary.md` finding `F-1`) | Empirically reproduced via `TestClient`: a login request with a password longer than 72 bytes against an **existing** username raises an uncaught `ValueError` from `bcrypt.checkpw` inside `verify_password` (confirmed locally: 72-byte password → clean 401; 73-byte password → unhandled `ValueError: password cannot be longer than 72 bytes`), which FastAPI would turn into an unauthenticated 500 in production — a real account-existence oracle. This is pre-existing code outside this unit's `packaging` scope, and `code-summary.md` discloses it honestly as `OPEN-CG9-2` with a reasoned "won't fix here" (does not belong to this unit, team.md bars bundling unrelated refactors). The sentinel actor's own hash is unaffected (verified clean `False` return for legal-length inputs via the contract test). Recorded here only to confirm the disclosure is accurate and the risk is real, not to block this unit. | No action required in this unit; track `OPEN-CG9-2` as a separate issue against `auth.py` as the plan already proposes. | Unresolved |
| R-03 | Major | DEPLOY.md > §2.2.11「首次啟用前必須先驗證選取條件」與新增的「期限」段 | 新裁決讓 `workflow_dispatch` 在 `ut` 併入 `main` 前完全不可用，但「首次啟用前必須先以 `dry_run=true` 手動觸發驗證選取條件」這條（對應 `OPEN-ID9-4`：已執行的清除不可回滾）原封不動留在同一節。併入 `main` 的當天，排程就會開始跑，而排程一律是真實清除（`memory-retention-purge.yml` 約第 144 行「A scheduled run ALWAYS performs the real purge」）。想先 dry-run，只能在合併後、第一次排程之前搶先手動觸發，文件沒有要求這個順序，也沒有說明這是競態。結果是 `OPEN-ID9-4` 規定的 blocking-downstream 前置驗證，在文件上被宣稱需要，實際上無法保證做得到。原計畫 Step 14 的第 ① 項（dry-run 驗證）一併落空，新裁決沒有為它另設處置。 | 在 §2.2.11 明寫合併 `ut`→`main` 時的順序要求，並選一種處置：（a）要求在 `main` 取得兩支 workflow 檔之後、第一次排程時間之前，先手動 `dry_run=true` 並核對邊界，再讓排程接手，同時寫出這個窗口有多長；或（b）明說 dry-run 驗證無法先於第一次真實清除，並依「期限內無任何逾期資料」的論點，記為已接受的殘留風險，同步更新 `traceability.json` 的 `OPEN-ID9-4`。兩者擇一，不要讓兩段文字互相矛盾。 | Resolved (reviewer) |
| R-04 | Minor | backend/tests/test_system_account_protection.py；code-summary.md「重新查驗與合併前必修第 11、17 項」二節的突變表 | 實作宣稱五個端點的 409，但核准授權申請（`POST /authorization-requests/{id}/approve`）沒有任何測試。A1–A7 涵蓋刪除、改角色、啟用、列表、常數、拒絕、一般停用帳號，唯獨沒有核准。突變驗證也只做了刪除與列表兩項。把核准、改角色、啟停用三處的保留判定拿掉，測試仍有可能全綠，只有 A2、A3、A6 對應各自的路徑，但這三條沒有被實際突變驗證過。核准路徑是這四道鎖中「角色」那道的第二個入口，被標為縱深防禦卻無任何斷言保護。另外，`PUT /active` 的 409 在 `Union` 宣告下，也沒有斷言 `is_active=false` 重送同樣被擋。 | 補一個核准保留帳號回 409、角色與申請狀態皆不變的案例；對改角色、啟停用、核准各做一次「拿掉判定即轉紅」的突變，並寫入 `code-summary.md`。 | Unresolved |
| R-05 | Minor | backend/services/collab_router.py > `get_users`（約第 304 行，`GET /api/collab/users`） | 實作方已承認此端點仍列出 `SYSTEM.retention-purge`（含 `role: system`）。任何有架構圖編輯權的使用者都看得到這個內部帳號名，也能把圖分享給它（會在 `diagram_shares` 寫入一列指向它的資料）。不影響清除的完整性，因為它的刪、改角色、啟停用四個入口都已被擋，但違反「保留帳號對一般使用者不可見」的意圖，也是 `DEPLOY.md` 刻意註明的缺口。`team.md` 不允許趁機改動 `collab_router.py`，所以不構成本單元阻擋項。 | 保持現狀可接受；請在 `traceability.json` 的 `open_items` 登記一個有承接者的項目（目前只寫在 `DEPLOY.md` 與摘要的散文裡），讓它不會因為沒有編號而無人追蹤。 | Unresolved |
| R-06 | Minor | DEPLOY.md > §2.2.11「期限」段；merge-blockers.md 第 17 列 | 「本分支第一次部署到 staging 後 90 天內 `ut` 須併入 `main`」的前提成立：我確認 `origin/ut` 的 `schema_rbac.sql` 沒有 `memory_records`，且記憶寫入路徑只有 `memory_service.create_record`（`expires_at = created_at + 90 天`，無其他可回填過期時間的寫入者）。但這是純人工義務，沒有任何提醒機制，也沒有指定負責人與日期的記錄位置；文件只說「例如 issue 或團隊行事曆」。監看者（watchdog）在期限內同樣無法運作，這點文件已如實寫明，是對的。 | 在文件中指名一位負責人，並在第一次部署當天於 repo 內建立一個帶日期的 issue 作為唯一記錄位置，取代「例如」的選項清單。 | Resolved (reviewer) |
| R-07 | Minor | `.github/workflows/memory-retention-watchdog.yml` 的 `Read the purge workflow's last successful scheduled run` 與 `Decide whether the purge is overdue`；`DEPLOY.md` 第 1132–1155 行 | `ut` 併入 `main` 的第一天，監看（每日 06:23 UTC）會早於第一次排程清除（17:41 UTC）執行。`gh api` 此時回傳零筆成功的排程 run（state=`never`）或 404，兩者都判為逾期，所以第一天必然開出一則假的「清除逾期」issue 並讓 run 變紅。`code-summary.md` 重做節說「在 `ut` 併入 `main` 之前它一旦執行就會判逾期並開 issue」，這個方向不對：併入前兩支 workflow 都不在 `main`，根本不會執行；實際風險發生在併入之後的第一天，而 `DEPLOY.md` 的期限段落沒有提到。 | 在 `DEPLOY.md` §2.2.11 補寫：併入 `main` 後第一天可能出現一則假警報，並說明如何辨識（沒有任何成功的排程 run）。同時更正 `code-summary.md` 與 `merge-blockers.md` 第 17 列中「併入前即會觸發」的說法。 | Unresolved |
| R-08 | Minor | `.github/workflows/memory-retention-purge.yml` 檔頭註解（引用 `deploy.yml:376-378`、`:472`、`:124/:471`、`:149`、`:20-22`） | 這些行號是舊的。實際「Remove the generated env file」在 `deploy.yml:630-632`，rollback 刪除 `deploy/.env` 在 `:726`。事實本身仍成立（我逐項核對了 `rm -f deploy/.env` 與 `if: always()`），但這份註解正是 `--env-file deploy/.env.example` 偏離的唯一論證，行號失效會讓後來的維護者查不到證據。重做摘要已承認落差，卻沒有修正 workflow 內的註解。 | 把註解中的行號改為目前的位置，或改成用步驟名稱（「Remove the generated env file」）引用，避免日後再漂移。 | Unresolved |
| R-09 | Minor | `.github/workflows/memory-retention-purge.yml` 的 `Run the purge against the deploy stack database` 步驟 | 整條 `docker compose -f … --env-file deploy/.env.example exec -T db sh -c 'PGUSER=… psql …' < file` 路徑從未被實際執行過：CI 的 `memory-schema` 以 TCP 連 `postgres` 服務，重做輪的驗證用本機 PostgreSQL，開發環境也沒有 Docker。所以「psql 走容器內 socket 無需密碼」「容器內有 `POSTGRES_USER`／`POSTGRES_DB`」「`ps --status running --services` 輸出可被 `grep -qx db` 比對到」都只是推論。第一次真實驗證會是第一次排程，而排程一律是真實清除。 | 在 `DEPLOY.md` 的順序要求中明寫：併入 `main` 後那次 `dry_run=true` 的手動觸發同時是這條 compose 路徑的首次煙霧測試，必須確認它成功（不只是核對計數為 0），失敗就先停用排程。 | Unresolved |
| R-10 | — | — | 無 | — | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round
