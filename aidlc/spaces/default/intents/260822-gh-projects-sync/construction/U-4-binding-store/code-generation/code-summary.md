# Code Summary — U-4 record 回寫與同步狀態

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-4-binding-store · kind: library
     Generated: 2026-09-05T00:39:58Z（讀自 date -u） -->

## 建立的檔案

全部在 `.github/actions/aidlc-sync-record/`（本 repo 工作樹其餘檔案零改動；lead 以 `git status` 驗、orchestrator 複驗）：

| 檔案 | 規模 | 職責 |
| --- | --- | --- |
| `action.yml` | 185 行 | 五個 `operation` 的介面轉接：9 個 input（`operation`／`record_path`／`issue_number`／`state_json`／`branch`／`paths`／`message`／`git_user_name`／`git_user_email`，**零憑證型 input**）→ `AIDLC_*` env；7 個 output（`binding`／`state_json`／`result`／`reason`／`attempts`／`commit_sha`／`message`）；逐 operation 的合法 input 組合與三種 exit code 寫在 description |
| `record.sh` | 770 行（可執行） | 全部邏輯：讀寫層（`load_state_file`／`write_state_with_patch`）、`commit_and_push` 的前置檢查→暫存 worktree→三方鍵層合併→push→stderr 分類→重試迴圈；檔頭含契約段、錯誤模型段（三種 exit code）、**R-3.1 三條線**（`main` 由平台擋、`ut` 平台不擋故本檔守、feature 分支無保護）、SEC-1〜SEC-4。另有 `defaults` 診斷子命令（測試鎖 schema 八鍵與 `MAX_RETRIES`） |
| `run-stub-tests.py` | 1235 行 | 離線層：每案在暫存目錄建**本機 bare repo 當 origin**（pre-receive hook 計次／模擬拒絕）＋ clone 當呼叫端；以 git PATH shim 攔第一次 push 製造**真實** client-side 非快轉；31 案 231 斷言，每案含 §4.4 規格註解（本單元無 API／UI，`@api`／`@ui` 一律不填） |
| `run-live-tests.py` | 456 行 | 真實 origin 層：一次性分支 `aidlc-sync/test/<utc-ts>`，三層防呆（分支名前綴斷言、shim 對 push refspec 的必含子字串檢查、`ut` 步驟在 origin URL 指向不存在路徑的 clone 內跑），(a)〜(d) 五步 41 斷言；無憑證／無 push 權 exit 3 明確 skip，測畢刪分支 |

## 關鍵實作決定

五項 Plan Approval 介面判斷（2026-09-05T00:02:37Z 核可）**全數照案落地**（落點由 orchestrator 開檔核對）：

| 裁決 | 落點 |
| --- | --- |
| 1 `ut`／`main` 介面層防線 | `PROTECTED_BRANCHES` 常數；`op_commit_and_push`（`record.sh:640`）的**第一個**檢查（`:645-649`）在 `require_git_repo` 之前 → `rejected policy`，零 git 動作 |
| 2 非快轉重試採三方鍵層合併 | `three_way_merge`（`:600`）：`$theirs + {ours 中與 base 不同的頂層鍵}`；重試迴圈 `refresh_theirs`（`:522`）→ `reset --hard` → 重合併 |
| 3 零 token、暫存 worktree、顯式身分 | `action.yml` 無憑證 input（stub `test_sec1_action_yml_no_credential_input` ＋ `test_action_yml_env_mapping_matches_record_sh` 鎖住）；`git worktree add --detach`（`:667`）＋ `trap cleanup_worktree EXIT`（`:661`）；身分以 `GIT_AUTHOR_*`／`GIT_COMMITTER_*` 環境變數只作用於 commit 指令（`:684`），見下方定案 7 |
| 4 live 邊界 | `run-live-tests.py` 每次 push／delete 前 `assert_test_branch()`；全程不對 `main` 發 push；`ut` 步驟 (c) 在 origin URL 改為不存在路徑的 clone 內跑 |
| 5 `state` 為部分物件 | `write_state_with_patch`（`:447`）：`($cur + $patch)` → `schema_version = max(現值, patch 值, 1)` → 補預設 → 暫存檔 `mv` |

計畫未逐字指定處的實作定案（lead 定案並回報；標「已核對」者為 orchestrator 開檔驗過）：

1. **三方鍵層合併在每一次嘗試都做，不只重試時**（已核對：`stage_changes_in_worktree`（`:608`）每輪都對 `origin/<branch>` 現況合併）。計畫 Step 5.3 字面是「複製檔案進 worktree」，但 fetch 到的 `origin/<branch>` 可能在本輪開始前就已領先呼叫端 HEAD——複製會把對方欄位靜默抹掉且**不會**觸發非快轉。以 `test_cap_origin_ahead_first_attempt_merges` 鎖住。**這是對計畫字面的擴充，屬偏離，見下段。**
2. **`attempts` ＝ push 總次數（含首次），`MAX_RETRIES=3` ＝ 3 次 push 用罄**。R-3.5 原文「重試 3 次後仍非快轉」若讀成 1＋3＝4 次會與已核可計畫 Step 6 的「`attempts=3`、hook log 計 3 次」衝突，以計畫為準。**歧義如實揭露，留給 gate**。
3. **exit code 分三種**：`ExternalError` 1、介面誤用 2、**`Rejected` 3**（`rejected()`，`:271`；已核對檔頭錯誤模型段）。U-3 沒有 `Rejected`，這是本單元新增的區分；`result` output 仍是唯一判定依據，exit code 只是 workflow 紅燈的載體。
4. **非快轉先於分支保護判定**（已核對 `classify_push_stderr`，`:573`）：任何伺服器端 hook 拒絕都會讓 git 印 `hook declined`，若先判分支保護，回報非快轉文字的 hook 會被誤判為永久失敗。樣式清單維持計畫的八個字串，只改順序。orchestrator 附註：GitHub 的分支保護拒絕形狀是 `! [remote rejected] …`，非快轉是 `! [rejected] … (fetch first)`，兩者的方括號文字不同，`*"[rejected]"*` 不會誤吃前者。
5. **冪等重跑**：工作樹內容與 origin 一致時回 `pushed`、`attempts=0`、`commit_sha`＝origin 既有 HEAD，不產生空 commit（`test_cap_idempotent_rerun_no_new_commit`）。契約仍是 `Pushed | Rejected` 二值。
6. 寫入層 output 多一個 `result=written`；新增診斷子命令 `record.sh defaults`。
7. **同步身分不寫任何 git config**，改以 `GIT_AUTHOR_*`／`GIT_COMMITTER_*` 只作用於 commit 那一個指令——比計畫「只設在 worktree 的 repo 層級 config」更窄，理由是 linked worktree 的 repo 層級 config 與呼叫端共用，寫進去就是污染呼叫端。`git_user_name` 明確傳空 → exit 2，未設定 → 預設（`${var-default}`，lead 第一版誤用 `${var:-default}`，被 `test_cap_identity_override_and_empty_rejected` 抓到後修正）。
8. 寫入的 patch 也過 `schema_version`／`binding` 型別檢查（exit 2），避免寫出下一輪讀不了的檔。
9. 檔案落地為 pretty JSON ＋ 尾端換行，鍵序「預設欄位在前、未知欄位在後」，diff 穩定。
10. `message` output 只含 push stderr 中 `remote:`／`!` 起頭的行、單行化、截 300 字元（它會進 C-5 的公開 issue）。
11. stub 的真實非快轉不能靠 hook（client-side 的 fast-forward 檢查在 hook 之前），故以 git PATH shim 攔第一次 `push`、先讓第二個 clone 推、再交給真 git；live 層共用同一份 shim。

## 測試覆蓋（orchestrator 逐項複驗，非轉引）

| 層 | 結果 | 複驗方式 |
| --- | --- | --- |
| stub（離線，本機 bare repo） | 31 案 231 斷言，**0 失敗** | orchestrator 以 `AIDLC_RECORD_BASH=/bin/bash`（3.2.57）與 `/opt/homebrew/bin/bash`（5.2.37）各重跑一次，同數字 |
| live（真實 origin） | 5 步 41 斷言，**0 失敗** | orchestrator 自行重跑：建立並刪除 `aidlc-sync/test/20260905T003833Z`，測畢 `git ls-remote origin 'refs/heads/aidlc-sync/test/*'` 為空；`ut`（`be73385`）與 `main`（`f8d6854`）HEAD 前後相同 |
| repo／env contract | 兩支 validator 皆綠 | orchestrator 自行重跑 |
| 語法 | `bash -n`（3.2 與 5.2）、`py_compile` 兩支測試 | orchestrator 自行重跑 |
| §4.4 註解 | 31＋5 個函式皆含 `@purpose`／`@given`／`@step`／`@pass`／`@story`，零 `@api`／`@ui` | lead 機械檢查 |

**完成判準對照**（[ug:unit-of-work.md] U-4）：
- 「推 `ut`／`main` 被分支保護拒絕回 `Rejected`」→ **`ut` 半邊由介面層承接**（`test_cap_ut_main_policy_rejected_before_any_git`、live (c)：`rejected`／`policy` 且 `ut` HEAD 不變）——平台對本憑證不擋，見計畫實測依據；**`main` 半邊只有 stub 涵蓋**（pre-receive hook 回 GH006 形狀 → `rejected`／`branch_protection`、`attempts=1`），無 live 反例（裁決 4）。
- 「回寫只落在觸發分支且僅涉 record 目錄下的綁定編號與 `sync-state.json`」→ stub happy path 斷言 origin 上該分支 HEAD 的 diff 只含 `sync-state.json`；live (a) 以 `gh api …/commits/<sha>` 斷言 `files` 只有它；路徑越界 exit 2 且零變更。
- 「commit 訊息含 `[aidlc-sync]`」→ 缺標記 exit 2 且 origin 零變更（R-3.3 為 blocking）；happy path 與 live (a) 斷言訊息含標記。

### 突變驗證（lead 執行，四條；每條改壞 → 紅 → 還原 → `diff -q` 逐位元一致 → 複跑 31/231/0）

| # | 突變 | 紅的測試與斷言數 |
| --- | --- | --- |
| ① | `jq '. + $patch'` 改成列舉八鍵重建物件 | `test_r23_unknown_fields_survive_read_modify_write`、`test_r24_higher_schema_version_not_rejected`：3 |
| ② | 拿掉 `ut`／`main` 防線（**只跑 stub**） | `test_cap_ut_main_policy_rejected_before_any_git`：12（origin URL 為假，變成 `external_error` 而非到網路） |
| ③ | 分支保護也重試 | `test_cap_branch_protection_immediate_no_retry`：3（reason、`attempts=1`、hook 計 1 次） |
| ④ | 三方合併改整檔覆寫 | `test_cap_real_non_fast_forward_retry_merges`、`test_cap_origin_ahead_first_attempt_merges`：2 |

## 與計畫的偏離

**一項**：定案 1——三方鍵層合併在**每一次**嘗試都執行，而非計畫 Step 5.3「複製檔案進 worktree、非快轉重試時才合併」。計畫字面的複製在「origin 於本輪開始前已領先」時會靜默覆寫並行寫入者的欄位且不觸發非快轉，即 R-3.5 要防的資料抹除換了一個入口；擴充後「首次嘗試」與「重試」走同一條合併路徑，且多一則測試鎖住。其餘 Step 1〜9 照序執行，五項介面判斷照案落地。

## 未完成項目（誠實列出）

1. **GH006 的逐字文字本輪未在真實 GitHub 上觀察**（裁決 4 刻意不推 `main`）：stub hook fixture 用的是 GitHub 慣用的 `GH006: Protected branch update failed` ＋ `Changes must be made through a pull request` 形狀，來源是文件而非本 session 實測；真實觀察到的只有非快轉那一半（live (b) 實際看到 `! [rejected] … (fetch first)`）。
2. **`hook declined` 的歸類是保守方向但 reason 可能失真**：一個既無非快轉字樣、又不是分支保護的自訂 hook 拒絕會被歸為 `branch_protection`（不重試）——結果同樣是紅燈＋通報，只是名稱與實情可能不符。
3. **三方合併的邊界**：只比對頂層鍵；`pending_reverse` 等巢狀物件整鍵覆寫；ours 相對 base **刪除**的鍵不傳播（寫入層本就無刪鍵語意）；base／ours／theirs 任一非 JSON 物件即 `ExternalError`。
4. **`attempts` 與 R-3.5「重試 3 次」字面的歧義**（定案 2），待 gate 確認採計畫讀法。
5. **`ut` 的 `enforce_admins: false`** 仍是 repo 設定層的開放項（計畫已列，標給 Bolt 1 gate）；本單元只在介面層守。
6. **[US:S-1 AC 7]**（回寫不取消既有 CI run）不由本單元承接，Bolt 1 須連 U-10a 一起上（同批次約束）。
7. live 測試在 public repo 的事件流留下痕跡：每次執行 3 次 push ＋ 1 次刪除（分支刪除後 commit 為不可達物件）。orchestrator 複驗又多跑一次，本輪合計兩次。

## 對呼叫端（U-6／U-7／U-8）的接線提示

- **憑證**：本 action 不讀任何 token；`fetch`／`push` 靠呼叫端 checkout 已持久化的憑證。**U-6／U-7／U-8 必須以同步 token 做 `actions/checkout`（`token:` 明訂、`persist-credentials: true`）**，否則得到 `external_error`（認證失敗）而非 `rejected`。
- **exit code 與 `result`**：`pushed` exit 0；`rejected` exit 3（`reason` ∈ `policy`／`branch_protection`／`non_fast_forward_exhausted`，皆為紅燈＋交 C-5）；`external_error` exit 1；介面誤用 exit 2。判定一律看 `result`。
- **`branch` 給觸發分支名**（`pull_request` 事件用 `github.event.pull_request.head.ref`，push 用 `github.ref_name`），U-7／U-8 給從 `ut` 分叉的自建分支名；分支不存在於 origin 時以呼叫端 HEAD 為分叉點建立——所以 U-7／U-8 的 checkout 必須先 `ref: ut`（其 R-7.1）。
- **`state_json` 只給要改的欄位**；`write_binding` 只在首建成功後呼叫一次；`read_binding` 空字串＝尚未首建。
- **同步身分**：不傳 `git_user_name`／`git_user_email` 即用預設 `aidlc-sync`／`aidlc-sync@users.noreply.github.com`；明確傳空會 exit 2。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T00:57:05Z
**Iteration:** 1

### Findings

| # | Severity | 檔案:行 | 分類 | Finding | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Major | `functional-design/business-rules.md:38,47` vs `code-generation/code-generation-plan.md:37,69` vs `code-generation/code-summary.md:85` | 新設計問題 | U-4 自己的產出對「U-7（對帳）該推哪個分支」給出兩個互相矛盾的答案，且較早那份的未決風險從未被關掉。`business-rules.md` R-3.1（iteration 3，2026-08-30T00:57:28Z）寫的是「對帳（U-7）推**其排程觸發分支**」，並附一則明確標示**不裁定**的註記（line 47）：「`schedule` 觸發只在**預設分支**上執行……**須在 Bolt 2 開工前確認**——**若預設分支就是 `main`，兩者直接衝突**」。而本輪 `code-generation-plan.md` 自己的「實測依據」表已經把這個「若」坐實為事實：`gh repo view --json defaultBranchRef` 回傳 `main`。但 `code-generation-plan.md`（line 37、69）與 `code-summary.md`（line 85）改口說「U-7 從 `ut` 分叉的**自建分支**（R-7.2）」——與 U-8 同一類，不是「排程觸發分支」。三個問題：(a) 若「自建分支」是對的，`business-rules.md:47` 那則明確標示待確認的衝突就是被**默默解決**的，卻沒有人回去把它標記為已解決或更新 R-3.1 的措辭，讓下一個讀 `business-rules.md` 的人（包括 U-7 自己的實作者）仍會看到一個「未決」的相容性警告；(b) 若「排程觸發分支」才是對的，那麼 `code-generation-plan.md`／`code-summary.md` 對 U-6／U-7／U-8 的接線提示就是**錯的**，會誤導 U-7 的實作者以為不需要處理 main 衝突；(c) `code-generation-plan.md` 引用的「R-7.2」不在本單元任何一份產出內（我核對過 U-4 全部六份 functional-design／nfr-requirements 檔與兩份 code-generation 檔，唯一出現處就是這兩行本身），本審查範圍內無法核實它是否存在、說了什麼——這本身就是一個「契約端點懸空」：一個被當作既定事實引用的規則編號，在可查證的範圍內找不到定義它的地方。三種情況都指向同一件事：這兩份文件需要互相對齊並回填 `business-rules.md:47` 的裁決狀態，不能讓兩個互相矛盾的分支策略同時留在 U-4 自己的紀錄裡。 | 在 U-7 進 code-generation 之前，把 `business-rules.md:47` 的「不裁定」關閉：若「自建分支」確實是後來的定案（引用其出處，例如 U-7 自己 business-rules.md 的 R-7.2 或對應 ADR 段落），回填一句更正並移除「須確認」措辭；若尚未定案，`code-generation-plan.md`／`code-summary.md` 的「U-7 給自建分支名」措辭要降級為「待 U-7 自己的 application-design／functional-design 確認，現階段兩種可能都要讓 R-3.1 的 `main` 封鎖線經得起考驗」，不要用肯定語氣。這不影響 U-4 本單元自身程式碼的正確性（`PROTECTED_BRANCHES="ut main"` 對任何呼叫者一視同仁，且已被 stub／mutation 驗證鎖住），純粹是跨單元交接的一致性缺口，故不擋 U-4 本身的 READY，但必須在 U-7 開工前收斂。 |
| 2 | Minor | `record.sh:318`（`require_paths` 的 `for p in $raw`）與 `:645`（`for b in $PROTECTED_BRANCHES`） | 新設計問題 | `for p in $raw` 對 `$AIDLC_PATHS` 做未加引號的展開，會同時經歷 word-splitting **與 pathname 展開（glob）**——`set -f`／`noglob` 全檔未設。目前之所以安全，是因為白名單比對是逐字相等且 fail-closed（任何展開出來的檔名只要不精確等於 `<record_path>/sync-state.json` 就 `fail`），不是因為輸入被正確中性化。若日後有人在別處複製這個迴圈形狀處理較不嚴格的白名單，同一個未加引號的展開就會變成真正的問題。`$PROTECTED_BRANCHES` 是常數、無風險，一併列出是因為兩處是同一種寫法。 | 在 `for p in $raw` 前後加 `set -f`／`set +f`（或改用 `read -ra` 搭配 `IFS` 明確分詞、關閉 glob），讓「白名單擋得住」和「輸入本來就被安全處理」兩件事分開成立，不要疊在一起靠巧合。非阻擋。 |
| 3 | Minor | `record.sh:709`（`printf 'record.sh: push 第 %s 次失敗...'` 印出未清洗的 `$LAST_PUSH_STDERR`） | 新設計問題 | 對外的 `message` output 有 `scrub_git_stderr` 把關（只留 `remote:`／`!` 開頭行、截 300 字元），但 `record.sh` 印到**自己 stderr**（即 GitHub Actions run log）的失敗訊息是**未清洗的原始** `git push` stderr。本 repo 為 public、Actions log 公開可讀（`team.md` 已記載的既有事實）。目前的風險由兩層外部機制吸收，而非本元件自己的控制：(a) `security-requirements.md` 的「Encryption」判定假設走 `actions/checkout` 的 `http.extraheader` 授權方式（token 不落在 remote URL 裡，一般 push 失敗訊息不會逐字帶出它），(b) GitHub Actions 對已知 secret 值有自動遮罩。兩者都成立，所以目前沒有可展示的洩漏路徑，但 `security-requirements.md` 的「Audit logging」／「Encryption」兩列都沒有明講這個「原始 stderr 進公開 log」的事實與其依賴的兩層外部假設——如果將來呼叫端改用會把 token 嵌進 URL 的認證方式（例如手動 `git remote set-url` 帶 basic auth），這裡會是第一個把它印出來的地方。 | 在 `security-requirements.md`（或 `record.sh` 檔頭的安全邊界段）補一句：「本檔印到自己 stderr（workflow log）的 push 失敗訊息不經 `scrub_git_stderr`；其不外洩憑證的假設依賴呼叫端使用 `actions/checkout` 的 extraheader 授權方式，不依賴 URL 內嵌 token」，讓這個依賴被寫下來而非隱含。非阻擋，不需要改程式碼行為。 |

### Attempted refutations that did not hold

- **推 `ut`／`main` 的介面層防線是否真的在任何 git 網路動作之前**：追過 `op_commit_and_push` 的控制流（`require_record_path` → `require_branch`（僅 `git check-ref-format`，純本地語法檢查，不需要在 git repo 內、不觸網）→ `PROTECTED_BRANCHES` 迴圈 → 才輪到 `require_message`／`require_paths`／`require_identity`／`require_git_repo`）。以 stub 測試（`test_cap_ut_main_policy_rejected_before_any_git`）把 origin 指向不存在路徑後仍拿到 `rejected/policy` 而非 `external_error`，獨立重跑確認一致；並實際把 `PROTECTED_BRANCHES=""` 的突變套進 scratchpad 隔離副本，該測試 12 項斷言全部轉為 `external_error`（因為程式碼真的去 `ls-remote` 那個假 origin 了）——證實防線確實在那個位置且確實有效，不是巧合過關。
- **`three_way_merge` 是否在 base 缺鍵／ours 為 null／theirs 有 U-4 不認得的鍵時出錯或抹資料**：逐一代入 jq 語意（`$theirs + ([$ours|to_entries[]|select(.value != $base[.key])]|from_entries)`）：新鍵（base 無、ours 有）因 `$base[.key]` 為 `null` 而必然入選，行為正確；ours 相對 base **刪除**的鍾不會傳播（因為它們根本不在 `$ours|to_entries[]` 裡）——但這與「寫入層從不刪鍵」的既有事實一致，不是本輪新發現的破洞；theirs 獨有、ours／base 皆無的鍵（模擬另一個並行寫入者的未知欄位）在 `test_cap_real_non_fast_forward_retry_merges` 與 `test_cap_origin_ahead_first_attempt_merges` 兩案中都斷言保留。在 scratchpad 隔離副本上把 `three_way_merge` 改成整檔覆寫（`printf '%s' "$ours"`），兩案精確地變紅（2/231），與突變表宣稱的測試與數字逐一相符；還原後未再複跑 diff（因操作對象是隔離副本而非原始檔，原始檔案自始未被觸碰，`git status --short` 核對過工作樹除 `.github/actions/` 與本 intent 目錄外零改動）。
- **非快轉樣式 `*"[rejected]"*` 是否會誤吃 GitHub 真實的分支保護拒絕**：GitHub 對分支保護拒絕的實際輸出形狀是 `! [remote rejected] ... (protected branch hook declined)`，字面含 `[remote rejected]`（方括號內先有 `remote` 才有 `rejected`），與非快轉樣式要求的連續子字串 `[rejected]`（方括號緊接 `rejected`）不同——逐字元核對後確認兩者不會混淆，`classify_push_stderr` 的判定順序在真實文字上並非僥倖；`run-live-tests.py` 的 step (b) 也斷言了真實非快轉的 stderr 含 `[rejected]` 且含 `fetch first`／`non-fast-forward`。
- **獨立複驗（不重跑 live push，改用唯讀查證）**：鑑於 code-summary 已記載本輪 live 測試已跑兩次（lead＋orchestrator，各留下 3 次 push＋1 次刪除的公開事件），為避免再替 public repo 增加無必要的事件，本輪改以唯讀方式核對其宣稱的最終狀態：`git rev-parse refs/remotes/origin/ut` = `be73385c95aee3ca095afa962bec6be830181a1d`、`refs/remotes/origin/main` = `f8d68548e10f613a4eb8400cfb8a526a48f8759c`，與 summary 宣稱的 `be73385`／`f8d6854` 前綴一致；`git ls-remote origin 'refs/heads/aidlc-sync/test/*'` 為空，無殘留分支。（過程中本機一個與此無關的雜散本地分支 `refs/heads/origin/ut` 曾造成 `git rev-parse origin/ut` 的 ref 解析歧義，已改用完整 `refs/remotes/...` 路徑排除誤判，記此以免下一個複驗的人重踩同一個陷阱。）
- **31/231/0 與突變①②③④是否真的可重現**：以 `AIDLC_RECORD_BASH=/bin/bash`（3.2.57）與 `/opt/homebrew/bin/bash`（5.2.37）分別重跑 `run-stub-tests.py`，皆為 31 tests, 231 checks, 0 failures；`bash -n`（兩版本）與 `python3 -m py_compile`（兩支 runner）皆過；`validate_repo_contract.py`／`validate_env_contract.py` 皆綠。在 scratchpad 建立兩份隔離副本重建突變②（`PROTECTED_BRANCHES=""`）與④（`three_way_merge` 改整檔覆寫），紅測試與計數與突變表逐字相符（12、2）。未重建突變①③（僅以邏輯追蹤 jq 語意與 `case` 分支順序核對，判斷與程式碼一致），未發現偏差。

### Summary

新引入 0、既存漏審 0、新設計問題 3（1 Major、2 Minor）。核心程式碼（`record.sh` 的五個 operation、R-2 跨版本相容、R-3 群的介面層防線與內部重試、三方鍵層合併、stderr 分類順序、SEC-1〜SEC-4）逐項核對＋獨立重跑＋兩項關鍵突變重建，結果與 code-summary 的宣稱一致，未能推翻。真正的缺口出在**文件間的一致性**：U-4 自己的 `business-rules.md` 留了一則明確標示「不裁定、須在 Bolt 2 前確認」的 `main`／U-7 相容性風險，本輪 `code-generation-plan.md` 自己的實測證據（`defaultBranchRef=main`）已經把那個「若」坐實，但同一輪的接線提示卻改口說 U-7 走自建分支、且未回頭關閉 `business-rules.md:47` 的裁決狀態，也未能在本審查範圍內找到「R-7.2」的定義處——這不影響 U-4 本身程式碼的正確性（不擋 READY），但必須在 U-7 進入 code-generation 之前收斂，否則兩份文件會繼續各說各話。

## Post-review 修正（2026-09-05T01:08:53Z）

reviewer iteration 1 判 **READY**（新引入 0／既存漏審 0／新設計問題 3：1 Major、2 Minor）。READY 不需再一輪，但兩項 Minor 皆為低成本可修、且其中一項落在公開 log 的洩漏面，故當輪修掉；Major 屬跨單元文件一致性，以澄清處置、不改程式碼。

### Major — U-7 推送落點在本單元自己的產出裡自相矛盾（分類：新設計問題）

reviewer 的觀察成立且重要：`business-rules.md` R-3.1 的註記把「`schedule` 只在預設分支執行，若預設分支就是 `main` 則與『不得推 `ut`／`main`』直接衝突」列為**待確認**，而本 stage 的實測依據表已把 `defaultBranchRef=main` 確認為事實——那個「若」已成真，但註記未被結案；同時本 stage 的計畫與 summary 又斷言 U-7 推「從 `ut` 分叉的自建分支（R-7.2）」，兩者是不同策略。

**澄清（orchestrator，非新裁決）**：`R-7.2` 確實存在，定義在 **U-7 的 `business-rules.md` R-7 群**（R-7.1 釘 `actions/checkout` 的 `ref: ut`、R-7.2 推自 `ut` 分叉的自建分支、R-7.3 把 `ut` HEAD SHA 寫進報告、R-7.4 同樣適用 U-8）；該衝突已由 **ADR-0015 §13 的人工裁決 Q6=A**（2026-08-30T01:31:09Z，使用者原話「不應該在 main 上跑」）收斂。reviewer 找不到 R-7.2 是**讀取範圍限制**的必然結果——U-7 的 construction 目錄不在本次 dispatch 的 exempt 清單內，這是 reviewer scope 規則要求的隔離，不是它的疏漏。

**未處置的部分（如實）**：U-4 `business-rules.md` 的那條待確認註記**未回改**（它是已通過 reviewer 的 functional-design 產出，本 stage 不改已核可上游）。因此只讀 U-4 的人仍會看到一個看似未決的開放項。**指派**：U-7 進 code-generation 時，在其 code-summary 明記該註記已由 ADR-0015 §13 結案並引用本節；**確認人為 Bolt 2 gate**（U-7 於該 Bolt 交付）。本單元的正確性不受影響——`PROTECTED_BRANCHES` 對 `ut` 與 `main` 一律擋，且突變 ② 驗過。

### Minor 1 — 無引號展開同時做了 word-splitting 與 glob（分類：新設計問題）

`require_paths` 的 `for p in $raw` 與 `op_commit_and_push` 的 `for b in $PROTECTED_BRANCHES` 需要 word-splitting，但沒有 `set -f` 時 glob 也會展開：一個含 `*` 的 `paths` 會先被 shell 依當前工作目錄展開成一組真實檔名，白名單比對看到的就不是呼叫端傳入的字串。先前不出事只因白名單是逐字相等比對（fail-closed），那是巧合不是防護。

**修法**：兩處迴圈前後加 `set -f`／`set +f`。**驗證**（orchestrator 實跑）：在暫存 repo 內以 `AIDLC_PATHS` 帶一個 `*.json` 樣式（目錄下另有兩個 `.json` 檔）呼叫 → 修正後逐字回報「`paths` 越出白名單（R-3.2）：'…/*.json' 不等於 '…/sync-state.json'」，即該樣式**未被展開**。

### Minor 2 — 原始 push stderr 進了公開的 workflow log（分類：新設計問題）

`message` output 過 `scrub_git_stderr`，但同一份原始 stderr 又被 `printf … >&2` 原樣印進 `record.sh` 自己的 stderr——那就是 GitHub Actions 的 workflow log，而本 repo 為 public。等於 SEC-2「不把收到的東西原樣貼出去」只守了一半，其安全性依賴兩個未寫下的外部假設（checkout 用 `extraheader` 而非 URL 內嵌 token、GitHub 會自動遮罩 secret）。

**修法**：該 `printf` 改用 `scrub_git_stderr` 的輸出（`To <url>` 這類可能內嵌憑證的行本就不在保留樣式內）。

### 修 Minor 2 時實測撞出的既有缺陷（本輪一併修）

改完後 stub 立刻紅一案：`scrub_git_stderr` 對 git 的 **client-side** 拒絕行完全不命中——那一行是「（一個空格）`! [rejected]        HEAD -> branch (fetch first)`」，**行首有一個空格**，而保留樣式是 `remote:` 開頭或 `!` 開頭。後果：非快轉重試耗盡時，`message` 只剩「（stderr 無 remote:／! 行）」——交給 C-5 通報給人的訊息裡**沒有任何原因**。伺服器端的「（空格）`! [remote rejected] …`」同樣有前導空格，一併漏掉。

**修法**：比對前先去行首空白（bash 3.2 相容的逐字元剝除迴圈）。**突變驗證**：把去空白那段拿掉 → 同一案立刻紅（訊息退回「（stderr 無 remote:／! 行）」）→ 還原 → `diff -q` 逐位元一致 → 複跑 31/231/0。

**這個缺陷 reviewer 沒抓到，`message` 的既有測試也沒鎖住**：現有斷言只驗 `result`／`reason`／`attempts`，沒有斷言 `message` 含實際原因。如實記載，不美化。

### 修正後的複驗（orchestrator 自行重跑，非轉引）

| 項目 | 結果 |
| --- | --- |
| stub，`/bin/bash` 3.2.57 | 31 tests, 231 checks, 0 failures |
| stub，`/opt/homebrew/bin/bash` 5.2.37 | 31 tests, 231 checks, 0 failures |
| live（真實 origin） | 5 steps, 41 checks, 0 failures；建立並刪除 `aidlc-sync/test/20260905T010614Z`，測畢 `ls-remote` 無殘留；`ut`（`be73385`）／`main`（`f8d6854`）HEAD 不變 |
| 兩支 validator | 皆 passed |
| `bash -n`（3.2 與 5.2） | ok |

### 未完成項目的增補

8. **`message` output 的內容沒有測試鎖住**（見上一節）：現有斷言只到 `result`／`reason`／`attempts`。指派 build-and-test 補一條「非快轉耗盡時 `message` 含 `[rejected]` 或 `fetch first`」的斷言。
9. **live 測試累計執行三次**（lead 一次、orchestrator 複驗一次、本輪修正後複驗一次），public repo 的事件流因此留下 9 次 push ＋ 3 次分支刪除。
