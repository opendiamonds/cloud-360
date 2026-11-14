## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-10 | Still applies | Minor | code-summary.md 第 230 行標題仍寫「勾回 42、未勾 1」,其下無歷史快照標記。文件陳述問題,不影響程式。 |
| R-11 | Still applies | Minor | traceability.json 的 AC2.1.4 note 已附 noeviction 更正,但 code-summary.md 第 295 行仍說該 note 寫 allkeys-lru、本輪不改寫,與現況不符。 |
| R-12 | Still applies | Minor | traceability.json 的 ADR-0006 note 仍寫單一 superuser 原樣承接,未反映 cloud360_memory 角色與 MEMORY_DB_PASSWORD;合併前必修整節仍無四面向判定表。 |
| R-13 | Still applies | Minor | DEPLOY.md 順序段仍只寫會觸發 rollback,沒寫 rollback 自動開 revert PR,也沒寫 rollback 的 render-env 同樣需要該 secret。 |
| R-14 | Still applies | Minor | deploy/initdb/02-memory-role-password.sh 第 15 行仍指向 LOCAL-DEV.md H6,實際在 H7;H7 未提醒需要 psql 15 以上。 |
| R-15 | Still applies | Minor | unit-test-instructions.md 現況註記仍寫 A1 到 A11 與六支新測試檔,漏列四支新測試與 verify_memory_role.sql。 |
| R-16 | Still applies | Minor | DEPLOY.md 與 deploy 目錄仍無 log_statement 不得為 ddl 或 all 的前提說明。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 計畫勾選實算(grep) | 68 勾、0 未勾 | 與新節宣稱的現況一致。 |
| git diff HEAD 加 numstat(計畫檔) | 1 行新增、1 行刪除,唯一差異是 A11 格的未勾改為已勾,其餘文字逐字相同 | 符合「只有勾選字元差異」,67 格勾回與 HEAD 一致。 |
| A11 補勾依據核對 | requirements.txt 第 78、79 行為 sse-starlette==3.0.3、mcp-types==2.3.0;ci.yml 第 264、446、632 行有 pip install -r requirements.txt;ff537a7 存在於本地歷史 | 釘選與 CI 安裝步驟成立。CI run 42454550208 的實際結果我未能連網複驗(限制不允許 gh),採信協調者陳述與已知 CI 結果;釘選與步驟本身已由讀碼確認。 |
| 新節內容核對(code-summary.md 第 617 行起) | 背景、依據、A11 說明、68 勾/0 未勾四點皆與上列實查相符 | 內容屬實。 |
| 來源指紋抽查(shasum -a 256) | requirements.txt、DEPLOY.md、deploy.yml 的雜湊與收據逐位元相同;git status 無應用程式碼變動 | 來源檔未動,沿用上次 50 個檔案全數相同的判定。 |

### Summary

此次僅計畫勾選與 code-summary 新節變動,差異驗證為只有 A11 勾選字元,依據與新節內容屬實,上次的勾選重設發現已解決;來源指紋未變。零 Critical、零 Major,七項舊 Minor 皆為文件陳述過期,不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四個勾選（`redis` 的 `command:` ... `--maxmemory-policy allkeys-lru`） | 這一格已勾回，但格子本文逐字要求的 `allkeys-lru` 在 repo 現況不成立：`deploy/docker-compose.deploy.yml` 的 redis `command:` 現為 `noeviction`（約 :258-276，註解引 NFR4.50／`[N3]=A`，由後續提交 `c2e5687a` 改入）。code-summary 承認「policy 值已被後續決定改變」，卻仍照原樣勾回，等於勾選了一個字面上為假的條件。複查者若只看勾選狀態，會以為 `allkeys-lru` 仍被驗過。 | 在該格就地標註「依 NFR4.50／`[N3]=A` 由 `noeviction` 取代，後續單元決定」，或把判準改為「`command:` 含 `--appendonly yes`、`--maxmemory`、且 policy 旗標存在」。不要在判準與現況字面不符的情況下直接勾選。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > AC2.1.4 的 note（約 :63）、S-8／S-9 的 note（約 :219、:255） | 三處敘述已過期且會誤導下游：AC2.1.4 仍寫 `--maxmemory-policy allkeys-lru`（現為 `noeviction`，改變了「滿了之後」的行為：寫入被拒而非淘汰）；S-8 寫「十個服務項（deploy 六＋test 四）全部設記憶體上限」、S-9 寫「六個 deploy 服務」，但 deploy compose 已有第七個服務 `mcp-bridge`（512m，`networks: [mcp]`），現為十一項、七個服務。本輪已知這些過期卻不改，下游單元（session-store 判斷第 18 項容量時）會讀到錯的政策。 | 在這三列 note 末尾追加「截至 HEAD `fa51564`：policy 為 `noeviction`；deploy 為 7 個服務、記憶體上限共 11 項（含 mcp-bridge）」，或把這些敘述標為「交付當時」並指向 code-summary 末節；不要讓 `allkeys-lru` 在可機讀檔裡被當作現況。 | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/unit-test-instructions.md > 第三節本單元專屬命令（約 :43、:56）與 `test_vector_extension_bootstrap.py（6 個）`（:64） | 命令用 `python -m unittest`，但 code-summary 實查本機 PATH 沒有 `python` 只有 `python3`；全套測試在系統 Python 會因 `mcp` 為 1.29.0（釘選 2.3.0）出現 28 個失敗，唯有 `backend/.venv/bin/python` 全綠（1204 tests OK）。此外測試數寫「6 個」而檔內實為 7 個 `def test_`。照這份說明跑的人會得到紅燈或空命令，且無法判斷是本單元壞了。 | 在說明中補 `backend/.venv/bin/python` 與 `PYTHONDONTWRITEBYTECODE=1`，並把測試數更正為 7。若此檔被核可指紋綁定而不能改，至少在 code-summary 與下一單元的交接處明列此為已知替代命令。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 「19 項合併前必修與本單元的關係」 | 「劃給 brain-infra 的為 0 項」就清單標示的單元欄成立，但有四項的實際修法會落在本單元的 13 個檔上：#15（部署步驟須把成員回填排在對外開放之前，落點是 `deploy.yml`／`DEPLOY.md`，目前 `deploy.yml` 無任何回填步驟，僅 `DEPLOY.md` §2.2.10 文字要求）、#16（鎖逾時與連線池，落點是 `backend/database.py` 的 engine 設定）、#18（Redis 容量，落點是 deploy compose 的 `command:`）、#19（`OPENROUTER_API_KEY` secret，`deploy.yml` :83 已有 required-secret 檢查，這一項實際已有守門）。本單元的審查收據與勾選因此會被他單元的修改再次改寫，卻沒有任何紀錄指明這些檔案的修改權屬。 | 在 code-summary 該節補一張「跨單元落點」表，列 #15／#16／#18／#19 各自會改到本單元哪個檔，並寫明由哪個單元負責、改完是否需要回頭重驗本單元對應勾選；#19 註明守門已存在於 `deploy.yml` :83。 | Resolved (reviewer) |
| R-05 | Minor | deploy/docker-compose.deploy.yml > `mcp-bridge` 服務與 `mcp` 網段；aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 後續變更第 3 點 | ADR-0006 四面向逐項核對後本單元判準未失效：IAM（redis `default` 仍只有 `+@connection`，app 使用者仍 `-@admin -@dangerous`，兩個身分在 `deploy.yml` 有探測）、network exposure（`mcp-bridge` 僅在 `internal: true` 的 `mcp` 網段、無 `ports:`，`cloudflared` 仍只在 `edge`）、audit logging 無變動。唯一待補的是 encryption：使用者 JWT 在 `mcp` 網段以明文往返（merge-blockers #7，仍待人裁決），而 code-summary 只在「語意變動」中提到服務與網段新增，沒有把它連到本單元「網路分段」這項控制的前提，讀者會誤以為分段已涵蓋該風險。 | 在 code-summary 後續變更第 3 點補一句「`mcp` 網段的明文往返屬 #7，本單元的網路分段不處理 encryption」，避免被當成已由本單元覆蓋。 | Resolved (reviewer) |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > 「重新驗證審查（review-03）的五項文件修正」一節 R-03 勾選 | 該格已打勾 [x]，內文寫「unit-test-instructions.md 本單元命令改為 PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B …，測試數更正為實數」，但 git 顯示該檔沒有任何變動，內容仍是舊命令與 6、5 個。code-summary 才承認未改。計畫勾選了一個字面上為假的條件，與前輪 R-01 同形；只讀計畫的複查者會以為說明檔已修好。 | 把該格改成如實描述：標明不改該檔的原因，並註明替代命令與實數記在 code-summary 末節；或取消打勾。計畫與 code-summary 對 R-03 的說法必須一致。 | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > R-03 處置說明（「不改該檔」的理由） | 不改說明檔的理由是它與計畫綁在同一份核可、改了會使核可失效；但同一輪已為 R-01 修改了計畫本身，且 traceability.json 也改了。理由前後不一，無法說服人替代做法是唯一可行路徑。 | 補一句說明為何計畫與可機讀檔可改而說明檔不可改（例如指紋或收據綁定的具體差異），或改採就地加一行指向 code-summary 的標註。 | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > I2 的 note（約 :255） | 寫「六個 deploy 服務 ＋ 四個 CI test 服務」，與同檔已更正的 S-8、S-9 不一致；deploy 現為 7 個服務。本輪只補了三列，同一事實的另一種表達形式漏掉。 | 在 I2 note 末尾追加與 S-8 相同的「截至 HEAD」標註。 | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四格註記與 code-summary「逐步查驗摘要（43 個勾選：勾回 42、未勾 1）」 | 計畫檔現況有 45 個未勾、5 個已勾（僅新增一節的五格），HEAD 版為 43 個已勾；Step 6 註記說「本格的勾選只代表…」，但該格目前沒有勾，code-summary 又宣稱勾回 42。兩者讀起來互相矛盾。 | 在 code-summary 註明計畫勾選狀態會被引擎於重開時重設，勾選結果以逐步查驗摘要為準，或讓計畫勾選與摘要一致。 | Resolved (reviewer) |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 「逐步查驗摘要（43 個勾選：勾回 42、未勾 1）」（:230）與其表內 Step 11 的「2／3」（:244） | 舊段落標題與表格仍以現在式寫「勾回 42、未勾 1」，段內沒有任何指向後文的標記。與計畫現況 55 全勾相矛盾，只有讀到 :307 的補勾與 :373 的「以本節為準」才解開。只讀到 :230 的人仍會得到互相矛盾的印象。 | 在 :230 標題下加一行：此為 2026-10-20 的歷史快照，未勾的 Step 11 第三格已於 :305 補勾，現況以 :371 起的本輪重驗為準。不需改任何數字。 | Unresolved |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四格（:202-204），以及 code-summary.md > 後續變更第 1 點（:295） | 第四格仍是 [x]，其正文字面寫 --maxmemory-policy allkeys-lru，而 deploy compose :273-289 實為 noeviction。註記已聲明勾選只代表旗標存在，因此不算新的虛假勾選，但格內條件文字本身仍為假。另外 :295 還說 traceability.json 的 AC2.1.4 註記仍寫 allkeys-lru、本輪不改寫，但該列 note 已追加截至 HEAD 的更正，此句與現況不符；計畫第一節故事追溯表（:31）也仍以 allkeys-lru 描述 AC2.1.4 的落點，沒有就地註記。 | 把 :295 改為「AC2.1.4 note 已附截至 HEAD 更正，第一節追溯表（:31）仍為交付當時敘述」。計畫的 :31 與第四格文字屬核可內容，不必為此重開核可；在 code-summary 交接處記明即可，下一個讀計畫的人才不會把 allkeys-lru 當現況。 | Unresolved |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > id ADR-0006 的 note，以及 code-summary.md > 「合併前必修：共用檔集中修正的處置」整節 | 本輪新增第二個資料庫身分 cloud360_memory、新 secret MEMORY_DB_PASSWORD，並在刪除使用者稽核加入清除筆數，都落在 IAM 與 audit logging 兩個面向。但 ADR-0006 那一列的 note 仍寫「既有缺口（PostgreSQL 單一 superuser）原樣承接」，與現況不符；新增的整節也沒有逐面向的判定表。專案規則要求涉及 IAM 與稽核的變更在產出內明列影響與處置，不得只靠 MB-20 與 MB-29 兩列帶過。 | 在 code-summary 新節補一張四面向判定表。IAM：新增只讀寫 memory schema 的角色，但記憶表實際存取仍走擁有者連線，邊界尚未對生產程式碼生效。Encryption：scram 雜湊儲存，連線字串不含 $，docker compose exec 的 -e 讓密碼出現在 runner 主機端 argv（已接受）。Network exposure：無新增 port。Audit logging：A4 稽核筆數。並把 ADR-0006 那列 note 附上截至 HEAD 的更正。 | New |
| R-13 | Minor | DEPLOY.md > §2.2.8「記憶專用資料庫角色」小節的「既有環境的順序」段 | 文件寫「否則部署步驟會失敗並觸發 rollback」，但沒寫兩個實際後果。其一：rollback job 會暫存「目前的」render-env.sh 再 checkout last-good，新版 render-env.sh 把 MEMORY_DB_PASSWORD 列為必填，因此在 secret 尚未建立的情況下（現況就是），rollback 自己的 render 步驟也會失敗，restored 結果不明。其二：只要不是 brain_ws_probe_failed，rollback 還會自動開 revert PR 並 dispatch Deploy Doctor，也就是順序做錯一次，會對一個好的合併自動開 revert PR。 | 在該段補兩句：secret 與遷移的順序做錯時，rollback 會自動開 revert PR，須人工關閉；rollback 的 render-env 同樣需要這個 secret，secret 缺失時 rollback 會一併失敗，但舊 stack 因為 up 之前就停下而未被動到。不需改程式。 | New |
| R-14 | Minor | deploy/initdb/02-memory-role-password.sh 檔頭「local development -- see LOCAL-DEV.md H6」；LOCAL-DEV.md > H7 | 腳本檔頭指向 LOCAL-DEV.md H6，但本機啟用步驟實際寫在 H7（H6 是 U5／U18 表不會自動建立的說明）。另外腳本與 H7 的本機步驟都以 psql 的 getenv 讀密碼，需要用戶端 psql 15 以上；CI 的 ubuntu-latest 與 pg18 容器內沒問題，但本機用較舊的 psql 時會得到不易理解的 meta-command 錯誤，H7 沒有提醒。 | 把檔頭的 H6 改為 H7；在 H7 的步驟 2 前加一句「需要 psql 15 以上，否則請在 db 容器內執行」。 | New |
| R-15 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/unit-test-instructions.md > 第三節「現況註記（2026-10-31）」 | 註記仍寫「A1–A11」與「A2–A9 的六支新測試檔」，並把 A12 範圍列為六支。實際本輪新測試是十二支，包含 test_meta_schema_expectations、test_memory_reference_counts、test_memory_db_role、test_memory_query_truncation，另有 verify_memory_role.sql 與 CI 新步驟。照這份註記重驗的人會漏跑四支新檔。 | 把註記的範圍更新為 A1–A13，並列出全部新測試檔；或加一句「完整清單以 code-summary 末節為準」。 | New |
| R-16 | Minor | DEPLOY.md > §2.2.8 與 deploy/initdb/02-memory-role-password.sh | 密碼經 ALTER ROLE ... PASSWORD 以字面值送進伺服器。若資料庫端將 log_statement 設為 ddl 或 all，明文密碼會落入 PostgreSQL 日誌；文件只談了命令列與 argv，沒談伺服器端語句日誌。目前 staging 預設為 none，所以不是現況缺陷，但屬於會被未來設定悄悄打破的前提。 | 在 §2.2.8 補一句：db 服務不得啟用 log_statement 為 ddl 或 all，否則 ALTER ROLE 的密碼會進日誌。 | New |

> R-10 Not re-checked this round

> R-11 Not re-checked this round

> R-12 Not re-checked this round

> R-13 Not re-checked this round

> R-14 Not re-checked this round

> R-15 Not re-checked this round

> R-16 Not re-checked this round
