# Code Summary — U-8 反向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service
     Generated: 2026-09-05T18:27:04Z（讀自 date -u） -->

## 交付物

**本表的每一格都在 2026-09-06T02:40:30Z 由 `wc -l` 重新量測**，理由見下方「修訂 2」。

| 檔案 | 行數（`wc -l`） |
| --- | --- |
| `.github/workflows/aidlc-sync-reverse-impl.yml` | **778** |
| `.github/workflows/aidlc-sync-reverse.yml` | **102** |
| `.github/actions/aidlc-sync-reverse/run-reverse-tests.py` | **2055** |

## 驗證（orchestrator 自行重跑）

| 項目 | 結果 | 取得方式 |
| --- | --- | --- |
| 行為測試 | **46 tests, 308 checks, 0 failures** | 實跑 `run-reverse-tests.py` 的收尾行 |
| 突變驗證 | 交付當時 **21 條**；reviewer 對抗式 **76 條**（18 條存活、其中 14 條為真實未覆蓋）；本輪修正後複驗 **18 條全數 killed** | 見下方「修訂 1」的突變表 |
| 兩支 contract validator | 皆 passed | 實跑 `validate_repo_contract.py`／`validate_env_contract.py`，rc=0 |
| U-9 第一段驅動 | passed（`46 tests、308 項斷言、0 失敗`，三條具名證據齊全） | 實跑 `run-selftest-fixtures.py`，rc=0 |
| `ci.yml` | `git diff --numstat` 為 **`125 0`**（本單元未觸及它；該數字是本分支較早單元累積的新增行數） | 實跑 `git diff --numstat -- .github/workflows/ci.yml` |
| 未動用真實 API／未 commit／未開 PR／未碰 #16 #23 | 是 | 全部 `gh`／`git` 呼叫都經 PATH shim，未預期子命令一律 exit 9 |

**Q1=A 已落地**（`impl:237`）：`REVERSE_PR_LABEL` 以 `sed` 從 U-6 的 `forward-impl:174` 推導，取不到即 fail-closed 中止。全 repo 維持**恰好一份字面**。

## **orchestrator 的計畫失誤（必須先講）**

**已核可計畫的「查證 1」聲稱盤點了 `open-items.md`，但只列了四項**（C-7.1／C-7.2／M-7.1／M-7.2＋#11）。實際上該檔有 **222 行**，項目橫跨 `A:`／`B:`／`N:`／`C-`／`M-`／`m-` 六種前綴——我的掃描用 `grep -E "^\\| \\*?\\*?[CM]-"`，**結構上就撿不到 `N:` 與 `A:`／`B:` 前綴的項目**。

**直接後果**：計畫 Step 10 寫「concurrency 自成一組」，而 **`N:C-2`（Critical）** 逐字說那正是 U-8 設計「**逕自裁定**、推翻已過 gate 的 `services.md:58`」的東西，處置為「**需 ADR 或回退**」。**我的計畫把一個未經核可的裁定寫成了指示。**

**實作者拒絕照做並選擇回退，這是對的**。orchestrator 追認：

| | 論證 | 強度 |
| --- | --- | --- |
| `services.md:58`（已過 gate） | 「與 S-B 同一組……**都碰 record，不應並行**」 | **正確性** |
| U-8 設計的第三組主張 | 「共用一組會讓其中一個延後而無實益」 | 便利性 |

正確性論證勝出，且 ADR-0015／0016 全文對反向同步 concurrency **零命中**（即「需 ADR」那一條沒有被滿足）。**已實測落地**：`reverse.yml:67` 與 `reconcile.yml:35` 同為 `aidlc-sync-reconcile-${{ github.repository }}`。

**這是同一個教訓的第三次**（U-7 兩次、本輪一次），且這次升級了——前兩次是漏讀，這次是**漏讀之後把錯的東西寫成了計畫指示**。

## 待 Bolt gate 追認

| # | 項目 |
| --- | --- |
| **(a)** | **Q1 的代價**：`REVERSE_PR_LABEL` 的真實來源落在**消費者**（U-6）而非**產生者**（U-8）。維持一份字面，但 U-6 那一行成為三支 workflow 的共同相依——刪掉它會讓 U-7 與 U-8 同時 fail-closed 中止（不靜默）。已有測試鎖住「本單元不得自抄字面」 |
| **(b)** | **N:C-2 已依「回退」處置**（見上）。若 gate 認為第三組才對，需補 ADR |
| **(c)** | **R-4c 列了兩個本單元結構上無法呼叫的方法**（`parse`／`content_hash`）：`read_item` 回的 `ItemState` 只有五欄、**不含 issue body**（`board.sh:559-563` 的零筆分支與 `:566-571` 的正常分支，兩處各 emit 同一組五欄，本輪重新開檔核對），沒有 body 就沒有東西可 parse；雜湊由 `board.sh` 內部呼叫 `block.sh` 算好。**這不是缺陷而是 ADR-0015 §10 等價不變式所要求的唯一形狀**，但 R-4c 的表格會讓下一個實作者去找一條不存在的呼叫。落點：Bolt 3 gate 更正該表 |
| **(d)** | **R-1 群沒有區分「儲存值為 null」與「儲存值不同」**。前者可達（U-6 回寫遺失，或 U-7 的修復推在 `aidlc-sync/reconcile/*` 而**該分支無合併回 `ut` 的路徑**——即 U-7 交還的缺口 (3)），依字面會被判為人為變更並開 PR。**照字面實作、不自創第三條規則**（`functional-design:c10`）。實務界限是 R-6.1（同 intent 至多一則開啟中 PR，不會每天增生） |
| **(e)** | **N:M-5／N:M-4(B) 已過期**：U-8 的 `performance-requirements.md`／`reliability-requirements.md` 各有一處要求「以編譯後的 `.lock.yml` 複驗」「取決於 gh-aw safe-outputs 語意」——本單元是**純 Actions，沒有 `.lock.yml`、沒有 gh-aw**。不照它們做，記載 |
| **(f)** | **U-5 的 `FailureIdentity` 鍵不含發動的 workflow**：本單元開的通報 issue 會被 U-6／U-7 的 `resolve_if_open` 在處理同一 intent 成功時關掉。U-5 既有的鍵設計，U-6 與 U-7 之間早已有同樣交互 |
| **(g)** | **label 冪等建立（上游未規定）**：repo 目前**沒有** `aidlc-sync-reverse` 這個 label，而 `gh pr create --label` 對不存在的 label 會失敗 ⇒ 會把**每一次真實人為改動**都推進 R-6.3 的刪分支路徑（症狀：每天紅燈但永遠開不出 PR）。沿用 U-5 的 Plan Approval 裁決 3 先例做冪等建立，整輪只做一次 |

## 對計畫的偏離（四項）

1. **Step 10 的 concurrency**——見上，**實作者的偏離是對的，錯的是計畫**。
2. **Step 1 的 inputs 六個而非「沿用 U-7 那一組」**：略去 `reconcile_batch_size`（`scalability-requirements.md` 逐字「本站不自行補一個數字」）、`whitelist` 與 `field_max_length`（本單元不呼叫 `map.sh`）；新增 `reverse_branch_prefix`。
3. **Step 9 只實作 `notify`、不實作 `resolve_if_open`**：依 `open-items.md` 的 **B:M-3**（Major，落點 code-generation）逐字裁定。
4. **無 live 測試**：需開真實 PR（public repo，編號永久），brief 明文禁止。

## 一項值得單獨記的測試發現（實作者自行抓到）

突變 **M19**（PR 內文拿掉「關閉」路徑）**第一次跑出全綠**——原斷言寫成 `"關閉" in body and "覆寫" in body`，而內文另一處引用 [req:FR-G3] 的原文（「直到對應 PR 被合併**或關閉**」）也含這兩個字，所以把條目標題改成「暫緩」測試照樣通過。

已改成抽出 `- **…**：` 條目、要求恰為「合併」與「關閉（不合併）」兩條、且關閉那一條的**同一行**要說出「恢復覆寫」與「被輾回」。重跑 M19 只有該條紅。

**這是本 intent 反覆出現的「斷言看起來在守、實際守不到」在字串比對上的變體**——實作者自己抓到，未等 reviewer。

## 未完成項目（誠實列出）

1. **`Pull requests: write` 從未被實測**（ADR-0016 Consequences 逐字，並說「若要補，落點為 Bolt 3（U-8）開工前」——**至今未做**）。本單元每一條 PR 路徑都只對 stub 驗證過。**這是 Bolt 3 上線第一個會爆的地方**，症狀由 R-6.3 承接（當場紅燈 ＋ 通報 ＋ 刪分支），不是靜默失效。
2. **Q3=A 的反例只是 stub**：證明的是「從 PR 的 `files` 推導 intent id 的 jq 邏輯正確」，證明不了「GitHub 真的會在 `--json files` 回這些路徑」「U-6 讀同一份資料得到同一集合」「U-10b 的排除真的生效」。**CAP-11 的『未實測』不因此消除**，測試註解已逐字寫明。
3. **U-8 ＋ U-10b 的真捆綁未解**：U-10b 未上線前，每則反向 PR 都送進含 **6 次 LLM agent 執行**的完整 gauntlet（R-5）。
4. **`aidlc-sync/reverse/*` 分支的清理無人負責**：PR 合併或關閉後 GitHub 是否自動刪分支取決於 repo 設定（未查證），也沒有任何已核可規則說誰刪。只有 R-6.3 的失敗路徑會刪。
5. **`tcms-test-cases` stage 仍未執行**（`project.md ## Mandated` 對本 intent 是 blocking）。

## Review (code-generation)

**Status:** 對抗式 reviewer 判 **NOT-READY**（1 Critical／4 Major／6 Minor；76 條突變、18 條存活、其中 14 條為真實的未覆蓋行為）。**全部已修**，見下方兩段修訂。

---

## 修訂 1（2026-09-06T02:40:30Z）：reviewer 的 NOT-READY 逐項處置

### Critical — R-6.1 的查詢參數幾乎完全沒有斷言

`gh pr list` 是本單元**唯一**的防重複開 PR 連鎖，而三條各只改一個 token 的突變讓它整條失效、當時 39 條測試全綠。

**根因是 harness 而不是覆蓋範圍**：`gh` 的 `pr list` shim **完全不看 argv**，無條件回一份固定 JSON；全套只有一條 argv 斷言（`--state open`）。而 `test_q1_…` 的 `'--label "$REVERSE_PR_LABEL"' in CODE` 檢查**被 `gh pr create` 那一處滿足**（該字串在 impl 出現兩次），所以拿掉 `pr list` 那一處仍通過——**文字斷言在錯的粒度上比對**。

處置（一次殺掉三條）：

1. `pr list` 的 shim 改為**依 argv 產生回應**：照 `--label` 過濾、照 `--state` 過濾、**遵守 `--json` 的欄位清單**（要求 `number` 時不吐 `files`），且沒有 `--json` 時輸出表格而非 JSON（與真實 `gh` 同語意，讓下游 `jq` 解析失敗）。
2. 新增 `test_r6_1_query_argv_is_complete`：對**那一次呼叫的 argv** 斷言 `--repo`／`--label`／`--state open`／`--json` 含 `files` 與 `number`，並要求每個旗標恰出現一次。**斷言的對象是 argv，不是 impl 的原始碼文字**——後者分不出兩個呼叫點。
3. 新增 `test_r6_1_only_labelled_prs_suppress`：一則碰到同一個 `sync-state.json` 的**人為** PR（無反向 label）不得抑制反向同步。
4. `test_q1_…` 的文字斷言改為 `CODE.count('--label "$REVERSE_PR_LABEL"') == 2`（兩個呼叫點），並在註解寫明真正的守衛是行為層的 argv 斷言。

### Major 1 — A-5 的「附 intent id 與分支名」在孤兒結局有一半是假的

三個存活突變，**三個都是斷言形狀的問題而不是覆蓋範圍的問題**：

- **stub 替受測程式作答**：`git push --delete` 的模擬失敗訊息含分支名，於是「通報 detail 含分支名」是被 stub 自己餵的。改成不含分支名的認證失敗（`GIT_DELETE_FAIL_MSG`），並在測試裡加一條**前提斷言**確認該訊息不含分支名／intent id，讓這個縫不會再被無聲地打開。
- **第三種結局沒有 `AIDLC_INTENT_ID` 斷言**（第二種有）。已補。
- **包含關係吞掉斷言**：孤兒清單原本斷言「含 intent id **且**含分支名」，而分支名構造上就是 `<prefix>/<intent_id>-<date>`，前半**不可能獨立失敗**。已改為逐字相等 `<intent_id> (<branch>)`。

### Major 2 — [Q3=A] 的反例帶了一個裝飾性輸入

`extra_paths=("README.md",)` 是為了驗 record_root 過濾而放的雜訊，但**沒有任何斷言讀得到它的差別**。已新增 `Round.open_reverse()`（解析腳本自己印出的抑制集合）並斷言該集合**恰為** `{X}`。

### Major 3 — 本檔每個標題數字都錯

原表的 743／1617／38 tests／237 checks／`impl:219`／`forward-impl:157`／`ci.yml 103 0` **全部**剛好差 F5 修正的量（impl +18、test +46、+1 test、+9 checks）——**屬交付後的修正沒有回寫**，不是原本就寫錯。已全部重量測並在表上加註取得方式；本次連 `board.sh` 的行號引用也重新開檔核對。

### Major 4 — `impl` 對 U-6 防線②的機制宣稱可被一行指令推翻

原文寫「反向 PR 合併進 `ut` 後，U-6 的防線②會 skip 那一輪」。實際上防線②讀的是 `git log -1 --format=%B HEAD`，命中與否取決於該事件 checkout 的是哪一個 commit：

- `pull_request`（含 closed）：U-6 checkout `github.event.pull_request.head.sha`，即本反向分支的頂端 commit——**帶標記，命中**。
- `push` 到 `ut`：HEAD 是合併產生的 commit。它帶不帶標記**不由本檔決定**，而由 repo 的合併訊息設定決定，**而那個設定不在版控裡**：查詢當下 merge commit 為 `MERGE_MESSAGE` ＋ PR 標題（**不含**標記），squash 為 `COMMIT_OR_PR_TITLE` ＋ `COMMIT_MESSAGES`（內文含本分支的 commit 訊息，故**含**標記）。

**這裡對 reviewer 的建議有一處偏離並已查證**：reviewer 寫「merge commit 與 squash commit 都不帶 `SYNC_MARKER`」，而以唯讀 `gh api repos/<owner>/<repo>` 查該 repo 的合併訊息設定後，**squash 的情形不成立**（`squash_merge_commit_message=COMMIT_MESSAGES`）。註解因此寫成上面這個逐事件、逐設定的形狀，而不是照抄那句話——照抄會把一個錯的宣稱換成另一個錯的宣稱。**行為結論不變**：兩種都是已核可的行為（R-3.3 明訂合併**或關閉**後恢復覆寫），本單元不依賴哪一種。

### Minor（六條，逐條補斷言）

| 突變 | 處置 |
| --- | --- |
| **STR-1** `permissions: contents` 提成 `write` | `test_structure_…` 逐字比對兩支 workflow 的整個 `permissions` mapping 等於 `{contents: read}`（ADR-0006 的 IAM 面向）。比對整個 mapping 而非只看一欄——多加一個 scope 與提權是同一類動作 |
| **BODY-1／BODY-4** PR 內文的 FR-G2 說明段與逐 intent 暫停說明可整段刪除 | 新增 `test_pr_body_states_the_write_scope_and_the_per_intent_pause`，逐行定位並檢查各自必須說出的事實 |
| **NP-1** 通報自身失敗的 `::warning::` 可靜默拿掉 | 新增 `test_notify_failure_is_surfaced_not_swallowed`（`construction.md`：Errors must be surfaced），並驗原始失敗不被通報失敗吃掉 |
| **TIME-1** `ROUND_AT` 整輪一值的不變式無斷言 | 新增 `date` 的 PATH shim（每次呼叫回遞增秒數、未預期 argv 一律 exit 9）＋ `test_round_at_is_taken_once_and_used_everywhere`。**真實的 `date` 在同一秒內連取兩次會回同一個值，測不出逐 intent 重算**——沒有 shim 就沒有辦法斷言這條不變式 |
| **CNT-1** `UNMANAGED` 計數器永不增加 | `test_r4c_…` 補報告計數斷言（清單與計數器是兩個獨立累計器） |
| **FC-2** 三支 composite action 缺席不再中止 | 新增 `test_missing_composite_action_is_fail_closed`（`run_round` 新增 `missing_tools` 參數），四支各缺席一次 |
| **R61-C** `grep -qxF` → `-qF`（前綴碰撞式 over-suppression） | 依 reviewer 判定**目前不可達，只補斷言、不改行為**：新增 `test_r6_1_matches_intent_ids_whole_line_not_by_prefix`。註解寫明不可達是**當下的資料狀態**而非結構性保證（`260899-alpha` 與 `260899-alpha-rev2` 都是合法的目錄名） |

判為等價突變而**未處理**：`LST-1`、`JQ-1`、`F5-B`。`GH-1`（`gh pr create` 少 `--repo`）雖也被判等價，仍隨 Critical 的修法一併補上斷言（`test_r2_3_…` 逐則檢查 `--repo` 與 `--label`）。

### 本輪的突變複驗（18 條，全數 killed）

每一條都在 `/tmp` 的獨立 `.github` 副本上跑（工作樹不被改動），逐條記錄實際變紅的測試：

| 突變 | 變紅的測試 |
| --- | --- |
| JQ-3（`--json` 少要 `files`） | `test_r6_1_open_pr_suppresses_a_second_one`、`test_r6_1_query_argv_is_complete`、`test_r6_1_matches_intent_ids_whole_line_not_by_prefix`、`test_q3_over_suppression_counterexample_pr_with_x_but_not_y` |
| R61-F（`pr list` 拿掉 `--label`） | `test_r6_1_query_argv_is_complete`、`test_r6_1_only_labelled_prs_suppress`、`test_q1_reverse_pr_label_is_derived_from_u6_not_copied` |
| JQ-2（jq 拿掉 record_root 過濾） | `test_q3_over_suppression_counterexample_pr_with_x_but_not_y` |
| R61-C（`grep -qxF` → `-qF`） | `test_r6_1_matches_intent_ids_whole_line_not_by_prefix` |
| GH-1（`pr create` 拿掉 `--repo`） | `test_r2_3_branch_name_and_label` |
| A5-1（孤兒通報掛錯 intent id） | `test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan` |
| A5-4（孤兒清單只留分支名） | 同上 |
| M5（孤兒通報 detail 拿掉分支名） | 同上 |
| BODY-1（刪「只動一個檔」整段） | `test_pr_body_states_the_write_scope_and_the_per_intent_pause` |
| BODY-4（刪逐 intent 暫停說明） | 同上 |
| BODY-3（刪 PR 內文的分支那一列） | `test_pr_body_states_the_close_path_honestly` |
| NP-1（通報自身失敗被吞掉） | `test_notify_failure_is_surfaced_not_swallowed` |
| TIME-1（`ROUND_AT` 逐 intent 重算） | `test_round_at_is_taken_once_and_used_everywhere`、`test_pr_body_states_the_close_path_honestly` |
| CNT-1（`UNMANAGED` 永不增加） | `test_r4c_parse_null_is_skipped_not_a_human_change` |
| FC-2（拿掉存在性檢查） | `test_missing_composite_action_is_fail_closed` |
| STR-1／STR-1b（impl／外層提成 `contents: write`） | `test_structure_triggers_concurrency_and_workflow_call` |
| MARK-1（commit 訊息把同步標記寫成字面） | `test_sync_marker_is_derived_from_record_sh` |

### `in` 斷言掃描（reviewer 要求的橫向複驗）

把全套的 `in`／`not in` 斷言逐一檢視「被斷言的字串是否構造上就含另一個」。找到**兩處**已重演的包含關係，另有一處是同族的弱化形式：

| 位置 | 形狀 | 處置 |
| --- | --- | --- |
| 孤兒清單 `ALPHA in cell[1] and pushed in cell[1]` | 分支名構造上含 intent id ⇒ 前半不可能獨立失敗 | 改逐字相等 |
| PR 內文 `ALPHA in body` ＋ `head in body` ＋ `"Done" in body` ＋ `TRUNK_SHA in body` | 同上（「分支」那一列的值含 intent id，於是刪掉「intent」那一列也不會紅） | 改為把內文表格逐列解析成 dict，與五列的期望值**整份**比對 |
| `f'"{MARKER}"' not in CODE` | 帶引號的字面比對抓不到把標記直接寫進 commit 訊息（`…人為改動 [aidlc-sync]"`），而那正是它要防的動作，且同一份硬寫字串同時滿足上一條「訊息含標記」 | 改為裸字面 `MARKER not in CODE`；以突變 MARK-1 複驗 |

其餘 `in` 斷言檢視後判定安全，分兩類：①前提斷言（`"雜湊已變" in r.stdout` 等）——needle 之間互不包含，且用途是證明情境成立；②list 成員比對（`REVERSE_LABEL in argv`）——那是精確的元素比對不是子字串比對。另外把數處「head 含 intent id」的鬆散斷言一併改成與 `branch_of()` 逐字相等（`test_q3_…`、`test_q2_…`、`test_f5_…`、`test_r2_3_…`）。

### reviewer 已查證通過、本輪未動的部分

F5 三項（`set +e` 的位置、`test_f5_…` 自帶 `bash_argv`、當時變紅的 5 條測試仍在守）、N:C-2 的處置（`reverse.yml:67` 與 `reconcile.yml:35` 逐字相同，本輪重新開檔複核）、label bootstrap 無死結、無 worktree 汙染、本單元對「反向 PR 不觸發別的同步」沒有錯誤假設（只有合併那一句的理由錯了，見 Major 4）。

---

## 修訂 2（同一時刻）：為什麼交付當時的數字全錯

**F5 修正是在 code-summary 寫完之後才做的，而修正沒有回寫本檔。** 交付當時的六個數字（743／1617／38 tests／237 checks／`impl:219`／`forward-impl:157`）各自剛好差 F5 那次修正的量。這是本 intent 第六次「可算的數字沒有先算」，前五次記在 `project.md` 的 `delivery-planning:dp-L1` 與 `units-generation:260822-ug-L1` 兩條。

**本輪起的做法**：交付物表與驗證表的每一格都附取得方式（`wc -l`／實跑收尾行／`git diff --numstat`），指不出來源的數字不寫。
