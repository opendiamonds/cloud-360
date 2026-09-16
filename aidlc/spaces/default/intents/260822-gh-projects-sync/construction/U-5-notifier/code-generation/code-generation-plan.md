# Code Generation Plan — U-5 通報

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-5-notifier · kind: library
     Created: 2026-09-05T00:53:22Z（讀自 date -u） -->

## 交付物與落點

**`.github/actions/aidlc-sync-notify/`** — 獨立 composite action（`nfr-requirements/tech-stack-decisions.md` 定案：與 U-3 打的是不同 API 面——Issues REST 而非 Projects v2 GraphQL——且驗證對象是 issue 生命週期）。`shell: bash`，以 `gh issue list／create／comment／edit／close` 子命令操作（有現成子命令就不手寫 GraphQL），憑證只經 `env: GH_TOKEN`（零憑證型 input，沿 U-3 SEC-1）。

沿用 U-1〜U-4 的形狀：**邏輯放 `notify.sh`，`action.yml` 只做介面轉接**，以 `operation` 分派 [ad:component-methods.md] §C-5 的兩個方法：`notify(FailureIdentity, detail) -> IssueRef`、`resolve_if_open(FailureIdentity)`。記憶體是 GitHub issue 本身，**不新增任何持久狀態**（ADR-A8）。

## 實測依據（本站唯讀查證，2026-09-05T00:5xZ；皆為 `gh` 的實際回應）

| 事實 | 取得方式 | 對實作的直接約束 |
| --- | --- | --- |
| repo **尚無** `aidlc-sync-alert` label（現有 `aidlc`、`aidlc:accepted`、`doc-sync`）；無任何帶該 label 的 issue | `gh label list --search aidlc`；`gh issue list --label aidlc-sync-alert --state all` | label 必須先存在才能 `--label` 列舉；由本 action 冪等建立（裁決 3） |
| `opendiamonds` 名下**沒有** sandbox／測試 repo（11 個 repo，公開的只有 `cloud-360`、`tg_bot`、`Credit-Lending`） | `gh repo list opendiamonds` | live 測試若要開真 issue，只能在 `cloud-360` 本身（裁決 4） |
| 擁有者 token 的 `repo` scope 涵蓋 Issues 寫入，PRE-1 第二輪已以 issue #538 實測開 issue | `PRE-1-results.md:87,181`；`gh issue view 538` | 開 issue 不需額外權限；#538 為「探測 issue 留下永久編號」的既有先例（標題即寫「可直接關閉」） |
| GitHub issue 搜尋索引對剛建立的 issue 有延遲 | `tech-stack-decisions.md`（本站設計時已定） | 搜尋一律 `gh issue list --label … --json number,title,body` ＋ 本地比對內文首行的機器可讀鍵，**不用 `gh search issues`** |
| U-6 R-6.1a／R-6.1b：迴圈結束後對本輪處理成功的每個 intent × 五個失敗碼（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`／`Failed`）各呼叫一次 `resolve_if_open`；U-5 R-3／[Q2=A]：**每輪一次查詢**列舉全部開啟中通報 issue | 兩單元的 `business-rules.md` | 兩者字面衝突（逐鍵呼叫 × 每次都列舉 ＝ Q2=B 被否決的 30 次呼叫）。以 **批次鍵** 介面收斂（裁決 1）：一次呼叫帶多個鍵、一次列舉、逐鍵判定——每個鍵的語意與單獨呼叫完全相同 |
| U-6 R-5.12「每一種失敗都交 C-5 `notify`」含 `write_field`／`write_body` 的 `Failed` | U-6 `business-rules.md:122` | `notify` 的 `reason_code` 值域為五個失敗碼（含 `Failed`），比 U-5 `domain-entities.md` 列的四個多一個（裁決 2） |

## 計畫步驟

- [x] **Step 1 — `action.yml` 介面**：兩個 `operation`。inputs：`intent_id`、`reason_code`、`stage`（FR-E3 的 stage 標識）、`detail`（`notify`）；`keys`（`resolve_if_open`，換行分隔的 `<intent_id>/<reason_code>`，一鍵即一行）；`label`（預設 `aidlc-sync-alert`）；`alert_repo`（預設 `GITHUB_REPOSITORY`，live 測試與未來搬遷用）。**零憑證型 input**。outputs：`issue_number`、`action`（`created`／`commented`／`deduplicated`）、`count`（標題 `×N` 的新值）、`closed_numbers`（換行分隔）、`closed`（計數）、`message`。逐 operation 在 description 列必要 input 與有效 output。
  **追溯**：[ad:component-methods.md] §C-5、[req:FR-E3]
- [x] **Step 2 — `notify.sh` 基座**：`fail`／`emit`／`gh_output`（沿 U-2〜U-4）；`require_repo`；`gh` 包裝（子命令非零 exit 即失敗，`--json` 結構化輸出再 `jq`，**不得**解析人類可讀表格）；鍵的正規形式——內文首行 `<!-- aidlc-alert: intent=<intent_id> reason=<reason_code> -->`（`domain-entities.md`）、標題 `[aidlc-sync] <intent_id> / <reason_code> (×N)`；`reason_code` 允許集合 {`ExternalError`, `Rejected`, `Aborted`, `CannotCreate`, `Failed`}（裁決 2）——五種正常判斷碼傳入即 `fail` exit 2（R-1：它們**根本不該呼叫** `notify`）；`detail` 的防禦性清洗（裁決 5）。檔頭 docstring 沿 `agent_router.py` 深度：契約段、通報／紅燈分流表（R-1 群）、安全邊界段（SEC-1 關閉別人看得到的 issue、SEC-2 公開 issue）、錯誤模型（唯一拋例外的路徑是 R-4）。
  **追溯**：R-1 群、R-4、SEC-1、SEC-2
- [x] **Step 3 — label 冪等建立**：`gh label list --json name` 找不到 `<label>` 時 `gh label create <label> --color … --description …`；已存在即跳過（裁決 3）。
- [x] **Step 4 — `notify`（R-2 群四支分流）**：`gh issue list --label <label> --state open --json number,title,body --limit 200` → 本地過濾「內文首行鍵逐字相符」（R-2.1：**不比標題**）→ 0 筆：`gh issue create`（內文第一行為機器可讀鍵；FR-E3 三要素——intent 識別字、stage 標識、`date -u` 的 ISO 8601 時間戳；`detail`），`action=created`；1 筆：`gh issue comment`（時間戳＋detail）＋ `gh issue edit --title` 把 `×N` 加一（N 由標題解析，解析不到時以「既有 comment 數＋1」重算——計數是給人看的，判定依據永遠是實際 comment 數與開關狀態），`action=commented`；>1 筆：取 **issue 編號最小者**（R-2.2）追加＋計數，其餘同鍵 issue 逐一 `gh issue close --comment "與 #<最舊> 重複…"`，`action=deduplicated`、`closed_numbers` 列出。**任一 API 失敗 → exit 1、`result=external_error`，不再呼叫 `notify`**（R-4：不可遞迴通報）。
  **追溯**：R-2.1／R-2.2、[req:FR-E1]／[FR-E3]、[US:S-8 AC 1–3]
- [x] **Step 5 — `resolve_if_open`（R-3 群，批次鍵）**：解析 `keys`（≥1 行，每行 `<intent_id>/<reason_code>`，格式不合即 exit 2）→ **一次** `gh issue list --label <label> --state open --json number,body` → 逐則解析內文首行鍵 → 鍵 ∈ `keys` 者 `gh issue close --comment "本輪未再發生…"`；鍵 ∉ `keys` 者**不動**（涵蓋「仍失敗」與「不屬本輪」，R-3.2）；`keys` 中沒有對應 issue 的鍵為 no-op（§C-5 逐字）。輸出 `closed`／`closed_numbers`。關閉失敗 → exit 1（呼叫端 U-6 R-6.1c：只記 log 與紅燈，不回滾）。
  **追溯**：R-3.1／R-3.2、[Q2=A]、U-6 R-6.1
- [x] **Step 6 — stub 測試 `run-stub-tests.py`**（離線；PATH shim 偽裝 `gh`，以暫存 JSON 檔為 issue 存放區，實作 `issue list／create／comment／edit／close／view` 與 `label list／create` 的最小子集並記錄 `calls.jsonl`）：0 筆 → 建立且內文首行為鍵、含 FR-E3 三要素、`action=created`；1 筆 → comment ＋ 標題 `×2`、`action=commented`、零 create；>1 筆 → 最舊者收到 comment、其餘被關閉且 comment 含「與 #<最舊> 重複」（R-2.2 以編號非建立時間：fixture 讓較新編號的 `created_at` 較早）；**標題被改過仍命中**（body 鍵不變）；**標題像但 body 鍵不同 → 不命中、不關閉**（R-2.1）；`reason_code` 為五種正常碼之一 → exit 2、零 API 呼叫（R-1）；`resolve_if_open` 只關 `keys` 內的鍵、其餘 intent 與仍失敗的鍵不動、缺 issue 的鍵 no-op、批次三鍵只發**一次** list；label 缺席時自動建立、存在時零 create；API 失敗（shim 回非零）→ exit 1、`result=external_error`、**零**第二次 create（R-4）；`detail` 內的 token 形狀字串（`ghp_…`／`gho_…`／`github_pat_…`）與 `Authorization:` 行被遮罩（裁決 5）；SEC-1 機械斷言 `action.yml` 無憑證型 input。
  **追溯**：[ug:unit-of-work.md] U-5 完成判準（開啟中數為 1 且 comment 數 +1）、R-1〜R-4
- [x] **Step 7 — live 測試 `run-live-tests.py`**（對 `alert_repo`，預設 `opendiamonds/cloud-360`；無 `GH_TOKEN` 或無 issues 寫入權時 exit 3 明確 skip）：進場防呆——`intent_id` 必以 `aidlc-sync-test-` 開頭、且測畢**必須**把本輪建立的全部 issue 關閉（`trap`）。步驟：(a) `notify` 兩次 → 第二次 `action=commented`，`gh api …/issues/<n>` 的 `comments` 為 1、標題 `×2`、開啟中同鍵 issue 數為 1（**完成判準逐字**）；(b) harness 以 `gh issue create` 手動再開一則同鍵 issue（模擬並行重複）→ `notify` → `action=deduplicated`、最舊者保留、新者已關閉且 comment 含「重複」；(c) `resolve_if_open` 帶該鍵 → 關閉，帶另一個不存在的鍵 → no-op；(d) 清理：關閉本輪全部 issue，`gh issue list --label … --state open` 過濾本輪 `intent_id` 為空。**每次執行會在 public repo 留下 2〜3 個已關閉 issue 的永久編號**（裁決 4）。
  **追溯**：[ug:unit-of-work.md] U-5 驗證方式「⑤Issues REST 行為」
- [x] **Step 8 — 突變驗證**（至少四條）：①鍵比對改成比標題 → R-2.1 案紅；②去重改留最新者 → R-2.2 案紅；③`resolve_if_open` 忽略 `keys` 一律關閉 → 「其餘不動」案紅；④API 失敗時再開一則「通報失敗」issue → R-4 案紅。每條改壞 → 紅 → 還原 → `diff -q` → 複跑綠。
- [x] **Step 9 — 規格註解與文件**：每個測試函式加 §4.4 註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`；`@api` 填實際觸及的 `gh issue` 子命令或 REST 路徑，不得捏造）；`notify.sh` 檔頭如 Step 2 所列。
- [x] **Step 10 — `code-summary.md`**（orchestrator 執筆）。

## 需 Plan Approval 裁決的五項介面判斷（上游未逐字指定，本計畫的落法）

1. **`resolve_if_open` 的介面為批次鍵**：input `keys` 為換行分隔的 `<intent_id>/<reason_code>` 清單，一鍵即一行。U-6 R-6.1a 要求「對每個待關閉鍵各呼叫一次」、U-5 R-3／[Q2=A] 要求「每輪一次查詢」——逐鍵呼叫而每次列舉正是 Q2=B 被否決的 30 次呼叫。批次讓 U-6 一個 step 帶全部鍵、一次列舉、逐鍵判定，**每個鍵的語意與單獨呼叫完全相同**（不存在即 no-op），簽章的語意未改、只是允許一次帶多個。
2. **`notify` 的 `reason_code` 允許集合為五個**：`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`／**`Failed`**。U-5 `domain-entities.md` 列四個，但 U-6 R-5.12 逐字「每一種失敗都交 C-5 `notify`」且其 R-6.1b 的鍵值域含 `Failed`（`write_field`／`write_body` 的不連坐失敗也需要人知道）。五種正常判斷碼傳入 → exit 2（R-1：不該呼叫）。
3. **label `aidlc-sync-alert` 由本 action 冪等建立**，不列為部署前置條件。repo 目前沒有這個 label；若列為前置，第一次真實通報會因 `--label` 不存在而失敗，而那正是需要通報的時刻。代價：`GH_TOKEN` 需 issues 寫入權（本來就需要）。
4. **live 測試在 `opendiamonds/cloud-360` 開真 issue**（`intent_id` 前綴 `aidlc-sync-test-`，測畢全部關閉）：沒有 sandbox repo，且 PRE-1 已有 #538 先例。每次執行留下 2〜3 個已關閉 issue 的永久編號、公開可見。替代（不跑 live、只信 stub）會讓完成判準「開啟中數為 1 且 comment 數 +1」只在 shim 上成立——而 shim 是我們自己寫的。`alert_repo` input 保留把目標換到別的 repo 的能力。
5. **`detail` 的防禦性清洗**：遮罩 `ghp_`／`gho_`／`github_pat_` 形狀的字串與 `Authorization:` 行、單行化、截 2000 字元。SEC-2 說「兩邊都要守」（U-3 不放、U-5 不貼），這是 U-5 那一邊的具體形式；不做語意過濾（做不到也不該做）。

## 測試策略對齊

Test Strategy = Standard。stub 層約 16 案，live 層 4 步。

## 已知的上游開放項（不阻擋本單元程式碼，列入 summary）

- U-8 的元件集合已由 ADR-0015 §5 補上 C-5（確認人 Bolt 3 gate）；U-7 的 `resolve_if_open` 承接在其 `business-logic-model.md` 邊界情形表——兩者都在各自單元實作時接線。
- NFR-S1 驗收判準欄的權限集合表述（ADR-0015 §8，Bolt 0 gate）。
- 通報 issue 的內容也是公開的稽核紀錄（ADR-0006 audit logging 面向）；本單元只保證 FR-E3 三要素存在，不保證呼叫端的 `detail` 有用。
