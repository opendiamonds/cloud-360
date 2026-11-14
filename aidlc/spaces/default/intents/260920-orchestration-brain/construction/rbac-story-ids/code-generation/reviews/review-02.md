## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T00:48:12Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-generation-plan.md > 一之一 第 3 點與第 184 行 | 把第 4 項移到 membership-service（U19）的方向合理：本單元只有 seed、log 與標籤，沒有邀請或改選的執行路徑，規則也寫明由 U19 執行。但這個移交沒有落地。第 3 點說以「membership-service 計畫中的對齊紀錄為準」，而 membership-service/code-generation 底下的計畫、摘要與測試指示全文都沒有提到 merge-blockers、BR7 或帳號狀態檢查（逐一 grep 為零命中），merge-blockers.md 第 13 列又指回本計畫的 §一之一。兩邊互相指向，沒有任何一邊有可執行步驟，第 4 項實際上沒有承接者。§一之一也只有「疊加 authorization_status 與 is_active」一句，沒有寫出 U19 要改的函式與要測的案例。 | 在 membership-service 的計畫補上第 4 項的實際步驟與對齊紀錄，或在 §一之一直接寫清楚交接內容：要改哪些函式、要加哪些案例（待核准受邀被拒、已停用受邀被拒、改選略過待核准與已停用者），並確認 U19 已接手。 | Resolved (reviewer) |
| R-02 | Major | backend/services/membership_service.py > assert_invitee_has_global_permission（約 657-682 行）、member_snapshots（282-296 行）、reselect_for_project（752 行起） | 現行程式與第 4 項描述的缺口只部分吻合，§一之一沒有區分。邀請端已經把 authorization_status 傳給 user_can，user_can 對非 approved 回 false，所以「待核准被邀請」其實已被擋；真正沒擋的是 is_active，這個函式完全沒有檢查。改選端更嚴重：member_snapshots 只讀 project_members 三個欄位，reselect_for_project 的候選只排除被停用的 owner，沒有任何地方過濾 K3.edit、approved 或 is_active，所以 BR7.3 的「持有 K3.edit」目前並未實作，待核准、已停用或只有 K3.view 的成員都可能被自動升為專案管理者。這是已提交程式裡的授權缺口，而它的修正步驟目前不在任何單元的計畫裡。 | 在移交內容中明寫兩點：邀請端補 is_active 檢查，改選端的候選集合必須過濾 K3.edit、approved、is_active，並用純函式（select_successor）以外的轉換層完成，以保持挑選函式的純度與排列不變性測試。對應的 allow/deny 雙向案例列入 U19 的測試。 | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-generation-plan.md > Step 10c、10d | 兩格維持未勾的處理是誠實的，也不阻擋：照字面執行的 M3、M4 仍為綠（PD-2），有效版本 M3-eff、M4-eff 已證明斷言不是恆真，勾上會讓計畫宣稱字面上沒發生的事。但計畫裡永遠留著兩個未勾項，之後的讀者要翻到摘要才知道原因。 | 在 10c、10d 旁加一行指向 code-summary 的 PD-2，並把 M3-eff、M4-eff 列為已勾的替代步驟，讓計畫自身說得清楚。 | Unresolved |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 七（最後一段） | 該段仍寫 schema_rbac.sql 驗證註解「位移至第 805 行」，現況是第 1248 行（檔頭的涵蓋清單在第 16 行，不是第 12 行），重新查驗表已用新行號，但原段落與 §二表格的「第 12 行」沒有同步。 | 在原段落加上行號已位移的註記，或改成不寫死行號的描述。 | Unresolved |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 三、七個測試與全套前後比對 | §三 的指令寫成 `cd backend && python -m unittest …`，基準數寫 432、439；重做節才寫須用 .venv，現為 1319。§三 沒有就地指向重做節。 | 在 §三 加一行指向「與已核可計畫／測試說明的落差」，避免照 §三 的指令跑會失敗或比錯基準。 | New |

> R-01 Reviewer note: 交接已落地：merge-blockers.md 第 4 列記為已修正，程式在 backend/services/membership_service.py 的 assert_invitee_has_global_permission（:829 起，:850 檢查 is_active，:857-863 把 authorization_status 傳給 user_can）。本單元的 seed、log、標籤與該修正沒有矛盾。

> R-02 Reviewer note: 改選端候選現經 qualified_successors（約 :471-501、:585、:945 起的 reselect_for_project），排除停用、待核准、只有 K3.view 者。邀請端補了 is_active 檢查。BR7.3 的 K3.edit 過濾已實作。

> R-03 Reviewer note: 計畫 :149-150 的 10c、10d 仍未勾，旁邊沒有指向 PD-2 與 M3-eff、M4-eff 的說明；:187 只寫「交由本輪判定」。code-summary 的重做節有說明，但讀計畫的人看不到。

> R-04 Reviewer note: code-summary 的 §二 表格（:27）仍寫「檔頭第 12 行」，§七（:265）仍寫「位移至第 805 行」。重做節雖已列出新行號（:16、:1248），原段落沒有加註已位移。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| tests.test_rbac_story_ids_seed（backend/.venv，快取導向 scratchpad） | Ran 7 tests，OK | 與 code-summary 重做節的紀錄一致；矩陣 352 列、兩份 seed 逐列等值的斷言在目前程式上成立。 |

### Summary

本單元零程式改動的重做可信：seed 測試實跑全綠，先前兩項 Major 已由 U19 的程式與測試處置，沒有開放的 Critical 或 Major。剩餘三項皆為 Minor，是計畫與摘要中的過期說明，不影響實作。計數：Prior 4（Fixed 2、Still applies 2）、New 1（Minor）。
