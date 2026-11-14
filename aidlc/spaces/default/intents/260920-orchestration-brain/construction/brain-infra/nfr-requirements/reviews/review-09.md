## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-26T16:48:41Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-50 | Minor | `security-requirements.md` `§〇` `S-5`（`:35`，名稱欄＋理由欄）與 `NFR4.1(c)` 承載者表第二列（`:80`） | 三處量詞全部落地，且修法比指定的更明確地保住了 `U10` 的兩條路。`:35` 名稱欄現逐字為「`REDIS_USER` ＋ **每個 stack 各自的** Redis 設定承載者」；同列理由欄現逐字為「沒記它**需要多一個設定資產承載者與多一個變數**」；`:80` 承載者欄現逐字為「**掛載的 Redis 設定資產**（`redis.conf`／`users.acl`，**兩份 compose 各自一份**），或 compose 的 `command:` 覆寫（由 compose 逐 stack 內插）——**兩份 compose 都必須有**，見下方範圍說明」。原問題（「一份……掛進兩份 compose」與同檔 `:95` 的論證對撞）已消除：全檔 `grep 一份` 只剩 `:80`／`:95` 兩處，兩處皆為「各自一份」「不會是同一份檔」，方向與 `:95` 一致；`:114`（`render-env.sh` 是一份 heredoc）與 `:669`（同一份主機）與本議題無關 | 無 | Resolved |
| R-51 | Major | `security-requirements.md` `§六`（`:764`–`:781`），特別是 `:769` 的狀態標記與 `:771` 的 `aidlc-state.md:87` 引用 | **本輪的路由修復沒有傳播到 `§六`——而 `§六` 的全文就是在轉交那個已被修掉的缺口。** `§六` 標題逐字仍為「**`functional-design` 已被整站標為跳過（`[S]`），但它對其餘 14 個單元是適用的**」，並以「狀態標記在 `aidlc-state.md:87`（`- [S] functional-design — EXECUTE`）」作為兩個來源之一。實查：`aidlc-state.md:87` 現在逐字是 `### CONSTRUCTION PHASE`，該 checkbox 已移到 `:89` 且逐字為 `- [-] functional-design — EXECUTE`（`[-]` 而非 `[S]`），同檔 `:31` 為 `**In Progress**: functional-design`、`:109` 為 `**Current Stage**: functional-design`。亦即：`§六` 的狀態主張、括號內的逐字引用、以及行號三者同時失效，而同檔問題檔的 `## Revision 2` 已完整記載這次修復。`§六` 還逐字要求「**必須在走到 `U2 brain-ws-contract` 之前處理**」——那件事此刻正在進行中。下游若單讀 `§六` 會去重新診斷一個已在處理中的缺口，且照 `:87` 這個行號開檔會看到一行標題而非它所宣稱的 checkbox。緩解因素：方向保守（它警告的缺口正在被關閉，不會誘使下游少做事），且 `§六` 另一個來源（audit shard `:18550` 的 `Skipped by jump to nfr-requirements (forward)`）作為歷史記錄仍為真 | 把 `§六` 改寫為「該 `[S]` 已由 `jump execute --target functional-design --direction backward` 修復，現為 `[-]`（`aidlc-state.md:89`）」的**歷史記載＋現況**兩段形式，或在該節開頭加一句就地更正並把行號改為 `:89`；不得讓一段已失效的狀態主張帶著失效的逐字引用交給下游 | New |

### Summary

**1. R-50 三處的落地判定與獨立判斷。** 三處逐字內容如上表（`:35` 兩欄、`:80` 一欄），與 `## Revision 2` 的修法表逐字一致。我獨立判斷修法**真的解決了原問題**，依據三項：(a) 全檔 `grep 一份` 現存四處，與本議題相關的只有 `:80`（「兩份 compose 各自一份」）與 `:95`（「不會是同一份檔」「故採掛載檔時**各自一份**」），方向一致、無自我矛盾；沒有任何一處讀起來像「共用一份設定檔」。(b) **沒有把任何一種做法寫死**：`:80` 新措辭保留「掛載設定資產」與「compose `command:` 覆寫」兩條並列，故 `§五`（`:756`–`:757`）「**Redis 設定資產採 compose `command:` 覆寫還是掛載設定檔**：由 `U10` 決定」仍然成立；若當初只寫「兩份 compose 各一份掛載檔」才會把掛載那條寫死，改法避開了這個陷阱。(c) 兩個交叉引用仍與新措辭一致：`traceability.json:113` 逐字「——**兩份 compose 都必須有**，但不會是同一份檔（Redis 設定檔不內插環境變數，而兩 stack 的 REDIS_PASSWORD 來源不同）」，`tech-stack-decisions.md` `§四` row 9（`:151`）逐字「**兩份 compose 都要掛**（`deploy` 與 `test`）」——兩者本來就沒有用「一份」這個量詞，故不需改動，也沒有被改動。

**2. 「除 R-50 外無其他改動」的證據。** 方法與結果：(i) `git status --porcelain` 對該目錄回報三份產出皆為 `A`（已進 index、未 commit），其中 `security-requirements.md` 與 `nfr-requirements-questions.md` 為 `AM`，`tech-stack-decisions.md` 與 `traceability.json` 為 `A `（工作樹與 index 相同）；`git diff --stat` 只列兩個檔（questions +27／-1、security-requirements +2／-2）。(ii) `git diff -- security-requirements.md` 全文為**兩個 hunk、各一行**，正好是 `:35`（名稱欄＋理由欄同一行）與 `:80`——R-50 的三個落點落在兩行上，故「三處」與「兩行」不矛盾。(iii) `tech-stack-decisions.md`／`traceability.json` 的 mtime 為 `00:41:26`／`00:41:35`，晚於 review-08 的 `00:01:23`，但 `git diff` 為空 → 是內容位元相同的重存（`project.md` 記載的 summary-authorization 蓋戳記模式），非內容變更。(iv) 我**不採信** index mtime 作為 `git add` 時點（`git status`／`git diff` 會刷新 stat cache，本 session 自己就刷過），改用**行號複驗**作為獨立證據：review-08 逐字引用的位置 `security-requirements.md:592`（`### \`NFR8.5\` — \`DEPLOY.md\` 同步`）、`:713`（`### 沒有閘門的九項`）、`:727`（`**這九項不是「缺工具」的抱怨…**`）、`tech-stack-decisions.md:147`（「**八項**…**兩條硬條件**…」）、`:156`（「**初版誤以為**那是唯一有 CI 閘門的一項」）**全部原位命中且逐字相同**——若在任一處上方增刪過行，這些行號必然位移。`traceability.json:113`／`:118` 的逐字片段亦仍在。結論：三份產出相對 review-08 已驗證的狀態，除 R-50 那兩行外逐字相同。

**3. 三支 sensor 的實際輸出（我自己重跑，`engine sensor fire` ＋ 直呼底層取 JSON）。**
- `required-sections`：`security-requirements.md` → `{"pass":true,"h2_count":9,"findings_count":0}`（九個 H2：這份檔在做什麼／〇、本階段新增…／一、ADR-0006…／二、安全需求／三、上游 NFR…／四、機械閘門…／五、本站刻意不決定的事／六、必須隨本單元一起帶走…／Assumptions & Open Questions）；`tech-stack-decisions.md` → `{"pass":true,"h2_count":6,"findings_count":0}`。與 review-08 完全相同。
- `traceability`：`traceability.json` → `{"pass":true,"gaps":[],"orphans":[],"missing_from_table":[],"missing_from_upstream_ids":[],"invalid_entries":[],"invalid_targets":[],"findings_count":0}`——六個陣列全空。該 sensor 的 filter 為 `**/traceability.json`，對兩份 md 直接拒收（`does not match sensor filter`），故它只驗那一個檔。
- `upstream-coverage`：`{"pass":true,"consumes":[],"unreferenced":[],"scanned_files":[],"reason":"no upstream","findings_count":0}`——**與 review-08 逐字相同，它這一輪同樣什麼都沒驗**。誠實記載其成因：stage 檔 `consumes:` 實際宣告了五項（`functional-spec` required、`rules` required、`requirements` required、`contract-summary`、`technology-stack`），但引擎交給 sensor 的 `consumes` 為空陣列、`scanned_files` 亦為空，故 `pass:true` 只代表「沒有可比對的上游」，不代表上游覆蓋被檢查過。附帶事實（不列為發現，屬路由而非產出）：`functional-spec` 的 `required: true` 正是本輪回跳要修的那條，而 `functional-design` 目前為 `[-]`、尚未完成。
- 額外跑到的 `claim-sources` 回 `failed`（detail: `questions file is missing ## Sources` ＋ 大量 `claim block has no source tag`）。**不列為發現**：`nfr-requirements` 的 stage 檔 `sensors:` 只宣告 `required-sections`／`upstream-coverage`／`linter`／`type-check`／`traceability`，`claim-sources` 不在其中，review-08 也未跑它；它是 ideation／inception 的 grounding contract 檢查，對本 stage 不適用。

**4. 重數的計數、雙向差集、行號越界。**
- `NFR8.5` 表：實數 **8 列**（rows 1–8，`:592` 標題之後）；`tech-stack-decisions.md:147` 寫「**八項**」並點名「第 8 項為窗口後復原 `rollback` job 的收尾步驟」——一致。
- 無閘門清單：實數 **9 列**（`NFR8.7`／`8.8` 併為一列、`NFR4.2`、`NFR6.3`、`NFR6.1`、`NFR8.9`、`NFR4.1(c)`、`NFR8.1a`、`NFR8.1b`、`rollback` job 存廢）；標題 `:713`「沒有閘門的九項」與結語 `:727`「這九項」一致。上方「真的有閘門的三項」實數 **3 列**，一致。
- `§四` 同步點表：`awk` 切出 `## 四` 至 `## 五` 區段後 `grep -c '^| [0-9]'` ＝ **9**；標題 `tech-stack-decisions.md:139`「九處部署資產同步」、`:172`「九處同步而非三處」、`security-requirements.md:9`／`:35`／`:84` 三處「九處」、`traceability.json:113`「六處→九處」——**六個落點全部一致**（`grep -n 九處` 共命中六處，無第七處）。
- `NFR6.1` 落點：實數 **5 列**；文中「落點 1–4 的 image 值必須相同」「第五個落點」「四處 image 一致」「五個落點（四處映像 ＋ volume 宣告改名）」（`traceability.json:46`）互不衝突。
- `§六` 的 **14**：`U2`–`U8`（7）＋ `U10`–`U16`（7）＝ 14；與 `## Revision 2` 的「17 個工作單元中的 14 個（三個 `packaging` 單元本來就 kind-vacuous）」自洽（17−3＝14）。
- `NFR{n}.{m}` **雙向差集**：以 `###`／`####` 標題取定義集合、對三份產出全文取引用集合。定義 20 項（`NFR4.1`/`4.2`/`4.3`、`6.1`/`6.2`/`6.2a`/`6.3`、`7.1`、`8.1`/`8.1a`/`8.1b`/`8.2`–`8.9`、`9.1`）。**引用−定義 ＝ ∅**（首輪掃描把 `NFR6.2a` 報為未定義，複查為我的正則只吃 `###` 而它是 `####` 標題，`:247` 逐字 `#### \`NFR6.2a\` — 本機建庫路徑的硬依賴`；已修正掃描）。**定義−引用 ＝ ∅**，無孤兒需求。
- **`<檔名>:<行號>` 越界檢查**：以正則抽出兩份 md 的全部外部檔案行引用，得 **50 個相異引用**，逐一解析目標檔並比對行數。初掃兩筆 `requirements.md:451` 報越界，原因是我的解析器用 `git ls-files` 撿到另一個 intent 的 `requirements.md`（182 行）；指向本 intent 的 `inception/requirements-analysis/requirements.md`（621 行）後在範圍內，且 `:451` 逐字以「另：Redis 連線憑證須最小權限」結尾，正是 `S-3`／`NFR4.1(b)` 所引的那一句。**修正後 50/50 全部在範圍內。** 唯一失效的行引用是 `§六` 的 `aidlc-state.md:87`（該檔有 118 行，未越界但內容已改），另立 R-51。
- `traceability.json`：`python3 -c "import json;json.load(...)"` 通過，頂層鍵為 `stage`／`unit`／`upstream_ids`／`coverage`／`reverse`。

**5. 三類切分與是否再跑一輪。** (a) **本輪編輯引入／傳播不完整：1 項**（R-51——`## Revision 2` 記下了路由修復，`§六` 沒有跟著改；這正是本 repo 反覆記載的「跨檔傳播同一個事實」失誤形狀，只是這次的「另一檔」是同一份檔的另一節）。(b) **既存漏審：0 項**。(c) **真正的新設計問題：0 項**。R-50 已 Resolved 且修法正確完整，未連帶破壞任何計數、交叉引用、差集或行號。**不該再跑一輪**：唯一的發現是單節措辭與行號的同步，屬機械性修正、不牽動任何需求或承載者判定，交由核可關卡上就地改掉即可；再派一輪審查的期望產出低於它的成本。
