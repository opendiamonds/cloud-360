# Code Generation Questions — U-10b 反向 PR 的高成本 workflow 排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10b-reverse-pr-workflow-exclusion · kind: packaging -->

> **本檔的 `aidlc-log.ts answer` 未能在寫檔的同一輪送出**（引擎回 `Refusing to record this answer: a real human has not acted at this checkpoint this turn.`）。一輪只容許一次人工檢查點，而該輪已被 U-9 用掉。**如實記載，不繞過**：本檔的 `[Answer]` 時間戳為實際寫檔時刻（`date -u` 取值）。**稽核事件已於 2026-09-05T23:45:27Z 的真實人工回合補送**（`QUESTION_ANSWERED`），該則 details 內含本註記，使 audit shard 自身也記得住這段延遲。

> 人工已授權 orchestrator 自行裁決（2026-09-05）。**不在授權範圍**：寫入 #16、commit／push／開 PR、建立憑證型 secret、啟用正式同步、代替 Bolt gate 做 ADR 級裁決。

## Q1（阻塞）— `.lock.yml` 要用哪個編譯器產生

**Question**: `open-items.md` 的 **`N:M-5／N:M-4(B)`（Major，期限 Bolt 1）** 逐字指出本單元「**缺 `gh aw compile` ＋ commit `.lock.yml`** 這一步（GitHub 執行的是 lock）；漏了則排除完全不生效且無紅燈」。

但 repo 內四支 lock 的 `compiler_version` 全是 **v0.81.6**，本機 `gh aw` 是 **v0.86.2**。orchestrator 已在 scratch 複本上實測（未動 repo）：

| 做法 | 每檔 lock 的變動行數 | 內容 |
| --- | --- | --- |
| **釘住 v0.81.6 重編** | **4 行**（1 行 `frontmatter_hash` ＋ 2 行 `paths-ignore`；diff 的 `-`／`+` 各計） | 只有本單元要的那一項 |
| 用本機 v0.86.2 重編 | **526 行** | `actions/cache` v5.0.5→v6.1.0、`actions/checkout` v7.0.0→v7.0.1、`actions/setup-node` v6.4.0→v7.0.0、防火牆容器 0.27.11→0.27.44、`gh-aw-mcpg` v0.3.30→v0.4.9、`github-mcp-server` v1.4.0→v1.9.0，另加新的 activation 判斷 |

> **修訂（m1，2026-09-06，本 stage 自我更正；原答案與選項本文均不改）**
>
> 上表第二列的「**526 行**」是錯的：**四支都不是 526，而且四者不相等**，故「每檔」也不成立。以同一把尺（`git diff --numstat` 的 added ＋ deleted，即第一列「4 行」的計法）在 scratchpad 隔離樹上用 `gh aw` v0.86.2 重編實測：
>
> | 讀法 | ui-regression | pr-reviewer | lint-fix | contract-guard |
> | --- | --- | --- | --- | --- |
> | 對 **HEAD** 的 `.md`（本題作答當下） | 519 | 520 | 527 | 527 |
> | 對**交付後**的 `.md`（選項 B 真正的代價） | 521 | 522 | 529 | 529 |
>
> **`[Answer]: A` 不變。** 依 `project.md` 的 `functional-design:c22`（下游查證推翻的是理由而非決定時，只修理由不改決定）：本題四項依據中，②③④完全不受影響，①「A 的 diff 只含本單元真正要的那兩行，B 的 526 行有 524 行與本單元無關」的**數字**要換成上表，**結論不換**——量級仍是「五百多行 vs 4 行」，B 仍是與本單元無關的供應鏈升級。此處為就地更正記載，非新裁決。

**額外實測**：用釘住的 v0.81.6 對**未修改**的四支 `.md` 重編，產出與 repo 內既有的四支 lock **逐位元相同**（BYTE-IDENTICAL）⇒ lock 可重現，「`.md` 與 `.lock.yml` 是否一致」是可機械判定的事實。

- **A. 下載釘住的 v0.81.6 binary 到 scratchpad，用它重編四支**（不改使用者的 `gh extension`）
- B. 用本機 v0.86.2 重編 — 把 action SHA、容器映像、MCP server 的**供應鏈升級**夾帶進一個範圍是「同步機制」的 intent，且每一項新 SHA 依 ADR-0006 都需要安全審查
- C. 只改 `.md`、不產 lock，把編譯留給 Bolt 1 — 正是 `N:M-5` 逐字警告的「漏了則排除完全不生效且無紅燈」
- D. 手改 `.lock.yml` — 產生物的檔頭逐字寫 `DO NOT EDIT`；且 `frontmatter_hash` 會對不上，要嘛留下漂移、要嘛偽造雜湊

[Answer]: A. 釘住 v0.81.6 重編 <!-- 2026-09-05T19:05:32Z, orchestrator 裁決 -->

**依據**：①A 的 diff 只含本單元真正要的那兩行，B 的 526 行有 524 行與本單元無關；②B 的內容是**供應鏈變更**（新的 action SHA 與容器映像），依 `project.md` 的 ADR-0006 hard constraint 須逐項安全審查，那是獨立決策不該由本單元夾帶；③C 直接踩 `N:M-5`；④D 偽造產生物。**「升級 gh-aw 到 v0.86.2」登錄為獨立 open item**，不由本單元夾帶。

## Q2 — `N:M-2(B)`：本單元記載的補償控制與 U-10a 的實作直接矛盾

**Question**: `security-requirements.md:14` 逐字寫「`ci.yml` 的 `repo-contract` job 在 `push` 到 `main`／`ut` 時仍會跑（**U-10a 的 `paths-ignore` 同樣不阻止合併後的 push 觸發**）」。

**這句話是錯的。** U-10a 交付的 `ci.yml` 把 `paths-ignore` 加在 **`on.push`** 上（逐字：`paths-ignore: - "aidlc/spaces/*/intents/*/sync-state.json"`，且 `pull_request` 側刻意**不**加）。反向 PR 合併後推進 `ut` 的那個 commit 只動該檔 ⇒ **CI run 根本不會建立**。`open-items.md` 的 `N:M-2(B)` 正是指這一點。

- **A. 實作照原設計（四支加 `paths-ignore`）不變，但在實作註解與 `code-summary.md` 逐字更正這條補償控制，並寫出真正的殘餘控制**
- B. 因補償控制不成立而改變機制選擇 — 補償控制是**事後說明**，不是選擇 `paths-ignore` 的理由（真正的理由是 `branches-ignore` 語意未定＋GitHub 無 `labels-ignore`），推翻它不動搖決定
- C. 回改 `security-requirements.md` — 已核可上游 artifact，超出授權

[Answer]: A. 實作不變，更正記載 <!-- 2026-09-05T19:05:32Z, orchestrator 裁決 -->

**真正的殘餘控制（實查後逐項）**：

| 檢查 | 反向 PR 是否被涵蓋 |
| --- | --- |
| 禁止**路徑**（`prod`／`production`／`secrets` 作為 path part） | **會被抓到，但延後**——`validate_repo_contract.py` 於 issue #509 後改為 `git ls-files` **全域掃描**，所以\_下一次任何其他原因觸發的 CI run\_ 會紅。對反向 PR 本身無實益（它只動一個路徑固定的檔） |
| 禁止**內容**（私鑰／三雲 credential 樣式） | **完全沒有涵蓋**——`validate_no_obvious_secrets()` 只掃 `contract_files()`（`REQUIRED_FILES` ＋ baseline record 必要檔 ＋ audit shard），`sync-state.json` 不在其中，PR 側與 push 側**都不掃** |
| `ci.yml` 的 `gate` job（U-10a，讀 commit message 的 `[aidlc-sync]`） | 那是**第二層抑制**，不是控制 |

**結論**：真正的殘餘風險比原文所述**大**——不是「有一個視窗」，而是「內容掃描對這條路徑從來就不存在」。但這**不是本單元新增的**：`sync-state.json` 由 U-4 的 `record.sh` 白名單寫入，機制本身寫不進憑證；缺口只在**人手動開一個只改該檔的 PR** 這條路徑上。**登錄為 open item 指派 Bolt 1 gate**（與 `N:M-2(B)` 同一則）。

> **修訂（MAJOR-2，2026-09-06，本 stage 自我更正；`[Answer]: A` 不變）**
>
> 上表**三列是對的**，問題出在兩處下游轉錄（`code-summary.md` 的 Q2 節、`contract-guard.md` 的 production 註解）**都只抄了兩列**，掉的正是第三列——而第三列決定 PR 層的結果。兩處已補回並依作者分流。
>
> 同時本結論段有一個未被補足的推論：它點名「人手動開一個只改該檔的 PR」是唯一可達情境，卻沒說**在那個情境下第三列的判定是反的**。人開的 PR 沒有 `[aidlc-sync]` 標記（`record.sh:183` 是唯一寫者）⇒ `gate` 輸出 `is_sync=false` ⇒ `repo-contract` 的 `if: needs.gate.outputs.is_sync != 'true'` 成立 ⇒ **在該 PR 當下就執行**，禁止**路徑**的全域掃描立即命中。所以對這個唯一可達情境而言，上表第一列的「延後」不適用（那是**機器**反向 PR 才對的判定），**只有禁止內容那一列在兩種情境下都成立**。
>
> 淨效果：本題的**決定與登錄動作不變**，但待 gate 裁決的缺口比原本描述的**窄**——要補的是內容掃描，不是路徑掃描。

## Q3 — 新發現：`deploy.yml` 不在本單元範圍，但反向 PR 會觸發它

**Question**: 實查 `deploy.yml:10-14`——`on: pull_request: types: [closed], branches: [ut]`，**無任何 `paths` 過濾**。反向 PR 合併進 `ut` ⇒ 觸發自架 runner 上 `timeout-minutes: 30` 的完整部署，為的是一個 JSON 欄位。

上游從未討論過這一項：`tech-stack-decisions.md` 的實測表只列 `on: pull_request` 的**開啟側** workflow，`deploy.yml` 走的是 `closed` ＋ `merged == true`，不在那張表裡。

- **A. 不在本單元處置，登錄為 open item 指派 gate**
- B. 一併加 `paths-ignore` — 那是改變**部署管線**的行為，屬 ADR-0008（Construction／Operations 連續、deploy-on-merge）的範圍，且本單元的擁有欄逐字只寫「高成本 `on: pull_request` workflow（至少 `ui-regression`）對反向同步 PR 的排除」

[Answer]: A. 登錄，不處置 <!-- 2026-09-05T19:05:32Z, orchestrator 裁決 -->

**依據**：`project.md ## Corrections` 逐字「不得在下游 stage 擅自擴大已核可的範圍」。本項是**新發現**（不在 `open-items.md` 的 60 項內），需要一個看過 ADR-0008 的人決定「同步回寫該不該觸發部署」——那不是實作細節。

## Plan Approval

[Answer]: Approve Plan（orchestrator 自核，依人工授權） <!-- 2026-09-05T19:05:32Z -->
