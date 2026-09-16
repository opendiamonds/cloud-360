# Phase Check — Construction → Operation

**執行時間**：2026-09-06T06:35Z 前後（`date -u`）
**執行方式**：機械計數與集合比對（腳本 ＋ `gh api`），非人工目視。每一項下方註明抽取方式，讓下一個人可獨立複驗。

## 檢查結果總覽

| # | 檢查項 | 結果 | 抽取方式 |
| --- | --- | --- | --- |
| ① | 每個單元都有 code-generation 產出 | **✅ 12/12**（`code-generation-plan.md` ＋ `code-summary.md` 各 12 份） | 對 `unit-of-work.md` 的 `### U-` 標題集合逐一檢查檔案存在 |
| ② | 每個單元都有 reviewer 終判 receipt | **✅ 12/12，全部由 `aidlc-architecture-reviewer-agent` 判** | 解析 audit shard 的 `REVIEW_COMPLETED` 區塊，取每單元最後一筆 |
| ③ | 終判為 READY | **⚠️ 11/12**——`U-6-forward-workflow` 終判 **NOT-READY**（輪次用罄，人工裁決收掉） | 同 ② |
| ④ | 設計 → 程式：每個單元都有實體交付物 | **✅ 12/12，23 條路徑全部存在** | 單元 → 交付物路徑對照表逐一 `Path.exists()` |
| ⑤ | 程式 → 測試：離線套件在 CI 執行 | **✅ 14/14**（本 stage 之前 10/14） | 對 `.github/workflows/` 逐支 `grep -rl` 並**開檔區分 `run:` 與註解**，再展開 `run-selftest-fixtures.py` 的 `UPSTREAM_DRIVERS` |
| ⑥ | 測試實跑 | **✅ 16 組全部 rc=0**：312 tests／**1844** checks ＋ 3257 條 fixture 斷言 ＋ 86 項檢查器項目，0 失敗，牆鐘 7 m 5 s | 本 stage 改動後整套重跑（不是沿用 `build-test-results.md` 的數字，見 ⑥ 的說明） |
| ⑦ | 既有系統回歸 | **✅** backend 247 tests OK；frontend lint 0 errors／`tsc -b`／build 全綠 | 同上 |
| ⑧ | CI pipeline configured | **✅** | `ci-config.md`、`quality-gates.md` |
| ⑨ | Infrastructure designed | **N/A** | scope 明列 `3.4 infrastructure-design` 為 SKIP；本 intent 不建任何基礎設施，交付物全部跑在 GitHub 託管的 runner 上 |
| ⑩ | live／端到端層實跑 | **❌ 零執行** | 見下方 |

## 逐項說明

### ③ U-6 的 NOT-READY 終判

`U-6-forward-workflow` 的 reviewer 在 iteration 2 判 NOT-READY，`reviewer_max_iterations`
為 2 ⇒ 輪次用罄。依 stage-protocol §12a「READY 或輪次用盡即 proceed」，且 lead 於派工前
訂定的停止判準（`application-design:c4`）條件成立時由**人工裁決收掉**，理由、雙方依據與
「哪些部分只經過 lead 自己驗證」全部寫在 U-6 的 `code-summary.md` 最末節。

**這一項不是檢查失敗，但它也不是通過。** 列在這裡是為了讓它跨過 phase 邊界時不被讀成
「12/12 全 READY」。

### ⑤ 「在 CI 執行」的判定為什麼要開檔

`grep -rl` 的命中不等於執行：三支 `-impl.yml` 與 `ci.yml` 對測試腳本的**全部**命中都是
註解。只看 `grep -rl` 會得到「12 支在 CI」的錯誤結論，實際（本 stage 之前）是 10 支。

本 stage 之後的分佈：第一段的 8 個直接 step ＋ `run-selftest-fixtures.py` 轉呼的 6 支
上游驅動 ＝ 14 支，無重複。

### ⑥ 本 stage 改動後的重跑

ci-pipeline 的四項變更（四支套件進 CI、`schedule` 觸發、`COMPILER:` 斷言、以及它逼出的
五處連帶改動）之後**整套重跑**，而不是沿用 build-and-test 的數字。變動的計數有四處，
**每一處都能指出原因**：

| 套件 | 變動 | 原因 |
| --- | --- | --- |
| `run-selftest-tests.py` | 89→**91 tests**、368→**385 checks** | 新增兩條 `COMPILER:` 的行為測試 |
| `check-paths-relations.py` | 17→**21 項** | 四支承載體各一條 `COMPILER:` |
| `run-reconcile-tests.py` | 210→**211 checks** | `test_r5_cron_does_not_collide` 逐支重掃 `.github/workflows/*.yml` 的 cron，本 stage 給 selftest 加了 `47 5 * * 3` ⇒ 多一次比對 |
| `run-reverse-tests.py` | 308→**309 checks** | 同上（`test_cron_does_not_collide_with_any_existing_schedule`） |

最後兩列是意料之外但正確的：**那兩支的既有守衛主動驗了本 stage 新加的 cron 不與任何
既有排程同分同時**，並且通過。本 intent 的 checks 總數因此由 1842 變為 **1844**。

### ⑨ Infrastructure designed 判為 N/A 的理由

不是「跳過所以不管」：本 intent 的交付物是 composite action、workflow YAML 與 shell／
python 腳本，**全部跑在 GitHub 託管的 runner 上，沒有任何自建基礎設施**。唯一的外部
狀態是 GitHub 自己的 Projects／Issues／repo。`3.4 infrastructure-design` 在 scope 定案時
即為 SKIP，與本判定一致。

### ⑩ live 層零執行——這是跨越邊界時最要緊的一項

| 未執行的部分 | 它會做什麼 |
| --- | --- |
| 5 支 `run-live-tests.py` | 寫測試看板 #23、改 issue #538 的 body、推一次性分支、在正式 repo 建真 issue |
| `aidlc-sync-selftest.yml` 第二段 | 同上，且會觸發 `issue-triage`（gh-aw／LLM 路徑） |
| 真實 CI 觸發（PR／push） | 本 stage 的**全部** CI 變更都只有本機證據 |
| NFR-P1 的 5 分鐘延遲量測 | 量測落點是 U-7 的 `latency_samples`，只在真實排程執行時產生 |

**「離線層 16 組全綠」與「這套機制可以啟用」是兩件事。** 前者已成立，後者的前提
（憑證鑄造、看板欄位命名、required check 的套用）都還在 gate 上。

## 帶進 Operation 的未結項目

這些全部通過上述機械檢查，但它們是**已標出而尚未關閉**的事實：

| # | 項目 | 落點 | 風險 |
| --- | --- | --- | --- |
| 1 | `AIDLC_SYNC_TOKEN` 不在 secrets 也不在 variables | Bolt 0 gate | **一個缺席的 secret 不是一道閘門**——它是目前唯一擋著正向 workflow 寫正式看板 #16 的東西 |
| 2 | `Sync write-back gate` 尚未設為 required check（指令已備妥） | 人工執行 | 在那之前，`[aidlc-sync]` 跳過四道關卡後合併不會被擋 |
| 3 | 直接推送到 `ut` 不被任何東西擋（`enforce_admins: false`、無 push restrictions、憑證為 admin） | Bolt 1 gate | required check 只在 PR 路徑上生效 |
| 4 | `COMPILER:` 斷言只涵蓋四支承載體，另 7 支 gh-aw 同樣暴露 | Bolt gate | 那 7 支不是 U-10b 的交付物 |
| 5 | `COMPILED:` 偵測不到一般性的 lock 過期（`types`／`permissions`／`engine`／`tools`／`network` 或 prompt 本文） | 已登錄缺口 | 本 stage 的 `COMPILER:` 補的是「誰編的」不是「編得夠不夠新」 |
| 6 | `deploy.yml` 對反向 PR 無 `paths` 過濾（實測 `on.pull_request` 為 `{types: [closed], branches: [ut]}`） | gate | 反向 PR 合併會觸發自架 runner 上 30 分鐘逾時的完整部署 |
| 7 | README 看板連結匿名 404（#16 為 `public: false`、repo 為 `public`） | 產品決定 | — |
| 8 | U-6 的 concurrency 與對帳共用一組，與 U-8 nfr 的裁定相反 | Bolt 3 gate | `open-items.md` N:C-2 的處置逐字為「需 ADR 或回退」，ADR 至今未開 |
| 9 | `team.md` 的前端 lint 基準（3 warnings）已過期，本輪實測 2 | 下一輪 practices-discovery | — |

## 判定

**Construction → Operation 邊界檢查：有條件通過。**

八項機械檢查（①②④⑤⑥⑦⑧）全綠，⑨ 判為 N/A 並附理由。**③ 與 ⑩ 不判為通過**：
一個單元帶著 NOT-READY 終判跨界，而 live 層一次未跑。九項未結事項各有落點，其中第 1、2、3
項合起來決定「這套機制什麼時候可以真的開始寫正式看板」——那是 Bolt 0／1 gate 的內容，
不是本檢查能代答的。

**不把它寫成「通過」的理由**：Operation 階段在本 scope 全部 SKIP，所以這份檢查是本 intent
對 Construction 成果的最後一次機械盤點。把「有一個單元 NOT-READY、live 層零執行」寫成
通過，等於讓下一個讀它的人以為那兩件事已經被處理過。
