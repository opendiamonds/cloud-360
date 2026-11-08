## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 2

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-10 | Still applies | Minor | code-summary.md 本輪無任何編輯。:230 標題仍寫「43 個勾選：勾回 42、未勾 1」，段內沒有歷史快照標記，與 :377 的「仍未勾的格：0」並存。 |
| R-11 | Still applies | Minor | :295 仍寫 traceability.json 的 AC2.1.4 註記「仍寫 allkeys-lru」；計畫 :31 的追溯表列也仍寫 allkeys-lru。deploy compose 實為 noeviction。兩處皆未動。 |
| R-12 | Still applies | Minor | traceability.json 的 ADR-0006 note 仍只談 Redis ACL 使用者、「PostgreSQL 單一 superuser 原樣承接」，全文無 cloud360_memory 與 MEMORY_DB_PASSWORD（逐字 grep 為空）。後續單元讓 memory_router 改走記憶專用連線（見新發現），使該 note 與現況的落差更大，嚴重度不變。 |
| R-13 | Still applies | Minor | DEPLOY.md「既有環境的順序」段（:637-644）仍只寫「失敗並觸發 rollback」，沒寫 rollback 的 render-env.sh 也缺 MEMORY_DB_PASSWORD、以及會自動開 revert PR。DEPLOY.md 本輪未再修改此段。 |
| R-14 | Still applies | Minor | deploy/initdb/02-memory-role-password.sh:15 仍指向 LOCAL-DEV.md H6（實為 H7）；LOCAL-DEV.md 全檔 grep 不到 psql 15 版本要求。 |
| R-15 | Still applies | Minor | unit-test-instructions.md:61 現況註記仍寫「A1–A11」與「A2–A9 的六支新測試檔」。 |
| R-16 | Still applies | Minor | DEPLOY.md 與 02-memory-role-password.sh 全文 grep 不到 log_statement，ALTER ROLE 密碼進伺服器語句日誌的前提仍未寫明。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | DEPLOY.md > 記憶專用資料庫角色小節「誠實的現況」（:627-628）與 backend 連線列（:624）；LOCAL-DEV.md > H7（:280-283） | 兩處文字已被他單元的後續改動推翻。DEPLOY.md 寫「記憶表的實際存取（memory_service.py）仍走主連線；改用 get_memory_session() 屬 memory-service 單元」，LOCAL-DEV.md 寫「不會退回主連線的帳號」「截至本節寫下時，記憶表的實際存取仍走主連線」。現況是 memory_router.py 的五個端點都改用 get_memory_db：邊界啟用時走 cloud360_memory；未設密碼且 APP_ENV 屬 local／test／ci 時會退回主連線並每程序記一次 WARNING；其他環境（含 staging）回 503。連帶後果是 staging 的記憶 HTTP 端點現在實際依賴 cloud360_memory 的密碼步驟，deploy.yml 在 up -d 之後才設密碼，兩者之間與密碼步驟失敗時，這五個端點會連線失敗；DEPLOY.md 沒有交代。brain_gateway、work_orchestrator 等同進程路徑仍走主連線，兩種狀態並存也未寫明。 | 更新 DEPLOY.md 該段：HTTP 五個端點已走記憶專用連線，同進程呼叫端仍走主連線；列出三種環境行為（啟用／本機退回／非本機 503）與 up -d 到設密碼之間的短暫失敗窗口。更新 LOCAL-DEV.md H7：本機未設密碼時會退回主連線（記一次 memory_db_local_fallback WARNING），而非「不退回」。連同 R-12 一併校正 traceability.json 的 ADR-0006 note。不需改程式。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對最新收據 reviewed-source-e0f4f731bd71.tsv 逐檔重算（欄位為 tab 起首，取第 2 欄路徑與第 4 欄雜湊） | 50 檔全部相同、0 變動、0 缺檔；manifest 列雜湊 9f0daee2… 與 source-manifest.json 現值一致 | 以最新收據為基準，工作樹與收據逐位元一致，沒有「收據後」的變動。brief 所稱的收據失效發生在更早的收據。 |
| 同法對上一份收據 reviewed-source-3a34f7543ebf.tsv 重算並與最新收據逐列比對 | 8 檔不同：verify_meta_schema.sql、test_meta_schema_expectations.py、memory_errors.py、memory_facade.py、memory_router.py、frontend/src/types/api.d.ts、frontend/tests/e2e/a11y.spec.ts、openapi.json；其餘 42 檔雜湊相同 | 這 8 檔就是審查要判定的「後續改動」集合。 |
| git diff／讀碼：verify_meta_schema.sql 與 test_meta_schema_expectations.py | 只新增 P17（system_requirement_fields 恰為 9 欄）與註解；P1–P16 原文未動；P5 仍為 9 欄（:106）；EXPECTED_TABLES 的 9 與 P17 一致；測試的正規式與 SQL 現文吻合；P17 已列入「全部通過」NOTICE | 來源是合併前必修第 30 列 (a)（project-meta-data）。未碰 brain-infra 修正，且與其回補的 cause 欄（9 欄）一致。 |
| git diff／讀碼：memory_errors.py、memory_facade.py、memory_router.py、openapi.json、api.d.ts | 來源是第 33 列（更名 MemoryServiceError、count_references_to_user、過期列不可放寬、query 截斷 4000、content 上限 4000）與第 48 列（get_memory_db、503）。後端全樹已無對 memory_errors.MemoryError 的匯入；user_router.py:475 仍呼叫 MemoryFacade(db).count_references_to_user；test_memory_reference_counts、test_memory_query_truncation、test_memory_input_limits、test_memory_db_session 與現行程式吻合；openapi.json 與 api.d.ts 各五處 503、content maxLength 4000，與路由宣告一致 | brain-infra 的 A4（刪除使用者稽核筆數）與 A1（記憶專用角色）的程式側仍成立，且 A1 被第 48 列接上執行路徑。只留下上方新發現的文件過期。 |
| 讀碼：a11y.spec.ts | 變動為第 26 掃描點（成員詳情頁 projectId 非數字）、@note 與 @story 註解、:77 註解改為「我的記憶 nav 現已有 aria-label」 | 來源是第 40、56、63 列。:77 的更正與 brain-infra A10 的 Sidebar.tsx:248 aria-label 事實吻合，未削弱修正。 |
| 讀碼：brain-infra 修正所在段落（收據 SAME 的檔） | A3：hierarchy_facade.py:98 的 HierarchyProjectAdminRequired、:342 與 :379 於擁有者檢查後判 project_admin；membership_service.can_administer_project（:430，:445-455）；membership_facade.project_admin_check（:570）；hierarchy_router.py:295 與 :326 注入。A7：DEPLOY.md:2340 已更正為 OPEN-GW13-6 與第 37 列 (c)。A10：Sidebar.tsx:248 aria-label=我的記憶、ContextBar.tsx:111 role=status、MemberDetailPage.tsx:292 aria-labelledby。requirements.txt:71／:78／:79 釘選 mcp、sse-starlette、mcp-types。deploy.yml:85／:93／:126／:161 帶入與檢查 MEMORY_DB_PASSWORD | 全部仍在且內容符合 code-summary 描述，無被後續單元破壞。 |
| 跨單元事實：tests_pg/test_membership_concurrency.py:431 的 C3 | 讀碼確認：該案把 bob 的成員列整列刪除，使 alice 成為專案唯一成員，再期望 assert_can_deactivate raise LastAdminGuard。membership_service.py:720-746 現在只在「除被停用者外仍有其他成員」的專案才擋；alice 獨自一人時回空清單，facade 不 raise，結果為 'passed' 而非 'guard' | 歸因正確：是第 21 列「獨自一人的專案不擋」使該案前提失效（第 57 列的記載）。與 brain-infra 的修正無關：membership_service.py 的該段是 brain-infra 自身以外的單元所改，且 C3 不碰 A1–A13 任何檔案的 brain-infra 專屬段落。 |
| code-summary 行號抽查（只記錄） | code-summary.md:500 寫 MemoryUserReferenceCounts 在 memory_facade.py:109、count_references_to_user 在 :519，現為 :114 與 :536。code-summary.md:501 引用 memory_errors.py:51 的 MemoryError，該行現為 class MemoryServiceError。其餘抽查項（DEPLOY.md:2340、Sidebar.tsx:248、ContextBar.tsx:111、membership_service.py:430）仍準確 | 漂移來自第 33 列的更名與新增；僅記錄，不要求改紀錄。 |
| 本輪未執行的項目 | 依限制未跑任何測試、python、npm、docker 或 gh，亦未連 DB／Redis | 判定全部以讀碼與 shasum 推演；真實 PostgreSQL 上以 cloud360_memory 執行向量相似度查詢仍無 CI 斷言（第 48 列 Minor (b) 已登記，非本輪新發現）。 |

### Summary

brain-infra 本輪沒有新改動，最新收據對 50 檔全部相同；相對上一份收據變動的 8 檔皆來自第 30、33、40、48、56、63 列，逐一讀碼後都沒有破壞 A1、A3、A4、A7、A10 等已落地修正。只剩一項 Minor 的文件過期：DEPLOY.md 與 LOCAL-DEV.md 仍寫記憶表存取走主連線，而第 48 列已讓 HTTP 五個端點走 cloud360_memory；R-10 至 R-16 七項 Minor 皆仍適用。0 Critical、0 Major，判定 READY。

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
