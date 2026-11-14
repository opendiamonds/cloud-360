# TCMS 同步報告 — 260920-orchestration-brain

> **狀態：只做了 `--dry-run`，尚未實際寫入 TCMS，待核可。**
> 核可後才拿掉 `--dry-run` 執行。以下輸出只含案例名稱、計畫名稱與字元數，不含任何憑證；
> `~/.tcms.conf` 存在（權限 600），本站未讀出或印出其內容。

- 執行時間（`date -u`）：`2026-11-14T05:18Z` 前後（手動案例在語意審查修正後重跑一次）
- 前提：驗證關卡已通過（`automation-test-plan.md` 第五節：本 intent 範圍 ERROR 0）。`--all` 剩 1 項 ERROR 屬 intent `260802-last-login-column` 的案例、由本分支引起，見第三節

## 一、手動案例（`--file`，建立＋更新）

指令：

```
python3 -B scripts/tcms_sync.py --file aidlc/spaces/default/intents/260920-orchestration-brain/construction/tcms-test-cases/manual-test-cases.md --dry-run
```

輸出（逐字）：

```
[dry-run] plan     將建立 260920 大腦入口：本機與部署環境（手動）
[dry-run] plan     將建立 260920 大腦入口：真實模型路徑（手動）
[dry-run] case     將建立 [P1] 真實模型下單一意圖的句子被交辦到正確的能力
[dry-run] case     將建立 [P1] 真實模型下語意不明的句子改為反問並列出候選，不建立工作項
[dry-run] case     將建立 [P2] 真實模型下一句含兩件事時拆成兩個工作項
[dry-run] case     將建立 [P1] 回歸：已選作業對象時說「評核這個系統」或「那張圖」仍交辦到目前對象
[dry-run] case     將建立 [P1] 回歸：在工作區產生並存檔的新架構圖會掛到作業對象的系統，大腦找得到它
[dry-run] case     將建立 [P2] 本機 LLM_PROVIDER=claude-code 只在 APP_ENV=local 生效，且 A3 建議以
[dry-run] case     將建立 [P1] 部署後記憶 API 以記憶專用角色運作，不回 503

[dry-run] 完成：新增 7 筆，更新 0 筆，共 7 筆
```

| 計畫 | 將建立的案例 | P1 | P2 |
|---|---|---|---|
| 260920 大腦入口：真實模型路徑（手動）（將建立） | 5 | 4 | 1 |
| 260920 大腦入口：本機與部署環境（手動）（將建立） | 2 | 1 | 1 |
| 合計 | 7 | 5 | 2 |

## 二、自動化案例描述（`--spec`，只更新既有案例）

自動化案例由 junit plugin 從 CI 結果建立；本工具只更新其 `text`（不碰 `is_automated`、`case_status`）。逐支 dry-run：

| spec 檔 | 規格註解數 | 將更新 | TCMS 上找不到 |
|---|---|---|---|
| `frontend/tests/e2e/a11y.spec.ts` | 28 | 28 | 0 |
| `frontend/tests/e2e/entry-page.spec.ts` | 63 | 62 | 1 |
| `frontend/tests/e2e/entry-page-live.spec.ts` | 5 | 5 | 0 |
| `frontend/tests/e2e/estimate-workspace.spec.ts` | 2 | 2 | 0 |
| `frontend/tests/e2e/member-pages.spec.ts` | 20 | 20 | 0 |
| `frontend/tests/e2e/memory-page.spec.ts` | 22 | 22 | 0 |
| `frontend/tests/e2e/object-picker.spec.ts` | 34 | 34 | 0 |
| `frontend/tests/e2e/project-pages.spec.ts` | 25 | 25 | 0 |
| `frontend/tests/e2e/regression.spec.ts` | 14 | 14 | 0 |
| `frontend/tests/e2e/sidebar-landmarks.spec.ts` | 3 | 3 | 0 |
| **合計** | **216** | **215** | **1** |

將更新的 215 筆與 PR #650 的 `ui-regression`（run 43556488900）`215 passed` 數目相同。

找不到的 1 筆（逐字）：

```
⚠️  TCMS 上找不到對應案例（1 筆）——該測試可能還沒在 CI 跑過：
  - U14 entry page › 只用鍵盤即可在入口頁輸入並送出
```

這是本站新寫的 `AC-A11Y.1` 案例，尚未在 CI 跑過；下一次 `ui-regression` 實跑後由 junit plugin 建立，屆時再跑一次 `--spec frontend/tests/e2e/entry-page.spec.ts` 寫入描述。**本工具不建立它**（會成為永遠沒有執行結果的孤兒）。

後端 `unittest`／`tests_pg` 的測試（含本站新增的 `test_claude_code_call_sites.py`、`test_cost_schema_startup_pg.py`）不經 junit plugin 回報 TCMS，`tcms_sync.py --spec` 也只解析 Playwright spec，故不在同步範圍內——它們的真實來源就是 repo 的測試碼與 `automation-test-plan.md`。

## 三、未同步或待處置

| 項目 | 狀態 | 理由 |
|---|---|---|
| 本 intent 7 個手動案例 | 未寫入（dry-run） | 待核可 |
| 215 筆自動化案例描述 | 未寫入（dry-run） | 待核可 |
| `U14 entry page › 只用鍵盤即可在入口頁輸入並送出` | 無法同步 | 尚未在 CI 跑過，TCMS 無對應案例 |
| intent `260802-last-login-column` 的兩個 cli 模式手動案例 | 未處置 | 本分支 commit `9781a97a` 退役了 `LLM_PROVIDER=cli`，兩案測的是已移除的功能，其中一案的追溯（`test_llm_provider.py::CliModeClearsConflictingVars`）已失效；需在 TCMS 停用並在該 intent record 註記，超出本站可寫範圍 |

## 核可後的實際同步（2026-11-14，conductor 執行）

使用者在核可關卡選「Approve」，授權寫入上方 dry-run 的內容。另外，那兩個過時案例的處理方式由使用者選「註記退役並停用」，看過 dry-run 後再選「寫入 TCMS」。

| 項目 | 結果 |
|---|---|
| 本 intent 手動案例（`--file manual-test-cases.md`） | 寫入前機械檢查全數通過；`完成：新增 7 筆，更新 0 筆，共 7 筆`。其中 claude-code 案例為 id 258，記憶角色案例為 id 259 |
| 自動化案例描述（`--spec`，10 支） | a11y 28、entry-page 62、entry-page-live 5、estimate-workspace 2、member-pages 20、memory-page 22、object-picker 34、project-pages 25、regression 14、sidebar-landmarks 3，合計 **215** 筆更新 |
| `U14 entry page › 只用鍵盤即可在入口頁輸入並送出` | 仍無對應案例。下一次 `ui-regression` 實跑後再跑一次 `--spec frontend/tests/e2e/entry-page.spec.ts` |
| `260802-last-login-column` 兩個 cli 案例 | 在該 intent 的 `manual-test-cases.md` 兩案的「目的」節加上退役註記，失效的追溯改為「已移除」說明。全 repo `tcms_validate.py --all` 結果為 `通過 27/27　ERROR 0　WARN 0`。以 `--file` 同步該檔：`完成：新增 0 筆，更新 13 筆`，兩案為 TCMS id 27、28。工具會整檔重送，所以另外 11 筆也被重送 |
| 兩案的 TCMS 狀態改為停用 | **未做**：`tcms_sync.py` 沒有改狀態的功能，需由使用者在 TCMS 介面把 id 27、28 設為停用 |

