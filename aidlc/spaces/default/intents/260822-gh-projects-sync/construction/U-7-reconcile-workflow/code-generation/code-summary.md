# Code Summary — U-7 對帳 workflow 與編排器

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service
     Generated: 2026-09-05T16:29:13Z（讀自 date -u） -->

## 交付物

| 檔案 | 行數（`wc -l`，orchestrator 實測） |
| --- | --- |
| `.github/workflows/aidlc-sync-reconcile-impl.yml` | **928**（`id: reconcile` 的 `run:` 佔 765） |
| `.github/workflows/aidlc-sync-reconcile.yml` | **77** |
| `.github/actions/aidlc-sync-reconcile/run-reconcile-tests.py` | **1461** |

不新增依賴。**未動任何 U-1～U-6／U-10a 的既有檔**。未 commit、未 push、未動用真實 API。

## 驗證（orchestrator 自行重跑，非轉引 agent 報告）

| 項目 | 結果 |
| --- | --- |
| U-7 行為測試 | **35 tests, 189 checks, 0 failures** |
| `validate_repo_contract.py` | `passed` |
| `validate_env_contract.py` | `passed` |
| `ci.yml`（U-10a 未被波及） | 仍 `103 0` |
| U-6 的測試（未被波及） | 39 tests, 145 checks, 0 failures |
| 突變驗證 | **13 條**，13/13 讓「**對應的那一條**」變紅 |

### 四個跨單元常數全部從來源推導，零自抄（orchestrator 開檔核對）

| 常數 | 推導來源 |
| --- | --- |
| `SYNC_MARKER` | `record.sh` 的 `^SYNC_MARKER="..."`（`:100`） |
| `REVERSE_PR_LABEL` | **U-6 的 impl**（`:108`） |
| 終局 Status | `map.sh` 的 R-3.3 那一列（`:115`） |
| record 路徑 | `record.sh` 的白名單 |

### Q1 的跨單元契約已機械驗證（orchestrator 獨立查證，不採信報告）

| 路徑 | `last_written_status` 取值 | 判斷 |
| --- | --- | --- |
| R-6.1 **補平**（`impl:719`） | `$st`（本輪判定，即它剛寫進看板的值） | ✓ |
| R-6.5 **修復**（`impl:778`） | **`$ws`（`board_status`，看板此刻真的有的值）** | ✓ **比照抄 `$st` 更正確** |

第二列的措辭已更正（reviewer iteration 1 Minor）：**原寫「比照抄 `$st` 更正確」是過度宣稱**。reviewer 代數證明 R-6.5 走到寫入那一刻，外層條件與內層前提合起來**保證 `board_status` 與 `dec_status` 逐字相等**，寫哪一個在行為上無差別。正確描述是：**兩者在此保證相等，取 `$ws` 只是保留「這是觀察到的看板事實、不是本單元的判定」的意圖標記供維護者辨讀**，不存在實質正確性差異。

**跨 U-6／U-7 的多輪測試是真的跨單元**：`run-reconcile-tests.py:158` 以 `importlib` 載入 U-6 的 runner，直接執行 **U-6 的真實編排腳本**。三輪：U-6 寫成功但 `commit_and_push` exit 3（狀態檔沒落地）→ U-7 走 R-6.5 修復 → U-6 再跑，斷言其 `expected` 是修復後的值而非補平前的舊值。

## 待 Bolt gate 追認的清單（十項；**#2 與 #3 是重點**）

### 1. Q1=A 對 R-6.1／R-6.5 字面的擴充（已裁決）

兩條回寫路徑都額外寫 `last_written_status`。程式就地標明。**確認人：Bolt 1 gate。**

### 2. **R-6.1 的 `last_synced_at` 與 U-6 的 R-5.13 語意相衝**（潛伏，Bolt 2 gate）

R-6.1 與 ADR-0015 §13 都明列該欄，但 **R-5.13 定義它是「受管區塊上一次成功寫入的時刻」**，而補平路徑一個字都沒寫進受管區塊（R-6.2 明禁）。

**後果鏈**：U-6 的 R-5.6 以 `closed_at > last_synced_at` 判斷反向 PR 被拒的告示是否還沒送 ⇒ 補平把它推進到本輪 ⇒ 一則**尚未送出**的告示被判為已送 ⇒ **[US:S-6 AC 5] 永久靜默**。U-6 的 R-5.12 第三種正是為了避免同一件事而刻意不推進它。

**可達路徑**：反向 PR 於 T1 關閉未合併 → U-7 在 U-6 下一輪之前補平該 intent → `notice_due` 恆為假。需 U-8 上線才實際發生，**今日為潛伏**。

**建議修法**：R-6.1 的欄位集合移除 `last_synced_at`（理由與 R-6.2 同源）；R-6.8 不受影響（它有「已確認區塊存在於看板上」的獨立理由）。

### 3. **R-7.2 的推送落點沒有合併路徑——R-6 群的目的因此不可達**（Bolt 2 gate）

回寫落在 `aidlc-sync/reconcile/<date>`，而**沒有任何已核可規則說這些 commit 怎麼回到 `ut`**（U-8 的反向分支有 PR，本單元沒有）⇒ R-6 群（含 Q1=A 的修復）到不了 U-6 讀取的那一版 record ⇒ **R-6 存在的目的不可達**。

**orchestrator 獨立查證**：`ci.yml` 的 push 觸發分支為 `main`／`ut`／`danniel/**`／`chore/**`——`aidlc-sync/reconcile/*` **不在其中**。而 ADR-0015 §13 的代價段寫著「會被觸發的是 `ci.yml`」，那段是在 Q6=A 決定分支落點**之前**寫的，**兩個決定沒互相核對過**。

**實作的處置正確**：不靜默——`impl:912` 在報告寫「**回寫落在 `<branch>` 上，需要人工合併回 `<trunk>`**」，`:921` 在 log 同樣明說。

**修法擇一**：(a) 比照 U-8 由本單元開 PR（ADR-0015 §8 已把 `Pull requests: write` 納入權限集合，前提已具備）；(b) 放寬 U-4 的 R-3.1。

### 4. R-6.5 對「判定的 Status 為 null」全無規定

本站推導：修其餘五欄、**不寫** `last_written_status`。理由：R-6.5 的安全論證（「人為改動不會恰好把看板改成 record 的值」）只在看板 == 判定時成立；判定為 null 時看板值可能是任何人放上去的，記進去會讓 U-6 下一輪的 `expected` 與人為值相符而**靜默覆寫**掉它（[req:FR-G3] 保護的正是這類 item）。

代價如實記載：該欄可能停在舊值、日後產生一次假 `Aborted` ＋ 通報——**那是大聲的失敗**，優於靜默覆寫。由 `test_r6_5_repair_with_null_status_does_not_claim_a_write` 與突變 M13 鎖住。

### 5–10（其餘）

| # | 項目 |
| --- | --- |
| 5 | R-1 群的表沒有「單一 intent 的 API 失敗」這一列。依 ADR-A5 原則計入分子（兩方向代價不對稱：偏高會消除注意） |
| 6 | R-3.4 的 `deferred` 形式取其自列的第一個候選；R-3.4 逐字「本站不裁定具體形式」。今日 registry 6 筆、上限 50，此清單恆空 |
| 7 | `reconcile_batch_size: "50"` 是薄外層第一個落地的數字（R-3.3 逐字「待 PRE-1 第 2 項實測後定」）。impl **刻意不給預設值**，由測試鎖住 |
| 8 | `stage_field_name: AI-DLC Stage` 沿用 U-6 的字面，上游從未定案（U-6 已列入待 gate） |
| 9 | `components.md` 給 reconcile 的元件鏈含 **C-2 但無任何規則呼叫它**（R-6.2 明訂不重寫受管區塊）。孤兒成員 |
| 10 | R-6.8 的雜湊修復**可能吸收人為的受管區塊編輯**（Minor）：修復窗口內若人也改了區塊，U-8 永遠看不到那次編輯 ⇒ 反向同步靜默漏一筆。窄但真實 |

## 對計畫的偏離（五項）

1. **inputs 九個而非計畫的七個**：另加 `trunk_ref`（R-7.1 要求明訂 ref，而 ADR-A10 不得寫死主幹名）與 `reconcile_branch_prefix`（R-7.2 的推送落點）。
2. **R-8 的資料來源用兩支**：`read_item` 也回 `issue_state`，但 R-8.1 逐字指名 `read_issue_state`（正是 R-8 群要承接的孤兒契約），故兩支都呼叫、以後者為準。每 intent 因此 2 次讀取，與 `performance-requirements.md` 的成本表一致。
3. **不使用 `block.sh`（C-2）**，存在性檢查只驗四支 action ＋ U-6 的 impl（後者是 `REVERSE_PR_LABEL` 的推導來源）。理由見待追認 #9。
4. **突變 13 條而非計畫列的 6 類**：必打點全數涵蓋，另加 M13（#4 的守衛）與 M5／M11／M12。
5. Step 14 由 orchestrator 執筆。

## 未完成項目（誠實列出）

1. **沒有 live 測試**。硬規則禁止動用真實 API，故 `read_issue_state` 的 GraphQL 回應形狀、`write_status` 對真實看板的 `Aborted` 行為、`commit_and_push` 在 origin 上首建分支的實際行為，**全部只有 stub 覆蓋**。（U-6 有 live 層，本單元沒有——**這是兩個單元之間的覆蓋不對稱，gate 應知情**。）
2. **測試未接進 CI**。三支腳本（U-10a 兩支、U-6 一支、U-7 一支）目前**都只有人工執行才會跑**。
3. **`latency_samples` 未填**，依 `domain-entities.md` 的裁定，且未以本輪執行耗時冒充。
4. **`tcms-test-cases` stage 未執行**——不在本次派工範圍，但 `project.md ## Mandated` 對本 intent 是 **blocking**。
5. **SEC-2 只被單點驗證**：測試以一個探針字串證明 `traceable_row` 不會流進報告，但「不得含 record 內容片段或任何 API 回應 body」那半句沒有對應斷言，目前靠「報告組裝段只讀 id 與計數」這個結構事實。

## 送審前自檢（`project.md` 六項）

| # | 自檢項 | 結果 |
| --- | --- | --- |
| 1 | **可達性** | **抓到兩項**：#3 的「R-6 目的不可達」經 `ci.yml` 分支清單實測確認；#2 的 `last_synced_at` 衝突已寫出完整可達路徑並判定為潛伏（需 U-8 上線） |
| 2 | **契約端點三問** | `last_written_status`：U-7 兩條路徑寫、U-6 讀、legacy 回退已測。**抓到一個孤兒**：C-2 在元件鏈中但無呼叫者（#9） |
| 3 | **引用逐字核對** | 四個跨單元常數的推導行（`:100`／`:108`／`:115`）、`impl:719`／`:778` 的兩條回寫、`:912`／`:921` 的人工合併揭露、`ci.yml` 的分支清單——全部開檔驗證 |
| 4 | **檔案集合一致性** | 與 U-6 比對：U-6 有 stub＋live 兩支，**U-7 只有 stub**。差異有理由（硬規則禁止真實 API）但**構成覆蓋不對稱**，已列為未完成項第 1 項 |
| 5 | **跨檔傳播** | 本輪為新增檔。`ci.yml` 仍 `103 0`、U-6 測試仍 39/145/0，兩者實跑確認未被波及 |
| 6 | **可算的數字先算再寫** | `928`／`77`／`1461` 行、`35 tests, 189 checks, 0 failures`、13 條突變——**全部由 orchestrator 自行重跑／重量**，非轉引 |

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T16:58:30Z（`date -u` 讀出）
**Iteration:** 1

### 停止判準（本輪開始前訂定，如實記載）

依 brief 訂定：只找到 Minor，或 Major 屬既存漏審／新設計問題 → 收斂為 open-items 帶進 gate；找到的 Critical／Major 若是本輪（code-generation）實作動作本身引入 → 修完再跑 iteration 2。**本輪結果：1 項 Critical（既存漏審，非本輪引入，但本輪的處置方式本身是新的過程缺陷）＋ 3 項 Major（其中 2 項為本輪新引入：測試覆蓋缺口、C-2／U-2 代號混淆；1 項為既存但本輪才可查證：U-6 push 無過濾造成的自我再觸發）。依判準應再跑一輪聚焦這 4 項。**

### 最高優先：兩個自陳重大缺口的獨立驗證

#### (A) 「R-6 群的目的目前不可達」——**成立，且找到一個 lead 未揭露的相關新後果**

**逐項查證**：
- `ci.yml` 的 push 觸發分支：`git diff --numstat -- .github/workflows/ci.yml` → `103 0`（未被本輪任何動作影響）；`grep -n "^on:" -A15 .github/workflows/ci.yml` 逐字確認分支清單為 `main`／`ut`／`danniel/**`／`chore/**`，`aidlc-sync/reconcile/*` 確實不在其中。
- ADR-0015 §13 的時序：文字比對確認「代價：……會被觸發的是 `ci.yml`」與 Q5=A 的 C-4 決定同一時間戳段落（`00:57:28Z`），而 Q6=A（分支落點）的時間戳為 `01:31:09Z`，**在其後**——lead「兩個決定沒互相核對過」的推論成立。
- 有沒有 lead 沒找到的合併路徑：`grep -n "commit_and_push\|create.*pr\|gh pr create" .github/actions/aidlc-sync-record/record.sh` 確認該函式**只 push、不開 PR**；`find aidlc/.../construction -maxdepth 1` 確認 `aidlc-sync-reverse*.yml` 尚未交付（U-8 未上線）——**目前確實沒有任何機制把 `aidlc-sync/reconcile/<date>` 併回 `ut`**，lead 的核心主張成立。
- 「報告與 log 明說需人工合併，不靜默」：讀 `impl.yml:912`／`:921` 確認屬實，這個處置本身是對的（大聲失敗優於沉默失真）。

**但本輪查證發現 lead 未揭露的相關新後果**：`aidlc-sync-forward.yml`（U-6）的 `on:` **刻意不加分支過濾**（`push:` 對任何分支觸發，程式碼註解逐字「選取是 registry 驅動的，不是事件 diff 驅動的」）。而 U-7 的 `commit_and_push` 用的憑證是 `sync_token`（ADR-0016 §1 的擁有者帳號 PAT，非 `GITHUB_TOKEN`）——`gh auth status` 實測目前使用中帳號的 token 為 `gho_` 開頭（OAuth token）而非 Actions 專用 token；U-6 自己的 `business-rules.md:65-67`（R-4.3）與其 code-summary 都已明文確認「PAT 推的 push 一樣觸發 workflow」是本 repo 查證過的既定行為（非 `GITHUB_TOKEN` 就會觸發）。**結論：U-7 每次對任一 intent 補平／修復而推送到 `aidlc-sync/reconcile/<date>` 時，這個 push 會觸發 U-6 對該分支的一次完整 registry 全掃**——U-6 的 concurrency group 以分支名分組（`aidlc-sync-event-...-${{ ref_name }}`），與 U-7 自己的 daily run 及既有 `ut` 上的 U-6 run 都不同組，會**真的併行**執行。若當下 repo 內同時有多個 intent 存在真實漂移（ADR-0015 §2 已明文承認 Projects v2 無 compare-and-swap、寫入視窗內會靜默丟失協作者的改動），這個被 reconcile 自己的推送**意外**觸發的 U-6 run，會在 U-7 主迴圈仍在跑的同時，對**其他**intent 獨立呼叫一次 `write_status`——這是一個 lead 的十項待追認清單與五項偏離都沒有提到的第三方寫入者，疊加在 ADR-0015 §2 已知的競態視窗之上。此發現屬**既存**（U-6 的 `push:` 無過濾與 U-7 的 PAT 推送兩個既有設計決定的交互作用），但只有在兩份 workflow 都已落地為真實檔案後才可查證，故計入本輪。

#### (B) 「`last_synced_at` 與 U-6 的 R-5.13 語意相衝」——**成立，但 lead 的定性嚴重低估了它的來歷與急迫性**

**逐字核對**：`impl.yml:716-723` 的 R-6.1 patch 確實含 `last_synced_at: $ts`；`business-rules.md` 的 R-6.2 逐字只排除 `managed_block_hash` 一欄。lead 對後果鏈的推導（反向 PR 於 T1 關閉未合併 → U-7 早於 U-6 下一輪先補平 → `last_synced_at` 前進 → U-6 的 `notice_due` 恆假 → [US:S-6 AC 5] 永久靜默）與「需 U-8 上線才實際發生」的判定，經獨立重推**成立**。

**但這不是 code-generation 時的新發現**——它是 **U-6 自己的 functional-design 審查 iteration 7**（`U-6/business-logic-model.md:543-604`，`Date: 2026-08-30T03:47:14Z`）已經找到、命名為 **C-7.1**、判為 **Critical**、且**逐字指名落點在 U-7 的 R-6.1／R-6.2**的既有發現。該輪 reviewer 明文寫「**C-7.1 與 C-7.2 應在 Bolt 1 開工前處理，不宜留給 code-generation 自行判讀**——兩者都會讓實作者在**沒有紅燈**的情況下做出違反 [US:S-6 AC 5] 的行為」，並指示不要再開修正迴圈、直接登錄 `open-items.md` 帶進閘門。**逐項機械核對**：
- `open-items.md:137` 確實登錄 C-7.1，deadline 逐字為「**Bolt 1 開工前**」（不是 Bolt 2 gate）。
- U-7 的 `business-rules.md`／`business-logic-model.md`／`domain-entities.md` 三檔的全部時間戳（`grep -oE "2026-08-3[01]T[0-9:]+Z"`）最晚為 `03:35:44Z`，**早於** C-7.1 被找到的 `03:47:14Z`——三檔從未回頭吸收這項修正。
- `bolt-plan.md` 的 Bolt 2 DoD（`grep -n "U-7\|Bolt"`）三條追加項（§3／§9／§13）**不含** C-7.1／R-5.13／`last_synced_at`。
- `ADR-0015` 全文（`grep -n "C-7\.1\|R-5\.13"`）**零命中**，即使該檔在 C-7.1 被發現之後仍有編輯（`stat` 顯示 mtime 晚於 `open-items.md`，但那次編輯是 ADR-0016 的無關內容）。
- U-7 本次 code-generation 的三份產出（plan／questions／summary）對 `open-items.md` **零引用**——而 U-1／U-2／U-10a／U-11 的 code-generation summary **都**引用了它。

**結論**：這不是「潛伏，Bolt 2 gate 追認即可」的新風險披露，而是一個**已有明確、更早期限（Bolt 1 開工前）、且該期限早已過期**的 Critical 缺陷，本應在 U-7 進 code-generation 之前就修掉（修法本身也早已確定：R-6.2 的禁動欄位由一欄擴為兩欄）。code-summary 把它降格陳述為「潛伏（Bolt 2 gate）」，等同**把一個已過期的強制關卡改寫成一個更弱、更晚的關卡**，而送審前自檢六項（尤其第 1 項可達性、第 3 項引用逐字核對）都應該在讀 `open-items.md` 時攔下這個落差——但六項自檢報告裡沒有任何一項提到 `open-items.md`。修法成本極低（R-6.1 的 patch 拿掉 `last_synced_at: $ts` 一行），不應該再拖到下一個 gate。

### 第二優先：測試是否真的在測東西

**35 tests, 189 checks, 0 failures 已重新執行確認**（本機重跑，非轉引）。以下為本輪獨立所做、與 lead 宣稱無關的抽驗：

| # | 動作 | 結果 |
|---|---|---|
| 1 | 移除 R-6.1（補平）patch 的 `last_written_status` 欄位 | 恰好 2 項失敗，命中 `test_r6_1_backfill_writeback_field_set` 相關斷言，無殃及其他測試 |
| 2 | 移除 R-6.5（修復）patch 的「`dec_status` 為空則不寫 `last_written_status`」防護 | 恰好 2 項失敗，命中 `test_r6_5_repair_with_null_status_does_not_claim_a_write`，無殃及其他測試 |
| 3 | 讓 `whitelisted` 誤入第三類排除（不計分母分子） | 恰好 4 項失敗，命中 `test_r2_3_no_third_exclusion_class`／`test_us_s3_ac6_whitelisted_has_no_list`，無殃及其他測試 |
| 4 | 讓補平成功也標記 `ROUND_RED=1` | 恰好 1 項失敗，命中 `test_us_s7_ac5_successful_backfill_is_not_red` |
| 5 | 讓薄外層 cron 撞上 `agentics-maintenance` 的 `37 0 * * *` | 恰好 1 項失敗，命中 `test_r5_cron_does_not_collide` |

以上 5 項抽驗（涵蓋 brief 指定的 M2／M3／M13 對應區域）**全部只命中正確的那一條測試**，佐證 lead「13/13 突變命中對應測試」的宣稱屬實、與 U-6 的「rc/exit」型假陽性不同型。

**跨單元多輪測試的真實性已驗證**：讀 `run-reconcile-tests.py:156-163`（`load_u6_runner`）與 `run-orchestration-tests.py:111-125`（`orchestrate_script`，從 `aidlc-sync-forward-impl.yml` 的 `id: orchestrate` 抽出 `run:` 逐字腳本）及 `run_round`（`subprocess.run([BASH, "-c", SCRIPT], ...)`）確認：`test_q1_cross_unit_last_written_status_round_trip` 的 round-1／round-3 **確實是 subprocess 執行 U-6 真實 bash 腳本**，不是重寫的替身。lead 的宣稱屬實。

**但本輪主動挖出兩個 lead 未發現、未列入十項待追認清單的零覆蓋分支**（皆以「整段拿掉錯誤處理，測試仍全綠」驗證）：

| 分支 | 驗證方式 | 結果 |
|---|---|---|
| `push_state()` 的整個失敗處理（rc≠0 時的 `Rejected`／`ExternalError` 分類、`notify_failure`、`ROUND_RED=1`，對應 R-6.4／R-4.1） | 整段改為 `return 0`（無條件視為成功、不通報、不紅燈） | **35 tests, 189 checks, 0 failures**——零測試命中 |
| R-6.1 補平路徑的 `write_sync_state` 失敗處理（「看板已補平但回寫失敗」分支） | 整段拿掉錯誤分支，強制視為成功並設 `wrote_state=1` | **35 tests, 189 checks, 0 failures**——零測試命中 |

這兩個分支目前**沒有任何測試在守**——若未來重構不慎讓推送失敗被靜默吞掉（不紅燈、不通報），現有 35 個測試不會發現。這正是本 intent 反覆出現、且 U-6 在同一 stage 已踩過的「看起來有保護，實際守不到」的同型風險，只是這次落在**完全沒寫斷言**而非「斷言用錯鍵名」。R-6.4／R-4.1 兩條規則本身的設計與實作看起來正確（見上方程式碼閱讀），這是測試覆蓋缺口，不是行為缺陷。

**抽查前提斷言**：抽驗 `test_r4_1_single_intent_failure_does_not_abort_round`、`test_r3_batch_limit_and_deferred_list`、`test_r8_issue_closed_with_non_done_status_is_listed`、`test_r8_issue_closed_with_done_status_is_not_a_mismatch`、`test_us_s7_ac5_successful_backfill_is_not_red` 五條，**每條都有明確的「前提」斷言**（先確認情境真的發生，再斷言後果），未發現 U-6 型的「空前提上恆真」問題。

**逐條對照 R-1～R-8 群與測試檔**：`grep -oE "R-[0-9]+\.[0-9]+"` 交叉比對，`business-rules.md` 定義而測試檔從未提及的規則僅 `R-1.2`（與 R-8.3 語意重複，已由 R-8 系列測試覆蓋實質）、`R-2.5`／`R-5.4`／`R-5.13`（皆為引用 U-6 規則的跨單元說明文字，非 U-7 自身規則）、`R-6.4`（見上方零覆蓋發現）——沒有找到「規則存在但完全沒被提及」以外的新缺口。

### 第三優先：Q1 的跨單元實作

**R-6.1／R-6.5 的欄位差異已逐字核對**（`impl.yml:716-723`、`:790-801`）：R-6.1 寫 `last_written_status = $st`；R-6.5 寫 `last_written_status = $ws`（僅當 `$st` 非空時）。

**嘗試推翻「比照抄 `$st` 更正確」的說法——部分推翻**：R-6.5 的外層條件是「`-n dec_status && board_status != dec_status` 為假」（即 `else` 分支），內層寫入的前提又要求 `$st` 非空——兩者合起來代數保證此時 **`board_status` 與 `dec_status` 逐字相等**（bash 字串比較，不是近似）。也就是說，在這條分支**真正執行寫入的那一刻，`$ws` 與 `$st` 是完全相同的字串**，寫哪一個在行為上沒有任何差別。code-summary 用「更正確」形容一個實際上不影響輸出的風格選擇，這句話本身**過度宣稱**——正確的描述應該是「兩者在此處保證相等，取 `$ws` 只是為了保留『這是觀察到的看板事實、不是本單元的判定』的意圖標記，供未來維護者辨讀」，而不是暗示存在一個實質正確性差異。判 Minor（自我審查用詞失準，非功能缺陷）。

**`read_issue_state` 雙來源、以其為準**：`performance-requirements.md:28-29` 逐字「`read_item` 1 次／`read_issue_state` 1 次」與程式碼呼叫次數一致，偏離理由成立。

### 第四優先（含 lead 主動揭露項的逐一裁決）

**偏離 #3「不使用 `block.sh`（C-2）」——判斷不成立，是本輪新引入的錯誤**：開 `aidlc/.../inception/application-design/components.md` 逐字核對元件代號——**`C-2` 是 `record-reader`**（`parse(state_md_text, intents_json_text, record_path) -> ParsedRecord`，且「承載形式：**與 C-1 同一個 composite action**」），**不是** managed-block 渲染器；managed-block 對應的元件代號是 **`C-6`**，其擁有單元才是 `U-2`（`construction/U-2-managed-block/`，`block.sh` 由此而來）。impl.yml 的註解（`:173-175`）與 code-summary 待追認 #9 把「單元 U-2（block.sh）」與「元件 C-2」兩個不同編號系統混為一談，導致兩個錯誤結論：(a) 宣稱「`components.md` 給 reconcile 的元件鏈含 C-2 但無呼叫者」——**假**，reconcile 呼叫 `map.sh`（C-1）時，依 `components.md` 逐字，C-2 的 `parse()` 就在同一個 composite action 內被呼叫，C-2 並非孤兒；(b) 真正沒被 reconcile 呼叫的是 C-6（managed-block／`block.sh`），但 `components.md:107` 給 reconcile 的元件鏈原文就只列 `C-2／C-1／C-3／C-5`（加 ADR-0015 §13 的 C-4），**從未包含 C-6**——所以「不呼叫 block.sh」根本不構成任何契約缺口，不需要被記成一個「孤兒成員」。這是送審前自檢第 2 項（契約端點三問）應該擋下卻沒擋下的一次誤判——核對方式應是開 `components.md` 逐字比對代號而非憑函式檔名（`block.sh`）推斷代號，本專案已有多筆「引用須逐字核對」的既有教訓（`project.md` 的 `intent-capture:c11` 等）適用於此。判 Major（自我審查產出了一個錯誤的契約結論，且同一錯誤同時寫進了程式碼註解與 code-summary 兩處）。

**其餘待追認／偏離項逐一覆核，結論皆維持**：
- 待追認 #4（R-6.5 對 Status 為 null 的安全論證）：**推翻失敗，論證站得住**。已用突變（上方第 2 項）驗證守衛真的在擋。
- 待追認 #5（R-1 群缺「單一 intent API 失敗」列）：如實記載的已知缺口，判斷與代價權衡（偏高優於偏低）合理，維持。
- 待追認 #6／#7（R-3.4 的 deferred 形式、`reconcile_batch_size` 無預設值）：均為明確標出「本站選擇，待上游定案」的誠實記載，維持。
- 待追認 #8（`stage_field_name` 上游未定案）：與 U-6 一致，維持。
- 待追認 #10（R-6.8 雜湊修復可能吸收人為編輯窗口）：時序推導合理，Minor 維持。
- 偏離 #1（inputs 九個而非七個）、#2（R-8 雙來源）：均逐字核對成立，維持。

### 覆蓋不對稱（第四優先另一半）

lead 的揭露（U-7 無 live 層，U-6 有）如實。本輪補充兩個**具體**、目前連 U-6 的 live 層都沒有涵蓋到的行為，讓「gate 應知情」的內容更具體：
1. `read_issue_state` 的真實 GraphQL 回應形狀（欄位是否確實叫這個名字、`open`／`closed` 的實際大小寫）——**這是全系統第一次呼叫這個方法**（R-8 群存在的理由正是它先前是孤兒契約），U-6 的 `run-live-tests.py`（L1～L4）不曾呼叫它，故它是一個**完全沒有任何單元的 live 層驗證過**的新契約點，不只是「U-7 沒有、U-6 有」的相對落差。
2. `record.sh` 的「origin 上沒有該分支時以 HEAD 為分叉點建立」這條分支（U-7 是第一個每天推新分支名的呼叫者），U-6 的 live 層只操作既有分支（`sync_branch` 固定），**這條 git 分支建立邏輯同樣沒有被任何 live 測試驗證過**。

兩者皆已被 lead 的「未完成項目 #1」概括揭露且正確地判為需要 gate 知情，本輪不新增為獨立扣分項，僅補上具體內容供 gate 參考。

### Attempted refutations that did not hold

1. 嘗試證明「R-6 群目的不可達」是誇大——**未推翻**，`ci.yml` 分支清單、`record.sh` 無開 PR 邏輯、U-8 未上線三項證據皆指向 lead 的結論成立（但找到一個 lead 沒發現的相關新後果，見上方 (A)）。
2. 嘗試證明 R-6.5 對 Status 為 null 的不回寫是不必要的保守（也許可以直接照抄 board_status）——**未推翻**，突變驗證確認拿掉這個防護會讓測試立刻抓到，安全論證本身也站得住。
3. 嘗試證明跨單元多輪測試其實是另一份重寫的替身腳本，並非真的執行 U-6 程式碼——**未推翻**，逐行讀 `load_u6_runner`／`orchestrate_script`／`run_round` 確認是真的 `subprocess` 執行從 `aidlc-sync-forward-impl.yml` 抽出的逐字腳本。
4. 嘗試證明「13/13 突變命中正確測試」的宣稱是誇大（懷疑有 U-6 型的假陽性）——**未推翻**，本輪獨立重做 5 項突變，每項都精準命中對應測試、無殃及其他測試。
5. 嘗試證明行數／測試數／`ci.yml` diff／U-6 測試數等「可算的數字」有誤植——**未推翻**，`wc -l`、實際執行測試、`git diff --numstat` 三者皆逐一重新量測，與 code-summary 逐字相符。
6. 嘗試證明 `read_issue_state` 的呼叫成本（每 intent 2 次）與上游成本表不符——**未推翻**，`performance-requirements.md:28-29` 逐字相符。

### Summary

**三類分佈**：新引入 2（測試覆蓋缺口——push_state／write_sync_state 兩處零覆蓋錯誤處理分支；C-2／U-2 代號混淆的錯誤自我審查結論）／既存漏審 2（R-5.13／`last_synced_at` 衝突：已由 U-6 iteration 7 判為 Critical 且訂出「Bolt 1 開工前」的期限，卻從未被吸收進 U-7 自身文件、`bolt-plan.md`、ADR-0015 或本次 code-generation 的送審前自檢，本輪重新發現時被誤判為「潛伏、Bolt 2 gate 即可」的新風險而非一個已過期的強制關卡；U-6 push 無分支過濾造成的自我再觸發，兩個既有設計決定的交互作用，只有兩份 workflow 都落地後才可查證）／新設計問題 0。

**核心結論**：code-generation 的實作品質本身相當扎實——928／77／1461 行、35/189/0 測試、5 項獨立抽驗突變全數精準命中、跨單元多輪測試貨真價實、Q1 的字面擴充理由正確、R-6.5 對 null 判定的安全論證站得住。**但存在一個已過期、被誤判嚴重度的 Critical 缺陷**（`last_synced_at` 與 U-6 R-5.13 的語意衝突，本應在 Bolt 1 開工前修好、修法早已確定，卻被本次送審前自檢當成全新的潛伏風險重新包裝並降級處置），加上兩個測試覆蓋缺口與一個錯誤的契約端點結論（C-2／U-2 混淆）。四項都成本低、修法明確，建議：(1) 直接在 R-6.1 拿掉 `last_synced_at` 這一行；(2) 為 `push_state()` 與 R-6.1 的 `write_sync_state` 失敗分支各補至少一條測試；(3) 更正 code-summary 待追認 #9 與 impl.yml 的相關註解，把「C-2 孤兒」的錯誤結論改為「C-6／`block.sh` 從未在 reconcile 的元件鏈內，非缺口」；(4) 揭露 U-6 的自我再觸發風險並記入待追認清單。修完後跑 iteration 2（本輪的問題不是新設計錯誤，預期一輪可收斂）。

VERDICT: NOT-READY

---

## Iteration 1 修正記錄（lead，2026-09-05T17:10:13Z）

四項全部處置完畢。**其中最重要的一項是我自己的過程缺陷，不是實作缺陷。**

| # | 嚴重度 | 分類 | 處置 |
| --- | --- | --- | --- |
| 1 | **Critical** | 既存漏審（但**降格陳述是本輪新引入的過程缺陷**） | **已修 ＋ 已更正定性**（見下） |
| 2 | Major | **新引入** | 兩條零覆蓋分支各補一條測試，M14／M15 突變驗證 |
| 3 | Major | **新引入** | C-2／C-6 代號混淆已更正，「孤兒」宣稱撤回 |
| 4 | Major | 既存 | **部分推翻**——防線②已擋掉主要後果（見下） |

### 1. Critical：我把一個已過期的關卡降格了

reviewer 查出這不是新發現，而是 **C-7.1**——U-6 的 functional-design iteration 7 已找到、判 Critical、逐字指名落點在 R-6.1／R-6.2，登錄於 `construction/functional-design/open-items.md:137`，**deadline 逐字為「Bolt 1 開工前」**，修法也早已寫定（「R-6.2 的禁動欄位由一欄擴為兩欄」）。

**我的第一版把它寫成「潛伏，Bolt 2 gate」——等同把一個已過期的強制關卡改寫成更弱、更晚的關卡。**

**根因是可指名的**：開工前查證**沒有讀 `open-items.md`**。U-1／U-2／U-10a／U-11 的 code-summary **都**引用了它，本單元沒有；而送審前自檢六項（尤其第 1 項可達性、第 3 項引用逐字核對）本應在讀它時攔下這個落差，六項報告裡**沒有任何一項提到它**。

**已修**（`impl.yml`）：R-6.1 的 patch 移除 `last_synced_at`，欄位集合由五欄改為**四欄**；連帶刪去死參數 `--arg ts`。R-6.8 的修復路徑**不受影響**（它有「已確認區塊存在於看板上」的獨立理由）。程式就地寫明 C-7.1 的來歷、期限與根因。

**測試同步更正**：`test_r6_1_backfill_writeback_field_set` 原本斷言的是**含 `last_synced_at` 的舊欄位集合**——它把缺陷行為編碼進去了。已改為四欄，並新增一條專屬斷言 `**C-7.1**：補平路徑不得推進 last_synced_at`。

### 2. Major：兩條零覆蓋分支（本輪新引入）

reviewer 以「整段拿掉、測試仍 35/189/0 全綠」證明它們沒有被守著。已各補一條測試：

| 測試 | 守什麼 |
| --- | --- |
| `test_r6_4_push_rejected_is_red_and_notified` | `commit_and_push` 回 Rejected（exit 3）⇒ **紅燈 ＋ 通報 Rejected**，不中止整輪（R-6.4／R-4.1） |
| `test_r6_1_writeback_failure_is_red_and_notified` | 「看板已補平但回寫失敗」⇒ **紅燈 ＋ 通報 ExternalError ＋ 不推送** |

兩條都有**前提斷言**（先確認情境真的發生）。

### 3. Major：C-2／C-6 代號混淆（本輪新引入）

我把「單元 U-2」與「元件 C-2」兩個編號系統混為一談。逐字核對 `components.md`：

| 代號 | 實際是什麼 |
| --- | --- |
| **C-2**（`:43`） | `record-reader`，**與 C-1 同一個 composite action** ⇒ 呼叫 `map.sh` 就等於呼叫了它，**不是孤兒** |
| **C-6**（`:84`） | `managed-block` ＝ `block.sh`，其**擁有單元**才是 U-2 |
| reconcile 的元件鏈（`:107`） | `C-7 →（內部）C-2／C-1／C-3／C-5`（加 §13 的 C-4）——**從來就沒有 C-6** |

**兩個結論都是假的**：C-2 不是孤兒；「不呼叫 `block.sh`」完全符合已核可的元件鏈，**不構成任何缺口**。原「待追認 #9」**撤回**。程式註解已就地更正。

### 4. Major：U-6 自我再觸發——**主要後果已被防線②擋掉**

reviewer 主張 U-7 推送到 `aidlc-sync/reconcile/<date>` 會觸發 **U-6 對該分支的一次完整 registry 全掃**，且與其他 run 真的併行。

**orchestrator 查證後部分推翻**：

| 事實 | 依據 |
| --- | --- |
| `record.sh:367` **強制** commit 訊息含 `SYNC_MARKER`，否則以介面誤用拒絕 | 錯誤訊息逐字「R-3.3：這是 U-6 自我排除的唯一依據」 |
| U-7 的訊息（`impl:426`）**含**該標記 | `"雜項(aidlc-sync): 對帳更新 ... ${SYNC_MARKER}"` |
| U-6 的防線②（`forward-impl:268`）命中即**整輪 skip** | 「防線②（R-4.2）命中：HEAD commit 訊息含 ...，整輪 skip」 |

**結論**：那個 push 確實會**建立**一個 U-6 run，但它在最開頭就 skip，**不會做 registry 全掃、也不會成為並行寫入者**。reviewer 對「run 會被建立」的判斷正確，對後果的定性過重。

**殘留成本如實記載**：每次對帳推送浪費一次 runner（一個立刻跳出的 run）。**不是 Major，降為 Minor**，登錄待 gate。

### 5. Minor：`$ws` 的「更正確」是過度宣稱

reviewer 代數證明：R-6.5 走到寫入那一刻，外層條件與內層前提合起來**保證 `board_status` 與 `dec_status` 逐字相等**，寫哪一個在行為上無差別。

**接受這項更正。** 正確描述是：**兩者在此保證相等，取 `$ws` 只是保留「這是觀察到的看板事實、不是本單元的判定」的意圖標記供維護者辨讀**，不存在實質正確性差異。本檔上方「Q1 的跨單元契約」一節的「比照抄 `$st` 更正確」措辭據此更正。

### 本輪機械證據（全部實跑）

| 項目 | 值 |
| --- | --- |
| 行為測試 | **37 tests, 199 checks, 0 failures**（原 35/189） |
| 新增突變 | **M14／M15**，各精準命中對應的那一條，還原後 `diff -q` clean |
| `impl.yml` | 951 行（原 928） |
| `run-reconcile-tests.py` | 1538 行（原 1461） |
| 兩支 contract validator | 皆 passed |
| `ci.yml` | 仍 `103 0` |

### 待追認清單的變動

- **撤回** #9（C-2 孤兒）——判斷錯誤，見上。
- **#2 的定性更正**：由「潛伏，Bolt 2 gate」改為「**C-7.1，已修**」——它本來就有更早的期限且修法已定，不應留給 gate。
- **新增**：U-7 的每次推送會浪費一次立刻 skip 的 U-6 run（Minor）。
- 其餘（#1、#3、#4～#8、#10）維持。

### 流程層的教訓（值得帶進 stage diary）

**開工前查證必須讀 `construction/functional-design/open-items.md`。** 本輪的 Critical 完全源於沒讀它——一個已登錄、已定修法、期限已過的缺陷，被我當成新發現重新描述並降格。四個姊妹單元的 code-summary 都引用了它，本單元沒有，而這個差異在檔案集合一致性自檢（第 4 項）中**應該**被看出來。

### 補做：`open-items.md` 全項逐一交叉核對（Critical 的根因處置）

Critical 揭露的真正風險不是那一個欄位，是**開工前查證從未讀過 `open-items.md`**。因此本輪補做全項核對——**四項全查，不只查被點名的那一項**：

| 項目 | 嚴重度 | 落點／期限 | 實作是否已涵蓋 | 依據 |
| --- | --- | --- | --- | --- |
| **C-7.1** | Critical | **Bolt 1 開工前** | ❌ **原本沒有，本輪才修** | 即本輪的 Critical |
| **C-7.2** | Critical | **Bolt 1 開工前** | ✅ **實作已正確** | U-6 `forward-impl:707-710` 逐字「write_body 回 failed → managed_block_hash 與 last_synced_at 皆維持原值（R-5.12／R-5.13）」。**殘留的是該項點名的四處上游文件**（`U-6/business-logic-model.md:53`／`:66`、`U-3/business-rules.md:104`、`U-3/domain-entities.md:50`）仍帶修正前文字——那是上游 artifact 的事，本站不回改 |
| **M-7.1** | Major | **code-generation** | ✅ **行為已覆蓋** | U-6 有 `test_r5_12_d_readback_external_error_writes_nothing`（`run-orchestration-tests.py:963`）。殘留的是序列圖沒畫出該分支，屬文件缺口 |
| **M-7.2** | Major | **code-generation** | ✅ **矛盾自然消解** | U-6 的回寫是**逐欄條件式**（`forward-impl:789-790`：`$fw` 把關 `last_field_value`、`$bw` 把關 `last_synced_at` ＋ `managed_block_hash`）。「同輪兩步皆失敗」時 `$fw=0` 且 `$bw=0`，兩欄都不寫——該項描述的字面互斥只存在於**逐案**表述，逐欄實作沒有這個問題 |

**這是不讀 `open-items.md` 的第二層代價**：M-7.1／M-7.2 的落點逐字寫著 `code-generation`——**指派給我這個 stage**——而 U-6 的 code-generation 在不知情的情況下做對了它們，卻沒有任何產出記錄「這兩項已關閉」。下一個人讀 `open-items.md` 時會以為它們還開著。

**本輪據此登錄三項狀態更新供 gate 覆核**：C-7.2 的**實作面**已滿足（文件面未），M-7.1 的**行為面**已覆蓋（序列圖未），M-7.2 **已由逐欄實作消解**。三者的殘留都是上游文件，不由本站回改。

## Review (code-generation) — Iteration 2

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T17:32:57Z（`date -u` 讀出）
**Iteration:** 2（上限）

### 停止判準（本輪開始前訂定，如實記載）

依 brief：只找到 Minor，或 Major 屬既存漏審／新設計問題 → 收斂為 open-items 帶進 gate；Critical／Major 若為 iteration 1 修正動作引入 → 需再一輪，但本輪為上限，屆時由 lead 依 `functional-design:c18` 的佔比訊號決定。**本輪結果：0 Critical、2 Major（1 項為 iteration 1 修正動作本身引入的跨位置傳播失敗；1 項為既存漏審，非本輪引入，亦非 iteration 1 造成）、0 新設計問題。** 依判準：Major ≤ 2 → 收斂為待追認項帶進 gate，不再開 iteration 3（且本輪已是上限）。

### 逐項驗證：iteration 1 的四項處置是否確實生效、有沒有製造新缺陷

#### 1. C-7.1（`last_synced_at` 移除）——**修正本身正確，但引入一項跨位置傳播失敗（新 Major，見下）**

**逐項查證**：
- `impl.yml:741-746` 的 R-6.1 patch 逐字核對：`jq -nc --arg st ... --arg fv ... --arg rc ...`，**恰為四個 key**（`last_status`／`last_written_status`／`last_field_value`／`last_reason_code`），`--arg ts` 確實已刪除，未見任何殘留的死參數。
- **`write_state_with_patch` 的合併語意已開檔核對**（`record.sh:454-479`）：`($cur + $patch)`——jq 物件合併，patch 未提及的 key **保留 `$cur` 原值**，不是替換整個物件。這代表移除 `last_synced_at`／`managed_block_hash` 不會把它們寫成 `null`，只是不動——**R-6.2「維持原值」的語意在這一層是真的成立的**，不是巧合也不是誤讀。此為本輪主動查證、brief 未直接問到但屬於「移除欄位是否會有副作用」的核心前提，結果：**成立，無副作用**。
- **測試鎖點正確**：`test_r6_1_backfill_writeback_field_set` 重新核對後確認斷言的是 **write_sync_state 收到的 patch 鍵集合**（`patch.keys()`），不是最終落地檔案內容——這是對的抽象層級（該測試的職責是鎖住「本單元往下游送出什麼」，物件合併的正確性屬於 `record.sh`／U-4 的職責，不該由 U-7 重複驗證）。
- **R-6.8（修復路徑）「不受影響」的說法逐一驗證了 R-5.9 的兩個實際觸發源**（U-6 `commit_and_push` 回 `Rejected`、R-5.4 回讀拋 `ExternalError`）：兩者的共同前提都是**看板寫入鏈（`write_status`／`write_field`／`write_body`）已經全部成功**，只是「記錄那次成功」的步驟失敗——這與 R-6.1 補平路徑（**保證**一個字都沒寫進受管區塊）在結構上是兩種不同的情形，「R-6.8 不受影響」在這兩個已知觸發源上**成立**。**但**深入推演後找到一個第三個、既有文件都沒檢驗過的殘留視窗，見下方新 Major #2——lead 的「不受影響」用詞因此**部分過度簡化**，不是錯，但不完整。

#### 2. 兩條零覆蓋分支的補測——**獨立重跑確認，精準命中，無殃及**

**本輪親自把兩個分支的錯誤處理各自整段還原成 iteration 1 reviewer 描述的樣子（`return 0` / 直接跳過失敗分支），實測**：

| 突變 | 命中 | 失敗數 | 波及範圍 |
| --- | --- | --- | --- |
| `push_state()` 整段錯誤處理改回 `return 0` | `test_r6_4_push_rejected_is_red_and_notified` | 恰 3 項失敗 | 僅該測試的 3 條 check，其餘 196 條全綠 |
| R-6.1 的 `write_sync_state` 失敗分支拿掉、強制 `wrote_state=1` | `test_r6_1_writeback_failure_is_red_and_notified` | 恰 3 項失敗 | 僅該測試的 3 條 check，其餘 196 條全綠 |

兩次突變後皆以 `diff -q` 確認還原乾淨。**lead 的「M14／M15 精準命中」宣稱屬實，非轉引**。兩條新測試也都有「前提」斷言（`commit_and_push 被呼叫`／`write_sync_state 被呼叫`），非空前提上的恆真通過。**判定：已修，無新缺陷。**

#### 3. C-2／C-6 代號更正——**逐字核對 `components.md`，更正正確**

`components.md:43` 確認 C-2＝`record-reader`（純函式層）；`:84` 確認 C-6＝`managed-block`；`:107` 確認 reconcile 的元件鏈原文為「`C-7 →（內部）C-2／C-1／C-3／C-5`」，**從無 C-6**。`impl.yml:176-183` 的更正註解與此逐字相符。**判定：已修，無新缺陷。**

#### 4. U-6 自我再觸發——**部分推翻的邏輯鏈已逐段驗證，成立**

- `record.sh:367` 附近的 SYNC_MARKER 介面檢查、`impl.yml:426` 的 push 訊息模板（含 `${SYNC_MARKER}`）、`forward-impl.yml:267-268` 的防線②比對邏輯，三處逐字核對屬實。
- **本輪額外查證 checkout 的 ref 釘選**（brief 明確要求的點）：`forward-impl.yml:85` 為 `ref: ${{ github.event.pull_request.head.sha || github.sha }}`——對 `push` 事件釘選的是**觸發該次事件的確切 commit**，不是執行當下的分支 tip。這代表即使 reconcile 在同一輪內對同一分支連續推送多個 commit（R-6.6 保證每 intent 至多一次，但一輪可能有多個 intent），**每一次推送觸發的 U-6 run 各自 checkout 到自己那個觸發 commit**，而 reconcile 的**每一個**commit 訊息都套用同一個含 `SYNC_MARKER` 的模板（`impl.yml:426`）——不存在「這一次 push 的 HEAD 恰好是別人的 commit」的情況，因為這條分支只有 reconcile 自己寫。**lead 的推翻邏輯站得住，且本輪找不到反例。判定：既存（防線②與自我排除是 U-6 原有設計），降為 Minor 的處置正確，維持。**

#### 5. `$ws` 措辭更正——已核對 `code-summary.md` 本文與 `impl.yml` 的實際註解，兩處皆已是更正後的用詞，`impl.yml` 的對應註解（`:791-798`）本來就沒有「更正確」這個過度宣稱，故不需要額外修正。**判定：已修，無新缺陷。**

### 補做：`open-items.md` 的 C-7.2／M-7.1／M-7.2 三項核對——**獨立重跑，結論皆正確**

- **C-7.2**：`forward-impl.yml:698-710` 逐字核對，`write_body` 回 `failed`（非外部錯誤 rc）時的 echo 訊息與後續邏輯確實只影響 `managed_block_hash`／`last_synced_at`（透過 `$bw` 閘門，見下）。
- **M-7.1**：本輪**沒有只信任 lead 引用的行號，而是直接執行該測試的 plan 並列印呼叫序列**確認：`board:write_status`／`board:write_field`／`block:render`／`board:write_body` 四步在 `board:read_item` 失敗**之前全部成功執行**（`rc: 1`，序列為 `read_sync_state → map → write_status → write_field → render → write_body → read_item(失敗) → notify`）——這代表「受管區塊已經寫成功、只是算不出雜湊」這個前提**在測試模擬中是真的成立的**，不是空前提上的恆真通過。**唯一的小瑕疵**：該測試本身沒有顯式 `check_true` 斷言這個前提（不像 U-7 自己新補的兩條測試都加了前提檢查）——這是 U-6 測試檔既有的風格缺口，不影響本輪判定，但值得留意（不計入本次 Major／Minor 計數，因為是 U-6 檔案的既有寫法，非本單元或本輪的產出）。
- **M-7.2**：**本輪直接用 U-6 的測試 harness 建構一個「write_field 與 write_body 同輪皆回 `failed`」的場景並實際執行**（非讀程式碼推論）：

  ```
  patch: {'last_status': 'In progress', 'last_reason_code': 'mapped', 'last_written_status': 'In progress'}
  rc: 0
  ```

  確認 `last_field_value`／`last_synced_at`／`managed_block_hash` 三者**皆不在 patch 內**（依合併語意即維持原值），且不紅燈（Failed 不連坐）。**lead「逐欄實作使字面互斥自然消解」的結論經直接執行驗證，成立，沒有找到「兩步皆失敗」的例外組合。**

### 新發現 #1（Major，新引入）：iteration 1 的修正在檔案內至少兩個位置沒有同步更新，其中一處是 gate 面向的摘要清單

- **`impl.yml:32-33`**（檔頭「本檔實作時發現、交還 Bolt 2 gate 追認的三項」清單）第 (2) 項逐字仍寫「**R-6.1 的 `last_synced_at` 與 U-6 的 R-5.13 語意相衝**（本檔**照字面實作**，見下方 R-6.1 回寫段的長註解）」——**這句話描述的正是 C-7.1 那個缺陷，且明說「本檔照字面實作」，即「這個缺陷目前還在」**。但下方 `:722` 起的長註解與實際程式碼（`:741-746`）都已確認**這個缺陷已經修好**（不再照字面實作，last_synced_at 已移除）。**檔頭清單與程式碼本體互相矛盾。**
- **`impl.yml:239`**：`ROUND_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"` 上方的注解仍寫「本輪時刻（**R-6.1／R-6.8** 的 last_synced_at）」——R-6.1 已不再使用 `ROUND_AT` 寫 `last_synced_at`（只剩 R-6.8 使用），這行注解未同步收窄。

**這是同一個根因（C-7.1 修正的傳播）在檔案內至少兩個位置留下的殘跡**，屬 `project.md` 已多次記載的「跨位置傳播失敗」同型缺陷（`application-design:260822-ad-L1`／`units-generation:260822-ug-L1` 等），差別在於這次落在單一檔案內部而非跨檔案。**判 Major 而非 Minor 的理由**：檔頭那三項清單的明文用途是「交還 Bolt 2 gate 追認」——這是設計給 gate 審閱者快速掌握現況的摘要區塊，若只讀這段（合理的閱讀路徑，因為它就放在檔案最前面且自稱是摘要），會得出「C-7.1 仍未修」的錯誤結論，與 code-summary 本文、`open-items.md` 的紀錄互相矛盾。**修法成本極低**（改兩行注解），不影響任何執行期行為。

**分類：新引入**（iteration 1 修正前，這兩處注解是準確的；修正動作本身造成了現在的不一致）。

### 新發現 #2（Major，既存漏審，非本輪引入）：R-6.8 對 `last_synced_at` 的「已確認區塊存在於看板上」理由，在一個 lead 未檢驗、`open-items.md` 自己留下警語但從未被回頭核對的殘留視窗上不成立

**brief 明確要求驗證的問題**：「R-6.8 仍在寫它，理由是『已確認區塊存在於看板上』——這個理由站得住嗎，還是它其實有和 R-6.1 同樣的問題？」

**結論：站得住的部分（大部分）站得住；但有一個更窄、真實可達、且從未被檢驗過的殘留視窗**。

**先說明為什麼不是「跟 R-6.1 同樣的問題」**：R-6.1 補平路徑**保證**沒有寫入受管區塊（R-6.2 明文禁止），所以它推進 `last_synced_at` **在任何情況下都是錯的**——這是本輪已確認修好的 C-7.1。R-6.8 觸發的兩個已知場景（`commit_and_push` 回 `Rejected`、R-5.4 回讀拋 `ExternalError`）**都是在「`write_status`／`write_field`／`write_body` 整條寫入鏈已經真的執行成功」之後才發生的記錄失敗**（本輪已用 U-6 業務規則文字與 forward-impl 的程式碼結構核對確認這點）——board 上的受管區塊內容，就其被寫入的那一刻而言，**確實已經包含了當時判定要遞交的 `rejection_notice`**（如果有的話）。這與 R-6.1 的「保證沒寫」是兩種不同性質的情形，`open-items.md:137` 的原句「本輪只對兩個做了語意對齊」不代表 R-6.8 一定是錯的，只代表**它沒被檢驗過**——本輪的任務正是去檢驗它。

**但檢驗後找到一個真實的殘留視窗**：R-6.8 把 `last_synced_at` 無條件寫死為 `$ROUND_AT`（對帳**執行當下**的時刻），而不是「受管區塊**實際**最後一次被成功寫入的時刻」。這兩個時刻在下列情境下會不同，且差異會產生後果：

1. U-6 在 T_write 成功寫入整條鏈（含 write_body），但記錄失敗（R-5.9 ②或③）——此時受管區塊的內容**只涵蓋到 T_write 為止**判定要遞交的通知。
2. 在 T_write 之後、reconcile 下一次執行（`$ROUND_AT`）之前，**又有一則新的反向 PR 在 T_new 關閉**（`T_write < T_new < $ROUND_AT`）。
3. 這則新關閉本應觸發 U-6 立即重跑（`pull_request: closed` 是 U-6 的觸發事件之一，本輪已核對 `forward.yml:16-20`），若這次重跑**成功**完整記錄，則 SyncState 會被正確更新、R-6.5 的觸發條件（三欄不符）不再成立，reconcile 不會做任何事——**沒有問題**。
4. **但如果這次重跑再次落入 R-5.9 ②或③的同型記錄失敗**（同一種暫時性外部錯誤又發生一次），受管區塊此時**才**真的涵蓋到 T_new 的通知（因為這次重跑的 write_body 使用的是重新組裝、含最新 `reverse_rejected` 狀態的 Context）——這種情況下 R-6.8 的修復其實還是對的（last_synced_at 該推進到涵蓋 T_new）。
5. **真正會出錯的組合是**：步驟 2 的新關閉發生了，但**沒有**任何後續的 U-6 重跑再次嘗試寫入（例如：U-6 的觸發本身因為某種原因沒有發生，或發生了但整輪在寫入鏈**之前**就中止，例如 R-2.5 的 `reverse_pending` 查詢失敗導致整輪 `ExternalError` 中止），使得受管區塊**真正**停留在 T_write 的內容（不含 T_new 的通知），而 SyncState 的三欄比對**恰好**因為其他原因（例如另一個欄位的漂移）仍然觸發 R-6.5 的修復。此時 R-6.8 會把 `last_synced_at` 推進到 `$ROUND_AT`（> T_new），使 U-6 下一輪對 T_new 的 `closed_at > last_synced_at` 判斷為假 ⇒ **T_new 這則告示永久靜默，且無紅燈**——與 C-7.1 的最終後果**完全同型**。

**reachability 與 C-7.1 的關鍵差異（這決定了嚴重度判斷）**：C-7.1 的觸發**不需要任何外部失敗**——它是兩個正常元件（每日排程 vs 事件驅動）之間純粹的時序競賽，在正常操作下就會發生。本項需要**至少一次**真實的外部失敗（R-5.9 ②或③其中之一）疊加一個特定的時間窗巧合，屬於複合條件，reachability 明顯更窄。**這是本項判 Major 而非 Critical 的理由**——後果同型，但不是在正常操作下就會發生的路徑。

**這個缺口為什麼是「既存漏審」而不是本輪或 iteration 1 引入的**：R-6.8 本身在 functional-design iteration 5（`2026-08-30T02:47:00Z`）就已定案，`open-items.md:137` 的 C-7.1 條目本身留下的那句「`last_synced_at` 現有三個寫者（R-5.4／R-6.1／R-6.8），本輪只對兩個做了語意對齊」，**已經是對這個缺口的明確預警**——只是從未被展開成一個具體場景。lead 在 iteration 1 的「open-items.md 全項核對」只核對了 open-items.md **獨立列出**的 C-7.2／M-7.1／M-7.2 三項，沒有回頭處理 C-7.1 條目**自己**留下的這句警語所指向的缺口——這與 lead 自己在 iteration 1 記錄的教訓（「開工前查證從未讀過 open-items.md」）是同一個根因的延伸：讀了，但只讀到條目本身，沒有讀進條目內文裡的但書。

**建議**：登錄為新的待追認項（第 11 項），措辭精確為「R-6.8 在兩個已知觸發場景（`commit_and_push` Rejected／R-5.4 回讀 ExternalError）下語意正確；未涵蓋的殘留視窗是『記錄失敗且無後續成功重試』與『同視窗內有新反向 PR 關閉』的複合情形，需 U-8 上線後才可能實際發生（與 C-7.1 的前置條件相同）」，並更正 code-summary「R-6.8 不受影響」一句的完整性（不是錯，但不完整）。**不建議在本輪修改程式碼**——現有的兩個已知場景处理正確，修法需要傳遞「板實際最後寫入時刻」這個目前系統不記錄的資訊，屬於需要上游（可能是 U-6 的 R-5.4 或 U-8 的介面）配合的設計變更，不是 code-generation 這個 stage 能單方面決定的落點。

**分類：既存漏審**。

### Attempted refutations that did not hold

1. 嘗試證明「移除 `last_synced_at` 會因為 `write_state_with_patch` 是整物件替換而把既有值清空」——**未推翻**：`record.sh:454-479` 逐字確認是 `$cur + $patch` 的物件合併，patch 未提及的 key 保留原值。
2. 嘗試證明 M14／M15 兩條新測試在某種輸入下也會恆真通過（懷疑同型於 U-6 的「rc/exit」假陽性）——**未推翻**：兩條測試都有「前提」斷言，且本輪獨立突變後精準命中、無殃及。
3. 嘗試證明 M-7.1 的測試前提是空的（`board:read_item` 全域 stub exit=1 可能連 write_status 自己內部的回讀也一併失敗，導致「board 已經寫成功」這個前提根本不成立）——**未推翻**：本輪直接執行該測試的 plan 並列印呼叫序列，確認 write_status／write_field／write_body 三步在 read_item 失敗前確實全部成功執行。
4. 嘗試證明 U-6 的自我排除防線②在「一輪內對同分支連續多次推送」下可能檢查到錯誤的 commit 訊息——**未推翻**：checkout 的 `ref` 釘選觸發事件的確切 commit（非分支 tip），而該分支僅 reconcile 自己寫且每次都套用同一含 marker 的訊息模板，故不存在檢查到別人訊息的情況。
5. 嘗試證明 R-6.8「已確認區塊存在於看板上」的理由與 R-6.1 同型錯誤（brief 明確要求的查證項）——**部分推翻**：兩個已知觸發場景下理由確實成立（board write 鏈含 write_body 已驗證成功），但深入推演後找到一個更窄、真實存在、從未被檢驗的殘留視窗（見新發現 #2），故 lead「不受影響」一句話過度簡化，不完整。
6. 嘗試證明 C-7.2／M-7.1／M-7.2 的「已涵蓋」結論有誤——**未推翻**：三項皆以獨立執行（非讀碼推論）確認成立。

### Summary

**三類分佈**：新引入 1（Major：`impl.yml` 檔頭的 Bolt 2 gate 摘要清單與 ROUND_AT 注解，共兩個位置未隨 C-7.1 修正同步更新，造成檔案內部自相矛盾）／既存漏審 1（Major：R-6.8 對 `last_synced_at` 的語意在一個複合條件的殘留視窗上仍可能導致 [US:S-6 AC 5] 永久靜默，`open-items.md` 的 C-7.1 條目本身留下的警語從未被展開查證）／新設計問題 0。iteration 1 原始的 1 Critical＋3 Major 全部確認已正確處置（逐項獨立重跑驗證，非轉引），且未在修正過程中製造功能性缺陷——本輪抓到的兩項都是**文件／語意完整性**層級，不是**執行期行為**層級：所有機械證據（37/199/0、37/199/0 突變後精準命中、`ci.yml` 103/0、U-6 測試 39/145/0、兩支 contract validator passed）全數再次確認無誤。

**核心結論**：code-generation 的實作品質在兩輪審查後依然扎實，iteration 1 的四項修正全部正確落地且逐一獨立驗證通過，沒有發現任何新的執行期缺陷。剩餘的兩個 Major 都是**成本低、範圍明確**的收斂項（改兩行注解；登錄一則新的待追認項並更正一句過度簡化的措辭），不需要也不建議開第三輪——依 `functional-design:c18` 的訊號判斷，這一輪找到的問題**全部**指向文件完整性而非功能正確性，繼續迴圈的邊際收益低。建議 lead 在進 Bolt 2 gate 前把這兩處注解就地改掉（不需要重新送審），並把新發現 #2 登錄為待追認清單第 11 項供 gate 知情裁決。

VERDICT: READY

### Validation Tool Results

| Tool | Result | Interpretation |
| --- | --- | --- |
| `python3 .github/actions/aidlc-sync-reconcile/run-reconcile-tests.py` | 37 tests, 199 checks, 0 failures | 與 lead 宣稱一致，本輪重跑確認 |
| `python3 .github/actions/aidlc-sync-forward/run-orchestration-tests.py` | 39 tests, 145 checks, 0 failures | U-6 未被本輪或 iteration 1 波及 |
| `python3 scripts/validate_repo_contract.py` | passed | 無違規 |
| `python3 scripts/validate_env_contract.py` | passed | 無違規 |
| `git diff --numstat -- .github/workflows/ci.yml` | `103 0` | U-10a 的 `paths-ignore` 未被波及 |
| `gh api graphql`（issue #16／#23） | #16 為已合併 PR（`updatedAt: 2026-07-12`）、#23 為已關閉 issue（`updatedAt: 2026-08-07`），皆無本輪異動 | 確認本輪查證未觸碰真實 API 寫入或無關項目 |
| 本輪 2 次獨立突變（`push_state()` 錯誤處理、R-6.1 的 `write_sync_state` 失敗分支） | 各恰好 3 項失敗，精準命中對應測試，其餘 196 條全綠 | 驗證 iteration 1 新補的兩條測試確實有效 |
| 本輪 1 次獨立突變（U-6：write_field＋write_body 同輪皆 `failed`） | `patch` 恰為 3 鍵、`rc=0` | 驗證 M-7.2 的「逐欄實作消解字面互斥」結論 |

---

## Iteration 2 修正記錄與收斂（lead，2026-09-05T17:40:53Z）

**Verdict: READY**（0 Critical、2 Major，皆為文件／完整性而非執行期缺陷）。

| 發現 | 分類 | 處置 |
| --- | --- | --- |
| #1 iteration 1 的修正在檔內留下未同步的殘跡 | **新引入（我的）** | **已修，且找到第三處** |
| #2 R-6.8 的 `last_synced_at` 有一個殘留視窗 | 既存漏審 | **登錄為 open item #11**，不在本站修 |

### #1：跨位置傳播失敗，我漏的比 reviewer 找到的多一處

reviewer 找到兩處，我修的時候按**事實**（而非它給的行號）重掃，發現**第三處**：

| 位置 | 殘跡 | 已修 |
| --- | --- | --- |
| `impl:34` | 檔頭「交還 gate 的三項」清單第 (2) 項仍寫「本檔照字面實作」＝缺陷還在 | ✅ 改為刪除線 ＋「已修，不再是待追認項」 |
| `impl:244` | `ROUND_AT` 註解仍寫「R-6.1／R-6.8 的 last_synced_at」 | ✅ 收窄為「只有 R-6.8」 |
| **`impl:715-716`** | **長註解的標題仍框成「交還 gate 的缺口 (2)」且說「照字面實作」**——reviewer 沒點名這處 | ✅ 改為「C-7.1（已修）」並把「一度照字面實作」的時態講清楚 |

**機械複驗**：`grep -nE "交還 gate 的缺口 \(2\)|本檔.*照字面實作"` → **零殘留**。

reviewer 判它 Major 的理由值得記：檔頭那份清單的**明文用途**是「交還 gate 追認」，是設計給審閱者快速掌握現況的摘要區塊——只讀它會得出「C-7.1 仍未修」的相反結論。**摘要區塊與本體矛盾，比兩份文件矛盾更危險**，因為摘要正是為了讓人不必讀本體而存在。

### #2：R-6.8 的殘留視窗 → open item #11

R-6.8 對 `last_synced_at` 的「已確認區塊存在於看板上」理由，在它的**兩個已知觸發情境**下成立（U-6 的 `commit_and_push` 回 `Rejected`、R-5.4 回讀拋 `ExternalError`——兩者的共同前提都是看板寫入鏈已全部成功）。

**但存在一個更窄、真實可達、從未被檢驗的殘留視窗**：需要一次真實的外部寫入失敗**疊加**一個時間窗巧合（同時有新的反向 PR 關閉），此時同樣會造成 [US:S-6 AC 5] 的告示靜默遺失——與 C-7.1 同型的後果。

**與 C-7.1 的關鍵差異（這決定嚴重度）**：C-7.1 的觸發**不需要任何外部失敗**，是兩個正常元件（每日排程 vs 事件驅動）之間的純時序競賽，正常操作下就會發生；本項是複合條件，reachability 明顯更窄。**故判 Major 而非 Critical。**

**這正是 `open-items.md:137` 自己留下的警語**——「該欄現有三個寫者（R-5.4／R-6.1／R-6.8），**本輪只對兩個做了語意對齊**」——**而它從未被回頭核對，包括我本輪自稱的「全項交叉核對」**。我的核對停在「四個項目各自是否被涵蓋」，沒有追它條目內部的但書。

**登錄為 open item #11**（Major，落點 Bolt 2 gate）：R-6.8 的第三個寫者從未做語意對齊，需與 C-7.1 同一個確認人一併處理。本站不修——修法涉及 R-6.8 的規則本身，屬上游。

### 本輪機械證據

| 項目 | 值 |
| --- | --- |
| 行為測試 | **37 tests, 199 checks, 0 failures**（未變） |
| C-7.1 殘跡 | **零殘留**（按事實重掃三個位置） |
| 兩支 contract validator | 皆 passed |
| `ci.yml` | 仍 `103 0` |

### 收斂決定

**READY，不跑第三輪。** 兩項 Major 皆非執行期缺陷：#1 已修完並機械複驗零殘留，#2 是規則層的既存缺口、修法屬上游、已登錄。reviewer 獨立重跑了 iteration 1 的全部四項修正（含自己重新突變兩條新測試、實際構造「同輪兩步皆失敗」情境驗證 M-7.2、核對 `record.sh` 的 `$cur + $patch` 合併語意確認省略欄位不會被 null 掉），無一被推翻。
