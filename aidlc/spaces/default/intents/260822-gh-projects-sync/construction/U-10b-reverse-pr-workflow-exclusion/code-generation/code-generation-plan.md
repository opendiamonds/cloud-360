# Code Generation Plan — U-10b 反向 PR 的高成本 workflow 排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10b-reverse-pr-workflow-exclusion · kind: packaging
     Created: 2026-09-05T19:05:32Z（讀自 date -u） -->

## 交付物

| 檔案 | 改動 |
| --- | --- |
| `.github/workflows/{ui-regression,pr-reviewer,lint-fix,contract-guard}.md` | frontmatter 的 `on.pull_request` 加 `paths-ignore`（一條 glob）＋ 註解 |
| `.github/workflows/{ui-regression,pr-reviewer,lint-fix,contract-guard}.lock.yml` | **由釘住的 gh-aw v0.81.6 重編產生**（Q1=A），每檔差 4 行 |
| `.github/actions/aidlc-sync-ci-guard/check-gh-aw-exclusion.py` | 機械檢查：四支的 `.md` 與 `.lock.yml` 都有該 glob **且兩者一致** |
| `.github/actions/aidlc-sync-ci-guard/run-gh-aw-exclusion-tests.py` | 上者的行為測試（含突變） |

複雜度上游記 **XS**；`N:M-5` 讓它實際落在 **S**——多了編譯與漂移檢查。不新增 repo 依賴（編譯器是 scratchpad 內的一次性 binary，不進版控、不改使用者的 `gh extension`）。

## 開工前查證（全部為 orchestrator 實測，非引用）

### 查證 1 — 現況：一則反向 PR 會發動幾組 workflow

逐檔解析 `.github/workflows/*.md` 的 `on:`，**四支**吃 `pull_request` 且**無 `paths` 過濾**：`ui-regression`／`pr-reviewer`／`lint-fix`／`contract-guard`（四支的 `on:` 形狀逐字相同：`types: [opened, synchronize, reopened]` ＋ `workflow_dispatch:`）。`code-drift-alert`／`local-dev-drift` 已被自身的 `paths:` allowlist 排除。加上 `ci.yml`（`on: pull_request` 無過濾），**五組**。

> **修訂（MAJOR-4，2026-09-06，code-generation stage 自我更正）**
>
> **原文的「五組」是錯的，正確是 6。** 錯誤成因是**範圍錯配**：上一段把實測範圍限在 `.github/workflows/*.md`（那裡只有 gh-aw workflow），卻給出一個宣稱涵蓋純 Actions workflow 的總數——`ci.yml` 是被記得的那一個，`aidlc-sync-forward.yml` 不是。而 `aidlc-sync-forward.yml` 正是本 intent 自己的 U-6 交付物，它的 `on.pull_request` 為 `{"types": ["opened","synchronize","closed"]}`，**無 `paths`、無 `branches`**。
>
> 正確的計數面是 `.github/workflows` 下每一個 **`.yml`／`.lock.yml`**（GitHub 執行的是 `.lock.yml`，而剩下的兩個根本沒有 `.md`）。以一個「變更檔案集合恰為 `<record>/sync-state.json`、base 為 `ut`、事件 `pull_request/opened`」的模擬逐檔判定 22 個檔（實際解析輸出見 `code-summary.md` 的交還清單第 6 項與本輪回報）：
>
> | | 會建立 run 的 workflow |
> | --- | --- |
> | **U-10b 之前**（6） | `ci.yml`、`aidlc-sync-forward.yml`、`ui-regression.lock.yml`、`pr-reviewer.lock.yml`、`lint-fix.lock.yml`、`contract-guard.lock.yml` |
> | **U-10b 之後**（2） | `ci.yml`（`gate` 成功、四個下游 job Skipped）、`aidlc-sync-forward.yml`（防線② `exit 0`，不寫看板） |
>
> 排除的理由逐項可查：`aidlc-sync-selftest`／`code-drift-alert`／`local-dev-drift` 的 `paths` allowlist 無一命中；`deploy.yml` 的 `types: [closed]` 不含 `opened`（它在**合併時**才觸發，見查證 4）。
>
> **本單元的交付範圍不變**——仍是那四支 gh-aw。`aidlc-sync-forward` 這一項屬 `open-items.md` **N:C-2**（Critical、未解）的範圍，**登錄不處置**。

### 查證 2 — lock 可重現（Q1=A 的實證基礎）

| 實測 | 結果 |
| --- | --- |
| repo 內四支 lock 的 `compiler_version` | 全為 **v0.81.6** |
| 本機 `gh aw` 版本 | **v0.86.2** |
| 用釘住的 v0.81.6 對**未修改**的四支 `.md` 重編 | 四支 lock **逐位元相同**（BYTE-IDENTICAL） |
| 用 v0.81.6 對**加了 `paths-ignore`** 的四支重編 | 每檔 diff **4 行**：1 行 `frontmatter_hash` ＋ 2 行 `paths-ignore` |
| 用 v0.86.2 重編 | 每檔 **526 行**（action SHA、防火牆容器、mcpg、github-mcp-server 全升） |

> **修訂（m1，2026-09-06，code-generation stage 自我更正）**
>
> **「每檔 526 行」是錯的：四支都不是 526，而且「每檔」也錯——四者不相等。** 本輪以 `gh aw` v0.86.2 在 scratchpad 的隔離樹上重編（真實 repo 未執行任何 v0.86.2 編譯），計數慣例與同表上一列的「4 行」同一把尺（`git diff --numstat` 的 added ＋ deleted）：
>
> | 讀法（基準 lock 與 `.md` 取自同一個時點） | ui-regression | pr-reviewer | lint-fix | contract-guard |
> | --- | --- | --- | --- | --- |
> | 對 **HEAD** 的 `.md`（本題作答當下的狀態） | 519 | 520 | 527 | 527 |
> | 對**交付後**的 `.md`（＝選項 B 真正的代價） | 521 | 522 | 529 | 529 |
>
> 兩種讀法固定相差 2 行（本單元加的 `paths-ignore` 兩行）。**Q1=A 的決定不受影響**：兩種讀法下量級都是「五百多行 vs 4 行」，且 B 的內容仍是與本單元無關的供應鏈升級。錯的是數字，不是判斷。

**「lock 可重現」這件事本身就是本單元的機械化基礎**——它讓「`.md` 改了但沒重編」成為可判定的事實，而不是靠紀律。

### 查證 3 — `N:M-2(B)`：上游記載的補償控制不成立

`security-requirements.md:14` 寫「U-10a 的 `paths-ignore` 同樣不阻止合併後的 push 觸發」。**實查 `ci.yml`：`paths-ignore` 就在 `on.push` 上**（`pull_request` 側刻意不加，該檔註解已寫明理由）。所以合併後的 push **不會**建立 CI run。

**真正的殘餘控制**（Q2=A 的表，逐項實查）：禁止**路徑**檢查因 issue #509 改為 `git ls-files` 全域掃描，會在\_下一次任何其他原因觸發的 CI run\_ 抓到；禁止**內容**檢查（`validate_no_obvious_secrets()`）只掃 `contract_files()`（= `REQUIRED_FILES` ＋ baseline record 必要檔 ＋ audit shard），**`sync-state.json` 不在其中，PR 側與 push 側都不掃**。

**這一段必須逐字寫進實作註解**——不寫，下一個讀 `contract-guard` 被加 `paths-ignore` 的人會合理地以為那是誤加（`security-requirements.md:17` 逐字要求）。

### 查證 4 — 本單元不擁有、但實查發現的一項（Q3=A：只登錄）

`deploy.yml:10-14` 為 `on: pull_request: types: [closed], branches: [ut]`，**無 `paths` 過濾**。反向 PR 合併 ⇒ 觸發自架 runner 上 `timeout-minutes: 30` 的完整部署。**不在本單元擁有範圍**（其擁有欄逐字只寫「高成本 `on: pull_request` workflow」，指的是 PR 開啟側），**不處置，登錄為 open item 指派 gate**。

### 查證 5 — 這個機制成立的唯一前提

`paths-ignore` 的語意是「變更的檔案**全部**命中才跳過」。反向 PR 只改一個檔，是 **E-1 的直接後果**而非巧合（U-8 的 `commit_and_push` 白名單只接受 `<record_path>/sync-state.json`，實查 `aidlc-sync-reverse-impl.yml:602` 的 `AIDLC_PATHS`）。**若哪天有人為反向 PR 多加一個檔，本單元的排除會靜默失效**——`tech-stack-decisions.md:53` 逐字要求這句話進實作註解，因為成因在 U-8 而後果在這裡。

## 計畫步驟

- [ ] **Step 1 — 改四支 `.md` 的 frontmatter**：`on.pull_request` 加 `paths-ignore: ["aidlc/spaces/*/intents/*/sync-state.json"]`。**glob 逐字與 U-10a 的 `ci.yml` 相同**（同一個機制、同一條 glob）。**追溯**：`tech-stack-decisions.md`「決定」節、[US:S-6 AC 7]
- [ ] **Step 2 — 四處註解**，每處都要寫：①為什麼排除（U-8 的反向 PR，成因在另一個單元）；②`contract-guard` 那一支額外寫查證 3 的殘餘控制更正；③查證 5 的「多一個檔就靜默失效」。**追溯**：`security-requirements.md:17`／`:34`、`tech-stack-decisions.md:53`、Q2=A
- [ ] **Step 3 — 重編 lock**：用 scratchpad 內釘住的 **v0.81.6** binary，於 repo 根目錄 `compile`（不加 `--dir`，否則 `runtime-import` 路徑與 `GH_AW_WORKFLOW_SOURCE_URL` 會不同）。**編譯前先確認：對未改的檔重編為逐位元相同**（若不是，代表環境有別的漂移，停下來報告，不要硬推）。**追溯**：Q1=A、`N:M-5`
- [ ] **Step 4 — `check-gh-aw-exclusion.py`**：對四支各斷言 ①`.lock.yml` 的 `on.pull_request.paths-ignore` 含該 glob；②`.md` 的 frontmatter 同樣含它；③兩者一致，`.md` 有而 lock 沒有 ⇒ 紅且訊息含「未重新編譯」。**glob 不寫死字面值**——與 `check-ci-yml.py` 同一個來源（`derive_glob_from_record_sh()`），漂移即紅。**追溯**：`N:M-5`、查證 2
- [ ] **Step 5 — 測試 ＋ 突變驗證**（見下節）
- [ ] **Step 6 — `code-summary.md`**（orchestrator 執筆）

## 測試策略

**行為測試**：以合成的暫存 repo 樹驅動檢查器，斷言 rc 與訊息。**不做文字結構斷言。**

**必測清單**：

| # | 測什麼 | 為什麼非測不可 |
| --- | --- | --- |
| 1 | 四支的 `.lock.yml` 缺該 glob ⇒ **紅**（逐支各一條） | `N:M-5` 的核心：GitHub 跑的是 lock |
| 2 | `.md` 有而 `.lock.yml` 沒有 ⇒ **紅**，訊息含「未重新編譯」 | 這是 lock 機制唯一的漂移形態 |
| 3 | `.lock.yml` 有而 `.md` 沒有 ⇒ **紅** | 反向漂移；lock 是產生物，不該領先原始檔 |
| 4 | glob 與 `record.sh` 推導出的不一致 ⇒ **紅** | 不寫死字面值 |
| 5 | `derive_glob_from_record_sh()` 推導失敗 ⇒ **紅**，不靜默放行 | fail-closed |
| 6 | 四支中少列一支（把清單改成三支）⇒ **紅** | 「檔案集合一致性」自檢項；少一支等於少一個排除而無人知 |
| 7 | glob 被放寬成 `aidlc/**` 或 `**/*.json` ⇒ **紅** | 與 U-10a 的 SEC-1 同一個危害：放寬會讓所有 AIDLC 產出或 lockfile 繞過檢查 |

**突變驗證**：#1～#7 各對應一次突變，逐條記錄**實際紅的測試名稱**，確認打中的是對應那一條。

## 與 U-9 的交界（不得重複實作）

U-9 的 `check-paths-relations.py` 已擁有 **A-6**（「U-8 寫入路徑集合 ⊆ `paths-ignore` glob 集合」＋「該集合 ∩ U-9 allowlist ＝ ∅」），且已被告知那四支要檢 `.lock.yml`。

**本單元的 `check-gh-aw-exclusion.py` 與它不重疊**：A-6 驗的是**集合關係**（誰被涵蓋、誰不相交），本單元驗的是**單一承載體內部的 `.md` ↔ `.lock.yml` 一致性**。兩者可以都紅、也可以只紅一個，是不同的失敗模式。**若實作時發現兩者其實同義，回報而不是二選一實作**——那代表我對交界的判斷錯了。

**本單元完成後，U-9 的 A-6 檢查器對真實 repo 應由紅轉綠**——這是 U-10b 的完成判準之一，實作完要實跑確認。

## 完成判準（上游 ＋ 本站擴大，逐條可驗）

| # | 判準 | 本 stage 的證據 |
| --- | --- | --- |
| 1 | 四支的 `.md` 與 `.lock.yml` 都含該 glob 且一致 | **可實跑證明**（`check-gh-aw-exclusion.py` 對真實 repo 綠） |
| 2 | lock 由釘住的 v0.81.6 產生，diff 只含本單元的改動 | **可實跑證明**（每檔 4 行） |
| 3 | U-9 的 A-6 檢查器對真實 repo 轉綠 | **可實跑證明** |
| 4 | 反向 PR 開啟後四支皆未執行 | **無法在本 stage 證明**——需真實反向 PR，不在授權內。列為 **Bolt 3 首次反向 PR 的實測項** |
