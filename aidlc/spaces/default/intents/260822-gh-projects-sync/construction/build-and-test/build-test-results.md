# Build and Test Results — 實測輸出

<!-- Stage: build-and-test（Construction）· 本檔的每一個數字都是本輪實跑的觀測值，非轉錄 -->

## 執行環境（本輪）

| 項目 | 值 |
| --- | --- |
| 時間 | 2026-09-06T05:40Z 〜 05:50Z（`date -u`） |
| commit | `9307dbc` ＋ 未 commit 的工作樹（本 intent 的 33 項變更） |
| 主機 | macOS 26.5.1 / arm64 |
| python3 | 3.13.7；PyYAML 6.0.3 |
| bash | GNU bash 3.2.57(1)-release |
| node / npm | v25.2.1 / 11.19.1 |
| gh / gh aw | 2.96.0 / v0.86.2（**未用於重編**——本輪無 gh-aw `.md` 改動） |

## A. 離線測試層 — 16 組，全數 rc=0

| # | 套件 | rc | 耗時 | 結果（腳本自己印的最後一行） |
| --- | --- | --- | --- | --- |
| 1 | `aidlc-sync-block/run-fixtures.py` | 0 | 3.50 s | 斷言數 **550**、失敗 0（round-trip 432 組組合） |
| 2 | `aidlc-sync-map/run-fixtures.py` | 0 | 16.99 s | 斷言數 **2707**、失敗 0（totality 2592 組窮舉） |
| 3 | `aidlc-sync-board/run-stub-tests.py` | 0 | 16.90 s | **31 tests, 173 checks, 0 failures** |
| 4 | `aidlc-sync-record/run-stub-tests.py` | 0 | 24.00 s | **31 tests, 231 checks, 0 failures** |
| 5 | `aidlc-sync-notify/run-stub-tests.py` | 0 | 17.08 s | **35 tests, 381 checks, 0 failures** |
| 6 | `aidlc-sync-forward/run-orchestration-tests.py` | 0 | 49.95 s | **40 tests, 154 checks, 0 failures** |
| 7 | `aidlc-sync-reconcile/run-reconcile-tests.py` | 0 | 48.84 s | **38 tests, 210 checks, 0 failures** |
| 8 | `aidlc-sync-reverse/run-reverse-tests.py` | 0 | 67.93 s | **46 tests, 308 checks, 0 failures** |
| 9 | `aidlc-sync-ci-guard/run-probe-tests.py` | 0 | 1.69 s | **13 項行為測試，0 失敗** |
| 10 | `aidlc-sync-ci-guard/check-ci-yml.py` | 0 | 0.12 s | **19 項檢查，0 失敗** |
| 11 | `aidlc-sync-selftest/run-selftest-tests.py` | 0 | 45.06 s | **89 tests, 368 checks, 0 failures** |
| 12 | `aidlc-sync-selftest/run-selftest-fixtures.py` | 0 | **142.52 s** | 第一段 fixture 驅動：**25 項檢查，0 失敗** |
| 13 | `aidlc-sync-selftest/check-agentic-steps.py` | 0 | 0.61 s | R-1.2 靜態檢查：**8 項檢查，0 失敗** |
| 14 | `aidlc-sync-selftest/check-paths-relations.py` | 0 | 0.93 s | A-6 路徑集合關係：**17 項檢查，0 失敗** |
| 15 | `scripts/validate_repo_contract.py` | 0 | 0.27 s | `Cloud-360 repository contract validation passed.` |
| 16 | `scripts/validate_env_contract.py` | 0 | 0.08 s | `Cloud-360 environment configuration contract validation passed.` |

### 合計（實算，非估計）

| 量 | 值 | 怎麼算的 |
| --- | --- | --- |
| 套件數 | **16** | 上表列數 |
| 失敗數 | **0** | 每支腳本自印的失敗欄相加 |
| tests | **310** | 第 3〜8、11 列的 tests 欄相加（31+31+35+40+38+46+89） |
| checks | **1825** | 同上七列的 checks 欄相加（173+231+381+154+210+308+368） |
| fixture 斷言 | **3257** | 第 1、2 列（550+2707） |
| 檢查器項目 | **82** | 第 9、10、12、13、14 列（13+19+25+8+17） |
| 牆鐘總時 | **436.47 s ＝ 7 m 16 s** | 上表耗時欄相加 |

> 上表的 tests／checks 三種計數口徑**不能相加成一個總數**——`tests`／`checks` 是行為
> 測試的兩層計數，`斷言數` 是 fixture runner 的單層計數，`項檢查` 是檢查器的單層計數。
> 硬湊一個「總測試數」會是一個沒有意義的數字。

### 一項與上游對不上的耗時（本輪觀測，非錯誤）

`run-selftest-fixtures.py` 本輪 **142.52 s**，U-9 `code-summary.md` 記載 **92.78 s**。
兩者量的是同一件事（第一段連同六支上游驅動）。差距的可能來源是機器負載——本輪 16 組
套件連續跑、期間另有 backend 回歸並行。**沒有進一步追查**：U-9 已把「10 分鐘上界是估計
值、須在 Bolt 4 首次真實執行後複核」登錄為交還項，142 s 仍遠低於該上界，本輪不改變那個
判斷。記在這裡是為了讓 Bolt 4 複核時知道曾觀測到接近 1.5 倍的浮動。

## B. 既有系統回歸（brownfield Test Validation）

本 intent 對 `backend/` 與 `frontend/` 的原始碼**零改動**（`git status` 未列出任何一個
檔案）。以下是「改動後仍然綠」的實測，不是本 intent 的產物。

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| backend import smoke | `python3 -c "import main"` | rc=0 |
| backend unittest | `python3 -m unittest discover -s tests` | **Ran 247 tests in 22.207 s — OK** |
| frontend lint | `npm run lint` | rc=0，**0 errors, 2 warnings** |
| frontend typecheck | `npx tsc -b` | rc=0 |
| frontend build | `npm run build` | rc=0，`✓ built in 1.64s` |

### 前端 lint 基準與 `team.md` 記載不符（本輪觀測）

`team.md ## Code Style` 記載「現況為 0 errors, 3 warnings（`AssessmentPage.tsx:365`、
`LoginPage.tsx:36`、`WorkspacePage.tsx:279`）」。**本輪實測是 2 warnings**：

- `AssessmentPage.tsx:365` — 仍在
- `WorkspacePage.tsx:**302**` — 行號已從 `:279` 移動
- `LoginPage.tsx:36` — **已不存在**

與本 intent 無關（前端零改動），是 `team.md` 的基準值在後續 PR 之後未回頭複驗。
`reverse-engineering:260822-re-c2` 已記載「codekb 內每一項事實都必須標明取得方式與證據
強度」，本項是它的又一個實例。**不逕自改 `team.md`**（那是 practices-discovery 的產出），
登錄給下一輪 practices-discovery。

## C. 安全查證（本輪以 `gh api` 實跑，非轉錄）

| 查證 | 結果 |
| --- | --- |
| repo secrets 名稱 | 11 個；**`AIDLC_SYNC_TOKEN` 不在其中** |
| repo variables 名稱 | `APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`；**同步憑證不在其中** |
| repo visibility | **`public`** |
| `ut` branch protection | `required_status_checks: **null**`、`enforce_admins: false` |
| `main` branch protection | 唯一 check 為 `Repository contract`、`enforce_admins: true` |
| 硬編碼憑證掃描（97 檔） | 2 處命中，**兩處都是刻意的合成假 token**（`aidlc-sync-notify/run-stub-tests.py:891`、`:921`，用來測遮罩邏輯本身） |

**第 4 列是本階段最要緊的查證結果**：`ut` 上沒有任何 required status check，所以
U-10a 的 `[aidlc-sync]` 標記讓四個 job 全部 skip 之後，**合併不會被任何東西擋**——而
`ut` 正是每個 Bolt 的合併目標，deploy-on-merge 掛在它上面。這比 U-4 `security-requirements.md`
SEC-2 原本登錄的「標記可被任何有推送權的人使用」更進一步。指派 Bolt 1 gate。

## D. 未執行的部分（明列，不是「跑過但沒問題」）

| 項目 | 為什麼沒跑 |
| --- | --- |
| 5 支 `run-live-tests.py` | 會對真實 GitHub 寫入（看板 #23、issue #538、一次性分支、正式 repo 的真 issue）。需要一次明確的人工授權，已綁在 Bolt 0 gate（憑證鑄造） |
| `aidlc-sync-selftest.yml` 第二段 | 同上，且會觸發 `issue-triage`（gh-aw／LLM 路徑） |
| gh-aw `.lock.yml` 重編 | **無觸發條件**——本輪未改動四支 gh-aw 的 `.md`。`build-instructions.md` 的 B-2 是 U-10b 實測的轉錄，不是本輪觀測值 |
| 真實 CI 觸發（PR／push） | 需要推送。「CI 紅燈」這條完成判準只能在那時被驗證 |
| NFR-P1 的 5 分鐘延遲量測 | 量測落點是 U-7 的 `latency_samples`，只在真實排程執行時產生 |
| SAST／依賴 CVE 掃描 | 見 `security-test-instructions.md` 的「本階段沒有做的」 |

## E. Step 10 的「On failure」分支

**未觸發**。16 組離線套件、2 支合約驗證器、backend 247 tests、frontend 三道全部 rc=0，
沒有可診斷或修復的失敗。

## 與上游的對應

受測對象與擁有單元的對照引自各單元的 `code-generation-plan.md` 與 `code-summary.md`；
`run-selftest-fixtures.py` 的 92.78 s 基準與 10 分鐘上界引自 U-9 的 `code-summary.md` 與
`performance-requirements.md`；`[aidlc-sync]` 標記的風險面引自 U-4 SEC-2 與 U-10a SEC-1；
前端 lint 基準引自 `team.md ## Code Style`。
