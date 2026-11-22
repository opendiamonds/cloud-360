## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-11-05T16:31:35Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `aidlc/spaces/default/intents/261105-d-iac-generation/inception/requirements-analysis/requirements.md` > FR6.2 | FR6.2 只指定「D1 成功草稿」為執行 D2／D3 的前置條件，但未規定「執行 D3 是否要求 D2 已執行過至少一次」。scope-document 明載依賴鏈 D1→D2→D3，然而 requirements.md 中 FR6.2 的 AC（「無草稿時呼叫執行 API → 4xx」）只測試 D1 缺失，不測試 D2 缺失時 D3 的預期行為。Q4=A Advisory 解決了「掃描結果不擋 D3」的問題，但「根本未執行 D2 時 D3 是否可執行」是另一個不同問題，現行 requirements 未定義。開發者實作 D3 API 的前置條件檢查時，只能從 FR6.2 推得「有 D1 即可」；若此認知錯誤，使用者可繞過掃描直接 secrets 改寫，違背 D2 的安全目的。QA 無法為「無 D2 情況下執行 D3」的邊界寫出有判準的測試案例。 | 在 FR6.2（或新增 FR6.4）明確補充：執行 D3 時 D2 是否為必要前置（「D2 已執行過至少一次且有報告」或「不要求 D2 曾執行，Advisory 下可直接跑 D3」）；並補充對應 AC（例如「無 D2 報告情況下呼叫 D3 執行 API → 行為 X」）。 | New |
| R-02 | Major | `requirements.md` > FR1.3 | FR1.3 規定工作區內可改選其他架構圖，AC 為「下拉切換後，脈絡更新為新圖；後續 D1 以新圖為輸入」。但現有 D1 草稿（已用舊圖產出）在切圖後的狀態未定義：是保留（造成脈絡圖與草稿不符）、清空（可能意外丟失工作），還是版本化分開存放？FR2.6 的「不清除既有草稿」只適用於 D1 失敗情境，不適用切圖情境。開發者實作切圖邏輯時缺乏依據，QA 無法寫出「切圖後草稿狀態」的可判定測試。 | 在 FR1.3 AC 補充：切換架構圖脈絡後，現有 D1 草稿（若存在）的處置方式（清空並提示、保留並標示「脈絡已更換」、或其他），使開發者和 QA 有可測的預期狀態。 | New |
| R-03 | Minor | `requirements.md` > FR1.4 | FR1.4 的 AC（「上傳成功後脈絡指向新建／匯入圖」）只涵蓋成功路徑，未定義失敗路徑：格式不符（非 `.drawio`／`.xml`）、檔案過大、伺服器錯誤時 UI 應呈現什麼。FR1.5 的阻擋態是「無任何可用圖」時的終態，不等同上傳失敗的中間態。 | 在 FR1.4 補充上傳失敗的 AC（至少定義：格式不符時呈現錯誤訊息且脈絡不變；不要求本 stage 規定具體錯誤字串，留給設計）。 | New |
| R-04 | Minor | `requirements.md` > 全文（citations） | requirements.md 中大量使用 `[tp]`、`[rm]`、`[kb:WorkspacePage]` 等引用標記，但 requirements-analysis-questions.md 的 `## Sources` register 只定義了 `[intent]`、`[scope]`、`[feas]`、`[ux]`、`[codekb]`、`[practices]`。`[tp]`（team-practices）應為 `[practices]`，`[rm]`（rough-mockups）應為 `[ux]`，`[kb:WorkspacePage]` 應為 `[codekb]` 加子路徑說明。格式不一致雖不影響人工理解，但若 upstream-coverage sensor 或後續工具以 source key 比對，可能產生誤報。 | 建議統一引用標記與 sources register 的 key（`[practices]` 取代 `[tp]`；`[ux]` 取代 `[rm]`；`[codekb]` 取代 `[kb:*]`）。如維持現有縮寫，在 sources register 補充對應表。 | New |
| R-05 | Minor | `requirements.md` > NFR5 | NFR5 無障礙需求寫「對比與可讀文字 [rm]」，「對比」未附可量測閾值（如 WCAG AA 4.5:1）。「嚴重度不單靠顏色」是具體可測的，「對比與可讀文字」則不可測。 | 在 NFR5 補充「顏色對比符合 WCAG 2.1 AA（文字 4.5:1，大文字 3:1）」或等效可量測標準；若本 stage 暫不決定，明列為 OQ 而非模糊宣稱。 | New |

### Summary

requirements.md 整體結構清楚，FR 與 NFR 的 Q/F 追溯完整，Advisory／RBAC／PBT 等團隊護欄均已落地為可測 AC。阻擋 READY 的是 R-01：FR6.2 只規定 D1 為 D3 的前置，但「Advisory 下可跳過 D2 直接執行 D3」與「D2 必須曾執行過」是兩個完全不同的產品決策，現行文件靜默遺漏，工程師實作時無法從 requirements.md 單獨推得正確答案，QA 也無法寫出對應邊界測試。建議在審批關卡前補充 FR6.2（或新增 FR6.4）的 D2→D3 前置定義，其餘 Major／Minor 可在後續設計 stage 收斂。
