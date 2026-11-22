## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四個勾選（`redis` 的 `command:` ... `--maxmemory-policy allkeys-lru`） | 這一格已勾回，但格子本文逐字要求的 `allkeys-lru` 在 repo 現況不成立：`deploy/docker-compose.deploy.yml` 的 redis `command:` 現為 `noeviction`（約 :258-276，註解引 NFR4.50／`[N3]=A`，由後續提交 `c2e5687a` 改入）。code-summary 承認「policy 值已被後續決定改變」，卻仍照原樣勾回，等於勾選了一個字面上為假的條件。複查者若只看勾選狀態，會以為 `allkeys-lru` 仍被驗過。 | 在該格就地標註「依 NFR4.50／`[N3]=A` 由 `noeviction` 取代，後續單元決定」，或把判準改為「`command:` 含 `--appendonly yes`、`--maxmemory`、且 policy 旗標存在」。不要在判準與現況字面不符的情況下直接勾選。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > AC2.1.4 的 note（約 :63）、S-8／S-9 的 note（約 :219、:255） | 三處敘述已過期且會誤導下游：AC2.1.4 仍寫 `--maxmemory-policy allkeys-lru`（現為 `noeviction`，改變了「滿了之後」的行為：寫入被拒而非淘汰）；S-8 寫「十個服務項（deploy 六＋test 四）全部設記憶體上限」、S-9 寫「六個 deploy 服務」，但 deploy compose 已有第七個服務 `mcp-bridge`（512m，`networks: [mcp]`），現為十一項、七個服務。本輪已知這些過期卻不改，下游單元（session-store 判斷第 18 項容量時）會讀到錯的政策。 | 在這三列 note 末尾追加「截至 HEAD `fa51564`：policy 為 `noeviction`；deploy 為 7 個服務、記憶體上限共 11 項（含 mcp-bridge）」，或把這些敘述標為「交付當時」並指向 code-summary 末節；不要讓 `allkeys-lru` 在可機讀檔裡被當作現況。 | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/unit-test-instructions.md > 第三節本單元專屬命令（約 :43、:56）與 `test_vector_extension_bootstrap.py（6 個）`（:64） | 命令用 `python -m unittest`，但 code-summary 實查本機 PATH 沒有 `python` 只有 `python3`；全套測試在系統 Python 會因 `mcp` 為 1.29.0（釘選 2.3.0）出現 28 個失敗，唯有 `backend/.venv/bin/python` 全綠（1204 tests OK）。此外測試數寫「6 個」而檔內實為 7 個 `def test_`。照這份說明跑的人會得到紅燈或空命令，且無法判斷是本單元壞了。 | 在說明中補 `backend/.venv/bin/python` 與 `PYTHONDONTWRITEBYTECODE=1`，並把測試數更正為 7。若此檔被核可指紋綁定而不能改，至少在 code-summary 與下一單元的交接處明列此為已知替代命令。 | Unresolved |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 「19 項合併前必修與本單元的關係」 | 「劃給 brain-infra 的為 0 項」就清單標示的單元欄成立，但有四項的實際修法會落在本單元的 13 個檔上：#15（部署步驟須把成員回填排在對外開放之前，落點是 `deploy.yml`／`DEPLOY.md`，目前 `deploy.yml` 無任何回填步驟，僅 `DEPLOY.md` §2.2.10 文字要求）、#16（鎖逾時與連線池，落點是 `backend/database.py` 的 engine 設定）、#18（Redis 容量，落點是 deploy compose 的 `command:`）、#19（`OPENROUTER_API_KEY` secret，`deploy.yml` :83 已有 required-secret 檢查，這一項實際已有守門）。本單元的審查收據與勾選因此會被他單元的修改再次改寫，卻沒有任何紀錄指明這些檔案的修改權屬。 | 在 code-summary 該節補一張「跨單元落點」表，列 #15／#16／#18／#19 各自會改到本單元哪個檔，並寫明由哪個單元負責、改完是否需要回頭重驗本單元對應勾選；#19 註明守門已存在於 `deploy.yml` :83。 | Resolved (reviewer) |
| R-05 | Minor | deploy/docker-compose.deploy.yml > `mcp-bridge` 服務與 `mcp` 網段；aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 後續變更第 3 點 | ADR-0006 四面向逐項核對後本單元判準未失效：IAM（redis `default` 仍只有 `+@connection`，app 使用者仍 `-@admin -@dangerous`，兩個身分在 `deploy.yml` 有探測）、network exposure（`mcp-bridge` 僅在 `internal: true` 的 `mcp` 網段、無 `ports:`，`cloudflared` 仍只在 `edge`）、audit logging 無變動。唯一待補的是 encryption：使用者 JWT 在 `mcp` 網段以明文往返（merge-blockers #7，仍待人裁決），而 code-summary 只在「語意變動」中提到服務與網段新增，沒有把它連到本單元「網路分段」這項控制的前提，讀者會誤以為分段已涵蓋該風險。 | 在 code-summary 後續變更第 3 點補一句「`mcp` 網段的明文往返屬 #7，本單元的網路分段不處理 encryption」，避免被當成已由本單元覆蓋。 | Resolved (reviewer) |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > 「重新驗證審查（review-03）的五項文件修正」一節 R-03 勾選 | 該格已打勾 [x]，內文寫「unit-test-instructions.md 本單元命令改為 PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B …，測試數更正為實數」，但 git 顯示該檔沒有任何變動，內容仍是舊命令與 6、5 個。code-summary 才承認未改。計畫勾選了一個字面上為假的條件，與前輪 R-01 同形；只讀計畫的複查者會以為說明檔已修好。 | 把該格改成如實描述：標明不改該檔的原因，並註明替代命令與實數記在 code-summary 末節；或取消打勾。計畫與 code-summary 對 R-03 的說法必須一致。 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > R-03 處置說明（「不改該檔」的理由） | 不改說明檔的理由是它與計畫綁在同一份核可、改了會使核可失效；但同一輪已為 R-01 修改了計畫本身，且 traceability.json 也改了。理由前後不一，無法說服人替代做法是唯一可行路徑。 | 補一句說明為何計畫與可機讀檔可改而說明檔不可改（例如指紋或收據綁定的具體差異），或改採就地加一行指向 code-summary 的標註。 | New |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/traceability.json > I2 的 note（約 :255） | 寫「六個 deploy 服務 ＋ 四個 CI test 服務」，與同檔已更正的 S-8、S-9 不一致；deploy 現為 7 個服務。本輪只補了三列，同一事實的另一種表達形式漏掉。 | 在 I2 note 末尾追加與 S-8 相同的「截至 HEAD」標註。 | New |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四格註記與 code-summary「逐步查驗摘要（43 個勾選：勾回 42、未勾 1）」 | 計畫檔現況有 45 個未勾、5 個已勾（僅新增一節的五格），HEAD 版為 43 個已勾；Step 6 註記說「本格的勾選只代表…」，但該格目前沒有勾，code-summary 又宣稱勾回 42。兩者讀起來互相矛盾。 | 在 code-summary 註明計畫勾選狀態會被引擎於重開時重設，勾選結果以逐步查驗摘要為準，或讓計畫勾選與摘要一致。 | New |

> R-01 Reviewer note: 計畫 Step 6 第四格已就地標註 noeviction 取代 allkeys-lru，並寫明勾選不代表 allkeys-lru 成立；deploy compose 現況 :258 --maxmemory、:273 --maxmemory-policy 與標註的 :273-274 相符。

> R-02 Reviewer note: traceability.json 的 AC2.1.4、S-8、S-9 三列 note 已追加截至 HEAD c6a40f9 的現況；實數核對無誤：deploy 7 個服務、記憶體上限 7 項（:77、:182、:323、:364、:386、:411、:454），test 4 服務 4 項，合計 11；JSON 仍可解析。

> R-03 Reviewer note: 刻意偏離：未改 unit-test-instructions.md。該檔現況仍寫 python -m unittest（:43、:56）、test_vector_extension_bootstrap 為 6 個（:64）、test_render_env_redis 為 5 個（:78）；實數為 7 與 9。替代命令與實數只寫在 code-summary 檔尾，讀說明檔的人不會看到；此外計畫自稱該檔已改（見新發現），替代做法不足以讓誤導消失。

> R-04 Reviewer note: code-summary 已補「跨單元落點」表；逐格實查成立：backend/main.py :24 與 :98 呼叫 ensure_project_members_on_startup，DEPLOY.md :951 為 2.2.10，backend/database.py 僅 :37 create_engine 無 pool_size 與 lock_timeout，deploy.yml :80、:85、:92、:100、:695 與表列一致。

> R-05 Reviewer note: code-summary 後續變更第 3 點末句已寫明 mcp 網段明文往返屬合併前必修 #7，本單元網路分段不處理 encryption。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| grep -c 'def test_' 兩支測試檔 | test_vector_extension_bootstrap.py 7、test_render_env_redis.py 9 | 與 code-summary 實數一致，說明檔的 6 與 5 確實過期。 |
| git diff --stat unit-test-instructions.md | 無輸出（未變動） | 證實計畫 R-03 勾選的敘述為假。 |
| 讀 deploy/docker-compose.deploy.yml、docker-compose.test.yml | deploy 7 服務 7 項 memory；test 4 服務 4 項 | 11 項、7 個服務成立。 |
| grep OPENROUTER_API_KEY .github/workflows/deploy.yml | :85、:92、:100、:123、:695 | 跨單元落點表 #19 行號正確。 |
| json.load traceability.json | 可解析 | 編輯未破壞 JSON。 |
| 測試未重跑 | 依指示不在工作樹寫檔 | 本輪僅文件修正，測試數以 grep 核對。 |

### Summary

R-01、R-02、R-04、R-05 已如實修正且數字核對無誤；R-03 的替代做法不足，說明檔仍留著錯的命令與測試數，更糟的是計畫把 R-03 勾成已改檔，與事實相反，這是新的 Major，需在計畫就地更正後才能 READY。
