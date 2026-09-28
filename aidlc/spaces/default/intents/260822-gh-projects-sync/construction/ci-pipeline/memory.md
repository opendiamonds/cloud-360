<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-09-06T06:31:29Z — 加完四個 step 與 `COMPILER:` 斷言後重跑，`run-selftest-tests.py` **紅了 5 條**，逐條追出來分屬三個不同原因，全部是本輪改動的直接後果而非既有缺陷：(1) 絆線 `test_the_real_repo_state_is_what_we_say_it_is` 的期望集合少了四個 `COMPILER:` 代號——**這正是它被設計來做的事**（U-10b 交付時它也紅過一次）；(2) `test_every_check_step_after_the_first_runs_unconditionally` 把四個新 step 歸成 setup；(3) `check-agentic-steps.py` 判 `check-paths-relations.py` 出現被禁字樣。三者都不是「改測試讓它變綠」可以了事的，各自的修法見 Deviations。

- 2026-09-06T06:23:36Z — CONDITIONAL 適用性逐項對照 condition 三個條款（needs creation／needs significant modification／already adequate）後判定**執行**：U-10a 已對 `ci.yml` 加 `gate` job 與四個 job 的 `if:`，且 build-and-test 查出 135 tests／995 checks 從未在 CI 執行 ⇒ 第二、三款成立。依 `project.md` 的 `feasibility:c1`，判定理由記入 diary 而非憑 feature 表面大小直覺。
- 2026-09-06T06:23:36Z — stage 檔的四道範例題有三道已由上游定案，逐條可引用故不重問：CI 工具（`project.md ## Tech Stack` 逐字「CI/CD：GitHub Actions」）、branch 策略（`org.md ## Way of Working` 逐字 trunk-based with `ut`）、artifact repository（本 intent 無 artifact 產出）。依 `scope-definition:260822-c5`——宣稱「已定案」必須能引用具體原文，引用不出來就代表未定案。
- 2026-09-06T06:23:36Z — 「哪些套件在 CI 執行」的判定方式選**逐支開檔區分 `run:` 與註解**，而不是 `grep -rl` 的命中即算。這一步是必要的：三支 `-impl.yml` 與 `ci.yml` 對測試腳本的全部命中都是註解，只看 `grep -rl` 會得到「12 支在 CI」的錯誤結論（實際是 10 支）。

<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

- 2026-09-06T06:39:19Z — 最終確認跑：16 組全部 rc=0（312 tests／1844 checks ＋ 3257 條 fixture 斷言 ＋ 86 項檢查器項目，牆鐘 7 m 5 s）。**有兩個計數變動不是我改出來的**：`run-reconcile-tests.py` 210→211、`run-reverse-tests.py` 308→309。追出來是這兩支的 `test_*cron*collide` 逐支重掃 `.github/workflows/*.yml` 的 cron，而本 stage 給 selftest 加了 `47 5 * * 3` ⇒ 各多一次比對，且都通過——**它們主動驗了我選的 cron 不與任何既有排程同分同時**。依 `delivery-planning:dp-L1`（可算的數字先算再寫），沒有把這 +2 當成雜訊帶過，而是查到原因才寫進 phase-check。

- 2026-09-06T06:40:55Z — §13 儀式：14 項候選依「跨 stage 可複用」收斂為 4 項呈示（c4「在 CI 執行」要開檔確認、c8 新增閘門就要新增它自己的行為測試、c7+P-T1「寫驗證判準前先讀實作」、c6 分類判準不得以路徑前綴界定），排除的 10 項為本 stage 機制性的解讀（c1／c2／c3）、單一決定的取捨（c9／c10／c12／c13／c14）與觀察（c11）。與前兩輪相同的偏離：協定要求選項 `label` 逐字用候選 `summary`，但 summary 皆數百字，故 label 用短標題、`description` 承載全文。人工結果：四項全部未勾選，補充題答「沒有要補充的」，`persist` 回 `rule_learned:0`。

## Deviations
- 2026-09-06T06:31:29Z — **`_GH_AW_METADATA_PREFIX = "# gh-aw-metadata: "` 這個字面值讓 `check-agentic-steps.py` 紅了**——`gh-aw` 是 `agentic-tokens.json` 的被禁字樣，而 `check-paths-relations.py` 自己在 R-1.2 的掃描面上。修法走**既有的具名查表機制**（`agentic-tokens.json` 的 `named` 表，原本就是為了讓 `run-selftest-tests.py` 能構造違規樹而不寫字面值）：新增 `lock_metadata_prefix`，並以 `agent_action_repo` 的尾段衍生出工具名供訊息使用。**沒有把字串拆開寫**（`"gh" + "-aw"`）——那正是該檢查宣告擋不住、而在自己的程式裡示範會讓「這是規避手法」失去說服力的做法，`agentic-tokens.json` 的 `_named_readme` 逐字寫過這一點。
- 2026-09-06T06:31:29Z — `test_every_check_step_after_the_first_runs_unconditionally` 的 `checkers` 判準是 `"aidlc-sync-selftest/" in s["run"]`——**以位置界定**。四個新 step 跑的是 `aidlc-sync-board/…` 等路徑，於是被歸成 setup，而 setup 的斷言是「不得帶 `always()`」⇒ 四條全紅，紅的理由與它們實際做的事無關。改為以**角色**界定：`re.search(r"\.github/actions/aidlc-sync-[a-z0-9-]+/\S+\.py", s["run"])`。**這是本 intent 第三次同型**（U-9 的 R-1.2 掃描面兩次），教訓仍是那句：位置型邊界每一輪都會有下一格。
- 2026-09-06T06:31:29Z — 合成樹的 lock 沒有 metadata 首行，於是 `COMPILER:` 的 fail-closed 路徑在每一棵合成樹上都紅。修法是**讓合成 lock 產生真實形狀的首行**（`synth_carriers` 加 `lock_compiler` 參數），不是讓檢查在讀不到時放行——後者會讓「把首行刪掉」變成繞過這道檢查最省事的方法。`SYNTH_LOCK_COMPILER` **刻意寫死 `v0.81.6` 而不從 `PINNED_COMPILER_VERSION` 推導**：推導的話兩邊會一起漂移而 baseline 照樣綠，與 `EXPECTED_CARRIERS` 是同一條紀律。
- 2026-09-06T06:31:29Z — 新增兩條測試把 `COMPILER:` 這道新閘門自己納入迴歸：`test_a_lock_compiled_by_another_compiler_version_is_red`（含對照組）與 `test_a_lock_without_metadata_is_red_not_a_vacuous_pass`。**新增一道閘門而不同時新增它自己的行為測試，就是本 intent 已重複四次的「看起來在守、實際沒在守」的下一個實例。** 套件由 89 tests／368 checks 增為 **91 tests／385 checks**。

- 2026-09-06T06:23:36Z — **Q2=A 的程式面做完、repo 設定面未執行**。把 `Sync write-back gate` 設為 required check 是 repo 設定變更，會立即影響所有人的合併路徑，且 `ut` 的 `required_status_checks` 只能經整包 `PUT` 設定——payload 少寫一欄就會清掉其他保護設定。處置：以 `gh api` 讀出 `ut` 的完整 protection 物件，據以寫出逐欄對應現值的 payload 放進 `quality-gates.md`，執行留給人工確認。這是「決定已定、執行需確認」的分法，不是把決定退回去。
- 2026-09-06T06:23:36Z — Step 6 的 phase boundary verification 依 `stage-protocol-governance.md` §13 寫入 `verification/phase-check-construction.md`，但**判定為「有條件通過」而非通過**：Construction→Operation 的三項檢查中「All units built and tested」只在離線層成立，live 層一次未跑。把它寫成通過會讓下游把未驗證當成已驗證。

<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-09-06T06:31:29Z — 五條紅燈之中，只有絆線那一條是「更新期望值」；另外四條都改的是**受測物或測試的判準**。這個比例本身是訊號：若五條都只需要更新期望值，代表這些測試沒有在守任何東西。

- 2026-09-06T06:23:36Z — 四支套件放 `aidlc-sync-selftest.yml` 第一段而非 `ci.yml` 新 job（Q1 的 A vs B）：決定性的理由不是成本，是 **`ci.yml` 的新 job 會被 `gate` 的 `[aidlc-sync]` skip 影響**——同步 commit 反而跳過這四支。而第一段的 allowlist 已涵蓋 `.github/actions/aidlc-sync-*/**`，那正是這四支與其受測物唯一能被改動的路徑。代價：只在觸及同步機制的 PR 上跑。
- 2026-09-06T06:23:36Z — 排程執行的 checkout 釘 `ut` 而非用 default branch：實測 default branch 是 `main`，而同步機制的整合主幹是 `ut`（`org.md`），每個 Bolt 合併到它、deploy-on-merge 掛在它上面。表達式寫成 `github.event_name == 'schedule' && 'ut' || github.ref`，使既有兩個事件的行為**逐字不變**（`github.ref` 對 `pull_request` 就是 `refs/pull/<n>/merge`，即 checkout 的預設值）。代價：`ut` 這個名字被硬編碼在 workflow 裡。
- 2026-09-06T06:23:36Z — `COMPILER:` 斷言的範圍限於四支承載體而非全部 11 支 gh-aw：另外 7 支目前同樣是 v0.81.6、同樣暴露在「用較新版本重編會夾帶六項未審查供應鏈變更」的風險上，但它們不是 U-10b 的交付物。擴大是獨立決定，登錄給 gate。**寫下這一句是因為「四支全綠」很容易被讀成「這個風險已經處理掉了」。**

<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-06T06:31:29Z — `COMPILED:` 仍然**偵測不到一般性的 lock 過期**（改 `types`／`permissions`／`engine`／`tools`／`network` 或 prompt 本文而不重編）。本輪新增的 `COMPILER:` 補的是「誰編的」，不是「編得夠不夠新」。這是 `run-selftest-tests.py` 絆線註解裡已登錄的缺口，本輪未動。

- 2026-09-06T06:23:36Z — **本 stage 的所有 CI 變更都沒有在真實 runner 上跑過**（新增的四個 step、`schedule` 觸發、`COMPILER:` 斷言在 CI 上的行為）。需要推送才會觸發。它與 U-9 交還清單第 5 項（PyYAML 在 runner 上是否可用）落在同一個未驗證面：本 stage 讓 14 支套件「在 CI 上執行」，而**這句話本身尚未被 CI 驗證過**。
- 2026-09-06T06:23:36Z — Q2=A 的處置讓「被跳過」這件事**看得見**，但沒有讓它**被阻止**，且完全不涵蓋「直接推送到 `ut`」——`ut` 的 `enforce_admins` 為 `false`、無 push restrictions、同步憑證為 admin。兩者都登錄給 Bolt 1 gate。
- 2026-09-06T06:23:36Z — `build-and-test-summary.md` 的待決第 3 項（U-10a 兩支守衛未接進任何 workflow）**已過期**，過期來源是 U-10a 自己的 `code-summary.md`（寫於被 U-9 的 F7 接上之前，之後未回頭更新）。依 `project.md` 不回改已核可上游，更正記在本 stage 的 `ci-config.md` 與問題檔。這是「成因與後果分屬不同單元」的第 N 次，但方向與前幾次相反——這次是**修好了而文件沒跟上**，而不是壞了沒人發現。

<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
