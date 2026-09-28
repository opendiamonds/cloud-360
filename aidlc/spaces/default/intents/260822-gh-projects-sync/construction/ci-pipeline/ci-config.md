# CI Configuration — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: ci-pipeline（Construction）· 上游：build-and-test-summary.md、build-test-results.md、12 份 code-summary.md -->

## 適用性判定（CONDITIONAL stage）

stage 檔的 condition 逐字：「Execute when CI pipeline needs creation or significant
modification. **Skip if CI already exists and is adequate.**」逐項對照：

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| needs creation | 否 | GitHub Actions 已存在（`project.md ## Tech Stack`），本 intent 不建新 CI 系統 |
| needs significant modification | **是** | U-10a 已對 `ci.yml` 加了一個 `gate` job 與四個 job 的 `if:`，且 build-and-test 查出 **135 tests／995 checks 從未在 CI 執行** |
| already adequate | **否** | 同上 |

**執行**（不 skip）。判定理由記入 stage diary。

## 既有 CI 拓撲（本 stage 實測，非引用）

| workflow | 觸發 | jobs |
| --- | --- | --- |
| `ci.yml` | `pull_request`（**無 paths 過濾**）＋ `push` 到 `main`／`ut`／`danniel/**`／`chore/**`（`paths-ignore: aidlc/spaces/*/intents/*/sync-state.json`） | `gate`、`repo-contract`、`frontend`、`backend`、`docker-build` |
| `deploy.yml` | PR closed 到 `ut`、`workflow_dispatch` | 部署、rollback |
| `aidlc-sync-selftest.yml` | `pull_request` ＋ 15 條 allowlist、`workflow_dispatch`、**`schedule`（本 stage 新增）** | `fixtures`（第一段）、`endtoend`（第二段，`workflow_dispatch` only） |
| `aidlc-sync-{forward,reconcile,reverse}.yml` | push／PR、cron `13 21 * * *`、cron `29 22 * * *` | 薄外層 `uses:` 對應的 `-impl.yml` |
| 11 支 gh-aw | 各自 | LLM 驅動 |

`gate` job 的 `name` 是 **`Sync write-back gate`**，且它是 `ci.yml` 五個 job 之中**唯一沒有
`if:`** 的——這個事實是 Q2 處置的基礎。

## 本 stage 的四項變更

### 變更 1（Q1=A）：四支從未在 CI 執行的離線套件併進 `aidlc-sync-selftest.yml` 第一段

查證方式：對 `.github/workflows/` 逐支 `grep -rl` 每一支測試腳本的路徑，**並逐一開檔區分
真正的 `run:` 呼叫與註解提及**——三支 `-impl.yml` 與 `ci.yml` 對測試腳本的全部命中都是註解。

| | 本 stage 之前 | 之後 |
| --- | --- | --- |
| 在 CI 執行的離線套件 | **10 / 14** | **14 / 14** |
| 第一段的檢查 step 數 | 4 | **8** |
| 未被任何 workflow 執行的 tests／checks | 135 / 995 | **0 / 0** |

新增的四個 step 各自獨立（不是一個迴圈），全部帶 `if: always()`：失敗時 GitHub 的 UI
直接指出是哪一個單元，而合成一步會讓四支的輸出混在同一塊 log 裡。

**連帶改動**：`run-selftest-tests.py::test_every_check_step_after_the_first_runs_unconditionally`
原本以 `"aidlc-sync-selftest/" in s["run"]` 判斷哪些 step 是「檢查步驟」——**以位置界定**。
四個新 step 跑的是 `aidlc-sync-board/…` 等路徑，於是被歸成 setup，而 setup 的斷言是
「不得帶 `always()`」⇒ 四條全紅，而紅的理由與它們實際做的事無關。判準改為以**角色**
界定（跑的是某個 `aidlc-sync-*` action 目錄下的 `.py`）。**這是本 intent 第三次同型**
（U-9 的 R-1.2 掃描面兩次）。

**為什麼放這裡而不是 `ci.yml`**：第一段的 allowlist 已涵蓋
`.github/actions/aidlc-sync-*/**`，也就是這四支與它們受測物**唯一**能被改動的路徑；
放進 `ci.yml` 反而會被 `gate` job 的 `[aidlc-sync]` skip 影響——同步 commit 會跳過它們。

成本：+106.82 s（board 16.90／record 24.00／notify 17.08／reconcile 48.84，本機實測），
仍落在 U-9 `performance-requirements.md` 的 10 分鐘上界內。

### 變更 2（Q3=C）：第一段加 `schedule`，每週三 05:47 UTC

U-9 的 `performance-requirements.md` 自陳這支 workflow 的常態是**不執行**，並把它列為
弱點：「一支很少跑的閘門，壞掉時不會立刻被發現」。allowlist 觸發只在有人改動同步機制
時生效——而「沒有人改動它」正是它悄悄壞掉最久的那段時間。

cron `47 5 * * 3` 避開全 repo 既有的五個排程（`0 23 * * 1-5`、`37 0 * * *`、`39 16 * * 1`、
`13 21 * * *`、`29 22 * * *`）。

**排程執行只跑第一段**：第二段的 `if: github.event_name == 'workflow_dispatch'` 讓它不碰
憑證、不建立任何 issue、不寫任何看板。

**checkout 的 ref 一併處理**：排程執行沒有 PR，`actions/checkout` 預設會檢出 default
branch（**實測為 `main`**），而同步機制的整合主幹是 `ut`（`org.md ## Way of Working`）。
第一段的 checkout 改為
`ref: ${{ github.event_name == 'schedule' && 'ut' || github.ref }}`——對 `pull_request`
（`refs/pull/<n>/merge`）與 `workflow_dispatch` 而言 `github.ref` 就是 checkout 的預設值，
**既有兩個事件的行為逐字不變**。

### 變更 3（Q4=A）：`check-paths-relations.py` 加 `COMPILER:` 斷言

判準、突變驗證、被禁字樣的處理與範圍限制見 `quality-gates.md` 的同名節。

**這一項的連帶改動比它看起來多**（全部由重跑測試逼出來，不是預先想到的）：

| 檔案 | 改了什麼 | 為什麼 |
| --- | --- | --- |
| `agentic-tokens.json` | `named` 加 `lock_metadata_prefix` | metadata 前綴含被禁字樣，而 `check-paths-relations.py` 在掃描面上 |
| `check-paths-relations.py` | 按名字取前綴與工具名，不寫字面值 | 同上；**不是**把字串拆開寫 |
| `run-selftest-tests.py` | 合成 lock 產生真實形狀的 metadata 首行（`lock_compiler` 參數） | 否則 fail-closed 路徑在每棵合成樹上都紅 |
| `run-selftest-tests.py` | `checkers` 判準由**位置**改為**角色** | 見下方變更 1 的連帶 |
| `run-selftest-tests.py` | 絆線期望集合 17 → 21 項 | 絆線正常運作的結果，不是它壞了 |
| `run-selftest-tests.py` | 新增兩條 `COMPILER:` 的行為測試 | 新增閘門而不新增它自己的測試 ＝ 下一個「看起來在守」 |

### 變更 4（Q2=A）：`Sync write-back gate` 設為 required status check

**指令已備妥但尚未執行**——它是 repo 設定變更，會立即影響所有人的合併路徑，且 `ut` 的
`required_status_checks` 只能經整包 `PUT` 設定（誤寫會清掉其他保護欄位）。完整 payload、
複驗指令、以及它**沒有**覆蓋的兩個洞，全部寫在 `quality-gates.md`。

## 一項對已核可上游的對齊更正（非本站新定案）

`build-and-test-summary.md` 的待決清單第 3 項與「逐單元覆蓋」表寫「U-10a 兩支守衛未接進
任何 workflow，要靠人記得手動跑」。**該敘述已過期**：

- U-9 的 reviewer iteration 2（M-4）與 iteration 3（F7）已把 `check-ci-yml.py` 與
  `run-probe-tests.py` 加進 `run-selftest-fixtures.py` 的 `UPSTREAM_DRIVERS`；
- 本 stage 實跑 `run-selftest-fixtures.py`，輸出可見
  `[通過] UPSTREAM:aidlc-sync-ci-guard/check-ci-yml` 與 `…/run-probe-tests` 兩行。

**過期的來源是 U-10a 自己的 `code-summary.md`**（寫於被接上之前，之後未回頭更新），
build-and-test 沿用了它而沒有回查。依 `project.md` **不回改已核可的上游 artifact**，
更正記於此處與本 stage 的問題檔。

這是本 intent 第 N 次的同型失效——「成因與後果分屬不同單元，而 per-unit 的視野停在單元
邊界」。與前幾次（U-4 的 R-7.2、U-5 的批次鍵、U-9 的 `set -o`）不同的是：這一次**接上的
動作發生在別的單元，而被接上的那個單元的文件沒有跟著更新**，方向相反但根因相同。

## 未執行 / 交還 gate

| # | 項目 | 為什麼 |
| --- | --- | --- |
| 1 | `Sync write-back gate` 設為 `ut`／`main` 的 required check | repo 設定變更，立即影響所有人的合併路徑；指令已備妥待人工確認 |
| 2 | 直接推送到 `ut` 仍不被擋（`enforce_admins: false`、無 push restrictions、憑證為 admin） | 堵它要改變人的日常工作方式，屬另一個決定 |
| 3 | `[aidlc-sync]` 標記仍可被任意使用（變更 4 讓它「看得見」而非「被阻止」） | 要阻止需把判定換成 commit author 是同步身分，前提是憑證先鑄出來（Bolt 0 gate） |
| 4 | `COMPILER:` 斷言只涵蓋四支承載體，另 7 支 gh-aw 同樣暴露 | 那 7 支不是 U-10b 的交付物；擴大是獨立決定 |
| 5 | 本 stage 的所有 CI 變更**都沒有在真實 runner 上跑過** | 需要推送才會觸發。新增的四個 step、`schedule` 觸發、`COMPILER:` 斷言在 CI 上的行為都只有本機證據 |

第 5 項要特別讀：本 stage 讓 14 支套件「在 CI 上執行」，但**這句話本身還沒有被 CI 驗證過**
——它與 U-9 交還清單第 5 項（PyYAML 在 runner 上是否可用）落在同一個未驗證面上。

## 與上游的對應

CI 拓撲、job 名稱與觸發設定為本 stage 以 `yaml.safe_load` 與 `gh api` 實讀；套件規模與
耗時引自 `build-test-results.md`；未進 CI 的四支與 135／995 的計數為本 stage 逐支比對
`grep -rl` 並開檔區分 `run:` 與註解後所得；`gate` job 的結構引自 U-10a 的
`code-generation-plan.md` Step 3；`COMPILED:` 不驗 `compiler_version` 與 v0.86.2 的六項
供應鏈變更引自 U-10b 的 `code-summary.md`；「很少跑的閘門」自陳引自 U-9 的
`performance-requirements.md`；14 支套件的分層與 live 層的邊界引自
`build-and-test-summary.md`。
