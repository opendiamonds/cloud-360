# Code Summary — U-10a `ci.yml` 的回寫排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging
     Generated: 2026-09-05T05:01:33Z（讀自 date -u） -->

## 變更

| 檔案 | 動作 | 量 |
| --- | --- | --- |
| `.github/workflows/ci.yml` | 修改 | `git diff --numstat` 實測 **`103 0`** —— 103 行插入、**0 行刪除** |
| `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py` | 新增 | 434 行（可執行，`+x`）——文字／結構斷言 |
| `.github/actions/aidlc-sync-ci-guard/ci-jobs-golden.json` | 新增 | 141 行（NFR-C1 的變更前快照） |
| `.github/actions/aidlc-sync-ci-guard/run-probe-tests.py` | 新增 | 204 行（可執行，`+x`）——**行為測試**，iteration 2 新增 |

不新增任何依賴（`PyYAML` 為本機既有；guard 不在 CI 內執行，見下方未完成項目第 1 項）。`ci.yml` 檔名未動——它在 `validate_repo_contract.py` 的 `REQUIRED_FILES` 內，改名即紅燈。

**`0` 行刪除是 NFR-C1 的機械證據**：既有四道關卡的內容一個字都沒被碰過，四個 job 各只多了 `needs:` 與 `if:` 兩行。

### ci.yml 的四處改動

1. **`on.push.paths-ignore`** 加一條 glob `aidlc/spaces/*/intents/*/sync-state.json`。同步回寫只碰這個檔，只改它的推送**根本不建立 CI run**——開發者手上正在跑的 run 因此不會被 `cancel-in-progress` 取消。
2. **`on.pull_request` 刻意不加 `paths-ignore`**，並就地註解寫明理由：GitHub 對 `pull_request` 的路徑過濾比對的是**整個 PR 的檔案集合**、不是這一次推送的 commit，PR 裡永遠還有別的檔案，所以它永遠不成立。寫了是假保證。
3. **新增前置 `gate` job**（65 行，`permissions: contents: read`）：讀 HEAD commit 訊息判斷是否含 `[aidlc-sync]`，輸出 `is_sync`。四個既有 job 各加 `needs: gate` 與 `if: needs.gate.outputs.is_sync != 'true'`。
4. **`concurrency` 維持原樣**（不加 `github.actor`），並就地註解寫明「為什麼沒加」——見下一節。

## 本站推翻的上游前提（最重要，先讀這一節）

nfr-requirements 已核可選項 A 的**唯一依據**逐字為：「同步以 bot 身分推送，`github.actor` 與開發者不同 ⇒ 落在不同 group ⇒ `cancel-in-progress` 取消不到開發者的 run」。

**這個前提為假。** ADR-0016 §1 已把同步身分定為**擁有者帳號 token**；實測 `gh api .../actions/workflows/ci.yml/runs` 最近 8 次 run，開發者推 code 與同步機制的 `github.actor` **同為 `opendiamonds`**，分不開。

被混為一談的兩件事：U-4 的 SEC-4 設定的 `aidlc-sync` 是 **commit 的 author**；`github.actor` 由**推送用的憑證**決定，與 commit author 無關。

**為什麼上游會寫錯**：兩份已核可產出**各自都對、合起來才錯**——nfr-requirements 寫那道題時憑證身分還是 GitHub App（App 有獨立的 `[bot]` 身分），ADR-0016 後來改成擁有者 token，但沒有回頭檢查哪些設計依賴了「身分可區分」。

因此 `github.actor` **沒有**被加進 `concurrency.group`，且由 guard 的 `CONC-1` 鎖住不准加回去——加了不會讓任何 run 免於被取消，只會讓下一個讀的人以為問題已解決。

### 對已核可上游的指派（不逕自修改）

> **修訂（2026-09-05T05:28:25Z，reviewer iteration 1 Finding #1／#2）**：本段原本只點名 `stories.md` 的 [US:S-1 AC 7] 與「nfr-requirements 那道題」兩處。reviewer 指出至少還有兩處未被點名；本輪依 `project.md` 的 `units-generation:260822-ug-L1`（**按事實列舉、逐一列出它的每種表達形式與定位方式**）把全 intent 重掃一次，實得**六個未歸檔落點**——比 reviewer 報告的多兩個。以下為完整清單。

**待改寫的事實有兩個，不是一個**：

- **事實 A**——「回寫 commit 推送後，既有 `ci.yml` run 不被取消」。本站證明它只在 `push` 事件成立；`pull_request` 事件下**結構性無解**（要分辨這次 synchronize 是機器還是人造成的，所需資訊都不在事件酬載裡，而 `concurrency` 是 workflow 層、在任何 job 跑起來之前就決定）。
- **事實 B**——「`github.actor` 可用來區分同步機制與開發者」。實測為假（同為 `opendiamonds`），理由見上一節。

定位方式一律用**檔名＋行號＋該處的欄位或表格名**，不用字串（字串在六處各不相同，grep 改過的字串只會命中一處——這正是上一輪漏掉四處的原因）：

| # | 落點 | 定位 | 陳述的是 | 為什麼需要改 |
| --- | --- | --- | --- | --- |
| 1 | `inception/user-stories/stories.md:67` | [US:S-1] 的 AC 第 7 條 | 事實 A | AC 原文無條件要求「該既有 run 不被取消」 |
| 2 | `inception/units-generation/unit-of-work.md:156` | U-10a 表格的 `完成判準` 欄 | 事實 A | 逐字「既有的 `ci.yml` run 未被取消」——**這是判定本單元完成與否的正式判準**，只巡 `stories.md` 的人會漏掉它 |
| 3 | `inception/units-generation/unit-of-work.md:153` | U-10a 表格的 `擁有` 欄 | 事實 A | 逐字「使同步的回寫 commit 不觸發一輪 CI、**也不取消既有 run**」 |
| 4 | `inception/units-generation/unit-of-work-dependency.md:27` | U-10a 那一列的依賴理由 | 事實 A | 逐字「其完成判準是『回寫 commit 不取消既有 CI run』」 |
| 5 | `construction/U-10a-ci-writeback-exclusion/nfr-requirements/tech-stack-decisions.md:51` | §2 機制表的「既有 run 不被取消」列 | 事實 B | 以**已定案的設計文字**（非 Q&A 紀錄）陳述那個假前提。這是任何人查 U-10a 設計理由時**會先開的檔** |
| 6 | 同上 `:56` | §2 的「`if:` 的取值來源」段 | 事實 B | 把 `pull_request` 側 `if:` 的候選判準寫成「`github.actor` 等於 bot 身分，與 concurrency 用的是同一個訊號」，並指派 code-generation 定案——**本站即為受指派者，定案結果是該路不可用**，故此處需一併加註 |

**不需要改的落點**（列出來，避免下一個人重掃時重複判斷）：`unit-of-work-story-map.md:20`、`unit-of-work.md:83`、`unit-of-work-dependency.md:76`、`U-4/functional-design/business-rules.md:72` 與 `functional-design-questions.md:23`。**判準**：它們陳述的是「AC 7 **歸屬** U-10a」或「rev0 曾有依賴環、如何靠歸屬消環」這類**歸屬／歷史**說明，不宣稱該機制可達成，改寫 AC 後仍然成立。`archive/*.rev0.md` 為歷史版本，同樣不動。

> `unit-of-work-dependency.md:76` 為 reviewer iteration 2 Finding #4 補入。原文寫「不需要改的**三處**」，是**枚舉不窮盡**——這正是本段要防的那種「清單看起來完整而實際遺漏」。現改為以**判準**界定（歸屬／歷史類一律不需改），而非仰賴我把每一處都數對；判準可讓下一個人自行判定新遇到的落點，枚舉不行。

**建議改寫方向（事實 A）**：把「不被取消」限定於 `push` 事件，明文承認 `pull_request` 事件下已知會被取消及其結構性理由。**建議改寫方向（事實 B）**：在 `tech-stack-decisions.md` §2 就地加註該前提已被 code-generation 實測推翻，並指向本檔的「本站推翻的上游前提」一節。

**確認人：Bolt 1 gate**（U-10a 與 U-4 於該 Bolt 交付，兩者是真捆綁）。六處全部不由本站回改。

**一項支持本站結論的上游證據**（非待改落點，列出供 gate 佐證）：`construction/U-1-map-parse-action/nfr-requirements/security-requirements.md:122` 早已逐字寫著「job 層 `if:` **不能**滿足『既有 run 不被取消』（取消發生在 run 建立時，與 job 是否 skip 無關）」。也就是**上游其實已經知道** job 層 `if:` 解不了事實 A 的那一半，只是這個認知沒有傳到 `tech-stack-decisions.md` §2 的機制表。本站的結論與它一致。

**選定方案的代價，如實記載**：開發者的 PR 測試**仍會被同步回寫取消一次**，需要重跑。重疊機率不低——同步由 push／PR 事件觸發，發生在開發者剛推完 code 後幾十秒到幾分鐘內，而四個 job 要跑好幾分鐘。被否決的三案與其代價記於 `code-generation-plan.md` 與問題檔。

## 驗證（實測輸出，非宣稱）

### 兩層驗證：文字斷言 ＋ 行為測試（iteration 2 起）

**這兩層抓的是不同種類的缺陷，缺一不可。**

| | `check-ci-yml.py` | `run-probe-tests.py` |
| --- | --- | --- |
| 種類 | 文字／結構斷言 | **實際執行 probe 腳本**，斷言判定值 |
| 抓得到 | 標記漂移、`if:` 被拿掉、job 內容被改、glob 放寬 | 邏輯方向被反轉、輸入源被換掉、fail-open 失效 |
| **抓不到** | **不動任何字串、只改邏輯方向的修改** | 設定層的形狀（`paths-ignore`、`needs:`、golden） |

iteration 2 的 Finding #1 是這個區分的由來：reviewer 示範**把 `if` 的兩個分支對調**——`grep` 呼叫一個字元沒動，19 項文字檢查全綠——判定卻完全反轉，**每一顆正常開發者 commit 都會被當成同步回寫而跳過全部四道關卡**。同類的還有 `grep -qFv`、`! grep`、把輸入從 `"$message"` 換成常數。

**修法刻意不是「再多加幾條文字斷言」**（reviewer 的建議方向）。那是同一個錯誤第三次：iteration 1 加 `MARKER-1` 有洞、iteration 1 修 `MARKER-1` 仍有洞，兩次都是**拿文字斷言去抓行為缺陷**。改為換一種東西——把 probe 腳本抽出來實際跑，餵不同的 commit 訊息，斷言它吐出的 `is_sync`。行為測試對「換個寫法達成同樣邏輯」免疫，因為它量的就是邏輯本身。

實測對照（同樣四個突變，兩層各自的反應）：

| 突變 | `check-ci-yml.py` | `run-probe-tests.py` |
| --- | --- | --- |
| M12 `if` 兩個分支互換 | 19 項 **0 失敗**（全盲） | **10／11 失敗** |
| M13 `grep -qF` → `-qFv` | 19 項 **0 失敗**（全盲） | **9／11 失敗** |
| M14 加 `!` 反轉 | 19 項 **0 失敗**（全盲） | **10／11 失敗** |
| M15 輸入源換成常數 | 19 項 **0 失敗**（全盲） | **7／11 失敗** |

### 行為測試（`run-probe-tests.py`）

`python3 .github/actions/aidlc-sync-ci-guard/run-probe-tests.py` → **11 項行為測試，0 失敗**（exit 0）。

以 `id: probe` 定位受測 step，抽出其 `run:` 以 bash 執行；`push` 路徑直接餵 `$PUSH_HEAD_MESSAGE`（不需 git），`pull_request` 路徑以 PATH 前置的假 `git` 控制 `git log` 的輸出與回傳值，因此「讀得到訊息」與「讀不到（fail-open）」兩條分支都測得到。標記字串同樣**從 `record.sh` 推導**，不在第三個地方再抄一份。

涵蓋：含標記／不含標記（push 與 PR 各一組）、標記在多行訊息的第二行、空訊息、大小寫不同、git 讀取失敗的 fail-open、無 head sha、未預期事件型別，外加一條「probe 必須以 exit 0 結束」（gate 非 0 會讓四個 job 全被 skip）。

### 靜態檢查腳本

`python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py` → **19 項檢查，0 失敗**（exit 0）。

| 檢查 | 鎖住什麼 |
| --- | --- |
| `SEC-1a` | `on.push.paths-ignore` 恰有一條 |
| `SEC-1b` | 該 glob 逐字等於「由 `record.sh` 的 `STATE_FILE_NAME` 與 `record_path` regex **推導**」的值——不是本檔自抄一份路徑字面值 |
| `SEC-1c` | glob 不含 `**`（不跨目錄層級） |
| `SEC-1d` | `on.pull_request` 沒有 `paths-ignore` |
| `GATE-1` | `gate` job 存在並宣告 `is_sync` output |
| `MARKER-1` | `gate` job **實際傳給 `grep` 的引數**含 `record.sh` 的 `SYNC_MARKER`（**本輪新增；iteration 1 後改寫，見下方修正記錄**） |
| `CONC-1` | `concurrency.group` 不含 `github.actor` |
| `NEEDS:*`／`IF:*`（各 4） | 四個 job 的 `needs: gate` 與 `if:` |
| `NFR-C1:*`（4） | 四個 job 的 `name`／`runs-on`／`steps` 與變更前逐字相同 |

**golden 快照的來源已驗**：`ci-jobs-golden.json` 的 `_source_sha256` 為 `d109965a…f825`，與 `git show HEAD:.github/workflows/ci.yml | shasum -a 256` 實測值**逐字相符**——快照確實取自變更前的 `ci.yml`，不是從已改過的檔重新產生的。

### 突變驗證（15 條，逐條 改壞 → 紅 → 還原 → 複跑綠）

| # | 突變 | 結果 |
| --- | --- | --- |
| M1 | glob 放寬成 `aidlc/**` | 紅（`SEC-1b` ＋ `SEC-1c` 兩項） |
| M2 | 拿掉 `frontend` 的 `if:` | 紅（`IF:frontend`） |
| M3 | `concurrency.group` 加回 `github.actor` | 紅（`CONC-1`） |
| M4 | `pull_request` 也加 `paths-ignore` | 紅（`SEC-1d`） |
| M5 | 改 `backend` job 的 `name` | 紅（`NFR-C1:backend`） |
| M6 | 改 `record.sh` 的 `SYNC_MARKER` | **修正前綠（缺陷）→ 修正後紅**（`MARKER-1`） |
| M7 | 改 `record.sh` 的 `STATE_FILE_NAME` | 紅（`SEC-1b`，推導值跟著變） |
| M8 | 改 `ci.yml` gate job 的 grep 字串 | 紅（`MARKER-1`，反向） |
| **M9** | grep 換成錯的標記 ＋ **同行註解**含正確標記 | **iteration 1 前綠（缺陷）→ 修正後紅** |
| **M10** | grep 換成錯的標記 ＋ **另一行字串**含正確標記 | **iteration 1 前綠（缺陷）→ 修正後紅** |
| **M11** | **整段 grep 拿掉**，只留 `UNUSED='[aidlc-sync]'` 這種沒人用的賦值 | **iteration 1 前綠（缺陷）→ 修正後紅** |

**M12–M15** 為 iteration 2 新增的**行為類**突變（分支互換、`-qFv`、`! grep`、輸入源換常數），對照表與各自的失敗數見上方「兩層驗證」一節——四條在文字檢查下全綠、在行為測試下全紅，這正是新增行為測試層的理由。

M9 為 reviewer iteration 1 Finding #3 的原始反例；M10／M11 是本站在修正前追問「這個反例的**類**是什麼」而自行構造的同類入口（`project.md`：reviewer 給的是一個反例，修之前要先問它的類，照單修一個會漏掉同類其餘）。**M11 最能說明問題的嚴重度：連比對動作本身都不存在了，舊版檢查仍是綠的。**

每條突變後皆以 `diff -q` 對原始副本確認完全還原，並複跑至綠。最終工作樹 `git diff --numstat -- .github/workflows/ci.yml` = `103 0`，`record.sh` 為未修改狀態。

### 全域 DoD

| 檢查 | 結果 |
| --- | --- |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.`（exit 0） |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.`（exit 0） |

## 關鍵實作決定

### `gate` job 取 commit 訊息分兩路（Plan Approval 裁決項 1）

- `push` 事件用 `github.event.head_commit.message`，**不 checkout**（`if: github.event_name != 'push'`）。這個 job 擋在四道關卡前面，它慢多久整條 CI 就慢多久。
- 其餘事件用 `git log -1 --format=%B ${{ github.event.pull_request.head.sha }}`，**不是 HEAD**：`pull_request` checkout 的是 `refs/pull/N/merge`，其 HEAD 是合併結果、訊息不是 PR head commit 的。`fetch-depth: 2` 才會把兩個 parent（其一即 PR head）帶下來。

### commit 訊息一律經 `env:` 傳入，不用 `${{ }}` 直接內插進 `run:`

訊息是任何有推送權的人可控的字串，內插等於把它當 shell 程式碼執行。

### 讀不到訊息時往「不是同步」判（fail-open 到「照跑 CI」）

誤判成同步 ⇒ 一顆真正的開發者 commit 完全沒被檢查；誤判成非同步 ⇒ 只是多跑一輪 CI。兩種誤判的代價不對稱，故往後者倒，並發 `::warning::`。

### `set -uo pipefail` ＋ `set +e`（與 U-4 的 `record.sh` 不同）

這個 step 的失敗代價不對稱：gate 一旦以非 0 結束，四個 job 就因 `needs` 全部被 skip。此時 run 的結論是 `failure`、gate job 自己是紅的，**PR 上看得到紅燈**；但 **merge 不會被擋**——GitHub 對 required status check 把 `skipped` 視同通過，而 `ut` 根本沒設任何 required check。所以真正的代價是「四道關卡沒跑卻仍可合併」。

因此這個 step 必須無論如何都走完並輸出一個判定。要買到這個保證，`set -uo pipefail` **不夠**：GitHub 對沒寫 `shell:` 的 `run:` 一律用 `bash -e {0}`，`-e` 從一開始就是開著的，而 `set -<flags>` 只開不關。故明寫 `set +e`。`-u` 與 `pipefail` 保留（`-u` 的中止與 errexit 無關，`set +e` 之後仍然有效）。

> **修訂（2026-09-05，F5 第四個實例）**——本節原文為：
>
> > ### `set -uo pipefail` 刻意不加 `-e`（與 U-4 的 `record.sh` 不同）
> >
> > 這個 step 的失敗代價不對稱：gate 一旦以非 0 結束，四個 job 就因 `needs` 全部被 skip，**CI 等於沒跑而且看起來是綠的**。所以它必須無論如何都走完並輸出一個判定，不能因某個非預期的非 0 回傳值中途中止。`-u` 與 `pipefail` 保留。
>
> 原文有**兩個**錯誤，都不是措辭問題：
>
> 1. **「刻意不加 `-e`」的前提不成立。** GitHub Actions 對未指定 `shell:` 的 `run:` 用 `bash -e {0}`，所以 `-e` 本來就是開的；`set -uo pipefail` 關不掉它（`set -<flags>` 只開不關）。原文宣稱的「不中止」保證從未被交付——腳本一直是在 `-e` 之下跑的。實際查證後確認**今天的程式碼仍是安全的**，因為每一個可能回非 0 的命令（`git log`、`printf | grep`）都剛好落在 `if` / `elif` 的條件位置，`-e` 對那裡不適用；但那是巧合不是設計，下一個人照著原文的說明在這裡加一行裸命令就會在普通 commit 上讓 gate 非 0 結束。
> 2. **「看起來是綠的」是誇大的。** gate job 失敗時它自己顯示為 failed、run 結論為 `failure`，PR 上是紅燈；四個 job 顯示為 skipped。查證依據：GitHub 官方文件「Successful check statuses are success, `skipped`, and neutral」，以及 `gh api repos/opendiamonds/cloud-360/branches/{ut,main}/protection` 實查——`ut` 無 `required_status_checks`，`main` 唯一的 required check 是 `Repository contract`（即 `repo-contract` job 的 `name`），而它在 gate 失敗時是 skipped、對 required check 視同通過。所以正確的說法是「紅燈看得見，但擋不住合併」，不是「看起來是綠的」。
>
> 發現時機：U-6／U-7／U-8 三支 impl workflow 的同型缺陷（F5）修完後，由使用者指出 `ci.yml` 是第四個實例。處置：`ci.yml` 補 `set +e` 並改寫該段註解；`run-probe-tests.py` 的執行器由 `bash -c`（不帶 `-e`，與 CI 相反）改為忠實的 `bash -e <檔案>`，並新增一條注入裸命令的行為迴歸測試把這條鎖住。
>
> 原文保留於上（區塊級 addendum，沿用本 record 既有的更正慣例），不做無聲改寫。**下方「Finding #5 對照表」第 5 列所記的理由與本節原文同源，一併失效**；該列屬 iteration 1 的歷史紀錄，不回改。
>
> 上一版註記（仍成立）：本節為 reviewer iteration 1 Finding #5 觸發後補寫。誠實記載：**這個理由是被問到才寫下來的**，不是當初就寫在檔案裡。但需一併更正的是——當時 reviewer「已獨立複驗此差異不造成實際錯誤」的結論，**結果對、理由錯**：它複驗的是「不加 `-e` 沒問題」，而實際情況是 `-e` 一直開著、沒出事另有原因（見上第 1 點）。

### `grep -qF` 的 `-F` 是必要的，不是風格

標記含中括號，當成 regex 會變成字元集而永遠比對不到。訊息可能多行，故用「含有」而非等於。

### `echo "判定：is_sync=${is_sync}…"` 的大括號是必要的

`$is_sync` 後面緊接全形括號時，bash 會把那個多位元組字元的位元組也讀進變數名，於是 `set -u` 判定為未設定變數、整個 step 以非 0 結束。**gate 一失敗，四個 job 因 `needs` 而全部被 skip——CI 等於沒跑。**

（2026-09-05 補註：上一節新增的 `set +e` 關掉的是 errexit，**關不掉 `-u`**——未設定變數仍會讓 step 當場中止，所以本節描述的風險真實存在，不會因為 `set +e` 而消失。已實測確認。）

## 對計畫的偏離（一項，如實揭露）

**計畫 Step 5 寫「機械斷言六件事」，實際落地七件**——多的是 `MARKER-1`。

觸發它的是突變驗證本身：M6（改 `record.sh` 的 `SYNC_MARKER`）在原版 guard 下**是綠的**。也就是說，U-4 若哪天改了標記字串，`ci.yml` 的 `gate` job 裡硬編碼的 `[aidlc-sync]` 就悄悄不再命中，每一顆同步回寫都會判 `is_sync=false`、四道關卡照跑——**這個單元等於沒做，而且不會有任何紅燈**。

這正是本 intent 反覆撞到的形狀（`project.md` 的 `functional-design:c10`；stage diary 記載三個單元的 reviewer 發現中有 3 個同形）：規則寫在文件上、看起來已經在守，實際上守不到它自己宣稱的東西。

修法沿用 `SEC-1b` 已建立的既有形狀（從 `record.sh` **推導**而非自抄一份），是同一個模式的第二次套用，不是新設計。M6／M8 雙向驗證：改任一邊都紅。

**不視為擴大已核可範圍**：guard 是 U-10a 自己的交付物，此改動只讓它守住本單元原本就宣稱要守的東西。仍列此段供 gate 覆核。reviewer iteration 1 獨立審查此點，結論一致（見其 "Attempted refutations" 第 9 條）。

### `MARKER-1` 第一版自己就有它要防的那個洞（reviewer iteration 1 Finding #3）

**第一版的實作是對 `gate` job 全部 `run:` 文字做子字串比對**（`expected_marker in probe`）。這只證明「這個字串出現在腳本的某處」，**不證明「它是被拿去比對的東西」**。reviewer 實測攻破，本站在修正前追問「這個反例的類是什麼」，另構造出兩個同類入口，三者皆能讓舊版通過而機制實際失效：

| 反例 | 手法 | 舊版 |
| --- | --- | --- |
| M9（reviewer 提出） | grep 換成錯的標記，同一行加註解含正確標記 | 綠 |
| M10（本站補） | grep 換成錯的標記，另一行的字串含正確標記 | 綠 |
| M11（本站補） | **整段 grep 拿掉**，只留沒人用的 `UNUSED='[aidlc-sync]'` | 綠 |

**M11 是最難堪也最說明問題的一個：連比對動作本身都不存在了，檢查仍報通過。** 這正是 `MARKER-1` 被引入要防的那類靜默失效——它自己就能被同一種手法騙過，屬 `project.md` `functional-design:c10` 的「修正動作本身也要過這道檢查」在本站的實證。

**修法**：改為逐行 `shlex` 斷詞後抽出**實際傳給 `grep` 的引數**再比對。兩個實作細節值得記下：
- `comments=True` 讓 `#` 之後的內容自動消失——M9 因此失效。
- **必須用 `shlex.shlex(..., punctuation_chars=True)` 而非 `shlex.split()`**：後者不把 `;` `|` 當分隔符，於是 `grep -qF '[aidlc-sync]'; then` 會斷出 `[aidlc-sync];`（尾巴多一個分號），永遠比不到正確標記。這是修正過程中實測撞出來的，不是預先想到的。

**兩項刻意接受的限制**（寫進程式碼 docstring，不假裝沒有）：①樣式若寫成變數（`grep -qF "$M"`）會判紅——方向是 fail closed，安全；②grep 存在且樣式正確但結果沒被使用（例如整段被 `if false` 包住）仍會綠——靜態檢查判不了語意可達性，由 Bolt 1 的真實觸發驗證承接。

## 未完成項目（誠實列出）

1. **guard 尚未接進任何 workflow，目前完全沒有自動執行**。`grep -rn "check-ci-yml" .github/workflows/ .github/aw/` 只命中 `ci.yml:24` 的一行**註解**，無任何實際呼叫。這是 Plan Approval 裁決項 2 的結果（接進 `repo-contract` job 會變成 `ci.yml` 檢查自己——把 `if:` 改壞的那一次修改，同時就讓檢查自己被 skip 掉）。**後果要講清楚：現在它是一支要靠人記得手動跑的腳本。** 正確落點是 Bolt 1 整合驗證或另一支獨立 workflow，不在 U-10a 範圍內。**不要把「19 項全綠」誤讀成「這些設定受保護」。**
2. **本單元的真實完成判準尚未實測**。真正的驗證是「推一顆含 `[aidlc-sync]` 的 commit，觀察四道關卡有沒有跑」，需要真實 push，屬 **Bolt 1 的整合驗證範圍**。`act` 不採用——它無法重現 `paths-ignore` 與 concurrency 的平台行為。如實記載：本單元目前**只有靜態證據，沒有執行期證據**。
3. **`[aidlc-sync]` 標記可被任何有推送權的人放進自己的 commit 訊息**，藉此讓自己的 commit 整輪跳過四道關卡。這不是本單元引入的——`record.sh` 的 `SEC-2` 已就地記載同一風險——但 `gate` job 讓它多了一個生效面（PR 事件下 skip 全部四個 job）。本 repo 為 public、任何有推送權者皆可為之。**指派 Bolt 1 gate 判斷是否需要收斂**（可能手段：`gate` 額外比對 commit author 是否為 `aidlc-sync`，但那同樣可偽造，真正的收斂要靠簽章）。
4. **上游六個落點待改寫**（事實 A 四處、事實 B 兩處），見上方「對已核可上游的指派」的完整清單。確認人：Bolt 1 gate。
5. **`gate` job 為四道關卡新增一段序列前置延遲**。它只 checkout（非 `push` 事件）＋讀一行訊息，但仍是一次 runner 排隊。未實測其秒數——需要真實 run 才量得到，與第 2 項同批。
6. **golden 的 `_source_sha256` 只在產生當下被驗過一次，`main()` 從不複驗**（reviewer iteration 1 Finding #4）。`grep -n "_source_sha256" check-ci-yml.py` 只命中 `emit_golden` 內的**寫入**行。本站已手動驗過它與 `git show HEAD:` 相符（見上方驗證段），但那是一次性的人工動作；日後若有人重新產生 golden，唯一的防線是「diff 會被人看到」這條人工紀律。
   **本站選擇「記載」而非「補一道檢查」。工程理由**：要機械複驗 golden 的來源，得掃 `git log` 中 `ci.yml` 的每個版本、逐一算 sha256 比對——那需要決定「掃多深」「淺 clone 怎麼辦」「合併後 `HEAD` 前進時語意是什麼」，是一個有自己設計面的獨立機制，範圍超出本輪三項 Major 的修正。**指派 Bolt 1 gate 決定**是否要補（候選做法即上述 git 歷史掃描，它在 U-10a 合併、`HEAD` 前進之後仍然成立）。

   > **理由更正（2026-09-05，reviewer iteration 2 Finding #5）**：先前這裡援引 `project.md` 的 `functional-design:c18` 來論證不補。**那是選錯規則**——c18 管的是「對抗式審查迴圈要不要再跑一輪」，與「這次的程式改動範圍該多大」是兩個層次的決定，用審查迴圈的停止規則去包裝一個獨立的功能決策，論證比它看起來的更弱。最終處置（不修、記載、指派 gate）不變，改的是支撐它的理由。

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T05:22:28Z
**Iteration:** 1

> **本節（iteration 1）是修正前狀態的紀錄，逐字保留不改寫。** 其中的 `97 0`、`359 行`、`8 條突變` 等數字是審查當下的值，**不是現況**；現況見本檔上半部。修正結果見本節之後的「Iteration 1 修正記錄」。

### 逐項發現

| # | 嚴重度 | 檔案:行 | 發現 | 可複驗證據 | 建議修法 | 分類 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Major | `inception/units-generation/unit-of-work.md`（U-10a 列，`完成判準` 欄） | 該欄逐字為「回寫 commit 推送後，該分支上既有的 `ci.yml` run **未被取消**，且未新增一輪四個 job」——無條件敘述。人工裁決（本站）已接受 `pull_request` 事件下既有 run **會**被取消，這使該欄與 [US:S-1 AC 7] 一樣為假，且是**同一個事實的另一種表達**。本站的「對已核可上游的指派」只點名 `stories.md` 的 [US:S-1 AC 7]，未點名 `unit-of-work.md` 這一列——Bolt 1 gate 若只巡 `stories.md` 會漏掉這一處，讀者對著 `unit-of-work.md` 仍會以為完成判準是「不被取消」。`project.md` 已把「同一事實需按其在產出裡的每一種表達形式各自定位並確認」列為本 intent 反覆撞到的教訓（`units-generation:260822-ug-L1`），本處是同型再犯。 | `grep -n "U-10a" .../inception/units-generation/unit-of-work.md`（第 83 行「不擁有」欄與第 148-155 行 U-10a 表格，`完成判準` 欄第 155 行逐字如上引） | 在 `code-summary.md`／`code-generation-plan.md` 的「對已核可上游的指派」段落追加一列，明確點名 `unit-of-work.md` 該欄同樣需要 Bolt 1 gate 一併改寫（限定於 `push` 事件），不只改 `stories.md` | 新設計問題（上游傳遞缺口，非本輪修正引入） |
| 2 | Major | `construction/U-10a-ci-writeback-exclusion/nfr-requirements/tech-stack-decisions.md`（`### 2. 新機制：concurrency 分組 ＋ job 層 if:` 節） | 該節以**已定案的設計文字**（非 Q&A 紀錄）逐字寫著「`concurrency.group` 追加 `${{ github.actor }}`｜同步以 bot 身分推送，`github.actor` 與開發者不同 ⇒ 落在不同 group ⇒ `cancel-in-progress` 取消不到開發者的 run」——與本站在 `code-generation-plan.md` 開頭推翻的前提逐字相同。本站的揭露只點名「nfr-requirements 那道題」（`nfr-requirements-questions.md` 的 Q&A），未點名 `tech-stack-decisions.md` 這份正式設計文件本身；後者是任何人查證 U-10a 設計理由時會先開的檔，而它現在仍陳述一個已被本站證偽的機制為「新機制」。`grep` 顯示這句斷言在 U-10a 目錄下**恰好出現在兩處**（`tech-stack-decisions.md` 與 `nfr-requirements-questions.md`），本站只標記了其中一處。 | `grep -rln "github.actor 與開發者不同" construction/U-10a-ci-writeback-exclusion/` → 兩處命中；`sed -n '1,40p' .../nfr-requirements/tech-stack-decisions.md` 第 27-35 行可見完整段落 | 在「對已核可上游的指派」段落明列 `tech-stack-decisions.md` §2 為第二個需要 Bolt 1 gate 知情／加註的落點，不能只寫「nfr-requirements 那道題」 | 新設計問題（上游傳遞缺口，非本輪修正引入） |
| 3 | Major | `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py`（`MARKER-1` 檢查，`gate_probe_script` ＋ `expected_marker in probe`） | `MARKER-1` 對 `gate` job 全部 `run:` 文字做**純子字串比對**，不驗證該字串是否出現在**實際被執行的 grep 引數**位置。本站實測：把 `ci.yml` 的 `grep -qF '[aidlc-sync]'` 改成功能上錯誤的 `grep -qF '[aidlc-sync-x]'`，但在同一行尾加一句含正確標記的**註解**（`# NB: real marker is [aidlc-sync], unrelated comment`），guard 回報 `MARKER-1` **通過**、19 項 0 失敗——而此時 `gate` job 對任何真正的同步回寫 commit 都會判 `is_sync=false`，四道關卡照跑，排除完全失效。這正是 `MARKER-1` 被引入要防的那種「不紅燈的靜默失效」，但它自己就能被同一種手法騙過。 | 見下方「Attempted refutations」第 2 條的重現步驟與輸出（`grep -qF '[aidlc-sync-BROKEN]'  # NB: real marker is [aidlc-sync]...` → `[通過] MARKER-1`／`19 項檢查，0 失敗`） | `MARKER-1` 改為解析 `gate` job 的 `run:` 腳本，抽出實際傳給 `grep -qF` 的引數字串（或至少排除以 `#` 起始的註解行）再比對，而非對整段文字做子字串搜尋 | 新設計問題（本輪新增的 `MARKER-1` 自身缺陷，非既有程式碼問題） |
| 4 | Minor | `.github/actions/aidlc-sync-ci-guard/ci-jobs-golden.json` ＋ `check-ci-yml.py` 的 `main()` | `_source_sha256` 只在 `--emit-golden` 時被寫入，`main()` 的一般檢查路徑**從未讀取或核對**它。golden 的來源保護完全依賴「未來若有人重新產生它，diff 會被人看到」的人工紀律，腳本本身不做任何機械核對。此為既有設計已承認的限制（`emit_golden` 的註解已寫明），非本輪新引入，但值得在 gate 覆核時一併記錄，因為它意味著「golden 綁定變更前的 `ci.yml`」這件事只在**產生當下**被驗證過一次（本站已驗證 `_source_sha256` 與 `git show HEAD` 相符），日後不會再自動複驗 | `grep -n "_source_sha256" check-ci-yml.py` 只命中 `emit_golden` 內的寫入行，`main()` 內無讀取 | 若要提高保護力，可在 `main()` 內對 `GOLDEN` 檔加一個「golden 的 `_source_sha256` 對應的四個 job 內容摘要與目前 `git log` 中最近一次 `--emit-golden` 呼叫時的 `ci.yml` 一致」之類的間接稽核，或明確接受此為人工紀律並在文件多寫一句 | 既存漏審（既有設計限制，非本輪引入） |
| 5 | Minor | `.github/workflows/ci.yml`（`gate` job 的 `probe` step） | `set -uo pipefail`，缺 `-e`；U-4 的 `record.sh` 全檔用 `set -euo pipefail`。本站未發現此差異造成實際錯誤（唯一可能因此「靜默續行」的路徑是 `echo "is_sync=$is_sync" >> "$GITHUB_OUTPUT"` 失敗，而此時 gate job 已在該行之前完成所有判斷邏輯，續行與否不影響正確性），純粹是與姊妹單元 U-4 的既有慣例不一致 | `grep -n "set -" .github/workflows/ci.yml .github/actions/aidlc-sync-record/record.sh` | 若無特別理由，加上 `-e` 以與 `record.sh` 的既有慣例一致；若有意排除，於 ci.yml 就地加一句理由註解 | 既存風格不一致（不影響正確性） |

### Attempted refutations that did not hold

1. **攻擊「`github.actor` 無法區分」是否為本站自己捏造的推翻**——用 `gh api repos/opendiamonds/cloud-360/actions/workflows/ci.yml/runs --jq '...actor...'` 實際查了最近 8 次 run，`push` 與 `pull_request` 事件的 `actor` **全部**是 `opendiamonds`。雖然這些都是人工推送（同步機制尚未上線，無同步 run 可查），但同步身分依 ADR-0016 §1 為同一顆擁有者 token，`github.actor` 由推送憑證決定而非 commit author，兩者理應同為 `opendiamonds`——本站的推翻站得住。
2. **攻擊 `MARKER-1` 的子字串比對是否真能被註解騙過**——見上方 Finding #3，**攻擊成立**，改列為正式發現而非駁回。
3. **攻擊 `${is_sync}` 大括號的「必要性」宣稱是否誇大**——用 `bash -c 'set -u; is_sync=true; echo "判定：is_sync=$is_sync（測試）"'` 在 `en_US.UTF-8` 與 `C.UTF-8` locale 下重現，**兩者皆**回 `bash: is_sync�: unbound variable`（exit 127）；加大括號後 `echo "判定：is_sync=${is_sync}（測試）"` 兩種 locale 下皆正常印出。本站的宣稱屬實，不是誇大的自我表揚。
4. **攻擊 commit 訊息內容是否可能經 `echo "::warning::..."` 觸發 GitHub Actions 的 log-injection／workflow-command 注入**——逐行追蹤發現：唯一把 `$message` 原樣塞進 `echo` 的分支，是 `git log` **本身失敗**時（`fatal: bad object ...` 一類，git 自己的錯誤輸出），此時 `$message` 不是攻擊者可控的 commit 訊息內容；成功讀到訊息的那一支路徑只把 `$message` 餵給 `printf '%s\n' "$message" | grep -qF ...`（安全），從未原樣 echo。此路無法利用，攻擊不成立。
5. **攻擊「加 `gate` job 的延遲是否違反 NFR-P1（5 分鐘同步延遲上限）」**——追到 `requirements.md` NFR-P1／NFR-P3，兩者管的是 U-6／U-8 同步 workflow **自己的** concurrency group 與延遲預算，與 `ci.yml` 是不同的 workflow 檔案，`gate` job 的延遲不落在 NFR-P1 的量測範圍內。攻擊不成立。
6. **嘗試構造「`git diff --numstat` 仍是純插入，但四道關卡實質被改壞」的反例**——任何對四個既有 job 的 `steps`／`name`／`runs-on` 的修改（含插入新 step）都會被 `NFR-C1` 的 golden 逐字比對抓到（已於 M5 突變驗證）。唯一找到的理論縫隙是 workflow 層級的 `env:`／`permissions:`／`defaults:` 區塊變動不在 `GOLDEN_KEYS` 涵蓋範圍內——但這與 U-10a 自己的 `security-requirements.md` SEC-3 已明文把 NFR-C1 的具體判準窄化為「四個 job 的 name/runs-on/steps 逐字相同＋glob 不超出白名單」一致，非本輪新開的缺口，不構成新發現。
7. **攻擊「`needs: gate` 造成的單點故障是否未被揭露」**——`ci.yml` 的 `gate` job 內就地有一句英文…不，繁中註解逐字寫著「這個 job 擋在四道關卡前面……gate 一失敗，四個 job 因 `needs` 而全部被 skip——CI 等於沒跑」，此風險已被明文揭露在程式碼本身，非隱藏缺口。攻擊不成立。
8. **攻擊 `fetch-depth: 2` ＋ `github.event.pull_request.head.sha` 是否真的取得到 PR head commit 訊息**——查證 git 的 shallow-fetch 深度語意：深度以「世代」計算，一個 merge commit 的所有 parent 都算作深度 1（不論 parent 數量），故 depth=2 會把 merge commit 本身與其兩個 parent（其一即 PR head）一併帶下來。機制成立，攻擊不成立。
9. **攻擊「`MARKER-1` 是否構成未經核可的範圍擴大」**——`MARKER-1` 只加強 guard 自身的自我驗證邏輯，不改變 `ci.yml` 的任何功能行為（`ci.yml` 的 `gate` job 本來就硬編碼 `[aidlc-sync]`，與是否有 `MARKER-1` 無關）。本站對此點的自我判斷（「不視為擴大已核可範圍」）成立，除 Finding #3 指出的子字串比對缺陷外，此項本身不構成問題。

### Summary

新引入：1（Finding #3，`MARKER-1` 的子字串比對可被註解騙過）；既存漏審：1（Finding #4，golden sha256 從未被機械複驗，屬既有設計限制）；新設計問題：2（Finding #1／#2，兩處上游文件的同一失效前提，只有一部分被本站的揭露段落點名）。三項 Major 皆源於「同一個事實／同一個已知失效前提有多種表達形式，只被追蹤到其中一部分」——這正是 `project.md` 已多次記載為本 intent 反覆出現的失誤形狀。程式碼本身（`ci.yml` 的觸發設定、`gate` job 的 shell 邏輯、8 條突變驗證、`97 0` 與 `19 項 0 失敗` 的機械證據）逐項複驗**全部屬實**，`gate` job 的 fail-open 設計、commit 訊息注入防護、`${is_sync}` 大括號的必要性等本站自陳的關鍵決定也逐一複驗成立——問題不在程式碼的正確性，而在**已核可上游需要修訂之處的揭露不完整**，加上新增的 `MARKER-1` 檢查本身有一個會被同類手法（本輪新增的檢查所要防的正是這類手法）繞過的縫隙。三項 Major（>2）依規則即為 NOT-READY，即使沒有任何 Critical。

VERDICT: NOT-READY

`project.md` 要求的**六項送審前自檢**已逐項執行，結果如下（blocking，未報告不得派工）：

| # | 自檢項 | 結果 |
| --- | --- | --- |
| 1 | **可達性**——每條「偵測 X 狀態」的規則先驗 X 可達 | **抓到一項**：原設計的「用 `github.actor` 區分機器與人」不可達（實測兩者同為 `opendiamonds`），已於計畫階段推翻並改設計。`gate` job 偵測的 `[aidlc-sync]` 可達性已驗：`record.sh:183` 的 `SYNC_MARKER` 確實會被寫進回寫 commit 訊息 |
| 2 | **契約端點三問**（誰寫／誰讀／誰清；誰擁有／誰呼叫） | `is_sync`：`gate` job 寫（`$GITHUB_OUTPUT`）、四個 job 讀（`needs.gate.outputs.is_sync`）、run 結束即消滅。`SYNC_MARKER`：U-4 `record.sh` 擁有並寫、U-10a `gate` job 與 U-6 R-4.2 讀。`paths-ignore` glob：U-10a 宣告、GitHub 平台消費、guard `SEC-1b` 從 U-4 推導比對。**無懸空端點** |
| 3 | **引用逐字核對** | `record.sh:183 SYNC_MARKER="[aidlc-sync]"`、`record.sh:186 STATE_FILE_NAME="sync-state.json"`、golden `_source_sha256` vs `git show HEAD` — 三項皆開檔／實跑驗證，非憑印象 |
| 4 | **檔案集合一致性** | 本單元 `kind: packaging`，無同類姊妹單元可 diff。與同為 packaging 的 U-11 比對：兩者皆為「改既有檔＋驗證證據」，U-11 無新增檔、本單元多一支 guard（因 U-11 的兩條規則可用 `git diff --numstat` 直接判，本單元的七項不行）。差異有理由 |
| 5 | **跨檔傳播** | 本輪改動的**事實**有二：①guard 檢查數 6→7；②新增 `MARKER-1`。①的表達形式有三處——docstring「它檢查**七**件事」（已改）、docstring 條列編號（已重排 5/6/7）、本檔驗證表（已含）。`grep -rn "六件事\|六項" .github/actions/aidlc-sync-ci-guard/` **命中 1 處**（`check-ci-yml.py:21`「本條為計畫六項之外的第七項」）——經開檔判定為**刻意的歷史引用**（指向已核可計畫的原始項數），非過期殘留，保留。②已寫進 docstring、guard 程式碼、本檔三處。**另有一處未改**：`code-generation-plan.md:73` 的「機械斷言六件事」——那是已核可計畫的原文，依規則不回改，以下方 Revision 段承接 |
| 6 | **可算的數字先算再寫** | `97 0`（`git diff --numstat`）、`19 項／0 失敗`（腳本輸出）、`359`／`141`／`59` 行（`wc -l`／`awk`）、8 條突變（逐條實跑）——**全部來自實際命令輸出**，無一由直覺產生 |


---

## Iteration 1 修正記錄（lead，2026-09-05T05:31:38Z）

五項發現全部處置完畢。**逐項對照**：

| # | 嚴重度 | 處置 | 證據 |
| --- | --- | --- | --- |
| 1 | Major | **已修，且範圍比發現更大**。reviewer 點出 `unit-of-work.md` 的 `完成判準` 欄未被點名；本站依 `units-generation:260822-ug-L1` 按**事實**而非字串重掃全 intent，實得**六個**未歸檔落點（reviewer 報告 2 個）。「對已核可上游的指派」段已改寫為完整清單，含每處的**定位方式**（檔名＋行號＋欄位／表格名）與待改理由，並另列「不需要改的三處」避免下一個人重複判斷 | 見該段表格；`grep -rn -e 未被取消 -e 不被取消 -e 不得取消 -e 不取消既有` 全 intent 掃描 |
| 2 | Major | **已修，且落點比發現更多**。`tech-stack-decisions.md` 除 reviewer 指出的 `:51`（機制表）外，`:56`（「`if:` 的取值來源」段）**同樣**依賴該假前提，且它明文指派 code-generation 定案——本站即受指派者，定案結果是該路不可用。兩處皆列入清單 | `sed -n '51p;56p' .../tech-stack-decisions.md` 逐字核對 |
| 3 | Major | **已修，且修的是類不是實例**。修正前先追問「這個反例的類是什麼」，另構造 M10／M11 兩個同類入口，三者在舊版皆為綠。改為 `shlex` 斷詞後抽取**實際 grep 引數**比對。過程中實測撞出 `shlex.split()` 不切 `;` 的問題，必須改用 `punctuation_chars=True` | M9／M10／M11 三條突變現皆紅；M6／M8 迴歸仍紅；基準 19 項 0 失敗 |
| 4 | Minor | **記載，不補檢查**（理由寫進未完成項目第 6 項）：本輪的 Finding #3 正是「計畫外自加檢查、而該檢查自己有洞」的直接後果，依 `functional-design:c18` 不在同一輪再自加一道。已指派 Bolt 1 gate 決定，並附上一個在合併後仍成立的候選做法 | 未完成項目第 6 項 |
| 5 | Minor | **記載理由，不改行為**。把「為什麼刻意不加 `-e`」就地寫進 `ci.yml`（gate 一旦非 0 結束，四個 job 全 skip，CI 等於沒跑而且看起來是綠的）。誠實標註：這個理由是被問到才寫下來的，不是當初就在檔案裡 | `ci.yml` 的 `probe` step 註解；`103 0` 仍為純插入 |

**本輪改動後的機械證據**（全部重跑，非沿用）：

| 項目 | 值 |
| --- | --- |
| `git diff --numstat -- .github/workflows/ci.yml` | `103 0`（原 `97 0`；+6 行為 Finding #5 的理由註解，**仍 0 刪除**） |
| guard | `19 項檢查，0 失敗`（項數未變——`MARKER-1` 是改寫不是新增） |
| 突變驗證 | **11 條**（原 8 ＋ M9／M10／M11），逐條紅→還原→綠 |
| `check-ci-yml.py` | 415 行（原 359） |
| `gate` job | 65 行（原 59） |
| `validate_repo_contract.py` / `validate_env_contract.py` | 皆 passed |

**送審前自檢（iteration 2）**——第 5 項「跨檔傳播」按事實列舉的結果：本輪改動的事實有四個（numstat `97 0`→`103 0`、guard 行數 `359`→`415`、gate job `59`→`65` 行、突變 `8`→`11` 條）。逐一 grep 舊值，殘留**全部落在 reviewer iteration 1 報告與當輪自檢表內**——那是修正前狀態的歷史紀錄，依規則不改寫，已於該節開頭加上明確的歷史框架標註。`gate_probe_script`（已刪除的函式名）在程式碼中零殘留，僅存於 reviewer 報告的引用。

**剩餘已知缺口**（不是本輪能關的，全部登錄於「未完成項目」）：guard 未接進任何 workflow、真實完成判準未實測、`[aidlc-sync]` 可偽造、上游六處待改寫、gate job 延遲未量測、golden sha256 不自動複驗。**六項全部指派 Bolt 1 gate。**

## Review (code-generation) — Iteration 2

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T05:45:54Z
**Iteration:** 2（上限 2；本輪找到的 Major #2 依規則觸發「驗證輪不計入原始上限」，見 Summary）

### 逐項發現

| # | 嚴重度 | 檔案:行 | 發現 | 可複驗證據 | 建議修法 | 分類 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Major | `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py`（`gate_grep_patterns` ＋ `MARKER-1`） | `MARKER-1` 修正後只驗證「`record.sh` 的標記字串曾被當成 `grep` 的某個位置引數」，**不驗證比對方向、也不驗證輸入來源是否為 `$message`**。最簡單、最寫實的反例：把 `if printf '%s\n' "$message" \| grep -qF '[aidlc-sync]'; then is_sync=true; else is_sync=false; fi` 的**兩個分支互換**（`is_sync=false`／`is_sync=true` 對調）——`grep` 呼叫本身一個字元都沒動，`gate_grep_patterns` 仍正確抓到 `[aidlc-sync]`，`MARKER-1` 與其餘 18 項照樣全綠——但邏輯已完全反轉：每一顆正常開發者 commit（訊息不含標記）會被判成「同步」而**跳過全部四道關卡**，每一顆真正的同步回寫反而照跑四道關卡。另外三個同類反例（`grep -qFv`／`! grep ...`／grep 改比對常數字串 `"[aidlc-sync]"` 而非 `"$message"`，使 `is_sync` 恆為 `true`）皆各自獨立達成同樣效果。這正是 `MARKER-1` 被引入要防的那種「不紅燈的靜默失效」，但它自己就能被同一類手法（不動標記字串、只動邏輯方向或輸入來源）繞過，且不在本輪揭露的兩項刻意接受的限制之列 | 見下方「Attempted refutations」重現步驟；4 組反例（分支互換、`-qFv`、`! grep`、輸入源替換）對 `gate_grep_patterns`／`MARKER-1` 實測皆回傳「PASS」，`19 項檢查，0 失敗` | 為 `MARKER-1` 補一條機械斷言：找到 `if <含 grep 的判斷式>; then A; else B; fi` 型態時，確認 `is_sync=true` 落在 grep **成功**（非 `-v`／非 `!`）分支；且抓到的 grep 呼叫其輸入來源（管線左側或 `<<<` 右側的變數）為 `$message` 或等價的訊息變數，不是常數字面值。若判定為超出本階段可負擔的範圍，至少把「不驗證比對方向與輸入來源」列為第三項刻意接受的限制，與現有兩項並列揭露，不要讓清單顯得完整而實際遺漏 | 既存漏審（naive substring 版與本輪 shlex 重寫版皆可被此類手法繞過——不是 shlex 重寫引入的新洞；但本輪重寫聚焦於 reviewer iteration 1 給出的 M9 一類「字面標記藏在別處」反例，未推廣去問「這個修法防得住的類是什麼、防不住的類又是什麼」，因而遺漏了同源但更嚴重的一類，也未併入已揭露限制清單） |
| 2 | Major | `construction/U-10a-ci-writeback-exclusion/code-generation/code-generation-plan.md:52-60`、`93-96` | 本輪修正 Finding #1／#2 時，`code-summary.md` 的「對已核可上游的指派」段已由原本的 2 處擴充為 6 處（事實 A／事實 B 的完整拆解、逐處的檔名＋行號＋定位方式、外加「不需要改的三處」的排除清單），但**同一個 stage 目錄下的姊妹檔** `code-generation-plan.md` 的同名段落（`## 對已核可上游的指派`）與其「已知的上游開放項（列入 summary）」段完全沒有同步，仍停留在只點名 [US:S-1 AC 7] 與「nfr-requirements 那道題」的舊版本，隻字未提 `unit-of-work.md:153`／`:156`、`unit-of-work-dependency.md:27`、`tech-stack-decisions.md:56` 這四個本輪新增的落點。`code-generation-plan.md` 本身不是「上游」——它是本單元的計畫產出，是本輪修正動作理應覆蓋、卻遺漏的檔案。Bolt 1 gate 若開的是標題為「Plan」的這一份而非 `code-summary.md`，看到的待辦事項只有 2 項不是 6 項 | `wc -l code-generation-plan.md` = 96（全檔讀畢，含 `## 對已核可上游的指派` 所在的 52-60 行與「已知的上游開放項」所在的 93-96 行）；`grep -n "tech-stack-decisions.md:56\|unit-of-work.md:153\|unit-of-work-dependency.md:27" code-generation-plan.md` 零命中 | 把 `code-summary.md` 那張六列表格（或至少其摘要與定位方式）同步貼進 `code-generation-plan.md` 對應兩段；或讓其中一份改寫為單純指向另一份的「詳見 code-summary.md『對已核可上游的指派』」，避免同一個 stage 目錄下兩份文件各自宣稱是「上游待辦事項」的正式來源卻內容不一致 | **新引入**（本輪修正動作只擴充了 `code-summary.md`，未依 `project.md` 的 `units-generation:260822-ug-L1`／`application-design:260822-ad-L1`——「改動一個事實前，先問它在本站產出裡有幾種表達形式，逐一開啟確認」——對同一 stage 目錄下的姊妹檔案做同一次核對；修正前兩份文件本來是一致的（都只有 2 項），本輪修正製造了這個新的不一致） |
| 3 | Minor | `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py:201-212`（`gate_grep_patterns` 逐行 `shlex` 斷詞） | 若未來有人把 `grep` 呼叫以 `\` 續行拆成兩個物理行（常見的長行折行風格），斷詞會在含尾端 `\` 的那一行拋出 `ValueError: No escaped character` 並被 `except ValueError: continue` 吞掉——即使邏輯正確，`gate_grep_patterns` 也完全偵測不到該行的 `grep`，`MARKER-1` 會回報失敗。方向是安全的（fail closed，不會誤放行一個真正壞掉的排除機制），但會對一個功能正確、只是換了折行風格的未來修改造成令人困惑的假紅燈，且此限制未列在「已知且刻意接受的限制」docstring 裡 | harness 測試：`grep -qF \`（單獨一行，尾端反斜線）＋續行 `'[aidlc-sync]' <<< "$message"` → `gate_grep_patterns` 回傳 `[]`；同一 `grep` 呼叫若不拆行，正確回傳 `['[aidlc-sync]']` | 在 docstring 的「已知且刻意接受的限制」補一句「`grep` 呼叫若以 `\` 續行跨行拆開，本檢查偵測不到，會誤報失敗（安全方向）」；或在 `except ValueError` 分支印出一則 `::warning::` 提示斷詞失敗的行號，讓維護者能分辨「真的標記漂移」與「斷詞限制」 | 新引入（`gate_grep_patterns` 是本輪／iteration 1 修正新寫的函式；naive substring 版按整段文字子字串搜尋，沒有這個逐行斷詞的限制） |
| 4 | Minor | `inception/units-generation/unit-of-work-dependency.md:76` | 本輪聲稱「依 `units-generation:260822-ug-L1` 把全 intent 重掃一次」，但該行同樣逐字引用 AC 7 原文（「回寫 commit 不得取消既有 `ci.yml` run」），既不在本輪列出的「需要改」6 處、也不在「不需要改的三處」排除清單裡。內容上它與排除清單裡的其餘四筆同屬一類（描述 rev0 曾有依賴環、如何靠「歸屬 U-10a」消環的**歷史／歸屬**說明，不宣稱該機制可達成），不影響任何人的判斷，但使「不需要改的三處，避免下一個人重掃時重複判斷」這句話的涵蓋範圍不完全準確——下一個人重掃到這一行時，仍要重新判斷一次它算不算數 | `grep -n "回寫 commit 不得取消既有" inception/units-generation/unit-of-work-dependency.md` 命中 `:76`；`code-summary.md` 的兩份清單（6 處＋3 處排除）均未提及此行 | 把該行併入「不需要改的三處」清單（變成四處），或在清單前言加一句「僅列本輪新發現，既有的依賴環消除說明本來就不宣稱可達成，不再重複列出」以明確涵蓋範圍 | 既存漏審（重掃本身的遺漏，非本輪修正動作造成新矛盾——該行內容本身不需要改寫，只是清單枚舉不夠窮盡） |
| 5 | Minor | `code-summary.md`「未完成項目」第 6 項 | 引用 `project.md` 的 `functional-design:c18`（「判斷一個對抗式審查迴圈要不要再跑一輪，判準是新缺陷從哪來」）來論證「不在本輪為 golden `_source_sha256` 補一道複驗」，但 c18 原文談的是**審查迴圈的停止判準**，與「這次修正順手要不要多補一個已知的 Minor 技術缺口」是不同層次的工程決定——一個管「reviewer 要不要再跑一輪」，一個管「這次的程式改動範圍該多大」。用審查迴圈的停止規則去包裝一個獨立的功能決策，論證本身比它看起來的更弱。最終處置（不修、如實記載、指派 Bolt 1 gate 決定）依規則仍站得住（Minor 從不強制修），這不是要推翻決定，是指出援引的理由選錯了規則 | 逐字核對 `project.md ## Mandated` 的 `functional-design:c18` 原文，主題明確是「reviewer 輪次上限」而非「本次改動範圍」 | 若要保留「不修」的決定，直接寫工程理由（例如：golden 對應到 git 歷史中哪個 commit 需要另外設計核對機制，範圍已超出本次三項 Critical 修正）取代援引 c18 | 既存漏審（引用選錯規則，非新缺陷，屬論證品質問題，不影響最終處置的正確性） |

### Attempted refutations that did not hold

1. **嘗試用 `eval` 間接呼叫繞過（`cmd="grep -qF [aidlc-sync-BROKEN]"; eval "$cmd"`）**——`gate_grep_patterns` 回傳 `[]`（shlex 只看到一個賦值 token，認不出內部字串裡的 `grep`），`MARKER-1` 正確回報失敗。這是誤報而非繞過（fail closed，只是拒絕了一種寫法怪異的合法程式），攻擊不成立。
2. **嘗試用變數別名呼叫（`G=grep; $G -qF "[aidlc-sync-BROKEN]"`）繞過**——`PurePosixPath(tok).name != "grep"` 對 `$G` 為真（字面不是 `grep`），偵測不到這是一次 grep 呼叫，`gate_grep_patterns` 回傳 `[]`，`MARKER-1` 正確回報失敗。同樣是誤報而非繞過，攻擊不成立。
3. **嘗試用 heredoc 包裹 grep 呼叫（`bash <<'EOS' ... grep -qF '[aidlc-sync]' ... EOS`）試圖讓斷詞失準**——`gate_grep_patterns` 逐行處理不受 heredoc 語法影響，只要 `grep` 那一行本身是完整可斷詞的一行，仍正確抓到樣式。攻擊不成立。
4. **嘗試用 `/bin/grep` 全路徑呼叫是否會被漏認**——`PurePosixPath(tok).name` 只取檔名部分，`/bin/grep` 仍被正確識別為 `grep`。攻擊不成立。
5. **嘗試用多個 `-e`／`--include=` 等選項堆疊，看能否讓迴圈邏輯抓錯 token 或漏抓**——逐一手算 `grep -e '[aidlc-sync]' -e 'other'`、`grep --include=*.txt -qF '[aidlc-sync]'` 兩種組合，`gate_grep_patterns` 的 index 推進邏輯在兩種情況下都正確落在真正的樣式 token 上。攻擊不成立。
6. **嘗試利用 `except ValueError: continue` 把一個標記錯誤的 grep 呼叫「藏」在會拋例外的一行裡，同時在另一行放一個含正確標記的 decoy，看能否讓 `MARKER-1` 通過而實際 grep 呼叫是壞的**——構造「錯誤標記＋未閉合引號」的那一行本身就拋 `ValueError` 被跳過（該行的 `grep` token 連帶消失，不會被誤判成任何東西），另一行的 decoy `echo` 因為根本不含 `grep` token 也不會被誤採；最終 `gate_grep_patterns` 回傳 `[]`，`MARKER-1` 正確回報失敗。這條路徑退化成 attempt #1 的變體，沒有找到能讓「錯的 grep 呼叫被隱藏、检查仍綠」成立的組合。攻擊不成立，但也印證 Finding #3：這個 `except: continue` 分支在**沒有惡意動機、純粹是折行風格**的情況下，仍然會把一個正確的 grep 呼叫錯判為「找不到」。
7. **重新檢查 M6／M8／M9／M10／M11 五條突變是否仍如 lead 所述（紅→還原→綠）**——在 repo 工作樹上實際重跑全部五條（非讀 code-summary.md 轉述），逐條使用 `sed` 改壞、跑 guard、確認 `19 項檢查，1 失敗` 且失敗訊息指向 `MARKER-1`、`cp` 還原、`diff -q` 確認逐位元組相同、複跑確認回到 `19 項 0 失敗`。五條全部與 lead 所述一致，lead 對這五條突變的描述沒有任何誇大或錯誤。
8. **檢查 `103 0` 是否仍為純插入、四個既有 job 是否被觸及**——`git diff -- .github/workflows/ci.yml` 顯示新增的 103 行裡，唯一涉及既有 job 內容的只有 4 個 `needs:`／4 個 `if:` 共 8 行插入；其餘為新 `on.push.paths-ignore`、新 `gate` job、新註解區塊。`NFR-C1:*` 四項檢查與 `python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py` 的即時重跑皆為 `[通過]`。與 iteration 1 到本輪之間的 `97→103`（+6 行）差額逐行核對，確實只對應 Finding #5 的理由註解（`gate` job 的 `probe` step，`set -uo pipefail` 上方新增的 6 行註解），不含任何邏輯改動。攻擊不成立，`103 0` 與「四個既有 job 未被觸及」的機械證據皆屬實。
9. **檢查 golden `_source_sha256` 是否真的對得上 `HEAD` 的 `ci.yml`**——`python3 -c "..."` 讀出 golden 的 `_source_sha256` 為 `d109965a…f825`，`git show HEAD:.github/workflows/ci.yml \| shasum -a 256` 實測值逐字相符。lead 對此的宣稱屬實。

### Summary

新引入：2（Finding #2：`code-generation-plan.md` 與 `code-summary.md` 的「對已核可上游的指派」段落不同步，屬本輪修正動作本身造成的新缺口；Finding #3：`gate_grep_patterns` 對 `\` 續行的 grep 呼叫會靜默漏檢，屬本輪新寫函式的副作用）。既存漏審：3（Finding #1：`MARKER-1` 可被「分支互換」「`-v`／`!` 反轉」「輸入來源替換」等不動標記字串的手法繞過，naive 版與本輪 shlex 版皆有此洞，非本輪重寫引入但本輪本可一併發現而未發現、也未併入揭露清單；Finding #4：`unit-of-work-dependency.md:76` 未被納入排除清單，屬重掃遺漏；Finding #5：援引 `functional-design:c18` 佐證「不補檢查」的決定，規則主題與決定不完全對應，屬論證品質問題）。新設計問題：0。

程式碼與機械證據本身（`103 0`、`19 項 0 失敗`、golden sha256 相符、M6／M8／M9／M10／M11 五條突變）逐一重跑**全部屬實**，lead 對 iteration 1 三項 Major 的修正（六處落點清單、`tech-stack-decisions.md` 兩處、`shlex` 斷詞重寫）在其自陳的範圍內都站得住——這次的問題不是「lead 修錯了」，而是**修正動作本身留下了兩種新的不完整**：一種是同一個 stage 目錄下兩份文件對「上游還欠什麼」給出不同答案（Finding #2，Major，新引入），一種是為了防堵 reviewer 給出的具體反例而寫的新函式，沒有問「這個反例所屬的類，除了 reviewer 給的那幾個變形之外還有沒有更根本的變形」——本輪找到的「分支互換」正是這樣一個變形：比 M9/M10/M11 都更簡單（連 grep 呼叫本身都不用動），也更嚴重（結果是四道關卡對所有正常 commit 永久失效，而非對某一顆 commit 誤判）。

依 `project.md` 的 `application-design:c4`（驗證輪的 Critical／Major 若源自上一輪修正動作本身，不計入原始上限，須再跑一輪）：Finding #2 是明確由本輪修正動作引入的 Major，依規則**應再跑一輪**，本輪的 iteration 上限（2）不適用於這個特定判準。Finding #1 雖分類為既存漏審（非本輪修正引入），但其嚴重度與 iteration 1 的 Finding #3 同級（同屬「MARKER-1 可被繞過」這個核心關切的一部分），也應在下一輪一併處置，不宜留到 Bolt 1 才發現。

VERDICT: NOT-READY




---

## Iteration 2 修正記錄（lead，2026-09-05T05:52:27Z）

五項發現全部處置完畢。

| # | 嚴重度 | 分類 | 處置 |
| --- | --- | --- | --- |
| 1 | Major | 既存漏審 | **換一種驗證，不是多加一條斷言**。新增 `run-probe-tests.py`（204 行）：抽出 probe 腳本實際執行、斷言判定值。reviewer 的四種繞過（分支互換／`-qFv`／`! grep`／輸入換常數）在文字檢查下**全綠**，在行為測試下**全紅**（M12–M15，見上方對照表）。`check-ci-yml.py` 的 docstring 同步把「不看比對方向與輸入來源」列為第 2 項刻意接受的限制，並註明由行為測試承接 |
| 2 | Major | **新引入** | **改為單一來源，不複製表格**。`code-generation-plan.md` 的「對已核可上游的指派」與「已知的上游開放項」兩段改為指向 `code-summary.md`，並就地寫明漂移的由來。複製一份表格只會讓同一份清單有兩個副本、下次再漂移一次——根因是兩份文件都宣稱是正式來源，不是其中一份忘了更新 |
| 3 | Minor | 新引入 | `\` 續行的 `grep` 會被 `except ValueError` 靜默吞掉 → 列為 docstring 第 3 項限制，並在該分支印出行號提示，讓維護者分辨得出「標記真的漂移」與「斷詞限制」 |
| 4 | Minor | 既存漏審 | 「不需要改的三處」是**枚舉不窮盡**（漏了 `unit-of-work-dependency.md:76`）。改為以**判準**界定（歸屬／歷史類一律不需改）而非枚舉——判準能讓下一個人自行判定新遇到的落點，數數不行 |
| 5 | Minor | 既存漏審 | 援引 `functional-design:c18` 論證「不補 golden 複驗」是**選錯規則**（c18 管審查輪次，不管改動範圍）。處置不變，改寫為真正的工程理由（掃 git 歷史比對 sha256 是有自己設計面的獨立機制） |

**本輪的核心教訓**（值得帶進 stage diary）：iteration 1 加 `MARKER-1`（文字斷言）有洞；iteration 1 修 `MARKER-1`（仍是文字斷言）仍有洞；iteration 2 才看出**問題不在斷言寫得不夠細，而在種類選錯了**——拿文字斷言去抓行為缺陷，補得再多都會有下一個變形。同型失誤連續三次之後才換種類，這個延遲本身是主要成本。

**本輪改動後的機械證據**（全部重跑）：

| 項目 | 值 |
| --- | --- |
| `git diff --numstat -- .github/workflows/ci.yml` | `103 0`（**未變**——本輪沒有改 `ci.yml`，全部改在 guard 與文件） |
| `check-ci-yml.py` | `19 項檢查，0 失敗`；434 行（原 415） |
| `run-probe-tests.py` | `11 項行為測試，0 失敗`；204 行（**新增**） |
| 突變驗證 | **15 條**（M1–M11 ＋ M12–M15），M12–M15 為本輪新增的行為類突變 |
| 兩支 contract validator | 皆 passed |

**剩餘已知缺口**（不變，全部登錄於「未完成項目」、指派 Bolt 1 gate）：兩支檢查都未接進任何 workflow、真實完成判準未實測、`[aidlc-sync]` 可偽造、上游六處待改寫、gate job 延遲未量測、golden sha256 不自動複驗。


## 審查迴圈的停止決定（人工裁決，2026-09-05T06:22Z）

**停止於 iteration 2，不跑第三輪。** 依 `project.md` 的 `functional-design:c18`，判準是「新缺陷從哪來」而非「還剩幾個」：

| 輪次 | 發現 | 新引入 | 既存漏審 | 新設計問題 | 新引入佔比 |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 Major ＋ 2 Minor | 1 | 1 | 2 | **20%** |
| 2 | 2 Major ＋ 3 Minor | 2 | 3 | 0 | **40%** |

**佔比上升（20% → 40%）是停止的訊號**，不是繼續的訊號——c18 明文：該佔比若持續不降，再跑一輪的期望值是「修好 N 項、新增 0.7N 項」，應停止迴圈並把已定位的缺口寫成 open-items 帶進閘門。

**與事前承諾的關係，如實記載**：iteration 2 派工前訂定的判準是「Major 若為上一輪修正引入 → 依 `application-design:c4`，驗證輪不計入上限，再跑一輪」。iteration 2 的 Finding #2 確實是新引入的 Major，**該條件成立**。人工裁決在知情此事的前提下選擇仍然停止，理由是同時看 c18 的佔比訊號，且 iteration 2 最重的發現（Finding #1）已用**換一種驗證機制**（行為測試）根本性關閉、非補丁——兩條規則指向相反方向時，由人裁決。**這不是判準用罄後的預設放行，是一次明示的取捨。**

**帶進 Bolt 1 gate 的 open-items**：見「未完成項目」六項，全部已指派。
