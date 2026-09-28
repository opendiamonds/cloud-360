# Quality Gates — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: ci-pipeline（Construction）· 上游：build-and-test-summary.md、build-test-results.md、12 份 code-summary.md -->

## 閘門一覽（本 stage 定案後）

| # | 閘門 | 觸發 | 判準 | 阻擋強度 |
| --- | --- | --- | --- | --- |
| G-1 | `ci.yml` 的 `gate` job（`Sync write-back gate`） | 每個 PR；push 到 `main`／`ut`／`danniel/**`／`chore/**` | 判定 `is_sync`，輸出布林。**它自己永遠成功**——它的價值是「一定會留下一筆紀錄」 | **要設為 required check**（見下節） |
| G-2 | `repo-contract`／`frontend`／`backend`／`docker-build` | 同上，且 `needs.gate.outputs.is_sync != 'true'` | 各自的既有判準（合約、lint＋tsc＋build、import＋247 tests、docker build） | 阻擋（但同步 commit 下 skip） |
| G-3 | `aidlc-sync-selftest.yml` 第一段 | PR ＋ 15 條 path allowlist；`workflow_dispatch`；**每週三 05:47 UTC**（本 stage 新增） | 8 個 step 全綠（其中 `run-selftest-fixtures.py` 再轉呼 6 支上游驅動） | 阻擋該 PR |
| G-4 | `aidlc-sync-selftest.yml` 第二段 | **只有** `workflow_dispatch` | 對測試看板 #23 的端到端往返 | 阻擋（但常態不執行） |
| G-5 | `ui-regression` gh-aw | PR（已排除同步回寫路徑） | `pw-report.json` 的 `.stats.unexpected` 為 0 | 阻擋 |
| G-6 | 三支 impl workflow 內建的行為測試 | 執行期 | 各自套件全綠 | 該次同步失敗 ⇒ 通報 issue |

## G-3 的判準（本 stage 的主要變更）

**14 支離線套件現在全部在 CI 執行**（本 stage 之前是 10 支）。分佈：

| 執行方式 | 套件 |
| --- | --- |
| 第一段的直接 step（8） | `check-agentic-steps.py`、`check-paths-relations.py`、`run-selftest-fixtures.py`、`run-selftest-tests.py`、`board/run-stub-tests.py`、`record/run-stub-tests.py`、`notify/run-stub-tests.py`、`reconcile/run-reconcile-tests.py` |
| 經 `run-selftest-fixtures.py` 的 `UPSTREAM_DRIVERS` 轉呼（6） | `map/run-fixtures`、`block/run-fixtures`、`forward/run-orchestration-tests`、`reverse/run-reverse-tests`、`ci-guard/check-ci-yml`、`ci-guard/run-probe-tests` |

**通過判準**：每一支退出碼 `0` 且自印的失敗數為 `0`。全部帶 `if: always()`——任何一支紅了，
其餘各支的結果仍要看得到，因為「哪幾支一起紅」本身就是診斷資訊。

**沒有覆蓋率門檻**。`team.md ## Testing Posture` 已如實記載本 repo 無 `coverage.py`、CI 無
coverage step，`org.md` 的 80% 是宣告而非閘門。本機制的實際門檻是二元的：退出碼與失敗數。

## required status check 的處置（Q2=A）

### 問題的精確形狀

- `[aidlc-sync]` 是 **commit 訊息裡的一段文字**，任何有推送權的人都放得進去；
- 放進去之後 `gate` 讓 G-2 的四個 job 全部 skip；
- **`ut` 的 `required_status_checks` 為 `null`**（本 intent 以 `gh api` 實測），所以那次合併不會被擋；
- 即使設了，GitHub 官方文件逐字「Successful check statuses are success, **skipped**, and neutral」——把 G-2 的四個 job 設為 required **也擋不住**，因為它們是 skipped。

### 選定的處置

把 **`Sync write-back gate`**（`gate` job 的 `name`）設為 `ut` 與 `main` 的 required status
check。它是唯一沒有 `if:` 的 job，**在任何情況下都會實際執行**，所以：

- 同步 commit 的 PR：四個 job skip，但 `Sync write-back gate` 仍然 success，且它的 log 寫出 `is_sync` 為何為 true ⇒ **「這一輪被跳過了」這件事本身留下紀錄**；
- 一般 PR：五個 check 全跑。

`ci.yml` 的 `on.pull_request` **沒有 paths 過濾**（只有 `push` 那一半有 `paths-ignore`），
所以每個 PR 都會產生這個 check，不會出現「required check 永遠不報告 ⇒ PR 永久卡住」。

### 執行指令（**尚未執行**，見下方「未執行」）

`ut` 目前的 protection 物件存在但 `required_status_checks` 為 `null`，而該欄位只能經
整包 `PUT` 設定。下列 payload 逐欄對應本 stage 以 `gh api` 讀到的現值，**只新增
`required_status_checks`，其餘不變**：

```bash
gh api -X PUT repos/opendiamonds/cloud-360/branches/ut/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": false,
    "contexts": ["Sync write-back gate"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
JSON
```

執行後複驗：

```bash
gh api repos/opendiamonds/cloud-360/branches/ut/protection \
  --jq '{checks: .required_status_checks.contexts, strict: .required_status_checks.strict}'
```

### 這個處置**沒有**覆蓋的兩個洞（必須一起讀）

1. **直接推送到 `ut`**。required status check 只在 PR 合併路徑上生效。`ut` 的
   `enforce_admins` 為 `false` 且無 push restrictions，而同步憑證是 admin ⇒ **直推 `ut` 仍然
   不會被任何東西擋**。要堵它需要 push restrictions 或 `enforce_admins: true`，兩者都會
   改變人的日常工作方式，屬另一個決定。
2. **標記本身仍可被任意使用**。G-1 變成 required 之後，被跳過的那一輪**看得見**了，但
   沒有被**阻止**。如果目標是阻止，處置形狀是把標記的判定從 commit 訊息換成
   「commit 的 author 是同步身分」——那需要憑證先鑄出來（Bolt 0 gate）。

**兩者都不在本 stage 自行處置的範圍**，登錄給 Bolt 1 gate。

## G-3 新增的 `COMPILER:` 斷言（Q4=A）

四支 gh-aw 承載體的 `.lock.yml` 必須由釘住的 `v0.81.6` 編出。

| 判準 | 結果 |
| --- | --- |
| 現況（四支皆 v0.81.6） | `21 項檢查，0 失敗`（本 stage 之前是 17 項） |
| **突變 M1**：把 `ui-regression.lock.yml` 的 `compiler_version` 改為 `v0.86.2` | **紅**：`ASSERTION-FAILED: … COMPILER:ui-regression`，`21 項檢查，1 失敗` |
| **突變 M2**：刪掉 `.lock.yml` 的 metadata 首行（fail-closed 路徑） | **紅**：訊息為「讀不到…**不得因為讀不到而視為通過**」 |
| 還原後 | `21 項檢查，0 失敗`；`md5` 與突變前逐位元相同 |

**這條斷言不禁止升級 gh-aw**，它只讓升級變成一個必須被明講的決定——改
`PINNED_COMPILER_VERSION` 的那一行 diff 就是那個決定的紀錄。

### 這道閘門自己也有行為測試（否則它就是下一個「看起來在守」）

新增兩條進 `run-selftest-tests.py`，該套件由 **89 tests／368 checks** 增為
**91 tests／385 checks**：

| 測試 | 驗什麼 |
| --- | --- |
| `test_a_lock_compiled_by_another_compiler_version_is_red` | 合成樹的四支 lock 寫入 `v9.99.9-not-the-pinned-one` ⇒ rc=1、四支 `COMPILER:` 全紅、訊息帶得出預期與實得；**含對照組**（版本正確時 rc=0） |
| `test_a_lock_without_metadata_is_red_not_a_vacuous_pass` | 拿掉 metadata 首行 ⇒ rc=1、訊息逐字含「不得因為讀不到而視為通過」 |

### 實作上的一個非顯而易見處：被禁字樣

`.lock.yml` 首行 metadata 註解的前綴**本身含 R-1.2 的被禁字樣**，而
`check-paths-relations.py` 自己就在 R-1.2 的掃描面上——把前綴寫成字面值會讓
`check-agentic-steps.py` 紅（本輪實測，先紅後修）。

修法走**既有的具名查表機制**：`agentic-tokens.json` 的 `named` 表新增
`lock_metadata_prefix`，程式按名字取。**沒有把字串拆開寫**（`"gh" + "-aw"`）——
那正是該檢查宣告擋不住、且 `agentic-tokens.json` 的 `_named_readme` 逐字說「在自己的
測試裡示範它會讓『這是規避手法』失去說服力」的做法。

**範圍限於四支承載體**。本 repo 另有 7 支 gh-aw workflow（`code-drift-alert`、
`deploy-doctor`、`daily-digest`、`issue-triage` 等）目前也都是 `v0.81.6`，**暴露在同一個
風險上但不在這條斷言的範圍內**——它們不是 U-10b 的交付物，擴大到 11 支是獨立決定。
登錄給 Bolt gate。

## 明知不設為閘門的項目

| 項目 | 為什麼不設 |
| --- | --- |
| 覆蓋率門檻 | 無量測機制（`team.md` 既成事實）。設一個量不到的門檻是宣告不是閘門 |
| SAST／依賴 CVE 掃描 | 本 intent 交付物零第三方依賴（除 PyYAML）；backend 側本來就無 linter／type checker，為本 intent 單獨引入是獨立的工具鏈決策 |
| live 測試層 | 會對真實 GitHub 寫入；需憑證與人工授權（Bolt 0 gate） |
| 第二段端到端 | 同上，且會觸發 `issue-triage`（LLM 路徑） |

## 與上游的對應

閘門清單與各單元的完成判準引自 12 份 `code-summary.md`；14 支套件的規模與耗時引自
`build-test-results.md`；分支保護實測與「skipped 視同通過」引自
`build-and-test-summary.md` 的待決清單第 2 項與本 stage 的 `gh api` 複驗；
`COMPILED:` 不驗 `compiler_version` 引自 U-10b 的 `code-summary.md`；`gate` job 的
`if:`／`needs` 結構引自 U-10a 的 `code-generation-plan.md` Step 3。
