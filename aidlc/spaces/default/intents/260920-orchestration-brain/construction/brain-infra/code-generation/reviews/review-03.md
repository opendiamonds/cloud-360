## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四個勾選（`redis` 的 `command:` ... `--maxmemory-policy allkeys-lru`） | 這一格已勾回，但格子本文逐字要求的 `allkeys-lru` 在 repo 現況不成立：`deploy/docker-compose.deploy.yml` 的 redis `command:` 現為 `noeviction`（約 :258-276，註解引 NFR4.50／`[N3]=A`，由後續提交 `c2e5687a` 改入）。code-summary 承認「policy 值已被後續決定改變」，卻仍照原樣勾回，等於勾選了一個字面上為假的條件。複查者若只看勾選狀態，會以為 `allkeys-lru` 仍被驗過。 | 在該格就地標註「依 NFR4.50／`[N3]=A` 由 `noeviction` 取代，後續單元決定」，或把判準改為「`command:` 含 `--appendonly yes`、`--maxmemory`、且 policy 旗標存在」。不要在判準與現況字面不符的情況下直接勾選。 | Unresolved |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > AC2.1.4 的 note（約 :63）、S-8／S-9 的 note（約 :219、:255） | 三處敘述已過期且會誤導下游：AC2.1.4 仍寫 `--maxmemory-policy allkeys-lru`（現為 `noeviction`，改變了「滿了之後」的行為：寫入被拒而非淘汰）；S-8 寫「十個服務項（deploy 六＋test 四）全部設記憶體上限」、S-9 寫「六個 deploy 服務」，但 deploy compose 已有第七個服務 `mcp-bridge`（512m，`networks: [mcp]`），現為十一項、七個服務。本輪已知這些過期卻不改，下游單元（session-store 判斷第 18 項容量時）會讀到錯的政策。 | 在這三列 note 末尾追加「截至 HEAD `fa51564`：policy 為 `noeviction`；deploy 為 7 個服務、記憶體上限共 11 項（含 mcp-bridge）」，或把這些敘述標為「交付當時」並指向 code-summary 末節；不要讓 `allkeys-lru` 在可機讀檔裡被當作現況。 | Unresolved |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/unit-test-instructions.md > 第三節本單元專屬命令（約 :43、:56）與 `test_vector_extension_bootstrap.py（6 個）`（:64） | 命令用 `python -m unittest`，但 code-summary 實查本機 PATH 沒有 `python` 只有 `python3`；全套測試在系統 Python 會因 `mcp` 為 1.29.0（釘選 2.3.0）出現 28 個失敗，唯有 `backend/.venv/bin/python` 全綠（1204 tests OK）。此外測試數寫「6 個」而檔內實為 7 個 `def test_`。照這份說明跑的人會得到紅燈或空命令，且無法判斷是本單元壞了。 | 在說明中補 `backend/.venv/bin/python` 與 `PYTHONDONTWRITEBYTECODE=1`，並把測試數更正為 7。若此檔被核可指紋綁定而不能改，至少在 code-summary 與下一單元的交接處明列此為已知替代命令。 | Unresolved |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 「19 項合併前必修與本單元的關係」 | 「劃給 brain-infra 的為 0 項」就清單標示的單元欄成立，但有四項的實際修法會落在本單元的 13 個檔上：#15（部署步驟須把成員回填排在對外開放之前，落點是 `deploy.yml`／`DEPLOY.md`，目前 `deploy.yml` 無任何回填步驟，僅 `DEPLOY.md` §2.2.10 文字要求）、#16（鎖逾時與連線池，落點是 `backend/database.py` 的 engine 設定）、#18（Redis 容量，落點是 deploy compose 的 `command:`）、#19（`OPENROUTER_API_KEY` secret，`deploy.yml` :83 已有 required-secret 檢查，這一項實際已有守門）。本單元的審查收據與勾選因此會被他單元的修改再次改寫，卻沒有任何紀錄指明這些檔案的修改權屬。 | 在 code-summary 該節補一張「跨單元落點」表，列 #15／#16／#18／#19 各自會改到本單元哪個檔，並寫明由哪個單元負責、改完是否需要回頭重驗本單元對應勾選；#19 註明守門已存在於 `deploy.yml` :83。 | Unresolved |
| R-05 | Minor | deploy/docker-compose.deploy.yml > `mcp-bridge` 服務與 `mcp` 網段；aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 後續變更第 3 點 | ADR-0006 四面向逐項核對後本單元判準未失效：IAM（redis `default` 仍只有 `+@connection`，app 使用者仍 `-@admin -@dangerous`，兩個身分在 `deploy.yml` 有探測）、network exposure（`mcp-bridge` 僅在 `internal: true` 的 `mcp` 網段、無 `ports:`，`cloudflared` 仍只在 `edge`）、audit logging 無變動。唯一待補的是 encryption：使用者 JWT 在 `mcp` 網段以明文往返（merge-blockers #7，仍待人裁決），而 code-summary 只在「語意變動」中提到服務與網段新增，沒有把它連到本單元「網路分段」這項控制的前提，讀者會誤以為分段已涵蓋該風險。 | 在 code-summary 後續變更第 3 點補一句「`mcp` 網段的明文往返屬 #7，本單元的網路分段不處理 encryption」，避免被當成已由本單元覆蓋。 | Unresolved |

> R-01 Reviewer note: 計畫 Step 6 第四個勾選（`code-generation-plan.md` 約 :180-181）仍逐字寫 `--maxmemory-policy allkeys-lru` 並維持勾選；`deploy/docker-compose.deploy.yml` :273-274 的註解明寫 `noeviction`，NOT `allkeys-lru`。本輪只追加了重新驗證一節，未就地標註。

> R-02 Reviewer note: `traceability.json` 無任何 `noeviction` 或 HEAD 註記（grep 零命中），AC2.1.4、S-8、S-9 的過期敘述未動。

> R-03 Reviewer note: `unit-test-instructions.md` :43、:56 仍用 `python -m unittest`；本輪副本實測以 `backend/.venv/bin/python` 跑才綠（16 個測試 OK）。

> R-04 Reviewer note: `code-summary.md` 未新增「跨單元落點」表；本輪補的是重新驗證一節，與此項無關。

> R-05 Reviewer note: `code-summary.md` 未補「`mcp` 網段明文往返屬 #7，網路分段不處理 encryption」；grep 只命中無關的一行。

### Validation Tool Results

- `git diff 624c170 7a50a40 -- .github/workflows/deploy.yml`：共 6 組變動（deploy job 的 `outputs` 加 `brain_ws_probe_failed`、步驟 6a 加 `id`、rollback 開頭註解、revert 步驟的 `if`、notify 的 `env` 與「刻意未開」分支，另有一處 :520 的行號註解）。除 :520 的註解行號外，全部與開發者所述 #26 一致。
- `git diff 624c170 7a50a40 -- DEPLOY.md`：19 組變動。我確認 :729-738（#24）與 §5.13 兩處（約 :2229、:2239）內容與開發者所述一致。「其餘 16 組在收據之前」的窮舉子集證明，我沒有重算。
- 本單元負責的步驟（必填 secret 檢查、`REDIS_PASSWORD`、Redis ACL 驗證、ollama pull、資料面探測、rollback 的 restore 與健康檢查迴圈）均不在上述變動內。`rollback` job 的 `if` 仍為 `failure() && needs.deploy.result == 'failure' && merged`。「Restore the last-good deployment」步驟的條件與輸出未動。被收窄的只有 revert 步驟（`always() && ... != 'true'`），所以每一種失敗來源仍會先還原 last-good，包含 6a 失敗。
- 副本（只複製 `backend/`、`deploy/`、`DEPLOY.md`、`LOCAL-DEV.md`、`schema_rbac.sql`、`docker-compose.yml`，`PYTHONDONTWRITEBYTECODE=1`、`-B`）：`tests.test_vector_extension_bootstrap` 與 `tests.test_render_env_redis` 共 16 個測試 OK。副本已刪除，工作樹的非 `aidlc/` 部分沒有新增檔案。

### Summary

共用檔異動（#24、#26）確實只落在 `deploy.yml` 與 `DEPLOY.md` 的非本單元段落，rollback 對所有失敗來源仍還原 last-good，本單元測試在副本仍綠，重新驗證結論成立。但前輪的 Major（R-01：計畫 Step 6 勾選的 `allkeys-lru` 與現況 `noeviction` 字面不符）及 4 項 Minor 都沒有處理，所以我維持 NOT-READY。只要在該勾選就地標註「依 NFR4.50／[N3]=A 由 noeviction 取代」即可關閉 R-01。
