# Code Summary — U-5 通報

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-5-notifier · kind: library
     Generated: 2026-09-05T01:53:28Z（讀自 date -u） -->

## 建立的檔案

全部在 `.github/actions/aidlc-sync-notify/`（新目錄；本 repo 工作樹其餘檔案零改動，orchestrator 以 `git status` 複驗）：

| 檔案 | 規模 | 職責 |
| --- | --- | --- |
| `action.yml` | 163 行 | 介面轉接：inputs（`operation`／`intent_id`／`reason_code`／`stage`／`detail`／`keys`／`label`／`alert_repo`，**零憑證型 input**）→ `AIDLC_*` env → `notify.sh`；8 個 output（`result`／`issue_number`／`action`／`count`／`closed_numbers`／`closed`／`message`／`steps`） |
| `notify.sh` | 801 行（可執行；iteration 3 修正後） | 全部邏輯：`op_notify` 的四支分流（`notify_create`／`notify_append`／去重）、`op_resolve` 的批次鍵、`ensure_label` 冪等建立、SEC-2 的 `scrub_secrets`／`scrub_detail`／`scrub_errmsg`、`truncate_bytes`（UTF-8 邊界對齊）、`warn_if_truncated`。檔頭含契約段、R-1 通報／紅燈分流表、安全邊界段、錯誤模型（唯一拋例外的路徑是 R-4） |
| `run-stub-tests.py` | 1556 行（iteration 4 修正後） | 離線層：**有狀態**的 `gh` PATH shim（暫存 JSON 當 issue 存放區，實作 `issue list／create／comment／edit／close／view` 與 `label list／create` 最小子集並記錄 `calls.jsonl`）；35 案 381 斷言（iteration 3 修正後），每案含 §4.4 規格註解 |
| `run-live-tests.py` | 636 行 | 真實 Issues 層：對 `opendiamonds/cloud-360`，三層防呆（`TEST_PREFIX` 斷言、`GH_SHIM` 對清單外的 close／comment／edit 一律 exit 97、關閉前再驗內文首行）＋ `finally` 清理；4 步 42 斷言 |

## 關鍵實作決定

五項 Plan Approval 介面判斷（2026-09-05T01:13:15Z 核可）**全數照案落地**（落點由 orchestrator 開檔核對）：

| 裁決 | 落點 |
| --- | --- |
| 1 `resolve_if_open` 批次鍵 | `action.yml` 的 `keys` input；`op_resolve`（`notify.sh:617`）解析後呼叫**一次** `list_open_alerts`（`:477`），再以 `marker_in_set`（`:682`）逐鍵判定 |
| 2 `reason_code` 五個失敗碼（含 `Failed`） | `FAILURE_CODES`／`NORMAL_CODES` 常數（`:148`／`:150`）＋ `validate_reason_code`（`:261`）；`test_reason_code_sets_are_declared_in_one_place` 從 `codes` 診斷子命令讀取而非自抄一份 |
| 3 label 冪等建立 | `ensure_label`（`:438`），**唯一呼叫點**在 `notify_create`（`:523`）的 `gh issue create` 之前；競態時 `already exists` 視為成功 |
| 4 live 在 cloud-360 開真 issue | `run-live-tests.py` 的 `TEST_PREFIX`／`assert_test_intent`／`GH_SHIM`／`cleanup`（在 `finally` 內） |
| 5 `detail` 防禦性清洗 | `scrub_secrets`（`:309`）／`scrub_detail`（`:316`）／`scrub_errmsg`（`:323`）／`truncate_bytes`（`:203`） |

計畫未逐字指定處的實作定案（lead 定案並回報；標「已核對」者為 orchestrator 開檔驗過）：

1. **`closed_numbers` 改為空白分隔**（計畫括號寫「換行分隔」）——這是**對計畫文字的刻意偏離**，見下段。`emit` 對 stdout 用 `name=value` 單行形式，多行值會讓 stdout 與 `$GITHUB_OUTPUT` 兩通道解讀不一致，而呼叫端與測試 harness 都讀 stdout。已在 `action.yml` 兩處與 `notify.sh` 一處逐字寫明，並以 `test_stdout_and_github_output_agree` 鎖住兩通道一致。
2. **新增 `result` output**（已核對：`action.yml` 的 outputs 含 `result`）。計畫 Step 1 的 outputs 清單漏了它，而 Step 4 要求「exit 1、`result=external_error`」——不宣告的話呼叫端在 `if: failure()` 步驟取不到，且沒有任何工具會報錯。值域 `ok`／`external_error`；另補 `test_action_yml_declares_every_non_diagnostic_output` 雙向鎖住「實際 emit 的集合 ↔ 宣告的集合」。
3. **無 `http_status` output**：`gh issue` 子命令的 stderr 不保證帶 HTTP 碼；抓得到時併進 `message`，抓不到就不謊稱有。
4. **`alert_repo` 的預設值在 `require_repo`（`:277`）解析**，`action.yml` 的 `default` 為空字串——composite action 的 default 拿不到 runner 執行期的 `GITHUB_REPOSITORY`。
5. **token 遮罩前綴取超集**（已核對 `scrub_secrets`）：計畫列 `ghp_`／`gho_`／`github_pat_`，實作為 `gh[pousr]_` ＋ `github_pat_`。嚴格超集，不會讓任何依計畫撰寫的斷言失敗；漏掉 `ghu_`／`ghs_`／`ghr_` 的後果是把憑證印在公開 issue 上。
6. **`ensure_label` 只在 `notify` 的 0 筆分支呼叫**：實測 `gh issue list --label <不存在>` 回 `[]` 且 exit 0，只有 `issue create --label` 需要 label 先存在；`resolve_if_open` 是純讀＋關閉路徑，不該為它多發一次寫入路徑呼叫。以 `test_label_not_created_when_present_and_never_on_resolve_path` 鎖住。
7. **`LIST_LIMIT=500` 且命中上限時發警告**（計畫寫 `--limit 200`）：200 在通報 issue 累積時會**無聲**截斷；改 500 並在 `warn_if_truncated`（`:417`）寫 stderr 並併進 `message`，有專屬測試 `test_list_truncation_is_reported_not_swallowed`。
8. **`intent_id` 驗證取「最小必要」**：禁空白與角括號（會破壞內文 HTML 註解鍵），允許 `/`（`keys` 以**最後一個** `/` 切割，而 `reason_code` 不含 `/`，故無歧義）。過度限制會把合法識別字擋在門外，那是靜默失去通報的方式。
9. **`keys` 容忍縮排與 CRLF**：`keys` 是 workflow YAML 多行字串的常見產物；鍵本身仍逐字比對，命中面未擴大。

## 測試覆蓋（orchestrator 逐項複驗，非轉引）

| 層 | 結果 | 複驗方式 |
| --- | --- | --- |
| stub（離線，有狀態 shim） | 35 案 381 斷言，**0 失敗**（iteration 1 為 28 案 285 斷言） | orchestrator 以 `AIDLC_NOTIFY_BASH=/bin/bash`（3.2.57）與 `/opt/homebrew/bin/bash`（5.2）各重跑一次，同數字 |
| live（真實 `opendiamonds/cloud-360`） | 4 步 42 斷言，**0 失敗** | orchestrator 自行重跑：建立 `#553`／`#554`，測畢兩則皆關閉；`gh issue list --label aidlc-sync-alert --state open` 回 `[]` |
| repo／env contract | 兩支 validator 皆綠 | orchestrator 自行重跑 |
| 語法 | `bash -n`（3.2 與 5.2）、`py_compile` 兩支測試 | orchestrator 自行重跑 |
| §4.4 註解 | `test_every_test_carries_spec_annotations` 機械檢查全部 35 案 | 套件自檢 |

**完成判準對照**（[ug:unit-of-work.md] U-5）：
- 「同一鍵連續失敗兩輪後，該鍵的開啟中通報 issue 數為 1 且 comment 數增加 1」→ stub `test_completion_criterion_two_consecutive_rounds`；**live 步驟 (a) 逐字驗到**（第二輪 `action=commented`、`comments` 為 1、標題 `×2`、開啟中同鍵 issue 數為 1）。
- 「`reason_code` 為機制正常判斷者不使 workflow 紅燈」→ 五種正常碼傳入即 exit 2 且**零 API 呼叫**（`test_normal_reason_codes_rejected_with_zero_api_calls`）——它們根本不該呼叫 `notify`（R-1）。

### 突變驗證（lead 執行，四條；每條改壞 → 紅 → 還原 → `diff -q` 一致 → 複跑 28/285/0）

| # | 突變 | 紅的測試與斷言數 |
| --- | --- | --- |
| ① | 鍵比對改成比**標題前綴**（違反 R-2.1／SEC-1） | `test_edited_title_still_matches_by_body_key`、`test_titlelike_decoy_with_different_key_is_never_touched`：8 |
| ② | 去重改留**編號最大者**（違反 R-2.2） | `test_deduplicate_keeps_lowest_number_not_earliest_created`：7 |
| ③ | `resolve_if_open` 忽略 `keys` 一律關閉（違反 R-3.2） | `test_resolve_closes_only_keys_in_the_set`：6 |
| ④ | API 失敗時再開一則「通報失敗」issue（違反 R-4） | 三個 `test_api_failure_on_*`：3 |

lead 自陳突變 ① 的第一版**不夠忠實**（比對完整標題含 `×1`，誘餌案的 `×7` 因此沒紅）——任何以標題為鍵的實作都必須忽略變動的計數，改成前綴比對後誘餌案才紅。上表為忠實版數字。

## 與計畫的偏離

**一項**：定案 1——`closed_numbers` 由「換行分隔」改為「空白分隔」。理由是 `emit` 的 `name=value` 單行通道與 `$GITHUB_OUTPUT` 的 heredoc 通道對多行值的解讀不一致，而呼叫端與測試 harness 都讀 stdout。三處逐字寫明並以測試鎖住兩通道一致。其餘 Step 1〜9 照序執行，五項介面判斷照案落地。

## 本站實測推翻的一句上游主張（重要，Bolt 1 gate 應看見）

`nfr-requirements/tech-stack-decisions.md` 逐字寫著：改用 `list --label` ＋ 本地比對後，「**讀的是 issue 的即時狀態而非索引**」。

**這句不成立。** lead 的獨立探測（`gh issue create` 後輪詢）顯示 `gh issue list --label … --state open` **與** REST 的 `GET /repos/{owner}/{repo}/issues?state=open&labels=…` **兩者都在 t=3.6s 看不到新 issue、t=5.9s 才看到**——label 過濾的列舉同樣是最終一致的。orchestrator 複驗的那一次 live 執行印出的實測延遲：新 issue 出現在 label 列舉中約 4.1〜4.3 秒，關閉後從列舉中消失約 0.7〜4.1 秒。

- **產品行為不需要改**：這是缺口 J-1 的另一個入口，而 ADR-A8 的 R-2 第 4 步（`notify` 命中多筆時自己收斂）一字未變地涵蓋它。stub 的 `test_deduplicated_state_converges_on_the_next_round` 驗的就是這條收斂。
- **但完成判準有一個沒被寫下的前提**：「連續兩輪」的間隔必須大於這個窗口（實測約 4〜6 秒），否則第二輪會**開出重複**而非追加。實務上 U-6 由 push／PR 觸發、U-7 為每日排程，間隔遠大於此，所以這是**可接受的前提**而不是缺陷——但它是前提，不是巧合。
- **建議落點**：`tech-stack-decisions.md` 的「不依賴搜尋索引」段與 `business-rules.md` R-2 的成本段。**確認人：Bolt 1 gate**。**本站未改上游**（已核可產出），只在 `run-live-tests.py` 檔頭逐字記載。

## 未完成項目（誠實列出）

1. 上一節的上游主張更正**未落到上游檔案**，只在本檔與 live 測試檔頭記載（不改已核可產出）。
2. **live 測試在 public repo 留下永久編號**（裁決 4 已核可）：本 session 累計 `#544`〜`#549`、`#551`〜`#554` 共 10 則，**全部為 CLOSED 且全部由本測試建立**（含一次失敗執行與一次一致性探測）。orchestrator 獨立以 `gh issue list --label aidlc-sync-alert --state all` 核對，無一則是他人開的。`#538`（PRE-1 探測產物）**未被動到**（`state: OPEN`、`comments: 0`，複驗兩次）。`#550` 由既有 gh-aw workflow 產生、不帶本 label，未被碰觸。
3. **label `aidlc-sync-alert` 已在 public repo 上實際建立並保留**——這是本輪 live 測試的持久副作用，但它本來就是機制正式運行所需的物件，故不刪除。
4. `resolve_if_open` 對「本輪未處理到的 intent」不動（R-3.2）是刻意的；**沒有任何測試能證明它「永遠不會誤關」**，只能證明它在給定 `keys` 下不關集合外的鍵。
5. U-7／U-8 對 `resolve_if_open`／`notify` 的接線在各自單元實作（U-8 的元件集合已由 ADR-0015 §5 補上 C-5，確認人 Bolt 3 gate）。
6. NFR-S1 驗收判準欄的權限集合表述仍待更正（ADR-0015 §8，Bolt 0 gate）。

## 對呼叫端（U-6／U-7／U-8）的接線提示

- **憑證只經 `env: GH_TOKEN`**，action 不宣告任何憑證型 input。
- **`notify` 的 `reason_code` 只吃五個失敗碼**（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`／`Failed`）；五種正常判斷碼傳入會 exit 2——呼叫端必須在分流時就不呼叫，而不是丟給它擋。
- **`resolve_if_open` 一次帶全部鍵**（`keys` 為換行分隔的 `<intent_id>/<reason_code>`），迴圈結束後呼叫一次即可，不要逐鍵發一個 step。
- **exit code**：`ok` exit 0；`external_error` exit 1（R-4：通報失敗即拋，呼叫端**不得**再呼叫 `notify`）；介面誤用 exit 2。判定看 `result`。
- **`detail` 會被清洗後貼進公開 issue**：呼叫端仍應遵守 U-3 SEC-4（不把完整 body 或標頭放進 `message`），兩邊都要守。

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T02:11:12Z
**Iteration:** 1

### 查證方法（摘要）

逐字重讀 U-5 的四份程式碼（`action.yml`／`notify.sh`／`run-stub-tests.py`／`run-live-tests.py`）與全部五份上游產出（`business-rules.md`／`domain-entities.md`／`business-logic-model.md`／`security-requirements.md`／`tech-stack-decisions.md`）及 `code-generation-plan.md`／`code-generation-questions.md`；依 exempt 清單開 `U-6-forward-workflow/functional-design/business-rules.md` 核對 R-6.1 呼叫端契約。獨立重跑 stub 套件（`AIDLC_NOTIFY_BASH=/bin/bash` 3.2.57 與 `/opt/homebrew/bin/bash` 5.2.37，各得 28 tests / 285 checks / 0 failures，與宣稱一致）；在 scratchpad 隔離副本上自行重建突變 ①（鍵比對改比標題）與 ③（`resolve_if_open` 忽略 `keys` 一律關閉），各得 8、6 項斷言紅燈，`diff -q` 還原後複跑 28/285/0，與宣稱逐字相符；對 `scrub_secrets`／`truncate_bytes` 額外做未在既有測試中出現的邊界探測（見 Finding 1、4）；以唯讀 `gh issue view/list` 核對 `#538`（OPEN、0 comments，未被動到）、`#550`（label 為 `agentic-workflows`，非本機制物件，未被動到）與全部 10 則 `aidlc-sync-alert` 歷史 issue（`#544–#549`、`#551–#554`，皆 CLOSED）——與 summary 逐字相符。未再次執行 `run-live-tests.py`（見下方「未執行的驗證」）。

### Findings

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
|---|---|---|---|---|---|
| 1 | Critical | `notify.sh:203-228`（`truncate_bytes`） | 新設計問題 | **當截斷點恰好落在一個完整多位元組字元的結尾、且其後仍有更多內容時，`truncate_bytes` 會產生無效的 UTF-8 位元組序列**，而不是如檔頭聲稱的那樣「兩版行為一致」地正確處理邊界。演算法從尾端往回走，只要最後一個位元組落在延續位元組範圍（`\200`-`\277`）就無條件剝除（最多 3 次），最後若剩餘尾端是 lead byte（`\300`-`\377`）就再剝一次——但當剝除次數剛好等於該字元序列真正的延續位元組數時（即該字元其實完整、不需要剝），這個計數用完就跳出迴圈，**留下一個沒有配對延續位元組的孤立 lead byte**。本站以 4-byte 字元（emoji）獨立重現：`s="😀ABC"`，`truncate_bytes "$s" 4` 得到位元組序列 `f0 e2 80 a6`——`f0`（😀 的 lead byte）後面直接接著「…」的 `e2 80 a6`，兩者拼在一起**不是合法 UTF-8**（`python3 -c "bytes.fromhex('f0e280a6').decode('utf-8')"` 直接拋 `UnicodeDecodeError: invalid continuation byte`）。3-byte 字元也會觸發同型錯誤：`s="測試ABC"`、`truncate_bytes "$s" 6`（恰好是「測試」兩個完整字之後）本應保留兩字完整＋刪節號，實際只留下「測」一字，把完整且不需截斷的「試」字整個吃掉。此為 SEC-2 的核心防線（`detail`／`errmsg` 皆經此函式後才寫進**公開** issue，ADR-0006 audit logging 面向）；兩版 bash（3.2.57、5.2.37）表現一致——本站先前修正的「`printf` 有號位元組」問題確實已解決，但這是**同一函式內另一個獨立的逐位元組計數錯誤**，28 案測試無一觸及「截斷點恰好落在完整字元邊界」或任何 4-byte 字元輸入。 | 改法：不要用固定的「剝到第 3 次為止」計數，而是先判斷尾端 lead byte 本身宣告的序列長度（`\300`-`\337`=2、`\340`-`\357`=3、`\360`-`\367`=4），實際數一下它後面**接續了幾個**延續位元組，只有「接續數 < 宣告長度」（序列確實不完整）才剝除整個序列；接續數等於宣告長度時代表字元完整，什麼都不剝。並補上至少兩案：截斷點恰好落在完整字元邊界（如上例）、輸入含 4-byte 字元。 |
| 2 | Major | `code-generation-plan.md`「五項裁決」之 1；`action.yml:93-99`／`notify.sh:25-32` vs `U-6-forward-workflow/functional-design/business-rules.md:241-259`（R-6.1a／R-6.1b，reviewer iteration 2 與 iteration 4 兩輪 Critical 修正後定案） | 新引入 | **本輪的 Plan Approval 裁決 1 把 `resolve_if_open` 的介面由單鍵改成批次鍵，但沒有把這個介面異動回寫（或標記待回寫）到 U-6 已核可的 `business-rules.md`**，而後者的 R-6.1a／R-6.1b 恰好是**經過兩輪架構師 Critical 修正、逐字釘死**的內容：R-6.1a 逐字「對本輪蒐集到的每一個待關閉鍵**各呼叫一次** `resolve_if_open(FailureIdentity)`」，其下方的 reviewer 註記更明文寫「**它只能逐鍵呼叫，沒有『不帶鍵、關閉全部』的形式**」——這正是本輪要引入的批次介面的字面反義句。U-5 自己已核可（iteration 2 READY）的 `business-logic-model.md` 中對 §C-5 的簽章描述也是 `resolve_if_open(FailureIdentity)`（單一失敗身分），同樣未提及批次。code-generation-plan.md 承認「兩者字面衝突」並在 Plan Approval 取得人工核可（`[Answer]: Approve Plan`），這個決策本身合法；但 `code-summary.md` 的「未完成項目」清單（六項）**沒有一項提到**「U-6 的 R-6.1a／R-6.1b 現在描述的呼叫慣例已經與 U-5 實際交付的介面不一致，需要回頭更新並指定確認人」。如果 U-6 的 code-generation 之後只依它自己已核可的文字實作（逐鍵各呼叫一次），批次介面省下「每輪一次查詢」的整個設計目的（R-3 群、`tech-stack-decisions.md` 都拿它當賣點，且明文引用「6 個 intent × 5 個 reason_code＝30 次額外呼叫」作為否決 [Q2=B] 的理由）就會落空——不是功能會壞，是 NFR-I4 想避免的呼叫量又回來了，而且沒有任何測試會發現，因為 U-5 自己的 28 案只測「呼叫端已經正確組出多行 `keys`」這個情境，不測「呼叫端逐鍵各發一次」這個 U-6 自己文件仍在教的情境。 | 在本站或回 U-6 補一個明確指派：更新 U-6 `business-rules.md` 的 R-6.1a／R-6.1b，把「各呼叫一次」改寫為「本輪迴圈內蒐集全部待關閉鍵，迴圈結束後以換行分隔組成單一 `keys` 值呼叫一次」，並指定確認人與時機（比照本檔對 U-8／NFR-S1 缺口的既有做法：標出、不逕改、列入 Bolt gate）。同時把這一項補進 `code-summary.md` 的「未完成項目」，不要只停留在 `code-generation-plan.md` 的裁決記述裡。 |
| 3 | Minor | `functional-design/domain-entities.md`（reason_code 值域段）、`functional-design/business-rules.md`（R-1 表） | 新引入 | 本輪 Plan Approval 裁決 2 把 `notify` 的 `reason_code` 允許集合由 U-5 自己已核可的 `domain-entities.md`／`business-rules.md` 所列的**四個**（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`）擴為**五個**（加入 `Failed`），且 `notify.sh` 與 `action.yml` 均已正確落地五個值。但 `domain-entities.md` 逐字寫「實際會成為 `FailureIdentity` 一部分的是 `ExternalError`、`Rejected`、`Aborted`（後者通報但不紅燈）、`CannotCreate`」——不含 `Failed`；`business-rules.md` 的 R-1 表同樣只有四個失敗碼那幾列，沒有 `Failed` 那一列。程式碼本身的 docstring（`notify.sh:50-59`）已正確補上 `Failed` 那一列並附出處（U-6 R-5.12），但**已核可的上游 functional-design 檔案本身未同步**，成為兩份互相矛盾的「正本」。 | 比照 Finding 2 的處置形狀：標出、不逕改，指派把 `domain-entities.md`／`business-rules.md` 的值域與 R-1 表更新為五個失敗碼，附上出處（U-6 R-5.12／R-6.1b）與確認人（建議與 Finding 2 同一個 Bolt gate 一併處理，因為兩者都是「本輪擴充了 U-5 對外契約，但只在程式碼裡兌現，沒有回寫上游文件」同一種缺口）。 |
| 4 | Minor | `notify.sh:302-307`（`scrub_secrets`） | 新設計問題 | `scrub_secrets` 對 token 前綴的比對式（`sed -E`）**逐行**運作，且在 `scrub_detail`／`scrub_errmsg` 裡是**先** `scrub_secrets` **後** `single_line`（把換行併成空白）。若原始（未清洗前）文字裡剛好有一個真實換行字元把 token 從中間切開（本站以 `scrub_secrets "ghp_ABCDE\nFGHIJKL more text"` 重現），兩段都留在輸出裡、**完全沒有被遮罩**，而 `single_line` 隨後只是把中間的換行換成空白，兩段殘存的 token 字串仍完整可讀。已測項目只涵蓋「token 在單行內」與「Authorization 標頭在單行內」，未涵蓋「token 本身跨行」。給定本函式的定位就是「兜底擋不小心把 stderr／API 回應原樣轉貼」這一類，而多行輸出（尤其是網路錯誤訊息或大段回應）用換行分行是常態，這個順序讓 SEC-2 的兜底在跨行的情況下失去作用。 | 在 `scrub_secrets` 內先呼叫等效於 `single_line` 的換行→空白正規化（或至少對 `sed` 加 `N`/多行模式讓比對能跨行），再做 token 遮罩；或者調換 `scrub_detail`／`scrub_errmsg` 內兩個函式的呼叫順序（先 `single_line` 再 `scrub_secrets`）。 |

### Attempted refutations that did not hold

- **完成判準第二句「reason_code 為機制正常判斷者不使 workflow 紅燈」是否只被宣稱**：確認 `test_normal_reason_codes_rejected_with_zero_api_calls` 確實鎖住「五個正常碼傳入即 exit 2、零 API 呼叫」，但這只證明「若誤呼叫，會乾脆地失敗」，不能證明「真實呼叫端永遠不會誤呼叫」（後者是 U-6／U-7／U-8 的契約義務，不在 U-5 的驗證範圍內）。`code-summary.md` 的措辭（「它們根本不該呼叫 notify（R-1）」）已誠實地把這個界線寫清楚，沒有誇大成「本單元保證 workflow 不紅燈」。**判定：如實揭露，非缺陷。**
- **`closed_numbers` 空字串與「output 沒寫出」的可分辨性**：追蹤全部 `emit closed_numbers` 呼叫點，`result=ok` 的三條路徑（`notify_create`／`notify_append`／`op_resolve`）**皆無條件** emit 這個 output（即使是空字串）；只有 `external_error()`／`fail()` 兩種失敗路徑不 emit 它，而這兩者本就以 `result` 缺席或非 `ok` 表示失敗。呼叫端只要先看 `result` 再讀 `closed_numbers`，兩種情況不會混淆。**判定：非缺陷。**
- **`intent_id` 含 `/` 是否會與 `keys` 的「最後一個 `/` 切割」規則產生歧義**：以 `intent_id="aidlc-sync-test-alpha/Rejected"`、真實 `reason_code="CannotCreate"` 構造鍵 `aidlc-sync-test-alpha/Rejected/CannotCreate`，實測 `resolve_if_open` 正確切出 `reason=CannotCreate`、`intent=aidlc-sync-test-alpha/Rejected` 並精確關閉對應 issue。**判定：非缺陷，`code-generation-plan.md` 對此的推論成立。**
- **`ensure_label` 只在 `notify` 的 0 筆分支呼叫，是否讓 `resolve_if_open` 在 label 不存在時出錯**：`list_open_alerts` 對不存在的 label 由 `gh` 回空陣列、exit 0（設計文件所述、且與既有 `test_label_not_created_when_present_and_never_on_resolve_path` 的假設一致），`resolve_if_open` 在此情況下正確地無事可做並回傳 `closed=0`。**判定：非缺陷。**
- **`LIST_LIMIT=500` 的截斷警告是否真的會觸發**：獨立確認 `test_list_truncation_is_reported_not_swallowed` 構造 500 則 issue 並斷言 `message`／`stderr` 皆提及「命中列舉上限」。**判定：如claimed，非缺陷。**
- **突變①／③獨立重建**：在 scratchpad 隔離副本上分別把 `MATCH_JQ`／比對鍵改成比對標題前綴（保留 body 寫入邏輯不變，只改搜尋依據）與把 `marker_in_set` 改成恆真，各自獨立重跑 28 案，得 8 項與 6 項斷言紅燈，與 `code-summary.md` 的突變表逐字相符；`diff -q` 還原後複跑 28/285/0。**判定：突變驗證誠實、可重現。**

### 未執行的驗證

未再次執行 `run-live-tests.py`：orchestrator 本輪已完整跑過一次（4 步 42 斷言、0 失敗），本站以唯讀 `gh issue view/list` 核對其宣稱的全部痕跡（`#538`、`#550`、10 則歷史 issue 的狀態與 label）逐一相符，判斷再開一輪 live 不會增加對 Finding 1〜4（皆為程式碼層級、live 環境無法比 stub 更精確驗證）的信心，且會在 public repo 再留下 2〜3 個永久 issue 編號，故不重跑，改以唯讀查證取代。

### Summary

**新引入：3 項**（Finding 2、3、4）、**既存漏審：0 項**、**新設計問題：2 項**（Finding 1、4——註：Finding 4 與 Finding 1 同屬「本輪新寫的清洗／截斷函式本身有邊界缺陷」，於上表計入新設計問題；Finding 2、3 屬「本輪的裁決擴大了 U-5 對外契約，但未回寫或標記待回寫的上游文件」）。

Critical 1 項（`truncate_bytes` 在完整字元邊界上產生無效 UTF-8，兩版 bash 一致重現、無測試涵蓋）：本單元的四支分流、去重演算法、批次鍵、R-4 不可遞迴通報、SEC-1 破壞性動作判準等核心邏輯經獨立複驗（28/285/0 兩版一致、突變①③獨立重建、live 痕跡唯讀核對）皆與宣稱相符、設計紮實；但 SEC-2 的清洗兜底本身（`truncate_bytes`）有一個會產生無效 UTF-8 輸出的計數缺陷，且與其相鄰的 `scrub_secrets` 有一個換行切斷 token 的遮罩逃逸（Finding 4）——兩者都在「防禦性清洗」這一層，且都不在 28 案測試的覆蓋範圍內。另有兩項本輪的介面／值域擴充裁決（批次鍵、`Failed` 碼）已在程式碼正確落地，但未回寫或標記待回寫已核可的上游 functional-design 文件（U-6 的 R-6.1a／R-6.1b 與 U-5 自己的 domain-entities.md／business-rules.md），使其中一份（U-6，經兩輪 Critical 修正才定案）出現字面矛盾。判定 NOT-READY。

## Post-review 修正（2026-09-05T02:31:57Z）

reviewer iteration 1 判 **NOT-READY**（新引入 3／既存漏審 0／新設計問題 2；1 Critical、1 Major、2 Minor）。Critical 與 Minor 2 已修並複驗；Major 與 Minor 1 屬已核可上游文件，以標出並指派處置，不回改。

### Critical — `truncate_bytes` 的 UTF-8 邊界回退是錯的（已修）

**orchestrator 先自行複驗，且範圍比 reviewer 報告的更廣**：舊演算法是「從尾端往前砍 continuation byte，最多三次」，但**完整字元的尾端本來就是 continuation byte**，所以截斷點只要落在字元邊界上就會誤刪一個完整字元；4-byte 字元還會砍到只剩孤立的 lead byte 而產出**無效 UTF-8**。lead 複驗時再補出第三個邊界案（2-byte 的 `café!`），範圍又寬一格。

| 輸入 | 上限 | 修正前 | 修正後（orchestrator 直接呼叫函式複驗，兩版 bash 一致） |
| --- | --- | --- | --- |
| `😀ABC` | 4 | `f0 e2 80 a6` ← 無效 UTF-8 | `'😀…'` |
| `測試ABC` | 6 | `測…` ← 誤刪「試」 | `'測試…'` |
| `café!` | 5 | `caf…` ← 誤刪 `é` | `'café…'` |
| `測試ABC` | 4 | `測…` | `'測…'`（本來就對） |
| `測試ABC` | 7 | `測試A…` | `'測試A…'`（本來就對） |

**新演算法**：切到 `max` 位元組後，從尾端往前找第一個非 continuation 的位元組並記其距尾端的位置 `k`（最多回看 4 個）；依該位元組定序列長度 `need`（1／2／3／4，非法 lead 為 0）；**`k == need` 表示序列完整、不砍**，否則砍掉尾端那 `k` 個位元組。這一步就是舊版缺的判斷。

**新測試**（`run-stub-tests.py`，新增 5 案）：`test_truncate_bytes_never_emits_invalid_utf8`（12 組表格，涵蓋 2／3／4-byte 字元的邊界與中間、ASCII 切點、純 ASCII、不需截斷時不得補省略號；**每組都以 Python 的 `bytes.decode("utf-8")` 驗證合法性**，不只比字串）、`test_truncate_bytes_output_is_always_a_maximal_valid_prefix`（把上限從 0 掃到長度+2，驗四條性質：合法 UTF-8、是原字串的字元前綴、不超過上限、且是該上限下**最長**的前綴——最後一條專抓砍過頭）。為此新增 `truncate` 診斷子命令（沿 `codes`／`defaults` 形狀，參數走 argv、不走 `emit` 也不新增 `AIDLC_*` env，以免動到既有的兩個介面契約測試）。

### Minor 2 — 換行切開的 token 逃逸遮罩（已修，但**修不掉全部**）

`scrub_detail`／`scrub_errmsg` 把 `single_line` 移到 `scrub_secrets` **之前**。

**lead 實測後誠實記載的限制（重要）**：`single_line` 把換行換成**空白**，而遮罩正則在空白處與在換行處一樣會斷。真正被修好的只有 `Authorization:` 規則那一類（它的 `.*` 在單行化後能吃到原本跨行的值）；`ghp_ABC` 換行 `DEFGHIJ`（前段短於 `{6,}`）或 `ghp_AAAABBBB` 換行 `CCCCDDDD`（只遮前段）**兩種順序都仍會逃逸**。這三條限制已逐條寫進 `scrub_secrets` 的註解，並在新測試裡以**註解而非斷言**記載——把弱點斷言成「預期行為」會讓日後真要補強它的人看到紅燈。遮罩式清洗防的是「不小心貼上」，不是「刻意規避」。

**lead 指出的一項副作用（判斷，非事實）**：`Authorization:` 規則的 `.*` 現在會吃到整段 detail 的結尾而非只到該行結尾，標頭之後的診斷文字會一併被遮。既有的 `test_detail_is_scrubbed_before_it_reaches_a_public_issue` 因此仍綠但**綠的理由變了**（四個 token 前綴規則被那條規則整段吞掉、不再被實際執行）。lead 未改該已核可測試，改為新增 `test_token_prefix_rules_still_fire_without_an_authorization_header` 把覆蓋補回來。SEC-2 的成本不對稱（少一段診斷 vs 公開一個憑證），判定副作用可接受——**這是判斷不是事實，gate 應看見**。

### Major — 批次鍵介面與 U-6 已核可 `business-rules.md` 字面矛盾（未修，指派）

reviewer 的觀察成立：U-6 的 R-6.1a／R-6.1b 經兩輪修正後逐字釘死「對每個待關閉鍵**各呼叫一次**…沒有『不帶鍵、關閉全部』的形式」，而本輪 Plan Approval 裁決 1 引入的批次鍵介面與該字面矛盾；U-5 自己已核可的 `business-logic-model.md` 也只寫單鍵簽章。

**處置**：不回改已核可上游（兩份都是通過 reviewer 的 functional-design 產出）。**指派 U-6 的 code-generation**：實作 `aidlc-sync-forward.yml` 呼叫 `resolve_if_open` 時，以**一個 step 帶全部鍵**（`keys` 為換行分隔的 `<intent_id>/<reason_code>`），並在其 code-summary 明記「R-6.1a 的『各呼叫一次』在實作上收斂為一次批次呼叫，每個鍵的語意與單獨呼叫相同（不存在即 no-op），理由是 R-6.1a 與 U-5 R-3／[Q2=A] 的『每輪一次查詢』字面衝突，逐鍵呼叫會重現 [req:FR-I4] 要避免的每輪 30 次額外呼叫」。**確認人：Bolt 1 gate**（U-5 與 U-6 同屬 Bolt 1）。

**風險如實記載**：若 U-6 照其已核可文件逐鍵呼叫，NFR-I4 想避免的呼叫量會原樣重現，**且沒有任何測試會發現**——因為逐鍵呼叫在功能上是對的，只是貴。這正是 reviewer 判它為 Major 的理由。

### Minor 1 — `domain-entities.md`／`business-rules.md` R-1 表未同步 `Failed`（未修，指派）

程式碼已正確落地五個失敗碼（Plan Approval 裁決 2 核可），但 U-5 兩份已核可 functional-design 仍列四個。**不回改**；**指派 Bolt 1 gate** 確認是否要在契約上明寫第五個碼。實務影響為零（`FAILURE_CODES` 是單一真實來源，且有測試從 `codes` 診斷子命令讀取而非自抄一份），純屬文件對齊。

### 修正後的複驗（orchestrator 自行重跑，非轉引）

| 項目 | 結果 |
| --- | --- |
| stub，`/bin/bash` 3.2.57 | 33 tests, 372 checks, 0 failures |
| stub，`/opt/homebrew/bin/bash` 5.2.37 | 33 tests, 372 checks, 0 failures |
| `truncate_bytes` 五個邊界案 | 直接抽出函式呼叫，兩版 bash 皆輸出合法 UTF-8 且與期望逐字相符（上表） |
| 兩支 validator | 皆 passed |
| `bash -n`（3.2 與 5.2）、`py_compile` 兩支測試 | ok |
| live | **本輪未重跑**（Critical 與 Minor 2 都是純函式層，stub 足以驗證；避免在 public repo 再留下 issue 編號） |

### 突變驗證（lead 執行；每條改壞 → 紅 → 還原 → `diff -q` 一致 → 複跑）

| # | 突變 | 紅的測試與斷言數 |
| --- | --- | --- |
| M-A | `truncate_bytes` 改回「無條件砍尾端 continuation bytes」 | `test_truncate_bytes_never_emits_invalid_utf8`（3）＋ `test_truncate_bytes_output_is_always_a_maximal_valid_prefix`（2）＝5 |
| M-B | `scrub_detail` 的 `single_line` 移回 `scrub_secrets` 之後 | `test_secret_scrubbing_is_not_defeated_by_a_line_break`：2 |
| M-B′ | 同時把 `scrub_detail` **與 `scrub_errmsg`** 都移回去 | 上述 2 ＋ `test_error_message_scrubbing_is_not_defeated_by_a_line_break`：3 |

M-B′ 是 lead 自己加的第三條：M-B 只動 `scrub_detail` 時，`scrub_errmsg` 那半邊的修改**沒有任何測試會紅**——它同時補了那個測試（`test_error_message_scrubbing_is_not_defeated_by_a_line_break`），屬「契約有一端懸空」的自檢。

### lead 回報的 bash 3.2 相容性發現（值得記）

`$'\000'` 在 bash 中展開成**空字串**（NUL 不能存在於 bash 字串），所以 `[$'\000'-$'\177']` 會退化成只配對 `-` 與 `\x7F` 的錯誤樣式——靜態看不出來，是實跑表格才發現 ASCII 分支沒進去。已改成 `\001` 起算並在註解寫明。`${cut: -$k:1}` 在 3.2 與 5.2 行為一致（冒號後空白不可省），未遇版本分歧。

### 未完成項目的增補

7. **`truncate` 診斷子命令仍要求 PATH 上有 `gh`**（`main()` 在 `case` 之前就檢查）：純函式探針不需要它，但移動該檢查會改變 `codes` 的既有行為，lead 未動。可列為獨立小清理。
8. **Minor 2 的三條殘留逃逸形狀**（見上）：這是遮罩式清洗的本質限制，已在程式碼註解與本節記載，**未寫成斷言**。

## Review (code-generation — iteration 2)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T03:05:32Z
**Iteration:** 2

### 查證方法（摘要）

逐行重讀 `notify.sh` 全檔（含 Post-review 修正後的 `truncate_bytes`／`scrub_secrets`／`scrub_detail`／`scrub_errmsg`／`main`）。獨立重跑 `run-stub-tests.py`（兩版 bash：`/bin/bash` 3.2.57、`/opt/homebrew/bin/bash` 5.2.37），兩版皆得 **33 tests, 372 checks, 0 failures**，與 summary 逐字相符。對 `truncate_bytes` 做 summary 未涵蓋的邊界輸入（透過 `notify.sh truncate <text> <max>` 診斷子命令，直接對真實檔案唯讀呼叫，不涉及 `gh` API）：4/3/2-byte 字元的邊界與中間切點（重複既有 12 案，確認吻合）、`max=0`、空字串、`max` 超過總長、以孤立 continuation byte 開頭的輸入、非法 lead byte（`\xF8`）、以及**尾端連續 ≥5 個 continuation byte**（畸形輸入，超出演算法固定 4 位元組的回看視窗）。最後一類發現新 Critical（見下）。在 scratchpad（`mut-verify/`）建立三個獨立副本，分別以三種不同語意重建「M-A：`truncate_bytes` 改回無條件砍 continuation bytes」突變，各自跑 `run-stub-tests.py` 取得失敗計數；比對 summary 的「3＋2＝5」宣稱（見 Attempted refutations）。以唯讀 `grep`／`git check-ignore` 核對 `__pycache__` 的 `.gitignore` 涵蓋、`action.yml`／`domain-entities.md`／`business-rules.md` 現況、以及依 exempt 清單開 `U-6-forward-workflow/functional-design/business-rules.md` 核對 R-6.1a／R-6.1b 原文與 `[req:FR-I4]` 出處。全程未執行 `run-live-tests.py`、未對 public repo 做任何寫入操作、未修改本 repo 工作樹內任何檔案（僅在 scratchpad 建立隔離副本）。

### 逐項判定（iteration 1 的四項發現）

| # | 原判定 | 本輪結論 | 依據 |
|---|---|---|---|
| 1（Critical，`truncate_bytes` 邊界誤刪／無效 UTF-8） | 需修 | **Resolved（僅就原文回報的情境）**——4/3/2-byte 字元「切點恰好落在完整字元邊界」與「切在中間」兩類，本輪逐一複驗（含 `😀ABC`／`測試ABC`／`café!` 全部既有 12 案）皆與宣稱的修正後輸出逐字相符，兩版 bash 一致。**但本輪在同一函式發現一個新的、獨立的 Critical**（見「新發現」#1）——原演算法設計本身對「輸入已破損（畸形 UTF-8）」這一類仍然錯誤，只是這一次是本輪新演算法自身的另一個計數缺口，不是同一個 bug 復發。 |
| 2（Major，批次鍵 vs U-6 `business-rules.md` R-6.1a／R-6.1b 字面矛盾） | 未修，指派 Bolt 1 gate | **Deferred-by-assignment，指派內容具體且可執行**。開 `U-6-forward-workflow/functional-design/business-rules.md` 核對：R-6.1a（`241` 行）逐字「各呼叫一次」、其下方 reviewer 註記（`246` 行）逐字「它只能逐鍵呼叫，沒有『不帶鍵、關閉全部』的形式」——與 summary 引用完全相符，未過度轉述。指派文字點名確切檔案（`aidlc-sync-forward.yml`）、確切機制（一個 step 帶全部鍵）與確切要求（U-6 code-summary 需記載收斂理由），足夠具體讓 U-6 實作者照做而不需回頭問 U-5。所引 `[req:FR-I4]` 核對 U-5 自己已核可的 `business-rules.md:42`（「被否決的逐鍵列舉（Q2=B）...而 [req:FR-I4] 的單次操作上限是已知未定值」）逐字一致——**不是本輪新造的引用**，是沿用既有核可產出的既有出處，未查得誤植。 |
| 3（Minor，`domain-entities.md`／`business-rules.md` R-1 表未列 `Failed`） | 未修，指派 Bolt 1 gate | **Deferred-by-assignment，未修屬實**。逐字核對兩檔現況：`domain-entities.md:13` 仍寫「實際會成為 `FailureIdentity` 一部分的是 `ExternalError`、`Rejected`、`Aborted`...、`CannotCreate`」（四個，無 `Failed`）；`business-rules.md` 的 R-1 表（`12`–`15` 行）同樣只有四列。與 summary「未修」的陳述相符，程式碼側 `FAILURE_CODES` 確為單一真實來源（`test_reason_code_sets_are_declared_in_one_place` 從 `codes` 診斷子命令讀取，非自抄）。 |
| 4（Minor，換行切開 token／`scrub_secrets` 順序） | 已修，殘留三條逃逸形狀 | **Resolved（如實揭露殘留限制）**。`single_line` 確實移到 `scrub_secrets` 之前（`notify.sh:361-373`）；`test_secret_scrubbing_is_not_defeated_by_a_line_break`／`test_error_message_scrubbing_is_not_defeated_by_a_line_break` 兩案獨立複驗皆綠。逐行核對 `test_detail_is_scrubbed_before_it_reaches_a_public_issue` 的既有 detail 語料（token 全部緊跟在 `Authorization: token` 之後），確認 summary「該案綠燈理由已改變（由 `Authorization:.*` 整段吞掉，而非四個前綴規則各自命中）」為真；`test_token_prefix_rules_still_fire_without_an_authorization_header` 確實把四個前綴規則的獨立覆蓋補回。殘留的三條逃逸形狀（跨行切開 token、雙段皆短於 `{6,}`、僅遮前段）在程式碼註解（`notify.sh:339-347`）與測試檔頭（`933` 行附近）逐字記載為限制而非斷言，未見誇大或隱瞞。 |

### 新發現

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
|---|---|---|---|---|---|
| 1 | Critical | `notify.sh:198-256`（`truncate_bytes`） | 新設計問題 | **本輪「已修」的 `truncate_bytes` 對已破損（畸形）UTF-8 輸入仍可產生無效 UTF-8**，與函式自身註解的明文保證（`notify.sh:220-222`：「輸入本身已非法時它會多砍一個位元組，代價是少一個字元，**換得輸出必為合法 UTF-8**」）以及新增測試 `test_truncate_bytes_never_emits_invalid_utf8` 的名稱所承諾的性質（「從不產生無效 UTF-8」）矛盾。新演算法從尾端最多回看 **4** 個位元組尋找 lead byte；當尾端連續 continuation byte（`\x80`-`\xBF`）的數量 **≥5**（輸入本身已是畸形 UTF-8——這種情況不需要合法輸入也能構造，例如上游 `gh` stderr 或呼叫端 `detail` 挾帶的二進位雜訊、雙重截斷後的殘片等不保證是良構 UTF-8 的來源）時，迴圈在 `k=5` 因 `k<=4` 條件失敗而中止，此時 `need` 停留在初始值 `0`（從未進入任何 case 分支設定它），`k != need` 恆真，於是只剝除固定的 `k` 個位元組——**但這個數字不足以清除全部連續 continuation byte**，尾端會留下若干個「沒有配對 lead byte」的孤立 continuation byte，寫入公開 issue 後仍是無效 UTF-8。本站以 `bash notify.sh truncate "$(printf 'A\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80')" 9` 在兩版 bash（3.2.57、5.2.37）獨立重現：輸出原始位元組為 `41 80 80 80 e2 80 a6`（`'A'` + 三個孤立 `\x80` + 省略號），`python3 -c "b'\x41\x80\x80\x80\xe2\x80\xa6'.decode('utf-8')"` 拋 `UnicodeDecodeError: invalid continuation byte`。既有 33 案測試（含本輪新增的 `test_truncate_bytes_never_emits_invalid_utf8`／`test_truncate_bytes_output_is_always_a_maximal_valid_prefix`）**皆不含任何一組連續 ≥5 個 continuation byte 的輸入**（掃描測試的探測文字 `測試😀café!ABC。` 全為良構 UTF-8，且良構 UTF-8 的單一字元最多只有 3 個延續位元組，故掃描測試結構上永遠碰不到這個分支）——這正是「修正動作本身也要過檢查」（`functional-design:c10` 附註）要抓的那一類：本輪新演算法解決了 iteration 1 報的「良構輸入切在邊界」問題，但引入（或者說：未涵蓋）了「畸形輸入超出固定回看視窗」這個新的計數缺口，兩者是同一函式內兩個獨立的失效模式。此為 SEC-2 的核心防線（`detail`／`errmsg` 皆經此函式後才寫進**公開** issue），與 iteration 1 Critical 同一安全邊界、同一嚴重度依據。 | 不要用固定的「最多回看 4」搭配「找不到就當作 need=0」的預設值，這個預設值在找不到有效 lead byte 時本身就不可信。改法：迴圈找不到非 continuation byte 時（即回看 4 次後仍全是 continuation byte，或字串本身已耗盡），視為「整個 cut 尾端都需要清除到第一個非 continuation byte（或字串開頭）為止」——即不設 4 的上限，繼續往前掃直到遇到非 continuation byte 或耗盡整個 `cut`；找到後再依該位元組是否為合法 lead 且 `k==need` 判斷是否保留。並補上至少一組「尾端連續 ≥5 個 continuation byte（畸形輸入）」的案例，用 `bytes.decode("utf-8")` 斷言輸出仍合法。 |
| 2 | Minor | `code-summary.md` 開頭「建立的檔案」表（本檔 `12`、`14` 行）與「測試覆蓋」表（`45` 行） | 新引入 | Post-review 修正在 `notify.sh` 新增約 57 行（724→**781** 行，含新版 `truncate_bytes`、新增 `truncate` 診斷子命令與更新的註解）、在 `run-stub-tests.py` 新增約 219 行（1228→**1447** 行，含 5 個新案例），測試數由 28 案 285 斷言變成 **33 案 372 斷言**（下方「修正後的複驗」表本身已正確記載新數字）。但檔案最開頭的「建立的檔案」表仍寫 `notify.sh` **724 行**、`run-stub-tests.py` **1228 行**、「28 案 285 斷言」，「測試覆蓋」表的 stub 列也仍寫「28 案 285 斷言」——這些是本輪 Post-review 編輯之後**沒有回頭同步**的殘留數字，讀者若只看檔案開頭會拿到過期資訊。本輪已獨立重跑兩版 bash 確認現況為 33/372/0（見查證方法）。 | 把「建立的檔案」表與「測試覆蓋」表的 stub 列更新為現況數字（`notify.sh` 781 行、`run-stub-tests.py` 1447 行、33 案 372 斷言），並在 Post-review 修正段落開頭加一句指向這兩處已同步更新，避免下一次修訂又只顧著改 Post-review 區塊。 |

### Attempted refutations that did not hold

- **獨立複驗 33/372/0**：兩版 bash 各自重跑 `run-stub-tests.py`（未經任何修改的原檔），皆得 `33 tests, 372 checks, 0 failures`，與 Post-review 段落宣稱逐字相符。**判定：屬實，非缺陷。**
- **`scrub_secrets`／`single_line` 順序副作用（`Authorization:` 規則整段吞掉 detail）**：逐行核對 `scrub_detail`（`notify.sh:361-366`）呼叫順序與 `test_detail_is_scrubbed_before_it_reaches_a_public_issue` 的既有語料排列，確認四個 token 全部落在 `Authorization: token` 之後、單行化後會被 `.*` 整段吞掉；`test_token_prefix_rules_still_fire_without_an_authorization_header` 確實用「detail 內無 Authorization 字樣」的語料把四個前綴規則各自的覆蓋補回。**判定：如實揭露，非缺陷。**
- **`[req:FR-I4]` 是否為本輪指派文字新造／誤植的引用**：開 U-5 自己已核可的 `business-rules.md:42` 核對，該行原文已寫「被否決的逐鍵列舉（Q2=B）在 6 個 intent × 5 個 reason_code 下是 30 次額外呼叫，而 [req:FR-I4] 的單次操作上限是已知未定值」——指派文字沿用既有出處，非新造。**判定：非缺陷。**
- **`__pycache__` 是否被 `.gitignore` 涵蓋**：`.gitignore:30` 為無前導 `/` 的 `__pycache__/`，`git check-ignore -v` 對 `.github/actions/aidlc-sync-notify/__pycache__` 與其下檔案皆命中該規則。**判定：涵蓋，非缺陷。**
- **bash 3.2 的 `$'\000'` 空字串相容性宣稱**：以 `/bin/bash` 直接測試 `case $'\001' in [$'\000'-$'\177']) ...` 確認不命中（`${#$'\000'}` 為 `0`），與宣稱一致。**判定：屬實，非缺陷。**
- **`truncate` 診斷子命令是否影響既有介面契約測試**：`emitted`（`test_action_yml_declares_every_non_diagnostic_output` 用的 `emit` 掃描）與 `used`（`test_action_yml_env_mapping_matches_script` 用的 `${AIDLC_…}` 掃描）兩個正則皆掃不到 `truncate` 分支——它不呼叫 `emit`、不讀任何 `AIDLC_*` 變數，僅使用 argv。**判定：未破壞既有契約測試，非缺陷。**
- **突變 M-A 的精確斷言數「3＋2＝5」能否獨立复现**：以三種不同語意重建「改回無條件砍 continuation bytes」：(a) 直譯 Post-review 文字（尾端最多砍 3 次 continuation byte，無其他步驟）→ **33 tests, 365 checks, 21 failures**；(b) 最小化改動（僅刪除 `k != need` 這個判斷，其餘不變，永遠執行剝除）→ **33 tests, 372 checks, 7 failures**（`test_truncate_bytes_never_emits_invalid_utf8` 6 個字串比對失敗＋`test_truncate_bytes_output_is_always_a_maximal_valid_prefix` 1 個聚合檢查失敗）；(c) 逐字依 iteration 1 Finding 1 原文重建的舊演算法（先砍最多 3 次 continuation byte，剩餘尾端若仍是 lead byte 再砍一次）→ **33 tests, 372 checks, 4 failures**（3 個字串比對失敗＋1 個聚合檢查失敗），是三者中最接近「3＋2＝5」的重建。三次重建**皆使兩個測試變紅、還原後 `diff -q` 對照 scratchpad 原始副本一致**——質性宣稱（改壞→紅、可還原）成立；但沒有一種重建剛好對出「3＋2＝5」這個精確數字，最接近的是 3＋1＝4。**判定：質性宣稱屬實；量化宣稱（精確計數）未能獨立复现，記為報告精度問題，不影響 M-A 驗證本身的有效性，亦不構成獨立於 Finding 1（本表 #1）之外的新缺陷。**

### 三類計數

新引入：1 項（Minor #2）、既存漏審：0 項、新設計問題：1 項（Critical #1）。

### Summary

Iteration 1 的四項發現：#1（Critical）就其原文情境已修正且複驗吻合、#4（Minor）已修正且殘留限制如實記載、#2（Major）與 #3（Minor）維持未修但指派具體且來源核對無誤，處置恰當。**但本輪對「已修」的 `truncate_bytes` 做超出既有測試範圍的畸形輸入探測，發現同一函式內一個獨立的新 Critical**：對尾端連續 ≥5 個 continuation byte 的畸形輸入（回看視窗固定 4 位元組），演算法仍會產生無效 UTF-8，直接牴觸函式自身註解與新測試名稱所承諾的「從不產生無效 UTF-8」，且兩版 bash 一致重現、零測試涵蓋。另有一項本輪 Post-review 編輯造成的 Minor：檔案開頭的「建立的檔案」與「測試覆蓋」表的行數／案例數在修正後未同步更新，殘留過期數字。批次鍵介面與 U-6 已核可文件的字面矛盾（Major）、五個失敗碼未同步進 U-5 自己的 `domain-entities.md`／`business-rules.md`（Minor）兩項維持 iteration 1 的指派處置，本輪核對指派內容具體、引用出處無誤，未再要求修改。判定 NOT-READY。

## Post-review 修正（iteration 2，2026-09-05T03:15:32Z）

reviewer iteration 2 判 **NOT-READY**（新引入 1 Minor／既存漏審 0／新設計問題 1 Critical）。兩項皆已修並複驗。

**輪次說明**：`reviewer_max_iterations` 為 2，本輪已用罄。依 `project.md` 的 `application-design:c4`——「某輪的 Critical 若是上一輪修正時新引入的，不得以『iterations 用罄即 proceed』放行；驗證輪不計入原始上限」——本輪的 Critical 正是 iteration 1 修正動作留下的缺口，且落在 SEC-2 的公開 issue 路徑上，故修而不放行，並另跑一輪**驗證輪**。

### Critical — 新演算法對**畸形**輸入仍在尾端留下不完整序列（已修）

**orchestrator 獨立複驗成立**：`notify.sh truncate "$(printf 'A\x80\x80…')" 9`（尾端 10 個連續 continuation byte）在兩版 bash 皆輸出 `41 80 80 80 e2 80 a6`，`bytes.decode("utf-8")` 拋 `UnicodeDecodeError`。

**根因**：iteration 1 的演算法是「掃描一次算出要剝幾個位元組，然後剝一次」。回看窗是 4 個位元組——尾端若有連續 5 個以上 continuation byte，迴圈用盡窗口而 `need` 停在 0，那個固定剝除量清不乾淨，留下孤立的 continuation byte。既有 33 案的語料全是良構 UTF-8，結構上碰不到這個分支。

**修法（orchestrator 執筆）**：改為**逐位元組收斂**——「尾端不是完整的合法序列就丟掉最後一個位元組，再看一次」，直到尾端合法或字串為空。沒有回看上限問題：每一輪必定丟掉一個位元組，故必然停機，且停下來時尾端一定是完整序列。修正後同一輸入輸出 `A…`（合法），兩版 bash 一致；八個良構邊界案逐一複驗仍正確。

### 同一個 Critical 揭露的第二件事：函式註解過度承諾（一併修）

寫新測試時發現「從不產生無效 UTF-8」這個承諾**對畸形輸入本來就不可能成立**，原因有二，兩者都不是截斷造成的：

1. `${#s} <= max` 時原樣回傳——本函式不清洗輸入，畸形進、畸形出；
2. 畸形位元組若在保留前綴的**中間**（例如 `A\xffB`），前綴截斷無法處理它。

**精確的契約是**：「不因截斷而產生不完整序列」——輸出必為輸入的位元組前綴，且**尾端**必為完整序列。已把這段邊界逐字寫進函式註解取代原本的過度承諾。**這是 reviewer 指出「牴觸函式自身註解」的正解**：不是把測試放寬到看不見缺陷，而是先修掉真缺陷（尾端），再把承諾修正到與責任邊界一致。

**新測試** `test_truncate_bytes_survives_malformed_input`：六種畸形輸入（尾端 10 個／恰好 5 個連續 continuation byte、非法 lead `0xF8`、`0xFF` 夾在中間、整串以 continuation byte 開頭、單一孤立 continuation byte），上限掃過每一個切點，逐格斷言三條性質——輸出是輸入的位元組前綴、不超過上限、**尾端為完整序列**（以獨立實作的 `_ends_with_complete_sequence` 判定，不重用受測邏輯）。

### Minor（iteration 2 新引入）— summary 數字未同步（已修）

檔案表與測試覆蓋表仍寫 iteration 1 的行數與案例數。已更新為現況並標明「iteration 2 修正後」。**這是我的疏漏**：iteration 1 的 Post-review 段補了修正敘述卻沒回頭改前面的表，正是 `project.md` 反覆記載的「改動的衍生數字未同步」那一型。

### 修正後的複驗（orchestrator 自行重跑）

| 項目 | 結果 |
| --- | --- |
| stub，`/bin/bash` 3.2.57 | 34 tests, 374 checks, 0 failures |
| stub，`/opt/homebrew/bin/bash` 5.2.37 | 34 tests, 374 checks, 0 failures |
| 畸形輸入直接複驗 | `A` ＋ 10×`\x80`，max=9 → `A…`（合法 UTF-8），兩版 bash 一致 |
| 八個良構邊界案 | 逐一比對期望值，全數相符 |
| 兩支 validator | 皆 passed |
| `bash -n`（3.2 與 5.2）、`py_compile` | ok |
| live | **本輪未跑**（純函式層修正；避免在 public repo 再留 issue 編號） |

### 突變驗證（orchestrator 執行）

| # | 突變 | 結果 |
| --- | --- | --- |
| M-C | 把逐位元組收斂迴圈改回 iteration 1 的「一次算出剝除量」 | `test_truncate_bytes_survives_malformed_input` **紅**（34 tests, 374 checks, 1 failure）→ 還原 → `diff -q` 逐位元一致 → 複跑 34/374/0 |

### reviewer 的一項精度更正（如實記載）

reviewer 指出 iteration 1 突變表宣稱的「M-A 紅 3+2=5 個斷言」它三次獨立重建分別得到 21、7、4 個失敗，**未能複現該精確數字**。它判定為報告精度問題、不影響修正有效性——orchestrator 同意此判定：突變的**質性**結論（改壞→紅、還原→乾淨）三次重建皆成立，而斷言數會隨突變的寫法（改壞到什麼程度）浮動，本來就不是穩定量。**iteration 1 的那個數字應讀作「lead 那一次突變的觀測值」，不是可複現的常數。**

## Review (code-generation — iteration 3，驗證輪)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T03:32:49Z
**Iteration:** 3（驗證輪）

### 查證方法（摘要）

逐行重讀 iteration 3 Post-review 修正後的 `truncate_bytes`（`notify.sh:232-271`）與其新契約註解（`notify.sh:198-231`），手動逐位元組推導收斂迴圈對多組輸入（含良構與畸形）的行為，確認其終止性（每輪未 `break` 必剝除恰一個位元組，故迴圈必然在 `cut` 縮短至完整序列或空字串前停機，無回看視窗上限問題殘留）。獨立重跑 `run-stub-tests.py`（`/bin/bash` 3.2.57、`/opt/homebrew/bin/bash` 5.2.37），兩版皆得 **34 tests, 374 checks, 0 failures**，與 summary 逐字相符。以 `notify.sh truncate T N`（不涉 `gh` API、僅需 PATH 上有 `gh`／`jq` 之存在性檢查，本機 `/opt/homebrew/bin/gh`／`jq` 已滿足，全程零網路呼叫、零 issue 寫入）直接對函式做 summary 與既有 33 案未涵蓋的邊界輸入：iteration 2 報告的 ≥5 連續 continuation byte 案（`A`+10×`\x80`，max=9）於兩版 bash 重現輸出 `A…`（合法 UTF-8）；並依 brief 指示自行構造三類**新**畸形形狀——overlong 2-byte 編碼（`\xC0\x80`、`\xC1\xBF`）、surrogate 範圍 3-byte 序列（`\xED\xA0\x80`）、已停用的 4-byte lead（`\xF7\xBF\xBF\xBF`）——在**真實生產尺度**的截斷邊界（`DETAIL_MAX=2000`、`ERRMSG_MAX=300`，非玩具用的小 max）逐一構造「畸形序列剛好完整落在切點內」的位元組排列並以 `bytes.decode("utf-8")` 驗證，兩版 bash 一致重現無效 UTF-8（見「新發現」）。以 `LC_ALL=C sed -E` 套用與 `scrub_secrets` 逐字相同的三條規則於構造出的 payload，確認該函式不會意外遮罩或改動這些位元組（排除「後續清洗步驟會意外掩蓋此缺陷」的可能性）。在 scratchpad（`mut-verify-r3/`，隔離副本，含 `notify.sh`／`action.yml`／`run-stub-tests.py`／`run-live-tests.py` 四檔以還原完整依賴，確認乾淨基準本身即為 34/374/0 後）重建突變 M-C（把收斂迴圈改回 iteration 1 的一次性計算），兩版 bash 皆得 **34 tests, 374 checks, 1 failure**（僅 `test_truncate_bytes_survives_malformed_input` 紅），與 summary 宣稱**精確相符**；`diff -q` 還原後複跑 34/374/0。逐行核對 `_ends_with_complete_sequence`（測試檔 `935-960` 行）與 `truncate_bytes` 的分類表是否為同一份複製（見「新發現」的說明）。核對「建立的檔案」表（`12`／`14` 行）與「測試覆蓋」表（`45` 行）現況數字（`795`／`1531`／`34`／`374`）與獨立 `wc -l`／實跑結果一致，全檔搜尋確認無殘留的 `724`／`1228`／`28`／`285`／`33`／`372` 等過期數字（僅出現在歷史敘述段落，非現況表）。核對 34 個 `def test_` 與 `TESTS` 清單的 34 個項目一一對應、無重複無遺漏，且新增區塊（`935-1013` 行，79 行）與宣稱的「約新增 84 行」量級相符。全程未執行 `run-live-tests.py`、未對 public repo 做任何寫入、未修改本 repo 工作樹內任何檔案（僅在 scratchpad 建立隔離副本並於複驗後保留供稽核）。

### 逐項判定（iteration 2 的兩項發現）

| # | 原判定 | 本輪結論 | 依據 |
|---|---|---|---|
| 1（Critical，尾端連續 ≥5 個 continuation byte 時回看視窗 4 用盡、剝除量清不乾淨） | 需修 | **Resolved**——手動推導新的逐位元組收斂迴圈（每輪未達成完整序列即剝一個位元組、重新計算，故無固定回看窗上限）在數學上對任意長度的尾端 continuation byte 都能收斂到完整序列或空字串；獨立重跑 iteration 2 報告的原始反例（`A`+10×`\x80`，max=9）兩版 bash 皆得合法輸出 `A…`；34/374/0 兩版一致；八個既有良構邊界案（`😀ABC`／`測試ABC`／`café!` 全組）逐一複驗與 `TRUNCATE_CASES` 期望值相符，無回歸。**此項本輪範圍內的失效模式已確實修復。** |
| 2（Minor，`code-summary.md` 開頭「建立的檔案」表與「測試覆蓋」表行數／案例數未同步） | 已修 | **Resolved**——現況表已正確顯示 `notify.sh` 795 行、`run-stub-tests.py` 1531 行、34 案 374 斷言，與獨立 `wc -l` 及實跑結果一致；全檔搜尋確認舊數字（724/1228/28/285/33/372）僅出現在歷史敘述（Post-review 段落與本表），未殘留於現況表。 |

### 新發現

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
|---|---|---|---|---|---|
| 1 | Critical | `notify.sh:198-271`（`truncate_bytes` 的「需要位元組數」分類表，`232-271` 行；`run-stub-tests.py:935-1013` 的對應測試與 oracle） | 既存漏審（分類邏輯自 iteration 1 Post-review 起字面不變，本輪修正只改了「一次計算」→「逐位元組收斂」的**迭代機制**，未動過 `need` 的分類規則本身，故非本輪修正引入，也非 iteration 2 已判定過的項目——iteration 1、2 兩輪皆未以此類輸入測試過） | **`truncate_bytes` 對「結構上位元組數正確、但該 lead byte 值本身在 Unicode 下永遠不合法，或該 lead byte 搭配的續行位元組值落在被 RFC 3629 排除的範圍」的畸形序列，仍會誤判為「完整」而不剝除，因而在真實生產尺度的截斷邊界上產生無效 UTF-8**——與函式自身新寫的精確契約（`notify.sh:201-202`：「保證『不因截斷而產生不完整序列』……且其尾端必為完整序列」）矛盾，且與 `test_truncate_bytes_survives_malformed_input` 的 `@purpose`（「斷言的是責任邊界內的契約：輸出必為輸入的位元組前綴，且尾端必為完整序列」）用同一把 oracle（`bytes.decode("utf-8")`）量測時不成立。根因：`need` 的分類只檢查 lead byte 落在哪個**寬泛區間**（`\xC0`-`\xDF`→2、`\xE0`-`\xEF`→3、`\xF0`-`\xF7`→4）與續行位元組**數量**是否相符，從不檢查（a）`\xC0`／`\xC1` 這兩個值作為 2-byte lead **永遠**只能編碼 overlong（U+0000–U+007F 本該用 1 byte）、根本不是合法 lead；（b）`\xF5`-`\xF7` 作為 4-byte lead 編碼的碼點必超過 U+10FFFF（Unicode 上限，僅 `\xF0`-`\xF4` 合法）、同樣永遠不合法；（c）`\xE0`／`\xED`／`\xF0`／`\xF4` 之後的**特定**續行位元組範圍限制（分別排除 overlong 3-byte、surrogate 範圍、overlong 4-byte、超出上限的 4-byte）。凡「lead byte 屬於上述永遠非法值，或屬於條件非法組合，但續行位元組**數量**剛好等於分類表期待的數量」的畸形輸入，`k == need` 成立，函式判定「完整、不砍」，原樣連同省略號一起輸出。**本站以三組獨立輸入、在函式實際使用的兩個真實常數（`DETAIL_MAX=2000`、`ERRMSG_MAX=300`，非玩具小 max）上構造「畸形序列剛好落在切點」，兩版 bash（3.2.57、5.2.37）一致重現：**(1) `1998 個 'A' + \xC0\x80 + 'TAIL_SHOULD_BE_CUT'`（共 2018 位元組）以 `truncate 2000` 呼叫，輸出尾端為 `...A\xc0\x80\xe2\x80\xa6`，`bytes.decode("utf-8")` 於 position 1998 拋 `invalid start byte`；(2) 同一 payload 在 max=2（玩具尺度）另得 `\xc0\x80\xe2\x80\xa6`，同樣的 `UnicodeDecodeError`；(3) `297 個 'B' + \xED\xA0\x80（surrogate D800）+ 'TAIL'` 以 `truncate 300` 呼叫（`ERRMSG_MAX` 的真實值），輸出尾端 `...BBBB\xed\xa0\x80\xe2\x80\xa6`，於 position 297 拋 `invalid continuation byte`；(4) `\xF7\xBF\xBF\xBF`（已停用的 4-byte lead，續 3 個合法範圍的 continuation byte）以 max=4（剛好完整落在切點內）呼叫，輸出 `\xf7\xbf\xbf\xbf\xe2\x80\xa6`，於 position 0 拋 `invalid start byte`。另以 `LC_ALL=C sed -E` 對案例 (1) 套用與 `scrub_secrets` 逐字相同的三條規則，確認輸出與輸入位元組級相同（該函式不處理非 ASCII 樣式的位元組，不會意外遮罩或改動這個缺陷，排除「後續清洗步驟碰巧補救」的可能）。**既有 33 案（含 iteration 2／3 新增的 5 案）結構上永遠碰不到這個分支**：`TRUNCATE_CASES` 與 `test_truncate_bytes_output_is_always_a_maximal_valid_prefix` 用的探測文字（`"測試😀café!ABC。"`）與 `test_truncate_bytes_survives_malformed_input` 的六組畸形案例（尾端連續 continuation byte、非法 lead `\xF8`、孤立 continuation byte）皆不含 `\xC0`／`\xC1`／`\xF5`-`\xF7` 這類「結構完整但語意非法」的 lead byte，也不含任何 overlong／surrogate／超界的續行位元組組合——因為前者是由合法 Unicode 字元編碼而來（合法編碼器不可能產生這些位元組），後者鎖的是「回看視窗上限」這一種**不同**的失效模式（迭代收斂與否），兩組測試在設計上就不會經過這個分類分支。**測試自己的 oracle 也共享同一個盲點**：`_ends_with_complete_sequence`（`run-stub-tests.py:935-960`）與 `truncate_bytes` 用的是**同一張**寬泛區間分類表（逐行核對：`0x80<=b<=0xBF`→continuation、`b<=0x7F`→need=1、`0xC0<=b<=0xDF`→need=2、`0xE0<=b<=0xEF`→need=3、`0xF0<=b<=0xF7`→need=4，與 `notify.sh` 的 case 樣式逐值相同），這使得 oracle 在「機制」上獨立於受測邏輯（單次判定 vs 逐位元組收斂），但在「分類定義」上與受測邏輯**共享同一個盲點**——若真的把這幾個反例塞進既有的畸形輸入掃描測試，oracle 會與函式一起誤判為「完整」，測試不會紅。這正是 `project.md` 對測試獨立性要求的字面意義（「它若複製了 notify.sh 的判定，兩邊一起錯就測不出來」）在此處成立的具體實例。實際可達性：`detail`／`errmsg` 的真實資料來源是 `gh` 子命令 stderr 與呼叫端組出的字串，overlong／surrogate 編碼在**刻意構造**的輸入中才會出現，但也是**編碼不一致**（非 UTF-8-aware 的工具把 Latin-1／CP1252 位元組原樣輸出，例如 `\xC0` 恰是 CP1252 的 'À'）這種常見真實故障模式的典型特徵，並非純理論建構；且與 iteration 1／2 兩個 Critical 屬同一 SEC-2 邊界（`detail`／`errmsg` 寫入**公開** issue 前的最後一關，ADR-0006 audit logging 面向）。 | 不要只檢查「續行位元組數量是否等於分類表期待值」，須額外排除：(a) lead byte 本身永遠非法的值（`\xC0`、`\xC1`、`\xF5`-`\xFF`）一律歸入 `need=0`（非法 lead），不論其後跟了幾個 continuation byte；(b) 對 `\xE0`（續行首位元組須 `\xA0`-`\xBF`，否則 overlong）、`\xED`（續行首位元組須 `\x80`-`\x9F`，否則落入 surrogate 範圍）、`\xF0`（續行首位元組須 `\x90`-`\xBF`，否則 overlong）、`\xF4`（續行首位元組須 `\x80`-`\x8F`，否則超過 U+10FFFF）額外檢查緊接在 lead 之後的那個位元組是否落在該 lead 專屬的合法子範圍內。或改用等價但更不易出錯的做法：呼叫 runner 上已存在的 `python3`（`step_run_python_diagnostics` 一類，或直接 `printf '%s' "$cut" | python3 -c 'import sys;sys.stdout.buffer.write(sys.stdin.buffer.read().decode("utf-8","strict").encode())' 2>/dev/null` 式的往返驗證）在剝除迴圈的「判斷完整」那一步做真正的 strict-UTF-8 驗證，取代手刻的 case 分類表——bash 3.2 case 樣式的分類天花板已經連續兩輪（iteration 2、3）在邊界處出錯，而 strict 解碼器是這個問題的權威定義，不需要重新發明。並補上至少三案（overlong `\xC0\x80`、surrogate `\xED\xA0\x80`、已停用 lead `\xF7\xBF\xBF\xBF`）覆蓋此分支，且務必包含「剛好落在 `DETAIL_MAX`／`ERRMSG_MAX` 真實邊界」的至少一組，不只用玩具 max。 |

### Attempted refutations that did not hold

- **懷疑這是 scrub_secrets／single_line 的清洗副作用意外掩蓋或觸發，而非 truncate_bytes 本身的獨立缺陷**：以 `LC_ALL=C sed -E` 套用與 `scrub_secrets` 逐字相同的三條規則於構造出的 overlong payload，輸出與輸入位元組級完全相同（`diff` 確認一致）——確認缺陷完全落在 `truncate_bytes` 本身，與 `scrub_secrets`／`single_line` 無關，也不是清洗步驟順序造成的。**判定：獨立於 SEC-2 清洗鏈的其餘部分，是 `truncate_bytes` 自身的分類缺陷。**
- **懷疑這三組反例只是玩具 max 下的人工產物，真實 `DETAIL_MAX=2000`／`ERRMSG_MAX=300` 下不會剛好命中邊界**：以 2018 位元組（`DETAIL_MAX=2000`）與 304 位元組（`ERRMSG_MAX=300`）的 payload、精確計算 padding 長度使畸形序列剛好落在真實截斷點，兩版 bash 皆重現。**判定：在函式實際使用的真實常數下可達，非玩具限定的產物。**
- **懷疑 `truncate` 診斷子命令的直接呼叫與 `scrub_detail`／`scrub_errmsg` 實際呼叫路徑不等價（例如少了某層轉換而導致假陽性）**：核對 `scrub_detail`（`notify.sh:375-380`）／`scrub_errmsg`（`382-387`）的呼叫序列（`single_line` → `scrub_secrets` → `truncate_bytes`），確認 `single_line`（只換 `\r`／`\n`）與 `scrub_secrets`（sed 規則，上一條已排除影響）皆不改動這些位元組，故 `truncate_bytes "$s" "$MAX"` 收到的 `$s` 與本站直接呼叫 `truncate` 診斷子命令的輸入位元組級相同。**判定：診斷子命令是真實呼叫路徑的忠實代理，非測試假象。**
- **獨立複驗 M-C 突變的精確斷言數「1 failure」**：第一次在 scratchpad 重建時因缺少 `run-live-tests.py`（`test_every_test_carries_spec_annotations` 依賴它）與 `cut=""`/`k>len(cut)` 邊界的手工實作疏漏，得到 2 failures／351 checks 的雜訊結果；補齊四份依賴檔並修正手工實作後的**第三次**重建精確得到 **34 tests, 374 checks, 1 failure**，與 summary 逐字相符，`diff -q` 還原後複跑 34/374/0。**判定：屬實，前兩次的落差是本站重建腳本的環境／實作瑕疵，非 M-C 宣稱本身的問題。**
- **iteration 2 報告的原始反例（≥5 連續 continuation byte）是否真的收斂**：獨立重跑 `A`+10×`\x80`、max=9，兩版 bash 皆得 `A…`，與 Post-review 段落宣稱逐字相符。**判定：屬實，此類失效模式已修復。**

### 三類計數

新引入：0 項、既存漏審：1 項（新發現 Critical #1）、新設計問題：0 項。

### Summary

Iteration 2 的兩項發現本輪逐一複驗：Critical（回看視窗固定 4、尾端 ≥5 個 continuation byte 清不乾淨）**已確實修復**——新的逐位元組收斂迴圈在數學上無回看視窗上限，八個既有良構邊界案與 iteration 2 的原始反例皆複驗吻合，兩版 bash 一致，34/374/0 全數通過；Minor（summary 數字過期）**已同步**，現況表與獨立複驗一致。M-C 突變重建三次後精確得到與 summary 逐字相符的「34/374/1」，質性與量化宣稱皆確認。

**但本輪依 brief 指示主動構造的三類新畸形形狀（overlong 2-byte、surrogate 3-byte、已停用的 4-byte lead）在 `truncate_bytes` 的真實生產截斷邊界（`DETAIL_MAX=2000`、`ERRMSG_MAX=300`）上仍會產生無效 UTF-8**，兩版 bash 一致重現，且已排除清洗鏈其餘部分與診斷子命令代理性的干擾可能。根因是 `need` 分類表只驗證「續行位元組數量」，從未驗證「lead byte 本身是否為永遠非法值」或「續行位元組是否落在該 lead 專屬的合法子範圍」——這是一個**獨立於**（既非同一個、也非本輪修正引入）iteration 1、2 兩個已修復 Critical 的第三種失效模式，兩輪既有測試在設計上（探測文字皆為合法 Unicode 編碼而來）結構上永遠碰不到它，且新測試自己的 oracle（`_ends_with_complete_sequence`）與受測邏輯共享同一張分類表、對此類輸入會與函式一起誤判，無法自行揭穿。與 iteration 1／2 屬同一 SEC-2 邊界（`detail`／`errmsg` 寫入公開 issue 前的最後一關），實際可達性以編碼不一致（如 Latin-1／CP1252 位元組原樣流入）最為典型，非純理論建構。判定 **NOT-READY**——建議的具體修法（排除永遠非法的 lead byte 值、檢查續行位元組的條件式合法子範圍，或改用 strict UTF-8 解碼器取代手刻分類表）已寫入建議欄，且分類為「既存漏審」而非「本輪修正引入」，故不與 `application-design:c4` 的强制驗證輪要求牴觸；是否值得為此再開一輪聚焦驗證，或以「開放項目＋指派」形式記入 Bolt gate（比照本檔既有對 Major #2／Minor #1 的處置形狀），留給 orchestrator 與人工 gate 決定。

## Post-review 修正（iteration 3 驗證輪，2026-09-05T03:41:32Z）

驗證輪判 **NOT-READY**（新引入 0／**既存漏審 1 Critical**／新設計問題 0）。iteration 2 的兩項發現皆判 **Resolved**（reviewer 獨立重跑 34/374/0、獨立重建 M-C 突變得 34/374/1 且僅新測試紅、還原後 `diff -q` 一致）。本輪的 Critical 是**自 iteration 1 起就存在、前兩輪都沒看到**的另一個缺陷。

### Critical（既存漏審）— 分類表只驗長度、不驗編碼合法性（已修）

**orchestrator 獨立複驗，三個反例在兩版 bash 全數重現**（reviewer 刻意用**生產常數**而非玩具上限構造，這一點很重要——它排除了「只在小 max 才出現」的辯解）：

| 反例 | 上限 | 修正前 | 修正後 |
| --- | --- | --- | --- |
| `1998×'A'` ＋ overlong `C0 80` ＋ 尾段 | 2000（`DETAIL_MAX`） | `invalid start byte` | 解碼 OK |
| `297×'B'` ＋ surrogate `ED A0 80` ＋ 尾段 | 300（`ERRMSG_MAX`） | `invalid continuation byte` | 解碼 OK |
| `F7 BF BF BF ZZ`（已停用的 4-byte lead） | 4 | `invalid start byte` | 解碼 OK |

**根因**：分類表問的是「這個 lead byte 說要幾個位元組」，答對了長度就放行。UTF-8 的合法性不只是長度——三類序列長度對但編碼非法：

- **overlong**：`C0`／`C1` 這兩個 lead 永遠非法（它們編出的碼位用更短的序列就能表示）；
- **surrogate**：`ED` 之後只允許 `80-9F`，`A0-BF` 落在 UTF-16 代理對區間，UTF-8 不得編碼；
- **超出上界**：`F5` 起已停用；`F0` 之後未達 `90`（overlong）、`F4` 之後超過 `8F`（超過 U+10FFFF）同樣非法。

**修法（orchestrator 執筆）**：把「lead byte → 需要幾個位元組」的表換成**完整的 UTF-8 合法性表**——直接用 case 樣式比對最後 k 個位元組是否構成一個合法字元，`E0`／`ED`／`F0`／`F4` 的條件式第二位元組子範圍逐一寫出。收斂迴圈的形狀不變（尾端不合法就丟一個位元組再看一次），只是判定從「數長度」升級為「驗合法性」。函式註解的契約同步由「尾端必為完整序列」改為「**尾端必為一個合法的 UTF-8 序列**」。

### reviewer 指出的方法論缺陷（同輪一併修，這一項比缺陷本身更要緊）

`_ends_with_complete_sequence`（測試的 oracle）**與受測邏輯共用同一張只數長度的表**，所以兩邊對這三類序列**一起誤判**——測試結構上無法揭穿自己。這是「用受測對象當自己的裁判」的典型形狀。

**修法**：oracle 改名為 `_tail_is_a_valid_sequence`，改以 **Python 自己的 UTF-8 解碼器**判定（`data[-k:].decode("utf-8")` 且長度為 1），完全不重用 `notify.sh` 的分類表。Python 的解碼器會拒絕 overlong／surrogate／超界，因此它是獨立的權威。**這個改動的價值不只修一次缺陷**：它讓這組測試從此有能力抓分類表的錯，而先前沒有。

### 新增測試

- `test_truncate_bytes_survives_malformed_input` 由 6 種畸形輸入擴為 **9 種**（加入 overlong `C0 80`、surrogate `ED A0 80`、已停用 lead `F7`），oracle 換成獨立版。
- 新增 `test_truncate_bytes_rejects_invalid_sequences_at_production_limits`：把三個歷史反例釘在**生產常數**（2000／300）上，避免日後有人以「只在小 max 出現」為由放寬分類表。

### 複驗與突變（orchestrator 自行執行）

| 項目 | 結果 |
| --- | --- |
| stub，`/bin/bash` 3.2.57 | 35 tests, 381 checks, 0 failures |
| stub，`/opt/homebrew/bin/bash` 5.2.37 | 35 tests, 381 checks, 0 failures |
| 三個反例直接複驗 | 兩版 bash 皆解碼 OK（上表） |
| 八個良構邊界案 | 逐一比對期望值，全數相符（無回歸） |
| 兩支 validator | 皆 passed |
| **突變 M-D** | 分類表改回只數長度（放行 `C0`／`C1`、`ED` 的 surrogate、`F5`-`F7`）→ **兩個新測試皆紅**（35 tests, 381 checks, **4 failures**）→ 還原 → `diff -q` 逐位元一致 → 複跑 35/381/0 |

### 本輪的停止判準（依 `project.md` 的 `functional-design:c18`，於下一輪**開始前**訂定）

三輪各出一個 Critical，全部落在同一個函式。但缺陷來源不同：iteration 2 的是**上一輪修正留下的缺口**，iteration 3 的是 **`既存漏審`**（自 iteration 1 起字面未變，前兩輪沒看到）。修正動作本身沒有在製造新缺陷，是審查在挖深——依 c18 這是「該再跑一輪」而非「該停止」的訊號。

**下一輪（iteration 4，仍為驗證輪、不計入原始上限）的停止判準，現在訂好**：

- 若它找到的 Critical 是**本輪修正引入的** → 修，再驗一輪。
- 若它找到的 Critical 又是**既存漏審**（即這個函式還有第四個獨立缺陷）→ **停止迴圈**，把該項寫成 open item 帶進 Bolt 1 gate 由人裁決，並在那裡揭露「同一個函式已連續四輪各出一個 Critical」這個事實本身——那時要決定的就不是再修一次，而是這個函式該不該換一個實作策略（例如把截斷改到呼叫端以 Python 完成，或乾脆不截斷而由 GitHub 的 API 拒絕）。
- 若它只找到 Major 以下 → 收斂，進 gate。

**這一輪的結構性改善使上述判準有意義**：oracle 已獨立，測試從此抓得到分類表的錯——先前三輪之所以能連續漏掉，正是因為裁判與受測對象共用同一張表。

## Review (code-generation — iteration 4，驗證輪)

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T04:00:25Z
**Iteration:** 4（驗證輪）

### 查證方法（摘要）

逐位元組手算 `notify.sh:198-277` 全部 20 個八進位字面量（`\001`／`\177`／`\302`／`\337`／`\200`／`\277`／`\340`／`\240`／`\341`／`\354`／`\355`／`\237`／`\356`／`\357`／`\360`／`\220`／`\361`／`\363`／`\364`／`\217`）換算成十六進位，逐一對照 RFC 3629 Table 3-7 的九條規則（`C2-DF`＋`80-BF`；`E0`＋`A0-BF`＋`80-BF`；`E1-EC`＋`80-BF`×2；`ED`＋`80-9F`＋`80-BF`；`EE-EF`＋`80-BF`×2；`F0`＋`90-BF`＋`80-BF`×2；`F1-F3`＋`80-BF`×3；`F4`＋`80-8F`＋`80-BF`×2），並以 Python 腳本重算全部 20 組換算，逐一相符、零誤差（見下方「Attempted refutations」）。

構造 10 組邊界反例（每一條規則的上下限各一組：`C1 BF` vs `C2 80`、`E0 9F BF` vs `E0 A0 80`、`ED 9F BF` vs `ED A0 80`、`F0 8F BF BF` vs `F0 90 80 80`、`F4 8F BF BF` vs `F4 90 80 80`），每組附加尾段使真正觸發截斷（非「長度剛好等於上限」的假陽性），對 `notify.sh truncate` 直接呼叫（不經 `gh` API，純函式探針），兩版 bash（`/bin/bash` 3.2.57、`/opt/homebrew/bin/bash` 5.2.37）各測一輪：全數 10 組皆與 RFC 3629 期望一致，兩版逐位元組相同。

以獨立探測文字（`"Zµ你🎉Ω श ABC𠀀!"`，涵蓋 1/2/3/4 位元組字元，與既有 `test_truncate_bytes_output_is_always_a_maximal_valid_prefix` 用的探測文字不同）掃過全部切點（`max_bytes` 從 0 到總長 +2），兩版 bash 皆 0 違反（合法、前綴、不超限、最長前綴四條性質全數成立）。

**窮舉測試（超出既有 35 案與 brief 建議範圍）**：抽出 `truncate_bytes` 函式本體（`notify.sh:233-277` 逐字複製，非改寫）到獨立腳本，在單一 bash 行程內窮舉呼叫（不逐次起行程，避開子行程開銷）：(a) 對每一個可能的 lead byte 值（1–255，扣除 bash 無法表示的 NUL）在 k=1/2/3/4 四種深度下各建構一組輸入（後續位置固定填合法延續位元組 `\200`），共 1020 組；(b) 對四個條件式 lead byte（`E0`／`ED`／`F0`／`F4`）的**第二位元組**窮舉 1–255 全部值、其餘位置固定 `\200`，共 1020 組。兩版 bash 各執行全部 2040 組（`time` 量測約 65 秒／64 秒，全在單一 bash 行程內完成），以 Python 對每組結果驗證四條性質（合法 UTF-8、位元組前綴、不超限、真正的最長前綴——後者以獨立方式重算「該上限下的真實最大合法前綴長度」逐一比對，不重用 `notify.sh` 的分類邏輯）。**在條件式規則的真實定義域內**（即 (b) 組的第二位元組落在延續位元組範圍 `128–191` 內，這才是 `E0`／`ED`／`F0`／`F4` 條件檢查真正要區分的情況）：2040 組窮舉**零違反**，兩版 bash 逐組輸出**逐位元組相同**（0 個交叉版本不一致）。(b) 組第二位元組落在 `128–191` **之外**的 654 組確實出現「輸出非合法 UTF-8」，但逐一核對後，那些組的**原始輸入本身**在該位置就已經是畸形 UTF-8（例如 `E0 01 80`：`01` 不是延續位元組，這個 3-byte 候選序列從一開始就不成立，與 `E0` 的 overlong 限制完全無關），命中的正是函式註解明文排除的「輸入自己中間就有的畸形位元組不在本函式責任內」——這是我建構掃描時把第二位元組掃過整個 0–255 而非侷限在其應有定義域（延續位元組 `80-BF`）的方法論瑕疵，不是函式的缺陷；篩掉定義域外的組別後即為上述「零違反」。

獨立以 20000 組隨機位元組（`random.seed(42)`，長度 0–8）加 15 組手工邊界案，對 `_tail_is_a_valid_sequence`（`run-stub-tests.py:935-953`）做差分測試——用另一個獨立寫法（由長至短搜尋 k=4→1，而非受測程式的由短至長 k=1→4）逐組比對，**零不一致**；並核對其判定所憑藉的位元組值域（continuation `80-BF` vs 其餘 lead byte 值域 `00-7F`／`C2-FF`）彼此不重疊，證明它不可能對真正合法的多位元組序列給出假陽性。

重建 M-D（`需要位元組數`分類表退回只數長度，放行 `C0`／`C1`、`ED` 的 surrogate、`F5`-`F7`）：兩版 bash 皆得 **35 tests, 381 checks, 4 failures**，與 iteration 3 宣稱**精確相符**（非僅質性）；`diff -q` 還原後複跑 35/381/0。

依 brief 指示自行設計**三個新突變**（僅各自窄化一條規則，其餘維持修正後版本）：M-E（只放寬 `ED` 的 surrogate 排除，改為全放行 `80-BF`）→ 兩版 bash 皆 **35 tests, 381 checks, 2 failures**，被抓到；M-F（只放寬 `F4` 的上界，改為全放行 `80-BF`）→ 兩版 bash 皆 **35 tests, 381 checks, 0 failures**，**未被任何測試抓到**；M-G（只放寬 `E0` 的 overlong 排除，改為全放行 `80-BF`）→ 兩版 bash 皆 **0 failures**，**未被抓到**；M-H（只放寬 `F0` 的 overlong 排除）→ 兩版 bash 皆 **0 failures**，**未被抓到**。四次重建皆 `diff -q` 還原後複跑 35/381/0 一致。

實測效能：`DETAIL_MAX=2000`／`ERRMSG_MAX=300` 兩個生產常數下的最壞情況（`cut` 視窗內尾端全為連續 delegation byte，收斂迴圈逐位元組剝除），各 5 次量測取中位數，並以「無需截斷的瑣碎輸入」為基準扣除行程啟動開銷。

獨立複驗 `notify.sh` 795→**801** 行、`run-stub-tests.py` 1531→**1550** 行（`wc -l` 實測），兩版 bash 各跑 `run-stub-tests.py`：**35 tests, 381 checks, 0 failures**。全程未執行 `run-live-tests.py`、未對 public repo 做任何寫入、未修改本 repo 工作樹內任何檔案（全部窮舉腳本、重建、突變皆在 scratchpad 隔離副本內進行）。本目錄（`.github/actions/aidlc-sync-notify/`）於版控中為全新未追蹤路徑（`git status --short` 顯示 `??`），無先前提交可供 `git diff` 比對「既有測試是否被改動」；改以結構性核對取代（見「Attempted refutations」）。

### 逐項判定（iteration 3 的發現）

| # | 原判定 | 本輪結論 | 依據 |
|---|---|---|---|
| 1（Critical，分類表只驗長度、不驗編碼合法性——overlong／surrogate／超界序列被放行） | 已修 | **Resolved，且驗證強度遠超原文回報的三個反例**。手算並以 Python 複算全部 20 個八進位字面量，逐一對照 RFC 3629 Table 3-7 全部九條規則，零誤差；獨立構造 10 組邊界反例（規則上下限各一）於兩版 bash 皆與期望相符；**進一步窮舉 2040 組**（涵蓋全部 255 個可能 lead byte 值於 k=1-4 四種深度、加上四個條件式 lead byte 的第二位元組於其真實定義域 `80-BF` 內的全部 64 個值）於兩版 bash 皆零違反、零版本間不一致。此為本輪在 reviewer 查證範圍內對這個函式做過最完整的一次驗證，未發現任何殘留的分類錯誤。 |
| 2（Minor，`_tail_is_a_valid_sequence` oracle 與受測邏輯共用同一張表的方法論缺陷） | 已修（改用 Python 解碼器） | **Resolved，並獨立驗證 oracle 本身無 bug**。以 20000 組隨機位元組＋15 組手工邊界案對 oracle 做差分測試（另一個獨立寫法：由長至短搜尋），零不一致；核對其分支所憑藉的位元組值域彼此不重疊（continuation byte 範圍與各類 lead byte 範圍無交集），這在數學上排除了它對合法序列給出假陽性或假陰性的可能。 |

### 新發現

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
|---|---|---|---|---|---|
| 1 | Major | `run-stub-tests.py:956-1031`（`test_truncate_bytes_survives_malformed_input`／`test_truncate_bytes_rejects_invalid_sequences_at_production_limits`） | 新引入（這四條條件式合法性限制本身是 iteration 3 的修正才新增的程式碼分支——iteration 2 及之前的分類表完全沒有 `E0`／`ED`／`F0`／`F4` 的第二位元組子範圍檢查；iteration 3 的同一次修正只為其中一條（`ED` 的 surrogate 排除）寫了對稱的測試案例，另外三條——`E0`／`F0` 的 overlong 排除、`F4` 的超界排除——沒有任何案例覆蓋，屬同一個修正動作內部「契約有一端懸空」的形狀，非既存漏審） | **`notify.sh:198-277` 的分類表對 `E0`／`F0`／`F4` 三條條件式限制（`overlong`／`overlong`／`超出 U+10FFFF`）目前**沒有任何測試**會在該限制被誤放寬時變紅**——只有 `ED` 的 surrogate 排除有對稱測試（`test_truncate_bytes_survives_malformed_input` 的 `surrogate 編碼 ED A0 80` 案、`test_truncate_bytes_rejects_invalid_sequences_at_production_limits` 的 `surrogate ED A0 80 @ ERRMSG_MAX` 案）。以三個獨立突變逐一證實：M-F（只放寬 `F4` 的上界為全 `80-BF`，等同放行超過 U+10FFFF 的序列）於兩版 bash 皆得 **35 tests, 381 checks, 0 failures**；M-G（只放寬 `E0` 的 overlong 排除為全 `80-BF`）兩版皆 **0 failures**；M-H（只放寬 `F0` 的 overlong 排除為全 `80-BF`）兩版皆 **0 failures**——三者皆與 M-E（只放寬 `ED`，被 2 個斷言抓到）及 M-D（全部放寬，被 4 個斷言抓到）形成對照，唯獨 `E0`／`F0`／`F4` 這三條在被單獨、精準地拆除時完全無聲。**這不是目前程式碼的缺陷**——本輪窮舉 2040 組（含這三條規則的真實定義域內全部第二位元組值）確認現行分類表在其定義域內完全正確，且 M-F/G/H 的突變本身不對，只是驗證了「即使改錯也不會被發現」。但鑑於這支函式已連續四輪（iteration 1、2、3、本輪窮舉才發現）在「看似已修好」之後仍藏著下一層的邊界問題，這個測試覆蓋缺口本身構成後續任何一次「順手精簡分類表」或「調整範圍」的編輯都可能無聲重新引入 iteration 3 剛修好的那三類非法序列（overlong 3-byte／overlong 4-byte／超出 Unicode 上界）——而 35 個測試會全數維持綠燈。 | 為 `E0`／`F0`／`F4` 各補一組測試案例，形狀比照既有 `ED` 覆蓋（`test_truncate_bytes_survives_malformed_input` 的 `surrogate 編碼 ED A0 80` 案與 `test_truncate_bytes_rejects_invalid_sequences_at_production_limits` 的生產常數案）：`E0 9F BF`（overlong 3-byte，`9F` 恰在 `A0` 下緣之外一格）、`F0 8F BF BF`（overlong 4-byte，`8F` 恰在 `90` 下緣之外一格）、`F4 90 80 80`（超出 U+10FFFF，`90` 恰在 `8F` 上緣之外一格）——三組皆為「差一格」的精確邊界值，而非任意落在非法範圍內的值，確保測試鎖住的是規則本身的邊界而非規則的某個內部點。成本低（純增補測試，程式碼不需改動，本輪已證實現行程式碼正確）、風險收益比高（鎖住的正是這支函式歷史上反覆出錯的那一類邊界）。是否本輪由 lead 直接補上，或列為 open item 隨其餘兩項既有指派（Major #2／Minor #1）一併帶進 Bolt 1 gate，留給 orchestrator 決定——兩種處置都不影響本輪 READY 判定，因為現行程式碼本身沒有缺陷。 |

### Attempted refutations that did not hold

- **懷疑窮舉掃描的 654 個「違反」是真缺陷**：逐一核對後，全部 654 組的第二位元組值都落在延續位元組範圍（`80-BF`）**之外**（例如 `E0 01 80` 的 `01`），意即這些輸入從一開始（截斷發生前）就已經是畸形 UTF-8，與 `E0`／`ED`／`F0`／`F4` 的條件式限制毫無關係，命中的是函式註解明文排除的「輸入自己中間就有的畸形位元組不在本函式責任內」。這是我建構第二位元組掃描時掃過整個 0–255（而非其應有定義域 `80-BF`）的方法論瑕疵；篩掉定義域外的組別後，條件式限制的真實定義域內（`128-191`，共 4×64=256 組，含於前述 2040 組中）零違反。**判定：測試方法論產物，非函式缺陷。**
- **懷疑 20 個八進位字面量換算有誤（reviewer brief 明文要求逐一核對）**：以 Python 重算全部 20 組八進位轉十六進位，與手算結果、與 RFC 3629 Table 3-7 對應規則的十六進位值三方比對，**零誤差**。**判定：換算正確，非缺陷。**
- **懷疑 `_tail_is_a_valid_sequence` oracle 本身有 bug（brief 明確要求檢查 `len(...decode())==1` 這個判準對哪些輸入會誤判）**：20000 組隨機位元組＋15 組手工邊界案，用獨立寫法（由長至短搜尋而非受測程式的由短至長）差分測試，零不一致；並證明其判定所憑藉的位元組值域彼此不重疊，數學上排除假陽性／假陰性。**判定：oracle 無 bug，非缺陷。**
- **懷疑效能構成實際問題**：`DETAIL_MAX=2000` 全連續延續位元組的最壞情況（`cut` 視窗尾端 1999 個延續位元組需逐一剝除）實測中位數約 250ms（`/opt/homebrew/bin/bash` 5.2.37）～360ms（`/bin/bash` 3.2.57，扣除約 10ms 的行程啟動基準後）；`ERRMSG_MAX=300` 的等價最壞情況約 40-45ms。這是**單次呼叫**（每個 workflow step 呼叫一次，非迴圈重複呼叫）、且觸發條件本身極端（`detail`／`errmsg` 近乎全部由連續延續位元組組成，真實故障模式如 Latin-1 洩漏通常只是零星幾個非法位元組夾雜在正常文字中，不會是連續近 2000 個）。**判定：次秒級、單次呼叫、觸發條件為理論上界而非常見情境，不構成實際問題，非缺陷。**
- **懷疑 M-D 突變重建的斷言數「4 failures」與 iteration 3 宣稱不符**：獨立重建（分類表完整退回只數長度，放行 `C0`／`C1`／`ED` 的 surrogate／`F5`-`F7`），兩版 bash 皆精確得到 **35 tests, 381 checks, 4 failures**，與 iteration 3 Post-review 段落宣稱逐字相符。**判定：屬實，非缺陷。**
- **懷疑既有測試在本輪查證過程中被意外改動**：本目錄在版控中為全新未追蹤路徑（`git status --short` 確認 `??`），沒有先前提交可供 `git diff`；改以結構性核對取代——`TESTS` 清單（`run-stub-tests.py:1486-1522`）逐一核對 35 個項目與其 `def test_` 定義一一對應、無重複無遺漏，且全程僅在 scratchpad 建立隔離副本，未對本 repo 工作樹寫入任何位元組（`diff -q` 逐次確認 scratchpad 副本與原檔在還原後一致）。**判定：本輪查證方法可交代其限制（無 git 歷史可比對），但結構性證據顯示測試檔在本輪查證過程中未被本 reviewer 改動；至於本輪之前、lead 在 iteration 3 修正時是否改動了 iteration 2 的既有測試本體，屬 iteration 3 自陳範圍，已於該輪 Post-review 段落自述變動內容（新增 5 案），本輪未發現與該自述矛盾之處。**

### 三類計數

新引入：1 項（Major #1，測試覆蓋缺口）、既存漏審：0 項、新設計問題：0 項。

### Summary

Iteration 3 的兩項發現本輪逐一複驗，且驗證強度超出原文回報範圍：Critical（分類表只驗長度）**已確實修復**——不只複現原本三個反例（overlong `C0 80`、surrogate `ED A0 80`、已停用 lead `F7`）皆解碼成功，更以 2040 組窮舉（涵蓋全部 255 個 lead byte 值於四種深度、四個條件式 lead byte 的第二位元組於其真實定義域內的全部 64 個值）證明分類表在其完整定義域內零違反、兩版 bash 逐組一致；Minor（oracle 與受測邏輯共用同一張表）**已確實修復**——新 oracle 以 20000 組隨機模糊測試＋15 組邊界案獨立驗證無 bug。

**本輪唯一的新發現是 Major 等級的測試覆蓋缺口，而非功能缺陷**：`E0`／`F0`／`F4` 三條 iteration 3 才新增的條件式合法性限制，只有其中一條（`ED`）有對稱的迴歸測試；以三個新突變（M-F／M-G／M-H，各自只放寬一條規則）逐一證實，放寬 `E0`／`F0`／`F4` 任何一條都不會讓現有 35 個測試中的任何一個變紅，而放寬 `ED`（M-E）或全部放寬（M-D）都會被抓到。現行程式碼本身經窮舉驗證是正確的——這是「已修好但沒有全部鎖住」的形狀，鑑於此函式的四輪歷史（每一輪「已修」之後都在更深的邊界發現下一層問題），這個覆蓋缺口具體、可還原、修法明確且成本低（三組新測試案例，程式碼不需改動）。

依本輪開始前訂定的停止判準：本輪未發現 Critical（既非本輪修正引入，亦非既存漏審），只發現 Major 以下的發現——**收斂進 gate**。建議把新發現的 Major（測試覆蓋缺口）與既有的 Major #2（批次鍵介面 vs U-6 `business-rules.md`）、Minor #1（`domain-entities.md`／`business-rules.md` 未同步 `Failed` 碼）一併帶進 Bolt 1 gate 由人裁決是否本輪由 lead 直接補上三組測試（成本低、不改程式碼）或列為 open item 延後處理；兩種處置皆不影響本判定。判定 **READY**。

## Post-review 修正（iteration 4 驗證輪，2026-09-05T04:09:56Z）

驗證輪判 **READY**（新引入 1 Major／既存漏審 0／新設計問題 0）。依既定停止判準——**未發現 Critical，只有 Major 以下 → 收斂進 gate**。iteration 3 的兩項發現皆判 Resolved，且 reviewer 的複驗遠比要求的徹底：**2040 組窮舉**（255 個 lead byte 值 × 4 種深度，加上 `E0`／`ED`／`F0`／`F4` 四個條件式 lead 在其定義域內的全部 64 個第二位元組值），兩版 bash 逐組一致零違反；20 個八進位字面量逐一換算核對 RFC 3629 Table 3-7 零誤差；新 oracle 以 20000 組隨機模糊測試加 15 組邊界案獨立驗證。

### Major（新引入）— 三條條件式規則沒有對稱測試（已修）

reviewer 用突變逐條驗覆蓋，結果**現行程式碼是對的，但測試抓不到它被改壞**：

| 突變 | reviewer 實測 | 補測後（orchestrator 複驗） |
| --- | --- | --- |
| M-E 放寬 `ED`（允許 surrogate） | 2 failures ✅ 抓得到 | 2 failures |
| M-G 放寬 `E0`（允許 overlong） | **0 failures ❌ 抓不到** | **1 failure ✅** |
| M-H 放寬 `F0`（允許 overlong） | **0 failures ❌ 抓不到** | **1 failure ✅** |
| M-F 放寬 `F4`（允許超界） | **0 failures ❌ 抓不到** | **1 failure ✅** |

原因是 iteration 3 新增的三組畸形案例（overlong `C0 80`、surrogate `ED A0 80`、已停用 lead `F7`）只覆蓋到 `ED` 那一條與「lead byte 本身非法」那一類，**沒有一組落在 `E0`／`F0`／`F4` 的「差一格」邊界上**。

**修法**：`test_truncate_bytes_survives_malformed_input` 的畸形輸入由 9 種擴為 **12 種**，補上三組恰好落在合法範圍外一格的序列——`E0 9F BF`（`E0` 之後須 `A0-BF`）、`F0 8F BF BF`（須 `90-BF`）、`F4 90 80 80`（須 `80-8F`）。**不改程式碼**（reviewer 已窮舉驗證程式碼正確）。

**這一項的意義與 iteration 3 的 oracle 缺陷同型**：規則寫對了，但沒有東西守著它不被改壞。突變測試是唯一能發現這種缺口的方法——「測試全綠」在這三條規則上先前是沒有資訊量的。

### 複驗（orchestrator 自行執行）

| 項目 | 結果 |
| --- | --- |
| stub，兩版 bash（3.2.57／5.2.37） | 35 tests, 381 checks, 0 failures |
| 四條條件式規則的突變 | 四條**皆**紅（上表右欄）→ 每次還原後 `diff -q` 逐位元一致 → 複跑 35/381/0 |
| 兩支 validator | 皆 passed |

### reviewer 的兩項附帶觀察（如實記載）

1. **窮舉掃描初次出現 654 項「違反」，逐一核對後全部是測試方法論產物**——它構造第二位元組時掃過了定義域外（非延續位元組），命中的是函式明文排除的「輸入中間畸形位元組不歸本函式負責」。不是缺陷。
2. **效能**：`DETAIL_MAX=2000` 的最壞情況（2000 個位元組全是延續位元組）逐位元組收斂，中位數約 250〜360ms。單次呼叫、且觸發條件是理論上界，判定非實際問題。**如實記載而非略過**：若未來 `DETAIL_MAX` 顯著放大，這個成本是二次的。

### U-5 收斂後仍帶進 Bolt 1 gate 的三項

1. **Major #2（iteration 1）**：批次鍵介面與 U-6 已核可 `business-rules.md` 的 R-6.1a／R-6.1b 字面矛盾——指派 U-6 的 code-generation 承接，**沒有任何測試會發現它**。
2. **Minor #1（iteration 1）**：U-5 的 `domain-entities.md`／`business-rules.md` R-1 表未同步第五個失敗碼 `Failed`（程式碼已正確）。
3. **`tech-stack-decisions.md` 的「讀的是即時狀態而非索引」已被實測推翻**（label 列舉同樣最終一致，約 4〜6 秒），連帶完成判準「連續兩輪」隱含一個未寫下的間隔前提。
