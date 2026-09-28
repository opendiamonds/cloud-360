# Code Summary — U-9 自我測試 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service
     Generated: 2026-09-05T21:15:51Z（讀自 date -u）
     Last updated: 2026-09-06T03:23:58Z 起算的 iteration 3 修正輪（時間讀自 date -u）
     本檔記錄三輪 reviewer 的修正：
       iteration 1（quality-agent，14 項：1 Critical／7 Major／6 Minor）
       iteration 2（quality-agent，10 項：1 Critical／5 Major／3 Minor ＋ 1 範圍裁決）
       iteration 3（architecture-reviewer，7 項：0 Critical／5 Major／2 Minor）
     **本檔的每一個數字都在 iteration 3 的全部程式改動完成之後重測**——iteration 2 交付
     時這張表有八處已對不上它所描述的程式（reviewer iteration 3 的 F5），其中一個是交給
     Bolt 4 gate 當複核基準的計時值。 -->

## 交付物與實際行數

全部行數為 iteration 3 收尾時的 `wc -l` 實測值（`iteration 2 交付時 → 本輪`）。iteration 2
那一欄的數字**在本輪重數過**：交付時寫的 506／632／2226 分別實為 521／636／2285——那不是
筆誤而是「改完程式沒有回頭重數」，本輪一併更正（reviewer iteration 3 的 F5）。

| 檔案 | 行數（`wc -l` 實測） | iteration 3 本輪 |
| --- | --- | --- |
| `.github/workflows/aidlc-sync-selftest.yml` | 512 → **599** | 修改（F1：allowlist 加三條真正可達的腳本；F2：清理改為關閉 ＋ 移出看板；F3：測試 item 載體的註解；F4：`20 分鐘` 那句補上交還落點） |
| `.github/actions/aidlc-sync-selftest/check-agentic-steps.py` | 1269 → **1434** | 修改（F1：`_walk_python` 收窄成只收 subprocess 呼叫位置；F7：報告分三區；新增 `scan_surface()`／`build_closure()` 供 COVERAGE-2 使用） |
| `.github/actions/aidlc-sync-selftest/check-paths-relations.py` | 521 → **554** | 修改（F1：新增 `COVERAGE-2`——掃描面 ⊆ allowlist ∪ SCAN_EXEMPT） |
| `.github/actions/aidlc-sync-selftest/run-selftest-fixtures.py` | 636 → **696** | 修改（F4：A-4／A-5 承接方式的偵測力邊界表；F6：三處 subprocess 加 `timeout=` 與具名逾時訊息） |
| `.github/actions/aidlc-sync-selftest/run-selftest-tests.py` | 2285 → **2507** | 修改（新增 7 條測試——82 → 89；F6：三處 subprocess 加 `timeout=`；絆線訊息補上「step 7 的紅有兩種來源」） |
| `.github/actions/aidlc-sync-selftest/agentic-tokens.json` | 54 → **54** | 未動 |
| `.github/actions/aidlc-sync-ci-guard/run-probe-tests.py` | 327 → **327** | 未動（iteration 2 的 M-6 之後未再改） |
| `<record>/.test-fixtures/` | 未動 | — |

測試規模：**44／161（iteration 1 前）→ 69／287（iteration 1 後）→ 82／336（iteration 2 後）
→ 89 tests／368 checks（iteration 3 後）**，0 failures。iteration 2 交付時本檔寫的是
「82 tests／335 checks」，實測為 336——同一種「沒有回頭重測」的失誤。
probe 行為測試：**13 項**（本輪未動）。

## 本輪修的 14 項

### F1（Critical）— R-1.2 的視野停在 workflow 檔邊界

`scan()` 原本只 glob `.github/workflows/aidlc-sync-*.yml`，五份 composite action 從頭到尾沒被開過。修法是把掃描面由 1 個擴為 3 個：

1. `.github/workflows/aidlc-sync-*.yml` 的 `jobs.*.steps`（原有）
2. `.github/actions/aidlc-sync-*/action.yml` 的 `runs.steps`——**套用同一份 `step_surfaces()`／`judge_surface()`**，不另寫一份判定（對其中一種嚴格、對另一種不看，正是 F1 的形狀）
3. 那些目錄下的 `*.sh`／`*.py`——剝掉註解與敘述後比對 `AGENTIC_TOKENS`

附帶三項讓這個擴充不會再度靜默失效：

- **`LOCALREF-1`**：workflow 以 `uses: ./.github/actions/aidlc-sync-X` 參照的每一個 action 都必須存在並被掃到。掃描集合＝glob 掃得到的 ∪ 實際被參照的，所以「把 action 搬走／改名」不可能靜默地少掃一份。
- **`USING-1`**：`runs.using` 必須是 `composite`。node／docker action 的執行面是一個本檢查看不進去的映像。
- **報告逐一印出掃到的檔**（本 repo 實測：7 份 workflow、5 份 `action.yml`、20 支腳本）。F1 的兩個繞過之所以能拿到「0 失敗」，正是因為報告只說結果、不說它看了哪些檔。

**兩處對 reviewer 建議的偏離，理由如下**：

- **`.py` 不用 `strip_shell_comments()` 剝**，改用 `tokenize` 剝註解與 docstring。原因是那個 shell 狀態機會把 `"""…"""` 當成「空字串、空字串、然後一段裸文字」，docstring 內容原樣留下——本 repo 的 `run-reverse-tests.py` 與 `run-reconcile-tests.py` 各有一句 docstring 在解釋「三支既有排程皆為 gh-aw」，照抄建議會把它們判紅。**不連字串值一起剝**：真正的繞過長成 `subprocess.run(["copilot", …])`，那正是一個字串值。
- **腳本掃描面不含 `LOCK_TOKEN`（`.lock.yml`）**。`check-paths-relations.py` 合法地處理那個檔名（被排除的四支 gh-aw 有 lock），把它納入會得到一份全紅而沒有意義的報告。workflow／`action.yml` 的 `run:` 面仍然含它。

**豁免，逐檔具名**：`VOCABULARY_OWNERS` 三支（`check-agentic-steps.py`、`check-paths-relations.py`、`run-selftest-tests.py`）——它們必須逐字寫出被禁的字樣才能檢查／解釋／構造它。這是這道掃描唯一的洞，所以它的形狀是逐檔路徑而非目錄樣式，並由 `test_the_vocabulary_exemption_is_exactly_three_named_files` 釘住（加第四個檔就紅）。同目錄的 `run-selftest-fixtures.py` **不在**豁免內。

### F2（Major）— 轉呼只斷言「總數 > 0」

`UPSTREAM_DRIVERS` 由 2-tuple 改為 4-tuple，第三欄是**這一次轉呼所宣稱承接的具名證據**，斷言它們逐一出現在該驅動的 stdout。總數擋得住「刪光」，擋不住「刪掉我要的那幾條」。

具名清單（實測核對過名稱存在）：

| 驅動 | 具名證據 |
| --- | --- |
| `aidlc-sync-map/run-fixtures.py` | `test_r1_1_first_match_wins`、`test_r1_2_present_but_empty_returns_empty_string`、`test_r1_3_absent_returns_null_not_empty`、`test_r1_4_indented_is_not_a_match`、`test_r3_1_parked_beats_completed` |
| `aidlc-sync-block/run-fixtures.py` | `test_serialization_is_deterministic_and_locale_independent`、`test_r4_4_serialization_golden_byte_identical`（A-2） |
| `aidlc-sync-forward/run-orchestration-tests.py` | `test_r5_5_no_drift_no_write`、`test_multi_round_suppressed_converges` |
| `aidlc-sync-reverse/run-reverse-tests.py` | `test_r2_1_diff_never_contains_aidlc_state_md`、`test_r6_3_outcome_2_pr_fails_branch_deleted`、`test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan`（A-4／A-5） |
| `aidlc-sync-ci-guard/check-ci-yml.py` | `[通過] SEC-1a`／`SEC-1c`／`SEC-1d`／`MARKER-1` |
| `aidlc-sync-ci-guard/run-probe-tests.py` | 三條標記偵測情境 |

**對 reviewer 建議的偏離**：後兩支不印 `[ok] test_x`（它們是檢查器型的驅動，印 `[通過] <代號>`），所以證據字串照它們的實際輸出寫。照抄一個它不會印的字串等於一條永遠紅的假斷言。`test_every_named_upstream_test_actually_exists_upstream` 會回上游原始碼逐一核對這些名稱，改名時那裡先紅。

順帶把 `parse_driver_summary()` 由回傳 `(tests, checks, failures)` 改為具名欄位的 dict，並支援四種收尾格式。理由：新加的兩支只有一個數字（檢查項數），把 19 項檢查寫成「19 tests, 19 checks」會在報告上長得像一個算出來的數字，而它是複製的。

### F3（Major）— DISJOINT-1 只跟單一 glob 求交集

改為收集五個承載體**實際宣告**的每一條 `paths-ignore`（附來源檔名），與推導出的寫入 glob 一起進交集判定。訊息指名「哪一條 allowlist ∩ 哪一條排除 glob（來自哪一個承載體）」。本 repo 實測納入判定的排除 glob 共 **2 條**（推導出的 1 條 ＋ `ci.yml` 宣告的 1 條，兩者字串相同）。

### F4（Major）— GitHub 的預設 shell 是 `bash -e {0}`

**修的順序是先讓測試紅**：`_bash()` 先改成 `["bash", "-e", "-c", script]`，跑一次確認 `test_stage_2_create_step_says_which_dependency_failed` 紅（rc 為 board.sh 的 7、診斷一個字都沒印），再改 workflow。三處修法：

- 建立 item 與往返：`rc=0; … || rc=$?`（原本的 `cmd` 後接 `rc=$?` 在 `-e` 下走不到第二行）
- R-1.3：把「取狀態碼」與「判定」拆開，取的時候一律 `|| true`——**403 是預期結果，不是錯誤**。原寫法讓通過路徑當場殺掉 step、寫入成功時才走得到 `ASSERTION-FAILED`，方向是反的。

另補一條 `test_the_step_harness_matches_githubs_default_shell`：以行為斷言 `_bash` 的 `-e` 真的生效（`false; echo reached` 必須 rc≠0 且沒印出 reached），並斷言 workflow 沒有任何 `shell:` 與 `defaults.run.shell`。**沒有這一條，M9 突變（把 `_bash` 退回無 `-e`）抓不到**——實測第一次跑 M9 時 0 failures。

### F6（Major）— CRED-1 沒有存在性前提

`CRED-0c`（`MAP_OUTPUTS` ⊆ `decision`）與 `CRED-0d`（`decision` ⊆ `MAP_OUTPUTS`，反向）。後者是為了讓 U-1 日後新增第六個 output 時，A-1 的掃描範圍**大聲地**少一項。

### F7（Major）— A-6 斷言的九個檔案不在觸發 allowlist 內

兩件事：

1. workflow 的 `on.pull_request.paths` 增列 `.github/workflows/ci.yml` 與四支 gh-aw 的 `.md`／`.lock.yml`（共九條）。YAML 是手寫的（`on:` 不能求值），但**不是第二份真實來源**：`check-paths-relations.py` 的 `COVERAGE-1` 從 `GH_AW_CARRIERS` 產生要求清單並逐一比對，少一條就紅。加完 **DISJOINT-1 仍成立**（實測 `[通過]`）。
2. 第一段的上游驅動清單加入 `check-ci-yml.py` 與 `run-probe-tests.py`。**reviewer 的發現屬實**：對 `.github/` 全樹 grep，`check-ci-yml.py` 當時沒有被任何 workflow 執行（唯一命中是 `ci.yml:24` 的一行註解）——U-10a 交付的守衛是死的。

   > **更正（iteration 2 的 M-4）**：本段原本寫「加進來之後它每次第一段都跑」。**那句話當時不成立。** 承載它們的 step（`A-1 / A-2 / A-3`）既無 `if: always()` 也無 `continue-on-error`，而它前一步 A-6 對真實 repo **是紅的**（U-10b 未交付），所以整個 `run-selftest-fixtures.py` 在 CI 上一次都不會執行——守衛只是從「沒有被任何 workflow 執行」換成「被一個永遠跑不到的 step 執行」，仍然是死的。連帶不執行的還有 A-1／A-2／A-3 的全部 fixture 斷言與 F2 的全部具名證據。已於本輪加上 `if: always()` 修正（見下）。

### F8（Major，安全）— 第二段改為只在 `workflow_dispatch` 執行

依 orchestrator 的保守收窄裁決。`endtoend` job 加 `if: github.event_name == 'workflow_dispatch'`；第一段維持 `pull_request`（它是閘門，且不碰憑證）。`needs: fixtures` 未動，兩段順序不受影響（該 `if:` 不含 `always()`／`cancelled()`，不覆寫 needs 的跳過語意）。

> **交還 Bolt 0 gate（IAM 面向）**：`security-requirements.md` 的 ADR-0006 四面向表**沒有處理這一面**——IAM 欄只指向缺口 Q-1 的 403，沒有涵蓋「以 `pull_request` 執行 PR head 的腳本、並餵入組織層讀寫憑證」這條路徑。該檔是已核可上游，本單元**不回改**。要放寬本段的觸發條件，必須連同這一項一起裁決。

### F9〜F14（Minor）

| # | 修法 |
| --- | --- |
| F9 | 「39 條 map 測試」→ **38**（實跑 `run-fixtures: 38 組測試`）。並補 `test_the_map_test_count_in_the_docstring_is_the_real_count`：從說明段抽出該數字，與 map 驅動的 `def test_` 實數比對——這個數字可以被計算，所以由計算得到 |
| F10 | `FIXTURE_DIR_REL` → `FIXTURE_DIR_GLOB = "aidlc/spaces/*/intents/*/.test-fixtures"`，與 workflow allowlist 同一個形狀；恰好一個才通過，找到兩個時**不猜** |
| F11 | `+` 量詞遇到即 `ExternalError`，與同函式對 `!` 與混寫 `**` 的處理一致 |
| F12 | 見下方「第一段的實測耗時」 |
| F13 | 新增三條抽出腳本的行為測試（建立 item 的成功與失敗、往返的兩類紅燈、R-1.3 的三種情境）。這一整節在本輪之前**不存在**：第二段除了 preflight 與 SEC-3 之外沒有任何一行被執行過 |
| F14 | 改用 `actions/setup-python@v5`（釘 `3.12`）。理由寫在 workflow 註解：`--break-system-packages` 只是繞過 PEP 668 的保護，並把第一段的可重現性押在系統 Python 的當下狀態上 |

## 第一段的實測耗時（F12）

本機（macOS，Darwin 25.5.0）依 workflow 的三個步驟順序實跑：

```
real 92.78   user 54.76   sys 83.60
```

分項：

| 步驟 | 實測 |
| --- | --- |
| `check-agentic-steps.py` | 0.26 s |
| `check-paths-relations.py` | 0.38 s |
| `run-selftest-fixtures.py` | 93.75 s（單獨計時） |

**成本主體是六支上游驅動而不是 fixture 數**——`scalability-requirements.md:25` 的推論前提（成本隨 fixture 數成長）與此不符。F7 新加的兩支只占約 1.0 s（`check-ci-yml.py` 0.08 s、`run-probe-tests.py` 0.89 s），reviewer 修正前實測的 90.69 s 與本輪的 92.78 s 差距主要是機器雜訊。

**這是本機值，不是 runner 值。** `performance-requirements.md` 給的 10 分鐘上界是估計值而非量測值，該檔本身寫明須在 Bolt 4 首次真實執行後複核——本節提供的是複核基準。

## 驗證（實測輸出）

```
$ python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py
69 tests, 287 checks, 0 failures
全數通過。

$ python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py        # rc=0
掃描面 1／3：7 份 workflow 原始檔
掃描面 2／3：5 份 composite action.yml（block、board、map、notify、record）
掃描面 3／3：20 支腳本
R-1.2 代理式步驟靜態檢查：8 項檢查，0 失敗。

$ python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py      # rc=1（正確）
A-6 路徑集合關係：16 項檢查，8 失敗。
失敗項＝ IGNORE:{ui-regression,pr-reviewer,lint-fix,contract-guard}.{md,lock.yml}

$ python3 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py      # rc=0
第一段 fixture 驅動：25 項檢查，0 失敗。
```

**A-6 的 16 項（原 15 項）**：多的一項是新增的 `COVERAGE-1`（通過）。**失敗仍恰為 U-10b 的八個承載體項目**，數量與內容都沒變——F3／F7 的改動沒有讓真實 repo 多紅或少紅任何一項，這一點由 `test_the_real_repo_state_is_what_we_say_it_is` 逐項比對集合相等（不是比對數量）。

兩支 validator：

```
$ python3 scripts/validate_repo_contract.py   → rc=0（passed）
$ python3 scripts/validate_env_contract.py    → rc=0（passed）
```

其餘單元的測試套件全部重跑，rc 皆為 0：map 2707 斷言、block 550 斷言、board 31 tests、record 31 tests、notify 35 tests、forward 39 tests、reverse 38 tests、reconcile 37 tests、ci-guard 11 項行為測試＋19 項檢查。

## 突變驗證（17 條，每條都跑完整套件並記錄實際紅的測試）

| # | 突變 | 實際紅的測試 | 是否為預期那條 |
| --- | --- | --- | --- |
| M1a | 不掃 composite `action.yml` 的 `runs.steps` | `test_agentic_step_hidden_in_a_composite_action_is_red` | 是 |
| M1b | 不掃 action 目錄下的 `.sh`／`.py` | `test_agentic_call_hidden_in_a_composite_action_script_is_red`、`test_composite_action_baseline_is_green`、`test_python_docstring_mention_is_not_red_but_a_call_is` | 是（後兩條是前提斷言，同一個掃描面） |
| M1c | 不理會參照得到卻不存在的 action | `test_a_referenced_local_action_that_does_not_exist_is_red` | 是 |
| M2 | 轉呼只斷言總數 | `test_an_upstream_driver_missing_its_named_tests_is_red` | 是 |
| M3 | DISJOINT-1 只比推導出的單一 glob | `test_a_carrier_that_ignores_the_selftest_allowlist_is_red`、`test_a_gh_aw_carrier_that_ignores_the_selftest_allowlist_is_red` | 是（兩條分別測 `ci.yml` 與 `.lock.yml` 兩個來源） |
| M4 | 不驗 output 存在性 | `test_a_missing_map_output_is_red_not_a_vacuous_pass` | 是 |
| M4b | 不驗多出來的 output | `test_an_unexpected_map_output_is_red` | 是 |
| M5 | allowlist 拿掉九條承載體路徑 | `test_the_real_repo_state_is_what_we_say_it_is` | 是（COVERAGE-1 對真實 repo 紅，使失敗集合多一項） |
| M6 | `+` 退回當字面字元 | `test_a_plus_quantifier_in_a_path_pattern_is_fail_closed` | 是 |
| M7 | fixture 目錄退回寫死 record | `test_the_fixture_dir_is_resolved_by_glob_not_a_hardcoded_intent` | 是 |
| M8 | 拿掉第二段的 `workflow_dispatch` 限制 | `test_stage_2_only_runs_on_workflow_dispatch` | 是 |
| M9 | `_bash` 退回無 `-e` | `test_the_step_harness_matches_githubs_default_shell` | 是（**補這條測試之前，M9 是 0 failures**——見 F4） |
| M10 | 建立 item 退回 `cmd` 後接 `rc=$?` | `test_stage_2_create_step_says_which_dependency_failed` | 是 |
| M11 | 往返退回 `cmd` 後接 `rc=$?` | `test_stage_2_round_trip_separates_external_error_from_assertion_failure` | 是 |
| M12 | R-1.3 退回把 `gh api` 直接接進管線 | `test_r13_probe_asserts_403_instead_of_dying_on_it` | 是 |
| M13 | 拿掉 `actions/setup-python` | `test_stage_1_pins_its_python_instead_of_trusting_the_runner_image` | 是 |
| M14 | 說明段的 map 測試數退回 39 | `test_the_map_test_count_in_the_docstring_is_the_real_count` | 是 |

## iteration 2 的 10 項（1 Critical／5 Major／3 Minor ＋ 1 範圍裁決）

> **這是最後一輪修正。** reviewer 已建議停止對抗式審查迴圈——它的 10 項發現全部二元可判、
> `git diff` 即可核對，正確性由本輪的突變驗證負責，修完不再送審。

### C-1（Critical）— 掃描集合由「檔案位置」換成「執行可達性」

iteration 1 的邊界是「只看 workflow 檔」，iteration 2 修成「再看 `.github/actions/aidlc-sync-*/`
底下的 `.sh`／`.py`」——**推了一格，沒有換原則**。reviewer 構造五個繞過，每一個單獨都
rc=0「8 項檢查，0 失敗」，其中 B1 **完全不需要惡意**：把 helper 放 `scripts/`（本 repo 的
慣用落點，`ci.yml` 有三個呼叫點）就掃不到了。

**換原則**：掃描集合 ＝ 從四支同步 workflow（＋ `ci.yml`）出發的**執行可達閉包**。對每個
已在掃描面上的 `run:` 本體或腳本本體，解析它呼叫的本 repo 檔案（`python3 X`／`bash X`／
`source X`／`./X` …），遞迴到不動點。解析不出來的呼叫目標 **fail-closed**。

**同步機制自己的五個 action 目錄仍是種子**（不是只有被 `uses:` 參照到才掃）——可達閉包補
的是「判定被搬到 repo 別處」，不取代「自己的目錄一律全掃」。實測本 repo 三支 `*-impl.yml`
其實完全沒有 `uses: ./.github/actions/…`（它們直接 `bash "$MAP_SH"`），只靠參照回填的話那
五份 `action.yml` 會一份都掃不到，等於 F1 原樣復發。

#### 換原則之後的代價（實測，不是估計）

| 項目 | 數值 |
| --- | --- |
| 掃描面：workflow 原始檔 | 8 份（7 支 `aidlc-sync-*` ＋ `ci.yml`） |
| 掃描面：composite `action.yml` | 5 份 |
| 掃描面：腳本 | **34 支**（iteration 2 為 20 支） |
| **解不開的呼叫目標** | **0 條** |
| `UNRESOLVABLE_INVOCATIONS` 具名豁免 | **0 條** |
| 真實 repo 的結果 | rc=0，8 項檢查，0 失敗（與 iteration 2 相同） |

**fail-closed 沒有產生任何假紅燈**，但那不是免費得到的。要讓「解不開」歸零，解析器必須真的
解得開下面這些——每一項都是實測踩出來的，不是預先想到的：

1. **`defaults.run.working-directory`**（workflow 層與 job 層）。`ci.yml` 的 backend job 有
   `working-directory: backend`，它的 `python scripts/dump_openapi.py` 指的是
   `backend/scripts/dump_openapi.py`（**該檔真的存在**）。不看 working-directory 就會對一個
   存在的檔案報「找不到」。
2. **字面賦值鏈**：`WORKSPACE="${GITHUB_WORKSPACE:-$PWD}"` → `ACTIONS_DIR="${WORKSPACE}/…"`
   → `MAP_SH="${ACTIONS_DIR}/…/map.sh"` → `bash "$MAP_SH"`。
3. **Actions 內建變數的兩套語法**：shell 的 `${GITHUB_ACTION_PATH}`（五份 `action.yml` 用這個）
   與表示式的 `${{ github.action_path }}`（合成 fixture 用這個）。只認一種，另一種就變成假紅燈。
4. **`$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` 慣用法** → 腳本自己的目錄。`board.sh` 靠
   它算出 `BLOCK_SH`，那是本 repo 唯一的 action → action 呼叫。
5. **續行折疊**（`\` ＋ 換行）。本 repo 的呼叫幾乎全長成
   `AIDLC_OPERATION=… \<換行>  GITHUB_OUTPUT="$out" bash "$RECORD_SH"`；不折疊會讓那個裸 `\`
   卡在命令名的位置，**14 個 `bash "$X"` 一個都認不出來**（而檢查看起來還是綠的）。
6. **引號要算數**。第一版的切段是一條 `re.split`，於是
   `sed -n 's/^SYNC_MARKER="\(.*\)"$/\1/p'` 的正則被切碎、碎片被當成命令，三支 `*-impl.yml`
   各報一條假的「解不開」。而且雙引號狀態也要追——漏掉它時 `echo "it's fine"` 的撇號會開啟
   一段假的單引號，把整段腳本剩下的部分吞進同一個 segment。
7. **本體內自己定義的包裝函式**（`run_pure() { env -u GH_TOKEN … "$@"; }`）要當成透明前綴，
   否則 `run_pure … bash "$MAP_SH"` 認不出來。但剝掉包裝函式之後**不再**認 `.`／`source`／
   `./x`——那時剩下的是函式引數（實例：`blob_or_empty_object . "HEAD:${rp}"` 的那個 `.`）。

**fail-closed 的界線**：只對「語法本身證明有檔案被執行」的形狀生效（`bash X`／`python3 X`／
`source X`／`./X`）。命令位置是一個裸變數時（`"$MAP_SH"` 直接執行）只在解得開時收進閉包，
解不開就略過——實測本 repo 有 10 條這種形狀（`eval "cur=\"\${$__name}\""`、被跳脫字元切碎
的 `[ "$x" = y ]` 之類），**全部不是呼叫**，對它們判紅只會製造假紅燈。這條界線的代價是
`"$SOME_SCRIPT"` 直接執行且變數算不出來時本檔看不到它，已寫進模組 docstring。

**非 shell 的本體不 fail-closed**：Python 檔走字串字面值的 best-effort（`.py` 本身仍在 token
掃描面上），`.ts`／`.js` 只做 token 掃描。拿 shell 的切段規則去解 TypeScript 會把它的正則判成
「解不開的呼叫」——那是假紅燈不是嚴格。

### M-1（Major，新引入）— 腳本副檔名由允許清單改為排除清單

`(".sh", ".py")` 讓 `.bash` 與**無副檔名**的檔案都掃不到（reviewer 實測兩者都 rc=0），`.js`／
`.mjs` 同樣落空而 `actions/github-script` 是 Actions 的一級公民。改為排除已知的非執行副檔名
（`.md`／`.json`／`.yml` 等 40 個），其餘一律當腳本掃。與同檔 USES-1 對允許清單的既有論證
（「禁止清單只擋得住它認得的名字」）方向一致——那裡剛好用反了。

### M-2（Major，新引入）— `VOCABULARY_OWNERS` 由整檔豁免縮成一份純資料檔

原本整檔豁免三支 `.py`，其中兩支**每個 `pull_request` 都在 CI 執行 PR head 的程式碼**；釘住它
的測試對「提到 token」與「呼叫 token」給同一個答案。reviewer 實測把真正的
`subprocess.run([…])` 加進被豁免的檔 → rc=0。

三份 token 清單抽到 `agentic-tokens.json`（**只豁免這一個資料檔**），三支 `.py` 全部回到掃描
面內。實測發現 `check-paths-relations.py` 本來就零命中、根本不需要豁免；`run-selftest-tests.py`
需要構造違規樹，改為按名字到資料檔取（`NAMED_TOKENS`）。

> **為什麼不是把字串拆開寫**（`c = "cop"; d = "ilot"`）：拆字正是本檢查宣告擋不住的那種刻意
> 混淆，在自己的測試裡示範它會讓「這是規避手法」這句話失去說服力。具名查表沒有這個問題——
> 檔案裡完全不出現那個詞的任何片段。

> **對 reviewer 建議的一處偏離**：它建議 `.txt`，本輪用 `.json`。理由是 `agentic_run_tokens` 的
> 第一項是 `"gh aw "`，**結尾有一個有意義的空白**（防 `gh aw compile` 而不該命中 `gh awesome`），
> 純文字檔的行尾空白會被編輯器與 pre-commit 靜默吃掉。

### M-3（Major）— 具名證據擋不住「留著名字、清空本體」

reviewer 雙向實測：改名 → 紅 ✅；**清空本體保留名字與 docstring → 全綠 ❌**，而 CI log 上的
斷言數由 154 掉到 **151**，數字就印在那一行，同一行仍逐字宣稱它承接了「無漂移 ⇒ 零看板寫入、
零 commit」。`numbers_ok` 只要求 `> 0`，沒有基準值。

`UPSTREAM_DRIVERS` 每項加第五欄 `(單元數基準, 斷言數基準)`，斷言**實得 ≥ 基準**。基準值由實跑
取得（每支都會印自己的收尾行）：

| 驅動 | 單元數 | 斷言數 |
| --- | --- | --- |
| `aidlc-sync-map/run-fixtures.py` | 38 | 2707 |
| `aidlc-sync-block/run-fixtures.py` | 34 | 550 |
| `aidlc-sync-forward/run-orchestration-tests.py` | 40 | 154 |
| `aidlc-sync-reverse/run-reverse-tests.py` | 39 → **46** | 246 → **308** |
| `aidlc-sync-ci-guard/check-ci-yml.py` | 19 | 不適用（收尾行只有一個數字） |
| `aidlc-sync-ci-guard/run-probe-tests.py` | 13 | 不適用（同上） |

斷言的是 **≥ 而不是 ＝**：加測試不該讓這裡紅，減測試才該。

> **reverse 那一列於 2026-09-06 提高**（39／246 → 46／308）：U-8 的 reviewer 以 76 條突變
> 查出 14 條真實未覆蓋行為（其中 R-6.1 的查詢參數幾乎完全沒有斷言，三條單 token 突變讓
> 防重複開 PR 整條失效而 39 條全綠），修正輪加了 7 條測試。下限沒跟著提高的話，有人把那
> 7 條刪掉不會讓本檢查紅。程式內的值（`run-selftest-fixtures.py` 的 `UPSTREAM_DRIVERS`）
> 早已是 46／308，本表在 iteration 3 才補上——這正是 reviewer iteration 3 的 F5 抓到的
> 「文件對它所描述的程式已過期」。

### M-4（Major）— F7 新接的兩支驅動，那個 step 在 CI 上到不了

`aidlc-sync-selftest.yml` 的 step 6（第一段 fixture 驅動）既無 `if: always()` 也無
`continue-on-error`，而它前一步 A-6 對真實 repo **是紅的** ⇒ `run-selftest-fixtures.py` 在 CI 上
**一次都不會執行**。連帶不執行的有 A-1／A-2／A-3 的全部 fixture 斷言、F2 的全部具名證據、以及
F7 這一輪才接進來的 `check-ci-yml.py` 與 `run-probe-tests.py`。

修法：**第一道檢查之後的每一道**都加 `if: always()`（同 job 其餘檢查 step 一併檢查過）。setup
步驟刻意**不加**——它們失敗時不該讓三道檢查各自再失敗一次。code-summary 的 F7 段落已就地更正
（見上方 F7 的更正區塊）。

### M-5（Major）— `ci.yml` 承載同步判定卻不在任何代理式檢查的視野內

`ci.yml` 納入 R-1.2 的掃描面。**但 `uses:` 那一面不能照搬**（對 brief 的一處刻意偏離）：同步
資產用的是**允許清單**，而 `ci.yml` 合法使用 `docker/setup-buildx-action@v3` 與
`docker/build-push-action@v6`——照搬會讓真實 repo 立刻恆紅，而恆紅的閘門等於沒有閘門。所以
`ci.yml` 走 `strict_uses=False`：`engine:` 鍵、`run:` 的 token 掃描、`uses:` 的**已知代理式禁止
清單**照樣適用，只有那份為同步資產量身訂做的允許清單不適用。M-5 要攔的是「判定被搬進 agent
step」，這三件事就攔得住（實測：注入 `is_sync="$(<agent> -p …)"` ⇒ RUN-1 紅並指名 gate job）。

**附帶評估（brief 要求回報，未改）**：`run-probe-tests.py` 確實**以真實 shell 執行從 `ci.yml`
抽出的腳本**——reviewer 注入代理式 CLI 之後，本機的該 CLI 真的被啟動並等待輸入，測試掛住直到
被 `pkill`。這是「行為測試執行受測資料」的固有性質，不是缺陷（它正是這支測試相對於文字比對的
價值所在）。**已寫進該檔的模組 docstring**讓下一個人知道；未加逾時或沙箱，理由是那會削弱它
「照 GitHub 的方式真的跑一次」的保證，且風險僅限於本機手動執行。

### M-6（Major，新引入）— 注入測試的注入點是從它所不信任的那段文字算出來的

`inject_after_set_block()` 錨定「最後一行 `set `」並插在其**後**，於是注入永遠落在 `set +e` 的
保護區內。reviewer 實跑四種位置，V2（`set +e` 下移到判定邏輯之後、兩行 echo 之前）**全綠**，
而 `git log`／`printf | grep` 那整段全部在 errexit 下裸奔。

新的錨點與 `set` 的位置**無關**：注入在「第一個不是 `set` 的敘述」之前，以及「最後一個敘述」
之前（後者抓「中途把 errexit 重新打開」）。斷言的性質變成「**在第一個非 `set` 的敘述執行之前，
errexit 必須已經關掉**」。

> **對 brief 的一處刻意偏離**：brief 寫「直接注入在整段腳本的第一行」。實測那會讓**正確的腳本
> 也必死**——GitHub 用 `bash -e {0}`，errexit 從第 1 行就開著，而 `set +e` 再怎麼早也只能是第一
> 個敘述，不可能早於「第一行」。照字面做出來的是一條恆紅的測試。這裡取它的意圖（注入點不得由
> `set` 的位置推導）而不是它的字面。四種位置的實測結果見突變表。

### m-1（Minor）— LOCALREF-1 不收集 `action.yml` → `action.yml` 的參照

`action_surfaces()` 的 `uses:` 現在也回填 `referenced_actions`（在統一的 `_judge_and_expand()`
裡處理，workflow 與 action 走同一條路徑）。模組 docstring 宣稱的「搬走／改名不可能靜默地少掃
一份」在 action → action 這條邊上原本不成立。

### m-2（Minor）— 執行面是禁止清單、`uses:` 面是允許清單，落差沒寫下來

不改機制（執行面的允許清單成本過高），在模組 docstring 寫明：本檔是**閘門不是沙箱**，防的是
**無意的搬移**（C-1 的 B1 就是照著既有形狀寫程式寫出來的），**擋不住刻意的混淆**（B4 的拆字、
B5 的 `eval` ＋ base64）。並補一條 `test_deliberate_obfuscation_is_out_of_scope_and_says_so`
把這個邊界寫成可執行的斷言——它同時斷言那兩種手法確實 rc=0、以及 docstring 逐字載明了這件事。
**這條測試斷言的是「已知且已載明」，不是「已修好」**。

### 範圍裁決（orchestrator）— `run-selftest-tests.py` 接進第一段

它過去**不被任何 workflow 執行**（`aidlc-sync-selftest.yml` 對它的四處命中全部是註解），後果是
兩輪合計 24 項修正的迴歸保護在 CI 上等於零。本輪接進第一段並加 `if: always()`。

**已知後果一併處理**：`test_the_real_repo_state_is_what_we_say_it_is` 是刻意的絆線，U-10b 交付後
會紅。保留絆線（用意是逼人回來更新），但在該測試的訊息裡明寫「若你剛交付 U-10b，這是預期的，
請更新本測試的預期集合」以及「若你沒動 U-10b 而它紅了，那就是有人把 gh-aw 四支寫成可選了」。

## iteration 2 的驗證（實測輸出）

```
$ python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py                  # rc=0
82 tests, 335 checks, 0 failures

$ python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py                 # rc=0
掃描面（執行可達閉包，種子＝四支同步 workflow ＋ ci.yml）
  workflow 原始檔 8 份、composite action.yml 5 份、腳本 34 支
  解不開的呼叫目標 0 條（具名豁免 0 條）
R-1.2 代理式步驟靜態檢查：8 項檢查，0 失敗。

$ python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py               # rc=1（正確）
A-6 路徑集合關係：16 項檢查，8 失敗。

$ python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py                        # rc=0
19 項檢查，0 失敗。

$ python3 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py               # rc=0
第一段 fixture 驅動：25 項檢查，0 失敗。

$ python3 .github/actions/aidlc-sync-ci-guard/run-probe-tests.py                     # rc=0
13 項行為測試，0 失敗。
```

**A-6 的失敗集合與 iteration 2 之前逐項相同**（8 條，`IGNORE:{ui-regression,pr-reviewer,
lint-fix,contract-guard}.{md,lock.yml}`）——以 `diff` 對兩次輸出的失敗代號排序後比對，**完全
一致**。C-1 把掃描面從 20 支擴到 34 支腳本、`ci.yml` 也納進來了，**沒有讓真實 repo 多紅或少紅
任何一項**。

其餘單元套件全部重跑，皆未被波及：

```
forward   40 tests, 154 checks, 0 failures      reconcile 38 tests, 210 checks, 0 failures
reverse   39 tests, 246 checks, 0 failures      map       斷言數 2707，失敗 0
block     斷言數 550，失敗 0                     check-ci-yml 19 項檢查，0 失敗
$ python3 scripts/validate_repo_contract.py  → rc=0（passed）
$ python3 scripts/validate_env_contract.py   → rc=0（passed）
```

## iteration 2 的突變驗證

每一條都先**確認舊版對它是綠的**（reviewer 的構造，本輪逐一複現），再套用修正確認變紅，
最後把修正還原確認測試自己會紅。

| 發現 | 突變 | 修正前 | 實際紅的測試／檢查 | 是否為預期那條 |
| --- | --- | --- | --- | --- |
| **C-1** | `run: python3 scripts/decide-status.py`，該檔真的呼叫代理式 CLI | rc=0「8 項檢查，0 失敗」 | `SCRIPT-1:scripts/decide-status.py`；還原修正時 `test_a_helper_outside_the_action_dirs_is_reachable_and_scanned` 紅 | 是 |
| **C-1** | 再往下推一層（workflow → `outer.sh` → `inner.sh`） | 同上 | `SCRIPT-1:scripts/inner.sh`；`test_a_transitively_reached_helper_is_scanned` | 是 |
| **C-1** | `bash "$MYSTERY_SCRIPT"`（變數無賦值） | 靜默略過 | `REACH-1:…`；`test_an_unresolvable_invocation_target_is_red` | 是（fail-closed） |
| **M-1** | `.bash` 與無副檔名的腳本，**沒有人呼叫**、只躺在 action 目錄裡 | rc=0 | `test_scripts_are_scanned_regardless_of_suffix`（四個「沒有人呼叫」的 check） | 是 |
| **M-2** | 真正的 `subprocess.run([…])` 加進被豁免的 `check-paths-relations.py` | rc=0 | `SCRIPT-1:…/check-paths-relations.py`；`test_an_agentic_call_added_to_a_selftest_checker_is_red` ＋ `test_the_scan_exemption_is_one_pure_data_file` | 是 |
| **M-3** | 清空 `test_r5_5_no_drift_no_write` 的本體、**保留名字與 docstring** | 全綠（斷言數 154 → 151 就印在那一行） | `UPSTREAM:aidlc-sync-forward/run-orchestration-tests`（訊息列出「斷言數 151 < 基準 154」） | 是 |
| **M-4** | 拿掉 fixture 驅動 step 的 `if: always()` | 該 step 在 CI 上一次都不會執行 | `test_every_check_step_after_the_first_runs_unconditionally` | 是 |
| **M-5** | `is_sync="$(<agent> -p …)"` 注入**真實** `ci.yml` 的 probe step | R-1.2 與 `check-ci-yml.py` **兩道同時綠** | `RUN-1:ci.yml：job gate / step 2`；`test_ci_yml_is_on_the_scan_surface` | 是 |
| **M-5** | `ci.yml` 保留合法的 `docker/build-push-action@v6` | —（新增的反向斷言） | 不紅（rc=0），`test_ci_yml_third_party_actions_do_not_go_red` | 是（確認沒有製造假紅燈） |
| **M-6** | `set +e` 下移到判定邏輯之後、兩行 echo 之前（reviewer 的 V2） | **PASS（綠）** | `run-probe-tests.py` 13 項中 1 項紅 | 是 |
| **M-6** | `set +e` 移到最後一行（V1，對照組） | FAIL（紅） | 13 項中 2 項紅 | 是（原本就會紅，修完仍紅） |
| **m-1** | `aidlc-sync-map/action.yml` 參照不存在的 `aidlc-sync-ghost` | rc=0 | `LOCALREF-1:aidlc-sync-ghost`；`test_an_action_referencing_a_missing_action_is_red` | 是 |
| **m-2** | 拆字（`c=cop; d=ilot`）與 `eval` ＋ base64 | rc=0 | **仍 rc=0**，由 `test_deliberate_obfuscation_is_out_of_scope_and_says_so` 斷言「已知且已載明」 | 是（**刻意不修**，見 m-2） |
| **裁決** | 把 `run-selftest-tests.py` 的呼叫換成 `echo '# …'` 偽裝 | 第一版的文字比對被騙過 | `test_the_checkers_own_behaviour_tests_run_in_ci`（改用檢查器自己的 `invocation_targets()`） | 是 |

**兩條測試在第一次寫的時候是綠的但驗不到東西，已修正並記錄**：

1. `test_scripts_are_scanned_regardless_of_suffix` 一開始只測「被呼叫到」的路徑，而那條路
   由可達閉包負責、與副檔名無關——把副檔名改回允許清單它照樣綠。補上「沒有人呼叫、只躺在
   目錄裡」的四個 case 之後才真的釘住 M-1。
2. `test_the_checkers_own_behaviour_tests_run_in_ci` 第一版用「這一行不是以 `#` 開頭」判斷，
   被 `run: echo '# … run-selftest-tests.py'` 騙過。改用受測檢查器自己的 `invocation_targets()`
   ——它是本 repo 對「這一行真的執行了什麼」的單一真實來源。

## iteration 3 的 7 項（0 Critical／5 Major／2 Minor）

第三輪由 `aidlc-architecture-reviewer-agent` 執行，視角與前兩輪的 quality-agent 不同。它的
定性值得先記下來：**前兩輪聚焦測試機制，因此漏掉的是邊界——「這個單元實際碰到的東西，比
它的設計文件說它碰到的東西多」。** 五項 Major 之中，兩項是 iteration 2 的修正新引入的
（F1、F5），兩項是從來沒被審過的設計面（F2、F3），一項是既存漏審（F4）。

### F1（Major，新引入）— R-1.2 的掃描面比觸發 allowlist **大**，誤報會落在無關的 PR 上

iteration 2 的 C-1 把掃描面由 1 檔擴為 34 檔，其中 **11 檔不在任何 allowlist glob 內**。
reviewer 實測：在 `frontend/tests/e2e/regression.spec.ts` 尾端加一行代理式 CLI 的字面值，
R-1.2 立刻紅——但**那個路徑不匹配 allowlist 任一條，所以變紅的那個 PR 根本不會跑自我
測試**，紅燈會落在下一個改同步機制的 PR 上。這正是 `business-rules.md` R-4 逐字警告的
「一個會誤報的閘門，比沒有閘門更快失去作用」。

**這是 iteration 1 的 F7 剛關上、iteration 2 的 C-1 又打開的同一個洞**：F7 為 A-6 的九個
承載體補了 `COVERAGE-1`，但 R-1.2 的掃描面沒有等價檢查，82 條測試裡也沒有一條斷言得到它。
餘裕只有一個字元——`deploy/render-env.sh` 已有 `ANTHROPIC_BASE_URL`，
`scripts/validate_env_contract.py` 已有 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`；而
`.claude/tools/aidlc-version.ts` 在掃描面上，`CLAUDE.md` §7 又要求每次 AIDLC 升級把
upstream `dist/claude/` **整批覆蓋**進 `.claude/`。

**修法兩件，都做了：**

1. **新增 `COVERAGE-2`**（`check-paths-relations.py`）：掃描面 ⊆ allowlist ∪ `SCAN_EXEMPT`，
   失敗訊息逐一列出未涵蓋清單並給兩條修法。形狀比照既有的 `COVERAGE-1`——兩者是**同一種
   缺口的兩個方向**：COVERAGE-1 管「A-6 斷言的檔案要在 allowlist 內」，COVERAGE-2 管
   「R-1.2 掃得到的檔案要在 allowlist 內」。掃描面由受測檢查器自己算
   （新增的 `check-agentic-steps.py::scan_surface()`），**不在這裡抄第二份**。
2. **收窄 `_walk_python`，而不是把三個大目錄拉進觸發面**（採 reviewer 傾向的那一條）。
   理由：那 11 檔中有 8 檔（`.claude/tools/aidlc-version.ts`、三份 `.env.example`、
   `deploy/render-env.sh`、`frontend/tests/e2e/regression.spec.ts`、`scripts/tcms_sync.py`、
   `scripts/tcms_validate.py`）**一個都不會被執行**——它們是被三份**資料清單**提到
   （`validate_repo_contract.py` 的必要檔、`validate_env_contract.py` 的環境範本、
   `tcms_validate.py` 的 spec 路徑），不是被呼叫。把 `frontend/`、`deploy/`、`.claude/`
   拉進本單元的觸發面會讓自我測試在無關的 PR 上跑，那是另一種形式的誤報。

   收窄後 `_walk_python` 改以 `ast` 只收 **subprocess／os.exec 系列呼叫的字面 argv**
   （`SUBPROCESS_CALLEES`／`OS_EXEC_CALLEES`），並刻意對**裸名字**（`from subprocess import
   run` 之後的 `run(...)`）也放行——多收的代價只是多掃一支檔，**漏收才是缺口**。

   **不漏的驗證是實跑的**：收窄後掃描面由 34 支降為 26 支，少掉的**恰好是那 8 支資料檔**，
   三支真正由 `ci.yml` 的 `run:` 執行的（`scripts/validate_repo_contract.py`、
   `scripts/validate_env_contract.py`、`backend/scripts/dump_openapi.py`）**仍在掃描面上**，
   並已補進 allowlist——它們是真的會被執行的東西，改它們的 PR 本來就該跑一次 R-1.2。
   反向斷言 `test_a_python_subprocess_call_site_is_still_followed` 釘住「收窄的是路徑形狀的
   字面值，不是呼叫位置」。

### F2（Major，新設計問題）— 清理用 `deleteIssue`，而已宣告的憑證權限做不到

GraphQL `deleteIssue` 需要 repo **admin**；fine-grained PAT／GitHub App 的 `issues: write`
只能建立／關閉／編輯，**沒有任何權限項可以刪除 issue**。而 `security-requirements.md`
（ADR-0015 §8）宣告的憑證是「組織層 Projects 讀寫 ＋ contents write ＋ issues write ＋
PR write」。

**後果不是「清理失敗一次」，是 R-4 想防的螺旋反過來成真**：清理失敗是紅燈 ⇒ 第二段永遠
紅，且每跑一次殘留一則 item。`run-selftest-tests.py` 的
`test_cleanup_runs_on_the_failure_path` 完全看不到這件事——它只驗 `if: always()`、
「失敗是 exit 1」與「訊息含識別資訊」，不驗用的是哪一個 API。

**修法（偏最小權限，不為了保留真刪除而去要 admin）**：清理改為兩個動作——
①`PATCH repos/…/issues/N -f state=closed -f state_reason=not_planned`；
②查出該 issue 在測試 Project 上的 item 並 `deleteProjectV2Item` 移出看板。兩者都在已宣告
的權限內。**兩種失敗都各自是紅燈**；查不到 item（看板上本來就沒有）走 `::notice::` 並
exit 0——那個狀態下看板無殘留，判紅會是假紅燈。

新測試 `test_stage_2_cleanup_closes_the_issue_and_removes_the_board_item` 斷言清理路徑
**不含** `deleteIssue`、含 `state=closed` 與 `deleteProjectV2Item`。比對的是**剝掉註解之後
的本體**（用受測檢查器自己的 `strip_shell_comments`）——那段腳本的註解逐字解釋了「為什麼
不能用它」，拿原文做否定比對會把解釋判成違規。

代價已登錄：測試 issue 會以 closed 狀態留在正式 repo，每次執行一則（交還第 11 項）。

### F3（Major，新設計問題）— 測試 item 是**正式 repo 的真 issue**，且會觸發 `issue-triage` 這條 LLM 路徑

`board.sh` 的 `create_item` 走 `POST repos/${REPO_OWNER}/${REPO_NAME}/issues`，owner／name
取自 `GITHUB_REPOSITORY`。而 `domain-entities.md:61-71` 把隔離邊界**只畫在 Project 上**。

實測（2026-09-06，逐檔解析 `.github/workflows` 下每一份 `.yml`／`.lock.yml` 的觸發區塊）：
全 repo 只有 `issue-triage.lock.yml` 吃 `on.issues`（`types: [opened, reopened]`）⇒
**每次第二段 dispatch 都會在正式 repo 開一則 issue 並立刻啟動一支 gh-aw（LLM 驅動）
workflow 去分類它**，而清理與那次 triage run 互相競賽。這落在 `project.md` 逐字點名的三塊
結構性盲區的第一塊（所有 LLM 路徑），而 U-9 的整個設計論證是「不把不確定性放進驗證層」。

**本輪不自行選定方案**（專用測試 repo vs. 把 selftest 的 issue 排除在 issue-triage 之外，
是範圍決定，屬 Bolt 0 gate 與憑證鑄造一起裁）。做的是兩件：①在 `aidlc-sync-selftest.yml`
的建立 step 逐字加註上面三點；②併入交還清單第 10 項，**並寫明它不只是一個 Project**——
`domain-entities.md:71` 已登錄「Bolt 4 前必須確認的外部依賴」，本項更正的是它的**範圍**。
上游 artifact 不回改。

### F4（Major，既存漏審）— A-5 的承接方式被靜默換掉，換成的那一種正好在剛失敗過的維度上較弱

`domain-entities.md:15`／`:28` 逐字指定 U-9 自己「**注入一次必然失敗的 PR 建立呼叫**，
斷言 (1) 分支被刪除、(2) 該次執行紅燈且訊息含 intent id 與分支名」。實作改為**轉呼** U-8
的測試並比對兩條具名測試。

轉呼的「單一真實來源」理由對**產品程式**成立，對**獨立驗證層**是類別錯誤：本單元交付的是
「機制壞了會有人知道」，而知識來源若完全等於受測單元自己的測試，A-2／A-4／A-5 的**獨立
偵測力是零**，只剩下防「刪除」與「掏空」。

**這在本 intent 內已實證**：U-8 的孤兒分支那一支曾有**三條假斷言**，而同期 U-9 全綠且
CI log 逐字印「承接：A-4…；A-5：PR 開不成的三種結局」。下限與具名證據擋得住刪與掏空，
**擋不住寫錯**。

**處置**：把偏離登進交還清單（第 9 項），並把**偵測力邊界逐字寫進
`run-selftest-fixtures.py` 的模組說明**（一張三列的對照表：刪掉／清空本體／斷言寫錯，
第三列是「偵測不到」）。「要不要改成規格指定的注入」要改 `domain-entities.md:28`，屬 Bolt
gate 的裁決——**登錄不處置**。

**兩處可機械查證的假宣稱一併修掉**：
- `run-selftest-fixtures.py` 的模組說明宣稱這項偏離「已記入交還報告」，而交還清單裡沒有
  它 ⇒ 本輪真的寫進去了（第 9 項），並把那段說明重寫成兩處偏離逐條列出。
- `aidlc-sync-selftest.yml` 宣稱「每個 job 各 10 分鐘、最壞 20 分鐘……已列入交還 Bolt 4
  gate 的清單」，而 `code-summary.md` grep `20 分鐘`／`workflow 層` 零命中 ⇒ 那句話補上具體
  落點（交還第 4 項），該項本身也補上 workflow 層無 `timeout-minutes` 這件事。

### F5（Major，新引入）— `code-summary.md` 對它所描述的程式已過期，其中一個數字是 gate 決策的輸入

本檔 iteration 2 的 mtime 早於三支腳本最後一次被改的時間，八處對不上。**最要緊的是計時**：
交還第 4 項把 92.78 s 交給 Bolt 4 gate 當「10 分鐘上界的複核基準」，而該計時**完全沒有計入
同一份文件自述本輪新加的 step 7**，也沒有計入 reverse 套件由 39／246 成長到 46／308。

**處置**：本輪的全部程式改動完成之後才重測並回寫——交付表、測試規模、上游基準表、驗證
輸出、計時表（**四個步驟都計**）全部重出；交還第 3、7 項改寫（兩者都已解決，狀態相反於
交還當時的記載）；第 8 項更正為 iteration 2 之後的實際豁免（一份 `.json`，不是三檔 `.py`）。

這是本 intent 第 N 次「可算的數字沒先算」型失誤，而它這次的代價比前幾次高：**一個假的
複核基準會讓 gate 以為餘裕比實際大**。

### F6（Minor，既存漏審）— 六支轉呼與兩處抽出腳本的執行皆無 `timeout=`

本 repo 已有這個形狀的實例（reviewer 注入代理式 CLI 之後測試掛住直到 `pkill`），而
`run-selftest-tests.py` 那一處正是以**真實 shell** 執行從 workflow 抽出來的腳本、並餵假
`gh`。job 的 `timeout-minutes: 10` 是有效上界，但失敗訊息會是「job timed out」而不是
「driver X 掛住」，而診斷成本高的閘門會被當成雜訊。

**修法**：六處 subprocess 全部帶 `timeout=`（`DRIVER_TIMEOUT_S = 300`、
`SHELL_TIMEOUT_S = 60`、`CHECKER_TIMEOUT_S = 180`，數值取自實測留餘裕），逾時一律走
**`EXTERNAL-ERROR`（exit 2）而不是斷言失敗（exit 1）**——`reliability-requirements.md` 的
三值退出慣例——並在訊息裡**指名是哪一支**。上界不是效能目標，正常路徑碰不到它。

`test_every_subprocess_call_in_the_selftest_scripts_has_a_timeout` 以 `ast` 逐一找出兩支檔
內每個 `subprocess.*` 呼叫並斷言帶 `timeout=`，所以下一個新增的呼叫漏帶也會紅。

### F7（Minor，新設計問題）— 報告抬頭說「執行可達閉包」，而其中一部分從未被執行

`check-agentic-steps.py` 的報告把三種來路平鋪成一張表，抬頭寫「執行可達閉包……腳本 34
支」，於是 fail-closed 的論證看起來適用於全部 34 支。實際上只適用於 shell 呼叫位置那一區。

**修法**：報告分三區印，各自標明計數與 fail-closed 與否——
①**執行可達 · shell 呼叫位置**（解不開即 `REACH-1` 紅，fail-closed）；
②**執行可達 · Python subprocess argv 位置**（best-effort，解不開不判紅）；
③**同步機制自有目錄全掃**（不經呼叫位置，未必會被執行）。
另補印「解不開語法的 `.py`」與「讀不到內容的檔」兩行——它們原本靜默累積在
`self.unreadable` 裡而從不出現在報告上。

與 F1 的修法互相影響，已一起想：收窄之後②區對真實 repo 是**空的**（`ci.yml` 先以 shell
位置帶進了那三支），報告照樣印「（無）」而不是隱藏該區——隱藏會讓下一個人以為沒有這一區。

## 交還 Bolt gate 的清單

| # | 項目 | 落點 | 指派 |
| --- | --- | --- | --- |
| 1 | **`security-requirements.md` 的 ADR-0006 四面向表沒有處理「以 `pull_request` 執行 PR head 腳本並餵高權限憑證」這一面**（IAM 欄只指向缺口 Q-1 的 403）。本輪已把第二段收窄為手動觸發；**要放寬回 `pull_request` 必須連同這一項一起裁決** | `U-9/nfr-requirements/security-requirements.md` | **Bolt 0 gate** |
| 2 | `functional-design` 四處仍寫「解析編譯後的 `.lock.yml`」／allowlist 涵蓋 `.md`／`.lock.yml`（`business-rules.md:25`、`:29`；`business-logic-model.md:22`、`:83`），與 `nfr-requirements` 的更正版矛盾。實作依更正版，並由 `LOCK-1` 與 allowlist 測試釘住 | `open-items.md` 的 `N:C-3` | **Bolt 1 gate**（原定期限） |
| 3 | ~~A-6 對真實 repo 現為紅（8 項）~~ → **已解決**：U-10b 已交付，四支 gh-aw 的 `.md` 與 `.lock.yml` 都有 `paths-ignore`，A-6 現為 **17 項全通過**（本輪重跑實測）。`test_the_real_repo_state_is_what_we_say_it_is` 的預期值已翻面並改為逐項比對**通過**的代號集合，所以「把檢查刪掉來轉綠」也會紅 | `check-paths-relations.py` | 已關閉 |
| 4 | 第一段實測 **92.78 s**（本機），成本主體是六支上游驅動而非 fixture 數，與 `scalability-requirements.md:25` 的推論前提不符；`performance-requirements.md` 的 10 分鐘上界是估計值 | 本檔「第一段的實測耗時」 | **Bolt 4 gate**（10 分鐘複核） |
| 5 | **PyYAML 在 GitHub runner 上可用、以及 `actions/setup-python@v5` 這條路真的能裝起來——本 session 無法實測**（沒有 CI 觸發）。如實記載為未驗證 | `aidlc-sync-selftest.yml` 第一段 | Bolt 4 首次真實執行 |
| 6 | **第二段從未被執行過**。本輪把它從「零覆蓋」提升為「抽出腳本 ＋ 假 `gh`／假 `board.sh` 的行為測試」，但**仍然沒有任何一次真實的看板往返**。完成判準第 3 條（憑證範圍外寫入回 403）在組織層授權下恆不發生，落點待裁決 | `security-requirements.md` 缺口 Q-1 | **Bolt 0 gate** |
| 7 | ~~`run-selftest-tests.py` 本身沒有被任何 workflow 執行~~ → **已解決**：iteration 2 的範圍裁決把它接進第一段的 step 7（`aidlc-sync-selftest.yml`，由 `test_the_checkers_own_behaviour_tests_run_in_ci` 以檢查器自己的 `invocation_targets()` 釘住）。目前是 **89 條**行為測試，不是交還當時寫的 69 條。它加進第一段的耗時已計入下方的計時表 | `aidlc-sync-selftest.yml` 第一段 | 已關閉（成本併入第 4 項） |
| 8 | 掃描面唯一的豁免是**一份純資料檔**（`agentic-tokens.json`），不是 iteration 1 交還時寫的「`VOCABULARY_OWNERS` 三檔」——iteration 2 的 M-2 已把三支 `.py` 全部放回掃描面（含 `check-agentic-steps.py` 自己）。集合大小由 `test_the_scan_exemption_is_one_pure_data_file` 釘住 | `check-agentic-steps.py` | 記錄，非待辦 |
| 9 | **A-4／A-5 的承接方式是「轉呼上游測試」，不是 `domain-entities.md:15`／`:28` 逐字指定的「注入一次必然失敗的 PR 建立呼叫」**（iteration 3 的 F4）。偵測力**不相等**，邊界逐字寫在 `run-selftest-fixtures.py` 的模組說明：轉呼＋具名證據＋斷言數下限偵測得到「刪掉那幾條」與「留著名字清空本體」，**偵測不到「斷言寫錯」**——而本 intent 內已實證那正是會發生的事（U-8 的孤兒分支那一支曾有三條假斷言，同期 U-9 全綠且 CI log 逐字宣稱承接了 A-5）。轉呼的「單一真實來源」理由對產品程式成立，對**獨立驗證層**是類別錯誤。**要不要改成規格指定的注入要改 `domain-entities.md:28`（已通過 reviewer 的上游產出），不由本單元自行決定**——本輪只登錄與寫明邊界 | `functional-design/domain-entities.md:15`、`:28`；`run-selftest-fixtures.py` 模組說明 | **Bolt gate** |
| 10 | **測試 item 的載體是正式 repo（`opendiamonds/cloud-360`）的真 issue，不只是一個獨立的 Project**（iteration 3 的 F3）。`board.sh` 的 `create_item` 走 `POST repos/${REPO_OWNER}/${REPO_NAME}/issues`，owner／name 取自 `GITHUB_REPOSITORY`；而全 repo 只有 `issue-triage.lock.yml` 吃 `on.issues`（`types: [opened, reopened]`，2026-09-06 逐檔解析全部 workflow，命中僅此一支）⇒ **每次第二段執行都會在正式 repo 開一則 issue 並立刻啟動一支 gh-aw（LLM 驅動）workflow 去分類它**，清理與那次 triage run 互相競賽。這落在 `project.md` 逐字點名的三塊結構性盲區的第一塊（所有 LLM 路徑），而本單元的整個設計論證是「不把不確定性放進驗證層」。**本輪不自行選定方案**（專用測試 repo vs. 把 selftest 的 issue 排除在 issue-triage 之外，是範圍決定）；已在 `aidlc-sync-selftest.yml` 的建立 step 逐字加註。這一項**併入 `domain-entities.md:71` 已登錄的「Bolt 4 前必須確認的外部依賴」**，並更正該項的範圍：要確認的不只是一個 Project | `functional-design/domain-entities.md:61-71`；`aidlc-sync-selftest.yml` 建立 step | **Bolt 0 gate**（與憑證鑄造一起裁） |
| 11 | **第二段的清理改為「關閉 issue ＋ `deleteProjectV2Item` 移出測試看板」**（iteration 3 的 F2）。原本的 GraphQL `deleteIssue` 需要 repo **admin**，而已宣告的憑證權限（ADR-0015 §8）只到 `issues: write`——那個呼叫在正式憑證下必然失敗，而清理失敗是紅燈 ⇒ 第二段永遠紅且每跑一次殘留一則 item。**沒有為了保留真刪除而去要 admin**；代價是測試 issue 會以 closed 狀態留在正式 repo（每次執行一則），這一點要在鑄造憑證時一併看過 | `aidlc-sync-selftest.yml` 清理 step；`security-requirements.md` | **Bolt 0 gate** |

## 未完成項目（誠實列出）

1. **完成判準①（把映射改壞 ⇒ CI 紅燈且輸出指出預期與實得）**：機制由突變驗證證實（M2／M4 等），但「CI 紅燈」本身需要真實 PR 觸發，本 session 不在授權內。
2. **完成判準②（把判定搬進 agent step ⇒ 靜態檢查失敗）**：由 M1a／M1b／M1c 與四條繞過測試證實，且本輪把它從「只看得到 workflow 檔」擴為三個掃描面。這一條**現在才真的成立**——修正前它對本 repo 五份 composite action 與 20 支腳本完全看不見。
3. **完成判準③（憑證做範圍外寫入 ⇒ 403）**：仍只有 stub 證據，見交還清單第 6 項。
4. 未 commit、未 push、未開 PR、未建立任何 secret、未寫入任何真實看板（本輪授權邊界）。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-06T05:37:01Z
**Iteration:** 4

### 驗證方法

本輪未只讀文件——對本單元交付的全部四支腳本與 workflow 逐一實測（`python3` 直接執行、
`wc -l`），並對 iteration 3 的 F1／F2／F4／F9（M9）四項做了**活體突變測試**：把整個
repo（不含 `.git`）rsync 到 scratchpad 副本，在副本上實際改壞被保護的行為，重跑
`run-selftest-tests.py`，確認對應測試真的轉紅，再還原確認轉綠——不是重讀 code-summary
的敘述就採信。副本已於審查結束後刪除，未修改、未 commit、未 push 任何檔案。

### Findings

| # | Severity | 分類 | Location | Finding | Recommendation |
|---|---|---|---|---|---|
| 1 | Minor | 新設計問題 | `code-summary.md` 第 141-171 行「## 驗證（實測輸出）」 | F5 逐字宣稱本輪「驗證輸出……全部重出」，但檔內只有兩個帶編號的驗證區塊（「## 驗證（實測輸出）」與「## iteration 2 的驗證（實測輸出）」），沒有對稱的「## iteration 3 的驗證（實測輸出）」。第一個區塊仍凍結著 iteration 1 尾聲的數字（`69 tests, 287 checks`、掃描面「20 支腳本」、A-6「16 項檢查，8 失敗」）——這些數字在 iteration 2 的 C-1（34 支）與 iteration 3 的 F1（26 支）之後都已經不是目前的狀態，只是因為它排在「## iteration 2 的驗證」之前，讀者要靠位置推斷它是舊快照，而不是靠標題。F5 本身要修的正是「文件對它所描述的程式已過期」這一類問題，這裡是同一種形狀的殘留，只是換了一個位置。**本欄以外的每一個可覆核數字（行數、測試數、六支上游驅動的 tests／checks、A-6 現況 17/0、掃描面 8+5+26=39）都經本輪直接執行覆核，全部與文件相符**，所以這不是資料錯誤，是敘事結構少了一段。 | 補一個「## iteration 3 的驗證（實測輸出）」區塊，貼上目前的 `89 tests, 368 checks, 0 failures`／掃描面 8+5+26＝39／A-6 17/0 等實際輸出；並把第 141 行的標題改成「## iteration 1 的驗證（實測輸出）」以消除「哪一輪」要靠位置推斷的問題。非 blocking：不影響任何已交付行為的正確性。 |

### 對 iteration 3 七項的逐項複核（0 Critical／5 Major／2 Minor，全部核實為已解決，本輪皆為既存漏審或新設計問題的登錄，非新引入）

| # | 嚴重度 | 複核結果 | 證據 |
|---|---|---|---|
| F1 | Major | **成立，已解決** | 實測真實 repo：`check-agentic-steps.py` 掃描面＝8 份 workflow ＋5 份 `action.yml` ＋26 支腳本（① shell 呼叫位置 12、② python subprocess argv 位置 0、③ 自有目錄全掃 14），與收窄前的 34 支相差 8（code-summary 宣稱的差值一致）。`check-paths-relations.py` 的 `COVERAGE-2` 對真實 repo 通過（「涵蓋 R-1.2 掃描面的全部 39 個檔案」）。合成測試 `test_a_python_subprocess_call_site_is_still_followed`（收窄不得漏掉真呼叫）與 `test_a_scanned_file_outside_the_allowlist_is_red`（COVERAGE-2 的突變面）皆存在且通過。 |
| F2 | Major | **成立，已解決** | 讀 `aidlc-sync-selftest.yml` 清理 step（第 531-599 行）：確認不含 `deleteIssue`，含 `PATCH … -f state=closed` 與 `deleteProjectV2Item`。**活體突變測試**：在 scratchpad 副本把清理腳本改回 `deleteIssue`（保留原有註解不動），重跑 `run-selftest-tests.py`，`test_stage_2_cleanup_closes_the_issue_and_removes_the_board_item` 從 `[ok]` 轉為 `[FAIL]`（總失敗數由 1→4，多出的 3 個含此測試）；還原後重新轉綠。 |
| F3 | Major | **成立，如實揭露** | 獨立查證（不依賴 code-summary 的陳述）：對 `.github/workflows/*.yml` 逐檔解析 `on:` 區塊，全 repo 僅 `issue-triage.lock.yml` 在 `on.issues.types` 含 `[opened, reopened]`；其餘含 `issues:` 字樣的命中全部是 `permissions.issues: write/read`，非觸發器。`board.sh` 的 `create_item` 確實打 `POST repos/${GITHUB_REPOSITORY}/issues`（workflow 第 350、384-399 行引用一致）。本輪未自行選定解法（專用 repo vs. triage 排除），正確地留給 Bolt 0 gate；第二段已收窄為僅 `workflow_dispatch`，不會自動發生。 |
| F4 | Major | **成立，如實揭露，非過度謹慎** | `run-selftest-fixtures.py` 模組說明的三列偵測力邊界表（刪除／清空本體／斷言寫錯）與 code-summary 逐字相符；「登錄不處置、指派 `domain-entities.md:28` 的 Bolt gate」的處置形狀符合 `project.md` 的既有教訓（發現已核可上游的契約缺口時標出缺口、不逕改上游）。 |
| F5 | Major | **部分成立，見上方新 Minor #1** | 交付表、測試規模、上游基準表（`aidlc-sync-reverse` 46/308）、計時表（四步驟）皆已重出且與本輪實測一致；唯獨立的「iteration 3 驗證輸出」轉錄段落缺席，第 141 行的舊區塊未被觸碰或重新標題。 |
| F6 | Minor | **成立，已解決** | `run-selftest-fixtures.py`／`run-selftest-tests.py` 內的 subprocess 呼叫皆帶 `timeout=`（`DRIVER_TIMEOUT_S`／`SHELL_TIMEOUT_S`／`CHECKER_TIMEOUT_S`），且有 `test_every_subprocess_call_in_the_selftest_scripts_has_a_timeout` 以 `ast` 逐一核對。 |
| F7 | Minor | **成立，已解決** | 實測 `check-agentic-steps.py` 的報告確實分三區列印（①②③標題與計數），`test_the_scan_report_separates_reachable_scripts_from_directory_seeds` 對真實 repo 斷言分區計數相加等於總數且③區非空，本輪重跑通過。 |

### 額外覆核（超出 iteration 3 清單，本輪主動查證）

- **可計算的數字**：行數（599/1434/554/696/2507/54，`wc -l` 全數相符）、測試規模（89 tests／368 checks，直接執行相符）、六支上游驅動的 tests／checks（map 38／2707、block 34／550、forward 40／154、reverse 46／308、ci-guard check 19、probe 13，全數直接執行相符）、A-6 現況（17 項全通過，直接執行相符，印證「交還 Bolt gate 清單」第 3 項「已解決」的宣稱）。**未發現任何一個對不上的數字。**
- **絆線可達性**：`test_the_real_repo_state_is_what_we_say_it_is` 以**通過代號集合的逐一相等**（非計數比對）鎖住 A-6 現況，且刻意不從受測的同一個 `GH_AW_CARRIERS` 常數產生期望集合（避免「兩邊一起縮水」的假陽性）——讀原始碼確認此設計成立。
- **SEC-3 守衛**：`016`／` 16`／`16 `／`0016`／`+16` 五種等價寫法與空字串／不可解析值的正反向測試皆存在（`test_sec3_refuses_the_production_board_in_every_normalised_form`），比對邏輯確為 `int()` 正規化而非字串比對或 bash 算術（`$((016))` 為八進位的陷阱有專屬前提斷言）。
- **`_bash` 對齊 CI 語意（M9）**：活體突變測試——把測試 harness 的 `["bash", "-e", "-c", script]` 改回 `["bash", "-c", script]`，重跑後 `test_the_step_harness_matches_githubs_default_shell` 轉紅（多出 2 項失敗）；還原後轉綠。證實這條測試不是裝飾性斷言。
- **零 TODO／FIXME／HACK／XXX**：本單元交付的 workflow 與四支腳本內無殘留標記，符合 `team.md` 既有紀律。
- **未逾越授權**：全程唯讀＋副本操作，未 commit／push／開 PR／建立 secret／寫入任何真實看板；stage 2 端到端測試全數以假 `gh`／假 `board.sh` 驅動，未觸發任何真實網路呼叫。

### Summary

iteration 3 的七項發現（F1-F7）逐一以直接執行、原始碼核對與活體突變測試複核，全部confirmed 為真實已解決，且四項可用突變驗證的（F1、F2、F6、對應的既有 M9）在本輪重新製造迴歸後都確實讓對應測試轉紅——這些不是裝飾性斷言。本單元交付物的每一個可計算數字（行數、測試數、六支上游驅動的計數、A-6 現況）皆與實測相符，沒有發現「數字沒先算」或「文件與程式脫鉤」的新例——除了一處：F5 宣稱「驗證輸出全部重出」，但檔內缺一個對稱的「iteration 3 的驗證（實測輸出）」轉錄區塊，第 141 行仍是 iteration 1 尾聲的舊快照且未被重新標題。這是本輪唯一的新發現，屬 Minor、不影響任何已交付行為的正確性，不阻擋 READY。三塊未驗證項（憑證 403、PyYAML on runner、第二段真實看板往返）皆如實記載為 stub／待 Bolt 0-4 gate，未被誇大為已驗證。
