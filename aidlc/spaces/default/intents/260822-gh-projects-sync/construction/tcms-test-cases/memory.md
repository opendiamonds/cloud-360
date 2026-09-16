<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-09-06T07:03:56Z — 分桶時把 live 層的 5 支 `run-live-tests.py` 判為「**已自動化**」而非「只能手動」：腳本存在且斷言的就是那些行為，重寫一份手動案例會製造第二個真實來源。但在盤點表加一欄「在 CI 跑過嗎」，並逐字寫明**那一欄問的是「會不會被 workflow 執行」，不是「在真實 runner 上跑過一次了嗎」**——後者對本 intent 全部是否。不加這一欄，「已自動化 12 項」會被讀成執行證據。
- 2026-09-06T07:03:56Z — [US:S-10 AC 5]（憑證做範圍外寫入回 403）判為**未分類**而非手動：ADR-0016 確認 `opendiamonds` 是個人帳號、寫入身分改為擁有者 token 後 `repo` scope 整包涵蓋三類寫入 ⇒ 沒有一種宣告範圍內的操作會回 403，**該 Given 走不到**。依撰寫標準「判不出來的不要預設丟給手動」，寫成手動案例會產出一個永遠無法執行的案例。
- 2026-09-06T07:03:56Z — 案例 5（README 連結匿名可開）**明寫「本案例目前預期為失敗」**。這不是寫壞的案例，是把一個已實測的未關閉缺口放在一個會定期紅的落點上，而不是只寫在報告的一行裡。語意審查的第 5 點（通過條件二元可判）標 ⚠️ 並附理由，不是漏寫。

<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

- 2026-09-06T07:15:33Z — 最終確認跑（本 stage 全部改動之後）：16 組全部 rc=0——**314 tests／1851 checks ＋ 3257 條 fixture 斷言 ＋ 87 項檢查器項目，0 失敗，牆鐘 6 m 44 s**。相對 ci-pipeline 收尾時的增量全部可指出來源：`run-selftest-tests.py` 91→93 tests／385→392 checks（`PR-TRIGGER-1` 的兩條行為測試）、`check-paths-relations.py` 21→22 項（`PR-TRIGGER-1` 本身）。
- 2026-09-06T07:15:33Z — §13 儀式：8 項候選收斂為 4 項呈示（c4 機械層擋住合理案例時改契約而非填假值、c5 斷言紅了先分 fixture 不完整與 repo 違規、c3 預期為紅的案例是認真的交付物、c1 分桶表要區分「會被執行」與「跑過一次了」），排除的 4 項為本 stage 的單一判定（c2、c6、c7、c8）。與前三輪相同的偏離：協定要求選項 `label` 逐字用候選 `summary`，但 summary 皆數百字，故 label 用短標題、`description` 承載全文。人工結果：四項全部未勾選，補充題答「沒有要補充的」，`persist` 回 `rule_learned:0`。

## Deviations
- 2026-09-06T07:03:56Z — **擴充格式契約而不是繞過機械層**（人工裁決 Q1=A）。本 intent 的交付物完全不在 web app 內，五個案例逐案撞上「受測介面沒有列出任何 API 端點或 UI 路徑」。填一個假端點可以讓機械層過關——那正是 `project.md` 的 `tcms-test-cases:c20` 逐字禁止的形狀。改為在 `TESTING.md` 與 `tcms_validate.py` 新增第三種行別 `- Workflow:`，比對 `.github/` 下檔案存在**且**宣告的事件真的在該檔的 `on:` 裡，「三者皆無」維持 ERROR。順帶修掉一個既有的靜默面：`TRACE_PATH` 原本不認 `.github/`，指向 workflow 的追溯**會被靜默忽略**（寫一個不存在的路徑也不會紅）。
- 2026-09-06T07:03:56Z — 待自動化的 B-1 逼出兩處合成樹修正，都是**補完 fixture 而非放寬檢查**：合成樹原本沒有 `deploy.yml`（釘住的集合含它 ⇒ 基準線會以「少掉的」那一側紅）、合成的 `aidlc-sync-forward.yml` 只宣告 `workflow_dispatch`（真實的是 `on: pull_request` 無 paths）。`SYNTH_LOCK_COMPILER` 與 `REVERSE_PR_TRIGGERS` 都刻意寫死、不從受測物推導——推導的話兩邊會一起漂移而 baseline 照樣綠。
- 2026-09-06T07:03:56Z — **`tcms-api` 未安裝 ⇒ 手動案例未寫入 TCMS**。`~/.tcms.conf` 存在，缺的是客戶端套件；性質與「設定檔不存在」相同，故依 `project.md ## Mandated` 記為未完成項並在 gate 說明，**不靜默跳過**。安裝套件是使用者環境的變更，未逕自執行，併入 gate 裁決。

<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

- 2026-09-06T07:17:28Z — gate 裁決為「安裝 `tcms-api` 並實際同步」，已執行：`pip install --user tcms-api` → dry-run 預覽（連得上 TCMS 之後才看得到「將建立 plan」那幾行）→ 實際寫入。結果：TestPlan `AI-DLC ↔ GitHub Projects 同步（手動）` id=26、案例 id 40〜44，新增 5 筆、更新 0 筆。`tcms-sync-report.md` 的「結果：未寫入」節已改寫為實際結果，未完成項第 1 條標為已關閉。**先 dry-run 再寫入的兩步沒有省**——工具以標題 upsert，預覽是確認「這一輪不會建出重複案例」的唯一機會。

## Tradeoffs
- 2026-09-06T07:03:56Z — `PR-TRIGGER-1` 的釘住清單含 `deploy.yml`（Q2=A）而非只釘 PR 開啟側：`deploy.yml` 的 `types: [closed]` 意謂反向 PR **合併**時觸發自架 runner 上 30 分鐘的完整部署，為的是一個 JSON 欄位。要不要加 paths 過濾涉及 ADR-0008 的部署模型，是 gate 的決定——但**在它被決定之前，這條斷言至少讓它可見**，而不是留在某份報告的一行裡。代價是這條斷言現在把一個已知的壞形狀寫成「預期值」，讀的人必須讀到那三行理由才知道它不是背書。
- 2026-09-06T07:03:56Z — `tcms_validate.py` 的 `DEFAULT_MANUAL` 硬編碼指向前一個 intent，`--all` 因此驗的是別人的檔案。**未逕自改**：改成解析 `active-intent` 會改變前一個 intent 的覆蓋範圍，屬獨立決定。本輪改以 `--file` 明確指定並登錄該落差。

<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-06T07:03:56Z — **本 intent 交付的 312 tests／1844 checks 在 TCMS 上完全不可見。** `test-case-management-plan.md` 的分工假設自動化案例經 junit plugin 進入 TCMS，該假設對 Playwright 成立、對本 intent 的 Python 檢查器層不成立（不產生 junit XML）。要不要讓這一層也回寫是獨立決定，登錄給 gate。
- 2026-09-06T07:03:56Z — 案例 1〜4 的前置條件都依賴「憑證已鑄造」（Bolt 0 gate）。在那之前，五個手動案例中**只有案例 5 現在就能執行**——而它預期為紅。這代表本 stage 交付的手動層在 Bolt 0 之前實際可執行的比例是 1/5，這一點應在 gate 上被看見，不要被「五個案例已就緒」蓋過去。

<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
