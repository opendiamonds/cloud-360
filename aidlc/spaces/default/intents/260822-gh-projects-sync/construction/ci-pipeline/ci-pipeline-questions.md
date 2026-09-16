# CI Pipeline — 澄清問題

<!-- Stage: ci-pipeline（Construction）· 本檔為本 stage 的問答正式來源 -->

## 前言：哪些不重問

stage 檔的範例題有四項，其中三項**已由上游定案，不重問**，理由逐條可引用：

| 範例題 | 已定案處 | 定案內容 |
| --- | --- | --- |
| 用哪個 CI 工具？ | `project.md ## Tech Stack` 逐字「CI/CD：GitHub Actions（`.github/workflows/ci.yml`…；`deploy.yml` 在 `ut` 觸發部署）」 | GitHub Actions |
| branch 策略？ | `org.md ## Way of Working` 逐字「trunk-based development with `ut` as the integration trunk」＋ `team.md ## Way of Working` 的 `<uploader>/<type>/<slug>` 命名與「一般 PR 用 merge commit、Construction Bolt 用 squash」 | trunk-based，trunk 是 `ut` |
| artifact repository？ | 本 intent **無 artifact 產出**（交付物是 bash／python／YAML，由 runner 直接執行，見 `build-instructions.md`） | 不適用 |

第四項（「merge 之前需要哪些 quality gate」）**是真的未定案**，且 build-and-test 的實測讓它變成三個具體的選擇——Q1〜Q3。Q4 是本 stage 查證時新發現的。

## 本 stage 查證出的事實（供題幹引用，非「來源」登錄）

以 `grep -rl` 對 `.github/workflows/` 逐支比對後（並區分**真正的 `run:` 呼叫**與**註解提及**——三支 impl workflow 與 `ci.yml` 對測試腳本的命中全是註解）：

**14 支離線套件中，10 支會在 CI 執行**，全部經由 `aidlc-sync-selftest.yml` 第一段：

- 直接 step：`check-agentic-steps.py`、`check-paths-relations.py`、`run-selftest-fixtures.py`、`run-selftest-tests.py`
- 經 `run-selftest-fixtures.py` 轉呼：`map/run-fixtures`、`block/run-fixtures`、`forward/run-orchestration-tests`、`reverse/run-reverse-tests`、`ci-guard/check-ci-yml`、`ci-guard/run-probe-tests`

**4 支從未被任何 workflow 執行**：

| 套件 | 擁有單元 | 規模 | 本機耗時 |
| --- | --- | --- | --- |
| `aidlc-sync-board/run-stub-tests.py` | U-3 | 31 tests／173 checks | 16.90 s |
| `aidlc-sync-record/run-stub-tests.py` | U-4 | 31 tests／231 checks | 24.00 s |
| `aidlc-sync-notify/run-stub-tests.py` | U-5 | 35 tests／381 checks | 17.08 s |
| `aidlc-sync-reconcile/run-reconcile-tests.py` | U-7 | 38 tests／210 checks | 48.84 s |
| **合計** | | **135 tests／995 checks** | **106.82 s** |

> 規模與耗時逐欄取自 `build-test-results.md` 的 A 表（本機實測值），不是估計。
>
> **提問當下的觀測值，不回改**：本 stage 的變更之後 reconcile 為 211 checks（它的
> `test_r5_cron_does_not_collide` 逐支重掃 workflow 的 cron，而本 stage 給 selftest 加了
> 一個）。最終值見 `verification/phase-check-construction.md` 的 ⑥。

> **一項對已核可上游的更正（對齊，非本站新定案）**：`build-and-test-summary.md` 的待決
> 清單第 3 項寫「U-10a 兩支守衛未接進任何 workflow」。**該敘述已過期**——U-9 的
> reviewer iteration 2（M-4）與 iteration 3（F7）已把 `check-ci-yml.py` 與
> `run-probe-tests.py` 接進 `run-selftest-fixtures.py` 的 `UPSTREAM_DRIVERS`，本輪實跑
> 輸出可見 `UPSTREAM:aidlc-sync-ci-guard/check-ci-yml` 與 `…/run-probe-tests` 兩行。
> 過期的來源是 U-10a 自己的 `code-summary.md`（寫於被接上之前，之後未回頭更新），
> build-and-test 沿用了它而沒有回查。**依 `project.md` 不回改已核可的上游 artifact**，
> 更正記於此處與 `ci-config.md`。

`aidlc-sync-selftest.yml` 的觸發是 `pull_request` ＋ 15 條 path allowlist ＋ `workflow_dispatch`，**沒有 `push` 觸發**。`ci.yml` 的觸發是 `pull_request`（無 paths）＋ `push` 到 `main`／`ut`／`danniel/**`／`chore/**`。

---

## Q1：四支從未在 CI 執行的離線套件（135 tests／995 checks）要接到哪裡？

- **A. 併進 `aidlc-sync-selftest.yml` 第一段**（沿用既有 allowlist 觸發與 `if: always()` 形狀）。成本：該 workflow +106.82 s。缺點：只在觸及同步機制的 PR 上跑。
- **B. 在 `ci.yml` 新增一個獨立 job**。每個 PR 都跑，不受 allowlist 限制。缺點：在完全無關的 PR 上也多花約 107 s，且會受 `gate` job 的 `[aidlc-sync]` skip 影響。
- **C. 新開一支獨立 workflow**（同一份 allowlist）。與 selftest 分離、失敗訊息歸屬更清楚。缺點：多一支要維護的 workflow，且 allowlist 變成兩份要同步。
- **D. 維持現狀**，只在 Bolt gate 手動跑。

`[Answer]`: A — 併進 `aidlc-sync-selftest.yml` 第一段（沿用既有 allowlist 與 `if: always()` 形狀，+106.82 s）  <!-- answered 2026-09-06T06:16:09Z -->

## Q2：`[aidlc-sync]` 標記跳過四道關卡之後，合併不會被任何東西擋——怎麼處置？

實測事實：`ut` 的 `required_status_checks` 為 `null`、`enforce_admins: false`；`main` 唯一的
required check 是 `Repository contract`，而 GitHub 官方文件逐字「Successful check statuses are
success, **skipped**, and neutral」。

- **A. 讓 `gate` job 本身成為 required check**。它一律執行、永遠不會 skip，所以「整輪被跳過」時仍有一個真的跑過的 check 存在，且它的 log 會寫出判定理由。其餘四個維持可 skip。
- **B. 在 `ut` 設 required status checks（四個 job）**。缺點：`skipped` 視同通過，**擋不住這條路**——設了會給人「已經有防護」的錯覺。
- **C. 縮小 skip 範圍**：`[aidlc-sync]` 只跳過 `frontend`／`backend`／`docker-build`，`repo-contract` 一律執行。缺點：同步 commit 只動一個 JSON 檔，跑 repo-contract 的邊際價值低，但成本也低（0.27 s 級）。
- **D. 不處置**，把風險登錄在 gate 清單，由人審 PR 把關。

`[Answer]`: A — 讓 `gate` job 本身成為 required check（它一律執行、不會 skip，log 寫出判定理由）；其餘四個維持可 skip  <!-- answered 2026-09-06T06:16:09Z -->

## Q3：`aidlc-sync-selftest.yml` 目前沒有 `push` 觸發，要加嗎？

U-9 的 `performance-requirements.md` 逐字記載這支 workflow 的常態是**不執行**，並自陳
「這是刻意的，也是它的弱點——一支很少跑的閘門，壞掉時不會立刻被發現」。

- **A. 不加**。每個觸及同步機制的 PR 都會跑到；push 到 `ut` 是同一批 commit，重跑無新資訊。
- **B. 加 `push: branches: [ut]`（同 allowlist）**。合併後再驗一次，擋得住「PR 綠燈但合併時被別的 PR 影響」。
- **C. 加 `schedule` 每週一次**（`workflow_dispatch` 已有）。專門對付「很少跑的閘門壞掉沒人發現」。
- **D. B ＋ C 都加。**

`[Answer]`: C — 加 `schedule` 每週一次（`workflow_dispatch` 已有），專門對付「很少跑的閘門壞掉沒人發現」  <!-- answered 2026-09-06T06:16:09Z -->

## Q4：`COMPILED:` 只驗 glob 不驗 `compiler_version`，要在本 stage 補上嗎？

U-10b 的 `code-summary.md` 逐字：「**沒有任何機械檢查會擋下「用較新版本重編」**——
`COMPILED:` 只驗那一條 glob，不驗 `compiler_version`」。用本機預設的 v0.86.2 重編會夾帶
六項未經 ADR-0006 審查的供應鏈變更（`actions/cache` v5.0.5→v6.1.0 等）。

- **A. 補**：在 `check-paths-relations.py` 加一條斷言——四支 `.lock.yml` 的 `compiler_version` 必須都等於 `v0.81.6`。零新依賴、二元可判，且該檔已在 CI 執行。
- **B. 不補**，登錄給 Bolt gate 一併處置（升級 gh-aw 是獨立決策，可能連帶改這個值）。
- **C. 補但只發 `::warning::`**，不讓它紅燈。

`[Answer]`: A — 補：在 `check-paths-relations.py` 斷言四支 `.lock.yml` 的 `compiler_version` 都等於 `v0.81.6`  <!-- answered 2026-09-06T06:16:09Z -->
