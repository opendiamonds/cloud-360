# Code Generation Plan — U-4 record 回寫與同步狀態

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-4-binding-store · kind: library
     Created: 2026-09-04T17:19:20Z（讀自 date -u） -->

## 交付物與落點

**`.github/actions/aidlc-sync-record/`** — 獨立 composite action（`nfr-requirements/tech-stack-decisions.md` 定案：不與 U-1／U-2 共用，本單元做**檔案系統與 git I/O**；也不與 U-3 共用，兩者的驗證方式分別是「④git 與 repo 行為」與「③真實 Projects v2 API」，併成一支會讓完成判準同時指涉兩種不可互換的驗證）。`shell: bash`，直接使用 `git` 與 `jq`，**不使用 `gh`**（同檔定案：本單元做的是 commit 與 push，不是 API 呼叫）。

沿用 U-1〜U-3 已核可的形狀：**邏輯放 `record.sh`，`action.yml` 只做介面轉接**，以 `operation` 分派 [ad:component-methods.md] §C-4 的五個方法：`read_binding`、`write_binding`、`read_sync_state`、`write_sync_state`、`commit_and_push`。四個存取器操作的是**同一份檔案** `<record>/sync-state.json`（缺口 L-1 定案，`domain-entities.md`），`read_binding`／`write_binding` 是它 `binding` 欄位的投影，不是第二份資料。

## 實測依據（本站唯讀查證，2026-09-04T17:19Z；全部為 `gh api` 與 `git` 的實際回應，非轉引）

| 事實 | 取得方式 | 對實作的直接約束 |
| --- | --- | --- |
| 預設分支 `main`、visibility `PUBLIC`、rulesets 為 `[]` | `gh repo view --json defaultBranchRef,visibility`；`gh api repos/…/rulesets` | 與 PRE-1-a「ruleset 不可行」一致；feature 分支無任何 ruleset ⇒ `requirements.md` A-8「同步身分對 feature 分支有寫入權且不受分支保護阻擋」在現況成立 |
| `main` 的 branch protection：`required_status_checks`（`Repository contract`，strict）＋ PR review（0 人）＋ **`enforce_admins: true`** | `gh api repos/…/branches/main/protection` | 擁有者 token 直推 `main` 會被平台拒絕（GH006）——完成判準的 `main` 半邊由平台承接 |
| **`ut` 的 branch protection：PR review（0 人）、無 `required_status_checks`、無 push restrictions、`enforce_admins: false`**；本憑證帳號 `permissions.admin: true` | `gh api repos/…/branches/ut/protection -q keys`；`gh api repos/…/cloud-360 -q .permissions` | **擁有者 token 直推 `ut` 不會被平台擋下**。完成判準「推 `ut` 被分支保護拒絕回 `Rejected`」對本憑證**無法由平台滿足**；R-3.1「不得推 `ut`／`main`」必須由**介面層自己守**（見裁決 1），且 live 測試**絕不可**對 `ut` 發出真實 push——它會成功 |
| 憑證為擁有者帳號 token（ADR-0016 §1），PAT 的 push **會**觸發 workflow | ADR-0016 §1；GitHub 行為（`GITHUB_TOKEN` 才有不觸發的例外） | [US:S-1 AC 5] 的「同步身分 ＋ `[aidlc-sync]`」防線②**確實會被執行**（`stories.md` 該 AC 的「恆真」前提不成立）；commit 訊息含標記是 U-6 R-4.2 skip 的唯一依據（R-3.3 為 blocking 檢查） |
| `sync-state.json` 不在 `.gitignore`（`.gitignore:47-53` 只排除 cursor、runtime-graph、`.aidlc-*`） | 逐行讀 `.gitignore` | 檔案可被 commit；不需改 `.gitignore` |
| `jq` 在 runner 預裝、本機亦有（U-3 已用） | U-3 `board.sh` 實測 | 未知欄位保留（R-2.3）以 `jq` 就地更新（`. + $patch`）實現，**不得**用 `jq -n '{…}'` 重建物件（`tech-stack-decisions.md` 的寫法對照表） |
| 本機 git 身分為個人（`D.C`），remote 為 ssh | `git config`／`git remote -v` | SEC-4：`record.sh` 必須顯式設定同步身分，不得沿用任何預設；live 測試以 ssh 憑證推送，runner 上則靠 checkout 持久化的 token（裁決 3） |

## 計畫步驟

- [x] **Step 1 — `action.yml` 介面**：五個 `operation` 的 inputs/outputs 宣告與 env 映射。輸入：`record_path`（必要，相對 repo 根）、`issue_number`（`write_binding`）、`state_json`（`write_sync_state`，**部分物件**，見裁決 5）、`branch`／`paths`／`message`（`commit_and_push`）、`git_user_name`／`git_user_email`（預設值見裁決 3）。**零憑證型 input**（與 U-3 SEC-1 同精神；本單元不讀任何 token，見裁決 3）。逐 operation 在 description 列必要 input 與有效 output（沿用 U-2／U-3 慣例）。輸出：`binding`（空字串＝`null`）、`state_json`（讀後的完整物件）、`result`（`pushed`／`rejected`）、`reason`（`rejected` 時：`branch_protection`／`non_fast_forward_exhausted`／`policy`）、`attempts`、`commit_sha`、`message`。
  **追溯**：[ad:component-methods.md] §C-4、[US:S-1 AC 2]／[AC 4]
- [x] **Step 2 — `record.sh` 基座**：`fail`／`emit`／`gh_output`（沿用 U-2／U-3 形狀，`$GITHUB_OUTPUT` heredoc 分隔符防注入）；`require_record_path`（必須是 `aidlc/spaces/<space>/intents/<slug>/` 形狀、必須存在）；**`paths` 白名單驗證器**（R-3.2：每一路徑必須逐字等於 `<record_path>/sync-state.json`——L-1 併檔後白名單只有一個檔；不合即 `fail`，exit 2，不是 `Rejected`——那是呼叫端接線錯誤，與 U-3「未知 operation 非零 exit」同型）；`SCHEMA_VERSION=1` 常數與七個已知欄位的預設值表。檔頭 docstring 沿 `agent_router.py` 樣板深度（契約段、安全邊界段、錯誤模型段）。
  **追溯**：R-3.2、SEC-1、`team.md` docstring 慣例
- [x] **Step 3 — 讀取層**：`read_sync_state`——檔案缺席 → 全部預設值（R-2.2，不視為錯誤）；欄位缺席 → 補預設（R-2.2）；未知欄位**原樣保留在輸出物件內**（R-2.3 的讀取半邊）；`schema_version` 高於自己 → **不拒絕**，原樣帶出（R-2.4）；JSON 不合法 → `ExternalError`（exit 1，紅燈——這不是「舊格式」，是損壞）。`read_binding` ＝ 同一次讀取取 `.binding`，缺席或 `null` → 空字串（＝`null`，觸發首建，R-1.1）。型別檢查只做 `schema_version`（正整數）與 `binding`（整數或 `null`）；`last_status`／`last_reason_code` 等的值域由 U-1 擁有，本單元**不解讀、不驗證**（`domain-entities.md`：「本單元只負責讀寫與保存」）。
  **追溯**：R-1.1、R-2.2〜R-2.4
- [x] **Step 4 — 寫入層**：`write_sync_state`——read-modify-write：讀現檔（缺席視為 `{}`）→ `jq '. + $patch'` 就地合併（**未知欄位保留**，R-2.3 的寫入半邊；`pending_reverse` 為物件，以整個鍵為單位覆寫）→ `schema_version` 取 `max(現值, 1)`（不降版，R-2.4）→ 已知七欄若仍缺席補預設（讓檔案自述完整）→ 寫到同目錄暫存檔再 `mv`（原子替換）。任何檔案寫入失敗 → `ExternalError`（exit 1，R-1.2）。`write_binding` ＝ `write_sync_state` 帶 `{binding: N}`（N 為正整數，否則 `fail`）。
  **追溯**：R-1.2、R-2.1〜R-2.4
- [x] **Step 5 — `commit_and_push`**（R-3 群，裁決 1〜4）：
  1. 前置檢查（**任何 git 動作之前**）：`branch` ∈ {`ut`, `main`} → `result=rejected`、`reason=policy`、非零 exit（裁決 1）；`message` 不含 `[aidlc-sync]` → `fail`（R-3.3，exit 2）；`paths` 逐一過白名單（Step 2）；`paths` 中的檔案必須存在於呼叫端工作樹。
  2. 顯式設定 `user.name`／`user.email`（SEC-4，只設在暫存 worktree 的 repo 層級 config，不污染呼叫端全域設定）。
  3. `git fetch origin <branch>`；以 **`git worktree add`** 在暫存目錄開出 `origin/<branch>`（分支不存在於 origin 時以呼叫端 HEAD 為分叉點建立——U-8 的 `aidlc-sync/reverse/*` 與 U-7 從 `ut` 分叉的自建分支都走這條）；把 `paths` 的檔案複製進 worktree；`git add` 限白名單路徑；`git commit`；`git push origin HEAD:refs/heads/<branch>`。呼叫端的 checkout（`pull_request` 事件下是 merge ref、可能 detached）**一個檔案都不動**（裁決 3）。
  4. push 失敗時**解析 stderr**分類（`business-rules.md` R-3.5「只看 exit code 無法區分」）：分支保護（`GH006`／`protected branch`／`Changes must be made through a pull request`／`hook declined`）→ `rejected`／`branch_protection`，**立即**、不重試；非快轉（`non-fast-forward`／`fetch first`／`[rejected]`）→ 重試：重新 `fetch`、worktree 重設到最新 `origin/<branch>`、**以三方鍵層合併重套本輪變更**（裁決 2）、再 commit、再 push，上限 3 次，仍失敗 → `rejected`／`non_fast_forward_exhausted`；其他失敗（網路、認證）→ `ExternalError`（exit 1）。
  5. 成功 → `result=pushed`、`commit_sha`、`attempts`；`Rejected` 兩種都非零 exit（[ad:services.md] 紅燈 ＋ 交 C-5）；worktree 一律 `git worktree remove` 清掉（`trap`）。
  **追溯**：R-3.1〜R-3.5、[req:FR-A3]、[US:S-1 AC 4]、SEC-3、SEC-4
- [x] **Step 6 — stub 測試 `run-stub-tests.py`**（離線；每案在暫存目錄建一個 **本機 bare repo 當 `origin`** ＋ 一個 clone 當呼叫端工作樹；hook 由測試安裝）：
  - 讀寫層：檔案缺席全預設；欄位缺席補預設；**含未知欄位的 fixture 經一次 read-modify-write 後未知欄位仍在且值未變**（R-2.3 必要 fixture）；`schema_version: 99` 不拒絕且寫回仍是 99；`binding` 缺席 → `read_binding` 空；`write_binding` → `read_binding` round-trip；JSON 損壞 → exit 1、`result=external_error`；目錄唯讀 → 寫入失敗 exit 1。
  - `commit_and_push`：happy path → `pushed`、origin 上該分支 HEAD 的 diff **只含** `sync-state.json`、訊息含 `[aidlc-sync]`、作者為設定的同步身分（SEC-4）、呼叫端工作樹的其他檔案未動、暫存 worktree 已清；訊息缺標記 → exit 2 且 origin 零變更；路徑越界 → exit 2 且零變更；`branch=ut`／`main` → `rejected`／`policy`、非零 exit、**零 git 網路操作**（bare repo 的 hook log 為空）；pre-receive hook 回 GH006 文字 → `rejected`／`branch_protection`、`attempts=1`（不重試，由 hook log 計次）；**真實非快轉**（第二個 clone 先推一個帶未知欄位的 `sync-state.json`）→ 第一次 push 被 bare repo 以真的 non-fast-forward 拒絕 → 重試後 `pushed`、`attempts=2`，且 origin 上的檔案**同時含**對方的未知欄位與本輪的變更（R-3.5 ＋ R-2.3 ＋ 裁決 2 一次驗到）；hook 每次都回非快轉文字 → 第 4 次放棄、`rejected`／`non_fast_forward_exhausted`、`attempts=3`（hook log 計 3 次 push）；分支不存在於 origin → 以 HEAD 分叉建立並 `pushed`。
  - SEC-1 機械斷言：`action.yml` 無憑證型 input。
  **追溯**：[ug:unit-of-work.md] U-4 完成判準第 2、3 條；R-2.3；R-3.5
- [x] **Step 7 — live 測試 `run-live-tests.py`**（對真實 `origin`，需 push 權；無權時明確 skip 並以非零聲明不完整）：進場防呆——**拒絕任何以 `ut`／`main` 為目標的步驟**（本單元的 SEC-3 對應物：隔離靠分支名，因為 `ut` 的平台保護對本憑證不生效）。步驟：(a) 在暫存 clone 中對 `aidlc-sync/test/<utc-ts>` 執行 `commit_and_push` → `pushed`，`gh api repos/…/commits/<sha>` 可查到、訊息含標記、`files` 只有 `sync-state.json`；(b) 用第二個 clone 先推一筆到同分支，再從第一個 clone 推 → 真實 GitHub 的 non-fast-forward → 重試後 `pushed`、對方欄位保留；(c) `branch=ut` → `rejected`／`policy` 且 `git reflog`／`gh api` 證明 `ut` HEAD 未變；(d) 測畢 `git push origin --delete aidlc-sync/test/<ts>` 清除分支並確認已不存在。**不對 `main` 發出任何真實 push**（裁決 4）。
  **追溯**：[ug:unit-of-work.md] U-4 驗證方式「④git 與 repo 行為」
- [x] **Step 8 — 突變驗證**（至少四條，每條：改壞 → 紅 → 還原 → `diff -q` → 複跑綠）：①R-2.3 的 `jq '. + $patch'` 改成 `jq -n '{…}'` 重建 → 未知欄位 fixture 紅；②拿掉 `ut`／`main` 介面層防線 → stub 的 policy 案紅（**此突變只跑 stub，絕不跑 live**）；③把「分支保護立即放棄」改成也重試 → `attempts=1` 斷言紅；④三方合併改成整檔覆寫 → 非快轉合併案的「對方未知欄位保留」紅。
- [x] **Step 9 — 規格註解與文件**：每個測試函式加 §4.4 結構化註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`；本單元無 API 端點與 UI，**`@api`／`@ui` 一律不填**——`project.md` 的 `tcms-test-cases:c20`：寧可缺、不得捏造）；`record.sh` 檔頭寫明：錯誤模型（`ExternalError` 例外式 exit 1、`Rejected` 兩種 reason 皆非零 exit、`Pushed` exit 0）、SEC-1〜SEC-4、**「`ut` 的平台保護對本憑證不生效，R-3.1 由本檔守」**、R-2.3 反直覺寫法的理由。
- [x] **Step 10 — `code-summary.md`**：檔案清單、關鍵決定、測試覆蓋、突變結果、誠實列出未完成項與對呼叫端（U-6／U-7／U-8）的接線提示。

## 需 Plan Approval 裁決的五項介面判斷（上游未逐字指定，本計畫的落法）

1. **`ut`／`main` 的介面層防線與其回傳形狀**：實測 `ut` 的 `enforce_admins: false` 且憑證為 admin，平台不會擋直推 `ut`；R-3.1 若不在介面層守，就沒有任何東西守。本計畫：`branch` 為 `ut`／`main` 時在**任何 git 動作之前**回 `result=rejected`、`reason=policy`、非零 exit——沿用契約的 `Rejected` 形狀（同樣是「需要人介入」的紅燈），但以 `reason` 與平台拒絕（`branch_protection`）區分，讓 C-5 的通報說得出是哪一種。替代（`fail` exit 2 當接線錯誤）的問題：接線錯誤的形狀是「呼叫端寫錯」，而事件路徑上 `branch=ut` 是**可達的正常輸入**（管理員直推 `ut` 的 record 變更會觸發 U-6），不該用接線錯誤的通道。
2. **非快轉重試的「重新套用本輪變更」＝三方鍵層合併**：base ＝ 呼叫端 `HEAD:<path>`（本輪起點的版本）、ours ＝ 工作樹現檔、theirs ＝ 重新 fetch 後的 `origin/<branch>` 版本；結果 ＝ theirs ＋ {ours 中與 base 不同的頂層鍵}。整檔覆寫會把並行寫入者（U-7 對帳）的欄位靜默抹掉，與 R-3.5「重新套用本輪的變更」字面不符；鍵層合併同時保住 R-2.3 的未知欄位。`pending_reverse` 以整個鍵為單位。
3. **憑證、隔離與身分**：本單元**不宣告、不讀取任何 token**，push 走 `origin` 並沿用呼叫端 checkout 已持久化的憑證——**U-6／U-7／U-8 必須以同步 token 做 `actions/checkout`（`token:` 明訂、`persist-credentials: true`）**，這是本計畫對呼叫端的接線要求，會寫進 summary。commit 在暫存 `git worktree` 內完成，呼叫端 checkout 不動（`pull_request` 事件下它是 merge ref）。同步身分以 `git_user_name`／`git_user_email` input 設定，預設 `aidlc-sync`／`aidlc-sync@users.noreply.github.com`（SEC-4 要求顯式，預設值即顯式值；U-6 可覆寫）。
4. **live 測試的邊界**：只對 `aidlc-sync/test/<utc-ts>` 這種一次性分支推送並於測畢刪除（會在 public repo 短暫出現一個分支、留下 push 事件）；**不對 `main` 發出真實 push 來驗 GH006**——若保護設定有任何閃失，落地的是一則機器 commit 在 `main` 上，而換到的資訊（GH006 的逐字文字）用 stub hook 就有。`main` 半邊的平台拒絕因此**只有 stub 涵蓋、無 live 反例**，summary 會如實記載。
5. **`write_sync_state` 的 `state` 為部分物件（patch）**：呼叫端只給要改的欄位（U-6 R-5.4 的五欄、U-8 R-1.3 的 `pending_reverse` 一欄、U-7 R-6 群的三到四欄），其餘由 read-modify-write 保留。若定為整份覆寫，R-2.3 的「保留未知欄位」就變成每個呼叫端各自的責任，三個呼叫端只要一個漏做就破功。

## 測試策略對齊

Test Strategy = Standard（state 檔）。stub 層約 18 案（讀寫層 8、`commit_and_push` 9、SEC-1 1），live 層 4 步。**R-3.5 的 N=3 沒有上游依據**（`business-rules.md` 自陳），本計畫照 3 實作並以常數集中，「若實測發現不足，改的是數字不是規則形狀」。

## 已知的上游開放項（不阻擋本單元程式碼，列入 summary）

- **[US:S-1 AC 7] 歸 U-10a**（同批次約束）：本單元完成不代表回寫不會取消開發者的 CI run；Bolt 1 必須連 U-10a 一起上。
- **`ut` 的 `enforce_admins: false`**：本站只能在介面層守；是否對 `ut` 開啟 `enforce_admins`（會連擁有者自己的直推一併擋下）是 repo 設定層的決定，不在本單元範圍，**標給 Bolt 1 gate**。
- **PRE-1-c**（`public_repo`＋`project` PAT）仍未執行；不影響 `record.sh` 形狀（它不讀 token），但影響裁決 3 的 checkout token 是哪一顆。
- U-7 的推送落點（從 `ut` 分叉的自建分支，R-7.2）與 U-8 的反向分支都依賴「分支不存在於 origin 時以 HEAD 分叉建立」（Step 5 第 3 點）——實作於本單元，驗證留給各自單元的 live 路徑。
