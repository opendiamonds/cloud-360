# Code Generation 問題檔 — `U14 entry-page-ui`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（15 步，含其內嵌的 Testing Contract，`test-after`、`standard`）、`unit-test-instructions.md`，以及隨計畫一併核可的 `adr-0022-draft.md`（核可後於 Step 1 原樣移入 `inception/decisions/0022-work-target-names-and-brain-read-visibility.md`）。明白揭露（逐條對應計畫 §七）：

- **交付規模**：後端應用 7 檔（含產生檔 1）、後端測試 9 檔（新 2、改 7）、前端 31 檔（新 23、改 7、產生檔 1）、e2e 4 檔（新 2、改 2）、`deploy.yml` 與 `DEPLOY.md`；零 DDL、零新環境變數、零 secret、零新依賴、零 HTTP 端點變更。
- **測試量**：後端新增 47 案；e2e 攔截層 49 案、真實 stack 層 5 案；既有 15 個 e2e 改落點斷言（其中 1 個改名，Kiwi 舊案例成孤兒，由 `tcms-test-cases` 人工停用）。
- **帶入項**：`carried-review-items.md` 的 26 項全數處置，0 項拒絕（22 項改程式並配測試、4 項只做紀錄或文件）。
- **可見性批次化的讀法**（ADR D-5）：`list_projects` 固定 3 條 SQL；目錄的可見性成本固定 ＋1，但 `_build_catalog` 總數仍是 3 ＋ 3N（`U13` 既有成本），若要總數也是常數需另改，本計畫未納入。此改動也改變 `U19`／`U23` 的 `project_visibility` 閉包（語意不變、改為每實例查一次）。
- **nfr-design R-03 的 M2 改承接**：改以等價突變 V1 承接，原 M2 仍由 `U23` 的測試承擔。
- **重開已交付單元**：`U2`、`U7`、`U13`、`U19`／`U23`；既有斷言只補參數不改期望，唯一例外是 `test_brain_gateway_startup.py:60` 的 lambda 簽章。
- **`deploy.yml` 多一道擋部署的步驟 6a**（`[EPI1]`=A）：影響全部單元的部署；失敗會回滾整個 intent；Cloudflare 一時異常可能誤回滾（12 輪重試緩解）。
- **偏離 `BR92.5` 字面**：4403 不導航，改為至多一次 `refreshMe()`。
- **合併前檢查與使用者必做**：`U13` 與 `U14` 必須同一次合併；合併前由使用者確認 `OPENROUTER_API_KEY` 在 Actions secrets 而不在 variables。
- **`ui-regression` 時間預算未量測**：新增 54 案，逾 15 分鐘時 `ui-regression` 會紅（訊號、不擋合併）。
- **殘留**：見計畫 §七 第 13 點（移出前已設好的作業對象不追溯清除、名稱陳舊、孤兒圖、`bearer.` 項只能人工實測等）。
- **本輪環境修復**：原本 `.kilo/worktrees/secret-deposit`（外來 git worktree）使原始碼無法綁定；已由使用者於 2026-10-17 以 `git worktree move` 搬到 chiton 之外，之後重算指紋，計畫內容未改。

## Plan Approval

[Approval Fingerprint]: sha256:v3:35dbfd7f8d0e3233e14da5bf6b95cf02e290bb0f757cc828140e1411c8a9992d
[Planned Source]: 859d0d244124503dc19e12e1e705dbc418e3342196b46425439bbf87ca718deb
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan
