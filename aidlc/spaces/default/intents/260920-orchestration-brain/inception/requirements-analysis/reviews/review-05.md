## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-25T01:51:19Z
**Iteration:** 1

本輪為限定範圍的最終複驗：只查 R-20（NFR2 量測機制的 `expect.soft()` 等價誤述）
與 R-21（R-11 段落的現在式失效主張）兩項修正，以及七項計數與 contract 的重算。
`review_class: advisory`。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-20 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md > NFR2 > 量測機制（R-14 修正） | 機制已收斂為單一路徑：N 個情境同在一個 `test()` 內、逐情境以 `try`／布林值捕捉、明文「不對單一情境下任何 `expect` 或 `expect.soft`」、最後只對 `通過數 / N ≥ 0.95` 下一次斷言。約束句已由「不得中止該 test」改為「不得使該 test 被判為失敗」並附「在 Playwright 下這兩者不是同一件事」的括號。新增的 `expect.soft()` 專屬子項技術上正確——soft assertion 不中止執行但仍把該 test 標為 failed，故 `.stats.unexpected` 非 0、`ui-regression` 的 `exit 1` 觸發、門檻回到 100%。已逐項複驗支撐事實：`frontend/playwright.config.ts` 確為單一 `chromium` project 且 `testDir: './tests/e2e'`；`.github/workflows/ui-regression.md` 確以 `jq '.stats.unexpected'` 非 0 即 `exit 1`（容忍 `stats.flaky`）。實作者已無法從本文合理推導出 100% 門檻 | 無 | Resolved |
| R-21 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md > 人工確認範圍的落差與其處置（R-11） | 句子已限定為「**修訂 2 當時**，`0.7` 這個數字在問題檔零出現」，後續子句改為「**當時那份**收據」，並以括號指向第 3 點與結語。實測問題檔現有 `0.7` 一次命中，與「修訂 2 當時為零、修訂 3 重取確認後納入」的沿革敘述一致，故本句以現行措辭為真。全段再讀一次無殘留的現在式失效主張：第 3 點與結語皆明述現況為「已完整涵蓋七項與 FR1.7 的數值」，與開頭的歷史落差描述不衝突 | 無 | Resolved |

### 相鄰影響檢查

- 移除 soft assertion 選項未破壞該子彈的其餘論證：「必須同一個 `test()` 內、只斷言一次」、「獨立測試在本 repo 不可行」、「`.stats.unexpected` 在本 NFR 下的語意」三個子項互相支撐且與新機制一致。
- **NFR11 豁免仍成立**：其判定為「每個情境的切換次數都嚴格少於基準」，屬全體量化條件，寫成各自的 `test()` 正確；本輪修正只收窄 NFR2 的記錄手段，不觸及 NFR11 的形狀，且「兩條 NFR 的量測形狀不得互相套用」一句仍在。

### 計數重算（本輪自行執行，非沿用 lead 報告）

| 項目 | lead 報告 | 本輪實算 | 一致 |
|---|---|---|---|
| FR 子需求 | 49 | 49（`^- **FR<n>.<m>**` 定義式；含 FR4.3a／FR4.3b／FR4.5a） | 是 |
| 重複 id | 0 | 0 | 是 |
| FR 群組 | 10 | 10（FR1–FR10） | 是 |
| NFR | 11 | 11（NFR1–NFR11，無跳號） | 是 |
| N-items | 7 | 7（N-1–N-7） | 是 |
| Open Questions | 14 | 14（OQ-1–OQ-14） | 是 |
| Assumptions | 7 | 7（A-1–A-7） | 是 |
| 懸空交叉引用 | 0 | 0（全部 `FR<n>.<m>` 引用皆有定義；NFR／N／OQ／A 無超出範圍者） | 是 |

`python3 scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`（本輪實跑）。

### Summary

R-20 與 R-21 皆已消除，且兩項修正未破壞相鄰推論（NFR11 豁免、`.stats.unexpected`
語意、R-11 段落的沿革敘述皆自洽）。七項計數與 repo contract 本輪逐項重算全數相符，
本 revision 四輪來的計數漂移特徵在本輪未再出現。範圍內無新發現。
