# 手動測試案例 — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: tcms-test-cases（Construction）· intent 260822-gh-projects-sync
     撰寫依據：aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md
     格式契約：TESTING.md -->

## 覆蓋盤點（先分桶，再寫案例）

本 intent 引入或改變的**外部可觀察行為**逐項分桶。**判不出來的不預設丟給手動**——
未分類項列在最後一節並說明卡在哪。

### 桶一：已自動化（不寫手動案例）

| # | 行為 | 斷言落點 | 在 CI 跑過嗎 |
| --- | --- | --- | --- |
| A-1 | record 訊號 → Status 的映射（含 park／skip／未列舉輸入） | `aidlc-sync-map/run-fixtures.py`（2707 條斷言，2592 組窮舉） | ✅ selftest 第一段轉呼 |
| A-2 | 受管區塊的序列化與解析（決定性、round-trip） | `aidlc-sync-block/run-fixtures.py`（550 條，432 組） | ✅ 同上 |
| A-3 | 看板讀寫的四類錯誤分類、回讀不符 ⇒ Aborted、`NOT_FOUND` 防誤映射 | `aidlc-sync-board/run-stub-tests.py`（31 tests／173 checks） | ✅ 本 stage 前一站接進第一段 |
| A-4 | 綁定狀態檔的 commit／push、非快轉重試、`paths` 白名單、分支拒絕 | `aidlc-sync-record/run-stub-tests.py`（31／231） | ✅ 同上 |
| A-5 | 失敗通報 issue 的建立／收斂／關閉、token 遮罩、截斷 | `aidlc-sync-notify/run-stub-tests.py`（35／381） | ✅ 同上 |
| A-6 | 正向編排：兩道自我排除防線、`reverse_pending` fail-closed、多輪收斂 | `aidlc-sync-forward/run-orchestration-tests.py`（40／154） | ✅ 同上 |
| A-7 | 對帳：清單成員規則、批次上限、補平計數、三份獨立清單、一致率分母 | `aidlc-sync-reconcile/run-reconcile-tests.py`（38／211） | ✅ 本 stage 前一站接進第一段 |
| A-8 | 反向同步：逐 intent 抑制、diff 不含 `aidlc-state.md`、雜湊比對、孤兒分支 | `aidlc-sync-reverse/run-reverse-tests.py`（46／309） | ✅ 同上 |
| A-9 | `ci.yml` 的 `gate` 判定邏輯（標記偵測十一種情境）與四個 job 的形狀未被改動 | `aidlc-sync-ci-guard/run-probe-tests.py`（13）＋ `check-ci-yml.py`（19） | ✅ 同上 |
| A-10 | 同步判定不得落在 LLM 步驟內（執行可達閉包，34 支腳本） | `check-agentic-steps.py`（8） | ✅ 直接 step |
| A-11 | 五個承載體的 `paths-ignore`、`.md`↔`.lock.yml` 一致、`compiler_version` 釘住 | `check-paths-relations.py`（22） | ✅ 直接 step |
| A-12 | README 存在指向 Project #16 的需求正本段落 | `scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]` | ✅ `repo-contract` job |

> 本表「斷言落點」與規模數字取自 `build-and-test/build-and-test-summary.md` 的逐單元
> 覆蓋表與 `ci-pipeline/ci-config.md` 的接線後狀態。
>
> **「在 CI 跑過嗎」欄位問的是「這支腳本會不會被 workflow 執行」，不是「它在真實
> runner 上跑過一次了嗎」。** 後者對本 intent 的答案**全部是否**——沒有任何一次真實
> 的 CI 觸發發生過。這一欄不能被讀成執行證據。

### 桶二：待自動化（本 stage 寫出腳本）

| # | 行為 | 為什麼之前沒有 | 本 stage 的落點 |
| --- | --- | --- | --- |
| B-1 | 反向同步 PR 會觸發的 workflow 集合不得變大 | `IGNORE:` 那一族驗的是「這五個被排除了」，**不是**「沒有別的跑起來」。那個事實（合併後仍有 `ci.yml` 與 `aidlc-sync-forward.yml`）原本只寫在絆線訊息的一段**註解**裡，且 `deploy.yml` 完全未被檢視 | `check-paths-relations.py` 的 `PR-TRIGGER-1`；行為測試見 `automation-test-plan.md` |

### 桶三：只能手動（下方五個案例）

| # | 行為 | 為什麼不能／不該自動化 |
| --- | --- | --- |
| M-1 | 真實 `[aidlc-sync]` push 之後四道 CI 關卡的實際執行狀況 | 需要真實 push 事件與真實 GitHub 排程；判定邏輯已由 A-9 涵蓋，**平台是否照它動作**只有真實事件驗得到 |
| M-2 | 反向同步 PR 開啟後實際被建立的 run | 同上；靜態面已由 B-1 涵蓋，**平台的過濾行為**要真的開一個 PR |
| M-3 | 自我測試第二段的端到端往返 | 會在正式 repo 建立真 issue，並因此啟動 `issue-triage`（gh-aw／LLM 路徑，每次執行都花錢），落在 `project.md` 點名的三塊結構性盲區之一 |
| M-4 | `AI-DLC Stage` 自訂欄位在正式看板 #16 上的自動建立 | 欄位名寫錯就是在正式看板上多開一個欄位、且**無法自動判斷名字對不對**——需要人看一眼；且是一次性事件 |
| M-5 | README 看板連結對匿名讀者可開 | 需要一個未登入的瀏覽器工作階段；`REQUIRED_TEXT` 只驗字串在不在，驗不到連結打不打得開 |

### 未分類（不預設丟手動）

| # | 行為 | 卡在哪 |
| --- | --- | --- |
| U-1 | [US:S-10 AC 5]「同步憑證做一次宣告範圍外的寫入 ⇒ GitHub 回 403」 | **該 Given 在現行憑證拓撲下不可達**。ADR-0016 確認 `opendiamonds` 是個人帳號而非組織，且寫入身分改為擁有者 token 後 `repo` scope 整包涵蓋 contents／issues／PR 寫入——**沒有一種宣告範圍內的操作會回 403**。這不是「還沒寫測試」，是那個狀態走不到。處置：回 user-stories 改寫該 AC 的落點，或在 ADR 中記明它隨憑證拓撲變更而失效。**不寫成手動案例**——寫了會是一個永遠無法執行的案例。 |

**分桶計數**：已自動化 **12**／待自動化 **1**／只能手動 **5**／未分類 **1**。

---

## TC: 帶 [aidlc-sync] 標記的 commit 推送後，ci.yml 四個 job 全部跳過且既有 run 不被取消

- plan: AI-DLC ↔ GitHub Projects 同步（手動）
- priority: P1

### 目的

回歸案例。驗證同步機制的回寫 commit 不會替開發者的分支多跑一輪 CI、也不會取消他當下
正在跑的那一次。

### 背景

**症狀（上游實測記載，見 [US:S-1 AC 7]）**：`ci.yml` 的 `concurrency` 為
`group: ci-…-${{ github.ref }}` ＋ `cancel-in-progress: true`，而本團隊分支一律
`danniel/**`（在 `push` 的 branches 清單內）。同步機制每次回寫都會觸發 `ci.yml`，
**並取消開發者當下正在跑的那一次**。

**既有自動化層為何沒抓到**：`ci.yml` 全檔沒有 commit message 過濾，`[aidlc-sync]`
標記原本只擋同步 workflow 自己。U-10a 交付的 `gate` job 與四個 job 的 `if:` 是修正，
而 `run-probe-tests.py` 的 13 項行為測試驗的是**判定邏輯**（給定 commit 訊息算出
`is_sync`），`check-ci-yml.py` 的 19 項驗的是**檔案形狀**。兩者都在本機、離線、對著
YAML 與抽出腳本跑——**沒有任何一項驗得到 GitHub 平台是否照那個 `if:` 動作**。
U-10a 的 `code-summary.md` 逐字把這一項列為「未實測，屬 Bolt 1 整合驗證」。

### 受測介面

- Workflow: `.github/workflows/ci.yml` → pull_request — `gate` job 與四個 job 的 `if:` 條件
- Workflow: `.github/actions/aidlc-sync-record/action.yml` → composite — 產生帶標記的 commit
- 外部相依: GitHub Actions 平台的 `concurrency` 與 job-level `if:` 語意

### 前置條件

1. 一個以 `danniel/` 開頭的測試分支，且該分支已有一個**執行中**的 `ci.yml` run
   （推一顆無關的 commit 即可製造）：
   ```bash
   git switch -c danniel/chore/aidlc-sync-manual-probe
   echo "probe $(date -u +%s)" >> /tmp/aidlc-probe.txt && cp /tmp/aidlc-probe.txt ./probe.txt
   git add probe.txt && git commit -m "雜項(ci): 製造一個執行中的 run 供手動驗證"
   git push -u origin HEAD
   ```
2. 記下該 run 的編號：`gh run list --branch danniel/chore/aidlc-sync-manual-probe --limit 1`

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 確認步驟 0 的 run 狀態 | `gh run list` 顯示該 run 為 `in_progress` 或 `queued` |
| 2 | 在同一分支推一顆訊息含 `[aidlc-sync]` 的 commit：`git commit --allow-empty -m "雜項(sync): 手動驗證 [aidlc-sync]" && git push` | push 成功 |
| 3 | 重新查詢步驟 1 的那個 run | 其狀態**不得**為 `cancelled` |
| 4 | 查新 commit 觸發的 run：`gh run view <新 run id> --json jobs --jq '.jobs[].conclusion'` | `gate` 的 conclusion 為 `success`；其餘四個為 `skipped`；**不得**有任何一個是 `success` 或 `failure` |
| 5 | 讀 `gate` job 的 log | 出現指出 `is_sync=true` 的判定輸出，且指得出是從 commit 訊息判定的 |
| 6 | 清理：`git push origin --delete danniel/chore/aidlc-sync-manual-probe` | 分支已刪除，`gh api` 對該 ref 回 404 |

### 通過條件

- 步驟 3 的既有 run 未被取消。
- 步驟 4 的四個 job **全部**為 `skipped`，且 `gate` 為 `success`（不是 skipped——它是唯一沒有 `if:` 的 job）。

### 失敗徵兆與對應肇因

| 徵兆 | 肇因 |
|---|---|
| 既有 run 變成 `cancelled` | `concurrency.group` 未追加 `github.actor`，或該追加被還原 |
| 四個 job 有任何一個 `success` | `if: needs.gate.outputs.is_sync != 'true'` 被改動，或 `gate` 的輸出沒有被正確傳遞 |
| `gate` 本身 `skipped` | 有人替 `gate` 加了 `if:`——它必須永遠執行，否則「被跳過」這件事本身不留痕跡 |
| 全部四個都跑了、`gate` 也 success | commit 訊息的標記沒被讀到（`pull_request` 事件取不到 `head_commit.message`，見 U-10a 的 fail-open 設計） |

### 追溯

- 實作：`.github/workflows/ci.yml`、`.github/actions/aidlc-sync-ci-guard/check-ci-yml.py`
- 自動化對應：`.github/actions/aidlc-sync-ci-guard/run-probe-tests.py`（判定邏輯層，**不涵蓋平台行為**）
- PR／commit：本 intent 尚未 commit，待 Bolt 1
- User story：S-1

---

## TC: 反向同步 PR 開啟後，只有釘住的那幾支 workflow 建立 run

- plan: AI-DLC ↔ GitHub Projects 同步（手動）
- priority: P1

### 目的

回歸案例。驗證一個只改同步狀態檔的反向 PR 不會把完整的 workflow gauntlet 跑一遍。

### 背景

**症狀**：`ui-regression.md` 的註解逐字記載 PR #510 曾在單一 PR 上燒掉約 **5h59m24s**
runner 時間、**零測試執行**、無可下載 log，重跑又 stall 一次。反向同步每日一次 ⇒
每天把一個只改 JSON 欄位的 diff 送進含六次 LLM 驅動 agent 執行的完整 gauntlet。

**既有自動化層為何沒抓到**：`check-paths-relations.py` 的 `IGNORE:` 那一族驗的是
「這五個承載體有 `paths-ignore`」——**它驗不到「沒有別的跑起來」**。本 stage 新增的
`PR-TRIGGER-1` 補上了集合斷言，但那仍是**靜態解析**：它算的是「依 GitHub 的過濾語意
應該觸發哪些」，不是「GitHub 實際建立了哪些 run」。兩者之間隔著平台行為。

### 受測介面

- Workflow: `.github/workflows/aidlc-sync-reverse.yml` → schedule — 產生反向 PR
- Workflow: `.github/workflows/ui-regression.lock.yml` → pull_request — 應被 `paths-ignore` 排除
- Workflow: `.github/workflows/deploy.yml` → pull_request — `types: [closed]`，合併時才觸發
- 外部相依: GitHub Actions 平台的 `paths-ignore` 過濾語意

### 前置條件

1. 反向同步已可執行（憑證已鑄造，見 Bolt 0 gate）。
2. 手動觸發一次反向同步以產生 PR：
   ```bash
   gh workflow run aidlc-sync-reverse.yml
   gh run watch
   ```
3. 記下產生的 PR 編號：`gh pr list --state open --json number,title --jq '.[] | select(.title | contains("aidlc-sync"))'`

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | `gh pr diff <PR> --name-only` | 只列出 `aidlc/spaces/*/intents/*/sync-state.json` 形狀的路徑；**不得**含 `aidlc-state.md` |
| 2 | `gh pr checks <PR>` | 列出的 check 只來自 `ci.yml` 與 `aidlc-sync-forward.yml` 兩支 |
| 3 | 檢視步驟 2 的清單 | **不得**出現 `ui-regression`、`pr-reviewer`、`lint-fix`、`contract-guard` 任何一個 |
| 4 | `python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py` | `PR-TRIGGER-1` 通過，且其通過訊息列出的集合與步驟 2 觀察到的一致 |
| 5 | 合併該 PR，觀察 `deploy.yml` | 觸發一次完整部署——**這是已知且已登錄的成本**（gate 待決第 7 項），不是本案例的失敗 |
| 6 | 記錄步驟 5 的實際耗時：`gh run view <deploy run> --json startedAt,updatedAt` | 得到一個可供 gate 判斷「這個成本可不可接受」的數字 |

### 通過條件

- 步驟 3 的四支高成本 gh-aw workflow **一個都沒有**建立 run。
- 步驟 4 的靜態判定與步驟 2 的實際觀察一致（兩者不一致代表靜態模型與平台語意有落差，比任一單獨的紅燈更要緊）。

### 失敗徵兆與對應肇因

| 徵兆 | 肇因 |
|---|---|
| `ui-regression` 出現在步驟 2 | 該支的 `.lock.yml` 少了 `paths-ignore`，或 `.md` 改了沒重編 |
| 步驟 2 出現步驟 4 沒預測到的第三支 | 有人新增了一支無 paths 過濾的 `on: pull_request` workflow——`PR-TRIGGER-1` 應該先紅；若它是綠的而實際多跑了，代表靜態模型漏了一種過濾語意 |
| 步驟 1 出現 `aidlc-state.md` | 反向同步的 diff 過濾失效（[US:S-6 AC 2]） |

### 追溯

- 實作：`.github/workflows/aidlc-sync-reverse.yml`、`.github/actions/aidlc-sync-selftest/check-paths-relations.py`
- 自動化對應：`.github/actions/aidlc-sync-selftest/run-selftest-tests.py::test_a_new_unfiltered_pull_request_workflow_is_red`（靜態層）
- PR／commit：本 intent 尚未 commit，待 Bolt 3
- User story：S-6

---

## TC: 自我測試第二段對測試看板的端到端往返

- plan: AI-DLC ↔ GitHub Projects 同步（手動）
- priority: P1

### 目的

驗證同步機制對真實 Projects v2 的完整寫入鏈（建立 item → 寫 Status → 回讀比對 →
清理）在真實憑證下走得完。

### 背景

**這一段從未被執行過。** U-9 的 `code-summary.md` 逐字：「本段從未被執行過……本 intent
至今對它只有 stub 證據，**沒有任何一次真實的看板往返**」。

**既有自動化層為何沒抓到**：它就是自動化層本身——`aidlc-sync-selftest.yml` 的第二段
有 `if: github.event_name == 'workflow_dispatch'`，所以在 PR、push、排程上一律不執行。
把它改成自動執行不可行：它會在**正式 repo** 建立一則真 issue（`create_item` 走
`POST repos/{owner}/{repo}/issues`），而全 repo 只有 `issue-triage.lock.yml` 監聽
`on.issues` ⇒ **每次執行都會啟動一支 gh-aw（LLM 驅動）workflow 去分類它**，清理還會
與那次 triage run 互相競賽。這落在 `project.md` 點名的第一塊結構性盲區。

### 受測介面

- Workflow: `.github/workflows/aidlc-sync-selftest.yml` → workflow_dispatch — 第二段 `endtoend` job
- Workflow: `.github/actions/aidlc-sync-board/action.yml` → composite — Projects v2 讀寫
- 外部相依: GitHub Projects v2 GraphQL API；測試看板 #23；`issue-triage` gh-aw workflow

### 前置條件

1. `AIDLC_SYNC_TOKEN` 已建立為 repo **secret**（不是 variable）：
   ```bash
   gh api repos/opendiamonds/cloud-360/actions/secrets --jq '.secrets[].name' | grep AIDLC_SYNC_TOKEN
   gh api repos/opendiamonds/cloud-360/actions/variables --jq '.variables[].name' | grep -c AIDLC_SYNC_TOKEN  # 必須是 0
   ```
2. 測試看板 **#23** 的 Status 選項已與 #16 同名（六個值）。
3. 已知悉本次執行會在正式 repo 留下一則 closed issue，並會觸發一次 `issue-triage`。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | `gh workflow run aidlc-sync-selftest.yml` | workflow 被排入 |
| 2 | 觀察第一段 `fixtures` job | conclusion 為 `success`（第一段紅則第二段依 `needs` 不執行） |
| 3 | 觀察 `SEC-3` 防呆步驟的 log | 出現對 `AIDLC_PROJECT_NUMBER != 16` 的斷言結果；若該值為 16 則整段以 exit 4 拒絕執行 |
| 4 | 觀察建立步驟 | 在正式 repo 建立一則 issue，log 印出其編號 |
| 5 | 觀察 round-trip 步驟 | 寫入 Status 後回讀，log 印出寫入值與讀回值且**兩者相同** |
| 6 | 觀察清理步驟 | issue 被**關閉**（不是刪除——`deleteIssue` 需 repo admin，憑證只到 `issues: write`），且該 item 以 `deleteProjectV2Item` 移出 #23 |
| 7 | `gh run list --workflow issue-triage.lock.yml --limit 3` | 出現一次由步驟 4 的 issue 觸發的 run——**這是預期成本，不是失敗** |
| 8 | 檢視正式看板 #16 | **不得**出現任何本次執行建立的 item |

### 通過條件

- 步驟 5 的寫入值與讀回值相同。
- 步驟 8 的正式看板未被寫入。
- 步驟 6 的清理完成（issue 為 closed、item 不在 #23 上）。

### 失敗徵兆與對應肇因

| 徵兆 | 肇因 |
|---|---|
| 步驟 3 以 exit 4 中止 | `AIDLC_PROJECT_NUMBER` 被設成 16——**這是防呆生效，不是缺陷**；改回 23 再跑 |
| 步驟 6 清理失敗且訊息含 `deleteIssue` | 有人把清理改回 `deleteIssue`，那需要 repo admin 而憑證沒有 |
| 步驟 8 的 #16 出現 item | 隔離失效——隔離只靠 `AIDLC_PROJECT_NUMBER` 這個設定值，不靠權限 |

### 追溯

- 實作：`.github/workflows/aidlc-sync-selftest.yml`、`.github/actions/aidlc-sync-board/board.sh`
- 自動化對應：`.github/actions/aidlc-sync-selftest/run-selftest-tests.py::test_stage_2_cleanup_closes_the_issue_and_removes_the_board_item`（stub 層）
- PR／commit：本 intent 尚未 commit，待 Bolt 4
- User story：S-10

---

## TC: AI-DLC Stage 自訂欄位在正式看板 #16 上被自動建立且名稱正確

- plan: AI-DLC ↔ GitHub Projects 同步（手動）
- priority: P1

### 目的

驗證第一次真實同步在 #16 上建立的自訂欄位名稱正確；名稱寫錯會在正式看板上多開一個
永久欄位。

### 背景

`aidlc-sync-forward.yml:43` 的註解逐字：「【上游未定案，本檔是它第一個落地的字面】
[req:FR-F1] 只說『以單一看板自訂欄位承載目前 stage 的 slug ＋ 編號』，**從未指名該欄位
叫什麼**。U-3 的 `write_field` 在欄位不存在時會**自動建立**（TEXT），所以這個字串寫錯
就是在正式看板上多開一個欄位。」

**既有自動化層為何沒抓到**：這不是邏輯錯誤——任何字串都會讓程式正確執行。自動化能驗
「欄位被建立了」，驗不到「這個名字是對的」。這是需要人看一眼的判斷（撰寫標準 §1 的
第 3 類）。且它是**一次性事件**：欄位一旦建立，之後的同步都走既有欄位。

### 受測介面

- Workflow: `.github/workflows/aidlc-sync-forward.yml` → push — `stage_field_name` 輸入值
- Workflow: `.github/actions/aidlc-sync-board/action.yml` → composite — `ensure_field` / `write_field`
- 外部相依: GitHub Projects v2 的 `createProjectV2Field`

### 前置條件

1. 確認 #16 上目前**沒有**同名欄位（本 intent 交付前的實測狀態）：
   ```bash
   gh project field-list 16 --owner opendiamonds --format json --jq '.fields[].name'
   ```
2. `AIDLC_SYNC_TOKEN` 已建立且啟用正向同步（Bolt 0／1 gate 已放行）。
3. 已與 gate 確認 `stage_field_name` 的字面值就是要落地的那一個。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | `grep -n "stage_field_name" .github/workflows/aidlc-sync-forward.yml` | 印出的字面值與 gate 核可的名稱**逐字相同** |
| 2 | 觸發一次正向同步（推一顆 record 變更） | workflow run 為 `success` |
| 3 | 重跑前置步驟 1 的欄位列舉 | 出現且**只出現一個**新欄位，名稱與步驟 1 的字面值逐字相同 |
| 4 | 檢視該欄位型別 | 為 `TEXT`（`write_field` 自動建立的型別） |
| 5 | 檢視該 intent 的 item 在該欄位的值 | 形如 `requirements-analysis (2.3)`，與該 record 的 `Current Stage` 一致 |
| 6 | 再觸發一次同步 | 欄位數**不變**（`ensure_field` 對既有欄位回 `FieldRef` 而不重建） |

### 通過條件

- 步驟 3 只新增一個欄位，名稱與核可值逐字相同。
- 步驟 6 的第二次同步未新增第二個欄位。

### 失敗徵兆與對應肇因

| 徵兆 | 肇因 |
|---|---|
| 步驟 3 出現兩個名稱相近的欄位 | `stage_field_name` 在兩次執行之間被改過，或既有欄位型別不同而觸發重建 |
| 步驟 5 的值為空 | `write_field` 建立了欄位但寫入失敗——依 [US:S-5 AC 2]，Status 寫入仍應照常完成 |
| 步驟 6 新增第二個欄位 | `ensure_field` 的既存判定失效 |

### 追溯

- 實作：`.github/workflows/aidlc-sync-forward.yml`、`.github/actions/aidlc-sync-board/board.sh`
- 自動化對應：`.github/actions/aidlc-sync-board/run-stub-tests.py`（`ensure_field` 的 stub 層行為）
- PR／commit：本 intent 尚未 commit，待 Bolt 1
- User story：S-5

---

## TC: README 的看板連結對未登入的讀者打得開

- plan: AI-DLC ↔ GitHub Projects 同步（手動）
- priority: P2

### 目的

驗證 README 宣告的「需求正本」對它的實際受眾（第一次進這個 repo 的協作者）真的取得得到。

### 背景

**症狀（本 intent 內實測）**：README 的看板連結**匿名存取回 404**——Project #16 為
`public: false`，而本 repo 為 `public`。新舊連結皆是。

**既有自動化層為何沒抓到**：`validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]`
驗的是**字串在不在**（本 stage 之前連這一項都沒有，是這一輪補上的）。字串在，連結卻
打不開——「宣告了正本在哪」與「讀者取得得到」是兩件事，而自動化只驗得到前者。要驗後者
需要一個未登入的工作階段，CI 的 `GITHUB_TOKEN` 永遠是登入狀態。

ADR-0016 §9 只授權修 URL 形狀（`/orgs/` → `/users/`），形狀已修正；**「public repo 的
README 宣告需求正本在一個外部讀者打不開的看板」是另一個問題**，屬產品決定。

### 受測介面

- Workflow: `.github/workflows/ci.yml` → pull_request — `repo-contract` job 執行字串檢查
- 外部相依: GitHub Projects 的公開性設定（`public: false`）

### 前置條件

1. 一個**未登入**的瀏覽器工作階段（無痕視窗，且未帶 GitHub cookie）。
2. 或以未帶憑證的 curl：`curl -s -o /dev/null -w '%{http_code}\n' https://github.com/users/opendiamonds/projects/16`

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | `grep -n "projects/16" README.md` | 印出「Requirements Source」段落中的連結 |
| 2 | 以未登入的 curl 取步驟 1 的 URL | HTTP 狀態碼為 **200**（目前實測為 404——這是已知的未關閉缺口） |
| 3 | 以無痕視窗開啟同一 URL | 看得到看板內容，**不得**是 404 頁面或登入導向 |
| 4 | `python3 scripts/validate_repo_contract.py` | 通過——確認字串層的斷言仍在（它與步驟 2／3 驗的不是同一件事） |

### 通過條件

- 步驟 2 的狀態碼為 200。
- **本案例目前預期為失敗**：#16 為非公開。通過的前提是產品決定「把看板轉公開」或
  「在 README 註明需授權」——後者的話本案例的通過條件要跟著改寫為「README 明載需授權」。

### 追溯

- 實作：`README.md`、`scripts/validate_repo_contract.py`
- 自動化對應：`scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]`（字串層，**驗不到可達性**）
- PR／commit：本 intent 尚未 commit
- User story：S-11
