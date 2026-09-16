# Stage Memory — Build and Test

> 本 stage 執行期間的觀察日誌。四個標準 H2，新條目 append 到既有標題下。

## Interpretations

- 2026-08-18T03:00:00Z — `produces` 宣告七份檔案，但 stage 檔 Step 4-8 對 **Minimal** 策略
  明示「generate ONLY `unit-test-instructions.md`，Skip all other test types」。兩者不衝突：
  `produces` 是**可能**產出的集合，策略決定實際子集。故產出四份
  （`build-instructions`／`unit-test-instructions`／`build-and-test-summary`／`build-test-results`），
  三份跳過並在 summary 逐項寫明理由 —— **跳過必須附理由，不能只是不寫**。
- 2026-08-18T03:00:30Z — `produces` 清單寫 `build-test-results.md`，stage prose 的 Step 10 寫
  `test-results.md`。以 `produces` 為準（`project.md` 有既有 correction：
  「produces 清單是 artifact 集合的正式來源」）。
- 2026-08-18T03:01:00Z — devsecops 是 support agent，本應提供安全測試輸入，但 Minimal 策略
  跳過 `security-test-instructions.md`。解讀為：**跳過的是「產出獨立的安全測試指示檔」，
  不是「跳過安全評估」**。ADR-0006 的四面向判定表因此寫進 `build-and-test-summary.md`，
  形式依 `project.md` 的既有 correction（缺一不可型 hard constraint 以逐項判定表呈現，
  不適用項也要附理由、不留空白）。

## Deviations

- 2026-08-18T03:01:30Z — consumes 收到的是**字面**的
  `construction/{unit-name}/code-generation/code-summary.md`（placeholder 未展開），
  手動解析為 `construction/production-path-check/`。這是上一站 reviewer 已預警的引擎缺口
  （`emitRunStageForSlug` 一律傳 `UNIT_NAME_PLACEHOLDER`，`splitConsumesByPresence`
  見到 placeholder 就跳過存在性檢查），**預警準確命中**。已在 `build-instructions.md`
  加註記，讓讀 artifact 的人不會照著字面路徑去找不存在的檔案。

## Tradeoffs

- 2026-08-18T03:02:00Z — 沒有為 NFR-3 建立獨立的效能測試基礎設施，改為在單元執行中
  直接量測（10 次取平均）。受測函式執行約 15 毫秒、門檻是 1 秒 —— 為 1/60 門檻的函式
  搭效能測試框架，成本遠高於收益。代價是沒有防迴歸的自動化效能斷言；
  接受此代價是因為若有人把全域掃描改成 O(n²)，先失敗的會是既有的正確性測試而非效能。
- 2026-08-18T03:02:30Z — 只跑三個 CI job，`docker-build` 留給 CI。代價是本機沒驗證
  image 建得起來。接受依據：本次變更不觸及 Dockerfile 或建置上下文
  （變更清單為 1 支 Python 腳本、1 支測試、3 份 markdown）。
  **但在 `build-test-results.md` 明列為「未執行項」而非併入通過清單** ——
  沒跑就是沒跑，不能讓讀者以為四個 job 全綠。

## Open questions

- 2026-08-18T03:03:00Z — `team.md` `## Code Style` 記的 `WorkspacePage.tsx:279` 實測已漂移到
  `301`（檔案與規則相同，只有行號過期）。本次未觸及前端，且該段落受 practices-discovery
  gate 治理，故不修改。這是**第三次**在這個 record 裡遇到「規則層文件的行號引用過期」
  （前兩次：`team.md` 的 `validate_repo_contract.py:347`、`:330`）。
  行號引用作為一種慣例本身可能就是錯的 —— 值得下一輪 practices-discovery 考慮
  改為只引函式名／段落名。
- 2026-08-18T03:03:30Z — 本 repo 無覆蓋率量測機制，故 `org.md` 宣告的 80% line coverage
  在本 stage 無法驗證。如實記載於 summary，不假裝有量。承接自 `team.md` 的既有記載，
  非本 stage 新增的問題。
