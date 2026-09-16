# Security Requirements — U-1 映射與解析 composite action

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-1-map-parse-action -->

## ADR-0006 security baseline 的四面向逐項判定

`CLAUDE.md` 第 3 章把 ADR-0006 列為 hard constraint，且 `project.md ## Mandated` 要求**對每一項變更**逐項判定四面向、不得以「已有 ADR-0006」帶過。判定為不適用者一律附理由，不留空白。

| 面向 | U-1 判定 | 理由 |
| --- | --- | --- |
| **IAM** | **不適用** | 本單元**不持有任何憑證**。它的 input 全部是文字與設定（`state_md`、`intents_json`、`record_path`、四項 Config），output 是**五個**字串（`Decision` 的四欄 ＋ `scope_note`；第五個於 functional-design 的 iteration 4 增設，見該單元 `business-logic-model.md` 的介面表。本處於 2026-08-30T05:10:02Z 由「四個」更正）。`requirements.md` NFR-S1 定義的權限（**ADR-0014 更正後為三項**：組織層 Projects 讀寫 ＋ repo 內容寫入 ＋ Issues 寫入）全部落在 U-3／U-4／U-5／workflow 層，不在此 |

> **權限集合現為四項（ADR-0015 §8），非三項**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數；更正指令與閘門（**Bolt 0，須在憑證鑄造前**）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。**此為 `open-items.md` 的 B:M-5，指名由 nfr-requirements 的閘門承接，於 2026-08-30T05:10:02Z 補上。**
| **Encryption** | **不適用** | 本單元不做任何網路呼叫、不落地任何檔案。NFR-S4 的「傳輸層由 GitHub API 的 HTTPS 承擔」對它無對應行為 |
| **Network exposure** | **不適用** | NFR-S5 已判定整個機制此面向不適用（不開埠、不新增端點）。本單元更是零 I/O，連出站呼叫都沒有 |
| **Audit logging** | **部分適用** | NFR-S6 要求每次 Status 變更可回答「哪個 intent、哪個 stage、什麼時間」。本單元**產生**其中兩項（`intent_id` 隱含於 `traceable_row`、stage 見 `field_value`），但**不負責記錄**——記錄落在 workflow 層與受管區塊 |

**「不持有憑證」是需要被寫下來的事，不是不必提的空白。** 若下一個人為了讓它「順便查一下 Projects」而給它 token，本單元的零 I/O 性質與 [US:S-10 AC 1] 的 fixture 驅動就同時失效。**本單元的 `action.yml` 不得宣告任何 secret 型 input。**

## SEC-1：record 全文進 Actions log 的暴露面

**事實**：本 repo 為 **public**，Actions log 公開可讀（此事實已記入 `project.md ## Mandated` 的憑證查證規則——一次意外 echo 即等同公開發布）。本單元讀 `aidlc-state.md` **全文**，並把 `current_stage`、`intent_id` 等片段寫進 action output，而 output 會出現在 workflow log 中。

**現況判定：不構成新的暴露面。** `aidlc-state.md` 本來就在公開版控中；本單元的 output 是四個具名欄位而非全文回顯。

**殘留風險**：若未來有人把機敏內容寫進 record（例如 `Parked` 理由含 token），本單元會原樣把它搬進 log——而它是**離 log 最近的一層**。

**處置（[Q2=A]）**：**不在本單元加遮罩**，改列為 **U-9 自我測試的一條斷言**——斷言 U-1 的 output 不含憑證樣式。

理由：防線落在**會持續執行**的層，而不是一段寫完就沒人再看的程式碼；且不會在 U-1 製造「已經有防線了」的錯覺。`project.md` 已記載「本 repo 唯一的 secret 掃描器（`validate_no_obvious_secrets()`）結構上看不到應用程式碼」——在 U-1 補一個作用域極窄的掃描器，正是那種讓人以為有閘門而其實沒有的形狀。

**已知代價（誠實記載）**：U-9 在 **Bolt 4**，U-1 在 **Bolt 1**，中間隔三個 Bolt。這段期間該斷言不存在。這是 [Q2=A] 選項本文即已載明的代價，不是事後才發現的。

**交付約束**：本項須列入 U-9 的 fixture 集需求，並在 Bolt 4 的 Definition of Done 可被確認。

## SEC-3：本地 composite action 沒有可 pin 的完整性錨點

[kb:technology-stack.md] 記載 repo 以 `.github/aw/actions-lock.json` 對第三方 action 做 SHA 釘選（5 筆）。**本單元的 action 拿不到這道保護**：本地 action 以路徑引用（`uses: ./.github/actions/aidlc-sync-map`），語法上沒有 SHA 可釘，完整性完全依賴 repo 的寫入權控管。

這不是本單元造成的新弱點（GitHub Actions 的本地 action 本來就如此），但它與 [ad:decisions.md] ADR-A1 已記載的缺口**疊加**：「`validate_repo_contract.py` 的 `REQUIRED_FILES` 不涵蓋它，被改名或刪除時無機制攔截」。合起來的結果是——這個承載全部決定性映射邏輯的檔案，**既無完整性錨點、也無存在性檢查**。

**處置**：ADR-A1 已把存在性檢查列為「收斂手段留 construction」的已知缺口，本站不重複指派，但把「無 pin」這一半補記於此，讓下游看到完整的形狀。最低成本的收斂是把該路徑加進 `validate_repo_contract.py` 的 `REQUIRED_FILES`——那同時解決存在性與改名兩種失效。

> **實測更正**：[kb:technology-stack.md] 的「action 釘選 全部 SHA pin」對手寫 workflow 不成立（`ci.yml` 等仍有 `actions/checkout@v4`／`@v6`、`actions/setup-node@v4`）。本節的論述不依賴該宣稱的強度——**本地 action 沒有 SHA 可釘是語法事實，與第三方 action 釘得多嚴無關**。

## SEC-2：本單元不得成為授權繞道

`phases/construction.md` 要求「標記任何繞過認證或授權檢查的程式碼」。本單元不做任何授權判斷，也不應該做——它的 `reason_code = "suppressed"`／`"parked"` 是**業務判定**（要不要寫看板），不是權限判定。

**約束**：不得在本單元加入任何「這個 intent 允不允許被同步」的檢查。若未來需要這類檢查，它屬 workflow 層或 C-3，不屬純函式映射層。

## 與上游的對應

四面向判定的依據為 `requirements.md` 的 NFR-S1～S6；暴露面事實與處置理由引自 `project.md`（public repo 的 Actions log、secret 掃描器的作用域）；本單元的零 I/O 性質與 output 清單引自 `business-logic-model.md` §承載形式與 `business-rules.md`；單元邊界引自 `unit-of-work.md` 的 U-1 條目。

---

## Review (nfr-requirements — Group B)

**Verdict**: **NOT-READY**（整組；2 Critical）
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T05:16:10Z（`date -u`）
**Iteration**: 1
**涵蓋單元**: U-1 / U-2 / U-3 / U-4 / U-5 / U-10a / U-10b

> **本段寫在 U-1 的檔內是 dispatch 指定的唯一寫入落點**，內容涵蓋整個 Group B，不專屬 U-1。本輪不再開修正迴圈，發現一律登錄後帶進閘門。

### 逐單元判定

| 單元 | kind | ADR-0006 四面向齊備？ | Verdict | 發現 |
| --- | --- | --- | --- | --- |
| U-1 map-parse-action | library | ✅ 四項皆有判定（但表格被截斷，見 m-1） | **NOT-READY** | C-2、m-1 |
| U-2 managed-block | library | ✅ 四項皆有；SEC-5 已就 `decided_at` 值域重判 audit logging | **READY**（附 1 Minor） | m-3 |
| U-3 board-client | library | ✅ 四項皆有 | **READY**（附 1 Major） | M-1、m-2 |
| U-4 binding-store | library | ✅ 四項皆有 | **READY** | — |
| U-5 notifier | library | ✅ 四項皆有 | **READY** | — |
| U-10a ci-writeback-exclusion | packaging | ✅ 四項皆有（SEC-2） | **NOT-READY** | C-1 |
| U-10b reverse-pr-exclusion | packaging | ✅ 四項皆有 | **READY**（臨界：2 Major，兩者皆關乎機制是否真的生效） | M-2、M-3 |

**被指名複查的項目，逐項結果**：

| 複查項 | 結果 |
| --- | --- |
| U-1／U-2 宣稱「零 I/O、不持有憑證」 | **成立**。`U-1/business-logic-model.md:9` 逐字「全程零 I/O：不讀檔、不呼叫 API、不寫 log」，`:21-32` 的介面表全部是字串 input／output，檔案由呼叫端 U-6 讀入。U-2 三個操作（`render`／`parse`／`content_hash`）皆吃值吐值。**「不得宣告任何 secret 型 input」的約束有效且二元可判** |
| U-2 SEC-1「sha256 不是加密也不是安全控制」 | **判定正確**。無金鑰、無簽章、任何能編輯 issue 的人都能重算——它是變更偵測（ETag 類），不是完整性保護。防迴圈失效的後果（每日增生 PR）是**可用性與正確性**事件，U-2 的 SEC-3 已把它正確歸類，兩節不矛盾 |
| ADR-0015 §11 `write_body` ⇒ U-3 的 IAM 判定 | **已反映**。`U-3/security-requirements.md:38` 逐字記載 `write_body` 需 `Issues: write`、本單元橫跨權限集合兩項 |
| §12 `rejection_notice` 與 `decided_at` 可為 `null` ⇒ U-2 的 SEC-2 揭露表與 audit logging | **U-2 自身一致**（SEC-2 補第五列、SEC-5 重判）。**但未傳播到 U-3**，見 M-1 |
| §8 權限四項的指標 | **五處齊備**：U-1 `:13`、U-3 `:32`、U-4 `:22`、U-5 `:9`（U-2／U-10a／U-10b 不涉及權限集合）。`open-items.md` 的 **B:M-5 可判定為已關閉**；但依賴該計數的散文未重算，見 m-2 |
| U-1 第五個 output `scope_note` ⇒ IAM 判定敘述 | **已更新**（`:11` 「五個字串」）。`business-logic-model.md:32` 有對應 output |
| U-10a 對 `.github/aw/actions-lock.json` 的供應鏈發現 | **成立且處置正確**。該檔實存（833 bytes）；U-10a 選定的 glob `aidlc/spaces/*/intents/*/sync-state.json` 不涵蓋它，且 `security-requirements.md:26-28` 明文把 `**/*.json` 列為禁用 glob 並給出理由。**這一項無發現** |

### 發現

| # | 嚴重度 | 檔案:行 | 一句話 | 建議落點 |
| --- | --- | --- | --- | --- |
| **C-1** | **Critical** | `U-10a/tech-stack-decisions.md:25-37`（尤其 `:29`） | `pull_request` 的 `paths-ignore` 比對的是**整個 PR diff** 而非本次 push，而 PR diff 必然含開發者的 record 變更（不在 glob 內）⇒ 過濾永不成立 ⇒ 新 run 照樣建立、`cancel-in-progress: true` 照樣取消既有 run，[US:S-1 AC 7] **兩半皆不成立**；而 U-10a 自己判定 `pull_request` 才是真正的失敗路徑 | **Bolt 1 開工前**（機制需重選，非實作細節） |
| **C-2** | **Critical** | `U-1/nfr-requirements-questions.md:58` vs 本檔 `:28`、`:32` | `[Answer]: A` 記的是選項 A（不設額外防線），但註解與 artifact 實作的是選項 **C**（列為 U-9 斷言）；`:32` 更把**選項 C 的代價原文**逐字掛成「[Q2=A] 選項本文即已載明」。人工裁決在紀錄上不可重建，而一條跨單元跨 Bolt 的交付約束（`:34` U-9 fixture ＋ Bolt 4 DoD）正壓在未被記為選中的那個選項上 | **本 stage 閘門前**：向使用者重新取得一次可驗證的裁決（`project.md` `user-stories:260822-us-L3`），或更正字母；不得由下游猜 |
| **M-1** | Major | `U-3/security-requirements.md:14` | audit-logging 列仍寫「記錄落在**受管區塊**（U-2）與 workflow log」，而 U-2 的 SEC-5（`:56-63`，本輪新增）已判定受管區塊在 `mapped` 支（＝真的有 Status 變更、NFR-S6 唯一涵蓋的那一支）**不含時間戳**；B:M-4 的重判只做在 U-2，未傳到實際寫入點 U-3 | code-generation（改為「workflow log 為正本，受管區塊只承載 intent 與 stage」） |
| **M-2** | Major | `U-10b/tech-stack-decisions.md:22`、`U-10b/security-requirements.md:34` | 交付物寫成「對四支 gh-aw workflow 的 `.md` 加 `paths-ignore`」，但 GitHub 執行的是編譯產物 `.lock.yml`（`ui-regression.lock.yml` 檔頭逐字 `DO NOT EDIT` ／ `run: gh aw compile`）。兩份產出**都沒有把 `gh aw compile` ＋ commit 四支 `.lock.yml` 列入交付**；只改 `.md` 則排除完全不生效且無紅燈，而 `stories.md:368-369` 明記本 intent **不新增** `.md` 對 `.lock.yml` 漂移的執行機制 | **Bolt 3 gate**（交付物清單補編譯步驟）。**佐證已查**：`paths:` 確實會被編譯進 lock（`code-drift-alert.md:7-12` → `code-drift-alert.lock.yml:56-62`），故風險純粹是漏了編譯步驟，不是 key 被剝除 |
| **M-3** | Major | `U-10b/security-requirements.md:14` | 補償控制寫「`ci.yml` 的 `repo-contract` job 在 push 到 `main`／`ut` 時仍會跑（U-10a 的 `paths-ignore` 同樣不阻止合併後的 push 觸發）」——**與 U-10a 自己的決定相反**：`U-10a/tech-stack-decisions.md:25`、`:31` 明訂同一條 glob 要加在**兩個觸發器**上，含 `push` 的 `main`／`ut`。一個 diff 全屬 `sync-state.json` 的變更（正是反向 PR）合併後同樣不觸發 `ci.yml` | code-generation ／ Bolt 3 gate（改寫該列；殘餘風險句仍成立，因 `git ls-files` 全域掃描會在**下一次任何** CI 執行時抓到） |
| **m-1** | Minor | 本檔 `:11-16` | ADR-0006 四面向表被 `:12-13` 插入的引文從中截斷，Encryption／Network exposure／Audit logging 三列失去表頭與分隔列、退化為字面直立線文字；`project.md` 要求四面向以**逐項判定表**呈現，正是為了讓「是否漏項」一眼可核對。U-3 `:32`／U-4 `:22`／U-5 `:9` 三處同樣的指標都放在完整表格**之後**——U-1 是唯一例外 | code-generation（把引文移到表後，比照另三個單元） |
| **m-2** | Minor | `U-3/security-requirements.md:36` | 「本單元需要……兩項，但它拿到的是完整憑證——**repo 內容寫入**的權限也在它手上」未隨 `:32` 的四項更正重算：四項集合下多出來的是 **`Contents: write` ＋ `Pull requests: write` 兩項**，不是一項 | code-generation |
| **m-3** | Minor | `U-2/security-requirements.md:61` | 「另有兩處**獨立**佐證同一次 Status 變更的時刻」——`last_synced_at` 就存在那個 commit 裡，兩者非獨立；且 `open-items.md` C-7.1 已記載 U-7 的 R-6.1 補平路徑也會推進 `last_synced_at`（該路徑無 Status 變更），故它答不了「每次 Status 變更的時刻」。重判的結論（正本為 workflow log，逐字引自 NFR-S6 驗收欄）不受影響，只有這句佐證過強 | code-generation |

### 已登錄缺口的判定（不重複列）

`open-items.md` 中落在本組範圍者，逐項核對後狀態：

| 既登錄項 | 本輪狀態 |
| --- | --- |
| **B:M-4**（`decided_at` 值域推翻 audit-logging 判定，指名 nfr-requirements gate） | **U-2 已重判且成立**（SEC-5）。但傳播未走完 ⇒ 新增 **M-1** |
| **B:M-5**（權限三項的 §8 指標，U-1／U-5 兩處缺） | **已關閉**（五處齊備）。衍生計數未重算 ⇒ 新增 **m-2** |
| B:M-1／B:m-3／B:m-4／B:m-5／B:m-6（U-1 的 `## R-6` 重號、`scope_note` 演算法、計數、`Unparseable` 的 `scope_note` 值、漂移三欄） | 皆屬 functional-design 層，**本輪不重列**；nfr 層未因它們產生新後果 |
| B:m-1／B:m-2（U-2 的 churn 敘述、R-1.2 可判定方式） | 同上，functional-design 層 |

### 未查證項（不臆測）

| 項目 | 卡在哪 |
| --- | --- |
| `pull_request` 的 `branches-ignore` 過濾 base 還是 head | 本 repo 內無可複驗設定；U-10b `tech-stack-decisions.md:45` 已指派 PRE-1（Bolt 0）實測，**且其機制選擇不依賴該答案**，故本輪不另列發現 |
| U-6／U-7／U-8／U-9／U-11 的 nfr 產出 | 屬 Group A／範圍外，本輪未開 |
| C-1 的替代機制成本 | 只查到「run 層抑制僅兩條路」（路徑過濾、commit 訊息的 `skip ci` 類標記）；job 層 `if:` **不能**滿足「既有 run 不被取消」（取消發生在 run 建立時，與 job 是否 skip 無關）。哪一條可接受屬設計裁決，本輪不代選 |

### Summary

整組最要緊的是 **C-1**：U-10a 的整個機制押在一個它自己判定為「真正失敗路徑」的觸發器上，而 `paths-ignore` 在該觸發器的語意（比對整個 PR diff）讓它在目標情境下**結構性不成立**——[US:S-1 AC 7] 兩半皆不可滿足，且失效無聲。這不是實作細節，必須在 Bolt 1 開工前重選機制。**C-2** 是另一類：人工裁決的字母與 artifact 實作的選項不同，且錯誤的來源標籤把一條跨 Bolt 的交付約束建立在未被記為選中的選項上，只能回到使用者重取。

其餘四個 library 單元（U-2／U-3／U-4／U-5）的四面向判定**紮實**——U-2 對 sha256 的定位、U-3 對「介面不提供 ≠ 回 403」的區分、U-4 對 `[aidlc-sync]` 標記雙用途的記載、U-5 對「關掉別人的 issue 不可自動復原」的嚴重度分級，都是「不適用」這種最容易寫錯的判定被認真做過的證據。剩下的三個 Major 全是同一個形狀：**規則在本單元寫對了，但依賴它的鄰檔／鄰單元沒跟上**（M-1 是 U-2→U-3，M-3 是 U-10a→U-10b，M-2 是設計檔→實際被執行的編譯產物）——與 `open-items.md` 開頭那張表診斷的形狀一致。
