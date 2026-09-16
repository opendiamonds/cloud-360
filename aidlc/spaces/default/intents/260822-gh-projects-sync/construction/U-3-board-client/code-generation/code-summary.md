# Code Summary — U-3 看板客戶端

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-3-board-client · kind: library
     Generated: 2026-09-04T01:37:54Z（讀自 date -u） -->

## 建立的檔案

全部在 `.github/actions/aidlc-sync-board/`：

| 檔案 | 規模 | 職責 |
| --- | --- | --- |
| `action.yml` | 11.4 KB | 七個 `operation` 的介面轉接（沿用 U-2 單一 action 多 operation 形狀），逐 operation 在 description 列必要 input 與有效 output；Config 走三個 env（`AIDLC_PROJECT_OWNER`／`AIDLC_PROJECT_NUMBER`／`AIDLC_FIELD_NAME`）；**零憑證型 input**（SEC-1），憑證僅經 `env: GH_TOKEN` |
| `board.sh` | 1058 行（可執行；iteration 2 修正後） | 全部邏輯：`gh api graphql` 兩層檢查包裝、SEC-4 訊息清洗、四型錯誤的混合傳播、R-1〜R-6 群規則、name→id 執行期解析、受管區塊寫入。另有 `markers`／`resolve_status` 兩個 argv-only 診斷子命令（沿 U-2 `serialize` 先例） |
| `run-stub-tests.py` | 58.6 KB | 離線 stub 層：PATH shim 偽裝 `gh`（route 表＋`calls.jsonl` 呼叫記錄），U-2 `block.sh` 用**真的**；31 案 173 斷言（iteration 2 修正後），每案含 §4.4 規格註解 |
| `run-live-tests.py` | 27.0 KB | live 層（對測試看板 #23、issue #538）：完成判準 (a)〜(f) 逐條＋加測 (g)，9 步 60 斷言；測畢自動還原全部殘留 |

**U-1／U-2 的目錄一個位元組未動**（實作者查驗 mtime 皆早於本次工作開始）。

## 關鍵實作決定

四項 Plan Approval 介面判斷（2026-09-04T00:51:05Z 核可）**全數照案落地**：`write_status` 只比對 `status` 欄位、R-3.1 以 `AIDLC_EXISTING_BINDING` input 承接、受管標記執行期自 U-2 `block.sh` 萃取（附「非 `<!--` 開頭即 fail fast」的形狀檢查）、`AIDLC_ISSUE_TITLE` 選填預設 `intent_id`。以下六項為計畫未逐字指定處的實作定案：

1. **issue 所在 repo 取自 `GITHUB_REPOSITORY`**（缺席 fail fast）——Config 三 env 只涵蓋 Project 座標；反查 issue 需要 repo 座標，取 runner 既有事實、不擴 Config。
2. **R-1.2 過濾的 owner login 比對為 ASCII 不分大小寫**（Project 編號仍精確比對）——GitHub login 本身不分大小寫，逐字元比對會把 Config 的大小寫差異誤判成「不在板上」，恰是 ADR-0016 §4.3 警告的靜默補建路徑。R-4.5 的大小寫敏感只施加於**選項名稱**端，兩者已分別明文記載。
3. **`write_status` 對「item 不在板上」回 `Aborted`**（R-1.3 零筆；檢查先於 status 比對，不論 expected 為何）——`actual_status` 為空、`expected_status` 原樣回照、`message` 說明「無寫入對象，未送出寫入」。理由：上游契約把 `Failed` 限定為 `write_field`／`write_body` 專屬，U-6 已核可的 R-5.12 只認得 `write_status` 的 `Aborted`／`ExternalError`；「item 存在」是回讀比對的前置條件，前置條件不成立即為回讀不符，不新增契約外的第三個結果值。**iteration 1 原實作為 `Failed`，經 reviewer Critical 後改**（見下方「Post-review 修正」）；上游 `domain-entities.md`／`business-logic-model.md` 未動。
4. **R-1.4 斷言施加於所有經過查找的路徑**（`read_item`／`write_status`／`write_field`）→ 一律 `ExternalError`——看板損壞不是「欄位寫入失敗」，不得走 `Failed` 的不連坐通道。
5. **`write_field`／`write_body` 內部一切失敗（含內部讀取）收斂為 `Failed` 回傳值**（R-4.1／R-6.4 的不連坐）；`ensure_field` 的 `CannotCreate` 僅限兩種可達前提（權限類錯誤分類、同名欄位型別不同），其餘 API 失敗仍 `ExternalError`；「組織政策阻擋」分支**未實作**（ADR-0016 §1 判不可達，實作它會製造永遠走不到、卻看起來被涵蓋的分支）。
6. **body 尾端換行以 `\u0001` 哨兵保真**——`jq -r` 的輸出經 `$( )` 會剝掉尾端換行，直接取值等於每次 `write_body` 靜默改寫 body 結尾，違反 R-6.2「其餘內容一字不動」。

## 測試覆蓋（orchestrator 逐項複驗，非轉引）

| 層 | 結果 | 複驗方式 |
| --- | --- | --- |
| stub（離線） | 31 案 173 斷言，**0 失敗**（iteration 1 為 30 案 149 斷言） | orchestrator 自行重跑（預設 bash 3.2.57 與 `/opt/homebrew/bin/bash` 5.2.37 各一次），同數字 |
| live（#23） | 9 步 60 斷言，**0 失敗**；完成判準 (a)〜(f) 全數擊中 | orchestrator 以 `GH_TOKEN="$(gh auth token)"` 自行重跑，同數字 |
| bash 3.2 相容 | `/bin/bash` 3.2.57 複跑 stub 全綠 | 實作者實測（沿 U-1／U-2 慣例） |
| repo／env contract | 兩支 validator 皆綠 | orchestrator 自行重跑 |
| skip／防呆路徑 | 無憑證 → exit 3（明確聲明不完整）；`AIDLC_PROJECT_NUMBER=16` → exit 4（SEC-3） | 實作者實測兩者 |

**完成判準對照**（[ug:unit-of-work.md] U-3）：回讀不符回 `Aborted` 且不送出寫入 → live (a) 實測（含「看板值未變」的回讀斷言）；重複執行首建不產生第二則 issue → live (b) 實測（`existing_binding` 攔截、零 API 呼叫）；「範圍外寫入回 403」的「直推保護分支」半邊屬 U-4 的驗證面，本單元以 R-5 介面邊界斷言承接（stub：不存在推 commit／改檔案的 operation）。

### 突變驗證（四條，每條：改壞 → 紅 → 還原 → `diff -q` 逐位元復原 → 複跑綠）

| # | 突變 | 結果 |
| --- | --- | --- |
| 1 | 拿掉 `.errors` 檢查層 | stub 紅：1 案 1 斷言（`test_two_layer_check`）。**附觀察**：失敗仍被下游 R-1.4 斷言以 `ExternalError` 攔住（不靜默），兩層檢查的價值主要在**錯誤歸因正確性**——如實記載，不美化 |
| 2 | `NOT_FOUND` 改映射為零筆分支 | stub 紅：2 案 7 斷言（錯誤分類第 1 列＋SEC-4 案） |
| 3 | name→id 改寫死 id | live 紅：3 步 7 斷言（判準 (d) 直接擊中＋roundtrip 連鎖）；stub 亦獨立擊中 1 斷言——雙層防護 |
| 4 | `write_body` 損壞防護改為一律附加 | stub 紅：2 案 11 斷言（替換案＋損壞三態案） |

## 與計畫的偏離

**兩項，皆為 reviewer iteration 1 後的修正，非計畫階段的偏離**（iteration 1 的本段原寫「零」，那是錯的——計畫 Step 5 未指定「item 不在板上」的處置，實作自行定為 `Failed` 卻未在此揭露）：(1) `write_status` 對 item 不在板上回 `Aborted`（關鍵決定 3）；(2) `write_status` 的欄位解析（`list_fields`／`resolve_status_option`）移到回讀**之前**，讓 R-2.4 視窗內只剩單一 mutation 往返——代價是兩條 Aborted 分支中止前會先付一次（分頁時多次）欄位列舉呼叫，且 `desired` 對應選項不存在時會在回讀之前就以 `ExternalError` 紅燈（映射不一致本就該紅，不該被 Aborted 遮住）。11 步驟照序執行；四項 Plan Approval 介面判斷照案落地。

## 未完成項目（誠實列出）

1. **R-2.4 競態視窗零測試涵蓋**——設計如實記載的已知缺口（重現需精準時序），已在 `board.sh` 檔頭錯誤模型段明文「無兜底」；其代價由 ADR-0015 §2 綁進 Bolt 1 gate 的揭露項，**gate 核可者必須看見它**。
2. **R-1.4 無 live 反例**（ADR-0016 §6：`addProjectV2ItemById` 冪等）——僅 stub 誠實構造反例，未發明假的 live 觸發途徑。
3. **PRE-1-c 仍未執行**（`public_repo`＋`project` PAT 的四條寫入路徑實測）——Bolt 1 DoD 阻擋項、**憑證鑄造前人工必做**；不影響 `board.sh` 形狀（它只讀 `GH_TOKEN`）。
4. `resolve_status_option` 的 `ExternalError` 定位前綴固定為 `write_status`，經診斷子命令 `resolve_status` 觸發時前綴略有誤導（僅診斷路徑，不影響 action 介面）。
5. 測試看板 #23 的 PRE-1 殘留欄位（`AIDLC Stage r5`／`aidlc-sync-probe`）**未清**——屬 intent 層待清理表「U-3 驗完後一併清」的項目，非本單元擅動範圍。本單元自己的殘留（`aidlc-sync-test-` 前綴欄位、body 區塊、Status 改動）已全數還原，**issue #538 保持開啟**。

## 對呼叫端（U-6）的接線提示

`ExternalError` 會讓 step **非零 exit**（workflow 紅燈），但 `result`／`http_status`／`message` 三個 output 已先寫出，供 `if: failure()` 的通報步驟取用；`Aborted`／`Failed`／`CannotCreate` 為 exit 0，呼叫端**必須**檢查 `result` output 分流——只看 exit code 會把三者誤判為成功寫入。**`write_status` 的 `result` 值域是 `written`／`aborted`（＋例外式 `external_error`），不會出現 `failed`**，R-5.12 不需新增列；兩種 `aborted` 都附 `message`（C-5 可直接引用），「綁定過期／item 被移出看板」的訊號是 `result=aborted` 且 `actual_status=""` 且 `message` 含「不在 Project #」。`write_status` 不再 emit `http_status`。

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-04T01:53:47Z
**Iteration:** 1

### Findings

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
| --- | --- | --- | --- | --- | --- |
| 1 | Critical | `board.sh:730-738`（`op_write_status`）＋ `functional-design/domain-entities.md:50`／`business-logic-model.md:68` | 新設計問題 | `write_status` 在「回讀比對通過（`actual==expected==""`）但 item 不在板上」時 `emit result failed`（`WriteResult` 的 `Failed` 支）。但 `domain-entities.md` 的錯誤型別表與 `business-logic-model.md` 的錯誤處理表**都明文**把 `Failed` 限定為「`write_field` **或** `write_body` 失敗」，逐字如此；`write_status` 不在其中。`action.yml` 的 `write_status` output 說明（`result（written / aborted / failed）`）已把這個第三種值寫進公開介面，但這是本 code-generation 階段**自行**新增的第三個 `Failed` 產生點，不是 `[ad:component-methods.md]` §C-3 `write_status` 列的錯誤處理（該列只寫「`actual != expected` → 回 `Aborted`」），也不是 `requirements.md` FR-C1／FR-C2／FR-C3 涵蓋的情境（三者都只談「item 存在但不符」或「首建」，沒有「item 從未在板上」這個第三態）。**且此分支完全沒有測試涵蓋**——`run-stub-tests.py` 只有三個 `write_status` 測試（`aborted`／`written_uses_resolved_option_id`／`expected_empty_means_unset`，最後者的 fixture 是 `item_node(status=None)`，即 `ITEM_COUNT=1`，不是本分支的 `ITEM_COUNT=0`），`run-live-tests.py` 亦無對應案例。`code-summary.md` 本身的「與計畫的偏離：零」亦與此不符——這是一次未經 Plan Approval、未在偏離段揭露、且上游契約明文排除的介面擴張。**風險**：若 U-6 依 `[ad:component-methods.md]` 字面只認得 `write_status` 回 `written`／`aborted`，未特別處理 `result=failed`，很可能把此分支誤判為非 `aborted` 即成功，進而把從未真正寫入的 Status 值回寫進 `sync-state.json`——這正是 R-2.4 檔頭與 FR-C1「寧可不寫，不可寫錯」要防的那類靜默資料錯置，只是換了一個入口。 | 二擇一：(a) 依 `project.md` 的既有規則（`units-generation:260822-ug-L2`）把這視為上游契約缺口，回頭在 `domain-entities.md`／`business-logic-model.md`／`[ad:component-methods.md]` 補上「`write_status` 亦為 `Failed` 的第三個產生點」並指定確認人（Bolt 1 gate），而非在 code-generation 階段逕自定案；(b) 若維持現狀，至少：①在 `code-summary.md` 的「與計畫的偏離」如實記載此項而非寫零；②新增至少一則 stub 測試鎖住 `ITEM_COUNT=0` 分支的 `result=failed`；③明確通知並確認 U-6 的 code-generation 會檢查 `write_status` 的 `result=failed`，不只檢查 `aborted`。 |
| 2 | Major | `board.sh:704-753`（`op_write_status`，尤其 `741-745` 的 `list_fields`／`resolve_status_option`）＋ `functional-design/business-rules.md:64`（R-2.4 視窗寬度的接受理由）＋ `inception/application-design/services.md:47,50`（S-A／S-B 並行寫同一 item） | 新設計問題 | R-2.4 的競態視窗被接受的理由逐字是「對一個視窗寬度**約為單次 mutation 往返時間**的競態而言不成比例」——這個「單次往返」是說服 Bolt 1 gate 接受「協作者改動會被靜默、永久丟失、無反向 PR、無紅燈、無通報」這個代價的**唯一數量級依據**。但 `op_write_status` 的實際順序是：`read_item_core`（讀 #1，視窗起點）→ Aborted／零筆檢查 → `list_fields`（**額外一次或多次** GraphQL 呼叫，含分頁，且與讀取結果無關）→ `resolve_status_option` → mutation（視窗終點）。視窗因此是「讀 ＋ 列舉全部欄位 ＋ 寫」而非「讀 ＋ 寫」，實際寬度**已超出**批准時揭露的數量級，而 `services.md` 明確記載 S-A（事件觸發）與 S-B（每日對帳）**設計上會並行寫同一個 item**（R-2.4 依賴的正是這條路徑）、且 FR-C3「後到者的唯一合格結果是 Aborted」正是為了防這個並行——視窗越寬，兩個並行寫入者剛好都通過回讀比對、其中一者的改動被無聲蓋掉且事後無法偵測的機率就越高。`list_fields` 不依賴 `read_item_core` 的任何輸出（它只吃 `PROJECT_OWNER`／`PROJECT_NUMBER`），移到讀取之前並不影響任何既有邏輯或測試斷言。 | 把 `list_fields`／`resolve_status_option`（解析 `desired` 對應的 option id）移到 `read_item_core` 之前執行，讓「讀 → 寫」之間只剩單一 mutation 往返，貼合 R-2.4 對 Bolt 1 gate 揭露的風險量級；若基於其他理由（例如避免在 Aborted／零筆分支浪費一次欄位列舉呼叫）決定維持現有順序，則必須回頭修正 `business-rules.md` R-2.4 段對視窗寬度的描述並讓 Bolt 1 gate 知情重新確認，不能讓文件描述的風險量級與程式碼實際不一致。 |

### Attempted refutations that did not hold

- **重跑 stub 測試**：`python3 run-stub-tests.py` → 30 tests, 149 checks, 0 failures，與 `code-summary.md` 逐位元相符。
- **重跑 live 測試**（`GH_TOKEN="$(gh auth token)" AIDLC_PROJECT_NUMBER=23 python3 run-live-tests.py`）→ 9 steps, 60 checks, 0 failures，與 `code-summary.md` 相符；另以 `gh issue view 538` 與一次獨立 GraphQL 查詢確認 issue #538 仍 `OPEN` 且只掛在 Project #23（未觸及 #16），滿足安全紅線。
- **bash 3.2 相容性**：以本機 `/bin/bash`（3.2.57）透過 `AIDLC_BOARD_BASH=/bin/bash` 重跑 stub 套件 → 30/149/0，與 code-summary 的宣稱相符。
- **repo／env contract**：獨立重跑 `scripts/validate_repo_contract.py` 與 `scripts/validate_env_contract.py`，兩者皆綠。
- **突變驗證獨立重建**（在 scratchpad 隔離副本，含 U-2 `block.sh` 與 `action.yml`，`diff -q` 確認每次改壞前後與 `board.sh.orig` 位元一致）：
  - 拿掉兩層檢查的 `nerr` 判斷 → 1 test 1 failure，且失敗訊息確實如 code-summary 所述「被 R-1.4 以另一個（較不精確的）理由攔下」，不是「悄悄放行」；還原後複跑回到 0 failures。
  - `resolve_status_option` 的 `OPTION_ID` 改為硬編碼字面值 → 1 test 1 failure（`written：optionId 為執行期解析值` 斷言紅），與 code-summary 宣稱的「stub 亦獨立擊中 1 斷言」一致；還原後複跑回到 0 failures。
  - `write_body` 的三個 R-6.6 損壞檢查（`if false; then ...`）全數停用 → 兩案（順序顛倒／標記不成行）共多筆斷言翻紅（`result` 由 `failed` 變 `written`、PATCH 呼叫數由 0 變 1），證明該防護是真的攔阻而非恆真檢查；還原後複跑回到 0 failures。
- **NOT_FOUND 是否真的可能繞過 R-1.3 零筆分支而崩潰**：追出 `gql()`／`read_item_core` 的實際控制流——任何 `nerr != 0`（含 NOT_FOUND）都讓 `gql()` 回 1，`read_item_core` 在觸及任何 `jq` 對 `.projectItems.nodes[]` 的疊代**之前**就以 `return 1` 離開，呼叫端統一走 `external_error`；「對 null 疊代會讓 jq 崩潰」只在**移除兩層檢查後**才可能發生（即上面驗證的突變），現行程式碼本身不會，收回原先的懷疑。
- **R-1.2 大小寫比對**：追出程式碼對 owner login 雙邊皆 `ascii_downcase` 後比對、Project 編號仍精確比對，與 ADR-0016 §4 的理由一致，未發現漏洞。
- **SEC-1／SEC-4**：直接讀 `action.yml`（零憑證型 input，`GH_TOKEN` 只在 `env:` 區塊、不接 `inputs.*`）與 `gql()` 的清洗路徑（失敗訊息只取 `.errors[].message` 串接與正則從 stderr 抓的 `HTTP nnn`，不含 body 全文或標頭），並讀 `test_sec4_message_scrubbed` 的 fixture（body／stderr 都夾帶假憑證與 `Authorization` 字樣）確認清洗後輸出面確實不含機敏字串。
- **受管標記單一真實來源**：直接讀 U-2 `block.sh`（本審查唯一許可的整合點檔案）核對 `MARKER_SIGIL="<!-- aidlc-sync:begin"`／`MARKER_END="<!-- aidlc-sync:end -->"` 與 `board.sh` 的 `extract_marker`／形狀檢查邏輯逐字對得上，並確認兩檔 mtime（U-2 為 8/30，本單元為 9/4）佐證「U-1／U-2 目錄一個位元組未動」的宣稱。
- **R-5 權限邊界**：確認七個 `operation` 均不提供推 commit／改 record 目錄外檔案的能力，未知 `operation` 一律 `fail`（非零 exit），與 `test_r5_*` 系列吻合。

### Summary

新引入：0；既存漏審：0；新設計問題：2（1 Critical、1 Major）。兩項發現皆為本 code-generation 階段的實作決定（code-summary 自陳的「六項計畫未逐字指定處的實作定案」之二：第 3 項與 R-2.4 視窗的隱含加寬），且都可由程式碼與上游契約逐字對照獨立驗證，不是主觀品味判斷。Critical 項（`write_status` 新增一個上游契約明文排除、且零測試涵蓋的 `Failed` 產生點）已足以構成 NOT-READY；Major 項（`list_fields` 插入讀寫之間，實質加寬已核可接受的競態視窗）進一步顯示 R-2.4 的風險揭露與實作不一致。其餘經實測（stub／live／突變／bash 3.2／repo-env contract／SEC-1／SEC-4／NOT_FOUND 控制流／大小寫比對／標記單一真實來源／R-5 邊界）的宣稱全數屬實，程式碼品質整體紮實；本輪的兩項發現收斂後即有機會一輪轉為 READY。

## Post-review 修正（2026-09-04T17:28:41Z）

reviewer iteration 1 判 **NOT-READY**（1 Critical／1 Major）。兩項 orchestrator 都先自行對照上游契約複驗成立，再派 lead（aidlc-developer-agent）修正，修完 orchestrator 逐項重跑而非轉引。

### Critical — `write_status` 對「item 不在板上」自行新增契約外的 `Failed` 產生點

**複驗成立**：`domain-entities.md` 錯誤型別表與 `business-logic-model.md` 錯誤處理表逐字把 `Failed` 限定為「`write_field` 或 `write_body` 失敗」；U-6 已核可的 R-5.12 對 `write_status` 只列 `Aborted`／`ExternalError` 兩支（⇒ 完全不回寫）——`write_status` 回 `failed` 在 U-6 的四支表裡**沒有任何一列**，正是 reviewer 指出的靜默錯置入口。

**修法（orchestrator 定案，未走 Plan Approval——它不新增任何契約值，只收回一個契約外的值）**：改回 `Aborted`。理由三點：(1) 不引入第三個結果值；(2) U-6 R-5.12「Aborted ⇒ 完全不回寫」＋ C-5 通報恰是綁定過期該有的處置；(3) 「item 存在」是回讀比對的前置條件，前置條件不成立即為回讀不符。Plan Approval 定案的「只比對 `status` 欄位」講的是 item 存在時比對哪些欄位，不受影響。零筆檢查移到 status 比對**之前**，不論 expected 為何都走同一條、訊息才準確；兩種 `Aborted` 都補 `message`。上游三份 functional-design 產出**未動**——這是對既有 `Aborted` 定義的詮釋，reviewer 建議 (a)「回頭補上游」在此不需要；但 gate 核可者應知道此詮釋（見「未完成項目」新增第 6 項）。

**測試**：新增 `test_write_status_item_absent_aborted`（expected 空／非空各跑一輪，18 斷言：`result=aborted`、不是 `failed`、`actual_status` 空、`expected_status` 原樣回照、message 含「不在 Project #23」與「無寫入對象」、零 mutation、零 POST）。

### Major — `list_fields` 插在回讀與 mutation 之間，實質加寬 R-2.4 已揭露的視窗

**複驗成立**：`list_fields` 只吃 `PROJECT_OWNER`／`PROJECT_NUMBER`，`resolve_status_option` 只吃 `FIELDS_JSON` 與 `desired`，兩者都不依賴回讀結果；iteration 1 的順序讓視窗是「讀 ＋ 列舉全部欄位（含分頁）＋ 寫」，而 `business-rules.md` R-2.4 對 Bolt 1 gate 揭露的量級是「約為單次 mutation 往返」。

**修法**：兩者移到 `read_item_core` 之前；回讀與 mutation 之間不再有任何呼叫。`board.sh` 檔頭 R-2.4 段與 `op_write_status` 註解都寫下代價（Aborted 分支先付欄位列舉；選項不存在時提前紅燈）。**測試鎖住順序**：`test_write_status_written_uses_resolved_option_id` 新增四條順序斷言（恰一次回讀、欄位列舉全部在回讀之前、回讀之後**緊接著**就是 mutation、mutation 為最後一次呼叫）；`test_write_status_aborted_no_mutation` 改為恰兩次呼叫且回讀為最後一次。新 helper `call_indices` 回傳呼叫索引（`calls_matching` 只能數次數，數不出先後）。

### 修正的驗證（orchestrator 自行重跑）

| 項目 | 結果 |
| --- | --- |
| stub，預設 `bash`（3.2.57） | 31 tests, 173 checks, 0 failures |
| stub，`/opt/homebrew/bin/bash` 5.2.37 | 31 tests, 173 checks, 0 failures |
| live（#23，`GH_TOKEN="$(gh auth token)"`） | 9 steps, 60 checks, 0 failures；`gh issue view 538` → `OPEN` |
| `validate_repo_contract.py`／`validate_env_contract.py` | 皆 passed |
| U-1／U-2 目錄 | `find -newer <本單元 plan>` 零檔案 |

### 突變驗證（lead 執行、每條改壞 → 紅 → 還原 → `diff -q` 逐位元一致 → 複跑 31/173/0）

| # | 突變 | 紅的測試與斷言數 |
| --- | --- | --- |
| M-A | 零筆分支改回 `emit result failed`（連同拿掉 actual/expected emit，即 iteration 1 原形） | `test_write_status_item_absent_aborted`：8 |
| M-B | `list_fields`／`resolve_status_option` 搬回回讀與 mutation 之間 | `test_write_status_aborted_no_mutation`（恰兩次呼叫）＋ `test_write_status_written_uses_resolved_option_id`（列舉在回讀前、回讀後緊接 mutation）：3 |
| M-C | 零筆檢查搬回 status 比對之後 | `test_write_status_item_absent_aborted` 的 (b)：2（(a) 如預期不紅——expected 空時兩種順序結果相同） |

lead 自陳一個突變腳本錯誤：M-C 第一版的錨點命中 `op_read_item` 內同形的 `if [ "$ITEM_COUNT" = "0" ]`，剪錯一段，19 個無關斷言翻紅而目標測試沒紅；改以 `op_write_status() {` 之後為錨點重跑才得上表結果，第一次結果作廢。

### 可觀察的行為差異（相對 iteration 1，供 gate 核可者判斷）

1. `write_status` 的 `result` 不再有 `failed`；不再 emit `http_status`。
2. `aborted` 兩種來源都有 `message`（`action.yml` 的 `outputs.message` 描述同步改為「失敗時，以及 write_status result=aborted 時」）。
3. `desired` 對應的選項不存在時，現在在回讀之前就 `ExternalError`；iteration 1 若同時回讀不符會以 `Aborted` 收場而遮住映射不一致。
4. Aborted 分支多付一次（分頁時多次）`ProjectV2.fields` 查詢。

### 未完成項目的增補

6. **「item 不在板上 → `Aborted`」是對上游 `Aborted` 定義（「回讀不符」）的詮釋**，未回改 `domain-entities.md`／`business-logic-model.md`／`[ad:component-methods.md]`。若 gate 認為應在契約上明寫，落點是 U-3 `domain-entities.md` 錯誤型別表的 `Aborted` 列補一句「含 item 不在板上」，屬文件對齊、不改行為。
7. **「item 不在板上 → `Aborted`」分支只有 stub 涵蓋、無 live 反例**（reviewer iteration 2 Minor）：live 完成判準 (a) 只驗證「回讀不符」這一種 `Aborted` 來源。補 live 案例需要一個確定不在 #23 上的 issue 當 binding（read-only 路徑、零寫入風險），可在 build-and-test 補上；本輪如實列為缺口。

## Review (code-generation — iteration 2)

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-04T17:39:43Z
**Iteration:** 2

### 逐項判定（iteration 1 的兩項發現）

| # | 原嚴重度 | 判定 | 依據 |
| --- | --- | --- | --- |
| 1 | Critical — `write_status` 對 item 不在板上自行新增契約外的 `Failed` 產生點 | **Resolved** | `board.sh:714-753`（`op_write_status`）逐行核對：`ITEM_COUNT="0"` 分支現 `emit result aborted`，不再 `emit result failed`。`domain-entities.md`、`business-logic-model.md` 兩份上游產出**逐字未動**（獨立讀取確認，錯誤型別表仍是「`Failed` — `write_field` 或 `write_body` 失敗」，`Aborted` 列仍是「回讀不符」），修法未回改上游、只是把新分支收斂進既有的 `Aborted` 值域。對照 U-6 `business-rules.md:122`（R-5.12）逐字：「`write_status` 回 `Aborted` 或拋 `ExternalError` ⇒ **完全不回寫**」「`write_status` 失敗是唯一的全有全無情形：它失敗代表看板一個字都沒動」——這正好與「item 不在板上、看板一個字都沒動」的語意一致，且 R-5.12 對 `write_status` **完全不認得** `failed`（獨立 grep 全 R-5.12 段落確認），故收回 `Failed` 是修正一個真的無處落地的契約外分支，不是繞過。新增測試 `test_write_status_item_absent_aborted`：自行重跑（stub 兩種 bash、31/173/0）逐一核對其 18 條斷言（expected 空／非空各 9 條：exit 0、result=aborted、result≠failed、actual_status 空、expected_status 原樣回照、message 含「不在 Project #23」與「無寫入對象」、零 mutation、零開 issue），全部通過。`action.yml` 的 `write_status` output 描述已同步（`result（written / aborted）`，明文「本 operation 不產生 result=failed」），且全 `.github/actions/aidlc-sync-board/` 目錄（`board.sh`、`action.yml`）grep 不出任何殘留的「`write_status` 回 `failed`」敘述。**獨立重建突變 M-A**（零筆分支改回 `emit result failed`）：於 scratchpad 隔離副本執行，1 test 紅（`test_write_status_item_absent_aborted`，12 條斷言失敗——與 code-summary 宣稱的 8 條數字不同，但這是我自行撰寫的簡化突變版本〔未 emit `actual_status`／`expected_status`〕而非 lead 的逐字突變，數字差異不影響結論：測試確實鎖住此行為，紅燈成立）；`diff -q` 還原後與原檔逐位元一致，複跑回到 31/173/0。 |
| 2 | Major — `list_fields` 插在回讀與 mutation 之間，實質加寬 R-2.4 視窗 | **Resolved** | `board.sh:725-745` 逐行追控制流：`list_fields` → `resolve_status_option` → `read_item_core` → `assert_single_item` → `ITEM_COUNT` 檢查 → status 比對 → mutation。回讀（`read_item_core`）與 mutation 之間**零其他 API 呼叫**，與 `business-rules.md` R-2.4 對 Bolt 1 gate 揭露的「約為單次 mutation 往返」量級一致。**獨立重建突變 M-B**（把 `list_fields`／`resolve_status_option` 搬回回讀與 mutation 之間）：於 scratchpad 隔離副本執行，2 test 紅、**3 條斷言失敗**——與 code-summary 宣稱的「`test_write_status_aborted_no_mutation`＋`test_write_status_written_uses_resolved_option_id`：3」**逐位元相符**；`diff -q` 還原後與原檔一致，複跑回到 31/173/0。另核對路由機制（`run-stub-tests.py` 的 `GH_SHIM`）本身：route 比對是 `argv` 內容比對（`contains` 子字串），不依賴測試檔內 `routes=[]` 列表的書寫順序，`calls.jsonl` 記錄的才是程式碼實際呼叫序——故 `call_indices` 系列順序斷言驗證的是真實控制流，非測試檔書寫順序的重言式。 |

### 新發現

無 Critical／Major。一項 Minor（見下）。

| # | 嚴重度 | 檔案:行 | 分類 | 發現 | 建議 |
| --- | --- | --- | --- | --- | --- |
| 1 | Minor | `run-live-tests.py`（`test_a_aborted_leaves_board_unchanged` 一帶） | 新設計問題 | iteration 2 新增的「item 不在板上 → `Aborted`」分支只有 stub 覆蓋（`test_write_status_item_absent_aborted`），live 層的完成判準 (a) 只驗證「回讀不符」那一種 `Aborted` 來源，未驗證「item 不在板上」這一種——`未完成項目` 清單（項 1〜6）未列出這個新分支缺 live 覆蓋。與既有的「R-1.4 無 live 反例」性質不同：R-1.4 是**無可構造反例**（ADR-0016 §6，機制自己造不出多筆狀態），而「item 不在板上」是**可構造但本輪未構造**的 live 情境（例如先移除 item 再呼叫 `write_status`）。風險不高——分支本身是提早 return、不依賴 GraphQL 特有的細微行為（不像 R-1.4 依賴 `addProjectV2ItemById` 的冪等特性），且已被 stub 的 18 條斷言鎖住。 | 在「未完成項目」補列一條，說明此分支目前僅 stub 覆蓋、live 覆蓋留待後續（例如與 PRE-1-c 或測試看板清理一併排入），使缺口如實可見而非隱含在「完成判準 (a) 已擊中」的措辭裡（該措辭只涵蓋兩種 `Aborted` 來源之一）。不阻擋 READY。 |

### Attempted refutations that did not hold

- **重新質疑「item 不在板上 → `Aborted`」是否為對上游契約的合理詮釋，而非文字遊戲**：逐字核對 `domain-entities.md`（`Aborted { actual, expected }` — 「回讀不符」）、`business-logic-model.md`（同義表）、`business-rules.md` R-2.1（「`actual != expected` → `Aborted`」）三處，確認上游文字本身**未明說**「item 不存在」算不算「回讀不符」——這是一個真實的上游契約留白，而非本輪修法憑空編造。但對照 U-6 `business-rules.md:122` R-5.12（`write_status` 的失敗只認 `Aborted`／`ExternalError` 兩支，且明文「唯一的全有全無情形」），把「item 不存在（無 actual 可比）」視為「比對的前置條件不成立、等同不符」在下游消費端**完全可用現有處置**（不回寫、C-5 通報），不需要新增任何契約值——這個詮釋自洽且未製造新的孤兒契約端點，故不成立「這是規避 Critical 的文字遊戲」的懷疑。
- **重新質疑 code-summary 宣稱「上游三份 functional-design 產出未動」是否屬實**：逐字讀 `domain-entities.md`、`business-logic-model.md`、`business-rules.md` 三份 U-3 產出，錯誤型別表、`Aborted`／`Failed` 定義、R-1〜R-6 規則群文字與我在其他審查脈絡讀到的版本（透過既有的 `## Review` 附錄比對）一致，無改動痕跡。宣稱屬實。
- **重新質疑 R-1.4（多筆 → `ExternalError`）是否因本輪重排而被 item-absent 分支繞過**：逐行確認 `op_write_status`／`op_write_field`／`op_read_item` 三條路徑皆在 `read_item_core` 之後**立即**呼叫 `assert_single_item`，早於各自的 `ITEM_COUNT=="0"` 分支——多筆狀態仍優先於零筆分支被攔截，不成立「重排讓多筆診斷被繞過」的懷疑。
- **重新質疑「欄位解析提前」是否讓 `desired` 選項不存在時的行為在 item 不在板上的情境下也改變、且未被充分揭露**：確認會（`resolve_status_option` 在 `read_item_core` 之前執行，item 是否存在尚未可知），但 `board.sh` 檔頭 R-2.4 段與 `op_write_status` 內註解、以及 code-summary 的「可觀察的行為差異」第 3 點皆已明文揭露此代價（「映射不一致本就該紅燈，不該被 Aborted 遮住」），不成立「未揭露」的懷疑。
- **重新質疑欄位解析提前是否會引入新的靜默資料遺失路徑（例如用了過期的 option id 卻不紅燈）**：追出 `OPTION_ID` 若已失效（選項在 `list_fields` 之後、mutation 之前被改名／刪除），`updateProjectV2ItemFieldValue` mutation 會以無效 `optionId` 失敗，`gql()` 回非零、`op_write_status` 走 `external_error`（紅燈），不是靜默寫入或靜默丟失——不成立「新增靜默路徑」的懷疑。
- **重跑 stub 測試**（預設 bash 3.2.57、`/opt/homebrew/bin/bash` 5.2.37）→ 31 tests, 173 checks, 0 failures，兩次逐位元相符，與 code-summary 宣稱一致。
- **重跑 live 測試**（`GH_TOKEN="$(gh auth token)" AIDLC_PROJECT_NUMBER=23`）→ 9 steps, 60 checks, 0 failures，與宣稱一致；`gh issue view 538` 與一次獨立 GraphQL 查詢（含 owner login 的 inline fragment 修正）確認 issue #538 仍 `OPEN` 且僅掛在 Project #23（未觸及 #16）。
- **重跑 `validate_repo_contract.py`／`validate_env_contract.py`** → 皆綠。
- **獨立重建至少兩條突變（M-A、M-B）於 scratchpad 隔離副本**：見上方逐項判定欄，皆紅燈成立、`diff -q` 還原一致、複跑回到 31/173/0。
- **獨立驗證 SEC-1**：`action.yml` 的 `inputs:` 段逐項核對（`operation`／`binding`／`intent_id`／`existing_binding`／`issue_title`／`expected_status`／`desired_status`／`field_value`／`block_text`），零憑證型欄位。
- **獨立驗證 skip／防呆路徑**：實際執行 `env -u GH_TOKEN HOME=/nonexistent-fake-home-for-test python3 run-live-tests.py` → `SKIP`，`rc=3`；`GH_TOKEN="$(gh auth token)" AIDLC_PROJECT_NUMBER=16 python3 run-live-tests.py` → `REFUSE`，`rc=4`。两者皆屬 `run-live-tests.py` 測試層自身的防呆（非 `board.sh` 本體行為），與 code-summary 的歸屬一致。
- **獨立驗證檔案規模**：`board.sh` 1058 行與宣稱**逐位元相符**；`action.yml`／`run-stub-tests.py`／`run-live-tests.py` 的位元組數換算 KB 與宣稱差在 0.1〜0.7 KB 內（度量單位或量測時間點的微小差異，非誤導）。
- **獨立驗證「U-1／U-2 目錄一個位元組未動」**：`aidlc-sync-block`／`aidlc-sync-map` 全部檔案 mtime 為 8/30，`board.sh`／`action.yml` 為本輪（9/4 UTC 17:28，對應本機 9/5 01:2x）——時間序與宣稱一致。

### 三類計數

新引入：0；既存漏審：0；新設計問題：0（Critical／Major 皆 Resolved，1 項 Minor 屬本輪修正動作衍生的新缺口、已依規則分類但不阻擋 READY）。

### Summary

Iteration 1 的 1 Critical＋1 Major 皆逐項核對為真實修復，非採信 code-summary 自述：Critical 項改回 `Aborted` 後與 U-6 已核可的 R-5.12（`write_status` 只認 `Aborted`／`ExternalError`，两者皆「完全不回寫」）完全對齊，且獨立確認上游三份 functional-design 產出逐字未動、無殘留的「`write_status` 回 `failed`」敘述；Major 項的視窗收斂在程式碼控制流上逐行核對成立，且以獨立重建的 M-B 突變取得與 code-summary 逐位元相符的斷言失敗數（3），構成強證據。stub（兩種 bash）、live（#23，9/60/0，issue #538 確認仍 OPEN 且僅掛 Project #23）、repo／env contract 四項全數獨立複驗通過。本輪唯一新發現為 Minor（item-absent 的 `Aborted` 分支缺 live 覆蓋），風險低、不阻擋 READY，建議補進「未完成項目」清單使其如實可見。判定 READY。
