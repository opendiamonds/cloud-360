# Code Generation Plan — U-3 看板客戶端

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-3-board-client · kind: library
     Created: 2026-09-03T16:18:40Z（讀自 date -u） -->

## 交付物與落點

**`.github/actions/aidlc-sync-board/`** — 獨立 composite action（`nfr-requirements/tech-stack-decisions.md` 定案：不與 U-1／U-2 共用，因本單元做真實網路 I/O 且持有憑證，混入會破壞純函式層的 fixture 前提）。`shell: bash`，以 `gh api graphql` 呼叫 Projects v2，憑證一律經 `env: GH_TOKEN` 傳入（SEC-1：`action.yml` 不得宣告任何憑證型 input）。

七個方法（[ad:component-methods.md] §C-3 ＋ ADR-0015 §11 的 `write_body`）以 `operation` 分派，沿用 U-2 `action.yml` 的單一 action 多 operation 形狀。

## 實測依據（全部引自 `PRE-1-results.md` 第四〜六輪與 ADR-0016）

| 事實 | 對實作的直接約束 |
| --- | --- |
| `opendiamonds` 是個人帳號 | GraphQL 查詢根一律 `user(login:)`（ADR-0016 §4.1，性質為缺口待補——上游從未指定查詢根） |
| `NOT_FOUND` 同時涵蓋「不存在」與「無權限」 | 不得把 `NOT_FOUND` 對應成「卡不在板上」；R-1.3 零筆分支只能由「查詢成功且過濾後為零筆」進入（ADR-0016 §4.3） |
| 單選欄位只吃 option id 且大小寫敏感 | name→id 一律執行期 per-project 解析，不得寫死（R-4.4／R-4.5）；每個單選欄位多一次讀取（R-4.6） |
| `addProjectV2ItemById` 冪等 | R-1.4（同 Project 多筆 → `ExternalError`）為防禦性斷言、無可構造的 live 反例（ADR-0016 §6）——以 stub 測試覆蓋該分支，不發明假的 live 觸發途徑 |
| `Issue.projectItems` 反查條件是同擁有者，不需 link | `read_item` 不需自行確保 repo↔project 連結 |
| `createProjectV2Field`／`updateProjectV2Field` 可用 | `ensure_field` 走「可自動建立」支；`CannotCreate` 可達前提收斂為兩種（憑證缺 Projects 寫入權、同名欄位型別不同）——「組織政策阻擋」不可達，不實作該分支 |
| 錯誤分類法四列（ADR-0016 §4 表） | 錯誤分類器的比對基準，逐字納入 stub fixtures |
| 測試看板 **#23**（`opendiamonds` 名下、Status 六選項已對齊 #16、option id 與 #16 不同） | live 測試的唯一寫入對象；harness 硬性防呆：目標 project number 斷言 ≠ 16（SEC-3） |

## 計畫步驟

- [x] **Step 1 — `action.yml` 介面**：七個 `operation` 的 inputs/outputs 宣告與 env 映射。Config 承載為三個 env：`AIDLC_PROJECT_OWNER`／`AIDLC_PROJECT_NUMBER`／`AIDLC_FIELD_NAME`。無任何憑證 input（SEC-1）。逐 operation 在 description 列必要 input 與有效 output（沿用 U-2 慣例）。
- [x] **Step 2 — `board.sh` 基座**：`gh api graphql` 包裝函式——每次呼叫檢查兩層（exit code **與** body `.errors`，`tech-stack-decisions.md` 定案：只檢查一層即為缺陷）；錯誤分類器（`ExternalError` → **非零 exit**（例外式，與其餘三型不同——[ad:component-methods.md] 的「拋」）；`Aborted`／`Failed`／`CannotCreate` → **回傳值**，exit 0）；SEC-4 訊息清洗（交給呼叫端／C-5 的 message 只含 GraphQL `errors[].message` 與 HTTP 狀態碼，不含完整 body、不含標頭）。
- [x] **Step 3 — 讀取層**：`read_item`（`Issue.projectItems` 反查 → R-1.2 依 Config 的 Project 過濾 → 零筆走 R-1.3（全 `null` 的 `ItemState`）、多筆走 R-1.4（`ExternalError`）；`managed_block_hash` 由 issue body 轉交 U-2 的 `block.sh parse`＋`hash` 取得（`domain-entities.md`：不是本元件算的，自算即第二份格式物化）；`issue_state` 一併取回）；`read_issue_state`（同查詢路徑的輕量投影）。
- [x] **Step 4 — 欄位解析層**：project node 解析（`user(login:).projectV2(number:)`）；欄位與選項列舉（`--paginate`，僅此處需分頁）；Status 與自訂欄位的 name→id 執行期解析（大小寫敏感，名稱端政策：**精確比對**並明文記載）；`ensure_field`（缺欄位 → `createProjectV2Field`（TEXT）；兩種可達失敗前提 → `CannotCreate`）。
- [x] **Step 5 — 寫入層**：`write_status`（**必先** `read_item`；`actual.status != expected_status` → `Aborted{actual, expected}`，不送出寫入、不開 issue、不紅燈；相符 → `updateProjectV2ItemFieldValue` 以 option id 寫入）；`write_field`（欄位不存在時嘗試建立，建立失敗 → `Failed` 不連坐 Status）；`create_item`（`existing_binding` 非空 → 不建、回既有值（R-3.1）；R-3.2 首建專屬檢查：解析 Config 指定的 Project 並驗證可寫，不符即中止；開 issue → `addProjectV2ItemById` → 回 binding；**不自行回寫綁定編號**（R-3.3，那是 U-4 職責））。
- [x] **Step 6 — `write_body`**：受管區塊唯一持久化路徑（R-6 群）。標記常數**執行期自 U-2 `block.sh` 萃取**（`MARKER_SIGIL`／`MARKER_END`，單一真實來源在 U-2；萃取失敗即 fail fast），輔以 `block.sh has_marker` 判定；無標記 → 附加於既有內容之後、有標記 → 替換 BEGIN〜END 整段（R-6.3）；有 BEGIN 無 END 或順序顛倒 → 視為 body 損壞，回 `Failed` 不猜不附加（R-6.6）；不做長度截斷（R-6.5）；失敗回 `Failed` 不連坐（R-6.4）。
- [x] **Step 7 — stub 測試 `run-stub-tests.py`**（離線、PATH shim 偽裝 `gh`）：錯誤分類四列逐字 fixture、`NOT_FOUND` 不得走零筆分支、R-1.2 過濾、R-1.3 零筆、R-1.4 多筆（stub 能誠實構造 live 構造不出的狀態）、兩層錯誤檢查（HTTP 200 + `.errors` 非空）、SEC-4 清洗斷言、`write_status` 的 Aborted 判定、`write_body` 的附加／替換／損壞三態、SEC-1（`action.yml` 無憑證 input 的機械斷言）、R-5 介面邊界（不存在推 commit／改檔案的 operation）。
- [x] **Step 8 — live 測試 `run-live-tests.py`**（對 #23，need `GH_TOKEN`；無 token 時明確 skip 並以非零聲明不完整，不靜默）：完成判準逐條——(a) 回讀不符 → `Aborted` 且看板值未變；(b) 以 `existing_binding` 重跑首建不產生第二則 issue；(c) `read_item` 反查 issue #538 回 #23 的 item；(d) name→id 解析對六個 Status 選項全數命中且與寫死 id 不同（斷言解析值非任何硬編碼）；(e) `write_body` round-trip（寫入 → `read_item` 的 `managed_block_hash` 非 `null` 且等於 U-2 `hash` 重算值）；(f) `ensure_field` 對既有欄位回 FieldRef 不重建。harness 進場斷言 `AIDLC_PROJECT_NUMBER != 16`（SEC-3 防呆）。測試殘留（欄位、body 改動）測畢清理；issue #538 保持開啟（PRE-1 待清理表：留到 U-3 驗完）。
- [x] **Step 9 — 突變驗證**（tcms 慣例先行）：至少四條——①拿掉 `.errors` 檢查層（stub 斷言紅）；②`NOT_FOUND` 改映射為零筆分支（stub 紅）；③name→id 改寫死 id（live (d) 紅）；④`write_body` 損壞防護改為附加（stub 紅）。結果記入 code-summary。
- [x] **Step 10 — 規格註解與文件**：每個測試函式加 §4.4 結構化註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`；`@api` 填實際觸及的 GraphQL 欄位路徑或省略——不得捏造）；`board.sh` 檔頭 docstring 沿 `agent_router.py` 樣板深度（契約段、安全邊界段、錯誤模型段——含「`ExternalError` 是例外式非回傳值」與 R-2.4 競態視窗「無兜底」的明文警示）。
- [ ] **Step 11 — `code-summary.md`**：檔案清單、關鍵決定、測試覆蓋、突變結果、誠實列出未完成項（R-2.4 視窗無測試涵蓋、R-1.4 無 live 反例、PRE-1-c 仍為 Bolt 1 DoD 開放項等）。

## 需 Plan Approval 裁決的四項介面判斷（上游未逐字指定，本計畫的落法）

1. **`write_status` 的比對範圍**：契約簽章是 `expected: ItemState`，本計畫落為**只比對 `status` 欄位**。理由：mutation 只觸及 Status，比對範圍對齊「這次寫入可能覆蓋掉的東西」；比對整個 `ItemState` 會讓無關的並行變更（body 編輯、自訂欄位）永久 Abort 一次合法的 Status 寫入。`expected` 以 `AIDLC_EXPECTED_STATUS` env 承載（含空值 = 期望未設值）。
2. **R-3.1 的承接方式**：record 讀取是 U-4 職責（`read_binding`），U-3 不碰 record 目錄。`create_item` 以 `AIDLC_EXISTING_BINDING` input 承接——呼叫端把 `read_binding` 的結果傳入，非空即不建、原值回傳。R-3.1 的攔截語意保留在介面上，record 知識不外洩進 U-3。
3. **受管標記的引用機制**：R-6.2 要求引用 U-2 的具名常數、不得自建副本。bash 跨 action 無 import，本計畫以**執行期萃取**（從 `.github/actions/aidlc-sync-block/block.sh` 讀取 `MARKER_SIGIL=`／`MARKER_END=` 的賦值行）實現引用，萃取失敗 fail fast；另加一條 stub 測試鎖住「萃取值與 `block.sh render` 實際輸出的首尾行一致」。
4. **`create_item` 的 issue 標題**：C-3 簽章只有 `(intent_id, Config)`，未指定標題格式。本計畫不替 U-6 發明標題慣例：`AIDLC_ISSUE_TITLE` 為選填 input，預設 `intent_id` 原文。標題格式的正式決定留給 U-6（它擁有呼叫端）。

## 測試策略對齊

Test Strategy = Standard（state 檔）。stub 層每方法 1〜3 案（分支覆蓋導向）＋ live 層對完成判準逐條，合計約 20+ 案。**R-2.4 的競態視窗沒有任何測試涵蓋**（`business-rules.md` 明文：重現需精準時序，且該視窗已由 ADR-0015 §2 綁進 Bolt 1 gate 的揭露項）——這是如實記載的已知缺口，不是漏寫。

## 已知的上游開放項（不阻擋本單元程式碼，但列入 summary）

- **PRE-1-c**（`public_repo`＋`project` PAT 的四條寫入路徑實測）：Bolt 1 DoD 的阻擋項、憑證鑄造前必做，**不影響 board.sh 的程式碼形狀**（它只讀 `GH_TOKEN`）。仍未執行，須在 Bolt 1 gate 前由人工完成。
- Pull requests write 未實測（U-8 依賴，非本單元）。
- 測試看板 #23 的殘留欄位（`AIDLC Stage r5`／`aidlc-sync-probe`）依 PRE-1 待清理表於 U-3 驗完後一併清。
