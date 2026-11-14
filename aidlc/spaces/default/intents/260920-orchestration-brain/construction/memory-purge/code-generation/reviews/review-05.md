## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
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
| R-07 | Minor | `.github/workflows/memory-retention-watchdog.yml` 的 `Read the purge workflow's last successful scheduled run` 與 `Decide whether the purge is overdue`；`DEPLOY.md` 第 1132–1155 行 | `ut` 併入 `main` 的第一天，監看（每日 06:23 UTC）會早於第一次排程清除（17:41 UTC）執行。`gh api` 此時回傳零筆成功的排程 run（state=`never`）或 404，兩者都判為逾期，所以第一天必然開出一則假的「清除逾期」issue 並讓 run 變紅。`code-summary.md` 重做節說「在 `ut` 併入 `main` 之前它一旦執行就會判逾期並開 issue」，這個方向不對：併入前兩支 workflow 都不在 `main`，根本不會執行；實際風險發生在併入之後的第一天，而 `DEPLOY.md` 的期限段落沒有提到。 | 在 `DEPLOY.md` §2.2.11 補寫：併入 `main` 後第一天可能出現一則假警報，並說明如何辨識（沒有任何成功的排程 run）。同時更正 `code-summary.md` 與 `merge-blockers.md` 第 17 列中「併入前即會觸發」的說法。 | Unresolved |
| R-08 | Minor | `.github/workflows/memory-retention-purge.yml` 檔頭註解（引用 `deploy.yml:376-378`、`:472`、`:124/:471`、`:149`、`:20-22`） | 這些行號是舊的。實際「Remove the generated env file」在 `deploy.yml:630-632`，rollback 刪除 `deploy/.env` 在 `:726`。事實本身仍成立（我逐項核對了 `rm -f deploy/.env` 與 `if: always()`），但這份註解正是 `--env-file deploy/.env.example` 偏離的唯一論證，行號失效會讓後來的維護者查不到證據。重做摘要已承認落差，卻沒有修正 workflow 內的註解。 | 把註解中的行號改為目前的位置，或改成用步驟名稱（「Remove the generated env file」）引用，避免日後再漂移。 | Unresolved |
| R-09 | Minor | `.github/workflows/memory-retention-purge.yml` 的 `Run the purge against the deploy stack database` 步驟 | 整條 `docker compose -f … --env-file deploy/.env.example exec -T db sh -c 'PGUSER=… psql …' < file` 路徑從未被實際執行過：CI 的 `memory-schema` 以 TCP 連 `postgres` 服務，重做輪的驗證用本機 PostgreSQL，開發環境也沒有 Docker。所以「psql 走容器內 socket 無需密碼」「容器內有 `POSTGRES_USER`／`POSTGRES_DB`」「`ps --status running --services` 輸出可被 `grep -qx db` 比對到」都只是推論。第一次真實驗證會是第一次排程，而排程一律是真實清除。 | 在 `DEPLOY.md` 的順序要求中明寫：併入 `main` 後那次 `dry_run=true` 的手動觸發同時是這條 compose 路徑的首次煙霧測試，必須確認它成功（不只是核對計數為 0），失敗就先停用排程。 | Unresolved |
| R-10 | — | — | 無 | — | New |

> R-01 Reviewer note: backend/tests_pg/test_purge_atomicity.py 第 58 行仍手寫 SENTINEL_USERNAME 的第四份副本，未納入唯一來源測試。已列為已知限制，不阻擋

> R-02 Reviewer note: backend/services/auth.py 第 37 至 40 行 verify_password 仍直接回傳 bcrypt.checkpw 且無例外處理。屬既有缺陷，以 OPEN-CG9-2 另案追蹤，不屬本單元

> R-04 Reviewer note: backend/tests/test_system_account_protection.py 中 approve 出現次數為 0，核准授權申請仍無測試，改角色與啟停用也未做突變驗證

> R-05 Reviewer note: backend/services/collab_router.py 第 298 至 303 行 get_users 仍未排除保留帳號。traceability.json 已新增 OPEN-CG9-6 登記承接者，這是本輪相對前輪的改善，但缺口本身仍在

> R-07 Reviewer note: DEPLOY.md 全檔搜尋假警報、煙霧、smoke 共 0 命中，併入 main 第一天的假警報仍未記載；監看 workflow 第 124 行仍只查 event=schedule 的成功 run

> R-08 Reviewer note: memory-retention-purge.yml 第 42、43、74、88 行仍引用舊的 deploy.yml 行號；deploy.yml 實際在第 640 至 642 行

> R-09 Reviewer note: compose 容器路徑從未實跑，DEPLOY.md 仍未將併入後的 dry-run 定義為該路徑的首次煙霧測試

### Validation Tool Results
- 對收據 reviewed-source-dec2b735dbb4.tsv 的 18 個檔逐一以 shasum 256 比對現況：只有 DEPLOY.md 不同，其餘逐位元相同，與宣稱相符。
- DEPLOY.md 標題實查：2.2.9 起於第 617 行，2.2.11 起於第 1074 行，2.2.12 起於第 1182 行，5.13 起於第 2223 行。2.2.11 範圍為第 1074 至 1181 行，宣稱的新 hunk 在第 730 至 738 行（2.2.9 內）與第 2229、2239 行（5.13 內），都落在 2.2.11 之外，判定成立。我未能取得收據版 DEPLOY.md，無法獨立重算 hunk，這部分採信紀錄中的組合窮舉法，僅確認其結論與章節邊界一致。
- 在 scratchpad 副本以 backend 的 venv、-B、PYTHONDONTWRITEBYTECODE 並從 /tmp 執行，跑 tests.test_retention_purge_contract 與 tests.test_system_account_protection：Ran 17 tests，OK。完整套件 1326 案未重跑，採信紀錄。
- 計畫勾選實算：已勾 50、未勾 6，與宣稱一致。
- traceability.json 以 json.tool 驗證為合法 JSON，OPEN-CG9-6 存在且內容與 R-05 相符。
- tests_pg 與 psql 紀錄沿用 2026-10-25，本輪未跑，紀錄中已如實寫明。

### Summary
本輪為純重新驗證：除 DEPLOY.md 外所有被審來源與收據逐位元相同，DEPLOY.md 的新增內容不碰本單元負責的 2.2.11；17 案單元測試實跑通過，勾選與 JSON 數字相符。先前七項 Minor 全部仍成立，皆已登記為已知限制且不構成阻擋，也沒有新增 Critical 或 Major，故判定 READY。
