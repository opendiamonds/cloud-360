# Code Summary — U-1 映射與解析 composite action

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-1-map-parse-action
     Generated: 2026-08-30T06:41:49Z（讀自 date -u） -->

## 建立的檔案

全部落在 `.github/actions/aidlc-sync-map/`，**本 repo 首個 composite action**（`.github/actions/` 先前不存在）。

| 檔案 | 行數 | 職責 |
| --- | --- | --- |
| `action.yml` | 85 | 介面轉接：7 inputs → 環境變數 → `map.sh` → 5 outputs 經 `$GITHUB_OUTPUT`。`using: composite`，唯一 step `shell: bash`。**未宣告任何 secret 型 input** |
| `map.sh` | 505 | 全部解析與判定邏輯。輸入**只從環境變數取**，結果寫 stdout；在 Actions 內另附加到 `$GITHUB_OUTPUT`。**不讀取任何檔案、不連網** |
| `fixtures/*.md` | 28 檔／389 行 | 純文字 fixture，逐條規則各一 |
| `run-fixtures.py` | 735 | 斷言 runner，非零 exit 表失敗 |

**修改**：`code-generation-plan.md` 的 20 個 checkbox 全數標記完成。

`git status` 確認新增只有 `.github/actions/`；未觸碰 `.github/workflows/*`、`sync-state.json`、受管區塊或 Projects API——**未越界到其他單元**。

## 關鍵實作決定

### 哨兵字串改用 `\x01`（SOH），不是設計檔舉例的 `\x00`

`tech-stack-decisions.md` 舉例以 `\x00` 承接 bash 缺少的 `null`。**該例在 bash 不可行**——bash 變數無法存放 NUL 位元組，指令替換會靜默剝除它。改用 `\x01`。

而且不只是「賭它不會出現在 markdown 裡」：`sanitise()` 在解析前把輸入中的 `\x01` **全部剝除**，使哨兵在結構上**不可能被輸入偽造**。這是 bash 能提供的最強保證，理由寫在 `map.sh:39-54`。

> 這是對設計檔的**實作層更正**（舉例不可行），不是對決定的推翻——`using: composite` ＋ `shell: bash` ＋「以哨兵承接 null」三項皆未變。

### `get_field` 的語意逐字複製自引擎正本

來源 `.claude/tools/aidlc-lib.ts:2676`：`^- \*\*field\*\*:[ \t]*(.*)$` 搭 `m` 旗標與 `.trim()`。R-1 的四條行為與該正則一一對應，對應關係寫在註解裡。[req:FR-J6] 要求的正是「語意複製」，故以正本為準而非重新發明。

### 子命令介面讓測試能直接斷言 `get_field`

`map.sh get_field <欄位>` 以 **exit 3 ＝ 缺席（`null`）／exit 0 ＋ 空 stdout ＝ 存在但空** 區分 R-1.2 與 R-1.3。這是 `business-rules.md` R-1 群明文要求的驗證方式——**不得只斷言最終 `Decision`**，因為兩者在第 1 條判定上結論相同，錯誤不會被判定結果暴露。突變驗證第 2 條實測證實了這一點（見下）。

### bash 3.2 相容

不用關聯陣列、`mapfile`、`${var^^}`。已在 macOS 內建 3.2.57 與 homebrew 5.2.37（GitHub runner 等價）**各跑一次全綠**。

## 測試覆蓋

**38 組測試、2707 個斷言、0 失敗**，wall-clock 約 15 秒。已由 orchestrator 獨立複跑確認，非僅採信實作者回報。

總函式性（`R-7`）採**完整窮舉**而非抽樣：`(6 checkbox × 2 scope)² × 3 runtime_status × 3 parked × 2 reverse_pending = 2592` 組。每組斷言不拋例外、output 恰好五個、`reason_code` 非空且在值域、`status` 在值域、`traceable_row` 與 `scope_note` 非空，且 `status != "" ⟺ reason_code == "mapped"`（**雙向**）。

### 突變驗證（4 條，全部紅燈 → 還原 → 複驗綠）

| # | 突變 | 結果 |
| --- | --- | --- |
| 1 | R-3.6 的 `' '\|'S')` 改成 `' ')`（讓 `[S]` 算動過） | 6 斷言／3 測試紅燈，含 `FR-B3 孿生：兩者 Status 相同` |
| 2 | `get_field` 缺席時回空字串（把 `null` 併進空字串） | 3 斷言／2 測試紅燈。**關鍵觀察：`test_r1_3_decision_cannot_expose_the_difference` 仍綠**——實測證實只有直接斷言 `get_field` 抓得到，`business-rules.md` 標它為安全關鍵是對的 |
| 3 | `build_field_value` 改成 naive 整串截斷 | 7 斷言／4 測試紅燈，含 `R-5.2 編號完整保留` |
| 4 | 拿掉 R-2.4 的零行下限檢查 | 6 斷言／1 測試紅燈，其中一條逐字是該規則存在的理由：`R-2.4 反例：不得靜默誤判為 Ready` |

還原後 `diff -q` 確認 `map.sh` 逐位元組回到原狀，複驗 2696／0。

## 未解決項目（誠實列出，不粉飾）

1. **`ParsedRecord.binding` 未實作**，`intents_json` 目前無消費者。上游對其來源有**兩處互相衝突**的敘述。已登錄 `open-items.md` 的 **CG:OPEN-1**，指派 Bolt 1 gate 裁決。**這是拒絕猜，不是遺漏**。
2. **`field_value` 的 `(<編號>)` 填的是 `intent_id` 而非 issue 編號**，依據 `business-logic-model.md` §步驟 3 第 2 點的逐字通式。與第 1 項同源——issue 編號在本單元不可得。
3. **`parked @ ` 後接 `parked_at_stage`（缺席時退回 `current_stage`）**。這是對兩處上游的調和：`domain-entities.md` 說該欄位「僅用於組 `field_value`」，但 `business-logic-model.md` 的通式寫 `<current_stage>`；照通式字面實作會讓 `parked_at_stage` 成為解析出來卻永不使用的死欄位。
4. **`undecidable` 的 `field_value` 輸出空字串**。ADR-0015 §14 明文「行為未定義，實作不得自行猜」，故不掰前綴。**這是「拒絕猜」而非「猜了一個空的」**，仍需 Bolt 1 gate 追認（該指標本就指名 Bolt 1 gate）。
5. **`Unparseable` 路徑的 `scope_note` ＝ `skipped-in-scope: none; out-of-scope: none`**，採 R-6.5 的字面要求（禁止空字串），非新裁決。即 `open-items.md` 的 **B:m-5**，落點 Bolt 1 gate。測試已把現況鎖住並在 docstring 標明。
6. **沒有 shellcheck**。本機未安裝，repo 亦無 shell linter（`team.md` 已載 backend 側零 linter／formatter／type checker）。`map.sh` **未經任何靜態檢查**，只有 2696 個執行期斷言。這是本單元覆蓋的真實邊界。
7. **SEC-1 的憑證樣式斷言不在本單元**（[Q2=A] 落在 U-9，Bolt 4）。這段期間該防線不存在——選項本文即已載明的代價。

> **一項實作者回報但經查不成立的**：回報稱 nfr reviewer 的 C-2（U-1 的 `[Answer]` 字母與 artifact 實作不符）尚未解決。實查 `nfr-requirements-questions.md:58` 已於 2026-08-30T05:48:54Z 由 A 更正為 C；:44 的 `[Answer]: A` 屬另一題（composite ＋ `shell: bash`），與 artifact 一致。**該項已解決，非未決。**

## Review (code-generation)

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-30T06:57:43Z
**Verdict:** READY

### 逐項發現

| # | Severity | 分類 | 位置 | 發現 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| F1 | **Major** | 新引入 | `map.sh:146-154`（`list_stages` 的 `case` 判斷） | **`## Stage Progress` 區塊邊界偵測用「前綴比對」而非「精確比對」，任何以此字串為前綴的標題都會被誤判為進入／延續真正的區塊，而 R-2.4／R-2.5 的下限檢查完全偵測不到——因為確實有非零筆 match，不是零筆。** 原始碼：`"## Stage Progress"*) in_section=1; has_section=1 ;;`——glob 的尾綴 `*` 使任何字面前綴為 `## Stage Progress` 的標題（例如歷史草稿、棄用區塊、未來若引擎改格式為逐 Bolt 標題）都會命中。**已用實際指令重現**：對下列文字餵給 `list_stages` 子命令 `bash map.sh list_stages`（`AIDLC_STATE_MD` 含兩個標題，一真一偽）：<br>`## Stage Progress Notes (deprecated draft, kept for history)`<br>`- [x] fake-decoy-stage — EXECUTE`<br>`## Stage Progress`<br>`- [ ] intent-capture — EXECUTE`<br>實際輸出為兩列：`x\tfake-decoy-stage\tEXECUTE` 與 ` \tintent-capture\tEXECUTE`——偽造區塊下的行被**靜默併入**真正的 stage 清單，且此情境下 `has_section=1`、`found=1`，R-2.4／R-2.5 兩道下限檢查都不會觸發，misparse 不會變成可觀察的失敗，與 `business-rules.md` R-2.4 自述的存在理由（「把靜默誤判變成可觀察的失敗」）直接相悖——這正是同一類風險，只是換了一個 R-2.4 抓不到的觸發方式。**檢查全部 26 個 fixture 確認無一使用非精確標題**（`grep -n "^## Stage Progress" fixtures/*.md` 25 筆全部逐字為 `## Stage Progress`，無尾綴文字），故此為現行 fixture 集合完全沒有覆蓋、且修正不會使任何既有測試變紅的一類缺口。 | 把 `case` 的模式從 `"## Stage Progress"*)` 改為精確比對整行（例如 `"## Stage Progress")`，若標題兩側可能有尾隨空白可先 `trim` 該行再比對），使區塊邊界要求逐字相等而非前綴相符；同時建議補一個 fixture 鎖住此行為（一個含有前綴相同但非精確標題的干擾區塊，斷言干擾區塊的行不進入 `STAGES`）。 |
| F2 | Minor | 新引入 | `map.sh:39-58`（`NULL_SENTINEL` 上方註解）對照 `map.sh:252-257`（實際套用點） | **「`sanitise()` 使哨兵在結構上不可能被輸入偽造」的宣稱範圍寫得比實作涵蓋的範圍寬。** 註解原文（`:52-53`）泛稱「輸入」，但實際只有 `STATE_MD="$(sanitise "${AIDLC_STATE_MD-}")"`（`:252`）套用了 `sanitise()`；`RECORD_PATH`、`RECORD_ROOT`、`WHITELIST`、`REVERSE_PENDING` 四個字串輸入（`:253-257`）**都沒有**經過 `sanitise()`。**目前不構成可利用的漏洞**——`derive_intent_id()` 與 `set_contains()` 都只做字面字串比對／子字串切割，從不與 `NULL_SENTINEL` 做相等比較，所以即使這四個輸入含 `\x01` 也不會造成哨兵被偽造成立（此點見下方「Attempted refutations」的獨立查證）。但註解的措辭會讓後續維護者誤以為這是一個涵蓋全部輸入的通用防護，而它其實只保護 `get_field()`／`STATE_MD` 這一條路徑（也是唯一真正需要防護的路徑，因為只有它會被拿去與 `NULL_SENTINEL` 比較）。 | 把註解改寫為明確限定範圍（例如「本保證只涵蓋 `state_md`——唯一會被 `get_field`／`is_null` 消費的輸入；其餘四個字串輸入不與哨兵比較，故不需要、也未套用同樣的剝除」），或為求一致性對全部字串輸入統一套用 `sanitise()`（防禦深度，非必要但更省維護者的判斷成本）。 |
| F3 | Minor | 新引入 | `code-summary.md:13`（本檔上方「建立的檔案」表格） | **自我矛盾的措辭**：「`map.sh` ... 只讀環境變數、只寫 stdout／`$GITHUB_OUTPUT`；**自身不開檔**、不連網」——附加寫入 `$GITHUB_OUTPUT`（`map.sh:301`：`printf ... >> "$GITHUB_OUTPUT"`）本身就是一次「開檔」（append 模式開啟一個真實檔案）。這不是功能缺陷——`run-fixtures.py:85` 的 `env.pop("GITHUB_OUTPUT", None)` 確保測試執行時從不觸發這個分支，`business-logic-model.md` 對「零 I/O」的原始定義本來就明確排除 `$GITHUB_OUTPUT`（「不讀檔、不呼叫 API、不寫 log」，未說「不寫任何檔案」），所以宣稱本身在**設計文件**層級是自洽的；問題只在 `code-summary.md` 這一句話把「只寫 stdout／`$GITHUB_OUTPUT`」與「自身不開檔」並列，讀起來自相矛盾。 | 把「自身不開檔」改為更精確的措辭，例如「除了 GitHub Actions 官方指定的 `$GITHUB_OUTPUT` 輸出管道外不開任何檔案」，與上一句的「只寫 stdout／`$GITHUB_OUTPUT`」呼應而非矛盾。 |
| F4 | Minor | 新引入 | `run-fixtures.py:594-647`（`_totality_case` / `test_totality`） | **總函式性測試的斷言強度是「結構完整性 ＋ 雙向蘊含式」，不釘住每個組合的具體判定值**——這本身正確對應 `business-rules.md` R-7 的字面要求（不多不少），但代表窮舉出的 2592 組裡，凡是**沒有**被任一條 R-3.x 專屬 fixture 覆蓋到的組合，其「回傳哪一個具體值」目前**沒有任何測試釘住**。已用實際指令重現一個真實可達但無專屬 fixture 的情境：**全部 in-scope stage 皆為 `checkbox` 非空值但 `in_scope` 全偽（即整個 record 目前顯示的 stage 都是 `— SKIP`，零個 in-scope stage）**——`AIDLC_STATE_MD` 內容為 `- [x] intent-capture — SKIP` ＋ `- [x] feasibility — SKIP`（`## Current Status` 的 `Current Stage: intent-capture`）餵給 `bash map.sh run`，實際輸出 `status=Ready`／`reason_code=mapped`／`traceable_row=R-3.6 no-in-scope-stage-touched`／`field_value=frozen: intent-capture (demo-intent)`——這是 R-3.6「無任何 in-scope stage 動過」的真空真值（vacuous truth）分支，**行為本身看起來正確**，但如果未來有人把這個分支改成別的 `reason_code`（例如改成 `undecidable`），`test_totality` 的雙向蘊含式檢查（`status != "" ⟺ reason_code == "mapped"`）**依然會通過**（`undecidable` 對應 `status=""`，蘊含式仍然成立），且沒有任何專屬 fixture 會抓到這個迴歸——這是一個真實存在、當前實作正確、但完全沒有測試釘住期望值的組合。 | 補一個專屬 fixture／測試（例如 `r3-6-all-out-of-scope.md`）明確斷言「record 內所有 stage 皆為 `— SKIP`」時 `status` 精確等於 `Ready`，把這個目前只靠總函式性弱斷言撐住的分支變成有專屬 example-based 覆蓋。 |



### Attempted refutations that did not hold

- **嘗試主張 `map.sh` 內部（非測試子命令介面）把 R-1.2（存在但空）與 R-1.3（缺席）混同**：不成立。逐一 grep 全部 `get_field`／`is_null`／`is_blank` 呼叫點（`map.sh:313-316`、`:367`、`:415-416`、`:432`、`:463-464`），四個欄位（`Current Stage`／`Status`／`Parked`／`Parked At Stage`）中唯一被 `business-rules.md` 標為安全關鍵的 `Parked`，在 `run_pipeline`（`:367`）與 `compose_field_value`（`:432`）兩處都正確使用 `is_blank`（同時涵蓋 R-1.2 與 R-1.3，且與判定第 1 條的語意「兩者都是『未暫停』」一致）；`current_stage`／`parked_at_stage` 在被使用前先經 `is_null` 轉換為空字串（`:415-416`），順序正確（轉換發生在 `stage_part` 賦值之前，不會洩漏原始哨兵位元組）；`runtime_status` 直接與字面 `"Completed"` 比較，無論是哨兵或空字串都正確判定為不相等。子命令介面（`main()` 的 `get_field` 分支）是**額外**的、供測試直接斷言用的介面，不是唯一做對的地方——內部路徑本來就用字串層級的 `is_null`／`is_blank` 達成相同的區分，只是不透過 exit code 表達。
- **嘗試主張 `sanitise()` 對 `RECORD_PATH`／`RECORD_ROOT`／`WHITELIST`／`REVERSE_PENDING` 未套用構成可利用的哨兵偽造漏洞**：不成立（已改列為 F2 的文件精確度問題，非安全漏洞）。`derive_intent_id()`（`:273-281`）只做前綴切割與 `${var##*/}` 取值，`set_contains()`（`:284-293`）只做逐行 `trim` 後的字面相等比較——兩者都**從未**呼叫 `is_null()` 或與 `$NULL_SENTINEL` 比較，因此就算這四個輸入含 `\x01`，也不會被誤判為「缺席」或反過來讓真正缺席的欄位被誤判為存在。哨兵偽造的唯一風險路徑是「文字被送進 `get_field()` 解析、其回傳值再與 `NULL_SENTINEL` 比較」，而這條路徑僅 `STATE_MD` 會走到，且 `STATE_MD` 確實經過 `sanitise()`。
- **嘗試主張 R-5.4（允許超過長度上限）在 `build_field_value` 中被「順手加了二次截斷」**：不成立。逐行核對 `map.sh:228-246`，budget 被 clamp 到最小 0（`:240-242`）後直接組字串並 `printf`，函式結尾沒有任何額外的 `${value:0:maxlen}` 或類似的二次截斷；`test_r5_4_over_limit_is_deliberate` 與獨立重跑的斷言（`len(d["field_value"]) > 10`）皆為真，證實超限值確實原樣輸出。
- **嘗試主張 `scope_note` 的「不排序、不去重」宣稱不實，懷疑有隱性 `sort`／`uniq`**：不成立。`compute_scope_note()`（`map.sh:194-210`）全程只用字串串接（`skipped="${skipped:+$skipped, }$slug"`），無管線、無 `sort`、無 `uniq`。**主動突變驗證**：在 `compute_scope_note` 的輸出前插入一段 `tr ',' '\n' | sort -u | paste -sd, -` 管線後重跑 `run-fixtures.py`，`test_scope_note_both_classes` 與 `test_scope_note_order_preserved_no_dedup` 立即紅燈（2 個斷言失敗），還原後複驗 2696／0 全綠，證實原始碼確實依賴「不排序不去重」這個行為且測試真的會抓到破壞它的改動。
- **嘗試主張「零 I/O」宣稱不實**：除了官方 `$GITHUB_OUTPUT` 附加寫入（設計文件已明確排除在「零 I/O」定義之外，見 F3 的討論）之外，`grep -n` 全檔搜尋重導向符號、`curl`／`wget`／`nc`／`/dev/tcp`／`source`／`cat`／`readlink`／`realpath` 等 I/O 相關字樣，命中處全部是註解文字或行內的 markdown 反引號說明，沒有一處是真正的檔案讀取或網路呼叫。宣稱成立。
- **嘗試主張 `action.yml` 的 7 個 input／5 個 output 與設計文件（`business-logic-model.md` 介面表）不符**：不成立。逐項比對名稱、`required`、`default` 三個維度，`state_md`（必填）、`intents_json`（選填，預設 `''`）、`record_path`（必填）、`record_root`（選填，預設 `''`）、`field_max_length`（選填，預設 `'50'`）、`whitelist`（選填，預設 `''`）、`reverse_pending`（選填，預設 `''`）——七項全部逐字相符；五個 output 名稱（`status`／`field_value`／`reason_code`／`traceable_row`／`scope_note`）與介面表逐字相符，且 `scope_note` 明確標注「不進 `Decision`」與設計文件一致。
- **嘗試主張「36 組測試、2696 個斷言、0 失敗」「26 檔／363 行 fixture」「wall-clock 約 15 秒」「bash 3.2.57 與 5.2.37 各跑一次全綠」等回報數字有灌水或未經複驗**：全部獨立重新執行核實，數字逐一相符（`python3 run-fixtures.py`：36 測試、2696 斷言、0 失敗；`wc -l fixtures/*.md`：26 檔、363 行；`time python3 run-fixtures.py`：15.016s wall-clock；`AIDLC_MAP_BASH=/bin/bash`（3.2.57）與 `AIDLC_MAP_BASH=/opt/homebrew/bin/bash`（5.2.37）各自重跑皆為 2696／0）。
- **嘗試主張突變驗證的 4 個案例本身可能是精心挑選、避開了測試套件真正的弱點**：以 4 個獨立設計、與實作者回報不重複的突變重新檢驗——①移除 `get_field` 的 `trim` 呼叫（13 個斷言紅燈，含 R-1.1／R-1.2／R-1.3／R-1.4／R-3.3／R-5 群多項）、②在 `compute_scope_note` 插入排序去重管線（2 個斷言紅燈）、③放寬 R-2.1 的行樣式正則以同時接受 `--` 與 `->`（7 個斷言紅燈，含 `r2-3-noise-in-section` 與 `r2-4-zero-stage-lines` 兩個依賴嚴格 em dash 匹配的 fixture）、④移除 `undecidable` 的空值短路（1 個斷言紅燈）——全部被抓到，且每次還原後以 `diff -q` 確認 `map.sh` 逐位元組回到原狀。測試套件的敏感度經得起與實作者回報不同角度的突變。

### Summary

**分類計數**：新引入 4（F1 Major、F2/F3/F4 Minor）；既存漏審 0；新設計問題 0。
**嚴重度計數**：Critical 0、Major 1、Minor 3。未達「任一 Critical 或 >2 Major」的 NOT-READY 門檻。

本單元的核心規則（R-1～R-5 群、`scope_note`、總函式性）逐條以獨立重跑的 fixture 執行、4 個自行設計的突變（另加獨立重放實作者回報的 4 個突變，合計 8 個角度）驗證，結果與回報一致且經得起挑戰；36 組測試／2696 斷言／0 失敗、26 檔／363 行 fixture、15 秒 wall-clock、bash 3.2.57 與 5.2.37 雙版本全綠等量化宣稱全數獨立複驗屬實。哨兵字串、R-1.2/R-1.3 區分、R-3.6 的「S 不算動過」、R-5.4 的刻意超限、`scope_note` 的保序不去重等本次審查重點攻擊項目全部沒有被推翻。真正找到的問題是一個未被任何既有 fixture 覆蓋的角落：`## Stage Progress` 區塊邊界判定用前綴比對而非精確比對（F1，Major），會讓字面前綴相同的異常標題把不屬於真正區塊的行靜默併入 stage 清單，且不會觸發 R-2.4／R-2.5 的既有下限檢查——這是本次審查中唯一一個「測試全綠但邏輯本身有實際可重現缺口」的發現，其餘三項（F2～F4）為文件措辭精確度與測試覆蓋深度的次要改善項，均不影響目前任何一條已核可 AC 的正確性。建議在合併前修 F1（一行 pattern 變更，且已確認修正不會使任何既有 fixture 變紅），F2～F4 可與 CG:OPEN-1／B:m-5 等既有 open items 一併排入後續小修，不需阻擋本輪交付。

VERDICT: READY


## Post-review 修正（2026-08-30T07:38:25Z）

reviewer 判 **READY**（0 Critical／1 Major／3 Minor）。READY 即可放行，但 Major 是**真實的正確性缺口**且修法只有一行，故一併修掉而非帶進 Bolt gate。**全部修正完成後才記 receipt**——受管產出的寫入若晚於 receipt 會使它失效。

| 發現 | 處置 | 驗證 |
| --- | --- | --- |
| **Major** — `list_stages` 用前綴 glob `"## Stage Progress"*`，誘餌標題 `## Stage Progress Notes (deprecated…)` 的 stage 行會靜默併進真清單；R-2.4／R-2.5 抓不到（它們檢的是「零行 match」與「無區塊」，誤匹配的 match 數非零） | 改為**精確比對**（僅容忍尾端空白），`map.sh` 內註明為什麼兩道既有下限檢查在這條路徑上恆真 | 新增 `fixtures/r2-6-decoy-section-heading.md` ＋ `test_r2_6_decoy_section_heading`。**修正前紅燈 4 個斷言、修正後全綠**，`map.sh` 以 `diff -q` 確認逐位元組還原 |
| **Minor #1** — 註解宣稱「輸入中的 `\x01` 全部剝除」，實際只有 `state_md` 經過 `sanitise` | **讓宣稱成真**（把 `sanitise` 套到全部字串輸入），而不是把註解改弱。理由：reviewer 查證目前不可利用，但下一個新增「拿某輸入與哨兵比對」的人會理所當然相信那句註解 | 全套件複跑綠 |
| **Minor #2** — 本檔敘述自相矛盾（「只寫 stdout／`$GITHUB_OUTPUT`」與「自身不開檔」並列，而附加到 `$GITHUB_OUTPUT` 本身就是開檔） | 改寫為「輸入只從環境變數取，結果寫 stdout；在 Actions 內另附加到 `$GITHUB_OUTPUT`。不讀取任何檔案、不連網」 | — |
| **Minor #3** — 總函式性只做結構與雙向蘊含斷言，「全部 stage 皆 out-of-scope」分支無專屬 fixture 釘住期望值 | 新增 `fixtures/r3-6-all-out-of-scope.md` ＋ `test_r3_6_all_stages_out_of_scope` | **如實記載：此測試修正前後皆綠**——它補的是覆蓋缺口，不是抓 bug，本來就不該出現紅→綠 |

**一項我自己的失誤**：新增的兩個測試第一版用 `r["slug"]` 取值，而 `list_stages` 回傳的是 tuple `(checkbox, slug, EXECUTE|SKIP)`，兩個測試都以 `TypeError` 爆掉。改用索引後通過。**測試腳本本身也要驗**——這正是 `project.md` 的 `application-design:260822-ad-L1` 附帶記載過的形狀。

**修正後的實測**：38 組測試、**2707 個斷言、0 失敗**（orchestrator 自行執行）。`bash -n` 語法檢查通過。
