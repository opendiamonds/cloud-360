<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-09-06T05:50:38Z — 本階段的「build」沒有編譯產物，故把 Step 3 的 build-instructions 改讀成「三件實際存在的建置動作」：執行環境（python3＋PyYAML＋bash 3.2 底線）、gh-aw `.lock.yml` 重編（只在改四支 gh-aw `.md` 時）、既有 frontend／backend 建置（本 intent 未觸及其原始碼，跑它是 brownfield 的 Test Validation 而非產物）。把「沒有 build」寫成一句話而不列出這三件，會讓下一個人以為這一格是空的。
- 2026-09-06T05:50:38Z — Test Strategy 為 Standard（「每元件 5〜8 條」），實測規模遠高於此（310 tests／1825 checks ＋ 3257 條 fixture 斷言）。判定為**刻意超標而非誤解等級**：受測對象是 shell 與 YAML，沒有型別系統，錯誤只能靠斷言擋；`testing-guide.md` 逐字允許 context demands 時超出。
- 2026-09-06T05:50:38Z — directive 的 `produces` 列了七份（含 performance／security 兩份），而 stage 檔的 Standard 分支只要求 unit＋integration 兩份。以 directive 的 `produces` 為準並全數產出，理由有二：(1) 12 個單元中有 5 個實際產出了 `performance-requirements.md`、12 個全部產出了 `security-requirements.md`，stage 檔的「IF NFR requirements exist」條件成立；(2) ADR-0006 是 hard constraint，安全面不能因策略等級而不寫。

<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-06T05:50:38Z — **未執行任何 live 測試層**（5 支 `run-live-tests.py` 與 `aidlc-sync-selftest.yml` 第二段）。它們會對真實 GitHub 寫入：測試看板 #23 的 Status／欄位、issue #538 的 body、一次性分支的 push、以及**在正式 repo 建立真 issue**（後者還會觸發 `issue-triage` 這條 gh-aw／LLM 路徑）。stage 檔 Step 10 要求「attempt to execute」，但對外部系統的寫入需要一次明確的人工授權，且各單元的交還清單都已把它綁在同一個 Bolt 0 gate（憑證鑄造）。改為在 `integration-test-instructions.md` 寫出完整指令、退出碼語意與三層防呆，讓授權當下可以直接跑。
- 2026-09-06T05:50:38Z — Step 10 的「On failure 嘗試修復」未觸發：16 組離線套件與 2 支合約驗證器**全部 rc=0**，backend 回歸 247 tests OK。沒有可修的東西，故未進入該分支。

<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

- 2026-09-06T05:57:10Z — 在 `produces` 之外改了一支程式：`scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]` 加入 `"Requirements Source"` 與看板 URL 兩條。起因是逐單元覆蓋盤點時發現 **U-11 的交付物零自動化覆蓋**——刪掉整段 README 不會讓任何檢查變紅（九條既有字串沒有一條涵蓋它；全 repo 另外三處 `("opendiamonds", "projects/16")` 字面檢查斷言的是 workflow 檔）。選擇「做」而非「登錄給 gate」的判準是三項同時成立：零風險（字串已存在，加入當下即通過）、二元可判、且正是本 intent 已重複四次的失效形狀。已突變驗證（刪段→rc=1 且訊息指名兩條缺失字串；還原→rc=0；README 的 `git diff --stat` 仍為 5 insertions）。改完重跑三支檢查器與兩支驗證器，全數 rc=0。

- 2026-09-06T06:00:00Z — `performance-test-instructions.md` 的 P-T1 第一版寫「三個 `group` 值互不相同」，是照 U-8 `performance-requirements.md` 缺口 P-2 的裁定寫的、**沒有先讀實作**。實跑 `yaml.safe_load` 才發現反向與對帳**共用同一組**，且 `aidlc-sync-reverse.yml:39-71` 有三個更強的理由（`open-items.md` N:C-2 把 P-2 判為 Critical、處置為「需 ADR 或回退」而 ADR 從未開出；`services.md:58` 是正確性論證而 P-2 是便利性論證；已核可計畫的查證 1 沒把 N:C-2 呈現給人看）。P-T3 同型：第一版寫「每支 workflow 都要有 `timeout-minutes`」，實測三支薄外層零命中——而零命中是正確的（該鍵只存在於 job／step 層，薄外層的 job 是 `uses:` 呼叫）。兩處都已改寫並跨檔傳播（`build-and-test-summary.md` 的 U-8 列與待決清單第 9 項）。這正是 `application-design:c8`（出選項前先實測既有結構）要防的形狀，本輪在寫進 artifact 之前接住。

- 2026-09-06T06:05:42Z — §13 儀式：9 項候選依「跨 stage 可複用」收斂為 4 項呈示（c6 零覆蓋時做 vs 登錄的判準、c7 寫驗證判準前先讀實作、c9 安全宣稱拿去實地查證、c4 對外部寫入的測試改寫成可直接跑的指令），排除的 5 項為本 stage 機制性的解讀（c1／c2／c3）、非事件（c5）與次要取捨（c8）。與 code-generation 那一輪相同的偏離：協定要求選項 `label` 逐字用候選 `summary`，但 summary 皆數百字，故 label 用短標題、`description` 承載全文。人工結果：四項全部未勾選，補充題答「沒有要補充的」，`persist` 回 `rule_learned:0`。

## Tradeoffs
- 2026-09-06T05:50:38Z — 前端回歸選擇「跑」而非「以 `check-ci-yml.py` 的 NFR-C1 斷言代替」。後者其實是更強的證據（它逐字比對四個 job 的 `name`／`runs-on`／`steps` 未變，19 項全綠），而本 intent 對 `frontend/` 零改動 ⇒ 建置結果在機制上不可能被影響。仍然跑的理由是 brownfield 的 Test Validation 要的是**執行後的實測**而不是推論；代價是一次 `npm ci` 的網路與時間。
- 2026-09-06T05:50:38Z — 安全面選擇「把上游宣稱拿去對真實 GitHub 查證」而非重抄各單元的四面向判定表。以 `gh api` 實跑四項（secrets／variables 名稱、repo visibility、`ut` 與 `main` 的 branch protection），結果證實了三項既有登錄並使其中一項的嚴重度**上修**：`ut` 的 `required_status_checks` 為 `null` ⇒ `[aidlc-sync]` 跳過四個 job 之後，合併不會被任何東西擋。代價是這份 artifact 與上游有部分重疊。

<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-06T05:50:38Z — **`AIDLC_SYNC_TOKEN` 目前不存在於 secrets 也不存在於 variables**（本階段以 `gh api` 兩邊各查一次複驗）。這是正向 workflow 目前唯一擋著不對正式看板 #16 寫入的東西——**一個缺席的 secret 不是一道閘門**。啟用時機、欄位名（#16 尚無 `AI-DLC Stage` 欄位而 `write_field` 會自動建立）必須由 gate 一併決定。
- 2026-09-06T05:50:38Z — 我在 code-generation 的核可摘要裡把工作樹的 5 個 `__pycache__` 目錄列為「要進 `.gitignore`」的待辦。**該項不成立**：`.gitignore:30` 早已有 `__pycache__/`，`git status --untracked-files=all .github/actions` 對 pycache 的命中數為 **0**。教訓與 `delivery-planning:dp-L1` 同型——可以用一條指令查證的事實，不要憑印象寫進要交給人做決定的摘要裡。
- 2026-09-06T05:50:38Z — `run-stub-tests.py:891`／`:921` 有兩個合成的假 GitHub token 字面值（用來測遮罩邏輯本身）。它們落在一個 **public** repo；GitHub 自身的 secret scanning 會驗證有效性所以不會告警，但外部的 naive 掃描器會命中。已知並接受，記錄以免下一輪重查。
- 2026-09-06T05:50:38Z — 本階段對 `.lock.yml` 的重編**沒有實跑**（沒有改動四支 gh-aw 的 `.md`，所以沒有觸發條件）。`build-instructions.md` 的 B-2 全部指令與版本警告來自 U-10b `code-summary.md` 的實測轉錄，**不是本階段的觀測值**。要在 Bolt 階段真的改那四支時才會第一次被執行。

<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
