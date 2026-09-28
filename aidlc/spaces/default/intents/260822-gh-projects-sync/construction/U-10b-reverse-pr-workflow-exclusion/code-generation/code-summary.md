# Code Summary — U-10b 反向 PR 的高成本 workflow 排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10b-reverse-pr-workflow-exclusion · kind: packaging
     Generated: 2026-09-05T23:54:38Z（讀自 date -u） -->

## 變更

| 檔案 | 動作 | 量（`git diff --numstat` 實測；括號內為 reviewer 輪之前的值） |
| --- | --- | --- |
| `.github/workflows/ui-regression.md` | 修改 | `62 0`（原 `27 0`） |
| `.github/workflows/pr-reviewer.md` | 修改 | `62 0`（原 `27 0`） |
| `.github/workflows/lint-fix.md` | 修改 | `62 0`（原 `27 0`） |
| `.github/workflows/contract-guard.md` | 修改 | `119 0`（原 `55 0`；多出 contract-guard 專屬的更正段） |
| `.github/workflows/ui-regression.lock.yml` | 重編 | `3 1` |
| `.github/workflows/pr-reviewer.lock.yml` | 重編 | `3 1` |
| `.github/workflows/lint-fix.lock.yml` | 重編 | `3 1` |
| `.github/workflows/contract-guard.lock.yml` | 重編 | `3 1` |
| `.github/actions/aidlc-sync-selftest/run-selftest-tests.py` | 修改 | 只改 `test_the_real_repo_state_is_what_we_say_it_is` 一個函式（絆線翻面 ＋ 本輪收窄第 (2) 條與 `@pass`）。該檔所在的 `.github/actions/` 整棵仍為 untracked，故無 numstat |

四支 `.md` 的行數增加、四支 lock 的 `3 1` **不變**：註解全部落在 frontmatter 內，lock 那 4 行仍是「1 行舊 `gh-aw-metadata` ＋ 1 行新 `gh-aw-metadata` ＋ 2 行 `paths-ignore`」，本輪重編只換掉了 metadata 那一行裡的 `frontmatter_hash`。

**四支 `.md` 皆為 `0` 行刪除**：既有的 `on:` 形狀、`types`、`workflow_dispatch:` 與所有既有註解（含 `ui-regression.md` 那段 #513 的 `timeout-minutes` 說明）一個字都沒被碰過，只是在 `types:` 與 `workflow_dispatch:` 之間插入註解與 `paths-ignore`。

不新增 repo 依賴。編譯器是 scratchpad 內的一次性 binary，不進版控、不改使用者的 `gh extension`。

## 本輪修訂（reviewer NOT-READY 之後）

reviewer 判 **NOT-READY**（0 Critical／4 Major／4 Minor）。**機制本身未被推翻**——`paths-ignore` 語意、承載體集合、lock 可重現性、絆線的紅燈能力皆經獨立複驗成立；失敗的是寫在機制周圍的宣稱。本節列出本輪改了哪些**事實**與它們的落點，其餘各節已就地更新，不再逐處加標記。

| # | 被更正的事實 | 落點 |
| --- | --- | --- |
| MAJOR-1 | 反向 PR 上 `ci.yml` **會**建立 run（`gate` 成功、四個下游 job 為字面意義的 Skipped），原「皆無 run 被創建（不是跳過，是不存在）」對 `ci.yml` 為假 | 交還清單第 4 項、完成判準 4、四支 `.md` 共用註解 |
| MAJOR-2 | Q2 殘餘控制表掉了決定答案的第三列（`gate` job），且把「有涵蓋」誤標為「延後」——人手開的單檔 PR 沒有 `[aidlc-sync]` 標記，`repo-contract` **在 PR 當下就跑**，禁止路徑是**立即**涵蓋 | Q2=A 節的表、交還清單第 1 項、`contract-guard.md` 專屬註解 |
| MAJOR-3 | 「改了 `.md` 沒重編 ⇒ `COMPILED:` 會紅」為假：它只在「增刪了**這一條 glob**」時成立 | 觸發紅燈表、交還清單第 5 項、絆線訊息第 (2) 條與該測試的 `@pass` |
| MAJOR-4 | 反向 PR 發動的組數：U-10b 前 **6** 組（非 5，漏掉 `aidlc-sync-forward.yml`）、後仍有 **2** 組（非 0） | 四支 `.md` 共用註解、`run-selftest-tests.py` 絆線第 (1) 條、本檔、`code-generation-plan.md` |
| m1 | v0.86.2 重編**不是**「每檔 526 行」，且四者不相等 | 交還清單第 3 項、`code-generation-plan.md`、`code-generation-questions.md` Q1 表 |
| m2 | 必測 #1／#2 對應的 checker ID 寫反 | 下一節 |
| m3 | `ci.yml`／SEC-1d 的全稱命題需加適用前提 | 四支 `.md` 共用註解 |
| m4 | 必測突變「各對應一次」的偏離未列進偏離表 | 偏離表 |

**改註解的連帶後果（本輪一併執行）**：四支 `.md` 被改的段落全在 **frontmatter 內**，而 `frontmatter_hash` 對 frontmatter 的任何文字變動（含純註解）都會變——實測：只改一行註解文字，hash 由 `804bda34…` 變為 `381ec1ed…`。因此四支 lock **必須以釘住的 v0.81.6 重編**，否則本輪就會親手製造 MAJOR-3 描述的那種漂移。已重編，metadata 變動欄位逐檔實測為 `['frontmatter_hash']` 單一項，`compiler_version` 維持 `v0.81.6`、`gh-aw-manifest` 在 diff 中出現 0 行。

## 計畫的一處更正：**不**新寫 `check-gh-aw-exclusion.py`

計畫的「與 U-9 的交界」節原本要本單元另交付 `check-gh-aw-exclusion.py` ＋ `run-gh-aw-exclusion-tests.py`，並附一句「若實作時發現兩者其實同義，回報而不是二選一實作」。

**確認就是同義的，故未實作。** U-9 在它的 reviewer iteration 1 之後（偏離 D-5）已把四支 gh-aw 各拆成三項檢查——`IGNORE:<名>.md`、`IGNORE:<名>.lock.yml`、`COMPILED:<名>`（`check-paths-relations.py` 的 `GH_AW_CARRIERS` 迴圈）。那 12 項逐字涵蓋了計畫要本單元斷言的全部三件事（lock 有、md 有、兩者一致），連「`.md` 有而 lock 沒有 ⇒ 訊息含未重新編譯」的措辭都已經在 `COMPILED:` 的失敗訊息裡。再寫第二支等於製造第二份斷言同一件事的程式——`team.md ## Code Style`「單一真實來源」逐字禁止的形狀，且兩份遲早會漂移。

計畫「測試策略」的必測 #1～#7 逐項落點（全部已被 U-9 既有測試覆蓋，本站複驗）：

| 必測 | 內容 | 對應的 checker ID |
| --- | --- | --- |
| #1 | 四支的 `.lock.yml` 缺該 glob ⇒ 紅 | `IGNORE:*.lock.yml` |
| #2 | `.md` 有而 `.lock.yml` 沒有 ⇒ 紅，訊息含「未重新編譯」 | `COMPILED:*` |
| #3 | `.lock.yml` 有而 `.md` 沒有 ⇒ 紅 | `IGNORE:*.md` |
| #4／#5 | glob 與 `record.sh` 推導不一致／推導失敗 ⇒ 紅 | `derive_write_glob()` 的 fail-closed（`run-selftest-tests.py` 既有測試） |
| #6 | 四支中少列一支 ⇒ 紅 | 本站**新**補的通過集合逐項比對（見下節，原本沒被覆蓋） |
| #7 | glob 被放寬 ⇒ 紅 | `DISJOINT-1` 的 glob 交集判定 |

> **修訂（m2，本輪）**：原文為一行式「#1／#2／#3 ＝ `COMPILED:*`／`IGNORE:*.lock.yml`／`IGNORE:*.md`」，其中 #1 與 #2 的對應**寫反了**。#1 是「lock 缺 glob」，那是 `IGNORE:<名>.lock.yml` 的判定（`lock_has`）；#2 是「md 有而 lock 沒有」，那才是 `COMPILED:<名>` 的判定式 `not (md_has and not lock_has)`。#3 的對應原本就正確。改為表格呈現以免同型錯誤再發生；**必測清單本身與覆蓋結論不變**，錯的只是對應標籤。

## Q1=A 的執行：三步逐一驗過

| 步驟 | 做法 | 實測結果 |
| --- | --- | --- |
| **A** 先證明可重現 | 在**真實 repo**（非 scratch 複本）上，用釘住的 v0.81.6 對**未修改**的四支 `.md` 重編 | 四支 lock 的 md5 **完全不變**，`git status --porcelain .github/workflows/` 未列出任何 lock ⇒ **BYTE-IDENTICAL 確認** |
| **B** 改四支 `.md` | 見下節 | frontmatter 四支皆解析出 `on.pull_request.paths-ignore: ['aidlc/spaces/*/intents/*/sync-state.json']` |
| **C** 重編 | 同一支 v0.81.6，`compile ui-regression pr-reviewer lint-fix contract-guard`（**不加 `--dir`**） | 每檔恰 **4 行**變動：`-` 1 行舊 `gh-aw-metadata` ＋ `+` 1 行新 `gh-aw-metadata` ＋ `+` 2 行 `paths-ignore` |
| **D** 波及範圍 | `git status --porcelain` | 相對開工前的基線，**只多出那 8 個檔** |

**Step C 的 metadata 行只有 `frontmatter_hash` 變**：`body_hash` 逐字不變（沒動 prompt 本文）、`compiler_version` 維持 `v0.81.6`、整條 `gh-aw-manifest`（action SHA、防火牆容器、mcpg、github-mcp-server 的 digest）**一個字元都沒變**。這是「沒有夾帶供應鏈升級」的機械證據——本機 `gh aw` 是 v0.86.2，用它會是每檔五百多行（實測值見交還清單第 3 項；原文寫的「每檔 526 行」是錯的，見 m1）。

## Step B：四支 `.md` 改了什麼

`on.pull_request` 加 `paths-ignore: ["aidlc/spaces/*/intents/*/sync-state.json"]`。

**glob 不是手抄的**：套用腳本以 `yaml.safe_load` 讀 `.github/workflows/ci.yml` 的 `on.push.paths-ignore`，斷言它仍是**單一** glob 後取用該字面值。U-10a 那條若改，這裡不會悄悄分岔（分岔會被 U-9 的 `IGNORE:*` 當場抓到，因為兩邊都跟 `record.sh` 推導出的同一條比）。

四處註解每處都寫了下列五件事（前三件為 `tech-stack-decisions.md:53`／`security-requirements.md:17`／`:34` 逐字要求；第 4、5 件為本輪 reviewer 之後補上），`contract-guard` 多寫第六件：

1. **為什麼排除**——U-8 的反向同步 PR（`aidlc-sync-reverse-impl.yml`）。成因在另一個單元，後果在這裡。
2. **這個機制成立的唯一前提**——`paths-ignore` 的語意是「變更的檔案**全部**命中才跳過，不是多數決」。反向 PR 只改一個檔是 **E-1 的直接後果**而非巧合：`record.sh` 的 `commit_and_push` 白名單只接受 `<record_path>/sync-state.json`，而 `aidlc-sync-reverse-impl.yml` 逐字只在 `AIDLC_PATHS` 傳那一個路徑。**多加一個檔，排除就靜默失效——沒有錯誤、沒有紅燈，這四支只是又開始跑。**
3. **被排除的 run 是「不存在」而非「跳過」**——GitHub 根本不建立 run，Actions 頁面上什麼都不會顯示，與「這支 workflow 從沒設定過」長得一模一樣。反向 PR 上看不到**這四支**，不要讀成它們壞了。
4. **（MAJOR-4，本輪新增）排除之後反向 PR 上還會跑什麼**——`ci.yml`（建立 run，`gate` 成功且四個下游 job 為 Skipped）與 `aidlc-sync-forward.yml`（建立 run，orchestration 於防線②`exit 0`）。並寫明計數是解析 `.yml`／`.lock.yml` 集合而非 `*.md`，以及 `aidlc-sync-forward` 這一項屬 **N:C-2**（Critical、未解）的範圍，**不得**自行為它加排除。
5. **（m3，本輪新增）`ci.yml` 全稱命題的適用前提**——`ci.yml:8-11` 與 `check-ci-yml.py` 的 SEC-1d 逐字宣稱 `pull_request` 側的 `paths-ignore`「永遠不會成立」，而讀者剛讀完的機制正好是反例。註解補上「那句話對**開發者** PR 為真、對這則**機器** PR 為假」的區分，讓兩者可以並存而不互相看起來像錯字。
6. **（僅 `contract-guard`）** `N:M-2(B)` 的更正與真正的殘餘控制——見下節。

**註解語言為英文**，這是量測既有慣例後的決定而非預設：四支的敘述性內容全英（`grep -c '[一-龥]'` 為 `ui-regression` 0／`pr-reviewer` 0／`lint-fix` 1／`contract-guard` 1，而那兩行是被引用的中文 commit type 與 `## 中文版` 標題字串，不是敘述）。對照 `ci.yml`（70 行中文）與 `aidlc-sync-selftest.yml`（226 行中文），本 repo 的慣例是**逐檔一致**而非全域一致，故沿用各檔自身的慣例（`team.md`「沿用既有 artifact 的格式前必須先量測既有樣本的實際慣例」）。`project.md` 的繁中強制涵蓋 `aidlc/**` 產出與 memory 層，不涵蓋程式碼註解。

## Q2=A：`N:M-2(B)` 的更正（已寫進 `contract-guard.md` 註解與此處，**未回改上游**）

`security-requirements.md:14` 逐字寫「`ci.yml` 的 `repo-contract` job 在 `push` 到 `main`／`ut` 時仍會跑（U-10a 的 `paths-ignore` 同樣不阻止合併後的 push 觸發）」。

**這句話是錯的**，本站以 `yaml.safe_load` 實查 `ci.yml` 複驗：`pull_request -> {}`（無任何過濾）、`push -> {'branches': [...], 'paths-ignore': ['aidlc/spaces/*/intents/*/sync-state.json']}`。`paths-ignore` **就在 `on.push` 上**，`pull_request` 側才是刻意留空的那一邊。合併後只動該檔的 push **根本不建立 CI run**。

**先修 MAJOR-2：影響這則 PR 的機制有三個，不是兩個，而第三個決定了答案。** 原本的殘餘控制表在問題檔（`code-generation-questions.md` Q2）有**三列**，第三列是「`ci.yml` 的 `gate` job（U-10a，讀 commit message 的 `[aidlc-sync]`）｜那是**第二層抑制**，不是控制」。本檔與 `contract-guard.md` 兩處下游轉錄**都只有兩列**——掉的正是決定 PR 層結果的那一個。

後果不只是漏寫，是**結論錯了**：原文只點名一個可達情境（「人手動開一個只改該檔的 PR」），而**對那個情境**「延後」的判定是假的。`[aidlc-sync]` 標記的唯一寫者是 `record.sh:183`，人開的 PR 沒有它 ⇒ `gate` 輸出 `is_sync=false` ⇒ 四個下游 job 的 `if: needs.gate.outputs.is_sync != 'true'` 成立 ⇒ `repo-contract` **在 PR 當下就跑**。

三個機制（複驗依據逐項回 code）：

| # | 機制 | 作用 |
| --- | --- | --- |
| 1 | 本單元的 `paths-ignore`（四支 gh-aw） | 讓 `contract-guard` 不建立 run |
| 2 | `ci.yml` 的 `on.push` `paths-ignore`（U-10a） | 讓合併後只動該檔的 push 不建立 CI run |
| 3 | `ci.yml` 的 `gate` job（U-10a） | `pull_request` 事件下讀 PR head commit 的 `[aidlc-sync]`，命中則 skip `repo-contract`。**第二層抑制，不是控制**；只對機器成立 |

殘餘涵蓋因此**依作者分流**：

| 情境 | 禁止**路徑** | 禁止**內容** |
| --- | --- | --- |
| **機器**反向 PR（有標記 ⇒ `gate` 抑制 `repo-contract`） | **涵蓋但延後**——下一次任何其他原因觸發的 CI run 才紅（`validate_no_production_config_added()` 迴圈跑的是 `git_ls_files()` 全域掃描，issue #509 後，不是 diff） | **完全沒有涵蓋** |
| **人手開**的單檔 PR（無標記 ⇒ `is_sync=false`） | **立即涵蓋，不是延後**——`repo-contract` 就在那則 PR 上跑，全域掃描當場命中 | **完全沒有涵蓋** |

禁止內容那一格兩種情境都是「沒有涵蓋，而且從來就沒有」：`validate_no_obvious_secrets()` 只迭代 `contract_files()`＝`REQUIRED_FILES` ＋ baseline record 必要檔 ＋ audit shard；本輪複驗 `grep -q "sync-state" scripts/validate_repo_contract.py` 仍**無命中**。

**殘餘風險比上游原文所述大**——不是「有一個視窗」，是內容掃描對這條路徑從來就不存在。但**這不是本單元新增的**：`sync-state.json` 由 `record.sh` 的白名單寫入，機制本身結構上寫不進憑證；缺口只在「人手動開一個只改該檔的 PR」這條路徑上——而在那條路徑上，禁止**路徑**的那一半是立即生效的，唯一真正的缺口是禁止**內容**。

**未回改 `security-requirements.md`**（已核可上游，超出授權）。登錄為 open item 指派 Bolt 1 gate。

## U-9 絆線的翻面（完成判準第 3 條）

`run-selftest-tests.py::test_the_real_repo_state_is_what_we_say_it_is` 原本刻意斷言「A-6 對真實 repo 是**紅**的、且失敗恰好是 U-10b 的八個承載體項目」，並在失敗訊息裡寫明「若你剛交付 U-10b，處置是更新預期集合，不是刪掉這條測試」。

**本單元照它自己寫的處置更新**：`paths.rc` 改斷言 `0`、失敗集合改斷言空集合，並保留（實為強化）它的用意。它現在仍是一條會紅的測試，紅燈條件只是換了：

| 觸發紅燈的動作 | 打中的斷言 |
| --- | --- |
| 有人拿掉某支承載體的 `paths-ignore`（`ci.yml` 或四支 gh-aw 的 `.md`／`.lock.yml`） | `IGNORE:<檔名>` 失敗 ⇒ rc、失敗集合、通過集合三條全紅 |
| 有人在 `.md` **增刪了這一條 glob** 卻沒重編 `.lock.yml` | `COMPILED:<名稱>` 失敗 ⇒ 同上 |
| 有人把檢查項本身拿掉（例如從 `GH_AW_CARRIERS` 移掉一支） | **只有**通過集合那條紅——`rc` 仍是 0 |
| **偵測不到**：一般性的 lock 過期（改 `types`／`permissions`／`engine`／`tools`／`timeout-minutes`／`network` 或 prompt 本文而不重編） | **無** ⇒ GitHub 會跑一份過期的 lock 而 repo 裡沒有任何東西會紅。見下方 MAJOR-3 段與交還清單第 5 項 |

**MAJOR-3：上表第 2 列原本寫的是「有人改了 `.md` 卻沒重編 `.lock.yml`」，那個範圍是假的。** `COMPILED:<名>` 的判定式是 `check-paths-relations.py` 的 `not (md_has and not lock_has)`，而 `md_has`／`lock_has` 都只是 `glob in paths_ignore_on_pull_request(...)`——**只有這一條 glob 的有無**進入比對。這是結構性的、不是覆蓋度問題：`paths_ignore_on_pull_request()` 從 frontmatter 只取 `on.pull_request.paths-ignore` 這一個清單，frontmatter 的其餘欄位與 prompt 本文根本沒有被讀出來比過。

本輪突變複驗（M-E，於**複本**上執行，另於真實 repo 暫時套用後以 md5 還原並複驗）：把 `ui-regression.md` 的 `types` 由 `[opened, synchronize, reopened]` 改為 `[..., ready_for_review, labeled]`、lock 不重編——

```
絆線測試： 1 tests, 4 checks, 0 failures
check-paths-relations.py： rc=0（16 項檢查，0 失敗）
```

GitHub 會跑一份 `types` 過期的 lock，而 repo 裡沒有任何東西會紅。已收窄絆線訊息第 (2) 條與該測試的 `@pass`，並把一般性 lock 過期登錄為 open item（交還清單第 5 項）。

### 本站自找到並修掉的一個缺陷（如實記載）

新增的第三條斷言**第一版是失效的**。它把預期的通過代號集合由 `GH_AW_CARRIERS` 產生——而那正是突變要動的常數，於是實際集合與預期集合一起縮水，斷言照樣通過。**突變驗證當場抓到**（見下表 M3 第一次），修法是把承載體清單改成**測試檔內的字面值** `EXPECTED_CARRIERS`，並就地註解寫明「這裡刻意不從 `GH_AW_CARRIERS` 產生，因為受測物就是那個常數」——本檔其餘各處（COVERAGE-1、allowlist 建構）從常數產生是對的，只有這一處必須脫鉤。這也正是 `team.md`「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試」裡的那個測試本身。

### 突變驗證（三次，每次還原複驗）

| # | 突變 | 檢查器 rc | 測試結果 |
| --- | --- | --- | --- |
| M1 | 從 `ui-regression.lock.yml` 拿掉 `paths-ignore`（lock 落後 md） | 1 | **紅**，3 條斷言失敗 |
| M2 | 從 `ui-regression.md` 拿掉 `paths-ignore`（md 落後 lock） | 1 | **紅**，3 條斷言失敗 |
| M3（第一次） | 從 `GH_AW_CARRIERS` 移掉 `ui-regression` | **0** | **綠——漏抓**（缺陷已修，見上） |
| M3（修後重驗） | 同上 | **0** | **紅**，恰好 1 條失敗＝通過集合那條 |
| **M-E**（本輪新增） | `ui-regression.md` 的 `types` 由 `[opened, synchronize, reopened]` 改為多加 `ready_for_review, labeled`，**lock 不重編** | **0** | **綠——這是真實缺口，不是待修的漏抓**。絆線輸出 `1 tests, 4 checks, 0 failures`。已收窄敘述並登錄（MAJOR-3） |
| — | 四個突變檔各 `diff` 對備份 | — | 全部 clean，無殘留（M-E 另以 md5 逐位元複驗還原：`6aab14e3…` 還原前後相同） |

## 執行證據

全部為 **reviewer 輪之後（2026-09-06）重跑**的實際輸出，非沿用上一輪。計數與上一輪逐項相同——本輪改的是註解、訊息文字與 artifact，未動任何斷言邏輯。

| 項目 | rc | 收尾行 |
| --- | --- | --- |
| `check-paths-relations.py`（**完成判準 1 ＋ 3**） | **0** | `A-6 路徑集合關係：16 項檢查，0 失敗。` |
| `check-agentic-steps.py` | 0 | `R-1.2 代理式步驟靜態檢查：8 項檢查，0 失敗。` |
| `run-selftest-tests.py`（全跑） | 0 | `82 tests, 336 checks, 0 failures` |
| `run-selftest-fixtures.py` | 0 | `第一段 fixture 驅動：25 項檢查，0 失敗。` |
| `scripts/validate_repo_contract.py` | 0 | `Cloud-360 repository contract validation passed.` |
| `scripts/validate_env_contract.py` | 0 | `Cloud-360 environment configuration contract validation passed.` |

**其餘單元套件未被波及**（全部實跑，非推論）：

| 套件 | rc | 收尾行 |
| --- | --- | --- |
| `aidlc-sync-map/run-fixtures.py` | 0 | `全數通過。` |
| `aidlc-sync-block/run-fixtures.py` | 0 | `全數通過。` |
| `aidlc-sync-board/run-stub-tests.py` | 0 | `31 tests, 173 checks, 0 failures` |
| `aidlc-sync-record/run-stub-tests.py` | 0 | `31 tests, 231 checks, 0 failures` |
| `aidlc-sync-notify/run-stub-tests.py` | 0 | `35 tests, 381 checks, 0 failures` |
| `aidlc-sync-forward/run-orchestration-tests.py` | 0 | `40 tests, 154 checks, 0 failures` |
| `aidlc-sync-reconcile/run-reconcile-tests.py` | 0 | `38 tests, 210 checks, 0 failures` |
| `aidlc-sync-reverse/run-reverse-tests.py` | 0 | `39 tests, 246 checks, 0 failures` |
| `aidlc-sync-ci-guard/run-probe-tests.py` | 0 | `13 項行為測試，0 失敗。` |
| `aidlc-sync-ci-guard/check-ci-yml.py`（U-10a guard，對真實 repo） | 0 | `19 項檢查，0 失敗。` |

## 完成判準

| # | 判準 | 狀態 |
| --- | --- | --- |
| 1 | 四支的 `.md` 與 `.lock.yml` 都含該 glob 且一致 | ✅ `check-paths-relations.py` rc=0，16 項 0 失敗 |
| 2 | lock 由釘住的 v0.81.6 產生，diff 只含本單元的改動 | ✅ Step A 逐位元相同 ＋ Step C 每檔 4 行、manifest 零變動 |
| 3 | U-9 的 A-6 檢查器對真實 repo 由紅轉綠 | ✅ 同 1；絆線測試已翻面並經三次突變驗證 |
| 4 | 反向 PR 開啟後**這四支**皆未執行 | ⚠️ **本 stage 無法證明**——需一則真實反向 PR，不在授權內。列為 **Bolt 3 首次反向 PR 的實測項**（見交還清單第 4 項；判準已由「五組皆無 run」改寫為分兩句，見 MAJOR-1） |

## 留給 gate 的項目

1. **`N:M-2(B)` 的更正（Q2=A）**：`security-requirements.md:14` 的補償控制記載為誤，且真正的殘餘風險比原文大（內容掃描對 `sync-state.json` 從來不存在）。更正已寫進 `contract-guard.md` 註解與本檔，**上游未回改**。需人裁決是否要（a）擴大 `validate_no_obvious_secrets()` 的作用域至 `sync-state.json`、或（b）接受並記錄。
   **本輪修訂（MAJOR-2）**：唯一真正的缺口是禁止**內容**。禁止**路徑**在「人手開的單檔 PR」這條路徑上是**立即**涵蓋的（無 `[aidlc-sync]` 標記 ⇒ `gate` 輸出 `is_sync=false` ⇒ `repo-contract` 當場執行），先前把機器情境的「延後」判定套到人的情境上，低估了既有涵蓋。裁決 (a) 的必要性因此比原本描述的**小**——它要補的是內容掃描，不是路徑掃描。
2. **`deploy.yml` 不在本單元範圍，但反向 PR 會觸發它（Q3=A）**：`deploy.yml:10-14` 為 `on: pull_request: types: [closed], branches: [ut]`，**無 `paths` 過濾**。反向 PR 合併 ⇒ 自架 runner 上 `timeout-minutes: 30` 的完整部署，為的是一個 JSON 欄位。**新發現，不在 `open-items.md` 的 60 項內**，需要一個看過 ADR-0008（Construction／Operations 連續、deploy-on-merge）的人決定「同步回寫該不該觸發部署」——那不是實作細節。
3. **升級 gh-aw 到 v0.86.2**：本單元刻意不夾帶（供應鏈變更：`actions/cache` v5.0.5→v6.1.0、`actions/checkout` v7.0.0→v7.0.1、`actions/setup-node` v6.4.0→v7.0.0、防火牆容器 0.27.11→0.27.44、`gh-aw-mcpg` v0.3.30→v0.4.9、`github-mcp-server` v1.4.0→v1.9.0）。依 ADR-0006 每個新 SHA 與映像都需安全審查，是獨立決策。**登錄為獨立 open item。**
   **本輪修訂（m1）**：原文寫「每檔 526 行」，**四支都不是 526，而且四者不相等**。本輪以 `gh aw` v0.86.2 在 scratchpad 的隔離樹上重編（真實 repo 未執行任何 v0.86.2 編譯），計數慣例與「每檔 4 行」那個宣稱同一把尺（`git diff --numstat` 的 added ＋ deleted）：

   | 讀法 | ui-regression | pr-reviewer | lint-fix | contract-guard |
   | --- | --- | --- | --- | --- |
   | 對 **HEAD** 的 `.md`（決策當下的狀態） | 519 | 520 | 527 | 527 |
   | 對**交付後**的 `.md`（＝Q1 選項 B 真正的代價） | 521 | 522 | 529 | 529 |

   兩種讀法相差固定的 2 行（即本單元的 `paths-ignore` 兩行）。**Q1=A 的決定不受影響**：無論取哪一列，量級都是「五百多行 vs 4 行」，且 B 的內容仍是與本單元無關的供應鏈升級。
4. **完成判準 4 的實測指派**：Bolt 3 首次反向 PR 開啟後，到 Actions 頁面確認——

   - **`ui-regression`／`pr-reviewer`／`lint-fix`／`contract-guard`：完全沒有 run 被建立**（不是「跳過」，是不存在；Actions 頁面上不會有它們的任何列）。
   - **`ci.yml`：會建立一個 run。** 預期狀態是 `gate` job 成功、輸出 `is_sync=true`，`repo-contract`／`frontend`／`backend`／`docker-build` 四個 job 標為 **Skipped**。看到這個 run 是**正確**的，不是 U-10b 失敗。
   - **`aidlc-sync-forward`：會建立一個 run**（見交還清單第 6 項）。

   **本輪修訂（MAJOR-1）**：原文把 `ci.yml` 與那四支併成一句「皆無 run 被建立（不是跳過，是不存在）」。`ci.yml` 的 `on.pull_request` 是**裸的**（實解為 `{"pull_request": null}`），所以它**會**建立 run，而四個下游 job 是**字面意義的 Skipped**——正是那句話說不會發生的「跳過 vs 不存在」。而「自然的修法」（給 `ci.yml` 的 `pull_request` 加 `paths-ignore`）被 `check-ci-yml.py` 的 **SEC-1d 硬性禁止**，兩個方向都無法滿足原句。這是完成判準 4 的**唯一**驗證方式，照原文執行會讓觀察者把一個正確的 run 讀成 U-10b 失敗。
5. **重編 lock 的操作前提，與 `COMPILED:` 偵測不到的一般性 lock 過期**：
   - 日後任何人改這四支 `.md` 的 frontmatter，必須用**與 lock 內 `compiler_version` 相同**的 gh-aw 重編，否則會夾帶供應鏈升級。**沒有任何機械檢查會擋下「用較新版本重編」**——`COMPILED:` 只驗那一條 glob，不驗 `compiler_version`。
   - **（MAJOR-3，本輪擴大）更根本的缺口**：`COMPILED:` 連「`.md` 改了沒重編」這件事本身都只涵蓋一種——`not (md_has and not lock_has)`，兩個布林值都只是「這一條 glob 在不在 `on.pull_request.paths-ignore` 裡」。改 `types`／`permissions`／`engine`／`tools`／`timeout-minutes`／`network` 或 prompt 本文而不重編，**檢查器與絆線都是綠的**（本輪突變實測：`1 tests, 4 checks, 0 failures`，`check-paths-relations.py` rc=0）。
   - **試過的收斂手段與為什麼不成立**：lock 的 `gh-aw-metadata` 帶 `frontmatter_hash` 與 `body_hash`，若能零依賴重現就能做決定性的過期偵測，不必呼叫編譯器。實測結果分兩半——
     - **`body_hash` 可以重現**：它就是 `sha256(body.lstrip("\n"))`（`body` ＝第二個 `---` 之後的全文）。四支逐一複驗**全部命中**。
     - **`frontmatter_hash` 不行。** 它對 frontmatter 的任何文字變動都敏感（只改一行註解文字即由 `804bda34…` 變為 `381ec1ed…`，加一行純註解再變為 `e1bc3699…`），所以不是解析後結構的雜湊；但它也不是 `.md` 任何一段文字的 sha256——以一個 91 字元的最小 workflow 窮舉其**全部 4,278 個連續子字串**，無任何一段的 sha256 等於它；另在真實檔上試過 70 種（frontmatter 內文／含 `---` 圍籬／各種尾綴／BOM／CRLF × sha256／sha512-256／blake2b／sha1／md5）與 44 種正規化 YAML／JSON 形式，皆無命中。結論：它是編譯器內部轉換後的產物，**零依賴重現不成立**，不硬湊。
     - **仍可行、但本單元不做**：`.md` frontmatter 的 `on:` 區塊與 `.lock.yml` 的 `on:` 區塊都是 YAML，可以逐欄比對，那能抓到本輪 M-E 那類**語意**漂移而完全不需要編譯器（抓不到純註解漂移，但純註解漂移沒有行為風險）。這是新增一項檢查、屬 U-9 檢查器的擁有範圍，**登錄給 gate 決定落點**，不由本單元夾帶。
6. **（MAJOR-4，本輪新增）`aidlc-sync-forward.yml` 在反向 PR 上會建立 run**：它的 `on.pull_request` 為 `{"types": ["opened","synchronize","closed"]}`，**無 `paths`、無 `branches`**（`aidlc-sync-forward.yml:16-20`）。所以 U-10b **之前**反向 PR 建立的是 **6** 組 run 而非 5，**之後**仍有 **2** 組而非 0。漏掉的原因是計畫的查證 1 把實測範圍限在 `.github/workflows/*.md`（只有 gh-aw），卻給了一個涵蓋純 Actions workflow 的總數——範圍錯配。
   實質問題不是算術：**沒有人問過「反向 PR 上跑一次正向同步是不是想要的」**。本輪追查該 run 的實際行為（`aidlc-sync-forward-impl.yml`，兩個 step）：checkout 用 `ref: ${{ github.event.pull_request.head.sha || github.sha }}`（`:85`）取到 PR head，orchestration 讀 HEAD commit 訊息，命中防線②（R-4.2，`:284-288`）後 `exit 0`——**在 R-2 群的反向 PR 查詢（`:291` 起）與任何看板寫入之前**。90–289 行間無任何 `gh api`／`board.sh` 呼叫（僅一行 `BOARD_SH=` 變數指派）。所以它**消耗一次 runner 與一次帶 `sync_token` 的 checkout，但不寫看板**。
   這一項**登錄，不處置**：`open-items.md` 的 **N:C-2**（Critical、未解、Bolt 2／3 gate）逐字是「`U-8` 逕自裁定反向同步『自成第三組 concurrency』，推翻已過 gate 的 `services.md:58`（與 S-B 同一組……都碰 record，不應並行）」，正是這件事的擁有者；且本單元的擁有欄逐字只寫「高成本 `on: pull_request` workflow」。**不得**自行為 `aidlc-sync-forward.yml` 加排除。
7. **（m3，本輪新增）`ci.yml:8-11` 與 `check-ci-yml.py` SEC-1d 的全稱命題**：兩處逐字宣稱 `pull_request` 側的路徑過濾「永遠不會成立／永遠不會建立」，理由是「PR 裡永遠還有別的檔案」。那對**開發者** PR 為真、對這則只有一個檔的**機器** PR 為假。本單元已在自己的四支 `.md` 補上區分子句；**`ci.yml` 與 SEC-1d 的訊息文字屬 U-10a 的產出，本單元不回改**，登錄給 gate 決定是否同步加註（純註解／訊息文字變更，不改行為）。

## 偏離 brief 之處

| 偏離 | 理由 |
| --- | --- |
| 絆線測試**多加**第三條斷言（通過代號集合逐項比對），非 brief 明列 | brief 要求「保留它的精神——仍要是一條會因為某人拿掉 `paths-ignore` 而紅的測試」。單看 `rc == 0` 做不到全部：把檢查項刪掉一樣是 rc=0（M3 實證）。第三條是補上那個洞，且它自己的第一版失效也已被突變抓到並修好 |
| **未**交付 `check-gh-aw-exclusion.py` 與 `run-gh-aw-exclusion-tests.py` | brief 逐字指示（「現在確認就是同義的……不要新寫第二支檢查器」）。本站複驗 U-9 的 12 項檢查後同意 |
| 註解用英文而非繁中 | 量測四支既有慣例後的決定，見上方 Step B 節 |
| **必測 #1～#7「各對應一次突變」實際只跑了三次**（M1／M2／M3） | **本輪補列（m4）**：這是對已核可計畫步驟 5 的偏離，先前未列進本表。替代方案是「#1–#5、#7 已由 U-9 既有測試覆蓋，本站只為未被覆蓋的 #6 新寫斷言並突變」——該替代**經 reviewer 複驗成立**，但偏離本身仍應揭露，因為未揭露的偏離會讓下一輪 reviewer 把它當成已驗證的部分而略過（`project.md` 的 `application-design:260822-ad-L2`）。本輪另加第四次突變 **M-E**（`.md` 的 `types` 漂移、lock 不重編），結果是**綠**——見 MAJOR-3 段 |
| **本輪為修正註解而重編四支 lock**，非 brief 明列 | 被改的段落全在 frontmatter 內，而 `frontmatter_hash` 對純註解變動也敏感（實測）。不重編就會親手製造 MAJOR-3 描述的漂移。重編仍用釘住的 v0.81.6，metadata 變動欄位逐檔實測為 `['frontmatter_hash']` 單一項 |
