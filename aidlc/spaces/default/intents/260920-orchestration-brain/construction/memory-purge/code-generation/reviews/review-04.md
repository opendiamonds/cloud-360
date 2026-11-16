## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T07:35:02Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/tests_pg/test_purge_atomicity.py:58` (`SENTINEL_USERNAME = "SYSTEM.retention-purge"`) | The plan (Step 7, assertion 6) and `code-summary.md` both claim the sentinel username is materialized in exactly three places and that `test_sentinel_username_has_one_source` locks all three to the same string. There is in fact a **fourth** hardcoded copy in `test_purge_atomicity.py`, and that test is not checked by `test_sentinel_username_has_one_source` (which only parses `schema_rbac.sql`'s `K)` block, `purge_expired_memory.sql`, and `seed_retention_system_actor.py`). A future rename of the sentinel in the three guarded places would leave this fourth copy stale and unguarded. Impact is bounded — a mismatch would surface as a loud test failure (actor not found) rather than a silent one — but the "single source of truth, locked by a test" claim as written is inaccurate. | Either add `test_purge_atomicity.py` as a fourth file parsed by `test_sentinel_username_has_one_source`, or import `SENTINEL_USERNAME` from `seed_retention_system_actor.py` instead of re-declaring it, and correct the "three places" wording in `code-summary.md`/the plan. | Unresolved |
| R-02 | Minor | `backend/services/user_router.py:403-408` / `backend/services/auth.py:37-40` (pre-existing, confirmed via `code-summary.md` finding `F-1`) | Empirically reproduced via `TestClient`: a login request with a password longer than 72 bytes against an **existing** username raises an uncaught `ValueError` from `bcrypt.checkpw` inside `verify_password` (confirmed locally: 72-byte password → clean 401; 73-byte password → unhandled `ValueError: password cannot be longer than 72 bytes`), which FastAPI would turn into an unauthenticated 500 in production — a real account-existence oracle. This is pre-existing code outside this unit's `packaging` scope, and `code-summary.md` discloses it honestly as `OPEN-CG9-2` with a reasoned "won't fix here" (does not belong to this unit, team.md bars bundling unrelated refactors). The sentinel actor's own hash is unaffected (verified clean `False` return for legal-length inputs via the contract test). Recorded here only to confirm the disclosure is accurate and the risk is real, not to block this unit. | No action required in this unit; track `OPEN-CG9-2` as a separate issue against `auth.py` as the plan already proposes. | Unresolved |
| R-03 | Major | DEPLOY.md > §2.2.11「首次啟用前必須先驗證選取條件」與新增的「期限」段 | 新裁決讓 `workflow_dispatch` 在 `ut` 併入 `main` 前完全不可用，但「首次啟用前必須先以 `dry_run=true` 手動觸發驗證選取條件」這條（對應 `OPEN-ID9-4`：已執行的清除不可回滾）原封不動留在同一節。併入 `main` 的當天，排程就會開始跑，而排程一律是真實清除（`memory-retention-purge.yml` 約第 144 行「A scheduled run ALWAYS performs the real purge」）。想先 dry-run，只能在合併後、第一次排程之前搶先手動觸發，文件沒有要求這個順序，也沒有說明這是競態。結果是 `OPEN-ID9-4` 規定的 blocking-downstream 前置驗證，在文件上被宣稱需要，實際上無法保證做得到。原計畫 Step 14 的第 ① 項（dry-run 驗證）一併落空，新裁決沒有為它另設處置。 | 在 §2.2.11 明寫合併 `ut`→`main` 時的順序要求，並選一種處置：（a）要求在 `main` 取得兩支 workflow 檔之後、第一次排程時間之前，先手動 `dry_run=true` 並核對邊界，再讓排程接手，同時寫出這個窗口有多長；或（b）明說 dry-run 驗證無法先於第一次真實清除，並依「期限內無任何逾期資料」的論點，記為已接受的殘留風險，同步更新 `traceability.json` 的 `OPEN-ID9-4`。兩者擇一，不要讓兩段文字互相矛盾。 | Resolved (reviewer) |
| R-04 | Minor | backend/tests/test_system_account_protection.py；code-summary.md「重新查驗與合併前必修第 11、17 項」二節的突變表 | 實作宣稱五個端點的 409，但核准授權申請（`POST /authorization-requests/{id}/approve`）沒有任何測試。A1–A7 涵蓋刪除、改角色、啟用、列表、常數、拒絕、一般停用帳號，唯獨沒有核准。突變驗證也只做了刪除與列表兩項。把核准、改角色、啟停用三處的保留判定拿掉，測試仍有可能全綠，只有 A2、A3、A6 對應各自的路徑，但這三條沒有被實際突變驗證過。核准路徑是這四道鎖中「角色」那道的第二個入口，被標為縱深防禦卻無任何斷言保護。另外，`PUT /active` 的 409 在 `Union` 宣告下，也沒有斷言 `is_active=false` 重送同樣被擋。 | 補一個核准保留帳號回 409、角色與申請狀態皆不變的案例；對改角色、啟停用、核准各做一次「拿掉判定即轉紅」的突變，並寫入 `code-summary.md`。 | Unresolved |
| R-05 | Minor | backend/services/collab_router.py > `get_users`（約第 304 行，`GET /api/collab/users`） | 實作方已承認此端點仍列出 `SYSTEM.retention-purge`（含 `role: system`）。任何有架構圖編輯權的使用者都看得到這個內部帳號名，也能把圖分享給它（會在 `diagram_shares` 寫入一列指向它的資料）。不影響清除的完整性，因為它的刪、改角色、啟停用四個入口都已被擋，但違反「保留帳號對一般使用者不可見」的意圖，也是 `DEPLOY.md` 刻意註明的缺口。`team.md` 不允許趁機改動 `collab_router.py`，所以不構成本單元阻擋項。 | 保持現狀可接受；請在 `traceability.json` 的 `open_items` 登記一個有承接者的項目（目前只寫在 `DEPLOY.md` 與摘要的散文裡），讓它不會因為沒有編號而無人追蹤。 | Unresolved |
| R-06 | Minor | DEPLOY.md > §2.2.11「期限」段；merge-blockers.md 第 17 列 | 「本分支第一次部署到 staging 後 90 天內 `ut` 須併入 `main`」的前提成立：我確認 `origin/ut` 的 `schema_rbac.sql` 沒有 `memory_records`，且記憶寫入路徑只有 `memory_service.create_record`（`expires_at = created_at + 90 天`，無其他可回填過期時間的寫入者）。但這是純人工義務，沒有任何提醒機制，也沒有指定負責人與日期的記錄位置；文件只說「例如 issue 或團隊行事曆」。監看者（watchdog）在期限內同樣無法運作，這點文件已如實寫明，是對的。 | 在文件中指名一位負責人，並在第一次部署當天於 repo 內建立一個帶日期的 issue 作為唯一記錄位置，取代「例如」的選項清單。 | Resolved (reviewer) |
| R-07 | Minor | `.github/workflows/memory-retention-watchdog.yml` 的 `Read the purge workflow's last successful scheduled run` 與 `Decide whether the purge is overdue`；`DEPLOY.md` 第 1132–1155 行 | `ut` 併入 `main` 的第一天，監看（每日 06:23 UTC）會早於第一次排程清除（17:41 UTC）執行。`gh api` 此時回傳零筆成功的排程 run（state=`never`）或 404，兩者都判為逾期，所以第一天必然開出一則假的「清除逾期」issue 並讓 run 變紅。`code-summary.md` 重做節說「在 `ut` 併入 `main` 之前它一旦執行就會判逾期並開 issue」，這個方向不對：併入前兩支 workflow 都不在 `main`，根本不會執行；實際風險發生在併入之後的第一天，而 `DEPLOY.md` 的期限段落沒有提到。 | 在 `DEPLOY.md` §2.2.11 補寫：併入 `main` 後第一天可能出現一則假警報，並說明如何辨識（沒有任何成功的排程 run）。同時更正 `code-summary.md` 與 `merge-blockers.md` 第 17 列中「併入前即會觸發」的說法。 | New |
| R-08 | Minor | `.github/workflows/memory-retention-purge.yml` 檔頭註解（引用 `deploy.yml:376-378`、`:472`、`:124/:471`、`:149`、`:20-22`） | 這些行號是舊的。實際「Remove the generated env file」在 `deploy.yml:630-632`，rollback 刪除 `deploy/.env` 在 `:726`。事實本身仍成立（我逐項核對了 `rm -f deploy/.env` 與 `if: always()`），但這份註解正是 `--env-file deploy/.env.example` 偏離的唯一論證，行號失效會讓後來的維護者查不到證據。重做摘要已承認落差，卻沒有修正 workflow 內的註解。 | 把註解中的行號改為目前的位置，或改成用步驟名稱（「Remove the generated env file」）引用，避免日後再漂移。 | New |
| R-09 | Minor | `.github/workflows/memory-retention-purge.yml` 的 `Run the purge against the deploy stack database` 步驟 | 整條 `docker compose -f … --env-file deploy/.env.example exec -T db sh -c 'PGUSER=… psql …' < file` 路徑從未被實際執行過：CI 的 `memory-schema` 以 TCP 連 `postgres` 服務，重做輪的驗證用本機 PostgreSQL，開發環境也沒有 Docker。所以「psql 走容器內 socket 無需密碼」「容器內有 `POSTGRES_USER`／`POSTGRES_DB`」「`ps --status running --services` 輸出可被 `grep -qx db` 比對到」都只是推論。第一次真實驗證會是第一次排程，而排程一律是真實清除。 | 在 `DEPLOY.md` 的順序要求中明寫：併入 `main` 後那次 `dry_run=true` 的手動觸發同時是這條 compose 路徑的首次煙霧測試，必須確認它成功（不只是核對計數為 0），失敗就先停用排程。 | New |

> R-01 Reviewer note: `backend/tests_pg/test_purge_atomicity.py:58` 仍手寫 `SENTINEL_USERNAME = "SYSTEM.retention-purge"`；`test_sentinel_username_has_one_source`（`test_retention_purge_contract.py:358` 起）只解析 purge SQL、seed 腳本、`K)` 區塊，沒有涵蓋這第四處。本輪零程式改動，故未修；後果有界（改名後會大聲失敗，不會靜默）。

> R-02 Reviewer note: 既有的登入 `ValueError`（超過 72 位元組密碼）不屬本單元，`code-summary.md` 已如實記為 `OPEN-CG9-2`；無需本單元處置，需另開 issue 追蹤。

> R-03 Reviewer note: `DEPLOY.md` 第 1138–1154 行現在寫明併入 `main` 之後立即在 `main` 上 `dry_run=true` 跑一次，說明部署日＋90 天之前排程選取皆為零列，並規定已有測試資料時先停用排程。兩段文字不再互相矛盾。

> R-04 Reviewer note: `test_system_account_protection.py` 仍只有 A1–A7（刪除、改角色、啟用、列表、常數、拒絕、一般停用帳號），沒有核准授權申請（`user_router.py:925`）的案例；改角色、啟停用、拒絕三處也沒有做過突變。重做輪明確把突變驗證留在「未重跑」。

> R-05 Reviewer note: `GET /api/collab/users` 仍列出保留帳號。`traceability.json` 的 `MB-11` 說明（:251）把它寫在散文裡，沒有獨立、有承接者的 open_items 條目。

> R-06 Reviewer note: `DEPLOY.md` 已指名負責人 Danniel，並指定部署當天開立的 GitHub issue 為唯一記錄位置。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest tests.test_retention_purge_contract tests.test_system_account_protection`（`backend/.venv`） | `Ran 17 tests`，OK | 與摘要一致，#11 的 5 個端點與列表排除在 code 與測試中可查（`user_router.py` :846、:925、:974、:1055、:1173、:1243）。 |
| 手讀 `purge_expired_memory.sql`、`purge_dry_run.sql`、兩支 workflow、`schema_rbac.sql` 的 `memory.*` DDL | 未觸發任何 workflow、未連任何資料庫、未執行清除 SQL | 選取條件 `kind = 'episodic' AND expires_at < now()` 正確：`ck_memory_records_episodic_has_expiry` 不排除非 episodic 帶過期時間的列，所以 `kind` 條件確實必要。`memory_audit_events.memory_id` 沒有外鍵，所以刪記憶不會被稽核列擋下。稽核 INSERT 取自 DELETE 的 `RETURNING`，一個交易內「刪 N 列 ⇒ 寫 N 筆」是結構性恆等；哨符查不到時 `actor_user_id` 為 NULL，`NOT NULL` 違反使整個交易回滾，屬大聲失敗。 |

**`--env-file deploy/.env.example` 偏離（Step 8.1）的判斷**

- 必要性成立：`deploy.yml` 每次結束都 `rm -f deploy/.env`（:632、:726），指向不存在的 env file 是硬錯誤；排程每天都會失敗。
- 範本滿足內插：`CLOUDFLARED_CREDENTIALS_FILE` 在範本中有值（`.env.example:90`），compose 內沒有 `${…:?}` 必填語法，所以空的 `POSTGRES_PASSWORD` 最多是警告。
- 不會連到錯的資料庫：project 名稱由 `name: cloud360` 固定，CI 的短生命週期 stack 是 `cloud360test`，兩者不會互相命中；`exec` 只附著到已在運行的容器，身分與資料庫名取自容器自己的環境。範本值無法影響連線目標。
- 殘餘風險只有上面第三則：這條路徑沒有被實際跑過。

**#17 期限處置的判斷**：`DEPLOY.md` 現已準確記載 `workflow_dispatch` 同樣要求檔案在預設分支、90 天期限、負責人、記錄位置與併入後先 dry-run 的順序；`merge-blockers.md` 第 17 列誠實標為「持續中的人工義務」而非已修正。「部署前沒有記憶列，第一筆最早部署後 90 天到期」的前提，與 `schema_rbac.sql` 及 `expires_at = created_at + 90 天` 的寫入路徑一致。缺口只剩上面的第一天假警報與首次煙霧測試。

### Summary

0 個 Critical、0 個 Major、3 個新 Minor；上一輪 6 項中 R-03 與 R-06 已修，R-01、R-02、R-04、R-05 仍為 Minor。清除的選取條件、單一交易內的稽核恆等、保留帳號的 409 防護與 `--env-file` 偏離都站得住腳，本單元可以放行；殘留風險集中在 compose 呼叫路徑尚未實跑，以及併入 `main` 第一天的假警報，兩者都可靠文件順序處理。
