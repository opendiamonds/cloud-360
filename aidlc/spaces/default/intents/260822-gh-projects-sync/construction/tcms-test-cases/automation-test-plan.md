# 自動化測試計畫 — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: tcms-test-cases（Construction）· intent 260822-gh-projects-sync -->

## 本 stage 的「待自動化」桶：一項

分桶結果見 `manual-test-cases.md` 的覆蓋盤點。桶二只有 **B-1** 一項，本 stage 已把腳本
寫出來並跑綠——**不是列願望清單**。

---

## B-1：反向同步 PR 會觸發的 workflow 集合不得變大

### 為什麼之前沒有斷言

`check-paths-relations.py` 的 `IGNORE:` 那一族（五項）驗的是「**這五個承載體**有
`paths-ignore`」。它驗不到的是「**沒有別的跑起來**」——新增一支無 paths 過濾的
`on: pull_request` workflow，`IGNORE:` 五項全綠，而反向同步每天多觸發它一次。

那個事實（U-10b 交付後仍有 `ci.yml` 與 `aidlc-sync-forward.yml` 會建立 run）原本
**只寫在 `run-selftest-tests.py:2313` 絆線訊息的一段註解裡**。註解不是斷言。

而 `deploy.yml` 完全沒有被任何檢查看過：`on.pull_request: {types: [closed], branches: [ut]}`、
**無 paths** ⇒ 反向 PR **合併**時觸發自架 runner 上 `timeout-minutes: 30` 的完整部署。

### 落點與理由

| 項目 | 值 |
| --- | --- |
| 層 | **建置期靜態檢查**（不是執行期行為） |
| 落點 | `.github/actions/aidlc-sync-selftest/check-paths-relations.py` 的 `PR-TRIGGER-1` |
| 為什麼是這裡 | 這支檢查器已經在解析全部 workflow 的觸發設定（`IGNORE:` 那一族做的就是這件事），且它**已經在 CI 上執行**（`aidlc-sync-selftest.yml` 第一段的直接 step）。另開一支要重寫同一套 YAML 解析與 glob 比對 |
| 為什麼不是 backend／frontend | 受測對象是 `.github/` 下的 YAML，與 `backend/tests/` 或 Playwright 無關 |

### 具體斷言（不是「測試 X 正常」）

以 GitHub 的過濾語意，對一個變更集合**只有**同步狀態檔的 PR（base `ut`）計算觸發閉包：

1. `on.pull_request` 未宣告 → 不觸發
2. `branches` 不含 `ut` → 不觸發
3. `paths-ignore` **全數命中**變更集合 → 不觸發
4. `paths` allowlist **不命中** → 不觸發
5. 其餘 → 觸發
6. **解析不開的檔一律計入觸發集合**（fail closed）

斷言：計算出的集合 **恰等於** 釘住的 `REVERSE_PR_TRIGGERS = ("aidlc-sync-forward.yml", "ci.yml", "deploy.yml")`。

釘住的清單**刻意寫死**、逐項附理由。改那個清單就是在做一個決定，而那一行 diff 就是
紀錄——與 `PINNED_COMPILER_VERSION`、`EXPECTED_CARRIERS` 同一條紀律。

### 配套的行為測試

| 測試 | 檔案 | 驗什麼 |
| --- | --- | --- |
| `test_a_new_unfiltered_pull_request_workflow_is_red` | `.github/actions/aidlc-sync-selftest/run-selftest-tests.py` | 合成樹加一支無 paths 的 `on: pull_request` workflow ⇒ rc=1、`PR-TRIGGER-1` 紅、訊息指名該檔；**含對照組**（拿掉之後 rc=0） |
| `test_an_unreadable_workflow_counts_as_triggering` | 同上 | 語法壞掉的 `.yml` ⇒ `PR-TRIGGER-READ:<檔名>` 紅，訊息逐字含「讀不到不等於安全」 |

### 合成樹的兩處配套修正（由這條斷言逼出來）

| 修正 | 為什麼 |
| --- | --- |
| `synth_deploy_yml()`：合成樹補上 `deploy.yml` 的觸發形狀 | 釘住的集合含它；合成樹少了它，基準線會以「少掉的」那一側紅——那是 fixture 不完整，不是 repo 違規 |
| `synth_forward_pr_trigger()`：把合成的 `aidlc-sync-forward.yml` 換成帶 `on: pull_request`（無 paths）的形狀 | `CLEAN_SYNC_WF` 只宣告 `workflow_dispatch`，對 R-1.2 的代理式檢查夠用，但 PR-TRIGGER-1 看的是觸發設定。**只改 `on:`，不動 `CLEAN_SYNC_WF` 本身**——那個常數被代理式那一族的測試共用 |

### 突變驗證（實測，非估計）

| 突變 | 動作 | 結果 |
| --- | --- | --- |
| **M1** | 在真實 repo 新增 `.github/workflows/zz-mutation-probe.yml`（`on: pull_request`，無 paths） | **紅**：`[失敗] PR-TRIGGER-1`，訊息「多出來的：['zz-mutation-probe.yml']」；`22 項檢查，1 失敗` |
| **M1 還原** | 刪掉該檔 | **綠**：`22 項檢查，0 失敗` |
| **M2** | 拿掉 `ui-regression.lock.yml` 的 `paths-ignore` | **紅 3 項**：`IGNORE:ui-regression.lock.yml`、`COMPILED:ui-regression`、`PR-TRIGGER-1`——三道不同的檢查各自從自己的角度看到同一個缺陷 |
| **M2 還原** | 複製回備份 | **綠**：`22 項檢查，0 失敗`；`md5` 與突變前**逐位元相同**（`72c3fa4c949c0b242d6793cd8ef3f56c`） |
| **M3** | 合成樹加一支語法壞掉的 `.yml`（`types: [` 未閉合） | **紅**：`PR-TRIGGER-READ:zz-broken.yml`（由 `test_an_unreadable_workflow_counts_as_triggering` 涵蓋，每次跑套件都驗一次） |

**突變本身有生效的確認**：M1 的紅燈訊息逐字印出 `zz-mutation-probe.yml`，M2 的訊息
指名三個不同的失敗代號——不是「有東西紅了」而是「紅的正是預期的那幾項」。

### 套件規模的變動

| 套件 | 之前 | 之後 | 差額來源 |
| --- | --- | --- | --- |
| `check-paths-relations.py` | 21 項 | **22 項** | `PR-TRIGGER-1` |
| `run-selftest-tests.py` | 91 tests／385 checks | **93 tests／392 checks** | 上表兩條行為測試 |

絆線 `test_the_real_repo_state_is_what_we_say_it_is` 的期望集合同步由 21 更新為 22 項
——它如預期紅了一次，這是它被設計來做的事。

---

## 同一 intent 內、前兩個 stage 已寫出的自動化（交叉引用，非本 stage 產出）

列在這裡是為了讓「這個 intent 的自動化到底涵蓋了什麼」在一個地方看得完；三者的突變
驗證各自記在自己 stage 的產出裡。

| 斷言 | 落點 | 寫於 | 突變驗證 |
| --- | --- | --- | --- |
| README 的需求正本段落被刪 ⇒ 紅 | `scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT["README.md"]` | build-and-test | 刪整段 ⇒ rc=1 且訊息指名兩條缺失字串；還原 ⇒ rc=0 |
| 四支 lock 的 `compiler_version` 不是釘住值 ⇒ 紅 | `check-paths-relations.py` 的 `COMPILER:<name>` | ci-pipeline | 改成 `v0.86.2` ⇒ 紅；刪 metadata 首行 ⇒ 紅（fail closed）；還原 ⇒ 綠且 md5 相同 |
| 四支從未在 CI 執行的套件接進 CI | `aidlc-sync-selftest.yml` 第一段 | ci-pipeline | 非斷言，是覆蓋範圍變更（10/14 → 14/14） |

---

## 沒有寫成腳本的項目（open items，附理由）

| 項目 | 為什麼沒寫 |
| --- | --- |
| 桶三的五項（M-1〜M-5） | 依撰寫標準 §1 的四類判準判定為「不能或不該自動化」，已寫成手動案例。理由逐項列在 `manual-test-cases.md` 的分桶表 |
| 未分類的 U-1（[US:S-10 AC 5] 的 403） | **該 Given 不可達**，不是「還沒寫」。寫成測試會是一條永遠不紅也不綠的死碼。處置指派回 user-stories 或 ADR，見分桶表 |
| `deploy.yml` 對反向 PR 無 paths 過濾這件事**本身** | `PR-TRIGGER-1` 讓它**可見**（它在釘住的集合裡、附理由），但**不阻擋**——要不要加 paths 過濾涉及 ADR-0008 的部署模型，是 gate 的決定不是測試的決定 |

## 執行方式

```bash
# 這條斷言與它的行為測試（離線、零依賴、秒級）
python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py
python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py -k pull_request_workflow
python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py -k unreadable_workflow

# 整套（16 組，約 7 分鐘）
# 逐支指令見 build-and-test/unit-test-instructions.md
```

在 CI 上，兩者都由 `aidlc-sync-selftest.yml` 第一段的直接 step 執行
（`check-paths-relations.py` 是 step 5、`run-selftest-tests.py` 是 step 7）。

## 與上游的對應

分桶依據引自 `manual-test-cases.md` 的覆蓋盤點，其「已自動化」欄的判定依據為
`build-and-test/build-and-test-summary.md` 的逐單元覆蓋表；`IGNORE:` 那一族的作用域限制與
「2 個仍會建立 run」引自 U-10b 的 `code-summary.md`（MAJOR-4）與 `run-selftest-tests.py`
的絆線訊息；`deploy.yml` 的觸發設定為本 stage 以 `yaml.safe_load` 實讀；
[US:S-6 AC 7] 引自 `stories.md`；套件規模引自 `build-and-test/build-test-results.md`
與本 stage 的重跑。
