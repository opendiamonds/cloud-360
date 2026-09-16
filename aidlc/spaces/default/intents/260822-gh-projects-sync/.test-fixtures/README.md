# U-9 自我測試的 fixture 集

<!-- Unit: U-9-selftest-workflow · 由 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py 讀取 -->

本目錄放 **U-9 自我測試第一段**（純文字 dry-run，無網路、無憑證）要用的 record 樣本。

## 這些檔案由誰讀

`.github/actions/aidlc-sync-selftest/run-selftest-fixtures.py`。**讀檔的是那支 runner，不是受測邏輯**——`map.sh`（U-1）與 `block.sh`（U-2）只從環境變數讀輸入、只往 stdout 寫，自身零 I/O，這是 [US:S-10 AC 1] 的 fixture 驅動前提。

## 為什麼放在這裡，以及它為什麼不會變成第 7 個 intent

落點由 `functional-design/domain-entities.md` 定案（引自 [ad:component-methods.md]）：事件路徑與排程路徑**一律以 `intents.json` 的 registry 為選取來源**，不得依事件 diff 推導 record；本目錄不註冊進 registry，兩條路徑都不會選中它。

附帶兩項本站實測的結構性保險：

- 本目錄在 **record 之內**（`<record>/.test-fixtures/`），不是 `intents/` 底下的兄弟目錄，所以它連「長得像一個 record」都不成立——U-4 `record.sh` 的 `record_path` 驗證正則是 `^aidlc/spaces/([A-Za-z0-9._-]+)/intents/([A-Za-z0-9._-]+)$`，本目錄多一層，比對不成立。
- `.test-fixtures` 不以 `.aidlc-` 開頭，不落入 `.gitignore` 的 `aidlc/spaces/*/intents/*/.aidlc-*` 排除（已用 `git check-ignore -v` 複驗：NOT IGNORED），故可進版控。

## 假憑證樣式：為什麼不能用真的樣式

`a1-credential-shaped-record.md` 需要一個「看起來像憑證」的輸入，才能斷言 U-1 的 output 不會把它搬進 Actions log（本 repo 為 public，log 公開可讀）。

**但它必須是結構相同、卻不觸發任何掃描器的假值**，理由有兩層：

1. `project.md ## Forbidden` 逐字警告 `scripts/validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`「**不分辨『示範』與『洩漏』，會直接紅燈**」。把真的樣式抄進 fixture，會讓這個為了防洩漏而存在的 fixture 自己變成 CI 紅燈的原因。
2. 本 repo 是 public，GitHub 的 push protection 對 `ghp_`／`AKIA` 這類**真實前綴**同樣不分辨示範與洩漏。所以本檔的假值一律**不使用任何真實前綴**。

**以及一項 `security-requirements.md` 額外要求的**：假樣式必須是**憑空構造**的，不得是任何曾經真實存在過的憑證的變形——「應該沒人看過」是沒有證據的假設。本檔的每一個值都是打字打出來的 `ZZTEST` 重複串，沒有任何一個字元來自任何真實憑證。

**下一個想「修好」這些假值的人請先讀完上面兩段。** 把它們換成真實樣式會同時讓 repo contract 紅燈與 push protection 擋下推送，而且從 diff 上看起來像是在做正確的事。

## 檔案

| 檔案 | 驅動哪一條斷言 |
| --- | --- |
| `a1-credential-shaped-record.md` | **A-1**：U-1 的 output 不含憑證樣式 |
| `a3-round-1-record.md` | **A-3** 第一輪 |
| `a3-round-2-record.md` | **A-3** 第二輪。與第一輪**語意相同、位元組不同**（多了註解行、非追蹤區段被改動）——「無漂移」判的是語意不是位元組 |
| `a3-drift-record.md` | **A-3 的反例組**：語意真的變了（`Current Stage` 前進一站）⇒ 三欄比對必須判有漂移。沒有這一組，「無漂移」的斷言可能只是因為比對根本沒在運作 |
