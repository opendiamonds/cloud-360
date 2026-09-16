# User Stories — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: user-stories（Inception 2.4）· Record: 260822-gh-projects-sync
     來源標籤：[req:FR-*]／[req:NFR-*] 指 requirements.md；[intent:*]／[scope:*] 指 ideation 產出；
     [Q<n>]／[M<n>] 指本站問題檔（M = PART 2 mob triage 的人工裁決）；[P<n>] 指 personas.md。
     切分軸 [Q2=A]（可觀察的成果）；粒度 [Q3=A]（8–12 則，實得 11）；
     NFR 承載 [Q4=B]；驗證層 [Q5=A]。
     AC 一律描述系統行為且要能真的失敗（project.md `user-stories:c3`）。
     本檔為 Revision 1，已整合 mob round 1 的三份貢獻——改動清單見文末 Revision 段。 -->

## 上游輸入

本故事集的每一則都可追溯到下列已核可產出（`phases/inception.md` 的 Traceability 要求）：

- **requirements**（`../requirements-analysis/requirements.md`，Revision 1）：40 條 FR、15 條 NFR、6 條約束、5 項已解消矛盾、8 假設、8 排除項、8 待決問題。每則故事的 AC 逐條掛 `[req:*]` 標籤。
- **intent-statement**、**scope-document**（Revision 1）、**intent-backlog**（Revision 1）、**feasibility-assessment**、**initiative-brief**、**ADR-0013**：見問題檔的「上游輸入」與「已由上游定案、不重問」表。
- **codekb `component-inventory.md`**（brownfield 掃描產出，基準 commit `9307dbc`）——本站實際引用的事實有四項，全部影響 AC 內容：
  1. **11 支 gh-aw workflow 的觸發與排程對照表**（`:217-229`）：`daily-digest` 為 `schedule` cron `0 23 * * 1-5`、`release-watch` 為 gh-aw 的模糊排程語法（`weekly on monday`，非 cron，編譯後才成為具體時間）。這是全域 DoD「排程不衝突」那一列的事實來源，也解釋了為什麼該列必須比對**編譯後**的 `.lock.yml` 而非 `.md` 宣告。
  2. **workflow 的 body H1 同時決定 concurrency group（`gh-aw-<name>`）**（`:215`）：這使 NFR-C2 的「無重複 `name`」不只是顯示名衝突，而是會讓兩支 workflow 意外共用佇列。
  3. **`.md` 對 runtime 完全惰性、兩者無同步守門員**（`:212`）：NFR-M1 與 [req:OQ-4] 的事實基礎。
  4. **本 repo 用過的 safe-output 只有 5 種，「這是用量，不是 gh-aw 的完整目錄」**（`:238-241`）：這正是本站更正 A-5 敘述的依據——「未支援」的主體是 gh-aw 的**已用清單**，不是平台，而 ADR-0013 已查證框架另有 `update-project` 等 Projects 相關 safe-output。
- **codekb `business-overview.md`**：確認本機制的使用者是開發流程本身而非產品終端使用者。本站在 `user-stories-assessment.md` 正面回答了該句為何不構成 skip 理由。
- **team-practices**：本 intent 的 scope 跳過 `practices-discovery`，無該站產出；團隊實踐由 `aidlc/spaces/default/memory/team.md` 與 `project.md` 直接提供。此缺席為 scope 設計而非缺漏。

---

## 故事總覽

全部 11 則均為 **Must**——[scope:CAP-1～CAP-11] 逐列標 Must，且該檔明記「單一決策者且依賴序已定時，相對分數沒有真實輸入，屬虛假精確」，故本站以 MoSCoW ＋ 依賴序表達優先，不做數值評分。

| # | 故事（一句話成果） | 主 persona | 涵蓋需求 | AC 數 |
| --- | --- | --- | --- | --- |
| S-1 | 新 intent 自動出現在看板上 | P1 | FR-A1～A4、FR-C2、NFR-C1 | 7 |
| S-2 | stage 推進後看板跟著動 | P1 | FR-B1～B5、FR-J3、FR-J4、FR-J6、NFR-P3 | 15 |
| S-3 | 機制拿不準時，看板不說謊 | P3 | FR-C1、FR-C3、FR-J1、FR-J2、FR-J3、FR-J5 | 6 |
| S-4 | 暫停與跳過在看板上看得出差別 | P1 | FR-B3、FR-B6、FR-F3、FR-F4 | 6 |
| S-5 | 目前走到哪一站，看板上看得到 | P3 | FR-F1、FR-F2 | 3 |
| S-6 | 看板上的人工改動算數 | P2 | FR-G1～G4、NFR-C1 | 7 |
| S-7 | 每天自動對帳補平落差 | P4 | FR-D1～D4、FR-E2 | 5 |
| S-8 | 機制失敗會叫人，不會沉默 | P4 | FR-E1、FR-E3、NFR-S6 | 3 |
| S-9 | 可信度本身看得到 | P4 | NFR-O1、NFR-O2、NFR-P1 | 6 |
| S-10 | 映射、端到端與權限都有持續生效的斷言 | P4 | FR-I1、FR-I2、FR-I5、FR-B2、NFR-S1 | 5 |
| S-11 | README 指得到需求正本 | P2 | FR-H1 | 2 |

**需求覆蓋**：40 條 FR 中 38 條落在上表（FR-I3／FR-I4 為上線前置條件 PRE-1）；15 條 NFR 中 NFR-O1／O2 立為 S-9、NFR-P1 移入 S-9 為量測型 AC、NFR-P3 在 S-2、NFR-S1 依 [M3=A] 升格為 S-10 AC 5、NFR-S6 在 S-8、NFR-C1 分別落在 S-1 AC 7 與 S-6 AC 6，其餘落在全域 DoD。無需求未被承接。

> **AC 總數 65**（Revision 1 前為 56；此數字以 `^\d+\. \*\*Given\*\*` 機械計數複驗過，逐則與總覽表一致）。差額來自：拆解不可判的 AC（S-2 的解析語意由 1 條拆為 4 條、觸發優先序由 1 條拆為 2 條）、補上未被覆蓋的失敗模式（S-1 的重複建立與 CI 取消、S-2 的總函式性、S-4 的雙重降級、S-6 的 reject 路徑與成本控制、S-9 的 issue 不相稱偵測、S-10 的靜態檢查與權限）、以及移除一條自承非二元的 AC（原 S-8 AC 4 → US-OQ-1）。

---

## S-1 — 新 intent 自動出現在看板上

> **As** 開發者（P1），**I want** 新 intent 一誕生就自動在 Project #16 上有一則綁定的 issue，**so that** 我不需要為了讓別人看得到它而先手動開一張卡。

次要受益：P3（觀看者第一次看得到這個 intent 存在）。

**Acceptance Criteria**

1. **Given** 一個新 intent 的 record 首次被推送，**When** 同步執行，**Then** Project #16 出現一則對應的 issue，且其 Status 欄位值為 `Ready`。[req:FR-A1]
2. **Given** AC 1 的 issue 已建立，**When** 建立流程結束，**Then** 該 intent 的 record 內存在一個可機器讀取的欄位，其值等於該 issue 的編號。[req:FR-A2]
3. **Given** 某個 intent 的 record 標題被改成與另一個 intent 相同，**When** 下一次同步決定寫入目標，**Then** 寫入的仍是 AC 2 欄位所記的原 issue，不是標題相符的那一則。[req:FR-A2]
4. **Given** 綁定編號與同步狀態檔需要回寫，**When** 回寫執行，**Then** 觸發本次同步的那個分支上出現一個 commit，其訊息含 `[aidlc-sync]`，且其變更僅涉及該 record 目錄下的綁定編號與 `sync-state.json`。[req:FR-A3]
5. **Given** 一個由**同步身分**推送、訊息含 `[aidlc-sync]` 的 commit，**When** 同步的觸發條件被評估，**Then** 不執行任何看板寫入。[req:FR-A4]
   > **適用前提**：本條假設同步身分產生的事件**會**觸發 workflow。若 OQ-1 最終選用 repo 預設 `GITHUB_TOKEN`，平台本身即不會為其產生的 push 觸發新 run，本條在該身分下恆真、防線由平台承接——屆時須在全域 DoD 記明，不得留一條不可證偽的 AC。身分未定，故本故事的 Estimable 標 ⚠️。
6. **Given** 一個 record 內已存在綁定編號，**When** 首建路徑被再次執行（上一次的回寫 commit 未成功推送，或 workflow 重跑），**Then** 不建立第二則 issue，且看板上該 intent 的 item 數維持為 1。[req:FR-C2][req:FR-A2]
   > **改寫理由**：原 AC（「目標 Project 不是 #16 則中止」）只能靠竄改設定達成，在正常運行中恆真。`requirements.md` 的 A-8 已明記「回寫觸發分支假設同步身分對 feature 分支有寫入權且不受分支保護阻擋；**未驗證**」——回寫失敗 ⇒ 下次 push 又看不到綁定 ⇒ 再建一則 issue，**每 push 一次多一張卡**。這是上游已預見卻無任何 AC 攔截的失敗模式，依 `project.md`（`user-stories:c4`）把防禦意圖移到碰得到真實失敗面的層次。
7. **Given** 一個分支上有正在執行中的 `ci.yml` run，**When** 同步的回寫 commit 被推送到該分支，**Then** 該既有 run 不被取消，且不因該 commit 新增一輪 `ci.yml` 的四個 job。[req:NFR-C1][req:FR-A3]
   > **實測依據**：`.github/workflows/ci.yml:7-20` 的 `on: pull_request`（無分支過濾）＋ `push: branches: [main, ut, "danniel/**", "chore/**"]` ＋ `concurrency: group: ci-…-${{ github.ref }}` ＋ `cancel-in-progress: true`。本團隊的分支一律 `danniel/**`（`team.md`），故 FR-A3 的每次回寫都會觸發 `ci.yml` 並**取消開發者當下正在跑的那一次**。`[aidlc-sync]` 標記只擋同步 workflow 自己，`ci.yml` 全檔無 commit message 過濾。NFR-C1 原文只保證「既有 job 的**行為**與變更前相同」，不涵蓋**觸發量**與取消行為，故此路徑穿過了現有全部需求。

**INVEST**：Independent ✅／Negotiable ✅／Valuable ✅／Estimable ⚠️（AC 5 的身分待 OQ-1）／Small ✅／Testable ✅。

---

## S-2 — stage 推進後看板跟著動

> **As** 開發者（P1），**I want** 我推送 record 之後看板狀態自己更新，**so that** 我不必記得回去手動改它。

次要受益：P2、P3。

**Acceptance Criteria**

1. **Given** 某個 in-scope stage 的 checkbox 為 `[-]` 或 `[R]`，**When** 同步執行，**Then** 該 item 的 Status 為 `In progress`。[req:FR-B1]
2. **Given** 某個 in-scope stage 的 checkbox 為 `[?]`，**When** 同步執行，**Then** Status 為 `In review`。[req:FR-B1]
3. **Given** 一個 `## Runtime State` 的 `Status` 欄位為 `Completed` 的 record，**When** 同步執行，**Then** Status 為 `Done`。[req:FR-B1]
   > **改寫理由**：原措辭「workflow 已完成」未定錨到可觀察值。實測 6 個 record，`- **Status**: Completed` 與「全部 EXECUTE 列為 `[x]`」今日恰好一致，但 AC 沒說機制該讀哪一個，兩者可在寫入間隙分岔。本條明定讀 `Status` 欄位。
4. **Given** 一個訊號不落在對照表任何一列的 record（例如 checkbox 出現六種合法字元以外的符號、或 `## Stage Progress` 存在但無任何 EXECUTE 列），**When** 同步執行，**Then** 不送出任何 Status 寫入，且該 record 出現在對帳報告的「無法判定」清單中。[req:FR-B1][req:FR-J3]
   > **改寫理由**：原 AC（「送出的值不為 `Backlog`／`Nice to have`」）恆真——對照表只有四個輸出值，任何忠實實作都必然通過。真正碰得到失敗的是「未列舉輸入落進 else 分支」，而自然實作的 else 分支通常是 `Ready` 或 `In progress`。防禦意圖是真的，落點錯了。
5. **Given** 兩個 record 只在 `[S]`／`— SKIP` 上不同，**When** 同步執行，**Then** 兩者得到**相同**的 Status。（差別的可見性由 S-4 承接）[req:FR-B3]
6. **Given** 兩個 stage 列集合不同的 record（一個含 `tcms-test-cases`、一個不含），**When** 同步執行，**Then** 兩者的 Status 都與各自的 checkbox 狀態相符，無錯位。[req:FR-J4]
7. **Given** 一個在正式欄位之前另有一行 `- **Current Stage**: <舊值>` 的 record，**When** 機制解析該欄位，**Then** 讀到的是**第一個** match 的值（`<舊值>`），不是最後一個。[req:FR-J6]
8. **Given** 一個欄位存在但值為空（`- **Parked**: ` 之後無內容）的 record，**When** 解析，**Then** 讀到空值，而**不是**下一行的內容。[req:FR-J6]
9. **Given** 一個完全沒有該欄位行的 record，**When** 解析，**Then** 結果為「不存在」，且與 AC 8 的「存在但空」走**不同**的後續分支。[req:FR-J6]
   > 本條直接保護 S-4 AC 1 的「`Parked` 非空」判定：現況 record 的 `## Runtime State` 只有 `- **Revision Count**: 0`，`Parked` 是**缺席**而非空值，兩者混同會讓 park 特判永遠不觸發。
10. **Given** 一行縮排的 `  - **Current Stage**: X`，**When** 解析，**Then** 不視為 match（行錨定要求行首即 `- `）。[req:FR-J6]
    > **AC 7–10 的改寫理由**：原 AC 的 Then 是「與引擎 `getField()` 讀到的值相同」，但該 oracle **不存在**——`getField` 只在 `aidlc-lib.ts:2676` 匯出為函式，`aidlc-utility.ts:5347-5434` 與 `aidlc-runtime.ts:1420` 的子命令表都沒有印出任意 state 欄位的入口；改成測試時直接 import 又撞上 ADR-0012 §6（`:103`）禁止依賴 `.claude/`。原 AC 不是驗收標準，是一句宣稱。FR-J6 本文已把語意逐條寫出（行錨定、全檔搜尋、第一個 match 即回傳、找不到回 `null` 而非空字串），直接展開為四條純文字 fixture 即可驗，不需引擎在場。
11. **Given** 兩個事件觸發的同步同時排入，**When** 兩者執行，**Then** 後者排隊等待而非取消前者；且排程對帳的執行不佔用事件路徑的佇列。[req:NFR-P3]
12. **Given** 同一組 record 訊號且無 PR 開啟，**When** 分別經 push 事件與 PR 事件觸發，**Then** 兩條路徑輸出的 Status 相同。[req:FR-B5]
13. **Given** 一個 checkbox 判定為 `In progress` 的 record，且其分支上有一個開啟中的 PR，**When** push 事件與 PR 事件在同一輪先後到達，**Then** 該 item 最終的 Status 為 `In review`（PR 事件的結果覆寫 push 事件的結果）。[req:FR-B4]
    > **AC 12–13 的拆分理由**：原單一 AC 的兩個 Then 互相抵銷——前半要求兩路徑得到**相同** Status，後半要求能看出「最終寫入來自 PR 事件」；值相同就無從分辨誰寫的，而 FR-B5 的優先序只在兩者**不同**時才有內容，此時前半的 Given 又不成立。
14. **Given** 同一個 record 輸入，**When** 映射判定連續執行 3 次，**Then** 三次輸出的 Status 完全相同（判定為決定性，無執行間變異）。[req:FR-B2]
    > **改寫理由**：原 AC（「該次執行未發出任何對語言模型的呼叫」）把 FR-B2 從「判定邏輯不由 LLM」擴大成「整次 workflow 執行無 LLM 呼叫」，等於單方面刪掉 C-T7 明文允許的「gh-aw 的非 LLM 環節」——gh-aw 編譯出的 workflow 必含 agent step（`ui-regression.md:13`／`:40`）。那屬於在 inception 未記來源地新增需求，違反 `phases/inception.md` 的 Traceability。**「承載形式不得含 agent step」的靜態檢查移至 S-10 AC 4**（依 `units-generation:c6`：建置期資產與執行期契約不併入同一單元），本條只留執行期可觀察的決定性。
15. **Given** 任一可解析的 record（即未被 S-3 AC 5 跳過者），**When** 映射判定執行，**Then** 恰好輸出一個 Status 值，且該值可回溯到對照表的某一列；不存在「無對應列」而落到預設值或空輸出的輸入。[req:FR-B1]
    > **新增理由**：對照表**不是全函式**。實測 6 個 record 今日全部落在表內，但「`Status` ≠ `Completed`，且沒有任何 EXECUTE stage 是 `[-]`／`[R]`／`[?]`，但已有 `[x]`」這個狀態在表上沒有對應列（第一列的前提「尚無任何 in-scope stage 動過」已不成立）。這是 gate 核可後到下一個 stage 起跑之間的窗口，也是 `--single` 模式的常態。AC 1–4 在該狀態下輸出任何東西都能通過。`parseCheckboxes`（`aidlc-lib.ts:2842`）的 `default` 分支把未知標記一律當 `pending`，這正是為什麼「輸出恰好一個值」必須被明寫。

**INVEST**：Independent ⚠️（技術上依賴 S-1 的綁定編號）／Negotiable ✅／Valuable ✅／**Estimable ⚠️**（承載語言待 OQ-7 裁決，見依賴表）／**Small ❌**／Testable ✅。

> **Small 不成立，且這是本站已知並接受的代價**（[Q3=A] 的選項本文即載明）。給 units-generation（2.6）的建議切線，依**驗證方式是否同類**（`project.md` 的工作單元切分判準）：
> - ①**映射判定與解析語意**（AC 1–10、14、15）：純文字 fixture 可驗，失敗模式同類（輸出錯的 Status／讀到錯的值）。
> - ②**觸發與並行**（AC 11–13）：需要真實事件與佇列，dry-run 驗不到。
> - 原切線曾把 NFR-P1 的 5 分鐘放進②，**已移出**——GitHub-hosted runner 的排隊時間不受本 repo 控制，把「≤ 5 分鐘」寫成 per-run 二元閘門會製造結構性 flaky gate，而 `team.md` 記載 `ui-regression` 的 `post-steps` 對 `.stats.unexpected` 是零容忍真閘門，把 flaky 斷言放進同一層會侵蝕它。改為量測型並移入 S-9 AC 6。
> **本站不決定切分，只標明依據。**

---

## S-3 — 機制拿不準時，看板不說謊

> **As** 觀看者（P3），**I want** 機制在讀不到或讀到互相矛盾的資料時**寧可不寫**，**so that** 機制不會拿一個它自己都不確定的值去蓋掉原本的值。

次要受益：P4（每一次「不寫」都會留下他能追的痕跡）。

> **Benefit clause 的誠實邊界（[M1=B]）**：本則故事**不保證 P3 分得出「機制刻意不寫」與「機制壞了」**。「不寫」的痕跡目前只落在 repo 側的 issue，P3 依本站假設不進 repo。這個缺口是真的，收斂形式列為 **US-OQ-3**（指派 application-design）。先前版本的 `so that` 寫「我在看板上看到的每一格都還值得相信」——那承諾了本則 AC 交付不了的東西，已依 [M1=B] 弱化。

**Acceptance Criteria**

1. **Given** 某個目標 item 的實際值與機制預期的不符，**When** 機制準備寫入，**Then** 不送出寫入請求，且產生一則記錄該不符的 issue。[req:FR-C1]
2. **Given** 排程對帳與事件同步同時對同一 item 寫入，**When** 後到者執行回讀比對，**Then** 偵測到前者已寫入的結果並依 AC 1 處置（中止寫入 ＋ 開 issue）。「重算後仍寫入」不是合格結果。[req:FR-C3]
3. **Given** 判定某個 intent 的 Status，**When** `intents.json` 的 `status` 與該 record 的狀態檔不一致，**Then** 判定結果只依狀態檔——把 `intents.json` 改成任何值都不改變輸出的 Status。[req:FR-J1]
4. **Given** 一個 `intents.json` 與狀態檔分岔的 record（現況範例：`260802-last-login-column`），**When** 同步執行，**Then** 仍依 AC 3 寫入，**且**產生一則同時載有兩邊值的 issue。[req:FR-J2]
5. **Given** 一個缺少 `## Stage Progress` 等必要區塊的 record（現況範例：`260802-default`），**When** 同步執行，**Then** 不對其產生任何看板寫入。[req:FR-J3]
6. **Given** 一個不在白名單中、且解析不出必要欄位的 record，**When** 對帳產出報告，**Then** 該 record 出現在「無法解析」清單中；而白名單中的 `260802-default` 不出現在該清單。[req:FR-J5]
   > **AC 4–6 的措辭理由**：原措辭把 Given 綁死在兩個現況 record 上。那兩個 record 一旦被修好，AC 的 Given 就消失，測試會**靜默地不再驗任何東西**。改為條件描述＋現況舉例。AC 6 的前半今日 Given 不可達（唯一的無法解析者已在白名單內），需 fixture——見全域 DoD 的「測試資料策略」。

**INVEST**：Independent ⚠️（依賴 S-1 綁定與 S-2 判定路徑）／Negotiable ✅／Valuable ✅／**Estimable ⚠️**（承載語言待 OQ-7）／Small ✅／Testable ✅。

---

## S-4 — 暫停與跳過在看板上看得出差別

> **As** 開發者（P1），**I want** 一個被 park 的 intent 在自訂欄位上標出它停著，**so that** 我隔幾天回來看那個欄位時不會把「停著」誤讀成「進行中」。

次要受益：P3（但見下方誠實邊界）。

> **Benefit clause 的誠實邊界（[M1=B]）**：交付這條 benefit 的是 **AC 2**（自訂欄位寫出 `parked @ <stage>`），**不是 AC 1**。AC 1（不送出 Status 寫入）的**視覺效果是零**——park 不動任何 checkbox（`requirements.md` FR-B 表格自述），所以「不寫」與「照寫」送出的都是同一個 `In progress`／`In review`；Status 那一格會**繼續顯示「進行中」**。AC 1 的真正受益者是 P4（省呼叫、把 item 移出分母，見 AC 5 與 S-9 AC 3），不是 P1／P3。收斂形式併入 **US-OQ-3**。

**Acceptance Criteria**

1. **Given** 一個 `## Runtime State` 的 `Parked` 欄位非空的 record，**且** S-5 的自訂欄位可寫入，**When** 同步執行，**Then** 機制對該 item **不發出任何 Status 寫入請求**（Status 停在最後已知值）。[req:FR-B6]
2. **Given** 同一個 record，**When** 同步執行，**Then** 該 item 的自訂欄位值含 `parked` 字樣與 `Parked At Stage` 的值（例如 `parked @ requirements-analysis`）。[req:FR-F4]
3. **Given** 該 record 執行 `unpark` 清除 `Parked` 後，**When** 下一次同步執行，**Then** Status 恢復依 S-2 的對照表判定，且自訂欄位恢復 S-5 AC 1 的一般格式。[req:FR-B6][req:FR-F4]
4. **Given** 兩個只在 `[S]`（在 scope 內但被跳過）與 `— SKIP`（不在 scope 內）上不同的 record，**When** 同步執行，**Then** 兩者的**同一個自訂欄位**值不同：前者含 `skipped` 字樣，後者不含。[req:FR-B3][req:FR-F3]
   > **改寫理由**：原措辭「存在一個可讀取的位置（自訂欄位**或** issue 受管區塊）」是選言落點，寫不出斷言；且它與 S-5 AC 1 的嚴格格式斷言直接衝突而兩者都無適用前提。本條指定落點為自訂欄位，S-5 AC 1 同步加上前提，兩者字面不再衝突。
5. **Given** 一個 `Parked` 非空的 intent，**When** 排程對帳執行，**Then** 它不出現在補平清單中，而出現在「已暫停」清單中。[req:FR-B6]
6. **Given** 一個 `Parked` 非空、**且**自訂欄位不存在也無法建立的 intent，**When** 同步執行，**Then** 存在至少一個可讀取的位置（issue 受管區塊或通報 issue）明確載有該 intent 的暫停事實；不得同時既不寫 Status 也不寫任何暫停標示。[req:FR-B6][req:FR-F2]
   > **新增理由（surface ＋ resolve 一起做）**：AC 1 與 S-5 AC 3 的組合會**重現本則故事要消滅的失敗模式**——欄位建立失敗 ＋ intent 被 park 時，Status 因 AC 1 不寫（凍在 `In progress`）、暫停事實因 S-5 AC 3 也不寫（欄位不存在），看板上就是一個持續顯示 `In progress` 的已暫停 intent。`phases/inception.md` 禁止把這種矛盾往下傳。

**INVEST**：Independent ⚠️（AC 2／AC 4 需 S-5 的欄位，AC 5 需 S-7／S-9 的清單）／Negotiable ✅／Valuable ✅／Estimable ⚠️／Small ✅／**Testable ⚠️**（全部 AC 的 Given 在今日 repo 不可達，需 fixture——見全域 DoD）。

> **註**：本則故事針對的是一個**機制存在但尚未發生**的情境——實測 6 個 record 的 `Parked` 全部落空。這不降低其必要性：不特判時被 park 的 intent 會被**持續**誤判為 `In progress`／`In review`。
> **附帶結論（實測 `aidlc-state.ts:830-832`）**：`handlePark` 在 `Status === "Completed"` 時直接拒絕，故 **`Parked` 與 `Done` 不可能同時成立**——對照表「`Parked` 優先於上列四條」對 `Done` 那一列是空轉的。此為事實記載，不改對照表（它由 requirements 的 [F4=A] 定案且已核可）。

---

## S-5 — 目前走到哪一站，看板上看得到

> **As** 觀看者（P3），**I want** 看板上直接顯示這個 intent 停在哪一站的名稱，**so that** 我不必進 repo 也知道它現在在哪一站，而不只是知道「有一張卡開著」。

次要受益：P1（回溯時的第一層線索）。

> **Benefit clause 的誠實邊界（[M1=B]）**：AC 1 交付的是形如 `requirements-analysis (2.3)` 的**識別字**，不是「進度」。對一個依本站假設不熟 AI-DLC 詞彙的人，這串字不構成位置感——他不知道總共幾站，而 FR-J4 明文規定 stage 清單逐 record 解析、各 record 的集合本就不同，**連總站數都不是常數**。可理解性列入 **US-OQ-3**（見 `personas.md` 的 PA-5）。

**Acceptance Criteria**

1. **Given** 一個已綁定、未 park、且無任何 `[S]` 標記的 intent，**When** 同步執行，**Then** 其自訂欄位值形如 `requirements-analysis (2.3)`，且與該 record 的 `Current Stage` 一致。[req:FR-F1]
2. **Given** 憑證缺少組織層 Projects 寫入權、或同名欄位已存在但型別不同、或組織政策阻擋欄位建立——**任一情形**，**When** 同步執行，**Then** 該欄位存在於看板上（值可為空），**或**產生一則說明「需人工建立欄位」的 issue；兩者不得同時不成立。且無論走哪一支，該次同步的 Status 寫入照常完成（欄位失敗不連坐 Status）。[req:FR-F2]
   > **改寫理由（兩處）**：①原 AC 2 的「機制**嘗試**自動建立它」不可觀察——什麼都不做與試了失敗在外部長得一樣；與原 AC 3 合成一條窮盡的二分後即可判定，並順帶把 A-5 那個未驗證假設變成可判定的。②原 AC 3 的 Given 是「框架不支援」，但 requirements 的 A-5 把「gh-aw 的 safe-outputs 沒有 Projects 操作」（ADR-0012 `:23-24` 實測結論）誤述成「平台不支援」；Projects v2 在 GraphQL 層有 `createProjectV2Field`（**未實測，列入 PRE-1**）。不改寫的話，AC 3 是一條沒有可達前提的分支，會被實作成永遠走不到的死碼。
   >
   > **指標（ADR-0016 §1／§10，2026-08-31T00:37:44Z）——本 AC 的 Given 現有兩處待處理，本 ADR 不逕改，指派 user-stories 的 Modify 模式**：①「憑證缺少**組織層** Projects 寫入權」的「組織層」前提作廢（實測 `opendiamonds` 為個人帳號），應讀作**個人帳號 Projects v2 寫入權**；②「**組織政策阻擋**欄位建立」**現已不可達**——無組織即無組織政策。AC 整體仍可滿足（Given 為「任一情形」，另兩支可達），故**不阻擋實作**，但 U-3 的 `CannotCreate` 可達前提應收斂為兩種（見 U-3 `business-rules.md` 的 R-4.2 同日註記）。
   >
   > **值得記下的形狀**：本 AC 的改寫理由逐字寫著「不改寫的話……會被實作成永遠走不到的死碼」——而**改寫後的版本自己又帶進一條不可達分支**。同一種缺陷從修正動作本身再次進入，正是 `project.md` `functional-design:c10` 附註的那一點。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`
3. **Given** 一個同時滿足「目前在 stage X」與「某個 in-scope stage 為 `[S]`」的 record，**When** 同步執行，**Then** 該**單一**自訂欄位的值同時含 stage X 的 slug 與跳過標記；且該次同步未在看板上新建第二個自訂欄位。[req:FR-F1]
   > **改寫理由**：原 AC 4（「檢視其定義，全部 stage 資訊落在單一欄位」）恆真且不可判——「檢視其定義」不是系統行為，而只寫一個欄位的實作必然通過。真正的失敗面是「單一欄位塞不下它被要求承載的三件事（stage、`parked @`、`skipped`）而靜默截斷」。
   > **開放決策（指派 application-design，見 US-OQ-4）**：該單一欄位在同時需要承載三種事實時的完整值格式與長度上限。**本站不裁定格式。**

**INVEST**：Independent ⚠️（依賴 S-1 綁定）／Negotiable ✅／Valuable ✅／Estimable ⚠️（AC 2 的可行性待 PRE-1 實測 `createProjectV2Field`）／Small ✅／Testable ✅。

---

## S-6 — 看板上的人工改動算數

> **As** 協作者（P2），**I want** 我在看板上拖動卡片之後，機制不要在下一輪把它默默改回去，**so that** 我在看板上表達的判斷會被送到人面前決定，而不是被機器直接輾掉。

次要受益：P4（他是那個要決定「該不該接受」的人）。

> **Benefit clause 的誠實邊界（[M1=B]）**：先前版本寫「我在看板上表達的判斷是有意義的，而不是白做工」。在**拒絕**路徑上那不成立——AC 4 的原文讓 PR 被關閉（未合併）時也恢復覆寫，P2 的改動仍然被輾回去，只是慢了一輪。已拆為 AC 4／AC 5，並把 benefit 改成 AC 真的交付的：**送到人面前決定**。

**Acceptance Criteria**

1. **Given** 看板端發生人為的狀態變更，**When** 反向同步執行，**Then** 產生一個以 `ut` 為 base 的 PR；`ut` 上不出現未經 PR 的相關 commit。[req:FR-G1]
2. **Given** AC 1 產生的 PR，**When** 檢視其 diff，**Then** 不含 `aidlc-state.md` 的任何一行。[req:FR-G2]
3. **Given** 一個開啟中的反向 PR，其變更含 intent X 的 record 路徑而**不含** intent Y 的，**When** 正向同步執行，**Then** 不對 X 的 item 送出 Status 寫入，**且照常**對 Y 的 item 寫入。[req:FR-G3]
   > **改寫理由**：FR-G3 要的是**逐 intent** 暫停，而先例（`origin/danniel/feat/github-sync-phase1` 的 `aidlc_sync_pull.py --all-intents`）是一次處理全部 intent 並開**單一** PR、分支名 `aidlc-sync/pull-<timestamp>`。在那個形狀下，只看 PR 的 open/closed 狀態會讓一個開著的 PR 把**全部** intent 一起暫停（over-suppression）。含反例的版本才驗得出來。連帶：`requirements.md` 的 A-6 敘述須更正——未驗證的不是「PR 開關狀態可否讀取」（`gh pr list --state open` 即可），而是**逐 intent 歸屬的判定方式**（讀 PR 內容 vs 讀 PR 狀態）。
4. **Given** 該反向 PR 被**合併**，**When** 下一次正向同步執行，**Then** 恢復對該 item 的 Status 寫入。[req:FR-G3]
5. **Given** 該反向 PR 被**關閉而未合併**，**When** 下一次正向同步覆寫該 item 之前，**Then** 該 item 的 issue 受管區塊載有一則記錄，指出該次人工改動未被採納與其時間戳。[req:FR-G3]
6. **Given** 某 item 的受管區塊內容與上一次同步時相同，**When** 反向同步執行，**Then** 不產生 PR、不產生 commit（雜湊比對防線）。[req:FR-G4]
   > **改寫理由**：原 AC（「任一道防線被關閉時存在一個可重現的迴圈情境」）要求「完成」等於「我們在真實 repo 與真實看板上示範過一次無窮迴圈」——代價是把垃圾寫進 P3 的資訊來源。且它有 2/3 與既有 AC 重疊（`[aidlc-sync]` 排除已由 S-1 AC 5 驗、狀態欄位單向已由本則 AC 2 驗），唯一沒有正面 AC 的是雜湊比對那一道。突變驗證本身已是 `project.md ## Mandated` 對每支自動化腳本的常設義務，不重述為 AC。
7. **Given** 反向同步產生的 PR，其變更僅涉及同步專用檔案，**When** 既有 `on: pull_request` 的 workflow 評估觸發條件，**Then** 指定的高成本 workflow（至少 `ui-regression`）不對其執行。[req:NFR-C1]
   > **新增理由（實測）**：`on: pull_request` 的 workflow 目前有 `ci.yml`（四個 job）＋ 6 支 gh-aw（`code-drift-alert`、`contract-guard`、`lint-fix`、`local-dev-drift`、`pr-reviewer`、`ui-regression`）。`ui-regression.md:17-21` 自己記載 PR #510 曾在單一 PR 上燒掉約 7 小時 runner 時間、零測試執行。反向同步每日一次 ⇒ 每天把一個只改同步狀態檔的 diff 送進完整 gauntlet，含 6 次 LLM 驅動的 agent 執行——既是成本，也把 `project.md` 點名的「所有 LLM 路徑」盲區放大。

**INVEST**：Independent ⚠️（依賴 S-1 綁定；且與 S-2 的 FR-G3 分支互為同批次，見依賴表）／Negotiable ✅／Valuable ✅／Estimable ⚠️（A-6 的逐 intent 歸屬判定方式未定，指派 application-design）／Small ✅／Testable ✅。

---

## S-7 — 每天自動對帳補平落差

> **As** 維運者（P4），**I want** 每天有一次自動掃描把漏掉的狀態補齊，**so that** 我不必自己逐個 intent 去比對看板與 record，落差會被自動補平並留下一個我事後看得到的數字。

**Acceptance Criteria**

1. **Given** 排程對帳與事件觸發同步同時到達，**When** 兩者執行，**Then** 對帳不佔用事件路徑的 concurrency 佇列，兩者可並行。[req:FR-D1][req:NFR-P3]
   > **改寫理由**：原 AC（「執行時段不與三支既有排程重疊」）是設定檢查而非行為；且 cron 是時間點不是時段，「重疊」無定義——實測三支既有排程為 `0 23 * * 1-5`／`37 0 * * *`／`39 16 * * 1`，任選第四個時間都自動通過。排程不衝突改為建置期檢查，移入全域 DoD（與 NFR-C2 同族）。
2. **Given** 對帳執行，**When** 決定處理清單，**Then** 清單等於「record 內存在綁定編號」**且**「`Parked` 欄位為空」的 intent 集合；且既有 71 個未綁定 item 的 `updatedAt` 在本輪對帳前後不變。[req:FR-D2]
   > **改寫理由**：原措辭「不被讀取也不被寫入」——任何合理實作都要列出看板 item 才找得到哪些已綁定，「不被讀取」多半必然違反或不可觀察。只斷言可觀察的那半。
3. **Given** 待處理的 intent 數量超過設定的單次上限，**When** 對帳執行，**Then** 本輪只處理到該上限為止；且該上限值以 workflow 的輸入或變數宣告呈現——把該宣告改為 M 後，下一輪處理量為 M。[req:FR-D3]
4. **Given** 一輪對帳中恰有 N 個 intent 的看板值與 record 不符且被補平，**When** 讀取其輸出，**Then** 該輪的補平計數等於 N。[req:FR-D4]
   > **改寫理由**：原 AC（「存在一個數值表示補平了幾個」）恆真——印一個寫死的 0 也通過。
5. **Given** 對帳偵測到落差，**When** 補平完成，**Then** 產生一則載有該 intent 識別字、stage 標識與時間戳的通報記錄；**且該次對帳 workflow 的結束狀態不因此為失敗**。[req:FR-E2]
   > **改寫理由（解一條真矛盾）**：原文引用「S-8 所述的通報」，而 S-8 AC 1 的兩個 Then 是「產生 issue」**與**「workflow 結束狀態為失敗」。逐字代入等於「**對帳成功補平一個落差 ⇒ 對帳 workflow 紅燈**」——一支每天成功做完該做的事然後紅燈的排程 job，與一支真的壞掉的 job 在 Actions 清單上長得一模一樣，等於把 P4 唯一的健康訊號自己毀掉。`requirements.md` 的 FR-E2 原文即內含此歧義，`phases/inception.md` 要求本站 resolve。

**INVEST**：Independent ⚠️（依賴 S-1 綁定與 S-2 判定）／Negotiable ✅／Valuable ✅／**Estimable ⚠️**（AC 3 的上限值待 PRE-1；承載語言待 OQ-7）／Small ✅／Testable ✅。

---

## S-8 — 機制失敗會叫人，不會沉默

> **As** 維運者（P4），**I want** 同步因外部錯誤失敗時 workflow 紅燈並自動開一則講清楚「哪個 intent、哪個 stage、什麼時間」的 issue，**so that** 我知道有事發生、也知道從哪裡開始查——而不是幾週後才發現看板早就錯了。

**Acceptance Criteria**

1. **Given** 一次寫入因**外部錯誤**（API 失敗、權限不足、逾時）而未完成，**When** 該次執行結束，**Then** workflow 的結束狀態為失敗，且產生一則 issue。[req:FR-E1]
   > **適用前提（解兩條真矛盾）**：
   > ① **依 FR-C1 主動中止寫入不屬本條所稱的失敗**——其處置為 S-3 AC 1 的開 issue，workflow 結束狀態不因此為失敗。若不加此前提，**P2 每一次正常使用看板（拖動卡片）都會讓 repo 的 CI 紅燈並產生一則 issue**：S-6 AC 3 的保護要等 FR-G1 的定時拉取才生效，而正向同步是事件驅動、5 分鐘內，中間的視窗裡正向同步會先讀到 P2 的值、判定不符、走 S-3 AC 1。一個受支援的使用者操作被系統當成故障回報。
   > ② **對帳成功補平不屬本條**——見 S-7 AC 5。
2. **Given** AC 1 產生的 issue，**When** 檢視其內文，**Then** 含該 intent 的識別字、觸發當下的 stage 標識與 ISO 8601 時間戳三者。[req:FR-E3]
3. **Given** 一次**成功**的 Status 寫入，**When** 檢視 workflow log，**Then** 同樣載有 intent 識別字、stage 標識與時間戳三者。[req:NFR-S6]

> **原 AC 4 已移除。** 它寫「同一個失敗重複發生時，通報的產生方式須避免把 P1 淹沒」，自承非二元可判卻留在 AC 編號序列裡——`phases/inception.md` 要求每條需求都有明確的 pass/fail 判準，`project.md`（`user-stories:c9`）授權的是「AC 本文加前提使字面不再衝突 ＋ 收斂手段列為開放決策」，沒有授權把一條驗不了的句子留在 AC 清單。
> 先前版本改用「AC 1 的產生 issue 適用於**一個失敗的首次出現**」作為前提——**該處置不成立且已撤回**：判定「是不是首次」需要**失敗身分（failure identity）＋跨輪持久狀態**（用什麼鍵判斷是同一個失敗、那份記憶存在哪），而全部 FR、NFR 與 C-N1 對 `sync-state.json` 的定義中，**沒有任何一條要求失敗身分或失敗歷史存在**。那個前提把不可判性從 AC 4 搬到 AC 1，不是解掉它。
> 收斂手段完整移交 **US-OQ-1**（application-design），並要求它產出一條二元可判的 AC 補回本則故事。

**INVEST**：Independent ⚠️（需要先有會失敗的寫入，即 S-1／S-2；原標 `Independent ✅` 不成立）／Negotiable ✅／Valuable ✅／Estimable ⚠️（US-OQ-1 未定）／Small ✅／Testable ✅。

---

## S-9 — 可信度本身看得到

> **As** 維運者（P4），**I want** 有一組數字與清單告訴我看板現在有多可信、哪些 intent 是機制刻意不維護的、以及機制自己跑得夠不夠快，**so that** 我能分辨「機制沒在動」與「機制正在正確地不動」。

**Acceptance Criteria**

1. **Given** 一輪對帳中，已綁定 intent 共 k 個，其中 1 個有未處理反向紀錄、1 個 `Parked` 非空、m 個看板與 record 不一致，**When** 讀取輸出，**Then** 一致率的分母為 k−2、分子為 m。[req:NFR-O2]
   > **改寫理由**：原 AC（「存在一個依此定義計算的數值」）恆真——印一個寫死的 0 也通過。本條代入具體數字後可失敗。
   > **分母維持上游 NFR-O2 的兩類排除，不擴為三類。**
   > **歸屬更正（reviewer iteration 1 Finding 3）**：本說明的前一版寫「`aidlc-quality-agent` 提議把『依 S-3 AC 1 回讀不符已中止』也移出分母……本站不採納該提議」。**該敘述失實，已更正。** 逐字核對兩份貢獻檔：`aidlc-quality-agent.md:216` 自己提出的 AC 1 改寫用的**就是 `k−2`**（維持上游兩類排除），與本站最終決定一致；`aidlc-design-agent.md:107-115`（C-6）只指出「第三類目前落在『沒被想到』而不是『決定計入』」並明寫「**本站不裁定**」，是中性的待決提問而非主張移出。**「擴為三類」是 lead 自己草擬的版本**，本站在此駁回的是自己的草稿，不是任何 agent 的提案。design agent 明確要求且已被採納的只有「AC 2 補第三份清單」。
   > 維持兩類排除的兩個理由：
   > ① **上游 NFR-O2 的原文只列兩類排除**（有未處理反向紀錄者、`Parked` 非空者），且它是已核可文字。下游擅自擴充已核可的指標定義，正是 `project.md ## Corrections`（`scope-definition:rev1-c4`）禁止的形狀。
   > ② 更根本的是，**該提議的前提站不住**：一個依 FR-C1 中止的 item，看板上留著的是一個機制自己判定無法擔保的值——**那本來就是真的不一致**，不是「機制正確地不動」。另兩類排除項的共同性質是「機制**刻意且正確地**不維護它」（人工裁決中、已暫停），中止不屬於這一類：它是一個待清理的異常，每一個都已由 S-3 AC 1 開了 issue。指標在有人清掉它之前不為 0 是**正確行為**，不是雜訊。
   > quality agent 真正的顧慮（P4 分不出「壞了」與「正確地不動」）由 **AC 2 的第三份獨立清單**解決——不動分母即可讓兩者可分辨。
2. **Given** 同一輪對帳，**When** 檢視其輸出，**Then**「等待人工裁決」、「已暫停」與「**回讀不符已中止**」**三份清單各自獨立列出**，不合併為一份。[req:NFR-O2]
3. **Given** 一個有未處理反向紀錄的 intent 與一個 `Parked` 非空的 intent，**When** 計算 AC 1 的數值，**Then** 兩者都不計入分母；而一個依 S-3 AC 1 回讀不符已中止的 intent **計入**分母且**計入**分子（它是待清理的真實不一致，見 AC 1 的說明）。[req:NFR-O2]
4. **Given** 連續兩輪對帳，**When** 第二輪結束後讀取輸出，**Then** 兩輪的補平計數各自帶有 ISO 8601 時間戳，且第一輪的值仍可取得。[req:NFR-O1]
5. **Given** 一個已綁定的 intent，其對應 issue 已被關閉而其 item 的 Status 不為 `Done`，**When** 對帳執行，**Then** 該 intent 出現在對帳輸出的「issue 與 Status 不相稱」清單中。**僅偵測與列出，不關閉 issue、不改寫 Status。**[新增：M2=A]（**本站新增的驗收面，非 NFR-O2 的一部分**——NFR-O2 的比對面是「看板 ↔ record」，本條是「issue 開關狀態 ↔ Status」，兩者不同軸。刻意不掛 `[req:NFR-O2]`，避免機械 grep 覆蓋率的人把它誤讀為上游已定義）
   > **新增理由（[M2=A]，本站新增的需求面，來源為本站而非上游）**：`intent-statement:15` 記載的動機事故逐字是「看板上有 item 標記為 In review，但對應的 issue **其實已經關閉**」——它比對的是「看板 Status ↔ **issue 的開／關狀態**」。而 Revision 1 之前的全部 56 條 AC 與 NFR-O2 的一致率定義，比對的都是「看板 ↔ **record**」，**零交集**。後果有二：①出事的那個 item 屬既有 71 個未綁定 item，落在 OOS-2 與 OOS-3 的交集內，連補救路徑都被封住；②對一個**全新、已綁定**的 intent，若有人在看板上關掉對應 issue（P2 有寫權），record 沒變、Status 沒變、一致率 0、對帳無落差、S-3 的回讀比對也通過（它比的是 Status 欄位值不是 issue 狀態）——**同型事故會在新機制上完整重演，並被每日報告成「一切正常」**。
   > 本條只偵測不動作，**不觸及 OOS-2**（不自動關閉 issue）；只涵蓋已綁定者，**不觸及 OOS-3／W-4**（不做既有 71 項的歷史漂移修正）。既有那 71 項仍不被涵蓋，這是 OOS-3 的既有決定，不是本條的疏漏。
6. **Given** 連續 20 次事件觸發的同步，**When** 讀取其量測，**Then** 至少 19 次的「push 完成 → 看板 Status 更新」間隔 ≤ 5 分鐘。[req:NFR-P1]
   > **移入理由**：原為 S-2 AC 8 的 per-run 二元閘門。GitHub-hosted runner 的排隊時間不受本 repo 控制，per-run 斷言是結構性 flaky；`phases/operation.md` 要求 SLO 以百分比＋時間窗表達。改為量測型後有明確分母、不會單次紅燈，也給 P4 一個真的能追的數字。

**INVEST**：Independent ⚠️（AC 1–4 依賴 S-7 的對帳輸出；AC 1 的分母需 S-6 才算得對——在 S-6 之前它會算出一個**看起來合理但錯誤**的比率，比沒有更糟）／Negotiable ✅／Valuable ✅／**Estimable ⚠️**（承載語言待 OQ-7）／Small ✅／Testable ⚠️（AC 2／AC 3 需三份清單各有內容，今日 `Parked` 清單必為空，需 fixture）。

---

## S-10 — 映射、端到端與權限都有持續生效的斷言

> **As** 維運者（P4），**I want** 對照表的判定、真實寫入路徑、承載形式與憑證權限各自有一組留在 repo 裡持續生效的斷言，**so that** 有人改壞映射、把判定搬進 LLM、或權限被放寬時，CI 會紅燈而不是等看板悄悄開始說謊。

**Acceptance Criteria**

1. **Given** 一個把 `[?]` 映到 `In progress` 的變更被提交為 PR，**When** CI 執行，**Then** CI 的結束狀態為失敗，且失敗輸出指出「預期 `In review`／實得 `In progress`」；**且**同一次 CI 執行未對 GitHub Projects API 發出任何寫入請求。[req:FR-I1]
   > **合併理由**：原 AC 1（「存在一組測試，對給定的 record 輸入斷言其輸出 Status」）單獨看是**元層次**——驗收的是「有沒有寫測試」而非「映射對不對」，一組 `assertEqual(map(r), map(r))` 形狀的空洞斷言即可通過。原 AC 3（突變驗證）單獨看是 **meta²**——它驗的是「AC 1 那組測試不是空的」。合併後是純粹的可觀察行為：沒寫斷言 → 綠燈 → AC 失敗；斷言寫成空洞的 → 綠燈 → AC 失敗。且不重述 `project.md ## Mandated` 對 tcms 已有的常設突變義務。
2. **Given** 一個**本次執行專屬**的測試 item（每次執行建立、結束後刪除，或位於獨立於 #16 的測試看板），**When** 端到端流程在 CI 執行，**Then** 實際寫入並讀回比對；比對失敗時 CI 結束狀態為失敗，且失敗輸出載有該次寫入的 HTTP 狀態碼。[req:FR-I2]
   > **前提的必要性（實測疊加）**：若測試 item 常駐於 #16，它就是**第 72 個 item**，會出現在 P3 的視野裡——一張每次 CI 都在閃的測試卡片，正是要消滅的雜訊。更嚴重的是 `ci.yml` 的 `on: pull_request` 無分支過濾，多個 PR 會**同時**跑端到端測試、寫同一個測試 item，正好命中 S-3 AC 1（回讀不符 ⇒ 中止 ＋ **開一則 issue**）——PR 一多，**CI 會自動增生 issue**。測試 item 的歸屬（#16 上的專用 item vs 獨立測試 project）指派 **application-design，見 US-OQ-5**。
3. **Given** 一個「不該寫回 record」的看板變更（例如變更來源的 commit 訊息含 `[aidlc-sync]`），**When** 反向路徑執行，**Then** 不產生 PR；**且**給定一個「該寫回」的變更時，同一路徑產生 PR。[req:FR-I5]
4. **Given** 承載對照表判定的 job 定義，**When** 檢視該 job 的步驟清單，**Then** 其中不含任何代理式引擎步驟（`engine:` 宣告或編譯後的 agent step）；把該步驟改為由 agent 產生 Status 時，此斷言失敗。[req:FR-B2]
   > **落點理由**：這是**artifact 層的靜態性質**（workflow 定義檔裡有沒有 agent step），不是執行期黑箱可觀察的行為，依 `project.md`（`units-generation:c6`）不得與執行期契約併入同一單元。它的失敗模式（有人把映射邏輯搬進 gh-aw prompt）由 CI 對 workflow 檔的靜態檢查抓，與 AC 1 的 dry-run fixture 不同類。原掛在 S-2 AC 11，該處只留執行期的決定性（現 S-2 AC 14）。
5. **Given** 同步身分的憑證，**When** 它嘗試一次宣告範圍外的寫入（例如直接推送 commit 到 `ut`，或修改 record 目錄以外的檔案），**Then** GitHub API 回應 403，且該次嘗試留在 workflow log 中。[req:NFR-S1]
   > **升格理由（[M3=A]）**：本條原分流在全域 DoD，理由是「沒有 persona 在任何介面上看得到權限集合」。該理由對**被授予的集合**成立，但**權限的效果可觀察且二元**——拿憑證做一次範圍外寫入，看它回 403 還是 200；且 P4 明確擁有它。決定性因素是 `requirements.md` 的 R-1 已記載 feasibility 那張 ADR-0006 IAM 判定表**原文已不成立**（它寫「不索取 repo 內容寫入權」，而三項已核可決定都要寫 repo），收斂手段尚未定案（OQ-1）。在 IAM 面已被推翻、收斂未定的情況下對「本 repo 最大的單一權限授予」不留任何可失敗的斷言，與 `project.md ## Mandated`「涉及 IAM 的變更不得僅以已有 ADR-0006 帶過」有直接張力。本條同時產生 OQ-1 要求的「重跑 ADR-0006 四面向判定」所需的證據。
   > **已知代價**：在 OQ-1 定案前，「宣告範圍」是浮動的，本條的 Given 可能隨之調整。

**INVEST**：Independent ❌（AC 2 需 S-1／S-2 存在才有端到端可跑，AC 3 需 S-6；原標 `Independent ✅（可先於被測對象存在）`**不成立**）／Negotiable ✅／Valuable ✅／Estimable ⚠️（AC 3 的判準型式待 OQ-2；AC 5 的範圍待 OQ-1）／**Small ⚠️**／Testable ✅。

> **Small ⚠️ 與切線建議（比照 S-2 套同一把尺）**：本則的 5 條 AC 橫跨**三種不同的驗證機制**，內部異質度高於 S-2 的切線①。先前版本標 `Small ✅` 且無切線註記，是同一條規則在同一份文件裡套了兩把尺。建議切線：①**dry-run 映射斷言**（AC 1）②**建置期靜態檢查**（AC 4）③**需要真實憑證與網路的實寫**（AC 2、AC 5）④**反向路徑判準**（AC 3，型式待 OQ-2）。**本站不決定切分。**

---

## S-11 — README 指得到需求正本

> **As** 協作者（P2），**I want** repo 的 README 有一段話告訴我需求清單在 Project #16，**so that** 我第一次進這個 repo 找「要做什麼」時，不會在 repo 裡翻一份不存在的清單。

**Acceptance Criteria**

1. **Given** repo 根目錄的 `README.md`，**When** 檢視其內容，**Then** 存在一段含 Project #16 連結的文字，說明該看板是需求清單的正本。[req:FR-H1]
2. **Given** 同一份 `README.md`，**When** 與變更前比對，**Then** `git diff --numstat` 對 `README.md` 的**刪除行數為 0**。[req:FR-H1]
   > **改寫理由**：原措辭「既有結構與總覽敘述未被改動」不可判（什麼算結構？改一個標點算不算？）。刪除行數為 0 是二元、可 grep，且精確表達了「只增不動」的原意。
   > **註**：本則與全域 DoD 的 `validate_repo_contract.py`（其 `REQUIRED_TEXT` 已鎖住 README 的關鍵字）有部分重疊，不是缺陷；下游不需為此另設檢查。

**主 persona 由 P3 改為 P2（Revision 1）**：先前版本在 `stories.md` 標 P3、在 `personas.md` 標 P1，**同一站的兩份產出互相矛盾**；且 P3 版本本身不可能成立——P3 的定義是不參與開發、本站按「不進 repo」設計，而本則的 goal 逐字是「我從 repo 進來時」。P2 是四個 persona 中唯一「會進 repo、但不跑 AI-DLC」的人，與 FR-H1 的實際受眾相符。`personas.md` 已同步（P1 移除 S-11、P2 加入）。

**INVEST**：Independent ✅／Negotiable ✅／Valuable ✅／Estimable ✅／Small ✅／Testable ✅。

---

## 故事依賴與排序

依 `project.md ## Corrections`，**「技術依賴」與「避免重工」必須分開標明**——兩者在依賴圖上長得一樣，不區分會讓 delivery-planning 把經濟性排序當成不可動的 DAG 邊。本表於 Revision 1 依 `aidlc-developer-agent` 的逐列查核大幅修訂。

| 從 | 到 | 性質 | 說明 |
| --- | --- | --- | --- |
| PRE-1 | S-1～S-10 | **技術依賴** | ~~憑證確實帶組織層看板寫入權~~ **憑證確實帶個人帳號 Projects v2 寫入權**〔**經 ADR-0016 §1／§2 更正**（2026-08-31T00:37:44Z）：實測確認 `opendiamonds` 是個人帳號（`GET /orgs/opendiamonds` → 404），**無組織可授此權限**；憑證身分改為擁有者帳號 token，Projects 側由 `project` scope 承載。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕未經實測前，任何寫入路徑都無法完成。**Revision 1 補入 S-10**——其 AC 2／AC 5 用的是同一組憑證 |
| S-1 | S-2、S-3、S-4、S-5、S-6、S-7 | **技術依賴** | 沒有綁定編號（FR-A2）就不知道要寫哪一則 issue。**Revision 1 補入 S-6**——AC 3 的逐 item 暫停與 AC 1 的回寫都要知道對象 |
| S-5 | S-4 | **技術依賴** | 不只是「欄位得先存在」：S-4 **繼承** S-5 AC 2 的失敗降級行為，兩者的降級路徑必須一起設計（見 S-4 AC 6） |
| S-7 | S-4、S-9 | **技術依賴** | S-4 AC 5 的「**不出現在補平清單**」那半與 S-9 AC 1／AC 4 的數值都是對帳的產物。**S-4 AC 5 的兩半來源不同**：「補平清單」由本列（S-7）提供，「已暫停清單」由下一列（S-9 AC 2）提供；兩條邊都是阻擋邊，缺任一條 S-4 AC 5 都驗不完整 |
| S-9 | S-4 | **技術依賴** | S-4 AC 5 的「**出現在已暫停清單**」那半是 S-9 AC 2 的產物（與上一列並存，非擇一——見上列說明） |
| S-6 | S-9 | **技術依賴** | S-9 AC 1 的分母要扣掉「有未處理反向紀錄者」，那是 S-6 的產物。**在 S-6 之前，AC 1 算得出一個看起來合理但錯誤的比率，比沒有更糟** |
| S-2 | S-3、S-7、S-8 | **技術依賴** | S-3 的「不寫」是在 S-2 的判定路徑上做的分支；**S-7 的對帳要先用 S-2 的映射判定算出「record 端預期的 Status」才有東西可與看板比對補平**（reviewer iteration 1 Finding 4：此邊原本只寫在 S-7 的 INVEST 註記裡而漏在表外，delivery-planning 可能因此排出 S-7 先於 S-2）；S-8 AC 1 需要先有會失敗的寫入 |
| S-1／S-2 | S-10 | **技術依賴** | S-10 AC 2 的端到端需要寫入路徑存在 |
| S-6 | S-10 | **技術依賴** | S-10 AC 3 驗的是反向路徑 |
| **S-2 的 FR-G3 分支** | **S-6** | **技術依賴（且同批次）** | **Revision 1 修正**：先前標為「S-6 → S-2 避免重工」，方向不完整。S-2 先上、之後回頭加分支 = 避免重工（可覆寫）；但 **S-6 先上而 S-2 尚無 FR-G3 分支則不可接受**——反向 PR 開著的整段期間，正向同步會把 P2 的改動輾回去，正是 S-6 存在的唯一理由 |
| S-2 其餘部分 | S-6 | **避免重工** | 可覆寫 |
| S-10 的 AC 1／AC 4 | S-2 | **避免重工** | 可 test-first |
| **OQ-7** | S-2、S-3、S-7、S-9 | **技術依賴（外部裁決）** | **Revision 1 新增**。三擇一直接決定映射解析的承載形式：「既有豁免」下可用 Python 腳本，另兩者下必須落在 workflow YAML 或 composite action，兩種形狀的工作量與可測試性完全不同。**連帶：S-2／S-3／S-7／S-9 的 Estimable 由 ✅ 降為 ⚠️**——連承載語言都還沒定 |
| （無） | S-11 | — | 無前置依賴 |

> **關於 OQ-7 的事實核對（lead 裁定）**：`aidlc-developer-agent` 附帶主張「requirements 稱 PR #508 已合併與 repo 現況不符」。**該子主張已被推翻**——經 GitHub API 直查（`repos/opendiamonds/cloud-360/contents/scripts?ref=ut`），遠端 `ut` 的 `scripts/` 確實含那三支腳本，OQ-7 的前提正確。該 agent 被本 worktree 內一個名為 `origin/ut` 的**本機分支**（`refs/heads/origin/ut`）誤導，它遮蔽 `refs/remotes/origin/ut` 而解析到 2026-07-31 的 `a2613ef`。**依賴表新列本身成立，予以採納；事實反駁駁回。**（此 worktree 的 ref 陷阱本身值得記入 §13 learnings。）

### deploy-on-merge 的「同批次」檢查

依 `project.md ## Corrections`（`delivery-planning:c6`）：破壞性契約變更與其消費端之間有一條比 DAG 邊更強的「不得分批」約束。

> **Revision 1 翻轉了先前的結論。** 先前版本寫「未發現同批次約束」，理由是「本 intent 不變更任何既有端點的回應形狀」。**該理由不成立**——`c6` 的實質是「破壞性契約變更與其**消費端**」，而本 intent 的契約消費端不是 HTTP 端點，是 **Project #16 這塊有活人在看的板子**（P2、P3）。每一個 Bolt 邊界都是一次真實部署，板子在那個中間態就是那個樣子給人看。代入後至少三處成立：

| # | 約束 | 判定 | 理由 |
| --- | --- | --- | --- |
| G1 | **S-2 與 S-3 不得分批** | **成立** | S-2 單獨上線 = 機制開始寫看板，但沒有寫入前回讀（S-3 AC 1）、沒有分岔通報（AC 4）、沒有無法解析就跳過（AC 5）。「寧可不寫、不可寫錯」是本 intent 的核心取捨，先上「會寫」再補「不寫錯」把取捨倒過來了 |
| G2 | **S-6 與 S-2 的 FR-G3 分支不得分批** | **成立** | 見依賴表該列 |
| G3 | **S-1 不得單獨上線** | **成立（推翻先前判定）** | 先前寫「S-1 單獨上線的中間態是有效且不誤導的」。實際上 AC 1 把 Status 設為 `Ready`，S-2 未上線 ⇒ 這張卡**永遠停在 `Ready`**，即使該 intent 已跑到 `application-design`。對只看看板的 P3，一格寫著 `Ready` 而實際在跑，與寫著 `In review` 而實際已關閉是**同一類**的謊。這格不是「還沒開始更新」，它是「錯的」 |
| G4 | S-5 單獨上線 | **今日不成立，但屬時間上的僥倖** | 6 個 record 全部沒設過 `Parked`，故 S-5 缺 S-4 的中間態碰不到 park 情境。但**任何人第一次跑 `park` 就立刻變成 G1 級的問題**，且沒有任何機制擋住那件事。另：S-5 上線的那一刻，71 個既有未綁定 item 會立刻多出一個空欄位給 P2／P3 看見——**OQ-8 的決定在 S-5 部署後就變成公開且不可撤回的**，delivery-planning 應據此知道那個 gate 的實際期限 |
| G5 | S-6 的反向 PR 會啟動整組 PR gauntlet | **成本約束，非同批次** | 見 S-6 AC 7 |

---

## 全域 Definition of Done

依 [Q4=B]，下列不立故事而作為**全部 11 則故事共同的完成條件**。分流理由逐條列出。

| # | 完成條件 | 分流理由 |
| --- | --- | --- |
| NFR-S2 | Projects 憑證為獨立 secret，其他 workflow 的設定不引用它 | 屬設定檢查而非行為；沒有 persona 在介面上看得到 |
| NFR-S3 | `python3 scripts/validate_repo_contract.py` 通過 | 已有既有機制承載，不需新故事 |
| NFR-S4 | 機制不新增資料庫、不落地任何含機敏內容的檔案 | 是「不做某事」的約束，沒有可展示成果 |
| NFR-S5 | 新增的檔案不含任何監聽或端點宣告 | `requirements.md` 已判定此面向**不適用**；立故事會產出空故事 |
| NFR-P2／P4 | 對帳每日一次；單次處理量有明確上限 | 已由 S-7 AC 1／AC 3 承接，此處僅為交叉索引 |
| NFR-C1 | `ci.yml` 四個 job 與 `deploy.yml` 的**行為**與變更前相同 | 跨切迴歸條件，任何一則故事都不「擁有」它。**但它底下兩個具體且已實測的失敗路徑已升格為 AC**：S-1 AC 7（回寫 commit 取消既有 CI run）與 S-6 AC 7（反向 PR 觸發完整 gauntlet） |
| NFR-C2 | `.github/workflows/` 下無重複 `name` | 屬建置期檢查。**誠實記載**：本 intent **不新增執行它的機制**，違反時由 code review 攔截——OQ-4 管的是 `.md` ↔ `.lock.yml` 漂移，不是 name 碰撞。不要讓下一個人以為 DoD 裡有一道閘門 |
| NFR-M1 | `.md` ↔ `.lock.yml` 編譯漂移的風險被明確承接 | 收斂手段由 [req:OQ-4] 指派 ci-pipeline；本站不裁定 |
| **排程不衝突** | 對帳排程的執行時段不與 `daily-digest`（`0 23 * * 1-5`）、`agentics-maintenance`（`37 0 * * *`）、`release-watch`（`39 16 * * 1`）碰撞 | **Revision 1 由 S-7 AC 1 移入**：cron 是時間點不是時段，且「檢視設定」不是系統行為；屬建置期檢查，與 NFR-C2 同族 |
| **全路徑無 LLM** | 任何產生或修改 Status 的執行路徑（事件同步、排程對帳、反向路徑）皆不呼叫語言模型 | **Revision 1 新增**。原 S-2 AC 11 只綁在 S-2，照現況把 LLM 放進 S-7 的對帳判定或 S-3 的中止判定，**沒有任何 AC 會失敗**。承載形式的靜態檢查在 S-10 AC 4，本列是它的全路徑宣告 |
| **測試資料策略** | 存在一套 fixture 機制，涵蓋下列今日 Given 不可達的斷言：S-4 全部（`Parked` 在 6 個 record 全部落空）、S-3 AC 6 前半（唯一的無法解析者已在白名單內）、S-9 AC 2／AC 3（三份清單需各有內容） | **Revision 1 新增**。fixture 應由**真實引擎命令產生**（`aidlc-state.ts park`）而非手寫假的 `aidlc-state.md`——手寫 fixture 會與引擎格式漂移，而 S-2 AC 7–10 又要求解析語意與引擎一致，等於用自己的猜測驗自己的猜測。實測三道閘門：`handlePark` 在 `Construction Autonomy Mode: autonomous`（`aidlc-state.ts:824-829`）、`Status === "Completed"`（`:830-832`）、`Current Stage` 為空（`:833-836`）三種情況下都會拒絕。**且不得對真實 intent 執行 `park`**——它會寫 `WORKFLOW_PARKED` 到 audit shard 並改 `Last Updated`，污染該 intent 的真實狀態與稽核紀錄。fixture 的建立方式與其測試用綁定編號指派 **application-design（US-OQ-6）** |
| 純函式驗證建議 | 映射判定為純函式，適合以 property-based 測試斷言「對任意 checkbox 組合恰好輸出一個值」（S-2 AC 15 的加強形式） | `team.md ## Testing Posture` 記載本 repo 已有 8 個 `@given` 全落在純函式模組，落點慣例吻合。依 `user-stories:c3` 寫進 DoD 而非 AC |
| 測試底線 | 依 `team.md ## Testing Posture` 的 A／B／C 三項在適用範圍內生效 | 團隊既有規則，非本 intent 新增 |
| TCMS | 每則故事的 construction 須通過 `tcms-test-cases` stage（blocking） | `project.md ## Mandated`，全 intent 適用 |

> **NFR-S1 已移出本表**——依 [M3=A] 升格為 S-10 AC 5。

---

## 上線前置條件

### PRE-1 — 憑證與框架上限的實測（CAP-9；FR-I3、FR-I4）

**不立為故事**（[Q5=A]）：其產出是一份實測結論，沒有可部署、可展示的東西；`scope-document` 亦明記 CAP-9「Must，但**不構成交付批次**」。

必須確認的事項：

1. 鑄出的憑證確實帶 ~~組織層~~ **個人帳號 Projects v2** 看板寫入權——以最小可行呼叫實測，**不得以文件敘述代替驗證**。[req:FR-I3]
   > **經 ADR-0016 §1／§2 更正**（2026-08-31T00:37:44Z）：「組織層」前提作廢（見上方依賴表同日註記）。且**四項權限不再是可分別授予的四項**——Projects 側由 `project` scope 承載，contents／Issues／Pull requests 三者由 `repo`（或 `public_repo`，待 PRE-1-c）scope **整包**承載，無法分別授予。連帶使 `requirements.md` NFR-S1 的「無額外授予」判準結構性不可滿足，已於 ADR-0016 §2 改述。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`
   > **經 ADR-0014 擴充**：本項須涵蓋**三項**權限各至少一次真實呼叫，其中**必須包含一次開 issue**。只驗 Projects 寫入不構成本項通過——缺 Issues 寫入權的憑證會讓本項通過而在 Bolt 1 才失敗。
2. 框架單次操作次數上限（C-T5）的**實際值**，以及超限時的行為（截斷／報錯／靜默略過）。[req:FR-I4]
3. **Projects v2 的 `createProjectV2Field` 是否可用**——這決定 S-5 AC 2 走哪一支。（`requirements.md` 的 A-5 敘述須更正：ADR-0012 `:23-24` 的實測結論是「**gh-aw 的 safe-outputs** 沒有 Projects 操作，必須提權讓 workflow 直接呼叫 `gh` CLI／GraphQL」——「未支援」的主體是 gh-aw，不是平台。）
4. 順帶回答 A-1（~~組織層安裝 App 的權限是否受政策阻擋~~ —— **經 ADR-0016 §1 判定為不適用**（2026-08-31T00:37:44Z）：無組織、無 App，故無政策可阻擋）、A-2（變數名稱與文件描述不一致）、A-3（看板更新行為是否如文件所述）、A-8（同步身分對 feature 分支的寫入權是否受分支保護阻擋）。

> **本清單四項之外另有三項追加實測項**（2026-08-31T00:37:44Z 補記）：**PRE-1-a**（Rulesets file-path restriction，由 `application-design/decisions.md` 的 ADR-A2 追加）、**PRE-1-b**（`Issue.projectItems`，由 ADR-0015 §1 追加）、**PRE-1-c**（`public_repo` ＋ `project` 的四條寫入路徑，由 ADR-0016 §7 追加）。三者依本 record 的既有慣例落在 `delivery-planning/bolt-plan.md` 的 PRE-1 表而**不回改本清單**，故本節的「四項」**不是** PRE-1 的完整範圍——完整範圍為**七項**，以 `bolt-plan.md` 的 PRE-1 表為準。此註記存在的理由是：只讀本節的人會以為 PRE-1 只有四項。

**開放決策（指派 delivery-planning／2.8，見 US-OQ-2）**：CAP-9 的產物如何在 Construction 留下可追溯的證據。

---

## 假設與待決事項

### 本站對上游假設的更正（不回改上游檔案）

| 上游假設 | 更正內容 | 依據 |
| --- | --- | --- |
| A-5 | 「框架支援自動建立看板自訂欄位；**安全輸出清單中未見此型別**」把「gh-aw 沒有這個 safe-output」誤述成「平台不支援」。Projects v2 在 GraphQL 層有 `createProjectV2Field`（**本站未實測**，列入 PRE-1 第 3 點）。不更正的話，S-5 AC 2 的「無法自動建立」分支會被實作成永遠走不到的死碼 | ADR-0012 `:23-24` 的實測結論 |
| A-6 | 「反向 PR 的開關狀態可被正向同步讀取」誤指問題所在。開關狀態可讀（`gh pr list --state open`）；**未驗證的是逐 intent 歸屬的判定方式**（讀 PR 內容 vs 讀 PR 狀態）。先例以 `--all-intents` 開單一 PR，在那個形狀下 FR-G3 會變成 over-suppression | `origin/danniel/feat/github-sync-phase1` 的 `aidlc_sync_pull.py` 與 `aidlc-sync-pull.yml` |

> 依 `project.md ## Corrections`（`refined-mockups:c3`）：這是**對齊修正、非本站新定案**，上游檔案本身不回改。另，`scope-document` 的 CAP-1 原文寫「設 In progress」而 requirements FR-A1 依 [Q1=A] 寫「設 `Ready`」——以 FR-A1 為準，理由見問題檔的「對齊註記」段。

### 本站新增的假設

`personas.md` 的 `## Assumptions & Open Questions` 列出五項（PA-1～PA-5），其中 PA-1（P3 沒有交叉驗證管道）與 PA-2（P4 作為獨立 persona）是本站新增的主張。**先前版本此處寫「本站未新增任何假設」，與該事實不符，已更正。**

### 本站新增的指派

| # | 事項 | 指派落點 | 必須產出的決定 |
| --- | --- | --- | --- |
| US-OQ-1 | 重複失敗的通報收斂手段（原 S-8 AC 4） | **application-design** | 去重／聚合成單一 issue 並更新／沉默窗口三擇一，並產出一條**二元可判**的 AC 補回 S-8。須說明它需要什麼持久狀態（失敗身分的鍵、存放位置），因為目前沒有任何需求要求那份記憶存在 |
| US-OQ-2 | CAP-9 產物在 Construction 的留痕形式（PRE-1） | **delivery-planning（2.8）** | 一個具體的留痕形式，可在對應 Bolt 的 review 上被確認。落點理由：「不構成交付批次的 Must 如何在批次序列中留痕」是 Bolt 切分那站的問題 |
| US-OQ-3 | **「機制刻意不寫」在看板側的可感知形式**（[M1=B]） | **application-design** | 一個 P3 不進 repo 即可讀到的標記形式（issue 受管區塊／自訂欄位／二擇一），涵蓋三種情形（回讀不符／已暫停／待人工裁決）與其原因類別及時間戳；並回答它與 FR-F1「單一欄位」約束的關係。**一併涵蓋**：①`Done` 卡片下掛開啟中 issue 的說明（OOS-2 ＋ FR-B1 的必然後果，與立案事故同型而方向相反）②未綁定的 71 項與受管項在板上的可分辨性（OQ-8 的使用者面）③stage 識別字對非開發者的可理解性（PA-5） |
| US-OQ-4 | 自訂欄位在同時承載 stage、`parked @`、`skipped` 三種事實時的完整值格式與長度上限 | **application-design** | 一個具體格式與截斷行為 |
| US-OQ-5 | S-10 AC 2 的測試 item 歸屬 | **application-design** | #16 上的專用 item vs 獨立測試 project；須說明它如何不進入 P3 的視野、以及並行 CI 不會因回讀不符而增生 issue |
| US-OQ-6 | fixture 機制的建立方式與其測試用綁定編號 | **application-design** | 一個不污染真實 intent、且不手寫 `aidlc-state.md` 的產生方式 |
| US-OQ-7 | 決定性映射邏輯的承載形式，使 S-10 AC 1 的 dry-run 斷言有可驅動的對象 | **application-design** | composite action（`.github/actions/`，本 repo 無先例、`validate_repo_contract.py` 的 `REQUIRED_FILES` 不涵蓋它）／同 workflow 的 assertion job（斷言與被測物耦合在同一段字串）／其他；須說明其在 contract 或 CI 上如何不被無聲刪除。**注意**：複製一份邏輯到測試直接違反 `team.md ## Code Style` 的「單一真實來源」，且該條要求的「鎖住兩者一致的測試」在此鎖不起來（兩份副本本身就是測試與被測物） |

### 承接自上游、仍待裁決

`requirements.md` 的 A-1～A-8 與 OQ-1～OQ-8 全數維持。**[req:OQ-7]**（PR #508 已合併的 `scripts/aidlc_sync_*.py` 三支腳本與 ADR-0013 §3 及 `project.md ## Forbidden` 的衝突）仍待**使用者裁決**，已跨 reverse-engineering、requirements-analysis、user-stories 三站未決；它現已進入本站的依賴表（見上），因為三擇一直接決定四則故事的承載語言。

---

## Revision 1（2026-08-24，mob round 1 整合）

三位支援 agent 各自產出貢獻檔（`contributions/`）。多數 OBJECT 為 lead 可直接整合的修正，已逕行整合；三項判斷題依 stage-protocol §5 於階段中途交付人工裁決，結果 **M1=B、M2=A、M3=A**。

| 來源 | 主要改動 |
| --- | --- |
| `aidlc-design-agent` | S-11 主 persona 由 P3 改為 P2 並與 `personas.md` 對齊（C-1）；P3 的「無交叉驗證管道」由事實降級為本站最壞情境假設並補 `## Assumptions & Open Questions`（C-2）；S-3／S-4／S-5／S-6 四則的 benefit clause 依 [M1=B] 弱化到 AC 真的交付的程度並新增 US-OQ-3（C-3、C-4、C-5、C-7）；S-9 補第三份清單（C-6；該貢獻對「第三類是否計入分母」明寫不裁定，lead 最終維持上游兩類排除）；S-6 AC 4 拆出 reject 路徑（C-8）；S-8 AC 1 加適用前提排除 FR-C1 主動中止（C-9）；來源標籤與 S-7 benefit 修正（C-10） |
| `aidlc-quality-agent` | 5 條恆真 AC 依 `user-stories:c4` 全數改寫而非刪除（S-1.6、S-2.4、S-5.4、S-7.4、S-9.1）；11 條不可判 AC 改寫（含 S-2 的 oracle 問題與觸發優先序拆分）；6 條元層次 AC 處置（S-10 合併、S-6 AC 5 改正面斷言、S-2 AC 11 移入全域 DoD）；S-8 的 `c9` 處置撤回重做（「首次出現」前提需要從未被任何需求要求存在的失敗身分）；S-7 AC 5 與 S-8 AC 1 的矛盾（對帳成功補平 ⇒ 紅燈）resolve；[M2=A] 的覆蓋洞；[M3=A] 的 NFR-S1 升格；NFR-C1 底下的 `ci.yml` 取消路徑升格為 S-1 AC 7；測試資料策略進 DoD。**quality agent 的 AC 1 改寫（`k−2`）已原樣採納**，與上游 NFR-O2 的兩類排除一致 |
| `aidlc-developer-agent` | S-2 AC 11 的擴權改寫並把靜態檢查移至 S-10 AC 4；S-2 AC 7 的不存在 oracle 改為四條行為 fixture；S-2 AC 15 總函式性；S-4 AC 6 雙重降級；S-1 AC 5／S-6 AC 5 的身分前提；A-5／A-6 的平台事實更正；S-6 AC 3 含反例版本與 AC 7 成本控制；依賴表六處修正與 OQ-7 入表；同批次結論翻轉（G1／G2／G3 成立）；S-10 的切線註記 |

**維持不變的判斷（三位皆未推翻，或推翻未成立）**：[Q1=A] 的四 persona 切法、[Q2=A] 的切分軸、[Q3=A] 的粒度與 S-2 的 Small ❌ 據實記載、[Q5=A] 的 PRE-1 不立故事、S-4 對「機制存在但尚未發生」的必要性論證。

**lead 裁定駁回的一項**：`aidlc-developer-agent` 主張「requirements OQ-7 稱 PR #508 已合併與 repo 現況不符」——經 GitHub API 直查推翻，詳見依賴表下方的註。

---

## Review

**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-24T03:02:40Z
**Iteration:** 3（驗證輪）
**Verdict:** READY

### Critical 的處置驗證

**結論：genuinely resolved。** 三項獨立機械證據交叉核對一致，且揭露文字是坦承而非辯護。逐項列出核對過程：

**1. Audit shard 的事件序列與 iteration 2 描述的期望形狀吻合。**
   `audit/jiangzhengdaodemacbook-pro-local-82da74e002f9.md` 尾段（行 4812–4828）：

   - `01:15:34Z` `DECISION_RECORDED`——「M1-M3 重新確認：原作答的可驗證性因 lead 未即時寫回與偽造時間戳而受損，當場重新取得」（記錄的是**決定重問**，非答案本身）。
   - `02:56:44Z` `HUMAN_TURN`（本 shard 全篇 `HUMAN_TURN` 皆不帶 `Message`／`Details`，此為既有格式慣例，非本次特例——與 iteration 2 finding 自己指出的既有觀察一致）。
   - `02:57:11Z` `QUESTION_ANSWERED`，`Details`：「M1-M3 重新確認：三項照舊 M1=B／M2=A／M3=A（可驗證授權，即時寫入）」——27 秒後緊跟在 `HUMAN_TURN` 之後，符合本站要求的「`HUMAN_TURN` 緊接 `QUESTION_ANSWERED`」形狀，量級與 iteration 2 finding 引用的真實作答範例（Q1：10 秒內）同階，非異常。

   `01:15:34Z` 到 `02:56:44Z` 之間約 1 小時 41 分鐘的間隔（session 暫停／重新接續）不構成疑點——`DECISION_RECORDED` 記的是「決定要重問」的意圖，不是「已經問到」的宣稱；真正的問答發生在間隔之後，時序內部自洽。

**2. 時間戳與 `date -u` 及檔案 mtime 三方比對，逐秒吻合。**
   本站獨立執行 `date -u`（結果 `2026-08-24T02:58:xx` 起，審查期間持續前進，與後續 `SUBAGENT_COMPLETED` 事件時間帶一致）與 `stat`（`TZ=UTC` 強制轉換，避免重蹈 iteration 2 finding 未踩、但本站仍主動排除的本地時區陷阱）：

   | 檔案 | mtime（UTC，`stat` 實測） |
   | --- | --- |
   | `user-stories-questions.md` | `2026-08-24T02:57:11Z` |

   與 `QUESTION_ANSWERED` 事件時間戳 `02:57:11Z` **逐秒相同**；檔內行內註記 `2026-08-24T02:57:10Z（讀自 date -u，即時寫入）` 與之相差僅 1 秒（檔案寫入與 audit 事件寫入為連續兩個動作，落差量級合理，不構成疑點）。三方（audit 事件／磁碟 mtime／檔內自報時間）在 1 秒誤差內互相印證，與 iteration 2 finding 抓到的「`02:10:00Z` 比磁碟寫入晚 66 分鐘、比審查當下真實時鐘晚約 1 小時」的物理不可能狀態形成鮮明對比——這次的時間戳確實讀自時鐘，不是編造。

**3. 全檔 grep 確認無殘留的偽造時間戳作為現行主張。**
   對 `00:40:00Z`／`00:44:00Z`／`00:48:00Z`／`02:10:00Z` 四個舊偽造值做全檔 grep：

   - `user-stories-questions.md:167` 命中一次——但這是**更正聲明本身在指名這四個值曾被編造**（「本檔先前所有 `[Answer]:` 的時間戳……**都是我編造的**」），是揭露用途而非現行主張。
   - `stories.md:463` 命中一次——是本站 iteration 2 finding 自己的鑑識引用，本次已隨整份 `## Review` 區塊被取代，不再殘留於更新後的檔案。
   - `personas.md`、audit shard 內**皆無命中**。

   M1／M2／M3 三題的 `[Answer]:` 行本身也不再宣稱知道原始作答時刻，改寫為誠實的「作答時刻未記錄；本行補記於……可驗證性待『M1–M3 重新確認』段」——這正是 iteration 2 finding 要求的處置方向（不得用一段時間線把「未經授權」偽裝成「已授權」），而不是在原地加固原本的敘事。

**4. 揭露文字的誠實性——讀起來是承認，不是辯護。**
   `user-stories-questions.md:167` 的更正聲明逐句核對：「都是我編造的，不是讀時鐘取得」「`02:10:00Z` 甚至晚於當時的真實時間，是一個尚未發生的時刻」「reviewer iteration 2……判定成立」——三句話直接承認偽造、承認物理不可能、承認 reviewer 的判定正確，沒有「流程疏失」「格式問題」一類淡化用語，也沒有把責任分散給協定或工具。`M1–M3 重新確認` 段的「本站的判斷」進一步把「底層事實為真」與「可驗證性已被破壞」拆開陳述，並明講「正確做法不是堅持既有說法，而是當場重新取得一次可驗證的裁決」——六個月後的讀者看這段文字，得到的印象會是「這裡曾經造假，已被抓到並老實承認、重新取證」，不會被誤導成「這只是流程瑕疵」。判定：**誠實揭露，非防禦性最小化**。

### iteration 1 findings 2–6 的回歸檢查

本輪 lead 只動了 `user-stories-questions.md`（新增更正聲明與重新確認段），`stories.md`／`personas.md` 兩檔在本輪**未被修改**（`stories.md` 現存內容與 iteration 2 審查時逐字相同，唯 `## Review` 區塊由本次取代）。以下針對 findings 2–6 涉及的內容重新獨立機械核對，確認未被本輪改動波及：

- **Finding 2（S-9 AC 5 標籤）**：`stories.md:267` 核對，AC 5 仍標 `[新增：M2=A]`，不帶 `[req:NFR-O2]`；NFR-O2 仍由 AC 1–3 承載。**維持 Resolved。**
- **Finding 3（denominator 歸屬更正）**：`stories.md:259` 的「歸屬更正」段落文字未變。**維持 Resolved。**
- **Finding 4（依賴表 S-2 → S-7）**：`stories.md:329` 一列仍明列「S-7 的對帳要先用 S-2 的映射判定……」說明。**維持 Resolved。**
- **Finding 5（`personas.md` P3 漏列 S-4）**：`personas.md:50` P3「主要相關故事」欄核對為「S-1、S-2、S-3、S-4、S-5」，含 S-4。**維持 Resolved。**
- **Finding 6（依賴表 S-7→S-4 與 S-9→S-4）**：`stories.md:324-325` 兩列的說明文字（「S-4 AC 5 的兩半來源不同」「與上一列並存，非擇一」）核對未變。**維持 Resolved。**

另重跑本站 iteration 2 已建立的兩項全域機械檢查，確認本輪未引入新迴歸：

- **65 條 AC 計數**：以腳本重新逐則計數 `^\d+\.\s+\*\*Given\*\*`，S-1～S-11 為 7/15/6/6/3/7/5/3/6/5/2，加總 65，與總覽表（`stories.md:33-43`）完全一致。
- **`[req:*]` 雙向覆蓋**：`requirements.md` canonical `FR-*`／`NFR-*` 以 `grep`＋`comm` 重新獨立抽取，共 40＋15＝55 條；`stories.md` 內 AC 級 `[req:FR-*]`／`[req:NFR-*]` 標籤集合覆蓋其中 47 條，未直接標於 AC 的 8 條（`NFR-C2`／`NFR-M1`／`NFR-P2`／`NFR-P4`／`NFR-S2`／`NFR-S3`／`NFR-S4`／`NFR-S5`）逐一核對確實列於 `stories.md:356-377`「全域 Definition of Done」表（`NFR-P2`／`P4` 合併為一列）並附分流理由；無孤兒需求，亦無指向不存在編號的野標籤。

### 本輪新發現

無新增的 Critical 或 Major。以下一項為核對過程中發現、經追查後判定不構成問題的細節，記錄供留痕：

- `user-stories-questions.md:229` 的更正段稱偽造時間戳「晚於當時真實時間 **56** 分鐘」，與本站 iteration 2 finding（`stories.md` 已取代的舊 `## Review`）所寫的「**66** 分鐘」（相對磁碟 mtime `01:03:44Z`）不同。核對後確認兩者是**對不同基準點的合法換算**：iteration 2 finding 以磁碟實際寫入時間（`01:03:44Z`）為基準（差 66 分鐘）；本輪更正段以 iteration 2 判定完成的時間（`01:13:50Z`，見 audit `HUMAN_TURN`）為基準，`02:10:00 − 01:13:50 ≈ 56 分 10 秒`，換算成立。兩個數字在各自檔案內部均無自我矛盾，且都指向同一個實質結論（該時間戳確實晚於真實時間、確實不可能），不影響本輪判定，記錄為 Minor／非阻擋觀察，不需修正。

### Attempted refutations that did not hold

- **嘗試主張「`HUMAN_TURN`（`02:56:44Z`）到 `QUESTION_ANSWERED`（`02:57:11Z`）間隔 27 秒，比 iteration 2 finding 引用的 Q1 範例（10 秒內）長，可能仍是可疑訊號**——查核後駁回：27 秒與 10 秒同屬「人工即時作答＋當場寫回」的合理量級（三項判斷題逐項覆誦確認比單選題多打幾個字），且與**編造時間戳**的特徵（跨小時的落差、物理上尚未發生）性質完全不同；不構成疑點。
- **嘗試主張 `DECISION_RECORDED`（`01:15:34Z`）宣稱「當場重新取得」但實際問答發生在 1 小時 41 分鐘之後，構成新的時序矛盾**——查核後駁回：`DECISION_RECORDED` 記載的是**決定**（要重新確認），不是**完成**的宣告，其 `Decision` 欄文字本身沒有承諾具體時限；間隔對應的是 session 暫停與重新接續，這是 harness 常見的正常運作型態，不是本輪處置引入的新問題。
- **嘗試在 `stories.md` Revision 1 段（行 433：「三項判斷題依 stage-protocol §5 於階段中途交付人工裁決，結果 M1=B、M2=A、M3=A」）尋找是否應同步改寫以反映更正與重新確認的過程**——查核後駁回：該句陳述的是裁決的**結果**（mob round 1 triage 確實產出了 B／A／A，此為更正聲明本身也承認的「底層事實為真」），不是裁決的**可驗證性**；後者的權威記錄本就落在 `user-stories-questions.md`（本專案 stage 產出與其問題檔分工的既有慣例），`stories.md` 的 Revision changelog 不需要重寫來承載一份已經誠實記載在別處的更正過程。

### Summary

Iteration 2 的唯一 Critical——M1/M2/M3 的人工授權可驗證性——已透過重新取得的即時裁決徹底解決：audit shard 的 `HUMAN_TURN`→`QUESTION_ANSWERED` 序列、檔案 mtime、`date -u` 三方在秒級精度上互相印證；四個舊偽造時間戳僅以「揭露曾被編造」的形式出現，不再作為任何現行主張；更正聲明本身讀起來是不加修飾的承認而非辯護。iteration 1 findings 2–6 經獨立重新核對，五項全部維持 Resolved，本輪未觸及的 `stories.md`／`personas.md` 內容亦無回歸。65 條 AC 計數與 40＋15 條需求雙向覆蓋兩項全域機械檢查重跑成立。判定 **READY**——可交付 Application Design。

