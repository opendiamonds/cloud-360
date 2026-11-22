## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-22T23:30:31Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `backend/tests_pg/test_purge_atomicity.py:58` (`SENTINEL_USERNAME = "SYSTEM.retention-purge"`) | The plan (Step 7, assertion 6) and `code-summary.md` both claim the sentinel username is materialized in exactly three places and that `test_sentinel_username_has_one_source` locks all three to the same string. There is in fact a **fourth** hardcoded copy in `test_purge_atomicity.py`, and that test is not checked by `test_sentinel_username_has_one_source` (which only parses `schema_rbac.sql`'s `K)` block, `purge_expired_memory.sql`, and `seed_retention_system_actor.py`). A future rename of the sentinel in the three guarded places would leave this fourth copy stale and unguarded. Impact is bounded — a mismatch would surface as a loud test failure (actor not found) rather than a silent one — but the "single source of truth, locked by a test" claim as written is inaccurate. | Either add `test_purge_atomicity.py` as a fourth file parsed by `test_sentinel_username_has_one_source`, or import `SENTINEL_USERNAME` from `seed_retention_system_actor.py` instead of re-declaring it, and correct the "three places" wording in `code-summary.md`/the plan. | New |
| R-02 | Minor | `backend/services/user_router.py:403-408` / `backend/services/auth.py:37-40` (pre-existing, confirmed via `code-summary.md` finding `F-1`) | Empirically reproduced via `TestClient`: a login request with a password longer than 72 bytes against an **existing** username raises an uncaught `ValueError` from `bcrypt.checkpw` inside `verify_password` (confirmed locally: 72-byte password → clean 401; 73-byte password → unhandled `ValueError: password cannot be longer than 72 bytes`), which FastAPI would turn into an unauthenticated 500 in production — a real account-existence oracle. This is pre-existing code outside this unit's `packaging` scope, and `code-summary.md` discloses it honestly as `OPEN-CG9-2` with a reasoned "won't fix here" (does not belong to this unit, team.md bars bundling unrelated refactors). The sentinel actor's own hash is unaffected (verified clean `False` return for legal-length inputs via the contract test). Recorded here only to confirm the disclosure is accurate and the risk is real, not to block this unit. | No action required in this unit; track `OPEN-CG9-2` as a separate issue against `auth.py` as the plan already proposes. | New |
| R-03 | Major | DEPLOY.md > §2.2.11「首次啟用前必須先驗證選取條件」與新增的「期限」段 | 新裁決讓 `workflow_dispatch` 在 `ut` 併入 `main` 前完全不可用，但「首次啟用前必須先以 `dry_run=true` 手動觸發驗證選取條件」這條（對應 `OPEN-ID9-4`：已執行的清除不可回滾）原封不動留在同一節。併入 `main` 的當天，排程就會開始跑，而排程一律是真實清除（`memory-retention-purge.yml` 約第 144 行「A scheduled run ALWAYS performs the real purge」）。想先 dry-run，只能在合併後、第一次排程之前搶先手動觸發，文件沒有要求這個順序，也沒有說明這是競態。結果是 `OPEN-ID9-4` 規定的 blocking-downstream 前置驗證，在文件上被宣稱需要，實際上無法保證做得到。原計畫 Step 14 的第 ① 項（dry-run 驗證）一併落空，新裁決沒有為它另設處置。 | 在 §2.2.11 明寫合併 `ut`→`main` 時的順序要求，並選一種處置：（a）要求在 `main` 取得兩支 workflow 檔之後、第一次排程時間之前，先手動 `dry_run=true` 並核對邊界，再讓排程接手，同時寫出這個窗口有多長；或（b）明說 dry-run 驗證無法先於第一次真實清除，並依「期限內無任何逾期資料」的論點，記為已接受的殘留風險，同步更新 `traceability.json` 的 `OPEN-ID9-4`。兩者擇一，不要讓兩段文字互相矛盾。 | New |
| R-04 | Minor | backend/tests/test_system_account_protection.py；code-summary.md「重新查驗與合併前必修第 11、17 項」二節的突變表 | 實作宣稱五個端點的 409，但核准授權申請（`POST /authorization-requests/{id}/approve`）沒有任何測試。A1–A7 涵蓋刪除、改角色、啟用、列表、常數、拒絕、一般停用帳號，唯獨沒有核准。突變驗證也只做了刪除與列表兩項。把核准、改角色、啟停用三處的保留判定拿掉，測試仍有可能全綠，只有 A2、A3、A6 對應各自的路徑，但這三條沒有被實際突變驗證過。核准路徑是這四道鎖中「角色」那道的第二個入口，被標為縱深防禦卻無任何斷言保護。另外，`PUT /active` 的 409 在 `Union` 宣告下，也沒有斷言 `is_active=false` 重送同樣被擋。 | 補一個核准保留帳號回 409、角色與申請狀態皆不變的案例；對改角色、啟停用、核准各做一次「拿掉判定即轉紅」的突變，並寫入 `code-summary.md`。 | New |
| R-05 | Minor | backend/services/collab_router.py > `get_users`（約第 304 行，`GET /api/collab/users`） | 實作方已承認此端點仍列出 `SYSTEM.retention-purge`（含 `role: system`）。任何有架構圖編輯權的使用者都看得到這個內部帳號名，也能把圖分享給它（會在 `diagram_shares` 寫入一列指向它的資料）。不影響清除的完整性，因為它的刪、改角色、啟停用四個入口都已被擋，但違反「保留帳號對一般使用者不可見」的意圖，也是 `DEPLOY.md` 刻意註明的缺口。`team.md` 不允許趁機改動 `collab_router.py`，所以不構成本單元阻擋項。 | 保持現狀可接受；請在 `traceability.json` 的 `open_items` 登記一個有承接者的項目（目前只寫在 `DEPLOY.md` 與摘要的散文裡），讓它不會因為沒有編號而無人追蹤。 | New |
| R-06 | Minor | DEPLOY.md > §2.2.11「期限」段；merge-blockers.md 第 17 列 | 「本分支第一次部署到 staging 後 90 天內 `ut` 須併入 `main`」的前提成立：我確認 `origin/ut` 的 `schema_rbac.sql` 沒有 `memory_records`，且記憶寫入路徑只有 `memory_service.create_record`（`expires_at = created_at + 90 天`，無其他可回填過期時間的寫入者）。但這是純人工義務，沒有任何提醒機制，也沒有指定負責人與日期的記錄位置；文件只說「例如 issue 或團隊行事曆」。監看者（watchdog）在期限內同樣無法運作，這點文件已如實寫明，是對的。 | 在文件中指名一位負責人，並在第一次部署當天於 repo 內建立一個帶日期的 issue 作為唯一記錄位置，取代「例如」的選項清單。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依派工限制，本輪未執行任何測試、lint、build 或 Python 命令 | 不適用 | 以讀取 diff、原始碼與 openapi.json 取代。已確認：`openapi.json` 的 `PUT /api/auth/{user_id}/active` 409 為 `anyOf[LastAdminGuardReport, ReservedAccountConflict]`，原守門報告形狀未變；保留判定為單一來源（`system_accounts.py`），並由 A5 以 AST 與 seed 腳本的 `SENTINEL_USERNAME` 比對；`GET /list` 的排除在查詢層，`total` 與分頁共用同一基底查詢；沒有任何路由能寫 `password_hash`、改 `username` 或繞過四道鎖，登錄與註冊的 `.lower()` 也產生不出保留名。 |

### Summary

#11 的實作是紮實的：四道鎖的所有入口都已封住，判定單一來源且有一致性測試，列表在查詢層排除，與 `hierarchy-data`、`membership-service` 的改動沒有互相干擾（保留帳號在兩者的邏輯之前即回 409；它是停用帳號，也進不了成員或繼任者清單）。主要的架構疑慮在 #17：延後的裁決本身合理，但它讓 `OPEN-ID9-4` 要求的「首次真實清除前先 dry-run」在文件上仍被宣稱、實際卻無法保證，這點需要在 DEPLOY.md 內修正成一致的說法。其餘為測試覆蓋與追蹤登記的 Minor。
