# Build and Test Summary — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· 實測明細見 build-test-results.md -->

## 一句話結論

**離線層完全就緒（16 組套件、0 失敗），live 層一次都沒跑過，而 live 層正是本機制唯一
會真的動到看板的那一半。** 這句話的兩半都要被讀到——只讀前半會把「測試全綠」誤讀成
「機制可以啟用」。

## 建置狀態

| 項目 | 狀態 | 依據 |
| --- | --- | --- |
| 執行環境 | ✅ 就緒 | python3 3.13.7 ＋ PyYAML 6.0.3 ＋ bash 3.2.57；五支 `.sh` 的檔頭逐字宣告 bash 3.2 為底線 |
| 編譯產物 | — 不適用 | 交付物是 bash／python／YAML，由 runner 直接執行 |
| gh-aw `.lock.yml` | — 本輪無觸發條件 | 未改動四支 gh-aw 的 `.md`。**重編必須用釘住的 v0.81.6**，本機預設是 v0.86.2 |
| 既有 frontend 建置 | ✅ 通過 | `npm run lint` 0 errors / 2 warnings、`tsc -b` rc=0、`npm run build` rc=0 |
| 既有 backend | ✅ 通過 | import smoke rc=0；`unittest` **247 tests OK** |

前置條件的完整清單在 `build-instructions.md`。唯一未驗證的前置是
**PyYAML 在 GitHub runner 上是否可用**——U-9 交還清單第 5 項，只有真實 CI 觸發才有答案。

## 測試型別盤點

| 型別 | 產出檔 | 本輪執行 | 規模 |
| --- | --- | --- | --- |
| 單元／離線（stub、fixture、行為） | `unit-test-instructions.md` | ✅ **全部執行** | 16 組、310 tests／1825 checks、3257 條 fixture 斷言、82 項檢查器項目、0 失敗、7 m 16 s |
| 整合（live，對真實 GitHub） | `integration-test-instructions.md` | ❌ **未執行** | 5 支 runner ＋ selftest 第二段 |
| 效能 | `performance-test-instructions.md` | ⚠️ 部分（建置期四項可判；量測面不可行） | NFR-P1 的量測落點在 U-7 的 `latency_samples`，只在真實排程時產生 |
| 安全 | `security-test-instructions.md` | ✅ 靜態面執行，並以 `gh api` 實地查證四項 | SAST／DAST／CVE 掃描不適用或未引入，理由逐條寫在該檔 |

## 逐單元覆蓋（本輪實測，非引用）

| 單元 | 離線覆蓋 | live／CI 覆蓋 | 明知的缺口 |
| --- | --- | --- | --- |
| U-1 map | 2707 斷言（2592 組窮舉 totality） | — | 無 |
| U-2 block | 550 斷言（432 組 round-trip） | — | 無 |
| U-3 board | 31 tests／173 checks | ❌ 完成判準 (a)〜(g) 全未驗 | R-1.4 多筆**設計上**只在 stub 驗（無可構造的 live 反例）；R-2.4 競態視窗**零覆蓋** |
| U-4 record | 31 tests／231 checks | ❌ 完成判準 (a)〜(d) 全未驗 | `main` 半邊的 GH006 只有 stub，且**刻意不補**（補它要對 `main` 發真實 push） |
| U-5 notify | 35 tests／381 checks | ❌「連續兩輪」判準未驗 | issue 列舉是最終一致的（本 intent 實測），該判準隱含「兩輪間隔 > 該視窗」 |
| U-6 forward | 40 tests／154 checks | ❌ L1〜L3 未驗 | R-5.4 雜湊等價性是 ADR-0015 §10 點名最危險的失敗模式，**只有 live 驗得到** |
| U-7 reconcile | 38 tests／210 checks | ❌ `latency_samples` 未產生過 | NFR-P1 目前**沒有任何量測機制**，是一條無法證偽的宣稱 |
| U-8 reverse | 46 tests／308 checks（含一條靜態斷言鎖住 concurrency 值） | ❌ | **實作與對帳共用同一組**，刻意反著做 U-8 nfr 階段「自成第三組」的裁定（`open-items.md` N:C-2 判該裁定為 Critical，處置為「需 ADR 或回退」而 ADR 從未開出）。待 Bolt 3 gate 開 ADR 或確認回退 |
| U-9 selftest | 89 tests／368 checks ＋ 25 fixture 檢查 ＋ 8 ＋ 17 檢查器項 | ❌ **第二段從未執行過** | 完成判準③（範圍外寫入回 403）在組織層授權下**不可達** |
| U-10a ci-guard | 13 項行為測試 ＋ 19 項文字檢查 | ❌ 真實 `[aidlc-sync]` push 未試 | **兩支守衛都沒接進任何 workflow**，要靠人記得手動跑 |
| U-10b gh-aw 排除 | `check-paths-relations.py` 的 12 項（4 承載體 × 3） | lock 可重現性已在**真實 repo** 上證明（逐位元） | `COMPILED:` 驗 glob 不驗 `compiler_version` ⇒ 擋不住有人用較新的 gh-aw 重編 |
| U-11 README | **本階段之前：零** → 現為 repo contract 的 2 條字串斷言 | — | 見下節 |

### 本階段對 U-11 的修補（唯一一處程式改動）

U-11 的交付物是 README 的「Requirements Source」段——本 intent 對外唯一的「需求正本在
哪」宣告。查證結果：**刪掉整段不會讓任何檢查變紅**。`REQUIRED_TEXT["README.md"]` 的九條
字串沒有一條涵蓋它，全 repo 也沒有其他斷言（三處 `("opendiamonds", "projects/16")` 字面
檢查斷言的是 workflow 檔，不是 README）。

處置：在 `scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]` 加入
`"Requirements Source"` 與看板 URL 兩條，並**突變驗證**：

| 步驟 | 結果 |
| --- | --- |
| 加入斷言後跑驗證器 | `passed`，rc=0 |
| 刪掉整個 Requirements Source 段後重跑 | `ERROR: … missing 'Requirements Source'; … missing 'https://github.com/users/opendiamonds/projects/16'`，**rc=1** |
| 還原 README 後重跑 | `passed`，rc=0；`git diff --stat README.md` 仍為 `1 file changed, 5 insertions(+)` |

這是本階段唯一一處 `produces` 之外的程式改動。做而不只是登錄的理由：它是**零風險**
（字串已存在，加入當下即通過）、**二元可判**，而且正是本 intent 已重複四次的失效形狀
——規則寫在文件上、看起來已經在守，實際上沒有東西在守。

## 就緒度評估

| 面向 | 判定 | 理由 |
| --- | --- | --- |
| **Build-ready** | ✅ 是 | 無編譯步驟；環境依賴明確且本機全數滿足 |
| **Test-ready（離線）** | ✅ 是 | 16 組全綠，可在任何一台有 python3＋PyYAML 的機器上重跑 |
| **Test-ready（整合／live）** | ⛔ 阻擋 | 需要憑證鑄造與一次明確的人工授權，已綁在 Bolt 0 gate |
| **CI-ready** | ⚠️ 部分 | 離線層可以接進 CI，但 U-10a 的兩支守衛目前**不在任何 workflow 內**；接法是下一個 stage（ci-pipeline）的工作 |
| **Deployment-ready** | ⛔ 否 | 見下方待決清單；`AIDLC_SYNC_TOKEN` 不存在是目前唯一擋著它對正式看板 #16 寫入的東西 |

## 待決清單（交還 gate，本階段不自行處置）

| # | 項目 | 本階段的新增證據 | 落點 |
| --- | --- | --- | --- |
| 1 | `AIDLC_SYNC_TOKEN` **不在 secrets 也不在 variables**（本輪 `gh api` 兩邊各查一次） | 一個缺席的 secret 不是一道閘門 | Bolt 0 gate（連同 #16 的 `AI-DLC Stage` 欄位名） |
| 2 | `[aidlc-sync]` 標記跳過四個 job 之後**合併不會被擋** | `ut` 的 `required_status_checks` 為 **`null`**、`enforce_admins: false`；`main` 唯一 check 在 skipped 時視同通過 | Bolt 1 gate |
| 3 | U-10a 兩支守衛未接進任何 workflow | 「19 項全綠」不等於「這些設定受保護」 | ci-pipeline stage ／ Bolt 1 gate |
| 4 | `COMPILED:` 不驗 `compiler_version` | 用較新 gh-aw 重編會夾帶 6 項未審查的供應鏈變更 | Bolt gate |
| 5 | NFR-P1 沒有量測機制，除非 U-7 真的產出 `latency_samples` | U-6 與 U-7 之間**沒有 DAG 邊** | Bolt 2 gate |
| 6 | README 看板連結**匿名 404**（#16 為 `public: false` 而 repo 為 `public`） | 本輪 `gh api` 確認 repo 為 public | 產品決定 |
| 7 | `deploy.yml` 對反向 PR 無 `paths` 過濾 ⇒ 反向 PR 合併觸發完整部署 | 涉及 ADR-0008 的部署模型 | gate |
| 8 | `team.md ## Code Style` 的前端 lint 基準（3 warnings）已過期 | 本輪實測 **2 warnings**，`LoginPage.tsx:36` 已消失、`WorkspacePage` 由 `:279` 移到 `:302` | 下一輪 practices-discovery |
| 9 | **反向同步與對帳共用 concurrency group**，與 U-8 nfr 階段的「自成第三組」裁定相反 | 實作的三個理由更強（`open-items.md` N:C-2 把該裁定判為 Critical、處置為「需 ADR 或回退」，而 ADR 至今未開出）；改回是一行的改動，且 `run-reverse-tests.py` 有靜態斷言鎖住現值 | Bolt 3 gate |

## 一項自我更正

我在 code-generation 的核可摘要裡把工作樹的 5 個 `__pycache__` 目錄列為「要進
`.gitignore`」的待辦。**該項不成立**——`.gitignore:30` 早已有 `__pycache__/`，
`git status --untracked-files=all .github/actions` 對它們的命中數為 **0**。用一條指令
就能查證的事實不該憑印象寫進要交給人做決定的摘要裡。

## 與上游的對應

逐單元的完成判準與明知缺口引自 12 個單元的 `code-generation-plan.md` 與
`code-summary.md`（尤其各檔的「交還 Bolt gate 的清單」與「未完成項目」）；NFR 面引自
U-6／U-7／U-8／U-9 的 `performance-requirements.md` 與 12 份 `security-requirements.md`；
分支保護、secrets／variables 與 repo visibility 為本階段以 `gh api` 實測；lock 可重現性
引自 U-10b 的 `code-summary.md`。
