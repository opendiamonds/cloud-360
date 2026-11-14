## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Fixed | Minor | tests_pg/test_purge_atomicity.py 已不含哨符字面值（grep 全 repo 的 backend 與 .github 只剩 system_accounts.py:28 與 seed_retention_system_actor.py:102 兩處）。test_sentinel_username_has_one_source 改為以 AST 掃全 repo 的 .py，字面字串只准出現在兩檔允許清單，並從被測檔解析三處 SQL 與 Python 物化值而非手寫。 |
| R-02 | Still applies | Minor | backend/services/auth.py:36-39 的 verify_password 仍直接 return bcrypt.checkpw，無 try/except，超過 72 位元組的密碼仍會對既有帳號拋 ValueError。屬既有缺陷、不在本單元範圍，已以 OPEN-CG9-2 另案追蹤並誠實揭露；本單元不阻擋。 |
| R-04 | Fixed | Minor | test_system_account_protection.py 新增 A8（核准授權申請回 409，角色、授權狀態、申請狀態皆不變，申請 decided_by 仍為空）與 A9（PUT /active 重送 is_active=false 仍回 409）。code-summary 第三節的突變表有核准（c1）、啟停用（c3、c3'）逐項「拿掉判定即轉紅」並以 cmp 還原複驗，記載與測試內容一致。 |
| R-05 | Fixed | Minor | traceability.json 的 open_items 已登記 OPEN-CG9-6（GET /api/collab/users 仍列出保留帳號），有 landing 欄位指定承接者。 |
| R-07 | Fixed | Minor | DEPLOY.md 已新增「併入 main 當天必有一則假的清除逾期 issue」的辨識三條件與處置，並與 memory-retention-watchdog.yml 的 state=never 判定、原因句、issue 標題逐字一致。code-summary 重做節 R-07 列明確標註舊說法「方向錯誤、以本列為準」；第 570 行的歷史敘述仍保留舊說法，但已被同檔後文推翻，不再構成誤導。 |
| R-08 | Fixed | Minor | memory-retention-purge.yml 檔頭註解已改以 job 與步驟名稱引用 deploy.yml，不再依賴行號。仍有一處同類殘留，見下方新發現。 |
| R-09 | Fixed | Minor | DEPLOY.md 已寫明併入 main 後那次 dry_run=true 手動觸發同時是 docker compose 路徑的首次煙霧測試，失敗時先在 Actions 介面停用排程，修好並以 dry_run=true 跑綠後才重新啟用。 |
| R-10 | Fixed | — | 原列為無發現，無事可複驗。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | backend/tests_pg/test_purge_atomicity.py 模組 docstring（第 8 行） | docstring 仍引用 deploy.yml:124 與 :471 作為 docker compose up --remove-orphans 的位置。目前實際位置是 deploy.yml:143 與 :798，所以行號已失效，與 R-08 已在 workflow 註解處理掉的是同一類問題。code-summary 已自承此項未處理。 | 改為以 deploy.yml 的 job 與步驟名稱引用（deploy 的 Build and start the stack、rollback 的 Restore the last-good deployment），或更新為目前行號。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-purge/code-generation/code-generation-plan.md 未勾格 1.3 與 12.5 | 兩格的未勾理由已過時。1.3 的條件是 git diff --stat -- backend/database.py 必須為空：現況 git diff HEAD 對該檔為空，最後一次提交為 ff537a7，先前未提交的 +72 行已併入提交。12.5 的 database.py 子句同理成立，且 CI run 42454550208（head ff537a7）除 tests_pg C3 外全綠，涵蓋 repo contract、env contract 與 backend unittest（ci.yml:154、:159、:320）。 | 1.3 可勾。12.5 可依上述 CI 證據勾選並在 code-summary 註記證據來源。1.4（K) 區塊已存在且恰為一個，照字面不可能成立）、2.6、8.1（--env-file deploy/.env.example 的偏離仍成立）與最後兩格人工義務維持未勾。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 收據重算（最新者 reviewed-source-5daebbd562fa.tsv，以 awk -F 取欄位、shasum -a 256 逐檔重算） | 18 檔全部相同 | 以最新收據為準時沒有任何來源漂移。 |
| 舊收據 7cb3888048dc 對照新收據 | 3 檔不同：backend/scripts/verify_memory_schema.sql、frontend/src/types/api.d.ts、openapi.json | git show ff537a7 判定來源：verify_memory_schema.sql 只多一行 S15 搜尋函式的 expires_at 過濾；api.d.ts 與 openapi.json 只是記憶端點的 503 回應與 4000 字元上限描述。三者皆為記憶服務單元的修正，不碰本單元的清除 SQL、哨符、保留帳號 409 守門或 workflow。 |
| git diff HEAD 針對 code-generation-plan.md | 無差異 | 計畫檔與 HEAD 逐位元相同，勾選回復屬實（55 勾、7 未勾，grep 實數吻合）。 |
| git diff HEAD 針對 code-summary.md | 僅檔尾新增 13 行「整站重跑後的勾選回復」 | 該節陳述的 3 變檔名、勾選數與 7 個未勾格皆經核實屬實。其中「以舊收據重算」的說法有效，且新收據已於 21:44 產生。 |
| code-generation-questions.md 差異 | 僅計畫核准紀錄由已核准改為計畫核准關閉 | 與本單元實作無關。 |
| 測試與建置類指令 | 依指示未執行 | 以讀碼推演判定，不影響來源指紋。 |

### Summary

上一輪的 Minor 發現中，R-01、R-04、R-05、R-07、R-08、R-09 已實質處置並在 repo 內查得到證據，只有既有的 auth.py 72 位元組缺陷（R-02）仍適用，且已另案追蹤，不屬本單元範圍。以最新收據重算，18 檔全部吻合，三個與舊收據不同的檔案都是記憶服務單元的改動，沒有碰到本單元的修正段落。僅有兩項新的 Minor：測試檔 docstring 內失效的 deploy.yml 行號，以及計畫 1.3 與 12.5 的未勾理由已過時、可以勾選。

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
