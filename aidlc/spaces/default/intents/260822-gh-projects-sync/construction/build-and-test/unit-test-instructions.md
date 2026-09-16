# Unit Test Instructions — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· Test Strategy: Standard（`aidlc-state.md`） -->

## 這一層測的是什麼

**離線層**：不需要網路、不需要憑證、不寫入任何外部系統。全部以 PATH shim 偽裝 `gh`、
以 fixture 檔提供輸入。這一層是本 intent 唯一能在每個 PR 上無條件執行的驗證層。

跨越到需要真實 GitHub 的那一層在 `integration-test-instructions.md`，兩者的分界是
**憑證**：離線層的任何一支腳本若開始需要 `GH_TOKEN`，就代表分層被打破了。

## 執行方式

**沒有測試框架**。每一支測試都是可獨立執行的 `python3` 腳本，退出碼即結果
（`0` ＝ 全綠，非 `0` ＝ 有失敗）。這與本 repo 既有的 backend `unittest` 慣例不同，
理由在 U-1 的 `code-summary.md`：受測對象是 `.sh` 與 workflow YAML，不是可 import 的
Python 模組。

### 全部離線套件（一次跑完）

```bash
cd <repo root>
for t in \
  .github/actions/aidlc-sync-block/run-fixtures.py \
  .github/actions/aidlc-sync-map/run-fixtures.py \
  .github/actions/aidlc-sync-board/run-stub-tests.py \
  .github/actions/aidlc-sync-record/run-stub-tests.py \
  .github/actions/aidlc-sync-notify/run-stub-tests.py \
  .github/actions/aidlc-sync-forward/run-orchestration-tests.py \
  .github/actions/aidlc-sync-reconcile/run-reconcile-tests.py \
  .github/actions/aidlc-sync-reverse/run-reverse-tests.py \
  .github/actions/aidlc-sync-ci-guard/run-probe-tests.py \
  .github/actions/aidlc-sync-selftest/run-selftest-tests.py \
  .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py ; do
    echo "== $t"; python3 "$t" || echo "FAILED: $t"
done
```

### 三支靜態檢查器（受測對象是 repo 本身的設定，不是程式邏輯）

```bash
python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py
python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py
python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py
```

這三支**沒有測試對象與受測者的分離**——它們讀真實 repo 的檔案並判定。把它們列在這裡
而不是 CI 章節，是因為它們的失敗訊息是給改動者看的，不是給維運看的。

## 套件對照表（誰測誰）

| 套件 | 擁有單元 | 受測對象 | 層 |
| --- | --- | --- | --- |
| `aidlc-sync-map/run-fixtures.py` | U-1 | `map.sh`（record → Status 映射與解析） | fixture 斷言 |
| `aidlc-sync-block/run-fixtures.py` | U-2 | `block.sh`（受管區塊序列化／解析） | fixture 斷言 |
| `aidlc-sync-board/run-stub-tests.py` | U-3 | `board.sh`（Projects v2 讀寫） | PATH shim 偽裝 `gh` |
| `aidlc-sync-record/run-stub-tests.py` | U-4 | `record.sh`（綁定狀態檔 commit／push） | PATH shim ＋ 暫存 git repo |
| `aidlc-sync-notify/run-stub-tests.py` | U-5 | `notify.sh`（失敗通報 issue） | PATH shim |
| `aidlc-sync-forward/run-orchestration-tests.py` | U-6 | `aidlc-sync-forward-impl.yml` 抽出的編排腳本 | harness 模擬 runner |
| `aidlc-sync-reconcile/run-reconcile-tests.py` | U-7 | `aidlc-sync-reconcile-impl.yml` 抽出的腳本 | 同上 |
| `aidlc-sync-reverse/run-reverse-tests.py` | U-8 | `aidlc-sync-reverse-impl.yml` 抽出的腳本 | 同上 |
| `aidlc-sync-ci-guard/run-probe-tests.py` | U-10a | `ci.yml` 的 `gate` job 判定邏輯 | 行為層 probe |
| `aidlc-sync-ci-guard/check-ci-yml.py` | U-10a | `ci.yml` 的檔案形狀 | 文字層檢查器 |
| `aidlc-sync-selftest/run-selftest-tests.py` | U-9 | 兩支 checker 自身的行為 | 行為層 |
| `aidlc-sync-selftest/run-selftest-fixtures.py` | U-9 | 自我測試 workflow 第一段的 fixture 斷言 | fixture 斷言 |
| `aidlc-sync-selftest/check-agentic-steps.py` | U-9 | 全 repo：同步判定不得落在 LLM 步驟內 | 靜態檢查器 |
| `aidlc-sync-selftest/check-paths-relations.py` | U-9 | 全 repo：`paths-ignore` 與 lock 一致性 | 靜態檢查器 |

## 涵蓋期望（Standard 策略）

`aidlc-state.md` 的 `Test Strategy` 為 **Standard**，對應「每元件 5〜8 條、涵蓋關鍵行為」。
實測的規模遠高於這個下限（見 `build-test-results.md` 的實測表），因為受測對象是 shell
與 YAML——它們沒有型別系統，錯誤只能靠斷言擋。**這是刻意超標，不是誤解策略等級**：
`.claude/knowledge/aidlc-quality-agent/testing-guide.md` 逐字允許「context demands 時超出」。

**沒有覆蓋率量測**。`team.md ## Testing Posture` 已如實記載本 repo 無 `coverage.py`、
無 CI coverage step，`org.md` 的 80% 是宣告而非閘門。本階段不假裝有一個量不到的數字，
改以下列**二元可判**的三項作為這一層的實際門檻：

1. 每支套件退出碼為 `0`；
2. 每支套件的失敗數為 `0`（腳本自己印在最後一行）；
3. **突變驗證**：任一支套件所保護的行為被改壞時，該套件必須轉紅（見下節）。

## 突變驗證（這一層的真正門檻）

本 intent 已重複四次證實同一種失效：**測試看起來在守、實際守不到它宣稱守的東西**
（U-9 的檔名樣式、U-10a 的 `paths-ignore`、U-6 兩次）。因此新增或改動任何一條斷言時，
規則是：

> 把被守的行為改成錯的 → 確認測試紅 → 還原 → 確認綠。三步都要記錄。

各單元 `code-summary.md` 的「突變驗證」節有已跑過的條目與結果。**斷言數不是可複現
常數**（U-5 的教訓：三次獨立重建得到 21／7／4），只記「哪些測試紅」與質性結論。

## harness 與 CI 語意對齊（三支 impl 測試的必讀項）

GitHub 對未指定 `shell:` 的 `run:` 使用 `bash -e {0}`。三支 impl workflow 的測試 harness
必須以同樣的方式啟動被測腳本，否則「單一 intent 失敗不中止整輪」這類宣稱在本機是綠的、
在 runner 上是假的——**這正是實際發生過的事**：改成忠實的 `bash -e` 之後，三支共 **23 條**
斷言變紅（forward 3／reconcile 8／reverse 12）。

因此：

- 三支腳本已加 `set +e`（`set -<flags>` 只開不關，`set -uo pipefail` 不會關掉 `-e`）；
- 各補一條釘住自己 `bash -e` 行為的迴歸測試；
- harness 的 bash 由 `AIDLC_*_BASH` 環境變數控制。**`AIDLC_FORWARD_BASH` 同時被兩支
  harness 讀取而兩者的正確預設相反**（`run-orchestration-tests.py:69` 需要 `-e`、
  `run-live-tests.py:80` 需要不帶 `-e`），目前靠 `IMPL_BASH` 另立變數繞開。只影響手動
  覆寫，未修——**手動覆寫這兩個變數之前先讀那兩行**。

## 已知不執行的部分（誠實列出，不是待辦清單）

| 項目 | 為什麼不在這一層 |
| --- | --- |
| 全部 5 支 `run-live-tests.py` | 需要真實憑證與真實看板寫入，見 `integration-test-instructions.md` |
| `aidlc-sync-selftest.yml` 第二段 | 同上，且會在正式 repo 建立真 issue |
| 「CI 紅燈」本身 | 需要真實 PR 觸發；離線層只能證明判定邏輯，不能證明 GitHub 會照它動作 |

## 與上游的對應

套件清單與擁有單元引自各單元的 `code-generation-plan.md` 與 `code-summary.md` 的
「交付物與實際行數」；`bash -e` 的 23 條斷言與 `AIDLC_FORWARD_BASH` 的雙讀者問題引自
U-9／U-6／U-7／U-8 的 `code-summary.md`；突變驗證的必要性引自各單元 `code-summary.md`
的「突變驗證」節；覆蓋率量測的缺席引自 `team.md ## Testing Posture`；Standard 策略的
量級引自 `.claude/knowledge/aidlc-quality-agent/testing-guide.md` 的策略表。
