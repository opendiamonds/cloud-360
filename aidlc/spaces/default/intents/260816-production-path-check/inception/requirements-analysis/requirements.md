# Requirements — 禁止 production 路徑的 contract 檢查修正

- Intent：`260816-production-path-check`
- Scope：bugfix（8 stages，Minimal depth）
- 來源：GitHub issue [#509](https://github.com/opendiamonds/cloud-360/issues/509)
- 決策依據：`requirements-analysis-questions.md` 的 Q1=A、Q2=C

## 問題陳述

`scripts/validate_repo_contract.py` 的 `validate_no_production_config_added()`（第 356 行）宣稱擋下含 `prod`／`production`／`secrets` 的路徑，但**它在 CI 裡從來不會擋到任何東西**。

輸入是 working tree 的 diff（`git diff --cached` ∪ `git diff`），而 **CI 跑的是乾淨 checkout —— 兩個集合都是空的**，迴圈不執行，函式必定回傳 0（[Q1 Sources S-1、S-2]）。

`project.md` 的 `## Forbidden` 卻寫著「CI 會擋（CI 紅燈）」。**規則的宣稱強度高於機制的實際強度**：只有本機有未提交變更時才作用，PR 上完全不設防。

## 功能需求

| ID | 需求 | 驗證方式 |
|---|---|---|
| **FR-1** | 檢查在**乾淨工作樹**（CI 的實際條件）下仍能偵測違規路徑 | 於乾淨工作樹建立含 `production` path part 的檔案並提交，檢查須 exit 1 |
| **FR-2** | 比對基準改為 `git ls-files` 的全域掃描，涵蓋所有版控中的檔案 | 讀程式碼確認不再依賴 `git diff` |
| **FR-3** | 維持 **path-part 精確比對**，不得以子字串比對 | 既有 10 個含 `prod`／`secret` 字串但非完整 path part 的檔案（如 `aidlc-product-agent.md`）不得被擋 |
| **FR-4** | 違規時列出所有違規路徑並回傳非 0 退出碼 | 觸發違規時輸出含完整路徑清單 |
| **FR-5** | 目前 repo 在修正後仍通過檢查 | 實測 0 命中（[Q1 Sources S-5]） |

## 非功能需求

| ID | 需求 | 理由 |
|---|---|---|
| **NFR-1** | **不得**修改 `.github/workflows/ci.yml` | 全域掃描不需要 base。`ci.yml` 未設定 `fetch-depth`，預設為淺 clone（[Q1 Sources S-3]）——`git log -p --follow` 顯示該欄位從未被設定過，故這是預設值而非已記錄的團隊決策；但全域掃描本就不依賴 base，沒有理由為此變更 CI |
| **NFR-2** | 不得引入新依賴 | `git ls-files` 由既有的 subprocess 呼叫即可取得 |
| **NFR-3** | `validate_no_production_config_added()` 單次執行 **< 1 秒** | 原措辭「不顯著增加」不可測，違反 `phases/inception.md` 的「NFR 須配可量測門檻」。實測基準：`git ls-files` ≈ 0.025s、兩次 `git diff --name-only` ≈ 0.034s，1 秒門檻有充裕餘裕且可機械判定 |

## 規則層同步（Q2=C）

| ID | 需求 | 內容 |
|---|---|---|
| **FR-6** | `project.md` `## Forbidden` **與 `CLAUDE.md` 第 4 章**的措辭與機制一致 | 語意由「不得**新增**」改為「不得**存在**」，並註明檢查方式為全域掃描。**`CLAUDE.md` 落點為 code-generation 階段補列（人工確認於 audit shard 的 `HUMAN_TURN 2026-08-17T23:40:58Z`；該次回合即為此決策的核可，`CLAUDE.md` 的實際寫入時間為 `23:41:16Z`，晚於它 18 秒。決策本身記於該 stage 的 `code-generation-questions.md` Q2（附 `[Answer]: A` tag），比照 Q3 的形式可獨立複驗）**：初版 FR-6 只點名 `project.md`，但 `CLAUDE.md` 第 4 章自述「本章為摘要，衝突時以 memory 層為準」，是 `project.md` 的**衍生落點**而非獨立規則，漏改它即構成本 intent 反覆在修的同一種失敗形狀（改上游、漏衍生落點）。實測 contract 的 `REQUIRED_TEXT` 未鎖該句，改動不影響 CI |
| **FR-7** | 移除 `team.md` 中已不成立的落差記載，**並同步修正該段落的收尾句** | 該處記載「這道檢查在 CI 恆為 no-op」，修正後不再為真。**該段落的開頭句與收尾句都必須一併改**（reviewer M-1 + 第二輪新發現）：**開頭句**為「`project.md ## Forbidden` 現有**兩條**規則的宣稱強度高於機制的實際強度：」，**收尾句**為「**這兩項**不是『缺工具』…**本輪不逕自變更腳本行為（未經訪談定案）**」。刪掉其中一條 bullet 後，兩處的複數指涉同時失效；且「不逕自變更腳本行為」在本 intent 正在變更腳本行為時字面成假。**這兩句是同型失誤，不可只改其一** |

### 關於編輯 `team.md` 的權限（經 reviewer 質疑後重新定案）

**初版論證**：`team.md` 標頭寫「Edit at the gate, not directly」，指的是**規則的新增與修改**須經 practices-discovery 的 affirmation gate；FR-7 移除的是一條在修正後不再為真的**事實記載**，屬事實更正而非政策變更。

**reviewer 的質疑（M-2，成立）**：上述論證只問了「這句話本身是事實還是政策」，**沒有回答「這句話落在哪個 section」**——而後者對這個區分不利：

- FR-7 的刪除目標位於 `team.md` 的 **`## Deployment`**，那是標頭宣告受 gate 治理的**五個實質段落之一**（Way of Working／Walking Skeleton／Testing Posture／Deployment／Code Style），**不是** `## Corrections`（自我學習迴圈的自由編輯區）。
- `project.md` 的 corrections 有一條把這五個 section 當**整體治理單位**處理（「practices-promote 是整段替換 team.md 的五個 section 而非合併…漏寫即等於刪除既有規則」），而非逐句判斷性質。

**定案（2026-08-18，人工確認）**：**本 intent 直接修改，並在此記明這是一次有意識的例外**，而非「不受 gate 管轄」的常態主張。

理由與邊界：

1. 保留一條**已知為假**的事實記載，其代價（後續每個讀 `team.md` 的 stage 都會取得錯誤認知）高於一次越界編輯的程序成本。
2. 本次變更**只刪除與修正一條已失效的事實描述及其收尾句**，不新增規則、不放寬任何約束、不改變任何政策。
3. reviewer 指出的治理邊界問題**確實存在**，故記為例外而非先例。下次 practices-discovery 應覆核此處，並順帶決定「五個 section 內的純事實記載該由誰維護」——那才是這個張力的根本解法。

FR-6（`project.md` 的措辭更新）不涉及此爭議：`project.md` 不受 practices-discovery gate 治理，且該變更是讓既有規則的措辭與其承載機制對齊，不新增也不放寬約束。

## 回歸測試的落點（reviewer C-1 指出的缺口，本節為其解決方案）

reviewer 指出 NFR-1（不得改 `ci.yml`）與 Definition of Done（測試須能防止缺陷靜默復發）之間存在未解決的矛盾：**CI 唯一的測試探索是 `backend` job 的 `python -m unittest discover -s tests -v`（`ci.yml:135`，`working-directory: backend`），只撿得到 `backend/tests/`**。把測試放在 `scripts/tests/` 之類的位置會字面滿足 DoD，卻不被任何 PR 執行——**與本 bug 的失敗形狀完全相同**（宣稱強度高於機制強度）。

因此本需求明確指定：

| ID | 需求 | 理由 |
|---|---|---|
| **FR-8** | 回歸測試放在 **`backend/tests/`**，檔名符合 `unittest discover` 的預設樣式（`test_*.py`） | 這是唯一會被既有 CI job 自動執行的 Python 測試落點，且不需要改 `ci.yml` |
| **FR-9** | 測試**不得**在真實 repo 上建立含違規路徑的檔案或 commit | 那會把違規路徑寫進共用 repo 的 git 歷史；即使事後 revert 也留痕，並可能誤觸他人分支上的同一道檢查 |
| **FR-10** | 測試以**隔離的暫存 git repo**（`tempfile` + `git init`）建構待測情境，並使被測函式指向該暫存目錄（例如以 `unittest.mock.patch` 覆寫模組層級的 `ROOT`） | 讓 AC-1 的「乾淨工作樹」條件可在測試內重現，而不污染真實 repo |

> `backend/tests/` 放一支測試 repo 根目錄腳本的測試，位置上略顯不直觀。但**「會被自動執行」的重要性高於「目錄語意純粹」**——一個放在語意正確位置卻永不執行的測試，正是這次要修的缺陷本身。檔案內以 docstring 註明它測的是 `scripts/` 下的腳本與此安排的理由。

## 驗收標準

**AC-1 缺陷本身可被重現與擋下**（核心驗收點）
- **Given** 一個乾淨的工作樹（無 staged、無 unstaged 變更）
- **When** 版控中存在路徑含 `production` 作為完整 path part 的檔案
- **Then** `validate_repo_contract.py` 回傳非 0 退出碼，並在輸出中列出該路徑

**AC-2 不誤擋含子字串的檔名**
- **Given** 版控中存在 `.claude/agents/aidlc-product-agent.md` 等 10 個含 `prod`／`secret` 字串但非完整 path part 的檔案
- **When** 執行檢查
- **Then** 這些檔案**不被**列為違規

**AC-3 現況通過**
- **Given** 修正後的檢查與目前的 repo 內容
- **When** 執行 `python3 scripts/validate_repo_contract.py`
- **Then** 退出碼為 0

**AC-4 CI 設定未被更動**
- **Given** 本次修正
- **When** 檢視 `git diff`
- **Then** `.github/workflows/ci.yml` **不在**變更清單中

**AC-5 規則與機制一致**
- **Given** 修正完成後的 `project.md` `## Forbidden`
- **When** 逐字比對其宣稱與 `validate_no_production_config_added()` 的實際行為
- **Then** 兩者一致，且 `team.md` 不再有「這道檢查在 CI 恆為 no-op」的記載
- **And** 該段落的收尾句不再以複數指涉單一項目，且不再宣稱「本輪不逕自變更腳本行為」
- **And** 通篇重讀該段落無內部矛盾（不能只做字串刪除就宣告完成）

**AC-6 回歸測試會被既有 CI job 自動執行**（reviewer C-1）
- **Given** 修正完成後的測試檔
- **When** 在 `backend/` 目錄執行 `python -m unittest discover -s tests`（即 `ci.yml:135` 的實際指令）
- **Then** 該測試被探索到並執行

## Definition of Done

依 `org.md` `## Testing Posture`，bugfix scope 需要**針對該缺陷的回歸測試**，且既有測試須維持全綠：

- 存在一個能在**乾淨工作樹**下重現 AC-1 的自動化驗證 —— 缺這一項，這個缺陷可以原樣復發而無人察覺
- 該驗證必須做過**突變測試**：把修正還原成 diff 基準後必須紅燈（依 `aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md` **§5「突變驗證：沒看過它紅過，就不算寫完」**。注意 `TESTING.md` §5 是 `tcms_validate.py` 的機械檢查，**不是**突變測試——兩者不可混淆）
- `python3 scripts/validate_repo_contract.py` 與 `validate_env_contract.py` 皆通過
- 後端既有測試維持全綠

## 範圍邊界

**在範圍內**：`scripts/validate_repo_contract.py` 的 `validate_no_production_config_added()`、其回歸測試、`project.md` 與 `team.md` 的對應措辭。

**不在範圍內**（各自獨立，不由本 intent 夾帶）：

- `unsupported` 的雙向死契約（前端處理、後端從未產生）—— 見 codekb `architecture.md`
- `fetch_icon_from_n8n()` 殘留的一條無 log 降級路徑（T-17）—— 屬 PR #499／#508 範圍
- `validate_no_obvious_secrets()` 的掃描範圍過窄（看不到 `backend/`／`frontend/`）—— 同屬 contract 的既知落差，但成因與修法都不同
- `FORBIDDEN_NEW_PATH_PARTS` 的內容調整

## 與既有記載的關係（reviewer Minor-2）

本缺陷已被記載於 `aidlc/spaces/default/intents/260802-last-login-column/inception/practices-discovery/discovered-rules.md` 第 4 項：

> **`validate_no_production_config_added()` 在 CI 恆為 no-op**：…待修正 diff 基準（PR 情境對 base ref，push 情境對 `HEAD~1`），讓它在 CI 真的會擋。

兩點須明記：

1. **該記載提出的修法是 diff 基準修正（即本站 Q1 的選項 B），本 intent 選的是 A（全域掃描）。** 這不是推翻它——該檔結尾明寫「具體導入方案（優先序、範圍、是否分階段）留待下一輪 practices-discovery **或獨立技術債任務**決定」，**本 intent 正是那個獨立技術債任務**，選 A 屬於它預期的決策路徑。選 A 的依據見 Q1 的 Sources S-3～S-5。
2. 修正完成後，該筆記載應被標註為已解決。它屬於另一個 intent 的 record，本 intent **不逕行修改**；改由 `tcms-sync-report` 或本 intent 的完成摘要中列為待辦，交下一輪 practices-discovery 處理。

## 假設

1. 修正範圍限於 `scripts/validate_repo_contract.py`，不擴及其他 contract 檢查。
2. 回歸測試須能在**乾淨工作樹**（CI 的實際條件）下重現原缺陷。
3. `FORBIDDEN_NEW_PATH_PARTS` 的內容（`prod`／`production`／`secrets`）不變。
4. 本 intent 不處理 codekb 中發現的其他缺陷。

## 開放問題

- 語意由「不得新增」轉為「不得存在」後，若日後真有正當理由需要一個含 `prod` path part 的檔案（例如第三方套件的目錄結構），豁免機制尚未定義。目前 0 命中，故不預先設計 —— 待實際出現時再處理。

## 追溯

| 需求 | 來源 |
|---|---|
| FR-1～FR-5、NFR-1～NFR-3 | issue #509 + Q1=A |
| FR-6、FR-7 | Q2=C；FR-6 的 `CLAUDE.md` 落點為 code-generation 階段補列，依據見該 stage 的 `code-generation-questions.md` Q2（`[Answer]: A`） |
| FR-8～FR-10、AC-6 | reviewer C-1（回歸測試的 CI 執行路徑） |
| FR-7 的收尾句修正、AC-5 的後兩條 And | reviewer M-1 |
| NFR-3 的量化門檻 | reviewer M-3 + `phases/inception.md` |
| AC-1～AC-6 | 上述 FR 的可驗證形式 |
| Definition of Done | `org.md` `## Testing Posture`（bugfix scope）、`test-case-authoring.md` §5（突變驗證） |
