# Code Generation Plan — U-9 自我測試 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service
     Created: 2026-09-05T18:58:04Z（讀自 date -u） -->

## 交付物

| 檔案 | 內容 |
| --- | --- |
| `.github/workflows/aidlc-sync-selftest.yml` | `pull_request`（paths allowlist）＋ `workflow_dispatch`，`timeout-minutes: 10`，兩段式（第一段全綠才跑第二段），清理 `if: always()` |
| `.github/actions/aidlc-sync-selftest/check-agentic-steps.py` | **R-1.2** 靜態檢查：`aidlc-sync-*.yml` 的決定性 job 不含代理式引擎步驟 |
| `.github/actions/aidlc-sync-selftest/check-paths-relations.py` | **A-6** 的兩個集合關係 |
| `.github/actions/aidlc-sync-selftest/run-selftest-fixtures.py` | **A-1／A-3** 的 fixture 驅動 ＋ 轉呼 U-1／U-2 既有驅動 |
| `.github/actions/aidlc-sync-selftest/run-selftest-tests.py` | **主力**：對上面三支的行為測試（含突變） |
| `<record>/.test-fixtures/`（`aidlc/spaces/default/intents/260822-gh-projects-sync/.test-fixtures/`） | A-1 的憑證樣式假樣本、A-3 的兩輪 record 樣本 |

複雜度 **M**。不新增依賴（`python3` ＋ 標準庫；YAML 以既有 `check-ci-yml.py` 的同一套自寫解析形狀處理，不引入 PyYAML）。

## 開工前查證（逐項，含 `open-items.md` 全項與條目內但書）

### 查證 1 — **N:C-3（Critical）：`functional-design` 的檢查對象仍是錯的**（Q1 的由來）

| 檔案 | 逐字 | 狀態 |
| --- | --- | --- |
| `nfr-requirements/tech-stack-decisions.md:32-34` | 「檢查對象是四支 workflow 的 **`.yml` 原始檔**（`.github/workflows/aidlc-sync-*.yml`）。**工具用 `python3`**」＋ 更正由來（2026-08-30T06:11:59Z，reviewer 判 Critical） | ✅ 已更正 |
| `nfr-requirements/performance-requirements.md:31` | 「該 allowlist 必須涵蓋 `.github/workflows/aidlc-sync-*.yml` 而非 `*.md`／`*.lock.yml`」 | ✅ 已更正 |
| `functional-design/business-rules.md:25` | 「解析編譯後的 **`.lock.yml`**……**檢 `.lock.yml` 而非 `.md`**」 | ❌ **未更正** |
| `functional-design/business-rules.md:29` | allowlist 涵蓋 `.github/workflows/aidlc-sync-*.md`／`.lock.yml` | ❌ **未更正** |
| `functional-design/business-logic-model.md:22` | 「R-1.2 靜態檢查：**.lock.yml** 的決定性 job……」 | ❌ **未更正** |
| `functional-design/business-logic-model.md:83`（邊界情形表） | 「改了 `.md` 未重編 `.lock.yml`，靜態檢查讀 `.lock.yml`，看到的是舊的」 | ❌ **未更正**（該列在純 Actions 下整條不成立） |

**Q1=A 定案：依 `nfr-requirements` 的更正版實作。** 實作對象與 allowlist 一律 `.github/workflows/aidlc-sync-*.yml`。**四處矛盾不由本站回改上游**，登錄為 open item 指派 Bolt 1 gate（`N:C-3` 的原定期限），並以測試釘住（見測試策略最後一條）。

**這與 U-8 的先例同型**：U-8 的實作者發現 orchestrator 的計畫指示與已過 gate 的 `services.md:58` 矛盾時，選擇已過 gate 的正確版本並拒絕照計畫寫。

### 查證 2 — 「四支 workflow」的計數在交付後已不成立

實測 `ls .github/workflows/aidlc-sync-*.yml`：**現有 6 個檔**（forward／reconcile／reverse 各一對薄外層＋`-impl`），本單元交付後為 **7 個**。上游的「四支」指的是**四個邏輯 workflow**（正向／對帳／反向／自我測試），ADR-A10 的兩檔拆分讓檔數不等於邏輯數。

**實作規則**：檢查以 **glob 列舉**為準，不寫死 4；但必須**額外斷言四個邏輯名稱都存在**（`aidlc-sync-forward`／`-reconcile`／`-reverse`／`-selftest`），否則某支被刪掉時檢查會靜默地少檢一支。**這正是「檔案集合一致性」自檢項的落點。**

### 查證 3 — A-1／A-2／A-3 有多少已被 U-1／U-2 的既有驅動涵蓋

| 斷言 | 既有涵蓋 | 本單元要做的 |
| --- | --- | --- |
| A-2（序列化逐位元相同） | **已完全涵蓋**——`aidlc-sync-block/run-fixtures.py` 的 `test_serialization_is_deterministic_and_locale_independent`、`test_r4_4_serialization_golden_byte_identical` | **不重寫**，第一段**轉呼**該驅動並斷言其 rc＝0 |
| A-1（U-1 的 output 不含憑證樣式） | **無**——`aidlc-sync-map/run-fixtures.py` 39 條測試無一條涉及憑證樣式 | **本單元新寫** |
| A-3（無漂移時不重寫，連續兩輪） | **部分**——`content_hash` 的決定性已測，但「連續兩輪不重寫」是**跨輪行為**，既有驅動是單輪純函式測試 | **本單元新寫**（兩輪驅動） |

**不重寫 A-2 的理由**：重寫會產生第二份斷言同一件事的程式，兩份必有一份先過期。轉呼＋斷言 rc 是「單一真實來源」規則（`team.md ## Code Style`）在測試層的體現。**但轉呼必須斷言它真的跑了**——只看 rc＝0 不夠，還要斷言輸出含測試數且該數 > 0，否則驅動被改成空殼時本單元不會紅。

### 查證 4 — A-6 的兩個關係，其中一個已有現成的推導來源

- **關係 1**（U-8 寫入路徑集合 ⊆ `paths-ignore` glob 集合）：`check-ci-yml.py:110` 已有 `derive_glob_from_record_sh()`，從 U-4 `record.sh` 的白名單常數推導。**本單元 import 它，不自抄一份**。
- **關係 2**（glob 集合 ∩ 本單元 allowlist ＝ ∅）：本單元自己算——把 `aidlc-sync-selftest.yml` 的 `on.pull_request.paths` 與 glob 集合做交集判定。

**U-10b 尚未交付**，四支 gh-aw workflow 的 `paths-ignore` 還不存在。處置：

> **檢查器對五個承載體（`ci.yml` ＋ 四支 gh-aw）逐一要求**，缺一即紅。**它現在對本 repo 跑會是紅的**——那是誠實的狀態（U-10b 未上線 ⇒ 反向 PR 現在真的會進 gh-aw gauntlet，正是 R-5 逐字警告的後果）。本單元自己的**測試套件**（`run-selftest-tests.py`，以合成輸入測檢查器）必須全綠；「對真實 repo 跑轉綠」列為 **U-10b 的完成判準**。

**不得**為了讓它現在綠而把 gh-aw 那四支寫成可選——那會讓 U-10b 漏做時沒有紅燈，正是 `N:M-5` 警告的形狀。

### 查證 5 — `open-items.md` 對本單元的其餘影響

| 項目 | 對 U-9 的意義 |
| --- | --- |
| **N:C-3** | Q1 的由來，見查證 1。**本單元不修上游，但實作依更正版** |
| **U-9 security Q-1**（R-1.3 的 403 在組織層授權下恆不發生） | 已由 `security-requirements.md:28` 標出並指派 units-generation／Bolt 0 gate。**本站不改完成判準**；R-1.3 落在第二段，依 Q2=A 為 stub |
| **`.test-fixtures` 與 registry** | `component-methods.md` 已定案 registry 選取，fixture record 不註冊 ⇒ 不會變成第 7 個 intent。**沿用該落點，不另尋位置** |
| **獨立測試 Project 是否已列入 `external-dependency-map.md`** | `domain-entities.md:71` 逐字「本站未逐項核對——列為 Bolt 4 前必須確認的一項」。**本站同樣不核對**（那是 Bolt 4 gate 的事），但實作要讓它缺席時**訊息指得出來是哪一個**（`business-logic-model.md` 錯誤表逐字要求） |

**條目內但書的追查**：`security-requirements.md:62` 的追加註（權限集合現為四項，ADR-0015 §8）指向 Bolt 0，與本單元的實作無交集——第二段依 Q2=A 為 stub，不鑄憑證。

### 查證 6 — 安全邊界（本 session 的常設約束）

第二段的看板寫入必須帶 **SEC-3 守衛**：以 `int()` 正規化後比對，等於 **16** 即拒絕並非零退出（`016`／`" 16"` 都要擋），無法解析也拒絕（fail-closed）。**形式逐字沿用 U-6 `run-live-tests.py` 與 U-3 `run-live-tests.py` 已修正的那一份**，不自創第二種寫法。

## 計畫步驟

- [ ] **Step 1 — `check-agentic-steps.py`（R-1.2）**：對 `.github/workflows/aidlc-sync-*.yml` glob 列舉 ＋ 斷言四個邏輯名稱齊備；逐 job 判定「決定性 job」並斷言其步驟不含代理式引擎（`uses:` 指向 gh-aw／copilot／agent 類、`engine:` 鍵、`.lock.yml` 產物引用）。**追溯**：R-1.2、R-2、`project.md ## Forbidden`、ADR-0013、Q1=A
- [ ] **Step 2 — `check-paths-relations.py`（A-6）**：import `check-ci-yml.py` 的 `derive_glob_from_record_sh()`；關係 1 對五個承載體逐一要求；關係 2 對本單元 allowlist 求交集。**追溯**：A-6、R-3、查證 4
- [ ] **Step 3 — fixture 集**：`<record>/.test-fixtures/` 放 A-1 的憑證樣式假樣本（**憑空構造、結構相同但不觸發 `FORBIDDEN_CONTENT_PATTERNS`**，並在檔內註明為何不能用真樣式）與 A-3 的兩輪 record 樣本。**追溯**：`domain-entities.md` fixture 集、`security-requirements.md:43`
- [ ] **Step 4 — `run-selftest-fixtures.py`（第一段驅動）**：A-1（U-1 output 純字串比對）＋ A-3（兩輪不重寫）＋ **轉呼** U-1／U-2 既有驅動並斷言「rc＝0 且測試數 > 0」。**追溯**：A-1、A-2、A-3、查證 3
- [ ] **Step 5 — `aidlc-sync-selftest.yml`**：`pull_request` 的 `paths` allowlist（`.github/workflows/aidlc-sync-*.yml`、`.github/actions/aidlc-sync-*/**`、`<record>/.test-fixtures/**`；**不含 `sync-state.json`**）＋ `workflow_dispatch`；`timeout-minutes: 10`；**兩段以 `needs` 串接**（第一段紅則第二段不跑）；清理 `if: always()`；**無 concurrency group**（`scalability-requirements.md:42` 逐字）。**追溯**：R-3、R-4、`performance-requirements.md`、`scalability-requirements.md`
- [ ] **Step 6 — 第二段（Q2=A：stub）**：job 以「憑證與測試 Project 編號皆存在」為 `if:` 條件，缺任一即 skip 並在 summary 寫明**是哪一個**缺席。含 SEC-3 守衛。**步驟本身完整寫出**（不是 TODO 佔位），但**沒有真實憑證所以從未被執行過**——這一點必須寫進 workflow 註解與 `code-summary.md`。**追溯**：Q2=A、查證 6、`business-logic-model.md` 錯誤表
- [ ] **Step 7 — 失敗語意兩類可分辨**：斷言失敗與外部錯誤在 **exit 訊息第一行**即可分辨；斷言失敗訊息**含預期與實得**。**追溯**：`reliability-requirements.md`、R-1.1
- [ ] **Step 8 — 測試**（見下節）
- [ ] **Step 9 — 突變驗證**（見下節）
- [ ] **Step 10 — `code-summary.md`**（orchestrator 執筆）

## 測試策略（吸取 U-6／U-7／U-8 的教訓）

**硬要求，逐條**：

1. **行為測試為主**——三支檢查器都是「讀檔案 → 判定」的純輸入輸出，**以合成的暫存 repo 樹驅動**，斷言 rc 與訊息內容，不做文字結構斷言。
2. **每條測試都有前提斷言**——先確認情境真的構造出來了再斷言後果。**stub 計畫鍵名一律 `"exit"`**。
3. **突變要打中「對應的那一條」**，不是打中別條。
4. **錯誤處理分支各有測試**——「四個邏輯名稱缺一」「glob 推導失敗」「承載體缺席」「fixture 不存在」各一條。

**必測清單**：

| # | 測什麼 | 為什麼非測不可 |
| --- | --- | --- |
| 1 | R-1.2：某支 workflow 的決定性 job 被塞進代理式步驟 ⇒ **紅**，且訊息指出是哪一支哪一個 job | 這是本單元存在的理由 |
| 2 | R-1.2：檢查對象是 **`.yml`**——把一個假的 `aidlc-sync-x.lock.yml` 放進 workflows 目錄，**檢查器不得因為它存在就轉綠，也不得因為它不存在就跳過** | **釘住 N:C-3 的更正**（Q1=A）。這一條紅了就代表有人把實作改回 `.lock.yml` |
| 3 | R-1.2：四個邏輯名稱缺一 ⇒ **紅** | 查證 2；缺了會靜默少檢一支 |
| 4 | A-6 關係 1：某個承載體缺 `paths-ignore` ⇒ **紅**（含 gh-aw 四支） | 查證 4；U-10b 漏做必須有紅燈 |
| 5 | A-6 關係 2：把 `sync-state.json` 加進本單元 allowlist ⇒ **紅** | R-3 逐字「兩個條件必須一起斷言」 |
| 6 | A-6：`derive_glob_from_record_sh()` 推導失敗 ⇒ **紅**，不得靜默放行 | fail-closed |
| 7 | A-1：U-1 的 output 含憑證樣式 ⇒ **紅** | 六條防線之一 |
| 8 | A-1 的 fixture **不觸發** `validate_repo_contract.py` | fixture 本身讓 CI 紅會讓整件事倒過來 |
| 9 | A-3：第二輪產生重寫 ⇒ **紅** | 跨輪行為，既有驅動測不到 |
| 10 | 轉呼 U-1／U-2：把被轉呼的驅動換成「rc＝0 但零測試」的空殼 ⇒ **紅** | 查證 3；只看 rc 會被空殼騙過 |
| 11 | 兩段順序：第一段紅 ⇒ 第二段**不跑**（靜態斷言 `needs` 與 `if`） | `performance-requirements.md` 的核心設計 |
| 12 | 清理以 `if: always()` 等價形式宣告（靜態斷言） | R-4 |
| 13 | 失敗訊息**含預期與實得**；斷言失敗與外部錯誤第一行可分辨 | R-1.1、`reliability-requirements.md` |
| 14 | SEC-3：測試 Project 編號為 `16`／`016`／`" 16"`／不可解析 ⇒ **拒絕、非零退出** | 本 session 常設約束 |
| 15 | allowlist **不含** `sync-state.json`（靜態斷言） | R-3、A-6 關係 2 的前提 |
| 16 | 無 concurrency group（靜態斷言） | `scalability-requirements.md:42` 與 U-8 的 P-2 相反，容易被「對齊」掉 |

**不動用真實 API**：不開真實 PR、不寫 #16／#23、不建立任何 secret。第二段的全部測試以 stub 驅動。

## 突變驗證（Step 9 的必打點）

至少涵蓋：把檢查對象改回 `.lock.yml`（必須讓 #2 紅）、四個邏輯名稱的斷言拿掉（#3）、A-6 的 gh-aw 四支改成可選（#4）、關係 2 拿掉（#5）、glob 推導失敗改成放行（#6）、A-1 的比對改成恆真（#7）、A-3 只驗一輪（#9）、轉呼只看 rc（#10）、`needs` 拿掉（#11）、`if: always()` 拿掉（#12）、SEC-3 改回字串比對（#14）。

**每條突變都要確認它讓「對應的那一條」紅，而不是讓別條紅**——並在報告中逐條寫出「紅的是哪幾條測試」。

## 本單元誠實記載的未驗證部分（必須進 `code-summary.md`）

| 完成判準 | 本 stage 的證據 |
| --- | --- |
| ① 把映射改壞 ⇒ CI 紅燈且輸出指出預期與實得 | **突變驗證可證**（第一段，離線） |
| ② 把判定搬進 agent step ⇒ 靜態檢查失敗 | **突變驗證可證**（#1／#2） |
| ③ 憑證做範圍外寫入 ⇒ 403 | **僅 stub 證據**。需真實憑證與真實 PR 觸發，兩者皆不在本 session 授權內；且 `security-requirements.md` Q-1 已標出它在組織層授權下**恆不發生**，落點待 Bolt 0 gate |
