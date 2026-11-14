## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 3

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-46 | Major | security-requirements.md `NFR4.1(c)` 範圍表第一列（`:95`）、`§五`（`:756–757`） | 已落地，且做得比指定的修法完整。`:95` 的 test 欄現逐字為「**必須有，但不會是同一份檔**」，並新增整段理由：「**為何不能是同一份檔**（本輪更正）：Redis 的 ACL 把密碼綁在 user 那一行（`user <name> on >pass ~... +@...`），而 `redis.conf`／`aclfile` **不內插環境變數**；兩個 stack 的 `REDIS_PASSWORD` 值不同來源（見本表第三列），共用一份檔只有兩種收法——把 deploy 的憑證改成 repo 內的字面值（**等於把部署憑證放進 public repo**，牴觸 `NFR4.1(a)` 與 `project.md ## Forbidden`），或讓 test 用 deploy 的真憑證。**兩者都不可接受**。故採掛載檔時**各自一份**，或採 compose 的 `command:` 覆寫由 compose 逐 stack 內插」。指定要額外檢查的 `§五` 矛盾也消失：`:756–757` 仍把「`command:` 覆寫還是掛載設定檔」留給 `U10`，而新措辭兩條路都寫了、不再預設掛載那一種 | 無（`:80` 承載者欄的殘留另立 R-50） | Resolved |
| R-47 | Minor | tech-stack-decisions.md `§四` row 5（`:147`） | 已落地。該格現逐字為「步驟 4 的**兩條硬條件**與採用哪一種做法（含兩者代價不對稱的說明）」，與 `security-requirements.md` `NFR8.5` row 3（`:601`）逐字對齊。同格「**八項**」與第 8 項的括號說明保留 | 無 | Resolved |
| R-48 | Minor | traceability.json `NFR4.1(c)`（`:113`）、`NFR6.3(b)`（`:118`） | 兩處都已落地。`:113` 的 target 現逐字含「——**兩份 compose 都必須有**，但不會是同一份檔（Redis 設定檔不內插環境變數，而兩 stack 的 REDIS_PASSWORD 來源不同）」，單數措辭已消除。`:118` 的第二條不變量現逐字為「窗口內自動 rollback 不可用＋窗口後必須以另一個 PR 復原 rollback job 並確認復原後首次部署有武裝」，與 `security-requirements.md` `§〇` `S-4`（`:34`）的「**＋ 窗口後的復原步驟**」對齊。`python3 -c "import json;json.load(...)"` 回 `JSON OK`，檔案仍可解析 | 無 | Resolved |
| R-49 | Minor | tech-stack-decisions.md `§四` 表下方敘述（`:156`） | 已落地。該括號現逐字為「（**初版誤以為**那是唯一有 CI 閘門的一項；實際三項皆有，見 row 3 與 `security-requirements.md` `§四`）」——指標不再指向自己被更正的說法，且多補了正確版本的落點。與 row 3（`:145`）的「**初版在此寫「唯一有閘門的一項」是錯的**……見下方更正」互為閉環 | 無 | Resolved |
| R-50 | Minor | security-requirements.md `NFR4.1(c)` 承載者表第二列（`:80`）；連帶 `§〇` `S-5`（`:35`）與 traceability.json `:113` 的 `S-5` 敘述 | **R-46 的修法未完全傳播到同一節上方的承載者欄。** `:80` 逐字仍是「**一份掛載的 Redis 設定資產**（`redis.conf`／`users.acl`），或 compose 的 `command:` 覆寫，**且必須掛進兩份 compose**（`deploy` 與 `test`）」——「一份……掛進兩份 compose」正是 R-46 判定為做不到的那個指令原樣留著，只是這一輪在它下方 15 行處補了更正。`S-5`（`:35`）的「`REDIS_USER` ＋ **一份掛載的 Redis 設定**」同形。緩解因素有兩層且都成立：`:80` 該格結尾逐字寫「——見下方範圍說明」，指標在場且指向正確的那一格；`tech-stack-decisions.md` `§四` row 9（`:151`）與 `traceability.json:113` 都沒有用「一份」這個數量詞。故跟著指標走的人拿得到對的資訊，只有單讀 `:80` 那一格的人會撞上舊措辭 | `:80` 的「**一份掛載的 Redis 設定資產**」改為「**Redis 設定資產**（採掛載檔時兩份 compose 各一份）」；`S-5`（`:35`）的「一份掛載的 Redis 設定」同步去掉「一份」 | New |

### Summary

**四項指定修法全部落地，且無一只做半套；本輪撞見一項殘留（R-50），屬本輪編輯傳播不完整。**

**1. 四項的落地判定（逐字引用改後內容）。** R-46：`security-requirements.md:95` 的 test 欄由「必須掛同一份」改為「**必須有，但不會是同一份檔**」，並補上完整理由段（ACL 把密碼綁在 user 行、`redis.conf`／`aclfile` 不內插環境變數、兩 stack 的 `REDIS_PASSWORD` 不同來源、兩種收法各自為何不可接受、兩條可行路徑）。指定額外檢查的 `§五`（`:756–757`）逐字仍為「**Redis 設定資產採 compose `command:` 覆寫還是掛載設定檔**：由 `U10` 決定」——新措辭把兩條路都寫進去，不再預設掛載，矛盾消失。R-47：`tech-stack-decisions.md:147` 逐字「步驟 4 的**兩條硬條件**與採用哪一種做法（含兩者代價不對稱的說明）」，與 `NFR8.5` row 3（`:601`）逐字一致。R-48：`traceability.json:113` 補「**兩份 compose 都必須有**，但不會是同一份檔（Redis 設定檔不內插環境變數，而兩 stack 的 REDIS_PASSWORD 來源不同）」；`:118` 補「窗口後必須以另一個 PR 復原 rollback job 並確認復原後首次部署有武裝」，與 `§〇` `S-4`（`:34`）的「**＋ 窗口後的復原步驟**」對齊；`json.load` 通過。R-49：`tech-stack-decisions.md:156` 逐字「（**初版誤以為**那是唯一有 CI 閘門的一項；實際三項皆有，見 row 3 與 `security-requirements.md` `§四`）」。

**2. 三支 sensor 的實際輸出（我自己重跑）。** `required-sections` 對 `security-requirements.md`：`{"pass":true,"h2_count":9,"findings_count":0}`（九個 H2 依序為「這份檔在做什麼／〇、本階段新增…／一、ADR-0006…／二、安全需求／三、上游 NFR…／四、機械閘門…／五、本站刻意不決定的事／六、必須隨本單元一起帶走…／Assumptions & Open Questions」）；對 `tech-stack-decisions.md`：`{"pass":true,"h2_count":6,"findings_count":0}`。`traceability`：`{"pass":true,"gaps":[],"orphans":[],"missing_from_table":[],"missing_from_upstream_ids":[],"invalid_entries":[],"invalid_targets":[],"findings_count":0}`——六個陣列全空。`upstream-coverage`：`{"pass":true,"consumes":[],"unreferenced":[],"scanned_files":[],"reason":"no upstream","findings_count":0}`——**誠實記載：它回的是 `reason:"no upstream"`，即本 stage 的 `consumes:` 為空，這支 sensor 本輪沒有驗證任何東西，`pass:true` 不代表上游覆蓋已被檢查過。**

**3. 重數的每一個計數。** `NFR8.5` 表以程式實數為 **8 列**（`:592` 標題後至 `:606`，表格 10 行扣表頭與分隔），`tech-stack-decisions.md:147` 寫「八項」——一致。無閘門清單實數 **9 列**（`NFR8.7`／`8.8`、`NFR4.2`、`NFR6.3`、`NFR6.1`、`NFR8.9`、`NFR4.1(c)`、`NFR8.1a`、`NFR8.1b`、`rollback` job 存廢），標題 `:713`「沒有閘門的九項」與結語 `:727`「這九項」同步。`§四` 同步點表實數 **9 列**（rows 1–9），標題 `:139`「九處部署資產同步」、`:172`「九處同步而非三處」、`security-requirements.md:9`／`:35`／`:84` 三處「九處」、`traceability.json:113`「六處→九處」——六個落點全部一致。`NFR6.1` 落點實數 **5 列**，文中「落點 1–4 的 image 值必須相同」「四處 image 一致」「落點 5 是 volume 宣告」三處互不衝突。`§六` 的 **14** 我以 `inception/units-generation/unit-of-work-dependency.md` 的 `kind:` 實算：17 個 `kind:` 中 `packaging` 為 3 個（`U1`／`U9`／`U17`），17−3＝14——成立。另 `grep` 舊計數「七項／八處／六處（作為同步點總數）」在三份產出中無殘留（僅存的「六處」皆為「六處→九處」的歷史對照，屬正確用法）。

**4. 雙向差集與行號越界。** `NFR{n}.{m}` 定義集合為 19 個 H3（`NFR4.1`／`4.2`／`4.3`／`6.1`／`6.2`／`6.2a`／`6.3`／`7.1`／`8.1`／`8.1a`／`8.1b`／`8.2`／`8.3`／`8.4`／`8.5`／`8.6`／`8.7`／`8.8`／`8.9`／`9.1`），引用集合另含 7 個子條款標籤（`NFR4.1(a)(b)(c)`、`NFR6.3(a)(b)(c)`、`NFR6.2a`）——逐一開檔確認全部有錨點：`NFR6.3(a)(b)(c)` 為 `:281`／`:297`／`:367` 三個 H4，`NFR6.2a` 為 `:247` 的 H4，`NFR4.1(a)(b)(c)` 為 `:61`／`:64`／`:73` 的粗體子段。**引用減定義＝空、定義減引用＝空**（每個定義的全文命中數皆 ≥2，無孤兒）。`<檔名>:<行號>` 引用：以正規式抽出兩份 md 中 **57 處可解析為 repo 實檔**的引用（含 `:a–b` 區間），逐一對照該檔實際行數，**越界 0 處**。

**5. 三類切分。** **(a) 由本輪編輯引入或傳播不完整 — 1 項**：R-50（`:80` 的「一份」未隨 `:95` 同步）。**(b) 既存漏審 — 0 項。** **(c) 真正的新設計問題 — 0 項**（第七次為 0）。**這輪不該再跑一輪。** 四項指定修法命中率 4／4，且 R-46 做得比指定的更完整；唯一的新發現是同一節上方 15 行的一個數量詞，它有明示指標指向正確版本、且兄弟檔與 `traceability.json` 都沒有沿用該措辭，所以它不會讓任何讀完整節的人做錯事。按 `project.md` 的停止判準，這已經是「定點編輯比審查更有效」的形狀：把 R-50 的兩處數量詞併進動筆寫 `DEPLOY.md` 的那一次即可，不需要第八輪。
