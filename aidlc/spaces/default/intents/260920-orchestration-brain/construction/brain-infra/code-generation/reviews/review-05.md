## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

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
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-summary.md > 「逐步查驗摘要（43 個勾選：勾回 42、未勾 1）」（:230）與其表內 Step 11 的「2／3」（:244） | 舊段落標題與表格仍以現在式寫「勾回 42、未勾 1」，段內沒有任何指向後文的標記。與計畫現況 55 全勾相矛盾，只有讀到 :307 的補勾與 :373 的「以本節為準」才解開。只讀到 :230 的人仍會得到互相矛盾的印象。 | 在 :230 標題下加一行：此為 2026-10-20 的歷史快照，未勾的 Step 11 第三格已於 :305 補勾，現況以 :371 起的本輪重驗為準。不需改任何數字。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/code-generation/code-generation-plan.md > Step 6 第四格（:202-204），以及 code-summary.md > 後續變更第 1 點（:295） | 第四格仍是 [x]，其正文字面寫 --maxmemory-policy allkeys-lru，而 deploy compose :273-289 實為 noeviction。註記已聲明勾選只代表旗標存在，因此不算新的虛假勾選，但格內條件文字本身仍為假。另外 :295 還說 traceability.json 的 AC2.1.4 註記仍寫 allkeys-lru、本輪不改寫，但該列 note 已追加截至 HEAD 的更正，此句與現況不符；計畫第一節故事追溯表（:31）也仍以 allkeys-lru 描述 AC2.1.4 的落點，沒有就地註記。 | 把 :295 改為「AC2.1.4 note 已附截至 HEAD 更正，第一節追溯表（:31）仍為交付當時敘述」。計畫的 :31 與第四格文字屬核可內容，不必為此重開核可；在 code-summary 交接處記明即可，下一個讀計畫的人才不會把 allkeys-lru 當現況。 | New |

> R-03 Reviewer note: unit-test-instructions.md 現況已核對：:43 與 :58 兩處命令為 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B；:46 說明直譯器與快取；:66 規劃 6 個實作 7 個；:80 規劃 5 個實作 9 個；:99 合計 16。grep -c 'def test_' 實得 vector 7、render-env 9，與檔內數字一致。backend/.venv/bin/python 存在。

> R-06 Reviewer note: 計畫 R-03 格現附更正註記並說明上一輪勾選與事實不符；該格所述三項（兩處命令、說明段、實作數）與說明檔現況逐項相符，勾選不再為假。

> R-07 Reviewer note: code-summary.md :351 已改寫：說明檔現已直接修正，並寫明上一輪不改的理由是核可綁定計畫、測試說明與 Testing Contract 三者，traceability.json 與 code-summary.md 不在綁定範圍、勾選不計入，與同輪能改計畫勾選和 traceability.json 不矛盾。

> R-08 Reviewer note: traceability.json :255 的 I2 note 末尾已追加截至 HEAD c6a40f9 實查標註（deploy 7 個服務、記憶體上限共 11 項）。我實查兩份 compose：deploy 有 7 個 memory 上限與 7 個服務，test 有 4 個，數字成立。「六個 deploy」「十個服務」只剩在 S-8 與 I2，兩列都帶現況標註並聲明上文為交付當時敘述。

> R-09 Reviewer note: code-summary.md :373 明載重開會重設勾選、勾選結果以該節為準；實查計畫 grep -c '^- [x]' 為 55、'^- [ ]' 為 0，與該節宣稱的 55 與 0 一致，組成 2+5+5+43=55 也算得對。舊段落是否標明已過時另見新發現。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| grep -c '^- \[x\]' 與 '^- \[ \]' 於 code-generation-plan.md | 55 與 0 | 與 code-summary.md :373 宣稱一致 |
| grep -n 'maxmemory\|appendonly\|allkeys\|noeviction' deploy/docker-compose.deploy.yml | :256 --appendonly、:258 --maxmemory、:273 --maxmemory-policy、:289 noeviction；allkeys 只出現在註解 | Step 6 第四格的旗標存在成立，allkeys-lru 不成立，註記如實 |
| grep -c 'def test_' 兩支測試檔 | vector 7、render-env 9 | 與 unit-test-instructions.md 第四、五節一致 |
| 以 shasum -a 256 逐檔比對 reviewed-source-47672a01e28d.tsv 的 13 個檔與現況 | 13 個全部相同 | 「共用檔重新驗證」格所稱對最新收據無差異屬實 |
| 兩份 compose 服務與 memory 上限計數 | deploy 7 服務 7 上限；test 4 服務（db、backend、redis、frontend）4 個 memory 上限 | traceability.json I2、S-8 的現況標註（7 加 4 共 11 項）成立 |
| 於 scratchpad 副本跑兩支單元測試 | 未執行：委派審查的 Bash 受護欄限制，不能執行動態命令 | 測試結果沿用 code-summary 的 Ran 16 tests OK 宣稱，本輪僅以靜態計數與雜湊核對，未獨立重跑 |

### Summary

本輪四項文件修正全部屬實：說明檔命令與測試數與現況一致，計畫 55 格勾選無新的虛假條件，I2 note 已補現況標註，共用檔對最新收據逐位元相同。僅剩兩項 Minor：code-summary 舊的「勾回 42、未勾 1」段落缺少歷史快照標記，以及 allkeys-lru 的過期敘述在 :295 與計畫 :31 尚有殘留。無 Critical 或 Major，判定 READY。
