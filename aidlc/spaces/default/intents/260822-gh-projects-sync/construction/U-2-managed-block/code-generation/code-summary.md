# Code Summary — U-2 受管區塊渲染與雜湊

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-2-managed-block · kind: library
     Generated: 2026-08-30T12:12:07Z（讀自 date -u） -->

## 建立的檔案

全部在 `.github/actions/aidlc-sync-block/`：

| 檔案 | 行數 | 職責 |
| --- | --- | --- |
| `action.yml` | 194 | 四個 `operation`（`render`／`parse`／`hash`／`has_marker`）的介面轉接，逐操作在 `description` 列出必要 input 與有效 output |
| `block.sh` | 623 | 全部邏輯 |
| `format-migrations.md` | 43 | 格式版本登錄表（R-4.2／R-4.3 的互鎖對象） |
| `run-fixtures.py` | 1008 | 32 個測試函式 |
| `fixtures/*.md` | 9 檔 | 3 個 golden 快照 ＋ 6 個 parse 案例 |

**U-1 的 `.github/actions/aidlc-sync-map/` 一個位元組未動**（實測 mtime 皆早於本次工作開始，且 2707 斷言複跑全綠）。

## 關鍵實作決定

### 正規化序列化的欄序沿用 `domain-entities.md` 的表順序

欄序為 `format_version, status, traceable_row, reason_category, decided_at, scope_note, rejection_closed_at`——**不是字母序、不是渲染順序**，而是 `Block` 表由上而下的順序。理由是要核對「雜湊有沒有漏欄位」時，可以把 `serialize_block` 的七行與那張表逐列並排。`run-fixtures.py` 把這個對應變成斷言（比對欄名清單），不是靠註解維持。

格式為每欄一行 `<欄名>=<跳脫後的值>`；跳脫順序 `\` → `\\`、LF → `\n`、CR → `\r`（**反斜線必須先跳脫**）。單射性：跳脫後的值不可能含 LF ⇒ 每欄恰佔一行 ⇒ 行數、欄名、順序皆固定 ⇒ 不同 `Block` 不可能得到同一序列化。這是 R-2.2 的依據，不是宣稱。

### 空字串代表 null，**不用** U-1 的 `\x01` 哨兵

逐欄查證七欄的非 null 值域都不含空字串（`traceable_row` 由 U-1 保證非空、`scope_note` 由 R-6.5 保證非空、其餘為列舉值或 ISO 時間戳），故空字串可無歧義表達 null。**與 U-1 的情形不同**——那裡「存在但空」與「缺席」都真的會出現且語意不同。已在 `block.sh` 註記：若日後有欄位允許空字串，這個等價會失效，屆時必須改哨兵，**而那是一次格式變更**。

### `has_managed_marker` 落成第四個 operation，且 `parse` 一併輸出它

同一個函式，不是第二份實作。它**刻意不看版本**（用較短的 `MARKER_SIGIL`），因為它要回答的是「這裡已經有一段別人的區塊了嗎」——版本壞掉也算有。

### `$GITHUB_OUTPUT` 的多行處理

`block_text` 用 heredoc 形式（`name<<DELIM`）而非 U-1 `emit()` 的單行 `name=value`——**後者會把換行壓成空格，區塊立刻壞掉**。已實測 heredoc 保留尾端換行。

## 測試覆蓋

**32 組測試、542 個斷言、0 失敗**（orchestrator 自行複跑確認）。以 `AIDLC_BLOCK_BASH=/bin/bash`（3.2.57）覆驗同樣全綠——bash 3.2 相容是實測的。

- **完成判準三條各有具名測試**：`test_completion_1_same_input_same_hash`／`_2_format_change_changes_hash`／`_3_parse_unmarked_body_returns_null`
- **R-2.2 逐欄位七個斷言**，且每對都選成兩個**合法**的 `Block`；另用 `check(sorted(pairs), sorted(BLOCK_FIELDS))` 鎖住不會漏欄
- **round-trip 432 組窮舉**（含前後空白、`=`／`;`／`,`、反斜線）
- R-1.5 額外機械驗證那兩個 case 真的只差一欄（`diff_keys == ["rejection_closed_at"]`）——**避免測試自己寫歪了還以為測到**

### 突變驗證（4 條，全部紅燈 → 還原 → `diff -q` → 複驗綠）

| # | 突變 | 結果 |
| --- | --- | --- |
| 1 | 拿掉 R-1.5 的 `null` 分支 | 3 斷言紅 |
| 2 | `decided_at` 移出雜湊涵蓋範圍 | 5 斷言紅 |
| 3 | 破壞 `scope_note` round-trip（`"; "` 收成 `";"`，模擬「順手整理排版」） | 19 斷言紅，round-trip 432 組中 288 組失敗 |
| 4（加做） | `has_managed_marker` 恆回 `false`（等同 ADR-0015 §6 未修的狀態） | 6 斷言紅 |

## 一項需閘門裁決的判斷性偏離

**`hash` 做成完全全函式、零驗證、永不失敗**——設計文件沒有明說 `hash` 該不該驗互斥不變式，實作者推導後選了「不驗」並寫測試鎖住。

**推理（經 orchestrator 複核，成立）**：`parse` 的輸入是**人可以編輯的** issue body，人手動刪掉 Status 那一行就會產生違反不變式的 `Block`——而那正是反向同步要**偵測**的情形（U-8 的流程是 `read_item → parse → content_hash → 比對`）。在 `hash` 硬失敗會讓一次**正常的人為編輯**變成 workflow 紅燈，直接違反 [ad:services.md] 的「機制的正常判斷不使 workflow 紅燈」。

不變式改由 `derive_block_from_decision` 在**構造上**保證，render 出來的 `Block` 恆合法，下游不需再驗。由 `test_hash_is_total_on_human_edited_block` 鎖住，並在 `block.sh` 檔頭「錯誤模型」段寫明「這一點極容易被後人好意修掉」。

**這仍是需要裁決的事項，不是既成事實。** 若閘門認為應該驗，這個決定要連同該測試一起翻掉。

## 未完成項目（誠實列出）

1. **R-3.4 的保護在 U-2 這一端只是「具備能力」，整體尚未生效**。`has_managed_marker` 提供了區分兩種 `null` 的手段，但實際的「不覆寫」行為必須由 **U-6 在寫入前呼叫它並在 `true` 時跳過**。**U-6 若沒接上，R-3.4 仍然不成立**，而本單元的測試抓不到那件事（它在 U-6 的驗證面）。已寫進 `block.sh` 註解，並列為跨單元依賴。
2. **golden 快照的首次產生本質上是套套邏輯**（用當前渲染器產生、再拿當前渲染器比對）。R-4.1 的價值在偵測**未來**的漂移，不在驗證首版正確。首版正確性由獨立的內容斷言（R-1.1～R-1.5 字串比對、round-trip、`derive` 的測試側對照實作）承擔。三個 golden 檔各 10–11 行，值得閘門親眼看一遍。
3. **ADR-0015 §10 的雜湊等價不變式本站只覆蓋 `render → parse`**。跨 GitHub 儲存與回讀那一段（markdown 是否被轉義、換行是否被正規化）落在 **U-9** 的端到端驗證，本站沒有也不能冒充。
4. **`action.yml` 未經 GitHub Actions 實際執行**。已用 PyYAML 驗過可解析，並以 `GITHUB_OUTPUT` 環境變數手動實測 `render`（多行 heredoc）與 `parse`（九個 output）的寫出格式。`inputs`／`outputs` 的接線正確性要到 U-6 真正 `uses:` 它時才會被執行期驗證。

## 附帶處理：U-1 的殘留備份檔

實作者在 U-1 目錄發現 `map.sh.bak`（20278 bytes，U-1 突變驗證的 pristine 備份），照指示沒有動它並回報。**它未被 `.gitignore` 涵蓋**（同目錄的 `__pycache__/` 有），`git add` 會一起進版控——一份 20KB 的舊版 `map.sh` 副本進 repo，正是 `team.md ## Code Style`「單一真實來源」要防的形狀。

**orchestrator 已刪除**（實測確認它是修正前的舊版，現行 `map.sh` 含 reviewer Major／Minor 的修正；刪除後 U-1 複跑 2707／0 全綠）。`__pycache__` 經 `git check-ignore` 確認已被涵蓋，不需處理。

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-30T12:24:47Z
**Iteration:** 1

### Findings

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
| --- | --- | --- | --- | --- | --- |
| 1 | **Critical** | `block.sh:487-497`（`serialize_block`／`escape_value`）＋ `format-migrations.md:26-32`（「改格式時要做的四件事」） | 新設計問題 | **R-4 三道互鎖完全不覆蓋 `content_hash` 的正規化序列化演算法（欄序、跳脫規則），只覆蓋 `render()` 產出的 markdown 文字與 `FORMAT_VERSION`／登錄表。這正是 review brief 點名要繞看看的那個洞，而且真的繞得過去。** 已用可重跑的變異測試證實：把 `serialize_block` 的 `decided_at`／`scope_note` 兩行對調（一次真實的雜湊演算法變更，`format_version`／`render()`／`parse_v1` 全部沒動），結果——(a) `test_r4_1_golden_snapshots_byte_identical` **仍綠**（golden 比對的是 `render()` 輸出，`render_block` 從不呼叫 `serialize_block`，兩者是不相交的程式碼路徑）；(b) `test_r4_2_format_version_matches_last_migration_row`／`test_r4_3_last_row_has_rebaseline_note` **仍綠**（`FORMAT_VERSION` 與 `format-migrations.md` 都沒被要求改動，因為改的不是 `render_block`／`parse_v<n>`）；(c) 唯一紅燈的是 `test_r2_1` 裡一條比對 `serialize` 輸出欄名順序與 python 端 `BLOCK_FIELDS` 常數是否相同的斷言——而這條斷言的「修法」就是把 `run-fixtures.py` 的 `BLOCK_FIELDS` 常數改成新順序。**把這個「修法」實際做下去之後，32 個測試、542 個斷言全綠、三道互鎖全綠、`FORMAT_VERSION` 仍是 1、`format-migrations.md` 一個字元未動**——而對完全相同的 `Block`（`golden-mapped.md` 的內容），`content_hash` 從 `2f1712e6…` 變成 `ed2c69b2…`（兩次實際執行 `bash block.sh hash` 的結果，見下方複驗指令）。這正是 ADR-A6 明文列為「本設計最危險的單一失誤模式」的觸發條件：下一輪反向同步（U-8）用新程式碼重新計算現有看板上每一個 item 的雜湊，與 U-4/U-6 先前寫進 `sync-state.json` 的舊雜湊逐一比對，**全部不符**，觸發整批誤判為人為變更的反向 PR 洪水——而三道互鎖全程不會亮紅燈，因為它們從設計上就沒有把 `serialize_block`／`escape_value` 納入「格式」的定義範圍。上游三份 functional-design 文件（`business-rules.md`、`domain-entities.md`、`business-logic-model.md`）全文搜尋 `serialize`／`escape`／`跳脫`／`序列化` **零命中**——正規化序列化的具體演算法是本單元（code-generation）自己發明的產物，上游從未討論它是否也該受 R-4 約束；而 code-generation 自己寫的 `format-migrations.md`「改格式時要做的四件事」第 1 步逐字只列「改 `block.sh` 的格式常數或 `render_block`／`parse_v<n>`」，同樣沒把 `serialize_block` 算進「格式」。這不是理論疑慮：連本檔自己的程式碼註解（`serialize_block` 上方的「欄位順序」小節）都在提醒「核對雜湊涵蓋範圍有沒有漏欄位」，卻完全沒提到動這個函式需要走 R-4 的三道互鎖，說明連實作者自己都沒有意識到這個函式落在互鎖之外——未來任何人為了「讀起來更順」而重排欄位、或「順手修正」跳脫規則，都會在毫無警訊的情況下讓現有 item 的雜湊全數位移。 | 把 R-4 群的三道互鎖擴大到覆蓋 `serialize_block`／`escape_value`：最小可行做法是新增一條 golden 測試——對固定的一組 `Block` 值，斷言 `content_hash` 等於一個**寫死在測試檔裡的期望 sha256 常數**（而非現在 `test_r2_1` 那種「拿 block.sh 自己的輸出去跟 python 重算一次同一份輸出」的內部一致性檢查，那種檢查對「演算法本身變了」是恆真的）。這個 golden 雜湊常數本身要能被 R-4.1／R-4.2／R-4.3 同一套機制鎖住——即：改動 `serialize_block`／`escape_value` 必須同時改這個 golden 雜湊常數，並比照 R-4.2／R-4.3 要求 `FORMAT_VERSION` bump 與 `format-migrations.md` 登錄（即使 `render()`／`parse_v<n>` 本身沒有變動）。這是本單元完成判準 2（「格式變更使雜湊改變」）目前唯一沒有具體測試撐住的方向——現有測試只驗證了「bump `format_version` 這個值本身會改變雜湊」，從未驗證「serialize 演算法變了要被攔下來」。 |
| 2 | Major | `block.sh:229-263`（`derive_block_from_decision`）＋ `code-summary.md:64`（「不變式改由 `derive_block_from_decision` 在構造上保證，render 出來的 `Block` 恆合法，下游不需再驗」） | 新設計問題 | **這句話不成立於一個具體、可重現的輸入組合：`status=""` 且 `reason_code=""` 同時成立時。** `derive_block_from_decision` 的 `else` 分支只是把 `BLOCK_REASON_CATEGORY` 設成「呼叫端傳進來的 `reason_code`」，並不檢查那個值是否真的非空；`render` 的 `main()` 對 `AIDLC_REASON_CODE` 只跑 `validate_render_value`（只擋 CR／LF／標記字首），完全沒有檢查「`status` 為空時 `reason_code` 必須非空」這條 R-1.1「或」子句賴以成立的前提。**已實測重現**：`AIDLC_STATUS="" AIDLC_REASON_CODE="" ... bash block.sh render` 以 exit 0 成功產出區塊，內文是 `- **未寫入 Status 的原因**: `（冒號後面空白）與 `- **判定時間**: `（同樣空白）——這正是 R-1.1「機制決定不寫的原因類別**與** ISO 8601 時間戳」承諾的必載內容雙雙缺席，而區塊本身完全不會標出任何錯誤，會被原樣寫進**真實** GitHub issue（U-3 的 `write_body`）。這不是「人為編輯之後才會出現的髒 Block」（那個情境 `hash` 的全函式化設計已經正確處理、有測試鎖住）——這是**呼叫端（U-6）把 `Decision` 兩個互斥欄位都餵成空字串時，`render` 自己會產出的髒區塊**，且 `render` 對這類「介面誤用而非人為編輯」的輸入，依它自己在 `validate_render_value` 上方寫的哲學（「render 的輸入來自機制自己……不可能來自人為編輯，所以違反前提就是呼叫端的 bug，屬介面誤用而非判定結果」）**本來就應該 fail fast，卻沒有**——現有的 `validate_render_value` 只檢查了 CR／LF／標記注入這兩類介面誤用，遺漏了「`status` 與 `reason_code` 恰有一個非空」這條同樣屬於「機制自己的 bug、不可能來自人為編輯」的前提。也就是說，code-summary 用來支撐「`hash` 不需要驗」這個結論的關鍵論據——「`derive_block_from_decision` 在構造上保證合法」——只對「兩者之一非空」這個常見情形成立，對「兩者皆空」這個呼叫端 wiring bug 不成立，而**這個缺口從未被文件、測試或 open-items 提及**。 | 在 `main()` 的 `render` 分支、呼叫 `derive_block_from_decision` 之前，新增一條與現有 `validate_render_value` 同哲學（機制自身的 bug、fail fast）的前提檢查：`status` 為空時 `reason_code` 必須非空（反之亦然，雖然目前呼叫慣例是兩者互斥傳遞）。這條檢查應該與 CR／LF／標記注入檢查並列，而不是留給下游（`code-summary.md` 未完成項目清單）發現。附帶：這個發現同時修正了對「hash 全函式化」偏離之推理成立性的判斷——見下方獨立判定段。 |
| 3 | Minor | `block.sh:419-421`（`parse_block` 的 `[ "$ver" -gt "$FORMAT_VERSION" ]`） | 既存漏審 | **版本標記為超大數字（超過 bash 64-bit 整數範圍）時，`[ -gt ]` 會丟出 `integer expression expected` 錯誤並印到 stderr，雖然最終仍正確以 `found=false` 收斂（靠 `set -e` 對 `&&`／`\|\|` 鏈結左側指令的豁免，以及後續 `version_is_known` 的字串比對兜底），但這是巧合式正確，不是刻意設計的邊界處理。** 已實測：`AIDLC_ISSUE_BODY` 帶 `v=99999999999999999999999999999999999999` 的合法閉合區塊，`parse` 回傳 `found=false`／`has_marker=true`（語意正確），但 stderr 印出 `block.sh: line 421: [: 99999999999999999999999999999999999999: integer expression expected`。`is_positive_integer` 只檢查字元類別（全數字、非零開頭），不限位數，也沒有測試涵蓋這類超長版本號——32 個測試中沒有一個 fixture 或案例觸及這個路徑。issue body 是人可編輯欄位，貼上或手誤造出一長串數字並非不可能，屆時 CI／workflow log 會出現一行看似「腳本壞掉」的錯誤訊息，容易誤導事後排查（尤其這類機制本來就標榜「parse 對人為編輯的輸入必須全函式、不能報錯」）。 | 在 `is_positive_integer` 加一個位數上限（例如 15 位，遠超過任何合理的 `FORMAT_VERSION`），超過上限直接判非正整數（回 `null`），避免把不受控的巨大數字餵進 `-gt` 的算術比較。 |
| 4 | Minor | `block.sh:130`（`GH_DELIM`）與 `block.sh:203-221`（`validate_render_value`） | 既存漏審 | `$GITHUB_OUTPUT` 的 heredoc 分隔符 `__AIDLC_SYNC_BLOCK_EOF__` 是寫死的固定字串，`gh_output()` 會在值含這個字串時 `fail`（拒絕寫出、非零 exit）——**已實測確認這是安全的失敗方向**（`fail closed`，不會被注入偽造的 output 鍵，見下方「Attempted refutations」），不是 review brief 點名的那種 GitHub Actions 已知洩漏／注入面。但這個檢查只發生在 `gh_output()` 內部、寫入的當下，**沒有被併入 `validate_render_value` 那組「介面誤用即 fail fast」的前置檢查**——`render` 的 stdout 那份輸出已經印出去之後，才因為 `$GITHUB_OUTPUT` 那份寫入失敗而讓整個 `render` operation 以非零 exit 收場。若 `scope_note`（目前值域是 U-1 `compute_scope_note` 拼出的 stage slug 清單，屬封閉詞彙、不含任意文字，故現實中不可達）未來被放寬成含自由文字的欄位，這條防線離「介面誤用即 fail fast」的一致性設計還差一步。 | 若 `scope_note`／`traceable_row` 等欄位未來允許自由文字輸入，把 `GH_DELIM` 字串也併入 `validate_render_value` 的黑名單清單，讓所有「機制自身輸入不合法」的判斷收斂在同一個前置檢查函式裡，而不是分散在 `validate_render_value` 與 `gh_output` 兩處。目前風險等級為 Minor，因為 scope_note 的實際值域是封閉的 stage slug 詞彙表，人類無法從外部注入這個字串。 |

**可複驗指令（供 gate 直接重跑）**：

```bash
# 1) 建立變異版本（scope_note/decided_at 對調）並「修正」測試常數以配合新順序
cp -r .github/actions/aidlc-sync-block/* <scratch>/mutated/
# 在 <scratch>/mutated/block.sh：交換 serialize_block 裡 decided_at / scope_note 兩行
# 在 <scratch>/mutated/run-fixtures.py：BLOCK_FIELDS 對應交換 decided_at / scope_note 順序
cd <scratch>/mutated && python3 run-fixtures.py   # → 32/542/0，三道互鎖全綠，FORMAT_VERSION 仍是 1

# 2) 證明同一個 Block 在兩份程式碼下雜湊不同
AIDLC_BLOCK_FORMAT_VERSION=1 AIDLC_BLOCK_STATUS="Ready" \
  AIDLC_BLOCK_TRACEABLE_ROW="R-3.6 no-in-scope-stage-touched" \
  AIDLC_BLOCK_SCOPE_NOTE="skipped-in-scope: none; out-of-scope: none" \
  bash .github/actions/aidlc-sync-block/block.sh hash        # 2f1712e6…
  bash <scratch>/mutated/block.sh hash                        # ed2c69b2…（不同）

# 3) render 雙空值產生殘缺區塊（Finding #2）
AIDLC_STATUS="" AIDLC_TRACEABLE_ROW="" AIDLC_REASON_CODE="" \
  AIDLC_SCOPE_NOTE="skipped-in-scope: none; out-of-scope: none" \
  bash .github/actions/aidlc-sync-block/block.sh render       # exit 0，兩個必載欄位皆空白

# 4) 超大版本號的 stderr 噪音（Finding #3）
AIDLC_ISSUE_BODY='<!-- aidlc-sync:begin v=99999999999999999999999999999999999999 -->
### AI-DLC 同步紀錄
- **Status**: Ready
<!-- aidlc-sync:end -->' bash .github/actions/aidlc-sync-block/block.sh parse
```

### 對「hash 全函式化」設計偏離的獨立判定

**成立，但支撐論證有一個具體、可重現的破口，需要一併修補才算完整落地。**

實作者的核心推理——「`parse` 的輸入是人可編輯的 issue body，人手動刪掉 Status 那一行會產生違反不變式的 `Block`，而這正是反向同步要偵測的情形；在 `hash` 硬失敗會讓一次正常的人為編輯變成 workflow 紅燈，直接違反 `[ad:services.md]` 的『機制的正常判斷不使 workflow 紅燈』」——這段推理本身**站得住腳**，且已用 `test_hash_is_total_on_human_edited_block` 搭配 `fixtures/body-human-edited.md`（同時具備 Status 與未寫入原因，兩者皆非空）具體驗證：hash 對這個違反不變式的真實 fixture 仍成功、且雜湊與機制自己寫的版本不同，讓 U-8 偵測得到這次人為編輯。**這部分的決定應該維持。**

但用來支撐「下游（含 `hash`）不需要再驗」這個更廣結論的論據——「不變式改由 `derive_block_from_decision` 在構造上保證，render 出來的 `Block` 恆合法」——**只驗證了不變式被違反的其中一個方向（人為編輯讓兩者都非空），沒有驗證另一個方向（呼叫端 wiring bug 讓兩者都是空字串）**。已用 Finding #2 具體重現：`status=""` 且 `reason_code=""` 同時傳入 `render` 時，`derive_block_from_decision` 不會攔下來，會安靜產出一個違反 R-1.1「或」子句的殘缺區塊並寫進真實 issue——這條路徑完全不經過人為編輯，純粹是 U-6 的呼叫端 bug，屬於 `validate_render_value` 自己劃定的「介面誤用即 fail fast」範疇，卻沒有被涵蓋。

換句話說：**「`hash` 該不該驗」這個問題的答案（不該，維持全函式）是對的，但「所以不用管」不代表「`render` 那一端不需要補一條前提檢查」——這是兩個不同層次的問題，實作者的論證把後者需要做的事，用前者的正確結論一併帶過去了。** 建議：`hash` 維持全函式化的決定與其測試不變；但 `render` 端需要按 Finding #2 補上前提檢查，讓「`derive_block_from_decision` 在構造上保證合法」這句話對兩個方向（人為編輯 vs. 呼叫端 bug）都成立，而不是只對其中一個方向成立又拿它去論證兩者。

### Attempted refutations that did not hold

1. **「正規化序列化不是單射」——嘗試構造雜湊碰撞。** 對現行（未變異）程式碼，針對跳脫規則的邊界（字面反斜線、字面 `\n`／`\r` 兩字元序列、真實 LF/CR、以上任意組合共 15 組對抗性字串）逐一呼叫 `block.sh serialize`，比對輸出：**15 組全部得到相異的序列化位元組，無碰撞**。手動驗證跳脫順序（反斜線優先於 LF/CR）在實際程式碼中確實依此順序執行（`block.sh:461-465`），這正是避免碰撞所需的順序；若順序顛倒（LF 優先），則字面 `"a\nb"`（反斜線+n 兩字元）與真實換行字元的跳脫結果會混淆——已用變異測試驗證：移除反斜線跳脫步驟後，`test_serialization_is_deterministic_and_locale_independent` 立刻紅燈（因為它的 fixture 剛好含一個字面反斜線）。**結論：R-2.2「單射」的核心論證在目前程式碼下成立，攻擊未遂。**（但見 Finding #1——單射性成立不代表「改動這個機制不需要走格式互鎖」，這是兩件不同的事。）

2. **「空字串代表 null 在某一欄實際上會混同合法值」——逐欄查證 U-1 的實際輸出。** 直接讀 `.github/actions/aidlc-sync-map/action.yml` 與 `map.sh`（本單元宣稱沿用其形狀、已通過審查、允許讀取比對）：`traceable_row` 的 `action.yml` outputs 明文「一律非空」，`map.sh` 的 9 個賦值分支（R-3.1～R-3.7、R-4.1、R-4.2）逐一檢查，全部是非空字面字串常數，無一分支可產出空字串；`scope_note` 由 `compute_scope_note()`（`map.sh:199-213`）用 `printf 'skipped-in-scope: %s; out-of-scope: %s'` 組出，`${skipped:-none}`／`${outs:-none}` 保證兩個子句永遠有內容，函式本身不可能回傳空字串。`reason_category`（六個 `ReasonCode` 字面值）、`decided_at`／`rejection_closed_at`（ISO 8601 字串，依定義非空）、`format_version`（正整數字面值）在本單元自己的程式碼裡都只被賦值為非空字面值或直接繼承上述保證。**七欄逐一查證完畢，沒有找到反例；「空字串表達 null」的等價關係在目前的呼叫鏈下成立。**

3. **「`$GITHUB_OUTPUT` 分隔符注入」——嘗試讓 `block_text` 內容偽造額外的 output 鍵。** 建構 `scope_note` 含 `GH_DELIM`（`__AIDLC_SYNC_BLOCK_EOF__`）字面值，實測 `render`：stdout 正常印出完整區塊文字，但 `gh_output()` 偵測到值含分隔符後主動 `fail`（exit 2），`$GITHUB_OUTPUT` 檔案完全沒有被寫入任何內容（未殘留半行）。**這是 fail-closed，不是可利用的注入面**——不會有偽造的 output 鍵被寫入。唯一的殘留問題記在 Finding #4（Minor，屬防禦深度而非可利用漏洞）。

4. **「`has_marker` 與 `parse` 的判定會互相矛盾」——嘗試構造 `found=true` 但 `has_marker=false`（或反之）的 body。** `MARKER_SIGIL`（`<!-- aidlc-sync:begin`）是 `MARKER_BEGIN_PREFIX`（`<!-- aidlc-sync:begin v=`）的嚴格字首，任何能讓 `parse` 判定 `in_block=1`（進而可能 `found=true`）的行必定同時含 `MARKER_SIGIL` 子字串，故 `found=true ⇒ has_marker=true` 由字串包含關係保證，無法構造反例。四個既有 fixture（`body-corrupt-version.md`／`body-future-version.md`／`body-missing-end.md`／`body-no-marker.md`）與新構造的「有 `begin` 但缺 `v=` 參數」案例（`<!-- aidlc-sync:begin -->`）皆與此推論一致（後者 `has_marker=true`、`found=false`，因為它連 `in_block=1` 都不會被觸發，直接落到函式尾端的 `return 0`）。**未找到矛盾狀態。**

5. **`action.yml` 的 inputs/outputs 與四個 operation 的實際需求。** 逐一比對 `block.sh` 讀取的 15 個 `AIDLC_*` 環境變數與 `action.yml` 的 `env:` 映射清單——**完全相同的 15 個名稱，一一對應，無缺漏、無多餘**。`action.yml` 用 PyYAML 可正常解析，`outputs:` 11 個鍵與 `block.sh` 四個 operation 實際 `emit` 的鍵集合（`block_text`；`found`／`has_marker`／七個 `block_*`；`content_hash`；`has_marker`）逐一核對一致。`operation` 為必要輸入、非法值與缺值皆已用 `test_operation_invalid_exits_nonzero`／`test_operation_missing_exits_nonzero` 驗證非零 exit。**未發現介面不一致。**

6. **「`decided_at` 只在 `status=null` 分支渲染」的 render／parse 一致性。** 手動追蹤 `derive_block_from_decision`（`status` 非空分支強制 `BLOCK_DECIDED_AT=""`）與 `render_block` 的二分支邏輯（`LABEL_DECIDED_AT` 只出現在 `else` 分支）、`parse_v1` 對 `LABEL_DECIDED_AT` 的無條件抽取（找不到該行時 `extract_label` 回空字串），三者邏輯自洽，round-trip 測試（`test_decided_at_only_in_null_status_branch`、432 組窮舉 round-trip）亦全綠。**未發現不一致。**

### Summary

**新引入：0（本次審查對象是首次送審的 code-generation 產出，沒有「上一輪修正」可比較）。既存漏審：2（Finding #3、#4，皆為 Minor，屬 code-generation 自己這輪產出內的邊界情形，非承接自更早階段）。新設計問題：2（Finding #1 Critical、Finding #2 Major，皆為本單元 code-generation 階段自己發明的機制——正規化序列化演算法與 `render` 前提檢查——所留下的缺口，上游三份 functional-design 文件從未討論過序列化演算法本身要不要受格式互鎖約束）。**

32 個測試、542 個斷言、0 失敗的宣稱**如實**（已重跑複驗）；針對單射性、`null` 等價、`$GITHUB_OUTPUT` 注入、`has_marker`／`parse` 一致性、`action.yml` 接線、`decided_at` round-trip 六個攻擊方向的嘗試均未能推翻設計，這些部分是穩固的。但 Critical #1 直接命中本單元被 ADR-A6 指派的核心設計目標本身——用實際變異測試證明「改格式（雜湊演算法）而三道互鎖都不紅」不是理論疑慮，是可以在 5 分鐘內重現的操作序列，且產生的後果（現有 item 雜湊全數位移、下一輪反向同步全數誤判為人為變更）正是 ADR-A6 明文列為最危險的單一失誤模式。Major #2 則指出支撐「`hash` 全函式化」決定的論證本身有一個未覆蓋的方向，需要在 `render` 端補一條前提檢查才算真正把「建構上保證合法」這句話做完整。兩者皆需修正後才能判 READY。

VERDICT: NOT-READY

## Post-review 修正（2026-08-30T12:33:53Z）

reviewer 判 **NOT-READY**（1 Critical／1 Major／2 Minor）。兩項主要發現我都自行複驗後確認成立，並修到「攻擊重跑會紅燈」為止。

### Critical — R-4 互鎖漏掉雜湊的實際輸入面（新設計問題）

**reviewer 的證據，我複驗成立**：三道互鎖**只看 `render()` 的 markdown 輸出**，完全沒有涵蓋 `serialize_block`／`escape_value`——而後者才是 `content_hash` 吃的東西。對調序列化的兩個欄位（一次真正的雜湊演算法變更）後，`test_r4_1`／`4_2`／`4_3` **一道都不紅**，`FORMAT_VERSION` 仍是 1、登錄表未動，而 golden Block 的雜湊改變。

**為什麼會漏**：三份 functional-design 文件中 `serialize`／`escape` 出現 **0 次**（實測 `grep -c`）——這個表面是 code-generation 為了實作 `content_hash(Block)` 而發明的中介表示，**從未被納入 ADR-A6 的紀律**。而 ADR-A6 正把「全部既有 item 雜湊一次改變 ⇒ 反向同步大規模誤判」列為最危險的失敗模式。

**修法**：新增 **R-4.4**——把 canonical serialization 與其 sha256 釘進 `serialize-golden.txt`，逐位元比對。

### 修正時實測發現的第二個缺口 — R-4.2 做不到它自己宣稱的觸發情形

`format-migrations.md` 對 R-4.2 寫的觸發情形是「**更新了快照但沒 bump 版本**」。**機制上做不到**：它只比對「`FORMAT_VERSION` 等於登錄表最後一列」，而「改 render → 更新 golden → 不 bump」這條路徑上**兩者都沒動**，故恆綠。

**實測重現**：把 `render_block` 的標題文字改一個字 → `test_r4_1` 紅 → 照著紅燈更新 golden → **全部 549 個斷言重新變綠**，版本仍是 1、登錄表未動。

**修法**：新增 **R-4.5**——把 golden 集合的合併指紋釘進登錄表。更新快照 ⇒ 必須更新登錄表 ⇒ 最後一列的版本必須等於 `FORMAT_VERSION`（R-4.2）且附非空說明（R-4.3）。**連鎖至此才閉合**，這正是 ADR-A6 指派的「機制而非流程紀律」。

### Major — `render` 對呼叫端接線 bug 不快速失敗（新引入）

`status` 與 `reason_code` **同時為空**時 `exit 0`，渲染出兩個必載欄位都空白的區塊（違反 R-1.1）並寫進真實 issue。**實測確認**（見下方指令）。

這**不是人為編輯，是呼叫端接線 bug**（U-6 沒把 `Decision` 接上）——與 `validate_render_value` 攔的是同一類問題，理應套用同一條哲學。**與 `hash` 的「不驗」不矛盾**：那裡的輸入來自人可編輯的 issue body，兩者的差別是**輸入來源**而非不變式本身。已在程式碼註解寫明這個區分。

**修法**：`render` 分支加前置條件，兩者皆空時 `exit 2` 並說明「代表呼叫端未接上 Decision」。

### 修正的驗證（攻擊重跑）

| 攻擊 | 修正前 | 修正後 |
| --- | --- | --- |
| A：對調序列化欄序 | 三道鎖**全綠** | `test_r4_4` ＋ `test_r2_1` **紅** |
| B：改 render → 更新 golden → 不 bump | **全綠**（549／0） | `test_r4_5` **紅** |
| C：`render` 兩欄皆空 | `exit 0`，寫出空白區塊 | `exit 2` ＋ 錯誤訊息 |

還原後 `diff -q` 確認 `block.sh` 逐位元回到修正版，**550 斷言／0 失敗**。

### 我自己在修正過程犯的一個錯

R-4.5 的第一版呼叫了不存在的 `migration_rows()`——實際 helper 是 `_migration_rows()` 且回傳 `(header, data)`。這是本 session **第二次**憑印象寫 helper 介面（前一次是 U-1 的 `r["slug"]`，實際是 tuple）。已記在該測試的 docstring 裡。

另附：在登錄表新增 `golden_fingerprint` 欄時，R-4.2／R-4.3 因欄索引錯位而紅燈——**這反而證明它們真的在讀那張表**，不是恆真的裝飾。索引已同步更新。

## Review (code-generation — iteration 2)

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-30T12:46:56Z
**Iteration:** 2

本輪範圍窄化為驗證 Post-review 修正三項，範圍內全部**自行重新執行**（不轉引 orchestrator 的複驗結果），並額外對 R-4.4／R-4.5 做了一次獨立的繞過嘗試。方法：在 scratchpad 建立三份獨立變異副本（欄序對調、雜湊演算法加鹽、render 標題改字），逐一跑 `python3 run-fixtures.py`，並用 Python 獨立重算 `golden_fingerprint` 與現行登錄表比對。

### 逐項判定（iteration 1 的四項發現）

| 原 # | 嚴重度 | 判定 | 我自己的複驗證據 |
| --- | --- | --- | --- |
| 1 | Critical | **已解決** | 重跑原攻擊：對調 `serialize_block` 的 `decided_at`／`scope_note` 兩行＋「修正」`BLOCK_FIELDS` 常數（與 iteration 1 的可複驗指令逐字相同）。修正前這套動作三道鎖全綠；本輪在獨立 scratch 副本上重跑，`test_r4_4_serialization_golden_byte_identical` 六個斷言全紅（3 個欄位逐位元不符＋3 個 sha256 不符），套件從 550/0 掉到 550/6。**繞過嘗試**：另外把 `content_hash()` 的輸入加一段固定鹽（`serialize_block \| printf 'SALT' \| sha256_of_stdin`，模擬「改雜湊演算法而不動序列化」），`test_r4_4` 本身維持綠（在設計上正確——R-4.4 只鎖序列化，不是雜湊演算法本身），但**既有的** `test_r2_1_hash_is_sha256_of_the_canonical_serialization`（差分驗證 `block_hash()` 等於 Python 獨立算的 `sha256(serialize 輸出)`）立刻紅燈。全檔 `grep` 未找到任何硬編碼的 64 hex 字元雜湊值——`block_hash()` 的每一處使用都是差分比較（同輸入同雜湊／異輸入異雜湊），R-2.1 是唯一同時驗證「演算法是 sha256」與「輸入是序列化位元組」的差分鎖。**結論：R-4.4（序列化欄位）＋既有 R-2.1（雜湊演算法本身）兩者合起來，對「改序列化」與「改演算法」兩個方向都無法繞過；R-4.4 單獨並不覆蓋演算法替換，但這是它的設計範圍（只管序列化），不是缺口——只要 R-2.1 沒被同時拆掉，攻擊面就是關閉的。** |
| 2（orchestrator 自行發現） | （未分級，機制性缺口） | **已解決，且鏈條確認閉合** | 重現「機制上做不到」：把 `BLOCK_HEADING` 加一個全形驚嘆號（一次真實的 render 變更），`test_r4_1` 紅；照紅燈重新產生三個 `fixtures/golden-*.md`（用 code-summary 記載的指令）；`FORMAT_VERSION`／登錄表完全未動——`test_r4_5_golden_fingerprint_matches_registry` 紅（`test_r4_2`／`test_r4_3` 維持綠，證實這兩者單獨確實抓不到這個情境，與 code-summary 的自陳一致）。**額外驗證鏈條的另一端**：對調 `serialize_block` 欄序＋正確重新產生 `serialize-golden.txt`（讓 R-4.4 變綠）、但不動登錄表——`test_r4_5` 同樣紅。**再驗證「照規矩走會不會被卡死」**：bump `FORMAT_VERSION`／`KNOWN_VERSIONS`、在登錄表新增一列並填入獨立重算的正確 `golden_fingerprint`——`test_r4_5` 轉綠（後續因為只是驗證鏈條、未真的補 `parse_v2`，`round-trip` 測試如預期紅，這是我刻意省略的步驟，不影響鏈條本身的判定）。**連鎖確認閉合：改 render 或改 serialize 任一者，都會被迫走到「更新登錄表且指紋吻合」這一步，且該步驟本身又受 R-4.2／R-4.3 的版本／說明檢查約束。** |
| 3 | Minor | **未解決（orchestrator 未嘗試，符合其修正範圍聲明）** | 重跑 iteration 1 的可複驗指令：超大版本號仍印出 `block.sh: line 421: [: ...: integer expression expected` 到 stderr，`is_positive_integer` 未加位數上限。Post-review 修正段落本身也只聲明處理了 Critical／第二缺口／Major 三項，未聲明處理此項，如實對應。 |
| 4 | Minor | **未解決（同上）** | `grep GH_DELIM block.sh` 確認該字面值仍只出現在 `gh_output()` 內部（fail-closed），未併入 `validate_render_value`。 |

### 新發現

| # | 嚴重度 | 檔案:行 | 分類 | 發現 |
| --- | --- | --- | --- | --- |
| 5 | **Major** | `format-migrations.md:3-4,7-8,18,26`；`action.yml:46`；`block.sh:67,73`；`run-fixtures.py:768,823,858,942` | **新引入**（本輪修正的直接副作用） | **修正新增了 R-4.4／R-4.5 兩道互鎖與 `golden_fingerprint` 欄，但本單元自己的四份檔案裡，仍有 9 處逐字寫著「三道互鎖」／「四件事」，沒有一處被同步更新為五道。** 逐一核對：`format-migrations.md` 開頭 HTML 註解宣稱「機械解析者：`test_r4_2_*` 與 `test_r4_3_*`」——但 `test_r4_5_golden_fingerprint_matches_registry`（`run-fixtures.py:807`）透過 `_migration_rows()` 同樣機械解析這張表的最後一列（讀 `golden_fingerprint` 那一欄），這份「機械解析者」清單漏了它自己；同檔 §「改格式時要做的四件事」（26-32 行）四步驟裡沒有一步提到「改動 `serialize_block`／`escape_value` 時要重新產生 `serialize-golden.txt`（R-4.4）」；`run-fixtures.py:823` 的 `test_r4_5` docstring 逐字寫「指紋的計算方式與 `format-migrations.md` §「改格式時要做的**五件事**」第 4 步逐字相同」——**這是一個懸空引用：`format-migrations.md` 裡沒有「五件事」這個標題，只有「四件事」，而現行的「四件事」四步驟裡完全沒有任何一步描述 `golden_fingerprint` 的計算方式（哪些檔案要納入、以什麼順序串接、要不要含檔名）**——這個演算法目前唯一的權威落點是 `test_r4_5` 自己的程式碼，不在任何供人讀的流程文件裡。附帶：`format-migrations.md` 對 R-4.2 那一列自己記載的「觸發紅燈的情形」欄仍寫著「更新了快照但沒 bump 版本」——但這正是 code-summary 自己在同一輪修正裡實測證明「機制上做不到」的情境（`code-summary.md:171`），R-4.2 單獨並不觸發於此，真正涵蓋這個情境的是新加的 R-4.5；這一列的文字描述在 orchestrator 自己已經查明它不準確之後，仍未被改寫，等於把一個已知錯誤的敘述留在原地，改用新增一列（R-4.5）的方式迴避，而不是修正舊列的錯誤歸因。**這不是機制的漏洞**（我用三次獨立變異測試證實 R-4.4＋R-4.5＋既有 R-2.1 合起來確實把「改序列化」「改演算法」「改 render 不 bump」三個攻擊面都關上了），而是**本單元自己奉為「機械解析者」與人工修改格式時的權威指南**（format-migrations.md 開頭即自稱此職能）在數量描述與程序步驟兩層都沒跟上同一輪修正引入的新機制。下一個要改格式的人，若照著「四件事」字面操作（含 `render`／`parse_v<n>` 變更但完全不知道 `serialize_block` 也可能屬於「格式」的一部分），仍會在 R-4.4／R-4.5 撞紅燈——機制不會放行，但唯一能告訴他怎麼做對的地方是要去讀 `test_r4_4`／`test_r4_5` 的 docstring 原始碼，而不是這份文件。建議：(a) 把「三道」全部 9 處改為「五道」；(b) `format-migrations.md` 的「四件事」擴充或分流成「改 render／parse 格式」與「改序列化演算法」兩條路徑各自的步驟清單，後者明列「重新產生 `serialize-golden.txt`」與 `golden_fingerprint` 的計算方式（可直接照抄 `test_r4_5` 現有邏輯轉譯成散文）；(c) 改寫 R-4.2 那一列的「觸發紅燈的情形」為它實際會紅的情境（`FORMAT_VERSION` 與登錄表最後一列的版本不一致），把「更新快照未 bump」的情境移到 R-4.5 那一列（若新增）；(d) `run-fixtures.py:823` 的懸空引用改指向實際存在的章節或直接把演算法寫進 `format-migrations.md`。 |

### 三類計數（本輪新發現）

**新引入：1**（Finding #5，Major——文件與程式碼在同一輪修正裡分岔，屬修正動作本身的副作用，不是修正前就存在的缺陷，也不是修正暴露出的全新設計問題）。**既存漏審：0**。**新設計問題：0**。

（iteration 1 的兩項 Minor 維持未解決，但屬「orchestrator 本輪未嘗試處理」而非「修正引入」或「本輪漏審」，不計入以上三類——它們已在上表逐項判定中如實記載。）

### Summary

Critical 與 Major 兩項主要發現都**已解決**，且我自行以三組獨立變異（欄位對調、雜湊加鹽、render 標題改字）重跑原攻擊與延伸攻擊，全部在 scratchpad 的隔離副本上重現「修正前綠、修正後紅」，不是轉引 orchestrator 的複驗結果。orchestrator 修正過程中自行發現的第二個缺口（R-4.2 機制上做不到它自稱的觸發情形）也經我獨立重現＋修正後重跑確認：R-4.4／R-4.5／既有 R-2.1 三者合起來，對「改序列化欄序」「改雜湊演算法」「改 render 不 bump 版本」三個攻擊面都無法繞過。全套件（.github/actions/aidlc-sync-block）在真實未變異程式碼上為 550 斷言／0 失敗，`AIDLC_BLOCK_BASH=/bin/bash`（3.2.57）覆驗同樣全綠；U-1（`.github/actions/aidlc-sync-map/`）獨立重跑仍為 2707／0，兩個宣稱皆如實。

本輪唯一的新發現（Finding #5，Major）不是機制缺口，而是本單元自己的四份檔案（`format-migrations.md`、`action.yml`、`block.sh`、`run-fixtures.py`）在同一輪修正裡對「互鎖道數」與「改格式的步驟」的描述沒有同步更新，其中一處是懸空引用（指向一個不存在的「五件事」章節）。這會讓下一個真的要改 `serialize_block` 的人必須去讀測試原始碼才能知道怎麼做對，但不會讓錯誤的格式變更悄悄通過——機制本身仍會攔下來。1 個 Major、0 個 Critical，未超過 READY 的門檻；兩項 Minor（#3、#4）維持未解決，orchestrator 已如實聲明其修正範圍不含這兩項，不構成隱瞞。

VERDICT: READY

## iteration 2 的新發現與其修正（2026-08-30T12:50:58Z）

reviewer 判 **READY**（三項修正皆經它**自行重建攻擊**確認，非採信我的宣稱），但抓到一個新的 **Major，且是我造成的**。

### 文件與實作不一致：互鎖已是五道，9 處仍寫「三道」／「四件事」

新增 R-4.4／R-4.5 與 `golden_fingerprint` 欄之後，我**改了步驟內容卻沒改標題**——`format-migrations.md` 的 `## 改格式時要做的四件事` 底下已經是五個步驟，而我在 `run-fixtures.py:823` 的 docstring 引用了「§改格式時要做的**五件事**」。**那是一個指向不存在章節的死引用。**

**這是本 intent 第六次同型失誤**（`application-design:260822-ad-L1`：改動一個事實前，先列出它在產出裡的**每一種表達形式**）。我改的是「互鎖有幾道」這個事實，但只 grep 了自己改過的字串。

**修正落點（10 處，逐一判定為現況陳述或歷史敘述）**：

| 檔案 | 處置 |
| --- | --- |
| `format-migrations.md:26` | 標題 四→**五件事**（死引用的根源） |
| `format-migrations.md:3-4` | 檔頭重寫：R-4.2／4.3／4.5 讀本檔，R-4.1 讀 golden、R-4.4 讀 serialize-golden |
| `format-migrations.md:18` | 天花板段 三→五道 |
| `format-migrations.md` R-4.2 列 | **觸發情形更正**——原寫「更新了快照但沒 bump 版本」，該宣稱已被實測推翻（見上節）；改為「版本與本表脫節」，那件事現由 **R-4.5** 承接 |
| `run-fixtures.py:768`、`942` | 群標題與天花板 docstring |
| `block.sh:67`、`73` | 常數段與天花板註解 |
| `action.yml:46` | 「三道 CI 互鎖」→ 五道 |

**逐字保留、不改的兩處（歷史敘述）**：`format-migrations.md:8`（「[Q1=C] 的定案是三道」——當時確實是三道）與 `run-fixtures.py:858`（描述修正**前**「三道鎖一道都不紅」的實測）。改掉會讓紀錄與當時實況不符。

**機械複掃抓到我漏的一處**：第一次 grep 用的是「三道互鎖」，而 `action.yml:46` 寫的是「三道 **CI** 互鎖」——**同一個事實的第三種表達形式**，正是那條規則警告的形狀。改用「三道」重掃才命中。

### reviewer 的三項複驗（它自己跑的）

| 項目 | 它做了什麼 | 結果 |
| --- | --- | --- |
| Critical（R-4.4） | 在隔離副本重建 iteration 1 的攻擊（對調欄序＋同步改 `BLOCK_FIELDS`） | 550/0 → 550/6 紅 |
| **繞過嘗試** | 改 `content_hash()` 的管線加鹽（演算法變更而非序列化變更） | R-4.4 綠（正確，超出其範圍），但 **R-2.1 立刻紅**——它是差分檢查（Python 自算 sha256 vs 實際 hash op），`run-fixtures.py` 內**無任何寫死的 64-hex 摘要**（它 grep 確認），故兩個攻擊方向都被關上 |
| R-4.5 | 雙向重現：①改 render→更新 golden→不 bump；②改 serialize→正確重生 golden→跳過登錄表 | 兩者都被 R-4.5 抓到；正確做法（bump＋獨立重算指紋）則轉綠 |
| Major | `status=""` ＋ `reason_code=""` → exit 2 | 確認無誤擋——`domain-entities.md:29-31` 記載 `Decision.reason_code` 為總函式（一律非空），該前置條件不可能正當觸發 |

**Minor #3／#4 未解決**（修正範圍明確只涵蓋 Critical ＋ Major，reviewer 複現確認仍在、非阻擋）。

**修正後複驗**：550 斷言／0 失敗（含 bash 3.2.57）；U-1 獨立複跑 2707／0。
